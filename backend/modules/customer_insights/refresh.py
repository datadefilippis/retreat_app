"""customer_metrics writer — the materialised view's ONLY writer.

Migrated from the legacy ``modules.customers_light.service`` during the
single-brain consolidation. Logic is bit-for-bit identical to the
legacy version so:

  • the materialised ``customer_metrics`` collection schema doesn't
    change (orgs see the same documents shape),
  • AI tools that read the docs (lifetime_value, churn_risk_score,
    preferred_products, etc.) keep returning the same fields,
  • re-running the refresh on the same input produces the same output.

Why we don't already use the corrected formulas from
``customer_insights.formulas``: those introduce ``None`` for short-history
customers (lifetime_value → projected_annual_revenue, frequency
None for count<3). Switching today would silently change the
materialised docs and break downstream AI assumptions
("lifetime_value is always a non-None number"). The new formulas are
exposed by the new UI surface; the legacy field names stay intact
here for AI continuity. A future migration can wire the corrected
formulas in lockstep with AI tool updates.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Segment classification (legacy hardcoded thresholds, preserved) ─────────


def _classify_segment(
    days_since_last: int,
    first_purchase_date: Optional[str],
    revenue_rank_pct: float,
) -> str:
    """Classify a customer into a segment. Legacy hardcoded thresholds.

    Priority: new > top > active > occasional > inactive
    """
    if first_purchase_date:
        try:
            first = datetime.strptime(first_purchase_date, "%Y-%m-%d").date()
            if (date.today() - first).days <= 90:
                return "new"
        except (ValueError, TypeError):
            pass

    if revenue_rank_pct <= 0.10:
        return "top"
    if days_since_last <= 60:
        return "active"
    if days_since_last <= 180:
        return "occasional"
    return "inactive"


# ── Core refresh ────────────────────────────────────────────────────────────


async def refresh_customer_metrics(org_id: str) -> dict:
    """Recompute all customer metrics for an organisation.

    Steps:
      1. Aggregate revenue from sales_records grouped by customer_id
      2. Look up customer names from shared master data
      3. Compute derived indicators and relative positions
      4. Classify segments
      5. Persist to customer_metrics (full replace)

    Returns: ``{"customers_computed": int, "message": str}``
    """
    from modules.customer_insights import repository
    from repositories import customer_repository

    aggregates = await repository.aggregate_revenue_by_customer(org_id)
    if not aggregates:
        await repository.replace_metrics_for_org(org_id, [])
        return {"customers_computed": 0, "message": "No linked customer data"}

    all_customers = await customer_repository.find_by_org(
        org_id, active_only=False, limit=5000,
    )
    name_map = {c.id: c.name for c in all_customers}

    from models.common import generate_id, utc_now

    total_org_revenue = sum(a["total_revenue"] for a in aggregates)
    today = date.today()
    today_iso = today.isoformat()
    total_customers = len(aggregates)
    computed_at = utc_now().isoformat()

    all_first_dates = [a.get("first_date") for a in aggregates if a.get("first_date")]
    period_start = min(all_first_dates) if all_first_dates else None

    # Parallel helper computations
    trend_map, preferred_products_map, payment_reliability_map, order_metrics_map = await asyncio.gather(
        _compute_revenue_trend(org_id, today),
        _compute_preferred_products(org_id),
        _compute_payment_reliability(org_id),
        _compute_order_metrics(org_id),
        return_exceptions=True,
    )
    if isinstance(trend_map, Exception):
        logger.warning("customer_insights: trend computation failed: %s", trend_map)
        trend_map = {}
    if isinstance(preferred_products_map, Exception):
        logger.warning("customer_insights: preferred products failed: %s", preferred_products_map)
        preferred_products_map = {}
    if isinstance(payment_reliability_map, Exception):
        logger.warning("customer_insights: payment reliability failed: %s", payment_reliability_map)
        payment_reliability_map = {}
    if isinstance(order_metrics_map, Exception):
        logger.warning("customer_insights: order metrics failed: %s", order_metrics_map)
        order_metrics_map = {}

    metrics_docs = []
    for rank_idx, agg in enumerate(aggregates):
        cid = agg["_id"]
        revenue = round(agg["total_revenue"], 2)
        count = agg["count"]
        first_date = agg.get("first_date")
        last_date = agg.get("last_date")

        days_since = 0
        if last_date:
            try:
                last_dt = datetime.strptime(last_date, "%Y-%m-%d").date()
                days_since = (today - last_dt).days
            except (ValueError, TypeError):
                pass

        months_active = 1.0
        if first_date and last_date and first_date != last_date:
            try:
                f = datetime.strptime(first_date, "%Y-%m-%d").date()
                l = datetime.strptime(last_date, "%Y-%m-%d").date()
                months_active = max((l - f).days / 30.0, 1.0)
            except (ValueError, TypeError):
                pass
        frequency = round(count / months_active, 2)

        share = round((revenue / total_org_revenue * 100) if total_org_revenue > 0 else 0, 2)
        rank_pct = rank_idx / total_customers if total_customers > 1 else 0.0
        segment = _classify_segment(days_since, first_date, rank_pct)

        avg_tx = round(revenue / count, 2) if count > 0 else 0
        lifetime_value = round(avg_tx * frequency * 12, 2)

        om = order_metrics_map.get(cid, {})
        cancel_rate = om.get("cancellation_rate_pct", 0)

        churn_risk_score = _compute_churn_risk(days_since, frequency, count)
        if cancel_rate > 30:
            churn_risk_score = min(100, churn_risk_score + 20)
        elif om.get("orders_cancelled", 0) > 3:
            churn_risk_score = min(100, churn_risk_score + 10)

        trend = trend_map.get(cid, {})
        trend_direction = _classify_trend(
            trend.get("recent", 0), trend.get("previous", 0), segment,
        )
        customer_status = _classify_status(segment, churn_risk_score, trend_direction)

        doc = {
            "id": generate_id(),
            "organization_id": org_id,
            "customer_id": cid,
            "customer_name": name_map.get(cid, ""),
            "total_revenue": revenue,
            "transaction_count": count,
            "avg_transaction_value": avg_tx,
            "first_purchase_date": first_date,
            "last_purchase_date": last_date,
            "days_since_last_purchase": days_since,
            "purchase_frequency_monthly": frequency,
            "revenue_rank": rank_idx + 1,
            "revenue_share_pct": share,
            "segment": segment,
            "trend_direction": trend_direction,
            "customer_status": customer_status,
            "lifetime_value": lifetime_value,
            "churn_risk_score": churn_risk_score,
            "preferred_products": preferred_products_map.get(cid, []),
            "preferred_categories": _extract_categories(preferred_products_map.get(cid, [])),
            "payment_reliability_pct": payment_reliability_map.get(cid),
            "computed_at": computed_at,
            "period_start": period_start,
            "period_end": today_iso,
            # Order-derived (v13.0)
            "order_count": om.get("order_count", 0),
            "order_total_value": om.get("order_total_value", 0),
            "avg_order_value": om.get("avg_order_value", 0),
            "last_order_date": om.get("last_order_date"),
            "orders_confirmed": om.get("orders_confirmed", 0),
            "orders_cancelled": om.get("orders_cancelled", 0),
            "cancellation_rate_pct": cancel_rate,
            "booking_count": om.get("booking_count", 0),
            "event_attendance": om.get("event_attendance", 0),
            "fulfillment_success_rate": om.get("fulfillment_success_rate"),
        }
        metrics_docs.append(doc)

    inserted = await repository.replace_metrics_for_org(org_id, metrics_docs)
    logger.info(
        "customer_insights: refreshed %d customer metrics for org=%s",
        inserted, org_id,
    )
    return {"customers_computed": inserted, "message": f"Computed metrics for {inserted} customers"}


# ── Helper functions (legacy bit-for-bit) ──────────────────────────────────


def _compute_churn_risk(days_since_last: int, frequency: float, tx_count: int) -> int:
    """Compute churn risk score 0-100. Legacy formula preserved."""
    if days_since_last <= 30:
        recency_score = 0
    elif days_since_last <= 180:
        recency_score = int((days_since_last - 30) / 150 * 50)
    else:
        recency_score = 50

    if frequency >= 2.0:
        freq_score = 0
    elif frequency >= 0.5:
        freq_score = int((2.0 - frequency) / 1.5 * 30)
    else:
        freq_score = 30

    single_penalty = 20 if tx_count == 1 else 0
    return min(recency_score + freq_score + single_penalty, 100)


def _classify_trend(recent_revenue: float, previous_revenue: float, segment: str) -> str:
    """Legacy hardcoded ±20% threshold."""
    if segment == "new":
        return "new"
    if previous_revenue <= 0:
        return "new" if recent_revenue > 0 else "stable"
    if recent_revenue >= previous_revenue * 1.2:
        return "growing"
    if recent_revenue <= previous_revenue * 0.8:
        return "declining"
    return "stable"


def _classify_status(segment: str, churn_risk: int, trend: str) -> str:
    """Operational customer status. Legacy."""
    if segment == "inactive":
        return "lost"
    if churn_risk >= 60:
        return "at_risk"
    if segment == "occasional" or trend == "declining":
        return "watch"
    return "healthy"


def _extract_categories(preferred_products: List[dict]) -> List[str]:
    seen = set()
    cats = []
    for p in preferred_products:
        cat = p.get("category")
        if cat and cat not in seen:
            seen.add(cat)
            cats.append(cat)
    return cats[:3]


async def _compute_preferred_products(org_id: str) -> Dict[str, List[dict]]:
    from database import sales_records_collection, products_collection

    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "customer_id": {"$ne": None, "$exists": True},
            "product_id": {"$ne": None, "$exists": True},
        }},
        {"$group": {
            "_id": {"customer_id": "$customer_id", "product_id": "$product_id"},
            "revenue": {"$sum": "$amount"},
        }},
        {"$sort": {"revenue": -1}},
    ]

    prod_cursor = products_collection.find(
        {"organization_id": org_id},
        {"_id": 0, "id": 1, "name": 1, "category": 1},
    )
    prod_names = {}
    prod_categories = {}
    async for p in prod_cursor:
        prod_names[p["id"]] = p.get("name", "")
        prod_categories[p["id"]] = p.get("category")

    result: Dict[str, List[dict]] = {}
    async for doc in sales_records_collection.aggregate(pipeline):
        cid = doc["_id"]["customer_id"]
        pid = doc["_id"]["product_id"]
        if cid not in result:
            result[cid] = []
        if len(result[cid]) < 3:
            result[cid].append({
                "product_id": pid,
                "product_name": prod_names.get(pid, pid[:8]),
                "category": prod_categories.get(pid),
                "revenue": round(doc["revenue"], 2),
            })

    return result


async def _compute_payment_reliability(org_id: str) -> Dict[str, Optional[float]]:
    from database import sales_records_collection

    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "customer_id": {"$ne": None, "$exists": True},
            "due_date": {"$ne": None, "$exists": True},
        }},
        {"$group": {
            "_id": "$customer_id",
            "total_with_due": {"$sum": 1},
            "paid_on_time": {"$sum": {
                "$cond": [
                    {"$or": [
                        {"$eq": ["$payment_status", "paid"]},
                        {"$and": [
                            {"$ne": ["$payment_date", None]},
                            {"$lte": ["$payment_date", "$due_date"]},
                        ]},
                    ]},
                    1, 0,
                ],
            }},
        }},
    ]

    result: Dict[str, Optional[float]] = {}
    try:
        async for doc in sales_records_collection.aggregate(pipeline):
            total = doc["total_with_due"]
            if total > 0:
                result[doc["_id"]] = round(doc["paid_on_time"] / total * 100, 1)
    except Exception as exc:
        logger.warning("payment_reliability computation failed: %s", exc)

    return result


async def _compute_revenue_trend(org_id: str, today: date) -> Dict[str, dict]:
    from database import sales_records_collection
    from datetime import timedelta

    d90 = (today - timedelta(days=90)).isoformat()
    d180 = (today - timedelta(days=180)).isoformat()
    today_iso = today.isoformat()

    async def _sum_by_customer(start: str, end: str) -> Dict[str, float]:
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "customer_id": {"$ne": None, "$exists": True},
                "date": {"$gte": start, "$lte": end},
            }},
            {"$group": {"_id": "$customer_id", "total": {"$sum": "$amount"}}},
        ]
        out = {}
        try:
            async for doc in sales_records_collection.aggregate(pipeline):
                out[doc["_id"]] = doc["total"] or 0
        except Exception as exc:
            logger.warning("revenue_trend computation failed: %s", exc)
        return out

    recent = await _sum_by_customer(d90, today_iso)
    previous = await _sum_by_customer(d180, d90)

    all_ids = set(recent.keys()) | set(previous.keys())
    return {
        cid: {"recent": recent.get(cid, 0), "previous": previous.get(cid, 0)}
        for cid in all_ids
    }


async def _compute_order_metrics(org_id: str) -> Dict[str, dict]:
    """Order-derived metrics (v13.0). Legacy."""
    from database import orders_collection
    from datetime import datetime as _dt

    result: Dict[str, dict] = {}

    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "customer_id": {"$ne": None, "$exists": True},
        }},
        {"$group": {
            "_id": "$customer_id",
            "order_count": {"$sum": 1},
            "order_total_value": {"$sum": {"$ifNull": ["$total", 0]}},
            "last_order_date": {"$max": "$created_at"},
            "orders_confirmed": {"$sum": {"$cond": [
                {"$in": ["$status", ["confirmed", "completed"]]}, 1, 0
            ]}},
            "orders_cancelled": {"$sum": {"$cond": [
                {"$eq": ["$status", "cancelled"]}, 1, 0
            ]}},
        }},
    ]

    async for doc in orders_collection.aggregate(pipeline):
        cid = doc["_id"]
        oc = doc.get("order_count", 0)
        ov = round(doc.get("order_total_value", 0) or 0, 2)
        canc = doc.get("orders_cancelled", 0)
        last_raw = doc.get("last_order_date")
        last_iso = None
        if last_raw is not None:
            try:
                last_iso = last_raw.strftime("%Y-%m-%d") if hasattr(last_raw, "strftime") else str(last_raw)[:10]
            except Exception:
                last_iso = None

        result[cid] = {
            "order_count": oc,
            "order_total_value": ov,
            "avg_order_value": round(ov / oc, 2) if oc > 0 else 0,
            "last_order_date": last_iso,
            "orders_confirmed": doc.get("orders_confirmed", 0),
            "orders_cancelled": canc,
            "cancellation_rate_pct": round(canc / oc * 100, 1) if oc > 0 else 0,
        }

    # Booking + event_attendance (separate pipeline w/ items unwind)
    items_pipeline = [
        {"$match": {
            "organization_id": org_id,
            "customer_id": {"$ne": None, "$exists": True},
            "status": {"$ne": "cancelled"},
        }},
        {"$unwind": {"path": "$items", "preserveNullAndEmptyArrays": False}},
        {"$group": {
            "_id": "$customer_id",
            "booking_count": {"$sum": {"$cond": [
                {"$eq": ["$items.item_type", "booking"]},
                {"$ifNull": ["$items.quantity", 1]}, 0,
            ]}},
            "event_attendance": {"$sum": {"$cond": [
                {"$eq": ["$items.item_type", "event_ticket"]},
                {"$ifNull": ["$items.quantity", 1]}, 0,
            ]}},
        }},
    ]
    async for doc in orders_collection.aggregate(items_pipeline):
        cid = doc["_id"]
        result.setdefault(cid, {})
        result[cid]["booking_count"] = doc.get("booking_count", 0)
        result[cid]["event_attendance"] = doc.get("event_attendance", 0)

    # fulfillment_success_rate (separate aggregation)
    fulfill_pipeline = [
        {"$match": {
            "organization_id": org_id,
            "customer_id": {"$ne": None, "$exists": True},
            "fulfillment.status": {"$exists": True, "$ne": None},
        }},
        {"$group": {
            "_id": "$customer_id",
            "total": {"$sum": 1},
            "fulfilled": {"$sum": {"$cond": [
                {"$in": ["$fulfillment.status", ["delivered", "picked_up", "fulfilled"]]},
                1, 0,
            ]}},
        }},
    ]
    async for doc in orders_collection.aggregate(fulfill_pipeline):
        cid = doc["_id"]
        total = doc.get("total", 0)
        if total > 0:
            result.setdefault(cid, {})
            result[cid]["fulfillment_success_rate"] = round(
                doc.get("fulfilled", 0) / total * 100, 1,
            )

    return result
