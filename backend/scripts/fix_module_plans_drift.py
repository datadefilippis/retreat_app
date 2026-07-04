#!/usr/bin/env python3
"""
fix_module_plans_drift.py — Align stale `module_plans` mappings on the main
commercial plans to match the seed file (single source of truth).

Why this script exists:

    `upsert_commercial_plan` uses ADDITIVE MERGE for `module_plans`: only
    new module keys are added, existing assignments are NEVER overwritten.
    This protects admin overrides — but it also means if seed_commercial_plans.py
    later changes a tier assignment (e.g. Solo: product_catalog_starter →
    product_catalog_free), the DB rows keep the old assignment forever.

    Result: a plan card on /plans may claim "50 prodotti" (per the seed)
    while the backend actually enforces "200 prodotti" (per the stale DB).
    Users get MORE than advertised (safe direction) but the card is lying.

    This script bypasses the additive-merge protection one-time, by doing
    direct $set on `module_plans` for the 5 main plans. After this runs,
    the additive-merge protection is unchanged for future seed runs.

USAGE:

    # Dry-run (default — shows diffs, no write):
    python backend/scripts/fix_module_plans_drift.py

    # Apply:
    python backend/scripts/fix_module_plans_drift.py --execute

WHAT IT DOES NOT DO:

    · Never deletes anything
    · Never touches add-on plans (is_addon=True)
    · Never touches pricing tiers themselves (just the assignment)
    · Never makes Stripe API calls
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument("--execute", action="store_true", help="Apply (default: dry-run).")
    args = parser.parse_args()
    dry_run = not args.execute

    print("=" * 70)
    print("fix_module_plans_drift.py")
    print(f"MODE: {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print(f"DB:   {os.environ.get('DB_NAME', 'test_database')}")
    print("=" * 70)
    print()

    from database import commercial_plans_collection
    from services.seed_commercial_plans import COMMERCIAL_PLANS

    counters = {"updated": 0, "unchanged": 0, "missing": 0}

    for seed in COMMERCIAL_PLANS:
        slug = seed["slug"]
        seed_mp = seed.get("module_plans", {})

        existing = await commercial_plans_collection.find_one(
            {"slug": slug, "is_addon": {"$ne": True}},
            {"_id": 0, "slug": 1, "name": 1, "module_plans": 1},
        )
        if not existing:
            print(f"  \u26A0 {slug}: not in DB")
            counters["missing"] += 1
            continue

        db_mp = existing.get("module_plans") or {}
        all_keys = sorted(set(db_mp.keys()) | set(seed_mp.keys()))
        diffs = [(k, db_mp.get(k), seed_mp.get(k)) for k in all_keys if db_mp.get(k) != seed_mp.get(k)]

        if not diffs:
            counters["unchanged"] += 1
            print(f"  \u2713 {slug:12} ({existing.get('name')}): no drift")
            continue

        print(f"  \u2192 {slug:12} ({existing.get('name')}):")
        for k, db_v, seed_v in diffs:
            print(f"      {k}: {db_v}  \u2192  {seed_v}")

        if not dry_run:
            await commercial_plans_collection.update_one(
                {"slug": slug},
                {"$set": {"module_plans": seed_mp}},
            )
        counters["updated"] += 1

    print(f"\n  Summary: updated={counters['updated']}  "
          f"unchanged={counters['unchanged']}  missing={counters['missing']}")

    if dry_run:
        print("\nNOTE: dry-run only. Re-run with --execute to apply.\n")
    else:
        print("\nDone. The card limits on /plans now reflect the real backend enforcement.\n")
        print("WARNING: any test org currently exceeding the new (lower) limits")
        print("will see quota errors on next request. For prod, do a per-org")
        print("audit first.\n")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
