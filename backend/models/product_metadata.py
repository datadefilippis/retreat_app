"""
Product metadata schemas — Pydantic models for the type-specific blob.

Today every product row carries a free-form `metadata: Dict[str, Any]`
field. Each type stores different keys there:

  physical     : (no metadata keys used today)
  service      : duration_label?, service_notes?
  rental       : rental_unit? (giorno|settimana|mese), rental_notes?
  event_ticket : (no metadata keys used today — event_occurrences are a
                  separate collection)
  booking      : slot_duration_minutes? (int), duration_label?
  digital      : download_filename?, download_size_bytes?, download_mime_type?,
                 max_downloads_per_delivery?, access_expiry_days?,
                 long_description?, cover_image_url?

This module declares a Pydantic model per type that describes the
EXPECTED shape, then a dispatcher `validate_metadata_for_type(item_type,
raw)` that returns a clean, normalized dict.

CRITICAL BACKWARD-COMPAT RULE:
  The schemas use `extra="ignore"` (not "forbid") and every field is
  Optional. That means:
    - Unknown keys in production data are silently kept in the raw dict
      passed through — nothing is ever lost or rejected.
    - Missing keys never raise — the writer is free to send only what
      they have.
    - Type coercion (e.g. int string for slot_duration_minutes) is
      attempted; on failure the value is dropped from the typed view
      but kept in the raw dict so we never break a read.

This is intentionally conservative: metadata has been a free-form blob
for a long time and we MUST NOT corrupt existing rows during rollout.
Tightening to "strict" is a future concern once all writers emit
well-formed payloads.
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Per-type schemas ────────────────────────────────────────────────────────


class PhysicalMetadata(BaseModel):
    """Physical goods have no dedicated metadata today. Placeholder kept
    for symmetry and to make future fields (weight, dimensions) easy to
    add without touching other types."""

    model_config = ConfigDict(extra="ignore")


class ServiceMetadata(BaseModel):
    """Intangible service — human description of duration + notes +
    (P9) machine-readable duration + delivery mode.

    Two duration representations coexist intentionally:
      duration_label   : DISPLAY string ("60 min", "1 sessione"). Always
                         accepted; what the merchant types is what the
                         customer sees.
      duration_minutes : MACHINE-READABLE integer. P9 addition. Used
                         by analytics / scheduling hints / invoice lines
                         when present. Does NOT turn a service into a
                         booking — for slot-level scheduling, use the
                         booking type.

    delivery_mode is a coarse taxonomy so the storefront can render
    appropriate copy ("prenota da remoto" vs "vieni in sede"). An
    unknown value is dropped from the typed view but preserved raw.

    scheduling_hint is a free-text human note ("entro 7 giorni dal
    pagamento") surfaced on invoices / storefront. Max 200 chars.
    """

    model_config = ConfigDict(extra="ignore")
    duration_label: Optional[str] = Field(default=None, max_length=120)
    service_notes: Optional[str] = Field(default=None, max_length=500)
    # ── P9 additions ────────────────────────────────────────────────────
    duration_minutes: Optional[int] = Field(default=None, ge=5, le=1440)
    delivery_mode: Optional[Literal[
        "remoto", "in_sede", "domicilio", "altro"
    ]] = None
    scheduling_hint: Optional[str] = Field(default=None, max_length=200)
    # ── F5 Onda 12 additions ────────────────────────────────────────────
    # service_allow_custom_request: when True the storefront shows a
    # "data/ora preferita" free-text field in addition to the slot picker,
    # letting the customer propose a time outside the standard availability
    # (merchant reviews manually). Optional, default False.
    service_allow_custom_request: Optional[bool] = False
    # ── Onda 13 additions ───────────────────────────────────────────────
    # long_description: markdown rich copy shown on the public landing
    # (/p/:org/:slug). Analogous to EventOccurrence.long_description.
    long_description: Optional[str] = Field(default=None, max_length=5000)
    # cover_image_url: dedicated hero image for the landing page. When
    # empty, the landing falls back to product.image_url.
    cover_image_url: Optional[str] = Field(default=None, max_length=500)


class RentalMetadata(BaseModel):
    """Rental — unit defines the pricing period multiplier.

    Accepted units mirror the storefront calendar picker. Anything else
    is dropped from the typed view (the raw string survives in the
    untyped dict so we never lose customer data during migration).

    ─ Onda 16 (Prenotazione consolidation) ─────────────────────────────
    `reservation_flavor` distinguishes the two user-facing rental UX:

      range — multi-day date range, daily granularity
              (B&B rooms, cars, equipment hire). Typically paired with
              rental_unit in {giorno, settimana, mese}.

      slot  — single time window (hh:mm) single-shot
              (meeting rooms, tennis courts, non-service bookable slots).
              Typically paired with rental_unit=ora or no unit.

    Absent value means legacy rental products created before Onda 16.
    A write-time normalizer in validators derives the flavor from
    rental_unit when not set explicitly, so existing products keep
    working.
    """

    model_config = ConfigDict(extra="ignore")
    rental_unit: Optional[Literal["ora", "giorno", "settimana", "mese"]] = None
    rental_notes: Optional[str] = Field(default=None, max_length=500)
    reservation_flavor: Optional[Literal["range", "slot"]] = None
    # Slot-flavor parity with BookingMetadata — so a rental+flavor=slot
    # product can carry the same scheduling knobs as the old item_type=booking.
    slot_duration_minutes: Optional[int] = Field(default=None, ge=5, le=480)
    duration_label: Optional[str] = Field(default=None, max_length=120)
    buffer_before_minutes: Optional[int] = Field(default=None, ge=0, le=240)
    buffer_after_minutes: Optional[int] = Field(default=None, ge=0, le=240)
    # Onda 17 — variable-duration rental slots. When set, the customer picks
    # start+end freely on the landing picker and the slot_generator returns
    # availability windows (not a fixed slot grid). All three fields fall back
    # to slot_duration_minutes when absent, so legacy products keep working.
    #   slot_min_duration_minutes : shortest bookable slot (defaults to step)
    #   slot_step_minutes         : granularity of the picker (15/30/60…)
    #   slot_max_duration_minutes : upper bound; None = unlimited up to 30 days
    slot_min_duration_minutes: Optional[int] = Field(default=None, ge=5, le=1440)
    slot_step_minutes: Optional[int] = Field(default=None, ge=5, le=120)
    slot_max_duration_minutes: Optional[int] = Field(default=None, ge=5, le=43200)


class EventTicketMetadata(BaseModel):
    """Event ticket — no type-specific metadata today.

    Per-occurrence data (dates, capacity, location overrides) lives in
    the dedicated event_occurrences collection, NOT here. This class
    exists so the registry can hand everyone a uniform shape.
    """

    model_config = ConfigDict(extra="ignore")


class DigitalMetadata(BaseModel):
    """Downloadable digital good — Release 3 (Digital) addition.

    File payload is NOT stored here. Instead, `digital_storage` (separate
    service) writes the binary to a private path outside StaticFiles; this
    schema carries only the safe descriptive metadata the storefront can
    show (filename, size, mime) plus optional policy knobs.

    Fields:
      download_filename / download_size_bytes / download_mime_type
          Snapshot of the uploaded file. Set by the upload endpoint;
          client code never writes these directly. Absent = no file
          uploaded yet → the validator rejects orders for safety.
      long_description / cover_image_url
          Landing page copy (markdown), mirrors ServiceMetadata.
      max_downloads_per_delivery
          Cap on downloads per IssuedDownload (None = unlimited).
          Backend `/downloads/{token}/file` enforces this atomically.
      access_expiry_days
          TTL for the access token starting at issue time (None = never
          expires). The token lands `expires_at` into IssuedDownload so
          the customer sees it on the landing.
    """

    model_config = ConfigDict(extra="ignore")
    # File snapshot — set by the dedicated upload endpoint, not user input.
    download_filename: Optional[str] = Field(default=None, max_length=255)
    download_size_bytes: Optional[int] = Field(default=None, ge=0)
    download_mime_type: Optional[str] = Field(default=None, max_length=120)
    # Landing copy parity with ServiceMetadata / RentalMetadata.
    long_description: Optional[str] = Field(default=None, max_length=5000)
    cover_image_url: Optional[str] = Field(default=None, max_length=500)
    # Policy knobs — admin-configurable.
    max_downloads_per_delivery: Optional[int] = Field(default=None, ge=1, le=100)
    access_expiry_days: Optional[int] = Field(default=None, ge=1, le=3650)


class BookingMetadata(BaseModel):
    """1:1 booking — slot duration drives calendar generation.

    slot_duration_minutes is the canonical field consumed by Phase P5
    for slot enforcement. Today the frontend captures it but the
    backend has been ignoring it; this schema acknowledges the field
    without YET enforcing it, so the migration is a no-op at read/write
    time.
    """

    model_config = ConfigDict(extra="ignore")
    slot_duration_minutes: Optional[int] = Field(default=None, ge=5, le=480)
    duration_label: Optional[str] = Field(default=None, max_length=120)
    buffer_before_minutes: Optional[int] = Field(default=None, ge=0, le=240)
    buffer_after_minutes: Optional[int] = Field(default=None, ge=0, le=240)


# ── Dispatcher ──────────────────────────────────────────────────────────────


# Static mapping so the registry P1 stays clean of Pydantic imports.
# Kept here (instead of inlined into product_types.py) to avoid a
# circular dependency when P3 validators also use the type registry.
TYPE_TO_METADATA_SCHEMA: Dict[str, type[BaseModel]] = {
    "physical": PhysicalMetadata,
    "service": ServiceMetadata,
    "rental": RentalMetadata,
    "event_ticket": EventTicketMetadata,
    "booking": BookingMetadata,
    "digital": DigitalMetadata,
}


def validate_metadata_for_type(item_type: str, raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate + normalize the metadata blob for a given type.

    Returns a plain dict that:
      - Contains all recognized fields coerced to their declared types
        (e.g. slot_duration_minutes coerced to int where possible).
      - Preserves every unrecognized key from the input untouched — we
        never discard production data silently.
      - Returns an empty dict when raw is None/empty.

    Never raises. If the input is malformed for a recognized field,
    that field is dropped from the typed view and the raw value is
    still included (last-write-wins from the input). Callers that
    need strict validation can compose this with their own check.
    """
    if not raw:
        return {}
    if not isinstance(raw, dict):
        # Defensive: legacy rows might carry non-dict metadata via a bug.
        # Rather than crash, return an empty typed view.
        return {}

    schema_cls = TYPE_TO_METADATA_SCHEMA.get(item_type)
    if schema_cls is None:
        # Unknown item_type: just echo the raw dict back.
        return dict(raw)

    # Parse with extras ignored — the typed view holds only known fields.
    try:
        typed = schema_cls.model_validate(raw).model_dump(exclude_none=True)
    except Exception:
        typed = {}

    # Merge typed (wins for known fields) with raw (keeps extras). The
    # resulting dict is the "clean" shape but no data from `raw` is ever
    # lost unless `typed` successfully coerces the same key to a
    # different value.
    merged = dict(raw)
    merged.update(typed)
    return merged


def metadata_schema_for_type(item_type: str) -> Optional[type[BaseModel]]:
    """Return the Pydantic class for a type's metadata, or None."""
    return TYPE_TO_METADATA_SCHEMA.get(item_type)
