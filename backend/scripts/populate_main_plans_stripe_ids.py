#!/usr/bin/env python3
"""
populate_main_plans_stripe_ids.py — Idempotent setter for Stripe Product/Price
IDs on the 3 main self-serve CommercialPlan rows (Solo / Commerce Starter /
Commerce Pro).

This is the companion of `populate_addon_stripe_ids.py` for the main bundle
plans. It does NOT touch:
  · `free` (no Stripe price needed — fallback plan)
  · `enterprise` / Custom (manual admin-only flow, no Stripe checkout)
  · the 4 add-on plans (use populate_addon_stripe_ids.py for those)

USAGE:

    # Dry-run (default — shows what would be set, no write):
    python backend/scripts/populate_main_plans_stripe_ids.py \\
        --solo-product            prod_xxx \\
        --solo-price-monthly      price_xxx \\
        --commerce-starter-product       prod_yyy \\
        --commerce-starter-price-monthly price_yyy \\
        --commerce-pro-product           prod_zzz \\
        --commerce-pro-price-monthly     price_zzz

    # Apply:
    python backend/scripts/populate_main_plans_stripe_ids.py --execute \\
        --solo-product prod_xxx --solo-price-monthly price_xxx \\
        --commerce-starter-product prod_yyy --commerce-starter-price-monthly price_yyy \\
        --commerce-pro-product prod_zzz --commerce-pro-price-monthly price_zzz

    # Optionally also set yearly prices (skip if you only have monthly in Stripe):
    python backend/scripts/populate_main_plans_stripe_ids.py --execute \\
        --solo-product prod_xxx --solo-price-monthly price_xxx --solo-price-yearly price_xxx_y \\
        ...etc

WHAT IT DOES:

    1. Loads the 3 main plan rows from MongoDB (slug=starter|core|pro).
    2. Sets stripe_product_id + stripe_price_id_monthly (and yearly if given).
    3. Verifies all 3 are populated, prints a summary.

WHAT IT DOES NOT DO:

    · Never deletes anything
    · Never touches Free / Enterprise / Add-on plans
    · Never makes Stripe API calls — only MongoDB writes
    · Never reads or writes secrets (no Stripe key needed)
    · Never overwrites a value that's already correct (idempotent)

SLUG MAPPING (DB slug → public name):

    starter → "Solo"
    core    → "Commerce Starter"
    pro     → "Commerce Pro"
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


# ── Slug ↔ CLI arg mapping ───────────────────────────────────────────────────
# DB slugs are the LEGACY keys (starter/core/pro) — public names changed but
# slugs stayed for Stripe webhook backward compatibility.

PLAN_SPECS = [
    # (db_slug, display_name, prod_arg, monthly_arg, yearly_arg, trial_arg)
    ("starter", "Solo",             "solo_product",             "solo_price_monthly",             "solo_price_yearly",             "solo_trial_days"),
    ("core",    "Commerce Starter", "commerce_starter_product", "commerce_starter_price_monthly", "commerce_starter_price_yearly", "commerce_starter_trial_days"),
    ("pro",     "Commerce Pro",     "commerce_pro_product",     "commerce_pro_price_monthly",     "commerce_pro_price_yearly",     "commerce_pro_trial_days"),
]


def _ok(msg: str) -> None: print(f"  \u2713 {msg}")
def _info(msg: str) -> None: print(f"  \u2192 {msg}")
def _warn(msg: str) -> None: print(f"  \u26A0 {msg}")
def _fail(msg: str) -> None: print(f"  \u2717 {msg}")


async def _apply_ids(target_ids: dict, dry_run: bool) -> dict:
    """Update each main plan row with the given Stripe IDs.

    target_ids shape:
      { "starter": {"stripe_product_id": "...", "stripe_price_id_monthly": "...",
                    "stripe_price_id_yearly": "..." or None}, ... }

    Returns counters {modified, already_set, missing_row, skipped_no_input}.
    """
    from database import commercial_plans_collection

    counters = {"modified": 0, "already_set": 0, "missing_row": 0, "skipped_no_input": 0}

    for slug, ids in target_ids.items():
        new_prod = ids.get("stripe_product_id")
        new_price_m = ids.get("stripe_price_id_monthly")
        new_price_y = ids.get("stripe_price_id_yearly")
        new_trial = ids.get("trial_days")

        # If user didn't pass any IDs OR trial-days for this slug, skip cleanly.
        if not new_prod and not new_price_m and not new_price_y and new_trial is None:
            _info(f"{slug}: no IDs/trial-days provided on CLI \u2014 skipping")
            counters["skipped_no_input"] += 1
            continue

        existing = await commercial_plans_collection.find_one(
            {"slug": slug},
            {"_id": 0, "stripe_product_id": 1,
             "stripe_price_id_monthly": 1, "stripe_price_id_yearly": 1,
             "trial_days": 1,
             "is_addon": 1, "is_self_serve": 1, "name": 1},
        )
        if not existing:
            _warn(f"{slug}: no row in commercial_plans (run seed_commercial_plans first)")
            counters["missing_row"] += 1
            continue
        if existing.get("is_addon"):
            _warn(f"{slug}: row exists but is_addon=True \u2014 wrong script (use populate_addon_stripe_ids.py)")
            counters["missing_row"] += 1
            continue

        # Build the $set patch only for fields that changed
        patch = {}
        if new_prod and new_prod != existing.get("stripe_product_id"):
            patch["stripe_product_id"] = new_prod
        if new_price_m and new_price_m != existing.get("stripe_price_id_monthly"):
            patch["stripe_price_id_monthly"] = new_price_m
        if new_price_y and new_price_y != existing.get("stripe_price_id_yearly"):
            patch["stripe_price_id_yearly"] = new_price_y
        if new_trial is not None and int(new_trial) != int(existing.get("trial_days") or 0):
            patch["trial_days"] = int(new_trial)

        if not patch:
            _ok(f"{slug} ({existing.get('name')}): IDs already correct (no change)")
            counters["already_set"] += 1
            continue

        if dry_run:
            _info(f"{slug} ({existing.get('name')}): WOULD set {patch}")
            counters["modified"] += 1
            continue

        await commercial_plans_collection.update_one({"slug": slug}, {"$set": patch})
        _ok(f"{slug} ({existing.get('name')}): set {list(patch.keys())}")
        counters["modified"] += 1

    return counters


async def _print_final_state() -> None:
    from database import commercial_plans_collection

    print()
    print("Final state of main self-serve plans:")
    print()
    cursor = commercial_plans_collection.find(
        {"slug": {"$in": ["starter", "core", "pro"]}},
        {"_id": 0, "slug": 1, "name": 1, "price_monthly": 1, "price_yearly": 1,
         "stripe_product_id": 1, "stripe_price_id_monthly": 1, "stripe_price_id_yearly": 1,
         "trial_days": 1, "is_self_serve": 1},
    ).sort([("sort_order", 1)])

    rows = []
    async for doc in cursor:
        rows.append(doc)
    rows.sort(key=lambda r: ["starter", "core", "pro"].index(r["slug"]))

    if not rows:
        _fail("No main plan rows in DB. Did seed_commercial_plans run?")
        return

    for row in rows:
        prod_ok = bool(row.get("stripe_product_id"))
        price_ok = bool(row.get("stripe_price_id_monthly"))
        marker = "\u2713" if (prod_ok and price_ok) else "\u2717"
        print(f"  {marker} {row['slug']:8} ({row.get('name', ''):20})  "
              f"\u20AC{row.get('price_monthly', 0)}/mo \u00B7 trial {row.get('trial_days', 0)}d")
        print(f"     product : {row.get('stripe_product_id') or '(missing)'}")
        print(f"     monthly : {row.get('stripe_price_id_monthly') or '(missing)'}")
        print(f"     yearly  : {row.get('stripe_price_id_yearly') or '(not set)'}")
        print()


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Populate Stripe Product/Price IDs on the 3 main self-serve plan rows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--execute", action="store_true", help="Apply changes (default: dry-run).")

    for db_slug, display, prod_arg, m_arg, y_arg, t_arg in PLAN_SPECS:
        parser.add_argument(f"--{prod_arg.replace('_', '-')}",
                            default=None, dest=prod_arg,
                            help=f"Stripe Product ID for {display} (slug={db_slug})")
        parser.add_argument(f"--{m_arg.replace('_', '-')}",
                            default=None, dest=m_arg,
                            help=f"Stripe MONTHLY Price ID for {display}")
        parser.add_argument(f"--{y_arg.replace('_', '-')}",
                            default=None, dest=y_arg,
                            help=f"Stripe YEARLY Price ID for {display} (optional)")
        parser.add_argument(f"--{t_arg.replace('_', '-')}",
                            default=None, dest=t_arg, type=int,
                            help=f"Override trial_days for {display} (optional, e.g. 14)")

    args = parser.parse_args()

    target_ids = {}
    for db_slug, _, prod_arg, m_arg, y_arg, t_arg in PLAN_SPECS:
        target_ids[db_slug] = {
            "stripe_product_id": getattr(args, prod_arg),
            "stripe_price_id_monthly": getattr(args, m_arg),
            "stripe_price_id_yearly": getattr(args, y_arg),
            "trial_days": getattr(args, t_arg),
        }

    dry_run = not args.execute

    print("=" * 70)
    print("populate_main_plans_stripe_ids.py")
    print(f"MODE: {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print(f"DB:   {os.environ.get('DB_NAME', 'test_database')}")
    print("=" * 70)

    print("\n[1/2] Applying Stripe IDs to main plans...")
    counters = await _apply_ids(target_ids, dry_run=dry_run)
    print(f"\n  Summary: modified={counters['modified']}  "
          f"already_set={counters['already_set']}  "
          f"missing_row={counters['missing_row']}  "
          f"skipped_no_input={counters['skipped_no_input']}")

    print("\n[2/2] Verifying final state...")
    await _print_final_state()

    if dry_run:
        print("\nNOTE: dry-run only. Re-run with --execute to apply.\n")
    else:
        if counters["missing_row"] > 0:
            _fail("Some rows missing \u2014 restart the backend so seed_commercial_plans runs, then retry.")
            return 1
        print("\nDone. If all 3 main plans show monthly Price IDs above, /plans Subscribe will work.")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
