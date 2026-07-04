"""
cleanup_orphan_stripe_subs.py
=============================
Onda 20 Layer 3 (manual sweep) — scan every AFianco org with a
stripe_customer_id and detect Stripe customers with ≥2 active|trialing
subscriptions. Cancels the orphans (those NOT matching the org's
stored stripe_subscription_id) to enforce the one-active-sub invariant.

Idempotent. Safe to run periodically.

Usage:
  cd backend && set -a; source .env; set +a
  ./venv/bin/python -m scripts.cleanup_orphan_stripe_subs --dry-run
  ./venv/bin/python -m scripts.cleanup_orphan_stripe_subs
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


def _setup_stripe():
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    return stripe


async def main(dry_run: bool) -> int:
    print(f"{'DRY-RUN' if dry_run else 'EXECUTE'} — Onda 20 orphan Stripe sub cleanup")
    print("=" * 78)

    from database import organizations_collection
    stripe = _setup_stripe()

    cursor = organizations_collection.find(
        {
            "stripe_customer_id": {"$nin": [None, ""]},
            "is_active": {"$ne": False},
        },
        {
            "_id": 0, "id": 1, "name": 1,
            "stripe_customer_id": 1, "stripe_subscription_id": 1,
            "commercial_plan_slug": 1, "billing_status": 1,
        },
    )
    orgs = await cursor.to_list(10000)
    print(f"\n  Inspecting {len(orgs)} orgs with stripe_customer_id\n")

    total_orphans = 0
    total_cancelled = 0
    affected_orgs = 0

    for org in orgs:
        cust_id = org["stripe_customer_id"]
        kept_sub_id = org.get("stripe_subscription_id")

        try:
            # Build aggregate of active+trialing
            active_data = stripe.Subscription.list(customer=cust_id, status="active", limit=20).data
            trialing_data = stripe.Subscription.list(customer=cust_id, status="trialing", limit=20).data
            all_active = list(active_data) + list(trialing_data)
        except Exception as e:
            print(f"  ✗ {org['name']:25s}  Stripe list failed: {e}")
            continue

        if len(all_active) <= 1:
            continue

        affected_orgs += 1
        # Determine orphans
        orphans = [s for s in all_active if s.id != kept_sub_id]
        total_orphans += len(orphans)
        print(f"  ⚠ {org['name']:25s}  {len(all_active)} active subs on Stripe "
              f"(DB keeps={kept_sub_id}, orphans={len(orphans)})")
        for s in orphans:
            print(f"      orphan: {s.id} status={s.status} cancel_at_period_end={s.cancel_at_period_end}")
            if dry_run:
                continue
            try:
                stripe.Subscription.cancel(s.id)
                total_cancelled += 1
                print(f"        ✓ cancelled")
            except Exception as e:
                print(f"        ✗ cancel failed: {e}")

    print()
    print("─" * 78)
    if total_orphans == 0:
        print("  ✓ No orphan subscriptions detected. Invariant holds across all orgs.")
    else:
        print(f"  Affected orgs:    {affected_orgs}")
        print(f"  Orphan subs found: {total_orphans}")
        if not dry_run:
            print(f"  Cancelled:        {total_cancelled}")
    print("─" * 78)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(dry_run=args.dry_run)))
