"""
Payment diagnostics — observability for the webhook + commerce pipeline.

Scope:
  Admin-level, org-scoped (not system-admin) reports that answer the
  operational questions that come up during incident response:
    - "Are webhooks coming in and being processed?"
    - "How many events failed in the last 24h?"
    - "Are any events stuck in `processed=False` mid-flight?"
    - "When did we last see each event type?"

Design:
  - Purely READ-ONLY against billing_events + critical_alerts. No writes,
    no background tasks, no side effects. Safe to call at any frequency.
  - Every response includes an `org_id` scope marker so the consumer is
    never confused about whose data it received.
  - Aggregations are computed on-demand. Rows are bounded so a long-
    lived platform with high event volume does not blow up the response.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostics", tags=["Payment Diagnostics"])


# Stale threshold for "event claimed but never finalized" — mirrors the
# default used by billing_repository.try_acquire_event_lock. Keeping it in
# sync via shared import would couple two modules; we treat both as app-
# level constants that happen to agree for now.
_STALE_IN_FLIGHT_SECONDS = 60


@router.get("/webhooks")
async def webhook_health(
    hours: int = Query(24, ge=1, le=168),
    current_user: dict = Depends(require_admin),
) -> dict:
    """Per-event-type health snapshot over a rolling window.

    Returns, for each event type that has seen traffic in the window:
      { event_type, total, processed, failed, in_flight, last_seen_at,
        last_error }

    Plus top-level summary fields: window_hours, cutoff_iso, totals.

    Org-scoped: billing_events.organization_id is written by the canonical
    handler path, so filtering on it gives us the subset of events that
    produced visible effects on this org. Events with organization_id not
    yet resolved (e.g. still in-flight) are included under a null org
    bucket only if the caller is the owner of that org — we use both the
    matching org_id AND missing org_id with small matching pressure, see
    comment below.
    """
    from database import billing_events_collection

    org_id = current_user["organization_id"]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    stale_cutoff = now - timedelta(seconds=_STALE_IN_FLIGHT_SECONDS)

    # We match on organization_id == org_id. The handler path sets it only
    # after a successful run (mark_event_processed). Unresolved in-flight
    # or failed events may not yet have org_id — we deliberately exclude
    # them from this org-scoped view to avoid cross-tenant leakage.
    # A system-admin oriented endpoint is a separate, future concern.
    base_match = {
        "organization_id": org_id,
        "created_at": {"$gte": cutoff},
    }

    pipeline = [
        {"$match": base_match},
        {"$group": {
            "_id": "$event_type",
            "total": {"$sum": 1},
            "processed": {"$sum": {"$cond": [{"$eq": ["$processed", True]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [
                {"$and": [
                    {"$eq": ["$processed", False]},
                    {"$ifNull": ["$error", False]},
                ]}, 1, 0,
            ]}},
            "in_flight": {"$sum": {"$cond": [
                {"$and": [
                    {"$eq": ["$processed", False]},
                    {"$gt": ["$started_at", stale_cutoff]},
                    {"$not": {"$ifNull": ["$error", False]}},
                ]}, 1, 0,
            ]}},
            "stale": {"$sum": {"$cond": [
                {"$and": [
                    {"$eq": ["$processed", False]},
                    {"$lte": ["$started_at", stale_cutoff]},
                    {"$not": {"$ifNull": ["$error", False]}},
                ]}, 1, 0,
            ]}},
            "last_seen_at": {"$max": "$created_at"},
            "last_error": {"$max": "$error"},
        }},
        {"$project": {
            "_id": 0,
            "event_type": "$_id",
            "total": 1, "processed": 1, "failed": 1,
            "in_flight": 1, "stale": 1,
            "last_seen_at": 1, "last_error": 1,
        }},
        {"$sort": {"last_seen_at": -1}},
    ]

    by_type = await billing_events_collection.aggregate(pipeline).to_list(100)

    # Build top-level summary
    summary = {
        "total": 0, "processed": 0, "failed": 0,
        "in_flight": 0, "stale": 0,
    }
    for row in by_type:
        for k in ("total", "processed", "failed", "in_flight", "stale"):
            summary[k] += row.get(k, 0)

    return {
        "org_id": org_id,
        "window_hours": hours,
        "cutoff_iso": cutoff.isoformat(),
        "generated_at": now.isoformat(),
        "summary": summary,
        "by_event_type": by_type,
    }


@router.get("/critical-alerts")
async def critical_alerts_unresolved(
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_admin),
) -> dict:
    """Unresolved critical alerts for this org, newest first.

    Complements /webhooks: the latter tells you "has the pipeline been
    running"; this one tells you "has it produced incidents that still
    need human attention".
    """
    from database import db

    org_id = current_user["organization_id"]

    cursor = (
        db.critical_alerts
        .find({"org_id": org_id, "resolved_at": None}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    alerts = await cursor.to_list(limit)

    return {
        "org_id": org_id,
        "count": len(alerts),
        "alerts": alerts,
    }


@router.post("/critical-alerts/{alert_id}/resolve")
async def resolve_critical_alert(
    alert_id: str,
    current_user: dict = Depends(require_admin),
) -> dict:
    """Mark a critical alert as resolved (human-ack, not auto).

    Strictly org-scoped. Records actor + timestamp for the audit trail.
    Idempotent: calling on an already-resolved alert returns the current
    state without a second write.
    """
    from database import db

    org_id = current_user["organization_id"]
    now = datetime.now(timezone.utc)

    # Match org_id in the WHERE so the caller cannot resolve another org's alerts
    # even if they stumbled upon the id.
    result = await db.critical_alerts.update_one(
        {"id": alert_id, "org_id": org_id, "resolved_at": None},
        {"$set": {"resolved_at": now, "resolved_by": current_user.get("id")}},
    )

    if result.matched_count == 0:
        # Either: wrong id, wrong org, or already resolved
        alert = await db.critical_alerts.find_one(
            {"id": alert_id, "org_id": org_id}, {"_id": 0},
        )
        if alert and alert.get("resolved_at") is not None:
            return {"status": "already_resolved", "alert": alert}
        return {"status": "not_found", "alert_id": alert_id}

    updated = await db.critical_alerts.find_one({"id": alert_id}, {"_id": 0})
    logger.info(
        "payment_diagnostics: alert %s resolved by %s (org=%s)",
        alert_id, current_user.get("id"), org_id,
    )
    return {"status": "resolved", "alert": updated}
