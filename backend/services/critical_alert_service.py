"""
Critical alert service — persistent record + best-effort notification for
payment-side incidents that require human attention.

The canonical trigger today is `payment_collected_confirm_failed`:
  Stripe collected the customer's payment, but our own confirm_order step
  raised. The order sits truthfully (payment_intent=collected, status=draft)
  but without alerting, ops might not notice for hours while the customer
  sees "ordine ricevuto" yet no confirmation email arrives.

Design principles:
  - Never raise from inside this module. Caller has already survived a
    real incident; we must not double-fail its handler.
  - Persistent record first, notification second. If Brevo is down, ops
    still finds the alert in the DB / admin dashboard.
  - Optional: separate OPS_ALERT_EMAIL env var to route alerts to an
    operational inbox distinct from admin user accounts.

Collection shape (critical_alerts):
  {
    id: uuid,
    org_id: str,
    type: "payment_confirm_failed" | ...,
    order_id: str,
    event_id: str,
    error_detail: str,
    stripe_payment_intent_id: str | None,
    created_at: datetime,
    resolved_at: datetime | None,
    resolved_by: str | None,      # admin user_id when marked resolved
  }
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# Alert type constants — keep surface small, grow as new incident types emerge.
ALERT_PAYMENT_CONFIRM_FAILED = "payment_confirm_failed"
ALERT_CHARGE_DISPUTED = "charge_disputed"


async def emit_payment_confirm_failed(
    *,
    org_id: str,
    order_id: str,
    order_number: Optional[str],
    event_id: str,
    error_detail: str,
    stripe_payment_intent_id: Optional[str] = None,
    customer_email: Optional[str] = None,
    total: Optional[float] = None,
    currency: str = "EUR",
) -> None:
    """Record a payment_confirm_failed incident and notify ops + org admins.

    Guaranteed not to raise — callers are already handling a real incident
    and must not have their recovery path short-circuited by alert delivery.
    """
    try:
        await _record_alert(
            org_id=org_id,
            alert_type=ALERT_PAYMENT_CONFIRM_FAILED,
            order_id=order_id,
            event_id=event_id,
            error_detail=error_detail,
            stripe_payment_intent_id=stripe_payment_intent_id,
        )
    except Exception as exc:
        # If even the persistence layer is down, we can't do much — but the
        # original CRITICAL log from the caller still carries the evidence.
        logger.error(
            "critical_alert: failed to persist alert for order=%s: %s",
            order_id, exc,
        )

    try:
        await _send_notifications(
            org_id=org_id,
            order_id=order_id,
            order_number=order_number,
            error_detail=error_detail,
            stripe_payment_intent_id=stripe_payment_intent_id,
            customer_email=customer_email,
            total=total,
            currency=currency,
        )
    except Exception as exc:
        logger.error(
            "critical_alert: failed to send notifications for order=%s: %s",
            order_id, exc,
        )


async def emit_charge_disputed(
    *,
    org_id: str,
    order_id: str,
    order_number: Optional[str],
    event_id: str,
    dispute_reason: Optional[str] = None,
    dispute_amount: Optional[float] = None,
    currency: str = "EUR",
    stripe_payment_intent_id: Optional[str] = None,
    customer_email: Optional[str] = None,
) -> None:
    """Record a charge_disputed incident and notify ops + org admins.

    Disputes have a hard Stripe deadline (7 calendar days typically) to
    submit evidence. The email copy reflects the urgency; the record
    persists for the audit dashboard.

    Guaranteed not to raise — callers are webhook handlers and must not
    be blocked by notification failures.
    """
    detail_parts = []
    if dispute_reason:
        detail_parts.append(f"reason={dispute_reason}")
    if dispute_amount is not None:
        detail_parts.append(f"amount={dispute_amount:.2f} {currency}")
    error_detail = ", ".join(detail_parts) or "dispute opened"

    try:
        await _record_alert(
            org_id=org_id,
            alert_type=ALERT_CHARGE_DISPUTED,
            order_id=order_id,
            event_id=event_id,
            error_detail=error_detail,
            stripe_payment_intent_id=stripe_payment_intent_id,
        )
    except Exception as exc:
        logger.error(
            "critical_alert: failed to persist dispute alert for order=%s: %s",
            order_id, exc,
        )

    # Custom copy for disputes — urgency matters, different action required
    try:
        from services.email_service import send_email

        recipients = await _collect_recipients(org_id)
        if not recipients:
            logger.warning(
                "critical_alert: no recipients to notify for dispute order=%s org=%s",
                order_id, org_id,
            )
            return

        subject = (
            f"[AFianco] 🚨 Contestazione pagamento ricevuta — "
            f"{order_number or order_id[:8]}"
        )
        html = _build_dispute_html(
            order_id=order_id,
            order_number=order_number,
            dispute_reason=dispute_reason,
            dispute_amount=dispute_amount,
            currency=currency,
            stripe_payment_intent_id=stripe_payment_intent_id,
            customer_email=customer_email,
        )
        for email in recipients:
            try:
                send_email(email, subject, html)
            except Exception as exc:
                logger.warning(
                    "critical_alert: dispute send_email raised for %s: %s",
                    email, exc,
                )
    except Exception as exc:
        logger.error(
            "critical_alert: failed to send dispute notifications for order=%s: %s",
            order_id, exc,
        )


def _build_dispute_html(
    *,
    order_id: str,
    order_number: Optional[str],
    dispute_reason: Optional[str],
    dispute_amount: Optional[float],
    currency: str,
    stripe_payment_intent_id: Optional[str],
    customer_email: Optional[str],
) -> str:
    """Inline-styled HTML for dispute notification — urgency-first copy."""
    amount_fmt = (
        f"{dispute_amount:.2f} {currency}" if dispute_amount is not None else "—"
    )
    reason_row = ""
    if dispute_reason:
        reason_row = (
            f"<tr><td style='padding:4px 8px'><b>Motivazione</b></td>"
            f"<td style='padding:4px 8px'>{dispute_reason}</td></tr>"
        )
    pi_row = ""
    if stripe_payment_intent_id:
        pi_row = (
            f"<tr><td style='padding:4px 8px'><b>Payment Intent</b></td>"
            f"<td style='padding:4px 8px;font-family:monospace'>{stripe_payment_intent_id}</td></tr>"
        )
    cust_row = ""
    if customer_email:
        cust_row = (
            f"<tr><td style='padding:4px 8px'><b>Cliente</b></td>"
            f"<td style='padding:4px 8px'>{customer_email}</td></tr>"
        )
    order_ref = order_number or order_id
    return (
        "<div style='font-family:-apple-system,Arial,sans-serif;max-width:600px'>"
        "<h2 style='color:#b91c1c'>🚨 Contestazione pagamento ricevuta</h2>"
        "<p>Un cliente ha aperto una contestazione (dispute) su un pagamento "
        "ricevuto tramite AFianco. "
        "<b>Hai tipicamente 7 giorni per inviare le prove a Stripe, "
        "altrimenti la disputa verrà persa automaticamente e l'importo "
        "sarà restituito al cliente (più eventuali commissioni).</b></p>"
        "<table style='border-collapse:collapse;border:1px solid #ddd;margin-top:12px'>"
        f"<tr><td style='padding:4px 8px'><b>Ordine</b></td><td style='padding:4px 8px'>{order_ref}</td></tr>"
        f"<tr><td style='padding:4px 8px'><b>Importo contestato</b></td>"
        f"<td style='padding:4px 8px;color:#b91c1c'>{amount_fmt}</td></tr>"
        f"{reason_row}{cust_row}{pi_row}"
        "</table>"
        "<p style='margin-top:16px'><b>Azione richiesta:</b> accedi al tuo "
        "Stripe Dashboard dalla sezione Impostazioni → Apri Dashboard Stripe, "
        "e rispondi alla disputa inviando prove di consegna, comunicazioni "
        "col cliente, fotografie del prodotto, ecc.</p>"
        "</div>"
    )


async def _record_alert(
    *,
    org_id: str,
    alert_type: str,
    order_id: str,
    event_id: str,
    error_detail: str,
    stripe_payment_intent_id: Optional[str],
) -> None:
    """Insert an alert record. Idempotent on (order_id, event_id, type)."""
    from database import db
    from models.common import generate_id, utc_now

    collection = db.critical_alerts
    now = utc_now()

    # Idempotency: same (order_id, event_id, type) = already recorded.
    # Use insert with a pre-check rather than upsert so we don't re-trigger
    # duplicate notifications on webhook retries.
    existing = await collection.find_one(
        {"org_id": org_id, "order_id": order_id, "event_id": event_id, "type": alert_type},
        {"_id": 0, "id": 1},
    )
    if existing:
        logger.info(
            "critical_alert: %s for order=%s event=%s already recorded, skipping",
            alert_type, order_id, event_id,
        )
        return

    doc = {
        "id": generate_id(),
        "org_id": org_id,
        "type": alert_type,
        "order_id": order_id,
        "event_id": event_id,
        "error_detail": (error_detail or "")[:500],  # defensive truncation
        "stripe_payment_intent_id": stripe_payment_intent_id,
        "created_at": now,
        "resolved_at": None,
        "resolved_by": None,
    }
    await collection.insert_one(doc)
    logger.info(
        "critical_alert: recorded %s org=%s order=%s alert_id=%s",
        alert_type, org_id, order_id, doc["id"],
    )


async def _send_notifications(
    *,
    org_id: str,
    order_id: str,
    order_number: Optional[str],
    error_detail: str,
    stripe_payment_intent_id: Optional[str],
    customer_email: Optional[str],
    total: Optional[float],
    currency: str,
) -> None:
    """Send notification emails to org admins and (if set) OPS_ALERT_EMAIL."""
    from services.email_service import send_email

    recipients = await _collect_recipients(org_id)
    if not recipients:
        logger.warning(
            "critical_alert: no recipients to notify for order=%s org=%s",
            order_id, org_id,
        )
        return

    subject = f"[AFianco] Pagamento incassato — conferma ordine fallita: {order_number or order_id[:8]}"
    html = _build_alert_html(
        order_id=order_id,
        order_number=order_number,
        error_detail=error_detail,
        stripe_payment_intent_id=stripe_payment_intent_id,
        customer_email=customer_email,
        total=total,
        currency=currency,
    )

    for email in recipients:
        try:
            send_email(email, subject, html)
        except Exception as exc:
            # send_email is best-effort by design, but guard against unexpected
            # sync raises (e.g. Brevo client bug).
            logger.warning("critical_alert: send_email raised for %s: %s", email, exc)


async def _collect_recipients(org_id: str) -> list:
    """Return a deduped list of emails: org admins + OPS_ALERT_EMAIL."""
    from database import users_collection

    recipients = []
    async for user in users_collection.find(
        {"organization_id": org_id, "role": "admin", "is_active": {"$ne": False}},
        {"_id": 0, "email": 1},
    ):
        email = user.get("email")
        if email:
            recipients.append(email)

    ops_email = os.environ.get("OPS_ALERT_EMAIL", "").strip()
    if ops_email and ops_email not in recipients:
        recipients.append(ops_email)

    return recipients


def _build_alert_html(
    *,
    order_id: str,
    order_number: Optional[str],
    error_detail: str,
    stripe_payment_intent_id: Optional[str],
    customer_email: Optional[str],
    total: Optional[float],
    currency: str,
) -> str:
    """Minimal inline-styled HTML alert — readable in every email client."""
    total_fmt = ""
    if total is not None:
        total_fmt = f"{total:.2f} {currency}"

    pi_row = ""
    if stripe_payment_intent_id:
        pi_row = (
            f"<tr><td style='padding:4px 8px'><b>Payment Intent</b></td>"
            f"<td style='padding:4px 8px;font-family:monospace'>{stripe_payment_intent_id}</td></tr>"
        )

    cust_row = ""
    if customer_email:
        cust_row = (
            f"<tr><td style='padding:4px 8px'><b>Cliente</b></td>"
            f"<td style='padding:4px 8px'>{customer_email}</td></tr>"
        )

    total_row = ""
    if total_fmt:
        total_row = (
            f"<tr><td style='padding:4px 8px'><b>Importo</b></td>"
            f"<td style='padding:4px 8px'>{total_fmt}</td></tr>"
        )

    order_ref = order_number or order_id
    return (
        "<div style='font-family:-apple-system,Arial,sans-serif;max-width:600px'>"
        "<h2 style='color:#b91c1c'>⚠️ Pagamento incassato — conferma ordine fallita</h2>"
        "<p>Un pagamento è stato correttamente incassato da Stripe "
        "ma la piattaforma non è riuscita a completare la conferma dell'ordine. "
        "<b>Il cliente ha pagato ma non riceverà la conferma finale finché l'ordine non viene riconciliato manualmente.</b></p>"
        "<table style='border-collapse:collapse;border:1px solid #ddd;margin-top:12px'>"
        f"<tr><td style='padding:4px 8px'><b>Ordine</b></td><td style='padding:4px 8px'>{order_ref}</td></tr>"
        f"{total_row}{cust_row}{pi_row}"
        f"<tr><td style='padding:4px 8px;vertical-align:top'><b>Errore</b></td>"
        f"<td style='padding:4px 8px;font-family:monospace;color:#b91c1c'>{error_detail}</td></tr>"
        "</table>"
        "<p style='margin-top:16px'><b>Azione consigliata:</b> apri l'ordine in AFianco → "
        "sezione Pagamento → \"Riprova conferma ordine\". L'operazione è idempotente e sicura.</p>"
        "</div>"
    )
