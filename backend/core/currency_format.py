"""
Server-side currency formatter for PDF receipts and outbound email.

Pairs with ``backend/core/numeric.py`` (which handles the *parse*
direction) and ``frontend/src/utils/currency.js`` (which renders for
the in-browser UI). This module is ASCII-friendly: ReportLab and many
email clients render unicode currency symbols inconsistently, so we
prefer the ISO code prefix (``CHF 49.50``) and emit the euro symbol
only when explicitly requested.

Public API:
    format_amount(amount, currency, *, locale="it") → str
    currency_symbol(currency) → str

Conventions:
  * CHF: ``CHF 1'234.50`` — apostrophe thousands, dot decimals, two
    decimals always (no trailing ``.-`` shorthand; consistent for
    machine-readable contexts like PDFs).
  * EUR: ``€ 1.234,50`` for it/de/fr locales; ``€ 1,234.50`` for en.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union

Numeric = Union[Decimal, int, float, str]


_SUPPORTED_CURRENCIES = ("EUR", "CHF")


def _quantize(amount: Numeric) -> Decimal:
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _split_groups(integer_part: str, group_sep: str) -> str:
    """Insert thousands separators into a digit string (sign-stripped)."""
    if len(integer_part) <= 3:
        return integer_part
    chunks = []
    while len(integer_part) > 3:
        chunks.insert(0, integer_part[-3:])
        integer_part = integer_part[:-3]
    chunks.insert(0, integer_part)
    return group_sep.join(chunks)


def _format_swiss(amount: Decimal) -> str:
    """``1234567.5`` → ``CHF 1'234'567.50``."""
    sign = "-" if amount < 0 else ""
    abs_str = f"{abs(amount):.2f}"  # always two decimals
    integer_part, _, fractional = abs_str.partition(".")
    grouped = _split_groups(integer_part, "'")
    return f"{sign}CHF {grouped}.{fractional}"


def _format_euro(amount: Decimal, locale: str) -> str:
    """``1234567.5`` → ``€ 1.234.567,50`` (it/de/fr) or ``€ 1,234,567.50`` (en)."""
    sign = "-" if amount < 0 else ""
    abs_str = f"{abs(amount):.2f}"
    integer_part, _, fractional = abs_str.partition(".")
    if locale.startswith("en"):
        grouped = _split_groups(integer_part, ",")
        return f"{sign}\u20ac {grouped}.{fractional}"
    # it / de / fr — European convention: dot thousands, comma decimal.
    grouped = _split_groups(integer_part, ".")
    return f"{sign}\u20ac {grouped},{fractional}"


def format_amount(
    amount: Numeric,
    currency: str,
    *,
    locale: str = "it",
) -> str:
    """Format ``amount`` for display in receipts/emails.

    ``locale`` is a short language code (``it``/``en``/``de``/``fr``);
    region suffixes are tolerated (``it_CH``, ``de_CH``) and ignored —
    the currency itself dictates the convention.

    Unknown currency → falls back to ISO-prefix with European style so
    the output is always readable, never blank.
    """
    quantized = _quantize(amount)
    code = currency.upper()

    if code == "CHF":
        return _format_swiss(quantized)
    if code == "EUR":
        return _format_euro(quantized, locale)

    # Defensive fallback: unknown ISO code. Print code + European style.
    sign = "-" if quantized < 0 else ""
    abs_str = f"{abs(quantized):.2f}"
    integer_part, _, fractional = abs_str.partition(".")
    grouped = _split_groups(integer_part, ".")
    return f"{sign}{code} {grouped},{fractional}"


def currency_symbol(currency: str) -> str:
    """Return a short user-facing symbol/code (``€`` for EUR, ``CHF`` for CHF)."""
    code = currency.upper()
    if code == "EUR":
        return "\u20ac"
    return code  # CHF and unknowns: use the ISO code itself.


def supported_currencies() -> tuple[str, ...]:
    return _SUPPORTED_CURRENCIES
