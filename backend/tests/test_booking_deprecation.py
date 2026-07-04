#!/usr/bin/env python3
"""
Onda 16 Fase 6 — Deprecation cleanup for item_type="booking".

Focused invariants (no external services, no DB required for the helper
tests; the migration idempotency test does hit MongoDB).

  1. _rewrite_deprecated_booking rewrites item_type + sets reservation_flavor
     when absent, preserves other metadata, and is a no-op for non-booking
     payloads.
  2. _rewrite_deprecated_booking leaves an explicit reservation_flavor alone
     (in case a caller already set it but also sent the legacy item_type).
  3. The migration script is idempotent: running twice leaves the DB in the
     same state as running once.

Runs directly with the project venv against the local MongoDB:

  cd backend && ./venv/bin/python tests/test_booking_deprecation.py

Exits 0 on full pass, non-zero on first failure.
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


PREFIX = "test_deprec_"


def t01_rewrite_basic():
    from routers.products import _rewrite_deprecated_booking

    payload = {
        "item_type": "booking",
        "name": "X",
        "metadata": {"slot_duration_minutes": 60, "duration_label": "1 ora"},
    }
    rewritten = _rewrite_deprecated_booking(payload)
    assert rewritten is True
    assert payload["item_type"] == "rental"
    assert payload["metadata"]["reservation_flavor"] == "slot"
    # Pre-existing metadata keys must be preserved verbatim.
    assert payload["metadata"]["slot_duration_minutes"] == 60
    assert payload["metadata"]["duration_label"] == "1 ora"


def t02_rewrite_noop_for_other_types():
    from routers.products import _rewrite_deprecated_booking

    for item_type in ("physical", "service", "rental", "event_ticket"):
        payload = {"item_type": item_type, "name": "X"}
        rewritten = _rewrite_deprecated_booking(payload)
        assert rewritten is False, item_type
        assert payload["item_type"] == item_type


def t03_rewrite_preserves_explicit_flavor():
    from routers.products import _rewrite_deprecated_booking

    # Odd but possible: caller sent legacy item_type AND an explicit flavor.
    # We must not clobber their intent.
    payload = {
        "item_type": "booking",
        "name": "X",
        "metadata": {"reservation_flavor": "range"},
    }
    rewritten = _rewrite_deprecated_booking(payload)
    assert rewritten is True
    assert payload["item_type"] == "rental"
    assert payload["metadata"]["reservation_flavor"] == "range"


def t04_rewrite_handles_missing_metadata():
    from routers.products import _rewrite_deprecated_booking

    payload = {"item_type": "booking", "name": "X"}
    rewritten = _rewrite_deprecated_booking(payload)
    assert rewritten is True
    assert payload["item_type"] == "rental"
    assert payload["metadata"] == {"reservation_flavor": "slot"}


async def t05_migration_idempotent():
    """End-to-end: seed a legacy booking doc, run the migration twice, assert
    the second run is a no-op."""
    from database import products_collection
    from models.common import utc_now

    org = f"{PREFIX}org"
    pid = f"{PREFIX}prod"

    # Cleanup previous runs
    await products_collection.delete_many({"organization_id": org})

    now = utc_now()
    await products_collection.insert_one({
        "id": pid,
        "organization_id": org,
        "item_type": "booking",
        "name": "Legacy Booking Product",
        "unit_price": 20,
        "is_active": True,
        "metadata": {"slot_duration_minutes": 60, "duration_label": "1 ora"},
        "created_at": now,
        "updated_at": now,
    })

    # Inline migration logic (mirrors migrate_booking_to_rental_slot.py) —
    # we avoid subprocess overhead for speed.
    async def _run_migration():
        count = 0
        async for prod in products_collection.find({"item_type": "booking", "organization_id": org}):
            meta = dict(prod.get("metadata") or {})
            if not meta.get("reservation_flavor"):
                meta["reservation_flavor"] = "slot"
            await products_collection.update_one(
                {"_id": prod["_id"]},
                {"$set": {
                    "item_type": "rental",
                    "metadata": meta,
                    "updated_at": utc_now(),
                }},
            )
            count += 1
        return count

    first_count = await _run_migration()
    assert first_count == 1, first_count

    # Verify end state
    doc = await products_collection.find_one({"id": pid, "organization_id": org})
    assert doc["item_type"] == "rental"
    assert doc["metadata"]["reservation_flavor"] == "slot"
    assert doc["metadata"]["slot_duration_minutes"] == 60

    # Second run — nothing matches item_type=booking anymore
    second_count = await _run_migration()
    assert second_count == 0, second_count

    # Cleanup
    await products_collection.delete_many({"organization_id": org})


def _sync_wrap(fn):
    async def runner():
        return fn()
    return runner


async def main():
    tests = [
        ("t01_rewrite_basic", _sync_wrap(t01_rewrite_basic)),
        ("t02_rewrite_noop_for_other_types", _sync_wrap(t02_rewrite_noop_for_other_types)),
        ("t03_rewrite_preserves_explicit_flavor", _sync_wrap(t03_rewrite_preserves_explicit_flavor)),
        ("t04_rewrite_handles_missing_metadata", _sync_wrap(t04_rewrite_handles_missing_metadata)),
        ("t05_migration_idempotent", t05_migration_idempotent),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            await fn()
            print(f"  ✅ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {name}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n  Result: {passed}/{len(tests)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    rc = asyncio.run(main())
    sys.exit(rc)
