from fastapi import APIRouter, HTTPException, Request, status, Depends, Query
from typing import List, Optional

from auth import get_current_user, get_verified_user, require_admin
from models.financial_record import FixedCostCreate, FixedCostUpdate, FixedCostResponse
from models import FixedCost
from repositories import fixed_cost_repository
from services.module_access import check_module_access, record_module_usage
# v5.8 / Onda 10 Step D.2 — rate limit
from routers.auth import limiter

router = APIRouter(prefix="/fixed-costs", tags=["Fixed Costs"])


@router.get("", response_model=List[FixedCostResponse])
async def list_fixed_costs(
    active_only: bool = Query(True),
    category: Optional[str] = None,
    limit: int = Query(200, le=500),
    current_user: dict = Depends(get_verified_user),
):
    """List fixed costs for the organisation."""
    costs = await fixed_cost_repository.find_by_org(
        current_user["organization_id"],
        active_only=active_only,
        category=category,
        limit=limit,
    )
    return [FixedCostResponse(**c.model_dump()) for c in costs]


@router.post("", response_model=FixedCostResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_fixed_cost(
    request: Request,
    data: FixedCostCreate,
    current_user: dict = Depends(require_admin),
):
    """Create a new fixed cost entry.  Requires admin role (configuration data).

    v5.8 / Onda 10 Step D.2 — 60 req/min IP.
    """
    org_id = current_user["organization_id"]
    await check_module_access(org_id, "cashflow_monitor", "data_rows", pending_quantity=1)
    cost = await fixed_cost_repository.create(org_id, data.model_dump())
    await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=1)
    return FixedCostResponse(**cost.model_dump())


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_fixed_costs_bulk(
    request: Request,
    records: List[FixedCostCreate],
    current_user: dict = Depends(require_admin),
):
    """Bulk create fixed cost records (manual entry).  Requires admin role.

    v5.8 / Onda 10 Step D.2 — 60 req/min IP.
    """
    org_id = current_user['organization_id']
    await check_module_access(org_id, "cashflow_monitor", "data_rows", pending_quantity=len(records))

    docs = []
    for r in records:
        fc = FixedCost(
            organization_id=org_id,
            name=r.name,
            category=r.category,
            amount=r.amount,
            frequency=r.frequency,
            start_date=r.start_date,
            end_date=r.end_date,
            source_label="Manuale",
        )
        docs.append(fc.model_dump())

    count = await fixed_cost_repository.insert_many(docs)
    await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=count)
    return {"inserted": count}


@router.get("/{cost_id}", response_model=FixedCostResponse)
async def get_fixed_cost(
    cost_id: str,
    current_user: dict = Depends(get_verified_user),
):
    cost = await fixed_cost_repository.find_by_id(cost_id, current_user["organization_id"])
    if not cost:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fixed cost not found")
    return FixedCostResponse(**cost.model_dump())


@router.patch("/{cost_id}", response_model=FixedCostResponse)
async def update_fixed_cost(
    cost_id: str,
    updates: FixedCostUpdate,
    current_user: dict = Depends(require_admin),
):
    cost = await fixed_cost_repository.update(
        cost_id,
        current_user["organization_id"],
        updates.model_dump(exclude_none=True),
    )
    if not cost:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fixed cost not found")
    return FixedCostResponse(**cost.model_dump())


@router.delete("/{cost_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_fixed_cost(
    cost_id: str,
    current_user: dict = Depends(require_admin),
):
    ok = await fixed_cost_repository.deactivate(cost_id, current_user["organization_id"])
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fixed cost not found")
