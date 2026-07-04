#!/usr/bin/env python3
"""
P10 — Physical stock service test suite.

Invocation:
  cd backend && ./venv/bin/python tests/test_stock_service.py
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

from database import products_collection  # noqa: E402
from models.common import utc_now  # noqa: E402
from services.stock_service import (  # noqa: E402
    check_stock_available,
    try_decrement_stock,
    restore_stock_for_order,
)

PREFIX = "test_p10_"
ORG = PREFIX + "org"


async def _cleanup():
    await products_collection.delete_many(
        {"organization_id": {"$regex": f"^{PREFIX}"}}
    )


async def _seed_product(pid: str, stock, org=ORG):
    await products_collection.delete_one({"id": pid})
    doc = {
        "id": pid,
        "organization_id": org,
        "name": pid,
        "price": 10.0,
        "item_type": "physical",
        "stock_quantity": stock,
        "category_id": PREFIX + "cat",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    await products_collection.insert_one(doc)


async def t01_check_available():
    pid = PREFIX + "p01"
    await _seed_product(pid, stock=5)
    status, rem = await check_stock_available(ORG, pid, 3)
    assert status == "available" and rem == 5
    await _cleanup()


async def t02_check_insufficient():
    pid = PREFIX + "p02"
    await _seed_product(pid, stock=2)
    status, rem = await check_stock_available(ORG, pid, 5)
    assert status == "insufficient" and rem == 2
    await _cleanup()


async def t03_check_untracked():
    pid = PREFIX + "p03"
    await _seed_product(pid, stock=None)
    status, rem = await check_stock_available(ORG, pid, 100)
    assert status == "untracked" and rem is None
    await _cleanup()


async def t04_check_not_found():
    status, rem = await check_stock_available(ORG, PREFIX + "ghost", 1)
    assert status == "not_found" and rem is None
    await _cleanup()


async def t05_check_invalid_qty():
    for bad in (0, -1, 1.5, "3"):
        status, _ = await check_stock_available(ORG, PREFIX + "anything", bad)
        assert status == "invalid_qty", f"bad={bad!r}"
    await _cleanup()


async def t06_decrement_basic():
    pid = PREFIX + "p06"
    await _seed_product(pid, stock=10)
    ok, reason, rem = await try_decrement_stock(
        order_id=PREFIX + "o06", org_id=ORG, product_id=pid, qty=3,
    )
    assert ok and reason == "decremented"
    assert rem == 7
    db = await products_collection.find_one({"id": pid}, {"_id": 0, "stock_quantity": 1})
    assert db["stock_quantity"] == 7
    await _cleanup()


async def t07_decrement_insufficient():
    pid = PREFIX + "p07"
    await _seed_product(pid, stock=2)
    ok, reason, rem = await try_decrement_stock(
        order_id=PREFIX + "o07", org_id=ORG, product_id=pid, qty=5,
    )
    assert not ok and reason == "insufficient_stock"
    assert rem == 2
    # Stock unchanged
    db = await products_collection.find_one({"id": pid}, {"_id": 0, "stock_quantity": 1})
    assert db["stock_quantity"] == 2
    await _cleanup()


async def t08_decrement_untracked_is_success_noop():
    pid = PREFIX + "p08"
    await _seed_product(pid, stock=None)
    ok, reason, rem = await try_decrement_stock(
        order_id=PREFIX + "o08", org_id=ORG, product_id=pid, qty=1000,
    )
    assert ok and reason == "untracked"
    assert rem is None
    db = await products_collection.find_one({"id": pid}, {"_id": 0, "stock_quantity": 1})
    assert db["stock_quantity"] is None
    await _cleanup()


async def t09_decrement_not_found():
    ok, reason, _ = await try_decrement_stock(
        order_id=PREFIX + "o09", org_id=ORG,
        product_id=PREFIX + "ghost", qty=1,
    )
    assert not ok and reason == "not_found"
    await _cleanup()


async def t10_concurrent_race_last_unit():
    pid = PREFIX + "p10"
    await _seed_product(pid, stock=1)

    async def attempt(i):
        return await try_decrement_stock(
            order_id=f"{PREFIX}race10_{i}", org_id=ORG, product_id=pid, qty=1,
        )

    results = await asyncio.gather(*[attempt(i) for i in range(10)])
    winners = [r for r in results if r[0] and r[1] == "decremented"]
    losers = [r for r in results if not r[0]]
    assert len(winners) == 1, f"expected 1 winner, got {len(winners)}"
    assert all(r[1] == "insufficient_stock" for r in losers), [r[1] for r in losers]

    db = await products_collection.find_one({"id": pid}, {"_id": 0, "stock_quantity": 1})
    assert db["stock_quantity"] == 0
    await _cleanup()


async def t11_restore_basic():
    pid = PREFIX + "p11"
    await _seed_product(pid, stock=10)
    await try_decrement_stock(
        order_id=PREFIX + "o11", org_id=ORG, product_id=pid, qty=4,
    )
    db = await products_collection.find_one({"id": pid}, {"_id": 0, "stock_quantity": 1})
    assert db["stock_quantity"] == 6

    restored = await restore_stock_for_order(
        PREFIX + "o11", ORG,
        [{"product_id": pid, "quantity": 4}],
    )
    assert restored == 1
    db = await products_collection.find_one({"id": pid}, {"_id": 0, "stock_quantity": 1})
    assert db["stock_quantity"] == 10
    await _cleanup()


async def t12_restore_skips_untracked():
    pid = PREFIX + "p12"
    await _seed_product(pid, stock=None)
    restored = await restore_stock_for_order(
        PREFIX + "o12", ORG,
        [{"product_id": pid, "quantity": 4}],
    )
    assert restored == 0  # untracked → skipped
    db = await products_collection.find_one({"id": pid}, {"_id": 0, "stock_quantity": 1})
    assert db["stock_quantity"] is None
    await _cleanup()


async def t13_validator_integration():
    from services.product_type_validators import validate_order_item

    class Item:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    pid = PREFIX + "p13"
    await _seed_product(pid, stock=3)

    # Physical within stock → valid
    r = await validate_order_item(
        Item(quantity=2, product_id=pid),
        {"item_type": "physical", "id": pid},
        {"org_id": ORG},
    )
    assert r.valid, f"got {r.reason}"

    # Physical exceeding stock → rejected with structured reason
    r2 = await validate_order_item(
        Item(quantity=10, product_id=pid),
        {"item_type": "physical", "id": pid},
        {"org_id": ORG},
    )
    assert not r2.valid and r2.reason == "insufficient_stock", f"got {r2.reason}"
    assert r2.context["remaining"] == 3 and r2.context["requested"] == 10

    # Untracked product → passes
    pid_u = PREFIX + "p13u"
    await _seed_product(pid_u, stock=None)
    r3 = await validate_order_item(
        Item(quantity=1000, product_id=pid_u),
        {"item_type": "physical", "id": pid_u},
        {"org_id": ORG},
    )
    assert r3.valid
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 check_stock_available tracked sufficient", t01_check_available),
    ("t02 check_stock_available insufficient", t02_check_insufficient),
    ("t03 check_stock_available untracked", t03_check_untracked),
    ("t04 check_stock_available not_found", t04_check_not_found),
    ("t05 check_stock_available invalid qty", t05_check_invalid_qty),
    ("t06 try_decrement_stock basic", t06_decrement_basic),
    ("t07 try_decrement_stock insufficient", t07_decrement_insufficient),
    ("t08 try_decrement_stock untracked no-op success", t08_decrement_untracked_is_success_noop),
    ("t09 try_decrement_stock not_found", t09_decrement_not_found),
    ("t10 concurrent race for last unit", t10_concurrent_race_last_unit),
    ("t11 restore_stock_for_order basic", t11_restore_basic),
    ("t12 restore skips untracked", t12_restore_skips_untracked),
    ("t13 P3 validator integration", t13_validator_integration),
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
