from typing import Optional, List
from database import users_collection
from models import User, UserResponse, UserRole


async def find_by_reset_token_hash(token_hash: str) -> Optional[dict]:
    """Find a user by their hashed password-reset token.
    Returns the full document so the caller can validate expiry and update the password.
    Returns None if not found."""
    return await users_collection.find_one({"reset_token_hash": token_hash}, {"_id": 0})


async def find_by_verification_token_hash(token_hash: str) -> Optional[dict]:
    """Find a user by their hashed email-verification token.
    Returns the full document so the caller can validate expiry.
    Returns None if not found."""
    return await users_collection.find_one({"verification_token_hash": token_hash}, {"_id": 0})


async def find_by_email(email: str) -> Optional[dict]:
    """Find user by email"""
    return await users_collection.find_one({"email": email}, {"_id": 0})


async def find_by_id(user_id: str) -> Optional[dict]:
    """Find user by ID — returns the document regardless of is_active status.
    Callers that need active-only semantics should use find_active_by_id()."""
    return await users_collection.find_one({"id": user_id}, {"_id": 0})


async def find_active_by_id(user_id: str) -> Optional[dict]:
    """Find user by ID only if the account is active.

    Returns None when the user does not exist OR when is_active is False.
    Use this when you need a single-query shortcut and do not need to
    distinguish between 'not found' and 'deactivated'.
    (get_current_user uses find_by_id + explicit is_active check instead,
    so it can return a precise 401 detail message for each case.)
    """
    return await users_collection.find_one(
        {"id": user_id, "is_active": True},
        {"_id": 0},
    )


async def find_by_org(org_id: str) -> List[dict]:
    """Find all users in an organization"""
    cursor = users_collection.find(
        {"organization_id": org_id},
        {"_id": 0, "password_hash": 0}
    ).sort("created_at", -1)
    return await cursor.to_list(100)


async def create(user: User) -> dict:
    """Create a new user"""
    user_doc = user.model_dump()
    user_doc['created_at'] = user_doc['created_at'].isoformat()
    user_doc['updated_at'] = user_doc['updated_at'].isoformat()
    await users_collection.insert_one(user_doc)
    return user_doc


async def update(user_id: str, update_data: dict) -> bool:
    """Update user by ID"""
    result = await users_collection.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    return result.modified_count > 0


async def delete(user_id: str) -> bool:
    """Delete user by ID"""
    result = await users_collection.delete_one({"id": user_id})
    return result.deleted_count > 0


async def update_role(user_id: str, role: UserRole) -> bool:
    """Update user role"""
    result = await users_collection.update_one(
        {"id": user_id},
        {"$set": {"role": role.value}}
    )
    return result.modified_count > 0
