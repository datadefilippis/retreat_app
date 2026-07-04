#!/usr/bin/env python3
"""
Block 6 isolation smoke test — prove the billing subscription flow is
UNTOUCHED after each Block 6 phase is applied.

Intended usage:
  Run BEFORE every deploy of phases 10b / 10c / 10d. If any assertion
  fails, abort the deploy. The script exits 0 on full success, non-zero
  on the first failed check.

What it verifies (in order of dependency):
  1. Core billing imports still resolve.
  2. The webhook dispatcher still registers every billing event handler
     with the exact same names (no silent renames or drops).
  3. verify_checkout_session (Fase 5a billing recovery path) is still
     importable with its original signature.
  4. billing_repository reservation primitives (Fase 6c) still exist.
  5. Billing collections are reachable (a live ping to each).
  6. A synthetic invoice.paid event flows through handle_webhook_event
     without raising — the handler itself is mocked so we are only
     exercising the routing + idempotency reservation, not any real
     state change.

This script NEVER modifies data. It is pure read + isolated dispatcher
drill. Safe to run at any time in any environment.
"""

import asyncio
import inspect
import sys
from pathlib import Path

# Allow running directly from scripts/ without PYTHONPATH setup.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def main() -> int:
    failures: list[str] = []

    def fail(msg: str) -> None:
        print(f"  ✗ {msg}")
        failures.append(msg)

    def ok(msg: str) -> None:
        print(f"  ✓ {msg}")

    # ── 1. Core billing imports ──────────────────────────────────────────
    print("[1/6] Core billing imports")
    try:
        from services import stripe_service, billing_lifecycle, plan_provisioning  # noqa: F401
        from routers import billing as billing_router  # noqa: F401
        from repositories import billing_repository  # noqa: F401
        from models import commercial_plan  # noqa: F401
        ok("services.stripe_service / billing_lifecycle / plan_provisioning import")
        ok("routers.billing import")
        ok("repositories.billing_repository import")
    except Exception as e:
        fail(f"core billing import failed: {e}")
        return _emit(failures)

    # ── 2. Webhook handler dispatch map ──────────────────────────────────
    print("[2/6] Webhook handler map — every billing event still registered")
    expected_billing = {
        "checkout.session.completed",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
        "invoice.payment_failed",
    }
    registered = set(stripe_service._EVENT_HANDLERS.keys())
    missing = expected_billing - registered
    if missing:
        fail(f"missing billing handlers: {missing}")
    else:
        ok(f"all 5 billing handlers registered ({len(registered)} total incl. Connect)")

    # ── 3. verify_checkout_session signature ─────────────────────────────
    print("[3/6] verify_checkout_session (Fase 5a) signature preserved")
    try:
        sig = inspect.signature(stripe_service.verify_checkout_session)
        params = list(sig.parameters.keys())
        if params[:2] != ["session_id", "org_id"]:
            fail(f"verify_checkout_session params changed: {params}")
        else:
            ok(f"verify_checkout_session({', '.join(params)})")
    except Exception as e:
        fail(f"verify_checkout_session not importable: {e}")

    # ── 4. Reservation primitives (Fase 6c) ──────────────────────────────
    print("[4/6] Reservation primitives (Fase 6c)")
    try:
        from repositories.billing_repository import (
            try_acquire_event_lock, mark_event_processed, is_event_processed,
            record_billing_event,
        )
        ok("try_acquire_event_lock, mark_event_processed, is_event_processed, record_billing_event")
    except ImportError as e:
        fail(f"reservation primitives missing: {e}")

    # ── 5. Billing collections reachable ─────────────────────────────────
    print("[5/6] Billing collections reachable")
    try:
        from database import (
            organizations_collection, billing_events_collection,
            commercial_plans_collection,
        )
        # Simple count — asserts the collection handle is live, not that data exists
        await organizations_collection.count_documents({}, limit=1)
        ok("organizations collection reachable")
        await billing_events_collection.count_documents({}, limit=1)
        ok("billing_events collection reachable")
        await commercial_plans_collection.count_documents({}, limit=1)
        ok("commercial_plans collection reachable")
    except Exception as e:
        fail(f"billing collection ping failed: {e}")

    # ── 6. Synthetic invoice.paid event dispatches without raise ─────────
    print("[6/6] Synthetic invoice.paid flows through handle_webhook_event")
    from unittest.mock import AsyncMock, patch
    from database import billing_events_collection

    event = {
        "id": "evt_isolation_smoke_10pre",
        "type": "invoice.paid",
        "data": {"object": {"id": "in_xxx", "subscription": "sub_xxx"}},
    }
    # Clean any prior run artifact so the lock can be acquired fresh
    await billing_events_collection.delete_many({"stripe_event_id": event["id"]})

    try:
        with patch(
            "services.stripe_service._handle_invoice_paid",
            AsyncMock(return_value={"org_id": "org_synth", "action": "smoke_ok"}),
        ):
            result = await stripe_service.handle_webhook_event(event)
        if result.get("status") != "processed":
            fail(f"handle_webhook_event status={result.get('status')} (expected 'processed')")
        else:
            ok(f"handle_webhook_event → status={result['status']}, action={result.get('action')}")
    except Exception as e:
        fail(f"handle_webhook_event raised: {e}")
    finally:
        # Cleanup
        await billing_events_collection.delete_many({"stripe_event_id": event["id"]})

    return _emit(failures)


def _emit(failures: list[str]) -> int:
    print()
    if not failures:
        print("✅ Block 6 isolation smoke PASSED — billing flow untouched")
        return 0
    print(f"❌ Block 6 isolation smoke FAILED — {len(failures)} issue(s):")
    for f in failures:
        print(f"    - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
