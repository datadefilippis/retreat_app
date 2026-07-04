# Subscription System Consolidation Plan — Onda 10

**Status**: PLANNING. Implementation requires explicit user approval per phase.
**Owner**: Subscription system holistic owner (Claude + Davide)
**Goal**: rendere il sistema abbonamento-alert-mantenimento **dinamicamente reattivo, scalabile, sicuro, e gestibile in self-serve dal system admin** — basato sui findings dell'audit forense del 2026-05-01.

---

## 0. Principi guida

| Principio | Cosa significa per ogni step |
|---|---|
| **Validabile** | Ogni step ha un test deterministico (script o procedura UI). Pass/fail prima di passare allo step successivo. |
| **Isolato** | 1 commit per step. Git-revert sicuro. Nessuna dipendenza cross-step se non esplicitata. |
| **Idempotente** | Migrazioni/seed re-eseguibili senza side effect. |
| **Backward-compatible** | Zero API breaking. Endpoint esistenti continuano a funzionare. |
| **Reversibile** | Ogni step ha un rollback documentato. |
| **DB-driven** | Niente nuovi hardcoded. Ogni nuova quota/feature/limit vive nel DB. |
| **Audit-traced** | Ogni mutazione admin lascia traccia in `catalog_audit_log` o `audit_logs`. |

---

## 1. Visione architetturale post-Onda 10

```
┌─────────────────────────────────────────────────────────────┐
│  System Admin                                                │
│   ↓                                                          │
│  Pannello /admin/catalog (UI)                                │
│   ├── Edit tier limits (già OK)                              │
│   ├── Edit plan metadata (già OK)                            │
│   ├── Edit pricing + Stripe sync (NEW: auto-validate)        │
│   ├── Create new plan (NEW)                                  │
│   ├── Create new tier (NEW)                                  │
│   ├── Create new addon (NEW + auto-Stripe)                   │
│   ├── Bulk actions (NEW: filter+action)                      │
│   └── Drift overview (cron-driven NEW)                       │
└─────────────────────────────────────────────────────────────┘
                          ↓ (PATCH/POST)
┌─────────────────────────────────────────────────────────────┐
│  /api/admin/catalog/* — extended                             │
│   ├── PATCH limits/metadata/pricing (esistenti)              │
│   ├── POST plans / tiers / addons (NEW)                      │
│   ├── DELETE soft (is_archived flag) (NEW)                   │
│   └── Stripe API integration server-side (NEW)               │
└─────────────────────────────────────────────────────────────┘
                          ↓ (write)
┌─────────────────────────────────────────────────────────────┐
│  MongoDB collections (single source of truth)                │
│   ├── pricing_plans (limits per modulo, EXTENDED)            │
│   ├── commercial_plans (bundle commerciale, EXTENDED)        │
│   │     · adds: chat_session_ttl_days,                       │
│   │             team_members_limit,                          │
│   │             addon_ctas: {feature: addon_slug},           │
│   │             hard_abuse_caps: {feature: int}              │
│   ├── module_subscriptions (org → tier, FK only)             │
│   ├── addon_subscriptions (org → addon, qty)                 │
│   └── catalog_audit_log (immutable history)                  │
└─────────────────────────────────────────────────────────────┘
                          ↓ (read, no cache)
┌─────────────────────────────────────────────────────────────┐
│  Backend gates (module_access.py)                            │
│   ├── check_module_access (esistente)                        │
│   ├── enforce_count_quota (esistente)                        │
│   ├── enforce_team_member_quota (NEW, ex hardcoded)          │
│   └── get_chat_ttl(plan) (NEW, ex hardcoded)                 │
└─────────────────────────────────────────────────────────────┘
                          ↓ (HTTP)
┌─────────────────────────────────────────────────────────────┐
│  Frontend hooks (live, dinamici)                             │
│   ├── useEntitlements (NEW: 60s polling + focus refresh)     │
│   ├── useBilling.plans (NEW: focus refresh)                  │
│   └── i18n parametriche {{limit}} (NEW)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Fasi del piano (6 fasi sequenziali)

| Fase | Tema | Step interni | Effort | Bloccante per scenario "admin alza quota → utente la vede"? |
|---|---|---|---|---|
| **A** | Adattabilità dinamica frontend (P0) | 4 | 4-5h | **SÌ — la fase critica** |
| **B** | Catalog completo (eliminazione hardcoded) | 5 | 6-8h | No, ma sblocca creazione plan/addon |
| **C** | System admin self-serve (create new entities) | 6 | 14-18h | No, ma è il pilastro di scalabilità |
| **D** | Sicurezza e robustezza | 4 | 6-8h | No |
| **E** | Monitoring e observability | 3 | 5-6h | No |
| **F** | UX gap residui + cleanup | 5 | 4-5h | No |

**Totale stimato: 39-50 ore** spalmate in ~20-25 commit indipendenti.

**Minimum viable per il tuo caso d'uso**: solo Fase A (~5h) sblocca la propagazione live.

---

## 3. FASE A — Adattabilità dinamica frontend (P0)

**Obiettivo**: quando system admin modifica una quota, gli utenti già loggati vedono il cambio entro 60 secondi (o al primo focus della finestra).

### Step A.1 — `useEntitlements` polling + focus refresh

**File**: `frontend/src/hooks/useEntitlements.js`

**Cambio**:
- Aggiungere `useEffect` con `setInterval(refresh, 60_000)` cleared on unmount
- Aggiungere `window.addEventListener('focus', refresh)` cleared on unmount
- Stessa logica di `PlanIndicator.jsx:34-50` (già implementata, da copiare)

**Acceptance criteria**:
1. Apri `/cashflow` come Free user a `data_rows: 0/200`
2. Su altro terminale: `db.pricing_plans.updateOne({slug:"cashflow_monitor_free"}, {$set:{"limits.data_rows":500}})`
3. Senza ricaricare la pagina, entro 60 sec il dashboard mostra `0/500`
4. Click sul tab → focus refresh anticipa il polling

**Validation procedure**:
```bash
# Console DevTools post-modifica DB
window.dispatchEvent(new Event('focus'))  # forza refresh manuale
# Aspetta 1s, poi verifica che fetch /api/billing/usage-summary sia chiamato
```

**Rollback**: revert del file, ~4 righe.

**Effort**: 30 min.

---

### Step A.2 — `useBilling.plans` focus refresh

**File**: `frontend/src/hooks/useBilling.js`

**Cambio**: stesso pattern di A.1 — focus listener (no polling per `plans` perché meno frequente del cambio).

**Acceptance criteria**:
1. PATCH metadata di un plan via `/admin/catalog/plans/starter`
2. Utente già loggato torna sulla pagina → focus event → vede metadata aggiornata in PlansPage

**Effort**: 20 min.

---

### Step A.3 — i18n parametriche per feature_display labels

**File**: `frontend/src/locales/{it,en,de,fr}/settings.json` + `frontend/src/components/UpgradeDialog.js`, `pages/PlansPage.js`

**Cambio**:
- Sostituire `data_rows_200`, `data_rows_1000`, ... con UN'UNICA chiave `data_rows` con interpolazione `{{limit}}`
- Stesso per `commerce_NNN_orders`, `ai_chat_NNN`, `products_NNN`
- Backend `features_display` array continua a contenere stringhe arbitrarie (es. `"data_rows:500"`), il frontend parsa il pattern e applica i18n con `t('feature.data_rows', { limit: 500 })`

**Schema decisionale**: `features_display` nel CommercialPlan diventa array di oggetti `{key, params}` invece di stringhe magic-string. Es:
```json
[
  {"key": "data_rows", "params": {"limit": 500}},
  {"key": "checkout_stripe", "params": {}},
  {"key": "stores_max", "params": {"limit": 3}}
]
```

**Migration**: script `scripts/migrate_features_display_to_structured.py` che converte il legacy array di stringhe nel nuovo shape. Idempotente.

**Acceptance criteria**:
1. Admin cambia `data_rows` Solo da 1000 a 7777
2. Edita `features_display[0]` di Solo CommercialPlan a `{"key":"data_rows","params":{"limit":7777}}`
3. PlansPage mostra `7777 righe dati / mese` in 4 locale, non la stringa raw `data_rows_7777`

**Effort**: 3h (incluso refactor frontend rendering).

---

### Step A.4 — Test E2E validazione FASE A

**File**: nuovo `backend/scripts/test_dynamic_quota_propagation.py`

**Scenari**:
1. Login user → fetch `/usage-summary` → assert `limit==X`
2. PATCH tier limits → `limit=Y`
3. Login NON re-fatto. Wait 65s.
4. Re-fetch `/usage-summary` (simula focus refresh) → assert `limit==Y`

**Effort**: 1h.

**Approval gate Fase A**: Davide testa manualmente lo scenario nel browser. Conferma → si passa a Fase B.

---

## 4. FASE B — Eliminazione hardcoded fuori catalog

**Obiettivo**: portare TUTTI i limiti/configurazioni nel catalog DB-driven. Aggiungere un nuovo plan slug (es. "growth") deve essere zero-deploy.

### Step B.1 — `_TEAM_LIMITS` → catalog feature_key

**File**: `backend/services/seed_pricing.py` + `backend/routers/organizations.py:1246` + `backend/routers/billing.py:238`

**Cambio**:
- Aggiungere `team_members` come feature_key in un nuovo modulo `team` (o riutilizzando `cashflow_monitor`):
  ```python
  "team_members": 1   # free
  "team_members": 2   # starter
  ```
- Refactor `routers/organizations.py:1252` per usare `get_effective_limit(org_id, "team", "team_members")` invece del dict hardcoded
- Stesso in `routers/billing.py:238` (dashboard mostra il limit)
- Eliminare `_TEAM_LIMITS` da entrambi i file

**Migration**: script `scripts/migrate_team_limits_to_catalog.py` che inserisce le entry `team_members` in tutti i tier `cashflow_monitor_*` esistenti.

**Acceptance criteria**:
1. Admin alza `team_members` Solo da 2 a 5 via PATCH limits
2. Org Solo immediatamente può invitare 5 membri (non più 2)
3. Dashboard `BillingUsageDashboard` mostra `2/5` invece di `2/2`
4. Nessun hit su `_TEAM_LIMITS` (verificato con grep post-deploy)

**Effort**: 1.5h.

---

### Step B.2 — `_PLAN_TTL_DAYS` → CommercialPlan field

**File**: `backend/models/commercial_plan.py` + `backend/services/chat_service.py:27`

**Cambio**:
- Aggiungere campo `chat_session_ttl_days: Optional[int] = None` a `CommercialPlan`
- Seed con valori storici (free=7, starter=30, ...)
- `chat_service.py:get_ttl_for_plan(slug)` legge da DB invece di dict hardcoded

**Acceptance criteria**:
1. PATCH `commercial_plans/starter` con `chat_session_ttl_days: 60`
2. Org Solo: nuova chat session creata oggi expire fra 60 giorni invece di 30

**Effort**: 1h.

---

### Step B.3 — `VALID_COMMERCIAL_PLANS` whitelist → DB validation

**File**: `backend/models/admin.py:144` + `backend/routers/admin.py:1052`

**Cambio**:
- Eliminare il frozenset hardcoded
- `admin_set_commercial_plan` valida con `commercial_plans_collection.find_one({slug: ...})`
- Se non trova → 400 "Unknown plan slug"

**Acceptance criteria**:
1. Crea via Mongo (manualmente per ora) un nuovo plan slug "growth"
2. PUT `/admin/organizations/{id}/commercial-plan` con `slug=growth` → 200 OK
3. Pre-fix: stesso request → 400 perché "growth" non in frozenset

**Effort**: 1h.

---

### Step B.4 — `METRIC_TO_ADDON_OFFER` → CommercialPlan campo

**File**: `backend/services/quota_email_service.py:69` + `backend/models/commercial_plan.py`

**Cambio**:
- Aggiungere `addon_ctas: Dict[str, str]` su CommercialPlan (mapping `feature_key → addon_slug`)
- `quota_email_service` legge da DB

**Acceptance criteria**:
1. Crea nuovo addon `addon_extra_chat_500`
2. Edita Free CommercialPlan, aggiunge `addon_ctas: {"chat": "addon_extra_chat_500"}`
3. Free user esaurisce chat → email/paywall mostra CTA "Buy +500 chat" puntando al nuovo slug

**Effort**: 1.5h.

---

### Step B.5 — `HARD_ABUSE_CAP` → catalog field

**File**: `backend/routers/stores.py:238` + `backend/models/commercial_plan.py`

**Cambio**:
- Aggiungere `hard_abuse_caps: Dict[str, int]` su CommercialPlan (es. `{"stores_max": 10}`)
- `stores.py` legge da `get_hard_abuse_cap(org, "stores_max")` con default 100
- Eliminare costante hardcoded

**Effort**: 1h.

**Approval gate Fase B**: Davide rivede il refactor + audit log entries. Conferma → si passa a Fase C.

---

## 5. FASE C — System admin self-serve (create new entities)

**Obiettivo**: rendere possibile via UI:
- Creare un nuovo tier (`PricingPlan`)
- Creare un nuovo plan commerciale (`CommercialPlan`)
- Creare un nuovo addon (`CommercialPlan` con `is_addon=True`)
- Stripe Product/Price auto-creati server-side

### Step C.1 — `POST /admin/catalog/entitlement-tiers`

**File**: `backend/routers/admin_catalog.py` + `backend/repositories/catalog_repository.py`

**Cambio**:
- Endpoint POST con body `{slug, module_key, name, limits, sort_order}`
- Validazione: slug univoco per modulo, module_key in `PRODUCT_MODULES`, limits con feature_keys validi
- Audit log su create

**Acceptance criteria**:
1. POST `/admin/catalog/entitlement-tiers` con body `{"slug":"cashflow_monitor_growth", "module_key":"cashflow_monitor", "name":"Growth Tier", "limits":{"data_rows":3000, ...}}` → 201
2. Re-POST stesso slug → 409 conflict

**Effort**: 2h.

---

### Step C.2 — `POST /admin/catalog/plans` (create new commercial plan)

**File**: idem + UI form in `CatalogTab.js`

**Cambio**:
- Endpoint POST con body completo CommercialPlan: `{slug, name, price_monthly, price_yearly, module_plans, features_display, is_public, is_self_serve, trial_days}`
- Validazione: tutti i `module_plans` slug devono esistere; slug univoco
- Audit log

**Acceptance criteria**:
1. Admin crea "Growth" plan con `cashflow_monitor: cashflow_monitor_growth, ai_assistant: ai_assistant_growth, ...`
2. PUT `/admin/organizations/{id}/commercial-plan` con `slug=growth` → 200 (post-Step B.3)
3. Org passa a Growth, eredita le limits del tier appena creato

**Effort**: 3h.

---

### Step C.3 — `POST /admin/catalog/addons`

**File**: idem

**Cambio**:
- Endpoint POST con body `{slug, name, price_monthly, addon_provides: {module: {feature: int}}, max_quantity, compatible_plans}`
- Validazione: addon_provides feature_keys esistono nei tier referenziati

**Acceptance criteria**:
1. POST con `{slug:"addon_500_orders", name:"+500 ordini", price_monthly:25, addon_provides:{commerce:{orders_monthly:500}}, max_quantity:5, compatible_plans:["starter","core","pro"]}` → 201
2. Org Solo assegna addon → `effective_limit(commerce, orders_monthly)` aumenta di 500

**Effort**: 2h.

---

### Step C.4 — Stripe Product/Price auto-create server-side

**File**: `backend/services/stripe_service.py` (nuovo metodo `create_product_and_price`) + integration in C.2/C.3 endpoints

**Cambio**:
- Quando admin crea plan/addon via POST, opzionalmente passa `auto_create_stripe: true`
- Server crea Stripe Product + Price (monthly + yearly), persiste IDs su CommercialPlan
- Se Stripe API down → log warning, plan creato senza Stripe IDs (admin può completare dopo)

**Acceptance criteria**:
1. POST plan con `auto_create_stripe:true` → Stripe Dashboard mostra nuovo Product + Price
2. `commercial_plans` doc ha `stripe_product_id` e `stripe_price_id_*` valorizzati

**Rollback**: rimuovere il Product creato su Stripe (non auto, log con ID per intervento manuale).

**Effort**: 4h.

---

### Step C.5 — UI "New Plan" / "New Addon" / "New Tier" forms

**File**: `frontend/src/features/admin/CatalogTab.js` + nuovi components

**Cambio**:
- 3 dialog + bottoni "+ New" in ognuna delle 3 viste (Plans, Tiers, Audit non)
- Form con tutti i campi richiesti, validazione client-side
- Toast su successo/errore + audit log entry visibile

**Acceptance criteria**:
1. Admin clicca "+ New Plan" → form modal si apre
2. Compila tutto, click Save → POST → toast "Plano Growth creato"
3. Lista plans aggiornata immediatamente

**Effort**: 4h.

---

### Step C.6 — Plan archive (soft delete)

**File**: `routers/admin_catalog.py` + UI

**Cambio**:
- Endpoint `PATCH /admin/catalog/plans/{slug}/archive` setta `is_archived=true`
- Plan archiviati non appaiono in PlansPage pubblica ma esistono ancora per org sub-scribed
- Endpoint `unarchive` per reverse

**Acceptance criteria**:
1. Archive Free plan → PlansPage non lo mostra più
2. Org Free esistente continua a funzionare

**Effort**: 2h.

**Approval gate Fase C**: Davide crea un plan "Test" via UI end-to-end e ne verifica funzionalità. Conferma → si passa a Fase D.

---

## 6. FASE D — Sicurezza e robustezza

### Step D.1 — `provision_commercial_plan` transazionale

**File**: `backend/services/plan_provisioning.py:74-114`

**Cambio**:
- Wrappare cancel-then-create in `async with await db.client.start_session() as s: async with s.start_transaction(): ...`
- Richiede MongoDB replica set (verificare se locale + prod sono in RS, altrimenti documentare requisito deploy)

**Effort**: 1.5h.

---

### Step D.2 — Rate limit sui POST quota-gated

**File**: tutti i `routers/sales.py`, `expenses.py`, `orders.py`, `purchases.py`, `fixed_costs.py`, `purchase_records.py`

**Cambio**:
- Decoratore `@limiter.limit("60/minute")` come Depends su tutti i POST
- Configurabile via env `RATE_LIMIT_DATA_WRITES`

**Effort**: 1h.

---

### Step D.3 — Stripe price drift detection + validate dialog

**File**: `routers/admin_catalog.py` (nuovo endpoint `GET /admin/catalog/plans/{slug}/stripe-validate`) + UI in `PlanManageDialog`

**Cambio**:
- Endpoint chiama Stripe `Price.retrieve(stripe_price_id_*)`, confronta `unit_amount` vs `price_monthly * 100`
- Risposta: `{matches: bool, db_price, stripe_price, recommendations: []}`
- UI mostra banner verde/rosso accanto al campo prezzo

**Effort**: 3h.

---

### Step D.4 — Bulk action infrastructure

**File**: `routers/admin.py` (nuovo endpoint `POST /admin/bulk/{action}`) + UI

**Cambio**:
- Action types: `downgrade_inactive_pro`, `migrate_legacy_plan`, `cancel_test_orgs`
- Body include `filter` (criteri) + `dry_run: bool` + `confirm: true`
- Audit log entry per ogni org affetta

**Acceptance criteria**:
1. POST con filter `{plan: "pro", inactive_days: 30}` + `dry_run: true` → ritorna lista 50 org candidate
2. Re-POST con `dry_run: false` → applica downgrade, audit log per ognuna

**Effort**: 4h.

**Approval gate Fase D**: Davide rivede coverage rate-limit e bulk actions. Conferma → si passa a Fase E.

---

## 7. FASE E — Monitoring e observability

### Step E.1 — Cron giornaliero `audit_billing_consistency` con email digest

**File**: `backend/services/background_service.py` + email template

**Cambio**:
- Nuovo job in lifespan startup che ogni 24h esegue `audit_billing_consistency.scan_all_orgs()`
- Se trova drift HIGH → email a `system_admin` con riassunto + link admin panel

**Effort**: 3h.

---

### Step E.2 — Drift overview banner in `OrganizationsTab`

**File**: `frontend/src/features/admin/OrganizationsTab.js`

**Cambio**:
- All'inizio della tab, banner che mostra stats batch da `/admin/catalog/organizations/commercial-overview`
- "12 org con drift, 3 critical" + link al filtro

**Effort**: 1.5h.

---

### Step E.3 — Filtro plan + billing_status nella OrganizationsTab

**File**: idem (`OrganizationsTab.js:458-488`)

**Cambio**:
- Estendere filter bar con select `plan` (Free/Solo/Core/Pro/Enterprise/All) e `status` (active/trialing/past_due/canceled/none)
- Filter client-side (org list già caricata)

**Effort**: 1.5h.

**Approval gate Fase E**: Davide riceve la prima email digest (manualmente triggerable). Conferma → si passa a Fase F.

---

## 8. FASE F — UX gap residui + cleanup

### Step F.1 — `forms.quota_exhausted_*` keys in 4 locale

**File**: `frontend/src/locales/{it,en,de,fr}/cashflow_monitor.json`

**Cambio**: aggiungere chiavi `forms.quota_exhausted_hint`, `_body`, `_cta` con interpolazione `{{used}}/{{limit}}` in 4 lingue.

**Effort**: 1h.

---

### Step F.2 — `QuotaProgressBanner` mount in OrdersPage / ChatWidget / UploadPage / StoresPage

**File**: 4 pages target

**Cambio**: aggiungere `<QuotaProgressBanner metric="..." />` in cima a ogni pagina, configurato per la metric pertinente.

**Effort**: 1h.

---

### Step F.3 — Cleanup dead code

**File**: rimuovere `PlanIndicator.jsx` (o montarlo se utile), `QuotaExceededBanner.js`, `UpgradePaywall.jsx` (no caller)

**Effort**: 30 min.

---

### Step F.4 — Pre-emptive gate `team_members` in TeamPage

**File**: `frontend/src/features/team/TeamPage.js`

**Cambio**: usare `useEntitlements().quotaExhausted("team", "team_members")` (post Step B.1) per disabilitare bottone "+ Invite member" con hint.

**Effort**: 30 min.

---

### Step F.5 — AI digest exhaustion: aggiungere paywall inline

**File**: `frontend/src/features/cashflow/components/DigestTab.js:262-358`

**Cambio**: quando `quotaExhausted('digest')`, mostrare card paywall sopra il bottone disabled con CTA upgrade.

**Effort**: 1h.

**Approval gate Fase F**: Davide fa giro UX completo per validare. Conferma → progetto chiuso.

---

## 9. Acceptance criteria globale (post-Onda 10)

1. ✅ Admin alza `data_rows` Solo 200→500 → utenti già loggati lo vedono entro 60s
2. ✅ Admin crea nuovo plan "Growth" via UI → org può sub-scriversi a quel plan
3. ✅ Admin crea nuovo addon → org può aggiungerlo
4. ✅ Stripe Product/Price si auto-creano (opzionale) o si validano vs Stripe
5. ✅ Cron giornaliero audit + email digest a system admin
6. ✅ Bulk downgrade/migrate disponibile via UI
7. ✅ Zero `_TEAM_LIMITS`/`_PLAN_TTL_DAYS`/`VALID_COMMERCIAL_PLANS`/`METRIC_TO_ADDON_OFFER`/`HARD_ABUSE_CAP` hardcoded fuori catalog
8. ✅ i18n parametriche → label si adattano a qualsiasi numero
9. ✅ POST quota-gated rate-limited
10. ✅ Provisioning transazionale (Mongo RS)

---

## 10. Mappa file modificati

| File | Tipo | Fase |
|---|---|---|
| `backend/database.py` | minor (eventuali nuovi indici) | varie |
| `backend/models/commercial_plan.py` | EXTENDED (nuovi campi) | B.2, B.4, B.5 |
| `backend/models/admin.py` | DELETE frozenset | B.3 |
| `backend/models/pricing_plan.py` | minor | A.3 |
| `backend/services/seed_pricing.py` | extended | B.1, B.2 |
| `backend/services/seed_commercial_plans.py` | extended | B.4, B.5 |
| `backend/services/chat_service.py` | refactor | B.2 |
| `backend/services/quota_email_service.py` | refactor | B.4 |
| `backend/services/plan_provisioning.py` | TRANSACTIONAL | D.1 |
| `backend/services/stripe_service.py` | extended (create_product) | C.4, D.3 |
| `backend/services/background_service.py` | NEW cron | E.1 |
| `backend/routers/organizations.py` | refactor (rm `_TEAM_LIMITS`) | B.1 |
| `backend/routers/billing.py` | refactor (rm dup) | B.1 |
| `backend/routers/stores.py` | refactor (rm `HARD_ABUSE_CAP`) | B.5 |
| `backend/routers/admin.py` | extended (validation, bulk) | B.3, D.4 |
| `backend/routers/admin_catalog.py` | extended (POST plans/tiers/addons, archive, validate-stripe) | C.1, C.2, C.3, C.6, D.3 |
| `backend/routers/sales.py`, `expenses.py`, `orders.py`, `purchases.py`, `fixed_costs.py`, `purchase_records.py` | rate-limit decorator | D.2 |
| `backend/repositories/catalog_repository.py` | extended | C.* |
| `backend/scripts/migrate_features_display_to_structured.py` | NEW | A.3 |
| `backend/scripts/migrate_team_limits_to_catalog.py` | NEW | B.1 |
| `backend/scripts/test_dynamic_quota_propagation.py` | NEW | A.4 |
| `frontend/src/hooks/useEntitlements.js` | polling+focus | A.1 |
| `frontend/src/hooks/useBilling.js` | focus listener | A.2 |
| `frontend/src/components/UpgradeDialog.js`, `pages/PlansPage.js` | i18n parametriche | A.3 |
| `frontend/src/features/admin/CatalogTab.js` | "New" forms | C.5 |
| `frontend/src/features/admin/OrganizationsTab.js` | filtri + drift banner | E.2, E.3 |
| `frontend/src/features/team/TeamPage.js` | pre-emptive gate | F.4 |
| `frontend/src/features/cashflow/components/DigestTab.js` | paywall inline | F.5 |
| `frontend/src/locales/{4}/settings.json` | nuove chiavi parametriche | A.3 |
| `frontend/src/locales/{4}/cashflow_monitor.json` | quota_exhausted keys | F.1 |
| `frontend/src/components/PlanIndicator.jsx`, `QuotaExceededBanner.js`, `UpgradePaywall.jsx` | DELETE (dead code) | F.3 |

**Totale stima**: ~20 file modificati + ~5 nuovi.

---

## 11. Rollback strategy

Ogni step ha un rollback specifico documentato sopra. A livello di fase:

- **Fase A**: `git revert` di 4 commit. UI torna stale-on-mount. Zero data loss.
- **Fase B**: ogni step ha migration script che può essere rieseguito al contrario (re-popola hardcoded da DB). Zero data loss.
- **Fase C**: nuovi plan/addon possono essere `is_archived=true` se sbagliati. Stripe Product creati sono soft-archivable.
- **Fase D**: rate-limit revert via env. Transazionale → revert plan_provisioning.py 1 commit.
- **Fase E**: cron disable via flag.
- **Fase F**: pure UX, ogni step revertibile in 5 min.

---

## 12. Approval gate

Prima di iniziare, Davide rivede questo piano e conferma:

- [ ] Scope: tutto A→F oppure subset (es. solo A+B per partire)
- [ ] Priorità: Fase A è bloccante per il caso d'uso? Sì → partiamo da lì
- [ ] Stripe API: hai chiavi test/live disponibili per Step C.4 + D.3?
- [ ] MongoDB: deploy prod è in replica set? Necessario per Step D.1
- [ ] Email digest: indirizzo destinatario per Step E.1?
- [ ] UI: vuoi che apra la prima dialog "New Plan" o preferisci un mockup prima?

Una volta approvato, parto da Fase A con cadenza step-per-step + validation dopo ogni commit.

---

**END OF PLAN**
