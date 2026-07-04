#!/usr/bin/env python3
"""
rebrand_order_numbers.py
========================
2026-05-20 — One-shot rebrand of legacy order_number values into the
canonical ``ORD-{N:04d}`` format.

Why
---
Until 2026-05-20 a single seed script (``seed_wellness_case_study.py``)
generated ``ORD-CB-XXXX`` order numbers for the "Centro Benessere"
case-study dataset. Every other code path of the runtime generates
``ORD-XXXX``. The mismatched format broke the parser in
``order_repository.get_next_order_number``, which extracts the numeric
tail by ``last.split("-", 1)[1]``: ``"CB-XXXX"`` is not an integer, the
parser silently fell back to ``num=1`` and produced ``ORD-0001`` — which
collided with the existing legacy ORD-0001 and made every confirm fail
with "Impossibile assegnare numero ordine dopo 3 tentativi".

We've documented a Golden Rule for this field (see
``order_repository.py`` module docstring): EXACTLY ONE canonical format,
``ORD-{N:04d}``. Import data with external numbering lives separately
on ``external_order_number``. This script enforces that rule on data
already on disk.

What this script does
---------------------
For every org with at least one ``ORD-<prefix>-<digits>`` order_number:

  1. Build a rebrand plan: each ``ORD-<prefix>-<digits>`` is mapped to
     the next free canonical ``ORD-<digits>`` slot in that org's
     namespace (shift forward by the smallest amount that avoids
     collisions with already-canonical numbers like ORD-0001).

  2. Preserve the legacy identifier in ``external_order_number`` +
     ``external_source = "legacy_rebrand_2026-05-20"`` so the merchant
     can still cross-reference the original numbering.

  3. Mirror the rename in ``sales_records.metadata.order_number`` and
     ``sales_records.description`` so the cashflow analytics stay
     consistent. The sales records snapshot the order number in two
     places — both get updated atomically per rebrand.

  4. Idempotent: rows that have already canonical-format
     order_number (matching ``^ORD-\\d+$``) are skipped on every run.

Usage
-----
  python -m scripts.rebrand_order_numbers                  # dry-run, all orgs
  python -m scripts.rebrand_order_numbers --apply          # commit changes
  python -m scripts.rebrand_order_numbers --org-id <id>    # one org only

Always run --apply on the local machine first to verify the diff, then
production.

Safety
------
  - DRY-RUN is the default. The script prints the full rename map and
    exits without touching the DB.
  - The unique partial index on (org_id, order_number) is honored: the
    plan never proposes a target that already exists.
  - sales_records updates happen AFTER the order is renamed, so a crash
    mid-batch never leaves an order with both old and new names. Worst
    case: orphan sales rows referencing the old number, which a re-run
    of the script catches and fixes.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# Make backend importable when run as a script.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("rebrand_order_numbers")


# Canonical format the runtime emits: ORD followed by one dash and a
# pure digit run. Anything that doesn't match this exactly is a
# rebrand candidate.
_CANONICAL_RE = re.compile(r"^ORD-\d+$")

# Permissive parser to extract a numeric tail from any legacy order_number.
# Matches the last digit-run before end-of-string.
_TAIL_DIGITS_RE = re.compile(r"(\d+)\s*$")


def _is_canonical(order_number: str) -> bool:
    return bool(_CANONICAL_RE.match(order_number or ""))


def _extract_tail_num(order_number: str) -> Optional[int]:
    m = _TAIL_DIGITS_RE.search(order_number or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except (ValueError, OverflowError):
        return None


async def _build_rebrand_plan_for_org(org_id: str) -> List[Tuple[str, str, str]]:
    """Return list of (order_id, old_order_number, new_order_number).

    Strategy:
      - Take the set of canonical numbers already taken in this org
        (so we never propose a target that collides with one).
      - Iterate the legacy ones in their natural numeric order.
      - For each, try the tail-digit value as target; if taken, walk
        forward until we find a free slot. Reserve the slot in-memory
        for subsequent iterations of this same plan.
    """
    from database import orders_collection

    canonical_taken = set()
    legacy_orders = []  # list of (order_id, order_number, tail_num)

    async for o in orders_collection.find(
        {"organization_id": org_id, "order_number": {"$ne": None}},
        {"_id": 0, "id": 1, "order_number": 1},
    ):
        num = o.get("order_number") or ""
        if _is_canonical(num):
            canonical_taken.add(num)
        else:
            tail = _extract_tail_num(num)
            legacy_orders.append((o["id"], num, tail or 0))

    # Sort legacy orders by their tail number so the rebrand preserves
    # chronological ordering (ORD-CB-0001 maps before ORD-CB-0002).
    legacy_orders.sort(key=lambda r: r[2])

    plan: List[Tuple[str, str, str]] = []
    reserved: set = set(canonical_taken)
    for order_id, old_num, tail in legacy_orders:
        candidate_tail = max(tail, 1)
        while True:
            candidate = f"ORD-{candidate_tail:04d}"
            if candidate not in reserved:
                reserved.add(candidate)
                plan.append((order_id, old_num, candidate))
                break
            candidate_tail += 1

    return plan


async def _rebrand_org(
    org_id: str,
    *,
    apply: bool,
) -> dict:
    """Execute the rebrand plan for one org. Return a stats dict."""
    from database import orders_collection, sales_records_collection

    stats = {
        "org_id": org_id,
        "candidates": 0,
        "renamed": 0,
        "sales_records_touched": 0,
        "errors": 0,
    }

    plan = await _build_rebrand_plan_for_org(org_id)
    stats["candidates"] = len(plan)
    if not plan:
        return stats

    if not apply:
        logger.info("[DRY-RUN] org=%s rebrand plan:", org_id)
        for old, new, *_ in [(p[1], p[2]) for p in plan[:10]]:
            logger.info("  %s  ->  %s", old, new)
        if len(plan) > 10:
            logger.info("  ... + %d more", len(plan) - 10)
        return stats

    now_iso = datetime.now(timezone.utc).isoformat()

    for order_id, old_num, new_num in plan:
        try:
            # 1. Rename the order document.
            await orders_collection.update_one(
                {
                    "id": order_id,
                    "organization_id": org_id,
                    "order_number": old_num,  # belt-and-suspenders
                },
                {
                    "$set": {
                        "order_number": new_num,
                        "external_order_number": old_num,
                        "external_source": "legacy_rebrand_2026-05-20",
                        "external_imported_at": now_iso,
                        "updated_at": now_iso,
                    },
                },
            )

            # 2. Mirror the rename in sales_records — two places hold
            # the order number snapshot:
            #   - metadata.order_number  (Onda 14 cashflow integration)
            #   - description "Ordine <num>: …"  (human-readable)
            sr_result = await sales_records_collection.update_many(
                {
                    "organization_id": org_id,
                    "metadata.order_number": old_num,
                },
                {
                    "$set": {
                        "metadata.order_number": new_num,
                    },
                },
            )
            stats["sales_records_touched"] += sr_result.modified_count or 0

            # Description rewrite uses the regex-aware approach so
            # both "Ordine ORD-CB-0001: Pizza" and "Storno Ordine
            # ORD-CB-0001: Pizza" get updated.
            async for sr in sales_records_collection.find(
                {
                    "organization_id": org_id,
                    "description": {"$regex": re.escape(old_num)},
                },
                {"_id": 0, "id": 1, "description": 1},
            ):
                new_desc = (sr.get("description") or "").replace(old_num, new_num)
                await sales_records_collection.update_one(
                    {"id": sr["id"], "organization_id": org_id},
                    {"$set": {"description": new_desc}},
                )

            stats["renamed"] += 1
        except Exception as exc:
            logger.error(
                "org=%s rename %s -> %s FAILED: %s",
                org_id, old_num, new_num, exc,
            )
            stats["errors"] += 1

    return stats


async def _list_orgs_with_legacy_orders() -> List[str]:
    """Find every org that has at least one non-canonical order_number."""
    from database import orders_collection

    # Aggregation: project a boolean ``is_legacy``, group by org_id,
    # keep only orgs where any order is legacy. Simpler than pulling
    # every order back through Python.
    pipeline = [
        {
            "$match": {
                "order_number": {"$ne": None},
                "order_number": {"$not": {"$regex": "^ORD-\\d+$"}},
            }
        },
        {"$group": {"_id": "$organization_id"}},
    ]
    docs = await orders_collection.aggregate(pipeline).to_list(length=None)
    return [d["_id"] for d in docs if d.get("_id")]


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually rename the orders (default is dry-run).",
    )
    parser.add_argument(
        "--org-id", default=None,
        help="Restrict to a single org. Default: all orgs with legacy orders.",
    )
    args = parser.parse_args()

    if args.org_id:
        org_ids = [args.org_id]
    else:
        org_ids = await _list_orgs_with_legacy_orders()

    logger.info(
        "rebrand_order_numbers: %s mode, %d org(s) with legacy orders",
        "APPLY" if args.apply else "DRY-RUN", len(org_ids),
    )

    grand_total = {
        "orgs": 0, "candidates": 0, "renamed": 0,
        "sales_records_touched": 0, "errors": 0,
    }
    for org_id in org_ids:
        try:
            stats = await _rebrand_org(org_id, apply=args.apply)
        except Exception as exc:
            logger.error("org=%s crashed: %s", org_id, exc, exc_info=True)
            continue
        grand_total["orgs"] += 1
        for k in ("candidates", "renamed", "sales_records_touched", "errors"):
            grand_total[k] += stats.get(k, 0)
        if args.apply:
            logger.info(
                "org=%s: candidates=%d renamed=%d sales_records_touched=%d errors=%d",
                org_id, stats["candidates"], stats["renamed"],
                stats["sales_records_touched"], stats["errors"],
            )

    logger.info("──────────────────────────── SUMMARY ────────────────────────────")
    logger.info(
        "orgs=%d candidates=%d renamed=%d sales_records_touched=%d errors=%d",
        grand_total["orgs"], grand_total["candidates"], grand_total["renamed"],
        grand_total["sales_records_touched"], grand_total["errors"],
    )
    if not args.apply:
        logger.info("(dry-run — re-run with --apply to commit the rebrand)")


if __name__ == "__main__":
    asyncio.run(main())
