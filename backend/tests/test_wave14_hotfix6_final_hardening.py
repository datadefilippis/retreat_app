"""Wave 14.HOTFIX6 — final hardening after the audit-identified
residual grey zones.

The post-HOTFIX5 audit identified 7 residual failure modes; only 2
warranted a fix because the other 5 were either false alarms (period
resolver supports ytd/mtd/qtd via the Wave 13.1 adapter) or already
mitigated (system prompt + epistemic caveats handle all-time scope
discipline).

This commit closes the last 2:

  F2 — Inconsistent zero/negative-baseline handling between
       ``_delta_pct`` (in query_period_comparison) and ``_yoy_pct``
       (in the cashflow_summary YoY block). Same logical question
       could return different answers via different tool paths.
       Fixed by extracting the canonical formula to
       ``core/delta_formulas.py``; both call sites delegate.

  F3 — Inverted dates (start_date > end_date) silently passed
       through to the tool, producing period_days < 0 and
       sign-flipped downstream math. Fixed by validation in
       the chat_service dispatcher that returns an explicit
       error envelope before tool dispatch.

This file is the regression sentinel for both fixes.
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


# ── F2: canonical compute_period_delta ────────────────────────────────────


class TestCanonicalDeltaFormula:
    """The canonical formula in core/delta_formulas.py must produce
    consistent output regardless of which subsystem calls it."""

    def test_standard_growth_case(self):
        from core.delta_formulas import compute_period_delta
        # 78885 (baseline) → 81275 (current). Macelleria YTD 2025→2026.
        r = compute_period_delta(78885.0, 81275.0)
        assert r["direction"] == "up"
        assert r["delta_pct"] > 0
        assert abs(r["delta_pct"] - 3.0) < 0.1
        assert r["delta_abs"] > 0
        assert r["baseline_sign"] == "positive"
        assert r["current_sign"] == "positive"

    def test_standard_decline_case(self):
        from core.delta_formulas import compute_period_delta
        r = compute_period_delta(18269.0, 17755.0)
        assert r["direction"] == "down"
        assert r["delta_pct"] < 0
        assert r["delta_abs"] < 0

    def test_zero_baseline_returns_none_pct(self):
        """When baseline is zero, delta_pct is mathematically
        undefined. Pre-HOTFIX6 _delta_pct returned 100 (or 0); _yoy_pct
        returned None. Canonical: None."""
        from core.delta_formulas import compute_period_delta
        r = compute_period_delta(0.0, 100.0)
        assert r["delta_pct"] is None
        assert r["direction"] == "undefined"
        assert r["delta_abs"] == 100.0

    def test_zero_to_zero_is_stable(self):
        from core.delta_formulas import compute_period_delta
        r = compute_period_delta(0.0, 0.0)
        assert r["delta_pct"] is None  # still undefined
        assert r["direction"] == "stable"

    def test_negative_baseline_loss_shrunk_positive_pct(self):
        """The key edge case: loss going from -1582 to -197 (smaller).
        Pre-HOTFIX6 _yoy_pct returned None; _delta_pct returned +87.5.
        Canonical: +87.5 (consistent across all callers)."""
        from core.delta_formulas import compute_period_delta
        r = compute_period_delta(-1582.0, -197.0)
        assert r["delta_pct"] is not None
        assert r["delta_pct"] > 0  # current "moved up" toward zero
        assert r["direction"] == "up"
        assert r["baseline_sign"] == "negative"
        assert r["current_sign"] == "negative"

    def test_negative_to_positive_loss_to_profit(self):
        from core.delta_formulas import compute_period_delta
        r = compute_period_delta(-500.0, 200.0)
        assert r["delta_pct"] is not None
        assert r["delta_pct"] > 0
        assert r["direction"] == "up"
        assert r["baseline_sign"] == "negative"
        assert r["current_sign"] == "positive"

    def test_stable_threshold_under_0_5_pct(self):
        from core.delta_formulas import compute_period_delta
        r = compute_period_delta(10000.0, 10020.0)  # +0.2%
        assert r["direction"] == "stable"

    def test_yoy_pct_now_uses_canonical_formula(self):
        """The overview_builder _yoy_pct delegates to
        compute_period_delta. Previously it returned None for any
        prev <= 0; now negatives produce a signed pct (consistent
        with query_period_comparison)."""
        from modules.cashflow_monitor.overview_builder import build_overview
        import inspect
        src = inspect.getsource(build_overview)
        # The function delegates to the canonical formula
        assert "compute_period_delta" in src

    def test_period_comparison_uses_canonical_formula(self):
        from modules.cashflow_monitor import ai_tools
        import inspect
        src = inspect.getsource(ai_tools.execute_tool)
        # The query_period_comparison branch imports the canonical
        # formula instead of defining _delta_pct inline
        assert "from core.delta_formulas import compute_period_delta" in src


# ── F3: dispatcher rejects inverted dates ────────────────────────────────


@pytest.mark.asyncio
async def test_dispatcher_rejects_inverted_start_end(caplog):
    """If the model emits start_date > end_date for any tool,
    the dispatcher must short-circuit with an error envelope."""
    import logging
    from tests.test_wave14_7_financial_analyst_eval import (
        _ScriptedAnthropicMock,
        _run_eval_scenario,
    )

    anthropic = _ScriptedAnthropicMock([
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {
                "start_date": "2026-05-16",  # AFTER end
                "end_date":   "2026-01-01",  # BEFORE start
            },
        }]},
        {"text": "Done."},
    ])

    with caplog.at_level(logging.WARNING, logger="services.chat_service"):
        await _run_eval_scenario(
            user_message="strange dates",
            period_context={
                "label": "30d", "start": "2026-04-17", "end": "2026-05-16",
            },
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    warnings = [r.message for r in caplog.records
                if r.levelno >= logging.WARNING]
    refused = any("inverted date pair" in w for w in warnings)
    assert refused, (
        "HOTFIX6 F3 — dispatcher must emit a WARNING with "
        "'inverted date pair' when start_date > end_date. Got: "
        + str(warnings)[:500]
    )


@pytest.mark.asyncio
async def test_dispatcher_rejects_inverted_period_a_in_comparison(caplog):
    """The period_comparison tool has its own pair check too."""
    import logging
    from tests.test_wave14_7_financial_analyst_eval import (
        _ScriptedAnthropicMock,
        _run_eval_scenario,
    )

    anthropic = _ScriptedAnthropicMock([
        {"tool_calls": [{
            "name": "query_period_comparison",
            "input": {
                "period_a_start": "2026-05-16",  # inverted A
                "period_a_end":   "2026-01-01",
                "period_b_start": "2025-01-01",
                "period_b_end":   "2025-05-16",
            },
        }]},
        {"text": "Done."},
    ])

    with caplog.at_level(logging.WARNING, logger="services.chat_service"):
        await _run_eval_scenario(
            user_message="inverted period_a",
            period_context=None,
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    warnings = [r.message for r in caplog.records
                if r.levelno >= logging.WARNING]
    refused = any(
        "inverted date pair" in w and "period_a_start>period_a_end" in w
        for w in warnings
    )
    assert refused


@pytest.mark.asyncio
async def test_dispatcher_accepts_correct_dates():
    """Sanity — the validation does NOT reject correctly-ordered
    dates."""
    import logging
    from tests.test_wave14_7_financial_analyst_eval import (
        _ScriptedAnthropicMock,
        _run_eval_scenario,
    )

    # Build a captured-call list to verify the tool ACTUALLY ran
    # (i.e. wasn't short-circuited).
    from modules.cashflow_monitor import cashflow_summary
    captured = []

    async def _spy_summary(org_id, period="30d", start_date=None,
                            end_date=None, locale="it"):
        captured.append({"start_date": start_date, "end_date": end_date})
        return {
            "has_data": True,
            "currency": "EUR",
            "period": {"label": period, "start_date": start_date, "end_date": end_date, "days": 30},
            "pnl": {},
            "health_score": {"score": 80},
        }

    anthropic = _ScriptedAnthropicMock([
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {
                "start_date": "2026-01-01",
                "end_date":   "2026-05-16",  # correct order
            },
        }]},
        {"text": "Done."},
    ])

    with patch(
        "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
        new=_spy_summary,
    ):
        await _run_eval_scenario(
            user_message="correct YTD dates",
            period_context=None,
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    assert len(captured) == 1, (
        "HOTFIX6 F3 regression — correct dates should NOT be "
        "rejected by the inversion validator."
    )


# ── Source-code sentinel ─────────────────────────────────────────────────


class TestHotfix6SourceSentinels:
    def test_dispatcher_has_inversion_check(self):
        import inspect
        from services.chat_service import chat
        src = inspect.getsource(chat)
        assert "Wave 14.HOTFIX6" in src
        assert "inverted_pairs" in src or "_inverted" in src

    def test_canonical_module_exists(self):
        from core.delta_formulas import compute_period_delta, delta_pct_signed
        assert callable(compute_period_delta)
        assert callable(delta_pct_signed)
