# Piano di Consolidamento, Pulizia e User-Friendliness
**retreat_app · 4 luglio 2026 · Prima della Fase 6**

> Obiettivo: pulizia, semplicità, controllo dell'operatore. NON aggiungere funzioni nuove — rifinire e snellire quelle fatte (Fasi 0–5). Basato su due audit del codebase (menu/nav + ciclo ordini) e sulle decisioni del founder. Ogni item ha priorità e Definition-of-Done; si spunta a verifica fatta.

---

## 0. Valutazione sintetica (le tue domande, con risposta)

**"L'operatore crea un evento in maniera semplice?"**
Sì, quasi. Il wizard a 5 tab (Cosa offri → Quando e dove → Biglietti → Come incassi → Pubblica) è lineare e con anteprima live. Frizioni residue: il tab "Biglietti" mescola concetti (dati partecipanti + tier) e usa la parola "biglietti" invece di "posti/pacchetti"; i contenuti ricchi (programma/galleria/FAQ) si curano DOPO dalla dashboard, non nel wizard — accettabile, ma va segnalato con un cue chiaro.

**"Ordini e schermata sono facili da capire e gestire?"**
In parte. Due badge distinti (stato ordine / stato pagamento) sono chiari. MA il problema strutturale: **gli acconti/rate NON si vedono dalla lista ordini** — solo dalla dashboard del singolo ritiro. L'operatore che apre un ordine dalla lista generale non vede le scadenze né può gestirle. Esperienza frammentata.

**"Gli acconti funzionano e le rate a seguito?"**
Sì, il motore è solido e testato (e2e con pagamento reale). Il problema non è il motore, è la **visibilità e i punti di accesso**: dispersi tra dashboard-ritiro e lista-ordini.

**"Quanto di AFianco mantenere?"**
- **Tipi di prodotto: TENERE il multi-tipo.** Giusto: gli operatori offrono più servizi. Da tenere: ritiro (event_ticket), servizio, prodotto fisico, digitale, corso. Da nascondere: `booking` (deprecato, sostituito da rental+slot). `rental` (alloggi/attrezzatura): tenere ma de-enfatizzare.
- **Cashflow + Dati: TENERE** (decisione founder — è il gestionale contabile).
- **Da nascondere**: Affitti (menu), Fornitori, Anomalie/Alert, Analisi AI, Qualità dati, Moduli (self-service piani).

---

## 1. Il nodo di design: cashflow sì, ma senza AI/anomalie

**Problema architetturale da risolvere per primo** (blocca lo snellimento del menu):

Oggi il menu gerarchizza così: **Fornitori, Anomalie, Analisi AI, Qualità dati sono tutti gated sul modulo `cashflow_monitor`** (`Layout.js:267-275`). Cioè: se cashflow è ACCESO (come vuoi tu), TUTTE e 4 riappaiono. Se è spento, spariscono ma perdi anche il gestionale.

Serve **gating a grana fine**: separare "cashflow core" (Dati, analytics, cashflow monitor) dalle sotto-feature che non servono (AI health/digest, anomalie/alert, qualità dati, fornitori). Il sistema di feature-key nei pricing plan lo permette già — va solo cablato nel menu.

**Decisione:** il menu non deve più gatare quelle 4 voci su `cashflow_monitor` (modulo), ma su feature-key dedicate spente nei piani retreat. Cashflow+Dati restano; AI/anomalie/qualità/fornitori spariscono anche con cashflow acceso.

---

## 2. I problemi trovati (raggruppati)

### A. Controllo ordini & flessibilità pagamento (il cuore del tuo feedback)
| # | Problema | Evidenza |
|---|---|---|
| A1 | **Bonifico esterno = limbo.** Cliente prenota online (ordine draft + link Stripe) ma paga con bonifico → l'operatore non può segnarlo pagato (mark-paid blocca i draft), non può confermarlo saltando il pagamento (skip_payment_check non esposto in UI). Workaround: cancellare e rifare a mano. | `order_service.py:1246`, `commerce_rules.py:30-117` |
| A2 | **Acconti/rate invisibili dalla lista ordini.** Lo schedule si vede solo in dashboard-ritiro; il dettaglio ordine standard non lo mostra né lo fetcha. | `OrdersPage.js` (nessuna call a `/orders/{id}/payment-schedule`) |
| A3 | **Ordine manuale senza piano di pagamento.** L'operatore crea un ordine a mano (prenotazione telefonica) ma non può dirgli "caparra oggi, saldo tra 15 giorni" dall'UI. | `OrderFormDialog` in `OrdersPage.js:91-368` |
| A4 | **Mark-paid a livello ordine non copre i draft.** La catena bozza→conferma→pagato ha uno scalino manuale poco ovvio. | `order_service.py:1236-1258` |

### B. Menu da snellire
| Voce | Path | Oggi | Azione |
|---|---|---|---|
| Affitti | `/reservations` | visibile (gated commerce) | **NASCONDERE** (feature-flag retreat) |
| Fornitori | `/suppliers` | gated cashflow → riappare se cashflow ON | **NASCONDERE** (grana fine) |
| Anomalie/Alert | `/alerts` | gated cashflow → riappare | **NASCONDERE** |
| Analisi AI | `/analisi-ai` | gated cashflow → riappare | **NASCONDERE** |
| Qualità dati | `/data-integrity` | gated cashflow → riappare | **NASCONDERE** |
| Moduli | `/modules` | sempre visibile | **NASCONDERE** (piani retreat fissi; evita che l'operatore riattivi moduli per errore) |
| Cashflow + Dati | `/modules/cashflow*` | gated cashflow | **TENERE** (gestionale) |
| Corsi | `/courses` | gated commerce | TENERE (corsi online) |
| Team | `/team` | sempre visibile | TENERE ma de-enfatizzare (operatore singolo; già limitato a 1) |

### C. Semplicità creazione prodotto
| # | Problema | Nota |
|---|---|---|
| C1 | Type-picker mostra anche `booking` (deprecato) e `rental` in evidenza pari a ritiro/servizio | Riordinare: Ritiro, Servizio, Prodotto, Digitale, Corso; nascondere booking |
| C2 | Lessico "biglietti/evento" ancora in punti del wizard e dashboard | Completare rename → ritiro/posti/partecipanti |
| C3 | I contenuti ricchi si editano solo post-creazione | Aggiungere un cue nel wizard ("dopo la pubblicazione, arricchisci la pagina dalla dashboard") |

---

## 3. Il piano — 4 workstream, in ordine di priorità

### WS-1 · Controllo ordini & pagamento flessibile (PRIORITÀ MASSIMA)
Il pezzo che dà all'operatore il "pieno controllo" che chiedi. Branch `feat/cons-ordini`.

- [x] **1.1 Endpoint "segna incassato fuori piattaforma"** *(fatto 4/7/2026 — VERIFICATO E2E: ordine draft ORD-0002 → 1 chiamata → confermato, caparra paid_manual con nota, saldo pending che prosegue col dunning, biglietto emesso, attore tracciato)*: nuovo `POST /orders/{id}/settle-manual` che (a) conferma l'ordine con `skip_payment_check=True`, (b) segna pagate le righe schedule (o l'intero ordine se non-evento) come `paid_manual` con nota obbligatoria, (c) traccia l'attore. Risolve A1+A4 in un'azione sola. **DoD**: un ordine draft da storefront con "cliente ha pagato con bonifico" si chiude in 1 click+nota; posto riservato, biglietto emesso.
- [x] **1.2 Schedule pagamenti nel dettaglio ordine standard** *(fatto 4/7/2026: OrderScheduleSection nel pannello dettaglio — righe con stato, segna-pagato, proroga, copia-link-pagamento; bottone "Segna incassato" con scelta caparra/tutto via commerce_rules)*: il pannello dettaglio di `OrdersPage` fetcha e mostra `/orders/{id}/payment-schedule` (caparra/saldo/rate + stato) con le stesse azioni della dashboard-ritiro (segna pagato, proroga, condona, invia link). Risolve A2+A3-visibilità. **DoD**: apro un ordine-ritiro dalla lista ordini e vedo/gestisco le scadenze senza passare dalla dashboard evento.
- [x] **1.3 Piano di pagamento su ordine manuale** *(fatto 4/7/2026: selettore data-ritiro nel form Nuovo ordine per i prodotti event_ticket — la data attiva lo schedule caparra/saldo esattamente come dal sito; hydration anche in edit)*: nel form "Nuovo ordine", se l'ordine contiene un ritiro (o su richiesta) permettere di scegliere il piano (unico/caparra+saldo/rate) → genera lo schedule anche per ordini `source=manual`. Risolve A3. **DoD**: prenotazione telefonica → ordine con caparra e saldo schedulati.
- [x] **1.4 Coerenza "segna pagato" bidirezionale** *(fatto 4/7/2026: mark_paid chiude anche le scadenze aperte come paid_manual con nota di sistema → mai dashboard che sollecita un ordine già pagato; mark_unpaid BLOCCATO se il libro mastro ha incassi — il ledger non si falsifica a ritroso, si usano rimborso o azioni per-scadenza. 2 test)*: `mark-paid`/`mark-unpaid` a livello ordine sincronizzati con lo stato schedule (oggi vivono separati). **DoD**: nessuno stato ordine/schedule divergente dopo un'azione manuale.

### WS-2 · Snellimento menu (grana fine su cashflow)
Branch `feat/cons-menu`.

- [x] **2.1 Feature-key retreat** *(fatto 4/7/2026: piano `cashflow_monitor_retreat` — core gestionale ON (analytics/dati/export -1), sotto-feature OFF (email_alerts/digest/alert_config/suppliers/data_quality=0); `rentals:0` su commerce_retreat; nuove chiavi nel registro usage-summary — canUse è ottimista sulle ignote; org demo UI provisionata)*: introdurre flag `retreat_hidden` (o riuso feature-key esistenti) per disaccoppiare Fornitori/Anomalie/AnalisiAI/QualitàDati dal modulo cashflow. Nei piani retreat: cashflow core ON, quelle 4 OFF. **DoD**: con cashflow acceso, quelle 4 voci NON compaiono; Cashflow+Dati sì.
- [x] **2.2 Nascondere Affitti e Moduli** *(fatto 4/7/2026 — VERIFICATO IN BROWSER: sidebar = Dashboard, Cashflow Monitor, Ordini, Calendario, Store, Newsletter, Prodotti, Corsi, Clienti, Team, Impostazioni; spariti Affitti/Fornitori/Anomalie/AnalisiAI/QualitàDati/Moduli — Moduli visibile solo a system_admin; route raggiungibili, solo fuori sidebar)* dal menu per i piani retreat (route restano raggiungibili per sicurezza, ma fuori dalla sidebar). **DoD**: sidebar retreat = Dashboard, Ordini, Calendario, Store, Newsletter, Prodotti, Corsi, Clienti, Cashflow+Dati, Team, Impostazioni.
- [x] **2.3 Verifica label** *(fatto 4/7/2026: nessuna label fuori-dominio residua nella sidebar snellita)* in ottica ritiri dove serve (es. "Calendario" resta, ma verificare che non evochi "affitti"). **DoD**: nessuna label fuori-dominio nella sidebar.

### WS-3 · User-friendliness creazione prodotto
Branch `feat/cons-prodotti`.

- [x] **3.1 Type-picker ripulito** *(fatto 4/7/2026 — VERIFICATO BROWSER: Ritiro 🧘 primo, poi Servizio/Prodotto/Digitale/Corso; rental_range+rental_slot gated su canUse(commerce,rentals) — spariti nel verticale ritiri, riappaiono se il piano riabilita i noleggi; booking già assente)*: ordine Ritiro → Servizio → Prodotto → Digitale → Corso; nascondere `booking`; de-enfatizzare `rental`. Copy che spiega ogni tipo in una riga ("Servizio: consulenze, massaggi, lezioni singole"). **DoD**: un operatore capisce quale tipo scegliere senza chiedere.
- [x] **3.2 Lessico ritiri (mirato)** *(fatto 4/7/2026: "tipologia biglietto"→"tipologia di posto", picker desc, campi partecipante, hint prezzo → posto/partecipante. Lasciato "biglietto" dove indica il pass QR emesso — rinominarlo sarebbe scorretto)*: sweep finale evento→ritiro, biglietto→posto/pacchetto, ticket-holder→partecipante nei punti rimasti (wizard tab Biglietti, dashboard, email admin). **DoD**: grep di "bigliett/evento/ticket" nei testi UI operatore = solo residui giustificati.
- [x] **3.3 Cue contenuti ricchi nel wizard** *(fatto 5/7/2026 in D4: banner al tab Pubblica)*: al tab Pubblica, banner "Dopo la pubblicazione puoi arricchire la pagina (programma, galleria, FAQ) dalla dashboard del ritiro". **DoD**: l'operatore sa dove trovare l'editor contenuti.

### WS-4 · Rifiniture ordini/UX (nice-to-have, dopo WS-1)
Branch `feat/cons-ux`.

- [x] **4.1 Vista "a rischio" in cima agli ordini** *(fatto in D2: chip Da gestire)*: badge/filtro per ordini che richiedono azione (pagato-non-confermato, saldo scaduto, a rischio). **DoD**: l'operatore vede in 2 secondi cosa richiede attenzione.
- [ ] **4.2 Empty states e microcopy** in italiano-ritiri su tutte le schermate operatore chiave.
- [x] **4.3 Semplificare il tab "Biglietti"** *(fatto 5/7/2026 in D4: sezione 1 Posti e pacchetti → sezione 2 Dati partecipanti)* del wizard: separare visivamente "posti e pacchetti" da "dati partecipanti".

---

## 4. Sequenza e regole

1. **WS-1 per primo** (è il "pieno controllo" richiesto e sblocca il caso bonifico, il più concreto).
2. **WS-2** subito dopo (snellimento visibile, basso rischio — solo gating).
3. **WS-3** in parallelo a WS-2 (indipendenti).
4. **WS-4** alla fine, o rimandabile.
5. Regole invariate: branch per workstream, suite verde prima del merge, verifica browser sui flussi toccati, nessuna feature nuova (solo rifinitura).

## 5. Cosa NON fare (per non "sfasciare")
- NON rimuovere codice dei moduli nascosti (AI, anomalie, affitti): si **nascondono via gating**, restano nel fork per un eventuale ripensamento. Rimuovere = rischio + irreversibile.
- NON toccare il motore pagamenti (Fase 2): è testato e funziona; qui si lavora solo su visibilità e punti d'accesso.
- NON introdurre l'account partecipante unico (5.4) ora: è backlog, non consolidamento.

## 6. Stima
WS-1: ~1 settimana · WS-2: 2–3 giorni · WS-3: 2–3 giorni · WS-4: 2–3 giorni. **Totale ~2 settimane** di consolidamento prima della Fase 6 (onboarding + produzione).
