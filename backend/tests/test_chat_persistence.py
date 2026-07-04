"""
Tests for AI chat session persistence (MongoDB-backed).

Covers:
- Repository layer (find_session, upsert_messages)
- Service layer (chat reads from DB, writes on success, skips on error)
- History compaction (max 30 messages)
- user_id pass-through from router

All tests mock MongoDB — no real DB connection needed.
"""
import pytest
from unittest.mock import AsyncMock, patch, ANY
from datetime import datetime, timezone


# ── Repository Tests ─────────────────────────────────────────────────────────


class TestChatSessionRepository:
    """Tests for repositories/chat_session_repository.py."""

    @pytest.fixture
    def mock_collection(self):
        """Patch chat_sessions_collection at the repository import site."""
        with patch("repositories.chat_session_repository.chat_sessions_collection") as m:
            m.find_one = AsyncMock(return_value=None)
            m.update_one = AsyncMock()
            yield m

    async def test_find_session_returns_doc(self, mock_collection):
        """find_session returns the raw document when session exists."""
        from repositories import chat_session_repository

        expected = {
            "id": "id_1",
            "organization_id": "org_1",
            "session_id": "sess_1",
            "user_id": "u_1",
            "messages": [{"role": "user", "content": "hello"}],
        }
        mock_collection.find_one.return_value = expected

        result = await chat_session_repository.find_session("org_1", "sess_1")

        assert result == expected
        mock_collection.find_one.assert_called_once_with(
            {"organization_id": "org_1", "session_id": "sess_1"},
            {"_id": 0},
        )

    async def test_find_session_returns_none(self, mock_collection):
        """find_session returns None when session does not exist."""
        from repositories import chat_session_repository

        mock_collection.find_one.return_value = None

        result = await chat_session_repository.find_session("org_1", "no_such_sess")
        assert result is None

    async def test_find_session_with_user_id_filters_query(self, mock_collection):
        """Wave 1.5: when user_id is provided, the Mongo filter includes it.

        This is the explicit acceptance test for B1 (intra-org session
        hijack). The repository must apply the user_id filter so a peer
        in the same org cannot retrieve another user's session.
        """
        from repositories import chat_session_repository

        mock_collection.find_one.return_value = None
        await chat_session_repository.find_session(
            "org_1", "sess_X", user_id="alice",
        )
        mock_collection.find_one.assert_called_once_with(
            {"organization_id": "org_1", "session_id": "sess_X", "user_id": "alice"},
            {"_id": 0},
        )

    async def test_find_session_without_user_id_is_org_scoped_only(
        self, mock_collection,
    ):
        """Backward-compat: when user_id is None, filter is the legacy shape.

        This branch exists for admin/system tooling that legitimately
        needs to find any session in an org. Production code paths
        always pass user_id.
        """
        from repositories import chat_session_repository

        mock_collection.find_one.return_value = None
        await chat_session_repository.find_session("org_1", "sess_X")
        mock_collection.find_one.assert_called_once_with(
            {"organization_id": "org_1", "session_id": "sess_X"},
            {"_id": 0},
        )

    async def test_upsert_creates_new_session(self, mock_collection):
        """upsert_messages calls update_one with upsert=True and correct shape."""
        from repositories import chat_session_repository

        messages = [{"role": "user", "content": "hello"}]
        await chat_session_repository.upsert_messages(
            "org_1", "sess_1", "user_1", messages,
        )

        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args

        # Wave 1.5 (2026-05) — filter now includes user_id to prevent
        # intra-org cross-user overwrites. See chat_session_repository.
        assert call_args[0][0] == {
            "organization_id": "org_1",
            "session_id": "sess_1",
            "user_id": "user_1",
        }

        # $set contains messages and updated_at
        update_doc = call_args[0][1]
        assert update_doc["$set"]["messages"] == messages
        assert isinstance(update_doc["$set"]["updated_at"], datetime)

        # $setOnInsert contains immutable fields
        insert_fields = update_doc["$setOnInsert"]
        assert insert_fields["organization_id"] == "org_1"
        assert insert_fields["session_id"] == "sess_1"
        assert insert_fields["user_id"] == "user_1"
        assert "id" in insert_fields
        assert isinstance(insert_fields["created_at"], datetime)

        # upsert=True
        assert call_args[1]["upsert"] is True

    async def test_upsert_refreshes_updated_at(self, mock_collection):
        """Each upsert call writes a fresh updated_at (TTL reset)."""
        from repositories import chat_session_repository

        await chat_session_repository.upsert_messages(
            "org_1", "sess_1", "user_1", [{"role": "user", "content": "m1"}],
        )
        first_ts = mock_collection.update_one.call_args[0][1]["$set"]["updated_at"]

        mock_collection.update_one.reset_mock()

        await chat_session_repository.upsert_messages(
            "org_1", "sess_1", "user_1", [
                {"role": "user", "content": "m1"},
                {"role": "assistant", "content": "r1"},
            ],
        )
        second_ts = mock_collection.update_one.call_args[0][1]["$set"]["updated_at"]

        # Both should be recent UTC datetimes (within same test run)
        assert isinstance(first_ts, datetime)
        assert isinstance(second_ts, datetime)
        assert second_ts >= first_ts


# ── Service Tests ────────────────────────────────────────────────────────────


class TestChatServicePersistence:
    """Tests for services/chat_service.py after in-memory → MongoDB migration."""

    @pytest.fixture
    def mock_deps(self):
        """Patch all dependencies of chat_service.chat()."""
        with (
            patch(
                "repositories.chat_session_repository.find_session",
                new_callable=AsyncMock,
            ) as find,
            patch(
                "repositories.chat_session_repository.upsert_messages",
                new_callable=AsyncMock,
            ) as upsert,
            patch(
                "services.claude_client.send_messages_with_tools",
                new_callable=AsyncMock,
            ) as send,
            patch(
                "services.claude_client.is_available",
                return_value=True,
            ),
            patch(
                "services.ai_tool_registry.get_tools_for_chat",
                new_callable=AsyncMock,
                return_value=([], AsyncMock(), {"cashflow_monitor"}),
            ),
        ):
            # Default: Claude returns a simple reply, no tool exchanges
            send.return_value = (
                "AI reply text",
                [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "AI reply text"},
                ],
                {"input_tokens": 100, "output_tokens": 50},
            )
            yield {
                "find_session": find,
                "upsert_messages": upsert,
                "send": send,
            }

    async def test_chat_reads_from_db(self, mock_deps):
        """chat() loads existing session history from MongoDB."""
        from services.chat_service import chat

        mock_deps["find_session"].return_value = {
            "messages": [
                {"role": "user", "content": "previous msg"},
                {"role": "assistant", "content": "previous reply"},
            ],
        }

        await chat("org_1", "sess_1", "new msg", user_id="u1")

        # find_session called with correct args.
        # Wave 1.5 (2026-05) — chat_service now passes user_id so the
        # repository can apply per-user isolation. See B1 in baseline.
        mock_deps["find_session"].assert_called_once_with(
            "org_1", "sess_1", user_id="u1",
        )

        # send_messages_with_tools received history including existing + new msg.
        # Wave 9.B.1: the NEW message now carries a "TODAY: YYYY-MM-DD\n\n"
        # prefix so the model has the date context without invalidating the
        # cacheable system prompt. Existing persisted messages stay verbatim.
        send_call = mock_deps["send"].call_args
        messages_sent = send_call[1]["messages"]
        assert len(messages_sent) == 3  # 2 existing + 1 new
        assert messages_sent[0] == {"role": "user", "content": "previous msg"}
        # New message: TODAY-prefix + original text
        new_content = messages_sent[2]["content"]
        assert messages_sent[2]["role"] == "user"
        assert new_content.endswith("new msg")
        assert new_content.startswith("TODAY: ")

    async def test_chat_first_message_creates_session(self, mock_deps):
        """chat() works when no session exists yet (find_session returns None)."""
        from services.chat_service import chat

        mock_deps["find_session"].return_value = None

        result = await chat("org_1", "sess_new", "first msg", user_id="u1")

        assert result == "AI reply text"
        # upsert_messages called to persist the new session
        mock_deps["upsert_messages"].assert_called_once()
        upsert_call = mock_deps["upsert_messages"].call_args
        assert upsert_call[0][0] == "org_1"      # org_id
        assert upsert_call[0][1] == "sess_new"   # session_id
        assert upsert_call[0][2] == "u1"          # user_id

    async def test_chat_persists_on_success(self, mock_deps):
        """chat() writes compacted history to DB after successful response."""
        from services.chat_service import chat

        mock_deps["find_session"].return_value = None

        await chat("org_1", "sess_1", "hello", user_id="u1")

        mock_deps["upsert_messages"].assert_called_once()
        persisted_messages = mock_deps["upsert_messages"].call_args[0][3]
        # Should contain the full exchange returned by send_messages_with_tools
        assert len(persisted_messages) == 2
        assert persisted_messages[0]["role"] == "user"
        assert persisted_messages[1]["role"] == "assistant"

    async def test_chat_does_not_persist_on_error(self, mock_deps):
        """chat() does NOT write to DB when Claude raises an error."""
        from services.chat_service import chat

        mock_deps["find_session"].return_value = None
        mock_deps["send"].side_effect = RuntimeError("Claude API failed")

        with pytest.raises(RuntimeError, match="Claude API failed"):
            await chat("org_1", "sess_1", "hello", user_id="u1")

        # upsert_messages must NOT have been called
        mock_deps["upsert_messages"].assert_not_called()

    async def test_user_id_passed_through(self, mock_deps):
        """user_id parameter flows from chat() to upsert_messages()."""
        from services.chat_service import chat

        mock_deps["find_session"].return_value = None

        await chat("org_1", "sess_1", "hi", user_id="user_42")

        upsert_call = mock_deps["upsert_messages"].call_args
        assert upsert_call[0][2] == "user_42"  # third positional arg is user_id

    async def test_compact_history_truncates(self, mock_deps):
        """History exceeding _MAX_HISTORY is truncated to last 30 messages."""
        from services.chat_service import chat

        # Create 35 existing messages
        existing = []
        for i in range(35):
            existing.append({"role": "user", "content": f"msg_{i}"})
            existing.append({"role": "assistant", "content": f"reply_{i}"})
        # Total: 70 messages (well over 30)

        mock_deps["find_session"].return_value = {"messages": existing}

        # send_messages_with_tools will receive truncated history
        # and return updated messages based on that
        long_result = existing[-30:] + [
            {"role": "user", "content": "new"},
            {"role": "assistant", "content": "new reply"},
        ]
        mock_deps["send"].return_value = (
            "new reply",
            long_result,
            {"input_tokens": 100, "output_tokens": 50},
        )

        await chat("org_1", "sess_1", "new", user_id="u1")

        # The messages sent to Claude should be truncated
        send_call = mock_deps["send"].call_args
        messages_sent = send_call[1]["messages"]
        assert len(messages_sent) <= 30

    async def test_chat_unavailable_raises(self, mock_deps):
        """chat() raises ClaudeUnavailableError when AI is not available."""
        from services.chat_service import chat
        from services.claude_client import ClaudeUnavailableError

        with patch("services.claude_client.is_available", return_value=False):
            with pytest.raises(ClaudeUnavailableError):
                await chat("org_1", "sess_1", "hello", user_id="u1")

        # No DB operations attempted
        mock_deps["find_session"].assert_not_called()
        mock_deps["upsert_messages"].assert_not_called()
