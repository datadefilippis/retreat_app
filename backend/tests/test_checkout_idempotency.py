"""Sub-stream 2.5: idempotency key generation in
``services.payment_checkout_service``.

The wire-level forwarding (key → Stripe SDK) is covered by
``test_stripe_provider.test_create_checkout_session_idempotency_key_forwarded``.
This test pins down that the caller actually generates a
deterministic key for every order and passes it to the provider.
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


@pytest.mark.asyncio
async def test_idempotency_key_is_passed_through_to_provider():
    """create_checkout_session must build a CheckoutSessionRequest
    with ``idempotency_key="checkout:<order_id>"`` and forward it to
    the provider.
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
        "id": "ord_idempotency_smoke",
        "payment_intent": "required",
        "total": 49.50,
        "currency": "CHF",
        "items": [{
            "product_name": "Test product",
            "quantity": 1,
            "unit_price": 49.50,
            "line_total": 49.50,
        }],
        "customer_id": "cus_x",
    }

    # Mock the auxiliary lookups so the function can reach the
    # provider call site.
    with patch.object(
        svc, "_get_connected_account_id",
        new=AsyncMock(return_value="acct_test"),
    ), patch.object(
        svc, "_lookup_customer_email",
        new=AsyncMock(return_value="buyer@example.test"),
    ), patch.object(
        svc, "_resolve_org_doc_for_provider",
        new=AsyncMock(return_value={"id": "org_x", "currency": "CHF"}),
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

    assert result is not None, "create_checkout_session returned None unexpectedly"
    assert "request" in captured, "Provider was not called"

    req: CheckoutSessionRequest = captured["request"]
    assert req.idempotency_key == "checkout:ord_idempotency_smoke"

    # Re-running with the same order_id must produce the same key
    # (deterministic so Stripe collapses retries).
    captured.clear()
    fake_orders.update_one.reset_mock()
    with patch.object(
        svc, "_get_connected_account_id",
        new=AsyncMock(return_value="acct_test"),
    ), patch.object(
        svc, "_lookup_customer_email",
        new=AsyncMock(return_value=None),
    ), patch.object(
        svc, "_resolve_org_doc_for_provider",
        new=AsyncMock(return_value={"id": "org_x", "currency": "CHF"}),
    ), patch(
        "services.commerce_rules.is_direct_checkout_safe_async",
        new=AsyncMock(return_value=(True, "ok")),
    ), patch(
        "services.payment_resolution.resolve_org_payment_readiness",
        new=AsyncMock(return_value=SimpleNamespace(
            checkout_available=True, reason_code=None,
        )),
    ), patch("database.orders_collection", fake_orders):
        await svc.create_checkout_session("org_x", order)

    req2: CheckoutSessionRequest = captured["request"]
    assert req2.idempotency_key == "checkout:ord_idempotency_smoke"


@pytest.mark.asyncio
async def test_idempotency_key_uses_order_id_namespace():
    """Different orders must get different keys (no collision)."""
    from services import payment_checkout_service as svc
    from payment_providers import (
        CheckoutSessionResult,
        PaymentProvider,
        PaymentProviderRegistry,
    )

    seen_keys: list[str] = []

    class CapturingProvider(PaymentProvider):
        name = "stripe"

        async def create_checkout_session(self, request):
            seen_keys.append(request.idempotency_key)
            return CheckoutSessionResult(
                url="https://x", session_id="cs_x",
                provider="stripe", connected_account="acct_test",
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

    def _make_order(oid: str) -> dict:
        return {
            "id": oid,
            "payment_intent": "required",
            "total": 10.0,
            "currency": "EUR",
            "items": [{"product_name": "x", "quantity": 1, "unit_price": 10.0, "line_total": 10.0}],
            "customer_id": "cus_x",
        }

    common_patches = [
        patch.object(svc, "_get_connected_account_id",
                     new=AsyncMock(return_value="acct_test")),
        patch.object(svc, "_lookup_customer_email",
                     new=AsyncMock(return_value=None)),
        patch.object(svc, "_resolve_org_doc_for_provider",
                     new=AsyncMock(return_value={})),
        patch("services.commerce_rules.is_direct_checkout_safe_async",
              new=AsyncMock(return_value=(True, "ok"))),
        patch("services.payment_resolution.resolve_org_payment_readiness",
              new=AsyncMock(return_value=SimpleNamespace(
                  checkout_available=True, reason_code=None,
              ))),
        patch("database.orders_collection", fake_orders),
    ]

    from contextlib import ExitStack
    with ExitStack() as stack:
        for p in common_patches:
            stack.enter_context(p)
        await svc.create_checkout_session("org_x", _make_order("ord_aaa"))
        await svc.create_checkout_session("org_x", _make_order("ord_bbb"))

    assert seen_keys == ["checkout:ord_aaa", "checkout:ord_bbb"]
