from typing import Optional, List
from database import alerts_collection
from models import Alert, AlertStatus
from datetime import datetime, timezone


async def find_by_id(alert_id: str, org_id: str) -> Optional[dict]:
    """Find alert by ID"""
    return await alerts_collection.find_one({
        "id": alert_id,
        "organization_id": org_id
    }, {"_id": 0})


async def find_by_org(
    org_id: str, 
    status_filter: Optional[AlertStatus] = None,
    severity_filter: Optional[str] = None,
    limit: int = 50
) -> List[dict]:
    """Find alerts for an organization"""
    query = {"organization_id": org_id}
    if status_filter:
        query["status"] = status_filter.value
    if severity_filter:
        query["severity"] = severity_filter
    
    cursor = alerts_collection.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(limit)


async def count_by_status(org_id: str) -> dict:
    """Count alerts by status for an organization"""
    pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    
    cursor = alerts_collection.aggregate(pipeline)
    results = await cursor.to_list(10)
    
    counts = {"new": 0, "acknowledged": 0, "resolved": 0, "total": 0}
    for item in results:
        counts[item["_id"]] = item["count"]
        counts["total"] += item["count"]
    
    return counts


async def create(alert: Alert) -> dict:
    """Create a new alert"""
    alert_doc = alert.model_dump()
    alert_doc['created_at'] = alert_doc['created_at'].isoformat()
    await alerts_collection.insert_one(alert_doc)
    return alert_doc


async def create_many(alerts: List[Alert]) -> int:
    """Create multiple alerts"""
    if not alerts:
        return 0
    
    alert_docs = []
    for alert in alerts:
        doc = alert.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        alert_docs.append(doc)
    
    result = await alerts_collection.insert_many(alert_docs)
    return len(result.inserted_ids)


async def update_status(alert_id: str, org_id: str, status: AlertStatus) -> bool:
    """Update alert status"""
    update_data = {"status": status.value}
    
    if status == AlertStatus.ACKNOWLEDGED:
        update_data["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
    elif status == AlertStatus.RESOLVED:
        update_data["resolved_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await alerts_collection.update_one(
        {"id": alert_id, "organization_id": org_id},
        {"$set": update_data}
    )
    return result.modified_count > 0


async def delete(alert_id: str, org_id: str) -> bool:
    """Delete alert by ID"""
    result = await alerts_collection.delete_one({
        "id": alert_id,
        "organization_id": org_id
    })
    return result.deleted_count > 0


# ── v2.5: AI analysis update ───────────────────────────────────────────────────

async def update_ai_analysis(alert_id: str, org_id: str, analysis: str) -> bool:
    """Set the ai_analysis field on an existing alert."""
    result = await alerts_collection.update_one(
        {"id": alert_id, "organization_id": org_id},
        {"$set": {"ai_analysis": analysis}},
    )
    return result.modified_count > 0


async def bulk_update_ai_analysis(analyses: dict, org_id: str) -> int:
    """Batch-set ai_analysis on multiple alerts in a single DB round-trip.

    Args:
        analyses: {alert_id: analysis_text, ...}
        org_id: organization scope

    Returns:
        Number of alerts modified.
    """
    if not analyses:
        return 0
    from pymongo import UpdateOne
    ops = [
        UpdateOne(
            {"id": alert_id, "organization_id": org_id},
            {"$set": {"ai_analysis": text}},
        )
        for alert_id, text in analyses.items()
    ]
    result = await alerts_collection.bulk_write(ops, ordered=False)
    return result.modified_count


# ── v2.1 addition: alert deduplication support ────────────────────────────────

async def find_active_keys(org_id: str, module_key: str) -> set:
    """Return a set of (date_reference, fingerprint) tuples for open alerts.

    Used by alert_service to skip generating duplicate alerts that are already
    sitting in status=new.  Only checks open (non-resolved) alerts to allow
    re-generation after the user resolves or acknowledges them.

    Fingerprint strategy (in priority order):
    1. ``metric_payload.alert_type`` when present — the most specific identifier.
       For category spike alerts the category name is appended to avoid
       cross-category collisions: ``"cat_<category_name>"``.
    2. First word of the title (lower-cased) as a legacy fallback for alerts
       that pre-date the metric_payload schema.

    Returns empty set on any error — never raises.
    """
    try:
        cursor = alerts_collection.find(
            {
                "organization_id": org_id,
                "module_key": module_key,
                "status": {"$in": ["new", "acknowledged"]},
            },
            {"_id": 0, "date_reference": 1, "title": 1, "metric_payload": 1},
        )
        docs = await cursor.to_list(500)
        keys = set()
        for doc in docs:
            date_ref = doc.get("date_reference") or ""
            payload = doc.get("metric_payload") or {}
            alert_type = payload.get("alert_type") or ""

            if alert_type == "category_expense_spike":
                # Include category name so each category gets its own dedup key
                cat = (payload.get("category") or "").lower().replace(" ", "_")
                fingerprint = f"cat_{cat}" if cat else "category_expense_spike"
            elif alert_type == "consecutive_negative_cashflow":
                # Include consecutive_days so escalating severity generates a new alert:
                # e.g. 3 consecutive → "consecutive_negative_cashflow_3",
                #      5 consecutive → "consecutive_negative_cashflow_5" (different key → new alert)
                days = payload.get("consecutive_days") or ""
                fingerprint = f"consecutive_negative_cashflow_{days}" if days else alert_type
            elif alert_type:
                fingerprint = alert_type
            else:
                # Legacy fallback: first word of the title
                title = doc.get("title") or ""
                fingerprint = title.lower().split()[0] if title else ""

            keys.add((date_ref, fingerprint))
        return keys
    except Exception:
        return set()


# ── v3.0: entity-key based deduplication ─────────────────────────────────────

async def find_active_dedup_keys_v3(org_id: str, module_key: str) -> set:
    """Return set of (alert_type, entity_key) for non-resolved v3 alerts.

    Falls back to legacy (date_reference, fingerprint) for alerts without entity_key.
    """
    try:
        cursor = alerts_collection.find(
            {
                "organization_id": org_id,
                "module_key": module_key,
                "status": {"$in": ["new", "acknowledged"]},
            },
            {"_id": 0, "date_reference": 1, "title": 1,
             "metric_payload": 1, "entity_key": 1},
        )
        docs = await cursor.to_list(500)
        keys = set()
        for doc in docs:
            entity_key = doc.get("entity_key")
            payload = doc.get("metric_payload") or {}
            alert_type = payload.get("alert_type") or ""

            if entity_key and alert_type:
                keys.add((alert_type, entity_key))
            else:
                # Legacy fallback for pre-v3 alerts
                date_ref = doc.get("date_reference") or ""
                if alert_type:
                    keys.add((alert_type, date_ref))
                else:
                    title = doc.get("title") or ""
                    fp = title.lower().split()[0] if title else ""
                    keys.add((fp, date_ref))
        return keys
    except Exception:
        return set()


async def find_recently_resolved_types(
    org_id: str,
    module_key: str,
    lookback_days: int = 60,
) -> set:
    """Return set of alert_type strings that were RESOLVED in the lookback window.

    Used by alert_engine to suppress rules that would otherwise re-fire
    the same alert_type with a fresh entity_key (e.g. new month) right
    after the merchant resolved it. The merchant's resolve action is
    treated as an implicit "I acknowledged this, don't tell me again
    for a while".

    The cooldown defaults to 60 days; can be tuned per-deployment via
    the alert_thresholds preset when we need fine-grained control.

    Returns an empty set on any error so the engine fails-open
    (preferable to a query failure silently silencing all rules).
    """
    try:
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
        cursor = alerts_collection.find(
            {
                "organization_id": org_id,
                "module_key": module_key,
                "status": "resolved",
                "resolved_at": {"$gte": cutoff},
            },
            {"_id": 0, "metric_payload.alert_type": 1},
        )
        out = set()
        async for doc in cursor:
            payload = doc.get("metric_payload") or {}
            atype = payload.get("alert_type")
            if atype:
                out.add(atype)
        return out
    except Exception:
        return set()


async def auto_resolve_stale(
    org_id: str,
    module_key: str,
    active_entities: set,
) -> int:
    """Auto-resolve open alerts whose (alert_type, entity_key) is no longer active.

    active_entities: set of (alert_type, entity_key) tuples that are still valid.
    Returns count of auto-resolved alerts.
    """
    try:
        cursor = alerts_collection.find(
            {
                "organization_id": org_id,
                "module_key": module_key,
                "status": {"$in": ["new", "acknowledged"]},
                "entity_key": {"$exists": True, "$ne": None},
            },
            {"_id": 0, "id": 1, "metric_payload": 1, "entity_key": 1},
        )
        docs = await cursor.to_list(500)
        to_resolve = []
        for doc in docs:
            payload = doc.get("metric_payload") or {}
            alert_type = payload.get("alert_type") or ""
            entity_key = doc.get("entity_key") or ""
            if (alert_type, entity_key) not in active_entities:
                to_resolve.append(doc["id"])

        if not to_resolve:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        result = await alerts_collection.update_many(
            {"id": {"$in": to_resolve}, "organization_id": org_id},
            {"$set": {
                "status": "resolved",
                "resolved_at": now,
                "auto_resolved": True,
                "resolution_note": "Condition no longer met",
            }},
        )
        return result.modified_count
    except Exception:
        return 0


async def find_open_alerts_for_digest(org_id: str, limit: int = 20) -> list:
    """Return open alerts for weekly email digest, ordered by severity then date."""
    severity_order = {"high": 0, "medium": 1, "low": 2}
    try:
        cursor = alerts_collection.find(
            {
                "organization_id": org_id,
                "status": {"$in": ["new", "acknowledged"]},
            },
            {"_id": 0},
        ).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(limit)
        docs.sort(key=lambda d: severity_order.get(d.get("severity", "low"), 2))
        return docs
    except Exception:
        return []
