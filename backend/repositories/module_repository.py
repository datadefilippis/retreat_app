from typing import Optional, List
from database import organization_modules_collection
from models import OrganizationModule


async def find_by_org(org_id: str) -> List[dict]:
    """Find all modules for an organization"""
    cursor = organization_modules_collection.find(
        {"organization_id": org_id, "is_active": True},
        {"_id": 0}
    )
    return await cursor.to_list(100)


async def find_by_key(org_id: str, module_key: str) -> Optional[dict]:
    """Find a specific module for an organization"""
    return await organization_modules_collection.find_one({
        "organization_id": org_id,
        "module_key": module_key
    }, {"_id": 0})


async def create(module: OrganizationModule) -> dict:
    """Create/activate a module for an organization"""
    module_doc = module.model_dump()
    module_doc['activated_at'] = module_doc['activated_at'].isoformat()
    await organization_modules_collection.insert_one(module_doc)
    return module_doc


async def activate(org_id: str, module_key: str) -> bool:
    """Activate a module"""
    result = await organization_modules_collection.update_one(
        {"organization_id": org_id, "module_key": module_key},
        {"$set": {"is_active": True}}
    )
    return result.modified_count > 0


async def deactivate(org_id: str, module_key: str) -> bool:
    """Deactivate a module"""
    result = await organization_modules_collection.update_one(
        {"organization_id": org_id, "module_key": module_key},
        {"$set": {"is_active": False}}
    )
    return result.modified_count > 0


async def delete(org_id: str, module_key: str) -> bool:
    """Delete a module record"""
    result = await organization_modules_collection.delete_one({
        "organization_id": org_id,
        "module_key": module_key
    })
    return result.deleted_count > 0
