"""
shipping_address_formatter.py — canonical one-line flattening of a
structured shipping address.

Single responsibility: given a `ShippingAddressDetails` dict, produce a
human-readable single-line string suitable for email receipts, PDF
invoices, and admin list views. This is the ONLY place the flattening
is performed on the backend so every reader sees the same format.

Format (IT convention, order optimized for carrier-friendliness):

    "Mario Rossi — Via Roma 12, 20100 Milano MI, IT"
     │            │       │   │     │      │   │
     │            │       │   │     │      │   └── country (if != default IT)
     │            │       │   │     │      └────── province (if present)
     │            │       │   │     └───────────── city
     │            │       │   └─────────────────── CAP
     │            │       └─────────────────────── civic
     │            └─────────────────────────────── line1 / street
     └──────────────────────────────────────────── recipient_name (if present)

Missing fields are gracefully omitted. The function never raises — a
malformed dict produces the best-effort partial string.

Pure function: no I/O, no DB, deterministic output. Easy to unit-test
and safe to call from request-handling hot paths.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _clean(val: Any) -> str:
    """Coerce to stripped string. Non-strings and None → empty string."""
    if val is None:
        return ""
    try:
        return str(val).strip()
    except Exception:
        return ""


def format_address_oneline(details: Optional[Dict[str, Any]]) -> str:
    """Return the canonical one-line flattening of a structured shipping
    address. Returns empty string when `details` is None/empty or every
    component is missing.

    Assembly:
      "<recipient> — <line1> <civic>, <cap> <city> <prov>, <country>"

    Rules:
      - Recipient prefix only when present (and followed by " — ").
      - Street block joins line1 + civic with a single space; when only
        one is present, the other is omitted (no awkward "Via Roma ").
      - City block joins cap + city + province; missing tokens collapse
        cleanly (no "20100  MI" with double space).
      - Country is only appended when != "IT" (default) to keep local
        addresses short; for foreign orders it's surfaced.
    """
    if not isinstance(details, dict):
        return ""

    recipient = _clean(details.get("recipient_name"))
    line1 = _clean(details.get("line1"))
    civic = _clean(details.get("civic"))
    cap = _clean(details.get("postal_code"))
    city = _clean(details.get("city"))
    province = _clean(details.get("province"))
    country = _clean(details.get("country")).upper()

    # Street block: "Via Roma 12" or just "Via Roma" or just "12".
    street_parts = [p for p in (line1, civic) if p]
    street = " ".join(street_parts)

    # City block: "20100 Milano MI" — skip each missing piece.
    city_parts = [p for p in (cap, city, province) if p]
    city_block = " ".join(city_parts)

    # Core geo: "<street>, <city_block>". When one half is missing, drop
    # the separator rather than leaving a dangling comma.
    geo_chunks = [p for p in (street, city_block) if p]
    geo = ", ".join(geo_chunks)

    # Append country only when non-default (IT is the baseline).
    if country and country != "IT":
        geo = f"{geo}, {country}" if geo else country

    # Recipient prefix.
    if recipient and geo:
        return f"{recipient} — {geo}"
    if recipient:
        return recipient
    return geo
