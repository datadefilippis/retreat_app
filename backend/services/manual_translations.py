"""Traduzioni MANUALI dell'operatore (6/7/2026).

Decisione founder: zero LLM, zero costi. L'operatore inserisce lui
stesso i testi nelle lingue che vuole offrire; quelle lingue sono le
lingue che ACCETTA per il suo prodotto:
  - vista in lingua X → compaiono solo prodotti con traduzione X
    (l'italiano, lingua sorgente, e' sempre disponibile)
  - il serving fa il merge dei campi tradotti, fallback italiano MAI
    (se manca la lingua il prodotto non appare — coerenza promessa)
"""

from typing import Any, Dict, List, Optional

SUPPORTED_LANGS = ("en", "de", "fr")
TRANSLATABLE_FIELDS = {"description": 2000, "long_description": 5000}


def sanitize_translations(raw: Optional[dict]) -> Optional[dict]:
    """Whitelist lingue+campi+lunghezze. None se vuoto."""
    if not isinstance(raw, dict):
        return None
    out: Dict[str, Dict[str, str]] = {}
    for lang, fields in raw.items():
        if lang not in SUPPORTED_LANGS or not isinstance(fields, dict):
            continue
        clean = {}
        for f, max_len in TRANSLATABLE_FIELDS.items():
            val = fields.get(f)
            if isinstance(val, str) and val.strip():
                clean[f] = val.strip()[:max_len]
        if clean:
            out[lang] = clean
    return out or None


def available_languages(product: Dict[str, Any]) -> List[str]:
    """it + le lingue con almeno la description tradotta."""
    langs = ["it"]
    for lang, fields in (product.get("translations") or {}).items():
        if lang in SUPPORTED_LANGS and (fields or {}).get("description"):
            langs.append(lang)
    return langs


def is_available_in(product: Dict[str, Any], lang: Optional[str]) -> bool:
    if not lang or lang == "it":
        return True
    return lang in available_languages(product)


def merge_language(product: Dict[str, Any], lang: Optional[str]) -> Dict[str, Any]:
    """Prodotto coi campi nella lingua richiesta (se offerta)."""
    if not lang or lang == "it":
        return product
    tr = (product.get("translations") or {}).get(lang) or {}
    if not tr:
        return product
    merged = {**product}
    for f in TRANSLATABLE_FIELDS:
        if tr.get(f):
            merged[f] = tr[f]
    return merged
