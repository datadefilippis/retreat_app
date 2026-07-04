"""
Cashflow Monitor — module status builder.

Pure function: derives a synthetic health status from already-computed KPI and
alert data.  No database queries — designed to be called by overview_builder
after all data is fetched and computed.

Public interface:
    compute_status(kpis: dict, alerts_summary: dict, locale: str) -> dict
        Returns the status block to include in the overview response.
        Never raises — returns "insufficient_data" on any error.

Status dict shape:
    {
        "level":          str,   # "healthy"|"monitor"|"warning"|"critical"|"insufficient_data"
        "color":          str,   # "green"|"yellow"|"orange"|"red"|"gray"
        "label":          str,   # localized label, e.g. "Healthy"
        "primary_driver": str,   # key that triggered the status, e.g. "outflow_ratio_extreme"
        "message":        str,   # 1-sentence localized description
        "data_warnings":  list,  # list of strings: structural incompleteness notes
    }

Priority rules (first match wins — top-down):
    1.  total_sales < 1.0 AND period_days >= 7  -> insufficient_data
    2.  total_outflow_ratio > 150              -> critical  (extreme burn rate)
    3.  net_after_fixed < 0 AND high >= 2       -> critical  (loss + multiple alerts)
    4.  total_outflow_ratio > 100              -> warning   (outflows exceed revenue)
    5.  net_after_fixed < 0                    -> warning   (negative net result)
    6.  total_outflow_ratio > 80 AND high >= 1  -> warning   (tight margin + alert)
    7.  high_alerts >= 1                        -> monitor   (alert despite profitability)
    8.  total_outflow_ratio > 80               -> monitor   (margin squeezing)
    9.  sales_trend_pct < -20                  -> monitor   (revenue declining)
    10. (else)                                 -> healthy
"""


# ── Locale-aware text tables ──────────────────────────────────────────────────
# Organized by locale code.  Each locale provides:
#   labels    — short status names
#   messages  — per-rule f-string templates (use {var} placeholders)
#   buckets   — dominant outflow bucket descriptions
#   warnings  — data completeness warning text

_L = {
    "it": {
        "labels": {
            "healthy": "Sano",
            "monitor": "Attenzione",
            "warning": "Allerta",
            "critical": "Critico",
            "insufficient_data": "Dati insufficienti",
        },
        "messages": {
            "no_revenue_data":
                "Non ci sono dati di ricavo sufficienti per valutare lo stato del modulo.",
            "outflow_ratio_extreme":
                "Le uscite totali rappresentano il {ratio:.0f}% dei ricavi: "
                "l'azienda sta erodendo cassa rapidamente.",
            "negative_result_with_high_alerts":
                "Risultato netto negativo ({currency}{net:,.0f}) con {alerts} "
                "alert critici attivi: e necessaria un'azione immediata.",
            "outflow_exceeds_revenue":
                "Le uscite superano i ricavi ({ratio:.0f}%): "
                "il contributo principale e {dominant}.",
            "negative_net_result":
                "Il Risultato Netto e negativo ({currency}{net:,.0f}): "
                "le uscite complessive superano i ricavi del periodo.",
            "high_expense_ratio_with_alerts":
                "Margine ridotto ({ratio:.0f}% di expense ratio) "
                "con {alerts} alert critici attivi.",
            "active_high_alerts":
                "Il risultato e positivo ma ci sono {alerts} alert critici "
                "da analizzare prima che si trasformino in un problema.",
            "high_expense_ratio":
                "L'expense ratio complessivo e {ratio:.0f}%: "
                "il margine si sta restringendo, tieni sotto controllo le uscite.",
            "declining_revenue":
                "I ricavi sono in calo del {trend:.0f}% rispetto al "
                "periodo precedente: monitora la tendenza nelle prossime settimane.",
            "all_clear":
                "Risultato Netto positivo ({currency}{net:,.0f}) e uscite sotto controllo "
                "({ratio:.0f}% di expense ratio).",
            "computation_error":
                "Impossibile calcolare lo stato del modulo.",
        },
        "buckets": {
            "expenses":  "le spese operative (Bucket A)",
            "purchases": "gli acquisti fornitori (Bucket B)",
            "fixed":     "i costi fissi (Bucket C)",
        },
        "warnings": {
            "no_fixed_costs":
                "Nessun costo fisso registrato — il Risultato Netto potrebbe essere "
                "sovrastimato rispetto alla realta strutturale dell'azienda.",
        },
    },
    "en": {
        "labels": {
            "healthy": "Healthy",
            "monitor": "Monitor",
            "warning": "Warning",
            "critical": "Critical",
            "insufficient_data": "Insufficient data",
        },
        "messages": {
            "no_revenue_data":
                "There is not enough revenue data to assess the module status.",
            "outflow_ratio_extreme":
                "Total outflows represent {ratio:.0f}% of revenue: "
                "the company is burning cash rapidly.",
            "negative_result_with_high_alerts":
                "Negative net result ({currency}{net:,.0f}) with {alerts} "
                "critical alerts active: immediate action is required.",
            "outflow_exceeds_revenue":
                "Outflows exceed revenue ({ratio:.0f}%): "
                "the main contributor is {dominant}.",
            "negative_net_result":
                "Net result is negative ({currency}{net:,.0f}): "
                "total outflows exceed revenue for the period.",
            "high_expense_ratio_with_alerts":
                "Tight margin ({ratio:.0f}% expense ratio) "
                "with {alerts} critical alerts active.",
            "active_high_alerts":
                "The result is positive but there are {alerts} critical alerts "
                "to address before they become a problem.",
            "high_expense_ratio":
                "The overall expense ratio is {ratio:.0f}%: "
                "the margin is narrowing, keep outflows under control.",
            "declining_revenue":
                "Revenue is down {trend:.0f}% compared to the "
                "previous period: monitor the trend in the coming weeks.",
            "all_clear":
                "Positive net result ({currency}{net:,.0f}) and outflows under control "
                "({ratio:.0f}% expense ratio).",
            "computation_error":
                "Unable to calculate module status.",
        },
        "buckets": {
            "expenses":  "operating expenses (Bucket A)",
            "purchases": "supplier purchases (Bucket B)",
            "fixed":     "fixed costs (Bucket C)",
        },
        "warnings": {
            "no_fixed_costs":
                "No fixed costs recorded — the net result may be overestimated "
                "relative to the company's structural cost base.",
        },
    },
    "de": {
        "labels": {
            "healthy": "Gesund",
            "monitor": "Beobachten",
            "warning": "Warnung",
            "critical": "Kritisch",
            "insufficient_data": "Ungenuegend Daten",
        },
        "messages": {
            "no_revenue_data":
                "Es liegen nicht genuegend Umsatzdaten vor, um den Modulstatus zu bewerten.",
            "outflow_ratio_extreme":
                "Die Gesamtausgaben betragen {ratio:.0f}% des Umsatzes: "
                "das Unternehmen verbrennt schnell Liquiditaet.",
            "negative_result_with_high_alerts":
                "Negatives Nettoergebnis ({currency}{net:,.0f}) mit {alerts} "
                "kritischen Warnungen: sofortiges Handeln ist erforderlich.",
            "outflow_exceeds_revenue":
                "Die Ausgaben uebersteigen den Umsatz ({ratio:.0f}%): "
                "der Haupttreiber ist {dominant}.",
            "negative_net_result":
                "Das Nettoergebnis ist negativ ({currency}{net:,.0f}): "
                "die Gesamtausgaben uebersteigen den Umsatz des Zeitraums.",
            "high_expense_ratio_with_alerts":
                "Enge Marge ({ratio:.0f}% Ausgabenquote) "
                "mit {alerts} kritischen Warnungen.",
            "active_high_alerts":
                "Das Ergebnis ist positiv, aber es gibt {alerts} kritische Warnungen, "
                "die analysiert werden sollten.",
            "high_expense_ratio":
                "Die Gesamtausgabenquote betraegt {ratio:.0f}%: "
                "die Marge wird enger, behalten Sie die Ausgaben im Blick.",
            "declining_revenue":
                "Der Umsatz ist um {trend:.0f}% gegenueber dem "
                "Vorzeitraum gesunken: beobachten Sie den Trend.",
            "all_clear":
                "Positives Nettoergebnis ({currency}{net:,.0f}) und Ausgaben unter Kontrolle "
                "({ratio:.0f}% Ausgabenquote).",
            "computation_error":
                "Modulstatus konnte nicht berechnet werden.",
        },
        "buckets": {
            "expenses":  "die Betriebsausgaben (Bucket A)",
            "purchases": "die Lieferanteneinkauefe (Bucket B)",
            "fixed":     "die Fixkosten (Bucket C)",
        },
        "warnings": {
            "no_fixed_costs":
                "Keine Fixkosten erfasst — das Nettoergebnis koennte im Verhaeltnis "
                "zur strukturellen Kostenbasis des Unternehmens ueberschaetzt sein.",
        },
    },
    "fr": {
        "labels": {
            "healthy": "Sain",
            "monitor": "A surveiller",
            "warning": "Alerte",
            "critical": "Critique",
            "insufficient_data": "Donnees insuffisantes",
        },
        "messages": {
            "no_revenue_data":
                "Les donnees de chiffre d'affaires sont insuffisantes pour evaluer le statut du module.",
            "outflow_ratio_extreme":
                "Les sorties totales representent {ratio:.0f}% du chiffre d'affaires : "
                "l'entreprise consomme sa tresorerie rapidement.",
            "negative_result_with_high_alerts":
                "Resultat net negatif ({currency}{net:,.0f}) avec {alerts} "
                "alertes critiques actives : une action immediate est necessaire.",
            "outflow_exceeds_revenue":
                "Les sorties depassent le chiffre d'affaires ({ratio:.0f}%) : "
                "le principal contributeur est {dominant}.",
            "negative_net_result":
                "Le resultat net est negatif ({currency}{net:,.0f}) : "
                "les sorties totales depassent le chiffre d'affaires de la periode.",
            "high_expense_ratio_with_alerts":
                "Marge reduite ({ratio:.0f}% de ratio de depenses) "
                "avec {alerts} alertes critiques actives.",
            "active_high_alerts":
                "Le resultat est positif mais il y a {alerts} alertes critiques "
                "a traiter avant qu'elles ne deviennent un probleme.",
            "high_expense_ratio":
                "Le ratio de depenses global est de {ratio:.0f}% : "
                "la marge se resserre, surveillez les sorties.",
            "declining_revenue":
                "Le chiffre d'affaires est en baisse de {trend:.0f}% par rapport a la "
                "periode precedente : surveillez la tendance.",
            "all_clear":
                "Resultat net positif ({currency}{net:,.0f}) et sorties sous controle "
                "({ratio:.0f}% de ratio de depenses).",
            "computation_error":
                "Impossible de calculer le statut du module.",
        },
        "buckets": {
            "expenses":  "les depenses operationnelles (Bucket A)",
            "purchases": "les achats fournisseurs (Bucket B)",
            "fixed":     "les couts fixes (Bucket C)",
        },
        "warnings": {
            "no_fixed_costs":
                "Aucun cout fixe enregistre — le resultat net pourrait etre "
                "surestime par rapport a la structure de couts reelle de l'entreprise.",
        },
    },
}


def _get_locale_texts(locale: str) -> dict:
    """Return the text table for the given locale, with Italian fallback."""
    return _L.get(locale, _L["it"])


def compute_status(kpis: dict, alerts_summary: dict, locale: str = "it") -> dict:
    """Derive the module health status from KPI and alert data.

    Args:
        kpis: subset of the KPI dict with the fields listed below.
        alerts_summary: {"open_count": int, "by_severity": {"high": int, ...}}
        locale: ISO 639-1 language code for user-facing text.

    Returns:
        Status dict with keys: level, color, label, primary_driver, message,
        data_warnings.  Never raises.
    """
    txt = _get_locale_texts(locale)
    labels = txt["labels"]
    msgs = txt["messages"]
    bkts = txt["buckets"]
    warns = txt["warnings"]

    try:
        total_sales        = float(kpis.get("total_sales", 0))
        net_after_fixed    = float(kpis.get("net_after_fixed", 0))
        total_outflow_ratio = float(kpis.get("total_outflow_ratio", 0))
        total_expenses     = float(kpis.get("total_expenses", 0))
        supplier_purchases = float(kpis.get("supplier_purchases", 0))
        fixed_costs_total  = float(kpis.get("fixed_costs_total", 0))
        # Wave 14.CONSOLIDATE R9 — sales_trend_pct is now None when
        # prev_period had zero sales (was 0.0, hiding infinite growth).
        # Coerce here so downstream threshold comparisons don't crash;
        # None semantically maps to 0.0 for THIS rule (we can't say
        # "declining revenue" when prev was zero — there's no baseline).
        _raw_trend = kpis.get("sales_trend_pct")
        sales_trend_pct    = float(_raw_trend) if _raw_trend is not None else 0.0
        period_days        = int(kpis.get("period_days", 30))

        by_severity  = alerts_summary.get("by_severity", {})
        high_alerts  = int(by_severity.get("high", 0))

        # ── Data completeness warnings ───────────────────────────────────────
        data_warnings: list = []
        if fixed_costs_total == 0:
            data_warnings.append(warns["no_fixed_costs"])

        # ── Rule 1: Insufficient data ────────────────────────────────────────
        if total_sales < 1.0 and period_days >= 7:
            return _make(
                "insufficient_data", "gray", labels["insufficient_data"],
                "no_revenue_data", msgs["no_revenue_data"], data_warnings,
            )

        # ── Rule 2: Critical — extreme burn rate ─────────────────────────────
        if total_outflow_ratio > 150:
            return _make(
                "critical", "red", labels["critical"],
                "outflow_ratio_extreme",
                msgs["outflow_ratio_extreme"].format(ratio=total_outflow_ratio),
                data_warnings,
            )

        # ── Rule 3: Critical — loss + multiple high alerts ───────────────────
        if net_after_fixed < 0 and high_alerts >= 2:
            return _make(
                "critical", "red", labels["critical"],
                "negative_result_with_high_alerts",
                msgs["negative_result_with_high_alerts"].format(
                    currency="\u20ac", net=net_after_fixed, alerts=high_alerts,
                ),
                data_warnings,
            )

        # ── Rule 4: Warning — outflows exceed revenue ────────────────────────
        if total_outflow_ratio > 100:
            dominant = _dominant_bucket(total_expenses, supplier_purchases, fixed_costs_total, bkts)
            return _make(
                "warning", "orange", labels["warning"],
                "outflow_exceeds_revenue",
                msgs["outflow_exceeds_revenue"].format(
                    ratio=total_outflow_ratio, dominant=dominant,
                ),
                data_warnings,
            )

        # ── Rule 5: Warning — negative net result ────────────────────────────
        if net_after_fixed < 0:
            return _make(
                "warning", "orange", labels["warning"],
                "negative_net_result",
                msgs["negative_net_result"].format(
                    currency="\u20ac", net=net_after_fixed,
                ),
                data_warnings,
            )

        # ── Rule 6: Warning — tight margin + at least one high alert ─────────
        if total_outflow_ratio > 80 and high_alerts >= 1:
            return _make(
                "warning", "orange", labels["warning"],
                "high_expense_ratio_with_alerts",
                msgs["high_expense_ratio_with_alerts"].format(
                    ratio=total_outflow_ratio, alerts=high_alerts,
                ),
                data_warnings,
            )

        # ── Rule 7: Monitor — at least one high alert (but profitable) ───────
        if high_alerts >= 1:
            return _make(
                "monitor", "yellow", labels["monitor"],
                "active_high_alerts",
                msgs["active_high_alerts"].format(alerts=high_alerts),
                data_warnings,
            )

        # ── Rule 8: Monitor — high expense ratio ────────────────────────────
        if total_outflow_ratio > 80:
            return _make(
                "monitor", "yellow", labels["monitor"],
                "high_expense_ratio",
                msgs["high_expense_ratio"].format(ratio=total_outflow_ratio),
                data_warnings,
            )

        # ── Rule 9: Monitor — declining revenue trend ────────────────────────
        if sales_trend_pct < -20 and total_sales > 0:
            return _make(
                "monitor", "yellow", labels["monitor"],
                "declining_revenue",
                msgs["declining_revenue"].format(trend=abs(sales_trend_pct)),
                data_warnings,
            )

        # ── Rule 10: Healthy ────────────────────────────────────────────────
        return _make(
            "healthy", "green", labels["healthy"],
            "all_clear",
            msgs["all_clear"].format(
                currency="\u20ac", net=net_after_fixed, ratio=total_outflow_ratio,
            ),
            data_warnings,
        )

    except Exception:
        return _make(
            "insufficient_data", "gray",
            _get_locale_texts(locale)["labels"]["insufficient_data"],
            "computation_error",
            _get_locale_texts(locale)["messages"]["computation_error"],
            [],
        )


# ── Private helpers ────────────────────────────────────────────────────────────

def _make(
    level: str, color: str, label: str,
    primary_driver: str, message: str,
    data_warnings: list,
) -> dict:
    """Build a status dict with consistent structure."""
    return {
        "level": level,
        "color": color,
        "label": label,
        "primary_driver": primary_driver,
        "message": message,
        "data_warnings": data_warnings,
    }


def _dominant_bucket(
    total_expenses: float,
    supplier_purchases: float,
    fixed_costs_total: float,
    bucket_labels: dict,
) -> str:
    """Return a localized name for the largest outflow bucket."""
    buckets = [
        (total_expenses,     bucket_labels["expenses"]),
        (supplier_purchases, bucket_labels["purchases"]),
        (fixed_costs_total,  bucket_labels["fixed"]),
    ]
    return max(buckets, key=lambda x: x[0])[1]
