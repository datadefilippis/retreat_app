#!/usr/bin/env python3
"""
backfill_connect_type.py
========================
One-time backfill: mark all existing payment_connections documents with
connect_type="standard".

Context:
  The platform is migrating from Standard Connect (OAuth) to Express Connect
  (Account Links). The PaymentConnection model gained a new `connect_type`
  discriminator field. This script sets it to "standard" for all pre-existing
  connections so the application can distinguish legacy accounts from new
  Express ones going forward.

Idempotent: only updates documents missing the field. Safe to re-run.

Run from the backend/ directory:

    cd backend
    python -m scripts.backfill_connect_type            # dry-run (default)
    python -m scripts.backfill_connect_type --apply    # actually write

No-op if all documents already have connect_type set.
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def run(apply: bool) -> int:
    from database import payment_connections_collection

    filter_missing = {"connect_type": {"$exists": False}}

    total = await payment_connections_collection.count_documents({})
    to_update = await payment_connections_collection.count_documents(filter_missing)

    print(f"payment_connections total docs:        {total}")
    print(f"payment_connections without connect_type: {to_update}")

    if to_update == 0:
        print("Nothing to backfill. All documents already have connect_type.")
        return 0

    if not apply:
        print("\nDry-run — pass --apply to execute the update.")
        return 0

    result = await payment_connections_collection.update_many(
        filter_missing,
        {"$set": {"connect_type": "standard"}},
    )
    print(f"\nUpdated {result.modified_count} documents → connect_type=\"standard\"")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute the update (default is dry-run)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(run(apply=args.apply)))


if __name__ == "__main__":
    main()
