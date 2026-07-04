import logging
from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Co-activation / Co-deactivation rules ────────────────────────────────────
# Declarative map: when module X is activated, also activate modules in list Y.
# Wave 7A (2026-05): commerce_signals removed from the platform — its
# cascade entries are no longer present here.

CO_ACTIVATE = {
    "commerce": ["product_catalog", "customers_light"],
}

CO_DEACTIVATE = {
    "commerce": ["product_catalog"],
}
from models import ModuleMetadata, OrganizationModule, AuditLog
from auth import get_current_user, get_verified_user, require_admin
from repositories import module_repository, audit_repository, organization_repository
from services.module_access import can_use_module
from core.module_registry import get_all_for_ui as _registered_modules_for_ui
from datetime import datetime, timezone

router = APIRouter(prefix="/modules", tags=["Modules"])

# Static modules for future features (not yet implemented as full modules)
FUTURE_MODULES = [
    {
        "key": "revenue_forecasting",
        "name": "Revenue Forecasting",
        "description": "AI-powered revenue predictions based on historical data and market trends.",
        "category": "Financial",
        "icon": "LineChart",
        "is_available": False
    },
    {
        "key": "expense_optimizer",
        "name": "Expense Optimizer", 
        "description": "Identify cost-saving opportunities and optimize spending patterns.",
        "category": "Financial",
        "icon": "PiggyBank",
        "is_available": False
    },
    {
        "key": "inventory_tracker",
        "name": "Inventory Tracker",
        "description": "Monitor stock levels, predict shortages, and optimize reordering.",
        "category": "Operations",
        "icon": "Package",
        "is_available": False
    },
]


def get_all_modules() -> List[dict]:
    """Get all modules (from registry + future modules).

    Reads from ``core.module_registry`` (the explicit-registration source
    of truth, populated at import time via each module's ``__init__.py``).
    Falls back through ``FUTURE_MODULES`` for placeholder modules that
    have no Python implementation yet.
    """
    all_modules = list(_registered_modules_for_ui())
    all_modules.extend(FUTURE_MODULES)
    return all_modules


@router.get("/available")
async def list_available_modules():
    """List all available modules in the platform"""
    return get_all_modules()


@router.get("/active")
async def list_active_modules(current_user: dict = Depends(get_verified_user)):
    """List modules activated by the organization"""
    org_modules = await module_repository.find_by_org(current_user['organization_id'])
    
    all_modules = get_all_modules()
    module_map = {m['key']: m for m in all_modules}
    
    result = []
    for om in org_modules:
        module_meta = module_map.get(om['module_key'])
        if module_meta:
            activated_at = om['activated_at']
            if isinstance(activated_at, str):
                activated_at = datetime.fromisoformat(activated_at)
            
            result.append({
                "id": om['id'],
                "module_key": om['module_key'],
                "name": module_meta['name'],
                "description": module_meta['description'],
                "category": module_meta['category'],
                "icon": module_meta['icon'],
                "activated_at": activated_at.isoformat(),
                "is_active": om['is_active']
            })
    
    return result


@router.post("/{module_key}/activate")
async def activate_module(
    module_key: str,
    current_user: dict = Depends(require_admin)
):
    """Activate a module for the organization"""
    all_modules = get_all_modules()
    module = next((m for m in all_modules if m['key'] == module_key), None)
    
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )
    
    if not module['is_available']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Module is not yet available"
        )
    
    existing = await module_repository.find_by_key(
        current_user['organization_id'],
        module_key
    )
    
    if existing:
        if existing.get('is_active'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Module is already activated"
            )
        await module_repository.activate(current_user['organization_id'], module_key)
    else:
        org_module = OrganizationModule(
            organization_id=current_user['organization_id'],
            module_key=module_key,
            activated_by=current_user['user_id']
        )
        await module_repository.create(org_module)

        audit = AuditLog(
            organization_id=current_user['organization_id'],
            user_id=current_user['user_id'],
            action="activate_module",
            resource_type="module",
            resource_id=module_key
        )
        await audit_repository.create(audit)

    # Co-activation: cascade through dependency rules (runs for both new and reactivated)
    org_id = current_user['organization_id']
    user_id = current_user['user_id']
    co_activated = []
    for dep_key in CO_ACTIVATE.get(module_key, []):
        try:
            dep_existing = await module_repository.find_by_key(org_id, dep_key)
            if not dep_existing:
                dep_module = OrganizationModule(
                    organization_id=org_id,
                    module_key=dep_key,
                    activated_by=user_id,
                )
                await module_repository.create(dep_module)
                co_activated.append(dep_key)
            elif not dep_existing.get('is_active'):
                await module_repository.activate(org_id, dep_key)
                co_activated.append(dep_key)
            # Cascade: check if the dep itself has co-activations
            for sub_dep in CO_ACTIVATE.get(dep_key, []):
                sub_existing = await module_repository.find_by_key(org_id, sub_dep)
                if not sub_existing:
                    await module_repository.create(OrganizationModule(
                        organization_id=org_id, module_key=sub_dep, activated_by=user_id))
                    co_activated.append(sub_dep)
                elif not sub_existing.get('is_active'):
                    await module_repository.activate(org_id, sub_dep)
                    co_activated.append(sub_dep)
        except Exception as e:
            logger.warning("modules: co-activation of %s failed: %s", dep_key, e)

    if co_activated:
        logger.info("modules: co-activated %s with %s for org=%s", co_activated, module_key, org_id)

    return {"message": f"Module {module['name']} activated successfully", "co_activated": co_activated}


@router.post("/{module_key}/deactivate")
async def deactivate_module(
    module_key: str,
    current_user: dict = Depends(require_admin)
):
    """Deactivate a module for the organization"""
    existing = await module_repository.find_by_key(
        current_user['organization_id'],
        module_key
    )
    
    if not existing or not existing.get('is_active'):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active module not found"
        )
    
    org_id = current_user['organization_id']
    await module_repository.deactivate(org_id, module_key)

    # Co-deactivation: cascade through dependency rules
    co_deactivated = []
    for dep_key in CO_DEACTIVATE.get(module_key, []):
        try:
            await module_repository.deactivate(org_id, dep_key)
            co_deactivated.append(dep_key)
            # Cascade sub-deps
            for sub_dep in CO_DEACTIVATE.get(dep_key, []):
                await module_repository.deactivate(org_id, sub_dep)
                co_deactivated.append(sub_dep)
        except Exception:
            pass
    if co_deactivated:
        logger.info("modules: co-deactivated %s with %s for org=%s", co_deactivated, module_key, org_id)

    audit = AuditLog(
        organization_id=current_user['organization_id'],
        user_id=current_user['user_id'],
        action="deactivate_module",
        resource_type="module",
        resource_id=module_key,
    )
    await audit_repository.create(audit)

    return {"message": "Module deactivated successfully"}


@router.get("/{module_key}/status")
async def get_module_status(
    module_key: str,
    current_user: dict = Depends(get_verified_user)
):
    """Check if a module is activated for the organization"""
    all_modules = get_all_modules()
    module = next((m for m in all_modules if m['key'] == module_key), None)
    
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )
    
    org_module = await module_repository.find_by_key(
        current_user['organization_id'],
        module_key
    )
    
    return {
        "module_key": module_key,
        "name": module['name'],
        "is_available": module['is_available'],
        "is_activated": bool(org_module and org_module.get('is_active')),
        "activated_at": org_module.get('activated_at') if org_module else None
    }


@router.get("/{module_key}/overview")
async def get_module_overview(
    module_key: str,
    period: str = Query("30d", description="Period label: 7d, 30d, 90d, or custom"),
    start_date: Optional[str] = Query(None, description="ISO date string, required when period=custom"),
    end_date: Optional[str] = Query(None, description="ISO date string, required when period=custom"),
    current_user: dict = Depends(get_verified_user),
):
    """Return a composite overview for the given module and period.

    Dispatches to the overview_builder registered for the module in
    core.module_registry.  Runs all data queries in parallel and returns
    KPIs, chart series, categories, open alerts, and the last AI insight
    in a single response.

    Returns 404 when the module is not registered, does not support the
    overview capability, or has no data for the requested period.
    """
    from core.module_registry import get as registry_get

    module = registry_get(module_key)
    if module is None or module.overview_builder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_key}' not found or does not support overview",
        )

    org_id = current_user["organization_id"]
    locale = current_user.get("locale", "it")
    overview = await module.overview_builder(org_id, period, start_date, end_date, locale=locale)

    if overview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data available for module '{module_key}'",
        )

    return overview


@router.post("/{module_key}/health-explanation-ai")
async def get_health_explanation_ai(
    module_key: str,
    period: str = Query("30d"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(get_verified_user),
):
    """On-demand AI explanation for the health score (single Claude call).

    The default overview uses a rule-based explanation (zero cost).
    This endpoint generates a richer AI-powered explanation when the user
    explicitly requests it.
    """
    from core.module_registry import get as registry_get

    module = registry_get(module_key)
    if module is None or module.overview_builder is None:
        raise HTTPException(status_code=404, detail="Module not found")

    org_id = current_user["organization_id"]

    # Wave 9.B.3 + Wave 10.A.6 — per-user rate limit (10 calls / minute).
    #
    # Spam-click protection: a user on AI Business / Enterprise has
    # ``health_explanation`` as an unlimited access flag (no quota
    # counter), so without this guard repeated clicks could hit
    # Anthropic at the rate of frontend clicks — easily $1+ in a few
    # seconds.
    #
    # Wave 10.A.6: replaced the pre-increment count_documents + later
    # record_usage pattern (TOCTOU — 50 concurrent clicks could all see
    # count<10 and proceed before any of them wrote) with an atomic
    # findOneAndUpdate counter via services.rate_limit. The counter is
    # incremented BEFORE the AI call; the post-increment value is
    # compared to the limit. Race-free.
    _user_id = current_user.get("user_id") or current_user.get("id") or ""
    if _user_id:
        from services.rate_limit import acquire as _rl_acquire, RateLimitExceeded
        try:
            await _rl_acquire(
                key=f"health_explanation:{org_id}:{_user_id}",
                limit=10,
                window_seconds=60,
            )
        except RateLimitExceeded as rl_exc:
            raise HTTPException(
                status_code=429,
                detail={
                    "error_code": "rate_limit_exceeded",
                    "message": "Too many AI explanation requests. Please wait a minute and retry.",
                    "scope": "user_per_minute",
                    "limit": rl_exc.limit,
                    "current_count": rl_exc.count,
                },
            )

    overview = await module.overview_builder(org_id, period, start_date, end_date)
    if overview is None:
        raise HTTPException(status_code=404, detail="No data")

    health_score = overview.get("health_score", {})
    kpis = overview.get("kpis", {})

    # ── Soft gate: use AI if module supports it and org has entitlement ───────
    # Wave 9.C.3 — surface the entitlement status to the frontend.
    # The previous response was just {"source": "rule-based"} for both the
    # "AI failed" and the "no entitlement" cases — indistinguishable on
    # the UI side. Now we send `entitlement_status` so the frontend can
    # show an upsell tooltip ("AI explanations require Starter plan or
    # higher") instead of a generic message.
    org_doc = await organization_repository.find_by_id(org_id) if module.health_explanation_ai is not None else None
    has_entitlement = (
        module.health_explanation_ai is not None
        and org_doc
        and await can_use_module(org_doc, "ai_assistant", "health_explanation")
    )

    if has_entitlement:
        # Build period label for AI context
        ov_period = overview.get("period", {})
        period_label = f"{ov_period.get('start_date', '')} — {ov_period.get('end_date', '')} ({ov_period.get('days', '')} giorni)"

        # Wave 8A.0 — pass org_id + user_id so the helper writes an
        # AIUsageEvent with full attribution.
        explanation = await module.health_explanation_ai(
            health_score,
            kpis={
                "net_after_fixed": kpis.get("net_after_fixed", 0),
                "operating_margin_pct": kpis.get("operating_margin_pct", 0),
                "giorni_autonomia": kpis.get("giorni_autonomia", 0),
                "dso": kpis.get("dso", 0),
                "total_outflow_ratio": kpis.get("total_outflow_ratio", 0),
                "total_sales": kpis.get("total_sales", 0),
            },
            locale=current_user.get("locale", "it"),
            period_label=period_label,
            org_id=org_id,
            user_id=current_user.get("user_id") or current_user.get("id"),
        )
        return {
            "explanation": explanation,
            "source": "ai",
            "entitlement_status": "active",
        }

    # ── Fallback: rule-based explanation from the overview health_score ───────
    # Wave 9.C.3 — tell the frontend WHY it's a fallback so the UI can
    # show "AI version requires a higher plan" upsell, distinguishing
    # this from a transient AI failure.
    explanation = health_score.get("explanation", "")
    if module.health_explanation_ai is None:
        # The module simply doesn't ship an AI explainer for health.
        ent_status = "not_available_for_module"
    else:
        # AI exists but the org's plan doesn't include it.
        ent_status = "requires_higher_plan"
    return {
        "explanation": explanation,
        "source": "rule-based",
        "entitlement_status": ent_status,
    }


# ==============================================================================
# Health Score dimension preferences
# ==============================================================================

@router.get("/{module_key}/health-score-config")
async def get_health_score_config(
    module_key: str,
    current_user: dict = Depends(get_verified_user),
):
    """Get the health score dimension on/off preferences for the org."""
    org_id = current_user["organization_id"]
    from database import module_configs_collection
    from modules.cashflow_monitor.health_score import DIMENSION_KEYS

    doc = await module_configs_collection.find_one(
        {"organization_id": org_id, "module_key": module_key},
        {"_id": 0, "health_score_dimensions": 1},
    )
    # Default: all dimensions enabled
    saved = doc.get("health_score_dimensions", {}) if doc else {}
    config = {k: saved.get(k, True) for k in DIMENSION_KEYS}
    return {"health_score_dimensions": config}


@router.patch("/{module_key}/health-score-config")
async def patch_health_score_config(
    module_key: str,
    body: dict,
    current_user: dict = Depends(get_verified_user),
):
    """Save health score dimension on/off preferences for the org.

    Body: { "health_score_dimensions": { "dso": false, "dpo": false, ... } }
    Only boolean values accepted. Unknown keys are ignored.
    """
    org_id = current_user["organization_id"]
    from database import module_configs_collection
    from modules.cashflow_monitor.health_score import DIMENSION_KEYS

    dims = body.get("health_score_dimensions", {})
    # Filter to valid keys only, boolean values only
    clean = {k: bool(v) for k, v in dims.items() if k in DIMENSION_KEYS and isinstance(v, bool)}

    await module_configs_collection.update_one(
        {"organization_id": org_id, "module_key": module_key},
        {"$set": {"health_score_dimensions": clean}},
        upsert=True,
    )
    # Return the full config (merged with defaults)
    config = {k: clean.get(k, True) for k in DIMENSION_KEYS}
    return {"health_score_dimensions": config}
