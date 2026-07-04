"""
Availability Router — scheduling rules, blocked slots, and free slot computation.

Endpoints:
  GET    /availability/rules           — list availability rules
  POST   /availability/rules           — create rule
  DELETE /availability/rules/{id}      — delete rule
  GET    /availability/blocked         — list blocked slots (by date range)
  POST   /availability/blocked         — create blocked slot
  DELETE /availability/blocked/{id}    — delete blocked slot
  GET    /availability/slots           — compute free slots for a date range
"""

import logging
from datetime import datetime, timedelta, date as date_type
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, status

from auth import get_current_user, get_verified_user, get_verified_user
from database import availability_rules_collection, blocked_slots_collection, orders_collection
from models.availability import (
    AvailabilityRule, AvailabilityRuleCreate, AvailabilityRuleResponse,
    BlockedSlot, BlockedSlotCreate, BlockedSlotBatchCreate, BlockedSlotResponse,
)
from models.common import generate_id, utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/availability", tags=["Availability"])

DAY_NAMES = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]


# ── Rules CRUD ───────────────────────────────────────────────────────────

@router.get("/rules")
async def list_rules(
    store_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_verified_user),
):
    """List availability rules for the org, optionally filtered by store
    or product (F5 Onda 12: per-product rules for service scheduling)."""
    query = {"organization_id": current_user["organization_id"], "is_active": True}
    if store_id:
        query["store_id"] = store_id
    if product_id:
        query["product_id"] = product_id
    cursor = availability_rules_collection.find(query, {"_id": 0}).sort("day_of_week", 1)
    rules = await cursor.to_list(100)
    return {"rules": rules}


@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_rule(
    body: AvailabilityRuleCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create an availability rule (recurring weekly pattern)."""
    org_id = current_user["organization_id"]

    # Validate times
    if body.start_time >= body.end_time:
        raise HTTPException(status_code=400, detail="start_time deve essere prima di end_time")

    rule = AvailabilityRule(
        organization_id=org_id,
        **body.model_dump(),
    )
    doc = rule.model_dump(mode="json")
    await availability_rules_collection.insert_one(doc)
    doc.pop("_id", None)

    logger.info("availability: rule created day=%d %s-%s org=%s",
                body.day_of_week, body.start_time, body.end_time, org_id)
    return doc


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Delete (deactivate) an availability rule."""
    result = await availability_rules_collection.update_one(
        {"id": rule_id, "organization_id": current_user["organization_id"]},
        {"$set": {"is_active": False, "updated_at": utc_now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Regola rimossa"}


# ── Blocked Slots CRUD ───────────────────────────────────────────────────

@router.get("/blocked")
async def list_blocked_slots(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    store_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_verified_user),
):
    """List blocked slots, optionally filtered by date range, store, and product."""
    query = {"organization_id": current_user["organization_id"]}
    if store_id:
        query["store_id"] = store_id
    if product_id:
        # Show blocks for this product + global blocks (product_id=null)
        query["$or"] = [{"product_id": product_id}, {"product_id": None}, {"product_id": {"$exists": False}}]
    if date_from and date_to:
        query["date"] = {"$gte": date_from, "$lte": date_to}
    elif date_from:
        query["date"] = {"$gte": date_from}

    cursor = blocked_slots_collection.find(query, {"_id": 0}).sort("date", 1).limit(500)
    slots = await cursor.to_list(500)
    return {"blocked_slots": slots}


@router.post("/blocked", status_code=status.HTTP_201_CREATED)
async def create_blocked_slot(
    body: BlockedSlotCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create a blocked slot (personal time, holiday, etc.)."""
    org_id = current_user["organization_id"]

    if body.start_time >= body.end_time:
        raise HTTPException(status_code=400, detail="start_time deve essere prima di end_time")

    slot = BlockedSlot(
        organization_id=org_id,
        **body.model_dump(),
    )
    doc = slot.model_dump(mode="json")
    await blocked_slots_collection.insert_one(doc)
    doc.pop("_id", None)

    logger.info("availability: blocked slot created date=%s %s-%s org=%s",
                body.date, body.start_time, body.end_time, org_id)
    return doc


@router.delete("/blocked/{slot_id}")
async def delete_blocked_slot(
    slot_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Delete a blocked slot."""
    result = await blocked_slots_collection.delete_one(
        {"id": slot_id, "organization_id": current_user["organization_id"]},
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Blocked slot not found")
    return {"message": "Blocco rimosso"}


@router.post("/blocked/batch", status_code=status.HTTP_201_CREATED)
async def create_blocked_slots_batch(
    body: BlockedSlotBatchCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create blocked slots for multiple dates at once (bulk/recurring)."""
    import re
    org_id = current_user["organization_id"]

    if body.start_time >= body.end_time:
        raise HTTPException(status_code=400, detail="start_time deve essere prima di end_time")

    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    for d in body.dates:
        if not date_pattern.match(d):
            raise HTTPException(status_code=400, detail=f"Data non valida: {d}")

    group_id = generate_id()
    docs = []
    for d in body.dates:
        slot = BlockedSlot(
            organization_id=org_id,
            store_id=body.store_id,
            date=d,
            start_time=body.start_time,
            end_time=body.end_time,
            reason=body.reason,
            note=body.note,
            group_id=group_id,
        )
        docs.append(slot.model_dump(mode="json"))

    if docs:
        await blocked_slots_collection.insert_many(docs)
        for doc in docs:
            doc.pop("_id", None)

    logger.info("availability: batch blocked %d slots group=%s org=%s",
                len(docs), group_id, org_id)
    return {"blocked_slots": docs, "group_id": group_id, "count": len(docs)}


@router.delete("/blocked/group/{group_id}")
async def delete_blocked_group(
    group_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Delete all blocked slots in a group (bulk delete)."""
    result = await blocked_slots_collection.delete_many(
        {"group_id": group_id, "organization_id": current_user["organization_id"]},
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Nessun blocco trovato per questo gruppo")
    return {"message": f"{result.deleted_count} blocchi rimossi", "deleted_count": result.deleted_count}


# ── Slot Computation ─────────────────────────────────────────────────────

def _time_to_minutes(t: str) -> int:
    """Convert HH:MM to minutes since midnight."""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _minutes_to_time(m: int) -> str:
    """Convert minutes since midnight to HH:MM."""
    return f"{m // 60:02d}:{m % 60:02d}"


def _generate_slots_from_rule(rule: dict) -> List[dict]:
    """Generate time slots from a rule's start/end/duration."""
    start = _time_to_minutes(rule["start_time"])
    end = _time_to_minutes(rule["end_time"])
    duration = rule.get("slot_duration_minutes", 60)
    slots = []
    current = start
    while current + duration <= end:
        slots.append({
            "start": _minutes_to_time(current),
            "end": _minutes_to_time(current + duration),
        })
        current += duration
    return slots


def _is_slot_blocked(slot_start: str, slot_end: str, blocked_list: List[dict]) -> bool:
    """Check if a slot overlaps with any blocked period."""
    s = _time_to_minutes(slot_start)
    e = _time_to_minutes(slot_end)
    for b in blocked_list:
        bs = _time_to_minutes(b["start_time"])
        be = _time_to_minutes(b["end_time"])
        if s < be and e > bs:  # overlap
            return True
    return False


@router.get("/slots")
async def get_available_slots(
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    store_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_verified_user),
):
    """Compute available time slots for a date range.

    Algorithm: for each date in range:
    1. Get rules for that day of week
    2. Generate slots from rules
    3. Subtract blocked_slots for that date
    4. Subtract confirmed booking orders for that date
    5. Return remaining free slots
    """
    org_id = current_user["organization_id"]

    # Parse dates
    try:
        start = date_type.fromisoformat(date_from)
        end = date_type.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato data non valido (YYYY-MM-DD)")

    if (end - start).days > 60:
        raise HTTPException(status_code=400, detail="Intervallo massimo 60 giorni")

    # Load rules
    rule_query = {"organization_id": org_id, "is_active": True}
    if store_id:
        rule_query["$or"] = [{"store_id": store_id}, {"store_id": None}]
    rules_cursor = availability_rules_collection.find(rule_query, {"_id": 0})
    all_rules = await rules_cursor.to_list(100)

    # Group rules by day_of_week
    rules_by_day = {}
    for r in all_rules:
        rules_by_day.setdefault(r["day_of_week"], []).append(r)

    # Load blocked slots for the range (per-product + global)
    block_query = {"organization_id": org_id, "date": {"$gte": date_from, "$lte": date_to}}
    if product_id:
        block_query["$or"] = [{"product_id": product_id}, {"product_id": None}, {"product_id": {"$exists": False}}]
    elif store_id:
        block_query["$or"] = [{"store_id": store_id}, {"store_id": None}]
    blocks_cursor = blocked_slots_collection.find(block_query, {"_id": 0})
    all_blocks = await blocks_cursor.to_list(1000)

    # Group blocks by date
    blocks_by_date = {}
    for b in all_blocks:
        blocks_by_date.setdefault(b["date"], []).append(b)

    # Compute free slots per day
    result = []
    current = start
    while current <= end:
        day_str = current.isoformat()
        dow = current.weekday()  # 0=Monday

        day_rules = rules_by_day.get(dow, [])
        if not day_rules:
            current += timedelta(days=1)
            continue

        # Generate all possible slots from rules
        all_slots = []
        for rule in day_rules:
            all_slots.extend(_generate_slots_from_rule(rule))

        # Get blocks for this date
        day_blocks = blocks_by_date.get(day_str, [])

        # Filter out blocked slots
        free_slots = [
            s for s in all_slots
            if not _is_slot_blocked(s["start"], s["end"], day_blocks)
        ]

        if free_slots:
            result.append({
                "date": day_str,
                "day_name": DAY_NAMES[dow],
                "slots": free_slots,
            })

        current += timedelta(days=1)

    return {"available": result, "date_from": date_from, "date_to": date_to}
