"""
Unified Cross-Module Business Summary — AI Reasoning Layer.

Composes cashflow, customer, and commerce signal summaries into a single
governed structure for horizontal AI reasoning.

This is a COMPOSITION layer, not a computation layer.  All business logic
stays in the module-level summaries/repositories.  This service:
1. Calls each module's canonical AI summary
2. Adds cross-module compatibility metadata
3. Adds a reasoning contract that governs what AI may claim
4. Adds structured connection points between modules

Public interface:
    build_unified_summary(org_id, period, start_date, end_date, locale) -> dict
        Returns a governed cross-module view.  Never raises.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Reasoning contract ───────────────────────────────────────────────────────
# This is returned in the summary so the AI knows what it can and cannot claim.

_REASONING_CONTRACT = {
    "evidence_hierarchy": [
        {
            "rank": 1,
            "source": "cashflow.pnl",
            "label": "Cashflow P&L (period)",
            "temporal_scope": "period",
            "epistemic_class": "observed/derived",
            "use_for": "Primary financial truth. Revenue, costs, net result, margins, ratios.",
            "claim_type": "factual",
        },
        {
            "rank": 2,
            "source": "customers.period",
            "label": "Customer analysis (period)",
            "temporal_scope": "period",
            "epistemic_class": "derived",
            "use_for": "Customer-level revenue attribution for the same period. Concentration, top customers.",
            "claim_type": "factual_if_data_quality_sufficient",
        },
        {
            "rank": 3,
            "source": "cashflow.scadenzario",
            "label": "Scadenzario / payment cycle",
            "temporal_scope": "mixed",
            "epistemic_class": "insufficient_data",
            "use_for": "Receivables, payables, DSO/DPO only when payment_status data exists.",
            "claim_type": "conditional",
        },
        {
            "rank": 4,
            "source": "cashflow.health_score",
            "label": "Health score composite",
            "temporal_scope": "period",
            "epistemic_class": "estimated",
            "use_for": "Directional summary. Decompose into dimensions, do not cite as precise.",
            "claim_type": "directional",
        },
        {
            "rank": 5,
            "source": "commerce_operations",
            "label": "Commerce operations (current state)",
            "temporal_scope": "current_state",
            "epistemic_class": "factual",
            "use_for": "Ordini attivi, evasioni pendenti, pagamenti in sospeso. Stato operativo reale.",
            "claim_type": "factual",
        },
        {
            "rank": 6,
            "source": "forecast/estimation",
            "label": "Revenue forecast and anomaly detection",
            "temporal_scope": "forecast",
            "epistemic_class": "estimated",
            "use_for": "Directional projections and statistical anomalies. NEVER cite as fact. Always qualify with 'sulla base del trend attuale, si stima...' or 'il modello suggerisce...'",
            "claim_type": "speculative",
        },
    ],
    "safe_comparisons": [
        "cashflow.pnl.total_sales vs customers.period.total_revenue (same collection, same period)",
        "cashflow.pnl.sales_trend_pct vs customers.period.concentration change (if both period-based)",
        "cashflow.status.level vs cashflow.health_score.score (both derived from same period data)",
        "commerce_operations.order_pipeline vs cashflow.pnl.total_sales (orders drive sales)",
        "commerce_operations.payment_at_risk vs cashflow.scadenzario.open_receivables (both current state)",
    ],
    "unsafe_comparisons": [
        "cashflow.pnl.net_after_fixed vs any snapshot-based metric (temporal mismatch)",
        "commerce_operations.order_pipeline (current) vs cashflow.pnl trends (period) — temporal mismatch",
    ],
    "claim_rules": {
        "factual": "AI may state as fact. Example: 'Your revenue this period was €45,200.'",
        "factual_if_data_quality_sufficient": "AI may state as fact only if data_quality coverage >= 50%. Otherwise qualify.",
        "conditional": "AI must check data_quality flags. If no data, say so explicitly.",
        "directional": "AI may use for general direction ('health is declining') but must not cite as precise.",
        "contextual_only": "AI may mention for context but must NOT compare with period metrics or claim causation.",
        "speculative": "AI must explicitly label as hypothesis. 'This might be because...'",
    },
}


async def build_unified_summary(
    org_id: str,
    period: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    locale: str = "it",
) -> dict:
    """Build the unified cross-module business summary.

    Calls each module's canonical summary and composes them with
    cross-module metadata and a reasoning contract.

    Never raises — returns a minimal response on error.
    """
    import asyncio

    try:
        # ── Resolve period dates for customer alignment ──────────────────
        from services.ai_analytics_service import _get_date_range
        resolved_start, resolved_end = _get_date_range(period, start_date, end_date)

        # ── Wave 1.10 (2026-05) — resolve org currency once.
        # Pre-Wave-1.10 this summary didn't expose the merchant's
        # currency at all. A CHF-configured org would receive monetary
        # numbers without any currency signal, and the AI defaulted to
        # citing EUR from the system-prompt fallback. The smoke harness
        # caught this (W1.A CHF -> EUR) before launch. We resolve here
        # once and inject the resolved currency into every monetary
        # block so the AI always has explicit context.
        from repositories import organization_repository
        from services.currency_service import get_currency_for_org
        _org_doc = await organization_repository.find_by_id(org_id)
        org_currency = get_currency_for_org(_org_doc or {})

        # ── Fetch module summaries in parallel ────────────────────────────
        from modules.cashflow_monitor.cashflow_summary import build_ai_summary as cashflow_summary
        from repositories.analytics_repository import (
            aggregate_customers_by_revenue_period,
            aggregate_customer_concentration_period,
            count_sales_with_customer_id,
        )

        (
            cashflow,
            top_customers,
            concentration,
            customer_data_quality,
        ) = await asyncio.gather(
            cashflow_summary(org_id, period, start_date, end_date, locale),
            aggregate_customers_by_revenue_period(org_id, resolved_start, resolved_end, limit=10),
            aggregate_customer_concentration_period(org_id, resolved_start, resolved_end, top_n=5),
            count_sales_with_customer_id(org_id, resolved_start, resolved_end),
        )

        # ── Commerce operations (current state — non-blocking) ────────────
        commerce_ops = {"has_data": False}
        try:
            from database import orders_collection
            # Order pipeline counts
            order_pipeline = [
                {"$match": {"organization_id": org_id, "status": {"$ne": "cancelled"}}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}, "amount": {"$sum": {"$ifNull": ["$total", 0]}}}},
            ]
            order_counts = {}
            async for doc in orders_collection.aggregate(order_pipeline):
                order_counts[doc["_id"]] = {"count": doc["count"], "amount": round(doc["amount"], 2)}

            # Fulfillment pending count
            ff_pending = await orders_collection.count_documents({
                "organization_id": org_id, "status": {"$in": ["confirmed", "completed"]},
                "fulfillment.status": "pending",
            })

            # Payment at risk
            payment_at_risk_cursor = orders_collection.aggregate([
                {"$match": {"organization_id": org_id, "status": {"$ne": "cancelled"},
                             "payment_status": {"$ne": "paid"}, "payment_intent": {"$in": ["required", "collected"]}}},
                {"$group": {"_id": None, "count": {"$sum": 1}, "amount": {"$sum": {"$ifNull": ["$total", 0]}}}},
            ])
            payment_at_risk = {"count": 0, "amount": 0}
            async for doc in payment_at_risk_cursor:
                payment_at_risk = {"count": doc["count"], "amount": round(doc["amount"], 2)}

            total_active = sum(v["count"] for v in order_counts.values())
            if total_active > 0:
                commerce_ops = {
                    "has_data": True,
                    "temporal_scope": "current_state",
                    "order_pipeline": order_counts,
                    "total_active_orders": total_active,
                    "fulfillment_pending": ff_pending,
                    "payment_at_risk": payment_at_risk,
                }
        except Exception:
            pass

        # ── Cross-module alignment check ──────────────────────────────────
        cf_revenue = (cashflow.get("pnl", {}).get("total_sales") or 0) if cashflow.get("has_data") else 0
        cust_revenue = concentration.get("total_revenue", 0)
        cust_coverage = customer_data_quality.get("coverage_pct", 0)
        has_customer_data = concentration.get("has_customer_data", False)

        # Revenue alignment: how much of cashflow revenue is explained by customer data
        revenue_alignment_pct = round(
            (cust_revenue / cf_revenue * 100) if cf_revenue > 0 and cust_revenue > 0 else 0, 1
        )

        cross_module_meta = {
            "cashflow_has_data": cashflow.get("has_data", False),
            "customers_has_data": has_customer_data,
            "commerce_has_data": commerce_ops.get("has_data", False),
            "customer_id_coverage_pct": cust_coverage,
            "revenue_alignment_pct": revenue_alignment_pct,
            "revenue_alignment_note": (
                f"Customer-attributed revenue covers {revenue_alignment_pct}% of total cashflow revenue for this period."
                if revenue_alignment_pct > 0 else
                "No customer-attributed revenue data. Customer analysis not available."
            ),
            "temporal_alignment": {
                "cashflow": "period",
                "customers": "period" if has_customer_data else "none",
                "commerce_operations": "current_state",
            },
        }

        # ── Assemble unified summary ──────────────────────────────────────
        return {
            "has_data": cashflow.get("has_data", False),
            "period": cashflow.get("period", {"label": period}),

            # Wave 1.10: explicit currency so the AI never has to guess.
            # Stored at root level so it's the FIRST thing the model
            # sees when scanning the tool result. Display layer can
            # reuse this without re-querying the org doc.
            "currency": org_currency,

            # Module summaries
            "cashflow": cashflow,
            "customers": {
                "has_data": has_customer_data,
                "period": {"start_date": resolved_start, "end_date": resolved_end},
                "temporal_scope": "period",
                "data_quality": {
                    "customer_id_coverage_pct": cust_coverage,
                    "total_records": customer_data_quality.get("total_records", 0),
                    "with_customer_id": customer_data_quality.get("with_customer_id", 0),
                },
                "top_customers": top_customers[:5],
                "concentration": {
                    "total_customers": concentration.get("total_customers", 0),
                    "top_5_share_pct": concentration.get("top_n_share_pct", 0),
                    "top_customers": concentration.get("top_customers", []),
                },
            },
            "commerce_operations": {
                **commerce_ops,
                "epistemic_note": "Dati operativi in tempo reale (ordini, evasioni, pagamenti). Riflettono lo stato attuale, non uno storico.",
            },

            # Cross-module governance
            "cross_module": cross_module_meta,
            "reasoning_contract": _REASONING_CONTRACT,
        }

    except Exception as exc:
        logger.error("business_summary: build_unified_summary failed: %s", exc, exc_info=True)
        return {
            "has_data": False,
            "error": "Failed to build unified business summary.",
            "reasoning_contract": _REASONING_CONTRACT,
        }
