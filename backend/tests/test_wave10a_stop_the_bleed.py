"""Wave 10.A — stop-the-bleed fixes.

Eight fixes that close the gaps surfaced by the Wave 10 deep audit:

  10.A.1  alert_analysis now invokes check_budget_or_raise before the
          Anthropic call (it was the only AI surface bypassing
          governance — kill switch + budget were not honoured).

  10.A.3  budget_guard.py docstring updated to reflect reality (per-
          call-site invocation, NOT inside the provider as the old
          docstring claimed).

  10.A.4  Fail-open emergency cap: a Mongo outage no longer means
          unbounded Anthropic spend. After _FAIL_OPEN_LIMIT (=100)
          fail-open events in a 10-minute window, the guard converts
          subsequent fail-opens to fail-CLOSED (AIDisabledError).

  10.A.5  Agentic loop convergence guards:
          - same (tool_name, tool_input) called twice in a row →
            force end_turn (synthetic tool_result with hint)
          - >5 parallel tool_use blocks in one round → cap, excess
            blocks get a marker

  10.A.6  health-explanation rate limit TOCTOU fix: replaces the
          count_documents + later-record_usage pattern (race-prone)
          with an atomic findOneAndUpdate counter in the new
          services.rate_limit module.

  10.A.7  ChatRequest.message has a Pydantic max_length=10_000 so a
          single API call can't ship a multi-MB paste through to the
          worker memory.

  10.A.8  Default AI budgets seeded at startup if ai_budgets is empty
          (idempotent — never overwrites operator changes).
"""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import pytest

pytestmark = pytest.mark.asyncio


# ════════════════════════════════════════════════════════════════════════════
# 10.A.1 — alert_analysis invokes governance pre-flight
# ════════════════════════════════════════════════════════════════════════════


async def test_alert_analysis_invokes_budget_guard():
    """When organization_id is passed, alert_analysis MUST call
    check_budget_or_raise before send_message_with_usage."""
    from modules.cashflow_monitor import alert_analysis

    alerts = []
    for i in range(3):
        a = MagicMock(id=f"alert_{i}")
        a.severity = "high"
        a.title = f"t{i}"
        a.message = f"m{i}"
        a.metric_value = 1
        a.threshold = 0
        a.created_at = MagicMock(isoformat=lambda: "2026-05-15")
        alerts.append(a)

    fake_usage = {"input_tokens": 50, "output_tokens": 20,
                  "cache_read_tokens": 0, "cache_creation_tokens": 0}

    guard_calls = {"n": 0}

    async def fake_guard(**kwargs):
        guard_calls["n"] += 1
        assert kwargs.get("feature") == "alert_analysis"
        assert kwargs.get("organization_id") == "org_x"

    async def fake_send(**kwargs):
        return ("[alert_0] ok", fake_usage)

    with patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.send_message_with_usage",
               new=fake_send), \
         patch("services.claude_client.resolve_non_chat_model",
               return_value=""), \
         patch("services.llm.budget_guard.check_budget_or_raise",
               new=fake_guard), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()):
        await alert_analysis.analyze_alerts(
            alerts, kpis={}, locale="it",
            organization_id="org_x",
        )

    assert guard_calls["n"] == 1, "budget guard MUST be invoked exactly once"


async def test_alert_analysis_refused_when_governance_blocks():
    """If check_budget_or_raise raises, alert_analysis returns {} without
    calling Anthropic."""
    from modules.cashflow_monitor import alert_analysis
    from services.llm.budget_guard import BudgetExceededError

    a = MagicMock(id="a1", severity="low", title="t", message="m",
                  metric_value=0, threshold=0,
                  created_at=MagicMock(isoformat=lambda: "2026-05-15"))

    send_calls = {"n": 0}

    async def fake_send(**kwargs):
        send_calls["n"] += 1
        return ("ok", {"input_tokens": 0, "output_tokens": 0,
                       "cache_read_tokens": 0, "cache_creation_tokens": 0})

    async def fake_guard(**kwargs):
        raise BudgetExceededError(
            "monthly budget exhausted",
            scope="feature", scope_id="alert_analysis",
            period="daily",
            current_spend_usd=99.0, hard_limit_usd=10.0,
        )

    with patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.send_message_with_usage",
               new=fake_send), \
         patch("services.llm.budget_guard.check_budget_or_raise",
               new=fake_guard):
        result = await alert_analysis.analyze_alerts(
            [a], kpis={}, locale="it",
            organization_id="org_x",
        )

    assert result == {}, "refused alert analysis returns empty dict"
    assert send_calls["n"] == 0, "Anthropic must NOT be called when refused"


# ════════════════════════════════════════════════════════════════════════════
# 10.A.4 — fail-open emergency cap
# ════════════════════════════════════════════════════════════════════════════


async def test_fail_open_below_cap_allows():
    """Single fail-open event allows the call (logs warning, returns None)."""
    from services.llm import budget_guard

    # Reset the sliding window for a deterministic test
    budget_guard._fail_open_timestamps.clear()

    # Simulate one fail-open from find_applicable_budgets
    with patch(
        "services.llm.budget_guard._read_kill_switch",
        new=AsyncMock(return_value={
            "ai_enabled": True, "ai_throttle_pct": 0,
            "kill_reason": None, "activated_at": None, "activated_by": None,
        }),
    ), patch(
        "repositories.ai_budget_repository.find_applicable_budgets",
        new=AsyncMock(side_effect=RuntimeError("mongo down")),
    ):
        # Should NOT raise — first fail-open is allowed
        await budget_guard.check_budget_or_raise(organization_id="org_x")

    assert len(budget_guard._fail_open_timestamps) == 1


async def test_fail_open_above_cap_blocks():
    """After _FAIL_OPEN_LIMIT events, the next fail-open raises
    AIDisabledError instead of returning silently."""
    from services.llm import budget_guard
    from services.llm.budget_guard import AIDisabledError

    # Pre-populate the window with cap-1 timestamps so the next event hits cap.
    budget_guard._fail_open_timestamps.clear()
    now_ts = datetime.now(timezone.utc).timestamp()
    for _ in range(budget_guard._FAIL_OPEN_LIMIT - 1):
        budget_guard._fail_open_timestamps.append(now_ts)

    with patch(
        "services.llm.budget_guard._read_kill_switch",
        new=AsyncMock(return_value={
            "ai_enabled": True, "ai_throttle_pct": 0,
            "kill_reason": None, "activated_at": None, "activated_by": None,
        }),
    ), patch(
        "repositories.ai_budget_repository.find_applicable_budgets",
        new=AsyncMock(side_effect=RuntimeError("mongo down")),
    ):
        with pytest.raises(AIDisabledError) as exc_info:
            await budget_guard.check_budget_or_raise(organization_id="org_x")

    assert "governance store unavailable" in str(exc_info.value).lower() or \
           "fail_open" in exc_info.value.context.get("reason", "")
    # Reset for other tests
    budget_guard._fail_open_timestamps.clear()


async def test_fail_open_window_expires():
    """Timestamps older than the window are dropped — the cap is
    sliding, not cumulative."""
    from services.llm import budget_guard

    budget_guard._fail_open_timestamps.clear()
    # Fill with timestamps from 2 windows ago (should be dropped)
    old_ts = datetime.now(timezone.utc).timestamp() - (
        budget_guard._FAIL_OPEN_WINDOW_SEC * 2
    )
    for _ in range(budget_guard._FAIL_OPEN_LIMIT - 1):
        budget_guard._fail_open_timestamps.append(old_ts)

    with patch(
        "services.llm.budget_guard._read_kill_switch",
        new=AsyncMock(return_value={
            "ai_enabled": True, "ai_throttle_pct": 0,
            "kill_reason": None, "activated_at": None, "activated_by": None,
        }),
    ), patch(
        "repositories.ai_budget_repository.find_applicable_budgets",
        new=AsyncMock(side_effect=RuntimeError("mongo down")),
    ):
        # Old timestamps should be evicted; new fail-open allowed
        await budget_guard.check_budget_or_raise(organization_id="org_x")

    # After eviction + the new event, there should be exactly 1 entry
    assert len(budget_guard._fail_open_timestamps) == 1


# ════════════════════════════════════════════════════════════════════════════
# 10.A.6 — atomic rate limit counter
# ════════════════════════════════════════════════════════════════════════════


async def test_rate_limit_acquire_increments_atomically():
    """First N calls return increasing count; (N+1)th raises RateLimitExceeded."""
    from services.rate_limit import acquire, RateLimitExceeded

    # Mock the collection's find_one_and_update so we don't need real Mongo.
    counter = {"n": 0}
    fake_coll = MagicMock()
    async def fake_update(*args, **kwargs):
        counter["n"] += 1
        return {"count": counter["n"]}
    fake_coll.find_one_and_update = AsyncMock(side_effect=fake_update)
    fake_coll.update_one = AsyncMock()
    fake_coll.create_index = AsyncMock()

    fake_db = MagicMock()
    fake_db.rate_limit_counters = fake_coll

    with patch("database.db", fake_db):
        # Reset the lazy index flag so the test setup runs cleanly
        import services.rate_limit as rl
        rl._TTL_INDEX_CREATED = False

        # First 5 calls all succeed and return increasing values
        for expected in range(1, 6):
            got = await acquire(key="k1", limit=5, window_seconds=60)
            assert got == expected

        # 6th call exceeds the cap
        with pytest.raises(RateLimitExceeded) as exc_info:
            await acquire(key="k1", limit=5, window_seconds=60)
        assert exc_info.value.limit == 5
        assert exc_info.value.count == 6


async def test_rate_limit_fail_open_on_mongo_error():
    """A Mongo outage during acquire() returns 0 (allowed) instead of
    crashing the caller."""
    from services.rate_limit import acquire

    fake_coll = MagicMock()
    fake_coll.find_one_and_update = AsyncMock(side_effect=RuntimeError("mongo down"))
    fake_coll.create_index = AsyncMock()
    fake_db = MagicMock()
    fake_db.rate_limit_counters = fake_coll

    with patch("database.db", fake_db):
        import services.rate_limit as rl
        rl._TTL_INDEX_CREATED = True  # skip the ensure_index path

        result = await acquire(key="k_outage", limit=5)
    assert result == 0


# ════════════════════════════════════════════════════════════════════════════
# 10.A.7 — ChatRequest max_length
# ════════════════════════════════════════════════════════════════════════════


def test_chat_request_rejects_oversize_message():
    """Pydantic must reject a message > 10_000 chars BEFORE it reaches
    the worker memory."""
    from routers.chat import ChatRequest
    from pydantic import ValidationError

    # 9_999 chars: accepted
    ChatRequest(message="x" * 9_999, session_id="s1")
    # 10_001 chars: rejected at validation time
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 10_001, session_id="s1")


def test_chat_request_rejects_empty_message():
    """min_length=1 means an empty string is rejected."""
    from routers.chat import ChatRequest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ChatRequest(message="", session_id="s1")


# ════════════════════════════════════════════════════════════════════════════
# 10.A.8 — default budgets seeded only when empty
# ════════════════════════════════════════════════════════════════════════════


async def test_seed_default_budgets_when_empty():
    """When ai_budgets is empty, the seed creates the default budgets."""
    from services import seed_ai_budgets

    create_calls = []

    async def fake_create(**kwargs):
        create_calls.append(kwargs)
        return {**kwargs, "id": f"b_{len(create_calls)}"}

    fake_coll = MagicMock()
    fake_coll.count_documents = AsyncMock(return_value=0)

    with patch("database.ai_budgets_collection", fake_coll), \
         patch("repositories.ai_budget_repository.create_budget",
               new=fake_create):
        n = await seed_ai_budgets.seed_default_ai_budgets_if_empty()

    assert n == len(seed_ai_budgets._DEFAULT_BUDGETS)
    assert n >= 5, "expected at least 5 default budgets seeded"
    # Verify the global daily cap is present
    has_global = any(
        c.get("scope") == "global" and c.get("period") == "daily"
        for c in create_calls
    )
    assert has_global, "global daily cap must be in seed"
    # Verify alert_analysis budget is present (the audit's CRIT path)
    has_alert = any(
        c.get("scope") == "feature" and c.get("scope_id") == "alert_analysis"
        for c in create_calls
    )
    assert has_alert, "alert_analysis feature budget must be in seed"


async def test_seed_default_budgets_skipped_when_not_empty():
    """If any budget already exists, the seed is a no-op."""
    from services import seed_ai_budgets

    fake_coll = MagicMock()
    fake_coll.count_documents = AsyncMock(return_value=1)

    create_calls = []

    async def fake_create(**kwargs):
        create_calls.append(kwargs)

    with patch("database.ai_budgets_collection", fake_coll), \
         patch("repositories.ai_budget_repository.create_budget",
               new=fake_create):
        n = await seed_ai_budgets.seed_default_ai_budgets_if_empty()

    assert n == 0
    assert create_calls == []


async def test_seed_default_budgets_skipped_when_env_opt_out():
    """Wave 12 deploy prep — AI_BUDGETS_SEED_DISABLED=1 bypasses the seed
    entirely, even when the collection is empty. Lets the operator
    configure budgets manually via the governance dashboard before any
    default is created."""
    import os
    from services import seed_ai_budgets

    fake_coll = MagicMock()
    fake_coll.count_documents = AsyncMock(return_value=0)  # empty — would seed

    create_calls = []
    async def fake_create(**kwargs):
        create_calls.append(kwargs)

    _old = os.environ.get("AI_BUDGETS_SEED_DISABLED")
    try:
        os.environ["AI_BUDGETS_SEED_DISABLED"] = "1"
        with patch("database.ai_budgets_collection", fake_coll), \
             patch("repositories.ai_budget_repository.create_budget",
                   new=fake_create):
            n = await seed_ai_budgets.seed_default_ai_budgets_if_empty()
    finally:
        if _old is None:
            os.environ.pop("AI_BUDGETS_SEED_DISABLED", None)
        else:
            os.environ["AI_BUDGETS_SEED_DISABLED"] = _old

    assert n == 0
    assert create_calls == []
    # Verify count_documents wasn't even queried — short-circuit before DB
    fake_coll.count_documents.assert_not_awaited()


# ════════════════════════════════════════════════════════════════════════════
# 10.A.5 — agentic loop convergence guards (introspection tests)
# ════════════════════════════════════════════════════════════════════════════


def test_agentic_loop_has_same_tool_guard():
    """The provider source must include the same-tool-twice end_turn
    forcing logic (introspection — runtime test is too coupled to the
    Anthropic SDK to be worth the mock complexity)."""
    import inspect
    from services.llm.providers import anthropic
    src = inspect.getsource(anthropic.AnthropicProvider.send_messages_with_tools)
    # Same-tool guard
    assert "_last_tool_signature" in src
    assert "wave10a5_same_tool_twice" in src
    # Per-round tool_use cap
    assert "_MAX_TOOL_USES_PER_ROUND" in src
    assert "wave10a5_max_tool_uses_per_round" in src
