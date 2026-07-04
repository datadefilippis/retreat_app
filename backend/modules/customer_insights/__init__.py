"""customer_insights — the single source of customer-intelligence truth.

Replaces the legacy ``modules.customers_light`` package as part of
the Phase-3 single-brain consolidation. Contains:

  formulas.py            pure formula layer (Phase 0)
  period_filter.py       period parsing + previous_period (Phase 1)
  cohort.py              cohort retention math (Phase 1)
  repository.py          materialised reads + writes + period-aware
                         queries + cohort source data + timeline +
                         outreach action audit reads (Phase 1+3)
  service.py             new period-aware orchestrator (Phase 1)
  router.py              new /api/customer-insights/* HTTP surface
                         (Phase 1, extended Phase 3 with outreach)
  refresh.py             writer for customer_metrics — fired by the
                         post_upload_hook + the legacy admin refresh
                         endpoint (migrated from customers_light)
  legacy_overview.py     bit-for-bit ``build_overview`` shape that the
                         platform module dispatcher serves at
                         /api/modules/customers_light/overview
                         (kept for downstream digest consumers)
  snapshot_builder.py    KPI snapshot builder for kpi_snapshots
  hooks.py               post_upload_hook (refresh on dataset upload)
  ai_tools.py            7 LLM tool definitions + executor

Critical migration constraint: the ``ModuleDefinition`` is registered
with ``module_key="customers_light"`` so:
  • orgs that already had this module activated keep access
  • pricing plans (``customers_light_free``, ``customers_light_pro``)
    keep their entitlement match
  • the AI tool registry collects these 7 tools for the same orgs as
    before — LLM behaviour identical
The module's PYTHON folder name changed (customer_insights/) but the
PUBLIC IDENTITY (module_key) stayed the same.

Co-existence with the legacy ``modules.customers_light`` package
during this migration: the legacy package is deprecated. After the
final cleanup commit, the customers_light/ folder is removed entirely
and any remaining import in the codebase is a bug.
"""

from core.module_registry import ModuleDefinition, register

from .ai_tools import TOOL_DEFINITIONS as ci_tool_defs
from .ai_tools import execute_tool as ci_execute_tool
from .hooks import post_upload_hook
from .legacy_overview import build_overview
from .snapshot_builder import build_snapshot
from .router import router

register(ModuleDefinition(
    # ``module_key="customers_light"`` is INTENTIONAL — see docstring:
    # the public identity (entitlements, AI tool dispatch, org module
    # records) is preserved. Only the Python code location changed.
    module_key="customers_light",
    module_name="Customers Light",
    is_available=True,
    description="Customer intelligence: segmenti, lifetime value, retention, outreach.",
    category="Customer",
    icon="Users",
    snapshot_builder=build_snapshot,
    post_upload_hooks=[post_upload_hook],
    overview_builder=build_overview,
    ai_tool_definitions=ci_tool_defs,
    ai_tool_executor=ci_execute_tool,
))


__all__ = ["router"]
