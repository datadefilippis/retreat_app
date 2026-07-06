# INSIGHTS & ACTION PLAN — Consolidamento cashflow, statistiche e azione diretta

**Data:** 2026-07-08 · **Stato:** approvato dal founder, in esecuzione
**Principio guida:** ogni pagina con numeri risponde SEMPRE a tre domande, nell'ordine:
1. **Come sta andando?** (1 numero grande + 1 trend)
2. **Cosa merita attenzione?** (lista corta, ordinata per urgenza)
3. **Cosa faccio ADESSO?** (azione one-click accanto all'insight: WhatsApp, email, link)

Un insight senza azione collegata non entra. Un grafico che non cambia una decisione esce.

---

## 0) Fotografia dell'esistente (ricognizione 2026-07-08)

### Dove vivono oggi i numeri
| Pagina | Route | Stato | Verdetto |
|---|---|---|---|
| Dashboard home operatore (D3) | /dashboard | prossimi ritiri, incassi 3 numeri, da fare | ✅ base giusta, da potenziare |
| Widget pinnabili (widgetRegistry) | /dashboard | 3 widget customers_light, PieChart recharts | 🔴 complessità senza valore → assorbire |
| Customer Insights | /modules/customers-light | KPI grid pesante (7+ KPI), coorti, ABC | 🟡 semplificare per olistico + azione |
| Product Performance (ABC/Pareto) | /modules/product-catalog | tier ABC, margin risk, health check | 🔴 pensato per e-commerce multi-SKU → gate |
| Event Dashboard | /events/{id} | revenue, tier, capienza, partecipanti, payments | ✅ core, manca timeline visiva + contatto |
| Ordini | /orders | triage chips + tabella | ✅ resta gestionale, no grafici |
| Recensioni (PR3) | /reviews | media, distribuzione, moderazione | ✅ appena fatto, si collega qui |
| Newsletter | /newsletter | solo config form, ZERO numeri | 🟡 unico modulo senza stats → mini-stats |
| POS | /pos/{storeId} | transazionale | resta (scelta founder), fuori scope stats |
| Cashflow Monitor legacy (BI_PMI) | nascosto | SalesRecord, data integrity | 🔴 non per olistico, resta gated system_admin |

### Asset già pronti da riusare (non ricostruire!)
- **`customers.phone`** raccolto al checkout (`_find_or_create_customer` upsert), `order.contact_phone` snapshot
- **`attendees[].holder_phone`** sui biglietti evento → contattabilità per-partecipante
- **Consenso marketing GDPR**: `customers.accepted_marketing_at` / `marketing_revoked_at` (mirror guest+registered), audit immutabile in `consent_audit`, unsubscribe con token firmato
- **`OutreachActions.jsx`** (customer-insights): bottoni mailto: + wa.me con template dal backend (`GET /customer-insights/actions/outreach`) — è il seme del sistema azione, va promosso a componente condiviso
- **`GET /orders/dashboard`**: 5 aggregazioni parallele già scritte
- **`GET /event-occurrences/{id}/analytics`**: revenue + timeline 30d + attendance + confronto occorrenze passate GIÀ calcolati (il frontend non li disegna)
- **Recharts** già in bundle (usato in 1 solo widget)

### Regola "realtà dei dati"
Solo campi che esistono davvero: `orders.total/order_date/status/payment_status`, payment schedules, `issued_tickets`, `reviews_stats`, `newsletter_subscriptions`. Nessun KPI derivato fragile (LTV proiettato, churn "previsto"). Empty state onesti: "Ancora nessun dato: arriverà col primo ordine", mai grafici finti.

---

## CF1 — Kit grafico condiviso + palette (fondamenta)

**Perché primo:** ogni step successivo disegna; senza kit ogni pagina reinventa colori e assi.

`frontend/src/components/charts/` (nuovo):
- `StatCard` — numero grande + label + delta vs periodo precedente (freccia ▲▼, verde/terracotta) + sublabel. UNICO formato KPI in tutta l'app.
- `TrendArea` — area chart recharts (incassi/iscritti nel tempo), 1 sola serie + eventuale serie tratteggiata "atteso", assi minimal, tooltip localizzato it/en/de/fr
- `MiniBars` — barre compatte (es. vendite per giorno in Event Dashboard)
- `DonutSplit` — torta per composizione (max 5 fette, poi "altro")
- Palette unica Salvia & Terracotta: `#376254` (primario), `#C97B5D` (attenzione), `#8A9088` (neutro), ambra solo per rating. Via CSS var, dark-mode ready.
- Ogni chart accetta `empty` → placeholder onesto, niente skeleton infiniti.

**Guardia:** test che nessuna pagina feature importi `recharts` direttamente (solo `components/charts`) → coerenza strutturale garantita nel tempo.

## CF2 — Azione diretta: `ContactActions` condiviso + template contestuali

**Promozione di OutreachActions a sistema.** Nuovo `frontend/src/components/ContactActions.js`:
- Props: `{name, email, phone, marketingConsent, context, entity}` → rende 2 icon-button: **WhatsApp** (wa.me, solo se phone normalizzabile E.164) e **Email** (mailto:)
- Il testo precompilato arriva dal backend: `GET /outreach/template?context=...&entity_id=...` (nuovo router `outreach.py`, org-scoped, nella lingua del cliente se nota — `gdpr_locale`/`order.locale`)
- **Contesti/template v1** (tutti con variabili reali, zero promesse automatiche):
  1. `payment_reminder` — sollecito caparra/saldo in scadenza (da payment schedule)
  2. `pre_retreat` — info pratiche X giorni prima del ritiro (da occurrence)
  3. `post_retreat_review` — ringraziamento + **link alla pagina profilo per la recensione** (sinergia PR1-PR5: il flusso OTP fa il resto)
  4. `winback` — ricontatto cliente inattivo (SOLO se `accepted_marketing_at` valorizzato e non revocato)
  5. `generic` — saluto neutro
- **Regola GDPR visibile:** i contesti transazionali (1–3, legati a un ordine esistente) sono sempre attivi; `winback`/marketing è disabilitato con tooltip "Nessun consenso marketing" se il consenso manca o è revocato. Nessun invio automatico: il click apre WhatsApp/client email dell'operatore — decisione e invio restano umani (niente obblighi Twilio/API Business, scalabile a integrazione nativa in futuro).

**Backend:** `routers/outreach.py` + `services/outreach_service.py` (template ×4 lingue, riuso chiavi in `email_service` dove sensato). Test: template risolvono ×4 lingue, winback bloccato senza consenso, telefono non E.164 → whatsapp_url null.

## CF3 — Cashflow consolidato: pagina "Incassi" (/incassi)

**La richiesta centrale.** Nuova pagina nel menu (icona Wallet, dopo Ordini), UNA pagina per tutta la tesoreria dell'attività:

**Endpoint nuovo `GET /analytics/cashflow`** (riusa i pattern di `orders/dashboard`):
- `months[]`: ultimi 12 mesi → incassato (paid) + atteso (pending schedules) per mese
- `upcoming[]`: prossimi pagamenti attesi 30gg (schedule con ordine, cliente, importo, data, telefono/email cliente)
- `overdue[]`: pagamenti in ritardo (stessa shape)
- `by_product[]`: incassato per prodotto/ritiro (top 8, periodo selezionabile)
- `summary`: incassato periodo, in arrivo, in ritardo, ticket medio
- Cache 60s in-process (pattern R13); tutte le pipeline org-scoped, `$match` su indici esistenti

**Layout (3 blocchi, ordine = priorità):**
1. **4 StatCard**: Incassato (periodo) · In arrivo · In ritardo (terracotta se >0) · Ticket medio
2. **TrendArea 12 mesi**: incassato pieno + atteso tratteggiato → colpo d'occhio stagionalità (il dato strategico per chi pianifica ritiri)
3. **"Da incassare"**: tabella overdue + upcoming, ogni riga con `ContactActions(context=payment_reminder)` → **il sollecito è a un click**. Più `DonutSplit` incassato per ritiro/prodotto.

La card Incassi della Dashboard home linka qui. Il vecchio blocco payments-overview resta come fonte, la pagina è la vista completa.

## CF4 — Dashboard home = radar unico (assorbe i widget)

- **Assorbire `DashboardPage`/`widgetRegistry`** (pin/unpin, preferenze, PieChart segmenti) nella OperatorHome: un solo file, zero configurabilità → chiarezza
- Layout finale: **Prossimi ritiri** (con barra riempimento posti — dato che già c'è) · **Incassi** (3 numeri + MiniBars 30gg, link /incassi) · **Da fare** (ordini da gestire, bozze, **recensioni in attesa** — pending_count già esposto, **pagamenti in ritardo**)
- Rotta `/api/preferences/dashboard` e widgetRegistry: deprecati (rimozione file, la preferenza salvata viene ignorata senza migrazione — è solo UI state)

## CF5 — Event Dashboard: dal numero all'azione sul partecipante

I dati ci sono già (`/analytics` per-occurrence), manca il disegno e l'azione:
- **MiniBars vendite 30gg** (timeline già nel payload) + StatCard revenue/attendance rate + confronto media occorrenze passate ("+18% vs le tue ultime 5 edizioni" — già calcolato dal backend!)
- **Partecipanti**: colonna contatto → `ContactActions(context=pre_retreat)` per riga (usa `holder_phone`/`holder_email` degli attendees; fallback contatto ordine)
- **Post-ritiro** (occurrence passata): banner "Chiedi una recensione" → `ContactActions(context=post_retreat_review)` per partecipante → alimenta il sistema recensioni appena costruito
- Payments card: riusa le righe con `payment_reminder` come /incassi

## CF6 — Clienti essenziale: da analisi a rubrica azionabile

Customer Insights oggi è über-analitico (coorti, concentration, 7 KPI). Per l'operatore olistico:
- **Ridurre a 4 StatCard**: Clienti totali · Nuovi (periodo) · Da ricontattare (inattivi CON consenso marketing) · Con telefono (contattabili WhatsApp)
- **1 solo grafico**: DonutSplit segmenti (il PieChart esistente, migrato al kit)
- **Tabella clienti**: aggiungere colonne contattabilità (icona ✆ se phone, ✉ se email, ★ se consenso mkt) + `ContactActions` inline per riga (context=winback per inattivi, generic altrove)
- Segmento pronto **"Da ricontattare"**: filtro one-click inattivi+consenso → la lista è già un piano di ricontatto settimanale
- Coorti/ABC/concentration: NON cancellati — spostati dietro un accordion "Analisi avanzata" chiuso di default (zero costo, zero rumore)
- Drill-down cliente (CustomerProfileSlide): resta, con ContactActions già lì

## CF7 — Newsletter: i numeri mancanti + potatura finale

- **Newsletter mini-stats** (unico modulo a zero numeri): StatCard Iscritti totali · Nuovi 30gg · TrendArea iscrizioni nel tempo + fonte (source D7 già tracciato). Endpoint `GET /newsletter/stats` (count + bucket mensili su `newsletter_subscriptions`)
- **Product Performance (ABC)**: la pagina resta per org commerce, ma per org retreat il menu mostra solo /products (gate su modulo `product_catalog` come già oggi — verificare che i piani retreat non lo attivino)
- **Guardie finali**: parità i18n nuovi namespace (`charts.*`, `outreach.*`, `cashflow.*` ×4 lingue nel guard test esistente), test endpoint cashflow (org-scoped, shape, cache), test outreach GDPR

---

## Ordine di esecuzione e dipendenze

```
CF1 kit grafico ──┬─→ CF3 /incassi ──→ CF4 dashboard home
CF2 ContactActions ┘      ├─→ CF5 event dashboard
                          └─→ CF6 clienti ──→ CF7 newsletter+potatura+guardie
```
Ogni CF = branch dedicato + suite verde + verifica browser + merge --no-ff (disciplina consolidata).

## Cosa NON facciamo (e perché)

- **Invio automatico WhatsApp/email in massa** — richiede WhatsApp Business API/provider, consensi rafforzati e gestione deliverability: la v1 apre il canale col messaggio pronto, l'operatore preme invio. Il design (`outreach_service` centralizzato) rende l'upgrade futuro un attacco pulito.
- **KPI predittivi** (LTV, churn score in evidenza) — modelli fragili con i volumi di un operatore ritiri: mostriamo fatti, non stime.
- **Cancellare Customer Insights/coorti** — utili a org commerce del fork; per olistico vanno solo fuori dalla vista di default.
