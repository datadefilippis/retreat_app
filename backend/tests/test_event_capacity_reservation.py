#!/usr/bin/env python3
"""
P7 — Event ticket capacity reservation test suite.

Focused, deterministic checks on services.event_capacity.
Complements commerce_rules occurrence checks with atomicity guarantees.

Invocation:
  cd backend && ./venv/bin/python tests/test_event_capacity_reservation.py

Every id is prefixed with "test_p7_" so cleanup queries cannot touch
production data. Each test seeds and tears down its own occurrence +
reservations.
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from typing import Callable

# Env defaults for local Mongo.
os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_database")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (  # noqa: E402
    event_occurrences_collection,
    event_seat_reservations_collection,
)
from models.common import utc_now  # noqa: E402
from services.event_capacity import (  # noqa: E402
    try_reserve_event_seats,
    release_event_seats,
    get_occurrence_remaining,
)

PREFIX = "test_p7_"
ORG = PREFIX + "org"
PRODUCT = PREFIX + "prod"


async def _cleanup():
    await event_occurrences_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await event_seat_reservations_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})


async def _seed_occurrence(occ_id: str, capacity, status="published", org=ORG):
    await event_occurrences_collection.delete_one({"id": occ_id})
    await event_occurrences_collection.insert_one({
        "id": occ_id,
        "organization_id": org,
        "product_id": PRODUCT,
        "start_at": "2026-08-14T20:30:00",
        "capacity": capacity,
        "status": status,
        "reserved_seats": 0,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    })


async def t01_reserve_basic():
    occ = PREFIX + "occ01"
    order = PREFIX + "ord01"
    await _seed_occurrence(occ, capacity=10)

    ok, reason, updated = await try_reserve_event_seats(
        order_id=order, org_id=ORG, occurrence_id=occ, qty=3,
    )
    assert ok and reason == "reserved", f"{ok} {reason}"
    assert updated["reserved_seats"] == 3, updated
    # reservation row written
    row = await event_seat_reservations_collection.find_one(
        {"order_id": order, "occurrence_id": occ}, {"_id": 0},
    )
    assert row and row["qty"] == 3
    await _cleanup()


async def t02_idempotent_same_qty():
    occ = PREFIX + "occ02"
    order = PREFIX + "ord02"
    await _seed_occurrence(occ, capacity=10)

    ok1, reason1, _ = await try_reserve_event_seats(
        order_id=order, org_id=ORG, occurrence_id=occ, qty=2,
    )
    ok2, reason2, existing = await try_reserve_event_seats(
        order_id=order, org_id=ORG, occurrence_id=occ, qty=2,
    )
    assert ok1 and reason1 == "reserved"
    assert ok2 and reason2 == "already_reserved"
    # counter not double-incremented
    occ_doc = await event_occurrences_collection.find_one({"id": occ}, {"_id": 0})
    assert occ_doc["reserved_seats"] == 2
    await _cleanup()


async def t03_qty_mismatch_same_order():
    occ = PREFIX + "occ03"
    order = PREFIX + "ord03"
    await _seed_occurrence(occ, capacity=10)

    await try_reserve_event_seats(order_id=order, org_id=ORG, occurrence_id=occ, qty=2)
    ok, reason, _ = await try_reserve_event_seats(
        order_id=order, org_id=ORG, occurrence_id=occ, qty=3,
    )
    assert not ok and reason == "qty_mismatch"
    # counter stays at the first qty
    occ_doc = await event_occurrences_collection.find_one({"id": occ}, {"_id": 0})
    assert occ_doc["reserved_seats"] == 2
    await _cleanup()


async def t04_capacity_enforced():
    occ = PREFIX + "occ04"
    await _seed_occurrence(occ, capacity=5)

    ok1, _, _ = await try_reserve_event_seats(order_id=PREFIX + "a", org_id=ORG, occurrence_id=occ, qty=3)
    ok2, _, _ = await try_reserve_event_seats(order_id=PREFIX + "b", org_id=ORG, occurrence_id=occ, qty=2)
    ok3, reason3, occ_full = await try_reserve_event_seats(order_id=PREFIX + "c", org_id=ORG, occurrence_id=occ, qty=1)

    assert ok1 and ok2
    assert not ok3 and reason3 == "occurrence_sold_out", f"{ok3} {reason3}"
    assert occ_full["capacity"] == 5
    # no reservation row for the failed order
    ghost = await event_seat_reservations_collection.find_one({"order_id": PREFIX + "c"})
    assert ghost is None
    await _cleanup()


async def t05_unlimited_capacity():
    occ = PREFIX + "occ05"
    await _seed_occurrence(occ, capacity=None)

    for i in range(5):
        ok, reason, _ = await try_reserve_event_seats(
            order_id=f"{PREFIX}ord05_{i}", org_id=ORG, occurrence_id=occ, qty=100,
        )
        assert ok and reason == "reserved", f"unlimited capacity failed at i={i}"
    occ_doc = await event_occurrences_collection.find_one({"id": occ}, {"_id": 0})
    assert occ_doc["reserved_seats"] == 500
    await _cleanup()


async def t06_status_blocks():
    for state in ("draft", "closed", "cancelled"):
        occ = PREFIX + "occ06_" + state
        await _seed_occurrence(occ, capacity=10, status=state)
        ok, reason, _ = await try_reserve_event_seats(
            order_id=PREFIX + "ord06_" + state, org_id=ORG, occurrence_id=occ, qty=1,
        )
        assert not ok, f"{state} accepted reservation"
        expected = {
            "draft": "occurrence_not_published",
            "closed": "occurrence_closed",
            "cancelled": "occurrence_cancelled",
        }[state]
        assert reason == expected, f"{state}: got {reason}"
    await _cleanup()


async def t07_occurrence_missing():
    ok, reason, _ = await try_reserve_event_seats(
        order_id=PREFIX + "ord07", org_id=ORG,
        occurrence_id=PREFIX + "does_not_exist", qty=1,
    )
    assert not ok and reason == "occurrence_not_found"
    await _cleanup()


async def t08_org_isolation():
    occ = PREFIX + "occ08"
    await _seed_occurrence(occ, capacity=10, org=ORG + "_A")

    ok, reason, _ = await try_reserve_event_seats(
        order_id=PREFIX + "ord08", org_id=ORG + "_B", occurrence_id=occ, qty=1,
    )
    assert not ok and reason == "occurrence_not_found"
    await _cleanup()


async def t09_invalid_qty():
    for bad in (0, -1, 1.5):
        ok, reason, _ = await try_reserve_event_seats(
            order_id=PREFIX + "ord09", org_id=ORG, occurrence_id=PREFIX + "occ09", qty=bad,
        )
        assert not ok and reason == "invalid_qty", f"bad={bad}"
    await _cleanup()


async def t10_concurrent_race_last_seat():
    occ = PREFIX + "occ10"
    await _seed_occurrence(occ, capacity=1)

    async def attempt(i):
        return await try_reserve_event_seats(
            order_id=f"{PREFIX}race10_{i}", org_id=ORG, occurrence_id=occ, qty=1,
        )

    results = await asyncio.gather(*[attempt(i) for i in range(10)])
    winners = [r for r in results if r[0]]
    losers = [r for r in results if not r[0]]
    assert len(winners) == 1, f"expected 1 winner, got {len(winners)}"
    assert all(r[1] == "occurrence_sold_out" for r in losers), [r[1] for r in losers]

    occ_doc = await event_occurrences_collection.find_one({"id": occ}, {"_id": 0})
    assert occ_doc["reserved_seats"] == 1
    # exactly 1 reservation row
    rows = await event_seat_reservations_collection.count_documents({"occurrence_id": occ})
    assert rows == 1
    await _cleanup()


async def t11_release_restores_seats():
    occ = PREFIX + "occ11"
    order = PREFIX + "ord11"
    other = PREFIX + "ord11_other"
    await _seed_occurrence(occ, capacity=10)

    await try_reserve_event_seats(order_id=order, org_id=ORG, occurrence_id=occ, qty=4)
    await try_reserve_event_seats(order_id=other, org_id=ORG, occurrence_id=occ, qty=3)

    deleted = await release_event_seats(order_id=order, org_id=ORG)
    assert deleted == 1

    occ_doc = await event_occurrences_collection.find_one({"id": occ}, {"_id": 0})
    # only the `order` release subtracted; the `other` row untouched
    assert occ_doc["reserved_seats"] == 3, occ_doc["reserved_seats"]
    # other reservation row intact
    still = await event_seat_reservations_collection.find_one({"order_id": other})
    assert still is not None and still["qty"] == 3
    await _cleanup()


async def t12_get_remaining():
    occ = PREFIX + "occ12"
    order = PREFIX + "ord12"
    await _seed_occurrence(occ, capacity=5)

    rem0 = await get_occurrence_remaining(ORG, occ)
    assert rem0 == 5
    await try_reserve_event_seats(order_id=order, org_id=ORG, occurrence_id=occ, qty=3)
    rem1 = await get_occurrence_remaining(ORG, occ)
    assert rem1 == 2
    # unlimited returns None
    occ_u = PREFIX + "occ12u"
    await _seed_occurrence(occ_u, capacity=None)
    assert await get_occurrence_remaining(ORG, occ_u) is None
    # missing returns None
    assert await get_occurrence_remaining(ORG, PREFIX + "nope") is None
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 reserve basic", t01_reserve_basic),
    ("t02 idempotent same qty", t02_idempotent_same_qty),
    ("t03 qty mismatch same order", t03_qty_mismatch_same_order),
    ("t04 capacity enforced", t04_capacity_enforced),
    ("t05 unlimited capacity", t05_unlimited_capacity),
    ("t06 status blocks reservation", t06_status_blocks),
    ("t07 occurrence missing", t07_occurrence_missing),
    ("t08 org isolation", t08_org_isolation),
    ("t09 invalid qty", t09_invalid_qty),
    ("t10 10-way concurrent race for last seat", t10_concurrent_race_last_seat),
    ("t11 release scoped to own rows", t11_release_restores_seats),
    ("t12 get_remaining", t12_get_remaining),
]


async def run_all() -> int:
    await _cleanup()
    passed = 0
    failed = 0
    for name, fn in TESTS:
        try:
            await fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {name}: {exc}")
            traceback.print_exc()
            failed += 1
            await _cleanup()
    await _cleanup()
    print()
    print(f"{passed}/{len(TESTS)} PASSED, {failed} FAILED")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_all()))
