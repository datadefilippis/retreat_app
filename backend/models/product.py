from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from .common import generate_id, utc_now
from .product_types import PRODUCT_TYPE_KEYS
from .offer_profiles import (
    OFFER_PROFILES,
    apply_profile_defaults,
    derive_profile_from_axes,
    validate_profile_id,
)
from .cost_source import CostSource

# ── Catalog item type constants ─────────────────────────────────────────────
# Historically this was a hardcoded tuple. It now derives from the central
# product_types registry so adding / removing a type is a one-line change
# there. The tuple shape is preserved for full backward compatibility with
# every caller that imports ITEM_TYPES directly from this module.
ITEM_TYPES = PRODUCT_TYPE_KEYS
PRICE_MODES = ("fixed", "inquiry")

# ── Transaction mode constants ─────────────────────────────────────────────
# Separates "what is sold" (item_type) from "how it transacts" (transaction_mode).
#   request  — visitor submits a request; admin confirms manually (current default)
#   direct   — visitor can complete the transaction directly (future: checkout/payment)
#   approval — like request, but signals heavier review (availability, custom quote)
TRANSACTION_MODES = ("request", "direct", "approval")


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sku: Optional[str] = Field(default=None, max_length=50)
    category: Optional[str] = None

    # Multilingua MANUALE (6/7/2026, decisione founder: zero LLM, zero
    # costi): l'operatore scrive le traduzioni che vuole offrire.
    # {"en": {"description": ..., "long_description": ...}, "de": ...}
    # Le lingue presenti = le lingue che l'operatore ACCETTA: nelle
    # viste in lingua X compaiono solo prodotti con la traduzione X
    # (l'italiano e' sempre disponibile).
    translations: Optional[dict] = None
    unit_price: Optional[float] = None
    # DEPRECATED (Wave 1, W1.S1): authoritative cost is now ``cost_source``
    # below. ``cost_price`` is retained for backward compatibility during
    # the migration window — the script
    # ``scripts/migrate_cost_price_to_components.py`` converts every
    # non-zero value into a single ``manual`` component on cost_source,
    # then this field becomes vestigial. Planned removal at the end of
    # Wave 1 once the new admin UI (W1.S5) is the only writer.
    cost_price: Optional[float] = None
    # ── Cost composition (Wave 1, W1.S1) ────────────────────────────────────
    # Optional container holding 0..N additive cost components (manual,
    # category-quantity, category-share, org-average). When present and
    # non-empty, this is the authoritative source for margin calculation
    # in product_catalog and for cost_at_sale snapshots on orders. See
    # ``models/cost_source.py`` for the full data model and the rationale
    # for the additive-components design.
    cost_source: Optional[CostSource] = None
    # CH compliance v1 — optional per-product currency override.
    # When None (the legacy default), reads fall back via
    # ``services.currency_service.get_currency_for_product`` to the
    # owning organization's currency, then to EUR. Set explicitly only
    # when this product's price is denominated in something different
    # from the org default — rare, but keeps the data model honest.
    currency: Optional[str] = None
    unit: Optional[str] = None           # e.g. "piece", "hour", "kg", "license"
    description: Optional[str] = None
    image_url: Optional[str] = None
    slug: Optional[str] = None
    is_published: bool = False

    # ── Catalog foundation (v8.0) ───────────────────────────────────────────
    item_type: str = "physical"          # physical | service | rental | event_ticket
    unit_label: Optional[str] = None     # display label: pz, servizio, giorno, posto
    price_mode: str = "fixed"            # fixed | inquiry
    transaction_mode: str = "request"    # request | direct | approval

    stock_quantity: Optional[int] = None   # null = no tracking; 0+ = tracked inventory
    tags: List[str] = []
    metadata: Dict[str, Any] = {}

    # P11: optional offer-profile identifier. When provided it MUST be
    # one of the registered profile ids; the three axes below are
    # auto-filled from the profile's defaults for any axis the client
    # left empty. When omitted, the product stores the three atomic
    # axes exactly as submitted (backward-compat: existing clients are
    # unaffected).
    offer_profile_id: Optional[str] = None

    @field_validator('offer_profile_id', mode='before')
    @classmethod
    def validate_offer_profile_id(cls, v):
        # Pass-through for None / empty string.
        if v is None or v == "":
            return None
        validate_profile_id(v)
        return v

    @field_validator('item_type', mode='before')
    @classmethod
    def validate_item_type(cls, v):
        if v and v not in ITEM_TYPES:
            raise ValueError(f'item_type must be one of {ITEM_TYPES}')
        return v or "physical"

    @field_validator('currency', mode='before')
    @classmethod
    def validate_currency(cls, v):
        """Restrict to ISO 4217 codes shipping today; None preserved.

        ``None`` and ``""`` mean *use the org's currency* (resolved at
        read-time via ``services.currency_service.get_currency_for_product``).
        Any explicit value must be supported.
        """
        if v is None or v == "":
            return None
        from services.currency_service import (
            UnsupportedCurrencyError,
            validate_currency_code,
        )
        try:
            return validate_currency_code(v)
        except UnsupportedCurrencyError as e:
            raise ValueError(str(e)) from e

    @field_validator('price_mode', mode='before')
    @classmethod
    def validate_price_mode(cls, v):
        if v and v not in PRICE_MODES:
            raise ValueError(f'price_mode must be one of {PRICE_MODES}')
        return v or "fixed"

    @field_validator('transaction_mode', mode='before')
    @classmethod
    def validate_transaction_mode(cls, v):
        if v and v not in TRANSACTION_MODES:
            raise ValueError(f'transaction_mode must be one of {TRANSACTION_MODES}')
        return v or "request"

    @model_validator(mode='before')
    @classmethod
    def apply_profile_id_defaults(cls, values):
        """P11: when offer_profile_id is provided, fill any missing axis
        from the profile's defaults so the three atomic fields stay
        authoritative and self-consistent.

        Clients that send all three axes explicitly are NOT overridden —
        their choice wins. Clients that send ONLY a profile_id get the
        three axes filled from the registry.
        """
        if not isinstance(values, dict):
            return values
        profile_id = values.get("offer_profile_id")
        if profile_id and profile_id in OFFER_PROFILES:
            values = apply_profile_defaults(profile_id, values)
        return values

    @model_validator(mode='after')
    def validate_config_compatibility(self):
        """Block contradictory configurations at save time."""
        if self.transaction_mode == 'direct' and self.price_mode == 'inquiry':
            raise ValueError(
                'Modalità diretta non compatibile con prezzo su richiesta. '
                'Il checkout richiede un prezzo definito.'
            )
        return self


class ProductCreate(ProductBase):
    store_ids: List[str] = Field(default_factory=list)  # v12.0: assign to specific stores


class ProductUpdate(BaseModel):
    """Pydantic model for PATCH /products/{id}.

    Only fields present in the request body are applied.
    System fields (id, organization_id, created_at) are intentionally absent.
    """
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    # Traduzioni manuali {lang: {description, long_description}} — la
    # whitelist (lingue/campi/lunghezze) e' in services/manual_translations.
    translations: Optional[Dict[str, Any]] = None
    unit_price: Optional[float] = None
    # DEPRECATED — see ProductBase for the rationale. Accepted on PATCH
    # only so existing clients keep working during the migration window;
    # new admin UI writes ``cost_source`` exclusively.
    cost_price: Optional[float] = None
    cost_source: Optional[CostSource] = None
    currency: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    slug: Optional[str] = None
    is_published: Optional[bool] = None
    item_type: Optional[str] = None
    unit_label: Optional[str] = None
    price_mode: Optional[str] = None
    transaction_mode: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    stock_quantity: Optional[int] = None    # null = no tracking; 0+ = tracked
    store_ids: Optional[List[str]] = None  # v12.0: assign to specific stores
    is_active: Optional[bool] = None
    # P11: update path accepts profile id too. Same validation contract
    # as ProductBase; unknown ids are rejected, known ids trigger axis
    # back-fill in the router/service layer.
    offer_profile_id: Optional[str] = None

    @field_validator('currency', mode='before')
    @classmethod
    def validate_currency_update(cls, v):
        """Mirror of ProductBase.validate_currency for the PATCH DTO."""
        if v is None or v == "":
            return None
        from services.currency_service import (
            UnsupportedCurrencyError,
            validate_currency_code,
        )
        try:
            return validate_currency_code(v)
        except UnsupportedCurrencyError as e:
            raise ValueError(str(e)) from e

    @field_validator('offer_profile_id', mode='before')
    @classmethod
    def validate_offer_profile_id_update(cls, v):
        if v is None or v == "":
            return None
        validate_profile_id(v)
        return v


class Product(ProductBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    store_ids: List[str] = Field(default_factory=list)  # v12.0: which stores this product appears in (empty = all stores)
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProductResponse(ProductBase):
    id: str
    organization_id: str
    store_ids: List[str] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime
