from typing import Optional, List
from datetime import datetime, timezone

from database import products_collection
from models.product import Product, ProductCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create(organization_id: str, data: ProductCreate) -> Product:
    product = Product(organization_id=organization_id, **data.model_dump())
    doc = product.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await products_collection.insert_one(doc)
    return product


async def find_by_id(product_id: str, organization_id: str) -> Optional[Product]:
    doc = await products_collection.find_one(
        {"id": product_id, "organization_id": organization_id}
    )
    return Product(**doc) if doc else None


async def find_by_org(
    organization_id: str,
    active_only: bool = True,
    limit: int = 500,
) -> List[Product]:
    query: dict = {"organization_id": organization_id}
    if active_only:
        query["is_active"] = True
    cursor = products_collection.find(query).sort("name", 1).limit(limit)
    return [Product(**doc) async for doc in cursor]


async def update(
    product_id: str,
    organization_id: str,
    updates: dict,
) -> Optional[Product]:
    updates["updated_at"] = _now().isoformat()
    result = await products_collection.update_one(
        {"id": product_id, "organization_id": organization_id},
        {"$set": updates},
    )
    if result.matched_count == 0:
        return None
    return await find_by_id(product_id, organization_id)


async def deactivate(product_id: str, organization_id: str) -> bool:
    result = await products_collection.update_one(
        {"id": product_id, "organization_id": organization_id},
        {"$set": {"is_active": False, "updated_at": _now().isoformat()}},
    )
    return result.modified_count > 0
