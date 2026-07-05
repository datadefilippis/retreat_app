# RETREAT MASTER PLAN — Piano esecutivo step-by-step
**Repo: `retreat_app` (fork di AFianco) · Creato: 4 luglio 2026 · Questo è il file vivo che seguiamo: ogni step ha una checkbox, si spunta solo a Definition-of-Done verificata.**

> Strategia e razionali sono nei tre documenti in `docs/`: `ECOSISTEMA_OLISTICO_STRATEGIA_2026-07.md` (perché), `BUSINESS_CONCEPT_RITIRI_2026-07.md` (cosa), `PIANO_OPERATIVO_RITIRI_2026-07.md` (journey operatore + gap analysis + design motore pagamenti). Questo file è il COME, in ordine di esecuzione.

---

## 0. Stato di partenza (verificato il 4/7/2026)

- `retreat_app` è una copia di BI_PMI (AFianco) fatta il 4/7 mattina, HEAD `80c8dda`, allineata.
- ⚠️ **Il remote `origin` punta ancora a `datadefilippis/BI_PMI`** → vietato pushare finché non è ripuntato (Fase 0.1).
- Nessun file pesante tracciato in git (mongodb tgz è ignorato). Working tree pulito a parte 5 file untracked ereditati.
- Il codebase eredita: eventi multi-giorno con tier e capienza atomica, attendee per-posto con campi custom, biglietti QR + check-in, broadcast partecipanti, Stripe Connect con `application_fee_percent` (a 0), newsletter, customer portal, cascata annullo ordine. Mancano (verificato): scheduler, acconti/rate, refund admin, cascata annullo evento, calendario pubblico cross-org.

## I 5 principi (cosa significano in pratica qui)

| Principio | Regola operativa |
|---|---|
| **Strutturato** | Si lavora solo su step di questo piano, in ordine; ogni step = branch dedicato + DoD verificata prima di spuntare |
| **Isolato** | Repo GitHub nuovo, DB nuovo, account Stripe nuovo, Brevo nuovo, segreti nuovi. Zero risorse condivise con AFianco. Hard fork: nessun merge da BI_PMI, solo cherry-pick motivati e annotati qui sotto (§ Registro cherry-pick) |
| **Solido** | Il denaro è una macchina a stati con test; idempotenza su tutto ciò che tocca Stripe; snapshot (non riferimenti) per policy/prezzi; nessuno step di pagamento si spunta senza test end-to-end su Stripe test mode |
| **Sicuro** | Checklist sicurezza per fase (sotto); segreti mai in repo e mai riusati da AFianco; webhook sempre signature-verified; GDPR pronto PRIMA del lancio pubblico |
| **Scalabile** | Single-VPS va benissimo per i primi 2 anni (è un vincolo dichiarato, non un difetto); si progettano oggi solo i punti che sarebbero costosi da cambiare dopo: indici Mongo del calendario, uploads separabili, job scheduler con lock (pronto per multi-nodo) |

---

## FASE 0 — Isolamento e igiene del fork (0,5–1 giorno)

**Obiettivo: questo repo diventa un progetto indipendente, pulito e sicuro. Nessuna feature.**

- [x] **0.1 Repo nuovo** *(fatto 4/7/2026)*: origin ripuntato su `datadefilippis/retreat_app`, push riuscito. **Nota: history AZZERATA di proposito** — la push protection di GitHub ha rilevato segreti reali (API key Anthropic + chiave Stripe in `backend/.env`, commit vecchi); ripartiti da un commit iniziale pulito (`8c33573`). La history completa resta in BI_PMI e nel branch locale `afianco-history` (mai pushare quel branch). ⚠️ Follow-up in BI_PMI: ruotare le chiavi esposte.
- [x] **0.2 Pulizia file ereditati** *(fatto 4/7/2026)*: rimossi docx/2FA/mongodb tgz+dir/.emergent/test_reports; doc AFianco non pertinenti spostati in `docs/legacy-afianco/` (embed plans, newsletter, CH/fiduciari, billing runbook storici, cashflow, financial model, MVP plan).
- [x] **0.3 Segreti nuovi** *(fatto 4/7/2026)*: `.env.example` root+backend riscritti brand-neutri e documentati; `backend/.env` dev rigenerato con JWT fresco e zero chiavi AFianco; `frontend/.env` ripulito dal DSN Sentry AFianco. I segreti di prod (Brevo webhook, metrics token, Mongo password) si generano in Fase 6.3 alla creazione dell'ambiente.
- [x] **0.4 Policy hard-fork** *(in vigore dal 4/7/2026)*: BI_PMI e retreat_app divergono. Fix di sicurezza critici su codice condiviso → cherry-pick, annotato nel Registro in fondo. Tutto il resto: no.
- [x] **0.5 `CLAUDE.md` nuovo** *(fatto 4/7/2026)* alla radice: contesto, regole non negoziabili, stack, convenzioni.
- [x] **0.6 Branch model** *(attivo dal 4/7/2026)*: da ora niente push diretti su `main` — feature branch `feat/s<fase>-<tema>` + merge, conventional commits. (Protezione lato GitHub da attivare se il piano account lo consente — su repo privati free non disponibile: vale la regola operativa.)

**DoD Fase 0**: `git remote -v` pulito; repo pushato; `.env.example` completo; working tree senza file estranei; CLAUDE.md presente.

---

## FASE 1 — Fondamenta: dev locale + identità + kill-list (3–5 giorni)

**Obiettivo: l'app gira in locale come "piattaforma ritiri" spoglia — moduli inutili invisibili, brand placeholder, CI verde.**

- [x] **1.1 Dev environment riproducibile** *(fatto 4/7/2026)*: DB `retreat_dev` nuovo; backend verificato in avvio (docs 200 in ~10s); comandi documentati in CLAUDE.md; org di test "Masseria Montanari Dev" creata via `backend/scripts/bootstrap_dev_org.py` (idempotente, con verifica gating integrata). Nota venv: copiato da BI_PMI ma funzionante dal nuovo path — usare sempre `venv/bin/python -m ...`.
- [x] **1.2 Baseline test verde** *(fatto 4/7/2026)*: **3796 passed, 0 failed** (esclusi e2e `test_new_features.py` che richiedono server live — documentato). Fix necessario ereditato dal fork: `database.py` faceva `load_dotenv(override=True)` che azzerava le env di shell/CI con i valori vuoti del nuovo `.env` (in BI_PMI mascherato dalle chiavi reali nel .env) → ora `override=False` come server.py; rimossi i valori vuoti dal `.env`. CI GitHub Actions: workflow ereditati, verifica del run al primo push del branch.
- [x] **1.3 Kill-list via configurazione** *(fatto 4/7/2026)*: aggiunti (ADDITIVI, zero piani legacy toccati) pricing plan `ai_assistant_disabled`, `cashflow_monitor_disabled`, `commerce_retreat` (ordini -1: monetizza la fee, non la quota) e commercial plan `retreat_free`/`retreat_pro` (29€). 11 test di guardia in `tests/test_retreat_plans.py` (integrità referenziale piani→pricing, limiti zero, posizionamento prezzi). Migliorato `_seed_module_plans`: idempotente PER PIANO (inserisce slug mancanti; prima skippava l'intero modulo se non vuoto — i piani nuovi non entravano mai nei DB già inizializzati). **DoD verificata live su retreat_dev**: org su retreat_free → ai_assistant=False, cashflow_monitor=False, commerce/catalog/customers=True. *Deviazione registrata*: i piani legacy restano nel catalogo (fallback e 5 file di test li referenziano); il default signup→retreat_free e la pulizia della pagina pricing sono spostati in Fase 6.1/6.2.
- [x] **1.4 Brand placeholder** *(fatto 4/7/2026)*: 56 occorrenze "AFianco" nei locale (it/de/fr/en) → working title "Retreat App" (ri-sostituibile con un sed al brand definitivo); titolo+description `index.html`. Invariati di proposito: commenti JS (innocui) e il CustomEvent `afianco:customer-logged-in` (funzionale — si rinomina insieme all'embed SDK, Fase 3+). Logo/palette definitivi al brand deciso.
- [x] **1.5 Lingua di dominio** *(fatto 4/7/2026, scope it)*: rename evento→ritiro sui VALORI (mai chiavi JSON) di 9 file locale it (products, catalog, calendar, landings, common, product_catalog, storefront, product_cost, stores) con regole grammaticali (dell'evento→del ritiro, gli eventi→i ritiri); preservati usi generici (webhook events, timeline clienti). de/fr/en si allineano quando il brand è definitivo. "Partecipante" al posto di ticket-holder: entra con la UI di Fase 3.
- [x] **1.6 Sicurezza fase 1** *(fatto 4/7/2026)*: lockout/rate-limit auth verificati dalla suite (test account_deactivation verdi); CORS dev "*" documentato (prod si chiude in Fase 6.3); dependabot GIÀ attivo sul nuovo repo (config ereditata, PR in arrivo). ⚠️ **RILIEVO: il repo GitHub è PUBBLICO** — valutare visibility→private (contiene l'intera piattaforma); decisione del founder.

**DoD Fase 1**: demo locale: creo un'org, creo un ritiro col wizard, lo compro con pagamento unico su Stripe test — e la UI non mostra nulla di AFianco (né AI né cashflow né POS).

---

## FASE 2 — Il motore dei soldi (3,5–4 settimane) — *il cuore, si fa per primo*

> Design completo in `docs/PIANO_OPERATIVO_RITIRI_2026-07.md` Parte III. Qui gli step esecutivi.

### S1 — Scheduler + modelli pagamento (1 settimana)
- [x] **2.1 APScheduler in-process** *(fatto 4/7/2026)*: lock a lease atomico su Mongo (`try_acquire_lock` via find_one_and_update — burst di 10 acquisizioni concorrenti → 1 solo vincitore, testato); lease scaduto viene rubato; journal `scheduler_job_runs` append-only; job heartbeat; avvio nel lifespan server, spento con ENVIRONMENT=test. 6 test integrazione (skip puliti in CI senza Mongo). `services/scheduler_service.py`
- [x] **2.2 Modelli** *(fatto 4/7/2026)*: `PaymentPlan` + `PaymentSchedule` + **`PaymentEvent` append-only** (tracciabilità totale richiesta dal founder: ogni transizione = 1 evento con attore esplicito webhook/scheduler/operator/system, scritto NEL momento). Macchina a stati sole-andata con **guardia ottimistica anti-webhook-doppio** ($elemMatch sullo stato di partenza). `apply_row_transition` = unica porta di modifica: valida, ricalcola totali DAI FATTI, logga. 158 test: invariante somma==totale su totali "cattivi" × modalità × % × rate; collapse last-minute; policy a scaglioni; snapshot congelato; concorrenza. Suite totale: 3960 verdi
- [x] **2.3 Wizard** *(fatto 4/7/2026)*: tab 4 "Come incassi" — 3 modalità con card radio, config caparra (%/fisso, EUR↔centesimi convertiti ai confini), saldo-entro-giorni, rate 2-6, policy a scaglioni editabile, **anteprima live** ("su 800€: 240€ alla prenotazione, 560€ entro il 2/9") — verificato end-to-end in browser: submit → 201 → piano normalizzato in `product.metadata.payment_plan` (validazione server 422 nel wizard endpoint). Blocco landing pubblica → S2 (si mostra solo quando il checkout caparra è reale). **Bug ereditato fixato**: `useUnsavedChangesPrompt` usava `useBlocker` senza data router → TUTTI e 5 i wizard crashavano al mount (mai visto in BI_PMI: CI ferma + error boundary); ora degrada a no-op con beforeunload attivo. Snapshot piano su ordine: già fatto in 2.2/2.4.
- [x] **2.4 Test** *(fatto 4/7/2026)*: coperti in 2.2 (158 unit generazione/stati) + 5 test hook checkout + 6 lock scheduler. Suite: 3965 verdi.

### S2 — Caparra + riserva posti (1 settimana)
- [x] **2.5 Checkout caparra** *(fatto 4/7/2026)*: session schedule-aware ("Caparra — {ritiro}", idempotency per-riga, metadata schedule_row_seq, riga→processing); webhook → riga→paid nel punto in cui il denaro è certo + conferma ordine (= riserva posti alla caparra) + mirror payment_state sull'ordine. Collasso sotto minimo Stripe (50 cent). **2 fix ereditati**: application_fee_amount top-level (Stripe lo rifiuta: va in payment_intent_data — la monetizzazione AFianco sarebbe fallita alla prima accensione; corretto anche il test che codificava il bug) + lookup schedule limitato a ordini-evento.
- [x] **2.6 Email conferma con riepilogo scadenze** *(fatto 4/7/2026)*: sezione "Il tuo piano di pagamenti" nell'email di conferma (pagate ✓ + future con scadenza localizzata + nota promemoria). **Decisione fissata**: MAI link Stripe grezzi nelle email (le session scadono in 24h) — i promemoria S3 porteranno `/pay/{token}` che genera la session fresca al click. Best-effort: errore sezione ≠ email persa. 4 test.
- [x] **2.7 Dashboard incassi v1 (backend)** *(fatto 4/7/2026)*: `GET /event-occurrences/{id}/payments` (aggregato incassato/in-arrivo/in-ritardo/a-rischio + dettaglio per ordine; carrelli abbandonati esclusi dalle metriche) + `POST .../mark-paid-manual` (nota obbligatoria, attore tracciato, fee=0, 409 su transizione invalida). `aggregate_schedules` pura, 4 test + verifica live sui dati e2e. **UI (card incassi in EventDashboard + blocco piano/policy sulla landing + messaging caparra nello storefront checkout) → prossimo blocco di lavoro per chiudere S2.**
- [x] **2.8 Test e2e Stripe test mode** *(fatto 4/7/2026, PAGAMENTO REALE in test)*: bootstrap Connect dev (`scripts/bootstrap_dev_stripe.py`: account custom abilitato, fee 5%) + driver `scripts/e2e_deposit_checkout.py`. Esito: ordine ORD-0001 da 800€ → session da 240€ verificata contro Stripe → pagamento carta 4242 dal founder → riga 0 paid / riga 1 pending, payment_state=deposit_paid, biglietto EVT-AU5K-SKXD emesso, **fee piattaforma 1200 minor (5% esatto) sul PaymentIntent**, event log completo (schedule_created → row_session_created → row_paid webhook:stripe). Nota: riserva posti skippata perché l'occurrence era in bozza (lo storefront non vende bozze; il driver la bypassa — comportamento corretto).

### S3 — Saldo, dunning, rimborsi, cascate (1,5 settimane)
- [x] **2.9 Saldo via link** *(fatto 4/7/2026)*: `pay_token` per riga + `GET /api/public/pay/{token}` → session Stripe FRESCA al click, 303 (smoke live: redirect a checkout.stripe.com; token finto 404; riga pagata → success page). `create_row_checkout_session` con fee, idempotency per-riga, session tracciate in `row_sessions`. **FIX CRITICO nel reconcile**: su ordini già collected la transizione riga viene comunque applicata — senza, il saldo pagato non sarebbe MAI stato registrato a libro.
- [x] **2.10 Dunning** *(fatto 4/7/2026)*: job orario `payment-schedule-scan` — planner PURO (T-7/T-0/overdue/T+3/T+7→at_risk; caparre mai sollecitate; draft/cancelled esclusi; MAI cancellazioni automatiche) + **write-ahead atomico** su reminders_sent (re-run e runner concorrenti → un solo invio, testato). Email promemoria/sollecito con bottone Paga-ora, notifica at-risk all'operatore con le azioni. Endpoint azioni: **postpone** (nuova scadenza futura, promemoria azzerati, overdue/at_risk→pending) e **waive** (motivo obbligatorio). 10 test.
- [x] **2.11 Refund admin** *(fatto 4/7/2026)*: `POST /orders/{id}/refund` — percentuale dalla policy SNAPSHOT sul totale pagato, distribuzione A RITROSO (ultima riga parziale), righe paid_manual flaggate "fuori piattaforma a carico operatore", override con motivo obbligatorio, keep_order per rimborsi senza annullo. Stripe Refund via **provider registry** (linter isolamento SDK rispettato — `create_refund` su StripeProvider). 12 test.
- [x] **2.12 Cascata annullo ritiro** *(fatto 4/7/2026)*: `POST /event-occurrences/{id}/cancel-cascade` con `{confirm:true}` esplicito — occurrence→cancelled, rimborso 100% a tutti (indipendente dalla policy: l'inadempienza è dell'organizzatore), biglietti void via cancel_order, broadcast template cancellation, summary con errori per-ordine. Doppia conferma UI → col blocco UI S3.
- [x] **2.13 Suite test del denaro** *(fatto 4/7/2026)*: **3999 verdi** — generazione (invariante somma su totali cattivi × modalità × % × rate) · collapse last-minute e sotto-minimo · webhook doppio (guardia ottimistica, 1 solo incasso) · race capienza (P7/E1 esistenti) · saldo via link (smoke live 303) · dunning (planner puro + write-ahead atomico) · fasce refund (90/45/5gg, data ignota) · distribuzione a ritroso e canali misti · cascata · regressione flusso full · lock scheduler. **+3 e2e LIVE su Stripe test**: caparra pagata (240€, fee 5%=1200 verificata sul PI) · saldo bonifico manuale · rimborso misto (Stripe refund succeeded + bonifico out-of-platform, biglietto voided).
- [x] **2.14 Sicurezza fase 2** *(fatto 4/7/2026)*: firma webhook invariata (stesso endpoint verificato, dedup event_id); importi SOLO server-side in minor units (il client mostra, mai decide); nessun PAN/PII nei log pagamenti (solo id Stripe e importi); pay_token uuid4 non enumerabile con 404 secco; refund via provider registry (linter isolamento SDK verde); azioni operatore con motivo tracciato e attore esplicito nel log append-only.

**DoD Fase 2**: su Stripe test, ciclo completo senza alcun intervento manuale: prenoto con caparra → ricevo promemoria → pago il saldo dal link → rinuncio → rimborso parziale secondo policy. Tutto visibile nella dashboard incassi.

---

## FASE 3 — La pagina di vendita e l'operatività (1,5 settimane)

- [x] **3.1 Pagina ritiro** *(fatto 4/7/2026)*: modelli AgendaDay/AgendaItem/FaqEntry + agenda/gallery_urls/included/excluded/faq su occurrence (validati); serializer pubblico; landing con Programma a timeline, Galleria grid, Incluso/Escluso a spunte, FAQ accordion — VERIFICATO IN BROWSER con contenuti reali. Editor dashboard `RetreatContentEditor` (card "Pagina di vendita": giorni/voci, galleria URL, liste una-per-riga, FAQ, un solo Salva) — round-trip UI→PATCH→API pubblica verificato live. Upload immagini galleria via URL per ora (upload diretto → backlog).
- [x] **3.2 Preset campi partecipante** *(fatto 4/7/2026)*: 3 bottoni nel wizard (Base / Residenziale: allergie+dieta select / Attività: esperienza+taglia) che popolano i FieldConfig — verificato a livello sorgente+bundle (il browser preview teneva cache; nel browser reale basta un refresh).
- [x] **3.3 Export CSV partecipanti** *(già esistente, verificato 4/7/2026)*: il CSV biglietti G3 include GIÀ le colonne dei campi custom per partecipante (F2 Onda 9) — niente da costruire.
- [x] **3.4 Duplica ritiro** *(fatto 4/7/2026)*: il prefill G6 ora porta anche contenuti F3 + payment_plan + campi partecipante; il wizard li conserva al submit (passthrough). Chi fa 4 ritiri l'anno cambia solo la data.

**DoD Fase 3**: la pagina di un ritiro Masseria regge il confronto visivo e informativo con BookRetreats; l'operatore esporta la lista partecipanti con le diete in 2 click.

---

## FASE 4 — Comunicazioni automatiche (0,5 settimane)

- [x] **4.1 Reminder automatici** *(fatto 4/7/2026)*: job orario `event-comms-scan` — T-7 (template reminder) e T-1 (logistics: venue+indirizzo+note) su occurrence published; planner PURO con finestre precise (scoperta tardiva → recupera entrambe; mai reminder post-inizio; eventi closed niente pre-reminder) + write-ahead atomico su `occurrence.comms_sent` (stesso pattern del dunning: mai doppi invii). 11 test.
- [x] **4.2 Follow-up post-ritiro** *(fatto 4/7/2026)*: T+2 dalla FINE (template followup nuovo, i18n it/en) — tono sobrio, niente marketing spinto; non parte oltre T+7 (un grazie tardivo è peggio di niente); vale anche per eventi closed.
- [x] **4.3 Unsubscribe/suppression** *(EREDITATO, verificato 4/7/2026)*: `email_gate` blocca bounced/blocked/unsubscribed su ogni invio; webhook Brevo aggiorna gli stati; endpoint unsubscribe pubblico per i footer newsletter già esistente. I broadcast automatici passano da broadcast_to_attendees → gate rispettato.

**DoD Fase 4**: ritiro di test riceve l'intera sequenza email senza azioni manuali; l'unsubscribe funziona.

---

## FASE 5 — La piattaforma pubblica (1,5–2 settimane)

- [x] **5.1 Calendario `/ritiri`** *(fatto 4/7/2026)*: `GET /public/retreats` cross-org (published+future, filtri categoria/regione/mese/prezzo); pagina griglia con card (foto/date/luogo/prezzo-da/posti-rimasti + badge "Prenoti con caparra"); tassonomia 9 categorie condivisa. **Indici Mongo F5** creati (status+start_at, region compound, +payment_schedules order/occ/paytoken, payment_events). VERIFICATO IN BROWSER (card reale, filtro detox→vuoto, URL sincronizzato).
- [x] **5.2 Pagine SEO** *(fatto 4/7/2026)*: route `/ritiri/:cat/:regione` (path param > query), hook `useSeoMeta` (title/description/OG/canonical dinamici — verificato "Ritiri yoga in Puglia — prenota online"); **sitemap.xml DINAMICA** (home+9 categorie+coppie categoria×regione reali+landing) e robots.txt dal backend. NOTA: CRA è SPA → per pre-render social/Bing serve SSR (Fase 6 infra, non blocca lancio; Google indicizza il render JS).
- [x] **5.3 Profilo pubblico operatore** *(fatto 4/7/2026)*: `GET /public/operator/{slug}` + pagina `/o/:slug` (brand, bio, prossimi ritiri) — verificato in browser. La Masseria è l'operatore founding; pagina location dedicata → rifinitura post-lancio (il profilo operatore la copre già).
- [ ] **5.4 Account partecipante unico** — PIANIFICATO 5/7/2026 (richiesta founder: 1 account per tutto il marketplace, acquisti da più operatori; single store invariato). Piano esecutivo in **docs/PLATFORM_ACCOUNT_PLAN.md** (P1-P4, ~2 settimane): platform_accounts + magic link sopra, CRM org-scoped intatto sotto, link via platform_account_id.
- [x] **5.5 Sicurezza fase 5** *(fatto 4/7/2026)*: endpoint pubblici read-only (nessun mutating), solo dati dichiarati esposti (whitelist esplicite, mai metadata integrale); robots/sitemap corretti; slug non enumerabili per i token; le query pubbliche filtrano sempre published+attivo+org-pubblica.

**DoD Fase 5**: un utente anonimo trova un ritiro col filtro "Yoga × Puglia × settembre" e completa la prenotazione con caparra di un operatore che non conosce.

---

## FASE 6 — Onboarding, pricing e lancio tecnico (2 settimane)

- [ ] **6.1 Onboarding operatore**: registrazione → Stripe Connect Express → primo ritiro pubblicato. Metrica nord: **meno di 15 minuti**. Test con persona reale non tecnica. → PIANO ESECUTIVO in docs/ONBOARDING_PLAN.md (O1-O4, ~3gg: checklist /inizia con stato derivato dai dati).
- [ ] **6.2 Fee transazionale**: `application_fee_percent` collegata al piano (retreat_free=5, retreat_pro=2) al cambio piano; upgrade Pro self-service (riuso Stripe Billing piattaforma esistente); banner upgrade nella dashboard incassi sopra 1.000€/mese di transato.
- [ ] **6.3 Infrastruttura prod**: VPS nuovo, docker-compose prod adattato, dominio+TLS, Brevo nuovo (SPF/DKIM verificati), account Stripe piattaforma LIVE, monitoraggio di base (uptime + alert email).
- [ ] **6.4 Backup**: mongodump notturno + copia offsite (es. object storage), restore PROVATO una volta (un backup non testato non è un backup).
- [ ] **6.5 GDPR & legale**: privacy policy e cookie della piattaforma, termini per operatori (chi vende è l'operatore, la piattaforma è intermediario tecnico — modello Connect), DPA Brevo/Stripe, registro trattamenti minimo.
- [ ] **6.6 Security review pre-lancio**: giro completo — segreti, CORS, headers (HSTS/CSP), permessi endpoint admin, injection sui filtri pubblici del calendario, dipendenze aggiornate.

**DoD Fase 6**: i ritiri reali della Masseria sono in vendita in produzione; un founding member si è attivato da solo; backup restore provato; checklist sicurezza spuntata.

---

## FASE 7 — Dogfooding e founding members (continuativa)

- [ ] **7.1** Vendere con la piattaforma i ritiri Masseria (primo cliente: noi).
- [ ] **7.2** Onboarding assistito 3–5 founding member (gratis 3 mesi, feedback settimanale).
- [ ] **7.3** Prima retro sul campo: cosa ha richiesto intervento manuale → diventa il backlog di fase 8.

---

## Checklist sicurezza trasversale (si rivede a fine di OGNI fase)

- [ ] Segreti solo in env/secret store; rotazione documentata; mai in log né in repo
- [ ] Webhook Stripe/Brevo: sempre signature-verified, idempotenti per event_id
- [ ] Denaro: importi calcolati solo server-side, minor units, mai fiducia nel client
- [ ] Auth: lockout/rate-limit attivi (ereditati), sessioni con scadenza, admin separato da operatore
- [ ] PII: minimizzazione nei log, export/cancellazione account possibile (GDPR), consensi snapshot
- [ ] Infra: TLS ovunque, backup testati, aggiornamenti dipendenze (dependabot), accesso VPS solo chiave SSH

## Note di scalabilità (decise ora, per non pagarle dopo)

1. **Indici Mongo del calendario** definiti in Fase 5 (non "poi").
2. **Uploads** dietro un'astrazione di storage: oggi volume Docker, domani object storage senza toccare il codice chiamante.
3. **Scheduler con lock distribuito** dal giorno 1: aggiungere un secondo nodo non richiederà refactor.
4. Tutto il resto (CDN, repliche, sharding): **esplicitamente rimandato** — sotto i 100k visitatori/mese il VPS singolo regge, e i soldi vanno in prodotto.

## Debito ereditato tracciato

| Data | Cosa | Dove | Quando si salda |
|---|---|---|---|
| 4/7/2026 | 15 test embed-sdk stale vs refactor embed 2026-06 di BI_PMI (CTA card→"Scopri di più", DOM pills, portal profile) — CI BI_PMI mai girata sugli ultimi 48 commit, rotture mai viste | `apps/embed-sdk/tests/*.test.ts` marcati `it.skip` con nota | Fase 3+, quando si riprende il modulo embed |
| 4/7/2026 | CI `security` rossa: pip-audit segnala CVE nelle dipendenze pinnate | PR Dependabot già aperte sul repo | Igiene parallela a Fase 2 (merge coi test come rete) |

## Registro cherry-pick da BI_PMI (vuoto = buon segno)

| Data | Commit BI_PMI | Motivo | Esito |
|---|---|---|---|
| — | — | — | — |

## Regole d'ingaggio (come lavoriamo su questo piano)

1. Uno step alla volta, nell'ordine del piano; deviazioni si scrivono qui PRIMA di farle.
2. Ogni step: branch dedicato → implementazione+test → DoD verificata → checkbox spuntata con data.
3. Le fasi 2 (soldi) non si comprimono; le fasi 3–4 sì, se serve.
4. Il gate di business resta sovrano: le interviste agli organizzatori (Fase 0 del piano operativo) corrono in parallelo alle Fasi 0–2 tecniche; se il gate fallisce, ci si ferma a fine Fase 2 con un motore pagamenti riusabile comunque.

**Stima totale: ~10 settimane di sviluppo** (coerente con il piano operativo, che resta la fonte per i dettagli di design).
