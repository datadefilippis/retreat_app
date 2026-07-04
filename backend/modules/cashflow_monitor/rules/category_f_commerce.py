"""
Category F — Commerce Operations Alerts (v13.0)

Monitors order lifecycle, fulfillment, payments, events, and rental utilization.
Alerts admin to operational issues with financial impact context.

Quality standard: matches Categories A-E with:
- Financial impact quantified in every alert
- Conditional severity based on value + time thresholds
- Rich metric_payload for AI analysis
- Proper auto-resolve via entity_key patterns
"""

from typing import List
from models.alert import Alert, AlertSeverity
from modules.cashflow_monitor.rules import ALL_RULES, AlertContext, _fmt_eur
from modules.cashflow_monitor.data_quality import requires_data
from modules.cashflow_monitor.alert_i18n import localize_title, localize_summary, localize_suggestion


@requires_data(min_days_of_data=7, datasets=(), confidence_label="high")
async def check_order_backlog(ctx: AlertContext) -> List[Alert]:
    """F1: Draft orders accumulating beyond threshold — revenue at risk."""
    alert_type = "order_backlog"
    entity_key = f"week_{ctx.today.strftime('%Y-W%V')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []

    t = ctx.thresholds
    threshold_count = t.get("f_order_backlog_count", 5)

    if ctx.orders_draft_older_than_3d < threshold_count:
        return []

    value = ctx.orders_draft_total_value
    severity = AlertSeverity.HIGH if value > 1000 else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key="cashflow_monitor",
        severity=severity,
        title=localize_title(alert_type, ctx.locale, count=ctx.orders_draft_older_than_3d),
        summary=localize_summary(alert_type, ctx.locale,
                                 count=ctx.orders_draft_older_than_3d, total=ctx.orders_draft_count),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "draft_count": ctx.orders_draft_count,
            "draft_older_than_3d": ctx.orders_draft_older_than_3d,
            "total_value_blocked": value,
            "revenue_impact": f"{_fmt_eur(value)} di ricavo potenziale bloccato in bozze",
        },
        schema_version="3.0",
        alert_category="F",
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=7, datasets=(), confidence_label="high")
async def check_fulfillment_delay(ctx: AlertContext) -> List[Alert]:
    """F2: Aggregated fulfillment delays — individual alerts only for critical cases."""
    alert_type = "fulfillment_delay"
    alerts = []

    if not ctx.fulfillment_delays:
        return []

    # Critical delays (>14 days) get individual alerts
    critical = [d for d in ctx.fulfillment_delays if d["days_pending"] >= 14]
    for delay in critical:
        entity_key = f"order_{delay['order_id']}"
        if ctx.is_dedup(alert_type, entity_key):
            continue
        alerts.append(Alert(
            organization_id=ctx.org_id,
            module_key="cashflow_monitor",
            severity=AlertSeverity.HIGH,
            title=localize_title(alert_type, ctx.locale,
                                 order=delay.get("order_number", "?"), days=delay["days_pending"]),
            summary=localize_summary(alert_type, ctx.locale,
                                     order=delay.get("order_number", "?"),
                                     customer=delay.get("customer_name", ""),
                                     days=delay["days_pending"]),
            suggested_action=localize_suggestion(alert_type, ctx.locale),
            date_reference=ctx.today.isoformat(),
            metric_payload={
                "alert_type": alert_type,
                "order_id": delay["order_id"],
                "order_number": delay.get("order_number"),
                "days_pending": delay["days_pending"],
                "order_value": delay.get("order_value", 0),
            },
            schema_version="3.0",
            alert_category="F",
            entity_key=entity_key,
        ))

    # Non-critical delays (7-14 days) get single aggregated alert
    non_critical = [d for d in ctx.fulfillment_delays if d["days_pending"] < 14]
    if non_critical:
        agg_key = f"fulfillment_batch_week_{ctx.today.strftime('%Y-W%V')}"
        if not ctx.is_dedup("fulfillment_delay_batch", agg_key):
            total_val = round(sum(d.get("order_value", 0) for d in non_critical), 2)
            severity = AlertSeverity.HIGH if total_val > 500 else AlertSeverity.MEDIUM
            alerts.append(Alert(
                organization_id=ctx.org_id,
                module_key="cashflow_monitor",
                severity=severity,
                title=localize_title("fulfillment_delay", ctx.locale,
                                     order=f"{len(non_critical)} ordini", days=7),
                summary=f"{len(non_critical)} ordini in attesa di evasione da 7+ giorni per un valore totale di {_fmt_eur(total_val)}.",
                suggested_action=localize_suggestion("fulfillment_delay", ctx.locale),
                date_reference=ctx.today.isoformat(),
                metric_payload={
                    "alert_type": "fulfillment_delay_batch",
                    "delay_count": len(non_critical),
                    "total_value": total_val,
                    "orders": [{"order_number": d.get("order_number"), "days": d["days_pending"]} for d in non_critical[:5]],
                },
                schema_version="3.0",
                alert_category="F",
                entity_key=agg_key,
            ))

    return alerts


@requires_data(min_days_of_data=0, datasets=(), confidence_label="high")
async def check_payment_limbo(ctx: AlertContext) -> List[Alert]:
    """F3: Payment collected but order not confirmed — always critical."""
    alert_type = "payment_limbo"
    alerts = []

    for limbo in ctx.payment_limbo_orders:
        entity_key = f"order_{limbo['order_id']}"
        if ctx.is_dedup(alert_type, entity_key):
            continue

        alerts.append(Alert(
            organization_id=ctx.org_id,
            module_key="cashflow_monitor",
            severity=AlertSeverity.HIGH,
            title=localize_title(alert_type, ctx.locale,
                                 order=limbo.get("order_number", "?"),
                                 amount=_fmt_eur(limbo["amount"])),
            summary=localize_summary(alert_type, ctx.locale,
                                     order=limbo.get("order_number", "?"),
                                     amount=_fmt_eur(limbo["amount"]),
                                     hours=limbo["hours_since"]),
            suggested_action=localize_suggestion(alert_type, ctx.locale),
            date_reference=ctx.today.isoformat(),
            metric_payload={
                "alert_type": alert_type,
                "order_id": limbo["order_id"],
                "amount": limbo["amount"],
                "hours_since": limbo["hours_since"],
                "total_limbo_amount": ctx.payment_limbo_total,
                "limbo_count": len(ctx.payment_limbo_orders),
            },
            schema_version="3.0",
            alert_category="F",
            entity_key=entity_key,
        ))

    return alerts


@requires_data(min_days_of_data=0, datasets=(), confidence_label="medium")
async def check_event_low_fill(ctx: AlertContext) -> List[Alert]:
    """F4: Upcoming events with low fill rate — revenue opportunity at risk."""
    alert_type = "event_low_fill"
    alerts = []

    t = ctx.thresholds
    fill_threshold = t.get("f_event_fill_warning_pct", 30)

    for evt in ctx.events_upcoming_3d:
        if evt["fill_rate_pct"] >= fill_threshold:
            continue

        entity_key = f"occ_{evt['occ_id']}"
        if ctx.is_dedup(alert_type, entity_key):
            continue

        remaining = evt["capacity"] - evt["booked"]
        severity = AlertSeverity.HIGH if remaining > 10 else AlertSeverity.MEDIUM

        alerts.append(Alert(
            organization_id=ctx.org_id,
            module_key="cashflow_monitor",
            severity=severity,
            title=localize_title(alert_type, ctx.locale,
                                 name=evt["name"], fill=evt["fill_rate_pct"]),
            summary=localize_summary(alert_type, ctx.locale,
                                     name=evt["name"], date=evt["date"],
                                     booked=evt["booked"], capacity=evt["capacity"],
                                     fill=evt["fill_rate_pct"]),
            suggested_action=localize_suggestion(alert_type, ctx.locale),
            date_reference=evt["date"],
            metric_payload={
                "alert_type": alert_type,
                "occurrence_id": evt["occ_id"],
                "fill_rate_pct": evt["fill_rate_pct"],
                "booked": evt["booked"],
                "capacity": evt["capacity"],
                "remaining_seats": remaining,
            },
            schema_version="3.0",
            alert_category="F",
            entity_key=entity_key,
        ))

    return alerts


@requires_data(min_days_of_data=30, datasets=(), confidence_label="medium")
async def check_rental_idle(ctx: AlertContext) -> List[Alert]:
    """F5: Rental products with zero utilization — monthly entity_key for auto-expire."""
    alert_type = "rental_idle"
    alerts = []

    for prod in ctx.rental_products_idle:
        # Monthly entity_key: auto-expires at month boundary, prevents daily repetition
        entity_key = f"product_{prod['product_id']}_month_{ctx.today.strftime('%Y-%m')}"
        if ctx.is_dedup(alert_type, entity_key):
            continue

        alerts.append(Alert(
            organization_id=ctx.org_id,
            module_key="cashflow_monitor",
            severity=AlertSeverity.LOW,
            title=localize_title(alert_type, ctx.locale, name=prod["name"]),
            summary=localize_summary(alert_type, ctx.locale, name=prod["name"]),
            suggested_action=localize_suggestion(alert_type, ctx.locale),
            date_reference=ctx.today.isoformat(),
            metric_payload={
                "alert_type": alert_type,
                "product_id": prod["product_id"],
                "product_name": prod["name"],
                "idle_period": "30 giorni",
            },
            schema_version="3.0",
            alert_category="F",
            entity_key=entity_key,
        ))

    return alerts


@requires_data(min_days_of_data=14, datasets=(), confidence_label="medium")
async def check_cancellation_spike(ctx: AlertContext) -> List[Alert]:
    """F6: Cancellation rate spike with financial impact."""
    alert_type = "cancellation_spike"
    entity_key = f"week_{ctx.today.strftime('%Y-W%V')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []

    if ctx.orders_total_7d < 5:
        return []

    t = ctx.thresholds
    threshold_pct = t.get("f_cancellation_spike_pct", 20)

    rate = round(ctx.orders_cancelled_7d / ctx.orders_total_7d * 100, 1)
    if rate < threshold_pct:
        return []

    value = ctx.orders_cancelled_value_7d
    severity = AlertSeverity.HIGH if rate > 30 or value > 1000 else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key="cashflow_monitor",
        severity=severity,
        title=localize_title(alert_type, ctx.locale, rate=rate),
        summary=localize_summary(alert_type, ctx.locale,
                                 rate=rate, cancelled=ctx.orders_cancelled_7d,
                                 total=ctx.orders_total_7d),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "cancellation_rate_pct": rate,
            "cancelled_7d": ctx.orders_cancelled_7d,
            "cancelled_value": value,
            "total_7d": ctx.orders_total_7d,
            "revenue_lost": f"{_fmt_eur(value)} di ricavo perso per cancellazioni",
        },
        schema_version="3.0",
        alert_category="F",
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=0, datasets=(), confidence_label="high")
async def check_low_stock(ctx: AlertContext) -> List[Alert]:
    """F7: Products with stock_quantity at or near zero."""
    alert_type = "low_stock"
    alerts = []

    for prod in ctx.low_stock_products:
        entity_key = f"product_{prod['product_id']}_stock"
        if ctx.is_dedup(alert_type, entity_key):
            continue

        stock = prod.get("stock_quantity", 0)
        severity = AlertSeverity.HIGH if stock <= 0 else AlertSeverity.MEDIUM

        alerts.append(Alert(
            organization_id=ctx.org_id,
            module_key="cashflow_monitor",
            severity=severity,
            title=localize_title(alert_type, ctx.locale, name=prod["name"], stock=stock),
            summary=localize_summary(alert_type, ctx.locale, name=prod["name"], stock=stock),
            suggested_action=localize_suggestion(alert_type, ctx.locale),
            date_reference=ctx.today.isoformat(),
            metric_payload={
                "alert_type": alert_type,
                "product_id": prod["product_id"],
                "product_name": prod["name"],
                "stock_quantity": stock,
            },
            schema_version="3.0",
            alert_category="F",
            entity_key=entity_key,
        ))

    return alerts


# ── Register all Category F rules ─────────────────────────────────────────
ALL_RULES.extend([
    check_order_backlog,
    check_fulfillment_delay,
    check_payment_limbo,
    check_event_low_fill,
    check_rental_idle,
    check_cancellation_spike,
    check_low_stock,
])
