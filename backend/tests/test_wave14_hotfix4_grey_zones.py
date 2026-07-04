"""Wave 14.HOTFIX4 — close the 3 structural grey zones identified
by the 2026-05-16 audit.

The user reported the chat AI giving sign-flipped answers and being
unable to drill into fixed_costs / health_score. The audit found
3 root causes — none of them AI hallucinations, all of them
structural issues with the tool layer:

  F1. query_period_comparison returns raw signed percentages
      (e.g. `revenue_pct: -2.9`) without a direction label. When
      the user emitted period_a=2026, period_b=2025, the math
      produced a negative pct (because period_b < period_a) and
      the AI faithfully reported "fatturato in calo del 2,9%" —
      while the user reads "2026 vs 2025" as "did 2026 grow?".
      The convention was ambiguous and the AI had to deduce it.

  F2. No tool returns fixed_costs PER LINE ITEM. The AI only had
      ``query_fixed_costs`` (totale + by_category). When the user
      said "Finanziamento Att.3 was closed in March", the AI had
      no way to ask "show me Att.3's contribution in the period"
      — it could only report the aggregate.

  F3. query_health_score_breakdown didn't exist as a standalone
      tool. The breakdown WAS computed (compute_health_score
      returns it) and WAS included in cashflow_summary.health_score,
      but the AI had to wade through a 1500-char summary to find
      it. With a dedicated tool, "perché il mio score è X?" is
      one call away.

This file is the regression sentinel for all 3 fixes.
"""

import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── F1: direction-labelled change interpretation ──────────────────────────


class TestDirectionLabels:
    """For each metric, the helper produces a human_label that
    bakes in the direction so the AI doesn't have to deduce it."""

    def test_revenue_growth_produces_crescita_label(self):
        from modules.cashflow_monitor.ai_tools import _interpret_change
        # 81276 (2026) vs 78885 (2025) — the exact prod numbers
        result = _interpret_change(
            "revenue", value_a=78885.0, value_b=81276.0,
            delta_pct=3.0, currency="EUR",
        )
        assert result["direction"] == "up"
        assert "CRESCITA" in result["human_label"]
        assert "+3.0%" in result["human_label"] or "+3%" in result["human_label"]
        assert "78885" in result["human_label"] or "78885.00" in result["human_label"]
        assert "81276" in result["human_label"] or "81276.00" in result["human_label"]

    def test_revenue_decline_produces_calo_label(self):
        from modules.cashflow_monitor.ai_tools import _interpret_change
        result = _interpret_change(
            "revenue", value_a=100000.0, value_b=85000.0,
            delta_pct=-15.0, currency="EUR",
        )
        assert result["direction"] == "down"
        assert "CALO" in result["human_label"]

    def test_expenses_up_is_labelled_as_aumento_negative_sentiment(self):
        """For cost categories (expenses/purchases/fixed_costs), UP
        is BAD. The label must say 'AUMENTO' with cost-cresciuto
        framing, not 'crescita'."""
        from modules.cashflow_monitor.ai_tools import _interpret_change
        result = _interpret_change(
            "expenses", value_a=10000.0, value_b=12000.0,
            delta_pct=20.0, currency="EUR",
        )
        assert result["direction"] == "up"
        assert "AUMENTO" in result["human_label"]
        assert "crescita" not in result["human_label"].lower(), (
            "F1 — expenses UP should NOT be labelled 'crescita' "
            "(that's revenue framing). For costs UP is bad."
        )

    def test_expenses_down_is_labelled_as_riduzione_positive_sentiment(self):
        from modules.cashflow_monitor.ai_tools import _interpret_change
        result = _interpret_change(
            "fixed_costs", value_a=6000.0, value_b=5300.0,
            delta_pct=-11.7, currency="EUR",
        )
        assert result["direction"] == "down"
        assert "RIDUZIONE" in result["human_label"]
        assert "miglioramento" in result["human_label"].lower()

    def test_net_result_loss_shrunk_is_improvement(self):
        """The CLASSIC sign-flip trap: both periods negative, loss
        got smaller. AI must report 'PERDITA RIDOTTA' not
        'crescita del +X%'."""
        from modules.cashflow_monitor.ai_tools import _interpret_change
        # Loss went from -1582 to -909 — improvement
        result = _interpret_change(
            "net_result", value_a=-1582.0, value_b=-909.0,
            delta_pct=42.5, currency="EUR",
        )
        assert result["direction"] == "improvement"
        assert "PERDITA RIDOTTA" in result["human_label"]
        # Critical: the label must NOT say "crescita" (could be misread
        # as profit growth)
        assert "crescita" not in result["human_label"].lower()

    def test_net_result_loss_grew_is_deterioration(self):
        from modules.cashflow_monitor.ai_tools import _interpret_change
        result = _interpret_change(
            "net_result", value_a=-500.0, value_b=-1500.0,
            delta_pct=-200.0, currency="EUR",
        )
        assert result["direction"] == "deterioration"
        assert "PERDITA AUMENTATA" in result["human_label"]

    def test_net_result_loss_to_profit_is_drastic_improvement(self):
        from modules.cashflow_monitor.ai_tools import _interpret_change
        result = _interpret_change(
            "net_result", value_a=-2000.0, value_b=500.0,
            delta_pct=125.0, currency="EUR",
        )
        assert result["direction"] == "improvement"
        assert "PASSATO DA PERDITA A PROFITTO" in result["human_label"]

    def test_net_result_profit_to_loss_is_drastic_deterioration(self):
        from modules.cashflow_monitor.ai_tools import _interpret_change
        result = _interpret_change(
            "net_result", value_a=3000.0, value_b=-1000.0,
            delta_pct=-133.3, currency="EUR",
        )
        assert result["direction"] == "deterioration"
        assert "PASSATO DA PROFITTO A PERDITA" in result["human_label"]

    def test_stable_metric_under_0_5_pct_marked_stable(self):
        from modules.cashflow_monitor.ai_tools import _interpret_change
        result = _interpret_change(
            "revenue", value_a=10000.0, value_b=10010.0,
            delta_pct=0.1, currency="EUR",
        )
        assert result["direction"] == "stable"
        assert "stabile" in result["human_label"].lower()


# ── F2: query_fixed_costs_detail / aggregate_fixed_costs_detail ──────────


class TestFixedCostsDetailRepository:
    """The new repository function returns per-cost-item detail
    with accurate proration."""

    @pytest.mark.asyncio
    async def test_aggregate_returns_one_item_per_active_cost(self):
        """Mock the fixed_costs_collection with the Macelleria
        scenario and assert the output structure."""
        from repositories import analytics_repository as ar

        fake_docs = [
            {"name": "Finanziament Attività 3", "amount": 277.70,
             "frequency": "monthly", "start_date": "2024-05-01",
             "end_date": "2026-02-28", "category": "finanziamento",
             "is_active": True, "organization_id": "test"},
            {"name": "Mutuo", "amount": 663.64,
             "frequency": "monthly", "start_date": "2024-05-01",
             "end_date": "2028-02-29", "category": "finanziamento",
             "is_active": True, "organization_id": "test"},
            {"name": "Att.1 chiuso 2024", "amount": 531.54,
             "frequency": "monthly", "start_date": "2024-05-01",
             "end_date": "2024-07-21", "category": "finanziamento",
             "is_active": True, "organization_id": "test"},
        ]

        class FakeCursor:
            def __init__(self, docs): self.docs = docs
            async def to_list(self, n): return self.docs

        fake_collection = type("FakeColl", (), {
            "find": lambda self, *a, **kw: FakeCursor(fake_docs),
        })()

        with patch.object(ar, "fixed_costs_collection", fake_collection):
            items = await ar.aggregate_fixed_costs_detail(
                "test", "2026-01-01", "2026-05-16",
            )

        # Att.1 ended in 2024 — should NOT appear
        names = [it["name"] for it in items]
        assert "Att.1 chiuso 2024" not in names
        assert "Finanziament Attività 3" in names
        assert "Mutuo" in names

    @pytest.mark.asyncio
    async def test_terminated_in_period_flag_is_set_correctly(self):
        from repositories import analytics_repository as ar

        fake_docs = [
            {"name": "Att.3 ended Feb 28", "amount": 277.70,
             "frequency": "monthly", "start_date": "2024-05-01",
             "end_date": "2026-02-28", "category": "finanziamento",
             "is_active": True, "organization_id": "test"},
            {"name": "Mutuo ends 2028", "amount": 663.64,
             "frequency": "monthly", "start_date": "2024-05-01",
             "end_date": "2028-02-29", "category": "finanziamento",
             "is_active": True, "organization_id": "test"},
        ]

        class FakeCursor:
            def __init__(self, docs): self.docs = docs
            async def to_list(self, n): return self.docs

        fake_collection = type("FakeColl", (), {
            "find": lambda self, *a, **kw: FakeCursor(fake_docs),
        })()

        with patch.object(ar, "fixed_costs_collection", fake_collection):
            items = await ar.aggregate_fixed_costs_detail(
                "test", "2026-01-01", "2026-05-16",
            )

        att3 = next(it for it in items if "Att.3" in it["name"])
        mutuo = next(it for it in items if "Mutuo" in it["name"])

        assert att3["terminated_in_period"] is True, (
            "F2 — Att.3 ends Feb 28 which is INSIDE the YTD 2026 "
            "query window; terminated_in_period must be True."
        )
        assert mutuo["terminated_in_period"] is False, (
            "F2 — Mutuo ends 2028 which is OUTSIDE the YTD 2026 "
            "query window; terminated_in_period must be False."
        )

    @pytest.mark.asyncio
    async def test_days_active_matches_clamped_window(self):
        """Att.3 (ends Feb 28) in YTD 2026: only Jan 1 - Feb 28
        = 59 days, not the full 136 days of the period."""
        from repositories import analytics_repository as ar

        fake_docs = [
            {"name": "Att.3", "amount": 277.70, "frequency": "monthly",
             "start_date": "2024-05-01", "end_date": "2026-02-28",
             "category": "finanziamento", "is_active": True,
             "organization_id": "test"},
        ]

        class FakeCursor:
            def __init__(self, docs): self.docs = docs
            async def to_list(self, n): return self.docs

        fake_collection = type("FakeColl", (), {
            "find": lambda self, *a, **kw: FakeCursor(fake_docs),
        })()

        with patch.object(ar, "fixed_costs_collection", fake_collection):
            items = await ar.aggregate_fixed_costs_detail(
                "test", "2026-01-01", "2026-05-16",
            )

        att3 = items[0]
        # Jan 1 - Feb 28 inclusive = 31 + 28 = 59 days
        assert att3["days_active_in_period"] == 59
        # Total period: Jan 1 - May 16 = 136 days
        assert att3["days_in_period"] == 136
        # Prorated: 277.70 * 59 / 30 ≈ 546.10
        assert abs(att3["prorated_contribution"] - 546.10) < 1.0


# ── F3: query_health_score_breakdown ──────────────────────────────────────


class TestHealthScoreBreakdownTool:
    """The new tool returns the 5-dimension breakdown as a
    first-class response."""

    def test_tool_is_registered(self):
        from modules.cashflow_monitor.ai_tools import TOOL_DEFINITIONS
        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "query_health_score_breakdown" in names

    def test_tool_description_mentions_dimensions(self):
        from modules.cashflow_monitor.ai_tools import TOOL_DEFINITIONS
        tool = next(
            t for t in TOOL_DEFINITIONS
            if t["name"] == "query_health_score_breakdown"
        )
        # The description should help the AI know when to call it
        desc = tool["description"]
        assert "perche" in desc.lower() or "spiegare" in desc.lower()
        assert "net_margin" in desc
        assert "5 dimensioni" in desc or "5 dimension" in desc.lower()

    def test_tool_is_in_TOOL_SCOPE_registry(self):
        from core.tool_temporal_scope import TOOL_SCOPE
        assert "query_health_score_breakdown" in TOOL_SCOPE
        assert TOOL_SCOPE["query_health_score_breakdown"] == "period_filtered"

    def test_fixed_costs_detail_tool_registered(self):
        from modules.cashflow_monitor.ai_tools import TOOL_DEFINITIONS
        from core.tool_temporal_scope import TOOL_SCOPE
        names = [t["name"] for t in TOOL_DEFINITIONS]
        assert "query_fixed_costs_detail" in names
        assert "query_fixed_costs_detail" in TOOL_SCOPE


# ── period_comparison return shape includes the new fields ───────────────


class TestPeriodComparisonReturnsInterpretation:
    """The return dict from execute_tool('query_period_comparison')
    must include _change_interpretation."""

    @pytest.mark.asyncio
    async def test_period_comparison_returns_change_interpretation(self):
        from modules.cashflow_monitor import ai_tools
        from repositories import analytics_repository as ar

        # Mock the underlying aggregates to return the prod numbers.
        # These imports happen INSIDE execute_tool, so we patch at the
        # source module (analytics_repository), not at ai_tools.
        async def _fake_sales(org_id, start, end):
            return {start: 81275.63} if start.startswith("2026") else {start: 78884.94}

        async def _fake_expenses(org_id, start, end):
            return {start: 17754.76} if start.startswith("2026") else {start: 18269.29}

        async def _fake_purchases(org_id, start, end):
            return {start: 58000.0} if start.startswith("2026") else {start: 60232.0}

        async def _fake_fixed(org_id, start, end):
            return 5300.0 if start.startswith("2026") else 6050.0

        async def _fake_currency(org_id):
            return "EUR"

        # Find the org-currency lookup callsite — likely in
        # ai_tools.execute_tool. It's imported as get_org_currency
        # from somewhere; we'll patch at ai_tools level if possible.
        with patch.object(ar, "aggregate_sales_by_date", _fake_sales), \
             patch.object(ar, "aggregate_expenses_by_date", _fake_expenses), \
             patch.object(ar, "aggregate_purchases_by_date", _fake_purchases), \
             patch.object(ar, "aggregate_fixed_costs_total", _fake_fixed):
            # currency lookup happens early in execute_tool — patch
            # whatever is importable
            try:
                from repositories import org_repository as _orgrepo
                _orgrepo_patch = patch.object(_orgrepo, "get_org_currency", _fake_currency)
                _orgrepo_patch.start()
            except Exception:
                _orgrepo_patch = None

            try:
                result = await ai_tools.execute_tool(
                    "test-org",
                    "query_period_comparison",
                    {
                        "period_a_start": "2025-01-01",
                        "period_a_end":   "2025-05-16",
                        "period_b_start": "2026-01-01",
                        "period_b_end":   "2026-05-16",
                    },
                )
            finally:
                if _orgrepo_patch is not None:
                    _orgrepo_patch.stop()

        assert "_change_interpretation" in result, (
            "F1 — period_comparison must include _change_interpretation "
            "with direction-labelled human strings."
        )
        interp = result["_change_interpretation"]
        for metric in ("revenue", "expenses", "purchases",
                       "fixed_costs", "net_result"):
            assert metric in interp
            assert "direction" in interp[metric]
            assert "human_label" in interp[metric]

        # The revenue interpretation must say CRESCITA (not CALO)
        # for the +3% case
        assert interp["revenue"]["direction"] == "up"
        assert "CRESCITA" in interp["revenue"]["human_label"], (
            "F1 — for period_a=2025 (78885), period_b=2026 (81275), "
            "revenue interpretation MUST say CRESCITA. Got: "
            + interp["revenue"]["human_label"]
        )

        assert "_convention_note" in result
