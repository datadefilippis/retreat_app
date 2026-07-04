#!/usr/bin/env python3
"""
E3 — Public event landing page test suite.

Covers:
  - slugify: normalization, accents, empty
  - generate_occurrence_slug: collision suffix, exclude_id
  - GET /public/events/{org_slug}/{slug}: 200 / 404 paths
  - Rich payload: tiers, map_url, long_description, is_buyable

Invocation:
  cd backend && ./venv/bin/python tests/test_event_landing.py
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
    organizations_collection,
    products_collection,
    stores_collection,
)
from models.common import utc_now  # noqa: E402
from models.event_occurrence import (  # noqa: E402
    slugify,
    generate_occurrence_slug,
)

PREFIX = "test_e3_"
ORG = PREFIX + "org"
ORG_SLUG = PREFIX + "michele"
PRODUCT = PREFIX + "prod"


async def _cleanup():
    await event_occurrences_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await event_ticket_tiers_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await products_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await organizations_collection.delete_many({"id": {"$regex": f"^{PREFIX}"}})
    await stores_collection.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})


async def _seed_org_and_product():
    await organizations_collection.insert_one({
        "id": ORG,
        "name": "Michele Events",
        "public_slug": ORG_SLUG,
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
        "description": "Serata di degustazione con menù a 4 portate.",
        "item_type": "event_ticket",
        "is_published": True,
        "is_active": True,
        "price_mode": "fixed",
        "transaction_mode": "direct",
        "image_url": "/uploads/masseria.jpg",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    })


# ── Synchronous slugify tests ───────────────────────────────────────────────


def t01_slugify_basic():
    assert slugify("Aperitivo d'Autunno!") == "aperitivo-d-autunno"
    assert slugify("  Cena  in  Masseria  ") == "cena-in-masseria"
    assert slugify("Evento 2026-08-14 · VIP") == "evento-2026-08-14-vip"


def t02_slugify_accents_stripped():
    assert slugify("Città di Lecce") == "citta-di-lecce"
    assert slugify("Café piccolo") == "cafe-piccolo"


def t03_slugify_empty_and_none():
    assert slugify(None) == ""
    assert slugify("") == ""
    assert slugify("   ") == ""
    # Only non-alphanum -> empty
    assert slugify("!@#$%^&*()") == ""


def t04_slugify_truncated():
    long = "a" * 120
    out = slugify(long)
    assert len(out) == 80


# ── Async generation / endpoint tests ──────────────────────────────────────


async def t05_generate_slug_no_collision():
    await _cleanup()
    slug = await generate_occurrence_slug(
        org_id=ORG, product_name="Cena in Masseria", start_at="2026-08-14T20:00:00",
    )
    assert slug == "cena-in-masseria-2026-08-14", slug


async def t06_generate_slug_with_collision_suffix():
    await _cleanup()
    # Seed one occurrence with the base slug taken
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "existing",
        "organization_id": ORG,
        "product_id": PRODUCT,
        "start_at": "2026-08-14T20:00:00",
        "status": "draft",
        "slug": "cena-in-masseria-2026-08-14",
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    slug = await generate_occurrence_slug(
        org_id=ORG, product_name="Cena in Masseria", start_at="2026-08-14T20:00:00",
    )
    assert slug == "cena-in-masseria-2026-08-14-2", slug
    await _cleanup()


async def t07_generate_slug_exclude_self():
    await _cleanup()
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "self",
        "organization_id": ORG,
        "product_id": PRODUCT,
        "start_at": "2026-08-14T20:00:00",
        "status": "draft",
        "slug": "cena-in-masseria-2026-08-14",
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    slug = await generate_occurrence_slug(
        org_id=ORG, product_name="Cena in Masseria", start_at="2026-08-14T20:00:00",
        exclude_id=PREFIX + "self",
    )
    # Excluded self -> base slug is free
    assert slug == "cena-in-masseria-2026-08-14"
    await _cleanup()


async def t08_generate_slug_empty_product_name():
    await _cleanup()
    slug = await generate_occurrence_slug(
        org_id=ORG, product_name=None, start_at="2026-08-14T20:00:00",
    )
    assert slug == "2026-08-14"
    await _cleanup()


async def _call_landing(org_slug, slug):
    from routers.public import get_public_event_landing
    return await get_public_event_landing(org_slug, slug)


async def t09_landing_404_unknown_org():
    await _cleanup()
    try:
        await _call_landing(PREFIX + "nonexistent_org", "any-slug")
        raise AssertionError("expected 404")
    except Exception as e:
        # HTTPException subclass
        from fastapi import HTTPException
        assert isinstance(e, HTTPException) and e.status_code == 404
    await _cleanup()


async def t10_landing_404_unknown_slug():
    await _cleanup()
    await _seed_org_and_product()
    try:
        await _call_landing(ORG_SLUG, PREFIX + "nope")
        raise AssertionError("expected 404")
    except Exception as e:
        from fastapi import HTTPException
        assert isinstance(e, HTTPException) and e.status_code == 404
    await _cleanup()


async def t11_landing_404_unpublished_occurrence():
    await _cleanup()
    await _seed_org_and_product()
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "draft_occ",
        "organization_id": ORG,
        "product_id": PRODUCT,
        "start_at": "2027-05-15T20:00:00",
        "status": "draft",  # not published
        "slug": "cena-draft",
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    try:
        await _call_landing(ORG_SLUG, "cena-draft")
        raise AssertionError("expected 404 for draft occurrence")
    except Exception as e:
        from fastapi import HTTPException
        assert isinstance(e, HTTPException) and e.status_code == 404
    await _cleanup()


async def t12_landing_full_payload():
    """Happy path: all rich E2 fields + E1 tiers -> full payload."""
    await _cleanup()
    await _seed_org_and_product()
    occ_id = PREFIX + "full_occ"
    await event_occurrences_collection.insert_one({
        "id": occ_id,
        "organization_id": ORG,
        "product_id": PRODUCT,
        "start_at": "2027-05-15T20:00:00",
        "status": "published",
        "slug": "cena-2027-05-15",
        "capacity": 30,
        "reserved_seats": 0,
        "venue_name": "Masseria del Sole",
        "address": "Via Roma 10",
        "city": "Lecce",
        "postal_code": "73100",
        "country": "IT",
        "latitude": 40.352,
        "longitude": 18.173,
        "cover_image_url": "/uploads/masseria_hero.jpg",
        "long_description": "## Il concept\n\nSerata con menù degustazione a 4 portate.",
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    # Seed 2 active tiers
    for tier_id, label, price, capacity, sort_order in [
        (PREFIX + "std", "Standard", 20.0, 20, 0),
        (PREFIX + "vip", "VIP", 50.0, 10, 1),
    ]:
        await event_ticket_tiers_collection.insert_one({
            "id": tier_id,
            "organization_id": ORG,
            "occurrence_id": occ_id,
            "label": label,
            "description": f"Biglietto {label}",
            "price": price,
            "capacity": capacity,
            "reserved_seats": 0,
            "sort_order": sort_order,
            "is_active": True,
            "created_at": utc_now(), "updated_at": utc_now(),
        })

    resp = await _call_landing(ORG_SLUG, "cena-2027-05-15")

    assert resp.org_name == "Michele Events"
    assert resp.product.name == "Cena in Masseria"
    assert resp.product.image_url == "/uploads/masseria.jpg"

    o = resp.occurrence
    assert o.venue_name == "Masseria del Sole"
    assert o.address == "Via Roma 10"
    assert o.city == "Lecce"
    assert o.latitude == 40.352
    assert o.cover_image_url == "/uploads/masseria_hero.jpg"
    assert o.long_description.startswith("## Il concept")
    assert o.map_url is not None and "40.352,18.173" in o.map_url
    assert o.remaining == 30

    # Tiers: stable order by sort_order
    assert len(o.tiers) == 2
    assert [t.label for t in o.tiers] == ["Standard", "VIP"]
    assert o.tiers[0].price == 20.0
    assert o.tiers[0].remaining == 20
    assert o.tiers[1].remaining == 10

    assert resp.is_buyable is True
    await _cleanup()


async def t13_landing_is_buyable_false_sold_out():
    await _cleanup()
    await _seed_org_and_product()
    occ_id = PREFIX + "full_occ2"
    await event_occurrences_collection.insert_one({
        "id": occ_id,
        "organization_id": ORG,
        "product_id": PRODUCT,
        "start_at": "2027-05-15T20:00:00",
        "status": "published",
        "slug": "sold-out-slug",
        "capacity": 1,
        "reserved_seats": 1,  # occurrence maxed out
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    # Simulate a confirmed order that "used" the 1 seat
    from database import orders_collection
    await orders_collection.delete_many({"organization_id": ORG})
    await orders_collection.insert_one({
        "id": PREFIX + "ord_sold",
        "organization_id": ORG,
        "status": "confirmed",
        "items": [{"occurrence_id": occ_id, "quantity": 1}],
    })

    resp = await _call_landing(ORG_SLUG, "sold-out-slug")
    assert resp.occurrence.remaining == 0
    assert resp.is_buyable is False
    await orders_collection.delete_many({"organization_id": ORG})
    await _cleanup()


async def t14_landing_404_product_unpublished():
    await _cleanup()
    await organizations_collection.insert_one({
        "id": ORG,
        "name": "Michele",
        "public_slug": ORG_SLUG,
        "is_active": True,
        "deactivated_at": None,
        "store_settings": {"is_storefront_published": True},
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await products_collection.insert_one({
        "id": PRODUCT,
        "organization_id": ORG,
        "name": "Hidden event",
        "item_type": "event_ticket",
        "is_published": False,  # hidden
        "is_active": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "occ_hidden",
        "organization_id": ORG,
        "product_id": PRODUCT,
        "start_at": "2027-06-01T20:00:00",
        "status": "published",
        "slug": "hidden-event",
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    try:
        await _call_landing(ORG_SLUG, "hidden-event")
        raise AssertionError("expected 404 when product unpublished")
    except Exception as e:
        from fastapi import HTTPException
        assert isinstance(e, HTTPException) and e.status_code == 404
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 slugify basic", t01_slugify_basic),
    ("t02 slugify accents stripped", t02_slugify_accents_stripped),
    ("t03 slugify empty/None", t03_slugify_empty_and_none),
    ("t04 slugify truncated at 80", t04_slugify_truncated),
    ("t05 generate_slug: no collision", t05_generate_slug_no_collision),
    ("t06 generate_slug: collision -> -2 suffix", t06_generate_slug_with_collision_suffix),
    ("t07 generate_slug: exclude_id allows self", t07_generate_slug_exclude_self),
    ("t08 generate_slug: empty name falls back to date", t08_generate_slug_empty_product_name),
    ("t09 landing 404 unknown org", t09_landing_404_unknown_org),
    ("t10 landing 404 unknown slug", t10_landing_404_unknown_slug),
    ("t11 landing 404 unpublished occurrence", t11_landing_404_unpublished_occurrence),
    ("t12 landing full rich payload (case Michele)", t12_landing_full_payload),
    ("t13 landing is_buyable=False when sold out", t13_landing_is_buyable_false_sold_out),
    ("t14 landing 404 when product unpublished", t14_landing_404_product_unpublished),
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
