"""AddonSubscription — per-org per-addon subscription record (v5.8 / Onda 3).

Tracks an active add-on (e.g. "+50 AI chat", "+200 orders") attached to an
organization's main subscription. One AddonSubscription per (org, addon_slug):
  · `add` action: insert new row (or reactivate cancelled one)
  · `remove` action: set status="cancelled"
  · `update_quantity` action: keep row, update `quantity` field

Why a separate collection instead of overloading `module_subscriptions`:
  · ModuleSubscription is per-module entitlement (1:1 with module_key).
  · AddonSubscription is orthogonal — many add-ons can co-exist without
    being tied to a single module (e.g. an addon could provide chat AI
    quota AND email pack quota in the future).
  · Keeping them separate means changes to add-on logic never touch the
    well-tested ModuleSubscription / module_access flows.

Stripe linkage:
  · Every active row carries `stripe_subscription_item_id` — the si_xxx
    inside the customer's main Stripe Subscription. The webhook handler
    (Onda 3) resolves these by reading sub.items.data[] and matching
    each item's metadata.addon_slug to a row here.
  · `stripe_subscription_id` (sub_xxx) is the parent — same as on
    ModuleSubscription. All add-ons of one org share the same parent.

Effective limit calculation (Onda 4):
  module_access.get_effective_limit(org, module, feature) sums:
    base_plan_limit + Σ(addon.quantity * addon_plan.addon_provides[module][feature])
  for every active AddonSubscription of the org. -1 (unlimited) on either
  side wins.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import generate_id, utc_now


class AddonSubscription(BaseModel):
    """An active add-on bought by an organization on top of its main plan.

    Rows are created via the webhook handler (`_handle_subscription_updated`)
    when Stripe reports new items. Direct creation in admin code paths is
    discouraged — go through `modify_subscription(addon_changes=...)` so the
    Stripe state remains the source of truth.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    addon_slug: str                              # FK to commercial_plans.slug (where is_addon=True)
    status: str = "active"                       # "active" | "cancelled" | "past_due"
    quantity: int = 1                            # stackable count (≤ addon.max_quantity)
    started_at: datetime = Field(default_factory=utc_now)
    cancelled_at: Optional[datetime] = None

    # ── Stripe linkage ────────────────────────────────────────────────────────
    # Both fields populated by webhook handler. Used for:
    #   · matching an existing item on remove/update_quantity in modify_subscription
    #   · rebuilding state from Stripe on billing_sweep / reconcile
    stripe_subscription_id: Optional[str] = None   # sub_xxx (shared with main plan)
    stripe_subscription_item_id: Optional[str] = None  # si_xxx (this addon's item)
    stripe_price_id: Optional[str] = None              # price_xxx (audit trail)

    # ── System admin override (Onda 8) ────────────────────────────────────────
    # When True, this AddonSubscription was created/granted via the system
    # admin UI without going through Stripe. The billing-status gate skips
    # over `is_custom_override=True` rows so a strategic partner can have an
    # add-on entitlement even with a free or manual main plan. Defaults to
    # False — the standard Stripe-driven path always sets this False.
    is_custom_override: bool = False

    # Audit
    assigned_by: str = "stripe_webhook"          # "stripe_webhook" | "system_admin:<user_id>"
    notes: str = ""                              # optional system_admin notes

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
