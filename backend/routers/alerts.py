from fastapi import APIRouter, HTTPException, Request, status, Depends, Query
from typing import List, Optional
from models import Alert, AlertUpdate, AlertSeverity, AlertStatus, AuditLog
from auth import get_current_user, get_verified_user, get_verified_user
from repositories import alert_repository, audit_repository
from services import alert_service
from routers.auth import limiter
from datetime import datetime

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=List[Alert])
async def list_alerts(
    status_filter: Optional[AlertStatus] = None,
    severity_filter: Optional[AlertSeverity] = None,
    category_filter: Optional[str] = Query(None, description="Filter by category: A, B, C, D, E"),
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_verified_user)
):
    """List alerts for the organization"""
    alerts = await alert_repository.find_by_org(
        current_user['organization_id'],
        status_filter=status_filter,
        severity_filter=severity_filter.value if severity_filter else None,
        limit=limit
    )

    result = []
    for doc in alerts:
        # v3 category filter (post-query, lightweight)
        if category_filter and doc.get("alert_category") != category_filter.upper():
            continue

        result.append(_doc_to_alert(doc))

    return result


@router.get("/count")
async def get_alert_counts(current_user: dict = Depends(get_verified_user)):
    """Get alert counts by status"""
    counts = await alert_repository.count_by_status(current_user['organization_id'])
    return counts


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: str,
    current_user: dict = Depends(get_verified_user)
):
    """Get a specific alert"""
    doc = await alert_repository.find_by_id(alert_id, current_user['organization_id'])
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    created_at = doc['created_at']
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    
    return _doc_to_alert(doc)


@router.put("/{alert_id}/status")
async def update_alert_status(
    alert_id: str,
    update: AlertUpdate,
    current_user: dict = Depends(get_verified_user)
):
    """Update alert status"""
    org_id = current_user['organization_id']
    
    doc = await alert_repository.find_by_id(alert_id, org_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    await alert_repository.update_status(alert_id, org_id, update.status)
    
    # Audit log
    audit = AuditLog(
        organization_id=org_id,
        user_id=current_user['user_id'],
        action=f"alert_{update.status.value}",
        resource_type="alert",
        resource_id=alert_id
    )
    await audit_repository.create(audit)
    
    return {"message": f"Alert status updated to {update.status.value}"}


@router.post("/generate")
@limiter.limit("5/minute")
async def generate_alerts(request: Request, current_user: dict = Depends(get_verified_user)):
    """Run anomaly detection and generate new alerts.

    Rate-limited to 5/minute per IP (same as /insights/generate).
    """
    result = await alert_service.generate_and_save_alerts(
        current_user['organization_id'],
        locale=current_user.get('locale', 'it'),
    )
    return result


# ── v3.0: Alert preferences ─────────────────────────────────────────────────

@router.get("/preferences")
async def get_alert_preferences(current_user: dict = Depends(get_verified_user)):
    """Get alert sensitivity preset and notification settings."""
    from database import module_configs_collection
    org_id = current_user['organization_id']
    doc = await module_configs_collection.find_one(
        {"organization_id": org_id, "module_key": "cashflow_monitor"},
        {"_id": 0, "settings": 1},
    )
    settings = (doc or {}).get("settings", {})
    return {
        "alert_sensitivity": settings.get("alert_sensitivity", "standard"),
        "email_high_alerts": settings.get("email_high_alerts", True),
        "email_weekly_digest": settings.get("email_weekly_digest", True),
        "weekly_digest_day": settings.get("weekly_digest_day", "sunday"),
        "digest_period_type": settings.get("digest_period_type", "weekly"),
        "disabled_categories": settings.get("disabled_categories", []),
    }


@router.put("/preferences")
async def update_alert_preferences(
    request: Request,
    current_user: dict = Depends(get_verified_user)
):
    """Update alert sensitivity preset and notification settings."""
    from database import module_configs_collection
    from modules.cashflow_monitor.alert_thresholds import VALID_PRESETS
    from services.module_access import check_module_access

    body = await request.json()
    org_id = current_user['organization_id']

    # Plan gating: only Core+ can configure alert preferences
    await check_module_access(org_id, "cashflow_monitor", "alert_config")

    update_fields = {}
    if "alert_sensitivity" in body:
        preset = body["alert_sensitivity"]
        if preset in VALID_PRESETS:
            update_fields["settings.alert_sensitivity"] = preset
    if "email_high_alerts" in body:
        update_fields["settings.email_high_alerts"] = bool(body["email_high_alerts"])
    if "email_weekly_digest" in body:
        update_fields["settings.email_weekly_digest"] = bool(body["email_weekly_digest"])

    VALID_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    if "weekly_digest_day" in body:
        day = body["weekly_digest_day"]
        if day in VALID_DAYS:
            update_fields["settings.weekly_digest_day"] = day
    if "digest_period_type" in body:
        ptype = body["digest_period_type"]
        if ptype in ("weekly", "monthly"):
            update_fields["settings.digest_period_type"] = ptype

    VALID_CATEGORIES = {"A", "B", "C", "D", "E", "F", "G"}
    if "disabled_categories" in body:
        cats = body["disabled_categories"]
        if isinstance(cats, list):
            valid = [c.upper() for c in cats if isinstance(c, str) and c.upper() in VALID_CATEGORIES]
            update_fields["settings.disabled_categories"] = valid

    if update_fields:
        await module_configs_collection.update_one(
            {"organization_id": org_id, "module_key": "cashflow_monitor"},
            {"$set": update_fields},
            upsert=True,
        )

    return {"message": "Alert preferences updated"}


# ── Helper ───────────────────────────────────────────────────────────────────

def _doc_to_alert(doc: dict) -> Alert:
    """Convert a MongoDB document to an Alert model, handling v2 and v3 fields."""
    created_at = doc['created_at']
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)

    return Alert(
        id=doc['id'],
        organization_id=doc['organization_id'],
        module_key=doc['module_key'],
        severity=AlertSeverity(doc['severity']),
        title=doc['title'],
        summary=doc['summary'],
        date_reference=doc['date_reference'],
        metric_payload=doc.get('metric_payload', {}),
        status=AlertStatus(doc['status']),
        created_at=created_at,
        schema_version=doc.get('schema_version'),
        auto_resolved=doc.get('auto_resolved'),
        resolution_note=doc.get('resolution_note'),
        ai_analysis=doc.get('ai_analysis'),
        alert_category=doc.get('alert_category'),
        entity_key=doc.get('entity_key'),
        suggested_action=doc.get('suggested_action'),
    )
