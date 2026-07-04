"""
Cashflow Monitor — overview builder.

Aggregates KPIs, chart series, category breakdowns, open alerts, and the
last AI insight for a requested period into a single composite dict.
Designed for GET /api/modules/cashflow_monitor/overview so the frontend
needs only one HTTP call to hydrate the entire module page.

Public interface:
    build_overview(org_id, period, start_date, end_date) -> Optional[dict]
        Returns the full overview dict, or None when there is no data for
        the organisation.  Never raises — any partial failure in a query
        produces a zero/empty value for that section.

All repository queries run concurrently via asyncio.gather() so latency
equals the slowest single query rather than the sum of all queries.

Response dict keys (all required by the consumer):
    module           dict   (module_key, module_name, is_available)
    period           dict   (label, start_date, end_date, days)
    data_availability dict  (has_data, min_date, max_date, days_of_data,
                             suggested_period)
    kpis             dict   (total_sales, total_expenses, net_cashflow,
                             fixed_costs_total, combined_expenses,
                             expense_ratio, burn_rate, avg_daily_sales,
                             avg_daily_expenses, sales_trend_pct,
                             expenses_trend_pct, period_days,
                             — v2.2 additions —
                             supplier_purchases, variable_outflows,
                             total_outflows, net_before_fixed,
                             net_after_fixed, purchase_ratio,
                             total_outflow_ratio)
    charts           dict   (daily_series: list of date/sales/expenses/
                             purchases/net_cashflow/cumulative)
    categories       dict   (top_sales, top_expenses — each a list of
                             {category, total, count, percentage})
    alerts           dict   (open_count, by_severity, recent)
    last_insight     dict|None
    status           dict   (level, color, label, primary_driver, message,
                             data_warnings) — v2.3 synthetic health status
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from repositories import analytics_repository, alert_repository, insight_repository
from modules.cashflow_monitor.status_builder import compute_status
from modules.cashflow_monitor.health_score import compute_health_score
from modules.cashflow_monitor.health_explanation import generate_health_explanation
from modules.cashflow_monitor import kpi_formulas


async def _count_with_payment_status(org_id: str, collection_type: str) -> int:
    """Count records with payment_status set. Non-blocking helper for gather."""
    try:
        if collection_type == "sales":
            from database import sales_records_collection as coll
        else:
            from database import purchase_records_collection as coll
        return await coll.count_documents({
            "organization_id": org_id,
            "payment_status": {"$exists": True, "$ne": None},
        })
    except Exception:
        return 0


async def build_overview(
    org_id: str,
    period: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    **kwargs,
) -> Optional[dict]:
    """Fetch all cashflow data and assemble the overview response.

    Returns a dict with keys: module, period, data_availability, kpis,
    charts, categories, alerts, last_insight.  Returns None when there
    is no sales or expense data for the organisation in the period.

    Accepts locale via **kwargs for locale-aware status text and health
    explanation.  Defaults to 'it' when not provided.
    """
    locale = kwargs.get("locale", "it")

    # Lazy import avoids circular-import risk at module load time
    from services.ai_analytics_service import _get_date_range

    start, end = _get_date_range(period, start_date, end_date)

    # Compute previous-period dates for trend comparison
    start_dt = datetime.strptime(start, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end, "%Y-%m-%d").date()
    period_days = (end_dt - start_dt).days + 1

    # Wave 14.CONSOLIDATE R3 — YTD detection.
    # ----------------------------------------
    # Pre-fix the "previous period" was always computed as "N days
    # immediately before the requested window". For most window
    # types (7d, 30d, 90d, Q1, Q2, custom 60d) that's the right
    # semantic. But for YTD (Jan 1 → today) it produces
    # Aug → Dec of the prior year — a 5-month chunk that has no
    # business meaning, and the chat AI happily reports trend
    # against it. The Wave 13 audit flagged this explicitly.
    #
    # We detect YTD by the canonical pattern (start = Jan 1 of the
    # requested year) and, when matched, redirect prev_period to
    # the SAME YTD WINDOW of the prior calendar year so the
    # comparison is "Jan-May 2026 vs Jan-May 2025" — a real
    # year-over-year YTD comparison.
    is_ytd_pattern = (start_dt.month == 1 and start_dt.day == 1)
    if is_ytd_pattern:
        # YTD prev_period = previous-year YTD window of the SAME shape
        prev_end_dt = end_dt.replace(year=end_dt.year - 1)
        prev_start_dt = start_dt.replace(year=start_dt.year - 1)
        period_semantic = "ytd"
    else:
        # Standard "immediately preceding N days" comparison
        prev_end_dt = start_dt - timedelta(days=1)
        prev_start_dt = prev_end_dt - timedelta(days=period_days - 1)
        period_semantic = "rolling"
    prev_start = prev_start_dt.isoformat()
    prev_end = prev_end_dt.isoformat()

    # Compute same-period-last-year dates for YoY comparison.
    # For YTD windows, YoY == prev_period (they collapse to the same
    # 12-months-ago window). We compute it anyway for downstream
    # uniformity, but the period_comparison block now correctly
    # describes the relation.
    yoy_start_dt = start_dt.replace(year=start_dt.year - 1)
    yoy_end_dt = end_dt.replace(year=end_dt.year - 1)
    yoy_start = yoy_start_dt.isoformat()
    yoy_end = yoy_end_dt.isoformat()

    # ── 18 parallel queries ────────────────────────────────────────────────
    (
        sales_by_date,
        expenses_by_date,
        prev_sales_by_date,
        prev_expenses_by_date,
        top_sales_cats,
        top_expense_cats,
        fixed_costs_total,
        date_range_info,
        all_alerts,
        last_insight_doc,
        purchases_by_date,       # v2.2: Bucket B — supplier purchases
        purchases_by_supplier,   # v2.4: Pareto fornitori
        open_receivables,        # v2.4: Scadenzario — crediti aperti
        open_payables,           # v2.4: Scadenzario — debiti aperti
        receivables_aging,       # v2.4: Scadenzario — aging crediti
        payables_aging,          # v2.4: Scadenzario — aging debiti
        upcoming_receivables,    # v2.4: Scadenzario — incassi attesi 60gg
        upcoming_payables,       # v2.4: Scadenzario — pagamenti attesi 60gg
        yoy_sales_by_date,       # v3.0: YoY comparison — same period last year
        yoy_expenses_by_date,    # v3.0: YoY comparison
        yoy_purchases_by_date,   # v3.0: YoY comparison
        purchases_by_product,    # Prodotto/Categoria Pareto
        purchases_by_category_macro,
        _sales_ps_count,         # Payment-status coverage counts (for CCG)
        _purchases_ps_count,
    ) = await asyncio.gather(
        analytics_repository.aggregate_sales_by_date(org_id, start, end),
        analytics_repository.aggregate_expenses_by_date(org_id, start, end),
        analytics_repository.aggregate_sales_by_date(org_id, prev_start, prev_end),
        analytics_repository.aggregate_expenses_by_date(org_id, prev_start, prev_end),
        analytics_repository.aggregate_sales_by_category(org_id, start, end),
        analytics_repository.aggregate_expenses_by_category(org_id, start, end),
        analytics_repository.aggregate_fixed_costs_total(org_id, start, end),
        analytics_repository.get_analytics_date_range(org_id),
        alert_repository.find_by_org(org_id, limit=100),
        insight_repository.find_latest(org_id, "cashflow_monitor"),
        analytics_repository.aggregate_purchases_by_date(org_id, start, end),  # v2.2
        analytics_repository.aggregate_purchases_by_supplier(org_id, start, end),  # v2.4
        analytics_repository.aggregate_open_receivables(org_id),               # v2.4
        analytics_repository.aggregate_open_payables(org_id),                  # v2.4
        analytics_repository.aggregate_receivables_by_aging(org_id),           # v2.4
        analytics_repository.aggregate_payables_by_aging(org_id),              # v2.4
        analytics_repository.aggregate_upcoming_receivables(org_id, 60),       # v2.4
        analytics_repository.aggregate_upcoming_payables(org_id, 60),          # v2.4
        analytics_repository.aggregate_sales_by_date(org_id, yoy_start, yoy_end),      # v3.0
        analytics_repository.aggregate_expenses_by_date(org_id, yoy_start, yoy_end),   # v3.0
        analytics_repository.aggregate_purchases_by_date(org_id, yoy_start, yoy_end),  # v3.0
        analytics_repository.aggregate_purchases_by_product(org_id, start, end),
        analytics_repository.aggregate_purchases_by_category_macro(org_id, start, end),
        _count_with_payment_status(org_id, "sales"),
        _count_with_payment_status(org_id, "purchases"),
    )

    # No data at all → caller returns 404
    if not sales_by_date and not expenses_by_date:
        return None

    # ── KPI computation ────────────────────────────────────────────────────
    total_sales = round(sum(sales_by_date.values()), 2)
    total_expenses = round(sum(expenses_by_date.values()), 2)
    net_cashflow = round(total_sales - total_expenses, 2)
    combined_expenses = round(total_expenses + fixed_costs_total, 2)
    expense_ratio = round(
        (total_expenses / total_sales * 100) if total_sales > 0 else 0.0, 1
    )

    days_with_data = len(set(sales_by_date.keys()) | set(expenses_by_date.keys()))
    avg_daily_sales = round(total_sales / days_with_data, 2) if days_with_data else 0.0
    avg_daily_expenses = (
        round(total_expenses / days_with_data, 2) if days_with_data else 0.0
    )
    burn_rate = avg_daily_expenses  # alias used in the UI

    prev_total_sales = (
        round(sum(prev_sales_by_date.values()), 2) if prev_sales_by_date else 0.0
    )
    prev_total_expenses = (
        round(sum(prev_expenses_by_date.values()), 2) if prev_expenses_by_date else 0.0
    )
    # Wave 14.CONSOLIDATE R9 — `None` instead of `0.0` when prev=0.
    # Pre-fix: a merchant who had ZERO sales in the prior period and
    # €209K in the current period got `sales_trend_pct = 0.0`, which
    # the chat AI read as "no growth" — exact opposite of reality
    # (infinite/undefined growth). Returning None unambiguously
    # signals "this comparison is undefined"; consumers and the AI
    # render it as "n/a" or "growth from zero base" rather than fake
    # zero.
    if prev_total_sales > 0:
        sales_trend_pct = round(
            (total_sales - prev_total_sales) / prev_total_sales * 100, 1,
        )
    else:
        sales_trend_pct = None
    if prev_total_expenses > 0:
        expenses_trend_pct = round(
            (total_expenses - prev_total_expenses) / prev_total_expenses * 100, 1,
        )
    else:
        expenses_trend_pct = None

    # ── v3.0: Year-over-year comparison — same period last year ─────────────
    yoy_total_sales = round(sum(yoy_sales_by_date.values()), 2) if yoy_sales_by_date else 0.0
    yoy_total_expenses = round(sum(yoy_expenses_by_date.values()), 2) if yoy_expenses_by_date else 0.0
    yoy_supplier_purchases = round(sum(yoy_purchases_by_date.values()), 2) if yoy_purchases_by_date else 0.0
    yoy_has_data = yoy_total_sales > 0 or yoy_total_expenses > 0

    def _yoy_pct(current: float, previous: float):
        """Compute YoY % change.

        Wave 14.HOTFIX6 (F2) — now delegates to ``core.delta_formulas.
        compute_period_delta`` so this builder and query_period_comparison
        agree on edge cases. Behaviour:
          - previous > 0  → same as before (signed pct of growth)
          - previous == 0 → None (unchanged — genuinely undefined)
          - previous < 0  → CHANGED: now returns signed pct relative to
                            |previous| (was None pre-HOTFIX6). Matches
                            the period_comparison convention and lets
                            the AI distinguish "loss shrunk" from
                            "loss grew" via the sign of the pct.
        """
        from core.delta_formulas import compute_period_delta
        return compute_period_delta(previous, current)["delta_pct"]

    # ── v2.2: Bucket B metrics (supplier purchases) ────────────────────────
    supplier_purchases = round(sum(purchases_by_date.values()), 2)
    variable_outflows = round(total_expenses + supplier_purchases, 2)
    total_outflows = round(variable_outflows + fixed_costs_total, 2)
    net_before_fixed = round(total_sales - variable_outflows, 2)
    net_after_fixed = round(total_sales - total_outflows, 2)
    purchase_ratio = kpi_formulas.cost_to_revenue_ratio(supplier_purchases, total_sales) or 0.0
    total_outflow_ratio = kpi_formulas.cost_to_revenue_ratio(total_outflows, total_sales) or 0.0

    # ── v3.0: Derived financial KPIs via canonical formulas ─────────────────
    operating_margin = round(total_sales - variable_outflows, 2)
    operating_margin_pct = kpi_formulas.net_margin_pct(operating_margin, total_sales) or 0.0
    vcr = kpi_formulas.variable_cost_ratio(variable_outflows, total_sales)
    break_even = kpi_formulas.break_even_point(fixed_costs_total, vcr)
    burn_rate_total = kpi_formulas.burn_rate_daily(total_outflows, period_days) or 0.0
    fixed_costs_pct = kpi_formulas.fixed_cost_ratio(fixed_costs_total, total_sales) or 0.0

    # ── v3.0: Payment cycle KPIs via canonical formulas ─────────────────────
    dso = kpi_formulas.dso(open_receivables, total_sales, period_days) or 0.0
    dpo = kpi_formulas.dpo(open_payables, supplier_purchases, period_days) or 0.0
    cash_conversion_cycle = kpi_formulas.cash_conversion_gap(
        kpi_formulas.dso(open_receivables, total_sales, period_days),
        kpi_formulas.dpo(open_payables, supplier_purchases, period_days),
    ) or 0.0

    # Scadenzario netto prossimi 30 giorni
    _thirty_days = (datetime.strptime(end, "%Y-%m-%d").date() + timedelta(days=30)).isoformat()
    upcoming_recv_total = round(sum(r["total"] for r in upcoming_receivables), 2)
    upcoming_pay_total = round(sum(p["total"] for p in upcoming_payables), 2)
    # Filter to 30-day window for net scadenzario
    _cutoff_30 = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    scadenzario_netto_30 = round(
        sum(r["total"] for r in upcoming_receivables if r["date"] <= _cutoff_30)
        - sum(p["total"] for p in upcoming_payables if p["date"] <= _cutoff_30),
        2,
    )

    # ── Canonical daily series (4-bucket: sales − expenses − purchases − fixed) ─
    # Every daily data point uses the full 4-bucket net, not the legacy 2-bucket.
    # This ensures cumulative, charts, and giorni_autonomia are all consistent
    # with net_after_fixed at the period level.
    all_dates = sorted(
        set(sales_by_date.keys()) | set(expenses_by_date.keys()) | set(purchases_by_date.keys())
    )
    daily_series = []
    running = 0.0
    daily_fixed = round(fixed_costs_total / period_days, 2) if period_days > 0 else 0.0
    for d in all_dates:
        s = round(sales_by_date.get(d, 0.0), 2)
        e = round(expenses_by_date.get(d, 0.0), 2)
        p = round(purchases_by_date.get(d, 0.0), 2)
        net = round(s - e - p - daily_fixed, 2)  # 4-bucket daily net
        running = round(running + net, 2)
        daily_series.append(
            {"date": d, "sales": s, "expenses": e, "purchases": p,
             "fixed_costs_daily": daily_fixed,
             "net_cashflow": net, "cumulative": running}
        )

    # Giorni di Autonomia — via canonical formula (diagnostic only in v3.0)
    giorni_autonomia = kpi_formulas.operational_coverage_days(
        net_after_fixed, total_outflows, period_days,
    ) or 0.0

    # ── Category percentages ───────────────────────────────────────────────
    total_sales_cat = sum(c.get("total", 0) for c in top_sales_cats)
    for cat in top_sales_cats:
        cat["percentage"] = round(
            (cat["total"] / total_sales_cat * 100) if total_sales_cat > 0 else 0.0, 1
        )

    total_exp_cat = sum(c.get("total", 0) for c in top_expense_cats)
    for cat in top_expense_cats:
        cat["percentage"] = round(
            (cat["total"] / total_exp_cat * 100) if total_exp_cat > 0 else 0.0, 1
        )

    # ── Alerts summary (cashflow_monitor only) ─────────────────────────────
    cf_alerts = [a for a in all_alerts if a.get("module_key") == "cashflow_monitor"]
    open_alerts = [a for a in cf_alerts if a.get("status") in ("new", "acknowledged")]

    by_severity: dict = {"high": 0, "medium": 0, "low": 0}
    for a in open_alerts:
        sev = (a.get("severity") or "").lower()
        if sev in by_severity:
            by_severity[sev] += 1

    recent_alerts_list = [
        {
            "id": a.get("id"),
            "title": a.get("title"),
            "severity": a.get("severity"),
            "date_reference": a.get("date_reference"),
            "status": a.get("status"),
            # Wave 13.4 — surface the original analysis window so the
            # chat AI (which consumes this list via query_cashflow_summary
            # / query_business_summary) can correctly explain alerts on
            # the period THEY were generated for, rather than the
            # user's current filter. May be None for pre-Wave-13.4
            # alerts; the chat layer treats None as "unknown window".
            "analysis_window": (
                {
                    "start": a.get("period_start"),
                    "end": a.get("period_end"),
                    "label": a.get("window_label"),
                }
                if a.get("period_start") and a.get("period_end")
                else None
            ),
        }
        for a in open_alerts[:5]
    ]

    # ── Last AI insight ────────────────────────────────────────────────────
    last_insight = None
    if last_insight_doc:
        last_insight = {
            "id": last_insight_doc.get("id"),
            "title": last_insight_doc.get("title"),
            "content": last_insight_doc.get("content"),
            "created_at": last_insight_doc.get("created_at"),
            "period_start": last_insight_doc.get("period_start"),
            "period_end": last_insight_doc.get("period_end"),
            "model_version": last_insight_doc.get("model_version"),
        }

    # ── v2.3: Module status (derived from already-computed KPIs + alerts) ──
    # Pure function — no additional queries.  compute_status() never raises.
    status = compute_status(
        kpis={
            "total_sales":         total_sales,
            "net_after_fixed":     net_after_fixed,
            "total_outflow_ratio": total_outflow_ratio,
            "total_expenses":      total_expenses,
            "supplier_purchases":  supplier_purchases,
            "fixed_costs_total":   fixed_costs_total,
            "sales_trend_pct":     sales_trend_pct,
            "period_days":         period_days,
        },
        alerts_summary={
            "open_count":   len(open_alerts),
            "by_severity":  by_severity,
        },
        locale=locale,
    )

    # ── v3.0: New KPIs for redesigned health score ─────────────────────────

    # Margin trend: compare current net margin % with previous period
    prev_supplier_purchases = round(sum((yoy_purchases_by_date or {}).values()), 2) if yoy_purchases_by_date else 0.0
    prev_variable_outflows = round(prev_total_expenses + prev_supplier_purchases, 2) if prev_total_expenses else 0.0
    prev_total_outflows = round(prev_variable_outflows + fixed_costs_total, 2)
    prev_net_after_fixed = round(prev_total_sales - prev_total_outflows, 2) if prev_total_sales > 0 else 0.0
    prev_net_margin = round((prev_net_after_fixed / prev_total_sales * 100), 1) if prev_total_sales > 0 else None
    current_net_margin = round((net_after_fixed / total_sales * 100), 1) if total_sales > 0 else None

    margin_trend_pp = None
    if current_net_margin is not None and prev_net_margin is not None:
        margin_trend_pp = round(current_net_margin - prev_net_margin, 1)

    # Sales trend: already computed (sales_trend_pct), convert 0.0→None when prev=0
    effective_sales_trend = sales_trend_pct if prev_total_sales > 0 else None

    # Cash conversion gap (counts already fetched in parallel gather above)
    cash_conversion_gap = None
    has_payment_data = _sales_ps_count >= 3 or _purchases_ps_count >= 3

    if has_payment_data and (dso > 0 or dpo > 0):
        cash_conversion_gap = round(dso - dpo, 1)

    # Data sources present (count of data types with at least 1 record)
    data_sources = 0
    if total_sales > 0: data_sources += 1
    if total_expenses > 0: data_sources += 1
    if supplier_purchases > 0: data_sources += 1
    if fixed_costs_total > 0: data_sources += 1

    # ── Load health score dimension preferences ────────────────────────────
    disabled_dimensions = set()
    try:
        from database import module_configs_collection
        from modules.cashflow_monitor.health_score import migrate_dimension_config
        config_doc = await module_configs_collection.find_one(
            {"organization_id": org_id, "module_key": "cashflow_monitor"},
            {"_id": 0, "health_score_dimensions": 1},
        )
        if config_doc and config_doc.get("health_score_dimensions"):
            dims = config_doc["health_score_dimensions"]
            # Auto-migrate old keys if detected
            old_keys = {"net_result", "outflow_ratio", "operating_margin", "liquidity"}
            if any(k in dims for k in old_keys):
                dims = migrate_dimension_config(dims)
            disabled_dimensions = {k for k, v in dims.items() if v is False}
    except Exception:
        pass

    # ── v3.0: Composite health score ──────────────────────────────────────
    health_kpis = {
        "total_sales": total_sales,
        "net_after_fixed": net_after_fixed,
        "total_outflows": total_outflows,
        "variable_outflows": variable_outflows,
        "break_even": break_even,
        "fixed_costs_total": fixed_costs_total,
        "sales_trend_pct": effective_sales_trend,
        "margin_trend_pp": margin_trend_pp,
        "cash_conversion_gap": cash_conversion_gap,
        "has_payment_status_data": has_payment_data,
        "dso": dso,
        "dpo": dpo,
        "data_sources_present": data_sources,
        "period_days": period_days,
        "total_outflow_ratio": total_outflow_ratio,
        "operating_margin_pct": operating_margin_pct,
        "giorni_autonomia": giorni_autonomia,
    }

    health_score = compute_health_score(
        kpis=health_kpis,
        alerts_high_count=by_severity.get("high", 0),
        disabled_dimensions=disabled_dimensions,
    )

    # ── Health explanation (consumes full structured output) ───────────────
    health_explanation = await generate_health_explanation(
        health_score,
        kpis=health_kpis,
        locale=locale,
    )
    health_score["explanation"] = health_explanation

    # ── Assemble response ──────────────────────────────────────────────────
    return {
        "module": {
            "module_key": "cashflow_monitor",
            "module_name": "Daily Cashflow Monitor",
            "is_available": True,
        },
        "period": {
            "label": period,
            "start_date": start,
            "end_date": end,
            "days": period_days,
            # Wave 14.CONSOLIDATE R3 — explicit semantic so the chat AI
            # and the comparison block consumers can tell apart a YTD
            # window (where prev_period == prior-year YTD) from a
            # rolling window (where prev_period == immediately preceding
            # N days). Pre-fix the model had to infer this from the
            # date math, which it could not do reliably.
            "semantic": period_semantic,  # "ytd" | "rolling"
            "prev_period": {
                "start_date": prev_start,
                "end_date":   prev_end,
                "semantic":   (
                    "ytd_prior_year" if period_semantic == "ytd"
                    else "rolling_prior_period"
                ),
            },
        },
        "data_availability": date_range_info,
        "kpis": {
            # ── Canonical 4-bucket fields (trusted, used by UI and AI) ────
            "total_sales": total_sales,
            "total_expenses": total_expenses,
            "supplier_purchases": supplier_purchases,
            "fixed_costs_total": fixed_costs_total,
            "total_outflows": total_outflows,
            "net_after_fixed": net_after_fixed,
            "total_outflow_ratio": total_outflow_ratio,
            "operating_margin": operating_margin,
            "operating_margin_pct": operating_margin_pct,
            "break_even": break_even,
            "burn_rate_total": burn_rate_total,
            "giorni_autonomia": giorni_autonomia,
            "fixed_costs_pct": fixed_costs_pct,
            "variable_outflows": variable_outflows,
            "net_before_fixed": net_before_fixed,
            "purchase_ratio": purchase_ratio,
            "avg_daily_sales": avg_daily_sales,
            "avg_daily_expenses": avg_daily_expenses,
            "sales_trend_pct": sales_trend_pct,
            "expenses_trend_pct": expenses_trend_pct,
            "period_days": period_days,
            # ── Scadenzario KPIs (data-quality dependent) ─────────────────
            "dso": dso,
            "dpo": dpo,
            "cash_conversion_cycle": cash_conversion_cycle,
            "open_receivables": open_receivables,
            "open_payables": open_payables,
            "scadenzario_netto_30": scadenzario_netto_30,
        },
        # ── Legacy fields (deprecated — kept for backward compat only) ────
        # These use 2-bucket or 1-bucket formulas and must NOT be used for
        # financial reasoning. They will be removed in a future version.
        "_legacy": {
            "net_cashflow": net_cashflow,         # 2-bucket: sales − expenses
            "burn_rate": burn_rate,                # 1-bucket: avg_daily_expenses
            "expense_ratio": expense_ratio,        # 1-bucket: expenses / sales
            "combined_expenses": combined_expenses, # 2-bucket: expenses + fixed
        },
        "yoy": {
            "has_data": yoy_has_data,
            "period_start": yoy_start,
            "period_end": yoy_end,
            "total_sales": yoy_total_sales,
            "total_expenses": yoy_total_expenses,
            "supplier_purchases": yoy_supplier_purchases,
            "total_outflows": round(yoy_total_expenses + yoy_supplier_purchases + (fixed_costs_total if yoy_has_data else 0), 2),
            "net_after_fixed": round(yoy_total_sales - yoy_total_expenses - yoy_supplier_purchases - (fixed_costs_total if yoy_has_data else 0), 2) if yoy_has_data else None,
            "pct": {
                "total_sales": _yoy_pct(total_sales, yoy_total_sales),
                "total_expenses": _yoy_pct(total_expenses, yoy_total_expenses),
                "supplier_purchases": _yoy_pct(supplier_purchases, yoy_supplier_purchases),
                "net_after_fixed": _yoy_pct(net_after_fixed, yoy_total_sales - yoy_total_expenses - yoy_supplier_purchases - fixed_costs_total) if yoy_has_data and (yoy_total_sales - yoy_total_expenses - yoy_supplier_purchases - fixed_costs_total) != 0 else None,
                "total_outflow_ratio": _yoy_pct(total_outflow_ratio, round((yoy_total_expenses + yoy_supplier_purchases + fixed_costs_total) / yoy_total_sales * 100, 1) if yoy_total_sales > 0 else 0) if yoy_has_data else None,
                "operating_margin_pct": _yoy_pct(operating_margin_pct, round((yoy_total_sales - yoy_total_expenses - yoy_supplier_purchases) / yoy_total_sales * 100, 1) if yoy_total_sales > 0 else 0) if yoy_has_data else None,
            },
        },
        "charts": {
            "daily_series": daily_series,
        },
        "suppliers": {
            "top_suppliers": [
                {
                    "supplier": s.get("_id"),
                    "total": round(s.get("total", 0), 2),
                    "count": s.get("count", 0),
                    "percentage": round(
                        (s.get("total", 0) / supplier_purchases * 100) if supplier_purchases > 0 else 0.0, 1
                    ),
                }
                for s in (purchases_by_supplier or [])[:10]
            ],
        },
        "purchase_distribution": {
            "by_product": [
                {
                    "name": p.get("_id", ""),
                    "total": round(p.get("total", 0), 2),
                    "count": p.get("count", 0),
                }
                for p in (purchases_by_product or [])[:15]
            ],
            "by_category": [
                {
                    "name": c.get("_id", ""),
                    "total": round(c.get("total", 0), 2),
                    "count": c.get("count", 0),
                }
                for c in (purchases_by_category_macro or [])[:15]
            ],
        },
        "categories": {
            "top_sales": [
                {
                    "category": c.get("_id"),
                    "total": round(c.get("total", 0), 2),
                    "count": c.get("count", 0),
                    "percentage": c.get("percentage", 0.0),
                }
                for c in top_sales_cats[:5]
            ],
            "top_expenses": [
                {
                    "category": c.get("_id"),
                    "total": round(c.get("total", 0), 2),
                    "count": c.get("count", 0),
                    "percentage": c.get("percentage", 0.0),
                }
                for c in top_expense_cats[:5]
            ],
        },
        "alerts": {
            "open_count": len(open_alerts),
            "by_severity": by_severity,
            "recent": recent_alerts_list,
        },
        "scadenzario": {
            "receivables_aging": receivables_aging,
            "payables_aging": payables_aging,
            "upcoming_receivables": upcoming_receivables,
            "upcoming_payables": upcoming_payables,
            "upcoming_receivables_total": upcoming_recv_total,
            "upcoming_payables_total": upcoming_pay_total,
        },
        "last_insight": last_insight,
        "status": status,           # v2.3: synthetic health status (additive)
        "health_score": health_score,  # v2.4: composite 0-100 score
    }
