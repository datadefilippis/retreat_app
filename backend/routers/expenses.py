from fastapi import APIRouter, HTTPException, Query, Request, status, Depends
from typing import List, Optional
from models import ExpenseRecord, ExpenseRecordCreate, ExpenseRecordUpdate
from auth import get_current_user, get_verified_user, get_verified_user
from repositories import expenses_repository
from services.module_access import check_module_access, record_module_usage
# v5.8 / Onda 10 Step D.2 — rate limit
from routers.auth import limiter


def _csv_to_list(v: Optional[str]) -> Optional[List[str]]:
    """Parse CSV query string → list. See sales.py for design notes."""
    if not v:
        return None
    parts = [s.strip() for s in v.split(",") if s.strip()]
    return parts if parts else None


router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("")
async def list_expenses(
    limit: int = Query(500, le=5000),
    current_user: dict = Depends(get_verified_user),
):
    """List expense records for the organization (default 500, max 5000)."""
    org_id = current_user['organization_id']
    records = await expenses_repository.find_by_org(org_id, limit=limit)
    return records


# ── Phase 2 endpoint — paginated + filtered search ──────────────────────
@router.get("/search")
async def search_expenses(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    categories: Optional[str] = None,
    suppliers: Optional[str] = None,           # CSV by name
    supplier_ids: Optional[str] = None,        # CSV by FK
    source: Optional[str] = Query(None, pattern="^(manual|file)$"),
    amount_min: Optional[float] = Query(None, ge=0),
    amount_max: Optional[float] = Query(None, ge=0),
    q: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_verified_user),
):
    """Paginated + filtered expense records. See sales.search for shape."""
    org_id = current_user['organization_id']
    return await expenses_repository.find_paginated(
        org_id,
        date_from=date_from,
        date_to=date_to,
        categories=_csv_to_list(categories),
        suppliers=_csv_to_list(suppliers),
        supplier_ids=_csv_to_list(supplier_ids),
        source=source,
        amount_min=amount_min,
        amount_max=amount_max,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.post("")
@limiter.limit("60/minute")
async def create_expenses(
    request: Request,
    records: List[ExpenseRecordCreate],
    current_user: dict = Depends(get_verified_user)
):
    """Bulk create expense records (manual entry).

    v5.8 / Onda 10 Step D.2 — 60 req/min IP.
    """
    org_id = current_user['organization_id']
    await check_module_access(org_id, "cashflow_monitor", "data_rows", pending_quantity=len(records))

    # Validate supplier_id FK if provided
    for r in records:
        if getattr(r, "supplier_id", None):
            from repositories import supplier_repository
            s = await supplier_repository.find_by_id(r.supplier_id, org_id)
            if not s:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Supplier '{r.supplier_id}' not found in organization",
                )

    docs = []
    for r in records:
        expense = ExpenseRecord(
            organization_id=org_id,
            dataset_id="manual",
            date=r.date,
            amount=round(r.amount, 2),
            category=r.category,
            description=r.description,
            supplier=r.supplier,
            supplier_id=r.supplier_id,
            source_label="Manuale",
        )
        docs.append(expense.model_dump())

    count = await expenses_repository.insert_many(docs)
    await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=count)
    return {"inserted": count}


@router.patch("/{record_id}")
async def update_expense(
    record_id: str,
    updates: ExpenseRecordUpdate,
    current_user: dict = Depends(get_verified_user),
):
    """Update a single expense record (partial update).

    supplier_id can be set to a valid ID or explicitly to null to unlink.
    """
    org_id = current_user['organization_id']
    data = updates.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nessun campo da aggiornare",
        )

    # Validate supplier_id if present and non-null
    if data.get("supplier_id"):
        from repositories import supplier_repository
        s = await supplier_repository.find_by_id(data["supplier_id"], org_id)
        if not s:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier not found")

    ok = await expenses_repository.update_one(record_id, org_id, data)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record non trovato",
        )
    return {"message": "Record aggiornato", "id": record_id}


@router.delete("/{record_id}")
async def delete_expense(
    record_id: str,
    current_user: dict = Depends(get_verified_user)
):
    """Delete a single expense record"""
    org_id = current_user['organization_id']
    deleted = await expenses_repository.delete_one(record_id, org_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense record not found"
        )
    return {"message": "Expense record deleted"}


@router.get("/categories")
async def get_categories(current_user: dict = Depends(get_verified_user)):
    """Get distinct category names for autocomplete"""
    org_id = current_user['organization_id']
    categories = await expenses_repository.get_distinct_categories(org_id)
    return categories


@router.get("/suppliers")
async def get_suppliers(current_user: dict = Depends(get_verified_user)):
    """Get distinct supplier names for autocomplete"""
    org_id = current_user['organization_id']
    suppliers = await expenses_repository.get_distinct_suppliers(org_id)
    return suppliers
