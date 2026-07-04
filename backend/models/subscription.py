"""ModuleSubscription — per-org per-module subscription record.

Links an organization to a specific PricingPlan for a given module_key.
An org may have at most one active subscription per module_key.

Statuses:
  "active"    — subscription is live, entitlements enforced
  "cancelled" — subscription was cancelled; entitlements revoked
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .common import generate_id, utc_now


class ModuleSubscription(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    module_key: str                              # e.g. "ai_assistant"
    pricing_plan_id: str                         # FK to pricing_plans.id
    status: str = "active"                       # "active" | "cancelled"
    started_at: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = None        # None = no expiry
    cancelled_at: Optional[datetime] = None
    assigned_by: str                             # user_id or "system_migration"
    notes: str = ""                              # optional admin notes

    # ── v5.0: Stripe linkage ──────────────────────────────────────────────────
    # All ModuleSubscriptions created from a single Stripe checkout share the
    # same stripe_subscription_id.  When Stripe cancels the subscription, all
    # linked ModuleSubscriptions are cancelled together.
    stripe_subscription_id: Optional[str] = None  # sub_xxx (shared across bundle)
    commercial_plan_slug: Optional[str] = None    # "core", "pro", etc. -- provenance

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
