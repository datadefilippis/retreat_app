#!/usr/bin/env python3
"""
E4 — Issued tickets test suite.

Covers:
  - Code format + randomness
  - Issuance: one row per seat, snapshots, idempotency
  - Mono-tier + multi-tier mix
  - Void on cancel (never deletes)
  - Atomic check_in with the five real-world outcomes
  - QR generation
  - Email render includes ticket block

Invocation:
  cd backend && ./venv/bin/python tests/test_issued_tickets.py
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
from models.issued_ticket import generate_ticket_code  # noqa: E402
from services.ticket_service import (  # noqa: E402
    issue_tickets_for_order,
    void_tickets_for_order,
    check_in_ticket,
    list_tickets_for_order,
    list_tickets_for_occurrence,
    generate_qr_png,
    qr_data_uri,
)

PREFIX = "test_e4_"
ORG = PREFIX + "org"


async def _cleanup():
    await issued_tickets_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await event_occurrences_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await products_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await organizations_collection.delete_many({"id": {"$regex": f"^{PREFIX}"}})


async def _seed_basic(order_id: str, occ_id: str, qty: int, tier_id=None, tier_label=None):
    """Build a minimal order dict suitable for issue_tickets_for_order."""
    await event_occurrences_collection.insert_one({
        "id": occ_id, "organization_id": ORG, "product_id": PREFIX + "prod",
        "start_at": "2027-06-01T20:00:00", "status": "published",
        "venue_name": "Masseria del Sole", "city": "Lecce",
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await products_collection.insert_one({
        "id": PREFIX + "prod", "organization_id": ORG, "name": "Cena di Autunno",
        "item_type": "event_ticket", "is_active": True, "is_published": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    order = {
        "id": order_id, "organization_id": ORG,
        "customer_name": "Mario Rossi", "customer_email": "mario@example.com",
        "items": [{
            "product_id": PREFIX + "prod", "occurrence_id": occ_id,
            "item_type": "event_ticket", "quantity": qty,
            **({"ticket_tier_id": tier_id} if tier_id else {}),
            **({"ticket_tier_label": tier_label} if tier_label else {}),
        }],
    }
    return order


# ── Synchronous ───────────────────────────────────────────────────────────


def t01_code_format():
    for _ in range(30):
        c = generate_ticket_code()
        assert c.startswith("EVT-")
        assert len(c) == 13, c  # EVT- + 4 + - + 4
        parts = c.split("-")
        assert len(parts) == 3 and len(parts[1]) == 4 and len(parts[2]) == 4
        # No ambiguous glyphs
        for ch in parts[1] + parts[2]:
            assert ch not in "01OIL", f"ambiguous char in {c}"


def t02_code_uniqueness_across_batch():
    seen = set()
    for _ in range(500):
        c = generate_ticket_code()
        assert c not in seen, "unexpected duplicate in 500 draws"
        seen.add(c)


def t03_qr_png():
    png = generate_qr_png("EVT-ABCD-2345")
    assert png[:4] == b"\x89PNG"
    assert len(png) > 100
    uri = qr_data_uri("EVT-ABCD-2345")
    assert uri.startswith("data:image/png;base64,")


# ── Async / DB ────────────────────────────────────────────────────────────


async def t04_issue_one_row_per_seat_mono_tier():
    await _cleanup()
    order = await _seed_basic(PREFIX + "o1", PREFIX + "occ1", qty=3)
    issued = await issue_tickets_for_order(order, ORG)
    assert len(issued) == 3
    # Each seat_index 1..3
    assert sorted([t["seat_index"] for t in issued]) == [1, 2, 3]
    assert all(t["seat_count"] == 3 for t in issued)
    assert all(t["status"] == "valid" for t in issued)
    # Unique codes
    codes = [t["code"] for t in issued]
    assert len(set(codes)) == 3, "duplicate codes in same order"
    # No tier snapshot on mono-tier
    assert all(t.get("tier_id") is None for t in issued)
    await _cleanup()


async def t05_issue_snapshots_tier_label_and_holder():
    await _cleanup()
    order = await _seed_basic(PREFIX + "o2", PREFIX + "occ2", qty=2,
                              tier_id=PREFIX + "vip", tier_label="VIP")
    issued = await issue_tickets_for_order(order, ORG)
    assert len(issued) == 2
    assert all(t["tier_id"] == PREFIX + "vip" for t in issued)
    assert all(t["tier_label"] == "VIP" for t in issued)
    assert all(t["holder_name"] == "Mario Rossi" for t in issued)
    assert all(t["holder_email"] == "mario@example.com" for t in issued)
    await _cleanup()


async def t06_idempotent_retry():
    await _cleanup()
    order = await _seed_basic(PREFIX + "o3", PREFIX + "occ3", qty=2)
    a = await issue_tickets_for_order(order, ORG)
    b = await issue_tickets_for_order(order, ORG)
    assert len(a) == 2 and len(b) == 2
    # Same codes returned — no duplicates created
    assert sorted(t["code"] for t in a) == sorted(t["code"] for t in b)
    count = await issued_tickets_collection.count_documents(
        {"order_id": PREFIX + "o3", "organization_id": ORG},
    )
    assert count == 2, f"expected 2, got {count}"
    await _cleanup()


async def t07_void_transitions_never_deletes():
    await _cleanup()
    order = await _seed_basic(PREFIX + "o4", PREFIX + "occ4", qty=3)
    await issue_tickets_for_order(order, ORG)
    n = await void_tickets_for_order(PREFIX + "o4", ORG)
    assert n == 3
    remaining = await issued_tickets_collection.count_documents(
        {"order_id": PREFIX + "o4"},
    )
    assert remaining == 3, "tickets were deleted — should be voided, not removed"
    # Second void is a no-op
    n2 = await void_tickets_for_order(PREFIX + "o4", ORG)
    assert n2 == 0
    # All have status=voided + voided_at
    async for t in issued_tickets_collection.find({"order_id": PREFIX + "o4"}):
        assert t["status"] == "voided"
        assert t.get("voided_at") is not None
    await _cleanup()


async def t08_check_in_happy_path():
    await _cleanup()
    order = await _seed_basic(PREFIX + "o5", PREFIX + "occ5", qty=1)
    issued = await issue_tickets_for_order(order, ORG)
    code = issued[0]["code"]
    ok, reason, ticket = await check_in_ticket(code=code, org_id=ORG)
    assert ok and reason == "ok"
    assert ticket["status"] == "checked_in"
    assert ticket.get("checked_in_at") is not None
    await _cleanup()


async def t09_check_in_already():
    await _cleanup()
    order = await _seed_basic(PREFIX + "o6", PREFIX + "occ6", qty=1)
    issued = await issue_tickets_for_order(order, ORG)
    code = issued[0]["code"]
    await check_in_ticket(code=code, org_id=ORG)  # first scan
    ok, reason, _ = await check_in_ticket(code=code, org_id=ORG)  # second scan
    assert ok and reason == "already_checked_in"
    await _cleanup()


async def t10_check_in_voided():
    await _cleanup()
    order = await _seed_basic(PREFIX + "o7", PREFIX + "occ7", qty=1)
    issued = await issue_tickets_for_order(order, ORG)
    code = issued[0]["code"]
    await void_tickets_for_order(PREFIX + "o7", ORG)
    ok, reason, ticket = await check_in_ticket(code=code, org_id=ORG)
    assert not ok and reason == "voided"
    assert ticket["status"] == "voided"
    await _cleanup()


async def t11_check_in_not_found():
    await _cleanup()
    ok, reason, _ = await check_in_ticket(code="EVT-ZZZZ-ZZZZ", org_id=ORG)
    assert not ok and reason == "not_found"
    await _cleanup()


async def t12_check_in_wrong_occurrence():
    await _cleanup()
    order = await _seed_basic(PREFIX + "o8", PREFIX + "occ8", qty=1)
    issued = await issue_tickets_for_order(order, ORG)
    code = issued[0]["code"]
    ok, reason, _ = await check_in_ticket(
        code=code, org_id=ORG, occurrence_id=PREFIX + "different_occ",
    )
    assert not ok and reason == "wrong_occurrence"
    # Ticket untouched
    t = await issued_tickets_collection.find_one({"code": code})
    assert t["status"] == "valid"
    await _cleanup()


async def t13_check_in_cross_org_isolation():
    """Codes from org A cannot check in against org B."""
    await _cleanup()
    order = await _seed_basic(PREFIX + "o9", PREFIX + "occ9", qty=1)
    issued = await issue_tickets_for_order(order, ORG)
    code = issued[0]["code"]
    ok, reason, _ = await check_in_ticket(code=code, org_id=PREFIX + "other_org")
    assert not ok and reason == "not_found"
    await _cleanup()


async def t14_concurrent_check_in_single_winner():
    """Two scanners hit the same valid code at the same moment — only
    one wins. The other sees already_checked_in."""
    await _cleanup()
    order = await _seed_basic(PREFIX + "o10", PREFIX + "occ10", qty=1)
    issued = await issue_tickets_for_order(order, ORG)
    code = issued[0]["code"]

    results = await asyncio.gather(*[
        check_in_ticket(code=code, org_id=ORG) for _ in range(5)
    ])
    first_time = [r for r in results if r[0] and r[1] == "ok"]
    already = [r for r in results if r[0] and r[1] == "already_checked_in"]
    assert len(first_time) == 1, f"expected 1 first-time, got {len(first_time)}"
    assert len(already) == 4, f"expected 4 already, got {len(already)}"
    await _cleanup()


async def t15_list_tickets_for_order():
    await _cleanup()
    order = await _seed_basic(PREFIX + "o11", PREFIX + "occ11", qty=3)
    await issue_tickets_for_order(order, ORG)
    got = await list_tickets_for_order(PREFIX + "o11", ORG)
    assert len(got) == 3
    assert [t["seat_index"] for t in got] == [1, 2, 3]
    await _cleanup()


async def t16_list_tickets_for_occurrence_excludes_voided_by_default():
    await _cleanup()
    # Two orders, one voided, on the same occurrence
    occ = PREFIX + "occ12"
    order_a = await _seed_basic(PREFIX + "oa", occ, qty=2)
    order_b = {
        "id": PREFIX + "ob", "organization_id": ORG,
        "customer_name": "Carla", "customer_email": "c@example.com",
        "items": [{
            "product_id": PREFIX + "prod", "occurrence_id": occ,
            "item_type": "event_ticket", "quantity": 1,
        }],
    }
    await issue_tickets_for_order(order_a, ORG)
    await issue_tickets_for_order(order_b, ORG)
    await void_tickets_for_order(PREFIX + "ob", ORG)

    active = await list_tickets_for_occurrence(occ, ORG)
    assert len(active) == 2  # only order_a's valid tickets
    all_incl = await list_tickets_for_occurrence(occ, ORG, include_voided=True)
    assert len(all_incl) == 3
    await _cleanup()


async def t17_email_renders_ticket_block():
    """_render_tickets_section returns HTML with codes + QR data URIs."""
    await _cleanup()
    order = await _seed_basic(PREFIX + "o13", PREFIX + "occ13", qty=2,
                              tier_id=PREFIX + "vip", tier_label="VIP")
    issued = await issue_tickets_for_order(order, ORG)
    # Put issued list on the order dict the way confirm_order does
    order["_issued_tickets"] = issued

    from services.order_email_service import _render_tickets_section
    html = await _render_tickets_section(order, ORG)

    assert html, "expected non-empty ticket section"
    assert "I tuoi biglietti" in html
    assert "Cena di Autunno" in html
    for t in issued:
        assert t["code"] in html, f"code {t['code']} missing"
    # QR embedded as data URI
    assert html.count("data:image/png;base64,") == len(issued)
    # Venue + date rendered
    assert "Masseria del Sole" in html
    assert "2027-06-01" in html
    # VIP label surfaced
    assert "VIP" in html
    await _cleanup()


async def t18_email_empty_when_no_event_tickets():
    from services.order_email_service import _render_tickets_section
    # Order with only a physical item -> no tickets -> empty block
    order = {"id": PREFIX + "ophys", "organization_id": ORG, "items": [
        {"item_type": "physical", "product_id": "x", "quantity": 1},
    ]}
    html = await _render_tickets_section(order, ORG)
    assert html == ""


TESTS: list[tuple[str, Callable]] = [
    ("t01 code format", t01_code_format),
    ("t02 code uniqueness 500 draws", t02_code_uniqueness_across_batch),
    ("t03 QR PNG + data URI", t03_qr_png),
    ("t04 issue one row per seat mono-tier", t04_issue_one_row_per_seat_mono_tier),
    ("t05 issue snapshots tier_label + holder", t05_issue_snapshots_tier_label_and_holder),
    ("t06 idempotent retry (no duplicates)", t06_idempotent_retry),
    ("t07 void transitions, never deletes", t07_void_transitions_never_deletes),
    ("t08 check_in happy path", t08_check_in_happy_path),
    ("t09 check_in already_checked_in", t09_check_in_already),
    ("t10 check_in voided", t10_check_in_voided),
    ("t11 check_in not_found", t11_check_in_not_found),
    ("t12 check_in wrong_occurrence", t12_check_in_wrong_occurrence),
    ("t13 check_in cross-org isolation", t13_check_in_cross_org_isolation),
    ("t14 5-way concurrent check_in -> 1 winner", t14_concurrent_check_in_single_winner),
    ("t15 list_tickets_for_order", t15_list_tickets_for_order),
    ("t16 list_tickets_for_occurrence excludes voided", t16_list_tickets_for_occurrence_excludes_voided_by_default),
    ("t17 email renders ticket block with QR", t17_email_renders_ticket_block),
    ("t18 email empty when no event_ticket items", t18_email_empty_when_no_event_tickets),
]


async def run_all() -> int:
    await _cleanup()
    passed = 0
    failed = 0
    for name, fn in TESTS:
        try:
            if asyncio.iscoroutinefunction(fn):
                await fn()
            else:
                fn()
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
