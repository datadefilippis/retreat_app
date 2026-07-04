"""
Product Catalog Snapshot Builder — KPI persistence for product analytics.

Returns a summary dict for the kpi_snapshots system.
"""

import logging
from database import product_metrics_collection, products_collection

logger = logging.getLogger(__name__)


async def build_snapshot(org_id: str, start_date: str, end_date: str) -> dict:
    """Build a KPI snapshot from materialized product_metrics."""
    metrics = await product_metrics_collection.find(
        {"organization_id": org_id},
        {"_id": 0, "total_revenue": 1, "total_cost": 1, "margin_pct": 1, "abc_class": 1},
    ).to_list(length=1000)

    if not metrics:
        return {
            "active_products": 0,
            "products_with_sales": 0,
            "total_product_revenue": 0,
            "avg_margin_pct": 0,
            "abc_a_count": 0,
            "abc_b_count": 0,
            "abc_c_count": 0,
        }

    active_count = await products_collection.count_documents(
        {"organization_id": org_id, "is_active": True}
    )

    total_revenue = sum(m["total_revenue"] for m in metrics)
    total_cost = sum(m["total_cost"] for m in metrics)
    avg_margin = round(sum(m["margin_pct"] for m in metrics) / len(metrics), 1)

    abc = {"A": 0, "B": 0, "C": 0}
    for m in metrics:
        abc[m.get("abc_class", "C")] += 1

    return {
        "active_products": active_count,
        "products_with_sales": len(metrics),
        "total_product_revenue": round(total_revenue, 2),
        "total_product_cost": round(total_cost, 2),
        "weighted_margin_pct": round(
            (total_revenue - total_cost) / total_revenue * 100, 1
        ) if total_revenue > 0 else 0,
        "avg_margin_pct": avg_margin,
        "abc_a_count": abc["A"],
        "abc_b_count": abc["B"],
        "abc_c_count": abc["C"],
    }
