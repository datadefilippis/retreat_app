#!/usr/bin/env python3
"""
seed_test_orgs.py — Idempotent seeder for billing test scenarios.

Creates 4 deterministic test organizations + 1 admin user each. Each org
is configured with a specific `billing_status` to cover all the flows
in BILLING_V58_NEW_PLANS_TESTING_RUNBOOK.md without polluting production-
like data:

    org_test_active     — active paid sub (Commerce Starter)        — locale=it
    org_test_trialing   — in trial, 3 days remaining                 — locale=en
    org_test_past_due   — payment failed, current_period_end past    — locale=de
    org_test_canceled   — sub canceled, fell back to free            — locale=fr

The 4 distinct locales let you test multi-language quota emails without
changing settings between scenarios (Section D of the runbook).

WHY THIS EXISTS:
    Without deterministic test orgs, every developer/QA testing the
    billing flow has to manually craft Mongo state. That leads to
    diverging local datasets and "works on my machine" bugs in the
    runbook scenarios. This script is the single source of truth for
    "billing test fixtures."

USAGE:
    # Preview what would be created (dry-run, default):
    ./venv/bin/python scripts/seed_test_orgs.py

    # Actually create the orgs (idempotent — re-run safely):
    ./venv/bin/python scripts/seed_test_orgs.py --execute

    # Reset to clean state (delete + recreate):
    ./venv/bin/python scripts/seed_test_orgs.py --reset

WHAT IS PRESERVED:
    * Real user accounts and organizations (production-like data) are
      never touched. The script only operates on orgs whose `id` starts
      with "org_test_".
    * Pricing plan + commercial plan seeds (those are managed by
      seed_pricing.py and seed_commercial_plans.py at startup).

WHAT IS DELETED ON --reset:
    * All 4 test orgs and their admin users
    * Their AddonSubscription / ModuleSubscription records (if any)
    * Their AI usage events of the current month
    * Their Stripe customer/subscription IDs are NOT touched here —
      use Stripe CLI / Dashboard test mode to clean Stripe-side
      separately. Mongo-side reset is sufficient for most scenarios.

INVARIANTS:
    * Every test org has its admin user logged in as
      `admin@<orgslug>.example.com` with password "Test1234!" (constant).
    * Every test org has `id == slug` for trivial mongo lookups.
    * The script never grants real Stripe customer IDs — those must
      come from a real Stripe Checkout flow when running test mode
      scenarios. The seeder only sets the *expected* `billing_status`
      and metadata; the Stripe IDs are populated by the actual flow.

SAFE TO RUN: idempotent. Re-running on already-seeded state is a no-op
unless --reset is passed.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# Resolve backend root so database.py / models / repositories can be imported.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


# ── Test fixture spec ────────────────────────────────────────────────────────
#
# Single source of truth for the 4 test orgs. To add/modify test scenarios,
# edit this list — NOT the script logic.

TEST_ORGS_SPEC = [
    {
        "id": "org_test_active",
        "name": "Test Org — Active Sub",
        "billing_status": "active",
        "commercial_plan_slug": "core",          # Commerce Starter (post Onda 5)
        "trial_ends_at_offset_days": None,       # never trialing now
        "current_period_end_offset_days": 30,    # renews in 30 days
        "cancel_at_period_end": False,
        "admin_locale": "it",
        "stripe_customer_id": None,              # populated by real flow
        "stripe_subscription_id": None,
    },
    {
        "id": "org_test_trialing",
        "name": "Test Org — Trialing",
        "billing_status": "trialing",
        "commercial_plan_slug": "core",
        "trial_ends_at_offset_days": 3,          # trial expires in 3 days
        "current_period_end_offset_days": 3,     # same as trial
        "cancel_at_period_end": False,
        "admin_locale": "en",
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
    },
    {
        "id": "org_test_past_due",
        "name": "Test Org — Past Due",
        "billing_status": "past_due",
        "commercial_plan_slug": "pro",           # Commerce Pro
        "trial_ends_at_offset_days": None,
        "current_period_end_offset_days": -2,    # period ended 2 days ago
        "cancel_at_period_end": False,
        "admin_locale": "de",
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
    },
    {
        "id": "org_test_canceled",
        "name": "Test Org — Canceled (fell to Free)",
        "billing_status": "canceled",
        "commercial_plan_slug": "free",          # downgraded to Free
        "trial_ends_at_offset_days": None,
        "current_period_end_offset_days": None,
        "cancel_at_period_end": False,
        "admin_locale": "fr",
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
    },
]


# ── Logging helpers ──────────────────────────────────────────────────────────

def _info(msg: str) -> None:
    print(f"  → {msg}")


def _ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠ {msg}")


def _fail(msg: str) -> None:
    print(f"  ✗ {msg}")


# ── Core seeding logic ───────────────────────────────────────────────────────

def _resolve_offset(offset_days: Optional[int]) -> Optional[str]:
    """Convert a day offset (positive = future, negative = past) to ISO string,
    or return None if offset is None.

    Used for `trial_ends_at` and `current_period_end` so the seeder produces
    realistic timestamps relative to *now* (not hardcoded dates that go stale).
    """
    if offset_days is None:
        return None
    return (datetime.now(timezone.utc) + timedelta(days=offset_days)).isoformat()


async def _create_or_update_org(org_spec: dict, dry_run: bool) -> str:
    """Upsert one test org from its spec. Returns 'created' / 'updated' / 'skipped'.

    Strict idempotency: if all fields already match the spec, no DB write.
    """
    from database import organizations_collection
    from models.common import utc_now

    org_id = org_spec["id"]
    existing = await organizations_collection.find_one({"id": org_id}, {"_id": 0})

    target_doc = {
        "id": org_id,
        "name": org_spec["name"],
        "billing_status": org_spec["billing_status"],
        "commercial_plan_slug": org_spec["commercial_plan_slug"],
        "trial_ends_at": _resolve_offset(org_spec["trial_ends_at_offset_days"]),
        "current_period_end": _resolve_offset(org_spec["current_period_end_offset_days"]),
        "cancel_at_period_end": org_spec["cancel_at_period_end"],
        "stripe_customer_id": org_spec["stripe_customer_id"],
        "stripe_subscription_id": org_spec["stripe_subscription_id"],
        # Defaults that real org provisioning would set:
        "billing_email": f"admin@{org_id.replace('_', '-')}.example.com",
        "is_active": True,
        "plan": "free",  # legacy field, kept for back-compat
        "plan_assigned_by": "test_seed",
        "billing_interval": "month" if org_spec["billing_status"] in ("active", "trialing", "past_due") else None,
        "legacy_pricing_lock": False,
        "legacy_pricing_locked_at": None,
        "legacy_price_ids": None,
        "schema_version": 1,
    }

    if existing:
        # Compare ONLY the fields we manage. Other fields (e.g. created_at) preserved.
        diff_keys = [k for k in target_doc if existing.get(k) != target_doc[k]]
        if not diff_keys:
            _ok(f"org {org_id}: already up to date")
            return "skipped"

        _info(f"org {org_id}: would update fields: {diff_keys}")
        if dry_run:
            return "updated"

        await organizations_collection.update_one(
            {"id": org_id},
            {"$set": {**{k: target_doc[k] for k in diff_keys}, "updated_at": utc_now().isoformat()}},
        )
        _ok(f"org {org_id}: updated {len(diff_keys)} fields")
        return "updated"

    # Create new
    target_doc["created_at"] = utc_now().isoformat()
    target_doc["updated_at"] = utc_now().isoformat()
    if dry_run:
        _info(f"org {org_id}: would CREATE")
        return "created"

    await organizations_collection.insert_one(target_doc)
    _ok(f"org {org_id}: created")
    return "created"


async def _create_or_update_admin_user(org_spec: dict, dry_run: bool) -> str:
    """Upsert the admin user for a test org. Email + password are deterministic."""
    from database import users_collection
    from models.common import generate_id, utc_now
    from auth import get_password_hash

    org_id = org_spec["id"]
    email = f"admin@{org_id.replace('_', '-')}.example.com"
    existing = await users_collection.find_one({"email": email}, {"_id": 0})

    target = {
        "email": email,
        "name": f"Admin — {org_spec['name']}",
        "role": "admin",
        "organization_id": org_id,
        "is_active": True,
        "email_verified": True,        # skip verification for fixtures
        "locale": org_spec["admin_locale"],
    }

    if existing:
        diff_keys = [k for k in target if existing.get(k) != target[k]]
        if not diff_keys:
            _ok(f"user {email}: already up to date")
            return "skipped"
        if dry_run:
            _info(f"user {email}: would update fields: {diff_keys}")
            return "updated"
        await users_collection.update_one(
            {"email": email},
            {"$set": {**{k: target[k] for k in diff_keys}, "updated_at": utc_now().isoformat()}},
        )
        _ok(f"user {email}: updated {len(diff_keys)} fields")
        return "updated"

    target["id"] = generate_id()
    target["password_hash"] = get_password_hash("Test1234!")
    target["created_at"] = utc_now().isoformat()
    target["updated_at"] = utc_now().isoformat()
    if dry_run:
        _info(f"user {email}: would CREATE (password Test1234!)")
        return "created"

    await users_collection.insert_one(target)
    _ok(f"user {email}: created (password Test1234!)")
    return "created"


async def _delete_test_orgs(dry_run: bool) -> None:
    """Hard-delete test orgs + admin users + scoped data.

    Only touches resources whose org_id starts with `org_test_`.
    """
    from database import (
        organizations_collection,
        users_collection,
    )
    # Collections scoped by org_id that we want to clean for test orgs.
    # Subset of reset_org_data's full list — only collections relevant to
    # billing scenarios. Add more here if a future test scenario uses them.
    SCOPED = [
        "module_subscriptions",
        "addon_subscriptions",     # post Onda 3
        "ai_usage_events",
        "email_usage_events",      # post Onda 6
        "billing_events",
        "org_quota_notices",       # post Onda 6
        "audit_logs",
    ]

    for spec in TEST_ORGS_SPEC:
        org_id = spec["id"]
        email = f"admin@{org_id.replace('_', '-')}.example.com"

        if dry_run:
            _info(f"would delete org {org_id} + user {email} + scoped data")
            continue

        # Org-scoped data
        from database import db
        for coll_name in SCOPED:
            try:
                coll = db[coll_name]
                result = await coll.delete_many({"organization_id": org_id})
                if result.deleted_count > 0:
                    _info(f"  · {coll_name}: deleted {result.deleted_count}")
            except Exception as exc:
                _warn(f"  · {coll_name}: {exc}")

        # Org + user
        u_res = await users_collection.delete_one({"email": email})
        o_res = await organizations_collection.delete_one({"id": org_id})
        _ok(f"removed org {org_id} (mongo deleted: org={o_res.deleted_count}, user={u_res.deleted_count})")


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Idempotent seeder for billing test orgs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply changes (default: dry-run).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all test orgs first, then re-seed. Implies --execute.",
    )
    args = parser.parse_args()

    dry_run = not (args.execute or args.reset)

    print("=" * 70)
    print("AFianco — seed_test_orgs.py")
    if dry_run:
        print("MODE: DRY-RUN (use --execute to apply, --reset to wipe and reseed)")
    elif args.reset:
        print("MODE: RESET (delete + recreate)")
    else:
        print("MODE: EXECUTE (idempotent upsert)")
    print("=" * 70)

    counters = {"created": 0, "updated": 0, "skipped": 0, "deleted": 0}

    if args.reset:
        print("\n[1/2] Deleting existing test orgs…")
        await _delete_test_orgs(dry_run=False)

    print("\n[1/2] Seeding orgs…")
    for spec in TEST_ORGS_SPEC:
        result = await _create_or_update_org(spec, dry_run=dry_run)
        counters[result] = counters.get(result, 0) + 1

    print("\n[2/2] Seeding admin users…")
    for spec in TEST_ORGS_SPEC:
        result = await _create_or_update_admin_user(spec, dry_run=dry_run)
        counters[result] = counters.get(result, 0) + 1

    print("\n" + "=" * 70)
    print("Summary:")
    for key, val in counters.items():
        if val > 0:
            print(f"  {key}: {val}")
    print("=" * 70)

    if dry_run:
        print("\nNOTE: This was a dry-run. Use --execute to apply.\n")
    else:
        print("\nDone. Test logins:")
        for spec in TEST_ORGS_SPEC:
            email = f"admin@{spec['id'].replace('_', '-')}.example.com"
            print(f"  · {email} / Test1234! ({spec['admin_locale']}) → {spec['billing_status']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
