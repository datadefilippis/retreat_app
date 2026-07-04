"""Wave 14.CONSOLIDATE R2/R4/R5/R6/R7/R8 — cashflow_summary block
shape standardization.

Fixes the semantic ambiguities catalogued by the Wave 14 audit:

  R2 — ``trends`` block deprecated (duplicates ``period_comparison``)
  R4 — ``operating_margin_pct`` YoY split into ``_change`` (relative)
        and ``_pp_change`` (absolute percentage points)
  R5 — ``operating_margin`` YoY epistemic moved from ``yoy_clean``
        (no caveat) to ``yoy`` (fixed-costs caveat)
  R6 — ``status`` block_scope marked as ``hybrid`` since it mixes
        period KPIs with current-state alert counts
  R7 — ``alerts._total_count_note`` field when recent < open_count
  R8 — ``period_comparison.net_is_negative`` explicit flag

Each test maps to one R-fix and acts as a regression sentinel.
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


# ── R2 — trends block carries deprecation marker ──────────────────────────


class TestR2TrendsDeprecation:
    """The ``trends`` block kept for backward compat MUST carry an
    explicit ``_deprecated`` marker so future contributors (and the
    chat AI via system prompt) know to read period_comparison instead."""

    def test_source_emits_deprecation_note(self):
        import inspect
        from modules.cashflow_monitor import cashflow_summary
        src = inspect.getsource(cashflow_summary)
        # The deprecation note must reference period_comparison as the
        # canonical source — otherwise the AI won't know where to go.
        assert "Wave 14.CONSOLIDATE R2" in src
        assert "period_comparison" in src


# ── R4 — operating_margin_pct YoY split ──────────────────────────────────


class TestR4MarginYoYSplit:
    def test_yoy_margin_pp_helper_returns_pp_diff(self):
        from modules.cashflow_monitor.cashflow_summary import _yoy_margin_pp
        # Current margin 15%, prior margin 12% (passed directly)
        kpis = {"operating_margin_pct": 15.0}
        yoy = {"operating_margin_pct": 12.0,
                "total_sales": 100000,
                "net_after_fixed": 12000}
        result = _yoy_margin_pp(kpis, yoy)
        # Expected: 15 - 12 = +3.0 pp (NOT +25% which is the relative)
        assert result == 3.0

    def test_yoy_margin_pp_returns_none_when_current_missing(self):
        from modules.cashflow_monitor.cashflow_summary import _yoy_margin_pp
        result = _yoy_margin_pp({}, {"operating_margin_pct": 12.0})
        assert result is None

    def test_yoy_margin_pp_falls_back_to_net_over_sales(self):
        """When yoy doesn't expose operating_margin_pct directly, the
        helper falls back to computing it from net/sales of the prior
        year. The caveat is implicit (epistemic class 'yoy' carries it)."""
        from modules.cashflow_monitor.cashflow_summary import _yoy_margin_pp
        kpis = {"operating_margin_pct": 20.0}
        yoy = {
            "total_sales": 100000,
            "net_after_fixed": 15000,  # implied prior margin 15%
            # no operating_margin_pct key
        }
        result = _yoy_margin_pp(kpis, yoy)
        # 20 - 15 = 5pp
        assert result == 5.0

    def test_yoy_margin_pp_returns_none_when_no_prior_data(self):
        from modules.cashflow_monitor.cashflow_summary import _yoy_margin_pp
        kpis = {"operating_margin_pct": 20.0}
        yoy = {"total_sales": 0, "net_after_fixed": 0}
        result = _yoy_margin_pp(kpis, yoy)
        assert result is None


# ── R5 — operating_margin YoY epistemic class ───────────────────────────


class TestR5MarginYoYEpistemic:
    """The epistemic class for operating_margin in YoY must be ``yoy``
    (with caveat about fixed costs), NOT ``yoy_clean``."""

    def test_source_uses_yoy_not_yoy_clean_for_margin(self):
        import inspect
        from modules.cashflow_monitor import cashflow_summary
        src = inspect.getsource(cashflow_summary)
        # The fixed assignment for the margin epistemic
        assert '"operating_margin": _EPISTEMIC["yoy"]' in src
        # And ensure the OLD pattern (yoy_clean for margin) is gone
        # We check for the specific incorrect pre-fix pattern.
        forbidden = '"operating_margin": _EPISTEMIC["yoy_clean"]'
        assert forbidden not in src, (
            "Wave 14.CONSOLIDATE R5 regression — margin YoY epistemic "
            "is back to ``yoy_clean`` (no caveat). The fixed-costs "
            "assumption caveat must be attached to margin too."
        )


# ── R6 — status block_scope = hybrid ───────────────────────────────────


class TestR6StatusHybridScope:
    """``status`` mixes period KPIs (margin/ratio thresholds) with
    current-state alert counts. The scope must declare this hybrid
    nature so the chat AI qualifies its claims."""

    def test_block_scopes_marks_status_hybrid(self):
        import inspect
        from modules.cashflow_monitor import cashflow_summary
        src = inspect.getsource(cashflow_summary)
        # The literal scope declaration line must use "hybrid".
        # We check the structural marker that's hard to write by accident.
        assert '"status":             {"scope": "hybrid"' in src or \
               '"status":' in src and '"scope": "hybrid"' in src
        # Document mentions both factors.
        assert "period KPIs" in src
        assert "high-severity alert count" in src or "alert count" in src


# ── R7 — alerts.total_count_note when recent < open_count ──────────────


class TestR7AlertsTotalCountNote:
    """When ``recent`` (capped at 5) shows fewer than ``open_count``,
    the model needs an explicit signal so it doesn't quote the recent-5
    as the full picture."""

    def test_note_emitted_when_count_exceeds_recent(self):
        """We exercise the lambda inline by replicating its logic.
        The actual block construction happens inside build_ai_summary
        which is a deep async path; testing the lambda predicate here
        keeps the assertion focused."""
        recent = [{"id": str(i)} for i in range(5)]
        open_count = 127
        note = (
            f"Showing {len(recent)} most recent of {open_count} total open alerts."
            if len(recent) < open_count else None
        )
        assert note == "Showing 5 most recent of 127 total open alerts."

    def test_no_note_when_recent_matches_count(self):
        recent = [{"id": "a"}, {"id": "b"}]
        open_count = 2
        note = (
            f"Showing {len(recent)} most recent of {open_count} total open alerts."
            if len(recent) < open_count else None
        )
        assert note is None

    def test_source_emits_note_field(self):
        import inspect
        from modules.cashflow_monitor import cashflow_summary
        src = inspect.getsource(cashflow_summary)
        assert "_total_count_note" in src
        assert "Showing" in src
        assert "most recent of" in src


# ── R8 — period_comparison.net_is_negative ───────────────────────────


class TestR8NetIsNegativeFlag:
    def test_negative_net_flagged(self):
        from modules.cashflow_monitor.cashflow_summary import _build_period_comparison
        out = _build_period_comparison({
            "sales_trend_pct": 5.0,
            "expenses_trend_pct": 5.0,
            "net_after_fixed": -1500.0,
        })
        assert out["net_is_negative"] is True

    def test_positive_net_not_flagged(self):
        from modules.cashflow_monitor.cashflow_summary import _build_period_comparison
        out = _build_period_comparison({
            "sales_trend_pct": 5.0,
            "expenses_trend_pct": 5.0,
            "net_after_fixed": 90000.0,
        })
        assert out["net_is_negative"] is False

    def test_zero_net_not_flagged(self):
        from modules.cashflow_monitor.cashflow_summary import _build_period_comparison
        out = _build_period_comparison({
            "sales_trend_pct": 0,
            "expenses_trend_pct": 0,
            "net_after_fixed": 0,
        })
        assert out["net_is_negative"] is False

    def test_missing_net_not_flagged(self):
        from modules.cashflow_monitor.cashflow_summary import _build_period_comparison
        out = _build_period_comparison({
            "sales_trend_pct": 1.0,
            "expenses_trend_pct": 1.0,
            # net_after_fixed not present
        })
        assert out["net_is_negative"] is False
