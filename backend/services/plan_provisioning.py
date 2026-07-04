"""Plan Provisioning Service -- the canonical entry point for ALL plan changes.

This service is the ONLY code that creates/cancels ModuleSubscriptions during
plan changes.  It bridges the gap between:
  - Commercial plans (user-facing bundles: Free/Core/Pro/Enterprise)
  - Module subscriptions (per-module entitlements read by module_access.py)

All callers (Stripe webhooks, admin panel, signup) go through this service.
Never create/cancel ModuleSubscriptions directly during plan changes.

Flow:
  1. Caller invokes provision_commercial_plan(org_id, plan_slug, ...)
  2. This service:
     a. Loads the CommercialPlan by slug
     b. Cancels all existing active ModuleSubscriptions for the org
     c. Creates new ModuleSubscriptions based on plan.module_plans
     d. Updates the Organization billing fields
  3. module_access.py picks up the new subscriptions automatically
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from models.common import utc_now
from models.subscription import ModuleSubscription
from repositories import billing_repository, subscription_repository

logger = logging.getLogger(__name__)


async def provision_commercial_plan(
    org_id: str,
    plan_slug: str,
    assigned_by: str,
    *,
    stripe_subscription_id: Optional[str] = None,
    billing_status: str = "manual",
    billing_interval: Optional[str] = None,
    trial_ends_at: Optional[datetime] = None,
    current_period_end: Optional[datetime] = None,
    notes: str = "",
) -> dict:
    """Provision a commercial plan for an organization.

    This is the CANONICAL entry point for all plan changes.

    Steps:
      1. Load the CommercialPlan from the catalog
      2. Cancel all existing active ModuleSubscriptions for this org
      3. Create new ModuleSubscriptions based on plan.module_plans
      4. Update the org billing fields

    Args:
        org_id: Organization ID.
        plan_slug: Commercial plan slug (e.g. "core", "pro").
        assigned_by: Who triggered the change ("stripe", "admin:<user_id>", "system", "signup").
        stripe_subscription_id: Stripe sub ID if this is a Stripe-driven change.
        billing_status: "active", "trialing", "manual", "none", etc.
        billing_interval: "month" or "year" (None for free/admin).
        trial_ends_at: When the trial ends (None if not trialing).
        current_period_end: When the current billing period ends.
        notes: Optional admin notes.

    Returns:
        Dict with provisioning summary.
    """
    # 1. Load commercial plan
    plan = await billing_repository.get_commercial_plan(plan_slug)
    if not plan:
        raise ValueError(f"Commercial plan '{plan_slug}' not found in catalog")

    # 2. Cancel all existing active subscriptions for this org
    existing_subs = await subscription_repository.list_subscriptions_by_org(org_id)
    cancelled_count = 0
    for sub in existing_subs:
        if sub.get("status") == "active":
            await subscription_repository.cancel_subscription(sub["id"])
            cancelled_count += 1

    # 3. Create new ModuleSubscriptions from plan.module_plans
    module_plans = plan.get("module_plans", {})
    created_subs = []

    for module_key, pricing_plan_slug in module_plans.items():
        # Look up the PricingPlan by module_key + slug
        pricing_plan = await subscription_repository.get_pricing_plan_by_slug(
            module_key, pricing_plan_slug,
        )
        if not pricing_plan:
            logger.warning(
                "PricingPlan '%s' not found for module '%s' -- skipping",
                pricing_plan_slug, module_key,
            )
            continue

        sub = ModuleSubscription(
            organization_id=org_id,
            module_key=module_key,
            pricing_plan_id=pricing_plan["id"],
            assigned_by=assigned_by,
            notes=notes or f"Provisioned via commercial plan '{plan_slug}'",
            stripe_subscription_id=stripe_subscription_id,
            commercial_plan_slug=plan_slug,
        )
        doc = sub.model_dump()
        # Serialize datetimes for MongoDB
        for dt_field in ("started_at", "expires_at", "cancelled_at", "created_at", "updated_at"):
            val = doc.get(dt_field)
            if isinstance(val, datetime):
                doc[dt_field] = val.isoformat()
        await subscription_repository.create_subscription(doc)
        created_subs.append({"module_key": module_key, "plan_slug": pricing_plan_slug})

    # 4. Update org billing fields
    now = utc_now()
    org_fields = {
        "commercial_plan_slug": plan_slug,
        "billing_status": billing_status,
        "billing_interval": billing_interval,
        "plan_assigned_by": assigned_by,
        "plan_assigned_at": now.isoformat(),
    }
    # Retreat fork — fee transazionale agganciata al piano: se il piano la
    # definisce, sovrascrive il campo org (unico punto letto dal checkout).
    # None = piano legacy che non governa la fee → il valore org resta.
    plan_fee = plan.get("transaction_fee_percent")
    if plan_fee is not None:
        org_fields["application_fee_percent"] = float(plan_fee)
    if stripe_subscription_id is not None:
        org_fields["stripe_subscription_id"] = stripe_subscription_id
    if trial_ends_at is not None:
        org_fields["trial_ends_at"] = trial_ends_at.isoformat()
    if current_period_end is not None:
        org_fields["current_period_end"] = current_period_end.isoformat()

    await billing_repository.update_org_billing_fields(org_id, org_fields)

    # 5. v5.8 / Onda 9.K — Reconcile commerce-quota-bound entities to the
    # new plan's effective limits. Currently handles stores; orders/products
    # stay enforced lazily at write-time (no need to retro-deactivate).
    #
    # Policy (Option B): if a downgrade reduces stores_max below the current
    # active count, deactivate the OVERFLOW stores (most-recent first) but
    # PRESERVE them in DB so a later upgrade can re-activate them. Likewise
    # an upgrade re-activates previously-deactivated stores up to the new
    # limit. This avoids data loss and the "stuck mid-downgrade" trap where
    # users couldn't change plan because they had too many stores.
    try:
        store_reconcile = await reconcile_stores_to_plan_limit(org_id)
    except Exception as e:
        # Best-effort: never block a plan change if store reconcile fails.
        # The store reconcile is a UX nicety, not a billing invariant.
        logger.warning("Store reconciliation failed for org=%s plan=%s: %s",
                       org_id, plan_slug, e)
        store_reconcile = {"error": str(e)}

    logger.info(
        "Provisioned plan '%s' for org '%s': cancelled %d subs, created %d subs (by: %s); store_reconcile=%s",
        plan_slug, org_id, cancelled_count, len(created_subs), assigned_by, store_reconcile,
    )

    return {
        "org_id": org_id,
        "plan_slug": plan_slug,
        "cancelled": cancelled_count,
        "created": created_subs,
        "store_reconcile": store_reconcile,
    }


async def reconcile_stores_to_plan_limit(org_id: str) -> dict:
    """Bring the org's active store count in line with the current plan's
    effective stores_max limit.

    Two cases:
      · Excess (active > limit): pick the most-recently-created stores
        beyond the limit (preserving the org's "original" stores) and
        flag them: is_active=False, deactivated_for_plan_violation=True,
        plan_violation_deactivated_at=<now>. The default store is always
        protected and never deactivated.
      · Headroom (active < limit AND deactivated_for_plan_violation rows
        exist): re-activate the longest-deactivated stores first (FIFO),
        up to the available headroom. Clears the flag.

    Special cases:
      · stores_max == -1 (unlimited): re-activate all previously
        plan-deactivated stores; never deactivate.
      · stores_max == 0 (Solo / Free): deactivate ALL non-default active
        stores (default store stays — it's the one bundled with sign-up
        and never counted against the limit per current product policy).

    Returns a counters dict for logging.
    """
    from database import stores_collection
    from services.module_access import get_effective_limit

    effective_max = await get_effective_limit(org_id, "commerce", "stores_max")
    now_iso = utc_now().isoformat()

    # Pull all stores for the org (small list — no pagination needed)
    cursor = stores_collection.find(
        {"organization_id": org_id},
        {"_id": 0, "id": 1, "is_active": 1, "is_default": 1, "created_at": 1,
         "deactivated_for_plan_violation": 1, "plan_violation_deactivated_at": 1},
    )
    stores = []
    async for s in cursor:
        stores.append(s)

    counters = {"deactivated": 0, "reactivated": 0, "skipped_default": 0,
                "current_active": 0, "effective_limit": effective_max}

    if not stores:
        return counters

    active = [s for s in stores if s.get("is_active", True)]
    plan_deactivated = [s for s in stores
                        if not s.get("is_active", True)
                        and s.get("deactivated_for_plan_violation")]

    # ── Case A: unlimited — reactivate everything previously plan-deactivated
    if effective_max == -1:
        for s in plan_deactivated:
            await stores_collection.update_one(
                {"id": s["id"]},
                {"$set": {
                    "is_active": True,
                    "deactivated_for_plan_violation": False,
                    "plan_violation_deactivated_at": None,
                    "updated_at": now_iso,
                }},
            )
            counters["reactivated"] += 1
        counters["current_active"] = len(active) + counters["reactivated"]
        return counters

    # ── Case B: excess — deactivate overflow (newest-first, default protected)
    if len(active) > effective_max:
        # Sort active by created_at DESC so the most-recent are deactivated first.
        # The default store is never deactivated.
        non_default_active = [s for s in active if not s.get("is_default")]
        # Sort by created_at desc; missing values sort last (treat as oldest)
        non_default_active.sort(key=lambda s: s.get("created_at") or "", reverse=True)

        # We want to keep `effective_max` stores active. The default counts as 1
        # if it exists, so deactivate (active - effective_max) from non_default.
        excess = len(active) - effective_max
        to_deactivate = non_default_active[:excess]

        # Edge case: even after picking only non-default, we may not have enough.
        # That can happen if effective_max == 0 and the org has a default store.
        # In that case we leave the default active anyway (Free / Solo orgs do
        # have a default store from signup; we don't tear it down).
        if effective_max == 0:
            counters["skipped_default"] = sum(1 for s in active if s.get("is_default"))

        for s in to_deactivate:
            await stores_collection.update_one(
                {"id": s["id"]},
                {"$set": {
                    "is_active": False,
                    "deactivated_for_plan_violation": True,
                    "plan_violation_deactivated_at": now_iso,
                    "updated_at": now_iso,
                }},
            )
            counters["deactivated"] += 1

    # ── Case C: headroom — reactivate previously-plan-deactivated (FIFO)
    elif len(active) < effective_max and plan_deactivated:
        headroom = effective_max - len(active)
        # Reactivate longest-deactivated first (oldest plan_violation_deactivated_at)
        plan_deactivated.sort(key=lambda s: s.get("plan_violation_deactivated_at") or "")
        to_reactivate = plan_deactivated[:headroom]
        for s in to_reactivate:
            await stores_collection.update_one(
                {"id": s["id"]},
                {"$set": {
                    "is_active": True,
                    "deactivated_for_plan_violation": False,
                    "plan_violation_deactivated_at": None,
                    "updated_at": now_iso,
                }},
            )
            counters["reactivated"] += 1

    counters["current_active"] = len(active) - counters["deactivated"] + counters["reactivated"]
    return counters


async def deprovision_stripe_subscription(
    org_id: str,
    stripe_subscription_id: str,
) -> int:
    """Cancel all module subscriptions linked to a Stripe subscription.

    Called from two paths (Onda 12):
      · Synchronously by services.stripe_service.cancel_subscription()
        right after a hard cancel succeeds on Stripe — guarantees the
        DB is consistent before the API response returns.
      · Asynchronously by the customer.subscription.deleted webhook
        handler (kept as a safety net for delayed/dropped sync calls
        and for cancellations triggered from outside the platform,
        e.g. Stripe Dashboard).

    Both paths now MUST tolerate being called twice for the same
    cancellation event. The idempotency guard below short-circuits if
    the org has already been reverted to free by an earlier caller —
    this prevents the original bug where a second call would create
    duplicate "active" free-tier ModuleSubscription rows.

    Also resets the org to the free plan.

    Returns the number of module subscriptions cancelled (0 when the
    idempotency guard kicks in).
    """
    # Onda 12 — idempotency guard: if a previous caller (sync or
    # webhook) already finished, exit cleanly. We trust the org doc
    # state because update_org_billing_fields below writes
    # commercial_plan_slug="free" + stripe_subscription_id=None
    # atomically (single $set), so any later caller that observes
    # both fields in their post-deprovision state can safely skip.
    org_summary = await billing_repository.get_org_billing_summary(org_id)
    if (
        org_summary
        and org_summary.get("commercial_plan_slug") == "free"
        and not org_summary.get("stripe_subscription_id")
    ):
        logger.info(
            "deprovision_stripe_subscription: org=%s sub=%s already "
            "deprovisioned, skipping (idempotent no-op).",
            org_id, stripe_subscription_id,
        )
        return 0

    cancelled = await billing_repository.cancel_subscriptions_by_stripe_sub(
        stripe_subscription_id,
    )

    # Reset org to free plan
    await billing_repository.update_org_billing_fields(org_id, {
        "commercial_plan_slug": "free",
        "billing_status": "canceled",
        "stripe_subscription_id": None,
        "billing_interval": None,
        "trial_ends_at": None,
        "current_period_end": None,
        "cancel_at_period_end": False,
        "plan_assigned_by": "stripe",
        "plan_assigned_at": utc_now().isoformat(),
    })

    # Provision free-tier module subscriptions
    free_plan = await billing_repository.get_commercial_plan("free")
    if free_plan:
        module_plans = free_plan.get("module_plans", {})
        for module_key, pricing_plan_slug in module_plans.items():
            pricing_plan = await subscription_repository.get_pricing_plan_by_slug(
                module_key, pricing_plan_slug,
            )
            if not pricing_plan:
                continue
            sub = ModuleSubscription(
                organization_id=org_id,
                module_key=module_key,
                pricing_plan_id=pricing_plan["id"],
                assigned_by="stripe",
                notes="Reverted to free after Stripe subscription deleted",
                commercial_plan_slug="free",
            )
            doc = sub.model_dump()
            for dt_field in ("started_at", "expires_at", "cancelled_at", "created_at", "updated_at"):
                val = doc.get(dt_field)
                if isinstance(val, datetime):
                    doc[dt_field] = val.isoformat()
            await subscription_repository.create_subscription(doc)

    logger.info(
        "Deprovisioned Stripe sub '%s' for org '%s': cancelled %d module subs, reverted to free",
        stripe_subscription_id, org_id, cancelled,
    )
    return cancelled


# v5.8 / Onda 9.Y.0.2 — terminal Stripe statuses that should trigger
# deprovision regardless of `new_plan_slug`. Stripe sometimes delivers
# `customer.subscription.updated` with a terminal status WITHOUT the
# matching `customer.subscription.deleted` event (delayed, dropped, or
# the sub stays at canceled/unpaid until period end). Without the line
# below, the metadata-only branch would update org fields but leave
# active module_subscriptions in place, granting Pro entitlements
# (e.g. cashflow_monitor.data_rows = -1) to a "canceled" tenant — a
# real-world drift confirmed by audit on 2026-04-30.
_TERMINAL_BILLING_STATUSES = frozenset({"canceled", "unpaid", "incomplete_expired"})


async def handle_subscription_updated(
    org_id: str,
    stripe_subscription_id: str,
    *,
    cancel_at_period_end: bool = False,
    current_period_end: Optional[datetime] = None,
    billing_status: str = "active",
    new_plan_slug: Optional[str] = None,
) -> dict:
    """Handle a Stripe subscription update (plan change or cancel-at-period-end).

    Behaviour matrix:
      · status terminal (canceled/unpaid/incomplete_expired) → deprovision
        (Onda 9.Y.0.2: closes the lifecycle drift window where module
         subs would survive a status-only cancellation)
      · plan changed                                          → reprovision
      · neither                                               → metadata-only

    Returns a dict describing the action taken.
    """
    # Get current org state
    org = await billing_repository.get_org_billing_summary(org_id)
    current_slug = org.get("commercial_plan_slug", "free") if org else "free"

    # Onda 9.Y.0.2 — Terminal status: deprovision module_subscriptions
    # tied to this stripe_subscription_id and revert org to free plan.
    # Same code path as the customer.subscription.deleted handler,
    # so we get the cancel + reset + provision-free triplet for free.
    if billing_status in _TERMINAL_BILLING_STATUSES:
        cancelled = await deprovision_stripe_subscription(
            org_id=org_id,
            stripe_subscription_id=stripe_subscription_id,
        )
        logger.info(
            "handle_subscription_updated: terminal status '%s' for org '%s' "
            "(stripe_sub=%s) → deprovisioned %d module subs",
            billing_status, org_id, stripe_subscription_id, cancelled,
        )
        return {
            "org_id": org_id,
            "action": "deprovisioned_terminal_status",
            "billing_status": billing_status,
            "module_subs_cancelled": cancelled,
        }

    # Plan change? Reprovision.
    if new_plan_slug and new_plan_slug != current_slug:
        result = await provision_commercial_plan(
            org_id=org_id,
            plan_slug=new_plan_slug,
            assigned_by="stripe",
            stripe_subscription_id=stripe_subscription_id,
            billing_status=billing_status,
            current_period_end=current_period_end,
        )
        # Also update cancel_at_period_end
        await billing_repository.update_org_billing_fields(org_id, {
            "cancel_at_period_end": cancel_at_period_end,
        })
        return {**result, "action": "plan_changed", "new_plan": new_plan_slug}

    # Metadata-only update (e.g. cancel_at_period_end toggled, or transient
    # active→past_due→active flap). Module subscriptions intentionally
    # untouched — this branch is for non-terminal mutations only.
    fields: dict = {
        "cancel_at_period_end": cancel_at_period_end,
        "billing_status": billing_status,
        "plan_assigned_by": "stripe",
    }
    if current_period_end:
        fields["current_period_end"] = current_period_end.isoformat()

    await billing_repository.update_org_billing_fields(org_id, fields)

    logger.info(
        "Updated billing metadata for org '%s': cancel_at_period_end=%s, status=%s",
        org_id, cancel_at_period_end, billing_status,
    )
    return {
        "org_id": org_id,
        "action": "metadata_updated",
        "cancel_at_period_end": cancel_at_period_end,
        "billing_status": billing_status,
    }


async def _cancel_org_stripe_subscription(org_id: str) -> Optional[str]:
    """Cancel active Stripe subscription for org, if any.

    Returns the cancelled subscription ID, or None if no active sub existed.
    Best-effort: logs warnings but never raises (admin action should not be
    blocked by Stripe failures).
    """
    org_doc = await billing_repository.get_org_billing_summary(org_id)
    stripe_sub_id = org_doc.get("stripe_subscription_id") if org_doc else None
    if not stripe_sub_id:
        return None
    try:
        import asyncio
        import stripe
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
        if stripe.api_key:
            await asyncio.to_thread(stripe.Subscription.cancel, stripe_sub_id)
            logger.info(
                "Cancelled Stripe sub %s for org %s (admin plan change)",
                stripe_sub_id, org_id,
            )
    except Exception as e:
        logger.warning(
            "Failed to cancel Stripe sub %s for org %s: %s",
            stripe_sub_id, org_id, e,
        )
    return stripe_sub_id


async def admin_set_plan(
    org_id: str,
    plan_slug: str,
    admin_user_id: str,
    notes: str = "",
) -> dict:
    """Admin manual plan override.

    Provisions the commercial plan with billing_status="manual" and no Stripe
    linkage. If the org has an active Stripe subscription, it is cancelled
    BEFORE re-provisioning to prevent double billing.
    """
    # Cancel any active Stripe subscription BEFORE re-provisioning
    cancelled_sub = await _cancel_org_stripe_subscription(org_id)

    result = await provision_commercial_plan(
        org_id=org_id,
        plan_slug=plan_slug,
        assigned_by=f"admin:{admin_user_id}",
        billing_status="manual",
        notes=notes or f"Admin override by {admin_user_id}",
    )

    # Clear Stripe fields since this is now a manual override
    await billing_repository.update_org_billing_fields(org_id, {
        "stripe_subscription_id": None,
        "cancel_at_period_end": False,
    })

    if cancelled_sub:
        result["cancelled_stripe_sub"] = cancelled_sub
    return result
