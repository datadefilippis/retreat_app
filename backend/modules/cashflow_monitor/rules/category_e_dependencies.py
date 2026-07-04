"""
Category E — Dependencies & Operational Risks

Rules:
  E1: supplier_concentration  — single supplier dominates purchases
  E2: dominant_product         — single category dominates revenue
  E3: fixed_cost_ratio_high    — fixed costs too large relative to revenue
"""

from typing import List
from models import Alert, AlertSeverity
from modules.cashflow_monitor.alert_i18n import (
    localize_title, localize_summary, localize_suggestion,
)
from modules.cashflow_monitor.kpi_formulas import fixed_cost_ratio as calc_fcr
from modules.cashflow_monitor.data_quality import requires_data
from . import AlertContext, _fmt_eur, ALL_RULES, humanize_entity_name, cap_share_pct

_SCHEMA = "3.0"
_MODULE = "cashflow_monitor"
_CAT = "E"


@requires_data(min_days_of_data=30, datasets=("purchases",), min_samples_30d=10, outlier_robust=False, confidence_label="high")
async def check_supplier_concentration(ctx: AlertContext) -> List[Alert]:
    """E1: Single supplier dominates purchases."""
    alert_type = "supplier_concentration"

    # v14.2 anti-ridondanza: even though entity_key is supplier-stable
    # (not date-rotating), once the merchant resolves the alert v14.1
    # would re-fire on the next run because resolved alerts are not in
    # the dedup set. Cooldown enforces the merchant's "I know" signal.
    if ctx.was_recently_resolved(alert_type):
        return []

    if not ctx.suppliers_by_amount or ctx.total_purchases_30d <= 0:
        return []

    # Smart suppression: if org has <= 2 suppliers, concentration is structural
    # (inevitable for micro-businesses), not an actionable risk.
    if len(ctx.suppliers_by_amount) <= 2:
        return []

    top = ctx.suppliers_by_amount[0]
    amount = top.get("total", 0.0)
    pct = round(amount / ctx.total_purchases_30d * 100, 1) if ctx.total_purchases_30d > 0 else 0
    pct = cap_share_pct(pct)  # v14.2 (P2.4d): supplier share ≤ 100%
    # v14.2 (P2.4c): defensive UUID-shape cleanup. If supplier_name was
    # imported as a UUID (rare but seen in PROD imports), substitute
    # a friendly fallback so the alert summary stays readable.
    supplier = humanize_entity_name(
        top.get("_id") or top.get("supplier"),
        fallback="Fornitore sconosciuto",
    )

    t = ctx.thresholds
    warning_pct = t.get("e_supplier_conc_warning_pct", 40)
    critical_pct = t.get("e_supplier_conc_critical_pct", 60)

    if pct < warning_pct:
        return []

    slug = supplier.lower().replace(" ", "_")[:50]
    entity_key = f"supplier_{slug}"
    if ctx.is_dedup(alert_type, entity_key):
        return []

    severity = AlertSeverity.HIGH if pct >= critical_pct else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale,
                             pct=round(pct, 0), supplier=supplier),
        summary=localize_summary(alert_type, ctx.locale,
                                 pct=round(pct, 0), supplier=supplier,
                                 amount=_fmt_eur(amount)),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "supplier": supplier,
            "pct": pct,
            "amount": round(amount, 2),
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=30, datasets=("sales",), min_samples_30d=15, outlier_robust=False, confidence_label="medium")
async def check_dominant_product(ctx: AlertContext) -> List[Alert]:
    """E2: Single product/category dominates revenue."""
    alert_type = "dominant_product"

    # v14.2 anti-ridondanza: stable per-product entity_key, same
    # reasoning as E1 — resolved alerts drop out of dedup so without
    # cooldown the rule re-fires identically next run.
    if ctx.was_recently_resolved(alert_type):
        return []

    if not ctx.sales_by_category or ctx.total_sales_30d <= 0:
        return []

    # Smart suppression: if org has <= 2 categories, concentration is structural
    # (inevitable for mono-category businesses like butchers, bakeries).
    if len(ctx.sales_by_category) <= 2:
        return []

    top = ctx.sales_by_category[0]
    amount = top.get("total", 0.0)
    pct = round(amount / ctx.total_sales_30d * 100, 1) if ctx.total_sales_30d > 0 else 0
    pct = cap_share_pct(pct)  # v14.2 (P2.4d): category share ≤ 100%
    # v14.2 (P2.4c): same UUID-defence as E1 — categories occasionally
    # leak as IDs in misconfigured imports.
    category = humanize_entity_name(
        top.get("_id") or top.get("category"),
        fallback="Categoria sconosciuta",
    )

    t = ctx.thresholds
    warning_pct = t.get("e_product_conc_warning_pct", 50)
    critical_pct = t.get("e_product_conc_critical_pct", 70)

    if pct < warning_pct:
        return []

    slug = category.lower().replace(" ", "_")[:30]
    entity_key = f"product_{slug}"
    if ctx.is_dedup(alert_type, entity_key):
        return []

    severity = AlertSeverity.HIGH if pct >= critical_pct else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale,
                             pct=round(pct, 0), category=category),
        summary=localize_summary(alert_type, ctx.locale,
                                 pct=round(pct, 0), category=category,
                                 amount=_fmt_eur(amount)),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "category": category,
            "pct": pct,
            "amount": round(amount, 2),
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


@requires_data(min_days_of_data=30, datasets=("sales", "fixed_costs"), min_samples_30d=20, outlier_robust=False, confidence_label="high")
async def check_fixed_cost_ratio_high(ctx: AlertContext) -> List[Alert]:
    """E3: Fixed costs too large relative to revenue."""
    alert_type = "fixed_cost_ratio_high"
    entity_key = f"fixed_{ctx.today.strftime('%Y-%m')}"
    if ctx.is_dedup(alert_type, entity_key):
        return []
    # v14.2 anti-ridondanza: monthly rotating entity_key — fixed cost
    # ratio is a slow-moving structural metric. After resolve, 60-day
    # cooldown matches the timescale on which the underlying cost
    # structure can plausibly change.
    if ctx.was_recently_resolved(alert_type):
        return []

    if ctx.total_sales_30d <= 0 or ctx.total_fixed_costs_30d <= 0:
        return []

    ratio = calc_fcr(ctx.total_fixed_costs_30d, ctx.total_sales_30d)
    if ratio is None:
        return []

    t = ctx.thresholds
    warning_pct = t.get("e_fixed_cost_ratio_warning_pct", 45)
    critical_pct = t.get("e_fixed_cost_ratio_critical_pct", 60)

    if ratio < warning_pct:
        return []

    severity = AlertSeverity.HIGH if ratio >= critical_pct else AlertSeverity.MEDIUM

    return [Alert(
        organization_id=ctx.org_id,
        module_key=_MODULE,
        severity=severity,
        title=localize_title(alert_type, ctx.locale, ratio=ratio),
        summary=localize_summary(alert_type, ctx.locale,
                                 ratio=ratio,
                                 fixed_costs=_fmt_eur(ctx.total_fixed_costs_30d),
                                 revenue=_fmt_eur(ctx.total_sales_30d)),
        suggested_action=localize_suggestion(alert_type, ctx.locale),
        date_reference=ctx.today.isoformat(),
        metric_payload={
            "alert_type": alert_type,
            "ratio": ratio,
            "fixed_costs": round(ctx.total_fixed_costs_30d, 2),
            "revenue": round(ctx.total_sales_30d, 2),
        },
        schema_version=_SCHEMA,
        alert_category=_CAT,
        entity_key=entity_key,
    )]


ALL_RULES.extend([
    check_supplier_concentration,
    check_dominant_product,
    check_fixed_cost_ratio_high,
])
