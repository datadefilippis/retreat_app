"""
Tickets Router — admin endpoints for door check-in + attendance.

E5 wires the E4 `ticket_service` primitives to HTTP so the admin-side
(Michele at the door with a phone) can scan/type ticket codes and see
a live attendance list during the event.

Endpoints:
  POST /tickets/check-in                       Check in a ticket by code.
                                               Body: {code, occurrence_id?}
                                               Returns: {ok, reason, ticket}
  GET  /tickets/occurrence/{occurrence_id}     List all tickets for an
                                               occurrence (ordered by
                                               seat_index; includes voided
                                               when ?include_voided=1).
  GET  /tickets/occurrence/{occurrence_id}/stats
                                               Quick counts:
                                               {issued, valid, checked_in,
                                                voided, remaining}

All endpoints are auth-protected and scoped to the caller's organization.
The underlying ticket_service functions already enforce org-scope on
queries, so cross-tenant snooping is impossible through this layer.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field

from auth import get_current_user, get_verified_user, get_verified_user
from services.ticket_service import (
    check_in_ticket,
    list_tickets_for_occurrence,
    void_single_ticket,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


# ── Request / response models ──────────────────────────────────────────────


class CheckInRequest(BaseModel):
    code: str = Field(min_length=6, max_length=32)
    # Optional: when present, the endpoint refuses to check in a code
    # that belongs to a DIFFERENT occurrence. Useful when Michele's
    # scanner is locked to tonight's event so a ticket from last month
    # never accidentally marks present.
    occurrence_id: Optional[str] = None


class CheckInResponse(BaseModel):
    ok: bool
    reason: str
    ticket: Optional[dict] = None


class AttendanceStats(BaseModel):
    issued: int        # total tickets ever issued (includes voided)
    valid: int         # status=valid  (not yet scanned)
    checked_in: int    # status=checked_in
    voided: int        # status=voided
    remaining: int     # valid count — what the door still expects
    # F1 Onda 8 — per-holder delivery counters. Only meaningful for
    # occurrences where requires_attendee_details is on; otherwise all
    # tickets have delivery_status=pending and that's fine.
    delivery_sent: int = 0
    delivery_pending: int = 0
    delivery_unsent: int = 0       # attempts that failed
    delivery_targets: int = 0      # holders with email != customer_email


# G4 — resend email / void single / broadcast

class VoidRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=200)


class VoidResponse(BaseModel):
    ok: bool
    reason: str
    ticket: Optional[dict] = None


class ResendResponse(BaseModel):
    ok: bool
    reason: str


class BroadcastRequest(BaseModel):
    template: str  # reminder | logistics | cancellation | custom
    message: Optional[str] = Field(default=None, max_length=5000)
    subject_override: Optional[str] = Field(default=None, max_length=180)
    include_voided: bool = False
    include_checked_in: bool = True


class BroadcastResponse(BaseModel):
    target: int
    sent: int
    skipped_no_email: int
    errors: int
    error_message: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/check-in", response_model=CheckInResponse)
async def check_in(
    body: CheckInRequest,
    current_user: dict = Depends(get_verified_user),
):
    """Atomic check-in for a ticket code.

    Returns a structured payload the UI maps to green / yellow / red
    feedback. The atomic transition guarantees that simultaneous
    scanners cannot both first-time-succeed on the same ticket.
    """
    org_id = current_user["organization_id"]
    ok, reason, ticket = await check_in_ticket(
        code=body.code, org_id=org_id,
        occurrence_id=body.occurrence_id,
    )
    return CheckInResponse(ok=ok, reason=reason, ticket=ticket)


@router.get("/occurrence/{occurrence_id}")
async def list_attendance(
    occurrence_id: str,
    include_voided: bool = Query(False),
    current_user: dict = Depends(get_verified_user),
):
    """Attendance list for an occurrence.

    Ordered by seat_index ASC so the check-in screen reads top-down
    like a guest list. Voided tickets are excluded by default
    (Michele almost always wants "currently active seats only").
    """
    org_id = current_user["organization_id"]
    tickets = await list_tickets_for_occurrence(
        occurrence_id, org_id, include_voided=include_voided,
    )
    # CF5 — contatto azionabile per riga: molti biglietti nascono senza
    # holder_email/phone (checkout guest: il contatto vive sull'ordine).
    # contact_email/contact_phone = holder_* con fallback all'acquirente,
    # così i bottoni WhatsApp/email del dashboard usano il meglio che
    # esiste davvero (se non c'è nulla, restano disabilitati).
    missing = [t for t in tickets
               if not (t.get("holder_email") or "").strip()
               or not (t.get("holder_phone") or "").strip()]
    order_ids = list({t.get("order_id") for t in missing if t.get("order_id")})
    buyers: dict = {}
    if order_ids:
        from database import orders_collection, customers_collection
        cust_by_order: dict = {}
        async for o in orders_collection.find(
                {"id": {"$in": order_ids}, "organization_id": org_id},
                {"_id": 0, "id": 1, "customer_id": 1, "contact_phone": 1}):
            cust_by_order[o["id"]] = o
        cust_ids = list({o.get("customer_id") for o in cust_by_order.values()
                         if o.get("customer_id")})
        cust_docs = {}
        if cust_ids:
            async for c in customers_collection.find(
                    {"id": {"$in": cust_ids}, "organization_id": org_id},
                    {"_id": 0, "id": 1, "email": 1, "phone": 1}):
                cust_docs[c["id"]] = c
        for oid, o in cust_by_order.items():
            c = cust_docs.get(o.get("customer_id")) or {}
            buyers[oid] = {
                "email": c.get("email"),
                "phone": c.get("phone") or o.get("contact_phone"),
            }
    for t in tickets:
        buyer = buyers.get(t.get("order_id")) or {}
        t["contact_email"] = (t.get("holder_email") or "").strip() or buyer.get("email")
        t["contact_phone"] = (t.get("holder_phone") or "").strip() or buyer.get("phone")
    return {"tickets": tickets, "total": len(tickets)}


@router.get("/occurrence/{occurrence_id}/stats", response_model=AttendanceStats)
async def attendance_stats(
    occurrence_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Fast counters for the check-in dashboard header.

    Designed to be cheap enough to poll every few seconds while the
    check-in screen is open (Michele's phone showing "17 / 30
    entrati"). Uses a single aggregation to avoid multiple
    count_documents round-trips.
    """
    from database import issued_tickets_collection, orders_collection

    org_id = current_user["organization_id"]
    pipeline = [
        {"$match": {"organization_id": org_id, "occurrence_id": occurrence_id}},
        {"$group": {"_id": "$status", "n": {"$sum": 1}}},
    ]
    counts = {"valid": 0, "checked_in": 0, "voided": 0}
    async for row in issued_tickets_collection.aggregate(pipeline):
        k = row.get("_id")
        if k in counts:
            counts[k] = int(row.get("n") or 0)
    issued = counts["valid"] + counts["checked_in"] + counts["voided"]

    # F1 Onda 8 — delivery counters. Target = tickets whose holder_email
    # differs from the order's customer_email (i.e. guests that need their
    # own email). Voided tickets excluded.
    delivery_sent = 0
    delivery_pending = 0
    delivery_unsent = 0
    delivery_targets = 0
    tickets_cursor = issued_tickets_collection.find(
        {"organization_id": org_id, "occurrence_id": occurrence_id,
         "status": {"$ne": "voided"}},
        {"_id": 0, "holder_email": 1, "order_id": 1, "delivery_status": 1},
    )
    # Cache customer_email per order to avoid O(N) order lookups
    customer_email_cache: dict = {}
    async for tk in tickets_cursor:
        hemail = (tk.get("holder_email") or "").strip().lower()
        if not hemail:
            continue
        oid = tk.get("order_id")
        if oid not in customer_email_cache:
            o = await orders_collection.find_one(
                {"id": oid, "organization_id": org_id},
                {"_id": 0, "customer_email": 1},
            ) or {}
            customer_email_cache[oid] = (o.get("customer_email") or "").strip().lower()
        if hemail == customer_email_cache[oid]:
            continue  # main customer — receives the summary email
        delivery_targets += 1
        ds = tk.get("delivery_status") or "pending"
        if ds == "sent":
            delivery_sent += 1
        elif ds == "unsent":
            delivery_unsent += 1
        else:
            delivery_pending += 1

    return AttendanceStats(
        issued=issued,
        valid=counts["valid"],
        checked_in=counts["checked_in"],
        voided=counts["voided"],
        remaining=counts["valid"],
        delivery_sent=delivery_sent,
        delivery_pending=delivery_pending,
        delivery_unsent=delivery_unsent,
        delivery_targets=delivery_targets,
    )


# ── G4 endpoints ──────────────────────────────────────────────────────────


@router.post("/{code}/resend-email", response_model=ResendResponse)
async def resend_ticket_email(
    code: str,
    current_user: dict = Depends(get_verified_user),
):
    """Re-send the ticket confirmation email to the holder's address.

    Used when the customer lost the original email. The current org
    scope prevents cross-tenant resends; a code belonging to a
    different org is treated as not-found.
    """
    from services.event_email_service import resend_ticket_email_by_code
    org_id = current_user["organization_id"]
    ok, reason = await resend_ticket_email_by_code(code, org_id)
    return ResendResponse(ok=ok, reason=reason)


# ── F1 Onda 8 — resend all per-holder emails for an occurrence ────────────

class ResendAllResponse(BaseModel):
    ok: bool = True
    sent: int = 0
    skipped: int = 0
    errors: int = 0
    target: int = 0


@router.post("/occurrence/{occurrence_id}/resend-individual", response_model=ResendAllResponse)
async def resend_individual_tickets(
    occurrence_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Re-send the per-holder personal ticket email for every non-voided
    ticket on this occurrence whose holder_email != customer_email.

    Bulk operation — useful after a delivery failure window (SMTP provider
    down) or when the merchant enables the attendee_details flag
    retroactively and wants to notify already-issued tickets. Idempotent:
    safe to click multiple times (delivery_status updates each run).
    """
    from database import issued_tickets_collection, orders_collection
    from services.event_email_service import send_individual_tickets_for_order

    org_id = current_user["organization_id"]

    # Group tickets by order_id so we can reuse send_individual_tickets_for_order
    # (which expects an order-level call).
    order_ids = await issued_tickets_collection.distinct(
        "order_id",
        {"organization_id": org_id, "occurrence_id": occurrence_id,
         "status": {"$ne": "voided"}},
    )

    totals = {"sent": 0, "skipped": 0, "errors": 0, "target": 0}
    for oid in order_ids:
        order = await orders_collection.find_one(
            {"id": oid, "organization_id": org_id},
            {"_id": 0},
        )
        if not order:
            continue
        res = await send_individual_tickets_for_order(order, org_id)
        for k in totals:
            totals[k] += int(res.get(k) or 0)

    return ResendAllResponse(
        ok=True,
        sent=totals["sent"],
        skipped=totals["skipped"],
        errors=totals["errors"],
        target=totals["target"],
    )


@router.post("/{code}/void", response_model=VoidResponse)
async def void_one_ticket(
    code: str,
    body: VoidRequest = VoidRequest(),
    current_user: dict = Depends(get_verified_user),
):
    """Void a single ticket by code without cancelling the parent order.

    Use cases:
      - A specific guest can no longer attend but the rest of the
        order is fine
      - The merchant flagged the ticket (stolen, counterfeit)

    Refuses to void a ticket that is already checked_in (the merchant
    must handle that manually at the door).
    """
    org_id = current_user["organization_id"]
    ok, reason, ticket = await void_single_ticket(
        code=code, org_id=org_id, reason=body.reason,
    )
    return VoidResponse(ok=ok, reason=reason, ticket=ticket)


@router.post("/occurrence/{occurrence_id}/email-attendees", response_model=BroadcastResponse)
async def broadcast_attendees(
    occurrence_id: str,
    body: BroadcastRequest,
    current_user: dict = Depends(get_verified_user),
):
    """Send a mail-merged email to every attendee of an occurrence.

    Templates: reminder | logistics | cancellation | custom
      - reminder    "Ci vediamo presto — {event}"
      - logistics   "Informazioni pratiche — {event}"
      - cancellation "Evento annullato — {event}"
      - custom      merchant provides subject (first line of message)
                     and body (message). Requires `message` non-empty.

    Deduplicates by holder_email. Returns counters so the UI can
    report outcomes.
    """
    from services.event_email_service import broadcast_to_attendees
    org_id = current_user["organization_id"]
    res = await broadcast_to_attendees(
        org_id=org_id,
        occurrence_id=occurrence_id,
        template_key=body.template,
        message=body.message,
        subject_override=body.subject_override,
        include_voided=body.include_voided,
        include_checked_in=body.include_checked_in,
    )
    return BroadcastResponse(**{k: v for k, v in res.items()
                                if k in {"target", "sent", "skipped_no_email", "errors", "error_message"}})
