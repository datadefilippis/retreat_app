"""Billing repository -- queries for commercial_plans, billing_events, and org billing fields.

Handles:
  - Commercial plan catalog CRUD
  - Billing event idempotency log
  - Organization billing field updates
  - Stripe customer/subscription lookups
  - Subscription-existence guards (v5.5 duplicate prevention)
  - v6.0: Stale billing state queries (expired trials, stale past_due)
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from database import (
    addon_subscriptions_collection,
    billing_events_collection,
    commercial_plans_collection,
    module_subscriptions_collection,
    org_quota_notices_collection,
    organizations_collection,
)
from models.common import utc_now


# ==============================================================================
# Commercial Plans
# ==============================================================================

async def get_commercial_plan(slug: str) -> Optional[dict]:
    """Get a commercial plan by slug."""
    return await commercial_plans_collection.find_one(
        {"slug": slug}, {"_id": 0}
    )


async def list_commercial_plans(public_only: bool = False) -> List[dict]:
    """List all commercial plans, optionally filtering to public-only."""
    filter_q: dict = {}
    if public_only:
        filter_q["is_public"] = True
    cursor = (
        commercial_plans_collection
        .find(filter_q, {"_id": 0})
        .sort("sort_order", 1)
    )
    return await cursor.to_list(50)


async def upsert_commercial_plan(doc: dict) -> None:
    """Insert or update a commercial plan by slug (idempotent seeding).

    Phase 2a seed hardening — authority model:

      On FIRST insert ($setOnInsert): all fields written normally.

      On subsequent startups:
        - Admin-editable fields (name, description, prices, trial_days, etc.)
          are NOT overwritten — protected so catalog admin edits survive restarts.
        - Stripe ID fields are NOT overwritten (existing protection).
        - module_plans uses ADDITIVE MERGE: new module keys are added via
          dot-notation, existing module-tier assignments are never overwritten.
        - Structural fields (slug, currency, updated_at) may be $set for
          schema evolution.
    """
    STRIPE_FIELDS = frozenset({
        "stripe_product_id",
        "stripe_price_id_monthly",
        "stripe_price_id_yearly",
    })

    # Fields that admin may edit via catalog UI — never overwrite on re-seed.
    ADMIN_EDITABLE_FIELDS = frozenset({
        "name",
        "description",
        "tagline",
        "trial_days",
        "sort_order",
        "is_public",
        "is_self_serve",
        "features_display",
        "price_monthly",
        "price_yearly",
    })

    # module_plans handled separately (additive merge below)
    _SEED_PROTECTED = ADMIN_EDITABLE_FIELDS | {"module_plans"}

    # Fields that CAN be $set on every startup (structural / schema evolution):
    # exclude Stripe fields (k not in STRIPE_FIELDS) AND admin-editable/special fields.
    update_fields = {
        k: v for k, v in doc.items()
        if k not in STRIPE_FIELDS and k not in _SEED_PROTECTED
    }

    # Fields only written on first insert
    insert_only_fields = {
        k: v for k, v in doc.items()
        if k in STRIPE_FIELDS or k in ADMIN_EDITABLE_FIELDS
    }

    # ── Additive merge for module_plans ──────────────────────────────────
    seed_module_plans = doc.get("module_plans", {})
    additive_sets: dict = {}

    existing = await commercial_plans_collection.find_one(
        {"slug": doc["slug"]},
        {"_id": 0, "module_plans": 1},
    )

    if existing and existing.get("module_plans"):
        # Plan exists — only add missing module keys via dot-notation
        existing_keys = set(existing["module_plans"].keys())
        for module_key, plan_slug in seed_module_plans.items():
            if module_key not in existing_keys:
                additive_sets[f"module_plans.{module_key}"] = plan_slug
    else:
        # Plan doesn't exist yet — include full module_plans in $setOnInsert
        insert_only_fields["module_plans"] = seed_module_plans

    # Build the update operation
    update_op: dict = {}
    final_set = {**update_fields, **additive_sets}
    if final_set:
        update_op["$set"] = final_set
    if insert_only_fields:
        update_op["$setOnInsert"] = insert_only_fields

    if update_op:
        await commercial_plans_collection.update_one(
            {"slug": doc["slug"]},
            update_op,
            upsert=True,
        )


async def count_commercial_plans() -> int:
    """Count all commercial plans."""
    return await commercial_plans_collection.count_documents({})


async def get_commercial_plan_by_stripe_price(stripe_price_id: str) -> Optional[dict]:
    """Find a commercial plan by its Stripe price ID (monthly or yearly)."""
    return await commercial_plans_collection.find_one(
        {
            "$or": [
                {"stripe_price_id_monthly": stripe_price_id},
                {"stripe_price_id_yearly": stripe_price_id},
            ]
        },
        {"_id": 0},
    )


# ==============================================================================
# Billing Events (webhook idempotency)
# ==============================================================================

async def is_event_processed(stripe_event_id: str) -> bool:
    """Check if a Stripe webhook event has already been SUCCESSFULLY processed.

    H2 hardening: Only skip events that were processed successfully.
    Failed events (processed=False) can be retried by Stripe.
    """
    doc = await billing_events_collection.find_one(
        {"stripe_event_id": stripe_event_id, "processed": True},
        {"_id": 1},
    )
    return doc is not None


async def record_billing_event(doc: dict) -> None:
    """Record a billing event for idempotency.

    C2 hardening: Uses update_one with upsert to avoid DuplicateKeyError
    race conditions when two concurrent webhook deliveries arrive.
    The unique index on stripe_event_id ensures at-most-once semantics.
    """
    await billing_events_collection.update_one(
        {"stripe_event_id": doc["stripe_event_id"]},
        {"$set": doc},
        upsert=True,
    )


# ── Atomic lock-before-handler pattern (Fase 6c) ─────────────────────────────
#
# Motivation:
#   The check-then-run pattern (is_event_processed → handler → record) has a
#   TOCTOU window: two concurrent deliveries of the same event both see
#   "not yet processed" and both execute the handler. Handler side effects
#   are mostly idempotent (plan_provisioning, reconcile_checkout_event) but
#   the race is real and surfaces under high load or retry storms.
#
#   This module exposes a reserve-before-run API that uses the existing
#   unique index on stripe_event_id as the serialization primitive:
#     - try_acquire_event_lock tries to INSERT a processed=False record.
#     - On DuplicateKeyError it inspects the existing doc:
#         * processed=True           → already fully handled, skip.
#         * processed=False, fresh   → another worker is processing, skip.
#         * processed=False, stale   → recover with conditional update.
#     - mark_event_processed finalizes the record after handler succeeds.
#
#   Failed handlers leave the record in processed=False with an error field
#   so the next real retry (past the stale window) can recover and try again.


async def try_acquire_event_lock(
    stripe_event_id: str,
    event_type: str,
    stale_after_seconds: int = 60,
) -> dict:
    """Atomically claim an event for processing.

    Returns {"acquired": bool, "status": "acquired" | "already_processed"
             | "in_flight" | "recovered" | "contention"}.

    - "acquired":          we just inserted the lock row, handler should run.
    - "recovered":         we re-took a stale unfinished attempt, handler
                           should run (idempotency lives in the handler).
    - "already_processed": another worker finished successfully.
    - "in_flight":         another worker is processing within the stale
                           window — do not double-run.
    - "contention":        race lost during a conditional update; safe to
                           skip (the owner will finish or go stale).
    """
    from datetime import timedelta, timezone
    from pymongo.errors import DuplicateKeyError
    from models.common import utc_now

    now = utc_now()
    stale_threshold = now - timedelta(seconds=stale_after_seconds)

    def _as_utc(dt):
        """Coerce naive datetimes (as Motor returns them) to UTC-aware."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    # 1. Try to insert — cheapest path on the common case (first-time arrival).
    try:
        await billing_events_collection.insert_one({
            "stripe_event_id": stripe_event_id,
            "event_type": event_type,
            "processed": False,
            "started_at": now,
            "created_at": now,
        })
        return {"acquired": True, "status": "acquired"}
    except DuplicateKeyError:
        pass

    # 2. Existing row — read its state to decide.
    existing = await billing_events_collection.find_one(
        {"stripe_event_id": stripe_event_id},
        {"_id": 0, "processed": 1, "started_at": 1},
    )
    if not existing:
        # Extremely rare: the other writer deleted between DuplicateKeyError
        # and our read. Treat as contention (caller can retry or skip).
        return {"acquired": False, "status": "contention"}

    if existing.get("processed"):
        return {"acquired": False, "status": "already_processed"}

    started = _as_utc(existing.get("started_at"))
    if started and started > stale_threshold:
        return {"acquired": False, "status": "in_flight"}

    # 3. Stale — attempt conditional takeover. Scope the match on the exact
    #    started_at we just observed so another recovering worker cannot steal
    #    it from under us.
    match = {"stripe_event_id": stripe_event_id, "processed": False}
    # Use the original (possibly naive) value for the match so the update
    # doesn't miss the row due to tz coercion mismatches; the $set uses now
    # (tz-aware) which Motor serializes as BSON date consistently.
    raw_started = existing.get("started_at")
    if raw_started is not None:
        match["started_at"] = raw_started
    update_res = await billing_events_collection.update_one(
        match,
        {"$set": {"started_at": now}},
    )
    if update_res.modified_count == 1:
        return {"acquired": True, "status": "recovered"}
    return {"acquired": False, "status": "contention"}


async def mark_event_processed(
    stripe_event_id: str,
    *,
    organization_id: Optional[str] = None,
    payload_summary: Optional[dict] = None,
    error: Optional[str] = None,
) -> None:
    """Finalize an event's billing record after handler completion.

    When error is None, sets processed=True. When error is provided, the
    record remains processed=False but the error is stored so the next
    retry past the stale window can see the history.
    """
    from models.common import utc_now

    update = {
        "completed_at": utc_now(),
    }
    if error is None:
        update["processed"] = True
    else:
        update["processed"] = False
        update["error"] = str(error)[:500]
    if organization_id is not None:
        update["organization_id"] = organization_id
    if payload_summary is not None:
        update["payload_summary"] = payload_summary

    await billing_events_collection.update_one(
        {"stripe_event_id": stripe_event_id},
        {"$set": update},
    )


async def list_billing_events(
    org_id: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    """List recent billing events, optionally filtered by org."""
    filter_q: dict = {}
    if org_id:
        filter_q["organization_id"] = org_id
    cursor = (
        billing_events_collection
        .find(filter_q, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    return await cursor.to_list(limit)


# ==============================================================================
# Organization billing fields
# ==============================================================================

async def update_org_billing_fields(org_id: str, fields: Dict[str, Any]) -> bool:
    """Update specific billing fields on an organization document.

    Args:
        org_id: Organization ID.
        fields: Dict of field names to new values (e.g. commercial_plan_slug, billing_status).

    Returns True if the org was found and updated.
    """
    fields["updated_at"] = utc_now().isoformat()
    result = await organizations_collection.update_one(
        {"id": org_id},
        {"$set": fields},
    )
    return result.modified_count > 0


async def get_org_by_stripe_customer(stripe_customer_id: str) -> Optional[dict]:
    """Find an organization by its Stripe customer ID."""
    return await organizations_collection.find_one(
        {"stripe_customer_id": stripe_customer_id},
        {"_id": 0},
    )


async def get_org_billing_summary(org_id: str) -> Optional[dict]:
    """Get the billing-relevant fields for an org."""
    return await organizations_collection.find_one(
        {"id": org_id},
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "commercial_plan_slug": 1,
            "stripe_customer_id": 1,
            "stripe_subscription_id": 1,
            "billing_status": 1,
            "billing_interval": 1,
            "trial_ends_at": 1,
            "current_period_end": 1,
            "cancel_at_period_end": 1,
            "plan_assigned_by": 1,
            "plan_assigned_at": 1,
            "billing_email": 1,
            # v5.8 / Onda 9.T — trial-once tracking
            "has_used_trial": 1,
            "has_used_trial_at": 1,
            "has_used_trial_plan_slug": 1,
            # v5.8 / Onda 5 — legacy pricing lock
            "legacy_pricing_lock": 1,
            "legacy_price_ids": 1,
        },
    )


# ==============================================================================
# Subscription existence guard (v5.5 -- duplicate prevention)
# ==============================================================================

# Billing states that represent an org with an active Stripe subscription.
# Creating a *new* Stripe Checkout session while the org is in one of these
# states would produce a duplicate subscription.
ACTIVE_BILLING_STATES = frozenset({"active", "trialing", "past_due"})


async def get_org_subscription_guard(org_id: str) -> dict:
    """Return the billing guard data needed before creating a checkout session.

    The caller uses the returned dict to decide whether a new Stripe
    Checkout Session should be allowed.

    Returns dict with:
      - billing_status: str
      - commercial_plan_slug: str
      - stripe_subscription_id: str | None
      - has_active_subscription: bool  (True if status in ACTIVE_BILLING_STATES)
      - cancel_at_period_end: bool
    """
    doc = await organizations_collection.find_one(
        {"id": org_id},
        {
            "_id": 0,
            "billing_status": 1,
            "commercial_plan_slug": 1,
            "stripe_subscription_id": 1,
            "cancel_at_period_end": 1,
            "plan_assigned_by": 1,
        },
    )
    if not doc:
        return {
            "billing_status": "none",
            "commercial_plan_slug": "free",
            "stripe_subscription_id": None,
            "has_active_subscription": False,
            "cancel_at_period_end": False,
        }
    status = doc.get("billing_status", "none")
    return {
        "billing_status": status,
        "commercial_plan_slug": doc.get("commercial_plan_slug", "free"),
        "stripe_subscription_id": doc.get("stripe_subscription_id"),
        "has_active_subscription": status in ACTIVE_BILLING_STATES,
        "cancel_at_period_end": doc.get("cancel_at_period_end", False),
    }


# ==============================================================================
# Module subscriptions -- Stripe-related queries
# ==============================================================================

async def cancel_subscriptions_by_stripe_sub(stripe_subscription_id: str) -> int:
    """Cancel all active module subscriptions linked to a Stripe subscription.

    Returns the number of subscriptions cancelled.
    """
    now = utc_now().isoformat()
    result = await module_subscriptions_collection.update_many(
        {
            "stripe_subscription_id": stripe_subscription_id,
            "status": "active",
        },
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": now,
                "updated_at": now,
            }
        },
    )
    return result.modified_count


async def list_subscriptions_by_stripe_sub(stripe_subscription_id: str) -> List[dict]:
    """List all module subscriptions linked to a Stripe subscription."""
    cursor = module_subscriptions_collection.find(
        {"stripe_subscription_id": stripe_subscription_id},
        {"_id": 0},
    )
    return await cursor.to_list(50)


# ==============================================================================
# v6.0: Stale billing state queries (for billing_lifecycle sweep)
# ==============================================================================

async def find_expired_trials(grace_hours: int = 2) -> List[dict]:
    """Find orgs with billing_status='trialing' where trial has expired beyond grace.

    Returns org docs where trial_ends_at < (now - grace_hours).
    ISO 8601 strings sort lexicographically identical to chronologically,
    so $lt comparison works correctly on ISO string fields.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=grace_hours)).isoformat()
    cursor = organizations_collection.find(
        {
            "billing_status": "trialing",
            "trial_ends_at": {"$lt": cutoff},
        },
        {"_id": 0},
    )
    return await cursor.to_list(100)


async def find_stale_past_due() -> List[dict]:
    """Find orgs with billing_status='past_due' where current billing period has ended.

    Returns org docs where current_period_end is in the past, or missing entirely.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor = organizations_collection.find(
        {
            "billing_status": "past_due",
            "$or": [
                {"current_period_end": {"$lt": now_iso}},
                {"current_period_end": None},
                {"current_period_end": {"$exists": False}},
            ],
        },
        {"_id": 0},
    )
    return await cursor.to_list(100)


# ==============================================================================
# Add-on subscriptions (v5.8 / Onda 3)
# ==============================================================================
#
# All write operations here are designed to be called FROM the Stripe webhook
# handler (`_handle_subscription_updated`), NOT from request-handling code.
# The Stripe state is the source of truth — webhook syncs DB to it.
#
# Read operations are called from request handlers (e.g. listing the user's
# active add-ons in BillingSection UI, computing effective limits in
# module_access).


async def list_active_addons_for_org(organization_id: str) -> List[dict]:
    """Return all active AddonSubscription rows for an org.

    Used by:
      · `module_access.get_effective_limit()` to sum addon contributions
      · UI `/api/billing/my-addons` to render the active-addons list
      · System admin usage dashboard

    Cancelled / past_due rows are excluded — they don't grant entitlements.
    """
    cursor = addon_subscriptions_collection.find(
        {"organization_id": organization_id, "status": "active"},
        {"_id": 0},
    ).sort([("addon_slug", 1)])
    return await cursor.to_list(50)


async def get_active_addon(organization_id: str, addon_slug: str) -> Optional[dict]:
    """Return the active AddonSubscription for a specific (org, slug), or None."""
    return await addon_subscriptions_collection.find_one(
        {
            "organization_id": organization_id,
            "addon_slug": addon_slug,
            "status": "active",
        },
        {"_id": 0},
    )


async def upsert_addon_subscription(doc: dict) -> str:
    """Idempotent upsert of an AddonSubscription row.

    Match key: (organization_id, addon_slug, status='active').
    On match: update mutable fields (quantity, stripe_subscription_item_id,
              stripe_price_id, updated_at). Never overwrite started_at.
    On miss: insert a new "active" row.

    Returns the row's `id` field (existing or newly created). Idempotent to
    re-runs of the webhook (the same items[] arriving twice will not produce
    duplicates).
    """
    from models.common import generate_id

    now = utc_now().isoformat()
    org_id = doc["organization_id"]
    addon_slug = doc["addon_slug"]

    existing = await addon_subscriptions_collection.find_one(
        {
            "organization_id": org_id,
            "addon_slug": addon_slug,
            "status": "active",
        },
        {"_id": 0, "id": 1, "started_at": 1},
    )

    if existing:
        await addon_subscriptions_collection.update_one(
            {"id": existing["id"]},
            {
                "$set": {
                    "quantity": doc.get("quantity", 1),
                    "stripe_subscription_id": doc.get("stripe_subscription_id"),
                    "stripe_subscription_item_id": doc.get("stripe_subscription_item_id"),
                    "stripe_price_id": doc.get("stripe_price_id"),
                    "updated_at": now,
                }
            },
        )
        return existing["id"]

    new_id = doc.get("id") or generate_id()
    insert_doc = {
        "id": new_id,
        "organization_id": org_id,
        "addon_slug": addon_slug,
        "status": "active",
        "quantity": doc.get("quantity", 1),
        "started_at": doc.get("started_at") or now,
        "cancelled_at": None,
        "stripe_subscription_id": doc.get("stripe_subscription_id"),
        "stripe_subscription_item_id": doc.get("stripe_subscription_item_id"),
        "stripe_price_id": doc.get("stripe_price_id"),
        "is_custom_override": doc.get("is_custom_override", False),
        "assigned_by": doc.get("assigned_by", "stripe_webhook"),
        "notes": doc.get("notes", ""),
        "created_at": now,
        "updated_at": now,
    }
    await addon_subscriptions_collection.insert_one(insert_doc)
    return new_id


async def cancel_addon_subscription(organization_id: str, addon_slug: str) -> bool:
    """Mark an active AddonSubscription as cancelled.

    Returns True if a row was actually updated (active row existed),
    False otherwise. Idempotent: cancelling an already-cancelled addon
    is a no-op.
    """
    now = utc_now().isoformat()
    result = await addon_subscriptions_collection.update_one(
        {
            "organization_id": organization_id,
            "addon_slug": addon_slug,
            "status": "active",
        },
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": now,
                "updated_at": now,
            }
        },
    )
    return result.modified_count > 0


async def cancel_all_addons_by_stripe_sub(stripe_subscription_id: str) -> int:
    """Cancel all active addons linked to a Stripe subscription that itself
    was just cancelled. Mirrors `cancel_subscriptions_by_stripe_sub` for
    ModuleSubscription.

    Returns count of rows updated.
    """
    now = utc_now().isoformat()
    result = await addon_subscriptions_collection.update_many(
        {
            "stripe_subscription_id": stripe_subscription_id,
            "status": "active",
        },
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": now,
                "updated_at": now,
            }
        },
    )
    return result.modified_count


async def reconcile_addons_with_stripe_items(
    organization_id: str,
    stripe_subscription_id: str,
    addon_items_from_stripe: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Sync DB addons to match what Stripe currently reports as add-on items.

    Called from `_handle_subscription_updated` (webhook) — Stripe is source-
    of-truth. The contract:
      · For every item Stripe reports → upsert (idempotent).
      · For every active DB addon NOT present in stripe items → cancel.

    `addon_items_from_stripe` items have shape:
      {"slug": "addon_x", "stripe_subscription_item_id": "si_yyy",
       "stripe_price_id": "price_zzz", "quantity": 1}

    Returns counters {"upserted": N, "cancelled": M} for logging.
    """
    upserted = 0
    seen_slugs: set = set()
    for item in addon_items_from_stripe:
        slug = item.get("slug")
        if not slug:
            continue
        await upsert_addon_subscription({
            "organization_id": organization_id,
            "addon_slug": slug,
            "quantity": item.get("quantity", 1),
            "stripe_subscription_id": stripe_subscription_id,
            "stripe_subscription_item_id": item.get("stripe_subscription_item_id"),
            "stripe_price_id": item.get("stripe_price_id"),
            "assigned_by": "stripe_webhook",
        })
        seen_slugs.add(slug)
        upserted += 1

    # Cancel any active row not in seen_slugs
    cancel_count = 0
    cursor = addon_subscriptions_collection.find(
        {
            "organization_id": organization_id,
            "stripe_subscription_id": stripe_subscription_id,
            "status": "active",
        },
        {"_id": 0, "addon_slug": 1},
    )
    async for row in cursor:
        if row["addon_slug"] not in seen_slugs:
            ok = await cancel_addon_subscription(organization_id, row["addon_slug"])
            if ok:
                cancel_count += 1

    return {"upserted": upserted, "cancelled": cancel_count}


# ==============================================================================
# Quota notices (v5.8 / Onda 6) — idempotent email-warning bookkeeping
# ==============================================================================
#
# These helpers back the quota_warning_sweep cron. The collection has a
# unique compound index on (org, metric, level, period) so duplicate
# inserts raise DuplicateKeyError — the caller catches it as "already sent
# this period, skip" without explicit pre-check.


async def has_quota_notice(
    organization_id: str,
    metric_key: str,
    level: str,
    period_start: str,
) -> bool:
    """Returns True if a notice for this (org, metric, level, period) was
    already recorded. Used by the sweep to skip already-notified orgs
    cheaply BEFORE bothering to render the email."""
    doc = await org_quota_notices_collection.find_one(
        {
            "organization_id": organization_id,
            "metric_key": metric_key,
            "level": level,
            "period_start": period_start,
        },
        {"_id": 1},
    )
    return doc is not None


async def record_quota_notice(doc: dict) -> bool:
    """Insert a notice record. Returns True on insert, False if a row
    already exists for the unique key (DuplicateKeyError → already sent).

    The email send is best-effort: even if it returned False (Brevo failure),
    we still record the notice so the sweep doesn't keep retrying within
    the same period — the merchant won't get spammed by retry storms.
    """
    from pymongo.errors import DuplicateKeyError
    try:
        await org_quota_notices_collection.insert_one(doc)
        return True
    except DuplicateKeyError:
        return False


async def list_recent_quota_notices(
    organization_id: str,
    months: int = 3,
) -> List[dict]:
    """List recent quota notices for an org (audit / system_admin UI)."""
    from datetime import datetime as _dt, timedelta, timezone
    cutoff = (_dt.now(timezone.utc) - timedelta(days=months * 31)).isoformat()
    cursor = org_quota_notices_collection.find(
        {
            "organization_id": organization_id,
            "sent_at": {"$gte": cutoff},
        },
        {"_id": 0},
    ).sort([("sent_at", -1)]).limit(100)
    return await cursor.to_list(100)


# ============================================================================
# v5.8 / Onda 9.T — Trial-once enforcement (anti-fraud) + history tracking
# ============================================================================
#
# `has_used_trial` is the source of truth for the trial-once gate. Once True,
# never reset (except via admin grant-trial endpoint, audit-logged).
#
# `trial_history[]` is an append-only audit log of every trial subscription
# the org has ever started. Granular fields support analytics + customer
# support forensics ("did this user ever try Pro?").


async def mark_trial_used(
    organization_id: str,
    plan_slug: str,
    started_at: str,
    stripe_subscription_id: Optional[str] = None,
    billing_interval: Optional[str] = None,
) -> bool:
    """Mark org as having used a trial AND start a new trial_history entry.

    Idempotent: re-calling for the same stripe_subscription_id is a no-op
    (entry already in history). Setting has_used_trial=True is idempotent
    by design (Mongo $set on already-True is a no-op).

    Returns True if a NEW history entry was added, False if already present.
    """
    # Upsert the flag (only set if not already True — defensive)
    await organizations_collection.update_one(
        {"id": organization_id},
        {"$set": {
            "has_used_trial": True,
        }},
    )
    # Set first-trial fields only on first trial (use $setOnInsert-style guard)
    await organizations_collection.update_one(
        {"id": organization_id, "has_used_trial_at": None},
        {"$set": {
            "has_used_trial_at": started_at,
            "has_used_trial_plan_slug": plan_slug,
        }},
    )

    # Check if this trial entry already exists (idempotent)
    if stripe_subscription_id:
        existing = await organizations_collection.find_one(
            {"id": organization_id, "trial_history.stripe_subscription_id": stripe_subscription_id},
            {"_id": 0, "id": 1},
        )
        if existing:
            return False  # already recorded

    # Append new history entry
    entry = {
        "plan_slug": plan_slug,
        "stripe_subscription_id": stripe_subscription_id,
        "billing_interval": billing_interval,
        "started_at": started_at,
        "ended_at": None,
        "outcome": None,
        "cancellation_reason": None,
        "days_used": None,
        "usage_snapshot": None,
        "conversion_lag_days": None,
    }
    await organizations_collection.update_one(
        {"id": organization_id},
        {"$push": {"trial_history": entry}},
    )
    return True


async def close_trial_history_entry(
    organization_id: str,
    stripe_subscription_id: str,
    *,
    outcome: str,  # "converted" | "cancelled_during_trial" | "expired_to_free"
    ended_at: str,
    cancellation_reason: Optional[str] = None,
    usage_snapshot: Optional[Dict[str, int]] = None,
    conversion_lag_days: Optional[int] = None,
) -> bool:
    """Close the most-recent open trial_history entry for this subscription.

    Sets outcome, ended_at, days_used, usage_snapshot, conversion_lag_days.
    Idempotent: if entry already closed (outcome != None), no-op.

    Returns True if entry was patched, False if no matching open entry found.
    """
    # Compute days_used from started_at to ended_at
    org = await organizations_collection.find_one(
        {"id": organization_id, "trial_history.stripe_subscription_id": stripe_subscription_id},
        {"_id": 0, "trial_history": 1},
    )
    if not org:
        return False

    history = org.get("trial_history", [])
    target_idx = None
    for i, entry in enumerate(history):
        if entry.get("stripe_subscription_id") == stripe_subscription_id and not entry.get("outcome"):
            target_idx = i
            break

    if target_idx is None:
        return False  # no open entry

    started_at_str = history[target_idx].get("started_at")
    days_used = None
    if started_at_str and ended_at:
        try:
            from datetime import datetime as _dt
            s = _dt.fromisoformat(started_at_str.replace("Z", "+00:00"))
            e = _dt.fromisoformat(ended_at.replace("Z", "+00:00"))
            days_used = max(0, (e - s).days)
        except (ValueError, TypeError):
            pass

    # Patch via positional operator
    update_doc = {
        f"trial_history.{target_idx}.outcome": outcome,
        f"trial_history.{target_idx}.ended_at": ended_at,
        f"trial_history.{target_idx}.days_used": days_used,
    }
    if cancellation_reason is not None:
        update_doc[f"trial_history.{target_idx}.cancellation_reason"] = cancellation_reason
    if usage_snapshot is not None:
        update_doc[f"trial_history.{target_idx}.usage_snapshot"] = usage_snapshot
    if conversion_lag_days is not None:
        update_doc[f"trial_history.{target_idx}.conversion_lag_days"] = conversion_lag_days

    await organizations_collection.update_one(
        {"id": organization_id},
        {"$set": update_doc},
    )
    return True


async def grant_trial_override(
    organization_id: str,
    admin_user_id: str,
    reason: str,
) -> bool:
    """Admin-only: reset has_used_trial to False so the org can use a trial again.

    Use cases: customer support comp, partner deal, beta program.
    Audit-logged via AuditLog.

    Does NOT clear trial_history — the audit trail of past trials is preserved.
    """
    await organizations_collection.update_one(
        {"id": organization_id},
        {"$set": {
            "has_used_trial": False,
            # Don't clear has_used_trial_at / has_used_trial_plan_slug — keep
            # the historical info for context. The audit log records who/why
            # the override was applied.
        }},
    )
    return True


async def get_trial_history(organization_id: str) -> List[dict]:
    """Return the full trial history of an org (chronological)."""
    org = await organizations_collection.find_one(
        {"id": organization_id},
        {"_id": 0, "trial_history": 1, "has_used_trial": 1, "has_used_trial_at": 1},
    )
    if not org:
        return []
    return org.get("trial_history", [])


# ── Onda 14: trial rotation on plan change during trial ─────────────────────


async def rotate_trial_history_on_plan_change(
    organization_id: str,
    stripe_subscription_id: str,
    *,
    new_plan_slug: str,
    new_billing_interval: Optional[str],
    rotated_at: str,
) -> bool:
    """Close the open trial_history entry for this sub and append a new one
    on the new plan.

    Onda 14 (Strategy A) — when a user changes plan while their Stripe
    subscription is still in `trialing` state (e.g. trialing on `core`
    then upgrading to `pro`), the underlying Stripe sub keeps the same
    `trial_end` and just swaps the price item. Without this rotation,
    `trial_history` would still show the trial as belonging to the
    original plan, and analytics would say "user trialed core" while
    in reality the trial was effectively spent on pro.

    Mechanics:
      1. Find the most-recent OPEN entry (outcome=None) for this
         stripe_subscription_id.
      2. Close it with outcome="upgraded_during_trial", ended_at=now,
         days_used computed from started_at.
      3. Append a new open entry with the new plan_slug, started_at=now,
         outcome=None.

    Idempotent: if no open entry exists (e.g. the user is not actually
    trialing, or the rotation already happened), returns False without
    side effects.

    Returns True if rotation happened, False if no-op.
    """
    org = await organizations_collection.find_one(
        {"id": organization_id, "trial_history.stripe_subscription_id": stripe_subscription_id},
        {"_id": 0, "trial_history": 1},
    )
    if not org:
        return False

    history = org.get("trial_history", [])
    target_idx = None
    target_entry = None
    for i in range(len(history) - 1, -1, -1):
        e = history[i]
        if (
            e.get("stripe_subscription_id") == stripe_subscription_id
            and e.get("outcome") is None
            and e.get("ended_at") is None
        ):
            target_idx = i
            target_entry = e
            break

    if target_idx is None:
        # No open entry → user wasn't trialing on this sub, nothing to rotate.
        return False

    # If the new plan equals the entry's current plan_slug, no actual rotation
    # needed (could happen if modify is called with the same plan).
    if target_entry.get("plan_slug") == new_plan_slug:
        return False

    # Compute days_used between started_at and rotated_at
    days_used = None
    started_at_str = target_entry.get("started_at")
    if started_at_str:
        try:
            started_dt = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
            rotated_dt = datetime.fromisoformat(rotated_at.replace("Z", "+00:00"))
            days_used = max(0, (rotated_dt - started_dt).days)
        except (ValueError, TypeError):
            pass

    # 1) Close the open entry
    await organizations_collection.update_one(
        {"id": organization_id},
        {"$set": {
            f"trial_history.{target_idx}.outcome": "upgraded_during_trial",
            f"trial_history.{target_idx}.ended_at": rotated_at,
            f"trial_history.{target_idx}.days_used": days_used,
        }},
    )

    # 2) Append a new open entry for the new plan on the SAME sub
    new_entry = {
        "plan_slug": new_plan_slug,
        "stripe_subscription_id": stripe_subscription_id,
        "billing_interval": new_billing_interval,
        "started_at": rotated_at,
        "ended_at": None,
        "outcome": None,
        "cancellation_reason": None,
        "days_used": None,
        "usage_snapshot": None,
        "conversion_lag_days": None,
        # Onda 14 — record that this entry was opened mid-sub via rotation
        # (vs. a fresh trial start). Useful for analytics querying.
        "rotated_from_plan": target_entry.get("plan_slug"),
    }
    await organizations_collection.update_one(
        {"id": organization_id},
        {"$push": {"trial_history": new_entry}},
    )
    return True
