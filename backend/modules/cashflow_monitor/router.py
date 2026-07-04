from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List
from collections import defaultdict
from models import KPIData, ChartDataPoint
from auth import get_current_user
from datetime import datetime, timedelta
from .service import get_date_range, get_aggregated_data, calculate_moving_average
from repositories import analytics_repository, organization_repository
from services.module_access import check_module_access, build_module_access_status

router = APIRouter(prefix="/analytics", tags=["Analytics"])


async def _get_org_doc(current_user: dict) -> dict:
    """Fetch the org document for the current user.  Used by access checks."""
    org_doc = await organization_repository.find_by_id(current_user["organization_id"])
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return org_doc


@router.get("/kpis")
async def get_kpis(
    period: str = Query("30d", regex="^(7d|30d|90d|custom|data_range)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> KPIData:
    """Get KPI data for the dashboard"""
    org_doc = await _get_org_doc(current_user)
    await check_module_access(org_doc["id"], "cashflow_monitor", "analytics", org_doc=org_doc)
    org_id = current_user['organization_id']
    start, end = get_date_range(period, start_date, end_date)
    
    current_data = await get_aggregated_data(org_id, start, end)
    
    if not current_data:
        return KPIData(
            total_sales=0, total_expenses=0, net_cashflow=0,
            avg_daily_sales=0, avg_daily_expenses=0,
            sales_trend_pct=0, expenses_trend_pct=0, cashflow_trend_pct=0,
            period_days=0
        )
    
    total_sales = sum(d.total_sales for d in current_data)
    total_expenses = sum(d.total_expenses for d in current_data)
    total_purchases = sum(d.total_purchases for d in current_data)
    total_fixed_costs = sum(d.total_fixed_costs for d in current_data)
    net_cashflow = total_sales - total_expenses - total_purchases - total_fixed_costs

    days_with_data = len(current_data)
    avg_daily_sales = total_sales / days_with_data if days_with_data > 0 else 0
    avg_daily_expenses = total_expenses / days_with_data if days_with_data > 0 else 0

    # Calculate previous period for trend comparison
    start_dt = datetime.strptime(start, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end, '%Y-%m-%d').date()
    period_length = (end_dt - start_dt).days + 1

    prev_end = start_dt - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length - 1)
    prev_data = await get_aggregated_data(org_id, prev_start.isoformat(), prev_end.isoformat())

    prev_sales = sum(d.total_sales for d in prev_data) if prev_data else 0
    prev_expenses = sum(d.total_expenses for d in prev_data) if prev_data else 0
    prev_purchases = sum(d.total_purchases for d in prev_data) if prev_data else 0
    prev_fixed_costs = sum(d.total_fixed_costs for d in prev_data) if prev_data else 0
    prev_cashflow = prev_sales - prev_expenses - prev_purchases - prev_fixed_costs

    sales_trend = ((total_sales - prev_sales) / prev_sales * 100) if prev_sales > 0 else 0
    expenses_trend = ((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
    cashflow_trend = ((net_cashflow - prev_cashflow) / abs(prev_cashflow) * 100) if prev_cashflow != 0 else 0

    return KPIData(
        total_sales=round(total_sales, 2),
        total_expenses=round(total_expenses, 2),
        total_purchases=round(total_purchases, 2),
        total_fixed_costs=round(total_fixed_costs, 2),
        net_cashflow=round(net_cashflow, 2),
        avg_daily_sales=round(avg_daily_sales, 2),
        avg_daily_expenses=round(avg_daily_expenses, 2),
        sales_trend_pct=round(sales_trend, 1),
        expenses_trend_pct=round(expenses_trend, 1),
        cashflow_trend_pct=round(cashflow_trend, 1),
        period_days=days_with_data
    )


@router.get("/charts")
async def get_chart_data(
    period: str = Query("30d", regex="^(7d|30d|90d|custom|data_range)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> List[ChartDataPoint]:
    """Get chart data for visualizations"""
    org_doc = await _get_org_doc(current_user)
    await check_module_access(org_doc["id"], "cashflow_monitor", "analytics", org_doc=org_doc)
    org_id = current_user['organization_id']
    start, end = get_date_range(period, start_date, end_date)

    data = await get_aggregated_data(org_id, start, end)
    
    if not data:
        return []
    
    sales_ma7 = calculate_moving_average(data, 'total_sales', 7)
    expenses_ma7 = calculate_moving_average(data, 'total_expenses', 7)
    
    result = []
    for d in data:
        result.append(ChartDataPoint(
            date=d.date,
            sales=round(d.total_sales, 2),
            expenses=round(d.total_expenses, 2),
            purchases=round(d.total_purchases, 2),
            fixed_costs=round(d.total_fixed_costs, 2),
            net_cashflow=round(d.net_cashflow, 2),
            sales_ma7=round(sales_ma7.get(d.date, 0), 2),
            expenses_ma7=round(expenses_ma7.get(d.date, 0), 2)
        ))
    
    return result


@router.get("/summary")
async def get_analytics_summary(
    period: str = Query("30d", regex="^(7d|30d|90d|custom|data_range)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive analytics summary for AI explanation"""
    org_doc = await _get_org_doc(current_user)
    await check_module_access(org_doc["id"], "cashflow_monitor", "analytics", org_doc=org_doc)
    org_id = current_user['organization_id']
    start, end = get_date_range(period, start_date, end_date)
    
    data = await get_aggregated_data(org_id, start, end)
    
    if not data:
        return {"has_data": False, "period": {"start": start, "end": end}}
    
    total_sales = sum(d.total_sales for d in data)
    total_expenses = sum(d.total_expenses for d in data)
    total_purchases = sum(d.total_purchases for d in data)
    total_fixed_costs = sum(d.total_fixed_costs for d in data)
    net_cashflow = total_sales - total_expenses - total_purchases - total_fixed_costs

    days = len(data)
    avg_sales = total_sales / days
    avg_expenses = total_expenses / days
    
    sales_values = [d.total_sales for d in data]
    expenses_values = [d.total_expenses for d in data]
    
    sales_std = (sum((x - avg_sales) ** 2 for x in sales_values) / len(sales_values)) ** 0.5 if sales_values else 0
    expenses_std = (sum((x - avg_expenses) ** 2 for x in expenses_values) / len(expenses_values)) ** 0.5 if expenses_values else 0
    
    start_dt = datetime.strptime(start, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end, '%Y-%m-%d').date()
    period_length = (end_dt - start_dt).days + 1
    
    prev_end = start_dt - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length - 1)
    prev_data = await get_aggregated_data(org_id, prev_start.isoformat(), prev_end.isoformat())
    
    prev_sales = sum(d.total_sales for d in prev_data) if prev_data else 0
    prev_expenses = sum(d.total_expenses for d in prev_data) if prev_data else 0
    
    low_sales_days = [d for d in data if d.total_sales < avg_sales * 0.7]
    high_expense_days = [d for d in data if d.total_expenses > avg_expenses * 1.3]
    negative_cashflow_days = [d for d in data if d.net_cashflow < 0]
    
    import itertools
    consecutive_negative = 0
    if any(d.net_cashflow < 0 for d in data):
        consecutive_negative = max(
            len(list(g)) for k, g in itertools.groupby([d.net_cashflow < 0 for d in data]) if k
        )
    
    return {
        "has_data": True,
        "period": {"start": start, "end": end, "days": days},
        "totals": {"sales": round(total_sales, 2), "expenses": round(total_expenses, 2), "purchases": round(total_purchases, 2), "fixed_costs": round(total_fixed_costs, 2), "net_cashflow": round(net_cashflow, 2)},
        "averages": {"daily_sales": round(avg_sales, 2), "daily_expenses": round(avg_expenses, 2)},
        "volatility": {"sales_std": round(sales_std, 2), "expenses_std": round(expenses_std, 2)},
        "trends": {
            "sales_vs_prev": round(((total_sales - prev_sales) / prev_sales * 100) if prev_sales > 0 else 0, 1),
            "expenses_vs_prev": round(((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0, 1)
        },
        "anomalies": {
            "low_sales_days_count": len(low_sales_days),
            "high_expense_days_count": len(high_expense_days),
            "negative_cashflow_days_count": len(negative_cashflow_days),
            "consecutive_negative_days": consecutive_negative
        },
        "notable_days": {
            "lowest_sales": min(data, key=lambda x: x.total_sales).model_dump() if data else None,
            "highest_expenses": max(data, key=lambda x: x.total_expenses).model_dump() if data else None,
            "best_cashflow": max(data, key=lambda x: x.net_cashflow).model_dump() if data else None,
            "worst_cashflow": min(data, key=lambda x: x.net_cashflow).model_dump() if data else None
        }
    }


@router.get("/date-range")
async def get_available_date_range(current_user: dict = Depends(get_current_user)):
    """Get the date range of available data for the organization."""
    return await analytics_repository.get_analytics_date_range(current_user["organization_id"])


@router.get("/categories/sales")
async def get_sales_by_category(
    period: str = Query("30d", regex="^(7d|30d|90d|custom|data_range)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get sales breakdown by category."""
    org_doc = await _get_org_doc(current_user)
    await check_module_access(org_doc["id"], "cashflow_monitor", "analytics", org_doc=org_doc)
    org_id = current_user["organization_id"]
    start, end = get_date_range(period, start_date, end_date)

    raw = await analytics_repository.aggregate_sales_by_category(org_id, start, end)

    categories = [
        {"category": doc["_id"], "total": round(doc["total"], 2), "count": doc["count"]}
        for doc in raw
    ]
    total = sum(c["total"] for c in categories)
    for cat in categories:
        cat["percentage"] = round((cat["total"] / total * 100) if total > 0 else 0, 1)

    return {"period": {"start": start, "end": end}, "total": round(total, 2), "categories": categories}


@router.get("/categories/expenses")
async def get_expenses_by_category(
    period: str = Query("30d", regex="^(7d|30d|90d|custom|data_range)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get expenses breakdown by category."""
    org_doc = await _get_org_doc(current_user)
    await check_module_access(org_doc["id"], "cashflow_monitor", "analytics", org_doc=org_doc)
    org_id = current_user["organization_id"]
    start, end = get_date_range(period, start_date, end_date)

    raw = await analytics_repository.aggregate_expenses_by_category(org_id, start, end)

    categories = [
        {"category": doc["_id"], "total": round(doc["total"], 2), "count": doc["count"]}
        for doc in raw
    ]
    total = sum(c["total"] for c in categories)
    for cat in categories:
        cat["percentage"] = round((cat["total"] / total * 100) if total > 0 else 0, 1)

    return {"period": {"start": start, "end": end}, "total": round(total, 2), "categories": categories}


@router.get("/categories/purchases")
async def get_purchases_by_category(
    period: str = Query("30d", regex="^(7d|30d|90d|custom|data_range)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get purchases breakdown by supplier."""
    org_doc = await _get_org_doc(current_user)
    await check_module_access(org_doc["id"], "cashflow_monitor", "analytics", org_doc=org_doc)
    org_id = current_user['organization_id']
    start, end = get_date_range(period, start_date, end_date)

    raw = await analytics_repository.aggregate_purchases_by_supplier(org_id, start, end)

    categories = [
        {"category": doc["_id"], "total": round(doc["total"], 2), "count": doc["count"]}
        for doc in raw
    ]
    total = sum(c["total"] for c in categories)
    for cat in categories:
        cat['percentage'] = round((cat['total'] / total * 100) if total > 0 else 0, 1)

    return {"period": {"start": start, "end": end}, "total": round(total, 2), "categories": categories}


@router.get("/categories/trends")
async def get_category_trends(
    category_type: str = Query("sales", regex="^(sales|expenses)$"),
    period: str = Query("30d", regex="^(7d|30d|90d|custom|data_range)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get daily trends by category."""
    org_doc = await _get_org_doc(current_user)
    await check_module_access(org_doc["id"], "cashflow_monitor", "analytics", org_doc=org_doc)
    org_id = current_user['organization_id']
    start, end = get_date_range(period, start_date, end_date)

    raw = await analytics_repository.aggregate_by_date_and_category(org_id, start, end, record_type=category_type)

    dates_data = defaultdict(dict)
    all_categories = set()

    for doc in raw:
        date = doc['_id']['date']
        category = doc['_id']['category']
        dates_data[date][category] = round(doc['total'], 2)
        all_categories.add(category)

    chart_data = []
    for date in sorted(dates_data.keys()):
        point = {"date": date}
        for cat in all_categories:
            point[cat] = dates_data[date].get(cat, 0)
        chart_data.append(point)

    return {"period": {"start": start, "end": end}, "categories": list(all_categories), "data": chart_data}


# ── v2.1: Enriched KPIs endpoint ──────────────────────────────────────────────
# Returns a superset of /kpis: all standard KPIData fields PLUS fixed_costs_total,
# expense_ratio, and the top expense category — computed in a single round-trip.
# The original /kpis endpoint is preserved unchanged for backward compatibility.

@router.get("/cashflow/enriched-kpis")
async def get_enriched_kpis(
    period: str = Query("30d", regex="^(7d|30d|90d|custom|data_range)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """KPI arricchiti per il Cashflow Monitor v2.

    Restituisce tutti i campi di /kpis più:
    - fixed_costs_total  — costi fissi proratizzati al periodo
    - expense_ratio      — spese / ricavi × 100
    - burn_rate          — media giornaliera delle spese (= avg_daily_expenses)
    - top_expense_category — prima categoria di spesa per importo
    - combined_expenses  — expense_records + fixed_costs
    """
    org_doc = await _get_org_doc(current_user)
    await check_module_access(org_doc["id"], "cashflow_monitor", "analytics", org_doc=org_doc)
    org_id = current_user["organization_id"]
    start, end = get_date_range(period, start_date, end_date)

    current_data = await get_aggregated_data(org_id, start, end)

    if not current_data:
        return {
            "total_sales": 0, "total_expenses": 0, "net_cashflow": 0,
            "avg_daily_sales": 0, "avg_daily_expenses": 0,
            "sales_trend_pct": 0, "expenses_trend_pct": 0, "cashflow_trend_pct": 0,
            "period_days": 0,
            "fixed_costs_total": 0, "expense_ratio": 0, "burn_rate": 0,
            "combined_expenses": 0, "top_expense_category": None,
        }

    total_sales = sum(d.total_sales for d in current_data)
    total_expenses = sum(d.total_expenses for d in current_data)
    net_cashflow = total_sales - total_expenses
    days_with_data = len(current_data)
    avg_daily_sales = total_sales / days_with_data if days_with_data > 0 else 0
    avg_daily_expenses = total_expenses / days_with_data if days_with_data > 0 else 0

    # Previous period for trend comparison
    start_dt = datetime.strptime(start, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end, "%Y-%m-%d").date()
    period_length = (end_dt - start_dt).days + 1
    prev_end = start_dt - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length - 1)
    prev_data = await get_aggregated_data(org_id, prev_start.isoformat(), prev_end.isoformat())
    prev_sales = sum(d.total_sales for d in prev_data) if prev_data else 0
    prev_expenses = sum(d.total_expenses for d in prev_data) if prev_data else 0
    prev_cashflow = prev_sales - prev_expenses

    sales_trend = ((total_sales - prev_sales) / prev_sales * 100) if prev_sales > 0 else 0
    expenses_trend = ((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0
    cashflow_trend = ((net_cashflow - prev_cashflow) / abs(prev_cashflow) * 100) if prev_cashflow != 0 else 0

    # New enriched fields
    fixed_costs_total = await analytics_repository.aggregate_fixed_costs_total(org_id, start, end)
    combined_expenses = round(total_expenses + fixed_costs_total, 2)
    expense_ratio = round((total_expenses / total_sales * 100) if total_sales > 0 else 0, 1)

    expense_cats = await analytics_repository.aggregate_expenses_by_category(org_id, start, end)
    top_expense_category = None
    if expense_cats:
        top = expense_cats[0]
        cat_total = round(top.get("total", 0), 2)
        cat_pct = round((cat_total / total_expenses * 100) if total_expenses > 0 else 0, 1)
        top_expense_category = {
            "category": top.get("_id", "N/D"),
            "total": cat_total,
            "percentage": cat_pct,
        }

    return {
        # Standard KPIData fields
        "total_sales": round(total_sales, 2),
        "total_expenses": round(total_expenses, 2),
        "net_cashflow": round(net_cashflow, 2),
        "avg_daily_sales": round(avg_daily_sales, 2),
        "avg_daily_expenses": round(avg_daily_expenses, 2),
        "sales_trend_pct": round(sales_trend, 1),
        "expenses_trend_pct": round(expenses_trend, 1),
        "cashflow_trend_pct": round(cashflow_trend, 1),
        "period_days": days_with_data,
        # Enriched fields
        "fixed_costs_total": fixed_costs_total,
        "combined_expenses": combined_expenses,
        "expense_ratio": expense_ratio,
        "burn_rate": round(avg_daily_expenses, 2),  # alias for clarity in UI
        "top_expense_category": top_expense_category,
    }


# ── v2.1: Cumulative Cashflow endpoint ────────────────────────────────────────

@router.get("/cashflow/cumulative")
async def get_cumulative_cashflow(
    period: str = Query("30d", regex="^(7d|30d|90d|custom|data_range)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Serie giornaliera con cashflow cumulativo.

    Ogni elemento: {date, sales, expenses, daily_net, cumulative}.
    Utile per grafici ad area che mostrano l'accumulo/erosione di cassa nel tempo.
    Restituisce [] se non ci sono dati.
    """
    org_doc = await _get_org_doc(current_user)
    await check_module_access(org_doc["id"], "cashflow_monitor", "analytics", org_doc=org_doc)
    org_id = current_user["organization_id"]
    start, end = get_date_range(period, start_date, end_date)
    return await analytics_repository.aggregate_cumulative_cashflow(org_id, start, end)


# ── Phase-3: KPI Snapshot endpoint ────────────────────────────────────────────
# Reads from pre-computed kpi_snapshots instead of running a live aggregation.
# Falls back to live data if no snapshot is found.

@router.get("/kpis/snapshot")
async def get_kpis_snapshot(
    module_key: str = Query("cashflow_monitor"),
    granularity: str = Query("monthly", regex="^(daily|weekly|monthly|quarterly)$"),
    limit: int = Query(12, le=24),
    current_user: dict = Depends(get_current_user),
):
    """Return pre-computed KPI snapshots.

    Faster than /kpis for dashboard widgets that don't need real-time data.
    Falls back to an empty list when no snapshots exist yet (trigger upload to populate).
    """
    org_doc = await _get_org_doc(current_user)
    await check_module_access(org_doc["id"], "cashflow_monitor", "analytics", org_doc=org_doc)
    from repositories.kpi_snapshot_repository import find_latest
    snapshots = await find_latest(
        current_user["organization_id"],
        module_key=module_key,
        limit=limit,
    )
    return {
        "module_key": module_key,
        "granularity": granularity,
        "snapshots": [
            {
                "period_start": s.period_start,
                "period_end": s.period_end,
                "metrics": s.metrics,
                "created_at": s.created_at.isoformat(),
                "schema_version": s.schema_version,
            }
            for s in snapshots
        ],
    }


# ── v4.0-D: Access status endpoint ──────────────────────────────────────────

@router.get("/cashflow/access-status")
async def cashflow_access_status(
    current_user: dict = Depends(get_current_user),
):
    """Return cashflow entitlements for the caller's org.

    Response: { "plan", "enabled", "period", "limits", "usage" }
    """
    org_doc = await _get_org_doc(current_user)
    return await build_module_access_status(org_doc["id"], "cashflow_monitor", org_doc=org_doc)
