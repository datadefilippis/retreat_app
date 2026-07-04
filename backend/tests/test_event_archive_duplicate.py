#!/usr/bin/env python3
"""
G6 — archive flag + duplicate endpoint tests.

Covers:
  - is_archived filter on admin/list (hide default / only / all)
  - PATCH sets is_archived true/false
  - POST /{id}/duplicate returns wizard-ready payload
  - duplicate strips IDs, slugs, is_published, start_at
  - duplicate preserves tiers sorted by sort_order

Invocation:
  cd backend && ./venv/bin/python tests/test_event_archive_duplicate.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import Callable

os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_database")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (  # noqa: E402
    event_occurrences_collection,
    event_ticket_tiers_collection,
    products_collection,
    organizations_collection,
)
from models.common import utc_now  # noqa: E402


PREFIX = "test_g6_"
ORG = PREFIX + "org"
OTHER = PREFIX + "other_org"


async def _cleanup():
    for c in [event_occurrences_collection, event_ticket_tiers_collection,
              products_collection, organizations_collection]:
        await c.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
        await c.delete_many({"id": {"$regex": f"^{PREFIX}"}})


async def _seed():
    await organizations_collection.insert_one({
        "id": ORG, "name": "Michele", "is_active": True,
        "deactivated_at": None, "created_at": utc_now(), "updated_at": utc_now(),
    })
    await products_collection.insert_one({
        "id": PREFIX + "p1", "organization_id": ORG, "name": "Cena",
        "description": "Serata intima",
        "image_url": "/img.jpg", "unit_price": 45.0,
        "price_mode": "fixed", "transaction_mode": "direct",
        "is_published": True,
        "item_type": "event_ticket", "is_active": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    # 3 occurrences: 1 active upcoming, 1 archived past, 1 plain past
    future = (datetime.utcnow() + timedelta(days=30)).isoformat()
    past1 = (datetime.utcnow() - timedelta(days=20)).isoformat()
    past2 = (datetime.utcnow() - timedelta(days=60)).isoformat()
    await event_occurrences_collection.insert_many([
        {"id": PREFIX + "occ_upcoming", "organization_id": ORG,
         "product_id": PREFIX + "p1", "start_at": future,
         "status": "published", "capacity": 30, "reserved_seats": 0,
         "slug": "cena-upcoming",
         "venue_name": "Masseria", "city": "Lecce",
         "is_archived": False,
         "created_at": utc_now(), "updated_at": utc_now()},
        {"id": PREFIX + "occ_archived", "organization_id": ORG,
         "product_id": PREFIX + "p1", "start_at": past1,
         "status": "closed", "capacity": 30, "reserved_seats": 30,
         "slug": "cena-past1",
         "is_archived": True,
         "created_at": utc_now(), "updated_at": utc_now()},
        {"id": PREFIX + "occ_past", "organization_id": ORG,
         "product_id": PREFIX + "p1", "start_at": past2,
         "status": "closed", "capacity": 30, "reserved_seats": 25,
         "slug": "cena-past2",
         # legacy row — no is_archived field at all
         "created_at": utc_now(), "updated_at": utc_now()},
    ])
    # Tiers on the upcoming occurrence — used for duplicate test
    await event_ticket_tiers_collection.insert_many([
        {"id": PREFIX + "t_vip", "organization_id": ORG,
         "occurrence_id": PREFIX + "occ_upcoming",
         "label": "VIP", "description": "Tavolo riservato",
         "price": 85.0, "capacity": 10, "reserved_seats": 0,
         "sort_order": 1, "is_active": True,
         "created_at": utc_now(), "updated_at": utc_now()},
        {"id": PREFIX + "t_std", "organization_id": ORG,
         "occurrence_id": PREFIX + "occ_upcoming",
         "label": "Standard", "description": None,
         "price": 45.0, "capacity": 20, "reserved_seats": 0,
         "sort_order": 0, "is_active": True,
         "created_at": utc_now(), "updated_at": utc_now()},
        # An inactive tier — must NOT appear in the duplicate
        {"id": PREFIX + "t_old", "organization_id": ORG,
         "occurrence_id": PREFIX + "occ_upcoming",
         "label": "Old", "price": 99.0, "capacity": 5, "reserved_seats": 0,
         "sort_order": 2, "is_active": False,
         "created_at": utc_now(), "updated_at": utc_now()},
    ])


def _user(org=ORG):
    return {"organization_id": org, "id": "u1", "email": "a@b.com"}


# ── Archive filter tests ───────────────────────────────────────────────────


async def t01_default_hides_archived():
    """archived=hide (default): only non-archived rows."""
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(
        status_filter=None, when="all", q=None, archived=None, limit=100,
        current_user=_user(),
    )
    ids = {e["id"] for e in res["events"]}
    # upcoming (not archived) + past (legacy, no field = treated as not archived)
    assert PREFIX + "occ_upcoming" in ids
    assert PREFIX + "occ_past" in ids
    assert PREFIX + "occ_archived" not in ids
    await _cleanup()


async def t02_archived_only():
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(
        status_filter=None, when="all", q=None, archived="only", limit=100,
        current_user=_user(),
    )
    ids = {e["id"] for e in res["events"]}
    assert ids == {PREFIX + "occ_archived"}
    await _cleanup()


async def t03_archived_all_returns_everything():
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(
        status_filter=None, when="all", q=None, archived="all", limit=100,
        current_user=_user(),
    )
    ids = {e["id"] for e in res["events"]}
    assert ids == {PREFIX + "occ_upcoming", PREFIX + "occ_archived", PREFIX + "occ_past"}
    await _cleanup()


async def t04_is_archived_field_in_response():
    """Each row in /admin/list carries is_archived."""
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(
        status_filter=None, when="all", q=None, archived="all", limit=100,
        current_user=_user(),
    )
    by_id = {e["id"]: e for e in res["events"]}
    assert by_id[PREFIX + "occ_archived"]["is_archived"] is True
    assert by_id[PREFIX + "occ_upcoming"]["is_archived"] is False
    assert by_id[PREFIX + "occ_past"]["is_archived"] is False  # legacy row, defaults False
    await _cleanup()


async def t05_patch_sets_archived():
    """PATCH with is_archived toggles the flag."""
    from routers.event_occurrences import update_occurrence
    from models.event_occurrence import EventOccurrenceUpdate
    await _cleanup(); await _seed()
    body = EventOccurrenceUpdate(is_archived=True)
    await update_occurrence(PREFIX + "occ_upcoming", body, current_user=_user())
    occ = await event_occurrences_collection.find_one({"id": PREFIX + "occ_upcoming"})
    assert occ["is_archived"] is True

    # Unarchive
    body2 = EventOccurrenceUpdate(is_archived=False)
    await update_occurrence(PREFIX + "occ_upcoming", body2, current_user=_user())
    occ = await event_occurrences_collection.find_one({"id": PREFIX + "occ_upcoming"})
    assert occ["is_archived"] is False
    await _cleanup()


# ── Duplicate endpoint tests ───────────────────────────────────────────────


async def t06_duplicate_returns_wizard_shape():
    from routers.event_occurrences import duplicate_occurrence_data
    await _cleanup(); await _seed()
    res = await duplicate_occurrence_data(PREFIX + "occ_upcoming", current_user=_user())
    assert "product" in res and "occurrence" in res and "tiers" in res
    # product carries merchant-facing fields
    assert res["product"]["name"] == "Cena"
    assert res["product"]["description"] == "Serata intima"
    assert res["product"]["image_url"] == "/img.jpg"
    assert res["product"]["unit_price"] == 45.0
    assert res["product"]["is_published"] is False  # SAFER default
    # Source metadata surfaced for the UI banner
    assert res["source_occurrence_id"] == PREFIX + "occ_upcoming"
    assert res["source_event_name"] == "Cena"
    await _cleanup()


async def t07_duplicate_strips_runtime_state():
    """Duplicate must not carry over slug, reserved_seats, status=published, start_at."""
    from routers.event_occurrences import duplicate_occurrence_data
    await _cleanup(); await _seed()
    res = await duplicate_occurrence_data(PREFIX + "occ_upcoming", current_user=_user())
    occ = res["occurrence"]
    assert occ["start_at"] == ""   # blank, merchant picks a new date
    assert occ["end_at"] == ""
    assert occ["status"] == "draft"
    assert "slug" not in occ
    assert "reserved_seats" not in occ
    assert "id" not in occ
    assert occ["venue_name"] == "Masseria"  # Venue carries over
    assert occ["city"] == "Lecce"
    assert occ["capacity"] == 30
    await _cleanup()


async def t08_duplicate_preserves_active_tiers_sorted():
    from routers.event_occurrences import duplicate_occurrence_data
    await _cleanup(); await _seed()
    res = await duplicate_occurrence_data(PREFIX + "occ_upcoming", current_user=_user())
    tiers = res["tiers"]
    # Inactive tier "Old" must NOT be duplicated
    labels = [t["label"] for t in tiers]
    assert "Old" not in labels
    # Sorted by sort_order: Standard (0) before VIP (1)
    assert labels == ["Standard", "VIP"]
    # Prices preserved, IDs stripped
    assert tiers[1]["price"] == 85.0
    assert tiers[1]["capacity"] == 10
    assert "id" not in tiers[0]
    assert "reserved_seats" not in tiers[0]
    await _cleanup()


async def t09_duplicate_unknown_404():
    from routers.event_occurrences import duplicate_occurrence_data
    from fastapi import HTTPException
    await _cleanup()
    try:
        await duplicate_occurrence_data(PREFIX + "nope", current_user=_user())
        raise AssertionError("expected 404")
    except HTTPException as e:
        assert e.status_code == 404
    await _cleanup()


async def t10_duplicate_cross_org_404():
    from routers.event_occurrences import duplicate_occurrence_data
    from fastapi import HTTPException
    await _cleanup(); await _seed()
    try:
        await duplicate_occurrence_data(PREFIX + "occ_upcoming", current_user=_user(OTHER))
        raise AssertionError("expected 404")
    except HTTPException as e:
        assert e.status_code == 404
    await _cleanup()


async def t11_duplicate_no_tiers_event():
    """Mono-tier event (no tiers): duplicate returns empty tiers array."""
    from routers.event_occurrences import duplicate_occurrence_data
    await _cleanup(); await _seed()
    # New occurrence with no tiers
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "occ_no_tier", "organization_id": ORG,
        "product_id": PREFIX + "p1",
        "start_at": "2027-12-01T20:00:00", "status": "draft",
        "capacity": 20, "reserved_seats": 0,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    res = await duplicate_occurrence_data(PREFIX + "occ_no_tier", current_user=_user())
    assert res["tiers"] == []
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 default hides archived rows", t01_default_hides_archived),
    ("t02 archived=only returns only archived", t02_archived_only),
    ("t03 archived=all returns everything", t03_archived_all_returns_everything),
    ("t04 admin/list rows include is_archived bool", t04_is_archived_field_in_response),
    ("t05 PATCH toggles is_archived true/false", t05_patch_sets_archived),
    ("t06 duplicate returns wizard-shape payload", t06_duplicate_returns_wizard_shape),
    ("t07 duplicate strips runtime state (slug, start_at, ids, published)", t07_duplicate_strips_runtime_state),
    ("t08 duplicate preserves active tiers sorted, excludes inactive", t08_duplicate_preserves_active_tiers_sorted),
    ("t09 duplicate unknown id -> 404", t09_duplicate_unknown_404),
    ("t10 duplicate cross-org -> 404", t10_duplicate_cross_org_404),
    ("t11 duplicate event without tiers -> empty tiers array", t11_duplicate_no_tiers_event),
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
