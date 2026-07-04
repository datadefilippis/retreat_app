"""
Cashflow Monitor — Canonical AI Summary Service.

Produces a single trusted summary of the entire Cashflow Monitor state,
designed for AI consumption.  This is the primary data source for AI
reasoning about cashflow — it includes epistemic metadata, data-quality
flags, health score dimensions, status banner, alerts, and scadenzario
context.

The summary is built from the same overview_builder that powers the UI,
ensuring AI and UI always see the same canonical data.

Public interface:
    build_ai_summary(org_id, period, start_date, end_date, locale) -> dict
        Returns a structured AI-safe summary.  Never raises.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Epistemic metadata definitions ───────────────────────────────────────────
# These are attached to metric groups so the AI knows how to interpret them.

_EPISTEMIC = {
    "core_pnl": {
        "epistemic_class": "derived",
        "reliability": "high",
        "interpretive_risk": "low",
        "ai_usability": "strong",
        "caveat": None,
    },
    "observed_totals": {
        "epistemic_class": "observed",
        "reliability": "high",
        "interpretive_risk": "low",
        "ai_usability": "strong",
        "caveat": None,
    },
    "fixed_costs": {
        "epistemic_class": "estimated",
        "reliability": "medium",
        "interpretive_risk": "medium",
        "ai_usability": "partial",
        "caveat": "Fixed costs are prorated from nominal monthly/quarterly/annual values. Actual amounts may differ by up to 3%.",
    },
    "break_even": {
        "epistemic_class": "estimated",
        "reliability": "medium",
        "interpretive_risk": "medium",
        "ai_usability": "partial",
        "caveat": "Break-even depends on prorated fixed costs. Returns null when variable costs exceed revenue or no fixed costs exist.",
    },
    "autonomy": {
        "epistemic_class": "proxy",
        "reliability": "low",
        "interpretive_risk": "high",
        "ai_usability": "weak",
        "caveat": "Giorni Autonomia is a proxy based on period cashflow accumulation, NOT actual bank balance. Do not present as factual cash runway.",
    },
    "scadenzario": {
        "epistemic_class": "insufficient_data",
        "reliability": "conditional",
        "interpretive_risk": "high",
        "ai_usability": "weak",
        "caveat": "DSO, DPO, CCC, receivables and payables depend on payment_status and due_date fields being populated. Zero values may mean no data, not absence of unpaid invoices.",
    },
    "yoy": {
        "epistemic_class": "estimated",
        "reliability": "medium",
        "interpretive_risk": "medium",
        "ai_usability": "partial",
        "caveat": "Year-over-year comparison for net result and outflow ratio uses current fixed costs for both years. If fixed costs changed, the comparison is approximate.",
    },
    "yoy_clean": {
        "epistemic_class": "derived",
        "reliability": "high",
        "interpretive_risk": "low",
        "ai_usability": "strong",
        "caveat": None,
    },
    "health_score": {
        "epistemic_class": "estimated",
        "reliability": "medium",
        "interpretive_risk": "high",
        "ai_usability": "partial",
        "caveat": "Health score is a weighted composite of 8 dimensions. 25% of weight comes from proxy/conditional inputs. Treat as a directional signal, not a precise diagnosis.",
    },
    "alerts": {
        "epistemic_class": "derived",
        "reliability": "high",
        "interpretive_risk": "low",
        "ai_usability": "strong",
        "caveat": "Alert thresholds are hardcoded. Scadenzario-related alerts depend on payment data quality.",
    },
    "status_banner": {
        "epistemic_class": "derived",
        "reliability": "high",
        "interpretive_risk": "low",
        "ai_usability": "strong",
        "caveat": None,
    },
}


def _build_drivers(kpis: dict, categories: dict, suppliers: dict) -> dict:
    """Identify the dominant cost driver and structural diagnosis."""
    sales = kpis.get("total_sales", 0)
    expenses = kpis.get("total_expenses", 0)
    purchases = kpis.get("supplier_purchases", 0)
    fixed = kpis.get("fixed_costs_total", 0)
    net = kpis.get("net_after_fixed", 0)
    ratio = kpis.get("total_outflow_ratio", 0)
    margin_pct = kpis.get("operating_margin_pct", 0)

    # Identify dominant cost bucket
    buckets = [
        ("operating_expenses", expenses),
        ("supplier_purchases", purchases),
        ("fixed_costs", fixed),
    ]
    buckets.sort(key=lambda x: x[1], reverse=True)
    dominant = buckets[0] if buckets[0][1] > 0 else None

    # Structural diagnosis
    if sales <= 0:
        diagnosis = "no_revenue"
        diagnosis_text = "No revenue recorded in this period."
    elif net > 0 and ratio < 80:
        diagnosis = "healthy"
        diagnosis_text = "Business is profitable with costs well under control."
    elif net > 0 and ratio >= 80:
        diagnosis = "profitable_but_tight"
        diagnosis_text = "Business is profitable but margins are tight. Cost pressure is high."
    elif net <= 0 and margin_pct > 0:
        diagnosis = "fixed_cost_problem"
        diagnosis_text = "Variable costs are manageable but fixed costs push the result negative."
    elif net <= 0:
        diagnosis = "structural_deficit"
        diagnosis_text = "Total costs exceed revenue. Both variable and structural costs need attention."
    else:
        diagnosis = "unclear"
        diagnosis_text = "Insufficient data for structural diagnosis."

    # Top expense category
    top_exp_cats = categories.get("top_expenses", [])
    top_expense = None
    if top_exp_cats:
        c = top_exp_cats[0]
        top_expense = {
            "category": c.get("category"),
            "total": c.get("total"),
            "pct_of_expenses": c.get("percentage"),
        }

    # Top supplier
    top_sups = suppliers.get("top_suppliers", [])
    top_supplier = None
    supplier_concentration = None
    if top_sups:
        s = top_sups[0]
        top_supplier = {"name": s.get("supplier"), "total": s.get("total"), "pct": s.get("percentage")}
        if len(top_sups) >= 3:
            top3_total = sum(x.get("total", 0) for x in top_sups[:3])
            supplier_concentration = round(
                (top3_total / purchases * 100) if purchases > 0 else 0, 1
            )

    return {
        "dominant_cost_bucket": dominant[0] if dominant else None,
        "dominant_cost_value": round(dominant[1], 2) if dominant else 0,
        "dominant_cost_pct_of_revenue": round(
            (dominant[1] / sales * 100) if dominant and sales > 0 else 0, 1
        ) if dominant else 0,
        "cost_ranking": [{"bucket": b[0], "value": round(b[1], 2)} for b in buckets if b[1] > 0],
        "diagnosis": diagnosis,
        "diagnosis_text": diagnosis_text,
        "top_expense_category": top_expense,
        "top_supplier": top_supplier,
        "top_3_supplier_concentration_pct": supplier_concentration,
    }


def _yoy_margin_pp(kpis: dict, yoy: dict):
    """Compute YoY margin change in PERCENTAGE POINTS (absolute), not
    as % of %. Wave 14.CONSOLIDATE R4.

    Pre-Wave-14 the YoY block exposed ONLY ``operating_margin_pct`` as
    "the percentage change of the operating margin percentage" — a
    composite figure (e.g. "+25%" when margin went from 12% to 15%)
    that the chat AI consistently misread as "+25 percentage points".
    The actual pp difference (3 pp here) is what merchants want.

    Returns None when current or prior margin is missing, so the chat
    layer can render "n/a" instead of fabricating zero. Rounds to
    1 decimal place for display parity.
    """
    cur = kpis.get("operating_margin_pct")
    # Reconstruct prior margin from yoy absolutes (cashflow_summary
    # doesn't carry it as a single field but the overview_builder
    # passes the prior absolutes through yoy). Defensive across shape.
    prior_sales = yoy.get("total_sales")
    prior_net = yoy.get("net_after_fixed")  # already includes fixed costs
    # Match the live operating_margin formula: (sales - variable_outflows) / sales * 100
    # but we don't have prior variable_outflows here. Fall back to the
    # net-based margin as a CONSERVATIVE proxy when raw operating
    # margin pct of prior year isn't available.
    if cur is None:
        return None
    # Best signal: use the prior-year operating_margin_pct directly if
    # yoy exposed it (some pipelines do, some don't).
    prior_margin = yoy.get("operating_margin_pct")
    if prior_margin is None:
        # Approximation from net & sales — flagged in epistemic caveat.
        if prior_sales and prior_sales > 0 and prior_net is not None:
            prior_margin = (prior_net / prior_sales) * 100
        else:
            return None
    return round(cur - prior_margin, 1)


def _build_period_comparison(kpis: dict) -> dict:
    """Build structured period-over-period deltas.

    Wave 14.CONSOLIDATE R9 — ``sales_trend_pct`` / ``expenses_trend_pct``
    are now None when the prior period had zero sales/expenses (pre-fix
    they were 0.0, which silently masked infinite growth as "stable").
    We preserve None into the OUTPUT (``sales_change_pct``, etc.) so
    the chat AI can render "n/a" or "growth from zero base", and the
    arithmetic comparisons in this function short-circuit safely
    using ``(value or 0)`` patterns.
    """
    sales_trend = kpis.get("sales_trend_pct")
    expenses_trend = kpis.get("expenses_trend_pct")

    # Safe coercions for the arithmetic comparisons below — None is
    # treated as "no signal" (0) for ranking and direction, but we
    # preserve the original None in the output payload so consumers
    # know the comparison was undefined.
    _sales_for_math = sales_trend if sales_trend is not None else 0.0
    _expenses_for_math = expenses_trend if expenses_trend is not None else 0.0

    # Determine what changed most
    changes = [
        ("sales", abs(_sales_for_math), _sales_for_math),
        ("expenses", abs(_expenses_for_math), _expenses_for_math),
    ]
    changes.sort(key=lambda x: x[1], reverse=True)
    biggest = changes[0] if changes[0][1] > 0 else None

    return {
        # Preserve None (R9) so consumers can render "n/a" precisely.
        "sales_change_pct": sales_trend,
        "expenses_change_pct": expenses_trend,
        "biggest_change": {
            "metric": biggest[0],
            "change_pct": biggest[2],
            "direction": "up" if biggest[2] > 0 else "down",
        } if biggest else None,
        "net_direction": (
            "improving" if _sales_for_math > 0 and _expenses_for_math <= 0 else
            "mixed" if (_sales_for_math > 0) != (_expenses_for_math > 0) else
            "worsening" if _sales_for_math < 0 and _expenses_for_math >= 0 else
            "stable"
        ),
        # Wave 14.CONSOLIDATE R9 — explicit undefined flags so the AI
        # KNOWS whether the trend was real-zero vs undefined-due-to-
        # no-prev-baseline. Pre-fix the model couldn't tell.
        "_undefined_metrics": [
            m for m, v in [("sales", sales_trend),
                            ("expenses", expenses_trend)]
            if v is None
        ],
        # Wave 14.CONSOLIDATE R8 — explicit "net result is negative"
        # signal. Pre-fix the ``net_direction`` field semantics were
        # ambiguous: "stable" could mean either "trend is flat" OR
        # "net result is consistently around zero/negative". Now the
        # AI can read this binary flag and ALWAYS qualify a negative
        # net (loss) regardless of trend direction.
        "net_is_negative": (
            kpis.get("net_after_fixed") is not None
            and kpis.get("net_after_fixed") < 0
        ),
    }


def _build_risk_focus(status: dict, alerts: dict, kpis: dict, scad_quality: dict) -> list:
    """Identify the top 1-2 risks from available data."""
    risks = []

    # Status-derived risk
    level = status.get("level", "")
    if level in ("critical", "warning"):
        risks.append({
            "source": "status_banner",
            "severity": level,
            "description": status.get("message", ""),
            "driver": status.get("primary_driver", ""),
        })

    # Alert-derived risk
    high_alerts = alerts.get("by_severity", {}).get("high", 0)
    if high_alerts > 0:
        risks.append({
            "source": "alerts",
            "severity": "high",
            "description": f"{high_alerts} high-severity alert(s) active.",
            "driver": "high_alerts",
        })

    # Scadenzario-derived risk
    if scad_quality.get("quality") == "no_payment_data":
        risks.append({
            "source": "data_quality",
            "severity": "informational",
            "description": "Payment data not yet populated. Collections risk cannot be assessed.",
            "driver": "missing_payment_data",
        })

    # Structural risk
    ratio = kpis.get("total_outflow_ratio", 0)
    if ratio > 100:
        risks.append({
            "source": "structure",
            "severity": "critical",
            "description": f"Total outflows are {ratio}% of revenue — spending exceeds income.",
            "driver": "outflow_exceeds_revenue",
        })

    return risks[:3]


def _build_action_focus(drivers: dict, risks: list, kpis: dict) -> list:
    """Suggest 1-2 data-grounded actions based on the dominant issue."""
    actions = []
    diagnosis = drivers.get("diagnosis", "")
    dominant = drivers.get("dominant_cost_bucket", "")

    if diagnosis == "structural_deficit":
        actions.append({
            "priority": 1,
            "action": f"Review the dominant cost bucket ({dominant}) for immediate reduction opportunities.",
            "reason": "Costs exceed revenue. The first priority is reducing the largest cost category.",
            "data_grounded": True,
        })
    elif diagnosis == "fixed_cost_problem":
        actions.append({
            "priority": 1,
            "action": "Review fixed costs (rent, salaries, subscriptions) for renegotiation or reduction.",
            "reason": "Variable margins are healthy but fixed costs push the result negative.",
            "data_grounded": True,
        })
    elif diagnosis == "profitable_but_tight":
        actions.append({
            "priority": 1,
            "action": f"Focus on the top expense category to improve margins.",
            "reason": f"Outflow ratio is {kpis.get('total_outflow_ratio', 0)}% — margins are narrow.",
            "data_grounded": True,
        })

    # Supplier concentration action
    conc = drivers.get("top_3_supplier_concentration_pct")
    if conc and conc > 60:
        actions.append({
            "priority": 2,
            "action": "Diversify supplier base — top 3 suppliers account for over 60% of purchases.",
            "reason": f"Top 3 supplier concentration: {conc}%. High dependency risk.",
            "data_grounded": True,
        })

    # Data quality action
    for risk in risks:
        if risk.get("driver") == "missing_payment_data":
            actions.append({
                "priority": 2,
                "action": "Start tracking payment status and due dates on sales and purchase records.",
                "reason": "Collections risk and cash cycle analysis are currently blind spots.",
                "data_grounded": True,
            })
            break

    return actions[:3]


def _build_analytical_blocks(kpis, categories, suppliers, status, alerts_data, scad_quality):
    """Compose all analytical blocks — called once, avoids redundant computation."""
    drivers = _build_drivers(kpis, categories, suppliers)
    risks = _build_risk_focus(status, alerts_data, kpis, scad_quality)
    return {
        "drivers": drivers,
        "period_comparison": _build_period_comparison(kpis),
        "risk_focus": risks,
        "action_focus": _build_action_focus(drivers, risks, kpis),
    }


def _assess_scadenzario_quality(overview: dict) -> dict:
    """Assess data quality for scadenzario metrics.

    Returns a data-quality assessment with explicit flags so the AI
    can distinguish real zeros from missing-data zeros.
    """
    kpis = overview.get("kpis", {})
    scad = overview.get("scadenzario", {})

    recv_aging = scad.get("receivables_aging", [])
    pay_aging = scad.get("payables_aging", [])
    upcoming_recv = scad.get("upcoming_receivables", [])
    upcoming_pay = scad.get("upcoming_payables", [])

    has_any_aging = len(recv_aging) > 0 or len(pay_aging) > 0
    has_any_upcoming = len(upcoming_recv) > 0 or len(upcoming_pay) > 0
    has_any_scad_data = has_any_aging or has_any_upcoming
    open_recv = kpis.get("open_receivables", 0)
    open_pay = kpis.get("open_payables", 0)
    has_open_data = open_recv > 0 or open_pay > 0

    if has_any_scad_data or has_open_data:
        coverage = "partial" if not (has_any_aging and has_any_upcoming) else "good"
        quality = "usable"
    else:
        coverage = "none"
        quality = "no_payment_data"

    return {
        "quality": quality,
        "coverage": coverage,
        "has_receivables_data": open_recv > 0 or len(recv_aging) > 0,
        "has_payables_data": open_pay > 0 or len(pay_aging) > 0,
        "has_aging_data": has_any_aging,
        "has_upcoming_data": has_any_upcoming,
        "warning": (
            "Payment status and due date fields are not populated. "
            "Scadenzario metrics (DSO, DPO, CCC, aging, receivables, payables) "
            "cannot be computed reliably. Zero values mean no data, not absence of debt."
        ) if quality == "no_payment_data" else None,
    }


async def build_ai_summary(
    org_id: str,
    period: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    locale: str = "it",
) -> dict:
    """Build the canonical AI-safe summary for Cashflow Monitor.

    Returns a structured dict with all data the AI needs for holistic
    cashflow reasoning, including epistemic metadata and data-quality flags.

    Never raises — returns a minimal "no data" response on error.
    """
    try:
        from modules.cashflow_monitor.overview_builder import build_overview

        overview = await build_overview(
            org_id, period, start_date, end_date, locale=locale,
        )

        # Wave 1.10 (2026-05) — resolve org currency once. Pre-Wave-1.10
        # this canonical cashflow summary didn't expose the merchant's
        # currency at the root level, so when the AI used it as the
        # primary data source for a CHF org, it defaulted to citing EUR.
        # See B12 in docs/operations/ai-baseline-2026-05.md.
        from repositories import organization_repository
        from services.currency_service import get_currency_for_org
        _org_doc = await organization_repository.find_by_id(org_id)
        org_currency = get_currency_for_org(_org_doc or {})

        if overview is None:
            return {
                "has_data": False,
                "period": {"label": period},
                "currency": org_currency,
                "message": "No sales or expense data available for this period.",
            }

        kpis = overview.get("kpis", {})
        yoy = overview.get("yoy", {})
        health = overview.get("health_score", {})
        status = overview.get("status", {})
        alerts_data = overview.get("alerts", {})
        scad = overview.get("scadenzario", {})
        categories = overview.get("categories", {})
        suppliers = overview.get("suppliers", {})

        # Scadenzario data quality assessment
        scad_quality = _assess_scadenzario_quality(overview)

        return {
            "has_data": True,
            "period": overview.get("period", {}),
            "currency": org_currency,

            # ── Block temporal scopes (AI must read before reasoning) ─────
            "block_scopes": {
                "pnl":                {"scope": "period_filtered", "note": "Filtered to requested date range."},
                "trends":             {"scope": "period_filtered", "note": "Compares requested period vs immediately preceding period of same length."},
                "yoy":                {"scope": "period_filtered", "note": "Compares requested period vs same dates one year ago."},
                "health_score":       {"scope": "period_filtered", "note": "Computed from period KPIs. Reflects requested date range."},
                "status":             {"scope": "period_filtered", "note": "Derived from period KPIs and current open alerts."},
                "drivers":            {"scope": "period_filtered", "note": "Analysis of the requested period data."},
                "period_comparison":  {"scope": "period_filtered", "note": "Period vs previous period deltas."},
                "top_expense_categories": {"scope": "period_filtered", "note": "Category breakdown for requested period."},
                "top_sales_categories":   {"scope": "period_filtered", "note": "Same."},
                "top_suppliers":      {"scope": "period_filtered", "note": "Supplier ranking for requested period."},
                "scadenzario":        {"scope": "current_state", "note": "Open receivables/payables/aging reflect CURRENT state, not a historical snapshot. DSO/DPO use period sales as denominator but open amounts are current."},
                "alerts":             {"scope": "current_state", "note": "Open alerts across all time. Not filtered to requested period."},
                "risk_focus":         {"scope": "mixed", "note": "Combines period-filtered status with current-state alerts and data quality."},
                "action_focus":       {"scope": "period_filtered", "note": "Actions derived from period analysis."},
                # Wave 14.CONSOLIDATE R6 — ``status.level`` is derived
                # from period KPIs (margin, ratio) AND includes the
                # COUNT of currently-open high-severity alerts. That
                # mixed sourcing was previously misdeclared as
                # ``period_filtered``, leading the chat AI to treat
                # the level as if it described only the period.
                # Declaring ``hybrid`` lets the AI qualify its claim
                # ("status reflects the period plus current alerts").
                "status":             {"scope": "hybrid", "note": "Derived from period KPIs (margin/ratio) AND current-state high-severity alert count. Mention both factors when explaining the level."},
            },

            # ── Canonical P&L ─────────────────────────────────────────────
            "pnl": {
                "total_sales": kpis.get("total_sales"),
                "total_expenses": kpis.get("total_expenses"),
                "supplier_purchases": kpis.get("supplier_purchases"),
                "fixed_costs_total": kpis.get("fixed_costs_total"),
                "total_outflows": kpis.get("total_outflows"),
                "net_after_fixed": kpis.get("net_after_fixed"),
                "total_outflow_ratio_pct": kpis.get("total_outflow_ratio"),
                "operating_margin": kpis.get("operating_margin"),
                "operating_margin_pct": kpis.get("operating_margin_pct"),
                "burn_rate_total": kpis.get("burn_rate_total"),
                "fixed_costs_pct": kpis.get("fixed_costs_pct"),
                "break_even": kpis.get("break_even"),
                "giorni_autonomia": kpis.get("giorni_autonomia"),
                "epistemic": {
                    "totals": _EPISTEMIC["observed_totals"],
                    "net_and_ratios": _EPISTEMIC["core_pnl"],
                    "fixed_costs": _EPISTEMIC["fixed_costs"],
                    "break_even": _EPISTEMIC["break_even"],
                    "giorni_autonomia": _EPISTEMIC["autonomy"],
                },
            },

            # ── Trends (Wave 14.CONSOLIDATE R2 — DEPRECATED) ──────────────
            # The ``trends`` block contained the SAME numbers as
            # ``period_comparison.{sales,expenses}_change_pct`` under
            # different field names, leading the chat AI to either cite
            # them twice or pick at random which block to read. Wave 14
            # makes ``period_comparison`` the single authoritative
            # block; ``trends`` is retained ONLY for backward compat
            # with any consumer still reading it (frontend, archived
            # digests, ai_eval_harness expectations) — its values are
            # IDENTICAL to period_comparison so the redundancy is
            # harmless but the duplication is loud-deprecated below.
            "trends": {
                "sales_vs_prev_period_pct": kpis.get("sales_trend_pct"),
                "expenses_vs_prev_period_pct": kpis.get("expenses_trend_pct"),
                "_deprecated": (
                    "Wave 14.CONSOLIDATE R2 — values duplicated from "
                    "period_comparison block. Read period_comparison."
                    "sales_change_pct / expenses_change_pct instead. "
                    "Will be removed in a future wave."
                ),
            },

            # ── YoY ──────────────────────────────────────────────────────
            # Wave 14.CONSOLIDATE R4 — split operating_margin_pct YoY
            # into TWO explicit fields:
            #   * ``operating_margin_pct_change`` — % change of the
            #     percentage (e.g. 25% from 12% to 15%); easy to
            #     misread as "+25 pp" so we keep the name suffixed
            #     with ``_change`` and pair it with...
            #   * ``operating_margin_pct_pp_change`` — the simple
            #     ``current_margin_pct - prev_margin_pct`` difference
            #     in PERCENTAGE POINTS (e.g. +3pp from 12% to 15%).
            # Pre-Wave-14 only the first was emitted under the
            # ambiguous name ``operating_margin_pct``.
            #
            # Wave 14.CONSOLIDATE R5 — operating_margin moved from
            # the ``yoy_clean`` epistemic class (no caveat) to the
            # ``yoy`` class (caveat about fixed-costs assumption)
            # since margin computation depends on the same fixed-cost
            # baseline the net/ratio comparison does.
            "yoy": {
                "has_data": yoy.get("has_data", False),
                "period_start": yoy.get("period_start"),
                "period_end": yoy.get("period_end"),
                "pct": {
                    "total_sales": yoy.get("pct", {}).get("total_sales"),
                    "total_expenses": yoy.get("pct", {}).get("total_expenses"),
                    # Wave 14 R4 — backward compat alias preserved
                    "operating_margin_pct": yoy.get("pct", {}).get("operating_margin_pct"),
                    # Wave 14 R4 — explicit % change (relative)
                    "operating_margin_pct_change": yoy.get("pct", {}).get("operating_margin_pct"),
                    # Wave 14 R4 — explicit pp diff (absolute) computed inline
                    "operating_margin_pct_pp_change": _yoy_margin_pp(kpis, yoy),
                    "net_after_fixed": yoy.get("pct", {}).get("net_after_fixed"),
                    "total_outflow_ratio": yoy.get("pct", {}).get("total_outflow_ratio"),
                },
                "epistemic": {
                    "sales_and_expenses": _EPISTEMIC["yoy_clean"],
                    # Wave 14 R5: margin now correctly carries the
                    # fixed-cost assumption caveat (was yoy_clean).
                    "operating_margin": _EPISTEMIC["yoy"],
                    "net_and_ratio": _EPISTEMIC["yoy"],
                },
            },

            # ── Scadenzario ───────────────────────────────────────────────
            "scadenzario": {
                "dso": kpis.get("dso"),
                "dpo": kpis.get("dpo"),
                "cash_conversion_cycle": kpis.get("cash_conversion_cycle"),
                "open_receivables": kpis.get("open_receivables"),
                "open_payables": kpis.get("open_payables"),
                "data_quality": scad_quality,
                "epistemic": _EPISTEMIC["scadenzario"],
            },

            # ── Health Score ──────────────────────────────────────────────
            "health_score": {
                "score": health.get("score"),
                "label": health.get("label"),
                "color": health.get("color"),
                "explanation": health.get("explanation"),
                "breakdown": health.get("breakdown", []),
                "epistemic": _EPISTEMIC["health_score"],
            },

            # ── Status Banner ─────────────────────────────────────────────
            "status": {
                "level": status.get("level"),
                "label": status.get("label"),
                "message": status.get("message"),
                "primary_driver": status.get("primary_driver"),
                "data_warnings": status.get("data_warnings", []),
                "epistemic": _EPISTEMIC["status_banner"],
            },

            # ── Alerts ────────────────────────────────────────────────────
            # Wave 14.CONSOLIDATE R7 — the ``recent`` list is capped
            # at 5 by overview_builder, but ``open_count`` is the TRUE
            # total. Pre-fix the chat AI saw a recent-list-of-5 and
            # treated it as "all open alerts", so when an org had 127
            # active alerts the model reported the wrong magnitude.
            # We now emit ``_total_count_note`` when the gap exists so
            # the model can qualify its answer.
            "alerts": (lambda _ac=alerts_data.get("open_count", 0),
                              _ar=alerts_data.get("recent", []): {
                "open_count": _ac,
                "by_severity": alerts_data.get("by_severity", {}),
                "recent": _ar,
                "epistemic": _EPISTEMIC["alerts"],
                "_total_count_note": (
                    f"Showing {len(_ar)} most recent of {_ac} total open alerts."
                    if len(_ar) < _ac else None
                ),
            })(),

            # ── Top Categories ────────────────────────────────────────────
            "top_expense_categories": [
                {"name": c.get("category"), "total": c.get("total"), "pct": c.get("percentage")}
                for c in categories.get("top_expenses", [])[:5]
            ],
            "top_sales_categories": [
                {"name": c.get("category"), "total": c.get("total"), "pct": c.get("percentage")}
                for c in categories.get("top_sales", [])[:5]
            ],

            # ── Top Suppliers ─────────────────────────────────────────────
            "top_suppliers": [
                {"name": s.get("supplier"), "total": s.get("total"), "pct": s.get("percentage")}
                for s in suppliers.get("top_suppliers", [])[:5]
            ],

            # ── Analytical Blocks (analyst-grade reasoning support) ───────
            **_build_analytical_blocks(kpis, categories, suppliers, status, alerts_data, scad_quality),
        }

    except Exception as exc:
        logger.error("cashflow_summary: build_ai_summary failed: %s", exc, exc_info=True)
        return {
            "has_data": False,
            "error": "Failed to build cashflow summary.",
        }
