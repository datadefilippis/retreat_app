"""
Health Score AI Explanation generator.

Default: rule-based explanation (zero API calls).
AI explanation available on-demand via generate_health_explanation_ai().

Public interface:
    generate_health_explanation(health_score: dict, kpis: dict, locale: str) -> str
        Rule-based, always instant, never calls Claude. Never raises.
    generate_health_explanation_ai(health_score: dict, kpis: dict, locale: str) -> str
        AI-powered via Claude. Falls back to rule-based on error. Never raises.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _build_system_prompt(locale: str = "it") -> str:
    """Build locale-aware system prompt for health explanation."""
    from core.locale_utils import get_locale_profile
    profile = get_locale_profile(locale)
    return (
        "You are a financial advisor for SMEs. "
        "Given a financial health score (0-100) with per-dimension breakdown, "
        "write exactly 2-3 short sentences explaining the score. "
        "Be concrete: cite strengths and critical areas with numbers. "
        "No bullet points, no headings, no emoji. Only flowing text. "
        "Maximum 250 characters. "
        "IMPORTANT: This score is a directional indicator (25% based on proxy metrics like estimated operational coverage). "
        "Never present it as an exact measure. Qualify with 'approximately' or 'indicates'. "
        "If 'Copertura operativa' is cited, clarify it is a proxy estimated from burn rate, not actual bank balance. "
        f"{profile.respond_instruction}. "
        f"When citing numbers, use {profile.number_format_hint}."
    )


def _build_user_message(
    health_score: dict,
    kpis: dict,
    period_label: str = "",
    currency: str = "EUR",
) -> str:
    breakdown_lines = "\n".join(
        f"- {b['dimension']}: {b['points']}/{b['max']}"
        for b in health_score.get("breakdown", [])
    )
    period_line = f"Periodo analizzato: {period_label}\n\n" if period_label else ""
    # CH compliance v1: AI prompt now reflects the org's currency so
    # Claude doesn't anchor its narrative on EUR for a CHF merchant.
    return (
        f"{period_line}"
        f"Punteggio: {health_score['score']}/100 ({health_score['label']})\n\n"
        f"Dettaglio dimensioni:\n{breakdown_lines}\n\n"
        f"KPI chiave:\n"
        f"- Risultato netto: {kpis.get('net_after_fixed', 0):,.0f} {currency}\n"
        f"- Margine operativo: {kpis.get('operating_margin_pct', 0):.1f}%\n"
        f"- Ricavi totali: {kpis.get('total_sales', 0):,.0f} {currency}\n"
        f"- Copertura operativa (proxy): {kpis.get('giorni_autonomia', 0):.0f} giorni\n"
        f"- DSO: {kpis.get('dso', 0):.0f} giorni\n"
        f"- Rapporto uscite: {kpis.get('total_outflow_ratio', 0):.1f}%\n\n"
        f"Scrivi 2-3 frasi di spiegazione contestualizzate al periodo indicato."
    )


# ── Locale-aware mappings for the rule-based fallback ──────────────────────────
# Backend (compute_health_score) always emits Italian labels/dimensions.
# We map them here to the user's language for the fallback explanation.

_FALLBACK_LABELS = {
    "it": {
        "Eccellente": "Eccellente", "Buono": "Buono",
        "Attenzione": "Attenzione", "Critico": "Critico", "N/D": "N/D",
    },
    "en": {
        "Eccellente": "Excellent", "Buono": "Good",
        "Attenzione": "Attention", "Critico": "Critical", "N/D": "N/A",
    },
    "de": {
        "Eccellente": "Ausgezeichnet", "Buono": "Gut",
        "Attenzione": "Achtung", "Critico": "Kritisch", "N/D": "k.A.",
    },
    "fr": {
        "Eccellente": "Excellent", "Buono": "Bon",
        "Attenzione": "Attention", "Critico": "Critique", "N/D": "N/D",
    },
}

_FALLBACK_DIMENSIONS = {
    "it": {
        # v3.0 new dimensions
        "Margine Netto": "Margine Netto", "Dinamica Ricavi": "Dinamica Ricavi",
        "Resilienza Strutturale": "Resilienza Strutturale", "Ciclo di Cassa": "Ciclo di Cassa",
        "Rischio Operativo": "Rischio Operativo",
        # Legacy (for backward compat if old breakdown still in use)
        "Risultato Netto": "Risultato Netto", "Rapporto Uscite": "Rapporto Uscite",
        "Margine Operativo": "Margine Operativo", "Liquidità (gg)": "Liquidita (gg)",
        "DSO": "DSO", "DPO": "DPO", "Margine Break-Even": "Margine Break-Even",
        "Alert Critici": "Alert Critici",
    },
    "en": {
        "Margine Netto": "Net Margin", "Dinamica Ricavi": "Revenue Dynamics",
        "Resilienza Strutturale": "Structural Strength", "Ciclo di Cassa": "Cash Cycle",
        "Rischio Operativo": "Operational Risk",
        "Risultato Netto": "Net Result", "Rapporto Uscite": "Outflow Ratio",
        "Margine Operativo": "Operating Margin", "Liquidità (gg)": "Liquidity (days)",
        "DSO": "DSO", "DPO": "DPO", "Margine Break-Even": "Break-Even Margin",
        "Alert Critici": "Critical Alerts",
    },
    "de": {
        "Margine Netto": "Nettomarge", "Dinamica Ricavi": "Umsatzdynamik",
        "Resilienza Strutturale": "Strukturelle Stabilitaet", "Ciclo di Cassa": "Kassenkreislauf",
        "Rischio Operativo": "Operatives Risiko",
        "Risultato Netto": "Nettoergebnis", "Rapporto Uscite": "Ausgabenquote",
        "Margine Operativo": "Operative Marge", "Liquidità (gg)": "Liquiditaet (Tage)",
        "DSO": "DSO", "DPO": "DPO", "Margine Break-Even": "Break-Even-Marge",
        "Alert Critici": "Kritische Warnungen",
    },
    "fr": {
        "Margine Netto": "Marge nette", "Dinamica Ricavi": "Dynamique des revenus",
        "Resilienza Strutturale": "Solidite structurelle", "Ciclo di Cassa": "Cycle de tresorerie",
        "Rischio Operativo": "Risque operationnel",
        "Risultato Netto": "Resultat net", "Rapporto Uscite": "Ratio des depenses",
        "Margine Operativo": "Marge operationnelle", "Liquidità (gg)": "Liquidite (jours)",
        "DSO": "DSO", "DPO": "DPO", "Margine Break-Even": "Seuil de rentabilite",
        "Alert Critici": "Alertes critiques",
    },
}

_FALLBACK_TEMPLATES = {
    "it": {
        "summary": "Salute finanziaria: {label} ({score}/100).",
        "weak":    "Area critica: {dimension} ({points}/{max}).",
        "strong":  "Punto di forza: {dimension}.",
    },
    "en": {
        "summary": "Financial health: {label} ({score}/100).",
        "weak":    "Critical area: {dimension} ({points}/{max}).",
        "strong":  "Strength: {dimension}.",
    },
    "de": {
        "summary": "Finanzgesundheit: {label} ({score}/100).",
        "weak":    "Kritischer Bereich: {dimension} ({points}/{max}).",
        "strong":  "Staerke: {dimension}.",
    },
    "fr": {
        "summary": "Sante financiere : {label} ({score}/100).",
        "weak":    "Zone critique : {dimension} ({points}/{max}).",
        "strong":  "Point fort : {dimension}.",
    },
}


_SPARSE_DATA_WARNING = {
    "it": "Attenzione: il punteggio si basa su una sola fonte dati e potrebbe sovrastimare la salute finanziaria. Carica spese, acquisti o costi fissi per un risultato piu accurato.",
    "en": "Warning: the score is based on a single data source and may overestimate financial health. Upload expenses, purchases, or fixed costs for a more accurate result.",
    "de": "Achtung: Der Score basiert auf nur einer Datenquelle und koennte die finanzielle Gesundheit ueberschaetzen. Laden Sie Ausgaben, Einkaeufe oder Fixkosten fuer ein genaueres Ergebnis.",
    "fr": "Attention : le score repose sur une seule source de donnees et pourrait surestimer la sante financiere. Chargez des depenses, achats ou couts fixes pour un resultat plus precis.",
}


def _generate_fallback(health_score: dict, locale: str = "it") -> str:
    """Rule-based explanation — always used by default (zero API cost)."""
    score = health_score.get("score", 0)
    raw_label = health_score.get("label", "N/D")
    breakdown = health_score.get("breakdown", [])

    labels_map = _FALLBACK_LABELS.get(locale, _FALLBACK_LABELS["it"])
    dims_map = _FALLBACK_DIMENSIONS.get(locale, _FALLBACK_DIMENSIONS["it"])
    templates = _FALLBACK_TEMPLATES.get(locale, _FALLBACK_TEMPLATES["it"])

    label = labels_map.get(raw_label, raw_label)

    # Find weakest and strongest dimensions (skip disabled/not_computable ones)
    weakest = None
    strongest = None
    for b in breakdown:
        if b.get("status") in ("disabled", "not_computable") or b.get("points") is None:
            continue
        ratio = b["points"] / b["max"] if b["max"] > 0 else 1
        if weakest is None or ratio < (weakest["points"] / weakest["max"] if weakest["max"] > 0 else 1):
            weakest = b
        if strongest is None or ratio > (strongest["points"] / strongest["max"] if strongest["max"] > 0 else 0):
            strongest = b

    parts = [templates["summary"].format(label=label, score=score)]

    if weakest and weakest["max"] > 0 and (weakest["points"] / weakest["max"]) < 0.4:
        dim_name = dims_map.get(weakest["dimension"], weakest["dimension"])
        parts.append(templates["weak"].format(
            dimension=dim_name, points=weakest["points"], max=weakest["max"],
        ))

    if strongest and strongest["max"] > 0 and (strongest["points"] / strongest["max"]) > 0.7:
        dim_name = dims_map.get(strongest["dimension"], strongest["dimension"])
        parts.append(templates["strong"].format(dimension=dim_name))

    # Sparse-data false-good safeguard: surface in explanation text
    data_caveats = health_score.get("data_caveats", [])
    has_sparse_warning = any("sola fonte dati" in c or "single data source" in c for c in data_caveats)
    if has_sparse_warning:
        parts.append(_SPARSE_DATA_WARNING.get(locale, _SPARSE_DATA_WARNING["it"]))

    return " ".join(parts)


async def generate_health_explanation(
    health_score: dict, kpis: dict, locale: str = "it",
    period_label: str = "",
) -> str:
    """Rule-based explanation — default for every page load (zero API cost)."""
    if not health_score or health_score.get("score") is None:
        return ""
    return _generate_fallback(health_score, locale=locale)


async def generate_health_explanation_ai(
    health_score: dict, kpis: dict, locale: str = "it",
    period_label: str = "",
    currency: str = "EUR",
    *,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """AI-powered explanation via Claude — called on-demand only. Never raises.

    ``currency`` is forwarded into the user message so Claude reads the
    same unit the merchant configured for the org (CH compliance v1).
    Defaults to EUR for legacy callers.

    Wave 8A.0: accepts ``org_id`` and ``user_id`` so each AI invocation
    is recorded as an AIUsageEvent (feature="health_explanation").
    When ``org_id`` is None (legacy callers / tests), tracking is
    skipped — but the LLM call still proceeds. Pass it always for
    governance coverage.
    """
    if not health_score or health_score.get("score") is None:
        return ""

    try:
        from services.claude_client import (
            send_message_with_usage, is_available,
            get_active_model, calculate_cost_usd, resolve_non_chat_model,
        )
        from repositories.usage_repository import record_usage

        if not is_available():
            return _generate_fallback(health_score, locale=locale)

        # Wave 8B — governance pre-flight (kill switch + budget).
        # If refused, fall back to rule-based explanation (zero cost).
        if org_id:
            from services.llm.budget_guard import check_budget_or_raise
            await check_budget_or_raise(
                organization_id=org_id, user_id=user_id,
                feature="health_explanation",
                agent_id="health_explanation",
            )

        # Wave 9.B.2 — Haiku is more than enough for a 200-token health
        # explanation (~25% of Sonnet cost).
        _model_override = resolve_non_chat_model() or None
        text, usage = await send_message_with_usage(
            system=_build_system_prompt(locale),
            user_message=_build_user_message(health_score, kpis, period_label, currency=currency),
            max_tokens=200,
            temperature=0.2,
            model_version=_model_override,
        )

        # Wave 8A.0 — record the previously-untracked health_explanation
        # call. This is the second-largest unmetered code path after
        # digest_builder (every dashboard health-explanation click hits
        # Anthropic; was completely invisible to governance).
        if org_id:
            # Wave 9.B.2 — record actual model used (Haiku by default).
            model_version = _model_override or get_active_model()
            cost = calculate_cost_usd(
                tokens_prompt=usage.get("input_tokens"),
                tokens_completion=usage.get("output_tokens"),
                cache_read_tokens=usage.get("cache_read_tokens", 0),
                cache_creation_tokens=usage.get("cache_creation_tokens", 0),
                model_version=model_version,
            )
            try:
                await record_usage(
                    org_id=org_id,
                    module_key="ai_assistant",
                    feature_key="health_explanation",
                    quantity=1,
                    tokens_prompt=usage.get("input_tokens"),
                    tokens_completion=usage.get("output_tokens"),
                    cache_read_tokens=usage.get("cache_read_tokens"),
                    cache_creation_tokens=usage.get("cache_creation_tokens"),
                    # Wave 10.B.6 — surface latency for dashboard SLO panels.
                    latency_ms=usage.get("latency_ms"),
                    provider="anthropic",
                    model_version=model_version,
                    cost_usd=cost,
                    user_id=user_id,
                    agent_id="health_explanation",
                )
            except Exception as track_exc:
                logger.warning(
                    "health_explanation: record_usage failed for org=%s: %s",
                    org_id, track_exc,
                )

        return text
    except Exception as e:
        logger.warning("health_explanation: AI failed, using fallback: %s", e)
        return _generate_fallback(health_score, locale=locale)
