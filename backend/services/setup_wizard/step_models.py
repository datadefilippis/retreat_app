"""
Pydantic models for the Setup Wizard service (Fase 2 Track F).

These shapes are the canonical contract between:
  - step_registry.py        (canonical step definitions)
  - step_evaluator.py       (per-step done predicates)
  - wizard_service.py       (composition layer)
  - routers/setup_wizard.py (HTTP boundary)
  - frontend setup-wizard/  (React widget)

Schema design rules:
  - i18n-first: only translation_keys travel over the wire (no Italian/
    English text). Frontend resolves with react-i18next namespace
    `setup_wizard`.
  - Backward compat: extra="ignore" everywhere so legacy fields in stored
    state never crash the wizard.
  - No timestamps: the wizard is purely derived state. We never persist
    it, so created_at/updated_at make no sense here.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ── Predicate ────────────────────────────────────────────────────────────────
# A predicate decides whether a step is VISIBLE for a given org. It is
# evaluated in entitlement_filter.py against the org's entitlement map.
#
# Three forms (all optional, mixable AND-combined):
#   feature_required: "commerce.orders_monthly"
#       step shown only if entitlement[commerce][orders_monthly] > 0 (or = -1
#       which means "unlimited"). Used to hide commerce steps from cashflow-
#       only plans.
#
#   plan_required: ["core", "pro", "enterprise"]
#       step shown only if org.commercial_plan_slug is in this allow-list.
#       Use sparingly — prefer feature_required to stay plan-rebrand-safe.
#
#   plan_excludes: ["enterprise"]
#       step skipped for these plans. Useful for "Custom" plans where
#       configuration is bespoke and the wizard isn't applicable.

class SetupStepPredicate(BaseModel):
    """Visibility rule for a step. Evaluated server-side."""

    model_config = ConfigDict(extra="ignore")

    # "module_key.feature_key" — checked against entitlement.
    # Step is shown if the feature is entitled (limit > 0 or unlimited).
    feature_required: Optional[str] = Field(
        default=None,
        description="dotted module.feature_key — show only when entitled",
    )

    # Allow-list of plan slugs. None or [] means "all plans".
    plan_required: List[str] = Field(default_factory=list)

    # Deny-list of plan slugs. Higher precedence than plan_required.
    plan_excludes: List[str] = Field(default_factory=list)


# ── CTA (Call To Action) ─────────────────────────────────────────────────────
# Each step renders 1..3 CTA buttons. Multiple CTAs are used when the step
# has alternative paths the user might take (e.g. "load cashflow data"
# offers both manual entry and CSV import). The frontend renders them
# side-by-side; the first one is "primary" (filled), others "secondary".
#
# href: admin-side route (e.g. "/modules/cashflow/data?tab=sales"). Anchors
# are supported (e.g. "/store/settings#section-identity").

class SetupCTA(BaseModel):
    """One actionable button shown next to a setup step."""

    model_config = ConfigDict(extra="ignore")

    # i18n key under setup_wizard.ctas.{label_key}
    label_key: str = Field(min_length=1, max_length=120)

    # Admin route to navigate to. Frontend renders as <Link>.
    href: str = Field(min_length=1, max_length=500)

    # Visual variant in the UI. Only the first CTA is typically primary.
    variant: Literal["primary", "secondary", "ghost"] = "primary"

    # Optional icon name (kebab-case, mapped to lucide-react icons in
    # frontend/.../stepIcons.js). None = no icon.
    icon_key: Optional[str] = Field(default=None, max_length=40)


# ── Step ─────────────────────────────────────────────────────────────────────
# The atomic unit of the wizard. One step = one user-facing task. The step's
# `done` flag is computed by step_evaluator.py — registry never sets it.

class SetupStep(BaseModel):
    """A single onboarding step shown in the dashboard widget."""

    model_config = ConfigDict(extra="ignore")

    # Unique stable identifier across the whole platform.
    # Convention: "<module_key>.<short_action>" or "global.<action>"
    # Examples: "cashflow_monitor.upload_first_data", "commerce.first_product"
    key: str = Field(min_length=1, max_length=80)

    # Module that owns this step. "global" for cross-cutting steps
    # (verify email, branding, team).
    module_key: str = Field(min_length=1, max_length=40)

    # i18n keys (resolved by frontend, namespace = "setup_wizard")
    title_key: str = Field(min_length=1, max_length=200)
    body_key: Optional[str] = Field(default=None, max_length=200)
    hint_key: Optional[str] = Field(default=None, max_length=200)

    # 1..3 CTAs. First is the suggested primary path.
    cta_options: List[SetupCTA] = Field(default_factory=list, max_length=3)

    # Computed at runtime by step_evaluator.is_done().
    # Registry never sets this — left as default at registry time.
    done: bool = False

    # If False, the step is "recommended but not required" and renders with
    # a gentler visual treatment in the widget. Used for educational steps
    # like "Try the AI chat".
    required: bool = True

    # Sort order within the step's section (lower = shown first).
    priority: int = Field(default=100, ge=0)

    # Visibility predicate. None = always visible (when section is shown).
    predicate: Optional[SetupStepPredicate] = None


# ── Section ──────────────────────────────────────────────────────────────────
# Steps are grouped by section. Default sections map 1:1 to module_key,
# plus a synthetic "global" section for cross-cutting concerns.

class SetupSection(BaseModel):
    """Group of related steps shown together in the widget."""

    model_config = ConfigDict(extra="ignore")

    # Same as SetupStep.module_key. "global" for non-module steps.
    module_key: str = Field(min_length=1, max_length=40)

    # i18n keys for the section header (namespace = "setup_wizard")
    title_key: str = Field(min_length=1, max_length=200)
    description_key: Optional[str] = Field(default=None, max_length=200)

    # Optional badge shown next to title (e.g. plan-specific note).
    # i18n key. None = no badge.
    badge_key: Optional[str] = Field(default=None, max_length=200)

    # Steps in this section, already filtered + sorted by priority.
    steps: List[SetupStep] = Field(default_factory=list)

    # Aggregated done counts (computed in wizard_service).
    done_count: int = 0
    total_count: int = 0


# ── Top-level response ───────────────────────────────────────────────────────
# This is what GET /api/setup/wizard returns.

class SetupWizardResponse(BaseModel):
    """Full payload for the dashboard wizard widget."""

    model_config = ConfigDict(extra="ignore")

    org_id: str

    # Plan context (display only — frontend uses it for the badge).
    plan_slug: str = Field(min_length=1, max_length=40)
    plan_name_key: str = Field(min_length=1, max_length=120)

    # Modules currently active for this org. Used by frontend to decide
    # which sections to render (in case the API briefly returns data for
    # a module that just got deactivated).
    active_modules: List[str] = Field(default_factory=list)

    # Sections, already sorted (cashflow first, then commerce, then ai,
    # then global). Each section's steps are pre-filtered for visibility.
    sections: List[SetupSection] = Field(default_factory=list)

    # Aggregate progress across ALL visible steps.
    progress_pct: int = Field(default=0, ge=0, le=100)

    # First not-done step (for the collapsed widget headline). Optional —
    # absent when everything is done.
    next_step_key: Optional[str] = None

    # True iff progress_pct == 100.
    is_complete: bool = False
