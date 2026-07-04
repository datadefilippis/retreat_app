"""Tests for Wave 13.5 — period-aware tools (smart_brief + product_trend).

Two tools were flagged in the Wave 13 audit for hardcoding a 30-day
window even when the user was viewing a different period:

  * ``query_smart_brief`` — pre-fix called
    ``build_ai_summary(period="30d")`` regardless of period_context.
    Now resolves the user's period like every other summary tool.

  * ``query_product_trend`` — relies on a precomputed
    ``trend_30d_pct`` field in product_metrics that can NOT be
    recomputed for arbitrary periods. We keep the snapshot but
    surface ``_temporal_scope`` + a ``_period_caveat`` so the LLM
    never quotes it as a period-filtered answer.

These tests exercise the dispatcher entry points directly, asserting
the new contract without spinning up the full chat loop.
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


# ── Tool registry — schema declares the new params ──────────────────────────


class TestSchemaContract:
    """The model SEES the schema — verify it advertises the new params
    so the dispatcher's period injection actually flows through."""

    def test_smart_brief_schema_has_period_params(self):
        from modules.cashflow_monitor.ai_tools import TOOL_DEFINITIONS
        sb = next(t for t in TOOL_DEFINITIONS if t["name"] == "query_smart_brief")
        params = sb["parameters"]
        assert "period" in params
        assert "start_date" in params
        assert "end_date" in params
        # The description must signal the expanded vocabulary so the
        # model knows YTD/MTD/QTD are accepted (Wave 13.0 vocabulary).
        assert "ytd" in sb["description"].lower()
        assert "mtd" in sb["description"].lower()

    def test_product_trend_schema_has_period_params(self):
        from modules.product_catalog.ai_tools import TOOL_DEFINITIONS
        pt = next(t for t in TOOL_DEFINITIONS
                  if t["name"] == "query_product_trend")
        props = pt["parameters"]["properties"]
        assert "period" in props
        assert "start_date" in props
        assert "end_date" in props
        # Description must clearly state the scope limitation so the
        # model can decide whether to call it.
        assert "30" in pt["description"]
        # An explicit signpost to the alternative tools.
        assert "query_business_summary" in pt["description"]


# ── query_smart_brief — period flows into build_ai_summary ──────────────────


@pytest.mark.asyncio
class TestSmartBriefPeriod:
    """The Wave 13.5 surgical fix: smart_brief uses the requested
    period instead of hardcoding 30d."""

    async def _run(self, tool_input, summary_return):
        """Execute the query_smart_brief branch with all collaborators
        mocked, return the final brief dict + the captured summary call."""
        from modules.cashflow_monitor import ai_tools

        # Patch every awaitable the dispatcher touches.
        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(return_value=summary_return),
        ) as mock_summary, \
             patch(
                "services.module_access.get_module_entitlements",
                new=AsyncMock(return_value={"enabled": False}),
             ), \
             patch(
                "repositories.alert_repository.find_by_org",
                new=AsyncMock(return_value=[]),
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
             ), \
             patch(
                 "modules.cashflow_monitor.ai_tools._get_org_currency",
                 new=AsyncMock(return_value="EUR"),
             ):
            result = await ai_tools.execute_tool(
                org_id="org_1",
                tool_name="query_smart_brief",
                tool_input=tool_input,
            )
        return result, mock_summary

    async def test_period_context_dates_forwarded_to_summary(self):
        """When the dispatcher injects start_date+end_date from
        period_context (e.g. YTD), smart_brief forwards them to
        build_ai_summary AND tags the brief with the period used."""
        fake_summary = {
            "pnl": {"net_after_fixed": 5000, "operating_margin_pct": 12.5},
            "status": {"level": "Buono"},
            "risk_focus": {"primary": {"summary": "Margine in calo"}},
            "action_focus": {},
            "period_comparison": {"direction": "stable"},
            "health_score": {"score": 33},
        }
        tool_input = {
            "period": "ytd",
            "start_date": "2026-01-01",
            "end_date": "2026-05-16",
            "locale": "it",
        }
        result, mock_summary = await self._run(tool_input, fake_summary)

        # The summary builder must have been called with the YTD dates
        _, kwargs = mock_summary.await_args
        assert kwargs["period"] == "ytd"
        assert kwargs["start_date"] == "2026-01-01"
        assert kwargs["end_date"] == "2026-05-16"
        assert kwargs["locale"] == "it"

        # The brief surfaces the period for unambiguous attribution.
        assert result["period_used"] == {
            "label": "ytd",
            "start_date": "2026-01-01",
            "end_date": "2026-05-16",
        }
        # Net result key is now period-agnostic (Wave 13.5 rename)
        assert result["cashflow"]["net_result"] == 5000
        # Old key removed — the audit explicitly called it out as
        # misleading once the tool honoured arbitrary windows.
        assert "net_result_30d" not in result["cashflow"]

    async def test_default_30d_when_no_period_provided(self):
        """When no period_context flows in (e.g. /ai standalone), the
        brief still works — falls back to 30d AND tags the brief
        explicitly so the model knows it's a default snapshot."""
        fake_summary = {
            "pnl": {"net_after_fixed": 1000, "operating_margin_pct": 5},
            "status": {"level": "Attenzione"},
            "risk_focus": {},
            "action_focus": {},
            "period_comparison": {},
            "health_score": {"score": 48},
        }
        result, mock_summary = await self._run(
            tool_input={"locale": "it"},  # no period, no dates
            summary_return=fake_summary,
        )

        _, kwargs = mock_summary.await_args
        assert kwargs["period"] == "30d"
        assert kwargs["start_date"] is None
        assert kwargs["end_date"] is None

        # Brief shows it was a default fallback (no dates, label=30d)
        assert result["period_used"]["label"] == "30d"
        assert result["period_used"]["start_date"] is None

    async def test_token_only_no_dates(self):
        """Some callers send only a token (no dates) — must still flow
        through correctly."""
        fake_summary = {
            "pnl": {"net_after_fixed": 0, "operating_margin_pct": 0},
            "status": {},
            "risk_focus": {},
            "action_focus": {},
            "period_comparison": {},
            "health_score": {},
        }
        result, mock_summary = await self._run(
            tool_input={"period": "90d", "locale": "it"},
            summary_return=fake_summary,
        )

        _, kwargs = mock_summary.await_args
        assert kwargs["period"] == "90d"
        assert result["period_used"]["label"] == "90d"


# ── query_product_trend — scope tagging + caveat ────────────────────────────


@pytest.mark.asyncio
class TestProductTrendScopeMarker:
    """The trend is a materialized 30d snapshot. Wave 13.5 makes that
    HONEST in the response so the model can't misattribute it."""

    async def _run(self, tool_input, metrics_docs):
        from modules.product_catalog import ai_tools

        # Build a stub that mimics motor's cursor chain
        # ``find(...).to_list(length=N)``.
        fake_cursor = MagicMock()
        fake_cursor.to_list = AsyncMock(return_value=metrics_docs)
        fake_collection = MagicMock()
        fake_collection.find = MagicMock(return_value=fake_cursor)

        with patch.object(ai_tools, "product_metrics_collection", fake_collection):
            return await ai_tools.execute_tool(
                org_id="org_1",
                tool_name="query_product_trend",
                tool_input=tool_input,
            )

    async def test_native_30d_no_caveat(self):
        """Compatible request (period='30d' or empty) → clean output."""
        docs = [
            {"product_name": "Prod A", "sku": "A1", "category": "x",
             "total_revenue": 1000, "trend_30d_pct": 15, "abc_class": "A"},
        ]
        result = await self._run({"period": "30d"}, docs)

        assert result["_temporal_scope"] == "materialized_30d_vs_prior_30d"
        # No caveat — request scope matches snapshot scope.
        assert "_period_caveat" not in result

    async def test_empty_period_treated_as_30d(self):
        """No params → still no caveat (defaults to materialised scope)."""
        result = await self._run({}, [])
        assert result["_temporal_scope"] == "materialized_30d_vs_prior_30d"
        assert "_period_caveat" not in result

    async def test_alias_last_30_days_no_caveat(self):
        result = await self._run({"period": "LAST_30_DAYS"}, [])
        assert "_period_caveat" not in result

    async def test_ytd_request_attaches_caveat(self):
        """Incompatible request — caveat tells the model to use a
        different tool for the actual requested window."""
        result = await self._run(
            {"period": "ytd", "start_date": "2026-01-01", "end_date": "2026-05-16"},
            [],
        )
        assert result["_temporal_scope"] == "materialized_30d_vs_prior_30d"
        assert "_period_caveat" in result
        # Caveat must explicitly direct the model to alternative tools.
        assert "query_business_summary" in result["_period_caveat"]
        # And must surface the requested period so log analysis can
        # spot scope-mismatched calls.
        assert "ytd" in result["_period_caveat"]

    async def test_custom_dates_only_attaches_caveat(self):
        result = await self._run(
            {"start_date": "2026-04-01", "end_date": "2026-04-30"},
            [],
        )
        assert "_period_caveat" in result

    async def test_data_shape_preserved(self):
        """The pre-Wave-13.5 data shape under ``data`` is unchanged so
        existing consumers don't break."""
        docs = [
            {"product_name": "Prod A", "sku": "A1", "category": "x",
             "total_revenue": 1000, "trend_30d_pct": 15, "abc_class": "A"},
            {"product_name": "Prod B", "sku": "B1", "category": "y",
             "total_revenue": 500, "trend_30d_pct": -20, "abc_class": "C"},
        ]
        result = await self._run({"direction": "all"}, docs)

        assert result["data"]["has_data"] is True
        assert len(result["data"]["products"]) == 2
        # Sorted by abs(trend) desc when direction=all
        assert result["data"]["products"][0]["name"] == "Prod B"
        assert result["data"]["products"][0]["trend_30d_pct"] == -20
