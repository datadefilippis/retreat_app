"""
Coupons Router — CRUD for promotional discount codes.

v14.0: Multi-store support via store_ids field.
  - store_ids=[] → coupon valid on all stores in org
  - store_ids=["id1", "id2"] → valid only on those stores
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Query, status
from auth import get_current_user, get_verified_user, get_verified_user
from routers.auth import limiter
from models.coupon import Coupon, CouponCreate, CouponUpdate
from models.common import generate_id, utc_now
from typing import Optional

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.get("")
async def list_coupons(
    store_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_verified_user),
):
    from database import coupons_collection
    org_id = current_user["organization_id"]

    query = {"organization_id": org_id}
    if store_id:
        # Show coupons assigned to this store OR global coupons (empty store_ids)
        query["$or"] = [
            {"store_ids": store_id},
            {"store_ids": {"$size": 0}},
            {"store_ids": {"$exists": False}},
        ]

    cursor = coupons_collection.find(query, {"_id": 0}).sort("created_at", -1).limit(200)
    return await cursor.to_list(200)


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_coupon(request: Request, body: CouponCreate, current_user: dict = Depends(get_verified_user)):
    from database import coupons_collection
    org_id = current_user["organization_id"]

    # Validate: at least one discount type
    if not body.discount_pct and not body.discount_amount:
        raise HTTPException(status_code=400, detail="Specificare discount_pct o discount_amount")

    # Validate: code unique per org (case-insensitive)
    code_upper = body.code.strip().upper()
    existing = await coupons_collection.find_one(
        {"organization_id": org_id, "code": code_upper})
    if existing:
        raise HTTPException(status_code=400, detail=f"Codice '{code_upper}' gia' esistente")

    coupon = Coupon(organization_id=org_id, code=code_upper, **body.model_dump(exclude={"code"}))
    doc = coupon.model_dump(mode="json")
    await coupons_collection.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.patch("/{coupon_id}")
async def update_coupon(coupon_id: str, body: CouponUpdate, current_user: dict = Depends(get_verified_user)):
    from database import coupons_collection
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")
    updates["updated_at"] = utc_now()
    result = await coupons_collection.update_one(
        {"id": coupon_id, "organization_id": current_user["organization_id"]},
        {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Coupon non trovato")
    return {"message": "Coupon aggiornato"}


@router.delete("/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coupon(coupon_id: str, current_user: dict = Depends(get_verified_user)):
    from database import coupons_collection
    result = await coupons_collection.delete_one(
        {"id": coupon_id, "organization_id": current_user["organization_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Coupon non trovato")


# ── Public validation (called from storefront) ──────────────────────────────

async def validate_coupon(
    org_id: str,
    code: str,
    subtotal: float,
    store_id: str = None,
    customer_key: str | None = None,
    order_id: str | None = None,
) -> dict:
    """Validate coupon and atomically reserve usage. Returns dict with discount or raises.

    Uses find_one first (read-only) for validation, then find_one_and_update
    for atomic usage increment — prevents double-redemption race condition.

    store_id: if provided, validates that the coupon is valid for this store.
    Coupons with empty store_ids are valid on all stores.

    R5 — per-customer anti-reuse: quando ``customer_key`` è fornito (account
    id se loggato, altrimenti email lower), si claima atomicamente uno slot in
    ``coupon_redemptions`` (unique su org+coupon+customer). Se il cliente ha
    già redento → 400. Se il global increment fallisce dopo il claim →
    rollback del claim (no slot fantasma). ``order_id`` lega la redemption
    all'ordine per il rollback su cancellazione.
    """
    from database import coupons_collection
    from datetime import date

    clean_code = code.strip().upper()

    # Step 1: Read coupon for validation (non-destructive)
    coupon = await coupons_collection.find_one(
        {"organization_id": org_id, "code": clean_code, "is_active": True},
        {"_id": 0},
    )
    if not coupon:
        raise HTTPException(status_code=400, detail="Codice promo non valido")

    # Store scope validation
    coupon_stores = coupon.get("store_ids") or []
    if store_id and coupon_stores and store_id not in coupon_stores:
        raise HTTPException(status_code=400, detail="Codice promo non valido per questo store")

    today = date.today().isoformat()
    if coupon.get("valid_from") and today < coupon["valid_from"]:
        raise HTTPException(status_code=400, detail="Codice promo non ancora valido")
    if coupon.get("valid_to") and today > coupon["valid_to"]:
        raise HTTPException(status_code=400, detail="Codice promo scaduto")
    if coupon.get("min_order_amount") and subtotal < coupon["min_order_amount"]:
        raise HTTPException(status_code=400, detail=f"Ordine minimo: €{coupon['min_order_amount']:.2f}")

    # Step 2a (R5): claim per-customer slot PRIMA del global increment.
    # L'unique index rifiuta un secondo riscatto dallo stesso cliente.
    redemption_claimed = False
    if customer_key:
        from database import coupon_redemptions_collection
        from models.common import generate_id, utc_now
        from pymongo.errors import DuplicateKeyError
        try:
            await coupon_redemptions_collection.insert_one({
                "id": generate_id(),
                "organization_id": org_id,
                "coupon_id": coupon["id"],
                "code": clean_code,
                "customer_key": customer_key,
                "order_id": order_id,
                "created_at": utc_now(),
            })
            redemption_claimed = True
        except DuplicateKeyError:
            raise HTTPException(status_code=400, detail="Codice promo già utilizzato")

    # Step 2b: Atomic increment — prevents race condition on max_uses
    max_uses = coupon.get("max_uses")
    usage_filter = {"organization_id": org_id, "code": clean_code, "is_active": True}
    if max_uses is not None:
        usage_filter["current_uses"] = {"$lt": max_uses}

    reserved = await coupons_collection.find_one_and_update(
        usage_filter,
        {"$inc": {"current_uses": 1}},
    )
    if not reserved:
        # Rollback del claim per-cliente: il coupon è globalmente esaurito,
        # il cliente non deve restare "bruciato".
        if redemption_claimed:
            from database import coupon_redemptions_collection
            await coupon_redemptions_collection.delete_one({
                "organization_id": org_id,
                "coupon_id": coupon["id"],
                "customer_key": customer_key,
            })
        raise HTTPException(status_code=400, detail="Codice promo esaurito")

    # Step 3: Calculate discount
    if coupon.get("discount_pct"):
        discount = round(subtotal * coupon["discount_pct"] / 100, 2)
    elif coupon.get("discount_amount"):
        discount = min(coupon["discount_amount"], subtotal)
    else:
        discount = 0

    return {"coupon_id": coupon["id"], "code": coupon["code"], "discount": discount}


async def validate_coupon_dry_run(
    org_id: str,
    code: str,
    subtotal: float,
    store_id: str | None = None,
    check_min_order: bool = True,
) -> dict:
    """Track E Step 4.1 — Dry-run validation per il widget price preview.

    Verifica TUTTE le condizioni di validate_coupon() (esiste, attivo, scope
    store, valid_from/to, min_order_amount, max_uses) MA NON incrementa
    current_uses. Usato dall'endpoint pubblico embed
    ``POST /api/public/embed/coupons/validate/{slug}`` per mostrare al
    customer il discount calcolato PRIMA che lui confermi il checkout.

    Il checkout reale invece chiama validate_coupon() (atomic increment)
    per evitare double-redemption race condition. Trade-off accettato:
    customer puo' vedere preview di coupon attivo + esaurirsi tra preview
    e checkout — error message chiaro al submit ("Codice promo esaurito").

    Args:
        org_id, code: come validate_coupon
        subtotal: per applicare min_order_amount check + computare discount
        store_id: optional scope check

    Returns:
        Stesso shape di validate_coupon: {coupon_id, code, discount}.
        Raises HTTPException 400 con detail leggibile (mostrato al user).
    """
    from database import coupons_collection
    from datetime import date

    clean_code = code.strip().upper()

    coupon = await coupons_collection.find_one(
        {"organization_id": org_id, "code": clean_code, "is_active": True},
        {"_id": 0},
    )
    if not coupon:
        raise HTTPException(status_code=400, detail="Codice promo non valido")

    coupon_stores = coupon.get("store_ids") or []
    if store_id and coupon_stores and store_id not in coupon_stores:
        raise HTTPException(status_code=400, detail="Codice promo non valido per questo store")

    today = date.today().isoformat()
    if coupon.get("valid_from") and today < coupon["valid_from"]:
        raise HTTPException(status_code=400, detail="Codice promo non ancora valido")
    if coupon.get("valid_to") and today > coupon["valid_to"]:
        raise HTTPException(status_code=400, detail="Codice promo scaduto")
    # B3 \u2014 il check min_order puo' essere saltato quando il subtotale reale non
    # e' ancora noto (pre-creazione ordine): verra' applicato dopo, sul subtotale
    # autoritativo, da validate_coupon().
    if check_min_order and coupon.get("min_order_amount") and subtotal < coupon["min_order_amount"]:
        raise HTTPException(
            status_code=400,
            detail=f"Ordine minimo: \u20ac{coupon['min_order_amount']:.2f}",
        )

    max_uses = coupon.get("max_uses")
    if max_uses is not None and coupon.get("current_uses", 0) >= max_uses:
        raise HTTPException(status_code=400, detail="Codice promo esaurito")

    # Compute discount (same logic as validate_coupon)
    if coupon.get("discount_pct"):
        discount = round(subtotal * coupon["discount_pct"] / 100, 2)
    elif coupon.get("discount_amount"):
        discount = min(coupon["discount_amount"], subtotal)
    else:
        discount = 0

    return {
        "coupon_id": coupon["id"],
        "code": coupon["code"],
        "discount": discount,
        "discount_pct": coupon.get("discount_pct"),
        "discount_amount": coupon.get("discount_amount"),
    }


async def increment_coupon_usage(org_id: str, coupon_id: str):
    """No-op — usage already incremented atomically in validate_coupon().
    Kept for backward compatibility if called from elsewhere."""
    pass


async def release_coupon_for_order(org_id: str, order: dict) -> int:
    """R5 — rilascia il consumo del coupon legato a un ordine (rollback).

    Chiamata su cancellazione ordine: il coupon non deve restare "consumato"
    se l'ordine è annullato. Idempotente e best-effort:
      1. Decrementa ``current_uses`` sul coupon (via ``order.coupon_code``),
         con floor a 0 (filtro ``current_uses > 0``). Copre anche gli ordini
         senza redemption per-cliente (customer_key assente).
      2. Cancella le righe ``coupon_redemptions`` di questo ordine così il
         cliente può riusare legittimamente il coupon.

    Ritorna il numero di decrementi globali applicati (0 o 1).
    """
    from database import coupons_collection, coupon_redemptions_collection

    code = (order.get("coupon_code") or "").strip().upper()
    order_id = order.get("id")
    released = 0

    if code and (order.get("discount_total") or 0) > 0:
        res = await coupons_collection.update_one(
            {"organization_id": org_id, "code": code, "current_uses": {"$gt": 0}},
            {"$inc": {"current_uses": -1}},
        )
        released = res.modified_count

    if order_id:
        await coupon_redemptions_collection.delete_many(
            {"organization_id": org_id, "order_id": order_id},
        )
    return released
