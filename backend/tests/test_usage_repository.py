"""Tests for repositories/usage_repository.py — count_usage and record_usage."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from repositories import usage_repository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_aggregate(results):
    """Return a mock cursor whose to_list() returns the given list."""
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=results)
    return cursor


# ---------------------------------------------------------------------------
# count_usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_count_usage_no_events():
    """No matching events → returns 0."""
    with patch.object(
        usage_repository, "ai_usage_events_collection"
    ) as col:
        col.aggregate.return_value = _mock_aggregate([])

        result = await usage_repository.count_usage(
            "org_1", "ai_assistant", "chat", "2026-03-01", "2026-03-31",
        )

    assert result == 0


@pytest.mark.asyncio
async def test_count_usage_sums_quantity():
    """3 events with quantity=1 → total 3."""
    with patch.object(
        usage_repository, "ai_usage_events_collection"
    ) as col:
        col.aggregate.return_value = _mock_aggregate([{"_id": None, "total": 3}])

        result = await usage_repository.count_usage(
            "org_1", "ai_assistant", "chat", "2026-03-01", "2026-03-31",
        )

    assert result == 3


@pytest.mark.asyncio
async def test_count_usage_bulk_quantity():
    """1 event with quantity=50 → total 50."""
    with patch.object(
        usage_repository, "ai_usage_events_collection"
    ) as col:
        col.aggregate.return_value = _mock_aggregate([{"_id": None, "total": 50}])

        result = await usage_repository.count_usage(
            "org_1", "cashflow_monitor", "data_rows", "2026-03-01", "2026-03-31",
        )

    assert result == 50


@pytest.mark.asyncio
async def test_count_usage_match_filter():
    """Verify the aggregation pipeline matches org_id + module_key + feature."""
    with patch.object(
        usage_repository, "ai_usage_events_collection"
    ) as col:
        col.aggregate.return_value = _mock_aggregate([])

        await usage_repository.count_usage(
            "org_42", "cashflow_monitor", "data_rows", "2026-01-01", "2026-01-31",
        )

    # Inspect the pipeline passed to aggregate
    pipeline = col.aggregate.call_args[0][0]
    match_stage = pipeline[0]["$match"]
    assert match_stage["organization_id"] == "org_42"
    assert match_stage["module_key"] == "cashflow_monitor"
    assert match_stage["feature"] == "data_rows"
    assert match_stage["created_at"]["$gte"] == "2026-01-01"
    assert match_stage["created_at"]["$lte"] == "2026-01-31T23:59:59"


# ---------------------------------------------------------------------------
# record_usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_usage_inserts_correct_doc():
    """record_usage inserts a doc with all expected fields."""
    with patch.object(
        usage_repository, "ai_usage_events_collection"
    ) as col:
        col.insert_one = AsyncMock()

        doc = await usage_repository.record_usage(
            "org_1", "cashflow_monitor", "data_rows", quantity=25,
        )

    assert doc["organization_id"] == "org_1"
    assert doc["module_key"] == "cashflow_monitor"
    assert doc["feature"] == "data_rows"
    assert doc["quantity"] == 25
    assert "id" in doc
    assert "created_at" in doc
    col.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_usage_default_quantity():
    """record_usage without quantity → quantity=1."""
    with patch.object(
        usage_repository, "ai_usage_events_collection"
    ) as col:
        col.insert_one = AsyncMock()

        doc = await usage_repository.record_usage(
            "org_1", "ai_assistant", "chat",
        )

    assert doc["quantity"] == 1
