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

- [ ] **1.1 Dev environment riproducibile**: DB Mongo locale NUOVO e vuoto (`retreat_dev`, mai il dump AFianco); backend+frontend avviabili con un comando documentato in CLAUDE.md; seed minimo (1 org di test "Masseria Montanari Dev").
- [ ] **1.2 Baseline test verde**: suite esistente gira; i test che falliscono per via del fork si sistemano o si marcano con motivazione. CI GitHub Actions attiva sul repo nuovo.
- [ ] **1.3 Kill-list via configurazione**: seed nuovi commercial plan `retreat_free` / `retreat_pro` con AI=0, cashflow=0, POS/spedizioni/magazzino/noleggi disattivati. Verifica: un'org su `retreat_free` NON vede nessuno di quei moduli nella UI. (Il gating esiste già: limiti a 0 = modulo nascosto.)
- [ ] **1.4 Brand placeholder**: `SMTP_FROM_NAME`, titolo app, logo temporaneo, palette via design tokens. Il nome definitivo (candidati verificati liberi: ritirando.it, ritiriinitalia.it) si decide fuori dal codice — qui tutto passa da env/config, zero hardcoding nuovo.
- [ ] **1.5 Lingua di dominio**: censimento stringhe UI area eventi → "evento" diventa "ritiro", "ticket holder" → "partecipante" (i18n: partire da `it`, `en` dopo).
- [ ] **1.6 Sicurezza fase 1**: `allowed_origins` CORS ripuliti (solo domini nostri); rate-limit/lockout auth ereditati verificati attivi; dependabot attivo sul repo nuovo.

**DoD Fase 1**: demo locale: creo un'org, creo un ritiro col wizard, lo compro con pagamento unico su Stripe test — e la UI non mostra nulla di AFianco (né AI né cashflow né POS).

---

## FASE 2 — Il motore dei soldi (3,5–4 settimane) — *il cuore, si fa per primo*

> Design completo in `docs/PIANO_OPERATIVO_RITIRI_2026-07.md` Parte III. Qui gli step esecutivi.

### S1 — Scheduler + modelli pagamento (1 settimana)
- [ ] **2.1 APScheduler in-process** con lock su Mongo (collection `scheduler_locks`): un solo runner attivo, job idempotenti, ogni run logga inizio/fine/esito. Job heartbeat di prova.
- [ ] **2.2 Modelli**: `PaymentPlan` (full / deposit+balance / installments; deposit % o fisso; `balance_due_days_before`; policy cancellazione a scaglioni) e `PaymentSchedule` per-ordine (righe con `seq, label, amount, due_at, status, stripe_ref`). Stati e transizioni documentati nel codice.
- [ ] **2.3 Wizard**: tab "Come incassi" nel wizard ritiro (scelta piano + policy). Snapshot congelato di piano+policy sull'ordine alla prenotazione (pattern consensi già esistente).
- [ ] **2.4 Test**: unit su generazione schedule (caparra 30%, rate 3×, arrotondamenti, fusi orari/scadenze).

### S2 — Caparra + riserva posti (1 settimana)
- [ ] **2.5 Checkout caparra**: Checkout Session esistente con line item caparra; webhook conferma → **riserva atomica dei posti alla caparra** (sposta il momento della riserva: chiude anche il bug oversell "pagato-ma-non-confermato" documentato).
- [ ] **2.6 Biglietti in stato "confermato — saldo dovuto"**; email conferma con riepilogo scadenze.
- [ ] **2.7 Dashboard incassi v1** per l'operatore: per ritiro — incassato, in scadenza, in ritardo; per partecipante — stato pagamenti.
- [ ] **2.8 Test e2e Stripe test mode**: prenotazione con caparra → posti scalati → ticket emesso → schedule corretto.

### S3 — Saldo, dunning, rimborsi, cascate (1,5 settimane)
- [ ] **2.9 Saldo via link**: alla scadenza lo scheduler genera Checkout Session del saldo + email "salda con un click" (niente carte salvate nell'MVP — decisione presa, opzione B in fase 2).
- [ ] **2.10 Dunning**: T-7 promemoria / T-0 scade oggi / T+3 sollecito / T+7 stato "a rischio" + notifica operatore con azioni (proroga / libera posto / contatta). Nessuna cancellazione automatica.
- [ ] **2.11 Refund admin**: endpoint `POST /orders/{id}/refund` → Stripe Refund API, importo calcolato dalla policy snapshot (override manuale possibile, tracciato), aggiorna schedule, innesca cascata annullo ordine esistente.
- [ ] **2.12 Cascata annullo ritiro**: evento → cancelled ⇒ refund automatico a tutti + void biglietti + broadcast template "cancellation" (esistente). Con doppia conferma in UI.
- [ ] **2.13 Suite test del denaro** (obbligatoria per spuntare la fase): caparra+saldo felice; saldo mai pagato; rinuncia entro/oltre policy; annullo ritiro; doppio webhook (idempotenza); race capienza.
- [ ] **2.14 Sicurezza fase 2**: firma webhook verificata anche sul nuovo flusso; log pagamenti senza PAN/PII sensibili; importi sempre in minor units server-side; nessun importo accettato dal client.

**DoD Fase 2**: su Stripe test, ciclo completo senza alcun intervento manuale: prenoto con caparra → ricevo promemoria → pago il saldo dal link → rinuncio → rimborso parziale secondo policy. Tutto visibile nella dashboard incassi.

---

## FASE 3 — La pagina di vendita e l'operatività (1,5 settimane)

- [ ] **3.1 Pagina ritiro**: programma/agenda strutturata giorno-per-giorno; galleria multi-foto (riuso uploads); sezioni incluso/escluso e FAQ.
- [ ] **3.2 Campi partecipante nel wizard** (oggi solo post-creazione) con 3 preset pronti: base / residenziale (allergie+diete) / attività (esperienza+taglia).
- [ ] **3.3 Export CSV partecipanti** con campi custom; vista aggregata per tipologia camera/tier.
- [ ] **3.4 Duplica ritiro** su nuova data (wizard precompilato).

**DoD Fase 3**: la pagina di un ritiro Masseria regge il confronto visivo e informativo con BookRetreats; l'operatore esporta la lista partecipanti con le diete in 2 click.

---

## FASE 4 — Comunicazioni automatiche (0,5 settimane)

- [ ] **4.1 Reminder automatici**: T-7 e T-1 pre-ritiro (template broadcast esistenti agganciati allo scheduler).
- [ ] **4.2 Follow-up post-ritiro** T+2 (ringraziamento + invito newsletter/prossimo ritiro).
- [ ] **4.3 Unsubscribe**: link nelle email marketing + suppression list rispettata (GDPR, obbligatorio prima del lancio pubblico).

**DoD Fase 4**: ritiro di test riceve l'intera sequenza email senza azioni manuali; l'unsubscribe funziona.

---

## FASE 5 — La piattaforma pubblica (1,5–2 settimane)

- [ ] **5.1 Calendario `/ritiri`**: card con foto/date/luogo/prezzo-da/posti-rimasti; filtri categoria, regione, mese, durata, prezzo. Tassonomia 9 categorie (Parte V del piano operativo). **Indici Mongo progettati qui** (categoria+regione+data) — è il punto costoso-da-cambiare-dopo.
- [ ] **5.2 Pagine SEO** `/ritiri/[categoria]/[regione]` server-rendered o pre-generate, sitemap, metadati.
- [ ] **5.3 Profilo pubblico operatore** `/o/[slug]` + **pagina location Masseria** (unica location al lancio — niente directory strutture, decisione presa).
- [ ] **5.4 Account partecipante unico di piattaforma** (DB vergine: si modella così da subito; il login del portal esistente si adatta).
- [ ] **5.5 Sicurezza fase 5**: endpoint pubblici read-only con rate limiting; nessun dato personale operatore esposto oltre il profilo dichiarato; robots/sitemap corretti.

**DoD Fase 5**: un utente anonimo trova un ritiro col filtro "Yoga × Puglia × settembre" e completa la prenotazione con caparra di un operatore che non conosce.

---

## FASE 6 — Onboarding, pricing e lancio tecnico (2 settimane)

- [ ] **6.1 Onboarding operatore**: registrazione → Stripe Connect Express → primo ritiro pubblicato. Metrica nord: **meno di 15 minuti**. Test con persona reale non tecnica.
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
