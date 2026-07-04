"""Unit tests for ``backend/core/currency_format.py``.

Pure-function tests; no DB, no fixtures from ``conftest`` required.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

# Match the conftest path bootstrap so this module can run standalone.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from core.currency_format import (
    currency_symbol,
    format_amount,
    supported_currencies,
)


# ── CHF formatting ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "amount, expected",
    [
        (Decimal("0"), "CHF 0.00"),
        (Decimal("0.5"), "CHF 0.50"),
        (Decimal("49.5"), "CHF 49.50"),
        (Decimal("1234.5"), "CHF 1'234.50"),
        (Decimal("1234567.89"), "CHF 1'234'567.89"),
        (Decimal("-49.50"), "-CHF 49.50"),
        (49.5, "CHF 49.50"),                # float input
        ("49.50", "CHF 49.50"),             # string input
        (Decimal("0.005"), "CHF 0.01"),     # ROUND_HALF_UP
    ],
)
def test_chf_formatting(amount, expected):
    assert format_amount(amount, "CHF") == expected


def test_chf_ignores_locale_suffix():
    """CHF output is stable across it_CH / de_CH / fr_CH."""
    for locale in ("it", "de", "fr", "it_CH", "de_CH", "fr_CH"):
        assert format_amount(Decimal("99"), "CHF", locale=locale) == "CHF 99.00"


# ── EUR formatting ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "amount, locale, expected",
    [
        (Decimal("49.5"), "it", "\u20ac 49,50"),
        (Decimal("1234.5"), "it", "\u20ac 1.234,50"),
        (Decimal("1234567.89"), "de", "\u20ac 1.234.567,89"),
        (Decimal("1234.5"), "fr", "\u20ac 1.234,50"),
        (Decimal("1234.5"), "en", "\u20ac 1,234.50"),
        (Decimal("-49.50"), "it", "-\u20ac 49,50"),
        (Decimal("0"), "it", "\u20ac 0,00"),
    ],
)
def test_eur_formatting(amount, locale, expected):
    assert format_amount(amount, "EUR", locale=locale) == expected


def test_eur_default_locale_is_italian():
    assert format_amount(Decimal("1234.5"), "EUR") == "\u20ac 1.234,50"


# ── Defensive fallback ──────────────────────────────────────────────────────


def test_unknown_currency_falls_back_safely():
    """Unknown ISO code: emit code + European-style numerics; never crash."""
    out = format_amount(Decimal("1234.5"), "USD")
    assert out.startswith("USD ")
    assert "1.234,50" in out


def test_currency_code_case_insensitive():
    assert format_amount(Decimal("10"), "chf") == "CHF 10.00"
    assert format_amount(Decimal("10"), "eur") == "\u20ac 10,00"


# ── currency_symbol / supported_currencies ──────────────────────────────────


def test_currency_symbol_eur_returns_euro_glyph():
    assert currency_symbol("EUR") == "\u20ac"


def test_currency_symbol_chf_returns_iso_code():
    assert currency_symbol("CHF") == "CHF"


def test_currency_symbol_unknown_returns_code():
    assert currency_symbol("usd") == "USD"


def test_supported_currencies_contains_eur_and_chf():
    codes = supported_currencies()
    assert "EUR" in codes
    assert "CHF" in codes
