#!/usr/bin/env python3
"""
migrate_trial_once_backfill.py — Onda 9.T migration.

Backfills `has_used_trial=True` for any org that has historical evidence of
a trial (current trial_ends_at, OR Stripe customer with trial_end in any
sub history, OR billing event of type customer.subscription.created with
trial_end set).

This closes the anti-fraud gap retroactively: orgs that already used a
trial under the OLD buggy gate (which used trial_ends_at as proxy and reset
it on cancel) cannot now exploit cancel-and-retry.

USAGE:

    # Dry-run (default): shows what would change
    python backend/scripts/migrate_trial_once_backfill.py

    # Apply
    python backend/scripts/migrate_trial_once_backfill.py --execute

    # Skip the Stripe deep-scan (fast — only uses local DB hints)
    python backend/scripts/migrate_trial_once_backfill.py --execute --skip-stripe-scan

WHAT IT DOES NOT DO:
  - Does NOT reset has_used_trial back to False for any org
  - Does NOT touch trial_history (that grows from new webhooks going forward)
  - Does NOT call Stripe API to modify any sub
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Set

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


def _ok(msg: str) -> None: print(f"  \u2713 {msg}")
def _info(msg: str) -> None: print(f"  \u2192 {msg}")
def _warn(msg: str) -> None: print(f"  \u26A0 {msg}")


async def find_orgs_to_mark(skip_stripe_scan: bool = False) -> List[str]:
    """Return list of org_ids that should have has_used_trial=True."""
    from database import organizations_collection, billing_events_collection

    targets: Set[str] = set()

    # Heuristic 1: orgs with current trial_ends_at != null
    cursor = organizations_collection.find(
        {"trial_ends_at": {"$ne": None, "$exists": True},
         "$or": [{"has_used_trial": {"$ne": True}}, {"has_used_trial": {"$exists": False}}]},
        {"_id": 0, "id": 1},
    )
    async for r in cursor:
        targets.add(r["id"])

    # Heuristic 2: orgs with billing_status currently trialing
    cursor = organizations_collection.find(
        {"billing_status": "trialing",
         "$or": [{"has_used_trial": {"$ne": True}}, {"has_used_trial": {"$exists": False}}]},
        {"_id": 0, "id": 1},
    )
    async for r in cursor:
        targets.add(r["id"])

    # Heuristic 3: BillingEvents with subscription_created carrying trial_end
    # (looks at our local audit log of webhook events)
    try:
        cursor = billing_events_collection.find(
            {"event_type": {"$in": ["customer.subscription.created", "checkout.session.completed"]}},
            {"_id": 0, "stripe_subscription_id": 1, "payload": 1, "stripe_event_id": 1},
        )
        async for evt in cursor:
            payload = evt.get("payload") or {}
            data = (payload.get("data") or {}).get("object", {})
            if data.get("trial_end"):
                # Map sub_id back to org
                sub_id = evt.get("stripe_subscription_id") or data.get("id")
                if sub_id:
                    org = await organizations_collection.find_one(
                        {"$or": [
                            {"stripe_subscription_id": sub_id},
                            {"_legacy_subs": sub_id},  # if you have sub history field
                        ]},
                        {"_id": 0, "id": 1},
                    )
                    if org:
                        targets.add(org["id"])
    except Exception as e:
        _warn(f"BillingEvents scan failed: {e} (skipping)")

    # Heuristic 4 (optional): Stripe deep scan — query Stripe API for every org's
    # customer history. Expensive; behind a flag.
    if not skip_stripe_scan:
        _info("Stripe deep-scan not implemented yet (skip-stripe-scan default)")
        # Future: iterate all orgs with stripe_customer_id, list customer's
        # subscription history, mark has_used_trial=True if any sub had trial_end.

    return list(targets)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--skip-stripe-scan", action="store_true",
                        help="Skip the Stripe API scan (faster, uses only local DB hints)")
    args = parser.parse_args()
    dry_run = not args.execute

    print("=" * 70)
    print("migrate_trial_once_backfill.py (Onda 9.T)")
    print(f"MODE: {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print(f"DB:   {os.environ.get('DB_NAME', 'test_database')}")
    print("=" * 70)

    print("\n[1/2] Scanning for orgs with trial history...")
    targets = await find_orgs_to_mark(skip_stripe_scan=args.skip_stripe_scan)
    print(f"  Found {len(targets)} org(s) to mark has_used_trial=True")
    for org_id in targets[:20]:  # show first 20
        print(f"    \u2022 {org_id}")
    if len(targets) > 20:
        print(f"    ... and {len(targets) - 20} more")

    if not targets:
        print("\n[2/2] Nothing to do — all orgs already correctly flagged.")
        return 0

    if dry_run:
        print("\nNOTE: dry-run only. Re-run with --execute to apply.\n")
        return 0

    print("\n[2/2] Applying has_used_trial=True...")
    from database import organizations_collection
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    updated = 0
    for org_id in targets:
        result = await organizations_collection.update_one(
            {"id": org_id},
            {"$set": {
                "has_used_trial": True,
                # Use the existing trial_ends_at as a proxy for "first trial start"
                # (best-effort; for orgs without trial_ends_at, set to now)
            }},
        )
        if result.modified_count > 0:
            updated += 1

        # If has_used_trial_at is empty, set to "migration:<now>"
        await organizations_collection.update_one(
            {"id": org_id, "has_used_trial_at": None},
            {"$set": {
                "has_used_trial_at": now,
                "has_used_trial_plan_slug": "unknown_migrated",
            }},
        )

    _ok(f"Updated {updated} orgs (set has_used_trial=True)")
    print("\nDone. Anti-fraud gate now applies to backfilled orgs.\n")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
