# Billing Gating — Audit Forensico Completo + Piano di Fix (Onda 9.Y)

**Status**: ANALISI FATTA · PIANO PRONTO · APPROVAZIONE NECESSARIA prima di implementare.
**Audit eseguito**: 2026-04-30 su `/Users/davidedefilippis/Desktop/BI_PMI/`
**Scope**: 155+ endpoint backend, 9 componenti frontend paywall, 4 locale i18n, 18 (module, feature_key) della matrice + team_members hardcoded.

---

## Executive Summary (TL;DR)

**Cosa funziona già oggi (la base è solida):**
- 28 endpoint hanno gate corretto (sales, expenses, purchases, fixed_costs, products, courses, event_occurrences, stores, orders manuale, public order, chat, digests, export, alerts/preferences, modules/health-explanation, team invite, dataset_service, order_service confirm).
- 2 paywall modali wired globalmente (`QuotaExceededPaywall` per 429, `ModuleAccessPaywall` per 403).
- 2 banner sticky funzionanti (`BillingStatusBanner` per trial-expired/past-due, `ReadOnlyGraceBanner`).
- `axios interceptor` intercetta correttamente 6 codici (`READ_ONLY_GRACE`, `BILLING_TRIAL_EXPIRED`, `BILLING_PAST_DUE`, `MODULE_NOT_AVAILABLE`, `FEATURE_NOT_AVAILABLE`, `QUOTA_EXCEEDED`) e dispatcha `CustomEvent` puntuali.
- `smartToastInit` (Onda 9.X) sopprime correttamente i toast duplicati per gli stessi 6 codici.
- AI features hanno **pre-emptive gating** client-side tramite `useAiAccess` (chat, digest, alert_analysis, health_explanation).

**Cosa è rotto oggi (in ordine di severità):**

| Severity | Categoria | Numero gap | Effort fix |
|---|---|---|---|
| **P0 — security** | Endpoint Stripe Connect totalmente ungated | **6** | 1h |
| **P1 — quota bypass** | Endpoint che mutano dati senza counter | **5** | 2-3h |
| **P1 — consistency** | Sorgenti dati gate vs dashboard divergenti | **4** | 2-4h |
| **P2 — UX** | i18n `body_by_feature.*` mancante per il 100% delle feature 403 | **18** | 4-6h |
| **P2 — UX** | Mancano `useEntitlements()` + bottoni client-side disabled | **7 azioni su 10** | 4-6h |
| **P2 — UX** | Bypass paywall: Excel export usa toast bespoke | **1** | 30min |
| **P2 — debt** | feature_key inesistenti nella matrice (coupons, AI store, customers, suppliers) | **15+** | 3-4h |
| **P3 — debt** | No caching `get_effective_limit`, log unbounded, TZ drift | **6** | 4-8h |

**Totale stimato fix completo:** ~25-35h split su 5 sotto-fasi. Patch immediata dei due bug riportati: ~2h.

---

## PARTE 1 — Stato attuale (analisi forensica)

### 1.1 La matrice canonica

Convenzione: `-1` = unlimited / flag ON, `0` = disabled / flag OFF, `>0` = quota mensile (counter).

| module | feature_key | tipo | free | starter | core | pro | enterprise | UI di consumo |
|---|---|---|---|---|---|---|---|---|
| `ai_assistant` | `chat` | counter | 3 | 20 | 80 | 200 | -1 | ChatWidget, AnalisiAIPage |
| `ai_assistant` | `digest` | counter | 0 | 0 | 4 | -1 | -1 | DigestTab |
| `ai_assistant` | `alert_analysis` | flag | 0 | 0 | -1 | -1 | -1 | (server-side only, no UI) |
| `ai_assistant` | `health_explanation` | flag | 0 | 0 | -1 | -1 | -1 | HealthScoreGauge |
| `cashflow_monitor` | `analytics` | flag | -1 | -1 | -1 | -1 | -1 | (sempre on) |
| `cashflow_monitor` | `data_rows` | counter | 200 | 1000 | -1 | -1 | -1 | sales/expenses/purchases/fixed_costs/datasets |
| `cashflow_monitor` | `export` | flag | 0 | -1 | -1 | -1 | -1 | CashflowDataPage |
| `cashflow_monitor` | `email_alerts` | flag | 0 | -1 | -1 | -1 | -1 | settings/alerts |
| `cashflow_monitor` | `email_digest` | flag | 0 | -1 | -1 | -1 | -1 | (?) |
| `cashflow_monitor` | `alert_config` | flag | 0 | -1 | -1 | -1 | -1 | settings/alerts |
| `product_catalog` | `analytics` | flag | 0 | 0 | -1 | -1 | -1 | ProductsPage |
| `product_catalog` | `products` | counter | 0 | 0 | 200 | -1 | -1 | ProductsPage |
| `commerce` | `analytics` | flag | 0 | 0 | -1 | -1 | -1 | OrdersPage |
| `commerce` | `orders_monthly` | counter | 0 | 0 | 200 | 1000 | -1 | OrdersPage, public storefront |
| `commerce` | `stores_max` | counter | 0 | 0 | 1 | 3 | -1 | StoresPage |
| `commerce` | `checkout_stripe` | flag | 0 | 0 | -1 | -1 | -1 | PaymentConnectionsCard, public order |
| `customers_light` | `analytics` | flag | -1 | -1 | -1 | -1 | -1 | (sempre on) |
| `commerce_signals` | `analytics` | flag | -1 | -1 | -1 | -1 | -1 | (sempre on) |

**Hardcoded fuori matrice** (debt — duplicato in 2 posti):
- `team_members`: `{free:1, starter:2, core:5, pro:15, enterprise:-1}` in `routers/organizations.py:1246` + `routers/billing.py:238`.
- `chat_session_ttl_days`: `{free:7, starter:30, core:90, pro:180, enterprise:365}` in `services/chat_service.py:27` (non azione, retention).
- `stores_hard_abuse_cap`: `10` constant in `routers/stores.py:238` (defense-in-depth).

**Add-on disponibili** (incrementano `effective_limit`):

| slug | €/mo | unlocks | piani compatibili | max_qty |
|---|---|---|---|---|
| `addon_ai_chat_pack` | 9 | `ai_assistant.chat += 50` | starter, core, pro | 5 |
| `addon_ai_chat_pro` | 29 | `ai_assistant.chat += 200` | core, pro | 3 |
| `addon_orders_pack` | 15 | `commerce.orders_monthly += 200` | core, pro | 5 |
| `addon_extra_store` | 19 | `commerce.stores_max += 1` | pro only | 7 |

**Add-on mancanti** (debt — feature_key senza top-up disponibile):
- `cashflow_monitor.data_rows` → niente addon (Free deve passare a Solo per più di 200 righe)
- `product_catalog.products` → niente addon (Core deve passare a Pro per più di 200)
- `team_members` → niente addon
- AI digest, AI alert_analysis, AI health_explanation → niente addon (richiede salto di piano)

### 1.2 Stato gate backend — endpoint per endpoint

**Totale endpoint inventariati**: ~155 routes + 2 service-level bulk mutators.

#### 1.2.A — GATED ✅ (28 endpoint che funzionano correttamente)

| Endpoint | Module / Feature | Pattern |
|---|---|---|
| `POST /sales`, `/expenses`, `/purchases`, `/fixed-costs`, `/fixed-costs/bulk` | `cashflow_monitor.data_rows` | A. counter monthly + record |
| `POST /products`, `/products/{id}/duplicate` | `product_catalog.products` | D. counter persistent (live count) |
| `POST /courses` (auto-link product), `/courses/{id}/product` | `product_catalog.products` | D. via `_ensure_linked_product` |
| `POST /event-occurrences/wizard` | `product_catalog.products` | D. |
| `POST /stores` | `commerce.stores_max` | D. + HARD_ABUSE_CAP=10 |
| `POST /orders` (manual create) | `commerce.orders_monthly` | A. counter snapshot |
| `POST /public/order-request` | `commerce.orders_monthly` + `commerce.checkout_stripe` | A. + flag for Free coercion |
| `POST /chat` | `ai_assistant.chat` | A. counter monthly + record |
| `POST /digests/generate` | `ai_assistant.digest` | A. |
| `POST /export/...` (cashflow) | `cashflow_monitor.export` | C. flag |
| `PUT /alerts/preferences` | `cashflow_monitor.alert_config` | C. flag |
| `POST /modules/{key}/health-explanation-ai` | `ai_assistant.health_explanation` | C. soft-fallback (200 con default explanation se ungated) |
| `POST /organizations/team/invite` | `team_members` (hardcoded) | D. counter persistent |
| `services/dataset_service.py:1486` (CSV upload) | `cashflow_monitor.data_rows` | B. bulk counter |
| `services/order_service.py:1294` (sales materialization on order confirm) | `cashflow_monitor.data_rows` | A. counter from order line items |
| `services/alert_notification_service.py:158, 334, 489` | `email_alerts`, `email_digest` | C. inline server-side check |
| `services/alert_service.py:104` | `alert_config` | C. inline check on alert generation |

#### 1.2.B — UNGATED ❌ (i 14 gap reali, ranked by severity)

##### **P0 — Security (Stripe Connect bypass)** — 6 endpoint

Tutti in `routers/payment_connections.py`:

| Endpoint | Linea | Auth | Manca |
|---|---|---|---|
| `POST /payment-connections/stripe/express/start` | 94 | `require_admin` | `check_module_access(commerce, checkout_stripe)` |
| `POST /payment-connections/stripe/express/refresh` | 128 | `require_admin` | idem |
| `POST /payment-connections/stripe/express/complete` | 150 | `require_admin` | idem |
| `POST /payment-connections/stripe/express/dashboard-link` | 177 | `require_admin` | idem |
| `POST /payment-connections` | 214 | `require_admin` | idem (per provider PayPal/Bank) |
| `PATCH /payment-connections/{id}` | 262 | `require_admin` | idem (per `is_default=true`) |

**Impatto**: org Free completa onboarding Express, ottiene un account Stripe Connect attivo. Il flusso `/public/order-request` controlla `checkout_stripe` flag (`public.py:2526-2530`) e **declassa l'ordine a contact-request** se mancante — quindi il danno è limitato (no double-charge), ma l'org può confondersi vedendo Stripe "connesso" senza poter ricevere pagamenti. **L'esperienza UX è incoerente**.

##### **P1 — Quota bypass su path collaterali** — 5 endpoint

| Endpoint | Linea | Manca | Impatto |
|---|---|---|---|
| `POST /orders/import` (CSV) | `routers/orders.py:814` | `commerce.orders_monthly` + `cashflow_monitor.data_rows` | Free user importa 1000 ordini, scrive sales rows beyond ogni quota |
| `POST /orders/import-with-mapping` | `routers/orders.py:892` | idem | Stesso bypass, secondo leg dopo column-mapping |
| `POST /orders/pos` | `routers/orders.py:698` | `commerce.orders_monthly` | POS chiama `svc_create` senza `enforce_count_quota` |
| `POST /purchase-records` | `routers/purchase_records.py:30` | `cashflow_monitor.data_rows` | Bug A segnalato dall'utente |
| `services/order_import_service.py` (bulk insert) | linea 496 | idem (chiamato da B7/B8) | Causa diretta del bypass |

##### **P2 — Flag/Counter bypass meno critici** — 9+ endpoint

| Endpoint | Manca | Note |
|---|---|---|
| `POST /coupons` (`routers/coupons.py:40`) | nuova feature_key `commerce.coupons` | Free user crea coupons illimitati |
| `POST /products/{id}/digital-file` (`routers/products.py:530`) | nuova feature_key `product_catalog.digital_storage` | Storage Bunny illimitato a costo piattaforma |
| `POST /alerts/generate` (`routers/alerts.py:99`) | `cashflow_monitor.alert_config` o nuovo `alert_generation` | Spam anomaly detection |
| `POST /ai-store/generate-identity` (`routers/ai_store.py:54`) | `ai_assistant.chat` o nuovo | Free user chiama Claude tramite onboarding senza counter |
| `POST /ai-store/generate-products` (linea 227) | idem | LLM cost a piattaforma |
| `POST /ai-store/suggest-fulfillment` (linea 325) | idem | idem |
| `POST /ai-store/enrich-product` (linea 411) | idem | idem |
| `POST /ai-store/generate-setup` (linea 526) | idem | idem |
| `POST /ai-store/extract-from-url` (linea 737) | idem | idem |
| `POST /customers`, `POST /suppliers` | nuova feature_key se monetizzate | Oggi free-for-all (governance review) |
| `POST /availability/rules`, `/blocked`, `/blocked/batch` | nuova feature_key se monetizzate | Servizi modulo non ancora monetizzato |

##### **P3 — Edit/delete su risorse già contate** — 30+ endpoint
Già accettabili (le modifiche su record già contati non muovono counter): edit prodotti/store/order/courses, image upload, lifecycle order, ticket check-in, ecc. **Non richiedono fix**.

#### 1.2.C — Statistica gate

```
Total endpoints inventoriati:  ~155 routers + 2 service bulk mutators
GATED ✅                          28 (18%)
UNGATED ❌                        20 (13%)
   ├─ P0 (security)                6
   ├─ P1 (quota bypass)            5
   └─ P2 (flag/counter, governance) 9+
N/A 🔘 (auth, system_admin, edits) ~107 (69%)
```

### 1.3 Stato paywall/popup frontend

#### 1.3.A — Componenti paywall

| Componente | Wired? | Trigger | Copy specifico per feature? |
|---|---|---|---|
| `QuotaExceededPaywall.jsx` | ✅ mounted in App.js:590 | `billing:quota-exceeded` (429) | ✅ 9 feature hanno `title_by_feature` + `body_by_feature` (chat, orders_monthly, data_rows, products, stores_max, digest, team_members, alert_analysis, health_explanation) |
| `ModuleAccessPaywall.jsx` | ✅ mounted in App.js:591 | `billing:module-not-available` + `billing:feature-not-available` (403) | ❌ **0 feature hanno copy specifico** — la chiave `body_by_feature.*` NON ESISTE in nessuna locale |
| `BillingStatusBanner.js` | ✅ mounted in App.js:582 (sticky top) | `billing:trial-expired` + `billing:past-due` | ✅ 2 stati (trial_expired, past_due) |
| `ReadOnlyGraceBanner.js` | ✅ mounted in App.js:583 | `billing:read-only-grace` | ✅ unico copy |
| `QuotaExceededBanner.js` | ❌ **dead code** (App.js:589 commento "rimosso, ridondante") | — | — |
| `UpgradePaywall.jsx` | ❌ **no callers** | — | — |
| `QuotaProgressBanner.jsx` | ❌ **no callers** | — | — |
| `StripeRequiredAlert.jsx` | ✅ inline in product form | `useStripeReadiness` hook | Stripe-readiness specifico (non plan-paywall) |
| `PlanIndicator.jsx` | ✅ topbar | polls `getUsageSummary` ogni 5min | tooltip su soglia |
| `UpgradeDialog.js` | ✅ controlled modal | click manuale "Upgrade plan" | catalog browser |

#### 1.3.B — Coverage i18n (4 locale: it/en/de/fr)

Per ognuna delle 18 (module, feature_key) della matrice + team_members:

| feature_key | 429 quota title (`title_by_feature.*`) | 429 quota body (`body_by_feature.*`) | 403 module_paywall body (`module_paywall.body_by_feature.*`) | metric label |
|---|---|---|---|---|
| `chat` | ✅ all 4 | ✅ all 4 | ❌ MISSING all 4 | ✅ |
| `digest` | ✅ all 4 | ✅ all 4 | ❌ MISSING all 4 | ✅ |
| `alert_analysis` | ✅ all 4 | ✅ all 4 | ❌ MISSING all 4 | ✅ |
| `health_explanation` | ✅ all 4 | ✅ all 4 | ❌ MISSING all 4 | ✅ |
| `data_rows` | ✅ all 4 | ✅ all 4 | ❌ MISSING all 4 | ✅ |
| `export` | ⚠️ generic fallback | ⚠️ generic | ❌ MISSING all 4 | ⚠️ generic |
| `email_alerts` | ⚠️ generic | ⚠️ generic | ❌ MISSING all 4 | ⚠️ generic |
| `email_digest` | ❌ MISSING all 4 | ❌ MISSING all 4 | ❌ MISSING all 4 | ❌ MISSING |
| `alert_config` | ⚠️ generic | ⚠️ generic | ❌ MISSING all 4 | ⚠️ generic |
| `products` | ✅ all 4 | ✅ all 4 | ❌ MISSING all 4 | ✅ |
| `orders_monthly` | ✅ all 4 | ✅ all 4 | ❌ MISSING all 4 | ✅ |
| `stores_max` | ✅ all 4 | ✅ all 4 | ❌ MISSING all 4 | ✅ |
| `checkout_stripe` | ❌ MISSING (capability, no 429) | n/a | ❌ MISSING all 4 | ❌ MISSING |
| `team_members` | ✅ all 4 | ✅ all 4 | ❌ MISSING all 4 | ✅ |

**Conclusione i18n**: il **100% delle feature in scenario 403** mostra all'utente il messaggio generico "Questa funzionalità richiede un piano superiore" senza spiegare quale piano sblocca cosa. La sottostruttura `module_paywall.body_by_feature.*` è referenziata in `ModuleAccessPaywall.jsx:91` ma **non esiste in nessuna delle 4 locale**.

#### 1.3.C — Pre-emptive UI gating (bottoni client-side disabled)

| Azione | Componente | Pre-emptive? | Copy locked-hint? |
|---|---|---|---|
| AI chat send | `ChatWidget.js`, `AnalisiAIPage.js` | ✅ disabled via `useAiAccess.canUse('chat')` | ✅ |
| AI Health AI explanation | `HealthScoreGauge.js:195-200` | ✅ button hidden via `useAiAccess.canUse('health_explanation')` | n/a (hidden) |
| AI digest | `DigestTab.js` | ✅ via `useAiAccess` | ✅ |
| "Connect Stripe" | `PaymentConnectionsCard.js:323-332` | ❌ NO — bottone visibile a tutti gli admin | ❌ |
| "Upload CSV" datasets | `UploadPage.js:547` | ❌ NO — solo `uploading` flag | ❌ |
| "+ Crea prodotto" | `ProductsPage.js` | ❌ NO — server-side only | ❌ |
| "+ Aggiungi store" | `StoresPage.js:874` | ❌ NO — server-side only (commento esplicito menziona over-limit dopo downgrade) | ❌ |
| "+ Invita team" | `TeamPage.js:157, 220` | ❌ NO — solo `inviting` flag | ❌ |
| "Esporta Excel" cashflow | `CashflowDataPage.js:60-66` | ❌ NO — solo `exporting` flag, fa toast bespoke (BYPASS PAYWALL) | ❌ |
| Configura email_alerts/digest | settings/alerts | ⚠️ UNCLEAR (chiavi i18n `prefs.upgrade_required` esistono ma codice non confermato) | ⚠️ |
| Anomaly Analysis (alert_analysis) | (server-only, no UI) | n/a | n/a |

**Conclusione**: **solo 3 azioni su 11** hanno pre-emptive gating, tutte AI. Le altre 8 si basano sulla rejection backend + paywall reattiva. **Mancanza strutturale**: non esiste un hook `useEntitlements()` generale per le feature non-AI.

#### 1.3.D — Hook entitlements esistenti

| Hook | File | Espone | Consumers |
|---|---|---|---|
| `useBilling` | `hooks/useBilling.js` | plan, status, trial, `hasPlan(tier)`, plan catalog. **No `canUse(featureKey)`** | 4 (SettingsPage, BillingSection, PlansPage, UpgradeDialog) |
| `useAiAccess` | `hooks/useAiAccess.js` | plan, `canUse(feature)`, `quotaExhausted(feature)`, `usage`, `limits` per AI features | 5 (BillingSection, AnalisiAIPage, DigestTab, ChatWidget, HealthScoreGauge) |

**Manca**: `useEntitlements()` con `canUse(moduleKey, featureKey)` + `getEffectiveLimit()` + `getUsage()` per feature non-AI (data_rows, products, stores_max, orders_monthly, checkout_stripe, export, email_alerts, team_members).

### 1.4 Stato sorgenti dati / consistency (P1 critico)

Il gate (`check_module_access`) e il dashboard (`/usage-summary`, email warning sweep) leggono **da fonti diverse** per alcune feature. Risultato: l'utente vede 145/200 nel dashboard ma il gate lo lascia passare oltre, oppure viceversa. Tabella:

| feature_key | source A — gate | source B — dashboard / email | aligned? |
|---|---|---|---|
| `ai_assistant.chat` | `ai_usage_events` `$sum quantity` | `ai_usage_events` `count_documents` (ignora quantity) | ⚠️ drift se quantity > 1 (oggi sempre 1, latente) |
| `cashflow_monitor.data_rows` | `ai_usage_events` `$sum quantity` | `datasets_collection` `$sum row_count` | ❌ **due collezioni diverse — drift fino a 100s di righe** |
| `commerce.orders_monthly` | `orders_collection.count_documents` (current month) | `orders_collection.count_documents` | ✅ aligned |
| `product_catalog.products` | `products_collection.count_documents({org_id})` | `products_collection.count_documents({org_id, is_active: True})` | ❌ gate ignora is_active, dashboard sì → drift su soft-delete |
| `commerce.stores_max` | `stores_collection.count_documents({org_id, is_active: True})` | idem | ✅ aligned |
| `team_members` | `users_repository.find_by_org` filter is_active in Python | `users_collection.count_documents({org_id, is_active: True})` | ✅ aligned ma entrambi bypassano `get_effective_limit` (no addon support) |

**Bug user-impacting confermati:**
- **P1.1 — `data_rows` split-brain**: il dashboard mostra il `row_count` dei datasets importati, il gate conta gli `ai_usage_events` scritti dai router manuali. **L'utente vede un numero, il gate ne usa un altro.** Tipico scenario: importi 800 righe via dataset_service (entrambe le sorgenti aumentano), poi crei 50 sales manuali (solo source A aumenta). Dashboard dice 850, gate dice 850. Ma se importi via `order_import` (B7/B8 ungated), né A né B vedono le righe.
- **P1.2 — `products` is_active mismatch**: soft-delete riduce il count nel dashboard ma il gate continua a contare. Utente cancella 5 prodotti su 200/200 → dashboard dice 195/200, gate dice 200/200 (rejected). Confusione UX.
- **P1.3 — `team_members` bypassa `get_effective_limit`**: hardcoded duplicato in 2 file. Se aggiungiamo un addon team in futuro, non funzionerà.

### 1.5 Esperienza utente attuale — 10 scenari

Fonte: codice frontend al 2026-04-30.

| # | Scenario | Cosa vede l'utente OGGI |
|---|---|---|
| 1 | Free, 200/200 data_rows, "+ Add sale" | ✅ **PAYWALL_MODAL** con copy specifico "Limite righe dati raggiunto. Hai importato 200/200 righe questo mese. Aggiorna…" + bottone Upgrade |
| 2 | Free, "Connect Stripe" | ⚠️ **NO BLOCK** — backend NON ritorna 403 (gate manca). Stripe account viene creato. Solo al primo `/public/order-request` il flag viene controllato e l'ordine declassato |
| 3 | Free, "+ team member" (2°) | ✅ **PAYWALL_MODAL** "Limite membri team raggiunto" + Upgrade |
| 4 | Free, "+ Crea prodotto" (51°) | ✅ **PAYWALL_MODAL** "Limite prodotti a catalogo raggiunto" |
| 5 | Free, "Esporta Excel" cashflow | ⚠️ **TOAST bespoke** "Export disponibile con piano Pro" — bypassa il sistema paywall. Possibile race con modal sottostante |
| 6 | Free, "Anomaly Analysis with AI" | ⚠️ **NO UI** — la feature è server-side automatica. L'utente Free vede gli alert ma senza spiegazione AI, senza messaggio che indichi perché |
| 7 | Free, AI chat 4° messaggio | ✅ **PRE-EMPTIVE** — input disabled. Se bypassato → modal "Chat AI esaurita" + addon CTA |
| 8 | Solo, "Connect Stripe" | ⚠️ Stesso scenario 2 — niente blocco lato connessione |
| 9 | Solo, 1001ª data_row | ✅ **PAYWALL_MODAL** "Limite righe dati raggiunto" (ma nessun addon CTA — non esiste addon per data_rows) |
| 10 | Core, 201° ordine pubblico | ⚠️ Lato merchant: paywall normale. Lato customer storefront anonimo: backend errore generico (no auth context per identificare i18n locale corretta) |

### 1.6 Problemi di osservabilità / debt latente

- **`get_effective_limit` no caching**: 3+N round trip Mongo per ogni gate check (1 active sub + 1 pricing plan + 1 active addons + N addon plans). Hot-path: chat, data import.
- **`ai_usage_events` unbounded**: nessun TTL, nessun rollup. Crescita ~12 mesi → aggregation pipeline lenta senza index su `(org_id, module_key, feature, created_at)` che non è verificato esistere.
- **TZ drift**: `count_usage` usa `date.today()` (server-local), `_count_monthly_usage` usa `datetime.now(timezone.utc)`. Su server non-UTC, drift di 24h ai confini mese.
- **`created_at` come ISO string**: query lessicografica funziona, ma fragile se un legacy doc ha `datetime` invece di string.
- **`is_monthly` flag confuso**: `commerce.orders_monthly` è classificato `monthly` in `_MONITORED_METRICS` ma usa `enforce_count_quota` snapshot. I due path coincidono per coincidenza.

---

## PARTE 2 — Piano di fix

Il piano è organizzato in **5 sotto-fasi sequenziali** con priorità decrescente. Ogni fase è git-revert-safe e testabile in isolamento.

### Fase 9.Y.0 — Patch immediata (P0 + P1 critici) · ~2-3h

**Obiettivo**: chiudere i due bug riportati dall'utente + tappare i 6 endpoint Stripe Connect.

**Backend** (~80 LOC):

1. **`routers/payment_connections.py`**: aggiungi prima riga in 4 endpoint (start, refresh, complete, dashboard-link):
   ```python
   await check_module_access(org_id, "commerce", "checkout_stripe")
   ```
   Per i 2 generic POST/PATCH (linee 214, 262), valuta se il check va dentro o fuori (probabilmente dentro `payment_connection_service.create_connection`).

2. **`routers/purchase_records.py:30`** — POST handler:
   ```python
   await check_module_access(org_id, "cashflow_monitor", "data_rows", pending_quantity=1)
   # ... existing code ...
   await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=1)
   ```

3. **`services/order_import_service.py`** — prima del bulk insert (linea ~496):
   ```python
   await check_module_access(org_id, "commerce", "orders_monthly", pending_quantity=len(orders))
   await check_module_access(org_id, "cashflow_monitor", "data_rows", pending_quantity=total_sales_lines)
   # ... existing bulk insert ...
   await record_module_usage(org_id, "commerce", "orders_monthly", quantity=len(orders))
   await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=total_sales_lines)
   ```

4. **`routers/orders.py:698`** (POS path) — aggiungi `enforce_count_quota` come fa `POST /orders` linea 314.

**Frontend** (~30 LOC):

5. **`PaymentConnectionsCard.js:323-332`** — usa `useBilling().hasPlan('core')` per disable button:
   ```jsx
   const { hasPlan } = useBilling();
   const canConnectStripe = hasPlan('core'); // core, pro, enterprise hanno checkout_stripe=-1
   <Button
     disabled={!canConnectStripe || !isAdmin || hasStripe}
     title={!canConnectStripe ? t('settings:billing.stripe_connect_locked_hint') : undefined}
     onClick={handleConnect}
   >
     {t('connect_stripe')}
   </Button>
   {!canConnectStripe && <UpgradeHint feature="checkout_stripe" />}
   ```

**Test consolidamento Fase 9.Y.0**:
- Tenant Free POST `/payment-connections/stripe/express/start` → 403 `FEATURE_NOT_AVAILABLE` + paywall visibile
- Tenant Free POST `/purchase-records` → 429 `QUOTA_EXCEEDED` + paywall
- Tenant Free POST `/orders/import` con 50 righe a counter=180 → 429 prima del save, nessun record persistito
- Tenant Free POST `/orders/pos` → 403 (`checkout_stripe` mancante) o 429 (`orders_monthly=0`)
- Pro+addon: tutto passa normalmente
- Bottone "Connect Stripe" in Free è disabled con tooltip + hint upgrade

### Fase 9.Y.1 — Allineamento sorgenti dati (P1 consistency) · ~3-4h

**Obiettivo**: gate e dashboard guardano lo stesso numero. Fine del split-brain.

1. **`cashflow_monitor.data_rows` unificazione**:
   - Decisione: `ai_usage_events` rimane sorgente unica. Il dashboard sweep in `background_service.py:493-504` viene aggiornato per leggere `count_usage(...)` invece di `datasets.row_count`.
   - Backfill: opzionale script `scripts/backfill_data_rows_events.py` che, per ogni dataset esistente del mese corrente, scrive un evento `ai_usage_events` retroattivo (idempotent). Valuta se necessario o se "this month forward" basta.

2. **`product_catalog.products` is_active alignment**:
   - In `routers/products.py:86`, aggiungi `"is_active": True` al filter di `count_documents`.
   - Verificare che il soft-delete imposti `is_active=False` (non delete).

3. **`team_members` centralizzazione**:
   - Sposta `_TEAM_LIMITS` da `routers/organizations.py` e `routers/billing.py` a `services/module_access.py:TEAM_LIMITS_BY_PLAN`.
   - Definisci `enforce_team_member_quota(org_id, current_count, pending=1)` in `module_access.py` che usa la costante centrale.
   - Routers usano l'helper.

4. **`ai_assistant.chat` quantity consistency**:
   - In `_count_monthly_usage` per `ai_assistant`, usa `$sum quantity` come `count_usage` (fix `background_service.py:480-490`).

**Test**:
- Confronto numerico: `/usage-summary` per ogni feature counter ritorna stesso numero che `check_module_access` userebbe (test diretto via script che chiama entrambi).
- Soft-delete prodotto Free: 199/200 visibile e gate accetta una creazione.

### Fase 9.Y.2 — `useEntitlements()` hook + i18n `body_by_feature` complete · ~5-7h

**Obiettivo**: ogni 403 mostra copy specifico + ogni azione gate-able è disabled client-side.

1. **Backend `/api/billing/entitlements`** (estensione di `/usage-summary`):
   ```json
   {
     "plan_slug": "free",
     "billing_status": "none",
     "limits": {
       "ai_assistant.chat": 3, "cashflow_monitor.data_rows": 200, ...
     },
     "usage": {
       "ai_assistant.chat": 0, "cashflow_monitor.data_rows": 145, ...
     },
     "flags": {
       "commerce.checkout_stripe": false, "cashflow_monitor.export": false, ...
     }
   }
   ```

2. **Frontend `useEntitlements.js`**:
   ```js
   export function useEntitlements() {
     const { data } = useSWR('/api/billing/entitlements', { refreshInterval: 60_000 });
     return {
       canUse: (moduleKey, featureKey) => { ... },
       getLimit: (moduleKey, featureKey) => { ... },
       getUsage: (moduleKey, featureKey) => { ... },
       isExhausted: (moduleKey, featureKey) => { ... },
     };
   }
   ```

3. **Aggiorna i 7 punti UI server-side-only (§1.3.C)** per usare `useEntitlements()`:
   - StoresPage, ProductsPage, OrdersPage, TeamPage, UploadPage (datasets), CashflowDataPage (export), PaymentConnectionsCard.

4. **i18n `module_paywall.body_by_feature.*` × 4 locale × 18 feature**:
   ```json
   "module_paywall": {
     "body_by_feature": {
       "checkout_stripe": "Per ricevere pagamenti con carta tramite Stripe Connect serve il piano Commerce Starter o superiore. Free e Solo gestiscono ordini come 'richiesta contatto'.",
       "export": "L'export Excel/CSV è disponibile dal piano Solo in poi. Aggiorna per scaricare i tuoi dati.",
       "email_alerts": "Le notifiche email per gli alert anomalie sono disponibili dal piano Solo.",
       "alert_analysis": "L'analisi AI degli alert è disponibile dal piano Commerce Starter.",
       "health_explanation": "La spiegazione AI dell'Health Score è disponibile dal piano Commerce Starter.",
       ...
     }
   }
   ```
   18 feature × 4 locale = 72 stringhe nuove.

5. **Bypass Excel toast bespoke**: `CashflowDataPage.js:39-44` rimuove il toast custom, lascia che `ModuleAccessPaywall` gestisca il 403.

**Test**:
- Per ognuna delle 18 feature, simula 403 → modal con copy specifico
- Free user vede bottoni disabled con tooltip su 7 azioni
- Tutti e 4 i locale validati

### Fase 9.Y.3 — Chiusura P2 (governance feature_key + AI Store) · ~4-6h

**Obiettivo**: nessun endpoint AI/storefront write è ungated.

1. **AI Store endpoints (B30-B35)** — 6 endpoint in `routers/ai_store.py`:
   - Decisione: ogni call consuma 1 unità di `ai_assistant.chat`. Aggiungi:
     ```python
     await check_module_access(org_id, "ai_assistant", "chat", pending_quantity=1)
     await record_module_usage(org_id, "ai_assistant", "chat", quantity=1)
     ```
   - Alternativa: nuovo `ai_assistant.store_setup` con limite generoso (free=10, starter=50, ...).

2. **Coupons** — nuova feature_key `commerce.coupons` (counter o flag):
   - Counter: free=0, starter=0, core=20, pro=100, enterprise=-1
   - Add gate in `routers/coupons.py:40` POST.
   - Aggiungi a matrice `seed_pricing.py`.

3. **Digital file storage** — nuova feature_key `product_catalog.digital_storage_mb`:
   - Counter MB: free=0, starter=0, core=500, pro=5000, enterprise=-1
   - Add gate in `routers/products.py:530` con `pending_quantity=file.size_mb`.

4. **Alert generation** — opzione: gate `POST /alerts/generate` con `cashflow_monitor.alert_config` o nuovo `alert_generation` (rate limit + plan).

5. **Customers/suppliers**: governance review — se rimane free-for-all, document esplicito; altrimenti nuova feature_key.

**Test**: estendi `run_payment_safety_tests.py` con scenari PMT-Z6...Z15 (uno per nuova feature_key gated).

### Fase 9.Y.4 — Helper canonico + GATE_REGISTRY + osservabilità · ~4-6h

**Obiettivo**: rendere il sistema dichiarativo + auto-difensivo.

1. **`module_access.GATE_REGISTRY`** (introdurre):
   ```python
   GATE_REGISTRY = {
     ("ai_assistant", "chat"): {"type": "counter_monthly"},
     ("ai_assistant", "digest"): {"type": "counter_monthly"},
     ("ai_assistant", "alert_analysis"): {"type": "flag"},
     ("ai_assistant", "health_explanation"): {"type": "flag"},
     ("cashflow_monitor", "data_rows"): {"type": "counter_monthly"},
     ("cashflow_monitor", "export"): {"type": "flag"},
     ("cashflow_monitor", "email_alerts"): {"type": "flag"},
     ("cashflow_monitor", "email_digest"): {"type": "flag"},
     ("cashflow_monitor", "alert_config"): {"type": "flag"},
     ("product_catalog", "products"): {"type": "counter_persistent", "count_fn": _count_products},
     ("commerce", "orders_monthly"): {"type": "counter_monthly"},
     ("commerce", "stores_max"): {"type": "counter_persistent", "count_fn": _count_stores},
     ("commerce", "checkout_stripe"): {"type": "flag"},
     ("commerce", "coupons"): {"type": "counter_persistent", "count_fn": _count_coupons},
     ("__hardcoded__", "team_members"): {"type": "counter_persistent", "count_fn": _count_team_members},
   }
   ```

2. **`enforce_feature_or_quota(module, feature, *, pending=1)`** unified helper.

3. **Decoratore `@billing_gated`** (opzionale ma consigliato):
   ```python
   @router.post("/sales")
   @billing_gated("cashflow_monitor", "data_rows")
   async def create_sale(...):
   ```

4. **Caching `get_effective_limit`**:
   - In-memory LRU per `(org_id, module, feature)` con TTL 30s. Invalidate on subscription change webhook.
   - Riduce 3+N query a 1 hit cache per gate.

5. **Index Mongo** verificato/creato:
   - `ai_usage_events`: compound `(organization_id, module_key, feature, created_at)`
   - `ai_usage_events`: TTL su `created_at` opzionale (es. 13 mesi) per evitare crescita unbounded.

6. **Startup integrity check**:
   - In `server.py` startup hook, scan tutti i router POST/PATCH/PUT/DELETE e verifica che ognuno appaia in una whitelist (gated o N/A esplicito). Log warning per orphans.

7. **TZ alignment**: `count_usage` usa `datetime.now(timezone.utc)` come `_count_monthly_usage`.

**Test**: gate_coverage_report.json al startup riporta `0 orphans` (eccetto whitelist N/A documentata).

---

## PARTE 3 — Acceptance criteria (fine 9.Y.4)

1. ✅ Per ogni endpoint POST/PATCH/PUT/DELETE in `backend/routers/`, il file `gate_coverage_report.json` marca **GATED** o **N/A**, mai **UNGATED**.
2. ✅ Per ogni (module, feature_key) della matrice §1.1 + team_members:
   - entry in `GATE_REGISTRY`
   - copy `body_by_feature.{key}` in 4 locale
   - test PMT-Z dedicato che verifica 429/403 al limite
3. ✅ Gate e dashboard `/usage-summary` ritornano lo stesso numero per ogni counter (consistency suite).
4. ✅ Free user NON riesce a:
   - inserire data oltre 200 righe (sales, expenses, purchases, fixed_costs, purchase_records, datasets, order_import)
   - completare Stripe Connect onboarding
   - aggiungere 2° team member
   - usare AI chat oltre 3, AI digest, alert_analysis, health_explanation, export Excel, email_alerts, alert_config, email_digest
   - creare prodotti, stores, ordini interni, coupons (oltre nuovo limit)
   - usare AI Store setup wizard senza counter
5. ✅ Per ogni azione bloccata l'utente vede:
   - bottone client-side disabled con tooltip esplicativo
   - se bypassato, paywall modal con copy specifico per feature in 4 locale
   - mai "[object Object]", mai 500 generico, mai toast generico
6. ✅ Pro user con `addon_orders_pack ×2` può creare 1400 ordini/mese.

---

## PARTE 4 — Approval gate

**Prima di iniziare 9.Y.0**, Davide rivede questo doc e:

- [ ] Conferma lista 14 gap §1.2.B (segnala feature mancanti?)
- [ ] Approva Fase 9.Y.0 (deploy in giornata, ~2-3h)
- [ ] Decide sequenza 9.Y.1 → 9.Y.4 (default: ordinata per severity)
- [ ] Conferma decisione su gate AI Store (counter `chat` esistente vs nuovo `store_setup`)
- [ ] Conferma decisione su `coupons` come counter (free=0, core=20, pro=100) vs flag
- [ ] Conferma `product_catalog.digital_storage_mb` come nuova feature
- [ ] Decide se backfill retroattivo `data_rows` events o "this month forward"
- [ ] Conferma se vuole il decoratore `@billing_gated` (più clean, refactor) o helper esplicito (no refactor)

Una volta approvato, partiamo da 9.Y.0.

---

## Appendice — File touched estimate

| File | Tipo modifica | Fase |
|---|---|---|
| `backend/routers/payment_connections.py` | +6 gate calls | 9.Y.0 |
| `backend/routers/purchase_records.py` | +1 gate + record | 9.Y.0 |
| `backend/services/order_import_service.py` | +2 gate + 2 record (bulk) | 9.Y.0 |
| `backend/routers/orders.py` | +1 gate (POS) | 9.Y.0 |
| `frontend/src/features/settings/PaymentConnectionsCard.js` | useBilling guard | 9.Y.0 |
| `backend/services/background_service.py` | unify data_rows source | 9.Y.1 |
| `backend/routers/products.py` | is_active filter | 9.Y.1 |
| `backend/services/module_access.py` | TEAM_LIMITS centralization, count_usage TZ fix | 9.Y.1 |
| `backend/routers/billing.py` | use central TEAM_LIMITS | 9.Y.1 |
| `backend/routers/organizations.py` | use central TEAM_LIMITS | 9.Y.1 |
| `backend/routers/billing.py` | NEW `/entitlements` endpoint | 9.Y.2 |
| `frontend/src/hooks/useEntitlements.js` | NEW | 9.Y.2 |
| `frontend/src/features/{stores,products,orders,team,datasets,cashflow,settings}/*` | useEntitlements consumers (~7 files) | 9.Y.2 |
| `frontend/src/locales/{it,en,de,fr}/settings.json` | +`module_paywall.body_by_feature.*` 18 keys × 4 = 72 | 9.Y.2 |
| `frontend/src/components/ModuleAccessPaywall.jsx` | (no change, uses keys) | 9.Y.2 |
| `frontend/src/features/cashflow/CashflowDataPage.js` | rimuovi toast bespoke | 9.Y.2 |
| `backend/routers/ai_store.py` | +6 gate + record | 9.Y.3 |
| `backend/routers/coupons.py` | +1 gate | 9.Y.3 |
| `backend/services/seed_pricing.py` | +`commerce.coupons`, `product_catalog.digital_storage_mb` | 9.Y.3 |
| `backend/routers/products.py` | digital_file gate | 9.Y.3 |
| `backend/services/module_access.py` | GATE_REGISTRY + helper + caching | 9.Y.4 |
| `backend/server.py` | startup integrity check | 9.Y.4 |
| `backend/database.py` | indices + TTL | 9.Y.4 |
| `backend/scripts/run_payment_safety_tests.py` | +PMT-Z series (~20 tests) | tutte |

**Totale file modificati**: ~22 backend + ~10 frontend. Tutti additivi, tutti git-revert sicuri.

---

## Appendice — Componenti frontend da rimuovere (cleanup)

`QuotaExceededBanner.js`, `UpgradePaywall.jsx`, `QuotaProgressBanner.jsx`: nessun caller, App.js commenta esplicitamente la rimozione. Possono essere cancellati in 9.Y.4 cleanup.
