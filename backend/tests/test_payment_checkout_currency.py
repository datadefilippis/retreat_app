"""Tests for the currency-aware paths in ``payment_checkout_service``.

Two surfaces:

  1. ``check_order_eligibility`` must gate against the per-currency
     Stripe minimum (CHF/EUR) instead of a hardcoded EUR floor.
  2. ``reconcile_checkout_event`` must reject events whose
     ``session.currency`` differs from the order's snapshot.

Webhook tests use an in-memory mock of ``orders_collection`` to keep
the suite DB-free; the reconciler imports the collection lazily inside
its body so a single ``patch("database.orders_collection", ...)`` is
enough.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services.payment_checkout_service import (
    MIN_CHECKOUT_AMOUNT_EUR,
    check_order_eligibility,
    reconcile_checkout_event,
)


# ── check_order_eligibility — per-currency minimum ──────────────────────────


def _eligible_order(**overrides) -> dict:
    base = {
        "id": "ord_test",
        "payment_intent": "required",
        "total": 50.0,
        "currency": "EUR",
        "items": [{"line_total": 50.0, "quantity": 1}],
    }
    base.update(overrides)
    return base


def test_eligibility_legacy_mineur_alias_preserved():
    """The legacy ``MIN_CHECKOUT_AMOUNT_EUR`` symbol must still equal
    the EUR minimum so that ``routers/public.py`` (which imports it
    directly to render a localized message) keeps working.
    """
    from core.checkout_minimums import get_minimum
    assert MIN_CHECKOUT_AMOUNT_EUR == float(get_minimum("EUR"))


def test_eligibility_eur_above_minimum_passes():
    eligible, reason = check_order_eligibility(_eligible_order(total=10.00, currency="EUR"))
    assert eligible is True
    assert reason == "eligible"


def test_eligibility_eur_below_minimum_fails():
    eligible, reason = check_order_eligibility(_eligible_order(total=0.30, currency="EUR"))
    assert eligible is False
    assert reason == "below_minimum_amount"


def test_eligibility_chf_above_minimum_passes():
    eligible, reason = check_order_eligibility(_eligible_order(total=10.00, currency="CHF"))
    assert eligible is True
    assert reason == "eligible"


def test_eligibility_chf_below_minimum_fails():
    eligible, reason = check_order_eligibility(_eligible_order(total=0.30, currency="CHF"))
    assert eligible is False
    assert reason == "below_minimum_amount"


def test_eligibility_legacy_order_without_currency_uses_eur_minimum():
    """An order doc with no ``currency`` field falls through to EUR via
    ``get_currency_for_order`` and is gated by the EUR minimum.
    """
    order = _eligible_order(total=0.30)
    order.pop("currency", None)
    eligible, reason = check_order_eligibility(order)
    assert eligible is False
    assert reason == "below_minimum_amount"


def test_eligibility_other_reasons_unchanged():
    """Smoke check: non-currency-related rejection paths still fire."""
    assert check_order_eligibility({"payment_intent": "none", "total": 50.0}) == (
        False, "payment_intent_not_required",
    )
    assert check_order_eligibility(_eligible_order(total=0)) == (False, "zero_total")
    bad_line = _eligible_order(items=[{"line_total": 0, "quantity": 2}])
    assert check_order_eligibility(bad_line) == (False, "zero_price_line")


# ── reconcile_checkout_event — currency match validation ────────────────────


def _event(session_currency: str = "eur", session_id: str = "cs_test_1") -> dict:
    return {
        "id": "evt_test_1",
        "type": "checkout.session.completed",
        "account": "acct_test",
        "data": {
            "object": {
                "id": session_id,
                "currency": session_currency,
                "payment_status": "paid",
                "metadata": {
                    "order_id": "ord_test",
                    "org_id": "org_test",
                    "source": "afianco",
                },
            }
        },
    }


def _stored_order(currency: str = "EUR") -> dict:
    return {
        "id": "ord_test",
        "organization_id": "org_test",
        "currency": currency,
        "payment_intent": "required",
        "payment_checkout": {
            "reference": "cs_test_1",
            "connected_account_id": "acct_test",
            "processed_events": [],
        },
    }


@pytest.mark.asyncio
async def test_reconcile_rejects_currency_mismatch():
    """Order is EUR, Stripe charged CHF → reconciler must refuse."""
    fake = AsyncMock()
    fake.find_one = AsyncMock(return_value=_stored_order(currency="EUR"))
    fake.update_one = AsyncMock()

    with patch("database.orders_collection", fake):
        with pytest.raises(ValueError, match="Currency mismatch"):
            await reconcile_checkout_event(_event(session_currency="chf"))

    # The mismatch must be detected BEFORE we mark the order collected.
    fake.update_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_reconcile_accepts_matching_currency_chf():
    """Order is CHF, Stripe charged CHF → reconciler proceeds (no raise)."""
    fake = AsyncMock()
    fake.find_one = AsyncMock(return_value=_stored_order(currency="CHF"))
    fake.update_one = AsyncMock()

    with patch("database.orders_collection", fake), \
         patch("services.order_service.confirm_order", new=AsyncMock(return_value={"order_number": "ORD-001"})), \
         patch("services.order_email_service.notify_merchant_new_order", new=AsyncMock()):
        result = await reconcile_checkout_event(_event(session_currency="chf"))

    assert result.get("action") == "confirmed"
    fake.update_one.assert_awaited()


@pytest.mark.asyncio
async def test_reconcile_skips_currency_check_when_session_lacks_currency():
    """Defensive: a malformed event with no currency field shouldn't break
    the legacy reconciliation path. The validator is best-effort.
    """
    event = _event()
    event["data"]["object"].pop("currency", None)

    fake = AsyncMock()
    fake.find_one = AsyncMock(return_value=_stored_order(currency="EUR"))
    fake.update_one = AsyncMock()

    with patch("database.orders_collection", fake), \
         patch("services.order_service.confirm_order", new=AsyncMock(return_value={"order_number": "ORD-001"})), \
         patch("services.order_email_service.notify_merchant_new_order", new=AsyncMock()):
        result = await reconcile_checkout_event(event)

    assert result.get("action") == "confirmed"
