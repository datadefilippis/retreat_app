"""Traduzione automatica dei contenuti ritiro (F5, 5/7/2026).

docs/DIRECTORY_DESIGN_PLAN.md §F5. Architettura:

  publish/update → job orario (scheduler esistente) → LLM (claude_client
  gia' in casa: budget guard, circuit breaker, costi) → collection
  content_translations con SOURCE HASH → la landing serve ?lang=en/de/fr
  col merge, fallback all'originale.

Regole:
  - invalidazione per hash: se il contenuto sorgente cambia, la
    traduzione si rigenera — MAI traduzioni stantie
  - il job e' best-effort e budget-cap per run: la pubblicazione non
    aspetta mai la traduzione
  - il NOME del ritiro non si traduce (e' il brand dell'operatore)
  - prompt conservativo: tradurre, mai inventare; struttura preservata
  - flag CONTENT_TRANSLATIONS_ENABLED + no-op se LLM non configurato
"""

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

from models.common import generate_id, utc_now
from services.scheduler_service import register_job

logger = logging.getLogger(__name__)

TARGET_LANGS = ("en", "de", "fr")
LANG_NAMES = {"en": "English", "de": "German", "fr": "French"}
MAX_TRANSLATIONS_PER_RUN = 12   # cap per run: 4 ritiri x 3 lingue


def _enabled() -> bool:
    # 6/7/2026 — decisione founder: traduzioni MANUALI, zero LLM, zero
    # costi. La pipeline resta nel codice ma e' SPENTA di default;
    # il serving pubblico non la legge piu' (manual_translations).
    return os.environ.get("CONTENT_TRANSLATIONS_ENABLED", "false").lower() \
        in ("1", "true", "on")


def build_source_fields(occ: Dict[str, Any],
                        product: Dict[str, Any]) -> Dict[str, Any]:
    """I campi traducibili, nella forma che verra' servita. Puro."""
    return {
        "description": (product or {}).get("description") or "",
        "long_description": occ.get("long_description") or "",
        "agenda": [{"time": a.get("time"), "title": a.get("title") or "",
                    "description": a.get("description") or ""}
                   for a in (occ.get("agenda") or [])],
        "included": list(occ.get("included") or []),
        "excluded": list(occ.get("excluded") or []),
        "faq": [{"q": f.get("q") or "", "a": f.get("a") or ""}
                for f in (occ.get("faq") or [])],
    }


def source_hash(fields: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(fields, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _has_content(fields: Dict[str, Any]) -> bool:
    return bool(fields.get("description") or fields.get("long_description")
                or fields.get("agenda") or fields.get("faq")
                or fields.get("included"))


_SYSTEM_PROMPT = """Sei un traduttore professionale per una piattaforma di ritiri benessere.
Traduci i VALORI del JSON dall'italiano alla lingua richiesta.

REGOLE FERREE:
- NON inventare, aggiungere o omettere contenuti: solo tradurre
- Preserva ESATTAMENTE la struttura JSON, le chiavi e l'ordine
- Preserva la formattazione markdown (##, **, -, elenchi)
- NON tradurre: orari, prezzi, nomi propri di persone e luoghi
- Tono: caldo e professionale, adatto al mondo del benessere
- Rispondi SOLO con il JSON tradotto, nessun testo prima o dopo"""


async def translate_fields(fields: Dict[str, Any], lang: str) -> Optional[Dict[str, Any]]:
    """Traduce via LLM. Ritorna il dict tradotto o None su errore/parse."""
    from services import claude_client

    user_msg = (f"Lingua di destinazione: {LANG_NAMES[lang]}\n\n"
                + json.dumps(fields, ensure_ascii=False, indent=1))
    try:
        raw = await claude_client.send_message(
            _SYSTEM_PROMPT, user_msg, max_tokens=4000, temperature=0.2,
        )
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        translated = json.loads(text)
        # la struttura DEVE combaciare: stesse chiavi, stesse cardinalita'
        if set(translated.keys()) != set(fields.keys()):
            logger.warning("traduzione %s: chiavi divergenti, scarto", lang)
            return None
        for key in ("agenda", "included", "excluded", "faq"):
            if len(translated.get(key) or []) != len(fields.get(key) or []):
                logger.warning("traduzione %s: cardinalita' %s divergente", lang, key)
                return None
        return translated
    except Exception as exc:
        logger.warning("traduzione %s fallita: %s", lang, exc)
        return None


async def get_translation(occurrence_id: str, lang: str,
                          expected_hash: str) -> Optional[Dict[str, Any]]:
    """La traduzione valida (hash combaciante) o None. Usata dalla landing."""
    if lang not in TARGET_LANGS:
        return None
    from database import db
    doc = await db.content_translations.find_one(
        {"occurrence_id": occurrence_id, "lang": lang,
         "source_hash": expected_hash},
        {"_id": 0, "fields": 1, "translated_at": 1},
    )
    return doc


async def run_translation_scan() -> Dict[str, int]:
    """Job orario: traduce i ritiri pubblicati futuri che ne hanno bisogno
    (nessuna traduzione per la lingua, o hash sorgente cambiato)."""
    from database import db, event_occurrences_collection, products_collection
    from services import claude_client

    summary = {"scanned": 0, "translated": 0, "skipped": 0, "errors": 0}
    if not _enabled() or not claude_client.is_available():
        return summary

    now_iso = utc_now().isoformat()[:16]
    occs = await event_occurrences_collection.find(
        {"status": "published", "start_at": {"$gte": now_iso}},
        {"_id": 0, "id": 1, "organization_id": 1, "product_id": 1,
         "long_description": 1, "agenda": 1, "included": 1,
         "excluded": 1, "faq": 1},
    ).to_list(500)
    prod_ids = list({o["product_id"] for o in occs})
    prods = {p["id"]: p for p in await products_collection.find(
        {"id": {"$in": prod_ids}}, {"_id": 0, "id": 1, "description": 1},
    ).to_list(500)}

    done = 0
    for occ in occs:
        if done >= MAX_TRANSLATIONS_PER_RUN:
            break
        summary["scanned"] += 1
        fields = build_source_fields(occ, prods.get(occ["product_id"], {}))
        if not _has_content(fields):
            continue
        h = source_hash(fields)
        for lang in TARGET_LANGS:
            if done >= MAX_TRANSLATIONS_PER_RUN:
                break
            existing = await db.content_translations.find_one(
                {"occurrence_id": occ["id"], "lang": lang,
                 "source_hash": h}, {"_id": 1},
            )
            if existing:
                summary["skipped"] += 1
                continue
            translated = await translate_fields(fields, lang)
            done += 1
            if not translated:
                summary["errors"] += 1
                continue
            # upsert: una traduzione per (occurrence, lang); l'hash nuovo
            # sostituisce il vecchio → mai traduzioni stantie
            await db.content_translations.update_one(
                {"occurrence_id": occ["id"], "lang": lang},
                {"$set": {
                    "id": generate_id(),
                    "organization_id": occ["organization_id"],
                    "occurrence_id": occ["id"],
                    "lang": lang,
                    "source_hash": h,
                    "fields": translated,
                    "translated_at": utc_now().isoformat(),
                }},
                upsert=True,
            )
            summary["translated"] += 1
            logger.info("traduzione %s per occ=%s completata", lang, occ["id"])
    return summary


@register_job("content-translation-scan", interval_seconds=3600)
async def content_translation_scan_job() -> Dict[str, int]:
    return await run_translation_scan()
