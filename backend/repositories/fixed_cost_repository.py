from typing import Optional, List
from datetime import datetime, timezone

from database import fixed_costs_collection
from models.financial_record import FixedCost, FixedCostBase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create(organization_id: str, data: dict) -> FixedCost:
    cost = FixedCost(organization_id=organization_id, **data)
    doc = cost.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await fixed_costs_collection.insert_one(doc)
    return cost


async def find_by_id(cost_id: str, organization_id: str) -> Optional[FixedCost]:
    doc = await fixed_costs_collection.find_one(
        {"id": cost_id, "organization_id": organization_id}
    )
    return FixedCost(**doc) if doc else None


async def find_by_org(
    organization_id: str,
    active_only: bool = True,
    category: Optional[str] = None,
    limit: int = 200,
) -> List[FixedCost]:
    query: dict = {"organization_id": organization_id}
    if active_only:
        query["is_active"] = True
    if category:
        query["category"] = category
    cursor = fixed_costs_collection.find(query).sort("name", 1).limit(limit)
    return [FixedCost(**doc) async for doc in cursor]


async def update(cost_id: str, organization_id: str, updates: dict) -> Optional[FixedCost]:
    updates["updated_at"] = _now()
    result = await fixed_costs_collection.update_one(
        {"id": cost_id, "organization_id": organization_id},
        {"$set": updates},
    )
    if result.matched_count == 0:
        return None
    return await find_by_id(cost_id, organization_id)


async def deactivate(cost_id: str, organization_id: str) -> bool:
    result = await fixed_costs_collection.update_one(
        {"id": cost_id, "organization_id": organization_id},
        {"$set": {"is_active": False, "updated_at": _now()}},
    )
    return result.modified_count > 0


async def insert_many(records: List[dict]) -> int:
    """Insert multiple fixed cost records"""
    if not records:
        return 0
    result = await fixed_costs_collection.insert_many(records)
    return len(result.inserted_ids)


async def delete_one(record_id: str, org_id: str) -> bool:
    """Delete a single fixed cost record"""
    result = await fixed_costs_collection.delete_one({
        "id": record_id,
        "organization_id": org_id
    })
    return result.deleted_count > 0


async def delete_by_org(org_id: str) -> int:
    """Delete all fixed costs for an organization"""
    result = await fixed_costs_collection.delete_many({"organization_id": org_id})
    return result.deleted_count


async def delete_by_dataset(dataset_id: str) -> int:
    """Delete all fixed costs for a dataset"""
    result = await fixed_costs_collection.delete_many({"dataset_id": dataset_id})
    return result.deleted_count


async def get_preview(dataset_id: str, limit: int = 20) -> List[dict]:
    """Get preview of fixed cost records"""
    cursor = fixed_costs_collection.find(
        {"dataset_id": dataset_id},
        {"_id": 0, "id": 0, "organization_id": 0, "dataset_id": 0}
    ).limit(limit)
    return await cursor.to_list(limit)
