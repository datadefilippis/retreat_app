"""
Track E Step 1.3 — Full-text search on embed /products endpoint.

Pre-E1.3 il widget embed forniva solo filter category + type + sort
predeterminati. Merchant non poteva offrire al customer la keyword
search "pizza", "pasta", "rossa". Per consolidamento commerce serve
search nativa coerente con l'esperienza utente moderno.

Design choices
==============

Mongo `$text` operator (NOT regex):
  - Sicuro from injection (operator-based, non concatena query string)
  - Stemming linguistico nativo (es. "panini" → match "panino", "panini")
  - Phrase support con quotes (es. q=`"farina 00"`)
  - Exclusion support con `-` prefix (es. q=`pasta -glutine`)
  - Score-based ranking (textScore)

Text index requirements
=======================

Mongo permette UN SOLO text index per collection. Indice canonical:

    products_collection.create_index(
        [("name", "text"), ("description", "text")],
        weights={"name": 3, "description": 1},
        default_language="italian",
    )

Razionale weights:
  - name match = 3x più rilevante di description match
  - "pizza" nel name ranked higher di "pizza" nel description
  - Pinned dal sentinel (anti-drift se qualcuno cambia equilibrio
    senza review consapevole UX)

Razionale language italian:
  - Stemmer italiano per i nostri merchant target (apertura Italia)
  - Stopwords italiane ("il", "la", "di", ecc.) ignorate
  - V2 multi-language: switch to "none" + lemmatization Python lato
    application (heavier, defer until international expansion)

Backward compatibility
======================

q optional. Default behavior preservato: q assente → no $text filter
→ stessa query Mongo del pre-E1.3. Sort default "name". Zero impact su
SDK embed esistenti che non passano q.

Security
========

- Length cap 200 char: anti-DOS via search string giganti
- Operator-based (no string concat): Mongo $text non vulnerable
- Multi-tenant: caller deve combinare con organization_id filter
  (the $text non scope auto). Sentinel pin.

Public API
==========

    MAX_SEARCH_LENGTH = 200
    SORT_MODE_RELEVANCE = "relevance"  # canonical sort key per ranking

    normalize_search_query(q) -> str | None
        Strip whitespace, truncate, return None se vuoto.

    build_text_search_match(q) -> dict
        Returns {} se q None/empty, {"$text": {...}} altrimenti.

    is_search_active(q) -> bool
        Helper: True se q "real" (normalize non-None).
"""

from typing import Optional


# Length cap — caller HTTP layer dovrebbe gia' truncare ma DEFENSE
# IN DEPTH al service level. Limite generoso: query reali in produzione
# raramente >50 char.
MAX_SEARCH_LENGTH = 200

# Sort mode canonical name per ranking-by-relevance. Aggiunto al
# whitelist EMBED_PRODUCT_SORT_MODES in embed_init_service. Quando
# q assente, fallback a default "name" (vedi _sort_spec).
SORT_MODE_RELEVANCE = "relevance"


def normalize_search_query(q: Optional[str]) -> Optional[str]:
    """Normalize a raw search input to canonical form or None.

    Rules:
      - None / non-str → None
      - Empty string after strip → None
      - Trim leading/trailing whitespace
      - Truncate to MAX_SEARCH_LENGTH (silent — UI dovrebbe gia'
        validare ma defense in depth).

    Returns:
        str (normalized, non-empty) OR None (treat as no search).

    Example:
        normalize_search_query("  pizza  ") → "pizza"
        normalize_search_query("") → None
        normalize_search_query(None) → None
        normalize_search_query("a" * 500) → "aaa...aaa" (200 chars)
    """
    if q is None or not isinstance(q, str):
        return None
    stripped = q.strip()
    if not stripped:
        return None
    if len(stripped) > MAX_SEARCH_LENGTH:
        return stripped[:MAX_SEARCH_LENGTH]
    return stripped


def is_search_active(q: Optional[str]) -> bool:
    """True se q (post-normalize) e' una search reale.

    Helper per branching logic: callers possono check senza ri-normalizzare.
    """
    return normalize_search_query(q) is not None


def build_text_search_match(q: Optional[str]) -> dict:
    """Build the Mongo match clause for full-text search.

    Returns:
        - {} se q None/empty (no filter, caller combina con altri match)
        - {"$text": {"$search": <normalized>}} altrimenti

    NB: Il caller DEVE combinare con organization_id filter:

        match = {"organization_id": org_id}
        match.update(build_text_search_match(q))
        # → {"organization_id": org_id, "$text": {"$search": "pizza"}}

    Mongo `$text` operator e' SAFE from injection (no string concat).
    Special syntax Mongo supportata in input (phrase quotes, exclusion -)
    e' feature, non bug.
    """
    normalized = normalize_search_query(q)
    if not normalized:
        return {}
    return {"$text": {"$search": normalized}}


def text_score_projection() -> dict:
    """Projection fragment to include textScore meta in find results.

    Use only when q active (Mongo error if $meta:textScore senza $text
    match upstream).

    Pattern usage:
        projection = _public_card_projection()
        if is_search_active(q):
            projection["score"] = {"$meta": "textScore"}
    """
    return {"score": {"$meta": "textScore"}}


def relevance_sort_spec() -> list:
    """Mongo sort spec for relevance ranking (score DESC).

    Mongo richiede sort by {"$meta": "textScore"} per ranking by relevance.
    Fallback sort secondario "name" ASC in caso di score ties.
    """
    return [("score", {"$meta": "textScore"}), ("name", 1)]


__all__ = [
    "MAX_SEARCH_LENGTH",
    "SORT_MODE_RELEVANCE",
    "normalize_search_query",
    "is_search_active",
    "build_text_search_match",
    "text_score_projection",
    "relevance_sort_spec",
]
