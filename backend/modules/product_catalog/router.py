"""
Product Catalog Module Router — analytics endpoints.

Note: CRUD operations remain at /api/products (routers/products.py).
These endpoints serve materialized analytics from product_metrics.

Wave 1 (W1.S3): adds three cost-related endpoints supporting the new
``cost_source`` configuration flow:

  GET  /modules/product-catalog/cost-categories
       → list of distinct purchase categories the org actually uses,
         each annotated with units in use and a "use count". Feeds the
         category dropdown in the admin UI so the merchant never types
         a category name (and never mistypes one).

  POST /modules/product-catalog/cost-preview
       → resolve a hypothetical cost_source for a product WITHOUT
         saving. Powers the live preview in the admin UI: the merchant
         tweaks components and instantly sees the resulting unit cost
         + decomposition + confidence.

  GET  /modules/product-catalog/cost-preview/{product_id}
       → resolve the CURRENT saved cost_source of an existing product.
         Read-only sibling of the POST endpoint, useful for the list
         view and the AI Analyst.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from auth import get_current_user, require_admin
from database import (
    product_metrics_collection,
    products_collection,
    purchase_records_collection,
)
from models.cost_source import CostSource

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/modules/product-catalog",
    tags=["Product Catalog"],
)


@router.get("/metrics")
async def list_product_metrics(
    category: str = None,
    abc_class: str = None,
    current_user: dict = Depends(get_current_user),
):
    """List all products with computed metrics (revenue, margin, trend, ABC)."""
    org_id = current_user["organization_id"]
    query = {"organization_id": org_id}
    if category:
        import re as _re
        query["category"] = {"$regex": _re.escape(category), "$options": "i"}
    if abc_class and abc_class in ("A", "B", "C"):
        query["abc_class"] = abc_class

    cursor = product_metrics_collection.find(
        query, {"_id": 0}
    ).sort("total_revenue", -1).limit(200)
    metrics = await cursor.to_list(length=200)
    return {"metrics": metrics, "total": len(metrics)}


@router.get("/metrics/{product_id}")
async def get_product_metric(
    product_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get detailed metrics for a single product."""
    org_id = current_user["organization_id"]
    doc = await product_metrics_collection.find_one(
        {"organization_id": org_id, "product_id": product_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product metrics not found. Run a data refresh first.",
        )
    return doc


@router.get("/abc")
async def get_abc_distribution(
    current_user: dict = Depends(get_current_user),
):
    """Get ABC classification distribution."""
    org_id = current_user["organization_id"]
    pipeline = [
        {"$match": {"organization_id": org_id}},
        {"$group": {
            "_id": "$abc_class",
            "count": {"$sum": 1},
            "total_revenue": {"$sum": "$total_revenue"},
            "avg_margin_pct": {"$avg": "$margin_pct"},
        }},
        {"$sort": {"_id": 1}},
    ]
    cursor = product_metrics_collection.aggregate(pipeline)
    classes = await cursor.to_list(length=3)
    return {
        "abc": [
            {
                "class": c["_id"],
                "count": c["count"],
                "total_revenue": round(c["total_revenue"], 2),
                "avg_margin_pct": round(c["avg_margin_pct"], 1),
            }
            for c in classes
        ]
    }


@router.post("/refresh")
async def refresh_metrics(
    current_user: dict = Depends(require_admin),
):
    """Manually trigger product metrics refresh (admin only)."""
    from modules.product_catalog.service import refresh_product_metrics
    result = await refresh_product_metrics(current_user["organization_id"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Intelligence Banner (IB.1+) — Health Check endpoint
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/health-check")
async def health_check(
    period: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Run every registered health check on the org's product catalog
    and return the issues found.

    Drives the Intelligence Banner at the top of Product Performance.
    Empty ``checks`` array means everything is fine (banner renders
    a "all good" pill).

    Output shape::

        {
          "summary": {
            "total_checks_run": int,
            "issues_found": int,
            "critical": int, "warnings": int, "info": int
          },
          "period": {"label": "30d", "start": "...", "end": "..."},
          "checks": [
            {
              "id": "products_without_cost",
              "category": "data_quality",
              "severity": "critical",
              "metrics": {...},
              "drill_data": {"type": "product_list", "items": [...]},
              "actions": [{"type": "bulk_configure_cost", "target_ids": [...]}, ...]
            },
            ...
          ]
        }

    See ``health_checks.py`` for the per-check definitions and
    threshold constants. Each check is a pure async function that the
    orchestrator runs in parallel, so adding the next check (e.g. the
    Cashflow-coherence checks in IB.2) is a one-line edit there with
    zero impact on this endpoint.
    """
    from modules.product_catalog.health_checks import run_all_checks
    return await run_all_checks(
        current_user["organization_id"],
        period=period,
        start_date=start_date,
        end_date=end_date,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Wave 1 (W1.S3) — Cost configuration support endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/cost-categories")
async def list_cost_categories(
    current_user: dict = Depends(get_current_user),
):
    """List purchase items actually used by this org, with their unit-
    level pricing aggregates.

    Source of truth for the "Prodotto degli acquisti" picker in the
    CostSourceEditor. The merchant sees exactly the items they have
    already used in the Purchases module — eliminating the entire class
    of "typed 'Pasta' here but 'pasta' there" mismatches that would
    silently break the resolver.

    Output shape (categories sorted by usage count desc)::

        {
          "categories": [
            {
              "name": "Farine e impasti",
              "units": ["kg", "g"],          # back-compat (string list)
              "unit_details": [              # NEW: per-unit aggregates
                {
                  "unit": "kg",
                  "purchase_count": 38,
                  "avg_unit_price": 1.25,    # Σ total_price / Σ quantity
                  "total_spent": 1860.0      # for the share path UI
                },
                {
                  "unit": "g",
                  "purchase_count": 9,
                  "avg_unit_price": 0.0012,
                  "total_spent": 80.0
                }
              ],
              "purchase_count": 47,           # all units combined
              "total_spent": 1940.0,           # all units combined (categ share UI)
              "last_seen": "2026-04-15"
            },
            ...
          ]
        }

    Why we expose ``unit_details``
    ------------------------------
    The CostSourceEditor needs three pieces of information when the
    merchant picks an item:

      1. Which units of measure the item has actually been bought in
         (so the unit selector can be pre-filtered or auto-resolved).
      2. The average price per unit (so the editor can show
         "Prezzo medio: €2.50/kg" and a live contribution preview).
      3. The total spent on the item (so the ``category_share`` flow
         can show the pool the share % is applied to).

    The legacy ``units`` string array is kept alongside for backward
    compatibility with any consumer that hasn't migrated yet.

    Empty names and ``None`` categories are filtered out — they are
    useless for exact-string matching downstream in the resolver.
    """
    org_id = current_user["organization_id"]
    # We aggregate at (category, unit) granularity first so we can
    # compute a meaningful WAC per unit. Then we group by category to
    # build the per-category envelope with unit_details inside.
    #
    # Note: Python dict literals collapse duplicate keys, so the filter
    # must use $nin to express "neither None nor empty string" in a
    # single condition. Using $ne twice would silently lose one.
    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "category": {"$nin": [None, ""]},
            }
        },
        # Per (category, unit) aggregation.
        {
            "$group": {
                "_id": {"category": "$category", "unit": "$unit"},
                "purchase_count": {"$sum": 1},
                # Spent: prefer total_price; fall back to quantity*unit_price
                # then to amount. Matches the same ladder used by the
                # resolver — see ``services/cost_resolver._spent_expression``.
                "total_spent": {
                    "$sum": {
                        "$ifNull": [
                            "$total_price",
                            {
                                "$ifNull": [
                                    {"$multiply": [
                                        {"$ifNull": ["$quantity", 0]},
                                        {"$ifNull": ["$unit_price", 0]},
                                    ]},
                                    {"$ifNull": ["$amount", 0]},
                                ]
                            },
                        ]
                    }
                },
                # Sum of quantities — only meaningful when unit is set;
                # records with quantity=null contribute 0.
                "total_qty": {"$sum": {"$ifNull": ["$quantity", 0]}},
                "last_seen": {"$max": "$date"},
            }
        },
        # Then group by category to fold unit_details together.
        {
            "$group": {
                "_id": "$_id.category",
                "unit_details": {
                    "$push": {
                        "unit": "$_id.unit",
                        "purchase_count": "$purchase_count",
                        "total_spent": "$total_spent",
                        "total_qty": "$total_qty",
                    }
                },
                "purchase_count": {"$sum": "$purchase_count"},
                "total_spent": {"$sum": "$total_spent"},
                "last_seen": {"$max": "$last_seen"},
            }
        },
        {"$sort": {"purchase_count": -1}},
        {"$limit": 200},  # defensive — no org realistically has 200+ categories
    ]
    docs = await purchase_records_collection.aggregate(pipeline).to_list(200)
    categories = []
    for d in docs:
        # Build the per-unit details list. Strip null/empty units
        # (they creep in from legacy imports) and compute avg_unit_price
        # only where we can divide safely.
        details_in = d.get("unit_details") or []
        clean_details = []
        for u in details_in:
            unit_name = u.get("unit")
            if not unit_name:  # null/empty unit → skip
                continue
            qty = u.get("total_qty") or 0
            spent = u.get("total_spent") or 0
            avg = round(spent / qty, 4) if qty > 0 else None
            clean_details.append({
                "unit": unit_name,
                "purchase_count": u.get("purchase_count", 0),
                "total_spent": round(spent, 2),
                "avg_unit_price": avg,
            })
        # Sort unit_details so the most-used unit comes first — the UI
        # uses this order to auto-select a default qty_unit.
        clean_details.sort(key=lambda x: x["purchase_count"], reverse=True)

        # Legacy ``units`` field (string list) for back-compat with the
        # original W1.S3 contract. The new ``unit_details`` is the
        # authoritative source going forward.
        units = [u["unit"] for u in clean_details]

        categories.append({
            "name": d["_id"],
            "units": units,
            "unit_details": clean_details,
            "purchase_count": d.get("purchase_count", 0),
            "total_spent": round(d.get("total_spent") or 0, 2),
            "last_seen": d.get("last_seen"),
        })
    return {"categories": categories}


class CostPreviewRequest(BaseModel):
    """Body for POST /cost-preview.

    The ``cost_source`` field carries a candidate composition that the
    admin is editing in the UI. We accept the same model the API stores
    so the preview matches exactly what would be persisted.

    ``product_id`` is required when ANY component is ``category_share``
    with auto-proportional share (share_pct=None), because the auto
    distribution needs to know which product is asking — otherwise we
    can't compute "this product's revenue / total linking revenue".
    For purely manual or category_quantity compositions the field is
    optional.

    ``product_category`` and ``product_item_type`` are required when
    using an ``org_average`` component with scope=same_category or
    scope=same_item_type respectively. Sent from the admin UI when the
    product is still unsaved (no DB row yet).
    """

    model_config = ConfigDict(extra="ignore")

    cost_source: CostSource
    product_id: Optional[str] = None
    product_category: Optional[str] = None
    product_item_type: Optional[str] = None


@router.post("/cost-preview")
async def preview_cost(
    body: CostPreviewRequest,
    current_user: dict = Depends(get_current_user),
):
    """Resolve a hypothetical cost_source WITHOUT saving anything.

    Drives the "Anteprima costo unitario" panel in the admin UI: while
    the merchant adds/removes components and tweaks values, the UI
    calls this endpoint with the in-memory state and renders the
    resolver's output (total + decomposition + confidence).

    Returns the same envelope the resolver produces, JSON-encoded:
        {
            "value": 2.43,
            "source": "mixed",
            "confidence": "mixed",
            "method": "wac_90d",
            "period_start": "2026-02-14",
            "period_end": "2026-05-14",
            "decomposition": [ {type, label, contribution, details, failed}, ... ]
        }
    """
    org_id = current_user["organization_id"]

    # Synthesise a product dict that the resolver expects. We don't
    # touch the database — this is a pure preview path.
    synth_product = {
        "id": body.product_id or "__preview__",
        "organization_id": org_id,
        "category": body.product_category,
        "item_type": body.product_item_type,
        "cost_source": body.cost_source.model_dump(),
    }

    # Local import to avoid pulling the resolver (which queries Mongo
    # asynchronously) into module import time and slowing app startup.
    from services.cost_resolver import resolve_unit_cost

    result = await resolve_unit_cost(synth_product, org_id)
    return {
        "value": result.value,
        "source": result.source,
        "confidence": result.confidence,
        "method": result.method,
        "period_start": result.period_start,
        "period_end": result.period_end,
        "decomposition": result.decomposition,
    }


@router.get("/cost-preview/{product_id}")
async def preview_cost_saved(
    product_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Resolve the CURRENT saved cost_source of an existing product.

    Read-only counterpart of POST /cost-preview, useful for:
      - List views that want to show the current resolved cost beside
        each product without computing on the client.
      - The AI Analyst's product-cost-trend tool (W1.S6).
      - Debugging in production: "what does the resolver think this
        product costs right now?"

    Returns 404 when the product doesn't exist or doesn't belong to
    the calling org.
    """
    org_id = current_user["organization_id"]
    product = await products_collection.find_one(
        {"organization_id": org_id, "id": product_id},
        {"_id": 0},
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    from services.cost_resolver import resolve_unit_cost

    result = await resolve_unit_cost(product, org_id)
    return {
        "product_id": product_id,
        "product_name": product.get("name"),
        "value": result.value,
        "source": result.source,
        "confidence": result.confidence,
        "method": result.method,
        "period_start": result.period_start,
        "period_end": result.period_end,
        "decomposition": result.decomposition,
    }
