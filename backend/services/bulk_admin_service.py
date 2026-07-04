"""
bulk_admin_service.py
=====================
Onda 10 Step D.4 — Bulk admin actions on organizations.

Provides batch operations that are out of scope for the per-org admin
endpoints (which act on a single org_id at a time). Typical use cases:

  · Bulk plan migration: org X currently on plan A → move to plan B
  · Bulk plan downgrade: orgs Pro inactive ≥30d → Solo
  · Bulk archive: orgs deactivated > N days
  · Bulk reprovision: re-align all orgs of plan X to current catalog

Design rules:
  · DRY-RUN by default: every action returns the would-be impacted list
    BEFORE doing anything. Operator confirms with a second call.
  · IDEMPOTENT: re-running the same action with same filter produces
    no additional changes if all targets are already in the desired state.
  · AUDIT-LOGGED: every applied action writes to `audit_logs` collection
    with a `bulk_action` source tag.
  · NON-DESTRUCTIVE: no hard-delete of orgs / users from this layer
    (admin.py owns hard-delete with stricter guards).

This is the SERVICE layer. The router (admin.py) is the HTTP entry point.

Public functions (all async):

  · find_targets(filter, action) → list of {org_id, name, current_state, ...}
  · apply_action(filter, action, performed_by) → {applied, skipped, failed, audit_ids}
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Allowed bulk actions. Anything else → 400 from the router.
BULK_ACTIONS = {
    "downgrade_plan",          # filter: source_plan + min_inactivity_days → target_plan
    "migrate_plan",            # filter: source_plan → target_plan (no inactivity check)
    "reprovision_to_catalog",  # filter: plan slug → re-align module subscriptions
}


def _get_filter_query(filter_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a high-level filter into a Mongo query against `organizations`."""
    q: Dict[str, Any] = {}
    if "plan" in filter_spec:
        q["commercial_plan_slug"] = filter_spec["plan"]
    if "billing_status" in filter_spec:
        q["billing_status"] = filter_spec["billing_status"]
    if "is_active" in filter_spec:
        q["is_active"] = bool(filter_spec["is_active"])
    return q


async def _apply_inactivity_filter(
    orgs: List[dict],
    min_inactivity_days: int,
) -> List[dict]:
    """Keep only orgs whose users have NOT logged in within
    `min_inactivity_days` days. An org is considered "active" if ANY of
    its users has `last_login_at` >= cutoff.
    """
    if min_inactivity_days <= 0:
        return orgs
    from database import users_collection

    cutoff = (datetime.now(timezone.utc) - timedelta(days=min_inactivity_days)).isoformat()
    inactive = []
    for org in orgs:
        org_id = org["id"]
        active_user = await users_collection.find_one(
            {
                "organization_id": org_id,
                "last_login_at": {"$gte": cutoff},
            },
            {"_id": 0, "id": 1},
        )
        if not active_user:
            inactive.append(org)
    return inactive


async def find_targets(
    *,
    action: str,
    filter_spec: Dict[str, Any],
    limit: int = 200,
) -> List[dict]:
    """Compute the list of org_ids that would be affected by the action.

    Args:
        action: one of BULK_ACTIONS
        filter_spec: dict with optional keys plan, billing_status,
                     is_active, min_inactivity_days
        limit: hard cap on returned rows (defence-in-depth, prevents
               accidentally enumerating all 10k orgs)

    Returns:
        List of dicts shaped {org_id, name, commercial_plan_slug,
        billing_status, last_login_at (latest among users)}
    """
    if action not in BULK_ACTIONS:
        raise ValueError(f"Unknown bulk action: {action!r}. Allowed: {sorted(BULK_ACTIONS)}")

    from database import organizations_collection, users_collection

    q = _get_filter_query(filter_spec)
    cursor = organizations_collection.find(q, {"_id": 0}).limit(limit)
    orgs = await cursor.to_list(limit)

    # Apply inactivity filter if requested
    if filter_spec.get("min_inactivity_days", 0) > 0:
        orgs = await _apply_inactivity_filter(orgs, filter_spec["min_inactivity_days"])

    # Enrich each org with last_login summary
    enriched = []
    for org in orgs:
        org_id = org["id"]
        last_user = await users_collection.find_one(
            {"organization_id": org_id},
            sort=[("last_login_at", -1)],
            projection={"_id": 0, "last_login_at": 1, "email": 1},
        )
        enriched.append({
            "org_id": org_id,
            "name": org.get("name"),
            "commercial_plan_slug": org.get("commercial_plan_slug"),
            "billing_status": org.get("billing_status"),
            "is_active": org.get("is_active", True),
            "last_login_at": (last_user or {}).get("last_login_at"),
            "stripe_subscription_id": org.get("stripe_subscription_id"),
        })

    return enriched


async def _validate_target_plan(target_plan_slug: str) -> None:
    """Raise ValueError if the target plan is invalid."""
    from repositories import billing_repository
    plan = await billing_repository.get_commercial_plan(target_plan_slug)
    if not plan:
        raise ValueError(f"Target plan {target_plan_slug!r} does not exist")
    if plan.get("is_addon"):
        raise ValueError(f"Target {target_plan_slug!r} is an addon, not a plan")
    if plan.get("is_archived"):
        raise ValueError(f"Target plan {target_plan_slug!r} is archived")


async def apply_action(
    *,
    action: str,
    filter_spec: Dict[str, Any],
    target_plan: Optional[str],
    performed_by: str,
    limit: int = 200,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Execute a bulk action against all matched orgs.

    Returns:
      {
        "applied":  [{"org_id", "name", "before", "after"}, ...],
        "skipped":  [{"org_id", "name", "reason"}, ...],
        "failed":   [{"org_id", "name", "error"}, ...],
        "dry_run":  bool,
        "summary":  {"total": int, "applied": int, "skipped": int, "failed": int},
      }

    On `dry_run=True`, no provisioning calls are made; "applied" lists
    what WOULD be done.
    """
    if action not in BULK_ACTIONS:
        raise ValueError(f"Unknown bulk action: {action!r}. Allowed: {sorted(BULK_ACTIONS)}")

    if action in ("downgrade_plan", "migrate_plan"):
        if not target_plan:
            raise ValueError(f"Action {action!r} requires `target_plan`")
        await _validate_target_plan(target_plan)

    targets = await find_targets(action=action, filter_spec=filter_spec, limit=limit)

    applied: List[dict] = []
    skipped: List[dict] = []
    failed: List[dict] = []

    for tgt in targets:
        org_id = tgt["org_id"]
        before_plan = tgt.get("commercial_plan_slug")

        # Action-specific guards
        if action in ("downgrade_plan", "migrate_plan"):
            if before_plan == target_plan:
                skipped.append({
                    "org_id": org_id,
                    "name": tgt.get("name"),
                    "reason": f"already on target plan {target_plan!r}",
                })
                continue
            if tgt.get("stripe_subscription_id"):
                # Stripe-managed subs are not safe to bulk-mutate from this
                # service. Operator must use admin-org-billing-reconcile.
                skipped.append({
                    "org_id": org_id,
                    "name": tgt.get("name"),
                    "reason": "stripe_subscription_id present — use Stripe-aware reconcile per org",
                })
                continue

        if dry_run:
            applied.append({
                "org_id": org_id,
                "name": tgt.get("name"),
                "before": before_plan,
                "after": target_plan or "(reprovision)",
                "would_apply": True,
            })
            continue

        # ── Actual apply ─────────────────────────────────────────────────
        try:
            from services.plan_provisioning import (
                provision_commercial_plan,
                admin_set_plan,
            )
            if action in ("downgrade_plan", "migrate_plan"):
                await admin_set_plan(
                    org_id=org_id,
                    plan_slug=target_plan,
                    assigned_by=f"bulk:{action}",
                )
            elif action == "reprovision_to_catalog":
                await provision_commercial_plan(
                    org_id=org_id,
                    plan_slug=before_plan or "free",
                    assigned_by=f"bulk:{action}",
                )

            applied.append({
                "org_id": org_id,
                "name": tgt.get("name"),
                "before": before_plan,
                "after": target_plan or "(reprovisioned)",
                "would_apply": False,
            })

            # Audit log per-org
            try:
                from repositories import audit_repository
                from models.audit import AuditLog
                audit_doc = AuditLog(
                    organization_id=org_id,
                    action=f"bulk_{action}",
                    actor_id=performed_by,
                    actor_email=performed_by,
                    description=(
                        f"Bulk {action}: {before_plan!r} → "
                        f"{target_plan or '(reprovisioned)'}"
                    ),
                    metadata={
                        "filter_spec": filter_spec,
                        "before_plan": before_plan,
                        "target_plan": target_plan,
                    },
                )
                await audit_repository.create(audit_doc)
            except Exception as audit_err:
                logger.warning("bulk_admin: audit log failed for org=%s: %s", org_id, audit_err)
        except Exception as e:
            logger.error("bulk_admin: action=%s failed for org=%s: %s", action, org_id, e)
            failed.append({
                "org_id": org_id,
                "name": tgt.get("name"),
                "error": f"{type(e).__name__}: {str(e)[:200]}",
            })

    return {
        "applied": applied,
        "skipped": skipped,
        "failed": failed,
        "dry_run": dry_run,
        "summary": {
            "total": len(targets),
            "applied": len(applied),
            "skipped": len(skipped),
            "failed": len(failed),
        },
    }
