"""AI tool definitions for the customer-intelligence brain.

Migrated from ``modules.customers_light.ai_tools`` during the
single-brain consolidation. **Tool NAMES + parameter SCHEMAS +
response SHAPES are bit-for-bit identical** because the LLM-side
function-calling contract is pinned on those — any drift breaks the
chat assistant's ability to answer customer questions.

Tool *description text* is allowed to evolve (Wave 14.8 rewrote
query_customer_summary / query_top_customers / query_customer_segments
to make temporal scope explicit — `period_filtered` vs `all_time` —
because the AI was attributing lifetime numbers to the user's period
filter, causing prod hallucinations on 2026-05-16).

The 7 tools (names — these MUST stay stable):
  • query_customer_summary       period-aware top customers + concentration
  • query_top_customers          all-time ranking
  • query_customer_segments      distribution per segment
  • query_customer_profile       single-customer drill-down + suggested actions
  • query_churn_risk             ranked at-risk list
  • query_customer_product_affinity  preferred products per top customer
  • query_customer_concentration  top-N share of revenue

Provider-agnostic format. The platform's ``ai_tool_registry``
converts ``parameters`` → JSON-Schema ``input_schema`` for Anthropic
when collecting active-module tool sets.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "query_customer_summary",
        "description": (
            "Riepilogo clienti per il periodo (allineato temporalmente con il "
            "cashflow). "
            "SCOPE: period_filtered (per la classifica LIFETIME usa "
            "query_top_customers). "
            "Restituisce: top clienti per fatturato DEL PERIODO, concentrazione, "
            "qualita dati (customer_id_coverage_pct), metadati temporali. "
            "Usa per cross-modulo cashflow+clienti: 'chi ha generato fatturato "
            "questo mese?', 'la concentrazione sta peggiorando?', 'i ricavi sono "
            "trainati da pochi clienti?'. "
            "Param OBBLIGATORI: start_date+end_date (YYYY-MM-DD). top_n default 10."
        ),
        "parameters": {
            "start_date": {
                "type": "string",
                "description": "Data inizio periodo in formato YYYY-MM-DD",
            },
            "end_date": {
                "type": "string",
                "description": "Data fine periodo in formato YYYY-MM-DD",
            },
            "top_n": {
                "type": "integer",
                "description": "Numero di top clienti (default 10)",
            },
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_top_customers",
        "description": (
            "Top clienti per fatturato LIFETIME (NON filtrato per periodo). "
            "SCOPE: all_time — i numeri sono aggregati storici totali, NON "
            "riconducibili al periodo del filtro frontend. Qualificare le "
            "risposte come 'lifetime' / 'totale storico'. "
            "Restituisce: nome cliente, fatturato totale lifetime, num transazioni, "
            "ultimo acquisto, segmento. "
            "Usa per: 'chi sono i miei migliori clienti?', 'top 10 clienti', "
            "'clienti per importanza'. "
            "Per i top clienti DEL PERIODO usa invece query_customer_summary. "
            "Param: limit (default 10)."
        ),
        "parameters": {
            "limit": {
                "type": "integer",
                "description": "Numero massimo di clienti da restituire (default 10)",
            },
        },
        "required": [],
    },
    {
        "name": "query_customer_segments",
        "description": (
            "Distribuzione clienti per segmento (top, attivi, occasionali, "
            "inattivi, nuovi). "
            "SCOPE: all_time — segmentazione lifetime basata sulla storia totale, "
            "NON sul periodo del filtro frontend. Qualificare come 'distribuzione "
            "storica' / 'lifetime'. "
            "Restituisce: per ogni segmento conteggio, fatturato totale, "
            "percentuale sul totale. "
            "Usa per: 'come sono fatti i miei clienti?', 'quanti clienti attivi "
            "ho?', 'distribuzione clienti', 'che mix ho?'. "
            "Per cohort di periodo specifico usa invece query_customer_summary."
        ),
        "parameters": {},
        "required": [],
    },
    {
        "name": "query_customer_profile",
        "description": (
            "Profilo dettagliato di un singolo cliente: LTV, rischio churn, "
            "prodotti preferiti, affidabilita pagamenti, storico acquisti recenti. "
            "Usare quando l'utente chiede informazioni su un cliente specifico."
        ),
        "parameters": {
            "customer_name": {
                "type": "string",
                "description": "Nome del cliente da cercare (ricerca parziale)",
            },
        },
        "required": ["customer_name"],
    },
    {
        "name": "query_churn_risk",
        "description": (
            "Restituisce i clienti a piu alto rischio di abbandono, ordinati per "
            "score di churn (0-100). Usare per domande tipo 'quali clienti stiamo perdendo', "
            "'chi rischia di non tornare', 'clienti a rischio'."
        ),
        "parameters": {
            "limit": {
                "type": "integer",
                "description": "Numero massimo di clienti (default 10)",
            },
        },
        "required": [],
    },
    {
        "name": "query_customer_product_affinity",
        "description": (
            "Restituisce i prodotti preferiti per ogni cliente (top 3 per fatturato). "
            "Usare per domande tipo 'cosa compra il cliente X', 'prodotti preferiti dei top clienti'."
        ),
        "parameters": {
            "limit": {
                "type": "integer",
                "description": "Numero di clienti da includere (default 10)",
            },
        },
        "required": [],
    },
    {
        "name": "query_customer_concentration",
        "description": (
            "Analizza la concentrazione del fatturato — quanto l'azienda "
            "dipende dai clienti principali. Restituisce la quota di fatturato "
            "dei top N clienti e il dettaglio per cliente."
        ),
        "parameters": {
            "top_n": {
                "type": "integer",
                "description": "Numero di top clienti da analizzare (default 5)",
            },
        },
        "required": [],
    },

    # ── Wave 7D: acquisition trend ─────────────────────────────────────────
    {
        "name": "query_customer_acquisition_trend",
        "description": (
            "Trend di acquisizione nuovi clienti: per ciascuno degli ultimi N mesi (default 6, "
            "max 24) restituisce il numero di customer_accounts creati. Aggiunge analisi "
            "direzionale (growing/stable/declining) confrontando le 2 meta del periodo. "
            "Usa per 'sto acquisendo nuovi clienti?', 'il marketing funziona?', 'trend acquisition'."
        ),
        "parameters": {
            "months_back": {
                "type": "integer",
                "description": "Mesi da analizzare a ritroso (default 6, max 24).",
            },
        },
        "required": [],
    },
]


async def execute_tool(org_id: str, tool_name: str, tool_input: dict) -> dict:
    """Dispatch + execute one of the 7 customer AI tools.

    Reads from materialised ``customer_metrics`` via the
    ``customer_insights`` repository (post-migration single brain).
    Response shapes preserved bit-for-bit so the LLM's downstream
    formatting prompts continue to apply.
    """
    from modules.customer_insights import repository

    logger.info("customer_insights ai_tools: executing %s", tool_name)

    try:
        if tool_name == "query_customer_summary":
            from repositories.analytics_repository import (
                aggregate_customers_by_revenue_period,
                aggregate_customer_concentration_period,
                count_sales_with_customer_id,
            )
            start = tool_input["start_date"]
            end = tool_input["end_date"]
            top_n = tool_input.get("top_n", 10)

            top_customers = await aggregate_customers_by_revenue_period(org_id, start, end, limit=top_n)
            concentration = await aggregate_customer_concentration_period(org_id, start, end, top_n=5)
            data_quality = await count_sales_with_customer_id(org_id, start, end)

            from database import orders_collection
            from datetime import datetime as _dt, timedelta as _td
            order_agg = {"total_orders": 0, "confirmed": 0, "cancelled": 0, "total_value": 0}
            try:
                s_dt = _dt.strptime(start, "%Y-%m-%d")
                e_dt = _dt.strptime(end, "%Y-%m-%d") + _td(days=1)
                pipeline = [
                    {"$match": {"organization_id": org_id, "created_at": {"$gte": s_dt, "$lt": e_dt}}},
                    {"$group": {"_id": "$status", "count": {"$sum": 1}, "value": {"$sum": {"$ifNull": ["$total", 0]}}}},
                ]
                async for doc in orders_collection.aggregate(pipeline):
                    order_agg["total_orders"] += doc["count"]
                    order_agg["total_value"] += doc["value"]
                    if doc["_id"] in ("confirmed", "completed"):
                        order_agg["confirmed"] += doc["count"]
                    elif doc["_id"] == "cancelled":
                        order_agg["cancelled"] += doc["count"]
                order_agg["total_value"] = round(order_agg["total_value"], 2)
                order_agg["cancellation_rate_pct"] = round(
                    order_agg["cancelled"] / order_agg["total_orders"] * 100, 1
                ) if order_agg["total_orders"] > 0 else 0
            except Exception:
                order_agg["cancellation_rate_pct"] = 0

            has_data = concentration.get("has_customer_data", False)
            coverage = data_quality.get("coverage_pct", 0)

            return {
                "period": {"start_date": start, "end_date": end},
                "temporal_scope": "period",
                "temporal_alignment_safe": True,
                "data_quality": {
                    "has_customer_data": has_data,
                    "total_sales_records": data_quality.get("total_records", 0),
                    "records_with_customer_id": data_quality.get("with_customer_id", 0),
                    "customer_id_coverage_pct": coverage,
                    "warning": (
                        "Only {:.0f}% of sales records have a customer_id. "
                        "Customer analysis covers a subset of total revenue.".format(coverage)
                    ) if 0 < coverage < 80 else (
                        "No sales records have a customer_id linked. "
                        "Customer-level analysis is not available for this period."
                    ) if coverage == 0 else None,
                },
                "top_customers": top_customers,
                "concentration": {
                    "total_customers": concentration.get("total_customers", 0),
                    "total_revenue": concentration.get("total_revenue", 0),
                    "top_5_share_pct": concentration.get("top_n_share_pct", 0),
                    "top_customers": concentration.get("top_customers", []),
                },
                "order_activity": {
                    "total_orders": order_agg["total_orders"],
                    "orders_confirmed": order_agg["confirmed"],
                    "orders_cancelled": order_agg["cancelled"],
                    "order_total_value": order_agg["total_value"],
                    "cancellation_rate_pct": order_agg["cancellation_rate_pct"],
                },
                "epistemic": {
                    "epistemic_class": "derived" if has_data else "insufficient_data",
                    "reliability": "high" if coverage >= 80 else "medium" if coverage >= 50 else "low",
                    "temporal_scope": "period",
                    "temporal_alignment_safe": True,
                    "ai_usability": "strong" if coverage >= 80 else "partial" if coverage >= 50 else "weak",
                    "caveat": (
                        "Period-filtered from sales_records. Temporally aligned with cashflow. "
                        + (f"Customer ID coverage: {coverage:.0f}%." if coverage < 100 else "")
                    ),
                },
            }

        elif tool_name == "query_top_customers":
            # Wave 14.1 — envelope migration. Import at branch level
            # (rather than module top) to avoid touching unrelated
            # tools in this dispatcher while migration progresses.
            from core.tool_envelope import attach_envelope_metadata

            limit = tool_input.get("limit", 10)
            metrics = await repository.find_metrics_by_org(org_id, limit=limit)

            if not metrics:
                return attach_envelope_metadata({
                    "has_data": False,
                    "message": "Nessun dato cliente disponibile. Verifica che le vendite abbiano l'ID cliente collegato.",
                    "_caveat": (
                        "No customer metrics exist for this org. The chat AI "
                        "should suggest enabling customer_id linking on "
                        "sales records, not synthesise numbers."
                    ),
                }, tool="query_top_customers", temporal_scope="all_time")

            return attach_envelope_metadata({
                "has_data": True,
                "total_customers": len(metrics),
                "top_customers": [
                    {
                        "name": m["customer_name"],
                        "total_revenue": round(m["total_revenue"], 2),
                        "transaction_count": m["transaction_count"],
                        "last_purchase_date": m.get("last_purchase_date"),
                        "segment": m["segment"],
                        "revenue_share_pct": m["revenue_share_pct"],
                    }
                    for m in metrics[:limit]
                ],
                "epistemic": {
                    "epistemic_class": "derived",
                    "reliability": "medium",
                    "temporal_scope": "snapshot",
                    "temporal_alignment_safe": False,
                    "ai_usability": "partial",
                    "caveat": "Based on materialized all-time customer_metrics. NOT period-filtered. Use query_customer_summary for period-aligned analysis.",
                },
            }, tool="query_top_customers", temporal_scope="all_time")

        elif tool_name == "query_customer_segments":
            all_metrics = await repository.find_metrics_by_org(org_id, limit=5000)

            if not all_metrics:
                return {"message": "Nessun dato cliente disponibile."}

            total_revenue = sum(m["total_revenue"] for m in all_metrics)
            segments = {}
            for m in all_metrics:
                seg = m["segment"]
                if seg not in segments:
                    segments[seg] = {"segment": seg, "count": 0, "total_revenue": 0.0}
                segments[seg]["count"] += 1
                segments[seg]["total_revenue"] = round(
                    segments[seg]["total_revenue"] + m["total_revenue"], 2
                )

            for s in segments.values():
                s["avg_revenue"] = round(s["total_revenue"] / s["count"], 2) if s["count"] > 0 else 0
                s["pct_of_total"] = round(
                    (s["total_revenue"] / total_revenue * 100) if total_revenue > 0 else 0, 1
                )

            return {
                "total_customers": len(all_metrics),
                "total_revenue": round(total_revenue, 2),
                "segments": list(segments.values()),
                "epistemic": {
                    "epistemic_class": "derived",
                    "reliability": "medium",
                    "temporal_scope": "snapshot",
                    "temporal_alignment_safe": False,
                    "ai_usability": "partial",
                    "caveat": "Segments from all-time customer_metrics snapshot. NOT period-filtered.",
                },
            }

        elif tool_name == "query_customer_profile":
            name_query = tool_input.get("customer_name", "")
            import re as _re
            from database import customer_metrics_collection
            safe_query = _re.escape(name_query)
            doc = await customer_metrics_collection.find_one(
                {
                    "organization_id": org_id,
                    "customer_name": {"$regex": safe_query, "$options": "i"},
                },
                {"_id": 0},
            )
            if not doc:
                return {"message": f"Nessun cliente trovato con nome '{name_query}'."}

            _actions = []
            _churn = doc.get("churn_risk_score", 0)
            _days = doc.get("days_since_last_purchase", 0)
            _seg = doc.get("segment", "")
            _cancel_rate = doc.get("cancellation_rate_pct", 0)
            _ltv = doc.get("lifetime_value") or doc.get("total_revenue", 0)
            _freq = doc.get("purchase_frequency_monthly", 0)

            if _churn >= 60 and _days > 60:
                _actions.append({
                    "action": "reattivazione",
                    "priority": "alta",
                    "detail": f"Contattare per reattivazione — LTV {_ltv:,.0f}, inattivo da {_days} giorni",
                })
            if _cancel_rate > 20 and doc.get("orders_cancelled", 0) > 2:
                _actions.append({
                    "action": "verifica_qualita",
                    "priority": "alta" if _cancel_rate > 40 else "media",
                    "detail": f"Verificare qualita servizio — {doc.get('orders_cancelled', 0)} cancellazioni su {doc.get('order_count', 0)} ordini ({_cancel_rate:.0f}%)",
                })
            if _seg == "top" and _days > 30:
                _actions.append({
                    "action": "contatto_prioritario",
                    "priority": "alta",
                    "detail": f"Contatto prioritario — cliente top inattivo da {_days} giorni (LTV {_ltv:,.0f})",
                })
            if _seg in ("active", "occasional") and _freq > 0:
                avg_interval = 30 / _freq if _freq > 0 else 999
                if _days > avg_interval * 2 and _days > 30:
                    _actions.append({
                        "action": "incentivo_fedelta",
                        "priority": "media",
                        "detail": f"Proporre incentivo fedelta — frequenza in calo (media {avg_interval:.0f}gg, ultimo acquisto {_days}gg fa)",
                    })

            return {
                "customer": {
                    "name": doc["customer_name"],
                    "total_revenue": doc["total_revenue"],
                    "transaction_count": doc["transaction_count"],
                    "avg_transaction_value": doc.get("avg_transaction_value", 0),
                    "segment": doc["segment"],
                    "lifetime_value": doc.get("lifetime_value", 0),
                    "churn_risk_score": doc.get("churn_risk_score", 0),
                    "preferred_products": doc.get("preferred_products", []),
                    "payment_reliability_pct": doc.get("payment_reliability_pct"),
                    "first_purchase_date": doc.get("first_purchase_date"),
                    "last_purchase_date": doc.get("last_purchase_date"),
                    "days_since_last_purchase": doc.get("days_since_last_purchase", 0),
                    "purchase_frequency_monthly": doc.get("purchase_frequency_monthly", 0),
                    "order_count": doc.get("order_count", 0),
                    "order_total_value": doc.get("order_total_value", 0),
                    "avg_order_value": doc.get("avg_order_value", 0),
                    "last_order_date": doc.get("last_order_date"),
                    "orders_confirmed": doc.get("orders_confirmed", 0),
                    "orders_cancelled": doc.get("orders_cancelled", 0),
                    "cancellation_rate_pct": doc.get("cancellation_rate_pct", 0),
                    "booking_count": doc.get("booking_count", 0),
                    "event_attendance": doc.get("event_attendance", 0),
                    "fulfillment_success_rate": doc.get("fulfillment_success_rate"),
                },
                "suggested_actions": _actions,
                "epistemic": {
                    "epistemic_class": "derived",
                    "reliability": "high",
                    "temporal_scope": "snapshot",
                    "ai_usability": "cite_directly",
                },
                "analytical_hints": {
                    "interpretation": "order_count e transaction_count possono differire: transaction_count conta SalesRecords (confermati), order_count conta tutti gli ordini. cancellation_rate_pct > 30% = cliente problematico.",
                    "cross_module": ["Confrontare order_total_value con total_revenue per verificare coerenza"],
                },
            }

        elif tool_name == "query_churn_risk":
            limit = min(tool_input.get("limit", 10), 50)
            from database import customer_metrics_collection
            cursor = customer_metrics_collection.find(
                {"organization_id": org_id, "churn_risk_score": {"$gt": 20}},
                {"_id": 0},
            ).sort("churn_risk_score", -1).limit(limit)
            at_risk = await cursor.to_list(length=limit)

            if not at_risk:
                return {"message": "Nessun cliente con rischio churn significativo."}

            return {
                "customers_at_risk": [
                    {
                        "name": m["customer_name"],
                        "churn_risk_score": m.get("churn_risk_score", 0),
                        "days_since_last_purchase": m.get("days_since_last_purchase", 0),
                        "segment": m["segment"],
                        "total_revenue": m["total_revenue"],
                        "lifetime_value": m.get("lifetime_value", 0),
                        "orders_cancelled": m.get("orders_cancelled", 0),
                        "cancellation_rate_pct": m.get("cancellation_rate_pct", 0),
                        "order_count": m.get("order_count", 0),
                    }
                    for m in at_risk
                ],
                "epistemic": {
                    "epistemic_class": "derived",
                    "reliability": "medium",
                    "temporal_scope": "snapshot",
                    "ai_usability": "qualify_with_caveat",
                    "caveat": "Churn risk e' stimato da recency, frequenza e tasso di cancellazione ordini. cancellation_rate > 30% aggiunge +20 punti rischio. Non e' un modello predittivo ma un segnale operativo.",
                },
            }

        elif tool_name == "query_customer_product_affinity":
            limit = min(tool_input.get("limit", 10), 50)
            from database import customer_metrics_collection
            cursor = customer_metrics_collection.find(
                {"organization_id": org_id, "preferred_products.0": {"$exists": True}},
                {"_id": 0, "customer_name": 1, "preferred_products": 1, "total_revenue": 1},
            ).sort("total_revenue", -1).limit(limit)
            customers = await cursor.to_list(length=limit)

            if not customers:
                return {"message": "Nessun dato affinita prodotto-cliente disponibile."}

            return {
                "customer_product_affinity": [
                    {
                        "name": c["customer_name"],
                        "preferred_products": c.get("preferred_products", []),
                    }
                    for c in customers
                ],
                "epistemic": {
                    "epistemic_class": "derived",
                    "reliability": "medium",
                    "temporal_scope": "snapshot",
                    "ai_usability": "cite_directly",
                },
            }

        elif tool_name == "query_customer_concentration":
            top_n = tool_input.get("top_n", 5)
            all_metrics = await repository.find_metrics_by_org(org_id, limit=5000)

            if not all_metrics:
                return {"message": "Nessun dato cliente disponibile."}

            total_revenue = sum(m["total_revenue"] for m in all_metrics)
            top = all_metrics[:top_n]
            top_revenue = sum(m["total_revenue"] for m in top)
            top_share = round((top_revenue / total_revenue * 100) if total_revenue > 0 else 0, 1)

            return {
                "total_customers": len(all_metrics),
                "top_n": top_n,
                "top_n_share_pct": top_share,
                "remaining_share_pct": round(100 - top_share, 1),
                "top_customers": [
                    {
                        "name": m["customer_name"],
                        "revenue": round(m["total_revenue"], 2),
                        "share_pct": m["revenue_share_pct"],
                    }
                    for m in top
                ],
                "epistemic": {
                    "epistemic_class": "derived",
                    "reliability": "medium",
                    "temporal_scope": "snapshot",
                    "temporal_alignment_safe": False,
                    "ai_usability": "partial",
                    "caveat": "All-time snapshot. NOT period-filtered. Use query_customer_summary for period-aligned concentration.",
                },
            }

        # ── Wave 7D: acquisition trend ──────────────────────────────────────

        elif tool_name == "query_customer_acquisition_trend":
            from database import customer_accounts_collection
            from datetime import datetime as dt, timedelta, timezone

            raw = tool_input.get("months_back", 6)
            try:
                months_back = max(1, min(int(raw), 24))
            except (TypeError, ValueError):
                months_back = 6

            now = dt.now(timezone.utc).replace(tzinfo=None)
            # Compute start = first day of (current month - months_back)
            year = now.year
            month = now.month - months_back + 1
            while month <= 0:
                month += 12
                year -= 1
            start_dt = dt(year, month, 1)

            pipeline = [
                {"$match": {
                    "organization_id": org_id,
                    "created_at": {"$gte": start_dt},
                }},
                {"$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"},
                    },
                    "count": {"$sum": 1},
                }},
                {"$sort": {"_id.year": 1, "_id.month": 1}},
            ]

            buckets: dict = {}
            async for doc in customer_accounts_collection.aggregate(pipeline):
                y = doc["_id"]["year"]
                m = doc["_id"]["month"]
                buckets[(y, m)] = doc["count"]

            # Build dense month list (fill zeros)
            months: list = []
            y = start_dt.year
            m = start_dt.month
            for _ in range(months_back):
                months.append({
                    "year": y, "month": m,
                    "label": f"{y}-{m:02d}",
                    "new_customers": buckets.get((y, m), 0),
                })
                m += 1
                if m > 12:
                    m = 1
                    y += 1

            total_new = sum(b["new_customers"] for b in months)
            avg_per_month = round(total_new / months_back, 1) if months_back > 0 else 0

            # Direction = compare first half vs second half
            half = months_back // 2
            if half > 0:
                first_half = sum(b["new_customers"] for b in months[:half])
                second_half = sum(b["new_customers"] for b in months[-half:])
                if second_half > first_half * 1.1:
                    direction = "growing"
                elif second_half < first_half * 0.9:
                    direction = "declining"
                else:
                    direction = "stable"
                delta_pct = round((second_half - first_half) / first_half * 100, 1) if first_half > 0 else None
            else:
                direction = "n/a"
                delta_pct = None

            peak_month = max(months, key=lambda b: b["new_customers"], default=None)
            peak_label = peak_month["label"] if peak_month and peak_month["new_customers"] > 0 else None

            return {
                "months_analyzed": months_back,
                "has_data": total_new > 0,
                "months": months,
                "totals": {
                    "new_customers_in_window": total_new,
                    "avg_per_month": avg_per_month,
                    "peak_month": peak_label,
                    "peak_count": peak_month["new_customers"] if peak_month else 0,
                },
                "trend": {
                    "direction": direction,
                    "half_over_half_delta_pct": delta_pct,
                },
                "epistemic": {
                    "epistemic_class": "factual",
                    "reliability": "high" if total_new >= 10 else "medium" if total_new > 0 else "low",
                    "temporal_scope": "period",
                    "temporal_alignment_safe": True,
                    "ai_usability": "strong" if total_new >= 10 else "qualify_with_caveat",
                    "caveat": "Conteggio basato su customer_accounts.created_at. Acquisizioni 'invisibili' (guest order senza account) NON sono contate." if total_new > 0 else "Pochi account creati nel periodo — il trend potrebbe non essere significativo.",
                },
            }

        else:
            return {"error": f"Tool sconosciuto: {tool_name}"}

    except Exception as e:
        logger.error("customer_insights ai_tools: %s failed: %s", tool_name, e, exc_info=True)
        return {"error": f"Errore nell'esecuzione del tool {tool_name}: {str(e)}"}
