"""Wave 14.7 — Financial Analyst Eval Harness.

End-to-end behavioural scaffolding that drives ``chat_service.chat()``
with mocked Anthropic responses + real tools + real envelope +
real period audit, and asserts that the AI received the context it
needs to behave like a "true financial analyst".

What this tests
---------------

This is NOT a test of Anthropic Sonnet's training — we cannot
deterministically test "the model said X" without paying for real
API calls. Instead, this harness verifies the SYSTEM CONTEXT that
flows TO Anthropic on each scenario:

  - The system prompt contains the right Rules (19-25) at the
    moment of inference
  - The tools list contains the right tools (entitlement-gated)
  - The period_context was correctly resolved into the system
    prompt's ACTIVE REPORT PERIOD block
  - When the AI's tool_use is processed, the dispatcher applies
    period injection correctly
  - The tool result fed back to Anthropic is envelope-compliant
    (has_data / _temporal_scope / _data_integrity / _source)
  - The period_audit accumulator captured the right forensic data

If all of these pass, the AI HAS what it needs to follow the
rules. The behavioural part (whether the AI ACTUALLY follows
the rules) is delegated to the Anthropic training; if it doesn't,
that's a prompt-engineering issue not a system issue.

Each scenario test maps to a specific failure mode in the
Wave 13 / Wave 14 audit doc — they are PERMANENT REGRESSION
SENTINELS.

Scenarios encoded:

  S1 — 2026-05-16 reproduction: user on YTD asks "qual è il mio
       health". Pre-Wave-14 AI quoted 44/100 (inventato). Post-
       Wave-14 the tool returns envelope with health=96 to the AI.
  S2 — YoY comparison: sign integrity (Rule 25).
  S3 — Tool error: tool returns _data_integrity.status=error.
  S4 — Truncation: tool returns _truncated=True structurally.
  S5 — Cross-turn period memory: turn 1 YTD, turn 2 follow-up.
  S6 — Snapshot vs period-filtered scope mixing.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Eval harness scaffolding ──────────────────────────────────────────────


class _ScriptedAnthropicMock:
    """Mock for ``services.claude_client.send_messages_with_tools``.

    Lets a scenario script the sequence of tool_use / text blocks the
    "model" emits. Captures everything the real chat() pipeline does
    in response — tool inputs, tool results, system prompt, history.
    """

    def __init__(self, scripted_responses):
        """scripted_responses is a list of "rounds", each one is:
            {
              "tool_calls": [{"name": "...", "input": {...}}, ...],  OR
              "text": "final answer text"
            }
        On each round the mock emits tool_use blocks (if any) and
        executes the corresponding on_tool_call, then proceeds.
        """
        self.script = list(scripted_responses)
        self.captured_tool_results = []  # what we fed back to "Claude"
        self.captured_systems = []       # system prompt each round
        self.captured_messages = []      # message history each round
        self.captured_on_round_calls = []
        self.tool_inputs_seen = []       # full tool inputs after injection

    async def __call__(
        self, *, system, messages, tools, on_tool_call,
        max_tokens, temperature, on_round=None,
        request_id=None, model_version=None, agent_id=None,
    ):
        self.captured_systems.append(system)
        self.captured_messages.append(list(messages))

        final_text = ""
        for round_idx, round_def in enumerate(self.script):
            if "tool_calls" in round_def:
                # Execute each scripted tool call through the real
                # on_tool_call pipeline. Capture the result and add
                # it to "what Claude would see in the next round".
                for tc in round_def["tool_calls"]:
                    result = await on_tool_call(tc["name"], tc.get("input", {}))
                    self.tool_inputs_seen.append({
                        "tool": tc["name"],
                        "model_input": tc.get("input", {}),
                    })
                    self.captured_tool_results.append({
                        "tool": tc["name"],
                        "result": result,
                    })
            if "text" in round_def:
                final_text = round_def["text"]
            if on_round is not None:
                try:
                    await on_round(round_idx, {
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "cache_read_tokens": 0,
                        "cache_creation_tokens": 0,
                        "latency_ms": 50,
                    })
                    self.captured_on_round_calls.append(round_idx)
                except Exception:
                    pass

        # Token usage summary (mocked)
        token_usage = {
            "input_tokens": 100 * len(self.script),
            "output_tokens": 50 * len(self.script),
        }
        return final_text, list(messages), token_usage


async def _run_eval_scenario(
    *,
    user_message: str,
    period_context: dict,
    scripted_anthropic: _ScriptedAnthropicMock,
    org_id: str = "org_eval",
    user_id: str = "user_eval",
    session_id: str = "session_eval",
    active_modules: set = None,
):
    """Drive ``chat_service.chat()`` end-to-end with the scripted mock.

    Returns a dict with the captured forensic state.
    """
    from services import chat_service
    from services.ai_tool_registry import get_tools_for_chat

    active_modules = active_modules or {"cashflow_monitor", "commerce_signals"}

    # Build a synthetic tools list + dispatcher matching what
    # ``get_tools_for_chat`` would produce, but bypassing the entitlement
    # DB query.
    from core.module_registry import get_all as registry_get_all
    fake_tools = []
    fake_executors = {}
    for module in registry_get_all():
        if module.module_key not in active_modules:
            continue
        if module.ai_tool_definitions and module.ai_tool_executor:
            for tool_def in module.ai_tool_definitions:
                fake_tools.append(tool_def)
                fake_executors[tool_def["name"]] = module.ai_tool_executor

    async def fake_dispatch(org_id, tool_name, tool_input):
        executor = fake_executors.get(tool_name)
        if not executor:
            return {"error": f"Tool {tool_name!r} not registered in test"}
        return await executor(org_id, tool_name, tool_input)

    async def fake_get_tools_for_chat(org_id):
        return fake_tools, fake_dispatch, active_modules

    with patch(
        "services.ai_tool_registry.get_tools_for_chat",
        new=fake_get_tools_for_chat,
    ), \
         patch(
            # The imports inside chat() are LAZY (``from services.
            # claude_client import send_messages_with_tools``). Patch
            # at the source module so the lazy import resolves to
            # the mock.
            "services.claude_client.send_messages_with_tools",
            new=scripted_anthropic,
         ), \
         patch(
            "services.claude_client.is_available",
            return_value=True,
         ), \
         patch(
            "services.llm.budget_guard.check_budget_or_raise",
            new=AsyncMock(),
         ), \
         patch(
            "repositories.chat_session_repository.find_session",
            new=AsyncMock(return_value=None),
         ), \
         patch(
            "repositories.chat_session_repository.upsert_messages",
            new=AsyncMock(),
         ), \
         patch(
            "repositories.usage_repository.record_usage",
            new=AsyncMock(),
         ), \
         patch(
            "repositories.organization_repository.find_by_id",
            new=AsyncMock(return_value={
                "id": org_id, "currency": "EUR",
                "commercial_plan_slug": "core",
            }),
         ), \
         patch(
            "repositories.billing_repository.get_commercial_plan",
            new=AsyncMock(return_value={
                "platform_limits": {"chat_session_ttl_days": 90},
            }),
         ), \
         patch(
            "services.chat_service._build_proactive_context",
            new=AsyncMock(return_value=""),
         ):
        reply = await chat_service.chat(
            org_id=org_id,
            session_id=session_id,
            user_message=user_message,
            locale="it",
            user_id=user_id,
            period_context=period_context,
        )

    return {
        "reply": reply,
        "tool_inputs_seen": scripted_anthropic.tool_inputs_seen,
        "tool_results_received": scripted_anthropic.captured_tool_results,
        "systems_passed": scripted_anthropic.captured_systems,
        "rounds_completed": scripted_anthropic.captured_on_round_calls,
    }


def _make_envelope_response(tool, has_data=True, data=None, period=None,
                              scope="period_filtered", integrity_ok=True,
                              caveat=None):
    """Convenience for building a mock tool response in envelope shape."""
    from core.tool_envelope import wrap_response, DataIntegrityStatus
    return wrap_response(
        tool=tool,
        has_data=has_data,
        data=data or {},
        currency="EUR",
        period=period,
        temporal_scope=scope,
        caveat=caveat,
        integrity_status=DataIntegrityStatus.OK.value if integrity_ok else "error",
        integrity_message=(None if integrity_ok else caveat or "Tool failed"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# S1 — Reproduction of the 2026-05-16 production incident
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_S1_ytd_health_query_no_hallucination_scaffold():
    """User on YTD filter asks "qual è il mio health". Pre-Wave-14 the
    AI quoted 44/100 (inventato). Post-Wave-14 the system MUST feed
    the AI an envelope-compliant tool result with health=96 AND have
    Rule 19 (SOURCE ATTRIBUTION) + Rule 21 (HAS_DATA BINDING) + Rule
    22 (NO ESTIMATION) in the system prompt.

    The Rules are documented in the prompt; the envelope carries the
    data verbatim. If both hold, the AI cannot legitimately quote
    anything other than 96 (and if it does, it's a prompt-engineering
    regression, caught by structural sentinels in this file)."""

    # The cashflow_monitor module is REAL — its query_cashflow_summary
    # tool calls build_ai_summary internally. We mock build_ai_summary
    # to return controlled YTD data, then let the real tool branch +
    # real envelope + real dispatcher run.
    from modules.cashflow_monitor.cashflow_summary import build_ai_summary

    fake_summary = {
        "has_data": True,
        "currency": "EUR",
        "period": {
            "label": "ytd",
            "start_date": "2026-01-01",
            "end_date": "2026-05-16",
            "days": 136,
            "semantic": "ytd",
        },
        "pnl": {
            "total_sales": 209954.34,
            "net_after_fixed": 90899.99,
            "operating_margin_pct": 44.6,
        },
        "health_score": {"score": 96, "label": "Eccellente"},
        "status": {"level": "ok"},
        "yoy": {
            "has_data": True,
            "pct": {
                "total_sales": 1808.7,
                "operating_margin_pct_pp_change": 3.2,
            },
        },
        "risk_focus": [],
        "action_focus": [],
        "period_comparison": {"direction": "stable",
                                "net_is_negative": False},
    }

    # The "Claude" we mock decides to call query_cashflow_summary
    # with the YTD dates (since the ACTIVE REPORT PERIOD instructs
    # that). Then it emits its final answer.
    anthropic = _ScriptedAnthropicMock([
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {"start_date": "2026-01-01", "end_date": "2026-05-16"},
        }]},
        {"text": "Il tuo health score YTD è 96/100 — Eccellente."},
    ])

    with patch(
        "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
        new=AsyncMock(return_value=fake_summary),
    ):
        result = await _run_eval_scenario(
            user_message="qual è il mio health score da inizio anno?",
            period_context={
                "label": "ytd",
                "start": "2026-01-01",
                "end":   "2026-05-16",
            },
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    # ── Assertion 1: tool called with YTD dates ──────────────────────────
    assert len(result["tool_inputs_seen"]) == 1
    seen = result["tool_inputs_seen"][0]
    assert seen["tool"] == "query_cashflow_summary"
    assert seen["model_input"]["start_date"] == "2026-01-01"
    assert seen["model_input"]["end_date"] == "2026-05-16"

    # ── Assertion 2: tool result fed to Claude is envelope-compliant ─────
    tool_result = result["tool_results_received"][0]["result"]
    assert isinstance(tool_result, dict)
    assert tool_result["has_data"] is True
    assert tool_result["_temporal_scope"] == "period_filtered"
    assert tool_result["_source"]["tool"] == "query_cashflow_summary"

    # ── Assertion 3: the envelope carries the REAL health score ─────────
    # If the tool's data block contained 96 then the AI saw 96.
    # Synthesising 44/48 would require the AI to IGNORE the envelope.
    assert tool_result.get("health_score", {}).get("score") == 96
    assert tool_result.get("pnl", {}).get("total_sales") == 209954.34
    assert tool_result.get("yoy", {}).get("pct", {}).get("total_sales") == 1808.7

    # ── Assertion 4: system prompt at inference has anti-hallucination rules
    system_payload = result["systems_passed"][0]
    # ``system`` can be a string or a list of {type, text} (Wave 10.B.1).
    # Flatten to one string for the contains checks.
    if isinstance(system_payload, list):
        system_text = "\n".join(b.get("text", "") for b in system_payload)
    else:
        system_text = str(system_payload)
    assert "19. SOURCE ATTRIBUTION" in system_text
    assert "20. HARD STOP ON TOOL ERROR" in system_text
    assert "21. HAS_DATA BINDING" in system_text
    assert "22. NO ESTIMATION" in system_text
    assert "ACTIVE REPORT PERIOD" in system_text
    assert "2026-01-01" in system_text  # YTD start date in prompt
    assert "2026-05-16" in system_text  # YTD end date in prompt


# ═══════════════════════════════════════════════════════════════════════════
# S2 — YoY sign integrity (Rule 25)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_S2_yoy_sign_integrity_envelope_carries_correct_sign():
    """The chat AI must read the SIGN from the tool's yoy.pct field
    rather than inferring it from prior context. We verify that the
    envelope delivers ``yoy.pct.total_sales = +1808.7`` (positive)
    to the AI — that's all the system can do; the AI's own sign
    handling is Rule 25's responsibility."""
    fake_summary = {
        "has_data": True,
        "currency": "EUR",
        "period": {"label": "ytd", "start_date": "2026-01-01",
                    "end_date": "2026-05-16", "days": 136},
        "pnl": {"total_sales": 209954.34},
        "yoy": {
            "has_data": True,
            "pct": {"total_sales": 1808.7},  # positive — growth
            "total_sales": 11000,  # prior-year absolute
        },
    }
    anthropic = _ScriptedAnthropicMock([
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {"start_date": "2026-01-01", "end_date": "2026-05-16"},
        }]},
        {"text": "YoY: ricavi +1808.7%."},
    ])

    with patch(
        "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
        new=AsyncMock(return_value=fake_summary),
    ):
        result = await _run_eval_scenario(
            user_message="confronto ricavi vs stesso periodo anno scorso",
            period_context={"label": "ytd",
                             "start": "2026-01-01", "end": "2026-05-16"},
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    tool_result = result["tool_results_received"][0]["result"]
    yoy_pct = tool_result.get("yoy", {}).get("pct", {}).get("total_sales")
    # The sign in the envelope MUST be positive (growth)
    assert yoy_pct == 1808.7
    assert yoy_pct > 0
    # Rule 25 in system prompt at inference
    system_text = result["systems_passed"][0]
    if isinstance(system_text, list):
        system_text = "\n".join(b.get("text", "") for b in system_text)
    assert "25. SIGN AND DIRECTION INTEGRITY" in system_text
    assert "+1808.7" in system_text  # The Rule 25 example anchored to this number


# ═══════════════════════════════════════════════════════════════════════════
# S3 — Tool error → AI must escalate (Rule 20)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_S3_tool_error_envelope_signals_integrity_error():
    """When a tool returns has_data=False + integrity=error, the
    envelope explicitly carries the error message. Combined with
    Rule 20 (HARD STOP ON TOOL ERROR) in the prompt, the AI MUST
    escalate to the user rather than synthesise numbers."""
    # smart_brief's "cashflow section failed" pattern — Wave 14.1.A
    # already makes this envelope-compliant. We trigger it by mocking
    # the inner build_ai_summary to raise.
    from modules.cashflow_monitor.cashflow_summary import build_ai_summary

    async def _failing_summary(*args, **kwargs):
        raise RuntimeError("simulated downstream failure")

    anthropic = _ScriptedAnthropicMock([
        {"tool_calls": [{
            "name": "query_smart_brief",
            "input": {"start_date": "2026-01-01", "end_date": "2026-05-16"},
        }]},
        {"text": "Il tool query_smart_brief ha fallito sulla sezione cashflow."},
    ])

    with patch(
        "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
        new=AsyncMock(side_effect=_failing_summary),
    ), \
         patch(
            "repositories.alert_repository.find_by_org",
            new=AsyncMock(return_value=[]),
         ):
        result = await _run_eval_scenario(
            user_message="dammi un brief",
            period_context={"label": "ytd",
                             "start": "2026-01-01", "end": "2026-05-16"},
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    tool_result = result["tool_results_received"][0]["result"]
    # The envelope still applies — but the cashflow section flags error
    assert tool_result.get("_temporal_scope") == "period_filtered"
    cashflow_section = tool_result.get("cashflow", {})
    assert isinstance(cashflow_section, dict)
    # The _hint guides the AI to escalate, not synthesise
    assert "_hint" in cashflow_section or "error" in cashflow_section
    # Rule 20 in the system prompt
    system_text = result["systems_passed"][0]
    if isinstance(system_text, list):
        system_text = "\n".join(b.get("text", "") for b in system_text)
    assert "20. HARD STOP ON TOOL ERROR" in system_text
    assert "NEVER synthesize" in system_text


# ═══════════════════════════════════════════════════════════════════════════
# S4 — Truncated tool result (Rule 23)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_S4_truncated_tool_result_signals_dropped_fields():
    """When the truncation pipeline (Wave 14.2) fires, the envelope
    carries ``_truncated`` + ``_truncated_fields`` + ``_hint``. Rule
    23 in the system prompt tells the AI to NEVER parse partial JSON
    and to re-call with a narrower scope."""
    # Build a summary that will DEFINITIVELY exceed the 30K cap so
    # Wave 14.2 fires. We pad each entry with a long string field to
    # blow past the cap without keys colliding via mod arithmetic.
    big_by_date = {
        # Unique date-like keys for 4000 entries
        f"2026-x{i:05d}": {
            "amount": float(i) * 100.0,
            "note": "padding text to push the result well past 30K chars " * 3,
        }
        for i in range(4000)
    }
    big_daily_series = [
        {"date": f"2026-y{i:05d}",
         "sales": float(i),
         "narrative": "additional weight on each entry to ensure cap exceeded " * 2}
        for i in range(4000)
    ]
    fake_summary = {
        "has_data": True,
        "currency": "EUR",
        "period": {"label": "ytd", "start_date": "2026-01-01",
                    "end_date": "2026-05-16", "days": 136},
        "pnl": {"total_sales": 209954.34},
        "health_score": {"score": 96, "label": "Eccellente"},
        "by_date": big_by_date,           # heavy
        "daily_series": big_daily_series,  # heavy
    }

    anthropic = _ScriptedAnthropicMock([
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {"start_date": "2026-01-01", "end_date": "2026-05-16"},
        }]},
        {"text": "I dati sono stati troncati, posso essere più mirato?"},
    ])

    with patch(
        "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
        new=AsyncMock(return_value=fake_summary),
    ):
        result = await _run_eval_scenario(
            user_message="full YTD analysis",
            period_context={"label": "ytd",
                             "start": "2026-01-01", "end": "2026-05-16"},
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    tool_result = result["tool_results_received"][0]["result"]
    # Truncation fired (Wave 14.2)
    assert tool_result.get("_truncated") is True
    assert tool_result["_truncated_by"] in (
        "wave14_structured", "wave14_head_only_fallback",
    )
    # Critical aggregates SURVIVED structured truncation (Pass 1 drops
    # by_date / daily_series first)
    assert tool_result.get("pnl", {}).get("total_sales") == 209954.34
    assert tool_result.get("health_score", {}).get("score") == 96
    # Rule 23 in system prompt
    system_text = result["systems_passed"][0]
    if isinstance(system_text, list):
        system_text = "\n".join(b.get("text", "") for b in system_text)
    assert "23. TRUNCATION HANDLING" in system_text
    assert "narrower" in system_text.lower() or "focus" in system_text.lower()


# ═══════════════════════════════════════════════════════════════════════════
# S5 — Cross-turn period memory (Rule 24)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_S5_cross_turn_period_memory_dispatcher_injects_dates():
    """Turn N: the user has YTD active. The model emits a tool call
    WITHOUT explicit start_date/end_date (typical for follow-ups).
    The dispatcher (Wave 13.1) MUST inject the YTD dates from
    period_context so the tool runs on the right window.

    Plus Rule 24 in the prompt instructs the model to RE-EMIT dates
    explicitly across turns."""
    fake_summary = {
        "has_data": True,
        "currency": "EUR",
        "period": {"label": "ytd"},
        "pnl": {"total_expenses": 114000},
    }

    anthropic = _ScriptedAnthropicMock([
        # Model omits dates — dispatcher must inject from period_context
        {"tool_calls": [{
            "name": "query_cashflow_summary",
            "input": {},  # no dates emitted
        }]},
        {"text": "Costi YTD: 114K."},
    ])

    with patch(
        "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
        new=AsyncMock(return_value=fake_summary),
    ) as mock_summary:
        await _run_eval_scenario(
            user_message="e i costi?",
            period_context={
                "label": "ytd",
                "start": "2026-01-01",
                "end":   "2026-05-16",
            },
            scripted_anthropic=anthropic,
            active_modules={"cashflow_monitor"},
        )

    # The actual build_ai_summary call received the YTD dates because
    # the dispatcher injected them when the model emitted none.
    assert mock_summary.await_count == 1
    _, kwargs = mock_summary.await_args
    assert kwargs["start_date"] == "2026-01-01"
    assert kwargs["end_date"] == "2026-05-16"


# ═══════════════════════════════════════════════════════════════════════════
# S6 — Scope discipline (Rule 18)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_S6_snapshot_tool_carries_all_time_scope():
    """When the AI calls a snapshot tool (e.g. query_top_customers),
    the envelope must carry ``_temporal_scope = all_time`` so the
    model qualifies its answer as "lifetime" rather than "for the
    period". Rule 18 in the prompt enforces this discipline."""
    fake_metrics = [
        {
            "customer_name": "ACME",
            "total_revenue": 50000,
            "transaction_count": 25,
            "last_purchase_date": "2026-04-01",
            "segment": "top",
            "revenue_share_pct": 25.0,
        },
    ]

    anthropic = _ScriptedAnthropicMock([
        {"tool_calls": [{"name": "query_top_customers", "input": {"limit": 5}}]},
        {"text": "Lifetime, ACME è il tuo top customer (50K all-time)."},
    ])

    with patch(
        "modules.customer_insights.repository.find_metrics_by_org",
        new=AsyncMock(return_value=fake_metrics),
    ):
        result = await _run_eval_scenario(
            user_message="chi sono i miei top customer?",
            period_context={"label": "ytd",
                             "start": "2026-01-01", "end": "2026-05-16"},
            scripted_anthropic=anthropic,
            active_modules={"customers_light"},
        )

    tool_result = result["tool_results_received"][0]["result"]
    # The envelope carries the all_time scope
    assert tool_result.get("_temporal_scope") == "all_time"
    # And the legacy data is also there for the AI to read
    assert tool_result.get("top_customers", [{}])[0].get("name") == "ACME"
    # Rule 18 in system prompt
    system_text = result["systems_passed"][0]
    if isinstance(system_text, list):
        system_text = "\n".join(b.get("text", "") for b in system_text)
    assert "18. TEMPORAL SCOPE DISCIPLINE" in system_text
    assert "all_time" in system_text


# ═══════════════════════════════════════════════════════════════════════════
# S7 — Anti-hallucination meta-test
# ═══════════════════════════════════════════════════════════════════════════


def test_S7_anti_hallucination_rules_block_present():
    """Sentinel: the full block of Rules 19-25 (Wave 14.HOTFIX
    discipline) appears in the system prompt at every chat
    construction. Any future commit that splits or removes them
    will trip here."""
    from services.chat_service import _PROMPT_CORE
    expected_rules = [
        "19. SOURCE ATTRIBUTION",
        "20. HARD STOP ON TOOL ERROR",
        "21. HAS_DATA BINDING",
        "22. NO ESTIMATION",
        "23. TRUNCATION HANDLING",
        "24. CROSS-TURN PERIOD MEMORY",
        "25. SIGN AND DIRECTION INTEGRITY",
    ]
    for rule in expected_rules:
        assert rule in _PROMPT_CORE, (
            f"Wave 14.7 regression — Rule {rule!r} missing from system "
            "prompt. The eval-harness anti-hallucination guarantee is "
            "void without it."
        )


def test_S8_envelope_scope_registry_complete_for_all_5_core_tools():
    """Every tool exercised by the eval scenarios must appear in
    the Wave 13.6 TOOL_SCOPE registry so dispatcher-level envelope
    wrapping (Wave 14.1.B) injects the scope correctly."""
    from core.tool_temporal_scope import TOOL_SCOPE
    eval_tools = [
        "query_cashflow_summary",
        "query_business_summary",
        "query_smart_brief",
        "query_top_customers",
        "query_revenue",
    ]
    for t in eval_tools:
        assert t in TOOL_SCOPE, (
            f"Wave 14.7 regression — tool {t!r} used in the eval "
            "harness is no longer in TOOL_SCOPE. The dispatcher will "
            "produce a non-envelope response and the AI loses scope "
            "discipline."
        )
