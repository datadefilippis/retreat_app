"""Repository for platform-level invitations (system admin → new org owner)."""

from datetime import datetime, timezone
from typing import Optional

from database import invites_collection
from models.invite import Invite


async def create(invite: Invite) -> dict:
    """Persist a new invite document."""
    doc = invite.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["expires_at"] = doc["expires_at"].isoformat()
    await invites_collection.insert_one(doc)
    return doc


async def find_by_token_hash(token_hash: str) -> Optional[dict]:
    """Find a pending, non-expired invite by its token hash."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return await invites_collection.find_one(
        {
            "token_hash": token_hash,
            "status": "pending",
            "expires_at": {"$gt": now_iso},
        },
        {"_id": 0},
    )


async def find_by_token_hash_any_status(token_hash: str) -> Optional[dict]:
    """Find an invite by token hash regardless of status (for error messages)."""
    return await invites_collection.find_one(
        {"token_hash": token_hash},
        {"_id": 0},
    )


async def list_all(skip: int = 0, limit: int = 50) -> tuple[list, int]:
    """List all invites (paginated, newest first)."""
    total = await invites_collection.count_documents({})
    cursor = invites_collection.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(limit)
    return items, total


async def revoke(invite_id: str) -> bool:
    """Set invite status to 'revoked'."""
    result = await invites_collection.update_one(
        {"id": invite_id, "status": "pending"},
        {"$set": {
            "status": "revoked",
        }},
    )
    return result.modified_count == 1


async def mark_used(invite_id: str) -> bool:
    """Set invite status to 'used' (called after successful signup)."""
    result = await invites_collection.update_one(
        {"id": invite_id, "status": "pending"},
        {"$set": {
            "status": "used",
        }},
    )
    return result.modified_count == 1
