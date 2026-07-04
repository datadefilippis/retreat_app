"""
Event Occurrences Router — CRUD for dated event_ticket instances.

Scoped to products with item_type="event_ticket".
All endpoints require authentication (org-scoped).

Endpoints (occurrence):
  GET    /event-occurrences?product_id=...  — list occurrences
  POST   /event-occurrences                 — create occurrence
  PATCH  /event-occurrences/{id}            — update occurrence

Endpoints (E1 — tiers nested under occurrence):
  GET    /event-occurrences/{id}/tiers              — list tiers
  POST   /event-occurrences/{id}/tiers              — create tier
  PATCH  /event-occurrences/{id}/tiers/{tier_id}    — update tier
  DELETE /event-occurrences/{id}/tiers/{tier_id}    — soft/hard delete tier
"""

import logging
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status, Request, UploadFile, File
from routers.auth import limiter
from pydantic import BaseModel, ConfigDict, Field
from auth import get_current_user, get_verified_user, get_verified_user

COVER_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "occurrences")
COVER_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
COVER_ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
COVER_MAX_SIZE = 5 * 1024 * 1024  # 5 MB
from models.event_occurrence import (
    EventOccurrenceCreate, EventOccurrenceUpdate, EventOccurrence,
    OCCURRENCE_STATUSES,
    generate_occurrence_slug, slugify,
)
from models.event_ticket_tier import (
    EventTicketTier, EventTicketTierCreate, EventTicketTierUpdate,
)
from models.common import utc_now
from database import (
    event_occurrences_collection,
    event_ticket_tiers_collection,
    products_collection,
    organizations_collection,
    stores_collection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/event-occurrences", tags=["Event Occurrences"])


# ── G2: Event Wizard — atomic product + occurrence + tiers create ──────────


class WizardProductPayload(BaseModel):
    """Product fields the wizard collects on the "Cosa offri" tab."""
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    image_url: Optional[str] = Field(default=None, max_length=500)
    unit_price: Optional[float] = Field(default=None, ge=0)
    price_mode: str = "fixed"
    transaction_mode: str = "direct"
    is_published: bool = False
    store_ids: List[str] = Field(default_factory=list)  # F4: assign to specific stores
    # F1/F2/F4 — the wizard collects attendee flags, custom fields and T&C override
    # under product.metadata. Prior to this field the Pydantic model silently
    # dropped them (extra="ignore"), so they only persisted if the merchant
    # re-saved from the dashboard PATCH path. Declaring it here lets the
    # single POST /wizard round-trip carry everything.
    metadata: Optional[Dict[str, Any]] = None


class WizardOccurrencePayload(BaseModel):
    """Occurrence fields from the "Quando e dove" tab."""
    model_config = ConfigDict(extra="ignore")
    start_at: str = Field(min_length=16, max_length=25)
    end_at: Optional[str] = Field(default=None, max_length=25)
    capacity: Optional[int] = Field(default=None, ge=1)
    status: str = "draft"  # draft | published
    location: Optional[str] = Field(default=None, max_length=255)
    # E2 structured
    venue_name: Optional[str] = Field(default=None, max_length=150)
    address: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default=None, max_length=2)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    cover_image_url: Optional[str] = Field(default=None, max_length=500)
    long_description: Optional[str] = Field(default=None, max_length=5000)


class WizardTierPayload(BaseModel):
    """Single tier row from the "Biglietti" tab."""
    model_config = ConfigDict(extra="ignore")
    label: str = Field(min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    price: float = Field(ge=0)
    capacity: Optional[int] = Field(default=None, ge=1)
    sort_order: int = 0


class EventWizardPayload(BaseModel):
    """Atomic create body for the Event Wizard (G2)."""
    model_config = ConfigDict(extra="ignore")
    product: WizardProductPayload
    occurrence: WizardOccurrencePayload
    tiers: List[WizardTierPayload] = Field(default_factory=list)


@router.post("/wizard", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_event_wizard(
    request: Request,
    body: EventWizardPayload,
    current_user: dict = Depends(get_verified_user),
):
    """G2 — one-shot atomic create for a brand-new event.

    Creates in sequence:
      1. the Product with item_type=event_ticket
      2. the EventOccurrence linked to it (auto-generates slug)
      3. the EventTicketTiers (0..N) linked to the occurrence

    On any failure the earlier inserts are rolled back so the org
    never ends up with a half-built event (orphan product without
    occurrence, or occurrence without product). Returns the trio of
    ids so the frontend can navigate straight to /events/:occurrence_id.

    Keeps the existing three CRUD endpoints untouched — this is just a
    coordinated wrapper around them.
    """
    from database import (
        event_occurrences_collection,
        event_ticket_tiers_collection,
        products_collection,
    )
    from models.product import ProductCreate, Product
    from models.event_occurrence import EventOccurrence
    from models.event_ticket_tier import EventTicketTier

    org_id = current_user["organization_id"]

    # Validate price/transaction mode combo early — same rule as
    # Product model. A direct event with inquiry price_mode makes no
    # sense (there's no price to charge).
    if body.product.transaction_mode == "direct" and body.product.price_mode == "inquiry":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modalità diretta non compatibile con prezzo su richiesta.",
        )

    # Fase 2 (retreat) — se il wizard invia un piano di pagamento, DEVE
    # essere valido: un piano malformato in metadata produrrebbe ordini
    # col fallback silenzioso a pagamento unico (sorpresa per l'operatore).
    # Meglio 422 esplicito alla creazione che sorpresa all'incasso.
    plan_raw = (body.product.metadata or {}).get("payment_plan")
    if plan_raw is not None:
        from models.payment_plan import PaymentPlan
        try:
            validated_plan = PaymentPlan(**plan_raw)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Piano di pagamento non valido: {exc}",
            )
        # Persistiamo la forma normalizzata (default espliciti inclusi).
        body.product.metadata["payment_plan"] = validated_plan.model_dump(mode="json")

    # v5.8 / Onda 9.L — This wrapper creates a Product as part of an event
    # occurrence wizard flow; same catalog quota gate as POST /products.
    from services.module_access import enforce_count_quota
    current_count = await products_collection.count_documents({"organization_id": org_id})
    await enforce_count_quota(
        org_id, "product_catalog", "products",
        current_count=current_count,
        message_template=(
            "Hai raggiunto il limite di {limit} prodotti a catalogo del tuo piano. "
            "Aggiorna il piano per creare altri eventi."
        ),
        hard_abuse_cap=10000,
    )

    product_id: Optional[str] = None
    occurrence_id: Optional[str] = None
    tier_ids: List[str] = []

    try:
        # ── 1. Create product ──────────────────────────────────────────
        product_model = Product(
            organization_id=org_id,
            item_type="event_ticket",
            **body.product.model_dump(),
        )
        prod_doc = product_model.model_dump(mode="json")
        await products_collection.insert_one(prod_doc)
        product_id = product_model.id

        # ── 2. Create occurrence (auto-slug from product name + date) ──
        occ_data = body.occurrence.model_dump()
        occ_model = EventOccurrence(
            organization_id=org_id,
            product_id=product_id,
            **occ_data,
        )
        occ_doc = occ_model.model_dump(mode="json")
        occ_doc["product_name"] = body.product.name
        # Auto-generate slug (same logic as the standalone create endpoint)
        occ_doc["slug"] = await generate_occurrence_slug(
            org_id=org_id,
            product_name=body.product.name,
            start_at=occ_doc.get("start_at"),
        )
        await event_occurrences_collection.insert_one(occ_doc)
        occurrence_id = occ_model.id

        # ── 3. Create tiers ────────────────────────────────────────────
        for t in body.tiers:
            tier_model = EventTicketTier(
                organization_id=org_id,
                occurrence_id=occurrence_id,
                **t.model_dump(),
            )
            await event_ticket_tiers_collection.insert_one(
                tier_model.model_dump(mode="json")
            )
            tier_ids.append(tier_model.id)

        logger.info(
            "event_wizard: created event product=%s occurrence=%s tiers=%d org=%s",
            product_id, occurrence_id, len(tier_ids), org_id,
        )
        return {
            "product_id": product_id,
            "occurrence_id": occurrence_id,
            "tier_ids": tier_ids,
            "slug": occ_doc["slug"],
        }
    except Exception as exc:
        # Roll back anything we managed to insert before the failure.
        logger.warning("event_wizard: create failed, rolling back: %s", exc)
        if tier_ids:
            try:
                await event_ticket_tiers_collection.delete_many({"id": {"$in": tier_ids}})
            except Exception:
                pass
        if occurrence_id:
            try:
                await event_occurrences_collection.delete_one({"id": occurrence_id})
            except Exception:
                pass
        if product_id:
            try:
                await products_collection.delete_one({"id": product_id})
            except Exception:
                pass

        # Re-raise as a clean 400 with the original detail
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Errore nella creazione dell'evento: {str(exc)[:200]}",
        )


@router.get("/admin/list")
async def list_events_admin(
    status_filter: Optional[str] = Query(None, alias="status", description="draft|published|closed|cancelled"),
    when: Optional[str] = Query(None, description="upcoming|past|all (default upcoming)"),
    q: Optional[str] = Query(None, description="search term (product name contains)"),
    archived: Optional[str] = Query(None, description="hide|only|all (default hide)"),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_verified_user),
):
    """G1 admin Eventi home — one row per occurrence with joined product
    data + light stats. Powers /events list page.

    Query params:
      status      draft|published|closed|cancelled (default: all)
      when        upcoming|past|all (default: upcoming). Uses start_at
                  compared to now.
      q           case-insensitive contains on product name (NOT on
                  occurrence.notes — we match what the admin sees as
                  the event name)
      limit       default 100, max 500

    Response shape: list of dicts with occurrence fields + product_name /
    product_id / product_image_url + capacity / reserved_seats /
    tier_count + status.

    Keeps reads cheap: no per-occurrence aggregation pipelines. The
    tier count is a batched `count_documents` after the occurrence
    scan so even an org with hundreds of events stays under ~200ms.
    Detailed analytics live in G3/G5 endpoints.
    """
    from database import (
        event_occurrences_collection,
        event_ticket_tiers_collection,
        products_collection,
    )
    from datetime import datetime as _dt

    org_id = current_user["organization_id"]

    # ── Base match ─────────────────────────────────────────────────
    match: dict = {"organization_id": org_id}
    if status_filter:
        if status_filter not in OCCURRENCE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status must be one of: {', '.join(OCCURRENCE_STATUSES)}",
            )
        match["status"] = status_filter

    # Upcoming vs past uses ISO lexicographic comparison on start_at,
    # which is safe because we always store "YYYY-MM-DDTHH:MM:SS".
    now_iso = _dt.utcnow().isoformat()
    when = (when or "upcoming").lower()
    if when == "upcoming":
        match["start_at"] = {"$gte": now_iso}
    elif when == "past":
        match["start_at"] = {"$lt": now_iso}
    # "all" — no date filter

    # G6: archived filter. Default hides archived rows so the listing
    # stays focused on the current roster; "only" shows the archive;
    # "all" shows everything. `is_archived` is treated as False when
    # missing (pre-G6 rows have no flag).
    archived = (archived or "hide").lower()
    if archived == "hide":
        match["$or"] = [
            {"is_archived": {"$exists": False}},
            {"is_archived": False},
        ]
    elif archived == "only":
        match["is_archived"] = True
    # "all" — no filter

    # ── Search filter needs a product lookup ───────────────────────
    if q:
        q_trim = q.strip()
        if q_trim:
            # Two-step: find matching product ids first, then restrict
            # occurrence query to those product_ids. Avoids a server-side
            # $lookup (keeps the list cheap on small-medium orgs).
            prod_ids = [
                p["id"] async for p in products_collection.find(
                    {
                        "organization_id": org_id,
                        "item_type": "event_ticket",
                        "is_active": True,
                        "name": {"$regex": q_trim, "$options": "i"},
                    },
                    {"_id": 0, "id": 1},
                )
            ]
            if not prod_ids:
                return {"events": [], "total": 0}
            match["product_id"] = {"$in": prod_ids}

    # ── Occurrence fetch ───────────────────────────────────────────
    sort_order = 1 if when == "upcoming" else -1
    cursor = event_occurrences_collection.find(match, {"_id": 0}) \
        .sort("start_at", sort_order).limit(limit)
    occurrences = await cursor.to_list(limit)
    if not occurrences:
        return {"events": [], "total": 0}

    # ── Batched product enrichment ─────────────────────────────────
    product_ids = list({o.get("product_id") for o in occurrences if o.get("product_id")})
    products = {
        p["id"]: p async for p in products_collection.find(
            {"id": {"$in": product_ids}, "organization_id": org_id},
            {"_id": 0, "id": 1, "name": 1, "image_url": 1, "is_published": 1},
        )
    }

    # ── Batched tier count per occurrence ──────────────────────────
    occ_ids = [o["id"] for o in occurrences]
    tier_counts: dict[str, int] = {}
    async for doc in event_ticket_tiers_collection.aggregate([
        {"$match": {
            "organization_id": org_id,
            "occurrence_id": {"$in": occ_ids},
            "is_active": True,
        }},
        {"$group": {"_id": "$occurrence_id", "n": {"$sum": 1}}},
    ]):
        tier_counts[doc["_id"]] = int(doc.get("n") or 0)

    # ── Shape response ─────────────────────────────────────────────
    out = []
    for occ in occurrences:
        pid = occ.get("product_id")
        prod = products.get(pid) or {}
        out.append({
            "id": occ["id"],
            "slug": occ.get("slug"),
            "status": occ.get("status", "draft"),
            "start_at": occ.get("start_at"),
            "end_at": occ.get("end_at"),
            "venue_name": occ.get("venue_name"),
            "city": occ.get("city"),
            "location": occ.get("location"),
            "capacity": occ.get("capacity"),
            "reserved_seats": int(occ.get("reserved_seats") or 0),
            "cover_image_url": occ.get("cover_image_url"),
            "product_id": pid,
            "product_name": prod.get("name"),
            "product_image_url": prod.get("image_url"),
            "product_is_published": prod.get("is_published", False),
            "tier_count": tier_counts.get(occ["id"], 0),
            "is_archived": bool(occ.get("is_archived", False)),
        })

    return {"events": out, "total": len(out)}


@router.post("/{occurrence_id}/duplicate")
@limiter.limit("10/minute")
async def duplicate_occurrence_data(
    request: Request,
    occurrence_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """G6 — return a wizard-ready payload derived from an existing event.

    Does NOT create anything itself. Returns the structured {product,
    occurrence, tiers} shape that EventWizard's POST /wizard endpoint
    expects. The frontend hands this to the wizard pre-fill, the user
    edits (typically just the date), and submits to create the real
    new event.

    Business case: Michele runs a bimonthly event — he wants to clone
    the last edition (venue / tiers / description identical, new date)
    without typing everything again.

    Returns 404 for cross-org / unknown occurrence ids.
    """
    from database import (
        event_occurrences_collection,
        event_ticket_tiers_collection,
        products_collection,
    )

    org_id = current_user["organization_id"]
    occ = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not occ:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occurrence not found")

    product = await products_collection.find_one(
        {"id": occ.get("product_id"), "organization_id": org_id},
        {"_id": 0},
    ) or {}

    tiers_cursor = event_ticket_tiers_collection.find(
        {"organization_id": org_id, "occurrence_id": occurrence_id, "is_active": True},
        {"_id": 0, "label": 1, "description": 1, "price": 1, "capacity": 1, "sort_order": 1},
    ).sort("sort_order", 1)
    tiers = await tiers_cursor.to_list(100)

    # Scrub runtime state so the caller doesn't accidentally copy stale
    # IDs / counters / slugs into the fresh event.
    product_clean = {
        "name": product.get("name") or "",
        "description": product.get("description"),
        "image_url": product.get("image_url"),
        "unit_price": product.get("unit_price"),
        "price_mode": product.get("price_mode", "fixed"),
        "transaction_mode": product.get("transaction_mode", "direct"),
        "is_published": False,  # safer default: duplicated event starts unpublished
    }
    occurrence_clean = {
        # start_at intentionally blanked — merchant must pick a new date
        "start_at": "",
        "end_at": "",
        "capacity": occ.get("capacity"),
        "status": "draft",
        "location": occ.get("location"),
        "venue_name": occ.get("venue_name"),
        "address": occ.get("address"),
        "city": occ.get("city"),
        "postal_code": occ.get("postal_code"),
        "country": occ.get("country"),
        "latitude": occ.get("latitude"),
        "longitude": occ.get("longitude"),
        "cover_image_url": occ.get("cover_image_url"),
        "long_description": occ.get("long_description"),
    }
    tiers_clean = [
        {
            "label": t.get("label") or "",
            "description": t.get("description"),
            "price": t.get("price") or 0,
            "capacity": t.get("capacity"),
            "sort_order": t.get("sort_order") or 0,
        }
        for t in tiers
    ]
    return {
        "product": product_clean,
        "occurrence": occurrence_clean,
        "tiers": tiers_clean,
        "source_occurrence_id": occurrence_id,
        "source_event_name": product.get("name"),
    }


async def _validate_event_product(product_id: str, org_id: str) -> dict:
    """Validate that the product exists, is active, and is an event_ticket."""
    product = await products_collection.find_one(
        {"id": product_id, "organization_id": org_id, "is_active": True},
        {"_id": 0, "id": 1, "name": 1, "item_type": 1},
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.get("item_type") != "event_ticket":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Occurrences can only be created for event_ticket products",
        )
    return product


@router.get("/{occurrence_id}/analytics")
async def get_occurrence_analytics(
    occurrence_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """G3 — revenue + per-tier breakdown + sales timeline for one event.

    Returns everything the enriched dashboard needs in one fetch:

      revenue_total          sum of items.line_total for non-cancelled
                             orders whose items point to this occurrence
      tickets_sold_total     sum of items.quantity (same filter)
      revenue_by_tier        [{tier_id, tier_label, revenue,
                              tickets_sold, price}]  — one row per
                             distinct tier touched by an order; mono-
                             tier events emit one row with tier_id=None
      sales_timeline         [{date: 'YYYY-MM-DD', tickets_sold,
                              revenue}]  — one row per day with at
                             least one order, sorted asc, last 30 days
      currency               org currency (falls back to EUR)

    Org-scoped through the aggregation match stage. 404 when the
    occurrence doesn't belong to the caller's org.
    """
    from database import (
        event_occurrences_collection,
        event_ticket_tiers_collection,
        orders_collection,
        organizations_collection,
    )
    from datetime import datetime as _dt, timedelta as _td

    org_id = current_user["organization_id"]

    # Ownership check — 404 if not ours
    occ = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"_id": 0, "id": 1},
    )
    if not occ:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occurrence not found")

    # Revenue totals and per-tier breakdown via ONE aggregation
    pipeline_revenue = [
        {"$match": {
            "organization_id": org_id,
            "status": {"$ne": "cancelled"},
            "items.occurrence_id": occurrence_id,
        }},
        {"$unwind": "$items"},
        {"$match": {"items.occurrence_id": occurrence_id}},
        {"$group": {
            "_id": {
                "tier_id": {"$ifNull": ["$items.ticket_tier_id", None]},
                "tier_label": {"$ifNull": ["$items.ticket_tier_label", None]},
            },
            "revenue": {"$sum": "$items.line_total"},
            "tickets_sold": {"$sum": "$items.quantity"},
            "unit_prices": {"$addToSet": "$items.unit_price"},
        }},
    ]
    by_tier = []
    total_rev = 0.0
    total_qty = 0
    async for row in orders_collection.aggregate(pipeline_revenue):
        rev = float(row.get("revenue") or 0)
        qty = int(row.get("tickets_sold") or 0)
        total_rev += rev
        total_qty += qty
        prices = [p for p in (row.get("unit_prices") or []) if p is not None]
        # If all units shared one price, surface it; otherwise None
        single_price = prices[0] if len(set(prices)) == 1 else None
        by_tier.append({
            "tier_id": row["_id"].get("tier_id"),
            "tier_label": row["_id"].get("tier_label"),
            "revenue": round(rev, 2),
            "tickets_sold": qty,
            "price": single_price,
        })
    # Stable sort: highest revenue first
    by_tier.sort(key=lambda r: -r["revenue"])

    # Enrich tier_label when the order line didn't snapshot it
    # (pre-E1 rows). Fetch tier names in one batch.
    tier_ids_missing_label = [r["tier_id"] for r in by_tier
                              if r["tier_id"] and not r["tier_label"]]
    if tier_ids_missing_label:
        name_by_id = {}
        async for t in event_ticket_tiers_collection.find(
            {"id": {"$in": tier_ids_missing_label}, "organization_id": org_id},
            {"_id": 0, "id": 1, "label": 1},
        ):
            name_by_id[t["id"]] = t.get("label")
        for r in by_tier:
            if not r["tier_label"] and r["tier_id"] in name_by_id:
                r["tier_label"] = name_by_id[r["tier_id"]]

    # Sales timeline — last 30 days, one row per day with activity
    cutoff = _dt.utcnow() - _td(days=30)
    cutoff_iso = cutoff.date().isoformat()
    pipeline_timeline = [
        {"$match": {
            "organization_id": org_id,
            "status": {"$ne": "cancelled"},
            "items.occurrence_id": occurrence_id,
        }},
        {"$unwind": "$items"},
        {"$match": {"items.occurrence_id": occurrence_id}},
        {"$addFields": {
            "day": {"$substr": [
                {"$ifNull": ["$order_date", {"$dateToString": {
                    "format": "%Y-%m-%d", "date": "$created_at",
                }}]}, 0, 10,
            ]},
        }},
        {"$match": {"day": {"$gte": cutoff_iso}}},
        {"$group": {
            "_id": "$day",
            "tickets_sold": {"$sum": "$items.quantity"},
            "revenue": {"$sum": "$items.line_total"},
        }},
        {"$sort": {"_id": 1}},
    ]
    timeline = []
    async for row in orders_collection.aggregate(pipeline_timeline):
        timeline.append({
            "date": row["_id"],
            "tickets_sold": int(row.get("tickets_sold") or 0),
            "revenue": round(float(row.get("revenue") or 0), 2),
        })

    # Currency from org
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "currency": 1},
    ) or {}

    # ── G5: attendance rate + past-event comparison ────────────────
    from database import issued_tickets_collection as _tickets

    # Attendance rate = checked_in / (valid + checked_in) — voided
    # excluded from the denominator because those tickets are no
    # longer "expected at the door".
    attendance_pipeline = [
        {"$match": {"organization_id": org_id, "occurrence_id": occurrence_id}},
        {"$group": {"_id": "$status", "n": {"$sum": 1}}},
    ]
    ci_count = 0
    active_count = 0
    async for row in _tickets.aggregate(attendance_pipeline):
        k = row.get("_id")
        n = int(row.get("n") or 0)
        if k == "checked_in":
            ci_count += n
            active_count += n
        elif k == "valid":
            active_count += n
        # voided -> not counted in denominator
    attendance_rate = (
        round((ci_count / active_count) * 100, 1)
        if active_count > 0 else None
    )

    # Past comparison — up to 5 previous occurrences of the SAME
    # product (past = start_at < this occurrence's start_at, plus
    # status != cancelled so we compare against events that actually
    # happened). One aggregation per past event is cheap; we limit
    # to 5 so the endpoint stays under ~200ms even for a merchant
    # with years of history.
    this_occ_full = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"_id": 0, "product_id": 1, "start_at": 1},
    ) or {}
    past_comparison: list = []
    if this_occ_full.get("product_id") and this_occ_full.get("start_at"):
        past_cursor = event_occurrences_collection.find(
            {
                "organization_id": org_id,
                "product_id": this_occ_full["product_id"],
                "start_at": {"$lt": this_occ_full["start_at"]},
                "status": {"$ne": "cancelled"},
                "id": {"$ne": occurrence_id},
            },
            {"_id": 0, "id": 1, "start_at": 1, "capacity": 1},
        ).sort("start_at", -1).limit(5)
        past_occs = await past_cursor.to_list(5)

        for po in past_occs:
            # revenue + tickets for this past occurrence
            rev_pipe = [
                {"$match": {
                    "organization_id": org_id,
                    "status": {"$ne": "cancelled"},
                    "items.occurrence_id": po["id"],
                }},
                {"$unwind": "$items"},
                {"$match": {"items.occurrence_id": po["id"]}},
                {"$group": {
                    "_id": None,
                    "revenue": {"$sum": "$items.line_total"},
                    "qty": {"$sum": "$items.quantity"},
                }},
            ]
            prev_rev = 0.0
            prev_qty = 0
            async for r in orders_collection.aggregate(rev_pipe):
                prev_rev = float(r.get("revenue") or 0)
                prev_qty = int(r.get("qty") or 0)

            # attendance on that past occurrence
            prev_ci = 0
            prev_active = 0
            async for r in _tickets.aggregate([
                {"$match": {"organization_id": org_id, "occurrence_id": po["id"]}},
                {"$group": {"_id": "$status", "n": {"$sum": 1}}},
            ]):
                k = r.get("_id")
                n = int(r.get("n") or 0)
                if k == "checked_in":
                    prev_ci += n
                    prev_active += n
                elif k == "valid":
                    prev_active += n
            prev_rate = (
                round((prev_ci / prev_active) * 100, 1)
                if prev_active > 0 else None
            )

            past_comparison.append({
                "occurrence_id": po["id"],
                "start_at": po.get("start_at"),
                "capacity": po.get("capacity"),
                "revenue": round(prev_rev, 2),
                "tickets_sold": prev_qty,
                "attendance_rate": prev_rate,
            })

    return {
        "occurrence_id": occurrence_id,
        "revenue_total": round(total_rev, 2),
        "tickets_sold_total": total_qty,
        "revenue_by_tier": by_tier,
        "sales_timeline": timeline,
        "currency": org.get("currency") or "EUR",
        # G5 additions
        "attendance_rate": attendance_rate,
        "checked_in_count": ci_count,
        "active_ticket_count": active_count,
        "past_comparison": past_comparison,
    }


@router.get("/{occurrence_id}/tickets-csv")
async def export_tickets_csv(
    occurrence_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """G3 — CSV attendance export. One row per issued ticket ordered by
    seat_index. Columns: code, holder_name, holder_email, tier_label,
    status, seat_index, seat_count, checked_in_at, order_id, created_at.

    Returns a StreamingResponse text/csv with Content-Disposition so
    the browser saves as attendance-{occurrence_id}.csv.
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse

    from database import (
        event_occurrences_collection,
        issued_tickets_collection,
    )

    org_id = current_user["organization_id"]
    occ = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"_id": 0, "id": 1, "product_id": 1},
    )
    if not occ:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occurrence not found")

    # F2 Onda 9 — load the product's custom field config so the CSV
    # includes one extra column per `attendee_fields` entry, ordered by
    # sort_order. Falls back to [] when the product has no custom fields
    # (legacy / F1 events).
    prod = await products_collection.find_one(
        {"id": occ.get("product_id"), "organization_id": org_id},
        {"_id": 0, "metadata": 1},
    ) or {}
    attendee_fields_cfg = sorted(
        (prod.get("metadata") or {}).get("attendee_fields") or [],
        key=lambda f: (f.get("sort_order") or 0, f.get("id") or ""),
    )
    custom_columns = [(f.get("id") or "", f.get("label") or f.get("id") or "")
                      for f in attendee_fields_cfg if f.get("id")]

    # Build CSV in memory (attendance lists rarely exceed a few hundred rows)
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    header = [
        "code", "holder_name", "holder_email", "holder_phone", "tier_label", "status",
        "seat_index", "seat_count", "checked_in_at", "order_id", "created_at",
    ]
    header.extend(col_label for (_, col_label) in custom_columns)
    writer.writerow(header)
    cursor = issued_tickets_collection.find(
        {"organization_id": org_id, "occurrence_id": occurrence_id},
        {"_id": 0},
    ).sort("seat_index", 1)
    n = 0
    async for t in cursor:
        row = [
            t.get("code", ""),
            t.get("holder_name", "") or "",
            t.get("holder_email", "") or "",
            t.get("holder_phone", "") or "",
            t.get("tier_label", "") or "",
            t.get("status", "") or "",
            t.get("seat_index", ""),
            t.get("seat_count", ""),
            t.get("checked_in_at", "") or "",
            t.get("order_id", "") or "",
            t.get("created_at", "") or "",
        ]
        cf = t.get("attendee_fields_data") or {}
        for field_id, _ in custom_columns:
            v = cf.get(field_id)
            row.append("" if v is None else str(v))
        writer.writerow(row)
        n += 1
    payload = buf.getvalue()
    buf.close()

    logger.info("event_occurrences: CSV export occ=%s org=%s rows=%d", occurrence_id, org_id, n)
    return StreamingResponse(
        iter([payload.encode("utf-8")]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="attendance-{occurrence_id}.csv"',
        },
    )


@router.get("/{occurrence_id}")
async def get_occurrence(
    occurrence_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Fetch a single occurrence by id. Powers the E6 event dashboard
    so the frontend can arrive by URL (/events/:id) without already
    knowing the parent product_id. Cross-org isolation via the filter
    on organization_id — 404 is returned for any occurrence not owned
    by the caller's org.
    """
    org_id = current_user["organization_id"]
    doc = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occurrence not found")

    # Denormalize product_name + product_id so the dashboard header
    # can render the event title without a second round-trip.
    prod = await products_collection.find_one(
        {"id": doc.get("product_id"), "organization_id": org_id},
        {"_id": 0, "name": 1, "image_url": 1, "description": 1,
         "is_published": 1, "is_active": 1, "store_ids": 1,
         "unit_price": 1, "transaction_mode": 1,
         "metadata": 1},  # E1 + F1: needed for full product edit + attendee policy
    ) or {}
    doc["product_name"] = prod.get("name")
    doc["product_image_url"] = prod.get("image_url")
    doc["product_description"] = prod.get("description")
    doc["product_is_published"] = prod.get("is_published", False)
    doc["product_is_active"] = prod.get("is_active", True)
    doc["product_store_ids"] = prod.get("store_ids") or []
    doc["product_metadata"] = prod.get("metadata") or {}
    doc["product_unit_price"] = prod.get("unit_price")          # E1
    doc["product_transaction_mode"] = prod.get("transaction_mode", "direct")  # E1

    # Resolve the slug that makes the landing URL /e/:slug/:event-slug work.
    # Priority: published store slug (multi-store) → org.public_slug (legacy).
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "public_slug": 1},
    ) or {}
    doc["org_public_slug"] = org.get("public_slug")

    # Multi-store resolution via the shared landing_resolver helper. Honors
    # `product.store_ids`, publish state, and visibility the same way
    # /api/public/events/{org}/{slug} does — so if the resolver returns a
    # slug, the storefront will accept it instead of 404-ing on a mismatch
    # between "first published store" and the product's actual assignment.
    from services.landing_resolver import resolve_best_landing_store

    resolved_store = await resolve_best_landing_store(
        org_id=org_id,
        product_store_ids=prod.get("store_ids") or [],
    )
    doc["org_store_slug"] = resolved_store.get("slug") if resolved_store else None

    return doc


@router.get("")
async def list_occurrences(
    product_id: str = Query(..., description="Product ID to list occurrences for"),
    current_user: dict = Depends(get_verified_user),
):
    """List event occurrences for a product."""
    org_id = current_user["organization_id"]
    cursor = event_occurrences_collection.find(
        {"organization_id": org_id, "product_id": product_id},
        {"_id": 0},
    ).sort("start_at", 1).limit(100)
    occurrences = await cursor.to_list(length=100)
    return {"occurrences": occurrences, "total": len(occurrences)}


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_occurrence(
    request: Request,
    body: EventOccurrenceCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create a new event occurrence for an event_ticket product."""
    org_id = current_user["organization_id"]
    product = await _validate_event_product(body.product_id, org_id)

    occurrence = EventOccurrence(
        organization_id=org_id,
        **body.model_dump(),
    )
    doc = occurrence.model_dump(mode="json")
    doc["product_name"] = product.get("name", "")

    # E3: autogenerate a URL slug when the admin left the field empty.
    # Client-provided slugs are respected but sanitized (slugify) — so
    # a paste of "Aperitivo d'Autunno!" becomes "aperitivo-d-autunno".
    requested_slug = slugify(doc.get("slug")) if doc.get("slug") else ""
    if requested_slug:
        # Check the sanitized slug is free; fall back to auto-generation
        # with the requested slug as the base when taken.
        existing = await event_occurrences_collection.find_one(
            {"organization_id": org_id, "slug": requested_slug},
            {"_id": 0, "id": 1},
        )
        if existing:
            doc["slug"] = await generate_occurrence_slug(
                org_id=org_id,
                product_name=requested_slug,
                start_at=doc.get("start_at"),
            )
        else:
            doc["slug"] = requested_slug
    else:
        doc["slug"] = await generate_occurrence_slug(
            org_id=org_id,
            product_name=product.get("name", ""),
            start_at=doc.get("start_at"),
        )

    await event_occurrences_collection.insert_one(doc)
    doc.pop("_id", None)

    logger.info(
        "event_occurrences: created %s (slug=%s) for product=%s org=%s",
        occurrence.id, doc["slug"], body.product_id, org_id,
    )
    return doc


@router.patch("/{occurrence_id}")
async def update_occurrence(
    occurrence_id: str,
    body: EventOccurrenceUpdate,
    current_user: dict = Depends(get_verified_user),
):
    """Update an event occurrence."""
    org_id = current_user["organization_id"]

    existing = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occurrence not found")

    updates = body.model_dump(exclude_unset=True)

    # Validate status transition if changing
    if "status" in updates:
        if updates["status"] not in OCCURRENCE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status must be one of: {', '.join(OCCURRENCE_STATUSES)}",
            )
        from services.commerce_rules import validate_occurrence_transition
        current_status = existing.get("status", "draft")
        valid, reason = validate_occurrence_transition(current_status, updates["status"])
        if not valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    # A4 (Onda 12) — hard constraint: occurrence.capacity cannot drop
    # below the sum of active tier capacities. Matches the symmetric
    # check in update_tier to prevent overbook via either side.
    if "capacity" in updates and updates["capacity"] is not None:
        new_cap = int(updates["capacity"])
        reserved = int(existing.get("reserved_seats") or 0)
        if new_cap < reserved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Capacità {new_cap} inferiore ai posti già riservati ({reserved})",
            )
        pipeline = [
            {"$match": {"organization_id": org_id,
                        "occurrence_id": occurrence_id,
                        "is_active": {"$ne": False}}},
            {"$group": {"_id": None,
                        "total_cap": {"$sum": {"$ifNull": ["$capacity", 0]}},
                        "any_unlimited": {"$max": {"$cond": [{"$eq": ["$capacity", None]}, 1, 0]}}}},
        ]
        agg = await event_ticket_tiers_collection.aggregate(pipeline).to_list(1)
        sum_tier_cap = int(agg[0]["total_cap"]) if agg else 0
        any_unlimited = bool(agg[0]["any_unlimited"]) if agg else False
        if not any_unlimited and sum_tier_cap > new_cap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Capacità {new_cap} inferiore alla somma dei tier "
                    f"({sum_tier_cap}). Riduci i tier oppure aumenta la capienza."
                ),
            )

    # E3: sanitize + deduplicate slug on update. Empty/null resets to
    # auto-generated (keeps the landing page URL stable by default).
    if "slug" in updates:
        raw = updates["slug"]
        sanitized = slugify(raw) if raw else ""
        if not sanitized:
            # Empty input -> regenerate from product name + date
            updates["slug"] = await generate_occurrence_slug(
                org_id=org_id,
                product_name=existing.get("product_name") or "",
                start_at=updates.get("start_at") or existing.get("start_at"),
                exclude_id=occurrence_id,
            )
        else:
            # Collision check against OTHER occurrences in the same org
            taken = await event_occurrences_collection.find_one(
                {"organization_id": org_id, "slug": sanitized,
                 "id": {"$ne": occurrence_id}},
                {"_id": 0, "id": 1},
            )
            if taken:
                updates["slug"] = await generate_occurrence_slug(
                    org_id=org_id,
                    product_name=sanitized,
                    start_at=updates.get("start_at") or existing.get("start_at"),
                    exclude_id=occurrence_id,
                )
            else:
                updates["slug"] = sanitized

    updates["updated_at"] = utc_now().isoformat()
    await event_occurrences_collection.update_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"$set": updates},
    )

    # Consistency auto-repair: for event_ticket, occurrence.status is the
    # single source of truth for visibility. When a merchant publishes an
    # occurrence, the parent product MUST be published + active — otherwise
    # the catalog filter (`product.is_published + is_active`) silently hides
    # the event and the merchant can't figure out why. We align the product
    # flags so the UI toggle actually has the expected effect.
    if updates.get("status") == "published" and existing.get("product_id"):
        await products_collection.update_one(
            {"id": existing["product_id"], "organization_id": org_id},
            {"$set": {"is_published": True, "is_active": True, "updated_at": utc_now().isoformat()}},
        )

    updated = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"_id": 0},
    )
    return updated


# ── E1: Ticket Tiers (nested under occurrence) ─────────────────────────────


async def _get_occurrence_or_404(occurrence_id: str, org_id: str) -> dict:
    """Fetch the occurrence and confirm it belongs to the caller's org.

    Shared guard for every tier endpoint so a client cannot sneak a
    cross-org tier write by crafting a URL path.
    """
    occ = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"_id": 0, "id": 1, "capacity": 1},
    )
    if not occ:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occurrence not found")
    return occ


def _with_remaining(tier: dict) -> dict:
    """Add the derived `remaining` field (capacity - reserved_seats)."""
    out = dict(tier)
    cap = tier.get("capacity")
    used = int(tier.get("reserved_seats") or 0)
    out["remaining"] = None if cap is None else max(0, cap - used)
    return out


@router.get("/{occurrence_id}/tiers")
async def list_tiers(
    occurrence_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """List ticket tiers for an occurrence, ordered by sort_order then created_at."""
    org_id = current_user["organization_id"]
    await _get_occurrence_or_404(occurrence_id, org_id)

    cursor = event_ticket_tiers_collection.find(
        {"organization_id": org_id, "occurrence_id": occurrence_id},
        {"_id": 0},
    ).sort([("sort_order", 1), ("created_at", 1)])
    tiers = await cursor.to_list(length=100)
    return {
        "tiers": [_with_remaining(t) for t in tiers],
        "total": len(tiers),
    }


@router.post("/{occurrence_id}/tiers", status_code=status.HTTP_201_CREATED)
async def create_tier(
    occurrence_id: str,
    body: EventTicketTierCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create a new ticket tier attached to the occurrence."""
    org_id = current_user["organization_id"]
    occ = await _get_occurrence_or_404(occurrence_id, org_id)

    # Defensive sanity: tier.capacity should not exceed the parent occurrence
    # capacity (if occurrence is capped). A merchant can still intentionally
    # create multiple tiers whose sum > occurrence.capacity — the atomic
    # reservation enforces the lower bound at write time, so this is only
    # a hint, not a hard error.
    occ_cap = occ.get("capacity")
    if occ_cap is not None and body.capacity is not None and body.capacity > occ_cap:
        logger.info(
            "event_occurrences: tier capacity %d > occurrence capacity %d for occ=%s (allowed, but reservation will cap at occurrence)",
            body.capacity, occ_cap, occurrence_id,
        )

    tier = EventTicketTier(
        organization_id=org_id,
        occurrence_id=occurrence_id,
        **body.model_dump(),
    )
    doc = tier.model_dump(mode="json")
    await event_ticket_tiers_collection.insert_one(doc)
    doc.pop("_id", None)

    logger.info("event_occurrences: created tier %s on occ=%s org=%s", tier.id, occurrence_id, org_id)
    return _with_remaining(doc)


@router.patch("/{occurrence_id}/tiers/{tier_id}")
async def update_tier(
    occurrence_id: str,
    tier_id: str,
    body: EventTicketTierUpdate,
    current_user: dict = Depends(get_verified_user),
):
    """Update a tier. Rejects edits that would overbook existing reservations."""
    org_id = current_user["organization_id"]
    await _get_occurrence_or_404(occurrence_id, org_id)

    existing = await event_ticket_tiers_collection.find_one(
        {"id": tier_id, "organization_id": org_id, "occurrence_id": occurrence_id},
        {"_id": 0},
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tier not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    # Guard: new capacity cannot go below already-reserved seats.
    if "capacity" in updates and updates["capacity"] is not None:
        reserved = int(existing.get("reserved_seats") or 0)
        if updates["capacity"] < reserved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Capacity {updates['capacity']} below already reserved ({reserved}): would overbook",
            )

        # A4 (Onda 12) — hard constraint: sum of tier capacities must
        # not exceed the occurrence.capacity. The wizard enforces this
        # soft; we enforce it hard on PATCH so manual edits after wizard
        # submission cannot create an overbook scenario.
        occ_doc = await event_occurrences_collection.find_one(
            {"id": occurrence_id, "organization_id": org_id},
            {"_id": 0, "capacity": 1},
        ) or {}
        occ_capacity = occ_doc.get("capacity")
        if occ_capacity is not None:
            # Sum of capacities across all ACTIVE tiers of this occurrence,
            # substituting the updated value for this one tier.
            pipeline = [
                {"$match": {"organization_id": org_id,
                            "occurrence_id": occurrence_id,
                            "is_active": {"$ne": False},
                            "id": {"$ne": tier_id}}},
                {"$group": {"_id": None,
                            "total_cap": {"$sum": {"$ifNull": ["$capacity", 0]}},
                            "any_unlimited": {"$max": {"$cond": [{"$eq": ["$capacity", None]}, 1, 0]}}}},
            ]
            agg = await event_ticket_tiers_collection.aggregate(pipeline).to_list(1)
            other_sum = int(agg[0]["total_cap"]) if agg else 0
            any_unlimited = bool(agg[0]["any_unlimited"]) if agg else False
            new_total = other_sum + int(updates["capacity"])
            # If any other tier has unlimited capacity (None), the sum is
            # meaningless — skip the constraint (merchant's explicit choice).
            if not any_unlimited and new_total > occ_capacity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Somma capacità tier ({new_total}) supererebbe la "
                        f"capienza dell'evento ({occ_capacity}). Riduci questo "
                        f"tier o aumenta la capienza dell'evento."
                    ),
                )

    updates["updated_at"] = utc_now().isoformat()
    await event_ticket_tiers_collection.update_one(
        {"id": tier_id, "organization_id": org_id},
        {"$set": updates},
    )

    updated = await event_ticket_tiers_collection.find_one(
        {"id": tier_id, "organization_id": org_id},
        {"_id": 0},
    )
    return _with_remaining(updated or {})


@router.delete("/{occurrence_id}/tiers/{tier_id}")
async def delete_tier(
    occurrence_id: str,
    tier_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Delete a tier. Soft-delete when seats are reserved, hard-delete otherwise."""
    org_id = current_user["organization_id"]
    await _get_occurrence_or_404(occurrence_id, org_id)

    existing = await event_ticket_tiers_collection.find_one(
        {"id": tier_id, "organization_id": org_id, "occurrence_id": occurrence_id},
        {"_id": 0, "reserved_seats": 1},
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tier not found")

    reserved = int(existing.get("reserved_seats") or 0)
    if reserved > 0:
        # Can't hard-delete — the order history still points here via snapshot.
        # Soft-delete: is_active=False. New reservations refused by
        # tier_capacity; existing ones remain valid.
        await event_ticket_tiers_collection.update_one(
            {"id": tier_id, "organization_id": org_id},
            {"$set": {"is_active": False, "updated_at": utc_now().isoformat()}},
        )
        return {"deleted": "soft", "reason": "has_reservations", "reserved_seats": reserved}

    # No reservations — safe to hard-delete.
    res = await event_ticket_tiers_collection.delete_one(
        {"id": tier_id, "organization_id": org_id},
    )
    return {"deleted": "hard", "removed": int(getattr(res, "deleted_count", 0))}


# ── Cover image upload ────────────────────────────────────────────────────────

@router.post("/{occurrence_id}/cover-image", status_code=200)
@limiter.limit("5/minute")
async def upload_occurrence_cover_image(
    request: Request,
    occurrence_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_verified_user),
):
    """Upload (or replace) the cover image of an event occurrence. Max 5MB, jpg/png/webp."""
    org_id = current_user["organization_id"]
    occ = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"_id": 0, "id": 1},
    )
    if not occ:
        raise HTTPException(status_code=404, detail="Occurrence not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in COVER_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Formato non supportato. Usa: {', '.join(COVER_ALLOWED_EXTENSIONS)}")
    if file.content_type and file.content_type not in COVER_ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail=f"Tipo file non supportato: {file.content_type}")

    contents = await file.read()
    if len(contents) > COVER_MAX_SIZE:
        raise HTTPException(status_code=400, detail="Immagine troppo grande. Max 5MB.")

    os.makedirs(COVER_UPLOAD_DIR, exist_ok=True)
    for old_ext in COVER_ALLOWED_EXTENSIONS:
        old_path = os.path.join(COVER_UPLOAD_DIR, f"{occurrence_id}{old_ext}")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    filename = f"{occurrence_id}{ext}"
    filepath = os.path.join(COVER_UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    cover_image_url = f"/uploads/occurrences/{filename}"
    await event_occurrences_collection.update_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"$set": {"cover_image_url": cover_image_url, "updated_at": utc_now().isoformat()}},
    )
    return {"cover_image_url": cover_image_url, "size": len(contents)}


# ── Fase 2 S2 (retreat) — dashboard incassi per ritiro ──────────────────────

@router.get("/{occurrence_id}/payments")
@limiter.limit("60/minute")
async def get_occurrence_payments(
    occurrence_id: str,
    request: Request,
    current_user: dict = Depends(get_verified_user),
):
    """Dashboard incassi del ritiro: aggregato (incassato / in arrivo /
    in ritardo / a rischio) + dettaglio per ordine con stato di ogni
    scadenza. Fonte di verità: payment_schedules; i nomi cliente vengono
    dagli ordini (snapshot)."""
    from database import db, orders_collection
    from services.payment_schedule_service import aggregate_schedules

    org_id = current_user["organization_id"]
    schedules = await db.payment_schedules.find(
        {"organization_id": org_id, "occurrence_id": occurrence_id},
        {"_id": 0},
    ).to_list(1000)

    order_ids = [s["order_id"] for s in schedules]
    orders = await orders_collection.find(
        {"organization_id": org_id, "id": {"$in": order_ids}},
        {"_id": 0, "id": 1, "customer_name": 1, "order_number": 1, "status": 1},
    ).to_list(1000)
    order_by_id = {o["id"]: o for o in orders}

    # Carrelli abbandonati (ordine draft, nessun incasso) fuori dalle
    # metriche: una caparra mai pagata di una bozza non è un "ritardo".
    live = [
        s for s in schedules
        if not (
            order_by_id.get(s["order_id"], {}).get("status") == "draft"
            and s.get("payment_state") in (None, "none")
        )
    ]

    detail = []
    for s in live:
        o = order_by_id.get(s["order_id"], {})
        detail.append({
            "order_id": s["order_id"],
            "order_number": o.get("order_number"),
            "customer_name": o.get("customer_name"),
            "order_status": o.get("status"),
            "payment_state": s.get("payment_state"),
            "currency": s.get("currency"),
            "totals": s.get("totals"),
            "rows": [
                {k: r.get(k) for k in (
                    "seq", "kind", "label", "amount_minor", "due_at",
                    "status", "paid_at", "manual_note")}
                for r in (s.get("rows") or [])
            ],
        })

    return {
        "occurrence_id": occurrence_id,
        "summary": aggregate_schedules(live),
        "abandoned_drafts": len(schedules) - len(live),
        "orders": detail,
    }


@router.post("/{occurrence_id}/cancel-cascade")
@limiter.limit("5/minute")
async def cancel_occurrence_with_cascade(
    occurrence_id: str,
    request: Request,
    body: dict = None,
    current_user: dict = Depends(get_verified_user),
):
    """Annulla il ritiro CON cascata: rimborso 100% a tutti gli ordini
    attivi, biglietti annullati, broadcast ai partecipanti. Richiede
    conferma esplicita nel body ({confirm: true}) — irreversibile."""
    from services.payment_refund_service import cancel_occurrence_cascade

    if not (body or {}).get("confirm"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conferma esplicita richiesta: {\"confirm\": true}",
        )
    org_id = current_user["organization_id"]
    actor = f"operator:{current_user.get('user_id') or 'unknown'}"
    try:
        return await cancel_occurrence_cascade(org_id, occurrence_id, actor=actor)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
