# Cashflow Monitor — Financial Model v1.0
**Modulo:** cashflow_monitor
**Data:** 2026-03-12
**Stato:** Definitivo — da usare come riferimento per backend, frontend e AI

---

## 1. Executive Summary

Il modulo **Cashflow Monitor** risponde a una domanda semplice che ogni imprenditore PMI ha ogni mattina:

> *"Quanti soldi sono entrati, quanti sono usciti, e quanto mi rimane per stare in piedi?"*

Il modello finanziario è volutamente semplice, orientato alla liquidità operativa — non alla contabilità ufficiale. Non è un bilancio, non è un rendiconto IAS/IFRS. È un cruscotto di sopravvivenza quotidiana per chi gestisce un'attività reale.

**Tre fonti di dati, tre bucket distinti. Un unico numero finale che conta.**

---

## 2. Current Data Capability Analysis

### 2.1 Sorgenti dati disponibili

| Collection | Cosa contiene | Come viene popolata |
|---|---|---|
| `sales_records` | Transazioni di vendita (data, importo, categoria, canale) | Upload CSV/XLSX o inserimento manuale |
| `expense_records` | Spese operative correnti (data, importo, categoria, fornitore) | Upload CSV/XLSX o inserimento manuale |
| `purchase_records` | Acquisti da fornitori (data, fornitore, quantità, unità, prezzo) | Upload CSV/XLSX o inserimento manuale |
| `fixed_costs` | Costi fissi strutturali ricorrenti (importo, frequenza, date validità) | Solo inserimento manuale |

### 2.2 Cosa è già calcolato nel codice (stato attuale)

| Metrica | Calcolata | Inclusa nei KPI principali | Note |
|---|---|---|---|
| `total_sales` | ✅ | ✅ | Da `sales_records` |
| `total_expenses` | ✅ | ✅ | Da `expense_records` soli — alias "spese variabili" |
| `net_cashflow` | ✅ | ✅ | `total_sales - total_expenses` (expense_records only) |
| `fixed_costs_total` | ✅ | ✅ parziale | Proratato, visibile ma NON incluso in net_cashflow |
| `combined_expenses` | ✅ | ✅ | `total_expenses + fixed_costs_total` |
| `expense_ratio` | ✅ | ✅ | `total_expenses / total_sales × 100` |
| `burn_rate` | ✅ | ✅ | `avg_daily_expenses` (da expense_records) |
| `supplier_purchases` | ✅ parziale | ❌ **GAP** | In DB e nei chart, NON nei KPI aggregati |
| `net_after_purchases` | ❌ | ❌ | Da definire |
| `net_after_fixed` | ❌ | ❌ | Da definire |

### 2.3 Il gap critico attuale

**`purchase_records` è attualmente un dato orfano nei KPI.**

È presente nel DB, è seedato con dati realistici (5 fornitori, 90 giorni), appare nell'endpoint `/analytics/charts` come campo `purchases`, ma **non entra in nessuna formula aggregata di KPI**. Il `net_cashflow` attuale è quindi incompleto perché ignora gli acquisti fornitori.

Questo non è un bug da correggere immediatamente — è una **scelta consapevole** da gestire con la migrazione descritta nella Sezione 6. Il modello attuale è internamente coerente; semplicemente non include ancora le uscite da acquisti nel conto principale.

---

## 3. Official Financial Model

### 3.1 Mappa concettuale

```
ENTRATE
└── Ricavi (sales_records)
        │
        ▼
USCITE — 3 bucket distinti, 3 nature diverse
├── Bucket A: Spese Operative Variabili  (expense_records)
│   → utilities, staff giornaliero, forniture, marketing, piccoli acquisti
│   → dipendono dal volume e dai giorni operativi
│
├── Bucket B: Acquisti Fornitori / COGS  (purchase_records)
│   → materie prime, merci, ingredienti in quantità
│   → legati al ciclo di produzione / approvvigionamento
│
└── Bucket C: Costi Strutturali Fissi    (fixed_costs)
    → affitto, stipendi, leasing, finanziamenti, abbonamenti
    → indipendenti dal volume, proratizzati al periodo

AGGREGATI
├── Variable Outflows    = Bucket A + Bucket B
├── Total Outflows       = Bucket A + Bucket B + Bucket C
├── Net Before Fixed     = Ricavi − Variable Outflows
└── Net After Fixed      = Ricavi − Total Outflows  ← il numero che conta davvero
```

### 3.2 Perché tre bucket e non uno

Un `expense_records` generico con tutto dentro è una trappola. Ogni bucket ha una natura di gestione diversa:

| | Bucket A: Operative | Bucket B: Acquisti | Bucket C: Fissi |
|---|---|---|---|
| **Controllo** | Giornaliero | Settimanale / per ordine | Mensile / contrattuale |
| **Prevedibilità** | Bassa | Media | Alta |
| **Leva di riduzione** | Immediata | Negoziazione fornitori | Rinegoziazione contratti |
| **Impatto su cashflow** | Continuo e frazionato | A blocchi (giorni di consegna) | Fisso e prevedibile |
| **Alert sensato** | Picco rispetto a media | Picco su fornitore singolo | Non serve (prevedibile) |

---

## 4. Metric-by-Metric Table

### 4.1 Metriche Core (già implementate, da mantenere stabili)

| # | Nome tecnico | Nome UI | Formula | Sorgenti | Stato |
|---|---|---|---|---|---|
| 1 | `total_sales` | Ricavi Totali | `Σ(sales_records.amount)` nel periodo | `sales_records` | ✅ Stabile |
| 2 | `operating_expenses` | Spese Operative | `Σ(expense_records.amount)` nel periodo | `expense_records` | ✅ Stabile (attuale alias: `total_expenses`) |
| 3 | `fixed_costs_total` | Costi Fissi | `Σ(amount × period_days / freq_days)` per costi attivi nel periodo | `fixed_costs` | ✅ Stabile |
| 4 | `avg_daily_sales` | Ricavo Medio / Giorno | `total_sales / days_with_data` | `sales_records` | ✅ Stabile |
| 5 | `avg_daily_expenses` | Spesa Media / Giorno | `operating_expenses / days_with_data` | `expense_records` | ✅ Stabile |
| 6 | `sales_trend_pct` | Var. Ricavi % | `(current − prev) / prev × 100` vs periodo precedente uguale lunghezza | `sales_records` | ✅ Stabile |
| 7 | `expenses_trend_pct` | Var. Spese % | `(current − prev) / prev × 100` vs periodo precedente | `expense_records` | ✅ Stabile |

### 4.2 Metriche Derivate — Fase 1 (già calcolate, da allineare al modello)

| # | Nome tecnico | Nome UI | Formula | Dipende da | Caveat |
|---|---|---|---|---|---|
| 8 | `net_cashflow` | Cashflow Operativo | `total_sales − operating_expenses` | #1, #2 | ⚠️ Non include acquisti né fissi. È il "margine operativo giornaliero". La UI deve essere chiara su cosa esclude. |
| 9 | `combined_expenses` | Spese Totali (A+C) | `operating_expenses + fixed_costs_total` | #2, #3 | ⚠️ Non include purchase_records (Bucket B). Nome "Spese Totali" è fuorviante — rinominare in "Spese Op. + Fissi" |
| 10 | `expense_ratio` | Incidenza Spese Operative | `operating_expenses / total_sales × 100` | #1, #2 | Misura quanto % dei ricavi viene assorbito dalle spese op. Standard per ristoranti: < 65%. |
| 11 | `burn_rate` | Burn Rate Giornaliero | `avg_daily_expenses` (alias di #5) | #5 | Il nome "burn rate" è appropriato solo se include tutte le uscite. Attualmente include solo Bucket A. Accettabile come indicatore di velocità di spesa operativa. |
| 12 | `top_expense_category` | Top Categoria Spesa | `argmax(expense_records.category)` | `expense_records` | Solo su Bucket A. Non considera purchase_records né fixed_costs. |
| 13 | `cashflow_trend_pct` | Var. Cashflow % | `(current_net − prev_net) / abs(prev_net) × 100` | #8 periodo precedente | Instabile se prev_net ≈ 0 o negativo. Gestire divisione per zero. |

### 4.3 Metriche Derivate — Fase 2 (da implementare al prossimo step)

Queste metriche **richiedono l'inclusione di `purchase_records` nel modello KPI**. Non devono essere mostrate finché Fase 2 non è implementata.

| # | Nome tecnico | Nome UI (proposto) | Formula | Dipende da | Priorità |
|---|---|---|---|---|---|
| 14 | `supplier_purchases` | Acquisti Fornitori | `Σ(purchase_records.total_price)` nel periodo | `purchase_records` | ALTA |
| 15 | `variable_outflows` | Uscite Variabili Totali | `operating_expenses + supplier_purchases` | #2, #14 | ALTA |
| 16 | `total_outflows` | Uscite Totali | `operating_expenses + supplier_purchases + fixed_costs_total` | #2, #14, #3 | ALTA |
| 17 | `net_before_fixed` | Margine ante Fissi | `total_sales − variable_outflows` | #1, #15 | ALTA |
| 18 | `net_after_fixed` | Risultato Netto | `total_sales − total_outflows` | #1, #16 | ALTA — questo è il numero che conta davvero |
| 19 | `purchase_ratio` | Incidenza Acquisti | `supplier_purchases / total_sales × 100` | #1, #14 | MEDIA |
| 20 | `total_outflow_ratio` | Incidenza Totale Uscite | `total_outflows / total_sales × 100` | #1, #16 | MEDIA |
| 21 | `cogs_approximation` | Costo del Venduto Appross. | `supplier_purchases + operating_expenses × cogs_factor` | #2, #14 | BASSA — solo dopo validazione |

### 4.4 Metriche Future — Non includere nel modulo v1

Queste metriche richiedono dati che il sistema non raccoglie ancora o che non sono affidabili con i dati attuali. **Non vanno promesse agli utenti ora.**

| Metrica | Perché non ancora | Prerequisito |
|---|---|---|
| Cashflow di cassa (cash basis) | Richiede tracking incassi effettivi vs competenza | Campo `payment_date` su tutti i record + raccolta sistematica |
| Previsione cashflow (forecast) | Richiede serie storica stabile + modello | ≥ 6 mesi di dati per org |
| Break-even giornaliero | Richiede COGS affidabile, separazione costi variabili/fissi per unità | Struttura dati più granulare |
| DSO / DPO (Days Sales/Payables Outstanding) | Richiede tracking scadenze + incassi | `payment_date`, `due_date` sistematici |
| Margine lordo % (Gross Margin) | Richiede costo del venduto preciso, non approssimato | COGS tracciato separatamente |
| EBITDA | Richiede ammortamenti, interessi — non tracciati | Fuori scope v1 |

---

## 5. Terminologia Ufficiale per UI e AI

### 5.1 Nomi definitivi per le metriche in UI

Questi nomi sono quelli da usare in label KPI, titoli grafici, testi AI insight, alert. **Coerenza assoluta tra frontend e AI.**

| Metrica tecnica | Label UI (breve) | Descrizione tooltip / AI |
|---|---|---|
| `total_sales` | **Ricavi** | Totale vendite nel periodo selezionato |
| `operating_expenses` | **Spese Operative** | Spese variabili correnti (utilities, forniture, staff, ecc.) |
| `supplier_purchases` | **Acquisti Fornitori** | Acquisti di materie prime e merci dai fornitori *(Fase 2)* |
| `fixed_costs_total` | **Costi Fissi** | Costi strutturali ricorrenti proratizzati al periodo (affitto, stipendi, ecc.) |
| `variable_outflows` | **Uscite Variabili** | Spese operative + acquisti fornitori *(Fase 2)* |
| `total_outflows` | **Uscite Totali** | Tutte le uscite del periodo *(Fase 2)* |
| `net_cashflow` | **Cashflow Operativo** | Ricavi meno spese operative. Non include acquisti fornitori né costi fissi. |
| `net_before_fixed` | **Margine ante Fissi** | Ricavi meno uscite variabili, prima dei costi strutturali *(Fase 2)* |
| `net_after_fixed` | **Risultato Netto** | Ricavi meno tutte le uscite. Il numero che conta davvero. *(Fase 2)* |
| `expense_ratio` | **Incidenza Spese Op.** | Quanta parte dei ricavi viene assorbita dalle spese operative |
| `burn_rate` | **Burn Rate / giorno** | Media giornaliera delle spese operative |
| `avg_daily_sales` | **Ricavo Medio / giorno** | Media giornaliera dei ricavi nel periodo |
| `sales_trend_pct` | **Var. Ricavi** | Variazione % rispetto al periodo precedente uguale |
| `expenses_trend_pct` | **Var. Spese Op.** | Variazione % rispetto al periodo precedente uguale |
| `top_expense_category` | **Top Categoria** | Categoria di spesa operativa con il maggior impatto |

### 5.2 Soglie di riferimento per una PMI ristorativa (contesto demo)

Da usare per colorare KPI, formulare alert e orientare il tono degli insight AI.

| Metrica | Verde (sano) | Giallo (attenzione) | Rosso (critico) |
|---|---|---|---|
| `expense_ratio` | < 60% | 60–80% | > 80% |
| `net_cashflow` | > 0 | 0 (pareggio) | < 0 |
| `sales_trend_pct` | > +5% | −5% / +5% | < −10% |
| `expenses_trend_pct` | < +5% | +5% / +20% | > +20% |
| Giorni consecutivi neg. cashflow | 0 | 1–2 | ≥ 3 |
| Categoria spike | — | +30% vs media | > +50% vs media |

### 5.3 Tono e framing per i testi AI

Il modulo parla a un **imprenditore PMI italiano**, non a un CFO. Il linguaggio deve essere:

- **Diretto:** "Martedì hai perso €400 rispetto alla media" non "Il 15/03 la metrica YoY è -16.3%"
- **Azionabile:** ogni insight finisce con almeno 1 azione concreta
- **Contestualizzato:** cita sempre il numero assoluto in €, non solo la percentuale
- **Non allarmista:** distingui tra rumore statistico e anomalia vera

**Framing ufficiale del modulo in UI:**
> *"Il Cashflow Monitor confronta i tuoi ricavi con le tue uscite operative, segnala anomalie e genera un'analisi settimanale con suggerimenti pratici."*

---

## 6. Cosa Include / Esclude il Modulo v1

### ✅ Cosa include (già disponibile e stabile)

- Tracking ricavi giornalieri da `sales_records`
- Tracking spese operative da `expense_records` (Bucket A)
- Tracking costi fissi ricorrenti da `fixed_costs` con proratio (Bucket C)
- KPI: Ricavi, Spese Op., Cashflow Operativo, Costi Fissi, Expense Ratio, Burn Rate
- Trend vs periodo precedente (7/30/90 gg e data_range)
- Serie giornaliera: ricavi, spese, cashflow giornaliero, cumulato
- Categorie spesa e ricavo (top per importo e percentuale)
- 4 tipi di alert automatici (calo ricavi, picco spese, spike categoria, negativo consecutivo)
- Insight narrativi AI in italiano con dati contestuali

### ⚠️ Cosa è presente nel DB ma non ancora nei KPI principali

- `purchase_records` (Bucket B — acquisti fornitori): tracciato, visibile nei grafici, **non ancora aggregato nei KPI**
- `combined_expenses` include solo Bucket A + C, NON Bucket B
- `net_cashflow` è "Cashflow Operativo" (sales − operative expenses), NON il cashflow reale totale

### ❌ Cosa il modulo non deve promettere (v1)

- Cashflow di cassa (cash basis / data di incasso effettivo)
- Previsione cashflow futura
- Margine lordo (Gross Margin)
- EBITDA o metriche contabili ufficiali
- Riconciliazione con conto bancario
- IVA, imposte, ritenute
- Contabilità in partita doppia

---

## 7. Financial Model Definitivo — Schema Sinottico

```
┌─────────────────────────────────────────────────────────────────┐
│                    CASHFLOW MONITOR v1                          │
│                  MODELLO FINANZIARIO UFFICIALE                  │
└─────────────────────────────────────────────────────────────────┘

ENTRATE
  total_sales            = Σ(sales_records.amount)        [CORE ✅]

USCITE
  operating_expenses     = Σ(expense_records.amount)      [CORE ✅]   Bucket A
  supplier_purchases     = Σ(purchase_records.total_price)[FASE 2 🔜] Bucket B
  fixed_costs_total      = Σ(proratio fixed_costs)        [CORE ✅]   Bucket C

AGGREGATI ATTUALI (v1)
  net_cashflow           = total_sales − operating_expenses         [CORE ✅]
  combined_expenses      = operating_expenses + fixed_costs_total   [CORE ✅]

AGGREGATI TARGET (v1 → v2, next step)
  variable_outflows      = operating_expenses + supplier_purchases  [FASE 2 🔜]
  total_outflows         = variable_outflows + fixed_costs_total    [FASE 2 🔜]
  net_before_fixed       = total_sales − variable_outflows          [FASE 2 🔜]
  net_after_fixed        = total_sales − total_outflows             [FASE 2 🔜]

METRICHE OPERATIVE (v1, tutte implementate)
  avg_daily_sales        = total_sales / days_with_data             [CORE ✅]
  avg_daily_expenses     = operating_expenses / days_with_data      [CORE ✅]
  burn_rate              = avg_daily_expenses                       [CORE ✅]
  expense_ratio          = operating_expenses / total_sales × 100   [CORE ✅]
  sales_trend_pct        = (cur − prev) / prev × 100               [CORE ✅]
  expenses_trend_pct     = (cur − prev) / prev × 100               [CORE ✅]

ALERT RULES (v1)
  sales_below_avg        → deviazione ricavi giornalieri vs media 30gg [CORE ✅]
  expenses_above_avg     → deviazione spese giornaliere vs media 30gg  [CORE ✅]
  category_expense_spike → picco categoria vs media categoria           [CORE ✅]
  consecutive_negative   → N giorni consecutivi cashflow operativo < 0  [CORE ✅]

NOTE IMPORTANTI PER L'AI (insight builder):
  - "cashflow netto" nel prompt = total_sales − operating_expenses (non include fissi né acquisti)
  - "spese totali combinate" nel prompt = combined_expenses = Bucket A + Bucket C
  - purchase_records NON entrano ancora nel prompt → da aggiungere in Fase 2
  - I giorni con cashflow negativo si riferiscono a cashflow operativo (Bucket A only)
```

---

## 8. Prossimi Step — Checklist per Fase 2

**Obiettivo Fase 2:** includere `purchase_records` (Bucket B) nel modello KPI e aggiornare UI e AI di conseguenza.

```
BACKEND:
□ analytics_repository: aggiungere aggregate_purchases_by_date()
□ overview_builder: aggiungere supplier_purchases ai KPI
□ overview_builder: calcolare variable_outflows, total_outflows, net_before_fixed, net_after_fixed
□ snapshot_builder: aggiungere le 4 nuove metriche
□ insight_builder: aggiungere supplier_purchases e net_after_fixed nel prompt
□ alert_rules: valutare se aggiungere alert su picco acquisti singolo fornitore

FRONTEND:
□ KPIStrip: aggiungere card "Acquisti Fornitori" (colore: arancione)
□ KPIStrip: sostituire/affiancare "Cashflow Operativo" con "Risultato Netto"
□ KPIStrip: rinominare "Spese Totali" → "Spese Op. + Fissi" (per chiarezza)
□ CashflowModulePage: mostrare breakdown 3 bucket nel tab Panoramica
□ Charts: includere purchases nella serie giornaliera

COMUNICAZIONE:
□ Aggiornare tooltip in UI per spiegare cosa include ogni metrica
□ Aggiornare system prompt AI con nuove metriche
□ Aggiornare SYSTEM_SPEC.md e questo documento
```

---

## 9. Ready for Next Step?

**Sì, il modulo v1 è solido e coerente internamente.**

Il modello attuale (v1) è:
- ✅ Internamente coerente (tutte le formule si basano su sorgenti reali disponibili)
- ✅ Comprensibile per una PMI (nessuna metrica richiede un commercialista per essere capita)
- ✅ Azionabile (gli alert e gli insight guidano a decisioni concrete)
- ✅ Tecnicamente stabile (nessun calcolo dipende da dati mancanti o inconsistenti)
- ⚠️ Incompleto sul lato acquisti fornitori (Bucket B è in DB ma non ancora nei KPI)
- ⚠️ Il "Cashflow Netto" mostrato in UI è in realtà un "Cashflow Operativo" — comunicarlo chiaramente nel tooltip

**La singola cosa più importante da fare prima di qualsiasi altra nuova feature:**
> Includere `purchase_records` nel calcolo di `total_outflows` e `net_after_fixed`.
> Senza questo, un ristorante che compra €1.500/settimana di materie prime vede un "cashflow netto" gonfio di €1.500 che in realtà non ha.

---

*Documento di riferimento per sviluppo backend, frontend e prompt AI — non modificare le definizioni senza aggiornare questo file.*
