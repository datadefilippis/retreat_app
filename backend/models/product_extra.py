"""
ProductExtra — merchant-defined add-on for any commerce product.

Onda 16 (Prenotazione consolidation). Generalizes the ServiceOption
radio-only primitive into a richer add-on concept usable across
services, rentals (both range and slot flavors), and potentially
physical / event products.

Three kinds model the three distinct UX patterns the merchant needs:

  mandatory     — auto-applied to every order of this product, no
                  customer choice. Examples:
                    * B&B: "Pulizia finale" 30€ flat
                    * Car rental: "Assicurazione base obbligatoria" 10€/day

  optional      — customer opts in via checkbox. Multiple optional
                  extras can be selected at once. Examples:
                    * B&B: "Colazione" 12€/day
                    * Car rental: "GPS unit" 5€/day
                    * Service: "Report dettagliato" 20€ flat

  radio_variant — mutually exclusive pick within a group_key. Replaces
                  the legacy ServiceOption one-of-many UX. Examples:
                    * Car rental: insurance franchigia (Standard vs Zero)
                    * Service: package tier (30min vs 1h vs 3-session
                      bundle — currently ServiceOption)

PRICING MODIFIERS
  flat          — absolute EUR added once (default)
  per_day       — multiplied by the number of rental days (only meaningful
                  for reservation_flavor=range products)
  per_unit      — multiplied by the line quantity (for multi-qty lines)

BACKWARD COMPAT
  The existing service_options_collection stays queryable for one
  release. A shim in the router projects ProductExtra rows with
  kind=radio_variant onto the legacy ServiceOption shape so old API
  consumers keep working.

Collection: `product_extras_collection` (see database.py).
Relationship: 1 Product → N ProductExtra.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime

from .common import generate_id, utc_now


EXTRA_KINDS = ("mandatory", "optional", "radio_variant")
PRICE_MODIFIER_TYPES = ("flat", "per_day", "per_unit")


class ProductExtraBase(BaseModel):
    """Fields shared by create/update contracts."""

    model_config = ConfigDict(extra="ignore")

    kind: Literal["mandatory", "optional", "radio_variant"]
    # Required when kind=radio_variant; optional otherwise.
    # Multiple radio_variant rows sharing the same group_key form a
    # mutually exclusive picker group on the storefront.
    group_key: Optional[str] = Field(default=None, max_length=80)

    label: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)

    price: float = Field(ge=0)
    price_modifier_type: Literal["flat", "per_day", "per_unit"] = "flat"
    # CH compliance v1 — optional override; resolved via currency_service
    # to the parent product's / org's currency when None.
    currency: Optional[str] = None

    # Legacy parity with ServiceOption — only meaningful for
    # kind=radio_variant on service/slot products. Lets a variant carry
    # its own slot duration override.
    duration_minutes_override: Optional[int] = Field(default=None, ge=5, le=1440)

    # For kind=optional: pre-checked at first render.
    # For kind=radio_variant: the default pick within its group.
    is_default: bool = False

    sort_order: int = 0
    is_active: bool = True

    @field_validator("group_key")
    @classmethod
    def _group_key_required_for_radio(cls, v, info):
        """Enforce group_key presence when kind=radio_variant."""
        kind = (info.data or {}).get("kind")
        if kind == "radio_variant" and not v:
            raise ValueError("group_key is required when kind=radio_variant")
        return v

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


class ProductExtra(ProductExtraBase):
    """Full ProductExtra document as stored in MongoDB."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    product_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProductExtraCreate(ProductExtraBase):
    """Input model for POST /api/products/{product_id}/extras."""
    pass


class ProductExtraUpdate(BaseModel):
    """Partial update for PATCH. All fields optional."""

    model_config = ConfigDict(extra="ignore")

    kind: Optional[Literal["mandatory", "optional", "radio_variant"]] = None
    group_key: Optional[str] = Field(default=None, max_length=80)
    label: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Optional[float] = Field(default=None, ge=0)
    price_modifier_type: Optional[Literal["flat", "per_day", "per_unit"]] = None
    currency: Optional[str] = None
    duration_minutes_override: Optional[int] = Field(default=None, ge=5, le=1440)
    is_default: Optional[bool] = None
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


# ── Order snapshot ───────────────────────────────────────────────────────────


class OrderLineExtra(BaseModel):
    """Per-line snapshot of an applied ProductExtra.

    Frozen at order create time — edits to the underlying ProductExtra
    (price, label, deletion) MUST NOT alter historical order totals.
    Stored as array on OrderLineBase.extras.
    """

    model_config = ConfigDict(extra="ignore")

    extra_id: str                      # FK at click-time, may be deleted later
    kind: Literal["mandatory", "optional", "radio_variant"]
    group_key: Optional[str] = None

    # Snapshot of the chosen values — NEVER re-read from the live product.
    label: str
    unit_price: float = Field(ge=0)
    price_modifier_type: Literal["flat", "per_day", "per_unit"] = "flat"

    # Multiplier applied to unit_price. For:
    #   flat      → 1
    #   per_day   → number of rental days (date_to - date_from + 1)
    #   per_unit  → line quantity
    quantity: float = Field(default=1, ge=0)
    line_total: float = Field(ge=0)


class ExtraSelections(BaseModel):
    """Input shape used by OrderLineCreate and /price-preview.

    The client never specifies mandatory extras — the server merges them
    unconditionally. mandatory_confirmed is a courtesy flag for UIs that
    want to show the customer "confirm you understand these fees will be
    added"; the server ignores its value.
    """

    model_config = ConfigDict(extra="ignore")

    mandatory_confirmed: bool = True
    optional_ids: List[str] = Field(default_factory=list)
    # group_key → extra_id (exactly one pick per group).
    radio_picks: dict = Field(default_factory=dict)
