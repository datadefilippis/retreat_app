#!/usr/bin/env python3
"""
Focused unit + integration tests for booking slot reservation (P5).

Distinct from the legacy e2e_booking.py (611 lines, flow-oriented): this
module zooms in on the atomic reservation primitive and the P3 validator
pre-flight that depends on it. Fast, isolated, deterministic.

Runs directly with the project venv against the local MongoDB:

  cd backend && ./venv/bin/python tests/test_booking_slot_reservation.py

Exits 0 on full pass, non-zero on first failure.

Invariants covered:

  1. Exact-slot idempotency — same order_id, same key returns
     already_reserved instead of creating a duplicate.
  2. Exact-slot conflict — different order_id, same key → slot_conflict.
  3. Half-open interval math — adjacent slots do not collide.
  4. Overlap detection — partially overlapping slots collide.
  5. Product isolation — same key on different product_id is free.
  6. Org isolation — same key on different organization is free.
  7. Global blocks (product_id=None) block product-specific bookings.
  8. Invalid time window rejected before any write.
  9. 10-way concurrency (same slot) — exactly 1 winner, 9 conflicts.
 10. 100-way concurrency (overlapping slots) — exactly 1 winner across
     both windows.
 11. release_booking_slot only deletes rows owned by the order_id.
 12. P3 validator pre-flight surfaces slot_conflict cleanly.
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


PREFIX = "test_p6_"   # sentinel so cleanup queries never touch production


async def _clean(collection):
    """Remove any test artifacts from previous runs."""
    await collection.delete_many({"reference_id": {"$regex": f"^{PREFIX}"}})
    await collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})


async def t01_exact_slot_idempotent():
    from database import blocked_slots_collection
    from services.booking_availability import try_reserve_booking_slot

    await _clean(blocked_slots_collection)
    org, prod, date = f"{PREFIX}org", f"{PREFIX}prod", "2026-09-01"

    ok, reason, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}ord_a", org_id=org, product_id=prod,
        date=date, start_time="10:00", end_time="11:00",
    )
    assert ok and reason == "reserved"

    # Same order retrying the exact same slot — must be idempotent
    ok, reason, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}ord_a", org_id=org, product_id=prod,
        date=date, start_time="10:00", end_time="11:00",
    )
    assert ok and reason == "already_reserved", (ok, reason)

    # Verify only one row exists
    c = await blocked_slots_collection.count_documents({
        "organization_id": org, "product_id": prod, "date": date,
    })
    assert c == 1


async def t02_exact_slot_conflict():
    from database import blocked_slots_collection
    from services.booking_availability import try_reserve_booking_slot

    await _clean(blocked_slots_collection)
    org, prod, date = f"{PREFIX}org", f"{PREFIX}prod", "2026-09-02"

    ok, reason, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}o_first", org_id=org, product_id=prod,
        date=date, start_time="10:00", end_time="11:00",
    )
    assert ok and reason == "reserved"

    ok, reason, conflict = await try_reserve_booking_slot(
        order_id=f"{PREFIX}o_second", org_id=org, product_id=prod,
        date=date, start_time="10:00", end_time="11:00",
    )
    assert not ok and reason == "slot_conflict"
    assert conflict is not None
    assert conflict.get("reference_id") == f"{PREFIX}o_first"


async def t03_half_open_intervals():
    from database import blocked_slots_collection
    from services.booking_availability import try_reserve_booking_slot

    await _clean(blocked_slots_collection)
    org, prod, date = f"{PREFIX}org", f"{PREFIX}prod", "2026-09-03"

    # Reserve 10:00-11:00, then try to reserve 11:00-12:00 — adjacent.
    ok, reason, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}a", org_id=org, product_id=prod,
        date=date, start_time="10:00", end_time="11:00",
    )
    assert ok
    ok, reason, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}b", org_id=org, product_id=prod,
        date=date, start_time="11:00", end_time="12:00",
    )
    assert ok and reason == "reserved", f"adjacent should be allowed, got {reason}"


async def t04_overlap_detected():
    from database import blocked_slots_collection
    from services.booking_availability import try_reserve_booking_slot

    await _clean(blocked_slots_collection)
    org, prod, date = f"{PREFIX}org", f"{PREFIX}prod", "2026-09-04"

    await try_reserve_booking_slot(
        order_id=f"{PREFIX}a", org_id=org, product_id=prod,
        date=date, start_time="10:00", end_time="11:00",
    )
    ok, reason, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}b", org_id=org, product_id=prod,
        date=date, start_time="10:30", end_time="11:30",
    )
    assert not ok and reason == "slot_conflict"


async def t05_product_isolation():
    from database import blocked_slots_collection
    from services.booking_availability import try_reserve_booking_slot

    await _clean(blocked_slots_collection)
    org, date = f"{PREFIX}org", "2026-09-05"

    ok, _, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}a", org_id=org, product_id=f"{PREFIX}prod_A",
        date=date, start_time="10:00", end_time="11:00",
    )
    assert ok
    ok, reason, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}b", org_id=org, product_id=f"{PREFIX}prod_B",
        date=date, start_time="10:00", end_time="11:00",
    )
    assert ok and reason == "reserved"


async def t06_org_isolation():
    from database import blocked_slots_collection
    from services.booking_availability import try_reserve_booking_slot

    await _clean(blocked_slots_collection)
    date = "2026-09-06"

    ok, _, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}a", org_id=f"{PREFIX}org_A", product_id=f"{PREFIX}prod",
        date=date, start_time="10:00", end_time="11:00",
    )
    assert ok
    ok, reason, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}b", org_id=f"{PREFIX}org_B", product_id=f"{PREFIX}prod",
        date=date, start_time="10:00", end_time="11:00",
    )
    assert ok and reason == "reserved"


async def t07_global_block():
    from database import blocked_slots_collection
    from services.booking_availability import check_booking_slot_available
    from models.common import generate_id, utc_now

    await _clean(blocked_slots_collection)
    org, prod, date = f"{PREFIX}org", f"{PREFIX}prod", "2026-09-07"

    # Simulate merchant marking themselves busy on that date
    await blocked_slots_collection.insert_one({
        "id": generate_id(), "organization_id": org, "store_id": None,
        "product_id": None,  # global
        "date": date, "start_time": "14:00", "end_time": "16:00",
        "reason": "personal", "reference_id": f"{PREFIX}personal",
        "note": "off", "created_at": utc_now(),
    })

    ok, reason, conflict = await check_booking_slot_available(
        org, prod, date, "15:00", "15:30",
    )
    assert not ok and reason == "slot_conflict"
    assert conflict is not None


async def t08_invalid_window_rejected():
    from services.booking_availability import try_reserve_booking_slot

    ok, reason, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}bad", org_id=f"{PREFIX}org", product_id=f"{PREFIX}prod",
        date="2026-09-08", start_time="11:00", end_time="10:00",  # inverted
    )
    assert not ok and reason == "invalid_time_window"


async def t09_concurrency_exact_slot():
    from database import blocked_slots_collection
    from services.booking_availability import try_reserve_booking_slot

    await _clean(blocked_slots_collection)
    org, prod, date = f"{PREFIX}org_conc", f"{PREFIX}prod", "2026-09-09"

    async def attempt(i):
        return await try_reserve_booking_slot(
            order_id=f"{PREFIX}conc_{i}", org_id=org, product_id=prod,
            date=date, start_time="09:00", end_time="10:00",
        )

    results = await asyncio.gather(*(attempt(i) for i in range(10)))
    wins = [r for r in results if r[0] and r[1] == "reserved"]
    confs = [r for r in results if not r[0] and r[1] == "slot_conflict"]
    assert len(wins) == 1, f"expected 1 winner, got {len(wins)}"
    assert len(confs) == 9, f"expected 9 conflicts, got {len(confs)}"

    c = await blocked_slots_collection.count_documents({
        "organization_id": org, "product_id": prod, "date": date,
    })
    assert c == 1


async def t10_concurrency_overlap():
    from database import blocked_slots_collection
    from services.booking_availability import try_reserve_booking_slot

    await _clean(blocked_slots_collection)
    org, prod, date = f"{PREFIX}org_ov", f"{PREFIX}prod", "2026-09-10"

    async def attempt(i):
        if i < 50:
            return await try_reserve_booking_slot(
                order_id=f"{PREFIX}ov_a_{i}", org_id=org, product_id=prod,
                date=date, start_time="09:00", end_time="10:00",
            )
        return await try_reserve_booking_slot(
            order_id=f"{PREFIX}ov_b_{i}", org_id=org, product_id=prod,
            date=date, start_time="09:30", end_time="10:30",
        )

    results = await asyncio.gather(*(attempt(i) for i in range(100)))
    wins = [r for r in results if r[0] and r[1] == "reserved"]
    assert len(wins) == 1, f"expected 1 winner across overlapping windows, got {len(wins)}"

    c = await blocked_slots_collection.count_documents({
        "organization_id": org, "product_id": prod, "date": date,
    })
    assert c == 1


async def t11_release_scoped():
    from database import blocked_slots_collection
    from services.booking_availability import try_reserve_booking_slot, release_booking_slot

    await _clean(blocked_slots_collection)
    org, prod, date = f"{PREFIX}org", f"{PREFIX}prod", "2026-09-11"

    # Two different orders reserve different slots
    await try_reserve_booking_slot(
        order_id=f"{PREFIX}mine", org_id=org, product_id=prod,
        date=date, start_time="09:00", end_time="10:00",
    )
    await try_reserve_booking_slot(
        order_id=f"{PREFIX}others", org_id=org, product_id=prod,
        date=date, start_time="10:00", end_time="11:00",
    )

    deleted = await release_booking_slot(f"{PREFIX}mine", org)
    assert deleted == 1

    # The other order's slot must still exist
    surv = await blocked_slots_collection.find_one({
        "reference_id": f"{PREFIX}others", "reason": "booking",
    })
    assert surv is not None, "release should not touch other orders' rows"


async def t12_validator_preflight():
    """The P3 validator must turn a slot_conflict into a structured
    ValidationResult so the router emits the correct user message."""
    from dataclasses import dataclass
    from database import blocked_slots_collection
    from services.booking_availability import try_reserve_booking_slot
    from services.product_type_validators import validate_order_item

    await _clean(blocked_slots_collection)
    org, prod, date = f"{PREFIX}org", f"{PREFIX}prod", "2026-09-12"

    # Pre-occupy the slot
    ok, _, _ = await try_reserve_booking_slot(
        order_id=f"{PREFIX}first", org_id=org, product_id=prod,
        date=date, start_time="10:00", end_time="11:00",
    )
    assert ok

    @dataclass
    class Item:
        product_id: str = prod
        quantity: float = 1
        booking_date: str = date
        booking_start_time: str = "10:00"
        booking_end_time: str = "11:00"

    r = await validate_order_item(Item(), {"item_type": "booking", "id": prod}, {"org_id": org})
    assert not r.valid
    assert r.reason == "slot_conflict", f"expected slot_conflict, got {r.reason}"
    assert r.detail  # must carry the formatted window


# ── Harness ─────────────────────────────────────────────────────────────────

TESTS = [
    ("t01 exact slot idempotency", t01_exact_slot_idempotent),
    ("t02 exact slot conflict", t02_exact_slot_conflict),
    ("t03 half-open intervals", t03_half_open_intervals),
    ("t04 overlap detected", t04_overlap_detected),
    ("t05 product isolation", t05_product_isolation),
    ("t06 org isolation", t06_org_isolation),
    ("t07 global block blocks bookings", t07_global_block),
    ("t08 invalid window rejected", t08_invalid_window_rejected),
    ("t09 10-way concurrent race", t09_concurrency_exact_slot),
    ("t10 100-way overlap race", t10_concurrency_overlap),
    ("t11 release scoped to own rows", t11_release_scoped),
    ("t12 P3 validator pre-flight", t12_validator_preflight),
]


async def main() -> int:
    failures = []
    for name, fn in TESTS:
        try:
            await fn()
            print(f"  [PASS] {name}")
        except AssertionError as e:
            failures.append((name, str(e) or "assertion failed"))
            print(f"  [FAIL] {name}  — {e}")
        except Exception as e:
            failures.append((name, f"{type(e).__name__}: {e}"))
            print(f"  [FAIL] {name}  — {type(e).__name__}: {e}")

    # Final cleanup
    try:
        from database import blocked_slots_collection
        await _clean(blocked_slots_collection)
    except Exception:
        pass

    print()
    if failures:
        print(f"{len(failures)}/{len(TESTS)} FAILED")
        for name, reason in failures:
            print(f"  - {name}: {reason}")
        return 1
    print(f"{len(TESTS)}/{len(TESTS)} PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
