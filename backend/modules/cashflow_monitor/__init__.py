"""
Cashflow Monitor module — bootstrap registration.

This file is executed automatically by Python when anything inside the
`modules.cashflow_monitor` package is first imported.  In the current
server.py, that happens at module level via:

    from modules.cashflow_monitor.router import router as cashflow_router

That import fires before the ASGI server accepts any request, so the
module is always registered before compute_and_save() or any post-upload
hook can be called.

Registration is idempotent (re-importing this file is safe).
"""
from core.module_registry import ModuleDefinition, register
from modules.cashflow_monitor.snapshot_builder import build_snapshot
from modules.cashflow_monitor.hooks import post_upload_hook
from modules.cashflow_monitor.alert_engine import run_alert_engine
from modules.cashflow_monitor.insight_builder import build_insight_context
from modules.cashflow_monitor.overview_builder import build_overview
from modules.cashflow_monitor.digest_builder import build_digest
from modules.cashflow_monitor.alert_analysis import analyze_alerts
from modules.cashflow_monitor.health_explanation import generate_health_explanation_ai
from modules.cashflow_monitor.ai_tools import TOOL_DEFINITIONS as cashflow_tool_defs
from modules.cashflow_monitor.ai_tools import execute_tool as cashflow_execute_tool

register(ModuleDefinition(
    module_key="cashflow_monitor",
    module_name="Daily Cashflow Monitor",
    is_available=True,
    description="Track and analyze daily cash inflows and outflows with AI-powered insights",
    category="finance",
    icon="trending-up",
    snapshot_builder=build_snapshot,
    post_upload_hooks=[post_upload_hook],
    alert_rules=run_alert_engine,
    insight_builder=build_insight_context,
    overview_builder=build_overview,
    digest_builder=build_digest,
    alert_analysis=analyze_alerts,
    health_explanation_ai=generate_health_explanation_ai,
    ai_tool_definitions=cashflow_tool_defs,
    ai_tool_executor=cashflow_execute_tool,
))
