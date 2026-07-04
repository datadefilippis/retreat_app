#!/usr/bin/env python3
"""
simulate_quota_exhausted.py
============================
Test helper: artificially push an org's `cashflow_monitor.data_rows`
counter just above its plan limit so the gate fires on the next insert.

Useful for end-to-end testing of:
  - QuotaExceededPaywall modal (frontend)
  - "save button disabled" pre-emptive UI gate (Onda 9.Y.0.2 D)
  - 429 QUOTA_EXCEEDED axios interceptor flow

Reversible: writes synthetic ai_usage_events with feature="data_rows"
and metadata.simulated=True so they can be cleaned up after the test:

    python -m scripts.simulate_quota_exhausted --email X --cleanup

Usage:

    cd backend

    # Push to limit (default: limit + 5 events)
    python -m scripts.simulate_quota_exhausted --email X@Y.z

    # Push to a custom usage value
    python -m scripts.simulate_quota_exhausted --email X --target 250

    # Remove the simulated events
    python -m scripts.simulate_quota_exhausted --email X --cleanup
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def _resolve_org_id(email: str) -> str:
    from database import users_collection, organizations_collection
    user = await users_collection.find_one({"email": email.lower().strip()})
    if not user or not user.get("organization_id"):
        print(f"ERROR: user email={email} has no organization", file=sys.stderr)
        sys.exit(2)
    org = await organizations_collection.find_one({"id": user["organization_id"]})
    print(f"Org: {org.get('name')!r} (id={org['id']})")
    return org["id"]


async def _current_authoritative_count(org_id: str) -> int:
    from services.module_access import (
        _count_data_rows_authoritative,
        get_current_period_range,
    )
    period_start, period_end = get_current_period_range()
    return await _count_data_rows_authoritative(org_id, period_start, period_end)


async def _push_to_target(org_id: str, target: int) -> int:
    """Insert synthetic ai_usage_events to reach `target` total."""
    from database import db
    import uuid

    current = await _current_authoritative_count(org_id)
    print(f"Current authoritative count: {current}")
    if current >= target:
        print(f"Already at/above target {target} — nothing to do.")
        return 0

    needed = target - current
    print(f"Inserting {needed} synthetic data_rows events to reach {target}...")
    docs = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for _ in range(needed):
        docs.append({
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "module_key": "cashflow_monitor",
            "feature": "data_rows",
            "quantity": 1,
            "created_at": now_iso,
            "metadata": {"simulated": True, "purpose": "quota_test"},
        })
    if docs:
        await db["ai_usage_events"].insert_many(docs)

    new_count = await _current_authoritative_count(org_id)
    print(f"New authoritative count: {new_count} / target {target}")
    return needed


async def _cleanup(org_id: str) -> int:
    from database import db
    res = await db["ai_usage_events"].delete_many({
        "organization_id": org_id,
        "metadata.simulated": True,
    })
    print(f"Removed {res.deleted_count} simulated events.")
    new_count = await _current_authoritative_count(org_id)
    print(f"New authoritative count: {new_count}")
    return res.deleted_count


async def _run(args) -> int:
    org_id = await _resolve_org_id(args.email)

    if args.cleanup:
        await _cleanup(org_id)
        return 0

    # Default target: just over 200 (the Free plan limit) so the next
    # insert will be rejected with 429 QUOTA_EXCEEDED.
    target = args.target if args.target is not None else 205
    await _push_to_target(org_id, target)

    print()
    print("✅ Done. Now in the UI:")
    print("   1. Hard refresh the browser (Ctrl+Shift+R / Cmd+Shift+R)")
    print("   2. Open any cashflow tab (Sales, Expenses, Purchases, Fixed Costs)")
    print("   3. Save button should be DISABLED with a Lock icon")
    print("   4. Try to bypass via DevTools — backend returns 429 + paywall")
    print()
    print("To remove the simulated events:")
    print(f"   python -m scripts.simulate_quota_exhausted --email {args.email} --cleanup")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--email", required=True, help="User email belonging to target org")
    parser.add_argument("--target", type=int, help="Target authoritative usage value (default 205)")
    parser.add_argument("--cleanup", action="store_true", help="Remove all simulated events for this org")
    args = parser.parse_args()
    rc = asyncio.run(_run(args))
    sys.exit(rc)


if __name__ == "__main__":
    main()
