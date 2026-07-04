# Setup Wizard — Backend (Fase 2 Track F)

Read-only service that produces a personalized onboarding wizard for an
organization, based on its plan, active modules, entitlements, and
current state.

## Files

| File | Role |
|---|---|
| `__init__.py`        | Package docstring + design invariants |
| `step_models.py`     | Pydantic schemas (`SetupStep`, `SetupCTA`, `SetupSection`, ...) |
| `step_registry.py`   | Canonical list of all setup steps (single source of truth) |
| `step_evaluator.py`  | Per-step async predicates that return `done: bool` |
| `entitlement_filter.py` | Decides which steps to show for a given org |
| `wizard_service.py`  | Orchestrator — composes the full response |

## Public API

The service is consumed only by `backend/routers/setup_wizard.py`.

```python
from services.setup_wizard.wizard_service import build_wizard

response = await build_wizard(org_id="...", current_user={...})
# returns SetupWizardResponse (Pydantic model)
```

## Adding a new step

1. Open `step_registry.py` and append a `SetupStep` to `STEP_REGISTRY`.
2. If the step is module-scoped, set `module_key`.
3. Set `predicate` to the entitlement check (e.g.
   `feature_required="commerce.orders_monthly"`).
4. Implement `is_done` in `step_evaluator.py` keyed by `step.key`.
5. Add the i18n keys in `frontend/public/locales/{it,en,fr,de}/setup_wizard.json`.

No modification to consumer code (frontend widget) is required — it
discovers steps dynamically via the API response.

## Adding a new CTA variant

CTAs are part of `SetupStep.cta_options[]`. Each CTA has a stable
`label_key` (i18n) and an `href` (admin-side route). Adding a new CTA to
an existing step is a one-line change in `step_registry.py`.

## Performance notes

- `build_wizard` runs at most ~10 small Mongo queries per call. Cached in
  the frontend with TTL 30s + on-focus refresh.
- All queries are org-scoped via `organization_id`. Never reads cross-org.

## Testing

Pure read-only logic. Unit tests live in `backend/tests/services/setup_wizard/`
(if added later). Each predicate is testable in isolation by feeding
fixture documents.

## Backwards compatibility

This service does NOT replace `routers/store_progress.py` (the
`/api/store/setup-progress` endpoint). The legacy endpoint stays online
for any external caller; the wizard service may invoke its logic
internally for the commerce-specific predicates.
