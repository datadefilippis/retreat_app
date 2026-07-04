#!/usr/bin/env python3
"""
E5 — Tickets router test suite.

Covers the HTTP layer on top of the E4 ticket_service primitives:
  - POST /tickets/check-in happy path + scope isolation + occurrence lock
  - GET  /tickets/occurrence/{id} default + include_voided
  - GET  /tickets/occurrence/{id}/stats counts correctly

Uses FastAPI dependency overrides for auth (no live user) so the test
suite stays hermetic. No HTTP client — calls the handler functions
directly through the router, same style as test_event_landing.py.

Invocation:
  cd backend && ./venv/bin/python tests/test_tickets_router.py
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
    issued_tickets_collection,
    event_occurrences_collection,
    products_collection,
    organizations_collection,
)
from models.common import utc_now  # noqa: E402
from services.ticket_service import issue_tickets_for_order, void_tickets_for_order  # noqa: E402

PREFIX = "test_e5_"
ORG = PREFIX + "org"


async def _cleanup():
    await issued_tickets_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await event_occurrences_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await products_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await organizations_collection.delete_many({"id": {"$regex": f"^{PREFIX}"}})


async def _seed(occ_id: str, order_id: str, qty: int = 2):
    await event_occurrences_collection.insert_one({
        "id": occ_id, "organization_id": ORG, "product_id": PREFIX + "prod",
        "start_at": "2027-06-01T20:00:00", "status": "published",
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await products_collection.insert_one({
        "id": PREFIX + "prod", "organization_id": ORG, "name": "Evento test",
        "item_type": "event_ticket", "is_active": True, "is_published": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    order = {
        "id": order_id, "organization_id": ORG,
        "customer_name": "Mario", "customer_email": "mario@example.com",
        "items": [{
            "product_id": PREFIX + "prod", "occurrence_id": occ_id,
            "item_type": "event_ticket", "quantity": qty,
        }],
    }
    return await issue_tickets_for_order(order, ORG)


def _current_user():
    """Fake authenticated user object matching get_current_user shape."""
    return {"organization_id": ORG, "email": "admin@example.com", "id": "u1"}


# ── Tests ──────────────────────────────────────────────────────────────────


async def t01_check_in_ok():
    from routers.tickets import check_in, CheckInRequest
    await _cleanup()
    tickets = await _seed(PREFIX + "occ1", PREFIX + "o1", qty=1)
    code = tickets[0]["code"]
    resp = await check_in(CheckInRequest(code=code), current_user=_current_user())
    assert resp.ok and resp.reason == "ok"
    assert resp.ticket["status"] == "checked_in"
    await _cleanup()


async def t02_check_in_already():
    from routers.tickets import check_in, CheckInRequest
    await _cleanup()
    tickets = await _seed(PREFIX + "occ2", PREFIX + "o2", qty=1)
    code = tickets[0]["code"]
    await check_in(CheckInRequest(code=code), current_user=_current_user())
    resp = await check_in(CheckInRequest(code=code), current_user=_current_user())
    assert resp.ok and resp.reason == "already_checked_in"
    await _cleanup()


async def t03_check_in_voided():
    from routers.tickets import check_in, CheckInRequest
    await _cleanup()
    tickets = await _seed(PREFIX + "occ3", PREFIX + "o3", qty=1)
    await void_tickets_for_order(PREFIX + "o3", ORG)
    resp = await check_in(CheckInRequest(code=tickets[0]["code"]),
                          current_user=_current_user())
    assert not resp.ok and resp.reason == "voided"
    await _cleanup()


async def t04_check_in_not_found():
    from routers.tickets import check_in, CheckInRequest
    await _cleanup()
    resp = await check_in(CheckInRequest(code="EVT-AAAA-9999"),
                          current_user=_current_user())
    assert not resp.ok and resp.reason == "not_found"
    await _cleanup()


async def t05_check_in_cross_org_isolation():
    """Caller in org A cannot check in a ticket belonging to org B."""
    from routers.tickets import check_in, CheckInRequest
    await _cleanup()
    tickets = await _seed(PREFIX + "occ5", PREFIX + "o5", qty=1)
    # Auth as a different org
    other_user = {"organization_id": PREFIX + "ORG_OTHER",
                  "email": "x@x.com", "id": "u2"}
    resp = await check_in(CheckInRequest(code=tickets[0]["code"]),
                          current_user=other_user)
    assert not resp.ok and resp.reason == "not_found"
    await _cleanup()


async def t06_check_in_occurrence_lock():
    """Scanner locked to occurrence X rejects a valid code from
    occurrence Y."""
    from routers.tickets import check_in, CheckInRequest
    await _cleanup()
    await _seed(PREFIX + "occA", PREFIX + "oA", qty=1)
    ticketsB = await _seed(PREFIX + "occB", PREFIX + "oB", qty=1)
    code_b = ticketsB[0]["code"]
    # Lock scanner to occA, scan a code from occB
    resp = await check_in(
        CheckInRequest(code=code_b, occurrence_id=PREFIX + "occA"),
        current_user=_current_user(),
    )
    assert not resp.ok and resp.reason == "wrong_occurrence"
    await _cleanup()


async def t07_list_attendance_sorted_excludes_voided():
    from routers.tickets import list_attendance
    await _cleanup()
    await _seed(PREFIX + "occ7", PREFIX + "o7a", qty=2)
    await _seed(PREFIX + "occ7", PREFIX + "o7b", qty=1)
    await void_tickets_for_order(PREFIX + "o7b", ORG)
    res = await list_attendance(PREFIX + "occ7", include_voided=False,
                                current_user=_current_user())
    # 2 active tickets only
    assert res["total"] == 2
    tickets = res["tickets"]
    # Ordered by seat_index ASC
    assert [t["seat_index"] for t in tickets] == [1, 2]
    # Include voided -> 3 total
    res2 = await list_attendance(PREFIX + "occ7", include_voided=True,
                                 current_user=_current_user())
    assert res2["total"] == 3
    await _cleanup()


async def t08_attendance_stats():
    from routers.tickets import attendance_stats, check_in, CheckInRequest
    await _cleanup()
    tickets_a = await _seed(PREFIX + "occ8", PREFIX + "o8a", qty=3)
    tickets_b = await _seed(PREFIX + "occ8", PREFIX + "o8b", qty=2)
    # Check in 2 of order A
    await check_in(CheckInRequest(code=tickets_a[0]["code"]),
                   current_user=_current_user())
    await check_in(CheckInRequest(code=tickets_a[1]["code"]),
                   current_user=_current_user())
    # Void order B (2 voided)
    await void_tickets_for_order(PREFIX + "o8b", ORG)

    stats = await attendance_stats(PREFIX + "occ8", current_user=_current_user())
    assert stats.issued == 5
    assert stats.checked_in == 2
    assert stats.voided == 2
    assert stats.valid == 1
    assert stats.remaining == 1
    await _cleanup()


async def t09_stats_empty():
    from routers.tickets import attendance_stats
    await _cleanup()
    stats = await attendance_stats(PREFIX + "ghost_occ",
                                   current_user=_current_user())
    assert stats.issued == 0 and stats.valid == 0 and stats.checked_in == 0
    await _cleanup()


async def t10_list_attendance_empty():
    from routers.tickets import list_attendance
    await _cleanup()
    res = await list_attendance(PREFIX + "ghost_occ", current_user=_current_user())
    assert res["total"] == 0 and res["tickets"] == []
    await _cleanup()


async def t11_check_in_code_normalized():
    """Codes dictated in lowercase with extra whitespace still work."""
    from routers.tickets import check_in, CheckInRequest
    await _cleanup()
    tickets = await _seed(PREFIX + "occ11", PREFIX + "o11", qty=1)
    original = tickets[0]["code"]  # EVT-XXXX-XXXX (uppercase)
    # Simulate a messy typed code — check_in_ticket uppercases + strips
    messy = "  " + original.lower() + "  "
    resp = await check_in(CheckInRequest(code=messy), current_user=_current_user())
    assert resp.ok and resp.reason == "ok"
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 POST /check-in ok", t01_check_in_ok),
    ("t02 POST /check-in already_checked_in", t02_check_in_already),
    ("t03 POST /check-in voided", t03_check_in_voided),
    ("t04 POST /check-in not_found", t04_check_in_not_found),
    ("t05 POST /check-in cross-org isolation", t05_check_in_cross_org_isolation),
    ("t06 POST /check-in occurrence lock -> wrong_occurrence", t06_check_in_occurrence_lock),
    ("t07 GET /occurrence list sorted, excludes voided by default", t07_list_attendance_sorted_excludes_voided),
    ("t08 GET /occurrence/stats counts by status", t08_attendance_stats),
    ("t09 GET /occurrence/stats empty occurrence -> zeros", t09_stats_empty),
    ("t10 GET /occurrence empty list -> total 0", t10_list_attendance_empty),
    ("t11 POST /check-in normalizes messy code", t11_check_in_code_normalized),
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
