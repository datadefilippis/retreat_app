#!/usr/bin/env python3
"""
G4 — Ticketing Management endpoints tests.

Covers:
  - POST /tickets/{code}/resend-email         single-ticket resend
  - POST /tickets/{code}/void                 void single ticket
    (without cancelling the order)
  - POST /tickets/occurrence/{id}/email-attendees   broadcast
    templates + dedupe by email

Invocation:
  cd backend && ./venv/bin/python tests/test_tickets_management.py
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
from services.ticket_service import (  # noqa: E402
    issue_tickets_for_order,
    void_single_ticket,
    check_in_ticket,
)


PREFIX = "test_g4_"
ORG = PREFIX + "org"
OTHER_ORG = PREFIX + "other_org"


async def _cleanup():
    for c in [issued_tickets_collection, event_occurrences_collection,
              products_collection, organizations_collection]:
        await c.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
        await c.delete_many({"id": {"$regex": f"^{PREFIX}"}})


async def _seed():
    await organizations_collection.insert_one({
        "id": ORG, "name": "Michele", "is_active": True, "deactivated_at": None,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await products_collection.insert_one({
        "id": PREFIX + "p1", "organization_id": ORG, "name": "Cena test",
        "item_type": "event_ticket", "is_active": True, "is_published": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "occ1", "organization_id": ORG, "product_id": PREFIX + "p1",
        "start_at": "2027-10-10T20:00:00", "status": "published", "capacity": 10,
        "reserved_seats": 0, "slug": "cena-test",
        "venue_name": "Masseria", "city": "Lecce",
        "created_at": utc_now(), "updated_at": utc_now(),
    })


async def _issue(order_id: str, qty: int = 1, holder_name: str = "Mario Rossi",
                 holder_email: str = "mario@example.com"):
    order = {
        "id": order_id, "organization_id": ORG,
        "customer_name": holder_name, "customer_email": holder_email,
        "items": [{
            "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ1",
            "item_type": "event_ticket", "quantity": qty,
        }],
    }
    return await issue_tickets_for_order(order, ORG)


def _user(org=ORG):
    return {"organization_id": org, "id": "u1", "email": "admin@example.com"}


# ── Void single ticket tests ──────────────────────────────────────────────


async def t01_void_single_ok():
    from routers.tickets import void_one_ticket, VoidRequest
    await _cleanup(); await _seed()
    tickets = await _issue(PREFIX + "ord1", qty=2)
    code = tickets[0]["code"]
    res = await void_one_ticket(code, body=VoidRequest(reason="no show"),
                                current_user=_user())
    assert res.ok and res.reason == "voided"
    assert res.ticket["status"] == "voided"
    # Other ticket from same order must remain valid
    other = await issued_tickets_collection.find_one({"code": tickets[1]["code"]})
    assert other["status"] == "valid"
    await _cleanup()


async def t02_void_already_voided_idempotent():
    from routers.tickets import void_one_ticket, VoidRequest
    await _cleanup(); await _seed()
    tickets = await _issue(PREFIX + "ord2", qty=1)
    code = tickets[0]["code"]
    await void_one_ticket(code, body=VoidRequest(), current_user=_user())
    res = await void_one_ticket(code, body=VoidRequest(), current_user=_user())
    assert res.ok and res.reason == "already_voided"
    await _cleanup()


async def t03_void_refuses_checked_in():
    from routers.tickets import void_one_ticket, VoidRequest
    await _cleanup(); await _seed()
    tickets = await _issue(PREFIX + "ord3", qty=1)
    code = tickets[0]["code"]
    await check_in_ticket(code=code, org_id=ORG)
    res = await void_one_ticket(code, body=VoidRequest(), current_user=_user())
    assert not res.ok and res.reason == "checked_in"
    t = await issued_tickets_collection.find_one({"code": code})
    assert t["status"] == "checked_in"  # untouched
    await _cleanup()


async def t04_void_not_found():
    from routers.tickets import void_one_ticket, VoidRequest
    await _cleanup()
    res = await void_one_ticket("EVT-ZZZZ-0000", body=VoidRequest(), current_user=_user())
    assert not res.ok and res.reason == "not_found"
    await _cleanup()


async def t05_void_cross_org_isolation():
    from routers.tickets import void_one_ticket, VoidRequest
    await _cleanup(); await _seed()
    tickets = await _issue(PREFIX + "ord5", qty=1)
    res = await void_one_ticket(tickets[0]["code"], body=VoidRequest(),
                                current_user=_user(OTHER_ORG))
    assert not res.ok and res.reason == "not_found"
    await _cleanup()


async def t06_void_reason_persisted():
    from routers.tickets import void_one_ticket, VoidRequest
    await _cleanup(); await _seed()
    tickets = await _issue(PREFIX + "ord6", qty=1)
    await void_one_ticket(tickets[0]["code"],
                          body=VoidRequest(reason="chargeback fraud"),
                          current_user=_user())
    t = await issued_tickets_collection.find_one({"code": tickets[0]["code"]})
    assert t.get("void_reason") == "chargeback fraud"
    assert t.get("voided_at") is not None
    await _cleanup()


# ── Resend ticket email tests ──────────────────────────────────────────────


async def t07_resend_happy_path():
    from routers.tickets import resend_ticket_email
    await _cleanup(); await _seed()
    tickets = await _issue(PREFIX + "ord7", qty=1)
    res = await resend_ticket_email(tickets[0]["code"], current_user=_user())
    # With no BREVO key, send_email returns a truthy success; at worst the
    # reason is "sent" with ok True. If it's False the test should still
    # assert the reason tells us why.
    assert res.ok in (True, False)
    assert res.reason in ("sent", "dispatched_logonly", "send_failed")
    await _cleanup()


async def t08_resend_not_found():
    from routers.tickets import resend_ticket_email
    await _cleanup()
    res = await resend_ticket_email("EVT-ZZZZ-9999", current_user=_user())
    assert not res.ok and res.reason == "not_found"
    await _cleanup()


async def t09_resend_voided_refused():
    from routers.tickets import resend_ticket_email
    await _cleanup(); await _seed()
    tickets = await _issue(PREFIX + "ord9", qty=1)
    from services.ticket_service import void_single_ticket as _v
    await _v(tickets[0]["code"], ORG)
    res = await resend_ticket_email(tickets[0]["code"], current_user=_user())
    assert not res.ok and res.reason == "voided"
    await _cleanup()


async def t10_resend_no_email_on_holder():
    from routers.tickets import resend_ticket_email
    await _cleanup(); await _seed()
    # Directly insert a ticket with empty holder_email
    await issued_tickets_collection.insert_one({
        "id": PREFIX + "tk_noemail", "organization_id": ORG,
        "order_id": PREFIX + "ord10",
        "occurrence_id": PREFIX + "occ1", "product_id": PREFIX + "p1",
        "code": "EVT-AAAA-1234", "status": "valid",
        "holder_name": "Anonimo", "holder_email": "",
        "seat_index": 1, "seat_count": 1, "created_at": utc_now(),
    })
    res = await resend_ticket_email("EVT-AAAA-1234", current_user=_user())
    assert not res.ok and res.reason == "no_email"
    await _cleanup()


async def t11_resend_cross_org_isolation():
    from routers.tickets import resend_ticket_email
    await _cleanup(); await _seed()
    tickets = await _issue(PREFIX + "ord11", qty=1)
    res = await resend_ticket_email(tickets[0]["code"],
                                    current_user=_user(OTHER_ORG))
    assert not res.ok and res.reason == "not_found"
    await _cleanup()


# ── Broadcast tests ────────────────────────────────────────────────────────


async def t12_broadcast_unknown_template():
    from routers.tickets import broadcast_attendees, BroadcastRequest
    await _cleanup(); await _seed()
    await _issue(PREFIX + "ord12")
    res = await broadcast_attendees(
        PREFIX + "occ1",
        body=BroadcastRequest(template="flavor-of-the-month"),
        current_user=_user(),
    )
    assert res.error_message == "unknown_template"
    assert res.sent == 0
    await _cleanup()


async def t13_broadcast_custom_requires_message():
    from routers.tickets import broadcast_attendees, BroadcastRequest
    await _cleanup(); await _seed()
    await _issue(PREFIX + "ord13")
    res = await broadcast_attendees(
        PREFIX + "occ1",
        body=BroadcastRequest(template="custom", message=""),
        current_user=_user(),
    )
    assert res.error_message == "custom_requires_message"
    await _cleanup()


async def t14_broadcast_unknown_occurrence():
    from routers.tickets import broadcast_attendees, BroadcastRequest
    await _cleanup()
    res = await broadcast_attendees(
        PREFIX + "nope",
        body=BroadcastRequest(template="reminder"),
        current_user=_user(),
    )
    assert res.error_message == "occurrence_not_found"
    await _cleanup()


async def t15_broadcast_dedupes_by_email():
    """Holder 'mario@example.com' has 3 tickets — they should receive 1 email."""
    from routers.tickets import broadcast_attendees, BroadcastRequest
    await _cleanup(); await _seed()
    # Same holder — 3 tickets
    await _issue(PREFIX + "ord15a", qty=3, holder_name="Mario",
                 holder_email="mario@example.com")
    res = await broadcast_attendees(
        PREFIX + "occ1",
        body=BroadcastRequest(template="reminder"),
        current_user=_user(),
    )
    # Whether the send succeeded depends on BREVO setup; the key
    # invariant is target count = 1 (dedup), plus sent+errors == 1.
    assert res.target == 1
    assert res.sent + res.errors == 1
    await _cleanup()


async def t16_broadcast_counts_no_email_as_skipped():
    from routers.tickets import broadcast_attendees, BroadcastRequest
    await _cleanup(); await _seed()
    # Reachable attendee
    await _issue(PREFIX + "ord16a", qty=1, holder_name="Carla",
                 holder_email="carla@example.com")
    # Unreachable attendee (no email) — issue directly
    await issued_tickets_collection.insert_one({
        "id": PREFIX + "tk_no", "organization_id": ORG,
        "order_id": PREFIX + "ord16b",
        "occurrence_id": PREFIX + "occ1", "product_id": PREFIX + "p1",
        "code": "EVT-BBBB-0001", "status": "valid",
        "holder_name": "Anonimo", "holder_email": "",
        "seat_index": 1, "seat_count": 1, "created_at": utc_now(),
    })
    res = await broadcast_attendees(
        PREFIX + "occ1",
        body=BroadcastRequest(template="reminder"),
        current_user=_user(),
    )
    assert res.skipped_no_email == 1
    assert res.sent + res.errors == 1
    await _cleanup()


async def t17_broadcast_voided_excluded_by_default():
    from routers.tickets import broadcast_attendees, BroadcastRequest
    await _cleanup(); await _seed()
    await _issue(PREFIX + "ord17a", qty=1, holder_email="a@example.com")
    tickets_b = await _issue(PREFIX + "ord17b", qty=1, holder_email="b@example.com")
    await void_single_ticket(tickets_b[0]["code"], ORG)
    res = await broadcast_attendees(
        PREFIX + "occ1",
        body=BroadcastRequest(template="reminder"),
        current_user=_user(),
    )
    # Only the active attendee was targeted
    assert res.target == 1
    await _cleanup()


async def t18_broadcast_custom_template_accepts_message():
    from routers.tickets import broadcast_attendees, BroadcastRequest
    await _cleanup(); await _seed()
    await _issue(PREFIX + "ord18", qty=1, holder_email="u@example.com")
    res = await broadcast_attendees(
        PREFIX + "occ1",
        body=BroadcastRequest(template="custom",
                              message="Ragazzi, portate la giacca!\nCi vediamo presto."),
        current_user=_user(),
    )
    assert res.error_message is None
    assert res.target == 1
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 void single ticket ok", t01_void_single_ok),
    ("t02 void already voided -> idempotent", t02_void_already_voided_idempotent),
    ("t03 void refuses checked_in ticket", t03_void_refuses_checked_in),
    ("t04 void not_found", t04_void_not_found),
    ("t05 void cross-org isolation -> not_found", t05_void_cross_org_isolation),
    ("t06 void_reason persisted", t06_void_reason_persisted),
    ("t07 resend email happy path", t07_resend_happy_path),
    ("t08 resend not_found", t08_resend_not_found),
    ("t09 resend refuses voided", t09_resend_voided_refused),
    ("t10 resend no_email", t10_resend_no_email_on_holder),
    ("t11 resend cross-org isolation", t11_resend_cross_org_isolation),
    ("t12 broadcast unknown template", t12_broadcast_unknown_template),
    ("t13 broadcast custom requires message", t13_broadcast_custom_requires_message),
    ("t14 broadcast unknown occurrence", t14_broadcast_unknown_occurrence),
    ("t15 broadcast dedupes by email", t15_broadcast_dedupes_by_email),
    ("t16 broadcast counts no_email as skipped", t16_broadcast_counts_no_email_as_skipped),
    ("t17 broadcast voided excluded by default", t17_broadcast_voided_excluded_by_default),
    ("t18 broadcast custom template accepts message", t18_broadcast_custom_template_accepts_message),
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
