"""
EventTicketTier — one ticket tier inside an EventOccurrence.

Example (case study Michele):
  Occurrence: "Cena 2026-08-14", capacity 30
  Tier A: label="Standard",  price=20, capacity=20
  Tier B: label="VIP",       price=50, capacity=10

A tier is always scoped to an occurrence (its parent event instance).
When an occurrence has NO tiers, the storefront falls back to the
legacy mono-tier behavior (single price_override, occurrence.capacity
as total). When an occurrence HAS tiers, the storefront picker shows
each tier with its own availability and the customer picks one
(or more in a single cart).

Capacity semantics:
  tier.capacity    = optional per-tier cap. None = "illimitato entro
                     l'occurrence capacity". A finite value is the
                     upper bound of THAT tier.
  tier.reserved_seats = atomically incremented counter (same pattern
                     as occurrence.reserved_seats in P7).

E1 enforces both limits at write time (see services/tier_capacity.py):
the order MUST fit within tier.capacity AND occurrence.capacity.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from .common import generate_id, utc_now


class EventTicketTierBase(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    price: float = Field(ge=0)
    # CH compliance v1 — optional override; resolved via currency_service
    # to the parent product / org currency when None.
    currency: Optional[str] = None
    capacity: Optional[int] = Field(default=None, ge=1)
    sort_order: int = 0

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


class EventTicketTierCreate(EventTicketTierBase):
    """Body for POST /event-occurrences/{id}/tiers.

    occurrence_id is taken from the URL path, not the body — keeps the
    request shape clean and prevents clients from pointing a tier at an
    occurrence in another org.
    """
    model_config = ConfigDict(extra="ignore")


class EventTicketTierUpdate(BaseModel):
    """Body for PATCH /event-occurrences/{id}/tiers/{tier_id}.

    All fields optional. reserved_seats is INTENTIONALLY not writable
    here — it is owned by the atomic reservation primitive.
    """
    model_config = ConfigDict(extra="ignore")

    label: Optional[str] = Field(default=None, min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None
    capacity: Optional[int] = Field(default=None, ge=1)
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


class EventTicketTier(EventTicketTierBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    occurrence_id: str
    reserved_seats: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EventTicketTierResponse(EventTicketTierBase):
    id: str
    organization_id: str
    occurrence_id: str
    reserved_seats: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Derived, read-only: capacity - reserved_seats (None = unlimited tier)
    remaining: Optional[int] = None
