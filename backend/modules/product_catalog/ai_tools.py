"""
Product Catalog AI Tools — tool definitions and executor for AI chat.

Tools allow the AI assistant to query product analytics, margins,
trends, and recommendations from materialized product_metrics.
"""

import logging
from typing import List, Dict, Any

from database import product_metrics_collection, sales_records_collection

logger = logging.getLogger(__name__)


# ── Tool Definitions (provider-agnostic) ────────────────────────────────────

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "query_product_analytics",
        "description": (
            "Restituisce KPI generali del catalogo prodotti: "
            "numero prodotti attivi, margine medio, distribuzione ABC, top sellers. "
            "Usare per rispondere a domande generali sui prodotti dell'azienda."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "query_product_margins",
        "description": (
            "Restituisce il dettaglio dei margini per prodotto o categoria. "
            "Usare quando l'utente chiede 'quali prodotti hanno margine alto/basso', "
            "'quanto guadagno su X', o analisi di profittabilità per prodotto."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filtra per categoria prodotto (opzionale)",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["margin_pct", "total_revenue", "margin_amount"],
                    "description": "Campo di ordinamento (default: margin_pct)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Numero massimo di prodotti (default: 10)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "query_product_trend",
        "description": (
            "Restituisce il trend di vendita per i prodotti, FISSO sulla finestra "
            "ULTIMI 30 GIORNI vs 30 GIORNI PRECEDENTI (snapshot materializzato dal "
            "job product_metrics — non ricomputabile su altri periodi senza "
            "chiamare query_business_summary). "
            "Usare quando l'utente chiede 'quali prodotti stanno crescendo/calando "
            "negli ultimi 30 giorni', 'trend vendite prodotti recenti'. "
            "Per finestre diverse (YTD, MTD, custom) usa query_business_summary o "
            "query_cashflow_summary. "
            "Accetta period / start_date / end_date per parità di contratto, ma "
            "quando il periodo richiesto NON è '30d' la risposta contiene un "
            "``_period_caveat`` che indirizza il modello al tool corretto."
        ),
        # Wave 13.5 — period params accepted for contract parity (so the
        # chat dispatcher can auto-inject from period_context without
        # special-casing this tool), but the underlying data is the
        # materialised 30d-vs-prior-30d snapshot. The implementation adds
        # ``_period_caveat`` when the requested period differs from 30d
        # so the model knows it's getting snapshot data, not requested-
        # window data.
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["growing", "declining", "all"],
                    "description": "Filtra per direzione trend (default: all)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Numero massimo di prodotti (default: 10)",
                },
                "period": {
                    "type": "string",
                    "description": (
                        "Periodo richiesto. SUPPORTATO NATIVAMENTE solo '30d'; "
                        "altri valori producono lo stesso snapshot 30d + un caveat."
                    ),
                },
                "start_date": {
                    "type": "string",
                    "description": (
                        "Data inizio (YYYY-MM-DD). Accettata per parità di "
                        "contratto ma ignorata per il calcolo del trend."
                    ),
                },
                "end_date": {
                    "type": "string",
                    "description": (
                        "Data fine (YYYY-MM-DD). Accettata per parità di "
                        "contratto ma ignorata per il calcolo del trend."
                    ),
                },
            },
            "required": [],
        },
    },
    {
        "name": "query_product_recommendations",
        "description": (
            "Restituisce raccomandazioni basate sui dati: prodotti con margine critico, "
            "prodotti star (alto margine + crescita), prodotti in declino. "
            "Usare quando l'utente chiede consigli sui prodotti."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    # ── Wave 7A.3: focused sub-tools extracted from query_product_recommendations.
    # The omnibus tool above stays as the "give me every alert at once" helper;
    # these let the AI ask precise questions with custom thresholds.
    {
        "name": "query_low_stock_products",
        "description": (
            "Restituisce i prodotti fisici con scorta bassa (stock_quantity <= soglia). "
            "Usare per domande tipo 'cosa sta finendo', 'di cosa devo riordinare', "
            "'quali prodotti sono sotto scorta'. Solo prodotti fisici con giacenza tracciata."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "integer",
                    "description": "Soglia massima di stock per considerare il prodotto 'low' (default: 3)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Numero massimo di prodotti (default: 10, max: 50)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "query_underperforming_events",
        "description": (
            "Restituisce gli eventi (item_type=event_ticket) con tasso di riempimento basso. "
            "Usare per 'quali eventi non vendono', 'eventi a rischio', 'fill rate eventi'. "
            "Richiede dati commerce (orders + product_metrics commerce-aware)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "max_fill_rate_pct": {
                    "type": "number",
                    "description": "Soglia massima di fill rate %% per considerare l'evento sottoperformante (default: 30)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Numero massimo di eventi (default: 10, max: 50)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "query_idle_rentals",
        "description": (
            "Restituisce gli asset di noleggio (item_type=rental) con utilizzo basso. "
            "Usare per 'noleggi che non rendono', 'asset fermi', 'utilization noleggi'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "max_utilization_pct": {
                    "type": "number",
                    "description": "Soglia massima di utilization %% per considerare l'asset idle (default: 10)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Numero massimo di asset (default: 10, max: 50)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "query_high_cancellation_products",
        "description": (
            "Restituisce i prodotti/servizi con tasso di cancellazione ordini elevato. "
            "Usare per 'cancellazioni anomale', 'prodotti con problemi di delivery', "
            "'dove perdo ordini'. Richiede dati commerce (orders con stato cancelled)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "min_cancel_rate_pct": {
                    "type": "number",
                    "description": "Soglia minima di cancellation rate %% per includere il prodotto (default: 20)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Numero massimo di prodotti (default: 10, max: 50)",
                },
            },
            "required": [],
        },
    },
]


# ── Tool Executor ───────────────────────────────────────────────────────────

async def execute_tool(org_id: str, tool_name: str, tool_input: dict) -> dict:
    """Dispatch AI tool calls to the appropriate handler."""
    try:
        if tool_name == "query_product_analytics":
            return await _tool_product_analytics(org_id)
        elif tool_name == "query_product_margins":
            return await _tool_product_margins(org_id, tool_input)
        elif tool_name == "query_product_trend":
            return await _tool_product_trend(org_id, tool_input)
        elif tool_name == "query_product_recommendations":
            return await _tool_product_recommendations(org_id)
        elif tool_name == "query_low_stock_products":
            return await _tool_low_stock_products(org_id, tool_input)
        elif tool_name == "query_underperforming_events":
            return await _tool_underperforming_events(org_id, tool_input)
        elif tool_name == "query_idle_rentals":
            return await _tool_idle_rentals(org_id, tool_input)
        elif tool_name == "query_high_cancellation_products":
            return await _tool_high_cancellation_products(org_id, tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as exc:
        logger.error("product_catalog tool %s failed: %s", tool_name, exc)
        return {"error": str(exc)}


# ── Tool Implementations ────────────────────────────────────────────────────

def _epistemic(metrics_count: int) -> dict:
    """Standard epistemic metadata for product tools."""
    return {
        "epistemic_class": "factual",
        "reliability": "high" if metrics_count >= 5 else "conditional",
        "temporal_scope": "all_time_with_trend",
        "temporal_alignment_safe": True,
        "ai_usability": "cite_directly" if metrics_count >= 5 else "qualify_with_caveat",
        "caveat": None if metrics_count >= 5 else "Pochi prodotti con dati — i risultati potrebbero non essere rappresentativi.",
    }


async def _tool_product_analytics(org_id: str) -> dict:
    """General product catalog KPIs."""
    metrics = await product_metrics_collection.find(
        {"organization_id": org_id},
        {"_id": 0},
    ).sort("total_revenue", -1).to_list(length=500)

    if not metrics:
        return {
            "data": {"has_data": False, "message": "Nessun prodotto con dati di vendita trovato."},
            **_epistemic(0),
        }

    total_revenue = sum(m["total_revenue"] for m in metrics)
    total_cost = sum(m["total_cost"] for m in metrics)
    margins = [m["margin_pct"] for m in metrics if m.get("margin_pct") is not None]
    avg_margin = round(sum(margins) / len(margins), 1) if margins else None

    abc = {"A": 0, "B": 0, "C": 0}
    for m in metrics:
        abc[m.get("abc_class", "C")] += 1

    top_5 = [
        {"name": m["product_name"], "revenue": m["total_revenue"], "margin_pct": m["margin_pct"]}
        for m in metrics[:5]
    ]

    # Commerce-derived analytics (v13.0)
    events = [m for m in metrics if m.get("item_type") == "event_ticket"]
    bookings = [m for m in metrics if m.get("item_type") == "booking"]
    rentals = [m for m in metrics if m.get("item_type") == "rental"]
    total_order_revenue = round(sum(m.get("order_revenue", 0) for m in metrics), 2)
    avg_cancel = round(sum(m.get("cancellation_rate_pct", 0) for m in metrics) / len(metrics), 1) if metrics else 0

    commerce_summary = {
        "total_order_revenue": total_order_revenue,
        "avg_cancellation_rate_pct": avg_cancel,
        "revenue_delta_cashflow_vs_orders": round(total_revenue - total_order_revenue, 2) if total_order_revenue > 0 else None,
        "epistemic_note": "Commerce metrics derivano da orders_collection. total_order_revenue puo' differire da total_revenue (cashflow) se ci sono vendite manuali non da ordini.",
        "by_type": {
            "event_ticket": {"count": len(events),
                             "avg_fill_rate": round(sum(e.get("event_fill_rate_pct", 0) or 0 for e in events) / len(events), 1) if events else None},
            "booking": {"count": len(bookings),
                        "avg_utilization": round(sum(b.get("booking_utilization_pct", 0) or 0 for b in bookings) / len(bookings), 1) if bookings else None},
            "rental": {"count": len(rentals),
                       "avg_utilization": round(sum(r.get("rental_utilization_pct", 0) or 0 for r in rentals) / len(rentals), 1) if rentals else None},
        },
    }

    return {
        "data": {
            "has_data": True,
            "total_products_with_sales": len(metrics),
            "total_revenue": round(total_revenue, 2),
            "total_cost": round(total_cost, 2),
            "weighted_margin_pct": round((total_revenue - total_cost) / total_revenue * 100, 1) if total_revenue > 0 else 0,
            "avg_margin_pct": avg_margin,
            "abc_distribution": abc,
            "top_5_by_revenue": top_5,
            "commerce": commerce_summary,
        },
        **_epistemic(len(metrics)),
    }


async def _tool_product_margins(org_id: str, tool_input: dict) -> dict:
    """Detailed margins by product."""
    category = tool_input.get("category")
    sort_by = tool_input.get("sort_by", "margin_pct")
    limit = min(tool_input.get("limit", 10), 50)

    query = {"organization_id": org_id}
    if category:
        query["category"] = {"$regex": category, "$options": "i"}

    sort_field = sort_by if sort_by in ("margin_pct", "total_revenue", "margin_amount") else "margin_pct"
    sort_dir = -1 if sort_field != "margin_pct" else -1  # All descending

    metrics = await product_metrics_collection.find(
        query, {"_id": 0}
    ).sort(sort_field, sort_dir).to_list(length=limit)

    products = [
        {
            "name": m["product_name"],
            "sku": m.get("sku"),
            "category": m.get("category"),
            "item_type": m.get("item_type", "physical"),
            "total_revenue": m["total_revenue"],
            "order_revenue": m.get("order_revenue", 0),
            "total_cost": m["total_cost"],
            "margin_amount": m["margin_amount"],
            "margin_pct": m["margin_pct"],
            "units_sold": m["total_units_sold"],
            "avg_price": m["avg_sale_price"],
            "cancellation_rate_pct": m.get("cancellation_rate_pct", 0),
        }
        for m in metrics
    ]

    return {
        "data": {
            "has_data": bool(products),
            "products": products,
            "filter_category": category,
            "sort_by": sort_field,
        },
        **_epistemic(len(products)),
    }


async def _tool_product_trend(org_id: str, tool_input: dict) -> dict:
    """Product sales trend (materialized 30d vs previous 30d).

    Wave 13.5 — accepts period/start_date/end_date for contract parity
    with other tools (so the chat dispatcher can auto-inject from
    period_context without special-casing), but the underlying
    ``product_metrics_collection`` carries a precomputed
    ``trend_30d_pct`` only. When the request asks for a different
    window we still return the 30d snapshot but attach an explicit
    ``_period_caveat`` so the LLM knows the data is scope-mismatched
    and can either qualify its answer or call the right tool.
    """
    direction = tool_input.get("direction", "all")
    limit = min(tool_input.get("limit", 10), 50)

    # Wave 13.5 — capture what the caller asked for to detect scope mismatch.
    _req_period = (tool_input.get("period") or "").strip().lower()
    _req_start = tool_input.get("start_date")
    _req_end = tool_input.get("end_date")
    # Aliases that resolve to the same window as the materialised data.
    _native_30d_tokens = {"", "30d", "last_30_days", "30days"}
    is_native_30d = (
        _req_period in _native_30d_tokens and not (_req_start and _req_end)
    )

    metrics = await product_metrics_collection.find(
        {"organization_id": org_id},
        {"_id": 0, "product_name": 1, "sku": 1, "category": 1,
         "total_revenue": 1, "trend_30d_pct": 1, "abc_class": 1},
    ).to_list(length=500)

    if direction == "growing":
        metrics = [m for m in metrics if m.get("trend_30d_pct", 0) > 0]
        metrics.sort(key=lambda m: m.get("trend_30d_pct", 0), reverse=True)
    elif direction == "declining":
        metrics = [m for m in metrics if m.get("trend_30d_pct", 0) < 0]
        metrics.sort(key=lambda m: m.get("trend_30d_pct", 0))
    else:
        metrics.sort(key=lambda m: abs(m.get("trend_30d_pct", 0)), reverse=True)

    products = [
        {
            "name": m["product_name"],
            "sku": m.get("sku"),
            "trend_30d_pct": m.get("trend_30d_pct", 0),
            "total_revenue": m["total_revenue"],
            "abc_class": m.get("abc_class"),
        }
        for m in metrics[:limit]
    ]

    response = {
        "data": {
            "has_data": bool(products),
            "products": products,
            "filter_direction": direction,
        },
        # Wave 13.5 — explicit temporal scope so the model never confuses
        # this snapshot with a period-filtered answer. Pre-13.5 the only
        # hint was the ``trend_30d_pct`` field name; many model traces in
        # the audit showed Sonnet quoting these as YTD/MTD figures.
        "_temporal_scope": "materialized_30d_vs_prior_30d",
        **_epistemic(len(products)),
    }

    if not is_native_30d:
        response["_period_caveat"] = (
            "Il trend è fisso sullo snapshot 'ultimi 30 giorni vs 30 giorni "
            "precedenti'. Il periodo richiesto "
            f"(period={tool_input.get('period')!r}, "
            f"start={_req_start!r}, end={_req_end!r}) "
            "NON è quello del trend mostrato. Qualifica la risposta come "
            "'negli ultimi 30 giorni' oppure usa query_business_summary / "
            "query_cashflow_summary con il periodo richiesto."
        )

    return response


async def _tool_product_recommendations(org_id: str) -> dict:
    """AI-ready product recommendations based on data."""
    metrics = await product_metrics_collection.find(
        {"organization_id": org_id},
        {"_id": 0},
    ).to_list(length=500)

    if not metrics:
        return {
            "data": {"has_data": False},
            **_epistemic(0),
        }

    # Stars: high margin + growing
    stars = [m for m in metrics if (m.get("margin_pct") or 0) > 20 and m.get("trend_30d_pct", 0) > 10]
    stars.sort(key=lambda m: m["total_revenue"], reverse=True)

    # Critical margin: margin < 5% but significant revenue
    median_revenue = sorted([m["total_revenue"] for m in metrics])[len(metrics) // 2]
    critical = [m for m in metrics if (m.get("margin_pct") or 0) < 5 and m.get("margin_pct") is not None and m["total_revenue"] > median_revenue]
    critical.sort(key=lambda m: m["total_revenue"], reverse=True)

    # Declining: trend < -20%
    declining = [m for m in metrics if m.get("trend_30d_pct", 0) < -20]
    declining.sort(key=lambda m: m.get("trend_30d_pct", 0))

    def _fmt(m, category=None):
        entry = {
            "name": m["product_name"],
            "revenue": m["total_revenue"],
            "margin_pct": m["margin_pct"],
            "trend_30d_pct": m.get("trend_30d_pct", 0),
        }
        # Actionable recommendations with specific data
        if category == "star":
            entry["action"] = (
                f"Margine {m.get('margin_pct', 0):.0f}% con crescita {m.get('trend_30d_pct', 0):+.0f}% "
                f"su {m['total_revenue']:,.0f} di fatturato — aumentare visibilita e considerare aumento prezzo"
            )
        elif category == "critical":
            entry["action"] = (
                f"Margine critico {m.get('margin_pct', 0):.1f}% su {m['total_revenue']:,.0f} di fatturato — "
                f"rinegoziare con fornitore o aumentare prezzo unitario"
            )
        elif category == "declining":
            entry["action"] = (
                f"Calo {m.get('trend_30d_pct', 0):+.0f}% negli ultimi 30 giorni — "
                f"verificare se problema di stock, stagionalita o concorrenza"
            )
        return entry

    # Commerce-derived recommendations (v13.0)
    underperforming_events = [m for m in metrics
                              if m.get("item_type") == "event_ticket"
                              and m.get("event_fill_rate_pct") is not None
                              and m["event_fill_rate_pct"] < 30]
    idle_rentals = [m for m in metrics
                    if m.get("item_type") == "rental"
                    and (m.get("rental_utilization_pct") or 0) < 10]
    high_cancel = [m for m in metrics if m.get("cancellation_rate_pct", 0) > 20]
    low_stock = [m for m in metrics if m.get("stock_quantity") is not None and m["stock_quantity"] <= 3]

    return {
        "data": {
            "has_data": True,
            "stars": [_fmt(m, "star") for m in stars[:5]],
            "critical_margin": [_fmt(m, "critical") for m in critical[:5]],
            "declining": [_fmt(m, "declining") for m in declining[:5]],
            # Commerce recommendations (v13.0)
            "underperforming_events": [{"name": m["product_name"], "fill_rate": m.get("event_fill_rate_pct"),
                                       "revenue": m["total_revenue"], "capacity": m.get("event_total_capacity"),
                                       "action": "Valutare promozione, reminder clienti, riduzione prezzo"} for m in underperforming_events[:5]],
            "idle_rentals": [{"name": m["product_name"], "utilization": m.get("rental_utilization_pct", 0),
                              "revenue": m["total_revenue"],
                              "action": "Valutare riduzione prezzo, promozione, o ritiro dal catalogo"} for m in idle_rentals[:5]],
            "high_cancellation_products": [{"name": m["product_name"], "cancel_rate": m.get("cancellation_rate_pct"),
                                            "revenue": m["total_revenue"],
                                            "action": "Indagare ragioni cancellazione, verificare esperienza d'acquisto"} for m in high_cancel[:5]],
            "low_stock_products": [{"name": m["product_name"], "stock": m.get("stock_quantity", 0),
                                    "revenue": m["total_revenue"],
                                    "action": "Riordinare o aggiornare giacenza"} for m in low_stock[:5]],
            "total_products_analyzed": len(metrics),
        },
        **_epistemic(len(metrics)),
    }


# ── Wave 7A.3: focused sub-tools ─────────────────────────────────────────────

def _clip_limit(raw: Any, default: int = 10, ceiling: int = 50) -> int:
    """Clamp a user-supplied limit into [1, ceiling]."""
    try:
        n = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        n = default
    return max(1, min(n, ceiling))


async def _tool_low_stock_products(org_id: str, tool_input: dict) -> dict:
    """Physical products with stock_quantity at or below threshold."""
    threshold = tool_input.get("threshold", 3)
    try:
        threshold = int(threshold)
    except (TypeError, ValueError):
        threshold = 3
    limit = _clip_limit(tool_input.get("limit"), default=10, ceiling=50)

    metrics = await product_metrics_collection.find(
        {
            "organization_id": org_id,
            "stock_quantity": {"$ne": None, "$lte": threshold},
        },
        {"_id": 0},
    ).sort("stock_quantity", 1).to_list(length=limit)

    products = [
        {
            "name": m["product_name"],
            "sku": m.get("sku"),
            "category": m.get("category"),
            "stock_quantity": m.get("stock_quantity", 0),
            "total_revenue": m.get("total_revenue", 0),
            "units_sold": m.get("total_units_sold", 0),
            "action": (
                "Riordinare con urgenza" if (m.get("stock_quantity") or 0) <= 1
                else "Pianificare riordino"
            ),
        }
        for m in metrics
    ]

    return {
        "data": {
            "has_data": bool(products),
            "products": products,
            "threshold_used": threshold,
            "count": len(products),
        },
        **_epistemic(len(products)),
    }


async def _tool_underperforming_events(org_id: str, tool_input: dict) -> dict:
    """Event tickets with fill rate below threshold."""
    raw_threshold = tool_input.get("max_fill_rate_pct", 30)
    try:
        max_fill = float(raw_threshold)
    except (TypeError, ValueError):
        max_fill = 30.0
    limit = _clip_limit(tool_input.get("limit"), default=10, ceiling=50)

    metrics = await product_metrics_collection.find(
        {
            "organization_id": org_id,
            "item_type": "event_ticket",
            "event_fill_rate_pct": {"$ne": None, "$lt": max_fill},
        },
        {"_id": 0},
    ).sort("event_fill_rate_pct", 1).to_list(length=limit)

    events = [
        {
            "name": m["product_name"],
            "sku": m.get("sku"),
            "fill_rate_pct": m.get("event_fill_rate_pct"),
            "total_capacity": m.get("event_total_capacity"),
            "tickets_sold": m.get("event_tickets_sold"),
            "revenue": m.get("total_revenue", 0),
            "action": "Valutare promozione, reminder clienti o riduzione prezzo",
        }
        for m in metrics
    ]

    return {
        "data": {
            "has_data": bool(events),
            "events": events,
            "threshold_used_pct": max_fill,
            "count": len(events),
        },
        **_epistemic(len(events)),
    }


async def _tool_idle_rentals(org_id: str, tool_input: dict) -> dict:
    """Rental assets with utilization below threshold."""
    raw_threshold = tool_input.get("max_utilization_pct", 10)
    try:
        max_util = float(raw_threshold)
    except (TypeError, ValueError):
        max_util = 10.0
    limit = _clip_limit(tool_input.get("limit"), default=10, ceiling=50)

    # Use $or: matches rentals with utilization < threshold OR utilization missing/0
    metrics = await product_metrics_collection.find(
        {
            "organization_id": org_id,
            "item_type": "rental",
            "$or": [
                {"rental_utilization_pct": {"$lt": max_util}},
                {"rental_utilization_pct": None},
            ],
        },
        {"_id": 0},
    ).sort("rental_utilization_pct", 1).to_list(length=limit)

    rentals = [
        {
            "name": m["product_name"],
            "sku": m.get("sku"),
            "utilization_pct": m.get("rental_utilization_pct") or 0,
            "revenue": m.get("total_revenue", 0),
            "units_sold": m.get("total_units_sold", 0),
            "action": "Valutare riduzione prezzo, promozione, o ritiro dal catalogo",
        }
        for m in metrics
    ]

    return {
        "data": {
            "has_data": bool(rentals),
            "rentals": rentals,
            "threshold_used_pct": max_util,
            "count": len(rentals),
        },
        **_epistemic(len(rentals)),
    }


async def _tool_high_cancellation_products(org_id: str, tool_input: dict) -> dict:
    """Products with cancellation rate at or above threshold."""
    raw_threshold = tool_input.get("min_cancel_rate_pct", 20)
    try:
        min_cancel = float(raw_threshold)
    except (TypeError, ValueError):
        min_cancel = 20.0
    limit = _clip_limit(tool_input.get("limit"), default=10, ceiling=50)

    metrics = await product_metrics_collection.find(
        {
            "organization_id": org_id,
            "cancellation_rate_pct": {"$gte": min_cancel},
        },
        {"_id": 0},
    ).sort("cancellation_rate_pct", -1).to_list(length=limit)

    products = [
        {
            "name": m["product_name"],
            "sku": m.get("sku"),
            "item_type": m.get("item_type", "physical"),
            "cancellation_rate_pct": m.get("cancellation_rate_pct"),
            "revenue": m.get("total_revenue", 0),
            "order_revenue": m.get("order_revenue", 0),
            "action": "Indagare ragioni cancellazione, verificare esperienza d'acquisto",
        }
        for m in metrics
    ]

    return {
        "data": {
            "has_data": bool(products),
            "products": products,
            "threshold_used_pct": min_cancel,
            "count": len(products),
        },
        **_epistemic(len(products)),
    }
