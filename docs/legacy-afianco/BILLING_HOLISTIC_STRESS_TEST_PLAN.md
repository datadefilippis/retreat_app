# AFianco — Billing/Subscription Holistic Stress Test Plan

**Versione**: v5.8 / Onda 9.I
**Audience**: tech lead + QA, manuale (no automation framework)
**Obiettivo**: stressare il sistema dal punto di vista dell'utente finale, mappare TUTTE
le casistiche di sottoscrizione, prove gratuite, blocchi modulo e blocchi quota,
identificare errori generici / non chiari, validare la UX dei flussi di upgrade.

**Criterio go-live**: il 100% degli scenari critici (marcati 🔴) e ≥90% degli
scenari standard (marcati 🟢) deve passare. Eventuali gap UX vanno almeno
documentati nel modulo "Known limitations" del runbook prima del deploy.

---

## 0. Pre-condizioni e setup ambiente

### 0.1 Test orgs richieste (creare prima di iniziare)

Esegui `backend/scripts/seed_test_orgs.py --reset` per generare un set deterministico,
oppure crea manualmente:

| Alias | Slug DB | Stato | Trial usato? | Note |
|---|---|---|---|---|
| `org_free_fresh` | free | none | no | Account appena creato, mai pagato |
| `org_free_trialed` | free | none | **sì** | Ha già usato 14gg trial e poi caduto |
| `org_solo_active` | starter | active | sì | Sub Stripe attiva su Solo |
| `org_solo_trial` | starter | trialing | sì | Giorno 5 di 14gg trial Solo |
| `org_starter_active` | core | active | sì | Sub attiva Commerce Starter |
| `org_starter_pastdue` | core | past_due | sì | Pagamento fallito 3gg fa |
| `org_pro_active` | pro | active | sì | Sub attiva Commerce Pro |
| `org_pro_cancelpending` | pro | active | sì | `cancel_at_period_end=true` |
| `org_pro_with_addons` | pro | active | sì | Ha 2× +50 AI chat + 1× +1 store |

### 0.2 Test users

Per ogni org, almeno 1 admin + 1 viewer. Email pattern: `admin.<orgalias>@test.afian.co`.

### 0.3 Stripe test mode

- Carta che funziona: `4242 4242 4242 4242` (qualsiasi CVV, data futura)
- Carta declined: `4000 0000 0000 0002` (per past_due scenarios)
- Carta che richiede 3DS: `4000 0025 0000 3155` (edge case)

### 0.4 Strumenti di osservazione consigliati

In ogni scenario, tieni aperti in parallelo:
- **Browser DevTools** → Console + Network (per vedere axios responses)
- **Stripe Dashboard test mode** → Subscriptions + Customers + Events
- **MongoDB shell** o Compass → `organizations`, `addon_subscriptions`, `audit_log`, `org_quota_notices`
- **Backend logs** (`docker logs ... -f` o equivalente) → cercare warning/error
- **App/Apple Mail / Mailtrap** → email recipients

---

## A. Subscription lifecycle (SUB)

### 🔴 SUB-01 — Free → checkout → trial active

**Pre**: usa `org_free_fresh` (mai pagato, no trial used).

**Steps**:
1. Login → vai a `/plans`
2. Click "Prova gratis 14 giorni" su Commerce Starter
3. Sei redirezzato a Stripe Checkout
4. Inserisci `4242 4242 4242 4242`, completa
5. Sei rimandato a `/settings?billing_success=1`

**Backend atteso**:
- Stripe webhook `customer.subscription.created` arriva
- `organizations.billing_status = "trialing"`
- `organizations.commercial_plan_slug = "core"`
- `organizations.trial_ends_at = <14gg da ora>`
- `module_subscriptions` per ogni modulo (cashflow_pro, ai_starter, ecc.)
- Email "Welcome to Commerce Starter" inviata in lingua dell'admin

**Frontend atteso**:
- Toast "Piano aggiornato con successo"
- BillingSection mostra "Commerce Starter · €39/mese · In prova fino al X (14 giorni rimanenti)"
- Sidebar nav include voci commerce (Stores, Orders, Reservations)

**Pass se**: tutto sopra entro 30 secondi dal checkout. Se webhook non arriva in 16s → fallback `verify-checkout` deve risolvere comunque.

---

### 🔴 SUB-02 — Trial → automatic conversion ad active

**Pre**: usa `org_solo_trial` (giorno 5 di trial). Per accelerare: in MongoDB
`db.organizations.updateOne({id:..}, {$set:{trial_ends_at: <ieri>}})`.
Trigger Stripe: dal Dashboard → Customer → Invoice → "Pay now" sulla carta default,
oppure aspetta che Stripe processi (test mode è quasi-istantaneo).

**Backend atteso**:
- Webhook `invoice.paid` → `billing_status: "trialing"` → `"active"`
- `current_period_end` posticipato di 1 mese
- Email "Subscription activated" inviata

**Frontend atteso**:
- Hero card BillingSection ora mostra "Prossimo rinnovo: <data>" (no più trial countdown)
- `useBilling()` riflette `isTrialing=false, isPaid=true`

**Pass se**: in /settings vedi info aggiornate, no errori in console, la sub è "active" in Stripe Dashboard.

---

### 🔴 SUB-03 — Cancel at period end (UI nativa)

**Pre**: usa `org_pro_active`.

**Steps**:
1. /settings → Billing → click rosso "Cancella abbonamento"
2. Modal: lascia "Cancella a fine periodo", reason "Test SUB-03"
3. Conferma

**Backend atteso**:
- POST `/api/billing/cancel-subscription {at_period_end:true, reason:"Test SUB-03"}` → 200
- Stripe `Subscription.cancel_at_period_end=true`
- AuditLog: `action="user_cancelled_subscription"`
- `billing_status` resta `active`

**Frontend atteso**:
- Toast "Abbonamento programmato per la cancellazione a fine periodo"
- Banner arancione "Dopo questa data il tuo piano tornerà a Gratuito"
- Hero subline ora "Accesso fino al X (cancellazione programmata)"
- Bottone "Cancella" nasconde, appare "Riprendi abbonamento"

**Pass se**: tutto sopra. Sub continua a essere usabile fino a current_period_end.

---

### 🔴 SUB-04 — Reactivate dopo cancel-pending

**Pre**: continua da SUB-03 (`cancel_at_period_end=true`).

**Steps**:
1. Click "Riprendi abbonamento"

**Backend atteso**:
- POST `/api/billing/reactivate-subscription` → 200
- Stripe `cancel_at_period_end=false`
- AuditLog: `action="user_reactivated_subscription"`

**Frontend atteso**:
- Toast "Abbonamento riattivato"
- Banner arancione sparisce
- Hero subline torna "Prossimo rinnovo: X"
- Bottone "Cancella" riappare

**Pass se**: stato visivo identico a pre-cancel.

---

### 🔴 SUB-05 — Immediate cancel → Free instantly

**Pre**: `org_pro_active` (resetta da SUB-04 se necessario).

**Steps**:
1. /settings → Billing → "Cancella abbonamento"
2. Switch radio a "Cancella subito" (rosso)
3. Reason "Test SUB-05" → conferma immediata

**Backend atteso**:
- Stripe `Subscription.cancel()` → status="canceled"
- Webhook `customer.subscription.deleted` arriva
- `billing_status: "canceled"`, eventualmente downgrade a `commercial_plan_slug="free"`
- Tutti gli `addon_subscriptions` linkati alla sub vengono cancellati

**Frontend atteso**:
- Toast "Abbonamento cancellato. Il piano è stato riportato a Free"
- Hero card mostra "Free · Gratis"
- Sidebar nav: voci commerce SCOMPAIONO (verifica con refresh)

**Pass se**: nav sidebar pulita, accesso a /commerce dà errore (vedi MOD-01).

---

### 🟢 SUB-06 — Cancel via Stripe Portal (esterno)

**Pre**: `org_starter_active`.

**Steps**:
1. /settings → Billing → "Gestisci fatturazione" → vai a Stripe Customer Portal
2. Click "Cancella subscription" nel portal Stripe
3. Torna in /settings

**Backend atteso**:
- Webhook `customer.subscription.updated` → reflect cancel state
- Stesso effetto di SUB-03 o SUB-05 a seconda della scelta nel portal

**Frontend atteso**:
- BillingSection mostra correttamente lo stato (potrebbe richiedere refresh manuale)

**Pass se**: il backend rispecchia lo stato Stripe entro 5 minuti.

**⚠ Failure indicator**: se l'utente vede ancora "active" dopo 5 minuti, c'è un bug di reconcile.

---

## B. Plan changes (PLN)

### 🔴 PLN-01 — Upgrade Solo → Commerce Pro (durante trial)

**Pre**: `org_solo_trial` giorno 5 di 14.

**Steps**:
1. /plans → click "Passa a Commerce Pro"
2. Modal "Conferma upgrade" → conferma

**Backend atteso**:
- POST `/api/billing/modify-subscription {plan_slug:"pro"}` → 200
- Stripe `Subscription.modify` con nuovo price_id Pro
- Webhook arriva, `commercial_plan_slug: "pro"`
- Se trial era attivo, **trial continua per i giorni rimanenti** (Stripe behavior)
- `module_subscriptions` aggiornati al tier Pro

**Frontend atteso**:
- Toast "Piano cambiato a Commerce Pro"
- BillingSection rifletterà Pro entro 10s (polling refresh)
- Sidebar nav: nuove voci per limiti più alti (es. multi-store)

**Pass se**: trial preservato, no doppia addebitazione.

---

### 🔴 PLN-02 — Downgrade Commerce Pro → Solo (LOSING commerce)

**Pre**: `org_pro_active` con 3 store attivi (1 default + 2 non-default) e 1 ordine in corso.

**Steps**:
1. /plans → click "Passa a Solo"
2. Modal "Conferma downgrade" → mostra credito proporzionale → conferma

**Backend atteso (post Onda 9.K — Option B implementata)**:
- Stripe `Subscription.modify` con price Solo
- Proration credit emesso (visibile in Stripe Dashboard → Invoice imminente)
- `commercial_plan_slug: "starter"`
- `module_subscriptions.commerce: commerce_disabled` (era commerce_pro)
- **`reconcile_stores_to_plan_limit()` chiamato in Step 5 di provisioning**:
  - effective_max=0 (Solo ha stores_max=0)
  - 2 store non-default → deactivated (`is_active=false, deactivated_for_plan_violation=true, plan_violation_deactivated_at=<now>`)
  - 1 store default → preserved (mai deattivato)
- Storefront `/co/<orgslug>/<store-slug>` per i 2 deattivati → 404 (filter `is_active:true`)

**Frontend atteso**:
- Toast "Piano cambiato a Solo"
- Sidebar nav: voci commerce SCOMPAIONO (commerce_disabled)
- Se l'utente accede `/stores` direttamente: vede 3 card di cui 2 con:
  - bordo amber + sfondo amber
  - banner inline "🔒 Store nascosto: limite del piano superato" + body chiaro
  - badge "🔒 Limite piano" accanto al nome
  - CTA "Aggiorna piano per riattivare" → navigate `/plans`

**Pass se**:
1. Downgrade va a buon fine senza errori
2. I 2 store non-default mostrano badge + banner amber
3. Storefront pubblico restituisce 404 sui 2 store deattivati
4. DB conserva tutti e 3 i record (nessun delete)
5. Logs backend mostrano `store_reconcile={'deactivated': 2, ...}`

### 🔴 PLN-02b — Re-upgrade Solo → Commerce Pro (auto-reactivation)

**Pre**: stesso org dopo PLN-02 (Solo con 2 store deattivati).

**Steps**:
1. /plans → "Passa a Commerce Pro"
2. Conferma upgrade

**Backend atteso**:
- `reconcile_stores_to_plan_limit()` rilevata effective_max=3 e plan_deactivated rows=2
- 2 store ri-attivati (FIFO: longest-deactivated first)
- `is_active=true, deactivated_for_plan_violation=false, plan_violation_deactivated_at=null`

**Frontend atteso**:
- Sidebar nav: voci commerce riappaiono
- /stores → 3 card normali (no più badge amber)
- Storefront pubblico: i 2 store sono di nuovo accessibili (con stessi slug/dati di prima)

**Pass se**: zero data loss, slug preservati, riattivazione automatica.

---

### 🟢 PLN-03 — Downgrade nello stesso tier commerce (Pro → Starter)

**Pre**: `org_pro_active` con 3 store attivi (1 default + 2 non-default, limite Pro=3).

**Steps**:
1. /plans → "Passa a Commerce Starter"
2. Conferma

**Backend atteso (post Onda 9.K)**:
- Stripe modify, `commercial_plan_slug: "core"`
- Starter ha `stores_max: 1`, già 3 store attivi → reconcile deactivates 2 newest non-default
- Default rimane attivo (1° creato durante signup)
- Storefront: solo lo store default è raggiungibile pubblicamente

**Frontend atteso**:
- 2 card su /stores con badge amber + banner upgrade CTA
- Sidebar nav: voci commerce restano (Starter ha commerce attivo, solo limit ridotto)
- Tentativo di creare 4° store → 429 `QUOTA_EXCEEDED` con `feature_key:"stores_max"` (vedi MOD-04)
- Editing dei 2 store deattivati: ancora permesso (no API guard sull'edit) — l'admin può modificarne i dati anche da deattivati

**Pass se**: 1 store rimane visibile (default), 2 nascosti ma editabili.

---

### 🟢 PLN-04 — Free → direct subscribe a Commerce Pro (no trial perché usato)

**Pre**: `org_free_trialed` (`has_used_trial=true`).

**Steps**:
1. /plans → "Abbonati" su Commerce Pro
2. Stripe Checkout NON deve mostrare "14-day free trial" — deve mostrare addebito immediato

**Backend atteso**:
- `create_checkout_session` con `subscription_data.trial_period_days=null` o assente
- Stripe Checkout in modalità "subscribe immediately"

**Pass se**: Stripe Checkout mostra "Pay €79 today" (no trial). Vedi anche TRL-01.

---

## C. Module access enforcement (MOD)

### 🔴 MOD-01 — Solo user prova ad accedere a /commerce via URL

**Pre**: `org_solo_active`.

**Steps**:
1. Login come admin Solo
2. Verifica sidebar: NON deve esserci voce "Stores", "Orders", "Calendar"
3. Forza nell'URL: `/stores` (digita a mano)
4. Cosa vede l'utente?

**Backend atteso**:
- Frontend chiama `GET /api/stores` → backend non blocca a livello list (probabilmente)
- Se l'utente prova `POST /api/stores` (creare store) → backend chiama `check_module_access('commerce', 'stores_max')` con `pending_quantity=1`
- Solo ha `commerce_disabled` con `stores_max: 0`. Limite=0 → 403 con `code:"FEATURE_NOT_AVAILABLE"`

**Frontend atteso (current state — POTENZIALMENTE BUGGY)**:
- ⚠️ Il frontend NON ha handler per `FEATURE_NOT_AVAILABLE`
- Risultato: errore axios generico, toast "Network error" o "Errore" senza spiegazione
- L'utente non capisce CHE deve fare upgrade per usare la feature

**Pass se**:
- Sidebar non mostra commerce ✓ (questo OK)
- Pagina `/stores` accessibile direttamente ma vuota / con messaggio "Non disponibile sul tuo piano" + CTA "Aggiorna piano"
- POST risponde con messaggio chiaro + suggerimento upgrade

**⚠ Gap noto**: serve aggiungere handler frontend per `MODULE_NOT_AVAILABLE` e `FEATURE_NOT_AVAILABLE` (vedi sezione finale "UX gaps").

---

### 🔴 MOD-02 — Free user prova ad attivare AI Chat oltre 3 messaggi

**Pre**: `org_free_fresh` con 3 messaggi AI già consumati.

**Steps**:
1. Vai su una pagina con AI chat (Dashboard insights)
2. Manda un 4° messaggio

**Backend atteso**:
- POST `/api/ai/chat` → `check_module_access('ai_assistant', 'chat')` con usage=3, limit=3, pending=1
- 3+1 > 3 → 429 `code:"QUOTA_EXCEEDED"` `message:"Quota mensile chat esaurita (3/3). Aggiorna il piano per continuare."`

**Frontend atteso**:
- ✅ Axios interceptor cattura `QUOTA_EXCEEDED` → mostra paywall modal `<UpgradePaywall>` con CTA "Vedi piani"
- Modal è in lingua dell'admin (it/en/de/fr)

**Pass se**: paywall si apre, click su CTA va a /plans, no errore generico in console.

---

### 🟢 MOD-03 — Past_due grace period (read-only)

**Pre**: `org_starter_pastdue` (pagamento fallito da 3 giorni). Il sistema mette in
"read_only" dopo 7 giorni di past_due. Per testare subito: in MongoDB
`db.organizations.updateOne({id:..}, {$set:{billing_status:"past_due", past_due_since: <8gg fa>}})`

**Steps**:
1. Login come admin
2. Prova a fare un'azione di scrittura (creare prodotto, ordine, alert config)

**Backend atteso**:
- `_check_billing_gate` rileva past_due > 7gg → entitlements.read_only = true
- Endpoint write → 403 `code:"READ_ONLY_GRACE"`

**Frontend atteso**:
- ✅ Axios interceptor (`api/client.js`) cattura READ_ONLY_GRACE → emette evento custom
- `<ReadOnlyGraceBanner>` appare in cima a tutte le pagine
- Letture (GET) funzionano, scritture bloccate

**Pass se**: banner visibile, scritture bloccate con messaggio chiaro, link a "Aggiorna piano" o "Aggiorna metodo pagamento".

---

### 🟢 MOD-04 — Downgrade-then-write: store create dopo Pro → Solo

**Pre**: `org_pro_active` → fai PLN-02 → ora è Solo con 3 store ancora esistenti.

**Steps**:
1. Vai a `/stores` (URL diretto, non in sidebar)
2. Prova a creare un nuovo store

**Backend atteso**:
- POST `/api/stores` → `check_module_access('commerce', 'stores_max')`
- Solo ha `stores_max=0`, già 3 esistono → 429 `code:"stores_max_reached"`

**Frontend atteso**:
- ⚠️ `code:"stores_max_reached"` NON è `QUOTA_EXCEEDED` standard → l'interceptor in `api/client.js` non lo riconosce
- Mostra errore generico

**Gap noto**: stores.py usa `code:"stores_max_reached"` ma il resto del sistema usa `QUOTA_EXCEEDED`. **Standardizzare** prima del go-live.

---

## D. Quota limits (QTA)

### 🔴 QTA-01 — Hit ordini mensili su Commerce Starter (200/mese)

**Pre**: `org_starter_active`. In MongoDB inserisci 200 usage events:
```js
for (let i=0; i<200; i++) {
  db.usage_events.insertOne({organization_id:"<id>", module_key:"commerce", feature_key:"orders_monthly", consumed_at: new Date(), quantity:1});
}
```

**Steps A (warning a 80%)**:
1. Trigger manuale `quota_warning_sweep`: `python -c "import asyncio; from services.background_service import _quota_warning_sweep_job; asyncio.run(_quota_warning_sweep_job())"`

**Backend atteso**:
- Email "Stai per raggiungere il limite ordini" in lingua admin
- Insert in `org_quota_notices` con `level:"warn_80"`

**Steps B (exceeded)**:
2. Crea 1 ordine in più (POST /api/orders)
3. Verifica risposta

**Backend atteso**:
- POST /api/orders → 429 `QUOTA_EXCEEDED` con `feature_key:"orders_monthly"`

**Frontend atteso**:
- `<QuotaExceededBanner>` o paywall modal
- Suggerimento "Aggiorna a Pro" o "Acquista pack +200 ordini"

**Pass se**: 80% email arriva, exceeded blocca con UI chiara, addon `+200 ordini` quando comprato sblocca subito.

---

### 🔴 QTA-02 — Hit stores_max su Commerce Pro (3/3)

**Pre**: `org_pro_active` con 3 store già attivi.

**Steps**:
1. Vai a `/stores`
2. Click "+ Nuovo store"
3. Compila form, salva

**Backend atteso**:
- POST `/api/stores` → 429 `code:"stores_max_reached"` con messaggio italiano

**Frontend atteso**:
- ⚠️ Vedi MOD-04 — gap UX

**Pass se**: messaggio chiaro che dice "Hai 3/3 store, acquista +1 store o contatta supporto".

---

### 🟢 QTA-03 — Buy +1 store addon → limite sale → riprovo

**Pre**: `org_pro_with_addons` (già ha +1 store).

**Steps**:
1. Verifica limite reale: GET `/api/billing/usage-summary` → `stores_max.effective_limit` deve essere 4 (3 base + 1 addon)
2. Crea il 4° store

**Backend atteso**:
- 200 OK, store creato

**Pass se**: lo store viene creato. Verifica effective_limit risponde correttamente.

---

### 🟢 QTA-04 — Stack add-on (3× +50 AI chat → +150 chat)

**Pre**: `org_starter_active`. Compra 3× addon_ai_chat_pack via /plans#addons.

**Steps**:
1. Verifica `effective_limit('ai_assistant', 'chat')` = 80 + 150 = 230
2. Consuma 230 chat
3. La 231° → 429 QUOTA_EXCEEDED

**Pass se**: stacking funziona, blocco corretto al 231°.

**Edge case da verificare**: comprare 6° pack quando max_quantity=5 → backend rifiuta con `code:"max_quantity_exceeded"`.

---

### 🟢 QTA-05 — Reset quota a inizio mese

**Pre**: org con quota esaurita questo mese.

**Steps**:
1. Fast-forward al 1° del mese successivo (manipolare `period_start` in MongoDB o aspettare)
2. Riprova l'azione bloccata

**Pass se**: usage counter riparte da 0, l'azione passa.

---

## E. Add-ons (ADO)

### 🔴 ADO-01 — Free user prova a comprare addon

**Pre**: `org_free_fresh`.

**Steps**:
1. /plans#addons → click "+ Aggiungi" su +50 AI chat

**Backend atteso**:
- POST `/api/billing/add-addon` → 400 `code:"plan_required"`
- Messaggio: "Add-ons richiedono un piano a pagamento. Sottoscrivi un piano prima."

**Frontend atteso**:
- Card addon ha già il bottone disabilitato per Free (UX preventiva)
- Se viene chiamato comunque, l'alert mostra il messaggio backend

**Pass se**: bottone disabilitato + tooltip "Disponibile dai piani a pagamento".

---

### 🟢 ADO-02 — Solo user prova a comprare +1 store (incompatibile)

**Pre**: `org_solo_active`. L'addon `addon_extra_store` ha `compatible_plans:["pro"]`.

**Steps**:
1. /plans#addons → tenta "+ Aggiungi" su +1 store

**Backend atteso**:
- 400 `code:"incompatible_plan"` con `compatible_plans:["pro"]`

**Frontend atteso**:
- Bottone disabilitato con tooltip "Richiede: Commerce Pro"

**Pass se**: l'utente capisce DAVANTI all'azione che l'addon serve un upgrade.

---

### 🟢 ADO-03 — Buy addon → cancel base sub → addon cancellato

**Pre**: `org_starter_active` con +50 AI chat attivo.

**Steps**:
1. Cancella sub immediata (SUB-05)

**Backend atteso**:
- Stripe webhook `customer.subscription.deleted`
- `cancel_all_addons_by_stripe_sub()` chiamato → tutti gli addon → status="cancelled"

**Frontend atteso**:
- /settings → BillingSection → "Add-on attivi" è vuoto

**Pass se**: nessun addon orfano in DB.

---

### 🟢 ADO-04 — Admin custom override (no Stripe)

**Pre**: `org_solo_active`. Login come system_admin.

**Steps**:
1. /admin → Organizations → apri `org_solo_active`
2. Tab "Add-ons" → assegna +50 AI chat con reason "Test ADO-04"

**Backend atteso**:
- POST `/api/admin/organizations/{id}/addons` → addon row con `is_custom_override:true`, `assigned_by:"system_admin:<id>"`
- Stripe NON tocca

**Frontend atteso**:
- Lista active addons mostra il nuovo con badge viola "custom override"
- L'utente Solo (logout/login) vede il +50 chat nella sua /settings BillingSection

**Pass se**: chat AI limit di Solo passa da 20 a 70 senza Stripe.

---

## F. Trial policy (TRL)

### 🔴 TRL-01 — Trial usato → no second trial su altro piano

**Critico**: l'utente ha esplicitamente chiesto di garantire questo.

**Pre**: `org_free_trialed` (già usato 14gg trial Solo, poi caduto a Free).

**Steps**:
1. /plans → click "Inizia prova gratis 14 giorni" su Commerce Starter
2. Verifica Stripe Checkout

**Backend atteso**:
- `create_checkout_session` deve detectare `has_used_trial=true`
- Trial deve essere SKIPPATO (subscription_data.trial_period_days non settato)

**Stripe atteso**:
- Checkout mostra "Pay €39 today" (no "14-day free trial")
- Subscription creata con `trial_end:null`

**Frontend atteso**:
- Bottone su /plans dovrebbe già mostrare "Abbonati" invece di "Prova gratis 14 giorni"

**Pass se**: NESSUNA seconda prova gratuita possibile, indipendentemente dal piano scelto.

**⚠ Failure indicator critico**: se Stripe mostra "trial 14 days" la seconda volta, è un BUG da fixare prima del go-live (frode preventiva).

---

### 🟢 TRL-02 — Trial cancellato a giorno 7 → nuovo abbonamento giorno 30

**Pre**: org che ha avuto trial 14gg poi cancellato a giorno 7.

**Steps**:
1. Aspettare 30 giorni (o forzare)
2. Riprovare subscribe

**Pass se**: come TRL-01, no nuovo trial.

---

### 🟢 TRL-03 — Trial estesa da admin → comportamento Stripe

**Pre**: `org_solo_trial` giorno 13 (1 giorno alla scadenza).

**Steps**:
1. Login system_admin → /admin → org → "Extend Trial" → +30 giorni, reason "Beta partner"

**Backend atteso**:
- `trial_ends_at` posticipato di 30gg in MongoDB
- Stripe trial NON viene esteso (lo dice il codice — backend gate locale skippa past_due)

**Da verificare**:
- Se Stripe trial scade prima → tenta di addebitare? In test mode con carta valida → addebita normalmente
- L'utente continua ad avere accesso? Sì, per il backend gate locale

**Pass se**: utente conserva accesso anche dopo scadenza Stripe trial.

---

## G. Edge cases & race conditions (EDG)

### 🟢 EDG-01 — Webhook in ritardo → verify-checkout fallback

**Pre**: stop temporaneamente il webhook listener (oppure simula con Stripe CLI).

**Steps**:
1. Completa Stripe Checkout
2. Webhook NON arriva entro 16 secondi
3. Frontend chiama `verify-checkout` automaticamente

**Backend atteso**:
- POST `/api/billing/verify-checkout {session_id:"..."}` → backend chiama Stripe API direttamente, recupera la sub, provisiona localmente
- Risposta `status:"provisioned"`

**Frontend atteso**:
- Toast di successo
- BillingSection riflette il nuovo piano

**Pass se**: l'utente non vede mai "stuck pending" oltre 30s.

---

### 🟢 EDG-02 — Doppio click su Subscribe

**Pre**: `org_free_fresh`.

**Steps**:
1. /plans → click "Abbonati" velocemente 2 volte

**Atteso**:
- Solo 1 checkout session creata (frontend disabilita il bottone con `loadingSlug`)
- Anche se backend riceve 2 chiamate, `BillingEvent.stripe_event_id` unique index garantisce idempotenza webhook

**Pass se**: 1 sub creata, no duplicati in `customer.subscriptions` Stripe.

---

### 🟢 EDG-03 — Pagamento fallito durante trial → past_due

**Pre**: `org_solo_trial` con carta `4000 0000 0000 0002` (declined).

**Steps**:
1. Aspetta che Stripe attivi la sub a fine trial
2. Pagamento fallisce
3. Webhook `invoice.payment_failed`

**Backend atteso**:
- `billing_status: "past_due"`
- Email "Pagamento fallito, aggiorna metodo di pagamento" inviata

**Frontend atteso**:
- Banner past_due in /settings
- BillingSection mostra status "past_due"

**Pass se**: l'utente capisce subito che deve aggiornare la carta.

---

### 🟢 EDG-04 — Concurrent webhook delivery

Stripe può consegnare lo stesso webhook più volte.

**Steps**:
1. Dal Stripe Dashboard → Events → seleziona un evento → "Resend"

**Backend atteso**:
- 2° delivery → `BillingEvent.stripe_event_id` unique violation → handler skippa idempotente
- Nessun side effect duplicato

**Pass se**: log mostra "duplicate event ignored" senza errori.

---

## H. UX message clarity (UXM) — il cuore della preoccupazione utente

### 🔴 UXM-01 — Audit dei codici errore — STATO POST-FIX (Onda 9.I)

| Backend code | HTTP | Frontend handler | UX risultante |
|---|---|---|---|
| `QUOTA_EXCEEDED` | 429 | ✅ axios interceptor + `<QuotaExceededBanner>` + `<UpgradePaywall>` | Modal chiaro |
| `READ_ONLY_GRACE` | 403 | ✅ banner via interceptor | Banner top |
| `MODULE_NOT_AVAILABLE` | 403 | ✅ **FIXED 9.I** — `<ModuleAccessPaywall>` modal | Modal con CTA "Vedi piani" |
| `FEATURE_NOT_AVAILABLE` | 403 | ✅ **FIXED 9.I** — `<ModuleAccessPaywall>` modal | Modal con CTA "Vedi piani" |
| `BILLING_TRIAL_EXPIRED` | 403 | ✅ `<BillingStatusBanner>` (già esisteva, era stato dimenticato) | Banner persistente |
| `BILLING_PAST_DUE` | 403 | ✅ `<BillingStatusBanner>` | Banner persistente |
| `stores_max_reached` | 429 | ✅ **FIXED 9.I** — rinominato `QUOTA_EXCEEDED` in stores.py | Modal chiaro |
| `plan_required` (addon) | 400 | ✅ alert custom in PlansAddonsSection | OK |
| `incompatible_plan` (addon) | 400 | ✅ tooltip preventivo | OK |
| `max_quantity_exceeded` | 400 | ⚠ alert generico (semantica addon-purchase, non quota) | Mediocre — accettabile |
| `orders_quota_exceeded` (storefront customer) | 429 | n/a — audience diversa (end customer storefront, non admin) | n/a |

**Tutti i gap UX critici sono stati risolti in Onda 9.I.** Resta solo:

- ⚠ `max_quantity_exceeded` (tentativo di comprare 6° pack quando max=5) — alert generico ma scenario raro e non bloccante. Documentato come "known limitation".
- ⚠ Downgrade Pro→Solo con store eccedenti (PLN-02/PLN-03) — necessita decisione di policy:
  - Opzione A: bloccare downgrade se in violation
  - Opzione B: permettere downgrade ma flag store eccedenti come "disabilitati"
  - Da decidere prima del go-live.

---

### 🔴 UXM-02 — Sidebar nav coerenza con piano

Per ogni piano, verificare la nav sidebar:

| Plan | Voci visibili attese | Voci NON visibili |
|---|---|---|
| Free | Dashboard, KPI base, AI chat (con paywall a 3/mese) | Stores, Orders, Reservations, Calendar |
| Solo | Dashboard, Cashflow full, Reports, AI chat | Stores, Orders, Reservations, Calendar (commerce_disabled) |
| Commerce Starter | + Stores (1), Orders, Calendar | (3rd store visibile ma create-disabled) |
| Commerce Pro | + Stores (3) | — |

**Pass se**: NON ci sono voci di nav che portano a 403 silenziosi.

---

### 🟢 UXM-03 — Linguaggio coerente: "negozio" vs "store" vs "vetrina"

L'utente ha già flagged questa cosa.

**Verifica**: tutti i punti UI usano lo stesso termine. Comando per cercare:
```bash
grep -rn "shop\|store\|vetrin\|negozi" frontend/src/locales/it/*.json | grep -v node_modules
```

**Pass se**: usa SEMPRE "Negozi online" (o un sinonimo unico) — niente mix.

---

### 🟢 UXM-04 — CTA "Aggiorna piano" sempre 1-click da blocco

In ogni paywall / modal di blocco, il CTA primario deve portare direttamente a /plans (non a Stripe Customer Portal, non a una helpdesk page).

**Pass se**: ogni blocco ha CTA → `/plans` (o `/plans#addons` se contestualmente add-on suggerito).

---

## I. Multi-language (I18N)

### 🟢 I18N-01 — Quota emails in 4 lingue

**Pre**: 4 org diverse con `account.locale ∈ {it, en, de, fr}`. Trigger quota_warning_sweep su tutte.

**Pass se**: ogni admin riceve email nella propria lingua, contenuto coerente con quota_email_service.py i18n keys.

---

### 🟢 I18N-02 — UI billing in 4 lingue

**Steps**:
1. Login con admin di lingua `de` → /plans, /settings → Billing
2. Tutto deve essere in tedesco (no fallback IT/EN visibili)

**Pass se**: nessuna stringa raw del tipo `billing.matrix.row.orders_monthly` o `billing.cancel_modal_title` visibile.

---

### 🟢 I18N-03 — Stripe Checkout localizzato

Stripe rispetta automaticamente la lingua del browser, ma possiamo forzarla via `locale` parameter in checkout-session.

**Verifica**: utenti DE vedono Stripe Checkout in tedesco? È nice-to-have, non bloccante.

---

## J. Admin scenarios (ADM)

### 🟢 ADM-01 — Custom plan creation

Già coperto in `BILLING_V58_NEW_PLANS_TESTING_RUNBOOK.md` scenario AA. Riconfermare.

### 🟢 ADM-02 — Trial extension

Coperto in BB. Riconfermare.

### 🟢 ADM-03 — MRR dashboard

`/admin → Billing tab` → verifica:
- MRR current = somma price_monthly delle sub attive + addon
- mrr_by_plan breakdown
- mrr_by_addon breakdown
- churn_30d count
- upsell_candidates list

**Pass se**: numeri quadrati con quanto vedi in Stripe Dashboard.

---

## K. Cleanup matrix (per ripristinare stato tra test)

| Sezione | Reset command |
|---|---|
| SUB-01..05 | `python backend/scripts/seed_test_orgs.py --reset` |
| QTA-01..05 | `db.usage_events.deleteMany({organization_id:"<orgid>"})` + `db.org_quota_notices.deleteMany({organization_id:"<orgid>"})` |
| ADO-01..04 | `db.addon_subscriptions.deleteMany({organization_id:"<orgid>"})` + Stripe.Subscription.modify(items=[main_only]) |
| TRL-01..03 | `db.organizations.updateOne({id:"<orgid>"}, {$set:{has_used_trial:false, trial_ends_at:null}})` + Stripe customer reset |
| EDG-01 | restart webhook listener |

---

## L. Go/No-Go criteria pre-deploy

### Bloccanti (devono passare TUTTI)
- [ ] SUB-01, SUB-02, SUB-03, SUB-04, SUB-05
- [ ] PLN-01, PLN-02
- [ ] MOD-01, MOD-02
- [ ] QTA-01, QTA-02
- [ ] ADO-01
- [ ] TRL-01 (critico)

### Importanti (≥90% deve passare)
- [ ] PLN-03, PLN-04
- [ ] MOD-03, MOD-04
- [ ] QTA-03, QTA-04, QTA-05
- [ ] ADO-02..04
- [ ] TRL-02, TRL-03
- [ ] UXM-01..04
- [ ] EDG-01..04
- [ ] I18N-01..02

### Strategic repositioning — Onda 9.N (cashflow-first ladder)

**Contesto**: production data ha rivelato che tutti gli utenti attuali sono cashflow-only. Il vecchio Free aveva un demo commerce (30 contact requests, 1 store, 50 prodotti) che creava un'incoerenza nella value ladder: Solo (€19) **perdeva** features commerce vs Free. Strategia: Free + Solo diventano **pure cashflow plans**, commerce inizia a Commerce Starter (€39).

**Cambi DB applicati via `migrate_cashflow_first_repositioning.py`**:
- Free: `commerce_free` → `commerce_disabled`, `product_catalog_free` → `product_catalog_disabled`
- Solo: `product_catalog_free` → `product_catalog_disabled`
- Tagline + features_display aggiornati su entrambi
- 1 org production reprovisionata (no impact: nessun utente prod usava commerce)

**Nuova ladder verificata coerente** (audit script):
| Tier | Cashflow | AI | Commerce | Products | Team |
|---|---|---|---|---|---|
| Free €0 | basic, 200 rows, 3 chat | — | ❌ 0 | ❌ 0 | 1 |
| Solo €19 | full, 1000 rows, 20 chat, alerts, digest KPI, export | — | ❌ 0 | ❌ 0 | 2 |
| Commerce Starter €39 | unlimited, 80 chat, 4 digest, AI alerts/health | 200 ord, 1 store, Stripe | 200 | 5 |
| Commerce Pro €79 | + 200 chat, ∞ digest | 1000 ord, 3 store | ∞ | 15 |
| Custom €199 | ∞ tutto | ∞ tutto | ∞ | ∞ |

**Migration risk**: ZERO (nessun utente prod commerce). Stripe IDs invariati. Stripe Products invariati. Frontend matrix card auto-aggiornata via PLAN_MATRIX_SECTIONS values.

**Ladder principle**: ogni piano è un **superset rigoroso** del precedente. Mai regressioni.

---

### UX gaps — STATO POST-FIX (Onda 9.I + 9.K + 9.L)
- [x] ✅ Aggiungere axios handler per `MODULE_NOT_AVAILABLE` (fixed in `api/client.js`)
- [x] ✅ Aggiungere axios handler per `FEATURE_NOT_AVAILABLE` (fixed in `api/client.js`)
- [x] ✅ Standardizzare `stores_max_reached` → `QUOTA_EXCEEDED` (fixed in `routers/stores.py`)
- [x] ✅ Verificare handler `BILLING_TRIAL_EXPIRED` / `BILLING_PAST_DUE` (già esistono in `BillingStatusBanner`)
- [x] ✅ Mount `<ModuleAccessPaywall>` in App.js root
- [x] ✅ i18n keys `module_paywall.*` aggiunte in 4 locale
- [x] ✅ **Onda 9.K**: policy downgrade-with-violation implementata (Option B):
  - `reconcile_stores_to_plan_limit()` in `services/plan_provisioning.py`
  - Auto-deactivate overflow stores (newest first, default protected)
  - Auto-reactivate on plan upgrade (FIFO: longest-deactivated first)
  - Frontend: badge amber + banner upgrade CTA in `StoresPage.js`
  - i18n: `plan_violation.*` in 4 locale (it/en/de/fr)
- [x] ✅ **Onda 9.L** — Closed silent quota bypasses + standardized team error:
  - **Products catalog limit** ora enforced in `routers/products.py` POST + duplicate, `routers/event_occurrences.py`, `routers/courses.py` (4 path)
  - **Orders monthly limit** ora enforced anche su `routers/orders.py` POST (admin manual orders)
  - **Team limit** convertito da plain-string 403 a coded 429 (`code: "QUOTA_EXCEEDED"`, `feature_key: "team_members"`) → ora il `<UpgradePaywall>` esistente lo cattura
  - Helper centralizzato `enforce_count_quota()` in `services/module_access.py` per limiti snapshot-style (counts vs monthly events)
  - Tutti i raise 429 ora portano `addon_slug` quando applicabile (es. orders → `addon_orders_pack`) per CTA "+200 ordini" nel paywall

**Tutti i gap UX critici sono risolti. Il sistema è pronto per i test holistici.**

### Nice-to-have (non bloccanti)
- [ ] I18N-03 (Stripe Checkout localizzato)
- [ ] ADM-01..03 (già testati in runbook precedente)

---

## M. Note finali

**Quanto tempo richiede l'esecuzione**: stimato 4-6 ore per un QA che esegue
manualmente tutti gli scenari bloccanti + importanti, partendo da DB pulito.
Le sezioni A-D + F sono critiche; H è il cuore della concern utente
("è chiaro perché sono bloccato e cosa devo fare?").

**Cosa fare con i fail**: ogni fallimento va loggato come issue con:
- Scenario ID (es. SUB-03)
- HTTP response (status + detail body)
- Browser console snapshot
- Stripe Dashboard event link
- DB state snippet

Le issue vengono triagiate prima del deploy: le bloccanti devono essere fixate,
le importanti possono essere documentate come "known limitation" se non ci sta
nei tempi.
