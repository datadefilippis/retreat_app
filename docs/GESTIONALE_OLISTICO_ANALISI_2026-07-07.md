# Analisi deep — Gestionale manuale, cashflow e visione olistica multi-prodotto

**Data:** 2026-07-07 · **Trigger:** review del founder post CF1-CF7
**Domande:** (1) l'app può ancora fare da gestionale manuale o solo vendite da store/directory? (2) performance prodotti e insight clienti sono al massimo del potenziale? (3) dove è finita la visione olistica (ritiri + consulenze + fisici + digitali + corsi)?

---

## PARTE 1 — Il verdetto sul gestionale manuale

### Cosa è successo davvero (diagnosi tecnica)

Nell'app convivono **due registri di verità** sui pagamenti:

| Registro | Chi lo scrive | Cosa copre |
|---|---|---|
| `payment_schedules` (libro mastro) | SOLO ordini con riga `event_ticket` datata (`create_schedule_for_new_order` ritorna None per tutto il resto — order_service.py:466) | Ritiri con caparra/saldo/rate |
| `orders.payment_status` + `due_date` + `mark-paid`/`mark-unpaid` | Tutto il resto: ordini manuali, POS, consulenze, fisici, digitali, corsi | Il gestionale classico |

CF3 ha promosso il **primo** registro a fonte unica della pagina /incassi (e CF4 della card home). Risultato: un ordine manuale da 500€ segnato "pagato" con mark-paid **non appare da nessuna parte** nella tesoreria. Peggio: il donut "per prodotto" nella stessa pagina legge invece da `orders` → la pagina mescola due fonti e i numeri non quadrano tra loro. **Violazione del mio stesso principio "realtà dei dati". Errore mio, non ambiguità.**

Nota di onestà: la cecità NON è nata con CF3 — anche il vecchio `payments-overview` (D3) leggeva solo il ledger. Ma finché era una card, era un dettaglio; ora che è LA tesoreria, è un buco.

### Il gestionale manuale esiste ancora? SÌ — intatto

Verificato: **niente della macchina gestionale è stato rimosso**:
- `POST /orders` — creazione ordine manuale (con cliente, righe di ogni tipo, `due_date`)
- `POST /orders/{id}/mark-paid` / `mark-unpaid` — registrazione manuale del pagamento (routers/orders.py:690)
- POS per la vendita al banco (scelta founder, mai toccato)
- `issued_bookings` (sessioni consulenza), `issued_reservations`, `issued_downloads`, course accesses — tutto il fulfillment per tipo è vivo

**È la LETTURA che è diventata parziale, non la scrittura.** Il danno è reale ma circoscritto a /incassi + card home; si ripara a livello endpoint senza toccare dati né flussi.

### Verdetto: mantenere il gestionale manuale? SÌ, senza esitazione

Ragioni di prodotto, non solo tecniche:
1. **L'operatore olistico incassa fuori piattaforma continuamente**: bonifico per la consulenza, contanti al ritiro, satispay per l'olio essenziale. Se l'app vede solo Stripe/store, la tesoreria mente e l'operatore torna a Excel → churn.
2. **Il gestionale è il fossato competitivo** del pivot (memoria: gap "directory+gestionale reale in Italia"). Solo-marketplace ci rende confrontabili con qualunque directory.
3. **Il costo di mantenerlo è ~zero**: è già scritto, testato, funzionante. La scelta non è "mantenere vs rimuovere" ma "renderlo di nuovo visibile".

**Decisione:** l'app resta directory+store+**gestionale completo**. /incassi diventa l'unione onesta dei due registri.

---

## PARTE 2 — Le 5 anime dell'operatore olistico: stato reale degli insight

Audit tipo per tipo (cosa esiste / cosa manca / quale azione):

| Anima | Dati che ESISTONO | Insight oggi | Cosa manca | Azione mancante |
|---|---|---|---|---|
| **Ritiri** | ledger, tickets, analytics per occurrence | ✅ forte (CF5: timeline, confronto edizioni, contatti, recensioni) | — | — |
| **Consulenze/Servizi** | `issued_bookings` (sessioni con data, cliente, stato) | ❌ zero: ServiceDashboard è solo editor | prossime sessioni, revenue 12m, cliente ricorrente | promemoria appuntamento (template `appointment_reminder` GIÀ in library.json, mai cablato!) |
| **Prodotti fisici** | stock, orders items, fulfillment | 🟡 stock badge, ordini recenti | unità vendute 12m, ricavo, rotazione (venduto vs giacenza) | — (fulfillment già gestito in Ordini) |
| **Digitali** | `issued_downloads` (consegne, download count, scadenze) | 🟡 lista consegne per prodotto | aggregato: consegne 12m, ricavo | reinvio già presente ✅ |
| **Videocorsi** | course accesses (enrollments), moduli/lezioni | ❌ zero: solo CRUD | iscritti per corso, attivi vs scaduti, ricavo | contatto iscritti (es. nuova edizione) |
| **Trasversale** | `orders.items[].item_type` su OGNI riga | ❌ nessuna vista "da cosa guadagno?" | **il donut per TIPO** — la domanda olistica per eccellenza | decidere dove investire il tempo |

### Performance prodotti — ho investigato abbastanza?

Onestamente: **no, mi sono fermato a metà**. La ProductPerformancePage (ABC/Pareto, margin risk) esiste ed è raggiungibile, ma:
- è pensata per e-commerce multi-SKU e usa concetti (classe ABC, margin risk) sovradimensionati per chi ha 8 prodotti;
- non l'ho né semplificata né collegata al resto (nessun ContactActions, nessun kit grafico);
- la vera domanda dell'operatore olistico non è "qual è la mia classe A?" ma "**quale delle mie 5 anime rende di più rispetto al tempo che ci metto?**" — e quella risposta oggi non esiste da nessuna parte.

### Insight clienti — al massimo?

CF6 è solido (essenziale + azionabile + accordion). Due gap veri:
1. il profilo cliente (slide) non dice **che TIPO di cliente è** (solo ritiri? compra anche corsi? consulenze ricorrenti?) — il cross-sell è LA strategia per un olistico ("ha fatto il ritiro ma mai una consulenza → proponigliela");
2. "Da ricontattare" c'è, ma non suggerisce COSA proporre.

---

## PARTE 3 — Risposta onesta: "hai prodotto il massimo?"

**No.** CF1-CF7 hanno costruito l'infrastruttura giusta (kit, azione one-click, tesoreria, radar) ma con:
1. **un buco di copertura** (fonte unica parziale in /incassi) — critico, da riparare per primo;
2. **la dimensione olistica assente**: tutte le viste sono per-prodotto o aggregate, mai per-ANIMA (tipo). L'operatore multi-attività non può rispondere a "da cosa guadagno?" né vedere le consulenze/corsi come business misurati;
3. **due pagine mai toccate** (ServiceDashboard, CoursesPage) che restano puri editor senza un numero.

---

## PARTE 4 — Piano CG (Consolidamento Gestionale) — 4 step

### CG1 — Tesoreria COMPLETA: unione dei due registri (fix critico, primo)
`/analytics/cashflow` diventa l'unione senza doppi conteggi:
- ordini **con** schedule → dal ledger (righe paid/pending/overdue, come oggi);
- ordini **senza** schedule (manuali, POS, servizi, fisici, digitali, corsi) → da `orders`: `payment_status=paid` → incassato (bucket per `order_date`); `pending/confirmed non pagato` → atteso con scadenza = `due_date` se presente, altrimenti `order_date` (→ se passata: in ritardo);
- anti-double-counting: si escludono da orders gli order_id presenti nel ledger;
- upcoming/overdue: le righe da ordini manuali portano il link all'ordine e `ContactActions(payment_reminder)` — il sollecito one-click funziona anche per il gestionale;
- da /incassi, riga non pagata → azione rapida "Registra pagamento" (mark-paid esistente) per chi incassa in contanti/bonifico;
- stessa correzione si riflette su card home (già stessa fonte) e `payments-overview` resta ledger-only per i SOLI contesti ritiro (Event Dashboard).
**Guardie:** test anti-double-counting (ordine con schedule non conta due volte), ordine manuale paid appare in incassato, manuale con due_date scaduta appare in overdue.

### CG2 — La vista olistica: "Da cosa guadagni" per anima
- In /incassi: **DonutSplit per `item_type`** (Ritiri / Consulenze / Fisici / Digitali / Corsi) accanto a quello per prodotto — periodo 12 mesi, da orders (tutti i tipi, inclusi manuali);
- StatCard "Anima principale" (tipo col ricavo maggiore) con % sul totale;
- semantica colori fissa per tipo nel kit (retreat=salvia, service=salvia chiara, physical=oliva, digital=argilla, course=terracotta chiara).

### CG3 — Mini-stats per anima nei loro dashboard (stesso pattern, kit + azione)
- **ServiceDashboard**: prossime sessioni (issued_bookings future, con `ContactActions(appointment_reminder)` — il template esiste già, si cabla e basta) + StatCard revenue 12m / sessioni svolte;
- **CoursesPage**: per corso → iscritti attivi / scaduti + ricavo (course accesses × orders);
- **PhysicalDashboard**: StatCard unità vendute 12m + ricavo + giacenza attuale (rotazione a colpo d'occhio);
- **DigitalDashboard**: StatCard consegne 12m + ricavo (la lista download c'è già);
- un solo endpoint leggero `GET /products/{id}/sales-stats` (aggregate su orders per product_id, cache 60s) riusato dai 4 dashboard.

### CG4 — Clienti cross-sell + potatura ProductPerformance
- Colonna/badge "anime" nel profilo cliente (slide): icone dei tipi acquistati (dai suoi ordini) → il gap cross-sell diventa visibile ("solo ritiri" = candidato consulenza);
- filtro pronto "Ha fatto ritiri ma mai consulenze" nella tabella clienti (drill semplice su item_type degli ordini del cliente);
- ProductPerformancePage: colori/empty state migrati al kit, ma resta "analisi avanzata" — niente redesign (ROI basso per 8 prodotti);
- guardie i18n nuovi namespace + suite.

### Ordine e dipendenze
```
CG1 (fix critico, sblocca la fiducia nei numeri)
 └→ CG2 (vista per anima — si appoggia all'endpoint corretto)
     └→ CG3 (mini-stats per tipo)  └→ CG4 (cross-sell + potatura + guardie)
```

### Cosa NON facciamo
- Non resuscitiamo il cashflow_monitor BI (SalesRecord): il registro orders+ledger copre tutto il verticale; due gestionali paralleli = il problema dell'audit di giugno;
- niente time-tracking per "ricavo/ora per anima" (dato che non esiste → lo stimeremmo, violando la realtà dei dati);
- niente KPI predittivi, come da principio.
