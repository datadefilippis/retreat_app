# AFianco — MVP Master Plan
**Versione:** 1.0 | **Data:** 2026-04-12 | **Autore:** Architettura di Sistema
**Obiettivo:** Go-live con soluzione vendibile, operativa, scalabile

---

## Visione Prodotto

AFianco e' un Business Operating System per PMI ibride italiane che unifica:
- **Commerce multi-canale** (storefront, POS, booking, eventi, noleggio)
- **Financial intelligence** (cashflow, margini, alert, forecast)
- **Customer intelligence** (segmentazione, LTV, churn risk)
- **AI assistant** (chat analitico con contesto completo)
- **Automazione operativa** (calendario, fulfillment, email, notifiche)

Il differenziatore: non e' un e-commerce che aggiunge analytics dopo, ne' un gestionale che aggiunge un sito dopo. E' **nativo ibrido** — commerce e intelligence nascono integrati.

---

## Stato Attuale (Pre-MVP)

### Consolidato e Testato (244+ E2E assertions)
- Commerce engine: 5 tipi prodotto (physical, event, booking, rental, service)
- Order lifecycle: draft > confirmed > completed/cancelled + storno
- Calendar: doppia vista (agenda + noleggi) con scope isolation
- Payment sync bidirezionale Order <> SalesRecord
- Fulfillment lifecycle (shipping, pickup, manual)
- Customer dedup, storefront pubblico, booking slot picker
- Cashflow analytics, customer segments, product ABC, AI chat

### Gap Critico Identificato
L'intelligence layer (AI, alert, analytics, dashboard) non vede il commerce layer.
Ordini, fulfillment, booking, eventi, rental sono invisibili a:
- AI Chat (21 tools, nessuno query orders/booking/rental)
- Alert Engine (7 categorie, tutte solo cashflow)
- Customer Metrics (solo da sales_records, non da orders)
- Product Metrics (solo da sales_records, non da eventi/rental)
- Dashboard (nessun widget commerce operativo)

---

## Piano Strutturato — 8 Blocchi Prioritizzati

Ogni blocco e' isolato, testabile indipendentemente, e non rompe i flussi esistenti.

---

### BLOCCO 1 — Intelligence Bridge: Commerce > AI Tools
**Priorita:** P0 (fondamenta per tutto il resto)
**Effort:** 2-3 giorni
**Dipendenze:** Nessuna

Creare nuovi AI tools che danno visibilita' al commerce engine:

| Tool | Query | Dato |
|------|-------|------|
| `query_order_pipeline` | orders per status | draft/confirmed/completed/cancelled counts + amounts |
| `query_fulfillment_status` | orders.fulfillment | pending/shipped/delivered breakdown + delays |
| `query_payment_pipeline` | orders per payment_status | awaiting/collected/paid amounts |
| `query_event_metrics` | event_occurrences + orders | per evento: capacity, booked, fill_rate, revenue |
| `query_booking_utilization` | blocked_slots + availability_rules | slot occupati vs disponibili per periodo |
| `query_rental_utilization` | blocked_slots (reason=rental) | per prodotto: days_booked, utilization_% |

**File toccati:**
- `backend/modules/cashflow_monitor/ai_tools.py` (aggiungere tools)
- `backend/services/ai_tool_registry.py` (registrare nuovi tools)

**Verifica:** Chiedere all'AI "quanti ordini ho in attesa?" e ricevere risposta accurata.

**Status:** [ ] Non iniziato

---

### BLOCCO 2 — Alert Engine Commerce-Aware
**Priorita:** P0
**Effort:** 2 giorni
**Dipendenze:** Nessuna (alert engine e' indipendente dai tools AI)

Nuove categorie alert nel motore esistente:

| Alert | Condizione | Severita |
|-------|-----------|----------|
| Order Backlog | draft orders > 5 per piu' di 3 giorni | warning |
| Fulfillment Delay | confirmed + pending shipment > 7 giorni | critical |
| Payment Limbo | payment_intent=collected + status=draft > 24h | critical |
| Event Low Fill | evento a <3 giorni con fill_rate <30% | warning |
| Rental Idle | prodotto rental con 0% utilization in 30gg | info |
| Cancellation Spike | tasso cancellazione >20% in 7 giorni | warning |

**File toccati:**
- `backend/modules/cashflow_monitor/alert_rules.py` (nuove rules)
- `backend/modules/cashflow_monitor/alert_engine.py` (nuovi data loaders)
- `backend/modules/cashflow_monitor/alert_i18n.py` (traduzioni)

**Verifica:** Alert appare in dashboard quando condizione soddisfatta.

**Status:** [ ] Non iniziato

---

### BLOCCO 3 — Customer Metrics Estese
**Priorita:** P0
**Effort:** 1-2 giorni
**Dipendenze:** Nessuna

Estendere `refresh_customer_metrics()` per includere dati da orders:

| Metrica | Fonte | Calcolo |
|---------|-------|---------|
| order_count | orders per customer_id | COUNT |
| order_value_total | orders.subtotal | SUM |
| avg_order_value | order_value / order_count | AVG |
| cancellation_rate | cancelled / total orders | % |
| booking_count | orders con item_type=booking | COUNT |
| event_attendance | orders con item_type=event_ticket | COUNT |
| last_order_date | orders.created_at MAX | DATE |
| fulfillment_reliability | completed_on_time / total | % |

**File toccati:**
- `backend/modules/customers_light/service.py` (refresh_customer_metrics)
- `backend/modules/customers_light/ai_tools.py` (esporre nuovi campi)

**Verifica:** Customer profile in AI chat mostra order count e cancellation rate.

**Status:** [ ] Non iniziato

---

### BLOCCO 4 — Product Metrics Estese
**Priorita:** P0
**Effort:** 1-2 giorni
**Dipendenze:** Nessuna

Estendere product analytics per tipi commerce:

| Metrica | Tipo Prodotto | Calcolo |
|---------|--------------|---------|
| event_fill_rate | event_ticket | booked / capacity per occurrence |
| rental_utilization_pct | rental | days_booked / days_available |
| booking_conversion | booking | confirmed / draft orders |
| cancellation_rate | tutti | cancelled / total orders |
| revenue_by_type | tutti | SUM(amount) GROUP BY item_type |

**File toccati:**
- `backend/modules/product_catalog/service.py` (metriche estese)
- `backend/modules/product_catalog/ai_tools.py` (esporre nuovi campi)

**Verifica:** AI risponde a "qual e' il fill rate della Cena Degustazione?"

**Status:** [ ] Non iniziato

---

### BLOCCO 5 — Dashboard Commerce Widgets
**Priorita:** P1
**Effort:** 2-3 giorni
**Dipendenze:** Blocco 1 (dati disponibili)

Nuovi widget nella dashboard admin:

| Widget | Visualizzazione | Dato |
|--------|----------------|------|
| Order Pipeline | Funnel orizzontale | draft > confirmed > shipped > completed |
| Revenue by Type | Pie chart / barre | fisico / evento / booking / rental |
| Calendar Occupancy | % bar | slot occupati questa settimana |
| Fulfillment Queue | Lista | ordini da spedire con giorni attesa |
| Payment Pending | Alert card | ammontare in attesa di pagamento |

**File toccati:**
- `backend/routers/orders.py` (endpoint /orders/analytics o estendere /orders/summary)
- `frontend/src/features/dashboard/DashboardPage.js` (nuovi widget)

**Verifica:** Dashboard mostra pipeline ordini e revenue breakdown.

**Status:** [ ] Non iniziato

---

### BLOCCO 6 — Operational Essentials (Feature Gap)
**Priorita:** P1
**Effort:** 3-4 giorni
**Dipendenze:** Nessuna (parallellizzabile)

| Feature | Descrizione | Effort |
|---------|-------------|--------|
| **6.1 Upload immagini** | S3/local upload per prodotti, preview in card | 1 giorno |
| **6.2 PDF ricevuta ordine** | Genera PDF da ordine confermato, scaricabile | 1 giorno |
| **6.3 Notifiche in-app** | Badge sidebar "N ordini nuovi", notification center | 1 giorno |
| **6.4 Stock tracking base** | Campo stock_quantity su product, alert esaurito | 0.5 giorni |
| **6.5 BREVO email config** | Documentazione setup + test invio reale | 0.5 giorni |

**File toccati (per sub-blocco):**
- 6.1: `backend/routers/products.py`, `frontend/ProductsPage.js`, `StorefrontPage.js`
- 6.2: nuovo `backend/services/order_pdf_service.py`, `backend/routers/orders.py`
- 6.3: nuovo `backend/routers/notifications.py`, `frontend/Layout.js`
- 6.4: `backend/models/product.py`, `backend/routers/public.py`
- 6.5: `.env`, documentazione

**Status:** [ ] Non iniziato

---

### BLOCCO 7 — Storefront & Customer Experience
**Priorita:** P2
**Effort:** 3-4 giorni
**Dipendenze:** Blocco 6.1 (immagini)

| Feature | Descrizione | Effort |
|---------|-------------|--------|
| **7.1 Storefront branding** | Colori, logo, banner da store_settings | 1 giorno |
| **7.2 Coupon/sconti base** | Codice promo, sconto % su ordine | 1 giorno |
| **7.3 Customer portal migliorato** | Storico ordini, download ricevute, rebooking | 1 giorno |
| **7.4 SEO base** | Meta tags, Open Graph, sitemap | 0.5 giorni |
| **7.5 Onboarding wizard** | Step-by-step da zero a store live | 0.5 giorni |

**Status:** [ ] Non iniziato

---

### BLOCCO 8 — Hardening & Scale Readiness
**Priorita:** P2
**Effort:** 2-3 giorni
**Dipendenze:** Tutti i blocchi precedenti

| Item | Descrizione |
|------|-------------|
| **8.1 E2E test suite completa** | Test integrazione AI tools + alert + dashboard |
| **8.2 Error handling robusto** | Retry logic, graceful degradation, error boundaries |
| **8.3 Performance audit** | Query optimization, index review, caching |
| **8.4 Security audit** | Rate limiting review, input sanitization, CORS |
| **8.5 Monitoring** | Health checks, error logging, uptime |
| **8.6 Backup strategy** | MongoDB dump schedule, S3 backup |
| **8.7 Documentation** | API docs, deployment guide, user manual |

**Status:** [ ] Non iniziato

---

## Timeline Stimata

```
Settimana 1:  Blocco 1 (AI Tools) + Blocco 2 (Alert Commerce)
Settimana 2:  Blocco 3 (Customer Metrics) + Blocco 4 (Product Metrics)
Settimana 3:  Blocco 5 (Dashboard) + Blocco 6 (Operational Essentials)
Settimana 4:  Blocco 7 (Storefront UX) + Blocco 8 (Hardening)
```

**Go-Live Target:** 4 settimane dalla data di inizio.

---

## Principi di Esecuzione

1. **Isolamento**: ogni blocco e' indipendente, testabile, deployabile separatamente
2. **Zero regressioni**: dopo ogni blocco, rieseguire tutte le E2E suite (244+ assertions)
3. **Backward compatibility**: nessun breaking change su API o modelli esistenti
4. **Audit trail**: ogni modifica documentata con context completo
5. **Test-first per intelligence**: ogni nuovo tool/alert/metrica ha test case dedicato
6. **Olistico**: ogni feature nuova deve essere visibile a AI, alert, dashboard, customer metrics

---

## Tracking Progresso

| Blocco | Stato | Test | Note |
|--------|-------|------|------|
| 1. AI Tools Commerce | [x] COMPLETATO + CONSOLIDATO | 15 tools enriched, business_summary integrato, 3 suite E2E green | 6 tools con epistemic metadata, analytical blocks, cross-module hints. Commerce ops nel business_summary (Rank 5). Reasoning contract aggiornato a 6 livelli. |
| 2. Alert Commerce | [x] COMPLETATO + CONSOLIDATO | 6 rules enriched, impatto finanziario, severity condizionale, F2 aggregato, F5 auto-expire fix, regression green | Ogni alert mostra €valore bloccato/perso. Severity HIGH/MEDIUM basata su importo. F2 aggrega ordini non-critici. |
| 3. Customer Metrics+ | [x] COMPLETATO + CONSOLIDATO | 32 fields, AI tools enriched (summary+churn+profile), overview enriched, regression green | query_customer_summary ha order_activity. query_churn_risk espone cancellazioni+caveat. build_overview ha 7 commerce KPIs + top_customers con order fields. |
| 4. Product Metrics+ | [x] COMPLETATO + CONSOLIDATO | 27 fields, AI tools enriched (analytics+margins+recommendations), overview enriched, regression green | commerce_summary con epistemic_note. Margins con order_revenue+item_type. Recommendations con action hints. build_overview ha 6 commerce KPIs + top_products con item_type/utilization. |
| 5. Dashboard Commerce | [x] COMPLETATO + CONSOLIDATO | 5 widgets, calcoli verificati, total_confirmed_revenue, regression green | Fix: query usa order_date (stringa ISO) invece di created_at (tipo misto). Aggiunto total_confirmed_revenue. Quick stats con sub-labels. Tutti i numeri cross-verificati con DB. |
| 6. Operational Essentials | [x] COMPLETATO + CONSOLIDATO | 5 features + 11 gaps fixed, regression green | Stock: restore on cancel + block on submit + low_stock alert F7 + AI tool. Images: old file cleanup. PDF: error handling + customer portal download. Notifications: polling. Stock in product_metrics + recommendations. Test timeout 30s. |
| 7. Storefront UX | [x] COMPLETATO + CONSOLIDATO | 4 sub-features + admin UI complete, regression green | 7.1 Branding: file upload logo (POST /store-settings/logo, 2MB), color picker con anteprima, CSS dynamic. 7.2 Coupon: /coupons page con CRUD, sidebar nav, storefront field, order integration. 7.3 Customer Portal: profilo + change password + receipt. 7.4 SEO: settings form + dynamic meta. Tutto accessibile e configurabile da admin. |
| 8. Hardening & Scale | [x] COMPLETATO + CONSOLIDATO (2 passaggi) | Rate limit globale + injection fix + MIME + concurrency fix + cost tracking, regression green | Pass 1: rate limit 60/min globale, re.escape() injection, MIME validation, write endpoint protection. Pass 2: stock $inc atomico (no race), coupon find_one_and_update (no double-redemption), order number retry 3x (no collision), payment sync conditional (no stale write), alert overlap guard, Claude API token logging. Zero impatto cashflow verificato. |

---

*Questo documento viene aggiornato ad ogni completamento di blocco.*
