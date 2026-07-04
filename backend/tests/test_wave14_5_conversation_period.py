"""Wave 14.5 — Conversation period inheritance (intra-chat).

When the chat AI emits explicit ``start_date``/``end_date`` on a
tool call (typically the first call when the user asks for a
non-default window like "YTD"), the dispatcher now CAPTURES those
dates as the conversation period for the REMAINDER of the same
chat() call. Subsequent tool calls that omit dates inherit the
conversation period rather than falling back to the frontend's
period_context.

Concrete scenario (the gap that Rule 24 alone doesn't fully close):

  User filter: 30d (frontend default)
  User message: "fatturato YTD vs anno scorso, e i costi?"

  Model round 1: query_period_comparison(
                   period_a_start="2026-01-01", period_a_end="2026-05-16",
                   period_b_start="2025-01-01", period_b_end="2025-05-16",
                 )
                 → dispatcher captures (2026-01-01, 2026-05-16) as
                   the conversation period
  Model round 2: query_expenses()   ← omits dates (Rule 24 violation)
                 → pre-Wave-14.5: dispatcher injects 30d from
                   period_context — WRONG WINDOW
                 → Wave 14.5: dispatcher injects 2026-01-01/2026-05-16
                   from conversation period — CORRECT WINDOW

The chat AI gets the right data on round 2 even if the model
forgot to re-emit dates. Rule 24 still tells the model to re-emit,
but the mechanical layer is no longer the failure point.

Scope: intra-chat (within one chat() call across multiple
Anthropic rounds). Cross-turn (multi-user-message) persistence
is a future extension — Wave 13.2 audit logging + the existing
Rule 24 prompt instruction cover that case for now.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Reuse the eval-harness mock from test_wave14_7 ────────────────────────


from tests.test_wave14_7_financial_analyst_eval import (
    _ScriptedAnthropicMock,
    _run_eval_scenario,
)


# ── Core conversation-frame inheritance ────────────────────────────────────


@pytest.mark.asyncio
async def test_explicit_dates_become_conversation_frame_for_next_call():
    """Round 1: model emits explicit YTD dates. Round 2: model omits
    dates. The dispatcher must inject the YTD dates (from the
    captured conversation period) rather than the 30d frontend
    filter."""
    from modules.cashflow_monitor.cashflow_summary import build_ai_summary

    # Track which dates each call to build_ai_summary received.
    captured_summary_calls = []

    async def _spy_summary(org_id, period="30d", start_date=None,
                            end_date=None, locale="it"):
        captured_summary_calls.append({
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
        })
        return {
            "has_data": True,
            "currency": "EUR",
            "period": {
                "label": period,
                "start_date": start_date or "n/a",
                "end_date": end_date or "n/a",
                "days": 30,
            },
            "pnl": {"total_sales": 100, "total_expenses": 50},
            "health_score": {"score": 80, "label": "Buono"},
        }

    anthropic = _ScriptedAnthropicMock([
        # Round 1: model explicitly asks for YTD
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {
                "start_date": "2026-01-01",
                "end_date":   "2026-05-16",
            },
        }]},
        # Round 2: model continues the conversation but omits dates
        # (the failure mode the conversation period inheritance
        # protects against)
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {},  # ← no dates
        }]},
        {"text": "Done."},
    ])

    with patch(
        "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
        new=_spy_summary,
    ):
        await _run_eval_scenario(
            user_message="fatturato YTD, e i costi?",
            # Frontend filter is 30d (the user changed nothing)
            period_context={
                "label": "30d",
                "start": "2026-04-17",
                "end":   "2026-05-16",
            },
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    # Two calls happened — verify each got the right window.
    assert len(captured_summary_calls) == 2

    # Round 1: model's explicit YTD dates
    assert captured_summary_calls[0]["start_date"] == "2026-01-01"
    assert captured_summary_calls[0]["end_date"] == "2026-05-16"

    # Round 2: WAVE 14.5 — the dispatcher inherited the YTD frame
    # from round 1 even though the model emitted no dates.
    # Pre-Wave-14.5 this would be 30d (2026-04-17 / 2026-05-16).
    assert captured_summary_calls[1]["start_date"] == "2026-01-01", (
        "Wave 14.5 regression — round 2 tool call did NOT inherit the "
        "conversation period from round 1's explicit YTD dates."
    )
    assert captured_summary_calls[1]["end_date"] == "2026-05-16"


# ── Frontend period_context wins on the FIRST call ─────────────────────────


@pytest.mark.asyncio
async def test_no_conversation_frame_yet_falls_back_to_period_context():
    """If the model never emitted explicit dates, the dispatcher
    falls back to the frontend period_context. This is the legacy
    Wave 13.1 behaviour — Wave 14.5 must not break it."""
    from modules.cashflow_monitor.cashflow_summary import build_ai_summary

    captured_calls = []

    async def _spy_summary(org_id, period="30d", start_date=None,
                            end_date=None, locale="it"):
        captured_calls.append({
            "start_date": start_date,
            "end_date": end_date,
        })
        return {
            "has_data": True,
            "currency": "EUR",
            "period": {"label": "30d"},
            "pnl": {},
            "health_score": {"score": 75},
        }

    anthropic = _ScriptedAnthropicMock([
        # Model omits dates from the very first call
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {},
        }]},
        {"text": "Done."},
    ])

    with patch(
        "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
        new=_spy_summary,
    ):
        await _run_eval_scenario(
            user_message="come va?",
            period_context={
                "label": "30d",
                "start": "2026-04-17",
                "end":   "2026-05-16",
            },
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    assert len(captured_calls) == 1
    # No conversation frame had been set → fall back to period_context
    assert captured_calls[0]["start_date"] == "2026-04-17"
    assert captured_calls[0]["end_date"] == "2026-05-16"


# ── Model can change the frame mid-conversation ───────────────────────────


@pytest.mark.asyncio
async def test_model_can_switch_the_conversation_frame():
    """Round 1: YTD frame. Round 2: model explicitly switches to Q1
    by emitting different dates. Round 3 inherits the NEW Q1 frame,
    not the old YTD."""
    from modules.cashflow_monitor.cashflow_summary import build_ai_summary

    captured = []

    async def _spy_summary(org_id, period="30d", start_date=None,
                            end_date=None, locale="it"):
        captured.append({"start_date": start_date, "end_date": end_date})
        return {
            "has_data": True, "currency": "EUR",
            "period": {"label": period},
            "pnl": {},
            "health_score": {"score": 70},
        }

    anthropic = _ScriptedAnthropicMock([
        # Round 1: YTD
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {"start_date": "2026-01-01", "end_date": "2026-05-16"},
        }]},
        # Round 2: model switches to Q1
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {"start_date": "2026-01-01", "end_date": "2026-03-31"},
        }]},
        # Round 3: model omits dates → must inherit Q1 (round 2),
        # NOT YTD (round 1) — the most recent explicit emission wins.
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {},
        }]},
        {"text": "Done."},
    ])

    with patch(
        "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
        new=_spy_summary,
    ):
        await _run_eval_scenario(
            user_message="confronta YTD e poi Q1, dimmi i costi",
            period_context={"label": "30d", "start": "2026-04-17",
                              "end": "2026-05-16"},
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    assert len(captured) == 3
    assert captured[0] == {"start_date": "2026-01-01",
                            "end_date": "2026-05-16"}  # YTD
    assert captured[1] == {"start_date": "2026-01-01",
                            "end_date": "2026-03-31"}  # Q1
    # Round 3 inherits the MOST RECENT frame (Q1), not the original YTD
    assert captured[2] == {"start_date": "2026-01-01",
                            "end_date": "2026-03-31"}, (
        "Wave 14.5 — round 3 should inherit the LATEST explicit frame "
        "(Q1 from round 2), not the original YTD (round 1)."
    )


# ── Source-code regression sentinel ───────────────────────────────────────


class TestSourceSentinel:
    def test_dispatcher_captures_conversation_period(self):
        import inspect
        from services.chat_service import chat
        src = inspect.getsource(chat)
        # The dispatcher must have the _conv_period closure variable
        assert "_conv_period" in src, (
            "Wave 14.5 regression — chat() dispatcher no longer "
            "captures the conversation period. Round 2+ tool calls "
            "will fall back to period_context (frontend filter), "
            "breaking the multi-round frame coherence."
        )
        # The injection priority is documented
        assert "Wave 14.5" in src
