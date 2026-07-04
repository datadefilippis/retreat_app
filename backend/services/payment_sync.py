"""
Payment Sync Service — maintains payment_status coherence between Orders and SalesRecords.

Design:
  - Isolated service, no business logic — only propagation
  - Called as a hook after payment_status changes on either side
  - Best-effort: logs warnings, never raises
  - Idempotent: safe to call multiple times with same status
"""

import logging
from database import orders_collection, sales_records_collection

logger = logging.getLogger(__name__)


async def sync_payment_to_sales(org_id: str, order_id: str, new_payment_status: str) -> int:
    """Propagate Order.payment_status → all linked SalesRecords.

    Called after: complete_order(), mark_paid(), mark_unpaid().
    Returns count of updated SalesRecords.
    """
    try:
        result = await sales_records_collection.update_many(
            {
                "organization_id": org_id,
                "metadata.order_id": order_id,
            },
            {"$set": {"payment_status": new_payment_status}},
        )
        if result.modified_count > 0:
            logger.info("payment_sync: order %s → %d SalesRecords set to '%s'",
                        order_id, result.modified_count, new_payment_status)
        return result.modified_count
    except Exception as e:
        logger.warning("payment_sync: failed to sync order→sales for %s: %s", order_id, e)
        return 0


async def sync_payment_from_sales(org_id: str, order_id: str, sr_payment_status: str) -> bool:
    """Propagate SalesRecord.payment_status → linked Order.

    Called after: PATCH /sales/{id} when the SR has metadata.order_id.
    Only updates if the Order.payment_status is different.
    Returns True if Order was updated.
    """
    try:
        order = await orders_collection.find_one(
            {"id": order_id, "organization_id": org_id},
            {"_id": 0, "payment_status": 1, "status": 1},
        )
        if not order:
            return False

        # Don't sync to draft or cancelled orders
        if order.get("status") in ("draft", "cancelled"):
            return False

        current = order.get("payment_status")
        if current == sr_payment_status:
            return False

        from models.common import utc_now
        # Conditional update: only if payment_status hasn't changed since we read it
        result = await orders_collection.update_one(
            {"id": order_id, "organization_id": org_id, "payment_status": current},
            {"$set": {"payment_status": sr_payment_status, "updated_at": utc_now()}},
        )
        if result.modified_count == 0:
            logger.info("payment_sync: order %s payment_status changed concurrently, skipping", order_id)
            return False
        logger.info("payment_sync: SR update → order %s payment_status '%s' → '%s'",
                     order_id, current, sr_payment_status)
        return True
    except Exception as e:
        logger.warning("payment_sync: failed to sync sales→order for %s: %s", order_id, e)
        return False
