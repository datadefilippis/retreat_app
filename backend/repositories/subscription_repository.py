"""Subscription repository — queries for pricing_plans and module_subscriptions.

Module-agnostic: works with any module_key.
"""

from typing import Optional, List

from database import pricing_plans_collection, module_subscriptions_collection
from models.common import utc_now


# ══════════════════════════════════════════════════════════════════════════════
# Pricing Plans
# ══════════════════════════════════════════════════════════════════════════════

async def list_pricing_plans(
    module_key: Optional[str] = None,
    active_only: bool = True,
) -> List[dict]:
    """List pricing plans, optionally filtered by module_key and active status."""
    filter_q: dict = {}
    if module_key is not None:
        filter_q["module_key"] = module_key
    if active_only:
        filter_q["is_active"] = True
    cursor = (
        pricing_plans_collection
        .find(filter_q, {"_id": 0})
        .sort("sort_order", 1)
    )
    return await cursor.to_list(500)


async def get_pricing_plan(plan_id: str) -> Optional[dict]:
    """Get a single pricing plan by ID."""
    return await pricing_plans_collection.find_one(
        {"id": plan_id}, {"_id": 0}
    )


async def get_pricing_plan_by_slug(module_key: str, slug: str) -> Optional[dict]:
    """Get a pricing plan by module_key + slug (unique combo)."""
    return await pricing_plans_collection.find_one(
        {"module_key": module_key, "slug": slug, "is_active": True},
        {"_id": 0},
    )


async def count_plans_by_module(module_key: str) -> int:
    """Count pricing plans for a module. Used for seed idempotency."""
    return await pricing_plans_collection.count_documents(
        {"module_key": module_key}
    )


async def list_plans_by_module(module_key: str) -> list:
    """List all pricing plans for a module (any is_active state).

    Used by the per-plan idempotent seed: the caller diffs seed slugs
    against existing ones and inserts only the missing plans.
    """
    cursor = pricing_plans_collection.find(
        {"module_key": module_key}, {"_id": 0}
    )
    return await cursor.to_list(500)


async def insert_pricing_plan(doc: dict) -> None:
    """Insert a pricing plan document."""
    await pricing_plans_collection.insert_one(doc)


async def update_plan_limits_by_slug(slug: str, limits: dict) -> bool:
    """Update the limits dict of a plan identified by slug.

    Returns True if a plan was found and updated.
    """
    from models.common import utc_now

    result = await pricing_plans_collection.update_one(
        {"slug": slug},
        {"$set": {"limits": limits, "updated_at": utc_now().isoformat()}},
    )
    return result.modified_count > 0


# ══════════════════════════════════════════════════════════════════════════════
# Module Subscriptions
# ══════════════════════════════════════════════════════════════════════════════

async def get_active_subscription(
    org_id: str,
    module_key: str,
) -> Optional[dict]:
    """Get the most recent active subscription for an org + module.

    If multiple active subscriptions exist (shouldn't, but defensive),
    returns the one with the latest started_at.
    """
    return await module_subscriptions_collection.find_one(
        {
            "organization_id": org_id,
            "module_key": module_key,
            "status": "active",
        },
        {"_id": 0},
        sort=[("started_at", -1)],
    )


async def list_subscriptions_by_org(org_id: str) -> List[dict]:
    """All active subscriptions for an organization."""
    cursor = (
        module_subscriptions_collection
        .find(
            {"organization_id": org_id, "status": "active"},
            {"_id": 0},
        )
        .sort("created_at", -1)
    )
    return await cursor.to_list(100)


async def create_subscription(doc: dict) -> dict:
    """Insert a new subscription document. Returns the inserted doc."""
    await module_subscriptions_collection.insert_one(doc)
    return doc


async def cancel_subscription(sub_id: str) -> bool:
    """Cancel a subscription. Returns True if found and updated."""
    now = utc_now().isoformat()
    result = await module_subscriptions_collection.update_one(
        {"id": sub_id, "status": "active"},
        {"$set": {"status": "cancelled", "cancelled_at": now, "updated_at": now}},
    )
    return result.modified_count > 0


async def get_recently_cancelled_subscription(
    org_id: str,
    module_key: str,
    grace_cutoff_iso: str,
) -> Optional[dict]:
    """Get the most recently cancelled subscription within the grace period.

    Returns the subscription if cancelled_at >= grace_cutoff_iso, else None.
    Used by module_access.py to provide soft read-only access after downgrade.
    """
    return await module_subscriptions_collection.find_one(
        {
            "organization_id": org_id,
            "module_key": module_key,
            "status": "cancelled",
            "cancelled_at": {"$gte": grace_cutoff_iso},
        },
        {"_id": 0},
        sort=[("cancelled_at", -1)],
    )
