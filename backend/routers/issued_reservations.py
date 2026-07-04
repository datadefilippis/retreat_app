"""
Issued Reservations — admin list + actions (Onda 16).

Routes:
  GET  /api/issued-reservations            — list (optional order_id filter)
  POST /api/issued-reservations/{id}/resend — re-send confirmation email
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from database import issued_reservations_collection
from auth import get_current_user, get_verified_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issued-reservations", tags=["Issued Reservations"])


class IssuedReservationListResponse(BaseModel):
    reservations: List[dict]


@router.get("", response_model=IssuedReservationListResponse)
async def list_issued_reservations(
    order_id: Optional[str] = Query(None),
    flavor: Optional[str] = Query(None, pattern="^(range|slot)$"),
    status_filter: Optional[str] = Query(None, alias="status", pattern="^(active|cancelled)$"),
    date_from: Optional[str] = Query(None, description="Filter reservations starting on or after this ISO date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter reservations ending on or before this ISO date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Case-insensitive match on code, holder_name, holder_email, product_name"),
    limit: int = Query(default=200, le=500),
    current_user: dict = Depends(get_verified_user),
):
    """List IssuedReservation rows for the admin dashboard.

    Supports filtering by flavor / status / order, by a date window (applied
    inclusively on date_from for range flavor and slot_date for slot flavor),
    and a free-text search across the most useful admin columns.
    """
    org_id = current_user["organization_id"]
    query: dict = {"organization_id": org_id}
    if order_id:
        query["order_id"] = order_id
    if flavor:
        query["reservation_flavor"] = flavor
    if status_filter:
        query["status"] = status_filter

    # Date window: ISO YYYY-MM-DD strings sort lexicographically so a string
    # comparison yields the same result as a date comparison.
    if date_from or date_to:
        date_conditions = []
        if date_from and date_to:
            date_conditions = [
                {"date_from": {"$gte": date_from, "$lte": date_to}},
                {"slot_date": {"$gte": date_from, "$lte": date_to}},
            ]
        elif date_from:
            date_conditions = [
                {"date_from": {"$gte": date_from}},
                {"slot_date": {"$gte": date_from}},
            ]
        elif date_to:
            date_conditions = [
                {"date_from": {"$lte": date_to}},
                {"slot_date": {"$lte": date_to}},
            ]
        if date_conditions:
            query["$or"] = date_conditions

    if search:
        import re
        safe = re.escape(search.strip())
        if safe:
            rx = {"$regex": safe, "$options": "i"}
            search_conditions = [
                {"code": rx},
                {"holder_name": rx},
                {"holder_email": rx},
                {"product_name": rx},
            ]
            # Compose with any existing $or (date window): use $and to preserve both.
            if "$or" in query:
                existing_or = query.pop("$or")
                query["$and"] = [{"$or": existing_or}, {"$or": search_conditions}]
            else:
                query["$or"] = search_conditions

    rows = await issued_reservations_collection.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"reservations": rows}


@router.post("/{reservation_id}/resend")
async def resend_reservation_email(
    reservation_id: str,
    current_user: dict = Depends(get_verified_user),
):
    if current_user.get("role") not in ("admin", "system_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    org_id = current_user["organization_id"]
    reservation = await issued_reservations_collection.find_one(
        {"id": reservation_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation non trovata")
    if reservation.get("status") == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reservation cancellata — non posso rinviare la conferma.",
        )
    # Defer the actual send to a lightweight helper so the email service
    # can be stubbed in tests without patching the router.
    from services.email_service import send_reservation_confirmation_email
    sent = await send_reservation_confirmation_email(reservation_id=reservation_id, org_id=org_id)
    return {"ok": bool(sent), "reservation_id": reservation_id}
