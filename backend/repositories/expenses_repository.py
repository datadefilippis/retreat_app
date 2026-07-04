import re
from typing import Optional, List
from database import expense_records_collection


async def find_by_org(org_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 1000) -> List[dict]:
    """Find expense records for an organization (capped by limit)."""
    query = {"organization_id": org_id}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    cursor = expense_records_collection.find(query, {"_id": 0}).sort("date", -1)
    return await cursor.to_list(limit)


# ── Phase 2 (cashflow refactor 2026-05-20) ──────────────────────────────
# See sales_repository.find_paginated for the design rationale. Same
# envelope shape, expenses-specific filter set.


async def find_paginated(
    org_id: str,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    categories: Optional[List[str]] = None,
    suppliers: Optional[List[str]] = None,           # by name (supplier field)
    supplier_ids: Optional[List[str]] = None,        # by FK (supplier_id)
    source: Optional[str] = None,                    # "manual" | "file"
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Paginated + filtered list of expense records.

    Returns ``{items, total, page, page_size, has_more}``. Uses the
    existing indexes on (org_id, date), (org_id, supplier_id), (org_id,
    category) — see database.py for the index list.
    """
    match: dict = {"organization_id": org_id}

    if date_from or date_to:
        match["date"] = {}
        if date_from:
            match["date"]["$gte"] = date_from
        if date_to:
            match["date"]["$lte"] = date_to

    if categories:
        match["category"] = {"$in": categories}
    if suppliers:
        match["supplier"] = {"$in": suppliers}
    if supplier_ids:
        match["supplier_id"] = {"$in": supplier_ids}

    if source == "manual":
        match["dataset_id"] = "manual"
    elif source == "file":
        match["dataset_id"] = {"$ne": "manual"}

    if amount_min is not None or amount_max is not None:
        match["amount"] = {}
        if amount_min is not None:
            match["amount"]["$gte"] = amount_min
        if amount_max is not None:
            match["amount"]["$lte"] = amount_max

    if q and q.strip():
        safe = re.escape(q.strip())
        match["description"] = {"$regex": safe, "$options": "i"}

    skip = (page - 1) * page_size
    total = await expense_records_collection.count_documents(match)
    cursor = (
        expense_records_collection
        .find(match, {"_id": 0})
        .sort([("date", -1), ("id", -1)])
        .skip(skip)
        .limit(page_size)
    )
    items = await cursor.to_list(page_size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": skip + len(items) < total,
    }


async def insert_many(records: List[dict]) -> int:
    """Insert multiple expense records"""
    if not records:
        return 0
    result = await expense_records_collection.insert_many(records)
    return len(result.inserted_ids)


async def update_one(record_id: str, org_id: str, updates: dict) -> bool:
    """Update a single expense record (partial update)."""
    result = await expense_records_collection.update_one(
        {"id": record_id, "organization_id": org_id},
        {"$set": updates},
    )
    return result.matched_count > 0


async def delete_one(record_id: str, org_id: str) -> bool:
    """Delete a single expense record"""
    result = await expense_records_collection.delete_one({
        "id": record_id,
        "organization_id": org_id
    })
    return result.deleted_count > 0


async def delete_by_org(org_id: str) -> int:
    """Delete all expense records for an organization"""
    result = await expense_records_collection.delete_many({"organization_id": org_id})
    return result.deleted_count


async def get_distinct_categories(org_id: str) -> List[str]:
    """Get distinct categories for autocomplete"""
    categories = await expense_records_collection.distinct(
        "category",
        {"organization_id": org_id, "category": {"$ne": None}}
    )
    return sorted(categories)


async def get_distinct_suppliers(org_id: str) -> List[str]:
    """Get distinct suppliers for autocomplete"""
    suppliers = await expense_records_collection.distinct(
        "supplier",
        {"organization_id": org_id, "supplier": {"$ne": None}}
    )
    return sorted(suppliers)
