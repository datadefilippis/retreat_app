#!/usr/bin/env python3
"""
check_customer_email_duplicates.py
==================================
Phase 4 of the Store consolidation plan — pre-deployment check for
existing (organization_id, email) duplicates in `customers_collection`.

Why this exists
---------------
Phase 4 introduces a UNIQUE partial index on `(organization_id, email)`
in `database.create_indexes()`. If the production DB carries any
duplicate (org_id, email) pairs at deploy time, the `create_index` call
fails with DuplicateKey and the FastAPI app crashes on startup.

This script is the pre-flight check: run it BEFORE deploying Phase 4
on each environment. It's read-only — never modifies data. If
duplicates are found, the operator must resolve them manually (or via
a separate, intentional merge script) before the new index can be safe.

How duplicates can exist
-------------------------
Pre-Phase-4 the storefront and POS paths used find-then-insert which
left a race window. Concurrent orders from the same email could each
insert a row. Most deployments will be clean (the race is narrow), but
high-traffic stores with simultaneous checkouts are the at-risk profile.

Usage:
    cd backend
    python -m scripts.check_customer_email_duplicates
    python -m scripts.check_customer_email_duplicates --verbose

Exit codes:
    0  No duplicates — safe to deploy Phase 4.
    1  Duplicates found — resolve before deploying.
    2  DB / aggregation error.
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def _find_duplicates(limit: int = 100):
    """Aggregate customers_collection to find (org_id, email) groups
    with count > 1. Email-null rows are filtered out (the partial
    index ignores them too, so they're not relevant)."""
    from database import customers_collection

    pipeline = [
        # The partial index uses {email: {$type: "string"}} — mirror
        # that filter here so we only count duplicates the index
        # would actually reject.
        {"$match": {"email": {"$type": "string"}}},
        {"$group": {
            "_id": {"org": "$organization_id", "email": "$email"},
            "count": {"$sum": 1},
            "ids": {"$push": "$id"},
            "names": {"$push": "$name"},
            "created_at": {"$push": "$created_at"},
        }},
        {"$match": {"count": {"$gt": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    return [doc async for doc in customers_collection.aggregate(pipeline)]


async def _run(verbose: bool):
    try:
        dups = await _find_duplicates()
    except Exception as e:
        print(f"ERROR: aggregation failed: {e}")
        return 2

    if not dups:
        print("=" * 70)
        print("customers_collection — (organization_id, email) duplicate check")
        print("=" * 70)
        print("CLEAN — no duplicate (org_id, email) pairs found.")
        print("Safe to deploy Phase 4's unique partial index.")
        return 0

    total_rows = sum(d["count"] for d in dups)
    print("=" * 70)
    print("customers_collection — (organization_id, email) duplicate check")
    print("=" * 70)
    print(f"FOUND {len(dups)} duplicate groups ({total_rows} rows total)")
    print()
    print("These prevent the Phase 4 unique partial index from being")
    print("created. Resolve manually before deploying:")
    print("  - merge customer rows (move orders, customer_accounts links)")
    print("  - OR null out the email on the duplicate(s) (keeps them as")
    print("    separate rows but they no longer collide on the index)")
    print()

    show = dups if verbose else dups[:10]
    for d in show:
        org = d["_id"]["org"]
        email = d["_id"]["email"]
        cnt = d["count"]
        ids = d["ids"]
        names = d["names"]
        print(f"  org={org}  email={email}  count={cnt}")
        for i, (cid, name) in enumerate(zip(ids, names)):
            print(f"    [{i}] id={cid}  name={name!r}")
        print()

    if not verbose and len(dups) > 10:
        print(f"... and {len(dups) - 10} more groups. Re-run with --verbose for all.")

    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show all duplicate groups (default: first 10)")
    args = parser.parse_args()
    rc = asyncio.run(_run(verbose=args.verbose))
    sys.exit(rc)


if __name__ == "__main__":
    main()
