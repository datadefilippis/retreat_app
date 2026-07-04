"""
Entitlement-based step visibility filter (Fase 2 Track F — Step 3).

Decides whether a setup step should be SHOWN to a given org based on:
  - per-(module, feature) entitlement (>0 or unlimited = visible)
  - plan slug allow-list / deny-list

The filter is purely declarative: it inspects the step's `predicate` and
the org's entitlement map. Never queries Mongo directly — `wizard_service`
prefetches entitlements once per request and feeds them in.

Why entitlement-based, not plan-based:
  Hardcoding "show commerce steps if plan==core" would break the moment
  the system_admin reshapes plans/addons in the catalog UI. By asking
  "is feature X entitled?" the wizard adapts automatically. If admin
  enables `commerce_starter` in the `free` plan, free orgs immediately
  start seeing the commerce section on next refresh — zero deploy.

Visibility rules (AND-combined, all must pass):

  1. feature_required (e.g. "commerce.orders_monthly")
       → effective_limit(org, module, feature) > 0 OR == -1 (unlimited)

  2. plan_required (e.g. ["core", "pro"])
       → org.commercial_plan_slug ∈ allow-list (skipped if list empty)

  3. plan_excludes (e.g. ["enterprise"])
       → org.commercial_plan_slug ∉ deny-list

A step with no predicate is always visible (when its section exists).
"""

from __future__ import annotations

import logging
from typing import Dict

from .step_models import SetupStep

logger = logging.getLogger(__name__)


# Entitlement map shape used by `should_show_step`:
#
#   {
#     "commerce":         {"orders_monthly": 200, "stores_max": 1, ...},
#     "cashflow_monitor": {"data_rows": -1, "email_alerts": 1, ...},
#     "ai_assistant":     {"chat": 80, "insights": 5, ...},
#   }
#
# `wizard_service.build_wizard` builds this dict by calling
# `module_access.get_module_entitlements` for each module that has at
# least one step in the registry.
EntitlementMap = Dict[str, Dict[str, int]]


def is_feature_entitled(
    entitlements: EntitlementMap,
    module_key: str,
    feature_key: str,
) -> bool:
    """True iff entitlements[module][feature] > 0 OR == -1 (unlimited).

    Returns False on:
      - missing module key
      - missing feature key
      - feature limit explicitly set to 0 (= disabled by plan)
    """
    module = entitlements.get(module_key) or {}
    limit = module.get(feature_key, 0)
    # -1 = unlimited; >0 = quota; 0 = disabled
    return limit == -1 or limit > 0


def should_show_step(
    step: SetupStep,
    org_plan_slug: str,
    entitlements: EntitlementMap,
) -> bool:
    """Decide whether `step` should be rendered for an org.

    Args:
        step:           the step from STEP_REGISTRY (with its predicate).
        org_plan_slug:  current commercial_plan_slug on the Organization.
        entitlements:   pre-built map of effective limits per module/feature.

    Returns:
        True if the step passes ALL visibility rules in its predicate.
    """
    pred = step.predicate
    if pred is None:
        # No predicate → always visible (for orgs whose section is shown).
        return True

    # Rule 1: feature_required must be entitled.
    if pred.feature_required:
        try:
            module_key, feature_key = pred.feature_required.split(".", 1)
        except ValueError:
            # Malformed predicate. Log but don't crash — hide the step
            # rather than leak it.
            logger.warning(
                "setup_wizard: malformed feature_required=%r on step %s — hiding step",
                pred.feature_required, step.key,
            )
            return False

        if not is_feature_entitled(entitlements, module_key, feature_key):
            return False

    # Rule 2: plan_required allow-list (if non-empty).
    if pred.plan_required and org_plan_slug not in pred.plan_required:
        return False

    # Rule 3: plan_excludes deny-list.
    if pred.plan_excludes and org_plan_slug in pred.plan_excludes:
        return False

    return True


def required_modules_from_registry(steps: list[SetupStep]) -> list[str]:
    """Return the unique list of module_keys referenced by step predicates.

    Used by wizard_service to know which modules to query entitlements for.
    Includes all module_keys from feature_required predicates, plus the
    section module_keys themselves (so a section always has its
    entitlement loaded even if no step has a predicate).
    """
    modules: set[str] = set()
    for step in steps:
        # Step's own section module is always relevant.
        if step.module_key and step.module_key != "global":
            modules.add(step.module_key)
        # Predicate-referenced module
        if step.predicate and step.predicate.feature_required:
            try:
                module_key, _ = step.predicate.feature_required.split(".", 1)
                modules.add(module_key)
            except ValueError:
                pass
    return sorted(modules)
