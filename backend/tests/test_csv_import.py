"""Tests for CSV import consistency — _TARGET_FIELDS, aliases, and processing.

Validates that:
1. All expected fields are present in _TARGET_FIELDS for each dataset type
2. Hardcoded aliases resolve correctly
3. _process_purchases_df handles new fields (due_date, invoice_number, payment_status)
4. Backward compatibility: DataFrames without new fields still parse correctly
"""

import pytest
import pandas as pd


# ── _TARGET_FIELDS completeness ────────────────────────────────────────────────

class TestTargetFieldsCompleteness:
    """Every model field that should be importable must be in _TARGET_FIELDS."""

    def test_purchases_target_fields_complete(self):
        from services.dataset_service import _TARGET_FIELDS
        from models.dataset import DatasetType
        fields = _TARGET_FIELDS[DatasetType.PURCHASES]
        expected = {
            "date", "supplier_name", "total_price", "quantity", "unit_price",
            "unit", "iva", "total_with_iva", "category", "category_macro",
            "description", "invoice_number", "due_date", "payment_status",
        }
        assert expected.issubset(set(fields.keys())), \
            f"Missing fields: {expected - set(fields.keys())}"

    def test_sales_target_fields_complete(self):
        from services.dataset_service import _TARGET_FIELDS
        from models.dataset import DatasetType
        fields = _TARGET_FIELDS[DatasetType.SALES]
        expected = {"date", "amount", "category", "description", "channel",
                    "due_date", "payment_status"}
        assert expected.issubset(set(fields.keys())), \
            f"Missing fields: {expected - set(fields.keys())}"

    def test_expenses_target_fields_complete(self):
        from services.dataset_service import _TARGET_FIELDS
        from models.dataset import DatasetType
        fields = _TARGET_FIELDS[DatasetType.EXPENSES]
        expected = {"date", "amount", "category", "description", "supplier",
                    "due_date", "payment_status", "is_paid"}
        assert expected.issubset(set(fields.keys())), \
            f"Missing fields: {expected - set(fields.keys())}"

    def test_fixed_costs_target_fields_complete(self):
        from services.dataset_service import _TARGET_FIELDS
        from models.dataset import DatasetType
        fields = _TARGET_FIELDS[DatasetType.FIXED_COSTS]
        expected = {"name", "amount", "frequency", "start_date", "end_date",
                    "category", "description"}
        assert expected.issubset(set(fields.keys())), \
            f"Missing fields: {expected - set(fields.keys())}"


# ── Alias resolution ──────────────────────────────────────────────────────────

class TestAliasResolution:
    """Hardcoded aliases must map to the correct target fields."""

    def test_purchase_aliases(self):
        from services.dataset_service import _HARDCODED_ALIASES
        assert _HARDCODED_ALIASES.get("data_scadenza") == "due_date"
        assert _HARDCODED_ALIASES.get("stato_pagamento") == "payment_status"
        assert _HARDCODED_ALIASES.get("pagato") == "is_paid"

    def test_column_normalize_accented(self):
        from services.dataset_service import _normalize_col
        assert _normalize_col("Prezzo Unitàrio") == "prezzo_unitario"
        assert _normalize_col("Quantità") == "quantita"
        assert _normalize_col("DATA SCADENZA") == "data_scadenza"
        assert _normalize_col("N. Fattura") == "n_fattura"


# ── _process_purchases_df ─────────────────────────────────────────────────────

class TestProcessPurchasesDf:
    """Processing logic for purchase DataFrames."""

    def test_backwards_compat_no_new_fields(self):
        """Existing files without new columns must still parse correctly."""
        from services.dataset_service import _process_purchases_df
        df = pd.DataFrame({
            'date': ['2026-01-15', '2026-01-16'],
            'supplier_name': ['Acme', 'Beta'],
            'quantity': [10, 5],
            'unit_price': [2.5, 3.0],
            'category': ['mele', 'pere'],
        })
        rows, errors = _process_purchases_df(df)
        assert len(errors) == 0
        assert len(rows) == 2
        assert rows[0]['supplier_name'] == 'Acme'
        assert rows[0]['total_price'] == 25.0
        # New fields should be None when not in DataFrame
        assert rows[0].get('invoice_number') is None
        assert rows[0].get('due_date') is None
        assert rows[0].get('payment_status') is None

    def test_with_new_fields(self):
        """New columns (due_date, invoice_number, payment_status) are extracted."""
        from services.dataset_service import _process_purchases_df
        df = pd.DataFrame({
            'date': ['2026-02-01'],
            'supplier_name': ['Gamma'],
            'total_price': [100.0],
            'invoice_number': ['FT-001'],
            'due_date': ['2026-03-01'],
            'payment_status': ['pagato'],
        })
        rows, errors = _process_purchases_df(df)
        assert len(errors) == 0
        assert len(rows) == 1
        assert rows[0]['invoice_number'] == 'FT-001'
        assert rows[0]['due_date'] == '2026-03-01'
        assert rows[0]['payment_status'] == 'paid'  # 'pagato' → 'paid'

    def test_payment_status_mapping(self):
        """Italian payment status values are mapped to English."""
        from services.dataset_service import _process_purchases_df
        df = pd.DataFrame({
            'date': ['2026-01-01', '2026-01-02', '2026-01-03'],
            'supplier_name': ['A', 'B', 'C'],
            'total_price': [10, 20, 30],
            'payment_status': ['In attesa', 'Scaduto', 'Annullato'],
        })
        rows, errors = _process_purchases_df(df)
        assert rows[0]['payment_status'] == 'pending'
        assert rows[1]['payment_status'] == 'overdue'
        assert rows[2]['payment_status'] == 'cancelled'

    def test_missing_required_date_errors(self):
        """Missing date column produces an error."""
        from services.dataset_service import _process_purchases_df
        df = pd.DataFrame({
            'supplier_name': ['Acme'],
            'total_price': [100],
        })
        rows, errors = _process_purchases_df(df)
        assert len(rows) == 0
        assert len(errors) > 0
        assert 'date' in errors[0].lower()

    def test_iva_computation_preserved(self):
        """IVA computation regression — total_with_iva = total * (1 + iva/100)."""
        from services.dataset_service import _process_purchases_df
        df = pd.DataFrame({
            'date': ['2026-01-01'],
            'supplier_name': ['Test'],
            'quantity': [10],
            'unit_price': [10.0],
            'iva': [22],
        })
        rows, errors = _process_purchases_df(df)
        assert len(rows) == 1
        assert rows[0]['total_price'] == 100.0
        assert rows[0]['total_with_iva'] == 122.0

    def test_column_map_aliases_applied(self):
        """Column map renames are applied before processing."""
        from services.dataset_service import _process_purchases_df
        df = pd.DataFrame({
            'Data Acquisto': ['2026-01-01'],
            'Fornitore': ['Test'],
            'Importo': [50.0],
        })
        column_map = {
            'data_acquisto': 'date',
            'fornitore': 'supplier_name',
            'importo': 'total_price',
        }
        rows, errors = _process_purchases_df(df, column_map=column_map)
        assert len(rows) == 1
        assert rows[0]['supplier_name'] == 'Test'
        assert rows[0]['total_price'] == 50.0
