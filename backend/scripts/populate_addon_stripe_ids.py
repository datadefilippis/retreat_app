#!/usr/bin/env python3
"""
populate_addon_stripe_ids.py — Idempotent setter for Stripe Product/Price IDs
on the 4 add-on CommercialPlan rows (v5.8 / Onda 3).

After creating the 4 add-on Products + Prices in Stripe Dashboard (test mode
or live mode), run this script to wire the IDs into the local MongoDB.
Re-running with the same IDs is a no-op.

USAGE:

    # Dry-run (default — shows what would be set, no write):
    python backend/scripts/populate_addon_stripe_ids.py

    # Apply the test-mode IDs hardcoded below:
    python backend/scripts/populate_addon_stripe_ids.py --execute

    # Override one or more IDs from CLI (useful for live mode):
    python backend/scripts/populate_addon_stripe_ids.py --execute \
        --ai-chat-pack-product prod_LIVE1 --ai-chat-pack-price price_LIVE1 \
        --ai-chat-pro-product  prod_LIVE2 --ai-chat-pro-price  price_LIVE2 \
        --orders-pack-product  prod_LIVE3 --orders-pack-price  price_LIVE3 \
        --extra-store-product  prod_LIVE4 --extra-store-price  price_LIVE4

WHAT IT DOES:

    1. Ensures the 4 add-on CommercialPlan rows exist (calls seed_commercial_plans)
    2. Sets stripe_product_id + stripe_price_id_monthly on each
    3. Verifies all 4 are populated and prints a summary

WHAT IT DOES NOT DO:

    · Never deletes anything
    · Never touches non-addon plans (free / starter / core / pro / enterprise)
    · Never makes Stripe API calls — only MongoDB writes
    · Never reads or writes secrets (no Stripe key needed)
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


# ── Default test-mode IDs (override from CLI for live mode) ──────────────────
# These are the IDs the user provided after creating Products in Stripe
# Dashboard test mode. Same script can be reused for live mode by passing
# --execute with the live IDs as CLI args.

DEFAULT_TEST_IDS = {
    "addon_ai_chat_pack": {
        "stripe_product_id": "prod_UQfY9RLdLUQ5J5",
        "stripe_price_id_monthly": "price_1TRoDWEwMqAIoAcCKNSGo2e7",
    },
    "addon_ai_chat_pro": {
        "stripe_product_id": "prod_UQfZaPjs6FTwYN",
        "stripe_price_id_monthly": "price_1TRoECEwMqAIoAcCkPHTFNo2",
    },
    "addon_orders_pack": {
        "stripe_product_id": "prod_UQfaAFpM0i1Eam",
        "stripe_price_id_monthly": "price_1TRoF0EwMqAIoAcCPQIQ6AMk",
    },
    "addon_extra_store": {
        "stripe_product_id": "prod_UQfacdnfbFyXBU",
        "stripe_price_id_monthly": "price_1TRoFdEwMqAIoAcCFkgJGgNb",
    },
}


def _ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def _info(msg: str) -> None:
    print(f"  → {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠ {msg}")


def _fail(msg: str) -> None:
    print(f"  ✗ {msg}")


async def _ensure_addons_seeded() -> int:
    """Make sure the 4 add-on CommercialPlan rows exist. Returns count present."""
    from database import commercial_plans_collection
    from services.seed_commercial_plans import seed_commercial_plans

    # Always run seed (idempotent upsert) so any missing add-on is materialised.
    await seed_commercial_plans()

    count = await commercial_plans_collection.count_documents({"is_addon": True})
    return count


async def _apply_ids(
    target_ids: dict, dry_run: bool,
) -> dict:
    """Update each add-on row with the given Stripe IDs.

    Returns counters {modified, already_set, missing_row}.
    """
    from database import commercial_plans_collection

    counters = {"modified": 0, "already_set": 0, "missing_row": 0}

    for slug, ids in target_ids.items():
        existing = await commercial_plans_collection.find_one(
            {"slug": slug},
            {"_id": 0, "stripe_product_id": 1, "stripe_price_id_monthly": 1, "is_addon": 1},
        )
        if not existing:
            _warn(f"{slug}: no row in commercial_plans (seed didn't run?)")
            counters["missing_row"] += 1
            continue
        if not existing.get("is_addon"):
            _warn(f"{slug}: row exists but is_addon=False (corrupted seed?)")
            counters["missing_row"] += 1
            continue

        cur_prod = existing.get("stripe_product_id")
        cur_price = existing.get("stripe_price_id_monthly")
        new_prod = ids["stripe_product_id"]
        new_price = ids["stripe_price_id_monthly"]

        if cur_prod == new_prod and cur_price == new_price:
            _ok(f"{slug}: IDs already correct (no change)")
            counters["already_set"] += 1
            continue

        if dry_run:
            _info(f"{slug}: WOULD set product={new_prod} price={new_price}")
            counters["modified"] += 1
            continue

        await commercial_plans_collection.update_one(
            {"slug": slug},
            {"$set": {
                "stripe_product_id": new_prod,
                "stripe_price_id_monthly": new_price,
            }},
        )
        _ok(f"{slug}: product={new_prod} price={new_price}")
        counters["modified"] += 1

    return counters


async def _print_final_state() -> None:
    from database import commercial_plans_collection

    print()
    print("Final state of all add-on plans:")
    print()
    cursor = commercial_plans_collection.find(
        {"is_addon": True},
        {"_id": 0, "slug": 1, "name": 1, "price_monthly": 1,
         "stripe_product_id": 1, "stripe_price_id_monthly": 1,
         "max_quantity": 1, "compatible_plans": 1},
    ).sort([("sort_order", 1)])

    rows = []
    async for doc in cursor:
        rows.append(doc)

    if not rows:
        _fail("No add-on rows in DB. Did seed_commercial_plans run?")
        return

    for row in rows:
        prod_ok = bool(row.get("stripe_product_id"))
        price_ok = bool(row.get("stripe_price_id_monthly"))
        marker = "✓" if (prod_ok and price_ok) else "✗"
        print(f"  {marker} {row['slug']:25} {row.get('name', ''):20} €{row.get('price_monthly', 0)}/mo")
        print(f"     product : {row.get('stripe_product_id') or '(missing)'}")
        print(f"     price   : {row.get('stripe_price_id_monthly') or '(missing)'}")
        print(f"     stack   : up to {row.get('max_quantity', 1)}× · compatible with: {row.get('compatible_plans') or 'any paid plan'}")
        print()


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Populate Stripe Product/Price IDs on add-on CommercialPlan rows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--execute", action="store_true", help="Apply changes (default: dry-run).")
    parser.add_argument("--ai-chat-pack-product", default=DEFAULT_TEST_IDS["addon_ai_chat_pack"]["stripe_product_id"])
    parser.add_argument("--ai-chat-pack-price", default=DEFAULT_TEST_IDS["addon_ai_chat_pack"]["stripe_price_id_monthly"])
    parser.add_argument("--ai-chat-pro-product", default=DEFAULT_TEST_IDS["addon_ai_chat_pro"]["stripe_product_id"])
    parser.add_argument("--ai-chat-pro-price", default=DEFAULT_TEST_IDS["addon_ai_chat_pro"]["stripe_price_id_monthly"])
    parser.add_argument("--orders-pack-product", default=DEFAULT_TEST_IDS["addon_orders_pack"]["stripe_product_id"])
    parser.add_argument("--orders-pack-price", default=DEFAULT_TEST_IDS["addon_orders_pack"]["stripe_price_id_monthly"])
    parser.add_argument("--extra-store-product", default=DEFAULT_TEST_IDS["addon_extra_store"]["stripe_product_id"])
    parser.add_argument("--extra-store-price", default=DEFAULT_TEST_IDS["addon_extra_store"]["stripe_price_id_monthly"])
    args = parser.parse_args()

    target_ids = {
        "addon_ai_chat_pack": {
            "stripe_product_id": args.ai_chat_pack_product,
            "stripe_price_id_monthly": args.ai_chat_pack_price,
        },
        "addon_ai_chat_pro": {
            "stripe_product_id": args.ai_chat_pro_product,
            "stripe_price_id_monthly": args.ai_chat_pro_price,
        },
        "addon_orders_pack": {
            "stripe_product_id": args.orders_pack_product,
            "stripe_price_id_monthly": args.orders_pack_price,
        },
        "addon_extra_store": {
            "stripe_product_id": args.extra_store_product,
            "stripe_price_id_monthly": args.extra_store_price,
        },
    }

    dry_run = not args.execute

    print("=" * 70)
    print("populate_addon_stripe_ids.py")
    print(f"MODE: {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print(f"DB:   {os.environ.get('DB_NAME', 'test_database')}")
    print("=" * 70)

    print("\n[1/3] Seeding add-on CommercialPlan rows (idempotent)…")
    addons_count = await _ensure_addons_seeded()
    if addons_count >= 4:
        _ok(f"{addons_count} add-on rows present in DB")
    else:
        _warn(f"only {addons_count}/4 add-on rows found — seed_commercial_plans may have been skipped")

    print("\n[2/3] Applying Stripe IDs…")
    counters = await _apply_ids(target_ids, dry_run=dry_run)
    print(f"\n  Summary: modified={counters['modified']}  "
          f"already_set={counters['already_set']}  "
          f"missing_row={counters['missing_row']}")

    print("\n[3/3] Verifying final state…")
    await _print_final_state()

    if dry_run:
        print("\nNOTE: dry-run only. Re-run with --execute to apply.\n")
    else:
        if counters["missing_row"] > 0:
            _fail("Some rows are missing — restart the backend so seed_commercial_plans() runs, then retry.")
            return 1
        all_ok = all(  # all 4 should be set
            bool(target_ids[s]["stripe_product_id"]) and bool(target_ids[s]["stripe_price_id_monthly"])
            for s in target_ids
        )
        if all_ok:
            print("✅ All 4 add-on plans are wired to Stripe IDs. You can now buy add-ons.")
        else:
            _fail("Some IDs were empty in the input — review the CLI args.")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
