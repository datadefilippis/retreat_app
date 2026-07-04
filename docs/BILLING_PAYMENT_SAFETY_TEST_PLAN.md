# AFianco — Billing Payment Safety Test Plan

**Versione**: v5.8 / Onda 9.S
**Audience**: tech lead + QA + payments engineer (esecuzione manuale + Stripe CLI)
**Obiettivo critico**: garantire che il sistema pagamenti sia **bulletproof** rispetto a:

1. **Doppia fatturazione** (impossibile)
2. **Subscription orfane** (sub Stripe attiva ma org non lo sa, o viceversa)
3. **Quota enforcement** (i limiti del piano funzionano sempre, non bypass possibili)
4. **Stato consistency** Stripe ↔ MongoDB (mai out of sync per >5 minuti)
5. **Plan changes** safe (proration corretta, no perdite di feature impreviste)
6. **Cancel & reactivate** atomici (no double charge dopo reactivate)
7. **Trial-once** (un solo trial per customer, anche cambiando piano)

**Criterio go-live**:
- 100% degli scenari 🔴 critici DEVONO passare
- ≥95% degli scenari 🟠 high
- ≥85% degli scenari 🟡 medium
- Eventuali fail vanno triagiati: bloccanti = no deploy.

**Companion docs**:
- `BILLING_HOLISTIC_STRESS_TEST_PLAN.md` (UX gaps + module access)
- `BILLING_V58_NEW_PLANS_TESTING_RUNBOOK.md` (catalog rebrand)
- `BILLING_V57_TESTING_RUNBOOK.md` (originale checkout flow)

---

## 0. Pre-flight setup

### 0.1 Stripe test mode

**Verifica configurazione environment**:
```bash
# Backend env
echo $STRIPE_SECRET_KEY  # deve iniziare con sk_test_
echo $STRIPE_WEBHOOK_SECRET  # deve iniziare con whsec_
echo $STRIPE_PUBLISHABLE_KEY  # deve iniziare con pk_test_
```

**Carte test Stripe** (riferimento):

| Carta | Comportamento | Uso |
|---|---|---|
| `4242 4242 4242 4242` | Success | flow normale |
| `4000 0000 0000 0002` | Decline (generic) | past_due test |
| `4000 0000 0000 9995` | Insufficient funds | renewal failure |
| `4000 0025 0000 3155` | Requires 3DS authentication | 3DS scenarios |
| `4000 0084 0000 0000` | Decline (lost card) | declined recovery |
| `4000 0000 0000 0341` | Attaches OK but charge fails on first invoice | first-renewal failure |

CVV/expiry: qualsiasi valore valido (`123`, `12/30`).

### 0.2 Stripe CLI — strumento essenziale

Installazione: `brew install stripe/stripe-cli/stripe`

Comandi che useremo:
```bash
# Forward webhook eventi al backend locale
stripe listen --forward-to http://localhost:8000/api/billing/webhook

# Trigger evento manualmente (per test idempotency)
stripe trigger customer.subscription.updated
stripe trigger invoice.payment_failed
stripe trigger customer.subscription.deleted

# Resend evento esistente (per test duplicate handling)
stripe events resend evt_xxx --webhook-endpoint we_xxx
```

### 0.3 Test orgs deterministiche

Esegui `python backend/scripts/seed_test_orgs.py --reset` per pulire e ricreare:

| Alias | Plan | Status | Purpose |
|---|---|---|---|
| `org_test_free_fresh` | free | none | First-time subscribe |
| `org_test_solo_active` | starter | active | Cancel / change plan |
| `org_test_solo_trial` | starter | trialing | Trial conversion / cancel |
| `org_test_pro_active` | pro | active | Downgrade / addon |
| `org_test_pro_pastdue` | pro | past_due | Recovery flows |
| `org_test_pro_addons` | pro | active | with 2× ai_chat_pack + 1× extra_store |

### 0.4 Strumenti di osservazione (tieni APERTI in parallelo)

1. **Stripe Dashboard test mode** → Payments + Subscriptions + Customers + Events
2. **Backend logs**: `docker logs -f afianco-backend` (cerca: WARNING, ERROR, "duplicate event")
3. **MongoDB shell**: queries su `organizations`, `addon_subscriptions`, `module_subscriptions`, `billing_events`, `audit_log`
4. **Browser DevTools**: Network tab (POST /billing/*) + Console
5. **Stripe CLI**: `stripe listen --print-json` per vedere eventi in tempo reale

---

## A. Initial subscription (first purchase)

### 🔴 PMT-A01 — Free → Solo trial active (happy path)

**Pre**: `org_test_free_fresh` (mai pagato, no trial used).

**Steps**:
1. Login admin → `/plans` → click "Inizia prova gratis 14 giorni" su Solo
2. Stripe Checkout aperto → carta `4242 4242 4242 4242`, completa
3. Redirect a `/settings?billing_success=1`
4. Aspetta 16 secondi max

**Verifiche backend (DB)**:
```js
db.organizations.findOne({id: '<orgid>'})
// MUST: commercial_plan_slug='starter', billing_status='trialing',
//       stripe_subscription_id='sub_xxx', trial_ends_at=<14d future>,
//       has_used_trial=true (or equivalent flag)

db.module_subscriptions.find({organization_id: '<orgid>', status: 'active'})
// MUST: 6 record (cashflow_starter, ai_starter_lite, ecc.)

db.billing_events.find({stripe_subscription_id: 'sub_xxx'})
// MUST: customer.subscription.created, evento processato 1 volta
```

**Verifiche Stripe Dashboard**:
- Customer created with email = org admin email
- Subscription created with `trial_end = +14d`, status = `trialing`
- Invoice $0.00 (trial preview, no charge)
- Customer.metadata.org_id = '<orgid>'

**Verifiche frontend**:
- Toast "Piano aggiornato con successo"
- BillingSection mostra hero card "Solo · €19/mese · In prova fino al X (14 giorni rimanenti)"

**Pass se**: tutti sopra entro 30 secondi. Se webhook ritarda → fallback verify-checkout deve risolvere.

**🚨 FAIL CRITICO se**:
- Multiple subscriptions create (Stripe Dashboard) per stesso checkout
- Multiple BillingEvent rows con stesso stripe_event_id
- Org ha 12 module_subscriptions (provisioning runned 2x)

---

### 🔴 PMT-A02 — Free → direct subscribe (no trial perché has_used_trial=true)

**Pre**: `org_test_free_fresh` ma con `has_used_trial=true` forzato in DB. Questo simula un utente che ha già usato il trial in passato.

**Steps**:
1. Login → `/plans` → click "Abbonati" su Commerce Pro

**Backend atteso**:
- `stripe_service.create_checkout_session` rileva `has_used_trial=true`
- Stripe Checkout creata con `subscription_data.trial_period_days=null`
- Stripe Checkout pagina mostra "Pay €79 today" (no "14-day free trial")

**🚨 FAIL CRITICO se**: Stripe Checkout mostra ancora il trial banner → l'utente ottiene un secondo trial → frode preventiva fallita.

---

### 🟠 PMT-A03 — Subscribe con doppio click rapido (idempotency)

**Pre**: `org_test_free_fresh`.

**Steps**:
1. /plans → click "Abbonati" su Solo **TWICE in rapid succession** (entro 200ms)
2. Network tab DevTools → osserva quante POST `/billing/checkout-session`

**Atteso**:
- Solo **1** POST inviata (frontend disabilita il bottone via `loadingSlug`)
- Solo **1** Stripe Checkout Session creata
- Solo **1** subscription creata after checkout

**Verifica idempotency anche se entrambe le POST passano**:
```js
db.billing_events.find({stripe_subscription_id: '<sub_id>', event_type: 'customer.subscription.created'})
// MUST be exactly 1 row (BillingEvent.stripe_event_id unique index)
```

**🚨 FAIL CRITICO se**: 2 subscriptions create per stesso utente.

---

### 🟠 PMT-A04 — Refresh page durante checkout (recovery)

**Pre**: `org_test_free_fresh`. Inizia checkout ma non completarlo subito.

**Steps**:
1. /plans → click "Abbonati" → Stripe Checkout aperto
2. Aspetta che la sessione esista (check Stripe Dashboard → Sessions)
3. **Chiudi tab senza completare**
4. Riapri /plans → click "Abbonati" di nuovo

**Atteso**:
- Nuova Checkout Session creata (la prima è abandonata)
- L'utente può completare la nuova senza interferenze
- Una volta completata, solo 1 subscription attiva

**Pass se**: non ci sono "subscription incompiete" che bloccano nuovi tentativi.

---

## B. Trial conversion & lifecycle

### 🔴 PMT-B01 — Trial → automatic active conversion

**Pre**: `org_test_solo_trial` (giorno 13 di 14).

**Steps**:
1. Forza scadenza trial: `db.organizations.updateOne({id:..}, {$set:{trial_ends_at: <-1h>}})` 
   AND in Stripe Dashboard → Subscription → trial_end = NOW
2. Trigger Stripe processing: dal Dashboard Customer → Invoice imminente → "Pay now" (oppure aspetta automatico)
3. Webhook `invoice.paid` arriva
4. Webhook `customer.subscription.updated` (status: active)

**Verifiche**:
```js
db.organizations.findOne({id: '<orgid>'})
// MUST: billing_status='active', trial_ends_at=null OR <past>
//       current_period_end=<+30d>
```

Stripe Dashboard:
- Subscription status = active
- Invoice paid €19.00
- Receipt email sent to customer

**🚨 FAIL CRITICO se**:
- Doppia fatturazione (2 invoice $19 per stesso periodo)
- Org resta `trialing` per >24h dopo trial_end
- Sub cancellata accidentalmente

---

### 🔴 PMT-B02 — Trial cancellato a metà → fall to free immediately

**Pre**: `org_test_solo_trial` (giorno 5).

**Steps**:
1. /settings → Billing → "Cancella abbonamento"
2. Modal → "Cancella subito" (NOT "a fine periodo")
3. Conferma reason "Test PMT-B02"

**Backend atteso**:
- POST `/api/billing/cancel-subscription {at_period_end:false}` → 200
- Stripe `Subscription.cancel()` immediate
- Webhook `customer.subscription.deleted` arriva
- DB: `billing_status='canceled'`, `commercial_plan_slug='free'`
- Tutti `addon_subscriptions` linkati alla sub → status='cancelled'
- AuditLog: action='user_cancelled_subscription' con `at_period_end=false`

**🚨 FAIL CRITICO se**:
- Stripe NON addebita un mese (utente deve poter cancellare in trial senza pagare)
- L'org resta su 'starter' invece di tornare a 'free'

---

### 🟠 PMT-B03 — Trial cancel-at-period-end (mantieni trial fino a fine)

**Pre**: `org_test_solo_trial` (giorno 5).

**Steps**:
1. /settings → Billing → "Cancella abbonamento"
2. Modal → lascia "Cancella a fine periodo"
3. Conferma

**Atteso**:
- `cancel_at_period_end=true` su Stripe sub
- Trial continua fino a giorno 14
- Al giorno 14: Stripe NON renews (cancel at period end)
- Webhook `customer.subscription.deleted` al giorno 14
- Org → free

**Pass se**: durante i giorni 5→14 l'utente può ancora usare le feature di Solo.

---

### 🟢 PMT-B04 — Trial reactivate (after cancel-pending in trial)

**Pre**: continua da PMT-B03.

**Steps**:
1. Giorno 7 (mid-cancel-pending): /settings → "Riprendi abbonamento"

**Atteso**:
- Stripe `cancel_at_period_end=false`
- Trial continua, sub ritornerà active a giorno 14
- AuditLog: action='user_reactivated_subscription'

---

## C. Active renewal (recurring billing)

### 🔴 PMT-C01 — Renewal mensile success

**Pre**: `org_test_solo_active` con sub attiva da 28 giorni (current_period_end imminente).

**Steps**:
1. Forza renewal: in Stripe Dashboard → Subscription → "Update upcoming invoice" → "Pay now"
   (oppure usa Stripe CLI: `stripe trigger invoice.paid`)
2. Aspetta webhook `invoice.paid` + `customer.subscription.updated`

**Atteso**:
- Stripe addebita €19.00 con success
- Invoice generata e marcata 'paid'
- Receipt email inviata
- DB: `current_period_end` posticipato di 30 giorni
- AuditLog: nessuna entry (renewal automatico, non user action)

**🚨 FAIL CRITICO se**:
- Doppio addebito (2 invoice per stesso periodo)
- Org diventa past_due nonostante pagamento OK

---

### 🔴 PMT-C02 — Renewal failure (carta declined)

**Pre**: org con sub attiva e carta `4000 0000 0000 0002` (decline). Forza renewal.

**Atteso flow**:
1. Stripe tenta charge → declined
2. Webhook `invoice.payment_failed` arriva
3. DB: `billing_status='past_due'`, `past_due_since=<now>`
4. Stripe automatically retries (3-4x in 7 giorni per default)
5. Email "Pagamento fallito" inviata in lingua admin
6. UI: BillingStatusBanner appare (red, sticky top)

**Dopo 7 giorni di past_due** (`past_due_since + 7d` → trigger backend gate):
7. `_check_billing_gate` rileva past_due > 7d → `read_only` mode
8. UI: ReadOnlyGraceBanner appare
9. Endpoint write → 403 READ_ONLY_GRACE

**Recovery**:
10. Admin va a /settings → "Aggiorna pagamento" → Stripe Customer Portal
11. Aggiorna carta a `4242...`
12. Stripe retries → success
13. Webhook `invoice.paid` → DB: `billing_status='active'`, `past_due_since=null`

**🚨 FAIL CRITICO se**:
- Org resta past_due dopo carta valida + retry
- Doppia fatturazione (vecchia invoice paid + nuova invoice creata)
- Read-only gate mai si attiva → utente continua a usare gratis

---

### 🟠 PMT-C03 — Renewal con 3DS (Strong Customer Authentication)

**Pre**: org con sub attiva e carta `4000 0025 0000 3155` (richiede 3DS).

**Atteso**:
1. Stripe genera invoice → tenta charge → richiede 3DS
2. Stripe invia email all'utente con link per autenticare
3. Se utente autentica → success
4. Se non autentica entro N giorni → past_due

**Pass se**: NESSUN charge senza autenticazione.

---

## D. Plan changes (proration & feature changes)

### 🔴 PMT-D01 — Upgrade Solo → Commerce Pro (mid-cycle, proration corretta)

**Pre**: `org_test_solo_active` da 15 giorni (15 giorni rimanenti).

**Steps**:
1. /plans → "Passa a Commerce Pro"
2. Modal "Conferma upgrade" → mostra proration credit/charge
3. Conferma

**Backend atteso**:
- `stripe_service.modify_subscription(plan_slug='pro', interval='month')`
- Stripe `Subscription.modify` con proration_behavior='create_prorations'
- Stripe genera invoice items: credit per Solo non utilizzato, charge per Pro residuo
- Invoice viene addebitata immediatamente (proration)
- `commercial_plan_slug='pro'`, `module_subscriptions` aggiornati al tier Pro

**Calcolo atteso (esempio 15gg residui)**:
- Credit Solo: €19 × 15/30 = €9.50 (rimborso)
- Charge Pro: €79 × 15/30 = €39.50 (proration)
- Net: €39.50 - €9.50 = **€30.00** addebitati

**Verifiche**:
```js
// Stripe Dashboard → Customer → Invoices
// Should see: 1 invoice with line_items [Credit Solo, Charge Pro] = €30.00 total
```

**🚨 FAIL CRITICO se**:
- L'utente paga il prezzo PIENO di Pro (€79) invece di proration
- Doppio invoice (Solo + Pro entrambi a prezzo pieno)
- Modulo commerce non disponibile dopo upgrade

---

### 🔴 PMT-D02 — Downgrade Commerce Pro → Solo (con store eccedenti)

**Pre**: `org_test_pro_active` con 3 store creati (limite Pro=3).

**Steps**:
1. /plans → "Passa a Solo"
2. Modal mostra credito proporzionale
3. Conferma

**Backend atteso (post Onda 9.K)**:
- Stripe modify a Solo
- Proration credit emesso (≥0, dipende dai giorni residui)
- `commercial_plan_slug='starter'`
- `module_subscriptions.commerce: commerce_disabled`
- **`reconcile_stores_to_plan_limit` deattiva i 2 store non-default** (Onda 9.K Option B)
- I 3 store **NON cancellati** dal DB (preservati)

**Stripe Dashboard atteso**:
- Subscription items aggiornati al price Solo
- Invoice immediato con proration credit
- Nessun double charge

**🚨 FAIL CRITICO se**:
- Stripe addebita €19 + €79 (entrambi)
- I 3 store cancellati dal DB (data loss)
- Nessun proration credit emesso

---

### 🔴 PMT-D03 — Plan change con addons attached (preserva addons)

**Pre**: `org_test_pro_addons` (Commerce Pro + 2× addon_ai_chat_pack + 1× addon_extra_store).

**Steps**:
1. /plans → "Passa a Commerce Starter"

**Atteso**:
- Stripe modify il main item a Starter
- Items addons RIMANGONO sulla sub
- MA: `addon_extra_store` ha `compatible_plans=['pro']` → backend dovrebbe rifiutare l'addon su Starter
- Opzione A: backend AUTO-CANCELLA addon_extra_store on downgrade (raccomandato)
- Opzione B: backend rifiuta il downgrade (utente deve rimuovere addon prima)

**Verifica policy attuale**:
```bash
grep -n "compatible_plans" backend/services/stripe_service.py
```

**🚨 FAIL CRITICO se**:
- Stripe continua a fatturare addon_extra_store su Starter (utente paga per feature non disponibile)
- Reconcile non deattiva l'addon orfano

---

### 🟠 PMT-D04 — Same-tier change (mensile → annuale)

**Pre**: org su Solo mensile (€19/mo).

**Steps**:
1. /plans → toggle "Annuale" → "Passa a Solo annuale"
2. Conferma

**Atteso**:
- Stripe modify con price_id_yearly invece di monthly
- Proration: credit per giorni mensile non utilizzati, charge per anno completo
- Net charge: ~€190 (con piccolo credit)

**Pass se**: addebito una sola volta per l'anno, non più recurrente mensile.

---

### 🟢 PMT-D05 — Plan change rate limiting

Stripe rate limita modify_subscription a ~10/min per customer.

**Steps**:
1. Cambia piano 11 volte in 1 minuto

**Atteso**:
- 11° tentativo → backend riceve `PlanChangeRateLimitError`
- Frontend mostra error 429 con messaggio "Troppi cambi piano"
- Nessun cambio applicato dal 11°

**Pass se**: rate limit gestito gracefully senza errori 500.

---

## E. Add-on lifecycle

### 🔴 PMT-E01 — Buy addon (effective_limit increase immediato)

**Pre**: `org_test_pro_active` con orders_monthly used=1000/1000.

**Steps**:
1. /plans#addons → click "+ Aggiungi" su "+200 ordini"
2. Conferma popup acquisto

**Atteso**:
- POST `/api/billing/add-addon {addon_slug:'addon_orders_pack', quantity:1}` → 200
- Stripe `Subscription.modify` aggiunge subscription_item per il price addon
- Invoice item aggiunto, fatturato proporzionalmente
- Webhook `customer.subscription.updated` arriva
- DB: `addon_subscriptions` upserted (status='active')
- `effective_limit('commerce', 'orders_monthly')` ora = 1000 + 200 = **1200**
- L'utente può ora creare il 1001° ordine

**🚨 FAIL CRITICO se**:
- Stripe addebita 2 volte (doppio addon item)
- Limit non si aggiorna immediatamente (utente blocked nonostante pagamento)

---

### 🔴 PMT-E02 — Buy addon double-click (idempotency)

**Pre**: `org_test_solo_active`.

**Steps**:
1. /plans#addons → click "+50 AI chat" → conferma → CLICK CONFERMA TWICE rapidamente

**Atteso**:
- Frontend `pendingSlug` blocca il 2° click
- Anche se backend riceve 2 POST, `addon_subscriptions` ha unique index su `(org_id, addon_slug, status='active')`
- Solo 1 row, quantity=1 (non 2)

**🚨 FAIL CRITICO se**: addon comprato 2 volte (Stripe addebita 2× €9 = €18).

---

### 🟠 PMT-E03 — Stack addons (3× +50 chat = +150)

**Pre**: `org_test_solo_active` con 0 addons.

**Steps**:
1. /plans#addons → click "+50 AI chat" → conferma (now active 1×)
2. Click "+ Aumenta" → ora active 2×
3. Click "+ Aumenta" → ora active 3×
4. Verifica `effective_limit('ai_assistant', 'chat')` = 20 + 150 = 170

**Atteso**:
- Stripe ha 1 subscription_item con quantity=3 per addon_ai_chat_pack
- DB: `addon_subscriptions.quantity=3`
- Fattura mensile: €27 (3 × €9)

**🚨 FAIL CRITICO se**:
- Stripe ha 3 subscription_items separati invece di 1 con qty=3 (doppia fatturazione)
- Quantity > max_quantity (=5) accettato

---

### 🟢 PMT-E04 — Remove addon (effective_limit drops)

**Pre**: continua da PMT-E03 (3× +50 chat attivo, limit 170).

**Steps**:
1. /settings → BillingSection → "Add-on attivi" → click 🗑 su "+50 AI chat"
2. Conferma

**Atteso**:
- DELETE `/api/billing/addon/addon_ai_chat_pack` → 200
- Stripe rimuove subscription_item
- Proration credit emesso per giorni residui
- DB: `addon_subscriptions.status='cancelled'`
- `effective_limit` torna a 20

---

### 🟢 PMT-E05 — Buy addon su Free (plan_required block)

**Pre**: `org_test_free_fresh`.

**Steps**:
1. /plans#addons → tenta "+ Aggiungi"

**Atteso**:
- Card disabilitata (frontend preventive)
- Se chiamato comunque: backend POST `/billing/add-addon` → 400 `code:'plan_required'`
- Frontend mostra alert "Add-ons richiedono un piano a pagamento"

**Pass se**: nessun addon comprato, nessuna sub creata.

---

## F. Cancellation flows

### 🔴 PMT-F01 — Cancel at period end (graceful)

Già coperto in `BILLING_HOLISTIC_STRESS_TEST_PLAN.md` SUB-03. Riconfermare con focus pagamento:

**Verifica essenziale**:
- Stripe `cancel_at_period_end=true`
- Stripe NOT charges at next renewal
- Org passa a free a current_period_end (webhook customer.subscription.deleted)
- Tutti gli addons → cancelled

**🚨 FAIL CRITICO se**: Stripe addebita anche dopo cancel.

---

### 🔴 PMT-F02 — Reactivate cancel-pending (NO double charge)

**Pre**: org con cancel_at_period_end=true.

**Steps**:
1. /settings → "Riprendi abbonamento"

**Backend atteso**:
- Stripe `cancel_at_period_end=false`
- DB: cancel_at_period_end=false
- Sub continua normalmente

**🚨 FAIL CRITICO se**:
- Stripe genera invoice immediato (doppio charge)
- Una nuova subscription creata invece di reactivate quella esistente

---

### 🔴 PMT-F03 — Immediate cancel → instant downgrade

Già coperto SUB-05. Verifica payment-side:

**🚨 FAIL CRITICO se**:
- Stripe NON cancella → continua a fatturare
- Customer Portal mostra sub still active dopo cancel

---

### 🟠 PMT-F04 — Resubscribe stesso piano dopo cancel (no second trial)

**Pre**: org che ha cancellato e tornata a free.

**Steps**:
1. Stessa org → /plans → "Abbonati" su Solo (stesso piano cancellato)

**Atteso**:
- NESSUN secondo trial offerto (`has_used_trial=true`)
- Pagamento immediato €19
- Sub creata correttamente

**🚨 FAIL CRITICO se**: utente ottiene secondo trial gratis (frode preventiva fallita).

---

### 🟠 PMT-F05 — Cancel via Stripe Customer Portal (esterno)

**Pre**: org attiva.

**Steps**:
1. /settings → "Gestisci fatturazione" → Stripe Portal
2. Cancel via portal
3. Torna in app

**Atteso**:
- Webhook `customer.subscription.updated` riflette cancel
- DB allineato entro 5 minuti

**🚨 FAIL CRITICO se**: app continua a mostrare sub active dopo 1 ora.

---

## G. Past due & payment failure

### 🔴 PMT-G01 — Card declined → past_due → recovery

Coperto in PMT-C02. Riconferma flow E2E.

---

### 🟠 PMT-G02 — Past due durante cancel-pending

**Pre**: org con cancel_at_period_end=true e renewal failure.

**Atteso**:
- Stripe non tenta più di addebitare (cancel pending)
- Org va direttamente a canceled a current_period_end

**Pass se**: nessun double-charge tentato.

---

## H. CRITICAL — Double billing prevention

### 🔴 PMT-H01 — Webhook event delivered twice (idempotency)

**Setup**: Stripe Dashboard → Events → seleziona `customer.subscription.updated` → "Resend"

**Atteso backend**:
- 2° delivery → backend rileva duplicate via `BillingEvent.stripe_event_id` unique index
- Logs: "duplicate event ignored: evt_xxx"
- DB state: invariato (provisioning eseguito 1 sola volta)

**Verifica**:
```js
db.billing_events.find({stripe_event_id: 'evt_xxx'}).count()
// MUST be exactly 1
```

**🚨 FAIL CRITICO se**:
- Doppia provision (12 module_subscriptions invece di 6)
- Doppio addon assegnato

---

### 🔴 PMT-H02 — Concurrent webhook delivery (race condition)

**Setup**: Stripe Dashboard → 2 eventi diversi che arrivano simultaneamente per stessa sub.

**Atteso**:
- `try_acquire_event_lock(stripe_event_id)` previene processing simultaneo
- Eventi processati in serie, no race
- DB consistente

---

### 🔴 PMT-H03 — Stripe outage during plan change (recovery)

**Setup**: Disabilita temporaneamente outbound HTTPS verso api.stripe.com sul backend.

**Steps**:
1. Org tenta plan change
2. `stripe_service.modify_subscription` fallisce con timeout
3. Frontend mostra errore "Errore Stripe, riprova"
4. **Riabilita Stripe**
5. Org ritenta plan change

**Atteso**:
- Nessun stato intermedio in DB (transazione atomica: o tutto o niente)
- Secondo tentativo riesce normalmente
- No double charge

**🚨 FAIL CRITICO se**:
- DB ha plan='pro' ma Stripe sub ancora su 'starter' (out of sync)
- Doppio charge dopo retry

---

### 🔴 PMT-H04 — Webhook never arrives → verify-checkout fallback

**Setup**: Disabilita webhook listener.

**Steps**:
1. Subscribe success in Stripe
2. Webhook NOT received entro 16 secondi
3. Frontend chiama `verify-checkout`

**Atteso**:
- Backend chiama Stripe API direttamente, recupera sub, provisiona localmente
- Risposta `status:'provisioned'`
- DB allineato a Stripe state

**🚨 FAIL CRITICO se**:
- Provisioning duplicato quando webhook eventualmente arriva
- BillingEvent unique constraint violato

---

### 🔴 PMT-H05 — Two browser tabs subscribe simultaneamente

**Setup**: Stesso utente, 2 browser tab aperte sulla pagina /plans.

**Steps**:
1. Tab A: click "Abbonati" su Solo → Stripe Checkout aperto
2. Tab B: click "Abbonati" su Commerce Pro → altra Stripe Checkout aperta
3. Completa Tab A → success
4. Completa Tab B → success

**Atteso**:
- 2 Stripe Checkout sessions create
- Entrambe vanno a buon fine, MA solo 1 subscription resta attiva (la più recente)
- L'altra viene auto-cancellata dal backend
- L'utente non ha 2 subscriptions parallele attive

**🚨 FAIL CRITICO se**:
- 2 subscriptions attive contemporaneamente per stesso customer
- Doppio addebito mensile (€19 + €79 = €98)

---

### 🔴 PMT-H06 — Stripe Customer with multiple sub history

**Pre**: customer ha 5 subscription history (2 cancellate, 1 trial scaduto, 1 active, 1 pending).

**Atteso**:
- Backend identifica SEMPRE la "active" sub (non confonde con storiche)
- Plan change opera SOLO sulla sub attiva
- Cancel opera SOLO sulla sub attiva

**🚨 FAIL CRITICO se**: backend cancella la sub sbagliata.

---

## I. Limit enforcement (no bypass possibile)

### 🔴 PMT-I01 — Quota hit blocks immediately (no off-by-one)

**Per ogni metric** (chat, products, orders, stores, data_rows, team_members):

1. Setup: usage = limit (esattamente)
2. Tenta 1 azione che incrementa di 1
3. **Atteso**: 429 QUOTA_EXCEEDED, paywall si apre

**Verifica off-by-one**:
- Limit=200, used=199 → 200° tentativo passa (ultimo gratis)
- Limit=200, used=200 → 201° tentativo blocca

**🚨 FAIL CRITICO se**: utente passa il limit di 1 (utente paga 200 ma usa 201).

---

### 🔴 PMT-I02 — Quota reset al 1° del mese

**Setup**: org con orders_monthly=200/200 (esaurito).

**Steps**:
1. Forza data: `db.usage_events.deleteMany({org:..., feature:'orders_monthly', period:<this month>})`
   OR aspetta cambio mese
2. Riprova creare ordine

**Atteso**: passa (counter resettato).

---

### 🔴 PMT-I03 — Buy addon → quota immediately extended

**Pre**: org Solo con chat=20/20 (esaurito, paywall opened).

**Steps**:
1. Modal paywall → click "Acquista pack +50 chat AI"
2. /plans#addons → conferma acquisto

**Atteso**:
- Webhook `customer.subscription.updated` arriva
- `effective_limit('chat')` ora = 70
- L'utente può inviare il 21° messaggio chat IMMEDIATAMENTE (entro 30s da acquisto)

**🚨 FAIL CRITICO se**:
- Limit non si aggiorna entro 5 minuti (utente blocked nonostante pagamento)
- Stripe addebita ma DB non riflette

---

## J. Multi-language verification

### 🟠 PMT-J01 — Email pagamento failed in 4 lingue

**Pre**: 4 org diverse con `account.locale ∈ {it,en,de,fr}`.

**Steps**: triggera payment_failed per ognuna (carta declined).

**Atteso**: ogni admin riceve email "Payment failed" in propria lingua.

---

### 🟠 PMT-J02 — Stripe Checkout localizzato

**Atteso**: Stripe Checkout pagina mostra lingua dell'admin (Stripe parametro `locale`).

---

### 🟠 PMT-J03 — Paywall + banner in 4 lingue

Già coperto in `BILLING_HOLISTIC_STRESS_TEST_PLAN.md` I18N-02. Riconfermare con scenari pagamento.

---

## K. Cleanup matrix (resetta tra test)

| Sezione | Reset command |
|---|---|
| A (subscribe) | `python backend/scripts/seed_test_orgs.py --reset` + Stripe Customer Portal cancel sub |
| B (trial) | Reset has_used_trial: `db.organizations.updateOne({id:..}, {$set:{has_used_trial:false, trial_ends_at:null}})` + Stripe sub cancel |
| C (renewal) | Stripe Dashboard → manualmente cancella invoice in pending |
| D (plan change) | `seed_test_orgs.py --reset` |
| E (addons) | `db.addon_subscriptions.deleteMany({org_id:..})` + Stripe.Subscription.modify items=[main_only] |
| F (cancel) | Restart from PMT-A01 with fresh org |
| G (past_due) | `db.organizations.updateOne({id:..}, {$set:{billing_status:'active', past_due_since:null}})` |
| H (idempotency) | `db.billing_events.deleteMany({stripe_event_id: 'evt_xxx'})` (per re-test) |
| I (quota) | `db.usage_events.deleteMany({org:..., period:<this month>})` |

---

## L. Go/No-Go production checklist

### Bloccanti — DEVONO TUTTI passare prima di deploy prod
- [ ] PMT-A01, A02, A03 (subscribe + idempotency + trial-once)
- [ ] PMT-B01, B02 (trial conversion + cancel)
- [ ] PMT-C01, C02 (renewal success + failure)
- [ ] PMT-D01, D02, D03 (upgrade + downgrade + addon preserve)
- [ ] PMT-E01, E02 (addon buy + idempotency)
- [ ] PMT-F01, F02, F03 (cancel + reactivate + immediate)
- [ ] PMT-G01 (past_due → recovery)
- [ ] **PMT-H01..H06 (TUTTI i critical double-billing)**
- [ ] PMT-I01, I02, I03 (quota enforcement no bypass)

### Importanti (≥95% deve passare)
- [ ] PMT-A04, B03, B04, C03, D04, D05, E03, E04, E05, F04, F05, G02
- [ ] PMT-J01, J02, J03 (multi-language)

### UX gaps gia fixati (verifica regressione)
- [x] Onda 9.O — paywall popup explanatory
- [x] Onda 9.P — z-index stacking
- [x] Onda 9.Q — i18n 100% in 4 lingue
- [x] Onda 9.R — no popup duplicato + dialog auto-close

---

## M. Severity guide

🔴 **CRITICAL** — Fail blocca deploy. Comporta:
  - Doppia fatturazione (utente paga 2x)
  - Subscription orfana (Stripe attiva, org non lo sa o viceversa)
  - Quota bypass (utente eccede senza pagare)
  - Trial-once bypass (frode possibile)
  - Stato inconsistente Stripe ↔ DB

🟠 **HIGH** — Fail richiede fix prima di deploy MA workaround possibile:
  - UX confusa (errore generico)
  - Email mancante in lingua sbagliata
  - Edge case di race conditions

🟡 **MEDIUM** — Fail accettabile temporaneamente, fix in roadmap:
  - Cosmetic (visualizzazione data formato)
  - Casi limite estremi (carta richiede 3DS particolare)

🟢 **LOW** — Nice to have, può aspettare prossima release.

---

## N. Stima esecuzione

- Setup ambiente + Stripe CLI: 30 min
- Sezione A (4 scenari): 45 min
- Sezione B (4 scenari): 30 min
- Sezione C (3 scenari): 30 min
- Sezione D (5 scenari): 60 min
- Sezione E (5 scenari): 45 min
- Sezione F (5 scenari): 45 min
- Sezione G (2 scenari): 20 min
- **Sezione H (6 scenari critical): 90 min** (massimo focus)
- Sezione I (3 scenari): 30 min
- Sezione J (3 scenari): 30 min

**Totale stimato**: 7-8 ore di QA dedicato, idealmente 2 sessioni da 4h.

---

## O. Cosa fare in caso di fail

Per ogni fail:
1. **Logga il dettaglio**:
   - Test ID (es. PMT-D02)
   - HTTP response (status + body)
   - Browser DevTools console
   - Stripe Dashboard event link (es. evt_xxxxx)
   - DB snippet (output mongo query rilevante)
2. **Severity**: classifica usando guida sezione M
3. **Triage**:
   - 🔴 Critical → blocca deploy, fix immediato
   - 🟠 High → fix entro 24h, può deployare con feature toggle off
   - 🟡 Medium → ticket per next sprint
4. **Re-test dopo fix** prima di marcare risolto

---

## P. Appendice — comandi utili

### Stripe CLI essentials
```bash
# Listen webhook events (forward to local backend)
stripe listen --forward-to http://localhost:8000/api/billing/webhook

# Trigger test events
stripe trigger customer.subscription.created
stripe trigger invoice.paid
stripe trigger invoice.payment_failed
stripe trigger customer.subscription.deleted

# Resend specific event (test idempotency)
stripe events resend evt_xxxxx --webhook-endpoint we_xxxxx

# List recent events
stripe events list --limit 20

# View specific event payload
stripe events retrieve evt_xxxxx
```

### MongoDB diagnostic queries
```js
// Check org billing state
db.organizations.findOne({id: '<orgid>'}, {
  commercial_plan_slug: 1, billing_status: 1, stripe_subscription_id: 1,
  trial_ends_at: 1, current_period_end: 1, cancel_at_period_end: 1,
  has_used_trial: 1, past_due_since: 1
})

// Active subscriptions for org
db.module_subscriptions.find({organization_id: '<orgid>', status: 'active'})

// Active addons for org
db.addon_subscriptions.find({organization_id: '<orgid>', status: 'active'})

// Recent billing events for sub
db.billing_events.find({stripe_subscription_id: '<sub_id>'}).sort({created_at: -1}).limit(20)

// Recent audit log for org
db.audit_log.find({org_id: '<orgid>', action: /billing|subscription/}).sort({created_at: -1}).limit(20)

// Usage current month for metric
db.usage_events.find({
  organization_id: '<orgid>',
  module_key: 'commerce',
  feature_key: 'orders_monthly',
  consumed_at: {$gte: <month_start_iso>}
}).count()
```

### Backend API direct probes
```bash
# Get current billing status
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/billing/status | jq

# Get usage summary
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/billing/usage-summary | jq

# Force verify checkout (recovery test)
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"cs_test_xxx"}' \
  http://localhost:8000/api/billing/verify-checkout | jq
```

---

**Last updated**: Onda 9.S
**Owner**: tech lead
**Next review**: dopo go-live + 2 settimane di monitoring
