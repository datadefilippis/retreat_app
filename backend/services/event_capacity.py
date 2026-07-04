"""
Event ticket capacity — atomic seat reservation.

Closes the event_ticket equivalent of the booking-slot race that P5
closed for bookings. Before this module, `validate_occurrence_for_order`
performed an aggregation of non-cancelled orders to estimate
`booked_qty` against `occurrence.capacity`. That check is authoritative
at READ time but non-atomic at WRITE time: two customers buying the
last seat at the same millisecond both see remaining=1 and both succeed.

This module introduces an atomic server-side primitive:

  try_reserve_event_seats(order_id, org_id, occurrence_id, qty)

Strategy (no unique-index migration needed):

  1. Upsert idempotency row in `event_seat_reservations` keyed on
     (order_id, occurrence_id). find_one_and_update with
     return_document=BEFORE is MongoDB-atomic — only one of N
     concurrent callers for the same order+occurrence actually inserts.

     If the upsert found a PRE-EXISTING row belonging to the same order
     with the same qty → `already_reserved` (retry-safe path).
     If it found a PRE-EXISTING row with a different qty → `qty_mismatch`.

  2. Atomic capacity decrement on the occurrence document. The $expr
     filter reads reserved_seats with $ifNull default 0 and only
     matches when the new total would stay within capacity. Under
     concurrency, the MongoDB server evaluates this predicate atomically
     — one winner per decrement, others get None back.

     If `capacity` is null (unlimited), the predicate short-circuits
     to true and any qty is allowed.

  3. If the decrement failed (occurrence sold out or missing), we roll
     back our idempotency row so a retry with a smaller qty is possible.
     We only ever delete by our own row id — never touch another order's
     reservation.

release_event_seats(order_id, org_id)
  Undoes the reservation on order cancel. Sums the qty per occurrence
  held by this order, applies $inc: {reserved_seats: -qty} to each
  occurrence (floored at 0 via defensive arithmetic), and deletes the
  reservation rows. Safe to call multiple times — no-op when no rows
  exist.

Backward compatibility:
  - Pre-P7 occurrences have no `reserved_seats` field. $ifNull handles
    this; the first reservation seeds the counter at qty.
  - Pre-P7 order rows are NOT counted against `reserved_seats`. This is
    a known one-way transition: after P7 lands, any new reservation
    starts accounting from 0, ignoring historical orders. This is
    conservative (will never overbook new sales) but can under-count
    legacy occupancy. A one-shot backfill helper `backfill_occurrence`
    is provided for merchants who want precise truth on existing
    occurrences.
  - Existing `validate_occurrence_for_order` aggregation advisory
    remains unchanged — P7 is additive, not replacing.

Never raises. All failures return structured results.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from models.common import generate_id, utc_now

logger = logging.getLogger(__name__)


async def try_reserve_event_seats(
    *,
    order_id: str,
    org_id: str,
    occurrence_id: str,
    qty: int,
    tier_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[dict]]:
    """Atomically reserve `qty` seats on an occurrence for this order.

    When `tier_id` is provided (E1 path), delegates to
    tier_capacity.try_reserve_with_tier which performs the two-level
    atomic flow (tier decrement first, then occurrence decrement, with
    compensating rollback). Returns `tier_sold_out` / `tier_not_found`
    / `tier_inactive` / `qty_mismatch` in addition to the base reasons.

    When `tier_id` is None (mono-tier legacy path, pre-E1 behavior),
    the P7 flow runs exactly as before — the idempotency row has
    tier_id=None stored so release iterates correctly.

    Returns:
      (True, "reserved", occurrence_after)
      (True, "already_reserved", existing_row)
      (False, "qty_mismatch", existing_row)
      (False, "invalid_qty", None)
      (False, "occurrence_not_found", None)
      (False, "occurrence_sold_out", occ_before)
      (False, "occurrence_status_invalid", occ)
      # tier-only reasons (when tier_id is not None):
      (False, "tier_not_found", None)
      (False, "tier_inactive", tier_doc)
      (False, "tier_sold_out", tier_doc)

    Never raises.
    """
    if tier_id:
        # Delegate the full two-level flow to tier_capacity.
        from services.tier_capacity import try_reserve_with_tier
        return await try_reserve_with_tier(
            order_id=order_id, org_id=org_id,
            occurrence_id=occurrence_id, tier_id=tier_id, qty=qty,
        )

    if not isinstance(qty, int) or qty <= 0:
        return False, "invalid_qty", None

    from database import (
        event_occurrences_collection,
        event_seat_reservations_collection,
    )
    from pymongo import ReturnDocument

    # Step 1 — idempotency upsert on (order_id, occurrence_id, tier_id=None).
    # E1: tier_id is part of the composite key so mono-tier reservations
    # and tier-scoped reservations can coexist in the same collection
    # without the unique index colliding.
    key = {
        "order_id": order_id,
        "occurrence_id": occurrence_id,
        "tier_id": None,
    }
    new_id = generate_id()
    now = utc_now()
    new_row = {
        "id": new_id,
        "order_id": order_id,
        "organization_id": org_id,
        "occurrence_id": occurrence_id,
        "tier_id": None,
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
        existing_qty = before.get("qty")
        if existing_qty == qty:
            return True, "already_reserved", before
        return False, "qty_mismatch", before

    # Step 2 — atomic capacity decrement on the occurrence. $expr allows
    # the filter to reference document fields, so we can express "new
    # total <= capacity" as a single server-side predicate.
    updated = await event_occurrences_collection.find_one_and_update(
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

    if updated is None:
        # Either the occurrence doesn't exist, or capacity would overflow.
        # Disambiguate by doing a fetch — this is the error path and not
        # hot; no atomicity concern.
        occ = await event_occurrences_collection.find_one(
            {"id": occurrence_id, "organization_id": org_id},
            {"_id": 0},
        )
        # Roll back our idempotency row so a later retry can succeed.
        await event_seat_reservations_collection.delete_one({"id": new_id})

        if occ is None:
            return False, "occurrence_not_found", None

        status = occ.get("status", "draft")
        if status != "published":
            # Match the reason code of commerce_rules where practical.
            reason = {
                "cancelled": "occurrence_cancelled",
                "closed": "occurrence_closed",
                "draft": "occurrence_not_published",
            }.get(status, f"occurrence_status_invalid:{status}")
            return False, reason, occ

        # Published but overflow.
        logger.info(
            "event_capacity: sold-out for order=%s occ=%s qty=%s (reserved=%s/%s)",
            order_id, occurrence_id, qty,
            occ.get("reserved_seats", 0), occ.get("capacity"),
        )
        return False, "occurrence_sold_out", occ

    return True, "reserved", updated


async def release_event_seats(
    order_id: str,
    org_id: str,
) -> int:
    """Release every seat reservation held by this order.

    Used on order cancel. For each reservation row belonging to the
    order, applies `$inc: {reserved_seats: -qty}` to the occurrence
    and deletes the reservation row.

    Defensive arithmetic: if the counter would go negative (e.g. manual
    DB tampering, or the order was partially released already), the
    counter is CLAMPED to 0 via a second update using $max:0.

    Returns the number of reservation rows deleted.
    """
    from database import (
        event_occurrences_collection,
        event_seat_reservations_collection,
    )

    rows = await event_seat_reservations_collection.find(
        {"order_id": order_id, "organization_id": org_id},
        {"_id": 0},
    ).to_list(None)

    if not rows:
        return 0

    # Decrement each occurrence. One update per row keeps the logic
    # trivially correct. These updates never need to be atomic w.r.t.
    # each other — only idempotency of the total release matters.
    for row in rows:
        occ_id = row.get("occurrence_id")
        qty = int(row.get("qty", 0) or 0)
        if not occ_id or qty <= 0:
            continue
        try:
            await event_occurrences_collection.update_one(
                {"id": occ_id, "organization_id": org_id},
                {"$inc": {"reserved_seats": -qty}, "$set": {"updated_at": utc_now()}},
            )
            # Clamp to 0 if drift pushed us negative (defensive).
            await event_occurrences_collection.update_one(
                {
                    "id": occ_id,
                    "organization_id": org_id,
                    "reserved_seats": {"$lt": 0},
                },
                {"$set": {"reserved_seats": 0}},
            )
        except Exception as exc:
            logger.warning(
                "event_capacity: release failed for order=%s occ=%s: %s",
                order_id, occ_id, exc,
            )

    res = await event_seat_reservations_collection.delete_many(
        {"order_id": order_id, "organization_id": org_id},
    )
    return getattr(res, "deleted_count", 0)


async def get_occurrence_remaining(
    org_id: str,
    occurrence_id: str,
) -> Optional[int]:
    """Return remaining seats for an occurrence using the P7 counter.

    Returns None when capacity is unlimited, or the occurrence is
    missing. Returns 0 as a floor — never negative. Used by UI /
    analytics only — NOT a substitute for the atomic reservation.
    """
    from database import event_occurrences_collection

    occ = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"_id": 0, "capacity": 1, "reserved_seats": 1},
    )
    if not occ:
        return None
    cap = occ.get("capacity")
    if cap is None:
        return None
    used = int(occ.get("reserved_seats") or 0)
    return max(0, cap - used)


async def backfill_occurrence(
    org_id: str,
    occurrence_id: str,
) -> Tuple[int, int]:
    """One-shot helper to seed `reserved_seats` from historical orders.

    Sums non-cancelled order-item quantities for the given occurrence
    and sets `reserved_seats` to that total. Intended to be called
    MANUALLY after P7 deploy for merchants who want the counter to
    reflect pre-existing bookings. Safe to run multiple times —
    re-run is idempotent.

    Returns (computed_total, updated).
    `updated` is 1 if the field was (re)set, 0 if occurrence missing.
    """
    from database import (
        event_occurrences_collection,
        orders_collection,
    )

    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "status": {"$ne": "cancelled"},
            "items.occurrence_id": occurrence_id,
        }},
        {"$unwind": "$items"},
        {"$match": {"items.occurrence_id": occurrence_id}},
        {"$group": {"_id": None, "total_qty": {"$sum": "$items.quantity"}}},
    ]
    cursor = orders_collection.aggregate(pipeline)
    agg = await cursor.to_list(1)
    total = int(agg[0]["total_qty"]) if agg else 0

    res = await event_occurrences_collection.update_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"$set": {"reserved_seats": total, "updated_at": utc_now()}},
    )
    return total, getattr(res, "modified_count", 0) or (
        1 if getattr(res, "matched_count", 0) else 0
    )
