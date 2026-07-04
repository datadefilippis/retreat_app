"""
Product Catalog Module — per-product analytics with margins, trends, and ABC.

Materializes product_metrics from sales_records and purchase_records.
Provides AI tools for product intelligence queries.
"""

from core.module_registry import register, ModuleDefinition
from .snapshot_builder import build_snapshot
from .hooks import post_upload_hook
from .service import build_overview
from .ai_tools import TOOL_DEFINITIONS, execute_tool

register(ModuleDefinition(
    module_key="product_catalog",
    module_name="Catalogo Prodotti",
    is_available=True,
    description="Product intelligence: margins, ABC classification, trends, and performance analytics per product",
    category="intelligence",
    icon="Package",
    snapshot_builder=build_snapshot,
    post_upload_hooks=[post_upload_hook],
    overview_builder=build_overview,
    ai_tool_definitions=TOOL_DEFINITIONS,
    ai_tool_executor=execute_tool,
))
