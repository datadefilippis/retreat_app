"""
Orders Router — CRUD + lifecycle actions for structured sales orders.

Endpoints:
  GET    /orders          — list orders (filterable by status)
  POST   /orders          — create draft order
  GET    /orders/{id}     — get single order
  PATCH  /orders/{id}     — update draft order
  POST   /orders/{id}/confirm   — confirm order (generates SalesRecords)
  POST   /orders/{id}/cancel    — cancel order (generates storno if was confirmed)
  POST   /orders/{id}/complete  — mark confirmed order as completed
  POST   /orders/import         — bulk import orders from CSV/XLSX
  POST   /orders/import-with-mapping — complete import with user column mapping
"""

import logging
import json
import base64
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Query, Request, status, UploadFile, File, Form
from auth import get_current_user, get_verified_user, get_verified_user
from routers.auth import limiter
from models.order import OrderCreate, OrderUpdate, OrderResponse, OrderLineCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("/unseen-count")
@limiter.limit("30/minute")
async def get_unseen_order_count(
    request: Request,
    current_user: dict = Depends(get_verified_user),
):
    """Count orders created since the user last viewed orders."""
    from database import orders_collection, organizations_collection

    org_id = current_user["organization_id"]

    # Get last_seen_at from org (simple approach — per org, not per user)
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "orders_last_seen_at": 1})
    last_seen = (org or {}).get("orders_last_seen_at")

    if not last_seen:
        # Never seen → count all draft orders from storefront
        count = await orders_collection.count_documents(
            {"organization_id": org_id, "status": "draft", "source": {"$regex": "^storefront"}})
    else:
        # Count orders with order_date > last_seen
        count = await orders_collection.count_documents(
            {"organization_id": org_id, "order_date": {"$gt": last_seen}})

    return {"unseen_count": count}


@router.post("/mark-seen")
@limiter.limit("10/minute")
async def mark_orders_seen(
    request: Request,
    current_user: dict = Depends(get_verified_user),
):
    """Mark all current orders as seen (update last_seen_at)."""
    from database import organizations_collection
    from datetime import date

    org_id = current_user["organization_id"]
    await organizations_collection.update_one(
        {"id": org_id},
        {"$set": {"orders_last_seen_at": date.today().isoformat()}},
    )
    return {"message": "ok"}


@router.get("/summary")
@limiter.limit("30/minute")
async def get_orders_summary(
    request: Request,
    current_user: dict = Depends(get_verified_user),
):
    """Lightweight counts for dashboard operations signals. No order data returned."""
    from database import orders_collection
    from services.commerce_rules import derive_review_info

    org_id = current_user["organization_id"]

    # Fetch minimal fields for counting (not full order documents)
    cursor = orders_collection.find(
        {"organization_id": org_id, "status": {"$in": ["draft", "confirmed"]}},
        {"_id": 0, "status": 1, "payment_intent": 1, "source": 1, "fulfillment": 1},
    )
    orders = await cursor.to_list(500)

    drafts = 0
    needs_review = 0
    fulfillment_pending = 0
    confirmed_active = 0
    paid_unconfirmed = 0

    for o in orders:
        st = o.get("status")
        if st == "draft":
            drafts += 1
            review = derive_review_info(o)
            if review:
                needs_review += 1
            # Payment collected but order still draft = critical
            if o.get("payment_intent") == "collected":
                paid_unconfirmed += 1
        elif st == "confirmed":
            confirmed_active += 1
            ff = o.get("fulfillment") or {}
            if ff.get("mode", "not_required") != "not_required" and ff.get("status") == "pending":
                fulfillment_pending += 1

    return {
        "drafts": drafts,
        "needs_review": needs_review,
        "fulfillment_pending": fulfillment_pending,
        "confirmed_active": confirmed_active,
        "paid_unconfirmed": paid_unconfirmed,
    }


@router.get("/dashboard")
@limiter.limit("15/minute")
async def get_orders_dashboard(
    request: Request,
    store_id: str = None,
    current_user: dict = Depends(get_verified_user),
):
    """Aggregated commerce data for dashboard widgets. Single call, 5 parallel pipelines.

    Optional store_id query param filters all pipelines to a specific store.
    Uses order_date (ISO string, always present) for temporal filters.
    """
    import asyncio
    from database import orders_collection
    from datetime import date, timedelta

    org_id = current_user["organization_id"]
    today = date.today()
    today_str = today.isoformat()
    d30_str = (today - timedelta(days=30)).isoformat()
    d7_str = (today - timedelta(days=7)).isoformat()

    # Base match filter — optionally scoped to a specific store
    base_match = {"organization_id": org_id}
    if store_id:
        base_match["store_id"] = store_id

    async def _pipeline():
        pipeline = [
            {"$match": {**base_match}},
            {"$group": {"_id": "$status", "count": {"$sum": 1},
                        "amount": {"$sum": {"$ifNull": ["$total", 0]}}}},
        ]
        result = {}
        async for doc in orders_collection.aggregate(pipeline):
            result[doc["_id"]] = {"count": doc["count"], "amount": round(doc["amount"], 2)}
        return result

    async def _revenue_by_type():
        pipeline = [
            {"$match": {**base_match, "status": {"$in": ["confirmed", "completed"]}}},
            # Project only the fields needed before $unwind to reduce memory/IO
            {"$project": {"_id": 0, "items.item_type": 1, "items.line_total": 1}},
            {"$unwind": "$items"},
            {"$group": {"_id": {"$ifNull": ["$items.item_type", "physical"]},
                        "revenue": {"$sum": "$items.line_total"}}},
        ]
        result = {}
        async for doc in orders_collection.aggregate(pipeline):
            result[doc["_id"]] = round(doc["revenue"], 2)
        return result

    async def _fulfillment_queue():
        cursor = orders_collection.find(
            {**base_match, "status": {"$in": ["confirmed", "completed"]},
             "fulfillment.status": "pending", "fulfillment.mode": {"$nin": ["not_required", None]}},
            {"_id": 0, "id": 1, "order_number": 1, "customer_name": 1, "total": 1,
             "order_date": 1, "fulfillment.mode": 1},
        ).sort("order_date", 1).limit(5)
        queue = []
        async for o in cursor:
            od = o.get("order_date")
            days = (today - date.fromisoformat(od)).days if od else 0
            queue.append({
                "order_id": o["id"], "order_number": o.get("order_number"),
                "customer_name": o.get("customer_name"), "total": o.get("total", 0),
                "days_pending": days,
                "fulfillment_mode": o.get("fulfillment", {}).get("mode"),
            })
        return queue

    async def _payment_at_risk():
        pipeline = [
            {"$match": {**base_match, "status": {"$ne": "cancelled"},
                         "payment_status": {"$ne": "paid"},
                         "payment_intent": {"$in": ["required", "collected"]}}},
            {"$group": {"_id": None, "count": {"$sum": 1},
                        "amount": {"$sum": {"$ifNull": ["$total", 0]}}}},
        ]
        result = await orders_collection.aggregate(pipeline).to_list(1)
        if result:
            return {"count": result[0]["count"], "amount": round(result[0]["amount"], 2)}
        return {"count": 0, "amount": 0}

    async def _stats():
        # Orders today (by order_date string)
        today_count = await orders_collection.count_documents(
            {**base_match, "order_date": today_str})

        # Revenue confirmed/completed in 30d
        rev_pipeline = [
            {"$match": {**base_match,
                         "status": {"$in": ["confirmed", "completed"]},
                         "order_date": {"$gte": d30_str}}},
            {"$group": {"_id": None,
                        "total": {"$sum": {"$ifNull": ["$total", 0]}},
                        "confirmed": {"$sum": {"$cond": [{"$eq": ["$status", "confirmed"]}, 1, 0]}},
                        "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}}}},
        ]
        rev_result = await orders_collection.aggregate(rev_pipeline).to_list(1)
        rev = rev_result[0] if rev_result else {"total": 0, "confirmed": 0, "completed": 0}
        active = rev["confirmed"] + rev["completed"]
        comp_rate = round(rev["completed"] / active * 100, 1) if active > 0 else 0

        # Cancellations 7d (by order_date)
        cancel_7d = await orders_collection.count_documents(
            {**base_match, "status": "cancelled", "order_date": {"$gte": d7_str}})

        return {
            "orders_today": today_count,
            "revenue_confirmed_30d": round(rev["total"], 2),
            "completion_rate_pct": comp_rate,
            "cancellations_7d": cancel_7d,
        }

    pipeline, rev_type, ff_queue, pay_risk, stats = await asyncio.gather(
        _pipeline(), _revenue_by_type(), _fulfillment_queue(), _payment_at_risk(), _stats(),
    )

    has_data = sum(v["count"] for v in pipeline.values()) > 0
    total_confirmed_rev = round(
        pipeline.get("confirmed", {}).get("amount", 0) + pipeline.get("completed", {}).get("amount", 0), 2)

    return {
        "has_data": has_data,
        "pipeline": pipeline,
        "total_confirmed_revenue": total_confirmed_rev,
        "revenue_by_type": rev_type,
        "fulfillment_queue": ff_queue,
        "payment_at_risk": pay_risk,
        "stats": stats,
    }


@router.get("")
async def list_orders(
    order_status: Optional[str] = Query(None, alias="status"),
    payment_intent: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
    current_user: dict = Depends(get_verified_user),
):
    """List orders for the current org, optionally filtered by status and payment_intent."""
    from repositories import order_repository
    orders = await order_repository.find_by_org(
        current_user["organization_id"],
        status=order_status,
        limit=limit,
    )
    # Client-side payment_intent filter (avoids repo change for MVP)
    if payment_intent:
        orders = [o for o in orders if o.get("payment_intent") == payment_intent]

    # Derive review_state for each order
    from services.commerce_rules import derive_review_info, get_order_actions, analyze_order_composition, get_fulfillment_actions
    for o in orders:
        review = derive_review_info(o)
        o["review_state"] = review["state"] if review else None
        o["review_reason"] = review["reason"] if review else None
        o["actions"] = get_order_actions(o)
        o["composition"] = analyze_order_composition(o)
        o["fulfillment_actions"] = get_fulfillment_actions(o)

    return {"orders": orders, "total": len(orders)}


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_order(
    request: Request,
    body: OrderCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create a new draft order.

    v5.8 / Onda 10 Step D.2 — 60 req/min IP.
    """
    # v5.8 / Onda 9.L — Orders monthly quota enforcement on the admin manual
    # order creation path. The storefront customer flow (public.py) already
    # had its own enforcement; this closes the gap where admins could create
    # unlimited orders via direct API or POS, bypassing the plan's
    # commerce.orders_monthly limit.
    from services.module_access import enforce_count_quota
    from database import orders_collection
    from datetime import datetime, timezone

    org_id = current_user["organization_id"]
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    current_count = await orders_collection.count_documents({
        "organization_id": org_id,
        "created_at": {"$gte": month_start},
    })
    await enforce_count_quota(
        org_id, "commerce", "orders_monthly",
        current_count=current_count,
        addon_slug="addon_orders_pack",  # surface "+200 ordini" in the paywall
        message_template=(
            "Hai raggiunto il limite di {limit} ordini/mese del tuo piano. "
            "Aggiorna il piano o aggiungi il pack '+200 ordini' per crearne altri."
        ),
        hard_abuse_cap=100000,
    )

    from services.order_service import create_order as svc_create
    try:
        order = await svc_create(org_id, body)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Onda 16 — Price preview (stateless, for storefront dynamic pricing) ──────


class _PricePreviewRequest(BaseModel):
    product_id: str
    quantity: float = 1
    discount_pct: float = 0
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    extra_selections: Optional[dict] = None
    # Onda 17 — slot flavor variable duration + cross-day.
    slot_date_from: Optional[str] = None
    slot_time_from: Optional[str] = None
    slot_date_to: Optional[str] = None
    slot_time_to: Optional[str] = None


@router.post("/price-preview")
@limiter.limit("60/minute")
async def price_preview(
    request: Request,
    body: _PricePreviewRequest,
    current_user: dict = Depends(get_verified_user),
):
    """Dry-run price calculation with extras resolved server-side.

    Returns {base, extras_total, total, day_count, extras[], extras_breakdown}.
    Used by the storefront landing pages for live price display as the
    customer toggles extras / picks dates. Stateless — no order is created.
    """
    from database import products_collection, product_extras_collection
    from services.pricing import compute_line_total, compute_rental_multiplier, PricingError

    org_id = current_user["organization_id"]
    product = await products_collection.find_one(
        {"id": body.product_id, "organization_id": org_id},
        {"_id": 0, "unit_price": 1, "item_type": 1, "name": 1, "metadata": 1},
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prodotto non trovato")

    extras_catalog = await product_extras_collection.find(
        {"organization_id": org_id, "product_id": body.product_id, "is_active": True},
        {"_id": 0},
    ).to_list(None)

    # Rental multiplier parity with order_service.create_order (see lines ~155-176).
    # compute_line_total itself computes `base = quantity * unit_price * (1-discount)`
    # but does NOT know about rental_unit / date span. To keep the preview numerically
    # identical to the checkout, we pre-inflate `quantity` by the rental multiplier so
    # the base the helper returns matches `unit_price × qty × rental_multiplier × …`.
    rental_multiplier = compute_rental_multiplier(
        item_type=product.get("item_type"),
        metadata=product.get("metadata") or {},
        date_from=body.date_from,
        date_to=body.date_to,
        slot_date_from=body.slot_date_from,
        slot_time_from=body.slot_time_from,
        slot_date_to=body.slot_date_to,
        slot_time_to=body.slot_time_to,
    )

    try:
        result = compute_line_total(
            unit_price=float(product.get("unit_price") or 0),
            quantity=float(body.quantity or 0) * rental_multiplier,
            discount_pct=body.discount_pct,
            extras_catalog=extras_catalog,
            extras_selection=body.extra_selections,
            date_from=body.date_from,
            date_to=body.date_to,
        )
    except PricingError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.detail, "context": e.context},
        )
    return result.to_dict()


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Get a single order by ID.

    Customer enrichment (read-only, non-persisting): if the order document is
    missing contact info (common on legacy orders pre-F2 Onda 9) we fall back
    to the linked customer record so the admin panel always has email/phone
    available to display.
    """
    from repositories import order_repository
    order = await order_repository.find_one(order_id, current_user["organization_id"])
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Enrich missing customer contact fields from customers_collection.
    # Never overwrites existing values; only fills None/empty.
    needs_enrichment = (
        not order.get("customer_email")
        or not order.get("contact_phone")
        or not order.get("customer_name")
    )
    if needs_enrichment and order.get("customer_id"):
        from database import customers_collection
        cust = await customers_collection.find_one(
            {"id": order["customer_id"], "organization_id": current_user["organization_id"]},
            {"_id": 0, "name": 1, "email": 1, "phone": 1},
        )
        if cust:
            if not order.get("customer_name"):
                order["customer_name"] = cust.get("name") or ""
            if not order.get("customer_email"):
                order["customer_email"] = cust.get("email")
            if not order.get("contact_phone"):
                order["contact_phone"] = cust.get("phone")

    return order


@router.get("/{order_id}/issued")
@limiter.limit("60/minute")
async def get_order_issued_entities(
    request: Request,
    order_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Aggregate IssuedTicket / IssuedBooking / IssuedReservation for an order.

    Single-call convenience endpoint for the admin order detail panel so it can
    render all downstream entities (tickets, bookings, reservations) with codes,
    access_token URLs, delivery status, and resend/open quick actions.

    Empty arrays are returned for kinds not present on the order — the shape is
    stable so the frontend can mount without optional-chaining.
    """
    from database import (
        issued_tickets_collection,
        issued_bookings_collection,
        issued_reservations_collection,
        orders_collection,
    )

    org_id = current_user["organization_id"]

    # Verify order ownership first (cheap guard before 3 lookups)
    order_exists = await orders_collection.count_documents(
        {"id": order_id, "organization_id": org_id}, limit=1,
    )
    if not order_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    q = {"organization_id": org_id, "order_id": order_id}
    tickets, bookings, reservations = [], [], []

    async for t in issued_tickets_collection.find(q, {"_id": 0}):
        t["landing_url"] = f"/t/{t.get('access_token')}" if t.get("access_token") else None
        tickets.append(t)

    async for b in issued_bookings_collection.find(q, {"_id": 0}):
        b["landing_url"] = f"/b/{b.get('access_token')}" if b.get("access_token") else None
        bookings.append(b)

    async for r in issued_reservations_collection.find(q, {"_id": 0}):
        r["landing_url"] = f"/rsv/{r.get('access_token')}" if r.get("access_token") else None
        reservations.append(r)

    return {
        "tickets": tickets,
        "bookings": bookings,
        "reservations": reservations,
    }


@router.get("/{order_id}/receipt")
async def download_order_receipt(
    order_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Generate and download a PDF receipt for an order."""
    from repositories import order_repository
    from services.order_pdf_service import generate_order_receipt
    from database import organizations_collection
    from fastapi.responses import Response

    org_id = current_user["organization_id"]
    order = await order_repository.find_one(order_id, org_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    org = await organizations_collection.find_one({"id": org_id}, {"_id": 0, "store_settings": 1, "name": 1})
    store_settings = (org or {}).get("store_settings") or {}
    if not store_settings.get("display_name"):
        store_settings["display_name"] = (org or {}).get("name", "Store")

    # Enrich order with customer_name if missing
    if not order.get("customer_name") and order.get("customer_id"):
        from database import customers_collection
        cust = await customers_collection.find_one({"id": order["customer_id"]}, {"_id": 0, "name": 1})
        if cust:
            order["customer_name"] = cust.get("name", "")

    pdf_bytes = generate_order_receipt(order, store_settings)
    filename = f"ricevuta_{order.get('order_number', order_id[:8])}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{order_id}")
async def update_order(
    order_id: str,
    body: OrderUpdate,
    current_user: dict = Depends(get_verified_user),
):
    """Update a draft order. Only draft orders can be updated."""
    from services.order_service import update_order as svc_update
    try:
        order = await svc_update(current_user["organization_id"], order_id, body)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{order_id}/confirm")
@limiter.limit("10/minute")
async def confirm_order(
    request: Request,
    order_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Confirm a draft order: assigns order number and generates SalesRecords.

    Idempotent: confirming an already-confirmed order returns it without side effects.
    """
    from services.order_service import confirm_order as svc_confirm
    try:
        order = await svc_confirm(current_user["organization_id"], order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{order_id}/verify-payment")
@limiter.limit("6/minute")
async def verify_order_payment(
    request: Request,
    order_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Admin-triggered: ask Stripe directly whether this order's session was paid.

    Safety net for orders that are stuck in draft because a webhook was lost or
    took too long. Delegates to payment_checkout_service.verify_commerce_order_payment
    which delegates back to the canonical reconciliation path — so side effects
    (order confirm, alerts, emails) are identical to a real webhook arrival.

    Idempotent: if the order is already reconciled, returns status=already_reconciled
    without mutating anything. The internal processed_events guard also prevents
    a later real webhook (arriving after the verify call) from double-confirming.

    Rate-limited tightly (6/min/user) because each call is a Stripe API round-trip.
    """
    from services.payment_checkout_service import verify_commerce_order_payment
    result = await verify_commerce_order_payment(
        order_id, current_user["organization_id"],
    )
    # Map error statuses to HTTP codes; reserve 200 for actionable outcomes.
    if result.get("status") == "error":
        detail = result.get("reason") or result.get("error") or "verification_failed"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
    return result


@router.post("/{order_id}/cancel")
@limiter.limit("10/minute")
async def cancel_order(
    request: Request,
    order_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Cancel an order. If it was confirmed, generates storno SalesRecords.

    Idempotent: cancelling an already-cancelled order returns it without side effects.
    """
    from services.order_service import cancel_order as svc_cancel
    try:
        order = await svc_cancel(current_user["organization_id"], order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{order_id}/complete")
@limiter.limit("10/minute")
async def complete_order(
    request: Request,
    order_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Mark a confirmed order as completed (paid/fulfilled)."""
    from services.order_service import complete_order as svc_complete
    try:
        order = await svc_complete(current_user["organization_id"], order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{order_id}/mark-paid")
@limiter.limit("30/minute")
async def mark_order_paid(
    request: Request,
    order_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Mark a confirmed/completed order as paid (manual payment registration)."""
    from services.order_service import mark_order_paid as svc_mark_paid
    try:
        order = await svc_mark_paid(current_user["organization_id"], order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{order_id}/mark-unpaid")
@limiter.limit("30/minute")
async def mark_order_unpaid(
    request: Request,
    order_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Revert a confirmed/completed order to pending payment (correction)."""
    from services.order_service import mark_order_unpaid as svc_mark_unpaid
    try:
        order = await svc_mark_unpaid(current_user["organization_id"], order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── POS (v12.0) ─────────────────────────────────────────────────────────

class PosOrderItem(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit_price: Optional[float] = Field(default=None, ge=0)


class PosOrderRequest(BaseModel):
    """Quick order creation for POS mode. Creates + confirms in one step."""
    customer_name: str = Field(min_length=1, max_length=255)
    customer_email: Optional[str] = None
    items: List[PosOrderItem] = Field(min_length=1)
    notes: Optional[str] = None
    store_id: Optional[str] = None


@router.post("/pos", status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_pos_order(
    request: Request,
    body: PosOrderRequest,
    current_user: dict = Depends(get_verified_user),
):
    """Create a POS order: find/create customer → create order → auto-confirm.

    POS orders skip payment (in-person payment assumed) and are immediately
    confirmed with source='pos'.

    v5.8 / Onda 10 Step D.2 — 60 req/min IP.

    v5.8 / Onda 9.Y.0 — Plan-gated under commerce.orders_monthly. POS
    was previously the last gap in the orders flow: the manual `POST /orders`
    enforces the quota at line 314 but POS bypassed straight into
    svc_create + svc_confirm. Same gate, same paywall payload (with
    addon_orders_pack hint).
    """
    from services.order_service import create_order as svc_create, confirm_order as svc_confirm
    from services.module_access import enforce_count_quota
    from database import customers_collection, orders_collection
    from models.common import generate_id, utc_now
    from datetime import datetime, timezone

    org_id = current_user["organization_id"]

    # Plan gate — same shape as POST /orders (line 303-323) so the
    # frontend axios interceptor + QuotaExceededPaywall handle the
    # rejection identically. Defence-in-depth hard_abuse_cap=100000.
    now_utc = datetime.now(timezone.utc)
    month_start = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    current_count = await orders_collection.count_documents({
        "organization_id": org_id,
        "created_at": {"$gte": month_start},
    })
    await enforce_count_quota(
        org_id, "commerce", "orders_monthly",
        current_count=current_count,
        addon_slug="addon_orders_pack",
        message_template=(
            "Hai raggiunto il limite di {limit} ordini/mese del tuo piano. "
            "Aggiorna il piano o aggiungi il pack '+200 ordini' per crearne altri."
        ),
        hard_abuse_cap=100000,
    )

    # Find or create customer by email (POS: email is optional).
    #
    # Phase 4 of the Store consolidation plan — race-safe upsert.
    # ----------------------------------------------------------
    # Pre-Phase-4 this was a find-then-insert pattern, vulnerable to
    # the same race condition as the storefront checkout flow: two
    # POS terminals scanning the same loyalty card simultaneously
    # could create two customer rows. The upsert helper guarantees
    # atomic convergence at the Mongo document level.
    #
    # When email is absent (anonymous POS walk-in), we fall back to
    # a plain insert with `email=None` — the unique partial index
    # filters on `{email: $type: "string"}` so null-email rows are
    # exempt from the constraint and can coexist freely.
    if body.customer_email:
        from repositories.customer_repository import upsert_by_email
        customer_id, _ = await upsert_by_email(
            org_id,
            name=body.customer_name.strip(),
            email=body.customer_email,
            source="pos",
        )
    else:
        now = utc_now()
        customer_doc = {
            "id": generate_id(),
            "organization_id": org_id,
            "name": body.customer_name.strip(),
            "email": None,
            "is_active": True,
            "tags": [],
            "metadata": {"source": "pos"},
            "created_at": now,
            "updated_at": now,
        }
        await customers_collection.insert_one(customer_doc)
        customer_id = customer_doc["id"]

    # Create order
    order_create = OrderCreate(
        customer_id=customer_id,
        notes=body.notes,
        items=[
            OrderLineCreate(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in body.items
        ],
    )

    try:
        order = await svc_create(
            org_id, order_create,
            source="pos",
            payment_intent="none",  # POS: no online payment
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Auto-confirm (POS orders don't need manual confirmation)
    try:
        order = await svc_confirm(org_id, order["id"], skip_payment_check=True)
    except ValueError as e:
        # Order created but confirm failed — return draft
        logger.warning("pos: auto-confirm failed for order %s: %s", order["id"], e)

    return order


# ── Fulfillment (v10.0) ──────────────────────────────────────────────────

from pydantic import BaseModel, Field as PydanticField


class FulfillmentUpdateBody(BaseModel):
    status: str = PydanticField(
        ...,
        pattern="^(shipped|delivered|ready_for_pickup|picked_up|fulfilled)$",
    )
    # Release 1 (Physical) — optional carrier tracking captured when the admin
    # transitions to "shipped". Silently ignored for transitions where tracking
    # is not meaningful (delivered / ready_for_pickup / picked_up / fulfilled).
    tracking_number: Optional[str] = PydanticField(default=None, max_length=120)
    tracking_url: Optional[str] = PydanticField(default=None, max_length=500)


@router.post("/{order_id}/fulfillment")
async def update_fulfillment(
    order_id: str,
    body: FulfillmentUpdateBody,
    current_user: dict = Depends(get_verified_user),
):
    """Transition fulfillment status. Admin-driven, mode-aware transitions."""
    from services.order_service import update_fulfillment_status
    try:
        order = await update_fulfillment_status(
            current_user["organization_id"], order_id, body.status,
            tracking_number=body.tracking_number,
            tracking_url=body.tracking_url,
        )
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Bulk Import (CSV/XLSX) ───────────────────────────────────────────────────

_MAX_IMPORT_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/import")
@limiter.limit("10/minute")
async def import_orders(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_verified_user),
):
    """Import orders from CSV/XLSX. Auto-confirms and generates SalesRecords.

    If column mapping is needed, returns 422 with mapping data.
    The frontend then calls /orders/import-with-mapping with the user's mapping.
    """
    from services.order_import_service import analyze_order_import, execute_order_import
    from database import temp_uploads_collection
    from datetime import datetime, timezone

    content = await file.read()

    if len(content) > _MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File troppo grande. Dimensione massima: {_MAX_IMPORT_BYTES // (1024 * 1024)} MB.",
        )

    org_id = current_user["organization_id"]

    try:
        # Analyze columns
        analysis = await analyze_order_import(content, file.filename, org_id)

        if analysis["status"] == "needs_column_mapping":
            # Store file temporarily (TTL 1h)
            temp_id = f"temp_order_{current_user['user_id']}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            await temp_uploads_collection.insert_one({
                "_id": temp_id,
                "content_b64": base64.b64encode(content).decode("ascii"),
                "filename": file.filename,
                "import_type": "orders",
                "organization_id": org_id,
                "user_id": current_user["user_id"],
                "created_at": datetime.now(timezone.utc),
            })
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "status": "needs_column_mapping",
                    "temp_upload_id": temp_id,
                    "recognized_columns": analysis["recognized_columns"],
                    "unmapped_columns": analysis["unmapped_columns"],
                    "missing_required": analysis["missing_required"],
                    "target_fields": analysis["target_fields"],
                    "preview_rows": analysis["preview_rows"],
                    "all_file_columns": analysis["all_file_columns"],
                },
            )

        # All columns auto-mapped — execute import
        result = await execute_order_import(
            content=content,
            filename=file.filename,
            org_id=org_id,
            user_id=current_user["user_id"],
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("import_orders parse error: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("import_orders unexpected error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante l'importazione. Riprova più tardi.",
        )


@router.post("/import-with-mapping")
@limiter.limit("10/minute")
async def import_orders_with_mapping(
    request: Request,
    temp_upload_id: str = Form(...),
    column_mapping: str = Form(...),  # JSON string: {"file_col": "target_field", ...}
    current_user: dict = Depends(get_verified_user),
):
    """Complete an order import using user-provided column mapping.

    Called after a 422 response from /orders/import.
    """
    from services.order_import_service import execute_order_import
    from database import temp_uploads_collection

    org_id = current_user["organization_id"]

    # 1. Retrieve temp upload
    temp_doc = await temp_uploads_collection.find_one({
        "_id": temp_upload_id,
        "organization_id": org_id,
    })
    if not temp_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload temporaneo non trovato o scaduto. Ricarica il file.",
        )

    # 2. Parse the column mapping JSON
    try:
        user_mapping = json.loads(column_mapping)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato mapping non valido.",
        )

    # 3. Decode stored file
    content = base64.b64decode(temp_doc["content_b64"])
    filename = temp_doc["filename"]

    try:
        result = await execute_order_import(
            content=content,
            filename=filename,
            org_id=org_id,
            user_id=current_user["user_id"],
            user_column_mapping=user_mapping,
        )

        # Clean up temp upload
        await temp_uploads_collection.delete_one({"_id": temp_upload_id})

        return result

    except ValueError as e:
        logger.warning("import_orders_with_mapping error: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("import_orders_with_mapping unexpected error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante l'importazione. Riprova più tardi.",
        )
