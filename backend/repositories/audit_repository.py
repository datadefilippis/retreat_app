from typing import Optional

from database import audit_logs_collection
from models import AuditLog


async def create(audit_log: AuditLog) -> dict:
    """Create a new audit log entry"""
    audit_doc = audit_log.model_dump()
    # Phase 1 Step D3 — populate expire_at as a BSON Date for the TTL index
    # (created_at stays as ISO string to preserve backward compat with all
    # existing readers; MongoDB TTL silently ignores string fields).
    # The TTL index on expire_at deletes audit logs older than 365 days.
    audit_doc['expire_at'] = audit_doc['created_at']  # datetime obj, BSON Date
    audit_doc['created_at'] = audit_doc['created_at'].isoformat()
    await audit_logs_collection.insert_one(audit_doc)
    return audit_doc


# Track O Step 1.4 — admin query API per audit log review
# Pattern: query usa compound index (organization_id, created_at) gia'
# esistente in database.py:429 → fast retrieval su org-scoped query.

async def list_audit_logs(
    *,
    organization_id: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """List audit_logs filtered + paginated.

    Args:
        organization_id: filter per single org (None = cross-org system_admin view).
                         Sfrutta compound index (organization_id, created_at).
        action: filter exact match su action field (es. 'login', 'gdpr_erasure_requested').
        since: ISO datetime string, inclusive lower bound on created_at.
        until: ISO datetime string, exclusive upper bound.
        skip: pagination offset.
        limit: max records returned (cap 200 hard).

    Returns:
        List of audit doc dicts, sorted by created_at DESC (newest first).
        _id field stripped (no Mongo internal leak).
    """
    # Hard cap limit per evitare query gigantesche accidentali
    limit = max(1, min(limit, 200))
    skip = max(0, skip)

    query: dict = {}
    if organization_id:
        query["organization_id"] = organization_id
    if action:
        query["action"] = action
    # Date range filter su created_at (ISO string lessicografico ordering)
    if since or until:
        date_filter: dict = {}
        if since:
            date_filter["$gte"] = since
        if until:
            date_filter["$lt"] = until
        query["created_at"] = date_filter

    cursor = (
        audit_logs_collection
        .find(query, {"_id": 0})
        .sort("created_at", -1)  # newest first
        .skip(skip)
        .limit(limit)
    )
    return [doc async for doc in cursor]


async def count_audit_logs(
    *,
    organization_id: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> int:
    """Count audit_logs matching same filters as list_audit_logs.

    NB: usa count_documents (NON estimated_document_count) per accuratezza
    con filter. Costo: O(N) tra match — accettabile per pagination UI con
    indici compound a coprire la query.
    """
    query: dict = {}
    if organization_id:
        query["organization_id"] = organization_id
    if action:
        query["action"] = action
    if since or until:
        date_filter: dict = {}
        if since:
            date_filter["$gte"] = since
        if until:
            date_filter["$lt"] = until
        query["created_at"] = date_filter
    return await audit_logs_collection.count_documents(query)
