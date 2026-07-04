"""Post-upload hooks for the customer_insights module.

Migrated from ``modules.customers_light.hooks``. Same fire-and-forget
contract: dataset_service calls it after every successful upload, we
refresh the materialised customer metrics so the analytics layer
reflects the new sales rows immediately.

Never raises — errors are caught + logged. The dataset upload must
not fail because the analytics refresh blew up.
"""

import logging

logger = logging.getLogger(__name__)


async def post_upload_hook(org_id: str) -> None:
    """Refresh customer metrics after a dataset upload."""
    try:
        from modules.customer_insights import repository
        linked = await repository.count_linked_sales(org_id)
        if linked == 0:
            return

        from modules.customer_insights.refresh import refresh_customer_metrics
        result = await refresh_customer_metrics(org_id)
        logger.info(
            "customer_insights post_upload_hook: %s for org=%s",
            result.get("message", "done"), org_id,
        )
    except Exception as exc:
        logger.error(
            "customer_insights post_upload_hook failed for org=%s: %s",
            org_id, exc, exc_info=True,
        )
