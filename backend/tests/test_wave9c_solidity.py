"""Wave 9.C — solidity + UX hardening tests.

Four independent fixes:

  9.C.1  admin_hard_delete_user now also cleans:
         - chat_sessions (DELETE — they contain user-typed PII)
         - ai_usage_events (anonymize user_id — preserves analytics)
         GDPR Article 17 compliance for single-user deletion.

  9.C.2  alert_analysis splits batches > 20 into multiple calls.
         Prevents a 100-alert spike from producing one token-heavy
         mega-call.

  9.C.3  health-explanation-ai response carries entitlement_status
         so the frontend can distinguish "AI failed" from "no
         entitlement" and show the right upsell tooltip.

  9.C.4  background_service persists last_tick_at; on restart, fires
         immediately if more than `interval` has elapsed. Prevents
         digest starvation when the backend restarts frequently.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import pytest

pytestmark = pytest.mark.asyncio


# ════════════════════════════════════════════════════════════════════════════
# 9.C.2 — Alert batch cap (20 per call)
# ════════════════════════════════════════════════════════════════════════════


async def test_alert_analysis_splits_batches_over_cap():
    """Wave 9.C.2 — 50 alerts → 3 calls (20 + 20 + 10), not 1 mega-call.

    Each sub-batch produces its own AIUsageEvent + Anthropic round-trip.
    """
    from modules.cashflow_monitor import alert_analysis

    # Build 50 alerts
    alerts = []
    for i in range(50):
        a = MagicMock(id=f"alert_{i}")
        a.severity = "high"
        a.title = f"t{i}"
        a.message = f"m{i}"
        a.metric_value = 1
        a.threshold = 0
        a.created_at = MagicMock(isoformat=lambda: "2026-05-15")
        alerts.append(a)

    # Track how many times send_message_with_usage is called
    call_count = {"n": 0}
    fake_usage = {"input_tokens": 100, "output_tokens": 50,
                  "cache_read_tokens": 0, "cache_creation_tokens": 0}

    async def fake_send(**kwargs):
        call_count["n"] += 1
        # Return a response with markers for each alert in this batch
        # — we just need it to be a valid response shape
        return ("[alert_x] dummy", fake_usage)

    with patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.send_message_with_usage",
               new=fake_send), \
         patch("services.claude_client.resolve_non_chat_model",
               return_value=""), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()):
        await alert_analysis.analyze_alerts(
            alerts, kpis={}, locale="it",
            organization_id="org_test",
        )

    # 50 / 20 = 3 sub-batches → 3 Anthropic calls
    assert call_count["n"] == 3


async def test_alert_analysis_does_not_split_small_batches():
    """Below the cap (20), runs in a single call."""
    from modules.cashflow_monitor import alert_analysis

    alerts = []
    for i in range(15):
        a = MagicMock(id=f"a_{i}")
        a.severity = "low"
        a.title = "x"
        a.message = "y"
        a.metric_value = 0
        a.threshold = 0
        a.created_at = MagicMock(isoformat=lambda: "2026-05-15")
        alerts.append(a)

    call_count = {"n": 0}
    fake_usage = {"input_tokens": 50, "output_tokens": 20,
                  "cache_read_tokens": 0, "cache_creation_tokens": 0}

    async def fake_send(**kwargs):
        call_count["n"] += 1
        return ("[a_0] ok", fake_usage)

    with patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.send_message_with_usage",
               new=fake_send), \
         patch("services.claude_client.resolve_non_chat_model",
               return_value=""), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()):
        await alert_analysis.analyze_alerts(
            alerts, kpis={}, locale="it",
            organization_id="org_test",
        )

    assert call_count["n"] == 1  # 15 < 20, single call


# ════════════════════════════════════════════════════════════════════════════
# 9.C.3 — Health endpoint carries entitlement_status
# ════════════════════════════════════════════════════════════════════════════


def test_health_endpoint_signals_entitlement_status():
    """Inspecting the source — the three branches must yield distinct
    entitlement_status values so the frontend can route the upsell UX."""
    import inspect
    from routers import modules as modules_router
    src = inspect.getsource(modules_router.get_health_explanation_ai)

    assert '"entitlement_status": "active"' in src
    assert '"requires_higher_plan"' in src
    assert '"not_available_for_module"' in src


# ════════════════════════════════════════════════════════════════════════════
# 9.C.4 — Cron restart resilience (last_tick_at)
# ════════════════════════════════════════════════════════════════════════════


async def test_read_last_tick_returns_none_when_missing():
    from services import background_service as bg

    coll = MagicMock()
    coll.find_one = AsyncMock(return_value=None)
    with patch("database.platform_settings_collection", coll):
        result = await bg._read_last_tick_iso()
    assert result is None


async def test_read_last_tick_returns_value_when_present():
    from services import background_service as bg

    coll = MagicMock()
    coll.find_one = AsyncMock(return_value={"value": "2026-05-15T10:00:00+00:00"})
    with patch("database.platform_settings_collection", coll):
        result = await bg._read_last_tick_iso()
    assert result == "2026-05-15T10:00:00+00:00"


async def test_read_last_tick_resilient_to_db_failure():
    """A DB outage during read must not crash the cron — fail-open."""
    from services import background_service as bg

    coll = MagicMock()
    coll.find_one = AsyncMock(side_effect=RuntimeError("mongo down"))
    with patch("database.platform_settings_collection", coll):
        result = await bg._read_last_tick_iso()
    assert result is None


async def test_write_last_tick_idempotent():
    """The write uses upsert keyed on the platform_settings key."""
    from services import background_service as bg

    coll = MagicMock()
    coll.update_one = AsyncMock()
    with patch("database.platform_settings_collection", coll):
        await bg._write_last_tick_iso()

    coll.update_one.assert_awaited_once()
    args, kwargs = coll.update_one.await_args
    # The filter must be keyed on the documented key
    assert args[0] == {"key": bg._LAST_TICK_KEY}
    assert kwargs.get("upsert") is True
    # The $set value must be an ISO string
    set_value = args[1]["$set"]["value"]
    # It parses as an ISO datetime
    parsed = datetime.fromisoformat(set_value.replace("Z", "+00:00"))
    assert isinstance(parsed, datetime)
