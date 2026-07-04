from typing import Optional, List
from database import (
    datasets_collection,
    sales_records_collection,
    expense_records_collection,
    purchase_records_collection,
    fixed_costs_collection
)
from models import Dataset, DatasetType, SalesRecord, ExpenseRecord
from datetime import datetime


async def find_by_id(dataset_id: str, org_id: str) -> Optional[dict]:
    """Find dataset by ID"""
    return await datasets_collection.find_one({
        "id": dataset_id,
        "organization_id": org_id
    }, {"_id": 0})


async def find_by_org(org_id: str, dataset_type: Optional[DatasetType] = None) -> List[dict]:
    """Find all datasets for an organization"""
    query = {"organization_id": org_id}
    if dataset_type:
        query["dataset_type"] = dataset_type.value
    
    cursor = datasets_collection.find(query, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(100)


async def create(dataset: Dataset) -> dict:
    """Create a new dataset"""
    dataset_doc = dataset.model_dump()
    dataset_doc['created_at'] = dataset_doc['created_at'].isoformat()
    await datasets_collection.insert_one(dataset_doc)
    return dataset_doc


async def update(dataset_id: str, update_data: dict) -> bool:
    """Update dataset by ID"""
    result = await datasets_collection.update_one(
        {"id": dataset_id},
        {"$set": update_data}
    )
    return result.modified_count > 0


async def delete(dataset_id: str, org_id: str) -> bool:
    """Delete dataset by ID.
    org_id is required — defense-in-depth so this function can never
    delete a document belonging to a different organisation even if called
    from a context that already did an ownership check at the router layer.
    """
    result = await datasets_collection.delete_one(
        {"id": dataset_id, "organization_id": org_id}
    )
    return result.deleted_count > 0


async def deactivate_by_type(org_id: str, dataset_type: DatasetType, exclude_id: str) -> int:
    """Deactivate all datasets of a type except one"""
    result = await datasets_collection.update_many(
        {
            "organization_id": org_id,
            "dataset_type": dataset_type.value,
            "id": {"$ne": exclude_id}
        },
        {"$set": {"is_active": False}}
    )
    return result.modified_count


async def insert_sales_records(records: List[dict]) -> int:
    """Insert multiple sales records"""
    if not records:
        return 0
    result = await sales_records_collection.insert_many(records)
    return len(result.inserted_ids)


async def insert_expense_records(records: List[dict]) -> int:
    """Insert multiple expense records"""
    if not records:
        return 0
    result = await expense_records_collection.insert_many(records)
    return len(result.inserted_ids)


async def delete_sales_records_by_org(org_id: str) -> int:
    """Delete all sales records for an organization.

    COMPATIBILITY NOTE (v2.1): retained for backward compatibility.
    This function deletes ALL sales records for the entire org (replace
    strategy). New code should prefer delete_records_by_dataset_id() for
    more surgical, per-dataset removal.
    """
    result = await sales_records_collection.delete_many({"organization_id": org_id})
    return result.deleted_count


async def delete_expense_records_by_org(org_id: str) -> int:
    """Delete all expense records for an organization.

    COMPATIBILITY NOTE (v2.1): retained for backward compatibility.
    This function deletes ALL expense records for the entire org (replace
    strategy). New code should prefer delete_records_by_dataset_id() for
    more surgical, per-dataset removal.
    """
    result = await expense_records_collection.delete_many({"organization_id": org_id})
    return result.deleted_count


async def delete_sales_records_by_dataset(dataset_id: str) -> int:
    """Delete all sales records for a dataset"""
    result = await sales_records_collection.delete_many({"dataset_id": dataset_id})
    return result.deleted_count


async def delete_expense_records_by_dataset(dataset_id: str) -> int:
    """Delete all expense records for a dataset"""
    result = await expense_records_collection.delete_many({"dataset_id": dataset_id})
    return result.deleted_count


# ── v2.1 addition ─────────────────────────────────────────────────────────────

async def delete_records_by_dataset_id(dataset_id: str, dataset_type: str) -> int:
    """Delete all records that belong to a specific dataset upload.

    v2.1: unified, type-safe wrapper around the two existing per-type
    functions.  More surgical than delete_*_by_org() — removes only the rows
    produced by a single upload, leaving all other datasets' records intact.

    Args:
        dataset_id:   The `id` field of the Dataset document.
        dataset_type: "sales" or "expenses" (matches DatasetType enum values).

    Returns:
        Number of deleted documents.

    Raises:
        ValueError: if dataset_type is not "sales" or "expenses".
    """
    if dataset_type == "sales":
        return await delete_sales_records_by_dataset(dataset_id)
    elif dataset_type in ("expenses", "expense"):
        return await delete_expense_records_by_dataset(dataset_id)
    else:
        raise ValueError(
            f"Unknown dataset_type {dataset_type!r}. Expected 'sales' or 'expenses'."
        )


async def get_sales_preview(dataset_id: str, limit: int = 20) -> List[dict]:
    """Get preview of sales records"""
    cursor = sales_records_collection.find(
        {"dataset_id": dataset_id},
        {"_id": 0, "id": 0, "organization_id": 0, "dataset_id": 0}
    ).limit(limit)
    return await cursor.to_list(limit)


async def get_expense_preview(dataset_id: str, limit: int = 20) -> List[dict]:
    """Get preview of expense records"""
    cursor = expense_records_collection.find(
        {"dataset_id": dataset_id},
        {"_id": 0, "id": 0, "organization_id": 0, "dataset_id": 0}
    ).limit(limit)
    return await cursor.to_list(limit)


# Purchase records
async def insert_purchase_records(records: List[dict]) -> int:
    """Insert multiple purchase records"""
    if not records:
        return 0
    result = await purchase_records_collection.insert_many(records)
    return len(result.inserted_ids)


async def delete_purchase_records_by_org(org_id: str) -> int:
    """Delete all purchase records for an organization"""
    result = await purchase_records_collection.delete_many({"organization_id": org_id})
    return result.deleted_count


async def delete_purchase_records_by_dataset(dataset_id: str) -> int:
    """Delete all purchase records for a dataset"""
    result = await purchase_records_collection.delete_many({"dataset_id": dataset_id})
    return result.deleted_count


async def get_purchase_preview(dataset_id: str, limit: int = 20) -> List[dict]:
    """Get preview of purchase records"""
    cursor = purchase_records_collection.find(
        {"dataset_id": dataset_id},
        {"_id": 0, "id": 0, "organization_id": 0, "dataset_id": 0}
    ).limit(limit)
    return await cursor.to_list(limit)


# Fixed costs
async def insert_fixed_cost_records(records: List[dict]) -> int:
    """Insert multiple fixed cost records"""
    if not records:
        return 0
    result = await fixed_costs_collection.insert_many(records)
    return len(result.inserted_ids)


async def delete_fixed_cost_records_by_org(org_id: str) -> int:
    """Delete all fixed costs for an organization"""
    result = await fixed_costs_collection.delete_many({"organization_id": org_id})
    return result.deleted_count


async def delete_fixed_cost_records_by_dataset(dataset_id: str) -> int:
    """Delete all fixed costs for a dataset"""
    result = await fixed_costs_collection.delete_many({"dataset_id": dataset_id})
    return result.deleted_count


async def get_fixed_cost_preview(dataset_id: str, limit: int = 20) -> List[dict]:
    """Get preview of fixed cost records"""
    cursor = fixed_costs_collection.find(
        {"dataset_id": dataset_id},
        {"_id": 0, "id": 0, "organization_id": 0, "dataset_id": 0}
    ).limit(limit)
    return await cursor.to_list(limit)
