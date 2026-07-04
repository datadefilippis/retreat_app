"""
KPI / Formula Trust Hardening — Cashflow Monitor.

Comprehensive unit tests for:
    - snapshot_builder.build_snapshot()
    - overview_builder.build_overview()
    - health_score.compute_health_score()
    - status_builder.compute_status()
    - Snapshot ↔ Overview parity on shared KPI fields.

All repository calls are mocked — no database connection needed.
Pre-computed numeric expectations are hand-verified against the formulas
in the source code.
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# Imports under test
# ═══════════════════════════════════════════════════════════════════════════════
from modules.cashflow_monitor.health_score import compute_health_score
from modules.cashflow_monitor.status_builder import compute_status
from modules.cashflow_monitor.snapshot_builder import build_snapshot


# ═══════════════════════════════════════════════════════════════════════════════
# Test Data Scenarios
# ═══════════════════════════════════════════════════════════════════════════════

# Scenario A — Healthy Business
SCENARIO_A = {
    "sales_by_date": {"2026-01-01": 5000.0, "2026-01-02": 3000.0, "2026-01-03": 2000.0},
    "expenses_by_date": {"2026-01-01": 1500.0, "2026-01-02": 1000.0, "2026-01-03": 500.0},
    "purchases_by_date": {"2026-01-01": 500.0, "2026-01-02": 300.0},
    "fixed_costs_total": 1000.0,
    "sales_by_cat": [
        {"_id": "Product A", "total": 7000.0, "count": 10},
        {"_id": "Product B", "total": 3000.0, "count": 5},
    ],
    "expenses_by_cat": [
        {"_id": "Rent", "total": 2000.0, "count": 3},
        {"_id": "Utilities", "total": 1000.0, "count": 2},
    ],
}

# Scenario B — Zero Data
SCENARIO_B = {
    "sales_by_date": {},
    "expenses_by_date": {},
    "purchases_by_date": {},
    "fixed_costs_total": 0.0,
    "sales_by_cat": [],
    "expenses_by_cat": [],
}

# Scenario C — High Burn / Critical
SCENARIO_C = {
    "sales_by_date": {"2026-02-01": 1000.0},
    "expenses_by_date": {"2026-02-01": 3000.0, "2026-02-02": 2000.0},
    "purchases_by_date": {"2026-02-01": 1000.0},
    "fixed_costs_total": 500.0,
    "sales_by_cat": [{"_id": "Service", "total": 1000.0, "count": 1}],
    "expenses_by_cat": [
        {"_id": "Salaries", "total": 3000.0, "count": 1},
        {"_id": "Rent", "total": 2000.0, "count": 1},
    ],
}

# Scenario D — Only Sales, No Expenses
SCENARIO_D = {
    "sales_by_date": {"2026-03-01": 8000.0, "2026-03-02": 2000.0},
    "expenses_by_date": {},
    "purchases_by_date": {},
    "fixed_costs_total": 0.0,
    "sales_by_cat": [{"_id": "Consulting", "total": 10000.0, "count": 4}],
    "expenses_by_cat": [],
}


# ═══════════════════════════════════════════════════════════════════════════════
# Snapshot Builder Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_snap_repo():
    """Patch analytics_repository as imported by snapshot_builder."""
    with patch("modules.cashflow_monitor.snapshot_builder.analytics_repository") as m:
        m.aggregate_sales_by_date = AsyncMock(return_value={})
        m.aggregate_expenses_by_date = AsyncMock(return_value={})
        m.aggregate_sales_by_category = AsyncMock(return_value=[])
        m.aggregate_expenses_by_category = AsyncMock(return_value=[])
        m.aggregate_fixed_costs_total = AsyncMock(return_value=0.0)
        m.aggregate_purchases_by_date = AsyncMock(return_value={})
        m.aggregate_open_receivables = AsyncMock(return_value=0.0)
        m.aggregate_open_payables = AsyncMock(return_value=0.0)
        yield m


def _configure_snap(repo, scenario, open_receivables=0.0, open_payables=0.0):
    """Configure snapshot repo mocks from a scenario dict."""
    repo.aggregate_sales_by_date.return_value = scenario["sales_by_date"]
    repo.aggregate_expenses_by_date.return_value = scenario["expenses_by_date"]
    repo.aggregate_sales_by_category.return_value = scenario["sales_by_cat"]
    repo.aggregate_expenses_by_category.return_value = scenario["expenses_by_cat"]
    repo.aggregate_fixed_costs_total.return_value = scenario["fixed_costs_total"]
    repo.aggregate_purchases_by_date.return_value = scenario["purchases_by_date"]
    repo.aggregate_open_receivables.return_value = open_receivables
    repo.aggregate_open_payables.return_value = open_payables


# ═══════════════════════════════════════════════════════════════════════════════
# Overview Builder Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_overview_repos():
    """Patch all repositories and helpers used by overview_builder."""
    with patch("modules.cashflow_monitor.overview_builder.analytics_repository") as ar, \
         patch("modules.cashflow_monitor.overview_builder.alert_repository") as alr, \
         patch("modules.cashflow_monitor.overview_builder.insight_repository") as ir, \
         patch("services.ai_analytics_service._get_date_range") as dr, \
         patch(
             "modules.cashflow_monitor.overview_builder.generate_health_explanation",
             new_callable=AsyncMock,
             return_value="Test explanation.",
         ):
        # Default empty returns for all aggregate methods
        ar.aggregate_sales_by_date = AsyncMock(return_value={})
        ar.aggregate_expenses_by_date = AsyncMock(return_value={})
        ar.aggregate_sales_by_category = AsyncMock(return_value=[])
        ar.aggregate_expenses_by_category = AsyncMock(return_value=[])
        ar.aggregate_fixed_costs_total = AsyncMock(return_value=0.0)
        ar.get_analytics_date_range = AsyncMock(return_value={
            "has_data": True, "min_date": "2025-01-01",
            "max_date": "2026-01-03", "days_of_data": 368,
            "suggested_period": "90d",
        })
        ar.aggregate_purchases_by_date = AsyncMock(return_value={})
        ar.aggregate_purchases_by_supplier = AsyncMock(return_value=[])
        ar.aggregate_open_receivables = AsyncMock(return_value=0.0)
        ar.aggregate_open_payables = AsyncMock(return_value=0.0)
        ar.aggregate_receivables_by_aging = AsyncMock(return_value=[])
        ar.aggregate_payables_by_aging = AsyncMock(return_value=[])
        ar.aggregate_upcoming_receivables = AsyncMock(return_value=[])
        ar.aggregate_upcoming_payables = AsyncMock(return_value=[])
        ar.aggregate_purchases_by_product = AsyncMock(return_value=[])
        ar.aggregate_purchases_by_category_macro = AsyncMock(return_value=[])

        alr.find_by_org = AsyncMock(return_value=[])
        ir.find_latest = AsyncMock(return_value=None)
        dr.return_value = ("2026-01-01", "2026-01-03")

        yield {"analytics": ar, "alerts": alr, "insights": ir, "date_range": dr}


def _configure_overview(repos, scenario, *,
                        prev_sales=None, prev_expenses=None,
                        open_receivables=0.0, open_payables=0.0,
                        yoy_sales=None, yoy_expenses=None, yoy_purchases=None,
                        alerts=None, upcoming_recv=None, upcoming_pay=None,
                        purchases_by_supplier=None):
    """Configure overview repo mocks with side_effect dispatchers.

    overview_builder calls aggregate_sales_by_date 3x (current, prev, yoy),
    aggregate_expenses_by_date 3x, and aggregate_purchases_by_date 2x.
    We use side_effect to dispatch based on the date arguments.
    """
    ar = repos["analytics"]

    # Date ranges derived from the default mock_get_date_range = ("2026-01-01", "2026-01-03")
    # period_days = 3
    # prev: 2025-12-29 to 2025-12-31
    # yoy:  2025-01-01 to 2025-01-03
    current_start, current_end = "2026-01-01", "2026-01-03"
    prev_start, prev_end = "2025-12-29", "2025-12-31"
    yoy_start, yoy_end = "2025-01-01", "2025-01-03"

    _prev_sales = prev_sales or {}
    _prev_expenses = prev_expenses or {}
    _yoy_sales = yoy_sales or {}
    _yoy_expenses = yoy_expenses or {}
    _yoy_purchases = yoy_purchases or {}

    async def _sales_dispatch(org_id, s, e):
        if s == current_start and e == current_end:
            return scenario["sales_by_date"]
        elif s == prev_start and e == prev_end:
            return _prev_sales
        elif s == yoy_start and e == yoy_end:
            return _yoy_sales
        return {}

    async def _expenses_dispatch(org_id, s, e):
        if s == current_start and e == current_end:
            return scenario["expenses_by_date"]
        elif s == prev_start and e == prev_end:
            return _prev_expenses
        elif s == yoy_start and e == yoy_end:
            return _yoy_expenses
        return {}

    async def _purchases_dispatch(org_id, s, e):
        if s == current_start and e == current_end:
            return scenario["purchases_by_date"]
        elif s == yoy_start and e == yoy_end:
            return _yoy_purchases
        return {}

    ar.aggregate_sales_by_date.side_effect = _sales_dispatch
    ar.aggregate_expenses_by_date.side_effect = _expenses_dispatch
    ar.aggregate_purchases_by_date.side_effect = _purchases_dispatch

    ar.aggregate_sales_by_category.return_value = scenario["sales_by_cat"]
    ar.aggregate_expenses_by_category.return_value = scenario["expenses_by_cat"]
    ar.aggregate_fixed_costs_total.return_value = scenario["fixed_costs_total"]
    ar.aggregate_open_receivables.return_value = open_receivables
    ar.aggregate_open_payables.return_value = open_payables
    ar.aggregate_purchases_by_supplier.return_value = purchases_by_supplier or []
    ar.aggregate_upcoming_receivables.return_value = upcoming_recv or []
    ar.aggregate_upcoming_payables.return_value = upcoming_pay or []

    if alerts:
        repos["alerts"].find_by_org.return_value = alerts


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: build a minimal healthy KPIs dict for status/health tests
# ═══════════════════════════════════════════════════════════════════════════════

def _healthy_kpis(**overrides):
    """Return a baseline healthy KPIs dict for v3.0 health score.  Override any key via kwargs."""
    base = {
        "total_sales": 10000.0,
        "total_expenses": 3000.0,
        "supplier_purchases": 800.0,
        "fixed_costs_total": 1000.0,
        "total_outflows": 4800.0,
        "variable_outflows": 3800.0,
        "net_after_fixed": 5200.0,
        "total_outflow_ratio": 48.0,
        "operating_margin_pct": 62.0,
        "dso": 20.0,
        "dpo": 60.0,
        "giorni_autonomia": 100.0,
        "break_even": 1612.90,
        "sales_trend_pct": 5.0,
        "margin_trend_pp": 2.0,
        "cash_conversion_gap": -5.0,
        "has_payment_status_data": True,
        "data_sources_present": 4,
        "period_days": 30,
    }
    base.update(overrides)
    return base


def _healthy_alerts(**overrides):
    """Return a baseline alerts summary.  Override via kwargs."""
    base = {"open_count": 0, "by_severity": {"high": 0, "medium": 0, "low": 0}}
    base.update(overrides)
    return base


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Health Score (pure function — no mocking)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthScore:
    """Tests for compute_health_score() — v3.0: 5-dimension scoring, 0-100 scale."""

    def test_perfect_score(self):
        """All metrics optimal → 100 points."""
        kpis = {
            "total_sales": 10000, "net_after_fixed": 2000,  # 20% margin
            "total_outflows": 8000, "variable_outflows": 7000,
            "sales_trend_pct": 15, "margin_trend_pp": 5,
            "break_even": 5000, "fixed_costs_total": 1000,
            "cash_conversion_gap": -5, "has_payment_status_data": True,
            "dso": 20, "dpo": 60,
            "data_sources_present": 4, "period_days": 30,
        }
        result = compute_health_score(kpis, alerts_high_count=0)
        assert result["score"] == 100
        assert result["label"] == "Eccellente"
        assert result["color"] == "#22C55E"

    def test_worst_score(self):
        """All metrics at worst tier → near 0."""
        kpis = {
            "total_sales": 10000, "net_after_fixed": -1000,
            "total_outflows": 11000, "variable_outflows": 8000,
            "sales_trend_pct": -30, "margin_trend_pp": -10,
            "break_even": 15000, "fixed_costs_total": 3000,
            "cash_conversion_gap": 90, "has_payment_status_data": True,
            "dso": 100, "dpo": 10,
            "data_sources_present": 4, "period_days": 30,
        }
        result = compute_health_score(kpis, alerts_high_count=5)
        assert result["score"] <= 10
        assert result["label"] == "Critico"

    def test_not_computable_dimensions_excluded(self):
        """Dimensions with missing data are excluded, score rescaled."""
        kpis = {
            "total_sales": 10000, "net_after_fixed": 2000,
            "total_outflows": 8000, "variable_outflows": 7000,
            # No trend data → Dinamica Ricavi = not_computable
            "sales_trend_pct": None, "margin_trend_pp": None,
            # No payment data → Ciclo di Cassa = not_computable
            "has_payment_status_data": False,
            "break_even": 5000, "fixed_costs_total": 1000,
            "data_sources_present": 2, "period_days": 30,
        }
        result = compute_health_score(kpis, alerts_high_count=0)
        # Should still produce a valid score from the computable dimensions
        assert 0 < result["score"] <= 100
        assert result["confidence"] < 1.0  # not all dimensions computable
        assert result["computable_dimensions"] < result["total_dimensions"]

    def test_no_sales_data(self):
        """total_sales=0 → Margine Netto not computable, not false-good."""
        kpis = {
            "total_sales": 0, "net_after_fixed": 0,
            "total_outflows": 0, "variable_outflows": 0,
            "data_sources_present": 0, "period_days": 30,
        }
        result = compute_health_score(kpis, alerts_high_count=0)
        # Net margin should be not_computable, not scored as "good"
        net_dim = [d for d in result["breakdown"] if d["key"] == "net_margin"][0]
        assert net_dim["status"] == "not_computable"

    def test_confidence_field(self):
        """Confidence reflects computable weight fraction."""
        # All computable
        kpis = {
            "total_sales": 10000, "net_after_fixed": 2000,
            "total_outflows": 8000, "variable_outflows": 7000,
            "sales_trend_pct": 5, "margin_trend_pp": 2,
            "break_even": 5000, "fixed_costs_total": 1000,
            "cash_conversion_gap": 10, "has_payment_status_data": True,
            "data_sources_present": 4, "period_days": 30,
        }
        result = compute_health_score(kpis, alerts_high_count=0)
        assert result["confidence"] == 1.0

    def test_diagnostics_included(self):
        """Output includes diagnostics section."""
        kpis = {
            "total_sales": 10000, "net_after_fixed": 2000,
            "total_outflows": 8000, "variable_outflows": 7000,
            "data_sources_present": 4, "period_days": 30,
        }
        result = compute_health_score(kpis, alerts_high_count=0)
        assert "diagnostics" in result
        assert "cost_to_revenue_ratio" in result["diagnostics"]
        assert "giorni_copertura" in result["diagnostics"]

    def test_net_loss_zero_points(self):
        """Net loss → 0 points for Margine Netto."""
        kpis = _healthy_kpis(net_after_fixed=-500)
        result = compute_health_score(kpis)
        net_dim = [d for d in result["breakdown"] if d["key"] == "net_margin"][0]
        assert net_dim["points"] == 0

    def test_output_contract_fields(self):
        """Output must include all v3.0 contract fields."""
        kpis = _healthy_kpis()
        result = compute_health_score(kpis, alerts_high_count=0)
        assert "score" in result
        assert "label" in result
        assert "color" in result
        assert "confidence" in result
        assert "breakdown" in result
        assert "diagnostics" in result
        assert "top_strengths" in result
        assert "top_issues" in result
        assert "priority_actions" in result
        assert "data_caveats" in result

    def test_exception_returns_grey_fallback(self):
        """Any exception → grey fallback score."""
        result = compute_health_score("not_a_dict", alerts_high_count=0)
        assert result["score"] == 0
        assert result["label"] == "N/D"
        assert result["color"] == "#94A3B8"

    def test_sparse_data_false_good_caveat(self):
        """Single data source with inflated margin → sparse-data caveat added."""
        kpis = {
            "total_sales": 5000, "net_after_fixed": 5000,  # 100% margin — no costs uploaded
            "total_outflows": 0, "variable_outflows": 0,
            "fixed_costs_total": 0,
            "data_sources_present": 1,  # only sales uploaded
            "period_days": 30,
        }
        result = compute_health_score(kpis, alerts_high_count=0)
        caveats = result["data_caveats"]
        sparse_caveat = [c for c in caveats if "sola fonte dati" in c]
        assert len(sparse_caveat) == 1, f"Expected sparse-data caveat, got: {caveats}"

    def test_sparse_data_no_caveat_when_multi_source(self):
        """Multiple data sources with high margin → no false-good caveat."""
        kpis = _healthy_kpis(data_sources_present=3)
        result = compute_health_score(kpis, alerts_high_count=0)
        caveats = result["data_caveats"]
        sparse_caveat = [c for c in caveats if "sola fonte dati" in c]
        assert len(sparse_caveat) == 0

    def test_sparse_data_no_caveat_when_margin_moderate(self):
        """Single source but moderate margin (30%) → no false-good caveat."""
        kpis = {
            "total_sales": 10000, "net_after_fixed": 3000,  # 30% margin
            "total_outflows": 7000, "variable_outflows": 7000,
            "fixed_costs_total": 0,
            "data_sources_present": 1,
            "period_days": 30,
        }
        result = compute_health_score(kpis, alerts_high_count=0)
        caveats = result["data_caveats"]
        sparse_caveat = [c for c in caveats if "sola fonte dati" in c]
        assert len(sparse_caveat) == 0, f"No caveat expected for 30% margin, got: {caveats}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Status Builder (pure function — no mocking)
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatusBuilder:
    """Tests for compute_status() — 10 priority rules, first match wins."""

    def test_rule1_insufficient_data(self):
        """sales < 1.0 AND period_days >= 7 → insufficient_data."""
        kpis = _healthy_kpis(total_sales=0.5, period_days=7)
        result = compute_status(kpis, _healthy_alerts(), "it")
        assert result["level"] == "insufficient_data"
        assert result["color"] == "gray"
        assert result["primary_driver"] == "no_revenue_data"

    def test_rule1_not_fired_below_7d(self):
        """period_days < 7 → rule 1 does not fire even with low sales."""
        kpis = _healthy_kpis(total_sales=0.5, period_days=3, net_after_fixed=0.5,
                             total_outflow_ratio=0)
        result = compute_status(kpis, _healthy_alerts(), "it")
        assert result["level"] != "insufficient_data"

    def test_rule2_extreme_outflow(self):
        """total_outflow_ratio > 150 → critical."""
        kpis = _healthy_kpis(total_outflow_ratio=160, total_sales=1000)
        result = compute_status(kpis, _healthy_alerts(), "it")
        assert result["level"] == "critical"
        assert result["primary_driver"] == "outflow_ratio_extreme"

    def test_rule3_loss_plus_alerts(self):
        """net < 0 AND high alerts >= 2 → critical."""
        kpis = _healthy_kpis(net_after_fixed=-100, total_outflow_ratio=90)
        alerts = _healthy_alerts(by_severity={"high": 2, "medium": 0, "low": 0})
        result = compute_status(kpis, alerts, "it")
        assert result["level"] == "critical"
        assert result["primary_driver"] == "negative_result_with_high_alerts"

    def test_rule3_needs_two_high_alerts(self):
        """net < 0 AND only 1 high alert → falls through to rule 5 (warning)."""
        kpis = _healthy_kpis(net_after_fixed=-100, total_outflow_ratio=90)
        alerts = _healthy_alerts(by_severity={"high": 1, "medium": 0, "low": 0})
        result = compute_status(kpis, alerts, "it")
        # Rule 4: ratio 90 ≤ 100 → skip. Rule 5: net < 0 → warning
        assert result["level"] == "warning"
        assert result["primary_driver"] == "negative_net_result"

    def test_rule4_outflow_exceeds_revenue(self):
        """total_outflow_ratio > 100 (but ≤ 150) → warning."""
        kpis = _healthy_kpis(total_outflow_ratio=110, net_after_fixed=100)
        result = compute_status(kpis, _healthy_alerts(), "it")
        assert result["level"] == "warning"
        assert result["primary_driver"] == "outflow_exceeds_revenue"

    def test_rule5_negative_net(self):
        """net < 0, ratio ≤ 100 → warning."""
        kpis = _healthy_kpis(net_after_fixed=-100, total_outflow_ratio=90)
        result = compute_status(kpis, _healthy_alerts(), "it")
        assert result["level"] == "warning"
        assert result["primary_driver"] == "negative_net_result"

    def test_rule6_tight_margin_alert(self):
        """ratio > 80 AND high_alerts >= 1 AND net > 0 → warning."""
        kpis = _healthy_kpis(total_outflow_ratio=85, net_after_fixed=100)
        alerts = _healthy_alerts(by_severity={"high": 1, "medium": 0, "low": 0})
        result = compute_status(kpis, alerts, "it")
        assert result["level"] == "warning"
        assert result["primary_driver"] == "high_expense_ratio_with_alerts"

    def test_rule7_alert_despite_profit(self):
        """ratio ≤ 80, net > 0, high_alerts >= 1 → monitor."""
        kpis = _healthy_kpis(total_outflow_ratio=70, net_after_fixed=100)
        alerts = _healthy_alerts(by_severity={"high": 1, "medium": 0, "low": 0})
        result = compute_status(kpis, alerts, "it")
        assert result["level"] == "monitor"
        assert result["primary_driver"] == "active_high_alerts"

    def test_rule8_high_expense_ratio(self):
        """ratio > 80 AND no high alerts AND net > 0 → monitor."""
        kpis = _healthy_kpis(total_outflow_ratio=85, net_after_fixed=100)
        result = compute_status(kpis, _healthy_alerts(), "it")
        assert result["level"] == "monitor"
        assert result["primary_driver"] == "high_expense_ratio"

    def test_rule9_declining_revenue(self):
        """sales_trend_pct < -20 AND total_sales > 0 → monitor."""
        kpis = _healthy_kpis(sales_trend_pct=-25, total_outflow_ratio=70,
                             net_after_fixed=100)
        result = compute_status(kpis, _healthy_alerts(), "it")
        assert result["level"] == "monitor"
        assert result["primary_driver"] == "declining_revenue"

    def test_rule9_needs_positive_sales(self):
        """sales_trend_pct < -20 but total_sales = 0 → rule 1 fires first (insufficient)."""
        kpis = _healthy_kpis(sales_trend_pct=-25, total_sales=0, period_days=30)
        result = compute_status(kpis, _healthy_alerts(), "it")
        assert result["level"] == "insufficient_data"

    def test_rule10_healthy(self):
        """All normal → healthy."""
        kpis = _healthy_kpis()
        result = compute_status(kpis, _healthy_alerts(), "it")
        assert result["level"] == "healthy"
        assert result["color"] == "green"
        assert result["primary_driver"] == "all_clear"

    def test_locale_en(self):
        result = compute_status(_healthy_kpis(), _healthy_alerts(), "en")
        assert result["label"] == "Healthy"

    def test_locale_de(self):
        result = compute_status(_healthy_kpis(), _healthy_alerts(), "de")
        assert result["label"] == "Gesund"

    def test_locale_fr(self):
        result = compute_status(_healthy_kpis(), _healthy_alerts(), "fr")
        assert result["label"] == "Sain"

    def test_data_warning_no_fixed_costs(self):
        """fixed_costs_total == 0 → data_warnings has one entry."""
        kpis = _healthy_kpis(fixed_costs_total=0)
        result = compute_status(kpis, _healthy_alerts(), "en")
        assert len(result["data_warnings"]) == 1
        assert "fixed cost" in result["data_warnings"][0].lower()

    def test_exception_returns_insufficient(self):
        """Malformed input → fallback to insufficient_data."""
        result = compute_status({}, {}, "it")
        assert result["level"] == "insufficient_data"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Snapshot Builder (async, mocked repos)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotBuilder:
    """Tests for build_snapshot() — KPI persistence contract."""

    @pytest.mark.asyncio
    async def test_happy_path_scenario_a(self, mock_snap_repo):
        _configure_snap(mock_snap_repo, SCENARIO_A,
                        open_receivables=2000.0, open_payables=500.0)

        result = await build_snapshot("org_test", "2026-01-01", "2026-01-03")

        assert result["total_sales"] == 10000.00
        assert result["total_expenses"] == 3000.00
        assert result["net_cashflow"] == 7000.00  # legacy 2-bucket
        assert result["period_days"] == 3
        assert result["supplier_purchases"] == 800.00
        assert result["variable_outflows"] == 3800.00
        assert result["total_outflows"] == 4800.00
        assert result["net_before_fixed"] == 6200.00
        assert result["net_after_fixed"] == 5200.00
        assert result["operating_margin"] == 6200.00
        assert result["operating_margin_pct"] == 62.0
        assert result["break_even"] == pytest.approx(1612.90, abs=0.01)
        assert result["burn_rate_total"] == pytest.approx(1600.00, abs=0.01)
        assert result["fixed_costs_pct"] == 10.0
        assert result["avg_daily_sales"] == pytest.approx(3333.33, abs=0.01)
        assert result["avg_daily_expenses"] == 1000.00
        assert result["fixed_costs_total"] == 1000.0

    @pytest.mark.asyncio
    async def test_zero_data_scenario_b(self, mock_snap_repo):
        _configure_snap(mock_snap_repo, SCENARIO_B)

        result = await build_snapshot("org_test", "2026-01-01", "2026-01-03")

        assert result["total_sales"] == 0.00
        assert result["total_expenses"] == 0.00
        assert result["net_cashflow"] == 0.00
        assert result["period_days"] == 1  # fallback via `or 1`
        assert result["supplier_purchases"] == 0.00
        assert result["variable_outflows"] == 0.00
        assert result["total_outflows"] == 0.00
        assert result["net_after_fixed"] == 0.00
        assert result["operating_margin_pct"] == 0.0
        assert result["break_even"] is None
        assert result["burn_rate_total"] == 0.00
        assert result["avg_daily_sales"] == 0.00

    @pytest.mark.asyncio
    async def test_high_burn_scenario_c(self, mock_snap_repo):
        _configure_snap(mock_snap_repo, SCENARIO_C)

        result = await build_snapshot("org_test", "2026-02-01", "2026-02-10")

        assert result["total_sales"] == 1000.00
        assert result["total_expenses"] == 5000.00
        assert result["supplier_purchases"] == 1000.00
        assert result["variable_outflows"] == 6000.00
        assert result["total_outflows"] == 6500.00
        assert result["net_after_fixed"] == -5500.00
        assert result["operating_margin"] == -5000.00
        assert result["operating_margin_pct"] == -500.0
        assert result["break_even"] is None  # vcr = 6.0 ≥ 1

    @pytest.mark.asyncio
    async def test_only_sales_scenario_d(self, mock_snap_repo):
        _configure_snap(mock_snap_repo, SCENARIO_D)

        result = await build_snapshot("org_test", "2026-03-01", "2026-03-02")

        assert result["total_sales"] == 10000.00
        assert result["total_expenses"] == 0.00
        assert result["net_cashflow"] == 10000.00
        assert result["variable_outflows"] == 0.00
        assert result["total_outflows"] == 0.00
        assert result["net_after_fixed"] == 10000.00
        assert result["operating_margin_pct"] == 100.0
        assert result["break_even"] is None  # no fixed costs

    @pytest.mark.asyncio
    async def test_break_even_vcr_equals_one(self, mock_snap_repo):
        """variable_cost_ratio = 1.0 exactly → break_even = None."""
        _configure_snap(mock_snap_repo, {
            "sales_by_date": {"2026-04-01": 5000.0},
            "expenses_by_date": {"2026-04-01": 4000.0},
            "purchases_by_date": {"2026-04-01": 1000.0},
            "fixed_costs_total": 2000.0,
            "sales_by_cat": [], "expenses_by_cat": [],
        })
        result = await build_snapshot("org_test", "2026-04-01", "2026-04-01")
        # vcr = (4000+1000)/5000 = 1.0; NOT < 1 → None
        assert result["break_even"] is None

    @pytest.mark.asyncio
    async def test_break_even_vcr_exceeds_one(self, mock_snap_repo):
        """variable_cost_ratio > 1 → break_even = None."""
        _configure_snap(mock_snap_repo, {
            "sales_by_date": {"2026-04-01": 1000.0},
            "expenses_by_date": {"2026-04-01": 800.0},
            "purchases_by_date": {"2026-04-01": 500.0},
            "fixed_costs_total": 200.0,
            "sales_by_cat": [], "expenses_by_cat": [],
        })
        result = await build_snapshot("org_test", "2026-04-01", "2026-04-01")
        # vcr = (800+500)/1000 = 1.3 ≥ 1 → None
        assert result["break_even"] is None

    @pytest.mark.asyncio
    async def test_break_even_no_fixed_costs(self, mock_snap_repo):
        """fixed_costs = 0 → break_even = None."""
        _configure_snap(mock_snap_repo, {
            "sales_by_date": {"2026-04-01": 10000.0},
            "expenses_by_date": {"2026-04-01": 3000.0},
            "purchases_by_date": {},
            "fixed_costs_total": 0.0,
            "sales_by_cat": [], "expenses_by_cat": [],
        })
        result = await build_snapshot("org_test", "2026-04-01", "2026-04-01")
        assert result["break_even"] is None

    @pytest.mark.asyncio
    async def test_break_even_computed(self, mock_snap_repo):
        """Computable break-even: vcr < 1 AND fixed > 0."""
        _configure_snap(mock_snap_repo, {
            "sales_by_date": {"2026-04-01": 10000.0},
            "expenses_by_date": {"2026-04-01": 2500.0},
            "purchases_by_date": {"2026-04-01": 500.0},
            "fixed_costs_total": 1000.0,
            "sales_by_cat": [], "expenses_by_cat": [],
        })
        result = await build_snapshot("org_test", "2026-04-01", "2026-04-01")
        # vcr = (2500+500)/10000 = 0.3; break_even = 1000 / (1-0.3) = 1428.57
        assert result["break_even"] == pytest.approx(1428.57, abs=0.01)

    @pytest.mark.asyncio
    async def test_days_fallback_to_one(self, mock_snap_repo):
        """Empty date dicts → days = 1 (not 0) to prevent division by zero."""
        _configure_snap(mock_snap_repo, SCENARIO_B)
        result = await build_snapshot("org_test", "2026-01-01", "2026-01-03")
        assert result["period_days"] == 1

    @pytest.mark.asyncio
    async def test_category_top_5(self, mock_snap_repo):
        """Only top 5 categories returned."""
        cats = [{"_id": f"Cat{i}", "total": float(100 - i), "count": 1} for i in range(7)]
        _configure_snap(mock_snap_repo, {
            **SCENARIO_A,
            "sales_by_cat": cats,
        })
        result = await build_snapshot("org_test", "2026-01-01", "2026-01-03")
        assert len(result["top_sales_categories"]) == 5

    @pytest.mark.asyncio
    async def test_scadenzario_computed(self, mock_snap_repo):
        """After fix: DSO/DPO/CCC computed from repository data."""
        _configure_snap(mock_snap_repo, SCENARIO_A,
                        open_receivables=2000.0, open_payables=500.0)

        result = await build_snapshot("org_test", "2026-01-01", "2026-01-03")

        # days = 3 (all 3 dates have data)
        # DSO = 2000 / 10000 * 3 = 0.6
        assert result["dso"] == pytest.approx(0.6, abs=0.1)
        # DPO = 500 / 800 * 3 = 1.875 → round to 1.9
        assert result["dpo"] == pytest.approx(1.9, abs=0.1)
        # CCC = 0.6 - 1.9 = -1.3
        assert result["cash_conversion_cycle"] == pytest.approx(-1.3, abs=0.1)
        assert result["open_receivables"] == 2000.0
        assert result["open_payables"] == 500.0
        # scadenzario_netto_30 stays 0.0 (not computed in snapshot)
        assert result["scadenzario_netto_30"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Overview Builder (async, full mock setup)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOverviewBuilder:
    """Tests for build_overview() — the live KPI endpoint."""

    @pytest.mark.asyncio
    async def test_returns_none_no_data(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        # Default mocks return {} for all → None
        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        assert result is None

    @pytest.mark.asyncio
    async def test_happy_path_kpis(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        _configure_overview(
            mock_overview_repos, SCENARIO_A,
            prev_sales={"2025-12-30": 4000.0, "2025-12-31": 3000.0},
            prev_expenses={"2025-12-30": 1200.0},
            open_receivables=2000.0,
            open_payables=500.0,
        )

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")

        assert result is not None
        kpis = result["kpis"]
        assert kpis["total_sales"] == 10000.00
        assert kpis["total_expenses"] == 3000.00
        assert kpis["supplier_purchases"] == 800.00
        assert kpis["variable_outflows"] == 3800.00
        assert kpis["total_outflows"] == 4800.00
        assert kpis["net_after_fixed"] == 5200.00
        assert kpis["operating_margin"] == 6200.00
        assert kpis["operating_margin_pct"] == 62.0
        assert kpis["total_outflow_ratio"] == 48.0
        assert kpis["purchase_ratio"] == 8.0
        assert kpis["break_even"] == pytest.approx(1612.90, abs=0.01)
        assert kpis["period_days"] == 3

    @pytest.mark.asyncio
    async def test_dso_dpo_ccc(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        _configure_overview(
            mock_overview_repos, SCENARIO_A,
            open_receivables=2000.0,
            open_payables=500.0,
        )

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        kpis = result["kpis"]

        # period_days = 3
        # DSO = 2000 / 10000 * 3 = 0.6
        assert kpis["dso"] == pytest.approx(0.6, abs=0.1)
        # DPO = 500 / 800 * 3 = 1.875 → round to 1.9
        assert kpis["dpo"] == pytest.approx(1.9, abs=0.1)
        # CCC = 0.6 - 1.9 = -1.3
        assert kpis["cash_conversion_cycle"] == pytest.approx(-1.3, abs=0.1)

    @pytest.mark.asyncio
    async def test_dso_zero_no_receivables(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        _configure_overview(mock_overview_repos, SCENARIO_A,
                            open_receivables=0.0)

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        assert result["kpis"]["dso"] == 0.0

    @pytest.mark.asyncio
    async def test_dpo_zero_no_purchases(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        no_purchases = {**SCENARIO_A, "purchases_by_date": {}}
        _configure_overview(mock_overview_repos, no_purchases,
                            open_payables=500.0)

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        # supplier_purchases = 0 → dpo = 0.0
        assert result["kpis"]["dpo"] == 0.0

    @pytest.mark.asyncio
    async def test_trends_ytd_pattern_compares_to_prior_year(
        self, mock_overview_repos,
    ):
        """Wave 14.CONSOLIDATE R3 — for a Jan 1 start, prev_period
        collapses to the SAME WINDOW of the prior calendar year
        (= the YoY window). Pre-Wave-14 prev_period for Jan 1-3 was
        Dec 29-31 of prior year, which had no business meaning.

        Because prev_period and yoy now share the same dates for YTD,
        we populate the YOY dispatcher in the fixture (the prev
        dispatcher's hardcoded dates won't be hit any more).
        """
        from modules.cashflow_monitor.overview_builder import build_overview

        # YTD-pattern window: 2026-01-01 → 2026-01-03
        # New R3 prev_period = YoY window = 2025-01-01 → 2025-01-03
        _configure_overview(
            mock_overview_repos, SCENARIO_A,
            yoy_sales={"2025-01-02": 4000.0, "2025-01-03": 3000.0},
            yoy_expenses={"2025-01-02": 1200.0},
        )

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        kpis = result["kpis"]

        # Same numeric expectation — only WHICH dates are queried
        # changed; the trend math is unchanged.
        # sales: (10000-7000)/7000*100 = 42.857 → 42.9
        assert kpis["sales_trend_pct"] == pytest.approx(42.9, abs=0.1)
        # expenses: (3000-1200)/1200*100 = 150.0
        assert kpis["expenses_trend_pct"] == pytest.approx(150.0, abs=0.1)

        # And the period block surfaces the new semantic flags
        period = result["period"]
        assert period["semantic"] == "ytd"
        assert period["prev_period"]["start_date"] == "2025-01-01"
        assert period["prev_period"]["end_date"] == "2025-01-03"
        assert period["prev_period"]["semantic"] == "ytd_prior_year"

    @pytest.mark.asyncio
    async def test_trends_none_when_no_previous(self, mock_overview_repos):
        """Wave 14.CONSOLIDATE R9 — when the prior period had ZERO
        sales/expenses, the trend is UNDEFINED and must be returned
        as None, not 0.0. Pre-Wave-14 the code returned 0.0 which
        silently hid infinite growth ("merchant had €0 last year and
        €200K this year" → trend reported as 0% / "stable" by the AI).
        """
        from modules.cashflow_monitor.overview_builder import build_overview

        _configure_overview(mock_overview_repos, SCENARIO_A)
        # prev defaults to {} → prev totals = 0 → trend = None (R9)

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        kpis = result["kpis"]
        assert kpis["sales_trend_pct"] is None
        assert kpis["expenses_trend_pct"] is None

    @pytest.mark.asyncio
    async def test_daily_series_4_bucket(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        _configure_overview(mock_overview_repos, SCENARIO_A)

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        series = result["charts"]["daily_series"]

        assert len(series) == 3
        # daily_fixed = round(1000 / 3, 2) = 333.33
        daily_fixed = round(1000.0 / 3, 2)

        # Day 1: 5000 - 1500 - 500 - 333.33 = 2666.67
        d1 = series[0]
        assert d1["date"] == "2026-01-01"
        assert d1["sales"] == 5000.0
        assert d1["expenses"] == 1500.0
        assert d1["purchases"] == 500.0
        expected_net_d1 = round(5000 - 1500 - 500 - daily_fixed, 2)
        assert d1["net_cashflow"] == pytest.approx(expected_net_d1, abs=0.01)

        # Day 3: 2000 - 500 - 0 - 333.33 = 1166.67
        d3 = series[2]
        assert d3["sales"] == 2000.0
        assert d3["purchases"] == 0.0
        expected_net_d3 = round(2000 - 500 - 0 - daily_fixed, 2)
        assert d3["net_cashflow"] == pytest.approx(expected_net_d3, abs=0.01)

    @pytest.mark.asyncio
    async def test_giorni_autonomia_zero_when_negative_running(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        # All expenses, tiny sales → running cumulative is negative
        _configure_overview(mock_overview_repos, SCENARIO_C)

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        kpis = result["kpis"]
        # running < 0 → giorni_autonomia = 0.0
        assert kpis["giorni_autonomia"] == 0.0

    @pytest.mark.asyncio
    async def test_giorni_autonomia_zero_when_zero_burn(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        _configure_overview(mock_overview_repos, SCENARIO_D)

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        kpis = result["kpis"]
        # burn_rate_total = 0 → giorni_autonomia = 0.0
        assert kpis["giorni_autonomia"] == 0.0

    @pytest.mark.asyncio
    async def test_critical_status_high_burn(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        _configure_overview(mock_overview_repos, SCENARIO_C)

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        assert result["status"]["level"] == "critical"
        assert result["status"]["primary_driver"] == "outflow_ratio_extreme"

    @pytest.mark.asyncio
    async def test_response_shape(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        _configure_overview(mock_overview_repos, SCENARIO_A)
        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")

        expected_keys = {
            "module", "period", "data_availability", "kpis", "charts",
            "categories", "alerts", "last_insight", "status", "health_score",
            "yoy", "suppliers", "purchase_distribution", "scadenzario", "_legacy",
        }
        assert set(result.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_yoy_computed(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        _configure_overview(
            mock_overview_repos, SCENARIO_A,
            yoy_sales={"2025-01-01": 4000.0, "2025-01-02": 2500.0, "2025-01-03": 1500.0},
            yoy_expenses={"2025-01-01": 1200.0, "2025-01-02": 800.0},
            yoy_purchases={"2025-01-01": 400.0},
        )

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        yoy = result["yoy"]
        assert yoy["has_data"] is True
        assert yoy["total_sales"] == 8000.0
        # sales pct: (10000 - 8000) / 8000 * 100 = 25.0
        assert yoy["pct"]["total_sales"] == 25.0

    @pytest.mark.asyncio
    async def test_yoy_none_no_data(self, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        _configure_overview(mock_overview_repos, SCENARIO_A)
        # yoy defaults to {} → has_data = False

        result = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")
        assert result["yoy"]["has_data"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Snapshot ↔ Overview Parity
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotOverviewParity:
    """Verify shared KPI fields produce identical values from both builders.

    IMPORTANT — Intentional divergences (documented, NOT tested for equality):
    ─────────────────────────────────────────────────────────────────────────────
    · period_days: snapshot uses len(active_data_dates), overview uses
      (end - start).days + 1 (calendar days).  In this test, all 3 calendar
      days have data → both equal 3 → burn_rate_total also matches.
    · net_cashflow: snapshot returns legacy 2-bucket value at top level;
      overview puts it in _legacy block.  Both compute it identically.
    · scadenzario_netto_30: only overview computes this (needs time-relative
      queries).  Snapshot always returns 0.0.
    · DSO/DPO/CCC: snapshot uses `days` (active dates), overview uses
      `period_days` (calendar).  They match here because all days have data.
      In general they may differ slightly when data has gaps.
    """

    # Fields that must be identical between snapshot and overview.kpis
    SHARED_FIELDS = [
        "total_sales", "total_expenses", "supplier_purchases",
        "fixed_costs_total", "variable_outflows", "total_outflows",
        "net_before_fixed", "net_after_fixed",
        "operating_margin", "operating_margin_pct",
        "break_even", "fixed_costs_pct",
    ]

    @pytest.mark.asyncio
    async def test_shared_kpis_match(self, mock_snap_repo, mock_overview_repos):
        from modules.cashflow_monitor.overview_builder import build_overview

        # Configure BOTH mocks with Scenario A data + receivables/payables
        _configure_snap(mock_snap_repo, SCENARIO_A,
                        open_receivables=2000.0, open_payables=500.0)
        _configure_overview(mock_overview_repos, SCENARIO_A,
                            open_receivables=2000.0, open_payables=500.0)

        snap = await build_snapshot("org_test", "2026-01-01", "2026-01-03")
        overview = await build_overview("org_test", "custom", "2026-01-01", "2026-01-03")

        assert overview is not None
        ov_kpis = overview["kpis"]

        for field in self.SHARED_FIELDS:
            snap_val = snap[field]
            ov_val = ov_kpis[field]
            if snap_val is None and ov_val is None:
                continue  # both None is OK
            assert snap_val == pytest.approx(ov_val, abs=0.01), \
                f"Parity mismatch on '{field}': snapshot={snap_val}, overview={ov_val}"

        # Also verify burn_rate_total matches (same because all 3 days have data)
        assert snap["burn_rate_total"] == pytest.approx(
            ov_kpis["burn_rate_total"], abs=0.01
        ), "burn_rate_total diverged (expected match when all days have data)"
