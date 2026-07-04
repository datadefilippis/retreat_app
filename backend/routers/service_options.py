"""
Service Options CRUD (F5 Onda 12).

Routes:
  POST   /api/products/{product_id}/service-options
  GET    /api/products/{product_id}/service-options
  PATCH  /api/products/{product_id}/service-options/{option_id}
  DELETE /api/products/{product_id}/service-options/{option_id}

Mirrors the event ticket tiers pattern but scoped to the PRODUCT (not an
occurrence): a service has N options (Consulenza 30 min / 60 min / ...),
each with its own price and optional duration override.

Authorization: require admin JWT + enforce organization_id scope.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from models.common import utc_now
from models.service_option import (
    ServiceOption, ServiceOptionCreate, ServiceOptionUpdate,
)
from database import (
    products_collection,
    service_options_collection,
)
from auth import get_current_user, get_verified_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/products/{product_id}/service-options",
    tags=["Service Options"],
)


class ServiceOptionListResponse(BaseModel):
    options: List[ServiceOption]


async def _get_service_product_or_404(product_id: str, org_id: str) -> dict:
    """Fetch a service product or raise 404. Used as a shared guard."""
    prod = await products_collection.find_one(
        {"id": product_id, "organization_id": org_id, "is_active": True},
        {"_id": 0, "id": 1, "item_type": 1, "name": 1},
    )
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prodotto non trovato",
        )
    if prod.get("item_type") != "service":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le opzioni sono configurabili solo per prodotti di tipo 'servizio'.",
        )
    return prod


@router.get("", response_model=ServiceOptionListResponse)
async def list_options(
    product_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """List all options (active + inactive) for a service product."""
    org_id = current_user["organization_id"]
    await _get_service_product_or_404(product_id, org_id)

    cursor = service_options_collection.find(
        {"organization_id": org_id, "product_id": product_id},
        {"_id": 0},
    ).sort("sort_order", 1)
    options = await cursor.to_list(None)
    return ServiceOptionListResponse(options=options)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_option(
    product_id: str,
    body: ServiceOptionCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create a new option on this service product."""
    org_id = current_user["organization_id"]
    await _get_service_product_or_404(product_id, org_id)

    option = ServiceOption(
        organization_id=org_id,
        product_id=product_id,
        **body.model_dump(),
    )
    doc = option.model_dump(mode="json")
    await service_options_collection.insert_one(doc)
    doc.pop("_id", None)
    logger.info(
        "service_options: created option=%s product=%s org=%s",
        option.id, product_id, org_id,
    )
    return doc


@router.patch("/{option_id}")
async def update_option(
    product_id: str,
    option_id: str,
    body: ServiceOptionUpdate,
    current_user: dict = Depends(get_verified_user),
):
    """Partial update of an option. Ignores fields not set in the body."""
    org_id = current_user["organization_id"]
    await _get_service_product_or_404(product_id, org_id)

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nessun campo da aggiornare",
        )
    updates["updated_at"] = utc_now().isoformat()

    res = await service_options_collection.update_one(
        {"id": option_id, "organization_id": org_id, "product_id": product_id},
        {"$set": updates},
    )
    if res.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opzione non trovata",
        )

    doc = await service_options_collection.find_one(
        {"id": option_id, "organization_id": org_id},
        {"_id": 0},
    )
    return doc


@router.delete("/{option_id}")
async def delete_option(
    product_id: str,
    option_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Delete an option. Since options are product-level (no reservation
    counter attached), hard-delete is safe: any historical order line
    already carries a snapshot of the label. New orders that referenced
    this option will simply fail validation."""
    org_id = current_user["organization_id"]
    await _get_service_product_or_404(product_id, org_id)

    res = await service_options_collection.delete_one(
        {"id": option_id, "organization_id": org_id, "product_id": product_id},
    )
    if res.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opzione non trovata",
        )
    logger.info(
        "service_options: deleted option=%s product=%s org=%s",
        option_id, product_id, org_id,
    )
    return {"deleted": True}
