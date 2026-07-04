"""
Store Setup Progress Router — deterministic progress model for merchant setup.

Single endpoint that aggregates setup completion state from existing data.
No AI, no new semantics — pure business logic queries on existing collections.

Used by the future Smart Setup Card in the dashboard.
"""

import logging
from fastapi import APIRouter, Depends

from auth import get_current_user, get_verified_user, get_verified_user
from database import (
    organizations_collection,
    products_collection,
    payment_connections_collection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/store", tags=["Store Progress"])

# Step order for next_step calculation
STEP_ORDER = ["identity", "products", "email", "payments", "fulfillment", "published"]


@router.get("/setup-progress")
async def get_setup_progress(current_user: dict = Depends(get_verified_user)):
    """Return deterministic setup progress for the current org's store.

    Each step has:
      done: bool — whether the step is complete
      details: dict — specific sub-checks for UI rendering

    Also returns:
      progress_pct: int — percentage of steps complete
      store_status: str — from compute_readiness (live/degraded/inactive)
      next_step: str|null — first incomplete step in logical order
    """
    org_id = current_user["organization_id"]

    # Load org with store_settings
    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "id": 1, "name": 1, "public_slug": 1, "is_active": 1, "store_settings": 1},
    )
    if not org:
        return {"error": "Organization not found"}

    store = org.get("store_settings") or {}

    # ── Step 1: Identity ─────────────────────────────────────────────────
    has_display_name = bool(store.get("display_name"))
    has_contact_email = bool(store.get("contact_email"))
    has_description = bool(store.get("store_description"))

    identity_done = has_display_name and has_contact_email

    # ── Step 2: Products ─────────────────────────────────────────────────
    # Reuse _is_product_truly_publishable from store_settings readiness
    from routers.store_settings import _is_product_truly_publishable

    products_cursor = products_collection.find(
        {"organization_id": org_id, "is_active": True},
        {"_id": 0, "is_published": 1, "transaction_mode": 1, "price_mode": 1, "unit_price": 1},
    ).limit(100)

    total_products = 0
    published_products = 0
    truly_publishable = 0
    without_price = 0
    with_errors = 0
    has_direct_products = False

    async for prod in products_cursor:
        total_products += 1
        is_pub = prod.get("is_published", False)
        if is_pub:
            published_products += 1
        # Check publishability (same logic as readiness)
        if _is_product_truly_publishable(prod):
            if is_pub:
                truly_publishable += 1
        else:
            if is_pub:
                with_errors += 1
        # Count products without price (fixed mode, no unit_price)
        pm = prod.get("price_mode", "fixed")
        up = prod.get("unit_price")
        if pm == "fixed" and not up and up != 0:
            without_price += 1
        # Track if any product uses direct checkout
        if prod.get("transaction_mode") == "direct":
            has_direct_products = True

    # Products done = at least 1 truly publishable product (same as readiness)
    products_done = truly_publishable > 0

    # ── Step 3: Email ────────────────────────────────────────────────────
    has_sender_name = bool(store.get("sender_display_name"))
    has_reply_to = bool(store.get("reply_to_email"))

    email_done = has_sender_name and has_reply_to

    # ── Step 4: Payments ─────────────────────────────────────────────────
    payment_conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "status": "active", "runtime_status": "ready"},
        {"_id": 0, "id": 1},
    )
    provider_connected = payment_conn is not None

    # Payments done if: Stripe connected, OR no direct products (Stripe not needed)
    payments_done = provider_connected or not has_direct_products

    # ── Step 5: Fulfillment ──────────────────────────────────────────────
    ff_modes = store.get("fulfillment_modes") or ["shipping"]

    # Fulfillment is always "done" — the default is a valid configuration
    fulfillment_done = True

    # ── Step 6: Published ────────────────────────────────────────────────
    is_published = bool(store.get("is_storefront_published"))

    # Get readiness for store_status and overall
    from routers.store_settings import compute_readiness
    readiness = await compute_readiness(org_id, org, store)

    published_done = is_published

    # ── Aggregate ────────────────────────────────────────────────────────
    steps = {
        "identity": {
            "done": identity_done,
            "details": {
                "has_display_name": has_display_name,
                "has_contact_email": has_contact_email,
                "has_description": has_description,
            },
        },
        "products": {
            "done": products_done,
            "details": {
                "total": total_products,
                "published": published_products,
                "truly_publishable": truly_publishable,
                "with_errors": with_errors,
                "without_price": without_price,
            },
        },
        "email": {
            "done": email_done,
            "details": {
                "has_sender_name": has_sender_name,
                "has_reply_to": has_reply_to,
            },
        },
        "payments": {
            "done": payments_done,
            "details": {
                "provider_connected": provider_connected,
                "has_direct_products": has_direct_products,
            },
        },
        "fulfillment": {
            "done": fulfillment_done,
            "details": {
                "modes": ff_modes,
            },
        },
        "published": {
            "done": published_done,
            "details": {
                "is_storefront_published": is_published,
                "readiness_overall": readiness.get("overall"),
            },
        },
    }

    done_count = sum(1 for s in steps.values() if s["done"])
    total_steps = len(steps)
    progress_pct = round((done_count / total_steps) * 100)

    # Next step: first incomplete in logical order
    next_step = None
    for key in STEP_ORDER:
        if not steps[key]["done"]:
            next_step = key
            break

    return {
        "steps": steps,
        "progress_pct": progress_pct,
        "store_status": readiness.get("store_status", "inactive"),
        "next_step": next_step,
    }
