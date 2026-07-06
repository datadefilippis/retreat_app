"""Embed Init Service — Phase 1 Step 12 (2026-05-28).

Bootstrap data per il widget embed cross-origin (Stream A). Aggrega in 1
round-trip:
  - storefront meta (branding, lingue, contatti)
  - currency dell'org
  - lista product types disponibili per questo store
  - categories pubbliche con count + slug normalizzato
  - capabilities (cart_enabled, customer_auth_enabled, checkout_stripe_enabled)
  - fulfillment_modes supportati

NON include la lista prodotti (fetched lazy via /embed/products) per
permettere cache aggressiva del bootstrap (max-age=60s) e fast first paint.

Contract di sicurezza
=====================
- Multi-tenant: ogni query filtra esplicitamente su organization_id
- No PII leak: solo campi della "Public" projection mai admin fields
- Categories: distinct case-normalized, slug URL-safe ASCII

Performance
===========
- 2 round-trip Mongo: 1 per resolve org+store, 1 per aggregation categories
- Aggregation pipeline categories: pre-filtered su (org_id, is_published,
  is_active) → indice (organization_id, category) garantisce O(log n)
"""

from __future__ import annotations

import html
import json
import logging
import re
import unicodedata
from typing import Iterable, Optional
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)


# ── Constants exposed for sentinel pinning + handler reuse ──────────────

# Sort modes whitelist — handler rifiuta input fuori da questa set per
# evitare query injection (es. ?sort={"$where": "..."}). Cambiarne il
# contenuto = breaking change del widget filter UI.
EMBED_PRODUCT_SORT_MODES = frozenset({
    "name",         # alphabetical ASC (default)
    "price_asc",    # unit_price ASC, nulls last
    "price_desc",   # unit_price DESC, nulls last
    "newest",       # created_at DESC
    # Track E Step 1.3 — additive: relevance ranking quando q presente.
    # Quando q assente, fallback a "name" (no special behavior breaking
    # SDK esistenti).
    "relevance",    # textScore DESC (solo se search query presente)
})

# Pagination guard rails.
EMBED_PRODUCT_LIMIT_DEFAULT = 20
EMBED_PRODUCT_LIMIT_MAX = 100  # hard cap anti-scraping


# ── Category slug normalization ─────────────────────────────────────────

# Pattern di caratteri NON consentiti nello slug finale.
# Mantieni solo a-z, 0-9, hyphen.
_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9-]+")

# Pattern di hyphens consecutivi → collapsare a uno solo.
_SLUG_COLLAPSE_HYPHENS = re.compile(r"-{2,}")


def _normalize_category_slug(name: Optional[str]) -> str:
    """Convert a free-text category name into an URL-safe ASCII lowercase slug.

    Steps:
      1. NFD Unicode decomposition → separa accenti dai caratteri base
      2. ASCII-only (`.encode('ascii', 'ignore')`) → "Café" → "Cafe"
      3. Lowercase
      4. Sostituisci tutto ciò che NON è [a-z0-9-] con "-"
      5. Collapse hyphens consecutivi
      6. Strip hyphens ai bordi

    Esempi:
        "Catering"          → "catering"
        "Catering Servizi"  → "catering-servizi"
        "Café Italiano"     → "cafe-italiano"
        "100% Bio"          → "100-bio"
        "Pizza/Pasta!"      → "pizza-pasta"
        None / ""           → ""

    Idempotente: ``_normalize_category_slug(_normalize_category_slug(x))``
    ritorna sempre lo stesso valore di ``_normalize_category_slug(x)``.
    """
    if not name:
        return ""

    # 1. NFD decomposition + 2. ASCII strip
    nfd = unicodedata.normalize("NFD", str(name))
    ascii_only = nfd.encode("ascii", "ignore").decode("ascii")

    # 3. lowercase
    lower = ascii_only.lower()

    # 4. Replace invalid chars with hyphen
    cleaned = _SLUG_INVALID_CHARS.sub("-", lower)

    # 5. Collapse consecutive hyphens
    collapsed = _SLUG_COLLAPSE_HYPHENS.sub("-", cleaned)

    # 6. Strip leading/trailing hyphens
    return collapsed.strip("-")


# ── Categories aggregation ──────────────────────────────────────────────


async def _aggregate_categories(org_id: str, store_id: Optional[str]) -> list[dict]:
    """Aggregate distinct categories with product count for an org/store.

    Returns a list of dicts ordered by count DESC, name ASC:
      [{"name": "Catering", "slug": "catering", "count": 3}, ...]

    Filters: is_published=True AND is_active=True. Products with
    `category=None` or empty are excluded entirely (no "uncategorized" row).
    Multi-store: if a store_id is provided, only includes products
    assigned to this store (or globally assigned, i.e. store_ids empty).
    """
    from database import products_collection

    match: dict = {
        "organization_id": org_id,
        "is_published": True,
        "is_active": True,
        "category": {"$nin": [None, ""]},
    }
    # Multi-store scoping (v12.0 pattern)
    if store_id:
        match["$or"] = [
            {"store_ids": store_id},
            {"store_ids": {"$size": 0}},
            {"store_ids": {"$exists": False}},
        ]

    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]

    try:
        cursor = products_collection.aggregate(pipeline)
        rows = await cursor.to_list(length=200)  # 200 categorie distinct max è abbondante
    except Exception as exc:
        logger.warning(
            "embed_init: categories aggregation failed for org=%s: %s",
            org_id, exc,
        )
        return []

    # Normalize + merge slug collisions (es. "Catering" + "catering" → unico)
    # Strategia: prima occorrenza vince per il display name, count è la somma.
    by_slug: dict[str, dict] = {}
    for row in rows:
        raw_name = (row.get("_id") or "").strip()
        if not raw_name:
            continue
        slug = _normalize_category_slug(raw_name)
        if not slug:
            continue
        if slug in by_slug:
            by_slug[slug]["count"] += int(row.get("count", 0))
        else:
            by_slug[slug] = {
                "name": raw_name,
                "slug": slug,
                "count": int(row.get("count", 0)),
            }

    # Re-sort post-merge: count desc, name asc
    return sorted(
        by_slug.values(),
        key=lambda d: (-d["count"], d["name"].lower()),
    )


# ── Per-category thumbnail (lazy) ───────────────────────────────────────


async def _find_category_thumbnail(
    org_id: str,
    store_id: Optional[str],
    category_name: str,
) -> Optional[str]:
    """Resolve image_url of the first published product in this category.

    The lookup is case-insensitive on ``category`` so collisions ("Catering"
    vs "catering") are merged consistently with ``_aggregate_categories``.
    Returns the first non-null ``image_url`` sorted by name ASC, or None.

    Soft-fail on Mongo error → None (widget falls back to default tile).
    """
    if not category_name:
        return None

    from database import products_collection
    import re

    # Case-insensitive exact match on category name.
    # NOTE: re.escape is critical — merchant categories may contain regex
    # metacharacters that would otherwise produce invalid patterns or
    # accidental matches.
    cat_filter = {
        "$regex": f"^{re.escape(category_name)}$",
        "$options": "i",
    }

    match: dict = {
        "organization_id": org_id,
        "is_published": True,
        "is_active": True,
        "category": cat_filter,
        "image_url": {"$nin": [None, ""]},
    }
    if store_id:
        match["$or"] = [
            {"store_ids": store_id},
            {"store_ids": {"$size": 0}},
            {"store_ids": {"$exists": False}},
        ]

    try:
        doc = await products_collection.find_one(
            match,
            {"_id": 0, "image_url": 1},
            sort=[("name", 1)],
        )
    except Exception as exc:
        logger.warning(
            "embed_init: thumbnail lookup failed org=%s cat=%s: %s",
            org_id, category_name, exc,
        )
        return None

    if not doc:
        return None
    return doc.get("image_url")


# ── Public API: categories endpoint backing function ────────────────────


async def get_embed_categories_data(
    slug: str,
    with_thumbnail: bool = False,
    include_empty: bool = False,
) -> dict:
    """Return the list of published categories for a store.

    Args:
        slug:           store slug (resolved via ``_resolve_org``).
        with_thumbnail: when True, each category includes a
                        ``thumbnail_url`` populated with the first
                        published product image in that category.
                        Default False to minimize Mongo round-trips.
        include_empty:  reserved for future compat (when categories
                        become first-class entities). Today there is no
                        category storage outside Product.category inline,
                        so this flag is a no-op — categorias with zero
                        published products simply don't exist in the
                        aggregation output. Param kept for forward compat.

    Returns:
        {
            "slug": "...",
            "categories": [
                {"name": "...", "slug": "...", "count": N,
                 "thumbnail_url": "..." | None}, ...
            ],
        }

    Raises:
        HTTPException(404) when slug doesn't resolve (via _resolve_org).
    """
    from routers.public import _resolve_org

    org = await _resolve_org(slug)
    org_id = org["id"]
    store_id = (org.get("_store") or {}).get("id")

    cats = await _aggregate_categories(org_id, store_id)

    # Decorate with thumbnail_url field (None if not requested)
    if with_thumbnail:
        for cat in cats:
            cat["thumbnail_url"] = await _find_category_thumbnail(
                org_id, store_id, cat["name"]
            )
    else:
        for cat in cats:
            cat["thumbnail_url"] = None

    # include_empty is currently a no-op (see docstring). When category
    # becomes a separate entity we'll honour it by left-joining the
    # category registry.
    _ = include_empty

    return {
        "slug": slug,
        "categories": cats,
    }


# ── Public API: products endpoint backing function ──────────────────────


def _build_product_match(
    org_id: str,
    store_id: Optional[str],
    category_slug: Optional[str] = None,
    item_type: Optional[str] = None,
) -> dict:
    """Compose the Mongo $match dict for the products query.

    Always enforces:
      - organization_id == org_id (multi-tenant)
      - is_published == True
      - is_active == True

    Optionally filters by:
      - category (case-insensitive regex against the slug)
      - item_type (exact match, whitelist-validated by handler)

    Multi-store: applies the v12.0 store_ids fan-out when store_id is set.
    """
    match: dict = {
        "organization_id": org_id,
        "is_published": True,
        "is_active": True,
    }

    if store_id:
        match["$or"] = [
            {"store_ids": store_id},
            {"store_ids": {"$size": 0}},
            {"store_ids": {"$exists": False}},
        ]

    # Category filter via slug normalization.
    # We can't $regex against a normalized field (Product.category is
    # raw string), so we re-normalize all distinct values and find which
    # raw names match the requested slug. The set is tiny (5-50 typical),
    # so an $in is cheap and uses the (organization_id, category) index.
    if category_slug:
        # We expect the slug to come URL-decoded already; normalize defensively.
        target_slug = _normalize_category_slug(category_slug)
        # If the merchant sent a non-existent slug, the match returns nothing
        # (and the handler returns total=0, items=[]) — no 404 needed.
        match["_category_filter_target_slug"] = target_slug  # marker (popped below)

    if item_type:
        match["item_type"] = item_type

    return match


async def _resolve_category_filter(
    org_id: str,
    store_id: Optional[str],
    target_slug: str,
) -> Optional[list[str]]:
    """Translate a target slug into the list of raw category names that
    match (case-insensitively normalized).

    Returns None if no category matches → caller should skip the filter
    AND return empty (the requested slug doesn't exist in the catalog).
    """
    if not target_slug:
        return None

    # Cheap distinct query: get all category values for this org+store.
    from database import products_collection

    distinct_match: dict = {
        "organization_id": org_id,
        "is_published": True,
        "is_active": True,
    }
    if store_id:
        distinct_match["$or"] = [
            {"store_ids": store_id},
            {"store_ids": {"$size": 0}},
            {"store_ids": {"$exists": False}},
        ]

    try:
        raw_cats = await products_collection.distinct("category", distinct_match)
    except Exception as exc:
        logger.warning(
            "embed_products: category distinct failed org=%s: %s",
            org_id, exc,
        )
        return None

    matching = [
        c for c in raw_cats
        if c and _normalize_category_slug(c) == target_slug
    ]
    return matching or None


def _sort_spec(sort_mode: str) -> list[tuple[str, int]]:
    """Convert a whitelist sort mode into a Mongo sort spec."""
    if sort_mode == "price_asc":
        return [("unit_price", 1), ("name", 1)]
    if sort_mode == "price_desc":
        return [("unit_price", -1), ("name", 1)]
    if sort_mode == "newest":
        return [("created_at", -1), ("name", 1)]
    # Default: name ASC
    return [("name", 1)]


def _public_card_projection() -> dict:
    """Mongo projection of the safe fields exposed by EmbedProductCard.

    Mirror the public projection used by /api/public/catalog/{slug} but
    DROP the heavy enrichment fields (metadata, occurrences). The handler
    re-derives:
      - category_slug from category (in-process normalization)
      - currency fallback chain in Python
    """
    return {
        "_id": 0,
        "id": 1,
        "slug": 1,
        "name": 1,
        "description": 1,
        "image_url": 1,
        "unit_price": 1,
        "category": 1,
        "unit": 1,
        "item_type": 1,
        "unit_label": 1,
        "price_mode": 1,
        "transaction_mode": 1,
        "stock_quantity": 1,
        "currency": 1,
        "created_at": 1,  # used for newest sort; STRIPPED from response
    }


async def get_embed_products_data(
    slug: str,
    *,
    category_slug: Optional[str] = None,
    type_filter: Optional[str] = None,
    sort_mode: str = "name",
    limit: int = EMBED_PRODUCT_LIMIT_DEFAULT,
    offset: int = 0,
    search_query: Optional[str] = None,
) -> dict:
    """Return a filterable, paginated list of public products for a store.

    Filters
    -------
    - ``category_slug``: case-insensitive match on the normalized slug.
      Resolves to all raw category names that normalize to the same slug
      (so ``"Catering"`` and ``"catering"`` collapse into a single filter).
    - ``type_filter``: exact match against ``item_type``. Handler is
      expected to validate against ``PRODUCT_TYPE_KEYS`` before calling.
    - ``search_query`` (Track E Step 1.3): full-text search across
      product name (weight 3) + description (weight 1). Mongo $text
      operator with italian stemmer. Empty/None = no search.

    Sort
    ----
    Whitelist of 5 modes (see ``EMBED_PRODUCT_SORT_MODES``). Default
    ``"name"`` (alphabetical ASC).
    ``"relevance"`` mode usa textScore quando search_query attiva,
    altrimenti falls back a ``"name"``.

    Pagination
    ----------
    ``offset``/``limit`` with hard cap ``EMBED_PRODUCT_LIMIT_MAX=100``.
    Caller should clamp these but the service double-checks.

    Returns
    -------
    ``{"slug": str, "currency": str, "items": [card dicts], "pagination":
       {"total": N, "limit": L, "offset": O, "has_more": bool}}``
    """
    from routers.public import _resolve_org
    from database import products_collection
    # Track E Step 1.3 — full-text search helper canonical.
    from core.embed_search import (
        is_search_active,
        build_text_search_match,
        text_score_projection,
        relevance_sort_spec,
        SORT_MODE_RELEVANCE,
    )

    # Resolve org (404 if slug unknown)
    org = await _resolve_org(slug)
    org_id = org["id"]
    resolved_store = org.get("_store") or {}
    store_id = resolved_store.get("id")

    # Currency fallback chain (same as init endpoint).
    org_currency = (org.get("currency_settings") or {}).get("default_currency") or "EUR"

    # ── Build query ──
    match = _build_product_match(
        org_id=org_id,
        store_id=store_id,
        item_type=type_filter,
    )
    # Resolve category slug → list of raw names
    if category_slug:
        raw_names = await _resolve_category_filter(org_id, store_id, category_slug)
        if not raw_names:
            # Unknown slug → no products; short-circuit with empty result
            return {
                "slug": slug,
                "currency": org_currency,
                "items": [],
                "pagination": {
                    "total": 0,
                    "limit": limit,
                    "offset": offset,
                    "has_more": False,
                },
            }
        match["category"] = {"$in": raw_names}

    # Clean up the placeholder marker
    match.pop("_category_filter_target_slug", None)

    # Track E Step 1.3 — apply text search filter (additive, multi-tenant
    # safe perche' match gia' scoped a organization_id sopra).
    search_active = is_search_active(search_query)
    if search_active:
        match.update(build_text_search_match(search_query))

    # ── Clamp pagination ──
    safe_limit = max(1, min(int(limit or EMBED_PRODUCT_LIMIT_DEFAULT), EMBED_PRODUCT_LIMIT_MAX))
    safe_offset = max(0, int(offset or 0))
    safe_sort = sort_mode if sort_mode in EMBED_PRODUCT_SORT_MODES else "name"
    # Track E Step 1.3 — sort='relevance' valido SOLO con search attiva.
    # Quando q assente, fallback a "name" (no Mongo error).
    if safe_sort == SORT_MODE_RELEVANCE and not search_active:
        safe_sort = "name"

    # ── Count + paginated find (parallel-able but kept sequential for clarity) ──
    try:
        total = await products_collection.count_documents(match)
    except Exception as exc:
        logger.warning("embed_products: count failed org=%s: %s", org_id, exc)
        total = 0

    # Build projection — include textScore meta quando search attiva
    # (richiesto da Mongo per sort by score).
    projection = _public_card_projection()
    if search_active:
        projection.update(text_score_projection())

    # Sort spec: relevance se search active + sort=relevance, altrimenti
    # whitelist legacy.
    if search_active and safe_sort == SORT_MODE_RELEVANCE:
        sort_spec = relevance_sort_spec()
    else:
        sort_spec = _sort_spec(safe_sort)

    try:
        cursor = products_collection.find(
            match, projection
        ).sort(sort_spec).skip(safe_offset).limit(safe_limit)
        rows = await cursor.to_list(length=safe_limit)
    except Exception as exc:
        logger.warning("embed_products: find failed org=%s: %s", org_id, exc)
        rows = []

    # ── Build card dicts ──
    items: list[dict] = []
    for doc in rows:
        # Strip created_at (used only for sort); enrich with category_slug.
        doc.pop("created_at", None)
        # Track E Step 1.3 — strip textScore meta from response.
        # Internal Mongo field (search relevance), non parte del contract
        # public EmbedProductCard. Pinned dal sentinel "no score leak".
        doc.pop("score", None)
        cat = doc.get("category")
        doc["category_slug"] = _normalize_category_slug(cat) if cat else None
        # Per-product currency override falls back to org currency.
        if not doc.get("currency"):
            doc["currency"] = org_currency
        items.append(doc)

    # ── FIX Track E Step 2.4.7 — Hide event_ticket products without
    # occurrences (parita' con lo storefront classico, public.py:1006).
    #
    # Razionale: un event_ticket senza occurrences attive NON puo' essere
    # acquistato (manca la data → manca il punto del biglietto). Lo
    # storefront classico li filtra fuori dal catalogo; il widget embed
    # deve fare lo stesso per evitare:
    #   - Customer confusion (card cliccabile ma drawer "no dates available")
    #   - Discrepancy admin/widget (admin nasconde correttamente nella
    #     pagina Eventi finche' non c'e' almeno 1 occurrence pubblicata)
    event_ticket_ids = [
        it["id"] for it in items if it.get("item_type") == "event_ticket"
    ]
    if event_ticket_ids:
        try:
            from database import event_occurrences_collection
            # 1 query bulk: trova product_id che hanno almeno 1 occurrence
            # attiva nel database (no N+1).
            occ_cursor = event_occurrences_collection.find(
                {
                    "organization_id": org_id,
                    "product_id": {"$in": event_ticket_ids},
                    "is_active": True,
                },
                {"_id": 0, "product_id": 1},
            )
            product_ids_with_occ: set[str] = set()
            async for occ in occ_cursor:
                pid = occ.get("product_id")
                if pid:
                    product_ids_with_occ.add(pid)
            # Filter items: tieni event_ticket SOLO se ha occurrences
            items = [
                it for it in items
                if it.get("item_type") != "event_ticket"
                or it["id"] in product_ids_with_occ
            ]
        except Exception as exc:
            logger.warning(
                "embed_products: occurrence filter failed org=%s: %s",
                org_id, exc,
            )
            # Conservative fallback: in caso di errore, NASCONDI tutti gli
            # event_ticket (no UX surprise; storefront classic does the same
            # implicitly perche' rilancia l'eccezione).
            items = [it for it in items if it.get("item_type") != "event_ticket"]

    # Recompute total post-filter (deve riflettere ITEMS visibili, non rows
    # raw del find). Importante per la paginazione client-side.
    visible_total = total - (len(rows) - len(items))
    has_more = (safe_offset + len(items)) < visible_total

    return {
        "slug": slug,
        "currency": org_currency,
        "items": items,
        "pagination": {
            "total": visible_total,
            "limit": safe_limit,
            "offset": safe_offset,
            "has_more": has_more,
        },
    }


# ── Product detail (Track E Step 2.4.5) ────────────────────────────────


def _public_detail_projection() -> dict:
    """Mongo projection per il product detail endpoint.

    Track E Step 2.4.6 — include ``metadata`` per estrarre i campi
    type-specific (duration_label, slot_duration_minutes, rental_unit,
    cover_image_url, long_description, requires_attendee_details,
    attendee_fields, order_fields, course_id, reservation_flavor,
    service_allow_custom_request, duration_minutes, use_default_schedule).

    Anti-PII / anti-leak:
      - cost_price + cost_source SCARTATI (admin internal)
      - tags SCARTATI (potrebbe contenere chiavi sensibili)
      - organization_id SCARTATO (multi-tenant boundary)
      - created_at + updated_at SCARTATI (no timeline disclosure)
      - sku SCARTATO (inventory-internal)
      - metadata INCLUSO ma poi FILTRATO (whitelist field) nel handler.

    Pin: sentinel ``INV-EP-8-DETAIL`` verifica che il response NON contenga
    cost_price, cost_source, tags, organization_id (metadata raw mai
    leakato; solo campi whitelistati derivati).
    """
    return {
        # Identity
        "_id": 0,
        "id": 1,
        "slug": 1,
        # Display
        "name": 1,
        "description": 1,
        "image_url": 1,
        # Pricing
        "unit_price": 1,
        "currency": 1,
        # Catalog metadata (safe-to-public)
        "category": 1,
        "item_type": 1,
        "unit": 1,
        "unit_label": 1,
        "price_mode": 1,
        "transaction_mode": 1,
        # Inventory hint
        "stock_quantity": 1,
        # Track E Step 2.4.5 — offer profile semantic identifier
        "offer_profile_id": 1,
        # Track E Step 2.4.6 — metadata included; whitelist extraction
        # nel service (NON esposto raw, solo campi safe).
        "metadata": 1,
    }


# Allowlist dei campi metadata estratti per il public detail.
# Tutto cio' che NON e' in questa whitelist viene SCARTATO dal response.
_DETAIL_METADATA_WHITELIST: tuple[str, ...] = (
    # Hero / landing display
    "cover_image_url",
    "long_description",
    # Service-specific
    "duration_label",
    "duration_minutes",
    "slot_duration_minutes",
    "service_allow_custom_request",
    "use_default_schedule",
    # Rental-specific
    "rental_unit",
    "reservation_flavor",
    # Event-specific
    "requires_attendee_details",
    "require_attendee_email",
    "require_attendee_phone",
    "attendee_fields",
    "order_fields",
    # Course
    "course_id",
)


async def get_embed_product_detail_data(
    slug: str,
    product_id: str,
) -> Optional[dict]:
    """Fetch a single product enriched per il drawer landing type-aware.

    Track E Step 2.4.6 — parita' storefront completa. Riusa la stessa
    pipeline di enrichment di ``get_product_landing`` (routers.public)
    per garantire shape consistency tra storefront-hosted e widget embed.

    Args:
        slug: store slug (validato upstream).
        product_id: product UUID (NB: non e' product.slug).

    Returns:
        Dict con tutti i campi di ``EmbedProductDetail`` Pydantic model.
        None se prodotto non trovato → 404 opaco nel handler.

    Multi-tenancy
    -------------
    Compound match (product_id, org_id) — un attacker NON puo' guessare
    un product_id per leakare prodotti di altro merchant.

    Side-fetch enrichment per item_type:
      - service: service_options[] + has_availability_slots flag
      - event_ticket: occurrences[] con tier embeddati (riuso shape
        PublicOccurrence di routers.public)
      - course: course_lessons_count + duration_seconds + access_policy
      - rental: extras[] (mandatory/optional/radio variants)

    Performance: ogni side-fetch e' singola query (no N+1). Total query
    count: 1 (find_one product) + 0..2 (depending on type).
    """
    from routers.public import _resolve_org
    from database import (
        products_collection,
        service_options_collection,
        availability_rules_collection,
    )

    # Resolve org (404 if slug unknown — handler propaga)
    org = await _resolve_org(slug)
    org_id = org["id"]
    resolved_store = org.get("_store") or {}
    store_id = resolved_store.get("id")
    store_doc = resolved_store  # alias semantico per terms resolver

    # Currency fallback chain
    org_currency = (org.get("currency_settings") or {}).get("default_currency") or "EUR"

    # Compound match: product_id + org_id + publication gate + store fan-out
    match: dict = {
        "id": product_id,
        "organization_id": org_id,
        "is_published": True,
        "is_active": True,
    }
    if store_id:
        match["$or"] = [
            {"store_ids": store_id},
            {"store_ids": {"$size": 0}},
            {"store_ids": {"$exists": False}},
        ]

    try:
        prod = await products_collection.find_one(match, _public_detail_projection())
    except Exception as exc:
        logger.warning(
            "embed_product_detail: find_one failed org=%s product=%s: %s",
            org_id, product_id, exc,
        )
        return None

    if not prod:
        return None

    # ── Extract whitelisted metadata fields ──
    raw_meta = prod.pop("metadata", None) or {}
    meta = {k: raw_meta.get(k) for k in _DETAIL_METADATA_WHITELIST if k in raw_meta}

    # Base shape (mirror PublicProduct from routers.public)
    item_type = prod.get("item_type", "physical")
    detail: dict = {
        "id": prod["id"],
        "slug": prod.get("slug"),
        "name": prod.get("name", ""),
        "description": prod.get("description"),
        "image_url": prod.get("image_url"),
        "unit_price": prod.get("unit_price"),
        "currency": prod.get("currency") or org_currency,
        "category": prod.get("category"),
        "category_slug": _normalize_category_slug(prod.get("category")) if prod.get("category") else None,
        "item_type": item_type,
        "unit": prod.get("unit"),
        "unit_label": prod.get("unit_label"),
        "price_mode": prod.get("price_mode", "fixed"),
        "transaction_mode": prod.get("transaction_mode", "request"),
        "stock_quantity": prod.get("stock_quantity"),
        "offer_profile_id": prod.get("offer_profile_id"),
        # Hero / landing
        "cover_image_url": meta.get("cover_image_url"),
        "long_description": meta.get("long_description"),
        # Service defaults (filled below se item_type == service)
        "service_options": [],
        "service_duration_minutes": meta.get("duration_minutes"),
        "service_allow_custom_request": bool(meta.get("service_allow_custom_request")),
        "has_availability_slots": False,
        "duration_label": meta.get("duration_label"),
        "slot_duration_minutes": meta.get("slot_duration_minutes"),
        # Event defaults
        "occurrences": [],
        "requires_attendee_details": bool(meta.get("requires_attendee_details")),
        "require_attendee_email": bool(meta.get("require_attendee_email", True)),
        "require_attendee_phone": bool(meta.get("require_attendee_phone", False)),
        # Field config defensive sanitization (mirrora public.py pattern)
        "attendee_fields": [
            f for f in (meta.get("attendee_fields") or [])
            if bool((f or {}).get("label") and str(f.get("label")).strip())
        ],
        "order_fields": [
            f for f in (meta.get("order_fields") or [])
            if bool((f or {}).get("label") and str(f.get("label")).strip())
        ],
        # Rental defaults
        "rental_unit": meta.get("rental_unit"),
        "reservation_flavor": meta.get("reservation_flavor"),
        "extras": [],
        # Course defaults
        "course_lessons_count": None,
        "course_duration_seconds": None,
        "course_access_policy": None,
        "course_access_expiry_days": None,
        # T&C resolved (Onda 11)
        "terms_content": None,
    }

    # ── Type-specific side-fetch enrichment ──

    if item_type == "service":
        # F5 Onda 12 — service options + availability rules existence flag
        try:
            options_cursor = service_options_collection.find(
                {
                    "organization_id": org_id,
                    "product_id": product_id,
                    "is_active": True,
                },
                {
                    "_id": 0, "id": 1, "label": 1, "description": 1,
                    "price": 1, "duration_minutes_override": 1, "sort_order": 1,
                },
            ).sort("sort_order", 1)
            detail["service_options"] = await options_cursor.to_list(300)
        except Exception as exc:
            logger.warning(
                "embed_product_detail: service_options fetch failed: %s", exc,
            )
            detail["service_options"] = []

        # has_availability_slots: True se esiste almeno una rule per il prodotto
        # OR per l'org globally, OR meta.use_default_schedule e' true (Onda 15
        # synth grid 9-18 7-day).
        try:
            rule_exists = await availability_rules_collection.find_one(
                {
                    "organization_id": org_id,
                    "$or": [{"product_id": product_id}, {"product_id": None}],
                },
                {"_id": 0, "id": 1},
            )
            detail["has_availability_slots"] = bool(rule_exists) or bool(
                meta.get("use_default_schedule")
            )
        except Exception as exc:
            logger.warning(
                "embed_product_detail: availability rules check failed: %s", exc,
            )

    elif item_type == "event_ticket":
        # E1 — occurrences + tier embeddati. Riuso direttamente la query
        # del catalog/landing storefront per parita' shape.
        # FIX E2.4.7 — collection corretta e' ``event_occurrences_collection``
        # (era ``product_occurrences_collection`` — non esiste, fallback silente
        # in try/except restituiva sempre lista vuota → bug widget).
        try:
            from database import event_occurrences_collection
            occ_cursor = event_occurrences_collection.find(
                {
                    "organization_id": org_id,
                    "product_id": product_id,
                    "is_active": True,
                },
                {"_id": 0},
            ).sort("start_at", 1)
            occurrences = await occ_cursor.to_list(300)
            # Filtro safe field whitelist (mirrora PublicOccurrence)
            safe_occ = []
            for o in occurrences:
                tiers_raw = o.get("tiers") or []
                safe_tiers = [
                    {
                        "id": t.get("id"),
                        "label": t.get("label"),
                        "description": t.get("description"),
                        "price": t.get("price"),
                        "remaining": t.get("remaining"),
                        "sort_order": t.get("sort_order", 0),
                    }
                    for t in tiers_raw
                ]
                safe_occ.append({
                    "id": o.get("id"),
                    "start_at": o.get("start_at"),
                    "end_at": o.get("end_at"),
                    "location": o.get("location"),
                    "capacity": o.get("capacity"),
                    "booked_count": o.get("booked_count"),
                    "remaining": o.get("remaining"),
                    "price_override": o.get("price_override"),
                    "tiers": safe_tiers,
                    "venue_name": o.get("venue_name"),
                    "address": o.get("address"),
                    "city": o.get("city"),
                    "postal_code": o.get("postal_code"),
                    "country": o.get("country"),
                    "latitude": o.get("latitude"),
                    "longitude": o.get("longitude"),
                    "map_url": o.get("map_url"),
                    "cover_image_url": o.get("cover_image_url"),
                    "long_description": o.get("long_description"),
                    "slug": o.get("slug"),
                })
            detail["occurrences"] = safe_occ
        except Exception as exc:
            logger.warning(
                "embed_product_detail: occurrences fetch failed: %s", exc,
            )
            detail["occurrences"] = []

    elif item_type == "course":
        # Release 4 (Courses) — light counters (no lesson content here;
        # full curriculum richiede customer enrollment via /customer/courses)
        try:
            from database import courses_collection
            course_id = meta.get("course_id")
            if course_id:
                course_doc = await courses_collection.find_one(
                    {"id": course_id, "organization_id": org_id, "is_active": True},
                    {"_id": 0},
                )
                if course_doc:
                    lessons = [
                        l for m in (course_doc.get("modules") or [])
                        for l in (m.get("lessons") or [])
                    ]
                    detail["course_lessons_count"] = len(lessons)
                    detail["course_duration_seconds"] = sum(
                        int(l.get("duration_seconds") or 0) for l in lessons
                    )
                    detail["course_access_policy"] = (
                        course_doc.get("access_policy") or "lifetime"
                    )
                    detail["course_access_expiry_days"] = course_doc.get(
                        "access_expiry_days"
                    )
        except Exception as exc:
            logger.warning(
                "embed_product_detail: course doc fetch failed: %s", exc,
            )

    # ── Track E Step 2.4.9 — side-fetch extras CROSS-TYPE ──
    # Pre-fix: extras fetchati solo per rental. Storefront React invece li
    # usa anche su PhysicalLandingPage + DigitalLandingPage + ProductLandingPage
    # (service). Per parita' totale, fetch extras per TUTTI i type che
    # supportano picker (physical, digital, service, rental). Event_ticket +
    # course tipicamente non usano extras (event ha tier picker; course e'
    # add-to-cart diretto).
    if item_type in ("physical", "digital", "service", "rental"):
        try:
            from database import product_extras_collection
            extras_cursor = product_extras_collection.find(
                {
                    "organization_id": org_id,
                    "product_id": product_id,
                    "is_active": True,
                },
                {
                    "_id": 0, "id": 1, "kind": 1, "group_key": 1,
                    "label": 1, "description": 1, "price": 1,
                    "price_modifier_type": 1, "duration_minutes_override": 1,
                    "is_default": 1, "sort_order": 1,
                },
            ).sort("sort_order", 1)
            detail["extras"] = await extras_cursor.to_list(300)
        except Exception as exc:
            logger.warning(
                "embed_product_detail: extras fetch failed (type=%s): %s",
                item_type, exc,
            )

    # ── T&C resolution (cross-type, Onda 11) ──
    try:
        from services.terms_resolver import resolve_effective_terms_sync
        # NB: resolve_effective_terms_sync e' sincrono (no await). Riceve
        # product dict + store dict. Se nessuna policy attiva ritorna None.
        detail["terms_content"] = resolve_effective_terms_sync(
            product={"metadata": meta}, store=store_doc,
        )
    except Exception as exc:
        logger.warning(
            "embed_product_detail: terms resolver failed: %s", exc,
        )

    return detail


# ── Product types in scope ──────────────────────────────────────────────


async def _available_product_types(org_id: str, store_id: Optional[str]) -> list[str]:
    """Return the set of item_type values actually present on published
    products for this org/store, sorted alphabetically.

    Permette al widget di sapere se vale la pena renderizzare filter UI
    per booking/event-ticket/digital (se l'org non ha nessun event ticket,
    il widget nasconde il filtro).
    """
    from database import products_collection

    match: dict = {
        "organization_id": org_id,
        "is_published": True,
        "is_active": True,
    }
    if store_id:
        match["$or"] = [
            {"store_ids": store_id},
            {"store_ids": {"$size": 0}},
            {"store_ids": {"$exists": False}},
        ]

    try:
        distinct_types = await products_collection.distinct("item_type", match)
    except Exception as exc:
        logger.warning(
            "embed_init: product_types distinct failed org=%s: %s",
            org_id, exc,
        )
        return []

    return sorted(t for t in distinct_types if t)


# ── Stripe checkout availability ────────────────────────────────────────


async def _checkout_stripe_enabled(org_id: str) -> bool:
    """Resolve commerce.checkout_stripe flag con fail-safe a True.

    Pattern identico a /storefront/{slug}/meta: in caso di errore lookup
    al modulo, default True per preservare l'UX "Acquista" (no silent
    disable per un blip Mongo).
    """
    try:
        from services.module_access import get_effective_limit
        flag = await get_effective_limit(org_id, "commerce", "checkout_stripe")
        return flag == -1  # -1 = "on", 0 = "off"
    except Exception:
        return True


# ── Public API ──────────────────────────────────────────────────────────


async def get_embed_init_data(slug: str) -> dict:
    """Aggregate all bootstrap data for the embed widget.

    Raises HTTPException(404) if slug doesn't resolve to a published
    public store (delegated to ``_resolve_org``).

    Returns a dict with keys:
      slug, org_name, store_info (StoreInfo or None), currency,
      storefront_languages, available_product_types, categories,
      capabilities, fulfillment_modes
    """
    from routers.public import _resolve_org, StoreInfo
    from services.branding_service import resolve_for_store as resolve_branding_for_store

    org = await _resolve_org(slug)
    resolved_store = org.get("_store") or {}
    org_id = org["id"]
    store_id = resolved_store.get("id")  # None if legacy pseudo-store

    # ── store_info build (same fallback chain as /storefront/{slug}/meta) ──
    branding = resolve_branding_for_store(resolved_store, org)
    ss = org.get("store_settings") or {}
    si = StoreInfo(
        display_name=(
            resolved_store.get("name")
            or resolved_store.get("display_name")
            or ss.get("display_name")
            or None
        ),
        store_description=(
            resolved_store.get("description")
            or resolved_store.get("store_description")
            or ss.get("store_description")
            or None
        ),
        contact_email=(
            resolved_store.get("contact_email")
            or ss.get("contact_email")
            or None
        ),
        contact_phone=(
            resolved_store.get("contact_phone")
            or ss.get("contact_phone")
            or None
        ),
        logo_url=branding.get("logo_url") or ss.get("logo_url"),
        brand_color=branding.get("brand_color") or ss.get("brand_color"),
        brand_color_text=branding.get("brand_color_text") or ss.get("brand_color_text"),
        seo_title=resolved_store.get("seo_title") or ss.get("seo_title"),
        seo_description=(
            resolved_store.get("seo_description") or ss.get("seo_description")
        ),
    )
    has_info = any([
        si.display_name, si.store_description, si.contact_email, si.contact_phone,
        si.logo_url, si.brand_color, si.brand_color_text,
        si.seo_title, si.seo_description,
    ])

    # ── Currency resolution ──
    # Priorità: org.currency_settings.default_currency → "EUR"
    currency = "EUR"
    cs = org.get("currency_settings") or {}
    if cs.get("default_currency"):
        currency = cs["default_currency"]

    # ── Categories + product types + Stripe gate (parallelizable, run sequentially
    #     to keep code simple; total wall-clock <100ms with indexed queries) ──
    categories = await _aggregate_categories(org_id, store_id)
    available_types = await _available_product_types(org_id, store_id)
    checkout_stripe = await _checkout_stripe_enabled(org_id)

    # ── Fulfillment modes (already public-safe field on store) ──
    fulfillment_modes = list(resolved_store.get("fulfillment_modes") or [])
    if not fulfillment_modes and ss.get("fulfillment_modes"):
        fulfillment_modes = list(ss["fulfillment_modes"])

    # Track E Step 4.3 — design tokens + custom nav links (parita storefront).
    # Sourced dal resolved_store (Phase 8/9) — payload identico a CatalogResponse
    # cosi' widget e storefront classico ricevono i medesimi valori.
    design_tokens = resolved_store.get("design_tokens") or {}
    custom_nav_links = list(resolved_store.get("custom_nav_links") or [])

    # Track E Step 7.4 — Legal disclosure URLs (Privacy Policy + Termini).
    # Default: pagine hosted afianco-side (storefront SPA React renderizza
    # /s/{slug}/privacy + /terms consumando /api/legal/storefront/{slug}/...).
    # Override merchant: se store config ha privacy_policy_url / terms_service_url
    # custom (es. dominio merchant), il widget linka quelli al posto delle
    # hosted page. Pattern stesso del React storefront che linka /s/{slug}/...
    # ma con URL ASSOLUTO cosi' funziona cross-origin nel widget embed.
    from core.embed_distribution import APP_BASE_URL
    privacy_policy_url = (
        resolved_store.get("privacy_policy_url")
        or ss.get("privacy_policy_url")
        or f"{APP_BASE_URL}/s/{slug}/privacy"
    )
    terms_service_url = (
        resolved_store.get("terms_service_url")
        or ss.get("terms_service_url")
        or f"{APP_BASE_URL}/s/{slug}/terms"
    )

    return {
        "slug": slug,
        "org_name": org.get("name", ""),
        "store_info": si if has_info else None,
        "currency": currency,
        "storefront_languages": resolved_store.get("storefront_languages") or ["it"],
        "available_product_types": available_types,
        "categories": categories,
        "capabilities": {
            "checkout_stripe_enabled": checkout_stripe,
            "cart_enabled": True,             # core feature legacy
            "customer_auth_enabled": True,    # core feature legacy
        },
        "fulfillment_modes": fulfillment_modes,
        # Track E Step 4.3 — Phase 8/9 customization payload
        "design_tokens": design_tokens,
        "custom_nav_links": custom_nav_links,
        # Track E Step 7.4 — Legal disclosure (Privacy + Terms) cliccabili
        "privacy_policy_url": privacy_policy_url,
        "terms_service_url": terms_service_url,
    }


# ── Step 16 — embed_return_url validator (anti-phishing) ────────────────


def _origin_of(url: str) -> Optional[str]:
    """Return scheme://netloc of a URL, or None if malformed.

    Mirror del modo in cui browser/CORS treat "Origin": è
    (scheme + host + port), case-normalized. Path/query/fragment ignorati.
    """
    if not url or not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    # netloc include host:port; lowercase per match case-insensitive
    return f"{parts.scheme}://{parts.netloc.lower()}"


def validate_embed_return_url(
    url: Optional[str],
    allowed_origins: Iterable[str],
) -> bool:
    """Return True iff ``url`` belongs to one of the allowed origins.

    Args:
        url:              candidate URL to validate (typically the
                          ``embed_return_url`` field of a checkout request).
        allowed_origins:  iterable of allowed origin strings from
                          ``store.allowed_origins``. Each entry is treated
                          as an exact origin match (scheme + host + port).

    Security
    --------
    - Empty / None URL → False (anti-bypass).
    - URL must parse as http(s) with a netloc.
    - The URL origin must EXACTLY match one of the allowed origins (no
      subdomain wildcard, no path-prefix tricks).
    - Scheme is enforced: an allowed ``https://merchant.com`` does NOT
      accept ``http://merchant.com``.

    Subdomain attack mitigated: ``https://merchant.com.attacker.com``
    has netloc ``merchant.com.attacker.com`` → doesn't match
    ``merchant.com`` (the allowed origin's netloc).
    """
    candidate = _origin_of(url) if url else None
    if not candidate:
        return False

    allowed_normalized = set()
    for entry in allowed_origins or ():
        normalized = _origin_of(entry)
        if normalized:
            allowed_normalized.add(normalized)

    return candidate in allowed_normalized


# ── Step 17 — postMessage bridge HTML payload ──────────────────────────


# HTML template del bridge: posizionato come costante per:
#   1. consentire pinning via inspect.getsource (sentinel)
#   2. evitare runtime f-string assembly che potrebbe leak con caratteri
#      non escapati
#
# I 5 placeholder ``$$ESC_*$$`` sono sostituiti con valori HTML/JSON-safe:
#   ESC_ORDER_ID          → order id JSON-encoded (safe in JS string literal)
#   ESC_STATUS            → order_status JSON-encoded
#   ESC_PAYMENT_STATUS    → payment_intent JSON-encoded
#   ESC_TARGET_ORIGIN     → return_url origin (scheme://host) JSON-encoded
#   ESC_DISPLAY_ORDER_ID  → order id HTML-escaped per visualizzazione fallback

_BRIDGE_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Order complete · afianco</title>
<meta name="referrer" content="no-referrer">
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif;
         max-width: 480px; margin: 64px auto; padding: 24px;
         line-height: 1.55; color: #1a202c; text-align: center; }
  h1 { font-size: 18px; margin-bottom: 12px; }
  p  { font-size: 14px; color: #4a5568; }
  code { background:#edf2f7; padding:2px 6px; border-radius:4px; }
</style>
</head>
<body>
  <h1>Order confirmation</h1>
  <p>Tornando al sito merchant&hellip;</p>
  <p><small>Order: <code>$$ESC_DISPLAY_ORDER_ID$$</code></small></p>

  <script>
    (function () {
      var msg = {
        source: 'afianco-embed',
        type: 'checkout_complete',
        order_id: $$ESC_ORDER_ID$$,
        order_status: $$ESC_STATUS$$,
        payment_status: $$ESC_PAYMENT_STATUS$$
      };
      var targetOrigin = $$ESC_TARGET_ORIGIN$$;
      try {
        if (window.opener && !window.opener.closed) {
          window.opener.postMessage(msg, targetOrigin);
        } else if (window.parent && window.parent !== window) {
          window.parent.postMessage(msg, targetOrigin);
        }
      } catch (e) { /* swallow — fallback link below */ }
      // Close popup after a short delay so merchant has time to read message.
      setTimeout(function () {
        try { window.close(); } catch (e) {}
      }, 800);
    })();
  </script>
</body>
</html>
"""


def _json_string_safe(value) -> str:
    """JSON-encode a value safely for embedding inside a <script> tag.

    Two-step:
      1. ``json.dumps(...)`` produces a valid JS string literal with all
         control chars + quotes escaped.
      2. Additional escape of ``</`` to ``<\\/`` so the response cannot
         be terminated by an injected ``</script>`` tag.
    """
    encoded = json.dumps(str(value))
    # Anti-script-injection: a JSON value containing "</script>" would
    # otherwise allow termination of the host <script> block.
    return encoded.replace("</", "<\\/")


async def get_embed_complete_payload(order_id: str) -> Optional[dict]:
    """Resolve the postMessage bridge payload for a completed embed checkout.

    Looks up the order, verifies it was created via embed (i.e. has
    ``embed_metadata.return_url`` set), derives the target origin
    server-side (NEVER from query params — anti-spoof), and renders the
    static HTML bridge.

    Returns None when:
      - order doesn't exist
      - order has no ``embed_metadata.return_url`` (legacy order)
      - the stored return_url is malformed (defense-in-depth)

    Args:
        order_id: the order identifier (already validated by the handler
                  for length / charset).

    Returns:
        ``{html, target_origin, order_status, payment_status}`` on success,
        ``None`` otherwise. Handler responds 404 on None.
    """
    if not order_id:
        return None

    from database import orders_collection

    try:
        order = await orders_collection.find_one(
            {"id": order_id},
            {
                "_id": 0,
                "id": 1,
                "organization_id": 1,
                "order_status": 1,
                "payment_intent": 1,
                "embed_metadata": 1,
            },
        )
    except Exception as exc:
        logger.warning("embed_complete: order lookup failed id=%s: %s", order_id, exc)
        return None

    if not order:
        return None

    meta = order.get("embed_metadata") or {}
    return_url = meta.get("return_url")
    if not return_url:
        # Not an embed-originated order — refuse to expose status (anti-leak)
        return None

    target_origin = _origin_of(return_url)
    if not target_origin:
        logger.warning(
            "embed_complete: order id=%s has malformed return_url=%r",
            order_id, return_url,
        )
        return None

    order_status = str(order.get("order_status") or "unknown")
    payment_status = str(order.get("payment_intent") or "unknown")

    # ── Build HTML with rigorous escaping ──
    # JSON values for the JS payload
    safe_order_id = _json_string_safe(order_id)
    safe_status = _json_string_safe(order_status)
    safe_payment = _json_string_safe(payment_status)
    safe_target_origin = _json_string_safe(target_origin)
    # HTML-escaped value for visible text fallback
    display_order_id = html.escape(order_id, quote=True)

    rendered = (
        _BRIDGE_HTML_TEMPLATE
        .replace("$$ESC_DISPLAY_ORDER_ID$$", display_order_id)
        .replace("$$ESC_ORDER_ID$$", safe_order_id)
        .replace("$$ESC_STATUS$$", safe_status)
        .replace("$$ESC_PAYMENT_STATUS$$", safe_payment)
        .replace("$$ESC_TARGET_ORIGIN$$", safe_target_origin)
    )

    return {
        "html": rendered,
        "target_origin": target_origin,
        "order_status": order_status,
        "payment_status": payment_status,
    }
