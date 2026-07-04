"""Wave 7B.2 — analytics tools added to modules.commerce.

Tests pin the contract of 4 new commerce tools that answer high-leverage
merchant questions:
  - query_orders_dashboard          ("how's the month going?")
  - query_aov_trend                 ("are customers spending more?")
  - query_cancellations_breakdown   ("how much revenue do I lose?")
  - query_dormant_products          ("what's not selling?")

We mock orders_collection and product_metrics_collection so tests don't
need MongoDB. The aggregate pipelines are exercised end-to-end with
controlled inputs; the assertions focus on response shape and the
business logic (AOV computation, rate calculations, sorting).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fake_agg_cursor(docs: list[dict]):
    """Build a fake Motor aggregate cursor that yields the given docs."""
    async def _aiter():
        for d in docs:
            yield d
    cursor = MagicMock()
    cursor.__aiter__ = lambda self: _aiter()
    return cursor


def _patch_orders(side_effect_pipelines: list[list[dict]]):
    """Patch orders_collection.aggregate to return one cursor per call,
    in the order of side_effect_pipelines."""
    coll = MagicMock()
    cursors = [_fake_agg_cursor(p) for p in side_effect_pipelines]
    coll.aggregate = MagicMock(side_effect=cursors)
    return patch("database.orders_collection", coll), coll


def _patch_product_metrics(docs: list[dict]):
    """Patch product_metrics_collection.find to return docs via cursor."""
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.to_list = AsyncMock(return_value=docs)
    coll = MagicMock()
    coll.find.return_value = cursor
    return patch("database.product_metrics_collection", coll), coll


def _patch_currency():
    """Stub _get_org_currency to avoid hitting the DB."""
    return patch(
        "modules.commerce.ai_tools._get_org_currency",
        new=AsyncMock(return_value="EUR"),
    )


# ── query_orders_dashboard ───────────────────────────────────────────────────

async def test_orders_dashboard_returns_expected_shape():
    """Status×source aggregation + daily top-5: response shape + AOV math."""
    from modules.commerce.ai_tools import execute_tool

    # Pipeline 1: status×source group
    status_source_docs = [
        {"_id": {"status": "completed", "source": "storefront"}, "count": 8, "amount": 1600.0},
        {"_id": {"status": "completed", "source": "manual"}, "count": 2, "amount": 400.0},
        {"_id": {"status": "cancelled", "source": "storefront"}, "count": 1, "amount": 100.0},
    ]
    # Pipeline 2: daily top-5
    daily_docs = [
        {"_id": "2026-05-10", "count": 5, "revenue": 1000.0},
        {"_id": "2026-05-12", "count": 3, "revenue": 700.0},
    ]

    ctx, _ = _patch_orders([status_source_docs, daily_docs])
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_orders_dashboard",
            {"start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

    assert result["has_data"] is True
    assert result["total_orders"] == 11
    assert result["total_revenue"] == 2100.0
    # AOV = total_revenue / active_orders (excl. cancelled) = 2000/10 = 200
    assert result["aov"] == 200.0
    assert result["currency"] == "EUR"
    assert result["by_status"] == {"completed": 10, "cancelled": 1}
    assert result["by_source"]["storefront"]["count"] == 9
    assert result["by_source"]["manual"]["count"] == 2
    # cancellation_rate = 1/11 ≈ 9.1%
    assert result["analysis"]["cancellation_rate_pct"] == 9.1
    assert len(result["top_days_by_volume"]) == 2
    assert result["top_days_by_volume"][0]["date"] == "2026-05-10"
    assert result["epistemic"]["epistemic_class"] == "factual"


async def test_orders_dashboard_no_data():
    from modules.commerce.ai_tools import execute_tool

    ctx, _ = _patch_orders([[], []])
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_orders_dashboard",
            {"start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

    assert result["has_data"] is False
    assert result["total_orders"] == 0
    assert result["aov"] == 0
    assert result["_caveat"] is not None


# ── query_aov_trend ──────────────────────────────────────────────────────────

async def test_aov_trend_computes_delta_correctly():
    """Current AOV 250, previous 200 → +25% growing."""
    from modules.commerce.ai_tools import execute_tool

    # 4 aggregations happen: current period, then previous period.
    # Each returns a single group doc with {count, revenue}.
    cur_period = [{"_id": None, "count": 20, "revenue": 5000.0}]   # AOV = 250
    prev_period = [{"_id": None, "count": 25, "revenue": 5000.0}]  # AOV = 200

    ctx, _ = _patch_orders([cur_period, prev_period])
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_aov_trend",
            {"period": "30d"},
        )

    assert result["current_period"]["aov"] == 250.0
    assert result["previous_period"]["aov"] == 200.0
    assert result["delta"]["aov_delta_pct"] == 25.0
    assert result["delta"]["direction"] == "growing"
    assert result["period_days"] == 30
    # 20 + 25 >= 10 per period → high reliability
    assert result["epistemic"]["reliability"] == "high"


async def test_aov_trend_low_volume_qualifies_caveat():
    from modules.commerce.ai_tools import execute_tool

    cur = [{"_id": None, "count": 3, "revenue": 600.0}]
    prev = [{"_id": None, "count": 2, "revenue": 300.0}]

    ctx, _ = _patch_orders([cur, prev])
    with ctx, _patch_currency():
        result = await execute_tool("org_x", "query_aov_trend", {"period": "30d"})

    assert result["epistemic"]["reliability"] == "medium"
    assert result["epistemic"]["caveat"] is not None
    assert "statisticamente" in result["epistemic"]["caveat"].lower()


async def test_aov_trend_period_parsing_garbage_falls_back():
    from modules.commerce.ai_tools import execute_tool

    ctx, _ = _patch_orders([[], []])
    with ctx, _patch_currency():
        r = await execute_tool("org_x", "query_aov_trend", {"period": "notanumber"})
    assert r["period_days"] == 30


# ── query_cancellations_breakdown ────────────────────────────────────────────

async def test_cancellations_breakdown_returns_full_report():
    from modules.commerce.ai_tools import execute_tool

    total_count = [{"n": 50}]
    cancel_agg = [{"_id": None, "count": 6, "lost_revenue": 1200.0}]
    top_products = [
        {"_id": {"product_id": "p1", "name": "Vino A"},
         "cancel_count": 3, "lost_amount": 600.0},
        {"_id": {"product_id": "p2", "name": "Vino B"},
         "cancel_count": 2, "lost_amount": 400.0},
    ]

    ctx, _ = _patch_orders([total_count, cancel_agg, top_products])
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_cancellations_breakdown",
            {"start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

    assert result["has_data"] is True
    assert result["total_orders_in_period"] == 50
    assert result["cancelled_count"] == 6
    assert result["lost_revenue"] == 1200.0
    # 6/50 = 12%
    assert result["cancellation_rate_pct"] == 12.0
    assert result["analysis"]["severity"] == "alta"  # 8 < 12 < 15
    assert result["analysis"]["avg_lost_per_cancelled"] == 200.0
    assert len(result["top_cancelled_products"]) == 2
    assert result["top_cancelled_products"][0]["product_name"] == "Vino A"


async def test_cancellations_severity_thresholds():
    """Severity buckets: critica >15, alta 8-15, fisiologica <8."""
    from modules.commerce.ai_tools import execute_tool

    cases = [
        # (total, cancelled, expected_severity)
        (100, 20, "critica"),   # 20%
        (100, 10, "alta"),      # 10%
        (100, 3, "fisiologica"),  # 3%
    ]
    for total, cancelled, expected in cases:
        total_count = [{"n": total}]
        cancel_agg = [{"_id": None, "count": cancelled, "lost_revenue": cancelled * 100.0}]
        ctx, _ = _patch_orders([total_count, cancel_agg, []])
        with ctx, _patch_currency():
            r = await execute_tool(
                "org_x", "query_cancellations_breakdown",
                {"start_date": "2026-05-01", "end_date": "2026-05-31"},
            )
        assert r["analysis"]["severity"] == expected, (
            f"Expected {expected} for {cancelled}/{total}, got {r['analysis']['severity']}"
        )


# ── query_dormant_products ───────────────────────────────────────────────────

async def test_dormant_products_classifies_buckets():
    from modules.commerce.ai_tools import execute_tool

    docs = [
        {"product_name": "Vino Vecchio", "sku": "WIN-001", "category": "Vini",
         "last_sale_date": "2025-01-15T10:00:00", "total_revenue": 500.0,
         "total_units_sold": 30},
        {"product_name": "Mai Venduto", "sku": "NEW-001", "category": "Snack",
         "last_sale_date": None, "total_revenue": 0, "total_units_sold": 0},
    ]
    ctx, _ = _patch_product_metrics(docs)
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_dormant_products",
            {"days_threshold": 30, "limit": 5},
        )

    assert result["data"]["has_data"] is True
    assert result["data"]["count"] == 2
    assert result["data"]["threshold_days_used"] == 30
    assert result["data"]["dormant_count"] == 1
    assert result["data"]["never_sold_count"] == 1

    by_name = {p["name"]: p for p in result["data"]["products"]}
    assert by_name["Vino Vecchio"]["bucket"] == "dormant"
    assert by_name["Vino Vecchio"]["days_since_last_sale"] is not None
    assert by_name["Vino Vecchio"]["days_since_last_sale"] > 30
    assert by_name["Mai Venduto"]["bucket"] == "never_sold"
    assert by_name["Mai Venduto"]["last_sale_date"] is None


async def test_dormant_products_clamps_threshold():
    """days_threshold must be clamped to [1, 365] and limit to [1, 50]."""
    from modules.commerce.ai_tools import execute_tool

    ctx, _ = _patch_product_metrics([])
    with ctx, _patch_currency():
        r = await execute_tool(
            "org_x", "query_dormant_products",
            {"days_threshold": 9999, "limit": 9999},
        )
    assert r["data"]["threshold_days_used"] == 365


async def test_dormant_products_handles_garbage_threshold():
    from modules.commerce.ai_tools import execute_tool

    ctx, _ = _patch_product_metrics([])
    with ctx, _patch_currency():
        r = await execute_tool(
            "org_x", "query_dormant_products",
            {"days_threshold": "notanumber"},
        )
    assert r["data"]["threshold_days_used"] == 30


# ── Registration check ──────────────────────────────────────────────────────

async def test_all_4_new_tools_registered():
    from modules.commerce.ai_tools import TOOL_DEFINITIONS
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert {
        "query_orders_dashboard",
        "query_aov_trend",
        "query_cancellations_breakdown",
        "query_dormant_products",
    }.issubset(names), f"Missing tools: {names}"


# ════════════════════════════════════════════════════════════════════════════
# Wave 7B.3 — channels, stores, catalog health, customer mix, basket
# ════════════════════════════════════════════════════════════════════════════


def _patch_stores(stores_docs: list[dict]):
    """Patch stores_collection.find to return docs via a cursor with .to_list."""
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=stores_docs)
    coll = MagicMock()
    coll.find.return_value = cursor
    coll.find_one = AsyncMock(return_value=stores_docs[0] if stores_docs else None)
    return patch("database.stores_collection", coll), coll


def _patch_products_count(counts_by_query: dict, examples_by_query: dict):
    """Patch products_collection.count_documents + .find for catalog_health.

    counts_by_query: {"_call_order": [int]} — counts returned per call in order.
    examples_by_query: similar for find().limit().__aiter__.
    """
    coll = MagicMock()
    # count_documents called 5 times: total, missing_price, missing_cost, missing_desc, inactive
    coll.count_documents = AsyncMock(side_effect=counts_by_query["calls"])

    # find().limit() — return async iter per call
    async def _aiter_for(docs):
        for d in docs:
            yield d

    find_cursors = []
    for docs in examples_by_query["calls"]:
        cur = MagicMock()
        cur.limit.return_value = cur
        cur.__aiter__ = lambda self, docs=docs: _aiter_for(docs)
        find_cursors.append(cur)
    coll.find = MagicMock(side_effect=find_cursors)

    return patch("database.products_collection", coll), coll


# ── query_channels_performance ───────────────────────────────────────────────

async def test_channels_performance_groups_by_source():
    from modules.commerce.ai_tools import execute_tool

    # 2 sources: storefront (completed + cancelled), manual (completed)
    docs = [
        {"_id": {"source": "storefront", "status": "completed"}, "count": 8, "amount": 1600.0},
        {"_id": {"source": "storefront", "status": "cancelled"}, "count": 2, "amount": 200.0},
        {"_id": {"source": "manual", "status": "completed"}, "count": 5, "amount": 750.0},
    ]
    ctx, _ = _patch_orders([docs])
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_channels_performance",
            {"start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

    assert result["has_data"] is True
    # Sorted by total_revenue desc → storefront (1800) before manual (750)
    assert result["channels"][0]["source"] == "storefront"
    assert result["channels"][0]["total_revenue"] == 1800.0
    # AOV computed from active revenue only: 1600 / 8 = 200
    assert result["channels"][0]["aov"] == 200.0
    # Cancellation rate storefront: 2/10 = 20%
    assert result["channels"][0]["cancellation_rate_pct"] == 20.0
    # Revenue share: storefront 1800/2550 ≈ 70.6%
    assert abs(result["channels"][0]["revenue_share_pct"] - 70.6) < 0.5
    assert result["top_channel"] == "storefront"


# ── query_stores_overview ────────────────────────────────────────────────────

async def test_stores_overview_combines_lifetime_and_30d():
    from modules.commerce.ai_tools import execute_tool

    stores = [
        {"id": "store1", "name": "Store Roma", "is_active": True, "is_published": True,
         "slug": "roma", "visibility": "public"},
        {"id": "store2", "name": "Store Milano", "is_active": True, "is_published": False,
         "slug": "milano", "visibility": "private"},
    ]
    lifetime_docs = [
        {"_id": "store1", "count": 100, "revenue": 25000.0},
        {"_id": "store2", "count": 20, "revenue": 4000.0},
    ]
    last30d_docs = [
        {"_id": "store1", "count": 10, "revenue": 2500.0},
    ]

    stores_ctx, _ = _patch_stores(stores)
    orders_ctx, _ = _patch_orders([lifetime_docs, last30d_docs])
    with stores_ctx, orders_ctx, _patch_currency():
        result = await execute_tool("org_x", "query_stores_overview", {})

    assert result["has_data"] is True
    assert result["total_stores"] == 2
    assert result["active_stores"] == 2
    assert result["published_stores"] == 1
    # Sorted by lifetime_revenue desc
    assert result["stores"][0]["name"] == "Store Roma"
    assert result["stores"][0]["lifetime_revenue"] == 25000.0
    assert result["stores"][0]["last_30d_revenue"] == 2500.0
    assert result["stores"][1]["last_30d_revenue"] == 0  # no orders in 30d


# ── query_store_performance ──────────────────────────────────────────────────

async def test_store_performance_returns_top_products_for_store():
    from modules.commerce.ai_tools import execute_tool

    store_doc = {"id": "store1", "name": "Store Roma",
                 "is_active": True, "is_published": True}
    by_status = [
        {"_id": "completed", "count": 10, "amount": 2000.0},
        {"_id": "cancelled", "count": 1, "amount": 200.0},
    ]
    top_products = [
        {"_id": {"product_id": "p1", "name": "Vino A"},
         "units": 20, "revenue": 1000.0},
        {"_id": {"product_id": "p2", "name": "Vino B"},
         "units": 15, "revenue": 750.0},
    ]

    # stores_collection.find_one returns the store doc
    coll = MagicMock()
    coll.find_one = AsyncMock(return_value=store_doc)
    stores_ctx = patch("database.stores_collection", coll)
    orders_ctx, _ = _patch_orders([by_status, top_products])

    with stores_ctx, orders_ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_store_performance",
            {"store_id": "store1", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

    assert result["has_data"] is True
    assert result["store"]["name"] == "Store Roma"
    assert result["total_orders"] == 11
    assert result["active_orders"] == 10
    # AOV = active_revenue / active_count = 2000 / 10
    assert result["aov"] == 200.0
    assert len(result["top_products"]) == 2
    assert result["top_products"][0]["product_name"] == "Vino A"


async def test_store_performance_missing_store_returns_error():
    from modules.commerce.ai_tools import execute_tool

    coll = MagicMock()
    coll.find_one = AsyncMock(return_value=None)
    stores_ctx = patch("database.stores_collection", coll)

    with stores_ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_store_performance",
            {"store_id": "nonexistent"},
        )

    assert result["has_data"] is False
    assert "non trovato" in result["error"]


# ── query_catalog_health ─────────────────────────────────────────────────────

async def test_catalog_health_reports_per_class():
    from modules.commerce.ai_tools import execute_tool

    # 5 count_documents calls (total, price, cost, desc, inactive)
    counts = [100, 5, 12, 8, 3]
    # 4 find() calls returning examples
    examples = [
        [{"name": "P-noprice-1", "sku": "X1", "id": "id1"}],
        [{"name": "P-nocost-1", "sku": "X2", "id": "id2"}],
        [{"name": "P-nodesc-1", "sku": "X3", "id": "id3"}],
        [{"name": "P-inactive-1", "sku": "X4", "id": "id4"}],
    ]
    ctx, _ = _patch_products_count(
        {"calls": counts},
        {"calls": examples},
    )
    with ctx, _patch_currency():
        result = await execute_tool("org_x", "query_catalog_health", {})

    assert result["has_data"] is True
    assert result["total_products"] == 100
    assert result["issues"]["missing_unit_price"]["count"] == 5
    assert result["issues"]["missing_cost_price"]["count"] == 12
    assert result["issues"]["missing_description"]["count"] == 8
    assert result["issues"]["inactive_products"]["count"] == 3
    # health_pct = max(0, 100 - (5+12+8+3)/100*25) = 100 - 7 = 93
    assert result["health_score_pct"] == 93.0
    assert len(result["issues"]["missing_unit_price"]["examples"]) == 1


# ── query_new_vs_returning_split ─────────────────────────────────────────────

async def test_new_vs_returning_split_classifies_correctly():
    from modules.commerce.ai_tools import execute_tool

    # Step 1: customers who ordered in period
    period_customers = [{"_id": "cust_a"}, {"_id": "cust_b"}]
    # Step 2: of those, who ordered BEFORE start? Only cust_a.
    returning_lookup = [{"_id": "cust_a"}]
    # Step 3a: aggregate revenue for new ids (cust_b)
    new_stats = [{"_id": None, "count": 3, "revenue": 600.0}]
    # Step 3b: aggregate for returning (cust_a)
    ret_stats = [{"_id": None, "count": 5, "revenue": 1500.0}]
    # Step 3c: guests
    guest_stats = [{"_id": None, "count": 2, "revenue": 300.0}]

    ctx, _ = _patch_orders([
        period_customers, returning_lookup,
        new_stats, ret_stats, guest_stats,
    ])
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_new_vs_returning_split",
            {"start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

    assert result["has_data"] is True
    assert result["buckets"]["new"]["orders"] == 3
    assert result["buckets"]["new"]["revenue"] == 600.0
    assert result["buckets"]["new"]["unique_customers"] == 1
    assert result["buckets"]["returning"]["orders"] == 5
    assert result["buckets"]["returning"]["unique_customers"] == 1
    assert result["buckets"]["guest"]["orders"] == 2
    assert result["buckets"]["guest"]["unique_customers"] is None
    # total revenue 600 + 1500 + 300 = 2400, returning share = 1500/2400 = 62.5
    assert result["buckets"]["returning"]["revenue_share_pct"] == 62.5
    assert result["totals"]["orders"] == 10


# ── query_basket_size_distribution ───────────────────────────────────────────

async def test_basket_size_distribution_buckets_correctly():
    from modules.commerce.ai_tools import execute_tool

    docs = [
        {"_id": "1_item", "count": 30, "revenue": 1500.0},
        {"_id": "2-3", "count": 15, "revenue": 1800.0},
        {"_id": "4-5", "count": 4, "revenue": 800.0},
        {"_id": "6+", "count": 1, "revenue": 300.0},
    ]
    ctx, _ = _patch_orders([docs])
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_basket_size_distribution",
            {"start_date": "2026-05-01", "end_date": "2026-05-31"},
        )

    assert result["has_data"] is True
    assert result["totals"]["orders"] == 50
    assert result["totals"]["revenue"] == 4400.0
    # 1_item AOV = 1500/30 = 50, share = 30/50 = 60%
    assert result["buckets"]["1_item"]["aov"] == 50.0
    assert result["buckets"]["1_item"]["order_share_pct"] == 60.0
    # single-item heavy at 60% — falls into "balanced" (30 < 60 <= 70)
    assert result["analysis"]["concentration_note"] == "balanced"


async def test_basket_size_distribution_no_data():
    from modules.commerce.ai_tools import execute_tool

    ctx, _ = _patch_orders([[]])
    with ctx, _patch_currency():
        result = await execute_tool(
            "org_x", "query_basket_size_distribution",
            {"start_date": "2026-05-01", "end_date": "2026-05-31"},
        )
    assert result["has_data"] is False
    assert result["totals"]["orders"] == 0


# ── Registration check (Wave 7B.3) ──────────────────────────────────────────

async def test_all_6_new_b3_tools_registered():
    from modules.commerce.ai_tools import TOOL_DEFINITIONS
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert {
        "query_channels_performance",
        "query_stores_overview",
        "query_store_performance",
        "query_catalog_health",
        "query_new_vs_returning_split",
        "query_basket_size_distribution",
    }.issubset(names), f"Missing Wave 7B.3 tools: {names}"
