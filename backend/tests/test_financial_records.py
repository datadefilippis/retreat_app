"""Tests for financial record models — regression + new fields.

Validates that PurchaseRecordCreate, PurchaseRecordUpdate, and their
sibling models behave as expected after the consistency alignment changes.
"""

import pytest
from pydantic import ValidationError


# ── Purchase Record Models ─────────────────────────────────────────────────────

class TestPurchaseRecordCreate:
    """Regression: existing create behaviour must be preserved."""

    def test_create_minimal(self):
        from models.financial_record import PurchaseRecordCreate
        rec = PurchaseRecordCreate(date="2026-01-15")
        assert rec.date == "2026-01-15"
        assert rec.supplier_name is None
        assert rec.category is None

    def test_create_full_existing_fields(self):
        from models.financial_record import PurchaseRecordCreate
        rec = PurchaseRecordCreate(
            date="2026-03-01",
            supplier_name="Acme",
            quantity=10,
            unit="kg",
            unit_price=5.50,
            category="pomodori",
            category_macro="verdura",
            iva=22,
            due_date="2026-04-01",
            payment_status="pending",
            description="Lotto #42",
        )
        assert rec.supplier_name == "Acme"
        assert rec.quantity == 10.0
        assert rec.iva == 22.0
        assert rec.due_date == "2026-04-01"
        assert rec.payment_status.value == "pending"

    def test_create_with_invoice_number(self):
        from models.financial_record import PurchaseRecordCreate
        rec = PurchaseRecordCreate(
            date="2026-01-01",
            invoice_number="FT-2026-001",
        )
        assert rec.invoice_number == "FT-2026-001"

    def test_create_invalid_date_raises(self):
        from models.financial_record import PurchaseRecordCreate
        with pytest.raises(ValidationError):
            PurchaseRecordCreate(date="not-a-date")

    def test_create_invalid_iva_over_100_raises(self):
        from models.financial_record import PurchaseRecordCreate
        with pytest.raises(ValidationError):
            PurchaseRecordCreate(date="2026-01-01", iva=150)


class TestPurchaseRecordUpdate:
    """Regression + new fields in update model."""

    def test_update_existing_fields(self):
        from models.financial_record import PurchaseRecordUpdate
        upd = PurchaseRecordUpdate(
            quantity=20,
            unit_price=3.0,
            category="mele",
            iva=10,
        )
        assert upd.quantity == 20.0
        assert upd.unit_price == 3.0
        assert upd.category == "mele"
        assert upd.iva == 10.0

    def test_update_invoice_number_accepted(self):
        """New: invoice_number was added to PurchaseRecordUpdate."""
        from models.financial_record import PurchaseRecordUpdate
        upd = PurchaseRecordUpdate(invoice_number="FT-2026-099")
        assert upd.invoice_number == "FT-2026-099"

    def test_update_tags_accepted(self):
        """New: tags was added to PurchaseRecordUpdate."""
        from models.financial_record import PurchaseRecordUpdate
        upd = PurchaseRecordUpdate(tags=["urgente", "promo"])
        assert upd.tags == ["urgente", "promo"]

    def test_update_amount_accepted(self):
        """New: amount was added to PurchaseRecordUpdate."""
        from models.financial_record import PurchaseRecordUpdate
        upd = PurchaseRecordUpdate(amount=150.0)
        assert upd.amount == 150.0

    def test_update_extra_fields_ignored(self):
        """extra='ignore' means unknown fields are silently dropped."""
        from models.financial_record import PurchaseRecordUpdate
        upd = PurchaseRecordUpdate(
            category="test",
            total_with_iva=999,  # should be ignored (extra=ignore)
        )
        assert upd.category == "test"
        assert not hasattr(upd, "total_with_iva") or upd.model_dump(exclude_none=True).get("total_with_iva") is None

    def test_update_empty_produces_no_fields(self):
        from models.financial_record import PurchaseRecordUpdate
        upd = PurchaseRecordUpdate()
        data = upd.model_dump(exclude_none=True)
        assert data == {}


# ── Fixed Cost Models ──────────────────────────────────────────────────────────

class TestFixedCostModels:
    """Regression: FixedCost models still work after changes."""

    def test_create_fixed_cost(self):
        from models.financial_record import FixedCostCreate
        fc = FixedCostCreate(
            name="Affitto",
            amount=1200,
            frequency="mensile",
            category="affitto",
            start_date="2026-01-01",
        )
        assert fc.name == "Affitto"
        assert fc.amount == 1200.0
        assert fc.frequency.value == "mensile"

    def test_update_fixed_cost(self):
        from models.financial_record import FixedCostUpdate
        upd = FixedCostUpdate(amount=1300, is_active=False)
        assert upd.amount == 1300.0
        assert upd.is_active is False
