#!/usr/bin/env python3
"""
backfill_cost_at_sale.py
========================
Wave 1 — Performance Prodotti fix (2026-05-20).

Companion to ``migrate_cost_price_to_components.py``. While the migration
script populated ``Product.cost_source`` from legacy ``cost_price``,
THIS script populates the per-sale snapshot
``SalesRecord.cost_at_sale`` for records that pre-date the fix.

Why:
  The Performance Prodotti page reads ``$sum cost_at_sale`` on
  ``sales_records`` to compute period-filtered margin. Until the
  ``order_service`` fix, the field was never written → every
  historical SalesRecord has ``cost_at_sale = None`` and margins
  for the past show up as "N/D". This script back-resolves the cost
  per record so historical margins reflect the merchant's current
  ``cost_source`` configuration.

What this script does:
  1. Iterate every SalesRecord with ``product_id != None``
     AND ``cost_at_sale IS NULL``.
  2. For each org, batch-resolve ``unit_cost`` via the CostResolver
     against the product's current ``cost_source``.
  3. ``$set cost_at_sale = unit_cost * sign(amount)`` so storni stay
     negative and forward records stay positive — the convention
     ``order_service`` adopted post-fix.
  4. Idempotent: records that already have ``cost_at_sale`` set are
     skipped.

Edge cases:
  - Product no longer exists (deleted)         → cost_at_sale stays None
  - Product has no ``cost_source`` configured  → cost_at_sale stays None
  - Resolver returns ``ResolverResult.value=None`` → cost_at_sale stays None

Usage (dry-run is the default — pass --apply to actually update):
  $ python -m scripts.backfill_cost_at_sale                    # dry run
  $ python -m scripts.backfill_cost_at_sale --apply            # commit
  $ python -m scripts.backfill_cost_at_sale --org-id <id>      # one org
  $ python -m scripts.backfill_cost_at_sale --batch-size 500   # tune

Run in production AFTER deploying the order_service fix so the going-
forward path doesn't add more rows to backfill.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional

# Make backend importable when run as a script.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("backfill_cost_at_sale")


async def _backfill_org(
    org_id: str,
    *,
    apply: bool,
    batch_size: int,
) -> dict:
    """Backfill cost_at_sale for all eligible sales_records in one org.

    Returns a stats dict for the caller to aggregate.
    """
    from database import sales_records_collection, products_collection
    from services.cost_resolver import CostResolver

    stats = {
        "org_id": org_id,
        "candidates": 0,
        "updated": 0,
        "skipped_no_product": 0,
        "skipped_no_cost_source": 0,
        "skipped_resolver_none": 0,
        "errors": 0,
    }

    # 1. Find every record needing a backfill in this org. We project only
    # the fields we need so a 100k-record org doesn't OOM the script.
    query = {
        "organization_id": org_id,
        "product_id": {"$ne": None, "$exists": True},
        "$or": [
            {"cost_at_sale": None},
            {"cost_at_sale": {"$exists": False}},
        ],
    }
    cursor = sales_records_collection.find(
        query, {"_id": 0, "id": 1, "product_id": 1, "amount": 1},
    )
    records = await cursor.to_list(length=None)  # full sweep per org
    stats["candidates"] = len(records)
    if not records:
        return stats

    # 2. Resolve unit_cost for every distinct product_id, in one batch.
    distinct_pids = sorted({r["product_id"] for r in records if r.get("product_id")})
    prod_cursor = products_collection.find(
        {"organization_id": org_id, "id": {"$in": distinct_pids}},
        {"_id": 0, "id": 1, "cost_source": 1, "cost_price": 1,
         "category": 1, "item_type": 1},
    )
    products = await prod_cursor.to_list(length=len(distinct_pids))
    products_by_id = {p["id"]: p for p in products}

    resolver = CostResolver(org_id=org_id)
    eligible_products = [
        p for p in products if (p.get("cost_source") or p.get("cost_price"))
    ]
    if not eligible_products:
        stats["skipped_no_cost_source"] = len(records)
        return stats

    resolver_results = await resolver.resolve_many(eligible_products)
    unit_cost_map: Dict[str, float] = {}
    for pid, result in resolver_results.items():
        if result and result.value is not None:
            unit_cost_map[pid] = float(result.value)

    # 3. Walk records, build the per-record $set ops. We don't use
    # update_many because each record needs a different cost_at_sale
    # (sign follows amount: positive forward, negative storno).
    bulk_ops: List[dict] = []
    for r in records:
        rid = r.get("id")
        pid = r.get("product_id")
        amount = r.get("amount") or 0
        if not rid:
            stats["errors"] += 1
            continue
        if pid not in products_by_id:
            stats["skipped_no_product"] += 1
            continue
        if pid not in unit_cost_map:
            stats["skipped_resolver_none"] += 1
            continue
        unit_cost = unit_cost_map[pid]
        # Sign follows amount: storni have negative amount and need
        # negative cost_at_sale so the period aggregate nets to zero.
        sign = -1 if amount < 0 else 1
        cost_at_sale = round(sign * unit_cost, 4)
        bulk_ops.append({
            "filter": {"id": rid, "organization_id": org_id},
            "update": {"$set": {"cost_at_sale": cost_at_sale}},
        })

    if not bulk_ops:
        return stats

    # 4. Execute (or dry-run report).
    if not apply:
        logger.info(
            "[DRY-RUN] org=%s would update %d records (sample first 3: %s)",
            org_id, len(bulk_ops),
            [
                {"id": op["filter"]["id"], "cost_at_sale": op["update"]["$set"]["cost_at_sale"]}
                for op in bulk_ops[:3]
            ],
        )
        stats["updated"] = len(bulk_ops)
        return stats

    # Batched bulk update — 500 ops per round-trip by default keeps the
    # working set comfortably below MongoDB's 16MB cap.
    updated_total = 0
    for i in range(0, len(bulk_ops), batch_size):
        chunk = bulk_ops[i:i + batch_size]
        from pymongo import UpdateOne
        bulk = [UpdateOne(op["filter"], op["update"]) for op in chunk]
        try:
            result = await sales_records_collection.bulk_write(bulk, ordered=False)
            updated_total += result.modified_count
            logger.info(
                "org=%s chunk %d-%d: modified=%d",
                org_id, i, i + len(chunk), result.modified_count,
            )
        except Exception as exc:
            logger.error(
                "org=%s chunk %d-%d failed: %s", org_id, i, i + len(chunk), exc,
            )
            stats["errors"] += len(chunk)
    stats["updated"] = updated_total
    return stats


async def _list_org_ids() -> List[str]:
    """Return every org_id that has at least one sales_record with a
    product_id and missing cost_at_sale."""
    from database import sales_records_collection
    pipeline = [
        {
            "$match": {
                "product_id": {"$ne": None, "$exists": True},
                "$or": [
                    {"cost_at_sale": None},
                    {"cost_at_sale": {"$exists": False}},
                ],
            }
        },
        {"$group": {"_id": "$organization_id"}},
    ]
    docs = await sales_records_collection.aggregate(pipeline).to_list(length=None)
    return [d["_id"] for d in docs if d.get("_id")]


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write the updates (default is dry-run).",
    )
    parser.add_argument(
        "--org-id", default=None,
        help="Restrict the backfill to a single org. Default: all orgs.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=500,
        help="Bulk-write batch size (default 500).",
    )
    args = parser.parse_args()

    if args.org_id:
        org_ids = [args.org_id]
    else:
        org_ids = await _list_org_ids()

    logger.info(
        "backfill_cost_at_sale: %s mode, %d org(s) to process",
        "APPLY" if args.apply else "DRY-RUN", len(org_ids),
    )

    grand_total = {
        "orgs": 0, "candidates": 0, "updated": 0,
        "skipped_no_product": 0, "skipped_no_cost_source": 0,
        "skipped_resolver_none": 0, "errors": 0,
    }
    for org_id in org_ids:
        try:
            stats = await _backfill_org(
                org_id, apply=args.apply, batch_size=args.batch_size,
            )
        except Exception as exc:
            logger.error("org=%s crashed: %s", org_id, exc, exc_info=True)
            continue
        grand_total["orgs"] += 1
        for k in (
            "candidates", "updated", "skipped_no_product",
            "skipped_no_cost_source", "skipped_resolver_none", "errors",
        ):
            grand_total[k] += stats.get(k, 0)
        logger.info(
            "org=%s: candidates=%d updated=%d skipped(no_product/no_cost/no_resolver)=%d/%d/%d errors=%d",
            org_id, stats["candidates"], stats["updated"],
            stats["skipped_no_product"], stats["skipped_no_cost_source"],
            stats["skipped_resolver_none"], stats["errors"],
        )

    logger.info("──────────────────────────── SUMMARY ────────────────────────────")
    logger.info(
        "orgs=%d candidates=%d updated=%d skipped(no_product/no_cost/no_resolver)=%d/%d/%d errors=%d",
        grand_total["orgs"], grand_total["candidates"], grand_total["updated"],
        grand_total["skipped_no_product"], grand_total["skipped_no_cost_source"],
        grand_total["skipped_resolver_none"], grand_total["errors"],
    )
    if not args.apply:
        logger.info("(dry-run — re-run with --apply to commit the updates)")


if __name__ == "__main__":
    asyncio.run(main())
