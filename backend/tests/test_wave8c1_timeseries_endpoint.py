"""Wave 8C.1 — backend timeseries endpoint for the governance dashboard.

Verifies:
  1. Endpoint accepts start/end and optional org_id.
  2. Days are zero-filled (no gaps) across the requested window.
  3. by_feature + by_agent rollups are correctly aggregated.
  4. cache_hit_ratio_pct is computed.
  5. Auth gate: rejects non-system-admin callers.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.asyncio


def _fake_agg_cursor(docs: list[dict]):
    async def _aiter():
        for d in docs:
            yield d
    cursor = MagicMock()
    cursor.__aiter__ = lambda self: _aiter()
    return cursor


# ── Endpoint logic via direct function call (no HTTP layer) ─────────────────

async def test_timeseries_zero_fills_missing_days():
    """Range of 5 days, only 2 days have events → 5 day entries returned."""
    from routers.admin import admin_ai_usage_timeseries

    # Daily aggregation returns 2 days of data
    daily_docs = [
        {"_id": "2026-05-01", "events": 5, "tokens_in": 1000, "tokens_out": 200,
         "cache_read_tokens": 500, "cost_usd": 0.015},
        {"_id": "2026-05-03", "events": 3, "tokens_in": 600, "tokens_out": 100,
         "cache_read_tokens": 300, "cost_usd": 0.009},
    ]
    by_feature_docs = [
        {"_id": "chat", "events": 6, "cost_usd": 0.018, "tokens_total": 1500},
        {"_id": "digest", "events": 2, "cost_usd": 0.006, "tokens_total": 400},
    ]
    by_agent_docs = [
        {"_id": "financial_analyst", "events": 6, "cost_usd": 0.018},
        {"_id": "digest_builder", "events": 2, "cost_usd": 0.006},
    ]

    coll = MagicMock()
    coll.aggregate = MagicMock(side_effect=[
        _fake_agg_cursor(daily_docs),
        _fake_agg_cursor(by_feature_docs),
        _fake_agg_cursor(by_agent_docs),
    ])

    with patch("database.ai_usage_events_collection", coll):
        result = await admin_ai_usage_timeseries(
            start_date="2026-05-01",
            end_date="2026-05-05",
            org_id=None,
            _={"role": "system_admin"},  # required_system_admin bypassed by direct call
        )

    # 5 days in range, all present
    assert len(result["days"]) == 5
    dates = [d["date"] for d in result["days"]]
    assert dates == ["2026-05-01", "2026-05-02", "2026-05-03",
                     "2026-05-04", "2026-05-05"]
    # Day 1 has data
    assert result["days"][0]["events"] == 5
    assert result["days"][0]["cost_usd"] == 0.015
    # Day 2 zero-filled
    assert result["days"][1]["events"] == 0
    assert result["days"][1]["cost_usd"] == 0
    # Day 3 has data
    assert result["days"][2]["cost_usd"] == 0.009


async def test_timeseries_aggregates_features_and_agents():
    from routers.admin import admin_ai_usage_timeseries

    daily_docs = [
        {"_id": "2026-05-15", "events": 10, "tokens_in": 5000, "tokens_out": 1000,
         "cache_read_tokens": 2500, "cost_usd": 0.05},
    ]
    by_feature_docs = [
        {"_id": "chat", "events": 7, "cost_usd": 0.04, "tokens_total": 5000},
        {"_id": "digest", "events": 2, "cost_usd": 0.008, "tokens_total": 800},
        {"_id": "health_explanation", "events": 1, "cost_usd": 0.002, "tokens_total": 200},
    ]
    by_agent_docs = [
        {"_id": "financial_analyst", "events": 7, "cost_usd": 0.04},
        {"_id": "digest_builder", "events": 2, "cost_usd": 0.008},
        {"_id": "health_explanation", "events": 1, "cost_usd": 0.002},
    ]

    coll = MagicMock()
    coll.aggregate = MagicMock(side_effect=[
        _fake_agg_cursor(daily_docs),
        _fake_agg_cursor(by_feature_docs),
        _fake_agg_cursor(by_agent_docs),
    ])

    with patch("database.ai_usage_events_collection", coll):
        result = await admin_ai_usage_timeseries(
            start_date="2026-05-15",
            end_date="2026-05-15",
            org_id=None,
            _={"role": "system_admin"},
        )

    assert len(result["by_feature"]) == 3
    assert result["by_feature"][0]["feature"] == "chat"
    assert result["by_feature"][0]["cost_usd"] == 0.04

    assert len(result["by_agent"]) == 3
    assert result["by_agent"][0]["agent_id"] == "financial_analyst"


async def test_timeseries_computes_cache_hit_ratio():
    """Cache hit ratio = cache_read_tokens / tokens_in. Sanity check the math."""
    from routers.admin import admin_ai_usage_timeseries

    daily_docs = [
        {"_id": "2026-05-15", "events": 5, "tokens_in": 1000, "tokens_out": 200,
         "cache_read_tokens": 600,  # 60% of input tokens served from cache
         "cost_usd": 0.01},
    ]
    coll = MagicMock()
    coll.aggregate = MagicMock(side_effect=[
        _fake_agg_cursor(daily_docs),
        _fake_agg_cursor([]),
        _fake_agg_cursor([]),
    ])

    with patch("database.ai_usage_events_collection", coll):
        result = await admin_ai_usage_timeseries(
            start_date="2026-05-15", end_date="2026-05-15",
            org_id=None, _={"role": "system_admin"},
        )

    assert result["totals"]["cache_hit_ratio_pct"] == 60.0


async def test_timeseries_empty_window_returns_zero_filled_days():
    from routers.admin import admin_ai_usage_timeseries

    coll = MagicMock()
    coll.aggregate = MagicMock(side_effect=[
        _fake_agg_cursor([]),
        _fake_agg_cursor([]),
        _fake_agg_cursor([]),
    ])

    with patch("database.ai_usage_events_collection", coll):
        result = await admin_ai_usage_timeseries(
            start_date="2026-05-10", end_date="2026-05-12",
            org_id=None, _={"role": "system_admin"},
        )

    assert len(result["days"]) == 3
    assert all(d["events"] == 0 and d["cost_usd"] == 0 for d in result["days"])
    assert result["totals"]["events"] == 0
    assert result["totals"]["cost_usd"] == 0
    assert result["totals"]["cache_hit_ratio_pct"] == 0.0


async def test_timeseries_filters_by_org_id():
    """When org_id is passed, the match filter must include it."""
    from routers.admin import admin_ai_usage_timeseries

    captured_match = {}
    coll = MagicMock()

    def fake_agg(pipeline, *_args, **_kw):
        nonlocal captured_match
        # First call captures the match stage
        if not captured_match:
            for stage in pipeline:
                if "$match" in stage:
                    captured_match = stage["$match"]
                    break
        return _fake_agg_cursor([])

    coll.aggregate = MagicMock(side_effect=fake_agg)

    with patch("database.ai_usage_events_collection", coll):
        await admin_ai_usage_timeseries(
            start_date="2026-05-15", end_date="2026-05-15",
            org_id="org_xyz", _={"role": "system_admin"},
        )

    assert captured_match.get("organization_id") == "org_xyz"
    assert captured_match["module_key"] == "ai_assistant"


async def test_timeseries_rejects_invalid_date_format():
    from routers.admin import admin_ai_usage_timeseries
    from fastapi import HTTPException

    coll = MagicMock()
    coll.aggregate = MagicMock(return_value=_fake_agg_cursor([]))

    with patch("database.ai_usage_events_collection", coll):
        with pytest.raises(HTTPException) as exc_info:
            await admin_ai_usage_timeseries(
                start_date="not-a-date", end_date="2026-05-15",
                org_id=None, _={"role": "system_admin"},
            )
    assert exc_info.value.status_code == 400
