"""
Column Mapping and Dataset Column Profile repositories.
"""
from typing import Optional, List
from datetime import datetime, timezone

from database import column_mappings_collection, dataset_column_profiles_collection
from models.column_mapping import (
    ColumnMapping,
    ColumnMappingBase,
    DatasetColumnProfile,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Column Mappings ───────────────────────────────────────────────────────────

async def create_mapping(
    organization_id: str, data: ColumnMappingBase
) -> ColumnMapping:
    mapping = ColumnMapping(organization_id=organization_id, **data.model_dump())
    doc = mapping.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await column_mappings_collection.insert_one(doc)
    return mapping


async def find_mappings_by_org_and_type(
    organization_id: str, dataset_type: str
) -> List[ColumnMapping]:
    cursor = column_mappings_collection.find(
        {
            "organization_id": organization_id,
            "dataset_type": dataset_type,
            "is_active": True,
        }
    )
    return [ColumnMapping(**doc) async for doc in cursor]


async def deactivate_mapping(mapping_id: str, organization_id: str) -> bool:
    result = await column_mappings_collection.update_one(
        {"id": mapping_id, "organization_id": organization_id},
        {"$set": {"is_active": False, "updated_at": _now().isoformat()}},
    )
    return result.modified_count > 0


async def deactivate_by_source_column(
    organization_id: str, dataset_type: str, source_column: str
) -> None:
    """Deactivate all active mappings for a specific (org, dataset_type, source_column) triple.

    Used by the batch endpoint before inserting a replacement mapping so that
    the collection never contains two active rules for the same column.
    Idempotent: safe to call when no matching active mapping exists.
    Never raises.
    """
    await column_mappings_collection.update_many(
        {
            "organization_id": organization_id,
            "dataset_type": dataset_type,
            "source_column": source_column,
            "is_active": True,
        },
        {"$set": {"is_active": False, "updated_at": _now().isoformat()}},
    )


async def save_user_mapping(
    org_id: str, dataset_type: str, mapping: dict
) -> None:
    """Persist user-provided column mappings from the interactive dialog.

    For each {file_column → target_field} entry, deactivates any existing
    mapping for that source column and creates a new active one.
    Non-blocking: silently ignores individual mapping failures.
    """
    for source_col, target_field in mapping.items():
        try:
            await deactivate_by_source_column(org_id, dataset_type, source_col)
            await create_mapping(
                org_id,
                ColumnMappingBase(
                    dataset_type=dataset_type,
                    source_column=source_col,
                    target_field=target_field,
                ),
            )
        except Exception:
            pass  # non-blocking


# ── Dataset Column Profiles ───────────────────────────────────────────────────

async def upsert_profile(profile: DatasetColumnProfile) -> DatasetColumnProfile:
    """Insert or replace profile for a given dataset_id."""
    doc = profile.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await dataset_column_profiles_collection.replace_one(
        {"dataset_id": profile.dataset_id},
        doc,
        upsert=True,
    )
    return profile


async def find_profile_by_dataset(dataset_id: str) -> Optional[DatasetColumnProfile]:
    doc = await dataset_column_profiles_collection.find_one(
        {"dataset_id": dataset_id}
    )
    return DatasetColumnProfile(**doc) if doc else None
