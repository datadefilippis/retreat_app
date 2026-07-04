#!/usr/bin/env python3
"""
backfill_drop_null_public_slug.py
==================================
Onda 9.Z Step B — clean up legacy `public_slug: null` explicit values
in `organizations` documents by `$unset`-ting the field.

Why:
  After Step A migration, the partialFilterExpression index correctly
  excludes documents with `public_slug: null` (or missing, or non-string).
  Legacy docs with explicit null still work — they simply bypass the
  index. But cosmetic: they pollute downstream queries like
  `find({public_slug: {$exists: false}})` (which returns ONLY missing,
  not nulls) and aggregation pipelines.

  Removing the explicit null brings the DB into a consistent shape:
  every org has either a real string slug or no field at all.

What this script does:
  1. Counts orgs where `public_slug: null` is EXPLICITLY set
     (i.e. {public_slug: null, public_slug: {$exists: true}} matches)
  2. Dry-run by default — prints what would change
  3. With --apply: `update_many({public_slug: null, $exists: true},
     {$unset: {public_slug: ""}})`
  4. Re-counts post-apply and verifies invariant

Idempotent. Safe to re-run. Zero data loss (the value was null —
removing it preserves "no slug" semantic).

Usage:
    cd backend
    python -m scripts.backfill_drop_null_public_slug          # dry-run
    python -m scripts.backfill_drop_null_public_slug --apply  # execute
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def _count_explicit_null():
    """Count orgs where public_slug is explicitly set to null.

    Note: in MongoDB, `find({public_slug: null})` matches BOTH explicit
    null AND missing field. To distinguish, we additionally require
    `public_slug: {$exists: true}` so only the explicit null subset is
    counted.
    """
    from database import organizations_collection
    return await organizations_collection.count_documents({
        "public_slug": None,
        "public_slug": {"$exists": True},
    })


async def _count_missing():
    from database import organizations_collection
    return await organizations_collection.count_documents({
        "public_slug": {"$exists": False},
    })


async def _count_string():
    from database import organizations_collection
    return await organizations_collection.count_documents({
        "public_slug": {"$type": "string"},
    })


async def _count_total():
    from database import organizations_collection
    return await organizations_collection.count_documents({})


async def _print_state(label: str):
    total = await _count_total()
    null_explicit = await _count_explicit_null()
    missing = await _count_missing()
    string_val = await _count_string()
    other = total - null_explicit - missing - string_val
    print(f"  [{label}] total={total}  string={string_val}  "
          f"null_explicit={null_explicit}  missing={missing}  other={other}")
    return null_explicit


async def _run(args) -> int:
    print("=" * 70)
    print("BACKFILL — drop explicit null `public_slug` from organizations")
    print("=" * 70)
    print()

    null_pre = await _print_state("BEFORE")

    if null_pre == 0:
        print()
        print("✅ No org with explicit null. Nothing to backfill.")
        return 0

    if not args.apply:
        print()
        print(f"DRY-RUN: would $unset public_slug on {null_pre} doc(s).")
        print("Re-run with --apply to execute.")
        return 0

    print()
    print(f"Applying $unset to {null_pre} doc(s)...")
    from database import organizations_collection
    res = await organizations_collection.update_many(
        # WARNING: in MongoDB, this matches both explicit null AND missing.
        # We don't filter by $exists here because $unset on missing field
        # is a no-op (idempotent), so matching too widely is safe.
        {"public_slug": None},
        {"$unset": {"public_slug": ""}},
    )
    print(f"  matched={res.matched_count}  modified={res.modified_count}")
    print()

    null_post = await _print_state("AFTER")
    print()

    if null_post == 0:
        print("✅ Backfill complete. No org has explicit null any more.")
        return 0
    else:
        print(f"⚠ {null_post} doc(s) still have explicit null. Investigate.")
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true",
                        help="Execute the backfill. Default is dry-run.")
    args = parser.parse_args()
    rc = asyncio.run(_run(args))
    sys.exit(rc)


if __name__ == "__main__":
    main()
