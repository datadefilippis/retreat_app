"""LS (14/9/2026) — bonifica una tantum dei link social gia' salvati.

In produzione 4 profili Instagram su 10 erano il solo nome utente (link
rotto sul sito) e gli altri portavano parametri di tracciamento. La
stessa funzione che da oggi normalizza al salvataggio
(services.social_links) passa una volta su tutte le organizzazioni.
Flag-gated (collezione migrations), idempotente; annota cosa ha cambiato.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_FLAG = "social_normalizzati_v1"


async def migrate_social_normalizzati_v1() -> None:
    from database import db
    from services.social_links import normalizza_social
    migrations = db["migrations"]
    if await migrations.find_one({"_id": _FLAG}):
        return
    cambiati = []
    async for org in db.organizations.find(
            {"$or": [{"public_profile.instagram": {"$nin": [None, ""]}},
                     {"public_profile.facebook": {"$nin": [None, ""]}},
                     {"public_profile.website": {"$nin": [None, ""]}}]},
            {"_id": 0, "id": 1, "name": 1, "public_profile.instagram": 1,
             "public_profile.facebook": 1, "public_profile.website": 1}):
        pp = org.get("public_profile") or {}
        nuovi = normalizza_social(pp)
        if not nuovi:
            continue
        await db.organizations.update_one(
            {"id": org["id"]},
            {"$set": {f"public_profile.{k}": v for k, v in nuovi.items()},
             "$push": {"public_profile.social_prima": {"quando": datetime.now(timezone.utc).isoformat(),
                                                       "prima": {k: pp.get(k) for k in nuovi}}}})
        cambiati.append({"org": org.get("name"), **{k: v for k, v in nuovi.items()}})
    await migrations.insert_one({"_id": _FLAG, "applied_at": datetime.now(timezone.utc),
                                 "cambiati": len(cambiati)})
    logger.info("migrate_social_normalizzati_v1: %s profili normalizzati: %s", len(cambiati), cambiati)
