"""Embed Public Router — Phase 1 Step 12 (2026-05-28).

Endpoint pubblici per il widget Web Components cross-origin (Stream A).
Mounted under `/api/public/embed/*` → coperti dal DynamicCORSMiddleware
(Phase 0 Step 7) + IdempotencyMiddleware (Phase 0 Step 8) per le mutazioni.

Endpoint in questo router (Track A, incremental):
  Step 12 — GET /init/{slug}        bootstrap meta + categories + capabilities
  Step 13 — GET /categories/{slug}  (futuro — endpoint dedicato con thumbnail)
  Step 14 — GET /products/{slug}    (futuro — catalog filterable)
  Step 15 — */cart/*                (futuro — alias cart)
  Step 16 — POST /checkout/start    (futuro — orchestrazione Stripe)
  Step 17 — GET /checkout/complete  (futuro — postMessage bridge)

Sicurezza
=========
- DynamicCORS rifiuta Origin non in store.allowed_origins[]
- Idempotency-Key obbligatorio su POST/PATCH/PUT/DELETE
- Multi-tenant: ogni handler usa `_resolve_org(slug)` per scoping
- No PII leak: response models sentinel-pinned
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from routers.auth import limiter
# Track E Step 2.4.6 — sub-models riusati per type-aware EmbedProductDetail.
# Riuso totale per evitare divergence con lo storefront pubblico (parita').
from routers.public import (
    StoreInfo,
    PublicServiceOption,
    PublicOccurrence,
    PublicTier,  # noqa: F401 — riferito da PublicOccurrence
    FieldConfig,
)

# Track O Step E1.1 — Embed API versioning helper.
# Applicato in TUTTI gli endpoint embed (sentinel verifica) per signal
# del contratto applicato + future-proof a breaking changes versionate.
from core.embed_versioning import apply_api_version

# Track E Step 1.4 — Per-merchant rate limit isolation.
# get_real_ip_with_slug compone bucket key = "{ip}|s={slug}" → merchant
# diverso bucket diverso. Override per-route del limiter default key_func
# (get_real_ip, IP only). Backward compat: endpoint senza slug fallback
# a IP only.
from core.rate_limiting import get_real_ip_with_slug, get_real_ip
# Step 15 — Riusiamo gli stessi modelli cart del legacy storefront. Niente
# duplicazione schema → zero risk di divergenza degli invarianti INV-CART-*.
#
# NOTE: NON usare `from __future__ import annotations` in questo file.
# FastAPI 0.x ha un bug con PEP 563 lazy annotations: i parametri Pydantic
# BaseModel come body vengono interpretati come Query params perché il
# ForwardRef non viene risolto correttamente da get_type_hints(). Sintomo:
# error 422 con `{"loc": ["query", "body"]}`. Reverting a annotations eager.
from models.cart import (
    CartCreate,
    CartUpdate,
    CartResponse,
    CartMergeRequest,
)
# F1/F2 — modulo Newsletter: config pubblica + payload/response del submit
from models.newsletter import (
    NewsletterSubmitRequest,
    NewsletterSubmitResponse,
    NewsletterFormPublic,
)

# Step 16 — EmailStr import per la validation di customer_email
from pydantic import EmailStr

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public/embed", tags=["Public Embed Widget"])


# ── Response models ─────────────────────────────────────────────────────


class EmbedCapabilities(BaseModel):
    """Feature gates the widget may use to enable/disable UI surfaces."""

    checkout_stripe_enabled: bool = True
    cart_enabled: bool = True
    customer_auth_enabled: bool = True


class EmbedCategorySummary(BaseModel):
    """A single category exposed to the widget for filter UI.

    ``slug`` is URL-safe ASCII lowercase (see
    ``services.embed_init_service._normalize_category_slug``).
    The widget accepts ``<afianco-product-grid category="catering">`` etc.
    """

    name: str
    slug: str
    count: int


class EmbedCategoryItem(BaseModel):
    """A single category in the dedicated /categories endpoint.

    Differs from ``EmbedCategorySummary`` only by the additional
    ``thumbnail_url`` field. Kept as a separate model so the init payload
    (Step 12) stays minimal — widgets that need thumbnails ALSO call
    /categories with ``?with_thumbnail=true``.
    """

    name: str
    slug: str
    count: int
    thumbnail_url: Optional[str] = None


class EmbedCategoriesResponse(BaseModel):
    """Response model for GET /api/public/embed/categories/{slug}."""

    slug: str
    categories: List[EmbedCategoryItem] = Field(default_factory=list)


class EmbedInitResponse(BaseModel):
    """Bootstrap payload returned by ``GET /api/public/embed/init/{slug}``.

    Field stability is a CONTRACT — sentinel test ``INV-EI-1`` pinna
    i campi obbligatori. Aggiunte additive sono OK; rimozioni o rinomine
    richiedono bumpare la versione embed SDK (es. /v0/ → /v1/).
    """

    slug: str
    org_name: str
    store_info: Optional[StoreInfo] = None
    currency: str = "EUR"
    storefront_languages: List[str] = Field(default_factory=lambda: ["it"])
    available_product_types: List[str] = Field(default_factory=list)
    categories: List[EmbedCategorySummary] = Field(default_factory=list)
    capabilities: EmbedCapabilities = Field(default_factory=EmbedCapabilities)
    fulfillment_modes: List[str] = Field(default_factory=list)
    # Track E Step 4.3 — Design tokens (Phase 9) per brand customization.
    # Stesso payload di CatalogResponse.design_tokens (parita' storefront).
    # Widget Lit applica come CSS variables sul host <afianco-storefront-init>:
    #   accent_color → --afianco-color-primary
    #   font_family → --afianco-font-family
    #   border_radius (sharp/standard/soft/pill) → --afianco-radius-md
    #   density (compact/standard/spacious) → --afianco-spacing-md
    #   header_style, card_style → CSS class modifiers
    # Empty dict = merchant non ha customizzato, widget usa defaults.
    design_tokens: Dict[str, Any] = Field(default_factory=dict)
    # Track E Step 4.3 — Custom navigation links (Phase 8). Lista di
    # {label, url} configurati nell'admin per il header storefront.
    # Widget <afianco-header> li renderizza opzionali tra brand-name e icone.
    custom_nav_links: List[Dict[str, Any]] = Field(default_factory=list)
    # Track E Step 7.4 — Legal disclosure URLs (Privacy Policy + Termini
    # di Servizio). Default: pagine hosted afianco-side
    # ``https://app.afianco.ch/s/{slug}/{privacy|terms}`` — la SPA React
    # le renderizza consumando ``/api/legal/storefront/{slug}/...``.
    # Override: merchant puo' configurare un URL custom in store settings
    # (campi ``privacy_policy_url`` / ``terms_service_url``) per puntare
    # al proprio dominio. Widget Lit aggiunge ``<a target="_blank">``
    # cliccabili nei checkbox GDPR di signup + checkout — PARITA' con lo
    # storefront classico che gia' linka questi URL. Sentinel INV-EI-LEGAL
    # pinna la presenza dei due field.
    privacy_policy_url: Optional[str] = None
    terms_service_url: Optional[str] = None


# ── Step 14 — Products list response models ─────────────────────────────


class EmbedProductCard(BaseModel):
    """Public-safe product card surface for grid render.

    DELIBERATELY LIGHT: nessun side-fetch (no service_options, no event
    occurrences, no rental extras). I dettagli type-specific saranno
    esposti in un futuro endpoint ``GET /embed/products/{slug}/{id}``
    (Step 14b). Lo widget grid mostra le card; il click apre un modal
    che chiama l'endpoint detail per il drill-down.

    Sentinel `INV-EP-8` pinna no PII leak su questo modello.
    """

    id: str
    slug: Optional[str] = None
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    unit_price: Optional[float] = None
    currency: str = "EUR"
    category: Optional[str] = None
    category_slug: Optional[str] = None
    item_type: str
    unit: Optional[str] = None
    unit_label: Optional[str] = None
    price_mode: str = "fixed"
    transaction_mode: str = "request"
    stock_quantity: Optional[int] = None


# Track E Step 2.4.5 → 2.4.6 — Product detail response model (type-aware)
class EmbedProductDetail(BaseModel):
    """Public-safe product DETAIL surface per il drawer "landing page".

    Track E Step 2.4.6 — parita' storefront completa: include tutti i
    campi type-specific che il widget Lit deve renderizzare per:
      - service: opzioni + slot booking (calendar/grid)
      - event_ticket: occurrences + tier picker
      - rental: date range / slot picker
      - course: progress + lessons count
      - digital: download policy
      - physical: stock + fulfillment options

    Mirror di ``PublicProduct`` (vedi ``backend/routers/public.py``) ma
    esposto via il path embed-ready ``/api/public/embed/products/{slug}/{id}``.
    Riusa gli stessi sub-models per consistency (PublicServiceOption,
    PublicOccurrence, PublicTier, FieldConfig).

    Pin: sentinel ``INV-EP-8-DETAIL`` verifica no PII leak (cost_price,
    cost_source, tags, metadata, organization_id MAI presenti).
    """

    # ── Identity + base display (parita' Card) ──
    id: str
    slug: Optional[str] = None
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    unit_price: Optional[float] = None
    currency: str = "EUR"
    category: Optional[str] = None
    category_slug: Optional[str] = None
    item_type: str
    unit: Optional[str] = None
    unit_label: Optional[str] = None
    price_mode: str = "fixed"
    transaction_mode: str = "request"
    stock_quantity: Optional[int] = None
    offer_profile_id: Optional[str] = None

    # ── Landing-only enrichment (E2.4.6) ──

    # Hero per landing (Onda 14 — pattern PublicProduct)
    cover_image_url: Optional[str] = None
    long_description: Optional[str] = None

    # SERVICE — opzioni + slot booking
    service_options: List["PublicServiceOption"] = Field(default_factory=list)
    service_duration_minutes: Optional[int] = None
    service_allow_custom_request: bool = False
    has_availability_slots: bool = False
    duration_label: Optional[str] = None
    slot_duration_minutes: Optional[int] = None

    # EVENT_TICKET — date + tier (sub-model riusato da public.py)
    occurrences: List["PublicOccurrence"] = Field(default_factory=list)
    requires_attendee_details: bool = False
    require_attendee_email: bool = True
    require_attendee_phone: bool = False
    attendee_fields: List["FieldConfig"] = Field(default_factory=list)
    order_fields: List["FieldConfig"] = Field(default_factory=list)

    # RENTAL — flavor + extras
    rental_unit: Optional[str] = None
    reservation_flavor: Optional[str] = None
    extras: List[dict] = Field(default_factory=list)

    # COURSE — progress + lessons (light counters)
    course_lessons_count: Optional[int] = None
    course_duration_seconds: Optional[int] = None
    course_access_policy: Optional[str] = None
    course_access_expiry_days: Optional[int] = None

    # T&C resolved (Onda 11) — markdown content da rendering nel checkout
    terms_content: Optional[str] = None


class EmbedPagination(BaseModel):
    """Pagination meta of /embed/products and similar list endpoints."""

    total: int
    limit: int
    offset: int
    has_more: bool


class EmbedProductsResponse(BaseModel):
    """Response of ``GET /api/public/embed/products/{slug}``."""

    slug: str
    currency: str = "EUR"
    items: List[EmbedProductCard] = Field(default_factory=list)
    pagination: EmbedPagination


# ── Step 16 — Checkout start request/response models ───────────────────


class EmbedCheckoutStartRequest(BaseModel):
    """Body of POST /api/public/embed/checkout/start.

    Triggera la conversione cart → order via la canonical pipeline
    ``services.order_creation_service.submit_order_from_storefront``.
    Tutti i field GDPR sono OBBLIGATORI (no default a True): il widget
    deve raccogliere consent ESPLICITO prima di chiamare questo endpoint.

    Security
    --------
    ``embed_return_url`` viene validato contro ``store.allowed_origins``
    PRIMA che qualsiasi business logic venga eseguita. Una merchant
    misconfiguration NON puo' phisheare il customer mandandolo a un
    dominio non autorizzato.

    Auth modes (Step 18)
    --------------------
    1) **Guest** (default): no Authorization header, no create_account.
       Pipeline crea customer record CRM (no account portal access).
    2) **Authenticated** (Step 18a): widget passa
       ``Authorization: Bearer <customer JWT>``. Handler estrae
       ``customer_account_id`` dal payload e lo propaga al order doc.
       org_id del token deve combaciare con lo store slug.
    3) **Signup-inline** (Step 18c): widget passa ``create_account=True``
       + ``account_password``. Handler chiama ``customer_signup(auto_login=True)``
       PRIMA del checkout, ottiene token, lega cart, crea order.
       Le tre flag GDPR sono usate sia per signup che per order.
    """

    slug: str = Field(min_length=3, max_length=50)
    cart_id: str = Field(min_length=1, max_length=64)
    customer_name: str = Field(min_length=1, max_length=255)
    customer_email: EmailStr
    customer_phone: Optional[str] = Field(default=None, max_length=50)
    embed_return_url: str = Field(min_length=1, max_length=1024)

    # GDPR (parity con OrderRequestPayload legacy)
    gdpr_terms_accepted: bool = False
    gdpr_privacy_accepted: bool = False
    gdpr_marketing_accepted: bool = False
    # Legacy T&C (CG-5 → GDPR replaces; kept additive for compat)
    terms_accepted: bool = False

    # Optional fulfillment fields — mirror dei OrderRequestPayload
    fulfillment_mode: Optional[str] = Field(default=None, pattern="^(shipping|local_pickup)$")
    notes: Optional[str] = Field(default=None, max_length=2000)

    # ── Track E Step 3.2 — Dynamic order_fields (custom merchant fields) ──
    # Dict {field_id: value} popolato dai FieldConfig configurati dal
    # merchant in product.metadata.order_fields[]. Validato server-side
    # vs i required field nei products del cart. Parita' con OrderRequestPayload.
    order_fields: Optional[Dict[str, Any]] = None

    # ── Track E Step 3.3 — Shipping address per prodotti physical ──
    # Dict con shape ShippingAddressInput (vedi backend/routers/public.py:308):
    # {recipient_name, line1, civic, postal_code, city, province, country}.
    # Required quando fulfillment_mode='shipping' + cart contiene physical.
    shipping_address_details: Optional[Dict[str, Any]] = None
    # Shipping option scelto (id + label per audit). Required se cart ha
    # physical + mode=shipping + merchant ha shipping_options configurati.
    shipping_option_id: Optional[str] = Field(default=None, max_length=64)
    shipping_option_label: Optional[str] = Field(default=None, max_length=120)

    # ── Track E Step 4.1 — Coupon code (discount promo) ──
    # Validato server-side via validate_coupon (atomic increment usage)
    # nel checkout pipeline. Customer puo' verificare validita' PRE-checkout
    # via POST /api/public/embed/coupons/validate/{slug} (dry-run, no usage
    # increment). Trade-off: tra preview + checkout coupon puo' esaurirsi —
    # error message chiaro al submit.
    coupon_code: Optional[str] = Field(default=None, max_length=30)

    # ── Step 18c: inline signup-during-checkout ──
    # Pattern Shopify/WooCommerce "Create an account? [✓]". Quando True,
    # il backend crea un customer account PRIMA del checkout, mintarsi
    # il customer JWT con ``auto_login=True``, e propaga
    # customer_account_id all'order. Senza questo flow il customer
    # dovrebbe fare 2 fetch (signup → checkout) → 2 round-trip.
    create_account: bool = False
    # Password per il nuovo account; validato lato signup service
    # (validate_password_strength: min 8 chars + complexity).
    account_password: Optional[str] = Field(default=None, min_length=8, max_length=100)
    # Locale del customer per i template email post-signup
    account_locale: Optional[str] = Field(default="it", min_length=2, max_length=8)


class EmbedCheckoutStartResponse(BaseModel):
    """Response del endpoint checkout/start.

    Quando ``payment_checkout_url`` è non-null, il widget apre il popup
    Stripe Checkout (gestito dalla pagina afianco-hosted di success).
    Altrimenti il customer va alla landing /co/<slug>/<order_id> o
    riceve solo il messaggio di conferma "richiesta ricevuta".

    Step 18c: ``customer_access_token`` viene popolato quando
    ``create_account=True`` ha avuto successo. Il widget deve salvarlo
    (localStorage prefixed per merchant) per le successive chiamate
    customer-portal e per evitare guest-checkout su acquisti successivi.
    """

    order_id: str
    transaction_mode: str = "request"
    order_status: str = "draft"
    message: str = ""
    payment_checkout_url: Optional[str] = None
    payment_reason: Optional[str] = None
    embed_return_url: str
    # Step 18c — token customer post-signup-inline (null in guest/auth modes)
    customer_access_token: Optional[str] = None
    # Step 18a/c — flag che permette al widget di sapere come gestire la response
    # (utile per UX: "Account creato!" toast vs solo confirmation)
    account_created: bool = False
    # Echo helpful: il widget conosce a quale origin postMessage targetare
    # quando Step 17 (postMessage bridge) viene completato.


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get(
    "/init/{slug}",
    response_model=EmbedInitResponse,
    summary="Embed widget bootstrap (meta + categories + capabilities)",
)
@limiter.limit("60/minute", key_func=get_real_ip_with_slug)
async def get_embed_init(
    request: Request,
    response: Response,
    slug: str,
) -> EmbedInitResponse:
    """One round-trip che restituisce tutto ciò che serve al widget per
    renderizzare header / footer / categorie / capability — esclusi i
    prodotti (fetched lazy via `/embed/products`).

    Caching
    -------
    ``Cache-Control: public, max-age=300`` (Track S Step 3.4) + ``ETag``
    deterministico permettono CDN cache + 304 Not Modified su retry.

    Errors
    ------
    - 404 se ``slug`` non risolve a uno store pubblicato e pubblico
      (delegato a ``_resolve_org``)
    - 429 se rate limit superato (60/min per IP)
    """
    from services.embed_init_service import get_embed_init_data
    from core.observability import metrics as _metrics

    # Track O Step E1.1 — apply API version (sets response X-API-Version
    # header + validates request header). Returns resolved version int.
    apply_api_version(request, response)

    data = await get_embed_init_data(slug)
    payload = EmbedInitResponse(**data)

    # ── Cache headers (CDN-friendly) ──
    # Track S Step 3.4: TTL 300s (5 min) per ridurre throughput su
    # competitor scraper. Pre-S3.4: 60s. Admin changes ora propagano
    # in ~5min — accettabile per init payload (categories, brand,
    # capabilities) che cambia raramente. Per il customer experience
    # cache-bust possibile via query param (?_v=<commit-sha>).
    response.headers["Cache-Control"] = "public, max-age=300"

    # Deterministic ETag → 304 short-circuit per scrape ripetute
    # dallo stesso widget cold start.
    etag_source = payload.model_dump_json().encode("utf-8")
    # NB: SHA-1 e' usato qui SOLO come content-hash per HTTP ETag
    # (deterministic short fingerprint per 304 Not Modified). NON e'
    # crittografico — il flag usedforsecurity=False segnala intent a
    # bandit (B324) e a FIPS-mode Python (Phase 0 audit Track S Step 4.3).
    etag = hashlib.sha1(etag_source, usedforsecurity=False).hexdigest()
    response.headers["ETag"] = f'"{etag}"'

    # Conditional GET: if client sends If-None-Match matching our ETag,
    # return 304 (no body). Riduce bandwidth su retry post-cache-expire.
    if_none_match = request.headers.get("if-none-match", "").strip('"')
    if if_none_match == etag:
        # Soft-fail metric (cache_result label "if-none-match")
        try:
            _metrics.record_embed_init(slug=slug, cache_result="if_none_match")
        except Exception:
            pass
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return payload  # body discarded by 304 semantics

    # Cache miss / first hit
    try:
        _metrics.record_embed_init(slug=slug, cache_result="miss")
    except Exception:
        pass

    return payload


@router.get(
    "/categories/{slug}",
    response_model=EmbedCategoriesResponse,
    summary="Public categories for a store (with optional thumbnail)",
)
@limiter.limit("60/minute", key_func=get_real_ip_with_slug)
async def get_embed_categories(
    request: Request,
    response: Response,
    slug: str,
    with_thumbnail: bool = Query(
        default=False,
        description=(
            "If true, each category includes a thumbnail_url field "
            "populated with the first published product image in that "
            "category. Adds one Mongo round-trip per category — keep "
            "default False unless the widget renders image tiles."
        ),
    ),
    include_empty: bool = Query(
        default=False,
        description=(
            "Reserved for future compat. Today categories with zero "
            "published products simply don't exist in the aggregation "
            "output, so this flag is a no-op. Will honour a future "
            "Category entity registry."
        ),
    ),
) -> EmbedCategoriesResponse:
    """Distinct public categories with count and (optionally) thumbnail.

    Caching
    -------
    ``Cache-Control: public, max-age=300`` (Track S Step 3.4, same TTL del
    /init) + deterministic ``ETag``. Conditional GET via ``If-None-Match``
    returns 304 Not Modified.

    Multi-tenant
    ------------
    Resolved via ``_resolve_org(slug)`` (404 if slug unknown). Store
    scoping applies in multi-store orgs (only products assigned to
    this store, or globally assigned).

    Slug normalization
    ------------------
    Categories are merged when two raw values normalize to the same
    slug (e.g. ``"Catering"`` and ``"catering"`` collapse into a single
    row with summed count). Slug is URL-safe ASCII lowercase — see
    ``services.embed_init_service._normalize_category_slug``.
    """
    from services.embed_init_service import get_embed_categories_data
    from core.observability import metrics as _metrics

    # Track O Step E1.1 — apply API version
    apply_api_version(request, response)

    data = await get_embed_categories_data(
        slug=slug,
        with_thumbnail=with_thumbnail,
        include_empty=include_empty,
    )
    payload = EmbedCategoriesResponse(**data)

    # ── Cache headers ── Track S Step 3.4: TTL 300s (was 60s) per
    # scrape defense — categories list changes rarely (new product
    # category = manual admin action). Same TTL del /init.
    response.headers["Cache-Control"] = "public, max-age=300"

    # Deterministic ETag — includes the thumbnail flag in the source
    # because the two variants produce different bodies.
    etag_source = (
        f"{with_thumbnail}:{include_empty}:" + payload.model_dump_json()
    ).encode("utf-8")
    # NB: SHA-1 e' usato qui SOLO come content-hash per HTTP ETag
    # (deterministic short fingerprint per 304 Not Modified). NON e'
    # crittografico — il flag usedforsecurity=False segnala intent a
    # bandit (B324) e a FIPS-mode Python (Phase 0 audit Track S Step 4.3).
    etag = hashlib.sha1(etag_source, usedforsecurity=False).hexdigest()
    response.headers["ETag"] = f'"{etag}"'

    # Conditional GET → 304
    if_none_match = request.headers.get("if-none-match", "").strip('"')
    if if_none_match == etag:
        try:
            _metrics.record_embed_category_lookup(
                slug=slug, with_thumbnail=with_thumbnail
            )
        except Exception:
            pass
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return payload

    try:
        _metrics.record_embed_category_lookup(
            slug=slug, with_thumbnail=with_thumbnail
        )
    except Exception:
        pass

    return payload


# ── Step 14 — Products list ────────────────────────────────────────────


@router.get(
    "/products/{slug}",
    response_model=EmbedProductsResponse,
    summary="Public products list with filter + sort + pagination",
)
@limiter.limit("60/minute", key_func=get_real_ip_with_slug)
async def get_embed_products(
    request: Request,
    response: Response,
    slug: str,
    category: Optional[str] = Query(
        default=None,
        description=(
            "Filter by category slug (URL-safe, case-insensitive). "
            "Esempio: ?category=catering. La normalizzazione mappa "
            "raw category names dei prodotti allo stesso slug."
        ),
        max_length=120,
    ),
    type: Optional[str] = Query(  # noqa: A002 — `type` is the public name
        default=None,
        description=(
            "Filter by item_type. Valori whitelistati: physical, service, "
            "rental, event_ticket, digital, course."
        ),
        max_length=40,
    ),
    sort: str = Query(
        default="name",
        description=(
            "Sort mode: name (default) | price_asc | price_desc | newest "
            "| relevance. Input non whitelistati → 400. 'relevance' valid "
            "solo se q presente, altrimenti fallback a 'name'."
        ),
        max_length=20,
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10_000),
    # Track E Step 1.3 — full-text search query opzionale. Mongo $text
    # operator (no regex injection). Cap a 200 char (defense in depth +
    # FastAPI Query max_length). Empty/whitespace = no filter.
    q: Optional[str] = Query(
        default=None,
        description=(
            "Full-text search query. Cerca in product name (weight 3) + "
            "description (weight 1). Italiano stemmer. Phrase con quotes, "
            "exclusion con `-` prefix. Empty = no filter."
        ),
        max_length=200,
    ),
) -> EmbedProductsResponse:
    """Paginated, filterable list of public products for embed widget.

    Sicurezza
    ---------
    - `category` viene normalizzato (slugify) e poi risolto in raw
      names via $in (no regex injection).
    - `type` validato contro la whitelist ``PRODUCT_TYPE_KEYS`` ad
      handler-level (400 se sconosciuto).
    - `sort` validato contro ``EMBED_PRODUCT_SORT_MODES`` (400 se altro).
    - `limit` hard-capped a 100 (anti-scraping); `offset` capped 10k.
    - Multi-tenant: ``_resolve_org(slug)`` filtra org_id su tutte le query.

    Performance
    -----------
    Cache 60s + ETag deterministico (include params nei digest così
    varianti producono cache distinte). Conditional GET → 304.
    Solo 2 query Mongo: count + find paginato. No N+1 (zero side-fetch
    enrichment — quello e' deferred a /products/{slug}/{id} detail).
    """
    from services.embed_init_service import (
        get_embed_products_data,
        EMBED_PRODUCT_SORT_MODES,
    )
    from models.product_types import PRODUCT_TYPE_KEYS
    from core.observability import metrics as _metrics
    from fastapi import HTTPException

    # ── Validate sort ──
    if sort not in EMBED_PRODUCT_SORT_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid sort='{sort}'. "
                f"Valid: {sorted(EMBED_PRODUCT_SORT_MODES)}"
            ),
        )

    # ── Validate type filter ──
    if type is not None and type not in PRODUCT_TYPE_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid type='{type}'. "
                f"Valid: {sorted(PRODUCT_TYPE_KEYS)}"
            ),
        )

    # Track O Step E1.1 — apply API version
    apply_api_version(request, response)

    # ── Fetch ──
    data = await get_embed_products_data(
        slug=slug,
        category_slug=category,
        type_filter=type,
        sort_mode=sort,
        limit=limit,
        offset=offset,
        # Track E Step 1.3 — pass through search_query (None se assente)
        search_query=q,
    )
    payload = EmbedProductsResponse(**data)

    # ── Cache headers ── Track S Step 3.4: TTL 300s (was 60s) per
    # scrape defense. Trade-off: prezzo / stock cambia in real-time per
    # alcuni merchant (es. last-minute restock), 5min potrebbe creare
    # discrepancy customer vs inventory. Mitigato da:
    #   · ETag deterministico → 304 Not Modified per re-request veloci
    #   · stock_quantity nel payload e' snapshot (al consumo cart usa
    #     query fresh dal DB, no over-sell)
    # Per merchant high-frequency: query param ?_v=<sha> per bypass cache.
    response.headers["Cache-Control"] = "public, max-age=300"

    # ETag includes all query params so different filters → different cache entries
    # Track E Step 1.3 — q incluso nel digest (varianti search → distinct cache).
    etag_source = (
        f"{category}|{type}|{sort}|{limit}|{offset}|{q or ''}|"
        + payload.model_dump_json()
    ).encode("utf-8")
    # NB: SHA-1 e' usato qui SOLO come content-hash per HTTP ETag
    # (deterministic short fingerprint per 304 Not Modified). NON e'
    # crittografico — il flag usedforsecurity=False segnala intent a
    # bandit (B324) e a FIPS-mode Python (Phase 0 audit Track S Step 4.3).
    etag = hashlib.sha1(etag_source, usedforsecurity=False).hexdigest()
    response.headers["ETag"] = f'"{etag}"'

    # ── Conditional GET → 304 ──
    if_none_match = request.headers.get("if-none-match", "").strip('"')
    has_filter = bool(category or type)
    if if_none_match == etag:
        try:
            _metrics.record_embed_product_search(slug=slug, has_filter=has_filter)
        except Exception:
            pass
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return payload

    try:
        _metrics.record_embed_product_search(slug=slug, has_filter=has_filter)
    except Exception:
        pass

    return payload


# ── Step 14b — Product detail endpoint (E2.4.5) ────────────────────────


@router.get(
    "/products/{slug}/{product_id}",
    response_model=EmbedProductDetail,
    summary="Public product detail per drawer landing page del widget",
)
@limiter.limit("60/minute", key_func=get_real_ip_with_slug)
async def get_embed_product_detail(
    request: Request,
    response: Response,
    slug: str,
    product_id: str,
) -> EmbedProductDetail:
    """Single product detail for the embed widget drawer.

    Use case
    --------
    Grid mostra cards leggere → user clicca → drawer apre con questo
    endpoint per fetcha description full + futuri type-specific data
    (service_options, ticket_tiers, occurrences, rental_rules).

    Sicurezza
    ---------
    - Multi-tenant: compound match ``(product_id, org_id)`` previene
      cross-tenant access. Un attacker NON puo' guessare product_id
      su slug X per leakare prodotti di slug Y.
    - Publication gate: ``is_published=True`` + ``is_active=True``.
      Prodotti soft-deleted / draft / nascosti → 404 opaco (no info
      leak su existence — Track S Step 3.5 pattern).
    - PII leak: projection chirurgica (vedi
      ``_public_detail_projection``). cost_price, cost_source, tags,
      metadata, organization_id MAI nel response. Pin sentinel.
    - Rate limit: 60/min per (IP, slug). Anti-scraping.

    Performance
    -----------
    Cache 300s + ETag deterministico. Single Mongo query (no N+1).
    Per type-specific extras (v2): lazy side-fetch SOLO per il type
    rilevante (es. service → service_options collection, event_ticket
    → ticket_tiers + product_occurrences). Mantenere O(1+small_k)
    queries per request.

    Args:
        slug: store slug del merchant
        product_id: product id (NB: NON product.slug — il widget
            passa l'id intero ricevuto dal grid `/products/{slug}`)

    Returns:
        EmbedProductDetail model

    Raises:
        404: prodotto non trovato (multi-tenant: slug/product_id
            mismatch o prodotto non pubblicato)
    """
    from services.embed_init_service import get_embed_product_detail_data
    from fastapi import HTTPException
    from core.observability import metrics as _metrics

    # Track O Step E1.1 — apply API version
    apply_api_version(request, response)

    doc = await get_embed_product_detail_data(slug=slug, product_id=product_id)
    if not doc:
        # Track S Step 3.5: 404 opaco con detail string standard, no leak
        # del motivo (slug unknown vs product unknown vs unpublished).
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    payload = EmbedProductDetail(**doc)

    # Cache headers — TTL 300s allineato al list endpoint.
    response.headers["Cache-Control"] = "public, max-age=300"

    # ETag deterministic — hash del payload content.
    etag_source = (
        f"{slug}|{product_id}|" + payload.model_dump_json()
    ).encode("utf-8")
    etag = hashlib.sha1(etag_source, usedforsecurity=False).hexdigest()
    response.headers["ETag"] = f'"{etag}"'

    # Conditional GET → 304
    if_none_match = request.headers.get("if-none-match", "").strip('"')
    if if_none_match == etag:
        try:
            _metrics.record_embed_product_detail(slug=slug)
        except Exception:
            pass
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return payload

    try:
        _metrics.record_embed_product_detail(slug=slug)
    except Exception:
        pass

    return payload


# ── Step 14c — Availability endpoint per service slot booking (E2.4.6) ──


class EmbedAvailabilitySlot(BaseModel):
    """Single time slot — start/end ISO time strings."""
    start: str  # HH:MM
    end: str    # HH:MM


class EmbedAvailabilityDay(BaseModel):
    """Available slots for a single date."""
    date: str       # YYYY-MM-DD
    day_name: str   # "lunedi", "martedi", ecc.
    slots: List[EmbedAvailabilitySlot] = Field(default_factory=list)


class EmbedAvailabilityResponse(BaseModel):
    """Response of GET /api/public/embed/products/{slug}/{id}/availability.

    Mirror of /api/public/availability/{slug} (public.py) ma scoped al
    product_id specifico + protetto da DynamicCORSMiddleware.
    """
    slug: str
    product_id: str
    duration_minutes: Optional[int] = None
    days: List[EmbedAvailabilityDay] = Field(default_factory=list)


@router.get(
    "/products/{slug}/{product_id}/availability",
    response_model=EmbedAvailabilityResponse,
    summary="Service product slot availability per il calendar widget",
)
@limiter.limit("30/minute", key_func=get_real_ip_with_slug)
async def get_embed_product_availability(
    request: Request,
    response: Response,
    slug: str,
    product_id: str,
    date_from: Optional[str] = Query(
        default=None,
        description="Start date YYYY-MM-DD. Default: today.",
    ),
    date_to: Optional[str] = Query(
        default=None,
        description="End date YYYY-MM-DD. Default: today + 30 days. Max range: 30 days.",
    ),
    duration: Optional[int] = Query(
        default=None,
        ge=15, le=480,
        description="Override slot duration in minutes (uses product service_duration_minutes by default).",
    ),
) -> EmbedAvailabilityResponse:
    """Compute available booking slots for a service product.

    Track E Step 2.4.7 (FIX) — wrapper di ``services.slot_generator.
    generate_available_slots()`` per parita' TOTALE con il storefront
    React (`/api/public/services/{id}/slots`). Riusa la stessa logica:
      - Fetch rules per product + global (org-scoped)
      - Fallback ``use_default_schedule`` (Onda 15): se nessuna rule
        ma il prodotto ha il flag, synthesize grid 9-18 7-day
      - Subtract blocked_slots + cross-product agenda overlap (scope)
      - Subtract booking confermati (no double-book)

    Pre-fix usava algoritmo manuale chiamando ``_generate_slots_from_rule``
    direttamente — mancava il fallback ``use_default_schedule`` e la
    cross-product overlap (`scope="agenda"`). Risultato: prodotti con
    `use_default_schedule=true` nel storefront avevano slot synth ma
    nel widget embed ritornavano `days: []` (bug discrepancy E2.4.7).

    Embed-ready features:
      - Multi-tenant guard (compound match slug + product_id)
      - CORS dinamico via DynamicCORSMiddleware
      - Rate limit 30/min per (IP, slug)

    Args:
        slug: store slug merchant
        product_id: service product UUID (item_type=service required)
        date_from/date_to: range (default: oggi -> +30g, max 30g)
        duration: override slot duration (default: product metadata.duration_minutes)

    Returns:
        EmbedAvailabilityResponse con days[] = [{date, day_name, slots[]}]
    """
    from datetime import date as date_type, timedelta
    from database import products_collection
    from routers.public import _resolve_org
    from services.slot_generator import generate_available_slots
    from routers.availability import DAY_NAMES

    apply_api_version(request, response)

    # Resolve org + store (multi-tenant validation)
    org = await _resolve_org(slug)
    org_id = org["id"]
    store_id = (org.get("_store") or {}).get("id")

    # Validate product exists in this org + is service/rental (multi-tenant)
    product_match: dict = {
        "id": product_id,
        "organization_id": org_id,
        "is_active": True,
        "is_published": True,
    }
    if store_id:
        product_match["$or"] = [
            {"store_ids": store_id},
            {"store_ids": {"$size": 0}},
            {"store_ids": {"$exists": False}},
        ]
    prod = await products_collection.find_one(
        product_match,
        {"_id": 0, "id": 1, "item_type": 1, "metadata": 1},
    )
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Validate item_type — solo service/rental supportano slot booking
    item_type = prod.get("item_type")
    if item_type not in ("service", "rental"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slot booking non supportato per item_type={item_type}",
        )

    # Parse date range (default: today → +30gg)
    today = date_type.today()
    try:
        start = date_type.fromisoformat(date_from) if date_from else today
        end_d = (
            date_type.fromisoformat(date_to) if date_to else (today + timedelta(days=30))
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format (expected YYYY-MM-DD)",
        )
    if (end_d - start).days > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Max 30 days range",
        )
    if end_d < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be >= date_from",
        )

    days_count = (end_d - start).days + 1

    # Apply duration override (se passato dal client) sul metadata copy
    meta = dict(prod.get("metadata") or {})
    if duration is not None:
        meta["duration_minutes"] = duration

    # Determina lo scope cross-product:
    #   - service → "agenda" (services condividono la stessa agenda admin)
    #   - rental+slot → "rentals" (rental calendar)
    scope = "agenda" if item_type == "service" else "rentals"

    # Generate slots via service condiviso con il storefront — parita' totale
    default_duration, slots_flat = await generate_available_slots(
        org_id=org_id,
        product_id=product_id,
        metadata=meta,
        days=days_count,
        scope=scope,
    )

    # Raggruppa per data + applica filtro date_from (slot_generator ritorna
    # da oggi, ma il client puo' richiedere un from > oggi)
    # NB: slot_generator ritorna {date, start_time, end_time} (vedi
    # services/slot_generator.py). Lo schema embed-public usa {start, end}
    # per consistency con i picker UI (Lit avoid keyword confusion).
    by_date: dict[str, list[dict]] = {}
    for s in slots_flat:
        d = s.get("date")
        if not d:
            continue
        # Skip se prima del date_from richiesto / dopo date_to
        if date_from and d < date_from:
            continue
        if date_to and d > date_to:
            continue
        by_date.setdefault(d, []).append({
            "start": s.get("start_time") or s.get("start") or "",
            "end": s.get("end_time") or s.get("end") or "",
        })

    # Sort by date + add day_name (localized via DAY_NAMES from availability router)
    days_out: list[dict] = []
    for d_str in sorted(by_date.keys()):
        try:
            dow = date_type.fromisoformat(d_str).weekday()
            day_name = DAY_NAMES[dow]
        except (ValueError, IndexError):
            day_name = ""
        days_out.append({
            "date": d_str,
            "day_name": day_name,
            "slots": by_date[d_str],
        })

    # Short cache — slot data e' fresh-sensitive
    response.headers["Cache-Control"] = "public, max-age=60"

    return EmbedAvailabilityResponse(
        slug=slug,
        product_id=product_id,
        duration_minutes=default_duration,
        days=days_out,
    )


def _embed_rental_product_match(org_id: str, store_id, product_id: str) -> dict:
    """R3 — match prodotto rental scoped a org+store (parità con availability)."""
    match: dict = {
        "id": product_id,
        "organization_id": org_id,
        "is_active": True,
        "is_published": True,
        "item_type": "rental",
    }
    if store_id:
        match["$or"] = [
            {"store_ids": store_id},
            {"store_ids": {"$size": 0}},
            {"store_ids": {"$exists": False}},
        ]
    return match


@router.get(
    "/products/{slug}/{product_id}/blocked-dates",
    summary="R3 — date occupate per un prodotto rental (parità storefront)",
)
@limiter.limit("30/minute", key_func=get_real_ip_with_slug)
async def get_embed_rental_blocked_dates(
    request: Request,
    response: Response,
    slug: str,
    product_id: str,
    date_from: str = Query(..., alias="from"),
    date_to: str = Query(..., alias="to"),
):
    """Date occupate (rental/booking/manual) — parità con
    ``/api/public/reservations/blocked-dates/{product_id}`` ma scoped per slug.
    Advisory UX: il guard atomico a confirm-time resta la verità.
    """
    from routers.public import _resolve_org
    from services.slot_generator import get_rental_blocked_dates
    from datetime import date as _d

    apply_api_version(request, response)
    try:
        d_from = _d.fromisoformat(date_from)
        d_to = _d.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Formato data non valido (YYYY-MM-DD)")
    if d_to < d_from:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "'to' deve essere >= 'from'")
    if (d_to - d_from).days > 90:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Finestra massima 90 giorni")

    org = await _resolve_org(slug)
    org_id = org["id"]
    store_id = (org.get("_store") or {}).get("id")
    prod = await products_collection.find_one(
        _embed_rental_product_match(org_id, store_id, product_id), {"_id": 0, "id": 1}
    )
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    response.headers["Cache-Control"] = "public, max-age=60"
    return {
        "blocked_dates": await get_rental_blocked_dates(org_id, product_id, date_from, date_to)
    }


@router.get(
    "/products/{slug}/{product_id}/availability-windows",
    summary="R3 — finestre disponibilità rental+slot (parità storefront)",
)
@limiter.limit("30/minute", key_func=get_real_ip_with_slug)
async def get_embed_rental_availability_windows(
    request: Request,
    response: Response,
    slug: str,
    product_id: str,
    days: int = Query(default=30, ge=1, le=90),
):
    """Finestre di disponibilità per rental+flavor=slot — parità con
    ``/api/public/reservations/{product_id}/availability-windows``."""
    from routers.public import _resolve_org
    from services.slot_generator import generate_availability_windows

    apply_api_version(request, response)
    org = await _resolve_org(slug)
    org_id = org["id"]
    store_id = (org.get("_store") or {}).get("id")
    prod = await products_collection.find_one(
        _embed_rental_product_match(org_id, store_id, product_id),
        {"_id": 0, "id": 1, "metadata": 1},
    )
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    meta = prod.get("metadata") or {}
    if meta.get("reservation_flavor") != "slot":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Endpoint riservato ai rental con flavor=slot",
        )

    config, windows_by_day = await generate_availability_windows(
        org_id=org_id, product_id=product_id, metadata=meta, days=days,
    )
    response.headers["Cache-Control"] = "public, max-age=60"
    return {
        "product_id": product_id,
        "min_duration_minutes": config["min_duration_minutes"],
        "step_minutes": config["step_minutes"],
        "max_duration_minutes": config["max_duration_minutes"],
        "default_duration_minutes": config["default_duration_minutes"],
        "days": windows_by_day,
    }


# ── Step 14d — Price preview embed-ready (E2.4.10) ─────────────────────


class EmbedPricePreviewRequest(BaseModel):
    """Stateless price preview per il widget detail drawer.

    Mirror di ``_PublicPricePreviewRequest`` (routers/public.py) ma scoped
    al store slug + protetto da DynamicCORSMiddleware. Usato dal componente
    Lit ``<afianco-price-preview>`` con debounced fetch (300ms) on
    qty/slot/date-range/extras change.
    """
    product_id: str
    quantity: float = 1
    discount_pct: float = 0
    # Rental flavor=range
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    # Extras selections (Onda 16 shape: {mandatory_confirmed, optional_ids,
    # radio_picks: {group_key: extra_id}})
    extra_selections: Optional[dict] = None
    # Rental flavor=slot (Onda 17 hourly pricing)
    slot_date_from: Optional[str] = None
    slot_time_from: Optional[str] = None
    slot_date_to: Optional[str] = None
    slot_time_to: Optional[str] = None


@router.post(
    "/price-preview/{slug}",
    summary="Stateless price preview per widget (drawer live total)",
)
@limiter.limit("60/minute", key_func=get_real_ip_with_slug)
async def get_embed_price_preview(
    request: Request,
    response: Response,
    slug: str,
    body: EmbedPricePreviewRequest,
):
    """Price preview embed-ready — wrapper di /api/public/price-preview.

    Sicurezza
    ---------
    - CORS dinamico (rifiuta Origin non in allowed_origins)
    - Multi-tenant: validazione (slug, product_id) prima di delegare
    - Rate limit 60/min per (IP, slug)
    - Stateless: nessun ordine creato, no persistence
    - Idempotente: stessa input → stesso output (riusabile cache HTTP)

    Args:
        slug: store slug
        body: EmbedPricePreviewRequest

    Returns:
        Dict con shape compute_line_total: {subtotal, tax, total, discount,
        extras_breakdown, currency, ...}.
    """
    from database import products_collection, product_extras_collection
    from services.pricing import (
        compute_line_total,
        compute_rental_multiplier,
        PricingError,
    )
    from routers.public import _resolve_org

    apply_api_version(request, response)

    # Resolve org + multi-tenant scope per product
    org = await _resolve_org(slug)
    org_id = org["id"]

    product = await products_collection.find_one(
        {
            "id": body.product_id,
            "organization_id": org_id,
            "is_active": True,
            "is_published": True,
        },
        {
            "_id": 0, "unit_price": 1, "item_type": 1, "name": 1,
            "organization_id": 1, "metadata": 1,
        },
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    extras_catalog = await product_extras_collection.find(
        {
            "organization_id": org_id,
            "product_id": body.product_id,
            "is_active": True,
        },
        {"_id": 0},
    ).to_list(None)

    # Rental multiplier per flavor=range / flavor=slot
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

    # No cache — price preview must be fresh (extras change live)
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return result.to_dict()


# ── Step 14f — Shipping options embed-ready (E4.2) ─────────────────────


# R14 — modello shipping condiviso. `EmbedShippingOption` era un duplicato
# byte-per-byte di `PublicShippingOption` (stessi campi public-safe): id,
# label, description, base_price, free_shipping_threshold, sort_order. Alias
# invece di ri-dichiarare → un solo contratto, niente drift storefront↔embed.
from models.shipping_option import PublicShippingOption as EmbedShippingOption


class EmbedShippingOptionsResponse(BaseModel):
    """Response of GET /api/public/embed/shipping-options/{slug}."""
    options: List[EmbedShippingOption] = Field(default_factory=list)


@router.get(
    "/shipping-options/{slug}",
    response_model=EmbedShippingOptionsResponse,
    summary="Shipping options per store (widget checkout picker)",
)
@limiter.limit("30/minute", key_func=get_real_ip_with_slug)
async def get_embed_shipping_options(
    request: Request,
    response: Response,
    slug: str,
) -> EmbedShippingOptionsResponse:
    """Track E Step 4.2 — wrapper embed-ready di
    /api/public/shipping-options/{slug} con CORS dinamico + multi-tenant.

    Union of per-store options + org-global (store_id=null) options,
    filtered to is_active=True, sorted by (sort_order, label).

    Empty list = merchant non ha configurato shipping options. Widget
    deve mostrare "Nessuna opzione di spedizione configurata. Contatta
    il fornitore" + disable checkout per cart con physical products.

    Cache: 300s (shipping options changes raramente, no atomic state).
    """
    from routers.public import _resolve_org
    from services.shipping_service import resolve_shipping_options

    apply_api_version(request, response)

    org = await _resolve_org(slug)
    store = org.get("_store") or {}
    options = await resolve_shipping_options(
        org_id=org["id"], store_id=store.get("id") or "",
    )

    public_options = [
        EmbedShippingOption(
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
    response.headers["Cache-Control"] = "public, max-age=300"
    return EmbedShippingOptionsResponse(options=public_options)


# ── Step 14e — Coupon validate embed-ready (E4.1) ──────────────────────


class EmbedCouponValidateRequest(BaseModel):
    """Body of POST /api/public/embed/coupons/validate/{slug}.

    Track E Step 4.1 — dry-run validation per widget UI feedback.
    Customer inserisce codice nel checkout drawer → widget POSTa qui →
    response indica se valido + discount calcolato. NESSUN incremento
    usage server-side (dry-run). Il checkout reale (checkout/start)
    chiama validate_coupon (atomic increment) per evitare race condition
    su max_uses.
    """
    code: str = Field(min_length=1, max_length=30)
    # Subtotal corrente del cart (per applicare min_order_amount check +
    # computare discount). Client side computa da cart.subtotal_snapshot.
    subtotal: float = Field(ge=0)


class EmbedCouponValidateResponse(BaseModel):
    """Response shape — mirror di validate_coupon_dry_run return dict.

    On success: response 200 con {coupon_id, code, discount, discount_pct?,
    discount_amount?}. On invalid/expired/exhausted: response 400 con
    detail string leggibile (es. "Codice promo esaurito").
    """
    coupon_id: str
    code: str
    discount: float
    discount_pct: Optional[float] = None
    discount_amount: Optional[float] = None


@router.post(
    "/coupons/validate/{slug}",
    response_model=EmbedCouponValidateResponse,
    summary="Dry-run coupon validation per widget checkout drawer",
)
@limiter.limit("30/minute", key_func=get_real_ip_with_slug)
async def embed_coupon_validate(
    request: Request,
    response: Response,
    slug: str,
    body: EmbedCouponValidateRequest,
) -> EmbedCouponValidateResponse:
    """Track E Step 4.1 — Validate coupon (dry-run, no usage increment).

    Sicurezza
    ---------
    - CORS dinamico (rifiuta Origin non in allowed_origins)
    - Multi-tenant: validazione scope store via _resolve_org(slug)
    - Rate limit 30/min per (IP, slug) — anti-bruteforce su codici coupon
    - Dry-run: NESSUNA mutation server-side, idempotente

    Race condition note
    ===================
    Customer puo' vedere preview di coupon valido + esaurirsi tra preview
    e checkout. Il checkout reale (checkout/start → validate_coupon vera)
    rivalidera' con atomic increment + ritornera' error chiaro se nel
    frattempo il coupon e' esaurito.

    Args:
        slug: store slug
        body: {code, subtotal}

    Returns:
        EmbedCouponValidateResponse con discount calcolato.

    Raises:
        400: codice invalido / scaduto / esaurito / non valido per store
    """
    from routers.public import _resolve_org
    from routers.coupons import validate_coupon_dry_run

    apply_api_version(request, response)

    org = await _resolve_org(slug)
    org_id = org["id"]
    store_id = (org.get("_store") or {}).get("id")

    result = await validate_coupon_dry_run(
        org_id=org_id,
        code=body.code,
        subtotal=body.subtotal,
        store_id=store_id,
    )

    # No cache — coupon validity dipende da max_uses dinamico
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return EmbedCouponValidateResponse(**result)


# ── Step 15 — Cart aliases (POST/GET/PATCH/DELETE) ─────────────────────
#
# Questi handler riusano il `cart_service` esistente (stesse INV-CART-*
# invarianti, stessa multi-tenant safety, stesso snapshot pricing) con
# 2 differenze rispetto al legacy /api/public/cart/*:
#
#   1. `source="embed"` invece di `"storefront_classic"` per analytics
#   2. Cooperano con DynamicCORSMiddleware (Phase 0 Step 7) +
#      IdempotencyMiddleware (Phase 0 Step 8): Origin + slug header
#      + Idempotency-Key obbligatori per ogni POST/PATCH/DELETE
#
# Resto: pari pari al legacy. Pydantic models riutilizzati senza alias.


_EMBED_CART_SOURCE = "embed"


def _assert_cart_in_store(cart_doc: dict, org: dict) -> None:
    """B1 — Isolamento per-store del carrello.

    Un cart appartiene a UN solo store. Se il cart porta uno ``store_id`` e lo
    store risolto dallo slug della richiesta e' diverso, rispondiamo 404
    (uniforme, anti-enumeration) per impedire l'uso cross-store nella stessa org.

    Backward-compat (fail-safe): se il cart NON ha ``store_id`` (cart legacy /
    org-global) o lo store risolto non ha id, nessun blocco.
    """
    cart_store = cart_doc.get("store_id")
    resolved_store = (org.get("_store") or {}).get("id")
    if cart_store and resolved_store and cart_store != resolved_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart non trovato o scaduto.",
        )


@router.post(
    "/cart",
    response_model=CartResponse,
    summary="Create a new empty embed cart bound to a store",
)
@limiter.limit("30/minute", key_func=get_real_ip_with_slug)
async def create_embed_cart(
    request: Request,
    response: Response,
    body: CartCreate,
) -> CartResponse:
    """Crea un cart vuoto associato allo store (body.slug).

    A differenza del legacy /api/public/cart, il campo ``source`` del
    body viene **forzato** a ``"embed"`` lato server: l'attribution e'
    autoritativa (no spoof da parte del widget).
    """
    from services import cart_service
    from routers.public import _resolve_org
    from core.observability import metrics as _metrics

    # Track O Step E1.1 — apply API version
    apply_api_version(request, response)

    org = await _resolve_org(body.slug)
    org_id = org["id"]
    store_id = (org.get("_store") or {}).get("id")

    cart = await cart_service.create_empty_cart(
        organization_id=org_id,
        store_id=store_id,
        source=_EMBED_CART_SOURCE,
    )

    # NOTE: NON impostiamo il cart_id cookie per il flow embed.
    # Il widget cross-origin gestisce la persistenza lato JS
    # (es. localStorage prefixed per merchant slug) — i cookie
    # third-party non sono affidabili nei browser moderni con ITP.

    cart_doc = await cart_service.get_cart(cart.id, org_id)

    # Metric: cart create da source embed
    try:
        _metrics.record_cart_op(operation="create", status="success", source="embed")
    except Exception:
        pass

    return cart_service.build_response(cart_doc)


@router.get(
    "/cart/{cart_id}",
    response_model=CartResponse,
    summary="Read embed cart by id",
)
@limiter.limit("60/minute", key_func=get_real_ip_with_slug)
async def get_embed_cart(
    request: Request,
    response: Response,
    cart_id: str,
    slug: str = Query(..., min_length=3, max_length=50),
) -> CartResponse:
    """Read cart by id, multi-tenant scoped via slug → org_id."""
    from services import cart_service
    from routers.public import _resolve_org
    from core.observability import metrics as _metrics

    # Track O Step E1.1 — apply API version
    apply_api_version(request, response)

    org = await _resolve_org(slug)
    cart_doc = await cart_service.get_cart(cart_id, org["id"])
    if not cart_doc:
        try:
            _metrics.record_cart_op(operation="get", status="not_found", source="embed")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart non trovato o scaduto.",
        )

    # B1 — isolamento per-store
    _assert_cart_in_store(cart_doc, org)

    try:
        _metrics.record_cart_op(operation="get", status="success", source="embed")
    except Exception:
        pass

    return cart_service.build_response(cart_doc)


@router.patch(
    "/cart/{cart_id}",
    response_model=CartResponse,
    summary="Update embed cart items + optionally bind customer_email",
)
@limiter.limit("30/minute", key_func=get_real_ip_with_slug)
async def update_embed_cart(
    request: Request,
    response: Response,
    cart_id: str,
    body: CartUpdate,
    slug: str = Query(..., min_length=3, max_length=50),
) -> CartResponse:
    """Update items + optional customer_email bind.

    Stesso contract del legacy /api/public/cart/{cart_id} PATCH:
    - items list completa sostituisce gli items esistenti
    - quantity=0 in input rimuove la riga
    - INV-CART-2 multi-tenant scoping garantito da cart_service.
    """
    from services import cart_service
    from routers.public import _resolve_org
    from core.observability import metrics as _metrics

    # Track O Step E1.1 — apply API version
    apply_api_version(request, response)

    org = await _resolve_org(slug)
    org_id = org["id"]

    existing = await cart_service.get_cart(cart_id, org_id)
    if not existing:
        try:
            _metrics.record_cart_op(operation="update", status="not_found", source="embed")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart non trovato o scaduto.",
        )

    # B1 — isolamento per-store
    _assert_cart_in_store(existing, org)

    updated_doc = existing

    if body.items is not None:
        # Track E Step 1.2 — map InsufficientStockError → HTTP 409 con
        # detail strutturato (code, product_id, requested, available).
        # Caller embed widget UI mostra al customer quale product e'
        # problematic + qual'e' la disponibilita' reale.
        from core.inventory_check import InsufficientStockError
        try:
            updated_doc = await cart_service.update_cart_items(
                cart_id=cart_id,
                organization_id=org_id,
                items_input=body.items,
            )
        except InsufficientStockError as stock_err:
            try:
                _metrics.record_cart_op(
                    operation="update", status="stock_rejected", source="embed",
                )
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=stock_err.to_detail(),
            )

    if body.customer_email:
        updated_doc = await cart_service.bind_customer_email(
            cart_id=cart_id,
            organization_id=org_id,
            customer_email=body.customer_email,
            customer_name=None,
            customer_phone=None,
        )

    try:
        _metrics.record_cart_op(operation="update", status="success", source="embed")
    except Exception:
        pass

    return cart_service.build_response(updated_doc or existing)


@router.delete(
    "/cart/{cart_id}",
    summary="Clear (soft) or hard-delete an embed cart",
)
@limiter.limit("30/minute", key_func=get_real_ip_with_slug)
async def clear_embed_cart(
    request: Request,
    response: Response,
    cart_id: str,
    slug: str = Query(..., min_length=3, max_length=50),
    hard: bool = Query(
        default=False,
        description="True = hard delete; False (default) = clear items only",
    ),
):
    """Clear cart items (default) o hard-delete.

    Per il widget embed niente cookie da pulire (non li usiamo, vedi
    note in create_embed_cart). Hard delete rimuove fisicamente il doc.
    """
    from services import cart_service
    from routers.public import _resolve_org
    from core.observability import metrics as _metrics

    # Track O Step E1.1 — apply API version
    apply_api_version(request, response)

    org = await _resolve_org(slug)
    org_id = org["id"]

    # B1 — isolamento per-store: se il cart esiste ma e' di un altro store, 404.
    _existing = await cart_service.get_cart(cart_id, org_id)
    if _existing:
        _assert_cart_in_store(_existing, org)

    if hard:
        from repositories import cart_repository
        ok = await cart_repository.delete_by_id(cart_id, org_id)
        if not ok:
            try:
                _metrics.record_cart_op(operation="delete", status="not_found", source="embed")
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart non trovato.",
            )
        try:
            _metrics.record_cart_op(operation="delete", status="success", source="embed")
        except Exception:
            pass
        return {"deleted": True, "cart_id": cart_id}

    # Soft: clear items only
    updated = await cart_service.clear_cart(cart_id, org_id)
    if not updated:
        try:
            _metrics.record_cart_op(operation="clear", status="not_found", source="embed")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart non trovato.",
        )

    try:
        _metrics.record_cart_op(operation="clear", status="success", source="embed")
    except Exception:
        pass

    return cart_service.build_response(updated)


# ── Step 18b — POST /embed/cart/{cart_id}/merge ─────────────────────────
#
# Lega un cart anonymous (creato come guest via /embed/cart) a un
# customer account già autenticato (Bearer JWT). Use case:
#   1. Visitor arriva su sito merchant, aggiunge prodotti al cart (guest)
#   2. Mid-cart decide di loggarsi via <afianco-login>
#   3. Widget chiama /embed/cart/{cart_id}/merge con Bearer token
#   4. Backend lega il cart all'account → cross-device retrieval abilitato
#
# Pattern replica il legacy POST /api/public/cart/{cart_id}/merge ma
# coperto da DynamicCORS + Idempotency middleware (parent /embed/* scope).


@router.post(
    "/cart/{cart_id}/merge",
    response_model=CartResponse,
    summary="Bind anonymous embed cart to authenticated customer account",
)
@limiter.limit("10/minute", key_func=get_real_ip_with_slug)
async def merge_embed_cart(
    request: Request,
    response: Response,
    cart_id: str,
    body: CartMergeRequest,
    slug: str = Query(..., min_length=3, max_length=50),
) -> CartResponse:
    """Merge guest cart → customer account.

    Auth
    ----
    Required: ``Authorization: Bearer <customer JWT>`` header.
    Validations:
      - 401 se Bearer mancante
      - 401 se token type != "customer"
      - 403 se token org_id != slug.organization_id
      - 403 se token.sub != body.customer_account_id (anti session-fixation)

    Multi-tenant
    ------------
    - Cart deve appartenere alla stessa org del slug.
    - Customer account deve appartenere alla stessa org.
    - 404 se cart non trovato (no leak di esistenza cross-tenant).
    """
    from auth import decode_token
    from routers.public import _resolve_org
    from services import cart_service
    from core.observability import metrics as _metrics

    # Track O Step E1.1 — apply API version
    apply_api_version(request, response)

    org = await _resolve_org(slug)
    org_id = org["id"]

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token customer richiesto per merge cart.",
        )

    try:
        payload_jwt = decode_token(auth_header[7:].strip())
    except HTTPException:
        raise  # 401 invalid/expired pass-through

    if payload_jwt.get("type") != "customer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token type non valido.",
        )

    if payload_jwt.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token customer per organizzazione diversa.",
        )

    if payload_jwt.get("sub") != body.customer_account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token customer non corrisponde all'account richiesto.",
        )

    # Verifica che il cart appartenga a questa org PRIMA del merge
    existing = await cart_service.get_cart(cart_id, org_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart non trovato o scaduto.",
        )

    # B1 — isolamento per-store
    _assert_cart_in_store(existing, org)

    # B9 — non assorbire un cart gia' associato a un ALTRO cliente
    existing_owner = existing.get("customer_account_id")
    if existing_owner and existing_owner != body.customer_account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cart gia' associato a un altro account.",
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

    try:
        _metrics.record_cart_op(operation="merge", status="success", source="embed")
    except Exception:
        pass

    return cart_service.build_response(updated)


# ── Step 16 — POST /embed/checkout/start ───────────────────────────────


@router.post(
    "/checkout/start",
    response_model=EmbedCheckoutStartResponse,
    summary="Convert embed cart to order + Stripe Checkout URL (Stream A)",
)
@limiter.limit("10/minute", key_func=get_real_ip_with_slug)
async def start_embed_checkout(
    request: Request,
    response: Response,
    body: EmbedCheckoutStartRequest,
) -> EmbedCheckoutStartResponse:
    """Convert an embed cart into an order, ready for payment/confirmation.

    Flow
    ----
    1. Resolve store via ``_resolve_org(body.slug)``.
    2. Validate ``embed_return_url`` against ``store.allowed_origins[]``
       (anti-phishing).
    3. Load cart by id, verify org match (anti-cross-tenant).
    4. Build ``OrderRequestPayload`` from cart items + body GDPR fields.
    5. Call ``submit_order_from_storefront`` with the cart_id so the
       resulting order is linked to the cart (Phase 0 Step 5).
       The service:
         · validates products, T&C, GDPR consent
         · creates the order (source="embed" derived from cart.source)
         · attempts Stripe Checkout creation if applicable
         · stamps GDPR snapshot + consent_audit records
    6. Persist ``embed_return_url`` on the order (``embed_metadata`` field)
       so Step 17 (postMessage bridge) can read it at completion time.
    7. Return order_id + payment_checkout_url + echo embed_return_url.

    Errors
    ------
    - 400 ``return_url_rejected``  if embed_return_url not allowed
    - 400 ``cart_empty`` if cart has 0 items
    - 403 ``cart_cross_tenant``    if cart_id belongs to another org
    - 400 anything raised by ``submit_order_from_storefront`` (GDPR
      missing, products unavailable, ecc.) — pass-through.
    - 429 rate limit (10/min)
    """
    from routers.public import (
        _resolve_org,
        _find_or_create_customer,
        OrderRequestPayload,
        OrderRequestItem,
    )
    from services import cart_service
    from services.order_creation_service import submit_order_from_storefront
    from services.embed_init_service import validate_embed_return_url
    from core.observability import metrics as _metrics

    # Track O Step E1.1 — apply API version
    apply_api_version(request, response)

    slug = body.slug

    # ── Resolve org ──
    org = await _resolve_org(slug)
    org_id = org["id"]
    resolved_store = org.get("_store") or {}
    allowed_origins = resolved_store.get("allowed_origins") or []

    # ── INV-EXO-1: embed_return_url allowlist guard ──
    if not validate_embed_return_url(body.embed_return_url, allowed_origins):
        try:
            _metrics.record_embed_checkout_start(slug=slug, outcome="return_url_rejected")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "return_url_rejected",
                "message": (
                    "embed_return_url non e' nella allowlist per questo store. "
                    "Il merchant deve aggiungere l'origin di destinazione in "
                    "store.allowed_origins prima che il widget possa redirect."
                ),
            },
        )

    # ── Load cart + verify multi-tenant scoping ──
    cart_doc = await cart_service.get_cart(body.cart_id, org_id)
    if not cart_doc:
        # Non riveliamo se il cart non esiste o appartiene ad altra org →
        # response uniforme per non leak cross-tenant.
        try:
            _metrics.record_embed_checkout_start(slug=slug, outcome="cart_cross_tenant")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart non trovato o scaduto.",
        )

    # B1 — isolamento per-store: il cart deve appartenere allo store dello slug.
    _assert_cart_in_store(cart_doc, org)

    cart_items = cart_doc.get("items") or []
    if not cart_items:
        try:
            _metrics.record_embed_checkout_start(slug=slug, outcome="cart_empty")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart e' vuoto — aggiungi almeno un prodotto prima del checkout.",
        )

    # ── Build OrderRequestPayload from cart items (parity con legacy) ──
    order_items: List[OrderRequestItem] = []
    for item in cart_items:
        order_items.append(OrderRequestItem(
            product_id=item.get("product_id"),
            quantity=float(item.get("quantity") or 0),
            occurrence_id=item.get("occurrence_id"),
            ticket_tier_id=item.get("ticket_tier_id"),
            rental_date_from=item.get("rental_date_from"),
            rental_date_to=item.get("rental_date_to"),
            rental_notes=item.get("rental_notes"),
            booking_date=item.get("booking_date"),
            booking_start_time=item.get("booking_start_time"),
            booking_end_time=item.get("booking_end_time"),
            booking_end_date=item.get("booking_end_date"),
            attendees=item.get("attendees"),
            service_option_id=item.get("service_option_id"),
            service_custom_request=bool(item.get("service_custom_request", False)),  # R4
            extra_selections=item.get("extra_selections"),  # R2
        ))

    # Track E Step 3.2/3.3 — propaga order_fields + shipping_address_details
    # + shipping_option_* dal embed widget al OrderRequestPayload.
    # Backend service order-creation li valida (es. order_fields required
    # check, shipping address required se fulfillment=shipping + physical).
    payload_kwargs: dict = {
        "slug": slug,
        "customer_name": body.customer_name,
        "customer_email": body.customer_email,
        "customer_phone": body.customer_phone,
        "items": order_items,
        "notes": body.notes,
        "fulfillment_mode": body.fulfillment_mode,
        "terms_accepted": body.terms_accepted,
        "gdpr_terms_accepted": body.gdpr_terms_accepted,
        "gdpr_privacy_accepted": body.gdpr_privacy_accepted,
        "gdpr_marketing_accepted": body.gdpr_marketing_accepted,
    }
    if body.order_fields:
        payload_kwargs["order_fields"] = body.order_fields
    if body.shipping_address_details:
        payload_kwargs["shipping_address_details"] = body.shipping_address_details
    if body.shipping_option_id:
        payload_kwargs["shipping_option_id"] = body.shipping_option_id
    if body.shipping_option_label:
        payload_kwargs["shipping_option_label"] = body.shipping_option_label
    # Track E Step 4.1 — coupon code propagation
    if body.coupon_code:
        payload_kwargs["coupon_code"] = body.coupon_code

    payload = OrderRequestPayload(**payload_kwargs)

    # ── Extract IP + UA for consent_audit trail (GDPR proof) ──
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # ── Step 18a/18c: resolve customer_account_id (3 auth modes) ──
    #
    # Mode 1 — Guest checkout (default):
    #   no Authorization header, no create_account flag → customer_account_id=None
    # Mode 2 — Authenticated (Bearer JWT):
    #   Authorization: Bearer <customer JWT> → decode + validate type='customer'
    #   + org_id match → customer_account_id from JWT payload.sub
    # Mode 3 — Signup inline (Step 18c):
    #   create_account=True + account_password set → customer_signup(auto_login=True)
    #   → ottieni nuovo customer_account_id (+ token, ritornato al widget)
    #
    # Bearer JWT ha precedenza su create_account: se il widget passa entrambi,
    # interpretiamo come "gia' autenticato, ignora richiesta signup" — il
    # frontend dovrebbe filtrare a monte ma il backend è defensivo.

    customer_account_id: Optional[str] = None
    inline_signup_token: Optional[str] = None  # ritornato al widget per uso futuro

    # ── Mode 2: optional Bearer JWT ──
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        from auth import decode_token
        token_str = auth_header[7:].strip()
        try:
            payload_jwt = decode_token(token_str)
        except HTTPException:
            # decode_token raises 401 on invalid/expired — bubble up
            try:
                _metrics.record_embed_checkout_start(slug=slug, outcome="bearer_invalid")
            except Exception:
                pass
            raise
        if payload_jwt.get("type") != "customer":
            try:
                _metrics.record_embed_checkout_start(slug=slug, outcome="bearer_type_mismatch")
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token type non valido per checkout embed.",
            )
        if payload_jwt.get("org_id") != org_id:
            try:
                _metrics.record_embed_checkout_start(slug=slug, outcome="bearer_cross_tenant")
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token customer per organizzazione diversa.",
            )
        customer_account_id = payload_jwt.get("sub")
        logger.info(
            "embed_checkout: authenticated mode account=%s org=%s",
            customer_account_id, org_id,
        )

    # ── Mode 3: inline signup (only if NOT already authenticated) ──
    elif body.create_account:
        if not body.account_password:
            try:
                _metrics.record_embed_checkout_start(slug=slug, outcome="signup_password_missing")
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "account_password e' richiesto quando create_account=True. "
                    "Il widget deve raccogliere la password prima del checkout."
                ),
            )
        # Inline signup richiede gli stessi GDPR flags del signup standalone.
        # I customer_signup li ricontrolla, ma falliamo qui per dare errore
        # piu' chiaro al widget.
        if not body.gdpr_terms_accepted or not body.gdpr_privacy_accepted:
            try:
                _metrics.record_embed_checkout_start(slug=slug, outcome="signup_gdpr_missing")
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Per creare un account devi accettare Privacy Policy + "
                    "Termini di Servizio (gdpr_privacy_accepted + "
                    "gdpr_terms_accepted)."
                ),
            )

        from services.customer_auth_service import customer_signup as _customer_signup
        try:
            signup_result = await _customer_signup(
                org_id=org_id,
                email=body.customer_email,
                name=body.customer_name,
                password=body.account_password,
                locale=body.account_locale or "it",
                auto_login=True,  # mint token immediato, bypass email verification
                signup_slug=slug,
                accepted_terms=bool(body.gdpr_terms_accepted),
                accepted_privacy=bool(body.gdpr_privacy_accepted),
                accepted_marketing=bool(body.gdpr_marketing_accepted),
                request_ip=client_ip,
                user_agent=user_agent,
            )
        except ValueError as exc:
            # customer_signup raises ValueError per duplicate email, weak
            # password, missing GDPR docs, ecc.
            try:
                _metrics.record_embed_checkout_start(slug=slug, outcome="signup_failed")
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )
        # Recupera account id + token (auto_login=True garantisce entrambi)
        cust = signup_result.get("customer") or {}
        customer_account_id = cust.get("id")
        inline_signup_token = signup_result.get("access_token")

        # Lega il cart anonimo al nuovo account (Step 18b semantica inline)
        if customer_account_id:
            try:
                await cart_service.merge_anonymous_to_account(
                    cart_id=body.cart_id,
                    organization_id=org_id,
                    customer_account_id=customer_account_id,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "embed_checkout: cart→account merge soft-fail account=%s: %s",
                    customer_account_id, exc,
                )

        try:
            _metrics.record_embed_checkout_start(slug=slug, outcome="account_created")
        except Exception:
            pass
        logger.info(
            "embed_checkout: signup-inline created account=%s org=%s",
            customer_account_id, org_id,
        )

    # ── Customer upsert (CRM record) ──
    # When customer_account_id is set (Mode 2 or 3), upsert_by_email links the
    # CRM customer row to that account for future portal access.
    customer_id = await _find_or_create_customer(
        org_id=org_id,
        name=body.customer_name,
        email=body.customer_email,
        phone=body.customer_phone,
        customer_account_id=customer_account_id,
    )

    # ── Delegate to canonical pipeline ──
    # source="embed" e' propagato via cart_doc.source = "embed" (settato
    # da create_embed_cart in Step 15). submit_order_from_storefront
    # legge cart.source quando cart_id e' provided.
    try:
        result = await submit_order_from_storefront(
            org=org,
            body=payload,
            customer_account_id=customer_account_id,
            customer_id=customer_id,
            client_ip=client_ip,
            user_agent=user_agent,
            cart_id=body.cart_id,
        )
    except HTTPException as exc:
        try:
            _metrics.record_embed_checkout_start(slug=slug, outcome="order_failed")
        except Exception:
            pass
        raise
    except Exception as exc:  # pragma: no cover
        logger.error("embed_checkout: unhandled exception org=%s: %s", org_id, exc, exc_info=True)
        try:
            _metrics.record_embed_checkout_start(slug=slug, outcome="order_failed")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nella creazione dell'ordine.",
        )

    # ── Persist embed_return_url on order (per Step 17 bridge) ──
    # Soft-fail: il return_url stamping non blocca il flow.
    try:
        from database import orders_collection
        await orders_collection.update_one(
            {"id": result.get("order_id"), "organization_id": org_id},
            {"$set": {
                "embed_metadata.return_url": body.embed_return_url,
                "embed_metadata.source": "embed",
            }},
        )
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "embed_checkout: failed to stamp embed_return_url on order=%s: %s",
            result.get("order_id"), exc,
        )

    try:
        _metrics.record_embed_checkout_start(slug=slug, outcome="success")
    except Exception:
        pass

    return EmbedCheckoutStartResponse(
        order_id=result["order_id"],
        transaction_mode=result.get("transaction_mode", "request"),
        order_status=result.get("order_status", "draft"),
        message=result.get("message", ""),
        payment_checkout_url=result.get("payment_checkout_url"),
        payment_reason=result.get("payment_reason"),
        embed_return_url=body.embed_return_url,
        # Step 18c: surface token + flag al widget se signup inline ha avuto luogo
        customer_access_token=inline_signup_token,
        account_created=inline_signup_token is not None,
    )


# ── Step 17 — GET /embed/checkout/complete (postMessage bridge) ────────


@router.get(
    "/checkout/complete",
    summary="postMessage bridge HTML for embed checkout return",
    include_in_schema=True,
)
@limiter.limit("60/minute", key_func=get_real_ip_with_slug)
async def embed_checkout_complete(
    request: Request,
    order_id: str = Query(..., min_length=1, max_length=64),
):
    """HTML bridge page rendered when the customer returns from Stripe
    Checkout (popup flow) to an embed widget on a third-party domain.

    The page contains an inline ``<script>`` that calls
    ``window.opener.postMessage(...)`` (or ``window.parent.postMessage``
    if the bridge is mounted in an iframe) so the merchant widget on
    the parent page receives ``{source: 'afianco-embed', order_id,
    order_status, payment_status}`` and can close the popup.

    Security
    --------
    - ``order_id`` must resolve to an order with
      ``embed_metadata.return_url`` set. Otherwise 404 — no leak of
      legacy / non-embed orders.
    - Target origin is DERIVED server-side from the stored return_url.
      The browser ignores postMessage to mismatched origins; we also
      pin via sentinel that the handler never reads it from query.
    - ``order_id`` and status fields are JSON-escaped before embedding
      in the JS string literal (anti-XSS), with an extra ``</`` →
      ``<\\/`` pass to defeat ``</script>`` termination attacks.
    - ``Content-Security-Policy: frame-ancestors 'none'`` prevents the
      bridge from being embedded inside a hostile iframe (clickjacking).
    - ``Cache-Control: no-store`` because the response carries order
      state — CDN caching would risk serving wrong customer's status.
    - ``Referrer-Policy: no-referrer`` so the merchant's domain never
      leaks to afianco when the user clicks any future link.

    Rate limit 60/min/IP (bridge is a 1-shot page per checkout).
    """
    from fastapi.responses import HTMLResponse
    from services.embed_init_service import get_embed_complete_payload
    from core.observability import metrics as _metrics

    payload = await get_embed_complete_payload(order_id=order_id)

    # Slug for metric label — best-effort lookup; "unknown" otherwise.
    slug_label = "unknown"

    if not payload:
        # Unified 404: legacy order, missing order, or malformed metadata.
        # We do NOT distinguish in the response — anti enumeration leak.
        try:
            _metrics.record_embed_postmessage_bridge(slug=slug_label, status="not_found")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Embed checkout complete payload not found for this order.",
        )

    # Optional: enrich slug label from order doc if available (soft-fail)
    try:
        from database import orders_collection
        order = await orders_collection.find_one(
            {"id": order_id},
            {"_id": 0, "organization_id": 1, "_store": 1, "store_id": 1},
        )
        if order:
            # Resolve slug from store_id if set (multi-store)
            sid = order.get("store_id")
            if sid:
                from database import stores_collection
                store = await stores_collection.find_one(
                    {"id": sid}, {"_id": 0, "slug": 1}
                )
                if store and store.get("slug"):
                    slug_label = store["slug"]
    except Exception:
        pass

    try:
        _metrics.record_embed_postmessage_bridge(slug=slug_label, status="served")
    except Exception:
        pass

    response = HTMLResponse(
        content=payload["html"],
        status_code=200,
    )
    # Track O Step E1.1 — apply API version (set X-API-Version + validate
    # request header). Helper accept Response, HTMLResponse is subclass.
    apply_api_version(request, response)
    # ── Security headers ──
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    # frame-ancestors 'none' = anti-clickjacking. Le `script-src 'unsafe-inline'`
    # è necessario perché lo script postMessage e' inline (nessun fetch external).
    # default-src 'self' + img-src 'self' impediscono qualsiasi altro external load.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'unsafe-inline'; "
        "style-src 'unsafe-inline'; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'; "
        "base-uri 'none'; "
        "form-action 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


# ── Newsletter form submit (F1, modulo Newsletter) ──────────────────────────
#
# Endpoint PUBBLICO di iscrizione via form embeddato. Il form è risolto per
# `form_id` (uuid globalmente unico e non indovinabile, coerente con
# `afianco-product product-id`); lo slug per-org resta solo un'etichetta admin.
#
# Flusso: honeypot → risolvi form attivo → consenso → upsert customer org-scoped
# → opt-in marketing via servizio condiviso (record_marketing_optin) → upsert
# subscription (dedup per email) con tracciamento sorgente (D7). Best-effort
# sull'opt-in/first-touch: la subscription resta il record durevole.
#
# CORS cross-origin per il browser: agganciato in F2 (dynamic_cors risolve il
# form_id → form.allowed_origins). Server-side l'endpoint è già funzionante.

@router.get(
    "/newsletter/{form_id}",
    response_model=NewsletterFormPublic,
    summary="Config pubblica del form newsletter (per il render embed)",
)
@limiter.limit("60/minute", key_func=get_real_ip_with_slug)
async def get_newsletter_form_public(
    request: Request,
    response: Response,
    form_id: str,
) -> NewsletterFormPublic:
    from database import newsletter_forms_collection

    apply_api_version(request, response)
    form = await newsletter_forms_collection.find_one(
        {"id": form_id, "is_active": True},
        {
            "_id": 0, "id": 1, "organization_id": 1, "name": 1,
            "collect_name": 1, "collect_phone": 1, "field_configs": 1,
            "consent_text": 1, "privacy_required": 1, "success_message": 1,
            "redirect_url": 1, "theme": 1, "privacy_mode": 1,
            "privacy_store_id": 1, "privacy_custom_url": 1, "layout": 1,
        },
    )
    if not form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form non trovato")

    # F7 — risolvi l'URL privacy da linkare nel consenso (riusa il pattern
    # dell'embed init: store esistente → /s/{slug}/privacy; custom → URL).
    privacy_url = await _resolve_newsletter_privacy_url(form)

    # Cache breve CDN-friendly: la config cambia di rado (azione admin).
    response.headers["Cache-Control"] = "public, max-age=120"
    return NewsletterFormPublic(
        id=form["id"],
        name=form.get("name", ""),
        collect_name=bool(form.get("collect_name")),
        collect_phone=bool(form.get("collect_phone")),
        field_configs=form.get("field_configs") or [],
        consent_text=form.get("consent_text"),
        privacy_required=form.get("privacy_required", True),
        success_message=form.get("success_message"),
        redirect_url=form.get("redirect_url"),
        layout=form.get("layout") or "vertical",
        theme=form.get("theme"),
        privacy_policy_url=privacy_url,
    )


async def _resolve_newsletter_privacy_url(form: dict) -> Optional[str]:
    """F7 — URL della privacy policy da linkare nel consenso del form.

    - mode='custom' → URL inserito dall'utente;
    - mode='store'  → privacy pubblica dello store scelto (riusa il route
      pubblico esistente {APP_BASE_URL}/s/{slug}/privacy, già servito da
      routers/legal.py — nessuna duplicazione);
    - mode='none'   → nessun link.
    """
    mode = form.get("privacy_mode") or "none"
    if mode == "custom":
        from models.newsletter import normalize_external_url
        return normalize_external_url(form.get("privacy_custom_url"))
    if mode == "store":
        store_id = form.get("privacy_store_id")
        if not store_id:
            return None
        from database import stores_collection
        store = await stores_collection.find_one(
            {"id": store_id, "organization_id": form.get("organization_id")},
            {"_id": 0, "slug": 1},
        )
        if store and store.get("slug"):
            from core.embed_distribution import APP_BASE_URL
            return f"{APP_BASE_URL}/s/{store['slug']}/privacy"
    return None


@router.post(
    "/newsletter/{form_id}/submit",
    response_model=NewsletterSubmitResponse,
    summary="Iscrizione pubblica via form newsletter embeddato",
)
@limiter.limit("30/minute", key_func=get_real_ip_with_slug)
async def submit_newsletter_form(
    request: Request,
    response: Response,
    form_id: str,
    body: NewsletterSubmitRequest,
) -> NewsletterSubmitResponse:
    from database import (
        newsletter_forms_collection,
        newsletter_subscriptions_collection,
        customers_collection,
    )
    from repositories import customer_repository
    from services.marketing_consent_service import record_marketing_optin
    from models.common import generate_id, utc_now

    apply_api_version(request, response)

    # Honeypot: campo invisibile compilato → bot → fingiamo successo, scartiamo.
    if body.hp:
        return NewsletterSubmitResponse(success=True, message="ok")

    form = await newsletter_forms_collection.find_one(
        {"id": form_id, "is_active": True}, {"_id": 0},
    )
    if not form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form non trovato")
    org_id = form["organization_id"]

    if form.get("privacy_required", True) and not body.consent_privacy:
        raise HTTPException(status_code=400, detail="Consenso privacy richiesto")

    email = body.email.strip().lower()

    # Sorgente (D7): server (trust anchor) + client.
    origin_hdr = request.headers.get("origin")
    referer_hdr = request.headers.get("referer")
    ua = request.headers.get("user-agent")
    ip = get_real_ip(request)

    # Upsert customer org-scoped (un iscritto = riga CRM, anche senza acquisti).
    customer_id, _ = await customer_repository.upsert_by_email(
        org_id,
        name=(body.name or "").strip(),
        email=email,
        phone=body.phone,
        source="newsletter_form",
    )

    # First-touch attribution sul customer (solo se assente: non sovrascrive).
    try:
        first_touch = body.source_label or origin_hdr or body.source_url
        if first_touch:
            await customers_collection.update_one(
                {
                    "id": customer_id,
                    "organization_id": org_id,
                    "metadata.acquisition_source": {"$exists": False},
                },
                {"$set": {"metadata.acquisition_source": first_touch}},
            )
    except Exception as exc:  # best-effort
        logger.warning("newsletter submit: acquisition_source set failed: %s", exc)

    # Opt-in marketing via servizio condiviso (best-effort: non blocca l'iscrizione).
    try:
        await record_marketing_optin(
            organization_id=org_id,
            customer_id=customer_id,
            store_id=form.get("store_id"),
            email=email,
            source="customer_marketing_optin",
            ip_address=ip,
            user_agent=ua,
        )
    except Exception as exc:
        logger.warning(
            "newsletter submit: marketing optin failed form=%s: %s", form_id, exc,
        )

    # Upsert subscription (dedup per (org, form, email)) + sorgente.
    now = utc_now().isoformat()
    sub_set = {
        "organization_id": org_id,
        "form_id": form_id,
        "email": email,
        "name": body.name,
        "phone": body.phone,
        "fields_data": body.fields_data or {},
        "status": "confirmed",
        "customer_id": customer_id,
        "source_url": body.source_url,
        "source_origin": origin_hdr,
        "source_referrer": body.source_referrer,
        "source_referrer_server": referer_hdr,
        "source_label": body.source_label,
        "ip_address": ip,
        "user_agent": ua,
        "updated_at": now,
    }
    doc = await newsletter_subscriptions_collection.find_one_and_update(
        {"organization_id": org_id, "form_id": form_id, "email": email},
        {"$set": sub_set, "$setOnInsert": {"id": generate_id(), "created_at": now}},
        upsert=True,
        return_document=True,
    )
    subscriber_id = doc.get("id") if doc else None

    msg = form.get("success_message") or "Iscrizione completata. Grazie!"
    return NewsletterSubmitResponse(success=True, message=msg, subscriber_id=subscriber_id)
