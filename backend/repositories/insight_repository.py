from typing import Optional, List
from datetime import datetime
from database import insights_collection
from models import Insight


def doc_to_insight(doc: dict) -> Insight:
    """Convert a raw MongoDB document to an Insight model.

    Handles both ISO-string and datetime objects for the created_at field,
    so callers never need to repeat this conversion.
    """
    created_at = doc["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    return Insight(
        id=doc["id"],
        organization_id=doc["organization_id"],
        module_key=doc["module_key"],
        title=doc["title"],
        content=doc["content"],
        metrics_context=doc.get("metrics_context", {}),
        created_at=created_at,
        period_start=doc["period_start"],
        period_end=doc["period_end"],
    )


async def find_by_id(insight_id: str, org_id: str) -> Optional[dict]:
    """Find insight by ID"""
    return await insights_collection.find_one({
        "id": insight_id,
        "organization_id": org_id
    }, {"_id": 0})


async def find_by_org(org_id: str, module_key: Optional[str] = None, limit: int = 20) -> List[dict]:
    """Find insights for an organization"""
    query = {"organization_id": org_id}
    if module_key:
        query["module_key"] = module_key
    
    cursor = insights_collection.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(limit)


async def find_latest(org_id: str, module_key: str = "cashflow_monitor") -> Optional[dict]:
    """Find the latest insight for a module"""
    cursor = insights_collection.find(
        {"organization_id": org_id, "module_key": module_key},
        {"_id": 0}
    ).sort("created_at", -1).limit(1)
    
    results = await cursor.to_list(1)
    return results[0] if results else None


async def create(insight: Insight) -> dict:
    """Create a new insight"""
    insight_doc = insight.model_dump()
    insight_doc['created_at'] = insight_doc['created_at'].isoformat()
    await insights_collection.insert_one(insight_doc)
    return insight_doc


async def delete(insight_id: str, org_id: str) -> bool:
    """Delete insight by ID"""
    result = await insights_collection.delete_one({
        "id": insight_id,
        "organization_id": org_id
    })
    return result.deleted_count > 0
