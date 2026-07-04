"""
Canonical setup step registry (Fase 2 Track F — Step 1).

Single source of truth for all wizard steps. To add/remove/reorder a step,
this is the ONLY place to touch (plus the matching predicate in
step_evaluator.py and the i18n keys in the frontend locale files).

Rules:
  - Each step has a stable, globally-unique `key`. Once shipped, never
    rename it (would break stored UI preferences down the line).
  - Steps belong to a `module_key`. "global" is reserved for cross-
    cutting concerns (verify email, branding, team).
  - `predicate` controls visibility, NOT done-ness. The done flag is
    computed elsewhere (step_evaluator.py).
  - All copy is referenced via i18n keys, never inline strings. The
    actual translations live under
    frontend/public/locales/<lang>/setup_wizard.json.
  - `priority` orders steps WITHIN a section; sections themselves are
    ordered in wizard_service.py via SECTION_ORDER.
  - Multiple CTAs are allowed when the step has genuine alternative paths
    (e.g. "load data" → manual / import). The first is primary; others
    are secondary — the user is free to pick.

i18n key convention:
  setup_wizard.steps.<step.key>.title         (required)
  setup_wizard.steps.<step.key>.body          (optional, 1-line description)
  setup_wizard.steps.<step.key>.hint          (optional, micro-tip)
  setup_wizard.ctas.<cta.label_key>           (button label, shared across steps)
  setup_wizard.sections.<module_key>.title    (section header)
"""

from __future__ import annotations

from typing import Dict, List

from .step_models import SetupCTA, SetupStep, SetupStepPredicate


# ── Module section metadata (i18n keys for section headers) ──────────────────
# Used by wizard_service to build SetupSection objects. Each entry maps a
# module_key to its display strings. Adding a module here is enough to make
# the wizard show its section automatically (assuming the module has at
# least one step that passes the visibility filter).

SECTION_META: Dict[str, Dict[str, str | None]] = {
    "cashflow_monitor": {
        "title_key": "sections.cashflow_monitor.title",
        "description_key": "sections.cashflow_monitor.description",
    },
    "commerce": {
        "title_key": "sections.commerce.title",
        "description_key": "sections.commerce.description",
    },
    "customers_light": {
        "title_key": "sections.customers_light.title",
        "description_key": "sections.customers_light.description",
    },
    "ai_assistant": {
        "title_key": "sections.ai_assistant.title",
        "description_key": "sections.ai_assistant.description",
    },
    "global": {
        "title_key": "sections.global.title",
        "description_key": None,
    },
}

# Section render order (top to bottom in the widget). Sections not listed
# here go to the end in arbitrary order.
SECTION_ORDER: List[str] = [
    "global",            # account-level basics first (verify email)
    "cashflow_monitor",  # core feature for ALL plans
    "commerce",          # only commerce-enabled plans
    "ai_assistant",      # AI features
    "customers_light",   # downstream of cashflow data
]


# ── Step registry ────────────────────────────────────────────────────────────
# Curated list of all steps the wizard knows about. Visibility filters are
# applied by entitlement_filter.py at request time — every org sees a
# tailored subset.

STEP_REGISTRY: List[SetupStep] = [

    # ── GLOBAL section ───────────────────────────────────────────────────────
    # Account-level basics that apply regardless of plan.

    SetupStep(
        key="global.verify_email",
        module_key="global",
        title_key="steps.global.verify_email.title",
        body_key="steps.global.verify_email.body",
        priority=10,
        required=True,
        cta_options=[
            SetupCTA(
                label_key="ctas.verify_email_now",
                href="/verify-email-required",
                variant="primary",
                icon_key="mail-check",
            ),
        ],
        # No predicate — visible to ALL orgs/plans.
    ),

    SetupStep(
        key="global.brand_identity",
        module_key="global",
        title_key="steps.global.brand_identity.title",
        body_key="steps.global.brand_identity.body",
        hint_key="steps.global.brand_identity.hint",
        priority=20,
        required=False,  # nice-to-have, not blocking
        cta_options=[
            SetupCTA(
                label_key="ctas.go_to_settings",
                href="/store/settings#section-identity",
                variant="primary",
                icon_key="palette",
            ),
        ],
    ),

    # ── CASHFLOW MONITOR section ─────────────────────────────────────────────
    # Active for all plans (free demo through enterprise). The first step is
    # the foundational one: every other module benefits from cashflow data
    # being present.

    SetupStep(
        key="cashflow_monitor.upload_first_data",
        module_key="cashflow_monitor",
        title_key="steps.cashflow_monitor.upload_first_data.title",
        body_key="steps.cashflow_monitor.upload_first_data.body",
        hint_key="steps.cashflow_monitor.upload_first_data.hint",
        priority=10,
        required=True,
        cta_options=[
            # Primary: manual entry — the lowest-friction entrypoint for
            # users who don't have a CSV ready yet.
            SetupCTA(
                label_key="ctas.manual_entry",
                href="/modules/cashflow/data/sales",
                variant="primary",
                icon_key="pencil",
            ),
            # Secondary: bulk import for users coming from a spreadsheet.
            SetupCTA(
                label_key="ctas.import_csv",
                href="/modules/cashflow/data/sales",
                variant="secondary",
                icon_key="upload",
            ),
        ],
        # Always visible — cashflow_monitor is in every plan.
    ),

    SetupStep(
        key="cashflow_monitor.first_alert",
        module_key="cashflow_monitor",
        title_key="steps.cashflow_monitor.first_alert.title",
        body_key="steps.cashflow_monitor.first_alert.body",
        priority=30,
        required=False,
        cta_options=[
            SetupCTA(
                label_key="ctas.configure_alert",
                href="/alerts",
                variant="primary",
                icon_key="bell",
            ),
        ],
        # Email alerts are gated by plan (free has no email). The
        # entitlement check protects the visibility.
        predicate=SetupStepPredicate(
            feature_required="cashflow_monitor.email_alerts",
        ),
    ),

    # ── COMMERCE section ─────────────────────────────────────────────────────
    # Whole section gated by `commerce.orders_monthly > 0` — automatically
    # hidden for free/starter where commerce is disabled.

    SetupStep(
        key="commerce.identity",
        module_key="commerce",
        title_key="steps.commerce.identity.title",
        body_key="steps.commerce.identity.body",
        priority=10,
        required=True,
        cta_options=[
            SetupCTA(
                label_key="ctas.fill_identity",
                href="/store/settings#section-identity",
                variant="primary",
                icon_key="store",
            ),
        ],
        predicate=SetupStepPredicate(
            feature_required="commerce.orders_monthly",
        ),
    ),

    SetupStep(
        key="commerce.first_product",
        module_key="commerce",
        title_key="steps.commerce.first_product.title",
        body_key="steps.commerce.first_product.body",
        hint_key="steps.commerce.first_product.hint",
        priority=20,
        required=True,
        cta_options=[
            SetupCTA(
                label_key="ctas.create_product_manually",
                href="/products",
                variant="primary",
                icon_key="package-plus",
            ),
            # NOTE: a "Import CSV products" CTA was envisaged here but the
            # backend doesn't yet ship a products import endpoint. The
            # `ctas.import_products_csv` i18n key is reserved across all
            # 4 locales and can be re-enabled in one line as soon as the
            # import flow lands.
        ],
        predicate=SetupStepPredicate(
            feature_required="commerce.orders_monthly",
        ),
    ),

    SetupStep(
        key="commerce.email_sender",
        module_key="commerce",
        title_key="steps.commerce.email_sender.title",
        body_key="steps.commerce.email_sender.body",
        priority=30,
        required=True,
        cta_options=[
            SetupCTA(
                label_key="ctas.configure_email",
                href="/store/settings#section-email",
                variant="primary",
                icon_key="mail",
            ),
        ],
        predicate=SetupStepPredicate(
            feature_required="commerce.orders_monthly",
        ),
    ),

    SetupStep(
        key="commerce.stripe_connect",
        module_key="commerce",
        title_key="steps.commerce.stripe_connect.title",
        body_key="steps.commerce.stripe_connect.body",
        priority=40,
        required=True,
        cta_options=[
            SetupCTA(
                label_key="ctas.connect_stripe",
                href="/settings",
                variant="primary",
                icon_key="credit-card",
            ),
        ],
        predicate=SetupStepPredicate(
            feature_required="commerce.orders_monthly",
        ),
    ),

    SetupStep(
        key="commerce.publish_storefront",
        module_key="commerce",
        title_key="steps.commerce.publish_storefront.title",
        body_key="steps.commerce.publish_storefront.body",
        priority=50,
        required=True,
        cta_options=[
            SetupCTA(
                label_key="ctas.publish_now",
                href="/store/settings",
                variant="primary",
                icon_key="rocket",
            ),
        ],
        predicate=SetupStepPredicate(
            feature_required="commerce.orders_monthly",
        ),
    ),

    SetupStep(
        key="commerce.first_order",
        module_key="commerce",
        title_key="steps.commerce.first_order.title",
        body_key="steps.commerce.first_order.body",
        hint_key="steps.commerce.first_order.hint",
        priority=60,
        required=False,  # educational — orders arrive on their own; this
                         # is a hint for those who want to test or import.
        cta_options=[
            # Three legitimate paths: manual order (admin-confirmed, no
            # payment), CSV import, or wait for live Stripe.
            SetupCTA(
                label_key="ctas.create_manual_order",
                href="/orders",
                variant="primary",
                icon_key="plus-circle",
            ),
            SetupCTA(
                label_key="ctas.import_orders_csv",
                href="/orders?action=import",
                variant="secondary",
                icon_key="upload",
            ),
            SetupCTA(
                label_key="ctas.configure_stripe_auto",
                href="/settings",
                variant="ghost",
                icon_key="zap",
            ),
        ],
        predicate=SetupStepPredicate(
            feature_required="commerce.orders_monthly",
        ),
    ),

    # ── AI ASSISTANT section ─────────────────────────────────────────────────
    # ai_assistant.chat is entitled in every plan with limit > 0; only the
    # `enterprise` "Custom" plan may opt out (admin override).

    SetupStep(
        key="ai_assistant.first_chat",
        module_key="ai_assistant",
        title_key="steps.ai_assistant.first_chat.title",
        body_key="steps.ai_assistant.first_chat.body",
        priority=10,
        required=False,
        cta_options=[
            SetupCTA(
                label_key="ctas.try_ai_chat",
                href="/dashboard",  # AI chat opens from the dashboard sidebar
                variant="primary",
                icon_key="sparkles",
            ),
        ],
        predicate=SetupStepPredicate(
            feature_required="ai_assistant.chat",
        ),
    ),
]


# ── Convenience accessors ────────────────────────────────────────────────────

def get_all_steps() -> List[SetupStep]:
    """Return a deep copy of the registry. Callers can safely mutate."""
    # model_copy() is Pydantic v2's idiomatic deep clone for BaseModel.
    return [step.model_copy(deep=True) for step in STEP_REGISTRY]


def get_step_by_key(key: str) -> SetupStep | None:
    """Look up a step by its global key. None if not registered."""
    for step in STEP_REGISTRY:
        if step.key == key:
            return step.model_copy(deep=True)
    return None
