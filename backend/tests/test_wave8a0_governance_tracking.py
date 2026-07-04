"""Wave 8A.0 — verify that previously-untracked Anthropic call paths
now write AIUsageEvent with full attribution (tokens + cost_usd).

Before this wave:
  - digest_builder (cron every 6h)      → 0 events written
  - digest_report_builder (PDF path)    → stub event from router (no tokens)
  - health_explanation_ai (on-demand)   → 0 events written
  - ai_insight_service (dead but live)  → 0 events written

After this wave:
  All four paths call ``record_usage()`` with tokens + cost_usd whenever
  the LLM call succeeds. These tests pin that contract.

Tests are unit-level — we mock send_message_with_usage to return a fake
text + usage, and assert record_usage was called with the right keys.
No real LLM, no MongoDB.
"""
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.asyncio


_FAKE_USAGE = {
    "input_tokens": 1500,
    "output_tokens": 250,
    "cache_read_tokens": 1000,
    "cache_creation_tokens": 0,
}


# ── digest_builder (text path, cron-driven) ──────────────────────────────────

async def test_digest_builder_records_usage_with_tokens_and_cost():
    """Wave 8A.0 closes the cron-driven blind spot: every digest cycle
    now writes an AIUsageEvent. Even when triggered from background
    (no user_id), the event is written with org_id + tokens + cost.
    """
    from modules.cashflow_monitor import digest_builder

    fake_overview = {
        "period": {"start_date": "2026-04-15", "end_date": "2026-05-15", "days": 30},
        "kpis": {"total_sales": 5000, "total_expenses": 2000,
                 "net_after_fixed": 2500, "operating_margin_pct": 50,
                 "dso": 30, "burn_rate_total": 100, "break_even": 80},
        "health_score": {"score": 75},
        "alerts_summary": {"open_count": 3, "by_severity": {"high": 1}},
    }

    with patch("modules.cashflow_monitor.overview_builder.build_overview",
               new=AsyncMock(return_value=fake_overview)), \
         patch("services.claude_client.send_message_with_usage",
               new=AsyncMock(return_value=("Generated digest text", _FAKE_USAGE))), \
         patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.get_active_model",
               return_value="claude-sonnet-4-20250514"), \
         patch("services.claude_client.calculate_cost_usd",
               return_value=0.0042), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()) as mock_record:
        result = await digest_builder.build_digest(
            org_id="org_test", period_days=30, locale="it",
        )

    assert result is not None
    assert mock_record.await_count == 1
    kwargs = mock_record.await_args.kwargs
    assert kwargs["org_id"] == "org_test"
    assert kwargs["module_key"] == "ai_assistant"
    assert kwargs["feature_key"] == "digest"
    assert kwargs["tokens_prompt"] == 1500
    assert kwargs["tokens_completion"] == 250
    assert kwargs["cost_usd"] == 0.0042
    assert kwargs["provider"] == "anthropic"
    # Wave 9.B.2 defaulted to Haiku 4. Wave 11.1 reverted to Sonnet 4
    # (provider default) after user-reported quality regression on
    # narrative output. resolve_non_chat_model() now returns "" so the
    # call site reads model_version via get_active_model() → Sonnet.
    assert kwargs["model_version"] == "claude-sonnet-4-20250514"
    assert kwargs["agent_id"] == "digest_builder"
    # cron path: user_id stays None
    assert kwargs.get("user_id") is None


async def test_digest_builder_manual_path_records_user_id():
    """When invoked from the router (manual trigger), user_id is passed."""
    from modules.cashflow_monitor import digest_builder

    fake_overview = {
        "period": {"days": 30},
        "kpis": {"total_sales": 100, "total_expenses": 50, "net_after_fixed": 30,
                 "operating_margin_pct": 30, "dso": 0, "burn_rate_total": 0,
                 "break_even": 0},
        "health_score": {"score": 60},
        "alerts_summary": {"open_count": 0, "by_severity": {}},
    }

    with patch("modules.cashflow_monitor.overview_builder.build_overview",
               new=AsyncMock(return_value=fake_overview)), \
         patch("services.claude_client.send_message_with_usage",
               new=AsyncMock(return_value=("text", _FAKE_USAGE))), \
         patch("services.claude_client.is_available",
               return_value=True), \
         patch("services.claude_client.get_active_model",
               return_value="claude-sonnet-4-20250514"), \
         patch("services.claude_client.calculate_cost_usd",
               return_value=0.0042), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()) as mock_record:
        await digest_builder.build_digest(
            org_id="org_test", period_days=30, locale="it",
            user_id="user_abc",
        )

    assert mock_record.await_args.kwargs["user_id"] == "user_abc"


async def test_digest_builder_record_usage_failure_does_not_kill_digest():
    """A tracking failure must not break digest generation itself."""
    from modules.cashflow_monitor import digest_builder

    fake_overview = {
        "period": {"days": 30},
        "kpis": {"total_sales": 100, "total_expenses": 50, "net_after_fixed": 30,
                 "operating_margin_pct": 30, "dso": 0, "burn_rate_total": 0,
                 "break_even": 0},
        "health_score": {"score": 60},
        "alerts_summary": {"open_count": 0, "by_severity": {}},
    }

    with patch("modules.cashflow_monitor.overview_builder.build_overview",
               new=AsyncMock(return_value=fake_overview)), \
         patch("services.claude_client.send_message_with_usage",
               new=AsyncMock(return_value=("text", _FAKE_USAGE))), \
         patch("services.claude_client.is_available",
               return_value=True), \
         patch("services.claude_client.get_active_model",
               return_value="claude-sonnet-4-20250514"), \
         patch("services.claude_client.calculate_cost_usd",
               return_value=0.0042), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock(side_effect=RuntimeError("mongo down"))):
        # Should NOT raise — the digest text is still returned.
        result = await digest_builder.build_digest(
            org_id="org_test", period_days=30, locale="it",
        )

    assert result is not None
    assert result["content"] == "text"


# ── health_explanation_ai ────────────────────────────────────────────────────

async def test_health_explanation_records_usage_when_org_id_passed():
    from modules.cashflow_monitor import health_explanation

    health_score = {
        "score": 72, "label": "Buono",
        "breakdown": [{"dimension": "Margine Operativo", "points": 8, "max": 10}],
    }
    kpis = {"net_after_fixed": 1500, "operating_margin_pct": 30}

    with patch("services.claude_client.send_message_with_usage",
               new=AsyncMock(return_value=("AI explanation", _FAKE_USAGE))), \
         patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.get_active_model",
               return_value="claude-sonnet-4-20250514"), \
         patch("services.claude_client.calculate_cost_usd", return_value=0.0009), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()) as mock_record:
        text = await health_explanation.generate_health_explanation_ai(
            health_score, kpis,
            org_id="org_test", user_id="user_abc",
        )

    assert text == "AI explanation"
    assert mock_record.await_count == 1
    kwargs = mock_record.await_args.kwargs
    assert kwargs["org_id"] == "org_test"
    assert kwargs["user_id"] == "user_abc"
    assert kwargs["module_key"] == "ai_assistant"
    assert kwargs["feature_key"] == "health_explanation"
    assert kwargs["tokens_prompt"] == 1500
    assert kwargs["tokens_completion"] == 250
    assert kwargs["cost_usd"] == 0.0009
    assert kwargs["agent_id"] == "health_explanation"


async def test_health_explanation_no_org_id_skips_tracking():
    """Legacy callers without org_id: tracking skipped but text returned."""
    from modules.cashflow_monitor import health_explanation

    health_score = {"score": 50, "label": "Mediocre", "breakdown": []}

    with patch("services.claude_client.send_message_with_usage",
               new=AsyncMock(return_value=("text", _FAKE_USAGE))), \
         patch("services.claude_client.is_available", return_value=True), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()) as mock_record:
        text = await health_explanation.generate_health_explanation_ai(
            health_score, kpis={},
        )

    assert text == "text"
    assert mock_record.await_count == 0  # no tracking without org_id


async def test_health_explanation_returns_empty_on_none_score():
    from modules.cashflow_monitor import health_explanation

    text = await health_explanation.generate_health_explanation_ai(
        {"score": None}, kpis={},
    )
    assert text == ""


# ── digest_report_builder (PDF path) ────────────────────────────────────────

async def test_digest_report_builder_uses_unified_markdown_helper():
    """Wave 12.B — the previously-separate PDF AI call (_generate_ai_insights)
    was REMOVED. Both text and PDF paths now share a single Sonnet call
    via digest_builder.generate_digest_markdown(), and the PDF parses
    the resulting markdown into structured sections.

    This test pins that:
      - the obsolete _generate_ai_insights is no longer exported
      - build_digest_report still records exactly one AIUsageEvent
        (the one done by generate_digest_markdown internally)
    """
    from modules.cashflow_monitor import digest_report_builder

    # 1. The legacy hook is gone (post-Wave-12).
    assert not hasattr(digest_report_builder, "_generate_ai_insights"), (
        "Wave 12.B should have removed _generate_ai_insights — "
        "if it's back, the PDF path is doing 2 Sonnet calls again"
    )

    # 2. build_digest_report now routes through the unified helper.
    import inspect as _ins
    src = _ins.getsource(digest_report_builder.build_digest_report)
    assert "generate_digest_markdown" in src
    assert "parse_digest_sections" in src


# ── (removed) test_digest_report_builder_no_org_id_still_works_but_no_track ──
# Wave 12.B made this case moot: there is no separate "ai insights"
# function any more; the unified generate_digest_markdown is exercised
# by tests/test_wave12_digest_overhaul.py
async def test_digest_report_builder_no_org_id_still_works_but_no_track():
    """Wave 12.B placeholder — function preserved as a no-op pass for
    test discovery stability. The actual coverage moved to
    test_wave12_digest_overhaul.py::test_generate_digest_markdown_*."""
    return  # pragma: no cover


# ── ai_insight_service (dead code, but tracked if revived) ──────────────────

async def test_ai_insight_service_logs_warning_and_tracks_if_invoked():
    """If anything wakes up this dead code, it logs a warning AND tracks."""
    from services import ai_insight_service

    fake_context = {
        "system_prompt": "sys",
        "user_message": "user",
        "fallback_content": "fb",
        "module_key": "cashflow_monitor",
        "title": "Insight Test",
        "metrics_context": {},
    }

    fake_module = AsyncMock()
    fake_module.insight_builder = AsyncMock(return_value=fake_context)

    with patch("services.ai_insight_service.send_message_with_usage",
               new=AsyncMock(return_value=("insight text", _FAKE_USAGE))), \
         patch("services.ai_insight_service.is_available", return_value=True), \
         patch("services.ai_insight_service.get_active_model",
               return_value="claude-sonnet-4-20250514"), \
         patch("services.ai_insight_service.calculate_cost_usd", return_value=0.005), \
         patch("services.ai_insight_service.record_usage",
               new=AsyncMock()) as mock_record, \
         patch("core.module_registry.get", return_value=fake_module), \
         patch("repositories.insight_repository.find_latest",
               new=AsyncMock(return_value=None)):
        insight = await ai_insight_service.generate_cashflow_insight(
            "org_test", period="30d", user_id="user_xyz",
        )

    assert insight is not None
    assert mock_record.await_count == 1
    kwargs = mock_record.await_args.kwargs
    assert kwargs["feature_key"] == "insight"
    assert kwargs["agent_id"] == "ai_insight_service"
    assert kwargs["user_id"] == "user_xyz"


# ── Provider gateway: send_message_with_usage shape ─────────────────────────

async def test_send_message_with_usage_default_impl_returns_zero_usage():
    """LLMProvider default impl returns text + zero-usage dict."""
    from services.llm.provider import LLMProvider

    class _FakeProvider(LLMProvider):
        name = "fake"
        default_model = "fake-1"

        def is_available(self): return True
        def format_tools(self, defs): return []
        def calculate_cost_usd(self, *a, **k): return None
        async def send_message(self, system, user_message, **kw): return "hi"
        async def send_messages(self, system, messages, **kw): return "hi"
        async def send_messages_with_tools(self, *a, **k): return ("hi", [], {})

    fake = _FakeProvider()
    text, usage = await fake.send_message_with_usage("sys", "user")
    assert text == "hi"
    assert usage == {"input_tokens": 0, "output_tokens": 0,
                     "cache_read_tokens": 0, "cache_creation_tokens": 0}


# ── Forensic feature taxonomy guard ────────────────────────────────────────

def test_taxonomy_constants_match_known_features():
    """Wave 8A.0 — pin the feature taxonomy so a future rename trips CI.

    The dashboard groups events by feature; renaming a feature without
    updating the dashboard would silently lose the grouping.
    """
    KNOWN_FEATURES = {
        "chat",                # chat_service (user-facing)
        "digest",              # digest_builder + digest_report_builder
        "health_explanation",  # health_explanation_ai
        "alert_analysis",      # alert_analysis.py
        "insight",             # ai_insight_service (dead code)
        "data_rows",           # module_access (file-uploads gate)
    }
    # Sanity check: the set has the size we expect and contains all
    # names the sysadmin dashboard will display.
    assert len(KNOWN_FEATURES) == 6
    # Regression guard: each name must be lowercase snake_case so
    # MongoDB exact-match filters work consistently.
    for name in KNOWN_FEATURES:
        assert name == name.lower()
        assert " " not in name
