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
# Il founder (7/7): anche il TITOLO si traduce — "voglio poter modificare
# in multilingua entrambe". La description resta il gate delle lingue
# accettate (available_languages): il titolo da solo non accende la lingua.
TRANSLATABLE_FIELDS = {"name": 255, "description": 2000, "long_description": 5000}


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


# ── Contenuti pagina di vendita (occurrence): agenda / incluso / FAQ ────
# Traduzione olistica (decisione founder 6/7): l'operatore traduce i TESTI
# della pagina di vendita nelle tab lingua; la STRUTTURA (giorni, voci,
# orari, foto) vive solo sulla sorgente italiana. Il merge e' per indice
# con guardia di cardinalita': se la struttura tradotta non combacia con
# la sorgente (l'operatore ha cambiato il programma dopo aver tradotto),
# quel blocco fa fallback all'italiano — mai contenuti sfasati.

OCC_LIST_FIELDS = ("included", "excluded")
_MAXLEN = {"label": 80, "title": 200, "description": 500,
           "q": 300, "a": 1000, "line": 200}


def _clip(v, key):
    return v.strip()[:_MAXLEN[key]] if isinstance(v, str) and v.strip() else None


def sanitize_occurrence_translations(raw: Optional[dict]) -> Optional[dict]:
    """Whitelist lingue+forma+lunghezze dei contenuti tradotti. None se vuoto."""
    if not isinstance(raw, dict):
        return None
    out: Dict[str, Dict[str, Any]] = {}
    for lang, blocks in raw.items():
        if lang not in SUPPORTED_LANGS or not isinstance(blocks, dict):
            continue
        clean: Dict[str, Any] = {}
        agenda = blocks.get("agenda")
        if isinstance(agenda, list):
            days = []
            for d in agenda[:21]:
                if not isinstance(d, dict):
                    days.append({"label": None, "items": []})
                    continue
                items = []
                for i in (d.get("items") or [])[:40]:
                    if not isinstance(i, dict):
                        i = {}
                    items.append({"title": _clip(i.get("title"), "title"),
                                  "description": _clip(i.get("description"), "description")})
                days.append({"label": _clip(d.get("label"), "label"), "items": items})
            if any(d["label"] or any(x["title"] or x["description"] for x in d["items"])
                   for d in days):
                clean["agenda"] = days
        for f in OCC_LIST_FIELDS:
            vals = blocks.get(f)
            if isinstance(vals, list):
                lines = [_clip(v, "line") or "" for v in vals[:20]]
                if any(lines):
                    clean[f] = lines
        faq = blocks.get("faq")
        if isinstance(faq, list):
            entries = []
            for e in faq[:15]:
                if not isinstance(e, dict):
                    e = {}
                entries.append({"q": _clip(e.get("q"), "q"),
                                "a": _clip(e.get("a"), "a")})
            if any(e["q"] or e["a"] for e in entries):
                clean["faq"] = entries
        if clean:
            out[lang] = clean
    return out or None


def merge_occurrence_language(occ: Dict[str, Any], lang: Optional[str]) -> Dict[str, Any]:
    """Occurrence coi blocchi testuali nella lingua richiesta.

    Merge per indice, guardia di cardinalita' per blocco: struttura
    divergente → quel blocco resta italiano. Mai eccezioni: la landing
    non deve rompersi per una traduzione stantia.
    """
    if not lang or lang == "it":
        return occ
    tr = (occ.get("translations") or {}).get(lang) or {}
    if not tr:
        return occ
    merged = {**occ}
    src_agenda = occ.get("agenda") or []
    tr_agenda = tr.get("agenda")
    if isinstance(tr_agenda, list) and len(tr_agenda) == len(src_agenda):
        days = []
        ok = True
        for sd, td in zip(src_agenda, tr_agenda):
            s_items = sd.get("items") or []
            t_items = (td or {}).get("items") or []
            if len(s_items) != len(t_items):
                ok = False
                break
            days.append({
                **sd,
                "label": (td or {}).get("label") or sd.get("label"),
                "items": [{**si,
                           "title": (ti or {}).get("title") or si.get("title"),
                           "description": (ti or {}).get("description") or si.get("description")}
                          for si, ti in zip(s_items, t_items)],
            })
        if ok:
            merged["agenda"] = days
    for f in OCC_LIST_FIELDS:
        src_list = occ.get(f) or []
        tr_list = tr.get(f)
        if isinstance(tr_list, list) and len(tr_list) == len(src_list):
            merged[f] = [t or s for s, t in zip(src_list, tr_list)]
    src_faq = occ.get("faq") or []
    tr_faq = tr.get("faq")
    if isinstance(tr_faq, list) and len(tr_faq) == len(src_faq):
        merged["faq"] = [{**se,
                          "q": (te or {}).get("q") or se.get("q"),
                          "a": (te or {}).get("a") or se.get("a")}
                         for se, te in zip(src_faq, tr_faq)]
    return merged
