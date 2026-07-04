"""Snapshot tests for the currency-aware ``_fmt_total`` helper used by
``services.order_email_service``.

We don't render the whole HTML email here (that would couple the test
to copy strings and styles). Instead we lock down the output of
``_fmt_total`` for the (currency, locale) combinations that matter
for the first 5–10 CH merchants — Italian Ticino + a few German/French
edge cases — so a future refactor can't silently regress to ``€`` on
CHF receipts.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services.order_email_service import _fmt_total


# ── EUR rendering across locales ────────────────────────────────────────────


@pytest.mark.parametrize(
    "amount, locale, expected",
    [
        (49.5, "it", "\u20ac 49,50"),
        (49.5, "de", "\u20ac 49,50"),
        (49.5, "fr", "\u20ac 49,50"),
        (49.5, "en", "\u20ac 49.50"),
        (1234.5, "it", "\u20ac 1.234,50"),
        (1234.5, "en", "\u20ac 1,234.50"),
        (0, "it", "\u20ac 0,00"),
    ],
)
def test_eur_locale_variants(amount, locale, expected):
    assert _fmt_total(amount, "EUR", locale) == expected


# ── CHF rendering: stable across locales ────────────────────────────────────


@pytest.mark.parametrize(
    "amount, expected",
    [
        (49.5, "CHF 49.50"),
        (1234.5, "CHF 1'234.50"),
        (0, "CHF 0.00"),
        (1234567.89, "CHF 1'234'567.89"),
    ],
)
@pytest.mark.parametrize("locale", ["it", "de", "fr", "en", "it_CH", "de_CH"])
def test_chf_is_locale_independent(amount, locale, expected):
    """CHF formatting is stable across the four supported locales — the
    Swiss convention (apostrophe thousands, dot decimals) wins regardless.
    """
    assert _fmt_total(amount, "CHF", locale) == expected


# ── Backwards compatibility ─────────────────────────────────────────────────


def test_fmt_total_two_arg_signature_still_works():
    """Legacy call sites that don't pass locale must keep their behaviour.

    Default locale is ``"it"`` so EUR continues to render the European
    way and CHF stays Swiss-style.
    """
    assert _fmt_total(49.5, "EUR") == "\u20ac 49,50"
    assert _fmt_total(49.5, "CHF") == "CHF 49.50"


def test_fmt_total_one_arg_defaults_to_eur():
    """Even simpler legacy: ``_fmt_total(total)`` uses EUR + Italian."""
    assert _fmt_total(49.5) == "\u20ac 49,50"


# ── Defensive paths ─────────────────────────────────────────────────────────


def test_fmt_total_handles_negative_amount():
    """Refunds appear as negative subtotals; the sign must be preserved."""
    assert _fmt_total(-49.5, "EUR", "it") == "-\u20ac 49,50"
    assert _fmt_total(-49.5, "CHF", "de") == "-CHF 49.50"


def test_fmt_total_unknown_currency_falls_back_safely():
    """A bogus currency code (e.g. legacy data) must not crash the email
    render: the formatter prints the ISO code with European numerics."""
    out = _fmt_total(99.0, "USD", "it")
    assert out.startswith("USD ")
    assert "99,00" in out
