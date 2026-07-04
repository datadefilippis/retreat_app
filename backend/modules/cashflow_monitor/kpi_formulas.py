"""
Canonical KPI Formulas — single source of truth for financial computations.

All functions are PURE: no IO, no DB, no side effects.
All functions return Optional[float]: None means "not computable."
All functions round internally per the rounding policy.

Rounding policy:
  - Percentages: round(value, 1)     →  72.5%
  - Day counts:  round(value, 1)     →  45.3 days
  - EUR amounts: round(value, 2)     →  €3,456.78
  - Ratios:      round(value, 4)     →  0.7823

Day-definition standard:
  All functions that accept `period_days` expect CALENDAR days:
    period_days = (end_date - start_date).days + 1
  Callers are responsible for computing this correctly.

Consumers:
  - overview_builder.py
  - insight_builder.py
  - alert_rules.py
  - health_score.py (via diagnostics)
"""

from typing import Optional


# ── Profitability ─────────────────────────────────────────────────────────────

def net_margin_pct(net_after_fixed: float, total_sales: float) -> Optional[float]:
    """Net profit margin as percentage of revenue.

    Returns None when total_sales <= 0 (margin not computable without revenue).
    """
    if total_sales <= 0:
        return None
    return round(net_after_fixed / total_sales * 100, 1)


def cost_to_revenue_ratio(total_outflows: float, total_sales: float) -> Optional[float]:
    """Total costs as percentage of revenue.

    Returns None when total_sales <= 0.
    Can exceed 100% when costs exceed revenue.
    """
    if total_sales <= 0:
        return None
    return round(total_outflows / total_sales * 100, 1)


def variable_cost_ratio(variable_outflows: float, total_sales: float) -> Optional[float]:
    """Variable costs as a ratio of revenue (0.0 to 1.0+).

    Returns None when total_sales <= 0.
    Used as input to break_even_point().
    """
    if total_sales <= 0:
        return None
    return round(variable_outflows / total_sales, 4)


# ── Break-even ────────────────────────────────────────────────────────────────

def break_even_point(fixed_costs: float, var_cost_ratio: Optional[float]) -> Optional[float]:
    """Break-even revenue point (EUR).

    Formula: fixed_costs / (1 - variable_cost_ratio)

    Returns None when:
      - var_cost_ratio is None (no sales data)
      - fixed_costs <= 0 (no fixed costs recorded)
      - var_cost_ratio >= 1.0 (variable costs consume all revenue)
    """
    if var_cost_ratio is None:
        return None
    if fixed_costs <= 0:
        return None
    if var_cost_ratio >= 1.0:
        return None
    return round(fixed_costs / (1 - var_cost_ratio), 2)


def break_even_headroom_pct(total_sales: float, break_even: Optional[float]) -> Optional[float]:
    """How far above break-even as percentage.

    Positive = above break-even (safe). Negative = below (deficit).
    Returns None when break_even is None or total_sales <= 0.
    """
    if break_even is None:
        return None
    if total_sales <= 0:
        return None
    if break_even <= 0:
        return None
    return round(((total_sales - break_even) / break_even) * 100, 1)


def fixed_cost_ratio(fixed_costs: float, total_sales: float) -> Optional[float]:
    """Fixed costs as percentage of revenue (operational leverage).

    Returns None when total_sales <= 0 or fixed_costs <= 0.
    """
    if total_sales <= 0:
        return None
    if fixed_costs <= 0:
        return None
    return round(fixed_costs / total_sales * 100, 1)


# ── Cash flow timing ──────────────────────────────────────────────────────────

def dso(open_receivables: float, total_sales: float, period_days: int) -> Optional[float]:
    """Days Sales Outstanding — average collection period.

    Returns None when total_sales <= 0 or period_days <= 0.
    Returns 0.0 when open_receivables == 0 (all paid — legitimate zero).
    """
    if total_sales <= 0 or period_days <= 0:
        return None
    return round(open_receivables / total_sales * period_days, 1)


def dpo(open_payables: float, supplier_purchases: float, period_days: int) -> Optional[float]:
    """Days Payable Outstanding — average payment period to suppliers.

    Returns None when supplier_purchases <= 0 or period_days <= 0.
    Returns 0.0 when open_payables == 0 (all paid — legitimate zero).
    """
    if supplier_purchases <= 0 or period_days <= 0:
        return None
    return round(open_payables / supplier_purchases * period_days, 1)


def cash_conversion_gap(dso_value: Optional[float], dpo_value: Optional[float]) -> Optional[float]:
    """Cash Conversion Gap = DSO - DPO (days).

    Negative = cash comes in before it goes out (good).
    Returns None only when BOTH DSO and DPO are not computable.
    When only one is computable, uses 0 for the missing one.
    """
    if dso_value is None and dpo_value is None:
        return None
    effective_dso = dso_value if dso_value is not None else 0.0
    effective_dpo = dpo_value if dpo_value is not None else 0.0
    return round(effective_dso - effective_dpo, 1)


# ── Operational metrics ───────────────────────────────────────────────────────

def burn_rate_daily(total_outflows: float, period_days: int) -> Optional[float]:
    """Average daily outflows (EUR/day).

    Returns None when period_days <= 0.
    Returns 0.0 when total_outflows == 0 (no costs — legitimate zero).
    """
    if period_days <= 0:
        return None
    return round(total_outflows / period_days, 2)


def operational_coverage_days(
    net_after_fixed: float, total_outflows: float, period_days: int,
) -> Optional[float]:
    """How many days the current margin covers the daily burn rate.

    This is a PROXY metric — NOT real liquidity (no bank balance input).

    Returns:
      None  — when period_days <= 0 or total_outflows <= 0 (not computable)
      0.0   — when net_after_fixed <= 0 (in loss, zero coverage)
      float — days of coverage when profitable
    """
    if period_days <= 0:
        return None
    if total_outflows <= 0:
        return None
    if net_after_fixed <= 0:
        return 0.0
    daily_burn = total_outflows / period_days
    return round(net_after_fixed / daily_burn, 1)
