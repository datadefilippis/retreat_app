"""
ICS service — build iCalendar (.ics) payloads for events & bookings.

Minimal, dependency-free implementation of RFC 5545 VCALENDAR.
Used by email attachments and the public /b/{token} / /t/{token}
landing pages so customers can add their appointment to their
personal calendar.

Scope is intentionally narrow:
  - Single VEVENT per call (no recurrence, no overrides)
  - No VTIMEZONE block; times are emitted as floating or UTC Z
    depending on inputs (ISO strings with offset)
  - No attendees / organizer block (would expose org/customer email
    in a way some clients mis-handle). Good enough for a personal
    calendar add.

If we later need RSVP-style calendaring we upgrade to the `icalendar`
package. For now the hand-rolled output passes Apple Calendar / Google
Calendar / Outlook / Thunderbird import.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def _escape(text: str) -> str:
    """Escape per RFC 5545 §3.3.11: backslash, comma, semicolon, newline."""
    if text is None:
        return ""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _fold_line(line: str) -> str:
    """RFC 5545 §3.1 — lines SHOULD be max 75 octets; continuation with CRLF + space."""
    if len(line) <= 75:
        return line
    chunks = []
    i = 0
    while i < len(line):
        chunk = line[i:i + 75]
        chunks.append(chunk)
        i += 75
    return "\r\n ".join(chunks)


def _fmt_dt_utc(dt: datetime) -> str:
    """Format as UTC: 20260512T143000Z"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _fmt_dt_floating(dt: datetime) -> str:
    """Format as floating local time: 20260512T143000 (no tz)."""
    return dt.strftime("%Y%m%dT%H%M%S")


def _parse_iso(value: str) -> Optional[datetime]:
    """Parse ISO datetime or date+time combo. Returns None on failure."""
    if not value:
        return None
    try:
        s = value.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _build_vevent(
    *,
    uid: str,
    dtstart: datetime,
    dtend: datetime,
    summary: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    url: Optional[str] = None,
    is_floating: bool = False,
) -> list[str]:
    """Emit the VEVENT block as a list of CRLF-joined lines."""
    fmt = _fmt_dt_floating if is_floating else _fmt_dt_utc
    dtstamp = _fmt_dt_utc(datetime.now(timezone.utc))

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{fmt(dtstart)}",
        f"DTEND:{fmt(dtend)}",
        f"SUMMARY:{_escape(summary)}",
    ]
    if description:
        lines.append(f"DESCRIPTION:{_escape(description)}")
    if location:
        lines.append(f"LOCATION:{_escape(location)}")
    if url:
        lines.append(f"URL:{_escape(url)}")
    lines.append("STATUS:CONFIRMED")
    lines.append("TRANSP:OPAQUE")
    lines.append("END:VEVENT")
    return [_fold_line(l) for l in lines]


def _wrap_vcalendar(vevent_lines: list[str]) -> str:
    """Wrap a VEVENT block into a VCALENDAR envelope with CRLF line endings."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Aurya//Commerce//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    lines.extend(vevent_lines)
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def build_ics_for_booking(booking: dict, product_name: str = "Consulenza", url: Optional[str] = None) -> str:
    """Generate an .ics string for a single IssuedBooking row.

    `booking` is the dict from issued_bookings_collection (or IssuedBooking.model_dump).
    We treat booking_date + booking_start_time / booking_end_time as floating
    local times, since we don't yet persist timezone. The customer's calendar
    app will interpret them as "at the organizer's location time".
    """
    bdate = booking.get("booking_date")
    bstart = booking.get("booking_start_time")
    bend = booking.get("booking_end_time")
    if not (bdate and bstart and bend):
        return ""

    try:
        dtstart = datetime.fromisoformat(f"{bdate}T{bstart}:00")
        dtend = datetime.fromisoformat(f"{bdate}T{bend}:00")
    except Exception:
        return ""

    option = booking.get("service_option_label")
    summary = f"{product_name}" + (f" — {option}" if option else "")
    desc_parts = []
    if booking.get("code"):
        desc_parts.append(f"Codice: {booking['code']}")
    if booking.get("holder_name"):
        desc_parts.append(f"Intestatario: {booking['holder_name']}")
    description = "\n".join(desc_parts) if desc_parts else None

    vevent = _build_vevent(
        uid=f"booking-{booking.get('id') or booking.get('code')}@afianco.ch",
        dtstart=dtstart,
        dtend=dtend,
        summary=summary,
        description=description,
        location=booking.get("location"),
        url=url,
        is_floating=True,
    )
    return _wrap_vcalendar(vevent)


def build_ics_for_reservation(reservation: dict, product_name: str = "Prenotazione", url: Optional[str] = None) -> str:
    """Generate an .ics string for a single IssuedReservation row.

    Supports both flavors:
      - range: multi-day VEVENT with DTSTART/DTEND dates (hotel-style,
        DTEND is the day AFTER the last night per ICS convention — but
        we keep the simpler inclusive representation: DTSTART=date_from
        00:00, DTEND=date_to 23:59 floating).
      - slot:  single VEVENT with hh:mm floating local time.

    Returns "" on malformed input.
    """
    flavor = reservation.get("reservation_flavor")
    if flavor == "range":
        dfrom = reservation.get("date_from")
        dto = reservation.get("date_to") or dfrom
        if not dfrom:
            return ""
        try:
            dtstart = datetime.fromisoformat(f"{dfrom}T00:00:00")
            dtend = datetime.fromisoformat(f"{dto}T23:59:00")
        except Exception:
            return ""
    elif flavor == "slot":
        sdate = reservation.get("slot_date")
        sstart = reservation.get("slot_start_time")
        send = reservation.get("slot_end_time")
        if not (sdate and sstart and send):
            return ""
        try:
            dtstart = datetime.fromisoformat(f"{sdate}T{sstart}:00")
            dtend = datetime.fromisoformat(f"{sdate}T{send}:00")
        except Exception:
            return ""
    else:
        return ""

    desc_parts = []
    if reservation.get("code"):
        desc_parts.append(f"Codice: {reservation['code']}")
    if reservation.get("holder_name"):
        desc_parts.append(f"Intestatario: {reservation['holder_name']}")
    extras = reservation.get("extras_snapshot") or []
    if extras:
        desc_parts.append("Extras:")
        for ex in extras:
            desc_parts.append(f"  - {ex.get('label')} (€{ex.get('line_total', 0):.2f})")
    description = "\n".join(desc_parts) if desc_parts else None

    vevent = _build_vevent(
        uid=f"rsv-{reservation.get('id') or reservation.get('code')}@afianco.ch",
        dtstart=dtstart,
        dtend=dtend,
        summary=product_name,
        description=description,
        location=reservation.get("location"),
        url=url,
        is_floating=True,
    )
    return _wrap_vcalendar(vevent)


def build_ics_for_occurrence(occurrence: dict, product_name: str = "Evento", url: Optional[str] = None) -> str:
    """Generate an .ics string for a single EventOccurrence row.

    Uses occurrence.start_at / end_at. Emits as UTC if the ISO carries
    an offset, otherwise as floating local time.
    """
    start_at = occurrence.get("start_at")
    end_at = occurrence.get("end_at") or start_at
    if not (start_at and end_at):
        return ""

    dtstart = _parse_iso(start_at)
    dtend = _parse_iso(end_at)
    if not (dtstart and dtend):
        return ""

    has_tz = dtstart.tzinfo is not None or "Z" in start_at.upper() or "+" in start_at[10:]

    summary = product_name
    description_parts = []
    if occurrence.get("venue_name"):
        description_parts.append(occurrence["venue_name"])
    if occurrence.get("city"):
        description_parts.append(occurrence["city"])
    description = " · ".join(description_parts) if description_parts else None

    location = occurrence.get("location") or " · ".join(
        p for p in [occurrence.get("venue_name"), occurrence.get("address"), occurrence.get("city")] if p
    ) or None

    vevent = _build_vevent(
        uid=f"occurrence-{occurrence.get('id')}@afianco.ch",
        dtstart=dtstart,
        dtend=dtend,
        summary=summary,
        description=description,
        location=location,
        url=url,
        is_floating=not has_tz,
    )
    return _wrap_vcalendar(vevent)
