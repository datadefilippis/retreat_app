# Simulazione multi-canale, consistenza globale e refinement Performance/Insights

**Data:** 2026-07-07 · **Metodo:** ordini VERI creati via API su retreat_dev per ogni canale × tipo, poi audit incrociato su tutti i registri (orders, sales_records, payment_schedules, /analytics/cashflow, CI overview, PP overview).

---

## PARTE 1 — La simulazione: cosa è stato creato

| # | Canale | Tipo | Esito |
|---|---|---|---|
| 1 | Checkout pubblico (store/directory) | Fisico ×2, ritiro in sede | ✅ 200 → draft `storefront_direct` |
| 2 | Checkout pubblico | Servizio (consulenza) | ✅ 200 → draft |
| 3 | Checkout pubblico | Digitale | ✅ 400 **onesto**: "file non ancora disponibile" (gate corretto: non vendi ciò che non puoi consegnare) |
| 4 | Checkout pubblico | Evento (ritiro, caparra) | ✅ 200 → draft + libro mastro creato |
| 5 | POS | Fisico | 🐛 **400 shipping_option_required** |
| 6 | Manuale admin | Servizio con scadenza | ✅ confermato, in tesoreria |
| 7 | Pagina Dati | Entrata manuale + Uscita | ✅ entrata in tesoreria (gamba C) |

## PARTE 2 — Verdetto di consistenza: il nucleo È solido

1. **Sync ordine↔registro vendite: PERFETTO.** Tutti i 7 ordini confermati (storefront, storefront_direct, manual) hanno record sincronizzati di importo identico, storni inclusi (ordine annullato → storno -800 presente).
2. **Aggregati puliti.** CI revenue 90d = 2.760€ = PP totalRevenue = esattamente la somma dei record da ordini. I 316 record legacy (v. sotto) sono **esclusi** dalle metriche (nessun customer_id/product_id).
3. **Anti-double-counting CG1 regge** anche sotto simulazione multi-canale: nessun importo contato due volte fra ledger, ordini e manuali.
4. **La catena manuale funziona**: entrata in Dati → tesoreria; ordine manuale → scadenzario → sollecito/mark-paid.

## PARTE 3 — I difetti trovati (in ordine di gravità)

### 🐛 B1 — CRITICO: la tesoreria conta i carrelli abbandonati
Il libro mastro nasce alla **creazione** dell'ordine-ritiro (draft). La gamba A di /incassi legge TUTTE le schedule → 9 schedule di ordini **draft** (8.800€!) e 1 di un ordine **cancellato** finiscono in "in arrivo/in ritardo". Il "2.400€ in ritardo" mostrato finora era in gran parte carrelli mai confermati. Anche il vecchio payments-overview (D3) ha lo stesso difetto da sempre.
**Fix:** la gamba A considera solo schedule di ordini `confirmed/completed` (join su order status, batch). Valori veri sui dati demo: in ritardo ~0€, in arrivo 1.680€ (saldi ORD-0002/0003).

### 🐛 B2 — POS bloccato sui prodotti fisici
Vendita al banco → `shipping_option_required`. Il router POS non passa il fulfillment: il default fisico=spedizione scatta anche in cassa. **Fix:** POS forza `local_pickup` (è la definizione stessa di POS). Stesso fix sul manuale admin (attrito già noto da CG1): il POST /orders accetta `fulfillment_mode` opzionale.

### 🧹 B3 — 316 record fantasma nella pagina Dati
Seed del vecchio BI ristorante ("Sales transaction", takeout/food_sales, 254.185€!) inquinano la LISTA della pagina Dati (non le metriche). Un operatore che apre Dati vede un ristorante. **Fix:** script di pulizia one-shot org demo (sono dati seed, non dell'utente) + su prod non esiste il problema (niente seed).

### ⚠️ B4 — minori
- `confirm` accetta ordini a totale 0 (successo silenzioso) → guardia con warning;
- il checkout digitale senza file blocca GIUSTAMENTE, ma il wizard digitale dovrebbe impedire il publish senza file (oggi il cliente scopre l'errore al checkout).

## PARTE 4 — Audit UX: Performance Prodotti

Stato attuale (visto live): **due banner ROSSI allarmistici** prima di qualunque numero; il secondo ("Discrepanza con Cashflow Monitor") mostra **chiavi i18n grezze** (`drill.products_revenue`), punta a un modulo **nascosto** (Cashflow Monitor BI) e la "discrepanza" è… i 316 record legacy. Poi 6 KPI di cui **3 morti** ("—" senza COGS), etichette troncate ("Costo prodotti (COG…"), tier di insight pensati per e-commerce multi-SKU.

Diagnosi: la pagina URLA problemi che non sono problemi, e tace ciò che serve ("quale prodotto rende?").

### Refinement RF-PP
1. **Via il banner Discrepanza** (confronto col BI potato: irreparabile e fuorviante) — al suo posto niente;
2. **Banner COGS**: da allarme rosso a suggerimento discreto in salvia, UNA riga ("Configura i costi per vedere i margini reali →") — sparisce da solo quando i costi ci sono;
3. **KPI onesti**: senza COGS mostra solo Ricavo / Prodotti attivi / Con vendite (le card margine appaiono quando calcolabili — mai trattini);
4. **Kit grafico**: StatCard del kit al posto delle card custom, palette Salvia&Terracotta;
5. **ABC/Pareto/health-check** → accordion "Analisi avanzata" chiuso (pattern CI), con i tier operativi (top seller, slow mover) in chiaro sopra;
6. i18n: eliminare le chiavi drill.* orfane.

## PARTE 5 — Audit UX: Customer Insights

CF6 ha già dato l'essenziale (4 StatCard + donut + cross-sell + accordion). Restano DUE carichi cognitivi:
1. **4 righe di filtri-chip** sulla tabella (Segmento / Stato / Account / Marketing = 16 chip visibili) — nessun operatore li usa tutti; è la parte "sporca" della pagina;
2. **periodo default 30 giorni**: per un operatore ritiri (stagionale, bassa frequenza) 30d mostra quasi sempre zeri → prima impressione "non funziona".

### Refinement RF-CI
1. **Filtri → 1 riga**: ricerca nome/email + bottone "Filtri" con popover (pattern già usato in Ordini D2) + chip attivi rimovibili; le 4 dimensioni vivono NEL popover;
2. **Periodo default 12 mesi** (il respiro giusto del verticale);
3. Micro: rinominare "Insight Clienti"/"Clienti" nel sottomenu in modo non ambiguo ("Panoramica" / "Anagrafica").

## PARTE 6 — Piano esecutivo RF1–RF4

```
RF1 — Tesoreria verità (B1): gamba A solo ordini confermati/completati
      + stesso filtro su payments-overview; guardie anti-draft. [CRITICO]
RF2 — Canali fisici sbloccati (B2): POS→local_pickup automatico;
      POST /orders accetta fulfillment_mode; guardia POS fisico 201.
RF3 — Performance Prodotti ripulita (RF-PP 1-6) + pulizia 316 record
      legacy demo (B3) + guardia no-drill-keys.
RF4 — Customer Insights snella (RF-CI 1-3) + guardia B4 (warn su
      confirm a totale 0; publish digitale richiede file).
```
Ordine: RF1 → RF2 → RF3 → RF4, ogni step branch + suite + verifica browser + merge.
