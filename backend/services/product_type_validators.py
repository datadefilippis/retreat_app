"""
Centralized per-type order validators.

Before this module, order validation for the 5 product types was
scattered:

  - routers/public.py:422-467 held inline if/elif chains with type-
    specific required fields (event_ticket occurrence_id, rental dates,
    booking date+time).
  - services/commerce_rules.validate_occurrence_for_order performed the
    event_ticket deep check (status + capacity).
  - Error messages were inlined as magic-string maps in the router.

Adding a type required touching both files; modifying a type risked
leaving one branch untouched. This module consolidates the per-type
checks behind one entry point:

    await validate_order_item(item, product, ctx)

Returns a ValidationResult dataclass the caller translates to an
HTTPException (or whatever transport it wants).

Design contract:
  - PURE per-type functions. Each validator gets the order item + the
    product snapshot + a context dict. No HTTP imports, no exceptions
    raised — caller decides how to surface failure.
  - Driven by the product_types registry. Dispatch is a simple dict
    lookup; adding a 6th type means adding one function + one entry.
  - Idempotent and side-effect-free. Validators never mutate state;
    they only read (from Mongo via commerce_rules for event_ticket,
    from the provided product dict for everything else).
  - Reason codes are stable strings. The router maps them to human
    messages (keeps i18n concerns at the boundary, not here).

Reason codes (stable, machine-readable):
  ok                                — validation passed
  occurrence_id_required
  occurrence_not_found
  occurrence_cancelled
  occurrence_closed
  occurrence_not_published
  occurrence_sold_out
  occurrence_status_invalid:<s>
  rental_date_from_required
  rental_date_range_invalid
  booking_slot_incomplete
  unknown_item_type
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Outcome of a single order-item validation.

    valid      : True when the item is orderable as configured.
    reason     : Stable machine code. "ok" on success; a type-specific
                 string on failure (see module docstring for the list).
    detail     : Optional human-readable context, typically used to
                 include the offending id or value in the error. The
                 caller composes the final user-facing message.
    context    : Optional extra data (e.g. the occurrence dict when
                 capacity info is available) that callers may want to
                 surface in structured responses. Never contains PII.
    """

    valid: bool
    reason: str
    detail: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


# ── Per-type validators (pure, async-safe) ──────────────────────────────────


async def _validate_physical(item, product, ctx) -> ValidationResult:
    """Physical goods gained a stock pre-flight in P10.

    When org_id + product_id + qty are all present, consults
    stock_service.check_stock_available. The pre-flight is advisory —
    it can false-negative under a hot race. The AUTHORITATIVE check
    happens atomically at confirm time via try_decrement_stock, which
    will refuse to decrement past zero regardless of what the validator
    saw.

    Backward-compat: products without stock_quantity tracked always
    return "untracked" and the validator passes — no behavior change
    for merchants who have not opted into stock tracking.
    """
    from services.stock_service import check_stock_available

    org_id = ctx.get("org_id")
    product_id = getattr(item, "product_id", None) or (product or {}).get("id")
    try:
        qty = int(getattr(item, "quantity", 1) or 1)
    except Exception:
        qty = 1

    if org_id and product_id and qty > 0:
        status, remaining = await check_stock_available(org_id, product_id, qty)
        if status == "insufficient":
            return ValidationResult(
                valid=False,
                reason="insufficient_stock",
                detail=f"richiesti {qty}, disponibili {remaining}",
                context={"remaining": remaining, "requested": qty},
            )
        # "available" / "untracked" / "not_found" → pass. not_found is
        # handled upstream by the order-creation path (caller validates
        # product existence before this point); the validator stays
        # minimal to avoid double-erroring.
    return ValidationResult(valid=True, reason="ok")


async def _validate_service(item, product, ctx) -> ValidationResult:
    """Service validation (F5 Onda 12).

    A service product may have:
      - availability_rules (stored in `availability_rules` collection,
        scoped by product_id): when present, the customer must supply
        booking_date + start_time + end_time and the slot must be free.
      - service_options (stored in `service_options` collection): when
        any active option exists, the customer must pick exactly one
        via `service_option_id`. The option must belong to this product
        and be active.

    Legacy services (no availability_rules, no options) continue to
    work: the validator returns ok. They behave like a generic request
    product — merchant handles scheduling manually.
    """
    from database import service_options_collection, availability_rules_collection
    from services.booking_availability import check_booking_slot_available

    org_id = ctx.get("org_id")
    product_id = getattr(item, "product_id", None) or (product or {}).get("id")

    # 1) Service option enforcement
    option_id = getattr(item, "service_option_id", None)
    has_active_options = await service_options_collection.find_one(
        {"organization_id": org_id, "product_id": product_id, "is_active": True},
        {"_id": 0, "id": 1},
    )
    if has_active_options:
        if not option_id:
            return ValidationResult(
                valid=False,
                reason="service_option_required",
                detail=str(product_id),
            )
        option = await service_options_collection.find_one(
            {"id": option_id, "organization_id": org_id, "product_id": product_id},
            {"_id": 0},
        )
        if not option:
            return ValidationResult(
                valid=False,
                reason="service_option_not_found",
                detail=str(option_id),
            )
        if not option.get("is_active", True):
            return ValidationResult(
                valid=False,
                reason="service_option_inactive",
                detail=option.get("label") or str(option_id),
                context={"option": option},
            )

    # 2) Availability slot enforcement
    # If the merchant configured any availability_rule for this product,
    # we treat the service as "bookable" and require a slot at order time.
    #
    # Onda 14 Parte B — hybrid mode: when
    # metadata.service_allow_custom_request is True AND the customer marks
    # the order-item with service_custom_request=True, the booking slot
    # does NOT need to match an active rule. We still require date+start
    # +end (so the admin can see what was proposed) and still reject hard
    # conflicts with already-reserved slots — but the rule-window check
    # is skipped. The admin confirms manually afterwards, at which point
    # _sync_calendar_blocks reserves the slot atomically.
    has_rules = await availability_rules_collection.find_one(
        {"organization_id": org_id, "product_id": product_id},
        {"_id": 0, "id": 1},
    )
    meta = (product or {}).get("metadata") or {}
    allow_custom = bool(meta.get("service_allow_custom_request"))
    is_custom_request = bool(getattr(item, "service_custom_request", False))
    # Onda 15 — "Usa calendario ufficiale". When the admin opted into the
    # default schedule, treat the service as bookable even without
    # explicit rules in the DB: slot is required and blocked_slots
    # collisions still reject. The synthetic rules live in the public
    # slot endpoint; here we just need to enforce "slot required +
    # collision-free" as if rules existed.
    use_default_schedule = bool(meta.get("use_default_schedule"))

    if has_rules or use_default_schedule:
        bd = getattr(item, "booking_date", None)
        bs = getattr(item, "booking_start_time", None)
        be = getattr(item, "booking_end_time", None)
        if not bd or not bs or not be:
            # When custom request is allowed on the product, a totally
            # missing slot is NOT a hard error — admin can schedule
            # post-purchase. Only enforce slot presence for strict mode.
            if not allow_custom:
                return ValidationResult(
                    valid=False,
                    reason="service_slot_required",
                    detail=str(product_id),
                )
        else:
            # Onda 15 — "calendario standard": no window restriction.
            # The admin governs availability purely through blocked_slots
            # on the calendar; we enforce slot presence + collision-free
            # against existing bookings (check below), nothing else.

            available, reason, conflict = await check_booking_slot_available(
                org_id, product_id, bd, bs, be,
            )
            if not available:
                # Hybrid mode: if the reason is "no rule matches" and the
                # product allows custom requests with the flag set, swallow
                # the failure. Hard conflicts (slot already taken) still
                # reject.
                strict_reject = reason in ("slot_conflict",) or not (allow_custom and is_custom_request)
                if strict_reject:
                    return ValidationResult(
                        valid=False,
                        reason="service_slot_conflict",
                        detail=f"{bd} {bs}-{be}",
                        context={"conflict": conflict, "underlying_reason": reason},
                    )
    else:
        # No rules configured. If the merchant allows custom requests and
        # the customer sent one, let it through with date+start+end. If
        # the customer sent nothing, still accept — admin schedules later.
        if allow_custom and is_custom_request:
            bd = getattr(item, "booking_date", None)
            bs = getattr(item, "booking_start_time", None)
            be = getattr(item, "booking_end_time", None)
            if bd and bs and be:
                # Still ensure the proposed slot doesn't already collide
                # with another reserved slot, to avoid double-booking.
                available, reason, conflict = await check_booking_slot_available(
                    org_id, product_id, bd, bs, be,
                )
                if not available and reason == "slot_conflict":
                    return ValidationResult(
                        valid=False,
                        reason="service_slot_conflict",
                        detail=f"{bd} {bs}-{be}",
                        context={"conflict": conflict, "underlying_reason": reason},
                    )

    return ValidationResult(valid=True, reason="ok")


async def _validate_rental(item, product, ctx) -> ValidationResult:
    """Rental validation is flavor-aware (Onda 16 + Onda 17).

    Two flavors live under item_type="rental":

      - flavor=range: multi-day date range (B&B, cars, equipment). Requires
        rental_date_from; rental_date_to optional but must be >= from.

      - flavor=slot: single time-window reservation, same-day or cross-day
        (meeting rooms, courts, ora-per-ora). Requires booking_date +
        booking_start_time + booking_end_time. booking_end_date optional —
        when absent, defaults to booking_date (same-day semantics).

    The flavor is read from product.metadata.reservation_flavor. Legacy
    rental products created before Onda 16 have no flavor set: if they
    carry rental_unit='ora' we treat them as slot, otherwise range —
    this mirrors the derive_flavor rule used by the frontend landing.

    P8 pre-flight: for range we advisory-check the calendar; for slot we
    run the same availability check as bookings. The authoritative
    reservation still happens atomically at confirm time
    (try_reserve_rental_range for range, try_reserve_booking_slot_range
    for slot).
    """
    meta = (product or {}).get("metadata") or {}
    flavor = (meta.get("reservation_flavor") or "").lower()
    if flavor not in ("range", "slot"):
        # Legacy product without explicit flavor: infer from rental_unit.
        flavor = "slot" if (meta.get("rental_unit") or "").lower() == "ora" else "range"

    if flavor == "slot":
        bd = getattr(item, "booking_date", None)
        bs = getattr(item, "booking_start_time", None)
        be = getattr(item, "booking_end_time", None)
        if not (bd and bs and be):
            return ValidationResult(
                valid=False,
                reason="booking_slot_incomplete",
                detail=str(getattr(item, "product_id", "") or ""),
            )
        bd_end = getattr(item, "booking_end_date", None) or bd
        if bd_end < bd:
            return ValidationResult(
                valid=False,
                reason="rental_date_range_invalid",
                detail=str(getattr(item, "product_id", "") or ""),
            )

        # Advisory overlap check. Same-day uses the single-slot primitive;
        # cross-day is left to the atomic guard at confirm (a conservative
        # overlap scan across N days would double the validator latency
        # without a strong win — the guard is the source of truth).
        org_id = ctx.get("org_id")
        product_id = getattr(item, "product_id", None) or (product or {}).get("id")
        if org_id and product_id and bd == bd_end:
            from services.booking_availability import check_booking_slot_available
            available, reason, conflict = await check_booking_slot_available(
                org_id, product_id, bd, bs, be,
            )
            if not available and reason == "slot_conflict":
                return ValidationResult(
                    valid=False,
                    reason="service_slot_conflict",
                    detail=f"{bd} {bs}-{be}",
                    context={"conflict": conflict, "underlying_reason": reason},
                )
        return ValidationResult(valid=True, reason="ok")

    # ── Range flavor (legacy default) ───────────────────────────────────
    date_from = getattr(item, "rental_date_from", None)
    if not date_from:
        return ValidationResult(
            valid=False,
            reason="rental_date_from_required",
            detail=str(getattr(item, "product_id", "") or ""),
        )
    date_to = getattr(item, "rental_date_to", None)
    if date_to and date_to < date_from:
        return ValidationResult(
            valid=False,
            reason="rental_date_range_invalid",
            detail=str(getattr(item, "product_id", "") or ""),
        )

    # P8: advisory availability check. Skipped when org/product context
    # is missing (e.g. dry-run/unit-test path) so the validator stays
    # callable without a live DB.
    from services.rental_availability import check_rental_range_available

    org_id = ctx.get("org_id")
    product_id = getattr(item, "product_id", None) or (product or {}).get("id")
    if org_id and product_id:
        available, reason, conflict = await check_rental_range_available(
            org_id, product_id, date_from, date_to or date_from,
        )
        if not available:
            return ValidationResult(
                valid=False,
                reason=reason,   # "rental_day_conflict" or "invalid_date_range"
                detail=f"{date_from}..{date_to or date_from}",
                context={"conflict": conflict} if conflict else None,
            )

    return ValidationResult(valid=True, reason="ok")


async def _validate_event_ticket(item, product, ctx) -> ValidationResult:
    """Event ticket requires an occurrence_id and the occurrence must
    be published + have remaining capacity when capacity is enforced.

    E1 extension: when the item carries a ticket_tier_id, the tier must
    exist, belong to the requested occurrence, be active, and have
    remaining seats for the requested qty.

    Delegates the occurrence deep check to commerce_rules.validate_occurrence_for_order
    so capacity / status logic stays in one place.
    """
    occurrence_id = getattr(item, "occurrence_id", None)
    if not occurrence_id:
        return ValidationResult(
            valid=False,
            reason="occurrence_id_required",
            detail=str(getattr(item, "product_id", "") or ""),
        )

    from services.commerce_rules import validate_occurrence_for_order

    org_id = ctx.get("org_id")
    product_id = getattr(item, "product_id", None) or (product or {}).get("id")
    qty = getattr(item, "quantity", 1) or 1

    valid, reason, occ = await validate_occurrence_for_order(
        occurrence_id, org_id, product_id, qty,
    )
    if not valid:
        return ValidationResult(
            valid=False,
            reason=reason,
            detail=occurrence_id,
            context={"occurrence": occ} if occ else None,
        )

    # E1: tier pre-flight
    tier_id = getattr(item, "ticket_tier_id", None)
    if tier_id:
        from database import event_ticket_tiers_collection
        tier = await event_ticket_tiers_collection.find_one(
            {"id": tier_id, "organization_id": org_id},
            {"_id": 0},
        )
        if not tier or tier.get("occurrence_id") != occurrence_id:
            return ValidationResult(
                valid=False,
                reason="tier_not_found",
                detail=tier_id,
            )
        if not tier.get("is_active", True):
            return ValidationResult(
                valid=False,
                reason="tier_inactive",
                detail=tier.get("label") or tier_id,
                context={"tier": tier},
            )
        cap = tier.get("capacity")
        if cap is not None:
            used = int(tier.get("reserved_seats") or 0)
            remaining = max(0, cap - used)
            try:
                req = int(qty)
            except Exception:
                req = 1
            if remaining < req:
                return ValidationResult(
                    valid=False,
                    reason="tier_sold_out",
                    detail=tier.get("label") or tier_id,
                    context={"tier": tier, "remaining": remaining, "requested": req},
                )

    # F1 (Onda 8) — attendee details policy
    # When product.metadata.requires_attendee_details is True, the customer
    # must supply one AttendeeInfo per seat. Each entry is a pydantic model
    # on OrderRequestItem (already Email-validated by pydantic), so here we
    # just check presence + length consistency with the quantity.
    meta = (product or {}).get("metadata") or {}
    if meta.get("requires_attendee_details"):
        attendees = getattr(item, "attendees", None)
        if not attendees:
            return ValidationResult(
                valid=False,
                reason="attendees_required",
                detail=str(getattr(item, "product_id", "") or ""),
            )
        try:
            req_qty = int(qty)
        except Exception:
            req_qty = 1
        if len(attendees) != req_qty:
            return ValidationResult(
                valid=False,
                reason="attendees_count_mismatch",
                detail=f"atteso {req_qty}, ricevuto {len(attendees)}",
                context={"expected": req_qty, "received": len(attendees)},
            )

        # F2 (Onda 9) — configurable contact required-ness + custom fields.
        # Defaults preserve F1 behavior: email required, phone optional.
        require_email = bool(meta.get("require_attendee_email", True))
        require_phone = bool(meta.get("require_attendee_phone", False))
        attendee_field_cfg = meta.get("attendee_fields") or []
        required_custom = [f for f in attendee_field_cfg if f.get("required")]

        for idx, a in enumerate(attendees):
            # Pydantic models -> dict-like via model_dump; dicts pass through.
            if hasattr(a, "model_dump"):
                a_dict = a.model_dump()
            elif isinstance(a, dict):
                a_dict = a
            else:
                a_dict = {"name": getattr(a, "name", None), "email": getattr(a, "email", None),
                          "phone": getattr(a, "phone", None),
                          "custom_fields": getattr(a, "custom_fields", {}) or {}}

            if require_email and not (a_dict.get("email") or "").strip():
                return ValidationResult(
                    valid=False,
                    reason="attendees_missing_email",
                    detail=f"biglietto {idx + 1}",
                )
            if require_phone and not (a_dict.get("phone") or "").strip():
                return ValidationResult(
                    valid=False,
                    reason="attendees_missing_phone",
                    detail=f"biglietto {idx + 1}",
                )

            cfs = a_dict.get("custom_fields") or {}
            for fc in required_custom:
                fid = fc.get("id")
                if not fid:
                    continue
                val = cfs.get(fid)
                # Non-empty check: text/textarea -> trim != ""; number -> not None
                empty = (val is None) or (isinstance(val, str) and val.strip() == "")
                if empty:
                    return ValidationResult(
                        valid=False,
                        reason="attendees_missing_custom_field",
                        detail=fc.get("label") or fid,
                        context={"field_id": fid, "attendee_index": idx},
                    )

    # F2 Onda 9 — order-level required custom fields (validated per item;
    # they're really per-order so we'd ideally check them once at a
    # higher layer, but checking here is equivalent and keeps the
    # validator self-contained — duplicates are cheap).
    order_field_cfg = meta.get("order_fields") or []
    required_order = [f for f in order_field_cfg if f.get("required")]
    if required_order:
        order_vals = ctx.get("order_fields") or {}
        for fc in required_order:
            fid = fc.get("id")
            if not fid:
                continue
            val = order_vals.get(fid)
            empty = (val is None) or (isinstance(val, str) and val.strip() == "")
            if empty:
                return ValidationResult(
                    valid=False,
                    reason="order_missing_custom_field",
                    detail=fc.get("label") or fid,
                    context={"field_id": fid},
                )

    return ValidationResult(valid=True, reason="ok")


async def _validate_booking(item, product, ctx) -> ValidationResult:
    """Booking requires a date and a start/end time slot, AND the slot
    must not conflict with an already-reserved window (P5).

    The conflict check is a pre-flight read: it can false-negative
    under a hot race. The AUTHORITATIVE reservation happens atomically
    at order creation via try_reserve_booking_slot — this method just
    gives the storefront an early, friendlier 'slot taken' response
    before we take a write lock.
    """
    bd = getattr(item, "booking_date", None)
    bs = getattr(item, "booking_start_time", None)
    be = getattr(item, "booking_end_time", None)
    if not bd or not bs or not be:
        return ValidationResult(
            valid=False,
            reason="booking_slot_incomplete",
            detail=str(getattr(item, "product_id", "") or ""),
        )

    # P5 pre-flight availability. Defensive: a failure of this check
    # returns the structured reason the storefront can turn into
    # "questo orario non è più disponibile, scegline un altro".
    from services.booking_availability import check_booking_slot_available

    org_id = ctx.get("org_id")
    product_id = getattr(item, "product_id", None) or (product or {}).get("id")
    if org_id and product_id:
        available, reason, conflict = await check_booking_slot_available(
            org_id, product_id, bd, bs, be,
        )
        if not available:
            return ValidationResult(
                valid=False,
                reason=reason,   # "slot_conflict" or "invalid_time_window"
                detail=f"{bd} {bs}-{be}",
                context={"conflict": conflict} if conflict else None,
            )

    return ValidationResult(valid=True, reason="ok")


# ── Dispatch table ──────────────────────────────────────────────────────────


# Keyed by item_type. Stays in sync with the registry via explicit entries.
# A missing key (e.g. a brand-new type before its validator is written)
# returns ValidationResult(valid=False, reason="unknown_item_type") so
# the caller does not silently accept unvalidated items.
async def _validate_digital(item, product, ctx) -> ValidationResult:
    """Digital goods validator — Release 3 B6.

    Two checks, both advisory at order-create time (the authoritative
    guards are `upload_digital_file` rejecting missing payloads, and
    `stock_service.try_decrement_stock` at confirm):

      1. The admin must have uploaded a file. `metadata.download_filename`
         is set by the upload endpoint; its absence means the product is
         misconfigured and we MUST NOT let a customer pay for a ghost link.

      2. If the merchant capped inventory via `stock_quantity`, the
         request must not exceed the remaining count. Same contract as
         physical: untracked products always pass this check.
    """
    from services.stock_service import check_stock_available

    meta = (product or {}).get("metadata") or {}
    if not meta.get("download_filename"):
        return ValidationResult(
            valid=False,
            reason="digital_file_missing",
            detail=str(getattr(item, "product_id", "") or ""),
        )

    org_id = ctx.get("org_id")
    product_id = getattr(item, "product_id", None) or (product or {}).get("id")
    try:
        qty = int(getattr(item, "quantity", 1) or 1)
    except Exception:
        qty = 1

    if org_id and product_id and qty > 0:
        status, remaining = await check_stock_available(org_id, product_id, qty)
        if status == "insufficient":
            return ValidationResult(
                valid=False,
                reason="insufficient_stock",
                detail=f"richiesti {qty}, disponibili {remaining}",
                context={"remaining": remaining, "requested": qty},
            )

    return ValidationResult(valid=True, reason="ok")


# Release 4 (Courses) — video course validator.
#
# Course products require no stock, no occurrences, no slot. The only
# meaningful precondition at order-create time is that the Course entity
# referenced via `product.metadata.course_id` still exists and is active.
# We intentionally DO NOT enforce "course has at least 1 lesson" or
# "lesson has bunny_video_guid" here because the admin can legitimately
# publish a course incrementally (first lesson being uploaded while the
# pre-sale is open). Those checks are soft-gated on the admin "publish"
# side (SalesCard publish_gate blockers) and at play time (player
# endpoint returns 404 lesson_no_video when the guid is missing).
#
# Quantity is hard-capped at 1: a course is licensed nominatively, not
# per-seat. Sending quantity > 1 is normalized to 1 rather than
# rejected — better UX than a hard 400.
async def _validate_course(item, product, ctx) -> ValidationResult:
    from database import courses_collection

    meta = (product or {}).get("metadata") or {}
    course_id = meta.get("course_id")
    if not course_id:
        return ValidationResult(
            valid=False,
            reason="course_not_linked",
            detail="product.metadata.course_id missing",
        )

    org_id = ctx.get("org_id") or (product or {}).get("organization_id")
    course = await courses_collection.find_one(
        {"id": course_id, "organization_id": org_id, "is_active": True},
        {"_id": 0, "id": 1, "title": 1},
    )
    if not course:
        return ValidationResult(
            valid=False,
            reason="course_unavailable",
            detail=str(course_id),
        )

    return ValidationResult(valid=True, reason="ok")


_VALIDATORS = {
    "physical": _validate_physical,
    "service": _validate_service,
    "rental": _validate_rental,
    "event_ticket": _validate_event_ticket,
    "booking": _validate_booking,
    "digital": _validate_digital,
    "course": _validate_course,
}


async def validate_order_item(item, product: dict, ctx: dict) -> ValidationResult:
    """Validate a single order-item given its resolved product snapshot
    and a context dict (must contain at least `org_id`).

    Returns a ValidationResult. Callers translate a non-ok reason to an
    HTTPException with their own localized message — this function does
    not speak HTTP.

    Never raises (all validators swallow their own errors and return a
    structured failure). An unexpected internal error surfaces as
    valid=False, reason="validator_internal_error".
    """
    item_type = (product or {}).get("item_type") or "physical"
    fn = _VALIDATORS.get(item_type)
    if fn is None:
        return ValidationResult(
            valid=False,
            reason="unknown_item_type",
            detail=item_type,
        )

    try:
        return await fn(item, product or {}, ctx or {})
    except Exception as exc:
        # Defensive: never allow a validator bug to blow up the request.
        logger.exception(
            "product_type_validators: %s raised during validation: %s",
            item_type, exc,
        )
        return ValidationResult(
            valid=False,
            reason="validator_internal_error",
            detail=str(exc)[:200],
        )


# Stable mapping from reason code → Italian human message. Kept here so
# any consumer (router, CLI, tests) can produce consistent copy.
# The router may still override for i18n or branding.
REASON_MESSAGES_IT = {
    "occurrence_id_required": "occurrence_id è richiesto per un prodotto event_ticket",
    "occurrence_not_found": "Occorrenza non trovata",
    "occurrence_cancelled": "Questa data è stata annullata",
    "occurrence_closed": "Questa data è chiusa",
    "occurrence_not_published": "Questa data non è ancora disponibile",
    "occurrence_sold_out": "Questa data è esaurita",
    "rental_date_from_required": "La data di inizio del noleggio è richiesta",
    "rental_date_range_invalid": "La data di fine noleggio deve essere >= data di inizio",
    "booking_slot_incomplete": "Data, orario di inizio e orario di fine sono richiesti per una prenotazione",
    "slot_conflict": "Questo orario è già stato prenotato. Scegli un altro slot.",
    "invalid_time_window": "L'orario di fine deve essere successivo a quello di inizio.",
    "rental_day_conflict": "Queste date non sono disponibili per il noleggio.",
    "invalid_date_range": "Intervallo di date non valido.",
    "insufficient_stock": "Quantità richiesta non disponibile a magazzino.",
    "tier_not_found": "Tipologia biglietto non trovata.",
    "tier_inactive": "Tipologia biglietto non più disponibile.",
    "tier_sold_out": "Tipologia biglietto esaurita. Scegli un'altra opzione.",
    "attendees_required": "Inserisci i dati per ogni partecipante.",
    "attendees_count_mismatch": "Il numero di partecipanti non corrisponde al numero di biglietti.",
    "attendees_missing_email": "Email del partecipante richiesta.",
    "attendees_missing_phone": "Telefono del partecipante richiesto.",
    "attendees_missing_custom_field": "Campo richiesto per ogni partecipante.",
    "order_missing_custom_field": "Campo ordine richiesto.",
    # F5 Onda 12 — service validation
    "service_option_required": "Scegli un'opzione del servizio.",
    "service_option_not_found": "Opzione del servizio non trovata.",
    "service_option_inactive": "Opzione del servizio non più disponibile.",
    "service_slot_required": "Seleziona data e ora per il servizio.",
    "service_slot_conflict": "Questo orario non è disponibile. Scegli un altro slot.",
    # Release 3 (Digital) — reasons raised by _validate_digital + download flow.
    "digital_file_missing": "Il file digitale non è ancora disponibile per questo prodotto.",
    "download_exhausted": "Hai raggiunto il numero massimo di download.",
    "download_expired": "Il link di download è scaduto.",
    "unknown_item_type": "Tipo prodotto sconosciuto",
    "validator_internal_error": "Errore interno di validazione",
    # Release 4 (Courses)
    "course_not_linked": "Il corso non è collegato correttamente al prodotto. Contatta il merchant.",
    "course_unavailable": "Questo corso non è più disponibile.",
}


def message_for_reason(reason: str, detail: Optional[str] = None) -> str:
    """Return an Italian human message for a reason code. Falls back to
    the raw reason if no canonical translation exists (e.g. occurrence_status_invalid:*
    which encodes a dynamic status). The detail string, when provided,
    is appended in parentheses for traceability.
    """
    # Handle dynamic reason codes with ':' suffix (e.g. occurrence_status_invalid:draft)
    base = reason.split(":", 1)[0] if ":" in reason else reason
    msg = REASON_MESSAGES_IT.get(base, f"Validazione non riuscita: {reason}")
    if detail and base not in ("validator_internal_error",):
        return f"{msg} ({detail})"
    return msg
