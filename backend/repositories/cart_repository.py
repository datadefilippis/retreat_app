"""Cart Repository — MongoDB CRUD for server-side persistent carts.

Phase 0 Step 4. Implementa le operazioni atomiche per il cart entity.

Invarianti garantite a livello repository
==========================================
INV-CART-1  Atomic operations via find_one_and_update.
INV-CART-2  Multi-tenant isolation — ogni query filtra su (id, organization_id).
INV-CART-3  expires_at resettato a +60gg ad ogni mutation (cart "vivo").

Note di design
==============
- Carts non hanno status state machine come Order. Sono mutable fino a
  conversione in ordine (poi marcati ``converted_to_order_id`` ma rimangono
  per ~30 giorni come storia, poi cleanup TTL).
- ``updated_at`` bumpato ad ogni mutation per:
  · Cache invalidation lato frontend
  · Identificazione abandon recovery candidates (cart vecchi senza conversione)
- ``expires_at`` esteso ad ogni mutation per "tenere vivo" il cart che il
  customer sta attivamente usando. Cart inattivi naturalmente scadono.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from database import carts_collection
from models.cart import CART_TTL_DAYS, Cart, CartItem


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_expires_at() -> datetime:
    """+60gg da adesso (estende vita del cart ad ogni mutation)."""
    return _utc_now() + timedelta(days=CART_TTL_DAYS)


# ── Create ───────────────────────────────────────────────────────────────


async def create(cart: Cart) -> Cart:
    """Insert a new cart document. Returns the persisted Cart."""
    doc = cart.model_dump()
    # Mongo non serializza datetime nativamente con tutti i client — passiamo
    # come ISO string per stabilità + compatibility con i sentinel test che
    # introspettano i field types.
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    if isinstance(doc.get("updated_at"), datetime):
        doc["updated_at"] = doc["updated_at"].isoformat()
    if isinstance(doc.get("expires_at"), datetime):
        doc["expires_at"] = doc["expires_at"].isoformat()
    await carts_collection.insert_one(doc)
    return cart


# ── Read ─────────────────────────────────────────────────────────────────


async def find_by_id(cart_id: str, organization_id: str) -> Optional[dict]:
    """Find a single cart by id within org (INV-CART-2 multi-tenant)."""
    return await carts_collection.find_one(
        {"id": cart_id, "organization_id": organization_id},
        {"_id": 0},
    )


async def find_active_for_customer_account(
    customer_account_id: str, organization_id: str,
) -> Optional[dict]:
    """Find the most recent active cart owned by a logged-in customer.

    Used during /merge flow: when a guest with cart logs in, we may
    want to surface their previously-saved cart if they have one.
    """
    now_iso = _utc_now().isoformat()
    cursor = (
        carts_collection.find(
            {
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "converted_to_order_id": None,
                "expires_at": {"$gt": now_iso},
            },
            {"_id": 0},
        )
        .sort("updated_at", -1)
        .limit(1)
    )
    docs = await cursor.to_list(length=1)
    return docs[0] if docs else None


# ── Update ───────────────────────────────────────────────────────────────


async def update_items(
    cart_id: str, organization_id: str, items: List[CartItem],
) -> Optional[dict]:
    """Atomic replace of cart items + bump timestamps.

    INV-CART-1: single Mongo find_one_and_update call, no read-then-write race.
    Returns the post-update doc (Mongo ReturnDocument.AFTER).
    """
    from pymongo import ReturnDocument

    now_iso = _utc_now().isoformat()
    expires_iso = _new_expires_at().isoformat()
    items_docs = [item.model_dump() for item in items]

    result = await carts_collection.find_one_and_update(
        {"id": cart_id, "organization_id": organization_id},
        {
            "$set": {
                "items": items_docs,
                "updated_at": now_iso,
                "expires_at": expires_iso,
            }
        },
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    return result


async def update_customer_binding(
    cart_id: str,
    organization_id: str,
    *,
    customer_id: Optional[str] = None,
    customer_email: Optional[str] = None,
    customer_account_id: Optional[str] = None,
) -> Optional[dict]:
    """Bind customer identifiers to an anonymous cart (merge flow).

    Used during checkout (email/account known) or during /merge endpoint
    (anonymous cart claimed by logged-in user).

    Only sets fields explicitly provided (None args are skipped). This
    prevents accidental nulling of an existing binding.
    """
    from pymongo import ReturnDocument

    set_fields = {
        "updated_at": _utc_now().isoformat(),
        "expires_at": _new_expires_at().isoformat(),
    }
    if customer_id is not None:
        set_fields["customer_id"] = customer_id
    if customer_email is not None:
        set_fields["customer_email"] = customer_email
    if customer_account_id is not None:
        set_fields["customer_account_id"] = customer_account_id

    result = await carts_collection.find_one_and_update(
        {"id": cart_id, "organization_id": organization_id},
        {"$set": set_fields},
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    return result


async def mark_converted_to_order(
    cart_id: str, organization_id: str, order_id: str,
) -> bool:
    """Mark cart as converted to a confirmed order.

    Cart non viene deleted — resta come storia consumption per analytics
    + abandon recovery (i recovery non sono mai inviati per cart già
    converted_to_order_id).
    """
    result = await carts_collection.update_one(
        {"id": cart_id, "organization_id": organization_id},
        {
            "$set": {
                "converted_to_order_id": order_id,
                "updated_at": _utc_now().isoformat(),
            }
        },
    )
    return result.matched_count > 0


# ── Delete / Clear ───────────────────────────────────────────────────────


async def clear_items(cart_id: str, organization_id: str) -> Optional[dict]:
    """Empty cart items list (cart stays alive for re-use).

    Diverso da delete — il cart_id rimane valido + il cookie del client
    non viene scartato. Permette al customer di svuotare e riempire.
    """
    return await update_items(cart_id, organization_id, [])


async def delete_by_id(cart_id: str, organization_id: str) -> bool:
    """Hard delete del cart (in caso di explicit "abbandon" request)."""
    result = await carts_collection.delete_one(
        {"id": cart_id, "organization_id": organization_id}
    )
    return result.deleted_count > 0


# ── Cleanup / Abandon recovery support ───────────────────────────────────


async def find_abandoned_for_recovery(
    organization_id: str,
    *,
    older_than_hours: int = 24,
    younger_than_days: int = 7,
    limit: int = 50,
) -> List[dict]:
    """Find abandoned carts eligible for email recovery.

    Criteri (default):
      - Updated > 24 ore fa (sufficientemente "stale")
      - Updated < 7 giorni fa (non troppo vecchio)
      - Non ancora converted (converted_to_order_id is None)
      - Customer email presente (per inviare email)
      - Almeno 1 item nel cart

    Phase 0 Step 4 espone questo metodo per il worker abandon recovery
    (Step 4b/4c, separato).
    """
    now = _utc_now()
    cutoff_old_iso = (now - timedelta(hours=older_than_hours)).isoformat()
    cutoff_young_iso = (now - timedelta(days=younger_than_days)).isoformat()

    cursor = carts_collection.find(
        {
            "organization_id": organization_id,
            "converted_to_order_id": None,
            "customer_email": {"$exists": True, "$ne": None},
            "updated_at": {"$lt": cutoff_old_iso, "$gt": cutoff_young_iso},
            "items.0": {"$exists": True},  # at least 1 item
        },
        {"_id": 0},
    ).limit(limit)
    return await cursor.to_list(length=limit)
