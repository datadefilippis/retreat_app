"""
Category A — Liquidity & Survival

Rules:
  A1: cash_runway_critical    — financial runway below threshold
  A2: persistent_negative_cashflow — too many negative days in window
  A3: month_closed_loss       — previous month ended in loss
  A4: revenue_concentration   — single customer dominates revenue
"""

from typing import List
from datetime import timedelta
from models import Alert, AlertSeverity
from modules.cashflow_monitor.alert_i18n import (
    localize_title, localize_summary, localize_suggestion,
)
from modules.cashflow_monitor.kpi_formulas import (
    operational_coverage_days, net_margin_pct,
)
from modules.cashflow_monitor.data_quality import requires_data
from . import AlertContext, _fmt_eur, ALL_RULES, humanize_entity_name, cap_share_pct

_SCHEMA = "3.0"
_MODULE = "cashflow_monitor"
_CAT = "A"


@requires_data(min_days_of_data=30, datasets=("sales", "expenses"), min_samples_30d=20, outlier_robust=True, confidence_label="high")
async def check_cash_runway_critical(ctx: AlertContext) -> List[Alert]:
    """A1: Alert when financial runway is dangerously short."""
    alert_type = "cash_runway_critical"
    entity_key = f"month_{ctx.today.strftime('%Y-%m')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: skip if merchant resolved this alert_type
    # within the last 60 days. The entity_key rotates every month so
    # without this cooldown the rule re-fires each new month after a
    # resolve, ignoring the merchant's "I know" signal.
    if ctx.was_recently_resolved(alert_type):
        return []

    total_sales = ctx.total_sales_30d
    variable_outflows = ctx.total_expenses_30d + ctx.total_purchases_30d
    total_outflows = variable_outflows + ctx.total_fixed_costs_30d
    net = total_sales - total_outflows

    days = operational_coverage_days(net, total_outflows, 30)
    if days is None:
        return []

    margin = net_margin_pct(net, total_sales)
    margin_str = f"{margin}%" if margin is not None else "N/A"

    t = ctx.thresholds
    critical_days = t.get("a_cash_runway_critical_days", 15)
    warning_days = t.get("a_cash_runway_warning_days", 30)

    if days <= critical_days:
        severity = AlertSeverity.HIGH
    elif days <= warning_days:
        severity = AlertSeverity.MEDIUM
    else:
        return []

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale, days=days),
        summary=localize_summary(alert_type, ctx.locale, days=days, margin=margin_str),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "coverage_days": days,
            "net_margin_pct": margin,
            "total_outflows": total_outflows,
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=21, datasets=("sales",), min_samples_30d=15, outlier_robust=True, confidence_label="high")
async def check_persistent_negative_cashflow(ctx: AlertContext) -> List[Alert]:
    """A2: Alert when too many days have negative cashflow in a window."""
    alert_type = "persistent_negative_cashflow"

    t = ctx.thresholds
    window_short = t.get("a_negative_window_short", 7)
    window_long = t.get("a_negative_window_long", 14)
    threshold_warning = t.get("a_negative_days_warning", 5)
    threshold_critical = t.get("a_negative_days_critical", 10)

    # Count negative days in the long window
    end = ctx.today
    start = end - timedelta(days=window_long - 1)

    neg_days = 0
    cumulative_loss = 0.0
    streak_start = None

    for i in range(window_long):
        d = (start + timedelta(days=i)).isoformat()
        sales = ctx.sales_by_date_90d.get(d, 0.0)
        expenses = ctx.expenses_by_date_90d.get(d, 0.0)
        purchases = ctx.purchases_by_date_90d.get(d, 0.0)
        daily_net = sales - expenses - purchases
        if daily_net < 0:
            neg_days += 1
            cumulative_loss += daily_net
            if streak_start is None:
                streak_start = d

    if neg_days < threshold_warning:
        return []

    entity_key = f"streak_{streak_start or ctx.today.isoformat()}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: a new streak naturally rotates the
    # entity_key. The 60-day cooldown gives the merchant time to act on
    # their previous resolution before being re-nagged about the same
    # class of problem.
    if ctx.was_recently_resolved(alert_type):
        return []

    severity = AlertSeverity.HIGH if neg_days >= threshold_critical else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale,
                             neg_days=neg_days, window=window_long),
        summary=localize_summary(alert_type, ctx.locale,
                                 neg_days=neg_days, window=window_long,
                                 cumulative_loss=_fmt_eur(abs(cumulative_loss))),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "negative_days": neg_days,
            "window_days": window_long,
            "cumulative_loss": round(cumulative_loss, 2),
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=30, datasets=("sales", "expenses"), min_samples_30d=20, outlier_robust=True, confidence_label="high")
async def check_month_closed_loss(ctx: AlertContext) -> List[Alert]:
    """A3: Alert when the previous month closed with a loss."""
    alert_type = "month_closed_loss"

    # Only check if we're past day 3 of the current month (data settling)
    if ctx.today.day < 3:
        return []

    if not ctx.monthly_snapshots:
        return []

    # Find last completed month
    current_month = ctx.today.strftime("%Y-%m")
    prev_months = [s for s in ctx.monthly_snapshots if s.get("month", "") < current_month]
    if not prev_months:
        return []

    last = prev_months[-1]
    month_label = last.get("month", "")
    revenue = last.get("sales", 0.0)
    outflows = (last.get("expenses", 0.0) + last.get("purchases", 0.0)
                + last.get("fixed_costs", 0.0))
    net = revenue - outflows

    if net >= 0:
        return []

    entity_key = f"month_{month_label}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: each new closed month rotates the
    # entity_key. After the merchant resolves a "loss month" alert
    # they explicitly acknowledged the issue — give them 60 days
    # before nagging again about subsequent loss months.
    if ctx.was_recently_resolved(alert_type):
        return []

    loss = abs(net)
    loss_pct = round(loss / revenue * 100, 1) if revenue > 0 else 100.0
    # v14.2 (P2.4b): "1000% dei ricavi" is gibberish — switch to a
    # "per €1 di ricavi, €X di costi" framing the merchant can parse.
    # cost_per_revenue = outflows / revenue, rounded to 1 decimal.
    cost_per_revenue = round(outflows / revenue, 1) if revenue > 0 else 0.0
    severe_narrative = loss_pct >= 100  # threshold where pct is meaningless

    t = ctx.thresholds
    minor_pct = t.get("a_month_loss_minor_pct", 10)

    severity = AlertSeverity.MEDIUM if loss_pct < minor_pct else AlertSeverity.HIGH

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale,
                             month=month_label, loss=_fmt_eur(loss)),
        summary=localize_summary(
            alert_type, ctx.locale,
            variant="severe" if severe_narrative else "",
            month=month_label, revenue=_fmt_eur(revenue),
            outflows=_fmt_eur(outflows), loss=_fmt_eur(loss),
            loss_pct=loss_pct,
            cost_per_revenue=cost_per_revenue,
        ),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "month": month_label,
            "revenue": round(revenue, 2),
            "outflows": round(outflows, 2),
            "net": round(net, 2),
            "loss_pct": loss_pct,
            "cost_per_revenue": cost_per_revenue,
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=30, datasets=("sales",), min_samples_30d=15, outlier_robust=False, confidence_label="medium")
async def check_revenue_concentration(ctx: AlertContext) -> List[Alert]:
    """A4: Alert when a single customer dominates revenue."""
    alert_type = "revenue_concentration"

    # v14.2 anti-ridondanza: cooldown the entire alert_type (not just
    # per-customer entity_key) — the merchant's resolve says "I know
    # we have concentration risk", which applies whether customer A
    # or customer B is the new top.
    if ctx.was_recently_resolved(alert_type):
        return []

    if not ctx.customers_by_revenue or ctx.total_sales_30d <= 0:
        return []

    # Smart suppression: if org has <= 3 customers total, concentration is structural
    if len(ctx.customers_by_revenue) <= 3:
        return []

    top = ctx.customers_by_revenue[0]
    pct = top.get("pct", 0.0)
    if not pct:
        rev = top.get("total_revenue", 0.0)
        pct = round(rev / ctx.total_sales_30d * 100, 1) if ctx.total_sales_30d > 0 else 0
    # v14.2 (P2.4d): defensive cap — a single customer's share cannot
    # exceed 100% of revenue but stale aggregates have produced 101%+
    # readings in the past. Keep the narrative mathematically sane.
    pct = cap_share_pct(pct)

    t = ctx.thresholds
    critical_pct = t.get("a_revenue_concentration_critical_pct", 60)
    warning_pct = t.get("a_revenue_concentration_warning_pct", 40)

    if pct < warning_pct:
        return []

    # v14.2 (P2.4c): aggregate_customers_by_revenue_period falls back
    # to customer_id when customer_name is null upstream. That UUID
    # then surfaces as "Cliente 7a4d-..." in the alert summary —
    # unparseable for the merchant. humanize_entity_name detects the
    # UUID shape and returns a localised "Sconosciuto" fallback.
    raw_name = top.get("customer_name") or top.get("_id") or "Unknown"
    customer_name = humanize_entity_name(raw_name, fallback="Cliente sconosciuto")
    customer_id = str(top.get("_id", top.get("customer_id", raw_name)))
    entity_key = f"customer_{customer_id.lower().replace(' ', '_')[:50]}"
    if ctx.is_dedup(alert_type, entity_key):
        return []

    severity = AlertSeverity.HIGH if pct >= critical_pct else AlertSeverity.MEDIUM
    amount = top.get("total_revenue", 0.0)

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale,
                             pct=round(pct, 0), customer=customer_name),
        summary=localize_summary(alert_type, ctx.locale,
                                 pct=round(pct, 0), customer=customer_name,
                                 amount=_fmt_eur(amount)),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "customer": customer_name,
            "pct": round(pct, 1),
            "amount": round(amount, 2),
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


# Register all rules
ALL_RULES.extend([
    check_cash_runway_critical,
    check_persistent_negative_cashflow,
    check_month_closed_loss,
    check_revenue_concentration,
])
