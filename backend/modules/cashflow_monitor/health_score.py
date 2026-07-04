"""
Cashflow Monitor — composite Health Score (0-100).

v3.0 — Redesigned model with 5 financially distinct dimensions.

    Dimension                Weight  What it measures
    ───────────────────────  ──────  ─────────────────────────────────────
    1. Margine Netto           25    Net profitability after all costs
    2. Dinamica Ricavi         20    Revenue + margin trajectory
    3. Resilienza Strutturale  20    Break-even distance + fixed cost leverage
    4. Ciclo di Cassa          25    Cash conversion timing (DSO - DPO)
    5. Rischio Operativo       10    Alert signals + data completeness
                               ───
                         Total 100

Design principles:
  - Each dimension measures a DISTINCT financial concept (no redundancy).
  - Dimensions that are not computable (missing data) are EXCLUDED from the
    score, and their weight is redistributed. A 'confidence' field indicates
    how much of the total weight was actually computable.
  - Proxy metrics (giorni_copertura, cost_to_revenue_ratio, etc.) are returned
    as diagnostics only — they are NOT scored.

Public interface:
    compute_health_score(kpis, alerts_high_count, disabled_dimensions) -> dict
"""

from typing import Optional


# ── Dimension registry ────────────────────────────────────────────────────────

DIMENSION_KEYS = [
    "net_margin",            # Margine Netto
    "revenue_dynamics",      # Dinamica Ricavi
    "structural_strength",   # Resilienza Strutturale
    "cash_cycle",            # Ciclo di Cassa
    "operational_risk",      # Rischio Operativo
]

_DEFAULT_WEIGHTS = {
    "net_margin": 25,
    "revenue_dynamics": 20,
    "structural_strength": 20,
    "cash_cycle": 25,
    "operational_risk": 10,
}

# Old dimension keys → new keys (for config migration)
_LEGACY_KEY_MAP = {
    "net_result": "net_margin",
    "outflow_ratio": None,          # removed (absorbed into net_margin concept)
    "operating_margin": None,       # removed (redundant)
    "liquidity": None,              # removed (diagnostic only)
    "dso": "cash_cycle",            # merged
    "dpo": "cash_cycle",            # merged
    "break_even": "structural_strength",
    "critical_alerts": "operational_risk",
}


# ── Scoring functions per dimension ───────────────────────────────────────────

def _score_net_margin(kpis: dict) -> dict:
    """Dim 1: Margine Netto (25pt). Returns {points, max, raw_value, status, ...}."""
    sales = kpis.get("total_sales", 0)
    net = kpis.get("net_after_fixed", 0)

    if sales <= 0:
        return {
            "points": None, "max": 25, "raw_value": None, "raw_unit": "%",
            "status": "not_computable", "reason": "Nessun dato di vendita",
        }

    margin = round((net / sales) * 100, 1)

    if margin > 15:    pts = 25
    elif margin > 10:  pts = 21
    elif margin > 5:   pts = 16
    elif margin > 0:   pts = 10
    elif margin == 0:  pts = 5   # break-even
    else:              pts = 0   # loss

    return {
        "points": pts, "max": 25, "raw_value": margin, "raw_unit": "%",
        "status": "active",
    }


def _score_revenue_dynamics(kpis: dict) -> dict:
    """Dim 2: Dinamica Ricavi (20pt = 10 sales trend + 10 margin trend)."""
    sales_trend = kpis.get("sales_trend_pct")
    margin_trend = kpis.get("margin_trend_pp")

    # Sub-score A: sales trend (10pt)
    if sales_trend is not None:
        if sales_trend > 10:    pts_a = 10
        elif sales_trend > 0:   pts_a = 7
        elif sales_trend > -10: pts_a = 4
        elif sales_trend > -20: pts_a = 2
        else:                    pts_a = 0
        sub_a_computable = True
    else:
        pts_a = 0
        sub_a_computable = False

    # Sub-score B: margin trend (10pt)
    if margin_trend is not None:
        if margin_trend > 2:     pts_b = 10
        elif margin_trend > -2:  pts_b = 7
        elif margin_trend > -5:  pts_b = 4
        else:                     pts_b = 0
        sub_b_computable = True
    else:
        pts_b = 0
        sub_b_computable = False

    if not sub_a_computable and not sub_b_computable:
        return {
            "points": None, "max": 20, "raw_value": None, "raw_unit": "composite",
            "status": "not_computable", "reason": "Nessun dato del periodo precedente",
        }

    # If only one sub is computable, rescale
    if sub_a_computable and sub_b_computable:
        pts = pts_a + pts_b
        max_pts = 20
    elif sub_a_computable:
        pts = round(pts_a * 2)  # rescale 10→20
        max_pts = 20
    else:
        pts = round(pts_b * 2)
        max_pts = 20

    return {
        "points": pts, "max": max_pts,
        "raw_value": {"sales_trend_pct": sales_trend, "margin_trend_pp": margin_trend},
        "raw_unit": "composite", "status": "active",
    }


def _score_structural_strength(kpis: dict) -> dict:
    """Dim 3: Resilienza Strutturale (20pt = 10 break-even + 10 fixed cost ratio)."""
    sales = kpis.get("total_sales", 0)
    be = kpis.get("break_even")
    fixed_costs = kpis.get("fixed_costs_total", 0)

    # Sub-score A: break-even headroom (10pt)
    sub_a_computable = False
    pts_a = 0
    headroom = None
    if be is not None and be > 0 and sales > 0:
        headroom = round(((sales - be) / be) * 100, 1)
        if headroom > 30:    pts_a = 10
        elif headroom > 15:  pts_a = 7
        elif headroom > 0:   pts_a = 4
        else:                 pts_a = 0
        sub_a_computable = True
    elif be is None and fixed_costs > 0:
        pts_a = 0  # structural deficit
        sub_a_computable = True

    # Sub-score B: fixed cost ratio (10pt)
    sub_b_computable = False
    pts_b = 0
    fc_ratio = None
    if sales > 0 and fixed_costs > 0:
        fc_ratio = round((fixed_costs / sales) * 100, 1)
        if fc_ratio < 15:    pts_b = 10
        elif fc_ratio < 25:  pts_b = 7
        elif fc_ratio < 35:  pts_b = 4
        elif fc_ratio < 50:  pts_b = 2
        else:                 pts_b = 0
        sub_b_computable = True

    if not sub_a_computable and not sub_b_computable:
        return {
            "points": None, "max": 20, "raw_value": None, "raw_unit": "composite",
            "status": "not_computable", "reason": "Dati insufficienti (nessun costo fisso o vendita)",
        }

    if sub_a_computable and sub_b_computable:
        pts = pts_a + pts_b
    elif sub_a_computable:
        pts = round(pts_a * 2)
    else:
        pts = round(pts_b * 2)

    return {
        "points": pts, "max": 20,
        "raw_value": {"headroom_pct": headroom, "fixed_cost_ratio": fc_ratio},
        "raw_unit": "composite", "status": "active",
    }


def _score_cash_cycle(kpis: dict) -> dict:
    """Dim 4: Ciclo di Cassa (25pt). Based on cash_conversion_gap = DSO - DPO."""
    gap = kpis.get("cash_conversion_gap")
    has_payment_data = kpis.get("has_payment_status_data", False)

    if not has_payment_data or gap is None:
        return {
            "points": None, "max": 25, "raw_value": None, "raw_unit": "days",
            "status": "not_computable",
            "reason": "Nessun dato di stato pagamento disponibile",
        }

    if gap <= 0:       pts = 25
    elif gap < 15:     pts = 19
    elif gap < 30:     pts = 13
    elif gap < 60:     pts = 6
    else:               pts = 0

    return {
        "points": pts, "max": 25, "raw_value": round(gap, 1), "raw_unit": "days",
        "status": "active",
    }


def _score_operational_risk(kpis: dict, alerts_high_count: int) -> dict:
    """Dim 5: Rischio Operativo (10pt = 5 alerts + 5 data completeness)."""
    # Sub A: alerts (5pt)
    if alerts_high_count == 0:      pts_a = 5
    elif alerts_high_count <= 2:    pts_a = 2
    else:                            pts_a = 0

    # Sub B: data completeness (5pt)
    # Count data sources with at least 1 record in period
    sources = kpis.get("data_sources_present", 0)
    if sources >= 4:    pts_b = 5
    elif sources >= 3:  pts_b = 3
    elif sources >= 2:  pts_b = 1
    else:                pts_b = 0

    return {
        "points": pts_a + pts_b, "max": 10,
        "raw_value": {"alerts_high": alerts_high_count, "data_sources": sources},
        "raw_unit": "composite", "status": "active",
    }


# ── Main scoring engine ──────────────────────────────────────────────────────

def compute_health_score(
    kpis: dict,
    alerts_high_count: int = 0,
    disabled_dimensions: set = None,
) -> dict:
    """Compute the composite health score.

    Returns dict with: score, breakdown, label, color, confidence,
    diagnostics, top_strengths, top_issues, priority_actions, data_caveats.
    """
    if disabled_dimensions is None:
        disabled_dimensions = set()

    try:
        # ── Score each dimension ──────────────────────────────────────────
        raw = {
            "net_margin": _score_net_margin(kpis),
            "revenue_dynamics": _score_revenue_dynamics(kpis),
            "structural_strength": _score_structural_strength(kpis),
            "cash_cycle": _score_cash_cycle(kpis),
            "operational_risk": _score_operational_risk(kpis, alerts_high_count),
        }

        # ── Build breakdown with rescaling ────────────────────────────────
        _DIM_LABELS = {
            "net_margin": "Margine Netto",
            "revenue_dynamics": "Dinamica Ricavi",
            "structural_strength": "Resilienza Strutturale",
            "cash_cycle": "Ciclo di Cassa",
            "operational_risk": "Rischio Operativo",
        }

        breakdown = []
        computable_weight = 0
        total_pts = 0

        # Determine which dimensions are active AND computable
        active_computable = []
        for key in DIMENSION_KEYS:
            entry = raw[key]
            if key in disabled_dimensions:
                breakdown.append({
                    "dimension": _DIM_LABELS[key], "key": key,
                    "points": None, "max": _DEFAULT_WEIGHTS[key],
                    "raw_value": entry.get("raw_value"),
                    "raw_unit": entry.get("raw_unit"),
                    "status": "disabled",
                })
            elif entry["status"] == "not_computable":
                breakdown.append({
                    "dimension": _DIM_LABELS[key], "key": key,
                    "points": None, "max": _DEFAULT_WEIGHTS[key],
                    "raw_value": None,
                    "raw_unit": entry.get("raw_unit"),
                    "status": "not_computable",
                    "reason": entry.get("reason"),
                })
            else:
                active_computable.append(key)

        # Rescale weights for computable dimensions
        computable_weight_sum = sum(_DEFAULT_WEIGHTS[k] for k in active_computable) or 1

        for key in active_computable:
            entry = raw[key]
            rescaled_max = round(_DEFAULT_WEIGHTS[key] / computable_weight_sum * 100, 1)
            rescaled_pts = round(entry["points"] / entry["max"] * rescaled_max, 1) if entry["max"] > 0 else 0

            breakdown.append({
                "dimension": _DIM_LABELS[key], "key": key,
                "points": round(rescaled_pts), "max": round(rescaled_max),
                "raw_value": entry.get("raw_value"),
                "raw_unit": entry.get("raw_unit"),
                "status": "active",
                "is_proxy": entry.get("is_proxy", False),
            })
            total_pts += rescaled_pts
            computable_weight += _DEFAULT_WEIGHTS[key]

        # Sort breakdown: active first (by key order), then not_computable, then disabled
        status_order = {"active": 0, "not_computable": 1, "disabled": 2}
        breakdown.sort(key=lambda b: (status_order.get(b["status"], 3), DIMENSION_KEYS.index(b["key"]) if b["key"] in DIMENSION_KEYS else 99))

        # ── Final score ───────────────────────────────────────────────────
        score = max(0, min(100, round(total_pts)))
        confidence = round(computable_weight / 100, 2)

        if score >= 80:
            label, color = "Eccellente", "#22C55E"
        elif score >= 60:
            label, color = "Buono", "#EAB308"
        elif score >= 40:
            label, color = "Attenzione", "#F97316"
        else:
            label, color = "Critico", "#EF4444"

        # ── Diagnostics (not scored) ──────────────────────────────────────
        diagnostics = _build_diagnostics(kpis)

        # ── Strengths, issues, actions, caveats ───────────────────────────
        top_strengths, top_issues, priority_actions, data_caveats = (
            _build_insights(breakdown, kpis, diagnostics)
        )

        return {
            "score": score,
            "label": label,
            "color": color,
            "confidence": confidence,
            "computable_dimensions": len(active_computable),
            "total_dimensions": len(DIMENSION_KEYS),
            "breakdown": breakdown,
            "diagnostics": diagnostics,
            "top_strengths": top_strengths,
            "top_issues": top_issues,
            "priority_actions": priority_actions,
            "data_caveats": data_caveats,
            "disabled_dimensions": list(disabled_dimensions),
        }

    except Exception:
        return {
            "score": 0, "breakdown": [], "label": "N/D",
            "color": "#94A3B8", "confidence": 0,
            "computable_dimensions": 0, "total_dimensions": len(DIMENSION_KEYS),
            "diagnostics": {}, "top_strengths": [], "top_issues": [],
            "priority_actions": [], "data_caveats": ["Errore nel calcolo del punteggio"],
            "disabled_dimensions": list(disabled_dimensions) if disabled_dimensions else [],
        }


# ── Diagnostic metrics (displayed but not scored) ────────────────────────────

def _build_diagnostics(kpis: dict) -> dict:
    """Build diagnostic metrics that are useful for display but not scored."""
    sales = kpis.get("total_sales", 0)
    total_outflows = kpis.get("total_outflows", 0)
    variable_outflows = kpis.get("variable_outflows", 0)
    period_days = kpis.get("period_days", 30)

    cost_ratio = round((total_outflows / sales * 100), 1) if sales > 0 else None
    op_margin = round(((sales - variable_outflows) / sales * 100), 1) if sales > 0 else None
    burn_rate = round(total_outflows / period_days, 2) if period_days > 0 else None
    net = kpis.get("net_after_fixed", 0)
    coverage_days = round(net / (total_outflows / period_days), 1) if total_outflows > 0 and period_days > 0 and net > 0 else 0

    return {
        "cost_to_revenue_ratio": {"value": cost_ratio, "unit": "%", "label": "Rapporto Costi/Ricavi"},
        "giorni_copertura": {
            "value": coverage_days, "unit": "days", "label": "Copertura Operativa",
            "is_proxy": True,
            "caveat": "Stimato dal margine operativo, non dal saldo bancario",
        },
        "operating_margin_pct": {"value": op_margin, "unit": "%", "label": "Margine Operativo"},
        "dso": {"value": kpis.get("dso"), "unit": "days", "label": "DSO"},
        "dpo": {"value": kpis.get("dpo"), "unit": "days", "label": "DPO"},
        "burn_rate_daily": {"value": burn_rate, "unit": "EUR/day", "label": "Uscite Giornaliere"},
    }


# ── Insight generation ───────────────────────────────────────────────────────

def _build_insights(breakdown, kpis, diagnostics):
    """Generate top strengths, issues, actions, and caveats from breakdown."""
    strengths = []
    issues = []
    actions = []
    caveats = []

    for dim in breakdown:
        if dim["status"] != "active":
            if dim["status"] == "not_computable":
                caveats.append(f"{dim['dimension']}: {dim.get('reason', 'dati insufficienti')}")
            continue

        ratio = dim["points"] / dim["max"] if dim["max"] > 0 else 0

        if ratio >= 0.75:
            strengths.append({"dimension": dim["dimension"], "key": dim["key"]})
        elif ratio < 0.35:
            issues.append({"dimension": dim["dimension"], "key": dim["key"], "priority": "high" if ratio < 0.2 else "medium"})

    # Priority actions from issues
    for issue in issues:
        if issue["key"] == "net_margin":
            actions.append("Ridurre i costi o aumentare i ricavi per migliorare il margine netto")
        elif issue["key"] == "revenue_dynamics":
            actions.append("Analizzare le cause del calo di ricavi o margine")
        elif issue["key"] == "structural_strength":
            actions.append("Valutare la struttura dei costi fissi e la distanza dal break-even")
        elif issue["key"] == "cash_cycle":
            actions.append("Accelerare gli incassi o negoziare termini di pagamento piu lunghi con i fornitori")
        elif issue["key"] == "operational_risk":
            actions.append("Risolvere gli alert critici e completare il caricamento dati")

    # Proxy caveats
    cov = diagnostics.get("giorni_copertura", {})
    if cov.get("is_proxy"):
        caveats.append("Copertura operativa e un indicatore proxy basato sul margine, non sulla liquidita reale")

    # Sparse-data false-good safeguard:
    # When only 1 data source is present (e.g. only sales uploaded) and net margin
    # appears very high (>50%), warn that costs may be missing entirely.
    sources = kpis.get("data_sources_present", 0)
    if sources <= 1:
        for dim in breakdown:
            if dim.get("key") == "net_margin" and dim.get("status") == "active":
                raw_margin = dim.get("raw_value")
                if raw_margin is not None and raw_margin > 50:
                    caveats.append(
                        "Il margine netto potrebbe essere sovrastimato: e stata caricata una sola fonte dati. "
                        "Aggiungi spese operative, acquisti fornitori o costi fissi per un punteggio piu accurato."
                    )
                break

    return strengths[:3], issues[:3], actions[:3], caveats


def migrate_dimension_config(old_config: dict) -> dict:
    """Migrate old 8-dimension config to new 5-dimension config.

    Old keys: net_result, outflow_ratio, operating_margin, liquidity, dso, dpo, break_even, critical_alerts
    New keys: net_margin, revenue_dynamics, structural_strength, cash_cycle, operational_risk
    """
    new_config = {}
    for old_key, enabled in old_config.items():
        new_key = _LEGACY_KEY_MAP.get(old_key)
        if new_key is not None:
            # If the old dimension was disabled, disable the new one too
            # But only if we haven't already set it to True from another mapping
            if new_key not in new_config:
                new_config[new_key] = enabled
            elif not enabled:
                new_config[new_key] = False  # any disabled old key disables the new merged key

    # Ensure all new keys have a value (default True)
    for key in DIMENSION_KEYS:
        if key not in new_config:
            new_config[key] = True

    return new_config
