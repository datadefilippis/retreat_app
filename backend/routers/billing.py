"""
routers/billing.py
==================
Public and authenticated billing endpoints.

Routes:
  GET  /billing/plans            — public plan catalog
  GET  /billing/config           — public Stripe publishable key
  GET  /billing/status           — authenticated billing status for current org
  POST /billing/checkout-session — create Stripe Checkout (org admin)
  POST /billing/portal-session   — create Stripe Customer Portal (org admin)
  POST /billing/verify-checkout  — verify & recover checkout completion (org admin, v5.7)
  POST /billing/webhooks         — Stripe webhook receiver (signature-only auth)
"""

import logging
import os
import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel

from auth import get_current_user, get_verified_user, require_admin
from repositories import billing_repository
from services import stripe_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


# -- Request / response models ------------------------------------------------

class CheckoutRequest(BaseModel):
    plan_slug: str
    interval: str = "month"  # "month" or "year"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PortalRequest(BaseModel):
    return_url: Optional[str] = None


class VerifyCheckoutRequest(BaseModel):
    session_id: str


# ==============================================================================
# Public endpoints
# ==============================================================================

@router.get(
    "/plans",
    summary="List public commercial plans",
)
async def list_plans() -> list:
    """Return all public commercial plans for the pricing page.

    v5.8 / Onda 10 Step A.3 — each plan is enriched with a `derived_limits`
    dict that resolves the actual limit values from the linked PricingPlan
    tiers (per module + feature_key). The frontend uses this for the
    plan-comparison matrix in PlansPage so the table reflects what
    `system_admin` has configured in the catalog, NOT a hardcoded snapshot.

    Shape of derived_limits:
        {
          "<module_key>": {
            "<feature_key>": <int>   # -1 unlimited, 0 disabled, >0 quota
          },
          "team": {"team_members": <int>},  # special: from _TEAM_LIMITS
        }

    If a tier referenced in module_plans cannot be resolved, the plan still
    returns but with that module's section empty (frontend treats unknown
    as "—" and logs to console for the admin to investigate).
    """
    from repositories import subscription_repository

    plans = await billing_repository.list_commercial_plans(public_only=True)

    # Onda 10 Step B.1 — team_members now lives in commercial_plans.
    # platform_limits. Hardcoded fallback for plans not yet migrated.
    _TEAM_LIMITS_FALLBACK = {"free": 1, "starter": 2, "core": 5, "pro": 15, "enterprise": -1}

    for plan in plans:
        # Strip internal Stripe IDs from public response
        plan.pop("stripe_product_id", None)
        plan.pop("stripe_price_id_monthly", None)
        plan.pop("stripe_price_id_yearly", None)

        # Onda 10 Step A.3 — Resolve derived limits from linked tiers.
        derived_limits: dict = {}
        module_plans = plan.get("module_plans") or {}
        for module_key, tier_slug in module_plans.items():
            try:
                tier = await subscription_repository.get_pricing_plan_by_slug(
                    module_key, tier_slug,
                )
            except Exception:
                tier = None
            if tier and isinstance(tier.get("limits"), dict):
                derived_limits[module_key] = dict(tier["limits"])
            else:
                derived_limits[module_key] = {}

        # Onda 10 Step B.1 — team_members from commercial_plans.platform_limits
        # (admin-editable). Falls back to legacy hardcoded dict if not yet set.
        slug = plan.get("slug") or "free"
        platform_limits = plan.get("platform_limits") or {}
        team_members_limit = platform_limits.get("team_members")
        if team_members_limit is None:
            team_members_limit = _TEAM_LIMITS_FALLBACK.get(slug, 1)
        derived_limits["team"] = {"team_members": team_members_limit}

        plan["derived_limits"] = derived_limits

    return plans


@router.get(
    "/config",
    summary="Public Stripe configuration",
)
async def billing_config() -> dict:
    """Return the Stripe publishable key for client-side initialization."""
    return {
        "stripe_publishable_key": os.environ.get("STRIPE_PUBLISHABLE_KEY", ""),
        "billing_enabled": bool(os.environ.get("STRIPE_SECRET_KEY")),
    }


# ==============================================================================
# Authenticated endpoints
# ==============================================================================

@router.get(
    "/status",
    summary="Current billing status for the authenticated user's org",
)
async def billing_status(
    current_user: dict = Depends(get_verified_user),
) -> dict:
    """Return the billing status for the current user's organization."""
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    summary = await billing_repository.get_org_billing_summary(org_id)
    if not summary:
        return {
            "commercial_plan_slug": "free",
            "billing_status": "none",
            "cancel_at_period_end": False,
            "has_had_trial": False,
        }

    return {
        "commercial_plan_slug": summary.get("commercial_plan_slug", "free"),
        "billing_status": summary.get("billing_status", "none"),
        "billing_interval": summary.get("billing_interval"),
        "trial_ends_at": summary.get("trial_ends_at"),
        "current_period_end": summary.get("current_period_end"),
        "cancel_at_period_end": summary.get("cancel_at_period_end", False),
        "plan_assigned_by": summary.get("plan_assigned_by", "system"),
        "has_stripe_customer": bool(summary.get("stripe_customer_id")),
        # v5.8 / Onda 9.T — `has_had_trial` is the field the frontend uses to
        # decide whether to show "Inizia prova gratis" vs "Abbonati" buttons.
        # Now backed by `has_used_trial` (immune to cancel-and-retry exploit).
        # Falls back to `trial_ends_at` for backward-compat with orgs that
        # were trialing BEFORE this migration ran (rare in prod).
        "has_had_trial": bool(summary.get("has_used_trial") or summary.get("trial_ends_at")),
        "has_used_trial": bool(summary.get("has_used_trial")),
        "has_used_trial_at": summary.get("has_used_trial_at"),
        "has_used_trial_plan_slug": summary.get("has_used_trial_plan_slug"),
        # v5.8 / Onda 5: surface the legacy lock so the UI can show
        # a "🔒 Legacy pricing" badge for grandfathered customers.
        "legacy_pricing_lock": bool(summary.get("legacy_pricing_lock")),
    }


# ==============================================================================
# v5.8 / Onda 7 — Usage summary endpoint
# ==============================================================================
#
# Single endpoint that returns "X/Y this month" for every monitored metric +
# the org's currently active add-ons. Powers the BillingSection UI dashboard
# and the QuotaProgressBanner per-page renders. Read-only / no side effects.

@router.get(
    "/usage-summary",
    summary="Current quota usage + active add-ons for the authenticated user's org",
)
async def billing_usage_summary(
    current_user: dict = Depends(get_verified_user),
) -> dict:
    """Return effective usage + limits + active add-ons for the org.

    Shape:
      {
        "metrics": [
          {"key": "chat", "module": "ai_assistant",
           "used": 52, "limit": 130, "percentage": 40, "status": "ok",
           "is_monthly": true, "addon_slug": "addon_ai_chat_pack"},
          ...
        ],
        "active_addons": [
          {"slug": "addon_ai_chat_pack", "name": "+50 AI chat",
           "quantity": 1, "price_monthly": 9.0, ...},
          ...
        ],
        "commercial_plan_slug": "core",
        "legacy_pricing_lock": false
      }

    Each `metric` entry includes:
      · `addon_slug` — the cheapest add-on slug that extends this metric,
        or null when no add-on exists. Lets the UI render context-aware
        "+ Pack X" CTAs without a second roundtrip.
      · `status` — "ok" (<60%), "info" (60-79%), "warn" (80-99%),
        "exceeded" (>=100%), "unlimited" (limit=-1), "off" (limit=0).

    Always returns 200 — even for orgs with no plan: an empty/zeroed
    structure renders the BillingSection with usable defaults.
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    from services.module_access import get_effective_limit
    from services.background_service import (
        _MONITORED_METRICS,
        _count_monthly_usage,
        _count_snapshot_usage,
    )
    # Onda 10 Step B.4 — use the resolver instead of the bare dict so
    # per-plan addon_ctas overrides take precedence.
    from services.quota_email_service import resolve_addon_for_metric

    # Resolve org's plan slug once for the addon CTAs
    _org_summary = await billing_repository.get_org_billing_summary(org_id) or {}
    _plan_slug_for_ctas = _org_summary.get("commercial_plan_slug", "free")

    out_metrics = []
    for metric_key, module_key, is_monthly in _MONITORED_METRICS:
        try:
            limit = await get_effective_limit(org_id, module_key, metric_key)
        except Exception:
            limit = 0

        if is_monthly:
            usage = await _count_monthly_usage(org_id, module_key, metric_key)
        else:
            usage = await _count_snapshot_usage(org_id, module_key, metric_key)

        # Status classification — mirrors QuotaProgressBanner thresholds
        if limit == -1:
            status_label = "unlimited"
            percentage = 0
        elif limit == 0:
            status_label = "off"
            percentage = 0
        else:
            ratio = usage / limit
            percentage = int(round(ratio * 100))
            if ratio >= 1:
                status_label = "exceeded"
            elif ratio >= 0.8:
                status_label = "warn"
            elif ratio >= 0.6:
                status_label = "info"
            else:
                status_label = "ok"

        out_metrics.append({
            "key": metric_key,
            "module": module_key,
            "used": usage,
            "limit": limit,
            "percentage": percentage,
            "status": status_label,
            "is_monthly": is_monthly,
            # Onda 10 Step B.4 — per-plan override resolution
            "addon_slug": await resolve_addon_for_metric(metric_key, _plan_slug_for_ctas),
        })

    # v5.8 / Onda 9.W — team_members is enforced in routers/organizations.py
    # via a hardcoded _TEAM_LIMITS dict (not in pricing_plans). Inject it here
    # so the dashboard surfaces team usage like the other counters.
    #
    # v5.8 / Onda 10 Step B.1 — Now read from
    # commercial_plans.platform_limits.team_members. Hardcoded fallback
    # kept for plan slugs not yet migrated to the catalog.
    summary = await billing_repository.get_org_billing_summary(org_id) or {}
    plan_slug = summary.get("commercial_plan_slug", "free")
    _TEAM_LIMITS_FALLBACK = {"free": 1, "starter": 2, "core": 5, "pro": 15, "enterprise": -1}
    plan_doc = await billing_repository.get_commercial_plan(plan_slug) or {}
    platform_limits = plan_doc.get("platform_limits") or {}
    team_limit = platform_limits.get("team_members")
    if team_limit is None:
        team_limit = _TEAM_LIMITS_FALLBACK.get(plan_slug, 1)
    try:
        from database import users_collection
        team_used = await users_collection.count_documents({
            "organization_id": org_id, "is_active": True,
        })
    except Exception:
        team_used = 0
    if team_limit == -1:
        team_status, team_pct = "unlimited", 0
    elif team_limit == 0:
        team_status, team_pct = "off", 0
    else:
        ratio = team_used / team_limit if team_limit else 0
        team_pct = int(round(ratio * 100))
        team_status = "exceeded" if ratio >= 1 else "warn" if ratio >= 0.8 else "info" if ratio >= 0.6 else "ok"
    out_metrics.append({
        "key": "team_members",
        "module": "team",
        "used": team_used,
        "limit": team_limit,
        "percentage": team_pct,
        "status": team_status,
        "is_monthly": False,
        "addon_slug": None,  # no team add-on at this point
    })

    # v5.8 / Onda 9.W — Boolean feature flags (NOT counters).
    # These are sì/no features (alert_analysis, health_explanation, email_*, export, alert_config,
    # stripe_connect). Showing them as quotas is misleading — they belong in
    # a separate "features included" section. For each, return:
    #   { key, module, included: bool, requires_plan: str (next plan that includes) }
    # Frontend renders as a checklist with upgrade CTA on locked items.
    features = []
    feature_specs = [
        # (feature_key, module_key, label_i18n_key, requires_plan_for_upgrade_cta)
        ("alert_analysis",     "ai_assistant",     "alert_analysis",     "core"),
        ("health_explanation", "ai_assistant",     "health_explanation", "core"),
        ("email_alerts",       "cashflow_monitor", "email_alerts",       "starter"),
        ("email_digest",       "cashflow_monitor", "email_digest",       "starter"),
        ("alert_config",       "cashflow_monitor", "alert_config",       "starter"),
        ("export",             "cashflow_monitor", "export",             "starter"),
        ("checkout_stripe",    "commerce",         "checkout_stripe",    "core"),
        # Consolidamento WS-2 (retreat) — feature-key per il gating fine del
        # menu: canUse() è ottimista sulle chiavi ignote, quindi DEVONO
        # passare dal summary per poter nascondere le voci.
        ("suppliers",          "cashflow_monitor", "suppliers",          "starter"),
        ("data_quality",       "cashflow_monitor", "data_quality",       "starter"),
        ("rentals",            "commerce",         "rentals",            "core"),
    ]
    for feat_key, mod_key, label_key, requires_plan in feature_specs:
        try:
            limit_val = await get_effective_limit(org_id, mod_key, feat_key)
        except Exception:
            limit_val = 0
        # Boolean semantics: -1 (unlimited) or > 0 → included; 0 → not included
        included = limit_val == -1 or (isinstance(limit_val, int) and limit_val > 0)
        features.append({
            "key": feat_key,
            "module": mod_key,
            "label_key": label_key,
            "included": included,
            "requires_plan": requires_plan if not included else None,
        })

    # Active add-ons (enriched with display fields)
    active_addons_raw = await billing_repository.list_active_addons_for_org(org_id)
    active_addons = []
    for row in active_addons_raw:
        plan = await billing_repository.get_commercial_plan(row["addon_slug"])
        if not plan:
            continue
        active_addons.append({
            "addon_slug": row["addon_slug"],
            "name": plan.get("name", row["addon_slug"]),
            "quantity": row.get("quantity", 1),
            "price_monthly": plan.get("price_monthly", 0.0),
            "started_at": row.get("started_at"),
            "addon_provides": plan.get("addon_provides") or {},
            "max_quantity": plan.get("max_quantity", 1),
            "is_custom_override": row.get("is_custom_override", False),
        })

    return {
        "metrics": out_metrics,
        "features": features,
        "active_addons": active_addons,
        "commercial_plan_slug": summary.get("commercial_plan_slug", "free"),
        "legacy_pricing_lock": bool(summary.get("legacy_pricing_lock")),
    }


# ==============================================================================
# Checkout & Portal (org admin only)
# ==============================================================================

@router.post(
    "/checkout-session",
    summary="Create a Stripe Checkout Session for plan purchase",
)
async def create_checkout(
    body: CheckoutRequest,
    current_user: dict = Depends(require_admin),
) -> dict:
    """Create a Stripe Checkout Session.

    Only org admins can initiate a purchase.
    Returns session_id and url for client-side redirect.

    v5.5 hardening: Returns 409 Conflict when the org already has an active
    Stripe subscription, with a ``redirect_to_portal`` hint so the frontend
    can route the user to the Customer Portal instead of creating a duplicate.
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    try:
        result = await stripe_service.create_checkout_session(
            org_id=org_id,
            org_name=current_user.get("org_name", ""),
            email=current_user.get("email", ""),
            plan_slug=body.plan_slug,
            interval=body.interval,
            success_url=body.success_url or "",
            cancel_url=body.cancel_url or "",
        )
        return result
    except stripe_service.DuplicateSubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "code": "duplicate_subscription",
                "redirect_to_portal": e.redirect_to_portal,
            },
        )
    except stripe_service.SamePlanError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(e),
                "code": "same_plan",
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Checkout session creation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@router.post(
    "/modify-subscription",
    summary="Modify an existing Stripe subscription (upgrade/downgrade)",
)
async def modify_subscription(
    body: CheckoutRequest,
    current_user: dict = Depends(require_admin),
) -> dict:
    """Modify an active Stripe subscription to a different plan.

    Uses Stripe Subscription.modify() for in-place plan changes with
    automatic proration. The webhook subscription.updated handles
    re-provisioning of module entitlements.

    Only works for orgs with an active Stripe subscription. Free users
    must use checkout-session instead.
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    try:
        result = await stripe_service.modify_subscription(
            org_id=org_id,
            plan_slug=body.plan_slug,
            interval=body.interval,
        )
        return result
    except stripe_service.NoActiveSubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "no_subscription"},
        )
    except stripe_service.PlanChangeRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": str(e), "code": "rate_limited"},
        )
    except stripe_service.SamePlanError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(e), "code": "same_plan"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Subscription modification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to modify subscription",
        )


# ==============================================================================
# v5.8 / Onda 9.A — Cancel + Reactivate subscription (native CTAs)
# ==============================================================================
#
# Native cancel UX so the merchant doesn't have to leave for Stripe Customer
# Portal. Two modes — see stripe_service.cancel_subscription docstring.


class CancelSubscriptionRequest(BaseModel):
    at_period_end: bool = True
    reason: Optional[str] = None


@router.post(
    "/cancel-subscription",
    summary="Cancel the org's active Stripe subscription",
)
async def cancel_subscription(
    body: CancelSubscriptionRequest,
    current_user: dict = Depends(require_admin),
) -> dict:
    """Cancel the active subscription. Default: cancel-at-period-end so the
    customer keeps access until current_period_end. Pass `at_period_end=false`
    for immediate hard cancel (no automatic refund).

    Idempotent — re-cancelling an already-cancelled sub returns the existing
    state without re-issuing Stripe API calls.
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    try:
        result = await stripe_service.cancel_subscription(
            org_id=org_id,
            at_period_end=body.at_period_end,
            reason=body.reason or "",
        )
    except stripe_service.NoActiveSubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "no_subscription"},
        )
    except Exception as e:
        logger.error("cancel_subscription failed for org=%s: %s", org_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        )

    # Audit log (best-effort) — gives the platform owner a trail of churn
    # decisions tied to actual user reasons.
    try:
        from repositories import audit_repository
        from models import AuditLog
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=current_user.get("user_id"),
            action="user_cancelled_subscription",
            resource_type="organization",
            resource_id=org_id,
            details={
                "at_period_end": body.at_period_end,
                "reason": body.reason or "",
                "result": result,
            },
        ))
    except Exception:
        pass

    return result


@router.post(
    "/reactivate-subscription",
    summary="Reverse a cancel-at-period-end before it takes effect",
)
async def reactivate_subscription(
    current_user: dict = Depends(require_admin),
) -> dict:
    """The merchant scheduled cancel-at-period-end and wants to keep the
    subscription. Sets `cancel_at_period_end=False` on Stripe; webhook
    propagates to DB on the next event."""
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    try:
        result = await stripe_service.reactivate_subscription(org_id=org_id)
    except stripe_service.NoActiveSubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "no_subscription"},
        )
    except Exception as e:
        logger.error("reactivate_subscription failed for org=%s: %s", org_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate subscription",
        )

    try:
        from repositories import audit_repository
        from models import AuditLog
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=current_user.get("user_id"),
            action="user_reactivated_subscription",
            resource_type="organization",
            resource_id=org_id,
            details={"result": result},
        ))
    except Exception:
        pass

    return result


@router.post(
    "/portal-session",
    summary="Create a Stripe Customer Portal session",
)
async def create_portal(
    body: PortalRequest,
    current_user: dict = Depends(require_admin),
) -> dict:
    """Create a Stripe Customer Portal session for card/invoice management.

    Only org admins can access the portal.
    Returns url for redirect.
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    try:
        result = await stripe_service.create_portal_session(
            org_id=org_id,
            return_url=body.return_url or "",
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ==============================================================================
# Checkout verification / recovery (v5.7)
# ==============================================================================

@router.post(
    "/verify-checkout",
    summary="Verify and recover a Stripe Checkout Session completion",
)
async def verify_checkout(
    body: VerifyCheckoutRequest,
    current_user: dict = Depends(require_admin),
) -> dict:
    """Verify a Stripe Checkout Session and provision the plan if needed.

    Pull-based recovery for when webhook delivery is missing, delayed,
    or misconfigured.  Same auth as checkout-session (org admin).

    Returns status:
      - "provisioned"           — plan activated via this call
      - "already_provisioned"   — org already had the correct state (no-op)
      - "session_incomplete"    — checkout not completed by customer
      - "subscription_not_active" — Stripe subscription in terminal state
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    try:
        result = await stripe_service.verify_checkout_session(
            session_id=body.session_id,
            org_id=org_id,
        )

        logger.info(
            "verify-checkout session_id=%s org_id=%s result=%s",
            body.session_id, org_id, result.get("status"),
        )

        return result
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "verify-checkout failed session_id=%s org_id=%s: %s",
            body.session_id, org_id, e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify checkout session",
        )


# ==============================================================================
# Onda 24 Phase F — Verify-addon-state recovery (parity with verify-checkout)
# ==============================================================================


@router.post(
    "/verify-addon-state",
    summary="Reconcile DB addon_subscriptions with live Stripe items (recovery)",
)
async def verify_addon_state(
    current_user: dict = Depends(get_verified_user),
) -> dict:
    """Pull-based recovery for addon state: read live Stripe sub items and
    upsert/cancel matching AddonSubscription rows.

    Onda 24 Phase F — parity with verify_checkout_session. The webhook
    customer.subscription.updated handler (and the sync block in
    modify_subscription / Onda 13) keeps addon_subscriptions in sync
    when Stripe events arrive promptly. In localhost without
    `stripe listen` and on rare prod webhook delays, an addon
    purchased via add_addon may be live on Stripe but not yet in DB.
    The frontend calls this endpoint a few seconds post-purchase as
    a self-healing safety net.

    Idempotent. Read-only on Stripe; only DB upsert/cancel.

    Returns:
      {
        "status": "ok",
        "stripe_subscription_id": "sub_xxx" | null,
        "addons_upserted": N,
        "addons_cancelled": M,
      }
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    guard = await billing_repository.get_org_subscription_guard(org_id)
    sub_id = guard.get("stripe_subscription_id")
    if not sub_id:
        # No active Stripe sub — nothing to reconcile. Cancel any
        # AddonSubscription rows still active for this org as a
        # defensive sweep.
        from database import addon_subscriptions_collection
        from datetime import datetime, timezone
        result = await addon_subscriptions_collection.update_many(
            {"organization_id": org_id, "status": "active"},
            {"$set": {
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return {
            "status": "no_subscription",
            "stripe_subscription_id": None,
            "addons_upserted": 0,
            "addons_cancelled": result.modified_count,
        }

    try:
        import stripe as _stripe
        import os as _os
        _stripe.api_key = _os.environ.get("STRIPE_SECRET_KEY", "").strip()
        sub = await asyncio.to_thread(
            _stripe.Subscription.retrieve, sub_id, expand=["items"],
        )
    except Exception as e:
        logger.error("verify-addon-state retrieve failed for org=%s sub=%s: %s",
                     org_id, sub_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch Stripe subscription state",
        )

    # Filter addon items (metadata.is_addon=true)
    addon_items: List[Dict[str, Any]] = []
    for item in (sub.get("items") or {}).get("data", []) or []:
        metadata = (item.get("metadata") if hasattr(item, "get")
                    else getattr(item, "metadata", None)) or {}
        if not isinstance(metadata, dict):
            try:
                metadata = dict(metadata)
            except Exception:
                metadata = {}
        if metadata.get("is_addon") != "true":
            continue
        slug = metadata.get("addon_slug")
        if not slug:
            continue
        item_id = item.get("id") if hasattr(item, "get") else getattr(item, "id", None)
        price = item.get("price") if hasattr(item, "get") else getattr(item, "price", None)
        price_id = (price.get("id") if hasattr(price, "get") else getattr(price, "id", None)) if price else None
        qty = item.get("quantity") if hasattr(item, "get") else getattr(item, "quantity", 1)
        addon_items.append({
            "slug": slug,
            "stripe_subscription_item_id": item_id,
            "stripe_price_id": price_id,
            "quantity": int(qty or 1),
        })

    counters = await billing_repository.reconcile_addons_with_stripe_items(
        organization_id=org_id,
        stripe_subscription_id=sub_id,
        addon_items_from_stripe=addon_items,
    )

    logger.info(
        "verify-addon-state org=%s sub=%s upserted=%d cancelled=%d items_seen=%d",
        org_id, sub_id, counters.get("upserted", 0),
        counters.get("cancelled", 0), len(addon_items),
    )

    return {
        "status": "ok",
        "stripe_subscription_id": sub_id,
        "addons_upserted": counters.get("upserted", 0),
        "addons_cancelled": counters.get("cancelled", 0),
    }


# ==============================================================================
# Webhooks (Stripe signature auth only -- no Bearer token)
# ==============================================================================

@router.post(
    "/webhooks",
    summary="Stripe webhook receiver",
    include_in_schema=False,  # Don't expose in OpenAPI docs
)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
) -> dict:
    """Receive and process Stripe webhook events.

    Authentication: Stripe signature verification (not Bearer token).
    Idempotent: duplicate events are detected and skipped.
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    payload = await request.body()

    try:
        event = stripe_service.verify_and_construct_event(payload, stripe_signature)
    except ValueError as e:
        logger.warning("Webhook signature verification failed: %s", e)
        # Track O Step 3.3 — record invalid signature attempt (security signal)
        try:
            from core.observability.metrics import record_payment
            record_payment(event_type="unknown", status="invalid_signature")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    # Fase 8b: seed a correlation id rooted in Stripe's event id so every
    # downstream log line under this handler is greppable by one token.
    from services.correlation_context import set_correlation_id, clear_correlation_id
    event_id = event.get("id", "unknown")
    set_correlation_id(f"wh_{event_id}")
    try:
        result = await stripe_service.handle_webhook_event(event)
    finally:
        clear_correlation_id()

    # Track O Step 3.3 — record payment outcome per Grafana panel.
    # Map raw Stripe type → canonical short tag (low cardinality).
    # Unknown event types collapse to "unknown" to bound cardinality.
    raw_event_type = event.get("type") or "unknown"
    canonical_event_type = {
        "checkout.session.completed": "checkout_completed",
        "charge.refunded":             "payment_refunded",
        "charge.dispute.created":      "payment_disputed",
    }.get(raw_event_type, "unknown")

    # C3 hardening: If the handler failed, return 500 so Stripe retries.
    # Returning 200 on error would cause Stripe to never retry the event,
    # permanently losing that billing state change.
    if result.get("status") == "error":
        logger.error(
            "Webhook handler failed for event '%s' (%s): %s",
            event.get("id"), event.get("type"), result.get("error"),
        )
        try:
            from core.observability.metrics import record_payment
            record_payment(event_type=canonical_event_type, status="error")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed -- Stripe should retry",
        )

    try:
        from core.observability.metrics import record_payment
        record_payment(event_type=canonical_event_type, status="ok")
    except Exception:
        pass

    return {"received": True, **result}


# ==============================================================================
# Add-on management (v5.8 / Onda 3)
# ==============================================================================
#
# Three endpoints expose add-on packs to the org admin:
#   GET    /billing/addons        — list all add-ons available for current plan
#   GET    /billing/my-addons     — list active add-ons of the current org
#   POST   /billing/add-addon     — buy / increase quantity of an add-on
#   DELETE /billing/addon/{slug}  — cancel an add-on (Stripe item removed)
#
# All write operations route through stripe_service.modify_subscription with
# `addon_changes` (Onda 2). The webhook handler (`_handle_subscription_updated`)
# is the source of truth: it persists the resulting AddonSubscription rows
# from the actual Stripe state. So if Stripe modify succeeds but webhook
# delivery is delayed, the DB will catch up on the next webhook delivery.
#
# Endpoints DO NOT directly write to AddonSubscription — only the webhook
# handler does. This preserves the invariant: "Stripe is source of truth".


class AddAddonRequest(BaseModel):
    addon_slug: str
    quantity: int = 1


@router.get(
    "/addons",
    summary="List add-ons available for the current org's plan",
)
async def list_available_addons(
    current_user: dict = Depends(get_verified_user),
) -> list:
    """Return all active add-on plans, with a `compatible` flag indicating
    whether the current org's plan can purchase each one.

    Free users see all add-ons with `compatible=False` so the UI can render
    them as "upgrade your plan to unlock add-ons".
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    org = await billing_repository.get_org_billing_summary(org_id)
    current_plan_slug = (org or {}).get("commercial_plan_slug") or "free"

    plans = await billing_repository.list_commercial_plans(public_only=True)
    addons = [p for p in plans if p.get("is_addon")]

    # Decorate with compatibility + active count for UI rendering
    active_addons = await billing_repository.list_active_addons_for_org(org_id)
    active_by_slug = {a["addon_slug"]: a for a in active_addons}

    out = []
    for addon in addons:
        compat = addon.get("compatible_plans") or []
        is_compatible = (
            current_plan_slug != "free"
            and (not compat or current_plan_slug in compat)
        )
        active = active_by_slug.get(addon["slug"])

        # ── Onda 24 Phase E — Stripe-readiness check ────────────────────
        # An addon is purchasable ONLY if it has a Stripe Price ID linked.
        # Without it, modify_subscription would 500 at purchase time.
        # Surfacing this state to the UI lets the frontend disable the
        # Buy button + show a clear "in setup" indicator instead of a
        # generic error post-click.
        stripe_price_id = addon.get("stripe_price_id_monthly")
        purchasable = bool(stripe_price_id) and is_compatible
        purchasable_reason = None
        if not stripe_price_id:
            purchasable_reason = "stripe_not_configured"
        elif not is_compatible:
            purchasable_reason = (
                "plan_incompatible" if current_plan_slug != "free"
                else "free_plan"
            )

        addon_dict = {
            "slug": addon["slug"],
            "name": addon["name"],
            "description": addon.get("description", ""),
            "tagline": addon.get("tagline", ""),
            "price_monthly": addon.get("price_monthly", 0.0),
            "currency": addon.get("currency", "EUR"),
            "addon_provides": addon.get("addon_provides") or {},
            "compatible_plans": compat,
            "max_quantity": addon.get("max_quantity", 1),
            "features_display": addon.get("features_display", []),
            "is_compatible": is_compatible,
            "active_quantity": (active or {}).get("quantity", 0) if active else 0,
            # Onda 24 Phase E
            "purchasable": purchasable,
            "purchasable_reason": purchasable_reason,
        }
        out.append(addon_dict)

    return out


@router.get(
    "/my-addons",
    summary="List active add-ons of the current org",
)
async def list_my_addons(
    current_user: dict = Depends(get_verified_user),
) -> list:
    """Return only the add-ons currently active on the org's subscription."""
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    rows = await billing_repository.list_active_addons_for_org(org_id)
    # Enrich each row with the add-on plan's display fields
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
            "started_at": row.get("started_at"),
            "addon_provides": addon_plan.get("addon_provides") or {},
            "max_quantity": addon_plan.get("max_quantity", 1),
            "is_custom_override": row.get("is_custom_override", False),
        })
    return out


@router.post(
    "/add-addon",
    summary="Add or increase quantity of an add-on on the org's subscription",
)
async def add_addon(
    body: AddAddonRequest,
    current_user: dict = Depends(require_admin),
) -> dict:
    """Add an add-on to the org's active Stripe subscription.

    If the add-on is already active, the call updates its quantity instead
    of adding a duplicate Stripe item (Stripe rejects duplicate price IDs
    on the same subscription).

    Free users cannot use this endpoint — they must upgrade to a paid plan
    first. Returns 400 with `code=plan_required` in that case.
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    if body.quantity < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Quantity must be >= 1.", "code": "invalid_quantity"},
        )

    addon = await billing_repository.get_commercial_plan(body.addon_slug)
    if not addon or not addon.get("is_addon"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Add-on '{body.addon_slug}' not found.", "code": "addon_not_found"},
        )

    if body.quantity > addon.get("max_quantity", 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Add-on '{body.addon_slug}' max quantity is {addon['max_quantity']}.",
                "code": "max_quantity_exceeded",
            },
        )

    # Need an active sub to attach add-ons (free users blocked here)
    guard = await billing_repository.get_org_subscription_guard(org_id)
    if not guard.get("stripe_subscription_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Add-ons require an active paid subscription. Subscribe to a plan first.",
                "code": "plan_required",
            },
        )

    # Compatibility check (also enforced inside stripe_service, but we want a
    # clean 400 with code=incompatible BEFORE touching Stripe API).
    current_plan = guard.get("commercial_plan_slug") or "free"
    compat = addon.get("compatible_plans") or []
    if compat and current_plan not in compat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Add-on '{body.addon_slug}' is not compatible with plan '{current_plan}'.",
                "code": "incompatible_plan",
                "compatible_plans": compat,
            },
        )

    # Determine action: "add" if new, "update_quantity" if already active.
    existing = await billing_repository.get_active_addon(org_id, body.addon_slug)
    if existing:
        change = {
            "action": "update_quantity",
            "slug": body.addon_slug,
            "quantity": body.quantity,
        }
    else:
        change = {
            "action": "add",
            "slug": body.addon_slug,
            "quantity": body.quantity,
        }

    try:
        result = await stripe_service.modify_subscription(
            org_id=org_id,
            plan_slug=None,            # not changing main plan
            interval="month",
            addon_changes=[change],
        )
    except stripe_service.NoActiveSubscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "no_subscription"},
        )
    except stripe_service.PlanChangeRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": str(e), "code": "rate_limited"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "invalid_addon"},
        )
    except Exception as e:
        # Onda 24 Phase B — surface Stripe-side errors to the user with the
        # ORIGINAL message (e.g. "The price specified only supports CHF…")
        # instead of a generic 500. The admin then knows EXACTLY what to
        # fix in the addon catalog (currency, archived Price, etc.) and
        # the customer is not stuck on an opaque error.
        try:
            import stripe as _stripe
            is_stripe_err = isinstance(e, _stripe.error.StripeError)
        except Exception:
            is_stripe_err = False

        logger.error(
            "add_addon failed for org=%s slug=%s: %s",
            org_id, body.addon_slug, e, exc_info=True,
        )

        if is_stripe_err:
            user_message = getattr(e, "user_message", None) or str(e)
            stripe_code = getattr(e, "code", None)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": (
                        f"L'add-on non è configurato correttamente per la fatturazione. "
                        f"Dettaglio Stripe: {user_message}"
                    ),
                    "code": "stripe_error",
                    "stripe_code": stripe_code,
                    "addon_slug": body.addon_slug,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add add-on",
        )

    return {
        "status": "ok",
        "addon_slug": body.addon_slug,
        "quantity": body.quantity,
        "subscription_id": result.get("subscription_id"),
        "note": "AddonSubscription will be persisted by webhook delivery.",
    }


@router.delete(
    "/addon/{addon_slug}",
    summary="Remove an active add-on from the org's subscription",
)
async def remove_addon(
    addon_slug: str,
    current_user: dict = Depends(require_admin),
) -> dict:
    """Remove an active add-on. The Stripe subscription_item is deleted via
    Subscription.modify; the main plan is unaffected.

    Returns 400 if the add-on is not active on this org.
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization",
        )

    existing = await billing_repository.get_active_addon(org_id, addon_slug)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Add-on '{addon_slug}' is not active on this organization.",
                "code": "addon_not_active",
            },
        )

    try:
        result = await stripe_service.modify_subscription(
            org_id=org_id,
            plan_slug=None,
            interval="month",
            addon_changes=[{"action": "remove", "slug": addon_slug}],
        )
    except stripe_service.PlanChangeRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": str(e), "code": "rate_limited"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "invalid_addon"},
        )
    except Exception as e:
        # Onda 24 Phase B — surface Stripe-side errors to the user
        try:
            import stripe as _stripe
            is_stripe_err = isinstance(e, _stripe.error.StripeError)
        except Exception:
            is_stripe_err = False

        logger.error(
            "remove_addon failed for org=%s slug=%s: %s",
            org_id, addon_slug, e, exc_info=True,
        )

        if is_stripe_err:
            user_message = getattr(e, "user_message", None) or str(e)
            stripe_code = getattr(e, "code", None)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"Errore Stripe durante rimozione add-on: {user_message}",
                    "code": "stripe_error",
                    "stripe_code": stripe_code,
                    "addon_slug": addon_slug,
                },
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove add-on",
        )

    return {
        "status": "ok",
        "addon_slug": addon_slug,
        "subscription_id": result.get("subscription_id"),
        "note": "AddonSubscription will be cancelled by webhook delivery.",
    }
