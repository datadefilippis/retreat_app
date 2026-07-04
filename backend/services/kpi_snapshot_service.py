"""
KPI Snapshot Service — Phase 2 / arch-v1.

Computes pre-aggregated KPI metrics from live sales/expense records
and persists them in the kpi_snapshots collection.

Called as a non-blocking side-effect after every dataset upload so
that dashboards can read from snapshots instead of running heavy
aggregations on every request (Phase 3).

Design decisions:
- Never raises: all errors are caught and logged so the caller's
  primary flow (upload) is never interrupted.
- Upsert semantics: safe to call multiple times for the same period.
- Decoupled: no dependency on dataset_service or ai_service.
- Module-agnostic dispatcher: actual KPI computation logic lives in
  each module's snapshot_builder, registered via core.module_registry.
  The lazy import of core.module_registry inside compute_and_save()
  prevents any circular-import risk at module load time.

Public API (signatures unchanged):
  compute_and_save(org_id, module_key, granularity, reference_date) -> bool
  compute_all_granularities(org_id, module_key) -> None
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from repositories.kpi_snapshot_repository import upsert as upsert_snapshot
from models.kpi_snapshot import KPISnapshotBase, KPISnapshotGranularity

logger = logging.getLogger(__name__)


def _period_bounds(granularity: str, reference_date: Optional[str] = None) -> tuple[str, str]:
    """Return (period_start, period_end) ISO strings for the given granularity."""
    today = datetime.now(timezone.utc).date()
    ref = datetime.strptime(reference_date, "%Y-%m-%d").date() if reference_date else today

    if granularity == KPISnapshotGranularity.MONTHLY:
        start = ref.replace(day=1)
        # Last day of same month
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(days=1)
    elif granularity == KPISnapshotGranularity.WEEKLY:
        start = ref - timedelta(days=ref.weekday())  # Monday
        end = start + timedelta(days=6)
    elif granularity == KPISnapshotGranularity.QUARTERLY:
        q = (ref.month - 1) // 3
        start = ref.replace(month=q * 3 + 1, day=1)
        end_month = q * 3 + 3
        end = (start.replace(month=end_month, day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    else:  # DAILY or fallback
        start = ref
        end = ref

    return start.isoformat(), end.isoformat()


async def compute_and_save(
    org_id: str,
    module_key: str = "cashflow_monitor",
    granularity: str = KPISnapshotGranularity.MONTHLY,
    reference_date: Optional[str] = None,
) -> bool:
    """Compute KPIs for the given period and persist a snapshot.

    Dispatches to the snapshot_builder registered for module_key in
    core.module_registry.  Returns True on success, False on any error
    (never raises).
    """
    # Lazy import avoids circular-import risk: kpi_snapshot_service is
    # imported by hooks.py at call time; hooks.py is imported by
    # cashflow __init__.py which also imports core.module_registry.
    from core.module_registry import get as registry_get

    module = registry_get(module_key)
    if module is None or module.snapshot_builder is None:
        logger.warning(
            "kpi_snapshot_service: no snapshot_builder registered for module_key=%s",
            module_key,
        )
        return False

    try:
        period_start, period_end = _period_bounds(granularity, reference_date)

        metrics = await module.snapshot_builder(org_id, period_start, period_end)

        if not metrics.get("period_days"):
            logger.info(
                "kpi_snapshot_service: no data for org=%s period=%s→%s",
                org_id, period_start, period_end,
            )
            return False

        snapshot_base = KPISnapshotBase(
            module_key=module_key,
            period_start=period_start,
            period_end=period_end,
            granularity=granularity,
            metrics=metrics,
        )

        await upsert_snapshot(org_id, snapshot_base)
        logger.info(
            "kpi_snapshot_service: saved snapshot org=%s module=%s period=%s→%s",
            org_id, module_key, period_start, period_end,
        )
        return True

    except Exception as exc:
        logger.error("kpi_snapshot_service: error org=%s: %s", org_id, exc, exc_info=True)
        return False


async def compute_all_granularities(org_id: str, module_key: str = "cashflow_monitor") -> None:
    """Convenience helper: compute monthly + weekly snapshots for the current period.

    Called after every dataset upload as a fire-and-forget side-effect.
    Both granularities are independent — run in parallel.
    Public signature unchanged.
    """
    import asyncio
    await asyncio.gather(
        compute_and_save(org_id, module_key=module_key, granularity=KPISnapshotGranularity.MONTHLY),
        compute_and_save(org_id, module_key=module_key, granularity=KPISnapshotGranularity.WEEKLY),
    )


async def invalidate_for_org(org_id: str, module_key: Optional[str] = None) -> int:
    """Delete stale snapshots when an org's underlying data changes.

    If ``module_key`` is given, deletes only snapshots for that module.
    If ``module_key`` is None, deletes ALL snapshots for the org.

    Returns the number of snapshots deleted.
    Never raises — errors are logged and 0 is returned.
    """
    from repositories.kpi_snapshot_repository import (
        delete_by_org,
        delete_by_org_and_module,
    )
    try:
        if module_key:
            count = await delete_by_org_and_module(org_id, module_key)
        else:
            count = await delete_by_org(org_id)
        logger.info(
            "kpi_snapshot_service: invalidated %d snapshots for org=%s module=%s",
            count, org_id, module_key or "ALL",
        )
        return count
    except Exception as exc:
        logger.error(
            "kpi_snapshot_service: invalidation error org=%s module=%s: %s",
            org_id, module_key, exc, exc_info=True,
        )
        return 0


async def refresh_for_org(org_id: str, module_key: str = "cashflow_monitor") -> None:
    """Invalidate stale snapshots then immediately recompute fresh ones.

    Convenience wrapper used after a dataset deletion: we first remove the
    now-stale snapshots, then rebuild them from the remaining data (if any).
    Like compute_all_granularities, this never raises.
    """
    await invalidate_for_org(org_id, module_key=module_key)
    await compute_all_granularities(org_id, module_key=module_key)
