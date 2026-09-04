"""
IL PROMEMORIA DEL CERCHIO (CN2, 3/9/2026, piano IL CERCHIO).

In produzione 6 iscritti su 9 non avevano mai confermato l'email: il
doppio opt-in perdeva due terzi. Una sola email di promemoria, una
sola volta, a chi e' «pending» da almeno 48 ore e da non piu' di 7
giorni (oltre, insistere e' rumore): «ti manca un clic». Mai due
promemoria alla stessa email (reminder_sent_at), mai a chi non ha
dato il consenso, mai a chi ha gia' confermato o si e' cancellato.

Decisione founder (3/9): «promemoria a 48h: sì, una sola email».
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

logger = logging.getLogger(__name__)

REMINDER_AFTER_HOURS = 48
REMINDER_WINDOW_DAYS = 7
_MAX_PER_TICK = 200


def _send_reminder_email(email: str, name, token: str) -> bool:
    try:
        from services.email_service import _link_block, _wrap_template, send_email
        from services.url_builder import build_public_url
        url = build_public_url(f"/newsletter/conferma/{token}")
        saluto = f"Ciao {name.strip()}," if (name or "").strip() else "Ciao,"
        html = _wrap_template(f"""
            <p>{saluto}</p>
            <p>ti manca un clic per entrare nel <strong>Cerchio di Aurya</strong>:
            le meditazioni riservate, i ritiri e le esperienze in anteprima,
            la Lettera ogni due settimane.</p>
            <p style="text-align: center;">
                <a href="{url}" class="btn">Entro nel Cerchio</a>
            </p>
            {_link_block(url)}
            <p>Se non ti interessa piu', non devi fare nulla: e' l'ultima
            email che ricevi da noi.</p>
        """)
        send_email(email, "Ti manca un clic per entrare nel Cerchio di Aurya",
                   html, bypass_gate=True)
        return True
    except Exception as exc:                # noqa: BLE001
        logger.warning("cerchio_reminder: email failed for %s: %s",
                       email[:2] + "***", exc)
        return False


async def run_cerchio_reminder_sweep(now: datetime = None) -> Dict[str, int]:
    """Un giro: trova i pending nella finestra e manda UN promemoria."""
    from database import db
    from routers.subscribers import generate_subscriber_token

    now = now or datetime.now(timezone.utc)
    oldest = now - timedelta(days=REMINDER_WINDOW_DAYS)
    newest = now - timedelta(hours=REMINDER_AFTER_HOURS)
    result = {"candidates": 0, "sent": 0, "errors": 0}
    cursor = db.aurya_subscribers.find(
        {"status": "pending", "consent": True,
         "reminder_sent_at": {"$exists": False},
         "created_at": {"$gte": oldest, "$lte": newest}},
        {"_id": 0, "email": 1, "name": 1},
    ).limit(_MAX_PER_TICK)
    async for doc in cursor:
        result["candidates"] += 1
        email = doc.get("email")
        if not email:
            continue
        # si marca PRIMA di inviare: se l'invio va storto meglio un
        # promemoria perso che uno doppio
        marked = await db.aurya_subscribers.update_one(
            {"email": email, "reminder_sent_at": {"$exists": False}},
            {"$set": {"reminder_sent_at": now}})
        if marked.modified_count != 1:
            continue
        if _send_reminder_email(email, doc.get("name"),
                                generate_subscriber_token(email)):
            result["sent"] += 1
        else:
            result["errors"] += 1
    if result["candidates"]:
        logger.info("cerchio_reminder: %s", result)
    return result
