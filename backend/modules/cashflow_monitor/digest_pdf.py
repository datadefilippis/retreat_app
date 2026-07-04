"""
Digest PDF v4 — Consultant-grade financial report.

Narrative structure:
  P1: Verdict + KPIs + outflow breakdown
  P2: Monthly trend + YoY + cash cycle interpretation
  P3: Charts (daily, cumulative, categories)
  P4: Situation assessment + health dimensions + priority actions + AI

All interpretive text is rule-based (no AI required).
"""

import io
from typing import Dict, List, Optional
from datetime import date
from collections import defaultdict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Circle, String

# ── Wave 12.F — modern palette ──────────────────────────────────────────────
#
# Pre-Wave-12.F the PDF used saturated colors (#2563EB blue, #DC2626 red)
# with full grid tables and heavy blue banners. The vibe was 90s-corporate
# spreadsheet. Wave 12.F refines: softer accents, more whitespace,
# cleaner typography hierarchy, and "card" patterns instead of bordered
# tables. The data flow stays identical.
P = {
    # Core neutrals — most surfaces are white-or-near-white
    "white": "#FFFFFF",
    "page": "#FAFBFC",            # very subtle page tint
    "border": "#E5E7EB",          # light hairline
    "borderS": "#F3F4F6",         # even softer (KPI card top border)
    "muted": "#6B7280",           # secondary text
    "mutedD": "#4B5563",          # tertiary text
    "dark": "#111827",            # primary heading / KPI value
    "darkS": "#1F2937",           # body text

    # Accent (single brand color)
    "blue": "#2563EB",
    "blueD": "#1E3A8A",           # deeper for section labels
    "blueT": "#EFF6FF",           # accent tint

    # Semantic palette — softer than before
    "green": "#10B981",           # emerald (was #16A34A — slightly less yellow)
    "greenT": "#ECFDF5",          # success tint
    "amber": "#F59E0B",
    "amberT": "#FFFBEB",
    "red": "#EF4444",             # softer than #DC2626
    "redT": "#FEF2F2",

    # Backward-compat aliases used by older parts of the file —
    # remove once all call-sites migrated. Currently kept to avoid
    # breaking the file mid-refactor.
    "blueL": "#EFF6FF",
    "greenL": "#ECFDF5",
    "amberL": "#FFFBEB",
    "redL": "#FEF2F2",
    "gray": "#6B7280",
    "grayL": "#F9FAFB",
}
hc = colors.HexColor
PAGE_W, PAGE_H = A4
MG = 16 * mm
CW = PAGE_W - 2 * MG

# ── i18n (abbreviated — full 4 lang) ─────────────────────────────────────────
_T = {
    "it": dict(
        weekly="Report Settimanale", monthly="Report Mensile", custom="Report",
        period="Periodo", verdict_title="Panoramica",
        kpi_title="Numeri del Periodo", metric="Indicatore", current="Attuale",
        previous="Precedente", change="Variazione",
        rev="Ricavi", opex="Spese operative", purch="Acquisti fornitori",
        fixed="Costi fissi", tot_out="Uscite totali", net="Risultato netto",
        margin="Margine operativo",
        outflow_title="Dove Vanno i Soldi",
        trend_title="Trend Mensile", month_h="Mese", trend_h="Trend",
        yoy_title="Confronto Anno su Anno", yoy_cur="Attuale", yoy_prev="Anno scorso",
        cash_title="Ciclo di Cassa e Liquidita'",
        dso="DSO (Giorni incasso)", dpo="DPO (Giorni pagamento)",
        ccc="Ciclo conversione cassa", autonomy="Giorni autonomia",
        burn="Burn rate /giorno", be="Break-even", days="giorni", na="N/D",
        charts_title="Analisi Visuale", daily="Andamento Giornaliero",
        cumul="Cashflow Cumulativo",
        top_rev="Top Categorie Ricavi", top_exp="Top Categorie Uscite",
        assess_title="Valutazione della Situazione",
        assess_critical="La situazione richiede attenzione immediata.",
        assess_warning="La situazione e' sotto osservazione.",
        assess_good="La situazione e' buona.",
        assess_ok="La situazione e' sotto controllo. Non sono state rilevate criticita'.",
        health_dim_title="Health Score — Dettaglio per Dimensione",
        dim="Dimensione", score="Punteggio", status="Stato",
        priority_title="Azioni Prioritarie",
        data_caveats_title="Note sui Dati",
        ai_insights="Insight dall'Analisi AI", ai_recs="Raccomandazioni",
        upgrade="Passa al piano Core per ricevere insight e raccomandazioni AI personalizzate.",
        footer="Generato da AFianco — afianco.app",
        # Rule-based interpretations
        verdict_loss="Le uscite ({outflows}) superano i ricavi ({sales}). Il margine e' {margin}%. La voce principale di costo e' {top_cost} ({top_cost_pct}% delle uscite).",
        verdict_thin="Il margine e' positivo ma sottile ({margin}%). I ricavi coprono i costi ma con poco margine di manovra.",
        verdict_decent="Il margine e' discreto ({margin}%). L'azienda genera valore ma c'e' spazio di miglioramento.",
        verdict_solid="Il margine e' solido ({margin}%). L'azienda e' in buona salute finanziaria.",
        trend_down="I ricavi sono in calo del {pct}% rispetto al periodo precedente.",
        trend_up="I ricavi sono in crescita del {pct}%.",
        trend_stable="I ricavi sono stabili rispetto al periodo precedente.",
        dso_zero="Non risultano crediti aperti — verifica se stai tracciando lo stato dei pagamenti.",
        dso_good="I clienti pagano in media in {dso} giorni. Il ciclo di incasso e' nella norma.",
        dso_warning="I clienti impiegano {dso} giorni a pagare — valuta solleciti per accorciare i tempi.",
        autonomy_critical="L'autonomia finanziaria e' critica ({days} giorni). Riduci le uscite non essenziali.",
        autonomy_ok="L'autonomia finanziaria e' di {days} giorni.",
        yoy_better="Rispetto allo stesso periodo dell'anno scorso, i ricavi sono cresciuti del {pct}%.",
        yoy_worse="Rispetto allo stesso periodo dell'anno scorso, i ricavi sono calati del {pct}%.",
        trend_monthly_down="Il margine e' in calo costante. La causa principale va ricercata nella dinamica dei costi rispetto ai ricavi.",
        trend_monthly_up="Il margine e' in miglioramento. Il trend e' positivo.",
        supplier_h="Fornitore", amount_h="Importo", share_h="Quota",
        top_suppliers_title="Top Fornitori",
        # Wave 12.D — cross-module sections
        customers_title="Clienti",
        cust_total="Clienti totali", cust_new="Nuovi nel periodo",
        cust_concentration="Concentrazione top 5",
        cust_churn_risk="A rischio churn (score >=60)",
        cust_avg_clv="Valore medio cliente (CLV)",
        cust_top_title="Top 5 clienti per fatturato",
        cust_name_h="Cliente", cust_revenue_h="Fatturato lifetime",
        cust_segment_h="Segmento",
        products_title="Catalogo Prodotti",
        prod_total="Prodotti totali", prod_avg_margin="Margine medio",
        prod_low_margin="A basso margine (<15%)",
        prod_declining="In declino (-10% in 30gg)",
        prod_dormant="Dormienti (60+ giorni)",
        prod_top_title="Top 5 prodotti per ricavo recente",
        prod_name_h="Prodotto", prod_revenue_h="Ricavo",
        prod_units_h="Unita'",
        commerce_title="Ordini & Vendite",
        comm_orders="Ordini nel periodo", comm_orders_prev="Periodo precedente",
        comm_aov="Valore medio ordine (AOV)",
        comm_aov_trend="Trend AOV vs precedente",
        comm_cancel="Tasso cancellazione",
        comm_draft="Ordini in bozza (cash at risk)",
        comm_channels_title="Top 3 canali",
        comm_channel_h="Canale", comm_count_h="Ordini",
    ),
    "en": dict(
        weekly="Weekly Report", monthly="Monthly Report", custom="Report",
        period="Period", verdict_title="Overview",
        kpi_title="Period Numbers", metric="Metric", current="Current",
        previous="Previous", change="Change",
        rev="Revenue", opex="Operating expenses", purch="Supplier purchases",
        fixed="Fixed costs", tot_out="Total outflows", net="Net result",
        margin="Operating margin",
        outflow_title="Where the Money Goes",
        trend_title="Monthly Trend", month_h="Month", trend_h="Trend",
        yoy_title="Year-over-Year Comparison", yoy_cur="Current", yoy_prev="Last year",
        cash_title="Cash Cycle & Liquidity",
        dso="DSO (Days to collect)", dpo="DPO (Days to pay)",
        ccc="Cash conversion cycle", autonomy="Days of autonomy",
        burn="Burn rate /day", be="Break-even", days="days", na="N/A",
        charts_title="Visual Analysis", daily="Daily Trend",
        cumul="Cumulative Cashflow",
        top_rev="Top Revenue Categories", top_exp="Top Expense Categories",
        assess_title="Situation Assessment",
        assess_critical="The situation requires immediate attention.",
        assess_warning="The situation is under observation.",
        assess_good="The situation is good.",
        assess_ok="Everything is under control. No critical issues detected.",
        health_dim_title="Health Score — Breakdown by Dimension",
        dim="Dimension", score="Score", status="Status",
        priority_title="Priority Actions",
        data_caveats_title="Data Notes",
        ai_insights="AI Analysis Insights", ai_recs="Recommendations",
        upgrade="Upgrade to Core for personalized AI insights and recommendations.",
        footer="Generated by AFianco — afianco.app",
        verdict_loss="Outflows ({outflows}) exceed revenue ({sales}). Margin is {margin}%. The main cost driver is {top_cost} ({top_cost_pct}% of outflows).",
        verdict_thin="Margin is positive but thin ({margin}%). Revenue covers costs with little room to maneuver.",
        verdict_decent="Margin is decent ({margin}%). The business generates value but there's room for improvement.",
        verdict_solid="Margin is solid ({margin}%). The business is in good financial health.",
        trend_down="Revenue declined {pct}% compared to the previous period.",
        trend_up="Revenue grew {pct}%.",
        trend_stable="Revenue is stable compared to the previous period.",
        dso_zero="No open receivables — verify if you are tracking payment status.",
        dso_good="Customers pay on average in {dso} days. Collection cycle is normal.",
        dso_warning="Customers take {dso} days to pay — consider follow-ups to shorten the cycle.",
        autonomy_critical="Financial autonomy is critical ({days} days). Reduce non-essential expenses.",
        autonomy_ok="Financial autonomy is {days} days.",
        yoy_better="Compared to the same period last year, revenue grew {pct}%.",
        yoy_worse="Compared to the same period last year, revenue declined {pct}%.",
        trend_monthly_down="Margin is consistently declining. The main cause is the cost dynamics relative to revenue.",
        trend_monthly_up="Margin is improving. The trend is positive.",
        supplier_h="Supplier", amount_h="Amount", share_h="Share",
        top_suppliers_title="Top Suppliers",
        # Wave 12.D — cross-module sections
        customers_title="Customers",
        cust_total="Total customers", cust_new="New in period",
        cust_concentration="Top 5 concentration",
        cust_churn_risk="At churn risk (score >=60)",
        cust_avg_clv="Average customer value (CLV)",
        cust_top_title="Top 5 customers by lifetime revenue",
        cust_name_h="Customer", cust_revenue_h="Lifetime revenue",
        cust_segment_h="Segment",
        products_title="Product Catalog",
        prod_total="Total products", prod_avg_margin="Average margin",
        prod_low_margin="Low margin (<15%)",
        prod_declining="Declining (-10% in 30d)",
        prod_dormant="Dormant (60+ days)",
        prod_top_title="Top 5 products by recent revenue",
        prod_name_h="Product", prod_revenue_h="Revenue",
        prod_units_h="Units",
        commerce_title="Orders & Sales",
        comm_orders="Orders in period", comm_orders_prev="Previous period",
        comm_aov="Average order value (AOV)",
        comm_aov_trend="AOV trend vs previous",
        comm_cancel="Cancellation rate",
        comm_draft="Draft orders (cash at risk)",
        comm_channels_title="Top 3 channels",
        comm_channel_h="Channel", comm_count_h="Orders",
    ),
    "de": dict(
        weekly="Wochenbericht", monthly="Monatsbericht", custom="Bericht",
        period="Zeitraum", verdict_title="Ueberblick",
        kpi_title="Zahlen des Zeitraums", metric="Kennzahl", current="Aktuell",
        previous="Vorperiode", change="Veraenderung",
        rev="Einnahmen", opex="Betriebsausgaben", purch="Lieferanteneinkaufe",
        fixed="Fixkosten", tot_out="Gesamtausgaben", net="Nettoergebnis",
        margin="Betriebsmarge",
        outflow_title="Wohin das Geld fliesst",
        trend_title="Monatstrend", month_h="Monat", trend_h="Trend",
        yoy_title="Jahresvergleich", yoy_cur="Aktuell", yoy_prev="Vorjahr",
        cash_title="Cash-Zyklus & Liquiditaet",
        dso="DSO (Inkassotage)", dpo="DPO (Zahlungstage)",
        ccc="Cash Conversion Cycle", autonomy="Autonomietage",
        burn="Burn Rate /Tag", be="Break-even", days="Tage", na="k.A.",
        charts_title="Visuelle Analyse", daily="Tagesverlauf",
        cumul="Kumulierter Cashflow",
        top_rev="Top Einnahmekategorien", top_exp="Top Ausgabenkategorien",
        assess_title="Situationsbewertung",
        assess_critical="Die Situation erfordert sofortiges Handeln.",
        assess_warning="Die Situation steht unter Beobachtung.",
        assess_good="Die Situation ist gut.",
        assess_ok="Alles unter Kontrolle. Keine kritischen Probleme erkannt.",
        health_dim_title="Health Score — Aufschluesselung",
        dim="Dimension", score="Punkte", status="Status",
        priority_title="Prioritaere Massnahmen",
        data_caveats_title="Datenhinweise",
        ai_insights="KI-Analyse-Insights", ai_recs="Empfehlungen",
        upgrade="Upgrade auf Core fuer personalisierte KI-Insights.",
        footer="Erstellt von AFianco — afianco.app",
        verdict_loss="Die Ausgaben ({outflows}) uebersteigen die Einnahmen ({sales}). Die Marge betraegt {margin}%. Der Hauptkostentreiber ist {top_cost} ({top_cost_pct}% der Ausgaben).",
        verdict_thin="Die Marge ist positiv aber duenn ({margin}%).",
        verdict_decent="Die Marge ist ordentlich ({margin}%).",
        verdict_solid="Die Marge ist solide ({margin}%).",
        trend_down="Die Einnahmen sind um {pct}% gesunken.",
        trend_up="Die Einnahmen sind um {pct}% gestiegen.",
        trend_stable="Die Einnahmen sind stabil.",
        dso_zero="Keine offenen Forderungen — pruefen Sie, ob Zahlungsstatus erfasst wird.",
        dso_good="Kunden zahlen im Durchschnitt in {dso} Tagen.",
        dso_warning="Kunden benoetigen {dso} Tage zum Zahlen — Mahnungen erwaegen.",
        autonomy_critical="Finanzielle Autonomie ist kritisch ({days} Tage).",
        autonomy_ok="Finanzielle Autonomie: {days} Tage.",
        yoy_better="Im Vergleich zum Vorjahr sind die Einnahmen um {pct}% gestiegen.",
        yoy_worse="Im Vergleich zum Vorjahr sind die Einnahmen um {pct}% gesunken.",
        trend_monthly_down="Die Marge sinkt kontinuierlich.",
        trend_monthly_up="Die Marge verbessert sich.",
        supplier_h="Lieferant", amount_h="Betrag", share_h="Anteil",
        top_suppliers_title="Top Lieferanten",
        # Wave 12.D — cross-module sections
        customers_title="Kunden",
        cust_total="Kunden gesamt", cust_new="Neu im Zeitraum",
        cust_concentration="Top-5-Konzentration",
        cust_churn_risk="Churn-Risiko (Score >=60)",
        cust_avg_clv="Durchschnittlicher Kundenwert (CLV)",
        cust_top_title="Top 5 Kunden nach Lifetime-Umsatz",
        cust_name_h="Kunde", cust_revenue_h="Lifetime-Umsatz",
        cust_segment_h="Segment",
        products_title="Produktkatalog",
        prod_total="Produkte gesamt", prod_avg_margin="Durchschnittliche Marge",
        prod_low_margin="Niedrige Marge (<15%)",
        prod_declining="Rueckl\u00e4ufig (-10% in 30T)",
        prod_dormant="Ruhend (60+ Tage)",
        prod_top_title="Top 5 Produkte nach j\u00fcngstem Umsatz",
        prod_name_h="Produkt", prod_revenue_h="Umsatz",
        prod_units_h="Einheiten",
        commerce_title="Bestellungen & Verk\u00e4ufe",
        comm_orders="Bestellungen im Zeitraum", comm_orders_prev="Vorperiode",
        comm_aov="Durchschnittlicher Bestellwert (AOV)",
        comm_aov_trend="AOV-Trend ggue. Vorperiode",
        comm_cancel="Stornoquote",
        comm_draft="Entwurfsbestellungen (Cash at Risk)",
        comm_channels_title="Top 3 Kan\u00e4le",
        comm_channel_h="Kanal", comm_count_h="Bestellungen",
    ),
    "fr": dict(
        weekly="Rapport Hebdomadaire", monthly="Rapport Mensuel", custom="Rapport",
        period="Periode", verdict_title="Vue d'ensemble",
        kpi_title="Chiffres de la Periode", metric="Indicateur", current="Actuel",
        previous="Precedent", change="Variation",
        rev="Revenus", opex="Charges d'exploitation", purch="Achats fournisseurs",
        fixed="Charges fixes", tot_out="Sorties totales", net="Resultat net",
        margin="Marge operationnelle",
        outflow_title="Repartition des Sorties",
        trend_title="Tendance Mensuelle", month_h="Mois", trend_h="Tendance",
        yoy_title="Comparaison Annuelle", yoy_cur="Actuel", yoy_prev="Annee precedente",
        cash_title="Cycle de Tresorerie & Liquidite",
        dso="DSO (Delai encaissement)", dpo="DPO (Delai paiement)",
        ccc="Cycle de conversion", autonomy="Jours d'autonomie",
        burn="Burn rate /jour", be="Seuil de rentabilite", days="jours", na="N/D",
        charts_title="Analyse Visuelle", daily="Tendance Quotidienne",
        cumul="Cashflow Cumule",
        top_rev="Top Categories Revenus", top_exp="Top Categories Depenses",
        assess_title="Evaluation de la Situation",
        assess_critical="La situation necessite une attention immediate.",
        assess_warning="La situation est sous observation.",
        assess_good="La situation est bonne.",
        assess_ok="Tout est sous controle. Aucun probleme critique detecte.",
        health_dim_title="Health Score — Detail par Dimension",
        dim="Dimension", score="Score", status="Statut",
        priority_title="Actions Prioritaires",
        data_caveats_title="Notes sur les Donnees",
        ai_insights="Insights de l'Analyse IA", ai_recs="Recommandations",
        upgrade="Passez a Core pour des insights IA personnalises.",
        footer="Genere par AFianco — afianco.app",
        verdict_loss="Les sorties ({outflows}) depassent les revenus ({sales}). La marge est de {margin}%. Le principal poste de cout est {top_cost} ({top_cost_pct}% des sorties).",
        verdict_thin="La marge est positive mais fine ({margin}%).",
        verdict_decent="La marge est correcte ({margin}%).",
        verdict_solid="La marge est solide ({margin}%).",
        trend_down="Les revenus ont baisse de {pct}%.",
        trend_up="Les revenus ont augmente de {pct}%.",
        trend_stable="Les revenus sont stables.",
        dso_zero="Pas de creances ouvertes — verifiez si le statut de paiement est suivi.",
        dso_good="Les clients paient en moyenne en {dso} jours.",
        dso_warning="Les clients mettent {dso} jours a payer — envisagez des relances.",
        autonomy_critical="L'autonomie financiere est critique ({days} jours).",
        autonomy_ok="Autonomie financiere : {days} jours.",
        yoy_better="Par rapport a la meme periode l'annee derniere, les revenus ont augmente de {pct}%.",
        yoy_worse="Par rapport a la meme periode l'annee derniere, les revenus ont baisse de {pct}%.",
        trend_monthly_down="La marge est en baisse constante.",
        trend_monthly_up="La marge s'ameliore.",
        supplier_h="Fournisseur", amount_h="Montant", share_h="Part",
        top_suppliers_title="Top Fournisseurs",
        # Wave 12.D — cross-module sections
        customers_title="Clients",
        cust_total="Clients totaux", cust_new="Nouveaux dans la p\u00e9riode",
        cust_concentration="Concentration top 5",
        cust_churn_risk="Risque de churn (score >=60)",
        cust_avg_clv="Valeur client moyenne (CLV)",
        cust_top_title="Top 5 clients par CA lifetime",
        cust_name_h="Client", cust_revenue_h="CA lifetime",
        cust_segment_h="Segment",
        products_title="Catalogue Produits",
        prod_total="Produits totaux", prod_avg_margin="Marge moyenne",
        prod_low_margin="Faible marge (<15%)",
        prod_declining="En d\u00e9clin (-10% en 30j)",
        prod_dormant="Dormants (60+ jours)",
        prod_top_title="Top 5 produits par CA r\u00e9cent",
        prod_name_h="Produit", prod_revenue_h="CA",
        prod_units_h="Unit\u00e9s",
        commerce_title="Commandes & Ventes",
        comm_orders="Commandes p\u00e9riode", comm_orders_prev="P\u00e9riode pr\u00e9c\u00e9dente",
        comm_aov="Panier moyen (AOV)",
        comm_aov_trend="Tendance AOV vs pr\u00e9c.",
        comm_cancel="Taux d'annulation",
        comm_draft="Brouillons (cash \u00e0 risque)",
        comm_channels_title="Top 3 canaux",
        comm_channel_h="Canal", comm_count_h="Commandes",
    ),
}

def _g(loc): return _T.get(loc, _T["it"])
def _eur(v):
    if v is None: return "N/D"
    v = float(v)
    if abs(v) >= 1e6: return f"EUR {v/1e6:,.1f}M"
    if abs(v) >= 1e3: return f"EUR {v:,.0f}"
    return f"EUR {v:,.2f}"
def _pchg(cur, prev):
    if not prev: return "—"
    p = ((cur-prev)/abs(prev))*100
    c = P["green"] if p >= 0 else P["red"]
    return f"<font color='{c}'>{p:+.1f}%</font>"

def _health_col(sc):
    if sc >= 70: return P["green"]
    if sc >= 40: return P["amber"]
    return P["red"]

def _mk_circle(sc, lbl=""):
    """Legacy small circle — kept for backward compat. New code should
    use _hero_gauge() (Wave 12.F)."""
    d = Drawing(55*mm, 30*mm)
    cx, cy, r = 27.5*mm, 17*mm, 11*mm
    col = _health_col(sc)
    d.add(Circle(cx, cy, r, fillColor=hc(col+"22"), strokeColor=hc(col), strokeWidth=2.5))
    d.add(Circle(cx, cy, r-2.5*mm, fillColor=colors.white, strokeColor=colors.white, strokeWidth=0))
    d.add(String(cx, cy-1.5*mm, str(sc), fontSize=18, fontName="Helvetica-Bold", fillColor=hc(col), textAnchor="middle"))
    d.add(String(cx, cy-7*mm, "/100", fontSize=7, fillColor=hc(P["gray"]), textAnchor="middle"))
    if lbl: d.add(String(cx, cy-11*mm, lbl, fontSize=7, fillColor=hc(P["gray"]), textAnchor="middle"))
    return d


# ─── Wave 12.F — new visual helpers ──────────────────────────────────────────
# These produce the "modern card" look that replaces the old bordered
# tables. All produce Flowable objects (Table, Drawing, Paragraph) ready
# to append to the PDF story.

def _hero_gauge(score, label=""):
    """Bigger health gauge for the cover hero card.

    Renders a 40mm × 40mm drawing: outer ring + inner score + label.
    The arc style + larger size makes the score a true cover element.
    """
    from reportlab.graphics.shapes import Wedge
    d = Drawing(50*mm, 50*mm)
    cx, cy = 25*mm, 25*mm
    r_outer = 22*mm
    r_inner = 18*mm
    col = _health_col(score) if score is not None else P["muted"]
    safe_score = max(0, min(100, int(score or 0)))

    # Background full ring (light tint)
    d.add(Circle(cx, cy, r_outer, fillColor=hc(col + "15"),
                  strokeColor=None, strokeWidth=0))
    # Arc progress: filled wedge from -90° going clockwise proportional to score
    # reportlab Wedge uses degrees, 0° = east, ccw positive.
    #
    # Bug workaround: reportlab.pdfgen.pdfgeom raises ZeroDivisionError
    # when the wedge extent is an exact multiple of 90° (the function
    # internally splits arcs into 90° fragments and the boundary case
    # triggers sin(0) in kappa computation). For score=25 (-90),
    # 50 (-180), 75 (-270), 100 (-360) we'd hit the singularity.
    # Nudge by half a degree to slip past the singular angle —
    # visually indistinguishable but reportlab-safe.
    start_angle = 90
    extent = -(safe_score / 100.0) * 360
    if abs(extent) > 0.1:
        if abs(extent) % 90 < 0.5:
            extent += -0.5 if extent < 0 else 0.5
        d.add(Wedge(cx, cy, r_outer, start_angle, extent,
                     fillColor=hc(col), strokeColor=None, strokeWidth=0))
    # Inner white disc to make it a "ring"
    d.add(Circle(cx, cy, r_inner, fillColor=colors.white,
                  strokeColor=None, strokeWidth=0))
    # Score number
    d.add(String(cx, cy + 0.5*mm, str(safe_score),
                  fontSize=28, fontName="Helvetica-Bold",
                  fillColor=hc(col), textAnchor="middle"))
    # /100 underneath
    d.add(String(cx, cy - 6.5*mm, "/ 100",
                  fontSize=8, fontName="Helvetica",
                  fillColor=hc(P["muted"]), textAnchor="middle"))
    if label:
        d.add(String(cx, cy - 11.5*mm, label.upper(),
                      fontSize=7, fontName="Helvetica-Bold",
                      fillColor=hc(col), textAnchor="middle"))
    return d


def _kpi_card(label, value, sub=None, value_color=None, w=None):
    """Wave 12.F — a single KPI as a soft-bordered card.

    Top: tiny grey label (uppercase, tracked).
    Middle: big bold value (dark or colored).
    Bottom (optional): tiny sub-text (trend %, "vs prev", etc.).

    Used in a Table[...] grid to form the KPI strip on P1.
    """
    if value_color is None:
        value_color = P["dark"]
    label_par = Paragraph(
        f"<font name='Helvetica-Bold' size='7' color='{P['muted']}'>{label.upper()}</font>",
        ParagraphStyle("KL", fontName="Helvetica-Bold", fontSize=7,
                       textColor=hc(P["muted"]), leading=9, spaceAfter=2),
    )
    value_par = Paragraph(
        f"<font name='Helvetica-Bold' size='14' color='{value_color}'>{value}</font>",
        ParagraphStyle("KV", fontName="Helvetica-Bold", fontSize=14,
                       textColor=hc(value_color), leading=16),
    )
    cell = [label_par, value_par]
    if sub:
        cell.append(Paragraph(
            f"<font name='Helvetica' size='7' color='{P['muted']}'>{sub}</font>",
            ParagraphStyle("KS", fontName="Helvetica", fontSize=7,
                            textColor=hc(P["muted"]), leading=9, spaceBefore=1),
        ))
    t = Table([[cell]], colWidths=[w or 40*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), hc(P["white"])),
        ("BOX", (0,0), (-1,-1), 0.6, hc(P["border"])),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("TOPPADDING", (0,0), (-1,-1), 3.5*mm),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3.5*mm),
        ("LEFTPADDING", (0,0), (-1,-1), 4*mm),
        ("RIGHTPADDING", (0,0), (-1,-1), 4*mm),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    return t


def _kpi_strip(cards, cols=4):
    """Arrange KPI cards in a horizontal grid.

    Pad with empty cells if fewer than `cols` cards.
    """
    while len(cards) < cols:
        cards.append("")
    col_w = (CW - (cols - 1) * 2*mm) / cols
    # Re-render each card at the correct width
    sized = []
    for c in cards:
        if isinstance(c, Table):
            c._argW = [col_w]  # type: ignore[attr-defined]
            sized.append(c)
        else:
            sized.append("")
    # Layout in a wrapper Table with small horizontal gutters
    row = []
    widths = []
    for i, c in enumerate(sized):
        row.append(c)
        widths.append(col_w)
        if i < cols - 1:
            row.append("")
            widths.append(2*mm)
    wrapper = Table([row], colWidths=widths)
    wrapper.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return wrapper


def _stacked_bar(segments, total_width=None, height=6*mm):
    """Wave 12.F — single horizontal stacked bar with colored segments.

    Replaces the old "3 separate bars" outflow breakdown — single bar
    that visually represents proportions is much more modern.

    Args:
        segments: list of (label, value, color, tint)
    Returns a Table with the bar + labels underneath.
    """
    total = sum(s[1] for s in segments if s[1] and s[1] > 0)
    if total <= 0:
        return Spacer(1, 0)
    total_width = total_width or CW
    # Use a single Table row, each cell being a colored stripe.
    # Skip segments with 0 width.
    bar_cells = []
    bar_widths = []
    bar_styles = []
    for i, (label, value, color, tint) in enumerate(segments):
        if value <= 0:
            continue
        w = total_width * (value / total)
        bar_cells.append("")
        bar_widths.append(w)
        bar_styles.append(("BACKGROUND", (len(bar_cells)-1, 0),
                            (len(bar_cells)-1, 0), hc(color)))

    if not bar_cells:
        return Spacer(1, 0)
    bar = Table([bar_cells], colWidths=bar_widths, rowHeights=[height])
    bar.setStyle(TableStyle([
        *bar_styles,
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    return bar


def _stacked_bar_legend(segments):
    """Three-column legend row under a stacked bar.

    Each segment shows a colored dot + label + % + absolute value.
    """
    total = sum(s[1] for s in segments if s[1] and s[1] > 0)
    if total <= 0:
        return Spacer(1, 0)
    items = []
    for label, value, color, tint in segments:
        if value <= 0:
            continue
        pct = (value / total) * 100
        # Colored dot via inline font HTML
        dot = f"<font color='{color}'>●</font>"
        items.append(
            Paragraph(
                f"<font size='7' color='{P['muted']}'><b>{dot} {label.upper()}</b></font><br/>"
                f"<font size='9' color='{P['dark']}'><b>{_eur(value)}</b></font> "
                f"<font size='8' color='{P['muted']}'>({pct:.0f}%)</font>",
                ParagraphStyle("LegItem", fontName="Helvetica", fontSize=8,
                                leading=11),
            )
        )
    if not items:
        return Spacer(1, 0)
    # Distribute evenly across CW
    col_w = CW / len(items)
    row = items
    wrapper = Table([row], colWidths=[col_w] * len(items))
    wrapper.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 2*mm),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1*mm),
        ("LEFTPADDING", (0,0), (-1,-1), 1*mm),
        ("RIGHTPADDING", (0,0), (-1,-1), 1*mm),
    ]))
    return wrapper


def _dimension_progress(name, points, max_pts, level=""):
    """Wave 12.F — horizontal progress bar for a health dimension.

    Replaces the old bordered dimensions table. Each row:
        [Dimension name]            [N/max]
        [██████░░░░░░░░░░░░░░]      [LEVEL chip]
    """
    if points is None:
        # not_computable
        col = P["muted"]
        pct = 0
        label_right = "N/D"
        chip = f"<font color='{P['muted']}' size='7'><b>N/D</b></font>"
    else:
        col = {"excellent": P["green"], "ok": P["green"],
                "warning": P["amber"], "critical": P["red"]}.get(level, P["muted"])
        pct = (points / max_pts) * 100 if max_pts else 0
        label_right = f"{points}/{max_pts}"
        chip = f"<font color='{col}' size='7'><b>{(level or '?').upper()}</b></font>"

    # Bar: 2 cells side-by-side (filled + empty) — horizontal progress
    bar_w = CW * 0.55
    fill_w = bar_w * (pct / 100)
    empty_w = bar_w - fill_w
    if fill_w <= 0.01:
        fill_w = 0.01  # min positive value reportlab accepts
        empty_w = bar_w - 0.01
    bar = Table([["", ""]], colWidths=[fill_w, empty_w], rowHeights=[3.5*mm])
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), hc(col)),
        ("BACKGROUND", (1,0), (1,0), hc(P["borderS"])),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))

    name_par = Paragraph(
        f"<font name='Helvetica-Bold' size='9' color='{P['dark']}'>{name}</font>",
        ParagraphStyle("DimN", fontName="Helvetica-Bold", fontSize=9, leading=11),
    )
    right_par = Paragraph(
        f"<font name='Helvetica-Bold' size='9' color='{P['dark']}'>{label_right}</font> &nbsp; {chip}",
        ParagraphStyle("DimR", fontName="Helvetica", fontSize=9, leading=11),
    )

    # Layout: name on left, bar on right
    row1 = Table([[name_par, right_par]], colWidths=[CW * 0.55, CW * 0.45])
    row1.setStyle(TableStyle([
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1*mm),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
    ]))
    return [row1, bar, Spacer(1, 2.5*mm)]


def _action_badge(idx, text):
    """Wave 12.F — numbered priority action with a circled badge.

    Visual match for the frontend's PriorityActionsPanel.
    Index 1 = red (top priority), 2 = amber, 3 = blue, 4 = green.
    """
    badge_colors = [P["red"], P["amber"], P["blue"], P["green"]]
    bc = badge_colors[min(max(idx - 1, 0), 3)]

    # Circled number via Drawing
    d = Drawing(7*mm, 7*mm)
    d.add(Circle(3.5*mm, 3.5*mm, 3*mm, fillColor=hc(bc),
                  strokeColor=hc(bc), strokeWidth=0))
    d.add(String(3.5*mm, 2*mm, str(idx),
                  fontSize=9, fontName="Helvetica-Bold",
                  fillColor=colors.white, textAnchor="middle"))

    text_par = Paragraph(
        f"<font size='9' color='{P['darkS']}'>{text}</font>",
        ParagraphStyle("Act", fontName="Helvetica", fontSize=9, leading=12),
    )

    row = Table([[d, text_par]], colWidths=[8*mm, CW - 10*mm])
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (0,0), "TOP"),
        ("VALIGN", (1,0), (1,0), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 1.5*mm),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1.5*mm),
    ]))
    return row


def _section_title(text, accent=None):
    """Wave 12.F — section header.

    Thin uppercase tracked title with a 12mm accent line underneath
    instead of the old bold-blue heading style.
    """
    if accent is None:
        accent = P["blue"]
    title = Paragraph(
        f"<font name='Helvetica-Bold' size='10' color='{P['dark']}'>"
        f"{text.upper()}</font>",
        ParagraphStyle("Sec12F", fontName="Helvetica-Bold", fontSize=10,
                       textColor=hc(P["dark"]), leading=12, spaceBefore=5*mm,
                       spaceAfter=0),
    )
    # Accent line — short colored bar underneath
    accent_line = HRFlowable(width=14*mm, thickness=1.5,
                              color=hc(accent), spaceBefore=1, spaceAfter=2.5*mm,
                              hAlign="LEFT")
    return [title, accent_line]

# ── Interpretation engine ────────────────────────────────────────────────────
def _build_verdict(kpis, t, overview):
    """Generate rule-based interpretive paragraphs.

    v14.2 fix (P2.4a): the verdict was reading ``operating_margin_pct``
    only — a metric that does NOT include fixed costs. For an org with
    sales=1k, variable=0, fixed=1k the operating margin is 100% but
    ``net_after_fixed`` is 0. The "margine solido 100%" narrative
    contradicted the health score (which DOES include fixed costs).

    We now drive the verdict from the *bottom-line* margin (net after
    fixed costs / sales). The operating margin is shown as nuance in
    the existing KPI table; here we only narrate the actually-relevant
    picture for cash health. This eliminates the Demo Restaurant
    "100% solid" + "13/100 critico" contradiction.
    """
    lines = []
    sales = kpis.get("total_sales", 0)
    outflows = kpis.get("total_outflows", 0)
    exp = kpis.get("total_expenses", 0)
    purch = kpis.get("supplier_purchases", 0)
    fixed = kpis.get("fixed_costs_total", 0)

    # Bottom-line margin = (sales - total_outflows) / sales × 100.
    # ``total_outflows`` ALREADY includes variable + purchases + fixed
    # (it's computed in snapshot_builder as sum of all three). This is
    # the metric the health score keys on, so narrating against it
    # eliminates the "margine solido 100% + health critico 13/100"
    # contradiction that came from using operating_margin_pct (which
    # excludes fixed costs).
    if sales and sales > 0:
        bottom_margin = round((sales - outflows) / sales * 100, 1)
    else:
        bottom_margin = kpis.get("operating_margin_pct", 0)

    margin = bottom_margin  # what we narrate against

    # Top cost driver
    costs = [("opex", exp), ("purch", purch), ("fixed", fixed)]
    costs.sort(key=lambda x: -x[1])
    top_name = {"opex": t["opex"], "purch": t["purch"], "fixed": t["fixed"]}.get(costs[0][0], "?")
    top_pct = int((costs[0][1] / outflows * 100) if outflows else 0)

    # Margin verdict — now based on bottom-line (net after fixed costs)
    if margin is not None and margin < 0:
        lines.append(t["verdict_loss"].format(outflows=_eur(outflows), sales=_eur(sales),
                                               margin=f"{margin:.0f}", top_cost=top_name, top_cost_pct=top_pct))
    elif margin is not None and margin < 10:
        lines.append(t["verdict_thin"].format(margin=f"{margin:.1f}"))
    elif margin is not None and margin < 25:
        lines.append(t["verdict_decent"].format(margin=f"{margin:.1f}"))
    elif margin is not None:
        lines.append(t["verdict_solid"].format(margin=f"{margin:.1f}"))

    # Revenue trend
    sales_trend = kpis.get("sales_trend_pct", 0) or 0
    if sales_trend < -10:
        lines.append(t["trend_down"].format(pct=f"{abs(sales_trend):.0f}"))
    elif sales_trend > 10:
        lines.append(t["trend_up"].format(pct=f"{sales_trend:.0f}"))
    else:
        lines.append(t["trend_stable"])

    # DSO
    dso = kpis.get("dso", 0) or 0
    if dso == 0:
        lines.append(t["dso_zero"])
    elif dso > 45:
        lines.append(t["dso_warning"].format(dso=f"{dso:.0f}"))
    elif dso > 0:
        lines.append(t["dso_good"].format(dso=f"{dso:.0f}"))

    # Autonomy
    autonomy = kpis.get("giorni_autonomia", 0) or 0
    if 0 < autonomy < 30:
        lines.append(t["autonomy_critical"].format(days=f"{autonomy:.0f}"))
    elif autonomy >= 30:
        lines.append(t["autonomy_ok"].format(days=f"{autonomy:.0f}"))

    return " ".join(lines)


def _build_assessment(health, alerts, kpis, t):
    """Build situation assessment — holistic, not just alert-based."""
    sc = health.get("score", 0)
    margin = kpis.get("operating_margin_pct", 0) or 0
    alert_count = len(alerts)
    high_count = sum(1 for a in alerts if a.get("severity") == "high")

    if sc < 40 or margin < 0:
        base = t["assess_critical"]
        issues = health.get("top_issues", [])
        if issues:
            issue_names = [i.get("dimension", "") for i in issues[:3]]
            base += f" Aree critiche: {', '.join(issue_names)}."
        if margin < 0:
            base += f" Il margine e' negativo ({margin:.0f}%)."
        return base, "critical"
    elif sc < 70 or high_count > 0:
        base = t["assess_warning"]
        if high_count:
            base += f" {high_count} alert ad alta priorita' richiedono attenzione."
        return base, "warning"
    elif alert_count > 0:
        base = t["assess_good"]
        base += f" {alert_count} alert attivi di cui nessuno critico."
        return base, "good"
    else:
        return t["assess_ok"], "ok"


def build_report_pdf(
    org_name: str, period_label: str, digest_type: str,
    kpis: dict, health: dict, charts: Dict[str, bytes],
    alerts: List[dict],
    insights: Optional[List[str]], recommendations: Optional[List[str]],
    locale: str = "it", is_starter: bool = False,
    overview: Optional[dict] = None,
) -> bytes:
    t = _g(locale)
    ov = overview or {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MG, rightMargin=MG,
                            topMargin=10*mm, bottomMargin=10*mm)

    # ── Styles (Wave 12.F refresh) ───────────────────────────────────────
    # Cleaner typography hierarchy:
    #   Headline (org name)     14pt bold dark
    #   Masthead label          7pt uppercase grey
    #   Section title           10pt uppercase tracked
    #   Body                    10pt regular dark
    #   Caption / sub           8pt regular muted
    #   Footer                  6pt centered muted
    st = getSampleStyleSheet()
    def _add(name, **kw): st.add(ParagraphStyle(name, **kw))
    # Headline (organization name on cover)
    _add("Headline", fontName="Helvetica-Bold", fontSize=18,
         textColor=hc(P["dark"]), leading=22, spaceAfter=1*mm)
    # Masthead small label (above the headline)
    _add("Masthead", fontName="Helvetica-Bold", fontSize=8,
         textColor=hc(P["muted"]), leading=10, spaceAfter=1*mm)
    # Period subtitle (under the headline)
    _add("Period", fontName="Helvetica", fontSize=9,
         textColor=hc(P["muted"]), leading=12, spaceAfter=5*mm)
    # Section title (legacy "Sec" — kept name for backward compat
    # with the cross-module sections that still call sec(...))
    _add("Sec", fontName="Helvetica-Bold", fontSize=10,
         textColor=hc(P["dark"]), leading=12,
         spaceBefore=6*mm, spaceAfter=1*mm,
         textTransform=None,  # uppercase done in body via .upper()
         )
    # Body
    _add("Body", fontName="Helvetica", fontSize=10, leading=14,
         textColor=hc(P["darkS"]))
    _add("BodyL", fontName="Helvetica", fontSize=11, leading=15,
         textColor=hc(P["darkS"]))
    _add("BodyS", fontName="Helvetica", fontSize=8, leading=11,
         textColor=hc(P["muted"]))
    _add("Verdict", fontName="Helvetica", fontSize=10.5, leading=15,
         textColor=hc(P["darkS"]))
    _add("Ftr", fontName="Helvetica", fontSize=6, textColor=hc(P["muted"]),
         alignment=TA_CENTER, spaceBefore=3*mm)
    _add("CTA", fontName="Helvetica-Oblique", fontSize=9,
         textColor=hc(P["blue"]), alignment=TA_CENTER, spaceBefore=5*mm)

    TH = ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)
    TD = ParagraphStyle("TD", fontName="Helvetica", fontSize=9, leading=12)
    TDB = ParagraphStyle("TDB", fontName="Helvetica-Bold", fontSize=9, leading=12)
    # Wave 12.F — clean table header (uppercase grey on light bg, no white-on-blue)
    TH_C = ParagraphStyle("TH_C", fontName="Helvetica-Bold", fontSize=7,
                           textColor=hc(P["muted"]), leading=10)

    def sec(txt): return Paragraph(txt, st["Sec"])
    def body(txt): return Paragraph(txt, st["Body"])
    def note(txt): return Paragraph(txt, st["BodyS"])
    def sp(h=4): return Spacer(1, h*mm)

    # Wave 12.F — clean borderless table style used by all "top X" lists
    # (no grid lines, just bottom-border on header + alternating row bg)
    def _clean_table_style(n_cols=None):
        return TableStyle([
            ("BACKGROUND", (0,0), (-1,0), hc(P["page"])),
            ("LINEBELOW", (0,0), (-1,0), 1, hc(P["border"])),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [hc(P["white"]), hc(P["page"])]),
            ("TOPPADDING", (0,0), (-1,-1), 2.5*mm),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2.5*mm),
            ("LEFTPADDING", (0,0), (-1,-1), 3*mm),
            ("RIGHTPADDING", (0,0), (-1,-1), 3*mm),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ])

    story = []

    # ═════════════════════════════════════════════════════════════════════
    # MASTHEAD (Wave 12.F — replaces the heavy blue header bar)
    # ═════════════════════════════════════════════════════════════════════
    rtype = {"weekly": t["weekly"], "monthly": t["monthly"]}.get(digest_type, t["custom"])
    # Thin top row: AFianco label + report-type chip on the right
    masthead_row = Table([[
        Paragraph(
            f"<font name='Helvetica-Bold' size='10' color='{P['dark']}'>AFianco</font>"
            f"&nbsp;&nbsp;<font color='{P['muted']}'>&middot;</font>&nbsp;&nbsp;"
            f"<font name='Helvetica' size='9' color='{P['muted']}'>{rtype}</font>",
            ParagraphStyle("MH", fontName="Helvetica", fontSize=10, leading=12),
        ),
        Paragraph(
            f"<font name='Helvetica' size='8' color='{P['muted']}'>{period_label}</font>",
            ParagraphStyle("MR", fontName="Helvetica", fontSize=8, leading=10,
                            alignment=TA_LEFT),
        ),
    ]], colWidths=[CW*0.65, CW*0.35])
    masthead_row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(masthead_row)
    story.append(HRFlowable(width="100%", thickness=0.6, color=hc(P["border"]),
                              spaceBefore=2*mm, spaceAfter=4*mm))
    # Org name as the headline
    story.append(Paragraph(org_name, st["Headline"]))
    story.append(sp(2))

    # ═════════════════════════════════════════════════════════════════════
    # P1 — EXECUTIVE HERO CARD
    # Wave 12.F — replaces the small circle + dense KPI table with a
    # high-impact cover that lets the merchant see the verdict in 3s.
    # ═════════════════════════════════════════════════════════════════════
    sc = health.get("score", 0)
    lbl = health.get("label", "")
    verdict_text = _build_verdict(kpis, t, ov)
    score_color = _health_col(sc) if sc is not None else P["muted"]

    # Verdict cell — bigger leading, clear typography
    verdict_inner = [
        Paragraph(
            f"<font name='Helvetica-Bold' size='8' color='{P['muted']}'>"
            f"{t['verdict_title'].upper()}</font>",
            ParagraphStyle("HL", fontName="Helvetica-Bold", fontSize=8,
                            textColor=hc(P["muted"]), leading=10, spaceAfter=2*mm),
        ),
        Paragraph(
            f"<font name='Helvetica' size='10.5' color='{P['darkS']}'>{verdict_text}</font>",
            ParagraphStyle("HV", fontName="Helvetica", fontSize=10.5,
                            textColor=hc(P["darkS"]), leading=15),
        ),
    ]

    hero = Table(
        [[_hero_gauge(sc, lbl), verdict_inner]],
        colWidths=[55*mm, CW - 55*mm],
    )
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), hc(P["white"])),
        ("BOX", (0,0), (-1,-1), 0.6, hc(P["border"])),
        ("LINEABOVE", (0,0), (-1,0), 2, hc(score_color)),  # top accent stripe
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 5*mm),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5*mm),
        ("LEFTPADDING", (0,0), (0,0), 3*mm),
        ("LEFTPADDING", (1,0), (1,0), 2*mm),
        ("RIGHTPADDING", (0,0), (-1,-1), 5*mm),
    ]))
    story.append(hero)
    story.append(sp(5))

    # ═════════════════════════════════════════════════════════════════════
    # P1 — KPI STRIP (Wave 12.F card grid)
    # Replaces the bordered metric table with 4 cards: Revenue, Outflows,
    # Net, Margin. Each shows label, value (color-coded for net/margin),
    # and a small "vs prev" trend line.
    # ═════════════════════════════════════════════════════════════════════
    sales = kpis.get("total_sales", 0)
    exp = kpis.get("total_expenses", 0)
    purch = kpis.get("supplier_purchases", 0)
    fixed = kpis.get("fixed_costs_total", 0)
    outflows = kpis.get("total_outflows", 0)
    net = kpis.get("net_after_fixed", 0)
    margin = kpis.get("operating_margin_pct", 0)
    ps = kpis.get("prev_total_sales", 0)
    pe = kpis.get("prev_total_expenses", 0)
    po = kpis.get("prev_total_outflows", 0)

    net_col = P["green"] if net >= 0 else P["red"]
    margin_col = P["green"] if (margin or 0) >= 10 else (
        P["amber"] if (margin or 0) >= 0 else P["red"]
    )

    def _trend_sub(cur, prev):
        if not prev or prev == 0:
            return None
        pct = ((cur - prev) / abs(prev)) * 100
        arrow = "&#9650;" if pct >= 0 else "&#9660;"
        col = P["green"] if pct >= 0 else P["red"]
        return f"<font color='{col}'>{arrow}</font> {abs(pct):.1f}% vs prev"

    kpi_cards = [
        _kpi_card(t["rev"], _eur(sales), sub=_trend_sub(sales, ps)),
        _kpi_card(t["tot_out"], _eur(outflows), sub=_trend_sub(outflows, po)),
        _kpi_card(t["net"], _eur(net), value_color=net_col),
        _kpi_card(t["margin"], f"{margin:.1f}%", value_color=margin_col),
    ]
    story.append(_kpi_strip(kpi_cards, cols=4))
    story.append(sp(5))

    # ═════════════════════════════════════════════════════════════════════
    # P1 — OUTFLOW BREAKDOWN (Wave 12.F — single stacked bar)
    # Was 3 separate horizontal bars. Now a single stacked bar with a
    # 3-segment legend underneath. Communicates proportions at a glance.
    # ═════════════════════════════════════════════════════════════════════
    if outflows > 0:
        story.extend(_section_title(t["outflow_title"]))
        segments = [
            (t["opex"],  exp,    P["red"],   P["redT"]),
            (t["purch"], purch,  P["amber"], P["amberT"]),
            (t["fixed"], fixed,  P["blue"],  P["blueT"]),
        ]
        story.append(_stacked_bar(segments))
        story.append(_stacked_bar_legend(segments))

    # ═════════════════════════════════════════════════════════════════════
    # PAGE 2 — BIG PICTURE
    # ═════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # Monthly trend from daily data
    daily_series = ov.get("charts", {}).get("daily_series", [])
    if daily_series:
        monthly = defaultdict(lambda: {"sales": 0, "expenses": 0, "purchases": 0})
        for pt in daily_series:
            m = pt.get("date", "")[:7]
            if m:
                monthly[m]["sales"] += pt.get("sales", 0)
                monthly[m]["expenses"] += pt.get("expenses", 0)
                monthly[m]["purchases"] += pt.get("purchases", 0)

        if monthly:
            story.extend(_section_title(t["trend_title"]))
            mrows = [[Paragraph(t["month_h"], TH_C), Paragraph(t["rev"], TH_C),
                       Paragraph(t["tot_out"], TH_C), Paragraph(t["margin"], TH_C),
                       Paragraph(t["trend_h"], TH_C)]]
            prev_margin = None
            for mo in sorted(monthly.keys())[-6:]:
                d = monthly[mo]
                s_val = d["sales"]
                o_val = d["expenses"] + d["purchases"]
                m_val = ((s_val - o_val) / s_val * 100) if s_val else 0
                arrow = "—"
                if prev_margin is not None:
                    if m_val > prev_margin + 1: arrow = f"<font color='{P['green']}'>&#9650;</font>"
                    elif m_val < prev_margin - 1: arrow = f"<font color='{P['red']}'>&#9660;</font>"
                    else: arrow = "&#9654;"
                prev_margin = m_val
                m_col = P["green"] if m_val >= 0 else P["red"]
                mrows.append([
                    Paragraph(mo, TD), Paragraph(_eur(s_val), TD),
                    Paragraph(_eur(o_val), TD),
                    Paragraph(f"<font color='{m_col}'>{m_val:.0f}%</font>", TDB),
                    Paragraph(arrow, TD),
                ])
            mtbl = Table(mrows, colWidths=[CW*0.18, CW*0.22, CW*0.22, CW*0.20, CW*0.18])
            mtbl.setStyle(_clean_table_style())
            story.append(mtbl)

            # Interpret trend
            margins = [((monthly[m]["sales"] - monthly[m]["expenses"] - monthly[m]["purchases"]) / monthly[m]["sales"] * 100)
                       if monthly[m]["sales"] else 0 for m in sorted(monthly.keys())[-3:]]
            if len(margins) >= 2 and all(margins[i] < margins[i-1] for i in range(1, len(margins))):
                story.append(note(f"<i>{t['trend_monthly_down']}</i>"))
            elif len(margins) >= 2 and all(margins[i] > margins[i-1] for i in range(1, len(margins))):
                story.append(note(f"<i>{t['trend_monthly_up']}</i>"))

    # YoY (Wave 12.F clean style)
    yoy = ov.get("yoy", {})
    if yoy.get("has_data"):
        story.append(sp(5))
        story.extend(_section_title(t["yoy_title"]))
        yoy_pct = yoy.get("pct", {})
        # column widths for the 4-column YoY table
        cw = [CW*0.35, CW*0.25, CW*0.20, CW*0.20]
        yoy_rows = [
            [Paragraph(t["metric"], TH_C), Paragraph(t["yoy_cur"], TH_C),
             Paragraph(t["yoy_prev"], TH_C), Paragraph(t["change"], TH_C)],
            [Paragraph(t["rev"], TD), Paragraph(_eur(sales), TDB),
             Paragraph(_eur(yoy.get("total_sales", 0)), TD),
             Paragraph(f"<font color='{P['green'] if (yoy_pct.get('sales',0) or 0) >= 0 else P['red']}'>{yoy_pct.get('sales',0) or 0:+.1f}%</font>", TD)],
            [Paragraph(t["tot_out"], TD), Paragraph(_eur(outflows), TD),
             Paragraph(_eur(yoy.get("total_outflows", 0)), TD),
             Paragraph(f"<font color='{P['red'] if (yoy_pct.get('outflows',0) or 0) > 0 else P['green']}'>{yoy_pct.get('outflows',0) or 0:+.1f}%</font>", TD)],
        ]
        ytbl = Table(yoy_rows, colWidths=cw)
        ytbl.setStyle(_clean_table_style())
        story.append(ytbl)
        # Interpret YoY
        yoy_s = yoy_pct.get("sales", 0) or 0
        if yoy_s > 0:
            story.append(note(f"<i>{t['yoy_better'].format(pct=f'{yoy_s:.0f}')}</i>"))
        elif yoy_s < 0:
            story.append(note(f"<i>{t['yoy_worse'].format(pct=f'{abs(yoy_s):.0f}')}</i>"))

    # Cash cycle (discursive) — Wave 12.F section title
    story.append(sp(5))
    story.extend(_section_title(t["cash_title"]))
    dso = kpis.get("dso", 0) or 0
    dpo = kpis.get("dpo", 0) or 0
    ccc = kpis.get("cash_conversion_cycle", 0) or 0
    auto = kpis.get("giorni_autonomia", 0) or 0
    burn = kpis.get("burn_rate_total", 0) or 0
    be = kpis.get("break_even")

    # Discursive paragraph
    cash_parts = []
    if dso == 0: cash_parts.append(t["dso_zero"])
    elif dso > 45: cash_parts.append(t["dso_warning"].format(dso=f"{dso:.0f}"))
    else: cash_parts.append(t["dso_good"].format(dso=f"{dso:.0f}"))
    if 0 < auto < 30: cash_parts.append(t["autonomy_critical"].format(days=f"{auto:.0f}"))
    elif auto >= 30: cash_parts.append(t["autonomy_ok"].format(days=f"{auto:.0f}"))
    story.append(body(" ".join(cash_parts)))
    story.append(sp(2))

    # Wave 12.F — cash cycle as 4 KPI cards in 2 rows instead of grid table
    def _dstr(v): return f"{v:.0f} {t['days']}" if v else t["na"]
    autonomy_col = (P["red"] if 0 < auto < 30 else
                     (P["green"] if auto >= 30 else P["dark"]))
    cash_cards_row1 = [
        _kpi_card(t["dso"], _dstr(dso)),
        _kpi_card(t["dpo"], _dstr(dpo)),
        _kpi_card(t["ccc"], _dstr(ccc)),
        _kpi_card(t["autonomy"], _dstr(auto), value_color=autonomy_col),
    ]
    story.append(_kpi_strip(cash_cards_row1, cols=4))
    story.append(sp(2))
    cash_cards_row2 = [
        _kpi_card(t["burn"], _eur(burn)),
        _kpi_card(t["be"], _eur(be) if be else t["na"]),
        _kpi_card("", ""),  # padding cell
        _kpi_card("", ""),  # padding cell
    ]
    # Render row 2 as 2 cards + 2 empties — skip empties visually
    cash_cards_row2 = [c for c in cash_cards_row2[:2]]
    while len(cash_cards_row2) < 4:
        cash_cards_row2.append("")
    story.append(_kpi_strip(cash_cards_row2, cols=4))

    # ═════════════════════════════════════════════════════════════════════
    # PAGE 3 — CHARTS (Wave 12.F section title style)
    # ═════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.extend(_section_title(t["charts_title"]))

    if charts.get("daily"):
        story.append(note(f"<b>{t['daily']}</b>"))
        story.append(sp(1))
        story.append(Image(io.BytesIO(charts["daily"]), width=CW, height=60*mm))
        story.append(sp(5))

    if charts.get("cumulative"):
        story.append(note(f"<b>{t['cumul']}</b>"))
        story.append(sp(1))
        story.append(Image(io.BytesIO(charts["cumulative"]), width=CW, height=50*mm))
        story.append(sp(5))

    ci = []
    if charts.get("categories_revenue"): ci.append((t["top_rev"], charts["categories_revenue"]))
    if charts.get("categories_expense"): ci.append((t["top_exp"], charts["categories_expense"]))
    if ci:
        hw = CW/2-2*mm
        ts = [Paragraph(f"<font size='8' color='{P['gray']}'><b>{c[0]}</b></font>", TD) for c in ci]
        ims = [Image(io.BytesIO(c[1]), width=hw, height=40*mm) for c in ci]
        if len(ci) == 2:
            story.append(Table([ts, ims], colWidths=[hw+2*mm, hw+2*mm]))
        else:
            story.append(ts[0]); story.append(ims[0])

    # ═════════════════════════════════════════════════════════════════════
    # PAGE 4 — ASSESSMENT + ACTIONS
    # ═════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # Situation assessment — Wave 12.F: cleaner callout (thin left bar +
    # very subtle tinted background, rounded corners)
    story.extend(_section_title(t["assess_title"]))
    assess_text, assess_level = _build_assessment(health, alerts, kpis, t)
    assess_bg = {"critical": P["redT"], "warning": P["amberT"],
                  "good": P["greenT"], "ok": P["greenT"]}.get(assess_level, P["blueT"])
    assess_bar = {"critical": P["red"], "warning": P["amber"],
                   "good": P["green"], "ok": P["green"]}.get(assess_level, P["blue"])

    at = Table([["", Paragraph(assess_text, st["BodyL"])]],
                colWidths=[2*mm, CW-4*mm])
    at.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), hc(assess_bar)),
        ("BACKGROUND", (1,0), (1,-1), hc(assess_bg)),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (1,0), (1,-1), 4*mm),
        ("BOTTOMPADDING", (1,0), (1,-1), 4*mm),
        ("LEFTPADDING", (1,0), (1,-1), 4*mm),
        ("RIGHTPADDING", (1,0), (1,-1), 4*mm),
        ("LEFTPADDING", (0,0), (0,0), 0),
        ("RIGHTPADDING", (0,0), (0,0), 0),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    story.append(at)

    # Alert details
    if alerts:
        story.append(sp(3))
        for al in alerts[:5]:
            sev = al.get("severity", "low")
            bc = {"high": P["red"], "medium": P["amber"]}.get(sev, P["blue"])
            bg = {"high": P["redL"], "medium": P["amberL"]}.get(sev, P["blueL"])
            parts = [Paragraph(f"<b>{al.get('title','')}</b>", ParagraphStyle("AT", fontName="Helvetica-Bold", fontSize=9, leading=12))]
            act = al.get("suggested_action", "")
            if act: parts.append(Paragraph(f"<i><font color='{P['gray']}' size='8'>→ {act}</font></i>", TD))
            acard = Table([["", parts]], colWidths=[2*mm, CW-6*mm])
            acard.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (0,-1), hc(bc)), ("BACKGROUND", (1,0), (1,-1), hc(bg)),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("TOPPADDING", (1,0), (1,-1), 2.5*mm), ("BOTTOMPADDING", (1,0), (1,-1), 2.5*mm),
                ("LEFTPADDING", (1,0), (1,-1), 3*mm),
            ]))
            story.append(acard)
            story.append(sp(1.5))

    # Health dimensions — Wave 12.F: horizontal progress bars per dimension
    breakdown = health.get("breakdown", [])
    if breakdown:
        story.append(sp(4))
        story.extend(_section_title(t["health_dim_title"]))
        for dim in breakdown:
            story.extend(_dimension_progress(
                name=dim.get("dimension", ""),
                points=dim.get("points"),
                max_pts=dim.get("max", 0),
                level=dim.get("level", ""),
            ))

    # Priority actions — Wave 12.F: numbered circle badges (like frontend)
    pactions = health.get("priority_actions", [])
    if pactions:
        story.append(sp(3))
        story.extend(_section_title(t["priority_title"]))
        for i, act in enumerate(pactions[:4], 1):
            story.append(_action_badge(i, act))

    # Data caveats
    caveats = health.get("data_caveats", [])
    if caveats:
        story.append(sp(3))
        story.append(Paragraph(f"<b>{t['data_caveats_title']}</b>", st["BodyS"]))
        for cav in caveats[:3]:
            story.append(Paragraph(f"<font color='{P['amber']}'>⚠</font> {cav}", st["BodyS"]))

    # ═════════════════════════════════════════════════════════════════════
    # Wave 12.D — Customer / Product / Commerce sections
    # ═════════════════════════════════════════════════════════════════════
    # Rendered only when the relevant module is active for the org
    # (digest_context_builder marks the section as available=False
    # otherwise). Rule-based: no AI required — these are tables and
    # KPIs directly from customer_metrics / product_metrics / orders.

    # ── Customers (Wave 12.F redesign) ─────────────────────────────────────
    customers = ov.get("customers_summary", {})
    if customers and customers.get("available") and customers.get("total_customers", 0) > 0:
        story.append(sp(5))
        story.extend(_section_title(t["customers_title"]))
        # KPI cards: total, new, concentration, churn risk
        churn_col = P["red"] if customers.get("churn_risk_count", 0) > 0 else P["dark"]
        cust_cards = [
            _kpi_card(t["cust_total"], str(customers.get("total_customers", 0))),
            _kpi_card(t["cust_new"], str(customers.get("new_customers_count", 0))),
            _kpi_card(t["cust_concentration"],
                       f"{customers.get('concentration_top5_pct', 0):.1f}%"),
            _kpi_card(t["cust_churn_risk"],
                       str(customers.get("churn_risk_count", 0)),
                       value_color=churn_col),
        ]
        story.append(_kpi_strip(cust_cards, cols=4))
        # CLV as a smaller secondary KPI line
        story.append(sp(2))
        story.append(Paragraph(
            f"<font name='Helvetica' size='8' color='{P['muted']}'>"
            f"{t['cust_avg_clv'].upper()}:</font> "
            f"<font name='Helvetica-Bold' size='9' color='{P['dark']}'>"
            f"{_eur(customers.get('avg_clv'))}</font>",
            ParagraphStyle("Sub", fontName="Helvetica", fontSize=8, leading=11),
        ))
        # Top customers — clean borderless table
        top_c = customers.get("top_customers") or []
        if top_c:
            story.append(sp(3))
            story.append(Paragraph(
                f"<font name='Helvetica-Bold' size='8' color='{P['muted']}'>"
                f"{t['cust_top_title'].upper()}</font>",
                ParagraphStyle("STT", fontName="Helvetica-Bold", fontSize=8,
                                leading=10, spaceAfter=1.5*mm),
            ))
            crows = [[Paragraph(t["cust_name_h"], TH_C),
                       Paragraph(t["cust_revenue_h"], TH_C),
                       Paragraph(t["cust_segment_h"], TH_C)]]
            for c in top_c:
                seg = c.get("segment") or "—"
                crows.append([
                    Paragraph(str(c.get("name", "?"))[:35], TD),
                    Paragraph(f"<b>{_eur(c.get('total_revenue'))}</b>", TDB),
                    Paragraph(seg, TD),
                ])
            cdtbl = Table(crows, colWidths=[CW*0.55, CW*0.25, CW*0.20])
            cdtbl.setStyle(_clean_table_style(3))
            story.append(cdtbl)

    # ── Products (Wave 12.F redesign) ──────────────────────────────────────
    products = ov.get("products_summary", {})
    if products and products.get("available") and products.get("total_products", 0) > 0:
        story.append(sp(5))
        story.extend(_section_title(t["products_title"]))
        low_col = P["amber"] if products.get("low_margin_count", 0) > 0 else P["dark"]
        decl_col = P["red"] if products.get("declining_count", 0) > 0 else P["dark"]
        dorm_col = P["amber"] if products.get("dormant_count", 0) > 0 else P["dark"]
        prod_cards = [
            _kpi_card(t["prod_total"], str(products.get("total_products", 0))),
            _kpi_card(t["prod_avg_margin"], f"{products.get('avg_margin_pct', 0):.1f}%"),
            _kpi_card(t["prod_low_margin"],
                       str(products.get("low_margin_count", 0)),
                       value_color=low_col),
            _kpi_card(t["prod_declining"],
                       str(products.get("declining_count", 0)),
                       value_color=decl_col),
        ]
        story.append(_kpi_strip(prod_cards, cols=4))
        # Second row: dormant + (blank for visual balance)
        story.append(sp(2))
        story.append(Paragraph(
            f"<font name='Helvetica' size='8' color='{P['muted']}'>"
            f"{t['prod_dormant'].upper()}:</font> "
            f"<font name='Helvetica-Bold' size='9' color='{dorm_col}'>"
            f"{products.get('dormant_count', 0)}</font>",
            ParagraphStyle("Sub", fontName="Helvetica", fontSize=8, leading=11),
        ))
        top_p = products.get("top_sellers") or []
        if top_p:
            story.append(sp(3))
            story.append(Paragraph(
                f"<font name='Helvetica-Bold' size='8' color='{P['muted']}'>"
                f"{t['prod_top_title'].upper()}</font>",
                ParagraphStyle("STT", fontName="Helvetica-Bold", fontSize=8,
                                leading=10, spaceAfter=1.5*mm),
            ))
            prows = [[Paragraph(t["prod_name_h"], TH_C),
                       Paragraph(t["prod_revenue_h"], TH_C),
                       Paragraph(t["prod_units_h"], TH_C)]]
            for p in top_p:
                prows.append([
                    Paragraph(str(p.get("name", "?"))[:35], TD),
                    Paragraph(f"<b>{_eur(p.get('revenue'))}</b>", TDB),
                    Paragraph(f"{p.get('units', 0)}", TD),
                ])
            ptbl = Table(prows, colWidths=[CW*0.55, CW*0.25, CW*0.20])
            ptbl.setStyle(_clean_table_style(3))
            story.append(ptbl)

    # ── Commerce (Wave 12.F redesign) ──────────────────────────────────────
    commerce = ov.get("commerce_summary", {})
    if commerce and commerce.get("available") and commerce.get("orders_count", 0) > 0:
        story.append(sp(5))
        story.extend(_section_title(t["commerce_title"]))
        aov_trend = commerce.get("aov_trend_pct", 0) or 0
        trend_col = (P["green"] if aov_trend > 0 else
                      P["red"] if aov_trend < 0 else P["dark"])
        cancel_col = (P["red"] if commerce.get("cancellation_rate_pct", 0) > 5
                       else P["dark"])
        comm_cards = [
            _kpi_card(t["comm_orders"], str(commerce.get("orders_count", 0)),
                       sub=f"{t['comm_orders_prev']}: {commerce.get('orders_prev_count', 0)}"),
            _kpi_card(t["comm_aov"], _eur(commerce.get("aov")),
                       sub=f"<font color='{trend_col}'>{aov_trend:+.1f}%</font> {t['comm_aov_trend']}"),
            _kpi_card(t["comm_cancel"],
                       f"{commerce.get('cancellation_rate_pct', 0):.1f}%",
                       value_color=cancel_col),
            _kpi_card(t["comm_draft"], str(commerce.get("draft_orders_count", 0))),
        ]
        story.append(_kpi_strip(comm_cards, cols=4))
        top_ch = commerce.get("top_channels") or []
        if top_ch:
            story.append(sp(3))
            story.append(Paragraph(
                f"<font name='Helvetica-Bold' size='8' color='{P['muted']}'>"
                f"{t['comm_channels_title'].upper()}</font>",
                ParagraphStyle("STT", fontName="Helvetica-Bold", fontSize=8,
                                leading=10, spaceAfter=1.5*mm),
            ))
            chrows = [[Paragraph(t["comm_channel_h"], TH_C),
                        Paragraph(t["amount_h"], TH_C),
                        Paragraph(t["share_h"], TH_C),
                        Paragraph(t["comm_count_h"], TH_C)]]
            for ch in top_ch:
                chrows.append([
                    Paragraph(str(ch.get("channel", "direct"))[:30], TD),
                    Paragraph(f"<b>{_eur(ch.get('revenue'))}</b>", TDB),
                    Paragraph(f"{ch.get('share_pct', 0):.0f}%", TD),
                    Paragraph(f"{ch.get('count', 0)}", TD),
                ])
            ctbl = Table(chrows, colWidths=[CW*0.45, CW*0.25, CW*0.15, CW*0.15])
            ctbl.setStyle(_clean_table_style(4))
            story.append(ctbl)

    # Top suppliers (Wave 12.F clean table style)
    top_sup = ov.get("suppliers", {}).get("top_suppliers", [])
    if top_sup and purch > 0:
        story.append(sp(5))
        story.extend(_section_title(t["top_suppliers_title"]))
        srows = [[Paragraph(t["supplier_h"], TH_C),
                   Paragraph(t["amount_h"], TH_C),
                   Paragraph(t["share_h"], TH_C)]]
        for su in top_sup[:5]:
            nm = str(su.get("_id") or su.get("supplier","?"))[:30]
            am = su.get("total", 0)
            pc = (am/purch*100) if purch else 0
            srows.append([
                Paragraph(nm, TD),
                Paragraph(f"<b>{_eur(am)}</b>", TDB),
                Paragraph(f"{pc:.0f}%", TD),
            ])
        stbl = Table(srows, colWidths=[CW*0.55, CW*0.25, CW*0.20])
        stbl.setStyle(_clean_table_style(3))
        story.append(stbl)

    # AI insights + recommendations — Wave 12.F: cleaner typography
    # AI recommendations reuse the same numbered-badge pattern as
    # the priority actions for visual consistency.
    story.append(sp(4))
    if insights:
        story.extend(_section_title(t["ai_insights"]))
        for ins in insights:
            story.append(Paragraph(
                f"<font color='{P['blue']}' size='10'>&#8226;</font>  "
                f"<font size='10' color='{P['darkS']}'>{ins}</font>",
                ParagraphStyle("Ins", fontName="Helvetica", fontSize=10,
                                leading=14, leftIndent=3*mm, spaceBefore=2*mm),
            ))
        story.append(sp(3))
    if recommendations:
        story.extend(_section_title(t["ai_recs"]))
        for i, rec in enumerate(recommendations, 1):
            story.append(_action_badge(i, rec))

    if is_starter and not insights and not recommendations:
        story.append(sp(5))
        ct = Table([[Paragraph(t["upgrade"], st["CTA"])]], colWidths=[CW-10*mm])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), hc(P["blueL"])),
            ("ROUNDEDCORNERS", [3,3,3,3]),
            ("TOPPADDING", (0,0), (-1,-1), 4*mm), ("BOTTOMPADDING", (0,0), (-1,-1), 4*mm),
            ("BOX", (0,0), (-1,-1), 0.5, hc(P["blue"])),
        ]))
        story.append(ct)

    # Footer
    story.append(sp(8))
    story.append(HRFlowable(width="100%", thickness=0.5, color=hc(P["border"])))
    story.append(Paragraph(f"{t['footer']}  |  {date.today().strftime('%d/%m/%Y')}", st["Ftr"]))

    doc.build(story)
    buf.seek(0)
    return buf.read()
