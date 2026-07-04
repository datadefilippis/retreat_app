"""Wave 7A.3 — focused sub-tools extracted from query_product_recommendations.

These tests pin the contract of the 4 new product_catalog tools:
  - query_low_stock_products
  - query_underperforming_events
  - query_idle_rentals
  - query_high_cancellation_products

The omnibus query_product_recommendations is unchanged and not retested here.

We mock product_metrics_collection so the tests don't need MongoDB.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


def _fake_cursor(docs: list[dict]):
    """Build a fake Motor cursor whose .find(...).sort(...).to_list() returns docs."""
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.to_list = AsyncMock(return_value=docs)
    return cursor


def _patch_collection(docs: list[dict]):
    """Patch product_metrics_collection.find to return our fake cursor."""
    coll = MagicMock()
    coll.find.return_value = _fake_cursor(docs)
    return patch(
        "modules.product_catalog.ai_tools.product_metrics_collection",
        coll,
    )


# ── query_low_stock_products ─────────────────────────────────────────────────

async def test_low_stock_tool_definition_registered():
    from modules.product_catalog.ai_tools import TOOL_DEFINITIONS
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert {
        "query_low_stock_products",
        "query_underperforming_events",
        "query_idle_rentals",
        "query_high_cancellation_products",
    }.issubset(names)


async def test_low_stock_returns_products_with_action():
    from modules.product_catalog.ai_tools import execute_tool

    docs = [
        {"product_name": "Vino Chianti", "sku": "VIN-001", "category": "Vini",
         "stock_quantity": 1, "total_revenue": 1500.0, "total_units_sold": 30},
        {"product_name": "Olio EVO", "sku": "OIL-002", "category": "Condimenti",
         "stock_quantity": 3, "total_revenue": 800.0, "total_units_sold": 20},
    ]

    with _patch_collection(docs):
        result = await execute_tool("org_x", "query_low_stock_products", {})

    assert result["data"]["has_data"] is True
    assert result["data"]["count"] == 2
    assert result["data"]["threshold_used"] == 3
    products = result["data"]["products"]
    # Stock=1 → urgenza
    assert "urgenza" in products[0]["action"].lower()
    # Stock=3 → pianificare
    assert "pianificare" in products[1]["action"].lower()
    assert result["epistemic_class"] == "factual"


async def test_low_stock_respects_custom_threshold():
    from modules.product_catalog.ai_tools import execute_tool

    with _patch_collection([]):
        result = await execute_tool(
            "org_x", "query_low_stock_products",
            {"threshold": 10, "limit": 5},
        )

    assert result["data"]["threshold_used"] == 10
    assert result["data"]["has_data"] is False


async def test_low_stock_clamps_limit_to_50():
    """User-supplied huge limits must be capped at 50."""
    from modules.product_catalog.ai_tools import execute_tool

    coll = MagicMock()
    coll.find.return_value = _fake_cursor([])
    with patch(
        "modules.product_catalog.ai_tools.product_metrics_collection", coll,
    ):
        await execute_tool(
            "org_x", "query_low_stock_products",
            {"limit": 9999},
        )

    # Inspect the cursor.to_list call
    cursor = coll.find.return_value
    cursor.to_list.assert_awaited_once_with(length=50)


# ── query_underperforming_events ─────────────────────────────────────────────

async def test_underperforming_events_returns_event_payload():
    from modules.product_catalog.ai_tools import execute_tool

    docs = [
        {"product_name": "Concerto Live", "sku": "EVT-001",
         "item_type": "event_ticket", "event_fill_rate_pct": 15.0,
         "event_total_capacity": 200, "event_tickets_sold": 30,
         "total_revenue": 600.0},
    ]

    with _patch_collection(docs):
        result = await execute_tool(
            "org_x", "query_underperforming_events", {"max_fill_rate_pct": 30},
        )

    assert result["data"]["has_data"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["threshold_used_pct"] == 30.0
    event = result["data"]["events"][0]
    assert event["fill_rate_pct"] == 15.0
    assert event["total_capacity"] == 200
    assert "promozione" in event["action"].lower()


async def test_underperforming_events_default_threshold():
    from modules.product_catalog.ai_tools import execute_tool

    with _patch_collection([]):
        result = await execute_tool(
            "org_x", "query_underperforming_events", {},
        )

    assert result["data"]["threshold_used_pct"] == 30.0


# ── query_idle_rentals ───────────────────────────────────────────────────────

async def test_idle_rentals_returns_rental_payload():
    from modules.product_catalog.ai_tools import execute_tool

    docs = [
        {"product_name": "E-bike", "sku": "RNT-001", "item_type": "rental",
         "rental_utilization_pct": 5.0, "total_revenue": 200.0,
         "total_units_sold": 2},
        {"product_name": "Kayak", "sku": "RNT-002", "item_type": "rental",
         "rental_utilization_pct": None, "total_revenue": 0.0,
         "total_units_sold": 0},
    ]

    with _patch_collection(docs):
        result = await execute_tool(
            "org_x", "query_idle_rentals", {"max_utilization_pct": 10},
        )

    assert result["data"]["has_data"] is True
    assert result["data"]["count"] == 2
    # None utilization should be normalized to 0
    rentals = {r["name"]: r for r in result["data"]["rentals"]}
    assert rentals["Kayak"]["utilization_pct"] == 0
    assert rentals["E-bike"]["utilization_pct"] == 5.0


# ── query_high_cancellation_products ─────────────────────────────────────────

async def test_high_cancellation_returns_product_payload():
    from modules.product_catalog.ai_tools import execute_tool

    docs = [
        {"product_name": "Spa Pacchetto", "sku": "SPA-001", "item_type": "booking",
         "cancellation_rate_pct": 35.0, "total_revenue": 4500.0,
         "order_revenue": 4500.0},
    ]

    with _patch_collection(docs):
        result = await execute_tool(
            "org_x", "query_high_cancellation_products",
            {"min_cancel_rate_pct": 20},
        )

    assert result["data"]["has_data"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["threshold_used_pct"] == 20.0
    p = result["data"]["products"][0]
    assert p["cancellation_rate_pct"] == 35.0
    assert p["item_type"] == "booking"
    assert "cancellazione" in p["action"].lower()


# ── invalid input robustness ─────────────────────────────────────────────────

async def test_subtools_handle_garbage_thresholds():
    """Non-numeric thresholds must fall back to defaults without crashing."""
    from modules.product_catalog.ai_tools import execute_tool

    with _patch_collection([]):
        r1 = await execute_tool(
            "org_x", "query_low_stock_products",
            {"threshold": "notanumber"},
        )
        r2 = await execute_tool(
            "org_x", "query_underperforming_events",
            {"max_fill_rate_pct": "bad"},
        )
        r3 = await execute_tool(
            "org_x", "query_idle_rentals",
            {"max_utilization_pct": None},
        )
        r4 = await execute_tool(
            "org_x", "query_high_cancellation_products",
            {"min_cancel_rate_pct": []},
        )

    assert r1["data"]["threshold_used"] == 3
    assert r2["data"]["threshold_used_pct"] == 30.0
    assert r3["data"]["threshold_used_pct"] == 10.0
    assert r4["data"]["threshold_used_pct"] == 20.0
