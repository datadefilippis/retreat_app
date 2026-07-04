"""Pure formula layer for Customer Insights.

Every customer KPI rendered on the Insights page is a deterministic
function of (raw aggregates, configuration). Putting them here as
pure functions yields:

  • Testability — unit tests cover edge cases (empty input, single
    purchase, division-by-zero, all-same-day) without spinning up
    a database.
  • Auditability — the merchant-facing "info-box" copy in the UI
    can quote the exact code path used to compute the number.
  • Single source of truth — the legacy ``modules.customers_light``
    service and the new ``customer_insights`` service both import
    from this module in Phase 1+. Refactoring one always refactors
    the other.

Five formulas were *corrected* relative to the legacy code (cf.
``docs/CUSTOMER_INSIGHTS_FORMULAS.md`` "Before/After" section):

  1.  ``projected_annual_revenue`` (was ``lifetime_value``)
      — only meaningful with ≥ 3 purchases; honest naming.
  2.  ``purchase_frequency_monthly``
      — returns None when history is too short (< 3 purchases)
        instead of an inflated value.
  3.  ``churn_risk_breakdown``
      — same score, but returns the per-component split so the
        info-box can explain "Recency 32 + Frequency 18 + …".
  4.  ``classify_segment``
      — accepts a ``LifecycleThresholds`` config so a yoga studio
        (weekly cadence) and a wedding photographer (annual) can
        each define what "active" means.
  5.  ``classify_trend``
      — accepts a ``threshold`` so the 20 % growth/decline cutoff
        is no longer hardcoded.

All functions are sync (no I/O) and accept primitives (no Pydantic
models, no Mongo dicts) so they remain easy to call from anywhere
and impossible to break by mocking the wrong thing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ─── Configuration ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LifecycleThresholds:
    """Configurable lifecycle bucket thresholds (in days, percentile).

    Defaults reproduce the legacy ``modules.customers_light`` behaviour
    exactly so the migration is bit-for-bit safe. Override per-org via
    ``organization.settings.customer_lifecycle``:

        {
          "new_days": 30,           # yoga studio: weekly cadence
          "active_days": 14,
          "occasional_days": 60,
          "top_pct": 0.10,
        }

    Attributes:
        new_days:        Customer is "new" if first purchase within this
                         many days.
        active_days:     Customer is "active" if last purchase within
                         this many days.
        occasional_days: Customer is "occasional" if last purchase
                         within this many days (otherwise inactive).
        top_pct:         Customer is "top" if revenue rank percentile
                         ≤ this value (0.10 = top 10 %).
    """

    new_days: int = 90
    active_days: int = 60
    occasional_days: int = 180
    top_pct: float = 0.10


@dataclass(frozen=True)
class TrendThresholds:
    """Configurable trend classification thresholds.

    The legacy code hardcoded ±20 %. Some industries (e.g. a coach
    with 1-2 sessions/month) need a tighter band; some (e.g. event
    organizers with seasonal swings) need wider.

    Attributes:
        growth_factor:   ``recent ≥ previous × growth_factor`` →
                         "growing". Default 1.20 (= +20 %).
        decline_factor:  ``recent ≤ previous × decline_factor`` →
                         "declining". Default 0.80 (= -20 %).
    """

    growth_factor: float = 1.20
    decline_factor: float = 0.80


@dataclass(frozen=True)
class ChurnRiskBreakdown:
    """Per-component split of the 0-100 churn risk score.

    Returned by :func:`compute_churn_risk_breakdown` so the info-box
    can render "Recency 32 + Frequency 18 + Single-purchase 20".

    Components sum (capped at 100):

        score = min(100, recency + frequency + single_penalty + cancel_penalty)
    """

    score: int
    recency: int
    frequency: int
    single_penalty: int
    cancel_penalty: int


# Sentinel for "not applicable" projected/frequency metrics.
_INSUFFICIENT_HISTORY = None
MIN_PURCHASES_FOR_FREQUENCY = 3
"""Minimum purchase count for ``purchase_frequency_monthly`` to be
considered representative. With < 3 purchases the implied cadence is
noise, so we return None and the UI shows "Storia troppo breve"."""


# ─── Date helpers (sync, side-effect-free) ─────────────────────────────────


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    """Parse a YYYY-MM-DD string. Returns None for None/invalid input.

    >>> _parse_iso_date("2026-01-15")
    datetime.date(2026, 1, 15)
    >>> _parse_iso_date(None) is None
    True
    >>> _parse_iso_date("not-a-date") is None
    True
    >>> _parse_iso_date("") is None
    True
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def days_since(today: date, last_date_iso: Optional[str]) -> int:
    """Days between today and the ISO date. Returns 0 if last is missing/invalid.

    The 0-fallback intentionally matches the legacy behaviour. The UI
    distinguishes "never purchased" from "purchased today" via
    ``transaction_count == 0``, so the 0 fallback is harmless here.

    >>> from datetime import date
    >>> days_since(date(2026, 1, 31), "2026-01-01")
    30
    >>> days_since(date(2026, 1, 31), None)
    0
    >>> days_since(date(2026, 1, 31), "garbage")
    0
    """
    last = _parse_iso_date(last_date_iso)
    if last is None:
        return 0
    return (today - last).days


def months_active_between(
    first_date_iso: Optional[str], last_date_iso: Optional[str]
) -> float:
    """Return the active span in months between first and last purchase.

    Floor of 1.0 month (30 days) — a customer with all purchases on the
    same day is still treated as having one month of "activity" for
    frequency math.

    >>> months_active_between("2026-01-01", "2026-01-01")
    1.0
    >>> months_active_between("2026-01-01", "2026-04-01")  # 90 days
    3.0
    >>> months_active_between(None, "2026-04-01")
    1.0
    """
    first = _parse_iso_date(first_date_iso)
    last = _parse_iso_date(last_date_iso)
    if first is None or last is None or first == last:
        return 1.0
    return max((last - first).days / 30.0, 1.0)


# ─── Per-customer derived metrics ──────────────────────────────────────────


def avg_transaction_value(total_revenue: float, count: int) -> float:
    """Average revenue per transaction, 0 if no transactions.

    >>> avg_transaction_value(1000.0, 4)
    250.0
    >>> avg_transaction_value(0.0, 0)
    0.0
    >>> avg_transaction_value(50.0, 1)
    50.0
    """
    if count <= 0:
        return 0.0
    return round(total_revenue / count, 2)


def purchase_frequency_monthly(
    count: int,
    first_date_iso: Optional[str],
    last_date_iso: Optional[str],
) -> Optional[float]:
    """Transactions per month (None when history is too short).

    Correction vs legacy: a customer with 1 purchase 5 days ago used
    to return ``1.0/month`` (because months_active was floored at 1.0,
    yielding 1/1 = 1.0). That's misleading: we have no signal at all.
    Now we return None for ``count < MIN_PURCHASES_FOR_FREQUENCY`` so
    the UI can render "Storia troppo breve" and downstream metrics
    (LTV projection, frequency-based segments) skip cleanly.

    >>> purchase_frequency_monthly(1, "2026-01-01", "2026-01-05") is None
    True
    >>> purchase_frequency_monthly(2, "2026-01-01", "2026-01-05") is None
    True
    >>> purchase_frequency_monthly(3, "2026-01-01", "2026-04-01")  # 90d → 3 months
    1.0
    >>> purchase_frequency_monthly(6, "2026-01-01", "2026-04-01")
    2.0
    >>> purchase_frequency_monthly(0, None, None) is None
    True
    """
    if count < MIN_PURCHASES_FOR_FREQUENCY:
        return _INSUFFICIENT_HISTORY
    months = months_active_between(first_date_iso, last_date_iso)
    return round(count / months, 2)


def revenue_share_pct(customer_revenue: float, total_org_revenue: float) -> float:
    """Customer's share of total org revenue, 0 if org has no revenue yet.

    >>> revenue_share_pct(150.0, 1000.0)
    15.0
    >>> revenue_share_pct(0.0, 1000.0)
    0.0
    >>> revenue_share_pct(150.0, 0.0)
    0.0
    """
    if total_org_revenue <= 0:
        return 0.0
    return round(customer_revenue / total_org_revenue * 100, 2)


def revenue_rank_pct(rank_idx: int, total_customers: int) -> float:
    """Percentile rank (0.0 = top, 1.0 = bottom) for segment classification.

    rank_idx is 0-based, sorted descending by revenue.

    >>> revenue_rank_pct(0, 100)
    0.0
    >>> revenue_rank_pct(9, 100)
    0.09
    >>> revenue_rank_pct(99, 100)
    0.99
    >>> revenue_rank_pct(0, 1)  # only customer
    0.0
    """
    if total_customers <= 1:
        return 0.0
    return rank_idx / total_customers


def projected_annual_revenue(
    avg_tx: float,
    frequency_monthly: Optional[float],
) -> Optional[float]:
    """Estimate of one customer's revenue over the next 12 months.

    Was previously named ``lifetime_value`` — renamed to
    ``projected_annual_revenue`` because it is *not* a true LTV
    (no retention curve, no discount rate). Honest naming prevents
    the merchant from over-trusting the number for valuation work.

    Returns None when frequency is None (i.e. history too short).

    >>> projected_annual_revenue(50.0, 2.0)  # 50 € avg × 2/month × 12
    1200.0
    >>> projected_annual_revenue(50.0, None) is None
    True
    >>> projected_annual_revenue(0.0, 1.0)
    0.0
    """
    if frequency_monthly is None:
        return _INSUFFICIENT_HISTORY
    return round(avg_tx * frequency_monthly * 12, 2)


# ─── Churn risk ────────────────────────────────────────────────────────────


def compute_churn_risk_breakdown(
    days_since_last: int,
    frequency_monthly: Optional[float],
    transaction_count: int,
    cancellation_rate_pct: float = 0.0,
    orders_cancelled: int = 0,
) -> ChurnRiskBreakdown:
    """Decompose the 0-100 churn risk score into transparent components.

    Score = min(100, recency + frequency + single_penalty + cancel_penalty).

    Components:
      • recency (0-50)        — linear from 0 (≤ 30 d) to 50 (≥ 180 d)
      • frequency (0-30)      — 0 if ≥ 2/month; 30 if < 0.5/month;
                                None-frequency treated as 30 (worst).
      • single_penalty (0-20) — flat +20 if exactly 1 purchase
      • cancel_penalty (0-20) — +20 if cancellation_rate_pct > 30,
                                else +10 if orders_cancelled > 3, else 0

    The legacy ``_compute_churn_risk`` returned only the final integer.
    We return the breakdown so the info-box can show
    "Recency 32 + Frequency 18 + Single +20" — addressing the merchant
    complaint that "the score appears arbitrary".

    >>> br = compute_churn_risk_breakdown(60, 1.0, 5)
    >>> br.score
    30
    >>> br.recency
    10
    >>> br.frequency
    20
    >>> br.single_penalty
    0

    >>> compute_churn_risk_breakdown(200, 0.1, 1).score
    100
    >>> compute_churn_risk_breakdown(10, 5.0, 10).score  # power user
    0
    """
    # Recency component (0-50)
    if days_since_last <= 30:
        recency = 0
    elif days_since_last <= 180:
        recency = int((days_since_last - 30) / 150 * 50)
    else:
        recency = 50

    # Frequency component (0-30)
    # None-frequency means "history too short to assess" — treat as worst
    # case so we err on the side of flagging the customer for follow-up.
    if frequency_monthly is None:
        frequency = 30
    elif frequency_monthly >= 2.0:
        frequency = 0
    elif frequency_monthly >= 0.5:
        frequency = int((2.0 - frequency_monthly) / 1.5 * 30)
    else:
        frequency = 30

    # Single-purchase flat penalty (0-20)
    single_penalty = 20 if transaction_count == 1 else 0

    # Cancellation penalty (0-20)
    if cancellation_rate_pct > 30:
        cancel_penalty = 20
    elif orders_cancelled > 3:
        cancel_penalty = 10
    else:
        cancel_penalty = 0

    raw = recency + frequency + single_penalty + cancel_penalty
    score = min(100, raw)
    return ChurnRiskBreakdown(
        score=score,
        recency=recency,
        frequency=frequency,
        single_penalty=single_penalty,
        cancel_penalty=cancel_penalty,
    )


def churn_risk_score(
    days_since_last: int,
    frequency_monthly: Optional[float],
    transaction_count: int,
    cancellation_rate_pct: float = 0.0,
    orders_cancelled: int = 0,
) -> int:
    """Convenience wrapper returning just the 0-100 score.

    Used by the legacy ``modules.customers_light.service`` for backward
    compatibility. New code should call
    :func:`compute_churn_risk_breakdown` directly to also get the
    component split.

    >>> churn_risk_score(10, 5.0, 10)
    0
    >>> churn_risk_score(200, 0.1, 1)
    100
    """
    return compute_churn_risk_breakdown(
        days_since_last,
        frequency_monthly,
        transaction_count,
        cancellation_rate_pct,
        orders_cancelled,
    ).score


# ─── Segment & lifecycle classification ────────────────────────────────────


def classify_segment(
    days_since_last: int,
    first_date_iso: Optional[str],
    rank_pct: float,
    today: Optional[date] = None,
    thresholds: LifecycleThresholds = LifecycleThresholds(),
) -> str:
    """Classify a customer into one of 5 segments.

    Priority (first match wins):
        new > top > active > occasional > inactive

    The legacy implementation hardcoded the three day thresholds and
    the top-revenue percentile. ``thresholds`` makes them configurable
    per-org so a yoga studio (weekly cadence) and a wedding
    photographer (annual cadence) can each define "active" correctly.

    >>> from datetime import date
    >>> today = date(2026, 6, 1)

    Customer with first purchase 30 days ago → "new"
    >>> classify_segment(2, "2026-05-02", 0.5, today=today)
    'new'

    Top-revenue customer (rank pct 5 %) → "top"
    >>> classify_segment(45, "2024-01-01", 0.05, today=today)
    'top'

    Active by recency (within 60 days)
    >>> classify_segment(45, "2024-01-01", 0.5, today=today)
    'active'

    Occasional (61-180 days)
    >>> classify_segment(120, "2024-01-01", 0.5, today=today)
    'occasional'

    Inactive (> 180 days)
    >>> classify_segment(300, "2024-01-01", 0.5, today=today)
    'inactive'

    Configurable thresholds — yoga studio with weekly cadence:
    >>> tight = LifecycleThresholds(new_days=14, active_days=7, occasional_days=30)
    >>> classify_segment(10, "2024-01-01", 0.5, today=today, thresholds=tight)
    'occasional'
    """
    if today is None:
        today = date.today()

    # 1. New: first purchase recently (relative to ``new_days``)
    first = _parse_iso_date(first_date_iso)
    if first is not None and (today - first).days <= thresholds.new_days:
        return "new"

    # 2. Top: revenue rank percentile
    if rank_pct <= thresholds.top_pct:
        return "top"

    # 3. Active: last purchase within ``active_days``
    if days_since_last <= thresholds.active_days:
        return "active"

    # 4. Occasional: last purchase within ``occasional_days``
    if days_since_last <= thresholds.occasional_days:
        return "occasional"

    # 5. Inactive: last purchase past occasional threshold
    return "inactive"


def classify_trend(
    recent_revenue: float,
    previous_revenue: float,
    segment: str,
    thresholds: TrendThresholds = TrendThresholds(),
) -> str:
    """Classify revenue trend direction relative to the previous window.

    Returns one of: ``new``, ``growing``, ``declining``, ``stable``.

    Rules:
      • ``segment == "new"`` → "new" (no previous window to compare).
      • ``previous_revenue ≤ 0`` and ``recent > 0`` → "new".
      • ``recent ≥ previous × growth_factor`` → "growing".
      • ``recent ≤ previous × decline_factor`` → "declining".
      • Otherwise → "stable".

    >>> classify_trend(100, 50, "active")  # +100 % → growing
    'growing'
    >>> classify_trend(50, 100, "active")  # -50 % → declining
    'declining'
    >>> classify_trend(105, 100, "active")  # +5 % within stable band
    'stable'
    >>> classify_trend(100, 0, "active")  # no previous → "new"
    'new'
    >>> classify_trend(100, 100, "new")  # any new customer → "new"
    'new'

    Tighter thresholds (10 %):
    >>> sensitive = TrendThresholds(growth_factor=1.10, decline_factor=0.90)
    >>> classify_trend(112, 100, "active", thresholds=sensitive)
    'growing'
    """
    if segment == "new":
        return "new"
    if previous_revenue <= 0:
        return "new" if recent_revenue > 0 else "stable"
    if recent_revenue >= previous_revenue * thresholds.growth_factor:
        return "growing"
    if recent_revenue <= previous_revenue * thresholds.decline_factor:
        return "declining"
    return "stable"


def classify_status(segment: str, churn_risk: int, trend: str) -> str:
    """Derive operational status from segment + churn + trend.

    Returns one of: ``healthy``, ``watch``, ``at_risk``, ``lost``.

    Priority (first match wins):
      • inactive segment → "lost"
      • churn_risk ≥ 60 → "at_risk"
      • occasional or declining → "watch"
      • everything else → "healthy"

    >>> classify_status("active", 10, "growing")
    'healthy'
    >>> classify_status("inactive", 0, "stable")
    'lost'
    >>> classify_status("active", 75, "growing")
    'at_risk'
    >>> classify_status("occasional", 30, "stable")
    'watch'
    >>> classify_status("active", 30, "declining")
    'watch'
    """
    if segment == "inactive":
        return "lost"
    if churn_risk >= 60:
        return "at_risk"
    if segment == "occasional" or trend == "declining":
        return "watch"
    return "healthy"


# ─── Concentration metrics (org-level) ────────────────────────────────────


def top_n_share_pct(customer_revenues: list[float], top_n: int) -> float:
    """Share of revenue captured by the top N customers.

    ``customer_revenues`` MAY be in any order — we sort here so the
    caller doesn't have to. Returns 0.0 when org has no revenue.

    >>> top_n_share_pct([100, 50, 30, 20], 2)  # top 2 = 150 / 200 = 75
    75.0
    >>> top_n_share_pct([100, 50, 30, 20], 10)  # top_n > len → all
    100.0
    >>> top_n_share_pct([], 5)
    0.0
    >>> top_n_share_pct([0, 0, 0], 2)  # zero-revenue customers
    0.0
    """
    total = sum(customer_revenues)
    if total <= 0:
        return 0.0
    sorted_desc = sorted(customer_revenues, reverse=True)
    top_sum = sum(sorted_desc[:top_n])
    return round(top_sum / total * 100, 1)


def avg_customer_value(total_revenue: float, total_customers: int) -> float:
    """Mean revenue per customer.

    >>> avg_customer_value(1000.0, 4)
    250.0
    >>> avg_customer_value(0.0, 0)
    0.0
    >>> avg_customer_value(1000.0, 0)
    0.0
    """
    if total_customers <= 0:
        return 0.0
    return round(total_revenue / total_customers, 2)


def inactive_rate_pct(inactive_count: int, total_customers: int) -> float:
    """Percentage of customers in the "inactive" segment.

    >>> inactive_rate_pct(15, 100)
    15.0
    >>> inactive_rate_pct(0, 100)
    0.0
    >>> inactive_rate_pct(5, 0)
    0.0
    """
    if total_customers <= 0:
        return 0.0
    return round(inactive_count / total_customers * 100, 1)


# ─── Payment reliability ───────────────────────────────────────────────────


def payment_reliability_pct(
    paid_on_time: int, total_with_due_date: int
) -> Optional[float]:
    """Share of invoices paid on time, None if no due-date data.

    None (not 0) communicates "we don't know" vs "they always pay
    late". The UI distinguishes the two states.

    >>> payment_reliability_pct(8, 10)
    80.0
    >>> payment_reliability_pct(0, 0) is None
    True
    >>> payment_reliability_pct(0, 5)
    0.0
    """
    if total_with_due_date <= 0:
        return None
    return round(paid_on_time / total_with_due_date * 100, 1)


# ─── Order metrics ─────────────────────────────────────────────────────────


def cancellation_rate_pct(orders_cancelled: int, order_count: int) -> float:
    """Share of orders cancelled, 0 if no orders.

    >>> cancellation_rate_pct(2, 10)
    20.0
    >>> cancellation_rate_pct(0, 0)
    0.0
    """
    if order_count <= 0:
        return 0.0
    return round(orders_cancelled / order_count * 100, 1)


def fulfillment_success_rate(
    fulfilled_count: int, total_with_fulfillment: int
) -> Optional[float]:
    """Share of orders successfully fulfilled, None if no fulfillment data.

    >>> fulfillment_success_rate(7, 10)
    70.0
    >>> fulfillment_success_rate(0, 0) is None
    True
    >>> fulfillment_success_rate(10, 10)
    100.0
    """
    if total_with_fulfillment <= 0:
        return None
    return round(fulfilled_count / total_with_fulfillment * 100, 1)


def avg_order_value(order_total_value: float, order_count: int) -> float:
    """Mean order value, 0 if no orders.

    >>> avg_order_value(450.0, 3)
    150.0
    >>> avg_order_value(0.0, 0)
    0.0
    """
    if order_count <= 0:
        return 0.0
    return round(order_total_value / order_count, 2)


# ─── Period delta (Phase 1 will use these for MoM/YoY) ────────────────────


def percentage_delta(current: float, previous: float) -> Optional[float]:
    """Percent change vs previous period. None when previous is zero.

    None preserves "no comparison possible" — better than +∞ or 0.0
    which would mislead the merchant.

    >>> percentage_delta(120, 100)
    20.0
    >>> percentage_delta(80, 100)
    -20.0
    >>> percentage_delta(50, 0) is None
    True
    >>> percentage_delta(0, 100)
    -100.0
    """
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)
