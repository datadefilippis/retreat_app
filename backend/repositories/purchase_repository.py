import re
from typing import Optional, List
from database import purchase_records_collection


async def find_by_org(org_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 1000) -> List[dict]:
    """Find purchase records for an organization (capped by limit)."""
    query = {"organization_id": org_id}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    cursor = purchase_records_collection.find(query, {"_id": 0}).sort("date", -1)
    return await cursor.to_list(limit)


# ── Phase 2 (cashflow refactor 2026-05-20) ──────────────────────────────
# See sales_repository.find_paginated for the design rationale. Purchases
# has the richest filter set (14 schema fields in filterSchemas.js).


async def find_paginated(
    org_id: str,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    supplier_names: Optional[List[str]] = None,    # by supplier_name (string)
    supplier_ids: Optional[List[str]] = None,      # by supplier_id (FK)
    product_ids: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    categories_macro: Optional[List[str]] = None,
    units: Optional[List[str]] = None,
    iva_values: Optional[List[float]] = None,
    payment_status: Optional[List[str]] = None,
    source: Optional[str] = None,                  # "manual" | "file"
    quantity_min: Optional[float] = None,
    quantity_max: Optional[float] = None,
    unit_price_min: Optional[float] = None,
    unit_price_max: Optional[float] = None,
    due_date_from: Optional[str] = None,
    due_date_to: Optional[str] = None,
    q: Optional[str] = None,                       # OR over description + invoice_number
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Paginated + filtered list of purchase records.

    Returns ``{items, total, page, page_size, has_more}``. Uses the
    existing indexes on (org_id, date), (org_id, supplier_id), (org_id,
    supplier_name), (org_id, product_id), (org_id, payment_status, due_date).

    The ``q`` parameter searches across BOTH ``description`` AND
    ``invoice_number`` (the two text fields the merchant types into),
    via a ``$or`` clause — matches the filterSchemas behaviour where
    those fields are separate but the UX needs a single search box.
    """
    match: dict = {"organization_id": org_id}

    if date_from or date_to:
        match["date"] = {}
        if date_from:
            match["date"]["$gte"] = date_from
        if date_to:
            match["date"]["$lte"] = date_to

    if due_date_from or due_date_to:
        match["due_date"] = {}
        if due_date_from:
            match["due_date"]["$gte"] = due_date_from
        if due_date_to:
            match["due_date"]["$lte"] = due_date_to

    if supplier_names:
        match["supplier_name"] = {"$in": supplier_names}
    if supplier_ids:
        match["supplier_id"] = {"$in": supplier_ids}
    if product_ids:
        match["product_id"] = {"$in": product_ids}
    if categories:
        match["category"] = {"$in": categories}
    if categories_macro:
        match["category_macro"] = {"$in": categories_macro}
    if units:
        match["unit"] = {"$in": units}
    if iva_values is not None and len(iva_values) > 0:
        match["iva"] = {"$in": iva_values}
    if payment_status:
        match["payment_status"] = {"$in": payment_status}

    if source == "manual":
        match["dataset_id"] = "manual"
    elif source == "file":
        match["dataset_id"] = {"$ne": "manual"}

    if quantity_min is not None or quantity_max is not None:
        match["quantity"] = {}
        if quantity_min is not None:
            match["quantity"]["$gte"] = quantity_min
        if quantity_max is not None:
            match["quantity"]["$lte"] = quantity_max

    if unit_price_min is not None or unit_price_max is not None:
        match["unit_price"] = {}
        if unit_price_min is not None:
            match["unit_price"]["$gte"] = unit_price_min
        if unit_price_max is not None:
            match["unit_price"]["$lte"] = unit_price_max

    if q and q.strip():
        safe = re.escape(q.strip())
        rgx = {"$regex": safe, "$options": "i"}
        match["$or"] = [{"description": rgx}, {"invoice_number": rgx}]

    skip = (page - 1) * page_size
    total = await purchase_records_collection.count_documents(match)
    cursor = (
        purchase_records_collection
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
    """Insert multiple purchase records"""
    if not records:
        return 0
    result = await purchase_records_collection.insert_many(records)
    return len(result.inserted_ids)


async def find_one(record_id: str, org_id: str) -> Optional[dict]:
    """Find a single purchase record by ID."""
    return await purchase_records_collection.find_one(
        {"id": record_id, "organization_id": org_id},
        {"_id": 0},
    )


async def update_one(record_id: str, org_id: str, updates: dict) -> bool:
    """Update a single purchase record (partial update)."""
    result = await purchase_records_collection.update_one(
        {"id": record_id, "organization_id": org_id},
        {"$set": updates},
    )
    return result.matched_count > 0


async def delete_one(record_id: str, org_id: str) -> bool:
    """Delete a single purchase record"""
    result = await purchase_records_collection.delete_one({
        "id": record_id,
        "organization_id": org_id
    })
    return result.deleted_count > 0


async def delete_by_org(org_id: str) -> int:
    """Delete all purchase records for an organization"""
    result = await purchase_records_collection.delete_many({"organization_id": org_id})
    return result.deleted_count


async def delete_by_dataset(dataset_id: str) -> int:
    """Delete all purchase records for a dataset"""
    result = await purchase_records_collection.delete_many({"dataset_id": dataset_id})
    return result.deleted_count


async def get_distinct_suppliers(org_id: str) -> List[str]:
    """Get distinct supplier names for autocomplete"""
    suppliers = await purchase_records_collection.distinct(
        "supplier_name",
        {"organization_id": org_id}
    )
    return sorted(suppliers)


async def get_distinct_categories(org_id: str) -> List[str]:
    """Get distinct categories for autocomplete"""
    categories = await purchase_records_collection.distinct(
        "category",
        {"organization_id": org_id, "category": {"$ne": None}}
    )
    return sorted(categories)


async def get_distinct_categories_macro(org_id: str) -> List[str]:
    """Get distinct category_macro values for autocomplete"""
    categories = await purchase_records_collection.distinct(
        "category_macro",
        {"organization_id": org_id, "category_macro": {"$ne": None}}
    )
    return sorted(categories)


async def get_preview(dataset_id: str, limit: int = 20) -> List[dict]:
    """Get preview of purchase records"""
    cursor = purchase_records_collection.find(
        {"dataset_id": dataset_id},
        {"_id": 0, "id": 0, "organization_id": 0, "dataset_id": 0}
    ).limit(limit)
    return await cursor.to_list(limit)
