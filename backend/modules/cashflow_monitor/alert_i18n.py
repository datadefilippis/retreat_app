"""
Alert i18n — locale text table for alert titles, summaries, and suggested actions.

Follows the same _L pattern used by status_builder.py.
Templates use str.format() with named placeholders.
"""

_L = {
    # ═════════════════════════════════════════════════════════════════════════
    # ITALIANO
    # ═════════════════════════════════════════════════════════════════════════
    "it": {
        # ── Category A: Liquidità ────────────────────────────────────────
        "cash_runway_critical": {
            "title": "Autonomia finanziaria critica: {days:.0f} giorni",
            "summary": "Al ritmo attuale di uscite, le risorse coprono circa {days:.0f} giorni. Il margine netto del periodo è {margin}.",
            "suggestion": "Priorità: ridurre le uscite non essenziali e accelerare gli incassi. Valutare rinvio dei pagamenti non urgenti.",
        },
        "persistent_negative_cashflow": {
            "title": "Cashflow negativo per {neg_days} giorni su {window}",
            "summary": "Negli ultimi {window} giorni, il saldo giornaliero (entrate - uscite) è stato negativo per {neg_days} giorni. Perdita netta cumulata: {cumulative_loss}.",
            "suggestion": "Verificare se ci sono incassi in ritardo o spese straordinarie. Controllare lo scadenzario dei pagamenti in entrata.",
        },
        "month_closed_loss": {
            "title": "Mese di {month} chiuso in perdita: {loss}",
            "summary": "Il mese di {month} ha registrato entrate totali di {revenue} contro uscite totali di {outflows}, con una perdita netta di {loss} ({loss_pct}% dei ricavi).",
            # v14.2 (P2.4b): used when loss_pct ≥ 100 — "1000% dei ricavi"
            # is unparseable for a human reader, so we switch to a per-€
            # framing that any small business owner instantly understands.
            "summary_severe": "Il mese di {month} ha registrato entrate di {revenue} contro uscite di {outflows} — per ogni €1 di ricavi sono stati spesi €{cost_per_revenue} di costi. Perdita netta: {loss}.",
            "suggestion": "Analizzare le voci di costo principali del mese. Confrontare con i mesi precedenti per identificare aumenti anomali.",
        },
        "revenue_concentration": {
            "title": "Il {pct}% dei ricavi dipende da un solo cliente",
            "summary": "Il cliente \"{customer}\" genera il {pct}% del fatturato totale nel periodo ({amount}). Se questo cliente riducesse gli ordini, l'impatto sarebbe significativo.",
            "suggestion": "Diversificare la base clienti. Valutare strategie di acquisizione per ridurre la dipendenza da un singolo cliente.",
        },
        # ── Category B: Marginalità ──────────────────────────────────────
        "margin_erosion_trend": {
            "title": "Margine in calo da {months} mesi consecutivi",
            "summary": "Il margine netto è sceso dal {start_margin}% ({start_month}) al {end_margin}% ({end_month}), una riduzione di {erosion_pp} punti percentuali.",
            "suggestion": "Verificare se i costi sono aumentati o i prezzi di vendita sono diminuiti. Controllare i prezzi dei fornitori principali.",
        },
        "unit_cost_increase": {
            "title": "Rapporto costi/ricavi in aumento: +{increase_pct}%",
            "summary": "Il rapporto costi totali su ricavi è passato dal {prev_ratio}% al {curr_ratio}% rispetto al periodo precedente, un aumento di {increase_pct} punti.",
            "suggestion": "Analizzare quali categorie di costo sono cresciute di più. Rinegoziare i contratti con i fornitori principali.",
        },
        "break_even_unreached": {
            "title": "Break-even non raggiunto a metà mese",
            "summary": "Al giorno {day} del mese, i ricavi cumulati sono {current_revenue} contro un break-even proiettato di {projected_be}. Deficit del {deficit_pct}%.",
            "suggestion": "Intensificare l'attività commerciale nelle prossime settimane. Valutare promozioni o solleciti ai clienti con ordini pendenti.",
        },
        "category_expense_trend": {
            "title": "Spese \"{category}\" in aumento da {months} mesi: +{increase_pct}%",
            "summary": "La categoria \"{category}\" è passata da {prev_amount} a {curr_amount} mese su mese, un aumento del {increase_pct}%. Importo assoluto: +{abs_increase}.",
            "suggestion": "Verificare se l'aumento è giustificato da maggiore attività o se è un costo fuori controllo. Confrontare con il budget previsto.",
        },
        # ── Category C: Ciclo di cassa ───────────────────────────────────
        "dso_worsening_trend": {
            "title": "Tempi di incasso in peggioramento: DSO {current_dso:.0f} giorni",
            "summary": "Il Days Sales Outstanding è passato da {prev_dso:.0f} a {current_dso:.0f} giorni negli ultimi 3 mesi, un aumento del {increase_pct}%. I clienti pagano sempre più tardi.",
            "suggestion": "Sollecitare i pagamenti in ritardo. Valutare condizioni di pagamento più stringenti per i nuovi ordini.",
        },
        "high_risk_invoice": {
            "title": "Fattura ad alto rischio: {amount} scaduta da {overdue_days} giorni",
            "summary": "Una fattura di {amount} (il {revenue_pct}% del fatturato mensile) è scaduta da {overdue_days} giorni. Cliente: \"{customer}\".",
            "suggestion": "Contattare immediatamente il cliente. Valutare azioni di sollecito formale o recupero crediti.",
        },
        "dpo_dso_imbalance": {
            "title": "Squilibrio incassi/pagamenti: gap di {gap:.0f} giorni",
            "summary": "Paghi i fornitori in media in {dpo:.0f} giorni ma incassi dai clienti in {dso:.0f} giorni. Stai finanziando il ciclo di cassa dei tuoi clienti per {gap:.0f} giorni.",
            "suggestion": "Negoziare termini di pagamento più lunghi con i fornitori e/o più brevi con i clienti.",
        },
        # ── Category D: Pattern ──────────────────────────────────────────
        "yoy_anomaly": {
            "title": "Ricavi {change_pct}% rispetto allo stesso mese dell'anno scorso",
            "summary": "Nel mese di {month} i ricavi sono {current_amount} contro {prev_amount} dello stesso mese dell'anno precedente. Variazione: {change_pct}%.",
            "suggestion": "Verificare se il calo è dovuto a fattori stagionali, perdita clienti o cambiamenti di mercato.",
        },
        "positive_trend_break": {
            "title": "Inversione trend: primo calo dopo {months} mesi di crescita",
            "summary": "I ricavi erano in crescita da {months} mesi consecutivi. Questo mese ({current_month}) si registra un calo del {decline_pct}% rispetto al mese precedente.",
            "suggestion": "Analizzare le cause del rallentamento. Potrebbe essere stagionale o segnalare un cambio di trend.",
        },
        "weekly_statistical_anomaly": {
            "title": "Settimana anomala: ricavi {sigma:.1f}σ sotto la media",
            "summary": "I ricavi della settimana ({current_amount}) sono statisticamente anomali rispetto alla media delle ultime {weeks} settimane ({avg_amount}). Deviazione: {sigma:.1f} sigma.",
            "suggestion": "Verificare se ci sono cause specifiche (festività, problemi operativi). Se non ci sono cause evidenti, monitorare la prossima settimana.",
        },
        # ── Category E: Dipendenze ───────────────────────────────────────
        "supplier_concentration": {
            "title": "Il {pct}% degli acquisti da un solo fornitore",
            "summary": "Il fornitore \"{supplier}\" rappresenta il {pct}% degli acquisti totali ({amount}). Una dipendenza elevata aumenta il rischio operativo.",
            "suggestion": "Identificare fornitori alternativi. Negoziare un contratto con garanzie di fornitura se non ci sono alternative.",
        },
        "dominant_product": {
            "title": "Il {pct}% dei ricavi da una sola categoria",
            "summary": "La categoria \"{category}\" genera il {pct}% del fatturato totale ({amount}). Una forte dipendenza da un prodotto/servizio aumenta il rischio.",
            "suggestion": "Valutare strategie di diversificazione dell'offerta per ridurre la dipendenza da una singola linea di prodotto.",
        },
        "fixed_cost_ratio_high": {
            "title": "Costi fissi al {ratio}% dei ricavi",
            "summary": "I costi fissi ({fixed_costs}) rappresentano il {ratio}% dei ricavi ({revenue}). Una struttura dei costi rigida riduce la capacità di adattamento.",
            "suggestion": "Verificare se alcuni costi fissi possono essere variabilizzati. Valutare rinegoziazione affitti, contratti, abbonamenti.",
        },
        # ── Category F: Commerce Operations ──────────────────────────────
        "order_backlog": {
            "title": "{count} ordini in bozza da oltre 3 giorni",
            "summary": "{count} ordini su {total} totali sono in stato bozza da piu' di 3 giorni. Potrebbero richiedere conferma o follow-up.",
            "suggestion": "Revisiona gli ordini in bozza e conferma o annulla quelli non piu' rilevanti.",
        },
        "fulfillment_delay": {
            "title": "Ordine {order} in attesa di evasione da {days} giorni",
            "summary": "L'ordine {order} ({customer}) e' confermato ma l'evasione e' ancora in stato 'pending' da {days} giorni.",
            "suggestion": "Verifica lo stato della spedizione o del ritiro per questo ordine e aggiorna il fulfillment.",
        },
        "payment_limbo": {
            "title": "Pagamento {amount} raccolto ma ordine {order} non confermato",
            "summary": "L'ordine {order} ha ricevuto il pagamento di {amount} da {hours} ore ma non e' stato confermato. Il denaro e' in limbo.",
            "suggestion": "Conferma immediatamente l'ordine per registrare il ricavo nel cashflow.",
        },
        "event_low_fill": {
            "title": "Evento '{name}' al {fill:.0f}% di capienza",
            "summary": "L'evento '{name}' del {date} ha solo {booked}/{capacity} posti prenotati ({fill:.0f}%). L'evento e' tra meno di 3 giorni.",
            "suggestion": "Valuta promozione last-minute, reminder ai clienti, o riduzione prezzo per aumentare le prenotazioni.",
        },
        "rental_idle": {
            "title": "Noleggio '{name}' inutilizzato negli ultimi 30 giorni",
            "summary": "Il prodotto '{name}' non ha ricevuto alcun noleggio negli ultimi 30 giorni. Potrebbe essere un costo inattivo.",
            "suggestion": "Considera riduzione prezzo, promozione, o ritiro dal catalogo se il prodotto non genera domanda.",
        },
        "cancellation_spike": {
            "title": "Tasso cancellazione al {rate:.0f}% negli ultimi 7 giorni",
            "summary": "{cancelled} ordini cancellati su {total} totali negli ultimi 7 giorni ({rate:.0f}%). Un tasso sopra il 20% richiede attenzione.",
            "suggestion": "Analizza le ragioni delle cancellazioni. Contatta i clienti per feedback. Verifica se ci sono problemi nel processo d'ordine.",
        },
        "low_stock": {
            "title": "Prodotto '{name}' — scorta a {stock} unita'",
            "summary": "Il prodotto '{name}' ha solo {stock} unita' in magazzino. A zero, il prodotto non sara' piu' ordinabile nello storefront.",
            "suggestion": "Riordina il prodotto o aggiorna la giacenza nel catalogo. Considera di disattivare la pubblicazione se non disponibile.",
        },
    },

    # ═════════════════════════════════════════════════════════════════════════
    # ENGLISH
    # ═════════════════════════════════════════════════════════════════════════
    "en": {
        "cash_runway_critical": {
            "title": "Critical cash runway: {days:.0f} days",
            "summary": "At the current outflow rate, resources cover approximately {days:.0f} days. Net margin for the period is {margin}.",
            "suggestion": "Priority: reduce non-essential expenses and accelerate collections. Consider deferring non-urgent payments.",
        },
        "persistent_negative_cashflow": {
            "title": "Negative cashflow for {neg_days} days out of {window}",
            "summary": "Over the last {window} days, daily balance (income - expenses) was negative for {neg_days} days. Cumulative net loss: {cumulative_loss}.",
            "suggestion": "Check for delayed collections or extraordinary expenses. Review the incoming payment schedule.",
        },
        "month_closed_loss": {
            "title": "Month of {month} closed at a loss: {loss}",
            "summary": "The month of {month} recorded total income of {revenue} against total outflows of {outflows}, resulting in a net loss of {loss} ({loss_pct}% of revenue).",
            "summary_severe": "The month of {month} recorded income of {revenue} against outflows of {outflows} — for every €1 of revenue, €{cost_per_revenue} of costs were incurred. Net loss: {loss}.",
            "suggestion": "Analyze the main cost items for the month. Compare with previous months to identify unusual increases.",
        },
        "revenue_concentration": {
            "title": "{pct}% of revenue depends on a single customer",
            "summary": "Customer \"{customer}\" generates {pct}% of total revenue in the period ({amount}). If this customer reduced orders, the impact would be significant.",
            "suggestion": "Diversify the customer base. Evaluate acquisition strategies to reduce dependency on a single customer.",
        },
        "margin_erosion_trend": {
            "title": "Margin declining for {months} consecutive months",
            "summary": "Net margin dropped from {start_margin}% ({start_month}) to {end_margin}% ({end_month}), a reduction of {erosion_pp} percentage points.",
            "suggestion": "Check whether costs have increased or selling prices have decreased. Review main supplier pricing.",
        },
        "unit_cost_increase": {
            "title": "Cost-to-revenue ratio increasing: +{increase_pct}%",
            "summary": "The total cost-to-revenue ratio went from {prev_ratio}% to {curr_ratio}% compared to the previous period, an increase of {increase_pct} points.",
            "suggestion": "Analyze which cost categories grew the most. Renegotiate contracts with main suppliers.",
        },
        "break_even_unreached": {
            "title": "Break-even not reached at mid-month",
            "summary": "On day {day} of the month, cumulative revenue is {current_revenue} vs a projected break-even of {projected_be}. Deficit: {deficit_pct}%.",
            "suggestion": "Intensify sales efforts in the coming weeks. Consider promotions or follow-ups with customers who have pending orders.",
        },
        "category_expense_trend": {
            "title": "\"{category}\" expenses rising for {months} months: +{increase_pct}%",
            "summary": "The \"{category}\" category went from {prev_amount} to {curr_amount} month-over-month, an increase of {increase_pct}%. Absolute increase: +{abs_increase}.",
            "suggestion": "Verify if the increase is justified by higher activity or if it's an uncontrolled cost. Compare with planned budget.",
        },
        "dso_worsening_trend": {
            "title": "Collection times worsening: DSO {current_dso:.0f} days",
            "summary": "Days Sales Outstanding went from {prev_dso:.0f} to {current_dso:.0f} days over the last 3 months, an increase of {increase_pct}%. Customers are paying later.",
            "suggestion": "Follow up on overdue payments. Consider stricter payment terms for new orders.",
        },
        "high_risk_invoice": {
            "title": "High-risk invoice: {amount} overdue by {overdue_days} days",
            "summary": "An invoice of {amount} ({revenue_pct}% of monthly revenue) is overdue by {overdue_days} days. Customer: \"{customer}\".",
            "suggestion": "Contact the customer immediately. Consider formal collection actions or debt recovery.",
        },
        "dpo_dso_imbalance": {
            "title": "Collection/payment imbalance: {gap:.0f}-day gap",
            "summary": "You pay suppliers in {dpo:.0f} days on average but collect from customers in {dso:.0f} days. You're financing your customers' cash cycle for {gap:.0f} days.",
            "suggestion": "Negotiate longer payment terms with suppliers and/or shorter terms with customers.",
        },
        "yoy_anomaly": {
            "title": "Revenue {change_pct}% vs same month last year",
            "summary": "In {month}, revenue is {current_amount} vs {prev_amount} in the same month last year. Change: {change_pct}%.",
            "suggestion": "Check whether the decline is due to seasonal factors, customer loss, or market changes.",
        },
        "positive_trend_break": {
            "title": "Trend reversal: first decline after {months} months of growth",
            "summary": "Revenue had been growing for {months} consecutive months. This month ({current_month}) shows a {decline_pct}% decline vs the previous month.",
            "suggestion": "Analyze the causes of the slowdown. It may be seasonal or signal a trend change.",
        },
        "weekly_statistical_anomaly": {
            "title": "Anomalous week: revenue {sigma:.1f}σ below average",
            "summary": "This week's revenue ({current_amount}) is statistically anomalous vs the average of the last {weeks} weeks ({avg_amount}). Deviation: {sigma:.1f} sigma.",
            "suggestion": "Check for specific causes (holidays, operational issues). If none, monitor next week.",
        },
        "supplier_concentration": {
            "title": "{pct}% of purchases from a single supplier",
            "summary": "Supplier \"{supplier}\" accounts for {pct}% of total purchases ({amount}). High dependency increases operational risk.",
            "suggestion": "Identify alternative suppliers. Negotiate supply guarantee contracts if no alternatives exist.",
        },
        "dominant_product": {
            "title": "{pct}% of revenue from a single category",
            "summary": "The \"{category}\" category generates {pct}% of total revenue ({amount}). Strong dependency on one product/service increases risk.",
            "suggestion": "Evaluate diversification strategies to reduce dependency on a single product line.",
        },
        "fixed_cost_ratio_high": {
            "title": "Fixed costs at {ratio}% of revenue",
            "summary": "Fixed costs ({fixed_costs}) represent {ratio}% of revenue ({revenue}). A rigid cost structure reduces adaptability.",
            "suggestion": "Check if some fixed costs can be made variable. Consider renegotiating leases, contracts, subscriptions.",
        },
        # ── Category F: Commerce Operations ──────────────────────────────
        "order_backlog": {
            "title": "{count} draft orders pending for over 3 days",
            "summary": "{count} out of {total} orders have been in draft status for over 3 days. They may need confirmation or follow-up.",
            "suggestion": "Review draft orders and confirm or cancel those no longer relevant.",
        },
        "fulfillment_delay": {
            "title": "Order {order} awaiting fulfillment for {days} days",
            "summary": "Order {order} ({customer}) is confirmed but fulfillment has been pending for {days} days.",
            "suggestion": "Check the shipping or pickup status and update fulfillment accordingly.",
        },
        "payment_limbo": {
            "title": "Payment {amount} collected but order {order} not confirmed",
            "summary": "Order {order} received payment of {amount} {hours} hours ago but hasn't been confirmed. Money is in limbo.",
            "suggestion": "Confirm the order immediately to register revenue in cashflow.",
        },
        "event_low_fill": {
            "title": "Event '{name}' at {fill:.0f}% capacity",
            "summary": "Event '{name}' on {date} has only {booked}/{capacity} seats booked ({fill:.0f}%). The event is less than 3 days away.",
            "suggestion": "Consider last-minute promotion, customer reminders, or price reduction to boost bookings.",
        },
        "rental_idle": {
            "title": "Rental '{name}' unused in last 30 days",
            "summary": "Product '{name}' has had zero rentals in the last 30 days. It may be a dormant cost.",
            "suggestion": "Consider price reduction, promotion, or removal from catalog if the product has no demand.",
        },
        "cancellation_spike": {
            "title": "Cancellation rate at {rate:.0f}% in last 7 days",
            "summary": "{cancelled} orders cancelled out of {total} in the last 7 days ({rate:.0f}%). A rate above 20% requires attention.",
            "suggestion": "Analyze cancellation reasons. Contact customers for feedback. Check for order process issues.",
        },
    },

    # ═════════════════════════════════════════════════════════════════════════
    # DEUTSCH
    # ═════════════════════════════════════════════════════════════════════════
    "de": {
        "cash_runway_critical": {
            "title": "Kritische Finanzreichweite: {days:.0f} Tage",
            "summary": "Bei der aktuellen Ausgabenrate reichen die Ressourcen für ca. {days:.0f} Tage. Die Nettomarge beträgt {margin}.",
            "suggestion": "Priorität: nicht wesentliche Ausgaben reduzieren und Einnahmen beschleunigen. Nicht dringende Zahlungen verschieben.",
        },
        "persistent_negative_cashflow": {
            "title": "Negativer Cashflow an {neg_days} von {window} Tagen",
            "summary": "In den letzten {window} Tagen war der Tagessaldo (Einnahmen - Ausgaben) an {neg_days} Tagen negativ. Kumulierter Nettoverlust: {cumulative_loss}.",
            "suggestion": "Prüfen Sie, ob Zahlungseingänge verzögert sind oder außergewöhnliche Ausgaben vorliegen.",
        },
        "month_closed_loss": {
            "title": "Monat {month} mit Verlust abgeschlossen: {loss}",
            "summary": "Der Monat {month} verzeichnete Gesamteinnahmen von {revenue} gegenüber Gesamtausgaben von {outflows}, was zu einem Nettoverlust von {loss} führte ({loss_pct}% des Umsatzes).",
            "summary_severe": "Der Monat {month} verzeichnete Einnahmen von {revenue} gegenüber Ausgaben von {outflows} — für jeden €1 Umsatz wurden €{cost_per_revenue} Kosten verursacht. Nettoverlust: {loss}.",
            "suggestion": "Analysieren Sie die wichtigsten Kostenpositionen des Monats. Vergleichen Sie mit den Vormonaten.",
        },
        "revenue_concentration": {
            "title": "{pct}% des Umsatzes hängen von einem einzelnen Kunden ab",
            "summary": "Der Kunde \"{customer}\" generiert {pct}% des Gesamtumsatzes im Zeitraum ({amount}).",
            "suggestion": "Diversifizieren Sie den Kundenstamm, um die Abhängigkeit von einem einzelnen Kunden zu reduzieren.",
        },
        "margin_erosion_trend": {
            "title": "Marge seit {months} aufeinanderfolgenden Monaten rückläufig",
            "summary": "Die Nettomarge ist von {start_margin}% ({start_month}) auf {end_margin}% ({end_month}) gefallen, eine Reduzierung um {erosion_pp} Prozentpunkte.",
            "suggestion": "Prüfen Sie, ob die Kosten gestiegen oder die Verkaufspreise gesunken sind.",
        },
        "unit_cost_increase": {
            "title": "Kosten-Umsatz-Verhältnis steigend: +{increase_pct}%",
            "summary": "Das Verhältnis Gesamtkosten zu Umsatz stieg von {prev_ratio}% auf {curr_ratio}%, ein Anstieg von {increase_pct} Punkten.",
            "suggestion": "Analysieren Sie, welche Kostenkategorien am stärksten gewachsen sind.",
        },
        "break_even_unreached": {
            "title": "Break-even zur Monatsmitte nicht erreicht",
            "summary": "Am Tag {day} des Monats betragen die kumulierten Einnahmen {current_revenue} gegenüber einem projizierten Break-even von {projected_be}. Defizit: {deficit_pct}%.",
            "suggestion": "Vertriebsaktivitäten in den kommenden Wochen intensivieren.",
        },
        "category_expense_trend": {
            "title": "Ausgaben \"{category}\" seit {months} Monaten steigend: +{increase_pct}%",
            "summary": "Die Kategorie \"{category}\" stieg von {prev_amount} auf {curr_amount}, ein Anstieg von {increase_pct}%. Absoluter Anstieg: +{abs_increase}.",
            "suggestion": "Prüfen Sie, ob der Anstieg durch höhere Aktivität gerechtfertigt ist.",
        },
        "dso_worsening_trend": {
            "title": "Inkassozeiten verschlechtern sich: DSO {current_dso:.0f} Tage",
            "summary": "Die durchschnittliche Inkassodauer stieg von {prev_dso:.0f} auf {current_dso:.0f} Tage in den letzten 3 Monaten (+{increase_pct}%).",
            "suggestion": "Überfällige Zahlungen nachverfolgen. Strengere Zahlungsbedingungen für neue Aufträge erwägen.",
        },
        "high_risk_invoice": {
            "title": "Hochrisiko-Rechnung: {amount} seit {overdue_days} Tagen überfällig",
            "summary": "Eine Rechnung über {amount} ({revenue_pct}% des Monatsumsatzes) ist seit {overdue_days} Tagen überfällig. Kunde: \"{customer}\".",
            "suggestion": "Kontaktieren Sie den Kunden sofort. Formelle Mahnverfahren erwägen.",
        },
        "dpo_dso_imbalance": {
            "title": "Ungleichgewicht Inkasso/Zahlungen: Lücke von {gap:.0f} Tagen",
            "summary": "Sie bezahlen Lieferanten in {dpo:.0f} Tagen, kassieren aber von Kunden in {dso:.0f} Tagen. Sie finanzieren den Cash-Zyklus Ihrer Kunden für {gap:.0f} Tage.",
            "suggestion": "Längere Zahlungsfristen mit Lieferanten und/oder kürzere mit Kunden aushandeln.",
        },
        "yoy_anomaly": {
            "title": "Umsatz {change_pct}% gegenüber demselben Monat im Vorjahr",
            "summary": "Im {month} beträgt der Umsatz {current_amount} gegenüber {prev_amount} im gleichen Monat des Vorjahres. Veränderung: {change_pct}%.",
            "suggestion": "Prüfen Sie, ob der Rückgang saisonbedingt, durch Kundenverlust oder Marktveränderungen verursacht wurde.",
        },
        "positive_trend_break": {
            "title": "Trendumkehr: erster Rückgang nach {months} Monaten Wachstum",
            "summary": "Der Umsatz war {months} aufeinanderfolgende Monate gewachsen. Dieser Monat ({current_month}) zeigt einen Rückgang von {decline_pct}%.",
            "suggestion": "Analysieren Sie die Ursachen der Verlangsamung. Es könnte saisonal sein oder einen Trendwechsel signalisieren.",
        },
        "weekly_statistical_anomaly": {
            "title": "Anomale Woche: Umsatz {sigma:.1f}σ unter dem Durchschnitt",
            "summary": "Der Wochenumsatz ({current_amount}) ist statistisch anomal im Vergleich zum Durchschnitt der letzten {weeks} Wochen ({avg_amount}). Abweichung: {sigma:.1f} Sigma.",
            "suggestion": "Prüfen Sie spezifische Ursachen (Feiertage, betriebliche Probleme). Falls keine, nächste Woche beobachten.",
        },
        "supplier_concentration": {
            "title": "{pct}% der Einkäufe von einem einzigen Lieferanten",
            "summary": "Der Lieferant \"{supplier}\" macht {pct}% der Gesamteinkäufe aus ({amount}). Hohe Abhängigkeit erhöht das operative Risiko.",
            "suggestion": "Alternative Lieferanten identifizieren. Liefergarantie-Verträge aushandeln, falls keine Alternativen bestehen.",
        },
        "dominant_product": {
            "title": "{pct}% des Umsatzes aus einer einzigen Kategorie",
            "summary": "Die Kategorie \"{category}\" generiert {pct}% des Gesamtumsatzes ({amount}).",
            "suggestion": "Diversifizierungsstrategien bewerten, um die Abhängigkeit von einer einzelnen Produktlinie zu reduzieren.",
        },
        "fixed_cost_ratio_high": {
            "title": "Fixkosten bei {ratio}% des Umsatzes",
            "summary": "Die Fixkosten ({fixed_costs}) machen {ratio}% des Umsatzes aus ({revenue}). Eine starre Kostenstruktur verringert die Anpassungsfähigkeit.",
            "suggestion": "Prüfen Sie, ob einige Fixkosten variabilisiert werden können. Mieten, Verträge, Abonnements neu verhandeln.",
        },
    },

    # ═════════════════════════════════════════════════════════════════════════
    # FRANÇAIS
    # ═════════════════════════════════════════════════════════════════════════
    "fr": {
        "cash_runway_critical": {
            "title": "Autonomie financière critique : {days:.0f} jours",
            "summary": "Au rythme actuel des sorties, les ressources couvrent environ {days:.0f} jours. La marge nette de la période est de {margin}.",
            "suggestion": "Priorité : réduire les dépenses non essentielles et accélérer les encaissements.",
        },
        "persistent_negative_cashflow": {
            "title": "Cashflow négatif pendant {neg_days} jours sur {window}",
            "summary": "Au cours des {window} derniers jours, le solde quotidien (entrées - sorties) a été négatif pendant {neg_days} jours. Perte nette cumulée : {cumulative_loss}.",
            "suggestion": "Vérifier s'il y a des encaissements en retard ou des dépenses extraordinaires.",
        },
        "month_closed_loss": {
            "title": "Mois de {month} clôturé en perte : {loss}",
            "summary": "Le mois de {month} a enregistré des recettes de {revenue} contre des sorties de {outflows}, soit une perte nette de {loss} ({loss_pct}% du chiffre d'affaires).",
            "summary_severe": "Le mois de {month} a enregistré des recettes de {revenue} contre des sorties de {outflows} — pour chaque €1 de chiffre d'affaires, €{cost_per_revenue} de coûts ont été engagés. Perte nette : {loss}.",
            "suggestion": "Analyser les principaux postes de coûts du mois. Comparer avec les mois précédents.",
        },
        "revenue_concentration": {
            "title": "{pct}% du chiffre d'affaires dépend d'un seul client",
            "summary": "Le client \"{customer}\" génère {pct}% du chiffre d'affaires total sur la période ({amount}).",
            "suggestion": "Diversifier la base clients pour réduire la dépendance à un seul client.",
        },
        "margin_erosion_trend": {
            "title": "Marge en baisse depuis {months} mois consécutifs",
            "summary": "La marge nette est passée de {start_margin}% ({start_month}) à {end_margin}% ({end_month}), une réduction de {erosion_pp} points.",
            "suggestion": "Vérifier si les coûts ont augmenté ou les prix de vente ont diminué.",
        },
        "unit_cost_increase": {
            "title": "Ratio coûts/revenus en hausse : +{increase_pct}%",
            "summary": "Le ratio coûts totaux sur revenus est passé de {prev_ratio}% à {curr_ratio}%, une hausse de {increase_pct} points.",
            "suggestion": "Analyser quelles catégories de coûts ont le plus augmenté.",
        },
        "break_even_unreached": {
            "title": "Seuil de rentabilité non atteint à mi-mois",
            "summary": "Au jour {day} du mois, les revenus cumulés sont de {current_revenue} contre un seuil projeté de {projected_be}. Déficit : {deficit_pct}%.",
            "suggestion": "Intensifier l'activité commerciale dans les prochaines semaines.",
        },
        "category_expense_trend": {
            "title": "Dépenses \"{category}\" en hausse depuis {months} mois : +{increase_pct}%",
            "summary": "La catégorie \"{category}\" est passée de {prev_amount} à {curr_amount}, soit une hausse de {increase_pct}%. Hausse absolue : +{abs_increase}.",
            "suggestion": "Vérifier si la hausse est justifiée par une activité accrue.",
        },
        "dso_worsening_trend": {
            "title": "Délais d'encaissement en hausse : DSO {current_dso:.0f} jours",
            "summary": "Le délai moyen d'encaissement est passé de {prev_dso:.0f} à {current_dso:.0f} jours sur les 3 derniers mois (+{increase_pct}%).",
            "suggestion": "Relancer les paiements en retard. Envisager des conditions de paiement plus strictes.",
        },
        "high_risk_invoice": {
            "title": "Facture à haut risque : {amount} en retard de {overdue_days} jours",
            "summary": "Une facture de {amount} ({revenue_pct}% du CA mensuel) est en retard de {overdue_days} jours. Client : \"{customer}\".",
            "suggestion": "Contacter le client immédiatement. Envisager des actions de recouvrement.",
        },
        "dpo_dso_imbalance": {
            "title": "Déséquilibre encaissements/paiements : écart de {gap:.0f} jours",
            "summary": "Vous payez les fournisseurs en {dpo:.0f} jours mais encaissez des clients en {dso:.0f} jours. Vous financez le cycle de trésorerie de vos clients pendant {gap:.0f} jours.",
            "suggestion": "Négocier des délais de paiement plus longs avec les fournisseurs et/ou plus courts avec les clients.",
        },
        "yoy_anomaly": {
            "title": "Revenus {change_pct}% par rapport au même mois l'année dernière",
            "summary": "En {month}, le CA est de {current_amount} contre {prev_amount} le même mois l'an dernier. Variation : {change_pct}%.",
            "suggestion": "Vérifier si la baisse est saisonnière, due à une perte de clients ou à des changements de marché.",
        },
        "positive_trend_break": {
            "title": "Inversion de tendance : premier recul après {months} mois de croissance",
            "summary": "Le CA était en croissance depuis {months} mois consécutifs. Ce mois ({current_month}) affiche un recul de {decline_pct}%.",
            "suggestion": "Analyser les causes du ralentissement. Il peut être saisonnier ou signaler un changement de tendance.",
        },
        "weekly_statistical_anomaly": {
            "title": "Semaine anomale : revenus {sigma:.1f}σ sous la moyenne",
            "summary": "Le CA de la semaine ({current_amount}) est statistiquement anomal par rapport à la moyenne des {weeks} dernières semaines ({avg_amount}). Écart : {sigma:.1f} sigma.",
            "suggestion": "Vérifier les causes spécifiques (jours fériés, problèmes opérationnels). Sinon, surveiller la semaine prochaine.",
        },
        "supplier_concentration": {
            "title": "{pct}% des achats auprès d'un seul fournisseur",
            "summary": "Le fournisseur \"{supplier}\" représente {pct}% des achats totaux ({amount}). Une forte dépendance augmente le risque opérationnel.",
            "suggestion": "Identifier des fournisseurs alternatifs. Négocier des contrats avec garantie de fourniture.",
        },
        "dominant_product": {
            "title": "{pct}% du CA issu d'une seule catégorie",
            "summary": "La catégorie \"{category}\" génère {pct}% du CA total ({amount}).",
            "suggestion": "Évaluer des stratégies de diversification pour réduire la dépendance à une seule ligne de produit.",
        },
        "fixed_cost_ratio_high": {
            "title": "Coûts fixes à {ratio}% du CA",
            "summary": "Les coûts fixes ({fixed_costs}) représentent {ratio}% du CA ({revenue}). Une structure de coûts rigide réduit la capacité d'adaptation.",
            "suggestion": "Vérifier si certains coûts fixes peuvent être variabilisés. Renégocier loyers, contrats, abonnements.",
        },
    },
}


def localize_title(alert_type: str, locale: str, **kwargs) -> str:
    """Return localized title with format variables applied."""
    return _resolve(alert_type, locale, "title", **kwargs)


def localize_summary(alert_type: str, locale: str, variant: str = "", **kwargs) -> str:
    """Return localized summary with format variables applied.

    v14.2 (P2.4b): the optional ``variant`` parameter lets a rule pick an
    alternative summary template (e.g. ``variant="severe"`` → field
    ``summary_severe``) when the default template would produce a
    nonsensical narrative — for example, "perdita pari al 1000% dei
    ricavi" when outflows are 11× revenue.

    If the variant-specific field is missing in the i18n dict the
    resolver transparently falls back to the canonical ``summary``
    template, so partial translations don't break the alert. This
    keeps the contract backward-compatible: callers that don't pass
    ``variant`` see exactly the v14.1 behaviour.
    """
    field_name = f"summary_{variant}" if variant else "summary"
    out = _resolve(alert_type, locale, field_name, **kwargs)
    # Fallback when the variant template doesn't exist: _resolve returns
    # a "[alert_type.field]" placeholder for missing keys; we detect
    # that and fall back to the canonical summary template so partial
    # translations never reach the user as raw placeholder strings.
    if variant and out.startswith("[") and out.endswith("]"):
        return _resolve(alert_type, locale, "summary", **kwargs)
    return out


def localize_suggestion(alert_type: str, locale: str, **kwargs) -> str:
    """Return localized suggested action with format variables applied."""
    return _resolve(alert_type, locale, "suggestion", **kwargs)


def _resolve(alert_type: str, locale: str, field: str, **kwargs) -> str:
    """Resolve a template from the _L dict with fallback to Italian."""
    lang_dict = _L.get(locale) or _L.get("it", {})
    type_dict = lang_dict.get(alert_type)
    if not type_dict:
        # Fallback to Italian
        type_dict = _L.get("it", {}).get(alert_type, {})
    template = type_dict.get(field, "")
    if not template:
        return f"[{alert_type}.{field}]"
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError, IndexError):
        return template
