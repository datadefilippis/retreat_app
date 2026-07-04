"""
Commerce Module — gate module for commerce features.

Activating this module unlocks: Orders, Store, Calendar, Products
in the sidebar navigation. Commerce-flavored operational logic lives
in order_service, public router, etc.

Wave 7B.1 (2026-05): the module gained an AI tools surface
(modules.commerce.ai_tools), with 6 tools moved here from
cashflow_monitor — order pipeline, fulfillment, payments, events,
bookings and rentals. These tools are now correctly gated by the
`commerce` entitlement instead of `cashflow_monitor`.
"""

from core.module_registry import register, ModuleDefinition
from modules.commerce.ai_tools import TOOL_DEFINITIONS as commerce_tool_defs
from modules.commerce.ai_tools import execute_tool as commerce_execute_tool

register(ModuleDefinition(
    module_key="commerce",
    module_name="Commerce",
    is_available=True,
    description="Gestione ordini, store, calendario e prodotti. Sblocca le funzionalita di vendita online e in negozio.",
    category="operations",
    icon="shopping-bag",
    ai_tool_definitions=commerce_tool_defs,
    ai_tool_executor=commerce_execute_tool,
))
