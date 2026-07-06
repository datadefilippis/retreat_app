"""Email del ciclo pagamenti (Fase 2 S3) — promemoria, solleciti, at-risk.

Riusa l'infrastruttura di order_email_service (contesto store, i18n,
wrapper brand, retry Brevo). Nelle email il pagamento viaggia SEMPRE come
link /pay/{token} (session Stripe generata fresca al click — mai URL
Stripe grezzi che scadono in 24h).
"""

import logging
from typing import Any, Dict, Optional

from services.order_email_service import (
    _fmt_short_date_localized,
    _fmt_total,
    _get_customer_email_and_locale,
    _load_store_context,
    _t,
    _wrap_template,
)
from services.email_service import send_email
from services.url_builder import build_public_url

logger = logging.getLogger(__name__)


def pay_url_for_row(row: Dict[str, Any]) -> str:
    return build_public_url(f"/api/public/pay/{row.get('pay_token', '')}")


async def send_payment_reminder(
    order: Optional[dict],
    schedule_doc: dict,
    row: dict,
    *,
    phase: str,          # remind_t7 | remind_t0 | sollecito_t3
) -> None:
    """Promemoria/sollecito al partecipante con bottone Paga ora."""
    if not order:
        return
    org_id = schedule_doc["organization_id"]
    try:
        ctx = await _load_store_context(org_id, store_id=order.get("store_id"))
        email, locale = await _get_customer_email_and_locale(order)
        if not email:
            return
        currency = schedule_doc.get("currency") or "EUR"
        amount = _fmt_total(row.get("amount_minor", 0) / 100.0, currency, locale)
        due = _fmt_short_date_localized((row.get("due_at") or "")[:10], locale)
        url = pay_url_for_row(row)
        order_ref = order.get("order_number") or order.get("id", "")[:12]

        subject_key = {
            "remind_t7": "pay_reminder_subject_t7",
            "remind_t0": "pay_reminder_subject_t0",
            "sollecito_t3": "pay_sollecito_subject",
        }[phase]
        body_key = "pay_sollecito_body" if phase == "sollecito_t3" else "pay_reminder_body"

        html = _wrap_template(f"""
            <p>{_t("greeting", locale)},</p>
            <p>{_t(body_key, locale, label=row.get("label", ""), amount=amount,
                   due_date=due, order_ref=order_ref)}</p>
            <p style="text-align: center;">
                <a href="{url}" class="btn">{_t("pay_now_cta", locale)}</a>
            </p>
            <p style="color:#666; font-size:12px;">{_t("pay_reminder_footer", locale)}</p>
        """, locale, reply_to=ctx["reply_to"], store_name=ctx["store_name"])

        subject = _t(subject_key, locale, store_name=ctx["store_name"], amount=amount)
        send_email(email, subject, html, reply_to=ctx["reply_to"],
                   sender_name=ctx["sender_name"])
        logger.info("payment_email: %s sent to=%s order=%s row=%s",
                    phase, email, order.get("id"), row.get("seq"))
    except Exception as exc:
        logger.warning("payment_email: reminder failed (%s): %s", phase, exc)


async def send_at_risk_to_operator(
    order: Optional[dict],
    schedule_doc: dict,
    row: dict,
) -> None:
    """T+7: il dunning è esaurito — la palla passa all'operatore.
    Destinatari: notification_email dello store o gli admin dell'org
    (stessa risoluzione delle notifiche nuovo-ordine)."""
    if not order:
        return
    org_id = schedule_doc["organization_id"]
    try:
        ctx = await _load_store_context(org_id, store_id=order.get("store_id"))
        recipients = []
        if ctx.get("notification_email"):
            recipients = [ctx["notification_email"]]
        else:
            from database import users_collection
            cursor = users_collection.find(
                {"organization_id": org_id, "role": {"$in": ["admin"]},
                 "is_active": True},
                {"_id": 0, "email": 1},
            )
            admins = await cursor.to_list(10)
            recipients = [a["email"] for a in admins if a.get("email")]
        if not recipients:
            return

        # R2a: lingua dell'OPERATORE (stessa catena delle notifiche
        # nuovo-ordine: user.locale del destinatario → lingua storefront
        # → it) al posto dello storico hardcoded "it".
        from services.order_email_service import _resolve_merchant_locale
        locale = await _resolve_merchant_locale(
            order, org_id,
            notification_user_email=recipients[0] if recipients else None,
        )
        currency = schedule_doc.get("currency") or "EUR"
        amount = _fmt_total(row.get("amount_minor", 0) / 100.0, currency, locale)
        due = _fmt_short_date_localized((row.get("due_at") or "")[:10], locale)
        order_ref = order.get("order_number") or order.get("id", "")[:12]
        customer = order.get("customer_name") or ""

        html = _wrap_template(f"""
            <p>{_t("pay_atrisk_merchant_body", locale, customer=customer,
                   label=row.get("label", ""), amount=amount, due_date=due,
                   order_ref=order_ref)}</p>
            <p>{_t("pay_atrisk_merchant_actions", locale)}</p>
        """, locale, reply_to=None, store_name=ctx["store_name"])

        subject = _t("pay_atrisk_merchant_subject", locale,
                     customer=customer, amount=amount)
        for r in recipients:
            send_email(r, subject, html, sender_name=ctx["sender_name"])
        logger.info("payment_email: at_risk sent to=%s order=%s row=%s",
                    recipients, order.get("id"), row.get("seq"))
    except Exception as exc:
        logger.warning("payment_email: at_risk failed: %s", exc)
