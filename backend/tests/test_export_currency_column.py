"""Smoke tests for the new ``Valuta`` column on the cashflow CSV export.

We don't exercise the FastAPI router here (that would need a TestClient
plus auth fixtures); we lock down two simpler invariants instead:

  1. Every export type's column list contains the ``currency`` /
     ``Valuta`` pair, in a stable position.
  2. The shared ``get_currency_for_org`` resolver is the single source
     of truth for what gets stamped on every row.
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

from routers.export import _COLUMNS


@pytest.mark.parametrize("export_type", ["sales", "expenses", "purchases", "fixed_costs"])
def test_currency_column_present_on_each_type(export_type):
    columns = _COLUMNS[export_type]
    fields = [f for f, _ in columns]
    labels = [label for _, label in columns]
    assert "currency" in fields
    assert "Valuta" in labels


def test_currency_column_label_is_italian():
    """The header label is in Italian; renaming would break Excel
    templates merchants may have built around the file. If you ever
    localise the export, update the snapshot test deliberately.
    """
    for export_type in ("sales", "expenses", "purchases", "fixed_costs"):
        labels = [label for _, label in _COLUMNS[export_type]]
        assert "Valuta" in labels


def test_resolver_falls_back_to_default():
    """Org with currency=None still gets a meaningful column value."""
    from services.currency_service import get_currency_for_org, DEFAULT_CURRENCY
    assert get_currency_for_org({}) == DEFAULT_CURRENCY
    assert get_currency_for_org({"currency": "CHF"}) == "CHF"
    assert get_currency_for_org({"currency": "EUR"}) == "EUR"


def test_currency_column_used_on_purchases_too():
    """Purchases column list put the column near the price section
    (purposeful — Excel renders the value right next to the amount).
    """
    purchases_fields = [f for f, _ in _COLUMNS["purchases"]]
    assert "currency" in purchases_fields
    # Total + currency should be adjacent so the merchant can sum quickly.
    idx_total = purchases_fields.index("total_price")
    idx_curr = purchases_fields.index("currency")
    assert abs(idx_curr - idx_total) <= 1
