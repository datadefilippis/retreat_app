"""
MIGRAZIONI DEL CERCHIO (FV5, 10/9/2026 sera).

migrate_cerchio_alert_esplicito_v1 — l'avviso ritiri era acceso a chi
non l'aveva mai chiesto: lib/cerchio.js (iscriviESblocca) mandava
`wants_experiences: true` di default dai cancelli delle meditazioni, di
InvitoSound e delle guide, cioe' da form con la sola email. Risultato:
«6 iscritti dalle meditazioni vogliono i ritiri» nei numeri del lunedi',
e un benvenuto che avrebbe parlato di ritiri a chi cercava una
meditazione. Da oggi il flag viaggia solo quando un form lo CHIEDE; qui
si spegne a chi lo aveva preso «di passaggio»: porta senza domanda,
nessuna via scelta, nessuna regione. Una volta sola (collezione
migrations), e si annota sull'iscritto (spento_da_migrazione) per
poterlo spiegare.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_FLAG = "cerchio_alert_esplicito_v1"


async def migrate_cerchio_alert_esplicito_v1() -> None:
    from database import db
    from services.sequenze import PORTE_MEDITAZIONI
    migrations = db["migrations"]
    if await migrations.find_one({"_id": _FLAG}):
        return
    porte = tuple(PORTE_MEDITAZIONI) + ("account_", "signup_pro")
    n = 0
    async for sub in db.aurya_subscribers.find(
            {"preferences.retreat_alert.enabled": True},
            {"_id": 0, "email": 1, "source": 1, "profile.interests": 1,
             "preferences.retreat_alert.regions": 1}):
        source = (sub.get("source") or "").lower()
        if not any(source.startswith(p) for p in porte):
            continue
        if (sub.get("profile") or {}).get("interests"):
            continue
        if ((sub.get("preferences") or {}).get("retreat_alert") or {}).get("regions"):
            continue
        await db.aurya_subscribers.update_one(
            {"email": sub["email"]},
            {"$set": {"preferences.retreat_alert.enabled": False,
                      "preferences.retreat_alert.spento_da_migrazione": _FLAG}})
        n += 1
    await migrations.insert_one({"_id": _FLAG, "applied_at": datetime.now(timezone.utc), "spenti": n})
    logger.info("migrate_cerchio_alert_esplicito_v1: avviso ritiri spento a %s iscritti mai interpellati", n)
