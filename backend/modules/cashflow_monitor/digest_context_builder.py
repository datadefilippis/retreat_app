"""
Digest context builder — Wave 12.A.

Orchestrator that produces the FULL data context the digest builder needs:
  - cashflow overview (existing build_overview)
  - customers_summary  — when customers_light is active for the org
  - products_summary   — when product_catalog is active
  - commerce_summary   — when commerce is active
  - health enrichment  — trend / weakest / strongest dimension

Why this exists
---------------
Pre-Wave-12 the digest text only used ~30% of the data already in
``build_overview`` and ignored every cross-module data source entirely.
The result was a digest that said "Revenue X, Margin Y%, Score Z/100"
and nothing about customers, products, or orders — even when those
modules were active and full of data the merchant cares about.

This builder is the foundation that ``build_digest`` (the Sonnet
prompt) and ``build_digest_report`` (the PDF) both consume. The cross-
module summaries are built BEST-EFFORT: a failure in one module logs
a warning but never blocks the digest. Modules that aren't active
contribute an empty section.

Return shape
------------
A dict that extends the build_overview return with:

    {
      ...build_overview fields,           # cashflow data
      "customers_summary": {              # populated when customers_light active
        "available": bool,
        "top_customers": [{name, total_revenue, segment}, ...] (top 5),
        "concentration_top5_pct": float,  # % of total from top 5
        "total_customers": int,
        "churn_risk_count": int,          # customers with churn_risk_score>=60
        "new_customers_count": int,       # created in period
        "avg_clv": float,                 # average customer lifetime value
      },
      "products_summary": {               # populated when product_catalog active
        "available": bool,
        "top_sellers": [{name, units_sold, revenue}, ...] (top 5),
        "total_products": int,
        "low_margin_count": int,          # margin_pct < 15
        "declining_count": int,           # trend_30d_pct < -10
        "dormant_count": int,             # no sales in 60+ days
        "avg_margin_pct": float,
      },
      "commerce_summary": {               # populated when commerce active
        "available": bool,
        "orders_count": int,
        "orders_prev_count": int,
        "aov": float,
        "aov_prev": float,
        "aov_trend_pct": float,
        "cancellation_rate_pct": float,
        "top_channels": [{channel, revenue, share_pct}, ...] (top 3),
        "draft_orders_count": int,        # in-flight not yet paid
      },
      "health_score": {
        ...existing health fields,
        "trend": "improving" | "stable" | "declining" | None,
        "trend_delta_points": int,        # vs previous period score
        "weakest_dimension": {dimension, points, max, level} | None,
        "strongest_dimension": {dimension, points, max, level} | None,
      },
    }
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ── Public entrypoint ────────────────────────────────────────────────────────


async def build_digest_context(
    org_id: str,
    period: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period_days: int = 30,
) -> Optional[dict]:
    """Build the full digest context (cashflow + cross-module).

    Args:
        org_id: organization id
        period: shorthand like "30d", or None
        start_date / end_date: explicit window (ISO date strings)
        period_days: used when neither period nor explicit dates apply

    Returns:
        dict ready for the digest builder, or None if cashflow overview
        produces no data (digest can't be built without at least cashflow).
    """
    from modules.cashflow_monitor.overview_builder import build_overview
    from services.module_access import get_module_entitlements

    # ── 1. Cashflow overview (always required) ─────────────────────────────
    if not start_date or not end_date:
        end_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = start_date or (
            datetime.now(timezone.utc) - timedelta(days=period_days)
        ).strftime("%Y-%m-%d")

    try:
        overview = await build_overview(
            org_id=org_id,
            period=period or f"{period_days}d",
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        logger.error(
            "digest_context: build_overview failed for org=%s: %s", org_id, exc,
        )
        return None

    if not overview:
        return None

    # ── 2. Cross-module summaries (best-effort) ────────────────────────────
    overview["customers_summary"] = await _build_customers_summary(
        org_id, start_date, end_date,
    )
    overview["products_summary"] = await _build_products_summary(
        org_id,
    )
    overview["commerce_summary"] = await _build_commerce_summary(
        org_id, start_date, end_date,
    )

    # ── 3. Health enrichment (trend + weakest/strongest) ───────────────────
    overview["health_score"] = _enrich_health_score(overview.get("health_score", {}))

    return overview


# ── Customers summary ────────────────────────────────────────────────────────


async def _build_customers_summary(
    org_id: str, start_date: str, end_date: str,
) -> dict:
    """Aggregate the 'cosa devo sapere sui miei clienti' summary."""
    from services.module_access import get_module_entitlements
    empty = {"available": False, "top_customers": [], "concentration_top5_pct": 0.0,
             "total_customers": 0, "churn_risk_count": 0,
             "new_customers_count": 0, "avg_clv": 0.0}
    try:
        ent = await get_module_entitlements(org_id, "customers_light")
        if not ent.get("enabled"):
            return empty
    except Exception:
        return empty

    try:
        from database import customer_metrics_collection, customers_collection
        # Total customers
        total = await customer_metrics_collection.count_documents(
            {"organization_id": org_id},
        )
        if total == 0:
            return empty

        # Top 5 by lifetime revenue (customer_metrics is materialised)
        top_cursor = customer_metrics_collection.find(
            {"organization_id": org_id},
            {"_id": 0, "customer_name": 1, "customer_id": 1,
             "total_revenue": 1, "segment": 1, "churn_risk_score": 1},
        ).sort("total_revenue", -1).limit(5)
        top_raw = await top_cursor.to_list(5)
        top_customers = [
            {
                "name": (r.get("customer_name") or
                         f"Cliente {r.get('customer_id', '')[:8]}").strip(),
                "total_revenue": round(float(r.get("total_revenue", 0) or 0), 2),
                "segment": r.get("segment"),
            }
            for r in top_raw
        ]

        # Concentration: top 5 / sum all
        agg = await customer_metrics_collection.aggregate([
            {"$match": {"organization_id": org_id}},
            {"$group": {"_id": None,
                        "total": {"$sum": {"$ifNull": ["$total_revenue", 0]}},
                        "avg_clv": {"$avg": {"$ifNull": ["$total_revenue", 0]}}}},
        ]).to_list(1)
        total_rev = float(agg[0]["total"]) if agg else 0.0
        avg_clv = round(float(agg[0]["avg_clv"]), 2) if agg else 0.0
        top5_rev = sum(c["total_revenue"] for c in top_customers)
        concentration = round((top5_rev / total_rev * 100), 1) if total_rev > 0 else 0.0

        # Churn risk
        churn_count = await customer_metrics_collection.count_documents({
            "organization_id": org_id, "churn_risk_score": {"$gte": 60},
        })

        # New customers (created_at in period)
        new_count = await customers_collection.count_documents({
            "organization_id": org_id,
            "created_at": {"$gte": start_date, "$lte": end_date + "T23:59:59"},
        })

        return {
            "available": True,
            "top_customers": top_customers,
            "concentration_top5_pct": concentration,
            "total_customers": total,
            "churn_risk_count": churn_count,
            "new_customers_count": new_count,
            "avg_clv": avg_clv,
        }
    except Exception as exc:
        logger.warning("digest_context: customers_summary failed: %s", exc)
        return empty


# ── Products summary ─────────────────────────────────────────────────────────


async def _build_products_summary(org_id: str) -> dict:
    """Aggregate the 'cosa sta succedendo nel catalogo' summary.

    Note: product_metrics is computed snapshot-style (not period-windowed),
    so this summary is "current state" — useful for spotting low-margin /
    declining / dormant items regardless of the digest's date window.
    """
    from services.module_access import get_module_entitlements
    empty = {"available": False, "top_sellers": [],
             "total_products": 0, "low_margin_count": 0,
             "declining_count": 0, "dormant_count": 0, "avg_margin_pct": 0.0}
    try:
        ent = await get_module_entitlements(org_id, "product_catalog")
        if not ent.get("enabled"):
            return empty
    except Exception:
        return empty

    try:
        from database import product_metrics_collection
        total = await product_metrics_collection.count_documents(
            {"organization_id": org_id},
        )
        if total == 0:
            return empty

        # Top 5 sellers by revenue_30d (or all-time fallback)
        top_cursor = product_metrics_collection.find(
            {"organization_id": org_id},
            {"_id": 0, "product_name": 1, "name": 1,
             "revenue_30d": 1, "units_30d": 1,
             "total_revenue": 1, "total_units": 1},
        ).sort("revenue_30d", -1).limit(5)
        top_raw = await top_cursor.to_list(5)
        top_sellers = [
            {
                "name": (r.get("product_name") or r.get("name") or "?").strip(),
                "revenue": round(float(
                    r.get("revenue_30d") or r.get("total_revenue") or 0,
                ), 2),
                "units": int(r.get("units_30d") or r.get("total_units") or 0),
            }
            for r in top_raw
            if (r.get("revenue_30d") or r.get("total_revenue") or 0) > 0
        ]

        # Counts: low margin, declining, dormant
        low_margin = await product_metrics_collection.count_documents({
            "organization_id": org_id,
            "margin_pct": {"$lt": 15, "$ne": None},
        })
        declining = await product_metrics_collection.count_documents({
            "organization_id": org_id,
            "trend_30d_pct": {"$lt": -10},
        })
        dormant = await product_metrics_collection.count_documents({
            "organization_id": org_id,
            "$or": [
                {"units_30d": {"$in": [0, None]}},
                {"days_since_last_sale": {"$gte": 60}},
            ],
        })

        # Avg margin
        agg = await product_metrics_collection.aggregate([
            {"$match": {"organization_id": org_id,
                        "margin_pct": {"$ne": None}}},
            {"$group": {"_id": None,
                        "avg": {"$avg": "$margin_pct"}}},
        ]).to_list(1)
        avg_margin = round(float(agg[0]["avg"]), 1) if agg else 0.0

        return {
            "available": True,
            "top_sellers": top_sellers,
            "total_products": total,
            "low_margin_count": low_margin,
            "declining_count": declining,
            "dormant_count": dormant,
            "avg_margin_pct": avg_margin,
        }
    except Exception as exc:
        logger.warning("digest_context: products_summary failed: %s", exc)
        return empty


# ── Commerce summary ─────────────────────────────────────────────────────────


async def _build_commerce_summary(
    org_id: str, start_date: str, end_date: str,
) -> dict:
    """Aggregate the 'come stanno andando gli ordini' summary."""
    from services.module_access import get_module_entitlements
    empty = {"available": False, "orders_count": 0, "orders_prev_count": 0,
             "aov": 0.0, "aov_prev": 0.0, "aov_trend_pct": 0.0,
             "cancellation_rate_pct": 0.0, "top_channels": [],
             "draft_orders_count": 0}
    try:
        ent = await get_module_entitlements(org_id, "commerce")
        if not ent.get("enabled"):
            return empty
    except Exception:
        return empty

    try:
        from database import orders_collection

        # Current period
        cur_match = {
            "organization_id": org_id,
            "created_at": {"$gte": start_date, "$lte": end_date + "T23:59:59"},
            "status": {"$nin": ["draft"]},  # exclude drafts from "real" orders
        }
        cur_agg = await orders_collection.aggregate([
            {"$match": cur_match},
            {"$group": {
                "_id": None,
                "count": {"$sum": 1},
                "revenue": {"$sum": {"$ifNull": ["$total_amount", 0]}},
                "cancelled": {"$sum": {"$cond": [
                    {"$eq": ["$status", "cancelled"]}, 1, 0,
                ]}},
            }},
        ]).to_list(1)
        cur = cur_agg[0] if cur_agg else {"count": 0, "revenue": 0, "cancelled": 0}
        cur_count = int(cur["count"])
        cur_rev = float(cur["revenue"])
        cur_cancelled = int(cur["cancelled"])
        cur_aov = round(cur_rev / cur_count, 2) if cur_count > 0 else 0.0

        # Previous period of equal length
        try:
            sd = datetime.fromisoformat(start_date)
            ed = datetime.fromisoformat(end_date)
            window = (ed - sd).days + 1
            prev_end = (sd - timedelta(days=1)).date().isoformat()
            prev_start = (sd - timedelta(days=window)).date().isoformat()
        except Exception:
            prev_start = prev_end = None

        prev_count = 0
        prev_aov = 0.0
        if prev_start and prev_end:
            prev_agg = await orders_collection.aggregate([
                {"$match": {
                    "organization_id": org_id,
                    "created_at": {"$gte": prev_start, "$lte": prev_end + "T23:59:59"},
                    "status": {"$nin": ["draft"]},
                }},
                {"$group": {"_id": None,
                            "count": {"$sum": 1},
                            "revenue": {"$sum": {"$ifNull": ["$total_amount", 0]}}}},
            ]).to_list(1)
            if prev_agg:
                prev_count = int(prev_agg[0]["count"])
                prev_aov = round(float(prev_agg[0]["revenue"]) / prev_count, 2) if prev_count > 0 else 0.0

        aov_trend_pct = 0.0
        if prev_aov > 0 and cur_aov > 0:
            aov_trend_pct = round((cur_aov - prev_aov) / prev_aov * 100, 1)

        # Cancellation rate
        cancel_rate = round(cur_cancelled / cur_count * 100, 1) if cur_count > 0 else 0.0

        # Top 3 channels
        ch_agg = await orders_collection.aggregate([
            {"$match": cur_match},
            {"$group": {
                "_id": {"$ifNull": ["$source", "direct"]},
                "revenue": {"$sum": {"$ifNull": ["$total_amount", 0]}},
                "count": {"$sum": 1},
            }},
            {"$sort": {"revenue": -1}},
            {"$limit": 3},
        ]).to_list(3)
        total_ch_rev = sum(c["revenue"] for c in ch_agg)
        top_channels = [
            {
                "channel": str(c["_id"] or "direct"),
                "revenue": round(float(c["revenue"]), 2),
                "share_pct": round(c["revenue"] / total_ch_rev * 100, 1) if total_ch_rev > 0 else 0.0,
                "count": int(c["count"]),
            }
            for c in ch_agg
        ]

        # Draft orders (in-flight, cash at risk)
        draft_count = await orders_collection.count_documents({
            "organization_id": org_id, "status": "draft",
        })

        return {
            "available": True,
            "orders_count": cur_count,
            "orders_prev_count": prev_count,
            "aov": cur_aov,
            "aov_prev": prev_aov,
            "aov_trend_pct": aov_trend_pct,
            "cancellation_rate_pct": cancel_rate,
            "top_channels": top_channels,
            "draft_orders_count": draft_count,
        }
    except Exception as exc:
        logger.warning("digest_context: commerce_summary failed: %s", exc)
        return empty


# ── Health score enrichment ──────────────────────────────────────────────────


def _enrich_health_score(health: dict) -> dict:
    """Add trend / weakest / strongest fields used by the new prompt.

    ``trend`` is a best-effort label — pre-Wave-12 health_score didn't
    keep a per-period history, so we approximate by looking at the
    ``revenue_dynamics`` dimension when present (it embeds margin_trend
    and sales_trend). A proper historical comparison would need a
    snapshot collection — out of scope here.
    """
    if not health or "breakdown" not in health:
        return health

    breakdown = health.get("breakdown") or []
    # Filter only computable dimensions
    computable = [
        d for d in breakdown
        if d.get("points") is not None and d.get("max", 0) > 0
    ]

    weakest = None
    strongest = None
    if computable:
        # Score ratio (points/max) used to rank.
        weakest = min(computable, key=lambda d: d["points"] / d["max"])
        strongest = max(computable, key=lambda d: d["points"] / d["max"])

    # Trend approximation: read revenue_dynamics raw_value if present
    trend = None
    trend_delta = None
    for dim in computable:
        if dim.get("dimension_key") == "revenue_dynamics":
            ratio = dim["points"] / dim["max"]
            if ratio >= 0.8:
                trend = "improving"
            elif ratio <= 0.3:
                trend = "declining"
            else:
                trend = "stable"
            break

    health["trend"] = trend
    health["trend_delta_points"] = trend_delta
    health["weakest_dimension"] = (
        {
            "dimension": weakest.get("dimension"),
            "dimension_key": weakest.get("dimension_key"),
            "points": weakest.get("points"),
            "max": weakest.get("max"),
            "level": weakest.get("level"),
        }
        if weakest else None
    )
    health["strongest_dimension"] = (
        {
            "dimension": strongest.get("dimension"),
            "dimension_key": strongest.get("dimension_key"),
            "points": strongest.get("points"),
            "max": strongest.get("max"),
            "level": strongest.get("level"),
        }
        if strongest else None
    )

    return health
