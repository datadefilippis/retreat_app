"""
Tests for locale-tolerant numeric normalization.

Covers:
  1. core.numeric.parse_locale_number — the canonical parser
  2. core.numeric.coerce_locale_number — the Pydantic BeforeValidator wrapper
  3. Pydantic model integration — Create/Update models accept locale strings
  4. file_parsing.clean_amount() delegation — same logic, same results

Run with: pytest tests/test_numeric_normalization.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.numeric import parse_locale_number, coerce_locale_number


# ═══════════════════════════════════════════════════════════════════════════════
# 1. parse_locale_number unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseLocaleNumber:

    # ── Passthrough / empty ──────────────────────────────────────────────
    def test_none_returns_none(self):
        assert parse_locale_number(None) is None

    def test_empty_string_returns_none(self):
        assert parse_locale_number("") is None

    def test_whitespace_returns_none(self):
        assert parse_locale_number("   ") is None

    def test_int_passthrough(self):
        assert parse_locale_number(42) == 42.0

    def test_float_passthrough(self):
        assert parse_locale_number(12.5) == 12.5

    # ── Plain numbers ────────────────────────────────────────────────────
    def test_plain_integer(self):
        assert parse_locale_number("1234") == 1234.0

    def test_plain_float_dot(self):
        assert parse_locale_number("1234.56") == 1234.56

    def test_zero(self):
        assert parse_locale_number("0") == 0.0

    def test_zero_dot_seventy_five(self):
        assert parse_locale_number("0.75") == 0.75

    # ── European format (dot=thousands, comma=decimal) ───────────────────
    def test_european_full(self):
        assert parse_locale_number("1.234,56") == 1234.56

    def test_european_large(self):
        assert parse_locale_number("12.500,75") == 12500.75

    def test_european_millions(self):
        assert parse_locale_number("1.234.567,89") == 1234567.89

    # ── US format (comma=thousands, dot=decimal) ─────────────────────────
    def test_us_full(self):
        assert parse_locale_number("1,234.56") == 1234.56

    def test_us_large(self):
        assert parse_locale_number("12,500.75") == 12500.75

    def test_us_millions(self):
        assert parse_locale_number("1,234,567.89") == 1234567.89

    # ── Single comma heuristic ───────────────────────────────────────────
    def test_comma_decimal_one_digit(self):
        assert parse_locale_number("12,5") == 12.5

    def test_comma_decimal_two_digits(self):
        assert parse_locale_number("12,50") == 12.50

    def test_comma_decimal_zero(self):
        assert parse_locale_number("0,75") == 0.75

    def test_comma_thousands_three_digits(self):
        assert parse_locale_number("1,000") == 1000.0

    def test_comma_thousands_large(self):
        assert parse_locale_number("1,000,000") == 1000000.0

    # ── Currency symbols ─────────────────────────────────────────────────
    def test_euro_symbol(self):
        assert parse_locale_number("€1.234,56") == 1234.56

    def test_dollar_symbol(self):
        assert parse_locale_number("$1,234.56") == 1234.56

    def test_gbp_symbol(self):
        assert parse_locale_number("£99,99") == 99.99

    # ── Whitespace handling ──────────────────────────────────────────────
    def test_leading_trailing_spaces(self):
        assert parse_locale_number("  1234.56  ") == 1234.56

    def test_french_space_thousands(self):
        assert parse_locale_number("1 234,56") == 1234.56

    def test_non_breaking_space(self):
        assert parse_locale_number("1\u00a0234,56") == 1234.56

    # ── Negative numbers ─────────────────────────────────────────────────
    def test_negative_dot(self):
        assert parse_locale_number("-1234.56") == -1234.56

    def test_negative_european(self):
        assert parse_locale_number("-1.234,56") == -1234.56

    # ── Invalid input ────────────────────────────────────────────────────
    def test_garbage_returns_none(self):
        assert parse_locale_number("abc") is None

    def test_pure_symbol_returns_none(self):
        assert parse_locale_number("€") is None


# ═══════════════════════════════════════════════════════════════════════════════
# 2. coerce_locale_number (Pydantic wrapper)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCoerceLocaleNumber:

    def test_none_passthrough(self):
        assert coerce_locale_number(None) is None

    def test_float_passthrough(self):
        assert coerce_locale_number(42.0) == 42.0

    def test_valid_string(self):
        assert coerce_locale_number("1.234,56") == 1234.56

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError, match="Valore numerico non valido"):
            coerce_locale_number("not-a-number")

    def test_empty_string_returns_none(self):
        assert coerce_locale_number("") is None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Pydantic model integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestPydanticModelIntegration:

    def test_sales_create_accepts_european_amount(self):
        from models.dataset import SalesRecordCreate
        record = SalesRecordCreate(date="2026-01-15", amount="1.234,56")
        assert record.amount == 1234.56

    def test_sales_create_accepts_float(self):
        from models.dataset import SalesRecordCreate
        record = SalesRecordCreate(date="2026-01-15", amount=1234.56)
        assert record.amount == 1234.56

    def test_sales_create_accepts_int(self):
        from models.dataset import SalesRecordCreate
        record = SalesRecordCreate(date="2026-01-15", amount=100)
        assert record.amount == 100.0

    def test_sales_update_accepts_comma_decimal(self):
        from models.dataset import SalesRecordUpdate
        record = SalesRecordUpdate(amount="99,50")
        assert record.amount == 99.50

    def test_expense_create_accepts_european(self):
        from models.dataset import ExpenseRecordCreate
        record = ExpenseRecordCreate(date="2026-01-15", amount="500,00")
        assert record.amount == 500.0

    def test_purchase_create_accepts_locale_quantity_and_price(self):
        from models.dataset import PurchaseRecordCreate
        record = PurchaseRecordCreate(
            date="2026-01-15",
            supplier_name="Fornitore Test",
            quantity="10,5",
            unit_price="3,50",
        )
        assert record.quantity == 10.5
        assert record.unit_price == 3.50

    def test_fixed_cost_create_accepts_european(self):
        from models.dataset import FixedCostCreate
        record = FixedCostCreate(
            name="Affitto",
            amount="1.500,00",
            start_date="2026-01-01",
        )
        assert record.amount == 1500.0

    def test_invalid_amount_raises_validation_error(self):
        from models.dataset import SalesRecordCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SalesRecordCreate(date="2026-01-15", amount="not-a-number")

    def test_zero_amount_rejected_by_gt_constraint(self):
        from models.dataset import SalesRecordCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SalesRecordCreate(date="2026-01-15", amount="0")

    def test_financial_record_purchase_base_accepts_european(self):
        from models.financial_record import PurchaseRecordCreate
        record = PurchaseRecordCreate(
            date="2026-01-15",
            quantity="5,5",
            unit_price="10,00",
        )
        assert record.quantity == 5.5
        assert record.unit_price == 10.0

    def test_financial_record_fixed_cost_accepts_european(self):
        from models.financial_record import FixedCostCreate
        record = FixedCostCreate(
            name="Leasing",
            amount="2.500,00",
            start_date="2026-01-01",
        )
        assert record.amount == 2500.0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. file_parsing.clean_amount delegation
# ═══════════════════════════════════════════════════════════════════════════════

_motor_available = False
try:
    import motor  # noqa: F401
    _motor_available = True
except ImportError:
    pass


@pytest.mark.skipif(not _motor_available, reason="motor not installed (integration env only)")
class TestCleanAmountDelegation:
    """Verify that file_parsing.clean_amount still works after refactor.

    Skipped in lightweight test environments where motor (MongoDB driver)
    is not installed.  These run in Docker / CI where all deps are present.
    """

    def test_clean_amount_european(self):
        from services.file_parsing import clean_amount
        assert clean_amount("1.234,56") == 1234.56

    def test_clean_amount_us(self):
        from services.file_parsing import clean_amount
        assert clean_amount("1,234.56") == 1234.56

    def test_clean_amount_comma_decimal(self):
        from services.file_parsing import clean_amount
        assert clean_amount("12,50") == 12.50

    def test_clean_amount_none(self):
        from services.file_parsing import clean_amount
        assert clean_amount(None) is None

    def test_clean_amount_float_passthrough(self):
        from services.file_parsing import clean_amount
        assert clean_amount(42.0) == 42.0

    def test_clean_amount_pandas_na(self):
        """pandas NA values must return None (handled by pd.isna guard)."""
        import pandas as pd
        from services.file_parsing import clean_amount
        assert clean_amount(pd.NA) is None
        assert clean_amount(float('nan')) is None
