"""
Order cleanup service — move abandoned unpaid draft orders to `expired` state.

Motivation:
  When Stripe.Session.create fails (e.g. below-minimum amount, temporary
  Stripe outage) the upstream order is already persisted. The resulting
  draft sits forever with `payment_intent=required` and either a null
  `payment_checkout` or a `payment_checkout` whose session is long past
  its Stripe expiry. These orders are visible in admin lists forever and
  accumulate as dead weight.

  This job sweeps them after a grace period and moves them to
  `status=expired` with an explicit reason. No data is deleted — the order
  remains queryable for audit and can be reactivated manually if needed
  (edit flow resets status).

Design:
  - Pure read-then-update; no Stripe API calls (cheap, idempotent).
  - Grace = ORDER_ORPHAN_GRACE_DAYS (default 7).
  - Tick interval = ORDER_CLEANUP_INTERVAL_HOURS (default 24) — not urgent;
    runs once daily in background.
  - Picks a bounded batch per tick (MAX_PER_TICK=500) to avoid DB pressure.
  - Stock is never affected (draft orders never decrement stock — that
    happens on confirm; see order_service.confirm_order).

Selection criteria:
  - payment_intent == "required"
  - status == "draft"
  - created_at < now - grace
  - EITHER payment_checkout is null (Session.create failed, no url)
    OR payment_checkout.created_at < now - grace (session was created but
       the customer never completed it in time)

Safety:
  - Confirmed / cancelled / completed orders are NEVER touched.
  - Orders with payment_intent=collected are NEVER touched — those need
    human attention (see critical_alert_service).
  - A collected-but-draft order (the "paid but confirm failed" class) is
    explicitly excluded from the expired bucket.
"""

import logging
import os
from datetime import timedelta
from typing import Optional

logger = logging.getLogger(__name__)


ORDER_ORPHAN_GRACE_DAYS = int(os.environ.get("ORDER_ORPHAN_GRACE_DAYS", "7"))
ORDER_CLEANUP_MAX_PER_TICK = int(os.environ.get("ORDER_CLEANUP_MAX_PER_TICK", "500"))

# Expiration reason code persisted on the order — stable identifier for
# admin UI filters and reporting queries.
EXPIRATION_REASON_PAYMENT_TIMEOUT = "payment_timeout"


def _build_orphan_filter(grace_cutoff) -> dict:
    """Construct the MongoDB filter for orphan draft orders past the grace window.

    Exposed as a helper so tests and dry-run tooling can reuse the exact
    same selector as the live job.
    """
    return {
        "payment_intent": "required",
        "status": "draft",
        "created_at": {"$lt": grace_cutoff},
        "$or": [
            {"payment_checkout": None},
            {"payment_checkout": {"$exists": False}},
            {"payment_checkout.created_at": {"$lt": grace_cutoff.isoformat()}},
        ],
    }


async def sweep_orphan_draft_orders(
    *, apply: bool = False, grace_days: Optional[int] = None,
) -> dict:
    """Find and optionally expire orphan draft orders.

    Args:
      apply:        False = dry-run (count only). True = actually update.
      grace_days:   Override ORDER_ORPHAN_GRACE_DAYS for this invocation.

    Returns summary dict:
      { "candidates": N, "expired": N (0 in dry-run), "grace_days": int, "cutoff": iso }
    """
    from database import orders_collection
    from models.common import utc_now

    effective_grace = grace_days if grace_days is not None else ORDER_ORPHAN_GRACE_DAYS
    now = utc_now()
    cutoff = now - timedelta(days=effective_grace)

    query = _build_orphan_filter(cutoff)

    # Cap the per-tick workload so a backlog does not monopolize DB time
    ids_to_expire = []
    cursor = orders_collection.find(
        query,
        {"_id": 0, "id": 1, "organization_id": 1},
    ).limit(ORDER_CLEANUP_MAX_PER_TICK)
    async for doc in cursor:
        ids_to_expire.append(doc["id"])

    result = {
        "candidates": len(ids_to_expire),
        "expired": 0,
        "grace_days": effective_grace,
        "cutoff": cutoff.isoformat(),
    }

    if not apply or not ids_to_expire:
        logger.info(
            "order_cleanup: sweep (%s) — candidates=%d grace=%dd cutoff=%s",
            "APPLY" if apply else "DRY-RUN", result["candidates"],
            effective_grace, cutoff.isoformat(),
        )
        return result

    # Bulk-update: set status=expired + expiration metadata. Untouch other fields.
    update_res = await orders_collection.update_many(
        {"id": {"$in": ids_to_expire}, "payment_intent": "required", "status": "draft"},
        {"$set": {
            "status": "expired",
            "expiration_reason": EXPIRATION_REASON_PAYMENT_TIMEOUT,
            "expired_at": now,
            "updated_at": now,
        }},
    )
    result["expired"] = update_res.modified_count
    logger.info(
        "order_cleanup: expired %d draft orphan orders (grace=%dd, candidates=%d)",
        result["expired"], effective_grace, result["candidates"],
    )
    return result
