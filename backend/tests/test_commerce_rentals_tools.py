"""Wave 7C.2 — rental calendar tools in modules.commerce.

Tests pin the contract of 5 forward-looking rental tools:
  - query_rentals_today        (active reservations covering today)
  - query_rentals_upcoming     (rentals starting in N days)
  - query_rentals_returning    (rentals ending in N days)
  - query_rental_availability  (single asset day-by-day calendar)
  - query_rental_pipeline      (aggregate forward view per asset)

Source of truth: issued_reservations_collection (reservation_flavor =
range | slot). Tests mock cursors so no MongoDB needed.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fake_find_cursor(docs: list[dict]):
    async def _aiter():
        for d in docs:
            yield d
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.__aiter__ = lambda self: _aiter()
    return cursor


def _fake_agg_cursor(docs: list[dict]):
    async def _aiter():
        for d in docs:
            yield d
    cursor = MagicMock()
    cursor.__aiter__ = lambda self: _aiter()
    return cursor


def _patch_reservations(side_effect_find: list[list[dict]] | None = None,
                        side_effect_agg: list[list[dict]] | None = None):
    coll = MagicMock()
    if side_effect_find is not None:
        cursors = [_fake_find_cursor(d) for d in side_effect_find]
        coll.find = MagicMock(side_effect=cursors)
    if side_effect_agg is not None:
        agg_cursors = [_fake_agg_cursor(d) for d in side_effect_agg]
        coll.aggregate = MagicMock(side_effect=agg_cursors)
    return patch("database.issued_reservations_collection", coll), coll


def _patch_products(find_one_result: dict | None):
    coll = MagicMock()
    coll.find_one = AsyncMock(return_value=find_one_result)
    return patch("database.products_collection", coll), coll


def _patch_currency():
    return patch(
        "modules.commerce.ai_tools._get_org_currency",
        new=AsyncMock(return_value="EUR"),
    )


# ── query_rentals_today ──────────────────────────────────────────────────────

async def test_rentals_today_returns_active_today():
    from modules.commerce.ai_tools import execute_tool

    today = date.today().isoformat()
    docs = [
        {"product_id": "bike1", "product_name": "E-bike",
         "reservation_flavor": "range",
         "date_from": today, "date_to": (date.today() + timedelta(days=2)).isoformat(),
         "code": "RSV-AA", "holder_name": "Mario"},
        {"product_id": "court1", "product_name": "Campo Tennis",
         "reservation_flavor": "slot",
         "slot_date": today, "slot_start_time": "10:00", "slot_end_time": "11:00",
         "code": "RSV-BB", "holder_name": "Anna"},
    ]
    ctx, _ = _patch_reservations(side_effect_find=[docs])
    with ctx, _patch_currency():
        result = await execute_tool("org_x", "query_rentals_today", {})

    assert result["has_data"] is True
    assert result["total_active"] == 2
    assert result["by_flavor"]["range"] == 1
    assert result["by_flavor"]["slot"] == 1
    # Range rental has days_remaining
    bike = next(r for r in result["rentals"] if r["product_id"] == "bike1")
    assert bike["days_remaining"] == 2
    # Slot rental has start_time/end_time
    court = next(r for r in result["rentals"] if r["product_id"] == "court1")
    assert court["start_time"] == "10:00"


async def test_rentals_today_empty():
    from modules.commerce.ai_tools import execute_tool

    ctx, _ = _patch_reservations(side_effect_find=[[]])
    with ctx, _patch_currency():
        result = await execute_tool("org_x", "query_rentals_today", {})

    assert result["has_data"] is False
    assert result["total_active"] == 0


# ── query_rentals_upcoming ───────────────────────────────────────────────────

async def test_rentals_upcoming_sorts_by_days_until():
    from modules.commerce.ai_tools import execute_tool

    today = date.today()
    d3 = (today + timedelta(days=3)).isoformat()
    d5 = (today + timedelta(days=5)).isoformat()
    docs = [
        {"product_id": "p1", "product_name": "Asset A",
         "reservation_flavor": "range",
         "date_from": d5, "date_to": (today + timedelta(days=7)).isoformat(),
         "code": "RSV-1", "holder_name": "Cust A"},
        {"product_id": "p2", "product_name": "Asset B",
         "reservation_flavor": "range",
         "date_from": d3, "date_to": (today + timedelta(days=4)).isoformat(),
         "code": "RSV-2", "holder_name": "Cust B"},
    ]
    ctx, _ = _patch_reservations(side_effect_find=[docs])
    with ctx, _patch_currency():
        result = await execute_tool("org_x", "query_rentals_upcoming",
                                     {"days_ahead": 14})

    assert result["has_data"] is True
    assert result["total_upcoming"] == 2
    # Sorted by days_until → p2 (3) before p1 (5)
    assert result["rentals"][0]["product_id"] == "p2"
    assert result["next_rental"]["product_name"] == "Asset B"
    assert result["next_rental"]["days_until"] == 3


async def test_rentals_upcoming_clamps_days_ahead():
    from modules.commerce.ai_tools import execute_tool

    ctx, _ = _patch_reservations(side_effect_find=[[]])
    with ctx, _patch_currency():
        r = await execute_tool("org_x", "query_rentals_upcoming",
                                {"days_ahead": 999})
    assert r["range"]["days_ahead"] == 60


# ── query_rentals_returning ──────────────────────────────────────────────────

async def test_rentals_returning_tracks_today_tomorrow():
    from modules.commerce.ai_tools import execute_tool

    today = date.today()
    today_str = today.isoformat()
    tomorrow_str = (today + timedelta(days=1)).isoformat()
    docs = [
        {"product_id": "p1", "product_name": "Asset A",
         "date_from": (today - timedelta(days=3)).isoformat(),
         "date_to": today_str,
         "code": "RSV-1", "holder_name": "C1"},
        {"product_id": "p2", "product_name": "Asset B",
         "date_from": (today - timedelta(days=2)).isoformat(),
         "date_to": tomorrow_str,
         "code": "RSV-2", "holder_name": "C2"},
    ]
    ctx, _ = _patch_reservations(side_effect_find=[docs])
    with ctx, _patch_currency():
        result = await execute_tool("org_x", "query_rentals_returning",
                                     {"days_ahead": 5})

    assert result["has_data"] is True
    assert result["total_returning"] == 2
    assert result["returning_today"] == 1
    assert result["returning_tomorrow"] == 1


# ── query_rental_availability ────────────────────────────────────────────────

async def test_rental_availability_marks_booked_days():
    from modules.commerce.ai_tools import execute_tool

    start = "2026-05-10"
    end = "2026-05-15"  # 6 days

    # 1 range reservation 5/12 to 5/13 (2 days)
    docs = [
        {"reservation_flavor": "range",
         "date_from": "2026-05-12", "date_to": "2026-05-13",
         "code": "RSV-1", "holder_name": "Mario"},
    ]
    ctx_r, _ = _patch_reservations(side_effect_find=[docs])
    ctx_p, _ = _patch_products({"name": "E-bike Pro"})

    with ctx_r, ctx_p, _patch_currency():
        result = await execute_tool(
            "org_x", "query_rental_availability",
            {"product_id": "bike1", "start_date": start, "end_date": end},
        )

    assert result["has_data"] is True
    assert result["product"]["name"] == "E-bike Pro"
    assert result["period"]["days"] == 6
    # Days marked booked: 2 (5/12, 5/13)
    assert result["summary"]["booked_days"] == 2
    assert result["summary"]["free_days"] == 4
    # utilization = 2/6 ≈ 33.3%
    assert result["summary"]["utilization_pct"] == 33.3
    # Verify the specific day flags
    by_date = {d["date"]: d["booked"] for d in result["days"]}
    assert by_date["2026-05-11"] is False
    assert by_date["2026-05-12"] is True
    assert by_date["2026-05-13"] is True
    assert by_date["2026-05-14"] is False


async def test_rental_availability_missing_asset():
    from modules.commerce.ai_tools import execute_tool

    ctx_r, _ = _patch_reservations(side_effect_find=[[]])
    ctx_p, _ = _patch_products(None)

    with ctx_r, ctx_p, _patch_currency():
        result = await execute_tool(
            "org_x", "query_rental_availability",
            {"product_id": "ghost", "start_date": "2026-05-10",
             "end_date": "2026-05-15"},
        )

    assert result["has_data"] is False
    assert "non trovato" in result["error"]


async def test_rental_availability_rejects_too_wide_range():
    from modules.commerce.ai_tools import execute_tool

    ctx_r, _ = _patch_reservations(side_effect_find=[[]])
    ctx_p, _ = _patch_products({"name": "X"})
    with ctx_r, ctx_p, _patch_currency():
        r = await execute_tool(
            "org_x", "query_rental_availability",
            {"product_id": "p1", "start_date": "2026-01-01",
             "end_date": "2026-12-31"},
        )
    assert "error" in r


# ── query_rental_pipeline ────────────────────────────────────────────────────

async def test_rental_pipeline_ranks_top_assets():
    from modules.commerce.ai_tools import execute_tool

    today = date.today()
    d2 = (today + timedelta(days=2)).isoformat()

    agg_docs = [
        {"_id": {"product_id": "bike1", "product_name": "E-bike"}, "count": 5},
        {"_id": {"product_id": "kayak1", "product_name": "Kayak"}, "count": 3},
    ]
    earliest_docs = [
        {"product_name": "E-bike", "reservation_flavor": "range",
         "date_from": d2, "holder_name": "Mario"},
    ]

    ctx, _ = _patch_reservations(
        side_effect_agg=[agg_docs],
        side_effect_find=[earliest_docs],
    )
    with ctx, _patch_currency():
        result = await execute_tool("org_x", "query_rental_pipeline",
                                     {"days_ahead": 30})

    assert result["has_data"] is True
    assert result["total_future_rentals"] == 8
    assert len(result["top_assets_by_volume"]) == 2
    assert result["top_assets_by_volume"][0]["product_name"] == "E-bike"
    assert result["next_rental"]["product_name"] == "E-bike"
    assert result["next_rental"]["days_until"] == 2


async def test_rental_pipeline_clamps_days_ahead():
    from modules.commerce.ai_tools import execute_tool

    ctx, _ = _patch_reservations(
        side_effect_agg=[[]],
        side_effect_find=[[]],
    )
    with ctx, _patch_currency():
        r = await execute_tool("org_x", "query_rental_pipeline",
                                {"days_ahead": 9999})
    assert r["range"]["days_ahead"] == 90


# ── Registration check ──────────────────────────────────────────────────────

async def test_all_5_rental_tools_registered():
    from modules.commerce.ai_tools import TOOL_DEFINITIONS
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert {
        "query_rentals_today",
        "query_rentals_upcoming",
        "query_rentals_returning",
        "query_rental_availability",
        "query_rental_pipeline",
    }.issubset(names), f"Missing rental tools: {names}"
