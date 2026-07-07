"""
routers/admin.py
================
System Admin control panel — read-only API (v2.9).

ALL routes require require_system_admin.
No org-scoped route should ever import or delegate to this router.

Current scope (read-only):
  GET /api/admin/organizations
  GET /api/admin/organizations/{org_id}
  GET /api/admin/organizations/{org_id}/modules
  GET /api/admin/users
  GET /api/admin/users/{user_id}
  GET /api/admin/audit-log

Future scope (next step — write actions, not yet implemented):
  PUT  /api/admin/organizations/{org_id}/plan        — change plan
  PUT  /api/admin/organizations/{org_id}/status      — suspend / reactivate
  PUT  /api/admin/users/{user_id}/status             — activate / deactivate
  POST /api/admin/users/{user_id}/reset-password     — generate reset link
  POST /api/admin/organizations/{org_id}/modules/{key}/activate
  POST /api/admin/organizations/{org_id}/modules/{key}/deactivate
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
# Onda 27.2 — see backend/core/rate_limiting.py for rationale.
# Replaces slowapi.util.get_remote_address which returned the proxy IP
# behind our nginx reverse proxy, making per-IP rate limits global.
from core.rate_limiting import get_real_ip

from auth import get_password_hash, require_system_admin
from models import AuditLog
from models.invite import Invite, InviteCreate, InviteResponse, InviteListResponse
from repositories import platform_settings_repository, invite_repository
from services.email_service import send_platform_invite, APP_URL

from models.admin import (
    AuditLogAdminEntry,
    AuditLogListResponse,
    OrgBillingFieldsPatch,
    OrgBillingInfo,
    OrgCommercialPlanUpdate,
    OrgDetailResponse,
    OrgListResponse,
    OrgModuleEntry,
    OrgPlanUpdate,
    OrgStatusUpdate,
    OrgSubscriptionEntry,
    OrgSummary,
    PATCHABLE_BILLING_FIELDS,
    PasswordResetResponse,
    UserAdminSummary,
    UserListAdminResponse,
    UserStatusUpdate,
    VALID_COMMERCIAL_PLANS,
    VALID_PLANS,
)
from core.module_registry import get_all_for_ui as _registered_modules_for_ui
from repositories import admin_repository, audit_repository, billing_repository, subscription_repository, user_repository
from models.subscription import ModuleSubscription
from services import plan_provisioning

limiter = Limiter(key_func=get_real_ip)

router = APIRouter(prefix="/admin", tags=["System Admin"])

# ── Known module keys (v3.1 hardening) ────────────────────────────────────────
#
# Registered modules come from core.module_registry (explicit register()
# call in each module's __init__.py).  Future modules are declared here
# to stay in sync with routers/modules.py::FUTURE_MODULES.  This set is
# used to reject activate requests for arbitrary/unknown keys.
#
_FUTURE_MODULE_KEYS: frozenset = frozenset({
    "revenue_forecasting",
    "expense_optimizer",
    "inventory_tracker",
})


def _all_known_module_keys() -> frozenset:
    """Return all recognized module keys: registered (live) + future (reserved)."""
    registered = frozenset(m["key"] for m in _registered_modules_for_ui())
    return registered | _FUTURE_MODULE_KEYS


# ── Date parsing helper ───────────────────────────────────────────────────────

def _dt(val: object) -> datetime:
    """Parse ISO string to datetime, or return as-is if already a datetime."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val)
    # Fallback: let Pydantic handle it
    return val  # type: ignore[return-value]


# ── Org parsers ───────────────────────────────────────────────────────────────

def _org_summary(doc: dict) -> OrgSummary:
    return OrgSummary(
        id=doc["id"],
        name=doc["name"],
        industry=doc.get("industry"),
        plan=doc.get("plan"),
        timezone=doc.get("timezone"),
        currency=doc.get("currency"),
        is_active=doc.get("is_active", True),  # v3.0: suspension flag
        commercial_plan_slug=doc.get("commercial_plan_slug", "free"),
        billing_status=doc.get("billing_status", "none"),
        cancel_at_period_end=doc.get("cancel_at_period_end", False),
        created_at=_dt(doc["created_at"]),
        updated_at=_dt(doc["updated_at"]),
    )


def _module_entry(doc: dict) -> OrgModuleEntry:
    return OrgModuleEntry(
        module_key=doc["module_key"],
        is_active=doc.get("is_active", True),
        activated_at=_dt(doc["activated_at"]),
        activated_by=doc.get("activated_by", ""),
    )


# ── User parser ───────────────────────────────────────────────────────────────

def _user_summary(doc: dict) -> UserAdminSummary:
    last_login = doc.get("last_login_at")
    return UserAdminSummary(
        id=doc["id"],
        email=doc["email"],
        name=doc["name"],
        role=doc["role"],
        organization_id=doc.get("organization_id"),
        is_active=doc.get("is_active", True),
        created_at=_dt(doc["created_at"]),
        last_login_at=_dt(last_login) if last_login else None,
    )


# ── Audit log parser ──────────────────────────────────────────────────────────

def _audit_entry(doc: dict) -> AuditLogAdminEntry:
    return AuditLogAdminEntry(
        id=doc["id"],
        organization_id=doc.get("organization_id"),
        user_id=doc["user_id"],
        action=doc["action"],
        resource_type=doc["resource_type"],
        resource_id=doc.get("resource_id"),
        details=doc.get("details", {}),
        created_at=_dt(doc["created_at"]),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Organizations
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/organizations",
    response_model=OrgListResponse,
    summary="List all organizations",
)
async def list_organizations(
    skip:  int = Query(0,  ge=0,  description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    _: dict = Depends(require_system_admin),
) -> OrgListResponse:
    """
    Return all organizations on the platform, newest first.
    Supports pagination via skip / limit.
    """
    total, docs = (
        await admin_repository.count_organizations(),
        await admin_repository.list_organizations(skip=skip, limit=limit),
    )
    return OrgListResponse(
        items=[_org_summary(d) for d in docs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/organizations/{org_id}",
    response_model=OrgDetailResponse,
    summary="Organization detail with users and modules",
)
async def get_organization(
    org_id: str,
    _: dict = Depends(require_system_admin),
) -> OrgDetailResponse:
    """
    Full organization detail: metadata + all users in the org + all module records.
    """
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    user_docs   = await admin_repository.list_users_all(org_id=org_id, limit=500)
    module_docs = await admin_repository.list_org_modules(org_id)

    # v5.0: build billing info
    billing_info = OrgBillingInfo(
        commercial_plan_slug=org_doc.get("commercial_plan_slug", "free"),
        billing_status=org_doc.get("billing_status", "none"),
        billing_interval=org_doc.get("billing_interval"),
        trial_ends_at=_dt(org_doc["trial_ends_at"]) if org_doc.get("trial_ends_at") else None,
        current_period_end=_dt(org_doc["current_period_end"]) if org_doc.get("current_period_end") else None,
        cancel_at_period_end=org_doc.get("cancel_at_period_end", False),
        plan_assigned_by=org_doc.get("plan_assigned_by", "system"),
        plan_assigned_at=_dt(org_doc["plan_assigned_at"]) if org_doc.get("plan_assigned_at") else None,
        stripe_customer_id=org_doc.get("stripe_customer_id"),
        stripe_subscription_id=org_doc.get("stripe_subscription_id"),
        billing_email=org_doc.get("billing_email"),
    )

    # v5.0: build subscription entries
    subs = await subscription_repository.list_subscriptions_by_org(org_id)
    sub_entries = []
    for sub in subs:
        plan = await subscription_repository.get_pricing_plan(sub["pricing_plan_id"])
        sub_entries.append(OrgSubscriptionEntry(
            module_key=sub["module_key"],
            pricing_plan_slug=plan["slug"] if plan else "",
            pricing_plan_name=plan["name"] if plan else "Unknown",
            status=sub["status"],
            started_at=_dt(sub["started_at"]) if sub.get("started_at") else None,
            assigned_by=sub.get("assigned_by", ""),
            commercial_plan_slug=sub.get("commercial_plan_slug"),
            stripe_subscription_id=sub.get("stripe_subscription_id"),
        ))

    return OrgDetailResponse(
        id=org_doc["id"],
        name=org_doc["name"],
        industry=org_doc.get("industry"),
        plan=org_doc.get("plan"),
        timezone=org_doc.get("timezone"),
        currency=org_doc.get("currency"),
        is_active=org_doc.get("is_active", True),  # v3.0
        created_at=_dt(org_doc["created_at"]),
        updated_at=_dt(org_doc["updated_at"]),
        users=[_user_summary(u) for u in user_docs],
        modules=[_module_entry(m) for m in module_docs],
        billing=billing_info,
        subscriptions=sub_entries,
    )


@router.get(
    "/organizations/{org_id}/modules",
    summary="Active and inactive modules for one organization",
)
async def list_org_modules(
    org_id: str,
    _: dict = Depends(require_system_admin),
) -> list:
    """
    All module records (active + inactive) for the given organization.
    Returns an empty list if the org has no modules or if the org does not exist.
    """
    # Verify org exists first — gives a 404 instead of a silent empty list.
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    module_docs = await admin_repository.list_org_modules(org_id)
    return [_module_entry(m).model_dump() for m in module_docs]


# ══════════════════════════════════════════════════════════════════════════════
# Users
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/users",
    response_model=UserListAdminResponse,
    summary="List all users (cross-org)",
)
async def list_users(
    skip:      int            = Query(0,    ge=0,  description="Records to skip"),
    limit:     int            = Query(50,   ge=1, le=200, description="Max records"),
    org_id:    Optional[str]  = Query(None, description="Filter by organization ID"),
    role:      Optional[str]  = Query(None, description="Filter by role (admin|user|system_admin)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    _: dict = Depends(require_system_admin),
) -> UserListAdminResponse:
    """
    All users across all organizations.  Optional filters: org_id, role, is_active.
    password_hash is never included in any response from this endpoint.
    """
    total, docs = (
        await admin_repository.count_users(org_id=org_id, role=role, is_active=is_active),
        await admin_repository.list_users_all(
            skip, limit, org_id=org_id, role=role, is_active=is_active
        ),
    )
    return UserListAdminResponse(
        items=[_user_summary(d) for d in docs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserAdminSummary,
    summary="Single user detail",
)
async def get_user(
    user_id: str,
    _: dict = Depends(require_system_admin),
) -> UserAdminSummary:
    """
    Full detail for a single user by ID.
    password_hash is never included.
    """
    doc = await admin_repository.get_user_detail(user_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )
    return _user_summary(doc)


# ══════════════════════════════════════════════════════════════════════════════
# Audit Log
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/audit-log",
    response_model=AuditLogListResponse,
    summary="Global audit log (cross-org)",
)
async def list_audit_log(
    skip:    int           = Query(0,   ge=0,  description="Records to skip"),
    limit:   int           = Query(100, ge=1, le=500, description="Max records"),
    org_id:  Optional[str] = Query(None, description="Filter by organization ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action:  Optional[str] = Query(None, description="Filter by action (e.g. login, invite_user)"),
    _: dict = Depends(require_system_admin),
) -> AuditLogListResponse:
    """
    Global audit log across all organizations, newest first.

    Filter tips:
    - org_id=<uuid>    → events for a specific organization
    - user_id=<uuid>   → events by a specific user
    - action=login     → all login events across the platform
    - (no filters)     → entire platform log, newest first
    """
    total, docs = (
        await admin_repository.count_audit_logs(org_id=org_id, user_id=user_id, action=action),
        await admin_repository.list_audit_logs(
            skip, limit, org_id=org_id, user_id=user_id, action=action
        ),
    )
    return AuditLogListResponse(
        items=[_audit_entry(d) for d in docs],
        total=total,
        skip=skip,
        limit=limit,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Org — Write Actions (v3.0)
# ══════════════════════════════════════════════════════════════════════════════

@router.put(
    "/organizations/{org_id}/status",
    summary="Suspend or reactivate an organization",
)
async def set_org_status(
    org_id: str,
    body: OrgStatusUpdate,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """
    Set is_active=False (suspend) or is_active=True (reactivate) for an org.

    Effect: `get_current_user` verifies org.is_active on every request, so
    all users in a suspended org are immediately blocked at the auth layer.
    Returns 400 if the org is already in the requested state.
    """
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    current_state = org_doc.get("is_active", True)
    if current_state == body.is_active:
        label = "active" if body.is_active else "suspended"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization is already {label}",
        )

    await admin_repository.set_org_status(org_id, body.is_active)

    action = "admin_reactivate_org" if body.is_active else "admin_suspend_org"
    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action=action,
        resource_type="organization",
        resource_id=org_id,
        details={"is_active": body.is_active, "org_name": org_doc.get("name")},
    ))

    return {"ok": True, "org_id": org_id, "is_active": body.is_active}


@router.put(
    "/organizations/{org_id}/plan",
    summary="[RITIRATO] usa /commercial-plan",
    deprecated=True,
)
async def set_org_plan(
    org_id: str,
    body: OrgPlanUpdate,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """SA6 — endpoint dell'era pre-catalogo (campo legacy `plan` con
    valori free/starter/pro/enterprise), superato dal provisioning
    commerciale. 410 esplicito: chi lo chiama da uno script vecchio
    deve capire subito dove andare, non scrivere un campo morto."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Endpoint ritirato: usa PUT /admin/organizations/{org_id}/commercial-plan",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Users — Write Actions (v3.0)
# ══════════════════════════════════════════════════════════════════════════════

@router.put(
    "/users/{user_id}/status",
    response_model=UserAdminSummary,
    summary="Activate or deactivate a user",
)
async def set_user_status(
    user_id: str,
    body: UserStatusUpdate,
    current_user: dict = Depends(require_system_admin),
) -> UserAdminSummary:
    """
    Activate or deactivate a user by user_id.

    Guards:
    - Cannot modify system_admin accounts (403).
    - Returns 400 if the user is already in the requested state.

    The change takes effect immediately: `get_current_user` checks is_active
    on every request, so active tokens are invalidated without a token revocation step.
    """
    user_doc = await admin_repository.get_user_detail(user_id)
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    if user_doc.get("role") == "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify the status of a system_admin account",
        )

    current_state = user_doc.get("is_active", True)
    if current_state == body.is_active:
        label = "active" if body.is_active else "inactive"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is already {label}",
        )

    updated = await admin_repository.set_user_status(user_id, body.is_active)

    action = "admin_activate_user" if body.is_active else "admin_deactivate_user"
    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action=action,
        resource_type="user",
        resource_id=user_id,
        details={
            "is_active": body.is_active,
            "target_email": user_doc.get("email"),
            "target_org": user_doc.get("organization_id"),
        },
    ))

    return _user_summary(updated)


@router.post(
    "/users/{user_id}/reset-password",
    response_model=PasswordResetResponse,
    summary="Admin password reset — generates a one-time temporary password",
)
async def reset_user_password(
    user_id: str,
    current_user: dict = Depends(require_system_admin),
) -> PasswordResetResponse:
    """
    Generate a cryptographically random temporary password for a user,
    overwrite their password hash, and return the plaintext once.

    The temporary password is NOT stored anywhere after this response.
    The admin must transmit it to the user via a secure out-of-band channel.

    Guards:
    - Cannot reset the password of a system_admin account (403).
    """
    user_doc = await admin_repository.get_user_detail(user_id)
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )

    if user_doc.get("role") == "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reset the password of a system_admin account",
        )

    temp_password = secrets.token_urlsafe(12)
    await admin_repository.reset_user_password(user_id, get_password_hash(temp_password))

    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_reset_user_password",
        resource_type="user",
        resource_id=user_id,
        details={"target_email": user_doc.get("email")},
    ))

    return PasswordResetResponse(temporary_password=temp_password)


# ══════════════════════════════════════════════════════════════════════════════
# Modules — Write Actions (v3.0)
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/organizations/{org_id}/modules/{module_key}/activate",
    summary="Activate a module for an organization",
)
async def activate_org_module(
    org_id: str,
    module_key: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """
    Activate a module for an organization.
    - Creates the module record if it doesn't exist yet (upsert).
    - Reactivates if it existed but was inactive.
    - Returns 400 if the module is already active.
    """
    # Validate module_key against the known catalogue (v3.1)
    if module_key not in _all_known_module_keys():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Module '{module_key}' is not a recognized module key",
        )

    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    module_doc = await admin_repository.get_org_module(org_id, module_key)
    if module_doc and module_doc.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Module '{module_key}' is already active for this organization",
        )

    await admin_repository.admin_activate_module(
        org_id, module_key, activated_by=current_user["user_id"]
    )

    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_activate_module",
        resource_type="organization_module",
        resource_id=f"{org_id}::{module_key}",
        details={"module_key": module_key, "org_name": org_doc.get("name")},
    ))

    return {"ok": True, "org_id": org_id, "module_key": module_key, "is_active": True}


@router.post(
    "/organizations/{org_id}/modules/{module_key}/deactivate",
    summary="Deactivate a module for an organization",
)
async def deactivate_org_module(
    org_id: str,
    module_key: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """
    Deactivate a module for an organization.
    - Returns 404 if no record exists for (org_id, module_key).
    - Returns 400 if the module is already inactive.
    """
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    module_doc = await admin_repository.get_org_module(org_id, module_key)
    if not module_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_key}' not found for organization '{org_id}'",
        )
    if not module_doc.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Module '{module_key}' is already inactive",
        )

    await admin_repository.admin_deactivate_module(org_id, module_key)

    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_deactivate_module",
        resource_type="organization_module",
        resource_id=f"{org_id}::{module_key}",
        details={"module_key": module_key, "org_name": org_doc.get("name")},
    ))

    return {"ok": True, "org_id": org_id, "module_key": module_key, "is_active": False}


# ══════════════════════════════════════════════════════════════════════════════
# Subscriptions — Admin management (v4.0-E)
# ══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/pricing-plans",
    summary="List pricing plans (optionally filtered by module_key)",
)
async def list_pricing_plans(
    module_key: Optional[str] = Query(None, description="Filter by module key"),
    _: dict = Depends(require_system_admin),
) -> list:
    """Return all active pricing plans. Optionally filter by module_key."""
    plans = await subscription_repository.list_pricing_plans(
        module_key=module_key, active_only=True,
    )
    return plans


@router.get(
    "/organizations/{org_id}/subscriptions",
    summary="List active subscriptions for an organization",
)
async def list_org_subscriptions(
    org_id: str,
    _: dict = Depends(require_system_admin),
) -> list:
    """All active subscriptions for an org, enriched with plan details."""
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    subs = await subscription_repository.list_subscriptions_by_org(org_id)
    result = []
    for sub in subs:
        plan = await subscription_repository.get_pricing_plan(sub["pricing_plan_id"])
        result.append({
            "id": sub["id"],
            "module_key": sub["module_key"],
            "pricing_plan_id": sub["pricing_plan_id"],
            "plan_name": plan["name"] if plan else "Unknown",
            "plan_slug": plan["slug"] if plan else "",
            "price_monthly": plan["price_monthly"] if plan else 0,
            "currency": plan["currency"] if plan else "EUR",
            "limits": plan.get("limits", {}) if plan else {},
            "status": sub["status"],
            "started_at": sub.get("started_at"),
            "assigned_by": sub.get("assigned_by", ""),
        })
    return result


@router.put(
    "/organizations/{org_id}/subscriptions/{module_key}",
    summary="Assign or change subscription plan for a module",
)
async def set_org_subscription(
    org_id: str,
    module_key: str,
    pricing_plan_id: str = Body(..., embed=True),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Assign a pricing plan to an org for a specific module.

    If an active subscription already exists for this org+module, it is
    cancelled first, then a new one is created with the specified plan.
    """
    # Validate org
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    # Validate pricing plan
    plan = await subscription_repository.get_pricing_plan(pricing_plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pricing plan '{pricing_plan_id}' not found",
        )
    if plan["module_key"] != module_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pricing plan '{plan['slug']}' belongs to module "
                   f"'{plan['module_key']}', not '{module_key}'",
        )

    # Cancel existing active subscription (if any)
    previous_plan_name = None
    existing = await subscription_repository.get_active_subscription(org_id, module_key)
    if existing:
        old_plan = await subscription_repository.get_pricing_plan(
            existing["pricing_plan_id"]
        )
        previous_plan_name = old_plan["name"] if old_plan else "Unknown"
        await subscription_repository.cancel_subscription(existing["id"])

    # Create new subscription
    sub = ModuleSubscription(
        organization_id=org_id,
        module_key=module_key,
        pricing_plan_id=pricing_plan_id,
        assigned_by=current_user["user_id"],
        notes=f"Assigned by admin via System Admin panel",
    )
    doc = sub.model_dump()
    doc["started_at"] = doc["started_at"].isoformat()
    doc["expires_at"] = None
    doc["cancelled_at"] = None
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await subscription_repository.create_subscription(doc)

    # Audit log
    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_set_subscription",
        resource_type="module_subscription",
        resource_id=f"{org_id}::{module_key}",
        details={
            "org_name": org_doc.get("name"),
            "module_key": module_key,
            "previous_plan": previous_plan_name,
            "new_plan": plan["name"],
            "pricing_plan_id": pricing_plan_id,
        },
    ))

    return {
        "ok": True,
        "org_id": org_id,
        "module_key": module_key,
        "plan_name": plan["name"],
        "subscription_id": doc["id"],
    }


@router.delete(
    "/organizations/{org_id}/subscriptions/{module_key}",
    summary="Cancel active subscription for a module",
)
async def cancel_org_subscription(
    org_id: str,
    module_key: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Cancel the active subscription for an org+module.

    After cancellation the org falls back to the free tier for this module.
    """
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    existing = await subscription_repository.get_active_subscription(org_id, module_key)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active subscription for module '{module_key}'",
        )

    plan = await subscription_repository.get_pricing_plan(existing["pricing_plan_id"])
    await subscription_repository.cancel_subscription(existing["id"])

    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_cancel_subscription",
        resource_type="module_subscription",
        resource_id=f"{org_id}::{module_key}",
        details={
            "org_name": org_doc.get("name"),
            "module_key": module_key,
            "cancelled_plan": plan["name"] if plan else "Unknown",
        },
    ))

    return {"ok": True, "org_id": org_id, "module_key": module_key}


# ══════════════════════════════════════════════════════════════════════════════
# Migration — Organization.plan → module_subscriptions (v4.0)
# ══════════════════════════════════════════════════════════════════════════════

# Maps legacy Organization.plan values to pricing plan slugs.
# Unknown/invalid plan values are skipped (conservative fallback to free).
_LEGACY_PLAN_SLUG_MAP = {
    "starter":    "ai_assistant_starter",
    "pro":        "ai_assistant_pro",
    "enterprise": "ai_assistant_enterprise",
}

_MIGRATION_MODULE_KEY = "ai_assistant"


@router.post(
    "/migrate/org-plans",
    summary="Migrate legacy Organization.plan to module_subscriptions (idempotent)",
)
async def migrate_org_plans(
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """One-time migration: for each org with a non-free legacy plan, create
    a module_subscription record for ai_assistant if one doesn't already exist.

    Idempotent: safe to re-run.

    Returns a detailed report with distinct categories:
      - migrated: subscription created successfully
      - skipped_free: org has no plan or plan="free" (nothing to do)
      - skipped_already_active: org already has an active subscription
      - skipped_unmapped_plan: org.plan value doesn't map to a known slug
      - errors: unexpected failures (missing seed data, DB errors)
    """
    import logging
    logger = logging.getLogger(__name__)

    all_orgs = await admin_repository.list_organizations(skip=0, limit=2000)

    migrated = 0
    skipped_free = 0
    skipped_already_active = 0
    skipped_unmapped_plan = 0
    errors = []

    for org_doc in all_orgs:
        org_id = org_doc["id"]
        org_name = org_doc.get("name", "?")
        org_plan = org_doc.get("plan")

        # ── No plan or free → nothing to migrate ────────────────────────
        if not org_plan or org_plan == "free":
            skipped_free += 1
            continue

        # ── Unknown plan value → conservative skip ──────────────────────
        slug = _LEGACY_PLAN_SLUG_MAP.get(org_plan)
        if not slug:
            logger.warning(
                "Migration: org '%s' (%s) has unmapped plan '%s' — "
                "treating as free (no subscription created).",
                org_id, org_name, org_plan,
            )
            skipped_unmapped_plan += 1
            continue

        # ── Already has active subscription → skip (idempotent) ─────────
        existing = await subscription_repository.get_active_subscription(
            org_id, _MIGRATION_MODULE_KEY,
        )
        if existing:
            skipped_already_active += 1
            continue

        # ── Lookup pricing plan by slug ─────────────────────────────────
        pricing_plan = await subscription_repository.get_pricing_plan_by_slug(
            _MIGRATION_MODULE_KEY, slug,
        )
        if not pricing_plan:
            err = (
                f"Pricing plan '{slug}' not found for org '{org_name}' "
                f"({org_id}) — ensure seed_pricing_plans_if_empty() ran."
            )
            logger.error("Migration: %s", err)
            errors.append(err)
            continue

        # ── Create subscription ─────────────────────────────────────────
        try:
            sub = ModuleSubscription(
                organization_id=org_id,
                module_key=_MIGRATION_MODULE_KEY,
                pricing_plan_id=pricing_plan["id"],
                assigned_by="system_migration",
                notes=f"Migrated from legacy Organization.plan='{org_plan}'",
            )
            doc = sub.model_dump()
            doc["started_at"] = doc["started_at"].isoformat()
            doc["expires_at"] = None
            doc["cancelled_at"] = None
            doc["created_at"] = doc["created_at"].isoformat()
            doc["updated_at"] = doc["updated_at"].isoformat()
            await subscription_repository.create_subscription(doc)
            migrated += 1
            logger.info(
                "Migration: created ai_assistant subscription for org '%s' (%s), plan '%s'.",
                org_name, org_id, org_plan,
            )
        except Exception as e:
            err = f"Failed to create subscription for org '{org_name}' ({org_id}): {e}"
            logger.error("Migration: %s", err)
            errors.append(err)

    # ── Audit log ───────────────────────────────────────────────────────
    report = {
        "migrated": migrated,
        "skipped_free": skipped_free,
        "skipped_already_active": skipped_already_active,
        "skipped_unmapped_plan": skipped_unmapped_plan,
        "errors": errors,
    }

    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_migrate_org_plans",
        resource_type="system",
        resource_id=None,
        details={
            "migrated": migrated,
            "skipped_free": skipped_free,
            "skipped_already_active": skipped_already_active,
            "skipped_unmapped_plan": skipped_unmapped_plan,
            "errors_count": len(errors),
        },
    ))

    return report


# ══════════════════════════════════════════════════════════════════════════════
# Commercial Plan Admin (v5.0)
# ══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/commercial-plans",
    summary="List all commercial plans (admin catalog view)",
)
async def list_commercial_plans(
    _: dict = Depends(require_system_admin),
) -> list:
    """Return all commercial plans (including non-public).

    Unlike /billing/plans (public), this returns Stripe IDs and all fields.
    """
    return await billing_repository.list_commercial_plans(public_only=False)


@router.put(
    "/organizations/{org_id}/commercial-plan",
    summary="Admin: set commercial plan for an organization",
)
async def admin_set_commercial_plan(
    org_id: str,
    body: OrgCommercialPlanUpdate,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Change an organization's commercial plan via admin override.

    This provisions all module subscriptions according to the plan's module_plans
    mapping, with billing_status="manual" (no Stripe involvement).

    v5.8 / Onda 10 Step B.3 — Plan slug validation now reads from the DB
    `commercial_plans` collection (not the hardcoded VALID_COMMERCIAL_PLANS
    frozenset). Effect: a system_admin can create a brand-new plan slug
    via the admin Catalog UI (Step C.2 will provide the form), and this
    endpoint will accept it immediately — no codebase change, no redeploy.

    Validation rules:
      · plan must exist in `commercial_plans` collection
      · plan must NOT be archived (is_archived=True excluded)
      · addons cannot be assigned as main plans (is_addon=False required)

    Backward compat: pre-Onda 10 frontends that submit one of the legacy
    5 slugs (free/starter/core/pro/enterprise) continue to work unchanged.
    """
    # DB-driven validation
    from repositories import billing_repository as _br
    plan_doc = await _br.get_commercial_plan(body.commercial_plan_slug)
    if (
        not plan_doc
        or plan_doc.get("is_addon") is True
        or plan_doc.get("is_archived") is True
    ):
        # Build the error message from the live DB list so admins see the
        # current valid options (not a stale hardcoded set).
        valid_plans = await _br.list_commercial_plans(public_only=False)
        valid_slugs = sorted(
            p.get("slug") for p in valid_plans
            if p.get("slug")
            and not p.get("is_addon")
            and not p.get("is_archived")
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"commercial_plan_slug {body.commercial_plan_slug!r} is not a valid plan. "
                f"Valid options: {valid_slugs}"
            ),
        )

    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    previous_slug = org_doc.get("commercial_plan_slug", "free")

    try:
        result = await plan_provisioning.admin_set_plan(
            org_id=org_id,
            plan_slug=body.commercial_plan_slug,
            admin_user_id=current_user["user_id"],
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Audit log
    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_set_commercial_plan",
        resource_type="organization",
        resource_id=org_id,
        details={
            "org_name": org_doc.get("name"),
            "previous_plan": previous_slug,
            "new_plan": body.commercial_plan_slug,
            "notes": body.notes,
            "modules_provisioned": result.get("created", []),
        },
    ))

    return {
        "ok": True,
        "org_id": org_id,
        "commercial_plan_slug": body.commercial_plan_slug,
        "previous_plan": previous_slug,
        "modules_provisioned": result.get("created", []),
        "modules_cancelled": result.get("cancelled", 0),
    }


@router.get(
    "/organizations/{org_id}/billing",
    summary="Admin: billing summary for an organization",
)
async def admin_org_billing(
    org_id: str,
    _: dict = Depends(require_system_admin),
) -> dict:
    """Full billing summary for an organization.

    Includes commercial plan info, billing status, Stripe linkage,
    active module subscriptions with their entitlement limits.
    """
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    # Get active subscriptions with plan details
    subs = await subscription_repository.list_subscriptions_by_org(org_id)
    enriched_subs = []
    for sub in subs:
        plan = await subscription_repository.get_pricing_plan(sub["pricing_plan_id"])
        enriched_subs.append({
            "module_key": sub["module_key"],
            "plan_name": plan["name"] if plan else "Unknown",
            "plan_slug": plan["slug"] if plan else "",
            "limits": plan.get("limits", {}) if plan else {},
            "status": sub["status"],
            "assigned_by": sub.get("assigned_by", ""),
            "commercial_plan_slug": sub.get("commercial_plan_slug"),
            "stripe_subscription_id": sub.get("stripe_subscription_id"),
        })

    # Get billing events
    events = await billing_repository.list_billing_events(org_id=org_id, limit=10)

    return {
        "org_id": org_id,
        "org_name": org_doc.get("name"),
        "commercial_plan_slug": org_doc.get("commercial_plan_slug", "free"),
        "billing_status": org_doc.get("billing_status", "none"),
        "billing_interval": org_doc.get("billing_interval"),
        "trial_ends_at": org_doc.get("trial_ends_at"),
        "current_period_end": org_doc.get("current_period_end"),
        "cancel_at_period_end": org_doc.get("cancel_at_period_end", False),
        "plan_assigned_by": org_doc.get("plan_assigned_by", "system"),
        "plan_assigned_at": org_doc.get("plan_assigned_at"),
        "stripe_customer_id": org_doc.get("stripe_customer_id"),
        "stripe_subscription_id": org_doc.get("stripe_subscription_id"),
        "billing_email": org_doc.get("billing_email"),
        "subscriptions": enriched_subs,
        "recent_billing_events": events,
    }


@router.get(
    "/billing-overview",
    summary="Admin: platform-wide billing overview",
)
async def admin_billing_overview(
    _: dict = Depends(require_system_admin),
) -> dict:
    """Platform-wide billing summary.

    Returns counts of orgs by plan, billing status distribution,
    and recent billing events.
    """
    all_orgs = await admin_repository.list_organizations(skip=0, limit=5000)

    plan_counts: dict = {}
    status_counts: dict = {}
    trialing = 0
    past_due = 0

    for org in all_orgs:
        slug = org.get("commercial_plan_slug", "free")
        plan_counts[slug] = plan_counts.get(slug, 0) + 1

        bs = org.get("billing_status", "none")
        status_counts[bs] = status_counts.get(bs, 0) + 1

        if bs == "trialing":
            trialing += 1
        elif bs == "past_due":
            past_due += 1

    # Get recent billing events (cross-org)
    recent_events = await billing_repository.list_billing_events(limit=20)

    return {
        "total_organizations": len(all_orgs),
        "plan_distribution": plan_counts,
        "billing_status_distribution": status_counts,
        "trialing_count": trialing,
        "past_due_count": past_due,
        "recent_billing_events": recent_events,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Billing Field Correction & Reconciliation (v5.2 hardening)
# ══════════════════════════════════════════════════════════════════════════════


@router.patch(
    "/organizations/{org_id}/billing-fields",
    summary="Admin: patch individual billing fields on an org",
)
async def admin_patch_billing_fields(
    org_id: str,
    body: OrgBillingFieldsPatch,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Directly correct individual billing metadata fields.

    Use this for state-drift recovery when a webhook was missed or applied
    incorrectly.  Only the fields present in the request body are applied;
    omitted fields are left untouched.

    Plan changes are NOT supported here — use PUT commercial-plan instead.
    """
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    # Build patch dict from non-None fields only
    patch = {
        field: value
        for field, value in body.model_dump().items()
        if value is not None and field in PATCHABLE_BILLING_FIELDS
    }
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No patchable fields provided",
        )

    # Record previous values for audit
    previous = {
        f: org_doc.get(f) for f in patch
    }

    await billing_repository.update_org_billing_fields(org_id, patch)

    # Audit log
    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_patch_billing_fields",
        resource_type="organization",
        resource_id=org_id,
        details={
            "org_name": org_doc.get("name"),
            "previous": previous,
            "applied": patch,
        },
    ))

    return {
        "ok": True,
        "org_id": org_id,
        "patched_fields": list(patch.keys()),
        "previous": previous,
        "applied": patch,
    }


@router.post(
    "/organizations/{org_id}/billing/reconcile",
    summary="Admin: reconcile internal billing state with Stripe",
)
async def admin_reconcile_billing(
    org_id: str,
    apply: bool = Query(False, description="Apply corrections (True) or dry-run (False)"),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Compare internal billing fields with the live Stripe subscription.

    By default this is a dry-run: returns the diff without applying changes.
    Pass ?apply=true to apply corrections.

    This endpoint:
      1. Reads the org's stripe_subscription_id
      2. Fetches the live Stripe subscription
      3. Compares billing_status, cancel_at_period_end, current_period_end, plan slug
      4. Returns diffs (and optionally applies them)
    """
    from services import stripe_service

    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    stripe_sub_id = org_doc.get("stripe_subscription_id")
    if not stripe_sub_id:
        return {
            "ok": True,
            "org_id": org_id,
            "reconciliation": "no_stripe_subscription",
            "message": "Org has no Stripe subscription linked — nothing to reconcile.",
        }

    # Fetch live Stripe subscription
    try:
        import asyncio
        stripe_mod = stripe_service._get_stripe()
        sub = await asyncio.to_thread(stripe_mod.Subscription.retrieve, stripe_sub_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Stripe subscription '{stripe_sub_id}': {e}",
        )

    # Extract Stripe state
    stripe_status = sub.get("status", "unknown")
    stripe_cancel = sub.get("cancel_at_period_end", False)
    stripe_period_end = None
    if sub.get("current_period_end"):
        from datetime import datetime as _dt, timezone as _tz
        stripe_period_end = _dt.fromtimestamp(
            sub["current_period_end"], tz=_tz.utc,
        ).isoformat()

    # Resolve plan slug from price
    stripe_plan_slug = None
    items = sub.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
        if price_id:
            commercial_plan = await billing_repository.get_commercial_plan_by_stripe_price(price_id)
            if commercial_plan:
                stripe_plan_slug = commercial_plan["slug"]

    # Build diff
    diffs = {}
    internal_status = org_doc.get("billing_status", "none")
    if internal_status != stripe_status:
        diffs["billing_status"] = {"internal": internal_status, "stripe": stripe_status}

    internal_cancel = org_doc.get("cancel_at_period_end", False)
    if internal_cancel != stripe_cancel:
        diffs["cancel_at_period_end"] = {"internal": internal_cancel, "stripe": stripe_cancel}

    internal_period_end = org_doc.get("current_period_end")
    if stripe_period_end and internal_period_end != stripe_period_end:
        diffs["current_period_end"] = {"internal": internal_period_end, "stripe": stripe_period_end}

    internal_plan = org_doc.get("commercial_plan_slug", "free")
    if stripe_plan_slug and internal_plan != stripe_plan_slug:
        diffs["commercial_plan_slug"] = {"internal": internal_plan, "stripe": stripe_plan_slug}

    result = {
        "ok": True,
        "org_id": org_id,
        "stripe_subscription_id": stripe_sub_id,
        "diffs": diffs,
        "in_sync": len(diffs) == 0,
        "applied": False,
    }

    if apply and diffs:
        # Apply metadata corrections (NOT plan changes — those need full reprovision)
        patch_fields = {}
        for field, values in diffs.items():
            if field == "commercial_plan_slug":
                # Plan changes require reprovision, not a field patch
                continue
            patch_fields[field] = values["stripe"]

        if patch_fields:
            await billing_repository.update_org_billing_fields(org_id, patch_fields)

        # If plan changed, reprovision through the canonical path
        if "commercial_plan_slug" in diffs:
            await plan_provisioning.provision_commercial_plan(
                org_id=org_id,
                plan_slug=diffs["commercial_plan_slug"]["stripe"],
                assigned_by=f"reconcile:admin:{current_user['user_id']}",
                stripe_subscription_id=stripe_sub_id,
                billing_status=stripe_status,
                current_period_end=(
                    _dt.fromtimestamp(sub["current_period_end"], tz=_tz.utc)
                    if sub.get("current_period_end") else None
                ),
            )

        result["applied"] = True

        # Audit log
        await audit_repository.create(AuditLog(
            organization_id=None,
            user_id=current_user["user_id"],
            action="admin_reconcile_billing",
            resource_type="organization",
            resource_id=org_id,
            details={
                "org_name": org_doc.get("name"),
                "diffs": diffs,
                "stripe_subscription_id": stripe_sub_id,
            },
        ))

    return result


# ── Controlled Access: Registration Mode & Platform Invites (v6.0) ────────────

from pydantic import BaseModel as _BaseModel


class RegistrationModeBody(_BaseModel):
    registration_mode: str  # "open" or "invite_only"


@router.get(
    "/settings/registration",
    summary="Get current registration mode",
)
async def get_registration_mode(
    current_user: dict = Depends(require_system_admin),
) -> dict:
    mode = await platform_settings_repository.get_registration_mode()
    return {"registration_mode": mode}


@router.put(
    "/settings/registration",
    summary="Set registration mode (open / invite_only)",
)
async def set_registration_mode(
    body: RegistrationModeBody,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    if body.registration_mode not in ("open", "invite_only"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="registration_mode must be 'open' or 'invite_only'",
        )

    old_mode = await platform_settings_repository.get_registration_mode()
    await platform_settings_repository.set_registration_mode(
        body.registration_mode, current_user["user_id"]
    )

    # Audit log
    try:
        await audit_repository.create(AuditLog(
            organization_id=None,
            user_id=current_user["user_id"],
            action="change_registration_mode",
            resource_type="platform_settings",
            resource_id="registration",
            details={
                "old_mode": old_mode,
                "new_mode": body.registration_mode,
            },
        ))
    except Exception:
        pass

    return {"registration_mode": body.registration_mode}


@router.post(
    "/invites",
    summary="Create a platform invitation for a new user",
    response_model=InviteResponse,
)
@limiter.limit("10/minute")
async def create_invite(
    request: Request,
    body: InviteCreate,
    current_user: dict = Depends(require_system_admin),
) -> InviteResponse:
    # Generate one-time token (plaintext sent via email, hash stored)
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    invite = Invite(
        email=body.email,
        token_hash=token_hash,
        created_by=current_user["user_id"],
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    await invite_repository.create(invite)

    invite_url = f"{APP_URL}/signup?invite={token}"

    # Send invite email (non-blocking, never raises)
    try:
        send_platform_invite(body.email, invite_url, locale=current_user.get("locale", "it"))
    except Exception:
        pass

    # Audit log
    try:
        await audit_repository.create(AuditLog(
            organization_id=None,
            user_id=current_user["user_id"],
            action="create_invite",
            resource_type="invite",
            resource_id=invite.id,
            details={"invited_email": body.email},
        ))
    except Exception:
        pass

    return InviteResponse(
        id=invite.id,
        email=invite.email,
        status=invite.status,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        invite_url=invite_url,
    )


@router.get(
    "/invites",
    summary="List all platform invitations",
    response_model=InviteListResponse,
)
async def list_invites(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_system_admin),
) -> InviteListResponse:
    items, total = await invite_repository.list_all(skip, limit)
    return InviteListResponse(
        items=[InviteResponse(**item) for item in items],
        total=total,
    )


@router.delete(
    "/invites/{invite_id}",
    summary="Revoke a pending platform invitation",
)
async def revoke_invite(
    invite_id: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    success = await invite_repository.revoke(invite_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite not found or already used/revoked",
        )

    # Audit log
    try:
        await audit_repository.create(AuditLog(
            organization_id=None,
            user_id=current_user["user_id"],
            action="revoke_invite",
            resource_type="invite",
            resource_id=invite_id,
        ))
    except Exception:
        pass

    return {"status": "revoked"}


# ══════════════════════════════════════════════════════════════════════════════
# Hard Delete (v6.1)
# ══════════════════════════════════════════════════════════════════════════════


@router.delete(
    "/organizations/{org_id}",
    summary="Admin: permanently delete an organization and ALL its data",
)
async def admin_hard_delete_organization(
    org_id: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Permanently delete an organization, all its users, and all associated data.

    This action is IRREVERSIBLE. It:
      1. Cancels any active Stripe subscription
      2. Deletes all org-scoped data (30+ collections)
      3. Deletes uploaded files (local + S3)
      4. Deletes all users belonging to the org
      5. Anonymizes audit logs
      6. Deletes the organization document
    """
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    org_name = org_doc.get("name", "unknown")

    # 1. Cancel Stripe subscription if present
    import os as _os
    stripe_sub_id = org_doc.get("stripe_subscription_id")
    if stripe_sub_id:
        try:
            import asyncio as _asyncio
            import stripe as _stripe
            _stripe.api_key = _os.environ.get("STRIPE_SECRET_KEY", "")
            if _stripe.api_key:
                await _asyncio.to_thread(_stripe.Subscription.cancel, stripe_sub_id)
        except Exception as e:
            # Log but don't block deletion
            import logging
            logging.getLogger(__name__).warning(
                "admin_hard_delete_org: failed to cancel Stripe sub %s: %s", stripe_sub_id, e
            )

    # 2. Audit log BEFORE deletion (data will be gone after)
    try:
        await audit_repository.create(AuditLog(
            organization_id=None,
            user_id=current_user["user_id"],
            action="admin_hard_delete_organization",
            resource_type="organization",
            resource_id=org_id,
            details={"org_name": org_name, "stripe_sub_cancelled": bool(stripe_sub_id)},
        ))
    except Exception:
        pass

    # 3. Cascade hard delete
    from services.hard_delete_service import cascade_hard_delete
    counts = await cascade_hard_delete(org_id)

    return {
        "ok": True,
        "org_id": org_id,
        "org_name": org_name,
        "deleted_counts": counts,
    }


@router.delete(
    "/users/{user_id}",
    summary="Admin: permanently delete a single user",
)
async def admin_hard_delete_user(
    user_id: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Permanently delete a single user.

    Guards:
      - Cannot delete system_admin users
      - Cannot delete the last admin of an organization (delete the org instead)

    Organization data is NOT affected — only the user document is removed.
    """
    user_doc = await user_repository.find_by_id(user_id)
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Guard: cannot delete system_admin
    if user_doc.get("role") == "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete a system administrator",
        )

    # Guard: cannot delete last admin of an org
    org_id = user_doc.get("organization_id")
    if org_id and user_doc.get("role") == "admin":
        org_admins = await admin_repository.list_users_all(
            org_id=org_id, role="admin", limit=10,
        )
        admin_count = sum(1 for u in org_admins if u.get("is_active", True) and u["id"] != user_id)
        if admin_count == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete the last admin of an organization. Delete the organization instead.",
            )

    email = user_doc.get("email", "unknown")

    # Audit log
    try:
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=current_user["user_id"],
            action="admin_hard_delete_user",
            resource_type="user",
            resource_id=user_id,
            details={"email": email, "role": user_doc.get("role"), "org_id": org_id},
        ))
    except Exception:
        pass

    # Wave 9.C.1 — GDPR-aware cleanup of AI artefacts owned by this user.
    # Two collections carry user-scoped data:
    #
    #   chat_sessions_collection   — DELETED (the messages array contains
    #                                  verbatim user-typed text = PII)
    #   ai_usage_events_collection — ANONYMIZED ($unset user_id) so that
    #                                  governance / cost analytics stay
    #                                  meaningful without retaining the
    #                                  link to a real person
    #
    # Both updates filter by (organization_id, user_id) which the existing
    # index on user_id covers (sparse, Wave 8A.1). Non-fatal: a failure
    # here is logged but does NOT abort user deletion.
    try:
        from database import chat_sessions_collection, ai_usage_events_collection
        chat_del = await chat_sessions_collection.delete_many(
            {"organization_id": org_id, "user_id": user_id}
        )
        ai_anon = await ai_usage_events_collection.update_many(
            {"organization_id": org_id, "user_id": user_id},
            {"$unset": {"user_id": ""}, "$set": {"user_id_anonymized_at": datetime.now(timezone.utc).isoformat()}},
        )
        import logging as _logging
        _logging.getLogger(__name__).info(
            "admin_hard_delete_user: cleaned AI artefacts for user=%s "
            "(chat_sessions deleted=%d, ai_usage_events anonymized=%d)",
            user_id, chat_del.deleted_count, ai_anon.modified_count,
        )
    except Exception as ai_cleanup_exc:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "admin_hard_delete_user: AI artefacts cleanup failed for "
            "user=%s: %s — proceeding with user deletion anyway",
            user_id, ai_cleanup_exc,
        )

    # Delete user
    await user_repository.delete(user_id)

    return {
        "ok": True,
        "deleted_user_id": user_id,
        "email": email,
    }


# ══════════════════════════════════════════════════════════════════════════════
# v5.8 / Onda 8 — System admin billing dashboard
# ══════════════════════════════════════════════════════════════════════════════
#
# 5 new endpoints exposing per-org and cross-org billing controls to system
# admins. All gated by require_system_admin and audit-logged. None modify
# Stripe state directly — they update DB state which the next Stripe sync
# (modify_subscription / billing_sweep) propagates outward.


# ── Per-org usage ────────────────────────────────────────────────────────────

@router.get(
    "/organizations/{org_id}/usage",
    summary="Quota usage + active add-ons for a specific org (system admin view)",
)
async def admin_org_usage(
    org_id: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Same shape as /api/billing/usage-summary, but scoped to any org by id.

    Lets system_admin see "X/Y this month" + active add-ons + the org's
    plan slug + legacy_pricing_lock flag for support / upselling decisions.
    Read-only.
    """
    from repositories import billing_repository
    from services.module_access import get_effective_limit
    from services.background_service import (
        _MONITORED_METRICS,
        _count_monthly_usage,
        _count_snapshot_usage,
    )
    # Onda 10 Step B.4 — use resolver for per-plan addon CTA override
    from services.quota_email_service import resolve_addon_for_metric

    org_doc = await billing_repository.get_org_billing_summary(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")
    _plan_slug_for_ctas = org_doc.get("commercial_plan_slug", "free")

    out_metrics = []
    for metric_key, module_key, is_monthly in _MONITORED_METRICS:
        try:
            limit = await get_effective_limit(org_id, module_key, metric_key)
        except Exception:
            limit = 0

        usage = (
            await _count_monthly_usage(org_id, module_key, metric_key)
            if is_monthly
            else await _count_snapshot_usage(org_id, module_key, metric_key)
        )

        if limit == -1:
            status_label = "unlimited"
            percentage = 0
        elif limit == 0:
            status_label = "off"
            percentage = 0
        else:
            ratio = usage / limit
            percentage = int(round(ratio * 100))
            if ratio >= 1: status_label = "exceeded"
            elif ratio >= 0.8: status_label = "warn"
            elif ratio >= 0.6: status_label = "info"
            else: status_label = "ok"

        out_metrics.append({
            "key": metric_key,
            "module": module_key,
            "used": usage,
            "limit": limit,
            "percentage": percentage,
            "status": status_label,
            "is_monthly": is_monthly,
            # Onda 10 Step B.4 — per-plan override aware
            "addon_slug": await resolve_addon_for_metric(metric_key, _plan_slug_for_ctas),
        })

    # Active addons (enriched)
    active_raw = await billing_repository.list_active_addons_for_org(org_id)
    active_addons = []
    for row in active_raw:
        plan = await billing_repository.get_commercial_plan(row["addon_slug"])
        if not plan:
            continue
        active_addons.append({
            "addon_slug": row["addon_slug"],
            "name": plan.get("name"),
            "quantity": row.get("quantity", 1),
            "price_monthly": plan.get("price_monthly", 0.0),
            "started_at": row.get("started_at"),
            "is_custom_override": row.get("is_custom_override", False),
        })

    # Recent quota notices for support context
    notices = await billing_repository.list_recent_quota_notices(org_id, months=3)

    return {
        "org_id": org_id,
        "metrics": out_metrics,
        "active_addons": active_addons,
        "recent_quota_notices": notices,
        "commercial_plan_slug": org_doc.get("commercial_plan_slug", "free"),
        "billing_status": org_doc.get("billing_status", "none"),
        "legacy_pricing_lock": bool(org_doc.get("legacy_pricing_lock")),
        "trial_ends_at": org_doc.get("trial_ends_at"),
        "current_period_end": org_doc.get("current_period_end"),
    }


# ── Custom plan creation (per-org override) ──────────────────────────────────

@router.post(
    "/organizations/{org_id}/custom-plan",
    summary="Create or update a custom CommercialPlan for one org (override limits/price)",
)
async def admin_create_custom_plan(
    org_id: str,
    body: dict = Body(...),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Create a custom CommercialPlan slug `custom_<orgid>_<ts>` with override
    fields, then assign it to the org via `admin_set_commercial_plan`.

    Body shape:
      {
        "template_slug": "core",
        "overrides": {
          "ai_assistant": {"chat": 500},
          "commerce":     {"orders_monthly": 5000}
        },
        "price_monthly_override": 49.0,        # optional
        "trial_days_override":    30,          # optional
        "notes":                  "Beta partner — strategic"
      }

    Behaviour:
      1. Loads the template plan (must exist + must be valid slug).
      2. Clones its module_plans + features + writes any overrides into
         a fresh `commerce_custom_*` PricingPlan row (per module touched
         by overrides) so existing PricingPlan slugs are untouched.
      3. Inserts a new CommercialPlan with `is_public=False`, slug
         = `custom_<orgid>_<unix>`.
      4. Audit-logs the operation.
      5. RETURNS the new commercial slug so the caller can call the
         existing `/admin/organizations/{org_id}/commercial-plan` to
         apply it (separate step keeps audit trail clean).

    Stripe is NOT modified here. The system_admin assigns the custom
    plan via the regular admin_set_commercial_plan endpoint, which sets
    `plan_assigned_by="admin:<user_id>"` so the webhook handler skips
    Stripe sync (already documented in `_handle_subscription_updated`).
    """
    from repositories import billing_repository, subscription_repository
    from models.common import generate_id, utc_now

    template_slug = body.get("template_slug")
    overrides = body.get("overrides") or {}
    price_override = body.get("price_monthly_override")
    trial_override = body.get("trial_days_override")
    notes = body.get("notes", "")

    if not template_slug:
        raise HTTPException(status_code=400, detail="template_slug is required")

    template = await billing_repository.get_commercial_plan(template_slug)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template plan '{template_slug}' not found")

    org = await billing_repository.get_org_billing_summary(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    ts = int(datetime.now(timezone.utc).timestamp())
    custom_slug = f"custom_{org_id[:8]}_{ts}"

    # Clone module_plans, then for each module with overrides create a
    # custom PricingPlan with the override limits.
    module_plans = dict(template.get("module_plans") or {})
    for module_key, override_limits in overrides.items():
        # Fetch the template's pricing plan for this module to inherit
        # all non-overridden limits.
        template_plan_slug = module_plans.get(module_key)
        if not template_plan_slug:
            continue
        template_plan = await subscription_repository.get_pricing_plan_by_slug(
            module_key=module_key, slug=template_plan_slug,
        )
        if not template_plan:
            continue

        merged_limits = {**(template_plan.get("limits") or {}), **override_limits}
        custom_plan_slug = f"{module_key}_custom_{org_id[:8]}_{ts}"
        custom_plan_doc = {
            "id": generate_id(),
            "module_key": module_key,
            "slug": custom_plan_slug,
            "name": f"Custom — {template_plan.get('name', module_key)}",
            "price_monthly": 0.0,        # bundled in commercial plan price
            "currency": "EUR",
            "limits": merged_limits,
            "is_active": True,
            "sort_order": 999,
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }
        await subscription_repository.insert_pricing_plan(custom_plan_doc)
        module_plans[module_key] = custom_plan_slug

    # Build CommercialPlan
    commercial_doc = {
        "id": generate_id(),
        "slug": custom_slug,
        "name": f"Custom — {template.get('name', template_slug)}",
        "description": template.get("description", "") + " (custom)",
        "tagline": notes or "Custom plan",
        "price_monthly": price_override if price_override is not None else template.get("price_monthly", 0.0),
        "price_yearly": template.get("price_yearly"),
        "currency": template.get("currency", "EUR"),
        "trial_days": trial_override if trial_override is not None else template.get("trial_days", 0),
        "is_public": False,             # custom plans never on public catalog
        "is_self_serve": False,
        "is_addon": False,
        "sort_order": 999,
        "module_plans": module_plans,
        "features_display": template.get("features_display", []),
        "stripe_product_id": None,      # custom plans don't have Stripe Product
        "stripe_price_id_monthly": None,
        "stripe_price_id_yearly": None,
        "created_at": utc_now().isoformat(),
        "updated_at": utc_now().isoformat(),
    }
    await billing_repository.upsert_commercial_plan(commercial_doc)

    # Audit log
    try:
        from repositories import audit_repository
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=current_user["user_id"],
            action="admin_create_custom_plan",
            resource_type="commercial_plan",
            resource_id=custom_slug,
            details={
                "template_slug": template_slug,
                "overrides": overrides,
                "price_monthly_override": price_override,
                "trial_days_override": trial_override,
                "notes": notes,
            },
        ))
    except Exception:
        pass

    return {
        "ok": True,
        "custom_plan_slug": custom_slug,
        "module_plans": module_plans,
        "next_step": (
            f"PUT /api/admin/organizations/{org_id}/commercial-plan with "
            f"slug='{custom_slug}' to assign this plan to the org."
        ),
    }


# ── Trial extension ──────────────────────────────────────────────────────────

@router.post(
    "/organizations/{org_id}/extend-trial",
    summary="Extend an org's trial_ends_at by N days (audit-logged)",
)
async def admin_extend_trial(
    org_id: str,
    body: dict = Body(...),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Add `extra_days` to `trial_ends_at`. Backend doesn't extend the
    Stripe trial — Stripe will still attempt to charge the card on its
    original trial_end. The local `trial_ends_at` extension covers the
    `module_access` billing gate (READ_ONLY_GRACE) so the customer keeps
    full access during the extension window even if Stripe deems the
    trial expired.

    Body: { "extra_days": int, "reason": str }

    Audit log entry: action="admin_extend_trial", details with
    {extra_days, reason, old_trial_ends_at, new_trial_ends_at}.
    """
    from repositories import billing_repository
    from database import organizations_collection
    from models.common import utc_now

    extra_days = int(body.get("extra_days", 0))
    reason = body.get("reason", "")

    if extra_days < 1 or extra_days > 365:
        raise HTTPException(status_code=400, detail="extra_days must be 1..365")
    if not reason:
        raise HTTPException(status_code=400, detail="reason is required for audit trail")

    org = await billing_repository.get_org_billing_summary(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    old_ends_at = org.get("trial_ends_at")
    # Compute new trial_ends_at: extend from current trial_ends_at if in the
    # future, else extend from now (catches expired trials being restored).
    base = datetime.now(timezone.utc)
    if old_ends_at:
        try:
            old_dt = datetime.fromisoformat(old_ends_at.replace("Z", "+00:00"))
            if old_dt.tzinfo is None:
                old_dt = old_dt.replace(tzinfo=timezone.utc)
            if old_dt > base:
                base = old_dt
        except (ValueError, TypeError):
            pass

    new_ends_at = (base + timedelta(days=extra_days)).isoformat()

    await organizations_collection.update_one(
        {"id": org_id},
        {"$set": {
            "trial_ends_at": new_ends_at,
            "billing_status": "trialing",  # restore status if expired
            "updated_at": utc_now().isoformat(),
        }},
    )

    # Audit log
    try:
        from repositories import audit_repository
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=current_user["user_id"],
            action="admin_extend_trial",
            resource_type="organization",
            resource_id=org_id,
            details={
                "extra_days": extra_days,
                "reason": reason,
                "old_trial_ends_at": old_ends_at,
                "new_trial_ends_at": new_ends_at,
            },
        ))
    except Exception:
        pass

    return {
        "ok": True,
        "old_trial_ends_at": old_ends_at,
        "new_trial_ends_at": new_ends_at,
        "extra_days": extra_days,
    }


# ── Impersonate (support tooling) ────────────────────────────────────────────

@router.post(
    "/organizations/{org_id}/impersonate",
    summary="Generate a short-lived JWT impersonating an admin of the org (30min TTL, audit-logged)",
)
async def admin_impersonate(
    org_id: str,
    request: Request,
    body: dict = Body(default={}),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Mint a JWT for the FIRST admin user of the org with TTL=30min, for
    support / debugging. The token includes:
      · sub        — target user id
      · org_id     — target org id
      · role       — target user's role
      · email      — target user's email
      · imp_by     — system_admin user id (audit trail in JWT itself)
      · iat / exp  — standard timestamps

    The frontend stores the token under a separate localStorage key so
    the system_admin's own session is preserved. Returning to the admin
    session is a frontend-only concern (just discard the impersonation
    token).

    Audit log entry: action="admin_impersonate", with target user id +
    impersonator id + reason (optional from body).
    """
    from auth import create_access_token
    from database import users_collection

    reason = (body or {}).get("reason", "")

    # Find the first active admin user of this org
    admin = await users_collection.find_one(
        {"organization_id": org_id, "role": "admin", "is_active": True},
        {"_id": 0, "id": 1, "email": 1, "role": 1, "name": 1},
        sort=[("created_at", 1)],
    )
    if not admin:
        raise HTTPException(
            status_code=404,
            detail="No active admin user found for this organization",
        )

    # Mint a token with 30min TTL (configurable via JWT settings; we hard-
    # code 30 here for safety regardless of platform JWT_TTL).
    token = create_access_token(
        data={
            "sub": admin["id"],
            "org_id": org_id,
            "role": admin["role"],
            "email": admin["email"],
            "imp_by": current_user["user_id"],
        },
        expires_delta=timedelta(minutes=30),
    )

    # Audit log
    try:
        from repositories import audit_repository
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=current_user["user_id"],
            action="admin_impersonate",
            resource_type="user",
            resource_id=admin["id"],
            details={
                "target_user_id": admin["id"],
                "target_email": admin["email"],
                "reason": reason,
                "ttl_minutes": 30,
                "request_ip": request.client.host if request.client else None,
            },
        ))
    except Exception:
        pass

    return {
        "ok": True,
        "access_token": token,
        "token_type": "bearer",
        "ttl_minutes": 30,
        "target_user": {
            "id": admin["id"],
            "email": admin["email"],
            "name": admin.get("name"),
            "role": admin["role"],
        },
    }


# ── MRR / churn cross-org dashboard ──────────────────────────────────────────

@router.get(
    "/billing-overview/mrr",
    summary="MRR + churn timeline + upselling candidates (cross-org, system admin)",
)
async def admin_mrr_overview(
    months: int = Query(default=6, ge=1, le=24),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Aggregate billing health across all orgs. Returns:

      · `mrr_current`       — sum of price_monthly for active subs +
                               sum of price_monthly per addon × quantity
      · `mrr_by_plan`       — breakdown { plan_slug: mrr }
      · `mrr_by_addon`      — breakdown { addon_slug: mrr }
      · `active_subs_count` — count of active main-plan subs
      · `active_addons_count` — count of active AddonSubscription rows
      · `churn_30d`         — count of subs canceled in the last 30 days
      · `upsell_candidates` — orgs with any metric ≥ 80% (sorted by MRR
                              ascending so highest-impact upsells first)

    All numbers are point-in-time snapshots; no historical timeseries
    (those would require sampling the data daily, which is out of scope
    for v5.8 onda 8). The system_admin can use these numbers for go-live
    decisions and as a sanity check pre/post deploy.
    """
    from repositories import billing_repository
    from database import organizations_collection, addon_subscriptions_collection

    # ── Active subs by plan ──────────────────────────────────────────────
    mrr_by_plan: dict = {}
    active_subs_count = 0
    cursor = organizations_collection.find(
        {
            "billing_status": {"$in": ["active", "trialing"]},
            "stripe_subscription_id": {"$ne": None},
        },
        {"_id": 0, "id": 1, "commercial_plan_slug": 1, "billing_interval": 1},
    )
    plan_price_cache: dict = {}
    async for org in cursor:
        active_subs_count += 1
        slug = org.get("commercial_plan_slug")
        if not slug:
            continue
        if slug not in plan_price_cache:
            plan = await billing_repository.get_commercial_plan(slug)
            plan_price_cache[slug] = (plan or {}).get("price_monthly", 0.0)
        # Yearly subs: amortise to monthly equivalent for MRR
        amount = plan_price_cache[slug]
        if org.get("billing_interval") == "year":
            # already monthly equivalent on the plan record; the yearly
            # discount is captured in the price_monthly field (callers
            # receive the discounted /month figure)
            pass
        mrr_by_plan[slug] = mrr_by_plan.get(slug, 0.0) + amount

    # ── Active addons MRR ────────────────────────────────────────────────
    mrr_by_addon: dict = {}
    active_addons_count = 0
    cursor = addon_subscriptions_collection.find(
        {"status": "active"},
        {"_id": 0, "addon_slug": 1, "quantity": 1},
    )
    addon_price_cache: dict = {}
    async for row in cursor:
        active_addons_count += 1
        slug = row.get("addon_slug")
        qty = int(row.get("quantity", 1) or 1)
        if not slug:
            continue
        if slug not in addon_price_cache:
            plan = await billing_repository.get_commercial_plan(slug)
            addon_price_cache[slug] = (plan or {}).get("price_monthly", 0.0)
        mrr_by_addon[slug] = mrr_by_addon.get(slug, 0.0) + (addon_price_cache[slug] * qty)

    mrr_current = round(sum(mrr_by_plan.values()) + sum(mrr_by_addon.values()), 2)

    # ── Churn 30d (canceled subs) ────────────────────────────────────────
    churn_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    churn_30d = await organizations_collection.count_documents({
        "billing_status": "canceled",
        "updated_at": {"$gte": churn_cutoff},
    })

    # ── Upsell candidates ────────────────────────────────────────────────
    # Cheap heuristic: orgs that received a quota_warning notice in the
    # last 7 days. Not a real-time scan of every metric (too expensive
    # cross-org), but reuses the data we already store in
    # org_quota_notices.
    from database import org_quota_notices_collection
    recent_notice_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    cursor = org_quota_notices_collection.aggregate([
        {"$match": {"sent_at": {"$gte": recent_notice_cutoff}, "level": {"$in": ["warn_80", "exceeded"]}}},
        {"$group": {"_id": "$organization_id", "metrics_hit": {"$addToSet": "$metric_key"}, "last_sent": {"$max": "$sent_at"}}},
        {"$limit": 50},
    ])
    upsell_candidates = []
    async for row in cursor:
        org_id_target = row["_id"]
        org = await billing_repository.get_org_billing_summary(org_id_target) or {}
        upsell_candidates.append({
            "org_id": org_id_target,
            "commercial_plan_slug": org.get("commercial_plan_slug"),
            "metrics_hit": row["metrics_hit"],
            "last_sent": row["last_sent"],
        })

    return {
        "mrr_current": mrr_current,
        "mrr_by_plan": {k: round(v, 2) for k, v in mrr_by_plan.items()},
        "mrr_by_addon": {k: round(v, 2) for k, v in mrr_by_addon.items()},
        "active_subs_count": active_subs_count,
        "active_addons_count": active_addons_count,
        "churn_30d": churn_30d,
        "upsell_candidates": upsell_candidates,
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# v5.8 / Onda 9.A.2 — Admin manual add-on assignment & removal
# ============================================================================
#
# Allows a system_admin to grant/remove an add-on on any org WITHOUT going
# through Stripe. Useful for support comps, beta testers, manual contracts.
#
# These rows are flagged `is_custom_override=True` and `assigned_by="system_admin:<id>"`
# so the Stripe webhook (`reconcile_addons_with_stripe_items`) does not
# try to cancel them — that reconcile cursor filters by `stripe_subscription_id`
# (which is None for overrides), so they are naturally invisible to webhook
# convergence.
#
# Audit-logged via AuditLog with action="admin_assign_addon" / "admin_remove_addon".


@router.get(
    "/organizations/{org_id}/addons",
    summary="Admin: list active add-ons of any org (enriched)",
)
async def admin_list_org_addons(
    org_id: str,
    _: dict = Depends(require_system_admin),
) -> list:
    """Return the org's active add-ons, enriched with plan details.

    Same shape as the user-facing /billing/my-addons but scoped to any org.
    """
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    rows = await billing_repository.list_active_addons_for_org(org_id)
    out = []
    for row in rows:
        addon_plan = await billing_repository.get_commercial_plan(row["addon_slug"])
        if not addon_plan:
            continue
        out.append({
            "addon_slug": row["addon_slug"],
            "name": addon_plan.get("name", row["addon_slug"]),
            "quantity": row.get("quantity", 1),
            "price_monthly": addon_plan.get("price_monthly", 0.0),
            "currency": addon_plan.get("currency", "EUR"),
            "started_at": row.get("started_at"),
            "addon_provides": addon_plan.get("addon_provides") or {},
            "max_quantity": addon_plan.get("max_quantity", 1),
            "is_custom_override": row.get("is_custom_override", False),
            "assigned_by": row.get("assigned_by", ""),
            "notes": row.get("notes", ""),
            "stripe_subscription_id": row.get("stripe_subscription_id"),
        })
    return out


@router.post(
    "/organizations/{org_id}/addons",
    summary="Admin: assign an add-on to any org (custom override, no Stripe)",
)
async def admin_assign_addon(
    org_id: str,
    body: dict = Body(...),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Manually grant an add-on to an org without Stripe billing.

    Body: { "addon_slug": str, "quantity": int (default 1), "notes": str (optional), "reason": str }

    The add-on is flagged `is_custom_override=True` so the Stripe webhook
    reconcile path does not cancel it. If the org later subscribes via
    Stripe and adds the same add-on, the upsert will link the row to the
    Stripe subscription (acceptable convergence).

    Audit log entry: action="admin_assign_addon".
    """
    addon_slug = body.get("addon_slug", "")
    quantity = int(body.get("quantity", 1))
    notes = body.get("notes", "") or ""
    reason = body.get("reason", "") or ""

    if not addon_slug:
        raise HTTPException(status_code=400, detail="addon_slug is required")
    if not reason:
        raise HTTPException(status_code=400, detail="reason is required for audit trail")
    if quantity < 1:
        raise HTTPException(status_code=400, detail="quantity must be >= 1")

    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    addon_plan = await billing_repository.get_commercial_plan(addon_slug)
    if not addon_plan or not addon_plan.get("is_addon"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Add-on '{addon_slug}' not found",
        )

    max_q = addon_plan.get("max_quantity", 1)
    if quantity > max_q:
        raise HTTPException(
            status_code=400,
            detail=f"quantity {quantity} exceeds max_quantity {max_q}",
        )

    # Idempotent upsert with override flag
    new_id = await billing_repository.upsert_addon_subscription({
        "organization_id": org_id,
        "addon_slug": addon_slug,
        "quantity": quantity,
        "stripe_subscription_id": None,
        "stripe_subscription_item_id": None,
        "stripe_price_id": None,
        "is_custom_override": True,
        "assigned_by": f"system_admin:{current_user['user_id']}",
        "notes": notes or reason,
    })

    # Audit log
    try:
        await audit_repository.create(AuditLog(
            organization_id=None,
            user_id=current_user["user_id"],
            action="admin_assign_addon",
            resource_type="organization",
            resource_id=org_id,
            details={
                "org_name": org_doc.get("name"),
                "addon_slug": addon_slug,
                "quantity": quantity,
                "notes": notes,
                "reason": reason,
                "addon_subscription_id": new_id,
            },
        ))
    except Exception:
        pass

    return {
        "ok": True,
        "addon_subscription_id": new_id,
        "addon_slug": addon_slug,
        "quantity": quantity,
        "is_custom_override": True,
    }


@router.delete(
    "/organizations/{org_id}/addons/{addon_slug}",
    summary="Admin: remove an active add-on from any org",
)
async def admin_remove_addon(
    org_id: str,
    addon_slug: str,
    reason: str = Query(default="", description="Audit reason"),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Cancel an active add-on (custom override or Stripe-linked).

    For custom overrides: only marks the DB row cancelled.
    For Stripe-linked add-ons: ALSO does NOT call Stripe — admin is expected
    to use the Stripe Dashboard if they need to remove the Stripe item too.
    This endpoint is the "DB-only" override; full removal requires both.

    Returns 404 if the addon is not active on this org.
    Audit log entry: action="admin_remove_addon".
    """
    if not reason:
        raise HTTPException(status_code=400, detail="reason query param is required for audit trail")

    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    existing = await billing_repository.get_active_addon(org_id, addon_slug)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Add-on '{addon_slug}' is not active on this organization",
        )

    was_override = bool(existing.get("is_custom_override"))
    stripe_sub_id = existing.get("stripe_subscription_id")

    ok = await billing_repository.cancel_addon_subscription(org_id, addon_slug)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to cancel addon")

    # Audit log
    try:
        await audit_repository.create(AuditLog(
            organization_id=None,
            user_id=current_user["user_id"],
            action="admin_remove_addon",
            resource_type="organization",
            resource_id=org_id,
            details={
                "org_name": org_doc.get("name"),
                "addon_slug": addon_slug,
                "was_custom_override": was_override,
                "stripe_subscription_id": stripe_sub_id,
                "reason": reason,
            },
        ))
    except Exception:
        pass

    return {
        "ok": True,
        "addon_slug": addon_slug,
        "was_custom_override": was_override,
        "stripe_warning": (
            None if was_override else
            "This add-on was linked to a Stripe subscription. The DB row is "
            "cancelled but the Stripe item is still active — use the Stripe "
            "Dashboard if you also need to stop billing."
        ),
    }


# ============================================================================
# v5.8 / Onda 9.T — Trial-once admin override + history
# ============================================================================
#
# Lets system_admin reset has_used_trial=False for a specific org so that org
# can use the trial again. Use cases:
#   - Customer support comp ("user lost data, give them another shot")
#   - Partner / beta program ("give this org a fresh trial")
#   - Refund + restart scenarios
#
# Audit-logged with required reason. The trial_history[] is preserved
# (showing the historical trials) so the admin can see prior attempts before
# granting the override.


@router.post(
    "/organizations/{org_id}/grant-trial",
    summary="Admin: reset has_used_trial to allow another trial (audit-logged)",
)
async def admin_grant_trial(
    org_id: str,
    body: dict = Body(...),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Reset has_used_trial=False for an org so they can use a trial again.

    Body: { "reason": str }   ← required for audit

    Effect:
      - has_used_trial → False (next checkout includes trial_period_days)
      - has_used_trial_at and has_used_trial_plan_slug PRESERVED for context
      - trial_history[] PRESERVED (audit trail of prior trials)
      - AuditLog entry: action="admin_grant_trial"

    The next time the user starts a Checkout Session for any plan with
    trial_days > 0, they will receive the full trial period.
    """
    reason = (body.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="reason is required for audit trail")

    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail=f"Organization '{org_id}' not found")

    previous_state = {
        "has_used_trial": org_doc.get("has_used_trial", False),
        "has_used_trial_at": org_doc.get("has_used_trial_at"),
        "has_used_trial_plan_slug": org_doc.get("has_used_trial_plan_slug"),
        "trial_history_count": len(org_doc.get("trial_history") or []),
    }

    await billing_repository.grant_trial_override(
        organization_id=org_id,
        admin_user_id=current_user["user_id"],
        reason=reason,
    )

    # Audit log
    try:
        await audit_repository.create(AuditLog(
            organization_id=None,
            user_id=current_user["user_id"],
            action="admin_grant_trial",
            resource_type="organization",
            resource_id=org_id,
            details={
                "org_name": org_doc.get("name"),
                "reason": reason,
                "previous_state": previous_state,
            },
        ))
    except Exception:
        pass

    return {
        "ok": True,
        "org_id": org_id,
        "previous_state": previous_state,
        "current_state": {
            "has_used_trial": False,
            "trial_history_preserved": True,
        },
        "next_checkout_will_include_trial": True,
    }


@router.get(
    "/organizations/{org_id}/trial-history",
    summary="Admin: full trial history for an org (analytics + support)",
)
async def admin_get_trial_history(
    org_id: str,
    _: dict = Depends(require_system_admin),
) -> dict:
    """Return the org's trial_history[] with summary stats for support context."""
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail=f"Organization '{org_id}' not found")

    history = await billing_repository.get_trial_history(org_id)

    # Summary stats
    total = len(history)
    converted = sum(1 for h in history if h.get("outcome") == "converted")
    cancelled = sum(1 for h in history if h.get("outcome") == "cancelled_during_trial")
    expired = sum(1 for h in history if h.get("outcome") == "expired_to_free")
    in_progress = sum(1 for h in history if not h.get("outcome"))

    return {
        "org_id": org_id,
        "org_name": org_doc.get("name"),
        "has_used_trial": org_doc.get("has_used_trial", False),
        "has_used_trial_at": org_doc.get("has_used_trial_at"),
        "has_used_trial_plan_slug": org_doc.get("has_used_trial_plan_slug"),
        "summary": {
            "total_trials": total,
            "converted": converted,
            "cancelled_during_trial": cancelled,
            "expired_to_free": expired,
            "in_progress": in_progress,
            "conversion_rate": round(converted / total, 2) if total > 0 else None,
        },
        "history": history,
    }



# ==============================================================================
# Onda 10 Step D.4 — Bulk admin actions
# ==============================================================================

class BulkActionRequest(_BaseModel):
    """Request body for POST /admin/bulk/{action}.

    Onda 10 Step D.4. Supports DRY-RUN and APPLY modes.

    Required fields:
      · action: one of `BULK_ACTIONS` from services.bulk_admin_service
      · filter_spec: dict with optional plan/billing_status/is_active/
                     min_inactivity_days
      · target_plan: required for downgrade_plan / migrate_plan actions

    Optional:
      · limit (default 200) — hard cap on rows scanned
      · dry_run (default True) — when False, actions are applied
    """
    action: str
    filter_spec: dict = {}
    target_plan: Optional[str] = None
    limit: int = 200
    dry_run: bool = True


@router.post(
    "/bulk/{action}",
    summary="Onda 10 Step D.4 — bulk admin action with dry-run by default",
)
async def admin_bulk_action(
    action: str,
    body: BulkActionRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Execute a bulk admin action against all matching orgs.

    Defaults to DRY-RUN. The response shows the orgs that WOULD be
    affected. To actually apply, re-call with `dry_run: false` in the body.

    Audit-logged per-org (one entry per applied action) when not dry-run.

    Examples:
      Migrate all Pro orgs to Solo:
        POST /admin/bulk/migrate_plan
        {"action":"migrate_plan", "filter_spec":{"plan":"pro"},
         "target_plan":"starter", "dry_run":true}

      Downgrade inactive Pro orgs (no login >30d) to free:
        POST /admin/bulk/downgrade_plan
        {"action":"downgrade_plan",
         "filter_spec":{"plan":"pro","min_inactivity_days":30},
         "target_plan":"free", "dry_run":true}

      Reprovision all Pro orgs to current catalog:
        POST /admin/bulk/reprovision_to_catalog
        {"action":"reprovision_to_catalog",
         "filter_spec":{"plan":"pro"},
         "dry_run":true}
    """
    # Body action MUST match URL action for clarity
    if body.action != action:
        raise HTTPException(
            status_code=400,
            detail=f"Body action {body.action!r} does not match URL action {action!r}",
        )

    from services.bulk_admin_service import apply_action, BULK_ACTIONS
    if action not in BULK_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action {action!r}. Allowed: {sorted(BULK_ACTIONS)}",
        )

    actor = current_user.get("email") or current_user.get("user_id") or "system_admin"
    try:
        result = await apply_action(
            action=action,
            filter_spec=body.filter_spec,
            target_plan=body.target_plan,
            performed_by=actor,
            limit=body.limit,
            dry_run=body.dry_run,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Onda 10 Step E.2 — on-demand catalog drift audit
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/billing/audit-now",
    summary="Onda 10 Step E.2 — run the catalog drift audit immediately",
)
async def admin_billing_audit_now(
    _: dict = Depends(require_system_admin),
) -> dict:
    """Trigger the same scan that the daily cron runs (Step E.1).

    Returns the digest summary in real time:
      {scanned, high_issues, medium_issues, issues_per_org[], email_sent}

    Read-only against orgs/subs (no mutations). Useful from the admin UI
    to refresh the drift overview banner without waiting 24h. Will email
    the system_admin only if CATALOG_DRIFT_DIGEST_RECIPIENT is set AND
    HIGH issues are found, same policy as the cron tick.
    """
    from services.background_service import _run_catalog_drift_digest
    return await _run_catalog_drift_digest()


# ─────────────────────────────────────────────────────────────────────────────
# Onda 29 — Anti-bruteforce manual unlock (system_admin only)
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/customer-accounts/{customer_account_id}/unlock",
    summary="Onda 29 — manually unlock a customer account locked by anti-bruteforce",
)
async def admin_unlock_customer_account(
    customer_account_id: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Reset a customer account's lockout state (Onda 29).

    Use case: a legitimate customer is locked out (e.g. typo'd password
    repeatedly, then keeps hitting the auto-extending lockout) and
    can't recover via forgot-password (lost email access, etc.). The
    operator manually clears the state so the customer can retry.

    Effect (atomic $set on the customer_accounts doc):
      · failed_login_attempts = 0
      · locked_until = None
      · lockout_count_today = 0

    The customer's password is NOT touched — they must still enter
    the correct one. Just the rate-limit-style state is cleared.

    Audit: an entry is recorded in audit_logs with action
    "CUSTOMER_ACCOUNT_UNLOCKED" so we can trace who unlocked whom and
    when.

    Idempotent: safe to call on an already-unlocked account (matched=1
    if the doc exists, modified=0).

    Requires: role=system_admin (require_system_admin dependency).
    """
    from database import customer_accounts_collection, audit_logs_collection
    from models.common import generate_id, utc_now

    doc = await customer_accounts_collection.find_one(
        {"id": customer_account_id},
        {"_id": 0, "id": 1, "email": 1, "organization_id": 1,
         "failed_login_attempts": 1, "locked_until": 1,
         "lockout_count_today": 1},
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"customer_account_id {customer_account_id!r} not found",
        )

    res = await customer_accounts_collection.update_one(
        {"id": customer_account_id},
        {"$set": {
            "failed_login_attempts": 0,
            "locked_until": None,
            "lockout_count_today": 0,
        }},
    )

    # Audit log — record what was unlocked so we can trace operator actions.
    now_dt = utc_now()
    now = now_dt.isoformat()
    try:
        await audit_logs_collection.insert_one({
            "id": generate_id(),
            "actor_user_id": current_user.get("user_id"),
            "actor_role": "system_admin",
            "organization_id": doc.get("organization_id"),
            "action": "CUSTOMER_ACCOUNT_UNLOCKED",
            "target_type": "customer_account",
            "target_id": customer_account_id,
            "metadata": {
                "customer_email": doc.get("email"),
                "previous_state": {
                    "failed_login_attempts": doc.get("failed_login_attempts"),
                    "locked_until": doc.get("locked_until"),
                    "lockout_count_today": doc.get("lockout_count_today"),
                },
            },
            "created_at": now,
            # Phase 1 Step D3 — BSON Date for TTL index (auto-delete after 365 days)
            "expire_at": now_dt,
        })
    except Exception:
        # Audit failure should not break the unlock itself.
        pass

    return {
        "customer_account_id": customer_account_id,
        "email": doc.get("email"),
        "matched": res.matched_count,
        "modified": res.modified_count,
        "previous_state": {
            "failed_login_attempts": doc.get("failed_login_attempts"),
            "locked_until": doc.get("locked_until"),
            "lockout_count_today": doc.get("lockout_count_today"),
        },
        "unlocked_at": now,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Onda 30 — Anti-bruteforce manual unlock for admin/owner User
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/users/{user_id}/unlock",
    summary="Onda 30 — manually unlock an admin/owner User locked by anti-bruteforce",
)
async def admin_unlock_user(
    user_id: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Reset an admin/owner User's lockout state (Onda 30).

    Mirror of admin_unlock_customer_account (Onda 29 Step 5) but on
    users_collection instead of customer_accounts_collection.

    Use case: a legitimate admin / owner is locked out (mistyped
    password 5x, then keeps hitting the auto-extending lockout) and
    cannot recover via forgot-password (lost email access, etc.).
    The system_admin operator clears the lockout state so the
    affected user can retry.

    Effect (atomic $set):
      · failed_login_attempts = 0
      · locked_until = None
      · lockout_count_today = 0

    The user's password is NOT touched — they must still enter
    the correct one. Just the rate-limit-style state is cleared.

    Audit: an entry is recorded in audit_logs with action
    "USER_UNLOCKED" so we can trace which operator unlocked whom.

    Idempotent: safe to call on an already-unlocked user.

    Requires: role=system_admin. Org-level admins do NOT have
    access — User unlock is a platform-level operation since it
    can impact users across orgs.

    Note: system_admin Users themselves can never be locked
    (Onda 30 Step 2 bypass), so this endpoint will only ever be
    called on role in {admin, user}.
    """
    from database import users_collection, audit_logs_collection
    from models.common import generate_id, utc_now

    doc = await users_collection.find_one(
        {"id": user_id},
        {"_id": 0, "id": 1, "email": 1, "organization_id": 1, "role": 1,
         "failed_login_attempts": 1, "locked_until": 1,
         "lockout_count_today": 1},
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"user_id {user_id!r} not found",
        )

    res = await users_collection.update_one(
        {"id": user_id},
        {"$set": {
            "failed_login_attempts": 0,
            "locked_until": None,
            "lockout_count_today": 0,
        }},
    )

    # Audit log — record the operator action so we can trace it.
    now_dt = utc_now()
    now = now_dt.isoformat()
    try:
        await audit_logs_collection.insert_one({
            "id": generate_id(),
            "actor_user_id": current_user.get("user_id"),
            "actor_role": "system_admin",
            "organization_id": doc.get("organization_id"),
            "action": "USER_UNLOCKED",
            "target_type": "user",
            "target_id": user_id,
            "metadata": {
                "user_email": doc.get("email"),
                "user_role": doc.get("role"),
                "previous_state": {
                    "failed_login_attempts": doc.get("failed_login_attempts"),
                    "locked_until": doc.get("locked_until"),
                    "lockout_count_today": doc.get("lockout_count_today"),
                },
            },
            "created_at": now,
            # Phase 1 Step D3 — BSON Date for TTL index (auto-delete after 365 days)
            "expire_at": now_dt,
        })
    except Exception:
        # Audit failure should not break the unlock itself.
        pass

    return {
        "user_id": user_id,
        "email": doc.get("email"),
        "role": doc.get("role"),
        "matched": res.matched_count,
        "modified": res.modified_count,
        "previous_state": {
            "failed_login_attempts": doc.get("failed_login_attempts"),
            "locked_until": doc.get("locked_until"),
            "lockout_count_today": doc.get("lockout_count_today"),
        },
        "unlocked_at": now,
    }


# ══════════════════════════════════════════════════════════════════════════════
# AI Usage — Wave 1.7 (2026-05)
#
# Per-user AI usage and cost monitoring. Answers the question
# "who is consuming how many tokens, on which agent, costing how much
# this month?" that became impossible to answer in baseline because
# AIUsageEvent didn't have user_id.
#
# All amounts are aggregated in USD (the storage currency — Anthropic
# billing currency). Display layer / system_admin UI converts to the
# org's display currency at READ time via currency_service.
# ══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/ai-usage/by-user",
    summary="AI usage aggregated by (org, user) for a date range — Wave 1.7",
    description=(
        "Returns per-user AI consumption: total tokens, total cost (USD), "
        "event count, optionally filtered by org/user/agent. Used by the "
        "system admin dashboard to detect runaway consumers and to size "
        "Anthropic plan upgrades."
    ),
)
async def admin_ai_usage_by_user(
    org_id: Optional[str] = Query(default=None, description="Limit to a single org. None = all orgs."),
    user_id: Optional[str] = Query(default=None, description="Limit to a single user. None = all users."),
    agent_id: Optional[str] = Query(default=None, description="Limit to a single agent (e.g. financial_analyst)."),
    start_date: str = Query(..., description="ISO date inclusive (e.g. 2026-05-01)"),
    end_date: str = Query(..., description="ISO date inclusive (e.g. 2026-05-31)"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max rows returned."),
    _: dict = Depends(require_system_admin),
):
    """Aggregate AIUsageEvent rows by (organization_id, user_id, agent_id).

    Filters apply BEFORE aggregation. Output rows are sorted by total
    cost descending, so the highest-spending users surface first — the
    exact data the system_admin needs for capacity planning + abuse
    detection.

    Backward-compat: legacy events without user_id show up as a single
    row per org with user_id=null. They still represent real spend.
    """
    from database import ai_usage_events_collection

    # Build match filter
    match: dict = {
        "module_key": "ai_assistant",  # only AI events, not data_rows
        "created_at": {
            "$gte": start_date,
            "$lte": end_date + "T23:59:59",
        },
    }
    if org_id:
        match["organization_id"] = org_id
    if user_id:
        match["user_id"] = user_id
    if agent_id:
        match["agent_id"] = agent_id

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {
                    "organization_id": "$organization_id",
                    "user_id": "$user_id",
                    "agent_id": "$agent_id",
                    "feature": "$feature",
                },
                "events": {"$sum": 1},
                "tokens_in": {"$sum": {"$ifNull": ["$tokens_prompt", 0]}},
                "tokens_out": {"$sum": {"$ifNull": ["$tokens_completion", 0]}},
                "cost_usd": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
                # Track model versions seen for transparency
                "models": {"$addToSet": "$model_version"},
            }
        },
        {"$sort": {"cost_usd": -1}},
        {"$limit": limit},
    ]

    cursor = ai_usage_events_collection.aggregate(pipeline)
    rows = await cursor.to_list(length=limit)

    # Convert ObjectId/etc. to JSON-safe + flatten the _id group key
    result = []
    for r in rows:
        gid = r["_id"]
        result.append({
            "organization_id": gid.get("organization_id"),
            "user_id": gid.get("user_id"),
            "agent_id": gid.get("agent_id"),
            "feature": gid.get("feature"),
            "events": r["events"],
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
            "tokens_total": r["tokens_in"] + r["tokens_out"],
            "cost_usd": round(r["cost_usd"], 4),
            "models": sorted([m for m in r["models"] if m]),
        })

    # Wave 10.C.2 — enrich each row with organization_name + user_name
    # via a single batch lookup. The dashboard's "detail by user" table
    # is the place admins use to identify runaway consumers; showing
    # human names instead of truncated IDs is the highest-leverage UX
    # change in the whole Wave 10.C plan.
    if result:
        from database import organizations_collection, users_collection
        org_ids_present = list({r["organization_id"] for r in result if r.get("organization_id")})
        user_ids_present = list({r["user_id"] for r in result if r.get("user_id")})
        org_name_map = {}
        user_name_map = {}
        if org_ids_present:
            async for o in organizations_collection.find(
                {"id": {"$in": org_ids_present}},
                {"_id": 0, "id": 1, "name": 1},
            ):
                org_name_map[o["id"]] = o.get("name")
        if user_ids_present:
            async for u in users_collection.find(
                {"id": {"$in": user_ids_present}},
                {"_id": 0, "id": 1, "name": 1, "email": 1},
            ):
                user_name_map[u["id"]] = u.get("name") or u.get("email")
        for r in result:
            r["organization_name"] = org_name_map.get(r.get("organization_id"))
            r["user_name"] = user_name_map.get(r.get("user_id"))

    # Top-line totals across the filtered window
    totals = {
        "events": sum(r["events"] for r in result),
        "tokens_in": sum(r["tokens_in"] for r in result),
        "tokens_out": sum(r["tokens_out"] for r in result),
        "tokens_total": sum(r["tokens_total"] for r in result),
        "cost_usd": round(sum(r["cost_usd"] for r in result), 4),
    }

    return {
        "period": {"start": start_date, "end": end_date},
        "filters": {
            "org_id": org_id, "user_id": user_id, "agent_id": agent_id,
        },
        "rows_returned": len(result),
        "totals": totals,
        "rows": result,
    }


@router.get(
    "/ai-usage/summary",
    summary="AI usage top-line summary across all orgs — Wave 1.7",
    description=(
        "Returns the platform-wide AI spend totals + breakdown by org "
        "and by model_version. Used by the system admin for capacity "
        "planning and Anthropic tier sizing."
    ),
)
async def admin_ai_usage_summary(
    start_date: str = Query(..., description="ISO date inclusive"),
    end_date: str = Query(..., description="ISO date inclusive"),
    _: dict = Depends(require_system_admin),
):
    """Platform-wide AI spend rollup. Reports both per-org and per-model.

    Numbers are USD as stored. The frontend converts to the system_admin
    user's display currency at presentation time (the system_admin user
    has its own currency setting; we don't assume EUR).
    """
    from database import ai_usage_events_collection

    match = {
        "module_key": "ai_assistant",
        "created_at": {
            "$gte": start_date,
            "$lte": end_date + "T23:59:59",
        },
    }

    # By-org rollup
    by_org_pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$organization_id",
            "events": {"$sum": 1},
            "tokens_in": {"$sum": {"$ifNull": ["$tokens_prompt", 0]}},
            "tokens_out": {"$sum": {"$ifNull": ["$tokens_completion", 0]}},
            "cost_usd": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
            "distinct_users": {"$addToSet": "$user_id"},
        }},
        {"$sort": {"cost_usd": -1}},
        {"$limit": 50},
    ]
    by_org = []
    async for r in ai_usage_events_collection.aggregate(by_org_pipeline):
        by_org.append({
            "organization_id": r["_id"],
            "events": r["events"],
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
            "cost_usd": round(r["cost_usd"], 4),
            "distinct_users_count": len([u for u in r["distinct_users"] if u]),
        })

    # Wave 10.C.2 — enrich by_org with org_name so the dashboard can
    # show readable labels instead of opaque "org_5e2b3a..." truncations.
    # Single batch lookup, no N+1.
    if by_org:
        from database import organizations_collection
        org_ids_present = [r["organization_id"] for r in by_org if r.get("organization_id")]
        if org_ids_present:
            org_name_map = {}
            async for o in organizations_collection.find(
                {"id": {"$in": org_ids_present}},
                {"_id": 0, "id": 1, "name": 1},
            ):
                org_name_map[o["id"]] = o.get("name")
            for r in by_org:
                r["organization_name"] = org_name_map.get(r["organization_id"])

    # By-model rollup (helps detect when a costly model is overused)
    by_model_pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$model_version",
            "events": {"$sum": 1},
            "cost_usd": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
        }},
        {"$sort": {"cost_usd": -1}},
    ]
    by_model = []
    async for r in ai_usage_events_collection.aggregate(by_model_pipeline):
        by_model.append({
            "model_version": r["_id"] or "<unknown>",
            "events": r["events"],
            "cost_usd": round(r["cost_usd"], 4),
        })

    # Grand totals
    totals = {
        "events": sum(r["events"] for r in by_org),
        "cost_usd": round(sum(r["cost_usd"] for r in by_org), 4),
        "distinct_orgs": len(by_org),
    }

    return {
        "period": {"start": start_date, "end": end_date},
        "totals": totals,
        "by_org": by_org,
        "by_model": by_model,
    }


# ── Wave 8C.1 — Daily timeseries + feature breakdown for governance dashboard

@router.get(
    "/ai-usage/timeseries",
    summary="Daily AI spend timeseries + per-feature breakdown — Wave 8C.1",
    description=(
        "Returns a dense daily series of AI spend in the requested window, "
        "plus a roll-up by feature (chat / digest / health_explanation / ...) "
        "and by agent. Powers the governance dashboard line/area chart + "
        "feature mix pie."
    ),
)
async def admin_ai_usage_timeseries(
    start_date: str = Query(..., description="ISO date inclusive"),
    end_date: str = Query(..., description="ISO date inclusive"),
    org_id: Optional[str] = Query(default=None, description="Optional org filter"),
    _: dict = Depends(require_system_admin),
):
    """Per-day AI usage rollup + feature/agent breakdowns.

    The dashboard plots ``days[].cost_usd`` as a line/area to expose spend
    trends. ``by_feature`` and ``by_agent`` populate pie/bar mix charts.

    Missing days in the range are zero-filled so the chart never has gaps.
    """
    from database import ai_usage_events_collection
    from datetime import date as date_type, timedelta

    match: dict = {
        "module_key": "ai_assistant",
        "created_at": {
            "$gte": start_date,
            "$lte": end_date + "T23:59:59",
        },
    }
    if org_id:
        match["organization_id"] = org_id

    # Daily breakdown via $dateToString. created_at is stored as ISO string,
    # so we use $substr to slice "YYYY-MM-DD" off the front.
    daily_pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "events": {"$sum": 1},
            "tokens_in": {"$sum": {"$ifNull": ["$tokens_prompt", 0]}},
            "tokens_out": {"$sum": {"$ifNull": ["$tokens_completion", 0]}},
            "cache_read_tokens": {"$sum": {"$ifNull": ["$cache_read_tokens", 0]}},
            "cost_usd": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]
    daily_raw: dict = {}
    async for r in ai_usage_events_collection.aggregate(daily_pipeline):
        daily_raw[r["_id"]] = {
            "events": r["events"],
            "tokens_in": r["tokens_in"],
            "tokens_out": r["tokens_out"],
            "tokens_total": r["tokens_in"] + r["tokens_out"],
            "cache_read_tokens": r["cache_read_tokens"],
            "cost_usd": round(r["cost_usd"], 4),
        }

    # Zero-fill missing days for a gap-free chart
    try:
        d0 = date_type.fromisoformat(start_date)
        d1 = date_type.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    days = []
    cur = d0
    while cur <= d1:
        s = cur.isoformat()
        days.append({
            "date": s,
            **daily_raw.get(s, {
                "events": 0, "tokens_in": 0, "tokens_out": 0,
                "tokens_total": 0, "cache_read_tokens": 0, "cost_usd": 0,
            }),
        })
        cur += timedelta(days=1)

    # By-feature rollup
    by_feature_pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$feature",
            "events": {"$sum": 1},
            "cost_usd": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
            "tokens_total": {"$sum": {"$add": [
                {"$ifNull": ["$tokens_prompt", 0]},
                {"$ifNull": ["$tokens_completion", 0]},
            ]}},
        }},
        {"$sort": {"cost_usd": -1}},
    ]
    by_feature = []
    async for r in ai_usage_events_collection.aggregate(by_feature_pipeline):
        by_feature.append({
            "feature": r["_id"] or "<unknown>",
            "events": r["events"],
            "cost_usd": round(r["cost_usd"], 4),
            "tokens_total": r["tokens_total"],
        })

    # By-agent rollup
    by_agent_pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$agent_id",
            "events": {"$sum": 1},
            "cost_usd": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
        }},
        {"$sort": {"cost_usd": -1}},
    ]
    by_agent = []
    async for r in ai_usage_events_collection.aggregate(by_agent_pipeline):
        by_agent.append({
            "agent_id": r["_id"] or "<unknown>",
            "events": r["events"],
            "cost_usd": round(r["cost_usd"], 4),
        })

    # Top-line totals across the whole window (sum of days)
    totals = {
        "events": sum(d["events"] for d in days),
        "cost_usd": round(sum(d["cost_usd"] for d in days), 4),
        "tokens_total": sum(d["tokens_total"] for d in days),
        "cache_read_tokens": sum(d["cache_read_tokens"] for d in days),
    }
    # Cache hit ratio across the window (0 if no input tokens)
    total_input = sum(d["tokens_in"] for d in days)
    totals["cache_hit_ratio_pct"] = round(
        totals["cache_read_tokens"] / total_input * 100, 1
    ) if total_input > 0 else 0.0

    return {
        "period": {"start": start_date, "end": end_date},
        "filters": {"org_id": org_id},
        "totals": totals,
        "days": days,
        "by_feature": by_feature,
        "by_agent": by_agent,
    }


# ── Track O Step 1.4 — Audit log query API ─────────────────────────────
#
# Endpoint admin per browse audit_logs cross-org. Pre-O1.4 l'unico modo
# di vedere audit log era via mongosh diretto al DB. Per open beta serve
# UI / API-driven review (compliance + customer support).
#
# Index sfruttato: (organization_id, created_at) compound
# (database.py:429, Phase 1 Step D3).
#
# Pin: tests/test_invariants_security.py::TestSEC_O_1_4_AuditLogQueryAPI

from pydantic import BaseModel  # noqa: E402 — local import for the model below


class AuditLogItem(BaseModel):
    """Single audit log row (admin response — no _id leak)."""
    id: Optional[str] = None
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    actor_id: Optional[str] = None        # newer field (Track L1 erasure)
    actor_type: Optional[str] = None      # 'admin' | 'customer' | 'system'
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str                       # ISO string


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    skip: int
    limit: int


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    summary="Admin: query audit logs (cross-org or per-org filtered)",
)
async def list_audit_logs_endpoint(
    organization_id: Optional[str] = Query(
        None,
        description="Filter per single org. None = cross-org system-wide view.",
    ),
    action: Optional[str] = Query(
        None,
        description="Filter exact match on action field (es. 'login', 'gdpr_erasure_requested').",
    ),
    since: Optional[str] = Query(
        None,
        description="ISO datetime inclusive lower bound (es. '2026-05-01T00:00:00').",
    ),
    until: Optional[str] = Query(
        None,
        description="ISO datetime exclusive upper bound.",
    ),
    skip: int = Query(0, ge=0, description="Pagination offset."),
    limit: int = Query(100, ge=1, le=200, description="Max records (hard cap 200)."),
    _: dict = Depends(require_system_admin),
) -> AuditLogListResponse:
    """List audit_logs with filters + pagination (system_admin only).

    Tipici use case:
      - Customer support: filtra per organization_id + user_id (via action
        contesto) per debug "cosa ha fatto questo customer"
      - Compliance review: filtra per action='gdpr_erasure_requested' +
        date range per audit GDPR
      - Security forensics: cross-org filter su action='login' con
        since/until per investigare attacchi

    Performance:
      - organization_id + created_at sfruttano compound index esistente
        → O(log N) query anche con N >> 10M
      - count_documents O(N) per pagination total — limit 200 hard cap
        evita query gigantesche
    """
    total = await audit_repository.count_audit_logs(
        organization_id=organization_id,
        action=action,
        since=since,
        until=until,
    )
    docs = await audit_repository.list_audit_logs(
        organization_id=organization_id,
        action=action,
        since=since,
        until=until,
        skip=skip,
        limit=limit,
    )
    return AuditLogListResponse(
        items=[AuditLogItem(**d) for d in docs],
        total=total,
        skip=skip,
        limit=limit,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Track O Step 4.5 — Admin manual email verification (customer support recovery)
# ─────────────────────────────────────────────────────────────────────────────
#
# Use case (open beta scenarios reali):
#   1. Merchant signup → welcome email finita in spam folder → user dice
#      "non ricevo il link"; support verifica manualmente.
#   2. Customer signup → verification email su dominio con DMARC reject
#      eccessivo → email bouncing; support intervene.
#   3. Brevo down per 1h → email coda persa → manual unblock.
#
# Pre-O4.5: support poteva solo "rinvia email verifica" (gia' presente)
# MA se l'email non arriva mai (vedi sopra), user resta locked-out.
# Workaround precedente: console mongo manual update — rischio errore +
# nessun audit + lento.
#
# O4.5: endpoint admin gated system_admin che setta email_verified=True
# + audit log + optional reason field per forensic trail.


class AdminVerifyEmailRequest(BaseModel):
    """Body opzionale per admin email-verify endpoints.

    `reason` e' caldamente raccomandato (audit-quality), MA optional per
    non bloccare emergency unblock. Tipici valori:
      - "User reports email not received (spam folder check failed)"
      - "Brevo outage 2026-05-29 14:00-15:00 lost queue"
      - "DMARC reject from customer org domain — manual override"
    """
    reason: Optional[str] = None


@router.post(
    "/users/{user_id}/verify-email",
    summary="Track O 4.5 — manually mark a User's email as verified (support tool)",
)
async def admin_verify_user_email(
    user_id: str,
    body: AdminVerifyEmailRequest = AdminVerifyEmailRequest(),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Manually set email_verified=True on a merchant User.

    Use case: legitimate merchant cannot receive verification email
    (spam folder, Brevo bounce, DMARC issue) → support unblocks.

    Effect (atomic $set):
      · email_verified = True

    The user's password is NOT touched. Resend verification token is
    NOT cleared (cosi' user puo' ancora usare il link se arriva poi).

    Audit: action 'USER_EMAIL_VERIFIED_BY_ADMIN' con metadata che include
    operatore + reason + previous state.

    Idempotent: safe su user gia' verified (matched=1, modified=0).

    Requires: role=system_admin (cross-org operation).
    """
    from database import users_collection, audit_logs_collection
    from models.common import generate_id, utc_now

    doc = await users_collection.find_one(
        {"id": user_id},
        {"_id": 0, "id": 1, "email": 1, "organization_id": 1, "role": 1,
         "email_verified": 1},
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"user_id {user_id!r} not found",
        )

    previous_verified = doc.get("email_verified", False)

    res = await users_collection.update_one(
        {"id": user_id},
        {"$set": {"email_verified": True}},
    )

    now_dt = utc_now()
    now = now_dt.isoformat()
    try:
        await audit_logs_collection.insert_one({
            "id": generate_id(),
            "actor_user_id": current_user.get("user_id"),
            "actor_role": "system_admin",
            "organization_id": doc.get("organization_id"),
            "action": "USER_EMAIL_VERIFIED_BY_ADMIN",
            "target_type": "user",
            "target_id": user_id,
            "metadata": {
                "user_email": doc.get("email"),
                "user_role": doc.get("role"),
                "previous_verified": previous_verified,
                "reason": body.reason,
            },
            "created_at": now,
            # Phase 1 Step D3 — BSON Date per TTL index (auto-delete 365d)
            "expire_at": now_dt,
        })
    except Exception:
        # Audit fail non blocca l'override (priority: unblock user).
        pass

    return {
        "user_id": user_id,
        "email": doc.get("email"),
        "matched": res.matched_count,
        "modified": res.modified_count,
        "previous_verified": previous_verified,
        "verified_at": now,
        "reason": body.reason,
    }


@router.post(
    "/customer-accounts/{customer_account_id}/verify-email",
    summary="Track O 4.5 — manually mark a customer account's email as verified",
)
async def admin_verify_customer_account_email(
    customer_account_id: str,
    body: AdminVerifyEmailRequest = AdminVerifyEmailRequest(),
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Mirror di admin_verify_user_email ma su customer_accounts collection.

    Use case: customer di un merchant non riceve verification email →
    merchant chiede a support AFianco di unblock il proprio customer.
    System admin (NON merchant org_admin) puo' eseguire il flow:
    decisione consapevole — cross-org bypass = platform-level op, non
    delegable al merchant per evitare abuse.

    Effect: email_verified = True su customer_accounts doc.

    Audit: action 'CUSTOMER_ACCOUNT_EMAIL_VERIFIED_BY_ADMIN'.
    """
    from database import customer_accounts_collection, audit_logs_collection
    from models.common import generate_id, utc_now

    doc = await customer_accounts_collection.find_one(
        {"id": customer_account_id},
        {"_id": 0, "id": 1, "email": 1, "organization_id": 1,
         "email_verified": 1},
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"customer_account_id {customer_account_id!r} not found",
        )

    previous_verified = doc.get("email_verified", False)

    res = await customer_accounts_collection.update_one(
        {"id": customer_account_id},
        {"$set": {"email_verified": True}},
    )

    now_dt = utc_now()
    now = now_dt.isoformat()
    try:
        await audit_logs_collection.insert_one({
            "id": generate_id(),
            "actor_user_id": current_user.get("user_id"),
            "actor_role": "system_admin",
            "organization_id": doc.get("organization_id"),
            "action": "CUSTOMER_ACCOUNT_EMAIL_VERIFIED_BY_ADMIN",
            "target_type": "customer_account",
            "target_id": customer_account_id,
            "metadata": {
                "customer_email": doc.get("email"),
                "previous_verified": previous_verified,
                "reason": body.reason,
            },
            "created_at": now,
            "expire_at": now_dt,
        })
    except Exception:
        pass

    return {
        "customer_account_id": customer_account_id,
        "email": doc.get("email"),
        "matched": res.matched_count,
        "modified": res.modified_count,
        "previous_verified": previous_verified,
        "verified_at": now,
        "reason": body.reason,
    }
