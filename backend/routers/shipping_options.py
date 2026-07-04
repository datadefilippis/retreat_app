"""
Shipping Options CRUD — admin-side configuration of delivery methods.

Routes (authenticated, org-scoped):
  GET    /api/shipping-options?store_id=&scope=
  POST   /api/shipping-options
  PATCH  /api/shipping-options/{option_id}
  DELETE /api/shipping-options/{option_id}

Scope model:
  - An option with store_id=null is GLOBAL for the org — it appears in
    every store's public checkout.
  - An option with store_id=X is visible ONLY in that store's checkout.
  - The public resolver (see routers/public.py) unions both for a given
    store_slug.

Why a top-level `/shipping-options` (not nested under /stores/{id}/...)?
  Because globals have no store parent. A non-nested router keeps create
  and list symmetric for both scopes with a single `store_id` query/body
  field. Admins pick scope explicitly at create time.

GET query params:
  scope=store  → only options with store_id == the provided store_id
  scope=global → only options with store_id=null (org-global)
  scope=all    → BOTH store-specific (if store_id given) + globals
  no scope, no store_id → listing all options across the org (admin overview)
  no scope, store_id given → equivalent to scope=store (back-compat default)

Authorization: `get_current_user`. Admin-only via role check on
mutation endpoints (POST/PATCH/DELETE), mirroring other admin routers.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from models.common import utc_now
from models.shipping_option import (
    ShippingOption, ShippingOptionCreate, ShippingOptionUpdate,
    ShippingOptionResponse,
)
from database import shipping_options_collection, stores_collection
from auth import get_current_user, get_verified_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shipping-options", tags=["Shipping Options"])


class ShippingOptionListResponse(BaseModel):
    options: List[ShippingOptionResponse]


def _require_admin(user: dict) -> None:
    """Admin-only gate for mutation endpoints (parity with other routers)."""
    if user.get("role") not in ("admin", "system_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo gli amministratori possono modificare le opzioni di spedizione.",
        )


async def _assert_store_belongs_to_org(store_id: str, org_id: str) -> None:
    """Validate that `store_id`, when provided, is an actual store of the
    calling org — prevents creating options scoped to another org's store."""
    store = await stores_collection.find_one(
        {"id": store_id, "organization_id": org_id},
        {"_id": 0, "id": 1},
    )
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store non trovato",
        )


# ── GET ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=ShippingOptionListResponse)
async def list_shipping_options(
    store_id: Optional[str] = Query(
        None,
        description="Filter by exact store_id. Empty = depends on `scope`.",
    ),
    scope: Optional[str] = Query(
        None,
        pattern="^(store|global|all)$",
        description=(
            "store = only options for the given store_id. "
            "global = only org-global options (store_id=null). "
            "all = store options AND globals (requires store_id)."
        ),
    ),
    current_user: dict = Depends(get_verified_user),
):
    """List shipping options for the current org, filtered by scope."""
    org_id = current_user["organization_id"]

    query: dict = {"organization_id": org_id}
    if scope == "global":
        query["store_id"] = None
    elif scope == "store":
        if not store_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope=store richiede il parametro store_id",
            )
        await _assert_store_belongs_to_org(store_id, org_id)
        query["store_id"] = store_id
    elif scope == "all":
        if not store_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope=all richiede il parametro store_id",
            )
        await _assert_store_belongs_to_org(store_id, org_id)
        query["$or"] = [{"store_id": store_id}, {"store_id": None}]
    else:
        # Back-compat: no scope → if store_id set filter by it, else list all
        # across the org (admin overview).
        if store_id:
            await _assert_store_belongs_to_org(store_id, org_id)
            query["store_id"] = store_id
        # else: no filter — return all options of the org

    cursor = shipping_options_collection.find(query, {"_id": 0}).sort(
        [("store_id", 1), ("sort_order", 1), ("label", 1)]
    )
    options = await cursor.to_list(None)
    return ShippingOptionListResponse(options=options)


# ── POST ────────────────────────────────────────────────────────────────────


@router.post("", response_model=ShippingOptionResponse, status_code=status.HTTP_201_CREATED)
async def create_shipping_option(
    body: ShippingOptionCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create a new shipping option.

    `body.store_id` = null creates a global (org-level) option.
    """
    _require_admin(current_user)
    org_id = current_user["organization_id"]

    if body.store_id:
        await _assert_store_belongs_to_org(body.store_id, org_id)

    doc = ShippingOption(
        organization_id=org_id,
        store_id=body.store_id,
        **body.model_dump(exclude={"store_id"}),
    ).model_dump(mode="json")

    await shipping_options_collection.insert_one(doc)
    doc.pop("_id", None)

    logger.info(
        "shipping_options: created id=%s org=%s store=%s label=%s",
        doc["id"], org_id, body.store_id or "(global)", body.label,
    )
    return ShippingOptionResponse(**doc)


# ── PATCH ───────────────────────────────────────────────────────────────────


@router.patch("/{option_id}", response_model=ShippingOptionResponse)
async def update_shipping_option(
    option_id: str,
    body: ShippingOptionUpdate,
    current_user: dict = Depends(get_verified_user),
):
    """Partial update. `store_id` is intentionally NOT updatable — delete
    and recreate to move an option between scopes. Snapshots on existing
    orders reference the option by id+label, not by scope, so historical
    data stays coherent."""
    _require_admin(current_user)
    org_id = current_user["organization_id"]

    existing = await shipping_options_collection.find_one(
        {"id": option_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opzione di spedizione non trovata",
        )

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        # Nothing to do — return the existing row unchanged.
        return ShippingOptionResponse(**existing)

    updates["updated_at"] = utc_now()
    await shipping_options_collection.update_one(
        {"id": option_id, "organization_id": org_id},
        {"$set": updates},
    )

    refreshed = await shipping_options_collection.find_one(
        {"id": option_id, "organization_id": org_id}, {"_id": 0},
    )
    logger.info("shipping_options: updated id=%s org=%s fields=%s",
                option_id, org_id, list(updates.keys()))
    return ShippingOptionResponse(**refreshed)


# ── DELETE ──────────────────────────────────────────────────────────────────


@router.delete("/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shipping_option(
    option_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Hard-delete the option row.

    Existing orders that reference this option keep their snapshot
    (`fulfillment.shipping_option_label` + `shipping_cost`) — deletion is
    safe because admin + customer reads never dereference option_id after
    the order exists. If a soft-delete audit trail is needed later, flip
    this to an `is_active=False` update."""
    _require_admin(current_user)
    org_id = current_user["organization_id"]

    result = await shipping_options_collection.delete_one(
        {"id": option_id, "organization_id": org_id},
    )
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opzione di spedizione non trovata",
        )
    logger.info("shipping_options: deleted id=%s org=%s", option_id, org_id)
    return None
