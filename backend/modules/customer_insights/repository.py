"""Repository layer for Customer Insights.

Reads-only: this module never writes to ``customer_metrics`` (that's the
legacy ``customers_light.repository`` job, kept as the single writer to
avoid divergence). All persistence is on ``audit_logs`` for action
tracking and on ``customer_tasks`` for the Phase 4 task system.

We split the reads into:

  • Period-aware queries — return data scoped to a ``PeriodWindow``.
    Every endpoint that supports the period selector goes through here.
  • Cohort source data — fetch the raw "customer → list of purchase dates"
    map that ``cohort.build_cohort_table`` consumes.
  • Customer timeline — combined orders + sales records for the slide-over
    drill-down.
  • Action log — read recent outreach actions for a customer (used by
    the smart-suggestions panel to dedupe "already contacted today").

All functions are async and tolerate empty results gracefully.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Iterable, Optional

from .period_filter import PeriodWindow

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Period-aware reads
# ──────────────────────────────────────────────────────────────────────────────


async def aggregate_revenue_in_period(
    org_id: str,
    window: PeriodWindow,
) -> list[dict]:
    """Sum revenue per customer over a window.

    Returns the same shape as the legacy ``aggregate_revenue_by_customer``
    but with ``date`` constrained to ``window``. Used by the period-aware
    overview to compute "revenue in the last 30 days vs the previous 30".

    Returns ``[]`` on any error (logged, never raised) so the endpoint
    can degrade to "no data for this window" instead of 500-ing.
    """
    from database import sales_records_collection

    try:
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "customer_id": {"$ne": None, "$exists": True},
                "date": {"$gte": window.start_iso, "$lte": window.end_iso},
            }},
            {"$group": {
                "_id": "$customer_id",
                "total_revenue": {"$sum": "$amount"},
                "count": {"$sum": 1},
                "first_date": {"$min": "$date"},
                "last_date": {"$max": "$date"},
            }},
            {"$sort": {"total_revenue": -1}},
        ]
        cursor = sales_records_collection.aggregate(pipeline)
        return await cursor.to_list(5000)
    except Exception as exc:
        logger.error(
            "customer_insights.repo: aggregate_revenue_in_period failed: %s",
            exc,
        )
        return []


async def count_new_customers_in_period(
    org_id: str,
    window: PeriodWindow,
) -> int:
    """Number of customers whose *first ever purchase* falls in the window.

    Important: we don't just count customers who purchased in the window
    — we count those for whom this window contains their first purchase
    across all time. That's the "new customers acquired this month" KPI.
    """
    from database import sales_records_collection

    try:
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "customer_id": {"$ne": None, "$exists": True},
            }},
            {"$group": {
                "_id": "$customer_id",
                "first_date": {"$min": "$date"},
            }},
            {"$match": {
                "first_date": {"$gte": window.start_iso, "$lte": window.end_iso},
            }},
            {"$count": "n"},
        ]
        result = await sales_records_collection.aggregate(pipeline).to_list(1)
        return result[0]["n"] if result else 0
    except Exception as exc:
        logger.error(
            "customer_insights.repo: count_new_customers_in_period failed: %s",
            exc,
        )
        return 0


async def count_active_customers_at(
    org_id: str,
    as_of: date,
    active_window_days: int = 60,
) -> int:
    """Number of customers whose latest purchase is within ``active_window_days``
    before ``as_of``.

    Used to compute "active customers at end of period" snapshot. This
    differs from ``aggregate_revenue_in_period`` in that we look at the
    most recent purchase across all-time, not just within the period.
    """
    from database import sales_records_collection
    from datetime import timedelta

    cutoff = (as_of - timedelta(days=active_window_days)).isoformat()
    as_of_iso = as_of.isoformat()

    try:
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "customer_id": {"$ne": None, "$exists": True},
                "date": {"$lte": as_of_iso},
            }},
            {"$group": {
                "_id": "$customer_id",
                "last_date": {"$max": "$date"},
            }},
            {"$match": {"last_date": {"$gte": cutoff}}},
            {"$count": "n"},
        ]
        result = await sales_records_collection.aggregate(pipeline).to_list(1)
        return result[0]["n"] if result else 0
    except Exception as exc:
        logger.error(
            "customer_insights.repo: count_active_customers_at failed: %s",
            exc,
        )
        return 0


# ──────────────────────────────────────────────────────────────────────────────
# Cohort source data
# ──────────────────────────────────────────────────────────────────────────────


async def fetch_purchase_dates_per_customer(
    org_id: str,
    since: Optional[str] = None,
) -> dict[str, list[date]]:
    """Fetch ``{customer_id: [date, date, ...]}`` for cohort math.

    The dates list is de-duplicated to days (multiple purchases on the
    same day count once for activity purposes). ``since`` is an ISO
    cut-off date — if set, purchases before that date are excluded
    (useful to limit the cohort table horizon when the org has years
    of history).

    Returns ``{}`` on any error.
    """
    from database import sales_records_collection
    from datetime import datetime

    match: dict = {
        "organization_id": org_id,
        "customer_id": {"$ne": None, "$exists": True},
    }
    if since:
        match["date"] = {"$gte": since}

    try:
        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": {"customer_id": "$customer_id", "date": "$date"},
            }},
            {"$project": {
                "_id": 0,
                "customer_id": "$_id.customer_id",
                "date": "$_id.date",
            }},
        ]
        out: dict[str, list[date]] = {}
        async for row in sales_records_collection.aggregate(pipeline):
            try:
                d = datetime.strptime(row["date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            cid = row["customer_id"]
            out.setdefault(cid, []).append(d)
        return out
    except Exception as exc:
        logger.error(
            "customer_insights.repo: fetch_purchase_dates_per_customer failed: %s",
            exc,
        )
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# Customer timeline
# ──────────────────────────────────────────────────────────────────────────────


async def fetch_customer_timeline(
    org_id: str, customer_id: str, limit: int = 50,
) -> list[dict]:
    """Fetch combined orders + sales records as a chronological timeline.

    Returns a list of ``{"kind": "order"|"sale", "date": str, ...}``
    sorted descending by date. Useful for the slide-over drill-down to
    show the customer's full history in one stream.

    Capped at ``limit`` total events; orders win in the case of mixing
    (we always take the most recent regardless of source).
    """
    from database import orders_collection, sales_records_collection

    events: list[dict] = []

    # Orders — newer schema
    try:
        async for o in orders_collection.find(
            {"organization_id": org_id, "customer_id": customer_id},
            {
                "_id": 0,
                "id": 1,
                "order_number": 1,
                "status": 1,
                "total": 1,
                "currency": 1,
                "created_at": 1,
                "items": 1,
            },
        ).sort("created_at", -1).limit(limit):
            created = o.get("created_at")
            if hasattr(created, "isoformat"):
                date_iso = created.isoformat()
            else:
                date_iso = str(created or "")
            events.append({
                "kind": "order",
                "date": date_iso[:10],
                "amount": o.get("total"),
                "currency": o.get("currency"),
                "order_id": o.get("id"),
                "order_number": o.get("order_number"),
                "status": o.get("status"),
                "items_count": len(o.get("items") or []),
            })
    except Exception as exc:
        logger.warning(
            "customer_insights.repo: orders timeline read failed: %s", exc,
        )

    # Sales records — legacy / cashflow side
    try:
        async for s in sales_records_collection.find(
            {"organization_id": org_id, "customer_id": customer_id},
            {
                "_id": 0,
                "date": 1,
                "amount": 1,
                "currency": 1,
                "category": 1,
                "description": 1,
                "product_id": 1,
            },
        ).sort("date", -1).limit(limit):
            events.append({
                "kind": "sale",
                "date": s.get("date"),
                "amount": s.get("amount"),
                "currency": s.get("currency"),
                "category": s.get("category"),
                "description": s.get("description"),
                "product_id": s.get("product_id"),
            })
    except Exception as exc:
        logger.warning(
            "customer_insights.repo: sales timeline read failed: %s", exc,
        )

    # Sort + cap
    events.sort(key=lambda e: e.get("date") or "", reverse=True)
    return events[:limit]


# ──────────────────────────────────────────────────────────────────────────────
# Action log reads (for de-duplication of smart-suggestion triggers)
# ──────────────────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────────────────
# Materialised customer_metrics — read + write
# (Migrated from the legacy modules/customers_light/repository.py
# during the single-brain consolidation. Same semantics, same data.)
# ──────────────────────────────────────────────────────────────────────────────


async def count_linked_sales(org_id: str) -> int:
    """Count sales_records that have a non-null customer_id for this org."""
    from database import sales_records_collection
    try:
        return await sales_records_collection.count_documents({
            "organization_id": org_id,
            "customer_id": {"$ne": None, "$exists": True},
        })
    except Exception as exc:
        logger.error("customer_insights.repo: count_linked_sales failed: %s", exc)
        return 0


async def aggregate_revenue_by_customer(
    org_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict]:
    """Aggregate sales_records grouped by customer_id (all-time by default)."""
    from database import sales_records_collection
    try:
        match: dict = {
            "organization_id": org_id,
            "customer_id": {"$ne": None, "$exists": True},
        }
        if start_date:
            match.setdefault("date", {})["$gte"] = start_date
        if end_date:
            match.setdefault("date", {})["$lte"] = end_date

        pipeline = [
            {"$match": match},
            {"$group": {
                "_id": "$customer_id",
                "total_revenue": {"$sum": "$amount"},
                "count": {"$sum": 1},
                "first_date": {"$min": "$date"},
                "last_date": {"$max": "$date"},
            }},
            {"$sort": {"total_revenue": -1}},
        ]
        cursor = sales_records_collection.aggregate(pipeline)
        return await cursor.to_list(5000)
    except Exception as exc:
        logger.error(
            "customer_insights.repo: aggregate_revenue_by_customer failed: %s",
            exc,
        )
        return []


async def replace_metrics_for_org(org_id: str, metrics: list[dict]) -> int:
    """Full replace of customer_metrics for an org. Returns # inserted."""
    from database import customer_metrics_collection
    try:
        await customer_metrics_collection.delete_many({"organization_id": org_id})
        if metrics:
            await customer_metrics_collection.insert_many(metrics)
        return len(metrics)
    except Exception as exc:
        logger.error(
            "customer_insights.repo: replace_metrics_for_org failed: %s", exc,
        )
        return 0


async def find_metrics_by_org(
    org_id: str,
    segment: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    """List materialised customer metrics, optionally filtered by segment."""
    from database import customer_metrics_collection
    try:
        query: dict = {"organization_id": org_id}
        if segment:
            query["segment"] = segment
        cursor = customer_metrics_collection.find(
            query, {"_id": 0},
        ).sort("total_revenue", -1).limit(limit)
        return await cursor.to_list(limit)
    except Exception as exc:
        logger.error(
            "customer_insights.repo: find_metrics_by_org failed: %s", exc,
        )
        return []


async def find_metric_customer_ids(org_id: str) -> set:
    """F4 — set di TUTTI i customer_id che hanno una riga metriche (acquirenti),
    indipendente dal filtro segment. Usato per distinguere i lead (nessun
    acquisto) dagli acquirenti esclusi da un filtro segment."""
    from database import customer_metrics_collection
    try:
        cursor = customer_metrics_collection.find(
            {"organization_id": org_id}, {"_id": 0, "customer_id": 1},
        )
        return {d["customer_id"] async for d in cursor if d.get("customer_id")}
    except Exception as exc:
        logger.error(
            "customer_insights.repo: find_metric_customer_ids failed: %s", exc,
        )
        return set()


async def find_metrics_by_customer(
    org_id: str, customer_id: str,
) -> Optional[dict]:
    """Get materialised metrics for a single customer."""
    from database import customer_metrics_collection
    try:
        return await customer_metrics_collection.find_one(
            {"organization_id": org_id, "customer_id": customer_id},
            {"_id": 0},
        )
    except Exception as exc:
        logger.error(
            "customer_insights.repo: find_metrics_by_customer failed: %s",
            exc,
        )
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Action log reads (existed in original Phase 1)
# ──────────────────────────────────────────────────────────────────────────────


async def find_recent_outreach_for_customers(
    org_id: str,
    customer_ids: Iterable[str],
    since_iso: str,
) -> set[str]:
    """Return the set of customer_ids that have a logged outreach event
    after ``since_iso``.

    Used by the smart-suggestions panel to skip "contact at-risk customers"
    triggers if we already pinged them today/this week.
    """
    from database import audit_logs_collection

    ids = list(customer_ids)
    if not ids:
        return set()

    try:
        cursor = audit_logs_collection.find(
            {
                "organization_id": org_id,
                "action": "customer.outreach.sent",
                "resource_id": {"$in": ids},
                "created_at": {"$gte": since_iso},
            },
            {"_id": 0, "resource_id": 1},
        )
        rows = await cursor.to_list(length=len(ids))
        return {r["resource_id"] for r in rows if r.get("resource_id")}
    except Exception as exc:
        logger.warning(
            "customer_insights.repo: find_recent_outreach failed: %s", exc,
        )
        return set()
