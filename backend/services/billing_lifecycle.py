"""Billing Lifecycle Service — background sync and enforcement.

v6.0: Periodically scans for stale billing states and syncs with Stripe.

Two scenarios handled:
  1. Expired trials: billing_status="trialing" but trial_ends_at is past.
     Stripe webhook (invoice.paid or customer.subscription.updated) should
     have updated the status but didn't arrive.  The sweep checks Stripe
     for the live subscription state and syncs the internal DB.

  2. Stale past_due: billing_status="past_due" with current_period_end in
     the past.  Stripe is still dunning but the user's paid period is over.
     If Stripe says the sub is canceled/unpaid, deprovision to free.

Design principles:
  - Stripe is the authority.  The sweep ALWAYS checks live Stripe state
    before mutating the internal DB.
  - Idempotent.  Running twice produces the same result.
  - Non-fatal.  Errors on individual orgs are caught and logged; the sweep
    continues with the remaining orgs.
  - Conservative.  When Stripe is unreachable, the sweep skips that org
    rather than guessing.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from repositories import billing_repository
from services.module_access import TRIAL_EXPIRED_GRACE_HOURS

logger = logging.getLogger(__name__)

# Maximum number of orgs to process per sweep (prevents runaway API usage)
_MAX_ORGS_PER_SWEEP = int(os.environ.get("BILLING_SWEEP_MAX_ORGS", "20"))


# ── Stripe access helpers ───────────────────────────────────────────────────

def _get_stripe():
    """Lazy-import and configure the Stripe SDK (same pattern as stripe_service.py)."""
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    return stripe


async def _retrieve_stripe_subscription(stripe_sub_id: str) -> dict:
    """Retrieve a Stripe subscription via the API (threaded to avoid blocking).

    Returns a plain nested dict, not a StripeObject — stripe-python v15 removed
    dict inheritance from StripeObject, so callers rely on `.get()` being a real
    method. Normalizing here keeps every consumer compatible across versions.

    Isolated as a helper so tests can mock it without touching asyncio.to_thread.
    """
    stripe = _get_stripe()
    from services.stripe_service import _normalize_stripe_object
    raw_sub = await asyncio.to_thread(stripe.Subscription.retrieve, stripe_sub_id)
    return _normalize_stripe_object(raw_sub)


# ── Individual org sync functions ────────────────────────────────────────────

async def _sync_expired_trial(org: dict) -> dict:
    """Sync an org whose trial has expired past the grace window.

    Checks live Stripe subscription status and updates internal state accordingly.

    Returns dict summary of what happened.
    """
    org_id = org["id"]
    org_name = org.get("name", "?")
    stripe_sub_id = org.get("stripe_subscription_id")

    # No Stripe subscription — orphaned trial (manual or data issue).
    # Safe to revert to free.
    if not stripe_sub_id:
        logger.info(
            "billing_sweep: org=%s (%s) — expired trial with no Stripe sub, reverting to free",
            org_id, org_name,
        )
        from services.plan_provisioning import provision_commercial_plan
        await provision_commercial_plan(
            org_id=org_id,
            plan_slug="free",
            assigned_by="billing_sweep",
            billing_status="none",
            notes="Expired trial with no Stripe subscription — reverted to free by billing sweep",
        )
        return {"org_id": org_id, "action": "reverted_to_free", "reason": "no_stripe_sub"}

    # Check Stripe for live subscription state
    try:
        sub = await _retrieve_stripe_subscription(stripe_sub_id)
    except Exception as e:
        logger.warning(
            "billing_sweep: could not retrieve Stripe sub '%s' for org=%s: %s — skipping",
            stripe_sub_id, org_id, e,
        )
        return {"org_id": org_id, "action": "skipped", "reason": f"stripe_error: {e}"}

    stripe_status = sub.get("status", "unknown")
    logger.info(
        "billing_sweep: org=%s (%s) — expired trial, Stripe says status='%s'",
        org_id, org_name, stripe_status,
    )

    if stripe_status == "active":
        # Webhook missed: trial converted to active. Sync it.
        fields = {"billing_status": "active"}
        if sub.get("current_period_end"):
            fields["current_period_end"] = datetime.fromtimestamp(
                sub["current_period_end"], tz=timezone.utc,
            ).isoformat()
        await billing_repository.update_org_billing_fields(org_id, fields)
        return {"org_id": org_id, "action": "synced_active", "stripe_status": stripe_status}

    if stripe_status == "past_due":
        # Trial ended but payment failed — Stripe is dunning.
        await billing_repository.update_org_billing_fields(org_id, {
            "billing_status": "past_due",
        })
        return {"org_id": org_id, "action": "synced_past_due", "stripe_status": stripe_status}

    if stripe_status == "trialing":
        # Still trialing in Stripe (trial_end differs from our record?).
        # Update trial_ends_at from Stripe to stay in sync.
        fields = {"billing_status": "trialing"}
        if sub.get("trial_end"):
            fields["trial_ends_at"] = datetime.fromtimestamp(
                sub["trial_end"], tz=timezone.utc,
            ).isoformat()
        await billing_repository.update_org_billing_fields(org_id, fields)
        return {"org_id": org_id, "action": "synced_trial_end", "stripe_status": stripe_status}

    if stripe_status in ("canceled", "unpaid", "incomplete_expired"):
        # Subscription terminated — deprovision to free.
        from services.plan_provisioning import deprovision_stripe_subscription
        await deprovision_stripe_subscription(org_id, stripe_sub_id)
        return {"org_id": org_id, "action": "deprovisioned", "stripe_status": stripe_status}

    # Unknown status — log and skip.
    logger.warning(
        "billing_sweep: unknown Stripe status '%s' for sub '%s' (org=%s) — skipping",
        stripe_status, stripe_sub_id, org_id,
    )
    return {"org_id": org_id, "action": "skipped", "reason": f"unknown_status: {stripe_status}"}


async def _sync_stale_past_due(org: dict) -> dict:
    """Sync an org whose billing_status is past_due and billing period has ended.

    Checks live Stripe subscription status.  If still past_due or canceled,
    syncs state; if active (payment succeeded), updates to active.
    """
    org_id = org["id"]
    org_name = org.get("name", "?")
    stripe_sub_id = org.get("stripe_subscription_id")

    if not stripe_sub_id:
        # past_due without Stripe subscription — shouldn't happen.
        # Safe to reset to free.
        logger.info(
            "billing_sweep: org=%s (%s) — past_due with no Stripe sub, reverting to free",
            org_id, org_name,
        )
        from services.plan_provisioning import provision_commercial_plan
        await provision_commercial_plan(
            org_id=org_id,
            plan_slug="free",
            assigned_by="billing_sweep",
            billing_status="none",
            notes="Past-due with no Stripe subscription — reverted to free by billing sweep",
        )
        return {"org_id": org_id, "action": "reverted_to_free", "reason": "no_stripe_sub"}

    # Check Stripe for live subscription state
    try:
        sub = await _retrieve_stripe_subscription(stripe_sub_id)
    except Exception as e:
        logger.warning(
            "billing_sweep: could not retrieve Stripe sub '%s' for org=%s: %s — skipping",
            stripe_sub_id, org_id, e,
        )
        return {"org_id": org_id, "action": "skipped", "reason": f"stripe_error: {e}"}

    stripe_status = sub.get("status", "unknown")
    logger.info(
        "billing_sweep: org=%s (%s) — stale past_due, Stripe says status='%s'",
        org_id, org_name, stripe_status,
    )

    if stripe_status == "active":
        # Payment succeeded (dunning resolved). Sync to active.
        fields = {"billing_status": "active"}
        if sub.get("current_period_end"):
            fields["current_period_end"] = datetime.fromtimestamp(
                sub["current_period_end"], tz=timezone.utc,
            ).isoformat()
        await billing_repository.update_org_billing_fields(org_id, fields)
        return {"org_id": org_id, "action": "synced_active", "stripe_status": stripe_status}

    if stripe_status in ("canceled", "unpaid", "incomplete_expired"):
        # Subscription terminated — deprovision to free.
        from services.plan_provisioning import deprovision_stripe_subscription
        await deprovision_stripe_subscription(org_id, stripe_sub_id)
        return {"org_id": org_id, "action": "deprovisioned", "stripe_status": stripe_status}

    if stripe_status == "past_due":
        # Still past_due in Stripe. Update current_period_end if changed.
        fields: dict = {}
        if sub.get("current_period_end"):
            fields["current_period_end"] = datetime.fromtimestamp(
                sub["current_period_end"], tz=timezone.utc,
            ).isoformat()
        if fields:
            await billing_repository.update_org_billing_fields(org_id, fields)
        return {"org_id": org_id, "action": "still_past_due", "stripe_status": stripe_status}

    # Unknown / trialing / incomplete — skip.
    logger.warning(
        "billing_sweep: unexpected Stripe status '%s' for past_due org=%s — skipping",
        stripe_status, org_id,
    )
    return {"org_id": org_id, "action": "skipped", "reason": f"unexpected_status: {stripe_status}"}


# ── Main sweep entry point ──────────────────────────────────────────────────

async def run_billing_sweep() -> dict:
    """Run the billing state sync sweep.

    Finds orgs with stale billing states, checks Stripe for live state,
    and syncs the internal DB.

    Returns:
        Dict with sweep summary:
        {
            "expired_trials_processed": int,
            "past_due_processed": int,
            "actions": [{"org_id": ..., "action": ...}, ...],
            "errors": int,
        }
    """
    results = {
        "expired_trials_processed": 0,
        "past_due_processed": 0,
        "actions": [],
        "errors": 0,
    }

    # 1. Expired trials
    try:
        expired = await billing_repository.find_expired_trials(
            grace_hours=TRIAL_EXPIRED_GRACE_HOURS,
        )
    except Exception as e:
        logger.error("billing_sweep: failed to query expired trials: %s", e)
        expired = []

    for org in expired[:_MAX_ORGS_PER_SWEEP]:
        try:
            action = await _sync_expired_trial(org)
            results["actions"].append(action)
            results["expired_trials_processed"] += 1
        except Exception as e:
            logger.error(
                "billing_sweep: error syncing expired trial for org=%s: %s",
                org.get("id", "?"), e, exc_info=True,
            )
            results["errors"] += 1

    # 2. Stale past_due
    try:
        stale = await billing_repository.find_stale_past_due()
    except Exception as e:
        logger.error("billing_sweep: failed to query stale past_due: %s", e)
        stale = []

    remaining_capacity = _MAX_ORGS_PER_SWEEP - results["expired_trials_processed"]
    for org in stale[:max(0, remaining_capacity)]:
        try:
            action = await _sync_stale_past_due(org)
            results["actions"].append(action)
            results["past_due_processed"] += 1
        except Exception as e:
            logger.error(
                "billing_sweep: error syncing stale past_due for org=%s: %s",
                org.get("id", "?"), e, exc_info=True,
            )
            results["errors"] += 1

    total = results["expired_trials_processed"] + results["past_due_processed"]
    if total > 0 or results["errors"] > 0:
        logger.info(
            "billing_sweep: completed — expired_trials=%d, past_due=%d, errors=%d",
            results["expired_trials_processed"],
            results["past_due_processed"],
            results["errors"],
        )

    return results
