"""Tests for the currency-aware PDF receipt
(``services.order_pdf_service.generate_order_receipt``).

ReportLab compresses the PDF text streams, so plain substring search on
the byte output is unreliable. We instead spy on the shared
``core.currency_format.format_amount`` helper that the receipt builder
calls for every monetary cell, and verify that:

  * the formatter is invoked with the order's currency (CHF or EUR),
    never a hardcoded ``"EUR"`` for a CHF order;
  * the locale propagates from caller to formatter;
  * the legacy two-arg signature still produces a valid PDF blob.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services.order_pdf_service import generate_order_receipt


def _order(currency: str | None = None, total: float = 49.50) -> dict:
    """Minimum order dict the PDF builder expects."""
    base = {
        "id": "ord_test_pdf",
        "order_number": "ORD-001",
        "order_date": "2026-05-10",
        "customer_name": "Maria Rossi",
        "status": "confirmed",
        "payment_status": "paid",
        "items": [
            {
                "item_type": "physical",
                "product_name": "Test Product",
                "quantity": 1,
                "unit_price": total,
                "line_total": total,
            },
        ],
        "subtotal": total,
        "total": total,
    }
    if currency is not None:
        base["currency"] = currency
    return base


def _store() -> dict:
    return {"display_name": "Test Store", "contact_email": "shop@example.com"}


def _spy_calls():
    """Return a list that records every (amount, currency, locale) tuple
    that the order-pdf builder passes to ``format_amount``.

    The spy *delegates* to the real formatter so the resulting PDF is
    still a real PDF — only the call sites are observed.
    """
    from core import currency_format as cf
    real = cf.format_amount
    calls = []

    def spy(amount, currency, *, locale="it"):
        calls.append((amount, currency, locale))
        return real(amount, currency, locale=locale)

    return calls, spy


# ── CHF ─────────────────────────────────────────────────────────────────────


def test_chf_order_passes_chf_to_formatter():
    """Every monetary cell on a CHF receipt must be formatted as CHF."""
    calls, spy = _spy_calls()
    # The pdf builder imports format_amount lazily from core.currency_format,
    # so patching at the source module is what takes effect.
    with patch("core.currency_format.format_amount", side_effect=spy):
        pdf = generate_order_receipt(_order(currency="CHF"), _store())

    assert isinstance(pdf, bytes) and len(pdf) > 1000
    # 3 monetary cells: unit_price + line_total + subtotal.
    assert len(calls) == 3
    for amount, currency, locale in calls:
        assert currency == "CHF"
        assert locale == "it"


def test_chf_order_locale_propagates():
    """Caller-supplied locale flows through to format_amount."""
    calls, spy = _spy_calls()
    with patch("core.currency_format.format_amount", side_effect=spy):
        generate_order_receipt(_order(currency="CHF"), _store(), locale="de")
    assert all(c[2] == "de" for c in calls)


# ── EUR ─────────────────────────────────────────────────────────────────────


def test_eur_order_passes_eur_to_formatter():
    calls, spy = _spy_calls()
    with patch("core.currency_format.format_amount", side_effect=spy):
        generate_order_receipt(_order(currency="EUR"), _store())
    assert all(c[1] == "EUR" for c in calls)


def test_legacy_order_without_currency_falls_back_to_eur():
    """An order without currency must default to EUR via
    get_currency_for_order — preserves pre-refactor receipts.
    """
    calls, spy = _spy_calls()
    with patch("core.currency_format.format_amount", side_effect=spy):
        generate_order_receipt(_order(currency=None), _store())
    assert all(c[1] == "EUR" for c in calls)


# ── Backwards compatibility ─────────────────────────────────────────────────


def test_two_arg_signature_still_returns_bytes():
    pdf = generate_order_receipt(_order(currency="EUR"), _store())
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_three_arg_signature_with_locale_returns_valid_pdf():
    for locale in ("it", "en", "de", "fr"):
        pdf = generate_order_receipt(_order(currency="CHF"), _store(), locale=locale)
        assert pdf.startswith(b"%PDF-")
        assert len(pdf) > 1000
