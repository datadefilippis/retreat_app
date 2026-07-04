"""
Issued Bookings — admin list + resend (parity with issued_reservations).

Routes:
  GET  /api/issued-bookings            — list (optional order_id filter)
  POST /api/issued-bookings/{id}/resend — re-send order confirmation email

Note: bookings are rendered inline inside the order confirmation email
(see order_email_service._render_bookings_section) — there is no per-booking
email. Resend here re-sends the full order confirmation to the customer,
which re-renders the bookings block with up-to-date links. This mirrors
how the customer originally received the message.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from database import issued_bookings_collection, orders_collection
from auth import get_current_user, get_verified_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issued-bookings", tags=["Issued Bookings"])


class IssuedBookingListResponse(BaseModel):
    bookings: List[dict]


@router.get("", response_model=IssuedBookingListResponse)
async def list_issued_bookings(
    order_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(default=200, le=500),
    current_user: dict = Depends(get_verified_user),
):
    org_id = current_user["organization_id"]
    query: dict = {"organization_id": org_id}
    if order_id:
        query["order_id"] = order_id
    if status_filter:
        query["status"] = status_filter
    rows = await issued_bookings_collection.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"bookings": rows}


@router.post("/{booking_id}/resend")
async def resend_booking_email(
    booking_id: str,
    current_user: dict = Depends(get_verified_user),
):
    if current_user.get("role") not in ("admin", "system_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    org_id = current_user["organization_id"]

    # Accept either the IssuedBooking id or the BKG-... code for flexibility.
    booking = await issued_bookings_collection.find_one(
        {"$or": [{"id": booking_id}, {"code": booking_id}],
         "organization_id": org_id},
        {"_id": 0},
    )
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking non trovato")
    if booking.get("status") == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking cancellato — non posso rinviare la conferma.",
        )

    order = await orders_collection.find_one(
        {"id": booking.get("order_id"), "organization_id": org_id},
        {"_id": 0},
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordine associato non trovato",
        )

    # Re-send the full order confirmation, which re-renders the bookings block.
    from services.order_email_service import notify_customer_order_confirmed
    try:
        await notify_customer_order_confirmed(order, org_id)
        sent = True
    except Exception as exc:
        logger.warning("issued_bookings.resend: failed for %s: %s", booking_id, exc)
        sent = False

    # Update delivery tracking on the booking doc (additive, best-effort).
    from models.common import utc_now
    await issued_bookings_collection.update_one(
        {"id": booking.get("id"), "organization_id": org_id},
        {"$set": {
            "last_resent_at": utc_now(),
            "delivery_status": "sent" if sent else "failed",
        },
         "$inc": {"delivery_attempts": 1}},
    )
    return {"ok": bool(sent), "booking_id": booking.get("id")}
