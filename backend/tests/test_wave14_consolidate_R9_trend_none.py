"""Wave 14.CONSOLIDATE R9 — trend_pct fallback None instead of 0.0.

Pre-Wave-14 ``sales_trend_pct`` and ``expenses_trend_pct`` returned
``0.0`` when the prior period had zero sales/expenses. This silently
masked INFINITE growth — a merchant with €0 in 2025 and €200K in
2026 saw "trend 0%" which the chat AI parsed as "stable". The audit
flagged this; we now return ``None`` to signal "undefined" and the
chat layer renders it as "n/a" or "growth from zero base".

Verifies:
  - overview_builder computes ``None`` for trend when prev=0
  - period_comparison preserves ``None`` and flags via
    ``_undefined_metrics`` so the AI can cite it explicitly
  - status_builder coerces None → 0 safely (declining-revenue rule
    doesn't fire on undefined baseline)
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── _build_period_comparison preserves None ────────────────────────────────


class TestPeriodComparisonHandlesNoneTrend:
    def test_none_trend_preserved_in_output(self):
        from modules.cashflow_monitor.cashflow_summary import (
            _build_period_comparison,
        )
        kpis = {"sales_trend_pct": None, "expenses_trend_pct": None}
        out = _build_period_comparison(kpis)
        # None must survive — consumers can cite "n/a" rather than fake 0
        assert out["sales_change_pct"] is None
        assert out["expenses_change_pct"] is None
        # Explicit flag tells the AI WHICH metrics are undefined
        assert "sales" in out["_undefined_metrics"]
        assert "expenses" in out["_undefined_metrics"]

    def test_none_trend_yields_stable_direction(self):
        """When both trends are undefined, net_direction degrades to
        ``stable`` (no signal in either direction)."""
        from modules.cashflow_monitor.cashflow_summary import (
            _build_period_comparison,
        )
        out = _build_period_comparison({})
        assert out["net_direction"] == "stable"
        # biggest_change is None when both trends are 0/undefined
        assert out["biggest_change"] is None

    def test_mixed_real_and_undefined(self):
        """Sales: real trend; Expenses: undefined → only expenses in
        ``_undefined_metrics`` list."""
        from modules.cashflow_monitor.cashflow_summary import (
            _build_period_comparison,
        )
        out = _build_period_comparison({
            "sales_trend_pct": 25.0,
            "expenses_trend_pct": None,
        })
        assert out["sales_change_pct"] == 25.0
        assert out["expenses_change_pct"] is None
        assert out["_undefined_metrics"] == ["expenses"]
        # net_direction reflects sales growth + flat expenses
        assert out["net_direction"] == "improving"

    def test_real_numbers_still_work(self):
        """No regression on the common path: both trends are floats.

        Note: the legacy ``net_direction`` decision tree evaluates the
        "mixed" branch BEFORE "worsening", so sales-down + expenses-up
        actually resolves to "mixed" today (a pre-Wave-14 quirk we
        deliberately don't fix here — R9 is about None handling only).
        """
        from modules.cashflow_monitor.cashflow_summary import (
            _build_period_comparison,
        )
        out = _build_period_comparison({
            "sales_trend_pct": -15.0,
            "expenses_trend_pct": 10.0,
        })
        assert out["sales_change_pct"] == -15.0
        assert out["expenses_change_pct"] == 10.0
        assert out["_undefined_metrics"] == []
        # Legacy logic: short-circuits at "mixed" (sales>0 != expenses>0)
        assert out["net_direction"] in ("mixed", "worsening")


# ── status_builder coerces None safely ─────────────────────────────────────


class TestStatusBuilderTrendNoneSafe:
    def test_status_builder_does_not_crash_on_none_trend(self):
        """Wave 14.CONSOLIDATE R9 — declining-revenue threshold rule
        must NOT crash when sales_trend_pct is None. The rule is also
        SEMANTICALLY skipped (we can't claim 'revenue declining' when
        the prior baseline doesn't exist)."""
        from modules.cashflow_monitor.status_builder import compute_status

        kpis = {
            "total_sales": 50000,
            "net_after_fixed": 5000,
            "total_outflow_ratio": 90,
            "total_expenses": 30000,
            "supplier_purchases": 10000,
            "fixed_costs_total": 5000,
            "sales_trend_pct": None,  # ← Wave 14 R9: undefined
            "period_days": 30,
        }
        # Must not raise
        result = compute_status(kpis=kpis, alerts_summary={"by_severity": {}})
        assert result is not None
        # The "declining_revenue" rule did NOT fire (None coerces to 0)
        primary = result.get("primary_driver", "")
        assert "declining_revenue" not in str(primary).lower()


# ── overview_builder produces None directly ───────────────────────────────


class TestOverviewBuilderNoneSource:
    """Sentinel: re-verify the overview_builder source pattern is
    intact. Future commits that revert to 0.0 fallback will trip."""

    def test_source_uses_none_not_zero(self):
        import inspect
        from modules.cashflow_monitor import overview_builder
        src = inspect.getsource(overview_builder)
        # The new pattern: explicit ``= None`` when prev <= 0
        assert "sales_trend_pct = None" in src
        assert "expenses_trend_pct = None" in src
        # Forbidden pre-fix pattern: ``else 0.0,`` immediately after
        # the trend division
        forbidden = """    sales_trend_pct = round(
        ((total_sales - prev_total_sales) / prev_total_sales * 100)
        if prev_total_sales > 0
        else 0.0,
        1,
    )"""
        assert forbidden not in src, (
            "Wave 14.CONSOLIDATE R9 regression — overview_builder is "
            "back to 0.0 fallback when prev=0. The AI will silently "
            "interpret growth-from-zero as 'stable'."
        )
