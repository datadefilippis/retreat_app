"""
Category C — Cash Cycle

Rules:
  C1: dso_worsening_trend  — DSO increasing over time
  C2: high_risk_invoice    — single large overdue invoice
  C3: dpo_dso_imbalance    — paying suppliers faster than collecting
"""

from typing import List
from models import Alert, AlertSeverity
from modules.cashflow_monitor.alert_i18n import (
    localize_title, localize_summary, localize_suggestion,
)
from modules.cashflow_monitor.kpi_formulas import (
    dso as calc_dso, dpo as calc_dpo, cash_conversion_gap,
)
from modules.cashflow_monitor.data_quality import requires_data
from . import AlertContext, _fmt_eur, ALL_RULES, humanize_entity_name

_SCHEMA = "3.0"
_MODULE = "cashflow_monitor"
_CAT = "C"


@requires_data(min_days_of_data=120, datasets=("sales",), min_samples_30d=20, outlier_robust=True, min_field_coverage={"due_dates": 30}, confidence_label="high")
async def check_dso_worsening_trend(ctx: AlertContext) -> List[Alert]:
    """C1 (v14.2): DSO elevated vs the 6-month historical baseline.

    Why the v14.1 logic was fragile
    -------------------------------
    Previously the rule compared ``current_dso`` against ``prev_snap.dso``
    (DSO from 3 months ago, a single value). That worked when DSO is
    stable but collapses in seasonal businesses:
      • One month with low sales (denominator) makes DSO spike.
      • DSO going from a low-season 50 to a normal-season 70 reads as
        "+40%" but is just seasonality.
      • Three-months-ago is itself one noisy sample.

    The v14.2 logic
    ---------------
    Compare current DSO against the *median* of the last 6 monthly DSO
    values (excluding current month). Median is robust to one seasonal
    spike — a 3-of-6 majority must agree before the baseline shifts.
    Significance test: current must be ≥ ``c_dso_median_ratio_threshold``
    (default 1.5×) AND absolute value above ``c_dso_min_days`` (already
    filtered out).

    This is the same robust-baseline idea used by B4 (median over
    historical non-zero values). We import the same helpers for
    consistency — one statistical-significance module, multiple consumers.
    """
    alert_type = "dso_worsening_trend"
    entity_key = f"trend_{ctx.today.strftime('%Y-%m')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: monthly rotating entity_key — without
    # cooldown the rule re-fires every new month after resolve.
    if ctx.was_recently_resolved(alert_type):
        return []

    # Need at least 6 historical months + current month
    if len(ctx.monthly_snapshots) < 7:
        return []

    current_snap = ctx.monthly_snapshots[-1]
    current_sales = current_snap.get("sales", 0)
    if current_sales <= 0:
        return []

    current_dso = calc_dso(ctx.open_receivables, current_sales, 30)
    if current_dso is None:
        return []

    t = ctx.thresholds
    min_days = t.get("c_dso_min_days", 30)
    median_ratio_threshold = t.get("c_dso_median_ratio_threshold", 1.5)

    # Absolute floor: DSO < 30 days is healthy regardless of trend.
    if current_dso < min_days:
        return []

    # Build the baseline from the previous 6 monthly snapshots' DSO.
    # Skip values where the snapshot couldn't compute DSO (e.g. zero sales).
    history_dsos = []
    for snap in ctx.monthly_snapshots[-7:-1]:
        v = snap.get("dso")
        if v is not None and v > 0:
            history_dsos.append(v)

    if len(history_dsos) < 4:
        # Not enough non-zero historical months to anchor a baseline.
        return []

    from modules.cashflow_monitor.statistical_significance import is_significant_anomaly

    outcome = is_significant_anomaly(
        current_value=current_dso,
        history=history_dsos,
        method="median_ratio",
        min_history=4,
        threshold=median_ratio_threshold,
        # Min absolute delta = 10 days: a ±10 day DSO drift on top of
        # the 30-day floor is the minimum business-meaningful swing.
        min_absolute_delta=10,
    )
    if not outcome.is_anomaly:
        return []

    baseline_median = round(sum(sorted(history_dsos)[len(history_dsos)//2:len(history_dsos)//2+1][0]
                                if len(history_dsos) else 0), 1)
    # Recompute the median cleanly (the score gave us the ratio, not the
    # baseline value, and the email summary wants the actual day count).
    sorted_h = sorted(history_dsos)
    n = len(sorted_h)
    baseline_dso = sorted_h[n // 2] if n % 2 else (sorted_h[n // 2 - 1] + sorted_h[n // 2]) / 2
    baseline_dso = round(baseline_dso, 1)

    # Severity from the ratio (P2.5 scaling) — uses the centralised
    # severity_tier_from_score helper so the tier shape stays
    # consistent across all anomaly-driven rules. DSO thresholds are
    # tighter than B4's (2.5 vs 5.0) because the underlying baseline
    # is itself a count of days, not a money amount: a 2.5× DSO jump
    # is already drastic.
    from modules.cashflow_monitor.statistical_significance import (
        severity_tier_from_score,
    )
    _tier = severity_tier_from_score(outcome.score, high_threshold=2.5, medium_threshold=1.8)
    severity = {
        "high": AlertSeverity.HIGH,
        "medium": AlertSeverity.MEDIUM,
        "low": AlertSeverity.LOW,
    }[_tier]

    increase_pct = round((current_dso - baseline_dso) / baseline_dso * 100, 1) if baseline_dso > 0 else 0

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale, current_dso=current_dso),
        summary=localize_summary(
            alert_type, ctx.locale,
            current_dso=current_dso,
            prev_dso=baseline_dso,
            increase_pct=increase_pct,
        ),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "current_dso": current_dso,
            "prev_dso": baseline_dso,
            "increase_pct": increase_pct,
            # v14.2 additions: baseline transparency
            "baseline_median_dso": baseline_dso,
            "history_months_used": len(history_dsos),
            "score": outcome.score,
            "method": "median_ratio_over_6mo_history",
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=30, datasets=("sales",), min_samples_30d=10, outlier_robust=False, min_field_coverage={"due_dates": 30}, confidence_label="high")
async def check_high_risk_invoice(ctx: AlertContext) -> List[Alert]:
    """C2: Single invoice that is both large and overdue."""
    alert_type = "high_risk_invoice"

    # v14.2 anti-ridondanza: a different overdue invoice every month
    # would re-fire identically. The merchant's resolve says "I'm
    # managing the overdue-invoice problem actively"; give them 60
    # days before flagging fresh ones from the same alert_type.
    if ctx.was_recently_resolved(alert_type):
        return []

    if not ctx.overdue_invoices or ctx.total_sales_30d <= 0:
        return []

    t = ctx.thresholds
    revenue_pct_threshold = t.get("c_invoice_risk_revenue_pct", 30)
    overdue_days_threshold = t.get("c_invoice_risk_overdue_days", 30)

    monthly_revenue = ctx.total_sales_30d
    alerts = []

    for inv in ctx.overdue_invoices:
        amount = inv.get("amount", 0.0)
        overdue_days = inv.get("overdue_days", 0)
        # v14.2 (P2.4c): UUID-defence on the customer label so the
        # alert text never shows raw IDs.
        customer = humanize_entity_name(
            inv.get("customer"), fallback="Cliente sconosciuto",
        )

        if overdue_days < overdue_days_threshold:
            continue

        revenue_pct = round(amount / monthly_revenue * 100, 1) if monthly_revenue > 0 else 0
        if revenue_pct < revenue_pct_threshold:
            continue

        inv_ref = inv.get("id", inv.get("ref", customer))
        entity_key = f"invoice_{str(inv_ref).lower().replace(' ', '_')[:50]}"
        if ctx.is_dedup(alert_type, entity_key):
            continue

        alerts.append(Alert(
            organization_id=ctx.org_id,
            module_key=_MODULE,
            severity=AlertSeverity.HIGH,
            title=localize_title(alert_type, ctx.locale,
                                 amount=_fmt_eur(amount),
                                 overdue_days=overdue_days),
            summary=localize_summary(alert_type, ctx.locale,
                                     amount=_fmt_eur(amount),
                                     revenue_pct=revenue_pct,
                                     overdue_days=overdue_days,
                                     customer=customer),
            suggested_action=localize_suggestion(alert_type, ctx.locale),
            date_reference=ctx.today.isoformat(),
            metric_payload={
                "alert_type": alert_type,
                "amount": round(amount, 2),
                "overdue_days": overdue_days,
                "revenue_pct": revenue_pct,
                "customer": customer,
            },
            schema_version=_SCHEMA,
            alert_category=_CAT,
            entity_key=entity_key,
        ))

    return alerts[:3]  # Max 3 high-risk invoice alerts at once


@requires_data(min_days_of_data=30, datasets=("sales", "purchases"), min_samples_30d=20, outlier_robust=True, confidence_label="medium")
async def check_dpo_dso_imbalance(ctx: AlertContext) -> List[Alert]:
    """C3: Paying suppliers faster than collecting from customers."""
    alert_type = "dpo_dso_imbalance"
    entity_key = f"gap_{ctx.today.strftime('%Y-%m')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: monthly rotating entity_key — cooldown
    # respects the merchant's resolve as an "I know" signal.
    if ctx.was_recently_resolved(alert_type):
        return []

    dso_val = calc_dso(ctx.open_receivables, ctx.total_sales_30d, 30)
    dpo_val = calc_dpo(ctx.open_payables, ctx.total_purchases_30d, 30)
    gap = cash_conversion_gap(dso_val, dpo_val)

    if gap is None or gap <= 0:
        return []

    t = ctx.thresholds
    warning_days = t.get("c_ccc_gap_warning_days", 45)
    critical_days = t.get("c_ccc_gap_critical_days", 90)

    if gap < warning_days:
        return []

    severity = AlertSeverity.HIGH if gap >= critical_days else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale,
                             gap=gap, dso=dso_val or 0, dpo=dpo_val or 0),
        summary=localize_summary(alert_type, ctx.locale,
                                 gap=gap, dso=dso_val or 0, dpo=dpo_val or 0),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "dso": dso_val,
            "dpo": dpo_val,
            "gap": gap,
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


ALL_RULES.extend([
    check_dso_worsening_trend,
    check_high_risk_invoice,
    check_dpo_dso_imbalance,
])
