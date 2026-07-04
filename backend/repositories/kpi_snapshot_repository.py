"""
KPI Snapshot repository.

Upsert semantics: one snapshot per (organization_id, module_key, period_start).
"""
from typing import Optional, List
from datetime import datetime, timezone

from database import kpi_snapshots_collection
from models.kpi_snapshot import KPISnapshot, KPISnapshotBase


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def upsert(organization_id: str, data: KPISnapshotBase) -> KPISnapshot:
    """Insert or replace snapshot for the same period."""
    snapshot = KPISnapshot(organization_id=organization_id, **data.model_dump())
    doc = snapshot.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await kpi_snapshots_collection.replace_one(
        {
            "organization_id": organization_id,
            "module_key": data.module_key,
            "period_start": data.period_start,
        },
        doc,
        upsert=True,
    )
    return snapshot


async def find_latest(
    organization_id: str,
    module_key: str,
    limit: int = 12,
) -> List[KPISnapshot]:
    cursor = (
        kpi_snapshots_collection.find(
            {"organization_id": organization_id, "module_key": module_key}
        )
        .sort("period_start", -1)
        .limit(limit)
    )
    return [KPISnapshot(**doc) async for doc in cursor]


async def find_by_period(
    organization_id: str,
    module_key: str,
    period_start: str,
) -> Optional[KPISnapshot]:
    doc = await kpi_snapshots_collection.find_one(
        {
            "organization_id": organization_id,
            "module_key": module_key,
            "period_start": period_start,
        }
    )
    return KPISnapshot(**doc) if doc else None


async def delete_by_org(organization_id: str) -> int:
    """Delete ALL snapshots for an organisation (e.g. when all data is wiped).

    Returns the number of documents deleted.
    """
    result = await kpi_snapshots_collection.delete_many(
        {"organization_id": organization_id}
    )
    return result.deleted_count


async def delete_by_org_and_module(organization_id: str, module_key: str) -> int:
    """Delete all snapshots for a specific (org, module) pair.

    Called when a dataset that feeds the module is deleted, so that
    stale pre-computed metrics are not served to the dashboard.

    Returns the number of documents deleted.
    """
    result = await kpi_snapshots_collection.delete_many(
        {"organization_id": organization_id, "module_key": module_key}
    )
    return result.deleted_count
