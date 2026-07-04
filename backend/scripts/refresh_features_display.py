#!/usr/bin/env python3
"""
refresh_features_display.py — Force-overwrite the `features_display` field on
each main commercial plan so that what users see on /plans matches the
canonical list in seed_commercial_plans.py.

Why this script exists:

    `upsert_commercial_plan` treats `features_display` as ADMIN_EDITABLE_FIELDS
    and only writes it on FIRST insert (via $setOnInsert). On subsequent seed
    runs, even if the seed file's features_display is updated (e.g. to add
    `commerce_200_orders`, `stripe_connect`, etc.), the DB rows remain stale
    showing the OLD list — leaving users to see undersized feature lists
    that hide the strongest selling points.

    This script bypasses that protection one-time, by doing a direct $set on
    the features_display field for the 5 main plans (free/starter/core/pro/
    enterprise). Add-on plans are not touched.

    After this runs, future seed runs will continue to leave features_display
    intact (the protection is unchanged) — the catalog admin can still edit
    via the admin UI without losing changes.

USAGE:

    # Dry-run (default — shows diffs, no write):
    python backend/scripts/refresh_features_display.py

    # Apply:
    python backend/scripts/refresh_features_display.py --execute

WHAT IT DOES NOT DO:

    · Never deletes anything
    · Never touches add-on plans (is_addon=True)
    · Never touches Stripe ID fields, prices, trial_days, name, tagline
    · Never makes Stripe API calls — only MongoDB writes
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Resolve backend root so database / models / services can be imported
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


def _ok(msg: str) -> None: print(f"  \u2713 {msg}")
def _info(msg: str) -> None: print(f"  \u2192 {msg}")
def _warn(msg: str) -> None: print(f"  \u26A0 {msg}")
def _diff(label: str, before: list, after: list) -> None:
    """Show added / removed feature keys."""
    before_set = set(before or [])
    after_set = set(after or [])
    added = after_set - before_set
    removed = before_set - after_set
    if not added and not removed and before == after:
        print(f"     {label}: identical (no change)")
        return
    if added:
        for f in sorted(added):
            print(f"     + {f}")
    if removed:
        for f in sorted(removed):
            print(f"     - {f}")


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Force-refresh features_display on the 5 main commercial plans.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--execute", action="store_true", help="Apply changes (default: dry-run).")
    args = parser.parse_args()
    dry_run = not args.execute

    print("=" * 70)
    print("refresh_features_display.py")
    print(f"MODE: {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print(f"DB:   {os.environ.get('DB_NAME', 'test_database')}")
    print("=" * 70)

    from database import commercial_plans_collection
    from services.seed_commercial_plans import COMMERCIAL_PLANS

    print(f"\n[1/2] Reading seed catalog ({len(COMMERCIAL_PLANS)} main plans)...\n")

    counters = {"updated": 0, "unchanged": 0, "missing": 0}

    for seed_plan in COMMERCIAL_PLANS:
        slug = seed_plan["slug"]
        new_features = seed_plan.get("features_display", [])

        existing = await commercial_plans_collection.find_one(
            {"slug": slug},
            {"_id": 0, "slug": 1, "name": 1, "features_display": 1, "is_addon": 1},
        )
        if not existing:
            _warn(f"{slug}: no row in commercial_plans (run seed first)")
            counters["missing"] += 1
            continue
        if existing.get("is_addon"):
            _warn(f"{slug}: row exists but is_addon=True (skipping)")
            continue

        old_features = existing.get("features_display") or []

        print(f"  --- {slug:12} ({existing.get('name')}) ---")
        _diff("features_display", old_features, new_features)

        if old_features == new_features:
            counters["unchanged"] += 1
            continue

        if not dry_run:
            await commercial_plans_collection.update_one(
                {"slug": slug},
                {"$set": {"features_display": new_features}},
            )
        counters["updated"] += 1

    print(f"\n  Summary: updated={counters['updated']}  "
          f"unchanged={counters['unchanged']}  missing={counters['missing']}")

    print("\n[2/2] Final state of features_display per plan:\n")
    cursor = commercial_plans_collection.find(
        {"is_addon": {"$ne": True}},
        {"_id": 0, "slug": 1, "name": 1, "features_display": 1},
    )
    rows = []
    async for r in cursor:
        rows.append(r)
    rows.sort(key=lambda r: ["free", "starter", "core", "pro", "enterprise"].index(r["slug"])
              if r["slug"] in ["free", "starter", "core", "pro", "enterprise"] else 99)

    for r in rows:
        print(f"  {r['slug']:12} ({r['name']})")
        for f in r.get("features_display", []):
            print(f"      \u2022 {f}")
        print()

    if dry_run:
        print("NOTE: dry-run only. Re-run with --execute to apply.\n")
    else:
        print("Done. Refresh /plans (Cmd+Shift+R) to see the updated feature lists.\n")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
