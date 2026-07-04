"""Admin Catalog router — Commercial Catalog control plane.

Phase 2a: read-only catalog endpoints.
Phase 2b: safe catalog mutations (cosmetic/commercial fields only).
Phase 2c: controlled entitlement mutations (PricingPlan.limits only).
Phase 2d: controlled commercial bundle mutations (module_plans only).
Phase 2e: controlled pricing mutations (price + Stripe price ID pairs).
Phase 3A: organization commercial state diagnostic (read-only).
Phase 3B: controlled reprovision to current catalog definition.

Mounted at ``/api/admin/catalog`` by server.py.
Requires ``system_admin`` authentication on every endpoint.

Design rules:
  - This router owns catalog READ and SAFE MUTATION operations.
  - Per-org subscription management stays in admin.py.
  - Dangerous/override operations stay in admin.py.
  - No imports from plan_provisioning, module_access, or stripe_service.
"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from auth import require_system_admin
from repositories import catalog_repository

router = APIRouter(
    prefix="/admin/catalog",
    tags=["admin-catalog"],
)


# ==============================================================================
# Commercial Plans (enriched)
# ==============================================================================

@router.get(
    "/plans",
    summary="List all commercial plans with entitlement details",
)
async def list_catalog_plans(
    current_user: dict = Depends(require_system_admin),
) -> list:
    """Return all commercial plans enriched with:

    - resolved entitlement details per module (PricingPlan.limits joined)
    - subscriber_count (number of orgs on this plan)
    """
    return await catalog_repository.list_enriched_commercial_plans()


@router.get(
    "/plans/{slug}",
    summary="Get a single commercial plan with full details",
)
async def get_catalog_plan(
    slug: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Return one commercial plan enriched with:

    - resolved entitlement details per module
    - subscriber_count
    - subscribing_organizations (id, name, billing_status only)
    """
    plan = await catalog_repository.get_enriched_commercial_plan(slug)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Commercial plan '{slug}' not found")
    return plan


# ==============================================================================
# Entitlement Tiers (PricingPlans grouped by module)
# ==============================================================================

@router.get(
    "/entitlement-tiers",
    summary="List entitlement tiers grouped by module",
)
async def list_entitlement_tiers(
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Return all active PricingPlans grouped by module_key.

    Conceptually these are entitlement tiers, not pricing plans.
    Vestigial ``price_monthly`` / ``price_yearly`` fields are excluded.
    """
    return await catalog_repository.list_entitlement_tiers_grouped()


# ==============================================================================
# Catalog Audit Log
# ==============================================================================

@router.get(
    "/audit-log",
    summary="List catalog audit log entries",
)
async def list_catalog_audit_log(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (commercial_plan, pricing_plan)"),
    entity_id: Optional[str] = Query(None, description="Filter by entity slug or id"),
    current_user: dict = Depends(require_system_admin),
) -> list:
    """Return catalog audit entries (paginated, filterable).

    Phase 2a: the audit log is empty — no mutation endpoints exist yet.
    This endpoint is infrastructure for Phase 2b.
    """
    return await catalog_repository.list_catalog_audit_entries(
        skip=skip,
        limit=limit,
        entity_type=entity_type,
        entity_id=entity_id,
    )


# ==============================================================================
# Phase 2b: Safe Catalog Mutations
# ==============================================================================

# ── Whitelist of fields allowed in PATCH /plans/{slug} ────────────────────────
_ALLOWED_PATCH_FIELDS = frozenset({
    "name",
    "description",
    "tagline",
    "features_display",
    "sort_order",
    "is_public",
    "is_self_serve",
    "trial_days",
    # Onda 24 Phase D — addon-specific fields (validated below to be
    # rejected on non-addon plans)
    "addon_provides",
    "compatible_plans",
    "max_quantity",
    "notes",  # not a plan field — used for audit entry only
})

# Fields that exist on CommercialPlan but are forbidden in this mutation phase.
_FORBIDDEN_FIELDS = frozenset({
    "slug",
    "currency",
    "module_plans",
    "price_monthly",
    "price_yearly",
    "stripe_product_id",
    "stripe_price_id_monthly",
    "stripe_price_id_yearly",
    "id",
    "created_at",
    "updated_at",
    "admin_modified_at",
    "is_archived",
})


class PlanPatchRequest(BaseModel):
    """Request body for PATCH /admin/catalog/plans/{slug}.

    All fields are optional.  Only allowed fields are accepted.
    Unknown or forbidden fields cause a 422 validation error.
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    features_display: Optional[List[str]] = None
    sort_order: Optional[int] = None
    is_public: Optional[bool] = None
    is_self_serve: Optional[bool] = None
    trial_days: Optional[int] = None

    # Onda 24 Phase D — Addon-specific fields. Only valid when the
    # target slug points at an addon (is_addon=True). Handler enforces
    # this; on a non-addon plan, sending any of these returns 422 with
    # a clear error.
    addon_provides: Optional[Dict[str, Dict[str, int]]] = None
    compatible_plans: Optional[List[str]] = None
    max_quantity: Optional[int] = Field(default=None, ge=1, le=100)

    # Audit metadata — not a plan field, used for audit entry notes only
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: Any) -> Any:
        """Explicitly reject forbidden fields with a clear error message."""
        if isinstance(data, dict):
            forbidden_found = set(data.keys()) & _FORBIDDEN_FIELDS
            if forbidden_found:
                raise ValueError(
                    f"Forbidden fields in this mutation phase: {sorted(forbidden_found)}. "
                    f"These fields require a different admin operation."
                )
        return data


@router.patch(
    "/plans/{slug}",
    summary="Update safe catalog fields on a commercial plan",
)
async def patch_catalog_plan(
    slug: str,
    body: PlanPatchRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Update cosmetic/commercial fields on a CommercialPlan.

    Phase 2b: only safe fields (name, description, tagline, features_display,
    sort_order, is_public, is_self_serve, trial_days) are accepted.

    Forbidden fields (prices, module_plans, Stripe IDs, slug) are rejected
    with a 422 error.

    If no effective changes are detected, returns the current plan and
    does NOT create an audit entry.
    """
    # Extract notes (audit metadata, not a plan field)
    audit_notes = body.notes

    # Build the patch dict: only fields explicitly set by the caller
    patch_fields: Dict[str, Any] = {}
    for field_name in ("name", "description", "tagline", "features_display",
                       "sort_order", "is_public", "is_self_serve", "trial_days"):
        value = getattr(body, field_name)
        if value is not None:
            patch_fields[field_name] = value

    # ── Onda 24 Phase D — Addon-specific fields ────────────────────────────
    # Reject if the target plan is NOT an addon: these fields are only
    # meaningful for addon entries (is_addon=true). Pre-load plan to
    # discriminate. Idempotency-friendly: the same checks happen
    # regardless of whether other fields are also being mutated.
    addon_only_fields = ("addon_provides", "compatible_plans", "max_quantity")
    addon_changes_pending = {
        f: getattr(body, f)
        for f in addon_only_fields
        if getattr(body, f) is not None
    }
    if addon_changes_pending:
        from database import commercial_plans_collection as _plans
        _existing = await _plans.find_one(
            {"slug": slug}, {"_id": 0, "is_addon": 1, "compatible_plans": 1},
        )
        if not _existing:
            raise HTTPException(
                status_code=404,
                detail=f"Commercial plan '{slug}' not found",
            )
        if not _existing.get("is_addon"):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "addon_fields_on_non_addon_plan",
                    "message": (
                        "Fields addon_provides/compatible_plans/max_quantity are "
                        f"only valid for addons. Plan '{slug}' is not an addon."
                    ),
                    "fields": sorted(addon_changes_pending.keys()),
                },
            )
        # Validate compatible_plans only contains real plan slugs (non-addon).
        # Optional but prevents typos that would silently break the
        # add-addon compatibility check.
        if "compatible_plans" in addon_changes_pending:
            cursor = _plans.find(
                {"is_addon": {"$ne": True}, "is_archived": {"$ne": True}},
                {"_id": 0, "slug": 1},
            )
            valid_plan_slugs = {p["slug"] async for p in cursor}
            requested = set(addon_changes_pending["compatible_plans"])
            unknown = requested - valid_plan_slugs - {"free"}
            if unknown:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "compatible_plans_unknown_slug",
                        "message": (
                            f"compatible_plans contains slugs that don't match any "
                            f"existing commercial plan: {sorted(unknown)}. "
                            f"Valid: {sorted(valid_plan_slugs)}."
                        ),
                        "unknown_slugs": sorted(unknown),
                    },
                )
        patch_fields.update(addon_changes_pending)

    if not patch_fields:
        # Nothing to change — return current plan
        plan = await catalog_repository.get_enriched_commercial_plan(slug)
        if not plan:
            raise HTTPException(status_code=404, detail=f"Commercial plan '{slug}' not found")
        return plan

    admin_user_id = current_user.get("user_id", current_user.get("email", "unknown"))

    result = await catalog_repository.patch_commercial_plan(
        slug=slug,
        patch_fields=patch_fields,
        performed_by=admin_user_id,
        notes=audit_notes,
    )

    if result is None:
        raise HTTPException(status_code=404, detail=f"Commercial plan '{slug}' not found")

    return result


# ==============================================================================
# Phase 2c: Controlled Entitlement Mutations
# ==============================================================================

# Fields forbidden in the limits mutation endpoint.
_LIMITS_FORBIDDEN_FIELDS = frozenset({
    "name",
    "module_key",
    "is_active",
    "sort_order",
    "price_monthly",
    "price_yearly",
    "currency",
    "slug",
    "id",
    "created_at",
    "updated_at",
})


class LimitsPatchRequest(BaseModel):
    """Request body for PATCH /admin/catalog/entitlement-tiers/{slug}/limits.

    Requires explicit ``confirm=true`` because limits changes have immediate
    enforcement impact on all organizations subscribed to this tier.
    """

    model_config = ConfigDict(extra="forbid")

    limits: Dict[str, int]
    confirm: bool
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: Any) -> Any:
        """Reject attempts to mutate non-limits PricingPlan fields."""
        if isinstance(data, dict):
            forbidden_found = set(data.keys()) & _LIMITS_FORBIDDEN_FIELDS
            if forbidden_found:
                raise ValueError(
                    f"Forbidden fields in this endpoint: {sorted(forbidden_found)}. "
                    f"Only 'limits', 'confirm', and 'notes' are accepted."
                )
        return data


@router.patch(
    "/entitlement-tiers/{slug}/limits",
    summary="Update limits on an entitlement tier (confirmation required)",
)
async def patch_entitlement_tier_limits(
    slug: str,
    body: LimitsPatchRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Update limits on a PricingPlan (entitlement tier).

    Phase 2c: this is a controlled mutation. Changes to limits affect
    runtime enforcement immediately for all organizations subscribed
    to this tier via module_access.py.

    Requires ``confirm: true`` in the request body.
    Returns the updated tier plus ``impact_count`` (number of active
    module subscriptions using this tier).
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail="Limits mutations require explicit confirmation. Set 'confirm': true.",
        )

    admin_user_id = current_user.get("user_id", current_user.get("email", "unknown"))

    result = await catalog_repository.patch_entitlement_tier_limits(
        slug=slug,
        new_limits=body.limits,
        performed_by=admin_user_id,
        notes=body.notes,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entitlement tier '{slug}' not found",
        )

    return result


# ==============================================================================
# Onda 10 Step C.1 — Create new entitlement tier
# ==============================================================================

class TierCreateRequest(BaseModel):
    """Request body for POST /admin/catalog/entitlement-tiers.

    Allows the system_admin to spin up a brand-new PricingPlan tier
    without redeploying. The new tier is immediately:
      · referenceable by `commercial_plans.module_plans` mappings
      · enforceable by `module_access.check_module_access` once a plan
        actually maps a module to it
      · queryable via the existing GET /admin/catalog/entitlement-tiers

    Validations:
      - slug: 3-60 chars, lowercase letters + digits + underscore only,
              globally unique across all modules
      - module_key: must be a known PRODUCT_MODULES key (or a future
                    one — we don't hardcode the whitelist; the limits
                    are still enforced module-side via the existing
                    feature_keys map)
      - limits: non-empty dict {feature_key: int}
      - sort_order: optional, defaults to 100
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    module_key: str
    name: str
    limits: Dict[str, int]
    sort_order: Optional[int] = 100
    notes: Optional[str] = None


@router.post(
    "/entitlement-tiers",
    status_code=201,
    summary="Create a new entitlement tier (PricingPlan)",
)
async def create_entitlement_tier(
    body: TierCreateRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Create a brand-new entitlement tier in the catalog.

    Onda 10 Step C.1 — admin self-serve creation. After this call, the
    tier exists in pricing_plans collection and is referenceable by any
    CommercialPlan.module_plans mapping (use PATCH module-plans to wire
    a plan to it).

    Audit: a `create_tier` entry is written to catalog_audit_log.

    Conflicts: 409 if slug already exists.
    Validation errors: 400 with structured detail.
    """
    admin_user_id = current_user.get("user_id", current_user.get("email", "unknown"))

    try:
        tier = await catalog_repository.create_entitlement_tier(
            slug=body.slug,
            module_key=body.module_key,
            name=body.name,
            limits=body.limits,
            sort_order=body.sort_order or 100,
            performed_by=admin_user_id,
            notes=body.notes,
        )
    except ValueError as e:
        msg = str(e)
        # Disambiguate: duplicate slug → 409, otherwise 400
        if "already exists" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return {"tier": tier, "created": True}


# ==============================================================================
# Onda 10 Step C.2 — Create new commercial plan
# ==============================================================================

class PlanCreateRequest(BaseModel):
    """Request body for POST /admin/catalog/plans.

    Creates a new public-facing CommercialPlan (not an addon — see C.3
    for addon creation). All fields are admin-editable post-creation
    via the existing PATCH endpoints.

    Stripe IDs (stripe_product_id, stripe_price_id_*) are NEVER set
    here — they remain managed by:
      · Step C.4 auto-create flow (optional, if `auto_create_stripe`
        is added to this body in a future iteration)
      · The existing PATCH /admin/catalog/plans/{slug}/pricing endpoint

    The frontend "+ New Plan" form (Step C.5) collects these fields.
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    description: Optional[str] = ""
    tagline: Optional[str] = ""
    price_monthly: float = 0.0
    price_yearly: Optional[float] = None
    currency: Optional[str] = "EUR"
    trial_days: Optional[int] = 0
    is_public: Optional[bool] = True
    is_self_serve: Optional[bool] = True
    sort_order: Optional[int] = 100
    module_plans: Optional[Dict[str, str]] = None
    features_display: Optional[List[str]] = None
    platform_limits: Optional[Dict[str, int]] = None
    addon_ctas: Optional[Dict[str, str]] = None
    notes: Optional[str] = None
    # Onda 10 Step C.4 — opt-in Stripe Product+Price auto-creation
    auto_create_stripe: Optional[bool] = False


@router.post(
    "/plans",
    status_code=201,
    summary="Create a new commercial plan (non-addon)",
)
async def create_commercial_plan(
    body: PlanCreateRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Create a brand-new commercial plan.

    Onda 10 Step C.2 — admin self-serve creation. After this call:
      · plan exists in commercial_plans (is_addon=False, is_archived=False)
      · admin can assign it to orgs via PUT /admin/organizations/{id}/
        commercial-plan (Step B.3 made this validation DB-driven, so the
        new slug is accepted immediately)
      · plan appears in /api/billing/plans if is_public=True
      · plan is editable via existing PATCH endpoints

    Conflicts: 409 if slug already exists.
    Validation errors: 400 for invalid slug, prices, or module_plans
    references.
    """
    admin_user_id = current_user.get("user_id", current_user.get("email", "unknown"))
    try:
        plan = await catalog_repository.create_commercial_plan(
            slug=body.slug,
            name=body.name,
            description=body.description or "",
            tagline=body.tagline or "",
            price_monthly=body.price_monthly,
            price_yearly=body.price_yearly,
            currency=body.currency or "EUR",
            trial_days=body.trial_days or 0,
            is_public=body.is_public if body.is_public is not None else True,
            is_self_serve=body.is_self_serve if body.is_self_serve is not None else True,
            sort_order=body.sort_order or 100,
            module_plans=body.module_plans,
            features_display=body.features_display,
            platform_limits=body.platform_limits,
            addon_ctas=body.addon_ctas,
            performed_by=admin_user_id,
            notes=body.notes,
        )
    except ValueError as e:
        msg = str(e)
        if "already exists" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    # Onda 10 Step C.4 — Optional Stripe Product+Price auto-create.
    # NON-FATAL on failure: plan stays in DB without Stripe IDs and
    # admin can complete manually later via PATCH plans/{slug}/pricing.
    stripe_result = None
    stripe_error = None
    if body.auto_create_stripe:
        try:
            from services.stripe_catalog_service import ensure_stripe_for_plan
            stripe_result = await ensure_stripe_for_plan(plan)
            if stripe_result:
                # Persist the IDs into the freshly-created plan doc
                from database import commercial_plans_collection
                await commercial_plans_collection.update_one(
                    {"slug": plan["slug"]},
                    {"$set": {
                        "stripe_product_id": stripe_result.get("stripe_product_id"),
                        "stripe_price_id_monthly": stripe_result.get("stripe_price_id_monthly"),
                        "stripe_price_id_yearly": stripe_result.get("stripe_price_id_yearly"),
                    }},
                )
                # Reflect into the response
                plan["stripe_product_id"] = stripe_result.get("stripe_product_id")
                plan["stripe_price_id_monthly"] = stripe_result.get("stripe_price_id_monthly")
                plan["stripe_price_id_yearly"] = stripe_result.get("stripe_price_id_yearly")
            else:
                stripe_error = "Stripe not configured or unreachable"
        except Exception as e:
            stripe_error = f"{type(e).__name__}: {str(e)[:200]}"

    return {
        "plan": plan,
        "created": True,
        "stripe": {
            "auto_create_requested": bool(body.auto_create_stripe),
            "result": stripe_result,
            "error": stripe_error,
        },
    }


# ==============================================================================
# Onda 10 Step C.3 — Create new addon
# ==============================================================================

class AddonCreateRequest(BaseModel):
    """Request body for POST /admin/catalog/addons.

    Creates a new addon (CommercialPlan with is_addon=True). Addons:
      · Add a Stripe subscription_item on top of the main plan
      · Contribute extra quota to specific feature_keys via
        addon_provides: {module_key: {feature_key: int}}
      · Are stackable up to `max_quantity`
      · Are restricted to specific main plans via `compatible_plans`
        (empty list = compatible with any non-free plan)

    Stripe Product+Price NOT auto-created here — Step C.4 adds that.
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    description: Optional[str] = ""
    price_monthly: float
    addon_provides: Dict[str, Dict[str, int]]
    compatible_plans: Optional[List[str]] = None
    max_quantity: Optional[int] = 1
    currency: Optional[str] = "EUR"
    sort_order: Optional[int] = 100
    notes: Optional[str] = None
    # Onda 10 Step C.4 — opt-in Stripe Product+Price auto-creation
    auto_create_stripe: Optional[bool] = False


@router.post(
    "/addons",
    status_code=201,
    summary="Create a new addon (CommercialPlan with is_addon=True)",
)
async def create_addon(
    body: AddonCreateRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Create a brand-new addon. After this call the addon can be:

      · Listed via GET /admin/catalog/plans (filtered by is_addon=True)
      · Purchased by orgs (subject to compatible_plans restriction)
      · Assigned manually by admin via the existing
        POST /admin/organizations/{org_id}/addons endpoint
      · Edited via PATCH /admin/catalog/plans/{slug} (existing endpoint)

    The addon's contribution to per-feature limits is computed live by
    `module_access._get_addon_contribution` — once created, it
    immediately enriches `effective_limit` for any org that subscribes.

    Conflicts: 409 if slug exists.
    Validation: 400 for invalid slug, prices, addon_provides, or
    compatible_plans references.
    """
    admin_user_id = current_user.get("user_id", current_user.get("email", "unknown"))
    try:
        addon = await catalog_repository.create_addon(
            slug=body.slug,
            name=body.name,
            description=body.description or "",
            price_monthly=body.price_monthly,
            addon_provides=body.addon_provides,
            compatible_plans=body.compatible_plans,
            max_quantity=body.max_quantity or 1,
            currency=body.currency or "EUR",
            sort_order=body.sort_order or 100,
            performed_by=admin_user_id,
            notes=body.notes,
        )
    except ValueError as e:
        msg = str(e)
        if "already exists" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    # Onda 10 Step C.4 — Optional Stripe auto-create for addons.
    stripe_result = None
    stripe_error = None
    if body.auto_create_stripe:
        try:
            from services.stripe_catalog_service import ensure_stripe_for_addon
            stripe_result = await ensure_stripe_for_addon(addon)
            if stripe_result:
                from database import commercial_plans_collection
                await commercial_plans_collection.update_one(
                    {"slug": addon["slug"]},
                    {"$set": {
                        "stripe_product_id": stripe_result.get("stripe_product_id"),
                        "stripe_price_id_monthly": stripe_result.get("stripe_price_id_monthly"),
                    }},
                )
                addon["stripe_product_id"] = stripe_result.get("stripe_product_id")
                addon["stripe_price_id_monthly"] = stripe_result.get("stripe_price_id_monthly")
            else:
                stripe_error = "Stripe not configured or unreachable"
        except Exception as e:
            stripe_error = f"{type(e).__name__}: {str(e)[:200]}"

    return {
        "addon": addon,
        "created": True,
        "stripe": {
            "auto_create_requested": bool(body.auto_create_stripe),
            "result": stripe_result,
            "error": stripe_error,
        },
    }


# ==============================================================================
# Onda 10 Step D.3 — Stripe price drift detection (read-only validate)
# ==============================================================================

@router.get(
    "/plans/{slug}/stripe-validate",
    summary="Validate plan pricing vs LIVE Stripe (read-only)",
)
async def validate_plan_stripe_pricing(
    slug: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Compare the DB-stored price_monthly/price_yearly + currency for a
    plan/addon against the actual Stripe Price objects referenced by
    `stripe_price_id_monthly` / `stripe_price_id_yearly`.

    Returns:
      {
        "slug": str,
        "configured": bool,           # True if any Stripe ID is set
        "monthly": {db_price, stripe_unit_amount, drift, reason} | None,
        "yearly":  {...} | None,
        "errors":  [str, ...],         # API/transport errors
        "overall_drift": bool,         # True if any drift OR any error
      }

    Read-only — does NOT mutate Stripe nor DB. Useful for the admin UI
    to surface mismatches between what the catalog says and what Stripe
    actually charges (e.g. after a manual Stripe Dashboard edit).

    Onda 10 Step D.3.
    """
    from repositories import billing_repository
    plan = await billing_repository.get_commercial_plan(slug)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {slug!r} not found")

    from services.stripe_catalog_service import validate_stripe_pricing
    result = await validate_stripe_pricing(plan)

    # Compute overall_drift
    monthly_drift = (result.get("monthly") or {}).get("drift", False)
    yearly_drift = (result.get("yearly") or {}).get("drift", False)
    has_errors = bool(result.get("errors"))
    overall = monthly_drift or yearly_drift or has_errors

    return {
        "slug": slug,
        "configured": result.get("configured", False),
        "monthly": result.get("monthly"),
        "yearly": result.get("yearly"),
        "errors": result.get("errors", []),
        "overall_drift": bool(overall),
    }


# ==============================================================================
# Onda 11 Step 2 — Stripe linkage snapshot (admin UI source of truth)
# ==============================================================================


def _build_linkage_advisories(
    *,
    is_addon: bool,
    db_snapshot: dict,
    product_remote: dict,
    pricing_remote: dict,
    active_subscriptions_count: int,
) -> List[str]:
    """Generate human-readable advisories for the Stripe linkage UI.

    Each advisory is a short sentence that the frontend can render
    verbatim as a warning chip. The list is empty when everything is
    healthy. Strings are deliberately operator-focused (English) — the
    system_admin pannel is internal-only and not localized.
    """
    advisories: List[str] = []

    # Product issues
    if db_snapshot.get("stripe_product_id") and product_remote.get("exists") is False:
        advisories.append(
            f"Stripe Product {db_snapshot['stripe_product_id']!r} not found "
            f"on your Stripe account. Re-link to a valid prod_xxx."
        )
    elif product_remote.get("exists") is True and product_remote.get("active") is False:
        advisories.append(
            "Linked Stripe Product is archived (Product.active=false). "
            "New checkouts on this plan will fail."
        )
    elif product_remote.get("exists") is True:
        meta_slug = product_remote.get("metadata_afianco_slug")
        if meta_slug and meta_slug != db_snapshot.get("slug"):
            advisories.append(
                f"Stripe Product metadata.afianco_slug={meta_slug!r} "
                f"does not match plan slug {db_snapshot.get('slug')!r}. "
                f"Possible wrong-Product linkage."
            )

    # Price issues (delegate to validate_stripe_pricing's reason codes)
    monthly = pricing_remote.get("monthly") or {}
    if monthly.get("drift"):
        reason = monthly.get("reason") or "drift"
        advisories.append(f"Monthly price drift: {reason}")
    yearly = pricing_remote.get("yearly") or {}
    if yearly.get("drift"):
        reason = yearly.get("reason") or "drift"
        advisories.append(f"Yearly price drift: {reason}")

    # Addon-only sanity
    if is_addon and db_snapshot.get("stripe_price_id_yearly"):
        advisories.append(
            "Addon has a stripe_price_id_yearly set, but addons are "
            "monthly-only by platform design. Yearly Price is ignored."
        )

    # Active subscriptions advisory (always emitted when count > 0 — it's
    # context, not necessarily an error)
    if active_subscriptions_count > 0:
        advisories.append(
            f"{active_subscriptions_count} organisation(s) have active "
            f"Stripe subscriptions on this plan. Changing stripe_product_id "
            f"will not migrate them."
        )

    # Stripe transport errors surfaced explicitly
    if pricing_remote.get("errors"):
        for err in pricing_remote["errors"]:
            advisories.append(f"Stripe API error: {err}")
    if product_remote.get("error") and product_remote.get("exists") is None:
        advisories.append(f"Stripe API error (product): {product_remote['error']}")

    return advisories


@router.get(
    "/plans/{slug}/stripe-linkage",
    summary="Onda 11 Step 2 — full plan/addon → Stripe linkage snapshot for admin UI",
)
async def get_plan_stripe_linkage(
    slug: str,
    _: dict = Depends(require_system_admin),
) -> dict:
    """Return a single source of truth for the system_admin "Stripe linking" UI.

    Combines:
      · DB-side snapshot of the 3 linkage fields (`stripe_product_id`,
        `stripe_price_id_monthly`, `stripe_price_id_yearly`) plus
        `price_monthly`, `price_yearly`, `currency`, `is_addon`
      · Live Stripe state via `validate_stripe_product()` and
        `validate_stripe_pricing()` (read-only)
      · Active-subscription count + 5 examples (drives the guardrail UX)
      · A list of human-readable advisories (warnings) that the UI can
        render as a row of chips

    Read-only — never mutates Stripe nor the DB. Safe to call repeatedly.

    Used by the frontend Step 3 form to populate fields on mount and
    after every save (re-fetch confirms drift was actually fixed).
    """
    from repositories import billing_repository
    plan = await billing_repository.get_commercial_plan(slug)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {slug!r} not found")

    from services.stripe_catalog_service import (
        validate_stripe_product,
        validate_stripe_pricing,
    )

    # 1. DB snapshot — only the fields the UI actually needs.
    db_snapshot = {
        "slug": plan.get("slug"),
        "name": plan.get("name"),
        "is_addon": bool(plan.get("is_addon", False)),
        "currency": (plan.get("currency") or "EUR").upper(),
        "price_monthly": plan.get("price_monthly"),
        "price_yearly": plan.get("price_yearly"),
        "stripe_product_id": plan.get("stripe_product_id"),
        "stripe_price_id_monthly": plan.get("stripe_price_id_monthly"),
        "stripe_price_id_yearly": plan.get("stripe_price_id_yearly"),
    }

    # 2. Stripe remote — Product + both Prices.
    product_remote = await validate_stripe_product(db_snapshot["stripe_product_id"])
    pricing_remote = await validate_stripe_pricing(plan)

    # 3. Active subscribers — count + small sample for the UX warning.
    from database import organizations_collection
    active_count = await organizations_collection.count_documents({
        "commercial_plan_slug": slug,
        "stripe_subscription_id": {"$nin": [None, ""]},
    })
    examples = []
    if active_count > 0:
        cursor = organizations_collection.find(
            {
                "commercial_plan_slug": slug,
                "stripe_subscription_id": {"$nin": [None, ""]},
            },
            {"_id": 0, "id": 1, "name": 1, "stripe_subscription_id": 1},
        ).limit(5)
        async for doc in cursor:
            examples.append({
                "org_id": doc.get("id"),
                "name": doc.get("name"),
                "stripe_subscription_id": doc.get("stripe_subscription_id"),
            })

    # 4. Advisories — derived warnings ready for UI consumption.
    advisories = _build_linkage_advisories(
        is_addon=db_snapshot["is_addon"],
        db_snapshot=db_snapshot,
        product_remote=product_remote,
        pricing_remote=pricing_remote,
        active_subscriptions_count=active_count,
    )

    return {
        "slug": slug,
        "name": db_snapshot["name"],
        "is_addon": db_snapshot["is_addon"],
        "currency": db_snapshot["currency"],
        "db_snapshot": db_snapshot,
        "stripe_remote": {
            "product": product_remote,
            "price_monthly": pricing_remote.get("monthly"),
            "price_yearly": pricing_remote.get("yearly"),
            "pricing_errors": pricing_remote.get("errors", []),
        },
        "active_subscriptions": {
            "count": active_count,
            "examples": examples,
        },
        "advisories": advisories,
    }


# ==============================================================================
# Onda 10 Step C.6 — Plan archive (soft delete) / unarchive
# ==============================================================================

class ArchivePatchRequest(BaseModel):
    """Request body for archive / unarchive endpoints."""

    model_config = ConfigDict(extra="forbid")

    confirm: bool
    notes: Optional[str] = None


@router.patch(
    "/plans/{slug}/archive",
    summary="Archive (soft-delete) a commercial plan",
)
async def archive_plan(
    slug: str,
    body: ArchivePatchRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Soft-delete a plan: marks `is_archived=True`.

    Onda 10 Step C.6. Effects:
      · Existing org subscriptions on this plan keep running (zero impact)
      · The plan is no longer assignable to new orgs (Step B.3 validation
        rejects is_archived=True plans in PUT commercial-plan)
      · Admin catalog UI continues to show it with archived flag for
        historical reference

    Reversible via `unarchive` endpoint below. Audit-logged.

    Requires `confirm: true`.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail="Archive requires explicit confirmation. Set 'confirm': true.",
        )

    admin_user_id = current_user.get("user_id", current_user.get("email", "unknown"))
    result = await catalog_repository.set_plan_archive_state(
        slug=slug,
        is_archived=True,
        performed_by=admin_user_id,
        notes=body.notes,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Plan {slug!r} not found")
    return result


@router.patch(
    "/plans/{slug}/unarchive",
    summary="Restore an archived commercial plan",
)
async def unarchive_plan(
    slug: str,
    body: ArchivePatchRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Reverse an archive: marks `is_archived=False`.

    Onda 10 Step C.6. After unarchive, the plan is again assignable
    to orgs via PUT commercial-plan. Audit-logged.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail="Unarchive requires explicit confirmation. Set 'confirm': true.",
        )
    admin_user_id = current_user.get("user_id", current_user.get("email", "unknown"))
    result = await catalog_repository.set_plan_archive_state(
        slug=slug,
        is_archived=False,
        performed_by=admin_user_id,
        notes=body.notes,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Plan {slug!r} not found")
    return result


# ==============================================================================
# Phase 2d: Controlled Commercial Bundle Mutations
# ==============================================================================

# Fields forbidden in the module-plans mutation endpoint.
_MODULE_PLANS_FORBIDDEN_FIELDS = frozenset({
    "name",
    "description",
    "tagline",
    "trial_days",
    "price_monthly",
    "price_yearly",
    "is_public",
    "is_self_serve",
    "sort_order",
    "features_display",
    "slug",
    "currency",
    "stripe_product_id",
    "stripe_price_id_monthly",
    "stripe_price_id_yearly",
    "id",
    "created_at",
    "updated_at",
    "admin_modified_at",
    "is_archived",
})


class ModulePlansPatchRequest(BaseModel):
    """Request body for PATCH /admin/catalog/plans/{slug}/module-plans.

    Requires explicit ``confirm=true`` because module_plans changes affect
    the commercial bundle definition for future provisioning.
    """

    model_config = ConfigDict(extra="forbid")

    module_plans: Dict[str, str]
    confirm: bool
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: Any) -> Any:
        """Reject attempts to mutate non-module_plans CommercialPlan fields."""
        if isinstance(data, dict):
            forbidden_found = set(data.keys()) & _MODULE_PLANS_FORBIDDEN_FIELDS
            if forbidden_found:
                raise ValueError(
                    f"Forbidden fields in this endpoint: {sorted(forbidden_found)}. "
                    f"Only 'module_plans', 'confirm', and 'notes' are accepted."
                )
        return data


@router.patch(
    "/plans/{slug}/module-plans",
    summary="Update module-plan mapping on a commercial plan (confirmation required)",
)
async def patch_plan_module_plans(
    slug: str,
    body: ModulePlansPatchRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Update the module_plans mapping on a CommercialPlan.

    Phase 2d: this is a controlled catalog-only mutation. It changes which
    entitlement tier each module maps to for this commercial plan.

    This affects FUTURE provisioning only. Already provisioned organizations
    are NOT automatically reprovisioned — the response explicitly signals
    ``auto_reprovisioned: false``.

    Requires ``confirm: true`` in the request body.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail="Module-plans mutations require explicit confirmation. Set 'confirm': true.",
        )

    # Validate the mapping: every slug must exist and match its module_key
    validation_error = await catalog_repository.validate_module_plans_mapping(
        body.module_plans
    )
    if validation_error:
        raise HTTPException(status_code=422, detail=validation_error)

    admin_user_id = current_user.get("user_id", current_user.get("email", "unknown"))

    result = await catalog_repository.patch_module_plans(
        slug=slug,
        new_module_plans=body.module_plans,
        performed_by=admin_user_id,
        notes=body.notes,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Commercial plan '{slug}' not found",
        )

    return result


# ==============================================================================
# Phase 2e: Controlled Pricing Mutations
# ==============================================================================

# Fields forbidden in the pricing mutation endpoint.
# Onda 11 Step 1 — `stripe_product_id` is no longer forbidden. It is now
# admin-editable so that broken plan→Stripe linkage can be repaired
# via the system_admin UI without DB hand-editing. The active-subscription
# guardrail in the handler protects orgs already on Stripe.
_PRICING_FORBIDDEN_FIELDS = frozenset({
    "name",
    "description",
    "tagline",
    "trial_days",
    "is_public",
    "is_self_serve",
    "sort_order",
    "features_display",
    "module_plans",
    "slug",
    "currency",
    "id",
    "created_at",
    "updated_at",
    "admin_modified_at",
    "is_archived",
})


class PricingPatchRequest(BaseModel):
    """Request body for PATCH /admin/catalog/plans/{slug}/pricing.

    Requires explicit ``confirm=true`` because pricing changes affect
    future checkout behavior.

    Pricing coherence rules:
      - ``price_monthly`` and ``stripe_price_id_monthly`` must be provided together
      - ``price_yearly`` and ``stripe_price_id_yearly`` must be provided together
      - At least one coherent pair OR ``stripe_product_id`` must be provided
        (Onda 11: a pure product-relink without price change is allowed.)

    Stripe ID format validation:
      - ``stripe_product_id``       must match ``^prod_[A-Za-z0-9]+$``
      - ``stripe_price_id_monthly`` must match ``^price_[A-Za-z0-9]+$``
      - ``stripe_price_id_yearly``  must match ``^price_[A-Za-z0-9]+$``

    Active-subscription guardrail (Onda 11 Step 1):
      Changing ``stripe_product_id`` while organisations have active
      Stripe subscriptions on this plan requires
      ``confirm_active_subscriptions: true``. The handler returns 409
      if active subs exist and the flag is false.
    """

    model_config = ConfigDict(extra="forbid")

    price_monthly: Optional[float] = None
    stripe_price_id_monthly: Optional[str] = Field(
        default=None,
        pattern=r"^price_[A-Za-z0-9]+$",
        description="Stripe Price ID for monthly billing (price_xxx).",
    )
    price_yearly: Optional[float] = None
    stripe_price_id_yearly: Optional[str] = Field(
        default=None,
        pattern=r"^price_[A-Za-z0-9]+$",
        description="Stripe Price ID for yearly billing (price_xxx).",
    )
    # Onda 11 Step 1 — admin-editable Stripe Product ID for linkage repair.
    stripe_product_id: Optional[str] = Field(
        default=None,
        pattern=r"^prod_[A-Za-z0-9]+$",
        description="Stripe Product ID (prod_xxx). Admin-editable for relink.",
    )
    confirm_active_subscriptions: bool = False

    confirm: bool
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: Any) -> Any:
        """Reject attempts to mutate non-pricing CommercialPlan fields."""
        if isinstance(data, dict):
            forbidden_found = set(data.keys()) & _PRICING_FORBIDDEN_FIELDS
            if forbidden_found:
                raise ValueError(
                    f"Forbidden fields in this endpoint: {sorted(forbidden_found)}. "
                    f"Only pricing fields, 'stripe_product_id', "
                    f"'confirm_active_subscriptions', 'confirm', and 'notes' "
                    f"are accepted."
                )
        return data

    @model_validator(mode="after")
    def validate_pricing_coherence(self) -> "PricingPatchRequest":
        """Enforce paired pricing fields for catalog coherence."""
        has_price_m = self.price_monthly is not None
        has_stripe_m = self.stripe_price_id_monthly is not None
        has_price_y = self.price_yearly is not None
        has_stripe_y = self.stripe_price_id_yearly is not None
        has_product_id = self.stripe_product_id is not None

        # Monthly pair coherence
        if has_price_m != has_stripe_m:
            raise ValueError(
                "Monthly pricing must be updated as a pair: "
                "provide both 'price_monthly' and 'stripe_price_id_monthly', or neither."
            )

        # Yearly pair coherence
        if has_price_y != has_stripe_y:
            raise ValueError(
                "Yearly pricing must be updated as a pair: "
                "provide both 'price_yearly' and 'stripe_price_id_yearly', or neither."
            )

        # At least one mutation required: monthly pair, yearly pair,
        # or a product-only relink (Onda 11).
        if not has_price_m and not has_price_y and not has_product_id:
            raise ValueError(
                "At least one mutation must be provided: "
                "monthly pair (price_monthly + stripe_price_id_monthly), "
                "yearly pair (price_yearly + stripe_price_id_yearly), "
                "or a product relink (stripe_product_id)."
            )

        return self


async def _count_active_stripe_subscribers(slug: str) -> int:
    """Onda 11 — count orgs on this plan with a non-null stripe_subscription_id.

    Distinct from `_get_subscriber_count` (which counts all orgs on the
    plan including free/manual): this is the safety-relevant figure for
    the active-subscription guardrail on `stripe_product_id` mutations.
    """
    from database import organizations_collection
    return await organizations_collection.count_documents({
        "commercial_plan_slug": slug,
        "stripe_subscription_id": {"$nin": [None, ""]},
    })


async def _count_active_addon_subscribers(addon_slug: str) -> int:
    """Onda 24 Phase C — count orgs with this addon currently active.

    For commercial plans that are addons (`is_addon=True`), the previous
    helper `_count_active_stripe_subscribers` always returned 0 because
    addons don't sit on `org.commercial_plan_slug` — they sit in the
    dedicated `addon_subscriptions` collection. This made the
    stripe_product_id guardrail silently never fire for addons,
    allowing an admin to swap the Product behind active addon customers
    without warning.

    Counts AddonSubscription rows with status="active". Webhook + Onda 12
    keep this collection up-to-date with Stripe truth.
    """
    from database import addon_subscriptions_collection
    return await addon_subscriptions_collection.count_documents({
        "addon_slug": addon_slug,
        "status": "active",
    })


async def _count_active_subscribers_for_slug(slug: str, is_addon: bool) -> int:
    """Onda 24 Phase C — dispatcher: pick the right counter based on
    whether the entity is a plan or an addon. Used by the
    active-subscription guardrail in patch_plan_pricing.
    """
    if is_addon:
        return await _count_active_addon_subscribers(slug)
    return await _count_active_stripe_subscribers(slug)


@router.patch(
    "/plans/{slug}/pricing",
    summary="Update pricing or Stripe linkage on a commercial plan (confirmation required)",
)
async def patch_plan_pricing(
    slug: str,
    body: PricingPatchRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Update pricing fields and/or Stripe linkage on a CommercialPlan.

    Phase 2e + Onda 11 Step 1: this is a controlled catalog-only
    mutation. It changes the price, the Stripe Price IDs, and/or the
    Stripe Product ID used for future checkouts.

    Pricing coherence is enforced: price and Stripe ID must be updated
    as pairs (monthly pair, yearly pair, or both).

    Existing subscribers are NOT migrated — their Stripe subscriptions
    reference the specific Product/Price ID at subscription creation
    time. To protect against silent inconsistency, mutations to
    ``stripe_product_id`` while active Stripe subscribers exist on this
    plan require ``confirm_active_subscriptions: true``. Otherwise the
    endpoint returns 409.

    Requires ``confirm: true`` in the request body.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail="Pricing mutations require explicit confirmation. Set 'confirm': true.",
        )

    # Onda 11 + Onda 24 Phase C — active-subscription guardrail on
    # stripe_product_id changes. Uses the right counter for plan vs
    # addon (Phase C: addons count via addon_subscriptions collection,
    # not via org.commercial_plan_slug which is always 0 for addons).
    if body.stripe_product_id is not None:
        from database import commercial_plans_collection
        existing = await commercial_plans_collection.find_one(
            {"slug": slug},
            {"_id": 0, "stripe_product_id": 1, "is_addon": 1},
        )
        # Only treat as a Product change if the value actually differs.
        is_actual_product_change = (
            existing is not None
            and existing.get("stripe_product_id") != body.stripe_product_id
        )
        if is_actual_product_change and not body.confirm_active_subscriptions:
            is_addon = bool(existing.get("is_addon", False))
            active_count = await _count_active_subscribers_for_slug(slug, is_addon)
            if active_count > 0:
                entity_label = "addon" if is_addon else "plan"
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "active_subscriptions_present",
                        "message": (
                            f"{active_count} organisation(s) have active "
                            f"{entity_label} subscriptions on '{slug}'. Changing "
                            f"stripe_product_id will leave their existing "
                            f"subscriptions linked to the OLD Product. "
                            f"Set 'confirm_active_subscriptions': true to proceed."
                        ),
                        "affected_org_count": active_count,
                        "slug": slug,
                        "field": "stripe_product_id",
                        "entity_kind": entity_label,
                    },
                )

    # ── Onda 24 Phase A — Pre-save Stripe state validation ────────────────
    # Before writing the linkage to the DB, verify that every Stripe ID
    # provided actually points at a usable resource on Stripe. Prevents
    # the class of bug "admin pastes a CHF Price into an EUR plan" that
    # only surfaces later as a 500 at customer purchase time.
    #
    # Universal: applies to plans AND addons (same endpoint, same
    # commercial_plans collection).
    #
    # Validations:
    #   · stripe_product_id  → must exist + active
    #   · stripe_price_id_*  → must exist + active + recurring with the
    #                          right interval + currency matching the
    #                          plan/addon currency
    #
    # On any mismatch raises 422 with a precise `code` so the frontend
    # can present a clear remediation hint.
    if (
        body.stripe_product_id is not None
        or body.stripe_price_id_monthly is not None
        or body.stripe_price_id_yearly is not None
    ):
        from database import commercial_plans_collection as _plans_col
        plan_doc = await _plans_col.find_one(
            {"slug": slug}, {"_id": 0, "currency": 1, "is_addon": 1},
        )
        if not plan_doc:
            raise HTTPException(
                status_code=404, detail=f"Plan '{slug}' not found",
            )
        expected_currency = (plan_doc.get("currency") or "EUR").upper()

        try:
            import stripe as _stripe
            import os as _os
            _stripe.api_key = _os.environ.get("STRIPE_SECRET_KEY", "").strip()
            stripe_ready = bool(_stripe.api_key)
        except Exception:
            stripe_ready = False

        # If Stripe SDK / key isn't configured, skip validation (graceful
        # degradation — the existing DB-only path still works).
        if stripe_ready:
            def _raise_invalid(code: str, message: str, **extra):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": code,
                        "message": message,
                        "slug": slug,
                        **extra,
                    },
                )

            # 1. Validate Product
            if body.stripe_product_id is not None:
                try:
                    prod = await asyncio.to_thread(
                        _stripe.Product.retrieve, body.stripe_product_id,
                    )
                except Exception as e:
                    _raise_invalid(
                        "stripe_product_not_found",
                        f"Stripe Product {body.stripe_product_id!r} non trovato. "
                        f"Verifica l'ID nel Stripe Dashboard. ({type(e).__name__}: {str(e)[:120]})",
                        field="stripe_product_id",
                    )
                # Onda 27.1 — Stripe SDK StripeObject doesn't expose `.get()` on
                # all versions; use the same hasattr-defensive pattern already
                # used at line 1518 below for `recurring`. Prevents AttributeError
                # 'get' on PATCH /api/admin/catalog/plans/{slug}/pricing.
                _prod_active = (
                    prod.get("active") if hasattr(prod, "get")
                    else getattr(prod, "active", True)
                )
                if _prod_active is False:
                    _raise_invalid(
                        "stripe_product_archived",
                        f"Stripe Product {body.stripe_product_id!r} è archiviato (active=false). "
                        "Riattivalo o usa un Product diverso.",
                        field="stripe_product_id",
                    )

            # 2. Validate Prices (monthly + optional yearly) for currency,
            # active, recurring, interval.
            for field_name, price_id, expected_interval in (
                ("stripe_price_id_monthly", body.stripe_price_id_monthly, "month"),
                ("stripe_price_id_yearly", body.stripe_price_id_yearly, "year"),
            ):
                if price_id is None:
                    continue
                try:
                    price = await asyncio.to_thread(
                        _stripe.Price.retrieve, price_id,
                    )
                except Exception as e:
                    _raise_invalid(
                        "stripe_price_not_found",
                        f"Stripe Price {price_id!r} non trovato. "
                        f"Verifica l'ID nel Stripe Dashboard. ({type(e).__name__}: {str(e)[:120]})",
                        field=field_name,
                    )
                # Onda 27.1 — same hasattr-defensive pattern as above.
                _price_active = (
                    price.get("active") if hasattr(price, "get")
                    else getattr(price, "active", True)
                )
                if _price_active is False:
                    _raise_invalid(
                        "stripe_price_inactive",
                        f"Stripe Price {price_id!r} è inattivo (active=false). "
                        "Crea un nuovo Price o riattivalo.",
                        field=field_name,
                    )
                _price_currency_raw = (
                    price.get("currency") if hasattr(price, "get")
                    else getattr(price, "currency", None)
                )
                price_currency = (_price_currency_raw or "").upper()
                if price_currency and price_currency != expected_currency:
                    _raise_invalid(
                        "stripe_currency_mismatch",
                        f"Stripe Price {price_id!r} è in valuta {price_currency} "
                        f"ma il piano usa {expected_currency}. "
                        f"Crea un Price nella valuta corretta.",
                        field=field_name,
                        stripe_currency=price_currency,
                        expected_currency=expected_currency,
                    )
                # Onda 27.1 — same hasattr-defensive pattern.
                _recurring_raw = (
                    price.get("recurring") if hasattr(price, "get")
                    else getattr(price, "recurring", None)
                )
                recurring = _recurring_raw or {}
                actual_interval = (
                    recurring.get("interval") if hasattr(recurring, "get")
                    else getattr(recurring, "interval", None)
                )
                if not actual_interval:
                    _raise_invalid(
                        "stripe_price_not_recurring",
                        f"Stripe Price {price_id!r} è one-time, non ricorrente. "
                        "Per gli abbonamenti serve un Price con recurring.",
                        field=field_name,
                    )
                if actual_interval != expected_interval:
                    _raise_invalid(
                        "stripe_price_interval_mismatch",
                        f"Stripe Price {price_id!r} è ricorrente {actual_interval}ly "
                        f"ma il campo {field_name} richiede {expected_interval}ly.",
                        field=field_name,
                        stripe_interval=actual_interval,
                        expected_interval=expected_interval,
                    )

    # Build mutation fields dict from provided pairs + optional product relink
    pricing_fields: Dict[str, Any] = {}
    if body.price_monthly is not None:
        pricing_fields["price_monthly"] = body.price_monthly
        pricing_fields["stripe_price_id_monthly"] = body.stripe_price_id_monthly
    if body.price_yearly is not None:
        pricing_fields["price_yearly"] = body.price_yearly
        pricing_fields["stripe_price_id_yearly"] = body.stripe_price_id_yearly
    if body.stripe_product_id is not None:
        pricing_fields["stripe_product_id"] = body.stripe_product_id

    admin_user_id = current_user.get("user_id", current_user.get("email", "unknown"))

    result = await catalog_repository.patch_pricing(
        slug=slug,
        pricing_fields=pricing_fields,
        performed_by=admin_user_id,
        notes=body.notes,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Commercial plan '{slug}' not found",
        )

    return result


# ==============================================================================
# Phase 3D: Batch Commercial Overview (read-only)
# ==============================================================================

@router.get(
    "/organizations/commercial-overview",
    summary="Cross-organization commercial health overview",
)
async def list_org_commercial_overview(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: dict = Depends(require_system_admin),
) -> list:
    """Return lightweight commercial summaries for all organizations.

    Phase 3D: read-only. Batch-optimized — avoids N+1 queries.
    Each summary includes sync status, drift flags, warning indicators,
    and a recommended action (if applicable).
    """
    return await catalog_repository.list_org_commercial_summaries(
        skip=skip, limit=limit,
    )


# ==============================================================================
# Phase 3A: Organization Commercial State (read-only diagnostic)
# ==============================================================================

@router.get(
    "/organizations/{org_id}/commercial-state",
    summary="Diagnostic view of an organization's commercial state",
)
async def get_org_commercial_state(
    org_id: str,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Return a structured commercial-state diagnostic for one organization.

    Phase 3A: read-only. No mutations. No side effects.

    Assembles data from organization, catalog plan, module subscriptions,
    and pricing plans. Computes drift flags that indicate whether the
    org's provisioned state is aligned with the current catalog definition.

    Drift flags include: catalog_plan_missing, missing_module_subscriptions,
    unexpected_module_subscriptions, module_plan_mismatch, limits_mismatch,
    manual_assignment_detected, billing_restricted, legacy_plan_fallback_risk.
    """
    result = await catalog_repository.build_org_commercial_state(org_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Organization '{org_id}' not found",
        )
    return result


# ==============================================================================
# Phase 3B: Controlled Reprovision
# ==============================================================================

class ReprovisionRequest(BaseModel):
    """Request body for POST /admin/catalog/organizations/{org_id}/reprovision-commercial-plan."""

    model_config = ConfigDict(extra="forbid")

    confirm: bool
    notes: Optional[str] = None


@router.post(
    "/organizations/{org_id}/reprovision-commercial-plan",
    summary="Reprovision an organization to its current catalog plan (confirmation required)",
)
async def reprovision_org_commercial_plan(
    org_id: str,
    body: ReprovisionRequest,
    current_user: dict = Depends(require_system_admin),
) -> dict:
    """Reprovision an organization's module subscriptions to match
    the current catalog definition of its assigned commercial plan.

    Phase 3B: uses the canonical provisioning path. Does NOT change
    which plan the org is on — only re-aligns module subscriptions.

    Preserves existing billing_status. Always records an audit entry
    (even if no effective change) to track the admin's explicit action.

    Requires ``confirm: true`` in the request body.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail="Reprovision requires explicit confirmation. Set 'confirm': true.",
        )

    admin_user_id = current_user.get("user_id", current_user.get("email", "unknown"))

    try:
        result = await catalog_repository.reprovision_org_to_catalog(
            org_id=org_id,
            performed_by=admin_user_id,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Organization '{org_id}' not found",
        )

    return result
