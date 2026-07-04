"""
Tests for Alert System v3 — thresholds, i18n, rules, deduplication.
"""

import pytest
from modules.cashflow_monitor.alert_thresholds import get_thresholds, VALID_PRESETS
from modules.cashflow_monitor.alert_i18n import (
    localize_title, localize_summary, localize_suggestion, _L,
)
from modules.cashflow_monitor.rules import AlertContext, _fmt_eur


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — Pure functions, no DB
# ═══════════════════════════════════════════════════════════════════════════════

class TestAlertThresholds:
    """Validate threshold preset structure and ordering."""

    def test_all_presets_exist(self):
        for preset in VALID_PRESETS:
            t = get_thresholds(preset)
            assert isinstance(t, dict)
            assert len(t) > 20  # Should have keys from all 5 categories

    def test_invalid_preset_falls_back_to_standard(self):
        t = get_thresholds("invalid")
        standard = get_thresholds("standard")
        assert t == standard

    def test_thresholds_have_all_categories(self):
        # Categories grew from 5 (a-e) to 6 (a-f) when sub-stream alert
        # category f was added. Bump consciously when introducing new categories.
        t = get_thresholds("standard")
        prefixes = {k.split("_")[0] for k in t}
        assert {"a", "b", "c", "d", "e", "f"} == prefixes

    def test_conservative_more_sensitive_than_relaxed(self):
        """Conservative thresholds should trigger alerts sooner (lower thresholds)."""
        c = get_thresholds("conservative")
        r = get_thresholds("relaxed")

        # Cash runway: conservative warns at more days remaining
        assert c["a_cash_runway_warning_days"] > r["a_cash_runway_warning_days"]

        # Negative days: conservative triggers with fewer negative days
        assert c["a_negative_days_warning"] < r["a_negative_days_warning"]

        # Revenue concentration: conservative triggers at lower %
        assert c["a_revenue_concentration_warning_pct"] < r["a_revenue_concentration_warning_pct"]

    def test_no_negative_thresholds(self):
        for preset in VALID_PRESETS:
            t = get_thresholds(preset)
            for key, value in t.items():
                assert value >= 0, f"{preset}.{key} = {value} (negative)"


class TestAlertI18n:
    """Validate i18n locale text table completeness and formatting."""

    EXPECTED_TYPES = [
        "cash_runway_critical", "persistent_negative_cashflow",
        "month_closed_loss", "revenue_concentration",
        "margin_erosion_trend", "unit_cost_increase",
        "break_even_unreached", "category_expense_trend",
        "dso_worsening_trend", "high_risk_invoice", "dpo_dso_imbalance",
        "yoy_anomaly", "positive_trend_break", "weekly_statistical_anomaly",
        "supplier_concentration", "dominant_product", "fixed_cost_ratio_high",
    ]

    EXPECTED_LOCALES = ["it", "en", "de", "fr"]

    def test_all_locales_present(self):
        for locale in self.EXPECTED_LOCALES:
            assert locale in _L, f"Locale '{locale}' missing from _L"

    def test_all_alert_types_in_all_locales(self):
        for locale in self.EXPECTED_LOCALES:
            for alert_type in self.EXPECTED_TYPES:
                assert alert_type in _L[locale], (
                    f"Alert type '{alert_type}' missing in locale '{locale}'"
                )

    def test_all_fields_present(self):
        for locale in self.EXPECTED_LOCALES:
            for alert_type in self.EXPECTED_TYPES:
                entry = _L[locale][alert_type]
                assert "title" in entry, f"{locale}.{alert_type} missing 'title'"
                assert "summary" in entry, f"{locale}.{alert_type} missing 'summary'"
                assert "suggestion" in entry, f"{locale}.{alert_type} missing 'suggestion'"

    def test_title_formatting(self):
        title = localize_title("cash_runway_critical", "it", days=15.0)
        assert "15" in title
        assert "giorni" in title.lower()

    def test_summary_formatting(self):
        summary = localize_summary(
            "persistent_negative_cashflow", "en",
            neg_days=7, window=14, cumulative_loss="€5,000"
        )
        assert "7" in summary
        assert "14" in summary

    def test_suggestion_returns_string(self):
        suggestion = localize_suggestion("revenue_concentration", "de")
        assert isinstance(suggestion, str)
        assert len(suggestion) > 10

    def test_missing_locale_falls_back_to_italian(self):
        title = localize_title("cash_runway_critical", "ja", days=10.0)
        assert "10" in title  # Should use Italian template

    def test_missing_alert_type_returns_placeholder(self):
        title = localize_title("nonexistent_alert", "it")
        assert "[nonexistent_alert.title]" == title

    def test_formatting_error_returns_template(self):
        # Missing required kwarg should not raise
        title = localize_title("cash_runway_critical", "it")
        assert isinstance(title, str)


class TestHelpers:
    def test_fmt_eur_large(self):
        assert _fmt_eur(12345.67) == "€12.346"  # rounds to nearest integer for large amounts

    def test_fmt_eur_small(self):
        assert "€" in _fmt_eur(42.50)


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS — AlertContext with mock data
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import date, timedelta


def _make_ctx(**overrides) -> AlertContext:
    """Create a test AlertContext with sensible defaults."""
    defaults = dict(
        org_id="test_org",
        locale="it",
        thresholds=get_thresholds("standard"),
        existing_keys=set(),
        today=date(2026, 4, 4),
        has_data=True,
        days_of_data=365,
        min_date="2025-04-04",
        max_date="2026-04-04",
        total_sales_30d=50000,
        total_expenses_30d=20000,
        total_purchases_30d=15000,
        total_fixed_costs_30d=5000,
        total_sales_prev_30d=48000,
        total_expenses_prev_30d=18000,
        total_purchases_prev_30d=14000,
    )
    defaults.update(overrides)
    return AlertContext(**defaults)


class TestCategoryA:
    """Category A: Liquidity & Survival rules."""

    @pytest.mark.asyncio
    async def test_cash_runway_triggers_on_low_coverage(self):
        from modules.cashflow_monitor.rules.category_a_liquidity import check_cash_runway_critical
        # Net = 50000 - 20000 - 15000 - 5000 = 10000
        # Coverage = 10000 / (40000/30) = 7.5 days → HIGH
        ctx = _make_ctx(
            total_sales_30d=50000,
            total_expenses_30d=20000,
            total_purchases_30d=15000,
            total_fixed_costs_30d=5000,
        )
        alerts = await check_cash_runway_critical(ctx)
        assert len(alerts) == 1
        assert alerts[0].severity.value == "high"
        assert "alert_type" in alerts[0].metric_payload
        assert alerts[0].alert_category == "A"

    @pytest.mark.asyncio
    async def test_cash_runway_no_alert_when_healthy(self):
        from modules.cashflow_monitor.rules.category_a_liquidity import check_cash_runway_critical
        # Net = 100000 - 10000 - 5000 - 2000 = 83000
        # Coverage = 83000 / (17000/30) = ~146 days → no alert
        ctx = _make_ctx(
            total_sales_30d=100000,
            total_expenses_30d=10000,
            total_purchases_30d=5000,
            total_fixed_costs_30d=2000,
        )
        alerts = await check_cash_runway_critical(ctx)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_revenue_concentration_triggers(self):
        # Smart suppression in the rule (`category_a_liquidity.py`) skips orgs
        # with ≤ 3 customers — those are "structurally concentrated" and the
        # alert would be noise. Test must include ≥ 4 customers, with BigCorp
        # still dominating at 55%.
        from modules.cashflow_monitor.rules.category_a_liquidity import check_revenue_concentration
        ctx = _make_ctx(
            total_sales_30d=100000,
            customers_by_revenue=[
                {"customer_name": "BigCorp", "_id": "bigcorp_id", "total_revenue": 55000},
                {"customer_name": "C2", "_id": "c2", "total_revenue": 20000},
                {"customer_name": "C3", "_id": "c3", "total_revenue": 15000},
                {"customer_name": "C4", "_id": "c4", "total_revenue": 10000},
            ],
        )
        alerts = await check_revenue_concentration(ctx)
        assert len(alerts) == 1
        assert "BigCorp" in alerts[0].summary  # customer name is in summary, not title

    @pytest.mark.asyncio
    async def test_revenue_concentration_no_alert_diversified(self):
        from modules.cashflow_monitor.rules.category_a_liquidity import check_revenue_concentration
        ctx = _make_ctx(
            total_sales_30d=100000,
            customers_by_revenue=[
                {"customer_name": "A", "_id": "a", "total_revenue": 20000}
            ],
        )
        alerts = await check_revenue_concentration(ctx)
        assert len(alerts) == 0


class TestCategoryE:
    """Category E: Dependencies & Operational Risks."""

    @pytest.mark.asyncio
    async def test_supplier_concentration_triggers(self):
        # Smart suppression skips orgs with ≤ 2 suppliers (structurally
        # concentrated, alert would be noise). Test must include ≥ 3 with
        # the dominant one still at 60%.
        from modules.cashflow_monitor.rules.category_e_dependencies import check_supplier_concentration
        ctx = _make_ctx(
            total_purchases_30d=50000,
            suppliers_by_amount=[
                {"_id": "Fornitore Unico", "total": 30000},
                {"_id": "Fornitore B", "total": 15000},
                {"_id": "Fornitore C", "total": 5000},
            ],
        )
        alerts = await check_supplier_concentration(ctx)
        assert len(alerts) == 1
        assert alerts[0].severity.value == "high"  # 60% > critical threshold

    @pytest.mark.asyncio
    async def test_fixed_cost_ratio_triggers(self):
        from modules.cashflow_monitor.rules.category_e_dependencies import check_fixed_cost_ratio_high
        ctx = _make_ctx(
            total_sales_30d=10000,
            total_fixed_costs_30d=6500,  # 65% → HIGH
        )
        alerts = await check_fixed_cost_ratio_high(ctx)
        assert len(alerts) == 1
        assert alerts[0].alert_category == "E"


class TestYoYComparison:
    """Category D: YoY anomaly — period-intelligent comparison."""

    @pytest.mark.asyncio
    async def test_yoy_skips_before_day_7(self):
        """Should skip if current month has < 7 days (too early)."""
        from modules.cashflow_monitor.rules.category_d_patterns import check_yoy_anomaly
        ctx = _make_ctx(
            today=date(2026, 4, 3),  # Day 3 of April
            current_month_day=3,
            days_of_data=400,
        )
        alerts = await check_yoy_anomaly(ctx)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_yoy_equal_days_no_false_positive(self):
        """Comparing 10 days vs 10 days with equal sales → no alert."""
        from modules.cashflow_monitor.rules.category_d_patterns import check_yoy_anomaly

        # Build daily sales: Apr 1-10 2026 = 1000/day, Apr 1-10 2025 = 1000/day
        # Plus Apr 11-30 2025 = 1000/day (rest of month — should NOT be counted)
        sales_365d = {}
        for d in range(10):
            sales_365d[f"2026-04-{d+1:02d}"] = 1000.0  # Current: 10 days × 1000
            sales_365d[f"2025-04-{d+1:02d}"] = 1000.0  # Last year same 10 days × 1000
        # Add rest of April 2025 (should be ignored by new logic)
        for d in range(10, 30):
            sales_365d[f"2025-04-{d+1:02d}"] = 1000.0  # Extra 20 days

        ctx = _make_ctx(
            today=date(2026, 4, 10),
            current_month_day=10,
            days_of_data=400,
            sales_by_date_365d=sales_365d,
        )
        alerts = await check_yoy_anomaly(ctx)
        assert len(alerts) == 0  # Equal sales, no decline

    @pytest.mark.asyncio
    async def test_yoy_detects_real_decline(self):
        """Comparing 10 days with genuine decline → alert fires."""
        from modules.cashflow_monitor.rules.category_d_patterns import check_yoy_anomaly

        sales_365d = {}
        for d in range(10):
            sales_365d[f"2026-04-{d+1:02d}"] = 200.0   # Current: 2000 total
            sales_365d[f"2025-04-{d+1:02d}"] = 1000.0  # Last year: 10000 total

        ctx = _make_ctx(
            today=date(2026, 4, 10),
            current_month_day=10,
            days_of_data=400,
            sales_by_date_365d=sales_365d,
        )
        alerts = await check_yoy_anomaly(ctx)
        assert len(alerts) == 1  # -80% decline
        assert alerts[0].severity.value == "high"
        assert alerts[0].metric_payload.get("days_compared") == 10

    @pytest.mark.asyncio
    async def test_yoy_full_month_works(self):
        """Full month comparison (day 30) still works correctly."""
        from modules.cashflow_monitor.rules.category_d_patterns import check_yoy_anomaly

        sales_365d = {}
        for d in range(30):
            sales_365d[f"2026-03-{d+1:02d}"] = 1000.0  # March 2026: 30k
            sales_365d[f"2025-03-{d+1:02d}"] = 2000.0  # March 2025: 60k

        ctx = _make_ctx(
            today=date(2026, 3, 30),
            current_month_day=30,
            days_of_data=400,
            sales_by_date_365d=sales_365d,
        )
        alerts = await check_yoy_anomaly(ctx)
        assert len(alerts) == 1  # -50% decline
        assert alerts[0].metric_payload.get("days_compared") == 30


class TestDeduplication:
    """Verify entity-key based deduplication."""

    @pytest.mark.asyncio
    async def test_existing_key_prevents_duplicate(self):
        from modules.cashflow_monitor.rules.category_a_liquidity import check_cash_runway_critical
        ctx = _make_ctx(
            existing_keys={("cash_runway_critical", "month_2026-04")},
            total_sales_30d=50000,
            total_expenses_30d=20000,
            total_purchases_30d=15000,
            total_fixed_costs_30d=5000,
        )
        alerts = await check_cash_runway_critical(ctx)
        assert len(alerts) == 0  # Deduped

    @pytest.mark.asyncio
    async def test_different_entity_creates_new(self):
        from modules.cashflow_monitor.rules.category_a_liquidity import check_cash_runway_critical
        ctx = _make_ctx(
            existing_keys={("cash_runway_critical", "month_2026-03")},  # Different month
            total_sales_30d=50000,
            total_expenses_30d=20000,
            total_purchases_30d=15000,
            total_fixed_costs_30d=5000,
        )
        alerts = await check_cash_runway_critical(ctx)
        assert len(alerts) == 1  # New entity_key → new alert


class TestAlertStructure:
    """Verify alert output structure conforms to v3 schema."""

    @pytest.mark.asyncio
    async def test_alert_has_v3_fields(self):
        from modules.cashflow_monitor.rules.category_e_dependencies import check_fixed_cost_ratio_high
        ctx = _make_ctx(
            total_sales_30d=10000,
            total_fixed_costs_30d=6500,
        )
        alerts = await check_fixed_cost_ratio_high(ctx)
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_category == "E"
        assert alert.entity_key is not None
        assert alert.suggested_action is not None
        assert alert.schema_version == "3.0"
        assert alert.metric_payload.get("alert_type") == "fixed_cost_ratio_high"
