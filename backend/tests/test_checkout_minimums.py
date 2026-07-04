"""Unit tests for ``backend/core/checkout_minimums.py``."""

import os
import sys
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from core.checkout_minimums import (
    DEFAULT_MINIMUM,
    get_minimum,
    is_below_minimum,
    supported_currencies,
)


def test_eur_minimum_is_50_cents():
    assert get_minimum("EUR") == Decimal("0.50")


def test_chf_minimum_is_50_centimes():
    assert get_minimum("CHF") == Decimal("0.50")


def test_currency_lookup_is_case_insensitive():
    assert get_minimum("eur") == get_minimum("EUR")
    assert get_minimum("chf") == get_minimum("CHF")


def test_unknown_currency_returns_default():
    """Read paths must never crash on a bad currency string."""
    assert get_minimum("USD") == DEFAULT_MINIMUM
    assert get_minimum("") == DEFAULT_MINIMUM


@pytest.mark.parametrize(
    "amount, currency, expected",
    [
        (Decimal("0.49"), "EUR", True),
        (Decimal("0.50"), "EUR", False),    # equal: not below
        (Decimal("0.51"), "EUR", False),
        (Decimal("0.49"), "CHF", True),
        (Decimal("100.00"), "CHF", False),
    ],
)
def test_is_below_minimum(amount, currency, expected):
    assert is_below_minimum(amount, currency) is expected


def test_supported_currencies_includes_eur_and_chf():
    codes = supported_currencies()
    assert "EUR" in codes
    assert "CHF" in codes
