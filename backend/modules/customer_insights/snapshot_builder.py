"""KPI snapshot builder for the customer_insights module.

Migrated from ``modules.customers_light.snapshot_builder`` during the
single-brain consolidation. Logic identical so kpi_snapshots history
stays consistent.

Registered as ``snapshot_builder`` on the ModuleDefinition; the
platform's kpi_snapshot_service calls it on the configured cadence
to persist pre-computed KPI dicts.
"""

import logging

logger = logging.getLogger(__name__)


async def build_snapshot(
    org_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Build KPI snapshot dict.

    Reads from materialised ``customer_metrics``. Returns zero-shaped
    dict when there's no linked customer data so the snapshot history
    table doesn't get gaps.
    """
    from modules.customer_insights import repository

    all_metrics = await repository.find_metrics_by_org(org_id, limit=5000)

    if not all_metrics:
        return {
            "total_customers": 0,
            "active_customers": 0,
            "inactive_rate_pct": 0,
            "new_customers": 0,
            "top_10_share_pct": 0,
            "avg_transaction_value": 0,
            "avg_customer_value": 0,
        }

    total = len(all_metrics)
    total_revenue = sum(m["total_revenue"] for m in all_metrics)
    active = sum(1 for m in all_metrics if m["segment"] in ("top", "active", "new"))
    inactive = sum(1 for m in all_metrics if m["segment"] == "inactive")
    new_count = sum(1 for m in all_metrics if m["segment"] == "new")

    top_10_revenue = sum(m["total_revenue"] for m in all_metrics[:10])
    top_10_share = round((top_10_revenue / total_revenue * 100) if total_revenue > 0 else 0, 1)

    total_transactions = sum(m["transaction_count"] for m in all_metrics)
    avg_txn = round(total_revenue / total_transactions, 2) if total_transactions > 0 else 0

    return {
        "total_customers": total,
        "active_customers": active,
        "inactive_rate_pct": round((inactive / total * 100) if total > 0 else 0, 1),
        "new_customers": new_count,
        "top_10_share_pct": top_10_share,
        "avg_transaction_value": avg_txn,
        "avg_customer_value": round(total_revenue / total, 2) if total > 0 else 0,
    }
