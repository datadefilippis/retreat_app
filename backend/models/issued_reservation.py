"""
IssuedReservation — one confirmed rental or slot booking.

Onda 16 (Prenotazione consolidation). Analog of IssuedTicket (events) and
IssuedBooking (service consulenze) for the unified Prenotazione umbrella
that covers the two rental flavors:

  range  — date-range reservation, multi-day, daily granularity.
           B&B rooms, cars, equipment hire.

  slot   — single time window reservation (hh:mm).
           Meeting rooms, tennis courts, non-service bookable slots.

Status lifecycle:
  active      — issued and valid.
  cancelled   — customer or admin cancelled the order
                (never deleted — kept for audit).

Code format: RSV-XXXX-XXXX (4+4 alphanumeric, uppercase, ambiguous
glyphs 0/O/I/1/L excluded). Human-readable enough to be dictated,
dense enough for a QR on the confirmation email.

Uniqueness: `code` is globally unique across all orgs. `access_token`
also globally unique.

Idempotency: one IssuedReservation per (order_id, order_line_index).
Enforced by a unique compound DB index so retries of confirm_order
never produce duplicates.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from .common import generate_id, utc_now
from .product_extra import OrderLineExtra


RESERVATION_STATUSES = ("active", "cancelled")
RESERVATION_FLAVORS = ("range", "slot")

# Same alphabet as IssuedTicket / IssuedBooking — excludes 0, O, I, 1, L.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_reservation_code() -> str:
    """Return a fresh RSV-XXXX-XXXX code.

    Uses `secrets.choice` for CSPRNG randomness. Cross-org global
    uniqueness is enforced by the unique DB index on `code`.
    """
    import secrets
    part1 = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    part2 = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    return f"RSV-{part1}-{part2}"


class IssuedReservationBase(BaseModel):
    """Shared fields — written to Mongo + surfaced by public / admin APIs."""

    model_config = ConfigDict(extra="ignore")

    order_id: str
    # Position of the source OrderLine inside the Order.items list.
    # Used together with order_id for idempotency.
    order_line_index: int = Field(ge=0)

    product_id: str
    product_name: str = Field(max_length=255)                     # snapshot

    reservation_flavor: Literal["range", "slot"]

    # Range-flavor slot payload. Both ISO date strings.
    date_from: Optional[str] = Field(default=None, min_length=10, max_length=10)
    date_to: Optional[str] = Field(default=None, min_length=10, max_length=10)

    # Slot-flavor payload.
    slot_date: Optional[str] = Field(default=None, min_length=10, max_length=10)
    slot_start_time: Optional[str] = Field(default=None, min_length=5, max_length=5)
    slot_end_time: Optional[str] = Field(default=None, min_length=5, max_length=5)
    # Onda 17 — cross-day slot end date. When None, the slot ends on slot_date
    # (same-day semantics, historic behaviour). When populated, the reservation
    # spans from slot_date + slot_start_time to slot_date_to + slot_end_time.
    slot_date_to: Optional[str] = Field(default=None, min_length=10, max_length=10)

    # Frozen at issue time — never re-read from the live product.
    extras_snapshot: List[OrderLineExtra] = Field(default_factory=list)

    # Human-readable code shown to the customer + embedded in QR.
    code: str = Field(min_length=10, max_length=24)

    # Unguessable public token for the customer landing page
    # (/rsv/{access_token}). Separate from `code` so leaking the URL does
    # NOT enable admin actions. URL-safe 32-char base64.
    access_token: Optional[str] = Field(default=None, max_length=64)
    # After this ISO timestamp the landing returns 404. None = no expiry.
    access_token_expires_at: Optional[str] = Field(default=None)

    status: Literal["active", "cancelled"] = "active"

    # Snapshot of the customer identity at issue time.
    holder_name: Optional[str] = Field(default=None, max_length=255)
    holder_email: Optional[str] = Field(default=None, max_length=320)
    holder_phone: Optional[str] = Field(default=None, max_length=40)

    # Where the reservation takes place — snapshotted from product / store.
    location: Optional[str] = Field(default=None, max_length=500)

    # Per-reservation email delivery audit (mirrors IssuedBooking /
    # IssuedTicket). Values: pending | sent | failed | bounced.
    delivery_status: Optional[str] = Field(default="pending", max_length=16)
    delivery_attempts: int = Field(default=0, ge=0)
    last_delivery_error: Optional[str] = Field(default=None, max_length=500)
    sent_at: Optional[datetime] = None
    delivery_last_attempt_at: Optional[str] = Field(default=None)


class IssuedReservation(IssuedReservationBase):
    """Full IssuedReservation document as stored in MongoDB."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    # Populated when cancel_order runs.
    cancelled_at: Optional[datetime] = None


class IssuedReservationResponse(IssuedReservationBase):
    """Response shape for admin / public endpoints."""

    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime] = None
