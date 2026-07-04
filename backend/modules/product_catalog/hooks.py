"""
Product Catalog Hooks — post-upload triggers.

Refreshes product_metrics when new data is uploaded.
"""

import logging
from database import sales_records_collection

logger = logging.getLogger(__name__)


async def post_upload_hook(org_id: str) -> None:
    """Refresh product metrics after data upload.

    Only runs if there are sales_records with product_id linked.
    Fire-and-forget — never raises.
    """
    try:
        linked = await sales_records_collection.count_documents(
            {"organization_id": org_id, "product_id": {"$ne": None, "$exists": True}},
            limit=1,
        )
        if linked == 0:
            logger.debug("product_catalog hook: no linked products for org=%s, skipping", org_id)
            return

        from modules.product_catalog.service import refresh_product_metrics
        result = await refresh_product_metrics(org_id)
        logger.info(
            "product_catalog hook: refreshed %d products for org=%s",
            result.get("products_computed", 0), org_id,
        )
    except Exception as exc:
        logger.error("product_catalog hook failed for org=%s: %s", org_id, exc)
