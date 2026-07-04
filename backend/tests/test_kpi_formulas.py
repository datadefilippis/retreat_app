"""Tests for the canonical KPI formulas layer.

Verifies:
  - Pure function correctness
  - None vs 0.0 semantics
  - Rounding policy
  - Edge cases
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from modules.cashflow_monitor import kpi_formulas


class TestNetMarginPct:
    def test_positive_margin(self):
        assert kpi_formulas.net_margin_pct(2000, 10000) == 20.0

    def test_negative_margin(self):
        assert kpi_formulas.net_margin_pct(-500, 10000) == -5.0

    def test_break_even(self):
        assert kpi_formulas.net_margin_pct(0, 10000) == 0.0

    def test_no_sales_returns_none(self):
        assert kpi_formulas.net_margin_pct(1000, 0) is None

    def test_negative_sales_returns_none(self):
        assert kpi_formulas.net_margin_pct(1000, -100) is None


class TestVariableCostRatio:
    def test_normal(self):
        result = kpi_formulas.variable_cost_ratio(7000, 10000)
        assert result == 0.7

    def test_no_sales_returns_none(self):
        assert kpi_formulas.variable_cost_ratio(5000, 0) is None

    def test_over_one(self):
        result = kpi_formulas.variable_cost_ratio(12000, 10000)
        assert result == 1.2


class TestBreakEvenPoint:
    def test_normal(self):
        vcr = kpi_formulas.variable_cost_ratio(7000, 10000)  # 0.7
        result = kpi_formulas.break_even_point(3000, vcr)
        assert result == 10000.0  # 3000 / (1-0.7) = 10000

    def test_no_fixed_costs_returns_none(self):
        assert kpi_formulas.break_even_point(0, 0.7) is None

    def test_vcr_none_returns_none(self):
        assert kpi_formulas.break_even_point(3000, None) is None

    def test_vcr_ge_one_returns_none(self):
        assert kpi_formulas.break_even_point(3000, 1.0) is None
        assert kpi_formulas.break_even_point(3000, 1.5) is None


class TestBreakEvenHeadroomPct:
    def test_above_break_even(self):
        result = kpi_formulas.break_even_headroom_pct(10000, 5000)
        assert result == 100.0  # (10000-5000)/5000*100

    def test_below_break_even(self):
        result = kpi_formulas.break_even_headroom_pct(4000, 5000)
        assert result == -20.0

    def test_none_break_even_returns_none(self):
        assert kpi_formulas.break_even_headroom_pct(10000, None) is None

    def test_no_sales_returns_none(self):
        assert kpi_formulas.break_even_headroom_pct(0, 5000) is None


class TestDSO:
    def test_normal(self):
        result = kpi_formulas.dso(5000, 10000, 30)
        assert result == 15.0  # 5000/10000*30

    def test_all_paid(self):
        result = kpi_formulas.dso(0, 10000, 30)
        assert result == 0.0

    def test_no_sales_returns_none(self):
        assert kpi_formulas.dso(5000, 0, 30) is None

    def test_zero_period_returns_none(self):
        assert kpi_formulas.dso(5000, 10000, 0) is None


class TestDPO:
    def test_normal(self):
        result = kpi_formulas.dpo(3000, 10000, 30)
        assert result == 9.0

    def test_no_purchases_returns_none(self):
        assert kpi_formulas.dpo(3000, 0, 30) is None


class TestCashConversionGap:
    def test_both_computable(self):
        result = kpi_formulas.cash_conversion_gap(45.0, 30.0)
        assert result == 15.0

    def test_negative_gap(self):
        result = kpi_formulas.cash_conversion_gap(20.0, 60.0)
        assert result == -40.0

    def test_both_none_returns_none(self):
        assert kpi_formulas.cash_conversion_gap(None, None) is None

    def test_one_none_uses_zero(self):
        result = kpi_formulas.cash_conversion_gap(45.0, None)
        assert result == 45.0
        result2 = kpi_formulas.cash_conversion_gap(None, 30.0)
        assert result2 == -30.0


class TestOperationalCoverageDays:
    def test_profitable(self):
        result = kpi_formulas.operational_coverage_days(3000, 9000, 30)
        # burn_rate = 9000/30 = 300/day, coverage = 3000/300 = 10 days
        assert result == 10.0

    def test_loss_returns_zero(self):
        result = kpi_formulas.operational_coverage_days(-1000, 9000, 30)
        assert result == 0.0

    def test_no_outflows_returns_none(self):
        assert kpi_formulas.operational_coverage_days(3000, 0, 30) is None

    def test_zero_period_returns_none(self):
        assert kpi_formulas.operational_coverage_days(3000, 9000, 0) is None

    def test_break_even_returns_zero(self):
        result = kpi_formulas.operational_coverage_days(0, 9000, 30)
        assert result == 0.0


class TestBurnRateDaily:
    def test_normal(self):
        result = kpi_formulas.burn_rate_daily(9000, 30)
        assert result == 300.0

    def test_no_outflows(self):
        result = kpi_formulas.burn_rate_daily(0, 30)
        assert result == 0.0

    def test_zero_period_returns_none(self):
        assert kpi_formulas.burn_rate_daily(9000, 0) is None


class TestFixedCostRatio:
    def test_normal(self):
        result = kpi_formulas.fixed_cost_ratio(2000, 10000)
        assert result == 20.0

    def test_no_sales_returns_none(self):
        assert kpi_formulas.fixed_cost_ratio(2000, 0) is None

    def test_no_fixed_costs_returns_none(self):
        assert kpi_formulas.fixed_cost_ratio(0, 10000) is None


class TestCostToRevenueRatio:
    def test_normal(self):
        result = kpi_formulas.cost_to_revenue_ratio(8000, 10000)
        assert result == 80.0

    def test_over_100(self):
        result = kpi_formulas.cost_to_revenue_ratio(12000, 10000)
        assert result == 120.0

    def test_no_sales_returns_none(self):
        assert kpi_formulas.cost_to_revenue_ratio(8000, 0) is None
