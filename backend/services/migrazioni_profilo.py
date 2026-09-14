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


def _stessa_citta(scritta, trovata) -> bool:
    """«Roma Capitale» ~ «Roma», «Collebeato (BS)» ~ «Collebeato»,
    «Sappada / Plodn / Sapade» ~ «Sappada»; «Bellinzona» vs «Roma» no."""
    import re as _re
    def _base(v):
        v = (v or "").lower()
        v = _re.split(r"[/(,]", v)[0]
        return _re.sub(r"[^a-z0-9àèéìòù]+", " ", v).strip()
    a, b = _base(scritta), _base(trovata)
    if not a or not b:
        return False
    return a == b or a.startswith(b) or b.startswith(a) or a.split()[0] == b.split()[0]


async def migrate_sedi_v1() -> None:
    """SD5 (14/9/2026) — integrazione, non reset: ogni profilo con una
    localita' riceve `sedi = [sede principale]` costruita da
    city/region/latitude/longitude, che restano IDENTICI (sono gli
    specchi). La regione mancante (11 profili su 13 in prod) si ricava
    dalle coordinate col reverse geocoding (cache, 1 req/s, best-effort:
    senza risposta resta vuota, mai un errore). `geo` diventa MultiPoint.
    Il valore precedente resta in `sedi_prima`. Flag-gated, idempotente."""
    from database import db
    from services.sedi import normalizza_sede, specchi
    from services.geocoding import reverse_geocode
    migrations = db["migrations"]
    flag = "sedi_v1"
    if await migrations.find_one({"_id": flag}):
        return
    fatti = []
    async for org in db.organizations.find(
            {"$or": [{"public_profile.city": {"$nin": [None, ""]}},
                     {"public_profile.region": {"$nin": [None, ""]}}],
             "public_profile.sedi.0": {"$exists": False}},
            {"_id": 0, "id": 1, "name": 1, "public_profile.city": 1,
             "public_profile.region": 1, "public_profile.latitude": 1,
             "public_profile.longitude": 1}):
        pp = org.get("public_profile") or {}
        raw = {"citta": pp.get("city"), "regione": pp.get("region"),
               "lat": pp.get("latitude"), "lng": pp.get("longitude")}
        sede = normalizza_sede(raw)
        if not sede:
            continue
        if not sede.get("regione") and sede.get("lat") is not None:
            dett = await reverse_geocode(sede["lat"], sede["lng"])
            # la regione si prende dalle coordinate SOLO se raccontano la
            # stessa citta' scritta dall'operatore: in prod «Bellinzona» ha
            # il punto a Roma (dato gia' sbagliato) e avrebbe preso «Lazio».
            # In caso di conflitto la regione resta vuota e si annota.
            if dett and _stessa_citta(sede.get("citta"), dett.get("citta")):
                sede = normalizza_sede({**raw, "regione": dett.get("regione"),
                                        "provincia": dett.get("provincia"),
                                        "paese": dett.get("paese")}) or sede
            elif dett:
                logger.warning("migrate_sedi_v1: %s — citta' «%s» ma coordinate a «%s»: regione lasciata vuota",
                               org.get("name"), sede.get("citta"), dett.get("citta"))
        sedi = [sede]
        set_ = {"public_profile.sedi": sedi,
                "public_profile.sedi_prima": {k: pp.get(k) for k in ("city", "region", "latitude", "longitude")},
                "public_profile.geo": specchi(sedi)["geo"],
                # la regione trovata si scrive anche nello specchio (era vuota)
                "public_profile.region": pp.get("region") or sede.get("regione")}
        await db.organizations.update_one({"id": org["id"]}, {"$set": set_})
        fatti.append({"org": org.get("name"), "sede": sede.get("etichetta")})
    await migrations.insert_one({"_id": flag, "applied_at": datetime.now(timezone.utc),
                                 "profili": len(fatti)})
    logger.info("migrate_sedi_v1: %s profili con sede principale: %s", len(fatti), fatti)
