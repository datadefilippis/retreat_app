#!/usr/bin/env python3
"""
P8 — Rental range reservation test suite.

Focused, deterministic checks on services.rental_availability.

Invocation:
  cd backend && ./venv/bin/python tests/test_rental_range_reservation.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from typing import Callable

os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_database")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import blocked_slots_collection  # noqa: E402
from services.rental_availability import (  # noqa: E402
    check_rental_range_available,
    try_reserve_rental_range,
    release_rental_range,
)

PREFIX = "test_p8_"
ORG = PREFIX + "org"
PRODUCT = PREFIX + "prod"


async def _cleanup():
    await blocked_slots_collection.delete_many(
        {"organization_id": {"$regex": f"^{PREFIX}"}}
    )
    # Also clean rows whose reference_id or product_id came from this suite
    # (stray cross-org overlap seeds).
    await blocked_slots_collection.delete_many(
        {"reference_id": {"$regex": f"^{PREFIX}"}}
    )
    await blocked_slots_collection.delete_many(
        {"product_id": {"$regex": f"^{PREFIX}"}}
    )


async def t01_reserve_basic():
    order = PREFIX + "ord01"
    ok, reason, info = await try_reserve_rental_range(
        order_id=order, org_id=ORG, product_id=PRODUCT,
        date_from="2026-09-01", date_to="2026-09-03",
    )
    assert ok and reason == "reserved", f"{ok} {reason}"
    assert info["days"] == 3
    rows = await blocked_slots_collection.count_documents(
        {"organization_id": ORG, "reference_id": order, "reason": "rental"},
    )
    assert rows == 3
    await _cleanup()


async def t02_idempotent_same_order_full_range():
    order = PREFIX + "ord02"
    await try_reserve_rental_range(
        order_id=order, org_id=ORG, product_id=PRODUCT,
        date_from="2026-09-10", date_to="2026-09-12",
    )
    ok, reason, info = await try_reserve_rental_range(
        order_id=order, org_id=ORG, product_id=PRODUCT,
        date_from="2026-09-10", date_to="2026-09-12",
    )
    assert ok and reason == "already_reserved", f"{ok} {reason}"
    assert info["days"] == 3
    # No extra rows
    rows = await blocked_slots_collection.count_documents(
        {"organization_id": ORG, "reference_id": order, "reason": "rental"},
    )
    assert rows == 3
    await _cleanup()


async def t03_conflict_overlap():
    # First order takes 10-12; second tries 12-14, overlaps on day 12.
    ok1, _, _ = await try_reserve_rental_range(
        order_id=PREFIX + "ord03a", org_id=ORG, product_id=PRODUCT,
        date_from="2026-09-10", date_to="2026-09-12",
    )
    ok2, reason2, conflict = await try_reserve_rental_range(
        order_id=PREFIX + "ord03b", org_id=ORG, product_id=PRODUCT,
        date_from="2026-09-12", date_to="2026-09-14",
    )
    assert ok1
    assert not ok2 and reason2 == "rental_day_conflict"
    # The conflict row belongs to order a, date 2026-09-12
    assert conflict["reference_id"] == PREFIX + "ord03a"
    assert conflict["date"] == "2026-09-12"
    # Partial insert rolled back: only order a's 3 days remain
    rows = await blocked_slots_collection.count_documents(
        {"organization_id": ORG, "reason": "rental", "product_id": PRODUCT},
    )
    assert rows == 3, f"expected 3, got {rows}"
    await _cleanup()


async def t04_product_isolation():
    # Same dates, different product_id → both succeed
    await try_reserve_rental_range(
        order_id=PREFIX + "ord04a", org_id=ORG, product_id=PRODUCT + "_A",
        date_from="2026-09-20", date_to="2026-09-21",
    )
    ok, reason, _ = await try_reserve_rental_range(
        order_id=PREFIX + "ord04b", org_id=ORG, product_id=PRODUCT + "_B",
        date_from="2026-09-20", date_to="2026-09-21",
    )
    assert ok and reason == "reserved"
    await _cleanup()


async def t05_org_isolation():
    await try_reserve_rental_range(
        order_id=PREFIX + "ord05a", org_id=ORG + "_A", product_id=PRODUCT,
        date_from="2026-09-22", date_to="2026-09-22",
    )
    ok, reason, _ = await try_reserve_rental_range(
        order_id=PREFIX + "ord05b", org_id=ORG + "_B", product_id=PRODUCT,
        date_from="2026-09-22", date_to="2026-09-22",
    )
    assert ok and reason == "reserved"
    await _cleanup()


async def t06_invalid_range():
    for (df, dt) in [(None, "2026-09-01"), ("2026-09-05", "2026-09-01"), ("bad", "2026-09-01")]:
        ok, reason, _ = await try_reserve_rental_range(
            order_id=PREFIX + "ord06", org_id=ORG, product_id=PRODUCT,
            date_from=df, date_to=dt,
        )
        assert not ok, f"{df}/{dt} accepted"
        assert reason == "invalid_date_range", reason
    await _cleanup()


async def t07_booking_blocks_rental_day():
    # Seed a booking block on 2026-10-05 in the product's calendar
    await blocked_slots_collection.insert_one({
        "id": PREFIX + "booking_block",
        "organization_id": ORG,
        "product_id": PRODUCT,
        "date": "2026-10-05",
        "start_time": "10:00",
        "end_time": "11:00",
        "reason": "booking",
        "reference_id": PREFIX + "other_order",
        "created_at": __import__("datetime").datetime.utcnow(),
    })
    ok, reason, _ = await try_reserve_rental_range(
        order_id=PREFIX + "ord07", org_id=ORG, product_id=PRODUCT,
        date_from="2026-10-04", date_to="2026-10-06",
    )
    assert not ok and reason == "rental_day_conflict"
    # No partial rental rows left
    rows = await blocked_slots_collection.count_documents(
        {"organization_id": ORG, "reason": "rental", "reference_id": PREFIX + "ord07"},
    )
    assert rows == 0
    await _cleanup()


async def t08_pre_flight_check():
    # Seed: reserve order A for 2026-11-01..02
    await try_reserve_rental_range(
        order_id=PREFIX + "ord08a", org_id=ORG, product_id=PRODUCT,
        date_from="2026-11-01", date_to="2026-11-02",
    )
    avail, reason, conflict = await check_rental_range_available(
        ORG, PRODUCT, "2026-11-02", "2026-11-05",
    )
    assert not avail and reason == "rental_day_conflict"
    assert conflict["date"] == "2026-11-02"
    # Non-overlapping check
    avail2, reason2, _ = await check_rental_range_available(
        ORG, PRODUCT, "2026-11-03", "2026-11-05",
    )
    assert avail2 and reason2 == "available"
    await _cleanup()


async def t09_concurrent_race_same_range():
    async def attempt(i):
        return await try_reserve_rental_range(
            order_id=f"{PREFIX}race09_{i}", org_id=ORG, product_id=PRODUCT,
            date_from="2026-12-01", date_to="2026-12-03",
        )

    results = await asyncio.gather(*[attempt(i) for i in range(10)])
    winners = [r for r in results if r[0]]
    losers = [r for r in results if not r[0]]
    # Race semantics: at most 1 winner. The primitive is conservative
    # (may false-negative under perfect concurrency — some losers may
    # all rollback and leave 0 winners). Retry always succeeds.
    assert len(winners) <= 1, f"impossible multi-winner: {len(winners)}"
    assert all(r[1] == "rental_day_conflict" for r in losers), [r[1] for r in losers]

    # Database invariant: either 0 or 3 rental rows, never partials
    rows = await blocked_slots_collection.count_documents(
        {"organization_id": ORG, "reason": "rental", "product_id": PRODUCT},
    )
    assert rows in (0, 3), f"partial insert: {rows}"

    if len(winners) == 0:
        # False negative case — retry deterministically succeeds
        ok, reason, _ = await try_reserve_rental_range(
            order_id=PREFIX + "race09_retry", org_id=ORG, product_id=PRODUCT,
            date_from="2026-12-01", date_to="2026-12-03",
        )
        assert ok and reason == "reserved", f"retry failed: {reason}"

    await _cleanup()


async def t10_single_day_rental():
    ok, reason, info = await try_reserve_rental_range(
        order_id=PREFIX + "ord10", org_id=ORG, product_id=PRODUCT,
        date_from="2027-01-15", date_to=None,
    )
    assert ok and reason == "reserved"
    assert info["days"] == 1
    await _cleanup()


async def t11_release_scoped():
    # Two orders, overlapping products but different ranges
    await try_reserve_rental_range(
        order_id=PREFIX + "ord11a", org_id=ORG, product_id=PRODUCT,
        date_from="2027-02-01", date_to="2027-02-03",
    )
    await try_reserve_rental_range(
        order_id=PREFIX + "ord11b", org_id=ORG, product_id=PRODUCT,
        date_from="2027-02-10", date_to="2027-02-11",
    )
    n = await release_rental_range(PREFIX + "ord11a", ORG)
    assert n == 3
    remain = await blocked_slots_collection.count_documents(
        {"organization_id": ORG, "reason": "rental", "product_id": PRODUCT},
    )
    assert remain == 2  # order b untouched
    await _cleanup()


async def t12_validator_integration():
    # P3 validator integrates rental pre-flight
    from services.product_type_validators import validate_order_item

    class Item:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    # Reserve 2027-03-01..02 for order X
    await try_reserve_rental_range(
        order_id=PREFIX + "ord12x", org_id=ORG, product_id=PRODUCT,
        date_from="2027-03-01", date_to="2027-03-02",
    )
    # Validator should now reject
    r = await validate_order_item(
        Item(rental_date_from="2027-03-01", rental_date_to="2027-03-02",
             product_id=PRODUCT, quantity=1),
        {"item_type": "rental", "id": PRODUCT},
        {"org_id": ORG},
    )
    assert not r.valid and r.reason == "rental_day_conflict"
    # Non-overlapping range passes
    r2 = await validate_order_item(
        Item(rental_date_from="2027-03-10", rental_date_to="2027-03-12",
             product_id=PRODUCT, quantity=1),
        {"item_type": "rental", "id": PRODUCT},
        {"org_id": ORG},
    )
    assert r2.valid, f"expected valid, got {r2.reason}"
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 reserve basic 3 days", t01_reserve_basic),
    ("t02 idempotent same order same range", t02_idempotent_same_order_full_range),
    ("t03 conflict on overlap rolls back", t03_conflict_overlap),
    ("t04 product isolation", t04_product_isolation),
    ("t05 org isolation", t05_org_isolation),
    ("t06 invalid date range", t06_invalid_range),
    ("t07 booking block blocks rental day", t07_booking_blocks_rental_day),
    ("t08 pre-flight check", t08_pre_flight_check),
    ("t09 10-way concurrent race on same range", t09_concurrent_race_same_range),
    ("t10 single day rental", t10_single_day_rental),
    ("t11 release scoped to own rows", t11_release_scoped),
    ("t12 P3 validator integration", t12_validator_integration),
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
