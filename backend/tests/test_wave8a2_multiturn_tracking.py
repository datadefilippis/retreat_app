"""Wave 8A.2 — multi-turn agentic loop tracking.

Verifies:
  1. Provider invokes on_round callback after each round-trip with per-round usage.
  2. Provider tolerates callback failure (logs but doesn't raise).
  3. Chat with N tool calls produces N events sharing conversation_id.

Mocks the Anthropic SDK; no real LLM, no MongoDB.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


def _mock_response(text: str, stop_reason: str = "end_turn",
                   input_tokens: int = 100, output_tokens: int = 50,
                   cache_read: int = 0, cache_write: int = 0,
                   tool_uses: list = None):
    """Build a fake anthropic.Message response."""
    response = MagicMock()
    # Build content blocks
    content_blocks = []
    if text:
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text
        content_blocks.append(text_block)
    for tu in (tool_uses or []):
        tu_block = MagicMock()
        tu_block.type = "tool_use"
        tu_block.id = tu["id"]
        tu_block.name = tu["name"]
        tu_block.input = tu["input"]
        content_blocks.append(tu_block)
    response.content = content_blocks
    response.stop_reason = stop_reason
    response.usage = MagicMock(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_write,
    )
    return response


# ── Provider invokes on_round per round ──────────────────────────────────────

async def test_on_round_fires_once_per_round_no_tools():
    """1 round (no tool use) → 1 callback invocation."""
    from services.llm.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider()
    fake_client = MagicMock()
    fake_response = _mock_response(
        "Final answer", stop_reason="end_turn",
        input_tokens=500, output_tokens=120,
        cache_read=200, cache_write=10,
    )
    fake_client.messages.create = AsyncMock(return_value=fake_response)

    rounds_seen = []

    async def on_round(round_idx, usage):
        rounds_seen.append((round_idx, usage))

    with patch.object(provider, "_get_client", return_value=fake_client):
        text, _, total = await provider.send_messages_with_tools(
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            on_tool_call=AsyncMock(),
            on_round=on_round,
        )

    assert text == "Final answer"
    assert len(rounds_seen) == 1
    idx, usage = rounds_seen[0]
    assert idx == 0
    assert usage["input_tokens"] == 500
    assert usage["output_tokens"] == 120
    assert usage["cache_read_tokens"] == 200
    assert usage["cache_creation_tokens"] == 10


async def test_on_round_fires_twice_with_one_tool_call():
    """2 rounds (model uses tool, then final text) → 2 callback invocations."""
    from services.llm.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider()
    fake_client = MagicMock()
    # Round 0: model emits tool_use
    round0 = _mock_response(
        "",
        stop_reason="tool_use",
        input_tokens=300, output_tokens=80,
        cache_read=0, cache_write=200,
        tool_uses=[{"id": "tu_1", "name": "query_business_summary",
                    "input": {"period": "30d"}}],
    )
    # Round 1: model emits final text
    round1 = _mock_response(
        "Here's your answer", stop_reason="end_turn",
        input_tokens=600, output_tokens=150,
        cache_read=200, cache_write=0,
    )
    fake_client.messages.create = AsyncMock(side_effect=[round0, round1])

    rounds_seen = []

    async def on_round(round_idx, usage):
        rounds_seen.append((round_idx, usage))

    async def fake_tool(name, input_):
        return {"result": "ok"}

    with patch.object(provider, "_get_client", return_value=fake_client):
        text, _, total = await provider.send_messages_with_tools(
            system="sys",
            messages=[{"role": "user", "content": "what's my revenue?"}],
            tools=[{"name": "query_business_summary",
                    "description": "...", "input_schema": {"type": "object"}}],
            on_tool_call=fake_tool,
            on_round=on_round,
        )

    assert text == "Here's your answer"
    assert len(rounds_seen) == 2
    # Round 0
    assert rounds_seen[0][0] == 0
    assert rounds_seen[0][1]["input_tokens"] == 300
    assert rounds_seen[0][1]["cache_creation_tokens"] == 200
    # Round 1
    assert rounds_seen[1][0] == 1
    assert rounds_seen[1][1]["input_tokens"] == 600
    assert rounds_seen[1][1]["cache_read_tokens"] == 200
    # Total sums correctly across rounds
    assert total["input_tokens"] == 900
    assert total["output_tokens"] == 230


async def test_on_round_callback_failure_does_not_kill_chat():
    """A tracking exception in the callback must be caught and logged."""
    from services.llm.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider()
    fake_client = MagicMock()
    fake_response = _mock_response(
        "Answer", stop_reason="end_turn",
        input_tokens=100, output_tokens=50,
    )
    fake_client.messages.create = AsyncMock(return_value=fake_response)

    async def broken_on_round(idx, usage):
        raise RuntimeError("mongo died")

    with patch.object(provider, "_get_client", return_value=fake_client):
        # Should NOT raise — the chat completes normally
        text, _, _ = await provider.send_messages_with_tools(
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            on_tool_call=AsyncMock(),
            on_round=broken_on_round,
        )

    assert text == "Answer"


async def test_on_round_is_optional_backward_compat():
    """Existing callers that don't pass on_round must keep working."""
    from services.llm.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider()
    fake_client = MagicMock()
    fake_response = _mock_response(
        "Answer", stop_reason="end_turn",
        input_tokens=100, output_tokens=50,
    )
    fake_client.messages.create = AsyncMock(return_value=fake_response)

    with patch.object(provider, "_get_client", return_value=fake_client):
        # No on_round parameter passed
        text, _, _ = await provider.send_messages_with_tools(
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            on_tool_call=AsyncMock(),
        )

    assert text == "Answer"


# ── chat_service writes per-round events with conversation_id ───────────────

async def test_chat_writes_one_event_per_round_with_same_conversation_id():
    """End-to-end: a chat with 2 rounds produces 2 AIUsageEvent
    docs sharing the same conversation_id."""
    from services import chat_service

    # Mock send_messages_with_tools to simulate the agentic loop firing
    # on_round twice (2 rounds) before returning.
    rounds_data = [
        (0, {"input_tokens": 300, "output_tokens": 80,
             "cache_read_tokens": 0, "cache_creation_tokens": 200}),
        (1, {"input_tokens": 600, "output_tokens": 150,
             "cache_read_tokens": 200, "cache_creation_tokens": 0}),
    ]

    async def fake_send(system, messages, tools, on_tool_call,
                        max_tokens=1024, temperature=0.3,
                        max_rounds=5, on_round=None):
        for idx, usage in rounds_data:
            if on_round is not None:
                await on_round(idx, usage)
        return ("Final assistant text", list(messages) + [
            {"role": "assistant", "content": [{"type": "text", "text": "Final assistant text"}]},
        ], {"input_tokens": 900, "output_tokens": 230})

    fake_tools = []
    fake_dispatch = AsyncMock(return_value={"ok": True})
    fake_active = set()

    with patch("services.claude_client.is_available", return_value=True), \
         patch("services.claude_client.send_messages_with_tools",
               new=fake_send), \
         patch("services.ai_tool_registry.get_tools_for_chat",
               new=AsyncMock(return_value=(fake_tools, fake_dispatch, fake_active))), \
         patch("repositories.chat_session_repository.find_session",
               new=AsyncMock(return_value=None)), \
         patch("repositories.chat_session_repository.upsert_messages",
               new=AsyncMock()), \
         patch("services.chat_service._compute_expires_at",
               new=AsyncMock(return_value=None)), \
         patch("repositories.usage_repository.record_usage",
               new=AsyncMock()) as mock_record, \
         patch("services.ai_cost_calculator.compute_cost_usd",
               return_value=0.001):
        reply = await chat_service.chat(
            org_id="org_test", session_id="sess_1",
            user_message="what's up?", locale="it", user_id="user_a",
        )

    assert reply == "Final assistant text"
    # Exactly 2 events written (one per round), NO aggregate
    assert mock_record.await_count == 2

    # Both events share the same conversation_id
    call_kwargs_list = [c.kwargs for c in mock_record.await_args_list]
    conv_ids = {c["conversation_id"] for c in call_kwargs_list}
    assert len(conv_ids) == 1
    assert next(iter(conv_ids))  # non-empty

    # First event = round 0, second = round 1
    assert call_kwargs_list[0]["feature_metadata"]["round_index"] == 0
    assert call_kwargs_list[1]["feature_metadata"]["round_index"] == 1
    # Token counts match the per-round data
    assert call_kwargs_list[0]["tokens_prompt"] == 300
    assert call_kwargs_list[1]["tokens_prompt"] == 600
    assert call_kwargs_list[0]["cache_creation_tokens"] == 200
    assert call_kwargs_list[1]["cache_read_tokens"] == 200
    # session_id propagated via feature_metadata
    assert call_kwargs_list[0]["feature_metadata"]["session_id"] == "sess_1"
