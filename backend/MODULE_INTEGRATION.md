# Module Integration Guide

How to integrate a new module with the subscription and entitlement system.

## Concepts

| Concept | Description | Example |
|---------|-------------|---------|
| `module_key` | Unique identifier for a module. Lowercase snake_case. | `"ai_assistant"`, `"cashflow_monitor"` |
| `feature_key` | A capability within a module that can be metered. Module-specific — NOT a global concept. | `"chat"`, `"insights"` (ai_assistant) |
| `pricing_plan` | A tier of access for a module, stored in `pricing_plans` collection. Has limits per feature_key. | AI Starter: chat=50, insights=5 |
| `module_subscription` | Links an org to a pricing plan for a module. At most one active per org+module. | Org X subscribes to AI Pro |
| `usage_event` | A single invocation of a feature, scoped to `(org_id, module_key, feature_key)`. Stored in `ai_usage_events` collection. | Org X used ai_assistant/chat |

## File Map

```
services/module_access.py          ← Generic entitlement service (DO NOT put module-specific logic here)
services/ai_access.py              ← AI-specific thin wrapper (pattern to follow for new modules)
services/seed_pricing.py           ← Seed pricing plans at startup

repositories/subscription_repository.py  ← Pricing plans + subscriptions CRUD
repositories/usage_repository.py         ← Module-aware usage recording + counting

models/pricing_plan.py             ← PricingPlan model
models/subscription.py             ← ModuleSubscription model
models/ai_usage.py                 ← AIUsageEvent model (used by all modules, not just AI)
```

## Usage Tracking — How It Works

Usage events are stored in a single collection (`ai_usage_events`, name is legacy).
Each event has three scoping fields:

```
{ organization_id, module_key, feature, created_at, ... }
```

- `module_key` prevents collisions: two modules can both have a `"reports"` feature.
- Queries always filter by `(organization_id, module_key, feature)`.
- Compound index: `(organization_id, module_key, feature, created_at)`.

### Write path

```python
# In your router, after business logic:
await usage_repository.record_usage(
    org_id=org_doc["id"],
    module_key="inventory_tracker",    # YOUR module_key — required
    feature_key="reports",
)
```

### Read path (automatic)

`module_access.check_module_access()` calls `usage_repository.count_usage()` with
the correct `module_key` internally.  You don't need to count manually.

### Why module_key matters

Without `module_key`, if `ai_assistant` and `inventory_tracker` both define
`feature_key="reports"`, their counts would collide.  With `module_key` in
every query, each module's usage is isolated.

## Adding a New Module (step by step)

### 1. Choose a module_key

Pick a unique, descriptive snake_case name: `"revenue_forecasting"`, `"expense_optimizer"`, etc.

### 2. Define feature_keys

Decide which features within your module need metering. These are opaque strings — the entitlement layer treats them generically.

Example for a hypothetical `inventory_tracker` module:
```python
# feature_keys: "stock_alerts" (alerts/month), "reports" (report generations/month)
```

### 3. Add seed pricing plans

In `services/seed_pricing.py`, add a plan list and call from `seed_pricing_plans_if_empty()`:

```python
INVENTORY_TRACKER_PLANS = [
    {
        "module_key": "inventory_tracker",
        "slug": "inventory_tracker_free",
        "name": "Free",
        "price_monthly": 0.0,
        "currency": "EUR",
        "limits": {
            # Feature keys specific to inventory_tracker:
            "stock_alerts": 0,
            "reports": 0,
        },
        "sort_order": 0,
    },
    {
        "module_key": "inventory_tracker",
        "slug": "inventory_tracker_basic",
        "name": "Inventory Basic",
        "price_monthly": 19.0,
        "currency": "EUR",
        "limits": {
            "stock_alerts": 100,
            "reports": 10,
        },
        "sort_order": 1,
    },
]

async def seed_pricing_plans_if_empty():
    await _seed_module_plans("ai_assistant", AI_ASSISTANT_PLANS)
    await _seed_module_plans("inventory_tracker", INVENTORY_TRACKER_PLANS)  # ← add
```

### 4. Create a thin wrapper service (optional but recommended)

Follow the pattern of `services/ai_access.py`:

```python
# services/inventory_access.py
from services.module_access import check_module_access, build_module_access_status

MODULE_KEY = "inventory_tracker"

async def assert_inventory_access(org_doc: dict, feature: str) -> None:
    await check_module_access(org_doc["id"], MODULE_KEY, feature, org_doc=org_doc)

async def build_inventory_access_status(org_doc: dict) -> dict:
    return await build_module_access_status(org_doc["id"], MODULE_KEY, org_doc=org_doc)
```

### 5. Use in your router

```python
from services.inventory_access import assert_inventory_access
from repositories import usage_repository

MODULE_KEY = "inventory_tracker"

@router.post("/inventory/generate-report")
async def generate_report(current_user: dict = Depends(get_current_user)):
    org_doc = current_user["organization"]

    # Check entitlements (raises 403 or 429)
    await assert_inventory_access(org_doc, "reports")

    # ... do the work ...

    # Record usage event — module_key is REQUIRED
    await usage_repository.record_usage(org_doc["id"], MODULE_KEY, "reports")

    return {"ok": True}
```

### 6. Add an access-status endpoint (optional)

If the frontend needs to show gating UI for this module:

```python
@router.get("/inventory/access-status")
async def inventory_access_status(current_user: dict = Depends(get_current_user)):
    return await build_inventory_access_status(current_user["organization"])
```

## Key Rules

1. **module_access.py is generic** — never add module-specific logic there.
2. **feature_keys are module-scoped** — "chat" means nothing outside ai_assistant.
3. **usage_repository requires module_key** — `record_usage(org_id, module_key, feature_key)` and `count_usage(org_id, module_key, feature_key, ...)`. Never omit module_key.
4. **One active subscription per org+module** — enforced by `get_active_subscription()` (returns most recent).
5. **Fallback to Organization.plan** is AI-specific legacy — new modules don't need it.
6. **Pricing plans are admin-managed** — the seed creates initial plans, but admins can modify prices/limits via API.
7. **Don't import ai_usage_repository** — new modules use `usage_repository` exclusively. `ai_usage_repository` is legacy AI-only.
8. **Access-status response uses neutral "enabled" key** — module_access.py returns `"enabled"`. Only ai_access.py remaps it to `"ai_enabled"` for frontend backward compat. New modules use `"enabled"` as-is.
9. **Two metering models** — *usage metering* (limit > 0, counts invocations) for per-action features like AI chat; *access gating* (limit = -1 or 0, binary) for read-only analytics. The same `check_module_access()` handles both.

## Architecture Diagram

```
Router (module-specific)
  │
  ├── assert_{module}_access(org_doc, feature_key)
  │     └── module_access.check_module_access(org_id, module_key, feature_key)
  │           ├── subscription_repository.get_active_subscription()
  │           ├── subscription_repository.get_pricing_plan()
  │           └── usage_repository.count_usage(org_id, module_key, feature_key, ...)
  │
  ├── ... business logic ...
  │
  └── [if usage metering] usage_repository.record_usage(org_id, module_key, feature_key)
```

## Live Case Studies

### ai_assistant — Usage Metering

```
module_key: "ai_assistant"
feature_keys: "chat" (50/month), "insights" (5/month)
metering: usage-based (limit > 0 → count invocations)
access-status: GET /ai/access-status → {"ai_enabled": ..., ...}  (legacy key)
wrapper: services/ai_access.py
```

### cashflow_monitor — Access Gating

```
module_key: "cashflow_monitor"
feature_keys: "analytics" (-1 = unlimited), "export" (0 = disabled in free)
metering: access gating only (limit = -1 or 0, no counting)
access-status: GET /analytics/cashflow/access-status → {"enabled": ..., ...}
wrapper: services/cashflow_access.py
pricing: free (analytics=-1, export=0) + pro (analytics=-1, export=-1)
note: free tier = exact current behavior, no regression
```

## Data Flow — Usage Metering (ai_assistant)

```
1. User calls POST /ai/chat
2. Router calls assert_ai_access(org_doc, "chat")
   → module_access.check_module_access(org_id, "ai_assistant", "chat")
     → get_active_subscription → pricing_plan → limits={"chat": 50}
     → usage_repository.count_usage(org_id, "ai_assistant", "chat", ...) → 7
     → 7 < 50 → OK
3. Router executes business logic (LLM call)
4. Router calls ai_usage_repository.record_event(org_id, "chat")
   → inserts {organization_id, module_key: "ai_assistant", feature: "chat", ...}
```

## Data Flow — Access Gating (cashflow_monitor)

```
1. User calls GET /analytics/kpis
2. Router calls assert_cashflow_access(org_doc, "analytics")
   → module_access.check_module_access(org_id, "cashflow_monitor", "analytics")
     → get_active_subscription (or fallback to free plan)
     → limits={"analytics": -1, "export": 0}
     → limit == -1 → return immediately (no counting)
3. Router executes business logic (KPI aggregation)
4. No record_usage() call needed — access gating has no counting
```
