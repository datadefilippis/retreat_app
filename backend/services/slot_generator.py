"""
slot_generator.py — shared helper to materialize available booking slots.

Used by the public storefront endpoints that expose hh:mm slot pickers:

    /public/services/{product_id}/slots      (service / consulenza)
    /public/reservations/{product_id}/slots  (rental flavor=slot, e.g. meeting room)

DESIGN
  - Pure I/O-bound function: reads availability_rules and blocked_slots, returns
    a plain list of {date, start_time, end_time} dicts. No Pydantic coupling so
    both callers can wrap the result in their own response schema.
  - `use_default_schedule` fallback (Onda 15): when a product has no rules of
    its own AND the admin opted into the store default, synthesize a 7-day
    Mon-Sun 09:00-18:00 grid using the product's default duration.
  - Blocked-slot subtraction respects all scopes (`agenda`, `rentals`, `manual`)
    so a rental block correctly removes slots that overlap in the service
    picker too — the calendar is org-wide, scope is just a visualization hint
    on the admin side.
  - Past slots on "today" are skipped so the customer never lands on a
    technically-available-but-already-passed time.

THREADING
  This helper is async because it hits MongoDB. The rest of the logic is pure.

CONTRACT
  generate_available_slots(
      org_id: str,
      product_id: str,
      metadata: dict,
      days: int = 30,
  ) -> (default_duration_minutes: int, slots: list[dict])

  Each slot dict: {"date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM"}
"""

from __future__ import annotations

from datetime import date as _date, datetime as _dt, timedelta
from typing import Any, Dict, List, Optional, Tuple


def _parse_hhmm(s: str) -> Tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)


def _minutes_to_hhmm(m: int) -> str:
    h = m // 60
    mm = m % 60
    return f"{h:02d}:{mm:02d}"


def _overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    """Half-open interval overlap: [a_start, a_end) ∩ [b_start, b_end) ≠ ∅."""
    if not (a_start and a_end and b_start and b_end):
        return False
    return a_start < b_end and b_start < a_end


# Reasons that count as "merchant is busy on the agenda" — i.e. blocks the
# same merchant cannot keep on parallel services. Mirrors `_BLOCKING_REASONS`
# in services/booking_availability.py minus "rental" (rentals have their own
# scope/tab and don't conflict with agenda services).
#
# Used as a legacy-compatibility fallback: blocked_slots created BEFORE the
# `scope` field existed in production (pre go-live data on existing accounts)
# don't carry scope="agenda", but they ARE agenda-relevant when the reason
# is one of these values. Without this fallback an old service-booking on
# product A would not block a parallel slot picker for product B on the
# same account.
_AGENDA_REASONS: Tuple[str, ...] = ("booking", "event", "personal", "holiday")


async def generate_available_slots(
    *,
    org_id: str,
    product_id: str,
    metadata: Dict[str, Any],
    days: int = 30,
    scope: Optional[str] = None,
) -> Tuple[int, List[Dict[str, str]]]:
    """Return `(default_duration_minutes, slots)` for a slot-picker UI.

    The caller must have already verified that the product is published,
    active, and of a type that supports slot pickers (service / rental+slot).

    `metadata` is the product's `metadata` dict — used to read
    `duration_minutes` (fallback 60), `slot_duration_minutes`, and the
    Onda 15 `use_default_schedule` flag.

    `scope` (optional): when provided (`"agenda"` or `"rentals"`), any block
    on the same day carrying that scope is subtracted regardless of
    `product_id`. This matches the merchant's mental model:
      - Services share a single personal agenda — a booking on service A
        must hide the same window on service B.
      - Rentals share a rentals calendar — a block on rental slot A must
        hide the same window on rental slot B.
    Without `scope` only product-scoped + global (product_id=None) blocks
    are subtracted (historic behaviour preserved for any caller that didn't
    opt in).
    """
    from database import availability_rules_collection, blocked_slots_collection

    default_duration = int(
        (metadata or {}).get("duration_minutes")
        or (metadata or {}).get("slot_duration_minutes")
        or 60
    )

    # Fetch all availability rules scoped to this product OR global.
    rules = await availability_rules_collection.find(
        {"organization_id": org_id,
         "$or": [{"product_id": product_id}, {"product_id": None}]},
        {"_id": 0},
    ).to_list(1000)

    # Onda 15 — "Usa calendario standard" fallback. When the product has no
    # rules of its own AND admin opted into default schedule, synthesize a
    # permissive 7-day weekly schedule. The rest of the generator (blocked-
    # slot subtraction, per-day materialization) runs unchanged.
    if not rules and bool((metadata or {}).get("use_default_schedule")):
        rules = [
            {
                "day_of_week": dow,  # 0=Mon .. 6=Sun
                "start_time": "09:00",
                "end_time": "18:00",
                "slot_duration_minutes": default_duration,
                "product_id": product_id,
                "organization_id": org_id,
            }
            for dow in range(7)
        ]

    if not rules:
        return default_duration, []

    today = _date.today()
    now = _dt.now()
    all_slots: List[Dict[str, str]] = []

    for offset in range(days):
        day = today + timedelta(days=offset)
        weekday = day.weekday()  # Mon=0 .. Sun=6
        day_iso = day.isoformat()

        # Pre-load blocked slots for this day (single query per day). Include
        # both product-scoped and global (product_id=None) blocks so admin-
        # placed holiday blocks mask the schedule as expected. When `scope`
        # is provided, also include any block that shares the same scope
        # regardless of product (cross-product agenda / rentals overlap).
        #
        # Legacy-compat (added when slot_generator first reached production):
        # rows created by older deploys do not carry the `scope` field.
        # When the caller asks for scope="agenda" we treat unscoped rows
        # whose reason is agenda-relevant (booking/event/personal/holiday)
        # as if they had been tagged scope="agenda". Without this branch a
        # service booking confirmed on product A — saved before scope was
        # rolled out — would fail to mask the same time on product B.
        blocked_query: Dict[str, Any] = {
            "organization_id": org_id,
            "date": day_iso,
        }
        or_clauses: List[Dict[str, Any]] = [
            {"product_id": product_id},
            {"product_id": None},
        ]
        if scope:
            or_clauses.append({"scope": scope})
            if scope == "agenda":
                # `{scope: None}` matches both null and missing in MongoDB,
                # so this single clause covers every legacy row shape.
                or_clauses.append({
                    "scope": None,
                    "reason": {"$in": list(_AGENDA_REASONS)},
                })
        blocked_query["$or"] = or_clauses
        blocked = await blocked_slots_collection.find(
            blocked_query,
            {"_id": 0, "start_time": 1, "end_time": 1},
        ).to_list(1000)

        for rule in rules:
            if rule.get("day_of_week") != weekday:
                continue
            slot_dur = int(rule.get("slot_duration_minutes") or default_duration)
            start_str = rule.get("start_time") or "09:00"
            end_str = rule.get("end_time") or "18:00"
            sh, sm = _parse_hhmm(start_str)
            eh, em = _parse_hhmm(end_str)
            cursor_dt = _dt(day.year, day.month, day.day, sh, sm)
            end_dt = _dt(day.year, day.month, day.day, eh, em)

            while cursor_dt + timedelta(minutes=slot_dur) <= end_dt:
                slot_start = cursor_dt.strftime("%H:%M")
                slot_end = (cursor_dt + timedelta(minutes=slot_dur)).strftime("%H:%M")
                # Skip past slots on today
                if day == today and cursor_dt <= now:
                    cursor_dt += timedelta(minutes=slot_dur)
                    continue
                overlaps = any(
                    _overlaps(
                        slot_start, slot_end,
                        b.get("start_time", ""), b.get("end_time", ""),
                    )
                    for b in blocked
                )
                if not overlaps:
                    all_slots.append({
                        "date": day_iso,
                        "start_time": slot_start,
                        "end_time": slot_end,
                    })
                cursor_dt += timedelta(minutes=slot_dur)

    return default_duration, all_slots


# ── Onda 17 — availability windows (continuous free intervals) ──────────────


def _hhmm_to_min(s: str) -> int:
    """Parse 'HH:MM' → minutes from midnight. Returns 0 on bad input."""
    try:
        h, m = s.split(":", 1)
        return int(h) * 60 + int(m)
    except Exception:
        return 0


def _subtract_intervals(
    free: List[Tuple[int, int]],
    blocked: List[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """Subtract `blocked` intervals from `free` intervals.

    Inputs/outputs are `(start_minute, end_minute)` tuples with half-open
    semantics `[start, end)`. Returns the set of free sub-intervals remaining
    after every blocked interval has been carved out. Intervals with zero
    width are dropped.
    """
    result = list(free)
    for bs, be in blocked:
        if be <= bs:
            continue
        next_result: List[Tuple[int, int]] = []
        for fs, fe in result:
            if be <= fs or bs >= fe:
                # No overlap — keep as-is.
                next_result.append((fs, fe))
                continue
            # Left remainder.
            if bs > fs:
                next_result.append((fs, bs))
            # Right remainder.
            if be < fe:
                next_result.append((be, fe))
        result = next_result
    return [(s, e) for (s, e) in result if e > s]


def _merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Union overlapping/adjacent `[start, end)` intervals."""
    if not intervals:
        return []
    items = sorted(intervals)
    merged: List[Tuple[int, int]] = [items[0]]
    for s, e in items[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged


async def generate_availability_windows(
    *,
    org_id: str,
    product_id: str,
    metadata: Dict[str, Any],
    days: int = 30,
) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """Return free availability windows for a rental+slot picker.

    Shape:
        (
            { "min_duration_minutes": int,
              "step_minutes": int,
              "max_duration_minutes": int | None,
              "default_duration_minutes": int },
            [ {"date": "YYYY-MM-DD", "windows": [{"start": "HH:MM", "end": "HH:MM"}, ...]}, ... ],
        )

    The caller (Onda 17 rental+slot storefront) picks any `[start, end)`
    inside these continuous windows, with duration constrained by the
    returned min/step/max. The windows are the UNION of availability_rules
    for each day, MINUS the blocked_slots intervals that overlap the same
    product or are global (product_id=None).

    Back-compat with the fixed-grid endpoint is preserved: `generate_available_slots`
    is untouched and still serves Service + legacy rental+slot clients.
    """
    from database import availability_rules_collection, blocked_slots_collection

    meta = metadata or {}
    default_duration = int(
        meta.get("duration_minutes")
        or meta.get("slot_duration_minutes")
        or 60
    )
    # Fallback policy: when min/step/max are not set, degrade to fixed-grid
    # behaviour by using the (legacy) slot_duration_minutes for all three.
    # This keeps a legacy product (admin never set the new fields) visually
    # equivalent to the old fixed-grid picker after the switch to windows.
    min_duration = int(meta.get("slot_min_duration_minutes") or default_duration)
    step_minutes = int(meta.get("slot_step_minutes") or default_duration)
    raw_max = meta.get("slot_max_duration_minutes")
    # None => unlimited (landing caps to the window size)
    max_duration: Optional[int] = int(raw_max) if raw_max else None

    config = {
        "min_duration_minutes": max(5, min_duration),
        "step_minutes": max(5, step_minutes),
        "max_duration_minutes": max_duration,
        "default_duration_minutes": default_duration,
    }

    rules = await availability_rules_collection.find(
        {"organization_id": org_id,
         "$or": [{"product_id": product_id}, {"product_id": None}]},
        {"_id": 0},
    ).to_list(1000)

    # Onda 15 default-schedule fallback — same as generate_available_slots.
    if not rules and bool(meta.get("use_default_schedule")):
        rules = [
            {
                "day_of_week": dow,
                "start_time": "09:00",
                "end_time": "18:00",
                "slot_duration_minutes": default_duration,
                "product_id": product_id,
                "organization_id": org_id,
            }
            for dow in range(7)
        ]

    if not rules:
        return config, []

    today = _date.today()
    now = _dt.now()
    now_minutes = now.hour * 60 + now.minute
    windows_by_day: List[Dict[str, Any]] = []

    for offset in range(days):
        day = today + timedelta(days=offset)
        weekday = day.weekday()
        day_iso = day.isoformat()

        # Collect all rule windows matching this weekday.
        free_intervals: List[Tuple[int, int]] = []
        for rule in rules:
            if rule.get("day_of_week") != weekday:
                continue
            s = _hhmm_to_min(rule.get("start_time") or "09:00")
            e = _hhmm_to_min(rule.get("end_time") or "18:00")
            if e > s:
                free_intervals.append((s, e))
        if not free_intervals:
            continue
        free_intervals = _merge_intervals(free_intervals)

        # Subtract the "past" portion of today so the customer cannot select a
        # window that has already started.
        if day == today and now_minutes > 0:
            free_intervals = _subtract_intervals(free_intervals, [(0, now_minutes)])
            if not free_intervals:
                continue

        # Subtract blocked slots (any blocking reason — booking/event/rental/
        # personal/holiday — mirroring booking_availability's conservative set).
        blocked_rows = await blocked_slots_collection.find(
            {"organization_id": org_id, "date": day_iso,
             "reason": {"$in": ["booking", "event", "rental", "personal", "holiday"]},
             "$or": [{"product_id": product_id}, {"product_id": None},
                     {"product_id": {"$exists": False}}]},
            {"_id": 0, "start_time": 1, "end_time": 1},
        ).to_list(1000)
        blocked_intervals: List[Tuple[int, int]] = []
        for b in blocked_rows:
            bs = _hhmm_to_min(b.get("start_time") or "")
            be = _hhmm_to_min(b.get("end_time") or "")
            if be > bs:
                blocked_intervals.append((bs, be))

        free_intervals = _subtract_intervals(free_intervals, blocked_intervals)
        if not free_intervals:
            continue

        # Drop windows that cannot even fit the minimum duration.
        min_d = config["min_duration_minutes"]
        free_intervals = [(s, e) for (s, e) in free_intervals if (e - s) >= min_d]
        if not free_intervals:
            continue

        windows_by_day.append({
            "date": day_iso,
            "windows": [
                {"start": _minutes_to_hhmm(s), "end": _minutes_to_hhmm(e)}
                for (s, e) in free_intervals
            ],
        })

    return config, windows_by_day


async def get_rental_blocked_dates(
    org_id: str, product_id: str, date_from: str, date_to: str,
) -> List[str]:
    """R3 — date occupate (reason rental/booking/manual) per un prodotto rental
    nella finestra [date_from, date_to]. Sorgente UNICA per storefront ed embed
    (advisory UX: il guard atomico a confirm-time resta la verita').
    Date come stringhe YYYY-MM-DD → sort lessicale == cronologico.
    """
    from database import blocked_slots_collection

    cursor = blocked_slots_collection.find(
        {
            "organization_id": org_id,
            "product_id": product_id,
            "date": {"$gte": date_from, "$lte": date_to},
            "reason": {"$in": ["rental", "booking", "manual"]},
        },
        {"_id": 0, "date": 1},
    )
    seen: set = set()
    async for doc in cursor:
        d = doc.get("date")
        if d:
            seen.add(d)
    return sorted(seen)
