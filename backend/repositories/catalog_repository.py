"""Catalog repository — enriched read/write queries for the commercial catalog admin.

Phase 2a: read-only catalog queries.
Phase 2b: safe catalog mutations (cosmetic/commercial fields only) + audit.

Keeps catalog query logic separate from billing_repository.py
(which owns billing event and org billing queries).

All queries project away ``_id`` to keep responses JSON-serialisable.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import (
    catalog_audit_log_collection,
    commercial_plans_collection,
    module_subscriptions_collection,
    organizations_collection,
    pricing_plans_collection,
)
from models.catalog_audit import CatalogAuditEntry


# ==============================================================================
# Commercial plans — enriched with entitlement details
# ==============================================================================

async def _resolve_entitlements(module_plans: Dict[str, str]) -> List[dict]:
    """Resolve module_plans dict into enriched entitlement details.

    For each entry in ``module_plans`` (e.g. {"ai_assistant": "ai_assistant_starter"}),
    join the corresponding PricingPlan and return its limits.

    Returns a list of dicts, one per module:
      [
        {
          "module_key": "ai_assistant",
          "pricing_plan_slug": "ai_assistant_starter",
          "pricing_plan_name": "AI Starter",
          "limits": {"chat": 50, "digest": 4, ...}
        },
        ...
      ]
    """
    entitlements = []
    for module_key, plan_slug in module_plans.items():
        plan = await pricing_plans_collection.find_one(
            {"module_key": module_key, "slug": plan_slug, "is_active": True},
            {"_id": 0, "name": 1, "limits": 1},
        )
        entitlements.append({
            "module_key": module_key,
            "pricing_plan_slug": plan_slug,
            "pricing_plan_name": plan["name"] if plan else None,
            "limits": plan.get("limits", {}) if plan else {},
        })
    return entitlements


async def _get_subscriber_count(slug: str) -> int:
    """Count organisations on a given commercial plan slug."""
    return await organizations_collection.count_documents(
        {"commercial_plan_slug": slug}
    )


async def list_enriched_commercial_plans() -> List[dict]:
    """List all commercial plans with resolved entitlements and subscriber counts."""
    cursor = (
        commercial_plans_collection
        .find({}, {"_id": 0})
        .sort("sort_order", 1)
    )
    plans = await cursor.to_list(50)

    enriched = []
    for plan in plans:
        plan["entitlements"] = await _resolve_entitlements(
            plan.get("module_plans", {})
        )
        plan["subscriber_count"] = await _get_subscriber_count(plan["slug"])
        enriched.append(plan)

    return enriched


async def get_enriched_commercial_plan(slug: str) -> Optional[dict]:
    """Get a single commercial plan with entitlements and subscribing orgs."""
    plan = await commercial_plans_collection.find_one(
        {"slug": slug}, {"_id": 0}
    )
    if not plan:
        return None

    plan["entitlements"] = await _resolve_entitlements(
        plan.get("module_plans", {})
    )
    plan["subscriber_count"] = await _get_subscriber_count(slug)

    # Subscribing orgs — lightweight projection (id, name, billing_status only)
    org_cursor = organizations_collection.find(
        {"commercial_plan_slug": slug},
        {"_id": 0, "id": 1, "name": 1, "billing_status": 1},
    )
    plan["subscribing_organizations"] = await org_cursor.to_list(500)

    return plan


# ==============================================================================
# Entitlement tiers (PricingPlans grouped by module)
# ==============================================================================

async def list_entitlement_tiers_grouped() -> Dict[str, List[dict]]:
    """List active PricingPlans grouped by module_key — SOLO i tier
    referenziati dai piani commerciali a catalogo (16/7/2026,
    consolidamento AU): i tier legacy AFianco non cablati a nessun
    piano Aurya restano nel DB per i fallback, ma non fanno rumore
    nella vista catalogo.

    Excludes vestigial ``price_monthly`` and ``price_yearly`` fields.
    """
    referenced: set = set()
    async for cp in commercial_plans_collection.find(
            {}, {"_id": 0, "module_plans": 1}):
        referenced.update((cp.get("module_plans") or {}).values())

    cursor = (
        pricing_plans_collection
        .find(
            {"is_active": True, "slug": {"$in": sorted(referenced)}},
            {
                "_id": 0,
                "price_monthly": 0,
                "price_yearly": 0,
            },
        )
        .sort("sort_order", 1)
    )
    plans = await cursor.to_list(100)

    grouped: Dict[str, List[dict]] = {}
    for plan in plans:
        module_key = plan.get("module_key", "unknown")
        grouped.setdefault(module_key, []).append(plan)

    return grouped


# ==============================================================================
# Catalog audit log
# ==============================================================================

async def list_catalog_audit_entries(
    skip: int = 0,
    limit: int = 50,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
) -> List[dict]:
    """List catalog audit entries with optional filters."""
    filter_q: dict = {}
    if entity_type:
        filter_q["entity_type"] = entity_type
    if entity_id:
        filter_q["entity_id"] = entity_id

    cursor = (
        catalog_audit_log_collection
        .find(filter_q, {"_id": 0})
        .sort("performed_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return await cursor.to_list(limit)


# ==============================================================================
# Phase 2b: Safe catalog mutations
# ==============================================================================

async def patch_commercial_plan(
    slug: str,
    patch_fields: Dict[str, Any],
    performed_by: str,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """Apply a safe patch to a CommercialPlan and record an audit entry.

    Only fields in ``patch_fields`` are compared and updated.
    If no effective changes are detected (all values match current),
    no write occurs and no audit entry is created.

    Returns the enriched plan after update, or None if slug not found.
    """
    # 1. Load existing plan
    existing = await commercial_plans_collection.find_one(
        {"slug": slug}, {"_id": 0}
    )
    if not existing:
        return None

    # 2. Compute diff: only fields that actually changed
    changes: Dict[str, Dict[str, Any]] = {}
    for field, new_value in patch_fields.items():
        old_value = existing.get(field)
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}

    if not changes:
        # No effective changes — return enriched plan, no audit
        return await get_enriched_commercial_plan(slug)

    # 3. Build the MongoDB update
    now = datetime.now(timezone.utc)
    update_set = {field: diff["new"] for field, diff in changes.items()}
    update_set["admin_modified_at"] = now.isoformat()
    update_set["updated_at"] = now.isoformat()

    await commercial_plans_collection.update_one(
        {"slug": slug},
        {"$set": update_set},
    )

    # 4. Write audit entry
    audit_entry = CatalogAuditEntry(
        entity_type="commercial_plan",
        entity_id=slug,
        action="update",
        changes=changes,
        performed_by=performed_by,
        performed_at=now,
        notes=notes,
    )
    audit_doc = audit_entry.model_dump()
    audit_doc["performed_at"] = audit_doc["performed_at"].isoformat()
    await catalog_audit_log_collection.insert_one(audit_doc)

    # 5. Return enriched plan
    return await get_enriched_commercial_plan(slug)


# ==============================================================================
# Phase 2c: Controlled entitlement mutations
# ==============================================================================

async def _get_active_subscription_count(pricing_plan_id: str) -> int:
    """Count active module_subscriptions referencing a given pricing_plan_id."""
    return await module_subscriptions_collection.count_documents(
        {"pricing_plan_id": pricing_plan_id, "status": "active"}
    )


async def create_commercial_plan(
    *,
    slug: str,
    name: str,
    description: str = "",
    tagline: str = "",
    price_monthly: float = 0.0,
    price_yearly: Optional[float] = None,
    currency: str = "EUR",
    trial_days: int = 0,
    is_public: bool = True,
    is_self_serve: bool = True,
    sort_order: int = 100,
    module_plans: Optional[Dict[str, str]] = None,
    features_display: Optional[List[str]] = None,
    platform_limits: Optional[Dict[str, int]] = None,
    addon_ctas: Optional[Dict[str, str]] = None,
    performed_by: str,
    notes: Optional[str] = None,
) -> dict:
    """Create a brand-new CommercialPlan (non-addon) in the catalog.

    Onda 10 Step C.2 — admin self-serve creation.

    Validations:
      · slug: 3-60 chars [a-z0-9_], globally unique across commercial_plans
      · price_monthly >= 0
      · module_plans (if provided): every (module_key, tier_slug) must
        reference an existing PricingPlan with the same module_key
      · platform_limits (if provided): values must be int

    Stripe IDs (stripe_product_id, stripe_price_id_*) are NOT set here.
    Step C.4 adds the optional Stripe auto-create flow.

    Returns the inserted plan doc (without _id).

    Raises ValueError on validation failure or duplicate slug.
    """
    import re
    from models.common import generate_id, utc_now

    if not re.match(r"^[a-z0-9_]{3,60}$", slug):
        raise ValueError(
            f"Invalid plan slug {slug!r}: must be 3-60 chars, lowercase "
            "letters, digits and underscores only."
        )
    if not isinstance(price_monthly, (int, float)) or price_monthly < 0:
        raise ValueError("price_monthly must be a non-negative number")
    if price_yearly is not None and (not isinstance(price_yearly, (int, float)) or price_yearly < 0):
        raise ValueError("price_yearly must be a non-negative number or null")

    # Duplicate slug check
    existing = await commercial_plans_collection.find_one({"slug": slug}, {"_id": 0, "slug": 1})
    if existing:
        raise ValueError(f"Commercial plan with slug {slug!r} already exists")

    # Module plans validation: every tier slug must exist with the same module_key
    mp = module_plans or {}
    for module_key, tier_slug in mp.items():
        tier = await pricing_plans_collection.find_one(
            {"slug": tier_slug, "module_key": module_key},
            {"_id": 0, "slug": 1},
        )
        if not tier:
            raise ValueError(
                f"module_plans[{module_key!r}]={tier_slug!r}: no PricingPlan "
                f"with that slug+module_key combination exists. "
                "Create the tier first via POST /admin/catalog/entitlement-tiers."
            )

    # Validate platform_limits values
    pl = platform_limits or {}
    for k, v in pl.items():
        if not isinstance(v, int):
            raise ValueError(f"platform_limits[{k!r}] must be int, got {type(v).__name__}")

    now = utc_now()
    plan_id = generate_id()
    doc = {
        "id": plan_id,
        "slug": slug,
        "name": name,
        "description": description,
        "tagline": tagline,
        "price_monthly": float(price_monthly),
        "price_yearly": float(price_yearly) if price_yearly is not None else None,
        "currency": currency,
        "trial_days": int(trial_days),
        "is_public": bool(is_public),
        "is_self_serve": bool(is_self_serve),
        "sort_order": int(sort_order),
        # No Stripe IDs — those are added later via PATCH or Step C.4 auto-create.
        "stripe_product_id": None,
        "stripe_price_id_monthly": None,
        "stripe_price_id_yearly": None,
        "module_plans": dict(mp),
        "features_display": list(features_display or []),
        "is_addon": False,
        "addon_provides": None,
        "compatible_plans": [],
        "max_quantity": 1,
        "is_archived": False,
        "admin_modified_at": now.isoformat(),
        "platform_limits": dict(pl) if pl else None,
        "addon_ctas": dict(addon_ctas) if addon_ctas else None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await commercial_plans_collection.insert_one(doc)

    # Audit
    audit_entry = CatalogAuditEntry(
        entity_type="commercial_plan",
        entity_id=slug,
        action="create_plan",
        changes={
            "name":          {"old": None, "new": name},
            "price_monthly": {"old": None, "new": price_monthly},
            "module_plans":  {"old": None, "new": dict(mp)},
        },
        performed_by=performed_by,
        performed_at=now,
        notes=notes,
    )
    audit_doc = audit_entry.model_dump()
    audit_doc["performed_at"] = audit_doc["performed_at"].isoformat()
    await catalog_audit_log_collection.insert_one(audit_doc)

    inserted = await commercial_plans_collection.find_one({"slug": slug}, {"_id": 0})
    return inserted


async def set_plan_archive_state(
    *,
    slug: str,
    is_archived: bool,
    performed_by: str,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """Archive (soft-delete) or unarchive a CommercialPlan.

    Onda 10 Step C.6 — admin self-serve archival without redeploy.

    Effects of `is_archived = True`:
      · Plan continues to exist for orgs already subscribed (zero impact
        on running subs)
      · Excluded from `/api/billing/plans` if also is_public=False, but
        the public endpoint already filters by is_public so the archive
        flag mainly serves as an admin-side hint
      · Catalog admin endpoints continue to show it (with the flag) so
        admins can see historic plans
      · POST /admin/organizations/{id}/commercial-plan REJECTS this slug
        (Step B.3 validation excludes is_archived=True plans)

    Reversible: re-running with is_archived=False restores eligibility.

    Returns the updated plan doc, or None if slug not found.
    """
    from datetime import datetime, timezone

    existing = await commercial_plans_collection.find_one({"slug": slug}, {"_id": 0})
    if not existing:
        return None

    current = existing.get("is_archived", False)
    if current == is_archived:
        # No-op
        return {**existing, "changed": False}

    now = datetime.now(timezone.utc).isoformat()
    await commercial_plans_collection.update_one(
        {"slug": slug},
        {"$set": {
            "is_archived": is_archived,
            "admin_modified_at": now,
            "updated_at": now,
        }},
    )

    audit_entry = CatalogAuditEntry(
        entity_type="commercial_plan",
        entity_id=slug,
        action="archive_plan" if is_archived else "unarchive_plan",
        changes={"is_archived": {"old": current, "new": is_archived}},
        performed_by=performed_by,
        performed_at=datetime.now(timezone.utc),
        notes=notes,
    )
    audit_doc = audit_entry.model_dump()
    audit_doc["performed_at"] = audit_doc["performed_at"].isoformat()
    await catalog_audit_log_collection.insert_one(audit_doc)

    updated = await commercial_plans_collection.find_one({"slug": slug}, {"_id": 0})
    return {**updated, "changed": True}


async def create_addon(
    *,
    slug: str,
    name: str,
    description: str = "",
    price_monthly: float,
    addon_provides: Dict[str, Dict[str, int]],
    compatible_plans: Optional[List[str]] = None,
    max_quantity: int = 1,
    currency: str = "EUR",
    sort_order: int = 100,
    performed_by: str,
    notes: Optional[str] = None,
) -> dict:
    """Create a brand-new addon CommercialPlan (is_addon=True).

    Onda 10 Step C.3 — admin self-serve creation of addons.

    An addon is a CommercialPlan with `is_addon=True` that adds a
    Stripe subscription_item on top of the main plan, contributing
    extra quota to specific feature_keys.

    Validations:
      · slug: 3-60 chars [a-z0-9_], globally unique
      · price_monthly > 0 (addons are paid)
      · addon_provides: non-empty dict {module_key: {feature_key: int}}
      · compatible_plans: each entry must reference an existing plan
        (or be empty list = compatible with any non-free)
      · max_quantity >= 1

    Stripe IDs are NOT set here. Step C.4 adds the optional
    Stripe Product+Price auto-create flow.

    Returns the inserted addon doc.

    Raises ValueError on validation failure or duplicate slug.
    """
    import re
    from models.common import generate_id, utc_now

    if not re.match(r"^[a-z0-9_]{3,60}$", slug):
        raise ValueError(
            f"Invalid addon slug {slug!r}: must be 3-60 chars, lowercase "
            "letters, digits and underscores only."
        )
    if not isinstance(price_monthly, (int, float)) or price_monthly <= 0:
        raise ValueError("Addon price_monthly must be a positive number")
    if not isinstance(addon_provides, dict) or not addon_provides:
        raise ValueError("addon_provides must be a non-empty dict {module_key: {feature_key: int}}")
    for module_key, features in addon_provides.items():
        if not isinstance(features, dict) or not features:
            raise ValueError(
                f"addon_provides[{module_key!r}] must be a non-empty dict {{feature_key: int}}"
            )
        for k, v in features.items():
            if not isinstance(v, int):
                raise ValueError(
                    f"addon_provides[{module_key!r}][{k!r}] must be int, got {type(v).__name__}"
                )
    if max_quantity < 1:
        raise ValueError("max_quantity must be >= 1")

    # Duplicate slug check
    existing = await commercial_plans_collection.find_one({"slug": slug}, {"_id": 0, "slug": 1})
    if existing:
        raise ValueError(f"Addon (or plan) with slug {slug!r} already exists")

    # Validate compatible_plans references
    cps = list(compatible_plans or [])
    for cp_slug in cps:
        ref = await commercial_plans_collection.find_one(
            {"slug": cp_slug, "is_addon": {"$ne": True}},
            {"_id": 0, "slug": 1},
        )
        if not ref:
            raise ValueError(
                f"compatible_plans[{cp_slug!r}]: no non-addon CommercialPlan "
                f"with that slug exists. Create it first via POST /admin/catalog/plans."
            )

    now = utc_now()
    addon_id = generate_id()
    doc = {
        "id": addon_id,
        "slug": slug,
        "name": name,
        "description": description,
        "tagline": "",
        "price_monthly": float(price_monthly),
        "price_yearly": None,  # addons are monthly-only by current design
        "currency": currency,
        "trial_days": 0,
        "is_public": True,  # addons are visible to admins/users to purchase
        "is_self_serve": True,
        "sort_order": int(sort_order),
        "stripe_product_id": None,
        "stripe_price_id_monthly": None,
        "stripe_price_id_yearly": None,
        "module_plans": {},  # addons don't bundle modules
        "features_display": [],
        "is_addon": True,
        "addon_provides": dict(addon_provides),
        "compatible_plans": cps,
        "max_quantity": int(max_quantity),
        "is_archived": False,
        "admin_modified_at": now.isoformat(),
        "platform_limits": None,
        "addon_ctas": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await commercial_plans_collection.insert_one(doc)

    audit_entry = CatalogAuditEntry(
        entity_type="commercial_plan",
        entity_id=slug,
        action="create_addon",
        changes={
            "is_addon":         {"old": None, "new": True},
            "name":             {"old": None, "new": name},
            "price_monthly":    {"old": None, "new": price_monthly},
            "addon_provides":   {"old": None, "new": dict(addon_provides)},
            "compatible_plans": {"old": None, "new": cps},
            "max_quantity":     {"old": None, "new": max_quantity},
        },
        performed_by=performed_by,
        performed_at=now,
        notes=notes,
    )
    audit_doc = audit_entry.model_dump()
    audit_doc["performed_at"] = audit_doc["performed_at"].isoformat()
    await catalog_audit_log_collection.insert_one(audit_doc)

    inserted = await commercial_plans_collection.find_one({"slug": slug}, {"_id": 0})
    return inserted


async def create_entitlement_tier(
    *,
    slug: str,
    module_key: str,
    name: str,
    limits: Dict[str, int],
    sort_order: int = 100,
    performed_by: str,
    notes: Optional[str] = None,
) -> dict:
    """Create a brand-new PricingPlan tier in the catalog.

    Onda 10 Step C.1 — gives system_admin self-serve creation of new
    tiers without redeploy. The new tier is immediately referenceable
    from `commercial_plans.module_plans` (admin sets it via
    `patch_module_plans_mapping`) and from `module_access` resolution.

    Validations (raise ValueError on failure):
      · slug must be globally unique within the same module_key
      · slug shape: lowercase letters, digits, underscores only
      · limits must be a dict of str → int, non-empty

    Returns the inserted tier doc (without the Mongo _id).

    Raises ValueError on validation failure or duplicate slug.
    """
    import re
    from models.common import generate_id, utc_now

    if not re.match(r"^[a-z0-9_]{3,60}$", slug):
        raise ValueError(
            f"Invalid tier slug {slug!r}: must be 3-60 chars, lowercase "
            "letters, digits and underscores only."
        )
    if not isinstance(limits, dict) or not limits:
        raise ValueError("limits must be a non-empty dict of feature_key → int")
    for k, v in limits.items():
        if not isinstance(k, str) or not isinstance(v, int):
            raise ValueError(
                f"limits entry {k!r}={v!r} invalid: keys must be str, values must be int"
            )

    # Duplicate slug check (slug is globally unique across all modules)
    existing = await pricing_plans_collection.find_one({"slug": slug}, {"_id": 0, "slug": 1})
    if existing:
        raise ValueError(f"Tier with slug {slug!r} already exists")

    now = utc_now()
    plan_id = generate_id()
    doc = {
        "id": plan_id,
        "slug": slug,
        "module_key": module_key,
        "name": name,
        "limits": dict(limits),
        "price_monthly": 0.0,  # tiers themselves carry no price; pricing
                                # is on the CommercialPlan that bundles them
        "is_active": True,
        "sort_order": sort_order,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await pricing_plans_collection.insert_one(doc)

    # Audit
    audit_entry = CatalogAuditEntry(
        entity_type="pricing_plan",
        entity_id=slug,
        action="create_tier",
        changes={
            "module_key": {"old": None, "new": module_key},
            "limits": {"old": None, "new": dict(limits)},
            "name": {"old": None, "new": name},
        },
        performed_by=performed_by,
        performed_at=now,
        notes=notes,
    )
    audit_doc = audit_entry.model_dump()
    audit_doc["performed_at"] = audit_doc["performed_at"].isoformat()
    await catalog_audit_log_collection.insert_one(audit_doc)

    # Return enriched (drop _id)
    inserted = await pricing_plans_collection.find_one({"slug": slug}, {"_id": 0})
    return inserted


async def patch_entitlement_tier_limits(
    slug: str,
    new_limits: Dict[str, int],
    performed_by: str,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """Update limits on a PricingPlan and record an audit entry.

    This is a controlled mutation: limits changes affect runtime enforcement
    immediately for all orgs subscribed to this tier via module_access.py.

    If no effective change (limits identical), no write and no audit entry.

    Returns dict with:
      - ``tier``: the updated PricingPlan (without vestigial price fields)
      - ``impact_count``: number of active module_subscriptions using this tier
    Or None if slug not found.
    """
    # 1. Load existing pricing plan by slug
    existing = await pricing_plans_collection.find_one(
        {"slug": slug},
        {"_id": 0},
    )
    if not existing:
        return None

    plan_id = existing.get("id")
    current_limits = existing.get("limits", {})

    # 2. Compute impact count
    impact_count = await _get_active_subscription_count(plan_id) if plan_id else 0

    # 3. Compute diff
    if current_limits == new_limits:
        # No effective changes — return current state, no audit
        tier = {k: v for k, v in existing.items()
                if k not in ("price_monthly", "price_yearly")}
        return {"tier": tier, "impact_count": impact_count, "changed": False}

    # 4. Update limits + updated_at in MongoDB
    now = datetime.now(timezone.utc)
    await pricing_plans_collection.update_one(
        {"slug": slug},
        {"$set": {
            "limits": new_limits,
            "updated_at": now.isoformat(),
        }},
    )

    # 5. Write audit entry
    changes = {"limits": {"old": current_limits, "new": new_limits}}
    audit_entry = CatalogAuditEntry(
        entity_type="pricing_plan",
        entity_id=slug,
        action="update_limits",
        changes=changes,
        performed_by=performed_by,
        performed_at=now,
        notes=notes,
    )
    audit_doc = audit_entry.model_dump()
    audit_doc["performed_at"] = audit_doc["performed_at"].isoformat()
    await catalog_audit_log_collection.insert_one(audit_doc)

    # 6. Return updated tier
    updated = await pricing_plans_collection.find_one(
        {"slug": slug},
        {"_id": 0, "price_monthly": 0, "price_yearly": 0},
    )
    return {"tier": updated, "impact_count": impact_count, "changed": True}


# ==============================================================================
# Phase 2d: Controlled commercial bundle mutations
# ==============================================================================

async def validate_module_plans_mapping(
    module_plans: Dict[str, str],
) -> Optional[str]:
    """Validate that every entry in module_plans points to a valid PricingPlan.

    For each (module_key, pricing_plan_slug) pair, checks:
      1. The PricingPlan exists
      2. Its module_key matches the key it's mapped under

    Returns None if valid, or an error message string if invalid.
    """
    for module_key, plan_slug in module_plans.items():
        plan = await pricing_plans_collection.find_one(
            {"slug": plan_slug},
            {"_id": 0, "module_key": 1, "slug": 1},
        )
        if not plan:
            return (
                f"PricingPlan '{plan_slug}' not found. "
                f"Cannot map module '{module_key}' to a non-existent tier."
            )
        if plan.get("module_key") != module_key:
            return (
                f"PricingPlan '{plan_slug}' belongs to module '{plan.get('module_key')}', "
                f"but was mapped under module '{module_key}'. "
                f"Each tier must belong to the module it is mapped under."
            )
    return None


async def patch_module_plans(
    slug: str,
    new_module_plans: Dict[str, str],
    performed_by: str,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """Update module_plans on a CommercialPlan and record an audit entry.

    This is a catalog-only mutation: it changes the plan definition for
    future provisioning.  Already provisioned organizations are NOT
    automatically reprovisioned.

    Caller must validate the mapping BEFORE calling this function
    (use ``validate_module_plans_mapping``).

    If no effective change (module_plans identical), no write, no audit.

    Returns dict with:
      - ``plan``: the enriched CommercialPlan after update
      - ``subscriber_count``: orgs currently on this plan
      - ``changed``: whether any mutation occurred
      - ``auto_reprovisioned``: always False in this phase
    Or None if slug not found.
    """
    # 1. Load existing plan
    existing = await commercial_plans_collection.find_one(
        {"slug": slug}, {"_id": 0}
    )
    if not existing:
        return None

    current_module_plans = existing.get("module_plans", {})
    subscriber_count = await _get_subscriber_count(slug)

    # 2. Compute diff
    if current_module_plans == new_module_plans:
        enriched = await get_enriched_commercial_plan(slug)
        return {
            "plan": enriched,
            "subscriber_count": subscriber_count,
            "changed": False,
            "auto_reprovisioned": False,
        }

    # 3. Update module_plans + timestamps in MongoDB
    now = datetime.now(timezone.utc)
    await commercial_plans_collection.update_one(
        {"slug": slug},
        {"$set": {
            "module_plans": new_module_plans,
            "admin_modified_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }},
    )

    # 4. Write audit entry
    changes = {"module_plans": {"old": current_module_plans, "new": new_module_plans}}
    audit_entry = CatalogAuditEntry(
        entity_type="commercial_plan",
        entity_id=slug,
        action="update_module_plans",
        changes=changes,
        performed_by=performed_by,
        performed_at=now,
        notes=notes,
    )
    audit_doc = audit_entry.model_dump()
    audit_doc["performed_at"] = audit_doc["performed_at"].isoformat()
    await catalog_audit_log_collection.insert_one(audit_doc)

    # 5. Return enriched plan
    enriched = await get_enriched_commercial_plan(slug)
    return {
        "plan": enriched,
        "subscriber_count": subscriber_count,
        "changed": True,
        "auto_reprovisioned": False,
    }


# ==============================================================================
# Phase 2e: Controlled pricing mutations
# ==============================================================================

async def patch_pricing(
    slug: str,
    pricing_fields: Dict[str, Any],
    performed_by: str,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """Update pricing fields on a CommercialPlan and record an audit entry.

    This is a catalog-only mutation affecting future checkout behavior.
    Existing subscribers are not migrated — their Stripe subscriptions
    reference the specific Stripe Price ID at subscription creation time.

    Caller must validate pricing coherence (paired fields) BEFORE calling.

    If no effective change, no write and no audit entry.

    Returns dict with:
      - ``plan``: the enriched CommercialPlan after update
      - ``subscriber_count``: orgs currently on this plan
      - ``changed``: whether any mutation occurred
      - ``affects_future_checkouts``: always True when changed
      - ``migrated_existing_subscribers``: always False in this phase
    Or None if slug not found.
    """
    # 1. Load existing plan
    existing = await commercial_plans_collection.find_one(
        {"slug": slug}, {"_id": 0}
    )
    if not existing:
        return None

    subscriber_count = await _get_subscriber_count(slug)

    # 2. Compute diff — only fields that actually changed
    changes: Dict[str, Dict[str, Any]] = {}
    for field, new_value in pricing_fields.items():
        old_value = existing.get(field)
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}

    if not changes:
        enriched = await get_enriched_commercial_plan(slug)
        return {
            "plan": enriched,
            "subscriber_count": subscriber_count,
            "changed": False,
            "affects_future_checkouts": False,
            "migrated_existing_subscribers": False,
        }

    # 3. Update pricing fields + timestamps
    now = datetime.now(timezone.utc)
    update_set = {field: diff["new"] for field, diff in changes.items()}
    update_set["admin_modified_at"] = now.isoformat()
    update_set["updated_at"] = now.isoformat()

    await commercial_plans_collection.update_one(
        {"slug": slug},
        {"$set": update_set},
    )

    # 4. Write audit entry
    audit_entry = CatalogAuditEntry(
        entity_type="commercial_plan",
        entity_id=slug,
        action="update_pricing",
        changes=changes,
        performed_by=performed_by,
        performed_at=now,
        notes=notes,
    )
    audit_doc = audit_entry.model_dump()
    audit_doc["performed_at"] = audit_doc["performed_at"].isoformat()
    await catalog_audit_log_collection.insert_one(audit_doc)

    # 5. Return enriched plan
    enriched = await get_enriched_commercial_plan(slug)
    return {
        "plan": enriched,
        "subscriber_count": subscriber_count,
        "changed": True,
        "affects_future_checkouts": True,
        "migrated_existing_subscribers": False,
    }


# ==============================================================================
# Phase 3A: Organization Commercial State (read-only diagnostic)
# ==============================================================================

_BILLING_RESTRICTED_STATES = frozenset({"past_due", "canceled"})


async def build_org_commercial_state(org_id: str) -> Optional[dict]:
    """Build a full commercial-state diagnostic for one organization.

    Returns None if the organization does not exist.

    This is a pure read operation — no writes, no side effects.
    It assembles data from organizations, commercial_plans,
    module_subscriptions, and pricing_plans to compute drift flags.
    """
    # ── 1. Load organization ─────────────────────────────────────────────
    org = await organizations_collection.find_one(
        {"id": org_id},
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "commercial_plan_slug": 1,
            "billing_status": 1,
            "plan_assigned_by": 1,
            "plan": 1,  # legacy field
            "created_at": 1,
        },
    )
    if not org:
        return None

    plan_slug = org.get("commercial_plan_slug", "free")
    billing_status = org.get("billing_status", "none")
    plan_assigned_by = org.get("plan_assigned_by", "system")

    # ── 2. Load catalog plan ─────────────────────────────────────────────
    catalog_plan = await commercial_plans_collection.find_one(
        {"slug": plan_slug}, {"_id": 0}
    )
    catalog_plan_missing = catalog_plan is None
    catalog_module_plans = catalog_plan.get("module_plans", {}) if catalog_plan else {}

    # ── 3. Load provisioned module subscriptions ─────────────────────────
    sub_cursor = module_subscriptions_collection.find(
        {"organization_id": org_id, "status": "active"},
        {"_id": 0},
    )
    active_subs = await sub_cursor.to_list(50)

    # Resolve PricingPlan for each subscription
    provisioned_modules = []
    provisioned_by_module: Dict[str, dict] = {}

    for sub in active_subs:
        module_key = sub.get("module_key", "unknown")
        pp_id = sub.get("pricing_plan_id")

        # Resolve PricingPlan
        pp = None
        if pp_id:
            pp = await pricing_plans_collection.find_one(
                {"id": pp_id}, {"_id": 0, "slug": 1, "limits": 1, "module_key": 1}
            )

        entry = {
            "module_key": module_key,
            "status": sub.get("status"),
            "pricing_plan_id": pp_id,
            "pricing_plan_slug": pp.get("slug") if pp else None,
            "limits": pp.get("limits", {}) if pp else {},
            "assigned_by": sub.get("assigned_by"),
            "cancelled_at": sub.get("cancelled_at"),
            "commercial_plan_slug": sub.get("commercial_plan_slug"),
        }
        provisioned_modules.append(entry)
        provisioned_by_module[module_key] = entry

    # ── 4. Compute drift flags ───────────────────────────────────────────
    provisioned_keys = set(provisioned_by_module.keys())
    catalog_keys = set(catalog_module_plans.keys())

    # A. catalog_plan_missing
    flag_catalog_plan_missing = catalog_plan_missing

    # B. missing_module_subscriptions
    missing_modules = catalog_keys - provisioned_keys if not catalog_plan_missing else set()
    flag_missing_module_subs = len(missing_modules) > 0

    # C. unexpected_module_subscriptions
    unexpected_modules = provisioned_keys - catalog_keys if not catalog_plan_missing else set()
    flag_unexpected_module_subs = len(unexpected_modules) > 0

    # D. module_plan_mismatch
    flag_module_plan_mismatch = False
    mismatched_modules = []
    if not catalog_plan_missing:
        for mk, expected_slug in catalog_module_plans.items():
            prov = provisioned_by_module.get(mk)
            if prov and prov.get("pricing_plan_slug") != expected_slug:
                flag_module_plan_mismatch = True
                mismatched_modules.append(mk)

    # E. limits_mismatch
    flag_limits_mismatch = False
    if not catalog_plan_missing:
        for mk, expected_slug in catalog_module_plans.items():
            prov = provisioned_by_module.get(mk)
            if not prov:
                continue
            # Load the catalog-expected PricingPlan limits
            expected_pp = await pricing_plans_collection.find_one(
                {"slug": expected_slug, "is_active": True},
                {"_id": 0, "limits": 1},
            )
            if expected_pp and prov.get("limits") != expected_pp.get("limits", {}):
                flag_limits_mismatch = True
                break

    # F. manual_assignment_detected
    flag_manual = plan_assigned_by in ("admin", "manual") or billing_status == "manual"
    if not flag_manual:
        for sub in active_subs:
            ab = sub.get("assigned_by", "")
            if ab and (ab.startswith("admin:") or ab == "manual"):
                flag_manual = True
                break

    # G. billing_restricted
    flag_billing_restricted = billing_status in _BILLING_RESTRICTED_STATES

    # H. legacy_plan_fallback_risk
    legacy_plan = org.get("plan")
    has_provisioned = len(active_subs) > 0
    flag_legacy_fallback = (
        not has_provisioned
        and legacy_plan is not None
        and legacy_plan != "free"
    )

    # ── 5. Summary ───────────────────────────────────────────────────────
    any_drift = (
        flag_catalog_plan_missing
        or flag_missing_module_subs
        or flag_unexpected_module_subs
        or flag_module_plan_mismatch
        or flag_limits_mismatch
    )

    recommended_actions = []
    if flag_catalog_plan_missing:
        recommended_actions.append("review_missing_catalog_plan")
    if flag_missing_module_subs:
        recommended_actions.append("consider_reprovision")
    if flag_unexpected_module_subs:
        recommended_actions.append("review_unexpected_subscriptions")
    if flag_module_plan_mismatch:
        recommended_actions.append("consider_reprovision")
    if flag_limits_mismatch and not flag_module_plan_mismatch:
        recommended_actions.append("review_limits_drift")
    if flag_manual:
        recommended_actions.append("review_manual_assignment")
    if flag_billing_restricted:
        recommended_actions.append("review_billing_status")
    if flag_legacy_fallback:
        recommended_actions.append("investigate_legacy_plan_fallback")

    # Deduplicate while preserving order
    seen = set()
    unique_actions = []
    for a in recommended_actions:
        if a not in seen:
            seen.add(a)
            unique_actions.append(a)

    # ── 6. Assemble response ─────────────────────────────────────────────
    catalog_plan_section = None
    if catalog_plan:
        catalog_plan_section = {
            "slug": catalog_plan.get("slug"),
            "name": catalog_plan.get("name"),
            "trial_days": catalog_plan.get("trial_days"),
            "is_public": catalog_plan.get("is_public"),
            "is_self_serve": catalog_plan.get("is_self_serve"),
            "module_plans": catalog_plan.get("module_plans", {}),
            "price_monthly": catalog_plan.get("price_monthly"),
            "price_yearly": catalog_plan.get("price_yearly"),
        }

    return {
        "organization": {
            "id": org.get("id"),
            "name": org.get("name"),
            "commercial_plan_slug": plan_slug,
            "billing_status": billing_status,
            "plan_assigned_by": plan_assigned_by,
            "created_at": org.get("created_at"),
        },
        "catalog_plan": catalog_plan_section,
        "provisioned_modules": provisioned_modules,
        "drift_flags": {
            "catalog_plan_missing": flag_catalog_plan_missing,
            "missing_module_subscriptions": flag_missing_module_subs,
            "unexpected_module_subscriptions": flag_unexpected_module_subs,
            "module_plan_mismatch": flag_module_plan_mismatch,
            "limits_mismatch": flag_limits_mismatch,
            "manual_assignment_detected": flag_manual,
            "billing_restricted": flag_billing_restricted,
            "legacy_plan_fallback_risk": flag_legacy_fallback,
        },
        "summary": {
            "is_out_of_sync": any_drift,
            "recommended_actions": unique_actions,
            "mismatched_modules": mismatched_modules if mismatched_modules else None,
            "missing_modules": list(missing_modules) if missing_modules else None,
            "unexpected_modules": list(unexpected_modules) if unexpected_modules else None,
        },
    }


# ==============================================================================
# Phase 3D: Batch commercial overview (lightweight)
# ==============================================================================

async def list_org_commercial_summaries(
    skip: int = 0,
    limit: int = 100,
) -> List[dict]:
    """Build lightweight commercial summaries for all organizations.

    Returns a list of per-org summaries with drift flags and sync status,
    suitable for a System Admin overview list.

    This is a batch-optimized version that avoids N+1 queries by:
      1. Loading all orgs in one query
      2. Loading all catalog plans once
      3. Loading all active subscriptions grouped by org
      4. Loading referenced pricing plans in batch
      5. Computing drift flags per org
    """
    # 1. Load all orgs (le org campione del prelaunch non sono
    #    operatori: fuori dalla salute commerciale)
    org_cursor = organizations_collection.find(
        {"is_sample": {"$ne": True}},
        {
            "_id": 0, "id": 1, "name": 1, "commercial_plan_slug": 1,
            "billing_status": 1, "plan_assigned_by": 1, "plan": 1,
        },
    ).skip(skip).limit(limit)
    orgs = await org_cursor.to_list(limit)

    if not orgs:
        return []

    # 2. Load all catalog plans (small collection, ~4 docs)
    plan_cursor = commercial_plans_collection.find({}, {"_id": 0})
    all_plans = await plan_cursor.to_list(50)
    plans_by_slug = {p["slug"]: p for p in all_plans}

    # 3. Load all active subscriptions for these orgs
    org_ids = [o["id"] for o in orgs]
    sub_cursor = module_subscriptions_collection.find(
        {"organization_id": {"$in": org_ids}, "status": "active"},
        {"_id": 0, "organization_id": 1, "module_key": 1, "pricing_plan_id": 1,
         "assigned_by": 1},
    )
    all_subs = await sub_cursor.to_list(500)

    # Group subs by org
    subs_by_org: Dict[str, List[dict]] = {}
    for s in all_subs:
        subs_by_org.setdefault(s["organization_id"], []).append(s)

    # 4. Batch-load referenced pricing plans
    pp_ids = list({s["pricing_plan_id"] for s in all_subs if s.get("pricing_plan_id")})
    pp_cursor = pricing_plans_collection.find(
        {"id": {"$in": pp_ids}},
        {"_id": 0, "id": 1, "slug": 1, "limits": 1},
    )
    all_pps = await pp_cursor.to_list(200)
    pps_by_id = {p["id"]: p for p in all_pps}

    # 5. Compute per-org summaries
    summaries = []
    for org in orgs:
        org_id = org["id"]
        plan_slug = org.get("commercial_plan_slug", "free")
        billing_status = org.get("billing_status", "none")
        plan_assigned_by = org.get("plan_assigned_by", "system")

        catalog_plan = plans_by_slug.get(plan_slug)
        catalog_plan_missing = catalog_plan is None
        catalog_module_plans = catalog_plan.get("module_plans", {}) if catalog_plan else {}

        org_subs = subs_by_org.get(org_id, [])
        provisioned_keys = {s["module_key"] for s in org_subs}
        catalog_keys = set(catalog_module_plans.keys())

        # Drift flags (lightweight computation)
        flag_missing_subs = bool(catalog_keys - provisioned_keys) if not catalog_plan_missing else False
        flag_unexpected_subs = bool(provisioned_keys - catalog_keys) if not catalog_plan_missing else False

        flag_plan_mismatch = False
        if not catalog_plan_missing:
            for s in org_subs:
                mk = s["module_key"]
                expected_slug = catalog_module_plans.get(mk)
                if expected_slug:
                    pp = pps_by_id.get(s.get("pricing_plan_id"))
                    if pp and pp.get("slug") != expected_slug:
                        flag_plan_mismatch = True
                        break

        flag_manual = (
            plan_assigned_by in ("admin", "manual")
            or billing_status == "manual"
            or any(
                (s.get("assigned_by", "").startswith("admin:") or s.get("assigned_by") == "manual")
                for s in org_subs
            )
        )

        flag_billing_restricted = billing_status in _BILLING_RESTRICTED_STATES

        legacy_plan = org.get("plan")
        flag_legacy_fallback = (
            len(org_subs) == 0
            and legacy_plan is not None
            and legacy_plan != "free"
        )

        is_out_of_sync = (
            catalog_plan_missing
            or flag_missing_subs
            or flag_unexpected_subs
            or flag_plan_mismatch
        )

        has_warnings = flag_manual or flag_billing_restricted or flag_legacy_fallback

        # Recommended action (compact — first applicable)
        recommended_action = None
        if catalog_plan_missing:
            recommended_action = "review_missing_catalog_plan"
        elif flag_missing_subs or flag_plan_mismatch:
            recommended_action = "consider_reprovision"
        elif flag_unexpected_subs:
            recommended_action = "review_unexpected_subscriptions"
        elif flag_billing_restricted:
            recommended_action = "review_billing_status"
        elif flag_manual:
            recommended_action = "review_manual_assignment"
        elif flag_legacy_fallback:
            recommended_action = "investigate_legacy_plan_fallback"

        summaries.append({
            "id": org_id,
            "name": org.get("name"),
            "commercial_plan_slug": plan_slug,
            "billing_status": billing_status,
            "plan_assigned_by": plan_assigned_by,
            "is_out_of_sync": is_out_of_sync,
            "has_warnings": has_warnings,
            "drift_flags": {
                "catalog_plan_missing": catalog_plan_missing,
                "missing_module_subscriptions": flag_missing_subs,
                "unexpected_module_subscriptions": flag_unexpected_subs,
                "module_plan_mismatch": flag_plan_mismatch,
                "manual_assignment_detected": flag_manual,
                "billing_restricted": flag_billing_restricted,
                "legacy_plan_fallback_risk": flag_legacy_fallback,
            },
            "recommended_action": recommended_action,
        })

    return summaries


# ==============================================================================
# Phase 3B: Controlled reprovision
# ==============================================================================

async def _snapshot_provisioned_modules(org_id: str) -> List[dict]:
    """Capture a lightweight snapshot of active module subscriptions."""
    cursor = module_subscriptions_collection.find(
        {"organization_id": org_id, "status": "active"},
        {"_id": 0},
    )
    subs = await cursor.to_list(50)

    snapshot = []
    for sub in subs:
        pp_id = sub.get("pricing_plan_id")
        pp = None
        if pp_id:
            pp = await pricing_plans_collection.find_one(
                {"id": pp_id}, {"_id": 0, "slug": 1}
            )
        snapshot.append({
            "module_key": sub.get("module_key"),
            "pricing_plan_slug": pp.get("slug") if pp else None,
            "assigned_by": sub.get("assigned_by"),
        })
    return snapshot


async def reprovision_org_to_catalog(
    org_id: str,
    performed_by: str,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """Reprovision an org to its current catalog plan definition.

    Uses the canonical ``provision_commercial_plan`` path.
    Does NOT change which plan the org is on — only re-aligns
    module subscriptions to the current catalog definition.

    Returns None if org not found.
    Raises ValueError if org has no valid commercial_plan_slug or
    the catalog plan doesn't exist.

    Audit: writes one CatalogAuditEntry on successful reprovision.
    If reprovision produces no effective change (before == after),
    the audit is still recorded with ``changed: false`` to track
    the admin's explicit action.
    """
    # 1. Load org
    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "id": 1, "name": 1, "commercial_plan_slug": 1, "billing_status": 1,
         "stripe_subscription_id": 1},
    )
    if not org:
        return None

    plan_slug = org.get("commercial_plan_slug")
    if not plan_slug:
        raise ValueError("Organization has no commercial_plan_slug assigned")

    # 2. Verify catalog plan exists
    catalog_plan = await commercial_plans_collection.find_one(
        {"slug": plan_slug}, {"_id": 0, "slug": 1}
    )
    if not catalog_plan:
        raise ValueError(
            f"Catalog plan '{plan_slug}' not found. "
            f"Cannot reprovision to a non-existent plan."
        )

    # 3. Capture before snapshot
    before_snapshot = await _snapshot_provisioned_modules(org_id)

    # 4. Call canonical provisioning
    from services.plan_provisioning import provision_commercial_plan

    # Preserve existing billing_status — reprovision should NOT change billing state
    current_billing_status = org.get("billing_status", "none")

    # Preserve existing stripe_subscription_id so recreated module subs
    # maintain Stripe linkage (used by cancellation, reconcile, diagnostics).
    existing_stripe_sub_id = org.get("stripe_subscription_id")

    await provision_commercial_plan(
        org_id=org_id,
        plan_slug=plan_slug,
        assigned_by=f"reprovision:admin:{performed_by}",
        billing_status=current_billing_status,
        stripe_subscription_id=existing_stripe_sub_id,
        notes=notes or f"Reprovisioned to catalog definition by {performed_by}",
    )

    # 5. Capture after snapshot
    after_snapshot = await _snapshot_provisioned_modules(org_id)

    # 6. Determine if anything changed
    before_set = {(m["module_key"], m["pricing_plan_slug"]) for m in before_snapshot}
    after_set = {(m["module_key"], m["pricing_plan_slug"]) for m in after_snapshot}
    changed = before_set != after_set

    # 7. Write audit entry (always, even on no-op — tracks explicit admin action)
    now = datetime.now(timezone.utc)
    audit_entry = CatalogAuditEntry(
        entity_type="organization",
        entity_id=org_id,
        action="reprovision_commercial_plan",
        changes={
            "before": [{"module_key": m["module_key"], "pricing_plan_slug": m["pricing_plan_slug"]} for m in before_snapshot],
            "after": [{"module_key": m["module_key"], "pricing_plan_slug": m["pricing_plan_slug"]} for m in after_snapshot],
        },
        performed_by=performed_by,
        performed_at=now,
        notes=notes,
    )
    audit_doc = audit_entry.model_dump()
    audit_doc["performed_at"] = audit_doc["performed_at"].isoformat()
    await catalog_audit_log_collection.insert_one(audit_doc)

    # 8. Return result
    return {
        "organization": {
            "id": org.get("id"),
            "name": org.get("name"),
            "commercial_plan_slug": plan_slug,
        },
        "before": before_snapshot,
        "after": after_snapshot,
        "result": {
            "changed": changed,
            "reprovisioned_to_plan": plan_slug,
            "notes": notes,
        },
    }
