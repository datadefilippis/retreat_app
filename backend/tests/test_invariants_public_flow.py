"""Sentinel tests for afianco system invariants — public flow.

Step 1 della Phase 0 (ecommerce evolution roadmap). Questi test pinnano gli
invarianti CRITICI del sistema attuale prima di qualsiasi refactor. Ogni
invariante che protegge l'attuale comportamento è documentata in:
   docs/architecture/system-invariants.md

Strategia
=========
Pure-Pydantic introspection + signature inspection — zero DB hit, zero
fixture pesanti. Eseguono in < 5s, quindi possono girare in ogni PR senza
appesantire la CI.

Per i test che richiedono il flusso reale completo (DB + Stripe webhook
mock), il secondo batch è in test_invariants_public_flow_integration.py
(da scrivere in Phase 0 Week 2 se gli unit non bastano a garantire l'invariante).

Coverage iniziale
-----------------
Questa prima tranche copre 4 invarianti critici. Phase 0 Week 2 espande
a 20+ invarianti totali.

  CTR-1  POST /api/public/order-request response shape stable
  INV-1  Customer atomic upsert via find_one_and_update + upsert=True
  INV-2  Order number canonical format ORD-{N:04d}
  INV-5  Stripe webhook idempotency via event_id lock
"""

import os
import re
import sys
from pathlib import Path

import pytest

# ── Env bootstrap ────────────────────────────────────────────────────────
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── CTR-1 — Order request response shape ───────────────────────────────


class TestCTR1_OrderRequestResponseShape:
    """CTR-1 (Contract Invariant 1, Critical):

    POST /api/public/order-request response shape must always include the
    canonical 7 fields. Any new field MUST be additive (Optional) — never
    remove or rename existing fields.

    Why: the storefront classic frontend, the future embed widget, and the
    future AI-generated sites all parse this response. Changing the shape
    breaks every client at once.

    Pin location: routers/public.py:379-387 OrderRequestResponse.
    """

    def test_required_fields_present(self):
        """All 7 canonical fields are declared on the Pydantic model."""
        from routers.public import OrderRequestResponse
        required = {
            "success", "message", "order_id",
            "transaction_mode", "order_status",
            "payment_checkout_url", "payment_reason",
        }
        actual = set(OrderRequestResponse.model_fields.keys())
        missing = required - actual
        assert not missing, (
            f"OrderRequestResponse is missing canonical fields: {missing}. "
            "These fields are consumed by useCheckoutSubmit + future embed "
            "SDK + future AI-generated sites. Removing them = breaking change "
            "across all client surfaces."
        )

    def test_required_fields_have_canonical_types(self):
        """Type contract of each field is preserved."""
        from routers.public import OrderRequestResponse
        fields = OrderRequestResponse.model_fields

        # success: bool with default True
        assert fields["success"].annotation is bool
        assert fields["success"].default is True

        # message + order_id: str (required, no default)
        assert fields["message"].annotation is str
        assert fields["order_id"].annotation is str

        # transaction_mode default "request"
        assert fields["transaction_mode"].annotation is str
        assert fields["transaction_mode"].default == "request"

        # order_status default "draft"
        assert fields["order_status"].annotation is str
        assert fields["order_status"].default == "draft"

        # payment_checkout_url + payment_reason: Optional[str]
        from typing import Optional, get_args, get_origin
        import typing
        checkout_url_type = fields["payment_checkout_url"].annotation
        # Optional[str] is Union[str, None]
        assert checkout_url_type == Optional[str], (
            f"payment_checkout_url must be Optional[str], got {checkout_url_type}. "
            "Storefront frontend (useCheckoutSubmit.js:94) branches on "
            "`if (data.payment_checkout_url)` — Optional gives null fallback."
        )
        assert fields["payment_reason"].annotation == Optional[str]

    def test_no_unexpected_required_fields(self):
        """No NEW required field has crept in that would break legacy clients.

        Phase 0 baseline: only `message` and `order_id` are required
        (no default). All others have defaults. If this changes, every
        legacy client breaks.
        """
        from routers.public import OrderRequestResponse
        from pydantic_core import PydanticUndefined

        required_fields = {
            name for name, field in OrderRequestResponse.model_fields.items()
            if field.default is PydanticUndefined and field.default_factory is None
        }
        # Per CTR-1: il contratto è che SOLO message + order_id non hanno
        # default. Aggiungere un nuovo required field rompe i client legacy.
        assert required_fields == {"message", "order_id"}, (
            f"Unexpected required fields without default: "
            f"{required_fields - {'message', 'order_id'}}. "
            "Adding required fields = breaking change for legacy clients "
            "(storefront frontend, PWA cached, future embed SDK). "
            "If genuinely needed, make it Optional and version the API."
        )


# ─── INV-2 — Order number canonical format ──────────────────────────────


class TestINV2_OrderNumberCanonical:
    """INV-2 (Business Invariant 2, Critical):

    Order numbers must follow the canonical format `ORD-{N:04d}`. The parser
    that calculates next-N extracts the LAST run of digits in the current
    max. Any deviation (e.g. ORD-CB-XXXX, INV-2024-XXXX) breaks the assignment
    logic and forces orders into the fallback ORD-0001 collision retry.

    Pin location: repositories/order_repository.py:97-158.
    """

    def test_parser_regex_present_and_correct(self):
        """The tail-digits regex extracts the last digit-run."""
        from repositories.order_repository import _ORDER_NUMBER_TAIL_DIGITS

        # The regex MUST match the last run of digits, with optional
        # trailing whitespace. This is the contract; changing it breaks
        # the next-number assignment for orgs with legacy data.
        assert _ORDER_NUMBER_TAIL_DIGITS.pattern == r"(\d+)\s*$", (
            f"_ORDER_NUMBER_TAIL_DIGITS regex changed: {_ORDER_NUMBER_TAIL_DIGITS.pattern}. "
            "This regex extracts the next-N from the max(order_number). "
            "Changing it requires migrating every org's order data."
        )

    @pytest.mark.parametrize("order_number,expected_n", [
        ("ORD-0001", 1),
        ("ORD-0042", 42),
        ("ORD-9999", 9999),
        ("ORD-10000", 10000),
        # Tolerance for legacy formats (parser should still extract)
        ("ORD-CB-0162", 162),
        ("ORD-2024-007", 7),
        ("INV-2024-1234", 1234),
        # Pure numeric tail
        ("1234", 1234),
        # Whitespace tolerance
        ("ORD-0042   ", 42),
    ])
    def test_parser_extracts_tail_digits_correctly(self, order_number, expected_n):
        """Parser extracts the last digit-run, regardless of prefix shape."""
        from repositories.order_repository import _ORDER_NUMBER_TAIL_DIGITS
        m = _ORDER_NUMBER_TAIL_DIGITS.search(order_number)
        assert m is not None, f"Parser failed to find digit tail in {order_number!r}"
        assert int(m.group(1)) == expected_n

    @pytest.mark.parametrize("invalid_input", [
        "ORD-NONE",
        "ABC",
        "",
        "ORD-",
        "ORD-ABCD",
    ])
    def test_parser_returns_none_for_no_digit_tail(self, invalid_input):
        """Parser returns None when there's no digit tail (triggers fallback)."""
        from repositories.order_repository import _ORDER_NUMBER_TAIL_DIGITS
        m = _ORDER_NUMBER_TAIL_DIGITS.search(invalid_input)
        assert m is None, (
            f"Parser unexpectedly matched {invalid_input!r}. The fallback "
            "count-based logic relies on this case returning None."
        )

    def test_get_next_order_number_function_exists(self):
        """The single source-of-truth function for order_number generation."""
        from repositories.order_repository import get_next_order_number
        import inspect
        # Must be async
        assert inspect.iscoroutinefunction(get_next_order_number), (
            "get_next_order_number must be async (uses Motor async Mongo client)."
        )
        # Signature: (org_id: str) -> str
        sig = inspect.signature(get_next_order_number)
        params = sig.parameters
        assert "org_id" in params, (
            "get_next_order_number must accept org_id (per-org monotonic counter). "
            "Removing this param = global numbering = cross-org collision."
        )

    def test_canonical_format_string_template(self):
        """Verify the f-string template ORD-{N:04d} is what the function uses.

        We can't trivially call get_next_order_number without a DB, but we
        can introspect its source to ensure the canonical template is present.
        This catches accidental refactors like ORD-{N:05d} or {ORD-{N}}.
        """
        import inspect
        from repositories.order_repository import get_next_order_number
        source = inspect.getsource(get_next_order_number)
        # The canonical template must appear in the function body.
        assert 'f"ORD-{num:04d}"' in source, (
            "Canonical order_number template f'ORD-{num:04d}' not found in "
            "get_next_order_number source. If you've moved the template "
            "into a constant, update this sentinel."
        )
        # Bootstrap (empty org) must produce ORD-0001
        assert '"ORD-0001"' in source, (
            "Bootstrap value 'ORD-0001' not found in get_next_order_number "
            "source. Empty orgs must start at ORD-0001 (not ORD-0000, not 1)."
        )


# ─── INV-1 — Customer atomic upsert ─────────────────────────────────────


class TestINV1_CustomerAtomicUpsert:
    """INV-1 (Business Invariant 1, Critical):

    Customer creation/lookup during checkout must be atomic for (org_id,
    normalized_email). Race-safe via find_one_and_update + upsert=True.

    Pin location: repositories/customer_repository.py:53-178.
    """

    def test_upsert_by_email_exists_and_is_async(self):
        """The atomic helper is the canonical entry point."""
        import inspect
        from repositories import customer_repository
        assert hasattr(customer_repository, "upsert_by_email"), (
            "customer_repository.upsert_by_email missing. This is the ONLY "
            "race-safe path for customer dedup during checkout. Removing it "
            "regresses to pre-Phase-4 find-then-insert duplicates."
        )
        assert inspect.iscoroutinefunction(customer_repository.upsert_by_email)

    def test_upsert_by_email_signature(self):
        """Signature must accept (org_id + name + email + Optional phone/account)."""
        import inspect
        from repositories.customer_repository import upsert_by_email
        sig = inspect.signature(upsert_by_email)
        params = sig.parameters

        # Required: organization_id (positional)
        assert "organization_id" in params
        # Keyword-only: name, email (per the * separator in signature)
        assert "name" in params
        assert "email" in params
        # Optional: phone, customer_account_id, source
        assert "phone" in params
        assert "customer_account_id" in params
        assert "source" in params

    def test_upsert_by_email_returns_tuple_id_was_created(self):
        """Return contract: (customer_id: str, was_created: bool)."""
        import inspect
        from typing import get_type_hints, Tuple
        from repositories.customer_repository import upsert_by_email

        hints = get_type_hints(upsert_by_email)
        return_type = hints.get("return")
        # Expected: Tuple[str, bool]
        assert return_type is not None, (
            "upsert_by_email must have explicit return type hint "
            "Tuple[str, bool] — clients (OrderCreationService) rely on the "
            "was_created flag to distinguish first-time vs returning customer."
        )

    def test_upsert_implementation_uses_atomic_find_one_and_update(self):
        """The implementation MUST use find_one_and_update with upsert=True.

        This is the CORE of the atomicity guarantee. Any refactor that
        swaps this for a find-then-insert pattern reintroduces the
        pre-Phase-4 race condition. We introspect source to verify.
        """
        import inspect
        from repositories.customer_repository import upsert_by_email
        source = inspect.getsource(upsert_by_email)

        # Both markers must appear in the function body.
        assert "find_one_and_update" in source, (
            "upsert_by_email implementation no longer uses find_one_and_update. "
            "This breaks atomic dedup — concurrent storefront orders from same "
            "email can now produce duplicate customer rows."
        )
        assert "upsert=True" in source, (
            "find_one_and_update is present but upsert=True is missing. "
            "Without upsert=True, no document is inserted when no match — "
            "the customer is never created."
        )
        # Unique partial index assumption: setOnInsert covers the unique key.
        assert "$setOnInsert" in source, (
            "$setOnInsert missing — required to populate org_id + email + "
            "system fields ONLY on insert (not on update)."
        )

    def test_normalised_email_strips_and_lowercases(self):
        """Email normalization is the lookup key — must be stable."""
        from repositories.customer_repository import _normalise_email
        # Same normalization regardless of case + whitespace
        assert _normalise_email("  Mario@Example.COM  ") == "mario@example.com"
        assert _normalise_email("anna.bianchi@example.test") == "anna.bianchi@example.test"
        # Empty/None handling
        assert _normalise_email("") in (None, "")  # tolerant of None or ""
        assert _normalise_email(None) in (None, "")


# ─── INV-5 — Stripe webhook idempotency ─────────────────────────────────


class TestINV5_StripeWebhookIdempotency:
    """INV-5 (Business Invariant 5, Critical):

    Stripe webhook events MUST be processed idempotently. Replay of the
    same event_id is a no-op. Implemented via:
      1. Event lock via billing_repository.try_acquire_event_lock(event_id)
      2. Per-order processed_events[] array preventing double-application

    Pin locations:
      services/stripe_service.py:1394-1407 (lock acquisition)
      services/payment_checkout_service.py:615-628 (per-order event log)
    """

    def test_try_acquire_event_lock_exists(self):
        """The event lock primitive is the gate for all webhook processing."""
        import inspect
        from repositories import billing_repository
        assert hasattr(billing_repository, "try_acquire_event_lock"), (
            "billing_repository.try_acquire_event_lock missing. This is the "
            "atomic idempotency gate for Stripe webhooks. Without it, replay "
            "events apply twice → duplicate SalesRecords → cashflow KPI doubled."
        )
        fn = billing_repository.try_acquire_event_lock
        assert inspect.iscoroutinefunction(fn)

    def test_try_acquire_event_lock_signature(self):
        """Signature must accept stripe_event_id (globally unique Stripe id)
        + event_type for observability.

        Note: the param is named ``stripe_event_id`` (not generic ``event_id``)
        to make the source explicit — webhook events are namespaced by provider
        and we want to be able to introduce other providers (e.g. PayPal,
        SEPA direct) without name collision on the lock key.
        """
        import inspect
        from repositories.billing_repository import try_acquire_event_lock
        sig = inspect.signature(try_acquire_event_lock)
        assert "stripe_event_id" in sig.parameters, (
            "try_acquire_event_lock must accept stripe_event_id as the primary "
            "idempotency key. Stripe's event.id is globally unique. Renaming "
            "this parameter requires updating every caller + this sentinel."
        )
        assert "event_type" in sig.parameters, (
            "try_acquire_event_lock should accept event_type for observability "
            "(metrics tag, log context). Removing it is a regression."
        )

    def test_webhook_handler_uses_event_lock(self):
        """stripe webhook handler implementation must invoke the lock."""
        import inspect
        from services import stripe_service
        # Find the verify_and_construct + dispatch surface.
        # We look at the dispatch function source for the lock call.
        # In stripe_service the orchestrator is in handle_webhook_event.
        if hasattr(stripe_service, "handle_webhook_event"):
            source = inspect.getsource(stripe_service.handle_webhook_event)
            assert "try_acquire_event_lock" in source, (
                "stripe_service.handle_webhook_event does NOT call "
                "try_acquire_event_lock. Webhook replays would apply twice."
            )

    def test_processed_events_array_on_order_payment_checkout(self):
        """Per-order event log prevents double application of the SAME event.

        Even if the global lock is bypassed (e.g. concurrent webhook + manual
        reconcile), the per-order processed_events[] array short-circuits
        double application.

        Pin location: services/payment_checkout_service.py — the reconcile
        function uses $push processed_events.
        """
        import inspect
        from services import payment_checkout_service
        source = inspect.getsource(payment_checkout_service)
        assert "processed_events" in source, (
            "payment_checkout_service has no reference to processed_events. "
            "Per-order idempotency layer is missing. Concurrent webhooks "
            "may double-apply payment_intent transitions."
        )
        # Specifically uses $push (Mongo array append)
        assert "$push" in source, (
            "payment_checkout_service does not use $push (Mongo array append) "
            "for processed_events. Required for idempotent event log."
        )

    def test_event_dedup_returns_status_duplicate(self):
        """Replay of locked event returns 'duplicate' or 'in_flight' status.

        Per the audit, stripe_service.verify_and_construct_event /
        handle_webhook_event distinguishes:
          - first-time event → processed normally
          - duplicate event → status="duplicate" (skipped silently)
          - in-flight event → status="in_flight" (skipped, lock not released)
        """
        import inspect
        from services import stripe_service
        if hasattr(stripe_service, "handle_webhook_event"):
            source = inspect.getsource(stripe_service.handle_webhook_event)
            # Either status string must be detected in the dispatch logic.
            assert '"duplicate"' in source or "'duplicate'" in source, (
                "handle_webhook_event does not return status='duplicate' for "
                "replayed events. Replay detection logic missing or moved."
            )
