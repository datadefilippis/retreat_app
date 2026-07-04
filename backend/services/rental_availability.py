"""
Rental availability + atomic range reservation.

Companion to P5 (booking_availability) and P7 (event_capacity), written
for the same reason: before this module, rental availability was
advisory only. Two customers renting the same item for overlapping
date ranges would both succeed; the calendar would carry conflicting
rows and the merchant would discover the collision manually.

The rental unit of reservation is ONE DAY. A rental from
date_from=2026-08-10 to date_to=2026-08-12 (inclusive) reserves three
daily rows. Partial-day resolution is not modelled today — a rental
day is treated as 00:00-23:59, and two rentals cannot share a day.

Entry points:

  check_rental_range_available(org_id, product_id, date_from, date_to)
    Read-only pre-flight. Returns (True, "available", None) if no
    blocked_slot row (rental or otherwise) already covers any day in
    the range, else (False, "rental_day_conflict", existing_row).

  try_reserve_rental_range(order_id, org_id, product_id, date_from,
                           date_to, note)
    Atomic per-day reservation. Same server-side primitive used by
    P5: find_one_and_update with upsert=True on the natural key
    (org, product, date, reason=rental). Exactly one caller wins each
    day; losers get the structured conflict back.

    Multi-day atomicity: this is NOT a cross-day ACID transaction. We
    reserve day-by-day and, on the first conflict, ROLL BACK every day
    we have inserted so far (by our own row ids only — never touching
    other orders' rows). The worst that can happen under perfect
    concurrency is that two callers take each other's first-day win
    and both roll back — neither reserves. That is conservative and
    correct (no overbooking), at the cost of rare false negatives.
    A retry succeeds deterministically.

  release_rental_range(order_id, org_id)
    Cancel-path cleanup. Deletes every rental row whose reference_id
    matches. Safe to call repeatedly.

Why reuse blocked_slots instead of a dedicated collection:
  - The existing calendar UI already renders blocked_slots rows.
  - No index migration.
  - The atomicity contract is the same as P5 — upsert on the natural
    key, rollback by own id.
  - P7 uses a dedicated collection because event seats are a counter,
    not a time slot. Rentals ARE time slots, so this fits.

Overlap semantics: a rental on 2026-08-10 to 2026-08-12 conflicts with
an existing rental covering any of those three days — same product +
same org. Different products on the same day are allowed (separate
inventory); different orgs obviously isolated. A booking / event /
personal / holiday block in the range is ALSO a conflict — the rental
physically cannot happen while the calendar is taken.

Never raises.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional, Tuple, List

from models.common import generate_id, utc_now

logger = logging.getLogger(__name__)

# Reasons that count as "this day is taken" when pre-flight / overlap
# check runs. Mirrors P5's _BLOCKING_REASONS so a booking scheduled
# inside a rental range also reports as a conflict.
_BLOCKING_REASONS = ("booking", "event", "rental", "personal", "holiday")


def _iter_days(date_from: str, date_to: str) -> List[str]:
    """Inclusive range of ISO date strings from `date_from` to `date_to`.

    Returns [] on malformed input — callers treat empty as invalid.
    """
    try:
        d_from = date.fromisoformat(date_from)
        d_to = date.fromisoformat(date_to)
    except Exception:
        return []
    if d_to < d_from:
        return []
    days: List[str] = []
    cur = d_from
    while cur <= d_to:
        days.append(cur.isoformat())
        cur += timedelta(days=1)
    return days


# Read-only pre-flight ------------------------------------------------------


async def check_rental_range_available(
    org_id: str,
    product_id: Optional[str],
    date_from: str,
    date_to: Optional[str] = None,
) -> Tuple[bool, str, Optional[dict]]:
    """Advisory availability check for a rental range.

    Returns:
      (True, "available", None)              — every day in the range
                                               is free.
      (False, "rental_day_conflict", row)    — at least one day is
                                               already taken; the
                                               first offending row is
                                               returned.
      (False, "invalid_date_range", None)    — date_to < date_from,
                                               malformed dates, or
                                               date_from missing.

    Advisory only: between this check and the atomic reservation,
    another caller may take a day. The authoritative guarantee is in
    try_reserve_rental_range.
    """
    if not date_from:
        return False, "invalid_date_range", None

    days = _iter_days(date_from, date_to or date_from)
    if not days:
        return False, "invalid_date_range", None

    from database import blocked_slots_collection

    query = {
        "organization_id": org_id,
        "date": {"$in": days},
        "reason": {"$in": list(_BLOCKING_REASONS)},
        "$or": [
            {"product_id": product_id},
            {"product_id": None},
            {"product_id": {"$exists": False}},
        ],
    }
    existing = await blocked_slots_collection.find_one(query, {"_id": 0})
    if existing is not None:
        return False, "rental_day_conflict", existing
    return True, "available", None


# Atomic reservation --------------------------------------------------------


async def try_reserve_rental_range(
    *,
    order_id: str,
    org_id: str,
    product_id: Optional[str],
    date_from: str,
    date_to: Optional[str] = None,
    note: Optional[str] = None,
    store_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[dict]]:
    """Atomically reserve every day in the given rental range.

    Returns:
      (True, "reserved", {"days": N})           — all N days claimed.
      (True, "already_reserved", {"days": N})   — this order already
                                                  holds the full
                                                  range (idempotent
                                                  retry path).
      (False, "rental_day_conflict", row)       — a day was taken by
                                                  another writer;
                                                  everything we
                                                  previously inserted
                                                  for this reservation
                                                  has been rolled back.
      (False, "invalid_date_range", None)       — bad input.

    Never raises.

    Strategy — the single-day primitive is a find_one_and_update with
    upsert on the key (org, product, date, reason=rental). That is
    atomic server-side: under concurrency one caller inserts, others
    see the existing row.

    Multi-day rollback: on the first day that returns a foreign row,
    we walk back and delete-by-id every day we just inserted. We
    never touch other orders' rows — the delete filter includes our
    own row id. A fresh retry will succeed cleanly once the conflict
    is resolved.

    Idempotency: if every day's upsert returns a pre-existing row
    belonging to our order_id, we treat the whole range as
    `already_reserved`.
    """
    if not date_from:
        return False, "invalid_date_range", None

    days = _iter_days(date_from, date_to or date_from)
    if not days:
        return False, "invalid_date_range", None

    from database import blocked_slots_collection
    from pymongo import ReturnDocument

    inserted_ids: List[str] = []
    all_pre_existing_mine = True  # flips to False on first NEW insert

    for day in days:
        key = {
            "organization_id": org_id,
            "product_id": product_id,
            "date": day,
            "reason": "rental",
        }
        new_id = generate_id()
        now = utc_now()
        new_doc = {
            "id": new_id,
            "organization_id": org_id,
            "store_id": store_id,
            "product_id": product_id,
            "date": day,
            "start_time": "00:00",
            "end_time": "23:59",
            "reason": "rental",
            "reference_id": order_id,
            # Rentals live in the "Noleggi" calendar tab so they don't pollute
            # the admin's personal agenda (bookings + manual blocks + events).
            # Previously this was "agenda" which caused rental blocks to show
            # up alongside the merchant's personal schedule.
            "scope": "rentals",
            "note": note,
            "created_at": now,
        }

        before = await blocked_slots_collection.find_one_and_update(
            key,
            {"$setOnInsert": new_doc},
            upsert=True,
            return_document=ReturnDocument.BEFORE,
            projection={"_id": 0},
        )

        if before is None:
            # Fresh insert for this day — we won this slot.
            all_pre_existing_mine = False
            inserted_ids.append(new_id)
            continue

        # Something already existed on this exact key. Is it ours?
        if before.get("reference_id") == order_id:
            # Idempotent re-entry — previous run of this same order
            # already reserved this day. Do not mark it as a new
            # insert so rollback never deletes it.
            continue

        # Foreign. Conflict. Roll back everything WE inserted this call.
        if inserted_ids:
            await blocked_slots_collection.delete_many({"id": {"$in": inserted_ids}})
            logger.info(
                "rental_availability: conflict on %s for order=%s — rolled back %d days",
                day, order_id, len(inserted_ids),
            )
        return False, "rental_day_conflict", before

    # Post-pass overlap defense: we claimed each EXACT (product, date,
    # reason=rental) key. Still need to verify no OTHER blocking row
    # (booking / event / personal / holiday) overlaps our days, since
    # those use different reason codes and wouldn't be caught by the
    # upsert filter.
    query = {
        "organization_id": org_id,
        "date": {"$in": days},
        "reason": {"$in": [r for r in _BLOCKING_REASONS if r != "rental"]},
        "$or": [
            {"product_id": product_id},
            {"product_id": None},
            {"product_id": {"$exists": False}},
        ],
    }
    other = await blocked_slots_collection.find_one(query, {"_id": 0})
    if other is not None:
        if inserted_ids:
            await blocked_slots_collection.delete_many({"id": {"$in": inserted_ids}})
            logger.info(
                "rental_availability: non-rental overlap detected for order=%s — rolled back %d days",
                order_id, len(inserted_ids),
            )
        return False, "rental_day_conflict", other

    if all_pre_existing_mine and not inserted_ids:
        return True, "already_reserved", {"days": len(days)}

    return True, "reserved", {"days": len(days)}


async def release_rental_range(order_id: str, org_id: str) -> int:
    """Release every rental day held by this order.

    Deletes only rows where reference_id matches — other orders'
    reservations are untouched. Safe to call repeatedly.

    Returns the number of rows deleted.
    """
    from database import blocked_slots_collection

    res = await blocked_slots_collection.delete_many({
        "organization_id": org_id,
        "reference_id": order_id,
        "reason": "rental",
    })
    return getattr(res, "deleted_count", 0)
