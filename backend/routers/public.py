"""
Public Router — unauthenticated endpoints for the public storefront.

These endpoints do NOT require JWT authentication.
They are accessible to any visitor via the organization's public_slug.

Endpoints:
  GET  /public/catalog/{slug}   — published products for an org
  POST /public/order-request    — submit an order request (creates draft)
"""

import copy
import logging
import time
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, EmailStr
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from routers.auth import limiter
from models.attendee import AttendeeInfo
from models.product_extra import ExtraSelections
from models.field_config import FieldConfig
from models.shipping_option import PublicShippingOption
from services.terms_resolver import resolve_effective_terms_sync
from services.branding_service import resolve_for_store as resolve_branding_for_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["Public Storefront"])


# ── Response / Request Models ───────────────────────────────────────────────

class PublicTier(BaseModel):
    """Public-safe tier fields embedded inside PublicOccurrence (E1)."""
    id: str
    label: str
    description: Optional[str] = None
    price: float
    remaining: Optional[int] = None       # None = unlimited within occurrence
    sort_order: int = 0


class PublicOccurrence(BaseModel):
    """Public-safe occurrence fields for event_ticket products."""
    id: str
    start_at: str
    end_at: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = None
    booked_count: Optional[int] = None    # seats booked (for sold-out display)
    remaining: Optional[int] = None       # seats remaining (None = unlimited)
    price_override: Optional[float] = None
    # E1: when non-empty, the storefront renders a tier picker and the
    # buyer's cart must include ticket_tier_id. When empty, the legacy
    # mono-tier flow is used (price_override + occurrence.capacity).
    tiers: List[PublicTier] = Field(default_factory=list)
    # ── E2: structured presentation fields ────────────────────────────
    # All optional. Storefront uses them to build a richer event card
    # and the dedicated landing page (E3). When absent the legacy
    # `location` text is used.
    venue_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_url: Optional[str] = None          # derived by build_map_url if not set
    cover_image_url: Optional[str] = None
    long_description: Optional[str] = None
    # F2: slug exposed so the storefront card can deep-link to
    # /e/:org_slug/:slug without a second fetch.
    slug: Optional[str] = None
    # Fase 3 (retreat) — pagina di vendita ricca (tutti opzionali; la
    # landing salta le sezioni vuote)
    agenda: List[Dict[str, Any]] = Field(default_factory=list)
    gallery_urls: List[str] = Field(default_factory=list)
    included: List[str] = Field(default_factory=list)
    excluded: List[str] = Field(default_factory=list)
    faq: List[Dict[str, Any]] = Field(default_factory=list)


class PublicServiceOption(BaseModel):
    """F5 Onda 12 — a service product's selectable option (radio)."""
    id: str
    label: str
    description: Optional[str] = None
    price: float
    duration_minutes_override: Optional[int] = None
    sort_order: int = 0


class PublicProduct(BaseModel):
    """Public-safe product fields only. No cost_price, sku, or internal data."""
    id: str
    # Onda 13 — slug for deep-linking the public landing page
    # (/p/:org_slug/:product_slug). Optional for legacy products.
    slug: Optional[str] = None
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    # Onda 14 — dedicated hero image for the public landing page
    # (`metadata.cover_image_url`). When null, the landing uses image_url.
    cover_image_url: Optional[str] = None
    # Onda 14 — markdown long description surfaced to the landing.
    long_description: Optional[str] = None
    unit_price: Optional[float] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    item_type: str = "physical"          # physical | service | rental | event_ticket
    unit_label: Optional[str] = None     # pz, servizio, giorno, posto
    price_mode: str = "fixed"            # fixed | inquiry
    transaction_mode: str = "request"    # request | direct | approval
    duration_label: Optional[str] = None    # service: "60 min", "mezza giornata"
    slot_duration_minutes: Optional[int] = None  # booking: slot duration in minutes
    rental_unit: Optional[str] = None    # rental: "ora", "giorno", "settimana"
    stock_quantity: Optional[int] = None  # null = unlimited; 0 = sold out; N = available
    occurrences: List[PublicOccurrence] = Field(default_factory=list)  # populated for event_ticket
    # F1 Onda 8 — event_ticket products: when True the storefront checkout
    # must collect one AttendeeInfo per seat (name + email + optional phone).
    # The validator enforces it server-side too. Only meaningful for
    # event_ticket; silently ignored for other item_types.
    requires_attendee_details: bool = False
    # F2 Onda 9 — configurable required-ness of the built-in email/phone
    # fields. Only meaningful when requires_attendee_details is True.
    require_attendee_email: bool = True
    require_attendee_phone: bool = False
    # F2 Onda 9 — merchant-defined custom fields. Surfaced to the
    # storefront so the checkout can render inputs dynamically.
    attendee_fields: List[FieldConfig] = Field(default_factory=list)
    order_fields: List[FieldConfig] = Field(default_factory=list)
    # F4 Onda 11 — pre-resolved T&C markdown (product override or
    # store default via services/terms_resolver). None = no T&C required.
    terms_content: Optional[str] = None
    # F5 Onda 12 — service products expose their options + duration +
    # "has_availability_slots" flag so the storefront can decide how to
    # render the checkout (radio picker, slot picker, free request).
    service_options: List["PublicServiceOption"] = Field(default_factory=list)
    service_duration_minutes: Optional[int] = None
    service_allow_custom_request: bool = False
    has_availability_slots: bool = False
    # Onda 16 — Prenotazione consolidation. reservation_flavor distinguishes
    # range (multi-day date picker) vs slot (hh:mm calendar) variants of
    # rental products. `extras` surfaces the ProductExtra rows so the
    # reservation landing page can render mandatory / optional / radio
    # pickers + live price preview.
    reservation_flavor: Optional[str] = None
    extras: List[dict] = Field(default_factory=list)
    # Release 4 (Courses) — lightweight counters for the catalog card.
    # Full module/lesson structure lives in PublicCoursePreview (landing
    # payload only). These two are safe to expose everywhere because
    # they are aggregate numbers, not content.
    course_lessons_count: Optional[int] = None
    course_duration_seconds: Optional[int] = None
    course_access_policy: Optional[str] = None            # "lifetime" | "expiring"
    course_access_expiry_days: Optional[int] = None

    # Fix caparra (4/7/2026) — piano pagamenti pubblico anche nel catalogo
    # (prima esisteva solo su PublicEventProduct: il serializer lo passava
    # ma Pydantic lo scartava in silenzio). Serve al riepilogo checkout per
    # la riga "oggi paghi solo la caparra". Solo dati pubblicabili: modalità,
    # percentuale/importo, scadenza saldo — nessun dato interno.
    payment_plan: Optional[Dict[str, Any]] = None


class StoreInfo(BaseModel):
    """Public-safe store identity fields. Only populated fields are included."""
    display_name: Optional[str] = None
    store_description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[str] = None
    brand_color: Optional[str] = None          # hex: #1a1a1a
    brand_color_text: Optional[str] = None     # hex: #ffffff
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None


class CatalogResponse(BaseModel):
    org_name: str
    slug: str
    products: List[PublicProduct]
    currency: str = "EUR"
    fulfillment_modes: List[str] = ["shipping"]  # v10.0: modes supported by this store
    store_info: Optional[StoreInfo] = None         # v10.2: public merchant identity
    storefront_languages: List[str] = ["it"]       # v15.0: languages enabled for this storefront
    # Phase 8 — Custom navigation links the merchant configured in the
    # admin UI. The frontend CategoryNav renders these next to the
    # category pills. Empty list = merchant hasn't configured any
    # (most stores at launch).
    custom_nav_links: List[Dict[str, Any]] = Field(default_factory=list)
    # Phase 9 — Design tokens (radius / density / font / accent / etc).
    # Empty dict = merchant hasn't customized anything; the frontend
    # useDesignTokens hook fills defaults. Always present in the
    # response so the client can rely on the field existing.
    design_tokens: Dict[str, Any] = Field(default_factory=dict)


# ── /storefront/{slug}/meta — i18n bootstrap payload ────────────────────────
#
# Lightweight metadata endpoint consumed by the frontend `StoreMetaProvider`
# context (Step 2 of the language-system refactor). Replies with the minimum
# data every public surface needs to render correctly BEFORE its own
# resource-heavy endpoint resolves:
#
#   - storefront_languages: drives the language resolver chain on every
#     landing page (so /p, /e, /co, /b, /t, /d, /rsv, /r, /ph, /dg can
#     mount the correct locale without each one re-fetching the catalog
#     just to learn the language list).
#
#   - store_info: lets landing pages render branded headers (logo + colors)
#     without their own dedicated endpoint having to ship those fields.
#
# The payload is intentionally tiny so it can be cached aggressively
# (5 min server-side via Cache-Control, plus the client persists it in
# localStorage for instant cold-start).
class PublicStorefrontMeta(BaseModel):
    slug: str
    org_name: str
    storefront_languages: List[str] = ["it"]
    store_info: Optional[StoreInfo] = None
    # v5.8 / Onda 4 — Whether the org's commerce plan supports Stripe Connect
    # checkout. When False, storefront UI shows "Richiedi info" instead of
    # "Acquista" and submitted orders are flagged as contact requests.
    # Default True keeps backward-compat for any caller that doesn't yet
    # populate this field (older catalog tiers, custom plans, etc.).
    checkout_stripe_enabled: bool = True
    # Phase 8 — Same custom_nav_links as CatalogResponse. Surfaced here
    # too so landing pages (which call /meta but NOT /catalog) can
    # render the same header nav and stay visually consistent with the
    # storefront index.
    custom_nav_links: List[Dict[str, Any]] = Field(default_factory=list)
    # Phase 9 — Same design_tokens as CatalogResponse. Surfaced on meta
    # so landing pages get the same visual treatment as the storefront
    # index (border radius, density, accent color, etc.) without
    # needing to fetch the full catalog.
    design_tokens: Dict[str, Any] = Field(default_factory=dict)


# ── E3: Event landing page response ─────────────────────────────────────────


class PublicEventProduct(BaseModel):
    """Minimal product payload for the landing page — only what the page
    actually shows. Internal fields (stock, sku) are intentionally absent."""
    id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    transaction_mode: str = "direct"
    currency: str = "EUR"
    # M2 — breadcrumb della landing (Ritiri › categoria › titolo)
    category: Optional[str] = None
    # Onda 15 — base unit_price surfaced so the landing can compute the
    # total for mono-tier events (general-price events without tiers).
    # Fallback chain on the frontend: occurrence.price_override ?? product.unit_price ?? 0.
    unit_price: Optional[float] = None
    # F1 Onda 8 — whether the checkout must collect per-ticket holder data.
    # Surfaced so the landing page can warn the user ahead of "Procedi al
    # checkout" and pre-size the next step.
    requires_attendee_details: bool = False
    # F2 Onda 9 — required-ness + custom fields (mirrored from PublicProduct)
    require_attendee_email: bool = True
    require_attendee_phone: bool = False
    attendee_fields: List[FieldConfig] = Field(default_factory=list)
    order_fields: List[FieldConfig] = Field(default_factory=list)
    # F4 Onda 11 — pre-resolved T&C markdown (product override or store default)
    terms_content: Optional[str] = None
    # Fase 2 S2 (retreat) — piano di pagamento pubblico (caparra/rate/policy).
    # Informazione per l'acquirente: la landing mostra "come paghi" e la
    # policy di cancellazione PRIMA della prenotazione. Whitelist esplicita
    # (mai metadata integrale sul pubblico).
    payment_plan: Optional[Dict[str, Any]] = None


class PublicEventLanding(BaseModel):
    """Full payload for a single public event landing page.

    Consumed by the `/e/:org_slug/:slug` route on the storefront. When
    the occurrence is cancelled or its parent product is unpublished,
    the endpoint returns 404 instead of exposing half-broken state.
    """
    org_slug: str
    org_name: str
    # F5 — True quando i contenuti serviti vengono dalla traduzione
    # automatica (?lang=en/de/fr): il frontend mostra il badge trasparenza
    auto_translated: bool = False
    store_info: Optional[StoreInfo] = None
    product: PublicEventProduct
    occurrence: PublicOccurrence
    # Computed convenience: is this event still buyable right now?
    # False when cancelled / closed / sold-out globally; the storefront
    # uses it to render the "buy" CTA vs an "esaurito" badge.
    is_buyable: bool = True


class OrderRequestItem(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    occurrence_id: Optional[str] = None  # required for event_ticket products
    # E1: optional tier for multi-tier event_ticket occurrences. When the
    # occurrence has tiers and the client sends none, the request is
    # still accepted only if the occurrence also supports mono-tier
    # (today: always, since tiers are purely additive). The validator
    # layer applies the stricter rule.
    ticket_tier_id: Optional[str] = None
    # Rental request context (rental items only)
    rental_date_from: Optional[str] = Field(default=None, max_length=10)  # ISO date
    rental_date_to: Optional[str] = Field(default=None, max_length=10)    # ISO date
    rental_notes: Optional[str] = Field(default=None, max_length=500)
    # Booking slot (v12.0)
    booking_date: Optional[str] = Field(default=None, max_length=10)      # ISO date
    booking_start_time: Optional[str] = Field(default=None, max_length=5) # HH:MM
    booking_end_time: Optional[str] = Field(default=None, max_length=5)   # HH:MM
    # Onda 17 — cross-day slot end date (optional). When absent or equal to
    # booking_date, same-day semantics apply (historic behaviour).
    booking_end_date: Optional[str] = Field(default=None, max_length=10)  # ISO date
    # Attendees (F1 Onda 8) — required for event_ticket products whose
    # product.metadata.requires_attendee_details is True. One AttendeeInfo
    # per seat; validator enforces len(attendees) == quantity. Pydantic
    # validates email format per entry.
    attendees: Optional[List[AttendeeInfo]] = None
    # F5 Onda 12 — service option selected by the customer (radio-select).
    # Only meaningful for item_type=service; validator rejects orders
    # missing this field when the product has any active option.
    service_option_id: Optional[str] = None
    # Onda 14 Parte B — signal that booking_date/start/end were proposed
    # by the customer rather than picked from the product's availability
    # rules. Combined with `metadata.service_allow_custom_request` on the
    # product, lets the validator accept a date that doesn't match any
    # rule. The admin confirms manually afterwards.
    service_custom_request: bool = False
    # R2 (Onda 16) — extra selezionati dal cliente (optional/radio oltre ai
    # mandatory). Server-merge + pricing in create_order via extras_total.
    extra_selections: Optional[ExtraSelections] = None


class ShippingAddressInput(BaseModel):
    """Structured shipping address submitted at checkout.

    Validation at the payload boundary — required fields get min_length=1
    so Pydantic rejects empty/whitespace-only values before the business
    logic runs. When the cart contains physical items and the customer
    chose mode=shipping, this object OR the legacy free-text
    `shipping_address` must be present (see boundary check below).
    """
    recipient_name: Optional[str] = Field(default=None, max_length=160)
    line1: str = Field(min_length=1, max_length=200)
    civic: str = Field(min_length=1, max_length=20)
    postal_code: str = Field(min_length=1, max_length=16)
    city: str = Field(min_length=1, max_length=120)
    province: Optional[str] = Field(default=None, max_length=8)
    # Strict 2-letter ISO; client defaults to "IT". Accepts lowercase —
    # normalization happens below.
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)


class OrderRequestPayload(BaseModel):
    slug: str = Field(min_length=3, max_length=50)
    customer_name: str = Field(min_length=1, max_length=255)
    customer_email: EmailStr
    customer_phone: Optional[str] = Field(default=None, max_length=50)
    items: List[OrderRequestItem] = Field(min_length=1)
    notes: Optional[str] = Field(default=None, max_length=2000)
    # Fulfillment (v10.0)
    fulfillment_mode: Optional[str] = Field(default=None, pattern="^(shipping|local_pickup)$")
    # Legacy free-text address — accepted for back-compat. When
    # `shipping_address_details` is also present the backend ignores this
    # string and synthesizes its own from the structured object.
    shipping_address: Optional[str] = Field(default=None, max_length=500)
    # Structured address, preferred input format.
    shipping_address_details: Optional[ShippingAddressInput] = None
    fulfillment_notes: Optional[str] = Field(default=None, max_length=500)
    # Shipping feature — reference to the ShippingOption chosen at
    # checkout. Required when mode=shipping and cart contains a physical
    # item; backend recalculates the cost from the option (client cannot
    # set the price itself).
    shipping_option_id: Optional[str] = Field(default=None, max_length=64)
    # Coupon (v13.0)
    coupon_code: Optional[str] = Field(default=None, max_length=30)
    # F2 Onda 9 — merchant-defined order-level custom fields, keyed by
    # FieldConfig.id. Validator enforces required entries against the
    # product's metadata.order_fields definition.
    order_fields: Optional[Dict[str, Any]] = None
    # F4 Onda 11 — customer acceptance of Terms & Conditions. Must be
    # True when the effective T&C (see services/terms_resolver.py) are
    # non-empty; the endpoint rejects the order otherwise.
    terms_accepted: bool = False
    # GT1 — canale di provenienza: "marketplace" (directory/calendario)
    # o "store" (vetrina propria dell'operatore). Governa la regola
    # d'incasso: gli ordini marketplace si chiudono SOLO online.
    channel: Optional[str] = Field(default=None, pattern="^(marketplace|store)$")

    # ── Wave GDPR-Commerce CG-5 (2026-05-19) — per-order consent flags ──
    #
    # These flags are STRICTLY ADDITIVE on top of the legacy
    # ``terms_accepted`` flow:
    #   - All default to False so existing clients that don't send them
    #     keep working unchanged (no schema break).
    #   - The endpoint ONLY enforces these when the merchant has
    #     published their per-store GDPR legal docs
    #     (merchant_legal_status == "published" or "stale_draft").
    #     Stores that have not configured GDPR continue to checkout
    #     exactly as they did before this commit — no Pydantic break,
    #     no behavioural change.
    #   - Marketing is fully optional even on GDPR-configured stores
    #     (granular consent under GDPR Art. 7).
    gdpr_terms_accepted: bool = False
    gdpr_privacy_accepted: bool = False
    gdpr_marketing_accepted: bool = False

    # ── R2a (2026-07-06) — lingua UI dell'utente al momento del checkout.
    # Timbrata sull'ordine (order.locale) e usata come priorità 1 per la
    # lingua di TUTTE le email verso il compratore (conferma, promemoria
    # caparre, rimborsi): il dunning di settembre parla la lingua con cui
    # hai comprato a luglio, non quella del negozio. Additiva: i client
    # che non la mandano cadono sulla catena esistente (account store →
    # lingua negozio → it). Valori fuori da {it,en,de,fr} vengono ignorati.
    locale: Optional[str] = Field(default=None, max_length=5)


class OrderRequestResponse(BaseModel):
    success: bool = True
    message: str
    order_id: str
    transaction_mode: str = "request"    # dominant mode that determined runtime behavior
    order_status: str = "draft"          # resulting order status
    payment_checkout_url: Optional[str] = None  # redirect URL for payment collection
    payment_reason: Optional[str] = None        # why checkout was/wasn't created


class PublicOrderStatus(BaseModel):
    """Public-safe order status snapshot for Stripe checkout redirect pages.

    Returned by GET /public/orders/{order_id}/status — no auth required.
    Exposes only fields needed to display progress and link back to the store.
    Excludes: customer PII, line items, cost data, admin notes, fulfillment details.
    """
    order_id: str
    order_number: Optional[str] = None
    order_status: str                     # draft | pending | confirmed | ...
    payment_intent: str                   # none | required | collected | waived
    total: float
    currency: str = "EUR"
    store_slug: Optional[str] = None      # for "back to store" link (null if no store)
    store_name: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────────

# ── R13 — TTL cache per la risoluzione slug→org ──────────────────────────
# `_resolve_org` è chiamato da quasi ogni endpoint pubblico (storefront +
# embed), spesso più volte per la stessa richiesta utente (catalogo, prodotto,
# meta, checkout). Cache positive-only con TTL corto: dati catalog-level, una
# staleness di ~45s è accettabile e un nuovo store pubblicato non subisce
# ritardi (i miss/404 NON vengono cacheati). Per-process (ogni worker la
# propria); thundering-herd benigno (più coroutine risolvono e settano).
_RESOLVE_ORG_TTL = 45.0  # secondi
_resolve_org_cache: Dict[str, "tuple[float, dict]"] = {}


def _invalidate_resolve_org_cache(slug: Optional[str] = None) -> None:
    """Svuota la cache di `_resolve_org` (tutto, o un singolo slug).

    Utile dopo update di store (pubblicazione, allowed_origins) o nei test.
    """
    if slug is None:
        _resolve_org_cache.clear()
    else:
        _resolve_org_cache.pop(slug, None)


async def _resolve_org(slug: str) -> dict:
    """Caching wrapper (R13) su :func:`_resolve_org_uncached`.

    TTL ~45s, positive-only. Ritorna una deep-copy così i mutamenti
    downstream (es. ``org["_store"]``) non inquinano la entry cacheata né
    altre richieste. Il 404 si propaga dal core e NON viene cacheato.
    """
    now = time.monotonic()
    cached = _resolve_org_cache.get(slug)
    if cached is not None and (now - cached[0]) < _RESOLVE_ORG_TTL:
        return copy.deepcopy(cached[1])
    org = await _resolve_org_uncached(slug)  # raises 404 on miss (non cacheato)
    _resolve_org_cache[slug] = (now, org)
    return copy.deepcopy(org)


async def _resolve_org_uncached(slug: str) -> dict:
    """Find org + store by slug. Tries multi-store collection first, then legacy.

    Returns org dict enriched with _store (the resolved store document)
    for downstream use. Raises 404 if not found, inactive, or unpublished.
    """
    from database import organizations_collection, stores_collection

    # v12.0: try multi-store collection first
    store_doc = await stores_collection.find_one(
        {"slug": slug, "is_published": True, "is_active": True, "visibility": "public"},
        {"_id": 0},
    )

    if store_doc:
        org = await organizations_collection.find_one(
            {"id": store_doc["organization_id"], "is_active": {"$ne": False}, "deactivated_at": None},
            {"_id": 0},
        )
        if org:
            org["_store"] = store_doc  # attach resolved store for downstream
            return org

    # Legacy fallback: org.public_slug + org.store_settings
    org = await organizations_collection.find_one(
        {
            "public_slug": slug,
            "is_active": True,
            "deactivated_at": None,
            "store_settings.is_storefront_published": True,
        },
        {"_id": 0},
    )
    if org:
        # Build a pseudo-store from legacy settings for consistent downstream access
        ss = org.get("store_settings") or {}
        org["_store"] = {
            "id": None,
            "slug": slug,
            "name": ss.get("display_name") or org.get("name", ""),
            "description": ss.get("store_description"),
            "contact_email": ss.get("contact_email"),
            "contact_phone": ss.get("contact_phone"),
            "fulfillment_modes": ss.get("fulfillment_modes") or ["shipping"],
            # B8 — espone allowed_origins dalle legacy store_settings così
            # l'embed checkout (validate_embed_return_url) funziona anche per le
            # org single-store legacy che li hanno configurati. Fail-safe: [].
            "allowed_origins": ss.get("allowed_origins") or [],
            "visibility": "public",
            "is_published": True,
        }
        return org

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog not found")


async def _find_or_create_customer(
    org_id: str, name: str, email: str, phone: Optional[str],
    customer_account_id: Optional[str] = None,
) -> str:
    """Find customer by email in org, or create one. Returns customer_id.

    If customer_account_id is provided (authenticated customer), it's linked
    on the customer record for future portal access.

    Phase 4 of the Store consolidation plan — race-safe upsert.
    -----------------------------------------------------------
    Pre-Phase-4 this was a find-then-insert pattern. Two concurrent
    storefront orders from the same email could each find no customer,
    each insert, producing duplicate rows in the same org. The
    `repositories.customer_repository.upsert_by_email` helper now wraps
    a `find_one_and_update(upsert=True)` which Mongo guarantees is
    atomic — two concurrent calls deterministically converge on a
    single row. Combined with the unique partial index on
    (organization_id, email) added in database.py, the duplicate
    invariant is enforced at BOTH the application AND storage layers.
    """
    from repositories.customer_repository import upsert_by_email

    customer_id, was_created = await upsert_by_email(
        org_id,
        name=name,
        email=email,
        phone=phone,
        customer_account_id=customer_account_id,
        source="storefront",
    )
    if was_created:
        logger.info(
            "public: created customer %s (%s) for org=%s",
            customer_id, email.strip().lower(), org_id,
        )
    return customer_id


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/storefront/{slug}/meta", response_model=PublicStorefrontMeta)
@limiter.limit("60/minute")
async def get_public_storefront_meta(request: Request, response: Response, slug: str):
    """Public store metadata — language list + branding only.

    Replies in <50ms (no product fetch) so it's safe to call as the
    very first request when a public surface mounts. Used by the
    frontend `StoreMetaProvider` to bootstrap the i18n resolver chain
    without forcing every landing page to fetch the full catalog.

    Cached 5 minutes server-side (`max-age=300`); the frontend ALSO
    persists the response in `localStorage[storefront_meta_<slug>]`
    with a 1-hour TTL so cold starts paint with the correct locale
    before the network round-trip even completes.

    404 when the slug doesn't resolve to a published+public store —
    same shape as `/catalog/{slug}`. Inactive/private/pos visibility
    are intentionally treated as not-found (don't leak existence).
    """
    org = await _resolve_org(slug)
    resolved_store = org.get("_store") or {}

    # Build StoreInfo with the same fallback chain the catalog endpoint
    # uses (resolver → store_settings → None). Duplicating the ~10 lines
    # is cheaper than refactoring out a shared helper now — both
    # endpoints stay independently testable. If a third caller ever
    # needs this exact payload, it's the right time to extract.
    branding = resolve_branding_for_store(resolved_store, org)
    ss = org.get("store_settings") or {}
    si = StoreInfo(
        display_name=resolved_store.get("name") or resolved_store.get("display_name") or ss.get("display_name") or None,
        store_description=resolved_store.get("description") or resolved_store.get("store_description") or ss.get("store_description") or None,
        contact_email=resolved_store.get("contact_email") or ss.get("contact_email") or None,
        contact_phone=resolved_store.get("contact_phone") or ss.get("contact_phone") or None,
        logo_url=branding.get("logo_url") or ss.get("logo_url"),
        brand_color=branding.get("brand_color") or ss.get("brand_color"),
        brand_color_text=branding.get("brand_color_text") or ss.get("brand_color_text"),
        seo_title=resolved_store.get("seo_title") or ss.get("seo_title"),
        seo_description=resolved_store.get("seo_description") or ss.get("seo_description"),
    )
    has_info = (
        si.display_name or si.store_description
        or si.contact_email or si.contact_phone
        or si.logo_url or si.brand_color or si.brand_color_text
        or si.seo_title or si.seo_description
    )

    # Short cache window: this endpoint MUST reflect admin changes
    # quickly (the merchant flips a language and expects the storefront
    # to follow within seconds, not minutes). 60s server-side covers
    # the burst of bootstrap calls that happen on a tab open without
    # pinning stale config visibly. The client uses stale-while-
    # revalidate on top: cache for instant render, refetch in the
    # background to catch admin changes within one round-trip.
    response.headers["Cache-Control"] = "public, max-age=60"

    # v5.8 / Onda 4 — Resolve `commerce.checkout_stripe` flag for storefront UI.
    # `get_effective_limit` returns -1 for "on" and 0 for "off". Translate to
    # bool. On any error → default True (preserve historical "Acquista" CTA
    # so no UI ever silently disables the buy button due to a Mongo blip).
    checkout_stripe_enabled = True
    try:
        from services.module_access import get_effective_limit
        flag = await get_effective_limit(org["id"], "commerce", "checkout_stripe")
        checkout_stripe_enabled = (flag == -1)
    except Exception:
        pass

    return PublicStorefrontMeta(
        slug=slug,
        org_name=org.get("name", ""),
        storefront_languages=resolved_store.get("storefront_languages") or ["it"],
        store_info=si if has_info else None,
        checkout_stripe_enabled=checkout_stripe_enabled,
        # Phase 8 — pass-through. Empty list when the merchant hasn't
        # configured any (default). Storefront header CategoryNav reads
        # this to render the merchant's custom links beside the
        # auto-generated category pills.
        custom_nav_links=resolved_store.get("custom_nav_links") or [],
        # Phase 9 — design tokens pass-through (empty dict when admin
        # hasn't customized; frontend hook fills defaults).
        design_tokens=resolved_store.get("design_tokens") or {},
    )


@router.get("/storefront/{slug}/marketing-status")
@limiter.limit("10/minute")
async def get_public_marketing_status(
    request: Request,
    response: Response,
    slug: str,
    email: str = Query(..., min_length=3, max_length=320),
):
    """Public endpoint — is this email already opted-in to marketing
    for this storefront's organization?

    Used by the guest checkout flow to HIDE the marketing checkbox
    when the customer is already opted-in. A re-display of the box
    would confuse the guest (the only legitimate way to revoke is
    the unsubscribe link in newsletter footers — Piece 1b).

    Privacy + Security:
      · Rate-limited to 10 req/min/IP to mitigate email enumeration.
      · Response is UNIFORMLY ``{opted_in: False}`` for unknown emails
        — indistinguishable from a known-but-not-opted-in email,
        so an attacker can't probe membership of the CRM via this
        endpoint.
      · Returns no PII, only a binary signal.

    Source of truth:
      ``customers.accepted_marketing_at`` + ``customers.marketing_revoked_at``
      with most-recent-wins semantics (identical to the helper used in
      Customer Insights ``_resolve_account_state``). The CRM customer
      doc is populated by:
        · submit_order_request (opt-in at checkout)
        · marketing-consent unsubscribe link (revoke)
        · 2026-05-20 backfill from consent_audit history
      so the answer is current within seconds of any user action.

    Response: ``{opted_in: bool}``
    Cache: ``private, no-store`` — the answer is per-email and
    changes when the user clicks unsubscribe; never cache.
    """
    org = await _resolve_org(slug)
    org_id = org["id"]

    # Normalise to the byte-shape stored in the index (lowercased).
    email_clean = (email or "").strip().lower()
    if "@" not in email_clean:
        # Malformed email — return the safe default rather than 400.
        # The frontend treats the response uniformly regardless.
        response.headers["Cache-Control"] = "private, no-store"
        return {"opted_in": False}

    from database import customers_collection
    cust = await customers_collection.find_one(
        {"organization_id": org_id, "email": email_clean},
        {
            "_id": 0,
            "accepted_marketing_at": 1,
            "marketing_revoked_at": 1,
        },
    )
    if not cust:
        response.headers["Cache-Control"] = "private, no-store"
        return {"opted_in": False}

    # Most-recent-wins semantics — same formula as CI-admin-vis.
    accepted = cust.get("accepted_marketing_at")
    revoked = cust.get("marketing_revoked_at")
    if accepted and (not revoked or accepted > revoked):
        opted_in = True
    else:
        opted_in = False

    response.headers["Cache-Control"] = "private, no-store"
    return {"opted_in": opted_in}


@router.get("/catalog/{slug}", response_model=CatalogResponse)
@limiter.limit("30/minute")
async def get_public_catalog(request: Request, slug: str,
    # en|de|fr: filtra e traduce i prodotti offerti in quella lingua.
    # Default semplice (non Query()) cosi' le chiamate dirette nei test
    # ricevono None reale e non l'oggetto Query (che e' truthy).
    lang: str = None):
    """Return published products for an organization. No auth required."""
    org = await _resolve_org(slug)

    from database import products_collection, event_occurrences_collection, orders_collection

    # v12.0: filter products by store_id if multi-store
    product_query = {"organization_id": org["id"], "is_published": True, "is_active": True}
    resolved_store = org.get("_store") or {}
    store_id = resolved_store.get("id")
    if store_id:
        # Products assigned to this store OR unassigned (empty store_ids = all stores)
        product_query["$or"] = [
            {"store_ids": store_id},
            {"store_ids": {"$size": 0}},
            {"store_ids": {"$exists": False}},
        ]

    # Phase 5 (Store consolidation) — N+1 fix on the public catalog.
    #
    # Pre-Phase-5 the per-product enrichment loop fired up to 3 side-fetches
    # per row (service_options + availability_rules + courses + extras).
    # Worst case for a 200-product catalog of mixed item_types: ~600 queries,
    # plus the products query itself. Each query added ~1-3ms on dev DB and
    # serialised over the same Motor connection pool, ballooning p99 latency.
    #
    # The new strategy is two-pass:
    #   1. Materialise the products cursor → list of raw docs (1 query).
    #   2. Bucket product_ids by item_type, then run 4 BATCHED side-fetches
    #      via `$in` in parallel (asyncio.gather → 1 round-trip wall clock).
    #   3. Build lookup dicts (product_id → side_data).
    #   4. Single enrichment loop reads from dicts — zero further queries.
    #
    # Net: catalog page goes from O(products) queries to O(1) — exactly
    # 5 queries regardless of catalog size, all parallelisable.
    #
    # Response shape preserved byte-for-byte (verified by test_catalog_n_plus_one.py).
    # Resilience preserved: per-product try/except still skips malformed rows.

    raw_products = await products_collection.find(
        product_query,
        {"_id": 0, "id": 1, "slug": 1, "name": 1, "description": 1, "image_url": 1,
         "unit_price": 1, "category": 1, "unit": 1,
         "item_type": 1, "unit_label": 1, "price_mode": 1, "transaction_mode": 1,
         "metadata": 1, "stock_quantity": 1, "translations": 1},
    ).sort("name", 1).to_list(200)

    # Multilingua manuale (6/7) — vista store in lingua X: solo i
    # prodotti offerti in X, coi campi tradotti dall'operatore.
    if lang and lang != "it":
        from services.manual_translations import is_available_in, merge_language
        raw_products = [merge_language(p, lang) for p in raw_products
                        if is_available_in(p, lang)]

    # Bucket product ids by item_type for the batched side-fetches.
    service_product_ids: list[str] = []
    course_id_to_product_id: dict[str, str] = {}  # course_id → owning product_id
    rental_product_ids: list[str] = []
    for raw in raw_products:
        it = raw.get("item_type")
        pid = raw.get("id")
        if not pid:
            continue
        if it == "service":
            service_product_ids.append(pid)
        elif it == "course":
            meta = raw.get("metadata") or {}
            cid = meta.get("course_id")
            if cid:
                course_id_to_product_id[cid] = pid
        elif it == "rental":
            rental_product_ids.append(pid)

    # Batched side-fetches — fire all four in parallel. Empty buckets
    # short-circuit to no-op coroutines so an all-physical catalog still
    # only pays for the products query.
    from database import (
        service_options_collection,
        availability_rules_collection,
        courses_collection,
        product_extras_collection,
    )

    async def _fetch_service_options():
        if not service_product_ids:
            return {}
        cursor = service_options_collection.find(
            {"organization_id": org["id"],
             "product_id": {"$in": service_product_ids},
             "is_active": True},
            {"_id": 0, "id": 1, "product_id": 1, "label": 1, "description": 1,
             "price": 1, "duration_minutes_override": 1, "sort_order": 1},
        ).sort("sort_order", 1)
        by_product: dict[str, list] = {}
        async for opt in cursor:
            ppid = opt.pop("product_id", None)
            if ppid:
                by_product.setdefault(ppid, []).append(opt)
        return by_product

    async def _fetch_availability_rule_signals():
        """Return (set_of_product_ids_with_rule, has_global_rule).

        Mirrors the pre-Phase-5 semantics:
          `$or: [{product_id: <id>}, {product_id: None}]`
        i.e. a global rule (product_id=None) gives EVERY service product
        access to slots. We compute the global signal once + a set of
        per-product ids and combine in the enrichment loop."""
        if not service_product_ids:
            return set(), False
        cursor = availability_rules_collection.find(
            {"organization_id": org["id"],
             "$or": [
                 {"product_id": {"$in": service_product_ids}},
                 {"product_id": None},
             ]},
            {"_id": 0, "product_id": 1},
        )
        per_product: set[str] = set()
        global_rule = False
        async for r in cursor:
            ppid = r.get("product_id")
            if ppid is None:
                global_rule = True
            else:
                per_product.add(ppid)
        return per_product, global_rule

    async def _fetch_courses():
        if not course_id_to_product_id:
            return {}
        course_ids = list(course_id_to_product_id.keys())
        cursor = courses_collection.find(
            {"id": {"$in": course_ids},
             "organization_id": org["id"],
             "is_active": True},
            {"_id": 0, "id": 1, "modules": 1, "access_policy": 1,
             "access_expiry_days": 1},
        )
        by_course_id: dict[str, dict] = {}
        async for c in cursor:
            by_course_id[c["id"]] = c
        return by_course_id

    async def _fetch_rental_extras():
        if not rental_product_ids:
            return {}
        cursor = product_extras_collection.find(
            {"organization_id": org["id"],
             "product_id": {"$in": rental_product_ids},
             "is_active": True},
            {"_id": 0, "id": 1, "product_id": 1, "kind": 1, "group_key": 1,
             "label": 1, "description": 1, "price": 1, "price_modifier_type": 1,
             "duration_minutes_override": 1, "is_default": 1, "sort_order": 1},
        ).sort("sort_order", 1)
        by_product: dict[str, list] = {}
        async for ex in cursor:
            ppid = ex.pop("product_id", None)
            if ppid:
                by_product.setdefault(ppid, []).append(ex)
        return by_product

    import asyncio as _asyncio
    (
        service_options_by_product,
        (products_with_rule, has_global_rule),
        courses_by_id,
        extras_by_product,
    ) = await _asyncio.gather(
        _fetch_service_options(),
        _fetch_availability_rule_signals(),
        _fetch_courses(),
        _fetch_rental_extras(),
    )

    # Enrichment loop — zero further DB queries. Each branch reads from
    # the per-product lookup dicts built above.
    products = []
    for doc in raw_products:
        meta = doc.pop("metadata", None) or {}
        doc["duration_label"] = meta.get("duration_label")
        doc["slot_duration_minutes"] = meta.get("slot_duration_minutes")
        doc["rental_unit"] = meta.get("rental_unit")
        # F1 Onda 8 — surface attendee policy to the storefront so it can
        # render the per-ticket holder forms in the checkout dialog.
        doc["requires_attendee_details"] = bool(meta.get("requires_attendee_details"))
        # F2 Onda 9 — expose required-ness flags and custom field lists.
        # Defaults preserve F1 behavior (email required, phone optional,
        # no custom fields).
        doc["require_attendee_email"] = bool(meta.get("require_attendee_email", True))
        doc["require_attendee_phone"] = bool(meta.get("require_attendee_phone", False))
        # Defensive sanitization: FieldConfig.label has min_length=1, so any
        # historic / manually-crafted row with an empty-label entry would
        # crash PublicProduct validation below and make the entire store
        # catalog unreachable. Silently drop those entries here.
        def _valid_field(f):
            return bool((f or {}).get("label") and str(f.get("label")).strip())
        doc["attendee_fields"] = [
            f for f in (meta.get("attendee_fields") or []) if _valid_field(f)
        ]
        doc["order_fields"] = [
            f for f in (meta.get("order_fields") or []) if _valid_field(f)
        ]
        # F4 Onda 11 — pre-resolve T&C (product override → store default)
        doc["terms_content"] = resolve_effective_terms_sync(
            product={"metadata": meta}, store=org.get("_store") or {},
        )
        # Onda 14 — surface cover image + long description from metadata so
        # the landing page can render them without a second fetch.
        doc["cover_image_url"] = meta.get("cover_image_url")
        doc["long_description"] = meta.get("long_description")
        # F5 Onda 12 — surface service options + duration + slot capability
        # only for service products. For other item_types these fields
        # default to empty / None and are harmless to the storefront.
        doc["service_duration_minutes"] = meta.get("duration_minutes")
        doc["service_allow_custom_request"] = bool(meta.get("service_allow_custom_request"))
        doc["service_options"] = []
        doc["has_availability_slots"] = False
        if doc.get("item_type") == "service":
            doc["service_options"] = service_options_by_product.get(doc["id"], [])
            # Onda 15 parity — `use_default_schedule` metadata flag tells
            # the slot generator to synthesize slots without concrete
            # rule rows in the DB. Mirror that here so the storefront
            # knows to show the picker.
            doc["has_availability_slots"] = (
                has_global_rule
                or doc["id"] in products_with_rule
                or bool(meta.get("use_default_schedule"))
            )

        # Release 4 (Courses) — lightweight counters for the catalog card.
        doc["course_lessons_count"] = None
        doc["course_duration_seconds"] = None
        doc["course_access_policy"] = None
        doc["course_access_expiry_days"] = None
        if doc.get("item_type") == "course":
            course_id = meta.get("course_id")
            if course_id:
                course_doc = courses_by_id.get(course_id)
                if course_doc:
                    lessons = [l for m in (course_doc.get("modules") or [])
                                 for l in (m.get("lessons") or [])]
                    doc["course_lessons_count"] = len(lessons)
                    doc["course_duration_seconds"] = sum(
                        int(l.get("duration_seconds") or 0) for l in lessons
                    )
                    doc["course_access_policy"] = course_doc.get("access_policy") or "lifetime"
                    doc["course_access_expiry_days"] = course_doc.get("access_expiry_days")

        # Onda 16 — expose reservation_flavor + extras for rental products.
        doc["reservation_flavor"] = meta.get("reservation_flavor")
        # Fix caparra (4/7/2026) — il checkout dello store deve poter dire
        # "oggi paghi solo la caparra": senza il piano nel catalogo, il
        # riepilogo mostrava il totale e il cliente credeva di pagarlo tutto
        # (la session Stripe chiedeva comunque la caparra giusta — bug di
        # comunicazione, non di soldi). Stesso campo già esposto dalla
        # landing evento (PublicEventLanding).
        doc["payment_plan"] = meta.get("payment_plan")
        doc.pop("translations", None)   # interne: il merge e' gia' fatto
        doc["extras"] = []
        if doc.get("item_type") == "rental":
            doc["extras"] = extras_by_product.get(doc["id"], [])
        # Resilience: a single malformed product must not take the whole
        # storefront offline. If Pydantic rejects this row, log + skip so
        # the other products keep rendering. The merchant can reconcile
        # the bad row from the admin dashboard (or via the cleanup script).
        try:
            products.append(PublicProduct(**doc))
        except Exception as exc:
            logger.warning(
                "public_catalog: skipping malformed product id=%s name=%r: %s",
                doc.get("id"), doc.get("name"), exc,
            )

    # Fetch published occurrences for event_ticket products (with booking counts)
    event_product_ids = [p.id for p in products if p.item_type == "event_ticket"]
    if event_product_ids:
        occ_cursor = event_occurrences_collection.find(
            {"organization_id": org["id"], "product_id": {"$in": event_product_ids}, "status": "published"},
            {
                "_id": 0, "id": 1, "product_id": 1, "start_at": 1, "end_at": 1,
                "location": 1, "capacity": 1, "price_override": 1,
                # E2 additions — structured presentation fields
                "venue_name": 1, "address": 1, "city": 1, "postal_code": 1,
                "country": 1, "latitude": 1, "longitude": 1, "map_url": 1,
                "cover_image_url": 1, "long_description": 1,
                # F2: slug for storefront card deep-link
                "slug": 1,
            },
        ).sort("start_at", 1).limit(500)
        occ_list = await occ_cursor.to_list(500)

        # Compute booked quantities per occurrence
        occ_ids = [o["id"] for o in occ_list]
        booked_map = {}
        if occ_ids:
            pipeline = [
                {"$match": {
                    "organization_id": org["id"],
                    "status": {"$ne": "cancelled"},
                    "items.occurrence_id": {"$in": occ_ids},
                }},
                {"$unwind": "$items"},
                {"$match": {"items.occurrence_id": {"$in": occ_ids}}},
                {"$group": {"_id": "$items.occurrence_id", "total_qty": {"$sum": "$items.quantity"}}},
            ]
            async for doc in orders_collection.aggregate(pipeline):
                booked_map[doc["_id"]] = int(doc["total_qty"])

        # E1: fetch active tiers for all these occurrences in one round-trip
        tiers_by_occ: dict[str, list] = {}
        if occ_ids:
            from database import event_ticket_tiers_collection
            tier_cursor = event_ticket_tiers_collection.find(
                {"organization_id": org["id"], "occurrence_id": {"$in": occ_ids}, "is_active": True},
                {"_id": 0, "id": 1, "occurrence_id": 1, "label": 1, "description": 1,
                 "price": 1, "capacity": 1, "reserved_seats": 1, "sort_order": 1},
            ).sort([("sort_order", 1), ("created_at", 1)])
            async for t in tier_cursor:
                occ_pid = t.pop("occurrence_id")
                cap_t = t.get("capacity")
                used_t = int(t.get("reserved_seats") or 0)
                public_tier = {
                    "id": t["id"],
                    "label": t["label"],
                    "description": t.get("description"),
                    "price": float(t.get("price") or 0),
                    "remaining": None if cap_t is None else max(0, cap_t - used_t),
                    "sort_order": int(t.get("sort_order") or 0),
                }
                tiers_by_occ.setdefault(occ_pid, []).append(PublicTier(**public_tier))

        # E2: derive map_url from structured location when admin did not
        # set an explicit override. Pure derivation, no external calls.
        from models.event_occurrence import build_map_url

        occ_by_product: dict[str, list] = {}
        for occ_doc in occ_list:
            pid = occ_doc.pop("product_id")
            cap = occ_doc.get("capacity")
            booked = booked_map.get(occ_doc["id"], 0)
            occ_doc["booked_count"] = booked if cap else None
            occ_doc["remaining"] = max(0, cap - booked) if cap else None
            occ_doc["tiers"] = tiers_by_occ.get(occ_doc["id"], [])
            # E2: if map_url was not set by the admin but we have either
            # lat/lng or a composed address, build the Google Maps link.
            if not occ_doc.get("map_url"):
                derived = build_map_url(occ_doc)
                if derived:
                    occ_doc["map_url"] = derived
            occ_by_product.setdefault(pid, []).append(PublicOccurrence(**occ_doc))

        for p in products:
            if p.item_type == "event_ticket":
                p.occurrences = occ_by_product.get(p.id, [])

        # Hide event products that have no published occurrence — occurrence.status
        # is the single visibility control; a product with only draft occurrences
        # must not appear on the storefront.
        products = [
            p for p in products
            if p.item_type != "event_ticket" or p.occurrences
        ]

    # v12.0: read store info from resolved _store (multi-store or legacy)
    resolved_store = org.get("_store") or {}
    ff_modes = resolved_store.get("fulfillment_modes") or ["shipping"]

    # ── Branding cascade ───────────────────────────────────────────────────
    # The visual identity fields (logo, colors, favicon) flow through the
    # centralized resolver in services/branding_service.py with priority
    #
    #     Store value > Org branding > legacy org.store_settings
    #
    # `strict_override=False` mirrors the previous inline `or` semantics:
    # falsy Store values inherit from Org. The new "olistic settings"
    # admin UI uses None/explicit-clear, so this is byte-for-byte
    # compatible with what existed before this commit. The text fields
    # (display_name, descriptions, contacts, SEO) are NOT in the
    # branding scope — they stay store-or-legacy fallback inline.
    branding = resolve_branding_for_store(resolved_store, org)

    # Legacy fallback layer: pre-v12 orgs put branding in
    # org.store_settings (a generic dict). Prefer the resolver output;
    # only fall back to store_settings when the resolver returned None.
    ss = org.get("store_settings") or {}

    si = StoreInfo(
        display_name=resolved_store.get("name") or resolved_store.get("display_name") or ss.get("display_name") or None,
        store_description=resolved_store.get("description") or resolved_store.get("store_description") or ss.get("store_description") or None,
        contact_email=resolved_store.get("contact_email") or ss.get("contact_email") or None,
        contact_phone=resolved_store.get("contact_phone") or ss.get("contact_phone") or None,
        logo_url=branding.get("logo_url") or ss.get("logo_url"),
        brand_color=branding.get("brand_color") or ss.get("brand_color"),
        brand_color_text=branding.get("brand_color_text") or ss.get("brand_color_text"),
        seo_title=resolved_store.get("seo_title") or ss.get("seo_title"),
        seo_description=resolved_store.get("seo_description") or ss.get("seo_description"),
    )
    # `has_info` decides whether to expose `store_info` to the client.
    # We must include the visual branding fields (logo, colors, SEO) —
    # otherwise a store that ONLY inherits a logo from the org cascade
    # (no description / contacts of its own) ends up with store_info=None,
    # and the AuthShell login header never sees the org logo. Before the
    # olistic-settings feature this was harmless because logos always
    # came from the same store row that had a name/description; now
    # branding can come from a higher level than the text fields.
    has_info = (
        si.display_name or si.store_description
        or si.contact_email or si.contact_phone
        or si.logo_url or si.brand_color or si.brand_color_text
        or si.seo_title or si.seo_description
    )

    from services.currency_service import get_currency_for_org

    return CatalogResponse(
        org_name=org.get("name", ""),
        slug=slug,
        products=products,
        currency=get_currency_for_org(org),
        fulfillment_modes=ff_modes,
        store_info=si if has_info else None,
        storefront_languages=resolved_store.get("storefront_languages") or ["it"],
        # Phase 8 — Custom navigation links from the merchant's store
        # config. Empty list = no custom links configured (most stores
        # at launch). The frontend CategoryNav renders them alongside
        # the auto-generated category pills.
        custom_nav_links=resolved_store.get("custom_nav_links") or [],
        # Phase 9 — Design tokens pass-through.
        design_tokens=resolved_store.get("design_tokens") or {},
    )


@router.get("/events/{org_slug}/{slug}", response_model=PublicEventLanding)
async def get_public_event_landing(org_slug: str, slug: str,
    # en|de|fr per contenuti tradotti (default semplice: vedi catalog)
    lang: str = None):
    """Public landing page payload for a single event occurrence.

    Returns 404 when:
      - the org/store slug is unknown
      - no occurrence with that slug exists in the org
      - the occurrence is not in 'published' status
      - the parent product is unpublished / inactive / not event_ticket

    When live, the response carries everything the frontend needs to
    render the landing in one round-trip: org branding, product title
    and image, structured occurrence details (venue / address / lat-lng
    / cover / long_description), tier cards with live remaining, and a
    boolean `is_buyable` flag.
    """
    from database import (
        event_occurrences_collection,
        event_ticket_tiers_collection,
        products_collection,
        orders_collection,
    )

    org = await _resolve_org(org_slug)

    occ = await event_occurrences_collection.find_one(
        {
            "organization_id": org["id"],
            "slug": slug,
            "status": "published",
        },
        {"_id": 0},
    )
    if not occ:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    product = await products_collection.find_one(
        {
            "id": occ["product_id"],
            "organization_id": org["id"],
            "is_active": True,
            "is_published": True,
            "item_type": "event_ticket",
        },
        {
            "_id": 0, "id": 1, "name": 1, "description": 1,
            "image_url": 1, "transaction_mode": 1,
            "metadata": 1,  # F1 Onda 8 — needed for requires_attendee_details
            # Onda 15 — unit_price exposed for mono-tier event totals.
            "unit_price": 1,
            # Multilingua manuale — serve al merge_language per ?lang=
            "translations": 1,
            # M2 — breadcrumb Ritiri › categoria › titolo
            "category": 1,
        },
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Booked count for remaining calculation (occurrence-level)
    booked = 0
    if occ.get("capacity"):
        pipeline = [
            {"$match": {
                "organization_id": org["id"],
                "status": {"$ne": "cancelled"},
                "items.occurrence_id": occ["id"],
            }},
            {"$unwind": "$items"},
            {"$match": {"items.occurrence_id": occ["id"]}},
            {"$group": {"_id": None, "total_qty": {"$sum": "$items.quantity"}}},
        ]
        cursor = orders_collection.aggregate(pipeline)
        async for doc in cursor:
            booked = int(doc.get("total_qty") or 0)

    # Load active tiers (event_ticket_tiers_collection imported above)
    tiers: list = []
    tier_cursor = event_ticket_tiers_collection.find(
        {"organization_id": org["id"], "occurrence_id": occ["id"], "is_active": True},
        {"_id": 0, "id": 1, "label": 1, "description": 1,
         "price": 1, "capacity": 1, "reserved_seats": 1, "sort_order": 1},
    ).sort([("sort_order", 1), ("created_at", 1)])
    async for t in tier_cursor:
        cap_t = t.get("capacity")
        used_t = int(t.get("reserved_seats") or 0)
        tiers.append(PublicTier(
            id=t["id"],
            label=t["label"],
            description=t.get("description"),
            price=float(t.get("price") or 0),
            remaining=None if cap_t is None else max(0, cap_t - used_t),
            sort_order=int(t.get("sort_order") or 0),
        ))

    # Capacity truth for the occurrence
    cap = occ.get("capacity")
    remaining = None if cap is None else max(0, cap - booked)
    occ_booked_count = booked if cap else None

    # Auto-derive map_url if admin did not explicitly set one
    from models.event_occurrence import build_map_url
    map_url = occ.get("map_url") or build_map_url(occ)
    # Multilingua MANUALE (6/7, decisione founder: zero LLM) — merge dei
    # campi tradotti DALL'OPERATORE; il badge auto-translated non serve
    # piu' (sono parole sue). La pipeline LLM resta dormiente e spenta.
    _auto_translated = False
    if lang and lang in ("en", "de", "fr"):
        from services.manual_translations import (
            merge_language, merge_occurrence_language,
        )
        merged = merge_language(product, lang)
        if merged is not product:
            product = merged
            # il racconto lungo tradotto vive sul product.translations:
            # sovrascrive quello dell'occurrence quando presente
            tr = (product.get("translations") or {}).get(lang) or {}
            if tr.get("long_description"):
                occ = {**occ, "long_description": tr["long_description"]}
        # Traduzione olistica pagina di vendita: agenda / incluso /
        # escluso / FAQ dall'operatore; blocchi non tradotti (o con
        # struttura divergente) restano in italiano — mai sfasati.
        occ = merge_occurrence_language(occ, lang)


    public_occ = PublicOccurrence(
        id=occ["id"],
        start_at=occ["start_at"],
        end_at=occ.get("end_at"),
        location=occ.get("location"),
        capacity=cap,
        booked_count=occ_booked_count,
        remaining=remaining,
        price_override=occ.get("price_override"),
        tiers=tiers,
        venue_name=occ.get("venue_name"),
        address=occ.get("address"),
        city=occ.get("city"),
        postal_code=occ.get("postal_code"),
        country=occ.get("country"),
        latitude=occ.get("latitude"),
        longitude=occ.get("longitude"),
        map_url=map_url,
        cover_image_url=occ.get("cover_image_url"),
        long_description=occ.get("long_description"),
        # Fase 3 — contenuti pagina di vendita
        agenda=occ.get("agenda") or [],
        gallery_urls=occ.get("gallery_urls") or [],
        included=occ.get("included") or [],
        excluded=occ.get("excluded") or [],
        faq=occ.get("faq") or [],
    )

    # Store info (branding) — same logic as the catalog handler
    resolved_store = org.get("_store") or {}
    ss = org.get("store_settings") or {}
    si = StoreInfo(
        display_name=resolved_store.get("name") or resolved_store.get("display_name") or ss.get("display_name") or None,
        store_description=resolved_store.get("description") or resolved_store.get("store_description") or ss.get("store_description") or None,
        contact_email=resolved_store.get("contact_email") or ss.get("contact_email") or None,
        contact_phone=resolved_store.get("contact_phone") or ss.get("contact_phone") or None,
        logo_url=resolved_store.get("logo_url") or ss.get("logo_url"),
        brand_color=resolved_store.get("brand_color") or ss.get("brand_color"),
        brand_color_text=resolved_store.get("brand_color_text") or ss.get("brand_color_text"),
        seo_title=ss.get("seo_title"),
        seo_description=ss.get("seo_description"),
    )
    has_info = any([si.display_name, si.store_description, si.logo_url, si.brand_color])

    # Buyability: occurrence is published (we already filtered), not globally
    # sold out, and has either tiers with remaining OR unlimited capacity.
    occurrence_has_room = remaining is None or remaining > 0
    tier_has_room = not tiers or any(
        (t.remaining is None or t.remaining > 0) for t in tiers
    )
    is_buyable = occurrence_has_room and tier_has_room

    from services.currency_service import get_currency_for_org

    return PublicEventLanding(
        org_slug=org_slug,
        org_name=org.get("name", ""),
        auto_translated=_auto_translated,
        store_info=si if has_info else None,
        product=PublicEventProduct(
            id=product["id"],
            name=product.get("name", ""),
            description=product.get("description"),
            image_url=product.get("image_url"),
            transaction_mode=product.get("transaction_mode", "direct"),
            category=product.get("category"),   # M2 — breadcrumb landing
            currency=get_currency_for_org(org),
            # Onda 15 — base unit_price for mono-tier events (no tiers &
            # no per-occurrence override). The landing riepilogo falls
            # back to this when occurrence.price_override is null.
            unit_price=product.get("unit_price"),
            requires_attendee_details=bool((product.get("metadata") or {}).get("requires_attendee_details")),
            # F2 Onda 9 — surface required-ness + custom fields so the
            # landing page can inform the user ahead of the checkout step.
            require_attendee_email=bool((product.get("metadata") or {}).get("require_attendee_email", True)),
            require_attendee_phone=bool((product.get("metadata") or {}).get("require_attendee_phone", False)),
            attendee_fields=(product.get("metadata") or {}).get("attendee_fields") or [],
            order_fields=(product.get("metadata") or {}).get("order_fields") or [],
            # F4 Onda 11 — pre-resolved T&C
            terms_content=resolve_effective_terms_sync(
                product=product, store=org.get("_store") or {},
            ),
            # Fase 2 S2 — piano pagamenti pubblico
            payment_plan=(product.get("metadata") or {}).get("payment_plan"),
        ),
        occurrence=public_occ,
        is_buyable=is_buyable,
    )


# ── Onda 3 (i18n) — shared storefront-context helper for token landings ────


_VALID_STOREFRONT_LANGS = {"it", "en", "de", "fr"}


def _normalize_storefront_languages(value) -> Optional[List[str]]:
    """Coerce a stored storefront_languages list into the 4-locale subset.

    Accepts None / non-list / empty list and returns None — the public
    payload then ships `null` and the frontend falls back to its own
    resolver chain. Filters out unknown codes silently rather than
    leaking implementation detail to the page.
    """
    if not value or not isinstance(value, (list, tuple)):
        return None
    out: List[str] = []
    for v in value:
        try:
            code = str(v).strip().lower().replace("_", "-").split("-")[0]
        except Exception:
            continue
        if code in _VALID_STOREFRONT_LANGS and code not in out:
            out.append(code)
    return out or None


async def _resolve_store_context_for_product(
    product: dict, org_id: Optional[str] = None,
) -> tuple:
    """Resolve (slug, name, storefront_languages) for a product's storefront.

    Used by the public token-landing endpoints so the /t /b /d /rsv pages
    can mount StoreMetaProvider and render in the storefront's language.

    Resolution order:
      1. product.store_id (single-store assignment) → that store.
      2. product.store_ids[0] (multi-store assignment) → first match in the
         org. The first-published+public store is preferred when multiple
         match, mirroring how the storefront resolves catalog pages.
      3. First published+public store of the org (legacy fallback).

    Returns (None, None, None) on any error or when nothing resolves.
    """
    if not product:
        return None, None, None
    try:
        from database import stores_collection

        candidate_id = product.get("store_id")
        if not candidate_id:
            ids = product.get("store_ids") or []
            if isinstance(ids, list) and ids:
                candidate_id = ids[0]

        store = None
        if candidate_id:
            store = await stores_collection.find_one(
                {"id": candidate_id},
                {"_id": 0, "slug": 1, "name": 1, "storefront_languages": 1,
                 "organization_id": 1, "is_published": 1, "is_active": 1,
                 "visibility": 1},
            )
            # Don't leak a store that's no longer published — fall through.
            if store and not (
                store.get("is_published") and store.get("is_active")
                and store.get("visibility") == "public"
            ):
                store = None

        if not store and org_id:
            store = await stores_collection.find_one(
                {"organization_id": org_id, "is_published": True,
                 "is_active": True, "visibility": "public"},
                {"_id": 0, "slug": 1, "name": 1, "storefront_languages": 1},
            )

        if not store:
            return None, None, None

        return (
            store.get("slug") or None,
            store.get("name") or None,
            _normalize_storefront_languages(store.get("storefront_languages")),
        )
    except Exception:
        return None, None, None


# ── F1 Onda 8 — public ticket landing page payload ─────────────────────────

class PublicTicketPayload(BaseModel):
    """What the /t/{token} landing page renders. No auth; the token is the key.

    The QR encodes the ticket `code` (EVT-AAAA-BBBB) which is used at the
    door. Exposing the code in the URL would make trivial "check in by HTTP"
    attacks possible, so the URL uses a separate access_token instead.
    """
    holder_name: Optional[str] = None
    holder_email: Optional[str] = None
    tier_label: Optional[str] = None
    seat_index: int = 1
    seat_count: int = 1
    # QR-ready image (data URI) of the ticket code for offline display.
    qr_data_uri: str
    # Plain text code — used by the scanner and printed under the QR.
    code: str
    status: str = "valid"  # valid | checked_in | voided

    # Event context
    event_name: str
    event_start_at: Optional[str] = None
    event_end_at: Optional[str] = None
    venue_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    cover_image_url: Optional[str] = None

    # Storefront i18n context (Onda 3 — multilingua landing pages).
    # The frontend uses these to mount StoreMetaProvider so the page
    # renders in the storefront's language even when the visitor has
    # no localStorage from a prior storefront visit. All Optional —
    # legacy tokens issued before the lookup was added still resolve.
    store_slug: Optional[str] = None
    store_name: Optional[str] = None
    storefront_languages: Optional[List[str]] = None


@router.get("/tickets/{access_token}", response_model=PublicTicketPayload)
async def get_public_ticket(access_token: str):
    """Public endpoint for the /t/{token} landing page.

    Returns 404 when:
      - token doesn't match any ticket
      - token is expired
      - ticket status is voided (e.g. order was cancelled)

    No auth; the unguessable token is the access credential.
    """
    from database import issued_tickets_collection, event_occurrences_collection, products_collection
    from services.ticket_service import qr_data_uri
    from datetime import datetime, timezone

    if not access_token or len(access_token) < 10:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biglietto non trovato")

    ticket = await issued_tickets_collection.find_one(
        {"access_token": access_token},
        {"_id": 0},
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biglietto non trovato")

    # Voided tickets are no longer viewable (order was cancelled)
    if ticket.get("status") == "voided":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biglietto annullato")

    # Expiry check
    exp = ticket.get("access_token_expires_at")
    if exp:
        try:
            exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if now > exp_dt:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Biglietto scaduto")
        except HTTPException:
            raise
        except Exception:
            pass  # Malformed expiry date — don't block access on parse errors

    # Hydrate event context
    occ = await event_occurrences_collection.find_one(
        {"id": ticket["occurrence_id"]},
        {"_id": 0, "start_at": 1, "end_at": 1, "venue_name": 1,
         "address": 1, "city": 1, "cover_image_url": 1, "product_id": 1},
    ) or {}
    prod = await products_collection.find_one(
        {"id": ticket["product_id"]},
        {"_id": 0, "name": 1, "image_url": 1, "store_id": 1, "store_ids": 1,
         "organization_id": 1},
    ) or {}

    # Resolve the storefront context (slug + storefront_languages) so the
    # /t/{token} landing page can mount StoreMetaProvider and render in
    # the right language. Best-effort: if the lookup fails for any reason
    # we still ship the ticket payload (the page falls back to localStorage).
    store_slug, store_name, storefront_langs = await _resolve_store_context_for_product(
        prod, ticket.get("organization_id"),
    )

    return PublicTicketPayload(
        holder_name=ticket.get("holder_name"),
        holder_email=ticket.get("holder_email"),
        tier_label=ticket.get("tier_label"),
        seat_index=ticket.get("seat_index", 1),
        seat_count=ticket.get("seat_count", 1),
        qr_data_uri=qr_data_uri(ticket["code"], box_size=10),
        code=ticket["code"],
        status=ticket.get("status", "valid"),
        event_name=prod.get("name", ""),
        event_start_at=occ.get("start_at"),
        event_end_at=occ.get("end_at"),
        venue_name=occ.get("venue_name"),
        address=occ.get("address"),
        city=occ.get("city"),
        cover_image_url=occ.get("cover_image_url") or prod.get("image_url"),
        store_slug=store_slug,
        store_name=store_name,
        storefront_languages=storefront_langs,
    )


# ── Onda 14 — public booking landing (service appointments) ─────────────────

class PublicBookingPayload(BaseModel):
    """What the /b/{token} landing page renders. No auth; token is the key.

    Analog of PublicTicketPayload for service bookings. No QR here — the
    token itself is the verification credential, and bookings don't have a
    door-scanner. The landing exposes an "Add to calendar" download that
    returns the same booking wrapped as an .ics file.
    """
    code: str
    status: str = "confirmed"
    holder_name: Optional[str] = None
    holder_email: Optional[str] = None

    # Booking slot (floating local time — interpreted as organizer's timezone)
    booking_date: str
    booking_start_time: str
    booking_end_time: str

    service_option_label: Optional[str] = None
    location: Optional[str] = None

    # Product + store context
    product_name: str
    product_image_url: Optional[str] = None
    store_name: Optional[str] = None
    store_slug: Optional[str] = None  # for "back to storefront" link
    # Onda 3 (i18n) — let /b/{token} mount StoreMetaProvider + resolver.
    storefront_languages: Optional[List[str]] = None


async def _resolve_booking_by_token(access_token: str) -> dict:
    """Shared lookup used by both the landing JSON + the ICS download.

    Raises HTTPException 404 on: not found, expired, cancelled.
    """
    from database import issued_bookings_collection
    from datetime import datetime, timezone

    if not access_token or len(access_token) < 10:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prenotazione non trovata")

    booking = await issued_bookings_collection.find_one(
        {"access_token": access_token},
        {"_id": 0},
    )
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prenotazione non trovata")
    if booking.get("status") == "cancelled":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prenotazione annullata")

    # Expiry check
    exp = booking.get("access_token_expires_at")
    if exp:
        try:
            exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if now > exp_dt:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prenotazione scaduta")
        except HTTPException:
            raise
        except Exception:
            pass

    return booking


@router.get("/bookings/{access_token}", response_model=PublicBookingPayload)
async def get_public_booking(access_token: str):
    """Public endpoint for the /b/{token} service booking landing page.

    Returns 404 when: token missing/unknown, booking cancelled, token expired.
    No auth; the unguessable token is the access credential.
    """
    from database import products_collection, organizations_collection, stores_collection

    booking = await _resolve_booking_by_token(access_token)

    prod = await products_collection.find_one(
        {"id": booking["product_id"]},
        {"_id": 0, "name": 1, "image_url": 1, "store_id": 1, "store_ids": 1,
         "organization_id": 1},
    ) or {}

    # Resolve the store name + slug for the "back to storefront" link
    # PLUS storefront_languages (Onda 3) so the page can localize.
    store_slug, store_name, storefront_langs = await _resolve_store_context_for_product(
        prod, booking.get("organization_id"),
    )
    if not store_name:
        org = await organizations_collection.find_one(
            {"id": booking["organization_id"]}, {"_id": 0, "name": 1},
        ) or {}
        store_name = org.get("name")

    return PublicBookingPayload(
        code=booking["code"],
        status=booking.get("status", "confirmed"),
        holder_name=booking.get("holder_name"),
        holder_email=booking.get("holder_email"),
        booking_date=booking["booking_date"],
        booking_start_time=booking["booking_start_time"],
        booking_end_time=booking["booking_end_time"],
        service_option_label=booking.get("service_option_label"),
        location=booking.get("location"),
        product_name=prod.get("name", "Consulenza"),
        product_image_url=prod.get("image_url"),
        store_name=store_name,
        store_slug=store_slug,
        storefront_languages=storefront_langs,
    )


@router.get("/bookings/{access_token}/ics")
async def download_booking_ics(access_token: str):
    """Return the booking as an .ics calendar file.

    Same auth/expiry rules as GET /bookings/{token}.
    """
    from fastapi.responses import Response
    from database import products_collection
    from services.ics_service import build_ics_for_booking
    from services.url_builder import build_public_url

    booking = await _resolve_booking_by_token(access_token)
    prod = await products_collection.find_one(
        {"id": booking["product_id"]}, {"_id": 0, "name": 1},
    ) or {}
    product_name = prod.get("name", "Consulenza")

    booking_url = build_public_url(f"/b/{access_token}")
    ics_text = build_ics_for_booking(booking, product_name=product_name, url=booking_url)

    if not ics_text:
        raise HTTPException(status_code=500, detail="Impossibile generare calendario")

    filename = f"prenotazione-{booking.get('code', 'aurya')}.ics"
    return Response(
        content=ics_text,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Onda 16 — Public reservation landing (rental range + slot) ─────────────

class PublicReservationPayload(BaseModel):
    """Shape returned by GET /api/public/reservations/{access_token}.

    Covers both flavors (range: date_from/date_to; slot: slot_*). Extras
    are exposed as a minimal list so the storefront landing can render
    the full summary.
    """
    code: str
    status: str
    reservation_flavor: str
    product_name: str
    holder_name: Optional[str] = None
    holder_email: Optional[str] = None
    location: Optional[str] = None

    date_from: Optional[str] = None
    date_to: Optional[str] = None
    slot_date: Optional[str] = None
    slot_start_time: Optional[str] = None
    slot_end_time: Optional[str] = None

    extras: list = []

    # Product image for the landing hero.
    product_image_url: Optional[str] = None
    store_name: Optional[str] = None
    store_slug: Optional[str] = None
    # Onda 3 (i18n) — let /rsv/{token} mount StoreMetaProvider + resolver.
    storefront_languages: Optional[List[str]] = None


async def _resolve_reservation_by_token(access_token: str) -> dict:
    """Shared lookup used by the landing JSON + the ICS download.

    Raises 404 on: not found, cancelled, expired.
    """
    from services.issued_reservation_service import get_by_token
    from datetime import datetime as _dt, timezone

    if not access_token or len(access_token) < 10:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prenotazione non trovata")
    reservation = await get_by_token(access_token)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prenotazione non trovata")
    if reservation.get("status") == "cancelled":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prenotazione annullata")

    exp = reservation.get("access_token_expires_at")
    if exp:
        try:
            exp_dt = _dt.fromisoformat(exp.replace("Z", "+00:00"))
            now = _dt.now(timezone.utc)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if now > exp_dt:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prenotazione scaduta")
        except HTTPException:
            raise
        except Exception:
            pass
    return reservation


@router.get("/reservations/{access_token}", response_model=PublicReservationPayload)
async def get_public_reservation(access_token: str):
    """Public landing payload for /rsv/{access_token}."""
    from database import products_collection, stores_collection, organizations_collection

    reservation = await _resolve_reservation_by_token(access_token)

    # Hydrate product image + store info (best-effort).
    product = await products_collection.find_one(
        {"id": reservation["product_id"]},
        {"_id": 0, "name": 1, "image_url": 1, "store_id": 1, "store_ids": 1,
         "organization_id": 1},
    ) or {}

    # Single shared resolver also feeds the new storefront_languages field
    # used by the /rsv/{token} landing to localise the page (Onda 3).
    store_slug, store_name, storefront_langs = await _resolve_store_context_for_product(
        product, reservation.get("organization_id"),
    )
    if not store_name:
        org = await organizations_collection.find_one(
            {"id": reservation["organization_id"]}, {"_id": 0, "name": 1},
        ) or {}
        store_name = org.get("name")

    return PublicReservationPayload(
        code=reservation["code"],
        status=reservation.get("status", "active"),
        reservation_flavor=reservation.get("reservation_flavor", "range"),
        product_name=product.get("name") or reservation.get("product_name", "Prenotazione"),
        holder_name=reservation.get("holder_name"),
        holder_email=reservation.get("holder_email"),
        location=reservation.get("location"),
        date_from=reservation.get("date_from"),
        date_to=reservation.get("date_to"),
        slot_date=reservation.get("slot_date"),
        slot_start_time=reservation.get("slot_start_time"),
        slot_end_time=reservation.get("slot_end_time"),
        extras=reservation.get("extras_snapshot") or [],
        product_image_url=product.get("image_url"),
        store_name=store_name,
        store_slug=store_slug,
        storefront_languages=storefront_langs,
    )


@router.get("/reservations/{access_token}/ics")
async def download_reservation_ics(access_token: str):
    """Return the reservation as an .ics calendar file."""
    from fastapi.responses import Response
    from services.ics_service import build_ics_for_reservation
    from database import products_collection
    from services.url_builder import build_public_url

    reservation = await _resolve_reservation_by_token(access_token)
    product = await products_collection.find_one(
        {"id": reservation["product_id"]}, {"_id": 0, "name": 1},
    ) or {}
    product_name = product.get("name") or reservation.get("product_name") or "Prenotazione"

    landing_url = build_public_url(f"/rsv/{access_token}")
    ics_text = build_ics_for_reservation(reservation, product_name=product_name, url=landing_url)
    if not ics_text:
        raise HTTPException(status_code=500, detail="Impossibile generare calendario")

    filename = f"prenotazione-{reservation.get('code', 'aurya')}.ics"
    return Response(
        content=ics_text,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Release 3 (Digital): public download landing + file stream ──────────────


class PublicDownloadPayload(BaseModel):
    """Shape returned by GET /api/public/downloads/{access_token}.

    The storefront landing at /d/{token} renders this payload. `status`
    plus `downloads_remaining` + `expires_at` let the UI display a
    precise reason when the link is no longer usable.
    """
    code: str
    product_name: str
    holder_name: Optional[str] = None
    download_filename: Optional[str] = None
    download_size_bytes: Optional[int] = None
    download_mime_type: Optional[str] = None
    status: str                                # active | exhausted | cancelled | expired
    downloads_remaining: Optional[int] = None  # None = unlimited
    downloads_used: int = 0
    max_downloads: Optional[int] = None
    expires_at: Optional[str] = None

    # Storefront i18n context (Onda 3 — multilingua landing pages).
    # Same purpose + fallback semantics as PublicTicketPayload.
    store_slug: Optional[str] = None
    store_name: Optional[str] = None
    storefront_languages: Optional[List[str]] = None


def _now_iso_utc() -> str:
    """UTC ISO timestamp for expiry comparisons."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _download_effective_status(row: dict) -> str:
    """Derive the user-facing status from the stored row + expiry check.

    The stored `status` handles active/cancelled/exhausted. Expiry is
    computed dynamically because a TTL sweep isn't worth the ops cost for
    this volume.
    """
    base = (row or {}).get("status") or "active"
    if base != "active":
        return base
    expires = (row or {}).get("access_token_expires_at")
    if expires:
        try:
            # String compare works because ISO-8601 with matching offsets
            # sorts chronologically. We normalize to UTC on write, so this
            # comparison is safe.
            if expires < _now_iso_utc():
                return "expired"
        except Exception:
            pass
    return base


@router.get("/downloads/{access_token}", response_model=PublicDownloadPayload)
@limiter.limit("30/minute")
async def get_public_download(request: Request, access_token: str):
    """Token-gated landing payload for /d/{access_token}.

    Always returns 200 + a payload with `status`, regardless of whether
    the link is usable — the UI renders the appropriate copy per status.
    A 404 is only returned when the token is unknown (prevents inference
    attacks that would otherwise probe valid-but-expired links).
    """
    from services.issued_download_service import get_by_token
    from database import products_collection

    row = await get_by_token(access_token)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link non valido o scaduto",
        )

    effective = _download_effective_status(row)
    max_dl = row.get("max_downloads")
    used = int(row.get("download_count", 0) or 0)
    remaining = (int(max_dl) - used) if max_dl is not None else None

    # Resolve storefront context (slug + storefront_languages) so the
    # /d/{token} landing page can mount StoreMetaProvider and render in
    # the right language. Best-effort.
    prod = await products_collection.find_one(
        {"id": row.get("product_id")},
        {"_id": 0, "store_id": 1, "store_ids": 1, "organization_id": 1},
    ) or {}
    store_slug, store_name, storefront_langs = await _resolve_store_context_for_product(
        prod, row.get("organization_id"),
    )

    return PublicDownloadPayload(
        code=row.get("code", ""),
        product_name=row.get("product_name") or "Download",
        holder_name=row.get("holder_name"),
        download_filename=row.get("download_filename"),
        download_size_bytes=row.get("download_size_bytes"),
        download_mime_type=row.get("download_mime_type"),
        status=effective,
        downloads_remaining=remaining,
        downloads_used=used,
        max_downloads=max_dl,
        expires_at=row.get("access_token_expires_at"),
        store_slug=store_slug,
        store_name=store_name,
        storefront_languages=storefront_langs,
    )


@router.get("/downloads/{access_token}/file")
@limiter.limit("10/minute")
async def download_digital_file(request: Request, access_token: str):
    """Stream the digital payload under the token.

    Runs all lifecycle checks, then atomically increments the download
    counter before streaming bytes via FileResponse with
    `Content-Disposition: attachment`.

    Status mapping:
      404 — token unknown OR order cancelled
      410 — exhausted OR expired (link was valid, no longer is)
      200 — file streamed
    """
    from fastapi.responses import FileResponse
    from services.issued_download_service import get_by_token, increment_download_count
    from services import digital_storage

    row = await get_by_token(access_token)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link non valido",
        )

    effective = _download_effective_status(row)
    if effective == "cancelled":
        # Treat cancelled as 404 to avoid leaking that the token ever existed.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link non valido",
        )
    if effective in ("exhausted", "expired"):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "Il link di download è scaduto"
                if effective == "expired"
                else "Hai raggiunto il numero massimo di download"
            ),
        )

    # Pre-check capacity before we touch disk so we don't increment for a
    # request that would be rejected anyway.
    max_dl = row.get("max_downloads")
    used = int(row.get("download_count", 0) or 0)
    if max_dl is not None and used >= int(max_dl):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Hai raggiunto il numero massimo di download",
        )

    try:
        on_disk = digital_storage.resolve_digital_path(
            row["organization_id"], row["product_id"],
        )
    except (FileNotFoundError, ValueError):
        logger.warning(
            "download_digital_file: file missing on disk for issued_download id=%s",
            row.get("id"),
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Il file non è più disponibile. Contatta il merchant.",
        )

    # Atomically bump counter + maybe flip to exhausted.
    await increment_download_count(row["id"])

    filename_for_client = (row.get("download_filename") or on_disk.name)[:200]
    media_type = row.get("download_mime_type") or "application/octet-stream"
    return FileResponse(
        path=str(on_disk),
        media_type=media_type,
        filename=filename_for_client,
    )


# ── Shipping options (public) — checkout picker ──────────────────────────


class PublicShippingOptionsResponse(BaseModel):
    """Shape returned by GET /api/public/shipping-options/{store_slug}.

    Client uses this to render the radio-picker at checkout. The backend
    validates the final choice independently at order-creation time.
    """
    options: List[PublicShippingOption]


@router.get(
    "/shipping-options/{store_slug}",
    response_model=PublicShippingOptionsResponse,
)
@limiter.limit("30/minute")
async def get_public_shipping_options(request: Request, store_slug: str):
    """Return the shipping options available at this store's checkout.

    Union of per-store options and org-global (store_id=null) options,
    filtered to is_active=True, sorted by (sort_order, label).

    An empty list is a legitimate answer — the storefront surfaces a
    "no options configured" banner and disables the submit.
    """
    from services.shipping_service import resolve_shipping_options

    org = await _resolve_org(store_slug)
    store = org.get("_store") or {}
    options = await resolve_shipping_options(
        org_id=org["id"], store_id=store.get("id") or "",
    )
    # Strip admin-only fields for the public response.
    public_options = [
        PublicShippingOption(
            id=o["id"],
            label=o["label"],
            description=o.get("description"),
            base_price=float(o.get("base_price") or 0),
            free_shipping_threshold=(
                float(o["free_shipping_threshold"])
                if o.get("free_shipping_threshold") is not None else None
            ),
            sort_order=int(o.get("sort_order") or 0),
        )
        for o in options
    ]
    return PublicShippingOptionsResponse(options=public_options)


# ── Rental range availability (public) — Onda 16 UX hardening ─────────────

@router.get("/reservations/blocked-dates/{product_id}")
@limiter.limit("30/minute")
async def public_rental_blocked_dates(
    request: Request,
    product_id: str,
    date_from: str = Query(..., alias="from", description="ISO date YYYY-MM-DD (inclusive lower bound)"),
    date_to: str = Query(..., alias="to", description="ISO date YYYY-MM-DD (inclusive upper bound, max 90 days after from)"),
):
    """Return the unavailable dates for a rental product within a date window.

    Used by the reservation landing page (`/r/:org_slug/:product_slug`) to
    surface already-booked days in the date picker so the customer can't
    attempt a range that will be rejected server-side. The atomic guard at
    confirm time (`try_reserve_rental_range`) remains the source of truth;
    this endpoint is an advisory UX helper.

    Contract:
      - Product must be active + published (no draft leak).
      - Window is capped at 90 days to prevent abuse.
      - Returns `{ blocked_dates: ["YYYY-MM-DD", …] }` sorted and deduplicated.
      - Only blocks with `reason` in {"rental", "booking"} are surfaced — those
        are the ones produced by actual customer confirmations. Manual admin
        blocks (`reason="manual"`) are included too so merchant holidays
        propagate to the storefront as well.
    """
    from database import products_collection, blocked_slots_collection
    from datetime import date as _date, timedelta

    # Validate window
    try:
        d_from = _date.fromisoformat(date_from)
        d_to = _date.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato data non valido (YYYY-MM-DD richiesto)")
    if d_to < d_from:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'to' deve essere >= 'from'")
    if (d_to - d_from).days > 90:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La finestra massima è di 90 giorni")

    # Resolve product (must be published + active; don't leak drafts)
    product = await products_collection.find_one(
        {"id": product_id, "is_active": True, "is_published": True},
        {"_id": 0, "organization_id": 1, "item_type": 1},
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prodotto non trovato")
    if product.get("item_type") != "rental":
        # Endpoint scoped to rental products. Slot-flavor uses the existing
        # `/public/availability/:slug` path for hh:mm granularity.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo per prodotti di tipo rental")

    # R3 — sorgente unica condivisa con l'embed.
    from services.slot_generator import get_rental_blocked_dates
    blocked = await get_rental_blocked_dates(
        product["organization_id"], product_id, date_from, date_to,
    )
    return {"blocked_dates": blocked}


# ── Onda 13 — Generic product landing page (public) ───────────────────────


class PublicCourseLesson(BaseModel):
    """Lesson snippet exposed in the public course landing.

    Deliberately OMITS bunny_video_guid — that value is never leaked to
    anonymous visitors. The signed embed URL is minted server-side at
    play time against an active IssuedCourseAccess (see Step 7).
    """
    id: str
    order: int
    title: str
    duration_seconds: int = 0
    is_preview: bool = False


class PublicCourseModule(BaseModel):
    """Module snippet exposed in the public course landing."""
    id: str
    order: int
    title: str
    description: Optional[str] = None
    lessons: List[PublicCourseLesson] = Field(default_factory=list)


class PublicCoursePreview(BaseModel):
    """Full curriculum preview for CourseLandingPage (Release 4 Step 3).

    Structured enough to render an accordion of modules + lesson
    titles/durations on the public landing, while safely excluding
    video GUIDs and any internal metadata.
    """
    title: str
    instructor_name: Optional[str] = None
    instructor_bio: Optional[str] = None
    cover_image_url: Optional[str] = None
    access_policy: str = "lifetime"                       # "lifetime" | "expiring"
    access_expiry_days: Optional[int] = None
    modules: List[PublicCourseModule] = Field(default_factory=list)
    total_lessons: int = 0
    total_duration_seconds: int = 0


class PublicProductLanding(BaseModel):
    """Full payload for a single product landing `/p/:org_slug/:product_slug`.

    Mirror of `PublicEventLanding` but for non-occurrence products
    (primarily services for MVP; extensible to rental/booking/physical).
    Uses `PublicProduct` shape directly since it already carries all
    the type-specific fields (service_options, duration, etc.) needed
    by the landing renderer.
    """
    org_slug: str
    org_name: str
    store_info: Optional[StoreInfo] = None
    product: PublicProduct
    # CH compliance v1: top-level currency so the landing pages can
    # render the price in the org's actual currency without needing to
    # peek into the (sparse) store_info shape. Mirrors CatalogResponse.
    currency: str = "EUR"
    is_buyable: bool = True
    # Release 4 (Courses) — populated only when product.item_type == "course".
    # Contains the full curriculum (modules + lessons) with duration but
    # without bunny_video_guid. For other item_types it is None.
    course_preview: Optional[PublicCoursePreview] = None


@router.get("/products/{org_slug}/{product_slug}", response_model=PublicProductLanding)
async def get_product_landing(org_slug: str, product_slug: str,
    # en|de|fr per contenuti tradotti (default semplice: vedi catalog)
    lang: str = None):
    """Public landing page for a product deep-link.

    Used by the storefront route /p/:org_slug/:product_slug. Returns 404
    when the product isn't found or isn't published/active or the org
    isn't active. No auth required.
    """
    from database import (
        products_collection, stores_collection, organizations_collection,
        service_options_collection, availability_rules_collection,
    )

    # Resolve org via store slug (same pattern as _resolve_org)
    store_doc = await stores_collection.find_one(
        {"slug": org_slug, "is_published": True, "is_active": True, "visibility": "public"},
        {"_id": 0},
    )
    if not store_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagina non trovata")
    org = await organizations_collection.find_one(
        {"id": store_doc["organization_id"], "is_active": {"$ne": False}, "deactivated_at": None},
        {"_id": 0},
    )
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pagina non trovata")

    prod = await products_collection.find_one(
        {"organization_id": org["id"], "slug": product_slug,
         "is_active": True, "is_published": True},
        {"_id": 0},
    )
    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prodotto non trovato")

    # Validate store assignment (like catalog filter): product without
    # store_ids is global, otherwise must include this store.
    store_ids = prod.get("store_ids") or []
    if store_ids and store_doc["id"] not in store_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prodotto non disponibile in questo store")

    # Build PublicProduct (same enrichment pipeline as the catalog)
    meta = prod.get("metadata") or {}
    # Multilingua manuale — merge dei campi tradotti dall'operatore quando
    # la lingua e' offerta; il racconto lungo vive in metadata.
    if lang and lang != "it":
        _tr = (prod.get("translations") or {}).get(lang) or {}
        if _tr.get("description"):
            prod = {**prod, "description": _tr["description"]}
        if _tr.get("long_description"):
            meta = {**meta, "long_description": _tr["long_description"]}
    pp_dict = {
        "id": prod["id"],
        "slug": prod.get("slug"),
        "name": prod.get("name", ""),
        "description": prod.get("description"),
        "image_url": prod.get("image_url"),
        "unit_price": prod.get("unit_price"),
        "category": prod.get("category"),
        "unit": prod.get("unit"),
        "item_type": prod.get("item_type", "physical"),
        "unit_label": prod.get("unit_label"),
        "price_mode": prod.get("price_mode", "fixed"),
        "transaction_mode": prod.get("transaction_mode", "request"),
        "stock_quantity": prod.get("stock_quantity"),
        "duration_label": meta.get("duration_label"),
        "slot_duration_minutes": meta.get("slot_duration_minutes"),
        "rental_unit": meta.get("rental_unit"),
        "requires_attendee_details": bool(meta.get("requires_attendee_details")),
        "require_attendee_email": bool(meta.get("require_attendee_email", True)),
        "require_attendee_phone": bool(meta.get("require_attendee_phone", False)),
        # Defensive sanitization — see get_public_catalog for the rationale.
        "attendee_fields": [
            f for f in (meta.get("attendee_fields") or [])
            if bool((f or {}).get("label") and str(f.get("label")).strip())
        ],
        "order_fields": [
            f for f in (meta.get("order_fields") or [])
            if bool((f or {}).get("label") and str(f.get("label")).strip())
        ],
        "terms_content": resolve_effective_terms_sync(
            product={"metadata": meta}, store=store_doc,
        ),
        "service_options": [],
        "service_duration_minutes": meta.get("duration_minutes"),
        "service_allow_custom_request": bool(meta.get("service_allow_custom_request")),
        "has_availability_slots": False,
        "occurrences": [],
        # Onda 14 — cover image + long description for the landing hero
        "cover_image_url": meta.get("cover_image_url"),
        "long_description": meta.get("long_description"),
        # Onda 16 — Prenotazione consolidation: reservation_flavor + extras.
        # Same population pattern as the catalog endpoint (get_public_catalog,
        # lines ~483-496). Without these the ReservationLandingPage cannot
        # render ProductExtrasPicker nor compute per_day price previews.
        "reservation_flavor": meta.get("reservation_flavor"),
        "extras": [],
    }
    if prod.get("item_type") == "service":
        options_cursor = service_options_collection.find(
            {"organization_id": org["id"], "product_id": prod["id"], "is_active": True},
            {"_id": 0, "id": 1, "label": 1, "description": 1, "price": 1,
             "duration_minutes_override": 1, "sort_order": 1},
        ).sort("sort_order", 1)
        pp_dict["service_options"] = await options_cursor.to_list(200)
        # Onda 15 parity — use_default_schedule counts as "has slots" so the
        # storefront shows the picker even without explicit DB rules (the slot
        # generator synthesizes a 7-day 9-18 grid at fetch time).
        rule_exists = await availability_rules_collection.find_one(
            {"organization_id": org["id"],
             "$or": [{"product_id": prod["id"]}, {"product_id": None}]},
            {"_id": 0, "id": 1},
        )
        pp_dict["has_availability_slots"] = bool(rule_exists) or bool(meta.get("use_default_schedule"))
    elif prod.get("item_type") == "course":
        # Release 4 (Courses) — lightweight counters surfaced everywhere
        # PublicProduct is consumed (catalog card + landing hero). Heavy
        # curriculum structure lives on the landing payload only (below).
        from database import courses_collection as _courses
        course_id = (meta.get("course_id") or (prod.get("metadata") or {}).get("course_id"))
        course_doc = None
        if course_id:
            course_doc = await _courses.find_one(
                {"id": course_id, "organization_id": org["id"], "is_active": True},
                {"_id": 0},
            )
        if course_doc:
            lessons = [l for m in (course_doc.get("modules") or [])
                         for l in (m.get("lessons") or [])]
            pp_dict["course_lessons_count"] = len(lessons)
            pp_dict["course_duration_seconds"] = sum(int(l.get("duration_seconds") or 0) for l in lessons)
            pp_dict["course_access_policy"] = course_doc.get("access_policy") or "lifetime"
            pp_dict["course_access_expiry_days"] = course_doc.get("access_expiry_days")
        # Capture doc for later use when building PublicCoursePreview
        # (see below, after the store_info block — we already have prod/org here).
        prod["_course_doc"] = course_doc
    elif prod.get("item_type") == "rental":
        # Expose active extras for the reservation picker. Fields mirror the
        # catalog endpoint so the frontend contract is identical across entry
        # points. Admin-only fields (created_at, is_active, timestamps) are
        # intentionally stripped.
        from database import product_extras_collection
        extras_cursor = product_extras_collection.find(
            {"organization_id": org["id"], "product_id": prod["id"], "is_active": True},
            {"_id": 0, "id": 1, "kind": 1, "group_key": 1, "label": 1,
             "description": 1, "price": 1, "price_modifier_type": 1,
             "duration_minutes_override": 1, "is_default": 1, "sort_order": 1},
        ).sort("sort_order", 1)
        pp_dict["extras"] = await extras_cursor.to_list(200)
        # Slot flavor also needs availability rules for the hh:mm picker.
        if meta.get("reservation_flavor") == "slot":
            rule_exists = await availability_rules_collection.find_one(
                {"organization_id": org["id"],
                 "$or": [{"product_id": prod["id"]}, {"product_id": None}]},
                {"_id": 0, "id": 1},
            )
            pp_dict["has_availability_slots"] = bool(rule_exists)

    # Store info — reused from catalog endpoint shape
    si = StoreInfo(
        display_name=store_doc.get("name") or store_doc.get("display_name"),
        store_description=store_doc.get("description") or store_doc.get("store_description"),
        contact_email=store_doc.get("contact_email"),
        contact_phone=store_doc.get("contact_phone"),
        logo_url=store_doc.get("logo_url"),
        brand_color=store_doc.get("brand_color"),
        brand_color_text=store_doc.get("brand_color_text"),
        seo_title=store_doc.get("seo_title"),
        seo_description=store_doc.get("seo_description"),
    )
    has_store_info = any([
        si.display_name, si.store_description, si.contact_email, si.contact_phone,
        si.logo_url, si.brand_color, si.brand_color_text, si.seo_title, si.seo_description,
    ])

    # Release 4 (Courses) — build the curriculum preview for course landings.
    # Done out of the elif branch because the PublicProductLanding model
    # carries it as a separate top-level field.
    course_preview = None
    course_doc = prod.pop("_course_doc", None)
    if prod.get("item_type") == "course" and course_doc:
        preview_modules = []
        total_lessons = 0
        total_duration = 0
        for m in (course_doc.get("modules") or []):
            lessons_out = []
            for l in (m.get("lessons") or []):
                lessons_out.append(PublicCourseLesson(
                    id=l.get("id", ""),
                    order=int(l.get("order") or 0),
                    title=l.get("title", ""),
                    duration_seconds=int(l.get("duration_seconds") or 0),
                    is_preview=bool(l.get("is_preview")),
                ))
                total_lessons += 1
                total_duration += int(l.get("duration_seconds") or 0)
            preview_modules.append(PublicCourseModule(
                id=m.get("id", ""),
                order=int(m.get("order") or 0),
                title=m.get("title", ""),
                description=m.get("description"),
                lessons=lessons_out,
            ))
        course_preview = PublicCoursePreview(
            title=course_doc.get("title", ""),
            instructor_name=course_doc.get("instructor_name"),
            instructor_bio=course_doc.get("instructor_bio"),
            cover_image_url=course_doc.get("cover_image_url"),
            access_policy=course_doc.get("access_policy") or "lifetime",
            access_expiry_days=course_doc.get("access_expiry_days"),
            modules=preview_modules,
            total_lessons=total_lessons,
            total_duration_seconds=total_duration,
        )

    from services.currency_service import get_currency_for_product

    return PublicProductLanding(
        org_slug=org_slug,
        org_name=org.get("name", ""),
        store_info=si if has_store_info else None,
        product=PublicProduct(**pp_dict),
        currency=get_currency_for_product(prod, org),
        is_buyable=True,
        course_preview=course_preview,
    )


# ── F5 Onda 12 — Service slot search (public) ─────────────────────────────


class PublicServiceSlot(BaseModel):
    """One available time window for a service product."""
    date: str           # ISO "2026-04-21"
    start_time: str     # HH:MM
    end_time: str       # HH:MM


class PublicServiceSlotsResponse(BaseModel):
    product_id: str
    duration_minutes: int
    slots: List[PublicServiceSlot]


@router.get("/services/{product_id}/slots", response_model=PublicServiceSlotsResponse)
async def get_service_slots(
    product_id: str,
    slug: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=90),
):
    """Return the next N days of available slots for a bookable service.

    Thin wrapper over `slot_generator.generate_available_slots`. Same helper
    is reused by the rental-slot endpoint so the two picker UIs stay in sync.
    """
    from database import products_collection
    from services.slot_generator import generate_available_slots

    prod = await products_collection.find_one(
        {"id": product_id, "is_active": True, "is_published": True,
         "item_type": "service"},
        {"_id": 0, "id": 1, "organization_id": 1, "metadata": 1},
    )
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servizio non trovato",
        )

    default_duration, slots = await generate_available_slots(
        org_id=prod["organization_id"],
        product_id=product_id,
        metadata=prod.get("metadata") or {},
        days=days,
        # Services share the merchant's agenda — a slot booked on another
        # service (or a personal block tagged "agenda") must hide the same
        # window here. Cross-product agenda overlap subtraction.
        scope="agenda",
    )
    return PublicServiceSlotsResponse(
        product_id=product_id,
        duration_minutes=default_duration,
        slots=[PublicServiceSlot(**s) for s in slots],
    )


@router.get("/reservations/{product_id}/slots", response_model=PublicServiceSlotsResponse)
@limiter.limit("30/minute")
async def get_rental_slot_slots(
    request: Request,
    product_id: str,
    days: int = Query(default=30, ge=1, le=90),
):
    """Return the next N days of available slots for a rental product with
    reservation_flavor=slot (e.g. meeting room, sports court).

    Shares the same helper as /public/services/{id}/slots so service and
    rental-slot pickers stay numerically aligned. The endpoint rejects
    products that are not rentals or are range-flavor (wrong picker).
    """
    from database import products_collection
    from services.slot_generator import generate_available_slots

    prod = await products_collection.find_one(
        {"id": product_id, "is_active": True, "is_published": True,
         "item_type": "rental"},
        {"_id": 0, "id": 1, "organization_id": 1, "metadata": 1},
    )
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prodotto non trovato",
        )
    meta = prod.get("metadata") or {}
    if meta.get("reservation_flavor") != "slot":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endpoint riservato ai prodotti rental con flavor=slot",
        )

    default_duration, slots = await generate_available_slots(
        org_id=prod["organization_id"],
        product_id=product_id,
        metadata=meta,
        days=days,
        # Rental+slot products share the rentals tab of the admin calendar;
        # a block on another rental slot product must hide the same window.
        scope="rentals",
    )
    return PublicServiceSlotsResponse(
        product_id=product_id,
        duration_minutes=default_duration,
        slots=[PublicServiceSlot(**s) for s in slots],
    )


# ── Onda 17: rental+slot availability windows (variable duration, cross-day) ──

class PublicAvailabilityWindow(BaseModel):
    start: str  # HH:MM
    end: str    # HH:MM


class PublicAvailabilityDay(BaseModel):
    date: str   # YYYY-MM-DD
    windows: List[PublicAvailabilityWindow]


class PublicAvailabilityWindowsResponse(BaseModel):
    product_id: str
    min_duration_minutes: int
    step_minutes: int
    max_duration_minutes: Optional[int] = None
    default_duration_minutes: int
    days: List[PublicAvailabilityDay]


@router.get(
    "/reservations/{product_id}/availability-windows",
    response_model=PublicAvailabilityWindowsResponse,
)
@limiter.limit("30/minute")
async def get_rental_slot_availability_windows(
    request: Request,
    product_id: str,
    days: int = Query(default=30, ge=1, le=90),
):
    """Return continuous availability windows for a rental+flavor=slot product.

    Unlike `/reservations/{id}/slots` (which emits a discrete fixed-duration
    grid), this endpoint returns the free `[start, end)` windows remaining per
    day after subtracting blocked_slots. The customer UI then picks any
    `[start, end]` inside these windows subject to `min/step/max_duration`.

    Zero impact on the legacy `/slots` endpoint: both coexist, Service and
    legacy rental+slot products continue using `/slots` unchanged.
    """
    from database import products_collection
    from services.slot_generator import generate_availability_windows

    prod = await products_collection.find_one(
        {"id": product_id, "is_active": True, "is_published": True,
         "item_type": "rental"},
        {"_id": 0, "id": 1, "organization_id": 1, "metadata": 1},
    )
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prodotto non trovato",
        )
    meta = prod.get("metadata") or {}
    if meta.get("reservation_flavor") != "slot":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endpoint riservato ai prodotti rental con flavor=slot",
        )

    config, windows_by_day = await generate_availability_windows(
        org_id=prod["organization_id"],
        product_id=product_id,
        metadata=meta,
        days=days,
    )
    return PublicAvailabilityWindowsResponse(
        product_id=product_id,
        min_duration_minutes=config["min_duration_minutes"],
        step_minutes=config["step_minutes"],
        max_duration_minutes=config["max_duration_minutes"],
        default_duration_minutes=config["default_duration_minutes"],
        days=[
            PublicAvailabilityDay(
                date=d["date"],
                windows=[PublicAvailabilityWindow(**w) for w in d["windows"]],
            )
            for d in windows_by_day
        ],
    )


@router.post("/order-request", response_model=OrderRequestResponse)
@limiter.limit("30/minute")
async def submit_order_request(request: Request, response: Response, body: OrderRequestPayload):
    """Submit a public order request. Creates customer + draft order.

    No auth required, but if a valid customer Bearer token is present,
    the order is linked to the customer account (guest vs registered semantics).

    Phase 0 Step 3 (2026-05-28) — questa funzione è un thin adapter sopra
    ``services.order_creation_service.submit_order_from_storefront``. Tutta
    la logica (validation, GDPR, order creation, Stripe checkout, emails,
    response messages) vive nel service, riusato dall'embed e da future
    surface (AI site builder, POS).

    R10 (2026-06-19) — il legacy inline path e il flag
    ``USE_ORDER_CREATION_SERVICE`` sono stati rimossi: il service è l'unico
    path, eliminando il principale punto di drift storefront↔embed.
    """
    org = await _resolve_org(body.slug)
    org_id = org["id"]

    # ── Optional customer identity from Bearer token (v9.1 org-scoped) ──
    customer_account_id = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from auth import decode_token
            payload = decode_token(auth_header[7:])
            if payload.get("type") == "customer":
                # Only accept customer token if it belongs to THIS org
                if payload.get("org_id") == org_id:
                    customer_account_id = payload.get("sub")
                # else: token for different org — treat as guest (no error)
        except Exception:
            pass  # Guest flow — ignore invalid/expired token silently

    # Find or create customer by email (INV-1: atomic upsert via repository)
    customer_id = await _find_or_create_customer(
        org_id, body.customer_name, body.customer_email, body.customer_phone,
        customer_account_id=customer_account_id,
    )

    # ── Phase 0 Step 3 — delegate to order_creation_service ────────────
    # Tutta la logica (validation, GDPR, order creation, Stripe checkout,
    # emails, response messages) vive nel service, condiviso con l'embed.
    from services.order_creation_service import submit_order_from_storefront

    # ── Phase 0 Step 5 — cart_id from cookie ────────────────────────────
    # Cookie ``afianco_cart_id`` letto dal browser e passato al service: se
    # presente e l'order è creato con successo, il service marca il cart come
    # converted (link cart→order per analytics + abandon-recovery exclusion).
    #
    # R10 (2026-06-19) — rimosso il dual-path + flag USE_ORDER_CREATION_SERVICE:
    # ``order_creation_service`` è ora l'UNICO path (legacy inline eliminato),
    # così storefront ed embed condividono la stessa pipeline senza drift.
    from services.cart_service import CART_COOKIE_NAME, LEGACY_CART_COOKIE_NAME
    cart_id_cookie = (request.cookies.get(CART_COOKIE_NAME)
                      or request.cookies.get(LEGACY_CART_COOKIE_NAME))

    result = await submit_order_from_storefront(
        org=org,
        body=body,
        customer_account_id=customer_account_id,
        customer_id=customer_id,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        cart_id=cart_id_cookie,
    )

    # Phase 0 Step 5 — clear cart cookie post-checkout success (solo se
    # l'order è effettivamente creato + cart_id era presente).
    if result.get("cart_converted") and cart_id_cookie:
        from services.cart_service import clear_cart_cookie
        clear_cart_cookie(response)

    return OrderRequestResponse(
        message=result["message"],
        order_id=result["order_id"],
        transaction_mode=result["transaction_mode"],
        order_status=result["order_status"],
        payment_checkout_url=result.get("payment_checkout_url"),
        payment_reason=result.get("payment_reason"),
    )


# ── Public Availability Slots (v12.0) ──────────────────────────────────────

@router.get("/availability/{slug}")
@limiter.limit("30/minute")
async def get_public_availability(
    request: Request,
    slug: str,
    date_from: str = Query(...),
    date_to: str = Query(...),
    duration: int = Query(None, ge=15, le=480),
    product_id: Optional[str] = Query(None),
):
    """Public endpoint: get available booking slots for a store.

    No auth required. Used by storefront for booking products.
    Optional `duration` param overrides rule's slot_duration_minutes
    (used when a booking product has a specific service duration).
    """
    from datetime import date as date_type, timedelta
    from database import availability_rules_collection, blocked_slots_collection, stores_collection

    # Resolve store
    store = await stores_collection.find_one(
        {"slug": slug, "is_published": True, "is_active": True},
        {"_id": 0, "id": 1, "organization_id": 1},
    )
    if not store:
        # Fallback: try org slug
        org = await _resolve_org(slug)
        org_id = org["id"]
        store_id = org.get("_store", {}).get("id")
    else:
        org_id = store["organization_id"]
        store_id = store["id"]

    try:
        start = date_type.fromisoformat(date_from)
        end = date_type.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    if (end - start).days > 30:
        raise HTTPException(status_code=400, detail="Max 30 days range")

    # Load rules
    rule_query = {"organization_id": org_id, "is_active": True}
    if store_id:
        rule_query["$or"] = [{"store_id": store_id}, {"store_id": None}]
    rules = await availability_rules_collection.find(rule_query, {"_id": 0}).to_list(100)

    rules_by_day = {}
    for r in rules:
        rules_by_day.setdefault(r["day_of_week"], []).append(r)

    # Load blocked slots (per-product + global)
    block_query = {"organization_id": org_id, "date": {"$gte": date_from, "$lte": date_to}}
    if product_id:
        block_query["$or"] = [{"product_id": product_id}, {"product_id": None}, {"product_id": {"$exists": False}}]
    elif store_id:
        block_query["$or"] = [{"store_id": store_id}, {"store_id": None}]
    blocks = await blocked_slots_collection.find(block_query, {"_id": 0}).to_list(1000)

    blocks_by_date = {}
    for b in blocks:
        blocks_by_date.setdefault(b["date"], []).append(b)

    # Compute
    from routers.availability import _generate_slots_from_rule, _is_slot_blocked, DAY_NAMES

    result = []
    current = start
    while current <= end:
        day_str = current.isoformat()
        dow = current.weekday()
        day_rules = rules_by_day.get(dow, [])
        if not day_rules:
            current += timedelta(days=1)
            continue

        all_slots = []
        for rule in day_rules:
            if duration:
                # Override rule duration with product-specific duration
                rule_copy = {**rule, "slot_duration_minutes": duration}
                all_slots.extend(_generate_slots_from_rule(rule_copy))
            else:
                all_slots.extend(_generate_slots_from_rule(rule))

        day_blocks = blocks_by_date.get(day_str, [])
        free_slots = [s for s in all_slots if not _is_slot_blocked(s["start"], s["end"], day_blocks)]

        result.append({"date": day_str, "day_name": DAY_NAMES[dow], "slots": free_slots})

        current += timedelta(days=1)

    return {"available": result}


# ── Public Order Status (Fase 2 — Stripe checkout redirect UX) ─────────────

@router.get("/orders/{order_id}/status", response_model=PublicOrderStatus)
@limiter.limit("60/minute")
async def get_public_order_status(request: Request, order_id: str):
    """Public-safe snapshot of an order's status.

    Used by the Stripe checkout success/cancel pages to:
      - Display the human-readable order number + amount to the customer
      - Poll for webhook-driven state transitions (payment_intent: required → collected)
      - Offer a "back to store" link via store_slug

    Auth: none. Security: order_id is a UUID; exposed fields are minimal and
    non-sensitive (no customer PII, no line items, no internal state).
    Rate-limited to accommodate polling from the redirect page (60/min/IP).
    """
    from database import orders_collection, stores_collection

    order = await orders_collection.find_one(
        {"id": order_id},
        {
            "_id": 0,
            "id": 1,
            "order_number": 1,
            "status": 1,
            "payment_intent": 1,
            "total": 1,
            "currency": 1,
            "store_id": 1,
        },
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    store_slug: Optional[str] = None
    store_name: Optional[str] = None
    if order.get("store_id"):
        store = await stores_collection.find_one(
            {"id": order["store_id"], "is_active": True},
            {"_id": 0, "slug": 1, "name": 1, "is_published": 1},
        )
        # Only expose slug if store is published (otherwise link wouldn't resolve)
        if store and store.get("is_published"):
            store_slug = store.get("slug")
        if store:
            store_name = store.get("name")

    from services.currency_service import get_currency_for_order

    return PublicOrderStatus(
        order_id=order["id"],
        order_number=order.get("order_number"),
        order_status=order.get("status", "draft"),
        payment_intent=order.get("payment_intent", "none"),
        total=float(order.get("total", 0) or 0),
        currency=get_currency_for_order(order),
        store_slug=store_slug,
        store_name=store_name,
    )


# ── Onda 16 — Public price preview (anonymous customers on the landing) ────

class _PublicPricePreviewRequest(BaseModel):
    """Mirrors the admin price-preview body in routers/orders.py, but usable
    without authentication so the public reservation landing can show a live
    total to anonymous visitors.

    R9 — ``slug`` è ORA richiesto: il preview è scoping-ato all'org dello store
    (parità col wrapper embed). Prima il prodotto era risolto per solo id →
    enumerazione cross-tenant (id ⇒ prezzo/nome di QUALSIASI org pubblicata).
    """
    slug: str
    product_id: str
    quantity: float = 1
    discount_pct: float = 0
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    extra_selections: Optional[dict] = None
    # Onda 17 — slot flavor with variable duration + cross-day support. When
    # populated on a rental+flavor=slot product, pricing becomes hourly.
    slot_date_from: Optional[str] = None
    slot_time_from: Optional[str] = None
    slot_date_to: Optional[str] = None
    slot_time_to: Optional[str] = None


@router.post("/price-preview")
@limiter.limit("60/minute")
async def public_price_preview(request: Request, body: _PublicPricePreviewRequest):
    """Stateless price preview for the public reservation landing.

    Resolves the product by id, enforces that it is active+published (so this
    endpoint never leaks draft products), fetches its active extras, and
    delegates to compute_line_total — same shape as the admin endpoint.

    Rate-limited and read-only; no order is created.
    """
    from database import products_collection, product_extras_collection
    from services.pricing import compute_line_total, compute_rental_multiplier, PricingError

    # R9 — risolvi l'org dallo slug e vincola il prodotto a quell'org
    # (no enumerazione cross-tenant per product_id). Parità col wrapper embed.
    org = await _resolve_org(body.slug)
    org_id = org["id"]

    product = await products_collection.find_one(
        {"id": body.product_id, "organization_id": org_id,
         "is_active": True, "is_published": True},
        {"_id": 0, "unit_price": 1, "item_type": 1, "name": 1,
         "organization_id": 1, "metadata": 1},
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prodotto non trovato")

    extras_catalog = await product_extras_collection.find(
        {"organization_id": product["organization_id"],
         "product_id": body.product_id, "is_active": True},
        {"_id": 0},
    ).to_list(200)

    # Rental multiplier parity with the admin preview + order_service.create_order.
    # Pre-inflates `quantity` so `base` reflects the full rental span (e.g. 4 nights
    # × €90) rather than a single unit.
    rental_multiplier = compute_rental_multiplier(
        item_type=product.get("item_type"),
        metadata=product.get("metadata") or {},
        date_from=body.date_from,
        date_to=body.date_to,
        slot_date_from=body.slot_date_from,
        slot_time_from=body.slot_time_from,
        slot_date_to=body.slot_date_to,
        slot_time_to=body.slot_time_to,
    )

    try:
        result = compute_line_total(
            unit_price=float(product.get("unit_price") or 0),
            quantity=float(body.quantity or 0) * rental_multiplier,
            discount_pct=body.discount_pct,
            extras_catalog=extras_catalog,
            extras_selection=body.extra_selections,
            date_from=body.date_from,
            date_to=body.date_to,
        )
    except PricingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.detail, "context": e.context},
        )
    return result.to_dict()


# ╔══════════════════════════════════════════════════════════════════════╗
# ║ Phase 0 Step 4 (2026-05-28) — Persistent server-side cart endpoints ║
# ╠══════════════════════════════════════════════════════════════════════╣
# ║ 5 endpoint per gestione cart server-side (cookie afianco_cart_id).   ║
# ║ Feature flag PERSISTENT_CART_ENABLED (default OFF) gate l'attivazione║
# ║ a livello frontend. Gli endpoint sono sempre disponibili — il flag   ║
# ║ governa se il frontend storefront li USA o resta su sessionStorage.  ║
# ║                                                                       ║
# ║ Invarianti pinnate da tests/test_invariants_cart.py:                 ║
# ║   INV-CART-1  Atomic operations via find_one_and_update              ║
# ║   INV-CART-2  Multi-tenant isolation (organization_id)               ║
# ║   INV-CART-3  expires_at sempre nel futuro per cart attivi           ║
# ║   INV-CART-4  Items shape compatibile con OrderRequestItem           ║
# ║   CTR-CART-1  CartResponse shape stable                              ║
# ╚══════════════════════════════════════════════════════════════════════╝


# Cart model imports — module-level so all 5 endpoints can use the classes
# as response_model directly. Models live in a separate package so no
# circular import risk.
from models.cart import (  # noqa: E402 — intentional below-line import
    CartCreate as _CartCreate,
    CartUpdate as _CartUpdate,
    CartMergeRequest as _CartMergeRequest,
    CartResponse as _CartResponse,
)


@router.post("/cart", response_model=_CartResponse)
@limiter.limit("30/minute")
async def create_cart(request: Request, response: Response, body: _CartCreate):
    """Create a new empty cart bound to a store.

    Body: ``{"slug": "<store-slug>", "source": "storefront_classic"}``

    Sets the ``afianco_cart_id`` cookie (HttpOnly, SameSite=Lax, 60gg TTL).
    Returns the cart in canonical CartResponse shape.
    """
    from services import cart_service

    org = await _resolve_org(body.slug)
    org_id = org["id"]
    store_id = (org.get("_store") or {}).get("id")

    cart = await cart_service.create_empty_cart(
        organization_id=org_id,
        store_id=store_id,
        source=body.source,
    )

    cart_service.set_cart_cookie(response, cart.id)

    # Read back full doc with materialized timestamps for response
    cart_doc = await cart_service.get_cart(cart.id, org_id)
    return cart_service.build_response(cart_doc)


@router.get("/cart/{cart_id}", response_model=_CartResponse)
@limiter.limit("60/minute")
async def get_cart_by_id(request: Request, cart_id: str, slug: str = Query(...)):
    """Read cart by id within a store's org context.

    Query param ``slug`` identifies the store (and thus the
    organization_id used for multi-tenant scoping INV-CART-2).
    """
    from services import cart_service

    org = await _resolve_org(slug)
    cart_doc = await cart_service.get_cart(cart_id, org["id"])
    if not cart_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart non trovato o scaduto.",
        )
    return cart_service.build_response(cart_doc)


@router.patch("/cart/{cart_id}", response_model=_CartResponse)
@limiter.limit("30/minute")
async def update_cart(
    request: Request,
    cart_id: str,
    body: _CartUpdate,
    slug: str = Query(...),
):
    """Update cart items + optionally bind customer_email.

    Items list semantics:
      - quantity=0 in input → remove that product line
      - missing product → kept as-is (only listed products replace)

    Pricing snapshot fields are populated server-side from current product
    state (best-effort; never authoritative for checkout pricing).
    """
    from services import cart_service

    org = await _resolve_org(slug)
    org_id = org["id"]

    # Verify cart exists + belongs to this org (INV-CART-2)
    existing = await cart_service.get_cart(cart_id, org_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart non trovato o scaduto.",
        )

    updated_doc = existing

    if body.items is not None:
        # Track E Step 1.2 — coerent inventory check (same as embed flow).
        # InsufficientStockError → HTTP 409 con detail strutturato.
        from core.inventory_check import InsufficientStockError
        try:
            updated_doc = await cart_service.update_cart_items(
                cart_id=cart_id,
                organization_id=org_id,
                items_input=body.items,
            )
        except InsufficientStockError as stock_err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=stock_err.to_detail(),
            )

    if body.customer_email:
        # Use cart name/phone fallback if available from existing snapshot
        updated_doc = await cart_service.bind_customer_email(
            cart_id=cart_id,
            organization_id=org_id,
            customer_email=body.customer_email,
            customer_name=None,
            customer_phone=None,
        )

    return cart_service.build_response(updated_doc or existing)


@router.post("/cart/{cart_id}/merge", response_model=_CartResponse)
@limiter.limit("10/minute")
async def merge_cart_to_account(
    request: Request,
    cart_id: str,
    body: _CartMergeRequest,
    slug: str = Query(...),
):
    """Bind an anonymous cart to a logged-in customer account.

    Use case: guest with cart logs into customer portal mid-cart. The
    cart_id cookie is retained on the browser, but server-side we now
    associate it with the customer's account for cross-device retrieval.

    Verifies via Bearer token that ``customer_account_id`` matches the
    authenticated session — server doesn't trust the body alone.
    """
    from services import cart_service

    org = await _resolve_org(slug)
    org_id = org["id"]

    # Verify the Bearer token matches the requested account.
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token customer richiesto per merge cart.",
        )
    try:
        from auth import decode_token
        payload = decode_token(auth_header[7:])
        if payload.get("type") != "customer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token customer richiesto.",
            )
        if payload.get("org_id") != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token customer per organizzazione diversa.",
            )
        if payload.get("sub") != body.customer_account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token customer non corrisponde all'account richiesto.",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token customer invalido o scaduto.",
        )

    updated = await cart_service.merge_anonymous_to_account(
        cart_id=cart_id,
        organization_id=org_id,
        customer_account_id=body.customer_account_id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart non trovato.",
        )
    return cart_service.build_response(updated)


@router.delete("/cart/{cart_id}")
@limiter.limit("30/minute")
async def clear_or_delete_cart(
    request: Request,
    response: Response,
    cart_id: str,
    slug: str = Query(...),
    hard: bool = Query(False, description="True = hard delete; False = clear items only"),
):
    """Clear cart items (default) or hard-delete cart entirely.

    Hard delete removes the document + clears the cookie (so the next
    storefront load gets a fresh cart). Soft clear keeps the cart_id
    alive — utile per "svuota e ricomincia" UX.
    """
    from services import cart_service

    org = await _resolve_org(slug)
    org_id = org["id"]

    if hard:
        from repositories import cart_repository
        ok = await cart_repository.delete_by_id(cart_id, org_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart non trovato.",
            )
        cart_service.clear_cart_cookie(response)
        return {"deleted": True, "cart_id": cart_id}

    # Soft: clear items only
    updated = await cart_service.clear_cart(cart_id, org_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart non trovato.",
        )
    return cart_service.build_response(updated)


# ── Fase 2 S3 (retreat) — link eterno paga-adesso ────────────────────────────

@router.get("/pay/{token}")
async def pay_by_token(token: str):
    """Il link che viaggia nelle email di promemoria: /pay/{token}.

    Al click genera la Checkout Session FRESCA per la riga (saldo/rata) e
    reindirizza — così il link non scade mai, mentre le session Stripe
    durano 24h. Token per-riga, non enumerabile (uuid4), risolto contro
    payment_schedules. Risposte:
      · riga pagabile  → 303 verso Stripe Checkout
      · riga già pagata → 303 verso la pagina di successo dello storefront
      · token ignoto / ordine mancante → 404 secco (nessun oracle)
    """
    from fastapi.responses import RedirectResponse
    from database import orders_collection
    from services.payment_schedule_service import (
        PAYABLE_STATES, find_schedule_by_pay_token,
    )
    from services.payment_checkout_service import create_row_checkout_session
    from services.url_builder import build_public_url

    resolved = await find_schedule_by_pay_token(token)
    if not resolved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link non valido")
    schedule_doc, row = resolved

    order = await orders_collection.find_one(
        {"id": schedule_doc["order_id"],
         "organization_id": schedule_doc["organization_id"]},
        {"_id": 0},
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link non valido")

    if row.get("status") in ("paid", "paid_manual", "refunded", "waived", "cancelled"):
        return RedirectResponse(
            build_public_url(f"/s/checkout-success?order_id={order['id']}&already_paid=1"),
            status_code=303,
        )
    if row.get("status") not in PAYABLE_STATES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link non valido")

    session = await create_row_checkout_session(
        schedule_doc["organization_id"], order, schedule_doc, row)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pagamento momentaneamente non disponibile. Riprova tra poco.",
        )
    return RedirectResponse(session["url"], status_code=303)


# ── Fase 5 (retreat) — calendario pubblico cross-organizzatore ───────────────

@router.get("/retreats")
async def list_public_retreats(
    category: Optional[str] = Query(default=None, max_length=30),
    region: Optional[str] = Query(default=None, max_length=30),
    # G1 — ricerca per raggio (docs/GEO_SEARCH_PLAN.md): lat+lng+radius_km
    # attivano il filtro geografico; country raggruppa/filtra per paese.
    lat: Optional[float] = Query(default=None, ge=-90, le=90),
    lng: Optional[float] = Query(default=None, ge=-180, le=180),
    radius_km: int = Query(default=100, ge=1, le=3000),
    country: Optional[str] = Query(default=None, min_length=2, max_length=2),
    month: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    price_max: Optional[int] = Query(default=None, ge=0, le=100000),
    limit: int = Query(default=60, ge=1, le=120),
    offset: int = Query(default=0, ge=0),
    lang: str = None,  # en|de|fr: solo i ritiri offerti in quella lingua (default semplice: vedi catalog)
):
    """IL calendario dei ritiri: occurrence pubblicate e future di TUTTE
    le organizzazioni, filtrabili per categoria (tassonomia), regione,
    mese (YYYY-MM) e prezzo massimo (EUR). Card pronte per la griglia
    /ritiri: titolo, date, luogo, prezzo-da, posti rimasti, link landing.

    Vende solo ciò che è vendibile: prodotto attivo+pubblicato, org con
    storefront pubblico raggiungibile (store slug o public_slug legacy).
    """
    from datetime import datetime, timezone
    from database import (
        event_occurrences_collection,
        organizations_collection,
        products_collection,
        stores_collection,
    )
    from models.retreat_taxonomy import RETREAT_CATEGORIES

    now_iso = datetime.now(timezone.utc).isoformat()

    occ_query: Dict[str, Any] = {
        "status": "published",
        "start_at": {"$gte": now_iso[:16]},   # future (ISO confronta bene)
    }
    if region:
        occ_query["region"] = region
    if country:
        occ_query["country"] = country.upper()
    _geo_active = lat is not None and lng is not None
    if _geo_active:
        # $centerSphere vuole il raggio in RADIANTI (raggio terrestre ~6371km)
        occ_query["geo"] = {"$geoWithin": {
            "$centerSphere": [[lng, lat], radius_km / 6371.0]}}
    if month:
        # start_at ISO: il prefisso YYYY-MM seleziona il mese
        occ_query["start_at"] = {"$gte": max(now_iso[:16], month + "-01"),
                                 "$lt": _next_month(month)}

    cursor = event_occurrences_collection.find(
        occ_query, {"_id": 0},
    ).sort("start_at", 1).limit(500)
    occs = await cursor.to_list(500)
    if not occs:
        return {"items": [], "total": 0, "categories": RETREAT_CATEGORIES}

    # prodotti (categoria + prezzo + nome) — solo vendibili
    product_ids = list({o["product_id"] for o in occs})
    prods = await products_collection.find(
        {"id": {"$in": product_ids}, "is_active": True, "is_published": True,
         "item_type": "event_ticket",
         **({"category": category} if category else {})},
        {"_id": 0, "id": 1, "name": 1, "category": 1, "unit_price": 1,
         "image_url": 1, "organization_id": 1, "metadata.payment_plan": 1,
         "translations": 1},
    ).to_list(1000)

    # Multilingua manuale (6/7) — vista in lingua X: SOLO i ritiri che
    # l'operatore offre in X (traduzione manuale presente). IT = tutti.
    if lang and lang != "it":
        from services.manual_translations import is_available_in, merge_language
        prods = [merge_language(p, lang) for p in prods if is_available_in(p, lang)]

    prod_by_id = {p["id"]: p for p in prods}

    # org slug pubblici (store multi-store o legacy public_slug)
    org_ids = list({p["organization_id"] for p in prods})
    org_slug: Dict[str, str] = {}
    org_name: Dict[str, str] = {}
    stores = await stores_collection.find(
        {"organization_id": {"$in": org_ids}, "is_published": True,
         "is_active": True, "visibility": "public"},
        {"_id": 0, "organization_id": 1, "slug": 1},
    ).to_list(1000)
    for s in stores:
        org_slug.setdefault(s["organization_id"], s["slug"])
    orgs = await organizations_collection.find(
        {"id": {"$in": org_ids}, "is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "name": 1, "public_slug": 1,
         "directory_featured": 1,
         "store_settings.is_storefront_published": 1,
         "store_settings.display_name": 1},
    ).to_list(1000)
    org_featured: Dict[str, bool] = {}
    for o in orgs:
        org_name[o["id"]] = (o.get("store_settings") or {}).get("display_name") or o.get("name") or ""
        org_featured[o["id"]] = bool(o.get("directory_featured"))
        if o["id"] not in org_slug and o.get("public_slug") and \
                (o.get("store_settings") or {}).get("is_storefront_published"):
            org_slug[o["id"]] = o["public_slug"]

    items = []
    for occ in occs:
        prod = prod_by_id.get(occ["product_id"])
        if not prod:
            continue
        slug_org = org_slug.get(prod["organization_id"])
        if not slug_org or not occ.get("slug"):
            continue   # senza landing raggiungibile non si lista
        price_from = occ.get("price_override") or prod.get("unit_price")
        if price_max is not None and price_from is not None and price_from > price_max:
            continue
        cap = occ.get("capacity")
        reserved = occ.get("reserved_seats") or 0
        distance_km = None
        if _geo_active and occ.get("latitude") is not None \
                and occ.get("longitude") is not None:
            distance_km = round(_haversine_km(
                lat, lng, occ["latitude"], occ["longitude"]), 1)
        items.append({
            "distance_km": distance_km,
            "country": occ.get("country"),
            "latitude": occ.get("latitude"),
            "longitude": occ.get("longitude"),
            "title": prod.get("name"),
            "category": prod.get("category"),
            "org_name": org_name.get(prod["organization_id"], ""),
            "org_slug": slug_org,
            # MD3 — promessa Pro resa vera: badge + boost nel calendario
            "featured": org_featured.get(prod["organization_id"], False),
            "slug": occ["slug"],
            "url": f"/e/{slug_org}/{occ['slug']}",
            "start_at": occ.get("start_at"),
            "end_at": occ.get("end_at"),
            "city": occ.get("city"),
            "region": occ.get("region"),
            "venue_name": occ.get("venue_name"),
            "cover_image_url": occ.get("cover_image_url") or prod.get("image_url"),
            "price_from": price_from,
            "remaining": (cap - reserved) if cap else None,
            "deposit_mode": bool(((prod.get("metadata") or {}).get("payment_plan")
                                  or {}).get("mode", "full") != "full"),
        })

    # MD3 — boost "In evidenza": il calendario resta cronologico
    # (un calendario che non rispetta le date tradisce il visitatore),
    # ma A PARITÀ DI GIORNO i ritiri dei piani featured vengono prima.
    items.sort(key=lambda i: ((i["start_at"] or "")[:10],
                              not i.get("featured"),
                              i["start_at"] or ""))

    # con una posizione attiva: i piu' vicini prima (featured a parità)
    if _geo_active:
        items.sort(key=lambda i: (i["distance_km"] is None,
                                  i["distance_km"] or 0,
                                  not i.get("featured"),
                                  i["start_at"] or ""))

    total = len(items)
    return {
        "items": items[offset:offset + limit],
        "total": total,
        "categories": RETREAT_CATEGORIES,
    }


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distanza great-circle in km. Pura, testabile."""
    import math
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = rlat2 - rlat1
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) \
        * math.sin(dlng / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def _next_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    return f"{y + (1 if m == 12 else 0)}-{(1 if m == 12 else m + 1):02d}-01"


@router.get("/geo/search")
@limiter.limit("20/minute")
async def public_geo_search(request: Request,
    q: str = Query(min_length=2, max_length=120)):
    """Autocomplete localita' per la barra "Dove?" della directory.
    Nominatim con cache aggressiva + rate limit: gratis e sostenibile."""
    from services.geocoding import search_places
    return {"results": await search_places(q, limit=5)}


async def _resolve_public_slug_for_org(org_id: str):
    """Slug pubblico dell'org (store pubblicato → slug; fallback
    public_slug legacy). None se l'org non ha superficie pubblica."""
    from database import stores_collection, organizations_collection
    store = await stores_collection.find_one(
        {"organization_id": org_id, "is_published": True,
         "is_active": True, "visibility": "public",
         "slug": {"$nin": [None, ""]}},
        {"_id": 0, "slug": 1},
    )
    if store:
        return store["slug"]
    org = await organizations_collection.find_one(
        {"id": org_id, "public_slug": {"$nin": [None, ""]}},
        {"_id": 0, "public_slug": 1},
    )
    return (org or {}).get("public_slug")


def _place_slug(name: str) -> str:
    """Slug URL-safe per i nomi luogo ('Greve in Chianti' → greve-in-chianti)."""
    import re as _re
    import unicodedata as _ud
    s = _ud.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    return _re.sub(r"[^a-z0-9]+", "-", s).strip("-")


@router.get("/destinations")
async def public_destinations_index():
    """S2b (SEO_MASTER_PLAN) — destinazioni con ritiri REALI in futuro.

    Le pagine /destinazioni/{luogo} esistono SOLO se c'è contenuto
    (anti thin-content): questa lista è la fonte, derivata dalle
    occorrenze future pubblicate (region + city)."""
    from datetime import datetime, timezone
    from database import event_occurrences_collection

    now_iso = datetime.now(timezone.utc).isoformat()[:16]
    occs = await event_occurrences_collection.find(
        {"status": "published", "start_at": {"$gte": now_iso}},
        {"_id": 0, "region": 1, "city": 1},
    ).to_list(2000)

    counts: dict = {}
    for o in occs:
        for name in {o.get("region"), o.get("city")}:
            if not name:
                continue
            k = _place_slug(name)
            if not k:
                continue
            e = counts.setdefault(k, {"slug": k, "label": name, "retreats": 0})
            e["retreats"] += 1
    items = sorted(counts.values(), key=lambda x: (-x["retreats"], x["label"]))
    return {"items": items, "total": len(items)}


_EXPERIENCE_TYPES = ("service", "rental", "course")
_EXPERIENCE_PREFIX = {"service": "p", "rental": "r", "course": "co"}


@router.get("/experiences")
async def public_experiences_index(category: str = Query(default=None, max_length=50)):
    """S2b — hub delle esperienze NON-evento (servizi, prenotazioni,
    corsi) degli operatori con vetrina pubblica. I fisici/digitali
    restano indicizzati a livello di landing e store (scelta commerce
    del piano: niente aggregatore retail cross-store)."""
    from database import stores_collection, products_collection

    stores = await stores_collection.find(
        {"is_published": True, "is_active": True, "visibility": "public",
         "slug": {"$nin": [None, ""]}},
        {"_id": 0, "organization_id": 1, "slug": 1, "name": 1},
    ).to_list(500)
    slug_by_org = {s["organization_id"]: s["slug"] for s in stores}
    name_by_org = {s["organization_id"]: s.get("name") or s["slug"]
                   for s in stores}

    q = {"organization_id": {"$in": list(slug_by_org)},
         "is_active": True, "is_published": True,
         "item_type": {"$in": list(_EXPERIENCE_TYPES)},
         "slug": {"$nin": [None, ""]}}
    prods = await products_collection.find(
        q, {"_id": 0, "name": 1, "slug": 1, "description": 1, "images": 1,
            "image_url": 1, "unit_price": 1, "category": 1, "item_type": 1,
            "organization_id": 1},
    ).to_list(1000)

    items = []
    all_categories: dict = {}
    for p in prods:
        org_slug = slug_by_org.get(p["organization_id"])
        if not org_slug:
            continue
        if p.get("category"):
            all_categories[p["category"]] = all_categories.get(p["category"], 0) + 1
        if category and p.get("category") != category:
            continue
        prefix = _EXPERIENCE_PREFIX[p["item_type"]]
        items.append({
            "title": p["name"],
            "url": f"/{prefix}/{org_slug}/{p['slug']}",
            "item_type": p["item_type"],
            "category": p.get("category"),
            "description": (p.get("description") or "")[:160] or None,
            "image": (p.get("images") or [None])[0] or p.get("image_url"),
            "price_from": p.get("unit_price"),
            "operator": name_by_org.get(p["organization_id"]),
        })
    items.sort(key=lambda x: x["title"].lower())
    return {"items": items, "total": len(items), "categories": all_categories}


@router.get("/operators")
async def public_operators_index(category: str = Query(default=None, max_length=50)):
    """S2 (SEO_MASTER_PLAN) — aggregatore pubblico degli operatori.

    Elenca le organizzazioni con vetrina pubblica: identita', categorie
    REALI (derivate dai prodotti attivi) e conteggi. Alimenta /operatori
    e /operatori/{categoria}; le categorie tornano anche in aggregato
    cosi' il frontend mostra solo filtri con contenuto (anti thin-content).
    """
    from datetime import datetime, timezone
    from database import (stores_collection, organizations_collection,
                          products_collection, event_occurrences_collection)

    stores = await stores_collection.find(
        {"is_published": True, "is_active": True, "visibility": "public",
         "slug": {"$nin": [None, ""]}},
        {"_id": 0, "organization_id": 1, "slug": 1, "name": 1,
         "description": 1, "logo_url": 1},
    ).to_list(500)
    org_ids = [s["organization_id"] for s in stores]
    orgs = {o["id"]: o for o in await organizations_collection.find(
        {"id": {"$in": org_ids}, "is_active": {"$ne": False},
         "deactivated_at": None},
        {"_id": 0, "id": 1, "name": 1, "public_profile": 1,
         "store_settings": 1},
    ).to_list(500)}

    prods = await products_collection.find(
        {"organization_id": {"$in": org_ids}, "is_active": True,
         "is_published": True},
        {"_id": 0, "id": 1, "organization_id": 1, "category": 1,
         "item_type": 1},
    ).to_list(2000)

    now_iso = datetime.now(timezone.utc).isoformat()[:16]
    occs = await event_occurrences_collection.find(
        {"organization_id": {"$in": org_ids}, "status": "published",
         "start_at": {"$gte": now_iso}},
        {"_id": 0, "organization_id": 1, "region": 1, "product_id": 1},
    ).to_list(2000)

    by_org: dict = {}
    for p in prods:
        b = by_org.setdefault(p["organization_id"],
                              {"categories": set(), "retreats": 0,
                               "products": 0, "regions": set()})
        if p.get("category"):
            b["categories"].add(p["category"])
        if p.get("item_type") != "event":
            b["products"] += 1
    for o in occs:
        b = by_org.setdefault(o["organization_id"],
                              {"categories": set(), "retreats": 0,
                               "products": 0, "regions": set()})
        b["retreats"] += 1
        if o.get("region"):
            b["regions"].add(o["region"])

    items = []
    all_categories: dict = {}
    for s in stores:
        org = orgs.get(s["organization_id"])
        if not org:
            continue
        b = by_org.get(s["organization_id"],
                       {"categories": set(), "retreats": 0,
                        "products": 0, "regions": set()})
        cats = sorted(b["categories"])
        for c in cats:
            all_categories[c] = all_categories.get(c, 0) + 1
        if category and category not in b["categories"]:
            continue
        pp = org.get("public_profile") or {}
        ss = org.get("store_settings") or {}
        items.append({
            "org_slug": s["slug"],
            "name": (ss.get("display_name") or s.get("name")
                     or org.get("name") or s["slug"]),
            "bio": ((pp.get("bio") or s.get("description") or "")[:200]) or None,
            "logo_url": s.get("logo_url") or ss.get("logo_url")
                        or pp.get("logo_url"),
            "cover_url": pp.get("cover_url"),
            "categories": cats,
            "upcoming_retreats": b["retreats"],
            "other_products": b["products"],
            "regions": sorted(b["regions"]),
        })

    items.sort(key=lambda x: (-x["upcoming_retreats"], x["name"].lower()))
    return {"items": items, "total": len(items),
            "categories": all_categories}


@router.get("/operator/{org_slug}")
async def public_operator_profile(org_slug: str):
    """Profilo pubblico organizzatore: bio, brand, prossimi ritiri.
    L'org_slug è quello dello storefront (store slug o public_slug)."""
    from datetime import datetime, timezone
    from database import event_occurrences_collection, products_collection

    org = await _resolve_org(org_slug)   # 404 se non pubblico
    org_id = org["id"]
    store = org.get("_store") or {}
    ss = org.get("store_settings") or {}

    now_iso = datetime.now(timezone.utc).isoformat()[:16]
    occs = await event_occurrences_collection.find(
        {"organization_id": org_id, "status": "published",
         "start_at": {"$gte": now_iso}},
        {"_id": 0, "id": 1, "slug": 1, "product_id": 1, "start_at": 1,
         "end_at": 1, "city": 1, "region": 1, "cover_image_url": 1,
         "price_override": 1},
    ).sort("start_at", 1).to_list(60)
    prod_ids = list({o["product_id"] for o in occs})
    prods = await products_collection.find(
        {"id": {"$in": prod_ids}, "is_active": True, "is_published": True},
        {"_id": 0, "id": 1, "name": 1, "category": 1, "unit_price": 1, "image_url": 1},
    ).to_list(200)
    prod_by_id = {p["id"]: p for p in prods}

    upcoming = []
    for o in occs:
        p = prod_by_id.get(o["product_id"])
        if not p or not o.get("slug"):
            continue
        upcoming.append({
            "title": p["name"], "category": p.get("category"),
            "url": f"/e/{org_slug}/{o['slug']}",
            "start_at": o["start_at"], "end_at": o.get("end_at"),
            "city": o.get("city"), "region": o.get("region"),
            "cover_image_url": o.get("cover_image_url") or p.get("image_url"),
            "price_from": o.get("price_override") or p.get("unit_price"),
        })

    # F2.0 (5/7/2026) — il profilo curato dall'operatore (public_profile)
    # VINCE sui fallback derivati dallo store; contatti solo se opt-in.
    pp = org.get("public_profile") or {}
    out = {
        "org_slug": org_slug,
        "name": store.get("name") or store.get("display_name") or ss.get("display_name") or org.get("name") or "",
        "bio": pp.get("bio") or store.get("description") or ss.get("store_description"),
        "logo_url": store.get("logo_url") or ss.get("logo_url"),
        "cover_url": pp.get("cover_url"),
        "brand_color": store.get("brand_color") or ss.get("brand_color"),
        "city": pp.get("city") or ss.get("city"),
        "region": pp.get("region"),
        "socials": {k: pp.get(k) for k in ("instagram", "website", "facebook")
                    if pp.get(k)},
        "upcoming": upcoming,
        "upcoming_count": len(upcoming),
        # F2.1 ecosistema — link allo store dell'operatore (se pubblicato)
        "store_slug": store.get("slug") if store.get("is_published", True) else None,
        # M3 — segnali di fiducia: anzianita' e ritiri organizzati (tutti,
        # anche passati: e' l'esperienza che conta)
        "member_since": (str(org.get("created_at") or "")[:4] or None),
        "retreats_organized": await event_occurrences_collection.count_documents(
            {"organization_id": org_id, "status": {"$in": ["published", "closed"]}}),
        # PR1 — carta d'identità
        "tagline": pp.get("tagline"),
        "portrait_url": pp.get("portrait_url"),
        "photos": pp.get("photos") or [],
        "founded_year": pp.get("founded_year"),
        "languages": pp.get("languages") or [],
        # PR2 — rating denormalizzato (None finché non ci sono recensioni)
        "reviews_stats": org.get("reviews_stats"),
        "reviews_open": bool(org.get("reviews_open")),
    }
    if pp.get("show_contacts"):
        out["contacts"] = {k: pp.get(k) for k in ("public_email", "public_phone")
                           if pp.get(k)}
    return out
