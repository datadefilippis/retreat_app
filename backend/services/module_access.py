"""Module Access Service — generic entitlements, access checks, and status for any module.

This service is module-agnostic: it works with any module_key by reading
pricing plans and subscriptions from the DB.  It replaces the old hardcoded
PLAN_LIMITS dict that was specific to the AI module.

Entitlement resolution order:
  0. Org-level billing gate (v6.0): checks billing_status for expired trials
     and stale past_due states.  Prevents orgs from keeping full paid access
     when Stripe webhooks are missed or delayed.
  1. Active subscription in module_subscriptions → linked pricing_plan → limits
  2. Fallback: Organization.plan field → pricing_plan lookup by slug
     "{module_key}_{org_plan}" (backward compat during migration)
  3. Default: module disabled, all limits = 0

Feature keys (stored in pricing_plan.limits) are module-specific:
  - ai_assistant: "chat", "insights"
  - Future modules will define their own feature keys.
  - A limit of -1 means unlimited.
  - A limit of 0 means the feature is not available.

H3: Soft restriction mode
  When a module subscription is recently cancelled (within GRACE_PERIOD_DAYS),
  check_module_access raises a 403 with code READ_ONLY_GRACE instead of
  MODULE_NOT_AVAILABLE. This gives users time to export data or adjust
  after a plan downgrade. The build_module_access_status also exposes a
  "read_only" flag for frontend components.

v6.0: Billing status enforcement
  billing_status on the Organization document is now *enforced*, not cosmetic.
  The billing gate (Step 0) catches two specific gaps:
    - BILLING_TRIAL_EXPIRED: trial ended > 2h ago but webhook didn't update subs
    - BILLING_PAST_DUE: payment failed AND current billing period has ended
  Statuses "active", "none", "manual" always pass through.
  The background billing sweep (billing_lifecycle.py) syncs with Stripe to
  resolve stale states; the gate provides real-time protection in between sweeps.
"""

import calendar
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, status

from repositories import subscription_repository, usage_repository

logger = logging.getLogger(__name__)

# H3: Grace period for soft restriction after downgrade (days)
GRACE_PERIOD_DAYS = 7

# v6.0: Billing gate constants
# Hours after trial_ends_at before the gate triggers (gives Stripe webhook time)
TRIAL_EXPIRED_GRACE_HOURS = 2
# Billing statuses that always pass the gate (no restriction)
_BILLING_PASSTHROUGH_STATUSES = frozenset({"active", "none", "manual"})


# ── Datetime helper ──────────────────────────────────────────────────────────

def _parse_iso_datetime(value) -> Optional[datetime]:
    """Parse an ISO datetime string or passthrough a datetime, returning None on failure."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


# ── v6.0: Org-level billing gate ────────────────────────────────────────────

def _check_billing_gate(org_doc: Optional[dict]) -> Optional[dict]:
    """Check org-level billing status for access restrictions.

    Returns:
        None — no restriction, access is allowed.
        dict — restriction detail (suitable as HTTPException.detail).

    This is a **pure function**: inspects org_doc fields only, no DB queries.

    Enforcement semantics:
      billing_status  | Condition                              | Result
      ─────────────── | ────────────────────────────────────── | ──────
      "active"        | —                                      | PASS
      "trialing"      | trial_ends_at in future (+ grace)      | PASS
      "trialing"      | trial_ends_at in past (beyond grace)   | READ_ONLY
      "past_due"      | current_period_end in future           | PASS
      "past_due"      | current_period_end in past or missing  | READ_ONLY
      "canceled"      | —                                      | PASS *
      "manual"        | —                                      | PASS
      "none"          | —                                      | PASS

    * canceled: deprovision webhook already cancelled paid subs and provisioned
      free-tier. The normal entitlement chain (step 1–4) handles it. If the
      webhook was missed, the background sweep will clean it up.
    """
    if not org_doc:
        return None  # No org doc available → can't check, pass through

    billing_status = org_doc.get("billing_status", "none")

    # Fast path: statuses that never trigger the gate
    if billing_status in _BILLING_PASSTHROUGH_STATUSES:
        return None

    # ── Trialing: check if trial has expired ───────────────────────────
    if billing_status == "trialing":
        trial_ends_at = _parse_iso_datetime(org_doc.get("trial_ends_at"))
        if trial_ends_at is None:
            return None  # No trial end date → can't determine, pass through

        cutoff = datetime.now(timezone.utc) - timedelta(hours=TRIAL_EXPIRED_GRACE_HOURS)
        if trial_ends_at > cutoff:
            return None  # Trial still valid (or within grace window)

        # Trial expired beyond the grace window
        logger.info(
            "billing_gate: trial expired for org=%s (trial_ends_at=%s)",
            org_doc.get("id", "?"), trial_ends_at.isoformat(),
        )
        return {
            "code": "BILLING_TRIAL_EXPIRED",
            "message": (
                "Il periodo di prova è terminato. "
                "Completa il pagamento per continuare ad usare le funzionalità premium."
            ),
            "read_only": True,
            "billing_status": "trialing",
        }

    # ── Past due: check if current billing period has ended ────────────
    if billing_status == "past_due":
        current_period_end = _parse_iso_datetime(org_doc.get("current_period_end"))
        if current_period_end is not None and current_period_end > datetime.now(timezone.utc):
            return None  # Still within the paid period — Stripe is dunning

        # Period ended (or unknown) AND payment failed
        logger.info(
            "billing_gate: past_due + period ended for org=%s (current_period_end=%s)",
            org_doc.get("id", "?"),
            current_period_end.isoformat() if current_period_end else "missing",
        )
        return {
            "code": "BILLING_PAST_DUE",
            "message": (
                "Pagamento non riuscito e periodo di fatturazione scaduto. "
                "Aggiorna il metodo di pagamento per ripristinare l'accesso completo."
            ),
            "read_only": True,
            "billing_status": "past_due",
        }

    # All other statuses (including "canceled") → pass through
    return None


# ── Period helpers (generic, not module-specific) ────────────────────────────

def get_current_period_range(now: Optional[date] = None) -> Tuple[str, str]:
    """Return (start, end) ISO date strings for the current calendar month."""
    today = now or date.today()
    first_day = today.replace(day=1)
    last_day_num = calendar.monthrange(today.year, today.month)[1]
    last_day = today.replace(day=last_day_num)
    return first_day.isoformat(), last_day.isoformat()


# ── Authoritative counters (defense-in-depth, source-agnostic) ──────────────


async def _count_data_rows_authoritative(
    org_id: str,
    period_start: str,
    period_end: str,
) -> int:
    """Return the maximum row count for `cashflow_monitor.data_rows` across
    every available source. The number returned is the one the gate
    compares against `effective_limit`.

    v5.8 / Onda 9.Y.0.3 — Why this exists:

    The "official" usage tracker is `ai_usage_events` (via
    `record_module_usage`). It is monotonic and perfectly accurate IF
    every cashflow insert path correctly invoked it. Reality: pre-9.Y.0
    inserts (manual /sales, /expenses, ...) rarely did. CSV imports via
    dataset_service did, and order confirms did. Mixed coverage means
    the events log is INCOMPLETE for legacy data.

    Symptom in the wild (2026-04-30): a Free org with ~250 rows imported
    in legacy format saw the Settings dashboard report exceeded (because
    it counted from `datasets.row_count`), while the gate read only ~5
    events from `ai_usage_events` and happily accepted new inserts.

    Fix: count usage from the SOURCE OF TRUTH — the actual row counts in
    each cashflow collection, scoped to the current billing period —
    AND from `ai_usage_events`. Return the MAX. Net effect:

      · No legacy bypass: an org with 250 sales rows already on disk is
        treated as 250 against the 200 quota, regardless of whether
        the corresponding usage events were ever written.
      · No double-counting on new inserts: a new row creates +1 in the
        collection AND +1 in ai_usage_events; both sources see the same
        increment, so MAX still tracks reality.
      · Defense-in-depth: any future insert path that forgets to call
        record_module_usage cannot bypass — the row count itself
        already counts.

    Performance: 5 indexed count_documents on `(organization_id, created_at)`
    plus the existing aggregation on ai_usage_events. ~6 round trips
    per gate check on a hot path. Acceptable for now; can be cached
    per-request if profiling shows it as a bottleneck.

    Period filter: `created_at >= period_start` (ISO date string). All
    five cashflow collections store `created_at` as ISO string with TZ,
    so lexicographic comparison is correct against `YYYY-MM-DD`.
    """
    from database import (
        sales_records_collection,
        expense_records_collection,
        purchase_records_collection,
        fixed_costs_collection,
    )

    # ai_usage_events count (the legacy tracker — still authoritative
    # going forward when all inserts are instrumented)
    try:
        events_count = await usage_repository.count_usage(
            org_id, "cashflow_monitor", "data_rows", period_start, period_end,
        )
    except Exception:
        events_count = 0

    # Live counts from the 5 cashflow collections, current period only.
    # Wrapped: a Mongo blip on one collection should not let the gate
    # silently approve — fall back to events_count which is at worst an
    # underestimate, but combined with a partial real count we still
    # take the max of what we got.
    real_total = 0
    period_filter = {"$gte": period_start}
    for coll in (
        sales_records_collection,
        expense_records_collection,
        purchase_records_collection,
        fixed_costs_collection,
    ):
        try:
            real_total += await coll.count_documents({
                "organization_id": org_id,
                "created_at": period_filter,
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "data_rows authoritative count: failed on %s for org=%s: %s",
                getattr(coll, "name", "?"), org_id, exc,
            )

    return max(events_count, real_total)


# ── Entitlement resolution ──────────────────────────────────────────────────

async def get_module_subscription(
    org_id: str,
    module_key: str,
) -> Optional[dict]:
    """Get the active subscription for an org + module, if any."""
    return await subscription_repository.get_active_subscription(org_id, module_key)


async def get_module_entitlements(
    org_id: str,
    module_key: str,
    org_doc: Optional[dict] = None,
) -> dict:
    """Resolve entitlements for an org + module.

    Returns:
        {
            "enabled": bool,
            "read_only": bool,  # H3: True during grace period after downgrade
            "limits": {"feature_key": int, ...},
            "plan_name": str,
            "plan_slug": str,
        }

    Resolution:
      1. Active subscription → pricing plan → limits
      2. H3: Recently-cancelled subscription within grace period → read_only
      3. Fallback: org_doc.plan → slug lookup "{module_key}_{plan}"
      4. Default: disabled, empty limits
    """
    default = {
        "enabled": False,
        "read_only": False,
        "limits": {},
        "plan_name": "free",
        "plan_slug": f"{module_key}_free",
    }

    # ── 1. Check for active subscription ─────────────────────────────────
    sub = await subscription_repository.get_active_subscription(org_id, module_key)
    if sub:
        plan = await subscription_repository.get_pricing_plan(sub["pricing_plan_id"])
        if plan:
            limits = plan.get("limits", {})
            enabled = _has_any_positive_limit(limits)
            return {
                "enabled": enabled,
                "read_only": False,
                "limits": limits,
                "plan_name": plan.get("name", "Unknown"),
                "plan_slug": plan.get("slug", ""),
            }

    # ── 2. H3: Check for recently-cancelled subscription (grace period) ──
    grace_cutoff = (
        datetime.now(timezone.utc) - timedelta(days=GRACE_PERIOD_DAYS)
    ).isoformat()
    grace_sub = await subscription_repository.get_recently_cancelled_subscription(
        org_id, module_key, grace_cutoff,
    )
    if grace_sub:
        plan = await subscription_repository.get_pricing_plan(grace_sub["pricing_plan_id"])
        if plan:
            limits = plan.get("limits", {})
            if _has_any_positive_limit(limits):
                return {
                    "enabled": True,
                    "read_only": True,
                    "limits": limits,
                    "plan_name": plan.get("name", "Unknown"),
                    "plan_slug": plan.get("slug", ""),
                }

    # ── 3. Fallback: Organization.plan → slug lookup ─────────────────────
    org_plan = (org_doc.get("plan") if org_doc else None) or "free"
    slug = f"{module_key}_{org_plan}"
    plan = await subscription_repository.get_pricing_plan_by_slug(
        module_key, slug,
    )
    if plan:
        limits = plan.get("limits", {})
        enabled = _has_any_positive_limit(limits)
        return {
            "enabled": enabled,
            "read_only": False,
            "limits": limits,
            "plan_name": plan.get("name", "Unknown"),
            "plan_slug": plan.get("slug", ""),
        }

    # ── 4. Default: module not available ─────────────────────────────────
    return default


def _has_any_positive_limit(limits: dict) -> bool:
    """True if any feature limit is > 0 or == -1 (unlimited)."""
    return any(v > 0 or v == -1 for v in limits.values())


# ── v5.8 / Onda 3: Add-on contribution to effective limits ────────────────────


async def _get_addon_contribution(
    org_id: str,
    module_key: str,
    feature_key: str,
) -> int:
    """Sum the contribution of every active AddonSubscription for (module, feature).

    Returns:
        -1 if any active add-on makes the feature unlimited (`addon_provides[m][f]=-1`)
         0 if no add-on provides this feature (org has no add-on, or none target it)
        >0 sum of (addon.quantity × addon_provides[module][feature]) across active rows

    Used by `get_effective_limit` and `check_module_access` to compute the
    final entitlement: base_plan_limit + addon_contribution. Safe to call
    on every gating check — the underlying `list_active_addons_for_org`
    query is a single Mongo find scoped by org_id (cheap; small N rows).

    For backward compatibility with orgs that have NO add-ons (the vast
    majority pre-rollout), this function returns 0 — and any caller that
    sums returns the unchanged base limit. Zero behavioural difference.
    """
    from repositories import billing_repository

    try:
        addons = await billing_repository.list_active_addons_for_org(org_id)
    except Exception:
        # Defensive: a Mongo blip during a quota check should never block
        # the user. Treat as "no add-ons", fall back to base limit only.
        return 0
    if not addons:
        return 0

    total_extra = 0
    for addon_sub in addons:
        plan = await billing_repository.get_commercial_plan(addon_sub.get("addon_slug", ""))
        if not plan:
            continue
        provides = (plan.get("addon_provides") or {}).get(module_key) or {}
        per_unit = provides.get(feature_key, 0)
        if per_unit == -1:
            return -1  # any unlimited add-on wins
        if per_unit > 0:
            qty = int(addon_sub.get("quantity", 1) or 1)
            total_extra += per_unit * qty
    return total_extra


async def get_effective_limit(
    org_id: str,
    module_key: str,
    feature_key: str,
    *,
    org_doc: Optional[dict] = None,
) -> int:
    """Compute the effective limit for (org, module, feature).

    effective_limit = base_plan_limit + Σ(addon contributions)

    Special values:
      -1 = unlimited (either base or any add-on is unlimited)
       0 = feature disabled (base=0 AND no add-on provides it)
      >0 = numeric quota

    Used by:
      · `check_module_access` to decide whether usage + pending exceeds quota
      · UI `usage-summary` endpoint to render the user's progress bar
      · System admin usage dashboard
    """
    entitlements = await get_module_entitlements(org_id, module_key, org_doc=org_doc)
    base = entitlements.get("limits", {}).get(feature_key, 0)
    if base == -1:
        return -1
    addon_extra = await _get_addon_contribution(org_id, module_key, feature_key)
    if addon_extra == -1:
        return -1
    return base + addon_extra


# ── Access checks ───────────────────────────────────────────────────────────

async def check_module_access(
    org_id: str,
    module_key: str,
    feature_key: str,
    org_doc: Optional[dict] = None,
    pending_quantity: int = 1,
) -> None:
    """Raise HTTPException if the org cannot use the given feature of a module.

    Checks:
      0. v6.0: Org-level billing gate (expired trial / stale past_due)
      1. Module enabled (entitlements.enabled) → 403 if not
      2. Feature limit exists and is not 0 → 403 if missing/zero
      3. Usage + pending_quantity within monthly quota → 429 if exceeded
      4. Limit == -1 → unlimited, always passes

    Args:
        org_id: Organization ID.
        module_key: Module identifier (e.g. "ai_assistant").
        feature_key: Feature within the module (e.g. "chat", "insights").
            Feature keys are module-specific, not global concepts.
        org_doc: Optional org document for fallback entitlement resolution.
        pending_quantity: Number of units about to be consumed (default 1).
            Used for pre-checking bulk operations (e.g. 50 data rows).
    """
    # v6.0: Step 0 — load org_doc if not provided (needed for billing gate)
    if org_doc is None:
        from repositories import organization_repository
        org_doc = await organization_repository.find_by_id(org_id)

    # v6.0: Step 0 — Org-level billing gate
    billing_restriction = _check_billing_gate(org_doc)
    if billing_restriction:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=billing_restriction,
        )

    entitlements = await get_module_entitlements(org_id, module_key, org_doc=org_doc)

    if not entitlements["enabled"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "MODULE_NOT_AVAILABLE",
                "message": (
                    "Funzionalità non disponibile nel piano attuale. "
                    "Aggiorna il piano per accedere."
                ),
            },
        )

    # H3: Soft restriction — read-only access during grace period after downgrade
    if entitlements.get("read_only"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "READ_ONLY_GRACE",
                "message": (
                    "Piano declassato. Accesso in sola lettura per "
                    f"{GRACE_PERIOD_DAYS} giorni. "
                    "Aggiorna il piano per ripristinare l'accesso completo."
                ),
                "read_only": True,
                "grace_period_days": GRACE_PERIOD_DAYS,
            },
        )

    base_limit = entitlements["limits"].get(feature_key, 0)

    # v5.8 / Onda 3: factor in active add-on contributions.
    # For orgs without any active add-on, _get_addon_contribution returns 0
    # and the resulting effective_limit == base_limit (zero behavioural diff).
    addon_extra = await _get_addon_contribution(org_id, module_key, feature_key)
    if addon_extra == -1 or base_limit == -1:
        return  # unlimited
    effective_limit = base_limit + addon_extra

    if effective_limit == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FEATURE_NOT_AVAILABLE",
                "message": f"Feature '{feature_key}' non disponibile nel piano attuale.",
            },
        )

    # Count usage for the current billing period (scoped by module_key)
    period_start, period_end = get_current_period_range()

    # v5.8 / Onda 9.Y.0.3 — Authoritative source for cashflow_monitor.data_rows.
    # Pre-9.Y.0 inserts didn't always call record_module_usage, so the
    # ai_usage_events collection is incomplete for orgs with legacy data.
    # The user-reported symptom: dashboard shows 250/200 (counted from
    # actual rows) but the gate reads only 5 events and lets new inserts
    # through. Defense-in-depth: take the MAX of both sources, so legacy
    # data still counts toward the quota even if its event was never
    # recorded.
    if module_key == "cashflow_monitor" and feature_key == "data_rows":
        usage = await _count_data_rows_authoritative(
            org_id, period_start, period_end,
        )
    else:
        usage = await usage_repository.count_usage(
            org_id, module_key, feature_key, period_start, period_end,
        )

    if usage + pending_quantity > effective_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": (
                    f"Quota mensile {feature_key} esaurita ({usage}/{effective_limit}). "
                    "Aggiorna il piano per continuare."
                ),
            },
        )


# ── Access status payload ───────────────────────────────────────────────────

async def build_module_access_status(
    org_id: str,
    module_key: str,
    org_doc: Optional[dict] = None,
) -> dict:
    """Build the full access-status payload for a module.

    Response shape (generic, module-neutral):
        {
            "plan": "<plan_name_without_prefix>",
            "enabled": bool,
            "read_only": bool,
            "period": {"start": "...", "end": "..."},
            "limits": {"feature_key": int, ...},
            "usage": {"feature_key": int, ...},
            "billing_restriction": str | None,  # v6.0: "BILLING_TRIAL_EXPIRED" etc.
        }

    Callers needing AI-specific response shape (ai_enabled instead of enabled)
    should remap the key at the router level.
    """
    # v6.0: Load org_doc if not provided (needed for billing gate)
    if org_doc is None:
        from repositories import organization_repository
        org_doc = await organization_repository.find_by_id(org_id)

    # v6.0: Check billing gate (non-raising — just include in status payload)
    billing_restriction = _check_billing_gate(org_doc)

    entitlements = await get_module_entitlements(org_id, module_key, org_doc=org_doc)
    period_start, period_end = get_current_period_range()

    # Build usage dict for all feature keys defined in limits (scoped by module_key)
    usage = {}
    for feature_key in entitlements["limits"]:
        usage[feature_key] = await usage_repository.count_usage(
            org_id, module_key, feature_key, period_start, period_end,
        )

    # Derive a short plan name by stripping the module_key prefix
    # "ai_assistant_starter" → "starter", "cashflow_monitor_pro" → "pro"
    plan_slug = entitlements["plan_slug"]
    prefix = f"{module_key}_"
    short_plan = plan_slug[len(prefix):] if plan_slug.startswith(prefix) else plan_slug

    read_only = entitlements.get("read_only", False)
    restriction_code = None

    # v6.0: Overlay billing gate restriction
    if billing_restriction:
        read_only = True
        restriction_code = billing_restriction.get("code")

    return {
        "plan": short_plan,
        "enabled": entitlements["enabled"],
        "read_only": read_only,
        "period": {"start": period_start, "end": period_end},
        "limits": entitlements["limits"],
        "usage": usage,
        "billing_restriction": restriction_code,
    }


# ── Convenience helpers (replace module-specific wrapper files) ──────────────

async def can_use_module(org_doc: dict, module_key: str, feature: str) -> bool:
    """Non-raising check. Returns False if the org cannot use the feature."""
    try:
        await check_module_access(org_doc["id"], module_key, feature, org_doc=org_doc)
        return True
    except HTTPException:
        return False


async def record_module_usage(
    org_id: str, module_key: str, feature_key: str, quantity: int = 1,
) -> None:
    """Record feature usage as a single usage event."""
    await usage_repository.record_usage(org_id, module_key, feature_key, quantity=quantity)


async def enforce_count_quota(
    org_id: str,
    module_key: str,
    feature_key: str,
    *,
    current_count: int,
    pending_quantity: int = 1,
    addon_slug: Optional[str] = None,
    message_template: Optional[str] = None,
    hard_abuse_cap: Optional[int] = None,
) -> int:
    """v5.8 / Onda 9.L — Enforce a snapshot-style quota (e.g. products in
    catalog, active stores, team members) where the quota is the SIZE of a
    collection rather than a count of monthly usage events.

    Use this for limits like:
      · product_catalog.products  (50 / 200 / unlimited)
      · commerce.stores_max       (1 / 3 / unlimited)
      · commerce.orders_monthly   (when counting actual orders this month)
      · team.team_members         (1 / 2 / 5 / 15)

    Behaviour:
      · Resolves the effective limit (base + addon contributions).
      · If unlimited (-1): only enforces hard_abuse_cap if provided.
      · If 0 or N: raises 429 QUOTA_EXCEEDED with rich detail dict
        (compatible with the frontend axios interceptor in client.js
        and the <UpgradePaywall> / <QuotaExceededBanner> components).

    Args:
        org_id: Organization ID.
        module_key: Module identifier (e.g. "product_catalog").
        feature_key: Feature within the module (e.g. "products").
        current_count: Current size of the collection (the caller has
            already counted it — we keep counting flexible per use case).
        pending_quantity: How many new items are about to be created
            (default 1 for single-item creates; pass N for bulk imports).
        addon_slug: Optional add-on plan slug to suggest in the error
            (e.g. "addon_orders_pack" → frontend offers "Buy +200 ordini").
        message_template: Optional custom user-facing message. Receives
            {limit} as format placeholder. Falls back to a generic message.
        hard_abuse_cap: Defence-in-depth absolute cap, applied even when
            limit is unlimited (-1). Prevents abusive automation from
            inserting millions of records.

    Returns:
        The resolved effective_limit (useful for logging / metrics).
    """
    effective_max = await get_effective_limit(org_id, module_key, feature_key)

    # Unlimited: only enforce hard abuse cap
    if effective_max == -1:
        if hard_abuse_cap is not None and current_count + pending_quantity > hard_abuse_cap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Numero massimo assoluto raggiunto ({hard_abuse_cap}). "
                    "Contatta il supporto per casi d'uso eccezionali."
                ),
            )
        return effective_max

    # Quota check
    if current_count + pending_quantity > effective_max:
        if message_template:
            message = message_template.format(limit=effective_max, used=current_count)
        else:
            message = (
                f"Hai raggiunto il limite di {effective_max} {feature_key} del tuo piano. "
                "Aggiorna il piano per crearne altri."
            )
        detail = {
            "code": "QUOTA_EXCEEDED",
            "module_key": module_key,
            "feature_key": feature_key,
            "message": message,
            "current_count": current_count,
            "used": current_count,
            "effective_limit": effective_max,
            "limit": effective_max,
        }
        if addon_slug:
            detail["addon_slug"] = addon_slug
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )

    return effective_max
