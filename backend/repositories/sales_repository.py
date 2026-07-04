import re
from typing import Optional, List
from database import sales_records_collection


async def find_by_org(org_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 1000) -> List[dict]:
    """Find sales records for an organization (capped by limit)."""
    query = {"organization_id": org_id}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    cursor = sales_records_collection.find(query, {"_id": 0}).sort("date", -1)
    return await cursor.to_list(limit)


# ── Phase 2 (cashflow refactor 2026-05-20) ──────────────────────────────
# Paginated + filtered query. Lives ALONGSIDE find_by_org (which is still
# used by analytics + dashboard aggregates) so the legacy contract is
# guaranteed untouched. See backend/tests/test_cashflow_search_endpoints.py
# for the response-shape sentinel and Section migration plan.


async def find_paginated(
    org_id: str,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    categories: Optional[List[str]] = None,        # OR within
    channels: Optional[List[str]] = None,          # OR within
    customer_ids: Optional[List[str]] = None,      # OR within
    payment_status: Optional[List[str]] = None,    # OR within
    source: Optional[str] = None,                  # "manual" | "file"
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    due_date_from: Optional[str] = None,
    due_date_to: Optional[str] = None,
    q: Optional[str] = None,                       # free-text on description
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Paginated + filtered list of sales records.

    Returns an envelope ``{items, total, page, page_size, has_more}``
    so the frontend can drive pagination without a second round-trip.

    All filters AND together. Multi-value filters OR within (e.g. a record
    passes if its ``category`` matches ANY of the ``categories`` provided).
    Uses the existing indexes on (org_id, date), (org_id, category),
    (org_id, payment_status, due_date), (org_id, customer_id, date) —
    see database.py:388 for the index list.

    Sort key is ``(date DESC, id DESC)`` — the secondary key guarantees a
    deterministic order so skip-based pagination doesn't drop or duplicate
    rows when two records share the same date.
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

    if categories:
        match["category"] = {"$in": categories}
    if channels:
        match["channel"] = {"$in": channels}
    if customer_ids:
        match["customer_id"] = {"$in": customer_ids}
    if payment_status:
        match["payment_status"] = {"$in": payment_status}

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
        # re.escape neutralises regex metacharacters — defence against
        # ReDoS (a hostile user typing ``(a+)+`` on a 100k-row collection).
        safe = re.escape(q.strip())
        match["description"] = {"$regex": safe, "$options": "i"}

    skip = (page - 1) * page_size
    total = await sales_records_collection.count_documents(match)
    cursor = (
        sales_records_collection
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
    """Insert multiple sales records"""
    if not records:
        return 0
    result = await sales_records_collection.insert_many(records)
    return len(result.inserted_ids)


async def update_one(record_id: str, org_id: str, updates: dict) -> bool:
    """Update a single sales record (partial update)."""
    result = await sales_records_collection.update_one(
        {"id": record_id, "organization_id": org_id},
        {"$set": updates},
    )
    return result.matched_count > 0


async def delete_one(record_id: str, org_id: str) -> bool:
    """Delete a single sales record"""
    result = await sales_records_collection.delete_one({
        "id": record_id,
        "organization_id": org_id
    })
    return result.deleted_count > 0


async def delete_by_org(org_id: str) -> int:
    """Delete all sales records for an organization"""
    result = await sales_records_collection.delete_many({"organization_id": org_id})
    return result.deleted_count


async def get_distinct_categories(org_id: str) -> List[str]:
    """Get distinct categories for autocomplete"""
    categories = await sales_records_collection.distinct(
        "category",
        {"organization_id": org_id, "category": {"$ne": None}}
    )
    return sorted(categories)


async def get_distinct_channels(org_id: str) -> List[str]:
    """Get distinct channels for autocomplete"""
    channels = await sales_records_collection.distinct(
        "channel",
        {"organization_id": org_id, "channel": {"$ne": None}}
    )
    return sorted(channels)
