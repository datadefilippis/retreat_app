"""
reservation_availability.py — unified facade over rental + slot availability.

Onda 16 (Prenotazione consolidation). Wraps the two existing atomic
reservation primitives (try_reserve_rental_range + try_reserve_booking_slot)
behind a single flavor-aware API, so the order_service and validators can
dispatch without knowing which item_type lives underneath.

DESIGN
  - Pure dispatch layer. No new reservation logic.
  - Preserves the existing (ok, status_code, detail) tuple contract.
  - Mirrors the release_for_order pattern.

WHY NOT COLLAPSE INTO ONE FILE
  rental_availability (full-day blocks) and booking_availability (hh:mm
  windows) have distinct MongoDB overlap semantics. Keeping them as
  separate implementations avoids merging two subtle concurrency proofs
  into one. This facade is the user-facing API; internals stay apart.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


async def try_reserve(
    *,
    flavor: str,
    order_id: str,
    org_id: str,
    product_id: str,
    # Range fields
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    # Slot fields
    slot_date: Optional[str] = None,
    slot_start_time: Optional[str] = None,
    slot_end_time: Optional[str] = None,
    note: Optional[str] = None,
    store_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Reserve a reservation by flavor.

    flavor="range" dispatches to rental_availability.try_reserve_rental_range
    flavor="slot"  dispatches to booking_availability.try_reserve_booking_slot

    Returns the underlying primitive's (ok, status_code, detail) tuple
    unchanged.
    """
    if flavor == "range":
        from services.rental_availability import try_reserve_rental_range
        if not date_from:
            return False, "missing_date_from", None
        return await try_reserve_rental_range(
            order_id=order_id,
            org_id=org_id,
            product_id=product_id,
            date_from=date_from,
            date_to=date_to,
            note=note,
            store_id=store_id,
        )
    if flavor == "slot":
        from services.booking_availability import try_reserve_booking_slot
        if not (slot_date and slot_start_time and slot_end_time):
            return False, "missing_slot_fields", None
        return await try_reserve_booking_slot(
            order_id=order_id,
            org_id=org_id,
            product_id=product_id,
            date=slot_date,
            start_time=slot_start_time,
            end_time=slot_end_time,
            note=note,
            store_id=store_id,
        )
    return False, "unknown_flavor", {"flavor": flavor}


async def check_available(
    *,
    flavor: str,
    org_id: str,
    product_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    slot_date: Optional[str] = None,
    slot_start_time: Optional[str] = None,
    slot_end_time: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Advisory pre-flight availability check (no side effects)."""
    if flavor == "range":
        from services.rental_availability import check_rental_range_available
        if not date_from:
            return False, "missing_date_from", None
        return await check_rental_range_available(
            org_id=org_id,
            product_id=product_id,
            date_from=date_from,
            date_to=date_to,
        )
    if flavor == "slot":
        from services.booking_availability import check_booking_slot_available
        if not (slot_date and slot_start_time and slot_end_time):
            return False, "missing_slot_fields", None
        return await check_booking_slot_available(
            org_id=org_id,
            product_id=product_id,
            date=slot_date,
            start_time=slot_start_time,
            end_time=slot_end_time,
        )
    return False, "unknown_flavor", {"flavor": flavor}


async def release_for_order(order_id: str, org_id: str) -> int:
    """Release every blocked_slots row tied to this order (both flavors).

    Runs both releases; returns total rows deleted. Safe + idempotent.
    """
    from services.rental_availability import release_rental_range
    from services.booking_availability import release_booking_slot

    n1 = await release_rental_range(order_id=order_id, org_id=org_id)
    n2 = await release_booking_slot(order_id=order_id, org_id=org_id)
    return (n1 or 0) + (n2 or 0)


def derive_flavor(product: Dict[str, Any]) -> Optional[str]:
    """Derive reservation_flavor from a product document.

    Precedence:
      1. Explicit metadata.reservation_flavor (range | slot)
      2. Legacy item_type=booking → slot
      3. item_type=rental with unit in {giorno,settimana,mese} → range
      4. item_type=rental with unit=ora or missing → slot
      5. Anything else → None (not a reservation)
    """
    meta = product.get("metadata") or {}
    flavor = meta.get("reservation_flavor")
    if flavor in ("range", "slot"):
        return flavor

    item_type = product.get("item_type")
    if item_type == "booking":
        return "slot"
    if item_type == "rental":
        unit = meta.get("rental_unit")
        if unit in ("giorno", "settimana", "mese"):
            return "range"
        return "slot"
    return None
