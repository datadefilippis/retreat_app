"""
Entity Resolver — centralised primitives for entity linking.

Provides reusable, deterministic functions to build lookup maps and
resolve transactional text fields to master entity IDs.

Design principles:
  - Non-blocking: map builders catch all errors and return {}
  - Deterministic: no fuzzy logic, no AI, no probabilistic matching
  - Ambiguity-safe: duplicate keys are excluded, never arbitrarily chosen
  - Pure resolvers: resolve_* functions are synchronous dict lookups
  - Domain-explicit: public API uses concrete function names per entity type

Usage pattern (future wave A1.3):
  1. Build maps once per import batch:  map = await build_customer_name_map(org_id)
  2. Resolve per row:                   cid = resolve_by_name(map, row_text)
  3. If resolved:                       row["customer_id"] = cid

Public API:
  Normalisation:
    normalize_entity_text(text) -> str

  Map builders (async, non-blocking):
    build_customer_name_map(org_id) -> dict[str, str]
    build_supplier_name_map(org_id) -> dict[str, str]
    build_product_name_map(org_id)  -> dict[str, str]
    build_customer_external_id_map(org_id) -> dict[str, str]
    build_supplier_external_id_map(org_id) -> dict[str, str]
    build_product_sku_map(org_id)   -> dict[str, str]

  Resolvers (sync, pure):
    resolve_by_name(name_map, text) -> str | None
    resolve_by_external_id(extid_map, text) -> str | None
    resolve_by_sku(sku_map, text) -> str | None
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Upper bound for entity loading.  find_by_org defaults are 200/500 which
# would silently truncate large catalogs.  We override with a generous
# limit so the resolver maps are complete for any realistic PMI org.
_RESOLVER_ENTITY_LIMIT = 10_000


# ── Normalisation ───────────────────────────────────────────────────────────

def normalize_entity_text(text) -> str:
    """Minimal, deterministic normalisation for entity name matching.

    Applies lower() + strip() only.  Does NOT transliterate Unicode —
    that is reserved for column-name normalisation in dataset_service.
    Consistent with the existing supplier auto-match pattern.
    """
    if not text:
        return ""
    return str(text).lower().strip()


# ── Internal map builder ────────────────────────────────────────────────────

def _build_unique_map(entities, key_fn) -> dict:
    """Build {key -> entity_id} dict, excluding ambiguous (duplicate) keys.

    Args:
        entities: iterable of objects with .id attribute
        key_fn: callable(entity) -> str | None  (returns normalised key)

    Duplicate handling: if two entities produce the same key, BOTH are
    excluded from the map.  This prevents arbitrary match on ambiguous data.
    """
    seen: dict = {}
    duplicates: set = set()
    for entity in entities:
        key = key_fn(entity)
        if not key:
            continue
        if key in seen:
            duplicates.add(key)
        else:
            seen[key] = entity.id
    for dup in duplicates:
        seen.pop(dup, None)
    return seen


# ── Name map builders (public, async, non-blocking) ────────────────────────

async def build_customer_name_map(org_id: str) -> dict:
    """Return {normalised_name -> customer_id} for all active customers."""
    try:
        from repositories import customer_repository
        customers = await customer_repository.find_by_org(
            org_id, active_only=True, limit=_RESOLVER_ENTITY_LIMIT,
        )
        return _build_unique_map(customers, lambda c: normalize_entity_text(c.name))
    except Exception as exc:
        logger.warning("entity_resolver: build_customer_name_map failed for org=%s: %s", org_id, exc)
        return {}


async def build_supplier_name_map(org_id: str) -> dict:
    """Return {normalised_name -> supplier_id} for all active suppliers."""
    try:
        from repositories import supplier_repository
        suppliers = await supplier_repository.find_by_org(
            org_id, active_only=True, limit=_RESOLVER_ENTITY_LIMIT,
        )
        return _build_unique_map(suppliers, lambda s: normalize_entity_text(s.name))
    except Exception as exc:
        logger.warning("entity_resolver: build_supplier_name_map failed for org=%s: %s", org_id, exc)
        return {}


async def build_product_name_map(org_id: str) -> dict:
    """Return {normalised_name -> product_id} for all active products."""
    try:
        from repositories import product_repository
        products = await product_repository.find_by_org(
            org_id, active_only=True, limit=_RESOLVER_ENTITY_LIMIT,
        )
        return _build_unique_map(products, lambda p: normalize_entity_text(p.name))
    except Exception as exc:
        logger.warning("entity_resolver: build_product_name_map failed for org=%s: %s", org_id, exc)
        return {}


# ── External ID map builders (public, async, non-blocking) ─────────────────

async def build_customer_external_id_map(org_id: str) -> dict:
    """Return {external_id (stripped, case-sensitive) -> customer_id}."""
    try:
        from repositories import customer_repository
        customers = await customer_repository.find_by_org(
            org_id, active_only=True, limit=_RESOLVER_ENTITY_LIMIT,
        )
        return _build_unique_map(
            customers,
            lambda c: c.external_id.strip() if getattr(c, "external_id", None) else None,
        )
    except Exception as exc:
        logger.warning("entity_resolver: build_customer_external_id_map failed for org=%s: %s", org_id, exc)
        return {}


async def build_supplier_external_id_map(org_id: str) -> dict:
    """Return {external_id (stripped, case-sensitive) -> supplier_id}."""
    try:
        from repositories import supplier_repository
        suppliers = await supplier_repository.find_by_org(
            org_id, active_only=True, limit=_RESOLVER_ENTITY_LIMIT,
        )
        return _build_unique_map(
            suppliers,
            lambda s: s.external_id.strip() if getattr(s, "external_id", None) else None,
        )
    except Exception as exc:
        logger.warning("entity_resolver: build_supplier_external_id_map failed for org=%s: %s", org_id, exc)
        return {}


# ── SKU map builder (public, async, non-blocking) ──────────────────────────

async def build_product_sku_map(org_id: str) -> dict:
    """Return {normalised_sku -> product_id} for all active products with SKU.

    SKU is normalised to lowercase + stripped because CSV data often has
    inconsistent casing (e.g. "ABC-123" vs "abc-123").
    """
    try:
        from repositories import product_repository
        products = await product_repository.find_by_org(
            org_id, active_only=True, limit=_RESOLVER_ENTITY_LIMIT,
        )
        return _build_unique_map(
            products,
            lambda p: p.sku.lower().strip() if getattr(p, "sku", None) else None,
        )
    except Exception as exc:
        logger.warning("entity_resolver: build_product_sku_map failed for org=%s: %s", org_id, exc)
        return {}


# ── Resolvers (public, sync, pure) ──────────────────────────────────────────

def resolve_by_name(name_map: dict, text) -> Optional[str]:
    """Look up a normalised name in a pre-built name map.

    Returns entity_id if exactly one match exists, None otherwise.
    """
    key = normalize_entity_text(text)
    if not key:
        return None
    return name_map.get(key)


def resolve_by_external_id(extid_map: dict, text) -> Optional[str]:
    """Look up an external ID in a pre-built map.

    Case-sensitive, stripped.  Returns entity_id or None.
    """
    if not text:
        return None
    key = str(text).strip()
    if not key:
        return None
    return extid_map.get(key)


def resolve_by_sku(sku_map: dict, text) -> Optional[str]:
    """Look up a SKU in a pre-built map.

    Normalised to lowercase + stripped.  Returns entity_id or None.
    """
    if not text:
        return None
    key = str(text).lower().strip()
    if not key:
        return None
    return sku_map.get(key)
