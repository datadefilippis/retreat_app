"""
Catalog — read-only reference endpoints for the product catalog.

Single responsibility: expose the backend's authoritative
declarations (offer profiles, product types) so frontend / mobile /
partner clients can fetch the registry instead of duplicating it.

Not a CRUD surface. No writes. Auth-protected so only logged-in
users see the catalog — prevents casual scraping but not a security
boundary (the data is not sensitive).

Endpoints:
  GET /api/catalog/offer-profiles
      Returns the 6 offer profiles with their atomic axes + behavior.
      Lets the frontend stop shipping its own copy of the list and
      sources the truth from the server. See models/offer_profiles.py
      for the schema.

  GET /api/catalog/product-types
      Returns the 5 product types with their capability flags
      (requires_stock / requires_calendar / requires_occurrences /
      direct_checkout_default_safe / default_fulfillment_mode).
      Mirror of models/product_types.PRODUCT_TYPES.

Design:
  - Both endpoints are GET, no query params, no pagination — the
    registries are small and stable.
  - Responses are plain JSON lists (not wrapped) to mirror the
    frontend's existing constant shapes.
  - Authenticated via get_current_user so the endpoints slot into the
    same auth model as /products. No org-scoping: the registry is
    platform-wide, not tenant-specific.
"""

from fastapi import APIRouter, Depends
from typing import List, Dict

from auth import get_current_user, get_verified_user, get_verified_user
from models.offer_profiles import serialize_catalog as serialize_offer_profiles
from models.product_types import PRODUCT_TYPES


router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/offer-profiles", response_model=List[Dict])
async def list_offer_profiles(
    current_user: dict = Depends(get_verified_user),
):
    """Return the canonical offer profile catalog.

    Each entry contains:
      id, item_type, transaction_mode, price_mode, behavior, description

    Order is stable (matches the UI picker order). Shape is the dict
    form of OfferProfile; UI-only decorations (icons, i18n labels)
    remain client-side concerns.
    """
    return serialize_offer_profiles()


@router.get("/product-types", response_model=List[Dict])
async def list_product_types(
    current_user: dict = Depends(get_verified_user),
):
    """Return the canonical product-type catalog.

    Each entry contains:
      key, label_key, requires_stock, requires_calendar,
      requires_occurrences, direct_checkout_default_safe,
      default_fulfillment_mode, description

    Mirror of models.product_types.PRODUCT_TYPES. Order matches the
    central registry.
    """
    out: List[Dict] = []
    for key, t in PRODUCT_TYPES.items():
        out.append({
            "key": t.key,
            "label_key": t.label_key,
            "requires_stock": t.requires_stock,
            "requires_calendar": t.requires_calendar,
            "requires_occurrences": t.requires_occurrences,
            "direct_checkout_default_safe": t.direct_checkout_default_safe,
            "default_fulfillment_mode": t.default_fulfillment_mode,
            "description": t.description,
        })
    return out
