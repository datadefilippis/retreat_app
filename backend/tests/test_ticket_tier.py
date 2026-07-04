#!/usr/bin/env python3
"""
E1 — Event ticket tier reservation test suite.

Focused checks on services.tier_capacity + services.event_capacity
in the multi-tier code path, plus CRUD + validator integration.

Invocation:
  cd backend && ./venv/bin/python tests/test_ticket_tier.py
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

from database import (  # noqa: E402
    event_occurrences_collection,
    event_ticket_tiers_collection,
    event_seat_reservations_collection,
)
from models.common import utc_now  # noqa: E402
from services.event_capacity import (  # noqa: E402
    try_reserve_event_seats,
    release_event_seats,
)
from services.tier_capacity import release_tier_seats  # noqa: E402

PREFIX = "test_e1_"
ORG = PREFIX + "org"
PRODUCT = PREFIX + "prod"


async def _cleanup():
    await event_occurrences_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await event_ticket_tiers_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await event_seat_reservations_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})


async def _seed_occurrence(occ_id: str, capacity, status="published", org=ORG):
    await event_occurrences_collection.delete_one({"id": occ_id})
    await event_occurrences_collection.insert_one({
        "id": occ_id,
        "organization_id": org,
        "product_id": PRODUCT,
        "start_at": "2027-01-01T20:00:00",
        "capacity": capacity,
        "status": status,
        "reserved_seats": 0,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    })


async def _seed_tier(tier_id, occ_id, label, price, capacity, org=ORG, is_active=True):
    await event_ticket_tiers_collection.delete_one({"id": tier_id})
    await event_ticket_tiers_collection.insert_one({
        "id": tier_id,
        "organization_id": org,
        "occurrence_id": occ_id,
        "label": label,
        "price": price,
        "capacity": capacity,
        "reserved_seats": 0,
        "sort_order": 0,
        "is_active": is_active,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    })


async def t01_mono_tier_backward_compat():
    """Reservation without tier_id runs the pre-E1 P7 flow unchanged."""
    occ = PREFIX + "occ01"
    await _seed_occurrence(occ, capacity=10)
    ok, reason, occ_after = await try_reserve_event_seats(
        order_id=PREFIX + "ord01", org_id=ORG, occurrence_id=occ, qty=2,
    )
    assert ok and reason == "reserved"
    assert occ_after["reserved_seats"] == 2
    # Idempotency row has tier_id=None
    row = await event_seat_reservations_collection.find_one(
        {"order_id": PREFIX + "ord01", "occurrence_id": occ},
        {"_id": 0},
    )
    assert row and row.get("tier_id") is None
    await _cleanup()


async def t02_reserve_with_tier_increments_both_counters():
    occ = PREFIX + "occ02"
    tier = PREFIX + "tier02"
    await _seed_occurrence(occ, capacity=30)
    await _seed_tier(tier, occ, label="VIP", price=50, capacity=10)

    ok, reason, occ_after = await try_reserve_event_seats(
        order_id=PREFIX + "ord02", org_id=ORG, occurrence_id=occ, qty=3,
        tier_id=tier,
    )
    assert ok and reason == "reserved"
    assert occ_after["reserved_seats"] == 3
    tier_doc = await event_ticket_tiers_collection.find_one({"id": tier}, {"_id": 0})
    assert tier_doc["reserved_seats"] == 3
    await _cleanup()


async def t03_tier_capacity_enforced():
    """3 VIP on capacity=3 then 4th request rejected with tier_sold_out."""
    occ = PREFIX + "occ03"
    tier = PREFIX + "tier03"
    await _seed_occurrence(occ, capacity=30)
    await _seed_tier(tier, occ, label="VIP", price=50, capacity=3)

    ok1, _, _ = await try_reserve_event_seats(
        order_id=PREFIX + "a", org_id=ORG, occurrence_id=occ, qty=2, tier_id=tier,
    )
    ok2, _, _ = await try_reserve_event_seats(
        order_id=PREFIX + "b", org_id=ORG, occurrence_id=occ, qty=1, tier_id=tier,
    )
    ok3, reason3, tier_doc = await try_reserve_event_seats(
        order_id=PREFIX + "c", org_id=ORG, occurrence_id=occ, qty=1, tier_id=tier,
    )
    assert ok1 and ok2
    assert not ok3 and reason3 == "tier_sold_out"
    # tier stuck at 3, no ghost idempotency row
    tier_now = await event_ticket_tiers_collection.find_one({"id": tier}, {"_id": 0})
    assert tier_now["reserved_seats"] == 3
    ghost = await event_seat_reservations_collection.find_one({"order_id": PREFIX + "c"})
    assert ghost is None
    await _cleanup()


async def t04_occurrence_capacity_still_enforced():
    """30 total, VIP=20 and Std=20 — cumulative > 30 should fail at occurrence."""
    occ = PREFIX + "occ04"
    vip = PREFIX + "vip04"
    std = PREFIX + "std04"
    await _seed_occurrence(occ, capacity=30)
    await _seed_tier(vip, occ, "VIP", 50, capacity=20)
    await _seed_tier(std, occ, "Standard", 20, capacity=20)

    # Fill 20 VIP
    ok1, _, _ = await try_reserve_event_seats(
        order_id=PREFIX + "v", org_id=ORG, occurrence_id=occ, qty=20, tier_id=vip,
    )
    # Fill 10 Std
    ok2, _, _ = await try_reserve_event_seats(
        order_id=PREFIX + "s1", org_id=ORG, occurrence_id=occ, qty=10, tier_id=std,
    )
    # Try 1 more Std — tier has room but occurrence is full
    ok3, reason3, _ = await try_reserve_event_seats(
        order_id=PREFIX + "s2", org_id=ORG, occurrence_id=occ, qty=1, tier_id=std,
    )
    assert ok1 and ok2
    assert not ok3 and reason3 == "occurrence_sold_out"
    # Std tier COMPENSATED — count stays at 10, not 11
    std_doc = await event_ticket_tiers_collection.find_one({"id": std}, {"_id": 0})
    assert std_doc["reserved_seats"] == 10, f"tier not compensated: {std_doc['reserved_seats']}"
    # Idempotency row for the failed order is gone
    ghost = await event_seat_reservations_collection.find_one({"order_id": PREFIX + "s2"})
    assert ghost is None
    await _cleanup()


async def t05_race_tier_last_seat():
    occ = PREFIX + "occ05"
    tier = PREFIX + "tier05"
    await _seed_occurrence(occ, capacity=10)
    await _seed_tier(tier, occ, "VIP", 50, capacity=1)

    async def attempt(i):
        return await try_reserve_event_seats(
            order_id=f"{PREFIX}race05_{i}", org_id=ORG,
            occurrence_id=occ, qty=1, tier_id=tier,
        )

    results = await asyncio.gather(*[attempt(i) for i in range(10)])
    winners = [r for r in results if r[0] and r[1] == "reserved"]
    losers = [r for r in results if not r[0]]
    assert len(winners) == 1, f"expected 1 winner, got {len(winners)}"
    assert all(r[1] == "tier_sold_out" for r in losers), [r[1] for r in losers]
    t = await event_ticket_tiers_collection.find_one({"id": tier}, {"_id": 0})
    assert t["reserved_seats"] == 1
    await _cleanup()


async def t06_idempotent_same_order_same_tier():
    occ = PREFIX + "occ06"
    tier = PREFIX + "tier06"
    await _seed_occurrence(occ, capacity=10)
    await _seed_tier(tier, occ, "VIP", 50, capacity=5)

    ok1, r1, _ = await try_reserve_event_seats(
        order_id=PREFIX + "ord06", org_id=ORG, occurrence_id=occ, qty=2, tier_id=tier,
    )
    ok2, r2, _ = await try_reserve_event_seats(
        order_id=PREFIX + "ord06", org_id=ORG, occurrence_id=occ, qty=2, tier_id=tier,
    )
    assert ok1 and r1 == "reserved"
    assert ok2 and r2 == "already_reserved"
    # Counter NOT double-incremented
    t = await event_ticket_tiers_collection.find_one({"id": tier}, {"_id": 0})
    assert t["reserved_seats"] == 2
    await _cleanup()


async def t07_same_order_two_tiers():
    """Michele compra 1 VIP + 1 Standard nello stesso cart: entrambi reserved, indipendenti."""
    occ = PREFIX + "occ07"
    vip = PREFIX + "vip07"
    std = PREFIX + "std07"
    await _seed_occurrence(occ, capacity=30)
    await _seed_tier(vip, occ, "VIP", 50, capacity=10)
    await _seed_tier(std, occ, "Standard", 20, capacity=20)

    ok1, r1, _ = await try_reserve_event_seats(
        order_id=PREFIX + "cart", org_id=ORG, occurrence_id=occ, qty=1, tier_id=vip,
    )
    ok2, r2, _ = await try_reserve_event_seats(
        order_id=PREFIX + "cart", org_id=ORG, occurrence_id=occ, qty=1, tier_id=std,
    )
    assert ok1 and r1 == "reserved"
    assert ok2 and r2 == "reserved"
    # Two separate idempotency rows with different tier_ids
    rows = await event_seat_reservations_collection.count_documents(
        {"order_id": PREFIX + "cart"},
    )
    assert rows == 2, f"expected 2 rows, got {rows}"
    # Occurrence counter sums both = 2
    occ_doc = await event_occurrences_collection.find_one({"id": occ}, {"_id": 0})
    assert occ_doc["reserved_seats"] == 2
    await _cleanup()


async def t08_qty_mismatch():
    occ = PREFIX + "occ08"
    tier = PREFIX + "tier08"
    await _seed_occurrence(occ, capacity=10)
    await _seed_tier(tier, occ, "VIP", 50, capacity=5)

    await try_reserve_event_seats(
        order_id=PREFIX + "ord08", org_id=ORG, occurrence_id=occ, qty=2, tier_id=tier,
    )
    ok, reason, _ = await try_reserve_event_seats(
        order_id=PREFIX + "ord08", org_id=ORG, occurrence_id=occ, qty=3, tier_id=tier,
    )
    assert not ok and reason == "qty_mismatch"
    # tier still at first qty
    t = await event_ticket_tiers_collection.find_one({"id": tier}, {"_id": 0})
    assert t["reserved_seats"] == 2
    await _cleanup()


async def t09_tier_inactive_rejected():
    occ = PREFIX + "occ09"
    tier = PREFIX + "tier09"
    await _seed_occurrence(occ, capacity=10)
    await _seed_tier(tier, occ, "VIP", 50, capacity=5, is_active=False)

    ok, reason, _ = await try_reserve_event_seats(
        order_id=PREFIX + "ord09", org_id=ORG, occurrence_id=occ, qty=1, tier_id=tier,
    )
    assert not ok and reason == "tier_inactive"
    await _cleanup()


async def t10_tier_not_found():
    occ = PREFIX + "occ10"
    await _seed_occurrence(occ, capacity=10)
    ok, reason, _ = await try_reserve_event_seats(
        order_id=PREFIX + "ord10", org_id=ORG, occurrence_id=occ, qty=1,
        tier_id=PREFIX + "ghost_tier",
    )
    assert not ok and reason == "tier_not_found"
    await _cleanup()


async def t11_release_restores_both_levels():
    occ = PREFIX + "occ11"
    vip = PREFIX + "vip11"
    std = PREFIX + "std11"
    await _seed_occurrence(occ, capacity=30)
    await _seed_tier(vip, occ, "VIP", 50, capacity=10)
    await _seed_tier(std, occ, "Std", 20, capacity=20)

    await try_reserve_event_seats(
        order_id=PREFIX + "o11", org_id=ORG, occurrence_id=occ, qty=2, tier_id=vip,
    )
    await try_reserve_event_seats(
        order_id=PREFIX + "o11", org_id=ORG, occurrence_id=occ, qty=3, tier_id=std,
    )
    # Other order that must not be touched
    await try_reserve_event_seats(
        order_id=PREFIX + "keep", org_id=ORG, occurrence_id=occ, qty=1, tier_id=vip,
    )

    # Release sequence like production (tier first, then occurrence).
    tier_released = await release_tier_seats(PREFIX + "o11", ORG)
    occ_released = await release_event_seats(PREFIX + "o11", ORG)
    assert tier_released == 2, f"tier releases {tier_released}"
    assert occ_released == 2, f"occurrence rows deleted {occ_released}"

    # VIP = 1 (only keep), Std = 0, Occ = 1
    v = await event_ticket_tiers_collection.find_one({"id": vip}, {"_id": 0})
    s = await event_ticket_tiers_collection.find_one({"id": std}, {"_id": 0})
    o = await event_occurrences_collection.find_one({"id": occ}, {"_id": 0})
    assert v["reserved_seats"] == 1, f"VIP leftover {v['reserved_seats']}"
    assert s["reserved_seats"] == 0, f"Std leftover {s['reserved_seats']}"
    assert o["reserved_seats"] == 1, f"Occ leftover {o['reserved_seats']}"
    # 'keep' idempotency row intact
    keep_row = await event_seat_reservations_collection.find_one({"order_id": PREFIX + "keep"})
    assert keep_row is not None
    await _cleanup()


async def t12_validator_preflight_tier_sold_out():
    """P3 validator returns structured tier_sold_out when remaining < requested."""
    from services.product_type_validators import validate_order_item

    class Item:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    occ = PREFIX + "occ12"
    tier = PREFIX + "tier12"
    await _seed_occurrence(occ, capacity=30)
    await _seed_tier(tier, occ, "VIP", 50, capacity=5)
    # Pre-fill 4 of 5 VIP via atomic primitive
    await try_reserve_event_seats(
        order_id=PREFIX + "prefill", org_id=ORG, occurrence_id=occ, qty=4, tier_id=tier,
    )

    r = await validate_order_item(
        Item(occurrence_id=occ, ticket_tier_id=tier, product_id=PRODUCT, quantity=3),
        {"item_type": "event_ticket", "id": PRODUCT},
        {"org_id": ORG},
    )
    assert not r.valid and r.reason == "tier_sold_out"
    assert r.context["remaining"] == 1 and r.context["requested"] == 3
    await _cleanup()


async def t13_validator_preflight_tier_not_found():
    from services.product_type_validators import validate_order_item

    class Item:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    occ = PREFIX + "occ13"
    await _seed_occurrence(occ, capacity=30)
    r = await validate_order_item(
        Item(occurrence_id=occ, ticket_tier_id=PREFIX + "nope", product_id=PRODUCT, quantity=1),
        {"item_type": "event_ticket", "id": PRODUCT},
        {"org_id": ORG},
    )
    assert not r.valid and r.reason == "tier_not_found"
    await _cleanup()


async def t14_mono_tier_p7_race_unaffected():
    """Regression guard: with no tier_id, P7 behavior is byte-identical."""
    occ = PREFIX + "occ14"
    await _seed_occurrence(occ, capacity=1)

    async def attempt(i):
        return await try_reserve_event_seats(
            order_id=f"{PREFIX}race14_{i}", org_id=ORG, occurrence_id=occ, qty=1,
        )

    results = await asyncio.gather(*[attempt(i) for i in range(10)])
    winners = [r for r in results if r[0] and r[1] == "reserved"]
    assert len(winners) == 1, f"expected 1 winner, got {len(winners)}"
    o = await event_occurrences_collection.find_one({"id": occ}, {"_id": 0})
    assert o["reserved_seats"] == 1
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 mono-tier backward-compat (no tier_id -> P7)", t01_mono_tier_backward_compat),
    ("t02 reserve with tier: both counters incremented", t02_reserve_with_tier_increments_both_counters),
    ("t03 tier capacity enforced", t03_tier_capacity_enforced),
    ("t04 occurrence capacity enforced, tier compensated on rollback", t04_occurrence_capacity_still_enforced),
    ("t05 race 10-way on last VIP seat", t05_race_tier_last_seat),
    ("t06 idempotent same order same tier", t06_idempotent_same_order_same_tier),
    ("t07 same order two tiers (Michele cart)", t07_same_order_two_tiers),
    ("t08 qty mismatch", t08_qty_mismatch),
    ("t09 tier inactive rejected", t09_tier_inactive_rejected),
    ("t10 tier not found", t10_tier_not_found),
    ("t11 release restores both levels, others intact", t11_release_restores_both_levels),
    ("t12 P3 validator tier_sold_out", t12_validator_preflight_tier_sold_out),
    ("t13 P3 validator tier_not_found", t13_validator_preflight_tier_not_found),
    ("t14 mono-tier P7 race unaffected", t14_mono_tier_p7_race_unaffected),
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
