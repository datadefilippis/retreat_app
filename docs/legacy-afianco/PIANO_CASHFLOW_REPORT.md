# Piano Evoluzione Cash Flow Monitor — Analisi & Roadmap

## 1. STATO ATTUALE

### KPI attuali (6 card)
| # | KPI | Formula | Note |
|---|-----|---------|------|
| 1 | Ricavi Totali | SUM(sales.amount) | con trend % vs periodo precedente |
| 2 | Spese Operative (Bucket A) | SUM(expenses.amount) | trend % (inverso: giù = bene) |
| 3 | Acquisti Fornitori (Bucket B) | SUM(purchases.amount) | + purchase_ratio % su ricavi |
| 4 | Costi Fissi (Bucket C) | prorata su periodo | da tabella fixed_costs |
| 5 | Risultato Netto | Ricavi - A - B - C | colorato verde/rosso |
| 6 | Incidenza Uscite | (A+B+C) / Ricavi × 100 | alert se > 80% |

### Grafici attuali (7)
1. Sales vs Expenses (bar giornaliero)
2. Net Cashflow giornaliero (area)
3. Cashflow Cumulato (area)
4. Trend Ricavi con MA7 (line)
5. Trend Spese con MA7 (line)
6. Categorie Pie (vendite + spese top 5)
7. Categorie Bar orizzontali (ranking)

### Alert Rules (4)
1. Ricavi sotto media 30gg (soglie 10/20/30%)
2. Spese sopra media 30gg (soglie 10/20/30%)
3. Spike per categoria spesa (soglia 50%)
4. Cashflow negativo consecutivo (3+ giorni)

### Dati AI Insight
L'AI riceve: totali periodo, 3 bucket, medie giornaliere, trend vs periodo precedente, top 3 categorie spesa, anomalie (giorni negativi, vendite basse, spese alte).

### Campi DB esistenti ma NON utilizzati
- `sales_records.payment_status` (paid/pending/overdue)
- `sales_records.payment_date` (data incasso effettivo)
- `sales_records.customer_id` (FK → customers)
- `sales_records.channel`
- `expense_records.is_paid`, `expense_records.payment_date`
- `purchase_records.payment_status`, `purchase_records.due_date`
- `purchase_records.invoice_number`
- `customers.*` (anagrafica clienti)
- `suppliers.*` (anagrafica fornitori)
- `products.*` (catalogo prodotti)

---

## 2. GAP ANALYSIS — Cosa manca per massimo valore

### A. Dati mancanti nel modello attuale
| Gap | Impatto | Soluzione |
|-----|---------|-----------|
| Nessuna previsione futura di cassa | L'imprenditore non sa se tra 30gg sarà in difficoltà | Usare due_date acquisti + payment_date vendite per forecast |
| Nessun tracking crediti vs debiti | Non si vede il "cash gap" | Attivare payment_status su vendite e acquisti |
| Nessun margine per prodotto/servizio | Non si sa cosa è redditizio | Collegare sales ↔ purchases per categoria/prodotto |
| Nessuna stagionalità | Trend YoY invisibile | Confronto stesso periodo anno precedente |
| Concentrazione clienti/fornitori | Rischio non visibile | Analisi Pareto su customer_id e supplier_name |
| Break-even non calcolato | Non si sa la soglia minima | CF / (1 - CV/Ricavi) |
| Nessun modulo fatture/preventivi | Processo frammentato, dati persi | Nuovo modulo documenti |

### B. Variabili da aggiungere al DB

#### Su `purchase_records` (già parzialmente presente):
```
payment_date: str (ISO)        # Data pagamento effettivo (NUOVA)
paid_amount: float             # Importo pagato (per pagamenti parziali)
```

#### Su `sales_records` (campi esistenti, da valorizzare):
```
payment_status: "paid"|"pending"|"overdue"  # GIA' ESISTE, va reso obbligatorio
payment_date: str                            # GIA' ESISTE, va popolato
customer_id: str                             # GIA' ESISTE, va collegato
due_date: str (ISO)                          # NUOVA - scadenza fattura cliente
```

#### Nuova collection `invoices` (per modulo fatture/preventivi):
```python
{
    _id: str,
    organization_id: str,
    type: "invoice" | "quote" | "credit_note",     # Fattura, Preventivo, Nota di credito
    status: "draft" | "sent" | "accepted" | "paid" | "overdue" | "cancelled",
    number: str,                    # Numero progressivo (es. FT-2026/001)
    date: str,                      # Data emissione
    due_date: str,                  # Scadenza
    customer_id: str,               # FK → customers
    customer_name: str,             # Denormalizzato
    customer_email: str,
    customer_address: str,
    customer_vat: str,              # P.IVA / CF
    items: [
        {
            description: str,
            quantity: float,
            unit_price: float,
            tax_rate: float,        # es. 22 per IVA 22%
            total: float,           # qty × unit_price
        }
    ],
    subtotal: float,                # Somma items.total
    tax_total: float,               # Somma IVA per aliquota
    total: float,                   # subtotal + tax_total
    notes: str,                     # Note libere
    payment_terms: str,             # "30gg" | "60gg" | "immediato"
    payment_method: str,            # "bonifico" | "carta" | "contanti" | "ri.ba"

    # Dati azienda (da org settings)
    company_name: str,
    company_vat: str,
    company_address: str,
    company_iban: str,

    # Tracking
    paid_date: str,                 # Quando è stata pagata
    paid_amount: float,             # Per pagamenti parziali
    linked_sale_id: str,            # FK → sales_records (opzionale)
    converted_from: str,            # FK → invoices._id (preventivo → fattura)

    pdf_path: str,                  # Path al PDF generato
    created_at: datetime,
    updated_at: datetime,
}
```

---

## 3. PIANO KPI — Dashboard ideale per l'imprenditore

### TIER 1 — KPI Primari (strip principale, sempre visibili)

| # | KPI | Formula | Perché è vitale |
|---|-----|---------|-----------------|
| 1 | **Ricavi** | SUM vendite periodo | Volume d'affari |
| 2 | **Margine Operativo** | Ricavi - Spese Op. - Acquisti | Quanto resta dopo i costi variabili |
| 3 | **Margine Operativo %** | Margine Op. / Ricavi × 100 | Efficienza operativa (target >20%) |
| 4 | **Risultato Netto** | Ricavi - A - B - C | Bottom line reale |
| 5 | **Cash Position** | Saldo cassa cumulato nel periodo | Liquidità disponibile |
| 6 | **Burn Rate** | Uscite medie giornaliere | Quanto "brucia" al giorno |

### TIER 2 — KPI di Controllo (sezione dedicata, espandibile)

| # | KPI | Formula | Insight |
|---|-----|---------|---------|
| 7 | **Incidenza Costi Fissi** | C / Ricavi × 100 | Peso strutturale (target <30%) |
| 8 | **Incidenza Acquisti** | B / Ricavi × 100 | Food cost / costo materie |
| 9 | **Break-Even Point** | C / (1 - (A+B)/Ricavi) | Fatturato minimo per coprire i costi |
| 10 | **Giorni di Autonomia** | Cash Position / Burn Rate | Quanti giorni puoi operare senza nuovi ricavi |
| 11 | **DSO** (Days Sales Outstanding) | (Crediti aperti / Ricavi) × gg periodo | Tempo medio incasso clienti |
| 12 | **DPO** (Days Payable Outstanding) | (Debiti aperti / Acquisti) × gg periodo | Tempo medio pagamento fornitori |

### TIER 3 — KPI Strategici (insights AI + grafici)

| # | KPI | Formula | Insight |
|---|-----|---------|---------|
| 13 | **Cash Conversion Cycle** | DSO - DPO | Efficienza ciclo finanziario |
| 14 | **Concentrazione Clienti** | % ricavi da top 3 clienti | Rischio dipendenza |
| 15 | **Concentrazione Fornitori** | % acquisti da top 3 fornitori | Rischio supply chain |
| 16 | **Trend YoY** | Ricavi periodo / Ricavi stesso periodo anno scorso | Crescita reale |
| 17 | **Scadenzario Netto 30gg** | Incassi attesi - Pagamenti dovuti (prossimi 30gg) | Previsione liquidità |
| 18 | **Tasso di Conversione Preventivi** | Fatture emesse / Preventivi inviati × 100 | Efficacia commerciale |

---

## 4. PIANO GRAFICI — Dashboard ideale

### Tab "Panoramica" (Overview)

1. **KPI Strip Tier 1** — 6 card con sparkline trend (EVOLUZIONE dell'attuale)

2. **Cashflow Giornaliero** — ComposedChart
   - Bar: Entrate (verde) vs Uscite (rosso, stacked A+B+C)
   - Line: Net cashflow
   - NUOVO: Area ombrata per forecast (giorni futuri basati su scadenze)

3. **Cashflow Cumulato con Forecast**
   - Area: Storico (teal solido)
   - Area tratteggiata: Previsione 30gg basata su scadenze note
   - Linea rossa orizzontale: Break-even / soglia critica

4. **Composizione Uscite (Waterfall)**
   - NUOVO: Waterfall chart che mostra Ricavi → -A → -B → -C → Risultato Netto
   - Visualizza immediatamente dove va il denaro

5. **Trend MA7 con Bande**
   - EVOLUZIONE: Aggiungere banda min-max oltre alla media mobile
   - Evidenzia volatilità ricavi/spese

### Tab "Analisi" (NUOVA)

6. **Pareto Clienti** — Bar + Line cumulativa
   - Top 10 clienti per fatturato
   - Linea cumulativa % (regola 80/20)

7. **Pareto Fornitori** — Bar + Line cumulativa
   - Top 10 fornitori per spesa
   - Linea cumulativa %

8. **Heatmap Giornaliera** — Calendar heatmap
   - NUOVO: Griglia stile GitHub contributions
   - Colore = net cashflow del giorno (rosso = negativo, verde = positivo)
   - Vista immediata dei pattern settimanali/mensili

9. **Margine per Categoria** — Horizontal stacked bar
   - Per ogni categoria: ricavo vs costo associato
   - Evidenzia le categorie più profittevoli

### Tab "Scadenzario" (NUOVA — richiede due_date)

10. **Scadenzario Visuale** — Timeline chart
    - NUOVO: Incassi attesi (verde, sopra asse X) vs Pagamenti dovuti (rosso, sotto)
    - Prossimi 60 giorni
    - Saldo netto proiettato

11. **Aging Crediti** — Stacked bar
    - NUOVO: Fatture cliente per fascia di scadenza
    - 0-30gg | 31-60gg | 61-90gg | >90gg
    - Identifica ritardi pagamento

12. **Aging Debiti** — Stacked bar
    - Stessa struttura per debiti verso fornitori

### Tab "Costi Fissi" (EVOLUZIONE)

13. **Fixed vs Variable Donut** — Già presente, da mantenere
14. **Break-Even Chart** — NUOVO: Line chart
    - Asse X: fatturato simulato (50%→150% dell'attuale)
    - Linee: costi totali vs ricavi
    - Punto di intersezione = break-even evidenziato

### Tab "Fatture" (NUOVA — modulo fatture)

15. **Funnel Preventivi → Fatture** — Funnel chart
    - Draft → Sent → Accepted → Paid
    - Tasso di conversione per step

16. **Fatturato Mensile** — Bar chart
    - Importo fatturato per mese
    - Overlay: importo incassato per mese

---

## 5. DATI DA DARE ALL'AI — Contesto arricchito

### Attuale (mantenere)
- Totali periodo 3 bucket
- Medie giornaliere
- Trend vs periodo precedente
- Top categorie spesa
- Anomalie

### Da aggiungere
```
POSIZIONE DI CASSA:
- Cash Position attuale: €X
- Burn rate giornaliero: €X/giorno
- Giorni di autonomia: X giorni
- Break-even mensile: €X

CICLO FINANZIARIO:
- DSO (tempo incasso): X giorni
- DPO (tempo pagamento): X giorni
- Cash Conversion Cycle: X giorni
- Crediti aperti: €X (di cui scaduti: €X)
- Debiti aperti: €X (di cui scaduti: €X)

CONCENTRAZIONE RISCHIO:
- Top 3 clienti: X% dei ricavi → [nomi e %]
- Top 3 fornitori: X% degli acquisti → [nomi e %]
- Cliente più grande: [nome] (X%)

SCADENZARIO PROSSIMI 30GG:
- Incassi attesi: €X
- Pagamenti dovuti: €X
- Saldo netto previsto: €X

STAGIONALITÀ (se dati >12 mesi):
- Stesso periodo anno scorso: €X ricavi
- Variazione YoY: ±X%

FATTURAZIONE (se modulo attivo):
- Preventivi inviati: X (€X totale)
- Tasso conversione: X%
- Fatture non pagate: X (€X)
- Tempo medio incasso: X giorni
```

### Prompt AI aggiornato — nuove regole
Aggiungere al system prompt:
- Se DSO > 60gg: segnalare rischio liquidità da crediti
- Se concentrazione top client > 40%: segnalare rischio dipendenza
- Se giorni di autonomia < 30: alert critico
- Se CCC > 90gg: segnalare inefficienza ciclo finanziario
- Se YoY negativo: contestualizzare (stagionalità vs declino)
- Suggerire azioni specifiche basate su scadenzario

---

## 6. ROADMAP IMPLEMENTATIVA

### Fase 1 — Quick Wins (nessun cambio DB)
**Effort: basso | Valore: alto**

1. Aggiungere KPI: Margine Operativo %, Break-Even, Burn Rate, Giorni Autonomia
2. Aggiungere grafico Waterfall (composizione uscite)
3. Arricchire contesto AI con burn rate, break-even, giorni autonomia
4. Aggiungere Pareto fornitori (supplier_name già presente in purchases)

### Fase 2 — Sblocco Scadenzario (aggiunta campi)
**Effort: medio | Valore: molto alto**

1. Aggiungere `due_date` a `sales_records`
2. Rendere `payment_status` valorizzato su vendite e acquisti
3. Aggiungere `payment_date` effettiva su `purchase_records`
4. Implementare calcolo DSO / DPO / Cash Conversion Cycle
5. Costruire tab Scadenzario con aging e forecast
6. Arricchire AI con dati ciclo finanziario

### Fase 3 — Modulo Fatture/Preventivi
**Effort: alto | Valore: alto**

1. Creare collection `invoices` con schema completo
2. CRUD fatture + preventivi
3. Generazione PDF (intestazione azienda, righe, totali, IVA)
4. Conversione preventivo → fattura
5. Collegamento fattura → sale_record (incasso)
6. Numerazione progressiva automatica
7. Tab dashboard con funnel e KPI fatturazione

### Fase 4 — Intelligence Avanzata
**Effort: medio | Valore: alto**

1. Forecast cashflow a 30/60/90gg basato su scadenze + pattern storici
2. Heatmap calendar
3. Confronto YoY (se dati sufficienti)
4. Analisi concentrazione clienti (richiede valorizzare customer_id)
5. Scoring salute aziendale (composito da tutti i KPI)
6. Alert predittivi ("tra 15gg potresti avere cash gap di €X")

---

## 7. PRIORITA' CONSIGLIATA

```
IMPATTO PER L'IMPRENDITORE:

[Fase 1] ████████████░░░  80% valore, 20% effort
   → KPI che rispondono a "come sta la mia azienda?"
   → Waterfall che mostra "dove vanno i miei soldi?"

[Fase 2] █████████████░░  90% valore, 40% effort
   → Scadenzario risponde a "avrò cash tra 30gg?"
   → DSO/DPO rispondono a "quanto è efficiente il mio ciclo?"

[Fase 3] ██████████░░░░░  70% valore, 60% effort
   → Fatture dentro la piattaforma = meno frammentazione
   → Dati auto-alimentano il cashflow monitor

[Fase 4] ████████████████ 100% valore, 30% effort (se Fase 2 fatta)
   → Forecast predittivo = la killer feature per PMI
   → L'AI diventa un vero advisor finanziario
```

---

## 8. SCHEMA RIASSUNTIVO KPI FINALI

```
┌─────────────────────────────────────────────────────────┐
│                    TIER 1 — STRIP PRINCIPALE            │
│                                                         │
│  Ricavi    Margine Op.   Margine%   Netto   Cash   Burn │
│  €45.2K    €28.1K        62.2%     €18.1K  €52K  €900  │
│  ↑12%      ↑8%                     ↑15%                 │
├─────────────────────────────────────────────────────────┤
│                    TIER 2 — CONTROLLO                   │
│                                                         │
│  Break-Even   Autonomia   DSO    DPO    Costi Fissi%   │
│  €32.0K/mese  58 giorni   42gg   35gg   22.2%          │
├─────────────────────────────────────────────────────────┤
│                    TIER 3 — STRATEGICI                  │
│                                                         │
│  CCC: 7gg  │  Top3 Clienti: 55%  │  Scadenzario +30gg │
│  YoY: +18% │  Top3 Fornit.: 62%  │  Netto: +€12.5K    │
└─────────────────────────────────────────────────────────┘
```
