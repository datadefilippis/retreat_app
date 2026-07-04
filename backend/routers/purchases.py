from fastapi import APIRouter, HTTPException, Query, Request, status, Depends
from typing import List, Optional
from models import PurchaseRecord, PurchaseRecordCreate
from models.financial_record import PurchaseRecordUpdate
from auth import get_current_user, get_verified_user, get_verified_user
from repositories import purchase_repository
from services.module_access import check_module_access, record_module_usage
# v5.8 / Onda 10 Step D.2 — rate limit
from routers.auth import limiter


def _csv_to_list(v: Optional[str]) -> Optional[List[str]]:
    """Parse CSV query string → list. See sales.py for design notes."""
    if not v:
        return None
    parts = [s.strip() for s in v.split(",") if s.strip()]
    return parts if parts else None


def _csv_to_float_list(v: Optional[str]) -> Optional[List[float]]:
    """Parse CSV of floats — used for the ``iva`` filter (0,4,10,22)."""
    if not v:
        return None
    out = []
    for s in v.split(","):
        s = s.strip()
        if not s:
            continue
        try:
            out.append(float(s))
        except ValueError:
            # Skip garbage tokens silently — the strict variant would
            # 422 the whole request, but for a numeric multi-select that
            # already comes from a static list the lenient path is safer.
            continue
    return out if out else None


router = APIRouter(prefix="/purchases", tags=["Purchases"])


@router.get("")
async def list_purchases(
    limit: int = Query(500, le=5000),
    current_user: dict = Depends(get_verified_user),
):
    """List purchase records for the organization (default 500, max 5000)."""
    org_id = current_user['organization_id']
    records = await purchase_repository.find_by_org(org_id, limit=limit)
    return records


# ── Phase 2 endpoint — paginated + filtered search ──────────────────────
@router.get("/search")
async def search_purchases(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    due_date_from: Optional[str] = None,
    due_date_to: Optional[str] = None,
    supplier_names: Optional[str] = None,      # CSV by name
    supplier_ids: Optional[str] = None,        # CSV by FK
    product_ids: Optional[str] = None,
    categories: Optional[str] = None,
    categories_macro: Optional[str] = None,
    units: Optional[str] = None,
    iva_values: Optional[str] = None,          # CSV of floats
    payment_status: Optional[str] = None,
    source: Optional[str] = Query(None, pattern="^(manual|file)$"),
    quantity_min: Optional[float] = Query(None, ge=0),
    quantity_max: Optional[float] = Query(None, ge=0),
    unit_price_min: Optional[float] = Query(None, ge=0),
    unit_price_max: Optional[float] = Query(None, ge=0),
    q: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_verified_user),
):
    """Paginated + filtered purchase records.

    ``q`` searches across BOTH ``description`` AND ``invoice_number`` —
    matches the merchant's mental model of a single search box on the UI.
    See sales.search_sales for the envelope shape.
    """
    org_id = current_user['organization_id']
    return await purchase_repository.find_paginated(
        org_id,
        date_from=date_from,
        date_to=date_to,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        supplier_names=_csv_to_list(supplier_names),
        supplier_ids=_csv_to_list(supplier_ids),
        product_ids=_csv_to_list(product_ids),
        categories=_csv_to_list(categories),
        categories_macro=_csv_to_list(categories_macro),
        units=_csv_to_list(units),
        iva_values=_csv_to_float_list(iva_values),
        payment_status=_csv_to_list(payment_status),
        source=source,
        quantity_min=quantity_min,
        quantity_max=quantity_max,
        unit_price_min=unit_price_min,
        unit_price_max=unit_price_max,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.post("")
@limiter.limit("60/minute")
async def create_purchases(
    request: Request,
    records: List[PurchaseRecordCreate],
    current_user: dict = Depends(get_verified_user)
):
    """Bulk create purchase records (manual entry).

    v5.8 / Onda 10 Step D.2 — 60 req/min IP.
    """
    org_id = current_user['organization_id']
    await check_module_access(org_id, "cashflow_monitor", "data_rows", pending_quantity=len(records))

    docs = []
    for r in records:
        total_price = round(r.quantity * r.unit_price, 2)

        # VAT computation (Wave A): server-owned, never trust client total_with_iva
        iva_val = getattr(r, 'iva', None)
        total_with_iva = None
        if iva_val is not None:
            total_with_iva = round(total_price * (1 + iva_val / 100), 2)

        # Validate FK references if provided
        resolved_supplier_id = getattr(r, 'supplier_id', None)
        if resolved_supplier_id:
            from repositories import supplier_repository
            s = await supplier_repository.find_by_id(resolved_supplier_id, org_id)
            if not s:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Supplier '{resolved_supplier_id}' not found")
        elif r.supplier_name:
            # Auto-create supplier if not explicitly provided
            try:
                from repositories import supplier_repository
                auto_supp = await supplier_repository.get_or_create_by_name(org_id, r.supplier_name)
                resolved_supplier_id = auto_supp.id
            except Exception:
                pass  # non-blocking

        if getattr(r, 'product_id', None):
            from repositories import product_repository
            p = await product_repository.find_by_id(r.product_id, org_id)
            if not p:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product '{r.product_id}' not found")

        purchase = PurchaseRecord(
            organization_id=org_id,
            date=r.date,
            supplier_name=r.supplier_name,
            quantity=r.quantity,
            unit=r.unit,
            unit_price=r.unit_price,
            total_price=total_price,
            iva=iva_val,
            total_with_iva=total_with_iva,
            category=r.category,
            category_macro=getattr(r, 'category_macro', None),
            description=r.description,
            supplier_id=resolved_supplier_id,
            product_id=getattr(r, 'product_id', None),
            source_label="Manuale",
        )
        docs.append(purchase.model_dump())

    count = await purchase_repository.insert_many(docs)
    await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=count)
    return {"inserted": count}


@router.patch("/{record_id}")
async def update_purchase(
    record_id: str,
    updates: PurchaseRecordUpdate,
    current_user: dict = Depends(get_verified_user),
):
    """Update a single purchase record (partial update).

    If quantity or unit_price is changed, total_price is recalculated
    automatically using the other value from the existing record.
    """
    data = updates.model_dump(exclude_unset=True)

    # Strip total_with_iva if client sent it — server-owned field
    data.pop("total_with_iva", None)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nessun campo da aggiornare",
        )
    org_id = current_user['organization_id']

    # Validate FK references if present and non-null
    if data.get("supplier_id"):
        from repositories import supplier_repository
        s = await supplier_repository.find_by_id(data["supplier_id"], org_id)
        if not s:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier not found")
    if data.get("product_id"):
        from repositories import product_repository
        p = await product_repository.find_by_id(data["product_id"], org_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not found")

    # Load existing record if we need it for recalculation
    needs_existing = ("quantity" in data or "unit_price" in data or "iva" in data)
    existing = None
    if needs_existing:
        existing = await purchase_repository.find_one(record_id, org_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record non trovato",
            )

    # Recalculate total_price when quantity or unit_price changes
    if "quantity" in data or "unit_price" in data:
        qty = data.get("quantity", existing["quantity"])
        price = data.get("unit_price", existing["unit_price"])
        data["total_price"] = round(qty * price, 2)

    # VAT computation (Wave A): server-owned total_with_iva
    if "iva" in data:
        iva_val = data.get("iva")
        if iva_val is not None:
            tp = data.get("total_price", existing["total_price"] if existing else 0)
            data["total_with_iva"] = round(tp * (1 + iva_val / 100), 2)
        else:
            data["total_with_iva"] = None
    elif "total_price" in data and existing and existing.get("iva") is not None:
        # total_price changed but IVA unchanged — recompute total_with_iva
        data["total_with_iva"] = round(data["total_price"] * (1 + existing["iva"] / 100), 2)

    ok = await purchase_repository.update_one(record_id, org_id, data)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record non trovato",
        )
    return {"message": "Record aggiornato", "id": record_id}


@router.delete("/{record_id}")
async def delete_purchase(
    record_id: str,
    current_user: dict = Depends(get_verified_user)
):
    """Delete a single purchase record"""
    org_id = current_user['organization_id']
    deleted = await purchase_repository.delete_one(record_id, org_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record non trovato"
        )
    return {"message": "Record eliminato"}


@router.get("/suppliers")
async def get_suppliers(current_user: dict = Depends(get_verified_user)):
    """Get distinct supplier names for autocomplete — merges purchase history + supplier catalog."""
    org_id = current_user['organization_id']
    purchase_names = await purchase_repository.get_distinct_suppliers(org_id)
    # Merge with supplier catalog for richer autocomplete
    try:
        from repositories import supplier_repository
        catalog = await supplier_repository.find_by_org(org_id, active_only=True, limit=500)
        catalog_names = [s.name for s in catalog]
    except Exception:
        catalog_names = []
    # Deduplicate case-insensitive
    seen = set()
    merged = []
    for name in purchase_names + catalog_names:
        key = name.lower().strip()
        if key and key not in seen:
            seen.add(key)
            merged.append(name)
    return sorted(merged)


@router.get("/categories")
async def get_categories(current_user: dict = Depends(get_verified_user)):
    """Get distinct categories (product-level) for autocomplete"""
    org_id = current_user['organization_id']
    categories = await purchase_repository.get_distinct_categories(org_id)
    return categories


@router.get("/categories-macro")
async def get_categories_macro(current_user: dict = Depends(get_verified_user)):
    """Get distinct macro categories for autocomplete"""
    org_id = current_user['organization_id']
    categories = await purchase_repository.get_distinct_categories_macro(org_id)
    return categories
