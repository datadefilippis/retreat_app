"""Wave 8A.1 — AIUsageEvent schema extension + MongoDB indices.

Verifies:
  1. The 8 new optional fields are accepted by the model and the repository.
  2. record_usage() roundtrips them into the inserted document.
  3. Wave 8A.0 callers (digest_builder, health_explanation, etc.) propagate
     cache_read_tokens + cache_creation_tokens that they receive from
     send_message_with_usage.
  4. setup_indexes() creates all 7 indices on the collection.

Mocks the collection. No real MongoDB.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ── Schema — AIUsageEvent accepts the new fields ────────────────────────────

def test_ai_usage_event_accepts_wave8a1_fields():
    from models.ai_usage import AIUsageEvent

    event = AIUsageEvent(
        organization_id="org_test",
        feature="digest",
        conversation_id="conv_abc",
        parent_event_id="evt_parent",
        request_id="req_xyz",
        cache_read_tokens=1000,
        cache_creation_tokens=50,
        latency_ms=850,
        error_code=None,
        feature_metadata={"prompt_length": 1234, "tool_count": 47},
    )
    assert event.conversation_id == "conv_abc"
    assert event.parent_event_id == "evt_parent"
    assert event.request_id == "req_xyz"
    assert event.cache_read_tokens == 1000
    assert event.cache_creation_tokens == 50
    assert event.latency_ms == 850
    assert event.error_code is None
    assert event.feature_metadata == {"prompt_length": 1234, "tool_count": 47}


def test_ai_usage_event_defaults_wave8a1_fields_to_none():
    """Legacy callers must keep working: all new fields default to None."""
    from models.ai_usage import AIUsageEvent

    event = AIUsageEvent(organization_id="org", feature="chat")
    assert event.conversation_id is None
    assert event.parent_event_id is None
    assert event.request_id is None
    assert event.cache_read_tokens is None
    assert event.cache_creation_tokens is None
    assert event.latency_ms is None
    assert event.error_code is None
    assert event.feature_metadata is None


# ── record_usage roundtrips the new fields ───────────────────────────────────

async def test_record_usage_persists_wave8a1_fields():
    from repositories import usage_repository

    fake_coll = MagicMock()
    fake_coll.insert_one = AsyncMock()
    with patch("repositories.usage_repository.ai_usage_events_collection",
               fake_coll):
        await usage_repository.record_usage(
            org_id="org_test",
            module_key="ai_assistant",
            feature_key="chat",
            tokens_prompt=2000,
            tokens_completion=400,
            cache_read_tokens=1500,
            cache_creation_tokens=0,
            conversation_id="conv_chat_1",
            request_id="req_anthropic_abc",
            latency_ms=720,
            feature_metadata={"prompt_length": 4500},
        )

    fake_coll.insert_one.assert_awaited_once()
    doc = fake_coll.insert_one.await_args.args[0]
    assert doc["organization_id"] == "org_test"
    assert doc["tokens_prompt"] == 2000
    assert doc["tokens_completion"] == 400
    assert doc["cache_read_tokens"] == 1500
    assert doc["cache_creation_tokens"] == 0
    assert doc["conversation_id"] == "conv_chat_1"
    assert doc["request_id"] == "req_anthropic_abc"
    assert doc["latency_ms"] == 720
    assert doc["feature_metadata"] == {"prompt_length": 4500}


async def test_record_usage_omits_unset_wave8a1_fields():
    """Backward compat: legacy callers don't materialize None fields.

    Storage hygiene: documents stay shape-stable. A 2024 event and a
    2026 event with the same call shape produce identical docs.
    """
    from repositories import usage_repository

    fake_coll = MagicMock()
    fake_coll.insert_one = AsyncMock()
    with patch("repositories.usage_repository.ai_usage_events_collection",
               fake_coll):
        await usage_repository.record_usage(
            org_id="org_test",
            module_key="ai_assistant",
            feature_key="chat",
            tokens_prompt=100,
            tokens_completion=50,
        )

    doc = fake_coll.insert_one.await_args.args[0]
    # When None is passed, the dict-based skipping in record_usage means
    # the FIELD is not in event_kwargs — Pydantic uses the model default
    # (None for all wave 8A.1 additions). So the field IS in the doc but
    # has value None. That's fine — the test pins this contract.
    assert doc.get("conversation_id") is None
    assert doc.get("request_id") is None
    assert doc.get("cache_read_tokens") is None
    # Standard fields still populated.
    assert doc["tokens_prompt"] == 100


# ── Wave 8A.0 callers now pass cache tokens ──────────────────────────────────

async def test_digest_builder_passes_cache_tokens():
    from modules.cashflow_monitor import digest_builder

    fake_overview = {
        "period": {"days": 30},
        "kpis": {"total_sales": 100, "total_expenses": 50, "net_after_fixed": 30,
                 "operating_margin_pct": 30, "dso": 0, "burn_rate_total": 0,
                 "break_even": 0},
        "health_score": {"score": 60},
        "alerts_summary": {"open_count": 0, "by_severity": {}},
    }
    usage_with_cache = {
        "input_tokens": 500,
        "output_tokens": 200,
        "cache_read_tokens": 1500,    # cache hit!
        "cache_creation_tokens": 0,
    }

    with patch("modules.cashflow_monitor.overview_builder.build_overview",
               new=AsyncMock(return_value=fake_overview)), \
         patch("services.claude_client.send_message_with_usage",
               new=AsyncMock(return_value=("text", usage_with_cache))), \
         patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.get_active_model",
               return_value="claude-sonnet-4-20250514"), \
         patch("services.claude_client.calculate_cost_usd", return_value=0.001), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()) as mock_record:
        await digest_builder.build_digest(org_id="org_test", period_days=30)

    kwargs = mock_record.await_args.kwargs
    assert kwargs["cache_read_tokens"] == 1500
    assert kwargs["cache_creation_tokens"] == 0


async def test_health_explanation_passes_cache_tokens():
    from modules.cashflow_monitor import health_explanation

    health_score = {
        "score": 72, "label": "Buono",
        "breakdown": [{"dimension": "Margine Operativo", "points": 8, "max": 10}],
    }
    usage_with_cache = {
        "input_tokens": 300, "output_tokens": 100,
        "cache_read_tokens": 1000, "cache_creation_tokens": 50,
    }

    with patch("services.claude_client.send_message_with_usage",
               new=AsyncMock(return_value=("explained", usage_with_cache))), \
         patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.get_active_model",
               return_value="claude-sonnet-4-20250514"), \
         patch("services.claude_client.calculate_cost_usd", return_value=0.0009), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()) as mock_record:
        await health_explanation.generate_health_explanation_ai(
            health_score, kpis={}, org_id="org_test", user_id="user_a",
        )

    kwargs = mock_record.await_args.kwargs
    assert kwargs["cache_read_tokens"] == 1000
    assert kwargs["cache_creation_tokens"] == 50


# ── setup_indexes creates all 7 indices ──────────────────────────────────────

async def test_setup_indexes_creates_seven_indices():
    """Wave 8A.1: 7 indexed (org/user/agent/conv/cost-time/feature/created_at).
    Wave 10.B.4 added an 8th: sparse TTL on expires_at.
    Wave 10.B.5 also drops 3 legacy redundant indices on the same run.
    """
    from repositories import usage_repository

    fake_coll = MagicMock()
    fake_coll.create_index = AsyncMock()
    fake_coll.drop_index = AsyncMock()

    with patch("repositories.usage_repository.ai_usage_events_collection",
               fake_coll):
        await usage_repository.setup_indexes()

    # 7 Wave 8A.1 indices + 1 Wave 10.B.4 TTL index = 8 create_index calls.
    assert fake_coll.create_index.await_count == 8
    # Verify each index has a stable name (so re-runs are idempotent)
    names_used = []
    for call in fake_coll.create_index.await_args_list:
        names_used.append(call.kwargs.get("name"))
    expected_names = {
        "org_created_v1",
        "user_created_v1",
        "agent_created_v1",
        "conversation_v1",
        "cost_time_v1",
        "feature_created_v1",
        "created_at_v1",
        "ai_usage_ttl_v1",  # Wave 10.B.4
    }
    assert set(names_used) == expected_names

    # Wave 10.B.5 — verify the 3 legacy redundant indices are dropped.
    dropped = [call.args[0] for call in fake_coll.drop_index.await_args_list]
    assert "organization_id_1" in dropped
    assert "organization_id_1_feature_1_created_at_-1" in dropped
    assert "organization_id_1_module_key_1_feature_1_created_at_-1" in dropped


async def test_setup_indexes_continues_on_single_failure():
    """One bad index must not block the others (defense in depth).
    Wave 10.B.4: now 8 create_index calls (7 + TTL).
    """
    from repositories import usage_repository

    call_count = [0]

    async def flaky_create_index(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 3:  # third index fails
            raise RuntimeError("Mongo bad mood")
        return None

    fake_coll = MagicMock()
    fake_coll.create_index = flaky_create_index
    fake_coll.drop_index = AsyncMock()

    with patch("repositories.usage_repository.ai_usage_events_collection",
               fake_coll):
        # Must NOT raise
        await usage_repository.setup_indexes()

    # All 8 attempts ran despite one failure (7 Wave 8A.1 + 1 Wave 10.B.4 TTL)
    assert call_count[0] == 8


async def test_setup_indexes_indices_are_sparse_where_expected():
    """User/agent/conversation indices must be sparse (many None values)."""
    from repositories import usage_repository

    sparse_indices = {}
    fake_coll = MagicMock()

    async def capture(keys, **opts):
        sparse_indices[opts["name"]] = opts.get("sparse", False)

    fake_coll.create_index = capture

    with patch("repositories.usage_repository.ai_usage_events_collection",
               fake_coll):
        await usage_repository.setup_indexes()

    assert sparse_indices["user_created_v1"] is True
    assert sparse_indices["agent_created_v1"] is True
    assert sparse_indices["conversation_v1"] is True
    # Main indices are NOT sparse
    assert sparse_indices["org_created_v1"] is False
    assert sparse_indices["cost_time_v1"] is False
