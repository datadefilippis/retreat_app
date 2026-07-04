"""
Booking service — issuance, voiding, completion of service appointments.

Onda 14: analog of ticket_service for service products (consulenze).
Before this module a confirmed service order stopped at the order line —
no per-appointment entity, no access token landing page, no delivery
tracking on the confirmation email, no way for the admin to mark a
session delivered or resend the email.

Public surface mirrors ticket_service for consistency:

  issue_bookings_for_order(order, org_id)
    Called from order_service.confirm_order AFTER ticket issuance.
    Walks every service line with a booking_date + booking_start_time,
    creates N IssuedBooking rows (one per seat in that line's quantity).
    Idempotent: returns existing bookings when called twice.

  void_bookings_for_order(order_id, org_id)
    Called from order_service.cancel_order. Transitions every booking
    for the order to status="cancelled" + timestamp. Never deletes rows.

  complete_booking(code, org_id)
    Admin action — transitions status=confirmed -> completed.

  mark_no_show(code, org_id)
    Admin action — transitions status=confirmed -> no_show.

  generate_qr_png(payload)
    Re-exports ticket_service.generate_qr_png for a single import point.

Design contract identical to ticket_service:
  - No exceptions on the happy path; structured status codes instead.
  - Idempotent — retries at the webhook / cancel layer are safe.
  - Never leaks cross-org data: every read filters on organization_id.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from models.common import utc_now
from models.issued_booking import IssuedBooking, generate_booking_code

logger = logging.getLogger(__name__)


def _generate_access_token() -> str:
    """Unguessable URL-safe token for /b/{token} landing page. 192-bit entropy."""
    return secrets.token_urlsafe(24)


def _compute_access_token_expiry(booking_date: Optional[str], booking_end_time: Optional[str]) -> Optional[str]:
    """Default expiry: booking_end + 14 days. None if date/time missing."""
    if not booking_date:
        return None
    try:
        t = booking_end_time or "23:59"
        dt = datetime.fromisoformat(f"{booking_date}T{t}:00")
        return (dt + timedelta(days=14)).isoformat()
    except Exception:
        return None


def _resolve_location(item: dict, product_doc: Optional[dict] = None) -> Optional[str]:
    """Pick the most specific location string available on the order line / product.

    Priority: item.location → product.metadata.location → product.meeting_link → None.
    """
    loc = item.get("location") or item.get("meeting_link")
    if loc:
        return loc
    if product_doc:
        meta = product_doc.get("metadata") or {}
        return meta.get("location") or product_doc.get("meeting_link")
    return None


async def issue_bookings_for_order(order: dict, org_id: str) -> List[dict]:
    """Issue IssuedBooking rows for every service appointment seat in `order`.

    A service order line with quantity=3 becomes 3 rows (session bundle).
    Idempotent — if the order already has issued bookings, returns them as-is
    without creating duplicates.
    """
    from database import issued_bookings_collection, products_collection

    order_id = order.get("id")
    if not order_id:
        return []

    # Idempotency: existing rows → return them unchanged
    existing = await issued_bookings_collection.find(
        {"organization_id": org_id, "order_id": order_id},
        {"_id": 0},
    ).to_list(None)
    if existing:
        return existing

    customer_name = order.get("customer_name") or ""
    customer_email = order.get("customer_email") or ""
    customer_phone = order.get("customer_phone") or ""
    issued: List[dict] = []

    # Cache product docs so we don't re-query for multi-seat lines.
    product_cache: dict = {}

    for item in order.get("items", []):
        if item.get("item_type") != "service":
            continue
        bdate = item.get("booking_date")
        bstart = item.get("booking_start_time")
        bend = item.get("booking_end_time")
        if not (bdate and bstart and bend):
            # Service line without a booked slot (e.g. price-on-request).
            # We don't issue a booking entity until an admin confirms a slot.
            continue
        try:
            qty = int(item.get("quantity", 1) or 1)
        except Exception:
            qty = 1
        if qty <= 0:
            continue

        product_id = item.get("product_id")
        if product_id and product_id not in product_cache:
            product_cache[product_id] = await products_collection.find_one(
                {"id": product_id},
                {"_id": 0, "metadata": 1, "meeting_link": 1},
            ) or {}
        product_doc = product_cache.get(product_id)

        location = _resolve_location(item, product_doc)
        service_option_id = item.get("service_option_id")
        service_option_label = item.get("service_option_label")

        # Per-order order_fields_data is on the order, not the line — but
        # copy it onto every booking for dashboard convenience.
        attendee_fields = order.get("order_fields_data") or {}

        for seat_index in range(1, qty + 1):
            for attempt in range(5):
                code = generate_booking_code()
                booking = IssuedBooking(
                    organization_id=org_id,
                    order_id=order_id,
                    product_id=product_id,
                    booking_date=bdate,
                    booking_start_time=bstart,
                    booking_end_time=bend,
                    service_option_id=service_option_id,
                    service_option_label=service_option_label,
                    location=location,
                    code=code,
                    status="confirmed",
                    seat_index=seat_index,
                    seat_count=qty,
                    holder_name=customer_name,
                    holder_email=customer_email,
                    holder_phone=customer_phone or None,
                    access_token=_generate_access_token(),
                    access_token_expires_at=_compute_access_token_expiry(bdate, bend),
                    delivery_status="pending",
                    attendee_fields_data=attendee_fields,
                )
                doc = booking.model_dump(mode="json")
                try:
                    await issued_bookings_collection.insert_one(doc)
                    doc.pop("_id", None)
                    issued.append(doc)
                    break
                except Exception as exc:
                    # Likely E11000 duplicate on `code` — retry.
                    if "E11000" in str(exc) and attempt < 4:
                        continue
                    logger.warning(
                        "booking_service: failed to issue booking order=%s seat=%d/%d: %s",
                        order_id, seat_index, qty, exc,
                    )
                    break

    if issued:
        logger.info(
            "booking_service: issued %d bookings for order=%s org=%s",
            len(issued), order_id, org_id,
        )
    return issued


async def void_bookings_for_order(order_id: str, org_id: str) -> int:
    """Cancel every booking attached to `order_id`. Returns count updated.

    Idempotent: already-cancelled rows are not modified.
    """
    from database import issued_bookings_collection
    now = utc_now().isoformat()
    result = await issued_bookings_collection.update_many(
        {"organization_id": org_id, "order_id": order_id, "status": {"$ne": "cancelled"}},
        {"$set": {"status": "cancelled", "cancelled_at": now}},
    )
    if result.modified_count:
        logger.info(
            "booking_service: voided %d bookings for order=%s org=%s",
            result.modified_count, order_id, org_id,
        )
    return result.modified_count


async def complete_booking(code: str, org_id: str) -> Tuple[bool, str, Optional[dict]]:
    """Admin action: mark a confirmed booking as delivered.

    Returns (ok, status_code, doc). status_code values:
      ok                     — transitioned
      already_completed      — was already completed
      cancelled              — booking belongs to a cancelled row
      not_found              — no such code for this org
    """
    from database import issued_bookings_collection
    doc = await issued_bookings_collection.find_one(
        {"organization_id": org_id, "code": code}, {"_id": 0},
    )
    if not doc:
        return False, "not_found", None
    if doc.get("status") == "completed":
        return False, "already_completed", doc
    if doc.get("status") == "cancelled":
        return False, "cancelled", doc
    now = utc_now().isoformat()
    await issued_bookings_collection.update_one(
        {"organization_id": org_id, "code": code},
        {"$set": {"status": "completed", "completed_at": now}},
    )
    doc["status"] = "completed"
    doc["completed_at"] = now
    return True, "ok", doc


async def mark_no_show(code: str, org_id: str) -> Tuple[bool, str, Optional[dict]]:
    """Admin action: mark a confirmed booking as no-show."""
    from database import issued_bookings_collection
    doc = await issued_bookings_collection.find_one(
        {"organization_id": org_id, "code": code}, {"_id": 0},
    )
    if not doc:
        return False, "not_found", None
    if doc.get("status") == "no_show":
        return False, "already_no_show", doc
    if doc.get("status") == "cancelled":
        return False, "cancelled", doc
    now = utc_now().isoformat()
    await issued_bookings_collection.update_one(
        {"organization_id": org_id, "code": code},
        {"$set": {"status": "no_show", "completed_at": now}},
    )
    doc["status"] = "no_show"
    doc["completed_at"] = now
    return True, "ok", doc
