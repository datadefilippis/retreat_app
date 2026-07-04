"""
admin.py — Response models for the System Admin control panel.

These models are used ONLY by routers/admin.py.
They are intentionally NOT re-exported from models/__init__.py to keep admin
models cleanly separated from the tenant-facing API surface.  Import directly:

    from models.admin import OrgSummary, OrgListResponse, ...
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Organizations ─────────────────────────────────────────────────────────────

class OrgSummary(BaseModel):
    """Lightweight organization row for the admin list view."""
    id: str
    name: str
    industry: Optional[str] = None
    plan: Optional[str] = None       # legacy "free" | "starter" | "pro" | "enterprise"
    timezone: Optional[str] = None
    currency: Optional[str] = None
    is_active: bool = True           # False = suspended by system admin (v3.0)
    # v5.0 billing fields
    commercial_plan_slug: str = "free"
    billing_status: str = "none"
    cancel_at_period_end: bool = False
    created_at: datetime
    updated_at: datetime


class OrgListResponse(BaseModel):
    items: List[OrgSummary]
    total: int
    skip: int
    limit: int


# ── Users (admin view) ────────────────────────────────────────────────────────

class UserAdminSummary(BaseModel):
    """User row for admin list and detail views.  password_hash never included."""
    id: str
    email: str
    name: str
    role: str                        # kept as str to avoid coupling with UserRole enum
    organization_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserListAdminResponse(BaseModel):
    items: List[UserAdminSummary]
    total: int
    skip: int
    limit: int


# ── Org detail (nested) ───────────────────────────────────────────────────────

class OrgModuleEntry(BaseModel):
    """Single module record as seen in org detail."""
    module_key: str
    is_active: bool
    activated_at: datetime
    activated_by: str               # user_id who activated


class OrgBillingInfo(BaseModel):
    """v5.0 billing information for an organization."""
    commercial_plan_slug: str = "free"
    billing_status: str = "none"
    billing_interval: Optional[str] = None
    trial_ends_at: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    plan_assigned_by: str = "system"
    plan_assigned_at: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    billing_email: Optional[str] = None


class OrgSubscriptionEntry(BaseModel):
    """Single module subscription as seen in org detail."""
    module_key: str
    pricing_plan_slug: str = ""
    pricing_plan_name: str = ""
    status: str = "active"
    started_at: Optional[datetime] = None
    assigned_by: str = ""
    commercial_plan_slug: Optional[str] = None
    stripe_subscription_id: Optional[str] = None


class OrgDetailResponse(BaseModel):
    """Full organization detail with embedded users, modules, and billing."""
    id: str
    name: str
    industry: Optional[str] = None
    plan: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    is_active: bool = True           # False = suspended (v3.0)
    created_at: datetime
    updated_at: datetime
    users: List[UserAdminSummary]   # all users in this org
    modules: List[OrgModuleEntry]   # all module records (active + inactive)
    # v5.0 billing
    billing: Optional[OrgBillingInfo] = None
    subscriptions: List[OrgSubscriptionEntry] = []


# ── Audit log ─────────────────────────────────────────────────────────────────

class AuditLogAdminEntry(BaseModel):
    id: str
    organization_id: Optional[str] = None  # None = system_admin action
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: List[AuditLogAdminEntry]
    total: int
    skip: int
    limit: int


# ── Write-action constants ─────────────────────────────────────────────────────

VALID_PLANS: frozenset = frozenset({"free", "starter", "core", "pro", "enterprise"})
VALID_COMMERCIAL_PLANS: frozenset = frozenset({"free", "starter", "core", "pro", "enterprise"})


# ── Write-action request bodies (v3.0) ────────────────────────────────────────

class OrgStatusUpdate(BaseModel):
    """Request body for suspend / reactivate organization."""
    is_active: bool


class OrgPlanUpdate(BaseModel):
    """Request body for legacy plan change. Validation against VALID_PLANS is done in the router."""
    plan: str


class OrgCommercialPlanUpdate(BaseModel):
    """Request body for v5.0 commercial plan change via admin."""
    commercial_plan_slug: str
    notes: str = ""


class UserStatusUpdate(BaseModel):
    """Request body for activate / deactivate user."""
    is_active: bool


# ── Write-action response bodies (v3.0) ───────────────────────────────────────

class PasswordResetResponse(BaseModel):
    """Response returned after an admin-initiated password reset."""
    temporary_password: str
    warning: str = (
        "This is a one-time temporary password. "
        "The user must change it immediately upon next login."
    )


# ── v5.2 Billing hardening request bodies ────────────────────────────────────

# Allowed fields for admin PATCH billing-fields endpoint.
# Intentionally limited to billing metadata — plan changes go through
# PUT /admin/organizations/{org_id}/commercial-plan instead.
PATCHABLE_BILLING_FIELDS: frozenset = frozenset({
    "billing_status",
    "billing_interval",
    "billing_email",
    "stripe_customer_id",
    "stripe_subscription_id",
    "cancel_at_period_end",
    "trial_ends_at",
    "current_period_end",
})


class OrgBillingFieldsPatch(BaseModel):
    """Request body for admin PATCH on individual billing fields.

    Only fields present in the request body are applied.
    Plan changes are NOT supported here — use PUT commercial-plan instead.
    """
    billing_status: Optional[str] = None
    billing_interval: Optional[str] = None
    billing_email: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None
    trial_ends_at: Optional[str] = None
    current_period_end: Optional[str] = None
