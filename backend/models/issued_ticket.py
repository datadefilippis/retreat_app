"""
IssuedTicket — one physical seat / admission issued after purchase.

Granularity: ONE ROW PER SEAT. If an order line says quantity=3 for a
VIP tier of occurrence Y, E4 writes 3 IssuedTicket rows, each with its
own human-readable code and check-in state. This is the unit the door
scanner operates on; capacity reservation (P7/E1) already guaranteed
the seat is ours, now we give each seat its identity.

Status lifecycle:
  valid        — just issued, not yet scanned
  checked_in   — scanned at the event door; `checked_in_at` populated
  voided       — the order was cancelled / the ticket was manually
                 invalidated. Never deleted — kept for audit.

The code format was chosen with the user in E1 design: EVT-XXXX-XXXX
(4+4 alphanumeric, uppercase, ambiguous glyphs 0/O/I/1/L excluded).
Human-readable enough to be dictated on the phone, dense enough to be
safe for a QR.

Uniqueness: `code` is globally unique across ALL orgs. Prevents any
risk of cross-tenant scanning confusion (org A's EVT-AAAA-BBBB cannot
ever scan as valid at org B's door).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .common import generate_id, utc_now


TICKET_STATUSES = ("valid", "checked_in", "voided")

# Alphabet excludes 0, O, I, 1, L to avoid dictation errors and
# look-alike confusion on printed or on-screen codes.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_ticket_code() -> str:
    """Return a fresh EVT-XXXX-XXXX code.

    Security note: uses `secrets.choice` for CSPRNG randomness. 8
    characters from a 31-char alphabet = 31**8 ~= 8.5e11 combinations;
    uniqueness across a single org for a single event is a non-issue.
    Cross-org global uniqueness is enforced by the unique DB index.
    The database insert is what provides the strong guarantee — the
    code generator only provides a good candidate.
    """
    import secrets
    part1 = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    part2 = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    return f"EVT-{part1}-{part2}"


class IssuedTicketBase(BaseModel):
    """Shared fields — mirrors what goes into Mongo and what the admin
    check-in API surfaces."""

    order_id: str
    occurrence_id: str
    product_id: str
    # tier_id is optional because mono-tier events (no E1 tiers) still
    # issue individual tickets. When a tier is present, the label
    # snapshot is stored so ticket lookups survive tier rename/delete.
    tier_id: Optional[str] = None
    tier_label: Optional[str] = None
    # Human-readable code shown to the buyer and embedded in the QR.
    code: str = Field(min_length=10, max_length=24)
    status: str = "valid"  # valid | checked_in | voided
    # Name of the ticket holder snapshotted from the customer at issue
    # time — useful for the door scanner UI even if the customer record
    # is later deleted.
    holder_name: Optional[str] = Field(default=None, max_length=255)
    holder_email: Optional[str] = Field(default=None, max_length=320)
    # F1 Onda 8 — optional phone, reserved for future SMS/WhatsApp delivery.
    holder_phone: Optional[str] = Field(default=None, max_length=40)
    # F1 Onda 8 — unguessable public token to access the landing page
    # (/t/{access_token}) which shows the QR + event details. Separate from
    # `code` (used at the door scanner) so leaking the URL does NOT enable
    # door check-in. URL-safe 32-char base64 (secrets.token_urlsafe(24)).
    access_token: Optional[str] = Field(default=None, max_length=64)
    # F2 Onda 9 — snapshot of merchant-defined attendee_fields values filled
    # at checkout time (keyed by FieldConfig.id). Kept on the ticket so the
    # dashboard / CSV export can show them even if the merchant later edits
    # the field list on the product.
    attendee_fields_data: dict = Field(default_factory=dict)
    # After this ISO timestamp the landing page returns 404. Defaults to
    # event_end + 14d when issued; None means no expiration.
    access_token_expires_at: Optional[str] = Field(default=None)
    # Per-holder email delivery audit (pending = not yet attempted, sent,
    # bounced, unsent = attempt failed). Lets the dashboard surface a
    # "X/Y email consegnate" indicator and a "rinvia a tutti" button.
    delivery_status: Optional[str] = Field(default="pending", max_length=16)
    delivery_last_attempt_at: Optional[str] = Field(default=None)


class IssuedTicket(IssuedTicketBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    # Position within the order line (1-based). Useful when printing
    # "Biglietto 2 di 3" on the email.
    seat_index: int = 1
    seat_count: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    # Populated on successful scan. Null while status != "checked_in".
    checked_in_at: Optional[datetime] = None
    # When the ticket was voided (e.g. order cancelled). Null otherwise.
    voided_at: Optional[datetime] = None


class IssuedTicketResponse(IssuedTicketBase):
    id: str
    organization_id: str
    seat_index: int
    seat_count: int
    created_at: datetime
    checked_in_at: Optional[datetime] = None
    voided_at: Optional[datetime] = None
