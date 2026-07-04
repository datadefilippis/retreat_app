"""
Setup Wizard service — Fase 2 Track F.

Dynamic merchant onboarding wizard. Composes a personalized list of setup
steps for each org based on:
  - active commercial plan (free / starter / core / pro / enterprise)
  - active modules (cashflow_monitor / commerce / ai_assistant / ...)
  - per-module entitlements (orders_monthly, ai_chat, stores_max, ...)
  - current state of the org (data uploaded? store published? Stripe connected?)

The wizard is read-only: it inspects the DB, computes a derived view, and
returns it. Never writes.

Architecture (this package):
  - step_models.py     → Pydantic models (SetupStep, SetupCTA, ...)
  - step_registry.py   → canonical list of steps (one source of truth)
  - step_evaluator.py  → per-step `is_done(org)` predicates
  - entitlement_filter → decides which steps to SHOW for a given org
  - wizard_service.py  → orchestrator (compose-all)

Architecture (consumers):
  - routers/setup_wizard.py → exposes GET /api/setup/wizard
  - frontend/.../setup-wizard/widget/ → renders the dashboard widget

Design invariants (NON-NEGOTIABLE):
  1. Pure additive: never modifies existing collections, endpoints, or services.
  2. Plan-agnostic: NEVER hardcodes plan slugs. Always asks `is feature
     entitled? > 0` instead of `plan_slug == "core"`. This way the wizard
     auto-adapts when admin reshapes plans/addons in the catalog UI.
  3. i18n-ready: backend returns translation_keys, never localized text.
     Frontend resolves via react-i18next namespace `setup_wizard`.
  4. Module self-disclosure: each module declares its own setup steps
     (future: via ModuleDefinition.setup_steps_builder). For Step 1 the
     registry is a static list; module-level extension comes later.
  5. Read-only contract: GET /api/setup/wizard never mutates state.
"""
