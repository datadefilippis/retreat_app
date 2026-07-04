"""
Chat Session Repository — MongoDB persistence for AI chat sessions.

Identity: (organization_id, user_id, session_id) — sessions are per-user
even within the same org. Wave 1.5 (2026-05) closed the intra-org
session hijack vector by requiring user_id on every read path.

Why per-user (not per-org):
A chat session contains the user's private business questions and the
AI's answers. A peer employee in the same org should NOT be able to
read those just because they share organization_id. The user_id
filter on every read/update/delete enforces this isolation.

Uses upsert to atomically create-or-update sessions.
TTL is managed by MongoDB TTL index on expires_at (per-document expiry).
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone

from database import chat_sessions_collection
from models.common import generate_id

logger = logging.getLogger(__name__)


async def find_session(
    org_id: str,
    session_id: str,
    user_id: Optional[str] = None,
) -> Optional[dict]:
    """Find a chat session by (org_id, session_id) — optionally scoped to user.

    Wave 1.5 (2026-05) — security fix
    ----------------------------------
    The original implementation filtered only by (org_id, session_id),
    which made intra-org session hijack possible: a user who learned
    another user's session_id (via log leak, screenshot, debug output)
    could fetch that user's private chat history just by passing the
    session_id back. Cross-tenant was safe (different org_id), but the
    intra-tenant gap was real.

    The new contract:
    - When ``user_id`` is provided (the production code path from
      chat_service.chat / routers/chat endpoints), the lookup also
      filters by user_id. Returns None when the session belongs to
      another user — same shape as "not found".
    - When ``user_id`` is None (only legitimate use: admin/system
      tooling that needs to see any session), the legacy behaviour is
      preserved. Production code paths SHOULD always pass user_id.

    The opt-in nature keeps backward compatibility while making the
    intended secure usage obvious at every call site.
    """
    query = {"organization_id": org_id, "session_id": session_id}
    if user_id is not None:
        query["user_id"] = user_id
    return await chat_sessions_collection.find_one(query, {"_id": 0})


async def upsert_messages(
    org_id: str,
    session_id: str,
    user_id: str,
    messages: list,
    *,
    expires_at: Optional[datetime] = None,
    title: Optional[str] = None,
) -> None:
    """Create or update a session's message history.

    Wave 1.5 (2026-05) — security fix
    ----------------------------------
    The filter now includes ``user_id``. Without it, a malicious user
    A in the same org could pass user_B's session_id and OVERWRITE
    user_B's chat history (the $set update applied because the
    (org_id, session_id) filter matched). Adding user_id to the
    filter makes such cross-user writes a no-op (filter doesn't
    match → upsert creates a new doc for user_A — that user owns it
    and never touches user_B's record).

    - First call: creates the document with id, user_id, created_at, title.
    - Subsequent calls: updates messages and refreshes updated_at + expires_at.
    - Atomic via MongoDB update_one with upsert=True.
    """
    now = datetime.now(timezone.utc)
    set_fields = {
        "messages": messages,
        "updated_at": now,
    }
    if expires_at is not None:
        set_fields["expires_at"] = expires_at

    set_on_insert = {
        "id": generate_id(),
        "organization_id": org_id,
        "session_id": session_id,
        "user_id": user_id,
        "created_at": now,
    }
    if title is not None:
        set_on_insert["title"] = title

    await chat_sessions_collection.update_one(
        {"organization_id": org_id, "session_id": session_id, "user_id": user_id},
        {
            "$set": set_fields,
            "$setOnInsert": set_on_insert,
        },
        upsert=True,
    )


async def list_sessions(
    org_id: str,
    user_id: str,
    limit: int = 50,
) -> List[dict]:
    """List chat sessions for a user (metadata only, no messages).

    Returns sessions sorted by updated_at DESC (most recent first).
    """
    cursor = chat_sessions_collection.find(
        {"organization_id": org_id, "user_id": user_id},
        {
            "_id": 0,
            "session_id": 1,
            "title": 1,
            "created_at": 1,
            "updated_at": 1,
        },
    ).sort("updated_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def delete_session(org_id: str, user_id: str, session_id: str) -> bool:
    """Delete a session (user_id filter ensures per-user isolation).

    Returns True if a document was deleted, False otherwise.
    """
    result = await chat_sessions_collection.delete_one(
        {"organization_id": org_id, "user_id": user_id, "session_id": session_id},
    )
    return result.deleted_count > 0


async def update_title(
    org_id: str,
    session_id: str,
    title: str,
    user_id: Optional[str] = None,
) -> bool:
    """Rename a session's title.

    Wave 1.5 (2026-05) — security fix
    ----------------------------------
    user_id is now part of the filter when provided (production code
    path). Without it, a user could rename any session in their org
    just by knowing the session_id. The opt-in form preserves backward
    compatibility for callers that intentionally don't have user_id
    (admin tooling) but the routers/chat handler now always passes it.

    Returns True if a document was updated, False otherwise.
    """
    query = {"organization_id": org_id, "session_id": session_id}
    if user_id is not None:
        query["user_id"] = user_id
    result = await chat_sessions_collection.update_one(
        query,
        {"$set": {"title": title}},
    )
    return result.modified_count > 0
