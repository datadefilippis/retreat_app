"""Wave 14.HOTFIX5 — auto-canonicalize period_comparison orientation.

2026-05-16, ~13:00 UTC (HOTFIX4 was live for ~10 minutes when the
user retested). The chat AI received the user's question "YTD 2026
vs YTD 2025" and emitted:

    query_period_comparison(
        period_a_start="2026-01-01",  # recent / current
        period_a_end="2026-05-16",
        period_b_start="2025-01-01",  # older / baseline
        period_b_end="2025-05-16",
    )

This is the natural way for a model to translate "X vs Y" — name
the first one A. Pre-HOTFIX5 the delta formula was:

    delta_pct = (period_b - period_a) / |period_a| * 100

With A=2026 (81275) and B=2025 (78885):
    delta = (78885 - 81275) / |81275| = -2.94%

The AI then read `revenue_pct: -2.9` (a CORRECT computation of "what
2025 represents relative to 2026") and reported "fatturato in CALO
del 2.9%". For a question "how is 2026 vs 2025?" the human expects
"+3% growth" — but the convention made the AI report the opposite.

HOTFIX4 (F1) added `_change_interpretation` with human labels, but
the labels were ALSO computed from the same delta sign — so "CALO"
was the label, matching the raw math but contradicting user intent.

HOTFIX5 fixes the root: the tool now AUTO-DETECTS chronological
order from the input dates. Whichever period_start is earlier is
labelled `period_baseline`; the other is `period_current`. Delta is
ALWAYS `(current - baseline)`, so positive = growth regardless of
input ordering.

This file is the regression sentinel that locks in the new
semantics — any future commit that breaks the auto-swap turns red.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Helper to mock the underlying aggregates ─────────────────────────────


def _mock_aggregates_2026_grew_over_2025():
    """Returns 4 patch context managers reproducing the Macelleria
    prod data: 2026 > 2025 on revenue, < on expenses, terminated
    Att.3 reduces 2026 fixed_costs."""
    from repositories import analytics_repository as ar

    async def _sales(org_id, start, end):
        return {start: 81275.63} if start.startswith("2026") else {start: 78884.94}

    async def _expenses(org_id, start, end):
        return {start: 17754.76} if start.startswith("2026") else {start: 18269.29}

    async def _purchases(org_id, start, end):
        return {start: 58380.41} if start.startswith("2026") else {start: 56148.03}

    async def _fixed(org_id, start, end):
        return 5337.11 if start.startswith("2026") else 6049.87

    return [
        patch.object(ar, "aggregate_sales_by_date", _sales),
        patch.object(ar, "aggregate_expenses_by_date", _expenses),
        patch.object(ar, "aggregate_purchases_by_date", _purchases),
        patch.object(ar, "aggregate_fixed_costs_total", _fixed),
    ]


async def _call_period_comparison(period_a_start, period_a_end,
                                    period_b_start, period_b_end):
    """Run the tool with mocked aggregates."""
    from modules.cashflow_monitor import ai_tools

    patches = _mock_aggregates_2026_grew_over_2025()
    for p in patches:
        p.start()
    try:
        return await ai_tools.execute_tool(
            "test-org",
            "query_period_comparison",
            {
                "period_a_start": period_a_start,
                "period_a_end":   period_a_end,
                "period_b_start": period_b_start,
                "period_b_end":   period_b_end,
            },
        )
    finally:
        for p in patches:
            p.stop()


# ── The critical regression: A=recent, B=older must NOT invert sign ──────


class TestAutoCanonicalize:
    """The tool must produce the same CORRECT semantics regardless
    of which way the model orders the periods."""

    @pytest.mark.asyncio
    async def test_a_recent_b_older_is_canonicalized(self):
        """The 2026-05-16 prod failure mode: model emits A=2026
        (recent), B=2025 (older). Pre-HOTFIX5 this produced
        delta_pct=-2.9 for revenue. Post-HOTFIX5 it must produce
        delta_pct=+3 with direction='up' / human_label='CRESCITA'."""
        result = await _call_period_comparison(
            "2026-01-01", "2026-05-16",  # period_a = recent
            "2025-01-01", "2025-05-16",  # period_b = older
        )

        # Revenue grew from 78885 (older) to 81275 (newer) → +3%
        rev_interp = result["_change_interpretation"]["revenue"]
        assert rev_interp["direction"] == "up", (
            f"HOTFIX5 regression — model emitted A=2026/B=2025 and "
            f"the tool produced direction={rev_interp['direction']!r}. "
            f"Must be 'up' (current=2026 grew over baseline=2025)."
        )
        assert "CRESCITA" in rev_interp["human_label"], (
            f"HOTFIX5 — revenue label must say CRESCITA, got: "
            f"{rev_interp['human_label']!r}"
        )

        # Delta pct should be positive (current - baseline)
        assert result["delta"]["revenue_pct"] > 0, (
            f"HOTFIX5 — delta.revenue_pct must be POSITIVE when "
            f"the more recent period has higher revenue. Got "
            f"{result['delta']['revenue_pct']}"
        )

    @pytest.mark.asyncio
    async def test_a_older_b_recent_also_canonicalized(self):
        """The mirror case: model emits A=2025 (older), B=2026
        (recent). Same canonical output expected."""
        result = await _call_period_comparison(
            "2025-01-01", "2025-05-16",  # period_a = older
            "2026-01-01", "2026-05-16",  # period_b = recent
        )

        rev_interp = result["_change_interpretation"]["revenue"]
        assert rev_interp["direction"] == "up"
        assert "CRESCITA" in rev_interp["human_label"]
        assert result["delta"]["revenue_pct"] > 0

    @pytest.mark.asyncio
    async def test_both_orderings_produce_identical_interpretation(self):
        """The killer test: the tool must produce semantically
        equivalent answers regardless of input ordering."""
        result_a_recent = await _call_period_comparison(
            "2026-01-01", "2026-05-16",
            "2025-01-01", "2025-05-16",
        )
        result_b_recent = await _call_period_comparison(
            "2025-01-01", "2025-05-16",
            "2026-01-01", "2026-05-16",
        )

        # _change_interpretation must be identical in both calls
        for metric in ("revenue", "expenses", "purchases",
                       "fixed_costs", "net_result"):
            interp_a = result_a_recent["_change_interpretation"][metric]
            interp_b = result_b_recent["_change_interpretation"][metric]
            assert interp_a["direction"] == interp_b["direction"], (
                f"HOTFIX5 — {metric} direction differs between "
                f"orderings: A-recent={interp_a['direction']!r} vs "
                f"B-recent={interp_b['direction']!r}. The tool MUST "
                f"be order-independent."
            )
            assert interp_a["human_label"] == interp_b["human_label"], (
                f"HOTFIX5 — {metric} human_label differs between "
                f"orderings."
            )
            assert interp_a["delta_pct_signed"] == interp_b["delta_pct_signed"]


# ── New baseline/current fields ──────────────────────────────────────────


class TestNewBaselineCurrentFields:
    """The response now includes period_baseline / period_current
    with semantic labels."""

    @pytest.mark.asyncio
    async def test_response_has_baseline_and_current_fields(self):
        result = await _call_period_comparison(
            "2026-01-01", "2026-05-16",
            "2025-01-01", "2025-05-16",
        )
        assert "period_baseline" in result
        assert "period_current" in result

        # Baseline should be the OLDER period (2025)
        assert result["period_baseline"]["start"] == "2025-01-01"
        assert result["period_current"]["start"] == "2026-01-01"

        # Baseline revenue should be the smaller number
        assert result["period_baseline"]["revenue"] == 78884.94
        assert result["period_current"]["revenue"] == 81275.63

    @pytest.mark.asyncio
    async def test_period_a_b_preserved_for_backward_compat(self):
        """period_a / period_b unchanged from input (backward compat)."""
        result = await _call_period_comparison(
            "2026-01-01", "2026-05-16",
            "2025-01-01", "2025-05-16",
        )
        assert result["period_a"]["start"] == "2026-01-01"
        assert result["period_b"]["start"] == "2025-01-01"

    @pytest.mark.asyncio
    async def test_orientation_metadata_present(self):
        result = await _call_period_comparison(
            "2026-01-01", "2026-05-16",
            "2025-01-01", "2025-05-16",
        )
        assert "_period_orientation" in result
        orient = result["_period_orientation"]
        assert orient["swapped_from_input"] is True
        assert "older" in orient["baseline_role"].lower() or "reference" in orient["baseline_role"].lower()
        assert "(current - baseline)" in orient["delta_convention"]


# ── Macelleria full prod scenario ────────────────────────────────────────


class TestMacelleriaProdScenarioPostHotfix5:
    """End-to-end: reproduce the exact prod call that produced the
    wrong answer, confirm post-HOTFIX5 it produces the right one."""

    @pytest.mark.asyncio
    async def test_macelleria_ytd_comparison_is_intuitive(self):
        result = await _call_period_comparison(
            "2026-01-01", "2026-05-16",  # current
            "2025-01-01", "2025-05-16",  # baseline
        )

        # The user expected: "fatturato cresciuto del +3%"
        assert result["delta"]["revenue_pct"] > 0
        assert "CRESCITA" in result["_change_interpretation"]["revenue"]["human_label"]

        # Expenses 2026 (17754) < 2025 (18269) → RIDUZIONE (good for business)
        assert result["delta"]["expenses_pct"] < 0
        exp_label = result["_change_interpretation"]["expenses"]["human_label"]
        assert "RIDUZIONE" in exp_label or "riduzione" in exp_label

        # Fixed costs 2026 (5337) < 2025 (6049) → RIDUZIONE
        assert result["delta"]["fixed_costs_pct"] < 0
        fc_label = result["_change_interpretation"]["fixed_costs"]["human_label"]
        assert "RIDUZIONE" in fc_label or "riduzione" in fc_label

        # Net result: both negative, 2026 (-197) > 2025 (-1582) →
        # PERDITA RIDOTTA = improvement
        net_interp = result["_change_interpretation"]["net_result"]
        assert net_interp["direction"] == "improvement"
        assert "PERDITA RIDOTTA" in net_interp["human_label"]


# ── Source-code sentinel ─────────────────────────────────────────────────


class TestHotfix5SourceSentinel:
    def test_swap_logic_present(self):
        import inspect
        from modules.cashflow_monitor import ai_tools
        src = inspect.getsource(ai_tools.execute_tool)
        # The Wave 14.HOTFIX5 marker + key concepts
        assert "Wave 14.HOTFIX5" in src
        assert "period_baseline" in src
        assert "period_current" in src
        assert "swapped" in src
