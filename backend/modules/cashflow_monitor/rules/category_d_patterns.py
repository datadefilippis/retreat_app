"""
Category D — Patterns & Seasonality

Rules:
  D1: yoy_anomaly              — revenue significantly different from same month last year
  D2: positive_trend_break     — first decline after N months of growth
  D3: weekly_statistical_anomaly — week statistically below 2σ of rolling mean
"""

import math
from typing import List
from datetime import timedelta
from models import Alert, AlertSeverity
from modules.cashflow_monitor.alert_i18n import (
    localize_title, localize_summary, localize_suggestion,
)
from modules.cashflow_monitor.data_quality import requires_data
from . import AlertContext, _fmt_eur, ALL_RULES

_SCHEMA = "3.0"
_MODULE = "cashflow_monitor"
_CAT = "D"


@requires_data(min_days_of_data=90, datasets=("sales",), min_samples_30d=30, outlier_robust=True, confidence_label="medium")
async def check_yoy_anomaly(ctx: AlertContext) -> List[Alert]:
    """D1: Revenue significantly different from same period last year.

    Compares the SAME number of days (day 1..N of current month vs day 1..N
    of same month last year) to avoid false positives from partial months.
    Skips if current month has < 7 days (too early for meaningful comparison).
    """
    alert_type = "yoy_anomaly"

    if ctx.days_of_data < 365:
        return []  # Need at least 13 months of data

    # Too early in month for meaningful comparison
    if ctx.current_month_day < 7:
        return []

    entity_key = f"yoy_{ctx.today.strftime('%Y-%m')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: monthly rotating entity_key. YoY decline
    # is a slow-moving trend — a 60-day cooldown after resolve gives
    # the merchant time to act before re-flagging.
    if ctx.was_recently_resolved(alert_type):
        return []

    # Sum sales day-by-day for current month (day 1..today)
    current_month_start = ctx.today.replace(day=1)
    days_to_compare = ctx.current_month_day

    current_amount = 0.0
    for d in range(days_to_compare):
        day_str = (current_month_start + timedelta(days=d)).isoformat()
        current_amount += ctx.sales_by_date_365d.get(day_str, 0.0)

    # Sum sales for SAME days last year (handles leap year gracefully)
    try:
        prev_year_start = current_month_start.replace(year=current_month_start.year - 1)
    except ValueError:
        # Feb 29 in leap year → use Feb 28
        prev_year_start = current_month_start.replace(year=current_month_start.year - 1, day=28)

    prev_amount = 0.0
    for d in range(days_to_compare):
        day_str = (prev_year_start + timedelta(days=d)).isoformat()
        prev_amount += ctx.sales_by_date_365d.get(day_str, 0.0)

    if prev_amount <= 0:
        return []

    change_pct = round((current_amount - prev_amount) / prev_amount * 100, 1)

    # Only alert on declines
    if change_pct >= 0:
        return []

    t = ctx.thresholds
    warning_pct = t.get("d_yoy_decline_warning_pct", 25)
    critical_pct = t.get("d_yoy_decline_critical_pct", 40)

    if abs(change_pct) < warning_pct:
        return []

    current_month = ctx.today.strftime("%Y-%m")
    severity = AlertSeverity.HIGH if abs(change_pct) >= critical_pct else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale, change_pct=change_pct),
        summary=localize_summary(alert_type, ctx.locale,
                                 month=current_month,
                                 current_amount=_fmt_eur(current_amount),
                                 prev_amount=_fmt_eur(prev_amount),
                                 change_pct=change_pct),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "current_amount": round(current_amount, 2),
            "prev_amount": round(prev_amount, 2),
            "change_pct": change_pct,
            "days_compared": days_to_compare,
            "current_period": f"{current_month_start.isoformat()} — {ctx.today.isoformat()}",
            "prev_period": f"{prev_year_start.isoformat()} — {(prev_year_start + timedelta(days=days_to_compare-1)).isoformat()}",
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=45, datasets=("sales",), min_samples_30d=30, outlier_robust=True, confidence_label="medium")
async def check_positive_trend_break(ctx: AlertContext) -> List[Alert]:
    """D2: First revenue decline after N+ months of consecutive growth."""
    alert_type = "positive_trend_break"

    t = ctx.thresholds
    required_months = t.get("d_trend_break_months", 3)

    if len(ctx.monthly_snapshots) < required_months + 2:
        return []

    # Check for consecutive growth then decline
    recent = ctx.monthly_snapshots[-(required_months + 2):]
    sales_series = [s.get("sales", 0) for s in recent]

    # Count consecutive growth months before the last
    growth_streak = 0
    for i in range(1, len(sales_series) - 1):
        if sales_series[i] > sales_series[i - 1]:
            growth_streak += 1
        else:
            growth_streak = 0

    if growth_streak < required_months:
        return []

    # Check if the last month is a decline
    last = sales_series[-1]
    prev = sales_series[-2]
    if last >= prev:
        return []

    decline_pct = round((last - prev) / prev * 100, 1) if prev > 0 else 0
    current_month = recent[-1].get("month", ctx.today.strftime("%Y-%m"))

    entity_key = f"break_{current_month}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: monthly rotating entity_key — the trend-
    # break is by nature a once-per-pattern event the merchant should
    # see, but after they resolve we shouldn't re-flag every subsequent
    # month's first dip for 60 days.
    if ctx.was_recently_resolved(alert_type):
        return []

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=AlertSeverity.MEDIUM,
        title=localize_title(alert_type, ctx.locale,
                             months=growth_streak),
        summary=localize_summary(alert_type, ctx.locale,
                                 months=growth_streak,
                                 current_month=current_month,
                                 decline_pct=abs(decline_pct)),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "growth_streak": growth_streak,
            "decline_pct": decline_pct,
            "current_month": current_month,
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=45, datasets=("sales",), min_samples_30d=30, outlier_robust=True, confidence_label="medium")
async def check_weekly_statistical_anomaly(ctx: AlertContext) -> List[Alert]:
    """D3: Current week's revenue statistically below 2σ of rolling mean."""
    alert_type = "weekly_statistical_anomaly"

    t = ctx.thresholds
    lookback_weeks = t.get("d_weekly_lookback_weeks", 8)
    sigma_warning = t.get("d_weekly_sigma_warning", 2.0)
    sigma_critical = t.get("d_weekly_sigma_critical", 3.0)

    # Need enough data
    required_days = lookback_weeks * 7 + 7
    if ctx.days_of_data < required_days:
        return []

    # Build weekly totals
    end = ctx.today
    weekly_totals = []

    for w in range(lookback_weeks + 1):
        week_end = end - timedelta(days=w * 7)
        week_start = week_end - timedelta(days=6)
        total = 0.0
        for i in range(7):
            d = (week_start + timedelta(days=i)).isoformat()
            total += ctx.sales_by_date_90d.get(d, 0.0)
        weekly_totals.append(total)

    weekly_totals.reverse()  # oldest first

    current_week = weekly_totals[-1]
    history = weekly_totals[:-1]

    if len(history) < 4:
        return []

    # Calculate mean and stddev
    mean = sum(history) / len(history)
    if mean <= 0:
        return []

    variance = sum((x - mean) ** 2 for x in history) / len(history)
    stddev = math.sqrt(variance) if variance > 0 else 0

    if stddev <= 0:
        return []

    sigma = (mean - current_week) / stddev  # positive = below mean

    if sigma < sigma_warning:
        return []

    # Calculate ISO week
    iso_year, iso_week, _ = ctx.today.isocalendar()
    entity_key = f"week_{iso_year}-W{iso_week:02d}"
    if ctx.is_dedup(alert_type, entity_key):
        return []

    severity = AlertSeverity.HIGH if sigma >= sigma_critical else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale, sigma=sigma),
        summary=localize_summary(alert_type, ctx.locale,
                                 sigma=sigma,
                                 current_amount=_fmt_eur(current_week),
                                 avg_amount=_fmt_eur(mean),
                                 weeks=len(history)),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "current_week_revenue": round(current_week, 2),
            "avg_weekly_revenue": round(mean, 2),
            "stddev": round(stddev, 2),
            "sigma": round(sigma, 2),
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


ALL_RULES.extend([
    check_yoy_anomaly,
    check_positive_trend_break,
    check_weekly_statistical_anomaly,
])
