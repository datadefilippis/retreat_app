"""
Column Mappings router — Phase 3.

Endpoints:
  GET    /column-mappings                      – list org mappings (optionally filtered by dataset_type)
  POST   /column-mappings                      – create a single mapping rule
  DELETE /column-mappings/{id}                 – deactivate a mapping rule
  POST   /column-mappings/batch                – upsert all mappings for a dataset_type in one call
  GET    /column-mappings/profiles/{dataset_id} – get column profile for a dataset
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from pydantic import BaseModel

from auth import get_current_user, get_verified_user, get_verified_user
from models.column_mapping import (
    ColumnMappingBase,
    ColumnMappingResponse,
    DatasetColumnProfileResponse,
)
from repositories.column_mapping_repository import (
    create_mapping,
    find_mappings_by_org_and_type,
    deactivate_mapping,
    deactivate_by_source_column,
    find_profile_by_dataset,
)

router = APIRouter(prefix="/column-mappings", tags=["Column Mappings"])


@router.get("", response_model=List[ColumnMappingResponse])
async def list_column_mappings(
    dataset_type: Optional[str] = Query(None, regex="^(sales|expenses|purchases)$"),
    current_user: dict = Depends(get_verified_user),
):
    """List column mapping rules for the organisation, optionally filtered by dataset_type."""
    if dataset_type:
        mappings = await find_mappings_by_org_and_type(
            current_user["organization_id"], dataset_type
        )
    else:
        # Return all types by querying each
        all_mappings = []
        for dt in ("sales", "expenses", "purchases"):
            all_mappings.extend(
                await find_mappings_by_org_and_type(current_user["organization_id"], dt)
            )
        mappings = all_mappings
    return [ColumnMappingResponse(**m.model_dump()) for m in mappings]


@router.post("", response_model=ColumnMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_column_mapping(
    data: ColumnMappingBase,
    current_user: dict = Depends(get_verified_user),
):
    """Create a new column mapping rule."""
    mapping = await create_mapping(current_user["organization_id"], data)
    return ColumnMappingResponse(**mapping.model_dump())


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_column_mapping(
    mapping_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Deactivate (soft-delete) a column mapping rule."""
    ok = await deactivate_mapping(mapping_id, current_user["organization_id"])
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Column mapping not found"
        )


# ── Batch endpoint ────────────────────────────────────────────────────────────

class _BatchMappingItem(BaseModel):
    """A single mapping rule within a batch request."""
    source_column: str
    target_field: str
    transform: Optional[str] = None


class _BatchRequest(BaseModel):
    """Body for POST /column-mappings/batch."""
    dataset_type: str          # "sales" | "expenses" | "purchases"
    mappings: List[_BatchMappingItem]


@router.post("/batch", response_model=List[ColumnMappingResponse], status_code=status.HTTP_201_CREATED)
async def save_batch_column_mappings(
    body: _BatchRequest,
    current_user: dict = Depends(get_verified_user),
):
    """Upsert a complete set of column mappings for one dataset_type.

    For each item in the batch:
      1. Deactivate any existing active mapping for the same
         (org, dataset_type, source_column) triple.
      2. Create a new active mapping with the supplied target_field.

    Source columns NOT included in the batch are left untouched.
    Items with target_field=="" (empty string) are skipped — this lets
    the caller clear a mapping without inserting a blank one.
    """
    if body.dataset_type not in ("sales", "expenses", "purchases"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="dataset_type must be one of: sales, expenses, purchases",
        )

    org_id = current_user["organization_id"]
    created = []

    for item in body.mappings:
        # Skip blank target_field (user left it unmapped)
        if not item.target_field.strip():
            continue

        # Deactivate existing mapping for this source_column (idempotent)
        await deactivate_by_source_column(org_id, body.dataset_type, item.source_column)

        # Create the new active mapping
        mapping_data = ColumnMappingBase(
            dataset_type=body.dataset_type,
            source_column=item.source_column,
            target_field=item.target_field,
            transform=item.transform,
        )
        mapping = await create_mapping(org_id, mapping_data)
        created.append(ColumnMappingResponse(**mapping.model_dump()))

    return created


@router.get("/profiles/{dataset_id}", response_model=DatasetColumnProfileResponse)
async def get_dataset_profile(
    dataset_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Get the statistical column profile for a dataset (generated automatically on upload)."""
    profile = await find_profile_by_dataset(dataset_id)
    if not profile or profile.organization_id != current_user["organization_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Column profile not found"
        )
    return DatasetColumnProfileResponse(**profile.model_dump())
