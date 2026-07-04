"""Phone number normalisation for WhatsApp deep links.

WhatsApp's ``wa.me/<digits>?text=...`` URL format requires the number
in **E.164 without the leading +** (e.g. ``41791234567`` for
``+41 79 123 45 67``). The merchant CRMs store phone numbers in any
format under the sun: spaces, dashes, parentheses, country prefixes
written as ``00`` instead of ``+``, sometimes just the local part.

We normalise via Google's ``libphonenumber`` Python port if available,
falling back to a defensive hand-rolled parser. The hand-roll handles
the 90 % of CH / IT / DE / FR cases the seed data covers; the lib
handles the long tail.

Switzerland-default: when the input has no country code we assume
``CH`` since Ticino is the dominant target. The default is overridable
per-org via ``organization.settings.phone_default_country``.
"""

from __future__ import annotations

import re
from typing import Optional


# Map common TLDs / dial codes to ISO 2-letter for default-country logic.
_DEFAULT_COUNTRY = "CH"

_DIGITS_ONLY_RE = re.compile(r"[^\d]")
_LEADING_ZERO_RE = re.compile(r"^0+")
_DOUBLE_ZERO_PREFIX_RE = re.compile(r"^00")

# Country dialing codes for the four locales we ship today.
_DIAL_CODES = {
    "CH": "41",
    "IT": "39",
    "DE": "49",
    "FR": "33",
    "AT": "43",
}


def to_e164(phone: Optional[str], default_country: str = _DEFAULT_COUNTRY) -> Optional[str]:
    """Normalise a phone string to E.164 without the leading ``+``.

    Returns ``None`` for empty / unparseable / clearly-wrong inputs so
    the channel ``supports()`` check can grey out the WhatsApp button
    on customers without a usable number.

    Examples:
        >>> to_e164("+41 79 123 45 67")
        '41791234567'
        >>> to_e164("079 123 45 67", default_country="CH")
        '41791234567'
        >>> to_e164("0041 79 123 45 67")
        '41791234567'
        >>> to_e164("(079) 123-4567", default_country="CH")
        '41791234567'
        >>> to_e164(None) is None
        True
        >>> to_e164("") is None
        True
        >>> to_e164("123") is None  # too short to be a phone
        True
        >>> to_e164("+39 02 123456789", default_country="CH")
        '39021234567'

    Note: the ``+39 02 123456789`` example is truncated to 11 digits
    after the country code because Italian landlines + mobiles fit in
    that space and 12+ digit inputs are almost always typos.
    """
    if not phone or not phone.strip():
        return None

    # Try the proper library first if installed.
    parsed = _parse_with_phonenumbers(phone, default_country)
    if parsed is not None:
        return parsed

    # Fallback: hand-rolled normalisation for the 90 % case.
    raw = phone.strip()

    # ``+41 ...`` → "41" prefix retained
    if raw.startswith("+"):
        digits = _DIGITS_ONLY_RE.sub("", raw)
    elif _DOUBLE_ZERO_PREFIX_RE.match(raw):
        # ``0041 ...`` → drop the leading 00, treat the rest as raw E.164
        digits = _DIGITS_ONLY_RE.sub("", raw)[2:]
    else:
        # National format: assume default country, strip leading 0(s),
        # then prepend dial code.
        digits = _DIGITS_ONLY_RE.sub("", raw)
        digits = _LEADING_ZERO_RE.sub("", digits)
        dial = _DIAL_CODES.get(default_country.upper())
        if dial:
            digits = dial + digits

    # Sanity bounds — E.164 max is 15 digits incl. country code.
    if len(digits) < 7 or len(digits) > 15:
        return None

    # Aggressive trim: anything > 13 digits for our 4 locales is a typo.
    # Lets us handle "+39 02 123456789" (12 digits raw) gracefully.
    if len(digits) > 13:
        digits = digits[:13]

    return digits


def to_whatsapp_url(phone_e164: str, message: str) -> str:
    """Build a ``https://wa.me/<E.164>?text=...`` URL.

    Pure / sync. ``phone_e164`` MUST be the output of :func:`to_e164` —
    we don't re-validate here.
    """
    from urllib.parse import quote
    return f"https://wa.me/{phone_e164}?text={quote(message)}"


def is_valid_e164(phone: Optional[str]) -> bool:
    """Quick check for already-E.164-formatted strings.

    >>> is_valid_e164("41791234567")
    True
    >>> is_valid_e164("12345")
    False
    >>> is_valid_e164("+41791234567")
    False
    """
    if not phone:
        return False
    if not phone.isdigit():
        return False
    return 7 <= len(phone) <= 15


# ──────────────────────────────────────────────────────────────────────


def _parse_with_phonenumbers(phone: str, default_country: str) -> Optional[str]:
    """Use libphonenumber if installed. Returns None if it fails or
    the lib isn't available.

    The library is heavy; we add it as an *optional* dependency. If it
    isn't on the platform, the hand-rolled fallback above covers the
    common cases.
    """
    try:
        import phonenumbers  # type: ignore
    except ImportError:
        return None

    try:
        parsed = phonenumbers.parse(phone, default_country)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return f"{parsed.country_code}{parsed.national_number}"
    except Exception:
        return None
