"""
IL PROMEMORIA DEL CERCHIO (CN2, 3/9/2026, piano IL CERCHIO).

In produzione 6 iscritti su 9 non avevano mai confermato l'email: il
doppio opt-in perdeva due terzi. Una sola email di promemoria, una
sola volta, a chi e' «pending» da almeno 48 ore e da non piu' di 7
giorni (oltre, insistere e' rumore): «ti manca un clic». Mai due
promemoria alla stessa email (reminder_sent_at), mai a chi non ha
dato il consenso, mai a chi ha gia' confermato o si e' cancellato.

Decisione founder (3/9): «promemoria a 48h: sì, una sola email».

C4 (24/9, strada B): con CERCHIO_SINGOLO_OPTIN acceso la Lettera arriva
gia' da subito, quindi il promemoria cambia parole (il clic apre solo i
contenuti riservati, non «l'ingresso»), e accanto al promemoria vive la
SOSPENSIONE: chi e' pending da 90 giorni senza mai aver verificato viene
segnato `sospeso_at` (mai cancellato) e smette di ricevere email.
Spento: parole e comportamento di sempre.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

logger = logging.getLogger(__name__)

REMINDER_AFTER_HOURS = 48
REMINDER_WINDOW_DAYS = 7
_MAX_PER_TICK = 200

SOSPENSIONE_DOPO_GIORNI = 90
_MAX_SOSPENSIONI_PER_TICK = 200


def _singolo_optin() -> bool:
    from services.sequenze import singolo_optin
    return singolo_optin()


def _testo_promemoria(saluto: str, url: str, link_block: str):
    """(oggetto, corpo) secondo l'interruttore. Spento: le parole di
    sempre, byte per byte."""
    if _singolo_optin():
        return ("Un clic e si aprono le meditazioni riservate", f"""
            <p>{saluto}</p>
            <p>sei nel <strong>Cerchio di Aurya</strong>: la Lettera ti arriva
            già, senza fare nulla. Un clic qui sotto apre anche i contenuti
            riservati: le meditazioni, le guide, i ritiri in anteprima.</p>
            <p style="text-align: center;">
                <a href="{url}" class="btn">Apro le meditazioni</a>
            </p>
            {link_block}
            <p>Se non ti interessano, non devi fare nulla: la Lettera
            continua ad arrivare e da lì ti cancelli con un clic.</p>
        """)
    return ("Ti manca un clic per entrare nel Cerchio di Aurya", f"""
            <p>{saluto}</p>
            <p>ti manca un clic per entrare nel <strong>Cerchio di Aurya</strong>:
            le meditazioni riservate, i ritiri e le esperienze in anteprima,
            la Lettera quando vale la pena.</p>
            <p style="text-align: center;">
                <a href="{url}" class="btn">Entro nel Cerchio</a>
            </p>
            {link_block}
            <p>Se non ti interessa piu', non devi fare nulla: e' l'ultima
            email che ricevi da noi.</p>
        """)


def _send_reminder_email(email: str, name, token: str) -> bool:
    try:
        from services.email_service import _link_block, _wrap_template, send_email
        from services.email_sequenze import _link, url_preferenze_nudo
        # C3: il link e' verificante (il clic prova che l'indirizzo e' suo)
        url = _link(email, f"/newsletter/conferma/{token}")
        saluto = f"Ciao {name.strip()}," if (name or "").strip() else "Ciao,"
        oggetto, corpo = _testo_promemoria(saluto, url, _link_block(url))
        # C1/C2: email editoriale → header List-Unsubscribe e niente
        # bypass del gate (un indirizzo rimbalzato non riceve il promemoria)
        send_email(email, oggetto, _wrap_template(corpo),
                   unsubscribe_url=url_preferenze_nudo(token))
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


async def run_cerchio_sospensione_sweep(now: datetime = None) -> Dict[str, int]:
    """C4: la sospensione a 90 giorni. Solo con l'interruttore acceso
    (spento, con il doppio opt-in, i pending non ricevono niente e non
    c'e' nulla da sospendere). Chi e' pending con consenso, iscritto da
    piu' di 90 giorni, mai verificato e non gia' sospeso, prende
    `sospeso_at`: SI SEGNA, NON SI CANCELLA. Max 200 per giro."""
    result = {"candidati": 0, "sospesi": 0}
    if not _singolo_optin():
        return result
    from database import db
    now = now or datetime.now(timezone.utc)
    soglia = now - timedelta(days=SOSPENSIONE_DOPO_GIORNI)
    filtro = {"status": "pending", "consent": True,
              "created_at": {"$lt": soglia},
              "verificato_at": {"$exists": False},
              "sospeso_at": {"$exists": False}}
    cursor = db.aurya_subscribers.find(filtro, {"_id": 0, "email": 1}).limit(_MAX_SOSPENSIONI_PER_TICK)
    async for doc in cursor:
        result["candidati"] += 1
        email = doc.get("email")
        if not email:
            continue
        # lo stesso filtro nell'update: mai sovrascrivere una sospensione,
        # mai sospendere chi nel frattempo ha verificato
        r = await db.aurya_subscribers.update_one(
            {"email": email, **filtro}, {"$set": {"sospeso_at": now}})
        if r.modified_count == 1:
            result["sospesi"] += 1
    if result["candidati"]:
        logger.info("cerchio_sospensione: %s", result)
    return result
