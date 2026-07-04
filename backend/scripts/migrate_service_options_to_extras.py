#!/usr/bin/env python3
"""
migrate_service_options_to_extras.py
=====================================
Onda 16 (Prenotazione consolidation) — one-time idempotent migration.

Context:
  ServiceOption is being generalized into ProductExtra with richer
  semantics (kind: mandatory | optional | radio_variant). Every existing
  ServiceOption is a mutually-exclusive choice (radio), so it maps
  cleanly to kind="radio_variant". Options of the same product share
  a product-scoped group_key so the storefront renders them as one
  picker group.

Strategy:
  For each ServiceOption row:
    - Create a ProductExtra with:
        kind="radio_variant"
        group_key=f"svc_{product_id}"  # stable per-product group
        label, description, price, duration_minutes_override,
        sort_order, is_active = copied verbatim
        price_modifier_type="flat"
        is_default=False  (UI can elect the default later)
  ServiceOption rows are LEFT IN PLACE — the back-compat shim on
  /api/products/:id/service-options continues to read from them for
  one release. A follow-up script will archive them once confirmed.

Idempotency:
  - Each ServiceOption has a unique id. Before creating a ProductExtra
    we check for an existing row with matching
    (organization_id, product_id, label, group_key="svc_<product_id>")
    — treat as already-migrated.

Rollback:
  - Delete ProductExtra rows where group_key LIKE "svc_%".

Run from the backend/ directory:

    cd backend
    python -m scripts.migrate_service_options_to_extras
    python -m scripts.migrate_service_options_to_extras --apply
    python -m scripts.migrate_service_options_to_extras --apply --verbose
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def run(apply: bool, verbose: bool) -> int:
    from database import service_options_collection, product_extras_collection
    from models.common import generate_id, utc_now

    total = await service_options_collection.count_documents({})
    existing_extras = await product_extras_collection.count_documents({
        "group_key": {"$regex": "^svc_"},
    })

    print(f"service_options total docs:     {total}")
    print(f"product_extras already migrated (svc_* group): {existing_extras}")

    if total == 0:
        print("No service options to migrate.")
        return 0

    # Build an index of already-migrated labels per product to avoid dupes.
    already_migrated: dict = {}
    async for pe in product_extras_collection.find(
        {"group_key": {"$regex": "^svc_"}},
        {"_id": 0, "organization_id": 1, "product_id": 1, "label": 1},
    ):
        key = (pe.get("organization_id"), pe.get("product_id"), pe.get("label"))
        already_migrated[key] = True

    to_migrate_rows = []
    async for so in service_options_collection.find({}, {"_id": 0}):
        org_id = so.get("organization_id")
        pid = so.get("product_id")
        label = so.get("label")
        if not (org_id and pid and label):
            continue
        if (org_id, pid, label) in already_migrated:
            continue
        to_migrate_rows.append(so)

    print(f"service options pending migration: {len(to_migrate_rows)}")

    if not to_migrate_rows:
        print("Nothing new to migrate.")
        return 0

    if not apply:
        print("\n[DRY RUN] Would migrate (first 20):")
        for so in to_migrate_rows[:20]:
            print(
                f"  - org={so.get('organization_id')} "
                f"product={so.get('product_id')} "
                f"label={so.get('label')!r} "
                f"price={so.get('price')}"
            )
        if len(to_migrate_rows) > 20:
            print(f"  ... and {len(to_migrate_rows) - 20} more")
        print("\nRun with --apply to actually migrate.")
        return 0

    # Apply.
    migrated = 0
    now = utc_now()
    for so in to_migrate_rows:
        org_id = so.get("organization_id")
        pid = so.get("product_id")
        extra_doc = {
            "id": generate_id(),
            "organization_id": org_id,
            "product_id": pid,
            "kind": "radio_variant",
            "group_key": f"svc_{pid}",
            "label": so.get("label"),
            "description": so.get("description"),
            "price": float(so.get("price") or 0),
            "price_modifier_type": "flat",
            "duration_minutes_override": so.get("duration_minutes_override"),
            "is_default": False,
            "sort_order": int(so.get("sort_order") or 0),
            "is_active": bool(so.get("is_active", True)),
            "created_at": now,
            "updated_at": now,
        }
        await product_extras_collection.insert_one(extra_doc)
        migrated += 1
        if verbose:
            print(f"  migrated service_option label={so.get('label')} product={pid}")

    print(f"\n[APPLY] migrated {migrated} / {len(to_migrate_rows)} service_options.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    exit_code = asyncio.run(run(apply=args.apply, verbose=args.verbose))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
