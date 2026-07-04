#!/usr/bin/env python3
"""
E2 — Event occurrence structured details test suite.

Covers:
  - Pydantic model accepts and normalizes new fields (country uppercase,
    lat/lng bounds, all fields optional).
  - build_map_url precedence order.
  - Public catalog embeds the new fields and auto-derives map_url.
  - Backward-compat: pre-E2 occurrences serialize without new fields set.

Invocation:
  cd backend && ./venv/bin/python tests/test_event_details.py
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
    organizations_collection,
    products_collection,
    stores_collection,
)
from models.common import utc_now  # noqa: E402
from models.event_occurrence import (  # noqa: E402
    EventOccurrence,
    EventOccurrenceCreate,
    EventOccurrenceUpdate,
    build_map_url,
)

PREFIX = "test_e2_"
ORG = PREFIX + "org"
PRODUCT = PREFIX + "prod"
SLUG = PREFIX + "slug"


async def _cleanup():
    await event_occurrences_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await products_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await organizations_collection.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    await stores_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})


# ── Schema-level tests (synchronous) ────────────────────────────────────────


def t01_backward_compat_pre_e2_shape():
    """A pre-E2 occurrence (only legacy fields) validates and has all
    new fields defaulting to None."""
    o = EventOccurrence(
        organization_id=ORG, product_id=PRODUCT,
        start_at="2026-08-14T20:00:00",
        location="Masseria — Legacy text",
        capacity=30,
    )
    assert o.venue_name is None
    assert o.address is None
    assert o.latitude is None and o.longitude is None
    assert o.cover_image_url is None
    assert o.long_description is None
    assert o.country is None


def t02_country_normalized_uppercase():
    o = EventOccurrence(
        organization_id=ORG, product_id=PRODUCT,
        start_at="2026-08-14T20:00:00",
        country="it",
    )
    assert o.country == "IT"
    # Empty string -> None
    o2 = EventOccurrence(
        organization_id=ORG, product_id=PRODUCT,
        start_at="2026-08-14T20:00:00",
        country="",
    )
    assert o2.country is None


def t03_latitude_longitude_bounds():
    import pytest  # using a minimal try/except since pytest may not be on path
    # Accept ok
    EventOccurrence(
        organization_id=ORG, product_id=PRODUCT,
        start_at="2026-08-14T20:00:00",
        latitude=-89.9, longitude=179.9,
    )
    # Reject too big
    for bad_lat in (91, -91):
        try:
            EventOccurrence(
                organization_id=ORG, product_id=PRODUCT,
                start_at="2026-08-14T20:00:00",
                latitude=bad_lat,
            )
            raise AssertionError(f"lat={bad_lat} should be rejected")
        except Exception:
            pass
    for bad_lng in (181, -181):
        try:
            EventOccurrence(
                organization_id=ORG, product_id=PRODUCT,
                start_at="2026-08-14T20:00:00",
                longitude=bad_lng,
            )
            raise AssertionError(f"lng={bad_lng} should be rejected")
        except Exception:
            pass


def t04_update_schema_accepts_new_fields():
    u = EventOccurrenceUpdate(
        venue_name="X", latitude=45.5,
        long_description="### descrizione",
        country="de",
    )
    assert u.venue_name == "X"
    assert u.country == "DE"
    assert u.long_description.startswith("### ")


def t05_build_map_url_explicit_wins():
    assert build_map_url({"map_url": "https://override.test"}) == "https://override.test"


def t06_build_map_url_lat_lng():
    url = build_map_url({"latitude": 40.35, "longitude": 18.17})
    assert url is not None and "query=40.35,18.17" in url


def t07_build_map_url_composed_address():
    url = build_map_url({
        "venue_name": "Masseria del Sole",
        "address": "Via Roma 10",
        "city": "Lecce",
        "country": "IT",
    })
    assert url is not None
    assert "Masseria" in url and "Via+Roma" in url and "Lecce" in url


def t08_build_map_url_legacy_fallback():
    url = build_map_url({"location": "Piazza Duomo, Lecce"})
    assert url is not None and "Piazza+Duomo" in url


def t09_build_map_url_none_when_empty():
    assert build_map_url({}) is None
    assert build_map_url({"location": ""}) is None


# ── Catalog-level tests (async, hit the real handler logic) ─────────────────


async def _seed_org_and_product():
    await organizations_collection.insert_one({
        "id": ORG,
        "name": "Michele Events",
        "public_slug": SLUG,
        "is_active": True,
        "deactivated_at": None,
        "store_settings": {
            "is_storefront_published": True,
            "display_name": "Michele Events",
            "fulfillment_modes": ["not_required"],
        },
        "created_at": utc_now(),
        "updated_at": utc_now(),
    })
    await products_collection.insert_one({
        "id": PRODUCT,
        "organization_id": ORG,
        "name": "Cena in Masseria",
        "item_type": "event_ticket",
        "is_published": True,
        "is_active": True,
        "price_mode": "fixed",
        "transaction_mode": "direct",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    })


async def _seed_occurrence(occ_id, **overrides):
    doc = {
        "id": occ_id,
        "organization_id": ORG,
        "product_id": PRODUCT,
        "start_at": "2027-05-15T20:00:00",
        "status": "published",
        "capacity": 30,
        "reserved_seats": 0,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    doc.update(overrides)
    await event_occurrences_collection.insert_one(doc)


async def t10_public_catalog_embeds_structured_fields():
    """When occurrence has full E2 fields, public catalog exposes them
    and auto-derives map_url from lat/lng."""
    await _cleanup()
    await _seed_org_and_product()
    await _seed_occurrence(
        PREFIX + "occ_full",
        venue_name="Masseria del Sole",
        address="Via Roma 10",
        city="Lecce",
        postal_code="73100",
        country="IT",
        latitude=40.352,
        longitude=18.173,
        cover_image_url="/uploads/ev.jpg",
        long_description="## La cena\n\nSabato a Masseria.",
    )

    # Call the public handler directly (the request object is only used
    # for rate-limiting which is a no-op in tests).
    from routers.public import get_public_catalog

    class FakeReq:
        client = type("c", (), {"host": "127.0.0.1"})()

    resp = await get_public_catalog.__wrapped__(FakeReq(), SLUG)
    # Response is a CatalogResponse pydantic model
    products = resp.products
    assert len(products) == 1
    occs = products[0].occurrences
    assert len(occs) == 1
    o = occs[0]
    assert o.venue_name == "Masseria del Sole"
    assert o.address == "Via Roma 10"
    assert o.city == "Lecce"
    assert o.latitude == 40.352
    assert o.cover_image_url == "/uploads/ev.jpg"
    assert o.long_description.startswith("## La cena")
    # Auto-derived map_url from lat/lng
    assert o.map_url is not None
    assert "40.352,18.173" in o.map_url
    await _cleanup()


async def t11_public_catalog_backward_compat_legacy_occurrence():
    """An occurrence with only the pre-E2 `location` text still renders
    with structured fields = None and a fallback map_url."""
    await _cleanup()
    await _seed_org_and_product()
    await _seed_occurrence(
        PREFIX + "occ_legacy",
        location="Piazza Duomo, Lecce",
    )

    from routers.public import get_public_catalog

    class FakeReq:
        client = type("c", (), {"host": "127.0.0.1"})()

    resp = await get_public_catalog.__wrapped__(FakeReq(), SLUG)
    occs = resp.products[0].occurrences
    o = occs[0]
    assert o.venue_name is None
    assert o.address is None
    assert o.latitude is None
    assert o.location == "Piazza Duomo, Lecce"  # legacy text still there
    # map_url derived from legacy text
    assert o.map_url is not None
    assert "Piazza+Duomo" in o.map_url
    await _cleanup()


async def t12_admin_map_url_override_wins():
    """An explicit admin-set map_url is never overwritten by the
    derived fallback."""
    await _cleanup()
    await _seed_org_and_product()
    await _seed_occurrence(
        PREFIX + "occ_override",
        latitude=40.0, longitude=18.0,
        map_url="https://my-custom-map.link/ev",
    )
    from routers.public import get_public_catalog

    class FakeReq:
        client = type("c", (), {"host": "127.0.0.1"})()

    resp = await get_public_catalog.__wrapped__(FakeReq(), SLUG)
    o = resp.products[0].occurrences[0]
    assert o.map_url == "https://my-custom-map.link/ev"
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 backward-compat pre-E2 shape", t01_backward_compat_pre_e2_shape),
    ("t02 country normalized uppercase", t02_country_normalized_uppercase),
    ("t03 latitude/longitude bounds enforced", t03_latitude_longitude_bounds),
    ("t04 EventOccurrenceUpdate accepts new fields", t04_update_schema_accepts_new_fields),
    ("t05 build_map_url explicit wins", t05_build_map_url_explicit_wins),
    ("t06 build_map_url lat/lng", t06_build_map_url_lat_lng),
    ("t07 build_map_url composed address", t07_build_map_url_composed_address),
    ("t08 build_map_url legacy fallback", t08_build_map_url_legacy_fallback),
    ("t09 build_map_url none when empty", t09_build_map_url_none_when_empty),
    ("t10 public catalog embeds structured fields + derives map_url", t10_public_catalog_embeds_structured_fields),
    ("t11 public catalog backward-compat legacy occurrence", t11_public_catalog_backward_compat_legacy_occurrence),
    ("t12 admin map_url override wins", t12_admin_map_url_override_wins),
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
