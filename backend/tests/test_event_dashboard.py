#!/usr/bin/env python3
"""
E6 — Event dashboard backend test suite.

Covers the new `GET /api/event-occurrences/{id}` endpoint that powers
the admin dashboard by returning the occurrence plus denormalized
product name + image + description and the org public_slug needed to
build the landing URL.

Invocation:
  cd backend && ./venv/bin/python tests/test_event_dashboard.py
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
    products_collection,
    organizations_collection,
)
from models.common import utc_now  # noqa: E402


PREFIX = "test_e6_"
ORG = PREFIX + "org"
PUBLIC_SLUG = "michele-test"


async def _cleanup():
    await event_occurrences_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await products_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await organizations_collection.delete_many({"id": {"$regex": f"^{PREFIX}"}})


async def _seed():
    await organizations_collection.insert_one({
        "id": ORG, "name": "Michele", "public_slug": PUBLIC_SLUG,
        "is_active": True, "deactivated_at": None,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await products_collection.insert_one({
        "id": PREFIX + "prod", "organization_id": ORG,
        "name": "Cena in Masseria", "description": "Serata intima",
        "image_url": "/uploads/cena.jpg",
        "item_type": "event_ticket", "is_active": True, "is_published": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })


def _user():
    return {"organization_id": ORG, "id": "u1", "email": "a@b.com"}


# ── Tests ─────────────────────────────────────────────────────────────────


async def t01_get_occurrence_returns_denormalized_fields():
    from routers.event_occurrences import get_occurrence
    await _cleanup()
    await _seed()
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "occ1", "organization_id": ORG,
        "product_id": PREFIX + "prod",
        "start_at": "2027-06-01T20:00:00", "status": "published",
        "slug": "cena-2027-06-01", "capacity": 30, "reserved_seats": 5,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    doc = await get_occurrence(PREFIX + "occ1", current_user=_user())
    assert doc["id"] == PREFIX + "occ1"
    assert doc["product_name"] == "Cena in Masseria"
    assert doc["product_image_url"] == "/uploads/cena.jpg"
    assert doc["product_description"] == "Serata intima"
    assert doc["product_is_published"] is True
    assert doc["org_public_slug"] == PUBLIC_SLUG
    assert doc["capacity"] == 30
    assert doc["reserved_seats"] == 5
    assert doc["slug"] == "cena-2027-06-01"
    await _cleanup()


async def t02_get_occurrence_404_unknown():
    from routers.event_occurrences import get_occurrence
    from fastapi import HTTPException
    await _cleanup()
    try:
        await get_occurrence(PREFIX + "does_not_exist", current_user=_user())
        raise AssertionError("expected 404")
    except HTTPException as e:
        assert e.status_code == 404
    await _cleanup()


async def t03_get_occurrence_cross_org_isolation():
    """Caller in org B cannot read occurrence owned by org A."""
    from routers.event_occurrences import get_occurrence
    from fastapi import HTTPException
    await _cleanup()
    await _seed()
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "occ3", "organization_id": ORG,
        "product_id": PREFIX + "prod", "start_at": "2027-06-01T20:00:00",
        "status": "published", "slug": "s", "capacity": 10, "reserved_seats": 0,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    other_user = {"organization_id": PREFIX + "OTHER_ORG", "id": "u2", "email": "x@x"}
    try:
        await get_occurrence(PREFIX + "occ3", current_user=other_user)
        raise AssertionError("expected 404 cross-org")
    except HTTPException as e:
        assert e.status_code == 404
    await _cleanup()


async def t04_get_occurrence_structured_fields_passthrough():
    from routers.event_occurrences import get_occurrence
    await _cleanup()
    await _seed()
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "occ4", "organization_id": ORG,
        "product_id": PREFIX + "prod",
        "start_at": "2027-06-01T20:00:00", "status": "published",
        "slug": "s2", "capacity": 30, "reserved_seats": 0,
        # E2 fields
        "venue_name": "Masseria", "address": "Via Roma", "city": "Lecce",
        "latitude": 40.35, "longitude": 18.17,
        "cover_image_url": "/uploads/hero.jpg",
        "long_description": "## Concept",
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    doc = await get_occurrence(PREFIX + "occ4", current_user=_user())
    assert doc["venue_name"] == "Masseria"
    assert doc["address"] == "Via Roma"
    assert doc["city"] == "Lecce"
    assert doc["latitude"] == 40.35 and doc["longitude"] == 18.17
    assert doc["cover_image_url"] == "/uploads/hero.jpg"
    assert doc["long_description"] == "## Concept"
    await _cleanup()


async def t05_get_occurrence_missing_product_still_returns():
    """If the parent product was deleted, the endpoint still returns
    the occurrence (product_name=None, etc.) rather than 404 — the
    admin needs visibility even in degraded state."""
    from routers.event_occurrences import get_occurrence
    await _cleanup()
    # Seed org + occurrence pointing at a non-existent product
    await organizations_collection.insert_one({
        "id": ORG, "name": "Michele", "public_slug": PUBLIC_SLUG,
        "is_active": True, "deactivated_at": None,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "occ5", "organization_id": ORG,
        "product_id": PREFIX + "ghost_prod",
        "start_at": "2027-06-01T20:00:00", "status": "draft",
        "slug": "x", "capacity": 10, "reserved_seats": 0,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    doc = await get_occurrence(PREFIX + "occ5", current_user=_user())
    assert doc["id"] == PREFIX + "occ5"
    assert doc["product_name"] is None
    assert doc["product_image_url"] is None
    assert doc["product_is_published"] is False
    assert doc["org_public_slug"] == PUBLIC_SLUG
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 GET occurrence denormalizes product + org_slug", t01_get_occurrence_returns_denormalized_fields),
    ("t02 GET occurrence unknown -> 404", t02_get_occurrence_404_unknown),
    ("t03 GET occurrence cross-org isolation -> 404", t03_get_occurrence_cross_org_isolation),
    ("t04 GET occurrence passes through E2 structured fields", t04_get_occurrence_structured_fields_passthrough),
    ("t05 GET occurrence still returns when product missing (degraded)", t05_get_occurrence_missing_product_still_returns),
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
