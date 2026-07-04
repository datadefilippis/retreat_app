"""
Tier capacity — atomic seat reservation extended to two levels.

E1 extends the P7 primitive (single-level occurrence capacity) to handle
multi-tier events: when a client buys a ticket for tier X inside
occurrence Y, BOTH limits must hold:

  tier.reserved_seats     + qty   <=   tier.capacity    (if tier capped)
  occurrence.reserved_seats + qty <=   occurrence.capacity  (if capped)

Design choice — two sequential atomic updates with compensating rollback:

  Step 1 (TIER): find_one_and_update on the tier doc with the $expr
    capacity predicate. If None → `tier_sold_out`, nothing persisted.

  Step 2 (OCCURRENCE): find_one_and_update on the occurrence doc with
    the same $expr predicate. If None → `occurrence_sold_out`, we
    compensate by decrementing the tier back down.

  The compensation removes ONLY the qty WE just added (by order id +
  tier id), so it can never touch another order's reservation.

This is NOT a cross-document ACID transaction. Worst case under perfect
concurrency: two callers both pass tier, one passes occurrence and the
other rolls back — correct outcome, just one retry wasted. Worse case
analyzed in tests (test_ticket_tier.t07).

Idempotency:
  Reservation rows in `event_seat_reservations` gain a nullable `tier_id`
  column. The composite key is now (order_id, occurrence_id, tier_id).
  Same order + same tier + same qty = idempotent retry.

Integration:
  `services/event_capacity.try_reserve_event_seats` keeps its existing
  signature and behavior. It now accepts an optional `tier_id` argument;
  when present it delegates to this module. Mono-tier callers
  (tier_id is None) stay on the P7 path with zero behavioral change.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from models.common import generate_id, utc_now

logger = logging.getLogger(__name__)


async def try_reserve_with_tier(
    *,
    order_id: str,
    org_id: str,
    occurrence_id: str,
    tier_id: str,
    qty: int,
) -> Tuple[bool, str, Optional[dict]]:
    """Atomic two-level seat reservation: tier first, then occurrence.

    Returns:
      (True,  "reserved",          occurrence_after)    success
      (True,  "already_reserved",  existing_row)         idempotent retry
      (False, "invalid_qty",       None)
      (False, "qty_mismatch",      existing_row)         same (order, occ, tier) with different qty
      (False, "tier_not_found",    None)                 no such tier
      (False, "tier_inactive",     tier_doc)             is_active=False
      (False, "tier_sold_out",     tier_doc)             tier capacity exceeded
      (False, "occurrence_not_found", None)              no such occurrence
      (False, "occurrence_status_invalid:*", occ_doc)    not published
      (False, "occurrence_sold_out", occ_doc)            occurrence capacity exceeded
                                                         (tier was already compensated)

    Never raises.
    """
    if not isinstance(qty, int) or qty <= 0:
        return False, "invalid_qty", None

    from database import (
        event_occurrences_collection,
        event_seat_reservations_collection,
        event_ticket_tiers_collection,
    )
    from pymongo import ReturnDocument

    # ── Step 0: idempotency upsert keyed on (order, occurrence, tier) ──────
    # tier_id is part of the key so the same order can hold BOTH tiers on
    # the same occurrence (Michele's cart: 1 VIP + 1 Standard).
    key = {
        "order_id": order_id,
        "occurrence_id": occurrence_id,
        "tier_id": tier_id,
    }
    new_id = generate_id()
    now = utc_now()
    new_row = {
        "id": new_id,
        "order_id": order_id,
        "organization_id": org_id,
        "occurrence_id": occurrence_id,
        "tier_id": tier_id,
        "qty": qty,
        "created_at": now,
    }
    before = await event_seat_reservations_collection.find_one_and_update(
        key,
        {"$setOnInsert": new_row},
        upsert=True,
        return_document=ReturnDocument.BEFORE,
        projection={"_id": 0},
    )

    if before is not None:
        # Row existed — same order, same tier. Compare qty.
        if before.get("qty") == qty:
            return True, "already_reserved", before
        return False, "qty_mismatch", before

    # ── Step 1: atomic decrement on the tier ───────────────────────────────
    tier_updated = await event_ticket_tiers_collection.find_one_and_update(
        {
            "id": tier_id,
            "organization_id": org_id,
            "occurrence_id": occurrence_id,
            "is_active": True,
            "$expr": {
                "$or": [
                    {"$eq": [{"$ifNull": ["$capacity", None]}, None]},
                    {
                        "$lte": [
                            {"$add": [{"$ifNull": ["$reserved_seats", 0]}, qty]},
                            "$capacity",
                        ]
                    },
                ]
            },
        },
        {
            "$inc": {"reserved_seats": qty},
            "$set": {"updated_at": now},
        },
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )

    if tier_updated is None:
        # Disambiguate: tier missing vs inactive vs capacity exceeded.
        tier_doc = await event_ticket_tiers_collection.find_one(
            {"id": tier_id, "organization_id": org_id},
            {"_id": 0},
        )
        await event_seat_reservations_collection.delete_one({"id": new_id})

        if tier_doc is None:
            return False, "tier_not_found", None
        if not tier_doc.get("is_active", True):
            return False, "tier_inactive", tier_doc
        if tier_doc.get("occurrence_id") != occurrence_id:
            # tier belongs to a different occurrence — treat as not found
            return False, "tier_not_found", None
        logger.info(
            "tier_capacity: tier sold_out order=%s occ=%s tier=%s qty=%s (%s/%s)",
            order_id, occurrence_id, tier_id, qty,
            tier_doc.get("reserved_seats", 0), tier_doc.get("capacity"),
        )
        return False, "tier_sold_out", tier_doc

    # ── Step 2: atomic decrement on the occurrence ─────────────────────────
    # Re-uses P7 semantics: must be published, new total <= capacity.
    occ_updated = await event_occurrences_collection.find_one_and_update(
        {
            "id": occurrence_id,
            "organization_id": org_id,
            "status": "published",
            "$expr": {
                "$or": [
                    {"$eq": [{"$ifNull": ["$capacity", None]}, None]},
                    {
                        "$lte": [
                            {"$add": [{"$ifNull": ["$reserved_seats", 0]}, qty]},
                            "$capacity",
                        ]
                    },
                ]
            },
        },
        {
            "$inc": {"reserved_seats": qty},
            "$set": {"updated_at": now},
        },
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )

    if occ_updated is None:
        # Occurrence failed — compensate the tier decrement we just made.
        # Only subtract exactly our qty; never touches other writers.
        await event_ticket_tiers_collection.update_one(
            {"id": tier_id, "organization_id": org_id},
            {"$inc": {"reserved_seats": -qty}, "$set": {"updated_at": utc_now()}},
        )
        # Clamp to 0 if drift pushed us negative.
        await event_ticket_tiers_collection.update_one(
            {
                "id": tier_id, "organization_id": org_id,
                "reserved_seats": {"$lt": 0},
            },
            {"$set": {"reserved_seats": 0}},
        )
        # Clean up idempotency row so a retry is possible.
        await event_seat_reservations_collection.delete_one({"id": new_id})

        # Disambiguate the occurrence failure for a clean reason code.
        occ = await event_occurrences_collection.find_one(
            {"id": occurrence_id, "organization_id": org_id},
            {"_id": 0},
        )
        if occ is None:
            return False, "occurrence_not_found", None
        status = occ.get("status", "draft")
        if status != "published":
            reason = {
                "cancelled": "occurrence_cancelled",
                "closed": "occurrence_closed",
                "draft": "occurrence_not_published",
            }.get(status, f"occurrence_status_invalid:{status}")
            return False, reason, occ
        logger.info(
            "tier_capacity: occurrence sold_out order=%s occ=%s tier=%s qty=%s (tier compensated)",
            order_id, occurrence_id, tier_id, qty,
        )
        return False, "occurrence_sold_out", occ

    return True, "reserved", occ_updated


async def release_tier_seats(
    order_id: str,
    org_id: str,
) -> int:
    """Release every tier-scoped reservation held by this order.

    Complements release_event_seats for the occurrence-level release.
    For every row with a non-null tier_id, applies $inc: -qty on the
    corresponding tier (defensive clamp to 0). The idempotency rows
    themselves are deleted by the occurrence-level release in
    event_capacity.release_event_seats, so this function does NOT
    delete rows — it only applies tier-side decrements.

    Returns the number of tier rows successfully decremented.
    """
    from database import (
        event_seat_reservations_collection,
        event_ticket_tiers_collection,
    )

    rows = await event_seat_reservations_collection.find(
        {
            "order_id": order_id,
            "organization_id": org_id,
            "tier_id": {"$ne": None},
        },
        {"_id": 0, "tier_id": 1, "qty": 1},
    ).to_list(None)

    if not rows:
        return 0

    decremented = 0
    for row in rows:
        tid = row.get("tier_id")
        qty = int(row.get("qty", 0) or 0)
        if not tid or qty <= 0:
            continue
        try:
            await event_ticket_tiers_collection.update_one(
                {"id": tid, "organization_id": org_id},
                {"$inc": {"reserved_seats": -qty}, "$set": {"updated_at": utc_now()}},
            )
            await event_ticket_tiers_collection.update_one(
                {
                    "id": tid, "organization_id": org_id,
                    "reserved_seats": {"$lt": 0},
                },
                {"$set": {"reserved_seats": 0}},
            )
            decremented += 1
        except Exception as exc:
            logger.warning(
                "tier_capacity: release failed for order=%s tier=%s: %s",
                order_id, tid, exc,
            )
    return decremented
