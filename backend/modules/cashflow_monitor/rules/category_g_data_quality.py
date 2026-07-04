"""
Category G — Data Quality Alerts (v14.0 / v14.1)

Monitors data completeness and consistency across modules.
Fires monthly (entity_key scoped to month) to avoid spam.

G1: Low customer_id coverage in sales records
G2: High percentage of products without cost_price (margins incalculable)
G3 (v14.1): System onboarding — too little history to run analytics

G3 design notes
---------------
Distinct from G1/G2 because it is the ONLY rule that fires for a brand-new
org. Its purpose is to inform the merchant that the silence elsewhere is
intentional ("we're not generating alerts because we don't have enough
data yet to be trustworthy") rather than a bug. Severity is info — it
never sends an email and never weights into the email_high_alerts batch.

The rule deliberately does NOT carry a @requires_data decorator: it
would create a chicken-and-egg situation (the rule that says "no data"
needs no data to fire). It reads ctx.data_quality directly because
this is the exact case the snapshot was designed to surface.
"""

from typing import List
from models.alert import Alert, AlertSeverity
from modules.cashflow_monitor.rules import ALL_RULES, AlertContext, _fmt_eur
from modules.cashflow_monitor.data_quality import requires_data


@requires_data(min_days_of_data=14, datasets=("sales",), confidence_label="medium")
async def check_low_customer_coverage(ctx: AlertContext) -> List[Alert]:
    """G1: customer_id coverage below threshold — customer analytics unreliable."""
    alert_type = "data_quality_customer_coverage"
    entity_key = f"month_{ctx.today.strftime('%Y-%m')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: data quality is a structural issue. Once
    # the merchant resolves, give them 60 days to fix the imports
    # before re-flagging the same coverage gap.
    if ctx.was_recently_resolved(alert_type):
        return []

    # Only fire if there are enough records to matter
    if ctx.total_sales_records < 50:
        return []

    threshold = ctx.thresholds.get("g_customer_coverage_pct", 30)
    if ctx.customer_id_coverage_pct >= threshold:
        return []

    severity = AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key="cashflow_monitor",
        severity=severity,
        title=f"Copertura clienti bassa: {ctx.customer_id_coverage_pct}%",
        summary=(
            f"Solo il {ctx.customer_id_coverage_pct}% dei record di vendita ha un cliente associato "
            f"(su {ctx.total_sales_records} record totali). "
            "L'analisi clienti, la segmentazione e il rischio churn non sono affidabili."
        ),
        suggested_action=(
            "Importare vendite con la colonna 'cliente' corrispondente ai clienti in anagrafica. "
            "Obiettivo: copertura superiore al 70% per analisi affidabili."
        ),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "coverage_pct": ctx.customer_id_coverage_pct,
            "total_records": ctx.total_sales_records,
            "threshold_pct": threshold,
        },
        schema_version="3.0",
        alert_category="G",
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=14, confidence_label="medium")
async def check_products_without_cost(ctx: AlertContext) -> List[Alert]:
    """G2: Too many products without cost_price — margins incalculable."""
    alert_type = "data_quality_products_no_cost"
    entity_key = f"month_{ctx.today.strftime('%Y-%m')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: same reasoning as G1 — structural issue
    # that needs merchant action; the cooldown respects that intent.
    if ctx.was_recently_resolved(alert_type):
        return []

    # Only fire if there are enough products
    if ctx.total_active_products < 5:
        return []

    threshold = ctx.thresholds.get("g_products_no_cost_pct", 50)
    if ctx.products_without_cost_pct < threshold:
        return []

    severity = AlertSeverity.LOW if ctx.products_without_cost_pct < 70 else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key="cashflow_monitor",
        severity=severity,
        title=f"Margini incompleti: {ctx.products_without_cost_pct}% prodotti senza costo",
        summary=(
            f"Il {ctx.products_without_cost_pct}% dei prodotti attivi non ha un costo impostato "
            f"({ctx.total_active_products} prodotti totali). "
            "I margini per questi prodotti non possono essere calcolati e l'analisi ABC "
            "potrebbe essere distorta."
        ),
        suggested_action=(
            "Aggiungere il costo unitario ai prodotti nell'area Catalogo Prodotti. "
            "Prioritizzare i prodotti con fatturato maggiore."
        ),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "no_cost_pct": ctx.products_without_cost_pct,
            "total_products": ctx.total_active_products,
            "threshold_pct": threshold,
        },
        schema_version="3.0",
        alert_category="G",
        entity_key=entity_key,
    )]


async def check_system_onboarding(ctx: AlertContext) -> List[Alert]:
    """G3 (v14.1): inform the merchant when the system is in onboarding.

    Fires once per (org, ISO-week) so the merchant sees a recurring
    reminder ~weekly until enough data is loaded — but never spams.

    Suppressed automatically once ``days_since_first_record >= 14``,
    because at that point general rules become eligible to fire on
    their own merits.
    """
    alert_type = "system_onboarding"
    # Weekly cadence so consecutive ticks within a week don't re-fire.
    year, week, _ = ctx.today.isocalendar()
    entity_key = f"week_{year}-W{week:02d}"
    if ctx.is_dedup(alert_type, entity_key):
        return []

    # No snapshot means we're in a legacy invocation path — skip the
    # rule rather than fire on incomplete information.
    if ctx.data_quality is None:
        return []

    snap = ctx.data_quality
    if not snap.is_org_onboarding(min_days=14):
        return []

    days = snap.days_since_first_record
    return [Alert(
        organization_id=ctx.org_id,
        module_key="cashflow_monitor",
        severity=AlertSeverity.LOW,
        title=f"Sistema in onboarding — analisi attiva tra {max(14 - days, 1)} giorni",
        summary=(
            f"Hai caricato {days} giorni di dati. Per emettere analisi affidabili "
            "(margini, trend, anomalie) il sistema attende almeno 14 giorni di "
            "storico. Continua a caricare dati per attivare il monitoraggio completo."
        ),
        suggested_action=(
            "Importa i dati di vendita, acquisti e costi fissi dei mesi precedenti "
            "tramite il modulo Dati > Importa. Anche solo lo storico degli ultimi "
            "30-60 giorni rende il sistema utile sin da subito."
        ),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "days_of_data": days,
            "threshold_days": 14,
        },
        schema_version="3.0",
        alert_category="G",
        entity_key=entity_key,
    )]


# ── Register all Category G rules ─────────────────────────────────────────
ALL_RULES.extend([
    check_low_customer_coverage,
    check_products_without_cost,
    check_system_onboarding,
])
