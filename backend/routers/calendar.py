"""
Calendar Router — temporal visibility for operators.

Returns event occurrences and rental order lines for a given month,
enabling a calendar view of scheduled/requested commercial items.

Read-only. No booking logic, no conflict detection.
"""

import logging
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from auth import get_current_user, get_verified_user, get_verified_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar"])


# ── Response models ────────────────────────────────────────────────────────

class CalendarEvent(BaseModel):
    id: str
    type: str                        # "event_occurrence" | "rental_order" | "service_booking"
    title: str
    date: str                        # ISO date "2026-08-14"
    end_date: Optional[str] = None   # ISO date (rental range end)
    time: Optional[str] = None       # "20:30" (events + bookings start time)
    end_time: Optional[str] = None   # "21:30" (booking end time)
    location: Optional[str] = None
    status: Optional[str] = None     # occurrence / order / booking status
    status_label: Optional[str] = None  # Italian label for display
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None  # Onda 14 — for calendar day-detail reach-out
    customer_phone: Optional[str] = None  # Onda 14 — for calendar day-detail reach-out
    order_id: Optional[str] = None
    notes: Optional[str] = None
    # Operational context
    review_reason: Optional[str] = None  # from order review_state derivation
    capacity: Optional[int] = None       # occurrence capacity (if set)
    booked_count: Optional[int] = None   # orders referencing this occurrence
    # Onda 14 — consulenza-specific booking fields
    booking_code: Optional[str] = None          # BKG-XXXX-XXXX
    booking_access_token: Optional[str] = None  # link to /b/:token landing
    service_option_label: Optional[str] = None  # which option the customer picked
    attendee_fields_data: Optional[dict] = None # custom merchant fields filled at checkout


class CalendarResponse(BaseModel):
    items: List[CalendarEvent]
    month: int
    year: int


# ── Endpoint ───────────────────────────────────────────────────────────────

@router.get("/items", response_model=CalendarResponse)
async def get_calendar_items(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    product_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_verified_user),
):
    """Return event occurrences and rental order lines for a given month, optionally filtered by product."""
    from database import event_occurrences_collection, orders_collection

    org_id = current_user["organization_id"]

    # Date range for the month (string prefix matching for ISO dates)
    month_prefix = f"{year}-{month:02d}"

    items: List[CalendarEvent] = []

    # ── 1. Event Occurrences ───────────────────────────────────────────────
    OCC_STATUS_LABELS = {
        "draft": "Bozza", "published": "Pubblicato",
        "closed": "Chiuso", "cancelled": "Annullato",
    }
    ORDER_STATUS_LABELS = {
        "draft": "Bozza", "confirmed": "Confermato",
        "completed": "Completato", "cancelled": "Annullato",
    }

    # A1 (Onda 12) — il calendario admin mostra solo occurrence published.
    # Le bozze sono visibili solo dalla lista eventi (EventsGrid). Evita
    # che il calendario sia inquinato da occurrence in fase di editing e
    # riduce le sovrapposizioni visive con i blocchi personal/booking.
    occ_query = {
        "organization_id": org_id,
        "start_at": {"$regex": f"^{month_prefix}"},
        "status": "published",
    }
    if product_id:
        occ_query["product_id"] = product_id
    occ_cursor = event_occurrences_collection.find(
        occ_query,
        {"_id": 0, "id": 1, "product_id": 1, "product_name": 1,
         "start_at": 1, "end_at": 1, "location": 1, "status": 1, "notes": 1,
         "capacity": 1},
    ).sort("start_at", 1).limit(200)

    occ_list = await occ_cursor.to_list(200)

    # Batch count bookings per occurrence
    occ_ids = [o["id"] for o in occ_list]
    booked_counts = {}
    if occ_ids:
        pipeline = [
            {"$match": {"organization_id": org_id, "status": {"$ne": "cancelled"},
                         "items.occurrence_id": {"$in": occ_ids}}},
            {"$unwind": "$items"},
            {"$match": {"items.occurrence_id": {"$in": occ_ids}}},
            {"$group": {"_id": "$items.occurrence_id", "count": {"$sum": 1}}},
        ]
        async for doc in orders_collection.aggregate(pipeline):
            booked_counts[doc["_id"]] = doc["count"]

    for occ in occ_list:
        start_at = occ.get("start_at", "")
        date_part = start_at[:10] if len(start_at) >= 10 else start_at
        time_part = start_at[11:16] if len(start_at) >= 16 else None
        occ_status = occ.get("status", "draft")
        cap = occ.get("capacity")
        booked = booked_counts.get(occ["id"], 0)

        items.append(CalendarEvent(
            id=occ["id"],
            type="event_occurrence",
            title=occ.get("product_name") or "Evento",
            date=date_part,
            time=time_part,
            location=occ.get("location"),
            status=occ_status,
            status_label=OCC_STATUS_LABELS.get(occ_status, occ_status),
            product_id=occ.get("product_id"),
            product_name=occ.get("product_name"),
            notes=occ.get("notes"),
            capacity=cap,
            booked_count=booked if cap else None,
        ))

    # ── 2. Rental Order Lines ──────────────────────────────────────────────
    # Two sub-flavors coexist under item_type="rental":
    #   range: rental_date_from / rental_date_to (multi-day, daily granularity)
    #   slot : booking_date / booking_start_time / booking_end_time
    #          (single time window, optionally cross-day via booking_end_date —
    #           Onda 17).
    # Match orders where EITHER field starts with the month prefix so both
    # flavors show up in the Lista view. The per-line loop below dispatches
    # on whichever field is populated.
    rental_elem_match_range = {"rental_date_from": {"$regex": f"^{month_prefix}"}}
    rental_elem_match_slot = {
        "item_type": "rental",
        "booking_date": {"$regex": f"^{month_prefix}"},
    }
    if product_id:
        rental_elem_match_range["product_id"] = product_id
        rental_elem_match_slot["product_id"] = product_id
    rental_pipeline = [
        {"$match": {
            "organization_id": org_id,
            "status": {"$ne": "cancelled"},
            "$or": [
                {"items": {"$elemMatch": rental_elem_match_range}},
                {"items": {"$elemMatch": rental_elem_match_slot}},
            ],
        }},
        {"$limit": 100},
        {"$project": {
            "_id": 0, "id": 1, "customer_name": 1, "status": 1,
            "items": 1,
        }},
    ]
    from services.commerce_rules import derive_review_info

    async for order in orders_collection.aggregate(rental_pipeline):
        order_status = order.get("status", "draft")
        review = derive_review_info(order)
        for line in order.get("items", []):
            if product_id and line.get("product_id") != product_id:
                continue

            # Range flavor — historic path.
            rd_from = line.get("rental_date_from") or ""
            if rd_from.startswith(month_prefix):
                items.append(CalendarEvent(
                    id=f"{order['id']}_{line['product_id']}",
                    type="rental_order",
                    title=line.get("product_name", "Noleggio"),
                    date=rd_from,
                    end_date=line.get("rental_date_to"),
                    location=None,
                    status=order_status,
                    status_label=ORDER_STATUS_LABELS.get(order_status, order_status),
                    product_name=line.get("product_name"),
                    customer_name=order.get("customer_name"),
                    order_id=order["id"],
                    notes=line.get("rental_notes"),
                    review_reason=review["reason"] if review else None,
                ))
                continue

            # Slot flavor — Onda 16 / Onda 17. Only rental lines qualify here;
            # service/booking consulenze are surfaced by the issued_bookings
            # pipeline below with type="service_booking".
            if line.get("item_type") != "rental":
                continue
            bd = line.get("booking_date") or ""
            if not bd.startswith(month_prefix):
                continue
            items.append(CalendarEvent(
                id=f"{order['id']}_{line['product_id']}",
                type="rental_order",
                title=line.get("product_name", "Noleggio"),
                date=bd,
                # booking_end_date (Onda 17) = cross-day end; when None the
                # reservation ends same-day so we leave end_date None.
                end_date=line.get("booking_end_date") if line.get("booking_end_date") and line.get("booking_end_date") != bd else None,
                time=line.get("booking_start_time"),
                end_time=line.get("booking_end_time"),
                location=None,
                status=order_status,
                status_label=ORDER_STATUS_LABELS.get(order_status, order_status),
                product_name=line.get("product_name"),
                customer_name=order.get("customer_name"),
                order_id=order["id"],
                notes=line.get("rental_notes"),
                review_reason=review["reason"] if review else None,
            ))

    # ── 3. Service Bookings (Onda 14 — consulenze) ────────────────────────
    # Query issued_bookings for the month. Each row represents one
    # confirmed consulenza slot; join on orders for customer contact fields
    # and on products if the product filter is active.
    from database import issued_bookings_collection

    booking_query = {
        "organization_id": org_id,
        "booking_date": {"$regex": f"^{month_prefix}"},
        "status": {"$ne": "cancelled"},
    }
    if product_id:
        booking_query["product_id"] = product_id

    bookings_list = await issued_bookings_collection.find(
        booking_query,
        {"_id": 0},
    ).sort([("booking_date", 1), ("booking_start_time", 1)]).limit(500).to_list(500)

    # Batch-fetch orders referenced by these bookings for customer_email + phone.
    # One query, one hop — avoids N+1 on the join.
    order_ids = list({b.get("order_id") for b in bookings_list if b.get("order_id")})
    order_contacts = {}
    if order_ids:
        order_cursor = orders_collection.find(
            {"organization_id": org_id, "id": {"$in": order_ids}},
            {"_id": 0, "id": 1, "customer_name": 1, "customer_email": 1,
             "customer_phone": 1, "contact_phone": 1, "order_fields_data": 1},
        )
        async for o in order_cursor:
            order_contacts[o["id"]] = o

    # Batch-fetch product names for bookings (falls back to snapshot on booking).
    from database import products_collection
    prod_ids = list({b.get("product_id") for b in bookings_list if b.get("product_id")})
    product_names = {}
    if prod_ids:
        async for p in products_collection.find(
            {"organization_id": org_id, "id": {"$in": prod_ids}},
            {"_id": 0, "id": 1, "name": 1},
        ):
            product_names[p["id"]] = p.get("name")

    for b in bookings_list:
        order = order_contacts.get(b.get("order_id"), {}) if b.get("order_id") else {}
        prod_name = product_names.get(b.get("product_id")) or "Consulenza"
        items.append(CalendarEvent(
            id=b.get("id", ""),
            type="service_booking",
            title=prod_name,
            date=b.get("booking_date", ""),
            time=b.get("booking_start_time"),
            end_time=b.get("booking_end_time"),
            location=b.get("location"),
            status=b.get("status", "confirmed"),
            status_label={"confirmed": "Confermata", "completed": "Completata",
                          "no_show": "Mancato appuntamento"}.get(b.get("status"), b.get("status")),
            product_id=b.get("product_id"),
            product_name=prod_name,
            customer_name=b.get("holder_name") or order.get("customer_name"),
            customer_email=b.get("holder_email") or order.get("customer_email"),
            customer_phone=b.get("holder_phone") or order.get("customer_phone") or order.get("contact_phone"),
            order_id=b.get("order_id"),
            booking_code=b.get("code"),
            booking_access_token=b.get("access_token"),
            service_option_label=b.get("service_option_label"),
            attendee_fields_data=b.get("attendee_fields_data") or order.get("order_fields_data") or None,
        ))

    # Sort all items by date (then by time when present so a day view
    # shows bookings in chronological order within the day).
    items.sort(key=lambda x: (x.date, x.time or ""))

    logger.info("calendar: returned %d items for %s org=%s", len(items), month_prefix, org_id)
    return CalendarResponse(items=items, month=month, year=year)
