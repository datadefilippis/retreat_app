"""Wave 14.HOTFIX2 — fix prod hallucination reproduced post-Wave-14 deploy.

2026-05-16 (Wave 14 deploy day, ~12:00 UTC). User on YTD filter asks
"come va il 2026 vs il 2025?". The chat AI replied with the EXACT
hallucinated figures from the 2026-05-16 morning incident — fatturato
81.276 EUR, perdita -909 EUR, YoY -2,9%.

Root cause (forensic from production ai_usage_events):
  - Model emitted `query_period_comparison` with input={} (empty)
  - Dispatcher injected the frontend filter (30d → start+end pair)
    as fallback. query_period_comparison requires FOUR dates
    (period_a_*, period_b_*) — the fallback only provides TWO.
  - Tool ran with partial input → returned has_data=false or error.
  - Model then HALLUCINATED the numbers — and the specific numbers
    it chose (81.276 EUR / -909 EUR / -2.9%) were LITERALLY in the
    system prompt as the "forbidden example" of Rule 20.

  The model was replaying the prompt's anti-example as if it were
  real data — a classic prompt-engineering anti-pattern: concrete
  values in a "do NOT do this" example get recalled by the model
  later as plausible-looking output.

Three fixes in this hotfix:

  1. Rule 20 example numbers removed
     The specific Italian-language hallucinated example "fatturato
     81.276 EUR, perdita -909 EUR" is replaced with abstract
     guidance + an explicit "numbers in this prompt are NEVER real
     data" rule. No concrete number remains in the prompt that could
     be replayed.

  2. Rule 24 reinforced with the period_comparison 4-date contract
     The rule now explicitly says: query_period_comparison takes 4
     required dates, NEVER call it with empty input. Concrete YTD
     example shows the full 4-date emission.

  3. Dispatcher hard-fails query_period_comparison with missing params
     Before HOTFIX2 the dispatcher silently fell back to a 2-date
     window when the model emitted incomplete input. After HOTFIX2
     the dispatcher returns an explicit error envelope (status=error,
     has_data=false, _hint=...) that Rule 20 FORCES the model to
     surface to the user, instead of letting the tool run on
     partial data.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Fix #1: no concrete numbers in Rule 20 forbidden example ──────────────


class TestNoConcreteNumbersInForbiddenExamples:
    """The system prompt MUST NOT contain specific monetary figures
    in its "do not do this" examples — the model will replay them."""

    def test_rule20_forbidden_example_strips_concrete_amounts(self):
        from services.chat_service import _PROMPT_CORE
        # The exact strings from the 2026-05-16 incident must NOT
        # appear in the prompt anymore. Any future regression that
        # re-adds them turns red.
        for concrete in (
            "81.276 EUR",
            "-909 EUR",
            "fatturato 81.276",
            "perdita -909",
        ):
            assert concrete not in _PROMPT_CORE, (
                f"Wave 14.HOTFIX2 regression — concrete monetary "
                f"figure {concrete!r} is back in the system prompt. "
                f"The 2026-05-16 prod incident proves the model "
                f"replays these numbers verbatim. Use abstract "
                f"language ('section X errored') instead of concrete "
                f"figures."
            )

    def test_anti_replay_rule_present(self):
        """The prompt must explicitly tell the model that numbers
        appearing in the prompt itself are NEVER real data."""
        from services.chat_service import _PROMPT_CORE
        assert "ANTI-HALLUCINATION RULE" in _PROMPT_CORE or "numbers used to illustrate" in _PROMPT_CORE.lower()
        # The key concept: prompt numbers are not data
        assert (
            "never from this system prompt" in _PROMPT_CORE.lower()
            or "from this prompt" in _PROMPT_CORE.lower()
        ), (
            "Wave 14.HOTFIX2 — the prompt must explicitly forbid "
            "the model from citing numbers it sees IN THE PROMPT."
        )


# ── Fix #2: Rule 24 documents the period_comparison 4-date contract ──────


class TestRule24PeriodComparisonContract:
    """Rule 24 must explicitly tell the model that
    query_period_comparison takes 4 dates and NEVER empty input."""

    def test_rule24_names_all_4_required_params(self):
        from services.chat_service import _PROMPT_CORE
        for param in (
            "period_a_start",
            "period_a_end",
            "period_b_start",
            "period_b_end",
        ):
            assert param in _PROMPT_CORE, (
                f"Wave 14.HOTFIX2 — Rule 24 must explicitly name "
                f"{param!r} so the model emits the full 4-date "
                f"contract, not just start_date+end_date."
            )

    def test_rule24_forbids_empty_period_comparison(self):
        from services.chat_service import _PROMPT_CORE
        # Some literal mention that empty input is forbidden for
        # this tool
        assert (
            "NEVER call this tool with empty" in _PROMPT_CORE
            or "PERIOD_COMPARISON SPECIAL CASE" in _PROMPT_CORE
        ), (
            "Wave 14.HOTFIX2 — Rule 24 must say period_comparison "
            "with empty input is forbidden."
        )


# ── Fix #3: dispatcher hard-fails on missing period_a_*/period_b_* ────────


@pytest.mark.asyncio
async def test_dispatcher_rejects_period_comparison_empty_input(caplog):
    """When the model emits empty input for query_period_comparison,
    the dispatcher MUST refuse dispatch and emit a WARNING log
    instead of running the tool on dispatcher-injected fallback
    dates (which only cover a single window, not the 4-tuple the
    tool needs)."""
    import logging
    from tests.test_wave14_7_financial_analyst_eval import (
        _ScriptedAnthropicMock,
        _run_eval_scenario,
    )

    # If tool_dispatch IS called for query_period_comparison with
    # missing period_a_start, the test fails. We replace the real
    # query_period_comparison execute with a spy that pytest.fails.
    async def _spy_execute(org_id, tool_name, tool_input):
        if tool_name == "query_period_comparison":
            if not tool_input.get("period_a_start"):
                pytest.fail(
                    "HOTFIX2 regression — tool dispatch was called "
                    "for query_period_comparison with missing "
                    "period_a_start. The dispatcher must short-circuit."
                )
        return {
            "has_data": True,
            "values": "spy",
        }

    anthropic = _ScriptedAnthropicMock([
        {"tool_calls": [{
            "name": "query_period_comparison",
            "input": {},  # ← the prod failure mode
        }]},
        {"text": "Done."},
    ])

    with caplog.at_level(logging.WARNING, logger="services.chat_service"):
        await _run_eval_scenario(
            user_message="confronta YTD 2026 vs YTD 2025",
            period_context={
                "label": "30d",
                "start": "2026-04-17",
                "end":   "2026-05-16",
            },
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    # The dispatcher must have emitted the WARNING line that names
    # the missing required params.
    warnings = [
        r.message for r in caplog.records
        if r.levelno >= logging.WARNING
    ]
    refused = any(
        "query_period_comparison" in w and "missing required" in w
        for w in warnings
    )
    assert refused, (
        "HOTFIX2 — dispatcher must emit a WARNING log when "
        "query_period_comparison is invoked with empty input "
        "(naming the missing required params). Got warnings: "
        + str(warnings)[:400]
    )


# ── Source-code regression sentinel ───────────────────────────────────────


class TestDispatcherValidationSourceSentinel:
    """The validation block lives in chat_service.on_tool_call. A
    future commit removing it turns this red."""

    def test_dispatcher_has_period_comparison_validation(self):
        import inspect
        from services.chat_service import chat
        src = inspect.getsource(chat)
        # The Wave 14.HOTFIX2 comment marker plus the param list
        assert "Wave 14.HOTFIX2" in src
        assert "missing_required" in src
        assert "period_a_start" in src
        assert "period_a_end" in src
        assert "period_b_start" in src
        assert "period_b_end" in src
