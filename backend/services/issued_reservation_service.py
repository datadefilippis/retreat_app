"""
issued_reservation_service.py — Onda 16 Prenotazione consolidation.

Issues IssuedReservation rows after an order is confirmed. Mirrors the
pattern of ticket_service (events) + booking_service (services) but for
rental products in both flavors (range + slot).

Lifecycle:
  issue_for_order(order, org_id)        → called by order_service.confirm_order
                                          AFTER blocked_slots are created and
                                          tickets/bookings are issued.
                                          Idempotent per (order_id, order_line_index).

  release_for_order(order_id, org_id)   → called by order_service.cancel_order
                                          transitions all active reservations
                                          to status="cancelled" (NEVER deletes).

IDEMPOTENCY
  The DB has a unique index on (order_id, order_line_index). On a retry
  of confirm_order the insert raises E11000 and we return the existing
  row. Safe under webhook replays and admin double-clicks.

LINE COVERAGE
  Only lines with item_type in {"rental", "booking"} that successfully
  resolved a flavor via reservation_availability.derive_flavor are
  materialized as IssuedReservation. Rental lines without dates and slot
  lines without time are skipped — those orders wait for the admin to
  schedule a slot manually before a reservation is issued.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

from models.common import utc_now
from models.issued_reservation import IssuedReservation, generate_reservation_code

logger = logging.getLogger(__name__)


def _generate_access_token() -> str:
    """Unguessable URL-safe token for /rsv/{token}. 192-bit entropy."""
    return secrets.token_urlsafe(24)


def _compute_expiry_range(date_to: Optional[str]) -> Optional[str]:
    """Default expiry: date_to + 30 days (rental runs are longer-lived
    than a single appointment so we keep the landing page accessible
    for a while after checkout)."""
    if not date_to:
        return None
    try:
        d = date.fromisoformat(date_to)
        return (d + timedelta(days=30)).isoformat()
    except (TypeError, ValueError):
        return None


def _compute_expiry_slot(slot_date: Optional[str], slot_end_time: Optional[str]) -> Optional[str]:
    """Default expiry: slot end + 14 days."""
    if not slot_date:
        return None
    try:
        t = slot_end_time or "23:59"
        dt = datetime.fromisoformat(f"{slot_date}T{t}:00")
        return (dt + timedelta(days=14)).isoformat()
    except (TypeError, ValueError):
        return None


def _resolve_location(item: Dict[str, Any], product_doc: Optional[Dict[str, Any]]) -> Optional[str]:
    loc = item.get("location") or item.get("rental_notes")
    if loc:
        return loc
    if product_doc:
        meta = product_doc.get("metadata") or {}
        return meta.get("location") or product_doc.get("meeting_link")
    return None


def _build_reservation_doc(
    *,
    org_id: str,
    order: Dict[str, Any],
    line_index: int,
    line: Dict[str, Any],
    flavor: str,
    product_doc: Optional[Dict[str, Any]],
    now: datetime,
) -> Optional[Dict[str, Any]]:
    product_id = line.get("product_id")
    product_name = line.get("product_name") or (product_doc.get("name") if product_doc else "")
    if not (product_id and product_name):
        return None

    customer_name = order.get("customer_name") or ""
    customer_email = order.get("customer_email") or ""
    customer_phone = order.get("customer_phone") or ""

    extras_snapshot = list(line.get("extras") or [])

    if flavor == "range":
        date_from = line.get("rental_date_from")
        if not date_from:
            return None
        date_to = line.get("rental_date_to") or date_from
        expiry = _compute_expiry_range(date_to)
        slot_fields = {
            "date_from": date_from,
            "date_to": date_to,
            "slot_date": None,
            "slot_start_time": None,
            "slot_end_time": None,
            "slot_date_to": None,
        }
    elif flavor == "slot":
        slot_date = line.get("booking_date")
        slot_start = line.get("booking_start_time")
        slot_end = line.get("booking_end_time")
        # Onda 17 — cross-day end date. None / missing → same-day semantics
        # (the reservation ends on slot_date). When populated, the IssuedReservation
        # spans slot_date + slot_start → slot_date_to + slot_end.
        slot_date_to = line.get("booking_end_date")
        if not (slot_date and slot_start and slot_end):
            return None
        # Expiry uses the end day (= slot_date for same-day, slot_date_to for
        # cross-day) so the access link stays valid 14 days after the slot
        # actually finishes.
        expiry = _compute_expiry_slot(slot_date_to or slot_date, slot_end)
        slot_fields = {
            "date_from": None,
            "date_to": None,
            "slot_date": slot_date,
            "slot_start_time": slot_start,
            "slot_end_time": slot_end,
            "slot_date_to": slot_date_to if slot_date_to and slot_date_to != slot_date else None,
        }
    else:
        return None

    reservation = IssuedReservation(
        organization_id=org_id,
        order_id=order["id"],
        order_line_index=line_index,
        product_id=product_id,
        product_name=product_name,
        reservation_flavor=flavor,
        code=generate_reservation_code(),
        access_token=_generate_access_token(),
        access_token_expires_at=expiry,
        status="active",
        extras_snapshot=extras_snapshot,
        holder_name=customer_name or None,
        holder_email=customer_email or None,
        holder_phone=customer_phone or None,
        location=_resolve_location(line, product_doc),
        delivery_status="pending",
        delivery_attempts=0,
        **slot_fields,
    )
    doc = reservation.model_dump(mode="json")
    # Pydantic emits ISO strings for datetimes; MongoDB accepts both.
    return doc


async def issue_for_order(order: Dict[str, Any], org_id: str) -> List[Dict[str, Any]]:
    """Issue IssuedReservation rows for every rental/booking line in `order`.

    Idempotent per (order_id, order_line_index). Returns every reservation
    (newly inserted or pre-existing) associated with the order.
    """
    from database import issued_reservations_collection, products_collection
    from services.reservation_availability import derive_flavor

    order_id = order.get("id")
    if not order_id:
        return []

    existing = await issued_reservations_collection.find(
        {"organization_id": org_id, "order_id": order_id},
        {"_id": 0},
    ).to_list(None)
    existing_by_index: Dict[int, Dict[str, Any]] = {
        r["order_line_index"]: r for r in existing if "order_line_index" in r
    }

    product_cache: Dict[str, Dict[str, Any]] = {}
    now = utc_now()
    issued: List[Dict[str, Any]] = []

    for line_index, line in enumerate(order.get("items", [])):
        if line.get("item_type") not in ("rental", "booking"):
            continue

        product_id = line.get("product_id")
        if not product_id:
            continue

        if product_id not in product_cache:
            product_cache[product_id] = await products_collection.find_one(
                {"id": product_id, "organization_id": org_id},
                {"_id": 0},
            ) or {}
        product_doc = product_cache[product_id]

        flavor = derive_flavor(product_doc or {"item_type": line.get("item_type")})
        if not flavor:
            continue

        # Idempotency — return existing row for this (order, line_index).
        if line_index in existing_by_index:
            issued.append(existing_by_index[line_index])
            continue

        doc = _build_reservation_doc(
            org_id=org_id,
            order=order,
            line_index=line_index,
            line=line,
            flavor=flavor,
            product_doc=product_doc,
            now=now,
        )
        if not doc:
            continue

        # Retry loop for rare code collisions on the unique index.
        for attempt in range(5):
            try:
                await issued_reservations_collection.insert_one(doc)
                doc.pop("_id", None)
                issued.append(doc)
                break
            except Exception as exc:
                msg = str(exc)
                if "E11000" in msg and "code" in msg and attempt < 4:
                    # Code collided; regenerate and retry.
                    doc["code"] = generate_reservation_code()
                    continue
                if "E11000" in msg and "order_id" in msg:
                    # Concurrent confirm race — the other writer already
                    # inserted this reservation. Read it back.
                    fresh = await issued_reservations_collection.find_one(
                        {"order_id": order_id, "order_line_index": line_index},
                        {"_id": 0},
                    )
                    if fresh:
                        issued.append(fresh)
                    break
                logger.warning(
                    "issued_reservation_service: insert failed order=%s line=%d: %s",
                    order_id, line_index, exc,
                )
                break

    if issued:
        logger.info(
            "issued_reservation_service: %d reservations present for order=%s org=%s",
            len(issued), order_id, org_id,
        )
    return issued


async def release_for_order(order_id: str, org_id: str) -> int:
    """Mark all reservations of an order as cancelled. Returns count updated."""
    from database import issued_reservations_collection
    now = utc_now()
    result = await issued_reservations_collection.update_many(
        {"organization_id": org_id, "order_id": order_id, "status": {"$ne": "cancelled"}},
        {"$set": {"status": "cancelled", "cancelled_at": now, "updated_at": now}},
    )
    if result.modified_count:
        logger.info(
            "issued_reservation_service: cancelled %d reservations for order=%s",
            result.modified_count, order_id,
        )
    return result.modified_count


async def list_for_order(order_id: str, org_id: str) -> List[Dict[str, Any]]:
    from database import issued_reservations_collection
    return await issued_reservations_collection.find(
        {"organization_id": org_id, "order_id": order_id},
        {"_id": 0},
    ).sort("order_line_index", 1).to_list(None)


async def get_by_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Public endpoint lookup. No org scoping (token is the credential)."""
    from database import issued_reservations_collection
    if not access_token:
        return None
    return await issued_reservations_collection.find_one(
        {"access_token": access_token}, {"_id": 0}
    )
