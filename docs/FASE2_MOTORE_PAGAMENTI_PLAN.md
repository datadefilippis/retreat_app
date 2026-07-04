# Fase 2 — Il Motore dei Soldi: piano di dettaglio
**Caparre, saldi, rate, promemoria, rimborsi · Il cuore della piattaforma ritiri · 4/7/2026**

> Figlio del RETREAT_MASTER_PLAN (Fase 2, S1–S3) e del design in PIANO_OPERATIVO Parte III. Questo documento è il riferimento di implementazione: funzionalità complete per l'operatore, architettura, regole di business, sequenza di build e suite di test. Nessuno step si chiude senza la sua DoD.

---

## 1. Obiettivo e principi

**Obiettivo:** l'operatore configura *come incassare* in 30 secondi; da lì in poi caparre, saldi, promemoria, solleciti e rimborsi girano da soli. Ogni euro è tracciato in una macchina a stati esplicita; l'operatore vede sempre chi ha pagato cosa e cosa manca.

**Principi non negoziabili** (dal master plan):
1. Importi SOLO server-side, in **minor units** (centesimi), mai fiducia nel client.
2. **Idempotenza** su ogni interazione Stripe (idempotency key sulle session — pattern esistente; dedup webhook per event_id — esistente; job scheduler idempotenti — nuovo).
3. **Snapshot, non riferimenti**: piano di pagamento e policy di cancellazione vengono congelati sull'ordine alla prenotazione (pattern consensi/attendee esistente). Cambiare il piano di un ritiro NON tocca gli ordini già presi.
4. **Test-first sul denaro**: la suite (§8) si scrive contestualmente, è requisito di chiusura sprint.
5. Riuso dei meccanismi collaudati: Checkout Session, webhook `payment_intent.succeeded`, riserva posti atomica P7/E1, cascata annullo ordine, email service Brevo con retry.

---

## 2. Cosa ottiene l'operatore (perimetro funzionale completo)

| # | Funzionalità | Sprint |
|---|---|---|
| F1 | **Piano di pagamento per ritiro**: unico · caparra+saldo · caparra+rate (config nel wizard, 3 default sensati) | S1 |
| F2 | **Policy di cancellazione a scaglioni** dichiarata sulla pagina di vendita e applicata automaticamente ai rimborsi | S1 |
| F3 | **Caparra online**: il partecipante prenota pagando la caparra; il posto si riserva SOLO a caparra incassata | S2 |
| F4 | **Dashboard incassi** per ritiro: incassato / in arrivo / in ritardo / a rischio; drill-down per partecipante con stato di ogni scadenza | S2 |
| F5 | **Promemoria & dunning automatici** sul saldo/rate: T-7, T-0, T+3, T+7 → "a rischio" con notifica all'operatore e azioni a un click (proroga / libera posto / segna pagato fuori piattaforma) | S3 |
| F6 | **Link paga-saldo** a 1 click nelle email; re-inviabile manualmente dall'operatore in ogni momento | S3 |
| F7 | **Rimborso da dashboard**: importo calcolato dalla policy (override manuale possibile, sempre tracciato con motivo), Stripe refund + posto liberato + email al partecipante in un'azione | S3 |
| F8 | **Annullo ritiro con cascata**: doppia conferma → rimborso 100% a tutti (caparre+saldi), biglietti annullati, broadcast di avviso (template esistente) | S3 |
| F9 | **"Segna pagato manualmente"**: bonifici/contanti fuori piattaforma registrabili sulla scadenza (la realtà degli operatori: qualcuno pagherà sempre con bonifico) — con nota; la fee piattaforma NON si applica agli incassi fuori Stripe | S2 |
| F10 | **Coupon compatibili**: lo sconto (modulo esistente) si applica al totale; caparra e saldo si ricalcolano di conseguenza | S2 |
| F11 | **Export movimenti CSV** per ritiro (per il commercialista): data, partecipante, tipo (caparra/saldo/rata/rimborso), importo, canale (Stripe/manuale), fee | S3 |
| F12 | **Notifiche operatore** via email: caparra incassata, saldo incassato, pagamento in ritardo, posto a rischio, rimborso emesso | S3 |
| F13 | **Fee piattaforma trasparente**: ogni movimento mostra la fee (5% Free / 2% Pro); nessuna sorpresa in dashboard (il wiring fee↔piano si completa in Fase 6.2, qui si predispone il campo per-transazione) | S2 |

**Il partecipante** vede: pagina ritiro con piano pagamenti e policy in chiaro PRIMA di prenotare; checkout caparra; email di conferma con riepilogo scadenze; email promemoria con link paga-adesso; area personale con stato pagamenti; ricevuta per ogni pagamento.

---

## 3. Architettura

### 3.1 Modelli nuovi

**`PaymentPlan`** (embedded nel prodotto-ritiro; snapshot sull'ordine):
```
mode:                "full" | "deposit_balance" | "deposit_installments"
deposit_type:        "percent" | "fixed"
deposit_value:       int (percent 1-90) | minor units se fixed
balance_due_days_before: int (default 30)
installments_count:  int 2-6 (solo deposit_installments)
cancellation_policy: [ {days_before: 60, refund_percent: 100},
                       {days_before: 30, refund_percent: 50},
                       {days_before: 0,  refund_percent: 0} ]
```

**`PaymentSchedule`** (collection nuova, 1 documento per ordine):
```
order_id, organization_id, occurrence_id
plan_snapshot: {PaymentPlan}          # congelato alla prenotazione
currency: "EUR"
rows: [ {seq, kind: "deposit"|"balance"|"installment",
         label, amount_minor, due_at,
         status: "pending"|"processing"|"paid"|"overdue"|"at_risk"
                 |"waived"|"paid_manual"|"refunded"|"cancelled",
         stripe_session_id?, stripe_payment_intent?,
         paid_at?, refund?: {amount_minor, reason, by, at},
         reminders_sent: [{kind, at}] } ]
totals: {due_minor, paid_minor, refunded_minor, fee_minor}
```

**Macchina a stati riga** (transizioni sole-andata, loggate):
```
pending → processing → paid            (Stripe webhook)
pending → paid_manual                  (azione operatore, con nota)
pending → overdue → at_risk            (scheduler, dopo dunning)
pending|overdue|at_risk → waived       (operatore: condona)
paid|paid_manual → refunded            (refund totale o parziale)
qualsiasi → cancelled                  (annullo ordine/ritiro)
```

**Stato ordine esteso**: `payment_state: none → deposit_paid → fully_paid` (derivato dalle righe; l'ordine esistente non cambia struttura, si aggiunge il campo).

### 3.2 Scheduler (fondazione, S1)
- **APScheduler in-process** nel container backend; **lock su Mongo** (`scheduler_locks`, lease con TTL) → un solo runner attivo anche con più repliche future.
- **Job journal** (`scheduler_job_runs`): ogni esecuzione registra job, finestra elaborata, esiti — i job sono rieseguibili senza doppi invii (un promemoria si segna in `reminders_sent` sulla riga PRIMA dell'invio email, pattern write-ahead).
- Job della fase: `payment-schedule-scan` (ogni ora: scadenze → genera session + email; ritardi → dunning; T+7 → at_risk + notifica operatore). I job pre/post-evento (T-7 logistica, T+2 follow-up) sono Fase 4 ma girano sulla stessa fondazione.

### 3.3 Flussi Stripe (riuso del collaudato)
- **Caparra** (alla prenotazione): Checkout Session esistente (mode=payment, idempotency key, application_fee su netto) con line item "Caparra — {ritiro}". Metadata estesa: `schedule_row_seq`. Webhook `payment_intent.succeeded` → row paid → **riserva atomica posti** (P7/E1 spostata qui: chiude il bug oversell "pagato-ma-non-confermato") → emissione biglietti "confermato — saldo dovuto" → email conferma con piano scadenze.
- **Saldo/rata** (a scadenza o on-demand): lo scheduler (o l'operatore col bottone "invia link") genera una nuova Checkout Session per la riga → email con link. Pagina pubblica `/pay/{token}` (token per-riga, scadenza) che reindirizza alla session fresca — così il link nell'email non scade mai davvero: al click si genera la session corrente.
- **Rimborso**: endpoint admin → `stripe.Refund.create` sul payment_intent della riga (parziale supportato), idempotency key per richiesta; webhook `charge.refunded` (handler esistente) riconcilia; cascata ordine/posti riusa `cancel_order`.
- **Niente carte salvate nell'MVP** (decisione presa: opzione B in fase 2 post-lancio se i dati mostrano attrito sul saldo).

### 3.4 Email nuove (su email service esistente, i18n it)
conferma-caparra (con piano scadenze) · promemoria-saldo T-7 · saldo-oggi T-0 · sollecito T+3 · posto-a-rischio (a operatore) T+7 · ricevuta-pagamento · rimborso-emesso · ritiro-annullato (esistente, si riusa) · notifiche operatore (F12).

### 3.5 API & UI
**Backend** (prefisso admin `/api/...`, auth org): CRUD PaymentPlan nel wizard endpoint esistente · `GET /retreats/{occ}/payments` (dashboard) · `POST /orders/{id}/schedule/{seq}/send-link` · `POST /orders/{id}/schedule/{seq}/mark-paid-manual` · `POST /orders/{id}/schedule/{seq}/waive` · `POST /orders/{id}/refund` (policy-driven, override con motivo) · `POST /occurrences/{id}/cancel-cascade` · `GET /retreats/{occ}/payments/export.csv`. **Pubblico**: `GET/POST /pay/{token}`.
**Frontend**: tab wizard "Come incassi" (3 modalità + policy, con anteprima testuale "Il cliente pagherà: …") · dashboard incassi per ritiro · badge stato pagamenti nella lista partecipanti · pagina pubblica paga-saldo · blocco "piano pagamenti + policy" sulla landing del ritiro.

---

## 4. Regole di business (decisioni prese a tavolino)

| Caso | Regola |
|---|---|
| Prenotazione dopo la deadline saldo (last-minute) | Se `oggi >= start - balance_due_days` → il piano collassa in **pagamento unico** (niente caparra a 3 giorni dal via) |
| Multi-posto (quantity N) | Un solo schedule per ordine sul totale; la caparra copre tutti i posti dell'ordine |
| Coupon | Si applica al totale PRIMA del calcolo caparra/saldo (caparra 30% del totale scontato); meccanica Stripe discount esistente (R1) |
| Fee piattaforma | Sul NETTO (post-sconto), come già implementato; registrata per-riga in `fee_minor`; NON si applica a `paid_manual` |
| Rimborso parziale da policy | Percentuale sul TOTALE PAGATO fin lì (caparra+saldi), rimborsata a ritroso: prima l'ultimo pagamento (meno fee già trattenute da Stripe sul primo) |
| Saldo mai pagato dopo dunning | MAI cancellazione automatica: riga `at_risk`, decide l'operatore (relazione > automatismo) |
| Annullo ritiro | Rimborso 100% a tutti indipendentemente dalla policy (l'inadempienza è dell'organizzatore) |
| Valuta | Solo EUR nell'MVP (il flusso CHF/TWINT ereditato resta dormiente) |
| Ordine con piano "unico" | Flusso identico a oggi: zero regressioni sull'esistente (guardia nei test) |
| Riga `processing` | Session generata ma non ancora conclusa: evita doppie session sulla stessa riga (idempotenza applicativa) |

**Default proposti** (config, modificabili dal founder senza codice): caparra 30% · saldo T-30 giorni · dunning T-7/T-0/T+3/T+7 · policy 100% fino a 60gg / 50% fino a 30gg / 0 oltre · rate: mensili, ultima T-30.

---

## 5. Sequenza di build (3 sprint, ~3,5-4 settimane)

### S1 — Fondazione (1 settimana) → branch `feat/f2-s1-scheduler`
| Task | DoD |
|---|---|
| APScheduler + lock Mongo + job journal | 2 processi avviati in parallelo: uno solo esegue; job journal registra le run; riavvio non duplica |
| Modelli PaymentPlan/PaymentSchedule + validazioni | Unit test: generazione schedule per le 3 modalità, arrotondamenti centesimi (somma righe == totale), last-minute collapse, policy snapshot |
| Wizard tab "Come incassi" + landing block | Creo un ritiro con caparra 30%+saldo T-30: la pagina pubblica mostra piano e policy |
| Estensione checkout: ordine nasce con schedule | Ordine di test ha schedule corretto e `payment_state=none` |

### S2 — La caparra (1 settimana) → `feat/f2-s2-caparra`
| Task | DoD |
|---|---|
| Checkout caparra (session su riga deposit, metadata estesa) | Su Stripe test: pago la caparra, la riga va `paid`, ordine `deposit_paid` |
| Riserva posti spostata alla caparra (P7/E1) + fix oversell | Test race: 2 caparre concorrenti su 1 posto → una sola riserva, l'altra gestita pulita |
| Biglietti "confermato — saldo dovuto" + email conferma con scadenze | Email ricevuta con piano corretto |
| Dashboard incassi v1 + mark-paid-manual + integrazione coupon | Vedo incassato/da incassare; segno un bonifico come pagato con nota |

### S3 — Saldo, dunning, rimborsi, cascate (1,5-2 settimane) → `feat/f2-s3-saldo-rimborsi`
| Task | DoD |
|---|---|
| Pagina `/pay/{token}` + generazione session saldo + email | Pago il saldo dal link email; ordine `fully_paid`; ricevuta |
| Job dunning completo + notifiche operatore + azioni (proroga/waive/libera) | Simulazione temporale: sequenza T-7→T+7 esatta, nessun doppio invio su re-run |
| Refund endpoint (policy + override tracciato) + webhook riconcilia | Rinuncia a 45gg con policy 50%@30: rimborso 100%? no: fascia corretta calcolata e verificata; posto liberato |
| Cascata annullo ritiro | Ritiro con 5 ordini misti (caparra sola / fully paid / manuale): tutti rimborsati correttamente, biglietti void, broadcast inviato |
| Export CSV + suite del denaro completa (§6) verde | CSV quadra col dashboard; suite 100% |

**Chiusura fase**: merge su main con CI verde + demo end-to-end su Stripe test documentata (screenshot nel PR di merge) + checkbox master plan.

---

## 6. Suite test del denaro (requisito di chiusura, non opzione)

1. Generazione schedule: 3 modalità × (percent/fixed) × arrotondamenti (99,99€, 3 rate) — la somma delle righe è SEMPRE il totale.
2. Last-minute collapse (T-29, T-1).
3. Caparra: webhook idempotente (stesso event 2×→1 riserva), session duplicata (riga processing), caparra su ordine multi-posto e con coupon.
4. Race capienza: 2 ordini, 1 posto — mai oversell, mai posto fantasma.
5. Saldo: link scaduto→rigenerato, pagamento dopo overdue, mark-paid-manual (fee=0).
6. Dunning: sequenza completa, re-run del job senza doppi invii (write-ahead), riga waived non sollecita.
7. Refund: fasce policy (61gg/45gg/29gg/5gg), override con motivo, refund parziale a ritroso, webhook charge.refunded riconcilia senza doppio conteggio.
8. Cascata annullo ritiro: mix di stati, totale rimborsato == totale incassato Stripe; paid_manual segnalato all'operatore (rimborso fuori piattaforma a suo carico).
9. Regressione: ordine "pagamento unico" si comporta ESATTAMENTE come oggi (snapshot test sul flusso esistente).
10. Scheduler: lock esclusivo, lease scaduto ripreso, job journal.

---

## 7. Fuori perimetro MVP (esplicito, per non ricascarci)
Carte salvate / addebito off-session (opzione B) · multi-valuta · fatturazione fiscale automatica (l'export CSV è il ponte) · split payment tra più partecipanti dello stesso ordine · gift card · pagamento in 2 clic dal wallet (Apple/Google Pay arriva gratis con Checkout, non si configura ad hoc) · lista d'attesa.

## 8. Nota operativa
- CI `security` (pip-audit) attualmente rossa per CVE nelle dipendenze pinnate: si risana mergiando le PR Dependabot già aperte (suite come rete di sicurezza) — task di igiene parallelo alla fase, non bloccante per S1.
- Serve un **account Stripe test dedicato Retreat App** entro l'inizio di S2 (chiavi sk_test/pk_test nel .env dev; 10 minuti su dashboard.stripe.com).
