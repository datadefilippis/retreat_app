"""Sub-stream 2.6: Organization.application_fee_percent + propagation.

Two surfaces:
  1. Pydantic model validation — value must be in [0, 10].
  2. The fee on the org doc reaches the provider via
     :class:`CheckoutSessionRequest.application_fee_percent`.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest
from pydantic import ValidationError

from models.organization import Organization


# ── Model validation ────────────────────────────────────────────────────────


def _build_org(**extra):
    payload = {"name": "Org X"}
    payload.update(extra)
    return Organization(**payload)


def test_default_application_fee_is_zero():
    """v1 founding clients pay no platform cut by default."""
    org = _build_org()
    assert org.application_fee_percent == 0.0


@pytest.mark.parametrize("value", [0, 0.5, 1.5, 2.5, 9.9, 10])
def test_accepts_values_in_range(value):
    org = _build_org(application_fee_percent=value)
    assert float(org.application_fee_percent) == float(value)


@pytest.mark.parametrize("bad", [-0.1, -1, 10.5, 11, 100])
def test_rejects_values_outside_range(bad):
    """A typo — 100 instead of 1 — must not silently drain a merchant."""
    with pytest.raises(ValidationError):
        _build_org(application_fee_percent=bad)


# ── Propagation: org → CheckoutSessionRequest → provider ────────────────────


@pytest.mark.asyncio
async def test_zero_fee_arrives_at_provider_as_zero():
    """A v1 org (default 0) must produce a request with fee=0 so the
    provider knows to skip ``application_fee_amount`` entirely.
    """
    captured = await _run_checkout_capture(org_doc={"application_fee_percent": 0})
    assert captured.application_fee_percent == Decimal("0")


@pytest.mark.asyncio
async def test_non_zero_fee_arrives_at_provider():
    captured = await _run_checkout_capture(
        org_doc={"application_fee_percent": 2.5},
    )
    assert captured.application_fee_percent == Decimal("2.5")


@pytest.mark.asyncio
async def test_legacy_org_without_field_defaults_to_zero():
    """Org docs that pre-date the field must not crash — default 0."""
    captured = await _run_checkout_capture(org_doc={})  # no field
    assert captured.application_fee_percent == Decimal("0")


@pytest.mark.asyncio
async def test_org_with_string_fee_value_is_coerced():
    """Defensive coercion: a string fee on a hand-edited DB doc
    (e.g. ``"1.5"``) must still produce a valid Decimal.
    """
    captured = await _run_checkout_capture(
        org_doc={"application_fee_percent": "1.5"},
    )
    assert captured.application_fee_percent == Decimal("1.5")


# ── Test infrastructure ─────────────────────────────────────────────────────


async def _run_checkout_capture(*, org_doc):
    """Drive ``create_checkout_session`` with a capturing provider.

    Returns the :class:`CheckoutSessionRequest` the service handed
    off so individual tests can assert on whichever field they care
    about. Keeps the fixture noise out of the test bodies.
    """
    from services import payment_checkout_service as svc
    from payment_providers import (
        CheckoutSessionRequest,
        CheckoutSessionResult,
        PaymentProvider,
        PaymentProviderRegistry,
    )

    captured: dict = {}

    class CapturingProvider(PaymentProvider):
        name = "stripe"

        async def create_checkout_session(self, request):
            captured["request"] = request
            return CheckoutSessionResult(
                url="https://checkout.example/cs_1",
                session_id="cs_1",
                provider="stripe",
                connected_account="acct_test",
            )

        async def get_account_capabilities(self, connected_account_id):
            from payment_providers import AccountCapabilities
            return AccountCapabilities(card_active=True)

        def verify_webhook(self, payload, signature_header, secret):
            return {}

        def parse_event(self, verified_event, connected_account=None):
            from payment_providers import NormalizedEvent
            return NormalizedEvent(
                type="", provider="stripe", provider_event_id="",
                connected_account=None, order_id=None, org_id=None,
                currency=None, amount=None, payment_intent_id=None,
                raw={},
            )

    PaymentProviderRegistry._reset_for_tests()
    PaymentProviderRegistry.register("stripe", CapturingProvider())

    fake_orders = MagicMock()
    fake_orders.update_one = AsyncMock()

    order = {
        "id": "ord_fee_smoke",
        "payment_intent": "required",
        "total": 100.0,
        "currency": "EUR",
        "items": [{
            "product_name": "Test product",
            "quantity": 1,
            "unit_price": 100.0,
            "line_total": 100.0,
        }],
        "customer_id": "cus_x",
    }

    with patch.object(
        svc, "_get_connected_account_id",
        new=AsyncMock(return_value="acct_test"),
    ), patch.object(
        svc, "_lookup_customer_email",
        new=AsyncMock(return_value=None),
    ), patch.object(
        svc, "_resolve_org_doc_for_provider",
        new=AsyncMock(return_value=org_doc),
    ), patch(
        "services.commerce_rules.is_direct_checkout_safe_async",
        new=AsyncMock(return_value=(True, "ok")),
    ), patch(
        "services.payment_resolution.resolve_org_payment_readiness",
        new=AsyncMock(return_value=SimpleNamespace(
            checkout_available=True, reason_code=None,
        )),
    ), patch("database.orders_collection", fake_orders):
        result = await svc.create_checkout_session("org_x", order)

    assert result is not None
    return captured["request"]
