"""
Cashflow Monitor — KPI snapshot builder.

Extracted verbatim from kpi_snapshot_service._compute_cashflow_kpis() so
the computation logic lives inside the module that owns the data contract.

Registered as the snapshot_builder capability in
modules/cashflow_monitor/__init__.py.

Public interface:
    build_snapshot(org_id, start_date, end_date) -> dict
        Returns the same metrics dict shape that was previously produced by
        kpi_snapshot_service._compute_cashflow_kpis().  All existing metric
        keys are preserved unchanged — this is an extraction, not a refactor.
"""
from repositories import analytics_repository


async def build_snapshot(org_id: str, start_date: str, end_date: str) -> dict:
    """Aggregate cashflow KPIs for the given period.

    Returns the metrics dict that kpi_snapshot_service will persist in
    the kpi_snapshots collection.

    v2.1: includes fixed_costs_total (prorated from the fixed_costs
    collection).  All pre-existing metric keys are preserved unchanged.

    NOTE: `net_cashflow` intentionally remains calculated from
    expense_records only (matching the live /analytics/kpis endpoint
    behaviour).  Consumers that need the combined view should use the
    `fixed_costs_total` key to compute their own adjusted figures without
    breaking existing callers.
    """
    # All 8 aggregations are independent — run in parallel for ~4× speedup.
    import asyncio
    (
        sales_by_date,
        expenses_by_date,
        sales_by_cat,
        expenses_by_cat,
        fixed_costs_total,
        purchases_by_date,
        open_receivables,
        open_payables,
    ) = await asyncio.gather(
        analytics_repository.aggregate_sales_by_date(org_id, start_date, end_date),
        analytics_repository.aggregate_expenses_by_date(org_id, start_date, end_date),
        analytics_repository.aggregate_sales_by_category(org_id, start_date, end_date),
        analytics_repository.aggregate_expenses_by_category(org_id, start_date, end_date),
        analytics_repository.aggregate_fixed_costs_total(org_id, start_date, end_date),
        analytics_repository.aggregate_purchases_by_date(org_id, start_date, end_date),
        analytics_repository.aggregate_open_receivables(org_id),
        analytics_repository.aggregate_open_payables(org_id),
    )

    total_sales = round(sum(sales_by_date.values()), 2)
    total_expenses = round(sum(expenses_by_date.values()), 2)
    net_cashflow = round(total_sales - total_expenses, 2)

    days = len(set(sales_by_date.keys()) | set(expenses_by_date.keys())) or 1

    # v2.2 derived metrics
    supplier_purchases = round(sum(purchases_by_date.values()), 2)
    variable_outflows = round(total_expenses + supplier_purchases, 2)
    total_outflows = round(variable_outflows + fixed_costs_total, 2)

    return {
        # ── Existing keys — DO NOT rename, remove, or reorder ────────────────
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "net_cashflow": net_cashflow,           # expense_records only (unchanged)
        "avg_daily_sales": round(total_sales / days, 2),
        "avg_daily_expenses": round(total_expenses / days, 2),
        "period_days": days,
        "top_sales_categories": [
            {"category": r["_id"], "total": round(r["total"], 2)}
            for r in (sales_by_cat or [])[:5]
        ],
        "top_expense_categories": [
            {"category": r["_id"], "total": round(r["total"], 2)}
            for r in (expenses_by_cat or [])[:5]
        ],
        # ── v2.1 additions — new keys only, safe to add ───────────────────────
        # fixed_costs_total: prorated sum of active fixed costs for the period.
        # 0.0 when the fixed_costs collection is empty (backward-safe default).
        "fixed_costs_total": fixed_costs_total,
        # ── v2.2 additions — Bucket B: supplier purchases ─────────────────────
        # All default to 0.0 when purchase_records collection is empty.
        # net_cashflow above intentionally unchanged (expense_records only).
        "supplier_purchases": supplier_purchases,           # Bucket B total
        "variable_outflows": variable_outflows,             # Bucket A + B
        "total_outflows": total_outflows,                   # Bucket A + B + C
        "net_before_fixed": round(total_sales - variable_outflows, 2),   # Sales - (A+B)
        "net_after_fixed": round(total_sales - total_outflows, 2),       # Sales - (A+B+C)
        # ── v2.4 additions — Phase 1 derived financial KPIs ──────────────────
        "operating_margin": round(total_sales - variable_outflows, 2),
        "operating_margin_pct": round(
            ((total_sales - variable_outflows) / total_sales * 100)
            if total_sales > 0 else 0.0, 1
        ),
        "break_even": (
            round(fixed_costs_total / (1 - (variable_outflows / total_sales)), 2)
            if total_sales > 0 and (variable_outflows / total_sales) < 1 and fixed_costs_total > 0
            else None  # Not computable: variable costs >= revenue or no fixed costs
        ),
        "burn_rate_total": round(total_outflows / days, 2) if days > 0 else 0.0,
        "fixed_costs_pct": round(
            (fixed_costs_total / total_sales * 100) if total_sales > 0 else 0.0, 1
        ),
        # ── v2.5 — Scadenzario KPIs (computed from open receivables/payables) ──
        # DSO/DPO use `days` (active-data-day count) as the period multiplier.
        # Note: overview_builder uses `period_days` (calendar days) — small
        # divergence when data has date gaps.  Both return 0.0 when there is
        # no payment-status data (aggregate returns 0.0).
        # scadenzario_netto_30 stays 0.0 because it needs time-relative
        # upcoming-receivables/payables queries that snapshot does not run.
        "dso": round(
            (open_receivables / total_sales * days) if total_sales > 0 else 0.0, 1
        ),
        "dpo": round(
            (open_payables / supplier_purchases * days) if supplier_purchases > 0 else 0.0, 1
        ),
        "cash_conversion_cycle": round(
            (open_receivables / total_sales * days if total_sales > 0 else 0.0)
            - (open_payables / supplier_purchases * days if supplier_purchases > 0 else 0.0),
            1,
        ),
        "open_receivables": open_receivables,
        "open_payables": open_payables,
        "scadenzario_netto_30": 0.0,  # requires upcoming queries — not in snapshot scope
    }
