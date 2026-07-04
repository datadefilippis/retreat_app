"""Wave 14.1.A — envelope migration contract tests.

Verifies that the 5 priority chat AI tools (the ones most frequently
called by the model, and the ones most exposed in the 2026-05-16
production incident) now return responses that pass
``validate_envelope`` in lenient mode AND carry the right
``_source.tool`` + ``_temporal_scope`` markers.

The migration strategy preserves legacy field shapes at the top
level (downstream consumers and the AI prompt keep working) and
only ADDS the envelope metadata fields. The contract tests below
pin both surfaces.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from core.tool_envelope import (
    ENVELOPE_VERSION,
    is_envelope,
    validate_envelope,
)


def _assert_envelope_compliant(result: dict, *, tool: str, scope: str):
    """Common contract assertion used by all migration tests."""
    assert isinstance(result, dict), (
        f"{tool}: result must be a dict (got {type(result).__name__})"
    )
    # Required envelope fields
    assert "has_data" in result, f"{tool}: missing has_data"
    assert isinstance(result["has_data"], bool), (
        f"{tool}: has_data must be bool (Wave 14 envelope contract)"
    )
    assert "_temporal_scope" in result, f"{tool}: missing _temporal_scope"
    assert result["_temporal_scope"] == scope, (
        f"{tool}: _temporal_scope should be {scope!r}, got "
        f"{result['_temporal_scope']!r}"
    )
    assert "_data_integrity" in result, f"{tool}: missing _data_integrity"
    di = result["_data_integrity"]
    assert isinstance(di, dict)
    assert di["status"] in ("ok", "warning", "error")
    assert "_source" in result, f"{tool}: missing _source"
    src = result["_source"]
    assert src["tool"] == tool
    assert src["envelope_version"] == ENVELOPE_VERSION

    # Full validator pass (lenient mode)
    result_obj = validate_envelope(result)
    assert result_obj.ok, (
        f"{tool}: validate_envelope failed: {result_obj.errors}"
    )
    # And is_envelope() probe identifies it
    assert is_envelope(result), f"{tool}: is_envelope() returned False"


# ── query_revenue ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestQueryRevenueEnvelope:
    async def test_revenue_has_envelope_metadata(self):
        from modules.cashflow_monitor import ai_tools

        with patch(
            "repositories.analytics_repository.aggregate_sales_by_date",
            new=AsyncMock(return_value={"2026-05-01": 1000.0, "2026-05-02": 1500.0}),
        ), \
             patch(
                "repositories.analytics_repository.aggregate_sales_by_category",
                new=AsyncMock(return_value=[
                    {"_id": "Cat A", "total": 2500.0, "count": 2},
                ]),
             ), \
             patch(
                "repositories.organization_repository.find_by_id",
                new=AsyncMock(return_value={"currency": "EUR"}),
             ):
            result = await ai_tools.execute_tool(
                org_id="org_1",
                tool_name="query_revenue",
                tool_input={
                    "start_date": "2026-05-01",
                    "end_date":   "2026-05-31",
                    "locale": "it",
                },
            )

        _assert_envelope_compliant(
            result, tool="query_revenue", scope="period_filtered",
        )
        # Legacy fields still present at top level (no consumer breakage)
        assert result["total"] == 2500.0
        assert result["currency"] == "EUR"
        assert result["period"]["start_date"] == "2026-05-01"
        assert "by_date" in result
        assert "by_category" in result

    async def test_revenue_no_data_envelope_compliant(self):
        from modules.cashflow_monitor import ai_tools

        with patch(
            "repositories.analytics_repository.aggregate_sales_by_date",
            new=AsyncMock(return_value={}),
        ), \
             patch(
                "repositories.analytics_repository.aggregate_sales_by_category",
                new=AsyncMock(return_value=[]),
             ), \
             patch(
                "repositories.organization_repository.find_by_id",
                new=AsyncMock(return_value={"currency": "EUR"}),
             ):
            result = await ai_tools.execute_tool(
                org_id="org_1",
                tool_name="query_revenue",
                tool_input={
                    "start_date": "2026-05-01",
                    "end_date":   "2026-05-31",
                    "locale": "it",
                },
            )

        # has_data=False + non-null caveat — envelope contract satisfied
        assert result["has_data"] is False
        assert result["_caveat"] is not None
        _assert_envelope_compliant(
            result, tool="query_revenue", scope="period_filtered",
        )


# ── query_cashflow_summary ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestQueryCashflowSummaryEnvelope:
    async def test_cashflow_summary_has_envelope_metadata(self):
        from modules.cashflow_monitor import ai_tools

        fake_summary = {
            "has_data": True,
            "currency": "EUR",
            "period": {"label": "30d", "start_date": "2026-04-17",
                        "end_date": "2026-05-16", "days": 30},
            "pnl": {"total_sales": 50000, "net_after_fixed": 5000},
            "status": {"level": "ok"},
            "health_score": {"score": 85, "label": "Buono"},
        }
        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(return_value=fake_summary),
        ), \
             patch(
                "repositories.organization_repository.find_by_id",
                new=AsyncMock(return_value={"currency": "EUR"}),
             ):
            result = await ai_tools.execute_tool(
                org_id="org_1",
                tool_name="query_cashflow_summary",
                tool_input={"period": "30d", "locale": "it"},
            )

        _assert_envelope_compliant(
            result, tool="query_cashflow_summary", scope="period_filtered",
        )
        # Legacy business fields preserved at top level
        assert result["pnl"]["total_sales"] == 50000
        assert result["health_score"]["score"] == 85


# ── query_business_summary ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestQueryBusinessSummaryEnvelope:
    async def test_business_summary_has_envelope_metadata(self):
        from modules.cashflow_monitor import ai_tools

        fake_unified = {
            "has_data": True,
            "currency": "EUR",
            "period": {"label": "ytd", "start_date": "2026-01-01",
                        "end_date": "2026-05-16", "days": 136},
            "cashflow": {"pnl": {"total_sales": 209954}},
            "customers": {"top": []},
            "commerce_operations": {},
            "reasoning_contract": {"version": "v2"},
        }
        with patch(
            "services.business_summary.build_unified_summary",
            new=AsyncMock(return_value=fake_unified),
        ), \
             patch(
                "repositories.organization_repository.find_by_id",
                new=AsyncMock(return_value={"currency": "EUR"}),
             ):
            result = await ai_tools.execute_tool(
                org_id="org_1",
                tool_name="query_business_summary",
                tool_input={
                    "start_date": "2026-01-01",
                    "end_date":   "2026-05-16",
                    "locale": "it",
                },
            )

        _assert_envelope_compliant(
            result, tool="query_business_summary", scope="period_filtered",
        )
        # Cross-module business fields preserved
        assert result["cashflow"]["pnl"]["total_sales"] == 209954
        assert "reasoning_contract" in result


# ── query_smart_brief — including the failure path ────────────────────────


@pytest.mark.asyncio
class TestQuerySmartBriefEnvelope:
    """The tool that crashed on 2026-05-16 in prod. Wave 14.HOTFIX #1
    fixed the underlying ``risk_focus`` shape mismatch; the envelope
    migration now ensures even a failed branch produces a valid
    envelope so the chat AI ALWAYS gets the right metadata to follow
    Rule 20 (HARD STOP ON TOOL ERROR)."""

    async def test_smart_brief_normal_path_envelope_compliant(self):
        from modules.cashflow_monitor import ai_tools

        with patch(
            "services.module_access.get_module_entitlements",
            new=AsyncMock(return_value={"enabled": True}),
        ), \
             patch(
                "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
                new=AsyncMock(return_value={
                    "has_data": True,
                    "pnl": {"net_after_fixed": 90900, "operating_margin_pct": 30},
                    "status": {"level": "ok"},
                    "health_score": {"score": 96},
                    "risk_focus": [],
                    "action_focus": [],
                    "period_comparison": {"direction": "stable"},
                }),
             ), \
             patch(
                "repositories.alert_repository.find_by_org",
                new=AsyncMock(return_value=[]),
             ), \
             patch(
                "repositories.organization_repository.find_by_id",
                new=AsyncMock(return_value="EUR"),
             ), \
             patch(
                "database.customer_metrics_collection",
                MagicMock(
                    count_documents=AsyncMock(return_value=0),
                    find_one=AsyncMock(return_value=None),
                    find=MagicMock(return_value=MagicMock(
                        sort=MagicMock(return_value=MagicMock(
                            limit=MagicMock(return_value=MagicMock(
                                to_list=AsyncMock(return_value=[]),
                            )),
                        )),
                    )),
                ),
             ), \
             patch(
                "database.product_metrics_collection",
                MagicMock(
                    count_documents=AsyncMock(return_value=0),
                    find_one=AsyncMock(return_value=None),
                ),
             ), \
             patch(
                "database.orders_collection",
                MagicMock(
                    count_documents=AsyncMock(return_value=0),
                    aggregate=MagicMock(return_value=MagicMock(
                        to_list=AsyncMock(return_value=[]),
                    )),
                ),
             ), \
             patch(
                "repositories.analytics_repository.count_sales_with_customer_id",
                new=AsyncMock(return_value={"total": 0, "with_customer_id": 0}),
             ):
            result = await ai_tools.execute_tool(
                org_id="org_1",
                tool_name="query_smart_brief",
                tool_input={
                    "start_date": "2026-01-01",
                    "end_date":   "2026-05-16",
                    "locale": "it",
                },
            )

        _assert_envelope_compliant(
            result, tool="query_smart_brief", scope="period_filtered",
        )
        # Integrity is OK when cashflow section succeeded
        assert result["_data_integrity"]["status"] == "ok"
        # period_used field still surfaces the user's window
        assert "period_used" in result


# ── query_top_customers — all_time scope ──────────────────────────────────


@pytest.mark.asyncio
class TestQueryTopCustomersEnvelope:
    async def test_top_customers_has_all_time_scope(self):
        from modules.customer_insights import ai_tools

        with patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new=AsyncMock(return_value=[
                {
                    "customer_name": "ACME",
                    "total_revenue": 50000,
                    "transaction_count": 10,
                    "last_purchase_date": "2026-04-01",
                    "segment": "top",
                    "revenue_share_pct": 25.0,
                },
            ]),
        ):
            result = await ai_tools.execute_tool(
                org_id="org_1",
                tool_name="query_top_customers",
                tool_input={"limit": 5},
            )

        _assert_envelope_compliant(
            result, tool="query_top_customers", scope="all_time",
        )
        # Legacy fields preserved
        assert result["total_customers"] == 1
        assert result["top_customers"][0]["name"] == "ACME"

    async def test_top_customers_empty_envelope_compliant(self):
        from modules.customer_insights import ai_tools

        with patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new=AsyncMock(return_value=[]),
        ):
            result = await ai_tools.execute_tool(
                org_id="org_1",
                tool_name="query_top_customers",
                tool_input={},
            )

        # has_data=False + non-null caveat
        assert result["has_data"] is False
        assert result.get("_caveat")
        _assert_envelope_compliant(
            result, tool="query_top_customers", scope="all_time",
        )
