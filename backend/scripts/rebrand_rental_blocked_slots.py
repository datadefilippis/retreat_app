#!/usr/bin/env python3
"""
rebrand_rental_blocked_slots.py — migrate legacy rental blocks from the
"agenda" calendar tab to the "rentals" tab.

Before the Fase 2 scope fix, `rental_availability.try_reserve_rental_range`
wrote every day-block with `scope="agenda"`. That meant rental confirmations
(e.g. a room rented 14→17 December) polluted the merchant's personal
calendar tab alongside consultations and manual blocks. The runtime fix is
in the service (now writes `scope="rentals"`), but the already-persisted
rows in `blocked_slots` still carry the wrong scope — the admin still sees
them in the wrong tab. This script rebrands them.

Selection rule: any blocked_slots doc where `reason == "rental"` **and**
`scope == "agenda"`. These are unambiguously produced by the rental
service; we never touch bookings (`reason=booking`) or events
(`reason=event`).

Usage:
  # Dry run (no writes):
  ./venv/bin/python scripts/rebrand_rental_blocked_slots.py

  # Apply:
  ./venv/bin/python scripts/rebrand_rental_blocked_slots.py --execute

  # Optional: restrict to a single org (via user email, mirrors reset_org_data.py)
  ./venv/bin/python scripts/rebrand_rental_blocked_slots.py --email me@example.com --execute

Idempotent — re-running after --execute is a no-op.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def _maybe_resolve_org(users_collection, email: str | None):
    if not email:
        return None
    user = await users_collection.find_one({"email": email}, {"_id": 0, "organization_id": 1})
    if not user or not user.get("organization_id"):
        raise SystemExit(f"No user/org found for email={email!r}. Aborting.")
    return user["organization_id"]


async def main():
    parser = argparse.ArgumentParser(description="Rebrand rental blocked_slots from scope='agenda' to scope='rentals'.")
    parser.add_argument("--execute", action="store_true", help="Apply updates. Without this flag the script is a dry run.")
    parser.add_argument("--email", default=None, help="Restrict to the org owned by this user email (optional).")
    args = parser.parse_args()

    from database import blocked_slots_collection, users_collection

    org_id = await _maybe_resolve_org(users_collection, args.email)

    query = {"reason": "rental", "scope": "agenda"}
    if org_id:
        query["organization_id"] = org_id

    # Preview
    total = await blocked_slots_collection.count_documents(query)
    print(f"Matching rental blocks with scope='agenda': {total}")

    if total and not args.execute:
        # Show a small sample so the operator can sanity-check before execute.
        sample = await blocked_slots_collection.find(
            query,
            {"_id": 0, "id": 1, "product_id": 1, "reference_id": 1, "date": 1, "note": 1},
        ).limit(5).to_list(5)
        print("Sample (first 5):")
        for s in sample:
            print(
                f"  - date={s.get('date')} note={s.get('note')!r} "
                f"product_id={s.get('product_id')} order_id={s.get('reference_id')}"
            )

    if not total:
        print("Nothing to do.")
        return

    if not args.execute:
        print("\nDRY RUN — nothing was modified. Re-run with --execute to apply.")
        return

    result = await blocked_slots_collection.update_many(
        query,
        {"$set": {"scope": "rentals"}},
    )
    print(f"\n✅ Updated {result.modified_count}/{total} blocks to scope='rentals'.")


if __name__ == "__main__":
    asyncio.run(main())
