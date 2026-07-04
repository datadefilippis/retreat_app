"""
Validation Rules router — v2.2.

Management API for per-organisation DataValidationRule documents.
Rules created here are automatically picked up by the upload pipeline
(dataset_service._load_validation_rules) on the next file upload.

Endpoints:
  GET    /validation-rules            – list rules (optionally filtered by dataset_type)
  POST   /validation-rules            – create a new rule
  PATCH  /validation-rules/{id}       – update is_active / rule_value / error_message
  DELETE /validation-rules/{id}       – hard-delete a rule
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional

from auth import get_current_user, get_verified_user, require_admin
from models.data_validation_rule import (
    DataValidationRuleBase,
    DataValidationRuleResponse,
    DataValidationRuleUpdate,
)
from repositories.data_validation_rule_repository import (
    create_rule,
    find_by_org,
    find_by_id,
    update_rule,
    delete_rule,
)

router = APIRouter(prefix="/validation-rules", tags=["Validation Rules"])

_VALID_DATASET_TYPES = ("sales", "expenses", "purchases")


@router.get("", response_model=List[DataValidationRuleResponse])
async def list_validation_rules(
    dataset_type: Optional[str] = Query(
        None,
        description="Filter by dataset type: sales | expenses | purchases",
    ),
    current_user: dict = Depends(get_verified_user),
):
    """List all validation rules for the organisation, optionally filtered by dataset_type.

    Returns both active and inactive rules so the management UI can show
    the full picture and allow toggling.
    """
    if dataset_type and dataset_type not in _VALID_DATASET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"dataset_type must be one of: {', '.join(_VALID_DATASET_TYPES)}",
        )
    rules = await find_by_org(current_user["organization_id"], dataset_type)
    return [DataValidationRuleResponse(**r.model_dump()) for r in rules]


@router.post("", response_model=DataValidationRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_validation_rule(
    data: DataValidationRuleBase,
    current_user: dict = Depends(require_admin),
):
    """Create a new validation rule for the organisation.

    The rule becomes active immediately and will be applied on the next upload.
    Requires admin role (rules affect the data ingestion pipeline).
    """
    if data.dataset_type not in _VALID_DATASET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"dataset_type must be one of: {', '.join(_VALID_DATASET_TYPES)}",
        )
    rule = await create_rule(current_user["organization_id"], data)
    return DataValidationRuleResponse(**rule.model_dump())


@router.patch("/{rule_id}", response_model=DataValidationRuleResponse)
async def update_validation_rule(
    rule_id: str,
    data: DataValidationRuleUpdate,
    current_user: dict = Depends(require_admin),
):
    """Partially update a validation rule.

    Only is_active, rule_value, and error_message can be changed.
    To change dataset_type, field_name, or rule_type: delete and re-create.
    """
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update",
        )

    rule = await update_rule(rule_id, current_user["organization_id"], updates)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation rule not found",
        )
    return DataValidationRuleResponse(**rule.model_dump())


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_validation_rule(
    rule_id: str,
    current_user: dict = Depends(require_admin),
):
    """Permanently delete a validation rule.

    The rule will no longer be applied on future uploads.
    """
    # Verify ownership before deleting
    existing = await find_by_id(rule_id, current_user["organization_id"])
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation rule not found",
        )
    await delete_rule(rule_id, current_user["organization_id"])
