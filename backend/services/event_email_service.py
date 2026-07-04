"""
Event Email Service — dedicated email helpers for events (G4).

Kept separate from order_email_service because the audience and
intent differ: orders emails are transactional per-order, event
emails are operational per-occurrence (single-ticket resend, mass
broadcast to every ticket holder of an occurrence). Sharing the
underlying `send_email` primitive keeps branding consistent.

Primitives:

  resend_ticket_email_by_code(code, org_id)
    Re-sends the single-ticket confirmation HTML (same rendering
    used by the original order-confirmed email, scoped to just the
    one ticket) to the holder's email address. Typical trigger: the
    customer lost the original email and asks the merchant for a
    copy. Idempotent — safe to call multiple times.

  broadcast_to_attendees(org_id, occurrence_id, template_key,
                          subject?, message?, filter_status?)
    Sends a mail-merged email to every holder of a ticket for the
    given occurrence. Status filter defaults to {valid, checked_in}
    (voided tickets excluded). Templates surface a pre-written body
    with placeholders, or `custom` allows the merchant to pass
    raw text. Returns counters: sent / skipped / errors.

Templates (G4):
  - `reminder`     — "Ci vediamo stasera!" + date, venue, code
  - `logistics`    — "Info pratiche per l'evento" + venue + notes
  - `cancellation` — "L'evento è stato annullato" + apology
  - `custom`       — merchant-provided subject + body

Every function is best-effort in the order-service tradition:
try/except per recipient, log failures, never raise. The HTTP layer
that calls this module surfaces the counters so the merchant knows
how many mails went through.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, List, Tuple

from services.email_service import send_email, _wrap_template, _t
from services.url_builder import build_public_url

logger = logging.getLogger(__name__)


# ── Locale resolution (Onda 2) ─────────────────────────────────────────────
#
# Event emails are operational: the merchant triggers a resend, a per-holder
# delivery, or a broadcast — and each recipient may speak a different
# language than the merchant. Resolution chain:
#
#   1. customer_account.locale — when an account exists for `holder_email`
#      (a returning customer who has explicitly chosen their language).
#   2. store.storefront_languages[0] — the storefront these tickets were
#      sold on. A DE storefront sends DE event emails by default.
#   3. "it" — final hardcoded fallback.
#
# Broadcasts use only steps 2-3 (one message, one locale) — a per-attendee
# locale lookup over hundreds of recipients would 10x the DB load for
# little practical gain when the storefront defines a primary language.


async def _resolve_event_email_locale(
    org_id: str,
    *,
    holder_email: Optional[str] = None,
    store_id: Optional[str] = None,
) -> str:
    """Resolve a locale for an event-related transactional email.

    Best-effort: any DB hiccup falls through to "it" rather than raising.
    Reuses `_resolve_store_locale` from order_email_service so the chain
    stays in lock-step with the order email path.
    """
    from services.order_email_service import _resolve_store_locale, _normalize_locale
    # Priority 1: customer_account matching holder_email
    if holder_email:
        try:
            from database import customer_accounts_collection
            account = await customer_accounts_collection.find_one(
                {"organization_id": org_id,
                 "email": holder_email.strip().lower()},
                {"_id": 0, "locale": 1},
            )
            if account:
                code = _normalize_locale(account.get("locale"))
                if code:
                    return code
        except Exception as exc:  # noqa: BLE001
            logger.debug("event_email: customer_account locale lookup failed: %s", exc)
    # Priority 2: storefront default
    code = await _resolve_store_locale(org_id, store_id)
    return code or "it"


# ── Single-ticket resend ──────────────────────────────────────────────────


async def resend_ticket_email_by_code(code: str, org_id: str) -> Tuple[bool, str]:
    """Send the single-ticket confirmation email to the holder.

    Returns (ok, reason):
      (True,  "sent")                — email dispatched
      (True,  "dispatched_logonly")  — BREVO key absent; logged but
                                        counted as ok from the
                                        caller's perspective
      (False, "not_found")           — no such code in this org
      (False, "no_email")            — ticket has no holder_email
      (False, "voided")              — don't resend voided tickets
      (False, "send_failed")         — email_service raised
    """
    from database import (
        issued_tickets_collection,
        event_occurrences_collection,
        products_collection,
        organizations_collection,
    )
    from services.ticket_service import qr_data_uri
    from services.order_email_service import _html_escape, _load_store_context

    if not code:
        return False, "not_found"
    code = code.strip().upper()

    ticket = await issued_tickets_collection.find_one(
        {"organization_id": org_id, "code": code},
        {"_id": 0},
    )
    if not ticket:
        return False, "not_found"
    if ticket.get("status") == "voided":
        return False, "voided"

    email = ticket.get("holder_email")
    if not email:
        return False, "no_email"

    occ = await event_occurrences_collection.find_one(
        {"id": ticket["occurrence_id"], "organization_id": org_id},
        {"_id": 0},
    ) or {}
    product = await products_collection.find_one(
        {"id": ticket.get("product_id"), "organization_id": org_id},
        {"_id": 0, "name": 1, "store_id": 1},
    ) or {}
    # Per-store branding (Onda 6): pulls store-level sender_name /
    # reply_to / store_name when the product is assigned to a store.
    ctx = await _load_store_context(org_id, store_id=product.get("store_id"))

    # Resolve recipient locale: account preference > storefront default >
    # "it". Per-recipient lookup so a returning DE customer reading on an
    # IT storefront gets DE; a guest on the same storefront gets IT.
    locale = await _resolve_event_email_locale(
        org_id,
        holder_email=ticket.get("holder_email"),
        store_id=product.get("store_id"),
    )

    event_name = product.get("name") or _t("event_email_fallback_event_name", locale)
    start_at = occ.get("start_at") or ""
    dt_line = start_at.replace("T", " \u00b7 ")[:16] if start_at else ""
    venue_parts = [p for p in [occ.get("venue_name"), occ.get("city"), occ.get("location")] if p][:2]
    venue_line = " \u00b7 ".join(venue_parts)

    tier = ticket.get("tier_label")
    seat_idx = int(ticket.get("seat_index") or 1)
    seat_count = int(ticket.get("seat_count") or 1)

    try:
        qr_src = qr_data_uri(code, box_size=6)
    except Exception:
        qr_src = ""

    holder_display = ticket.get("holder_name") or _t("event_email_greeting_attendee_fallback", locale)
    greeting_line = _t("event_email_greeting", locale, name=_html_escape(holder_display))
    intro_line = _t("event_email_ticket_resend_intro", locale, event=_html_escape(event_name))
    ticket_label = _t("event_email_ticket_label", locale)
    seat_hint = _t("event_email_ticket_seat_hint", locale, seat_index=seat_idx, seat_count=seat_count)
    qr_hint = _t("event_email_ticket_qr_hint", locale)

    body_html = f"""
    <p>{greeting_line}</p>
    <p>{intro_line}</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;">
      <tr>
        <td style="padding:16px;border:1px solid #d1d5db;border-radius:12px;background:#ffffff;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7280;margin-bottom:6px;">{ticket_label}</div>
          <h3 style="margin:0 0 8px 0;font-size:18px;color:#111827;">{_html_escape(event_name)}</h3>
          <div style="color:#374151;font-size:14px;">{_html_escape(dt_line)}</div>
          {f'<div style="color:#6b7280;font-size:13px;margin-top:2px;">{_html_escape(venue_line)}</div>' if venue_line else ""}
          <div style="height:12px;"></div>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="vertical-align:top;">
                      <div style="font-family:monospace;font-size:18px;font-weight:700;letter-spacing:1px;color:#111827;">{_html_escape(code)}</div>
                      {f'<div style="color:#6b7280;font-size:12px;margin-top:2px;">{_html_escape(tier)}</div>' if tier else ""}
                      <div style="color:#6b7280;font-size:11px;margin-top:4px;">{seat_hint}</div>
                    </td>
                    <td style="vertical-align:top;text-align:right;width:120px;">
                      {f'<img src="{qr_src}" width="110" height="110" alt="QR {_html_escape(code)}" style="display:block;border:1px solid #e5e7eb;border-radius:4px;" />' if qr_src else ""}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
          <div style="color:#6b7280;font-size:12px;margin-top:8px;">
            {qr_hint}
          </div>
        </td>
      </tr>
    </table>
    """

    html = _wrap_template(
        body_html, locale,
        reply_to=ctx["reply_to"],
        store_name=ctx["store_name"],
    )
    subject = _t("event_email_subject_ticket", locale, event=event_name)

    try:
        ok = send_email(email, subject, html,
                        reply_to=ctx["reply_to"],
                        sender_name=ctx["sender_name"])
        if ok is False:
            return False, "send_failed"
        logger.info("event_email: resent code=%s to=%s org=%s", code, email, org_id)
        return True, "sent"
    except Exception as exc:
        logger.warning("event_email: resend failed code=%s: %s", code, exc)
        return False, "send_failed"


# ── Broadcast ─────────────────────────────────────────────────────────────


def _render_template(
    template_key: str,
    *,
    event_name: str,
    dt_line: str,
    venue_line: str,
    holder_name: str,
    code: str,
    extra_message: Optional[str] = None,
    locale: str = "it",
) -> Tuple[str, str]:
    """Return (subject, html_body_inner) for a broadcast template.

    extra_message lets the merchant append a personal note on top of
    the pre-written body; it's wrapped in a <p> block. Custom
    template ignores the pre-written body entirely — extra_message
    IS the body.

    `locale` drives every translatable string. The broadcast caller
    resolves it once from the storefront defaults and passes the same
    value for every recipient (one message, one locale).
    """
    from services.order_email_service import _html_escape

    holder_display = holder_name or _t("event_email_greeting_attendee_fallback", locale)
    greeting = f'<p>{_t("event_email_greeting", locale, name=_html_escape(holder_display))}</p>'
    code_label = _t("event_email_broadcast_code_label", locale)
    event_box = f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;">
      <tr><td style="padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;">
        <strong>{_html_escape(event_name)}</strong><br>
        <span style="color:#6b7280;font-size:13px;">{_html_escape(dt_line)}</span>
        {f'<br><span style="color:#6b7280;font-size:13px;">{_html_escape(venue_line)}</span>' if venue_line else ""}
        {f'<br><span style="color:#6b7280;font-size:12px;font-family:monospace;">{code_label}: {_html_escape(code)}</span>' if code else ""}
      </td></tr>
    </table>
    """
    extra_block = f'<p>{_html_escape(extra_message)}</p>' if extra_message else ''

    if template_key == "reminder":
        subject = _t("event_email_broadcast_reminder_subject", locale, event=event_name)
        body = (
            greeting
            + f'<p>{_t("event_email_broadcast_reminder_body", locale)}</p>'
            + event_box
            + f'<p>{_t("event_email_broadcast_reminder_outro", locale)}</p>'
            + extra_block
        )
    elif template_key == "logistics":
        subject = _t("event_email_broadcast_logistics_subject", locale, event=event_name)
        body = (
            greeting
            + f'<p>{_t("event_email_broadcast_logistics_body", locale)}</p>'
            + event_box
            + f'<p>{_t("event_email_broadcast_logistics_outro", locale)}</p>'
            + extra_block
        )
    elif template_key == "cancellation":
        subject = _t("event_email_broadcast_cancellation_subject", locale, event=event_name)
        body = (
            greeting
            + f'<p>{_t("event_email_broadcast_cancellation_body", locale)}</p>'
            + event_box
            + f'<p>{_t("event_email_broadcast_cancellation_outro", locale)}</p>'
            + extra_block
        )
    else:
        # custom: no prebuilt body, merchant provides everything
        if extra_message:
            subject = extra_message.split("\n")[0][:120]
        else:
            subject = _t("event_email_broadcast_custom_subject_fallback", locale, event=event_name)
        body = (
            greeting
            + event_box
            + extra_block
        )

    return subject, body


async def broadcast_to_attendees(
    *,
    org_id: str,
    occurrence_id: str,
    template_key: str,
    message: Optional[str] = None,
    subject_override: Optional[str] = None,
    include_voided: bool = False,
    include_checked_in: bool = True,
) -> Dict[str, int]:
    """Send a templated email to every attendee of an occurrence.

    Returns counters: {target, sent, skipped_no_email, errors}.

    Deduplicates by holder_email so a customer with 3 tickets only
    receives one email per broadcast. Uses the tier/code of the FIRST
    ticket belonging to that email for the merge fields (tier name,
    code) — close-enough for a broadcast message.

    template_key ∈ {reminder, logistics, cancellation, custom}.
    For custom, `message` is mandatory and becomes both the subject
    (first line, max 120 chars) and the body.
    """
    from database import (
        issued_tickets_collection,
        event_occurrences_collection,
        products_collection,
    )
    from services.order_email_service import _load_store_context

    template_key = (template_key or "").strip().lower()
    if template_key not in {"reminder", "logistics", "cancellation", "custom"}:
        return {"target": 0, "sent": 0, "skipped_no_email": 0, "errors": 0,
                "error_message": "unknown_template"}

    if template_key == "custom" and not (message or "").strip():
        return {"target": 0, "sent": 0, "skipped_no_email": 0, "errors": 0,
                "error_message": "custom_requires_message"}

    # Load occurrence + product for merge context
    occ = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id}, {"_id": 0},
    )
    if not occ:
        return {"target": 0, "sent": 0, "skipped_no_email": 0, "errors": 0,
                "error_message": "occurrence_not_found"}

    product = await products_collection.find_one(
        {"id": occ.get("product_id"), "organization_id": org_id},
        {"_id": 0, "name": 1, "store_id": 1},
    ) or {}
    # One locale for the whole broadcast: storefront default of the
    # storefront these tickets were sold on. Per-recipient locale would
    # explode DB queries on big events for marginal gain.
    broadcast_locale = await _resolve_event_email_locale(
        org_id, store_id=product.get("store_id"),
    )
    event_name = product.get("name") or _t("event_email_fallback_event_name", broadcast_locale)
    start_at = occ.get("start_at") or ""
    dt_line = start_at.replace("T", " \u00b7 ")[:16] if start_at else ""
    venue_parts = [p for p in [occ.get("venue_name"), occ.get("city"), occ.get("location")] if p][:2]
    venue_line = " \u00b7 ".join(venue_parts)

    # Build audience — dedupe by email
    status_filter: List[str] = ["valid"]
    if include_checked_in:
        status_filter.append("checked_in")
    if include_voided:
        status_filter.append("voided")

    seen_emails: Dict[str, dict] = {}  # email -> ticket dict
    async for t in issued_tickets_collection.find(
        {"organization_id": org_id, "occurrence_id": occurrence_id,
         "status": {"$in": status_filter}},
        {"_id": 0},
    ):
        email = (t.get("holder_email") or "").strip().lower()
        if email and email not in seen_emails:
            seen_emails[email] = t

    # Per-store branding (Onda 6): broadcast picks up sender_name +
    # reply_to from the product's store when known. Single ctx for the
    # whole broadcast — same product = same store for every attendee.
    ctx = await _load_store_context(org_id, store_id=product.get("store_id"))

    counters = {
        "target": len(seen_emails),
        "sent": 0,
        "skipped_no_email": 0,
        "errors": 0,
    }

    if not seen_emails:
        return counters

    for email, ticket in seen_emails.items():
        subject, body = _render_template(
            template_key,
            event_name=event_name,
            dt_line=dt_line,
            venue_line=venue_line,
            holder_name=ticket.get("holder_name") or "",
            code=ticket.get("code") or "",
            extra_message=message,
            locale=broadcast_locale,
        )
        if subject_override:
            subject = subject_override
        html = _wrap_template(
            body, broadcast_locale,
            reply_to=ctx["reply_to"],
            store_name=ctx["store_name"],
        )
        try:
            ok = send_email(email, subject, html,
                            reply_to=ctx["reply_to"],
                            sender_name=ctx["sender_name"])
            if ok is False:
                counters["errors"] += 1
            else:
                counters["sent"] += 1
        except Exception as exc:
            counters["errors"] += 1
            logger.warning("event_email: broadcast to=%s failed: %s", email, exc)

    # Count attendees with no email as skipped. We build this AFTER
    # dedup, so the count is "distinct tickets we couldn't reach".
    async for t in issued_tickets_collection.find(
        {"organization_id": org_id, "occurrence_id": occurrence_id,
         "status": {"$in": status_filter},
         "$or": [{"holder_email": None}, {"holder_email": ""}]},
        {"_id": 0, "id": 1},
    ):
        counters["skipped_no_email"] += 1
    # Reflect the accurate target = sent + errors + skipped_no_email
    counters["target"] = counters["sent"] + counters["errors"] + counters["skipped_no_email"]

    logger.info(
        "event_email: broadcast occ=%s org=%s template=%s -> sent=%d errors=%d skipped=%d",
        occurrence_id, org_id, template_key,
        counters["sent"], counters["errors"], counters["skipped_no_email"],
    )
    return counters


# ── F1 Onda 8 — per-holder ticket delivery ────────────────────────────────


async def _render_personal_ticket_email_html(
    ticket: dict,
    event_name: str,
    dt_line: str,
    venue_line: str,
    ticket_url: str,
    locale: str = "it",
) -> str:
    """Render the body of a single-holder ticket email (link-based).
    Used both at order confirmation and at manual resend.

    `locale` drives every translatable string. Caller resolves it once
    per recipient (account preference > storefront default > "it").
    """
    from services.order_email_service import _html_escape

    holder_name = ticket.get("holder_name") or ""
    code = ticket.get("code", "")
    tier = ticket.get("tier_label")
    seat_idx = int(ticket.get("seat_index") or 1)
    seat_count = int(ticket.get("seat_count") or 1)

    seat_hint = (
        _t("event_email_ticket_seat_hint", locale,
           seat_index=seat_idx, seat_count=seat_count)
        if seat_count > 1 else ""
    )

    holder_display = holder_name or _t("event_email_greeting_attendee_fallback", locale)
    greeting_line = _t("event_email_greeting", locale, name=_html_escape(holder_display))
    intro_line = _t("event_email_ticket_personal_intro", locale, event=_html_escape(event_name))
    ticket_label = _t("event_email_ticket_label", locale)
    open_cta = _t("event_email_ticket_open_cta", locale)
    privacy_hint = _t("event_email_ticket_link_privacy_hint", locale)

    # Pre-compute the optional tier+seat strip outside the f-string —
    # f-string expression parts cannot contain backslash escapes
    # (Py 3.9 limitation), so the "\u00b7" literal would break parsing
    # if inlined. Building it here keeps the template clean.
    middle_dot = "\u00b7"
    if tier and seat_hint:
        tier_seat_inner = f"{_html_escape(tier)} {middle_dot} {seat_hint}"
    elif tier:
        tier_seat_inner = _html_escape(tier)
    elif seat_hint:
        tier_seat_inner = seat_hint
    else:
        tier_seat_inner = ""
    tier_seat_html = (
        f'<div style="color:#6b7280;font-size:12px;margin-top:6px;text-align:center;">{tier_seat_inner}</div>'
        if tier_seat_inner else ""
    )
    venue_html = (
        f'<div style="color:#6b7280;font-size:13px;margin-top:2px;">{_html_escape(venue_line)}</div>'
        if venue_line else ""
    )

    return f"""
    <p>{greeting_line}</p>
    <p>{intro_line}</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;">
      <tr>
        <td style="padding:20px;border:1px solid #d1d5db;border-radius:12px;background:#ffffff;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#6b7280;margin-bottom:6px;">{ticket_label}</div>
          <h3 style="margin:0 0 8px 0;font-size:18px;color:#111827;">{_html_escape(event_name)}</h3>
          <div style="color:#374151;font-size:14px;">{_html_escape(dt_line)}</div>
          {venue_html}
          <div style="height:16px;"></div>
          <div style="text-align:center;">
            <a href="{ticket_url}" style="display:inline-block;padding:12px 24px;background:#111827;color:#ffffff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;">{open_cta}</a>
          </div>
          <div style="color:#6b7280;font-size:11px;margin-top:10px;text-align:center;font-family:monospace;">{_html_escape(code)}</div>
          {tier_seat_html}
          <div style="color:#6b7280;font-size:12px;margin-top:14px;text-align:center;">
            {privacy_hint}
          </div>
        </td>
      </tr>
    </table>
    """


async def send_individual_tickets_for_order(
    order: dict,
    org_id: str,
    *,
    tickets: Optional[List[dict]] = None,
) -> dict:
    """F1 Onda 8 — send ONE personal email per issued ticket whose
    holder_email differs from the order's customer_email.

    Purpose: when a customer buys N tickets for N guests (each with their
    own email), each guest should get their own link — not be lost in a
    bulk email to the buyer.

    Skipped cases:
      - ticket has no holder_email
      - holder_email equals order.customer_email (already in main email)
      - ticket status is voided

    Concurrency: gather with a semaphore (=10) so a large batch doesn't
    saturate the SMTP provider.

    Updates delivery_status on each ticket: sent | unsent. Returns a
    counters dict for the caller to surface in logs and dashboards.
    """
    import asyncio
    from database import (
        issued_tickets_collection,
        event_occurrences_collection,
        products_collection,
    )
    from services.order_email_service import _load_store_context
    from models.common import utc_now

    order_id = order.get("id")
    if not order_id:
        return {"sent": 0, "skipped": 0, "errors": 0, "target": 0}

    # Acquire tickets (from stash if caller passed them; else load)
    if tickets is None:
        if order.get("_issued_tickets"):
            tickets = order["_issued_tickets"]
        else:
            tickets = await issued_tickets_collection.find(
                {"organization_id": org_id, "order_id": order_id},
                {"_id": 0},
            ).to_list(None)
    if not tickets:
        return {"sent": 0, "skipped": 0, "errors": 0, "target": 0}

    customer_email = (order.get("customer_email") or "").strip().lower()

    # Cache occurrence + product lookups so we don't re-query per ticket
    occ_cache: dict = {}
    prod_cache: dict = {}
    async def load_event_info(occ_id: str, prod_id: str):
        if occ_id not in occ_cache:
            occ_cache[occ_id] = await event_occurrences_collection.find_one(
                {"id": occ_id, "organization_id": org_id},
                {"_id": 0, "start_at": 1, "end_at": 1, "venue_name": 1,
                 "address": 1, "city": 1, "location": 1},
            ) or {}
        if prod_id not in prod_cache:
            prod_cache[prod_id] = await products_collection.find_one(
                {"id": prod_id, "organization_id": org_id},
                {"_id": 0, "name": 1, "store_id": 1},
            ) or {}
        return occ_cache[occ_id], prod_cache[prod_id]

    # Per-store branding (Onda 6): the order's `store_id` is the right
    # source — every ticket on the same order belongs to the same store
    # (orders cannot mix products from sibling stores in the same cart),
    # so a single ctx is correct. Falls back to org-level when missing.
    ctx = await _load_store_context(org_id, store_id=order.get("store_id"))

    # Cache the storefront-default locale by store_id so we don't re-query
    # `stores` for every recipient. When the holder has a customer_account
    # we still defer to that account's locale instead.
    store_locale_cache: dict = {}
    async def resolve_locale_for_holder(holder_email: str, store_id: Optional[str]) -> str:
        cache_key = (holder_email or "").strip().lower(), store_id or ""
        if cache_key in store_locale_cache:
            return store_locale_cache[cache_key]
        loc = await _resolve_event_email_locale(
            org_id, holder_email=holder_email, store_id=store_id,
        )
        store_locale_cache[cache_key] = loc
        return loc

    sem = asyncio.Semaphore(10)
    counters = {"sent": 0, "skipped": 0, "errors": 0, "target": 0}

    async def deliver(t: dict):
        nonlocal counters
        if t.get("status") == "voided":
            counters["skipped"] += 1
            return
        holder_email = (t.get("holder_email") or "").strip()
        if not holder_email:
            counters["skipped"] += 1
            return
        # Skip tickets whose holder matches the main customer — already in
        # the order confirmation email.
        if holder_email.lower() == customer_email:
            counters["skipped"] += 1
            return
        token = t.get("access_token")
        if not token:
            counters["skipped"] += 1
            return

        counters["target"] += 1
        async with sem:
            occ, prod = await load_event_info(t.get("occurrence_id"), t.get("product_id"))
            recipient_locale = await resolve_locale_for_holder(
                holder_email, prod.get("store_id"),
            )
            event_name = prod.get("name") or _t("event_email_fallback_event_name", recipient_locale)
            start_at = occ.get("start_at") or ""
            dt_line = start_at.replace("T", " \u00b7 ")[:16] if start_at else ""
            venue_parts = [p for p in [occ.get("venue_name"), occ.get("city"), occ.get("location")] if p][:2]
            venue_line = " \u00b7 ".join(venue_parts)
            ticket_url = build_public_url(f"/t/{token}")

            body = await _render_personal_ticket_email_html(
                t, event_name, dt_line, venue_line, ticket_url,
                locale=recipient_locale,
            )
            html = _wrap_template(body, recipient_locale,
                                  reply_to=ctx["reply_to"],
                                  store_name=ctx["store_name"])
            subject = _t("event_email_subject_ticket", recipient_locale, event=event_name)

            now = utc_now().isoformat()
            try:
                ok = send_email(
                    holder_email, subject, html,
                    reply_to=ctx["reply_to"],
                    sender_name=ctx["sender_name"],
                )
                status_code = "sent" if ok is not False else "unsent"
                if ok is False:
                    counters["errors"] += 1
                else:
                    counters["sent"] += 1
            except Exception as exc:
                logger.warning(
                    "event_email: individual ticket send failed code=%s to=%s: %s",
                    t.get("code"), holder_email, exc,
                )
                counters["errors"] += 1
                status_code = "unsent"

            # Persist delivery_status so the dashboard can show "X/Y inviate"
            try:
                await issued_tickets_collection.update_one(
                    {"organization_id": org_id, "id": t.get("id")},
                    {"$set": {
                        "delivery_status": status_code,
                        "delivery_last_attempt_at": now,
                    }},
                )
            except Exception as exc:
                logger.warning(
                    "event_email: failed to persist delivery_status for code=%s: %s",
                    t.get("code"), exc,
                )

    await asyncio.gather(*(deliver(t) for t in tickets))

    logger.info(
        "event_email: individual tickets order=%s org=%s -> sent=%d errors=%d skipped=%d target=%d",
        order_id, org_id, counters["sent"], counters["errors"],
        counters["skipped"], counters["target"],
    )
    return counters
