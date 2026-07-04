"""
Booking availability + atomic slot reservation.

Two entry points:

1. check_booking_slot_available(org_id, product_id, date, start_time, end_time)
   Read-only pre-flight check used during order validation (P3 validator).
   Returns (available: bool, reason: str, conflict: dict|None).

   "Conflict" here means: there exists a blocked_slot in the same
   organization + date that OVERLAPS the requested time window. Overlap
   semantics: two intervals [a,b) and [c,d) overlap iff a < d and c < b.

   Scope of the check:
     - Same organization.
     - Same product_id when either side is product-scoped, OR a
       global block (product_id null) which blocks everything.
     - Any date that matches.
     - Reasons considered blocking: booking | event | personal |
       holiday | rental. Everything we store goes into this list
       today, so the check is conservative.

2. try_reserve_booking_slot(order_id, org_id, product_id, date,
                            start_time, end_time, note)
   ATOMIC reservation. Inserts a blocked_slot row with reason="booking"
   and reference_id=order_id. The design guarantees that two concurrent
   callers cannot both succeed on the same physical slot.

   Strategy (no unique-index migration needed):
   - Uses find_one_and_update with upsert=True filtered on (org, product,
     date, exact start, exact end, reason=booking). This is atomic in
     MongoDB — the first writer wins even under contention.
   - BUT: exact-match is not sufficient for overlap protection (two
     different slots 09:00-10:00 vs 09:30-10:30 would both insert).
     We therefore do a secondary re-read AFTER the insert to verify
     no overlap with OTHER existing slots exists. If a conflict is
     detected, we roll back our insert (reference_id=order_id) and
     return not_available.
   - The roll-back window is tiny (ms) and the insert we made had our
     reference_id, so we only ever delete what we just inserted.

   Returns (ok: bool, reason: str, conflict: dict|None).

Why this module lives here and not in order_service.py:
- It's a shared primitive: the P3 item-level validator wants to call
  it pre-flight (best-effort, before order creation), and the
  confirm_order path wants to call it atomically as the commit step.
- Keeping it out of order_service.py lets us unit-test without the
  whole order machinery booting.

No side-effect on other types. rental / event_ticket continue to rely
on their existing advisory-check paths (P7 / P8 will harden them).
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from models.common import generate_id, utc_now

logger = logging.getLogger(__name__)


# Time parsing -------------------------------------------------------------


def _hhmm_to_minutes(hhmm: str) -> int:
    """Parse a 'HH:MM' string into minutes from midnight.

    Permissive: accepts zero-padded or not. Returns 0 on malformed
    input so callers never raise in the critical path.
    """
    try:
        h, m = hhmm.split(":", 1)
        return int(h) * 60 + int(m)
    except Exception:
        return 0


def _intervals_overlap(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    """Half-open interval overlap in minutes-of-day.

    Uses half-open semantics [a_start, a_end) so a 09:00-10:00 slot
    does NOT conflict with an immediately adjacent 10:00-11:00 slot —
    the standard calendar convention.
    """
    a0, a1 = _hhmm_to_minutes(a_start), _hhmm_to_minutes(a_end)
    b0, b1 = _hhmm_to_minutes(b_start), _hhmm_to_minutes(b_end)
    return a0 < b1 and b0 < a1


# Read-only pre-flight ------------------------------------------------------


# Reasons that count as "this slot is taken" when we find a matching row.
# Extended when new types adopt calendar sync (kept conservative today).
_BLOCKING_REASONS = ("booking", "event", "rental", "personal", "holiday")


async def check_booking_slot_available(
    org_id: str,
    product_id: Optional[str],
    date: str,
    start_time: str,
    end_time: str,
) -> Tuple[bool, str, Optional[dict]]:
    """Pre-flight availability check for a booking request.

    Returns:
      (True, "available", None)              — slot is free.
      (False, "slot_conflict", existing)     — an existing blocked_slot
                                               overlaps the requested
                                               window.
      (False, "invalid_time_window", None)   — start >= end or malformed
                                               times.

    Safe to call repeatedly; no writes. An overlapping rental / event
    / personal block also triggers a conflict (conservative — we'd
    rather block a double booking than leak a reservation).
    """
    # Basic sanity on the window itself.
    if _hhmm_to_minutes(end_time) <= _hhmm_to_minutes(start_time):
        return False, "invalid_time_window", None

    from database import blocked_slots_collection

    # Pull all same-date blocks for this org that could plausibly
    # conflict. product_id filter: include rows that match the
    # requested product_id OR global (null) blocks.
    query = {
        "organization_id": org_id,
        "date": date,
        "reason": {"$in": list(_BLOCKING_REASONS)},
        "$or": [
            {"product_id": product_id},
            {"product_id": None},
            {"product_id": {"$exists": False}},
        ],
    }
    async for existing in blocked_slots_collection.find(query, {"_id": 0}):
        if _intervals_overlap(
            start_time, end_time,
            existing.get("start_time", "00:00"),
            existing.get("end_time", "00:00"),
        ):
            return False, "slot_conflict", existing

    return True, "available", None


# Atomic reservation --------------------------------------------------------


async def try_reserve_booking_slot(
    *,
    order_id: str,
    org_id: str,
    product_id: Optional[str],
    date: str,
    start_time: str,
    end_time: str,
    note: Optional[str] = None,
    store_id: Optional[str] = None,
    scope: str = "agenda",
) -> Tuple[bool, str, Optional[dict]]:
    """Atomically reserve a booking slot.

    Returns:
      (True, "reserved", {..row..})          — slot now belongs to order_id.
      (True, "already_reserved", {..row..})  — an earlier call with the
                                               SAME order_id already
                                               reserved this exact slot
                                               (re-entrant safe on retry).
      (False, "slot_conflict", existing)     — another order took this
                                               slot; row not inserted.
      (False, "invalid_time_window", None)   — window malformed.

    Never raises.

    Atomicity contract — how it works:

    1. MongoDB find_one_and_update with upsert=True is used to claim the
       exact-match slot key (org, product, date, start, end, reason).
       This is an atomic server-side operation: under concurrent callers
       only one insert actually happens, all others see a pre-existing
       row. No index migration is required — upsert uses the filter as
       the uniqueness key.

    2. If the upsert returned a pre-existing doc whose reference_id is
       our own order_id, treat as already_reserved (retry path).
       Otherwise some other order already has this exact slot: conflict.

    3. After winning the exact-match race, we still have to defend
       against OVERLAPPING but non-identical slots (10:30-11:30 racing
       against 10:00-11:00 — different keys, both would upsert cleanly).
       We scan for overlap. If we find an overlap, we remove our just-
       inserted row and report conflict.

    The step 3 scan compares created_at timestamps: if a conflicting
    overlap exists that was created BEFORE ours, we lost; if AFTER
    ours, the other writer will see our row and roll themselves back.
    This gives deterministic winner selection even under perfect
    synchronized contention. Ties (identical created_at) are broken
    by lexicographic id comparison (lower id wins), which is total
    ordering guaranteed by generate_id() uniqueness.
    """
    if _hhmm_to_minutes(end_time) <= _hhmm_to_minutes(start_time):
        return False, "invalid_time_window", None

    from database import blocked_slots_collection
    from pymongo import ReturnDocument

    # Step 1: atomic exact-slot claim via upsert. The filter is the
    # natural uniqueness key for a booking slot; $setOnInsert only
    # writes when we're actually creating the row.
    slot_key = {
        "organization_id": org_id,
        "product_id": product_id,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "reason": "booking",
    }
    new_id = generate_id()
    now = utc_now()
    new_doc = {
        "id": new_id,
        "organization_id": org_id,
        "store_id": store_id,
        "product_id": product_id,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "reason": "booking",
        "reference_id": order_id,
        # Scope defaults to "agenda" (service consulenza — an appointment the
        # merchant personally attends, shown on their personal calendar tab).
        # Callers that reserve a rental-flavor slot (e.g. meeting room) pass
        # scope="rentals" so the block appears only in the Rentals tab.
        "scope": scope,
        "note": note,
        "created_at": now,
    }
    before = await blocked_slots_collection.find_one_and_update(
        slot_key,
        {"$setOnInsert": new_doc},
        upsert=True,
        return_document=ReturnDocument.BEFORE,
        projection={"_id": 0},
    )

    # If `before` is None, we INSERTED. Proceed to overlap defense (step 3).
    # If `before` is not None, the row already existed — decide what it means.
    if before is not None:
        if before.get("reference_id") == order_id:
            return True, "already_reserved", before
        # Foreign reservation on the exact slot key.
        return False, "slot_conflict", before

    # Step 2: we are the exact-slot winner. Re-fetch our row so we have
    # the full persisted doc (some Mongo drivers do not echo all fields
    # in the projection on upsert).
    mine = await blocked_slots_collection.find_one(
        {"id": new_id}, {"_id": 0},
    ) or new_doc

    # Step 3: overlap defense. Scan for any other blocking row on this
    # date that overlaps our window. A conflict here is only real if
    # their created_at is BEFORE ours; otherwise the other side will
    # roll themselves back when they run this same step.
    query = {
        "organization_id": org_id,
        "date": date,
        "reason": {"$in": list(_BLOCKING_REASONS)},
        "id": {"$ne": new_id},
        "$or": [
            {"product_id": product_id},
            {"product_id": None},
            {"product_id": {"$exists": False}},
        ],
    }
    async for other in blocked_slots_collection.find(query, {"_id": 0}):
        if not _intervals_overlap(
            start_time, end_time,
            other.get("start_time", "00:00"),
            other.get("end_time", "00:00"),
        ):
            continue

        other_created = other.get("created_at")
        mine_created = mine.get("created_at", now)
        # Deterministic tiebreak: earlier created_at wins; on ties,
        # the lexicographically smaller id wins.
        we_win = True
        if other_created is not None and mine_created is not None:
            if other_created < mine_created:
                we_win = False
            elif other_created == mine_created:
                we_win = new_id < other.get("id", "\uffff")

        if we_win:
            # The other side is a late arrival — their own step 3 will
            # detect our row as winner and roll themselves back. We stay.
            continue

        # We lost. Roll back our row; only ever remove by our own id.
        await blocked_slots_collection.delete_one({"id": new_id})
        logger.info(
            "booking_availability: race lost for order=%s date=%s %s-%s, rolled back",
            order_id, date, start_time, end_time,
        )
        return False, "slot_conflict", other

    # Clean win — no conflict survived.
    return True, "reserved", mine


async def try_reserve_booking_slot_range(
    *,
    order_id: str,
    org_id: str,
    product_id: Optional[str],
    date_from: str,
    time_from: str,
    date_to: str,
    time_to: str,
    note: Optional[str] = None,
    store_id: Optional[str] = None,
    scope: str = "agenda",
) -> Tuple[bool, str, Optional[dict]]:
    """Reserve a booking slot that may span multiple days.

    When `date_from == date_to` this delegates to try_reserve_booking_slot
    (same-day, historic semantics). When the range crosses midnight, the
    reservation is materialized as N one-day blocks — same pattern used by
    rental_availability.try_reserve_rental_range — all carrying the same
    `reference_id=order_id` so release_booking_slot() still tears everything
    down atomically on cancel.

    Day breakdown:
      day 1        : time_from → 23:59
      day 2 … N-1  : 00:00 → 23:59 (full days, when > 2 days span)
      day N        : 00:00 → time_to

    Returns the same tuple shape as try_reserve_booking_slot. On any-day
    conflict, every block already inserted for this order is released before
    returning so the reservation is all-or-nothing.
    """
    from datetime import date as _date, timedelta

    # Same-day fast path — delegate to the historic single-day primitive.
    if date_from == date_to:
        return await try_reserve_booking_slot(
            order_id=order_id,
            org_id=org_id,
            product_id=product_id,
            date=date_from,
            start_time=time_from,
            end_time=time_to,
            note=note,
            store_id=store_id,
            scope=scope,
        )

    # Cross-day validation.
    try:
        d_from = _date.fromisoformat(date_from)
        d_to = _date.fromisoformat(date_to)
    except (TypeError, ValueError):
        return False, "invalid_date", None
    if d_to < d_from:
        return False, "invalid_date_range", None

    # Build per-day windows. First day: time_from → end-of-day. Last day:
    # start-of-day → time_to. Middle days: full day. End-of-day sentinel is
    # "23:59" (one-minute before midnight) to keep the [start, end) overlap
    # semantics consistent with the rest of the codebase — blocks that touch
    # exactly at midnight do not overlap.
    days = (d_to - d_from).days
    windows = []
    if days == 1:
        windows.append((date_from, time_from, "23:59"))
        windows.append((date_to, "00:00", time_to))
    else:
        windows.append((date_from, time_from, "23:59"))
        for i in range(1, days):
            d = (d_from + timedelta(days=i)).isoformat()
            windows.append((d, "00:00", "23:59"))
        windows.append((date_to, "00:00", time_to))

    inserted = []
    for (wd, ws, we) in windows:
        ok, reason, row = await try_reserve_booking_slot(
            order_id=order_id,
            org_id=org_id,
            product_id=product_id,
            date=wd,
            start_time=ws,
            end_time=we,
            note=note,
            store_id=store_id,
            scope=scope,
        )
        if not ok:
            # Roll back anything we already laid down for this order.
            await release_booking_slot(order_id=order_id, org_id=org_id)
            return False, reason, row
        inserted.append(row)

    # Represent the composite reservation by its first day's block so the
    # caller has something to inspect/log; order_service uses reference_id
    # rather than this value for downstream wiring.
    return True, "reserved", inserted[0] if inserted else None


async def release_booking_slot(order_id: str, org_id: str) -> int:
    """Release every booking reservation held by this order.

    Used on order cancel. Deletes only rows where reference_id matches,
    so we never touch other orders' data.

    Returns the number of rows deleted.
    """
    from database import blocked_slots_collection

    res = await blocked_slots_collection.delete_many({
        "organization_id": org_id,
        "reference_id": order_id,
        "reason": "booking",
    })
    return getattr(res, "deleted_count", 0)
