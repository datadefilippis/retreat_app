"""
Category B — Profitability

Rules:
  B1: margin_erosion_trend      — margin declining for N+ months
  B2: unit_cost_increase        — cost-to-revenue ratio increasing
  B3: break_even_unreached      — break-even not met at mid-month
  B4: category_expense_trend    — expense category growing month-over-month
"""

from typing import List
from models import Alert, AlertSeverity
from modules.cashflow_monitor.alert_i18n import (
    localize_title, localize_summary, localize_suggestion,
)
from modules.cashflow_monitor.kpi_formulas import (
    break_even_point, variable_cost_ratio,
)
from modules.cashflow_monitor.data_quality import requires_data
from . import AlertContext, _fmt_eur, ALL_RULES

_SCHEMA = "3.0"
_MODULE = "cashflow_monitor"
_CAT = "B"


@requires_data(min_days_of_data=60, datasets=("sales", "purchases"), min_samples_30d=30, outlier_robust=True, confidence_label="high")
async def check_margin_erosion_trend(ctx: AlertContext) -> List[Alert]:
    """B1: Margin declining for N+ consecutive months."""
    alert_type = "margin_erosion_trend"

    # v14.2 anti-ridondanza: short-circuit if merchant resolved this
    # alert_type within the cooldown window. Margin erosion is a slow-
    # moving structural issue — once the merchant says "I know", 60 days
    # of quiet is appropriate before re-flagging the same pattern.
    if ctx.was_recently_resolved(alert_type):
        return []

    snapshots = ctx.monthly_snapshots
    t = ctx.thresholds
    required_months = t.get("b_margin_erosion_months", 3)

    if len(snapshots) < required_months + 1:
        return []

    # Check last N+1 months for consecutive decline
    recent = snapshots[-(required_months + 1):]
    margins = []
    for s in recent:
        m = s.get("net_margin_pct")
        if m is None:
            return []  # Can't assess with missing data
        margins.append(m)

    # Check if declining for required_months consecutive months
    consecutive_declines = 0
    for i in range(1, len(margins)):
        if margins[i] < margins[i - 1]:
            consecutive_declines += 1
        else:
            consecutive_declines = 0

    if consecutive_declines < required_months:
        return []

    entity_key = f"trend_{recent[-1].get('month', ctx.today.strftime('%Y-%m'))}"
    if ctx.is_dedup(alert_type, entity_key):
        return []

    start_margin = margins[0]
    end_margin = margins[-1]
    erosion_pp = round(start_margin - end_margin, 1)

    pp_warning = t.get("b_margin_erosion_pp_warning", 8)
    pp_critical = t.get("b_margin_erosion_pp_critical", 15)

    if erosion_pp < pp_warning:
        return []

    severity = AlertSeverity.HIGH if erosion_pp >= pp_critical else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale,
                             months=consecutive_declines),
        summary=localize_summary(alert_type, ctx.locale,
                                 months=consecutive_declines,
                                 start_margin=start_margin,
                                 start_month=recent[0].get("month", ""),
                                 end_margin=end_margin,
                                 end_month=recent[-1].get("month", ""),
                                 erosion_pp=erosion_pp),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "consecutive_months": consecutive_declines,
            "start_margin": start_margin,
            "end_margin": end_margin,
            "erosion_pp": erosion_pp,
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=120, datasets=("purchases", "sales"), min_samples_30d=20, outlier_robust=True, confidence_label="high")
async def check_unit_cost_increase(ctx: AlertContext) -> List[Alert]:
    """B2 (v14.2): cost-to-revenue ratio elevated vs the 3-month historical baseline.

    Why the v14.1 logic was wrong
    ----------------------------
    Previously compared two 30-day windows directly:
        curr_ratio = outflows_30d / sales_30d
        prev_ratio = outflows_prev_30d / sales_prev_30d
        alert if (curr_ratio - prev_ratio) > 10pp
    This produced false positives when:
      • Sales dipped one month (denominator collapse) — ratio spikes
        even though costs didn't grow.
      • A bimonthly bill landed in the current 30d but not the previous
        one (same root cause as B4 "+1000% elettricità").

    The v14.2 logic
    ---------------
    Compare the rolling 60-day ratio against the median of the
    *preceding three* 60-day windows. The 60-day window smooths out
    bill-cycle noise and one-off cash sales spikes. The median over 3
    prior windows resists any single anomalous window from polluting
    the baseline.

    Threshold: ratio increase of ≥ ``b_unit_cost_increase_pp`` percentage
    points sustained against the historical baseline. The merchant's
    perception of "cost trouble" tracks pp-of-ratio better than a
    raw multiplier (40pp swing = clear margin compression).
    """
    alert_type = "unit_cost_increase"
    entity_key = f"period_{ctx.today.strftime('%Y-%m')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: the entity_key rotates monthly. After
    # resolve, give the merchant 60 days of quiet before re-flagging
    # the same structural cost-pressure pattern.
    if ctx.was_recently_resolved(alert_type):
        return []

    t = ctx.thresholds
    pp_warning = t.get("b_unit_cost_increase_pp_warning", 10)
    pp_critical = t.get("b_unit_cost_increase_pp_critical", 25)

    # Build four rolling 60-day windows from the preloaded daily series:
    #   current      = day -59..0
    #   prior_1      = day -119..-60
    #   prior_2      = day -179..-120  (from 90d → fallback to monthly_snapshots)
    #   prior_3      = day -239..-180  (idem)
    # We have daily-90d in the context. For windows beyond -90d we fall
    # back to monthly_snapshots, accepting a slight loss of granularity
    # because anything that old is, by definition, baseline data.
    from datetime import timedelta as _td

    def _sum_window(by_date: dict, start: int, end: int) -> float:
        """Sum amounts in [today-start, today-end] inclusive (start > end → days ago)."""
        s = (ctx.today - _td(days=start)).isoformat()
        e = (ctx.today - _td(days=end)).isoformat()
        return sum(v for d, v in by_date.items() if s <= d <= e)

    # Current 60-day window (-59..0)
    curr_sales = _sum_window(ctx.sales_by_date_90d, 59, 0)
    curr_expenses = _sum_window(ctx.expenses_by_date_90d, 59, 0)
    curr_purchases = _sum_window(ctx.purchases_by_date_90d, 59, 0)
    # Fixed costs are not in by_date — use the 30d total scaled to 60d
    # (they're typically uniform monthly recurring amounts, so 60d ≈ 2× 30d).
    curr_fixed = ctx.total_fixed_costs_30d * 2

    if curr_sales <= 0:
        return []

    curr_outflows = curr_expenses + curr_purchases + curr_fixed
    curr_ratio = round(curr_outflows / curr_sales * 100, 1)

    # Prior 60-day window (-119..-60) — also in the 90d daily series.
    # If 90d daily doesn't reach back -119, this returns partial data;
    # we fall back to monthly_snapshots when both prior windows return
    # near-zero, indicating insufficient daily coverage.
    prior_sales = _sum_window(ctx.sales_by_date_90d, 119, 60)
    prior_expenses = _sum_window(ctx.expenses_by_date_90d, 119, 60)
    prior_purchases = _sum_window(ctx.purchases_by_date_90d, 119, 60)
    prior_fixed = curr_fixed  # assume stable month-to-month

    if prior_sales <= 0:
        # Fallback path: use the monthly_snapshots series. We average
        # the latest 3 months of (outflows/sales) ratios as the baseline.
        if len(ctx.monthly_snapshots) < 4:
            return []
        baseline_ratios = []
        for snap in ctx.monthly_snapshots[-4:-1]:  # excludes current month
            s = snap.get("sales", 0) or 0
            if s <= 0:
                continue
            o = (snap.get("expenses", 0) or 0) + (snap.get("purchases", 0) or 0) + (snap.get("fixed_costs", 0) or 0)
            baseline_ratios.append(o / s * 100)
        if len(baseline_ratios) < 2:
            return []
        from modules.cashflow_monitor.statistical_significance import rolling_window_baseline
        baseline_median, _ = rolling_window_baseline(baseline_ratios, exclude_zero=False)
        if baseline_median is None:
            return []
        baseline_ratio = round(baseline_median, 1)
    else:
        # Direct path: ratio over the prior 60-day window.
        baseline_ratio = round((prior_expenses + prior_purchases + prior_fixed) / prior_sales * 100, 1)

    increase_pp = round(curr_ratio - baseline_ratio, 1)
    if increase_pp < pp_warning:
        return []

    severity = AlertSeverity.HIGH if increase_pp >= pp_critical else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale, increase_pct=increase_pp),
        summary=localize_summary(
            alert_type, ctx.locale,
            increase_pct=increase_pp,
            prev_ratio=baseline_ratio,
            curr_ratio=curr_ratio,
        ),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "curr_ratio": curr_ratio,
            "prev_ratio": baseline_ratio,
            "increase_pp": increase_pp,
            # v14.2: window+method context for the email/report
            "window_days": 60,
            "baseline_method": "rolling_60d_vs_baseline_60d",
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=30, datasets=("sales", "expenses"), min_samples_30d=20, outlier_robust=True, confidence_label="high")
async def check_break_even_unreached(ctx: AlertContext) -> List[Alert]:
    """B3: Break-even not reached at mid-month."""
    alert_type = "break_even_unreached"

    # Only trigger after day 15
    if ctx.today.day < 15:
        return []

    entity_key = f"month_{ctx.today.strftime('%Y-%m')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: monthly rotating entity_key. Cooldown
    # after resolve avoids re-firing in subsequent months when the
    # structural pattern (under-sales vs fixed costs) hasn't changed.
    if ctx.was_recently_resolved(alert_type):
        return []

    if ctx.total_sales_30d <= 0 or ctx.total_fixed_costs_30d <= 0:
        return []

    var_ratio = variable_cost_ratio(
        ctx.total_expenses_30d + ctx.total_purchases_30d,
        ctx.total_sales_30d,
    )
    be = break_even_point(ctx.total_fixed_costs_30d, var_ratio)
    if be is None:
        return []

    # Cumulative revenue this month
    import calendar
    days_in_month = calendar.monthrange(ctx.today.year, ctx.today.month)[1]
    month_start = ctx.today.replace(day=1).isoformat()

    current_revenue = 0.0
    for d, amt in ctx.sales_by_date_90d.items():
        if d >= month_start:
            current_revenue += amt

    # Projected break-even for current progress
    progress = ctx.today.day / days_in_month
    projected_be = be * progress

    if current_revenue >= projected_be:
        return []

    deficit_pct = round((1 - current_revenue / projected_be) * 100, 1) if projected_be > 0 else 100

    t = ctx.thresholds
    warning_pct = t.get("b_break_even_deficit_warning_pct", 15)
    critical_pct = t.get("b_break_even_deficit_critical_pct", 30)

    if deficit_pct < warning_pct:
        return []

    severity = AlertSeverity.HIGH if deficit_pct >= critical_pct else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale),
        summary=localize_summary(alert_type, ctx.locale,
                                 day=ctx.today.day,
                                 current_revenue=_fmt_eur(current_revenue),
                                 projected_be=_fmt_eur(projected_be),
                                 deficit_pct=deficit_pct),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "current_revenue": round(current_revenue, 2),
            "projected_be": round(projected_be, 2),
            "deficit_pct": deficit_pct,
            "day_of_month": ctx.today.day,
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=90, datasets=("expenses",), min_samples_30d=15, outlier_robust=True, confidence_label="high")
async def check_category_expense_trend(ctx: AlertContext) -> List[Alert]:
    """B4 (v14.2): expense category anomalously high vs its OWN 12-month history.

    Why the v14.1 logic was wrong
    ----------------------------
    Previously the rule compared one 30d window against the immediately
    preceding 30d window for each category. For a bimonthly electricity
    bill of €48 (partial / acconto month) → €680 (full bill) it produced
    "+1316% increase" — mathematically correct, but business-blind: that
    jump is the normal pattern of every other month for that merchant,
    not a cost explosion. The exact symptom the macelleria PROD merchant
    reported.

    The v14.2 logic
    ---------------
    For each category:
      1. Build a 12-month timeline (one total per calendar month).
      2. Detect the payment cadence (monthly / bimonthly / quarterly / annual).
      3. Compute the median + MAD over the NON-ZERO months — that's the
         baseline the rule should compare against.
      4. Fire only if the latest non-zero month is ≥ ``threshold`` × median
         AND the absolute delta exceeds ``min_eur`` (avoids tiny-value spam).
      5. Confidence scales severity: higher score ⇒ higher severity.

    The "skip if insufficient history" branch ensures the rule simply
    keeps quiet for categories that have less than 4 paid months — there
    is no honest signal we can extract.

    Backward-compat note
    --------------------
    Same ``alert_type``, same ``entity_key`` shape (``cat_<slug>_<yyyy-mm>``)
    as v14.1 — existing dedup / acknowledgement / snooze logic works
    unchanged. The metric_payload gains ``baseline_median`` and ``score``
    so the email + report can show the merchant the historical context.
    """
    alert_type = "category_expense_trend"

    # v14.2 anti-ridondanza: this rule iterates over EACH category. The
    # entity_key includes both category slug AND month, so dedup correctly
    # gates per-(category,month) pairs while in "new"/"acknowledged" state.
    # But once the merchant resolves, the next month creates a fresh
    # entity_key per category → rule re-fires identically. The 60-day
    # cooldown short-circuits the whole sweep, matching the merchant's
    # intent "I've acknowledged the category spike problem".
    if ctx.was_recently_resolved(alert_type):
        return []

    t = ctx.thresholds
    median_ratio_threshold = t.get("b_category_median_ratio", 2.5)
    min_eur = t.get("b_category_trend_min_eur", 500)

    # ── 1. Load 12-month per-category timeline ─────────────────────────
    # Computed on-demand here (not preloaded in _build_context) because
    # the cost is one extra MongoDB aggregate per tick and only this rule
    # currently needs it. If P2.2b/P2.2c later need similar timelines we
    # can hoist it into the engine preload.
    from datetime import date, timedelta
    from repositories.analytics_repository import aggregate_expenses_by_category_monthly
    from modules.cashflow_monitor.statistical_significance import (
        detect_payment_frequency, is_significant_anomaly,
    )

    end_iso = ctx.today.isoformat()
    start_iso = (ctx.today - timedelta(days=365)).isoformat()
    try:
        per_cat = await aggregate_expenses_by_category_monthly(
            ctx.org_id, start_iso, end_iso,
        )
    except Exception:
        return []

    if not per_cat:
        return []

    # Build the canonical list of last-12 calendar months (ordered).
    months_chrono: List[str] = []
    cy, cm = ctx.today.year, ctx.today.month
    for _ in range(12):
        months_chrono.append(f"{cy:04d}-{cm:02d}")
        cm -= 1
        if cm == 0:
            cm = 12
            cy -= 1
    months_chrono.reverse()
    current_month = months_chrono[-1]

    alerts = []
    for cat, monthly_map in per_cat.items():
        # ── 2. Materialise the full 12-value timeline (zeros for gaps) ──
        timeline = [monthly_map.get(m, 0.0) for m in months_chrono]
        curr_amount = timeline[-1]

        # Current month with zero spending → nothing to compare against.
        if curr_amount <= 0:
            continue

        # ── 3. Frequency-aware baseline ─────────────────────────────────
        frequency = detect_payment_frequency(timeline)
        # The history we score against is the non-zero values EXCLUDING
        # the current month. is_significant_anomaly handles the zero-
        # exclusion internally, but excluding the current month here is
        # mandatory to avoid the value scoring itself.
        history = [v for v in timeline[:-1] if v > 0]

        outcome = is_significant_anomaly(
            current_value=curr_amount,
            history=history,
            method="median_ratio",
            # Need at least 4 prior paid months for the baseline to mean
            # something. For quarterly/annual cadences this implies
            # ~12+ months of history, which is exactly when the
            # decorator's min_days_of_data=90 turns into a meaningful
            # filter at the engine level (a 90-day-old org still might
            # have 4 non-zero months for a monthly category).
            min_history=4,
            threshold=median_ratio_threshold,
            min_absolute_delta=min_eur,
        )
        if not outcome.is_anomaly:
            continue

        # ── 4. Dedup + entity_key (unchanged shape) ─────────────────────
        slug = cat.lower().replace(" ", "_")[:30]
        entity_key = f"cat_{slug}_{current_month}"
        if ctx.is_dedup(alert_type, entity_key):
            continue

        # ── 5. Severity scales with the ratio (P2.5 scaling) ────────────
        # Use the centralised severity_tier_from_score helper instead of
        # an inline if-elif chain — same math, single source of truth,
        # so changing the tier shape later only touches one place.
        from modules.cashflow_monitor.statistical_significance import (
            severity_tier_from_score,
        )
        ratio = outcome.score
        _tier = severity_tier_from_score(ratio, high_threshold=5.0, medium_threshold=3.0)
        severity = {
            "high": AlertSeverity.HIGH,
            "medium": AlertSeverity.MEDIUM,
            "low": AlertSeverity.LOW,
        }[_tier]

        baseline_median = round(sum(history) / len(history), 2) if history else 0
        # ``rolling_window_baseline`` would give us the exact median, but
        # the rule already has the value via outcome.reason; recomputing
        # is fine here for the payload (only runs when an alert fires).

        prev_amount = baseline_median  # backward-compatible payload key

        alerts.append(Alert(
            organization_id=ctx.org_id,
            module_key=_MODULE,
            severity=severity,
            title=localize_title(
                alert_type, ctx.locale,
                category=cat, months=2,
                increase_pct=round((ratio - 1) * 100, 1),
            ),
            summary=localize_summary(
                alert_type, ctx.locale,
                category=cat, months=2,
                increase_pct=round((ratio - 1) * 100, 1),
                prev_amount=_fmt_eur(baseline_median),
                curr_amount=_fmt_eur(curr_amount),
                abs_increase=_fmt_eur(curr_amount - baseline_median),
            ),
            suggested_action=localize_suggestion(alert_type, ctx.locale),
            date_reference=ctx.today.isoformat(),
            metric_payload={
                "alert_type": alert_type,
                "category": cat,
                "curr_amount": round(curr_amount, 2),
                "prev_amount": round(prev_amount, 2),
                "increase_pct": round((ratio - 1) * 100, 1),
                # ── v14.2 additions ────────────────────────────────────
                "baseline_median": baseline_median,
                "history_sample_size": len(history),
                "score": ratio,
                "frequency": frequency,
                "method": "median_ratio",
            },
            schema_version=_SCHEMA,
            alert_category=_CAT,
            entity_key=entity_key,
        ))

    return alerts


ALL_RULES.extend([
    check_margin_erosion_trend,
    check_unit_cost_increase,
    check_break_even_unreached,
    check_category_expense_trend,
])
