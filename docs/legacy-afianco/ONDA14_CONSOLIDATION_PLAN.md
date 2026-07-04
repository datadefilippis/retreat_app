# Onda 14 — Consolidation Plan (4 fix isolati, non-invasivi)

**Contesto:** dopo il consolidamento commerce (eventi + consulenze + IssuedBooking
+ unified card) l'utente ha identificato 4 aree di miglioramento che non toccano
i flow esistenti ma arricchiscono l'esperienza admin. Ogni fix qui sotto è
isolato, scalabile e strutturato — zero impatti su cashflow, payment, order
lifecycle, customer_metrics schema.

---

## Fix A — Filtro per periodo date nella lista Ordini

### Problema
`OrdersPage.js` permette di filtrare per status / source / payment / review / tipo
e fare ricerca testuale, ma **non ha un filtro date range**. L'admin non può
rispondere a "mostrami tutti gli ordini di settembre" senza scrollare.

### Stato attuale (verificato)
- Frontend: `filteredOrders` useMemo (OrdersPage.js:870-914) filtra lato client;
  ha già 5 filtri distinti, pattern consolidato
- Backend: `GET /api/orders` (orders.py:262-289) accetta solo `status` e
  `payment_intent`, nessun parametro date; `find_by_org()` ignora le date
- Field: `order_date` è ISO string, **già indicizzato** (fa parte del compound
  index aggiunto in Fase 5)

### Strategia (isolata, nessuna modifica backend)
**Opzione A — solo client-side (minimale, consigliata)**: aggiunta di 2 date
input + filtro sul `filteredOrders` useMemo, zero cambiamenti backend. Funziona
fino a ~5k ordini per org. Quando cresce, promuoviamo a server-side.

**Opzione B — client + backend (scalabile)**: aggiunge parametri `from_date` /
`to_date` query a `GET /api/orders`, passa l'indice già presente, riduce
payload su org con anni di storia.

### File da toccare (Opzione A)
- `frontend/src/features/orders/OrdersPage.js`
  - `~825`: aggiungi state `filterDateFrom`, `filterDateTo`
  - `~870`: aggiungi nel useMemo un filtro `if (filterDateFrom) list = list.filter(o => (o.order_date || '') >= filterDateFrom)`
    e analogo per `filterDateTo` (comparazione lessicografica su ISO è
    equivalente a ordine temporale)
  - `~1180` (sezione filtri): aggiungi 2 `<input type="date">` con pulsante
    "Pulisci"; preset rapidi "Oggi / 7gg / 30gg / Mese corrente / Personalizzato"
  - Aggiorna il contatore `{filteredOrders.length} / {orders.length}` per
    includere filterDate nello check di attività filtri

### File da toccare (Opzione B — se Opzione A non basta)
- `backend/routers/orders.py:262-289`: aggiungi `from_date: Optional[str] = Query(None)`,
  `to_date: Optional[str] = Query(None)`
- `backend/repositories/order_repository.py:31-41`: estendi `find_by_org()` con
  i due parametri, aggiungi al `$match` se presenti
- `frontend/src/api/orders.js`: passa i params `from_date` / `to_date` al list call

### Verifica
- Seleziona "7gg" su org di test → lista si riduce a soli ordini degli ultimi 7 giorni
- Seleziona date_from=date_to=oggi → solo ordini odierni
- Pulisci → torna a tutti

### Rischio: **minimo**. Additivo, nessuna modifica flow.

---

## Fix B — Customer insights non popolate dopo nuovi ordini

### Problema
L'utente ha creato ordini di test (ORD-0001, ORD-0002, ORD-0003, ORD-0004),
confermati e con sales_records generati, ma la pagina Customers Light non
mostra insight su quei clienti.

### Root cause (trovata dall'esplorazione)
1. **Trigger mancante**: `refresh_customer_metrics(org_id)` viene chiamato
   SOLO da `post_upload_hook` (caricamento file Excel/CSV) e da un pulsante
   manuale in admin UI. **NON viene chiamato su `order_service.confirm_order()`
   e `cancel_order()`**.
2. **Conseguenza**: il `customer_metrics_collection` resta fermo allo snapshot
   dell'ultimo upload → nuovi ordini invisibili anche se in DB.

### Strategia (hook-based, isolato, idempotente)
Aggiungere un hook `_refresh_customer_metrics_async()` che dopo `confirm_order`
e `cancel_order` triggeri il refresh per il SOLO customer_id dell'ordine.
Best-effort (try/except, log, mai blocca il flow). Idempotente
(ricalcolo sempre completo dei metrics del customer).

### File da toccare
- `backend/modules/customers_light/service.py`
  - Verifica che esista `refresh_customer_metrics_for_customer(org_id, customer_id)`.
    Se non esiste, aggiungi una variante scoped del `refresh_customer_metrics`
    esistente che ricalcola 1 customer invece di tutti.
- `backend/services/order_service.py` (la funzione che ho già toccato per category)
  - In `confirm_order`: dopo `_trigger_module_hooks(org_id)`, aggiungi
    chiamata fire-and-forget a `refresh_customer_metrics_for_customer(org_id, order["customer_id"])`
  - In `cancel_order`: stesso trattamento dopo `_generate_storno_records`
  - Entrambe: wrap in try/except con logger.warning su errore, mai raise
- (Opzionale) `backend/modules/customers_light/hooks.py`: aggiungi un
  `post_order_confirm_hook` esplicito se preferisci mantenere gli order_service
  puliti

### Nota importante (richiesta utente)
Draft orders sono intenzionalmente esclusi dai metrics (line 622 service.py) —
questo va LASCIATO così. Un draft non è fatturato, quindi non deve contare. Il
fix riguarda solo il refresh su confirm/cancel (transizioni verso stati materiali).

### Verifica
- Crea cliente X, ordine confermato con item €200 → `customer_metrics` per X
  aggiornato: `total_revenue=200`, `transaction_count=1`, `segment="new"`
- Apri CustomersLightPage → cliente X visibile nella lista
- Cancella ordine → refresh: revenue scende a 0, storno contato

### Rischio: **basso**. L'aggiunta è fire-and-forget; se fallisce, il metrics
resta al valore precedente (degradazione graceful, già il comportamento attuale
quando nessun upload è mai avvenuto).

---

## Fix C — Calendario: vista dettaglio giorno più ricca

### Problema
`CalendarPage` mostra solo **event occurrences + rental lines**. Cliccando un
giorno si apre un pannello ma mancano:
- consulenze (service bookings) del giorno
- ordini confermati del giorno (non eventi, non rental — es. ordine fisico)
- dati contatto cliente (email, telefono) e `order_fields_data` (campi custom
  compilati al checkout)

L'admin di una clinica/ristorante/studio vuole aprire il lunedì e vedere in
un colpo: "ok oggi ho 3 consulenze di Mario/Luca/Giulia alle 9/11/15, un
evento workshop alle 18 con 12 iscritti, un ordine di noleggio in consegna".

### Strategia (additiva, non cambia API esistenti)
**Backend**: estendere `GET /api/calendar/month?month=YYYY-MM` per includere
un nuovo array `bookings[]` (issued_bookings del mese). I frontend vecchi che
non conoscono il campo lo ignorano (backward compatible).

**Frontend**: il `DayDetail` component riceve i nuovi bookings e li mostra in
una sezione dedicata "Consulenze del giorno" con: cliente, orario slot, opzione,
codice, link "Apri prenotazione" (`/b/:token`), link "Ordine" (`/orders?order_id=X`).
Arricchimento anche per event occurrences del giorno: lista partecipanti
(issued_tickets.holder_name) inline con conteggio attendees.

### File da toccare

**Backend:**
- `backend/routers/calendar.py`
  - Nuova query in `get_calendar_month()`: `issued_bookings_collection.find({"organization_id": org_id, "booking_date": {"$regex": f"^{month_prefix}"}, "status": {"$ne": "cancelled"}})`
  - Per ogni booking: join su order per avere customer_email/phone (1 query batch),
    join su product per avere product_name (già in booking), include `order_fields_data`
  - Ritorna in response: `bookings: [{id, code, booking_date, booking_start_time, booking_end_time, product_name, service_option_label, holder_name, holder_email, holder_phone, location, access_token, order_id, attendee_fields_data}]`
- `backend/routers/calendar.py` — **opzionale**: nuovo endpoint
  `GET /api/calendar/day/{date}` che restituisce tutto il dettaglio di un singolo
  giorno (events + bookings + orders + blocked). Più efficiente se la UI è
  "clicca giorno → fetch on-demand" invece di "carica tutto il mese in memoria".

**Frontend:**
- `frontend/src/features/calendar/CalendarPage.js`
  - `DayDetail` component: aggiungi sezione "Consulenze" renderizzata con
    stile coerente al blocco eventi esistente (icona 📅, colore indaco), con
    espandibile per ogni booking che mostra `attendee_fields_data` in chiave/valore
  - Per ogni item (event + booking + rental) aggiungi link rapido "Apri ordine"
    e "Contatta cliente" (mailto: / tel:)
  - Opzionale: summary header del giorno "3 consulenze · 1 evento · 2 ordini · €850"

### Scalabilità
- Query bookings del mese usa l'indice composto `(org_id, booking_date, booking_start_time)`
  già creato in Fase 2.1
- Numero atteso bookings/mese < 500 per org tipica → single query, nessuna
  paginazione necessaria
- Se la UI va oltre il month view (week view, day view), l'endpoint day
  dedicato è già previsto

### Verifica
- Crea consulenza per il 2026-05-10 → apri calendario maggio 2026 → click 10
  → vedi "consulenza ipnosi · Mario Rossi · 10:00-11:00 · BKG-XXXX"
- Click "Apri prenotazione" → landing `/b/:token`
- Click "Apri ordine" → OrdersPage deep-link con panel aperto

### Rischio: **basso**. Endpoint esistente esteso additivamente; frontend
aggiunge sezione, non modifica quelle esistenti.

---

## Fix D — Pagina Clienti: ranking, valore, LTV

### Stato attuale (verificato dall'esplorazione)
**TUTTO IL BACKEND È GIÀ FATTO.** Il modulo `customers_light` calcola e persiste
in `customer_metrics_collection`:

| Metrica | Già presente | Dove |
|---|---|---|
| Total revenue | ✅ | `customer_metrics.total_revenue` |
| Transaction count | ✅ | `customer_metrics.transaction_count` |
| Avg transaction value | ✅ | `customer_metrics.avg_transaction_value` |
| **Lifetime Value (LTV)** | ✅ | `customer_metrics.lifetime_value` |
| **Revenue rank** (posizione) | ✅ | `customer_metrics.revenue_rank` |
| **Revenue share %** | ✅ | `customer_metrics.revenue_share_pct` |
| **Segment** (new/top/active/occasional/inactive) | ✅ | `customer_metrics.segment` |
| **Churn risk** (0-100) | ✅ | `customer_metrics.churn_risk_score` |
| Days since last purchase | ✅ | `customer_metrics.days_since_last_purchase` |
| Purchase frequency | ✅ | `customer_metrics.purchase_frequency_monthly` |
| Preferred products | ✅ | `customer_metrics.preferred_products` (top 3) |
| Payment reliability % | ✅ | `customer_metrics.payment_reliability_pct` |
| Trend direction | ✅ | `customer_metrics.trend_direction` (growing/stable/declining/new) |
| Customer status | ✅ | `customer_metrics.customer_status` (healthy/watch/at_risk/lost) |
| Order count | ✅ (v13.0) | `customer_metrics.order_count` |
| Avg order value | ✅ (v13.0) | `customer_metrics.avg_order_value` |
| Cancellation rate | ✅ (v13.0) | `customer_metrics.cancellation_rate_pct` |
| Fulfillment success rate | ✅ (v13.0) | `customer_metrics.fulfillment_success_rate` |

Org-level overview (`GET /modules/customers_light/overview`) già espone:
`avg_ltv`, `top_10_share_pct`, `high_risk` count, `growing_count`, `declining_count`, etc.

### Gap reali (molto più piccoli del previsto)
Il problema NON è calcolare nuove metriche (ci sono già tutte). Il problema è:

1. **Visibilità per-customer**: CustomersLightPage mostra la top 10 table e KPI
   aggregati, ma il **customer profile** (`GET /modules/customers_light/customers/{id}/profile`)
   mostra solo metrics + ultime 20 sales_records. Non surface LTV, rank,
   segment con visual indicatori, preferred_products con grafico.
2. **Refresh stale** (dipende da Fix B): senza il trigger su confirm_order,
   metrics è vecchio.
3. **Marketing-actionable view mancante**: le metriche ci sono, ma non c'è una
   vista "chi sono i miei clienti top in cui investire? chi sta sbiadendo?"
   con CTA chiare (es. "Invia email a questi 5 at_risk").

### Strategia (solo frontend, leva su backend esistente)
- **Arricchire il Customer Profile page** con:
  - Hero card con nome + segment badge colorato + rank badge (#3 di 47)
  - KPI strip: Revenue totale · LTV · Rank · Churn risk (con barra 0-100)
  - Grafico "Spend nei mesi" (usa sales_records già restituiti dall'endpoint profile)
  - Sezione "Preferred products" con top 3
  - Banner smart se at_risk/lost: "Non acquista da X giorni — invia promo?"
- **Aggiungere vista "Customer Ranking"** nella CustomersLightPage principale:
  - Tab "Classifica" oltre alla tabella top 10 esistente
  - Tabella completa paginata con colonne: rank, nome, revenue, LTV, segment,
    churn_risk, last_purchase, trend, azioni (email / tag / nota)
  - Filter segment + search
- **(Opzionale) Action list**:
  - Box "📧 5 clienti at_risk — reach out"
  - Box "🌟 10 top customers — loyalty program?"
  - Box "🆕 3 new customers questo mese — welcome?"

### File da toccare (solo frontend)
- `frontend/src/features/customers-light/CustomersLightPage.js`
  - Nuova tab "Classifica" (paginata su `/modules/customers_light/metrics`)
  - Eventuali "action cards" a inizio pagina
- `frontend/src/features/customers-light/CustomerProfilePage.js` (se esiste,
  altrimenti crearlo) — oppure espandere il panel esistente
  - Usa endpoint `/modules/customers_light/customers/{id}/profile` già esistente
  - Render dei campi metrics già calcolati

### Backend: zero cambiamenti
Tutto calcolato, tutto esposto. L'unica dipendenza è Fix B per tenere i
metrics freschi.

### Verifica
- Apri CustomersLightPage → vedi tab "Classifica" → ranking completo con LTV/segment
- Apri un singolo customer → vedi hero con LTV/rank/churn
- Al_risk banner: crea customer senza acquisti recenti (o data-test mock) → banner appare

### Rischio: **nullo lato backend**. Solo UI additiva.

---

## Ordine di esecuzione consigliato

1. **Fix B (5-10 min)** — dipendenza upstream per Fix D (metrics freschi)
   → solo 2 hook fire-and-forget in order_service
2. **Fix A (15-20 min)** — date filter client-side, isolato
3. **Fix C (45-60 min)** — estensione calendar endpoint + day detail
4. **Fix D (60-90 min)** — ranking/profile UI rich, solo frontend

Totale stimato: **2-3h** per il blocco completo.

## Garanzie invariabili

Per ogni fix:
- ✅ Zero modifiche al cashflow_monitor module
- ✅ Zero modifiche al SalesRecord model o generation logic (Fix A category
  fatto già in commit separato `cf195ed`)
- ✅ Zero modifiche al Order lifecycle (draft→confirmed→cancelled)
- ✅ Zero modifiche al customer_metrics schema (solo trigger di refresh)
- ✅ Zero modifiche alle API esistenti (solo additive: nuovi endpoint/params
  opzionali, response extend)
- ✅ Fire-and-forget per tutti i nuovi hook (failure logged, flow mai bloccato)

## Out of scope (intenzionalmente)

- Campagne marketing automatizzate (email blast, segment-driven)
- RFM score formale (useremmo i campi già presenti come proxy)
- Net Promoter Score (richiede feedback survey)
- Cost of acquisition (richiede marketing spend data)
- Customer journey maps

Questi sono blocchi pluri-giornata; si valutano in un secondo round se serve.
