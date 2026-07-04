"""Wave 10.B — cost optimization & dashboard observability.

Seven fixes targeting the cost-side gaps that survived Wave 10.A:

  10.B.1  System prompt split into stable (cache_control:ephemeral) +
          dynamic (no cache_control) blocks. The forensic audit measured
          cache hit ratio at 12.3% — most of the gap came from
          period_context being concatenated into a single 'system' string
          on every call. Expected: ~60% hit ratio after the split.

  10.B.2  Atomic budget counter (ai_budget_counters collection) replaces
          the per-call compute_period_spend aggregation. The race window
          on the chat budget check shrinks from ~10-50 ms (Mongo agg) to
          <1 ms (counter $inc), AND every event $incs the counter so the
          guard reads a near-realtime value.

  10.B.3  Provider marks itself "degraded" for 60s after a call exhausts
          ≥2 retries. While degraded, max_retries drops to 1 — bounding
          the retry-storm cost amplification during an Anthropic outage.

  10.B.4  Sparse TTL index on ai_usage_events.expires_at. Events that
          opt in to expires_at auto-purge after the configured retention.

  10.B.5  Drop 3 legacy redundant indices that cost write throughput.

  10.B.6  Provider returns latency_ms in the usage dict; all four AI
          surfaces (chat, digest, health_explanation, alert_analysis)
          plumb it into record_usage so the governance dashboard can
          surface a real "AI call latency" KPI.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ════════════════════════════════════════════════════════════════════════════
# 10.B.1 — system prompt cache split
# ════════════════════════════════════════════════════════════════════════════


def test_system_with_cache_accepts_list_passthrough():
    """When caller passes a pre-formatted list, _system_with_cache
    returns it untouched (cache_control markers preserved)."""
    from services.llm.providers.anthropic import _system_with_cache, _PROMPT_CACHE_ENABLED
    blocks = [
        {"type": "text", "text": "stable", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "dynamic"},
    ]
    out = _system_with_cache(blocks)
    if _PROMPT_CACHE_ENABLED:
        assert out == blocks  # passthrough
    else:
        # When cache disabled, markers are stripped but structure preserved.
        assert all("cache_control" not in b for b in out)
        assert [b["text"] for b in out] == ["stable", "dynamic"]


def test_system_with_cache_wraps_string_as_single_cached_block():
    """Legacy string input becomes a 1-block list with cache_control."""
    from services.llm.providers.anthropic import _system_with_cache, _PROMPT_CACHE_ENABLED
    out = _system_with_cache("stable prompt")
    if _PROMPT_CACHE_ENABLED:
        assert isinstance(out, list)
        assert len(out) == 1
        assert out[0]["text"] == "stable prompt"
        assert out[0].get("cache_control", {}).get("type") == "ephemeral"
    else:
        assert out == "stable prompt"


def test_chat_service_builds_two_block_system_when_dynamic_present():
    """Static introspection: chat_service.chat must construct a list
    payload when proactive or period context exists, so the cache
    marker stays only on the stable prefix."""
    import inspect
    from services import chat_service
    src = inspect.getsource(chat_service.chat)
    # The split flag and cache_control on the stable block must both
    # appear in the assembly logic.
    assert "system_dynamic_parts" in src
    assert "cache_control" in src
    assert "system_stable" in src


# ════════════════════════════════════════════════════════════════════════════
# 10.B.2 — atomic budget counter
# ════════════════════════════════════════════════════════════════════════════


async def test_budget_counter_increment_returns_cumulative_cents():
    """increment() uses findOneAndUpdate with $inc and upsert."""
    from repositories import budget_counter_repository as bcr

    fake_coll = MagicMock()
    fake_coll.find_one_and_update = AsyncMock(return_value={"cumulative_cents": 250})
    fake_db = MagicMock()
    fake_db.ai_budget_counters = fake_coll

    with patch("database.db", fake_db):
        result = await bcr.increment(
            scope="org", scope_id="org_a",
            period="monthly", period_start="2026-05-01",
            cost_usd=2.50,
        )
    assert result == 250
    # Verify the $inc payload converted 2.50 USD → 250 cents
    args, kwargs = fake_coll.find_one_and_update.await_args
    inc_payload = args[1]["$inc"]
    assert inc_payload["cumulative_cents"] == 250
    assert inc_payload["event_count"] == 1


async def test_budget_counter_skips_zero_cost():
    """No-op when cost_usd is 0 / None — keeps the cron data_rows events
    (which are non-billable) from polluting the counter."""
    from repositories import budget_counter_repository as bcr

    fake_coll = MagicMock()
    fake_coll.find_one_and_update = AsyncMock()
    with patch("database.db", MagicMock(ai_budget_counters=fake_coll)):
        r1 = await bcr.increment(
            scope="org", scope_id="x", period="daily",
            period_start="2026-05-15", cost_usd=0,
        )
        r2 = await bcr.increment(
            scope="org", scope_id="x", period="daily",
            period_start="2026-05-15", cost_usd=None,
        )
    assert r1 is None and r2 is None
    fake_coll.find_one_and_update.assert_not_called()


async def test_budget_counter_read_cents_returns_none_when_missing():
    """First call before any seed returns None, signaling the caller to
    fall back to aggregation."""
    from repositories import budget_counter_repository as bcr

    fake_coll = MagicMock()
    fake_coll.find_one = AsyncMock(return_value=None)
    with patch("database.db", MagicMock(ai_budget_counters=fake_coll)):
        result = await bcr.read_cents(
            scope="org", scope_id="x", period="monthly",
            period_start="2026-05-01",
        )
    assert result is None


async def test_budget_counter_seed_uses_setOnInsert():
    """seed_from_aggregation uses $setOnInsert so concurrent seeders
    don't double-count."""
    from repositories import budget_counter_repository as bcr

    fake_coll = MagicMock()
    fake_coll.update_one = AsyncMock()
    with patch("database.db", MagicMock(ai_budget_counters=fake_coll)):
        await bcr.seed_from_aggregation(
            scope="org", scope_id="x", period="monthly",
            period_start="2026-05-01", aggregated_usd=7.25,
        )
    args, kwargs = fake_coll.update_one.await_args
    assert kwargs.get("upsert") is True
    set_on_insert = args[1]["$setOnInsert"]
    assert set_on_insert["cumulative_cents"] == 725


async def test_budget_guard_uses_counter_fast_path():
    """check_budget_or_raise must read the counter before falling back
    to aggregation. We verify by mocking the counter to return a value
    above the limit — the call MUST raise BudgetExceededError, AND
    compute_period_spend must NOT be invoked."""
    from services.llm.budget_guard import check_budget_or_raise, BudgetExceededError

    budgets = [{
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly",
        "soft_limit_usd": 5.0, "hard_limit_usd": 10.0,
        "hard_action": "block", "is_active": True,
    }]

    agg_calls = {"n": 0}

    async def fake_agg(**kw):
        agg_calls["n"] += 1
        return 0.0  # if called, would say "under budget"

    with patch(
        "services.llm.budget_guard._read_kill_switch",
        new=AsyncMock(return_value={
            "ai_enabled": True, "ai_throttle_pct": 0,
            "kill_reason": None, "activated_at": None, "activated_by": None,
        }),
    ), patch(
        "repositories.ai_budget_repository.find_applicable_budgets",
        new=AsyncMock(return_value=budgets),
    ), patch(
        "repositories.budget_counter_repository.read_cents",
        new=AsyncMock(return_value=1000),  # 1000 cents = $10 = at hard limit
    ), patch(
        "repositories.ai_budget_repository.compute_period_spend",
        new=fake_agg,
    ):
        with pytest.raises(BudgetExceededError):
            await check_budget_or_raise(organization_id="org_a")

    assert agg_calls["n"] == 0, (
        "compute_period_spend MUST NOT be called when counter is populated "
        "(otherwise we negate the whole point of the fast path)"
    )


async def test_budget_guard_falls_back_to_aggregation_on_counter_miss():
    """When the counter is None, the guard must fall back to aggregation
    AND seed the counter for next time."""
    from services.llm.budget_guard import check_budget_or_raise

    budgets = [{
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly",
        "soft_limit_usd": 5.0, "hard_limit_usd": 10.0,
        "hard_action": "block", "is_active": True,
    }]
    seed_calls = []

    async def fake_seed(**kw):
        seed_calls.append(kw)

    with patch(
        "services.llm.budget_guard._read_kill_switch",
        new=AsyncMock(return_value={
            "ai_enabled": True, "ai_throttle_pct": 0,
            "kill_reason": None, "activated_at": None, "activated_by": None,
        }),
    ), patch(
        "repositories.ai_budget_repository.find_applicable_budgets",
        new=AsyncMock(return_value=budgets),
    ), patch(
        "repositories.budget_counter_repository.read_cents",
        new=AsyncMock(return_value=None),  # miss
    ), patch(
        "repositories.ai_budget_repository.compute_period_spend",
        new=AsyncMock(return_value=3.0),  # under budget
    ), patch(
        "repositories.budget_counter_repository.seed_from_aggregation",
        new=fake_seed,
    ):
        # Should NOT raise (3 < 10) AND should call seed_from_aggregation.
        await check_budget_or_raise(organization_id="org_a")

    assert len(seed_calls) == 1
    assert seed_calls[0]["aggregated_usd"] == 3.0


# ════════════════════════════════════════════════════════════════════════════
# 10.B.3 — degraded mark after consecutive retries
# ════════════════════════════════════════════════════════════════════════════


def test_degraded_helpers_exist():
    """Introspection: the degraded-mark helpers must be exported by the
    anthropic module so a future test or monitoring tool can poll them."""
    from services.llm.providers import anthropic
    assert hasattr(anthropic, "_is_degraded")
    assert hasattr(anthropic, "_mark_degraded")
    assert hasattr(anthropic, "_DEGRADED_THRESHOLD_RETRIES")
    assert hasattr(anthropic, "_DEGRADED_WINDOW_SECONDS")


def test_retry_with_backoff_respects_degraded_clamp():
    """When _is_degraded() returns True, max_retries is clamped to 1."""
    import inspect
    from services.llm.providers import anthropic
    src = inspect.getsource(anthropic._retry_with_backoff)
    # The clamp line is the key piece — verify the logic is present.
    assert "_is_degraded()" in src
    assert "min(max_retries, 1)" in src


# ════════════════════════════════════════════════════════════════════════════
# 10.B.4 / 10.B.5 — TTL + drop legacy indices
# ════════════════════════════════════════════════════════════════════════════


def test_setup_indexes_creates_ttl_and_drops_legacy():
    """Introspection: setup_indexes must (a) create the TTL index on
    expires_at, (b) drop the 3 legacy redundant indices identified by
    the Wave 10 audit."""
    import inspect
    from repositories import usage_repository
    src = inspect.getsource(usage_repository.setup_indexes)
    # TTL index
    assert "expires_at" in src
    assert "expireAfterSeconds=0" in src or "expireAfterSeconds = 0" in src
    # Legacy indices to drop
    assert "organization_id_1_feature_1_created_at_-1" in src
    assert "organization_id_1_module_key_1_feature_1_created_at_-1" in src
    assert "drop_index" in src


# ════════════════════════════════════════════════════════════════════════════
# 10.B.6 — latency_ms wired everywhere
# ════════════════════════════════════════════════════════════════════════════


def test_provider_send_message_with_usage_returns_latency_ms():
    """Introspection: provider must measure time around the SDK call
    and emit usage['latency_ms']."""
    import inspect
    from services.llm.providers import anthropic
    src = inspect.getsource(anthropic.AnthropicProvider.send_message_with_usage)
    assert "latency_ms" in src
    assert "monotonic()" in src


def test_provider_agentic_round_returns_latency_ms():
    """Same check for the multi-turn path — every round-trip must carry
    its own latency_ms so chat_service can write it per-AIUsageEvent."""
    import inspect
    from services.llm.providers import anthropic
    src = inspect.getsource(anthropic.AnthropicProvider.send_messages_with_tools)
    # The per-round timer and the assignment into round_usage must both exist.
    assert "_t0_round" in src
    assert "_round_elapsed_ms" in src
    assert 'round_usage["latency_ms"]' in src or "round_usage.get(\"latency_ms\")" in src \
           or "\"latency_ms\": _round_elapsed_ms" in src


def test_chat_service_plumbs_latency_into_record_usage():
    import inspect
    from services import chat_service
    src = inspect.getsource(chat_service.chat)
    assert 'latency_ms=round_usage.get("latency_ms")' in src \
        or "latency_ms=round_usage.get('latency_ms')" in src


def test_health_explanation_plumbs_latency():
    import inspect
    from modules.cashflow_monitor import health_explanation
    src = inspect.getsource(health_explanation.generate_health_explanation_ai)
    assert "latency_ms=usage.get" in src


def test_alert_analysis_plumbs_latency():
    import inspect
    from modules.cashflow_monitor import alert_analysis
    src = inspect.getsource(alert_analysis.analyze_alerts)
    assert "latency_ms=usage.get" in src


def test_digest_builder_plumbs_latency():
    import inspect
    from modules.cashflow_monitor import digest_builder
    src = inspect.getsource(digest_builder)
    assert "latency_ms=usage.get" in src
