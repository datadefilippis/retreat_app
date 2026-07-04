"""
Ticket service — issuance, voiding, check-in, QR generation.

E4 introduces the ISSUED TICKET as a first-class entity. Before E4 an
"event_ticket" order line said "3 seats booked" and stopped there —
no identity per seat, no way to check in, no email with a scannable
code. This module fills the gap:

  issue_tickets_for_order(order, org_id)
    Called from order_service.confirm_order after the P7/E1 atomic
    capacity reservation succeeds. Walks every event_ticket order
    line, creates N IssuedTicket rows (one per seat in that line's
    quantity), each with a globally-unique EVT-XXXX-XXXX code.
    Idempotent: returns existing tickets for the order when called
    twice on the same order (survives retries / webhook duplicates).

  void_tickets_for_order(order_id, org_id)
    Called from order_service.cancel_order. Transitions every ticket
    for the order to status="voided" with a `voided_at` timestamp —
    NEVER deletes rows (audit trail requirement). Idempotent: voiding
    an already-voided ticket is a no-op.

  check_in_ticket(code, org_id)
    Called by the door-scanner endpoint (E5). Atomic transition
    status=valid -> checked_in. Returns a structured result so the
    UI can distinguish the three real-world cases:
      ok                     — first-time scan, green light
      already_checked_in     — same ticket scanned a second time
      voided                 — ticket belongs to a cancelled order
      not_found              — no such code in this org
      wrong_occurrence       — code valid but for a DIFFERENT event

  generate_qr_png(payload)
    Returns a PNG bytes buffer encoding `payload` as a QR code at a
    size suitable for email embedding (base64 data URI) or PDF.

Design contract mirrors the rest of the onda 5 primitives:
  - No exceptions on the happy path; structured status codes instead.
  - Idempotent — retries at the webhook / cancel layer are safe.
  - Never leaks cross-org data: every read filters on organization_id.
"""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from typing import List, Optional, Tuple

from models.common import utc_now
from models.issued_ticket import IssuedTicket, generate_ticket_code

logger = logging.getLogger(__name__)


def _generate_access_token() -> str:
    """Unguessable URL-safe token for the public /t/{token} landing page.
    32 chars (192-bit entropy) — infeasible to enumerate."""
    return secrets.token_urlsafe(24)


def _compute_access_token_expiry(event_end_iso: Optional[str]) -> Optional[str]:
    """Default: event_end + 14d. None if no event_end is available — the
    caller can still revoke via admin action later."""
    if not event_end_iso:
        return None
    try:
        from datetime import datetime
        # Accept both "2026-04-25T16:48" and full ISO with offset
        s = event_end_iso.replace("Z", "+00:00")
        d = datetime.fromisoformat(s) if "T" in s else None
        if d is None:
            return None
        return (d + timedelta(days=14)).isoformat()
    except Exception:
        return None


async def issue_tickets_for_order(
    order: dict,
    org_id: str,
) -> List[dict]:
    """Issue IssuedTicket rows for every event_ticket seat in `order`.

    One row per seat: an order line with quantity=3 becomes 3 rows.
    Idempotent — if the order already has issued tickets, the existing
    ones are returned without creating duplicates.

    Returns the list of stored ticket dicts (most useful for the
    caller to embed into the confirmation email).
    """
    from database import issued_tickets_collection

    order_id = order.get("id")
    if not order_id:
        return []

    # Idempotency: if we already issued tickets for this order, return them.
    existing = await issued_tickets_collection.find(
        {"organization_id": org_id, "order_id": order_id},
        {"_id": 0},
    ).to_list(None)
    if existing:
        return existing

    from database import event_occurrences_collection

    customer_name = order.get("customer_name") or ""
    customer_email = order.get("customer_email") or ""
    customer_phone = order.get("customer_phone") or ""
    issued: List[dict] = []

    # Cache occurrence end timestamps (for access_token expiry) so we don't
    # re-query for every seat in the same line.
    occ_end_cache: dict = {}

    for item in order.get("items", []):
        if item.get("item_type") != "event_ticket":
            continue
        occ_id = item.get("occurrence_id")
        if not occ_id:
            continue
        try:
            qty = int(item.get("quantity", 1) or 1)
        except Exception:
            qty = 1
        if qty <= 0:
            continue

        product_id = item.get("product_id")
        tier_id = item.get("ticket_tier_id")
        tier_label = item.get("ticket_tier_label")

        # Fetch occurrence end (or start, if end is null) for token expiry
        if occ_id not in occ_end_cache:
            occ_doc = await event_occurrences_collection.find_one(
                {"id": occ_id}, {"_id": 0, "end_at": 1, "start_at": 1},
            ) or {}
            occ_end_cache[occ_id] = occ_doc.get("end_at") or occ_doc.get("start_at")
        occ_end = occ_end_cache[occ_id]

        # F1 Onda 8 — if the order line carries per-seat attendees (set when
        # product.metadata.requires_attendee_details is True), use them to
        # populate holder_name / holder_email / holder_phone. Otherwise
        # fall back to the order's customer_* for backward-compat.
        attendees = item.get("attendees") or []

        for seat_index in range(1, qty + 1):
            # Pick this seat's holder (1-based index). Fallback to customer
            # when the line has no attendees or the array is shorter than qty.
            holder = None
            if attendees and len(attendees) >= seat_index:
                holder = attendees[seat_index - 1] or {}
            hname = (holder.get("name") if holder else "") or customer_name
            hemail = (holder.get("email") if holder else "") or customer_email
            hphone = (holder.get("phone") if holder else "") or customer_phone
            # F2 Onda 9 — snapshot the per-holder custom_fields on the
            # ticket so the dashboard + CSV export can read them without
            # joining back to the order line, and historical data survives
            # product config edits.
            hcustom = (holder.get("custom_fields") if holder else {}) or {}

            # Retry code generation on the rare collision against the
            # unique index. `generate_ticket_code` uses CSPRNG so the
            # collision rate is negligible, but we guard anyway.
            for attempt in range(5):
                code = generate_ticket_code()
                ticket = IssuedTicket(
                    organization_id=org_id,
                    order_id=order_id,
                    occurrence_id=occ_id,
                    product_id=product_id,
                    tier_id=tier_id,
                    tier_label=tier_label,
                    code=code,
                    status="valid",
                    seat_index=seat_index,
                    seat_count=qty,
                    holder_name=hname,
                    holder_email=hemail,
                    holder_phone=hphone or None,
                    # F1 Onda 8 — access_token for the /t/{token} landing page
                    access_token=_generate_access_token(),
                    access_token_expires_at=_compute_access_token_expiry(occ_end),
                    delivery_status="pending",
                    # F2 Onda 9 — snapshot custom fields
                    attendee_fields_data=hcustom,
                )
                doc = ticket.model_dump(mode="json")
                try:
                    await issued_tickets_collection.insert_one(doc)
                    doc.pop("_id", None)
                    issued.append(doc)
                    break
                except Exception as exc:
                    # Likely E11000 duplicate on `code` — retry.
                    if "E11000" in str(exc) and attempt < 4:
                        continue
                    logger.warning(
                        "ticket_service: failed to issue ticket order=%s seat=%d/%d: %s",
                        order_id, seat_index, qty, exc,
                    )
                    break
    if issued:
        logger.info(
            "ticket_service: issued %d tickets for order=%s org=%s",
            len(issued), order_id, org_id,
        )
    return issued


async def void_single_ticket(
    code: str,
    org_id: str,
    reason: Optional[str] = None,
) -> Tuple[bool, str, Optional[dict]]:
    """G4 — atomic void of ONE ticket by code, without cancelling the
    containing order.

    Use case: customer's order had 3 VIP seats, one guest can't make
    it — the merchant voids only that ticket without refunding /
    cancelling the whole order. Also used to invalidate a ticket
    flagged by the door (stolen, counterfeit, etc.).

    Returns the standard (ok, reason, ticket) tuple:
      (True,  "voided",            ticket)  first-time void
      (True,  "already_voided",    ticket)  idempotent re-call
      (False, "checked_in",        ticket)  refuse to void a ticket
                                             whose holder is already
                                             inside — merchant must
                                             handle in person
      (False, "not_found",         None)

    Never decrements the occurrence.reserved_seats counter — that's
    the job of release_event_seats on order cancel. Voiding a single
    ticket leaves the seat "held" for audit purposes; the merchant
    can manually re-issue if needed.
    """
    from database import issued_tickets_collection
    from pymongo import ReturnDocument

    if not code:
        return False, "not_found", None
    code = code.strip().upper()

    now = utc_now()
    # Atomic valid -> voided
    updated = await issued_tickets_collection.find_one_and_update(
        {"organization_id": org_id, "code": code, "status": "valid"},
        {"$set": {
            "status": "voided",
            "voided_at": now,
            **({"void_reason": reason[:200]} if reason else {}),
        }},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    if updated is not None:
        logger.info("ticket_service: voided single ticket code=%s org=%s", code, org_id)
        return True, "voided", updated

    # Disambiguate failure
    existing = await issued_tickets_collection.find_one(
        {"organization_id": org_id, "code": code}, {"_id": 0},
    )
    if existing is None:
        return False, "not_found", None
    if existing.get("status") == "voided":
        return True, "already_voided", existing
    if existing.get("status") == "checked_in":
        return False, "checked_in", existing
    return False, "invalid_status", existing


async def void_tickets_for_order(
    order_id: str,
    org_id: str,
) -> int:
    """Mark every ticket for this order as voided. Never deletes rows.

    Returns the number of tickets transitioned to voided. Already-
    voided tickets are a no-op (filter: status != voided).
    """
    from database import issued_tickets_collection

    now = utc_now()
    res = await issued_tickets_collection.update_many(
        {
            "organization_id": org_id,
            "order_id": order_id,
            "status": {"$ne": "voided"},
        },
        {"$set": {"status": "voided", "voided_at": now}},
    )
    count = int(getattr(res, "modified_count", 0) or 0)
    if count:
        logger.info(
            "ticket_service: voided %d tickets for cancelled order %s",
            count, order_id,
        )
    return count


async def check_in_ticket(
    *,
    code: str,
    org_id: str,
    occurrence_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[dict]]:
    """Atomic check-in for a ticket code.

    Returns:
      (True,  "ok",                   ticket)  first-time scan, ticket
                                                 now checked_in
      (True,  "already_checked_in",   ticket)  scanned again, no-op
      (False, "voided",               ticket)  belongs to cancelled order
      (False, "not_found",            None)    no such code in this org
      (False, "wrong_occurrence",     ticket)  code valid but for a
                                                 different event — door
                                                 scanner rejects when
                                                 `occurrence_id` filter
                                                 is supplied

    The atomic transition is a `find_one_and_update` with the filter
    status="valid", so two simultaneous scans at the door cannot both
    succeed on the first pass.
    """
    from database import issued_tickets_collection
    from pymongo import ReturnDocument

    if not code:
        return False, "not_found", None
    code = code.strip().upper()

    # First attempt: the happy path — atomic transition valid -> checked_in.
    filter_ = {
        "organization_id": org_id,
        "code": code,
        "status": "valid",
    }
    if occurrence_id:
        filter_["occurrence_id"] = occurrence_id

    now = utc_now()
    updated = await issued_tickets_collection.find_one_and_update(
        filter_,
        {"$set": {"status": "checked_in", "checked_in_at": now}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    if updated is not None:
        logger.info(
            "ticket_service: checked in code=%s order=%s",
            code, updated.get("order_id"),
        )
        return True, "ok", updated

    # Couldn't transition — disambiguate. Error path is allowed a
    # second read.
    existing = await issued_tickets_collection.find_one(
        {"organization_id": org_id, "code": code},
        {"_id": 0},
    )
    if existing is None:
        return False, "not_found", None
    if occurrence_id and existing.get("occurrence_id") != occurrence_id:
        return False, "wrong_occurrence", existing
    status = existing.get("status")
    if status == "checked_in":
        return True, "already_checked_in", existing
    if status == "voided":
        return False, "voided", existing
    # Catch-all for any unexpected state
    return False, "invalid_status", existing


async def list_tickets_for_order(order_id: str, org_id: str) -> List[dict]:
    """Return every ticket for an order — used by the buyer email
    rendering and the admin order detail view."""
    from database import issued_tickets_collection
    return await issued_tickets_collection.find(
        {"organization_id": org_id, "order_id": order_id},
        {"_id": 0},
    ).sort("seat_index", 1).to_list(None)


async def list_tickets_for_occurrence(
    occurrence_id: str,
    org_id: str,
    include_voided: bool = False,
) -> List[dict]:
    """Attendance list: every ticket for an occurrence. Used by the
    admin dashboard + the E5 check-in screen to show "23 of 30
    checked in"."""
    from database import issued_tickets_collection
    query = {"organization_id": org_id, "occurrence_id": occurrence_id}
    if not include_voided:
        query["status"] = {"$ne": "voided"}
    return await issued_tickets_collection.find(
        query, {"_id": 0},
    ).sort("seat_index", 1).to_list(None)


# ── QR generation ──────────────────────────────────────────────────────────


def generate_qr_png(payload: str, box_size: int = 8, border: int = 2) -> bytes:
    """Render `payload` as a QR code PNG (bytes).

    Defaults chosen for email embedding: box_size=8 gives a ~280-320px
    image for a short EVT-XXXX-XXXX code, which is crisp on retina and
    small enough to email. Never raises — on any library error returns
    a 1x1 transparent placeholder so the email still sends.
    """
    try:
        import qrcode
        import io

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(payload or "")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as exc:
        logger.warning("ticket_service: QR generation failed for %r: %s", payload, exc)
        # 1x1 transparent PNG fallback — keeps the email email-able.
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01"
            b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )


def qr_data_uri(payload: str, box_size: int = 8) -> str:
    """Return a data: URI suitable for <img src="..."> in an email."""
    import base64
    png = generate_qr_png(payload, box_size=box_size)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
