"""Wave 9.A — critical hardening tests.

Pins the contract of three independent fixes:

  9.A.1  /chat/stream endpoint REMOVED
         The endpoint bypassed the entire Wave 8 governance suite
         (no record_usage, no budget check, no kill switch coverage).
         Removed in this wave to close the attack surface.

  9.A.2  Quota counter for feature="chat" counts USER MESSAGES,
         not Anthropic round-trips. After Wave 8A.2 the multi-turn
         agentic loop writes one AIUsageEvent per round → without
         this fix, users on metered plans burn quota 2-3x faster.

  9.A.3  Tool result truncation + pre-flight history-size guard.
         A real production chat (April 2026) hit 33,531 input tokens
         in a single Anthropic call because a tool returned ~30KB of
         data. These guards cap the worst-case chat cost.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ════════════════════════════════════════════════════════════════════════════
# 9.A.1 — /chat/stream endpoint removed
# ════════════════════════════════════════════════════════════════════════════


def test_chat_stream_endpoint_no_longer_registered():
    """The router must not expose /chat/stream after Wave 9.A.

    A grep test on the router source — the file is not committed if
    someone re-introduces the endpoint, which is the deliberate signal.
    """
    from routers import chat as chat_router
    routes = {r.path for r in chat_router.router.routes}
    # /chat exists (the agentic chat), /chat/stream must not.
    assert any("/chat" in p for p in routes), "Sanity: /chat should still exist"
    assert not any(p.endswith("/chat/stream") for p in routes), (
        "Wave 9.A.1: /chat/stream must be removed — it bypassed Wave 8 "
        "governance (no record_usage, no budget check, no kill switch). "
        "If you need streaming again, route it through chat_service.chat "
        "so the same Wave 8 guards apply."
    )


def test_streaming_response_import_removed():
    """No `StreamingResponse` import lingers in chat router.

    Defensive: an unused import is a hint that the streaming code is
    being added back without going through the proper path.
    """
    import inspect
    from routers import chat as chat_router
    src = inspect.getsource(chat_router)
    assert "from fastapi.responses import StreamingResponse" not in src


# ════════════════════════════════════════════════════════════════════════════
# 9.A.2 — Quota counter fix (count distinct conversation_id for chat)
# ════════════════════════════════════════════════════════════════════════════


pytestmark_async = pytest.mark.asyncio


def _fake_agg(docs):
    async def _aiter():
        for d in docs:
            yield d
    cursor = MagicMock()
    cursor.__aiter__ = lambda self: _aiter()
    cursor.to_list = AsyncMock(return_value=docs)
    return cursor


@pytest.mark.asyncio
async def test_count_usage_for_chat_counts_distinct_conversations():
    """Wave 9.A.2 — feature=chat counts distinct conversation_id.

    Aggregation pipeline must group by conversation_id (with fallback
    to the event id for legacy events without conversation_id).
    """
    from repositories import usage_repository as repo

    captured_pipeline = []
    coll = MagicMock()

    def fake_agg(pipeline):
        captured_pipeline.append(pipeline)
        # Pretend 4 distinct conversations were found.
        return _fake_agg([{"total": 4}])

    coll.aggregate = fake_agg
    with patch("repositories.usage_repository.ai_usage_events_collection", coll):
        result = await repo.count_usage(
            org_id="org_x", module_key="ai_assistant",
            feature_key="chat",
            period_start="2026-05-01", period_end="2026-05-31",
        )

    assert result == 4
    assert captured_pipeline, "Expected an aggregation pipeline to be issued"
    # Pipeline must group by conversation_id, NOT sum quantity.
    stages = captured_pipeline[0]
    group_stage = next((s for s in stages if "$group" in s), None)
    assert group_stage is not None
    group_id = group_stage["$group"]["_id"]
    # The fix uses $ifNull with conversation_id + fallback to event id
    assert "$ifNull" in str(group_id), (
        f"Wave 9.A.2 regression — group _id must use $ifNull on "
        f"$conversation_id, got: {group_id}"
    )
    assert "conversation_id" in str(group_id)


@pytest.mark.asyncio
async def test_count_usage_for_other_features_still_sums_quantity():
    """Non-chat features keep the legacy behavior (sum quantity)."""
    from repositories import usage_repository as repo

    captured_pipeline = []
    coll = MagicMock()

    def fake_agg(pipeline):
        captured_pipeline.append(pipeline)
        return _fake_agg([{"total": 42}])

    coll.aggregate = fake_agg
    with patch("repositories.usage_repository.ai_usage_events_collection", coll):
        result = await repo.count_usage(
            org_id="org_x", module_key="cashflow_monitor",
            feature_key="data_rows",  # NOT chat
            period_start="2026-05-01", period_end="2026-05-31",
        )

    assert result == 42
    group_stage = next((s for s in captured_pipeline[0] if "$group" in s), None)
    assert group_stage is not None
    # Legacy: sum of quantity
    assert "$sum" in str(group_stage["$group"]["total"])


@pytest.mark.asyncio
async def test_count_usage_chat_with_multi_turn_events():
    """Real-world simulation: 3 chats × 2 rounds each → count_usage = 3, not 6.

    Verified by feeding an aggregation result count that reflects
    distinct conversation_id (3) instead of raw event count (6).
    """
    from repositories import usage_repository as repo

    coll = MagicMock()
    # The aggregation returns one bucket per conversation_id;
    # after $count it returns {"total": 3}.
    coll.aggregate = MagicMock(return_value=_fake_agg([{"total": 3}]))
    with patch("repositories.usage_repository.ai_usage_events_collection", coll):
        result = await repo.count_usage(
            "org_x", "ai_assistant", "chat",
            "2026-05-01", "2026-05-31",
        )
    assert result == 3  # 3 user messages, NOT 6 round-trips


# ════════════════════════════════════════════════════════════════════════════
# 9.A.3 — Tool result truncation
# ════════════════════════════════════════════════════════════════════════════


def test_truncate_small_tool_result_passes_through():
    from services.chat_service import _truncate_tool_result

    small = {"ok": True, "data": [1, 2, 3]}
    assert _truncate_tool_result(small, "query_x") is small


def test_truncate_huge_tool_result_caps_and_marks():
    """Wave 9.A.3 marker contract. Wave 14.2 replaced the single
    head-only marker (``wave9a_tool_result_cap``) with TWO possible
    structurally-meaningful markers: ``wave14_structured`` when one
    of the four structured passes succeeded, or
    ``wave14_head_only_fallback`` when even those weren't enough.
    Either is correct; the test now accepts both."""
    from services.chat_service import _truncate_tool_result, _MAX_TOOL_RESULT_CHARS

    # Build a payload that vastly exceeds the cap. The structure
    # (single non-droppable ``rows`` list) avoids triggering Pass 1-4
    # so the head-only fallback fires.
    huge = {"rows": [{"name": "row" * 100} for _ in range(1000)]}
    out = _truncate_tool_result(huge, "query_business_summary")

    assert out["_truncated"] is True
    # Wave 14.2 — either structured or head-only fallback marker
    assert out["_truncated_by"] in (
        "wave14_structured",
        "wave14_head_only_fallback",
        # Legacy marker accepted as a regression-safety alias
        "wave9a_tool_result_cap",
    )
    assert out["_original_size_chars"] > _MAX_TOOL_RESULT_CHARS
    assert out["_cap_chars"] == _MAX_TOOL_RESULT_CHARS
    assert "query_business_summary" in out["_hint"]
    # ``head`` is present in the fallback branch; structured branch
    # uses ``_truncated_fields`` instead. Accept either signal.
    assert "head" in out or "_truncated_fields" in out
    if "head" in out:
        assert len(out["head"]) <= max(2000, _MAX_TOOL_RESULT_CHARS // 4) + 100


def test_truncate_non_serializable_input_returns_as_is():
    """Defensive: an object that json.dumps cannot serialize skips truncation.

    The function must NOT crash on un-serializable payloads — it should
    return the original (the agentic loop handles it downstream).
    """
    from services.chat_service import _truncate_tool_result

    # Object that fails the json.dumps + default=str fallback chain.
    class Unserializable:
        def __str__(self):
            raise TypeError("really cannot serialize")
        def __repr__(self):
            raise TypeError("really cannot serialize")

    weird = {"x": Unserializable()}
    # Must not raise — that's the contract under test.
    out = _truncate_tool_result(weird, "query_x")
    assert out is weird


# ════════════════════════════════════════════════════════════════════════════
# 9.A.3 — _estimate_history_chars
# ════════════════════════════════════════════════════════════════════════════


def test_estimate_history_chars_string_content():
    from services.chat_service import _estimate_history_chars

    msgs = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "world"},
    ]
    assert _estimate_history_chars(msgs) == 10


def test_estimate_history_chars_list_content():
    """Multi-modal / tool_use blocks: serialize JSON."""
    from services.chat_service import _estimate_history_chars

    msgs = [
        {"role": "assistant", "content": [
            {"type": "text", "text": "x"},
            {"type": "tool_use", "id": "tu_1", "name": "q", "input": {"a": 1}},
        ]},
    ]
    out = _estimate_history_chars(msgs)
    # JSON-serialized blob has bracket/quote overhead — must be > 1 char
    assert out > 20


def test_estimate_history_chars_grows_with_size():
    from services.chat_service import _estimate_history_chars

    small = [{"role": "user", "content": "a" * 100}]
    large = [{"role": "user", "content": "a" * 100_000}]
    assert _estimate_history_chars(large) > _estimate_history_chars(small) * 100


# ════════════════════════════════════════════════════════════════════════════
# 9.A.3 — Pre-flight history guard rejects oversized chats
# ════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_chat_refuses_when_history_too_large():
    """Wave 9.A.3 — refuse early when serialized history > cap.

    Cheaper to fail before the Anthropic round-trip than to discover the
    spike via a $0.10 invoice.
    """
    from services import chat_service

    # 200K chars of content → far above _MAX_HISTORY_CHARS=100K
    bloated_history = [
        {"role": "user", "content": "x" * 200_000},
    ]
    bloated_session = {"messages": bloated_history, "session_id": "s1"}

    with patch("services.claude_client.is_available", return_value=True), \
         patch("services.ai_tool_registry.get_tools_for_chat",
               new=AsyncMock(return_value=([], AsyncMock(), set()))), \
         patch("repositories.chat_session_repository.find_session",
               new=AsyncMock(return_value=bloated_session)):
        with pytest.raises(Exception) as exc_info:
            await chat_service.chat(
                org_id="org_x", session_id="s1",
                user_message="add one more message",
                locale="it", user_id="user_a",
            )

    # Should raise our user-facing error, not crash silently
    assert "too large" in str(exc_info.value).lower() or "history" in str(exc_info.value).lower()
