# AFianco — System Specification Document
**Versione:** 2.1 (Cashflow Monitor v2)
**Data:** 2026-03-12
**Scopo:** Mapping completo dello stato attuale del sistema per onboarding AI agent

---

## INDICE

1. [Panoramica del Sistema](#1-panoramica-del-sistema)
2. [Stack Tecnologico](#2-stack-tecnologico)
3. [Database — MongoDB](#3-database--mongodb)
4. [Autenticazione e Sicurezza](#4-autenticazione-e-sicurezza)
5. [Data Models — Pydantic](#5-data-models--pydantic)
6. [Backend — API Endpoints](#6-backend--api-endpoints)
7. [Backend — Servizi e Repository](#7-backend--servizi-e-repository)
8. [Modulo: Cashflow Monitor](#8-modulo-cashflow-monitor)
9. [Frontend — Architettura React](#9-frontend--architettura-react)
10. [Frontend — Cashflow Monitor UI](#10-frontend--cashflow-monitor-ui)
11. [Upload Dati e Inserimento Manuale](#11-upload-dati-e-inserimento-manuale)
12. [Variabili d'Ambiente](#12-variabili-dambiente)
13. [Scalabilità e Performance](#13-scalabilità-e-performance)
14. [Data Flow End-to-End](#14-data-flow-end-to-end)

---

## 1. Panoramica del Sistema

**AFianco** è una piattaforma SaaS di Business Intelligence per PMI. Permette a un imprenditore di caricare dati aziendali (vendite, spese, acquisti, costi fissi), monitorare il cashflow in tempo reale, ricevere alert automatici sulle anomalie e generare insight narrativi tramite AI.

**Architettura:**
```
Browser (React 19)
    ↕ HTTPS / REST JSON
FastAPI (Python) — port 8000
    ↕ Motor (async)
MongoDB Atlas (cloud) o locale
```

**Multi-tenancy:** completa — ogni dato è isolato da `organization_id`. Un'organizzazione può avere più utenti (admin + user).

**Moduli attivabili per org:** sistema modulare a registry. Attualmente un solo modulo implementato: `cashflow_monitor`.

---

## 2. Stack Tecnologico

### Backend
| Componente | Tecnologia | Note |
|---|---|---|
| Framework | FastAPI 0.104 | Async, OpenAPI auto-generato |
| Runtime | Python 3.12+ | Uvicorn ASGI server |
| ORM/ODM | Motor (AsyncIO) | Driver async per MongoDB |
| Auth | python-jose + passlib | JWT HS256 + bcrypt |
| Validation | Pydantic v2 | Tutti i modelli I/O |
| File Parsing | pandas + openpyxl | CSV, XLSX, XLS |
| AI | Anthropic SDK | Claude client (chat + digest narrative) |
| Storage locale | backend/uploads/ | fallback sempre attivo |
| Storage cloud | AWS S3 (opzionale) | non-blocking, dual-write |

### Frontend
| Componente | Tecnologia | Note |
|---|---|---|
| Framework | React 19 | Automatic batching |
| Build | Craco + CRA | Webpack con alias @/ |
| Routing | React Router v7 | Protected routes |
| UI Components | Radix UI + Shadcn | Primitive accessibili |
| Styling | Tailwind CSS 3 | |
| Charts | Recharts 3 | Line, Area, Bar, Pie |
| HTTP | Axios 1.8 | Interceptors per auth |
| Forms | React Hook Form + Zod | Validazione client-side |
| Toast | Sonner 2 | |
| Icons | Lucide React | |

### Database
| Componente | Tecnologia | Note |
|---|---|---|
| DB | MongoDB 7.0 | Atlas cloud o locale |
| Driver | Motor 3 | Async per FastAPI |
| Modello | Document-based | Multi-collection, indexed |

---

## 3. Database — MongoDB

### 3.1 Connessione e Configurazione

```python
# backend/database.py
client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
```

Il database si chiama tipicamente `bi_pmi`. Tutti gli index sono creati all'avvio (`create_indexes()` in lifespan).

---

### 3.2 Collections — Legacy (immutabili)

Queste collections esistono dalla v1 e **non vanno mai rinominate**.

| Collection | Scopo | Chiave di partizione |
|---|---|---|
| `organizations` | Entità organizzazione | `id` |
| `users` | Utenti con hash password | `email` (unique), `organization_id` |
| `datasets` | Metadati file caricati | `organization_id`, `dataset_type` |
| `sales_records` | Transazioni di vendita | `organization_id`, `date` |
| `expense_records` | Transazioni di spesa | `organization_id`, `date` |
| `organization_modules` | Stato attivazione moduli | `organization_id`, `module_key` |
| `alerts` | Anomalie rilevate | `organization_id`, `status`, `severity` |
| `insights` | Analisi AI generate | `organization_id`, `module_key` |
| `audit_logs` | Log operazioni sensibili | `organization_id`, `created_at` |

---

### 3.3 Collections — Phase-1 (additive, zero breaking change)

Aggiunte nella v2. Non esistevano in v1.

| Collection | Scopo | Chiave di partizione |
|---|---|---|
| `customers` | Anagrafica clienti | `organization_id`, `external_id` |
| `suppliers` | Anagrafica fornitori | `organization_id`, `external_id` |
| `products` | Catalogo prodotti | `organization_id`, `sku` |
| `purchase_records` | Acquisti da fornitori | `organization_id`, `date`, `supplier_name` |
| `fixed_costs` | Costi fissi ricorrenti | `organization_id`, `is_active`, `category` |
| `column_mappings` | Regole mapping colonne file→DB | `organization_id`, `dataset_type` |
| `dataset_column_profiles` | Profili statistici colonne per dataset | `dataset_id` (unique) |
| `data_validation_rules` | Regole validazione su upload | `organization_id`, `dataset_type` |
| `kpi_snapshots` | KPI pre-calcolati per periodo | `(org_id, module_key, period_start)` unique |
| `module_configs` | Config per-modulo per org | `(organization_id, module_key)` unique |
| `schema_versions` | Tracking versioni schema DB | `collection_name` (unique) |

---

### 3.4 Index Completi

```python
# Users
users.email                                             (unique)
users.organization_id

# Datasets
datasets.organization_id
datasets.[organization_id, dataset_type]

# Sales Records
sales_records.organization_id
sales_records.[organization_id, date]
sales_records.dataset_id
sales_records.[organization_id, category]               # Phase-1 aggiunto

# Expense Records
expense_records.organization_id
expense_records.[organization_id, date]
expense_records.dataset_id
expense_records.[organization_id, category]             # Phase-1 aggiunto

# Organization Modules
organization_modules.organization_id
organization_modules.[organization_id, module_key]      (unique)

# Alerts
alerts.organization_id
alerts.[organization_id, status]
alerts.[organization_id, created_at DESC]
alerts.[organization_id, severity, status]              # Phase-1 aggiunto

# Insights
insights.organization_id
insights.[organization_id, created_at DESC]
insights.[organization_id, module_key, created_at DESC] # Phase-1 aggiunto

# Audit Logs
audit_logs.organization_id
audit_logs.[organization_id, created_at DESC]

# Customers
customers.organization_id
customers.[organization_id, external_id]                (unique, sparse)
customers.[organization_id, name]

# Suppliers
suppliers.organization_id
suppliers.[organization_id, external_id]                (unique, sparse)
suppliers.[organization_id, name]

# Products
products.organization_id
products.[organization_id, sku]                         (unique, sparse)
products.[organization_id, category]

# Purchase Records
purchase_records.organization_id
purchase_records.[organization_id, date]
purchase_records.[organization_id, supplier_id]
purchase_records.dataset_id
purchase_records.[organization_id, supplier_name]

# Fixed Costs
fixed_costs.organization_id
fixed_costs.[organization_id, is_active]
fixed_costs.[organization_id, category]
fixed_costs.dataset_id

# Column Mappings
column_mappings.organization_id
column_mappings.[organization_id, dataset_type]

# Dataset Column Profiles
dataset_column_profiles.organization_id
dataset_column_profiles.dataset_id                      (unique)

# Data Validation Rules
data_validation_rules.organization_id
data_validation_rules.[organization_id, dataset_type, is_active]

# KPI Snapshots
kpi_snapshots.organization_id
kpi_snapshots.[organization_id, module_key, period_start] (unique)
kpi_snapshots.[organization_id, created_at DESC]

# Module Configs
module_configs.[organization_id, module_key]            (unique)

# Schema Versions
schema_versions.collection_name                         (unique)
schema_versions.[applied_at DESC]
```

---

## 4. Autenticazione e Sicurezza

### 4.1 Meccanismo JWT

**File:** `backend/auth.py`

```
Algorithm:      HS256
Secret:         JWT_SECRET_KEY (env var, required)
Expiration:     7 giorni (60*24*7 minuti)
Transport:      HTTP Authorization: Bearer <token>
```

**Payload claims:**
```json
{
  "sub":    "user_id (UUID)",
  "org_id": "organization_id (UUID)",
  "role":   "admin | user",
  "email":  "user@example.com",
  "exp":    1234567890
}
```

### 4.2 Password Hashing

```python
# passlib bcrypt
get_password_hash(password: str) -> str
verify_password(plain: str, hashed: str) -> bool
```

### 4.3 FastAPI Dependencies

```python
# Iniettabili nei router come Depends()
get_current_user(credentials: HTTPAuthorizationCredentials) -> dict
  # Verifica token, ritorna {user_id, organization_id, role, email}

require_admin(current_user: dict) -> dict
  # Verifica role == "admin", altrimenti 403
```

### 4.4 Multi-tenancy e Isolamento Dati

**Ogni query al DB include `organization_id` come filtro obbligatorio.** Nessun endpoint espone dati cross-tenant. L'`org_id` viene estratto dal token JWT, non dal body della request.

### 4.5 CORS

```python
allow_origins: os.environ.get('CORS_ORIGINS', '*').split(',')
allow_credentials: True
allow_methods: ["*"]
allow_headers: ["*"]
```

In produzione, `CORS_ORIGINS` deve essere impostato esplicitamente (non `*`).

### 4.6 Audit Logging

La collection `audit_logs` traccia operazioni sensibili. Schema:
```json
{
  "organization_id": "...",
  "user_id": "...",
  "action": "...",
  "resource": "...",
  "created_at": "..."
}
```

---

## 5. Data Models — Pydantic

### 5.1 User & Organization

```python
class UserRole(str, Enum):
    ADMIN = "admin"
    USER  = "user"

class User(BaseModel):
    id:              str           # auto UUID
    email:           EmailStr      # unique nel DB
    name:            str
    role:            UserRole = UserRole.USER
    password_hash:   str
    organization_id: str
    created_at:      datetime
    updated_at:      datetime
    is_active:       bool = True
    last_login_at:   Optional[datetime]
    preferences:     Optional[Dict[str, Any]]
    mfa_enabled:     Optional[bool]

class Organization(BaseModel):
    id:                  str
    name:                str
    industry:            Optional[str]
    created_at:          datetime
    updated_at:          datetime
    plan:                Optional[str]       # free|starter|pro|enterprise
    data_classification: Optional[str]       # internal|confidential|restricted
    timezone:            Optional[str]       # IANA (es. Europe/Rome)
    currency:            Optional[str]       # ISO 4217 (es. EUR)
    settings:            Optional[Dict[str, Any]]
```

### 5.2 Dataset

```python
class DatasetType(str, Enum):
    SALES       = "sales"
    EXPENSES    = "expenses"
    PURCHASES   = "purchases"
    FIXED_COSTS = "fixed_costs"

class Dataset(BaseModel):
    id:                str
    name:              str
    dataset_type:      DatasetType
    organization_id:   str
    file_path:         str
    uploaded_by:       str
    row_count:         int = 0
    is_active:         bool = True
    created_at:        datetime
    original_filename: Optional[str]
    schema_version:    Optional[str]         # "2.0" per upload recenti
    source_type:       Optional[str]         # file_upload|api|manual
    tags:              Optional[List[str]]
    s3_key:            Optional[str]         # se caricato su S3
```

### 5.3 Sales Record

```python
class SalesRecord(BaseModel):
    id:               str
    organization_id:  str
    dataset_id:       str
    date:             str              # ISO: "2026-03-12"
    amount:           float
    category:         Optional[str]    # es. food_sales, beverage_sales
    description:      Optional[str]
    channel:          Optional[str]    # dine_in|takeout|delivery|catering
    source_record_id: Optional[str]    # row ID nel CSV originale
    customer_id:      Optional[str]    # FK → customers
    product_id:       Optional[str]    # FK → products
    payment_status:   Optional[str]    # paid|pending|overdue
    payment_date:     Optional[str]    # data incasso effettivo
    tags:             Optional[List[str]]
```

### 5.4 Expense Record

```python
class ExpenseRecord(BaseModel):
    id:               str
    organization_id:  str
    dataset_id:       str
    date:             str
    amount:           float
    category:         Optional[str]    # ingredients|utilities|staff|rent|supplies|marketing
    description:      Optional[str]
    supplier:         Optional[str]    # nome fornitore (stringa libera)
    source_record_id: Optional[str]
    supplier_id:      Optional[str]    # FK → suppliers
    product_id:       Optional[str]    # FK → products
    is_fixed:         Optional[bool]   # se è un costo fisso
    is_paid:          Optional[bool]
    payment_date:     Optional[str]
    tags:             Optional[List[str]]
```

### 5.5 Purchase Record

```python
class PaymentStatus(str, Enum):
    PENDING   = "pending"
    PAID      = "paid"
    OVERDUE   = "overdue"
    CANCELLED = "cancelled"

class PurchaseRecord(BaseModel):
    id:              str
    organization_id: str
    dataset_id:      Optional[str]     # None se inserimento manuale
    date:            str
    supplier_name:   str               # obbligatorio
    quantity:        float
    unit:            str = "kg"        # kg|pezzi|litri|etc
    unit_price:      float
    total_price:     float             # = quantity * unit_price
    category:        Optional[str]     # carni|frutta_verdura|bevande|etc
    description:     Optional[str]
    payment_status:  PaymentStatus = PaymentStatus.PENDING
    due_date:        Optional[str]
    metadata:        Dict[str, Any] = {}
    created_at:      datetime
```

### 5.6 Fixed Cost

```python
class FixedCostFrequency(str, Enum):
    MENSILE     = "mensile"
    SETTIMANALE = "settimanale"
    TRIMESTRALE = "trimestrale"
    ANNUALE     = "annuale"

class FixedCostCategory(str, Enum):
    AFFITTO      = "affitto"
    STIPENDIO    = "stipendio"
    FINANZIAMENTO = "finanziamento"
    LEASING      = "leasing"
    ABBONAMENTO  = "abbonamento"
    ALTRO        = "altro"

class FixedCost(BaseModel):
    id:              str
    organization_id: str
    dataset_id:      Optional[str]     # None se inserimento manuale
    name:            str               # es. "Affitto locale"
    category:        str               # valori FixedCostCategory o custom
    amount:          float             # importo per occorrenza
    frequency:       str               # valori FixedCostFrequency
    start_date:      str               # ISO date: da quando è attivo
    end_date:        Optional[str]     # ISO date: scadenza (None = perpetuo)
    is_active:       bool = True
    created_at:      datetime
    updated_at:      datetime
```

### 5.7 Master Data

```python
class Customer(BaseModel):
    id:              str
    organization_id: str
    name:            str
    external_id:     Optional[str]    # ID nel sistema sorgente
    email:           Optional[str]
    phone:           Optional[str]
    address:         Optional[str]
    tags:            List[str] = []
    metadata:        Dict[str, Any] = {}
    is_active:       bool = True
    created_at:      datetime
    updated_at:      datetime

class Supplier(BaseModel):
    id:              str
    organization_id: str
    name:            str
    external_id:     Optional[str]
    email:           Optional[str]
    phone:           Optional[str]
    address:         Optional[str]
    category:        Optional[str]
    tags:            List[str] = []
    metadata:        Dict[str, Any] = {}
    is_active:       bool = True
    created_at:      datetime
    updated_at:      datetime

class Product(BaseModel):
    id:              str
    organization_id: str
    name:            str
    sku:             Optional[str]     # codice articolo (unique per org)
    category:        Optional[str]
    unit_price:      Optional[float]
    unit:            Optional[str]
    tags:            List[str] = []
    metadata:        Dict[str, Any] = {}
    is_active:       bool = True
    created_at:      datetime
    updated_at:      datetime
```

### 5.8 Alert & Insight

```python
class AlertSeverity(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"

class AlertStatus(str, Enum):
    NEW          = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED     = "resolved"

class Alert(BaseModel):
    id:               str
    organization_id:  str
    module_key:       str              # es. "cashflow_monitor"
    severity:         AlertSeverity
    status:           AlertStatus = AlertStatus.NEW
    title:            str
    summary:          str
    date_reference:   str             # ISO date a cui si riferisce l'anomalia
    metric_payload:   Dict[str, Any]  # dati numerici dell'anomalia
    created_at:       datetime
    acknowledged_at:  Optional[datetime]
    resolved_at:      Optional[datetime]
    schema_version:   Optional[str]
    auto_resolved:    Optional[bool]
    resolution_note:  Optional[str]

class Insight(BaseModel):
    id:               str
    organization_id:  str
    module_key:       str
    title:            str
    content:          str             # testo Markdown generato da AI
    metrics_context:  Dict[str, Any]  # snapshot KPI usati per il prompt
    created_at:       datetime
    period_start:     str
    period_end:       str
    schema_version:   Optional[str]   # "2.0"
    model_version:    Optional[str]   # "gpt-4o" | "fallback"
    confidence_score: Optional[float] # 0.0–1.0
```

### 5.9 Configuration Models

```python
class ColumnMapping(BaseModel):
    id:              str
    organization_id: str
    dataset_type:    str           # sales|expenses|purchases|fixed_costs
    source_column:   str           # nome colonna nel file
    target_field:    str           # campo canonico nel DB
    transform:       Optional[str] # regola trasformazione (es. strip, lowercase)
    is_active:       bool = True
    created_at:      datetime
    updated_at:      datetime

class ValidationRuleType(str, Enum):
    REQUIRED         = "required"
    MIN_VALUE        = "min_value"
    MAX_VALUE        = "max_value"
    DATE_RANGE       = "date_range"
    CATEGORY_WHITELIST = "category_whitelist"
    REGEX            = "regex"

class DataValidationRule(BaseModel):
    id:              str
    organization_id: str
    dataset_type:    str
    field_name:      str
    rule_type:       ValidationRuleType
    rule_value:      Optional[Any]      # es. 0 per min_value
    error_message:   Optional[str]
    is_active:       bool = True
    created_at:      datetime
    updated_at:      datetime

class KPISnapshot(BaseModel):
    id:              str
    organization_id: str
    module_key:      str
    period_start:    str               # ISO date
    period_end:      str
    granularity:     str = "monthly"
    metrics:         Dict[str, Any]    # vedi sezione KPI
    metadata:        Optional[Dict[str, Any]]
    created_at:      datetime
    schema_version:  str = "1.0"
```

---

## 6. Backend — API Endpoints

### 6.1 Autenticazione `/api/auth/*`

| Method | Path | Auth | Body | Response |
|---|---|---|---|---|
| POST | `/api/auth/signup` | No | `{email, password, name, organization_name?}` | `TokenResponse` |
| POST | `/api/auth/login` | No | `{email, password}` | `TokenResponse` |
| GET | `/api/auth/me` | Bearer | — | `UserResponse` |

```json
// TokenResponse
{
  "access_token": "eyJ...",
  "token_type":   "bearer",
  "user": {
    "id":              "...",
    "email":           "admin@demo.com",
    "name":            "Demo Admin",
    "role":            "admin",
    "organization_id": "...",
    "created_at":      "...",
    "is_active":       true
  }
}
```

### 6.2 Analytics KPI `/api/analytics/*`

Tutti richiedono Bearer token. L'`organization_id` viene estratto dal JWT.

| Method | Path | Query Params | Response |
|---|---|---|---|
| GET | `/api/analytics/kpis` | `period`, `start_date`, `end_date` | `KPIData` |
| GET | `/api/analytics/charts` | `period`, `start_date`, `end_date` | `List[ChartDataPoint]` |
| GET | `/api/analytics/summary` | `period`, `start_date`, `end_date` | `SummaryData` |
| GET | `/api/analytics/date-range` | — | `DateRangeInfo` |
| GET | `/api/analytics/categories/sales` | `period`, `start_date`, `end_date` | `CategoryData` |
| GET | `/api/analytics/categories/expenses` | `period`, `start_date`, `end_date` | `CategoryData` |
| GET | `/api/analytics/categories/purchases` | `period`, `start_date`, `end_date` | `CategoryData` |
| GET | `/api/analytics/categories/trends` | `period`, `start_date`, `end_date` | `TrendsData` |
| GET | `/api/analytics/cashflow/enriched-kpis` | `period`, `start_date`, `end_date` | `EnrichedKPIData` |
| GET | `/api/analytics/cashflow/cumulative` | `period`, `start_date`, `end_date` | `List[CumulativePoint]` |
| GET | `/api/analytics/kpis/snapshot` | `module_key`, `granularity` | `SnapshotResponse` |

**Period values:** `7d` | `30d` | `90d` | `custom` | `data_range`

**KPIData schema:**
```json
{
  "total_sales":          12345.67,
  "total_expenses":       8901.23,
  "net_cashflow":         3444.44,
  "avg_daily_sales":      411.52,
  "avg_daily_expenses":   296.71,
  "sales_trend_pct":      8.5,
  "expenses_trend_pct":   3.2,
  "cashflow_trend_pct":   12.1,
  "period_days":          30
}
```

**EnrichedKPIData** (superset di KPIData):
```json
{
  ...KPIData,
  "fixed_costs_total":      9800.00,
  "expense_ratio":          72.09,
  "burn_rate":              296.71,
  "top_expense_category":   "stipendio",
  "combined_expenses":      18701.23
}
```

**CumulativePoint:**
```json
{
  "date":       "2026-03-01",
  "sales":      1250.00,
  "expenses":   890.00,
  "daily_net":  360.00,
  "cumulative": 3600.00
}
```

### 6.3 Modulo Overview `/api/modules/*`

| Method | Path | Params | Response |
|---|---|---|---|
| GET | `/api/modules/active` | — | `List[ModuleStatus]` |
| GET | `/api/modules/available` | — | `List[ModuleInfo]` |
| POST | `/api/modules/{module_key}/activate` | — | `OrganizationModule` |
| POST | `/api/modules/{module_key}/deactivate` | — | `OrganizationModule` |
| GET | `/api/modules/{module_key}/overview` | `period` | `OverviewData` |
| GET | `/api/modules/{module_key}/status` | — | `ModuleStatus` |

**OverviewData** (risposta del modulo overview — 1 round-trip):
```json
{
  "kpis": {...EnrichedKPIData},
  "daily_series": [
    {"date": "2026-03-01", "sales": 1250, "expenses": 890,
     "net_cashflow": 360, "cumulative": 360}
  ],
  "categories": {
    "top_sales":    [{"category": "food_sales", "total": 8000}],
    "top_expenses": [{"category": "stipendio",  "total": 4400}]
  },
  "last_insight": {...Insight | null},
  "data_availability": {
    "min_date": "2025-12-15",
    "max_date": "2026-03-12",
    "has_data": true
  }
}
```

### 6.4 Dataset Upload `/api/datasets/*`

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/datasets/upload` | multipart form (file + metadata) | `UploadResponse` |
| GET | `/api/datasets/` | — | `List[DatasetResponse]` |
| GET | `/api/datasets/{id}` | — | `DatasetResponse` |
| GET | `/api/datasets/{id}/preview` | — | `PreviewResponse` |
| DELETE | `/api/datasets/{id}` | — | `{message}` |

### 6.5 Data Management CRUD

**Purchase Records** `/api/purchase-records/*`:
```
GET  /             ?start_date ?end_date ?supplier_id ?limit=200
POST /             body: PurchaseRecordCreate
GET  /{id}
DELETE /{id}
```

**Fixed Costs** `/api/fixed-costs/*`:
```
GET  /             ?active_only=true ?category ?limit=200
POST /             body: FixedCostCreate
POST /bulk         body: List[FixedCostCreate]   → {inserted: N}
GET  /{id}
PATCH /{id}        body: partial update
DELETE /{id}
```

**Sales** `/api/sales/*`:
```
GET  /             ?start_date ?end_date ?limit=500
POST /             body: SalesRecordCreate
GET  /{id}
DELETE /{id}
GET  /categories
```

**Expenses** `/api/expenses/*`:
```
GET  /             ?start_date ?end_date ?limit=500
POST /             body: ExpenseRecordCreate
GET  /{id}
DELETE /{id}
GET  /categories
GET  /suppliers
```

**Purchases** (legacy) `/api/purchases/*`:
```
GET  /             ?start_date ?end_date ?limit=500
POST /             body: PurchaseCreate
GET  /{id}
DELETE /{id}
GET  /suppliers
```

### 6.6 Alert & Insights `/api/alerts/*`, `/api/insights/*`

```
# Alerts
GET  /api/alerts              ?status ?severity ?limit=50 ?skip=0
GET  /api/alerts/{id}
PATCH /api/alerts/{id}        body: {status: "acknowledged"|"resolved"}
GET  /api/alerts/count        → {total, by_severity, by_status}
POST /api/alerts/generate     → {generated: N, skipped: N}   (manuale)

# Insights
GET  /api/insights            ?module_key ?limit=10 ?skip=0
GET  /api/insights/{id}
POST /api/insights/generate   body: {module_key, period?, start_date?, end_date?}
GET  /api/insights/latest     ?module_key → Insight | null
```

### 6.7 Master Data `/api/customers/*`, `/api/suppliers/*`, `/api/products/*`

Pattern identico per tutti e tre:
```
GET  /             ?active_only=true ?limit=200
POST /             body: Create schema
GET  /{id}
PATCH /{id}        body: partial update
DELETE /{id}       → 204 No Content (soft delete: is_active=False)
```

### 6.8 Column Mappings & Validation Rules

```
# Column Mappings
GET  /api/column-mappings               ?dataset_type
POST /api/column-mappings               body: ColumnMappingCreate
DELETE /api/column-mappings/{id}
POST /api/column-mappings/batch         body: {dataset_type, mappings: [...]}
GET  /api/column-mappings/profiles/{dataset_id}

# Validation Rules
GET  /api/validation-rules              ?dataset_type
POST /api/validation-rules              body: DataValidationRuleCreate
PATCH /api/validation-rules/{id}
DELETE /api/validation-rules/{id}
```

---

## 7. Backend — Servizi e Repository

### 7.1 Dataset Service (`backend/services/dataset_service.py`)

Pipeline completa di upload file:

```
1. Receive bytes + filename + dataset_type
2. Parse CSV/XLSX/XLS → DataFrame
3. Normalize column names (lowercase, strip, underscore)
4. Load org's ColumnMappings from DB
5. Apply mappings + hardcoded aliases (fallback)
6. Extract canonical fields per type:
   - SALES:      date, amount, category, description, channel, customer_id, product_id
   - EXPENSES:   date, amount, category, description, supplier, supplier_id, product_id
   - PURCHASES:  date, supplier_name, quantity, unit, unit_price, total_price, category
   - FIXED_COSTS: name, category, amount, frequency, start_date, end_date
7. [v2.2] Evaluate DataValidationRules → skip/warn invalid rows
8. Insert records with:
   - source_record_id: sha256 hash of raw row
   - schema_version: "2.0"
   - source_type: "file_upload"
9. Create DatasetColumnProfile (statistiche colonne)
10. [Non-blocking] S3 upload if AWS vars present
11. [Non-blocking] KPI snapshot computation
Return: UploadResponse {id, rows_inserted, rows_skipped, errors, validation_summary}
```

**UPLOAD_DIR:** `Path(__file__).parent.parent / "uploads"` (relativo, non hardcoded)

### 7.2 Analytics Repository (`backend/repositories/analytics_repository.py`)

Funzioni di aggregazione MongoDB usate da tutti gli endpoint:

```python
aggregate_sales_by_date(org_id, start_date, end_date) -> Dict[str, float]
    # {date_string: total_amount, ...}

aggregate_expenses_by_date(org_id, start_date, end_date) -> Dict[str, float]
    # {date_string: total_amount, ...}

aggregate_sales_by_category(org_id, start_date, end_date) -> List[dict]
    # [{_id: "category", total: float, count: int}, ...]

aggregate_expenses_by_category(org_id, start_date, end_date) -> List[dict]
    # [{_id: "category", total: float, count: int}, ...]

aggregate_fixed_costs_total(org_id, start_date, end_date) -> float
    # Prorata i costi fissi nel periodo: importo * (giorni_nel_periodo / giorni_frequenza)

aggregate_cumulative_cashflow(org_id, start_date, end_date) -> List[dict]
    # [{date, sales, expenses, daily_net, cumulative}, ...]

get_analytics_date_range(org_id) -> dict
    # {min_date, max_date, has_sales, has_expenses, ...}
```

### 7.3 Alert Service (`backend/services/alert_service.py`)

Orchestratore alert multi-modulo:
```python
async def generate_and_save_alerts(org_id: str, module_key: str) -> dict
    # 1. Get module from registry
    # 2. Call module.alert_rules(org_id)
    # 3. Dedup: filter alerts already open (find_active_keys)
    # 4. Insert new alerts
    # Return: {generated: N, skipped: N, module_key: str}
```

### 7.4 AI Services

**`ai_analytics_service.py`:**
```python
async def get_analytics_summary(org_id, period, start_date, end_date) -> dict
    # Aggrega dati per il prompt AI: sales, expenses, trends, categories, anomalies
```

**`ai_insight_service.py`:**
```python
async def generate_cashflow_insight(org_id, period, start_date, end_date) -> Optional[Insight]
    # 1. Get module from registry
    # 2. Call module.insight_builder(org_id, start, end) → context dict
    # 3. Build prompt with system_prompt + user_message from context
    # 4. Call Claude via Anthropic SDK
    # 5. On error → use context["fallback_content"]
    # 6. Return Insight(org_id, module_key, title, content, metrics_context, ...)
```

---

## 8. Modulo: Cashflow Monitor

### 8.1 Registrazione nel Registry

**File:** `backend/modules/cashflow_monitor/__init__.py`

```python
register(ModuleDefinition(
    module_key      = "cashflow_monitor",
    module_name     = "Daily Cashflow Monitor",
    is_available    = True,
    snapshot_builder = build_snapshot,    # pre-calcola KPI
    post_upload_hooks = [post_upload_hook], # trigger su upload
    alert_rules     = run_alert_checks,   # genera alert
    insight_builder = build_insight_context, # prepara contesto AI
    overview_builder = build_overview,    # dashboard 1 round-trip
))
```

### 8.2 KPI Calcolati

#### KPI Base (sempre disponibili)
| KPI | Formula | Unità |
|---|---|---|
| `total_sales` | SUM(sales_records.amount) nel periodo | € |
| `total_expenses` | SUM(expense_records.amount) nel periodo | € |
| `net_cashflow` | total_sales − total_expenses | € |
| `avg_daily_sales` | total_sales / period_days | €/giorno |
| `avg_daily_expenses` | total_expenses / period_days | €/giorno |
| `sales_trend_pct` | ((periodo corrente − periodo precedente) / precedente) × 100 | % |
| `expenses_trend_pct` | come sopra per expenses | % |
| `cashflow_trend_pct` | come sopra per net_cashflow | % |
| `period_days` | numero giorni nel periodo selezionato | giorni |

#### KPI Enriched (da `/enriched-kpis` e `overview`)
| KPI | Formula | Unità |
|---|---|---|
| `fixed_costs_total` | SUM costi fissi proratati nel periodo | € |
| `expense_ratio` | total_expenses / total_sales × 100 | % |
| `burn_rate` | avg_daily_expenses (alias semantico) | €/giorno |
| `top_expense_category` | categoria con maggior spesa | stringa |
| `combined_expenses` | total_expenses + fixed_costs_total | € |

### 8.3 Alert Rules (`alert_rules.py`)

4 tipi di alert, tutti con deduplicazione:

#### Alert 1: Calo Vendite Giornaliero
```
Trigger:  vendite di un giorno < media 30gg × (1 - threshold)
Periodo:  ultimi 7 giorni controllati
Dedup key: (date_reference, "sales_below_avg")
Severità:
  LOW    → deviazione 10–20%
  MEDIUM → deviazione 20–30%
  HIGH   → deviazione > 30%
metric_payload: {actual, average, deviation_pct, alert_type: "sales_below_avg"}
title: "Ricavi {N}% sotto la media"
```

#### Alert 2: Picco Spese Giornaliero
```
Trigger:  spese di un giorno > media 30gg × (1 + threshold)
Periodo:  ultimi 7 giorni
Dedup key: (date_reference, "expenses_above_avg")
Severità: LOW/MEDIUM/HIGH (10/20/30%)
metric_payload: {actual, average, deviation_pct, alert_type: "expenses_above_avg"}
title: "Spese {N}% sopra la media"
```

#### Alert 3: Picco Spese per Categoria
```
Trigger:  spese categoria X in un giorno > media 30gg categoria × 1.5
Periodo:  ultimi 7 giorni
Dedup key: (date_reference, "cat_{category_slug}")
Severità: sempre HIGH
metric_payload: {category, actual, average, deviation_pct,
                alert_type: "category_expense_spike"}
title: "Categoria {X} sopra la media"
```

#### Alert 4: Cashflow Negativo Consecutivo
```
Trigger:  N giorni consecutivi con (sales - expenses) < 0
Periodo:  ultimi 14 giorni
Soglie:   3 giorni → MEDIUM, 5+ giorni → HIGH
Dedup key: (date_ultimo_giorno, "consecutive_negative_cashflow_{N}")
           Il conteggio nel key permette escalation (3→5 = nuovo alert)
metric_payload: {consecutive_days, alert_type: "consecutive_negative_cashflow"}
title: "Cashflow negativo per {N} giorni consecutivi"
```

**Deduplicazione (alert_repository.find_active_keys):**
```python
# Prima di inserire un alert, verifica se esiste già uno aperto (new/acknowledged)
# con stessa date_reference e stesso tipo
# fingerprint estratto da metric_payload.alert_type
existing_keys: Set[Tuple[str, str]] = {(date_ref, fingerprint)}
```

### 8.4 Insight AI (`insight_builder.py`)

**System Prompt (italiano, tono PMI-friendly):**
```
Sei un consulente finanziario esperto in piccole e medie imprese italiane.
Analizza questi dati di cashflow in modo concreto e pratico.
Usa termini semplici che un imprenditore possa capire immediatamente.
Struttura: 1) Situazione attuale (2-3 frasi), 2) Punti critici (3 bullet),
3) Un'azione consigliata concreta.
Massimo 250 parole. Usa numeri specifici.
```

**Dati inclusi nel prompt (context["user_message"]):**
- Periodo analizzato (start_date → end_date, N giorni)
- total_sales, total_expenses, net_cashflow
- avg_daily_sales, avg_daily_expenses
- sales_trend_pct vs periodo precedente
- expenses_trend_pct
- fixed_costs_total (costi fissi proratati)
- top 3 categorie di spesa (nome + importo + %)
- expense_ratio (% del ricavo che va in uscita)
- Numero di giorni con cashflow negativo

**Modello AI:** Claude via Anthropic SDK
**Schema versione:** `"2.0"`
**Fallback:** testo pre-generato se LLM non disponibile

### 8.5 Overview Builder (`overview_builder.py`)

Esegue 10 query in parallelo (asyncio.gather) per il dashboard principale:

```python
# Tutte le query sono lanciate in contemporanea
results = await asyncio.gather(
    aggregate_sales_by_date(...),      # serie giornaliera vendite
    aggregate_expenses_by_date(...),   # serie giornaliera spese
    aggregate_sales_by_category(...),  # top categorie vendite
    aggregate_expenses_by_category(...), # top categorie spese
    aggregate_fixed_costs_total(...),  # totale costi fissi proratati
    aggregate_cumulative_cashflow(...),# serie cumulativa
    get_analytics_date_range(...),     # min/max date disponibili
    find_latest_insight(...),          # ultimo insight
    find_alerts_by_status(...),        # alert aperti count
    find_active_fixed_costs(...),      # lista costi fissi attivi
)
```

**Output Overview:**
```json
{
  "kpis": {
    "total_sales":          12345.67,
    "total_expenses":       8901.23,
    "net_cashflow":         3444.44,
    "avg_daily_sales":      411.52,
    "avg_daily_expenses":   296.71,
    "sales_trend_pct":      8.5,
    "expenses_trend_pct":   3.2,
    "period_days":          30,
    "fixed_costs_total":    9800.0,
    "expense_ratio":        72.09,
    "burn_rate":            296.71,
    "top_expense_category": "stipendio"
  },
  "daily_series": [
    {"date": "2026-02-11", "sales": 1250, "expenses": 890,
     "net_cashflow": 360, "cumulative": 360},
    ...
  ],
  "categories": {
    "top_sales":    [{"category": "food_sales", "total": 8000, "count": 45}],
    "top_expenses": [{"category": "stipendio",  "total": 4400, "count": 2}]
  },
  "last_insight": {...Insight | null},
  "data_availability": {
    "min_date": "2025-12-15",
    "max_date": "2026-03-12",
    "has_data": true
  }
}
```

---

## 9. Frontend — Architettura React

### 9.1 Routing (`src/App.js`)

```
Public:
  /                 → LandingPage
  /login            → LoginPage (credenziali: admin@demo.com / demo123)
  /signup           → SignupPage

Protected (ProtectedRoute — richiede token valido):
  /dashboard              → DashboardPage
  /modules/cashflow       → CashflowModulePage (analytics)
  /modules/cashflow/data  → CashflowDataPage (inserimento dati)
  /upload                 → UploadPage (upload CSV/XLSX generico)
  /datasets               → DatasetsPage (lista dataset caricati)
  /column-mappings        → ColumnMappingsPage (regole mapping)
  /validation-rules       → ValidationRulesPage (regole validazione)
  /modules                → ModulesPage (attivazione moduli)
  /alerts                 → AlertsPage (tutti gli alert)
  /insights               → InsightsPage (tutti gli insight)
  /team                   → TeamPage (gestione team)
  /settings               → SettingsPage
```

### 9.2 Sidebar Navigation (`src/components/Layout.js`)

```
Sezione principale:
  📊 Dashboard             → /dashboard
  💰 Cashflow Monitor
     ├─ Analytics          → /modules/cashflow
     └─ Dati               → /modules/cashflow/data
  🧩 Modules               → /modules
  🔔 Alerts                → /alerts
  💡 Insights              → /insights

Sezione secondaria:
  👥 Team                  → /team
  ⚙️  Settings              → /settings
  🚪 Logout
```

Il submenu "Cashflow Monitor" è collassabile e si espande automaticamente quando la route corrente è una delle sue voci.

### 9.3 API Client (`src/api/client.js`)

```javascript
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
// In dev: '' → URLs relative → proxied to :8000 via setupProxy.js
// In prod: 'https://api.example.com'

api.interceptors.request.use((config) => {
  // Prepend BACKEND_URL to relative paths
  // Add Authorization: Bearer <token> from localStorage
})

api.interceptors.response.use(null, (error) => {
  if (error.response?.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
  }
})
```

**Proxy Dev** (`src/setupProxy.js`):
```javascript
// Tutte le richieste /api/* da localhost:3000 → localhost:8000
createProxyMiddleware('/api', { target: 'http://localhost:8000' })
```

### 9.4 Auth Context (`src/context/AuthContext.js`)

```javascript
// State
user:            UserResponse | null
token:           string | null
loading:         boolean
isAuthenticated: boolean

// Methods
login(email, password)  → POST /api/auth/login
signup(email, password, name, orgName) → POST /api/auth/signup
logout()
```

Token salvato in `localStorage`. Al mount, verifica token con `GET /api/auth/me`.

---

## 10. Frontend — Cashflow Monitor UI

### 10.1 CashflowModulePage (`/modules/cashflow`)

**Stato locale:**
```javascript
period:      '30d' | '7d' | '90d' | 'custom'
startDate:   string  // solo per period='custom'
endDate:     string
loading:     boolean
moduleActive: boolean

// Dati
overview:      OverviewData | null     // da /modules/cashflow_monitor/overview
chartData:     ChartDataPoint[] | null // da /analytics/charts (per MA7)
cumulativeData: CumulativePoint[]      // da overview.daily_series
alerts:        Alert[] | null
insights:      Insight[] | null
fixedCosts:    FixedCost[] | null
```

**Strategia di fetch (al mount e al cambio periodo):**
```javascript
// Parallelo:
1. GET /modules/cashflow_monitor/overview?period={period}  → overview + kpis + daily_series + categories
2. GET /analytics/charts?period={period}                   → chartData con sales_ma7, expenses_ma7
3. GET /alerts?status=new&limit=50                         → alerts
4. GET /insights?module_key=cashflow_monitor&limit=5       → insights history
5. GET /fixed-costs?active_only=true                       → fixedCosts
6. GET /modules/cashflow_monitor/status                    → moduleActive
```

### 10.2 Tab Structure

#### Tab 1: Panoramica
```
KPIStrip (8 card):
  [Total Sales + trend%]   [Total Expenses + trend%]
  [Net Cashflow + trend%]  [Burn Rate (€/gg)]
  [Fixed Costs]            [Expense Ratio %]
  [Avg Daily Sales]        [Top Expense Category]

Charts (2+1 layout):
  SalesExpensesChart    ← data: cumulativeData (daily_series)
  NetCashflowChart      ← data: cumulativeData

CumulativeCashflowChart ← data: cumulativeData (campo 'cumulative')

DetailedTrendsCharts    ← data: chartData (per sales_ma7, expenses_ma7)
```

#### Tab 2: Categorie
```
CategoryPieCharts:
  - Pie: top categorie vendite (% su totale)
  - Pie: top categorie spese (% su totale)

CategoryBarCharts:
  - Bar: acquisti da fornitori per categoria/fornitore
```

#### Tab 3: Costi Fissi
```
FixedCostsTab:
  - Tabella: name, category, amount, frequency, start_date, end_date, status
  - Totale proratato nel periodo selezionato
  - Stacked bar: Fixed vs Variable expenses
  - Azioni: modifica, disattiva
```

#### Tab 4: Alert
```
AlertsTab:
  - Filtri: stato (new/acknowledged/resolved), severità (low/medium/high)
  - Lista alert con:
    - Badge severità (colore: low=gray, medium=yellow, high=red)
    - Titolo, sommario
    - Data riferimento
    - Contesto numerico dal metric_payload
  - Pulsante "Genera Alert" → POST /alerts/generate
```

#### Tab 5: AI Insights
```
InsightsTab:
  - Ultimo insight: titolo, contenuto Markdown, periodo, modello usato
  - Accordion storia (ultimi 5): data, preview testo
  - Pulsante "Genera Nuovo Insight" → POST /insights/generate
```

### 10.3 KPI Strip — Dettaglio Card

| Card | Valore | Trend | Icona | Colore positivo |
|---|---|---|---|---|
| Total Sales | € totale | % vs periodo prec. | TrendingUp | Verde se positivo |
| Total Expenses | € totale | % vs periodo prec. | TrendingDown | Rosso se aumenta |
| Net Cashflow | € netto | % vs periodo prec. | Activity | Verde se positivo |
| Burn Rate | €/giorno | — | Flame | — |
| Fixed Costs | € totale proratato | — | Lock | — |
| Expense Ratio | % | — | Percent | Verde se < 80% |
| Avg Daily Sales | €/giorno | — | BarChart2 | — |
| Top Expense Cat. | stringa | — | Tag | — |

### 10.4 Charts — Libreria Recharts

| Chart | Tipo | X-Axis | Y-Axis | Serie |
|---|---|---|---|---|
| SalesExpensesChart | LineChart | date | € | sales, expenses |
| NetCashflowChart | AreaChart | date | € | net_cashflow |
| CumulativeCashflowChart | AreaChart | date | € | cumulative |
| DetailedTrendsCharts | ComposedChart | date | € | sales, expenses, sales_ma7, expenses_ma7 |
| CategoryPieCharts | PieChart | — | % | categories |
| CategoryBarCharts | BarChart | categoria | € | importo |

---

## 11. Upload Dati e Inserimento Manuale

### 11.1 Upload File (`/upload` e `/datasets`)

**Formati accettati:** CSV, XLSX, XLS

**Tipi di dataset:**
```
SALES       → popola sales_records
EXPENSES    → popola expense_records
PURCHASES   → popola purchase_records
FIXED_COSTS → popola fixed_costs
```

**Column Mapping automatico (alias hardcoded):**

*SALES — colonne riconosciute:*
```
date:        data, date, giorno, data_vendita, sale_date
amount:      importo, amount, totale, total, valore, ricavo, revenue, sales_amount
category:    categoria, category, tipo, type, reparto
description: descrizione, description, note, notes
channel:     canale, channel
```

*EXPENSES — colonne riconosciute:*
```
date:        data, date, giorno
amount:      importo, amount, totale, costo, spesa, expense_amount
category:    categoria, category, tipo
description: descrizione, description, note
supplier:    fornitore, supplier, vendor, fornitore_nome
```

*PURCHASES — colonne riconosciute:*
```
date:         data, date
supplier_name: fornitore, supplier, supplier_name, nome_fornitore
quantity:     quantita, quantità, quantity, qty
unit:         unita, unità, unit, um
unit_price:   prezzo_unitario, unit_price, prezzo, price
total_price:  totale, total, importo, total_price, importo_totale
category:     categoria, category
```

*FIXED_COSTS — colonne riconosciute:*
```
name:       nome, name, descrizione, description
amount:     importo, amount, costo, cost
frequency:  frequenza, frequency, periodicita, period
start_date: data_inizio, start_date, inizio
end_date:   data_fine, end_date, fine, scadenza
category:   categoria, category
```

**Mapping personalizzato:** configurabile per org via `/api/column-mappings`.

**Validazione dati (DataValidationRules):** righe che violano le regole sono skippate (non bloccano l'upload) e riportate nel response.

### 11.2 Inserimento Manuale — CashflowDataPage (`/modules/cashflow/data`)

Pagina con 4 tab, una per tipo di dato:

#### Tab Vendite
**Form (SalesEntryForm):**
```
Data *          → date picker
Importo *       → number input (€)
Categoria       → select: food_sales | beverage_sales | takeout | catering | altro
Canale          → select: dine_in | takeout | delivery | catering
Descrizione     → textarea
[+ Aggiungi riga / Inserimento bulk]
```

#### Tab Spese
**Form (ExpensesEntryForm):**
```
Data *          → date picker
Importo *       → number input (€)
Categoria       → select: ingredients | utilities | staff | rent | supplies | marketing | altro
Fornitore       → text input (stringa libera)
Descrizione     → textarea
[+ Aggiungi riga / Inserimento bulk]
```

#### Tab Acquisti Fornitori
**Form (PurchaseEntryForm):**
```
Data *              → date picker
Fornitore *         → text input
Quantità *          → number input
Unità               → select: kg | pezzi | litri | etc
Prezzo Unitario *   → number input (€)
Totale              → calcolato auto (quantità × prezzo)
Categoria           → text input
Stato pagamento     → select: pending | paid | overdue | cancelled
Data scadenza       → date picker (opzionale)
[+ Aggiungi riga]
```

#### Tab Costi Fissi
**Form (FixedCostEntryForm):**
```
Nome *          → text input (es. "Affitto locale")
Categoria *     → select: affitto | stipendio | finanziamento | leasing | abbonamento | altro
                          [campo custom se "altro" selezionato]
Importo *       → number input (€)
Frequenza *     → select: mensile | settimanale | trimestrale | annuale
Data inizio *   → date picker
Data fine       → date picker (vuoto = perpetuo)
```

Ogni section mostra anche la **lista dei record esistenti** con opzioni modifica/elimina.

---

## 12. Variabili d'Ambiente

### Backend (`backend/.env`)

| Variabile | Tipo | Obbligatoria | Descrizione |
|---|---|---|---|
| `MONGO_URL` | string | ✅ | URI MongoDB (es. `mongodb+srv://...`) |
| `DB_NAME` | string | ✅ | Nome database (es. `bi_pmi`) |
| `JWT_SECRET_KEY` | string | ✅ | Chiave segreta JWT (min 32 char random) |
| `CORS_ORIGINS` | CSV string | ✅ prod | Domini frontend autorizzati |
| `ENVIRONMENT` | string | No | `development` \| `production` (default: `development`) |
| `ANTHROPIC_API_KEY` | string | No | API key per Claude (AI chat + digest narrative) |
| `AWS_ACCESS_KEY_ID` | string | No | Per S3 upload |
| `AWS_SECRET_ACCESS_KEY` | string | No | Per S3 upload |
| `AWS_S3_BUCKET` | string | No | Bucket S3 |
| `AWS_REGION` | string | No | Region AWS (es. `eu-west-1`) |

### Frontend

| Variabile | Tipo | Default | Descrizione |
|---|---|---|---|
| `REACT_APP_BACKEND_URL` | string | `''` | URL backend. Vuoto = usa proxy |

**Proxy dev** (`package.json`):
```json
"proxy": "http://localhost:8000"
```

**setupProxy.js** (`src/setupProxy.js`): gestisce tutte le richieste `/api/*` verso il backend in development. **Questo file è necessario per il login — non rimuovere.**

---

## 13. Scalabilità e Performance

### 13.1 Query Performance

**Index coverage:** tutte le query produzione usano index su `organization_id` + il campo di filtro principale. Nessuna full collection scan sulle collection transazionali.

**Compound index ottimizzati per:**
- `(org, date)` — query per periodo (il 95% delle analytics queries)
- `(org, category)` — aggregazioni per categoria
- `(org, module_key, period_start)` — lookup KPI snapshot (O(log n))
- `(org, status)` — filtraggio alert aperti

### 13.2 Pattern di Ottimizzazione

| Tecnica | Dove | Impatto |
|---|---|---|
| **Overview endpoint** | `/modules/cashflow_monitor/overview` | 1 call frontend invece di 4-6 |
| **asyncio.gather** | overview_builder.py | 10 query MongoDB in parallelo |
| **KPI Snapshots** | kpi_snapshots collection | Query O(1) su periodi passati |
| **Async throughout** | Tutto il backend | Nessun blocking I/O |
| **Column mapping cache** | dataset_service.py | Evita query ripetuta per ogni riga |
| **Non-blocking uploads** | S3, KPI computation | Non rallentano la response |

### 13.3 Limiti Attuali

| Limite | Valore | Note |
|---|---|---|
| Max records per lista | 200–500 | Configurabile per endpoint |
| Alert history | 50 per chiamata | Paginabile con skip |
| Insights history | 10 per chiamata | Paginabile |
| Upload file | Sincrono | Max RAM disponibile |
| LLM calls | On-demand | Nessun rate limiting implementato |
| Tenant isolation | Row-level | Non collection-level |

### 13.4 Sicurezza Dati

- **Isolamento tenant:** ogni documento ha `organization_id`. Ogni query backend forza il filtro sull'`org_id` estratto dal JWT. Non è possibile leakage cross-tenant tramite API normale.
- **Soft delete:** customers/suppliers/products usano `is_active=False` (mai DELETE fisico).
- **source_record_id:** hash SHA-256 della riga CSV originale, utile per deduplicazione re-upload.
- **schema_version:** ogni record ha versione schema per gestire migrazioni future.

---

## 14. Data Flow End-to-End

### Scenario A: Upload File Vendite

```
1. User: POST /api/datasets/upload
   form: file=sales_q1.csv, name="Sales Q1", dataset_type="sales"

2. dataset_service.parse_and_save_dataset()
   ├─ pandas.read_csv() → DataFrame
   ├─ normalize columns: "Data Vendita" → "data_vendita"
   ├─ load ColumnMappings per org (se configurate)
   ├─ apply aliases: "data_vendita" → "date", "Importo" → "amount"
   ├─ extract per row: {date, amount, category, description, channel}
   ├─ DataValidationRules check (es. amount > 0, date in range)
   ├─ INSERT SalesRecords con source_record_id + schema_version="2.0"
   ├─ INSERT DatasetColumnProfile
   ├─ [async] S3 upload (se configurato)
   └─ [async] kpi_snapshot_service.compute_all_granularities()

3. Return: {id, rows_inserted: 245, rows_skipped: 2, errors: [...]}
```

### Scenario B: Dashboard Load

```
1. User naviga a /modules/cashflow

2. CashflowModulePage.fetchData() — chiamate parallele:
   ├─ GET /modules/cashflow_monitor/overview?period=30d
   │   └─ backend: asyncio.gather(10 queries) → OverviewData
   ├─ GET /analytics/charts?period=30d
   │   └─ backend: sales+expenses+MA7 → ChartDataPoint[]
   ├─ GET /alerts?status=new
   ├─ GET /insights?module_key=cashflow_monitor&limit=5
   ├─ GET /fixed-costs?active_only=true
   └─ GET /modules/cashflow_monitor/status

3. React state update → render:
   ├─ KPIStrip (8 card)
   ├─ SalesExpensesChart ← overview.daily_series
   ├─ NetCashflowChart ← overview.daily_series
   ├─ CumulativeCashflowChart ← overview.daily_series
   └─ [su tab change] AlertsTab / InsightsTab / FixedCostsTab
```

### Scenario C: Generazione Insight AI

```
1. User: POST /api/insights/generate
   body: {module_key: "cashflow_monitor", period: "30d"}

2. insight_service.generate_and_save()
   ├─ ai_insight_service.generate_cashflow_insight(org_id, "30d")
   │   ├─ registry.get("cashflow_monitor").insight_builder(org_id, start, end)
   │   │   └─ build_insight_context():
   │   │       ├─ fetch: sales, expenses, fixed_costs, top_categories
   │   │       └─ return {system_prompt, user_message, fallback_content, metrics_context}
   │   ├─ LlmChat.send_message(user_message) → gpt-4o response
   │   └─ Insight(content=response, model_version="gpt-4o", schema_version="2.0")
   └─ insights_collection.insert_one(insight_doc)

3. Return: Insight {id, title, content, metrics_context, period_start, period_end}
```

### Scenario D: Generazione Alert Automatici

```
1. Trigger: POST /api/alerts/generate  (manuale)
   oppure: chiamato da post_upload_hook dopo ogni upload

2. alert_service.generate_and_save_alerts(org_id, "cashflow_monitor")
   ├─ run_alert_checks(org_id)
   │   ├─ Query: sales_by_date ultimi 37gg (7 check + 30 media)
   │   ├─ Query: expenses_by_date ultimi 37gg
   │   ├─ Query: expenses_by_category_by_date ultimi 37gg
   │   ├─ Check 1: sales deviation → candidati Alert
   │   ├─ Check 2: expenses deviation → candidati Alert
   │   ├─ Check 3: per-category spike → candidati Alert
   │   └─ Check 4: consecutive negative cashflow → candidati Alert
   ├─ alert_repository.find_active_keys(org_id, "cashflow_monitor")
   │   └─ existing_keys = {(date_ref, fingerprint), ...}
   ├─ filter: [a for a in candidati if (a.date_reference, fingerprint(a)) not in existing_keys]
   └─ alerts_collection.insert_many(new_alerts)

3. Return: {generated: N, skipped: M}
```

---

## Appendice: Credenziali Demo

```
Email:    admin@demo.com
Password: demo123
Ruolo:    admin
Org:      Demo Restaurant (Food & Beverage)

Dati seed:
- 90 giorni di vendite (categories: food_sales, beverage_sales, takeout, catering)
- 90 giorni di spese (categories: ingredients, utilities, staff, rent, supplies, marketing)
- 90 giorni di acquisti da fornitori (5 fornitori italiani)
- 6 costi fissi mensili (affitto, stipendi, leasing, abbonamento, finanziamento)
- 3 alert di esempio
- 1 insight AI di esempio
- Modulo cashflow_monitor già attivato
```

---

*Documento generato automaticamente dall'analisi del codebase — Marzo 2026*
