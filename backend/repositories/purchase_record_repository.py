from typing import Optional, List
from datetime import datetime, timezone

from database import purchase_records_collection
from models.financial_record import PurchaseRecord, PurchaseRecordBase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create(organization_id: str, data: dict) -> PurchaseRecord:
    record = PurchaseRecord(organization_id=organization_id, **data)
    doc = record.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await purchase_records_collection.insert_one(doc)
    return record


# v5.8 / Onda 9.Y.0.2 (Step F) — `create_many` was DEAD CODE: zero callers
# anywhere in routers/services. Removed to eliminate a latent bypass: any
# future contributor wiring it into a new bulk endpoint without
# `check_module_access(cashflow_monitor.data_rows)` would have created a
# silent quota bypass identical to the pre-9.Y.0 purchase_records gap.
# If a bulk path is ever needed, route it through routers/purchase_records.py
# with the gate, mirroring the pattern in routers/sales.py POST /sales.


async def find_by_id(record_id: str, organization_id: str) -> Optional[PurchaseRecord]:
    doc = await purchase_records_collection.find_one(
        {"id": record_id, "organization_id": organization_id}
    )
    return PurchaseRecord(**doc) if doc else None


async def find_by_org(
    organization_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    supplier_id: Optional[str] = None,
    limit: int = 200,
) -> List[PurchaseRecord]:
    query: dict = {"organization_id": organization_id}
    if start_date or end_date:
        query["date"] = {}
        if start_date:
            query["date"]["$gte"] = start_date
        if end_date:
            query["date"]["$lte"] = end_date
    if supplier_id:
        query["supplier_id"] = supplier_id
    cursor = (
        purchase_records_collection.find(query).sort("date", -1).limit(limit)
    )
    return [PurchaseRecord(**doc) async for doc in cursor]


async def delete(record_id: str, organization_id: str) -> bool:
    result = await purchase_records_collection.delete_one(
        {"id": record_id, "organization_id": organization_id}
    )
    return result.deleted_count > 0
