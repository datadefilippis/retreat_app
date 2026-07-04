"""Wave 7D — polish tools across cashflow + commerce + customer_insights.

Tests pin the contract of 4 new tools that close gaps in the chat surface:
  - query_late_payers              (cashflow_monitor)
  - query_coupon_usage             (commerce)
  - query_course_engagement        (commerce)
  - query_customer_acquisition_trend  (customer_insights)
"""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timezone, timedelta

import pytest

pytestmark = pytest.mark.asyncio


def _fake_agg_cursor(docs: list[dict]):
    async def _aiter():
        for d in docs:
            yield d
    cursor = MagicMock()
    cursor.__aiter__ = lambda self: _aiter()
    return cursor


def _fake_find_cursor(docs: list[dict]):
    async def _aiter():
        for d in docs:
            yield d
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=docs)
    cursor.__aiter__ = lambda self: _aiter()
    return cursor


def _patch_collection_aggregate(target: str, side_effect_docs: list[list[dict]]):
    coll = MagicMock()
    coll.aggregate = MagicMock(side_effect=[_fake_agg_cursor(d) for d in side_effect_docs])
    return patch(target, coll), coll


def _patch_currency():
    return patch(
        "modules.commerce.ai_tools._get_org_currency",
        new=AsyncMock(return_value="EUR"),
    )


def _patch_cashflow_currency():
    return patch(
        "modules.cashflow_monitor.ai_tools._get_org_currency",
        new=AsyncMock(return_value="EUR"),
    )


# ── query_late_payers (cashflow) ─────────────────────────────────────────────

async def test_late_payers_groups_by_customer_and_sorts():
    from modules.cashflow_monitor.ai_tools import execute_tool

    today = date.today()
    old_date = (today - timedelta(days=45)).isoformat()
    recent_date = (today - timedelta(days=5)).isoformat()

    agg_docs = [
        {"_id": "c1", "customer_name": "Mario Rossi", "customer_id": "c1",
         "total_overdue": 1500.0, "invoice_count": 3, "oldest_due_date": old_date},
        {"_id": "c2", "customer_name": "Anna Verdi", "customer_id": "c2",
         "total_overdue": 800.0, "invoice_count": 1, "oldest_due_date": recent_date},
    ]

    ctx, _ = _patch_collection_aggregate(
        "database.sales_records_collection",
        [agg_docs],
    )
    with ctx, _patch_cashflow_currency():
        result = await execute_tool("org_x", "query_late_payers", {})

    assert result["has_data"] is True
    assert result["total_late_customers"] == 2
    assert result["customers"][0]["customer_name"] == "Mario Rossi"
    assert result["customers"][0]["total_overdue"] == 1500.0
    assert result["customers"][0]["days_late"] == 45
    assert result["total_overdue_amount"] == 2300.0
    assert result["top_late_payer"]["name"] == "Mario Rossi"


async def test_late_payers_respects_min_overdue_days():
    from modules.cashflow_monitor.ai_tools import execute_tool

    today = date.today()
    agg_docs = [
        {"_id": "c1", "customer_name": "Anna", "customer_id": "c1",
         "total_overdue": 500.0, "invoice_count": 1,
         "oldest_due_date": (today - timedelta(days=10)).isoformat()},
        {"_id": "c2", "customer_name": "Bruno", "customer_id": "c2",
         "total_overdue": 200.0, "invoice_count": 1,
         "oldest_due_date": (today - timedelta(days=40)).isoformat()},
    ]
    ctx, _ = _patch_collection_aggregate(
        "database.sales_records_collection",
        [agg_docs],
    )
    with ctx, _patch_cashflow_currency():
        result = await execute_tool("org_x", "query_late_payers",
                                     {"min_overdue_days": 30})

    # Only Bruno qualifies (40 days late, > 30 threshold)
    assert result["total_late_customers"] == 1
    assert result["customers"][0]["customer_name"] == "Bruno"


async def test_late_payers_empty():
    from modules.cashflow_monitor.ai_tools import execute_tool

    ctx, _ = _patch_collection_aggregate(
        "database.sales_records_collection",
        [[]],
    )
    with ctx, _patch_cashflow_currency():
        result = await execute_tool("org_x", "query_late_payers", {})

    assert result["has_data"] is False
    assert result["total_late_customers"] == 0


# ── query_coupon_usage (commerce) ────────────────────────────────────────────

async def test_coupon_usage_combines_coupons_with_order_discounts():
    from modules.commerce.ai_tools import execute_tool

    coupons = [
        {"id": "cp1", "code": "SUMMER", "discount_pct": 10,
         "current_uses": 8, "max_uses": 20, "is_active": True},
        {"id": "cp2", "code": "WINTER", "discount_amount": 5,
         "current_uses": 2, "max_uses": None, "is_active": True},
    ]
    agg_docs = [
        {"_id": "SUMMER", "discount": 250.0, "uses": 8},
        {"_id": "WINTER", "discount": 30.0, "uses": 2},
    ]

    coll_coupons = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=coupons)
    coll_coupons.find.return_value = cursor
    coll_orders = MagicMock()
    coll_orders.aggregate = MagicMock(return_value=_fake_agg_cursor(agg_docs))

    with patch("database.coupons_collection", coll_coupons), \
         patch("database.orders_collection", coll_orders), \
         _patch_currency():
        result = await execute_tool("org_x", "query_coupon_usage", {})

    assert result["has_data"] is True
    assert result["total_coupons"] == 2
    # Sorted by discount granted desc → SUMMER (250) first
    assert result["coupons"][0]["code"] == "SUMMER"
    assert result["coupons"][0]["discount_granted_in_window"] == 250.0
    # usage_quota_pct = 8/20 = 40
    assert result["coupons"][0]["usage_quota_pct"] == 40.0
    # WINTER has no max_uses → usage_quota_pct = None
    assert result["coupons"][1]["usage_quota_pct"] is None
    assert result["total_discount_granted"] == 280.0
    assert result["top_coupon_by_discount"] == "SUMMER"


async def test_coupon_usage_excludes_inactive_by_default():
    from modules.commerce.ai_tools import execute_tool

    # Two coupons but only one is_active=True; find query must filter
    coll_coupons = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[
        {"id": "cp1", "code": "OK", "current_uses": 0, "is_active": True},
    ])
    coll_coupons.find.return_value = cursor
    coll_orders = MagicMock()
    coll_orders.aggregate = MagicMock(return_value=_fake_agg_cursor([]))

    with patch("database.coupons_collection", coll_coupons), \
         patch("database.orders_collection", coll_orders), \
         _patch_currency():
        result = await execute_tool("org_x", "query_coupon_usage", {})

    # Verify the find query had is_active != false filter
    call_kwargs = coll_coupons.find.call_args[0][0]
    assert call_kwargs["is_active"] == {"$ne": False}
    assert result["total_coupons"] == 1


# ── query_course_engagement (commerce) ───────────────────────────────────────

async def test_course_engagement_sorts_by_enrollments():
    from modules.commerce.ai_tools import execute_tool

    courses = [
        {"id": "c1", "title": "Yoga base", "is_published": True},
        {"id": "c2", "title": "Pilates", "is_published": True},
    ]
    agg_docs = [
        {"_id": "c1", "total_enrolled": 30, "active_enrolled": 25,
         "recent_access_count": 10},
        {"_id": "c2", "total_enrolled": 10, "active_enrolled": 8,
         "recent_access_count": 6},
    ]

    coll_courses = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=courses)
    coll_courses.find.return_value = cursor
    coll_accesses = MagicMock()
    coll_accesses.aggregate = MagicMock(return_value=_fake_agg_cursor(agg_docs))

    with patch("database.courses_collection", coll_courses), \
         patch("database.issued_course_accesses_collection", coll_accesses), \
         _patch_currency():
        result = await execute_tool("org_x", "query_course_engagement", {})

    assert result["has_data"] is True
    assert result["total_courses"] == 2
    # Sorted by total_enrolled desc → Yoga base first
    assert result["courses"][0]["title"] == "Yoga base"
    assert result["courses"][0]["total_enrolled"] == 30
    # engagement_30d_pct = 10/25 = 40%
    assert result["courses"][0]["engagement_30d_pct"] == 40.0
    assert result["total_enrollments"] == 40
    assert result["top_course_by_enrollments"] == "Yoga base"


async def test_course_engagement_no_enrollments_caveat():
    from modules.commerce.ai_tools import execute_tool

    courses = [{"id": "c1", "title": "Test", "is_published": True}]

    coll_courses = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=courses)
    coll_courses.find.return_value = cursor
    coll_accesses = MagicMock()
    coll_accesses.aggregate = MagicMock(return_value=_fake_agg_cursor([]))

    with patch("database.courses_collection", coll_courses), \
         patch("database.issued_course_accesses_collection", coll_accesses), \
         _patch_currency():
        result = await execute_tool("org_x", "query_course_engagement", {})

    assert result["has_data"] is False
    assert "venduti" in result["_caveat"].lower()


# ── query_customer_acquisition_trend (customer_insights) ─────────────────────

async def test_customer_acquisition_trend_returns_dense_months():
    from modules.customer_insights.ai_tools import execute_tool

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cur_year = now.year
    cur_month = now.month
    # Compute previous 2 months
    prev1_m = cur_month - 1 or 12
    prev1_y = cur_year if cur_month > 1 else cur_year - 1
    prev2_m = (prev1_m - 1) or 12
    prev2_y = prev1_y if prev1_m > 1 else prev1_y - 1

    agg_docs = [
        {"_id": {"year": prev2_y, "month": prev2_m}, "count": 5},
        {"_id": {"year": prev1_y, "month": prev1_m}, "count": 8},
        {"_id": {"year": cur_year, "month": cur_month}, "count": 12},
    ]
    coll = MagicMock()
    coll.aggregate = MagicMock(return_value=_fake_agg_cursor(agg_docs))

    with patch("database.customer_accounts_collection", coll):
        result = await execute_tool(
            "org_x", "query_customer_acquisition_trend",
            {"months_back": 3},
        )

    assert result["has_data"] is True
    assert result["months_analyzed"] == 3
    assert len(result["months"]) == 3
    # Last month should be current month with count 12
    assert result["months"][-1]["new_customers"] == 12
    assert result["totals"]["new_customers_in_window"] == 25
    # Direction: first half (5) vs second half (12) → growing
    assert result["trend"]["direction"] == "growing"


async def test_customer_acquisition_trend_clamps_months_back():
    from modules.customer_insights.ai_tools import execute_tool

    coll = MagicMock()
    coll.aggregate = MagicMock(return_value=_fake_agg_cursor([]))

    with patch("database.customer_accounts_collection", coll):
        r = await execute_tool(
            "org_x", "query_customer_acquisition_trend",
            {"months_back": 999},
        )
    assert r["months_analyzed"] == 24


async def test_customer_acquisition_trend_empty_caveat():
    from modules.customer_insights.ai_tools import execute_tool

    coll = MagicMock()
    coll.aggregate = MagicMock(return_value=_fake_agg_cursor([]))

    with patch("database.customer_accounts_collection", coll):
        result = await execute_tool(
            "org_x", "query_customer_acquisition_trend",
            {"months_back": 6},
        )

    assert result["has_data"] is False
    assert result["totals"]["new_customers_in_window"] == 0
    assert "significativo" in (result["epistemic"]["caveat"] or "").lower()


# ── Registration check ──────────────────────────────────────────────────────

async def test_all_4_wave7d_tools_registered():
    from modules.cashflow_monitor.ai_tools import TOOL_DEFINITIONS as CF
    from modules.commerce.ai_tools import TOOL_DEFINITIONS as CM
    from modules.customer_insights.ai_tools import TOOL_DEFINITIONS as CI

    cf_names = {t["name"] for t in CF}
    cm_names = {t["name"] for t in CM}
    ci_names = {t["name"] for t in CI}

    assert "query_late_payers" in cf_names
    assert "query_coupon_usage" in cm_names
    assert "query_course_engagement" in cm_names
    assert "query_customer_acquisition_trend" in ci_names
