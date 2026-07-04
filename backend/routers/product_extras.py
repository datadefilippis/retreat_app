"""
Product Extras CRUD (Onda 16 Prenotazione consolidation).

Routes:
  POST   /api/products/{product_id}/extras
  GET    /api/products/{product_id}/extras
  PATCH  /api/products/{product_id}/extras/{extra_id}
  DELETE /api/products/{product_id}/extras/{extra_id}  (soft via is_active=False)

Generalizes the service_options pattern. Applicable to any product type;
the storefront renders only active extras, sorted by sort_order, and
groups radio_variant rows by group_key.

Authorization: admin JWT + organization scoping.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from models.common import utc_now
from models.product_extra import (
    ProductExtra, ProductExtraCreate, ProductExtraUpdate,
)
from database import (
    products_collection,
    product_extras_collection,
)
from auth import get_current_user, get_verified_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/products/{product_id}/extras",
    tags=["Product Extras"],
)


class ProductExtraListResponse(BaseModel):
    extras: List[ProductExtra]


async def _get_product_or_404(product_id: str, org_id: str) -> dict:
    prod = await products_collection.find_one(
        {"id": product_id, "organization_id": org_id, "is_active": True},
        {"_id": 0, "id": 1, "item_type": 1, "name": 1},
    )
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prodotto non trovato",
        )
    return prod


@router.get("", response_model=ProductExtraListResponse)
async def list_extras(
    product_id: str,
    current_user: dict = Depends(get_verified_user),
):
    org_id = current_user["organization_id"]
    await _get_product_or_404(product_id, org_id)
    rows = await product_extras_collection.find(
        {"organization_id": org_id, "product_id": product_id},
        {"_id": 0},
    ).sort("sort_order", 1).to_list(None)
    return {"extras": rows}


@router.post("", response_model=ProductExtra, status_code=status.HTTP_201_CREATED)
async def create_extra(
    product_id: str,
    body: ProductExtraCreate,
    current_user: dict = Depends(get_verified_user),
):
    if current_user.get("role") not in ("admin", "system_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    org_id = current_user["organization_id"]
    await _get_product_or_404(product_id, org_id)

    extra = ProductExtra(
        organization_id=org_id,
        product_id=product_id,
        **body.model_dump(exclude_none=False),
    )
    doc = extra.model_dump(mode="json")
    await product_extras_collection.insert_one(doc)
    doc.pop("_id", None)
    logger.info(
        "product_extras: created id=%s product=%s kind=%s",
        extra.id, product_id, body.kind,
    )
    return doc


@router.patch("/{extra_id}", response_model=ProductExtra)
async def update_extra(
    product_id: str,
    extra_id: str,
    body: ProductExtraUpdate,
    current_user: dict = Depends(get_verified_user),
):
    if current_user.get("role") not in ("admin", "system_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    org_id = current_user["organization_id"]
    await _get_product_or_404(product_id, org_id)

    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    # Explicit booleans for is_default/is_active that were set to False must survive.
    for field in ("is_default", "is_active"):
        if field in body.model_dump(exclude_unset=True):
            updates[field] = getattr(body, field)
    updates["updated_at"] = utc_now()

    # Enforce: if the update changes kind to radio_variant, require group_key.
    existing = await product_extras_collection.find_one(
        {"id": extra_id, "organization_id": org_id, "product_id": product_id},
        {"_id": 0},
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extra non trovato")
    merged = {**existing, **updates}
    if merged.get("kind") == "radio_variant" and not merged.get("group_key"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_key obbligatorio quando kind=radio_variant",
        )

    await product_extras_collection.update_one(
        {"id": extra_id, "organization_id": org_id, "product_id": product_id},
        {"$set": updates},
    )
    merged.pop("_id", None)
    return merged


@router.delete("/{extra_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_extra(
    product_id: str,
    extra_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Soft delete via is_active=False. Order snapshots remain intact
    (extras_snapshot is frozen at order create time). A hard delete would
    break admin views that still want to surface the deleted extra by id."""
    if current_user.get("role") not in ("admin", "system_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    org_id = current_user["organization_id"]
    await _get_product_or_404(product_id, org_id)

    result = await product_extras_collection.update_one(
        {"id": extra_id, "organization_id": org_id, "product_id": product_id},
        {"$set": {"is_active": False, "updated_at": utc_now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extra non trovato")
    return None
