"""
Customers router — Phase 3.
Prefix: /customers  (registered as /api/customers in server.py)
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional

from auth import get_current_user, get_verified_user, get_verified_user
from models.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from repositories import customer_repository

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=List[CustomerResponse])
async def list_customers(
    active_only: bool = Query(True),
    limit: int = Query(200, le=500),
    current_user: dict = Depends(get_verified_user),
):
    """List all customers for the organisation."""
    customers = await customer_repository.find_by_org(
        current_user["organization_id"], active_only=active_only, limit=limit
    )
    return [CustomerResponse(**c.model_dump()) for c in customers]


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    data: CustomerCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create a new customer."""
    customer = await customer_repository.create(current_user["organization_id"], data)
    return CustomerResponse(**customer.model_dump())


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Get a specific customer by ID."""
    customer = await customer_repository.find_by_id(
        customer_id, current_user["organization_id"]
    )
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return CustomerResponse(**customer.model_dump())


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    updates: CustomerUpdate,
    current_user: dict = Depends(get_verified_user),
):
    """Partially update a customer."""
    customer = await customer_repository.update(
        customer_id,
        current_user["organization_id"],
        updates.model_dump(exclude_none=True),
    )
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return CustomerResponse(**customer.model_dump())


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_customer(
    customer_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Soft-delete (deactivate) a customer."""
    ok = await customer_repository.deactivate(
        customer_id, current_user["organization_id"]
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
