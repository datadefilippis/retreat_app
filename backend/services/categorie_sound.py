"""MR4 (8/10/2026, piano refinement meditazioni) — LE CATEGORIE DELLE MEDITAZIONI.

Decisione del founder: le categorie le crea il system admin dalla Regia
(Sound → Categorie) e si assegnano quando si crea la meditazione; una sola
all'inizio, «Meditazioni guidate», le altre arrivano in prod senza deploy e
compaiono subito nella scelta. Stesso disegno del registro vivo delle
discipline (DV1): slug immutabile, mai cancellazioni (si spegne), ordine.

Vive in `sound_categorie`; cache in memoria con TTL di 60 s e ricarica
dopo ogni scrittura (prod: un worker). `intent` NON sparisce: resta
interno (motore, pagine vecchie); la casa e i filtri leggono `categoria`.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aurya.categorie_sound")

SEME = {"slug": "meditazioni-guidate", "label": "Meditazioni guidate",
        "descrizione": "Le meditazioni guidate dalla voce.", "tono": "salvia", "ordine": 1, "attiva": True}
TONI = ("salvia", "viola", "acqua", "oro")
LABEL_MIN, LABEL_MAX = 2, 60
DESCRIZIONE_MAX = 300
_TTL = 60.0
_cache: Dict[str, Any] = {"al": 0.0, "voci": []}


def slugify(label: str) -> str:
    from services.discipline_vive import slugify as s
    return s(label)


def slug_valido(slug: str) -> bool:
    from services.discipline_vive import slug_valido as v
    return v(slug)


async def _assicura_seme() -> None:
    from database import db
    from models.common import utc_now
    if await db.sound_categorie.count_documents({}) == 0:
        await db.sound_categorie.insert_one({**SEME, "created_at": utc_now(), "updated_at": utc_now()})
        logger.info("categorie_sound: seme «%s» piantato", SEME["slug"])


async def ricarica() -> List[dict]:
    from database import db
    await _assicura_seme()
    voci = []
    async for c in db.sound_categorie.find({}, {"_id": 0}).sort([("ordine", 1), ("label", 1)]):
        voci.append(c)
    _cache["voci"] = voci
    _cache["al"] = time.time()
    return voci


async def elenco(solo_attive: bool = True) -> List[dict]:
    if time.time() - _cache["al"] > _TTL or not _cache["voci"]:
        await ricarica()
    voci = _cache["voci"]
    return [c for c in voci if c.get("attiva", True)] if solo_attive else list(voci)


async def esiste(slug: Optional[str], solo_attive: bool = True) -> bool:
    if not slug:
        return False
    return any(c["slug"] == slug for c in await elenco(solo_attive))


async def etichette() -> Dict[str, str]:
    return {c["slug"]: c["label"] for c in await elenco(solo_attive=False)}


def valida_nuova(body: dict) -> dict:
    label = str(body.get("label") or "").strip()
    if not (LABEL_MIN <= len(label) <= LABEL_MAX):
        raise ValueError(f"Etichetta: da {LABEL_MIN} a {LABEL_MAX} caratteri.")
    slug = str(body.get("slug") or "").strip() or slugify(label)
    if not slug_valido(slug):
        raise ValueError("Slug non valido: minuscole, numeri e trattini.")
    tono = str(body.get("tono") or "oro")
    if tono not in TONI:
        raise ValueError(f"Tono sconosciuto: {', '.join(TONI)}.")
    try:
        ordine = int(body.get("ordine") or 100)
    except (TypeError, ValueError):
        raise ValueError("Ordine: un numero.")
    return {"slug": slug, "label": label, "descrizione": str(body.get("descrizione") or "").strip()[:DESCRIZIONE_MAX],
            "tono": tono, "ordine": ordine, "attiva": True}


def valida_modifica(body: dict) -> dict:
    out: Dict[str, Any] = {}
    if "label" in body:
        label = str(body.get("label") or "").strip()
        if not (LABEL_MIN <= len(label) <= LABEL_MAX):
            raise ValueError(f"Etichetta: da {LABEL_MIN} a {LABEL_MAX} caratteri.")
        out["label"] = label
    if "descrizione" in body:
        out["descrizione"] = str(body.get("descrizione") or "").strip()[:DESCRIZIONE_MAX]
    if "tono" in body:
        if body.get("tono") not in TONI:
            raise ValueError(f"Tono sconosciuto: {', '.join(TONI)}.")
        out["tono"] = body["tono"]
    if "ordine" in body:
        try:
            out["ordine"] = int(body.get("ordine"))
        except (TypeError, ValueError):
            raise ValueError("Ordine: un numero.")
    if "attiva" in body:
        out["attiva"] = bool(body.get("attiva"))
    if "slug" in body:
        raise ValueError("Lo slug è immutabile.")
    return out
