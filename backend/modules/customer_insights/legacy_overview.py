"""Legacy ``build_overview`` shape, served via the platform module dispatcher.

Lives at GET /api/modules/customers_light/overview (mounted by the
generic ``routers/modules.py`` dispatcher that reads
``ModuleDefinition.overview_builder``). Kept untouched in shape so
the legacy dashboard widget + AI digest paths that consume it
continue to deserialise the same keys.

The new ``customer_insights/service.py:build_overview`` is a richer
period-aware response used by the new UI directly via
/api/customer-insights/overview. Two builders, two URLs, same source
collection (``customer_metrics``).

Migrated from ``modules.customers_light.service.build_overview``;
behaviour bit-for-bit identical.
"""

from __future__ import annotations

from typing import Dict, Optional


async def build_overview(
    org_id: str,
    period: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    **kwargs,
) -> Optional[dict]:
    """Build the legacy composite overview.

    Reads from materialised ``customer_metrics``. Returns
    ``{"has_data": False, ...}`` when no customer linkage exists so
    the dashboard widget can render a "no data yet" state instead of
    crashing.
    """
    from modules.customer_insights import repository
    from database import sales_records_collection

    linked_count = await repository.count_linked_sales(org_id)
    total_sales_count = 0
    try:
        total_sales_count = await sales_records_collection.count_documents(
            {"organization_id": org_id}
        )
    except Exception:
        pass

    if linked_count == 0:
        return {
            "has_data": False,
            "reason": "no_customer_linkage",
            "message": (
                "Nessun dato cliente collegato. Carica vendite con l'ID cliente "
                "mappato per attivare l'analisi clienti."
            ),
            "coverage": {
                "linked_sales": 0,
                "total_sales": total_sales_count,
                "coverage_pct": 0,
            },
        }

    all_metrics = await repository.find_metrics_by_org(org_id, limit=5000)
    if not all_metrics:
        return {
            "has_data": False,
            "reason": "no_metrics_computed",
            "message": "Metriche clienti non ancora calcolate. Attendere il prossimo aggiornamento.",
        }

    total_customers = len(all_metrics)
    total_revenue = sum(m["total_revenue"] for m in all_metrics)
    active_count = sum(1 for m in all_metrics if m["segment"] in ("top", "active", "new"))
    inactive_count = sum(1 for m in all_metrics if m["segment"] == "inactive")
    new_count = sum(1 for m in all_metrics if m["segment"] == "new")
    inactive_rate = round((inactive_count / total_customers * 100) if total_customers > 0 else 0, 1)

    top_10 = all_metrics[:10]
    top_10_revenue = sum(m["total_revenue"] for m in top_10)
    top_10_share = round((top_10_revenue / total_revenue * 100) if total_revenue > 0 else 0, 1)

    segments: Dict[str, dict] = {}
    for m in all_metrics:
        seg = m["segment"]
        if seg not in segments:
            segments[seg] = {"segment": seg, "count": 0, "total_revenue": 0.0}
        segments[seg]["count"] += 1
        segments[seg]["total_revenue"] = round(segments[seg]["total_revenue"] + m["total_revenue"], 2)

    for seg_data in segments.values():
        seg_data["pct_of_total"] = round(
            (seg_data["total_revenue"] / total_revenue * 100) if total_revenue > 0 else 0, 1
        )

    high_risk = sum(1 for m in all_metrics if m.get("churn_risk_score", 0) >= 60)
    avg_ltv = round(sum(m.get("lifetime_value", 0) for m in all_metrics) / total_customers, 2) if total_customers > 0 else 0
    growing_count = sum(1 for m in all_metrics if m.get("trend_direction") == "growing")
    declining_count = sum(1 for m in all_metrics if m.get("trend_direction") == "declining")

    top_customers = [
        {
            "customer_id": m.get("customer_id"),
            "customer_name": m["customer_name"],
            "total_revenue": m["total_revenue"],
            "transaction_count": m["transaction_count"],
            "avg_transaction_value": m.get("avg_transaction_value", 0),
            "purchase_frequency_monthly": m.get("purchase_frequency_monthly", 0),
            "first_purchase_date": m.get("first_purchase_date"),
            "last_purchase_date": m.get("last_purchase_date"),
            "days_since_last_purchase": m.get("days_since_last_purchase", 0),
            "segment": m["segment"],
            "revenue_share_pct": m["revenue_share_pct"],
            "lifetime_value": m.get("lifetime_value", 0),
            "churn_risk_score": m.get("churn_risk_score", 0),
            "trend_direction": m.get("trend_direction", "stable"),
            "customer_status": m.get("customer_status", "healthy"),
            "payment_reliability_pct": m.get("payment_reliability_pct"),
            "preferred_products": m.get("preferred_products", [])[:3],
            "preferred_categories": m.get("preferred_categories", [])[:3],
            "order_count": m.get("order_count", 0),
            "cancellation_rate_pct": m.get("cancellation_rate_pct", 0),
            "last_order_date": m.get("last_order_date"),
        }
        for m in top_10
    ]

    return {
        "has_data": True,
        "module": {"module_key": "customers_light", "module_name": "Customers Light"},
        "kpis": {
            "total_customers": total_customers,
            "active_customers": active_count,
            "inactive_customers": inactive_count,
            "new_customers": new_count,
            "inactive_rate_pct": inactive_rate,
            "top_10_share_pct": top_10_share,
            "total_revenue": round(total_revenue, 2),
            "avg_customer_value": round(total_revenue / total_customers, 2) if total_customers > 0 else 0,
            "avg_lifetime_value": avg_ltv,
            "high_churn_risk_count": high_risk,
            "growing_count": growing_count,
            "declining_count": declining_count,
            "total_order_count": sum(m.get("order_count", 0) for m in all_metrics),
            "total_orders_confirmed": sum(m.get("orders_confirmed", 0) for m in all_metrics),
            "total_orders_cancelled": sum(m.get("orders_cancelled", 0) for m in all_metrics),
            "avg_cancellation_rate_pct": round(
                sum(m.get("cancellation_rate_pct", 0) for m in all_metrics) / total_customers, 1
            ) if total_customers > 0 else 0,
            "customers_high_cancel": sum(1 for m in all_metrics if m.get("cancellation_rate_pct", 0) > 30),
            "total_booking_count": sum(m.get("booking_count", 0) for m in all_metrics),
            "total_event_attendance": sum(m.get("event_attendance", 0) for m in all_metrics),
        },
        "segments": list(segments.values()),
        "top_customers": top_customers,
        "concentration": {
            "top_5_share_pct": round(
                (sum(m["total_revenue"] for m in all_metrics[:5]) / total_revenue * 100)
                if total_revenue > 0 else 0, 1
            ),
            "top_10_share_pct": top_10_share,
            "total_customers": total_customers,
        },
        "coverage": {
            "linked_sales": linked_count,
            "total_sales": total_sales_count,
            "coverage_pct": round(linked_count / total_sales_count * 100, 1) if total_sales_count > 0 else 0,
        },
    }
