"""
Alert Thresholds — configurable sensitivity presets for alert rules.

Three presets: CONSERVATIVE (more alerts), STANDARD (balanced), RELAXED (fewer alerts).
Pure data module, no IO. Loaded once per alert generation cycle.

Each key corresponds to an alert rule identifier.
Values are dicts with rule-specific threshold parameters.
"""

# ── Category A: Liquidity & Survival ─────────────────────────────────────────

_CAT_A = {
    "conservative": {
        "cash_runway_warning_days": 45,
        "cash_runway_critical_days": 20,
        "negative_days_warning": 3,       # out of 7
        "negative_days_critical": 7,      # out of 14
        "negative_window_short": 7,
        "negative_window_long": 14,
        "month_loss_minor_pct": 5,        # loss < 5% revenue → MEDIUM
        "revenue_concentration_warning_pct": 30,
        "revenue_concentration_critical_pct": 50,
    },
    "standard": {
        "cash_runway_warning_days": 30,
        "cash_runway_critical_days": 15,
        "negative_days_warning": 5,
        "negative_days_critical": 10,
        "negative_window_short": 7,
        "negative_window_long": 14,
        "month_loss_minor_pct": 10,
        "revenue_concentration_warning_pct": 40,
        "revenue_concentration_critical_pct": 60,
    },
    "relaxed": {
        "cash_runway_warning_days": 15,
        "cash_runway_critical_days": 7,
        "negative_days_warning": 7,
        "negative_days_critical": 12,
        "negative_window_short": 7,
        "negative_window_long": 14,
        "month_loss_minor_pct": 15,
        "revenue_concentration_warning_pct": 50,
        "revenue_concentration_critical_pct": 70,
    },
}

# ── Category B: Profitability ────────────────────────────────────────────────

_CAT_B = {
    "conservative": {
        "margin_erosion_months": 2,
        "margin_erosion_pp_warning": 5,     # percentage points total erosion
        "margin_erosion_pp_critical": 10,
        "unit_cost_increase_warning_pct": 5,
        "unit_cost_increase_critical_pct": 15,
        "break_even_deficit_warning_pct": 10,
        "break_even_deficit_critical_pct": 25,
        "category_trend_warning_pct": 30,
        "category_trend_months": 2,
        "category_trend_min_eur": 300,
    },
    "standard": {
        "margin_erosion_months": 3,
        "margin_erosion_pp_warning": 8,
        "margin_erosion_pp_critical": 15,
        "unit_cost_increase_warning_pct": 10,
        "unit_cost_increase_critical_pct": 25,
        "break_even_deficit_warning_pct": 15,
        "break_even_deficit_critical_pct": 30,
        "category_trend_warning_pct": 50,
        "category_trend_months": 2,
        "category_trend_min_eur": 500,
    },
    "relaxed": {
        "margin_erosion_months": 4,
        "margin_erosion_pp_warning": 12,
        "margin_erosion_pp_critical": 20,
        "unit_cost_increase_warning_pct": 15,
        "unit_cost_increase_critical_pct": 35,
        "break_even_deficit_warning_pct": 25,
        "break_even_deficit_critical_pct": 40,
        "category_trend_warning_pct": 75,
        "category_trend_months": 3,
        "category_trend_min_eur": 1000,
    },
}

# ── Category C: Cash Cycle ───────────────────────────────────────────────────

_CAT_C = {
    "conservative": {
        "dso_increase_warning_pct": 15,
        "dso_min_days": 20,
        "invoice_risk_revenue_pct": 20,
        "invoice_risk_overdue_days": 20,
        "ccc_gap_warning_days": 30,
        "ccc_gap_critical_days": 60,
    },
    "standard": {
        "dso_increase_warning_pct": 20,
        "dso_min_days": 30,
        "invoice_risk_revenue_pct": 30,
        "invoice_risk_overdue_days": 30,
        "ccc_gap_warning_days": 45,
        "ccc_gap_critical_days": 90,
    },
    "relaxed": {
        "dso_increase_warning_pct": 30,
        "dso_min_days": 45,
        "invoice_risk_revenue_pct": 40,
        "invoice_risk_overdue_days": 45,
        "ccc_gap_warning_days": 60,
        "ccc_gap_critical_days": 120,
    },
}

# ── Category D: Patterns & Seasonality ───────────────────────────────────────

_CAT_D = {
    "conservative": {
        "yoy_decline_warning_pct": 15,
        "yoy_decline_critical_pct": 30,
        "trend_break_months": 2,
        "weekly_sigma_warning": 1.5,
        "weekly_sigma_critical": 2.5,
        "weekly_lookback_weeks": 8,
    },
    "standard": {
        "yoy_decline_warning_pct": 25,
        "yoy_decline_critical_pct": 40,
        "trend_break_months": 3,
        "weekly_sigma_warning": 2.0,
        "weekly_sigma_critical": 3.0,
        "weekly_lookback_weeks": 8,
    },
    "relaxed": {
        "yoy_decline_warning_pct": 35,
        "yoy_decline_critical_pct": 50,
        "trend_break_months": 4,
        "weekly_sigma_warning": 2.5,
        "weekly_sigma_critical": 3.5,
        "weekly_lookback_weeks": 12,
    },
}

# ── Category E: Dependencies & Operational Risks ────────────────────────────

_CAT_E = {
    "conservative": {
        "supplier_conc_warning_pct": 30,
        "supplier_conc_critical_pct": 50,
        "product_conc_warning_pct": 40,
        "product_conc_critical_pct": 60,
        "fixed_cost_ratio_warning_pct": 35,
        "fixed_cost_ratio_critical_pct": 50,
    },
    "standard": {
        "supplier_conc_warning_pct": 40,
        "supplier_conc_critical_pct": 60,
        "product_conc_warning_pct": 50,
        "product_conc_critical_pct": 70,
        "fixed_cost_ratio_warning_pct": 45,
        "fixed_cost_ratio_critical_pct": 60,
    },
    "relaxed": {
        "supplier_conc_warning_pct": 50,
        "supplier_conc_critical_pct": 70,
        "product_conc_warning_pct": 60,
        "product_conc_critical_pct": 80,
        "fixed_cost_ratio_warning_pct": 55,
        "fixed_cost_ratio_critical_pct": 70,
    },
}

_CAT_F = {
    "conservative": {
        "order_backlog_count": 3,
        "fulfillment_delay_days": 5,
        "event_fill_warning_pct": 40,
        "cancellation_spike_pct": 15,
    },
    "standard": {
        "order_backlog_count": 5,
        "fulfillment_delay_days": 7,
        "event_fill_warning_pct": 30,
        "cancellation_spike_pct": 20,
    },
    "relaxed": {
        "order_backlog_count": 10,
        "fulfillment_delay_days": 14,
        "event_fill_warning_pct": 20,
        "cancellation_spike_pct": 30,
    },
}

VALID_PRESETS = ("conservative", "standard", "relaxed")


def get_thresholds(preset: str = "standard") -> dict:
    """Return merged threshold dict for the given preset.

    Keys are prefixed by category for clarity:
      a_cash_runway_warning_days, b_margin_erosion_months, f_order_backlog_count, etc.
    """
    if preset not in VALID_PRESETS:
        preset = "standard"

    merged: dict = {}
    for prefix, cat_dict in [
        ("a", _CAT_A),
        ("b", _CAT_B),
        ("c", _CAT_C),
        ("d", _CAT_D),
        ("e", _CAT_E),
        ("f", _CAT_F),
    ]:
        for key, value in cat_dict[preset].items():
            merged[f"{prefix}_{key}"] = value

    return merged
