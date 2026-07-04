from typing import List, Optional
from collections import defaultdict
from database import sales_records_collection, expense_records_collection, fixed_costs_collection, purchase_records_collection
from models import DailyAggregate
from datetime import datetime, timedelta


async def aggregate_sales_by_date(org_id: str, start_date: str, end_date: str) -> dict:
    """Aggregate sales by date"""
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$group": {
                "_id": "$date",
                "total": {"$sum": "$amount"}
            }
        }
    ]
    
    cursor = sales_records_collection.aggregate(pipeline)
    return {doc['_id']: doc['total'] async for doc in cursor}


async def aggregate_expenses_by_date(org_id: str, start_date: str, end_date: str) -> dict:
    """Aggregate expenses by date"""
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$group": {
                "_id": "$date",
                "total": {"$sum": "$amount"}
            }
        }
    ]
    
    cursor = expense_records_collection.aggregate(pipeline)
    return {doc['_id']: doc['total'] async for doc in cursor}


async def aggregate_sales_by_category(org_id: str, start_date: str, end_date: str) -> List[dict]:
    """Aggregate sales by category"""
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$group": {
                "_id": {"$ifNull": ["$category", "Uncategorized"]},
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"total": -1}}
    ]
    
    cursor = sales_records_collection.aggregate(pipeline)
    return await cursor.to_list(100)


async def aggregate_expenses_by_category(org_id: str, start_date: str, end_date: str) -> List[dict]:
    """Aggregate expenses by category"""
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$group": {
                "_id": {"$ifNull": ["$category", "Uncategorized"]},
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"total": -1}}
    ]
    
    cursor = expense_records_collection.aggregate(pipeline)
    return await cursor.to_list(100)


async def get_date_range(org_id: str) -> dict:
    """Get min/max dates for an organization's data"""
    sales_pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {
            "_id": None,
            "min_date": {"$min": "$date"},
            "max_date": {"$max": "$date"}
        }}
    ]
    
    expenses_pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {
            "_id": None,
            "min_date": {"$min": "$date"},
            "max_date": {"$max": "$date"}
        }}
    ]
    
    sales_result = await sales_records_collection.aggregate(sales_pipeline).to_list(1)
    expenses_result = await expense_records_collection.aggregate(expenses_pipeline).to_list(1)
    
    min_dates = []
    max_dates = []
    
    if sales_result and sales_result[0].get('min_date'):
        min_dates.append(sales_result[0]['min_date'])
        max_dates.append(sales_result[0]['max_date'])
    
    if expenses_result and expenses_result[0].get('min_date'):
        min_dates.append(expenses_result[0]['min_date'])
        max_dates.append(expenses_result[0]['max_date'])
    
    if not min_dates:
        return {"has_data": False, "min_date": None, "max_date": None}
    
    return {
        "has_data": True,
        "min_date": min(min_dates),
        "max_date": max(max_dates)
    }


async def get_analytics_date_range(org_id: str) -> dict:
    """Return the full date-range response shape for GET /analytics/date-range.

    Extends get_date_range() with ``days_of_data`` and ``suggested_period`` so
    the router does not need to perform any computation inline.

    Returns:
        dict with keys: has_data, min_date, max_date, days_of_data, suggested_period.
        Never raises — returns has_data=False on any error.
    """
    try:
        base = await get_date_range(org_id)

        if not base["has_data"]:
            return {
                "has_data": False,
                "min_date": None,
                "max_date": None,
                "days_of_data": 0,
                "suggested_period": "30d",
            }

        min_date: str = base["min_date"]
        max_date: str = base["max_date"]
        min_dt = datetime.strptime(min_date, "%Y-%m-%d")
        max_dt = datetime.strptime(max_date, "%Y-%m-%d")
        days_diff = (max_dt - min_dt).days + 1

        if days_diff <= 7:
            suggested = "7d"
        elif days_diff <= 30:
            suggested = "30d"
        else:
            suggested = "90d"

        return {
            "has_data": True,
            "min_date": min_date,
            "max_date": max_date,
            "days_of_data": days_diff,
            "suggested_period": suggested,
        }
    except Exception:
        return {
            "has_data": False,
            "min_date": None,
            "max_date": None,
            "days_of_data": 0,
            "suggested_period": "30d",
        }


async def aggregate_by_date_and_category(
    org_id: str,
    start_date: str,
    end_date: str,
    record_type: str = "sales"
) -> List[dict]:
    """Aggregate by date and category for trend charts"""
    collection = sales_records_collection if record_type == "sales" else expense_records_collection
    
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "date": "$date",
                    "category": {"$ifNull": ["$category", "Uncategorized"]}
                },
                "total": {"$sum": "$amount"}
            }
        },
        {"$sort": {"_id.date": 1}}
    ]
    
    cursor = collection.aggregate(pipeline)
    return await cursor.to_list(1000)


# ── v2.1 additions: Fixed Costs aggregation ───────────────────────────────────
# These functions are NEW and purely additive.
# No existing function above is modified.
#
# Fixed costs differ from sales/expense records: they have no per-row date
# stamp.  Instead they carry a frequency (monthly / weekly / quarterly /
# annual / one_off) and an optional validity window (start_date … end_date).
# All three functions below prorate amounts to the requested date range using
# that frequency, and silently return 0 / [] on any error so that callers
# (especially fire-and-forget snapshot computation) are never interrupted.

_FREQUENCY_DAYS: dict = {
    "monthly": 30,
    "weekly": 7,
    "quarterly": 90,
    "annual": 365,
}


def _prorate(amount: float, frequency: str, period_days: int, cost_start_str: Optional[str],
             range_start: "datetime.date", range_end: "datetime.date",
             cost_end_str: Optional[str] = None) -> float:
    """Return the portion of *amount* that falls within the OVERLAP of
    the cost's validity window and the requested [range_start, range_end].

    Wave 14.HOTFIX3 (2026-05-16) — pre-fix the function ignored
    ``cost_start_str`` and ``cost_end_str`` for recurring frequencies
    and just used ``period_days`` flat, so a cost that ended in the
    middle of the period (e.g. "Finanziament Attività 3" with
    end_date=2026-02-28 vs a YTD 2026 query running to May 16) was
    charged for the FULL period instead of only its active portion.
    The bug surfaced as: AI reporting identical fixed_costs for
    YTD 2026 vs YTD 2025, while the user knew a financing had ended
    in Feb 2026 and the YTD 2026 figure should be lower.

    For one_off costs the full amount is included only when the
    cost's start_date lies inside the requested date range
    (unchanged behaviour).

    For recurring costs (monthly / weekly / quarterly / annual /
    default), the function:
      1. Computes the OVERLAP days between [cost_start, cost_end]
         and [range_start, range_end] — both bounds INCLUSIVE.
      2. Returns ``amount * (overlap_days / divisor)`` where divisor
         depends on frequency (30 days/month etc.).
      3. Returns 0.0 if there is no overlap.

    cost_start_str defaulting to None preserves the legacy semantics
    "cost was always active" (pre-13.0 fixed_costs that have no
    start_date). cost_end_str=None means open-ended — the cost is
    active up to the end of the query range.
    """
    if frequency == "one_off":
        if cost_start_str:
            try:
                cs = datetime.strptime(cost_start_str, "%Y-%m-%d").date()
                return float(amount) if range_start <= cs <= range_end else 0.0
            except ValueError:
                return 0.0
        return 0.0

    # Recurring: clamp the cost's validity window to the query range
    # and use the OVERLAP for proration.
    effective_start = range_start
    effective_end = range_end

    if cost_start_str:
        try:
            cs = datetime.strptime(cost_start_str, "%Y-%m-%d").date()
            if cs > effective_start:
                effective_start = cs
        except ValueError:
            pass

    if cost_end_str:
        try:
            ce = datetime.strptime(cost_end_str, "%Y-%m-%d").date()
            if ce < effective_end:
                effective_end = ce
        except ValueError:
            pass

    overlap_days = (effective_end - effective_start).days + 1
    if overlap_days <= 0:
        return 0.0

    # Safety cap — never report more than the full period (defensive
    # in case input dates are pathological).
    if overlap_days > period_days:
        overlap_days = period_days

    divisor = _FREQUENCY_DAYS.get(frequency, 30)
    return float(amount) * (overlap_days / divisor)


def _cost_overlaps_period(doc: dict, range_start: "datetime.date",
                           range_end: "datetime.date") -> bool:
    """Return True when the cost's validity window overlaps [range_start, range_end]."""
    cost_start = doc.get("start_date")
    cost_end = doc.get("end_date")
    if cost_start:
        try:
            if datetime.strptime(cost_start, "%Y-%m-%d").date() > range_end:
                return False  # cost starts after the period ends
        except ValueError:
            pass
    if cost_end:
        try:
            if datetime.strptime(cost_end, "%Y-%m-%d").date() < range_start:
                return False  # cost ended before the period started
        except ValueError:
            pass
    return True


async def aggregate_fixed_costs_total(org_id: str, start_date: str, end_date: str) -> float:
    """Return total fixed-cost burden prorated to [start_date, end_date].

    Only active costs whose validity window overlaps the period are included.
    Returns 0.0 on any error — never raises.

    Output shape: a single float (rounded to 2 decimals).
    Compatible with: kpi_snapshot_service._compute_cashflow_kpis() (v2.1+).
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        period_days = (end_dt - start_dt).days + 1
        if period_days <= 0:
            return 0.0

        docs = await fixed_costs_collection.find(
            {"organization_id": org_id, "is_active": True},
            {"_id": 0},
        ).to_list(1000)

        total = 0.0
        for doc in docs:
            if not _cost_overlaps_period(doc, start_dt, end_dt):
                continue
            amount = float(doc.get("amount") or 0)
            frequency = doc.get("frequency") or "monthly"
            # Wave 14.HOTFIX3 — pass cost_end_str so terminated costs
            # are prorated only for their active days within the range.
            total += _prorate(
                amount, frequency, period_days,
                doc.get("start_date"), start_dt, end_dt,
                doc.get("end_date"),
            )

        return round(total, 2)

    except Exception:
        return 0.0


async def aggregate_fixed_costs_detail(
    org_id: str, start_date: str, end_date: str,
) -> List[dict]:
    """Return per-cost-item detail for fixed costs in [start, end].

    Wave 14.HOTFIX4 (F2) — pre-HOTFIX4 the AI had only
    ``aggregate_fixed_costs_total`` (a scalar) and
    ``aggregate_fixed_costs_by_category`` (aggregated by category).
    Neither could answer "Att.3 ended Feb 28 — how much did it
    contribute to YTD 2026 vs YTD 2025?". This function returns
    every cost item with name, monthly amount, days active in the
    period, prorated contribution, and a ``terminated_in_period``
    flag.

    Output is a list of dicts:
        [{
          "name": str,                       # e.g. "Finanziament Attività 3"
          "category": str,                   # e.g. "finanziamento"
          "monthly_amount": float,           # nominal monthly amount
          "frequency": str,                  # "mensile" | "monthly" | ...
          "validity_start": str | None,      # YYYY-MM-DD or None (always-on)
          "validity_end": str | None,        # YYYY-MM-DD or None (open-ended)
          "days_active_in_period": int,      # overlap days, 0 if no overlap
          "days_in_period": int,             # total days in the query range
          "prorated_contribution": float,    # actual contribution in EUR
          "terminated_in_period": bool,      # True iff cost's end_date
                                              # falls inside the query window
        }, ...]

    Sorted by prorated_contribution descending (biggest first).
    Returns [] on any error.
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        period_days = (end_dt - start_dt).days + 1
        if period_days <= 0:
            return []

        docs = await fixed_costs_collection.find(
            {"organization_id": org_id, "is_active": True},
            {"_id": 0},
        ).to_list(1000)

        items: list = []
        for doc in docs:
            if not _cost_overlaps_period(doc, start_dt, end_dt):
                # Cost doesn't overlap at all — skip
                continue

            amount = float(doc.get("amount") or 0)
            frequency = doc.get("frequency") or "monthly"
            cost_start_str = doc.get("start_date")
            cost_end_str = doc.get("end_date")

            # Compute overlap days (same logic as _prorate post-HOTFIX3)
            effective_start = start_dt
            effective_end = end_dt
            if cost_start_str:
                try:
                    cs = datetime.strptime(cost_start_str, "%Y-%m-%d").date()
                    if cs > effective_start:
                        effective_start = cs
                except ValueError:
                    pass
            if cost_end_str:
                try:
                    ce = datetime.strptime(cost_end_str, "%Y-%m-%d").date()
                    if ce < effective_end:
                        effective_end = ce
                except ValueError:
                    pass
            days_active = max(0, (effective_end - effective_start).days + 1)

            # Terminated within the query window — important signal for
            # the AI ("Att.3 ended Feb 28, only 59/136 days active")
            terminated_in_period = False
            if cost_end_str:
                try:
                    ce = datetime.strptime(cost_end_str, "%Y-%m-%d").date()
                    terminated_in_period = start_dt <= ce <= end_dt
                except ValueError:
                    pass

            prorated = _prorate(
                amount, frequency, period_days,
                cost_start_str, start_dt, end_dt, cost_end_str,
            )

            items.append({
                "name": doc.get("name", ""),
                "category": doc.get("category", "Uncategorized"),
                "monthly_amount": round(amount, 2),
                "frequency": frequency,
                "validity_start": cost_start_str,
                "validity_end": cost_end_str,
                "days_active_in_period": days_active,
                "days_in_period": period_days,
                "prorated_contribution": round(prorated, 2),
                "terminated_in_period": terminated_in_period,
            })

        items.sort(key=lambda d: d["prorated_contribution"], reverse=True)
        return items

    except Exception:
        return []


async def aggregate_fixed_costs_by_category(
    org_id: str, start_date: str, end_date: str
) -> List[dict]:
    """Return active fixed costs grouped by category for [start_date, end_date].

    Amounts are prorated to the period length using the same logic as
    aggregate_fixed_costs_total().

    Output shape matches aggregate_expenses_by_category():
        [{"_id": "<category>", "total": <prorated_float>, "count": <int>}, ...]
    Sorted by total descending.
    Returns [] on any error — never raises.
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        period_days = (end_dt - start_dt).days + 1
        if period_days <= 0:
            return []

        docs = await fixed_costs_collection.find(
            {"organization_id": org_id, "is_active": True},
            {"_id": 0},
        ).to_list(1000)

        buckets: dict = defaultdict(lambda: {"total": 0.0, "count": 0})
        for doc in docs:
            if not _cost_overlaps_period(doc, start_dt, end_dt):
                continue
            amount = float(doc.get("amount") or 0)
            frequency = doc.get("frequency") or "monthly"
            category = doc.get("category") or "Uncategorized"
            # Wave 14.HOTFIX3 — pass cost_end_str so a financing that
            # ended mid-period is not double-counted.
            prorated = _prorate(
                amount, frequency, period_days,
                doc.get("start_date"), start_dt, end_dt,
                doc.get("end_date"),
            )
            buckets[category]["total"] += prorated
            buckets[category]["count"] += 1

        result = [
            {"_id": cat, "total": round(data["total"], 2), "count": data["count"]}
            for cat, data in buckets.items()
        ]
        result.sort(key=lambda x: x["total"], reverse=True)
        return result

    except Exception:
        return []


async def aggregate_expenses_with_fixed_costs(
    org_id: str, start_date: str, end_date: str
) -> dict:
    """Convenience function: combined view of expense_records + fixed_costs.

    Does NOT replace any existing function.  Callers can use this for richer
    analytics without touching the existing aggregation pipelines.

    Output shape:
        {
            "expense_records_total": float,   # from expense_records collection
            "fixed_costs_total":     float,   # prorated from fixed_costs collection
            "combined_total":        float,   # sum of the two
        }
    Returns all zeros on any error — never raises.
    """
    try:
        expense_records_total = round(
            sum((await aggregate_expenses_by_date(org_id, start_date, end_date)).values()), 2
        )
        fixed_costs_total = await aggregate_fixed_costs_total(org_id, start_date, end_date)
        return {
            "expense_records_total": expense_records_total,
            "fixed_costs_total": fixed_costs_total,
            "combined_total": round(expense_records_total + fixed_costs_total, 2),
        }
    except Exception:
        return {"expense_records_total": 0.0, "fixed_costs_total": 0.0, "combined_total": 0.0}


# ── v2.1 additions: Cashflow Monitor enriched metrics ─────────────────────────
# These two functions power the /analytics/cashflow/enriched-kpis and
# /analytics/cashflow/cumulative endpoints introduced in the v2 module plan.
# Both are purely additive — no existing function is modified.


async def aggregate_expense_ratio(org_id: str, start_date: str, end_date: str) -> float:
    """Return total_expenses / total_sales × 100 for the given period.

    Useful as a single-number health check: < 80% is healthy, > 100% means
    the business is spending more than it earns.
    Returns 0.0 when sales are zero or on any error — never raises.
    """
    try:
        sales_pipeline = [
            {"$match": {"organization_id": org_id, "date": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        expenses_pipeline = [
            {"$match": {"organization_id": org_id, "date": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        sales_res = await sales_records_collection.aggregate(sales_pipeline).to_list(1)
        expenses_res = await expense_records_collection.aggregate(expenses_pipeline).to_list(1)

        total_sales = sales_res[0]["total"] if sales_res else 0.0
        total_expenses = expenses_res[0]["total"] if expenses_res else 0.0

        if total_sales <= 0:
            return 0.0
        return round((total_expenses / total_sales) * 100, 1)

    except Exception:
        return 0.0


async def aggregate_cumulative_cashflow(
    org_id: str, start_date: str, end_date: str
) -> List[dict]:
    """Return a day-by-day list with daily and running cumulative cashflow.

    Each element: {"date": "YYYY-MM-DD", "sales": float, "expenses": float,
                   "daily_net": float, "cumulative": float}
    Sorted by date ascending.  Missing days (no data) are skipped rather than
    filled with zeros to keep the payload small.
    Returns [] on any error — never raises.
    """
    try:
        sales_by_date = await aggregate_sales_by_date(org_id, start_date, end_date)
        expenses_by_date = await aggregate_expenses_by_date(org_id, start_date, end_date)

        all_dates = sorted(set(sales_by_date.keys()) | set(expenses_by_date.keys()))
        if not all_dates:
            return []

        result = []
        running = 0.0
        for date in all_dates:
            s = round(sales_by_date.get(date, 0.0), 2)
            e = round(expenses_by_date.get(date, 0.0), 2)
            daily_net = round(s - e, 2)
            running = round(running + daily_net, 2)
            result.append({
                "date": date,
                "sales": s,
                "expenses": e,
                "daily_net": daily_net,
                "cumulative": running,
            })
        return result

    except Exception:
        return []


# ── v2.2 additions: Purchase Records aggregation ──────────────────────────────
# Additive only — no existing function is modified.
#
# purchase_records stores monetary amounts in 'amount' (Pydantic model, manual
# entry) or 'total_price' (CSV legacy import path).  Both aggregations use
# $ifNull to handle either field transparently so callers are insulated from
# the storage-layer inconsistency.
# All functions return empty collections on any error — never raise.


async def aggregate_purchases_by_date(
    org_id: str, start_date: str, end_date: str
) -> dict:
    """Aggregate purchase records by date. Returns {date: total} dict.

    Handles both 'amount' (Pydantic model) and 'total_price' (CSV legacy)
    field names via $ifNull fallback.
    Returns {} on any error — never raises.
    """
    try:
        pipeline = [
            {
                "$match": {
                    "organization_id": org_id,
                    "date": {"$gte": start_date, "$lte": end_date},
                }
            },
            {
                "$group": {
                    "_id": "$date",
                    "total": {
                        "$sum": {
                            "$ifNull": [
                                "$total_with_iva",
                                {"$ifNull": [
                                    "$amount",
                                    {"$ifNull": ["$total_price", 0]},
                                ]},
                            ]
                        }
                    },
                }
            },
        ]
        cursor = purchase_records_collection.aggregate(pipeline)
        return {doc["_id"]: doc["total"] async for doc in cursor}
    except Exception:
        return {}


async def aggregate_purchases_by_supplier(
    org_id: str, start_date: str, end_date: str,
) -> List[dict]:
    """Aggregate purchases grouped by supplier_name for the given period.

    Output shape matches aggregate_expenses_by_category():
        [{"_id": "<supplier_name>", "total": float, "count": int}, ...]
    Sorted by total descending.
    Returns [] on any error — never raises.
    """
    try:
        pipeline = [
            {
                "$match": {
                    "organization_id": org_id,
                    "date": {"$gte": start_date, "$lte": end_date},
                }
            },
            {
                "$group": {
                    "_id": {"$ifNull": ["$supplier_name", "Sconosciuto"]},
                    "total": {
                        "$sum": {
                            "$ifNull": [
                                "$total_with_iva",
                                {"$ifNull": [
                                    "$amount",
                                    {"$ifNull": ["$total_price", 0]},
                                ]},
                            ]
                        }
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"total": -1}},
        ]
        cursor = purchase_records_collection.aggregate(pipeline)
        return await cursor.to_list(100)
    except Exception:
        return []


async def aggregate_purchases_by_product(
    org_id: str, start_date: str, end_date: str,
) -> List[dict]:
    """Aggregate purchases grouped by product (category field) for Pareto analysis.

    Uses effective_total (Wave B coalesce: total_with_iva → amount → total_price).
    Sorted by total descending.  Returns [] on any error.
    """
    try:
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date},
            }},
            {"$group": {
                "_id": {"$ifNull": ["$category", "Senza prodotto"]},
                "total": {"$sum": {
                    "$ifNull": [
                        "$total_with_iva",
                        {"$ifNull": ["$amount", {"$ifNull": ["$total_price", 0]}]},
                    ]
                }},
                "count": {"$sum": 1},
            }},
            {"$sort": {"total": -1}},
        ]
        cursor = purchase_records_collection.aggregate(pipeline)
        return await cursor.to_list(100)
    except Exception:
        return []


async def aggregate_purchases_by_category_macro(
    org_id: str, start_date: str, end_date: str,
) -> List[dict]:
    """Aggregate purchases grouped by category_macro for Pareto analysis.

    Uses effective_total (Wave B coalesce: total_with_iva → amount → total_price).
    Excludes records without category_macro (null/missing).
    Sorted by total descending.  Returns [] on any error.
    """
    try:
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date},
                "category_macro": {"$exists": True, "$ne": None},
            }},
            {"$group": {
                "_id": "$category_macro",
                "total": {"$sum": {
                    "$ifNull": [
                        "$total_with_iva",
                        {"$ifNull": ["$amount", {"$ifNull": ["$total_price", 0]}]},
                    ]
                }},
                "count": {"$sum": 1},
            }},
            {"$sort": {"total": -1}},
        ]
        cursor = purchase_records_collection.aggregate(pipeline)
        return await cursor.to_list(100)
    except Exception:
        return []


# ── v2.4 additions: Scadenzario aggregations ────────────────────────────────
# All functions are purely additive, async, and never raise.


async def aggregate_open_receivables(org_id: str) -> float:
    """Total unpaid sales where payment_status is explicitly set to a non-paid value.
    Records with null/missing payment_status are EXCLUDED to avoid false positives.
    Returns 0.0 on error — never raises.
    """
    try:
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "payment_status": {"$exists": True, "$ne": None, "$nin": ["paid"]},
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        result = await sales_records_collection.aggregate(pipeline).to_list(1)
        return round(result[0]["total"], 2) if result else 0.0
    except Exception:
        return 0.0


async def aggregate_open_payables(org_id: str) -> float:
    """Total unpaid purchases where payment_status is explicitly set to a non-paid value.
    Records with null/missing payment_status are EXCLUDED to avoid false positives.
    Returns 0.0 on error — never raises.
    """
    try:
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "payment_status": {"$exists": True, "$ne": None, "$nin": ["paid"]},
            }},
            {"$group": {
                "_id": None,
                "total": {"$sum": {
                    "$ifNull": ["$total_with_iva", {"$ifNull": ["$amount", {"$ifNull": ["$total_price", 0]}]}]
                }},
            }},
        ]
        result = await purchase_records_collection.aggregate(pipeline).to_list(1)
        return round(result[0]["total"], 2) if result else 0.0
    except Exception:
        return 0.0


async def aggregate_receivables_by_aging(org_id: str) -> list:
    """Bucket unpaid sales by aging from due_date.
    Buckets: 0-30, 31-60, 61-90, >90 days.
    Returns [{"bucket": str, "total": float, "count": int}].
    Pure MongoDB aggregation — no Python-side loop.
    Returns [] on error — never raises.
    """
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "payment_status": {"$nin": ["paid"]},
                "due_date": {"$exists": True, "$ne": None},
            }},
            {"$addFields": {
                "_days_overdue": {
                    "$divide": [
                        {"$subtract": [
                            {"$dateFromString": {"dateString": today_str, "format": "%Y-%m-%d"}},
                            {"$dateFromString": {"dateString": "$due_date", "format": "%Y-%m-%d",
                                                  "onError": {"$dateFromString": {"dateString": today_str}}}},
                        ]},
                        86400000,  # ms → days
                    ]
                },
            }},
            {"$addFields": {
                "_bucket": {"$switch": {
                    "branches": [
                        {"case": {"$lte": ["$_days_overdue", 30]}, "then": "0-30"},
                        {"case": {"$lte": ["$_days_overdue", 60]}, "then": "31-60"},
                        {"case": {"$lte": ["$_days_overdue", 90]}, "then": "61-90"},
                    ],
                    "default": ">90",
                }},
            }},
            {"$group": {
                "_id": "$_bucket",
                "total": {"$sum": {"$ifNull": [{"$toDouble": "$amount"}, 0]}},
                "count": {"$sum": 1},
            }},
        ]
        result = []
        async for doc in sales_records_collection.aggregate(pipeline):
            result.append({
                "bucket": doc["_id"],
                "total": round(doc["total"], 2),
                "count": doc["count"],
            })
        return result
    except Exception:
        return []


async def aggregate_payables_by_aging(org_id: str) -> list:
    """Same as receivables aging but for purchase_records.
    Returns [{"bucket": str, "total": float, "count": int}].
    Pure MongoDB aggregation — no Python-side loop.
    Uses total_with_iva if present, otherwise falls back to total_price / amount.
    Returns [] on error — never raises.
    """
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "payment_status": {"$nin": ["paid"]},
                "due_date": {"$exists": True, "$ne": None},
            }},
            {"$addFields": {
                "_days_overdue": {
                    "$divide": [
                        {"$subtract": [
                            {"$dateFromString": {"dateString": today_str, "format": "%Y-%m-%d"}},
                            {"$dateFromString": {"dateString": "$due_date", "format": "%Y-%m-%d",
                                                  "onError": {"$dateFromString": {"dateString": today_str}}}},
                        ]},
                        86400000,
                    ]
                },
                "_amt": {"$ifNull": [
                    {"$toDouble": "$total_with_iva"},
                    {"$ifNull": [
                        {"$toDouble": "$total_price"},
                        {"$ifNull": [{"$toDouble": "$amount"}, 0]},
                    ]},
                ]},
            }},
            {"$addFields": {
                "_bucket": {"$switch": {
                    "branches": [
                        {"case": {"$lte": ["$_days_overdue", 30]}, "then": "0-30"},
                        {"case": {"$lte": ["$_days_overdue", 60]}, "then": "31-60"},
                        {"case": {"$lte": ["$_days_overdue", 90]}, "then": "61-90"},
                    ],
                    "default": ">90",
                }},
            }},
            {"$group": {
                "_id": "$_bucket",
                "total": {"$sum": "$_amt"},
                "count": {"$sum": 1},
            }},
        ]
        result = []
        async for doc in purchase_records_collection.aggregate(pipeline):
            result.append({
                "bucket": doc["_id"],
                "total": round(doc["total"], 2),
                "count": doc["count"],
            })
        return result
    except Exception:
        return []


async def aggregate_upcoming_receivables(org_id: str, days: int = 60) -> list:
    """Expected inflows by due_date within next N days.
    Returns [{"date": str, "total": float}] sorted by date.
    Returns [] on error — never raises.
    """
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        future_str = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "payment_status": {"$nin": ["paid"]},
                "due_date": {"$gte": today_str, "$lte": future_str},
            }},
            {"$group": {
                "_id": "$due_date",
                "total": {"$sum": "$amount"},
            }},
            {"$sort": {"_id": 1}},
        ]
        cursor = sales_records_collection.aggregate(pipeline)
        return [{"date": doc["_id"], "total": round(doc["total"], 2)} async for doc in cursor]
    except Exception:
        return []


async def aggregate_upcoming_payables(org_id: str, days: int = 60) -> list:
    """Expected outflows by due_date within next N days.
    Returns [{"date": str, "total": float}] sorted by date.
    Returns [] on error — never raises.
    """
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        future_str = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "payment_status": {"$nin": ["paid"]},
                "due_date": {"$gte": today_str, "$lte": future_str},
            }},
            {"$group": {
                "_id": "$due_date",
                "total": {"$sum": {
                    "$ifNull": ["$total_with_iva", {"$ifNull": ["$amount", {"$ifNull": ["$total_price", 0]}]}]
                }},
            }},
            {"$sort": {"_id": 1}},
        ]
        cursor = purchase_records_collection.aggregate(pipeline)
        return [{"date": doc["_id"], "total": round(doc["total"], 2)} async for doc in cursor]
    except Exception:
        return []


# ── v4.0: Period-aware customer aggregations ──────────────────────────────────
# These query sales_records directly (same collection as cashflow revenue) but
# group by customer_id.  This enables temporally aligned cross-module reasoning.
# All functions return empty collections on error — never raise.


async def aggregate_customers_by_revenue_period(
    org_id: str, start_date: str, end_date: str, limit: int = 20,
) -> List[dict]:
    """Top customers by revenue for a specific date range.

    Reads from sales_records (same as cashflow total_sales), grouped by
    customer_id.  Only records with a non-null customer_id are included.

    Returns: [{"customer_id", "customer_name", "total_revenue", "transaction_count",
               "revenue_share_pct", "first_date", "last_date"}]
    Sorted by total_revenue descending.  Returns [] on error.
    """
    try:
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date},
                "customer_id": {"$ne": None, "$exists": True},
            }},
            {"$group": {
                "_id": "$customer_id",
                "customer_name": {"$first": {"$ifNull": ["$customer_name", "$customer_id"]}},
                "total_revenue": {"$sum": "$amount"},
                "transaction_count": {"$sum": 1},
                "first_date": {"$min": "$date"},
                "last_date": {"$max": "$date"},
            }},
            {"$sort": {"total_revenue": -1}},
            {"$limit": limit},
        ]
        cursor = sales_records_collection.aggregate(pipeline)
        results = await cursor.to_list(limit)

        # Compute share percentages
        total = sum(r["total_revenue"] for r in results)
        return [
            {
                "customer_id": r["_id"],
                "customer_name": r["customer_name"],
                "total_revenue": round(r["total_revenue"], 2),
                "transaction_count": r["transaction_count"],
                "revenue_share_pct": round((r["total_revenue"] / total * 100) if total > 0 else 0, 1),
                "first_date": r["first_date"],
                "last_date": r["last_date"],
            }
            for r in results
        ]
    except Exception:
        return []


async def aggregate_customer_concentration_period(
    org_id: str, start_date: str, end_date: str, top_n: int = 5,
) -> dict:
    """Customer concentration for a specific date range.

    Returns: {
        "total_customers": int,
        "total_revenue": float,
        "top_n": int,
        "top_n_revenue": float,
        "top_n_share_pct": float,
        "has_customer_data": bool,
        "top_customers": [{"customer_id", "customer_name", "revenue", "share_pct"}]
    }
    Returns a "no data" response on error — never raises.
    """
    try:
        # Count total customers with data in this period
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date},
                "customer_id": {"$ne": None, "$exists": True},
            }},
            {"$group": {
                "_id": "$customer_id",
                "customer_name": {"$first": {"$ifNull": ["$customer_name", "$customer_id"]}},
                "total": {"$sum": "$amount"},
            }},
            {"$sort": {"total": -1}},
        ]
        cursor = sales_records_collection.aggregate(pipeline)
        all_customers = await cursor.to_list(5000)

        if not all_customers:
            return {
                "total_customers": 0,
                "total_revenue": 0.0,
                "top_n": top_n,
                "top_n_revenue": 0.0,
                "top_n_share_pct": 0.0,
                "has_customer_data": False,
                "top_customers": [],
            }

        total_revenue = sum(c["total"] for c in all_customers)
        top = all_customers[:top_n]
        top_revenue = sum(c["total"] for c in top)
        top_share = round((top_revenue / total_revenue * 100) if total_revenue > 0 else 0, 1)

        return {
            "total_customers": len(all_customers),
            "total_revenue": round(total_revenue, 2),
            "top_n": top_n,
            "top_n_revenue": round(top_revenue, 2),
            "top_n_share_pct": top_share,
            "has_customer_data": True,
            "top_customers": [
                {
                    "customer_id": c["_id"],
                    "customer_name": c["customer_name"],
                    "revenue": round(c["total"], 2),
                    "share_pct": round((c["total"] / total_revenue * 100) if total_revenue > 0 else 0, 1),
                }
                for c in top
            ],
        }
    except Exception:
        return {
            "total_customers": 0, "total_revenue": 0.0, "top_n": top_n,
            "top_n_revenue": 0.0, "top_n_share_pct": 0.0,
            "has_customer_data": False, "top_customers": [],
        }


async def count_sales_with_customer_id(org_id: str, start_date: str, end_date: str) -> dict:
    """Count how many sales records have customer_id populated vs total.

    Returns: {"total_records": int, "with_customer_id": int, "coverage_pct": float}
    Used for data-quality assessment of customer-level analysis.
    """
    try:
        total = await sales_records_collection.count_documents({
            "organization_id": org_id,
            "date": {"$gte": start_date, "$lte": end_date},
        })
        with_cid = await sales_records_collection.count_documents({
            "organization_id": org_id,
            "date": {"$gte": start_date, "$lte": end_date},
            "customer_id": {"$ne": None, "$exists": True},
        })
        return {
            "total_records": total,
            "with_customer_id": with_cid,
            "coverage_pct": round((with_cid / total * 100) if total > 0 else 0, 1),
        }
    except Exception:
        return {"total_records": 0, "with_customer_id": 0, "coverage_pct": 0.0}


async def count_sales_with_due_date(org_id: str, start_date: str, end_date: str) -> dict:
    """Count how many sales records have ``due_date`` populated vs total.

    Returns ``{"total_records": int, "with_due_date": int, "coverage_pct": float}``.

    Used by Pillar 1's data-quality gate (``@requires_data`` decorator) to
    suppress C1 (dso_worsening_trend) and C2 (high_risk_invoice) when too
    few records carry a ``due_date`` — those rules are meaningless without
    it. Without this metric the snapshot defaults coverage to 0 and the
    rules would never fire even on perfectly-populated data (the bug we
    discovered during the Pillar 2 smoke E2E).
    """
    try:
        total = await sales_records_collection.count_documents({
            "organization_id": org_id,
            "date": {"$gte": start_date, "$lte": end_date},
        })
        with_due = await sales_records_collection.count_documents({
            "organization_id": org_id,
            "date": {"$gte": start_date, "$lte": end_date},
            "due_date": {"$ne": None, "$exists": True},
        })
        return {
            "total_records": total,
            "with_due_date": with_due,
            "coverage_pct": round((with_due / total * 100) if total > 0 else 0, 1),
        }
    except Exception:
        return {"total_records": 0, "with_due_date": 0, "coverage_pct": 0.0}


async def count_sales_with_payment_status(org_id: str, start_date: str, end_date: str) -> dict:
    """Count how many sales records have ``payment_status`` populated.

    Same pattern as :func:`count_sales_with_due_date` — feeds the
    Pillar 1 data-quality snapshot so rules can declare a
    ``min_field_coverage={"payment_status": N}`` constraint that
    actually evaluates instead of always seeing 0.
    """
    try:
        total = await sales_records_collection.count_documents({
            "organization_id": org_id,
            "date": {"$gte": start_date, "$lte": end_date},
        })
        with_ps = await sales_records_collection.count_documents({
            "organization_id": org_id,
            "date": {"$gte": start_date, "$lte": end_date},
            "payment_status": {"$ne": None, "$exists": True},
        })
        return {
            "total_records": total,
            "with_payment_status": with_ps,
            "coverage_pct": round((with_ps / total * 100) if total > 0 else 0, 1),
        }
    except Exception:
        return {"total_records": 0, "with_payment_status": 0, "coverage_pct": 0.0}


# ── v14.2 Pillar 2 — monthly category timeline for statistical anomaly detection ──
#
# Used by rules B2/B4/C1 (refactored to use median-ratio anomaly detection
# instead of spot 30d-vs-30d comparison). Returns a chronologically-ordered
# list of monthly totals per category, including months with zero spending
# (the zeros are signal — they tell us whether the category is monthly,
# bimonthly, quarterly, …).
#
# Lives next to the per-category aggregators so the schema/index assumptions
# stay co-located. The MongoDB pipeline uses a $project to extract the year-
# month prefix from the date string (ISO yyyy-mm-dd), then groups by that
# prefix. We keep it pure — no defaults, no None handling: callers decide
# whether to skip or fill missing months.

async def aggregate_expenses_by_category_monthly(
    org_id: str, start_date: str, end_date: str,
) -> dict:
    """Return ``{category: {yyyy_mm: total}}`` for the given window.

    Caller normally wants this for ~12 months ending today. The result
    is a dict-of-dicts: outer key is the category name (or "Uncategorized"
    when the field is null), inner key is the year-month string, inner
    value is the sum of ``amount`` for that month and category.

    Caller is responsible for backfilling missing months with 0.0 — the
    ``monthly_totals_from_daily`` helper in
    ``modules.cashflow_monitor.statistical_significance`` does that for
    daily data; for category data the rule does it inline because the
    list of categories is dynamic.
    """
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date},
            }
        },
        {
            "$project": {
                "category": {"$ifNull": ["$category", "Uncategorized"]},
                "amount": 1,
                "year_month": {"$substr": ["$date", 0, 7]},  # yyyy-mm
            }
        },
        {
            "$group": {
                "_id": {"category": "$category", "year_month": "$year_month"},
                "total": {"$sum": "$amount"},
            }
        },
    ]
    cursor = expense_records_collection.aggregate(pipeline)
    out: dict = {}
    async for doc in cursor:
        cat = doc["_id"]["category"]
        ym = doc["_id"]["year_month"]
        out.setdefault(cat, {})[ym] = round(doc["total"], 2)
    return out


async def aggregate_purchases_by_supplier_monthly(
    org_id: str, start_date: str, end_date: str,
) -> dict:
    """Return ``{supplier_name: {yyyy_mm: total}}`` for the given window.

    Mirror of ``aggregate_expenses_by_category_monthly`` but for the
    purchases collection. Used by B2 unit_cost_increase to compare each
    supplier's monthly spend against its own historical baseline (rather
    than the org-wide one which can mask category-specific shifts).

    The ``supplier_name`` field is preserved verbatim — no normalisation
    here. Callers that need merging across variants (e.g. "ENEL spa" vs
    "Enel SPA") should do it at consume time.
    """
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "date": {"$gte": start_date, "$lte": end_date},
            }
        },
        {
            "$project": {
                "supplier_name": {"$ifNull": ["$supplier_name", "Unknown"]},
                "amount": 1,
                "year_month": {"$substr": ["$date", 0, 7]},
            }
        },
        {
            "$group": {
                "_id": {"supplier": "$supplier_name", "year_month": "$year_month"},
                "total": {"$sum": "$amount"},
            }
        },
    ]
    cursor = purchase_records_collection.aggregate(pipeline)
    out: dict = {}
    async for doc in cursor:
        sup = doc["_id"]["supplier"]
        ym = doc["_id"]["year_month"]
        out.setdefault(sup, {})[ym] = round(doc["total"], 2)
    return out
