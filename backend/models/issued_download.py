"""
IssuedDownload — one fulfilled digital delivery.

Release 3 (Digital) B3. Analog of IssuedReservation (rental/slot) /
IssuedBooking (service) / IssuedTicket (event_ticket) for item_type=digital.

One IssuedDownload row per (order_id, order_line_index). A single order
line with quantity > 1 still produces ONE IssuedDownload row — a digital
good is typically licensed per order, not per seat. The
`max_downloads` knob caps how many times the customer can pull the file
from that one link.

Status lifecycle:
  active      — token valid, under max_downloads, not expired.
  cancelled   — order cancelled. Token rejects with 404.
  exhausted   — max_downloads reached. Token rejects with 410.

Code format: DLD-XXXX-XXXX (4+4 alphanumeric, uppercase, ambiguous glyphs
0/O/I/1/L excluded). Aligned with the other issued artifacts.

Uniqueness: `code` and `access_token` are globally unique across orgs.
Idempotency: one row per (order_id, order_line_index) — enforced by a
unique compound index so confirm_order retries never duplicate.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from .common import generate_id, utc_now
from .product_extra import OrderLineExtra


DOWNLOAD_STATUSES = ("active", "cancelled", "exhausted")

# Same alphabet as IssuedReservation / IssuedBooking / IssuedTicket —
# excludes 0, O, I, 1, L.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_download_code() -> str:
    """Return a fresh DLD-XXXX-XXXX code.

    CSPRNG-backed. Cross-org global uniqueness is enforced by the unique
    DB index on `code`; callers handle the duplicate-key retry on insert.
    """
    import secrets
    part1 = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    part2 = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    return f"DLD-{part1}-{part2}"


class IssuedDownloadBase(BaseModel):
    """Shared fields — persisted to Mongo + surfaced by public / admin APIs."""

    model_config = ConfigDict(extra="ignore")

    order_id: str
    # Position of the source OrderLine inside the Order.items list.
    # Together with order_id this is the idempotency key.
    order_line_index: int = Field(ge=0)

    product_id: str
    product_name: str = Field(max_length=255)                     # snapshot

    # Snapshot of the uploaded file at issue time. Copied from
    # product.metadata (DigitalMetadata.download_*) so that changing the
    # product file later does not retroactively change the customer's
    # download. None means the file was missing at issue time — the
    # download endpoint will return 404.
    download_filename: Optional[str] = Field(default=None, max_length=255)
    download_size_bytes: Optional[int] = Field(default=None, ge=0)
    download_mime_type: Optional[str] = Field(default=None, max_length=120)

    # Human-readable code shown to the customer + printable on receipts.
    code: str = Field(min_length=10, max_length=24)

    # Unguessable public token for the customer landing page
    # (/d/{access_token}). Separate from `code` so leaking the URL does
    # NOT enable admin actions. URL-safe 32-char base64 (secrets.token_urlsafe).
    access_token: Optional[str] = Field(default=None, max_length=64)
    # After this ISO timestamp the landing returns 410/404. None = no
    # expiry. Derived from DigitalMetadata.access_expiry_days at issue time.
    access_token_expires_at: Optional[str] = Field(default=None)

    status: Literal["active", "cancelled", "exhausted"] = "active"

    # Frozen at issue time — never re-read from the live product. Used by
    # the email section and landing to reflect the extras the customer paid for.
    extras_snapshot: List[OrderLineExtra] = Field(default_factory=list)

    # Snapshot of the customer identity at issue time.
    holder_name: Optional[str] = Field(default=None, max_length=255)
    holder_email: Optional[str] = Field(default=None, max_length=320)
    holder_phone: Optional[str] = Field(default=None, max_length=40)

    # Download policy. `max_downloads` is a cap (None = unlimited);
    # `download_count` is atomically $inc'd by the download endpoint and
    # flips `status` to "exhausted" when it reaches the cap.
    max_downloads: Optional[int] = Field(default=None, ge=1, le=100)
    download_count: int = Field(default=0, ge=0)
    last_downloaded_at: Optional[str] = Field(default=None)

    # Per-delivery email audit (mirrors IssuedReservation).
    delivery_status: Optional[str] = Field(default="pending", max_length=16)
    delivery_attempts: int = Field(default=0, ge=0)
    last_delivery_error: Optional[str] = Field(default=None, max_length=500)
    sent_at: Optional[datetime] = None
    delivery_last_attempt_at: Optional[str] = Field(default=None)


class IssuedDownload(IssuedDownloadBase):
    """Full IssuedDownload document as stored in MongoDB."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    # Populated when cancel_order runs.
    cancelled_at: Optional[datetime] = None


class IssuedDownloadResponse(IssuedDownloadBase):
    """Response shape for admin / public endpoints."""

    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime] = None
