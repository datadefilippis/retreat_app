"""
ShippingOption — admin-configured shipping method for the storefront.

Introduced to let merchants offer multiple, priced shipping modes at
checkout (e.g. "Corriere espresso 24h €9.90", "Corriere standard €4.90
gratis sopra €50") instead of the single free-form `shipping_address`
today's checkout captures.

SCOPE
  - `organization_id`: always required. Every option belongs to one org.
  - `store_id`: nullable.
      - When set: the option is visible only in THAT store's checkout.
      - When null: the option is a *global* org-level option, visible in
        every store of that org (unless overridden store-side with a
        same-label option — but there's no uniqueness constraint, the
        admin picks labels carefully).

PRICING MODEL (v1, flat + free-shipping threshold)
  - `base_price`: flat fee applied to the order when this option is chosen.
  - `free_shipping_threshold`: optional EUR amount. When the PHYSICAL-items
    subtotal of the cart is >= threshold, the effective shipping cost is
    €0. Otherwise it's `base_price`.
  - Future extensions (per-zone, per-weight, carrier integration) fit here
    without breaking the v1 payload — add new optional fields.

Collection: `shipping_options_collection` (see database.py).
Indexed by (organization_id, store_id, sort_order) for fast per-store
resolution at public checkout time, and (organization_id, is_active) for
admin listing.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime

from .common import generate_id, utc_now


class ShippingOptionBase(BaseModel):
    """Fields shared by create/update contracts."""
    label: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    base_price: float = Field(ge=0)
    # None = no free-shipping threshold. When set, reaching the physical
    # subtotal makes the effective shipping cost €0 for this option.
    free_shipping_threshold: Optional[float] = Field(default=None, ge=0)
    # CH compliance v1 — optional override; resolved via
    # services.currency_service to the org currency when None.
    currency: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

    @field_validator('currency', mode='before')
    @classmethod
    def validate_currency(cls, v):
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


class ShippingOption(ShippingOptionBase):
    """Full ShippingOption document as stored in MongoDB."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    # None → global (all stores of the org). Non-null → limited to that store.
    store_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ShippingOptionCreate(ShippingOptionBase):
    """Input model for POST /api/shipping-options.

    store_id is part of the body (not the URL) because we need to
    distinguish global vs per-store creation from a single endpoint.
    """
    store_id: Optional[str] = None


class ShippingOptionUpdate(BaseModel):
    """Partial update for PATCH /api/shipping-options/{id}.

    Every field is optional. `store_id` is intentionally NOT updatable
    after creation — to "move" an option between scopes, delete and
    recreate. This prevents silent scope changes that would confuse
    already-placed orders referencing the option via snapshot.
    """
    model_config = ConfigDict(extra="ignore")

    label: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    base_price: Optional[float] = Field(default=None, ge=0)
    free_shipping_threshold: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator('currency', mode='before')
    @classmethod
    def validate_currency(cls, v):
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


class ShippingOptionResponse(ShippingOptionBase):
    """Admin response shape — echoes the full document."""
    model_config = ConfigDict(extra="ignore")

    id: str
    organization_id: str
    store_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PublicShippingOption(BaseModel):
    """Slimmed-down public shape returned by the storefront endpoint.

    Admin-only fields (created_at, is_active, organization_id) are
    intentionally stripped.
    """
    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    description: Optional[str] = None
    base_price: float
    free_shipping_threshold: Optional[float] = None
    sort_order: int = 0
