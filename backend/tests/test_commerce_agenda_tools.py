"""Wave 7C.1 — agenda calendar tools in modules.commerce.

Tests pin the contract of 5 agenda/service tools:
  - query_agenda_today
  - query_agenda_upcoming
  - query_agenda_summary
  - query_free_slots
  - query_blocked_periods

Mocks issued_bookings_collection, availability_rules_collection,
blocked_slots_collection so tests don't need MongoDB. Scope-awareness
(agenda vs rentals) is exercised end-to-end.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fake_find_cursor(docs: list[dict]):
    """Build a fake Motor cursor that supports .sort(...).to_list / async iteration."""
    async def _aiter():
        for d in docs:
            yield d
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.to_list = AsyncMock(return_value=docs)
    cursor.__aiter__ = lambda self: _aiter()
    return cursor


def _fake_agg_cursor(docs: list[dict]):
    async def _aiter():
        for d in docs:
            yield d
    cursor = MagicMock()
    cursor.__aiter__ = lambda self: _aiter()
    return cursor


def _patch_bookings(side_effect_find: list[list[dict]] | None = None,
                    side_effect_agg: list[list[dict]] | None = None):
    """Patch issued_bookings_collection.find AND .aggregate to return cursors per call."""
    coll = MagicMock()
    if side_effect_find is not None:
        cursors = [_fake_find_cursor(d) for d in side_effect_find]
        coll.find = MagicMock(side_effect=cursors)
    if side_effect_agg is not None:
        agg_cursors = [_fake_agg_cursor(d) for d in side_effect_agg]
        coll.aggregate = MagicMock(side_effect=agg_cursors)
    return patch("database.issued_bookings_collection", coll), coll


def _patch_blocks(side_effect_find: list[list[dict]] | None = None,
                  count_documents: list[int] | None = None):
    coll = MagicMock()
    if side_effect_find is not None:
        cursors = [_fake_find_cursor(d) for d in side_effect_find]
        coll.find = MagicMock(side_effect=cursors)
    if count_documents is not None:
        coll.count_documents = AsyncMock(side_effect=count_documents)
    return patch("database.blocked_slots_collection", coll), coll


def _patch_rules(rules: list[dict]):
    coll = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=rules)
    coll.find.return_value = cursor
    return patch("database.availability_rules_collection", coll), coll


def _patch_currency():
    return patch(
        "modules.commerce.ai_tools._get_org_currency",
        new=AsyncMock(return_value="EUR"),
    )


# ── query_agenda_today ───────────────────────────────────────────────────────

async def test_agenda_today_returns_bookings_and_blocks():
    from modules.commerce.ai_tools import execute_tool

    bookings = [
        {"booking_start_time": "09:00", "booking_end_time": "10:00",
         "service_option_label": "Consulenza fiscale", "holder_name": "Mario Rossi",
         "location": "Studio", "code": "BKG-AAAA-AAAA", "status": "confirmed"},
        {"booking_start_time": "11:00", "booking_end_time": "12:00",
         "service_option_label": "Audit", "holder_name": "Anna Verdi",
         "code": "BKG-BBBB-BBBB", "status": "completed"},
    ]
    blocks = [
        {"start_time": "13:00", "end_time": "14:00",
         "reason": "personal", "note": "Pranzo"},
    ]
    ctx_b, _ = _patch_bookings(side_effect_find=[bookings])
    ctx_bl, _ = _patch_blocks(side_effect_find=[blocks])
    with ctx_b, ctx_bl, _patch_currency():
        result = await execute_tool("org_x", "query_agenda_today", {})

    assert result["has_data"] is True
    assert len(result["bookings"]) == 2
    assert result["bookings"][0]["customer"] == "Mario Rossi"
    assert result["bookings"][0]["service"] == "Consulenza fiscale"
    assert result["summary"]["confirmed_appointments"] == 1
    assert result["summary"]["total_appointments"] == 2
    assert result["summary"]["first_appointment_at"] == "09:00"
    assert result["summary"]["last_appointment_at"] == "12:00"
    assert len(result["blocks"]) == 1
    assert result["blocks"][0]["reason"] == "personal"


async def test_agenda_today_empty_day_caveat():
    from modules.commerce.ai_tools import execute_tool

    ctx_b, _ = _patch_bookings(side_effect_find=[[]])
    ctx_bl, _ = _patch_blocks(side_effect_find=[[]])
    with ctx_b, ctx_bl, _patch_currency():
        result = await execute_tool("org_x", "query_agenda_today", {})

    assert result["has_data"] is False
    assert "libera" in result["_caveat"].lower()


# ── query_agenda_upcoming ────────────────────────────────────────────────────

async def test_agenda_upcoming_aggregates_per_day():
    from modules.commerce.ai_tools import execute_tool

    today = date.today()
    d0 = today.isoformat()
    d1 = (today + timedelta(days=1)).isoformat()

    bookings = [
        {"booking_date": d0, "booking_start_time": "09:00",
         "service_option_label": "S1", "holder_name": "C1",
         "status": "confirmed", "code": "B1"},
        {"booking_date": d0, "booking_start_time": "11:00",
         "service_option_label": "S2", "holder_name": "C2",
         "status": "cancelled", "code": "B2"},
        {"booking_date": d1, "booking_start_time": "10:00",
         "service_option_label": "S3", "holder_name": "C3",
         "status": "confirmed", "code": "B3"},
    ]
    ctx_b, _ = _patch_bookings(side_effect_find=[bookings])
    with ctx_b, _patch_currency():
        result = await execute_tool(
            "org_x", "query_agenda_upcoming", {"days_ahead": 3},
        )

    assert result["has_data"] is True
    assert result["summary"]["total_confirmed"] == 2
    assert result["summary"]["total_cancelled"] == 1
    assert len(result["days"]) == 3  # range filled
    # day 0 has 2 (1 confirmed + 1 cancelled)
    day0 = result["days"][0]
    assert day0["confirmed"] == 1
    assert day0["cancelled"] == 1
    # busiest day: day0 (1 confirmed) vs day1 (1 confirmed) — tie, first wins
    assert result["summary"]["busiest_day"] in (d0, d1)


async def test_agenda_upcoming_clamps_days_ahead():
    from modules.commerce.ai_tools import execute_tool

    ctx_b, _ = _patch_bookings(side_effect_find=[[]])
    with ctx_b, _patch_currency():
        result = await execute_tool(
            "org_x", "query_agenda_upcoming", {"days_ahead": 999},
        )
    assert result["range"]["days_ahead"] == 30


async def test_agenda_upcoming_handles_garbage_input():
    from modules.commerce.ai_tools import execute_tool

    ctx_b, _ = _patch_bookings(side_effect_find=[[]])
    with ctx_b, _patch_currency():
        r = await execute_tool(
            "org_x", "query_agenda_upcoming", {"days_ahead": "notanumber"},
        )
    assert r["range"]["days_ahead"] == 7


# ── query_agenda_summary ─────────────────────────────────────────────────────

async def test_agenda_summary_combines_3_windows_and_free_slots():
    from modules.commerce.ai_tools import execute_tool

    # 3 aggregate calls: today, tomorrow, week
    today_agg = [{"_id": "confirmed", "n": 3}, {"_id": "cancelled", "n": 1}]
    tomorrow_agg = [{"_id": "confirmed", "n": 2}]
    week_agg = [{"_id": "confirmed", "n": 8}, {"_id": "completed", "n": 4}]

    today_dow = date.today().weekday()
    rules = [
        {"day_of_week": today_dow, "start_time": "09:00",
         "end_time": "13:00", "slot_duration_minutes": 60, "is_active": True},
        {"day_of_week": today_dow, "start_time": "14:00",
         "end_time": "18:00", "slot_duration_minutes": 60, "is_active": True},
    ]
    # 4 + 4 = 8 slots today. confirmed+completed today = 3+0=3. blocks (non-rental/non-booking) = 1.
    # free = 8 - 3 - 1 = 4.

    ctx_b, _ = _patch_bookings(side_effect_agg=[today_agg, tomorrow_agg, week_agg])
    ctx_r, _ = _patch_rules(rules)
    ctx_bl, _ = _patch_blocks(count_documents=[1])
    with ctx_b, ctx_r, ctx_bl, _patch_currency():
        result = await execute_tool("org_x", "query_agenda_summary", {})

    assert result["today"]["confirmed"] == 3
    assert result["today"]["cancelled"] == 1
    assert result["tomorrow"]["confirmed"] == 2
    assert result["this_week"]["completed"] == 4
    assert result["today_total_slots"] == 8
    assert result["free_slots_today"] == 4
    assert result["has_data"] is True


# ── query_free_slots ─────────────────────────────────────────────────────────

async def test_free_slots_respects_rules_blocks_bookings():
    from modules.commerce.ai_tools import execute_tool

    start = "2026-05-15"  # Friday (weekday 4)
    end = "2026-05-15"

    # Rules: Friday 09-12 = 3 hourly slots
    rules = [
        {"day_of_week": 4, "start_time": "09:00",
         "end_time": "12:00", "slot_duration_minutes": 60, "is_active": True},
    ]
    # 1 block on that day
    blocks = [{"date": start, "start_time": "09:00", "end_time": "10:00"}]
    # 1 booking
    booking_agg = [{"_id": start, "n": 1}]

    ctx_b, _ = _patch_bookings(side_effect_agg=[booking_agg])
    ctx_r, _ = _patch_rules(rules)
    ctx_bl, _ = _patch_blocks(side_effect_find=[blocks])
    with ctx_b, ctx_r, ctx_bl, _patch_currency():
        result = await execute_tool(
            "org_x", "query_free_slots",
            {"start_date": start, "end_date": end},
        )

    assert result["has_data"] is True
    assert len(result["days"]) == 1
    day = result["days"][0]
    assert day["total_slots"] == 3
    assert day["booked_slots"] == 1
    assert day["blocked_count"] == 1
    assert day["free_slots"] == 1  # 3 - 1 - 1
    assert day["approximate_first_free"] == "09:00"
    # utilization = 1 - 1/3 ≈ 66.7%
    assert result["summary"]["utilization_pct"] == 66.7


async def test_free_slots_rejects_too_wide_range():
    from modules.commerce.ai_tools import execute_tool

    ctx_b, _ = _patch_bookings(side_effect_agg=[[]])
    ctx_r, _ = _patch_rules([])
    ctx_bl, _ = _patch_blocks(side_effect_find=[[]])
    with ctx_b, ctx_r, ctx_bl, _patch_currency():
        r = await execute_tool(
            "org_x", "query_free_slots",
            {"start_date": "2026-01-01", "end_date": "2026-12-31"},
        )
    assert "error" in r
    assert "30" in r["error"]


async def test_free_slots_rejects_inverted_range():
    from modules.commerce.ai_tools import execute_tool

    ctx_b, _ = _patch_bookings(side_effect_agg=[[]])
    ctx_r, _ = _patch_rules([])
    ctx_bl, _ = _patch_blocks(side_effect_find=[[]])
    with ctx_b, ctx_r, ctx_bl, _patch_currency():
        r = await execute_tool(
            "org_x", "query_free_slots",
            {"start_date": "2026-05-15", "end_date": "2026-05-10"},
        )
    assert "error" in r


# ── query_blocked_periods ────────────────────────────────────────────────────

async def test_blocked_periods_groups_by_reason():
    from modules.commerce.ai_tools import execute_tool

    blocks = [
        {"date": "2026-05-12", "start_time": "09:00", "end_time": "18:00",
         "reason": "holiday", "note": "Ferie"},
        {"date": "2026-05-13", "start_time": "12:00", "end_time": "13:00",
         "reason": "personal", "note": "Pranzo"},
        {"date": "2026-05-14", "start_time": "10:00", "end_time": "11:00",
         "reason": "booking", "note": None},
    ]
    ctx, _ = _patch_blocks(side_effect_find=[blocks])
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_blocked_periods",
            {"start_date": "2026-05-12", "end_date": "2026-05-14"},
        )

    assert result["has_data"] is True
    assert result["total_blocks"] == 3
    assert result["by_reason"] == {"holiday": 1, "personal": 1, "booking": 1}
    assert result["periods"][0]["date"] == "2026-05-12"
    assert result["filter_applied"] is None


async def test_blocked_periods_with_reason_filter():
    from modules.commerce.ai_tools import execute_tool

    blocks = [
        {"date": "2026-05-12", "start_time": "09:00", "end_time": "18:00",
         "reason": "holiday", "note": "Ferie"},
    ]
    ctx, _ = _patch_blocks(side_effect_find=[blocks])
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_blocked_periods",
            {"start_date": "2026-05-01", "end_date": "2026-05-31",
             "reason": "holiday"},
        )

    assert result["filter_applied"] == "holiday"
    assert result["by_reason"] == {"holiday": 1}


# ── Registration check ──────────────────────────────────────────────────────

async def test_all_5_agenda_tools_registered():
    from modules.commerce.ai_tools import TOOL_DEFINITIONS
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert {
        "query_agenda_today",
        "query_agenda_upcoming",
        "query_agenda_summary",
        "query_free_slots",
        "query_blocked_periods",
    }.issubset(names), f"Missing agenda tools: {names}"
