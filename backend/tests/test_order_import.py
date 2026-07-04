"""Tests for order import — column mapping, row processing, grouping, propagation.

Covers:
  1. Target fields and alias resolution
  2. Row processing: required fields, defaults, edge cases
  3. Date parsing: multi-format, Italian months, broken dates
  4. Amount parsing: EU/US/mixed formats, currency symbols, negatives
  5. Payment status normalization
  6. Grouping logic: (customer + date) → one order
  7. Customer resolution and auto-creation
  8. Full import pipeline with auto-confirm → SalesRecords propagation
  9. Stress: empty files, all-error files, mixed valid/invalid rows
  10. Column mapping analysis: auto-mapped vs needs-mapping
"""

import pytest
import pandas as pd
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch, MagicMock
from collections import defaultdict


# ══════════════════════════════════════════════════════════════════════════════
# 1. TARGET FIELDS & ALIASES
# ══════════════════════════════════════════════════════════════════════════════

class TestOrderTargetFields:
    """ORDER_TARGET_FIELDS must contain all expected importable fields."""

    def test_required_fields_present(self):
        from services.order_import_service import ORDER_TARGET_FIELDS
        required = {k for k, v in ORDER_TARGET_FIELDS.items() if v["required"]}
        assert required == {"customer_name", "date", "product_name", "unit_price"}

    def test_optional_fields_present(self):
        from services.order_import_service import ORDER_TARGET_FIELDS
        optional = {k for k, v in ORDER_TARGET_FIELDS.items() if not v["required"]}
        expected = {"customer_email", "quantity", "discount_pct", "category", "sku", "notes", "due_date", "payment_status"}
        assert expected == optional

    def test_all_fields_have_labels(self):
        from services.order_import_service import ORDER_TARGET_FIELDS
        for field, meta in ORDER_TARGET_FIELDS.items():
            assert "label" in meta, f"Field '{field}' missing label"
            assert "required" in meta, f"Field '{field}' missing required flag"


class TestOrderAliasResolution:
    """Hardcoded aliases must map to the correct target fields."""

    def test_customer_aliases(self):
        from services.order_import_service import _ORDER_ALIASES
        assert _ORDER_ALIASES["cliente"] == "customer_name"
        assert _ORDER_ALIASES["customer"] == "customer_name"
        assert _ORDER_ALIASES["nome_cliente"] == "customer_name"
        assert _ORDER_ALIASES["ragione_sociale"] == "customer_name"

    def test_date_aliases(self):
        from services.order_import_service import _ORDER_ALIASES
        assert _ORDER_ALIASES["data"] == "date"
        assert _ORDER_ALIASES["data_ordine"] == "date"
        assert _ORDER_ALIASES["order_date"] == "date"

    def test_product_aliases(self):
        from services.order_import_service import _ORDER_ALIASES
        assert _ORDER_ALIASES["prodotto"] == "product_name"
        assert _ORDER_ALIASES["nome_prodotto"] == "product_name"
        assert _ORDER_ALIASES["articolo"] == "product_name"

    def test_price_aliases(self):
        from services.order_import_service import _ORDER_ALIASES
        assert _ORDER_ALIASES["prezzo"] == "unit_price"
        assert _ORDER_ALIASES["prezzo_unitario"] == "unit_price"
        assert _ORDER_ALIASES["importo"] == "unit_price"

    def test_discount_aliases(self):
        from services.order_import_service import _ORDER_ALIASES
        assert _ORDER_ALIASES["sconto"] == "discount_pct"
        assert _ORDER_ALIASES["sconto_percentuale"] == "discount_pct"

    def test_due_date_aliases(self):
        from services.order_import_service import _ORDER_ALIASES
        assert _ORDER_ALIASES["scadenza"] == "due_date"
        assert _ORDER_ALIASES["data_scadenza"] == "due_date"

    def test_email_aliases(self):
        from services.order_import_service import _ORDER_ALIASES
        assert _ORDER_ALIASES["email"] == "customer_email"
        assert _ORDER_ALIASES["email_cliente"] == "customer_email"
        assert _ORDER_ALIASES["mail"] == "customer_email"
        assert _ORDER_ALIASES["e_mail"] == "customer_email"

    def test_normalize_accented_columns(self):
        from services.dataset_service import _normalize_col
        # These accented columns should normalize to alias keys
        assert _normalize_col("Quantità") == "quantita"
        assert _normalize_col("Prezzo Unitàrio") == "prezzo_unitario"
        assert _normalize_col("CLIENTE") == "cliente"
        assert _normalize_col("  Data Ordine ") == "data_ordine"


# ══════════════════════════════════════════════════════════════════════════════
# 2. ROW PROCESSING — _process_order_rows
# ══════════════════════════════════════════════════════════════════════════════

class TestProcessOrderRows:
    """Test the core row processing logic."""

    def _process(self, data, extra_map=None):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame(data)
        col_map = dict(_ORDER_ALIASES)
        if extra_map:
            col_map.update(extra_map)
        return _process_order_rows(df, col_map)

    # ── Happy path ─────────────────────────────────────────────────────────

    def test_basic_valid_row(self):
        rows, errors = self._process({
            "cliente": ["Mario Rossi"],
            "data": ["2026-03-01"],
            "prodotto": ["Pizza"],
            "prezzo": ["10.00"],
        })
        assert len(rows) == 1
        assert len(errors) == 0
        assert rows[0]["customer_name"] == "Mario Rossi"
        assert rows[0]["date"] == "2026-03-01"
        assert rows[0]["product_name"] == "Pizza"
        assert rows[0]["unit_price"] == 10.0
        assert rows[0]["quantity"] == 1.0  # default
        assert rows[0]["discount_pct"] == 0.0  # default
        assert rows[0]["line_total"] == 10.0
        assert rows[0]["payment_status"] == "pending"  # default

    def test_all_fields_populated(self):
        rows, errors = self._process({
            "cliente": ["Anna Verdi"],
            "data": ["15/04/2026"],
            "prodotto": ["Vino Rosso"],
            "prezzo_unitario": ["18,50"],
            "quantita": ["3"],
            "sconto": ["10"],
            "categoria": ["beverage"],
            "codice_prodotto": ["VIN-001"],
            "note": ["Ordine speciale"],
            "scadenza": ["2026-05-01"],
            "stato_pagamento": ["pagato"],
        })
        assert len(rows) == 1
        assert len(errors) == 0
        r = rows[0]
        assert r["customer_name"] == "Anna Verdi"
        assert r["date"] == "2026-04-15"
        assert r["product_name"] == "Vino Rosso"
        assert r["unit_price"] == 18.5
        assert r["quantity"] == 3.0
        assert r["discount_pct"] == 10.0
        assert r["line_total"] == round(18.5 * 3 * 0.9, 2)  # 49.95
        assert r["category"] == "beverage"
        assert r["sku"] == "VIN-001"
        assert r["notes"] == "Ordine speciale"
        assert r["due_date"] == "2026-05-01"
        assert r["payment_status"] == "paid"

    # ── Customer email ──────────────────────────────────────────────────

    def test_email_parsed(self):
        rows, _ = self._process({
            "cliente": ["Mario"],
            "email": ["mario@test.com"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["10"],
        })
        assert rows[0]["customer_email"] == "mario@test.com"

    def test_email_empty_is_none(self):
        rows, _ = self._process({
            "cliente": ["Mario"],
            "email": [""],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["10"],
        })
        assert rows[0]["customer_email"] is None

    def test_email_without_at_is_none(self):
        rows, _ = self._process({
            "cliente": ["Mario"],
            "email": ["not-an-email"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["10"],
        })
        assert rows[0]["customer_email"] is None

    def test_email_absent_is_none(self):
        """No email column at all → customer_email is None."""
        rows, _ = self._process({
            "cliente": ["Mario"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["10"],
        })
        assert rows[0]["customer_email"] is None

    def test_multiple_rows(self):
        rows, errors = self._process({
            "cliente": ["A", "B", "C"],
            "data": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "prodotto": ["P1", "P2", "P3"],
            "prezzo": ["10", "20", "30"],
        })
        assert len(rows) == 3
        assert len(errors) == 0

    # ── Defaults ───────────────────────────────────────────────────────────

    def test_quantity_defaults_to_1(self):
        rows, _ = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["100"],
        })
        assert rows[0]["quantity"] == 1.0

    def test_discount_defaults_to_0(self):
        rows, _ = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["100"],
        })
        assert rows[0]["discount_pct"] == 0.0
        assert rows[0]["line_total"] == 100.0

    def test_negative_quantity_defaults_to_1(self):
        rows, _ = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["50"],
            "quantita": ["-5"],
        })
        assert rows[0]["quantity"] == 1.0

    def test_zero_quantity_defaults_to_1(self):
        rows, _ = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["50"],
            "quantita": ["0"],
        })
        assert rows[0]["quantity"] == 1.0

    def test_invalid_discount_defaults_to_0(self):
        rows, _ = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["100"],
            "sconto": ["150"],  # > 100 → reset to 0
        })
        assert rows[0]["discount_pct"] == 0.0

    def test_negative_discount_defaults_to_0(self):
        rows, _ = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["100"],
            "sconto": ["-10"],
        })
        assert rows[0]["discount_pct"] == 0.0

    # ── Line total computation ─────────────────────────────────────────────

    def test_line_total_with_discount(self):
        rows, _ = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["100"],
            "quantita": ["2"],
            "sconto": ["25"],
        })
        # 100 * 2 * (1 - 0.25) = 150.0
        assert rows[0]["line_total"] == 150.0

    def test_line_total_rounding(self):
        rows, _ = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["9.99"],
            "quantita": ["3"],
            "sconto": ["7"],
        })
        # 9.99 * 3 * 0.93 = 27.8721 → 27.87
        assert rows[0]["line_total"] == 27.87

    # ── Required field validation ──────────────────────────────────────────

    def test_missing_customer_skipped(self):
        rows, errors = self._process({
            "cliente": ["", "Valid"],
            "data": ["2026-01-01", "2026-01-02"],
            "prodotto": ["P1", "P2"],
            "prezzo": ["10", "20"],
        })
        assert len(rows) == 1
        assert len(errors) == 1
        assert "cliente mancante" in errors[0].lower()

    def test_missing_date_skipped(self):
        rows, errors = self._process({
            "cliente": ["X"],
            "data": [""],
            "prodotto": ["P"],
            "prezzo": ["10"],
        })
        assert len(rows) == 0
        assert len(errors) == 1
        assert "data" in errors[0].lower()

    def test_missing_product_skipped(self):
        rows, errors = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": [""],
            "prezzo": ["10"],
        })
        assert len(rows) == 0
        assert "prodotto mancante" in errors[0].lower()

    def test_missing_price_skipped(self):
        rows, errors = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": [""],
        })
        assert len(rows) == 0
        assert "prezzo" in errors[0].lower()

    def test_invalid_price_skipped(self):
        rows, errors = self._process({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["abc"],
        })
        assert len(rows) == 0
        assert "prezzo" in errors[0].lower()

    def test_invalid_date_skipped(self):
        rows, errors = self._process({
            "cliente": ["X"],
            "data": ["not-a-date"],
            "prodotto": ["P"],
            "prezzo": ["10"],
        })
        assert len(rows) == 0
        assert "data" in errors[0].lower()


# ══════════════════════════════════════════════════════════════════════════════
# 3. DATE PARSING EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

class TestDateParsing:
    """Test clean_date via _process_order_rows with various date formats."""

    def _parse_date(self, date_str):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["X"], "data": [date_str], "prodotto": ["P"], "prezzo": ["10"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        return rows[0]["date"] if rows else None

    def test_iso_format(self):
        assert self._parse_date("2026-03-15") == "2026-03-15"

    def test_european_slash(self):
        assert self._parse_date("15/03/2026") == "2026-03-15"

    def test_european_dash(self):
        assert self._parse_date("15-03-2026") == "2026-03-15"

    def test_european_dot(self):
        assert self._parse_date("15.03.2026") == "2026-03-15"

    def test_excel_timestamp(self):
        assert self._parse_date("2026-03-15 00:00:00") == "2026-03-15"

    def test_iso8601_with_time(self):
        assert self._parse_date("2026-03-15T14:30:00") == "2026-03-15"

    def test_italian_month_full(self):
        assert self._parse_date("15 marzo 2026") == "2026-03-15"

    def test_italian_month_short(self):
        assert self._parse_date("15 mar 2026") == "2026-03-15"

    def test_compact_format(self):
        assert self._parse_date("20260315") == "2026-03-15"

    def test_year_first_slash(self):
        assert self._parse_date("2026/03/15") == "2026-03-15"

    def test_none_for_empty(self):
        assert self._parse_date("") is None

    def test_none_for_garbage(self):
        assert self._parse_date("xyz-abc") is None

    def test_none_for_nat(self):
        assert self._parse_date("NaT") is None

    def test_none_for_na(self):
        assert self._parse_date("N/A") is None


# ══════════════════════════════════════════════════════════════════════════════
# 4. AMOUNT PARSING EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

class TestAmountParsing:
    """Test clean_amount via _process_order_rows with various numeric formats."""

    def _parse_amount(self, amount_str):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["X"], "data": ["2026-01-01"], "prodotto": ["P"], "prezzo": [amount_str],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        return rows[0]["unit_price"] if rows else None

    def test_integer(self):
        assert self._parse_amount("100") == 100.0

    def test_decimal_dot(self):
        assert self._parse_amount("10.50") == 10.5

    def test_decimal_comma(self):
        assert self._parse_amount("10,50") == 10.5

    def test_european_thousands(self):
        assert self._parse_amount("1.234,56") == 1234.56

    def test_us_thousands(self):
        assert self._parse_amount("1,234.56") == 1234.56

    def test_euro_symbol(self):
        assert self._parse_amount("€ 10,50") == 10.5

    def test_dollar_symbol(self):
        assert self._parse_amount("$100.00") == 100.0

    def test_whitespace_around(self):
        assert self._parse_amount("  25.00  ") == 25.0

    def test_empty_string_fails(self):
        assert self._parse_amount("") is None

    def test_text_fails(self):
        assert self._parse_amount("gratuito") is None

    def test_zero_is_valid(self):
        assert self._parse_amount("0") == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# 5. PAYMENT STATUS NORMALIZATION
# ══════════════════════════════════════════════════════════════════════════════

class TestPaymentStatus:
    """Test payment_status mapping from various inputs."""

    def _parse_status(self, status_str):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["X"], "data": ["2026-01-01"], "prodotto": ["P"],
            "prezzo": ["10"], "stato_pagamento": [status_str],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        return rows[0]["payment_status"] if rows else None

    def test_paid_english(self):
        assert self._parse_status("paid") == "paid"

    def test_pagato_italian(self):
        assert self._parse_status("pagato") == "paid"

    def test_si_italian(self):
        assert self._parse_status("si") == "paid"

    def test_si_accented(self):
        assert self._parse_status("sì") == "paid"

    def test_yes_english(self):
        assert self._parse_status("yes") == "paid"

    def test_true_boolean(self):
        assert self._parse_status("true") == "paid"

    def test_overdue_english(self):
        assert self._parse_status("overdue") == "overdue"

    def test_scaduto_italian(self):
        assert self._parse_status("scaduto") == "overdue"

    def test_pending_default(self):
        assert self._parse_status("pending") == "pending"

    def test_empty_defaults_to_pending(self):
        assert self._parse_status("") == "pending"

    def test_unknown_defaults_to_pending(self):
        assert self._parse_status("in_attesa") == "pending"

    def test_none_defaults_to_pending(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["X"], "data": ["2026-01-01"], "prodotto": ["P"], "prezzo": ["10"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert rows[0]["payment_status"] == "pending"


# ══════════════════════════════════════════════════════════════════════════════
# 6. COLUMN MAPPING ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalyzeOrderImport:
    """Test analyze_order_import for auto-mapped vs needs-mapping detection."""

    @pytest.mark.asyncio
    async def test_auto_mapped_with_standard_columns(self):
        import io
        from services.order_import_service import analyze_order_import
        csv = "cliente,data,prodotto,prezzo_unitario\nA,2026-01-01,P,10"
        content = csv.encode("utf-8")
        result = await analyze_order_import(content, "test.csv", "org_1")
        assert result["status"] == "auto_mapped"
        assert len(result["missing_required"]) == 0

    @pytest.mark.asyncio
    async def test_needs_mapping_missing_required(self):
        import io
        from services.order_import_service import analyze_order_import
        csv = "nome,valore\nA,10"
        content = csv.encode("utf-8")
        result = await analyze_order_import(content, "test.csv", "org_1")
        assert result["status"] == "needs_column_mapping"
        assert len(result["missing_required"]) > 0

    @pytest.mark.asyncio
    async def test_needs_mapping_unmapped_columns(self):
        from services.order_import_service import analyze_order_import
        csv = "cliente,data,prodotto,prezzo_unitario,colonna_extra\nA,2026-01-01,P,10,x"
        content = csv.encode("utf-8")
        result = await analyze_order_import(content, "test.csv", "org_1")
        assert result["status"] == "needs_column_mapping"
        assert "colonna_extra" in result["unmapped_columns"]

    @pytest.mark.asyncio
    async def test_preview_rows_present(self):
        from services.order_import_service import analyze_order_import
        csv = "cliente,data,prodotto,prezzo_unitario\nA,2026-01-01,P1,10\nB,2026-01-02,P2,20\nC,2026-01-03,P3,30\nD,2026-01-04,P4,40"
        content = csv.encode("utf-8")
        result = await analyze_order_import(content, "test.csv", "org_1")
        assert len(result["preview_rows"]) == 3  # max 3
        assert "all_file_columns" in result

    @pytest.mark.asyncio
    async def test_italian_alias_auto_mapping(self):
        from services.order_import_service import analyze_order_import
        csv = "Cliente,Data Ordine,Prodotto,Prezzo Unitàrio\nA,2026-01-01,P,10"
        content = csv.encode("utf-8")
        result = await analyze_order_import(content, "test.csv", "org_1")
        assert result["status"] == "auto_mapped"

    @pytest.mark.asyncio
    async def test_unsupported_file_format_raises(self):
        from services.order_import_service import analyze_order_import
        with pytest.raises(ValueError, match="non supportato"):
            await analyze_order_import(b"data", "test.pdf", "org_1")


# ══════════════════════════════════════════════════════════════════════════════
# 7. MIXED VALID/INVALID ROWS
# ══════════════════════════════════════════════════════════════════════════════

class TestMixedRows:
    """Ensure valid rows are processed even when some rows have errors."""

    def test_mixed_valid_and_invalid(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["Good", "", "Good2", "Good3"],
            "data": ["2026-01-01", "2026-01-02", "not-a-date", "2026-01-04"],
            "prodotto": ["P1", "P2", "P3", ""],
            "prezzo": ["10", "20", "30", "40"],
        })
        rows, errors = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert len(rows) == 1  # only first row valid
        assert len(errors) == 3  # missing customer, bad date, missing product
        assert rows[0]["customer_name"] == "Good"

    def test_all_invalid_rows(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["", "", ""],
            "data": ["", "", ""],
            "prodotto": ["", "", ""],
            "prezzo": ["", "", ""],
        })
        rows, errors = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert len(rows) == 0
        assert len(errors) == 3

    def test_nan_values_treated_as_missing(self):
        import numpy as np
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": [np.nan],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["10"],
        })
        rows, errors = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert len(rows) == 0
        assert len(errors) == 1

    def test_whitespace_only_customer_treated_as_missing(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["   "],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["10"],
        })
        rows, errors = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert len(rows) == 0

    def test_dash_treated_as_missing(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["-"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["10"],
        })
        rows, errors = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert len(rows) == 0


# ══════════════════════════════════════════════════════════════════════════════
# 8. GROUPING LOGIC
# ══════════════════════════════════════════════════════════════════════════════

class TestGroupingLogic:
    """Test that rows are grouped by (customer_name, date) correctly."""

    def test_same_customer_same_date_grouped(self):
        """Two rows with same customer + date should yield 1 group."""
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        from collections import defaultdict

        df = pd.DataFrame({
            "cliente": ["Mario", "Mario"],
            "data": ["2026-01-01", "2026-01-01"],
            "prodotto": ["Pizza", "Pasta"],
            "prezzo": ["10", "12"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        groups = defaultdict(list)
        for r in rows:
            groups[(r["customer_name"], r["date"])].append(r)
        assert len(groups) == 1
        assert len(groups[("Mario", "2026-01-01")]) == 2

    def test_different_customers_separate_groups(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        from collections import defaultdict

        df = pd.DataFrame({
            "cliente": ["Mario", "Luigi"],
            "data": ["2026-01-01", "2026-01-01"],
            "prodotto": ["P1", "P2"],
            "prezzo": ["10", "20"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        groups = defaultdict(list)
        for r in rows:
            groups[(r["customer_name"], r["date"])].append(r)
        assert len(groups) == 2

    def test_same_customer_different_dates_separate(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        from collections import defaultdict

        df = pd.DataFrame({
            "cliente": ["Mario", "Mario"],
            "data": ["2026-01-01", "2026-01-02"],
            "prodotto": ["P1", "P2"],
            "prezzo": ["10", "20"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        groups = defaultdict(list)
        for r in rows:
            groups[(r["customer_name"], r["date"])].append(r)
        assert len(groups) == 2

    def test_three_customers_two_dates_correct_groups(self):
        """Example CSV scenario: 3 customers, 2 dates → correct number of groups."""
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        from collections import defaultdict

        df = pd.DataFrame({
            "cliente": ["Mario", "Mario", "Luigi", "Anna", "Anna", "Mario"],
            "data": ["2026-01-01", "2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02", "2026-01-02"],
            "prodotto": ["P1", "P2", "P3", "P4", "P5", "P6"],
            "prezzo": ["10", "12", "15", "8", "20", "30"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        groups = defaultdict(list)
        for r in rows:
            groups[(r["customer_name"], r["date"])].append(r)
        # Mario/01: 2 items, Luigi/01: 1, Anna/02: 2, Mario/02: 1
        assert len(groups) == 4
        assert len(groups[("Mario", "2026-01-01")]) == 2
        assert len(groups[("Luigi", "2026-01-01")]) == 1
        assert len(groups[("Anna", "2026-01-02")]) == 2
        assert len(groups[("Mario", "2026-01-02")]) == 1


# ══════════════════════════════════════════════════════════════════════════════
# 9. FULL IMPORT PIPELINE (mocked DB)
# ══════════════════════════════════════════════════════════════════════════════

class TestExecuteOrderImport:
    """Test execute_order_import with mocked repositories.

    The import pipeline creates orders directly as CONFIRMED (no draft→confirm),
    batch-inserts SalesRecords, and triggers hooks once at the end.
    """

    def _make_csv(self, rows_str):
        return rows_str.encode("utf-8")

    def _base_patches(self):
        """Return an ExitStack that enters the standard set of patches.

        IMPORTANT: ``execute_order_import`` makes async calls to MongoDB
        via ``organization_repository.find_by_id`` (CH compliance v1
        currency lookup) and ``check_module_access``/``record_module_usage``
        (Onda 9.Y.0 billing gate). If those aren't mocked, motor binds
        its client to the first test's event loop, then every subsequent
        test in the same file fails with ``RuntimeError: Event loop is
        closed``. Hence the comprehensive mock set below.
        """
        stack = ExitStack()
        mocks = (
            stack.enter_context(patch("services.order_import_service.build_customer_name_map")),
            stack.enter_context(patch("repositories.customer_repository")),
            stack.enter_context(patch("repositories.order_repository")),
            stack.enter_context(patch("repositories.sales_repository")),
            stack.enter_context(patch("services.order_service._trigger_module_hooks", new_callable=AsyncMock)),
            stack.enter_context(patch("database.orders_collection")),
        )
        # Additional patches that don't need to be exposed to per-test
        # callers but must be in place to keep motor off the real loop.
        stack.enter_context(patch(
            "repositories.organization_repository.find_by_id",
            new_callable=AsyncMock,
            return_value={"id": "org_test", "currency": "EUR"},
        ))
        stack.enter_context(patch(
            "services.module_access.check_module_access",
            new_callable=AsyncMock,
        ))
        stack.enter_context(patch(
            "services.module_access.record_module_usage",
            new_callable=AsyncMock,
        ))
        return stack, mocks

    def _setup_mocks(self, mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo,
                     mock_orders_coll=None,
                     customer_map=None, find_by_id_map=None, orders_inserted=None):
        """Wire up common mock defaults."""
        mock_cmap.return_value = customer_map or {}
        mock_cust_repo.find_by_id = AsyncMock(
            side_effect=lambda cid, oid: (find_by_id_map or {}).get(cid)
        )
        _orders = orders_inserted if orders_inserted is not None else []
        mock_order_repo.get_next_order_number = AsyncMock(return_value="ORD-0001")
        mock_sales_repo.insert_many = AsyncMock(side_effect=lambda docs: len(docs))
        # Mock orders_collection.insert_many for batch insert
        if mock_orders_coll is not None:
            async def _capture_insert_many(docs):
                _orders.extend(docs)
                # Simulate MongoDB adding _id
                class FakeResult:
                    inserted_ids = list(range(len(docs)))
                return FakeResult()
            mock_orders_coll.insert_many = AsyncMock(side_effect=_capture_insert_many)

    @pytest.mark.asyncio
    async def test_basic_import_creates_orders(self):
        """Import 3 rows, 2 customers, 2 dates → 2 orders."""
        csv = self._make_csv(
            "cliente,data,prodotto,prezzo\n"
            "Mario,2026-01-01,Pizza,10\n"
            "Mario,2026-01-01,Pasta,12\n"
            "Luigi,2026-01-02,Birra,5\n"
        )

        fake_mario = MagicMock(id="cust_mario", name="Mario")
        fake_luigi = MagicMock(id="cust_luigi", name="Luigi")
        orders_inserted = []

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"mario": "cust_mario", "luigi": "cust_luigi"},
                              find_by_id_map={"cust_mario": fake_mario, "cust_luigi": fake_luigi},
                              orders_inserted=orders_inserted)
            result = await self._run_import(csv)

        assert result["orders_created"] == 2
        assert result["customers_created"] == 0
        assert result["rows_processed"] == 3
        assert result["sales_records_generated"] == 3  # 3 line items total

    @pytest.mark.asyncio
    async def test_auto_creates_unknown_customer(self):
        """Import with unknown customer → auto-create."""
        csv = self._make_csv(
            "cliente,data,prodotto,prezzo\n"
            "New Customer,2026-01-01,Pizza,10\n"
        )

        created_customers = []
        fake_new = MagicMock(id="cust_new", name="New Customer")

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              find_by_id_map={"cust_new": fake_new})
            mock_cust_repo.create = AsyncMock(side_effect=lambda org, data: (
                created_customers.append(data.name) or fake_new
            ))
            result = await self._run_import(csv)

        assert result["customers_created"] == 1
        assert "New Customer" in created_customers

    @pytest.mark.asyncio
    async def test_all_rows_invalid_raises(self):
        """File where every row fails validation → raises ValueError.

        Even though this test expects an early ValueError before any DB
        write, ``execute_order_import`` now calls
        ``organization_repository.find_by_id`` upfront (CH compliance v1
        currency lookup). We need the base patches to keep motor off the
        real loop — otherwise this test fails with ``Event loop is closed``
        when run after another test in the same session.
        """
        csv = self._make_csv(
            "cliente,data,prodotto,prezzo\n"
            ",bad-date,,\n"
            ",,,\n"
        )
        stack, _ = self._base_patches()
        with stack:
            with pytest.raises(ValueError, match="Nessuna riga valida"):
                await self._run_import(csv)

    @pytest.mark.asyncio
    async def test_orders_created_as_confirmed(self):
        """Orders should be inserted directly with status=confirmed."""
        csv = self._make_csv(
            "cliente,data,prodotto,prezzo\n"
            "A,2026-01-01,P1,10\n"
        )
        orders_inserted = []

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"a": "cust_a"},
                              find_by_id_map={"cust_a": MagicMock(id="cust_a", name="A")},
                              orders_inserted=orders_inserted)
            await self._run_import(csv)

        assert orders_inserted[0]["status"] == "confirmed"
        assert orders_inserted[0]["order_number"] == "ORD-0001"

    @pytest.mark.asyncio
    async def test_sales_records_batch_inserted(self):
        """SalesRecords should be inserted in a single batch call."""
        csv = self._make_csv(
            "cliente,data,prodotto,prezzo\n"
            "A,2026-01-01,P1,10\n"
            "A,2026-01-01,P2,20\n"
            "B,2026-01-02,P3,30\n"
        )

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"a": "cust_a", "b": "cust_b"},
                              find_by_id_map={"cust_a": MagicMock(id="cust_a", name="A"),
                                              "cust_b": MagicMock(id="cust_b", name="B")})
            result = await self._run_import(csv)

        # insert_many called exactly once with all 3 SalesRecords
        mock_sales_repo.insert_many.assert_called_once()
        docs = mock_sales_repo.insert_many.call_args[0][0]
        assert len(docs) == 3
        assert result["sales_records_generated"] == 3

    @pytest.mark.asyncio
    async def test_module_hooks_triggered_once(self):
        """Module hooks should fire exactly once, not per order."""
        csv = self._make_csv(
            "cliente,data,prodotto,prezzo\n"
            "A,2026-01-01,P1,10\n"
            "B,2026-01-02,P2,20\n"
        )

        import asyncio
        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_hooks, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"a": "cust_a", "b": "cust_b"},
                              find_by_id_map={"cust_a": MagicMock(id="cust_a", name="A"),
                                              "cust_b": MagicMock(id="cust_b", name="B")})
            await self._run_import(csv)
            # Let the background task run
            await asyncio.sleep(0)

            mock_hooks.assert_called_once()

    @pytest.mark.asyncio
    async def test_payment_status_grouping(self):
        """Order with all-paid rows → paid. Mixed → pending."""
        csv = self._make_csv(
            "cliente,data,prodotto,prezzo,stato_pagamento\n"
            "A,2026-01-01,P1,10,pagato\n"
            "A,2026-01-01,P2,20,pagato\n"
            "B,2026-01-01,P3,30,pagato\n"
            "B,2026-01-01,P4,15,pending\n"
        )
        orders_inserted = []

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"a": "cust_a", "b": "cust_b"},
                              find_by_id_map={"cust_a": MagicMock(id="x", name="X"),
                                              "cust_b": MagicMock(id="x", name="X")},
                              orders_inserted=orders_inserted)
            await self._run_import(csv)

        order_a = next(o for o in orders_inserted if o["customer_id"] == "cust_a")
        order_b = next(o for o in orders_inserted if o["customer_id"] == "cust_b")
        assert order_a["payment_status"] == "paid"
        assert order_b["payment_status"] == "pending"

    @pytest.mark.asyncio
    async def test_notes_consolidated_from_group(self):
        """Multiple rows with notes → consolidated into one order notes field."""
        csv = self._make_csv(
            "cliente,data,prodotto,prezzo,note\n"
            "A,2026-01-01,P1,10,Primo commento\n"
            "A,2026-01-01,P2,20,Secondo commento\n"
            "A,2026-01-01,P3,30,Primo commento\n"
        )
        orders_inserted = []

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"a": "cust_a"},
                              find_by_id_map={"cust_a": MagicMock(id="cust_a", name="A")},
                              orders_inserted=orders_inserted)
            await self._run_import(csv)

        assert orders_inserted[0]["notes"] == "Primo commento; Secondo commento"

    @pytest.mark.asyncio
    async def test_user_column_mapping_applied(self):
        """Custom user mapping should override defaults."""
        csv = self._make_csv(
            "nome,giorno,articolo,costo\n"
            "Mario,2026-01-01,Pizza,10\n"
        )

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"mario": "cust_mario"},
                              find_by_id_map={"cust_mario": MagicMock(id="cust_mario", name="Mario")})
            result = await self._run_import(csv, user_mapping={
                "nome": "customer_name",
                "giorno": "date",
                "articolo": "product_name",
                "costo": "unit_price",
            })

        assert result["orders_created"] == 1
        assert result["rows_processed"] == 1

    @pytest.mark.asyncio
    async def test_order_source_is_import(self):
        """Created orders should have source='import'."""
        csv = self._make_csv("cliente,data,prodotto,prezzo\nA,2026-01-01,P,10\n")
        orders_inserted = []

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"a": "cust_a"},
                              find_by_id_map={"cust_a": MagicMock(id="cust_a", name="A")},
                              orders_inserted=orders_inserted)
            await self._run_import(csv)

        assert orders_inserted[0]["source"] == "import"

    @pytest.mark.asyncio
    async def test_order_lines_have_import_product_id(self):
        """Order lines should use __import__ as product_id placeholder."""
        csv = self._make_csv("cliente,data,prodotto,prezzo\nA,2026-01-01,Pizza Margherita,8.50\n")
        orders_inserted = []

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"a": "cust_a"},
                              find_by_id_map={"cust_a": MagicMock(id="cust_a", name="A")},
                              orders_inserted=orders_inserted)
            await self._run_import(csv)

        items = orders_inserted[0]["items"]
        assert len(items) == 1
        assert items[0]["product_id"] == "__import__"
        assert items[0]["product_name"] == "Pizza Margherita"
        assert items[0]["unit_price"] == 8.5

    @pytest.mark.asyncio
    async def test_auto_create_customer_with_email(self):
        """Auto-created customer should include email from CSV."""
        csv = self._make_csv("cliente,email,data,prodotto,prezzo\nNew Customer,new@example.com,2026-01-01,Pizza,10\n")

        created_data = []
        fake_new = MagicMock(id="cust_new", name="New Customer")

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              find_by_id_map={"cust_new": fake_new})
            mock_cust_repo.create = AsyncMock(side_effect=lambda org, data: (
                created_data.append(data) or fake_new
            ))
            result = await self._run_import(csv)

        assert result["customers_created"] == 1
        assert created_data[0].name == "New Customer"
        assert created_data[0].email == "new@example.com"

    @pytest.mark.asyncio
    async def test_enrich_existing_customer_email(self):
        """Existing customer without email gets enriched from CSV."""
        csv = self._make_csv("cliente,email,data,prodotto,prezzo\nExisting,existing@test.com,2026-01-01,Pizza,10\n")

        updated_calls = []
        fake_existing = MagicMock(id="cust_exist", name="Existing", email=None)

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"existing": "cust_exist"},
                              find_by_id_map={"cust_exist": fake_existing})
            mock_cust_repo.update = AsyncMock(side_effect=lambda cid, oid, data: updated_calls.append((cid, data)))
            result = await self._run_import(csv)

        assert result["customers_updated"] == 1
        assert updated_calls[0] == ("cust_exist", {"email": "existing@test.com"})

    @pytest.mark.asyncio
    async def test_no_enrich_if_customer_already_has_email(self):
        """Customer with existing email should NOT be overwritten."""
        csv = self._make_csv("cliente,email,data,prodotto,prezzo\nExisting,new@test.com,2026-01-01,Pizza,10\n")

        fake_existing = MagicMock(id="cust_exist", name="Existing", email="old@test.com")

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"existing": "cust_exist"},
                              find_by_id_map={"cust_exist": fake_existing})
            mock_cust_repo.update = AsyncMock()
            result = await self._run_import(csv)

        assert result["customers_updated"] == 0
        mock_cust_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_order_numbers_sequential(self):
        """Multiple orders should get sequential order numbers."""
        csv = self._make_csv(
            "cliente,data,prodotto,prezzo\n"
            "A,2026-01-01,P1,10\n"
            "B,2026-01-02,P2,20\n"
            "C,2026-01-03,P3,30\n"
        )
        orders_inserted = []

        stack, (mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, _, mock_orders_coll) = self._base_patches()
        with stack:
            self._setup_mocks(mock_cmap, mock_cust_repo, mock_order_repo, mock_sales_repo, mock_orders_coll,
                              customer_map={"a": "ca", "b": "cb", "c": "cc"},
                              find_by_id_map={"ca": MagicMock(id="ca", name="A"),
                                              "cb": MagicMock(id="cb", name="B"),
                                              "cc": MagicMock(id="cc", name="C")},
                              orders_inserted=orders_inserted)
            await self._run_import(csv)

        numbers = sorted(o["order_number"] for o in orders_inserted)
        assert numbers == ["ORD-0001", "ORD-0002", "ORD-0003"]

    async def _run_import(self, csv_bytes, user_mapping=None):
        from services.order_import_service import execute_order_import
        return await execute_order_import(
            content=csv_bytes,
            filename="test.csv",
            org_id="org_test",
            user_id="user_test",
            user_column_mapping=user_mapping,
        )


# ══════════════════════════════════════════════════════════════════════════════
# 10. STRESS / EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

class TestStressEdgeCases:
    """Test edge cases: empty files, weird cell formats, mixed encodings."""

    def test_extra_whitespace_in_cells(self):
        """Cells with leading/trailing whitespace should be cleaned."""
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["  Mario Rossi  "],
            "data": [" 2026-01-01 "],
            "prodotto": ["  Pizza  "],
            "prezzo": [" 10.50 "],
        })
        rows, errors = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert len(rows) == 1
        assert rows[0]["customer_name"] == "Mario Rossi"
        assert rows[0]["product_name"] == "Pizza"
        assert rows[0]["unit_price"] == 10.5

    def test_multiple_spaces_collapsed(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["Mario   Rossi   Junior"],
            "data": ["2026-01-01"],
            "prodotto": ["Pizza   Margherita   XL"],
            "prezzo": ["10"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert rows[0]["customer_name"] == "Mario Rossi Junior"
        assert rows[0]["product_name"] == "Pizza Margherita XL"

    def test_case_insensitive_payment_status(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["A", "B", "C"],
            "data": ["2026-01-01", "2026-01-01", "2026-01-01"],
            "prodotto": ["P1", "P2", "P3"],
            "prezzo": ["10", "10", "10"],
            "stato_pagamento": ["PAGATO", "Overdue", "PENDING"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert rows[0]["payment_status"] == "paid"
        assert rows[1]["payment_status"] == "overdue"
        assert rows[2]["payment_status"] == "pending"

    def test_mixed_date_formats_in_same_file(self):
        """Different date formats in different rows should all parse."""
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["A", "B", "C", "D"],
            "data": ["2026-03-15", "15/03/2026", "15.03.2026", "15 marzo 2026"],
            "prodotto": ["P1", "P2", "P3", "P4"],
            "prezzo": ["10", "20", "30", "40"],
        })
        rows, errors = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert len(rows) == 4
        assert len(errors) == 0
        # All should parse to same date
        for r in rows:
            assert r["date"] == "2026-03-15"

    def test_mixed_price_formats_in_same_file(self):
        """EU and US price formats in same file."""
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["A", "B", "C", "D"],
            "data": ["2026-01-01"] * 4,
            "prodotto": ["P1", "P2", "P3", "P4"],
            "prezzo": ["10.50", "10,50", "1.234,56", "€ 99"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert len(rows) == 4
        assert rows[0]["unit_price"] == 10.5
        assert rows[1]["unit_price"] == 10.5
        assert rows[2]["unit_price"] == 1234.56
        assert rows[3]["unit_price"] == 99.0

    def test_single_row_file(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["Solo"],
            "data": ["2026-06-15"],
            "prodotto": ["Unico"],
            "prezzo": ["42"],
        })
        rows, errors = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert len(rows) == 1
        assert len(errors) == 0

    def test_special_characters_in_names(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["O'Brien & Co."],
            "data": ["2026-01-01"],
            "prodotto": ["Crème brûlée (spécial)"],
            "prezzo": ["15"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert rows[0]["customer_name"] == "O'Brien & Co."
        assert rows[0]["product_name"] == "Crème brûlée (spécial)"

    def test_large_discount_boundary(self):
        """Exactly 100% discount should be valid, 101% should reset to 0."""
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        df = pd.DataFrame({
            "cliente": ["A", "B"],
            "data": ["2026-01-01", "2026-01-01"],
            "prodotto": ["P1", "P2"],
            "prezzo": ["100", "100"],
            "sconto": ["100", "101"],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert rows[0]["discount_pct"] == 100.0
        assert rows[0]["line_total"] == 0.0
        assert rows[1]["discount_pct"] == 0.0  # reset
        assert rows[1]["line_total"] == 100.0

    def test_very_long_notes_preserved(self):
        from services.order_import_service import _process_order_rows, _ORDER_ALIASES
        long_note = "A" * 500
        df = pd.DataFrame({
            "cliente": ["X"],
            "data": ["2026-01-01"],
            "prodotto": ["P"],
            "prezzo": ["10"],
            "note": [long_note],
        })
        rows, _ = _process_order_rows(df, dict(_ORDER_ALIASES))
        assert rows[0]["notes"] == long_note
