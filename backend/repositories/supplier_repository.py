import re
import logging
from typing import Optional, List
from datetime import datetime, timezone

from database import suppliers_collection
from models.supplier import Supplier, SupplierCreate
from models.common import generate_id

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create(organization_id: str, data: SupplierCreate) -> Supplier:
    supplier = Supplier(organization_id=organization_id, **data.model_dump())
    doc = supplier.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await suppliers_collection.insert_one(doc)
    return supplier


async def find_by_id(supplier_id: str, organization_id: str) -> Optional[Supplier]:
    doc = await suppliers_collection.find_one(
        {"id": supplier_id, "organization_id": organization_id}
    )
    return Supplier(**doc) if doc else None


async def find_by_org(
    organization_id: str,
    active_only: bool = True,
    limit: int = 200,
) -> List[Supplier]:
    query: dict = {"organization_id": organization_id}
    if active_only:
        query["is_active"] = True
    cursor = suppliers_collection.find(query).sort("name", 1).limit(limit)
    return [Supplier(**doc) async for doc in cursor]


async def update(
    supplier_id: str,
    organization_id: str,
    updates: dict,
) -> Optional[Supplier]:
    updates["updated_at"] = _now().isoformat()
    result = await suppliers_collection.update_one(
        {"id": supplier_id, "organization_id": organization_id},
        {"$set": updates},
    )
    if result.matched_count == 0:
        return None
    return await find_by_id(supplier_id, organization_id)


async def deactivate(supplier_id: str, organization_id: str) -> bool:
    result = await suppliers_collection.update_one(
        {"id": supplier_id, "organization_id": organization_id},
        {"$set": {"is_active": False, "updated_at": _now().isoformat()}},
    )
    return result.modified_count > 0


async def get_or_create_by_name(org_id: str, supplier_name: str) -> Supplier:
    """Find supplier by normalised name or create a new one.

    Case-insensitive exact match (lower + strip). If not found, creates
    a new supplier tagged with metadata.auto_created=True.

    Idempotent: calling twice with the same name returns the same supplier.
    Non-blocking by design — caller wraps in try/except.
    """
    clean_name = supplier_name.strip()
    if not clean_name:
        raise ValueError("Empty supplier name")

    # Case-insensitive exact match using regex anchor
    escaped = re.escape(clean_name)
    existing = await suppliers_collection.find_one(
        {"organization_id": org_id, "name": {"$regex": f"^{escaped}$", "$options": "i"}, "is_active": True},
    )
    if existing:
        return Supplier(**existing)

    # Create new supplier
    now = _now().isoformat()
    doc = {
        "id": generate_id(),
        "organization_id": org_id,
        "name": clean_name,
        "is_active": True,
        "metadata": {"auto_created": True, "source": "purchase_import"},
        "tags": [],
        "created_at": now,
        "updated_at": now,
    }
    await suppliers_collection.insert_one(doc)
    doc.pop("_id", None)
    logger.info("supplier_repo: auto-created supplier '%s' for org=%s", clean_name, org_id[:8])
    return Supplier(**doc)
