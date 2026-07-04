from fastapi import APIRouter, HTTPException, Query, Request, status, Depends
from typing import List, Optional
from models import SalesRecord, SalesRecordCreate, SalesRecordUpdate
from auth import get_current_user, get_verified_user, get_verified_user
from repositories import sales_repository
from services.module_access import check_module_access, record_module_usage
# v5.8 / Onda 10 Step D.2 — shared slowapi Limiter instance
from routers.auth import limiter


# ── Phase 2 helper (cashflow refactor 2026-05-20) ───────────────────────
def _csv_to_list(v: Optional[str]) -> Optional[List[str]]:
    """Parse a CSV query string into a list, returning None for empty.

    Used by the /search endpoints so the frontend can pass
    ``?categories=A,B,C`` instead of repeating the param. ``None``
    propagates to the repository which treats it as "no filter".
    """
    if not v:
        return None
    parts = [s.strip() for s in v.split(",") if s.strip()]
    return parts if parts else None

router = APIRouter(prefix="/sales", tags=["Sales"])


# ── FK validation helper ────────────────────────────────────────────────────

_FK_FIELDS = {"customer_id": "customers", "product_id": "products"}


async def _validate_fk_fields(record, org_id: str) -> None:
    """Validate FK references exist in the org. Raises HTTP 400 if not found."""
    from repositories import customer_repository, product_repository

    if getattr(record, "customer_id", None):
        c = await customer_repository.find_by_id(record.customer_id, org_id)
        if not c:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer '{record.customer_id}' not found in organization",
            )
    if getattr(record, "product_id", None):
        p = await product_repository.find_by_id(record.product_id, org_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{record.product_id}' not found in organization",
            )


@router.get("")
async def list_sales(
    limit: int = Query(500, le=5000),
    current_user: dict = Depends(get_verified_user),
):
    """List sales records for the organization (default 500, max 5000)."""
    org_id = current_user['organization_id']
    records = await sales_repository.find_by_org(org_id, limit=limit)
    return records


# ── Phase 2 endpoint — paginated + filtered search ──────────────────────
# Lives ALONGSIDE GET / (the legacy list endpoint). The list endpoint is
# still consumed by dashboard widgets / analytics call sites that expect
# the bare-array shape; this new endpoint always returns the envelope
# ``{items, total, page, page_size, has_more}`` and is what the cashflow
# Section tables use post-Phase 2 migration.

@router.get("/search")
async def search_sales(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    due_date_from: Optional[str] = None,
    due_date_to: Optional[str] = None,
    categories: Optional[str] = None,          # CSV
    channels: Optional[str] = None,            # CSV
    customer_ids: Optional[str] = None,        # CSV
    payment_status: Optional[str] = None,      # CSV
    source: Optional[str] = Query(None, pattern="^(manual|file)$"),
    amount_min: Optional[float] = Query(None, ge=0),
    amount_max: Optional[float] = Query(None, ge=0),
    q: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_verified_user),
):
    """Paginated + filtered sales records.

    All filters AND together; multi-value filters (CSV) OR within.
    Response envelope:
        {items: [...], total: N, page: K, page_size: P, has_more: bool}

    Limits: ``q`` max 100 chars, ``page_size`` max 200, ``page`` max 10k.
    These caps protect against payload bloat + accidental DoS from a
    runaway client (a legit merchant browsing the table never needs
    page=10001 or page_size=201).
    """
    org_id = current_user['organization_id']
    return await sales_repository.find_paginated(
        org_id,
        date_from=date_from,
        date_to=date_to,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        categories=_csv_to_list(categories),
        channels=_csv_to_list(channels),
        customer_ids=_csv_to_list(customer_ids),
        payment_status=_csv_to_list(payment_status),
        source=source,
        amount_min=amount_min,
        amount_max=amount_max,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.post("")
@limiter.limit("60/minute")
async def create_sales(
    request: Request,
    records: List[SalesRecordCreate],
    current_user: dict = Depends(get_verified_user)
):
    """Bulk create sales records (manual entry).

    v5.8 / Onda 10 Step D.2 — Rate-limited to 60 req/min per IP.
    Defence-in-depth against authenticated CPU/IO DoS via spam.
    Limit slowapi-provided 429 vs the 429 QUOTA_EXCEEDED we already
    raise from check_module_access (different `code` in the detail).
    """
    org_id = current_user['organization_id']
    await check_module_access(org_id, "cashflow_monitor", "data_rows", pending_quantity=len(records))

    # Validate FK references (only for records that have them)
    for r in records:
        await _validate_fk_fields(r, org_id)

    docs = []
    for r in records:
        sale = SalesRecord(
            organization_id=org_id,
            dataset_id="manual",
            date=r.date,
            amount=round(r.amount, 2),
            category=r.category,
            description=r.description,
            channel=r.channel,
            payment_status=r.payment_status,
            due_date=r.due_date,
            customer_id=r.customer_id,
            product_id=r.product_id,
            source_label="Manuale",
        )
        docs.append(sale.model_dump())

    count = await sales_repository.insert_many(docs)
    await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=count)
    return {"inserted": count}


@router.patch("/{record_id}")
async def update_sale(
    record_id: str,
    updates: SalesRecordUpdate,
    current_user: dict = Depends(get_verified_user),
):
    """Update a single sales record (partial update).

    FK fields (customer_id, product_id) can be set to a valid ID or explicitly
    set to null to unlink. Fields not present in the request body are not touched.
    """
    org_id = current_user['organization_id']
    data = updates.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nessun campo da aggiornare",
        )

    # Validate FK references if present and non-null
    if data.get("customer_id"):
        from repositories import customer_repository
        c = await customer_repository.find_by_id(data["customer_id"], org_id)
        if not c:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer not found")
    if data.get("product_id"):
        from repositories import product_repository
        p = await product_repository.find_by_id(data["product_id"], org_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not found")

    ok = await sales_repository.update_one(record_id, org_id, data)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record non trovato",
        )

    # Sync payment_status back to linked Order (if SR came from an order)
    if "payment_status" in data:
        from database import sales_records_collection
        sr = await sales_records_collection.find_one(
            {"id": record_id, "organization_id": org_id},
            {"_id": 0, "metadata": 1},
        )
        order_id = (sr or {}).get("metadata", {}).get("order_id")
        if order_id:
            from services.payment_sync import sync_payment_from_sales
            await sync_payment_from_sales(org_id, order_id, data["payment_status"])

    return {"message": "Record aggiornato", "id": record_id}


@router.delete("/{record_id}")
async def delete_sale(
    record_id: str,
    current_user: dict = Depends(get_verified_user)
):
    """Delete a single sales record"""
    org_id = current_user['organization_id']
    deleted = await sales_repository.delete_one(record_id, org_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales record not found"
        )
    return {"message": "Sales record deleted"}


@router.get("/categories")
async def get_categories(current_user: dict = Depends(get_verified_user)):
    """Get distinct category names for autocomplete"""
    org_id = current_user['organization_id']
    categories = await sales_repository.get_distinct_categories(org_id)
    return categories


@router.get("/channels")
async def get_channels(current_user: dict = Depends(get_verified_user)):
    """Get distinct channel names for autocomplete"""
    org_id = current_user['organization_id']
    channels = await sales_repository.get_distinct_channels(org_id)
    return channels
