#!/usr/bin/env python3
"""
clean_empty_field_labels.py — remove empty-label entries from product metadata.

Context:
  FieldConfig.label has a min_length=1 invariant (backend/models/field_config.py).
  If a merchant saved an attendee_fields / order_fields row without a label
  (common accidental save after clicking "+ Aggiungi campo"), the public
  catalog endpoint can't serialise that product — Pydantic raises a
  ValidationError and, before the resilience patch, the whole store's
  catalog went down with a 500. The backend now silently filters bad
  rows at read time, but the merchant dashboard still displays the empty
  entry. This script gives operators a way to clean the stored documents
  once and for all.

Usage (mirrors reset_org_data.py ergonomics):
  # Preview — no writes.
  ./venv/bin/python scripts/clean_empty_field_labels.py

  # Apply the cleanup.
  ./venv/bin/python scripts/clean_empty_field_labels.py --execute

  # Restrict to a single organization (matches users.email).
  ./venv/bin/python scripts/clean_empty_field_labels.py --email foo@example.com

Idempotent — running twice after an --execute is a no-op.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _keep(field: dict) -> bool:
    label = (field or {}).get("label")
    return bool(label and str(label).strip())


async def _maybe_resolve_org(users_collection, organizations_collection, email: str | None):
    if not email:
        return None
    user = await users_collection.find_one({"email": email}, {"_id": 0, "organization_id": 1})
    if not user or not user.get("organization_id"):
        raise SystemExit(f"No user/org found for email={email!r}. Aborting.")
    return user["organization_id"]


async def main():
    parser = argparse.ArgumentParser(description="Remove empty-label entries from product metadata fields.")
    parser.add_argument("--execute", action="store_true", help="Apply updates. Without this flag the script is a dry run.")
    parser.add_argument("--email", default=None, help="Restrict to a single user's organization (optional).")
    args = parser.parse_args()

    from database import products_collection, users_collection, organizations_collection

    org_id = await _maybe_resolve_org(users_collection, organizations_collection, args.email)
    base_query = {"organization_id": org_id} if org_id else {}
    # We only care about products that actually have metadata fields arrays.
    query = {
        **base_query,
        "$or": [
            {"metadata.attendee_fields": {"$exists": True, "$ne": []}},
            {"metadata.order_fields": {"$exists": True, "$ne": []}},
        ],
    }

    total_seen = 0
    total_dirty = 0
    planned_updates: list[dict] = []

    async for prod in products_collection.find(query, {"_id": 0, "id": 1, "name": 1, "metadata": 1, "organization_id": 1}):
        total_seen += 1
        meta = prod.get("metadata") or {}
        attendee = meta.get("attendee_fields") or []
        order = meta.get("order_fields") or []
        cleaned_attendee = [f for f in attendee if _keep(f)]
        cleaned_order = [f for f in order if _keep(f)]
        if len(cleaned_attendee) == len(attendee) and len(cleaned_order) == len(order):
            continue
        total_dirty += 1
        planned_updates.append({
            "id": prod["id"],
            "name": prod.get("name"),
            "attendee_before": len(attendee),
            "attendee_after": len(cleaned_attendee),
            "order_before": len(order),
            "order_after": len(cleaned_order),
            "new_attendee": cleaned_attendee,
            "new_order": cleaned_order,
            "organization_id": prod.get("organization_id"),
        })

    print(f"Scanned {total_seen} products with field arrays; {total_dirty} need cleanup.")
    for u in planned_updates:
        print(
            f"  - {u['name']!r} ({u['id']}): "
            f"attendee {u['attendee_before']}→{u['attendee_after']}, "
            f"order {u['order_before']}→{u['order_after']}"
        )

    if not planned_updates:
        return

    if not args.execute:
        print("\nDRY RUN — nothing was modified. Re-run with --execute to apply.")
        return

    # Apply updates.
    updated = 0
    for u in planned_updates:
        result = await products_collection.update_one(
            {"id": u["id"], "organization_id": u["organization_id"]},
            {"$set": {
                "metadata.attendee_fields": u["new_attendee"],
                "metadata.order_fields": u["new_order"],
            }},
        )
        updated += result.modified_count

    print(f"\n✅ Updated {updated}/{len(planned_updates)} products.")


if __name__ == "__main__":
    asyncio.run(main())
