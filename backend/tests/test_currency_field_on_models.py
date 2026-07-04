"""Tests for the new optional ``currency`` field on Product, ProductExtra,
ShippingOption and EventTicketTier (and their *Update DTOs).

The field is purposefully optional — ``None`` means "fall back to the
org's currency at read time". Explicit values must be one of the
supported ISO 4217 codes; anything else is rejected.

This is a foundation test: we only check the validator surface here.
The actual fallback resolution lives in
``services.currency_service.get_currency_for_product`` (Priority A2).
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
from pydantic import ValidationError

from models.product import ProductBase, ProductUpdate
from models.product_extra import ProductExtraBase, ProductExtraUpdate
from models.shipping_option import ShippingOptionBase, ShippingOptionUpdate
from models.event_ticket_tier import EventTicketTierBase, EventTicketTierUpdate


# ── Common payloads (minimum fields to instantiate each model) ──────────────

def _product(**extra):
    return ProductBase(name="Test", **extra)


def _product_extra(**extra):
    return ProductExtraBase(kind="optional", label="Add-on", price=5.0, **extra)


def _shipping_option(**extra):
    return ShippingOptionBase(label="Standard", base_price=4.90, **extra)


def _ticket_tier(**extra):
    return EventTicketTierBase(label="Standard", price=20.0, **extra)


# ── ProductBase.currency ────────────────────────────────────────────────────

class TestProductCurrency:
    def test_default_is_none(self):
        assert _product().currency is None

    @pytest.mark.parametrize("v", ["EUR", "CHF", "eur", "chf", " EUR ", " chf "])
    def test_accepts_supported(self, v):
        assert _product(currency=v).currency in ("EUR", "CHF")

    @pytest.mark.parametrize("v", [None, ""])
    def test_legacy_none_or_empty_preserved_as_none(self, v):
        assert _product(currency=v).currency is None

    @pytest.mark.parametrize("v", ["USD", "GBP", "XYZ"])
    def test_rejects_unsupported(self, v):
        with pytest.raises(ValidationError):
            _product(currency=v)

    def test_update_dto_validator_present(self):
        """ProductUpdate must apply the same constraints as ProductBase."""
        assert ProductUpdate(currency="chf").currency == "CHF"
        with pytest.raises(ValidationError):
            ProductUpdate(currency="USD")
        assert ProductUpdate(currency=None).currency is None

    def test_other_fields_unaffected(self):
        """Smoke check: validator addition didn't break sibling fields."""
        p = _product(unit_price=10.5, sku="SKU-1", currency="CHF")
        assert p.unit_price == 10.5
        assert p.sku == "SKU-1"
        assert p.currency == "CHF"


# ── ProductExtraBase.currency ───────────────────────────────────────────────

class TestProductExtraCurrency:
    def test_default_is_none(self):
        assert _product_extra().currency is None

    @pytest.mark.parametrize("v", ["EUR", "CHF", "eur", "chf"])
    def test_accepts_supported(self, v):
        assert _product_extra(currency=v).currency in ("EUR", "CHF")

    @pytest.mark.parametrize("v", ["USD", "XX"])
    def test_rejects_unsupported(self, v):
        with pytest.raises(ValidationError):
            _product_extra(currency=v)

    def test_update_dto_validator_present(self):
        assert ProductExtraUpdate(currency="EUR").currency == "EUR"
        with pytest.raises(ValidationError):
            ProductExtraUpdate(currency="USD")


# ── ShippingOptionBase.currency ─────────────────────────────────────────────

class TestShippingOptionCurrency:
    def test_default_is_none(self):
        assert _shipping_option().currency is None

    @pytest.mark.parametrize("v", ["EUR", "CHF"])
    def test_accepts_supported(self, v):
        assert _shipping_option(currency=v).currency == v

    def test_rejects_unsupported(self):
        with pytest.raises(ValidationError):
            _shipping_option(currency="USD")

    def test_update_dto_validator_present(self):
        assert ShippingOptionUpdate(currency="chf").currency == "CHF"
        with pytest.raises(ValidationError):
            ShippingOptionUpdate(currency="USD")


# ── EventTicketTierBase.currency ────────────────────────────────────────────

class TestEventTicketTierCurrency:
    def test_default_is_none(self):
        assert _ticket_tier().currency is None

    @pytest.mark.parametrize("v", ["EUR", "CHF"])
    def test_accepts_supported(self, v):
        assert _ticket_tier(currency=v).currency == v

    def test_rejects_unsupported(self):
        with pytest.raises(ValidationError):
            _ticket_tier(currency="USD")

    def test_update_dto_validator_present(self):
        assert EventTicketTierUpdate(currency="EUR").currency == "EUR"
        with pytest.raises(ValidationError):
            EventTicketTierUpdate(currency="USD")
