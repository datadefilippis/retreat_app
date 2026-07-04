"""Wave 7C.3 — events calendar tool + CALENDAR prompt section.

Tests:
  1. query_events_calendar — operational forward view of public events
  2. _PROMPT_CALENDAR is present in chat_service and includes
     all three calendar surfaces (agenda / rentals / events)
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


def _fake_find_cursor(docs: list[dict]):
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


def _patch_event_occurrences(docs: list[dict]):
    """Patch database.db.event_occurrences to return docs via cursor.

    Note: query_events_calendar uses
    `__import__('database', fromlist=['db']).db.event_occurrences`
    so we patch the actual `db.event_occurrences` attribute.
    """
    import database as db_mod
    coll = MagicMock()
    coll.find.return_value = _fake_find_cursor(docs)
    return patch.object(db_mod.db, "event_occurrences", coll)


def _patch_orders(agg_docs: list[dict]):
    coll = MagicMock()
    coll.aggregate = MagicMock(return_value=_fake_agg_cursor(agg_docs))
    return patch("database.orders_collection", coll)


def _patch_currency():
    return patch(
        "modules.commerce.ai_tools._get_org_currency",
        new=AsyncMock(return_value="EUR"),
    )


# ── query_events_calendar ────────────────────────────────────────────────────

async def test_events_calendar_returns_forward_view():
    from modules.commerce.ai_tools import execute_tool
    from datetime import date, timedelta

    today = date.today()
    in_3d = today + timedelta(days=3)
    occ_docs = [
        {"id": "occ1", "product_name": "Concerto Rock",
         "start_at": f"{in_3d.isoformat()}T20:30:00",
         "location": "Teatro X", "capacity": 200, "status": "published"},
        {"id": "occ2", "product_name": "Workshop",
         "start_at": f"{(today + timedelta(days=10)).isoformat()}T09:00:00",
         "location": None, "capacity": 30, "status": "published"},
    ]
    # Booked counts
    agg_docs = [
        {"_id": "occ1", "booked": 150},
        {"_id": "occ2", "booked": 5},
    ]

    with _patch_event_occurrences(occ_docs), _patch_orders(agg_docs), _patch_currency():
        result = await execute_tool(
            "org_x", "query_events_calendar", {"days_ahead": 14},
        )

    assert result["has_data"] is True
    assert result["total_events"] == 2
    assert result["future_events"] == 2
    assert result["past_events"] == 0
    # 150/200 = 75%
    rock = next(e for e in result["events"] if e["event_id"] == "occ1")
    assert rock["fill_rate_pct"] == 75.0
    assert rock["days_until"] == 3
    assert rock["status_label"] == "upcoming"
    # next_event surfaces the closest
    assert result["next_event"]["name"] == "Concerto Rock"
    assert result["next_event"]["days_until"] == 3


async def test_events_calendar_empty_caveat():
    from modules.commerce.ai_tools import execute_tool

    with _patch_event_occurrences([]), _patch_orders([]), _patch_currency():
        result = await execute_tool(
            "org_x", "query_events_calendar", {},
        )

    assert result["has_data"] is False
    assert result["_caveat"] is not None


async def test_events_calendar_clamps_days_ahead():
    from modules.commerce.ai_tools import execute_tool

    with _patch_event_occurrences([]), _patch_orders([]), _patch_currency():
        r = await execute_tool(
            "org_x", "query_events_calendar", {"days_ahead": 999},
        )
    assert r["range"]["days_ahead"] == 60


async def test_events_calendar_include_past_widens_window():
    from modules.commerce.ai_tools import execute_tool

    with _patch_event_occurrences([]), _patch_orders([]), _patch_currency():
        r = await execute_tool(
            "org_x", "query_events_calendar",
            {"days_ahead": 7, "include_past": True},
        )
    assert r["range"]["include_past"] is True


async def test_events_calendar_handles_missing_capacity():
    """Events with capacity=None should not crash; fill_rate=None."""
    from modules.commerce.ai_tools import execute_tool
    from datetime import date, timedelta

    today = date.today()
    occ_docs = [
        {"id": "occ_free", "product_name": "Open mic",
         "start_at": f"{(today + timedelta(days=5)).isoformat()}T19:00:00",
         "capacity": None, "status": "published"},
    ]

    with _patch_event_occurrences(occ_docs), _patch_orders([]), _patch_currency():
        result = await execute_tool(
            "org_x", "query_events_calendar", {},
        )

    event = result["events"][0]
    assert event["capacity"] is None
    assert event["fill_rate_pct"] is None
    # Caveat surfaces the missing-capacity case
    assert "capacity" in (result["epistemic"]["caveat"] or "").lower()


# ── Registration check ──────────────────────────────────────────────────────

async def test_events_calendar_tool_registered():
    from modules.commerce.ai_tools import TOOL_DEFINITIONS
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert "query_events_calendar" in names


# ── _PROMPT_CALENDAR section ────────────────────────────────────────────────

def test_prompt_calendar_section_exists():
    from services.chat_service import _PROMPT_CALENDAR
    assert "CALENDAR DISCIPLINE" in _PROMPT_CALENDAR


def test_prompt_calendar_covers_three_surfaces():
    """The section must enumerate AGENDA, RENTALS and EVENTS by name."""
    from services.chat_service import _PROMPT_CALENDAR
    assert "AGENDA" in _PROMPT_CALENDAR
    assert "RENTALS" in _PROMPT_CALENDAR
    assert "EVENTS" in _PROMPT_CALENDAR


def test_prompt_calendar_mentions_key_tools_per_surface():
    """Each surface should reference at least one of its dedicated tools."""
    from services.chat_service import _PROMPT_CALENDAR
    assert "query_agenda_today" in _PROMPT_CALENDAR
    assert "query_rentals_today" in _PROMPT_CALENDAR
    assert "query_events_calendar" in _PROMPT_CALENDAR


def test_prompt_calendar_appended_when_commerce_active():
    """_PROMPT_CALENDAR should be in the assembled prompt when commerce is active."""
    from services.chat_service import _build_system_prompt
    from core.locale_utils import get_locale_profile

    profile = get_locale_profile("it")
    prompt = _build_system_prompt(
        {"commerce", "cashflow_monitor"}, profile, "2026-05-15",
    )
    assert "CALENDAR DISCIPLINE" in prompt


def test_prompt_calendar_skipped_when_commerce_inactive():
    """Without commerce active, the calendar section should not appear."""
    from services.chat_service import _build_system_prompt
    from core.locale_utils import get_locale_profile

    profile = get_locale_profile("it")
    prompt = _build_system_prompt(
        {"cashflow_monitor"}, profile, "2026-05-15",
    )
    assert "CALENDAR DISCIPLINE" not in prompt
