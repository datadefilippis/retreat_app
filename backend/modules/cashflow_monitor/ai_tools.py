"""
Cashflow Monitor — AI tool definitions and execution.

Provider-agnostic tool definitions for the AI chat assistant.
All tools query cashflow-specific data (sales, expenses, purchases,
fixed costs, receivables/payables) via analytics_repository.

Provider-specific formatting (e.g. Anthropic input_schema) is handled
by the platform's ai_tool_registry, not here.

Public interface:
    TOOL_DEFINITIONS  — list of provider-agnostic tool dicts
    execute_tool(org_id, tool_name, tool_input) -> dict
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# ── Provider-agnostic tool definitions ───────────────────────────────────────

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "query_business_summary",
        "description": (
            "Riepilogo cross-modulo (cashflow + clienti + segnali commerce) allineato "
            "temporalmente sullo stesso periodo. "
            "SCOPE: period_filtered. "
            "Restituisce: P&L completo (4 bucket), top clienti del periodo, "
            "concentrazione, alert, health_score (0-100), reasoning_contract con "
            "le regole di confrontabilita tra moduli. "
            "Usa come PRIMA SCELTA per domande trasversali: 'perche peggiora il "
            "risultato?', 'i clienti stanno cambiando?', 'la crescita e sana?', "
            "'quale modulo spiega il problema?'. "
            "Param: period='7d|30d|90d|1y|ytd|mtd|qtd' OPPURE "
            "start_date+end_date (YYYY-MM-DD). Default 30d."
        ),
        "parameters": {
            "period": {
                "type": "string",
                "description": "Periodo standard: 7d, 30d, 90d. Ignorato se start_date e end_date sono specificati. Default 30d.",
            },
            "start_date": {
                "type": "string",
                "description": "Data inizio periodo in formato YYYY-MM-DD. Opzionale — usare per date personalizzate.",
            },
            "end_date": {
                "type": "string",
                "description": "Data fine periodo in formato YYYY-MM-DD. Opzionale — usare per date personalizzate.",
            },
        },
        "required": [],
    },
    {
        "name": "query_cashflow_summary",
        "description": (
            "Riepilogo finanziario completo per il periodo. "
            "SCOPE: period_filtered. "
            "Restituisce: 4 bucket di costo (spese operative, acquisti fornitori, "
            "costi fissi prorati → net_after_fixed), margine, incidenza uscite, "
            "health_score (0-100), alert, scadenzario con qualita dati, yoy.pct.*, "
            "top categorie. "
            "Usa come PRIMA SCELTA per qualsiasi domanda su cashflow, fatturato, "
            "salute finanziaria del periodo: 'come va il fatturato?', 'qual e il "
            "mio health score?', 'sto guadagnando o perdendo?'. "
            "Param: period='7d|30d|90d|1y|ytd|mtd|qtd' OPPURE "
            "start_date+end_date (YYYY-MM-DD). Default 30d."
        ),
        "parameters": {
            "period": {
                "type": "string",
                "description": "Periodo standard: 7d, 30d, 90d. Ignorato se start_date e end_date sono specificati. Default 30d.",
            },
            "start_date": {
                "type": "string",
                "description": "Data inizio periodo in formato YYYY-MM-DD. Opzionale.",
            },
            "end_date": {
                "type": "string",
                "description": "Data fine periodo in formato YYYY-MM-DD. Opzionale.",
            },
        },
        "required": [],
    },
    {
        "name": "query_revenue",
        "description": (
            "Ricavi/vendite del periodo. "
            "SCOPE: period_filtered. "
            "Restituisce: totale, breakdown giornaliero, breakdown per categoria. "
            "Usa quando l'utente chiede SOLO il fatturato ('quanto ho fatturato?', "
            "'vendite di questa settimana'). Per analisi piu' ampie con margine e "
            "salute preferisci query_cashflow_summary o query_business_summary. "
            "Param OBBLIGATORI: start_date+end_date (YYYY-MM-DD)."
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
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_expenses",
        "description": (
            "Spese operative del periodo (bucket A, esclude acquisti fornitori e "
            "costi fissi). "
            "SCOPE: period_filtered. "
            "Restituisce: totale, breakdown giornaliero, breakdown per categoria. "
            "Usa per domande mirate sulle uscite ('quanto ho speso?', 'top "
            "categoria di spesa'). Per un quadro completo dei costi (incluso "
            "fornitori + costi fissi) preferisci query_cashflow o "
            "query_cashflow_summary. "
            "Param OBBLIGATORI: start_date+end_date (YYYY-MM-DD)."
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
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_purchases",
        "description": (
            "Interroga gli acquisti da fornitori in un periodo specifico. "
            "Restituisce il totale, il breakdown giornaliero e il breakdown per fornitore. "
            "Opzionalmente, può raggruppare per prodotto o categoria usando group_by."
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
            "group_by": {
                "type": "string",
                "description": "Raggruppamento opzionale: 'supplier' (default), 'product' (prodotto specifico), 'category' (categoria/raggruppamento)",
            },
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_fixed_costs",
        "description": (
            "Costi fissi proratati per il periodo (totale + breakdown per "
            "categoria). "
            "SCOPE: period_filtered. "
            "Restituisce: totale proratato, breakdown per categoria, totale "
            "voci attive. "
            "Usa per domande aggregate: 'quanto pago di costi fissi?', "
            "'totale costi fissi del periodo'. "
            "Per il dettaglio VOCE PER VOCE (con nome, monthly, giorni "
            "attivi, contributo prorato e flag terminated_in_period) usa "
            "invece query_fixed_costs_detail. "
            "Param OBBLIGATORI: start_date+end_date (YYYY-MM-DD)."
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
        },
        "required": ["start_date", "end_date"],
    },
    {
        # Wave 14.HOTFIX4 (F3)
        "name": "query_health_score_breakdown",
        "description": (
            "Dettaglio delle 5 dimensioni che compongono lo health_score "
            "(0-100): net_margin, revenue_dynamics, structural_strength, "
            "cash_cycle, operational_risk. "
            "SCOPE: period_filtered. "
            "Restituisce: score finale, label, color, explanation, e "
            "breakdown per ogni dimensione con points / max / raw_value / "
            "raw_unit / status ('active' o 'not_computable' o 'disabled'). "
            "Usa per spiegare lo score: 'perche il mio score e X?', "
            "'cosa sta peggiorando lo score?', 'su cosa devo migliorare?', "
            "'quali dimensioni sono peggio?'. "
            "Param: period='7d|30d|90d|1y|ytd|mtd|qtd' OPPURE "
            "start_date+end_date (YYYY-MM-DD). Default 30d."
        ),
        "parameters": {
            "period": {
                "type": "string",
                "description": (
                    "Periodo standard: 7d, 30d, 90d, 1y, ytd, mtd, qtd. "
                    "Ignorato se start_date e end_date sono specificati. "
                    "Default 30d."
                ),
            },
            "start_date": {
                "type": "string",
                "description": "Data inizio periodo (YYYY-MM-DD). Opzionale.",
            },
            "end_date": {
                "type": "string",
                "description": "Data fine periodo (YYYY-MM-DD). Opzionale.",
            },
        },
        "required": [],
    },
    {
        # Wave 14.HOTFIX4 (F2)
        "name": "query_fixed_costs_detail",
        "description": (
            "Dettaglio VOCE PER VOCE dei costi fissi nel periodo, "
            "con proration accurato che rispetta start_date / end_date "
            "di ogni cost. "
            "SCOPE: period_filtered. "
            "Restituisce: lista di costi (ordinati per contributo "
            "decrescente) con name, category, monthly_amount, "
            "validity_start, validity_end, days_active_in_period, "
            "days_in_period, prorated_contribution, terminated_in_period "
            "(True se il cost si è chiuso DENTRO il periodo richiesto). "
            "Usa per domande granulari: 'come si compongono i costi fissi?', "
            "'quali finanziamenti sono ancora attivi?', 'l'Att.3 quanto ha "
            "contribuito YTD 2026?', 'qual è il finanziamento più caro?'. "
            "Param OBBLIGATORI: start_date+end_date (YYYY-MM-DD)."
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
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_cashflow",
        "description": (
            "Calcola il risultato finanziario completo nel periodo. "
            "Include tutti i 4 bucket di costo: spese operative, acquisti fornitori, costi fissi. "
            "Restituisce: ricavi, tutti i costi, risultato netto, incidenza uscite, margine, e serie giornaliera."
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
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_receivables_payables",
        "description": (
            "Interroga crediti e debiti aperti dell'azienda. "
            "Restituisce: totale crediti aperti, totale debiti aperti, "
            "aging buckets (0-30, 31-60, 61-90, >90 giorni), "
            "e scadenze prossime (prossimi 60 giorni)."
        ),
        "parameters": {},
        "required": [],
    },
    {
        "name": "get_data_range",
        "description": (
            "Restituisce il range di date per cui esistono dati aziendali. "
            "Utile per capire quali periodi sono disponibili prima di fare altre query."
        ),
        "parameters": {},
        "required": [],
    },

    # Wave 7B.1: query_order_pipeline, query_fulfillment_status,
    # query_payment_pipeline, query_event_metrics, query_booking_utilization,
    # query_rental_utilization moved to modules.commerce.ai_tools.

    {
        "name": "query_revenue_forecast",
        "description": (
            "Proiezione del fatturato futuro basata su media mobile ponderata e pattern settimanale. "
            "Calcolo statistico puro (non AI). Restituisce: fatturato stimato per il periodo, "
            "livello di confidenza, trend direction, e pattern per giorno della settimana. "
            "Usa per domande tipo 'quanto fatturero il prossimo mese?', 'previsione vendite', "
            "'proiezione fatturato'. IMPORTANTE: qualifica sempre come stima, mai come fatto."
        ),
        "parameters": {
            "horizon_days": {"type": "integer", "description": "Giorni di proiezione futura (default 30, max 90)"},
        },
        "required": [],
    },
    {
        "name": "query_anomaly_detection",
        "description": (
            "Identifica giorni anomali in fatturato e spese (oltre 2 sigma dalla "
            "media mobile a 14 giorni). "
            "SCOPE: period_filtered. "
            "Restituisce: lista giorni anomali con z-score, classificazione "
            "(picco/crollo), valore osservato vs valore atteso. "
            "Usa per: 'ci sono stati giorni anomali?', 'outlier nelle vendite', "
            "'picchi o crolli insoliti', validare se un risultato e' un'anomalia "
            "vs il trend normale. "
            "Param OBBLIGATORI: start_date+end_date (YYYY-MM-DD)."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine (YYYY-MM-DD)"},
        },
        "required": ["start_date", "end_date"],
    },
    {
        "name": "query_data_quality_audit",
        "description": (
            "Audit completo della qualita dei dati aziendali. Controlla: "
            "copertura customer_id nei record finanziari, prodotti senza costo (margini incalcolabili), "
            "clienti senza email o senza transazioni, duplicati potenziali, record senza categoria. "
            "Restituisce un punteggio complessivo e raccomandazioni specifiche. "
            "Usa quando l'utente chiede 'i miei dati sono affidabili?', 'qualita dati', "
            "'perche i margini sono incompleti?', o quando noti copertura dati bassa."
        ),
        "parameters": {},
        "required": [],
    },
    {
        "name": "query_smart_brief",
        "description": (
            "Briefing conciso multi-modulo (aggrega SOLO i moduli attivi: "
            "cashflow + clienti + prodotti + commerce). "
            "SCOPE: period_filtered. "
            "Restituisce: health_score, alert attivi, rischi chiave, opportunita, "
            "azioni prioritarie — formato narrativo. "
            "Usa per domande generiche sullo stato dell'azienda: 'come sto "
            "andando?', 'novita?', 'cosa devo sapere?', 'dammi un brief'. "
            "Per analisi numeriche specifiche preferisci query_cashflow_summary o "
            "query_business_summary. "
            "Param: period='7d|30d|90d|1y|ytd|mtd|qtd' OPPURE "
            "start_date+end_date (YYYY-MM-DD). Default 30d."
        ),
        # Wave 13.5 — period params for parity with query_business_summary
        # and query_cashflow_summary. Pre-13.5 this tool hardcoded a 30-day
        # window even when the user was viewing a different period in the
        # cashflow dashboard, producing briefings that contradicted the UI.
        "parameters": {
            "period": {
                "type": "string",
                "description": (
                    "Periodo standard: 7d, 30d, 90d, 1y, ytd, mtd, qtd. "
                    "Ignorato se start_date e end_date sono specificati. Default 30d."
                ),
            },
            "start_date": {
                "type": "string",
                "description": "Data inizio periodo in formato YYYY-MM-DD. Opzionale.",
            },
            "end_date": {
                "type": "string",
                "description": "Data fine periodo in formato YYYY-MM-DD. Opzionale.",
            },
        },
        "required": [],
    },
    {
        "name": "query_period_comparison",
        "description": (
            "Confronta due periodi side-by-side su fatturato, spese, acquisti, "
            "costi fissi, risultato netto. "
            "SCOPE: period_filtered (entrambi i periodi). "
            "Restituisce: period_baseline (periodo più vecchio) + "
            "period_current (periodo più recente), delta calcolato come "
            "(current - baseline), _change_interpretation con human_label "
            "esplicito ('CRESCITA del +3%' / 'CALO del -5%' / 'PERDITA "
            "RIDOTTA') così non devi dedurre la direzione dal sign. "
            "Usa per: 'come e andato gennaio vs febbraio?', 'Q1 vs Q2?', "
            "'questo mese vs stesso mese anno scorso?', 'YTD vs YTD anno scorso?'. "
            "Param OBBLIGATORI: period_a_start, period_a_end, period_b_start, "
            "period_b_end (tutti YYYY-MM-DD). Wave 14.HOTFIX5: il tool "
            "auto-detect quale dei due è il più recente — puoi emetterli "
            "in qualsiasi ordine. Per leggere la risposta usa SEMPRE i "
            "campi period_baseline/period_current/_change_interpretation, "
            "MAI dedurre la direzione dai pct numerici."
        ),
        "parameters": {
            "period_a_start": {"type": "string", "description": "Data inizio periodo A (YYYY-MM-DD)"},
            "period_a_end": {"type": "string", "description": "Data fine periodo A (YYYY-MM-DD)"},
            "period_b_start": {"type": "string", "description": "Data inizio periodo B (YYYY-MM-DD)"},
            "period_b_end": {"type": "string", "description": "Data fine periodo B (YYYY-MM-DD)"},
        },
        "required": ["period_a_start", "period_a_end", "period_b_start", "period_b_end"],
    },
    {
        "name": "query_monthly_trend",
        "description": (
            "Restituisce il trend mensile di fatturato, spese e risultato netto. "
            "Una riga per mese con variazione percentuale mese su mese. "
            "Usa per domande tipo 'come sta andando il fatturato negli ultimi mesi', "
            "'mostrami il trend mensile', 'andamento da inizio anno'."
        ),
        "parameters": {
            "months": {"type": "integer", "description": "Numero di mesi da mostrare (default 6, max 12)"},
        },
        "required": [],
    },
    {
        "name": "query_data_coherence",
        "description": (
            "Verifica coerenza tra dati cashflow (sales_records) e ordini (orders). "
            "Identifica: ricavi in cashflow senza ordine corrispondente, ordini confermati senza SalesRecord, "
            "disallineamenti tra pagamento ordine e pagamento cashflow. "
            "Usa per audit dati, verifica integrita, identificare inserimenti manuali o dati mancanti."
        ),
        "parameters": {
            "start_date": {"type": "string", "description": "Data inizio periodo (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "Data fine periodo (YYYY-MM-DD)"},
        },
        "required": ["start_date", "end_date"],
    },

    # ── Wave 7D: late payers (receivables drilled to customer level) ───────
    {
        "name": "query_late_payers",
        "description": (
            "Top clienti morosi: aggrega sales_records non pagate con due_date < oggi, "
            "raggruppate per customer (customer_id o customer_name), ordinate per importo "
            "decrescente. Restituisce: nome cliente, totale scaduto, conteggio fatture, "
            "giorni di ritardo medio, fattura piu vecchia. Usa per 'chi devo sollecitare?', "
            "'top clienti morosi', 'aging clienti'."
        ),
        "parameters": {
            "min_overdue_days": {
                "type": "integer",
                "description": "Soglia minima di giorni di ritardo per includere il cliente (default 0 = qualsiasi ritardo).",
            },
            "limit": {
                "type": "integer",
                "description": "Numero massimo di clienti (default 10, max 50).",
            },
        },
        "required": [],
    },
]


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_org_currency(org_id: str) -> str:
    """Fetch the organization's configured currency (default EUR)."""
    try:
        from repositories import organization_repository
        org = await organization_repository.find_by_id(org_id)
        return (org.get("currency") if org else None) or "EUR"
    except Exception:
        return "EUR"


def _first_item(value) -> dict:
    """Normalise ``risk_focus`` / ``action_focus`` style payloads to a dict.

    Wave 14.HOTFIX — pre-fix, the smart_brief code assumed these fields
    were dicts (``risk_focus.get("primary")``) but ``build_ai_summary``
    actually returns them as ``List[dict]`` (see ``cashflow_summary.py:
    _build_risk_focus`` / ``_build_action_focus``). On rich-data orgs
    where the list is non-empty, the legacy ``.get()`` exploded with
    AttributeError, the surrounding ``try/except`` swallowed it into
    ``brief["cashflow"]["error"] = "..."``, and the chat AI silently
    hallucinated numbers to fill the void (observed 2026-05-16 in prod).

    Contract: accepts list[dict], dict, or None. Returns the canonical
    "first item" view — a dict ready for ``.get(...)`` access:

        []                 → {}
        None               → {}
        [{...}]            → first dict
        [{...a}, {...b}]   → first dict
        {"primary": {...}} → the dict (legacy dict shape, preserved
                              for backward compat)
        any other          → {} (defensive)
    """
    if value is None:
        return {}
    if isinstance(value, list):
        if not value:
            return {}
        head = value[0]
        return head if isinstance(head, dict) else {}
    if isinstance(value, dict):
        # Legacy dict shape ``{"primary": {...}}`` — flatten to the
        # inner dict so the caller can ``.get("description")`` uniformly.
        primary = value.get("primary")
        if isinstance(primary, dict):
            return primary
        return value
    return {}


# ── Wave 14.HOTFIX4 (F1) — direction-aware change interpretation ─────────────
#
# Pre-HOTFIX4 the period_comparison tool returned raw signed percentages
# (e.g. `revenue_pct: -2.9`) without a direction label. The 2026-05-16
# prod incident showed the AI reading those numbers and producing
# answers like "fatturato in calo del 2,9%" for a metric that had
# actually GROWN by +3% — because the model misinterpreted the sign
# convention.
#
# This helper produces a self-documenting label per metric:
#   - revenue: "crescita del +3,0%" / "calo del -2,5%"
#   - expenses/purchases/fixed_costs: "aumento" / "riduzione" (semantics
#     flipped — UP is bad for cost categories)
#   - net_result: special handling for negative-to-negative transitions
#     ("perdita ridotta del X%") and sign flips ("passato da perdita a
#     profitto")
#
# The AI reads `human_label` directly instead of deducing direction
# from sign, eliminating the entire class of sign-integrity violations.

def _interpret_change(
    metric: str,
    value_a: float,
    value_b: float,
    delta_pct: float,
    currency: str,
) -> dict:
    """Return a self-explanatory interpretation of the change from
    period_a to period_b for a single metric.

    Always populates:
        direction: "up" | "down" | "improvement" | "deterioration" | "stable"
        human_label: human-readable Italian description with the
                     concrete from/to values
        delta_pct_signed: the raw signed percentage (passthrough)
        delta_abs: absolute change (period_b - period_a)
    """
    delta_abs = round(value_b - value_a, 2)
    pct = round(delta_pct, 1)

    # ── net_result: special semantics for negative values ──────────────
    if metric == "net_result":
        if value_a < 0 and value_b < 0:
            # Both periods in loss
            if value_b > value_a:
                # Loss got smaller (closer to zero) — improvement
                magnitude_pct = round(
                    abs((value_b - value_a) / value_a) * 100, 1
                ) if value_a != 0 else 0
                return {
                    "direction": "improvement",
                    "human_label": (
                        f"net_result: PERDITA RIDOTTA del {magnitude_pct}% "
                        f"(da {value_a:.2f} {currency} a {value_b:.2f} {currency} — "
                        f"entrambi negativi, ma la perdita è diminuita)"
                    ),
                    "delta_pct_signed": pct,
                    "delta_abs": delta_abs,
                }
            elif value_b < value_a:
                # Loss got bigger — deterioration
                magnitude_pct = round(
                    abs((value_b - value_a) / value_a) * 100, 1
                ) if value_a != 0 else 0
                return {
                    "direction": "deterioration",
                    "human_label": (
                        f"net_result: PERDITA AUMENTATA del {magnitude_pct}% "
                        f"(da {value_a:.2f} {currency} a {value_b:.2f} {currency} — "
                        f"entrambi negativi, la perdita è peggiorata)"
                    ),
                    "delta_pct_signed": pct,
                    "delta_abs": delta_abs,
                }
            else:
                return {
                    "direction": "stable",
                    "human_label": f"net_result: perdita stabile a {value_a:.2f} {currency}",
                    "delta_pct_signed": pct,
                    "delta_abs": delta_abs,
                }
        elif value_a < 0 and value_b >= 0:
            return {
                "direction": "improvement",
                "human_label": (
                    f"net_result: PASSATO DA PERDITA A PROFITTO "
                    f"(da {value_a:.2f} {currency} a +{value_b:.2f} {currency}) "
                    f"— miglioramento drastico"
                ),
                "delta_pct_signed": pct,
                "delta_abs": delta_abs,
            }
        elif value_a >= 0 and value_b < 0:
            return {
                "direction": "deterioration",
                "human_label": (
                    f"net_result: PASSATO DA PROFITTO A PERDITA "
                    f"(da +{value_a:.2f} {currency} a {value_b:.2f} {currency}) "
                    f"— peggioramento drastico"
                ),
                "delta_pct_signed": pct,
                "delta_abs": delta_abs,
            }
        else:
            # Both non-negative
            if abs(pct) < 0.5:
                return {
                    "direction": "stable",
                    "human_label": (
                        f"net_result: stabile (variazione < 0,5%, "
                        f"da +{value_a:.2f} a +{value_b:.2f} {currency})"
                    ),
                    "delta_pct_signed": pct,
                    "delta_abs": delta_abs,
                }
            verb = "CRESCIUTO" if pct > 0 else "RIDOTTO"
            direction = "improvement" if pct > 0 else "deterioration"
            return {
                "direction": direction,
                "human_label": (
                    f"net_result: {verb} del {abs(pct)}% "
                    f"(da +{value_a:.2f} {currency} a +{value_b:.2f} {currency}) "
                    f"— entrambi positivi"
                ),
                "delta_pct_signed": pct,
                "delta_abs": delta_abs,
            }

    # ── revenue: UP is good (growth), DOWN is bad (decline) ────────────
    if metric == "revenue":
        if abs(pct) < 0.5:
            return {
                "direction": "stable",
                "human_label": (
                    f"revenue: stabile (variazione < 0,5%, "
                    f"da {value_a:.2f} a {value_b:.2f} {currency})"
                ),
                "delta_pct_signed": pct,
                "delta_abs": delta_abs,
            }
        if pct > 0:
            return {
                "direction": "up",
                "human_label": (
                    f"revenue: CRESCITA del +{pct}% "
                    f"(da {value_a:.2f} a {value_b:.2f} {currency}, "
                    f"+{delta_abs:.2f} {currency})"
                ),
                "delta_pct_signed": pct,
                "delta_abs": delta_abs,
            }
        return {
            "direction": "down",
            "human_label": (
                f"revenue: CALO del {pct}% "
                f"(da {value_a:.2f} a {value_b:.2f} {currency}, "
                f"{delta_abs:.2f} {currency})"
            ),
            "delta_pct_signed": pct,
            "delta_abs": delta_abs,
        }

    # ── expenses/purchases/fixed_costs: UP is bad, DOWN is good ────────
    if metric in ("expenses", "purchases", "fixed_costs"):
        if abs(pct) < 0.5:
            return {
                "direction": "stable",
                "human_label": (
                    f"{metric}: stabile (variazione < 0,5%, "
                    f"da {value_a:.2f} a {value_b:.2f} {currency})"
                ),
                "delta_pct_signed": pct,
                "delta_abs": delta_abs,
            }
        if pct > 0:
            return {
                "direction": "up",
                "human_label": (
                    f"{metric}: AUMENTO del +{pct}% "
                    f"(da {value_a:.2f} a {value_b:.2f} {currency}, "
                    f"+{delta_abs:.2f} {currency} — costo cresciuto)"
                ),
                "delta_pct_signed": pct,
                "delta_abs": delta_abs,
            }
        return {
            "direction": "down",
            "human_label": (
                f"{metric}: RIDUZIONE del {pct}% "
                f"(da {value_a:.2f} a {value_b:.2f} {currency}, "
                f"{delta_abs:.2f} {currency} — costo diminuito, miglioramento)"
            ),
            "delta_pct_signed": pct,
            "delta_abs": delta_abs,
        }

    # Default
    direction = "up" if pct > 0 else "down" if pct < 0 else "stable"
    return {
        "direction": direction,
        "human_label": (
            f"{metric}: {pct:+}% "
            f"(da {value_a:.2f} a {value_b:.2f} {currency})"
        ),
        "delta_pct_signed": pct,
        "delta_abs": delta_abs,
    }


# ── Tool execution dispatch ──────────────────────────────────────────────────

async def execute_tool(org_id: str, tool_name: str, tool_input: dict) -> dict:
    """Execute a cashflow AI tool and return the result as a JSON-serializable dict.

    All handlers delegate to existing analytics_repository functions.
    Returns {"error": "..."} if the tool is unknown or execution fails.
    """
    from repositories.analytics_repository import (
        aggregate_sales_by_date,
        aggregate_sales_by_category,
        aggregate_expenses_by_date,
        aggregate_expenses_by_category,
        aggregate_purchases_by_date,
        aggregate_purchases_by_supplier,
        aggregate_purchases_by_product,
        aggregate_purchases_by_category_macro,
        aggregate_fixed_costs_total,
        aggregate_fixed_costs_by_category,
        aggregate_open_receivables,
        aggregate_open_payables,
        aggregate_receivables_by_aging,
        aggregate_payables_by_aging,
        aggregate_upcoming_receivables,
        aggregate_upcoming_payables,
        get_date_range,
    )

    logger.info("cashflow ai_tools: executing %s with input %s", tool_name, tool_input)

    currency = await _get_org_currency(org_id)

    # Wave 1.5 (B10): locale is injected into tool_input by chat_service's
    # on_tool_call wrapper. We honour it here so summary builders return
    # locale-aware content. Fallback "it" preserves behaviour when the
    # tool is invoked outside chat (e.g. tests, direct API).
    locale = tool_input.get("locale", "it")

    # Wave 14.1 — envelope migration helper imported lazily at the
    # dispatcher boundary so individual tool branches can wrap their
    # return values uniformly without per-branch boilerplate.
    from core.tool_envelope import attach_envelope_metadata

    try:
        if tool_name == "query_business_summary":
            from services.business_summary import build_unified_summary
            sd = tool_input.get("start_date")
            ed = tool_input.get("end_date")
            bs_period = "custom" if (sd and ed) else tool_input.get("period", "30d")
            _bs_result = await build_unified_summary(
                org_id, period=bs_period, start_date=sd, end_date=ed, locale=locale,
            )
            # Wave 14.1 — wrap the cross-module summary response with
            # envelope metadata. Business fields stay at the top level
            # (downstream consumers and the AI prompt have been reading
            # them there for waves); we only ADD has_data/_temporal_scope/
            # _data_integrity/_source so the response now satisfies the
            # canonical envelope contract.
            return attach_envelope_metadata(
                _bs_result if isinstance(_bs_result, dict) else {"error": "no result"},
                tool="query_business_summary",
                temporal_scope="period_filtered",
            )

        elif tool_name == "query_cashflow_summary":
            from modules.cashflow_monitor.cashflow_summary import build_ai_summary
            sd = tool_input.get("start_date")
            ed = tool_input.get("end_date")
            period = "custom" if (sd and ed) else tool_input.get("period", "30d")
            _cs_result = await build_ai_summary(
                org_id, period=period, start_date=sd, end_date=ed, locale=locale,
            )
            return attach_envelope_metadata(
                _cs_result if isinstance(_cs_result, dict) else {"error": "no result"},
                tool="query_cashflow_summary",
                temporal_scope="period_filtered",
            )

        elif tool_name == "query_revenue":
            start = tool_input["start_date"]
            end = tool_input["end_date"]
            by_date = await aggregate_sales_by_date(org_id, start, end)
            by_category = await aggregate_sales_by_category(org_id, start, end)
            total = round(sum(by_date.values()), 2)
            has_data = len(by_date) > 0 or len(by_category) > 0
            return attach_envelope_metadata({
                "total": total,
                "has_data": has_data,
                "currency": currency,
                "period": {"start_date": start, "end_date": end},
                "by_date": by_date,
                "by_category": [
                    {"category": c["_id"], "total": round(c["total"], 2), "count": c["count"]}
                    for c in by_category
                ],
                "_caveat": None if has_data else "Nessun dato ricavi nel periodo. Il totale zero potrebbe indicare che i dati non sono ancora stati caricati.",
            }, tool="query_revenue", temporal_scope="period_filtered")

        elif tool_name == "query_expenses":
            start = tool_input["start_date"]
            end = tool_input["end_date"]
            by_date = await aggregate_expenses_by_date(org_id, start, end)
            by_category = await aggregate_expenses_by_category(org_id, start, end)
            total = round(sum(by_date.values()), 2)
            has_data = len(by_date) > 0 or len(by_category) > 0
            return {
                "total": total,
                "has_data": has_data,
                "currency": currency,
                "period": {"start_date": start, "end_date": end},
                "by_date": by_date,
                "by_category": [
                    {"category": c["_id"], "total": round(c["total"], 2), "count": c["count"]}
                    for c in by_category
                ],
                "_caveat": None if has_data else "Nessun dato spese nel periodo. Il totale zero potrebbe indicare che i dati non sono ancora stati caricati.",
            }

        elif tool_name == "query_purchases":
            start = tool_input["start_date"]
            end = tool_input["end_date"]
            group_by = tool_input.get("group_by", "supplier")
            by_date = await aggregate_purchases_by_date(org_id, start, end)
            total = round(sum(by_date.values()), 2)

            # Grouping by the requested dimension
            distribution = []
            distribution_label = "by_supplier"
            if group_by == "product":
                raw = await aggregate_purchases_by_product(org_id, start, end)
                distribution = [{"name": p["_id"], "total": round(p["total"], 2), "count": p["count"]} for p in raw]
                distribution_label = "by_product"
            elif group_by == "category":
                raw = await aggregate_purchases_by_category_macro(org_id, start, end)
                distribution = [{"name": c["_id"], "total": round(c["total"], 2), "count": c["count"]} for c in raw]
                distribution_label = "by_category"
            else:
                raw = await aggregate_purchases_by_supplier(org_id, start, end)
                distribution = [{"name": s["_id"], "total": round(s["total"], 2), "count": s["count"]} for s in raw]

            has_data = len(by_date) > 0 or len(distribution) > 0
            return {
                "total": total,
                "has_data": has_data,
                "currency": currency,
                "period": {"start_date": start, "end_date": end},
                "group_by": group_by,
                "by_date": by_date,
                distribution_label: distribution,
                "_caveat": None if has_data else "Nessun dato acquisti nel periodo. Il totale zero potrebbe indicare che i dati non sono ancora stati caricati.",
            }

        elif tool_name == "query_fixed_costs":
            start = tool_input["start_date"]
            end = tool_input["end_date"]
            total = await aggregate_fixed_costs_total(org_id, start, end)
            by_category = await aggregate_fixed_costs_by_category(org_id, start, end)
            has_data = total > 0 or len(by_category) > 0
            return {
                "total": total,
                "has_data": has_data,
                "currency": currency,
                "period": {"start_date": start, "end_date": end},
                "by_category": [
                    {"category": c["_id"], "total": c["total"], "count": c["count"]}
                    for c in by_category
                ],
                "_caveat": None if has_data else "Nessun costo fisso configurato. Il totale zero potrebbe indicare che i costi fissi non sono ancora stati inseriti.",
            }

        elif tool_name == "query_fixed_costs_detail":
            # Wave 14.HOTFIX4 (F2) — per-cost-item detail with accurate
            # proration honouring start_date / end_date.
            from repositories.analytics_repository import (
                aggregate_fixed_costs_detail,
            )
            start = tool_input["start_date"]
            end = tool_input["end_date"]
            items = await aggregate_fixed_costs_detail(org_id, start, end)
            total = round(sum(it["prorated_contribution"] for it in items), 2)
            terminated_count = sum(1 for it in items if it["terminated_in_period"])
            has_data = len(items) > 0
            return {
                "has_data": has_data,
                "currency": currency,
                "period": {"start_date": start, "end_date": end},
                "items": items,
                "summary": {
                    "active_count": len(items),
                    "terminated_in_period_count": terminated_count,
                    "total_prorated": total,
                },
                "_caveat": (
                    None if has_data else
                    "Nessun costo fisso attivo nel periodo. Se ne hai "
                    "configurati, verifica le date di start/end."
                ),
                "_temporal_scope": "period_filtered",
                "_data_integrity": {"status": "ok"} if has_data else {
                    "status": "warning",
                    "message": "No active fixed_costs in window.",
                },
                "_source": "analytics_repository.aggregate_fixed_costs_detail",
            }

        elif tool_name == "query_health_score_breakdown":
            # Wave 14.HOTFIX4 (F3) — standalone tool for explaining the
            # health score. Returns the 5-dimension breakdown that
            # compute_health_score produces. Pre-HOTFIX4 the breakdown
            # was only accessible by digging into the cashflow_summary
            # response; this exposes it as a first-class tool so the AI
            # can answer "perché il mio score è X?" with a single call.
            from .cashflow_summary import build_ai_summary
            start = tool_input.get("start_date")
            end = tool_input.get("end_date")
            period_token = tool_input.get("period", "30d")
            summary = await build_ai_summary(
                org_id, period=period_token,
                start_date=start, end_date=end,
                locale=tool_input.get("locale", "it"),
            )
            health = (summary or {}).get("health_score") or {}
            if not health or health.get("score") is None:
                return {
                    "has_data": False,
                    "_caveat": "Health score non calcolabile per il periodo.",
                    "_temporal_scope": "period_filtered",
                    "_data_integrity": {
                        "status": "warning",
                        "message": "Health score not computable.",
                    },
                    "_source": "compute_health_score",
                }
            return {
                "has_data": True,
                "currency": currency,
                "period": (summary or {}).get("period", {}),
                "score": health.get("score"),
                "label": health.get("label"),
                "color": health.get("color"),
                "explanation": health.get("explanation"),
                "breakdown": health.get("breakdown", []),
                "_convention_note": (
                    "Ogni voce di 'breakdown' ha: dimension (label IT), "
                    "key (machine name), points (punti effettivi), max "
                    "(punti massimi rescaled), raw_value (valore della "
                    "metrica componente), raw_unit (unità di misura), "
                    "status ('active'/'not_computable'/'disabled'). "
                    "Il punteggio finale = somma dei points delle "
                    "dimensions 'active'. Spiegare lo score significa "
                    "elencare quali dimensioni hanno contribuito di più "
                    "(points/max alto) e quali poco (points basso)."
                ),
                "_temporal_scope": "period_filtered",
                "_data_integrity": {"status": "ok"},
                "_source": "compute_health_score",
            }

        elif tool_name == "query_cashflow":
            start = tool_input["start_date"]
            end = tool_input["end_date"]
            # Canonical 4-bucket computation — matches overview_builder exactly
            sales_by_date = await aggregate_sales_by_date(org_id, start, end)
            expenses_by_date = await aggregate_expenses_by_date(org_id, start, end)
            purchases_by_date_d = await aggregate_purchases_by_date(org_id, start, end)
            from datetime import datetime as _dt, timedelta as _td
            start_dt = _dt.strptime(start, "%Y-%m-%d").date()
            end_dt = _dt.strptime(end, "%Y-%m-%d").date()
            p_days = (end_dt - start_dt).days + 1
            fc_total = await aggregate_fixed_costs_total(org_id, start, end)
            daily_fixed = round(fc_total / p_days, 2) if p_days > 0 else 0.0

            total_sales = round(sum(sales_by_date.values()), 2)
            total_expenses = round(sum(expenses_by_date.values()), 2)
            total_purchases = round(sum(purchases_by_date_d.values()), 2)
            total_outflows = round(total_expenses + total_purchases + fc_total, 2)
            net_after_fixed = round(total_sales - total_outflows, 2)
            outflow_ratio = round((total_outflows / total_sales * 100) if total_sales > 0 else 0.0, 1)
            op_margin_pct = round(((total_sales - total_expenses - total_purchases) / total_sales * 100) if total_sales > 0 else 0.0, 1)

            # Build canonical daily series (4-bucket net)
            all_dates = sorted(set(sales_by_date) | set(expenses_by_date) | set(purchases_by_date_d))
            running = 0.0
            series = []
            for d in all_dates:
                s = round(sales_by_date.get(d, 0), 2)
                e = round(expenses_by_date.get(d, 0), 2)
                p = round(purchases_by_date_d.get(d, 0), 2)
                net_d = round(s - e - p - daily_fixed, 2)
                running = round(running + net_d, 2)
                series.append({"date": d, "sales": s, "expenses": e, "purchases": p, "fixed_daily": daily_fixed, "net": net_d, "cumulative": running})

            has_data = len(all_dates) > 0
            return {
                "period": {"start_date": start, "end_date": end, "days": p_days},
                "currency": currency,
                "has_data": has_data,
                "summary": {
                    "total_sales": total_sales,
                    "total_expenses": total_expenses,
                    "supplier_purchases": total_purchases,
                    "fixed_costs_total": fc_total,
                    "total_outflows": total_outflows,
                    "net_after_fixed": net_after_fixed,
                    "total_outflow_ratio_pct": outflow_ratio,
                    "operating_margin_pct": op_margin_pct,
                },
                "daily_series": series,
                "_caveat": None if has_data else "Nessun dato finanziario nel periodo. Tutti i totali a zero potrebbero indicare dati non ancora caricati.",
            }

        elif tool_name == "query_receivables_payables":
            open_recv = await aggregate_open_receivables(org_id)
            open_pay = await aggregate_open_payables(org_id)
            recv_aging = await aggregate_receivables_by_aging(org_id)
            pay_aging = await aggregate_payables_by_aging(org_id)
            upcoming_recv = await aggregate_upcoming_receivables(org_id)
            upcoming_pay = await aggregate_upcoming_payables(org_id)
            has_data = (open_recv > 0 or open_pay > 0
                        or len(recv_aging) > 0 or len(pay_aging) > 0)
            return {
                "currency": currency,
                "has_data": has_data,
                "receivables": {
                    "total_open": open_recv,
                    "aging": recv_aging,
                    "upcoming_60_days": upcoming_recv,
                },
                "payables": {
                    "total_open": open_pay,
                    "aging": pay_aging,
                    "upcoming_60_days": upcoming_pay,
                },
                "_caveat": (
                    "Nessun credito o debito aperto trovato. Potrebbe indicare che i campi "
                    "payment_status e due_date non sono stati compilati nei dati importati."
                ) if not has_data else None,
            }

        elif tool_name == "get_data_range":
            data_range = await get_date_range(org_id)
            return data_range

        # Wave 7B.1: query_order_pipeline, query_fulfillment_status,
        # query_payment_pipeline, query_event_metrics,
        # query_booking_utilization, query_rental_utilization moved to
        # modules.commerce.ai_tools.execute_tool.

        elif tool_name == "query_revenue_forecast":
            from datetime import date as _date_fc, timedelta as _td_fc
            import statistics as _stats

            horizon = min(int(tool_input.get("horizon_days", 30)), 90)
            today = _date_fc.today()

            # Fetch last 90 days of sales data
            start_90 = (today - _td_fc(days=90)).isoformat()
            end_str = today.isoformat()
            sales_by_date = await aggregate_sales_by_date(org_id, start_90, end_str)

            if len(sales_by_date) < 14:
                return {
                    "has_data": False,
                    "message": "Dati insufficienti per una proiezione (servono almeno 14 giorni di vendite).",
                    "epistemic": {
                        "epistemic_class": "insufficient_data",
                        "reliability": "none",
                        "ai_usability": "do_not_cite",
                    },
                }

            # Build daily series (fill zeros for missing days)
            daily = []
            for i in range(90):
                d = (today - _td_fc(days=89 - i)).isoformat()
                daily.append({"date": d, "amount": sales_by_date.get(d, 0)})

            amounts = [d["amount"] for d in daily]

            # Weighted moving average (recent days weighted more)
            # Last 30 days get weight 3, 31-60 get weight 2, 61-90 get weight 1
            weighted_sum = 0
            weight_total = 0
            for i, amt in enumerate(amounts):
                if i >= 60:
                    w = 3
                elif i >= 30:
                    w = 2
                else:
                    w = 1
                weighted_sum += amt * w
                weight_total += w
            avg_daily = weighted_sum / weight_total if weight_total > 0 else 0

            # Weekday pattern
            weekday_totals = {i: 0.0 for i in range(7)}
            weekday_counts = {i: 0 for i in range(7)}
            for d in daily:
                dt = _date_fc.fromisoformat(d["date"])
                wd = dt.weekday()
                weekday_totals[wd] += d["amount"]
                weekday_counts[wd] += 1

            weekday_avg = {}
            for wd in range(7):
                if weekday_counts[wd] > 0:
                    weekday_avg[wd] = weekday_totals[wd] / weekday_counts[wd]
                else:
                    weekday_avg[wd] = avg_daily

            overall_avg = sum(weekday_avg.values()) / 7 if weekday_avg else avg_daily
            weekday_factors = {}
            day_names = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
            for wd in range(7):
                factor = weekday_avg[wd] / overall_avg if overall_avg > 0 else 1.0
                weekday_factors[day_names[wd]] = round(factor, 2)

            # Forecast
            forecast_total = 0
            for i in range(1, horizon + 1):
                future_date = today + _td_fc(days=i)
                wd = future_date.weekday()
                factor = weekday_avg.get(wd, avg_daily) / overall_avg if overall_avg > 0 else 1.0
                forecast_total += avg_daily * factor
            forecast_total = round(forecast_total, 2)

            # Trend direction
            last_30_avg = sum(amounts[-30:]) / 30 if len(amounts) >= 30 else avg_daily
            prev_30_avg = sum(amounts[-60:-30]) / 30 if len(amounts) >= 60 else avg_daily
            if prev_30_avg > 0:
                growth_rate = round((last_30_avg - prev_30_avg) / prev_30_avg * 100, 1)
            else:
                growth_rate = 0

            if growth_rate > 5:
                direction = "growing"
            elif growth_rate < -5:
                direction = "declining"
            else:
                direction = "stable"

            # Confidence based on data consistency
            if len(sales_by_date) >= 60:
                cv = _stats.stdev(amounts[-30:]) / last_30_avg if last_30_avg > 0 else 1
                confidence = "alto" if cv < 0.3 else "medio" if cv < 0.6 else "basso"
            else:
                confidence = "basso"

            return {
                "has_data": True,
                "currency": currency,
                "forecast": {
                    "horizon_days": horizon,
                    "estimated_revenue": forecast_total,
                    "avg_daily_projected": round(avg_daily, 2),
                    "confidence": confidence,
                },
                "basis": {
                    "data_days_used": len(sales_by_date),
                    "avg_daily_90d": round(sum(amounts) / 90, 2),
                    "avg_daily_30d": round(last_30_avg, 2),
                    "trend_direction": direction,
                    "growth_rate_monthly_pct": growth_rate,
                },
                "weekday_pattern": weekday_factors,
                "epistemic": {
                    "epistemic_class": "estimated",
                    "reliability": "low" if confidence == "basso" else "medium",
                    "temporal_scope": "forecast",
                    "ai_usability": "qualify_always",
                    "caveat": (
                        "Proiezione basata su media mobile ponderata degli ultimi 90 giorni. "
                        "Non considera eventi straordinari, stagionalita annuale, o cambiamenti di mercato. "
                        "Usare come indicazione direzionale, non come previsione precisa."
                    ),
                },
            }

        elif tool_name == "query_anomaly_detection":
            from datetime import date as _date_ad, timedelta as _td_ad
            import statistics as _stats_ad

            start = tool_input["start_date"]
            end = tool_input["end_date"]

            # Fetch data with 14-day pre-buffer for moving average calculation
            buffer_start = (_date_ad.fromisoformat(start) - _td_ad(days=14)).isoformat()
            sales = await aggregate_sales_by_date(org_id, buffer_start, end)
            expenses = await aggregate_expenses_by_date(org_id, buffer_start, end)

            if len(sales) < 14:
                return {
                    "has_data": False,
                    "message": "Dati insufficienti per la detection anomalie (servono almeno 14 giorni).",
                    "epistemic": {"epistemic_class": "insufficient_data"},
                }

            # Build daily series
            all_dates = sorted(set(list(sales.keys()) + list(expenses.keys())))
            # Filter to only requested period for anomaly output
            requested_dates = [d for d in all_dates if start <= d <= end]

            def _detect_anomalies(by_date: dict, label: str):
                anomalies = []
                dates_sorted = sorted(by_date.keys())
                for target_date in requested_dates:
                    if target_date not in dates_sorted:
                        continue
                    idx = dates_sorted.index(target_date)
                    if idx < 14:
                        continue
                    # 14-day moving average and std dev
                    window = [by_date.get(dates_sorted[j], 0) for j in range(idx - 14, idx)]
                    if not window:
                        continue
                    avg = _stats_ad.mean(window)
                    std = _stats_ad.stdev(window) if len(window) > 1 else 0
                    if std == 0:
                        continue
                    value = by_date.get(target_date, 0)
                    deviation = (value - avg) / std
                    if abs(deviation) >= 2.0:
                        anomalies.append({
                            "date": target_date,
                            "value": round(value, 2),
                            "expected_avg": round(avg, 2),
                            "expected_range": [round(avg - 2 * std, 2), round(avg + 2 * std, 2)],
                            "deviation_sigma": round(deviation, 1),
                            "direction": "spike" if deviation > 0 else "drop",
                            "type": label,
                        })
                return anomalies

            revenue_anomalies = _detect_anomalies(sales, "revenue")
            expense_anomalies = _detect_anomalies(expenses, "expenses")
            all_anomalies = sorted(revenue_anomalies + expense_anomalies, key=lambda a: a["date"])

            return {
                "has_data": True,
                "currency": currency,
                "period": {"start_date": start, "end_date": end},
                "anomalies": all_anomalies,
                "anomaly_count": len(all_anomalies),
                "revenue_anomalies": len(revenue_anomalies),
                "expense_anomalies": len(expense_anomalies),
                "interpretation_hint": (
                    "Un'anomalia indica un valore oltre 2 deviazioni standard dalla media mobile a 14 giorni. "
                    "Puo essere un evento reale (promozione, fattura grossa) o un errore di inserimento dati. "
                    "Verificare con l'utente il contesto di ogni anomalia."
                ),
                "epistemic": {
                    "epistemic_class": "derived",
                    "reliability": "medium",
                    "temporal_scope": "period",
                    "ai_usability": "qualify_with_context",
                    "caveat": "Anomalie statistiche, non necessariamente problemi. Ogni anomalia va contestualizzata.",
                },
            }

        elif tool_name == "query_data_quality_audit":
            from database import (
                customers_collection, products_collection,
                sales_records_collection as _sr_coll,
            )
            from services.module_access import get_module_entitlements as _gme_dq

            audit = {"currency": currency}
            recommendations = []

            # Determine active modules
            _active = set()
            for _mk in ["cashflow_monitor", "customers_light", "product_catalog"]:
                try:
                    _ent = await _gme_dq(org_id, _mk)
                    if _ent.get("enabled"):
                        _active.add(_mk)
                except Exception:
                    pass

            # ── Financial data quality ──
            try:
                from repositories.analytics_repository import count_sales_with_customer_id
                cov = await count_sales_with_customer_id(org_id)
                total_sr = cov.get("total", 0)
                with_cid = cov.get("with_customer_id", 0)
                cov_pct = round(with_cid / total_sr * 100) if total_sr > 0 else 0

                # Records without category
                no_cat = await _sr_coll.count_documents(
                    {"organization_id": org_id, "$or": [{"category": None}, {"category": ""}]})

                # Data range
                from repositories.analytics_repository import get_date_range
                dr = await get_date_range(org_id)

                audit["financial"] = {
                    "total_records": total_sr,
                    "customer_id_coverage_pct": cov_pct,
                    "records_without_category": no_cat,
                    "data_range": dr if dr else {"min_date": None, "max_date": None},
                }
                if cov_pct < 30 and total_sr > 50:
                    recommendations.append(
                        f"Copertura customer_id molto bassa ({cov_pct}%) — importare vendite "
                        "con la colonna 'cliente' per abilitare analisi clienti affidabili"
                    )
                if no_cat > total_sr * 0.2 and total_sr > 20:
                    recommendations.append(
                        f"{no_cat} record finanziari senza categoria — assegnare categorie "
                        "per analisi spese/ricavi più accurate"
                    )
            except Exception as e:
                audit["financial"] = {"error": str(e)[:100]}

            # ── Customer data quality (if module active) ──
            if "customers_light" in _active:
                try:
                    total_cust = await customers_collection.count_documents({"organization_id": org_id})
                    missing_email = await customers_collection.count_documents(
                        {"organization_id": org_id, "$or": [{"email": None}, {"email": ""}]})
                    no_transactions = await customers_collection.count_documents(
                        {"organization_id": org_id, "total_revenue": {"$in": [None, 0]}})

                    # Duplicate candidates: group by lowercase name, count > 1
                    dup_pipeline = [
                        {"$match": {"organization_id": org_id, "name": {"$ne": None}}},
                        {"$group": {
                            "_id": {"$toLower": "$name"},
                            "count": {"$sum": 1},
                        }},
                        {"$match": {"count": {"$gt": 1}}},
                        {"$count": "duplicates"},
                    ]
                    dup_result = await customers_collection.aggregate(dup_pipeline).to_list(1)
                    dup_count = dup_result[0]["duplicates"] if dup_result else 0

                    audit["customers"] = {
                        "total": total_cust,
                        "missing_email": missing_email,
                        "no_transactions": no_transactions,
                        "duplicate_candidates": dup_count,
                    }
                    if dup_count > 0:
                        recommendations.append(
                            f"{dup_count} possibili clienti duplicati — verificare e unificare"
                        )
                    if missing_email > total_cust * 0.3 and total_cust > 10:
                        recommendations.append(
                            f"{missing_email} clienti senza email — aggiungere per comunicazioni"
                        )
                except Exception as e:
                    audit["customers"] = {"error": str(e)[:100]}

            # ── Product data quality (if module active) ──
            if "product_catalog" in _active:
                try:
                    total_prod = await products_collection.count_documents(
                        {"organization_id": org_id, "is_active": True})
                    no_cost = await products_collection.count_documents(
                        {"organization_id": org_id, "is_active": True,
                         "$or": [{"cost_price": None}, {"cost_price": 0}]})
                    no_category = await products_collection.count_documents(
                        {"organization_id": org_id, "is_active": True,
                         "$or": [{"category": None}, {"category": ""}]})
                    zero_stock_published = await products_collection.count_documents(
                        {"organization_id": org_id, "is_active": True, "is_published": True,
                         "stock_quantity": {"$lte": 0}, "item_type": "physical"})

                    audit["products"] = {
                        "total": total_prod,
                        "no_cost_price": no_cost,
                        "no_cost_pct": round(no_cost / total_prod * 100) if total_prod > 0 else 0,
                        "no_category": no_category,
                        "zero_stock_published": zero_stock_published,
                    }
                    if no_cost > total_prod * 0.3 and total_prod > 5:
                        recommendations.append(
                            f"{no_cost} prodotti senza costo ({audit['products']['no_cost_pct']}%) — "
                            "aggiungere costo per calcolo margini completi"
                        )
                    if zero_stock_published > 0:
                        recommendations.append(
                            f"{zero_stock_published} prodotti pubblicati con stock esaurito — "
                            "aggiornare stock o togliere dalla vetrina"
                        )
                except Exception as e:
                    audit["products"] = {"error": str(e)[:100]}

            # ── Overall score ──
            issues = 0
            fin = audit.get("financial", {})
            if fin.get("customer_id_coverage_pct", 100) < 40:
                issues += 2
            if fin.get("records_without_category", 0) > 10:
                issues += 1
            cust = audit.get("customers", {})
            if cust.get("duplicate_candidates", 0) > 0:
                issues += 1
            prod = audit.get("products", {})
            if prod.get("no_cost_pct", 0) > 50:
                issues += 2
            if prod.get("zero_stock_published", 0) > 0:
                issues += 1

            if issues >= 4:
                audit["overall_score"] = "critico"
            elif issues >= 2:
                audit["overall_score"] = "discreto"
            else:
                audit["overall_score"] = "buono"

            audit["recommendations"] = recommendations
            audit["epistemic"] = {
                "epistemic_class": "factual",
                "reliability": "high",
                "temporal_scope": "current_state",
                "ai_usability": "cite_directly",
            }

            return audit

        elif tool_name == "query_smart_brief":
            import asyncio as _aio_sb
            from services.module_access import get_module_entitlements

            brief = {"modules_active": []}

            # Wave 13.5 — resolve the user's period instead of the pre-fix
            # hardcoded 30d. The dispatcher auto-injects start_date/end_date
            # from period_context (see chat_service.on_tool_call), so by
            # the time this branch runs ``tool_input`` already carries the
            # user's active window when there is one.
            #
            # Resolution priority mirrors query_cashflow_summary at line 382:
            #   - both dates → label "custom" (dates win in build_ai_summary)
            #   - period token alone → token wins
            #   - nothing → fall back to 30d AND tell the caller (top-level
            #     ``period_used`` field) so the model never confuses a default
            #     snapshot with the user's filter.
            _brief_sd = tool_input.get("start_date")
            _brief_ed = tool_input.get("end_date")
            _brief_period_in = tool_input.get("period")
            if _brief_sd and _brief_ed:
                _brief_period = _brief_period_in or "custom"
            else:
                _brief_period = _brief_period_in or "30d"

            # Surface the period so downstream consumers (frontend tag,
            # log analysis, eval harness) can tell which window each
            # brief was computed on.
            brief["period_used"] = {
                "label": _brief_period,
                "start_date": _brief_sd,
                "end_date": _brief_ed,
            }

            # Determine active modules for this org
            _module_keys = ["cashflow_monitor", "customers_light", "product_catalog"]
            for mk in _module_keys:
                try:
                    ent = await get_module_entitlements(org_id, mk)
                    if ent.get("enabled"):
                        brief["modules_active"].append(mk)
                except Exception:
                    pass

            # ── Cashflow section (always present) ──
            try:
                from modules.cashflow_monitor.cashflow_summary import build_ai_summary
                cs = await build_ai_summary(
                    org_id,
                    period=_brief_period,
                    start_date=_brief_sd,
                    end_date=_brief_ed,
                    locale=locale,
                )
                pnl = cs.get("pnl", {}) or {}
                status = cs.get("status", {}) or {}
                # Wave 14.HOTFIX — ``risk_focus`` and ``action_focus`` are
                # LISTS in ``build_ai_summary`` output (see
                # cashflow_summary.py:_build_risk_focus + _build_action_focus,
                # both return List[dict]). The pre-fix code treated them as
                # dicts and exploded with AttributeError when a non-empty
                # list was returned — visible only with rich-data orgs.
                # Bug observed in prod on 2026-05-16: a YTD chat returned
                # cashflow.error and the AI hallucinated numbers to fill
                # the void. We now normalise to "first item or empty dict"
                # AND accept both shapes for forward compat.
                risk_focus_raw = cs.get("risk_focus")
                action_focus_raw = cs.get("action_focus")
                risk_first = _first_item(risk_focus_raw)
                action_first = _first_item(action_focus_raw)

                brief["cashflow"] = {
                    "health_score": (cs.get("health_score") or {}).get("score"),
                    "health_level": status.get("level"),
                    "health_direction": (cs.get("period_comparison") or {}).get("direction", "stable"),
                    # Wave 13.5 — renamed from net_result_30d to net_result.
                    # The "_30d" suffix was misleading once the tool started
                    # honouring arbitrary periods. The actual window is in
                    # brief["period_used"] for unambiguous attribution.
                    "net_result": pnl.get("net_after_fixed"),
                    "margin_pct": pnl.get("operating_margin_pct"),
                    # Wave 14.HOTFIX — read from the normalised first-item
                    # form (handles list[dict] and dict shapes uniformly).
                    "key_risk": risk_first.get("description") or risk_first.get("summary"),
                    "key_positive": (cs.get("period_comparison") or {}).get("most_improved_bucket"),
                    "primary_action": action_first.get("description") or action_first.get("summary"),
                }
            except Exception as e:
                logger.warning(
                    "ai_tools.query_smart_brief: cashflow section failed for org=%s: %s",
                    org_id, e,
                )
                brief["cashflow"] = {
                    "error": str(e)[:100],
                    # Wave 14.HOTFIX — surface a HINT to the model so it
                    # does NOT silently synthesise. The model is instructed
                    # by Rule 20 (HARD STOP ON ERROR) to escalate, not
                    # invent numbers when this branch fires.
                    "_hint": (
                        "Cashflow section of smart_brief failed. Call "
                        "query_cashflow_summary directly with the same "
                        "period to retry. Do NOT estimate values."
                    ),
                }

            # ── Alerts ──
            try:
                # Wave 13.5 — same latent bug as in chat_service
                # _build_proactive_context: ``alert_repository.find_active``
                # has never existed; the try/except silently swallowed the
                # AttributeError, so the alerts section was effectively
                # always empty in every brief ever generated. Now use the
                # real function ``find_by_org`` and filter resolved alerts
                # in Python so the model finally sees active alerts.
                from repositories import alert_repository
                alerts_raw = await alert_repository.find_by_org(org_id, limit=50)
                alerts = [a for a in alerts_raw if a.get("status") != "resolved"]
                severity_counts = {"high": 0, "medium": 0, "low": 0}
                top_alert = None
                for a in alerts:
                    sev = a.get("severity", "low").lower()
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1
                    if top_alert is None and sev in ("high", "medium"):
                        top_alert = a.get("title", "")[:100]
                brief["alerts"] = {**severity_counts, "top_alert": top_alert}
            except Exception:
                brief["alerts"] = {"high": 0, "medium": 0, "low": 0}

            # ── Customers section (if module active) ──
            if "customers_light" in brief["modules_active"]:
                try:
                    from database import customer_metrics_collection
                    total = await customer_metrics_collection.count_documents({"organization_id": org_id})
                    active = await customer_metrics_collection.count_documents(
                        {"organization_id": org_id, "segment": {"$in": ["top", "active", "new"]}})
                    churn_high = await customer_metrics_collection.count_documents(
                        {"organization_id": org_id, "churn_risk_score": {"$gte": 60}})
                    # Top customer at risk
                    at_risk = await customer_metrics_collection.find_one(
                        {"organization_id": org_id, "churn_risk_score": {"$gte": 60}},
                        {"_id": 0, "customer_name": 1, "total_revenue": 1, "days_since_last_purchase": 1},
                        sort=[("total_revenue", -1)],
                    )
                    # Concentration
                    top5 = await customer_metrics_collection.find(
                        {"organization_id": org_id},
                        {"_id": 0, "revenue_share_pct": 1},
                    ).sort("total_revenue", -1).limit(5).to_list(5)
                    top5_share = round(sum(c.get("revenue_share_pct", 0) for c in top5), 1)

                    brief["customers"] = {
                        "total_customers": total,
                        "total_active": active,
                        "churn_risk_high": churn_high,
                        "top_customer_at_risk": {
                            "name": at_risk.get("customer_name"),
                            "ltv": at_risk.get("total_revenue"),
                            "days_inactive": at_risk.get("days_since_last_purchase"),
                        } if at_risk else None,
                        "concentration": {
                            "top5_share_pct": top5_share,
                            "risk_level": "alto" if top5_share > 60 else "medio" if top5_share > 40 else "basso",
                        },
                    }
                except Exception as e:
                    brief["customers"] = {"error": str(e)[:100]}

            # ── Products section (if module active) ──
            if "product_catalog" in brief["modules_active"]:
                try:
                    from database import product_metrics_collection
                    total = await product_metrics_collection.count_documents({"organization_id": org_id})
                    critical = await product_metrics_collection.count_documents(
                        {"organization_id": org_id, "margin_pct": {"$lt": 15, "$ne": None}})
                    declining = await product_metrics_collection.count_documents(
                        {"organization_id": org_id, "trend_30d_pct": {"$lt": -10}})
                    # Top star
                    star = await product_metrics_collection.find_one(
                        {"organization_id": org_id, "margin_pct": {"$gte": 30}, "trend_30d_pct": {"$gt": 0}},
                        {"_id": 0, "product_name": 1, "margin_pct": 1, "trend_30d_pct": 1},
                        sort=[("total_revenue", -1)],
                    )
                    brief["products"] = {
                        "total_active": total,
                        "critical_margin_count": critical,
                        "declining_count": declining,
                        "top_star": {
                            "name": star.get("product_name"),
                            "margin_pct": star.get("margin_pct"),
                            "trend": f"+{star.get('trend_30d_pct')}%",
                        } if star else None,
                    }
                except Exception as e:
                    brief["products"] = {"error": str(e)[:100]}

            # ── Commerce operations ──
            try:
                from database import orders_collection
                draft_count = await orders_collection.count_documents(
                    {"organization_id": org_id, "status": "draft"})
                if draft_count > 0 or True:  # always include commerce section
                    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
                    _7d_ago = (_dt.now(_tz.utc) - _td(days=7)).isoformat()
                    delayed = await orders_collection.count_documents({
                        "organization_id": org_id,
                        "status": "confirmed",
                        "fulfillment.status": "pending",
                        "created_at": {"$lt": _7d_ago},
                    })
                    # Payment at risk
                    pay_risk_cursor = orders_collection.aggregate([
                        {"$match": {
                            "organization_id": org_id,
                            "status": {"$in": ["confirmed", "completed"]},
                            "payment_status": {"$in": ["awaiting_payment", "pending"]},
                        }},
                        {"$group": {"_id": None, "count": {"$sum": 1}, "amount": {"$sum": "$subtotal"}}},
                    ])
                    pay_risk = await pay_risk_cursor.to_list(1)
                    pr = pay_risk[0] if pay_risk else {"count": 0, "amount": 0}

                    brief["commerce"] = {
                        "draft_orders_pending": draft_count,
                        "fulfillment_delayed": delayed,
                        "payment_at_risk": {"count": pr.get("count", 0), "amount": round(pr.get("amount", 0), 2)},
                    }
            except Exception as e:
                brief["commerce"] = {"error": str(e)[:100]}

            # ── Data quality summary ──
            try:
                from repositories.analytics_repository import count_sales_with_customer_id
                cov = await count_sales_with_customer_id(org_id)
                total_sr = cov.get("total", 0)
                with_cid = cov.get("with_customer_id", 0)
                cov_pct = round(with_cid / total_sr * 100) if total_sr > 0 else 0
                brief["data_quality"] = {
                    "customer_id_coverage_pct": cov_pct,
                    "overall": "buono" if cov_pct >= 70 else "discreto" if cov_pct >= 40 else "critico",
                }
            except Exception:
                brief["data_quality"] = {"overall": "non calcolabile"}

            # ── Action priorities (top 3) ──
            actions = []
            cf = brief.get("cashflow", {})
            if cf.get("key_risk"):
                actions.append(cf["key_risk"])
            comm = brief.get("commerce", {})
            if isinstance(comm, dict) and comm.get("draft_orders_pending", 0) > 3:
                actions.append(f"Evadere {comm['draft_orders_pending']} ordini in bozza")
            if isinstance(comm, dict) and comm.get("fulfillment_delayed", 0) > 0:
                actions.append(f"Gestire {comm['fulfillment_delayed']} ordini in ritardo di evasione")
            cust = brief.get("customers", {})
            if isinstance(cust, dict) and cust.get("top_customer_at_risk"):
                ar = cust["top_customer_at_risk"]
                if ar.get("name"):
                    actions.append(
                        f"Contattare {ar['name']} (LTV {ar.get('ltv', 0):,.0f} {currency}, "
                        f"inattivo {ar.get('days_inactive', '?')}gg) — rischio churn"
                    )
            brief["action_priorities"] = actions[:3]

            # Wave 14.1 — wrap with envelope metadata. ``has_data`` is
            # inferred from the presence of the cashflow section: if
            # cashflow failed (carries an "error" key), the brief is
            # effectively a degraded response and the AI is instructed
            # (Rule 20) to escalate rather than synthesise from the
            # other sections. We use integrity_status="warning" when
            # cashflow errored so the AI sees the signal explicitly.
            _cf = brief.get("cashflow") or {}
            _cf_failed = isinstance(_cf, dict) and "error" in _cf
            return attach_envelope_metadata(
                brief,
                tool="query_smart_brief",
                temporal_scope="period_filtered",
                integrity_status=("warning" if _cf_failed else "ok"),
                integrity_message=(
                    f"cashflow section failed: {_cf.get('error', 'unknown')[:120]}"
                    if _cf_failed else None
                ),
                has_data_default=not _cf_failed,
            )

        elif tool_name == "query_period_comparison":
            import asyncio as _aio

            pa_start = tool_input["period_a_start"]
            pa_end = tool_input["period_a_end"]
            pb_start = tool_input["period_b_start"]
            pb_end = tool_input["period_b_end"]

            # Fetch both periods in parallel
            async def _fetch_period(s, e):
                sales, expenses, purchases, fixed = await _aio.gather(
                    aggregate_sales_by_date(org_id, s, e),
                    aggregate_expenses_by_date(org_id, s, e),
                    aggregate_purchases_by_date(org_id, s, e),
                    aggregate_fixed_costs_total(org_id, s, e),
                )
                rev = round(sum(sales.values()), 2)
                exp = round(sum(expenses.values()), 2)
                pur = round(sum(purchases.values()), 2)
                fix = round(fixed, 2)
                net = round(rev - exp - pur - fix, 2)
                margin = round((net / rev * 100), 1) if rev > 0 else 0
                return {
                    "revenue": rev, "expenses": exp, "purchases": pur,
                    "fixed_costs": fix, "net_result": net, "margin_pct": margin,
                }

            period_a, period_b = await _aio.gather(
                _fetch_period(pa_start, pa_end),
                _fetch_period(pb_start, pb_end),
            )

            # ── Wave 14.HOTFIX5 — auto-canonicalize orientation ────────────
            # Pre-HOTFIX5 the convention was ambiguous: the user/model
            # could emit (period_a=2026, period_b=2025) OR (period_a=2025,
            # period_b=2026), and the delta formula `(b - a) / |a|`
            # produced OPPOSITE results for the same semantic question.
            #
            # The 2026-05-16 post-HOTFIX4 incident: model emitted
            # period_a=2026 (recent), period_b=2025 (reference). Tool
            # computed (2025 - 2026) / |2026| = -2.9% revenue.
            # _interpret_change saw value_a=2026.revenue, value_b=2025.revenue,
            # delta_pct=-2.9 → labelled "CALO" (correct given inputs),
            # but the AI read it as "revenue è in calo" which is WRONG
            # because 2026 is the CURRENT period and IT HAS GROWN.
            #
            # HOTFIX5 makes the tool ROBUST to either ordering: it
            # detects which period is older (baseline) vs newer (current)
            # by comparing start dates, and ALWAYS labels them
            # accordingly. The delta is then computed as
            # (current - baseline) / |baseline|, so:
            #
            #   positive delta = current grew over baseline (intuitive)
            #   negative delta = current declined vs baseline (intuitive)
            #
            # The response includes period_a / period_b unchanged for
            # backward compat, PLUS new period_baseline / period_current
            # fields that label the semantic role, PLUS
            # _period_orientation explaining the auto-detection.
            swapped = pa_start > pb_start
            if swapped:
                # period_a is newer than period_b → swap so A=baseline (older)
                period_baseline = period_b
                period_current = period_a
                baseline_dates = {"start": pb_start, "end": pb_end}
                current_dates = {"start": pa_start, "end": pa_end}
            else:
                period_baseline = period_a
                period_current = period_b
                baseline_dates = {"start": pa_start, "end": pa_end}
                current_dates = {"start": pb_start, "end": pb_end}

            # Wave 14.HOTFIX6 (F2) — delegate to the canonical formula
            # in core.delta_formulas so this tool and overview_builder's
            # YoY block agree on zero/negative-baseline edge cases.
            from core.delta_formulas import compute_period_delta

            delta = {}
            for key in ["revenue", "expenses", "purchases", "fixed_costs", "net_result"]:
                d = compute_period_delta(period_baseline[key], period_current[key])
                delta[f"{key}_pct"] = d["delta_pct"] if d["delta_pct"] is not None else 0
                delta[f"{key}_abs"] = d["delta_abs"]
            delta["margin_pp"] = round(period_current["margin_pct"] - period_baseline["margin_pct"], 1)

            # Determine overall direction
            net_delta = delta["net_result_pct"]
            if net_delta > 5:
                direction = "improvement"
            elif net_delta < -5:
                direction = "deterioration"
            else:
                direction = "stable"

            # Identify key driver (biggest absolute change)
            drivers = []
            if abs(delta["revenue_pct"]) > 5:
                d = "aumento" if delta["revenue_pct"] > 0 else "calo"
                drivers.append(f"Fatturato: {d} del {abs(delta['revenue_pct'])}%")
            if abs(delta["expenses_pct"]) > 5:
                d = "aumento" if delta["expenses_pct"] > 0 else "riduzione"
                drivers.append(f"Spese: {d} del {abs(delta['expenses_pct'])}%")
            if abs(delta["purchases_pct"]) > 5:
                d = "aumento" if delta["purchases_pct"] > 0 else "riduzione"
                drivers.append(f"Acquisti: {d} del {abs(delta['purchases_pct'])}%")

            # ── Wave 14.HOTFIX5 — interpretation uses baseline/current ─────
            # _interpret_change is now passed (baseline, current) instead
            # of raw (period_a, period_b). Combined with the auto-swap
            # above, this means delta_pct sign is ALWAYS intuitive:
            # positive = current grew over baseline. The "CRESCITA" /
            # "CALO" labels match the user's mental model regardless of
            # which period the model named "a" or "b" in the tool call.
            change_interp = {
                "revenue": _interpret_change(
                    "revenue", period_baseline["revenue"], period_current["revenue"],
                    delta["revenue_pct"], currency,
                ),
                "expenses": _interpret_change(
                    "expenses", period_baseline["expenses"], period_current["expenses"],
                    delta["expenses_pct"], currency,
                ),
                "purchases": _interpret_change(
                    "purchases", period_baseline["purchases"], period_current["purchases"],
                    delta["purchases_pct"], currency,
                ),
                "fixed_costs": _interpret_change(
                    "fixed_costs", period_baseline["fixed_costs"], period_current["fixed_costs"],
                    delta["fixed_costs_pct"], currency,
                ),
                "net_result": _interpret_change(
                    "net_result", period_baseline["net_result"], period_current["net_result"],
                    delta["net_result_pct"], currency,
                ),
            }

            return {
                "has_data": period_baseline["revenue"] > 0 or period_current["revenue"] > 0,
                "currency": currency,
                # Backward-compat: period_a / period_b unchanged from
                # what the model emitted (preserves caller naming)
                "period_a": {"start": pa_start, "end": pa_end, **period_a},
                "period_b": {"start": pb_start, "end": pb_end, **period_b},
                # Wave 14.HOTFIX5 — semantically-labelled periods
                # (always present, always correctly oriented)
                "period_baseline": {**baseline_dates, **period_baseline},
                "period_current": {**current_dates, **period_current},
                "delta": delta,
                "direction": direction,
                "key_drivers": drivers or ["Nessuna variazione significativa"],
                # Wave 14.HOTFIX4 (F1) / HOTFIX5 (canonicalised)
                "_change_interpretation": change_interp,
                "_period_orientation": {
                    "swapped_from_input": swapped,
                    "baseline_role": "older / reference period",
                    "current_role": "newer / compared period",
                    "delta_convention": "(current - baseline) / |baseline|",
                    "note": (
                        "delta_pct sign è intuitivo: positivo = current "
                        "(periodo più recente) è CRESCIUTO rispetto al "
                        "baseline. Negativo = current è DIMINUITO. "
                        "Il tool ha auto-detectato l'ordine cronologico "
                        "dai date di input, quindi la convenzione vale "
                        "indipendentemente da quale periodo è stato "
                        "etichettato 'period_a' vs 'period_b' nella call."
                    ),
                },
                "_convention_note": (
                    "Per ogni metric, '_change_interpretation' contiene un "
                    "human_label esplicito (es. 'revenue: crescita del +3,0%') "
                    "che disambigua la direzione. NON dedurre la direzione "
                    "dal sign di delta_*_pct: leggi sempre il human_label."
                ),
                "epistemic": {
                    "epistemic_class": "factual",
                    "reliability": "high",
                    "temporal_scope": "period_comparison",
                    "ai_usability": "cite_directly",
                },
            }

        elif tool_name == "query_monthly_trend":
            from datetime import date as _date
            from dateutil.relativedelta import relativedelta

            months = min(int(tool_input.get("months", 6)), 12)
            today = _date.today()

            # Build month boundaries
            trend = []
            for i in range(months - 1, -1, -1):
                m_start = (today.replace(day=1) - relativedelta(months=i))
                if i == 0:
                    m_end = today
                else:
                    m_end = (m_start + relativedelta(months=1)) - relativedelta(days=1)
                s = m_start.isoformat()
                e = m_end.isoformat()

                sales = await aggregate_sales_by_date(org_id, s, e)
                expenses = await aggregate_expenses_by_date(org_id, s, e)
                rev = round(sum(sales.values()), 2)
                exp = round(sum(expenses.values()), 2)
                net = round(rev - exp, 2)

                trend.append({
                    "month": m_start.strftime("%Y-%m"),
                    "month_label": m_start.strftime("%b %Y"),
                    "revenue": rev,
                    "expenses": exp,
                    "net_result": net,
                })

            # Compute MoM growth
            for i in range(1, len(trend)):
                prev_rev = trend[i - 1]["revenue"]
                curr_rev = trend[i]["revenue"]
                if prev_rev > 0:
                    trend[i]["revenue_growth_mom_pct"] = round((curr_rev - prev_rev) / prev_rev * 100, 1)
                else:
                    trend[i]["revenue_growth_mom_pct"] = 0
            if trend:
                trend[0]["revenue_growth_mom_pct"] = None  # no previous month

            return {
                "has_data": any(m["revenue"] > 0 or m["expenses"] > 0 for m in trend),
                "currency": currency,
                "months": trend,
                "total_months": len(trend),
                "epistemic": {
                    "epistemic_class": "factual",
                    "reliability": "high",
                    "temporal_scope": "monthly_series",
                    "ai_usability": "cite_directly",
                },
            }

        elif tool_name == "query_data_coherence":
            from database import orders_collection, sales_records_collection
            from datetime import datetime as dt, timedelta

            start = tool_input["start_date"]
            end = tool_input["end_date"]
            start_dt = dt.strptime(start, "%Y-%m-%d")
            end_dt = dt.strptime(end, "%Y-%m-%d") + timedelta(days=1)

            # 1. Cashflow total from sales_records (dataset=orders only)
            sr_pipeline = [
                {"$match": {"organization_id": org_id, "dataset_id": "orders",
                             "date": {"$gte": start, "$lte": end}}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
            ]
            sr_agg = await sales_records_collection.aggregate(sr_pipeline).to_list(1)
            sr_total = round(sr_agg[0]["total"], 2) if sr_agg else 0
            sr_count = sr_agg[0]["count"] if sr_agg else 0

            # 2. Cashflow total from ALL sales_records (including manual)
            sr_all_pipeline = [
                {"$match": {"organization_id": org_id,
                             "date": {"$gte": start, "$lte": end}}},
                {"$group": {"_id": "$dataset_id", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
            ]
            sr_by_source = {}
            async for doc in sales_records_collection.aggregate(sr_all_pipeline):
                sr_by_source[doc["_id"] or "unknown"] = {"total": round(doc["total"], 2), "count": doc["count"]}

            # 3. Orders total (confirmed + completed)
            order_pipeline = [
                {"$match": {"organization_id": org_id,
                             "status": {"$in": ["confirmed", "completed"]},
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$group": {"_id": None, "total": {"$sum": "$total"}, "count": {"$sum": 1}}},
            ]
            ord_agg = await orders_collection.aggregate(order_pipeline).to_list(1)
            ord_total = round(ord_agg[0]["total"], 2) if ord_agg else 0
            ord_count = ord_agg[0]["count"] if ord_agg else 0

            # 4. Orphan check: SalesRecords with order_id that don't match any order
            orphan_pipeline = [
                {"$match": {"organization_id": org_id, "dataset_id": "orders",
                             "date": {"$gte": start, "$lte": end},
                             "metadata.order_id": {"$exists": True}}},
                {"$lookup": {
                    "from": "orders", "localField": "metadata.order_id",
                    "foreignField": "id", "as": "order_match",
                }},
                {"$match": {"order_match": {"$size": 0}}},
                {"$count": "orphans"},
            ]
            orphan_result = await sales_records_collection.aggregate(orphan_pipeline).to_list(1)
            orphan_count = orphan_result[0]["orphans"] if orphan_result else 0

            # 5. Orders confirmed but missing SalesRecord
            missing_sr_pipeline = [
                {"$match": {"organization_id": org_id,
                             "status": {"$in": ["confirmed", "completed"]},
                             "created_at": {"$gte": start_dt, "$lt": end_dt}}},
                {"$lookup": {
                    "from": "sales_records", "localField": "id",
                    "foreignField": "metadata.order_id", "as": "sr_match",
                }},
                {"$match": {"sr_match": {"$size": 0}}},
                {"$count": "missing"},
            ]
            missing_result = await orders_collection.aggregate(missing_sr_pipeline).to_list(1)
            missing_sr_count = missing_result[0]["missing"] if missing_result else 0

            # 6. Payment status mismatches
            mismatch_pipeline = [
                {"$match": {"organization_id": org_id, "dataset_id": "orders",
                             "date": {"$gte": start, "$lte": end},
                             "metadata.order_id": {"$exists": True}}},
                {"$lookup": {
                    "from": "orders", "localField": "metadata.order_id",
                    "foreignField": "id", "as": "order",
                }},
                {"$unwind": {"path": "$order", "preserveNullAndEmptyArrays": True}},
                {"$match": {"$expr": {"$and": [
                    {"$ne": [{"$ifNull": ["$order", None]}, None]},
                    {"$ne": ["$payment_status", "$order.payment_status"]},
                ]}}},
                {"$count": "mismatches"},
            ]
            mismatch_result = await sales_records_collection.aggregate(mismatch_pipeline).to_list(1)
            payment_mismatches = mismatch_result[0]["mismatches"] if mismatch_result else 0

            # Analysis
            delta = round(sr_total - ord_total, 2)
            manual_revenue = round(sum(v["total"] for k, v in sr_by_source.items() if k != "orders"), 2)
            issues = []
            if abs(delta) > 0.01:
                issues.append(f"Delta cashflow ordini vs ordini confermati: {delta} {currency}")
            if orphan_count > 0:
                issues.append(f"{orphan_count} SalesRecord orfani (ordine non trovato)")
            if missing_sr_count > 0:
                issues.append(f"{missing_sr_count} ordini confermati senza SalesRecord")
            if payment_mismatches > 0:
                issues.append(f"{payment_mismatches} disallineamenti payment_status tra ordine e cashflow")
            if manual_revenue > 0:
                issues.append(f"{manual_revenue} {currency} in cashflow da fonti non-ordini (inserimento manuale/import)")

            return {
                "period": {"start_date": start, "end_date": end},
                "has_data": sr_count > 0 or ord_count > 0,
                "currency": currency,
                "cashflow_from_orders": {"total": sr_total, "records": sr_count},
                "cashflow_by_source": sr_by_source,
                "orders_confirmed": {"total": ord_total, "count": ord_count},
                "delta": delta,
                "checks": {
                    "orphan_sales_records": orphan_count,
                    "orders_missing_sales_record": missing_sr_count,
                    "payment_status_mismatches": payment_mismatches,
                    "manual_revenue": manual_revenue,
                },
                "issues": issues,
                "is_coherent": len(issues) == 0,
                "analysis": {
                    "coherence_score": "alto" if len(issues) == 0 else "medio" if len(issues) <= 2 else "basso",
                    "summary": f"{len(issues)} problemi trovati" if issues else "Dati coerenti, nessun problema rilevato.",
                },
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong",
                    "caveat": "Il delta puo derivare da date di registrazione diverse (order.created_at vs sales_record.date). Piccoli delta (< 1 unita di valuta) sono normali per arrotondamenti.",
                },
                "temporal_context": {
                    "scope": "period_filtered",
                    "note": "Confronto tra SalesRecords (filtrati per date) e Orders (filtrati per created_at). Lievi disallineamenti temporali possibili.",
                },
                "analytical_hints": {
                    "interpretation": "is_coherent=true = sistema integro. issues non vuote = indagare ogni voce. manual_revenue > 0 non e' necessariamente un problema (l'admin puo' inserire vendite fuori piattaforma).",
                    "action_guidance": "Se orphan_sales_records > 0 = possibile bug, segnalare. Se orders_missing_sales_record > 0 = ordini confermati senza registrazione cashflow, bug critico.",
                },
                "_caveat": None if (sr_count > 0 or ord_count > 0) else "Nessun dato nel periodo.",
            }

        # ── Wave 7D: late payers ────────────────────────────────────────────

        elif tool_name == "query_late_payers":
            from database import sales_records_collection
            from datetime import date as date_type

            today_str = date_type.today().isoformat()
            raw_min = tool_input.get("min_overdue_days", 0)
            try:
                min_overdue = max(0, int(raw_min))
            except (TypeError, ValueError):
                min_overdue = 0
            raw_limit = tool_input.get("limit", 10)
            try:
                limit = max(1, min(int(raw_limit), 50))
            except (TypeError, ValueError):
                limit = 10

            # Group unpaid records past due_date by customer
            pipeline = [
                {"$match": {
                    "organization_id": org_id,
                    "payment_status": {"$exists": True, "$ne": None, "$nin": ["paid"]},
                    "due_date": {"$exists": True, "$ne": None, "$lt": today_str},
                }},
                {"$group": {
                    "_id": {"$ifNull": ["$customer_id", "$customer_name"]},
                    "customer_name": {"$first": {"$ifNull": ["$customer_name", "$customer_id"]}},
                    "customer_id": {"$first": "$customer_id"},
                    "total_overdue": {"$sum": "$amount"},
                    "invoice_count": {"$sum": 1},
                    "oldest_due_date": {"$min": "$due_date"},
                }},
                {"$sort": {"total_overdue": -1}},
                {"$limit": 100},
            ]

            today_date = date_type.today()
            customers = []
            async for doc in sales_records_collection.aggregate(pipeline):
                oldest = doc.get("oldest_due_date") or today_str
                try:
                    days_late = (today_date - date_type.fromisoformat(oldest)).days
                except (ValueError, TypeError):
                    days_late = 0
                if days_late < min_overdue:
                    continue
                customers.append({
                    "customer_name": doc.get("customer_name") or "Sconosciuto",
                    "customer_id": doc.get("customer_id"),
                    "total_overdue": round(doc.get("total_overdue", 0), 2),
                    "invoice_count": doc.get("invoice_count", 0),
                    "oldest_due_date": oldest,
                    "days_late": days_late,
                })
                if len(customers) >= limit:
                    break

            total_overdue_all = round(sum(c["total_overdue"] for c in customers), 2)
            top_customer = customers[0] if customers else None

            return {
                "has_data": bool(customers),
                "currency": currency,
                "as_of": today_str,
                "min_overdue_days_filter": min_overdue,
                "customers": customers,
                "total_late_customers": len(customers),
                "total_overdue_amount": total_overdue_all,
                "top_late_payer": {
                    "name": top_customer["customer_name"],
                    "amount": top_customer["total_overdue"],
                    "days_late": top_customer["days_late"],
                } if top_customer else None,
                "epistemic": {
                    "epistemic_class": "factual", "reliability": "high",
                    "ai_usability": "strong",
                    "caveat": "Aggregazione su sales_records con payment_status != paid e due_date < oggi. Record senza customer_id raggruppati per customer_name (puo' creare aggregati impropri se i nomi sono digitati in modo inconsistente).",
                },
                "temporal_context": {
                    "scope": "current_state",
                    "note": "Snapshot al momento della richiesta. days_late = oggi - oldest_due_date.",
                },
                "analytical_hints": {
                    "interpretation": "days_late > 60 = critico, sollecito formale. days_late > 30 = warning, contatto telefonico. Confronta total_overdue_amount con query_receivables_payables.receivables.total_open per verificare quota concentrata sui top morosi.",
                    "cross_module": ["query_customer_profile per drill-down su singolo cliente"],
                },
                "_caveat": None if customers else "Nessun cliente moroso con i filtri impostati.",
            }

        else:
            return {"error": f"Tool sconosciuto: {tool_name}"}

    except Exception as e:
        logger.error("cashflow ai_tools: execution failed for %s: %s", tool_name, e, exc_info=True)
        return {"error": f"Errore nell'esecuzione del tool {tool_name}: {str(e)}"}
