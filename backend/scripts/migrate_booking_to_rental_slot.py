#!/usr/bin/env python3
"""
migrate_booking_to_rental_slot.py
==================================
Onda 16 (Prenotazione consolidation) — one-time idempotent migration.

Context:
  item_type="booking" is being deprecated in favor of a unified
  "rental" type with metadata.reservation_flavor. Products previously
  created as booking become rental + flavor=slot with the same slot
  scheduling knobs (slot_duration_minutes, duration_label,
  buffer_*_minutes). Order rows are NOT touched — OrderLine.item_type
  snapshot stays as "booking" for historical orders so invoices and
  dashboards render unchanged via a read-time shim.

Strategy:
  - Match docs with item_type="booking".
  - Copy existing metadata to a new dict and set reservation_flavor="slot".
  - Change item_type to "rental".
  - Update updated_at timestamp.
  - Re-running on an already-migrated org is a no-op (zero matches).

Rollback:
  - Reverse script sets item_type back to "booking" and removes
    metadata.reservation_flavor. Available on request.

Idempotency:
  - Repeat runs match zero documents after the first successful apply.

Run from the backend/ directory:

    cd backend
    python -m scripts.migrate_booking_to_rental_slot            # dry-run
    python -m scripts.migrate_booking_to_rental_slot --apply    # write
    python -m scripts.migrate_booking_to_rental_slot --apply --verbose  # per-doc log
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def run(apply: bool, verbose: bool) -> int:
    from database import products_collection
    from models.common import utc_now

    filter_booking = {"item_type": "booking"}

    total_products = await products_collection.count_documents({})
    to_migrate = await products_collection.count_documents(filter_booking)

    print(f"products total docs:        {total_products}")
    print(f"products with item_type=booking: {to_migrate}")

    if to_migrate == 0:
        print("Nothing to migrate. All booking products already migrated.")
        return 0

    if not apply:
        print("\n[DRY RUN] Would migrate the following products:")
        async for p in products_collection.find(
            filter_booking,
            {"_id": 0, "id": 1, "name": 1, "organization_id": 1, "metadata": 1},
        ).limit(20):
            meta = p.get("metadata") or {}
            print(
                f"  - id={p.get('id')} name={p.get('name')!r} "
                f"org={p.get('organization_id')} "
                f"slot_duration={meta.get('slot_duration_minutes')} "
                f"duration_label={meta.get('duration_label')}"
            )
        if to_migrate > 20:
            print(f"  ... and {to_migrate - 20} more")
        print("\nRun with --apply to actually migrate.")
        return 0

    # Apply: batch update preserves per-doc metadata (no $set constant blob).
    migrated = 0
    async for p in products_collection.find(filter_booking, {"_id": 0, "id": 1, "metadata": 1}):
        pid = p.get("id")
        if not pid:
            continue
        new_meta = dict(p.get("metadata") or {})
        # Only set flavor if not already present (defensive re-run safety).
        if new_meta.get("reservation_flavor") not in ("range", "slot"):
            new_meta["reservation_flavor"] = "slot"
        result = await products_collection.update_one(
            {"id": pid, "item_type": "booking"},
            {"$set": {
                "item_type": "rental",
                "metadata": new_meta,
                "updated_at": utc_now(),
            }}
        )
        if result.modified_count:
            migrated += 1
            if verbose:
                print(f"  migrated product id={pid}")

    print(f"\n[APPLY] migrated {migrated} / {to_migrate} products.")

    # Post-validation: re-query to assert no booking rows remain.
    remaining = await products_collection.count_documents({"item_type": "booking"})
    if remaining:
        print(
            f"\nWARNING: {remaining} booking products still present — "
            f"verify manually. They may have concurrent writes."
        )
        return 2
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write. Without this flag the script runs in dry-run mode.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Log each migrated product id.",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(run(apply=args.apply, verbose=args.verbose))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
