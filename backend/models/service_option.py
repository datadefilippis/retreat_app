"""
ServiceOption — merchant-defined radio option for a service product.

Introduced by Onda 12 / F5 to mirror the tier concept of events but
tailored to services:

- Unlike event_ticket_tiers (which are scoped to a specific occurrence),
  ServiceOption is scoped to the **product**. A service has N options
  (e.g. "Consulenza 30 min", "Pacchetto 3 sedute"); each option has its
  own price and optional duration override.
- At checkout the customer must pick exactly ONE (radio-select), not
  multiple like event tiers.
- `duration_minutes_override` lets an option carry a different slot
  duration than the product default (e.g. a "pacchetto" takes a longer
  block).

Collection: `service_options_collection` (see database.py).
Relationship: 1 Product → N ServiceOption (1-to-many).
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from .common import generate_id, utc_now


class ServiceOptionBase(BaseModel):
    """Fields shared by create/update contracts."""
    label: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    price: float = Field(ge=0)
    duration_minutes_override: Optional[int] = Field(default=None, ge=5, le=1440)
    sort_order: int = 0
    is_active: bool = True


class ServiceOption(ServiceOptionBase):
    """Full ServiceOption document as stored in MongoDB."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    product_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ServiceOptionCreate(ServiceOptionBase):
    """Input model for POST /api/products/{product_id}/service-options."""
    pass


class ServiceOptionUpdate(BaseModel):
    """Partial update for PATCH. All fields optional."""
    model_config = ConfigDict(extra="ignore")

    label: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Optional[float] = Field(default=None, ge=0)
    duration_minutes_override: Optional[int] = Field(default=None, ge=5, le=1440)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
