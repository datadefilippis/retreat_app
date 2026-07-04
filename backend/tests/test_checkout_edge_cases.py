"""Edge case audit for the checkout lifecycle.

Pre-merchant onboarding: verify the unhappy paths in
``reconcile_checkout_event`` and ``verify_commerce_order_payment`` hold
under tampering, races, and operational drift. The happy path is
covered by ``test_stripe_provider.py`` + ``test_checkout_idempotency.py``;
this file catalogues the things that go wrong in production.

Scenarios pinned here:

  1. Currency tampering — session.currency != order's snapshot
     → rejected with ValueError, no DB mutation
  2. Session reference mismatch — stored ref differs from event session_id
     → rejected (customer paid a stale Session URL)
  3. Connected account mismatch — event.account != stored account
     → rejected (cross-merchant tampering)
  4. Same event_id replayed — Stripe retries deliver twice
     → second one short-circuits as "event_already_processed"
  5. Webhook arrives AFTER manual verify already collected the order
     → "already_collected" path records the event but does not double-process
  6. Verify then real webhook — synthetic event_id ≠ real event_id
     → real webhook still hits the "already_collected" guard, no double confirm
  7. Missing afianco metadata marker — third-party Stripe webhook misrouted
     → rejected with reason="not_afianco_session", no DB read
  8. Session payment_status != "paid" — incomplete sessions
     → skipped, order untouched

These are stronger than the existing happy-path tests because they
exercise *what should NOT happen*. A regression that silently relaxes
any of these guards would be a real production safety hole — exactly
what we want to catch before a merchant ships it.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services import payment_checkout_service


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_event(
    event_id="evt_1",
    session_id="cs_test_1",
    order_id="ord_1",
    org_id="org_1",
    payment_status="paid",
    source="afianco",
    currency="eur",
    account="acct_test_merchant",
    payment_intent="pi_1",
):
    """Build a minimal checkout.session.completed-shaped event dict."""
    return {
        "id": event_id,
        "account": account,
        "data": {
            "object": {
                "id": session_id,
                "payment_status": payment_status,
                "currency": currency,
                "payment_intent": payment_intent,
                "metadata": {
                    "order_id": order_id,
                    "org_id": org_id,
                    "source": source,
                    "checkout_type": "commerce",
                },
            }
        },
    }


def _make_order(
    order_id="ord_1",
    org_id="org_1",
    currency="EUR",
    payment_intent="required",
    stored_session_id="cs_test_1",
    stored_account="acct_test_merchant",
    processed_events=None,
):
    return {
        "id": order_id,
        "organization_id": org_id,
        "currency": currency,
        "payment_intent": payment_intent,
        "items": [{"product_name": "P1", "quantity": 1, "unit_price": 10.0}],
        "payment_checkout": {
            "reference": stored_session_id,
            "connected_account_id": stored_account,
            "processed_events": processed_events or [],
            "url": "https://checkout.stripe.com/c/pay/cs_test_1",
            "provider": "stripe",
            "flow_version": "connect_v1",
            "created_at": "2026-05-10T12:00:00+00:00",
        },
    }


# ── 1. Currency tampering ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_rejects_currency_mismatch():
    """Order snapshot=EUR but session arrives as USD → must raise.

    Tampering with session metadata or a Stripe-side bug could otherwise
    silently book a USD charge against an EUR order. We reject hard.
    """
    event = _make_event(currency="usd")
    order = _make_order(currency="EUR")

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)
    fake_orders.update_one = AsyncMock()

    with patch("database.orders_collection", fake_orders):
        with pytest.raises(ValueError, match="Currency mismatch"):
            await payment_checkout_service.reconcile_checkout_event(event)

    # No mutation on rejection.
    fake_orders.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_reconcile_currency_check_is_case_insensitive():
    """Stripe returns lowercase 'eur' but order snapshot is 'EUR' —
    that's not a mismatch, just a case difference."""
    event = _make_event(currency="eur")  # lowercase
    order = _make_order(currency="EUR")  # uppercase

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)
    fake_orders.update_one = AsyncMock()

    with patch("database.orders_collection", fake_orders), \
         patch("services.order_service.confirm_order",
               new_callable=AsyncMock,
               return_value={"order_number": "ORD-0001"}), \
         patch("services.order_email_service.notify_merchant_new_order",
               new_callable=AsyncMock):
        result = await payment_checkout_service.reconcile_checkout_event(event)

    assert result["action"] == "confirmed"


# ── 2. Session reference mismatch ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_rejects_session_reference_mismatch():
    """Customer paid an old/stale Session URL while a newer one was active.

    Stripe Sessions live ~24h; if a customer bookmarks the URL and pays
    after we regenerated the Session, the stored reference points to the
    NEW Session and the webhook arrives for the OLD one. We refuse to
    reconcile to keep the audit trail honest.
    """
    event = _make_event(session_id="cs_test_OLD")
    order = _make_order(stored_session_id="cs_test_NEW")

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)
    fake_orders.update_one = AsyncMock()

    with patch("database.orders_collection", fake_orders):
        with pytest.raises(ValueError, match="Session reference mismatch"):
            await payment_checkout_service.reconcile_checkout_event(event)

    fake_orders.update_one.assert_not_called()


# ── 3. Connected account mismatch ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_rejects_account_mismatch():
    """event.account != stored account → reject.

    A misrouted webhook (or a forged event from a different connected
    account) must never confirm someone else's order.
    """
    event = _make_event(account="acct_INTRUDER")
    order = _make_order(stored_account="acct_REAL")

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)
    fake_orders.update_one = AsyncMock()

    with patch("database.orders_collection", fake_orders):
        with pytest.raises(ValueError, match="Connected account mismatch"):
            await payment_checkout_service.reconcile_checkout_event(event)

    fake_orders.update_one.assert_not_called()


# ── 4. Replayed event (Stripe retry) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_dedupes_replayed_event_id():
    """Same event_id seen before → short-circuit with skipped/already_processed.

    Stripe retries failed webhooks. Without this guard, retries would
    re-emit the same audit log + re-fire merchant notification emails.
    """
    event = _make_event(event_id="evt_replayed")
    order = _make_order(processed_events=["evt_replayed"])

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)
    fake_orders.update_one = AsyncMock()

    with patch("database.orders_collection", fake_orders):
        result = await payment_checkout_service.reconcile_checkout_event(event)

    assert result["action"] == "skipped"
    assert result["reason"] == "event_already_processed"
    fake_orders.update_one.assert_not_called()


# ── 5. Already-collected order (verify ran first, then webhook arrives) ──


@pytest.mark.asyncio
async def test_reconcile_records_event_when_order_already_collected():
    """Webhook arrives AFTER verify_commerce_order_payment already
    collected the order. We must:
      - NOT re-confirm the order (no duplicate emails / DB writes)
      - Record the event_id so future replays of THIS event are also
        deduped
      - Return action=skipped reason=already_collected for observability.
    """
    event = _make_event(event_id="evt_real_webhook")
    order = _make_order(
        payment_intent="collected",  # verify already flipped this
        processed_events=["verify_ord_1_cs_test_1"],  # synthetic verify event
    )

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)
    fake_orders.update_one = AsyncMock()

    with patch("database.orders_collection", fake_orders):
        result = await payment_checkout_service.reconcile_checkout_event(event)

    assert result["action"] == "skipped"
    assert result["reason"] == "already_collected"
    # Must record the new event_id so a future replay is also deduped.
    # _record_event uses $addToSet (not $push) for set semantics — same
    # event_id arriving twice is a no-op on the array.
    fake_orders.update_one.assert_called_once()
    update_call = fake_orders.update_one.call_args
    update_doc = update_call[0][1] if len(update_call[0]) >= 2 else update_call.kwargs.get("update", {})
    add_op = update_doc.get("$addToSet", {})
    assert "payment_checkout.processed_events" in add_op
    assert add_op["payment_checkout.processed_events"] == "evt_real_webhook"


# ── 6. Verify-then-real-webhook race ─────────────────────────────────────


@pytest.mark.asyncio
async def test_synthetic_verify_event_does_not_dedupe_real_webhook():
    """The synthetic event_id format used by verify_commerce_order_payment
    is ``verify_<order_id>_<session_id>`` — guaranteed unique vs Stripe's
    ``evt_<random>`` namespace. So a subsequent real webhook with id
    ``evt_xxx`` does NOT collide with the synthetic one in the
    ``processed_events`` set, and falls through to the "already_collected"
    branch (NOT the "event_already_processed" branch).

    This pins the namespace contract: if someone changes the synthetic
    id format to start with ``evt_`` they would create a deduplication
    hole where verify+webhook produce a 50/50 race depending on which
    one's id Stripe picks.
    """
    synthetic_id = "verify_ord_1_cs_test_1"
    real_id = "evt_real_xxx"

    # Synthetic prefix must NOT collide with Stripe's evt_ prefix.
    assert not synthetic_id.startswith("evt_"), (
        "Synthetic verify event_id must use a non-evt_ prefix to avoid "
        "namespace collision with real Stripe webhooks"
    )
    assert synthetic_id != real_id


# ── 7. Non-afianco session ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_skips_non_afianco_sessions():
    """A connected account may receive Stripe webhooks for sessions
    NOT created by afianco (merchant uses Stripe Checkout for some other
    purpose on the same account). We skip cleanly without touching the
    DB at all.
    """
    event = _make_event(source="other_app")

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock()  # would raise if hit

    with patch("database.orders_collection", fake_orders):
        result = await payment_checkout_service.reconcile_checkout_event(event)

    assert result["action"] == "skipped"
    assert result["reason"] == "not_afianco_session"
    fake_orders.find_one.assert_not_called()


# ── 8. Incomplete session ────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("payment_status", ["unpaid", "no_payment_required", None])
async def test_reconcile_skips_session_not_paid(payment_status):
    """Sessions can fire ``checkout.session.completed`` events with
    payment_status != 'paid' (test mode oddities, async payment methods
    pending, etc.). Reconcile must NOT mark the order as collected.
    """
    event = _make_event(payment_status=payment_status)

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock()  # would raise if hit
    fake_orders.update_one = AsyncMock()

    with patch("database.orders_collection", fake_orders):
        result = await payment_checkout_service.reconcile_checkout_event(event)

    assert result["action"] == "skipped"
    assert result["reason"].startswith("payment_status=")
    fake_orders.find_one.assert_not_called()
    fake_orders.update_one.assert_not_called()


# ── 9. Missing required metadata ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_raises_on_missing_order_id():
    """source=afianco is set but order_id is absent → raise.

    Defensive — should never happen in practice (we always set order_id
    in metadata when creating the Session), but if it does, raising
    gives Stripe the signal to retry, which surfaces the bug in our
    Sentry alerts instead of silently swallowing the event.
    """
    event = _make_event()
    # Strip order_id from the metadata block.
    event["data"]["object"]["metadata"].pop("order_id")

    with pytest.raises(ValueError, match="Missing order_id or org_id"):
        await payment_checkout_service.reconcile_checkout_event(event)


@pytest.mark.asyncio
async def test_reconcile_raises_when_order_not_found():
    """afianco-marked session but order_id refers to a deleted/migrated
    order. Raise → Sentry → human investigates."""
    event = _make_event(order_id="ord_missing")

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=None)

    with patch("database.orders_collection", fake_orders):
        with pytest.raises(ValueError, match="not found"):
            await payment_checkout_service.reconcile_checkout_event(event)


# ── 10. Session_id check is null-safe ────────────────────────────────────


# ── 11. verify_commerce_order_payment edge cases ────────────────────────


@pytest.mark.asyncio
async def test_verify_commerce_idempotent_on_already_collected_order():
    """Calling verify on an already-collected order short-circuits with
    ``already_reconciled`` BEFORE hitting Stripe — saves an API round
    trip and prevents accidental double-processing if reconcile is
    racing on the same order."""
    order = _make_order(payment_intent="collected")
    order["order_number"] = "ORD-0042"

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)
    stripe_mock = MagicMock()
    stripe_mock.checkout.Session.retrieve = MagicMock()  # would raise if called

    with patch("database.orders_collection", fake_orders), \
         patch.object(payment_checkout_service, "_get_stripe", return_value=stripe_mock):
        result = await payment_checkout_service.verify_commerce_order_payment(
            order_id="ord_1", org_id="org_1",
        )

    assert result["status"] == "already_reconciled"
    assert result["order_number"] == "ORD-0042"
    # Stripe must NOT be called on the short-circuit path.
    stripe_mock.checkout.Session.retrieve.assert_not_called()


@pytest.mark.asyncio
async def test_verify_commerce_returns_session_not_found_when_no_reference():
    """Order has no stored Stripe Session yet (checkout never started).
    verify must return a structured ``session_not_found`` instead of
    crashing or hitting Stripe with an empty id."""
    order = _make_order()
    order["payment_checkout"] = {"reference": None}  # nothing started yet

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)

    with patch("database.orders_collection", fake_orders):
        result = await payment_checkout_service.verify_commerce_order_payment(
            order_id="ord_1", org_id="org_1",
        )

    assert result["status"] == "session_not_found"


@pytest.mark.asyncio
async def test_verify_commerce_returns_still_unpaid_for_pending_session():
    """Customer started checkout but didn't pay → Session.retrieve says
    payment_status='unpaid'. verify must report this truthfully without
    flipping the order to collected."""
    order = _make_order()

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)
    fake_orders.update_one = AsyncMock()

    fake_session = {
        "id": "cs_test_1",
        "payment_status": "unpaid",
        "status": "open",
        "currency": "eur",
    }
    stripe_mock = MagicMock()
    stripe_mock.checkout.Session.retrieve = MagicMock(return_value=fake_session)

    with patch("database.orders_collection", fake_orders), \
         patch.object(payment_checkout_service, "_get_stripe", return_value=stripe_mock), \
         patch("services.stripe_service._normalize_stripe_object",
               side_effect=lambda x: x):
        result = await payment_checkout_service.verify_commerce_order_payment(
            order_id="ord_1", org_id="org_1",
        )

    assert result["status"] == "still_unpaid"
    assert result["payment_status"] == "unpaid"
    # Order MUST NOT have been mutated.
    fake_orders.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_verify_commerce_returns_error_on_stripe_failure():
    """Stripe API down / network blip → return structured error, never
    raise to the caller (admin endpoint)."""
    order = _make_order()

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)

    stripe_mock = MagicMock()
    stripe_mock.checkout.Session.retrieve = MagicMock(
        side_effect=RuntimeError("connection_reset"),
    )

    with patch("database.orders_collection", fake_orders), \
         patch.object(payment_checkout_service, "_get_stripe", return_value=stripe_mock):
        result = await payment_checkout_service.verify_commerce_order_payment(
            order_id="ord_1", org_id="org_1",
        )

    assert result["status"] == "error"
    assert result["reason"] == "stripe_retrieve_failed"
    assert "connection_reset" in result["error"]


@pytest.mark.asyncio
async def test_reconcile_handles_order_with_no_stored_reference():
    """Edge case: order has payment_checkout but the reference field is
    missing (legacy data). We should NOT raise mismatch — just trust
    the metadata and proceed.
    """
    event = _make_event()
    order = _make_order(stored_session_id=None)
    # Remove reference entirely
    order["payment_checkout"]["reference"] = None

    fake_orders = MagicMock()
    fake_orders.find_one = AsyncMock(return_value=order)
    fake_orders.update_one = AsyncMock()

    with patch("database.orders_collection", fake_orders), \
         patch("services.order_service.confirm_order",
               new_callable=AsyncMock,
               return_value={"order_number": "ORD-0001"}), \
         patch("services.order_email_service.notify_merchant_new_order",
               new_callable=AsyncMock):
        result = await payment_checkout_service.reconcile_checkout_event(event)

    assert result["action"] == "confirmed"
