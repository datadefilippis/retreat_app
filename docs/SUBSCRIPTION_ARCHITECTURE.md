# AFianco — Architettura Subscription 2D

> Documento tecnico completo: moduli, abbonamenti, logiche, DB, gap e roadmap.
> Aggiornato: 15 Marzo 2026

---

## 1. Modello concettuale

L'architettura subscription segue un modello **a due dimensioni**:

```
                    ┌─────────────────────────────────────────────────┐
                    │           Dimensione 2 — ORIZZONTALE            │
                    │              ai_assistant                       │
                    │   (chat, digest, alert_analysis, health_expl.)  │
                    └────────────────────┬────────────────────────────┘
                                         │ cross-module
    ┌──────────────┐    ┌──────────────┐ │ ┌──────────────┐
    │ cashflow_    │    │  (futuro)    │ │ │  (futuro)    │
    │ monitor      │    │  fatturaz.   │◄┤ │  magazzino   │
    │              │    │              │ │ │              │
    │ analytics    │    │              │ │ │              │
    │ data_rows    │    │              │ │ │              │
    │ export       │    │              │ │ │              │
    └──────────────┘    └──────────────┘   └──────────────┘
         Dimensione 1 — VERTICALE (dati + analytics per modulo)
```

- **Dim 1 (verticale)**: ogni modulo controlla i propri dati e analytics. Ogni modulo ha il proprio set di pricing plan.
- **Dim 2 (orizzontale)**: `ai_assistant` fornisce funzionalita AI cross-module (chat, digest, analisi anomalie, spiegazione health).

Ogni organizzazione ha **una subscription per modulo** (o ricade nel free tier).

---

## 2. Moduli attivi

### 2.1 `cashflow_monitor` (verticale)

| Feature Key | Tipo | Descrizione |
|---|---|---|
| `analytics` | Access flag | KPI, grafici, categorie, forecast, health, aging |
| `data_rows` | Usage metered | Righe dati inserite nel mese (vendite, spese, acquisti, costi fissi) |
| `export` | Access flag | Export report CSV/PDF |

### 2.2 `ai_assistant` (orizzontale)

| Feature Key | Tipo | Descrizione |
|---|---|---|
| `chat` | Usage metered | Messaggi chat AI per mese |
| `digest` | Usage metered | Generazioni digest (riassunto finanziario AI) per mese |
| `alert_analysis` | Access flag | Analisi AI root-cause sugli alert |
| `health_explanation` | Access flag | Spiegazione AI dello health score |

---

## 3. Pricing plan definiti

### 3.1 AI Assistant Plans

| Slug | Nome | Prezzo/mese | chat | digest | alert_analysis | health_explanation |
|---|---|---|---|---|---|---|
| `ai_assistant_free` | Free | €0 | 0 | 0 | 0 | 0 |
| `ai_assistant_starter` | AI Starter | €29 | 50 | 4 | -1 | -1 |
| `ai_assistant_pro` | AI Business | €79 | 300 | -1 | -1 | -1 |
| `ai_assistant_enterprise` | AI Enterprise | €199 | -1 | -1 | -1 | -1 |

### 3.2 Cashflow Monitor Plans

| Slug | Nome | Prezzo/mese | analytics | data_rows | export |
|---|---|---|---|---|---|
| `cashflow_monitor_free` | Free | €0 | -1 | 100 | 0 |
| `cashflow_monitor_pro` | Cashflow Pro | €29 | -1 | -1 | -1 |

### 3.3 Semantica dei limiti

| Valore | Significato |
|---|---|
| `-1` | Illimitato (feature accessibile, nessun conteggio) |
| `0` | Disabilitato (feature non disponibile) |
| `> 0` | Quota mensile (usage metering attivo) |

---

## 4. Struttura Database (MongoDB)

### 4.1 Collection Map

```
Database
├── organizations                  # Organizzazioni (tenant)
├── users                          # Utenti (legati a org)
├── organization_modules           # Attivazione moduli per org
├── pricing_plans                  # Piani tariffari per modulo [NEW v4.0]
├── module_subscriptions           # Sottoscrizioni org↔piano [NEW v4.0]
├── ai_usage_events                # Log usage append-only [NEW v3.0]
├── datasets                       # Dataset caricati
├── sales_records                  # Vendite
├── expense_records                # Spese
├── purchase_records               # Acquisti
├── fixed_costs                    # Costi fissi
├── customers                      # Clienti
├── suppliers                      # Fornitori
├── products                       # Prodotti
├── alerts                         # Alert generati
├── insights                       # Insight AI (deprecated, read-only)
├── digests                        # Digest AI
├── kpi_snapshots                  # Snapshot KPI pre-calcolati
├── audit_logs                     # Log audit admin
├── column_mappings                # Mappatura colonne dataset
├── dataset_column_profiles        # Profili colonne
├── data_validation_rules          # Regole validazione
├── module_configs                 # Config per-modulo per-org
└── temp_uploads                   # Upload temporanei (TTL)
```

### 4.2 Schema: `pricing_plans`

```json
{
  "_id": "ObjectId",
  "id": "string (UUID)",
  "module_key": "ai_assistant | cashflow_monitor",
  "slug": "ai_assistant_starter",
  "name": "AI Starter",
  "price_monthly": 29.0,
  "price_yearly": null,
  "currency": "EUR",
  "limits": {
    "chat": 50,
    "digest": 4,
    "alert_analysis": -1,
    "health_explanation": -1
  },
  "is_active": true,
  "sort_order": 1,
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime"
}
```

**Indici**:
- `module_key` (semplice)
- `(module_key, slug)` — unique

### 4.3 Schema: `module_subscriptions`

```json
{
  "_id": "ObjectId",
  "id": "string (UUID)",
  "organization_id": "string (FK → organizations.id)",
  "module_key": "ai_assistant",
  "pricing_plan_id": "string (FK → pricing_plans.id)",
  "status": "active | cancelled",
  "started_at": "ISO datetime",
  "expires_at": null,
  "cancelled_at": null,
  "assigned_by": "user_id | system_migration",
  "notes": "optional string",
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime"
}
```

**Indici**:
- `organization_id`
- `(organization_id, module_key, status)` — query rapida per entitlement
- `pricing_plan_id`

### 4.4 Schema: `ai_usage_events`

```json
{
  "_id": "ObjectId",
  "id": "string (UUID)",
  "organization_id": "string",
  "module_key": "ai_assistant | cashflow_monitor",
  "feature": "chat | digest | alert_analysis | data_rows | ...",
  "quantity": 1,
  "tokens_prompt": null,
  "tokens_completion": null,
  "created_at": "ISO datetime"
}
```

**Indici**:
- `organization_id`
- `(organization_id, feature, created_at)` — legacy
- `(organization_id, module_key, feature, created_at)` — primary query

**Nota**: Il campo `quantity` (default 1) permette di registrare bulk events (es. 50 righe inserite) come singolo documento, evitando 50 insert separati.

### 4.5 Schema: `organizations` (campi subscription-related)

```json
{
  "id": "string",
  "name": "string",
  "plan": "free | starter | pro | enterprise",
  "currency": "EUR",
  "timezone": "Europe/Rome",
  "is_active": true
}
```

**Nota**: il campo `plan` e il campo legacy. Usato come fallback quando non esiste una `module_subscription` esplicita per il modulo.

### 4.6 Schema: `organization_modules`

```json
{
  "id": "string",
  "organization_id": "string",
  "module_key": "cashflow_monitor",
  "is_active": true,
  "activated_at": "ISO datetime",
  "activated_by": "user_id"
}
```

**Indici**:
- `organization_id`
- `(organization_id, module_key)` — unique

---

## 5. Logica di risoluzione entitlement

### 5.1 Flusso `get_module_entitlements(org_id, module_key)`

```
1. Cerca module_subscription attiva:
   module_subscriptions.findOne({
     organization_id, module_key, status: "active"
   })

2. Se trovata → carica pricing_plan collegato:
   pricing_plans.findOne({ id: subscription.pricing_plan_id })
   → return { enabled: true, limits: plan.limits, plan_name, plan_slug }

3. Se NON trovata → fallback su organization.plan:
   slug = "{module_key}_{org.plan}"  (es. "ai_assistant_starter")
   pricing_plans.findOne({ module_key, slug })
   → Se trovato: return { enabled: true, limits: plan.limits }
   → Se non trovato: return { enabled: false, limits: {} }
```

### 5.2 Flusso `check_module_access(org_id, module_key, feature_key, pending_quantity=1)`

```
1. Chiama get_module_entitlements()

2. Se enabled == false → HTTP 403 MODULE_NOT_AVAILABLE

3. limit = limits[feature_key]
   - Se limit == 0 → HTTP 403 FEATURE_NOT_AVAILABLE
   - Se limit == -1 → OK (illimitato, no conteggio)
   - Se limit > 0:
     usage = count_usage(org_id, module_key, feature_key, period_start, period_end)
     Se usage + pending_quantity > limit → HTTP 429 QUOTA_EXCEEDED
     Altrimenti → OK
```

### 5.3 Conteggio usage

```python
# Pipeline di aggregazione MongoDB
pipeline = [
    {"$match": {
        "organization_id": org_id,
        "module_key": module_key,
        "feature": feature_key,
        "created_at": {"$gte": period_start, "$lte": period_end}
    }},
    {"$group": {
        "_id": None,
        "total": {"$sum": {"$ifNull": ["$quantity", 1]}}
    }}
]
```

- `period_start/end` = primo/ultimo giorno del mese corrente
- `$ifNull: ["$quantity", 1]` per backward compat con eventi legacy senza quantity

### 5.4 Registrazione usage

```python
# Singola riga
record_usage(org_id, "cashflow_monitor", "data_rows", quantity=1)

# Bulk (es. 50 righe da CSV)
record_usage(org_id, "cashflow_monitor", "data_rows", quantity=50)
# → 1 solo documento con quantity=50
```

---

## 6. Gating per feature — mappa completa

| Feature | File | Tipo gate | Comportamento se negato |
|---|---|---|---|
| Chat AI | `routers/chat.py` | Hard gate (`assert_ai_access`) | HTTP 403 |
| Digest | `routers/digests.py` | Hard gate (`assert_ai_access`) | HTTP 403 |
| Alert AI Analysis | `services/alert_service.py` | Soft gate (`can_use_ai`) | Alert creati senza AI analysis |
| Health Explanation | `routers/modules.py` | Soft gate (`can_use_ai`) | Fallback a spiegazione rule-based |
| Background Digest | `services/background_service.py` | Soft gate (`can_use_ai`) | Skip org silenziosamente |
| Data Rows | `routers/sales.py, expenses.py, purchases.py, fixed_costs.py, dataset_service.py` | Hard gate (`check_data_rows_quota`) | HTTP 429 |

**Hard gate**: blocca l'operazione con errore HTTP.
**Soft gate**: degrada gracefully (skip AI, usa fallback rule-based).

---

## 7. API endpoints subscription

### 7.1 Endpoints utente

| Method | Path | Descrizione |
|---|---|---|
| `GET` | `/ai/access-status` | Status AI: enabled, limits, usage, plan |
| `GET` | `/modules/available` | Lista moduli disponibili per l'org |
| `GET` | `/modules/{module_key}/status` | Status specifico del modulo |

### 7.2 Endpoints admin (system_admin only)

| Method | Path | Descrizione |
|---|---|---|
| `GET` | `/admin/pricing-plans` | Lista pricing plan (filtrabile per module_key) |
| `GET` | `/admin/organizations/{org_id}/subscriptions` | Subscriptions attive dell'org |
| `PUT` | `/admin/organizations/{org_id}/subscriptions/{module_key}` | Assegna piano a org+modulo |
| `DELETE` | `/admin/organizations/{org_id}/subscriptions/{module_key}` | Cancella subscription (fallback a free) |
| `PUT` | `/admin/organizations/{org_id}/plan` | Aggiorna campo legacy org.plan |

### 7.3 Endpoints deprecati

| Method | Path | Status | Nota |
|---|---|---|---|
| `POST` | `/insights/generate` | **410 Gone** | Sostituito da `/digests/generate` |

---

## 8. Frontend: componenti subscription-aware

| Componente | File | Logica |
|---|---|---|
| **useAiAccess** hook | `hooks/useAiAccess.js` | Context globale: `canUse(feature)`, `quotaExhausted(feature)` |
| **SettingsPage** | `features/settings/SettingsPage.js` | 4 meter AI: Chat, Digest, Analisi Anomalie, Health AI |
| **DigestTab** | `features/cashflow/components/DigestTab.js` | `canUse('digest')` per bottone genera |
| **HealthScoreGauge** | `features/cashflow/components/HealthScoreGauge.js` | `canUse('health_explanation')` per AI explain |
| **ChatWidget** | `features/cashflow/components/ChatWidget.js` | `canUse('chat')` per invio messaggi |
| **InlineChat** | `features/cashflow/components/InlineChat.js` | `canUse('chat')` per invio messaggi |
| **UpgradeDialog** | `components/UpgradeDialog.js` | Dialog placeholder (no Stripe), CTA "Contattaci" |
| **InsightsPage** | `features/insights/InsightsPage.js` | Read-only archive, banner "Usa Digest" |
| **Admin OrganizationsTab** | `features/admin/OrganizationsTab.js` | CRUD subscription per org (system admin) |

---

## 9. Flusso di vita di una subscription

```
1. System admin assegna piano:
   PUT /admin/organizations/{org_id}/subscriptions/ai_assistant
   body: { "pricing_plan_id": "xxx" }

2. Backend:
   a. Cancella subscription precedente (se esiste) → status="cancelled"
   b. Crea nuova subscription → status="active"
   c. Log audit: admin_set_subscription

3. Utente usa feature:
   POST /ai/chat
   → assert_ai_access(org_doc, "chat")
   → get_module_entitlements() → limits.chat = 50
   → count_usage() → usage = 12
   → 12 + 1 <= 50 → OK
   → ... risposta AI ...
   → record_event(org_id, "chat") → usage diventa 13

4. Quota esaurita:
   POST /ai/chat
   → count_usage() → usage = 50
   → 50 + 1 > 50 → HTTP 429 QUOTA_EXCEEDED

5. Reset mensile:
   Il conteggio e basato su date (first/last of month).
   Nessun cron job — il primo del mese, count_usage() ritorna 0 per il nuovo periodo.
```

---

## 10. Inizializzazione server (startup)

```python
# server.py — lifespan
1. ensure_indexes()                    # Crea indici MongoDB
2. seed_pricing_plans_if_empty()       # Seed piani se collection vuota
3. migrate_pricing_plans()             # Allinea limiti piani esistenti ai seed
4. backfill_module_key()               # Migra usage events legacy
5. start background_service            # Alert periodici
```

---

## 11. GAP per Go-Live

### 11.1 CRITICO — Pagamenti e billing

| Gap | Descrizione | Effort stimato |
|---|---|---|
| **Integrazione Stripe** | Nessun sistema di pagamento integrato. Tutto e manuale via admin. Serve: Stripe Checkout/Customer Portal, webhooks per attivare/disattivare subscription automaticamente. | Alto |
| **Webhook handler** | Endpoint per ricevere eventi Stripe (payment_succeeded, subscription_cancelled, invoice_paid). Deve aggiornare module_subscriptions automaticamente. | Alto |
| **Billing period tracking** | expires_at e sempre null. Serve logica di scadenza reale legata al ciclo di billing Stripe. | Medio |
| **Fatturazione/ricevute** | Nessun sistema di generazione fatture. Da valutare se delegare a Stripe Billing o integrare servizio terzo. | Medio |
| **Prezzi annuali** | Campo `price_yearly` presente nel model ma mai usato. Serve UI e logica monthly/yearly switch. | Basso |

### 11.2 IMPORTANTE — Funzionalita mancanti

| Gap | Descrizione | Effort |
|---|---|---|
| **Self-service upgrade** | L'utente non puo cambiare piano da solo. `UpgradeDialog` e un placeholder che apre una mail. Serve un flusso self-service collegato a Stripe. | Alto |
| **Export (feature_key `export`)** | Gating definito ma funzionalita export CSV/PDF non implementata. Nessun endpoint di export. | Medio |
| **Pricing page pubblica** | Nessuna pagina pubblica con comparazione piani e CTA. Serve per conversione. | Medio |
| **Trial period** | Nessun supporto trial. Il model non ha campo trial_ends_at. | Medio |
| **Downgrade flow** | Cosa succede quando un org passa da Pro a Free con >100 righe? Nessuna logica di data retention/archivio. | Medio |
| **Usage dashboard per utente** | SettingsPage mostra solo metriche AI. Manca: usage data_rows, storico mensile, grafici. | Basso |
| **Email notifications** | Nessuna notifica quando quota sta per esaurirsi (es. 80% usage) o quando subscription scade. | Medio |
| **CRUD pricing plans (admin)** | Admin puo solo assegnare piani, non crearli/modificarli da UI. Solo seed + migration via codice. | Basso |

### 11.3 MIGLIORAMENTI — Nice to have

| Gap | Descrizione | Effort |
|---|---|---|
| **Multi-currency pricing** | Piani definiti solo in EUR. Servirebbero prezzi localizzati. | Basso |
| **Coupon/sconti** | Nessun supporto coupon o sconti promozionali. | Medio (con Stripe) |
| **Usage analytics (admin)** | L'admin non vede statistiche aggregate: MRR, churn, usage trends. | Medio |
| **Rate limiting** | Nessun rate limiting HTTP sugli endpoint AI (solo quota mensile). | Basso |
| **Graceful degradation UI** | Quando quota e esaurita, la UI mostra errore generico. Serve UX dedicata con upsell. | Basso |
| **Moduli futuri** | Architettura pronta ma nessun altro modulo verticale definito (fatturazione, magazzino, HR). | Futuro |
| **UpgradeDialog aggiornamento** | Il dialog mostra ancora "Insights" e valori vecchi. Da allineare ai nuovi 4 feature_key e ai piani reali. | Basso |

### 11.4 TECNICO — Debito tecnico

| Gap | Descrizione | Effort |
|---|---|---|
| **Campo legacy `organization.plan`** | Usato come fallback. Da rimuovere quando tutte le org hanno module_subscriptions esplicite. | Basso |
| **Doppio repository usage** | `usage_repository.py` (module-aware) e `ai_usage_repository.py` (legacy). Consolidare. | Basso |
| **Test automatici** | Nessun test unitario/integrazione per logiche subscription e gating. | Medio |
| **Idempotenza bulk insert** | Se insert va a buon fine ma record_usage fallisce, la quota e disallineata. Serve transazione o compensazione. | Basso |
| **Monitoraggio usage events** | Nessun alerting se la collection ai_usage_events cresce troppo. Serve TTL o archiviazione. | Basso |

---

## 12. Roadmap proposta

### Fase A — Foundation (2 settimane)
1. Test automatici per logiche subscription (pytest)
2. Consolidare ai_usage_repository in usage_repository
3. Aggiornare UpgradeDialog con nuovi feature_key
4. Implementare export CSV base (feature_key `export`)

### Fase B — Stripe Integration (3-4 settimane)
1. Setup Stripe account + API keys
2. Stripe Products + Prices (mappati 1:1 ai pricing_plans)
3. Stripe Checkout Session per upgrade self-service
4. Webhook handler: `checkout.session.completed` → crea module_subscription
5. Webhook handler: `customer.subscription.deleted` → cancella subscription
6. Stripe Customer Portal per gestione carta/fatture
7. Rimuovere placeholder UpgradeDialog, sostituire con redirect a Checkout

### Fase C — Self-Service UX (2 settimane)
1. Pricing page pubblica (/pricing)
2. In-app upgrade button con redirect a Stripe Checkout
3. Usage dashboard esteso (data_rows, storico, grafici)
4. Email notifiche: quota 80%, quota esaurita, subscription scaduta
5. Downgrade flow: warning + data archival policy

### Fase D — Polish & Scale (1-2 settimane)
1. Trial period (7/14 giorni) con auto-downgrade
2. Rimuovere campo legacy `organization.plan`
3. Admin analytics: MRR, active subscriptions, churn
4. Rate limiting endpoint AI
5. Monitoring + alerting usage events

---

## 13. Variabili ambiente rilevanti

| Variabile | Dove | Descrizione |
|---|---|---|
| `MONGO_URL` | backend/.env | Connection string MongoDB |
| `DB_NAME` | backend/.env | Nome database |
| `OPENAI_API_KEY` | backend/.env | Per chat AI, digest, health explanation |
| `BACKGROUND_ALERT_INTERVAL_HOURS` | env (default 6) | Intervallo background alert check |
| `BACKGROUND_INITIAL_DELAY_SECONDS` | env (default 30) | Delay iniziale background service |

**Variabili da aggiungere per Stripe**:
| Variabile | Descrizione |
|---|---|
| `STRIPE_SECRET_KEY` | API key Stripe (server-side) |
| `STRIPE_PUBLISHABLE_KEY` | API key Stripe (client-side) |
| `STRIPE_WEBHOOK_SECRET` | Signing secret per validare webhook |
| `STRIPE_PRICE_ID_*` | Mapping slug → Stripe Price ID |

---

## 14. Diagramma flusso completo

```
 Utente           Frontend              Backend                  MongoDB
   │                  │                     │                       │
   │─ Usa feature ──►│                     │                       │
   │                  │─ POST /ai/chat ───►│                       │
   │                  │                     │─ get_module_          │
   │                  │                     │  entitlements() ────►│
   │                  │                     │                       │─ find subscription
   │                  │                     │                       │─ find pricing_plan
   │                  │                     │◄─ {limits, plan} ────│
   │                  │                     │                       │
   │                  │                     │─ check_module_        │
   │                  │                     │  access("chat") ───►│
   │                  │                     │                       │─ aggregate usage
   │                  │                     │◄─ usage=12 ──────────│
   │                  │                     │                       │
   │                  │                     │  12+1 <= 50 → OK     │
   │                  │                     │                       │
   │                  │                     │─ OpenAI call ───────►│ (esterno)
   │                  │                     │◄─ risposta AI ───────│
   │                  │                     │                       │
   │                  │                     │─ record_event() ───►│
   │                  │                     │                       │─ insert usage doc
   │                  │◄─ risposta ─────────│                       │
   │◄─ render ────────│                     │                       │
```

---

## 15. File chiave — indice rapido

| Area | File | Ruolo |
|---|---|---|
| **Models** | `backend/models/pricing_plan.py` | Schema PricingPlan |
| | `backend/models/subscription.py` | Schema ModuleSubscription |
| | `backend/models/ai_usage.py` | Schema AIUsageEvent |
| | `backend/models/module.py` | Schema OrganizationModule |
| **Repos** | `backend/repositories/subscription_repository.py` | CRUD plans + subscriptions |
| | `backend/repositories/usage_repository.py` | count_usage, record_usage (module-aware) |
| | `backend/repositories/ai_usage_repository.py` | Legacy usage repo (da consolidare) |
| **Services** | `backend/services/module_access.py` | Entitlement engine generico |
| | `backend/services/ai_access.py` | Wrapper AI module |
| | `backend/services/cashflow_access.py` | Wrapper cashflow module |
| | `backend/services/seed_pricing.py` | Seed + migrazione piani |
| **Routers** | `backend/routers/admin.py` | Admin API (subscription CRUD) |
| | `backend/routers/chat.py` | Chat AI con gating |
| | `backend/routers/digests.py` | Digest con gating |
| | `backend/routers/insights.py` | Insights (deprecated 410) |
| **Frontend** | `frontend/src/hooks/useAiAccess.js` | Context globale AI access |
| | `frontend/src/components/UpgradeDialog.js` | Placeholder upgrade |
| | `frontend/src/features/settings/SettingsPage.js` | Usage meters |
| | `frontend/src/features/admin/OrganizationsTab.js` | Admin subscription UI |
| **Config** | `backend/database.py` | Collection definitions + indexes |
| | `backend/server.py` | Startup: seed, migrate, backfill |
