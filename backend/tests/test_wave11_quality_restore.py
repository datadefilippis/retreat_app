"""Wave 11 — restore Sonnet for non-chat AI + reduce alert cron to daily.

Wave 9.B.2 had switched digest / health_explanation / alert_analysis to
Haiku 4 to save ~75% per call. After 3 weeks the user reported a
significant quality regression on narrative output: "the digest used to
be a real report with explanation, now it's just 4 numbers."

The Wave 11 audit (chat history 2026-05) concluded:
  - Haiku is structurally weaker at narrative synthesis / cause-effect
    reasoning. The prompts (designed for Sonnet) ask for reasoning that
    Haiku can't deliver.
  - The cost trade-off of reverting to Sonnet is small at current scale
    (~$11/mo at 50 org, ~$110/mo at 500 org).
  - Reducing the alert cron from 6h → 24h cuts AI call frequency by 4×,
    offsetting the 3.75× Sonnet price markup. Net cost flat.
  - Entitlement gate at services/alert_service.py:103-112 already
    blocks free/starter orgs from the AI call (Option 2 in the audit) —
    no extra filter needed.

This test pack pins the new defaults so a future contributor can't
silently flip them back to Haiku without seeing a failing test.
"""
import os

import pytest


# ════════════════════════════════════════════════════════════════════════════
# 11.1 — non-chat default = provider default (Sonnet)
# ════════════════════════════════════════════════════════════════════════════


def test_resolve_non_chat_model_returns_empty_when_env_unset():
    """Wave 11.1 — unset env returns empty string (= provider default =
    Sonnet 4). Was 'claude-haiku-4-20250514' pre-Wave-11.1."""
    from services.claude_client import resolve_non_chat_model

    _old = os.environ.pop("LLM_NON_CHAT_MODEL", None)
    try:
        assert resolve_non_chat_model() == ""
    finally:
        if _old is not None:
            os.environ["LLM_NON_CHAT_MODEL"] = _old


def test_resolve_non_chat_model_haiku_still_available_via_env():
    """Wave 11.1 — the env escape hatch must still allow forcing Haiku
    explicitly (e.g. for high-volume / low-quality-need surfaces in the
    future, or for emergency cost cutting)."""
    from services.claude_client import resolve_non_chat_model

    _old = os.environ.get("LLM_NON_CHAT_MODEL")
    try:
        os.environ["LLM_NON_CHAT_MODEL"] = "claude-haiku-4-20250514"
        assert resolve_non_chat_model() == "claude-haiku-4-20250514"
    finally:
        if _old is None:
            os.environ.pop("LLM_NON_CHAT_MODEL", None)
        else:
            os.environ["LLM_NON_CHAT_MODEL"] = _old


def test_resolve_non_chat_model_explicit_default_keyword_still_works():
    """Backward compat: ``LLM_NON_CHAT_MODEL=default`` keeps returning ""."""
    from services.claude_client import resolve_non_chat_model

    _old = os.environ.get("LLM_NON_CHAT_MODEL")
    try:
        os.environ["LLM_NON_CHAT_MODEL"] = "default"
        assert resolve_non_chat_model() == ""
        os.environ["LLM_NON_CHAT_MODEL"] = "provider"
        assert resolve_non_chat_model() == ""
    finally:
        if _old is None:
            os.environ.pop("LLM_NON_CHAT_MODEL", None)
        else:
            os.environ["LLM_NON_CHAT_MODEL"] = _old


# ════════════════════════════════════════════════════════════════════════════
# 11.2 — alert cron 6h → 24h
# ════════════════════════════════════════════════════════════════════════════


def test_alert_cron_default_interval_is_24_hours():
    """Wave 11.2 — _ALERT_INTERVAL_HOURS default flipped from 6 to 24.
    The module reads this at import-time from the env, so to test the
    default we re-import with the env clean.

    This test pins the default so a regression toward 6h gets caught.
    """
    # Strip the env var, reload the module to pick up the static default.
    import importlib
    import services.background_service as bg

    _old = os.environ.pop("BACKGROUND_ALERT_INTERVAL_HOURS", None)
    try:
        importlib.reload(bg)
        assert bg._ALERT_INTERVAL_HOURS == 24.0, (
            f"Wave 11.2 default must be 24h; got {bg._ALERT_INTERVAL_HOURS}. "
            "Reducing the alert cron to once-a-day is what makes the "
            "Sonnet upgrade cost-neutral at current scale."
        )
    finally:
        if _old is not None:
            os.environ["BACKGROUND_ALERT_INTERVAL_HOURS"] = _old
        importlib.reload(bg)


def test_alert_cron_env_override_still_works():
    """Env override BACKGROUND_ALERT_INTERVAL_HOURS still wins."""
    import importlib
    import services.background_service as bg

    _old = os.environ.get("BACKGROUND_ALERT_INTERVAL_HOURS")
    try:
        os.environ["BACKGROUND_ALERT_INTERVAL_HOURS"] = "12"
        importlib.reload(bg)
        assert bg._ALERT_INTERVAL_HOURS == 12.0
    finally:
        if _old is None:
            os.environ.pop("BACKGROUND_ALERT_INTERVAL_HOURS", None)
        else:
            os.environ["BACKGROUND_ALERT_INTERVAL_HOURS"] = _old
        importlib.reload(bg)


# ════════════════════════════════════════════════════════════════════════════
# 11.3 — entitlement gate already in place in alert_service.py
# ════════════════════════════════════════════════════════════════════════════


def test_alert_service_still_gates_ai_analysis_by_entitlement():
    """Wave 11 chose Option 2 (soft filter): the cron iterates all orgs,
    but the AI portion is blocked for non-entitled orgs by the existing
    check_module_access call in alert_service.py.

    This test pins that the gate is still in the source (would have
    caught its accidental removal during the Wave 11 work, and remains
    a safety net for the future)."""
    import inspect
    from services import alert_service

    src = inspect.getsource(alert_service.generate_and_save_alerts)
    # The gate call must still be there.
    assert "check_module_access" in src
    assert '"alert_analysis"' in src
    # The continue branch on entitlement failure must still be there
    # (otherwise non-entitled orgs would slip through).
    assert "continue" in src


# ════════════════════════════════════════════════════════════════════════════
# 11.4 — wiring smoke test on the four non-chat surfaces
# ════════════════════════════════════════════════════════════════════════════


def test_all_non_chat_surfaces_use_resolve_non_chat_model():
    """Pin that the 3 non-chat AI surfaces still funnel through the
    single ``resolve_non_chat_model()`` helper. If any of them gets a
    hardcoded model_version in the future, this test fails and the
    contributor sees that Wave 11.1's central revert no longer covers
    that surface.

    Wave 12.B note: digest_builder.build_digest no longer holds the AI
    call inline — it was extracted into ``generate_digest_markdown``
    so the PDF path can reuse it. Both paths still route through
    resolve_non_chat_model() because that helper is invoked in
    ``generate_digest_markdown``. The Wave 12 test verifies the
    extracted helper is the right target.

    Wave 12.B also removed ``_generate_ai_insights`` entirely (it was
    the 2nd Sonnet call for the PDF path, now unified). That surface
    is therefore dropped from the list.
    """
    import inspect
    surfaces = [
        ("modules.cashflow_monitor.digest_builder", "generate_digest_markdown"),
        ("modules.cashflow_monitor.health_explanation", "generate_health_explanation_ai"),
        ("modules.cashflow_monitor.alert_analysis", "analyze_alerts"),
    ]
    import importlib
    for mod_path, fn_name in surfaces:
        mod = importlib.import_module(mod_path)
        fn = getattr(mod, fn_name)
        src = inspect.getsource(fn)
        assert "resolve_non_chat_model" in src, (
            f"{mod_path}.{fn_name} no longer routes through "
            "resolve_non_chat_model() — Wave 11.1 default revert does not "
            "cover this surface anymore. Add the helper back or update "
            "the test list."
        )
