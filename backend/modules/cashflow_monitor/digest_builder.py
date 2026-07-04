"""
Digest Builder — generates weekly/monthly financial digests via Claude.

Public interface:
    build_digest(org_id, period_days, digest_type, locale) -> Optional[dict]

Reuses build_overview() for all financial data (zero extra DB queries).
Falls back to rule-based summary when Claude is unavailable.

Locale support:
    - AI prompt: parameterized via LocaleProfile (same pattern as chat_service)
    - Fallback text: 4-locale text table (same pattern as status_builder._L)
    - Unknown locales fall back to Italian
"""
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# ── Locale text table (same pattern as status_builder._L) ────────────────────

_L = {
    "it": {
        "digest_type": {"weekly": "settimanale", "monthly": "mensile"},
        "headings": {
            "summary": "Sintesi del periodo",
            "key_points": "Punti chiave",
            "alerts": "Alert e rischi",
            "recommendations": "Raccomandazioni",
            "outlook": "Outlook",
        },
        # Wave 12.B — 7 sections, each with concrete instructions.
        # Each tuple element maps to one section's si_* placeholder.
        "structure_instructions": (
            # TL;DR
            "2-3 frasi che rispondono a: 'Come sta andando l'azienda?'. "
            "Cita i 2-3 numeri piu importanti (risultato netto, margine, health score) e indica direzione. "
            "Se c'e' UN problema dominante o UNA opportunita' dominante, dillo qui.",
            # Salute Finanziaria
            "Spiega il health score citando la dimensione PIU' DEBOLE e quella PIU' FORTE dal breakdown fornito. "
            "Non listare tutte le dimensioni — interpreta. "
            "Includi un > callout con la dimensione critica se score < 50. "
            "Qualifica come 'indicatore direzionale'.",
            # Performance del Periodo
            "Ricavi, uscite, margine, con confronto periodo precedente (sales_trend_pct, expenses_trend_pct) e YoY se disponibile. "
            "Spiega COSA e' cambiato di rilevante e PERCHE'. "
            "Se i ricavi sono in calo > 10% o le uscite in crescita > 10%, fai notare.",
            # Driver del Risultato
            "Identifica i 2-3 driver principali del risultato del periodo. "
            "Usa: top categoria spese, top fornitore, top cliente (se customer data presente), top prodotto (se product data presente), top canale (se commerce data presente). "
            "Es: 'Il margine 12% deriva da: concentrazione su Cliente X (22% ricavi), categoria spesa Y in crescita +18%, prodotto Z trainante con 35% delle vendite'.",
            # Rischi e Anomalie
            "Lista i rischi attivi cross-module: "
            "alert aperti per severity (se >0), clienti a rischio churn (se churn_risk_count >0), prodotti dormienti/declining (se >0), tasso cancellazioni alto (se >5%), bozze ordini aperti (se >0). "
            "Per ogni rischio: cosa e' e quanto impatta. NO se non ci sono rischi reali — dillo.",
            # Azioni Prioritarie
            "1-4 azioni numerate, ognuna legata a un dato specifico del periodo. "
            "Formato: 'Azione - perche dato X'. "
            "Es: '1. Sollecitare i 3 clienti con DSO >60gg (recuperabili EUR Y)'. "
            "Priorita' 1 = massimo impatto.",
            # Prospettive
            "1-2 frasi su cosa aspettarsi nel periodo successivo SE i trend attuali continuano. "
            "Non profetare — proietta. "
            "Es: 'Se il trend ricavi -8% continua, il margine scendera' sotto il break-even entro 6 settimane.'",
        ),
        "rules": (
            "Cita SEMPRE numeri concreti dai dati — non inventare",
            "Sii pratico e diretto",
            "Non usare emoji",
        ),
        "user_msg": {
            "digest_type": "Tipo digest",
            "period": "Periodo",
            "days": "giorni",
            "kpi_header": "KPI PRINCIPALI",
            "total_sales": "Ricavi totali",
            "total_expenses": "Spese operative",
            "supplier_purchases": "Acquisti fornitori",
            "fixed_costs": "Costi fissi",
            "net_result": "Risultato netto",
            "operating_margin": "Margine operativo",
            "outflow_ratio": "Rapporto uscite",
            "dso": "DSO",
            "dpo": "DPO",
            "ccc": "Ciclo di cassa (CCC)",
            "burn_rate": "Burn rate",
            "days_autonomy": "Giorni autonomia",
            "break_even": "Break-even",
            "sales_trend": "Trend ricavi",
            "expenses_trend": "Trend spese",
            "health_header": "SALUTE FINANZIARIA",
            "score": "Score",
            "alerts_header": "ALERT",
            "open_alerts": "Alert aperti",
            "critical": "Critici",
            "warning": "Warning",
            "info": "Info",
            "days_unit": "giorni",
            "per_day": "EUR/giorno",
            "na": "N/D",
        },
        "fallback": {
            "positive": "positivo",
            "negative": "negativo",
            "summary_tpl": (
                "Nel periodo {start} \u2014 {end} il risultato netto \u00e8 stato {trend} "
                "con {net} EUR e un margine operativo del {margin}%. "
                "La salute finanziaria \u00e8 {label} ({score}/100)."
            ),
            "revenue": "Ricavi",
            "expenses": "Spese operative",
            "fixed_costs": "Costi fissi",
            "burn_rate": "Burn rate",
            "days_autonomy": "Giorni di autonomia",
            "alerts_tpl": "Ci sono {count} alert aperti nel periodo analizzato.",
            "rec_burn": "Monitorare il burn rate e garantire adeguata copertura di cassa",
            "rec_dso": "Verificare i tempi di incasso (DSO: {dso} giorni)",
            "outlook_text": "Mantenere attenzione sulla gestione del capitale circolante.",
        },
    },
    "en": {
        "digest_type": {"weekly": "weekly", "monthly": "monthly"},
        "headings": {
            "summary": "Period Summary",
            "key_points": "Key Points",
            "alerts": "Alerts & Risks",
            "recommendations": "Recommendations",
            "outlook": "Outlook",
        },
        # Wave 12.B — 7 sections matching the IT version above. See IT for full doc.
        "structure_instructions": (
            "2-3 sentences answering 'How is the company doing?'. Cite 2-3 key numbers (net result, margin, health score), state direction. If ONE dominant problem or opportunity exists, say it here.",
            "Explain health score citing WEAKEST and STRONGEST dimension from the breakdown. Don't list every dimension — interpret. Include a > callout with the critical dimension if score < 50. Qualify as 'directional indicator'.",
            "Revenue, outflows, margin with vs-previous-period comparison (sales_trend_pct, expenses_trend_pct) and YoY when available. Explain WHAT changed and WHY. Flag changes > 10% in either direction.",
            "Identify 2-3 main drivers of the period result. Use: top expense category, top supplier, top customer (when present), top product (when present), top channel (when present). E.g. 'Margin 12% from: concentration on Customer X (22% revenue), expense category Y +18%, product Z driving 35% sales'.",
            "List active cross-module risks: open alerts by severity (if >0), at-risk customers for churn (if churn_risk_count >0), dormant/declining products (if >0), high cancellation rate (if >5%), draft orders (if >0). For each: what it is and impact. NO risks? Say so.",
            "1-4 numbered actions, each tied to a specific data point. Format: 'Action - because data X'. E.g. '1. Follow up the 3 customers with DSO >60d (EUR Y recoverable)'. Priority 1 = highest impact.",
            "1-2 sentences on what to expect in the next period IF current trends continue. Don't prophesy — project. E.g. 'If revenue trend -8% continues, margin drops below break-even within 6 weeks.'",
        ),
        "rules": (
            "ALWAYS cite concrete numbers from the data \u2014 never make up numbers",
            "Be practical and direct",
            "Do not use emoji",
        ),
        "user_msg": {
            "digest_type": "Digest type",
            "period": "Period",
            "days": "days",
            "kpi_header": "KEY KPIS",
            "total_sales": "Total revenue",
            "total_expenses": "Operating expenses",
            "supplier_purchases": "Supplier purchases",
            "fixed_costs": "Fixed costs",
            "net_result": "Net result",
            "operating_margin": "Operating margin",
            "outflow_ratio": "Outflow ratio",
            "dso": "DSO",
            "dpo": "DPO",
            "ccc": "Cash Conversion Cycle (CCC)",
            "burn_rate": "Burn rate",
            "days_autonomy": "Days of autonomy",
            "break_even": "Break-even",
            "sales_trend": "Revenue trend",
            "expenses_trend": "Expenses trend",
            "health_header": "FINANCIAL HEALTH",
            "score": "Score",
            "alerts_header": "ALERTS",
            "open_alerts": "Open alerts",
            "critical": "Critical",
            "warning": "Warning",
            "info": "Info",
            "days_unit": "days",
            "per_day": "EUR/day",
            "na": "N/A",
        },
        "fallback": {
            "positive": "positive",
            "negative": "negative",
            "summary_tpl": (
                "In the period {start} \u2014 {end} the net result was {trend} "
                "at {net} EUR with an operating margin of {margin}%. "
                "Financial health is {label} ({score}/100)."
            ),
            "revenue": "Revenue",
            "expenses": "Operating expenses",
            "fixed_costs": "Fixed costs",
            "burn_rate": "Burn rate",
            "days_autonomy": "Days of autonomy",
            "alerts_tpl": "There are {count} open alerts in the analyzed period.",
            "rec_burn": "Monitor burn rate and ensure adequate cash coverage",
            "rec_dso": "Review collection times (DSO: {dso} days)",
            "outlook_text": "Maintain focus on working capital management.",
        },
    },
    "de": {
        "digest_type": {"weekly": "w\u00f6chentlich", "monthly": "monatlich"},
        "headings": {
            "summary": "Zusammenfassung des Zeitraums",
            "key_points": "Kernpunkte",
            "alerts": "Warnungen & Risiken",
            "recommendations": "Empfehlungen",
            "outlook": "Ausblick",
        },
        # Wave 12.B — 7 sections (see IT for full doc).
        "structure_instructions": (
            "2-3 S\u00e4tze: 'Wie l\u00e4uft das Unternehmen?'. 2-3 Hauptzahlen (Nettoergebnis, Marge, Health Score) + Richtung. EIN dominantes Problem oder Chance hier.",
            "Health Score erkl\u00e4ren mit SCHW\u00c4CHSTER und ST\u00c4RKSTER Dimension. Nicht alle auflisten — interpretieren. > Callout f\u00fcr kritische Dimension wenn Score < 50.",
            "Umsatz, Ausgaben, Marge mit Vergleich Vorperiode + YoY wenn verf\u00fcgbar. WAS hat sich ge\u00e4ndert und WARUM. \u00c4nderungen > 10% hervorheben.",
            "2-3 Haupttreiber des Periodenergebnisses identifizieren. Top-Ausgabenkategorie, Top-Lieferant, Top-Kunde (falls vorhanden), Top-Produkt (falls vorhanden), Top-Kanal (falls vorhanden).",
            "Aktive Risiken: offene Warnungen nach Severity, Kunden mit Churn-Risiko, ruhende/r\u00fcckl\u00e4ufige Produkte, hohe Stornoquote, offene Bestellentw\u00fcrfe. Pro Risiko: was und Auswirkung. KEINE Risiken? Sagen.",
            "1-4 nummerierte Aktionen, jede an einen Datenpunkt gekoppelt. Format: 'Aktion - wegen Daten X'. Priorit\u00e4t 1 = h\u00f6chster Impact.",
            "1-2 S\u00e4tze: Was erwartet uns im n\u00e4chsten Zeitraum, WENN aktuelle Trends anhalten. Nicht prophezeien — projizieren.",
        ),
        "rules": (
            "Zitiere IMMER konkrete Zahlen aus den Daten \u2014 erfinde keine",
            "Sei praktisch und direkt",
            "Verwende keine Emoji",
        ),
        "user_msg": {
            "digest_type": "Digest-Typ",
            "period": "Zeitraum",
            "days": "Tage",
            "kpi_header": "WICHTIGE KENNZAHLEN",
            "total_sales": "Gesamtumsatz",
            "total_expenses": "Betriebsausgaben",
            "supplier_purchases": "Lieferanteneink\u00e4ufe",
            "fixed_costs": "Fixkosten",
            "net_result": "Nettoergebnis",
            "operating_margin": "Betriebsmarge",
            "outflow_ratio": "Ausgabenquote",
            "dso": "DSO",
            "dpo": "DPO",
            "ccc": "Cash Conversion Cycle (CCC)",
            "burn_rate": "Burn Rate",
            "days_autonomy": "Tage Autonomie",
            "break_even": "Break-even",
            "sales_trend": "Umsatztrend",
            "expenses_trend": "Ausgabentrend",
            "health_header": "FINANZIELLE GESUNDHEIT",
            "score": "Score",
            "alerts_header": "WARNUNGEN",
            "open_alerts": "Offene Warnungen",
            "critical": "Kritisch",
            "warning": "Warnung",
            "info": "Info",
            "days_unit": "Tage",
            "per_day": "EUR/Tag",
            "na": "k.A.",
        },
        "fallback": {
            "positive": "positiv",
            "negative": "negativ",
            "summary_tpl": (
                "Im Zeitraum {start} \u2014 {end} war das Nettoergebnis {trend} "
                "mit {net} EUR und einer Betriebsmarge von {margin}%. "
                "Die finanzielle Gesundheit ist {label} ({score}/100)."
            ),
            "revenue": "Umsatz",
            "expenses": "Betriebsausgaben",
            "fixed_costs": "Fixkosten",
            "burn_rate": "Burn Rate",
            "days_autonomy": "Tage Autonomie",
            "alerts_tpl": "Es gibt {count} offene Warnungen im analysierten Zeitraum.",
            "rec_burn": "Burn Rate \u00fcberwachen und ausreichende Liquidit\u00e4t sicherstellen",
            "rec_dso": "Inkassofristen pr\u00fcfen (DSO: {dso} Tage)",
            "outlook_text": "Weiterhin Augenmerk auf das Working-Capital-Management legen.",
        },
    },
    "fr": {
        "digest_type": {"weekly": "hebdomadaire", "monthly": "mensuel"},
        "headings": {
            "summary": "Synth\u00e8se de la p\u00e9riode",
            "key_points": "Points cl\u00e9s",
            "alerts": "Alertes et risques",
            "recommendations": "Recommandations",
            "outlook": "Perspectives",
        },
        # Wave 12.B — 7 sections (voir IT pour la doc compl\u00e8te).
        "structure_instructions": (
            "2-3 phrases : 'Comment va l'entreprise ?'. 2-3 chiffres cl\u00e9s (r\u00e9sultat net, marge, score) + direction. UN probl\u00e8me ou opportunit\u00e9 dominant.",
            "Expliquer le score de sant\u00e9 en citant la dimension la PLUS FAIBLE et la PLUS FORTE. Ne pas tout lister — interpr\u00e9ter. > Callout pour dimension critique si score < 50.",
            "Revenus, sorties, marge avec comparaison p\u00e9riode pr\u00e9c\u00e9dente + YoY si disponible. QUOI a chang\u00e9 et POURQUOI. Mettre en avant les changements > 10%.",
            "Identifier 2-3 drivers principaux. Top cat\u00e9gorie charges, top fournisseur, top client (si disponible), top produit (si disponible), top canal (si disponible).",
            "Risques actifs : alertes ouvertes par s\u00e9v\u00e9rit\u00e9, clients \u00e0 risque de churn, produits dormants/d\u00e9clinants, taux d'annulation \u00e9lev\u00e9, commandes brouillons. Par risque : quoi et impact. PAS de risques ? Le dire.",
            "1-4 actions num\u00e9rot\u00e9es, chacune li\u00e9e \u00e0 une donn\u00e9e sp\u00e9cifique. Format : 'Action - parce que donn\u00e9e X'. Priorit\u00e9 1 = impact max.",
            "1-2 phrases : que pr\u00e9voir si les tendances actuelles continuent. Ne pas proph\u00e9tiser — projeter.",
        ),
        "rules": (
            "Cite TOUJOURS des chiffres concrets tir\u00e9s des donn\u00e9es \u2014 n'invente pas",
            "Sois pratique et direct",
            "N'utilise pas d'emoji",
        ),
        "user_msg": {
            "digest_type": "Type de digest",
            "period": "P\u00e9riode",
            "days": "jours",
            "kpi_header": "KPI PRINCIPAUX",
            "total_sales": "Chiffre d'affaires total",
            "total_expenses": "Charges d'exploitation",
            "supplier_purchases": "Achats fournisseurs",
            "fixed_costs": "Charges fixes",
            "net_result": "R\u00e9sultat net",
            "operating_margin": "Marge op\u00e9rationnelle",
            "outflow_ratio": "Ratio de sorties",
            "dso": "DSO",
            "dpo": "DPO",
            "ccc": "Cycle de conversion de tr\u00e9sorerie (CCC)",
            "burn_rate": "Burn rate",
            "days_autonomy": "Jours d'autonomie",
            "break_even": "Seuil de rentabilit\u00e9",
            "sales_trend": "Tendance du CA",
            "expenses_trend": "Tendance des charges",
            "health_header": "SANT\u00c9 FINANCI\u00c8RE",
            "score": "Score",
            "alerts_header": "ALERTES",
            "open_alerts": "Alertes ouvertes",
            "critical": "Critiques",
            "warning": "Avertissements",
            "info": "Info",
            "days_unit": "jours",
            "per_day": "EUR/jour",
            "na": "N/D",
        },
        "fallback": {
            "positive": "positif",
            "negative": "n\u00e9gatif",
            "summary_tpl": (
                "Sur la p\u00e9riode {start} \u2014 {end} le r\u00e9sultat net a \u00e9t\u00e9 {trend} "
                "\u00e0 {net} EUR avec une marge op\u00e9rationnelle de {margin}%. "
                "La sant\u00e9 financi\u00e8re est {label} ({score}/100)."
            ),
            "revenue": "Chiffre d'affaires",
            "expenses": "Charges d'exploitation",
            "fixed_costs": "Charges fixes",
            "burn_rate": "Burn rate",
            "days_autonomy": "Jours d'autonomie",
            "alerts_tpl": "Il y a {count} alertes ouvertes dans la p\u00e9riode analys\u00e9e.",
            "rec_burn": "Surveiller le burn rate et garantir une couverture de tr\u00e9sorerie ad\u00e9quate",
            "rec_dso": "V\u00e9rifier les d\u00e9lais d'encaissement (DSO : {dso} jours)",
            "outlook_text": "Maintenir l'attention sur la gestion du fonds de roulement.",
        },
    },
}

# ── Wave 12.B — system prompt redesign for Sonnet ──────────────────────────
#
# Pre-Wave-12 prompt asked for 5 vague sections ("3-4 frasi che riassumono")
# and Sonnet would respond with sterile lists of numbers. The new prompt:
#
#   1. Defines 7 specific sections with CONCRETE instructions per section
#   2. Adds reasoning rules (claim discipline, hedging, cross-data links)
#   3. Specifies the exact markdown output format (## H2, > callouts,
#      numbered priorities, inline KPI emphasis) so the frontend
#      renderer can visualize it richly
#   4. Tells the model HOW to use cross-module data when present
#      (customers, products, commerce)
#   5. Includes a few-shot quality bar (in the user message) so the
#      model knows what "good" looks like
#
# The prompt is locale-aware via the existing _L["structure_instructions"]
# but now those instructions are MUCH more detailed and section-specific.

_SYSTEM_PROMPT = """You are a senior financial analyst writing a {digest_type_label} report for an SME owner. \
Your role: turn raw numbers into actionable understanding. The owner reads this in 90 seconds — every paragraph must earn its place.

# OUTPUT FORMAT (strict)

Produce a markdown document with EXACTLY these 7 sections in this order. Each section starts with a level-2 heading (`## `). Do not skip sections — when data is missing, say so briefly inside the section.

## TL;DR
{si_tldr}

## Salute Finanziaria
{si_health}

## Performance del Periodo
{si_performance}

## Driver del Risultato
{si_drivers}

## Rischi e Anomalie
{si_risks}

## Azioni Prioritarie
{si_actions}

## Prospettive
{si_outlook}

# REASONING RULES (MANDATORY)

1. **Cite numbers, never invent them.** Every claim must reference a specific data point from the input. If you can't, omit the claim.

1bis. **YoY / period comparison transparency (Wave Digest-Consistency, 2026-05-16):** when you cite a percentage variation (YoY, vs prior period, growth, decline, change), you MUST ALWAYS include BOTH absolute values (from-value AND to-value) in EUR. Examples:
   - CORRECT: "fatturato in crescita del +3,0% (da 78.884 EUR nel periodo precedente a 81.275 EUR nel periodo corrente)"
   - CORRECT: "perdita ridotta dell'87,6% (da -1.582 EUR a -197 EUR)"
   - CORRECT: "spese operative in calo del -2,8% (da 18.269 EUR a 17.755 EUR)"
   - FORBIDDEN: "ricavi in crescita +4,1% YoY" (manca il valore di partenza/arrivo)
   - FORBIDDEN: "crescita del 3%" (nessun valore assoluto)
The YEAR-OVER-YEAR section of the input data provides BOTH values side-by-side — use those exact numbers. Never derive a YoY % from the MoM "Trend ricavi" / "Trend spese" fields (those are vs previous-period, not vs prior year — they coincide only when the period is YTD).

2. **Connect dots across sections.** Don't restate numbers — explain what they mean together. "Margin 12% with revenue +5% but supplier cost +18%" is one insight, not three facts.

3. **Hedge epistemically:**
   - "Days of autonomy" is an ESTIMATE based on burn rate (not actual bank balance). Always qualify with "stimati" / "approssimativamente".
   - DSO/DPO are unreliable when payment_status or due_date are missing. If both are 0, flag possible missing data.
   - Health score below 100% confidence means some dimensions weren't computable — say so.

4. **Cross-module reasoning:** when customer / product / commerce data is present in the input, USE IT. Link cashflow trends to specific drivers (e.g. "Revenue +12% driven by Top Customer X, which now represents 22% of revenue — concentration risk"). When a module isn't in the input, don't mention it.

5. **No emoji. No tables (use bullets instead). No code blocks. No "Conclusione" / "Summary" wrap-up paragraphs** — TL;DR already serves that purpose.

6. **Action discipline:** every action in "Azioni Prioritarie" must:
   - Reference a specific data point ("perché X / dato che Y")
   - Be concrete ("contattare i 3 clienti dormienti", not "monitorare i clienti")
   - Be ranked by impact (priority 1 first, max 4 items)

7. **Format markdown** with: `## Section Title`, `**bold for KPIs**`, `> ` for callout boxes (one critical insight per section max), numbered lists `1.` `2.` for priority actions, bullet lists `-` for everything else. Inline KPI values in `**bold**`.

8. {respond_instruction}. Numbers formatted as {number_format_hint}.

# QUALITY BAR

A WEAK digest just restates the input ("Revenue 50k, margin 12%, score 65/100"). \
A STRONG digest tells the owner a STORY: what happened, why, what matters, what to do next. \
Aim for the strong version. \
"""


def _get_texts(locale: str) -> dict:
    """Return locale text table, falling back to Italian for unknown locales."""
    return _L.get(locale, _L["it"])


def _build_user_message(
    overview: dict, digest_type: str, period_days: int, locale: str = "it",
) -> str:
    """Build the structured data message sent to Claude for digest generation.

    Wave 12.B redesign:
      - Adds health BREAKDOWN (5 dimensions) so the model can explain WHY
      - Adds YoY block when available
      - Adds CUSTOMER_SUMMARY block when customers_light entitled
      - Adds PRODUCT_SUMMARY block when product_catalog entitled
      - Adds COMMERCE_SUMMARY block when commerce entitled
      - Adds TOP_CATEGORIES (sales + expenses) and TOP_SUPPLIERS so the
        model can identify drivers without inventing names
    """
    kpis = overview.get("kpis", {})
    health = overview.get("health_score", {})
    alerts = overview.get("alerts", {})
    alerts_summary = overview.get("alerts_summary", {})  # legacy fallback
    period = overview.get("period", {})
    yoy = overview.get("yoy", {})
    categories = overview.get("categories", {})
    suppliers = overview.get("suppliers", {})
    customers = overview.get("customers_summary", {})
    products = overview.get("products_summary", {})
    commerce = overview.get("commerce_summary", {})
    t = _get_texts(locale)["user_msg"]
    na = t["na"]

    def _f(v, fmt=",.0f"):
        try:
            return format(float(v or 0), fmt)
        except Exception:
            return na

    lines = [
        f"{t['digest_type']}: {digest_type}",
        f"{t['period']}: {period.get('start_date', na)} \u2014 {period.get('end_date', na)} ({period_days} {t['days']})",
        "",
        f"=== {t['kpi_header']} ===",
        f"- {t['total_sales']}: {_f(kpis.get('total_sales'))} EUR",
        f"- {t['total_expenses']}: {_f(kpis.get('total_expenses'))} EUR",
        f"- {t['supplier_purchases']}: {_f(kpis.get('supplier_purchases'))} EUR",
        f"- {t['fixed_costs']}: {_f(kpis.get('fixed_costs_total'))} EUR",
        f"- {t['net_result']}: {_f(kpis.get('net_after_fixed'))} EUR",
        f"- {t['operating_margin']}: {_f(kpis.get('operating_margin_pct'), '.1f')}%",
        f"- {t['outflow_ratio']}: {_f(kpis.get('total_outflow_ratio'), '.1f')}%",
        f"- {t['dso']}: {_f(kpis.get('dso'), '.0f')} {t['days_unit']}",
        f"- {t['dpo']}: {_f(kpis.get('dpo'), '.0f')} {t['days_unit']}",
        f"- {t['burn_rate']}: {_f(kpis.get('burn_rate_total'))} {t['per_day']}",
        f"- {t['days_autonomy']}: {_f(kpis.get('giorni_autonomia'), '.0f')} (stimati da burn rate, non saldo banca reale)",
        # Wave Digest-Consistency (2026-05-16) — explicit MoM label so
        # Claude does not confuse this with the YoY section below.
        # When the period is YTD, sales_trend_pct == YoY pct by design
        # (overview_builder R3); but in non-YTD periods they differ.
        f"- Trend ricavi (vs periodo precedente): {_f(kpis.get('sales_trend_pct'), '+.1f')}%",
        f"- Trend spese (vs periodo precedente): {_f(kpis.get('expenses_trend_pct'), '+.1f')}%",
    ]

    # ── Wave Digest-Consistency (2026-05-16) — explicit side-by-side YoY ──
    # Pre-fix the YoY section gave Claude only (yoy_value, yoy_pct), no
    # current-year value paired with it. Claude could then pattern-match
    # the MoM `sales_trend_pct` field and report THAT as YoY, producing
    # a +4.1% narrative against a verified-correct +3.0% canonical YoY.
    #
    # Now the section presents the data as side-by-side CURRENT vs PRIOR
    # YEAR rows with EXPLICIT date ranges + pre-computed delta, so the
    # LLM can ONLY cite correct YoY (and is forced to include both
    # absolute values for transparency).
    if yoy.get("has_data"):
        pct = yoy.get("pct", {}) or {}
        period_start = period.get("start_date", na)
        period_end = period.get("end_date", na)
        yoy_period_start = yoy.get("period_start", "?")
        yoy_period_end = yoy.get("period_end", "?")
        lines += [
            "",
            "=== YEAR-OVER-YEAR (stesso periodo anno precedente) ===",
            f"Periodo corrente:  {period_start} -> {period_end}",
            f"Periodo confronto: {yoy_period_start} -> {yoy_period_end}",
            "",
            "Confronto side-by-side (current vs prior year):",
        ]
        # Each row: <metric>: <current> EUR (corrente) vs <prior> EUR (precedente) -> +X.X%
        _kpi_yoy_rows = [
            (t['total_sales'], kpis.get('total_sales'), yoy.get('total_sales'), pct.get('total_sales')),
            (t['total_expenses'], kpis.get('total_expenses'), yoy.get('total_expenses'), pct.get('total_expenses')),
            (t['supplier_purchases'], kpis.get('supplier_purchases'), yoy.get('supplier_purchases'), pct.get('supplier_purchases')),
            (t['fixed_costs'], kpis.get('fixed_costs_total'), kpis.get('fixed_costs_total'), 0),  # fixed_costs are prorated same in both periods
            (t['net_result'], kpis.get('net_after_fixed'), yoy.get('net_after_fixed'), pct.get('net_after_fixed')),
        ]
        for label, cur_val, prior_val, p in _kpi_yoy_rows:
            if cur_val is None and prior_val is None:
                continue
            cur_s = _f(cur_val) if cur_val is not None else "N/D"
            prior_s = _f(prior_val) if prior_val is not None else "N/D"
            p_s = (
                _f(p, '+.1f') + "%" if p is not None else "N/D"
            )
            lines.append(
                f"  - {label}: {cur_s} EUR (corrente) vs {prior_s} EUR (precedente) -> {p_s}"
            )
        lines += [
            "",
            "NOTA per la stesura: quando citi una variazione YoY, INCLUDI SEMPRE entrambi i valori assoluti (corrente E precedente) in EUR, e cita la percentuale come 'rispetto all'anno precedente' o 'YoY'. Mai citare solo il %. Esempio corretto: 'fatturato in crescita del +3,0% (da 78.884 EUR a 81.275 EUR)'.",
        ]

    # Health: header + breakdown
    lines += [
        "",
        f"=== {t['health_header']} ===",
        f"- {t['score']}: {health.get('score', na)}/100 ({health.get('label', na)})",
    ]
    if health.get("trend"):
        lines.append(f"- Trend: {health['trend']}")
    if health.get("weakest_dimension"):
        w = health["weakest_dimension"]
        lines.append(
            f"- Dimensione PIU' DEBOLE: {w.get('dimension')} "
            f"({w.get('points')}/{w.get('max')}, level={w.get('level')})"
        )
    if health.get("strongest_dimension"):
        s = health["strongest_dimension"]
        lines.append(
            f"- Dimensione PIU' FORTE: {s.get('dimension')} "
            f"({s.get('points')}/{s.get('max')}, level={s.get('level')})"
        )
    breakdown = health.get("breakdown") or []
    if breakdown:
        lines.append("- Breakdown completo (per riferimento, non listarlo tutto):")
        for b in breakdown[:5]:
            pts = b.get("points")
            if pts is None:
                lines.append(
                    f"  · {b.get('dimension')}: N/D ({b.get('status', 'not_computable')})"
                )
            else:
                lines.append(
                    f"  · {b.get('dimension')}: {pts}/{b.get('max')} ({b.get('level', '?')})"
                )

    # Confidence + caveats
    conf = health.get("confidence")
    if conf is not None:
        lines.append(f"- Health confidence: {conf}%")
    caveats = health.get("data_caveats") or []
    if caveats:
        lines.append("- Data caveats:")
        for c in caveats[:3]:
            lines.append(f"  · {c}")

    # Top categories (drivers ready)
    top_sales = (categories.get("top_sales") or [])[:5]
    top_exp = (categories.get("top_expenses") or [])[:5]
    if top_sales or top_exp:
        lines.append("")
        lines.append("=== TOP CATEGORIES (drivers) ===")
        if top_sales:
            lines.append("- Top categorie RICAVI:")
            for c in top_sales:
                lines.append(
                    f"  · {c.get('category', '?')}: {_f(c.get('total'))} EUR ({_f(c.get('percentage'), '.1f')}%)"
                )
        if top_exp:
            lines.append("- Top categorie SPESE:")
            for c in top_exp:
                lines.append(
                    f"  · {c.get('category', '?')}: {_f(c.get('total'))} EUR ({_f(c.get('percentage'), '.1f')}%)"
                )

    # Top suppliers
    top_sup = (suppliers.get("top_suppliers") or [])[:5]
    if top_sup:
        lines.append("")
        lines.append("=== TOP SUPPLIERS ===")
        for s in top_sup:
            lines.append(
                f"  · {s.get('supplier', '?')}: {_f(s.get('total'))} EUR ({_f(s.get('percentage'), '.1f')}%)"
            )

    # Customer summary — only if module active and has data
    if customers.get("available"):
        lines += [
            "",
            "=== CUSTOMER_SUMMARY (modulo customers_light attivo) ===",
            f"- Clienti totali: {customers.get('total_customers', 0)}",
            f"- Nuovi clienti nel periodo: {customers.get('new_customers_count', 0)}",
            f"- Concentrazione top 5 clienti: {_f(customers.get('concentration_top5_pct'), '.1f')}% del fatturato",
            f"- Clienti a rischio churn (score >=60): {customers.get('churn_risk_count', 0)}",
            f"- CLV medio (revenue per cliente): {_f(customers.get('avg_clv'))} EUR",
        ]
        if customers.get("top_customers"):
            lines.append("- Top 5 clienti per fatturato lifetime:")
            for c in customers["top_customers"]:
                seg = f" [{c.get('segment')}]" if c.get("segment") else ""
                lines.append(
                    f"  · {c.get('name', '?')}: {_f(c.get('total_revenue'))} EUR{seg}"
                )

    # Product summary — only if module active and has data
    if products.get("available"):
        lines += [
            "",
            "=== PRODUCT_SUMMARY (modulo product_catalog attivo) ===",
            f"- Prodotti totali: {products.get('total_products', 0)}",
            f"- Margine medio: {_f(products.get('avg_margin_pct'), '.1f')}%",
            f"- Prodotti a basso margine (<15%): {products.get('low_margin_count', 0)}",
            f"- Prodotti in declino (-10% in 30gg): {products.get('declining_count', 0)}",
            f"- Prodotti dormienti (no vendite 60+ giorni): {products.get('dormant_count', 0)}",
        ]
        if products.get("top_sellers"):
            lines.append("- Top 5 prodotti per ricavo recente:")
            for p in products["top_sellers"]:
                lines.append(
                    f"  · {p.get('name', '?')}: {_f(p.get('revenue'))} EUR ({p.get('units', 0)} unita')"
                )

    # Commerce summary — only if module active and has data
    if commerce.get("available"):
        lines += [
            "",
            "=== COMMERCE_SUMMARY (modulo commerce attivo) ===",
            f"- Ordini nel periodo: {commerce.get('orders_count', 0)} (precedente: {commerce.get('orders_prev_count', 0)})",
            f"- AOV (Average Order Value): {_f(commerce.get('aov'))} EUR (precedente: {_f(commerce.get('aov_prev'))} EUR, trend {_f(commerce.get('aov_trend_pct'), '+.1f')}%)",
            f"- Tasso cancellazione: {_f(commerce.get('cancellation_rate_pct'), '.1f')}%",
            f"- Ordini in bozza (cash at risk): {commerce.get('draft_orders_count', 0)}",
        ]
        if commerce.get("top_channels"):
            lines.append("- Top 3 canali per fatturato:")
            for ch in commerce["top_channels"]:
                lines.append(
                    f"  · {ch.get('channel', '?')}: {_f(ch.get('revenue'))} EUR "
                    f"({_f(ch.get('share_pct'), '.1f')}%, {ch.get('count', 0)} ordini)"
                )

    # Alerts
    by_sev_modern = (alerts.get("by_severity") or {}) if alerts else {}
    by_sev_legacy = (alerts_summary.get("by_severity") or {}) if alerts_summary else {}
    by_sev = by_sev_modern or by_sev_legacy
    open_count = alerts.get("open_count") or alerts_summary.get("open_count") or 0

    lines += [
        "",
        f"=== {t['alerts_header']} ===",
        f"- {t['open_alerts']}: {open_count}",
        f"  · {t['critical']}: {by_sev.get('critical', 0) or by_sev.get('high', 0)}",
        f"  · {t['warning']}: {by_sev.get('warning', 0) or by_sev.get('medium', 0)}",
        f"  · {t['info']}: {by_sev.get('info', 0) or by_sev.get('low', 0)}",
    ]

    return "\n".join(lines)


# ── Wave 12.B — markdown parser for the 7-section digest ───────────────────
#
# The new prompt produces output with ## section headers. digest_report_builder
# (PDF path) uses this parser to extract each section's body, so we generate
# the digest ONCE (single Sonnet call) and reuse the output for both the
# frontend markdown rendering AND the PDF body text. Eliminates the second
# AI call that pre-Wave-12 was made by digest_report_builder._generate_ai_insights.

_SECTION_KEYS = [
    "tldr", "health", "performance", "drivers", "risks", "actions", "outlook",
]


def parse_digest_sections(markdown: Optional[str]) -> dict:
    """Parse the 7-section markdown output into a structured dict.

    Tolerant: missing sections come back as empty strings. Section
    matching is locale-aware via fuzzy keyword (TL;DR / Salute /
    Performance / Driver / Rischi / Azioni / Prospettive — and EN/DE/FR
    equivalents). If a contributor renames a section in the prompt,
    this parser may need to be updated (low risk: section names are
    stable per locale).

    Returns:
        {"tldr": str, "health": str, "performance": str,
         "drivers": str, "risks": str, "actions": list[str], "outlook": str,
         "raw": str}  # raw markdown for fallback rendering
    """
    out = {k: "" for k in _SECTION_KEYS}
    out["actions"] = []
    out["raw"] = markdown or ""

    if not markdown:
        return out

    # Locale-aware header matching. We look for level-2 headers (## ...)
    # and classify by keyword. Single source of truth — the section
    # ORDER from the prompt is deterministic, so we could also assume
    # order, but keyword matching is more robust against minor model
    # output variations.
    import re as _re
    _hdr_re = _re.compile(r"^##\s+(.+?)\s*$", _re.MULTILINE)

    def _classify(header: str) -> Optional[str]:
        h = header.lower().strip()
        if any(k in h for k in ["tl;dr", "tldr", "tl,dr", "tl/dr"]):
            return "tldr"
        if any(k in h for k in ["salute", "health", "gesund", "sant"]):
            return "health"
        if any(k in h for k in ["performance", "andamento", "leistung"]):
            return "performance"
        if any(k in h for k in ["driver", "leva", "treiber"]):
            return "drivers"
        if any(k in h for k in ["rischi", "rischio", "risk", "anomalie",
                                  "anomal", "risiko"]):
            return "risks"
        if any(k in h for k in ["azioni", "actions", "massnahmen", "actions"]):
            return "actions"
        if any(k in h for k in ["prospettive", "outlook", "perspectiv",
                                  "ausblick", "aussichten"]):
            return "outlook"
        return None

    # Find all ## headers with positions
    matches = list(_hdr_re.finditer(markdown))
    for i, m in enumerate(matches):
        key = _classify(m.group(1))
        if key is None:
            continue
        # Section body = from end-of-this-header to start-of-next-header
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[body_start:body_end].strip()
        if key == "actions":
            # Extract numbered items "1." "2." etc. — drop the numbering
            # and keep just the action text.
            actions = []
            for line in body.split("\n"):
                ls = line.strip()
                ma = _re.match(r"^\d+[.)]\s+(.+)$", ls)
                if ma:
                    actions.append(ma.group(1).strip())
            out["actions"] = actions[:4]
        else:
            out[key] = body

    return out


# ── Wave 12.B — extracted AI-call helper (unifies text + PDF paths) ─────────
# Pre-Wave-12 the PDF path had its own second Sonnet call via
# digest_report_builder._generate_ai_insights. Post-Wave-12, both paths
# call this single helper with the SAME pre-built overview, so the AI
# call happens exactly ONCE per digest regardless of format. The PDF
# path then parses the markdown to extract sections.

async def generate_digest_markdown(
    overview: dict,
    digest_type: str,
    period_days: int,
    locale: str = "it",
    *,
    org_id: str,
    user_id: Optional[str] = None,
    agent_id: str = "digest_builder",
) -> dict:
    """Generate the markdown digest from a pre-built context.

    Returns a dict:
        {"content": markdown_str or None,
         "model_version": str,
         "usage": dict or None,
         "ok": bool}

    Never raises — failures return {"content": None, "model_version": "rule-based"}.
    """
    from services.claude_client import (
        send_message_with_usage, is_available,
        get_active_model, calculate_cost_usd, resolve_non_chat_model,
    )
    from core.locale_utils import get_locale_profile
    from repositories.usage_repository import record_usage

    if not is_available():
        return {"content": None, "model_version": "rule-based",
                "usage": None, "ok": False}

    texts = _get_texts(locale)
    digest_type_label = texts["digest_type"].get(digest_type, digest_type)
    si = texts["structure_instructions"]
    profile = get_locale_profile(locale)

    try:
        from services.llm.budget_guard import check_budget_or_raise
        await check_budget_or_raise(
            organization_id=org_id, feature="digest",
            agent_id=agent_id,
        )

        system = _SYSTEM_PROMPT.format(
            digest_type_label=digest_type_label,
            si_tldr=si[0],
            si_health=si[1],
            si_performance=si[2],
            si_drivers=si[3],
            si_risks=si[4],
            si_actions=si[5],
            si_outlook=si[6],
            respond_instruction=profile.respond_instruction,
            number_format_hint=profile.number_format_hint,
        )
        user_msg = _build_user_message(overview, digest_type, period_days, locale)
        _model_override = resolve_non_chat_model() or None
        content, usage = await send_message_with_usage(
            system=system, user_message=user_msg,
            max_tokens=2048, temperature=0.4,  # Wave 12.B — bump temp for richer narrative
            model_version=_model_override,
        )

        # Tracking — same shape as build_digest's previous record_usage call
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
                org_id=org_id, module_key="ai_assistant", feature_key="digest",
                quantity=1,
                tokens_prompt=usage.get("input_tokens"),
                tokens_completion=usage.get("output_tokens"),
                cache_read_tokens=usage.get("cache_read_tokens"),
                cache_creation_tokens=usage.get("cache_creation_tokens"),
                latency_ms=usage.get("latency_ms"),
                provider="anthropic", model_version=model_version,
                cost_usd=cost,
                user_id=user_id, agent_id=agent_id,
            )
        except Exception as track_exc:
            logger.warning(
                "digest: record_usage failed for org=%s: %s", org_id, track_exc,
            )

        return {"content": content, "model_version": model_version,
                "usage": usage, "ok": True}
    except Exception as exc:
        logger.warning("digest: Claude generation failed for org=%s: %s",
                       org_id, exc)
        return {"content": None, "model_version": "rule-based",
                "usage": None, "ok": False}


def _rule_based_fallback(
    overview: dict, digest_type: str, locale: str = "it",
) -> str:
    """Generate a simple rule-based digest when Claude is unavailable.

    Uses the same _L locale text table as the AI prompt path, so fallback
    output respects the user's locale preference.
    """
    texts = _get_texts(locale)
    h = texts["headings"]
    f = texts["fallback"]
    t = texts["user_msg"]

    kpis = overview.get("kpis", {})
    health = overview.get("health_score", {})
    alerts_summary = overview.get("alerts_summary", {})
    period = overview.get("period", {})

    net = kpis.get("net_after_fixed", 0)
    margin = kpis.get("operating_margin_pct", 0)
    score = health.get("score", 0)
    label = health.get("label", t["na"])
    open_alerts = alerts_summary.get("open_count", 0)

    trend = f["positive"] if net > 0 else f["negative"]
    p_start = period.get("start_date", t["na"])
    p_end = period.get("end_date", t["na"])

    sections = [
        f"**{h['summary']}**\n"
        + f["summary_tpl"].format(
            start=p_start, end=p_end, trend=trend,
            net=f"{net:,.0f}", margin=f"{margin:.1f}",
            label=label, score=score,
        ),
        f"**{h['key_points']}**\n"
        f"- {f['revenue']}: {kpis.get('total_sales', 0):,.0f} EUR\n"
        f"- {f['expenses']}: {kpis.get('total_expenses', 0):,.0f} EUR\n"
        f"- {f['fixed_costs']}: {kpis.get('fixed_costs_total', 0):,.0f} EUR\n"
        f"- {f['burn_rate']}: {kpis.get('burn_rate_total', 0):,.0f} {t['per_day']}\n"
        f"- {f['days_autonomy']}: {kpis.get('giorni_autonomia', 0):.0f}",
        f"**{h['alerts']}**\n"
        + f["alerts_tpl"].format(count=open_alerts),
        f"**{h['recommendations']}**\n"
        f"- {f['rec_burn']}\n"
        "- " + f["rec_dso"].format(dso=f"{kpis.get('dso', 0):.0f}"),
        f"**{h['outlook']}**\n"
        + f["outlook_text"],
    ]
    return "\n\n".join(sections)


async def build_digest(
    org_id: str,
    period_days: int = 30,
    digest_type: str = "weekly",
    locale: str = "it",
    format: str = "text",
    include_ai: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> Optional[dict]:
    """Build a financial digest for the given organization.

    Args:
        format: "text" (legacy markdown) or "report" (PDF with charts).
        include_ai: If False, skip AI insights (Starter plan).
        start_date/end_date: Custom period (overrides period_days).

    Returns a dict ready to be saved as a Digest model, or None on failure.
    """
    if format == "report":
        from modules.cashflow_monitor.digest_report_builder import build_digest_report
        return await build_digest_report(
            org_id=org_id, period_days=period_days, digest_type=digest_type,
            locale=locale, include_ai=include_ai,
            start_date=start_date, end_date=end_date,
            user_id=user_id,  # Wave 8A.0 — propagate for usage tracking
        )
    # Wave 12.A — replace bare overview with the full cross-module context.
    # Adds customer_summary / product_summary / commerce_summary when those
    # modules are entitled, and enriches health with trend + weakest/strongest.
    from modules.cashflow_monitor.digest_context_builder import build_digest_context

    # Compute date range
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (
        datetime.now(timezone.utc) - timedelta(days=period_days)
    ).strftime("%Y-%m-%d")

    try:
        overview = await build_digest_context(
            org_id=org_id,
            period=f"{period_days}d",
            start_date=start_date,
            end_date=end_date,
            period_days=period_days,
        )
    except Exception as exc:
        logger.error("digest_builder: context failed for org=%s: %s", org_id, exc)
        return None

    if not overview:
        logger.info("digest_builder: no data for org=%s \u2014 skipping", org_id)
        return None

    # Wave 12.B — delegate the AI call to the extracted helper so that
    # digest_report_builder (PDF path) can reuse it without duplicating
    # the prompt+tracking logic. The single helper guarantees that:
    #   - both paths use the SAME prompt
    #   - both paths use the SAME governance gate (budget + kill switch)
    #   - both paths record exactly ONE AIUsageEvent
    ai_result = await generate_digest_markdown(
        overview=overview, digest_type=digest_type,
        period_days=period_days, locale=locale,
        org_id=org_id, user_id=user_id,
    )
    content = ai_result.get("content")
    model_version = ai_result.get("model_version") or "rule-based"

    if not content:
        content = _rule_based_fallback(overview, digest_type, locale)
        model_version = "rule-based"

    kpis = overview.get("kpis", {})
    alerts_summary = overview.get("alerts_summary", {})

    return {
        "organization_id": org_id,
        "digest_type": digest_type,
        "content": content,
        "period_start": start_date,
        "period_end": end_date,
        "kpis_summary": {
            "total_sales": kpis.get("total_sales", 0),
            "total_expenses": kpis.get("total_expenses", 0),
            "net_after_fixed": kpis.get("net_after_fixed", 0),
            "operating_margin_pct": kpis.get("operating_margin_pct", 0),
            "health_score": overview.get("health_score", {}).get("score", 0),
        },
        "alerts_count": alerts_summary.get("open_count", 0),
        "model_version": model_version,
    }
