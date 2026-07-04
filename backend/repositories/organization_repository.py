from typing import Optional
from database import organizations_collection
from models import Organization


async def find_by_id(org_id: str) -> Optional[dict]:
    """Find organization by ID"""
    return await organizations_collection.find_one({"id": org_id}, {"_id": 0})


async def find_by_name(name: str) -> Optional[dict]:
    """Find organization by name"""
    return await organizations_collection.find_one({"name": name}, {"_id": 0})


async def create(org: Organization) -> dict:
    """Create a new organization"""
    org_doc = org.model_dump()
    org_doc['created_at'] = org_doc['created_at'].isoformat()
    org_doc['updated_at'] = org_doc['updated_at'].isoformat()
    await organizations_collection.insert_one(org_doc)
    return org_doc


async def update(org_id: str, update_data: dict) -> bool:
    """Update organization by ID"""
    result = await organizations_collection.update_one(
        {"id": org_id},
        {"$set": update_data}
    )
    return result.modified_count > 0


async def delete(org_id: str) -> bool:
    """Delete organization by ID"""
    result = await organizations_collection.delete_one({"id": org_id})
    return result.deleted_count > 0
