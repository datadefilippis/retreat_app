"""
IssuedBooking — one confirmed consultation/service appointment.

Analog of IssuedTicket for service products (consulenze). Where events
create one ticket per seat purchased, a service order typically creates
ONE booking per order line (the customer books one appointment slot).
If a service is sold in bundles or multi-seat, we mirror the ticket
pattern and issue one row per seat within the line.

Status lifecycle:
  confirmed    — just issued, appointment scheduled
  completed    — admin marked the session as delivered
  no_show      — customer didn't show up
  cancelled    — customer or admin cancelled
                 (never deleted — kept for audit)

Code format: BKG-XXXX-XXXX (4+4 alphanumeric, uppercase, ambiguous
glyphs 0/O/I/1/L excluded). Human-readable enough to be dictated,
dense enough for a QR on the confirmation email.

Uniqueness: `code` is globally unique across all orgs.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .common import generate_id, utc_now


BOOKING_STATUSES = ("confirmed", "completed", "no_show", "cancelled")

# Same alphabet as IssuedTicket — excludes 0, O, I, 1, L.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_booking_code() -> str:
    """Return a fresh BKG-XXXX-XXXX code.

    Uses `secrets.choice` for CSPRNG randomness. Cross-org global
    uniqueness is enforced by the unique DB index.
    """
    import secrets
    part1 = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    part2 = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    return f"BKG-{part1}-{part2}"


class IssuedBookingBase(BaseModel):
    """Shared fields — written to Mongo + surfaced by public / admin APIs."""

    order_id: str
    product_id: str

    # Slot information — the core booking payload.
    # Stored as ISO strings (YYYY-MM-DD + HH:MM) to match how
    # availability_rules and blocked_slots already persist time.
    booking_date: str = Field(min_length=10, max_length=10)           # "2026-05-12"
    booking_start_time: str = Field(min_length=5, max_length=5)       # "14:30"
    booking_end_time: str = Field(min_length=5, max_length=5)         # "15:30"

    # Optional link to the service_option selected by the customer.
    # Snapshot label is kept so a subsequent option rename/delete does
    # not break the confirmation email / admin view.
    service_option_id: Optional[str] = None
    service_option_label: Optional[str] = Field(default=None, max_length=255)

    # Where the service is delivered — snapshotted from store or product.
    # Free-text; may be an address, a URL (for remote consulting), etc.
    location: Optional[str] = Field(default=None, max_length=500)

    # Human-readable code shown to the customer and embedded in the QR
    # on the confirmation email / landing page.
    code: str = Field(min_length=10, max_length=24)
    status: str = "confirmed"  # confirmed | completed | no_show | cancelled

    # Snapshot of the customer identity at issue time.
    holder_name: Optional[str] = Field(default=None, max_length=255)
    holder_email: Optional[str] = Field(default=None, max_length=320)
    holder_phone: Optional[str] = Field(default=None, max_length=40)

    # Unguessable public token for the customer landing page
    # (/b/{access_token}). Separate from `code` so leaking the URL does
    # NOT enable admin actions on the booking. URL-safe 32-char base64.
    access_token: Optional[str] = Field(default=None, max_length=64)
    # ISO timestamp; after this the landing returns 404. Defaults to
    # booking_end + 14d when issued. None means no expiration.
    access_token_expires_at: Optional[str] = Field(default=None)

    # Snapshot of merchant-defined order_fields values filled at checkout.
    # Analogous to IssuedTicket.attendee_fields_data.
    attendee_fields_data: dict = Field(default_factory=dict)

    # Per-booking email delivery audit.
    delivery_status: Optional[str] = Field(default="pending", max_length=16)
    delivery_last_attempt_at: Optional[str] = Field(default=None)


class IssuedBooking(IssuedBookingBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    # Position within the order line (1-based). For quantity>1 services
    # (bundles of sessions) this indicates which session in the bundle.
    seat_index: int = 1
    seat_count: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    # Populated when admin marks the session delivered.
    completed_at: Optional[datetime] = None
    # Populated when booking is cancelled.
    cancelled_at: Optional[datetime] = None


class IssuedBookingResponse(IssuedBookingBase):
    id: str
    organization_id: str
    seat_index: int
    seat_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
