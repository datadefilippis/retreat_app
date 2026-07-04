"""AI budget repository — CRUD + period-aware spend aggregation.

Two responsibilities:
  1. Persist AIBudget documents (created/updated by system admin)
  2. Compute current_spend_usd within a budget's period on-the-fly
     by aggregating ai_usage_events.

Wave 8B (2026-05): part of the Anthropic spend governance suite.
Wave 10.C.6 (2026-05): mutations now emit audit_logs entries with
resource_type="ai_budget" so the governance dashboard can show "who
changed what, when".
"""

import logging
from datetime import datetime, date as date_type, timedelta, timezone
from typing import Optional, List

from database import ai_budgets_collection, ai_usage_events_collection
from models.ai_budget import AIBudget

logger = logging.getLogger(__name__)


async def _audit_budget_action(
    *,
    action: str,
    budget_id: Optional[str],
    actor: Optional[str],
    details: dict,
) -> None:
    """Wave 10.C.6 — write an audit_logs entry for a budget mutation.

    Best-effort: a write failure is logged but does NOT abort the
    surrounding CRUD operation. Uses the existing audit_logs collection
    (TTL-managed) instead of a parallel one.
    """
    try:
        from models import AuditLog
        from repositories import audit_repository
        await audit_repository.create(AuditLog(
            organization_id=None,  # platform-level
            user_id=actor or "system",
            action=action,
            resource_type="ai_budget",
            resource_id=budget_id,
            details=details,
        ))
    except Exception as exc:
        logger.warning(
            "ai_budget_repository: audit-log write failed for %s/%s: %s",
            action, budget_id, exc,
        )


# ── Period window helpers ────────────────────────────────────────────────────

def period_start_iso(period: str, now: Optional[datetime] = None) -> str:
    """Return ISO-date start of the current period window for the given type.

    Examples:
        period="daily"   → today's date (UTC)
        period="monthly" → first of current month
        period="yearly"  → first day of current year

    All returned as YYYY-MM-DD strings matching the ISO-date format used
    elsewhere (created_at on ai_usage_events is stored as ISO string).
    """
    now = now or datetime.now(timezone.utc)
    d = now.date()
    if period == "daily":
        return d.isoformat()
    if period == "monthly":
        return d.replace(day=1).isoformat()
    if period == "yearly":
        return d.replace(month=1, day=1).isoformat()
    raise ValueError(f"Unknown period: {period}")


# ── CRUD ─────────────────────────────────────────────────────────────────────

async def setup_indexes() -> None:
    """Wave 8B — indices to keep budget lookups fast on every chat call.

    Idempotent. Called from server.py lifespan.
    """
    indexes = [
        # Lookup all applicable budgets for a (scope, scope_id) combo.
        # The guard runs this on every Anthropic call, so it must be fast.
        ([("scope", 1), ("scope_id", 1), ("is_active", 1)],
         {"name": "scope_scopeid_active_v1"}),
        # Lookup by org for the admin "show me all my org's budgets" view.
        ([("organization_id", 1), ("scope", 1)],
         {"name": "org_scope_v1", "sparse": True}),
    ]
    for keys, opts in indexes:
        try:
            await ai_budgets_collection.create_index(keys, **opts)
        except Exception as exc:
            logger.warning(
                "ai_budget_repository.setup_indexes: %s failed: %s",
                opts.get("name"), exc,
            )
    logger.info("ai_budget_repository.setup_indexes: %d indices ensured", len(indexes))


async def create_budget(
    *,
    scope: str,
    scope_id: str,
    period: str,
    soft_limit_usd: float,
    hard_limit_usd: float,
    hard_action: str = "block",
    organization_id: Optional[str] = None,
    notes: Optional[str] = None,
    created_by: Optional[str] = None,
) -> dict:
    """Create or REPLACE a budget for the given key tuple.

    The tuple (scope, scope_id, period) is unique. If a budget with the
    same tuple already exists, this performs an upsert (preserving id +
    created_at). Returns the resulting document.
    """
    now = datetime.now(timezone.utc)
    existing = await ai_budgets_collection.find_one({
        "scope": scope, "scope_id": scope_id, "period": period,
    })

    if existing:
        update = {
            "$set": {
                "soft_limit_usd": soft_limit_usd,
                "hard_limit_usd": hard_limit_usd,
                "hard_action": hard_action,
                "organization_id": organization_id,
                "notes": notes,
                "is_active": True,
                "override_until": None,
                "updated_at": now,
            },
        }
        await ai_budgets_collection.update_one({"id": existing["id"]}, update)
        # Wave 10.C.6 — record the upsert as an audit event so the
        # governance dashboard can show "who re-tuned this budget".
        await _audit_budget_action(
            action="budget_upserted",
            budget_id=existing["id"],
            actor=created_by,
            details={
                "scope": scope, "scope_id": scope_id, "period": period,
                "soft_limit_usd": soft_limit_usd,
                "hard_limit_usd": hard_limit_usd,
                "hard_action": hard_action,
                "organization_id": organization_id,
                "notes": notes,
            },
        )
        return await ai_budgets_collection.find_one(
            {"id": existing["id"]}, {"_id": 0}
        )

    budget = AIBudget(
        scope=scope, scope_id=scope_id,
        period=period,
        soft_limit_usd=soft_limit_usd, hard_limit_usd=hard_limit_usd,
        hard_action=hard_action,
        organization_id=organization_id, notes=notes,
        created_by=created_by,
    )
    doc = budget.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    if doc.get("override_until"):
        doc["override_until"] = doc["override_until"].isoformat()
    await ai_budgets_collection.insert_one(doc)
    doc.pop("_id", None)
    # Wave 10.C.6 — audit the create event.
    await _audit_budget_action(
        action="budget_created",
        budget_id=doc["id"],
        actor=created_by,
        details={
            "scope": scope, "scope_id": scope_id, "period": period,
            "soft_limit_usd": soft_limit_usd,
            "hard_limit_usd": hard_limit_usd,
            "hard_action": hard_action,
            "organization_id": organization_id,
            "notes": notes,
        },
    )
    return doc


async def update_budget(
    budget_id: str,
    updates: dict,
    *,
    actor: Optional[str] = None,
) -> Optional[dict]:
    """Apply partial updates. Returns the resulting document or None.

    Wave 10.C.6 — accepts an ``actor`` kwarg so the audit log can
    attribute the change. Callers that don't pass it record actor='system'.
    """
    if not updates:
        return await ai_budgets_collection.find_one({"id": budget_id}, {"_id": 0})
    payload = dict(updates)
    payload["updated_at"] = datetime.now(timezone.utc)
    if isinstance(payload.get("override_until"), datetime):
        payload["override_until"] = payload["override_until"].isoformat()
    if isinstance(payload.get("updated_at"), datetime):
        payload["updated_at"] = payload["updated_at"].isoformat()
    result = await ai_budgets_collection.update_one(
        {"id": budget_id}, {"$set": payload},
    )
    if result.matched_count == 0:
        return None
    # Wave 10.C.6 — audit the patch.
    await _audit_budget_action(
        action="budget_updated",
        budget_id=budget_id,
        actor=actor,
        details={"changes": updates},
    )
    return await ai_budgets_collection.find_one({"id": budget_id}, {"_id": 0})


async def delete_budget(
    budget_id: str,
    *,
    actor: Optional[str] = None,
) -> bool:
    """Hard-delete a budget. Returns True if deleted, False if not found.

    Wave 10.C.6: ``actor`` is plumbed to the audit log.
    """
    # Capture the doc for audit details before we drop it.
    snapshot = await ai_budgets_collection.find_one(
        {"id": budget_id}, {"_id": 0},
    )
    result = await ai_budgets_collection.delete_one({"id": budget_id})
    deleted = result.deleted_count > 0
    if deleted:
        await _audit_budget_action(
            action="budget_deleted",
            budget_id=budget_id,
            actor=actor,
            details={"snapshot": snapshot},
        )
    return deleted


async def list_budgets(
    *,
    organization_id: Optional[str] = None,
    scope: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 200,
) -> List[dict]:
    """List budgets with optional filters."""
    query: dict = {}
    if organization_id is not None:
        query["organization_id"] = organization_id
    if scope:
        query["scope"] = scope
    if is_active is not None:
        query["is_active"] = is_active
    cursor = ai_budgets_collection.find(query, {"_id": 0}).sort(
        [("scope", 1), ("scope_id", 1)],
    )
    return await cursor.to_list(length=limit)


# ── Aggregation: current spend within a budget's period window ──────────────

async def compute_period_spend(
    *,
    scope: str,
    scope_id: str,
    period: str,
    organization_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> float:
    """Sum cost_usd of ai_usage_events matching this budget's scope within
    its current period window.

    Returns the sum rounded to 4 decimals.

    Performance: powered by the indices created in 8A.1
    (org_created_v1 / user_created_v1 / agent_created_v1 / feature_created_v1).
    """
    period_start = period_start_iso(period, now=now)

    # Match clause depends on scope.
    match: dict = {
        "module_key": "ai_assistant",
        "created_at": {"$gte": period_start},  # ISO strings compare lexicographically
        "cost_usd": {"$ne": None},
    }

    if scope == "global":
        pass  # no further filter
    elif scope == "org":
        match["organization_id"] = scope_id
    elif scope == "user":
        match["user_id"] = scope_id
        if organization_id:
            match["organization_id"] = organization_id
    elif scope == "feature":
        match["feature"] = scope_id
        if organization_id:
            match["organization_id"] = organization_id
    elif scope == "agent":
        match["agent_id"] = scope_id
        if organization_id:
            match["organization_id"] = organization_id
    else:
        raise ValueError(f"Unknown scope: {scope}")

    pipeline = [
        {"$match": match},
        {"$group": {"_id": None, "spend": {"$sum": "$cost_usd"}}},
    ]
    async for doc in ai_usage_events_collection.aggregate(pipeline):
        return round(float(doc.get("spend", 0) or 0), 4)
    return 0.0


# ── Applicable budgets lookup (cascade) ──────────────────────────────────────

async def find_applicable_budgets(
    *,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    feature: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> List[dict]:
    """Return ALL active budgets that apply to this Anthropic call.

    The cascade includes (in declaration order):
      - scope=global, scope_id="*"
      - scope=org,    scope_id=organization_id
      - scope=user,   scope_id=user_id
      - scope=feature, scope_id=feature
      - scope=agent,  scope_id=agent_id

    Inactive budgets are filtered out. Override_until is NOT filtered
    here — the guard handles that at check-time so the document is still
    visible in the response (audit transparency).
    """
    candidates: list = [{"scope": "global", "scope_id": "*"}]
    if organization_id:
        candidates.append({"scope": "org", "scope_id": organization_id})
    if user_id:
        candidates.append({"scope": "user", "scope_id": user_id})
    if feature:
        candidates.append({"scope": "feature", "scope_id": feature})
    if agent_id:
        candidates.append({"scope": "agent", "scope_id": agent_id})

    if not candidates:
        return []

    query = {
        "$or": candidates,
        "is_active": True,
    }
    cursor = ai_budgets_collection.find(query, {"_id": 0})
    return await cursor.to_list(length=20)
