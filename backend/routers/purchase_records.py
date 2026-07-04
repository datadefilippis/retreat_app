from fastapi import APIRouter, HTTPException, Request, status, Depends, Query
from typing import List, Optional

from auth import get_current_user, get_verified_user, get_verified_user
from models.financial_record import PurchaseRecordCreate, PurchaseRecordResponse
from repositories import purchase_record_repository
from services.module_access import check_module_access, record_module_usage
# v5.8 / Onda 10 Step D.2 — rate limit
from routers.auth import limiter

router = APIRouter(prefix="/purchase-records", tags=["Purchase Records"])


@router.get("", response_model=List[PurchaseRecordResponse])
async def list_purchase_records(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    supplier_id: Optional[str] = None,
    limit: int = Query(200, le=500),
    current_user: dict = Depends(get_verified_user),
):
    """List purchase records, optionally filtered by date range or supplier."""
    records = await purchase_record_repository.find_by_org(
        current_user["organization_id"],
        start_date=start_date,
        end_date=end_date,
        supplier_id=supplier_id,
        limit=limit,
    )
    return [PurchaseRecordResponse(**r.model_dump()) for r in records]


@router.post("", response_model=PurchaseRecordResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_purchase_record(
    request: Request,
    data: PurchaseRecordCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create a single purchase record.

    v5.8 / Onda 10 Step D.2 — 60 req/min IP.

    v5.8 / Onda 9.Y.0 — Plan-gated under cashflow_monitor.data_rows
    (same gate as /sales, /expenses, /purchases, /fixed-costs). Closes
    the bypass where Free orgs at 200/200 quota could keep inserting via
    this collateral endpoint that previously skipped enforcement.
    """
    org_id = current_user["organization_id"]
    await check_module_access(org_id, "cashflow_monitor", "data_rows", pending_quantity=1)

    record = await purchase_record_repository.create(
        org_id, data.model_dump()
    )
    await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=1)
    return PurchaseRecordResponse(**record.model_dump())


@router.get("/{record_id}", response_model=PurchaseRecordResponse)
async def get_purchase_record(
    record_id: str,
    current_user: dict = Depends(get_verified_user),
):
    record = await purchase_record_repository.find_by_id(
        record_id, current_user["organization_id"]
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase record not found")
    return PurchaseRecordResponse(**record.model_dump())


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_record(
    record_id: str,
    current_user: dict = Depends(get_verified_user),
):
    ok = await purchase_record_repository.delete(record_id, current_user["organization_id"])
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase record not found")
