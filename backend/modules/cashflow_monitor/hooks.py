"""
Cashflow Monitor — post-upload hooks.

Registered as post_upload_hooks in modules/cashflow_monitor/__init__.py.

These hooks are called fire-and-forget by dataset_service after every
successful dataset upload.  They must never raise; errors are caught
by the caller (_run_post_upload_hooks in dataset_service.py).

Import strategy:
  All service imports are lazy (inside the function body) to break any
  potential circular-import chain at module load time:
    cashflow __init__ → hooks → kpi_snapshot_service → core.module_registry
  The actual imports happen at call time, well after all module-level
  code has finished running.
"""
import logging

logger = logging.getLogger(__name__)


async def post_upload_hook(org_id: str) -> None:
    """Recompute KPI snapshots and auto-generate alerts after a dataset upload.

    Step 1 — Recompute KPI snapshots (monthly + weekly) from the freshly
    ingested data.  This replaces the behaviour previously hardcoded in
    dataset_service.py step 10.

    Step 2 — Auto-generate anomaly alerts.  This runs immediately after
    the snapshot recompute so that the user sees up-to-date alerts the
    moment they land on the dashboard after an upload, without needing to
    click "Genera Alert" manually.  Deduplication inside alert_service
    prevents re-inserting alerts that are already open.

    Both steps are fire-and-forget: errors are caught internally and
    logged; this function never raises.
    """
    # ── Step 1: recompute KPI snapshots ──────────────────────────────────────
    from services.kpi_snapshot_service import compute_all_granularities
    await compute_all_granularities(org_id, module_key="cashflow_monitor")

    # ── Step 2: auto-generate alerts ─────────────────────────────────────────
    try:
        from services.alert_service import generate_and_save_alerts
        result = await generate_and_save_alerts(org_id)
        logger.info(
            "post_upload_hook: %s for org=%s",
            result.get("message", "alerts done"), org_id,
        )
    except Exception as exc:
        logger.error(
            "post_upload_hook: alert generation failed for org=%s: %s",
            org_id, exc, exc_info=True,
        )
