"""
Product type registry — single source of truth for the 5 product types
(physical, service, rental, event_ticket, booking).

Rationale:
  The historical architecture spreads type-specific knowledge across 8+
  files (routers, services, modules, frontend constants). Each time a
  type evolves or a new one is added, that knowledge has to be kept in
  sync by hand. This module centralizes the declarations so every other
  module can read them from a single place.

Design contract:
  - Pure declarations (no I/O, no DB, no side effects).
  - Backward-compatible with the existing models.product.ITEM_TYPES
    tuple — the legacy constant now re-exports keys from this registry.
  - Expandable: adding a 6th type means adding one record here, nothing
    else.
  - Introspectable at runtime via PRODUCT_TYPES dict + helper functions.
  - The metadata_schema attribute is intentionally set to None in this
    commit; Phase P2 will attach Pydantic validators. Keeping the field
    in the dataclass now avoids a schema rewrite later.

What this module does NOT do (yet, on purpose):
  - Does not enforce metadata shape. That's P2.
  - Does not relocate existing type-dispatch chains. Those will be
    migrated page-by-page in later phases.
  - Does not change any model field or database shape.

This is the "catalog" of types — nothing reads from it in this commit
except the legacy ITEM_TYPES tuple (which re-exports keys for
backward compat).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple


# ── Type descriptor ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProductTypeDef:
    """Immutable descriptor for a single product type.

    Fields:
      key:
        Canonical identifier. MUST match the value used on Product.item_type
        rows in the database. Never rename without a migration.

      label_key:
        i18n namespace + key that resolves to the human label. Frontend
        reads this to render a localized display name. Format:
        "catalog:item_type.<key>".

      requires_stock:
        True if the type participates in stock_quantity tracking. Physical
        is the only one today.

      requires_calendar:
        True if orders of this type block/consume calendar time slots
        (rental, event_ticket, booking). Used downstream to decide whether
        calendar sync is relevant.

      requires_occurrences:
        True if the type depends on event_occurrences rows (event_ticket
        only). Drives validation flow.

      direct_checkout_default_safe:
        Default answer to "can this type complete a Stripe direct
        checkout without human review?" Physical / service / booking
        default to True, rental / event_ticket-with-capacity default to
        False (reviewed case-by-case in commerce_rules.py).

      default_fulfillment_mode:
        What fulfillment mode makes sense out-of-the-box for this type
        when the storefront form doesn't specify one. None = unknown
        (requires user choice).

      metadata_schema:
        Pydantic model validating Product.metadata for this type.
        None in this phase — populated by P2. Defensive fallback is to
        accept any dict (current behavior).

      description:
        Short human description of the type's purpose. Documentation only.

      deprecated:
        Onda 16 — when True, product creation endpoints emit an
        X-Deprecated header and a server-side log warning. Existing
        products keep working; new products should prefer the
        replacement type. Used for the `booking` → `rental+flavor=slot`
        consolidation.

      replacement:
        Canonical key of the preferred type when deprecated=True.
        Purely documentary — migration scripts still do the actual work.
    """

    key: str
    label_key: str
    requires_stock: bool = False
    requires_calendar: bool = False
    requires_occurrences: bool = False
    direct_checkout_default_safe: bool = True
    default_fulfillment_mode: Optional[str] = None
    metadata_schema: Optional[Callable] = None   # Pydantic class, set in P2
    description: str = ""
    deprecated: bool = False
    replacement: Optional[str] = None


# ── Registry ────────────────────────────────────────────────────────────────


_PRODUCT_TYPE_LIST: Tuple[ProductTypeDef, ...] = (
    ProductTypeDef(
        key="physical",
        label_key="catalog:item_type.physical",
        requires_stock=True,
        requires_calendar=False,
        requires_occurrences=False,
        direct_checkout_default_safe=True,
        default_fulfillment_mode="shipping",
        description=(
            "Tangible good with optional stock tracking. The canonical "
            "ecommerce case: pay, ship (or pickup), done."
        ),
    ),
    ProductTypeDef(
        key="service",
        label_key="catalog:item_type.service",
        requires_stock=False,
        requires_calendar=False,
        requires_occurrences=False,
        direct_checkout_default_safe=True,
        default_fulfillment_mode="manual_arrangement",
        description=(
            "Intangible service (consulting, installation, session). No "
            "inventory; optional duration metadata for display."
        ),
    ),
    ProductTypeDef(
        key="rental",
        label_key="catalog:item_type.rental",
        requires_stock=False,
        requires_calendar=True,
        requires_occurrences=False,
        direct_checkout_default_safe=False,   # review-only until P8
        default_fulfillment_mode="local_pickup",
        description=(
            "Item rented for a date range. Price is per-unit (day/week/"
            "month). Currently review-only — direct checkout is enabled "
            "once availability enforcement lands."
        ),
    ),
    ProductTypeDef(
        key="event_ticket",
        label_key="catalog:item_type.event_ticket",
        requires_stock=False,
        requires_calendar=True,
        requires_occurrences=True,
        direct_checkout_default_safe=True,    # overridden per-occurrence when capacity is set
        default_fulfillment_mode="not_required",
        description=(
            "Ticket to a specific event occurrence (date + optional "
            "venue). Capacity is optional and when set behaves as a "
            "seat cap. Fulfillment is the ticket delivery itself."
        ),
    ),
    ProductTypeDef(
        key="booking",
        label_key="catalog:item_type.booking",
        requires_stock=False,
        requires_calendar=True,
        requires_occurrences=False,
        direct_checkout_default_safe=True,
        default_fulfillment_mode="not_required",
        description=(
            "DEPRECATED (Onda 16). 1:1 time-slot booking now lives under "
            "item_type=rental with metadata.reservation_flavor='slot'. "
            "Existing booking products keep working; new products should "
            "be created as rental+slot. A migration script converts "
            "historical rows."
        ),
        deprecated=True,
        replacement="rental",
    ),
    ProductTypeDef(
        key="digital",
        label_key="catalog:item_type.digital",
        # Stock is opt-in: the merchant can cap the number of downloads
        # available (e.g. a limited-edition PDF). When stock_quantity is
        # left None, the product is always purchasable.
        requires_stock=True,
        requires_calendar=False,
        requires_occurrences=False,
        direct_checkout_default_safe=True,
        # Digital goods are fulfilled by the download link itself; no
        # shipping / pickup flow is involved.
        default_fulfillment_mode="not_required",
        description=(
            "Downloadable digital good (PDF, audio, e-book, software, "
            "template). File is uploaded by the merchant and served via a "
            "token-gated endpoint after purchase. Optional limits: max "
            "downloads per delivery, link expiry in days."
        ),
    ),
    # Release 4 (Courses) — video courses hosted externally on Bunny Stream.
    # Structurally closer to digital (no shipping, no calendar, no
    # occurrences) but the content lives in a dedicated Course entity
    # (Product.metadata.course_id → Course). Fulfillment is the
    # enrollment itself (IssuedCourseAccess) + the course player in the
    # customer portal.
    ProductTypeDef(
        key="course",
        label_key="catalog:item_type.course",
        # Courses are nominatively licensed per customer; no seat pool
        # or limited stock. Merchants who want to cap sales can use the
        # admin controls (unpublish) or rely on custom policies.
        requires_stock=False,
        requires_calendar=False,
        requires_occurrences=False,
        direct_checkout_default_safe=True,
        # Access is delivered through the customer portal player; no
        # shipping / pickup flow is involved.
        default_fulfillment_mode="not_required",
        description=(
            "Video course (modules + lessons) with Bunny Stream-hosted "
            "videos. Purchase emits an IssuedCourseAccess enrollment; "
            "the customer follows lessons from their account area. "
            "Requires a logged-in customer at checkout."
        ),
    ),
)


# Dict for O(1) lookup by key — built once at import.
PRODUCT_TYPES: "dict[str, ProductTypeDef]" = {t.key: t for t in _PRODUCT_TYPE_LIST}


# Tuple of keys, used by legacy code paths that want the same shape as
# the historical ITEM_TYPES constant in models.product.
PRODUCT_TYPE_KEYS: Tuple[str, ...] = tuple(t.key for t in _PRODUCT_TYPE_LIST)


# ── Helpers ─────────────────────────────────────────────────────────────────


def get_type(key: str) -> Optional[ProductTypeDef]:
    """Return the ProductTypeDef for a key, or None if unknown.

    Callers that expect a known key should either check the return or
    call `require_type` which raises on unknown.
    """
    return PRODUCT_TYPES.get(key)


def require_type(key: str) -> ProductTypeDef:
    """Return the ProductTypeDef for a key, raising KeyError if unknown.

    Prefer this in validation paths where an unknown key is a bug.
    """
    if key not in PRODUCT_TYPES:
        raise KeyError(f"Unknown product type: {key!r}. Known: {PRODUCT_TYPE_KEYS}")
    return PRODUCT_TYPES[key]


def list_types() -> "list[ProductTypeDef]":
    """Return all registered ProductTypeDef records in declaration order."""
    return list(_PRODUCT_TYPE_LIST)


def types_matching(predicate: Callable[[ProductTypeDef], bool]) -> "list[ProductTypeDef]":
    """Return records where predicate(td) is truthy.

    Example:
      types_matching(lambda t: t.requires_calendar)
      → [rental, event_ticket, booking]
    """
    return [t for t in _PRODUCT_TYPE_LIST if predicate(t)]


def public_registry_snapshot() -> "list[dict]":
    """Serializable snapshot for the future public /product-types-meta endpoint.

    Returns a plain list of dicts with fields safe to expose externally
    (no callables, no internal descriptions if sensitive). Deliberate
    omissions: metadata_schema (internal), direct_checkout_default_safe
    (backend detail — frontend should ask the resolver, not assume).
    """
    return [
        {
            "key": t.key,
            "label_key": t.label_key,
            "requires_stock": t.requires_stock,
            "requires_calendar": t.requires_calendar,
            "requires_occurrences": t.requires_occurrences,
            "default_fulfillment_mode": t.default_fulfillment_mode,
        }
        for t in _PRODUCT_TYPE_LIST
    ]


# ── Metadata schema resolver (P2) ───────────────────────────────────────────


def metadata_schema_for(key: str):
    """Return the Pydantic model class validating metadata for this type.

    Resolved indirectly via product_metadata.TYPE_TO_METADATA_SCHEMA so
    the registry module stays free of heavy Pydantic imports at the top
    level and avoids any circular-import risk between product_types and
    product_metadata. Returns None if the type is unknown.
    """
    # Lazy import: keeps the registry importable even in minimal test
    # environments that do not need metadata validation.
    from .product_metadata import TYPE_TO_METADATA_SCHEMA
    return TYPE_TO_METADATA_SCHEMA.get(key)


def validate_metadata(key: str, raw):
    """Normalize raw metadata for a type (best-effort, never raises).

    See product_metadata.validate_metadata_for_type for the full contract.
    This wrapper is the preferred public entry point so call sites can
    import from a single module (product_types) and future refactors
    can change the backend without ripple.
    """
    from .product_metadata import validate_metadata_for_type
    return validate_metadata_for_type(key, raw)
