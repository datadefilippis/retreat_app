#!/usr/bin/env python3
"""
G1 — Admin Eventi list endpoint tests.

Covers GET /api/event-occurrences/admin/list with filters:
  - status
  - when (upcoming / past / all)
  - q (product name search)
  - org isolation
  - tier_count aggregation
  - product enrichment (name, image, is_published)

Invocation:
  cd backend && ./venv/bin/python tests/test_events_list.py
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


PREFIX = "test_g1_"
ORG = PREFIX + "org"
OTHER_ORG = PREFIX + "other_org"


async def _cleanup():
    await event_occurrences_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await event_ticket_tiers_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await products_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await organizations_collection.delete_many({"id": {"$regex": f"^{PREFIX}"}})


async def _seed():
    """Creates a rich fixture across orgs + time + status."""
    await organizations_collection.insert_many([
        {"id": ORG, "name": "Michele", "is_active": True, "deactivated_at": None,
         "created_at": utc_now(), "updated_at": utc_now()},
        {"id": OTHER_ORG, "name": "Other", "is_active": True, "deactivated_at": None,
         "created_at": utc_now(), "updated_at": utc_now()},
    ])
    # Two products in our org
    await products_collection.insert_many([
        {"id": PREFIX + "p_cena", "organization_id": ORG, "name": "Cena in Masseria",
         "item_type": "event_ticket", "is_active": True, "is_published": True,
         "image_url": "/img/cena.jpg",
         "created_at": utc_now(), "updated_at": utc_now()},
        {"id": PREFIX + "p_concerto", "organization_id": ORG, "name": "Concerto rock",
         "item_type": "event_ticket", "is_active": True, "is_published": False,
         "image_url": "/img/concerto.jpg",
         "created_at": utc_now(), "updated_at": utc_now()},
        # Product in other org — must never appear in our list
        {"id": PREFIX + "p_other", "organization_id": OTHER_ORG, "name": "Altro evento",
         "item_type": "event_ticket", "is_active": True, "is_published": True,
         "created_at": utc_now(), "updated_at": utc_now()},
    ])

    now = datetime.utcnow()
    future1 = (now + timedelta(days=7)).isoformat()
    future2 = (now + timedelta(days=14)).isoformat()
    past1 = (now - timedelta(days=30)).isoformat()
    # occurrences
    await event_occurrences_collection.insert_many([
        # Upcoming, published
        {"id": PREFIX + "o_cena_next", "organization_id": ORG, "product_id": PREFIX + "p_cena",
         "start_at": future1, "status": "published", "capacity": 30, "reserved_seats": 5,
         "slug": "cena-next", "venue_name": "Masseria", "city": "Lecce",
         "created_at": utc_now(), "updated_at": utc_now()},
        # Upcoming, draft
        {"id": PREFIX + "o_cena_draft", "organization_id": ORG, "product_id": PREFIX + "p_cena",
         "start_at": future2, "status": "draft", "capacity": 20, "reserved_seats": 0,
         "slug": "cena-draft", "created_at": utc_now(), "updated_at": utc_now()},
        # Past, closed
        {"id": PREFIX + "o_cena_past", "organization_id": ORG, "product_id": PREFIX + "p_cena",
         "start_at": past1, "status": "closed", "capacity": 30, "reserved_seats": 30,
         "slug": "cena-past", "created_at": utc_now(), "updated_at": utc_now()},
        # Upcoming concerto
        {"id": PREFIX + "o_concerto", "organization_id": ORG, "product_id": PREFIX + "p_concerto",
         "start_at": future1, "status": "published", "capacity": 100, "reserved_seats": 10,
         "slug": "concerto-next", "created_at": utc_now(), "updated_at": utc_now()},
        # Cross-org — must be excluded
        {"id": PREFIX + "o_other", "organization_id": OTHER_ORG, "product_id": PREFIX + "p_other",
         "start_at": future1, "status": "published", "capacity": 50, "reserved_seats": 0,
         "slug": "other-next", "created_at": utc_now(), "updated_at": utc_now()},
    ])
    # Seed a few tiers on o_cena_next to verify tier_count
    await event_ticket_tiers_collection.insert_many([
        {"id": PREFIX + "t_std", "organization_id": ORG, "occurrence_id": PREFIX + "o_cena_next",
         "label": "Standard", "price": 20.0, "capacity": 20, "reserved_seats": 0,
         "sort_order": 0, "is_active": True, "created_at": utc_now(), "updated_at": utc_now()},
        {"id": PREFIX + "t_vip", "organization_id": ORG, "occurrence_id": PREFIX + "o_cena_next",
         "label": "VIP", "price": 50.0, "capacity": 10, "reserved_seats": 0,
         "sort_order": 1, "is_active": True, "created_at": utc_now(), "updated_at": utc_now()},
        # Inactive tier must NOT be counted
        {"id": PREFIX + "t_old", "organization_id": ORG, "occurrence_id": PREFIX + "o_cena_next",
         "label": "Old", "price": 99.0, "capacity": 5, "reserved_seats": 0,
         "sort_order": 2, "is_active": False, "created_at": utc_now(), "updated_at": utc_now()},
    ])


def _user(org=ORG):
    return {"organization_id": org, "id": "u1", "email": "a@b.com"}


# ── Tests ──────────────────────────────────────────────────────────────────


async def t01_default_upcoming():
    """Default call: upcoming + all statuses. Returns 3 upcoming occurrences,
    excludes past + cross-org."""
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(status_filter=None, when=None, q=None, limit=100, archived=None, current_user=_user())
    ids = [e["id"] for e in res["events"]]
    assert PREFIX + "o_cena_next" in ids
    assert PREFIX + "o_cena_draft" in ids
    assert PREFIX + "o_concerto" in ids
    assert PREFIX + "o_cena_past" not in ids
    assert PREFIX + "o_other" not in ids
    # Sorted ascending by start_at (upcoming)
    starts = [e["start_at"] for e in res["events"]]
    assert starts == sorted(starts)
    await _cleanup()


async def t02_when_past_sorts_desc():
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(status_filter=None, when="past", q=None, limit=100, archived=None, current_user=_user())
    assert len(res["events"]) == 1
    assert res["events"][0]["id"] == PREFIX + "o_cena_past"
    await _cleanup()


async def t03_when_all_returns_everything():
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(status_filter=None, when="all", q=None, limit=100, archived=None, current_user=_user())
    ids = {e["id"] for e in res["events"]}
    assert ids == {PREFIX + "o_cena_next", PREFIX + "o_cena_draft",
                   PREFIX + "o_concerto", PREFIX + "o_cena_past"}
    await _cleanup()


async def t04_filter_by_status():
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(status_filter="draft", when=None, q=None, limit=100, archived=None, current_user=_user())
    assert len(res["events"]) == 1
    assert res["events"][0]["id"] == PREFIX + "o_cena_draft"
    await _cleanup()


async def t05_search_q_case_insensitive():
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    # "masseria" case-insensitive → hits "Cena in Masseria" occurrences
    res = await list_events_admin(status_filter=None, when=None, q="masseria", limit=100, archived=None, current_user=_user())
    ids = {e["id"] for e in res["events"]}
    # upcoming filter default → both cena upcoming occurrences
    assert ids == {PREFIX + "o_cena_next", PREFIX + "o_cena_draft"}
    # Search that matches nothing
    res2 = await list_events_admin(status_filter=None, when=None, q="inesistente", limit=100, archived=None, current_user=_user())
    assert res2["events"] == [] and res2["total"] == 0
    await _cleanup()


async def t06_cross_org_isolation():
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(status_filter=None, when="all", q=None, limit=100, archived=None, current_user=_user(OTHER_ORG))
    ids = {e["id"] for e in res["events"]}
    assert ids == {PREFIX + "o_other"}
    await _cleanup()


async def t07_product_enrichment():
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(status_filter=None, when=None, q=None, limit=100, archived=None, current_user=_user())
    cena = next((e for e in res["events"] if e["id"] == PREFIX + "o_cena_next"), None)
    assert cena is not None
    assert cena["product_name"] == "Cena in Masseria"
    assert cena["product_image_url"] == "/img/cena.jpg"
    assert cena["product_is_published"] is True
    concerto = next((e for e in res["events"] if e["id"] == PREFIX + "o_concerto"), None)
    assert concerto["product_name"] == "Concerto rock"
    assert concerto["product_is_published"] is False
    await _cleanup()


async def t08_tier_count_excludes_inactive():
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(status_filter=None, when=None, q=None, limit=100, archived=None, current_user=_user())
    cena = next((e for e in res["events"] if e["id"] == PREFIX + "o_cena_next"), None)
    # Standard + VIP active, old inactive -> count is 2
    assert cena["tier_count"] == 2
    # No tiers on other occurrences
    other = next((e for e in res["events"] if e["id"] == PREFIX + "o_concerto"), None)
    assert other["tier_count"] == 0
    await _cleanup()


async def t09_invalid_status_rejects():
    from routers.event_occurrences import list_events_admin
    from fastapi import HTTPException
    await _cleanup(); await _seed()
    try:
        await list_events_admin(status_filter="nope", when=None, q=None, limit=100, archived=None, current_user=_user())
        raise AssertionError("expected 400")
    except HTTPException as e:
        assert e.status_code == 400
    await _cleanup()


async def t10_limit_capped():
    from routers.event_occurrences import list_events_admin
    await _cleanup(); await _seed()
    res = await list_events_admin(status_filter=None, when=None, q=None, limit=1, archived=None, current_user=_user())
    assert len(res["events"]) == 1
    await _cleanup()


async def t11_empty_when_no_events():
    from routers.event_occurrences import list_events_admin
    await _cleanup()
    # Seed only the org, no events
    await organizations_collection.insert_one({
        "id": ORG, "name": "Michele", "is_active": True, "deactivated_at": None,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    res = await list_events_admin(status_filter=None, when="all", q=None, limit=100, archived=None, current_user=_user())
    assert res["events"] == [] and res["total"] == 0
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 default upcoming sorted asc", t01_default_upcoming),
    ("t02 when=past sorted desc, only past", t02_when_past_sorts_desc),
    ("t03 when=all returns every status/time", t03_when_all_returns_everything),
    ("t04 status=draft filter", t04_filter_by_status),
    ("t05 q search case-insensitive contains", t05_search_q_case_insensitive),
    ("t06 cross-org isolation", t06_cross_org_isolation),
    ("t07 product enrichment fields present", t07_product_enrichment),
    ("t08 tier_count counts active tiers only", t08_tier_count_excludes_inactive),
    ("t09 invalid status -> 400", t09_invalid_status_rejects),
    ("t10 limit is honored", t10_limit_capped),
    ("t11 empty org returns empty list", t11_empty_when_no_events),
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
