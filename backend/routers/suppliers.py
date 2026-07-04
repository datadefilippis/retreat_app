import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List

from auth import get_current_user, get_verified_user, get_verified_user
from models.supplier import SupplierCreate, SupplierResponse, SupplierUpdate
from repositories import supplier_repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("", response_model=List[SupplierResponse])
async def list_suppliers(
    active_only: bool = Query(True),
    limit: int = Query(200, le=500),
    current_user: dict = Depends(get_verified_user),
):
    suppliers = await supplier_repository.find_by_org(
        current_user["organization_id"], active_only=active_only, limit=limit
    )
    return [SupplierResponse(**s.model_dump()) for s in suppliers]


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    data: SupplierCreate,
    current_user: dict = Depends(get_verified_user),
):
    supplier = await supplier_repository.create(current_user["organization_id"], data)
    return SupplierResponse(**supplier.model_dump())


# /metrics MUST be before /{supplier_id} to avoid FastAPI matching "metrics" as a supplier_id
@router.get("/metrics")
async def get_supplier_metrics(
    current_user: dict = Depends(get_verified_user),
):
    """Lightweight supplier intelligence: spend, frequency, last activity per supplier."""
    from database import purchase_records_collection, expense_records_collection

    org_id = current_user["organization_id"]
    metrics = {}

    # Aggregate purchases by supplier_id
    purchase_pipeline = [
        {"$match": {"organization_id": org_id, "supplier_id": {"$ne": None, "$exists": True}}},
        {"$group": {
            "_id": "$supplier_id",
            "total_spend": {"$sum": "$total_price"},
            "purchase_count": {"$sum": 1},
            "last_purchase": {"$max": "$date"},
            "categories": {"$addToSet": "$category"},
        }},
    ]
    async for doc in purchase_records_collection.aggregate(purchase_pipeline):
        sid = doc["_id"]
        metrics[sid] = {
            "total_spend": round(doc["total_spend"], 2),
            "purchase_count": doc["purchase_count"],
            "last_purchase": doc["last_purchase"],
            "top_categories": [c for c in (doc.get("categories") or []) if c][:3],
        }

    # Add expense records by supplier_id
    expense_pipeline = [
        {"$match": {"organization_id": org_id, "supplier_id": {"$ne": None, "$exists": True}}},
        {"$group": {
            "_id": "$supplier_id",
            "total_expenses": {"$sum": "$amount"},
            "expense_count": {"$sum": 1},
            "last_expense": {"$max": "$date"},
        }},
    ]
    async for doc in expense_records_collection.aggregate(expense_pipeline):
        sid = doc["_id"]
        if sid not in metrics:
            metrics[sid] = {"total_spend": 0, "purchase_count": 0, "last_purchase": None, "top_categories": []}
        metrics[sid]["total_spend"] = round(metrics[sid]["total_spend"] + doc["total_expenses"], 2)
        metrics[sid]["purchase_count"] += doc["expense_count"]
        if doc["last_expense"] and (not metrics[sid]["last_purchase"] or doc["last_expense"] > metrics[sid]["last_purchase"]):
            metrics[sid]["last_purchase"] = doc["last_expense"]

    return {"metrics": metrics}


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: str,
    current_user: dict = Depends(get_verified_user),
):
    supplier = await supplier_repository.find_by_id(
        supplier_id, current_user["organization_id"]
    )
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return SupplierResponse(**supplier.model_dump())


@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    updates: SupplierUpdate,
    current_user: dict = Depends(get_verified_user),
):
    supplier = await supplier_repository.update(
        supplier_id,
        current_user["organization_id"],
        updates.model_dump(exclude_none=True),
    )
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return SupplierResponse(**supplier.model_dump())


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_supplier(
    supplier_id: str,
    current_user: dict = Depends(get_verified_user),
):
    ok = await supplier_repository.deactivate(supplier_id, current_user["organization_id"])
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
