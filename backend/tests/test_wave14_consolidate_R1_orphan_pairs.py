"""Wave 14.CONSOLIDATE R1 — orphan tool_use/tool_result pair stripping.

Pre-Wave-14 _compact_history did a blind ``messages[-_MAX_HISTORY:]``
slice. When the slice boundary fell BETWEEN a ``tool_use`` block and
its matching ``tool_result`` block, one or both sides became orphans.
Anthropic's API rejects orphan tool blocks with HTTP 400, which then
bubbled up as a generic chat failure for the user. The Wave 13.2
audit flagged this as a latent crash; we close it here with
``_strip_orphan_tool_blocks``.

These tests are also regression sentinels — any future refactor of
truncation logic that re-introduces the orphan risk will turn red.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Helpers ────────────────────────────────────────────────────────────────


def _tool_use_msg(tid, name="query_x", inp=None):
    return {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": tid, "name": name, "input": inp or {}},
        ],
    }


def _tool_result_msg(tid, body="ok"):
    return {
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": tid, "content": body},
        ],
    }


def _text_msg(role, text):
    return {"role": role, "content": text}


# ── The orphan-stripping core ──────────────────────────────────────────────


class TestStripOrphanToolBlocks:
    def test_balanced_pair_preserved(self):
        """No orphans → output identical (no destructive rewrites)."""
        from services.chat_service import _strip_orphan_tool_blocks
        messages = [
            _text_msg("user", "TODAY: 2026-05-16\n\nhello"),
            _tool_use_msg("call_1"),
            _tool_result_msg("call_1", body="result_1"),
            _text_msg("assistant", "done"),
        ]
        out = _strip_orphan_tool_blocks(messages)
        assert out == messages

    def test_orphan_result_dropped_when_tool_use_missing(self):
        """Head-side orphan: a tool_result whose tool_use was already
        truncated out. Must be dropped."""
        from services.chat_service import _strip_orphan_tool_blocks
        messages = [
            _tool_result_msg("call_old", body="orphan"),
            _text_msg("user", "TODAY: hello"),
            _tool_use_msg("call_new"),
            _tool_result_msg("call_new"),
        ]
        out = _strip_orphan_tool_blocks(messages)
        # The orphan tool_result message (only one block, the orphan)
        # gets dropped entirely; the rest is preserved.
        assert len(out) == 3
        assert out[0] == _text_msg("user", "TODAY: hello")
        assert out[1]["content"][0]["id"] == "call_new"

    def test_orphan_tool_use_dropped_when_result_missing(self):
        """Tail-side orphan: a tool_use without its tool_result."""
        from services.chat_service import _strip_orphan_tool_blocks
        messages = [
            _text_msg("user", "TODAY: hello"),
            _tool_use_msg("call_1"),
            _tool_result_msg("call_1"),
            # call_2 never got its tool_result back
            _tool_use_msg("call_2"),
        ]
        out = _strip_orphan_tool_blocks(messages)
        # call_2 message dropped (only block is orphan tool_use)
        assert len(out) == 3
        ids_used = [
            b.get("id")
            for m in out
            for b in (m["content"] if isinstance(m["content"], list) else [])
            if isinstance(b, dict) and b.get("type") == "tool_use"
        ]
        assert "call_2" not in ids_used

    def test_mixed_assistant_message_keeps_text_drops_orphan_tool_use(self):
        """An assistant message with text + orphan tool_use → text kept,
        tool_use dropped, message survives."""
        from services.chat_service import _strip_orphan_tool_blocks
        messages = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me check..."},
                    {"type": "tool_use", "id": "orphan", "name": "x", "input": {}},
                ],
            },
            # No tool_result for "orphan"
        ]
        out = _strip_orphan_tool_blocks(messages)
        assert len(out) == 1
        assert out[0]["content"] == [
            {"type": "text", "text": "Let me check..."},
        ]

    def test_mixed_user_message_keeps_text_drops_orphan_result(self):
        """A user message with text + orphan tool_result → text kept."""
        from services.chat_service import _strip_orphan_tool_blocks
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "orphan",
                     "content": "stale"},
                    {"type": "text", "text": "and what about Y?"},
                ],
            },
        ]
        out = _strip_orphan_tool_blocks(messages)
        assert out[0]["content"] == [
            {"type": "text", "text": "and what about Y?"},
        ]

    def test_string_content_unchanged(self):
        """Plain string content (legacy/text-only) must pass through
        without any rewriting."""
        from services.chat_service import _strip_orphan_tool_blocks
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello there"},
        ]
        out = _strip_orphan_tool_blocks(messages)
        assert out == messages

    def test_empty_message_list(self):
        from services.chat_service import _strip_orphan_tool_blocks
        assert _strip_orphan_tool_blocks([]) == []

    def test_multiple_orphans_logged_once(self, caplog):
        """A single info log is emitted summarising how many orphan
        blocks were stripped — important for forensics post-prod."""
        import logging
        from services.chat_service import _strip_orphan_tool_blocks

        messages = [
            _tool_result_msg("orphan_a"),
            _tool_use_msg("orphan_b"),
            _tool_use_msg("call_x"),
            _tool_result_msg("call_x"),
        ]
        with caplog.at_level(logging.INFO, logger="services.chat_service"):
            _strip_orphan_tool_blocks(messages)
        # At least one INFO log about the stripping
        msgs = [r.message for r in caplog.records if "orphan" in r.message]
        assert any("removed" in m for m in msgs)


# ── _compact_history integration ───────────────────────────────────────────


class TestCompactHistoryUsesOrphanStripping:
    def test_under_max_history_no_stripping(self):
        """Histories shorter than _MAX_HISTORY skip the truncation +
        stripping pass entirely (perf — common case)."""
        from services.chat_service import _compact_history, _MAX_HISTORY
        messages = [_text_msg("user", f"m{i}") for i in range(_MAX_HISTORY - 5)]
        out = _compact_history(messages)
        assert out == messages

    def test_truncation_drops_orphan_result_at_head(self):
        """Wave 14 R1 — the canonical scenario: truncation slice
        leaves a tool_result whose tool_use is now beyond the slice."""
        from services.chat_service import _compact_history, _MAX_HISTORY

        # Build a long history where call_1 (tool_use) lives at index 0
        # but its tool_result is at index 1 — both before _MAX_HISTORY
        # cutoff. Then add enough text messages to push call_1 OUT of
        # the truncation window but leave the tool_result IN.
        messages = []
        # Old tool_use that will be truncated out
        messages.append(_tool_use_msg("call_old"))
        # Its tool_result — also old but earlier than the cutoff
        messages.append(_tool_result_msg("call_old"))
        # Fill with text messages to push the boundary
        for i in range(_MAX_HISTORY - 1):
            messages.append(_text_msg("user", f"msg_{i}"))
            messages.append(_text_msg("assistant", f"reply_{i}"))
        # Add a balanced pair AT THE END (must survive)
        messages.append(_tool_use_msg("call_new"))
        messages.append(_tool_result_msg("call_new"))

        out = _compact_history(messages)
        # Length must be <= _MAX_HISTORY
        assert len(out) <= _MAX_HISTORY
        # No orphan tool_result for call_old
        for msg in out:
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        assert block.get("tool_use_id") != "call_old", (
                            "Wave 14 R1 regression — orphan tool_result "
                            "for call_old survived truncation."
                        )
        # call_new pair MUST survive (most recent)
        ids_used = [
            b.get("id")
            for m in out for b in (m["content"] if isinstance(m["content"], list) else [])
            if isinstance(b, dict) and b.get("type") == "tool_use"
        ]
        assert "call_new" in ids_used

    def test_truncation_drops_orphan_tool_use_at_tail(self):
        """The reverse: tool_use at the boundary, tool_result outside."""
        from services.chat_service import _compact_history, _MAX_HISTORY

        # Filler at start
        messages = []
        for i in range(_MAX_HISTORY + 5):
            messages.append(_text_msg("user", f"m{i}"))
        # Append a tool_use without its tool_result (truncated case)
        messages.append(_tool_use_msg("call_x"))
        # NO tool_result for call_x is added

        out = _compact_history(messages)
        # call_x is orphan → must be stripped
        ids_used = [
            b.get("id")
            for m in out for b in (m["content"] if isinstance(m["content"], list) else [])
            if isinstance(b, dict) and b.get("type") == "tool_use"
        ]
        assert "call_x" not in ids_used
