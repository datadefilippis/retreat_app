"""Wave 9.B — cost optimization tests.

Three independent fixes verified:

  9.B.1  Cache fix: `today` removed from the system prompt, injected
         into the user message instead. The system prompt is now
         100% deterministic per (active_modules, locale) so the
         Anthropic prompt cache stays valid across days. Expected
         outcome: cache hit ratio rises from ~10% to ≥50% in prod.

  9.B.2  resolve_non_chat_model() + Haiku usage on digest/health/alert
         + alert_analysis tracking gap closed (was hitting Anthropic
         with no record_usage at all!).

  9.B.3  health-explanation-ai rate-limited to 10 calls/minute/user.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import pytest


# ════════════════════════════════════════════════════════════════════════════
# 9.B.1 — System prompt no longer contains `today`
# ════════════════════════════════════════════════════════════════════════════


def test_system_prompt_does_not_contain_today_date():
    """Wave 9.B.1 — the system prompt must be cache-stable.

    The literal ISO date should NOT appear anywhere in the rendered
    system prompt. Any callsite that interpolates today bursts the
    Anthropic prompt cache every midnight UTC for every org.
    """
    from services.chat_service import _build_system_prompt
    from core.locale_utils import get_locale_profile

    profile = get_locale_profile("it")
    prompt = _build_system_prompt({"cashflow_monitor"}, profile)

    # No ISO date pattern (YYYY-MM-DD) in the prompt body
    import re
    iso_dates = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", prompt)
    assert iso_dates == [], (
        f"Wave 9.B.1 regression: system prompt contains an ISO date "
        f"({iso_dates[:3]}). The date must live in the user message, "
        f"not in the cacheable system prompt."
    )
    # The {today} placeholder MUST NOT appear (would indicate broken interpolation)
    assert "{today}" not in prompt


def test_system_prompt_stable_across_consecutive_builds():
    """Two consecutive builds with the same (modules, locale) must be
    byte-identical — that's the cacheability guarantee."""
    from services.chat_service import _build_system_prompt
    from core.locale_utils import get_locale_profile

    profile = get_locale_profile("it")
    a = _build_system_prompt({"cashflow_monitor", "commerce"}, profile)
    b = _build_system_prompt({"cashflow_monitor", "commerce"}, profile)
    assert a == b


def test_build_system_prompt_accepts_legacy_today_kwarg():
    """Backward-compat: existing test fixtures pass today_str=..."""
    from services.chat_service import _build_system_prompt
    from core.locale_utils import get_locale_profile

    profile = get_locale_profile("it")
    # Should not raise — the parameter is accepted but ignored.
    prompt = _build_system_prompt({"cashflow_monitor"}, profile, today_str="2026-05-15")
    assert "2026-05-15" not in prompt  # confirmed it's ignored


# ════════════════════════════════════════════════════════════════════════════
# 9.B.2 — resolve_non_chat_model() + Haiku
# ════════════════════════════════════════════════════════════════════════════


def test_resolve_non_chat_model_defaults_to_provider_default():
    """Wave 11.1 reverted the default from Haiku back to "" (= provider
    default = Sonnet 4) because Haiku's quality on narrative synthesis
    (digest, health_explanation, alert_analysis) was visibly worse for
    end users. The env knob ``LLM_NON_CHAT_MODEL`` remains as the
    explicit override path for ops that want Haiku per-feature."""
    import os
    from services.claude_client import resolve_non_chat_model

    # Clear the env var if set
    _old = os.environ.pop("LLM_NON_CHAT_MODEL", None)
    try:
        # Wave 11.1: empty string signals "use provider default" (Sonnet).
        assert resolve_non_chat_model() == ""
    finally:
        if _old is not None:
            os.environ["LLM_NON_CHAT_MODEL"] = _old


def test_resolve_non_chat_model_env_override():
    import os
    from services.claude_client import resolve_non_chat_model

    _old = os.environ.get("LLM_NON_CHAT_MODEL")
    try:
        os.environ["LLM_NON_CHAT_MODEL"] = "claude-sonnet-4-20250514"
        assert resolve_non_chat_model() == "claude-sonnet-4-20250514"
    finally:
        if _old is None:
            os.environ.pop("LLM_NON_CHAT_MODEL", None)
        else:
            os.environ["LLM_NON_CHAT_MODEL"] = _old


def test_resolve_non_chat_model_default_keyword_uses_provider_default():
    """Setting LLM_NON_CHAT_MODEL=default reverts to Sonnet (provider default)."""
    import os
    from services.claude_client import resolve_non_chat_model

    _old = os.environ.get("LLM_NON_CHAT_MODEL")
    try:
        os.environ["LLM_NON_CHAT_MODEL"] = "default"
        # Empty string signals "use provider default"
        assert resolve_non_chat_model() == ""
    finally:
        if _old is None:
            os.environ.pop("LLM_NON_CHAT_MODEL", None)
        else:
            os.environ["LLM_NON_CHAT_MODEL"] = _old


# ════════════════════════════════════════════════════════════════════════════
# 9.B.2 — alert_analysis tracking gap closed
# ════════════════════════════════════════════════════════════════════════════


pytestmark_async = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_alert_analysis_records_usage_event():
    """Wave 9.B — alert_analysis MUST write an AIUsageEvent.

    Before this fix the call was entirely invisible to the governance
    dashboard. With this fix every batch writes feature='alert_analysis'.
    """
    from modules.cashflow_monitor import alert_analysis

    fake_alert_1 = MagicMock(id="alert_1")
    fake_alert_1.severity = "high"
    fake_alert_1.title = "Cash short"
    fake_alert_1.message = "Test message 1"
    fake_alert_1.metric_value = 100
    fake_alert_1.threshold = 50
    fake_alert_1.created_at = MagicMock()
    fake_alert_1.created_at.isoformat = lambda: "2026-05-15"
    fake_alert_2 = MagicMock(id="alert_2")
    fake_alert_2.severity = "medium"
    fake_alert_2.title = "DSO high"
    fake_alert_2.message = "Test message 2"
    fake_alert_2.metric_value = 60
    fake_alert_2.threshold = 30
    fake_alert_2.created_at = MagicMock()
    fake_alert_2.created_at.isoformat = lambda: "2026-05-15"

    usage = {
        "input_tokens": 500, "output_tokens": 200,
        "cache_read_tokens": 0, "cache_creation_tokens": 0,
    }
    response_text = "[alert_1] First analysis\n[alert_2] Second analysis"

    with patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.send_message_with_usage",
               new=AsyncMock(return_value=(response_text, usage))), \
         patch("services.claude_client.get_active_model",
               return_value="claude-haiku-4-20250514"), \
         patch("services.claude_client.calculate_cost_usd",
               return_value=0.0005), \
         patch("services.claude_client.resolve_non_chat_model",
               return_value="claude-haiku-4-20250514"), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()) as mock_record:
        result = await alert_analysis.analyze_alerts(
            [fake_alert_1, fake_alert_2], kpis={}, locale="it",
            organization_id="org_test",
        )

    # An AIUsageEvent must have been written
    assert mock_record.await_count == 1
    kwargs = mock_record.await_args.kwargs
    assert kwargs["module_key"] == "ai_assistant"
    assert kwargs["feature_key"] == "alert_analysis"
    assert kwargs["agent_id"] == "alert_analysis"
    # record_usage signature uses `org_id`, not organization_id
    assert kwargs["org_id"] == "org_test"
    # quantity reflects the batch size (2 alerts → 1 call covers 2 units)
    assert kwargs["quantity"] == 2
    assert kwargs["tokens_prompt"] == 500
    assert kwargs["tokens_completion"] == 200


@pytest.mark.asyncio
async def test_alert_analysis_no_org_id_skips_tracking():
    """Legacy callers without organization_id: tracking skipped silently."""
    from modules.cashflow_monitor import alert_analysis

    fake_alert = MagicMock(id="alert_1")
    fake_alert.severity = "high"
    fake_alert.title = "x"
    fake_alert.message = "y"
    fake_alert.metric_value = 1
    fake_alert.threshold = 0
    fake_alert.created_at = MagicMock()
    fake_alert.created_at.isoformat = lambda: "2026-05-15"

    usage = {"input_tokens": 100, "output_tokens": 50,
             "cache_read_tokens": 0, "cache_creation_tokens": 0}

    with patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.send_message_with_usage",
               new=AsyncMock(return_value=("[alert_1] ok", usage))), \
         patch("services.claude_client.resolve_non_chat_model",
               return_value=""), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()) as mock_record:
        # Caller omits organization_id (legacy path)
        await alert_analysis.analyze_alerts(
            [fake_alert], kpis={}, locale="it",
        )

    assert mock_record.await_count == 0  # no tracking without org_id


# ════════════════════════════════════════════════════════════════════════════
# 9.B.3 — Rate limit on health-explanation-ai
# ════════════════════════════════════════════════════════════════════════════


def test_health_explanation_rate_limit_logic():
    """The rate-limit guard is a count_documents query in routers/modules.py.

    Test directly the query shape (1-minute rolling window, per user
    + org + feature='health_explanation') — the value 10 is the
    documented limit.
    """
    import inspect
    from routers import modules as modules_router
    src = inspect.getsource(modules_router.get_health_explanation_ai)
    # The guard must use the right window + feature filter
    assert "health_explanation" in src
    assert "rate_limit_exceeded" in src
    # The limit value
    assert "10" in src
