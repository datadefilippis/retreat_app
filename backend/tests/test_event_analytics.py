#!/usr/bin/env python3
"""
G3 — Event analytics endpoint tests.

Covers:
  - GET /api/event-occurrences/{id}/analytics
  - revenue totals + per-tier breakdown
  - tier_label fallback (fetch from tier doc when order line lacks snapshot)
  - sales_timeline aggregation by day
  - cancelled orders excluded
  - cross-org isolation
  - CSV export shape

Invocation:
  cd backend && ./venv/bin/python tests/test_event_analytics.py
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
    issued_tickets_collection,
    orders_collection,
    organizations_collection,
    products_collection,
)
from models.common import utc_now  # noqa: E402


PREFIX = "test_g3_"
ORG = PREFIX + "org"
OTHER_ORG = PREFIX + "other_org"


async def _cleanup():
    for c in [event_occurrences_collection, event_ticket_tiers_collection,
              issued_tickets_collection, orders_collection,
              organizations_collection, products_collection]:
        await c.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
        await c.delete_many({"id": {"$regex": f"^{PREFIX}"}})


async def _seed_basic():
    """One org, one event_ticket product, one occurrence with two tiers."""
    await organizations_collection.insert_one({
        "id": ORG, "name": "Michele", "currency": "EUR",
        "is_active": True, "deactivated_at": None,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await products_collection.insert_one({
        "id": PREFIX + "p1", "organization_id": ORG, "name": "Cena gala",
        "item_type": "event_ticket", "is_active": True, "is_published": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "occ1", "organization_id": ORG, "product_id": PREFIX + "p1",
        "start_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "status": "published", "capacity": 30, "reserved_seats": 0,
        "slug": "cena-test",
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await event_ticket_tiers_collection.insert_many([
        {"id": PREFIX + "t_std", "organization_id": ORG, "occurrence_id": PREFIX + "occ1",
         "label": "Standard", "price": 45.0, "capacity": 20, "reserved_seats": 0,
         "sort_order": 0, "is_active": True, "created_at": utc_now(), "updated_at": utc_now()},
        {"id": PREFIX + "t_vip", "organization_id": ORG, "occurrence_id": PREFIX + "occ1",
         "label": "VIP", "price": 85.0, "capacity": 10, "reserved_seats": 0,
         "sort_order": 1, "is_active": True, "created_at": utc_now(), "updated_at": utc_now()},
    ])


async def _add_order(order_id, items, status_str="confirmed", order_date=None):
    """Minimal order doc compatible with the analytics pipelines."""
    now = datetime.utcnow()
    await orders_collection.insert_one({
        "id": order_id, "organization_id": ORG,
        "status": status_str,
        "items": items,
        "order_date": order_date or now.date().isoformat(),
        "created_at": utc_now(), "updated_at": utc_now(),
    })


def _user(org=ORG):
    return {"organization_id": org, "id": "u1", "email": "a@b.com"}


# ── Tests ──────────────────────────────────────────────────────────────────


async def t01_empty_occurrence_returns_zeros():
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert r["revenue_total"] == 0.0
    assert r["tickets_sold_total"] == 0
    assert r["revenue_by_tier"] == []
    assert r["sales_timeline"] == []
    assert r["currency"] == "EUR"
    await _cleanup()


async def t02_single_tier_revenue():
    """3 tickets @ 45€ = 135€ in one order, single tier VIP."""
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    await _add_order(PREFIX + "ord1", [{
        "product_id": PREFIX + "p1",
        "occurrence_id": PREFIX + "occ1",
        "ticket_tier_id": PREFIX + "t_std",
        "ticket_tier_label": "Standard",
        "quantity": 3, "unit_price": 45.0, "line_total": 135.0,
    }])
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert r["revenue_total"] == 135.0
    assert r["tickets_sold_total"] == 3
    assert len(r["revenue_by_tier"]) == 1
    tier = r["revenue_by_tier"][0]
    assert tier["tier_id"] == PREFIX + "t_std"
    assert tier["tier_label"] == "Standard"
    assert tier["revenue"] == 135.0
    assert tier["tickets_sold"] == 3
    assert tier["price"] == 45.0
    await _cleanup()


async def t03_multi_tier_aggregated():
    """Two orders: 2 VIP (170€) + 1 Standard (45€) = 215€."""
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    await _add_order(PREFIX + "ord_vip", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ1",
        "ticket_tier_id": PREFIX + "t_vip", "ticket_tier_label": "VIP",
        "quantity": 2, "unit_price": 85.0, "line_total": 170.0,
    }])
    await _add_order(PREFIX + "ord_std", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ1",
        "ticket_tier_id": PREFIX + "t_std", "ticket_tier_label": "Standard",
        "quantity": 1, "unit_price": 45.0, "line_total": 45.0,
    }])
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert r["revenue_total"] == 215.0
    assert r["tickets_sold_total"] == 3
    # Sorted desc by revenue -> VIP first
    assert [row["tier_id"] for row in r["revenue_by_tier"]] == [PREFIX + "t_vip", PREFIX + "t_std"]
    assert r["revenue_by_tier"][0]["revenue"] == 170.0
    assert r["revenue_by_tier"][1]["revenue"] == 45.0
    await _cleanup()


async def t04_cancelled_orders_excluded():
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    await _add_order(PREFIX + "ord_live", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ1",
        "ticket_tier_id": PREFIX + "t_std", "ticket_tier_label": "Standard",
        "quantity": 1, "unit_price": 45.0, "line_total": 45.0,
    }])
    await _add_order(PREFIX + "ord_cx", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ1",
        "ticket_tier_id": PREFIX + "t_vip", "ticket_tier_label": "VIP",
        "quantity": 5, "unit_price": 85.0, "line_total": 425.0,
    }], status_str="cancelled")
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert r["revenue_total"] == 45.0  # only the live order
    assert r["tickets_sold_total"] == 1
    assert len(r["revenue_by_tier"]) == 1
    assert r["revenue_by_tier"][0]["tier_id"] == PREFIX + "t_std"
    await _cleanup()


async def t05_tier_label_fallback_from_tier_doc():
    """Order line missing ticket_tier_label but has tier_id. Endpoint
    should enrich the label by fetching the tier document."""
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    await _add_order(PREFIX + "ord_legacy", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ1",
        "ticket_tier_id": PREFIX + "t_vip",
        # no ticket_tier_label in snapshot
        "quantity": 1, "unit_price": 85.0, "line_total": 85.0,
    }])
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert len(r["revenue_by_tier"]) == 1
    tier = r["revenue_by_tier"][0]
    assert tier["tier_id"] == PREFIX + "t_vip"
    assert tier["tier_label"] == "VIP"  # filled from tier doc
    await _cleanup()


async def t06_mono_tier_no_tier_id():
    """Mono-tier event: order item has no ticket_tier_id. Row appears
    with tier_id=None, tier_label=None."""
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    await _add_order(PREFIX + "ord_mono", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ1",
        "quantity": 2, "unit_price": 30.0, "line_total": 60.0,
    }])
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert r["revenue_total"] == 60.0
    assert len(r["revenue_by_tier"]) == 1
    assert r["revenue_by_tier"][0]["tier_id"] is None
    assert r["revenue_by_tier"][0]["tier_label"] is None
    await _cleanup()


async def t07_sales_timeline_groups_by_day():
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    d1 = (datetime.utcnow() - timedelta(days=2)).date().isoformat()
    d2 = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
    await _add_order(PREFIX + "ord_a", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ1",
        "quantity": 2, "unit_price": 45.0, "line_total": 90.0,
    }], order_date=d1)
    await _add_order(PREFIX + "ord_b", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ1",
        "quantity": 1, "unit_price": 45.0, "line_total": 45.0,
    }], order_date=d1)
    await _add_order(PREFIX + "ord_c", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ1",
        "quantity": 1, "unit_price": 85.0, "line_total": 85.0,
    }], order_date=d2)
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert len(r["sales_timeline"]) == 2
    # Sorted asc
    assert r["sales_timeline"][0]["date"] == d1
    assert r["sales_timeline"][0]["tickets_sold"] == 3
    assert r["sales_timeline"][0]["revenue"] == 135.0
    assert r["sales_timeline"][1]["date"] == d2
    assert r["sales_timeline"][1]["tickets_sold"] == 1
    assert r["sales_timeline"][1]["revenue"] == 85.0
    await _cleanup()


async def t08_cross_org_404():
    from routers.event_occurrences import get_occurrence_analytics
    from fastapi import HTTPException
    await _cleanup(); await _seed_basic()
    try:
        await get_occurrence_analytics(PREFIX + "occ1", current_user=_user(OTHER_ORG))
        raise AssertionError("expected 404")
    except HTTPException as e:
        assert e.status_code == 404
    await _cleanup()


async def t09_unknown_occurrence_404():
    from routers.event_occurrences import get_occurrence_analytics
    from fastapi import HTTPException
    await _cleanup()
    try:
        await get_occurrence_analytics(PREFIX + "nope", current_user=_user())
        raise AssertionError("expected 404")
    except HTTPException as e:
        assert e.status_code == 404
    await _cleanup()


async def t10_csv_export_shape():
    """CSV export includes header + one row per issued ticket."""
    from routers.event_occurrences import export_tickets_csv
    await _cleanup(); await _seed_basic()

    # Issue 3 tickets directly for deterministic output
    await issued_tickets_collection.insert_many([
        {"id": PREFIX + "tk1", "organization_id": ORG, "order_id": PREFIX + "ord",
         "occurrence_id": PREFIX + "occ1", "product_id": PREFIX + "p1",
         "tier_id": PREFIX + "t_vip", "tier_label": "VIP",
         "code": "EVT-AAAA-1111", "status": "valid",
         "holder_name": "Mario Rossi", "holder_email": "mario@example.com",
         "seat_index": 1, "seat_count": 2, "created_at": utc_now()},
        {"id": PREFIX + "tk2", "organization_id": ORG, "order_id": PREFIX + "ord",
         "occurrence_id": PREFIX + "occ1", "product_id": PREFIX + "p1",
         "tier_id": PREFIX + "t_vip", "tier_label": "VIP",
         "code": "EVT-BBBB-2222", "status": "checked_in",
         "holder_name": "Mario Rossi", "holder_email": "mario@example.com",
         "seat_index": 2, "seat_count": 2, "created_at": utc_now(),
         "checked_in_at": utc_now()},
        {"id": PREFIX + "tk3", "organization_id": ORG, "order_id": PREFIX + "ord2",
         "occurrence_id": PREFIX + "occ1", "product_id": PREFIX + "p1",
         "tier_id": PREFIX + "t_std", "tier_label": "Standard",
         "code": "EVT-CCCC-3333", "status": "voided",
         "holder_name": "Carla", "holder_email": "carla@example.com",
         "seat_index": 1, "seat_count": 1, "created_at": utc_now()},
    ])

    resp = await export_tickets_csv(PREFIX + "occ1", current_user=_user())
    # StreamingResponse — collect the body
    body_chunks = []
    async for chunk in resp.body_iterator:
        body_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
    body = b"".join(body_chunks).decode("utf-8")
    lines = [l for l in body.splitlines() if l]
    assert lines[0].startswith("code,holder_name,holder_email,tier_label,status")
    assert len(lines) == 1 + 3  # header + 3 tickets
    # Sorted by seat_index 1,2,1 -> order: tk1(1), tk3(1), tk2(2) OR
    # (Mongo sort is on seat_index only; same value ordering undefined)
    assert "EVT-AAAA-1111" in body
    assert "EVT-BBBB-2222" in body
    assert "EVT-CCCC-3333" in body
    assert "VIP" in body and "Standard" in body
    # Headers on response
    assert resp.media_type == "text/csv"
    assert "attachment" in resp.headers.get("Content-Disposition", "")
    await _cleanup()


async def t11_csv_export_empty():
    from routers.event_occurrences import export_tickets_csv
    await _cleanup(); await _seed_basic()
    resp = await export_tickets_csv(PREFIX + "occ1", current_user=_user())
    body_chunks = []
    async for chunk in resp.body_iterator:
        body_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
    body = b"".join(body_chunks).decode("utf-8")
    lines = [l for l in body.splitlines() if l]
    # Header only
    assert len(lines) == 1
    await _cleanup()


async def t12_csv_export_404_unknown():
    from routers.event_occurrences import export_tickets_csv
    from fastapi import HTTPException
    await _cleanup()
    try:
        await export_tickets_csv(PREFIX + "nope", current_user=_user())
        raise AssertionError("expected 404")
    except HTTPException as e:
        assert e.status_code == 404
    await _cleanup()


async def t13_attendance_rate_computed():
    """G5 — attendance_rate = checked_in / (valid+checked_in) * 100."""
    from routers.event_occurrences import get_occurrence_analytics
    from database import issued_tickets_collection
    await _cleanup(); await _seed_basic()
    # Seed 4 tickets: 3 checked_in, 1 valid, 1 voided. Rate = 3/(3+1)*100 = 75%
    from datetime import datetime as _dt
    base_doc = {"organization_id": ORG, "occurrence_id": PREFIX + "occ1",
                "product_id": PREFIX + "p1", "order_id": PREFIX + "x",
                "seat_index": 1, "seat_count": 1, "created_at": _dt.utcnow()}
    await issued_tickets_collection.insert_many([
        {**base_doc, "id": PREFIX + "t1", "code": "C1", "status": "checked_in"},
        {**base_doc, "id": PREFIX + "t2", "code": "C2", "status": "checked_in"},
        {**base_doc, "id": PREFIX + "t3", "code": "C3", "status": "checked_in"},
        {**base_doc, "id": PREFIX + "t4", "code": "C4", "status": "valid"},
        {**base_doc, "id": PREFIX + "t5", "code": "C5", "status": "voided"},
    ])
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert r["checked_in_count"] == 3
    assert r["active_ticket_count"] == 4  # 3 checked + 1 valid, voided excluded
    assert r["attendance_rate"] == 75.0
    await _cleanup()


async def t14_attendance_rate_none_when_no_tickets():
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert r["attendance_rate"] is None
    assert r["checked_in_count"] == 0
    assert r["active_ticket_count"] == 0
    await _cleanup()


async def t15_past_comparison_populated_for_same_product():
    """G5 — past_comparison lists past occurrences of the same product."""
    from routers.event_occurrences import get_occurrence_analytics
    from datetime import datetime as _dt
    await _cleanup(); await _seed_basic()
    # Seed 2 past occurrences of the same product + orders for each
    await event_occurrences_collection.insert_many([
        {"id": PREFIX + "occ_past1", "organization_id": ORG, "product_id": PREFIX + "p1",
         "start_at": "2026-01-10T20:00:00", "status": "closed",
         "capacity": 30, "reserved_seats": 20, "slug": "past1",
         "created_at": utc_now(), "updated_at": utc_now()},
        {"id": PREFIX + "occ_past2", "organization_id": ORG, "product_id": PREFIX + "p1",
         "start_at": "2026-03-10T20:00:00", "status": "closed",
         "capacity": 30, "reserved_seats": 15, "slug": "past2",
         "created_at": utc_now(), "updated_at": utc_now()},
        # Cancelled past — must be excluded from comparison
        {"id": PREFIX + "occ_past_cxl", "organization_id": ORG, "product_id": PREFIX + "p1",
         "start_at": "2026-02-10T20:00:00", "status": "cancelled",
         "capacity": 30, "reserved_seats": 0, "slug": "pastcxl",
         "created_at": utc_now(), "updated_at": utc_now()},
    ])
    await _add_order(PREFIX + "ord_past1", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ_past1",
        "quantity": 20, "unit_price": 30.0, "line_total": 600.0,
    }])
    await _add_order(PREFIX + "ord_past2", [{
        "product_id": PREFIX + "p1", "occurrence_id": PREFIX + "occ_past2",
        "quantity": 15, "unit_price": 40.0, "line_total": 600.0,
    }])
    # The current occurrence (occ1) needs a future-ish start_at for past
    # to be "before". _seed_basic already sets now+30d. Good.
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    ids = [p["occurrence_id"] for p in r["past_comparison"]]
    assert PREFIX + "occ_past1" in ids
    assert PREFIX + "occ_past2" in ids
    assert PREFIX + "occ_past_cxl" not in ids  # cancelled excluded
    # Sorted DESC by start_at (most recent first)
    start_ats = [p["start_at"] for p in r["past_comparison"]]
    assert start_ats == sorted(start_ats, reverse=True)
    # Revenue + tickets aggregated per past event
    p_recent = next(p for p in r["past_comparison"] if p["occurrence_id"] == PREFIX + "occ_past2")
    assert p_recent["revenue"] == 600.0
    assert p_recent["tickets_sold"] == 15
    await _cleanup()


async def t16_past_comparison_limited_to_5():
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    # Seed 7 past occurrences — endpoint must cap at 5
    for i, d in enumerate(["2026-01-01", "2026-02-01", "2026-03-01",
                            "2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01"]):
        await event_occurrences_collection.insert_one({
            "id": f"{PREFIX}occ_p{i}", "organization_id": ORG,
            "product_id": PREFIX + "p1",
            "start_at": f"{d}T20:00:00", "status": "closed",
            "capacity": 10, "reserved_seats": 0, "slug": f"past{i}",
            "created_at": utc_now(), "updated_at": utc_now(),
        })
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert len(r["past_comparison"]) == 5
    await _cleanup()


async def t17_past_comparison_excludes_other_products():
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    # Different product, same org — must NOT appear
    await products_collection.insert_one({
        "id": PREFIX + "p_other", "organization_id": ORG, "name": "Other",
        "item_type": "event_ticket", "is_active": True, "is_published": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    await event_occurrences_collection.insert_one({
        "id": PREFIX + "occ_other_past", "organization_id": ORG,
        "product_id": PREFIX + "p_other",
        "start_at": "2026-01-10T20:00:00", "status": "closed",
        "capacity": 10, "reserved_seats": 0, "slug": "other-past",
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert r["past_comparison"] == []
    await _cleanup()


async def t18_past_comparison_empty_for_first_event():
    from routers.event_occurrences import get_occurrence_analytics
    await _cleanup(); await _seed_basic()
    r = await get_occurrence_analytics(PREFIX + "occ1", current_user=_user())
    assert r["past_comparison"] == []
    await _cleanup()


TESTS: list[tuple[str, Callable]] = [
    ("t01 empty occurrence -> zeros", t01_empty_occurrence_returns_zeros),
    ("t02 single-tier revenue", t02_single_tier_revenue),
    ("t03 multi-tier aggregated + sorted desc", t03_multi_tier_aggregated),
    ("t04 cancelled orders excluded", t04_cancelled_orders_excluded),
    ("t05 tier_label fallback from tier doc", t05_tier_label_fallback_from_tier_doc),
    ("t06 mono-tier (no tier_id) emits null row", t06_mono_tier_no_tier_id),
    ("t07 sales_timeline groups by day", t07_sales_timeline_groups_by_day),
    ("t08 analytics cross-org 404", t08_cross_org_404),
    ("t09 analytics unknown occurrence 404", t09_unknown_occurrence_404),
    ("t10 CSV export shape + all 3 tickets", t10_csv_export_shape),
    ("t11 CSV export empty = header only", t11_csv_export_empty),
    ("t12 CSV export 404 unknown", t12_csv_export_404_unknown),
    ("t13 G5 attendance_rate 75% with 3 in / 1 valid / 1 voided", t13_attendance_rate_computed),
    ("t14 G5 attendance_rate None when no tickets", t14_attendance_rate_none_when_no_tickets),
    ("t15 G5 past_comparison lists same-product past occurrences", t15_past_comparison_populated_for_same_product),
    ("t16 G5 past_comparison capped at 5", t16_past_comparison_limited_to_5),
    ("t17 G5 past_comparison excludes other products", t17_past_comparison_excludes_other_products),
    ("t18 G5 past_comparison empty for first event", t18_past_comparison_empty_for_first_event),
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
