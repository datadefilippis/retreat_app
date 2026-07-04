"""
admin_repository.py
===================
Cross-org read queries for the System Admin control panel.

ISOLATION CONTRACT:
  Functions in this module intentionally do NOT apply an organization_id filter.
  They exist solely to power /api/admin/* routes protected by require_system_admin.

  !! Never import or call these functions from org-scoped routers !!

  All write operations (suspend org, toggle user, reset password, etc.) will be
  added here in the next implementation step, still behind require_system_admin.
"""

from datetime import timezone
from typing import List, Optional

from database import (
    audit_logs_collection,
    organization_modules_collection,
    organizations_collection,
    users_collection,
)
from models.common import generate_id, utc_now


# ── Organizations ─────────────────────────────────────────────────────────────

async def list_organizations(skip: int = 0, limit: int = 50) -> List[dict]:
    """All organizations, newest first.  No org-id filter — intentionally cross-tenant."""
    cursor = (
        organizations_collection
        .find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return await cursor.to_list(limit)


async def count_organizations() -> int:
    return await organizations_collection.count_documents({})


async def get_organization_detail(org_id: str) -> Optional[dict]:
    """Single organization by ID.  Returns None if not found."""
    return await organizations_collection.find_one({"id": org_id}, {"_id": 0})


# ── Users ─────────────────────────────────────────────────────────────────────

async def list_users_all(
    skip: int = 0,
    limit: int = 50,
    *,
    org_id: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[dict]:
    """
    All users across all orgs.  password_hash is always excluded.
    Optional filters: org_id, role, is_active.
    """
    filter_q: dict = {}
    if org_id is not None:
        filter_q["organization_id"] = org_id
    if role is not None:
        filter_q["role"] = role
    if is_active is not None:
        filter_q["is_active"] = is_active

    cursor = (
        users_collection
        .find(filter_q, {"_id": 0, "password_hash": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return await cursor.to_list(limit)


async def count_users(
    *,
    org_id: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> int:
    filter_q: dict = {}
    if org_id is not None:
        filter_q["organization_id"] = org_id
    if role is not None:
        filter_q["role"] = role
    if is_active is not None:
        filter_q["is_active"] = is_active
    return await users_collection.count_documents(filter_q)


async def get_user_detail(user_id: str) -> Optional[dict]:
    """Single user by ID.  password_hash excluded.  Returns None if not found."""
    return await users_collection.find_one(
        {"id": user_id},
        {"_id": 0, "password_hash": 0},
    )


# ── Modules ───────────────────────────────────────────────────────────────────

async def list_org_modules(org_id: str) -> List[dict]:
    """All module records (active AND inactive) for a specific org, newest first."""
    cursor = (
        organization_modules_collection
        .find({"organization_id": org_id}, {"_id": 0})
        .sort("activated_at", -1)
    )
    return await cursor.to_list(100)


# ── Audit Logs ────────────────────────────────────────────────────────────────

async def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    *,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
) -> List[dict]:
    """
    Global audit log — all orgs, newest first.
    Optional filters: org_id (exact), user_id (exact), action (exact).
    Pass org_id=None with no other filters to see system_admin audit entries.
    """
    filter_q: dict = {}
    if org_id is not None:
        filter_q["organization_id"] = org_id
    if user_id is not None:
        filter_q["user_id"] = user_id
    if action is not None:
        filter_q["action"] = action

    cursor = (
        audit_logs_collection
        .find(filter_q, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return await cursor.to_list(limit)


async def count_audit_logs(
    *,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
) -> int:
    filter_q: dict = {}
    if org_id is not None:
        filter_q["organization_id"] = org_id
    if user_id is not None:
        filter_q["user_id"] = user_id
    if action is not None:
        filter_q["action"] = action
    return await audit_logs_collection.count_documents(filter_q)


# ══════════════════════════════════════════════════════════════════════════════
# Write helpers (v3.0) — all protected by require_system_admin at the router
# ══════════════════════════════════════════════════════════════════════════════

# ── Module lookup ─────────────────────────────────────────────────────────────

async def get_org_module(org_id: str, module_key: str) -> Optional[dict]:
    """Return the single module record for (org_id, module_key), or None."""
    return await organization_modules_collection.find_one(
        {"organization_id": org_id, "module_key": module_key},
        {"_id": 0},
    )


# ── Organization writes ───────────────────────────────────────────────────────

async def set_org_status(org_id: str, is_active: bool) -> bool:
    """
    Suspend (is_active=False) or reactivate (is_active=True) an organization.
    Returns True if the org was found (whether or not anything changed).
    """
    result = await organizations_collection.update_one(
        {"id": org_id},
        {"$set": {"is_active": is_active, "updated_at": utc_now().isoformat()}},
    )
    return result.matched_count > 0


async def set_org_plan(org_id: str, plan: str) -> bool:
    """
    Change the subscription plan for an organization.
    Returns True if the org was found.
    """
    result = await organizations_collection.update_one(
        {"id": org_id},
        {"$set": {"plan": plan, "updated_at": utc_now().isoformat()}},
    )
    return result.matched_count > 0


# ── User writes ───────────────────────────────────────────────────────────────

async def set_user_status(user_id: str, is_active: bool) -> Optional[dict]:
    """
    Activate or deactivate a user.
    Returns the updated user doc (password_hash excluded) or None if not found.
    """
    result = await users_collection.update_one(
        {"id": user_id},
        {"$set": {"is_active": is_active}},
    )
    if result.matched_count == 0:
        return None
    return await users_collection.find_one(
        {"id": user_id},
        {"_id": 0, "password_hash": 0},
    )


async def reset_user_password(user_id: str, password_hash: str) -> bool:
    """
    Overwrite a user's password hash with a new (already hashed) value.
    Also stamps password_changed_at so that all previously issued tokens for
    this user are invalidated by get_current_user() on next use.
    Returns True if the user was found.
    """
    now_iso = utc_now().isoformat()
    result = await users_collection.update_one(
        {"id": user_id},
        {"$set": {
            "password_hash": password_hash,
            "password_changed_at": now_iso,
            "updated_at": now_iso,
            "must_change_password": True,
        }},
    )
    return result.matched_count > 0


# ── Module writes ─────────────────────────────────────────────────────────────

async def admin_activate_module(
    org_id: str,
    module_key: str,
    activated_by: str,
) -> None:
    """
    Activate a module for an org.
    - Creates the record (upsert) if it doesn't exist yet.
    - Updates is_active=True + activated_at + activated_by if it exists.
    The caller must pre-check that the module is NOT already active (400 guard).
    """
    now = utc_now().isoformat()
    await organization_modules_collection.update_one(
        {"organization_id": org_id, "module_key": module_key},
        {
            "$set": {
                "is_active": True,
                "activated_at": now,
                "activated_by": activated_by,
            },
            "$setOnInsert": {
                "id": generate_id(),
                "organization_id": org_id,
                "module_key": module_key,
            },
        },
        upsert=True,
    )


async def admin_deactivate_module(org_id: str, module_key: str) -> bool:
    """
    Deactivate a module for an org.
    Returns True if a record was found and updated, False if nothing changed.
    The caller must pre-check that the module EXISTS and IS active (404/400 guards).
    """
    result = await organization_modules_collection.update_one(
        {"organization_id": org_id, "module_key": module_key},
        {"$set": {"is_active": False}},
    )
    return result.modified_count > 0
