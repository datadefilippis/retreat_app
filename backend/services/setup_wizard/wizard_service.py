"""
Setup Wizard orchestrator (Fase 2 Track F — Step 3).

`build_wizard(org_id, current_user)` is the single public entry point.
It composes the canonical step registry, the per-org entitlement map,
and the per-step done predicates into a `SetupWizardResponse` ready for
the dashboard widget.

Pipeline:

  1. Load Organization document (for plan_slug)
  2. Determine which modules are "in scope" for this wizard (= modules
     referenced by any step in the registry)
  3. For each in-scope module, fetch entitlements via module_access
  4. Filter the registry: drop steps whose predicate fails for this org
  5. Compute `done` for each surviving step (parallel asyncio.gather)
  6. Group steps by section (module_key); sort by SECTION_ORDER then
     by step.priority within a section
  7. Aggregate progress (% complete + first not-done step)

The whole pipeline is read-only and idempotent. Calling it twice yields
identical results (modulo state changes between the two calls).
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from database import organizations_collection

from .step_models import SetupSection, SetupStep, SetupWizardResponse
from .step_registry import (
    SECTION_META,
    SECTION_ORDER,
    get_all_steps,
)
from .entitlement_filter import (
    EntitlementMap,
    required_modules_from_registry,
    should_show_step,
)
from .step_evaluator import is_step_done

logger = logging.getLogger(__name__)


# i18n key for the plan name display. Maps slug → "plans.<slug>" key.
# Kept here (not in step_registry) so localization config lives close to
# its consumer. Frontend resolves with namespace `setup_wizard`.
def _plan_name_key(plan_slug: str) -> str:
    """Return the i18n key for the plan display name."""
    # Defensive: any unknown slug falls back to "plans.unknown" so the
    # widget never blanks out.
    return f"plans.{plan_slug}" if plan_slug else "plans.unknown"


async def _load_org(org_id: str) -> Optional[dict]:
    """Load the org doc with only the fields we need.

    Returns None if the org doesn't exist (caller should 404).
    """
    return await organizations_collection.find_one(
        {"id": org_id},
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "commercial_plan_slug": 1,
            "plan": 1,                 # legacy fallback
            "is_active": 1,
            "billing_status": 1,
            "trial_ends_at": 1,
            "current_period_end": 1,
        },
    )


def _resolve_plan_slug(org: dict) -> str:
    """Pick the most authoritative plan slug for the org.

    Order: commercial_plan_slug → legacy `plan` field → "free" fallback.
    """
    return (
        org.get("commercial_plan_slug")
        or org.get("plan")
        or "free"
    )


async def _build_entitlement_map(
    org_id: str,
    org_doc: dict,
    in_scope_modules: List[str],
) -> EntitlementMap:
    """Fetch effective entitlements for every module referenced by the registry.

    Uses module_access.get_module_entitlements which already accounts for:
      - active subscription / pricing plan
      - billing-gate restrictions (trial expired, past_due)
      - read-only grace period after downgrade

    NOTE: the returned `limits` dict is the BASE plan limits. Add-ons
    contribute via `module_access.get_effective_limit`. For visibility-
    decision purposes (just "is feature > 0?") base limits are usually
    enough — when an add-on is the SOLE reason a feature is entitled, we
    upgrade to get_effective_limit per-feature in a follow-up. For Step 3
    we keep it simple: base limits drive visibility.
    """
    # Local import to avoid a circular at module load time (services are
    # auto-imported by services/__init__.py).
    from services import module_access

    result: EntitlementMap = {}

    # Run all module entitlement lookups in parallel — they hit the same
    # subscription_repository under the hood and are quick.
    tasks = [
        module_access.get_module_entitlements(
            org_id=org_id,
            module_key=m,
            org_doc=org_doc,
        )
        for m in in_scope_modules
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for module_key, ent in zip(in_scope_modules, results):
        if isinstance(ent, Exception):
            logger.warning(
                "setup_wizard: get_module_entitlements failed for org=%s module=%s: %s",
                org_id, module_key, ent,
            )
            result[module_key] = {}
            continue
        # ent shape: {enabled, read_only, limits: {...}, plan_name, plan_slug}
        result[module_key] = (ent or {}).get("limits", {}) or {}

    return result


def _filter_visible_steps(
    all_steps: List[SetupStep],
    plan_slug: str,
    entitlements: EntitlementMap,
) -> List[SetupStep]:
    """Apply the predicate filter to drop steps the org should NOT see."""
    return [
        step for step in all_steps
        if should_show_step(step, plan_slug, entitlements)
    ]


async def _compute_done_flags(
    steps: List[SetupStep],
    org_id: str,
    user_id: Optional[str],
) -> List[SetupStep]:
    """Mutate `step.done` in-place using the evaluator. Returns same list.

    Done flags are computed in parallel — at most ~10 small Mongo queries.
    """
    tasks = [is_step_done(s.key, org_id, user_id) for s in steps]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for step, done in zip(steps, results):
        if isinstance(done, Exception):
            logger.warning(
                "setup_wizard: is_step_done raised for step=%s: %s — leaving done=False",
                step.key, done,
            )
            step.done = False
        else:
            step.done = bool(done)
    return steps


def _group_into_sections(steps: List[SetupStep]) -> List[SetupSection]:
    """Group steps by module_key and produce SetupSection objects.

    Sections appear in SECTION_ORDER; sections not in the order list are
    appended at the end (alphabetical). Within a section, steps are sorted
    by `priority` (ascending — lower goes first).
    """
    by_module: dict[str, List[SetupStep]] = {}
    for step in steps:
        by_module.setdefault(step.module_key, []).append(step)

    # Compose ordered list: SECTION_ORDER first, then any extras
    ordered_modules: List[str] = []
    for m in SECTION_ORDER:
        if m in by_module:
            ordered_modules.append(m)
    extras = sorted(set(by_module.keys()) - set(SECTION_ORDER))
    ordered_modules.extend(extras)

    sections: List[SetupSection] = []
    for module_key in ordered_modules:
        module_steps = sorted(by_module[module_key], key=lambda s: s.priority)
        meta = SECTION_META.get(module_key) or {}
        # Defensive default for unknown modules — keeps the widget from
        # blanking out if a future module is added before SECTION_META.
        title_key = meta.get("title_key") or f"sections.{module_key}.title"
        description_key = meta.get("description_key")

        done_count = sum(1 for s in module_steps if s.done)
        sections.append(SetupSection(
            module_key=module_key,
            title_key=title_key,
            description_key=description_key,
            steps=module_steps,
            done_count=done_count,
            total_count=len(module_steps),
        ))

    return sections


def _aggregate_progress(sections: List[SetupSection]) -> tuple[int, Optional[str]]:
    """Return (progress_pct, next_step_key) across all visible steps.

    `next_step_key` = the first not-done step encountered in render order
    (sections in their order, steps within in priority order). Used by
    the collapsed widget headline.
    """
    total = sum(s.total_count for s in sections)
    if total == 0:
        return 0, None

    done = sum(s.done_count for s in sections)
    pct = round(done / total * 100)

    next_key: Optional[str] = None
    for section in sections:
        for step in section.steps:
            if not step.done:
                next_key = step.key
                break
        if next_key:
            break

    return pct, next_key


# ── Public entry point ───────────────────────────────────────────────────────

async def build_wizard(
    org_id: str,
    user_id: Optional[str] = None,
) -> Optional[SetupWizardResponse]:
    """Compose a full wizard payload for the given org.

    Args:
        org_id:  the requesting user's organization_id (from JWT).
        user_id: the requesting user's id, used by handlers that check
                 account-level state (e.g. global.verify_email).

    Returns:
        SetupWizardResponse on success, None if the org doesn't exist.
        Never raises (degrades gracefully — see step_evaluator).
    """
    org = await _load_org(org_id)
    if not org:
        logger.warning("setup_wizard: org_id=%s not found", org_id)
        return None

    plan_slug = _resolve_plan_slug(org)

    # Snapshot the registry (deep-copied → safe to mutate `done`).
    all_steps = get_all_steps()

    # Determine in-scope modules + load entitlements in parallel.
    in_scope = required_modules_from_registry(all_steps)
    entitlements = await _build_entitlement_map(org_id, org, in_scope)

    # Filter steps by predicate, then compute done flags.
    visible = _filter_visible_steps(all_steps, plan_slug, entitlements)
    visible = await _compute_done_flags(visible, org_id, user_id)

    # Group + sort into sections.
    sections = _group_into_sections(visible)

    # Active modules (derived): those that ended up with at least 1 step
    # visible. Useful for frontend to render module-specific affordances.
    active_modules = sorted({
        s.module_key for s in visible
        if s.module_key != "global"
    })

    # Aggregate.
    progress_pct, next_step_key = _aggregate_progress(sections)
    is_complete = progress_pct >= 100

    return SetupWizardResponse(
        org_id=org_id,
        plan_slug=plan_slug,
        plan_name_key=_plan_name_key(plan_slug),
        active_modules=active_modules,
        sections=sections,
        progress_pct=progress_pct,
        next_step_key=next_step_key,
        is_complete=is_complete,
    )
