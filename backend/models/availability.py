"""
Availability models — scheduling foundation for booking and events.

Two collections:
- availability_rules: recurring weekly patterns (e.g., Mon-Fri 9-18, 60min slots)
- blocked_slots: specific date/time blocks (personal, holidays, bookings, events)

Availability computation: rules - blocked_slots - confirmed bookings = free slots.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from .common import generate_id, utc_now


# ── Availability Rules (recurring weekly patterns) ───────────────────────

class AvailabilityRule(BaseModel):
    """A recurring weekly availability window."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    store_id: Optional[str] = None              # Optional: store-specific rule
    # F5 Onda 12 — product_id is optional. When set, the rule applies
    # only to that product (typically a service for slot-based booking).
    # When None, the rule is a store-wide default.
    product_id: Optional[str] = None
    day_of_week: int = Field(ge=0, le=6)        # 0=Monday, 6=Sunday
    start_time: str = "09:00"                   # HH:MM format
    end_time: str = "18:00"                     # HH:MM format
    slot_duration_minutes: int = Field(default=60, ge=15, le=480)
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AvailabilityRuleCreate(BaseModel):
    store_id: Optional[str] = None
    product_id: Optional[str] = None  # F5 Onda 12 — per-product scoping
    day_of_week: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    end_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    slot_duration_minutes: int = Field(default=60, ge=15, le=480)


class AvailabilityRuleResponse(BaseModel):
    id: str
    organization_id: str
    store_id: Optional[str] = None
    day_of_week: int
    start_time: str
    end_time: str
    slot_duration_minutes: int
    is_active: bool
    created_at: datetime


# ── Blocked Slots (specific date/time blocks) ───────────────────────────

class BlockedSlot(BaseModel):
    """A specific date/time block when the merchant is unavailable."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    store_id: Optional[str] = None
    date: str                                   # ISO date: "2026-05-15"
    start_time: str                             # HH:MM: "09:00"
    end_time: str                               # HH:MM: "10:00"
    reason: str = "personal"                    # personal | holiday | booking | event | rental
    reference_id: Optional[str] = None          # order_id or occurrence_id
    product_id: Optional[str] = None            # per-product block (rental); null = global (person busy)
    scope: Optional[str] = None                 # agenda | rentals | null=global (visible everywhere)
    group_id: Optional[str] = None               # shared ID for bulk-created blocks
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)


class BlockedSlotCreate(BaseModel):
    store_id: Optional[str] = None
    product_id: Optional[str] = None
    scope: Optional[str] = None          # agenda | rentals | null=global
    date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    end_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    reason: str = "personal"
    note: Optional[str] = Field(default=None, max_length=500)


class BlockedSlotBatchCreate(BaseModel):
    """Create blocked slots for multiple dates at once (bulk/recurring)."""
    store_id: Optional[str] = None
    product_id: Optional[str] = None
    scope: Optional[str] = None          # agenda | rentals | null=global
    dates: List[str] = Field(min_length=1, max_length=60)  # ISO dates
    start_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    end_time: str = Field(pattern=r'^\d{2}:\d{2}$')
    reason: str = "personal"
    note: Optional[str] = Field(default=None, max_length=500)


class BlockedSlotResponse(BaseModel):
    id: str
    organization_id: str
    store_id: Optional[str] = None
    date: str
    start_time: str
    end_time: str
    reason: str
    reference_id: Optional[str] = None
    product_id: Optional[str] = None
    scope: Optional[str] = None
    group_id: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
