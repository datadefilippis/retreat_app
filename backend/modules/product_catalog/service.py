"""
Product Catalog Service — materialized product analytics.

Computes per-product metrics (revenue, cost, margin, trend, ABC class)
from sales_records and purchase_records, then materializes them into
product_metrics for fast reads.

Public interface:
    refresh_product_metrics(org_id) -> dict
    build_overview(org_id, period, start_date, end_date, **kw) -> dict
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

from database import (
    product_metrics_collection,
    products_collection,
    sales_records_collection,
    purchase_records_collection,
)
from models.common import utc_now

logger = logging.getLogger(__name__)


async def refresh_product_metrics(org_id: str) -> dict:
    """Recompute and persist product metrics for all products with sales data.

    Steps:
    1. Aggregate total revenue per product_id from sales_records
    2. Aggregate total cost per product_id from purchase_records
    3. Compute margins, trend, ABC classification
    4. Full replace in product_metrics collection
    """
    now = utc_now()

    # ── 1. Revenue per product from sales_records ──────────────────────────
    revenue_pipeline = [
        {"$match": {"organization_id": org_id, "product_id": {"$ne": None, "$exists": True}}},
        {"$group": {
            "_id": "$product_id",
            "total_revenue": {"$sum": "$amount"},
            "total_units_sold": {"$sum": 1},
            "first_sale_date": {"$min": "$date"},
            "last_sale_date": {"$max": "$date"},
        }},
    ]
    revenue_cursor = sales_records_collection.aggregate(revenue_pipeline)
    revenue_by_product = {}
    async for doc in revenue_cursor:
        pid = doc["_id"]
        revenue_by_product[pid] = {
            "total_revenue": doc["total_revenue"] or 0,
            "total_units_sold": doc["total_units_sold"] or 0,
            "first_sale_date": doc.get("first_sale_date"),
            "last_sale_date": doc.get("last_sale_date"),
        }

    if not revenue_by_product:
        # No sales with product_id — clear metrics and return
        await product_metrics_collection.delete_many({"organization_id": org_id})
        return {"products_computed": 0, "total_revenue": 0}

    # ── 2. Cost per product from purchase_records ──────────────────────────
    cost_pipeline = [
        {"$match": {"organization_id": org_id, "product_id": {"$ne": None, "$exists": True}}},
        {"$group": {
            "_id": "$product_id",
            "total_cost": {"$sum": "$amount"},
            "total_units_purchased": {"$sum": 1},
        }},
    ]
    cost_cursor = purchase_records_collection.aggregate(cost_pipeline)
    cost_by_product = {}
    async for doc in cost_cursor:
        cost_by_product[doc["_id"]] = {
            "total_cost": doc["total_cost"] or 0,
            "total_units_purchased": doc["total_units_purchased"] or 0,
        }

    # ── 3. Trend: revenue last 30d vs previous 30d ────────────────────────
    today = date.today()
    start_30d = (today - timedelta(days=29)).isoformat()
    start_60d = (today - timedelta(days=59)).isoformat()
    end_str = today.isoformat()

    import asyncio as _aio
    trend_current, trend_prev, commerce_map = await _aio.gather(
        _sum_revenue_by_product(org_id, start_30d, end_str),
        _sum_revenue_by_product(org_id, start_60d, start_30d),
        _compute_commerce_product_metrics(org_id),
        return_exceptions=True,
    )
    if isinstance(trend_current, Exception):
        logger.warning("product_catalog: trend_current failed: %s", trend_current)
        trend_current = {}
    if isinstance(trend_prev, Exception):
        logger.warning("product_catalog: trend_prev failed: %s", trend_prev)
        trend_prev = {}
    if isinstance(commerce_map, Exception):
        logger.warning("product_catalog: commerce metrics failed: %s", commerce_map)
        commerce_map = {}

    # ── 4. Load product master data ────────────────────────────────────────
    # 2026-05-20 — Fix Performance Prodotti #1: also load ``cost_source``
    # so we can call the resolver as a fallback for products that have
    # NO purchase_records but DO have a declared cost on the product
    # itself (the common case after a merchant uses CostSourceEditor in
    # the wizard but never inputs purchase rows in cashflow).
    products_by_id = {}
    cursor = products_collection.find(
        {"organization_id": org_id, "is_active": True},
        {
            "_id": 0, "id": 1, "name": 1, "sku": 1, "category": 1,
            "stock_quantity": 1, "item_type": 1,
            # cost_source + cost_price are read for the fallback below.
            # cost_price is the legacy single-decimal field; cost_source
            # is the Wave 1 structured composition (preferred).
            "cost_source": 1, "cost_price": 1,
        },
    )
    async for p in cursor:
        products_by_id[p["id"]] = p

    # ── 4.5. Resolve declared unit-cost from cost_source (Wave 1 fix) ──────
    # The previous implementation calculated total_cost ONLY from
    # purchase_records aggregated by product_id. If the merchant
    # configured cost_source on the product but never recorded purchases,
    # total_cost stayed at 0 and margin_pct came out None — which is
    # the bug the merchant saw in production.
    #
    # Strategy (additive, zero regression):
    #   · purchase_records as cost source → WINS when present (real,
    #     auditable, tracks WAC over time).
    #   · cost_source resolver as fallback → fills in when no purchase
    #     rows exist for the product. The resolver itself already handles
    #     legacy cost_price by migrating it to a manual component upstream
    #     (see scripts/migrate_cost_price_to_components.py).
    #
    # We pre-resolve in batch so the resolver's internal caches are
    # warmed once and shared across the whole org — ~500 products in a
    # single sweep instead of N×M Mongo round-trips.
    unit_cost_from_source: Dict[str, float] = {}
    try:
        from services.cost_resolver import CostResolver
        from datetime import datetime as _dt, timezone as _tz
        candidate_products = [
            p for p in products_by_id.values()
            if (p.get("cost_source") or p.get("cost_price"))
        ]
        if candidate_products:
            resolver = CostResolver(
                org_id=org_id,
                as_of=_dt.now(_tz.utc),
            )
            resolver_results = await resolver.resolve_many(candidate_products)
            for pid, result in resolver_results.items():
                if result and result.value is not None and result.value > 0:
                    unit_cost_from_source[pid] = float(result.value)
    except Exception as exc:
        # Soft-fail: a resolver glitch must NOT block the refresh —
        # we just fall back to the legacy behaviour (cost from
        # purchase_records only).
        logger.warning(
            "product_catalog.refresh: cost_source resolver batch "
            "failed for org=%s: %s",
            org_id, exc,
        )
        unit_cost_from_source = {}

    # ── 5. Build metrics per product ───────────────────────────────────────
    all_product_ids = set(revenue_by_product.keys())
    metrics_list = []
    total_org_revenue = sum(r["total_revenue"] for r in revenue_by_product.values())

    for pid in all_product_ids:
        rev = revenue_by_product.get(pid, {})
        cost = cost_by_product.get(pid, {})
        prod = products_by_id.get(pid, {})

        total_revenue = rev.get("total_revenue", 0)
        total_cost = cost.get("total_cost", 0)
        total_units_sold = rev.get("total_units_sold", 0)
        total_units_purchased = cost.get("total_units_purchased", 0)

        # 2026-05-20 — Fix: fallback to declared cost_source when no
        # purchase_records exist for the product. We multiply the
        # resolver's unit_cost by total_units_sold so the aggregate
        # (total_cost) is in the same shape consumers already expect.
        # ``total_cost_source`` labels which fonte vinse — used by the
        # frontend cost-banner to surface "declared cost" vs "actual
        # purchases" without ambiguity.
        if total_cost > 0:
            total_cost_source_label = "purchase_records"
        elif pid in unit_cost_from_source and total_units_sold > 0:
            declared_unit_cost = unit_cost_from_source[pid]
            total_cost = round(declared_unit_cost * total_units_sold, 2)
            total_units_purchased = total_units_sold
            total_cost_source_label = "cost_source"
        else:
            total_cost_source_label = "none"

        has_cost = total_cost > 0
        margin_amount = total_revenue - total_cost if has_cost else None
        margin_pct = round((margin_amount / total_revenue) * 100, 1) if has_cost and total_revenue > 0 else None
        avg_sale_price = round(total_revenue / total_units_sold, 2) if total_units_sold > 0 else 0
        # When the cost came from cost_source the avg_unit_cost IS the
        # resolver's value verbatim (more accurate than dividing total
        # by units, which would just round-trip the same number).
        if total_cost_source_label == "cost_source":
            avg_unit_cost = round(unit_cost_from_source[pid], 2)
        else:
            avg_unit_cost = round(total_cost / total_units_purchased, 2) if has_cost and total_units_purchased > 0 else None
        markup_pct = round((avg_sale_price - avg_unit_cost) / avg_unit_cost * 100, 1) if avg_unit_cost and avg_unit_cost > 0 and avg_sale_price > 0 else None

        # Trend
        cur = trend_current.get(pid, 0)
        prv = trend_prev.get(pid, 0)
        trend_30d_pct = round((cur - prv) / prv * 100, 1) if prv > 0 else (100.0 if cur > 0 else 0)

        # Commerce-derived fields (v13.0 additive)
        cm = commerce_map.get(pid, {})

        metrics_list.append({
            "organization_id": org_id,
            "product_id": pid,
            "product_name": prod.get("name", f"Product {pid[:8]}"),
            "sku": prod.get("sku"),
            "category": prod.get("category"),
            # ── Cashflow-derived (19 original) ────────────────────────
            "total_revenue": round(total_revenue, 2),
            "total_units_sold": total_units_sold,
            "total_cost": round(total_cost, 2),
            "total_units_purchased": total_units_purchased,
            # 2026-05-20 — Fix: surface WHICH source supplied the cost so
            # the frontend can distinguish "declared by merchant" from
            # "computed from purchase records". Possible values:
            #   "purchase_records"  — total_cost = $sum purchase_records.amount
            #   "cost_source"       — total_cost = resolver(cost_source) * units_sold
            #   "none"              — no cost data on either side
            "total_cost_source": total_cost_source_label,
            "margin_amount": round(margin_amount, 2) if margin_amount is not None else None,
            "margin_pct": margin_pct,
            "avg_sale_price": avg_sale_price,
            "avg_unit_cost": avg_unit_cost,
            "markup_pct": markup_pct,
            "trend_30d_pct": trend_30d_pct,
            "first_sale_date": rev.get("first_sale_date"),
            "last_sale_date": rev.get("last_sale_date"),
            "abc_class": "",  # Computed below
            "computed_at": now,
            # ── Commerce-derived (v13.0, 8 new fields) ────────────────
            "item_type": cm.get("item_type", "physical"),
            "order_count": cm.get("order_count", 0),
            "order_revenue": cm.get("order_revenue", 0),
            "cancellation_rate_pct": cm.get("cancellation_rate_pct", 0),
            "event_fill_rate_pct": cm.get("event_fill_rate_pct"),
            "event_total_capacity": cm.get("event_total_capacity"),
            "booking_utilization_pct": cm.get("booking_utilization_pct"),
            "rental_utilization_pct": cm.get("rental_utilization_pct"),
            "stock_quantity": prod.get("stock_quantity"),
        })

    # ── 6. ABC classification ──────────────────────────────────────────────
    metrics_list.sort(key=lambda m: m["total_revenue"], reverse=True)
    cumulative = 0
    for m in metrics_list:
        cumulative += m["total_revenue"]
        pct = (cumulative / total_org_revenue * 100) if total_org_revenue > 0 else 100
        if pct <= 80:
            m["abc_class"] = "A"
        elif pct <= 95:
            m["abc_class"] = "B"
        else:
            m["abc_class"] = "C"

    # ── 7. Persist (full replace) ──────────────────────────────────────────
    await product_metrics_collection.delete_many({"organization_id": org_id})
    if metrics_list:
        await product_metrics_collection.insert_many(metrics_list)

    logger.info(
        "product_catalog: refreshed %d product metrics for org=%s (total_revenue=%.2f)",
        len(metrics_list), org_id, total_org_revenue,
    )
    return {
        "products_computed": len(metrics_list),
        "total_revenue": round(total_org_revenue, 2),
    }


async def build_overview(
    org_id: str,
    period: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    **kwargs,
) -> Optional[dict]:
    """Build product catalog overview for the module page.

    Wave 1 (PP.2) — restructured to mirror the Customer Insights pattern:
    every KPI carries ``{value, previous, delta_pct}`` so the UI can
    render comparison badges, AND we keep the flat ``kpis`` shape for
    backward compatibility with the legacy ProductCatalogPage during
    the consolidation window.

    Period semantics:
      - ``value``    aggregated over the requested window
      - ``previous`` aggregated over the immediately preceding window of
                     the same length (e.g. 30d → previous 30d)
      - ``delta_pct`` = percentage_delta(value, previous)

    Reads from:
      - ``product_metrics_collection``  — life-of-product aggregates
        (the materialized metric set is NOT period-filtered; used for
        ABC class, category mix, and the top-products list).
      - ``sales_records_collection``    — period-filtered aggregations
        for revenue / cost / margin in the current and previous windows.
      - ``products_collection``         — active count (master data).
    """
    # ── Period parsing ─────────────────────────────────────────────────────
    # The helpers live in customer_insights/period_filter today (Phase 1
    # shared helpers). A future consolidation step will move them under
    # ``core/`` to remove the cross-module import; for now we accept the
    # coupling since both pages share the exact same window semantics.
    from modules.customer_insights.period_filter import (
        parse_period as _parse_period,
        previous_period as _previous_period,
    )
    from modules.customer_insights.formulas import (
        percentage_delta as _percentage_delta,
    )

    window = _parse_period(period, start=start_date, end=end_date)
    prev_window = _previous_period(window)

    # Read materialized metrics (life-of-product). We still depend on these
    # for ABC classification, category mix, top-products list, and the
    # cost-coverage indicator — they're all "structural" views of the
    # catalog that don't need period filtering.
    cursor = product_metrics_collection.find(
        {"organization_id": org_id},
        {"_id": 0},
    ).sort("total_revenue", -1)
    metrics = await cursor.to_list(length=500)

    if not metrics:
        return None

    # Count active products from master data — strictly a "now" snapshot.
    active_count = await products_collection.count_documents(
        {"organization_id": org_id, "is_active": True}
    )

    # ── Period-filtered revenue + cost aggregates ──────────────────────────
    # Aggregations at the org level for current and previous windows.
    # Reason: a merchant looking at "Performance Prodotti" with a 30-day
    # filter wants the totals for those 30 days, not life-of-product.
    revenue_current, cost_current, units_current = await _aggregate_period(
        org_id, window.start_iso, window.end_iso
    )
    revenue_previous, cost_previous, units_previous = await _aggregate_period(
        org_id, prev_window.start_iso, prev_window.end_iso
    )

    # Products with sales / cost — both computed off the period set.
    products_with_sales_current = await _count_products_with_sales(
        org_id, window.start_iso, window.end_iso
    )
    products_with_sales_previous = await _count_products_with_sales(
        org_id, prev_window.start_iso, prev_window.end_iso
    )

    has_cost_data = cost_current > 0
    has_cost_data_prev = cost_previous > 0

    weighted_margin_current = round(
        (revenue_current - cost_current) / revenue_current * 100, 1
    ) if has_cost_data and revenue_current > 0 else None
    weighted_margin_previous = round(
        (revenue_previous - cost_previous) / revenue_previous * 100, 1
    ) if has_cost_data_prev and revenue_previous > 0 else None

    # Per-product margin list — only for products that actually sold
    # in the period AND have cost configured. Used both for avg margin
    # and "most profitable" KPI.
    per_product_period = await _per_product_period(
        org_id, window.start_iso, window.end_iso
    )
    per_product_period_prev = await _per_product_period(
        org_id, prev_window.start_iso, prev_window.end_iso
    )

    margins = [p["margin_pct"] for p in per_product_period if p.get("margin_pct") is not None]
    margins_prev = [p["margin_pct"] for p in per_product_period_prev if p.get("margin_pct") is not None]
    avg_margin = round(sum(margins) / len(margins), 1) if margins else None
    avg_margin_prev = round(sum(margins_prev) / len(margins_prev), 1) if margins_prev else None

    # Cost coverage — share of products-with-sales that have a configured cost.
    products_with_cost_current = sum(1 for p in per_product_period if p.get("total_cost", 0) > 0)
    cost_coverage_pct = round(
        products_with_cost_current / len(per_product_period) * 100, 1
    ) if per_product_period else 0

    # ── Top seller / most profitable (period-filtered) ─────────────────────
    # Build a quick lookup so we can substitute the materialised product
    # name (clean) for the raw description carried in sales_records (which
    # often looks like "Ordine ORD-0002: Pizza x 1.0").
    name_by_pid = {m["product_id"]: m["product_name"] for m in metrics}
    def _clean_name(p):
        return name_by_pid.get(p["product_id"]) or p.get("product_name") or "—"

    sorted_by_revenue = sorted(per_product_period, key=lambda p: p["total_revenue"], reverse=True)
    sorted_by_profit = sorted(
        [p for p in per_product_period if p.get("profit") is not None],
        key=lambda p: p["profit"], reverse=True,
    )
    top_seller = sorted_by_revenue[0] if sorted_by_revenue else None
    sorted_by_revenue_prev = sorted(per_product_period_prev, key=lambda p: p["total_revenue"], reverse=True)
    top_seller_prev = sorted_by_revenue_prev[0] if sorted_by_revenue_prev else None

    most_profitable = sorted_by_profit[0] if sorted_by_profit else None

    # ── Concentration top 10 — period-filtered ─────────────────────────────
    top10_revenue = sum(p["total_revenue"] for p in sorted_by_revenue[:10])
    top10_concentration = round(
        top10_revenue / revenue_current * 100, 1
    ) if revenue_current > 0 else None
    sorted_by_revenue_prev_full = sorted_by_revenue_prev
    top10_revenue_prev = sum(p["total_revenue"] for p in sorted_by_revenue_prev_full[:10])
    top10_concentration_prev = round(
        top10_revenue_prev / revenue_previous * 100, 1
    ) if revenue_previous > 0 else None

    # ── ABC distribution (structural, NOT period-filtered) ────────────────
    abc_counts = {"A": 0, "B": 0, "C": 0}
    for m in metrics:
        cls = m.get("abc_class", "C")
        abc_counts[cls] = abc_counts.get(cls, 0) + 1

    # ── Top products table — period-filtered ───────────────────────────────
    top_products = []
    for p in sorted_by_revenue[:20]:
        # Look up structural fields from the materialized metric row when
        # we have one (carries ABC class, item_type, etc.).
        struct = next((m for m in metrics if m["product_id"] == p["product_id"]), {})
        top_products.append({
            "product_id": p["product_id"],
            "product_name": _clean_name(p),
            "sku": struct.get("sku"),
            "category": struct.get("category"),
            "total_revenue": round(p["total_revenue"], 2),
            "total_cost": round(p.get("total_cost") or 0, 2),
            "margin_pct": p.get("margin_pct"),
            "profit": round(p["profit"], 2) if p.get("profit") is not None else None,
            "total_units_sold": p.get("total_units_sold", 0),
            "trend_30d_pct": struct.get("trend_30d_pct", 0),
            "abc_class": struct.get("abc_class", "C"),
            "item_type": struct.get("item_type", "physical"),
        })

    # ── Category breakdown — period-filtered ───────────────────────────────
    cat_revenue = defaultdict(float)
    for p in per_product_period:
        struct = next((m for m in metrics if m["product_id"] == p["product_id"]), {})
        cat = struct.get("category") or "Senza categoria"
        cat_revenue[cat] += p["total_revenue"]
    categories = sorted(
        [{"category": k, "total_revenue": round(v, 2)} for k, v in cat_revenue.items()],
        key=lambda x: x["total_revenue"],
        reverse=True,
    )[:10]

    # ── KPI envelope helpers ───────────────────────────────────────────────
    def _kpi(value, previous):
        return {
            "value": value,
            "previous": previous,
            "delta_pct": _percentage_delta(value, previous) if (
                isinstance(value, (int, float)) and isinstance(previous, (int, float))
            ) else None,
        }

    return {
        "module_key": "product_catalog",
        "has_data": True,
        "period": {
            "label": window.label,
            "start": window.start_iso,
            "end": window.end_iso,
        },
        # ── New shape: per-KPI envelope (consumed by the new
        # ProductPerformancePage via InsightCard). Add new KPIs HERE.
        "kpi": {
            "totalRevenue": _kpi(round(revenue_current, 2), round(revenue_previous, 2)),
            "totalCost": _kpi(
                round(cost_current, 2) if has_cost_data else None,
                round(cost_previous, 2) if has_cost_data_prev else None,
            ),
            "weightedMargin": _kpi(weighted_margin_current, weighted_margin_previous),
            "avgMargin": _kpi(avg_margin, avg_margin_prev),
            "activeProducts": _kpi(active_count, None),
            "productsWithSales": _kpi(
                products_with_sales_current, products_with_sales_previous
            ),
            "topSeller": {
                "value": _clean_name(top_seller) if top_seller else None,
                "subvalue": round(top_seller["total_revenue"], 2) if top_seller else None,
                "product_id": top_seller["product_id"] if top_seller else None,
                "previous": _clean_name(top_seller_prev) if top_seller_prev else None,
            },
            "mostProfitable": {
                "value": _clean_name(most_profitable) if most_profitable else None,
                "subvalue": round(most_profitable["profit"], 2) if most_profitable else None,
                "product_id": most_profitable["product_id"] if most_profitable else None,
            },
            "costCoverage": _kpi(cost_coverage_pct, None),
            "top10Concentration": _kpi(top10_concentration, top10_concentration_prev),
        },
        # ── Legacy flat shape (consumed by the old ProductCatalogPage —
        # will be removed at PP.9 cleanup once the new page is live).
        "kpis": {
            "active_products": active_count,
            "products_with_sales": products_with_sales_current,
            "total_revenue": round(revenue_current, 2),
            "total_cost": round(cost_current, 2),
            "has_cost_data": has_cost_data,
            "products_with_cost": products_with_cost_current,
            "cost_coverage_pct": cost_coverage_pct,
            "avg_margin_pct": avg_margin,
            "weighted_margin_pct": weighted_margin_current,
            "top_seller_name": _clean_name(top_seller) if top_seller else None,
            "top_seller_revenue": round(top_seller["total_revenue"], 2) if top_seller else 0,
            "total_order_revenue": round(sum(m.get("order_revenue", 0) for m in metrics), 2),
            "total_order_count": sum(m.get("order_count", 0) for m in metrics),
            "avg_cancellation_rate_pct": round(
                sum(m.get("cancellation_rate_pct", 0) for m in metrics) / len(metrics), 1
            ) if metrics else 0,
            "event_products": sum(1 for m in metrics if m.get("item_type") == "event_ticket"),
            "booking_products": sum(1 for m in metrics if m.get("item_type") == "booking"),
            "rental_products": sum(1 for m in metrics if m.get("item_type") == "rental"),
        },
        "abc_distribution": abc_counts,
        "top_products": top_products,
        "categories": categories,
    }


# ── Period-filtered aggregation helpers (PP.2) ───────────────────────────────


async def _aggregate_period(org_id: str, start_iso: str, end_iso: str):
    """Total revenue + cost + units for the org in [start_iso, end_iso].

    Cost is the snapshot ``cost_at_sale × 1`` per sales record (each
    record is 1 unit by convention — see order_service). Falls back to
    the legacy materialized cost ratio when ``cost_at_sale`` is missing
    on older records.

    Returns (revenue, cost, units).
    """
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "product_id": {"$ne": None, "$exists": True},
                "date": {"$gte": start_iso, "$lte": end_iso},
            }
        },
        {
            "$group": {
                "_id": None,
                "revenue": {"$sum": "$amount"},
                # cost_at_sale is the Wave-1 snapshot field (W1.S7).
                # When absent (legacy records pre-W1.S7), the addition
                # uses 0 — we fall back below via _per_product_period
                # which consults the resolver for those rows.
                "cost": {"$sum": {"$ifNull": ["$cost_at_sale", 0]}},
                "units": {"$sum": 1},
            }
        },
    ]
    docs = await sales_records_collection.aggregate(pipeline).to_list(1)
    if not docs:
        return 0.0, 0.0, 0
    d = docs[0]
    return d.get("revenue") or 0.0, d.get("cost") or 0.0, d.get("units") or 0


async def _count_products_with_sales(org_id: str, start_iso: str, end_iso: str) -> int:
    """Distinct count of products with ≥1 sale in [start_iso, end_iso]."""
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "product_id": {"$ne": None, "$exists": True},
                "date": {"$gte": start_iso, "$lte": end_iso},
            }
        },
        {"$group": {"_id": "$product_id"}},
        {"$count": "n"},
    ]
    docs = await sales_records_collection.aggregate(pipeline).to_list(1)
    return docs[0]["n"] if docs else 0


async def _per_product_period(org_id: str, start_iso: str, end_iso: str):
    """Per-product aggregates for [start_iso, end_iso].

    Each entry::

        {
          "product_id": str,
          "product_name": str|None,    # from sales_records.description fallback
          "total_revenue": float,
          "total_cost": float,           # 0 if cost_at_sale missing on all records
          "total_units_sold": int,
          "margin_pct": float|None,
          "profit": float|None,
        }

    Used to compute period-filtered top_products, top_seller,
    most_profitable, average margin and category breakdown.
    """
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "product_id": {"$ne": None, "$exists": True},
                "date": {"$gte": start_iso, "$lte": end_iso},
            }
        },
        {
            "$group": {
                "_id": "$product_id",
                "revenue": {"$sum": "$amount"},
                "cost": {"$sum": {"$ifNull": ["$cost_at_sale", 0]}},
                "units": {"$sum": 1},
                "any_name": {"$first": "$description"},  # heuristic fallback
            }
        },
    ]
    out = []
    async for d in sales_records_collection.aggregate(pipeline):
        revenue = d.get("revenue") or 0
        cost = d.get("cost") or 0
        # margin_pct only when cost is known (> 0); profit is None
        # when cost is 0 (treated as "unknown" rather than 100% margin).
        has_cost = cost > 0
        margin_pct = round((revenue - cost) / revenue * 100, 1) if has_cost and revenue > 0 else None
        profit = round(revenue - cost, 2) if has_cost else None
        out.append({
            "product_id": d["_id"],
            "product_name": d.get("any_name"),
            "total_revenue": revenue,
            "total_cost": cost,
            "total_units_sold": d.get("units", 0),
            "margin_pct": margin_pct,
            "profit": profit,
        })
    return out


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _compute_commerce_product_metrics(org_id: str) -> Dict[str, dict]:
    """Compute order-derived metrics per product from orders + events + blocked_slots.

    Returns dict keyed by product_id with:
      item_type, order_count, order_revenue, cancellation_rate_pct,
      event_fill_rate_pct, event_total_capacity, booking_utilization_pct, rental_utilization_pct
    """
    from database import orders_collection, blocked_slots_collection, products_collection
    result: Dict[str, dict] = {}

    try:
        # 1. Product item_type map
        prod_cursor = products_collection.find(
            {"organization_id": org_id, "is_active": True},
            {"_id": 0, "id": 1, "item_type": 1},
        )
        type_map = {}
        async for p in prod_cursor:
            type_map[p["id"]] = p.get("item_type", "physical")

        # 2. Order aggregates per product (from order line items)
        # Project only needed fields before $unwind to reduce memory/IO.
        order_pipeline = [
            {"$match": {"organization_id": org_id, "items": {"$ne": []}}},
            {"$project": {"_id": 0, "status": 1,
                          "items.product_id": 1, "items.quantity": 1, "items.line_total": 1}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": {"pid": "$items.product_id", "status": "$status"},
                "count": {"$sum": "$items.quantity"},
                "revenue": {"$sum": "$items.line_total"},
            }},
        ]
        raw_orders: Dict[str, dict] = {}
        async for doc in orders_collection.aggregate(order_pipeline):
            pid = doc["_id"]["pid"]
            status = doc["_id"]["status"]
            if pid not in raw_orders:
                raw_orders[pid] = {"total": 0, "revenue": 0, "cancelled": 0}
            raw_orders[pid]["total"] += doc["count"]
            raw_orders[pid]["revenue"] += doc["revenue"]
            if status == "cancelled":
                raw_orders[pid]["cancelled"] += doc["count"]

        for pid, data in raw_orders.items():
            active_rev = round(data["revenue"] - (raw_orders.get(pid, {}).get("cancelled", 0) * (data["revenue"] / data["total"] if data["total"] > 0 else 0)), 2) if data["total"] > 0 else 0
            # Simpler: revenue from non-cancelled = total revenue (cancelled items have 0 in line_total after storno)
            result[pid] = {
                "item_type": type_map.get(pid, "physical"),
                "order_count": data["total"],
                "order_revenue": round(data["revenue"], 2),
                "cancellation_rate_pct": round(data["cancelled"] / data["total"] * 100, 1) if data["total"] > 0 else 0,
                "event_fill_rate_pct": None,
                "event_total_capacity": None,
                "booking_utilization_pct": None,
                "rental_utilization_pct": None,
            }

        # 3. Event fill rates (event_ticket products)
        event_pids = [pid for pid, t in type_map.items() if t == "event_ticket"]
        if event_pids:
            eo_coll = __import__("database", fromlist=["db"]).db.event_occurrences
            occ_cursor = eo_coll.find(
                {"organization_id": org_id, "product_id": {"$in": event_pids},
                 "status": {"$in": ["published", "closed"]}, "capacity": {"$gt": 0}},
                {"_id": 0, "id": 1, "product_id": 1, "capacity": 1},
            )
            occs = await occ_cursor.to_list(500)
            occ_ids = [o["id"] for o in occs]

            booked_map = {}
            if occ_ids:
                booked_pipeline = [
                    {"$match": {"organization_id": org_id, "status": {"$ne": "cancelled"},
                                 "items.occurrence_id": {"$in": occ_ids}}},
                    {"$unwind": "$items"},
                    {"$match": {"items.occurrence_id": {"$in": occ_ids}}},
                    {"$group": {"_id": "$items.occurrence_id", "booked": {"$sum": "$items.quantity"}}},
                ]
                async for doc in orders_collection.aggregate(booked_pipeline):
                    booked_map[doc["_id"]] = int(doc["booked"])

            # Aggregate fill per product
            product_fill: Dict[str, list] = {}
            product_cap: Dict[str, int] = {}
            for occ in occs:
                pid = occ["product_id"]
                cap = occ["capacity"]
                booked = booked_map.get(occ["id"], 0)
                fill = round(booked / cap * 100, 1) if cap > 0 else 0
                product_fill.setdefault(pid, []).append(fill)
                product_cap[pid] = product_cap.get(pid, 0) + cap

            for pid in event_pids:
                if pid not in result:
                    result[pid] = {"item_type": "event_ticket", "order_count": 0, "order_revenue": 0,
                                   "cancellation_rate_pct": 0, "event_fill_rate_pct": None,
                                   "event_total_capacity": None, "booking_utilization_pct": None, "rental_utilization_pct": None}
                fills = product_fill.get(pid, [])
                result[pid]["event_fill_rate_pct"] = round(sum(fills) / len(fills), 1) if fills else None
                result[pid]["event_total_capacity"] = product_cap.get(pid)

        # 4. Booking utilization
        booking_pids = [pid for pid, t in type_map.items() if t == "booking"]
        if booking_pids:
            from datetime import date, timedelta
            today = date.today()
            d30_ago = (today - timedelta(days=30)).isoformat()
            today_str = today.isoformat()

            book_pipeline = [
                {"$match": {"organization_id": org_id, "reason": "booking",
                             "product_id": {"$in": booking_pids},
                             "date": {"$gte": d30_ago, "$lte": today_str}}},
                {"$group": {"_id": "$product_id", "dates": {"$addToSet": "$date"}}},
                {"$project": {"product_id": "$_id", "days_booked": {"$size": "$dates"}, "_id": 0}},
            ]
            async for doc in blocked_slots_collection.aggregate(book_pipeline):
                pid = doc["product_id"]
                if pid not in result:
                    result[pid] = {"item_type": "booking", "order_count": 0, "order_revenue": 0,
                                   "cancellation_rate_pct": 0, "event_fill_rate_pct": None,
                                   "event_total_capacity": None, "booking_utilization_pct": None, "rental_utilization_pct": None}
                # Rough: weekday slots in 30 days ≈ 22 days, assuming 9 slots/day = 198 slots
                # For simplicity: days_booked / 22 weekdays * 100
                result[pid]["booking_utilization_pct"] = round(doc["days_booked"] / 22 * 100, 1)

        # 5. Rental utilization
        rental_pids = [pid for pid, t in type_map.items() if t == "rental"]
        if rental_pids:
            from datetime import date, timedelta
            today = date.today()
            d30_ago = (today - timedelta(days=30)).isoformat()
            today_str = today.isoformat()

            rental_pipeline = [
                {"$match": {"organization_id": org_id, "reason": "rental",
                             "product_id": {"$in": rental_pids},
                             "date": {"$gte": d30_ago, "$lte": today_str}}},
                {"$group": {"_id": "$product_id", "dates": {"$addToSet": "$date"}}},
                {"$project": {"product_id": "$_id", "days_booked": {"$size": "$dates"}, "_id": 0}},
            ]
            async for doc in blocked_slots_collection.aggregate(rental_pipeline):
                pid = doc["product_id"]
                if pid not in result:
                    result[pid] = {"item_type": "rental", "order_count": 0, "order_revenue": 0,
                                   "cancellation_rate_pct": 0, "event_fill_rate_pct": None,
                                   "event_total_capacity": None, "booking_utilization_pct": None, "rental_utilization_pct": None}
                result[pid]["rental_utilization_pct"] = round(doc["days_booked"] / 30 * 100, 1)

        # Ensure all products have item_type even without orders
        for pid, itype in type_map.items():
            if pid not in result:
                result[pid] = {"item_type": itype, "order_count": 0, "order_revenue": 0,
                               "cancellation_rate_pct": 0, "event_fill_rate_pct": None,
                               "event_total_capacity": None, "booking_utilization_pct": None, "rental_utilization_pct": None}

    except Exception as e:
        logger.warning("product_catalog: _compute_commerce_product_metrics failed: %s", e)

    return result


async def _sum_revenue_by_product(org_id: str, start: str, end: str) -> dict:
    """Aggregate revenue per product_id for a date range."""
    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "product_id": {"$ne": None, "$exists": True},
            "date": {"$gte": start, "$lte": end},
        }},
        {"$group": {"_id": "$product_id", "total": {"$sum": "$amount"}}},
    ]
    result = {}
    async for doc in sales_records_collection.aggregate(pipeline):
        result[doc["_id"]] = doc["total"] or 0
    return result
