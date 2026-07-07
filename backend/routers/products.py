from fastapi import APIRouter, HTTPException, status, Depends, Query, Request, UploadFile, File, Response
from routers.auth import limiter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
import os
import shutil

from auth import get_current_user, get_verified_user, get_verified_user
from models.product import ProductCreate, ProductResponse, ProductUpdate
from repositories import product_repository
from services.url_builder import PUBLIC_APP_URL

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "products")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# Onda 16 Fase 6: deprecation signal for item_type=booking.
# The value itself still works (accepted on writes, shown on reads of legacy
# documents) but is silently rewritten to `rental + reservation_flavor=slot`
# on new writes. Clients receive the X-Deprecated header as a nudge.
_DEPRECATED_BOOKING_HEADER = (
    "item_type=booking; replacement=rental+reservation_flavor=slot"
)


def _rewrite_deprecated_booking(data_dict: dict) -> bool:
    """Rewrite item_type=booking → rental+reservation_flavor=slot in-place.

    Mutates data_dict. Returns True when a rewrite happened (used to decide
    whether to add the X-Deprecated response header).

    Preserves any existing metadata keys (slot_duration_minutes, duration_label,
    etc.) so the resulting product behaves exactly like the old booking did.
    """
    if data_dict.get("item_type") != "booking":
        return False
    data_dict["item_type"] = "rental"
    meta = dict(data_dict.get("metadata") or {})
    if not meta.get("reservation_flavor"):
        meta["reservation_flavor"] = "slot"
    data_dict["metadata"] = meta
    logger.warning(
        "products: rewrote deprecated item_type=booking to rental+slot for payload name=%r",
        data_dict.get("name"),
    )
    return True


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/check-sku")
async def check_sku_availability(
    sku: str = Query(..., min_length=1, max_length=120),
    exclude_product_id: Optional[str] = Query(
        None,
        description=(
            "When editing an existing product, exclude it from the conflict "
            "check so the user can save the form without changing the SKU."
        ),
    ),
    current_user: dict = Depends(get_verified_user),
):
    """Lightweight SKU uniqueness check for the create / edit forms.

    2026-05-20 — Added so the frontend can debounce a per-keystroke
    availability check (typically 400ms) and tell the merchant
    immediately whether their chosen SKU is free, instead of waiting
    until they hit "Crea prodotto" at the end of a 5-step wizard.

    The check is ORG-SCOPED: SKUs only need to be unique within the
    same organization. Two different organizations can both have a
    product with SKU "PIZZA-MARGHERITA" — they live in separate
    tenant universes.

    The endpoint:
      · returns 200 with ``{available: bool, conflicting_product_id?:
        str}`` whether or not the SKU is taken — this is a query,
        not a mutation, so 4xx feels wrong.
      · trims + lowercases nothing — the comparison is byte-exact so
        "PIZZA-001" and "pizza-001" are considered different (matches
        the product create logic which is also case-sensitive).
      · is rate-limited implicitly through ``get_verified_user`` →
        the auth layer already throttles per-user.

    Sub-200ms response: a single ``find_one`` with a projection and
    an index on ``(organization_id, sku)`` is enough.
    """
    from database import products_collection

    org_id = current_user["organization_id"]
    query = {
        "organization_id": org_id,
        "sku": sku,
    }
    if exclude_product_id:
        # When editing, the product being edited is allowed to keep its
        # own SKU. Exclude it from the conflict scan.
        query["id"] = {"$ne": exclude_product_id}

    try:
        conflict = await products_collection.find_one(
            query, {"_id": 0, "id": 1},
        )
    except Exception as exc:
        # Soft-fail: report "available=true" rather than blocking the
        # form on a database hiccup. The hard uniqueness check still
        # runs at create-time on the backend — this endpoint is a UX
        # hint, not the authoritative gate.
        logger.warning(
            "products.check_sku_availability: lookup failed for org=%s "
            "sku=%r: %s", org_id, sku, exc,
        )
        return {"available": True, "degraded": True}

    if conflict:
        return {
            "available": False,
            "conflicting_product_id": conflict.get("id"),
        }
    return {"available": True}


@router.get("", response_model=List[ProductResponse])
async def list_products(
    active_only: bool = Query(True),
    store_id: Optional[str] = Query(None),
    limit: int = Query(500, le=1000),
    current_user: dict = Depends(get_verified_user),
):
    products = await product_repository.find_by_org(
        current_user["organization_id"], active_only=active_only, limit=limit
    )
    # v12.0: optional store_id filter (products with this store in store_ids, or unassigned)
    if store_id:
        products = [p for p in products if store_id in (p.store_ids or []) or not p.store_ids]
    return [ProductResponse(**p.model_dump()) for p in products]


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    response: Response,
    current_user: dict = Depends(get_verified_user),
):
    # v5.8 / Onda 9.L — Catalog quota enforcement. The /plans page advertises
    # "Fino a N prodotti a catalogo" per plan; this is the write-time gate
    # that makes that promise real. Without this, the limit was a marketing
    # claim with no enforcement (Free user could create unlimited products).
    org_id = current_user["organization_id"]

    # V4 (5/7/2026) — categoria dalla tassonomia per-tipo (mai testo
    # libero) e gate store-first su OGNI pubblicazione, non solo ritiri.
    from models.retreat_taxonomy import PRODUCT_TAXONOMIES, RETREAT_CATEGORIES
    _tax = PRODUCT_TAXONOMIES.get(data.item_type) or (
        RETREAT_CATEGORIES if data.item_type == "event_ticket" else None)
    if _tax is not None and data.category and data.category not in _tax:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Categoria non valida. Scegli una categoria dall'elenco.",
        )
    if getattr(data, "is_published", False):
        from services.store_guard import require_public_home
        await require_public_home(org_id)

    # Multilingua manuale (6/7) — whitelist lingue/campi/lunghezze
    if getattr(data, "translations", None) is not None:
        from services.manual_translations import sanitize_translations
        data.translations = sanitize_translations(data.translations)

    from services.module_access import enforce_count_quota
    from database import products_collection
    current_count = await products_collection.count_documents({"organization_id": org_id})
    await enforce_count_quota(
        org_id, "product_catalog", "products",
        current_count=current_count,
        message_template=(
            "Hai raggiunto il limite di {limit} prodotti a catalogo del tuo piano. "
            "Aggiorna il piano per crearne altri."
        ),
        hard_abuse_cap=10000,  # safety net for unlimited plans
    )

    # P4: normalize type-specific metadata through the registry validator.
    # Permissive by design — unknown keys pass through, typed fields get
    # coerced / range-checked. No legitimate payload is rejected.
    from models.product_types import validate_metadata
    data_dict = data.model_dump()
    # Onda 16 Fase 6: soft-deprecate item_type=booking. Rewrite BEFORE metadata
    # validation so the registry picks the new schema.
    if _rewrite_deprecated_booking(data_dict):
        response.headers["X-Deprecated"] = _DEPRECATED_BOOKING_HEADER
    data_dict["metadata"] = validate_metadata(data_dict.get("item_type"), data_dict.get("metadata"))

    # Sprint 1 W1.5 — sanitize merchant-editable text fields (anti-XSS
    # defense-in-depth, pinned by TestSEC_E_8_5_MarkdownXSSSafe). Strips
    # tutti gli HTML tag + event handler + URL schemes pericolosi PRIMA
    # della persistenza Mongo. Anche se frontend render fosse compromesso,
    # input dannoso non raggiunge mai il database.
    from services.markdown_safe import sanitize_merchant_text
    if data_dict.get("description"):
        data_dict["description"] = sanitize_merchant_text(data_dict["description"])
    # long_description vive in metadata (vedi product detail enrichment)
    meta = data_dict.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("long_description"):
        meta["long_description"] = sanitize_merchant_text(meta["long_description"])
        data_dict["metadata"] = meta

    # P11: if the client sent the three atomic axes but no
    # offer_profile_id, derive the canonical id and persist it alongside.
    # Keeps the stored row self-describing for future analytics /
    # reporting without requiring the frontend to always send it.
    if not data_dict.get("offer_profile_id"):
        from models.offer_profiles import derive_profile_from_axes
        derived = derive_profile_from_axes(
            data_dict.get("item_type"),
            data_dict.get("transaction_mode"),
            data_dict.get("price_mode"),
        )
        if derived:
            data_dict["offer_profile_id"] = derived

    # Onda 13 — auto-generate unique slug when the caller didn't provide
    # one (or provided empty). Used by the public product landing page.
    org_id = current_user["organization_id"]
    raw_slug = data_dict.get("slug")
    if not raw_slug or not str(raw_slug).strip():
        from services.product_slug import generate_product_slug
        data_dict["slug"] = await generate_product_slug(
            org_id, data_dict.get("name", ""),
        )
    else:
        # Sanitize + dedupe against existing (admin may have typed one manually)
        from models.event_occurrence import slugify
        from services.product_slug import generate_product_slug
        sanitized = slugify(raw_slug)
        if sanitized:
            data_dict["slug"] = await generate_product_slug(
                org_id, sanitized,
            )
        else:
            data_dict["slug"] = await generate_product_slug(
                org_id, data_dict.get("name", ""),
            )

    # CH compliance v1: snapshot the org's currency onto the product at
    # create time when the client didn't supply one. Without this, every
    # product created on a CHF org would persist with currency=None and
    # later default to EUR through the read-time fallback chain.
    if not data_dict.get("currency"):
        from repositories import organization_repository
        from services.currency_service import get_currency_for_org
        org_doc = await organization_repository.find_by_id(org_id)
        data_dict["currency"] = get_currency_for_org(org_doc or {})

    # Re-build the Pydantic instance so downstream code keeps using the
    # typed ProductCreate object — we only touched the metadata dict in-place.
    data = type(data)(**data_dict)
    product = await product_repository.create(org_id, data)
    return ProductResponse(**product.model_dump())


@router.get("/taxonomies")
async def get_product_taxonomies(current_user: dict = Depends(get_verified_user)):
    """V4 — le tassonomie categoria per tipo, per i dropdown dei wizard.
    Fonte unica: models/retreat_taxonomy (la stessa che valida)."""
    from models.retreat_taxonomy import PRODUCT_TAXONOMIES, RETREAT_CATEGORIES
    return {"event_ticket": RETREAT_CATEGORIES, **PRODUCT_TAXONOMIES}


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    response: Response,
    current_user: dict = Depends(get_verified_user),
):
    product = await product_repository.find_by_id(product_id, current_user["organization_id"])
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    # Onda 16 Fase 6: surface deprecation for legacy booking products that
    # haven't been migrated yet, so integrations get a visible nudge.
    if getattr(product, "item_type", None) == "booking":
        response.headers["X-Deprecated"] = _DEPRECATED_BOOKING_HEADER
    return ProductResponse(**product.model_dump())


# ── Landing URL resolution (admin dashboards) ──────────────────────────────

# Response model for GET /products/{id}/landing-info. Mirrors the shape of
# `services.landing_resolver.resolve_landing_info()` so the router is a thin
# pass-through.
class LandingInfoResponse(BaseModel):
    has_landing: bool
    landing_url_path: Optional[str] = None       # e.g. "/r/store-slug/product-slug"
    landing_url_absolute: Optional[str] = None   # includes scheme + host
    store_id: Optional[str] = None
    store_slug: Optional[str] = None
    store_name: Optional[str] = None
    product_slug: Optional[str] = None
    item_type: Optional[str] = None
    blockers: List[str] = []


@router.get("/{product_id}/landing-info", response_model=LandingInfoResponse)
async def get_product_landing_info(
    product_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Admin-side resolution of the public landing URL for this product.

    Centralizes the logic the four dashboards (Reservation / Service /
    Physical / Digital) used to duplicate client-side. Emits the exact URL
    that `get_product_landing` / `get_public_catalog` will accept,
    considering `product.store_ids`, store visibility, publish state, and
    item_type → route-prefix mapping.

    When `has_landing=false` the payload includes human-readable
    `blockers` the UI can show as a tooltip on a disabled button.
    """
    import os
    from services.landing_resolver import resolve_landing_info

    org_id = current_user["organization_id"]
    product = await product_repository.find_by_id(product_id, org_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Resolver takes a plain dict to stay decoupled from the Pydantic model.
    info = await resolve_landing_info(
        org_id=org_id,
        product=product.model_dump(),
        # PUBLIC_APP_URL is the canonical post-purchase host; the resolver
        # concatenates it with the landing path. See services/url_builder.
        public_base_url=PUBLIC_APP_URL,
    )
    return LandingInfoResponse(**info)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    updates: ProductUpdate,
    response: Response,
    current_user: dict = Depends(get_verified_user),
):
    org_id = current_user["organization_id"]

    # V4 — gate store-first sulla transizione a pubblicato + categoria
    # dalla tassonomia (stessa logica del create; fonte unica).
    if getattr(updates, "is_published", None) is True:
        from services.store_guard import require_public_home
        await require_public_home(org_id)
        # RF4/B4 — un digitale senza file non si pubblica: il cliente
        # scoprirebbe l'errore solo al checkout (digital_file_missing).
        from database import products_collection as _pc_pub
        _prod_pub = await _pc_pub.find_one(
            {"id": product_id, "organization_id": org_id},
            {"_id": 0, "item_type": 1, "metadata": 1})
        if (_prod_pub or {}).get("item_type") == "digital" and not (
                (_prod_pub.get("metadata") or {}).get("download_filename")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "digital_file_missing",
                        "message": "Carica il file digitale prima di "
                                   "pubblicare il prodotto."})
        # S3 — IndexNow al publish (best-effort, no-op senza chiave)
        try:
            from services.indexnow import ping_urls_async
            from routers.public import _resolve_public_slug_for_org
            from routers.seo import _PRODUCT_PREFIX
            from database import products_collection as _pc_seo
            _prod = await _pc_seo.find_one(
                {"id": product_id, "organization_id": org_id},
                {"_id": 0, "slug": 1, "item_type": 1})
            _prefix = _PRODUCT_PREFIX.get((_prod or {}).get("item_type"))
            if _prod and _prod.get("slug") and _prefix:
                _org_slug = await _resolve_public_slug_for_org(org_id)
                if _org_slug:
                    import asyncio as _aio
                    _aio.create_task(ping_urls_async(
                        [f"/{_prefix}/{_org_slug}/{_prod['slug']}"]))
        except Exception:  # noqa: BLE001 — mai bloccare un publish
            pass
    if getattr(updates, "category", None):
        from database import products_collection as _pc
        from models.retreat_taxonomy import PRODUCT_TAXONOMIES, RETREAT_CATEGORIES
        _existing = await _pc.find_one(
            {"id": product_id, "organization_id": org_id},
            {"_id": 0, "item_type": 1},
        )
        _it = (_existing or {}).get("item_type")
        _tax = PRODUCT_TAXONOMIES.get(_it) or (
            RETREAT_CATEGORIES if _it == "event_ticket" else None)
        if _tax is not None and updates.category not in _tax:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Categoria non valida. Scegli una categoria dall'elenco.",
            )
    if getattr(updates, "translations", None) is not None:
        from services.manual_translations import sanitize_translations
        updates.translations = sanitize_translations(updates.translations)
    update_dict = updates.model_dump(exclude_unset=True)

    # Onda 16 Fase 6: soft-deprecate item_type=booking on updates too.
    if "item_type" in update_dict and _rewrite_deprecated_booking(update_dict):
        response.headers["X-Deprecated"] = _DEPRECATED_BOOKING_HEADER

    # P4: if the caller sent a metadata payload, normalize it against the
    # registry schema. We resolve the effective item_type from either the
    # update payload (if the caller is also changing the type in the same
    # request) or the existing product row so we always pick the right
    # schema.
    if "metadata" in update_dict:
        from models.product_types import validate_metadata
        effective_type = update_dict.get("item_type")
        if not effective_type:
            existing = await product_repository.find_by_id(product_id, org_id)
            effective_type = getattr(existing, "item_type", None) or "physical" if existing else "physical"
        update_dict["metadata"] = validate_metadata(effective_type, update_dict.get("metadata"))

    # Sprint 1 W1.5 — sanitize merchant-editable text fields on update.
    # Mirror del pattern create_product. Pinned by sentinel
    # TestSEC_E_8_5_MarkdownXSSSafe.
    from services.markdown_safe import sanitize_merchant_text
    if "description" in update_dict and update_dict["description"]:
        update_dict["description"] = sanitize_merchant_text(update_dict["description"])
    if "metadata" in update_dict and isinstance(update_dict.get("metadata"), dict):
        meta = update_dict["metadata"]
        if meta.get("long_description"):
            meta["long_description"] = sanitize_merchant_text(meta["long_description"])
            update_dict["metadata"] = meta

    # Onda 13 — if caller sends `slug` explicitly, normalize + dedupe.
    # If they send slug=None/empty, regenerate from the (new or existing) name.
    if "slug" in update_dict:
        from models.event_occurrence import slugify
        from services.product_slug import generate_product_slug
        raw = update_dict.get("slug")
        sanitized = slugify(raw) if raw else ""
        name_for_gen = update_dict.get("name")
        if not name_for_gen:
            existing = await product_repository.find_by_id(product_id, org_id)
            name_for_gen = getattr(existing, "name", None) or ""
        if not sanitized:
            update_dict["slug"] = await generate_product_slug(
                org_id, name_for_gen, exclude_id=product_id,
            )
        else:
            update_dict["slug"] = await generate_product_slug(
                org_id, sanitized, exclude_id=product_id,
            )

    product = await product_repository.update(product_id, org_id, update_dict)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductResponse(**product.model_dump())


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_product(
    product_id: str,
    current_user: dict = Depends(get_verified_user),
):
    ok = await product_repository.deactivate(product_id, current_user["organization_id"])
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


@router.post("/{product_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_product(
    product_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Onda 13 — create a clone of a product with status=draft.

    Copies:
      - Core fields (name, description, image, unit_price, item_type,
        price_mode, transaction_mode, unit, category, metadata, store_ids)
      - For services: service_options + availability_rules
      - New slug auto-generated with "(copia)" suffix so it doesn't collide

    Does NOT copy:
      - order history, sales_records, issued_tickets (those are per-sale)
      - is_published stays False (admin reviews the copy first)
      - sku cleared (unique constraint per org)
    """
    from models.product import ProductCreate
    from models.common import generate_id, utc_now
    from services.product_slug import generate_product_slug
    from database import (
        products_collection, service_options_collection,
        availability_rules_collection,
    )

    org_id = current_user["organization_id"]
    source = await products_collection.find_one(
        {"id": product_id, "organization_id": org_id, "is_active": True},
        {"_id": 0},
    )
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # v5.8 / Onda 9.L — Catalog quota gate also on duplicate (it creates a
    # new product row, same impact as POST /products on the catalog count).
    from services.module_access import enforce_count_quota
    current_count = await products_collection.count_documents({"organization_id": org_id})
    await enforce_count_quota(
        org_id, "product_catalog", "products",
        current_count=current_count,
        message_template=(
            "Hai raggiunto il limite di {limit} prodotti a catalogo del tuo piano. "
            "Aggiorna il piano per duplicare altri prodotti."
        ),
        hard_abuse_cap=10000,
    )

    new_name = f"{source.get('name', 'Prodotto')} (copia)"
    new_slug = await generate_product_slug(org_id, new_name)
    new_id = generate_id()
    now = utc_now()

    # Build the new product doc (mirror existing + overrides)
    copy = {k: v for k, v in source.items() if k not in ("id", "sku", "slug", "created_at", "updated_at", "is_published")}
    copy.update({
        "id": new_id,
        "organization_id": org_id,
        "name": new_name,
        "slug": new_slug,
        "sku": None,
        "is_published": False,
        "created_at": now,
        "updated_at": now,
    })
    await products_collection.insert_one(copy)

    # For services, also clone service_options + availability_rules
    if source.get("item_type") == "service":
        # Clone options
        option_docs = await service_options_collection.find(
            {"organization_id": org_id, "product_id": product_id},
            {"_id": 0},
        ).to_list(500)
        for opt in option_docs:
            clone = {k: v for k, v in opt.items() if k not in ("id", "product_id", "created_at", "updated_at")}
            clone.update({
                "id": generate_id(),
                "organization_id": org_id,
                "product_id": new_id,
                "created_at": now,
                "updated_at": now,
            })
            await service_options_collection.insert_one(clone)
        # Clone availability rules (per-product only; skip global rules)
        rule_docs = await availability_rules_collection.find(
            {"organization_id": org_id, "product_id": product_id},
            {"_id": 0},
        ).to_list(500)
        for r in rule_docs:
            clone = {k: v for k, v in r.items() if k not in ("id", "product_id", "created_at", "updated_at")}
            clone.update({
                "id": generate_id(),
                "organization_id": org_id,
                "product_id": new_id,
                "created_at": now,
                "updated_at": now,
            })
            await availability_rules_collection.insert_one(clone)

    # Re-read and return
    created = await products_collection.find_one({"id": new_id, "organization_id": org_id}, {"_id": 0})
    return created


@router.get("/{product_id}/bookings")
async def list_product_bookings(
    product_id: str,
    upcoming: int = Query(1, ge=0, le=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_verified_user),
):
    """Onda 14 Parte C — list bookings associated with a service product.

    Reads from `blocked_slots` for reserved/booking-type entries tied to
    this product, joins order info (number, status, customer) via
    `reference_id`, and returns a compact list sorted by date+time.

    Used by the ServiceDashboardPage to show 'Prossimi appuntamenti'.
    Query params:
      - upcoming (0|1): when 1 (default), only returns slots whose date
        is today or later.
      - limit: max results (default 10).
    """
    from database import blocked_slots_collection, orders_collection, customers_collection
    from datetime import datetime, timezone

    org_id = current_user["organization_id"]

    # Ensure the product belongs to the org (defense in depth)
    product = await product_repository.find_by_id(product_id, org_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    q = {
        "organization_id": org_id,
        "product_id": product_id,
        # booking slots are created with reason="booking" (or "rental" for
        # rentals); we accept both so the endpoint is useful across
        # scheduled types, with services being the primary consumer.
        "reason": {"$in": ["booking", "rental", "reserved"]},
    }
    if upcoming:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        q["date"] = {"$gte": today}

    cursor = blocked_slots_collection.find(q, {"_id": 0}).sort([("date", 1), ("start_time", 1)]).limit(limit)
    slots = await cursor.to_list(length=limit)

    # Resolve orders + customers in bulk for a cheap join
    order_ids = list({s.get("reference_id") for s in slots if s.get("reference_id")})
    orders_by_id = {}
    customers_by_id = {}
    if order_ids:
        order_cursor = orders_collection.find(
            {"id": {"$in": order_ids}, "organization_id": org_id},
            {"_id": 0, "id": 1, "order_number": 1, "status": 1, "customer_id": 1},
        )
        async for o in order_cursor:
            orders_by_id[o["id"]] = o

        customer_ids = list({o.get("customer_id") for o in orders_by_id.values() if o.get("customer_id")})
        if customer_ids:
            cust_cursor = customers_collection.find(
                {"id": {"$in": customer_ids}, "organization_id": org_id},
                {"_id": 0, "id": 1, "name": 1, "email": 1},
            )
            async for c in cust_cursor:
                customers_by_id[c["id"]] = c

    result = []
    for s in slots:
        order = orders_by_id.get(s.get("reference_id")) or {}
        customer = customers_by_id.get(order.get("customer_id")) or {}
        result.append({
            "date": s.get("date"),
            "start_time": s.get("start_time"),
            "end_time": s.get("end_time"),
            "reason": s.get("reason"),
            "note": s.get("note"),
            "order_id": order.get("id"),
            "order_number": order.get("order_number"),
            "order_status": order.get("status"),
            "customer_name": customer.get("name"),
            "customer_email": customer.get("email"),
        })

    return {"bookings": result, "total": len(result)}


@router.post("/{product_id}/image", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def upload_product_image(
    request: Request,
    product_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_verified_user),
):
    """Upload a product image. Replaces existing image. Max 5MB, jpg/png/webp."""
    org_id = current_user["organization_id"]
    product = await product_repository.find_by_id(product_id, org_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Formato non supportato. Usa: {', '.join(ALLOWED_EXTENSIONS)}")
    if file.content_type and file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail=f"Tipo file non supportato: {file.content_type}")

    # Validate size
    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Immagine troppo grande. Max 5MB.")

    # Delete old file if exists (cleanup)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    for old_ext in ALLOWED_EXTENSIONS:
        old_path = os.path.join(UPLOAD_DIR, f"{product_id}{old_ext}")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    # Save file
    filename = f"{product_id}{ext}"
    # R3 — adapter storage: S3 se configurato, filesystem locale in dev
    from services.object_storage import save_public_upload
    image_url = save_public_upload("products", filename, contents,
                                   content_type=f"image/{ext.lstrip('.')}")
    from database import products_collection
    from models.common import utc_now
    await products_collection.update_one(
        {"id": product_id, "organization_id": org_id},
        {"$set": {"image_url": image_url, "updated_at": utc_now()}},
    )

    return {"image_url": image_url, "size": len(contents)}


# ── Release 3 (Digital) — digital file upload ──────────────────────────────


@router.post("/{product_id}/digital-file", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def upload_digital_file(
    request: Request,
    product_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_verified_user),
):
    """Upload the payload of an item_type=digital product.

    The file is stored under a PRIVATE root (not served by StaticFiles) and
    will be delivered to customers only through the token-gated download
    endpoint created with the order's IssuedDownload. Product metadata is
    updated atomically with the snapshot (filename / size / mime) so the
    storefront can display a "download ready" state.

    Replaces any previously-uploaded payload for the same product.

    Errors:
      404 → product not found or not digital
      413 → file exceeds DIGITAL_MAX_UPLOAD_BYTES (default 100 MB)
      400 → upload stream malformed (best-effort surface)
    """
    org_id = current_user["organization_id"]
    product = await product_repository.find_by_id(product_id, org_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if getattr(product, "item_type", None) != "digital":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endpoint riservato ai prodotti di tipo digital",
        )

    from services import digital_storage
    try:
        snapshot = await digital_storage.save_digital_file(org_id, product_id, file)
    except ValueError as exc:
        # Size limit and sanitization errors — surface as 413/400.
        msg = str(exc)
        code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE if "massima" in msg else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=msg)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nel caricamento del file: {exc}",
        )

    # Merge snapshot into product.metadata without wiping unrelated keys.
    from database import products_collection
    from models.common import utc_now
    existing_meta = dict(getattr(product, "metadata", None) or {})
    existing_meta.update({
        "download_filename": snapshot["filename"],
        "download_size_bytes": snapshot["size_bytes"],
        "download_mime_type": snapshot["mime_type"],
    })
    await products_collection.update_one(
        {"id": product_id, "organization_id": org_id},
        {"$set": {"metadata": existing_meta, "updated_at": utc_now()}},
    )

    return {
        "filename": snapshot["filename"],
        "size_bytes": snapshot["size_bytes"],
        "mime_type": snapshot["mime_type"],
    }


# ── CG3 — mini-stats vendite per prodotto (tutte le anime) ──────────────────

_SALES_STATS_CACHE: dict = {}
_SALES_STATS_TTL = 60.0


@router.get("/{product_id}/sales-stats")
async def product_sales_stats(
    product_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """I numeri di UN prodotto, qualunque anima (INSIGHTS/CG3).

    Base comune (ordini confermati/completati, 12 mesi):
      units_12m / revenue_12m / orders_12m
    Extra per anima:
      service  → upcoming_sessions (prossime 5 sessioni con contatto:
                 il promemoria appuntamento è a un click)
      digital  → deliveries_12m (consegne emesse)
      course   → enrollments {active, expired}
    Realtà dei dati: niente stime — solo conteggi dalle collection
    di fulfillment già esistenti. Cache 60s per (org, prodotto).
    """
    import time as _time
    from datetime import timedelta as _td
    from models.common import utc_now as _now
    from database import (
        products_collection, orders_collection,
        issued_bookings_collection, issued_downloads_collection,
        issued_course_accesses_collection,
    )

    org_id = current_user["organization_id"]
    ck = f"{org_id}:{product_id}"
    hit = _SALES_STATS_CACHE.get(ck)
    mono = _time.monotonic()
    if hit and (mono - hit[0]) < _SALES_STATS_TTL:
        return hit[1]

    product = await products_collection.find_one(
        {"id": product_id, "organization_id": org_id},
        {"_id": 0, "id": 1, "item_type": 1, "metadata": 1})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Product not found")

    now = _now()
    cutoff_day = (now - _td(days=365)).isoformat()[:10]
    units = revenue = n_orders = 0
    async for g in orders_collection.aggregate([
        {"$match": {"organization_id": org_id,
                    "status": {"$in": ["confirmed", "completed"]},
                    "order_date": {"$gte": cutoff_day},
                    "items.product_id": product_id}},
        {"$unwind": "$items"},
        {"$match": {"items.product_id": product_id}},
        {"$group": {"_id": None,
                    "units": {"$sum": "$items.quantity"},
                    "revenue": {"$sum": "$items.line_total"},
                    "orders": {"$sum": 1}}},
    ]):
        units = g.get("units") or 0
        revenue = round(g.get("revenue") or 0, 2)
        n_orders = g.get("orders") or 0

    payload = {
        "item_type": product.get("item_type") or "physical",
        "units_12m": units,
        "revenue_12m": revenue,
        "orders_12m": n_orders,
    }

    itype = payload["item_type"]
    if itype == "service":
        today = now.isoformat()[:10]
        sessions = await issued_bookings_collection.find(
            {"organization_id": org_id, "product_id": product_id,
             "booking_date": {"$gte": today},
             "status": {"$nin": ["cancelled"]}},
            {"_id": 0, "booking_date": 1, "booking_start_time": 1,
             "holder_name": 1, "holder_email": 1, "holder_phone": 1},
        ).sort([("booking_date", 1), ("booking_start_time", 1)]).to_list(5)
        payload["upcoming_sessions"] = sessions
        payload["upcoming_count"] = await issued_bookings_collection.count_documents(
            {"organization_id": org_id, "product_id": product_id,
             "booking_date": {"$gte": today},
             "status": {"$nin": ["cancelled"]}})
    elif itype == "digital":
        payload["deliveries_12m"] = await issued_downloads_collection.count_documents(
            {"organization_id": org_id, "product_id": product_id,
             "status": {"$ne": "cancelled"}})
    elif itype == "course":
        course_id = (product.get("metadata") or {}).get("course_id")
        if course_id:
            now_dt = now
            active = expired = 0
            async for a in issued_course_accesses_collection.find(
                    {"organization_id": org_id, "course_id": course_id},
                    {"_id": 0, "revoked_at": 1, "expires_at": 1}).limit(5000):
                if a.get("revoked_at"):
                    continue
                exp = a.get("expires_at")
                if exp and str(exp) <= now_dt.isoformat():
                    expired += 1
                else:
                    active += 1
            payload["enrollments"] = {"active": active, "expired": expired}

    _SALES_STATS_CACHE[ck] = (mono, payload)
    return payload
