"""Stripe Service -- single point of contact with the Stripe API.

Responsibilities:
  - Lazy Stripe initialization (graceful no-op when STRIPE_SECRET_KEY is unset)
  - Customer creation/lookup
  - Checkout Session creation (hosted page -- minimal PCI scope)
  - Customer Portal session creation
  - Webhook signature verification + event dispatch
  - Event handlers that delegate to plan_provisioning

Design:
  - Stripe is the billing rail, NOT the source of truth for access.
  - All access decisions read from internal DB (module_access.py).
  - Webhook handlers update internal DB via plan_provisioning.

v5.1 hardening:
  - All blocking Stripe SDK calls wrapped in asyncio.to_thread (B3).
  - Redirect URLs target /settings (not /settings/billing) (B1).
  - Exception classes use stripe.* not stripe.error.* for >=5.0 compat (H4).

v5.5 hardening:
  - Duplicate subscription prevention: pre-flight guard in create_checkout_session.
  - One-subscription-per-org invariant enforced before creating Stripe Checkout.
  - Stale subscription cleanup in checkout webhook handler.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models.commercial_plan import BillingEvent
from repositories import billing_repository

logger = logging.getLogger(__name__)

# Lazy Stripe import -- avoids hard crash if stripe is not installed
_stripe = None


def _get_stripe():
    """Lazy-import and configure Stripe SDK."""
    global _stripe
    if _stripe is not None:
        return _stripe

    try:
        import stripe
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
        stripe.api_version = "2024-06-20"
        _stripe = stripe
        if not stripe.api_key:
            logger.warning("STRIPE_SECRET_KEY not set -- Stripe operations will fail")
        return stripe
    except ImportError:
        logger.error("stripe package not installed -- pip install stripe")
        raise RuntimeError("stripe package not installed")


def _stripe_configured() -> bool:
    """Check if Stripe is properly configured."""
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


# ==============================================================================
# Customer management
# ==============================================================================

async def get_or_create_stripe_customer(
    org_id: str,
    org_name: str,
    email: str,
) -> str:
    """Get or create a Stripe customer for the organization.

    If the org already has a stripe_customer_id, verify it exists in Stripe.
    Otherwise, create a new customer and store the ID on the org.

    Returns the Stripe customer ID (cus_xxx).
    """
    stripe = _get_stripe()

    # Check if org already has a Stripe customer
    org = await billing_repository.get_org_billing_summary(org_id)
    existing_cus = org.get("stripe_customer_id") if org else None

    if existing_cus:
        try:
            await asyncio.to_thread(stripe.Customer.retrieve, existing_cus)
            return existing_cus
        except stripe.InvalidRequestError:
            logger.warning("Stripe customer '%s' not found -- creating new", existing_cus)

    # Create new Stripe customer
    customer = await asyncio.to_thread(
        stripe.Customer.create,
        name=org_name,
        email=email,
        metadata={
            "org_id": org_id,
            "platform": "afianco",
        },
    )

    # Store on org
    await billing_repository.update_org_billing_fields(org_id, {
        "stripe_customer_id": customer.id,
        "billing_email": email,
    })

    logger.info("Created Stripe customer '%s' for org '%s'", customer.id, org_id)
    return customer.id


# ==============================================================================
# Checkout Session
# ==============================================================================

class DuplicateSubscriptionError(Exception):
    """Raised when attempting to create a checkout for an org that already has an active subscription."""

    def __init__(self, message: str, *, redirect_to_portal: bool = False, org_id: str = ""):
        super().__init__(message)
        self.redirect_to_portal = redirect_to_portal
        self.org_id = org_id


class SamePlanError(Exception):
    """Raised when attempting to checkout for the plan the org is already on."""
    pass


class NoActiveSubscriptionError(Exception):
    """Raised when modify is called but org has no active Stripe subscription."""
    pass


class PlanChangeRateLimitError(Exception):
    """Raised when org exceeds plan change rate limit."""
    pass


# In-memory rate limiter for plan changes: {org_id: [timestamp, ...]}
_plan_change_timestamps: dict = {}
_MAX_PLAN_CHANGES = 3
_PLAN_CHANGE_WINDOW_HOURS = 24


async def create_checkout_session(
    org_id: str,
    org_name: str,
    email: str,
    plan_slug: str,
    interval: str = "month",  # "month" or "year"
    success_url: str = "",
    cancel_url: str = "",
    addon_slugs: Optional[List[str]] = None,
) -> dict:
    """Create a Stripe Checkout Session for plan purchase.

    v5.5 hardening: Pre-flight guards enforce the one-subscription-per-org
    invariant.  Before touching Stripe, we check the org's current billing
    state and reject or redirect when:
      - Org already has an active/trialing subscription → redirect to portal
      - Org is on the requested plan already → error
      - Org is past_due → redirect to portal to fix payment first

    v5.8 / Onda 2: optional `addon_slugs` extends the checkout with one
    additional line_item per add-on. When None or empty, the call is
    BYTE-IDENTICAL to the previous behaviour — single line_item, exactly
    as today. When populated, each add-on is appended as an extra item
    with `metadata.is_addon=true` so the webhook handler can distinguish
    main plan from add-ons. Add-on validation rules (compatible_plans,
    is_addon flag, stripe_price_id present) are enforced before any
    Stripe API call.

    Returns dict with session_id and url for client-side redirect.

    Raises:
      DuplicateSubscriptionError: org already has an active Stripe subscription.
      SamePlanError: org is already on the requested plan.
      ValueError: plan not found, not self-serve, no Stripe price configured,
                  or an add-on is incompatible / unknown / lacks Stripe price.
    """
    stripe = _get_stripe()

    # ── v5.5: Pre-flight subscription guard (DB-side) ─────────────────────
    guard = await billing_repository.get_org_subscription_guard(org_id)

    if guard["has_active_subscription"]:
        # Sub-case 1: same plan — reject outright
        if guard["commercial_plan_slug"] == plan_slug:
            raise SamePlanError(
                f"Organization is already subscribed to '{plan_slug}'. "
                "Use the Customer Portal to manage your subscription."
            )
        # Sub-case 2: past_due — must fix payment via portal, not create new sub
        if guard["billing_status"] == "past_due":
            raise DuplicateSubscriptionError(
                "Organization has a past-due subscription. "
                "Please update your payment method in the billing portal before changing plans.",
                redirect_to_portal=True,
                org_id=org_id,
            )
        # Sub-case 3: active/trialing with a different plan request — use
        # modify-subscription endpoint for in-place plan changes, not a
        # new checkout that would create a duplicate subscription.
        if guard["stripe_subscription_id"]:
            raise DuplicateSubscriptionError(
                f"Organization already has an active Stripe subscription "
                f"(status={guard['billing_status']}, plan={guard['commercial_plan_slug']}). "
                "Use the billing portal to change plans, or cancel the existing subscription first.",
                redirect_to_portal=True,
                org_id=org_id,
            )

    # ── Onda 20 Layer 1: Stripe-side authoritative guard ──────────────────
    # The DB-side guard above only sees state the webhook has already
    # propagated. In localhost (no `stripe listen`) and on webhook delays
    # in production, an org may have just completed a checkout and have
    # an active Stripe sub that the DB doesn't yet know about. Without
    # this remote check, a second checkout attempt would create a
    # duplicate subscription → double billing.
    #
    # Source-of-truth invariant: ONE active|trialing sub per Stripe customer.
    # If Stripe says one already exists, refuse to create another.
    cust_id = guard.get("stripe_customer_id")
    if cust_id:
        try:
            remote_active = await asyncio.to_thread(
                _list_active_or_trialing_subs_sync, stripe, cust_id,
            )
        except Exception as e:
            # Stripe API failure: log but don't block — the DB guard above
            # is at least some defense, and Layer 2 (post-checkout cleanup)
            # will catch any duplicate that slips through.
            logger.warning(
                "create_checkout_session: Stripe pre-flight list failed for "
                "customer=%s — falling back to DB-only guard: %s",
                cust_id, e,
            )
            remote_active = []

        if remote_active:
            latest = remote_active[0]
            logger.warning(
                "create_checkout_session: Stripe-side guard caught duplicate — "
                "org=%s already has active sub %s on Stripe (DB had stripe_subscription_id=%s). "
                "Refusing new checkout; client should use modify_subscription instead.",
                org_id, latest.get("id"), guard.get("stripe_subscription_id"),
            )
            raise DuplicateSubscriptionError(
                "An active Stripe subscription already exists for this account. "
                "Use the change-plan flow instead of creating a new checkout.",
                redirect_to_portal=False,
                org_id=org_id,
            )

    # ── v5.6: Free plan is never a checkout target ──────────────────────
    if plan_slug == "free":
        raise ValueError(
            "The Free plan is the system baseline and cannot be purchased "
            "through checkout.  Use the billing portal to downgrade, or "
            "cancel the current subscription to revert to Free."
        )

    # ── Plan validation ───────────────────────────────────────────────────

    # Get the commercial plan
    plan = await billing_repository.get_commercial_plan(plan_slug)
    if not plan:
        raise ValueError(f"Commercial plan '{plan_slug}' not found")

    if not plan.get("is_self_serve"):
        raise ValueError(f"Plan '{plan_slug}' is not self-serve -- contact sales")

    # Determine the Stripe price ID
    # v5.8 / Onda 5 — grandfather override: if the org has legacy_pricing_lock
    # AND an explicit legacy_price_ids[plan_slug] from the migration snapshot,
    # use THAT price instead of the catalog price. Customers who subscribed
    # before the rebrand keep paying their original Stripe price for the
    # selected plan, even when they upgrade/modify via this checkout flow.
    legacy_price_id = None
    org_doc_for_legacy = await billing_repository.get_org_billing_summary(org_id) or {}
    if org_doc_for_legacy.get("legacy_pricing_lock"):
        legacy_map = org_doc_for_legacy.get("legacy_price_ids") or {}
        if isinstance(legacy_map, dict):
            legacy_price_id = legacy_map.get(plan_slug)

    if legacy_price_id:
        price_id = legacy_price_id
        logger.info(
            "create_checkout_session: org=%s using LEGACY price_id=%s for plan=%s",
            org_id, legacy_price_id, plan_slug,
        )
    elif interval == "year" and plan.get("stripe_price_id_yearly"):
        price_id = plan["stripe_price_id_yearly"]
    elif plan.get("stripe_price_id_monthly"):
        price_id = plan["stripe_price_id_monthly"]
    else:
        raise ValueError(
            f"No Stripe price configured for plan '{plan_slug}' interval '{interval}'. "
            "Set stripe_price_id_monthly/yearly on the commercial plan first."
        )

    # ── v5.8 / Onda 2: validate + resolve add-ons (if any) ────────────────
    #
    # Each add-on becomes one extra Stripe line_item with metadata flagging
    # it as an add-on. We pre-fetch the CommercialPlan for each addon_slug
    # and run all validations BEFORE the Stripe API call so a misconfigured
    # add-on aborts the whole checkout cleanly (no partial Stripe state).
    addon_line_items: List[Dict[str, Any]] = []
    if addon_slugs:
        for addon_slug in addon_slugs:
            addon_plan = await billing_repository.get_commercial_plan(addon_slug)
            if not addon_plan:
                raise ValueError(f"Add-on plan '{addon_slug}' not found.")
            if not addon_plan.get("is_addon"):
                raise ValueError(
                    f"Plan '{addon_slug}' is not an add-on (is_addon=False)."
                )
            compat = addon_plan.get("compatible_plans") or []
            if compat and plan_slug not in compat:
                raise ValueError(
                    f"Add-on '{addon_slug}' is not compatible with plan "
                    f"'{plan_slug}' (allowed: {compat})."
                )
            addon_price_id = addon_plan.get("stripe_price_id_monthly")
            if not addon_price_id:
                raise ValueError(
                    f"Add-on '{addon_slug}' has no stripe_price_id_monthly."
                )
            addon_line_items.append({
                "price": addon_price_id,
                "quantity": 1,
                "metadata": {
                    "is_addon": "true",
                    "addon_slug": addon_slug,
                    "org_id": org_id,
                },
            })

    # ── Customer ──────────────────────────────────────────────────────────

    # Get or create customer
    customer_id = await get_or_create_stripe_customer(org_id, org_name, email)

    # ── Build checkout session ────────────────────────────────────────────
    #
    # Main plan is always the first line_item. Add-ons (if any) follow.
    # Note: Stripe stores `metadata` only on subscription_items, not on
    # checkout line_items at session creation time — but we pass it in
    # `subscription_data.metadata` AND in each item's metadata so the
    # webhook handler can distinguish main vs add-on items reliably.
    main_line_item: Dict[str, Any] = {
        "price": price_id,
        "quantity": 1,
    }

    session_params: Dict[str, Any] = {
        "customer": customer_id,
        "mode": "subscription",
        "line_items": [main_line_item] + addon_line_items,
        "success_url": success_url or f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/settings?billing_success=1&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": cancel_url or f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/settings?billing_cancelled=1",
        "metadata": {
            "org_id": org_id,
            "plan_slug": plan_slug,
            "interval": interval,
            "addon_slugs": ",".join(addon_slugs) if addon_slugs else "",
        },
        "subscription_data": {
            "metadata": {
                "org_id": org_id,
                "plan_slug": plan_slug,
                "addon_slugs": ",".join(addon_slugs) if addon_slugs else "",
            },
        },
    }

    # v5.8 / Onda 9.T — Trial-once gate.
    # PREVIOUSLY used `trial_ends_at is not None` which was buggy: that field
    # is reset to None during deprovision (cancel→free), allowing the
    # cancel-and-retry-with-trial exploit (free 42d × 3 plans).
    # NOW uses `has_used_trial` which is set permanently by webhook on first
    # trial start and NEVER reset (except by admin grant-trial endpoint).
    if plan.get("trial_days", 0) > 0:
        org = await billing_repository.get_org_billing_summary(org_id)
        has_used = bool(org and org.get("has_used_trial"))
        if not has_used:
            session_params["subscription_data"]["trial_period_days"] = plan["trial_days"]
            session_params["payment_method_collection"] = "always"
        else:
            logger.info(
                "[trial-once] org=%s already has_used_trial=True (first trial on %s at %s) — "
                "checkout session will charge immediately, no trial_period_days set",
                org_id,
                org.get("has_used_trial_plan_slug"),
                org.get("has_used_trial_at"),
            )

    session = await asyncio.to_thread(
        lambda: stripe.checkout.Session.create(**session_params)
    )

    logger.info(
        "Created Checkout Session '%s' for org '%s', plan '%s' (%s)",
        session.id, org_id, plan_slug, interval,
    )

    return {
        "session_id": session.id,
        "url": session.url,
    }


# ==============================================================================
# Onda 20 — One-active-sub-per-customer invariant helpers
# ==============================================================================

def _list_active_or_trialing_subs_sync(stripe_module, customer_id: str) -> List[Dict[str, Any]]:
    """Sync helper (run inside asyncio.to_thread) — returns ACTIVE + TRIALING
    subs for a customer, sorted newest-first.

    Used by the Layer 1 pre-flight guard in create_checkout_session and
    by the Layer 2 cleanup sweep. Returns plain dicts so the async caller
    doesn't have to worry about Stripe SDK object lifecycles.
    """
    out: List[Dict[str, Any]] = []
    for status in ("active", "trialing"):
        page = stripe_module.Subscription.list(
            customer=customer_id,
            status=status,
            limit=20,  # generous — orgs should never have this many
        )
        for sub in page.data:
            # Convert Stripe object to plain dict for safe async use
            out.append({
                "id": sub.id,
                "status": sub.status,
                "created": getattr(sub, "created", 0) or 0,
                "cancel_at_period_end": bool(getattr(sub, "cancel_at_period_end", False)),
            })
    out.sort(key=lambda s: s.get("created", 0), reverse=True)
    return out


async def _cancel_orphan_subs_for_customer(
    customer_id: str,
    keep_sub_id: str,
    *,
    org_id: Optional[str] = None,
    reason: str = "onda_20_orphan_cleanup",
) -> int:
    """Onda 20 Layer 2 — cancel every active/trialing Stripe sub on this
    customer EXCEPT `keep_sub_id`. Used as a defensive sweep after a new
    checkout completes, to enforce the one-active-sub invariant in case
    Layer 1 was bypassed (race / missing webhook / manual operator
    intervention).

    Idempotent: if the only active sub is keep_sub_id, returns 0.
    Best-effort: failures on individual cancels are logged, not raised
    (the new sub is already provisioned and we don't want to break the
    user's checkout success flow over a cleanup hiccup).

    Returns the count of subs cancelled.
    """
    stripe = _get_stripe()
    if stripe is None:
        return 0
    try:
        all_subs = await asyncio.to_thread(
            _list_active_or_trialing_subs_sync, stripe, customer_id,
        )
    except Exception as e:
        logger.warning(
            "_cancel_orphan_subs_for_customer: list failed customer=%s: %s",
            customer_id, e,
        )
        return 0

    cancelled = 0
    for sub_summary in all_subs:
        sid = sub_summary.get("id")
        if not sid or sid == keep_sub_id:
            continue
        try:
            await asyncio.to_thread(
                stripe.Subscription.cancel,
                sid,
            )
            cancelled += 1
            logger.warning(
                "[onda_20] Cancelled ORPHAN Stripe sub %s on customer %s "
                "(org=%s, kept=%s, reason=%s)",
                sid, customer_id, org_id, keep_sub_id, reason,
            )
        except Exception as e:
            logger.error(
                "[onda_20] Failed to cancel orphan sub %s on customer %s: %s",
                sid, customer_id, e, exc_info=True,
            )
    return cancelled


# ==============================================================================
# Subscription Modify (upgrade / downgrade in-place)
# ==============================================================================

def _is_main_plan_item(item: Dict[str, Any]) -> bool:
    """Decide whether a Stripe subscription item represents the MAIN plan
    (vs an add-on). True if the item is NOT explicitly tagged as add-on.

    This works for:
      · Subs created BEFORE Onda 2 (no metadata at all → treated as main)
      · Subs created AFTER Onda 2 (main has metadata.is_addon != "true",
        add-ons have metadata.is_addon == "true")

    Centralised in one helper so every call site (modify_subscription +
    webhook handler) uses identical detection logic.
    """
    md = (item or {}).get("metadata") or {}
    return md.get("is_addon") != "true"


async def modify_subscription(
    org_id: str,
    plan_slug: Optional[str] = None,
    interval: str = "month",
    addon_changes: Optional[List[Dict[str, Any]]] = None,
) -> dict:
    """Modify an existing Stripe subscription: change main plan AND/OR add/remove add-ons.

    Uses Subscription.modify() for in-place upgrade/downgrade with automatic
    proration. The webhook subscription.updated handles re-provisioning.

    If the subscription is set to cancel_at_period_end, the cancellation is
    reversed before modifying the plan.

    BACKWARD-COMPATIBLE behaviour (v5.8 / Onda 2):
      · Calling with ONLY (org_id, plan_slug, interval) → IDENTICAL to pre-Onda-2:
        a single item is modified to the new price, no add-on touched.
      · Passing `addon_changes=None` and `plan_slug=None` is invalid (nothing to do).
      · Passing only `addon_changes` (no plan_slug) → only add-ons modified;
        main plan unchanged. Use case: customer adds/removes a pack from the
        billing UI without changing tier.
      · Passing both → main plan AND add-ons modified atomically in a single
        Stripe API call.

    `addon_changes` shape:
      [
        {"action": "add",             "slug": "addon_x", "quantity": 1},
        {"action": "remove",          "slug": "addon_y"},
        {"action": "update_quantity", "slug": "addon_z", "quantity": 3},
      ]

    Returns dict with status and new plan info.

    Raises:
        NoActiveSubscriptionError: org has no active Stripe subscription.
        SamePlanError: org is already on the requested plan AND no addon_changes given.
        ValueError: plan not found, not self-serve, no Stripe price, addon
                    incompatible / unknown / lacks price, or invalid action.
    """
    if plan_slug is None and not addon_changes:
        raise ValueError(
            "modify_subscription requires either plan_slug or addon_changes "
            "(or both). Nothing to modify."
        )

    stripe = _get_stripe()

    # ── Load org billing state ────────────────────────────────────────────
    guard = await billing_repository.get_org_subscription_guard(org_id)

    if not guard.get("stripe_subscription_id"):
        raise NoActiveSubscriptionError(
            "Organization has no active Stripe subscription. Use checkout instead."
        )

    if guard.get("billing_status") == "past_due":
        raise ValueError(
            "Subscription is past due. Please update your payment method "
            "in the billing portal before changing plans."
        )

    # ── Rate limit: max N plan changes per 24h ────────────────────────────
    # NOTE: rate limit applies to ALL modifications (main plan or add-ons)
    # to keep one shared throttle. An admin spamming addon adds is treated
    # the same as spamming plan changes — both produce Stripe API calls.
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=_PLAN_CHANGE_WINDOW_HOURS)
    timestamps = _plan_change_timestamps.get(org_id, [])
    timestamps = [ts for ts in timestamps if ts > cutoff]
    if len(timestamps) >= _MAX_PLAN_CHANGES:
        raise PlanChangeRateLimitError(
            f"Too many plan changes. Maximum {_MAX_PLAN_CHANGES} changes per "
            f"{_PLAN_CHANGE_WINDOW_HOURS} hours. Please try again later."
        )

    # ── Same-plan guard (only when actually changing plan) ────────────────
    if plan_slug is not None and guard.get("commercial_plan_slug") == plan_slug and not addon_changes:
        raise SamePlanError(
            f"Organization is already on plan '{plan_slug}' and no add-on changes were requested."
        )

    # ── Resolve new main-plan price (only if plan_slug was passed) ────────
    # v5.8 / Onda 5 — grandfather override: legacy_pricing_lock orgs reuse
    # their snapshotted price_id instead of the catalog price. See the
    # twin block in `create_checkout_session` for the rationale.
    new_price_id: Optional[str] = None
    if plan_slug is not None and guard.get("commercial_plan_slug") != plan_slug:
        org_doc_for_legacy = await billing_repository.get_org_billing_summary(org_id) or {}
        legacy_price_id = None
        if org_doc_for_legacy.get("legacy_pricing_lock"):
            legacy_map = org_doc_for_legacy.get("legacy_price_ids") or {}
            if isinstance(legacy_map, dict):
                legacy_price_id = legacy_map.get(plan_slug)

        if legacy_price_id:
            new_price_id = legacy_price_id
            logger.info(
                "modify_subscription: org=%s using LEGACY price_id=%s for plan=%s",
                org_id, legacy_price_id, plan_slug,
            )
        else:
            plan = await billing_repository.get_commercial_plan(plan_slug)
            if not plan:
                raise ValueError(f"Plan '{plan_slug}' not found.")

            if not plan.get("is_self_serve"):
                raise ValueError(f"Plan '{plan_slug}' is not available for self-service.")

            price_key = f"stripe_price_id_{'yearly' if interval == 'year' else 'monthly'}"
            new_price_id = plan.get(price_key)
            if not new_price_id:
                raise ValueError(
                    f"Plan '{plan_slug}' has no Stripe price for interval '{interval}'."
            )

    # ── Retrieve current subscription from Stripe ─────────────────────────
    sub_id = guard["stripe_subscription_id"]
    raw_sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
    sub = _normalize_stripe_object(raw_sub)  # v15 compat: see _normalize_stripe_object

    if not sub.get("items") or not sub["items"].get("data"):
        raise ValueError("Stripe subscription has no items.")

    items = sub["items"]["data"]

    # Identify the main plan item (NOT an add-on). Falls back to items[0]
    # for legacy subs created before Onda 2 (no metadata).
    main_item = next((it for it in items if _is_main_plan_item(it)), items[0])
    main_item_id = main_item["id"]

    # Build a slug→item lookup for existing add-on items (for remove/update_quantity).
    # An item is recognised as a specific add-on if its metadata.addon_slug matches.
    addon_items_by_slug: Dict[str, Dict[str, Any]] = {}
    for it in items:
        md = (it or {}).get("metadata") or {}
        if md.get("is_addon") == "true" and md.get("addon_slug"):
            addon_items_by_slug[md["addon_slug"]] = it

    # ── If cancel_at_period_end, reverse the cancellation first ───────────
    if sub.get("cancel_at_period_end"):
        await asyncio.to_thread(
            stripe.Subscription.modify,
            sub_id,
            cancel_at_period_end=False,
        )
        logger.info(
            "modify_subscription: reversed cancel_at_period_end for sub %s org %s",
            sub_id, org_id,
        )

    # ── Build the items[] payload for Stripe.Subscription.modify ──────────
    items_payload: List[Dict[str, Any]] = []

    # Main plan change (only if requested)
    if new_price_id is not None:
        items_payload.append({"id": main_item_id, "price": new_price_id})

    # Add-on changes (each operation validated before generating payload)
    for change in (addon_changes or []):
        action = change.get("action")
        slug = change.get("slug")
        if not action or not slug:
            raise ValueError(f"Invalid addon_change: {change} (missing action or slug)")

        if action == "add":
            if slug in addon_items_by_slug:
                raise ValueError(
                    f"Add-on '{slug}' is already on the subscription. "
                    "Use 'update_quantity' to change quantity."
                )
            addon_plan = await billing_repository.get_commercial_plan(slug)
            if not addon_plan or not addon_plan.get("is_addon"):
                raise ValueError(f"Add-on '{slug}' not found or not an add-on plan.")
            target_plan_slug = plan_slug or guard.get("commercial_plan_slug")
            compat = addon_plan.get("compatible_plans") or []
            if compat and target_plan_slug not in compat:
                raise ValueError(
                    f"Add-on '{slug}' is not compatible with plan '{target_plan_slug}'."
                )
            addon_price_id = addon_plan.get("stripe_price_id_monthly")
            if not addon_price_id:
                raise ValueError(f"Add-on '{slug}' has no stripe_price_id_monthly.")
            items_payload.append({
                "price": addon_price_id,
                "quantity": int(change.get("quantity", 1)),
                "metadata": {
                    "is_addon": "true",
                    "addon_slug": slug,
                    "org_id": org_id,
                },
            })

        elif action == "remove":
            existing = addon_items_by_slug.get(slug)
            if not existing:
                raise ValueError(
                    f"Cannot remove add-on '{slug}': not found on this subscription."
                )
            # Stripe API: passing {"id": ..., "deleted": true} removes the item.
            items_payload.append({"id": existing["id"], "deleted": True})

        elif action == "update_quantity":
            existing = addon_items_by_slug.get(slug)
            if not existing:
                raise ValueError(
                    f"Cannot update add-on '{slug}': not found on this subscription."
                )
            new_qty = int(change.get("quantity", 1))
            if new_qty < 1:
                raise ValueError(
                    f"Add-on '{slug}' quantity must be >= 1 (use 'remove' to drop)."
                )
            items_payload.append({"id": existing["id"], "quantity": new_qty})

        else:
            raise ValueError(
                f"Unknown addon_change action: '{action}' "
                "(expected: add | remove | update_quantity)"
            )

    if not items_payload:
        # Defensive: should not happen given the early check, but be explicit.
        raise ValueError("modify_subscription produced empty items[] — nothing to send to Stripe.")

    # ── Onda 15 (Strategy B) — end trial on plan change ───────────────────
    # When the user changes plan (any direction: upgrade or downgrade)
    # while the sub is still in `trialing`, force the trial to end
    # immediately. Stripe will create a prorated invoice for the new
    # plan and attempt to charge the card on file (collected at
    # checkout). Rationale: the user explicitly chose a different plan
    # and entered payment credentials at signup, so a plan change is
    # treated as a commitment. The previous Strategy A (trial follows
    # the sub) caused user confusion ("I subscribed to pro, why isn't
    # it being charged?") and is replaced.
    #
    # Cancel-during-trial (no plan change) is unchanged — Onda 9.T
    # still forces at_period_end=True so the user keeps access until
    # trial_end without charge.
    #
    # Addon-only changes (no plan_slug) do NOT end the trial — the
    # main plan stays on its current trial and the addon is added
    # to the existing sub at the addon's standard pricing.
    # Onda 15 — read current Stripe-side status to detect trial state.
    # We trust Stripe over the DB guard because the webhook may have
    # lagged (especially in localhost) and DB.billing_status could be
    # stale; the sub object retrieved a few lines above is fresh.
    pre_modify_status = sub.get("status")
    is_plan_change_during_trial = (
        plan_slug is not None
        and plan_slug != guard.get("commercial_plan_slug")
        and pre_modify_status == "trialing"
    )
    modify_kwargs: Dict[str, Any] = {
        "items": items_payload,
        "proration_behavior": "create_prorations",
    }
    if is_plan_change_during_trial:
        # "now" is a Stripe-recognised string that ends the trial at the
        # exact moment of the API call. Stripe will then bill prorated
        # from now to the existing current_period_end.
        modify_kwargs["trial_end"] = "now"

    # ── Modify the subscription ───────────────────────────────────────────
    modified_sub = await asyncio.to_thread(
        stripe.Subscription.modify,
        sub_id,
        **modify_kwargs,
    )

    # Record plan change timestamp for rate limiting
    _plan_change_timestamps.setdefault(org_id, []).append(now)

    logger.info(
        "modify_subscription: sub=%s org=%s plan=%s→%s addons_changed=%d (interval=%s) trial_ended=%s",
        sub_id, org_id,
        guard.get("commercial_plan_slug"),
        plan_slug or "(no change)",
        len(addon_changes or []),
        interval,
        is_plan_change_during_trial,
    )

    # Onda 13 — sync DB so /billing/status reflects the new plan/addon
    # state immediately after the API response. Without this, the
    # frontend refresh after an upgrade shows the OLD plan until the
    # customer.subscription.updated webhook arrives (1-10s production,
    # never in localhost without `stripe listen`). Same pattern as
    # Onda 12 cancel sync. Wrapped: a Mongo-side failure must not 5xx
    # the API call — Stripe is canonical, the webhook handler is the
    # safety net.
    db_synced = False
    db_sync_error: Optional[str] = None
    try:
        # Re-fetch normalized sub so we see the post-modify state
        # (modified_sub may not include all fields with the same shape).
        sub_after = _normalize_stripe_object(modified_sub)
        cpe_dt = None
        cpe_ts = sub_after.get("current_period_end")
        if cpe_ts:
            cpe_dt = datetime.fromtimestamp(cpe_ts, tz=timezone.utc)
        new_status = sub_after.get("status", "active")
        new_cancel_at_period_end = bool(sub_after.get("cancel_at_period_end", False))

        if plan_slug is not None and plan_slug != guard.get("commercial_plan_slug"):
            # Plan change → re-provision (cancels old module_subs, creates new ones,
            # writes commercial_plan_slug + billing_status + interval + period_end).
            from services import plan_provisioning
            await plan_provisioning.provision_commercial_plan(
                org_id=org_id,
                plan_slug=plan_slug,
                assigned_by="stripe",
                stripe_subscription_id=sub_id,
                billing_status=new_status,
                current_period_end=cpe_dt,
            )
            # provision_commercial_plan does not write billing_interval or
            # cancel_at_period_end — patch them explicitly.
            await billing_repository.update_org_billing_fields(org_id, {
                "billing_interval": interval,
                "cancel_at_period_end": new_cancel_at_period_end,
            })

            # Onda 15 (Strategy B) — if the plan change happened while
            # trialing, the trial was just ended via trial_end="now".
            # Close the open trial_history entry with outcome
            # "ended_via_upgrade" so analytics record "user upgraded
            # mid-trial, became paying customer here". We do NOT open a
            # new trial entry on the new plan because there is no longer
            # a trial — the sub is now active and being charged.
            if is_plan_change_during_trial:
                try:
                    ended_at_iso = datetime.now(timezone.utc).isoformat()
                    closed = await billing_repository.close_trial_history_entry(
                        organization_id=org_id,
                        stripe_subscription_id=sub_id,
                        outcome="ended_via_upgrade",
                        ended_at=ended_at_iso,
                    )
                    if closed:
                        logger.info(
                            "modify_subscription: org=%s sub=%s closed "
                            "trial_history (outcome=ended_via_upgrade) — "
                            "trial terminated, paid plan=%s active",
                            org_id, sub_id, plan_slug,
                        )
                except Exception as trial_err:
                    logger.error(
                        "modify_subscription: org=%s sub=%s trial_history "
                        "close failed: %s (main provision succeeded)",
                        org_id, sub_id, trial_err, exc_info=True,
                    )
            elif new_status == "trialing":
                # Edge case: plan_slug was unchanged (addon-only modify)
                # AND sub is still trialing → no trial state change to
                # record. Intentional no-op.
                pass
        else:
            # Addon-only change (no plan change) → just sync flags.
            await billing_repository.update_org_billing_fields(org_id, {
                "billing_status": new_status,
                "cancel_at_period_end": new_cancel_at_period_end,
            })

        # Addon row reconcile: mirror the webhook path so AddonSubscription
        # rows reflect the current Stripe items[] state. Idempotent.
        if addon_changes:
            try:
                addon_items_from_stripe = [
                    it for it in sub_after.get("items", {}).get("data", [])
                    if not _is_main_plan_item(it)
                ]
                await billing_repository.reconcile_addons_with_stripe_items(
                    organization_id=org_id,
                    stripe_subscription_id=sub_id,
                    addon_items_from_stripe=addon_items_from_stripe,
                )
            except Exception as addon_err:
                logger.error(
                    "modify_subscription: org=%s sub=%s addon DB reconcile "
                    "failed: %s (main plan sync succeeded)",
                    org_id, sub_id, addon_err, exc_info=True,
                )

        db_synced = True
        logger.info(
            "modify_subscription: org=%s sub=%s sync DB write OK "
            "(plan=%s, status=%s, cancel_at_period_end=%s)",
            org_id, sub_id, plan_slug or "(unchanged)",
            new_status, new_cancel_at_period_end,
        )
    except Exception as e:
        db_sync_error = f"{type(e).__name__}: {str(e)[:200]}"
        logger.error(
            "modify_subscription: org=%s sub=%s Stripe modified OK but DB "
            "sync FAILED: %s. Webhook will retry on customer.subscription.updated.",
            org_id, sub_id, e, exc_info=True,
        )

    return {
        "status": "modified",
        "new_plan": plan_slug or guard.get("commercial_plan_slug"),
        "interval": interval,
        "subscription_id": modified_sub.id,
        "addon_changes_applied": len(addon_changes or []),
        # Onda 13 — caller can know whether the DB is in sync without
        # an extra round-trip to /billing/status.
        "db_synced": db_synced,
        "db_sync_error": db_sync_error,
    }


# ==============================================================================
# Cancel subscription (v5.8 / Onda 9.A — native cancel CTA)
# ==============================================================================

async def cancel_subscription(
    org_id: str,
    *,
    at_period_end: bool = True,
    reason: str = "",
) -> dict:
    """Cancel an org's active Stripe subscription.

    Two modes (chosen by `at_period_end`):
      · True  (default, recommended): Subscription.modify(cancel_at_period_end=True).
        Customer keeps full access until current_period_end, no proration
        refund. Stripe fires customer.subscription.updated immediately
        (with cancel_at_period_end=true) then customer.subscription.deleted
        when the period actually ends.
      · False (hard cancel): Subscription.cancel(). Service is revoked
        immediately. NO automatic refund (the platform owner can issue
        one manually via Stripe Dashboard).

    Idempotent: cancelling an already-cancelled sub returns the existing
    state without re-issuing Stripe API calls. Safe to retry.

    Returns dict with cancellation timing info.

    Raises:
        NoActiveSubscriptionError: org has no active sub.
    """
    stripe = _get_stripe()
    guard = await billing_repository.get_org_subscription_guard(org_id)

    sub_id = guard.get("stripe_subscription_id")
    if not sub_id:
        raise NoActiveSubscriptionError(
            "Organization has no active Stripe subscription to cancel."
        )

    raw_sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
    sub = _normalize_stripe_object(raw_sub)
    current_status = sub.get("status")
    already_period_end = sub.get("cancel_at_period_end", False)

    # v5.8 / Onda 9.T — During trial, NEVER hard-cancel: silently force
    # at_period_end=True. This preserves the trial benefit (user keeps
    # access until trial_end as agreed) and avoids the bottleneck where
    # trial cancel = immediate downgrade to free with no value delivered.
    # Frontend should also enforce this in the UI; this is defence-in-depth.
    if current_status == "trialing" and not at_period_end:
        logger.info(
            "[trial-once] org=%s cancel during trialing → forcing at_period_end=True "
            "(was: at_period_end=False)",
            org_id,
        )
        at_period_end = True

    # Idempotency short-circuits
    if at_period_end and already_period_end:
        # Onda 12 — Stripe already has cancel_at_period_end=True, but
        # the DB org doc may still show False (typical when the
        # customer.subscription.updated webhook never arrived). Write
        # the flag synchronously so the frontend sees the schedule
        # immediately on /billing/status. Idempotent: if the DB is
        # already in sync, this is a no-op write.
        try:
            await billing_repository.update_org_billing_fields(org_id, {
                "cancel_at_period_end": True,
            })
            logger.info(
                "cancel_subscription[already_cancel_at_period_end]: org=%s "
                "sub=%s synced cancel_at_period_end=True to DB",
                org_id, sub_id,
            )
        except Exception as e:
            logger.error(
                "cancel_subscription[already_cancel_at_period_end]: org=%s "
                "sub=%s DB sync failed: %s",
                org_id, sub_id, e, exc_info=True,
            )
        return {
            "status": "already_cancel_at_period_end",
            "subscription_id": sub_id,
            "current_period_end": sub.get("current_period_end"),
            "cancel_at_period_end": True,
            "reason": reason,
        }
    if not at_period_end and current_status == "canceled":
        # Onda 12 — Stripe says the sub is already canceled, BUT the DB
        # may still be stale (typical after a previous failed sync, or
        # a webhook that never arrived in localhost). Run the
        # idempotent sync deprovision here too so this short-circuit
        # path always converges to a coherent DB state. The guard in
        # plan_provisioning.deprovision_stripe_subscription makes this
        # a no-op when the org is already on free.
        db_deprovisioned = False
        db_deprovision_error: Optional[str] = None
        cancelled_addons_count = 0
        try:
            from services import plan_provisioning
            await plan_provisioning.deprovision_stripe_subscription(org_id, sub_id)
            try:
                cancelled_addons_count = (
                    await billing_repository.cancel_all_addons_by_stripe_sub(sub_id)
                )
            except Exception as addon_err:
                logger.error(
                    "cancel_subscription[already_canceled]: org=%s sub=%s "
                    "addon cleanup failed: %s",
                    org_id, sub_id, addon_err, exc_info=True,
                )
            db_deprovisioned = True
            logger.info(
                "cancel_subscription[already_canceled]: org=%s sub=%s "
                "DB reconciled (idempotent if already on free)",
                org_id, sub_id,
            )
        except Exception as e:
            db_deprovision_error = f"{type(e).__name__}: {str(e)[:200]}"
            logger.error(
                "cancel_subscription[already_canceled]: org=%s sub=%s "
                "DB reconcile FAILED: %s",
                org_id, sub_id, e, exc_info=True,
            )
        return {
            "status": "already_canceled",
            "subscription_id": sub_id,
            "cancel_at_period_end": False,
            "reason": reason,
            "db_deprovisioned": db_deprovisioned,
            "db_deprovision_error": db_deprovision_error,
            "cancelled_addons": cancelled_addons_count,
        }

    if at_period_end:
        modified = await asyncio.to_thread(
            stripe.Subscription.modify,
            sub_id,
            cancel_at_period_end=True,
            # Cancellation reason metadata — visible in Stripe Dashboard
            # for the platform owner to triage churn.
            metadata={"cancellation_reason": reason or "user_initiated"},
        )
        logger.info(
            "cancel_subscription: org=%s sub=%s mode=at_period_end period_end=%s reason=%s",
            org_id, sub_id, sub.get("current_period_end"), reason,
        )
        # Onda 12 — sync DB write so the frontend sees the schedule
        # without waiting for the customer.subscription.updated webhook.
        # Mirrors the hard-cancel sync path; here we only flip the flag
        # because the sub stays active until period_end (no module sub
        # cleanup yet — that happens at sub.deleted time).
        cancel_flag_synced = False
        try:
            await billing_repository.update_org_billing_fields(org_id, {
                "cancel_at_period_end": True,
            })
            cancel_flag_synced = True
        except Exception as e:
            logger.error(
                "cancel_subscription: org=%s sub=%s mode=at_period_end "
                "DB sync of cancel_at_period_end FAILED: %s. Webhook "
                "will retry.",
                org_id, sub_id, e, exc_info=True,
            )
        return {
            "status": "scheduled_at_period_end",
            "subscription_id": modified.id,
            "current_period_end": sub.get("current_period_end"),
            "cancel_at_period_end": True,
            "reason": reason,
            "db_cancel_flag_synced": cancel_flag_synced,
        }

    # Hard cancel — immediate revocation. Onda 12: deprovision the DB
    # synchronously after the Stripe call succeeds so the API response
    # reflects the actual post-cancel state. Without this, the
    # frontend's billing.refresh() would still see the old plan until
    # the customer.subscription.deleted webhook arrives (1-10s in
    # production, NEVER in localhost without `stripe listen`). The
    # webhook handler is still wired up as a safety net but is now
    # idempotent (plan_provisioning.deprovision_stripe_subscription
    # short-circuits if the org is already on free).
    canceled = await asyncio.to_thread(
        stripe.Subscription.cancel,
        sub_id,
    )
    logger.info(
        "cancel_subscription: org=%s sub=%s mode=immediate reason=%s "
        "Stripe-side OK, attempting sync deprovision...",
        org_id, sub_id, reason,
    )

    # Onda 12 — sync DB deprovision. Wrapped: a Mongo-side failure here
    # must NOT cause the API to return 5xx, because Stripe is already
    # canceled and the user has already lost their service. The webhook
    # remains the safety net and the audit_billing_consistency cron
    # (Onda 10 Step E.1) will surface any drift.
    db_deprovisioned = False
    db_deprovision_error: Optional[str] = None
    cancelled_addons_count = 0
    try:
        from services import plan_provisioning
        await plan_provisioning.deprovision_stripe_subscription(org_id, sub_id)
        # Onda 12 — also cancel any active AddonSubscription rows tied
        # to this Stripe sub. Mirrors what the webhook handler does at
        # services/stripe_service.py:1671-1686. Idempotent: filters
        # status="active", a later webhook call sees 0 active rows.
        try:
            cancelled_addons_count = (
                await billing_repository.cancel_all_addons_by_stripe_sub(sub_id)
            )
        except Exception as addon_err:
            # Best-effort, never abort the cancel response.
            logger.error(
                "cancel_subscription: org=%s sub=%s addon cleanup failed: %s "
                "(main deprovision succeeded; webhook will retry).",
                org_id, sub_id, addon_err, exc_info=True,
            )
        db_deprovisioned = True
        logger.info(
            "cancel_subscription: org=%s sub=%s sync deprovision OK "
            "(addons cancelled: %d)",
            org_id, sub_id, cancelled_addons_count,
        )
    except Exception as e:
        db_deprovision_error = f"{type(e).__name__}: {str(e)[:200]}"
        logger.error(
            "cancel_subscription: org=%s sub=%s Stripe canceled OK but "
            "sync DB deprovision FAILED: %s. The webhook handler will "
            "retry on customer.subscription.deleted; meanwhile the "
            "drift cron (Onda 10 E.1) will flag the inconsistency.",
            org_id, sub_id, e, exc_info=True,
        )

    return {
        "status": "canceled",
        "subscription_id": canceled.id,
        "cancel_at_period_end": False,
        "reason": reason,
        # Onda 12 — caller can know whether the DB is now in sync with
        # Stripe without an extra round-trip to /billing/status.
        "db_deprovisioned": db_deprovisioned,
        "db_deprovision_error": db_deprovision_error,
        "cancelled_addons": cancelled_addons_count,
    }


async def reactivate_subscription(org_id: str) -> dict:
    """Reverse a cancel-at-period-end before it takes effect.

    Useful for the "I changed my mind" UX: the customer scheduled
    cancellation but the period hasn't expired yet. Sets
    cancel_at_period_end=False on Stripe; webhook propagates to DB.

    Idempotent: if the sub is already not-cancel-pending, returns the
    existing state without re-issuing the Stripe call.
    """
    stripe = _get_stripe()
    guard = await billing_repository.get_org_subscription_guard(org_id)

    sub_id = guard.get("stripe_subscription_id")
    if not sub_id:
        raise NoActiveSubscriptionError(
            "Organization has no active Stripe subscription."
        )

    raw_sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
    sub = _normalize_stripe_object(raw_sub)
    if not sub.get("cancel_at_period_end"):
        return {"status": "no_op_not_cancel_pending", "subscription_id": sub_id}

    modified = await asyncio.to_thread(
        stripe.Subscription.modify,
        sub_id,
        cancel_at_period_end=False,
    )
    logger.info("reactivate_subscription: org=%s sub=%s reactivated", org_id, sub_id)

    # Onda 13 — sync the cancel_at_period_end flag to the org doc so the
    # frontend's billing.refresh() sees False immediately, without
    # waiting for the customer.subscription.updated webhook. Same
    # pattern as Onda 12 part 3.
    db_synced = False
    db_sync_error: Optional[str] = None
    try:
        await billing_repository.update_org_billing_fields(org_id, {
            "cancel_at_period_end": False,
        })
        db_synced = True
    except Exception as e:
        db_sync_error = f"{type(e).__name__}: {str(e)[:200]}"
        logger.error(
            "reactivate_subscription: org=%s sub=%s Stripe OK but DB sync "
            "FAILED: %s. Webhook will retry.",
            org_id, sub_id, e, exc_info=True,
        )

    return {
        "status": "reactivated",
        "subscription_id": modified.id,
        "cancel_at_period_end": False,
        "db_synced": db_synced,
        "db_sync_error": db_sync_error,
    }


# ==============================================================================
# Customer Portal
# ==============================================================================

async def create_portal_session(
    org_id: str,
    return_url: str = "",
) -> dict:
    """Create a Stripe Customer Portal session for card/invoice management.

    Returns dict with url for redirect.
    """
    stripe = _get_stripe()

    org = await billing_repository.get_org_billing_summary(org_id)
    customer_id = org.get("stripe_customer_id") if org else None

    if not customer_id:
        raise ValueError("Organization has no Stripe customer -- cannot open portal")

    session = await asyncio.to_thread(
        stripe.billing_portal.Session.create,
        customer=customer_id,
        return_url=return_url or f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/settings",
    )

    return {"url": session.url}


# ==============================================================================
# Webhook verification + dispatch
# ==============================================================================

def _normalize_stripe_object(obj: Any) -> Dict[str, Any]:
    """Normalize a Stripe object (Event, Session, Subscription, Account, ...) to a plain nested dict.

    Rationale:
      stripe-python v15 removed dict inheritance from StripeObject — `.get()`
      is no longer a method and triggers `__getattr__` → `KeyError: 'get'`.
      stripe-python v14 still behaved dict-like. Normalizing at trust boundaries
      (webhook entry and pull-path retrievals) keeps downstream code compatible
      across versions and guarantees plain dicts with working `.get()` access.

    Tries in order:
      1. to_dict_recursive() (public in v14)
      2. _to_dict_recursive() (private in v15, still present)
      3. to_dict() (public in both; recursive in v15)

    Returns:
        Plain nested dict. Raises ValueError if no conversion method works.
    """
    if isinstance(obj, dict):
        return obj
    for attr in ("to_dict_recursive", "_to_dict_recursive", "to_dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            result = fn()
            if isinstance(result, dict):
                return result
    raise ValueError(
        "Cannot normalize Stripe object to dict — no known conversion method found"
    )


# Backwards-compatible alias for the webhook-specific name still used internally.
_normalize_stripe_event = _normalize_stripe_object


def verify_and_construct_event(payload: bytes, sig_header: str) -> Dict[str, Any]:
    """Verify Stripe webhook signature and construct the event as a plain dict.

    Supports dual webhook secrets for isolating platform billing from
    Stripe Connect commerce events:
      - STRIPE_WEBHOOK_SECRET: platform account webhooks (subscriptions, invoices)
      - STRIPE_WEBHOOK_SECRET_CONNECT: connected account webhooks (commerce payments)

    The function tries each configured secret in order. This allows a single
    webhook endpoint to receive events from both the platform and connected
    accounts without cross-contamination.

    Returns the event normalized to a plain nested dict (see
    _normalize_stripe_event for rationale).

    Args:
        payload: Raw request body bytes.
        sig_header: Stripe-Signature header value.

    Returns:
        Plain dict representation of the Stripe Event.

    Raises:
        ValueError: On invalid signature or no secrets configured.
    """
    stripe = _get_stripe()
    platform_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    connect_secret = os.environ.get("STRIPE_WEBHOOK_SECRET_CONNECT", "")

    secrets_to_try = []
    if platform_secret:
        secrets_to_try.append(("platform", platform_secret))
    if connect_secret:
        secrets_to_try.append(("connect", connect_secret))

    if not secrets_to_try:
        raise ValueError(
            "No Stripe webhook secret configured. "
            "Set STRIPE_WEBHOOK_SECRET (platform) and/or "
            "STRIPE_WEBHOOK_SECRET_CONNECT (commerce) in .env."
        )

    last_error = None
    for label, secret in secrets_to_try:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, secret,
            )
            logger.debug("webhook: signature verified with %s secret", label)
            return _normalize_stripe_event(event)
        except stripe.SignatureVerificationError as e:
            last_error = e
            continue

    raise ValueError(
        f"Invalid Stripe signature — verified against "
        f"{len(secrets_to_try)} secret(s): {last_error}"
    )


async def handle_webhook_event(event: Any) -> dict:
    """Route a verified Stripe event to the appropriate handler.

    Uses the reserve-before-run pattern (Fase 6c): the event row is
    atomically claimed via try_acquire_event_lock BEFORE any handler runs,
    so two concurrent webhook deliveries can never both execute side effects
    for the same event. Handler results are persisted via mark_event_processed.

    Returns a dict summary of what was processed:
      - status="processed"         : handler ran and finished successfully
      - status="duplicate"         : already fully handled (second call)
      - status="in_flight"         : another worker holds the lock (recent)
      - status="ignored"           : no handler registered for the event type
      - status="error"             : handler raised; record stays processed=False
                                     so a retry past the stale window can recover
    """
    event_type = event["type"]
    event_id = event["id"]

    # 1. Atomic reserve — fails fast for duplicates and concurrent retries.
    lock = await billing_repository.try_acquire_event_lock(event_id, event_type)
    if not lock.get("acquired"):
        status = lock.get("status", "contention")
        logger.info(
            "Skipping event '%s' (%s) — lock status=%s",
            event_id, event_type, status,
        )
        # Map to a return status the webhook endpoint can reason about.
        # "already_processed" → duplicate; "in_flight" / "contention" → keep distinct
        # so Stripe retry telemetry remains interpretable.
        return {
            "status": "duplicate" if status == "already_processed" else status,
            "event_id": event_id,
        }

    handler = _EVENT_HANDLERS.get(event_type)

    # 2. No handler registered — we've already reserved the row; mark it
    #    processed so future deliveries short-circuit.
    if handler is None:
        logger.debug("Unhandled event type '%s' -- ignoring", event_type)
        await billing_repository.mark_event_processed(
            event_id,
            payload_summary={"note": "no_handler_registered"},
        )
        return {"status": "ignored", "event_type": event_type, "event_id": event_id}

    # 3. Run the handler under our lock; finalize the row based on outcome.
    try:
        result = await handler(event)
    except Exception as e:
        logger.error("Error handling event '%s' (%s): %s", event_id, event_type, e)
        # Leave processed=False so a retry past the stale window can recover.
        await billing_repository.mark_event_processed(
            event_id,
            error=str(e),
        )
        return {"status": "error", "error": str(e), "event_id": event_id}

    # Handler returned normally → record success + summary metadata.
    result["status"] = "processed"
    await billing_repository.mark_event_processed(
        event_id,
        organization_id=result.get("org_id"),
        payload_summary={k: v for k, v in result.items() if k != "status"},
    )
    return result


# ==============================================================================
# Shared provisioning (v5.7)
# ==============================================================================

async def _provision_from_checkout_session(
    session_data: dict,
    *,
    verify_org_id: Optional[str] = None,
    _stripe_sub: Optional[Any] = None,
) -> dict:
    """Provision a commercial plan from a Stripe Checkout Session object.

    Shared by both the webhook handler (_handle_checkout_completed) and the
    verify-checkout recovery path (verify_checkout_session).

    Args:
        session_data: Stripe Checkout Session dict (from webhook event or API).
        verify_org_id: If set, assert that session metadata org_id matches.
                       Raises PermissionError on mismatch.
        _stripe_sub: Pre-fetched Stripe Subscription object.  When provided,
                     the function skips the Subscription.retrieve call.
                     Used by verify_checkout_session to avoid a duplicate
                     Stripe API call (v5.7.1).

    Returns:
        Dict with provisioning result (plan_slug, billing_status, etc.).

    Does NOT:
      - Cancel stale Stripe subscriptions (webhook-only concern).
      - Record billing events (caller's responsibility).
    """
    from services import plan_provisioning

    org_id = session_data.get("metadata", {}).get("org_id")
    plan_slug = session_data.get("metadata", {}).get("plan_slug")
    interval = session_data.get("metadata", {}).get("interval", "month")
    stripe_sub_id = session_data.get("subscription")

    if not org_id or not plan_slug:
        raise ValueError("Missing org_id or plan_slug in checkout session metadata")

    if verify_org_id and org_id != verify_org_id:
        raise PermissionError(
            f"Session does not belong to this organization "
            f"(session org_id={org_id}, caller org_id={verify_org_id})"
        )

    # Determine billing status from the subscription
    billing_status = "active"
    trial_ends_at = None
    current_period_end = None

    if stripe_sub_id:
        # v5.7.1: Reuse pre-fetched sub if provided, else retrieve from Stripe
        sub = _stripe_sub
        if sub is None:
            stripe = _get_stripe()
            raw_sub = await asyncio.to_thread(stripe.Subscription.retrieve, stripe_sub_id)
            sub = _normalize_stripe_object(raw_sub)  # v15 compat
        else:
            # Caller may pass either a dict or a raw StripeObject — normalize defensively.
            sub = _normalize_stripe_object(sub)
        billing_status = sub.get("status", "active")  # "trialing", "active", etc.
        if sub.get("trial_end"):
            trial_ends_at = datetime.fromtimestamp(sub["trial_end"], tz=timezone.utc)
        if sub.get("current_period_end"):
            current_period_end = datetime.fromtimestamp(
                sub["current_period_end"], tz=timezone.utc,
            )

    # v5.8 / Onda 9.T — Trial-once enforcement.
    # If the new subscription includes a trial period, MARK the org as having
    # used a trial. This flag is the source-of-truth for the gate that
    # prevents the cancel-and-retry-with-trial exploit. Idempotent + survives
    # cancellation (NEVER reset by deprovision).
    if trial_ends_at is not None:
        try:
            await billing_repository.mark_trial_used(
                organization_id=org_id,
                plan_slug=plan_slug,
                started_at=datetime.now(timezone.utc).isoformat(),
                stripe_subscription_id=stripe_sub_id,
                billing_interval=interval,
            )
            logger.info(
                "[trial-once] org=%s marked has_used_trial=True (plan=%s, sub=%s)",
                org_id, plan_slug, stripe_sub_id,
            )
        except Exception as e:
            # Best-effort: never block provisioning on the trial flag write.
            # The webhook can be re-tried; the flag is self-healing.
            logger.error(
                "[trial-once] mark_trial_used failed for org=%s: %s (provisioning continues)",
                org_id, e,
            )

    result = await plan_provisioning.provision_commercial_plan(
        org_id=org_id,
        plan_slug=plan_slug,
        assigned_by="stripe",
        stripe_subscription_id=stripe_sub_id,
        billing_status=billing_status,
        billing_interval=interval,
        trial_ends_at=trial_ends_at,
        current_period_end=current_period_end,
        notes=f"Checkout completed: {session_data.get('id')}",
    )

    # ── Onda 20 Layer 2: post-checkout orphan-sub cleanup ────────────────
    # If the same Stripe customer has any OTHER active/trialing sub
    # besides the one we just provisioned, cancel them. This catches:
    #   · Layer 1 race (DB stale at pre-flight, second checkout completed)
    #   · Manual operator-created subs from Stripe Dashboard
    #   · Any future bug that creates a duplicate
    # Best-effort: failures don't break the new sub's provisioning.
    customer_id = session_data.get("customer")
    if customer_id and stripe_sub_id:
        try:
            cancelled = await _cancel_orphan_subs_for_customer(
                customer_id=customer_id,
                keep_sub_id=stripe_sub_id,
                org_id=org_id,
                reason="post_checkout_completion_sweep",
            )
            if cancelled:
                logger.warning(
                    "[onda_20] post-checkout sweep cancelled %d orphan sub(s) "
                    "on customer=%s (kept new sub=%s for org=%s)",
                    cancelled, customer_id, stripe_sub_id, org_id,
                )
                # Best-effort audit entry (catalog audit log is generic
                # enough for billing events; we use a billing-events
                # collection if available, otherwise a regular log).
                try:
                    from database import billing_events_collection
                    import uuid as _uuid
                    await billing_events_collection.insert_one({
                        "id": _uuid.uuid4().hex,
                        "organization_id": org_id,
                        "event_type": "orphan_sub_cleanup",
                        "stripe_customer_id": customer_id,
                        "kept_sub_id": stripe_sub_id,
                        "cancelled_count": cancelled,
                        "trigger": "post_checkout_completion",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass  # billing_events not strictly required
        except Exception as e:
            logger.error(
                "[onda_20] post-checkout sweep failed for org=%s customer=%s: %s",
                org_id, customer_id, e, exc_info=True,
            )

    return result


# ==============================================================================
# Checkout verification / recovery (v5.7)
# ==============================================================================

async def verify_checkout_session(
    session_id: str,
    org_id: str,
) -> dict:
    """Verify a Stripe Checkout Session and provision the plan if needed.

    This is the pull-based recovery path for when webhooks are missing,
    delayed, or misconfigured.  It retrieves the Checkout Session directly
    from Stripe, validates ownership and status, checks for idempotency,
    and delegates to the canonical provisioning path.

    Args:
        session_id: Stripe Checkout Session ID (cs_xxx).
        org_id: Authenticated caller's organization ID (for ownership check).

    Returns:
        Dict with ``status`` key:
          - "provisioned": plan was activated via this call.
          - "already_provisioned": org already had the correct state (no-op).
          - "session_incomplete": checkout was not completed by the customer.
          - "subscription_not_active": Stripe subscription is in a terminal state.

    Raises:
        ValueError: Invalid session_id, missing metadata, bad session mode.
        PermissionError: Session does not belong to the caller's organization.
    """
    stripe = _get_stripe()

    # 1. Retrieve Checkout Session from Stripe
    try:
        raw_session = await asyncio.to_thread(
            stripe.checkout.Session.retrieve, session_id,
        )
    except stripe.InvalidRequestError as e:
        raise ValueError(f"Invalid or expired checkout session: {e}")

    # Normalize to plain dict — stripe-python v15 StripeObject lacks .get().
    # See _normalize_stripe_object for rationale. Protects every .get() below.
    session = _normalize_stripe_object(raw_session)

    # 2. Validate session mode
    if session.get("mode") != "subscription":
        raise ValueError(
            f"Checkout session mode is '{session.get('mode')}', expected 'subscription'"
        )

    # 3. Validate session completion
    if session.get("status") != "complete":
        return {
            "status": "session_incomplete",
            "session_status": session.get("status"),
        }

    # 4. Validate ownership via metadata
    session_org_id = session.get("metadata", {}).get("org_id")
    if session_org_id != org_id:
        raise PermissionError(
            f"Session does not belong to this organization "
            f"(session org_id={session_org_id}, caller org_id={org_id})"
        )

    # 5. Validate subscription exists
    stripe_sub_id = session.get("subscription")
    if not stripe_sub_id:
        raise ValueError("Checkout session has no subscription ID")

    plan_slug = session.get("metadata", {}).get("plan_slug")
    if not plan_slug:
        raise ValueError("Checkout session metadata missing plan_slug")

    interval = session.get("metadata", {}).get("interval", "month")

    # 6. Idempotency check: if org already has matching state, return no-op
    org_summary = await billing_repository.get_org_billing_summary(org_id)
    if org_summary:
        from repositories.billing_repository import ACTIVE_BILLING_STATES

        if (
            org_summary.get("stripe_subscription_id") == stripe_sub_id
            and org_summary.get("commercial_plan_slug") == plan_slug
            and org_summary.get("billing_status") in ACTIVE_BILLING_STATES
        ):
            logger.info(
                "[verify] Org '%s' already provisioned with plan='%s' sub='%s' status='%s' -- no-op",
                org_id, plan_slug, stripe_sub_id, org_summary.get("billing_status"),
            )
            return {
                "status": "already_provisioned",
                "commercial_plan_slug": plan_slug,
                "billing_status": org_summary.get("billing_status"),
                "billing_interval": org_summary.get("billing_interval"),
                "trial_ends_at": (
                    org_summary["trial_ends_at"].isoformat()
                    if org_summary.get("trial_ends_at")
                    else None
                ),
                "current_period_end": (
                    org_summary["current_period_end"].isoformat()
                    if org_summary.get("current_period_end")
                    else None
                ),
            }

    # 7. Retrieve Stripe Subscription to check its status
    try:
        raw_sub = await asyncio.to_thread(stripe.Subscription.retrieve, stripe_sub_id)
    except stripe.InvalidRequestError as e:
        raise ValueError(f"Failed to retrieve subscription: {e}")

    # Normalize to plain dict for .get() compatibility on stripe-python v15+.
    sub = _normalize_stripe_object(raw_sub)

    sub_status = sub.get("status", "unknown")
    if sub_status not in ("active", "trialing", "past_due"):
        return {
            "status": "subscription_not_active",
            "stripe_status": sub_status,
        }

    # 8. Provision via shared function (canonical path)
    #    Pass session as a dict matching the shape _provision_from_checkout_session expects.
    session_dict = {
        "id": session.get("id"),
        "metadata": {
            "org_id": org_id,
            "plan_slug": plan_slug,
            "interval": interval,
        },
        "subscription": stripe_sub_id,
    }

    # v5.7.1: Pass the already-fetched subscription to avoid a duplicate
    # Stripe API call inside the shared provisioning helper.
    result = await _provision_from_checkout_session(
        session_dict,
        verify_org_id=org_id,
        _stripe_sub=sub,
    )

    logger.info(
        "[verify] Provisioned org '%s' with plan='%s' status='%s' via checkout recovery",
        org_id, plan_slug, sub_status,
    )

    # Build response with billing state
    trial_ends_at = None
    current_period_end = None
    if sub.get("trial_end"):
        trial_ends_at = datetime.fromtimestamp(
            sub["trial_end"], tz=timezone.utc,
        ).isoformat()
    if sub.get("current_period_end"):
        current_period_end = datetime.fromtimestamp(
            sub["current_period_end"], tz=timezone.utc,
        ).isoformat()

    return {
        "status": "provisioned",
        "commercial_plan_slug": plan_slug,
        "billing_status": sub_status,
        "billing_interval": interval,
        "trial_ends_at": trial_ends_at,
        "current_period_end": current_period_end,
    }


# ==============================================================================
# Event handlers (private)
# ==============================================================================

async def _handle_checkout_completed(event: Any) -> dict:
    """Handle checkout.session.completed — route to billing or commerce handler.

    Commerce checkout sessions have metadata.checkout_type="commerce" and source="afianco".
    Billing/subscription sessions have metadata.plan_slug.
    """
    session = event["data"]["object"]
    checkout_type = session.get("metadata", {}).get("checkout_type")

    # Route commerce checkouts to the reconciliation service
    if checkout_type == "commerce":
        from services.payment_checkout_service import reconcile_checkout_event
        return await reconcile_checkout_event(event)

    # Otherwise: existing subscription billing flow
    org_id = session.get("metadata", {}).get("org_id")
    plan_slug = session.get("metadata", {}).get("plan_slug")
    interval = session.get("metadata", {}).get("interval", "month")

    logger.info(
        "[webhook] checkout.session.completed event_id=%s session_id=%s org_id=%s plan=%s interval=%s",
        event["id"], session.get("id"), org_id, plan_slug, interval,
    )

    if not org_id or not plan_slug:
        raise ValueError("Missing org_id or plan_slug in checkout session metadata")

    stripe_sub_id = session.get("subscription")
    stripe = _get_stripe()

    # ── v5.5: Cancel stale subscription if org already has a different one ─
    if stripe_sub_id:
        org_guard = await billing_repository.get_org_subscription_guard(org_id)
        old_sub_id = org_guard.get("stripe_subscription_id")
        if old_sub_id and old_sub_id != stripe_sub_id:
            logger.warning(
                "[webhook] checkout.session.completed: org '%s' already has sub '%s', "
                "new checkout created sub '%s' -- cancelling old sub to prevent duplicates",
                org_id, old_sub_id, stripe_sub_id,
            )
            try:
                await asyncio.to_thread(
                    stripe.Subscription.cancel, old_sub_id
                )
                logger.info(
                    "[webhook] Cancelled stale Stripe subscription '%s' for org '%s'",
                    old_sub_id, org_id,
                )
            except Exception as cancel_err:
                # Log but don't fail the checkout — the new sub should still be provisioned
                logger.error(
                    "[webhook] Failed to cancel stale sub '%s' for org '%s': %s",
                    old_sub_id, org_id, cancel_err,
                )

    # Delegate to shared provisioning function (v5.7 extraction)
    result = await _provision_from_checkout_session(session)
    result["org_id"] = org_id
    return result


async def _handle_subscription_updated(event: Any) -> dict:
    """Handle customer.subscription.updated -- plan change or cancel-at-period-end."""
    from services import plan_provisioning

    sub = event["data"]["object"]
    stripe_sub_id = sub["id"]
    org_id = sub.get("metadata", {}).get("org_id")

    logger.info(
        "[webhook] subscription.updated event_id=%s sub_id=%s org_id=%s status=%s cancel_at_period_end=%s",
        event["id"], stripe_sub_id, org_id, sub.get("status"), sub.get("cancel_at_period_end"),
    )

    if not org_id:
        # Try to resolve from Stripe customer
        customer_id = sub.get("customer")
        if customer_id:
            org = await billing_repository.get_org_by_stripe_customer(customer_id)
            org_id = org.get("id") if org else None

    if not org_id:
        raise ValueError(f"Cannot resolve org_id for subscription '{stripe_sub_id}'")

    # Guard: skip if plan was manually assigned by admin (not Stripe-managed)
    org_doc = await billing_repository.get_org_subscription_guard(org_id)
    if (org_doc.get("plan_assigned_by") or "").startswith("admin:"):
        logger.info(
            "[webhook] subscription.updated SKIPPED for org=%s — plan is admin-assigned (%s)",
            org_id, org_doc["plan_assigned_by"],
        )
        return {"org_id": org_id, "action": "skipped_admin_assigned"}

    cancel_at_period_end = sub.get("cancel_at_period_end", False)
    billing_status = sub.get("status", "active")

    current_period_end = None
    if sub.get("current_period_end"):
        current_period_end = datetime.fromtimestamp(
            sub["current_period_end"], tz=timezone.utc,
        )

    # v5.8 / Onda 9.T — Trial conversion detection (trialing → active).
    # When Stripe transitions a sub from trialing to active (after the trial
    # period expires and the first invoice is paid), close the open trial
    # history entry with outcome="converted" and compute conversion_lag_days.
    # This is best-effort: failures don't abort the webhook.
    if billing_status == "active":
        try:
            previous_status = (org_doc or {}).get("billing_status")
            # Only fire on actual transition (not on every active update)
            if previous_status == "trialing":
                # Snapshot usage during trial for analytics
                usage_snapshot = await _capture_trial_usage_snapshot(org_id)
                # Get trial start to compute lag
                trial_history = (await billing_repository.get_trial_history(org_id) or [])
                conv_lag = None
                for entry in reversed(trial_history):
                    if entry.get("stripe_subscription_id") == stripe_sub_id and not entry.get("outcome"):
                        try:
                            from datetime import datetime as _dt
                            s = _dt.fromisoformat(entry["started_at"].replace("Z", "+00:00"))
                            now_dt = datetime.now(timezone.utc)
                            conv_lag = max(0, (now_dt - s).days)
                        except (ValueError, TypeError, KeyError):
                            pass
                        break
                await billing_repository.close_trial_history_entry(
                    organization_id=org_id,
                    stripe_subscription_id=stripe_sub_id,
                    outcome="converted",
                    ended_at=datetime.now(timezone.utc).isoformat(),
                    usage_snapshot=usage_snapshot,
                    conversion_lag_days=conv_lag,
                )
                logger.info(
                    "[trial-once] org=%s trial converted (sub=%s, days=%s)",
                    org_id, stripe_sub_id, conv_lag,
                )
        except Exception as e:
            logger.error(
                "[trial-once] conversion close failed for org=%s: %s (continuing)",
                org_id, e,
            )

    # ── Resolve main plan via items iteration (v5.8 / Onda 2) ─────────────
    #
    # Pre-Onda 2: a sub had exactly 1 item, so items[0] always WAS the main
    # plan. Post-Onda 2: a sub can have 1 main + N add-on items, so we must
    # find the main one explicitly via metadata. Legacy subs (no metadata)
    # fall back to items[0] which is always correct for them.
    #
    # Add-on items are also collected here for logging. Their persistence
    # to a dedicated AddonSubscription model lands in Onda 3 — for now we
    # just log so the webhook flow stays robust against the new shape.
    new_plan_slug = None
    addons_seen: List[Dict[str, Any]] = []
    items = sub.get("items", {}).get("data", [])
    if items:
        main_item = next((it for it in items if _is_main_plan_item(it)), items[0])
        main_price_id = (main_item or {}).get("price", {}).get("id")
        if main_price_id:
            commercial_plan = await billing_repository.get_commercial_plan_by_stripe_price(main_price_id)
            if commercial_plan:
                new_plan_slug = commercial_plan["slug"]

        # Collect add-on items for logging (Onda 2). Onda 3 wires the
        # AddonSubscription persistence here.
        for it in items:
            md = (it or {}).get("metadata") or {}
            if md.get("is_addon") == "true":
                addons_seen.append({
                    "slug": md.get("addon_slug"),
                    "stripe_subscription_item_id": it.get("id"),
                    "stripe_price_id": (it.get("price") or {}).get("id"),
                    "quantity": it.get("quantity", 1),
                })

    # ── v5.8 / Onda 3: persist add-on subscriptions ──────────────────────
    #
    # Sync the AddonSubscription rows to match exactly what Stripe reports
    # in this event. `reconcile_addons_with_stripe_items`:
    #   · upserts every addon item present in the event (idempotent)
    #   · cancels every active DB row NOT present in the event (drift fix)
    #
    # This makes the webhook fully self-healing: even if a previous webhook
    # was missed or the DB drifted, this single call restores correctness.
    addon_sync_counters = {"upserted": 0, "cancelled": 0}
    if addons_seen or stripe_sub_id:
        try:
            addon_sync_counters = await billing_repository.reconcile_addons_with_stripe_items(
                organization_id=org_id,
                stripe_subscription_id=stripe_sub_id,
                addon_items_from_stripe=addons_seen,
            )
            logger.info(
                "[webhook] subscription.updated org=%s sub=%s addon sync: upserted=%d cancelled=%d",
                org_id, stripe_sub_id,
                addon_sync_counters["upserted"], addon_sync_counters["cancelled"],
            )
        except Exception as exc:  # noqa: BLE001 — defensive: addon sync is best-effort
            # Addon sync failure must NOT abort the webhook — main plan
            # provisioning is the higher-priority concern. Log loudly so
            # ops can re-run reconcile manually if needed.
            logger.error(
                "[webhook] subscription.updated org=%s addon sync FAILED: %s "
                "(main plan provisioning continues). Manual reconcile may be needed.",
                org_id, exc, exc_info=True,
            )

    result = await plan_provisioning.handle_subscription_updated(
        org_id=org_id,
        stripe_subscription_id=stripe_sub_id,
        cancel_at_period_end=cancel_at_period_end,
        current_period_end=current_period_end,
        billing_status=billing_status,
        new_plan_slug=new_plan_slug,
    )

    result["org_id"] = org_id
    result["addons_seen"] = len(addons_seen)
    result["addons_upserted"] = addon_sync_counters.get("upserted", 0)
    result["addons_cancelled"] = addon_sync_counters.get("cancelled", 0)
    return result


async def _capture_trial_usage_snapshot(org_id: str) -> dict:
    """v5.8 / Onda 9.T — Capture a usage snapshot for trial_history analytics.

    Counts current-period usage for the metrics most likely to differentiate
    converted vs cancelled trials. Used for analytics ("did the user actually
    explore the product or just sign up?").

    Best-effort: returns {} on any error rather than blocking the trial close.
    """
    snapshot: Dict[str, int] = {}
    try:
        from services.module_access import get_current_period_range
        from repositories import usage_repository
        from database import products_collection, stores_collection
        period_start, period_end = get_current_period_range()
        # Monthly-metered metrics
        for module_key, feature_key in [
            ("ai_assistant", "chat"),
            ("ai_assistant", "digest"),
            ("cashflow_monitor", "data_rows"),
            ("commerce", "orders_monthly"),
        ]:
            try:
                used = await usage_repository.count_usage(
                    org_id, module_key, feature_key, period_start, period_end,
                )
                snapshot[f"{module_key}.{feature_key}"] = used
            except Exception:
                pass
        # Snapshot-style metrics (count documents)
        try:
            snapshot["product_catalog.products"] = await products_collection.count_documents(
                {"organization_id": org_id}
            )
        except Exception:
            pass
        try:
            snapshot["commerce.stores_active"] = await stores_collection.count_documents(
                {"organization_id": org_id, "is_active": True}
            )
        except Exception:
            pass
    except Exception:
        pass
    return snapshot


async def _handle_subscription_deleted(event: Any) -> dict:
    """Handle customer.subscription.deleted -- cancel and revert to free."""
    from services import plan_provisioning

    sub = event["data"]["object"]
    stripe_sub_id = sub["id"]
    org_id = sub.get("metadata", {}).get("org_id")

    logger.info(
        "[webhook] subscription.deleted event_id=%s sub_id=%s org_id=%s",
        event["id"], stripe_sub_id, org_id,
    )

    if not org_id:
        customer_id = sub.get("customer")
        if customer_id:
            org = await billing_repository.get_org_by_stripe_customer(customer_id)
            org_id = org.get("id") if org else None

    if not org_id:
        raise ValueError(f"Cannot resolve org_id for deleted subscription '{stripe_sub_id}'")

    # Guard: skip if plan was manually assigned by admin
    org_doc = await billing_repository.get_org_subscription_guard(org_id)
    if (org_doc.get("plan_assigned_by") or "").startswith("admin:"):
        logger.info(
            "[webhook] subscription.deleted SKIPPED for org=%s — plan is admin-assigned (%s)",
            org_id, org_doc["plan_assigned_by"],
        )
        return {"org_id": org_id, "action": "skipped_admin_assigned"}

    # v5.8 / Onda 9.T — Close any open trial_history entry for this sub.
    # Determine outcome:
    #   - sub.status was "trialing" + cancel_at_period_end was true → "expired_to_free"
    #   - sub.status was "trialing" + immediate cancel → "cancelled_during_trial"
    #   - sub.status was "active" → not a trial event (skip)
    # Best-effort: never abort the deletion handler.
    sub_status_before_delete = sub.get("status")  # at deletion time
    was_trialing = (org_doc or {}).get("billing_status") == "trialing"
    if was_trialing or sub_status_before_delete == "trialing":
        try:
            # Distinguish expired-vs-cancelled by the sub's `ended_at` and
            # `canceled_at` timestamps if available; otherwise default to
            # "expired_to_free" (most common — trial ran out via cancel_at_period_end).
            outcome = "expired_to_free"
            cancellation_reason = None
            if sub.get("canceled_at") and not sub.get("trial_end"):
                outcome = "cancelled_during_trial"
            cancellation_metadata = (sub.get("metadata") or {}).get("cancellation_reason")
            if cancellation_metadata:
                cancellation_reason = cancellation_metadata
            usage_snapshot = await _capture_trial_usage_snapshot(org_id)
            await billing_repository.close_trial_history_entry(
                organization_id=org_id,
                stripe_subscription_id=stripe_sub_id,
                outcome=outcome,
                ended_at=datetime.now(timezone.utc).isoformat(),
                cancellation_reason=cancellation_reason,
                usage_snapshot=usage_snapshot,
            )
            logger.info(
                "[trial-once] org=%s trial closed (sub=%s, outcome=%s)",
                org_id, stripe_sub_id, outcome,
            )
        except Exception as e:
            logger.error(
                "[trial-once] close trial entry failed for org=%s: %s (continuing)",
                org_id, e,
            )

    cancelled = await plan_provisioning.deprovision_stripe_subscription(
        org_id, stripe_sub_id,
    )

    # ── v5.8 / Onda 3: cancel any active addons attached to this sub ─────
    # When the parent Stripe subscription is deleted, the items inside it
    # are gone too. Mark every active AddonSubscription row linked to this
    # sub as cancelled so the org's effective limits revert to base-only.
    cancelled_addons = 0
    try:
        cancelled_addons = await billing_repository.cancel_all_addons_by_stripe_sub(
            stripe_sub_id,
        )
        if cancelled_addons:
            logger.info(
                "[webhook] subscription.deleted org=%s sub=%s also cancelled %d add-on subs",
                org_id, stripe_sub_id, cancelled_addons,
            )
    except Exception as exc:  # noqa: BLE001 — addon cleanup is best-effort
        logger.error(
            "[webhook] subscription.deleted org=%s addon cancel FAILED: %s "
            "(main deprovision succeeded). Manual reconcile may be needed.",
            org_id, exc, exc_info=True,
        )

    return {
        "org_id": org_id,
        "cancelled_subs": cancelled,
        "cancelled_addons": cancelled_addons,
    }


async def _handle_invoice_paid(event: Any) -> dict:
    """Handle invoice.paid -- update billing status to active."""
    invoice = event["data"]["object"]
    stripe_sub_id = invoice.get("subscription")
    customer_id = invoice.get("customer")

    if not stripe_sub_id or not customer_id:
        logger.info("[webhook] invoice.paid event_id=%s skipped (no subscription)", event["id"])
        return {"note": "Invoice not tied to a subscription -- skipped"}

    org = await billing_repository.get_org_by_stripe_customer(customer_id)
    if not org:
        logger.warning(
            "[webhook] invoice.paid event_id=%s customer=%s -- no org found (mapping broken?)",
            event["id"], customer_id,
        )
        return {"note": f"No org found for customer '{customer_id}' -- skipped"}

    org_id = org["id"]

    # Guard: skip if plan was manually assigned by admin
    if (org.get("plan_assigned_by") or "").startswith("admin:"):
        logger.info(
            "[webhook] invoice.paid SKIPPED for org=%s — plan is admin-assigned (%s)",
            org_id, org["plan_assigned_by"],
        )
        return {"org_id": org_id, "action": "skipped_admin_assigned"}

    await billing_repository.update_org_billing_fields(org_id, {
        "billing_status": "active",
        "plan_assigned_by": "stripe",
    })

    logger.info(
        "[webhook] invoice.paid event_id=%s org_id=%s -- billing_status set to active",
        event["id"], org_id,
    )
    return {"org_id": org_id, "action": "billing_status_set_active"}


async def _handle_invoice_payment_failed(event: Any) -> dict:
    """Handle invoice.payment_failed -- update billing status to past_due."""
    invoice = event["data"]["object"]
    customer_id = invoice.get("customer")

    if not customer_id:
        logger.info("[webhook] invoice.payment_failed event_id=%s skipped (no customer)", event["id"])
        return {"note": "Invoice has no customer -- skipped"}

    org = await billing_repository.get_org_by_stripe_customer(customer_id)
    if not org:
        logger.warning(
            "[webhook] invoice.payment_failed event_id=%s customer=%s -- no org found",
            event["id"], customer_id,
        )
        return {"note": f"No org found for customer '{customer_id}' -- skipped"}

    org_id = org["id"]

    # Guard: skip if plan was manually assigned by admin
    if (org.get("plan_assigned_by") or "").startswith("admin:"):
        logger.info(
            "[webhook] invoice.payment_failed SKIPPED for org=%s — plan is admin-assigned (%s)",
            org_id, org["plan_assigned_by"],
        )
        return {"org_id": org_id, "action": "skipped_admin_assigned"}

    await billing_repository.update_org_billing_fields(org_id, {
        "billing_status": "past_due",
        "plan_assigned_by": "stripe",
    })

    logger.warning(
        "[webhook] invoice.payment_failed event_id=%s org_id=%s -- billing_status set to past_due",
        event["id"], org_id,
    )
    return {"org_id": org_id, "action": "billing_status_set_past_due"}


async def _handle_account_updated(event: Any) -> dict:
    """Dispatcher shim for Stripe Connect `account.updated` events.

    Lazy import keeps this module free of any coupling to the Connect Express
    implementation. The handler is defensive by contract: it never raises and
    returns {status: "processed" | "ignored"}, which guarantees the webhook
    endpoint returns 200 for all account.updated events (Option A — billing-
    safety gate: Stripe will not retry benign events we don't care about).
    """
    try:
        from services.stripe_connect_express import handle_account_updated
        return await handle_account_updated(event)
    except Exception as exc:
        # Explicitly swallow — billing flow must not regress on Connect errors.
        logger.warning("[webhook] account.updated dispatcher error (ignored): %s", exc)
        return {"status": "ignored", "reason": "dispatcher_error", "error": str(exc)}


async def _handle_charge_refunded(event: Any) -> dict:
    """Dispatcher shim for `charge.refunded` (commerce) events.

    Lazy-imports the commerce handler so this module stays decoupled from
    the commerce implementation. Defensive: never raises; returns
    {status: "ignored"} on any failure path so the webhook returns 200 and
    Stripe does not retry benign mismatches.
    """
    try:
        from services.payment_checkout_service import handle_charge_refunded
        return await handle_charge_refunded(event)
    except Exception as exc:
        logger.warning("[webhook] charge.refunded dispatcher error (ignored): %s", exc)
        return {"status": "ignored", "reason": "dispatcher_error", "error": str(exc)}


async def _handle_charge_dispute_created(event: Any) -> dict:
    """Dispatcher shim for `charge.dispute.created` (commerce) events."""
    try:
        from services.payment_checkout_service import handle_charge_dispute_created
        return await handle_charge_dispute_created(event)
    except Exception as exc:
        logger.warning("[webhook] charge.dispute.created dispatcher error (ignored): %s", exc)
        return {"status": "ignored", "reason": "dispatcher_error", "error": str(exc)}


# Event handler dispatch map
_EVENT_HANDLERS = {
    "checkout.session.completed": _handle_checkout_completed,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.paid": _handle_invoice_paid,
    "invoice.payment_failed": _handle_invoice_payment_failed,
    # Connect Express capability sync — isolated handler, cannot affect billing.
    "account.updated": _handle_account_updated,
    # Commerce post-charge events (Fase 7c) — isolated handlers, billing-safe.
    "charge.refunded": _handle_charge_refunded,
    "charge.dispute.created": _handle_charge_dispute_created,
}
