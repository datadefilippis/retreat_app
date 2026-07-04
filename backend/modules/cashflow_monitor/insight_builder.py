"""
Cashflow Monitor — AI insight builder.

Extracted from ai_insight_service.py (v2.1).  Contains all cashflow-specific
content for the LLM call:
  - System prompt definition
  - Data enrichment (fixed costs, expense categories)
  - User message construction
  - Rule-based fallback content generation

Public interface:
    build_insight_context(org_id, start, end) -> Optional[dict]
        Fetches cashflow data, builds the prompt pair and fallback string.
        Returns a context dict consumed by ai_insight_service.  Returns None
        when there is no data available for the period.

Context dict keys (all required by ai_insight_service):
    system_prompt     str
    user_message      str
    fallback_content  str
    module_key        str   ("cashflow_monitor")
    title             str   ("Analisi Cashflow")
    metrics_context   dict  (persisted in the Insight document)
"""
import asyncio
import re
from typing import Optional

from repositories import analytics_repository
from services.ai_analytics_service import get_analytics_summary
from modules.cashflow_monitor import kpi_formulas


def _sanitize_prompt_text(text: str, max_len: int = 80) -> str:
    """Sanitize a user-data string before embedding it in an LLM prompt.

    Defenses:
    - Strips newlines and control characters (prevent prompt structure injection)
    - Collapses whitespace
    - Truncates to max_len to prevent prompt bloat
    - Removes quotes that could break prompt delimiters
    """
    if not text:
        return "N/D"
    text = re.sub(r'[\r\n\t\x00-\x1f\x7f]', ' ', text)   # control chars → space
    text = re.sub(r'["\']', '', text)                       # strip quotes
    text = re.sub(r'\s+', ' ', text).strip()                # collapse whitespace
    return text[:max_len] if text else "N/D"


# ── System prompt (cashflow-specific, PMI-friendly tone) ──────────────────────

_SYSTEM_PROMPT = """Sei un consulente finanziario esperto di piccole e medie imprese italiane.
Il tuo compito è analizzare i dati di cassa di un'azienda e fornire un'analisi chiara e concreta.

Regole fondamentali:
1. Usa SOLO i numeri forniti nei dati — non inventare o stimare cifre
2. Parla come se stessi spiegando a un imprenditore, non a un contabile
3. Il "Risultato Netto Finale" (ricavi meno tutte le uscite) è la cifra chiave — citala sempre
4. I costi sono organizzati in 3 bucket:
   - Bucket A (Spese Operative): costi variabili del business quotidiano
   - Bucket B (Acquisti Fornitori): acquisto di merci e materie prime
   - Bucket C (Costi Fissi): struttura fissa dell'azienda (affitti, stipendi fissi, ecc.)
5. Se il risultato è negativo o sotto pressione, identifica QUALE bucket è il principale responsabile
6. Per ogni problema identificato, suggerisci UN'azione specifica e praticabile per quel bucket
7. Tono professionale ma accessibile — evita jargon tecnico non necessario
8. Usa la valuta e il formato numerico dei dati ricevuti

Regole aggiuntive di diagnosi (usa SOLO se i dati lo supportano):
- Se DSO > 60 giorni → segnalare rischio liquidità e suggerire revisione politica incassi
- Se Giorni Autonomia < 30 → priorità critica, azione immediata sulla riduzione costi
- Se Cash Conversion Cycle > 90 giorni → inefficienza nel ciclo finanziario
- Se top fornitore > 40% degli acquisti → rischio concentrazione fornitore
- Se fatturato corrente < break-even → deficit strutturale, urge intervento
- Se Margine Operativo < 10% → marginalità insufficiente, rischio di fragilità

Formato della risposta (obbligatorio, con sezioni in grassetto):
**Situazione generale**
2-3 frasi sulla salute complessiva del periodo. Cita il Risultato Netto Finale come dato chiave.
Indica chiaramente se l'azienda è in utile o in perdita.

**Cosa è successo**
3-4 bullet point con le osservazioni più importanti.
Per ogni voce anomala specifica quale bucket è coinvolto (A, B o C) e il numero.

**Rischio finanziario** (includi SOLO se i dati evidenziano rischi concreti)
1 paragrafo con rischi identificati e azione suggerita. Basa i rischi SOLO sugli indicatori
forniti (DSO, CCC, giorni autonomia, concentrazione fornitori, break-even).

**Cosa fare**
1-2 azioni concrete rivolte al bucket problematico identificato.
Evita consigli generici — solo azioni ragionevolmente praticabili da un imprenditore PMI."""


# ── Prompt helpers ────────────────────────────────────────────────────────────

def _format_categories(categories: list, limit: int = 3) -> str:
    """Format top N categories as a readable string for the LLM prompt."""
    if not categories:
        return "  (nessun dato per categoria)"
    lines = []
    for cat in categories[:limit]:
        name = _sanitize_prompt_text(cat.get("_id") or cat.get("category") or "N/D")
        total = cat.get("total", 0)
        pct = cat.get("percentage", 0)
        lines.append(f"  - {name}: €{total:,.2f} ({pct:.1f}%)")
    return "\n".join(lines) if lines else "  (nessun dato per categoria)"


def _build_scadenzario_block(
    open_receivables: float,
    open_payables: float,
    upcoming_recv_30: float,
    upcoming_pay_30: float,
    total_sales: float,
    supplier_purchases: float,
    period_days: int,
) -> str:
    """Build the CICLO DI CASSA section for the LLM prompt."""
    if open_receivables == 0 and open_payables == 0 and upcoming_recv_30 == 0:
        return "CICLO DI CASSA:\n  (nessun dato scadenzario — due_date non ancora popolato)"

    dso = kpi_formulas.dso(open_receivables, total_sales, period_days) or 0.0
    dpo = kpi_formulas.dpo(open_payables, supplier_purchases, period_days) or 0.0
    ccc = kpi_formulas.cash_conversion_gap(
        kpi_formulas.dso(open_receivables, total_sales, period_days),
        kpi_formulas.dpo(open_payables, supplier_purchases, period_days),
    ) or 0.0
    scad_netto = round(upcoming_recv_30 - upcoming_pay_30, 2)

    return (
        f"CICLO DI CASSA:\n"
        f"- DSO (Days Sales Outstanding): {dso} giorni\n"
        f"- DPO (Days Payable Outstanding): {dpo} giorni\n"
        f"- Cash Conversion Cycle (DSO−DPO): {ccc} giorni\n"
        f"- Crediti aperti (non incassati): €{open_receivables:,.2f}\n"
        f"- Debiti aperti (non pagati): €{open_payables:,.2f}\n"
        f"- Scadenzario netto prossimi 30gg (incassi − pagamenti): €{scad_netto:,.2f}"
    )


def _build_supplier_concentration_block(
    purchases_by_supplier: list,
    supplier_purchases: float,
) -> str:
    """Build the CONCENTRAZIONE FORNITORI section for the LLM prompt."""
    if not purchases_by_supplier or supplier_purchases <= 0:
        return "CONCENTRAZIONE FORNITORI:\n  (nessun dato acquisti fornitori)\n"

    top = purchases_by_supplier[0] if purchases_by_supplier else {}
    top_name = _sanitize_prompt_text(str(top.get("_id", "N/D")))
    top_total = top.get("total", 0)
    top_pct = round((top_total / supplier_purchases * 100) if supplier_purchases > 0 else 0, 1)

    # Top 3 cumulative
    top3_total = sum(s.get("total", 0) for s in purchases_by_supplier[:3])
    top3_pct = round((top3_total / supplier_purchases * 100) if supplier_purchases > 0 else 0, 1)

    return (
        f"CONCENTRAZIONE FORNITORI:\n"
        f"- Top fornitore: {top_name} — €{top_total:,.2f} ({top_pct}% degli acquisti)\n"
        f"- Top 3 fornitori cumulato: {top3_pct}% degli acquisti\n"
    )


def _build_user_message(
    summary: dict,
    fixed_costs_total: float,
    expense_categories: list,
    supplier_purchases: float = 0.0,
    *,
    purchases_by_supplier: list = None,
    open_receivables: float = 0.0,
    open_payables: float = 0.0,
    upcoming_recv_30: float = 0.0,
    upcoming_pay_30: float = 0.0,
) -> str:
    """Build the full LLM user message with all available metrics (v2.4: scadenzario + suppliers)."""
    # Compute expense_ratio inline (safe division)
    total_sales = summary["totals"]["sales"]
    total_expenses = summary["totals"]["expenses"]
    expense_ratio = round((total_expenses / total_sales * 100) if total_sales > 0 else 0, 1)

    # v2.2: 3-bucket view
    variable_outflows = round(total_expenses + supplier_purchases, 2)
    total_outflows = round(variable_outflows + fixed_costs_total, 2)
    net_after_fixed = round(total_sales - total_outflows, 2)
    total_outflow_ratio = round((total_outflows / total_sales * 100) if total_sales > 0 else 0, 1)

    # Top categories block
    cat_block = _format_categories(expense_categories)

    # Only show purchases block if there is data
    purchase_block = (
        f"- Acquisti fornitori (Bucket B): €{supplier_purchases:,.2f}\n"
        if supplier_purchases > 0
        else ""
    )

    # Dominant bucket hint — helps the AI focus its diagnosis
    buckets = [
        (total_expenses,     "Bucket A (Spese Operative)"),
        (supplier_purchases, "Bucket B (Acquisti Fornitori)"),
        (fixed_costs_total,  "Bucket C (Costi Fissi)"),
    ]
    dominant_bucket_name = max(buckets, key=lambda x: x[0])[1]

    # v3.0: derived financial KPIs via canonical formulas
    operating_margin = round(total_sales - variable_outflows, 2)
    operating_margin_pct = kpi_formulas.net_margin_pct(operating_margin, total_sales) or 0.0
    vcr = kpi_formulas.variable_cost_ratio(variable_outflows, total_sales)
    break_even = kpi_formulas.break_even_point(fixed_costs_total, vcr) or 0.0
    period_days = summary["period"]["days"]
    burn_rate_total = kpi_formulas.burn_rate_daily(total_outflows, period_days) or 0.0
    giorni_autonomia = kpi_formulas.operational_coverage_days(
        net_after_fixed, total_outflows, period_days,
    ) or 0.0
    fixed_costs_pct = kpi_formulas.fixed_cost_ratio(fixed_costs_total, total_sales) or 0.0

    return f"""Analizza questi dati di cassa per un'azienda PMI:

PERIODO: {summary['period']['start']} → {summary['period']['end']} ({period_days} giorni)

TOTALI DEL PERIODO (modello a 3 bucket):
- Ricavi totali: €{total_sales:,.2f}
- Bucket A — Spese operative (costi variabili): €{total_expenses:,.2f}
{purchase_block}- Bucket C — Costi fissi (proratizzati): €{fixed_costs_total:,.2f}
- Uscite totali (A+B+C): €{total_outflows:,.2f}
- Cashflow operativo (ricavi − A): €{summary['totals']['net_cashflow']:,.2f}
- ★ RISULTATO NETTO FINALE (ricavi − A − B − C): €{net_after_fixed:,.2f}
- Expense ratio complessivo: {total_outflow_ratio}%

BUCKET PIÙ PESANTE (maggiore incidenza sulle uscite): {dominant_bucket_name}

INDICATORI FINANZIARI DERIVATI:
- Margine Operativo (ricavi − costi variabili): €{operating_margin:,.2f} ({operating_margin_pct}%)
- Break-Even Point (fatturato minimo per coprire i costi): €{break_even:,.2f}
- Burn Rate giornaliero totale (uscite medie/giorno): €{burn_rate_total:,.2f}
- Giorni di Autonomia stimati (cassa / burn rate): {giorni_autonomia:.0f} giorni
- Incidenza Costi Fissi sul fatturato: {fixed_costs_pct}%

MEDIE GIORNALIERE:
- Ricavi giornalieri medi: €{summary['averages']['daily_sales']:,.2f}
- Spese giornaliere medie: €{summary['averages']['daily_expenses']:,.2f}

TREND VS PERIODO PRECEDENTE:
- Variazione ricavi: {summary['trends']['sales_change_pct']:+.1f}%
- Variazione spese operative: {summary['trends']['expenses_change_pct']:+.1f}%

PRINCIPALI CATEGORIE DI SPESA OPERATIVA (Bucket A):
{cat_block}

ANOMALIE RILEVATE:
- Giorni con cashflow negativo: {summary['concerns']['negative_cashflow_days']}
- Giorni con vendite basse (>30% sotto media): {len(summary['concerns']['low_sales_days'])}
- Giorni con spese alte (>30% sopra media): {len(summary['concerns']['high_expense_days'])}

{_build_scadenzario_block(open_receivables, open_payables, upcoming_recv_30, upcoming_pay_30, total_sales, supplier_purchases, period_days)}
{_build_supplier_concentration_block(purchases_by_supplier, supplier_purchases)}
BREAK-EVEN vs REALTÀ:
- Fatturato periodo: €{total_sales:,.2f}
- Break-Even: €{break_even:,.2f}
- {"✅ Fatturato SOPRA break-even" if total_sales >= break_even and break_even > 0 else "⚠️ Fatturato SOTTO break-even — deficit strutturale" if break_even > 0 else "N/D (dati insufficienti)"}

Fornisci la tua analisi seguendo il formato richiesto."""


def _generate_fallback_content(
    summary: dict,
    fixed_costs_total: float,
    expense_categories: list,
    supplier_purchases: float = 0.0,
) -> str:
    """Generate a rule-based insight text when the LLM call fails (v2.2: 3-bucket aware)."""
    totals = summary["totals"]
    trends = summary["trends"]
    concerns = summary["concerns"]

    # v2.2: use full 3-bucket view for health assessment
    total_outflows = round(totals["expenses"] + supplier_purchases + fixed_costs_total, 2)
    net_after_fixed = round(totals["sales"] - total_outflows, 2)
    total_outflow_ratio = round(
        (total_outflows / totals["sales"] * 100) if totals["sales"] > 0 else 0, 1
    )

    if net_after_fixed > 0 and concerns["negative_cashflow_days"] < 3:
        health = "positiva"
    elif net_after_fixed > 0:
        health = "stabile ma con alcune criticità"
    else:
        health = "sotto pressione"

    top_cat = expense_categories[0] if expense_categories else None
    top_cat_line = ""
    if top_cat:
        cat_name = _sanitize_prompt_text(top_cat.get("_id") or top_cat.get("category") or "N/D")
        cat_total = top_cat.get("total", 0)
        top_cat_line = (
            f"- La categoria di spesa principale è '{cat_name}' con €{cat_total:,.2f}.\n"
        )

    purchase_line = (
        f"- Acquisti fornitori: €{supplier_purchases:,.2f}.\n"
        if supplier_purchases > 0
        else ""
    )

    return (
        f"**Situazione generale**\n"
        f"La cassa del periodo è {health}. Ricavi di €{totals['sales']:,.2f} contro uscite "
        f"totali di €{total_outflows:,.2f} (spese operative + acquisti fornitori + costi fissi), "
        f"per un risultato netto di €{net_after_fixed:,.2f}. "
        f"L'expense ratio complessivo è {total_outflow_ratio}%.\n\n"
        f"**Cosa è successo**\n"
        f"- I ricavi sono {trends['sales_change_pct']:+.1f}% rispetto al periodo precedente.\n"
        f"- Le spese operative sono {trends['expenses_change_pct']:+.1f}% rispetto al periodo precedente.\n"
        f"{purchase_line}"
        f"{top_cat_line}"
        f"- {concerns['negative_cashflow_days']} giorni hanno registrato un cashflow negativo.\n\n"
        f"**Cosa fare**\n"
        + (
            "Mantieni il ritmo attuale e monitora le categorie di spesa principali."
            if net_after_fixed > 0
            else "Rivedi le categorie di spesa più pesanti e valuta se ci sono costi "
            "comprimibili nel breve termine."
        )
    )


# ── Public entry point ────────────────────────────────────────────────────────

async def build_insight_context(
    org_id: str,
    start: str,
    end: str,
) -> Optional[dict]:
    """Fetch cashflow data and build the full context for the LLM call.

    Returns a dict with keys: system_prompt, user_message, fallback_content,
    module_key, title, metrics_context.  Returns None when there is no data
    for the period (get_analytics_summary returns None).
    """
    summary = await get_analytics_summary(org_id, start, end)
    if not summary:
        return None

    # Enrich with fixed costs, purchase records, category breakdown,
    # supplier concentration, and scadenzario data (non-blocking)
    (
        fixed_costs_total,
        purchases_by_date,
        expense_categories,
        purchases_by_supplier,       # v2.4: Pareto fornitori
        open_receivables,            # v2.4: Scadenzario
        open_payables,               # v2.4: Scadenzario
        upcoming_receivables_30,     # v2.4: Scadenzario (30gg)
        upcoming_payables_30,        # v2.4: Scadenzario (30gg)
    ) = await asyncio.gather(
        analytics_repository.aggregate_fixed_costs_total(org_id, start, end),
        analytics_repository.aggregate_purchases_by_date(org_id, start, end),  # v2.2
        analytics_repository.aggregate_expenses_by_category(org_id, start, end),
        analytics_repository.aggregate_purchases_by_supplier(org_id, start, end),  # v2.4
        analytics_repository.aggregate_open_receivables(org_id),                   # v2.4
        analytics_repository.aggregate_open_payables(org_id),                      # v2.4
        analytics_repository.aggregate_upcoming_receivables(org_id, 30),           # v2.4
        analytics_repository.aggregate_upcoming_payables(org_id, 30),              # v2.4
    )

    # v2.2: compute total supplier purchases
    supplier_purchases = round(sum(purchases_by_date.values()), 2)

    # Add percentage to each category for the prompt
    total_exp = sum(c.get("total", 0) for c in expense_categories)
    for cat in expense_categories:
        cat["percentage"] = round(
            (cat["total"] / total_exp * 100) if total_exp > 0 else 0, 1
        )

    # v2.4: compute upcoming totals for AI context
    recv_30_total = round(sum(r["total"] for r in upcoming_receivables_30), 2)
    pay_30_total = round(sum(p["total"] for p in upcoming_payables_30), 2)

    return {
        "system_prompt": _SYSTEM_PROMPT,
        "user_message": _build_user_message(
            summary, fixed_costs_total, expense_categories, supplier_purchases,
            purchases_by_supplier=purchases_by_supplier,
            open_receivables=open_receivables,
            open_payables=open_payables,
            upcoming_recv_30=recv_30_total,
            upcoming_pay_30=pay_30_total,
        ),
        "fallback_content": _generate_fallback_content(
            summary, fixed_costs_total, expense_categories, supplier_purchases
        ),
        "module_key": "cashflow_monitor",
        "title": "Analisi Cashflow",
        "metrics_context": {
            **summary,
            "fixed_costs_total": fixed_costs_total,
            "supplier_purchases": supplier_purchases,       # v2.2
            "top_expense_categories": expense_categories[:5],
            "open_receivables": open_receivables,           # v2.4
            "open_payables": open_payables,                 # v2.4
        },
    }
