"""
Order Service — business logic for order lifecycle.

Handles: draft creation, update, confirmation (→ SalesRecords bridge),
cancellation (→ storno SalesRecords), and order numbering.

Design decisions:
  - unit_price (internal/manual): client can override; if omitted, uses product.unit_price.
    This allows the seller to adjust prices per-order (common in B2B PMI).
  - unit_price (storefront): always server-authoritative. Client input is ignored.
    Price resolution: occurrence.price_override > product.unit_price.
  - Snapshots: product_name and sku are captured at creation time.
  - Totals: always server-computed, never trusted from client.
  - Idempotency: confirm/cancel check current status before acting.
    The unique index on (org_id, order_number) prevents duplicate numbering.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from models.order import (
    Order, OrderCreate, OrderUpdate, OrderLineBase,
    OrderStatus, OrderPaymentStatus,
)
from models.common import generate_id, utc_now
from models.dataset import SalesRecord

logger = logging.getLogger(__name__)


def derive_fulfillment(items: list, fulfillment_input: dict = None) -> dict:
    """Derive fulfillment mode + initial status from item composition and customer choice.

    Centralized derivation rule (deterministic, documented):
      1. If ANY item is rental → manual_arrangement (always, no customer choice)
      2. Else if ANY item is physical → customer/admin chooses shipping or local_pickup
      3. Else (only service / event_ticket) → not_required (automatic)

    fulfillment_input can contain: mode, shipping_address, fulfillment_notes
    """
    types = set()
    for item in items:
        # Support both Pydantic model objects and dicts
        if hasattr(item, 'item_type'):
            types.add(item.item_type)
        elif isinstance(item, dict):
            types.add(item.get('item_type', 'physical'))
        else:
            types.add('physical')

    has_rental = 'rental' in types
    has_physical = 'physical' in types

    # Rule 1: rental → manual_arrangement (always)
    if has_rental:
        mode = "manual_arrangement"
    # Rule 2: physical → customer/admin chooses
    elif has_physical:
        mode = (fulfillment_input or {}).get("mode", "shipping")
        if mode not in ("shipping", "local_pickup"):
            mode = "shipping"
    # Rule 3: service/event only → not_required
    else:
        mode = "not_required"

    status = "not_required" if mode == "not_required" else "pending"

    result = {"mode": mode, "status": status}
    if fulfillment_input:
        if mode == "shipping":
            # Structured and free-text coexist intentionally — the backend
            # synthesized `shipping_address` server-side from
            # `shipping_address_details` (see routers/public.py), so
            # email/PDF/admin readers keep working off the legacy string
            # while new clients gain the structured payload.
            if fulfillment_input.get("shipping_address"):
                result["shipping_address"] = fulfillment_input["shipping_address"]
            if fulfillment_input.get("shipping_address_details"):
                result["shipping_address_details"] = fulfillment_input["shipping_address_details"]
        if fulfillment_input.get("fulfillment_notes"):
            result["fulfillment_notes"] = fulfillment_input["fulfillment_notes"]

    return result


async def create_order(
    org_id: str, data: OrderCreate, source: str = "manual",
    payment_intent: str = "none", customer_account_id: str = None,
    fulfillment_input: dict = None, contact_phone: str = None,
    store_id: str = None,
    order_fields_data: dict = None,  # F2 Onda 9 — order-level custom fields
    terms_accepted_at: str = None,   # F4 Onda 11 — T&C acceptance timestamp
) -> dict:
    """Create a draft order with validated FKs and computed snapshots/totals."""
    from repositories import (
        customer_repository,
        product_repository,
        order_repository,
        organization_repository,
    )

    # Validate customer
    customer = await customer_repository.find_by_id(data.customer_id, org_id)
    if not customer:
        raise ValueError(f"Customer '{data.customer_id}' not found")

    # CH compliance v1 — currency is server-authoritative.
    # We derive it from the organisation (with the safe EUR fallback for
    # legacy orgs that never set the field). The currency on `data` —
    # which carries the legacy ``"EUR"`` Pydantic default — is ignored on
    # purpose: a client must not be able to smuggle in a mismatched code.
    from services.currency_service import get_currency_for_org

    org_doc = await organization_repository.find_by_id(org_id)
    order_currency = get_currency_for_org(org_doc or {})

    # Build lines with product snapshots
    lines = []
    # Fase 2 (retreat): contesto della prima riga event_ticket con data —
    # serve per generare il PaymentSchedule (libro mastro) post-insert.
    first_event_ctx = None
    for item in data.items:
        product = await product_repository.find_by_id(item.product_id, org_id)
        if not product:
            raise ValueError(f"Product '{item.product_id}' not found")

        # unit_price resolution:
        #   - storefront: always server-authoritative (ignore client unit_price)
        #   - manual/api:  client can override; if omitted, use product.unit_price
        if source == "storefront":
            unit_price = product.unit_price or 0
        else:
            unit_price = item.unit_price if item.unit_price is not None else (product.unit_price or 0)

        # Occurrence snapshot for event_ticket items
        occurrence_id = None
        occurrence_start_at = None
        occurrence_location = None
        ticket_tier_id = None
        ticket_tier_label = None
        if item.occurrence_id:
            from database import event_occurrences_collection
            occ = await event_occurrences_collection.find_one(
                {"id": item.occurrence_id, "organization_id": org_id},
                {"_id": 0, "start_at": 1, "location": 1, "price_override": 1, "status": 1},
            )
            if occ and occ.get("status") not in ("cancelled", "closed"):
                occurrence_id = item.occurrence_id
                occurrence_start_at = occ.get("start_at")
                occurrence_location = occ.get("location")
                # price_override from occurrence always wins for storefront;
                # for internal orders, only when client didn't set unit_price
                if occ.get("price_override") is not None:
                    if source == "storefront" or item.unit_price is None:
                        unit_price = occ["price_override"]

                # E1: when a tier is requested, its price overrides any
                # occurrence-level price_override — tier pricing is the
                # most specific level. Label snapshot is stored on the
                # line so admin views survive tier rename/delete.
                tier_id_req = getattr(item, "ticket_tier_id", None)
                if tier_id_req:
                    from database import event_ticket_tiers_collection
                    tier_doc = await event_ticket_tiers_collection.find_one(
                        {
                            "id": tier_id_req,
                            "organization_id": org_id,
                            "occurrence_id": item.occurrence_id,
                        },
                        {"_id": 0, "id": 1, "label": 1, "price": 1, "is_active": 1},
                    )
                    if tier_doc and tier_doc.get("is_active", True):
                        ticket_tier_id = tier_doc["id"]
                        ticket_tier_label = tier_doc.get("label")
                        tp = tier_doc.get("price")
                        if tp is not None:
                            if source == "storefront" or item.unit_price is None:
                                unit_price = float(tp)

                # Fase 2 (retreat): snapshot del piano di pagamento del
                # prodotto per lo schedule. Prima riga evento con data vince.
                if occurrence_id and occurrence_start_at and first_event_ctx is None:
                    first_event_ctx = {
                        "occurrence_id": occurrence_id,
                        "start_at": occurrence_start_at,
                        "plan_raw": (getattr(product, "metadata", None) or {}).get("payment_plan"),
                    }

        # Rental duration multiplier: compute from date range + rental_unit
        item_type = getattr(product, 'item_type', None) or 'physical'
        rental_multiplier = 1
        if item_type == 'rental':
            rental_date_from = getattr(item, 'rental_date_from', None)
            rental_date_to = getattr(item, 'rental_date_to', None)
            if rental_date_from:
                try:
                    d_from = date.fromisoformat(rental_date_from)
                    d_to = date.fromisoformat(rental_date_to) if rental_date_to else d_from
                    days = max(1, (d_to - d_from).days + 1)
                    rental_unit = (getattr(product, 'metadata', None) or {}).get('rental_unit', 'giorno')
                    if rental_unit == 'settimana':
                        rental_multiplier = -(-days // 7)  # ceil division
                    elif rental_unit == 'mese':
                        rental_multiplier = -(-days // 30)
                    else:
                        rental_multiplier = days
                except (ValueError, TypeError):
                    rental_multiplier = 1

        base_line_total = round(unit_price * item.quantity * rental_multiplier * (1 - item.discount_pct / 100), 2)

        # F5 Onda 12 — Service option snapshot (analogous to tier snapshot
        # for events). When the customer picked an option, resolve its
        # label + price and lock them onto the line.
        service_option_id = getattr(item, 'service_option_id', None)
        service_option_label = None
        if item_type == "service" and service_option_id:
            try:
                from database import service_options_collection as _soc
                option_doc = await _soc.find_one(
                    {"id": service_option_id, "organization_id": org_id,
                     "product_id": item.product_id},
                    {"_id": 0, "label": 1, "price": 1},
                )
                if option_doc:
                    service_option_label = option_doc.get("label")
                    # Option price wins over product/occurrence default
                    if source == "storefront":
                        unit_price = float(option_doc.get("price") or unit_price)
                    base_line_total = round(
                        unit_price * item.quantity * rental_multiplier
                        * (1 - item.discount_pct / 100), 2,
                    )
            except Exception as exc:
                logger.warning(
                    "create_order: failed to snapshot service option %s: %s",
                    service_option_id, exc,
                )

        # Onda 16 — ProductExtra resolution. Server-authoritative.
        # Fetches active extras for this product, auto-merges mandatory,
        # validates the customer's optional/radio picks, and computes
        # per-extra line totals with flavor-aware multipliers. Snapshot
        # is frozen on OrderLine.extras — subsequent edits to the extra
        # never alter the historical total.
        extras_snapshot: list = []
        extras_total = 0.0
        try:
            from database import product_extras_collection
            from services.pricing import (
                compute_line_total as _compute_with_extras,
                normalize_legacy_service_option,
                PricingError,
            )
            extras_catalog = await product_extras_collection.find(
                {"organization_id": org_id, "product_id": item.product_id,
                 "is_active": True},
                {"_id": 0},
            ).to_list(None)
            if extras_catalog:
                # Back-compat shim — translate legacy scalar service_option_id
                # into radio_picks if the client hasn't sent an explicit one.
                selection = getattr(item, 'extra_selections', None)
                selection_dict = (
                    selection.model_dump() if hasattr(selection, 'model_dump')
                    else (selection or None)
                )
                selection_dict = normalize_legacy_service_option(
                    service_option_id=service_option_id,
                    extras_catalog=extras_catalog,
                    existing_selection=selection_dict,
                )
                pricing_result = _compute_with_extras(
                    unit_price=unit_price,
                    quantity=item.quantity * rental_multiplier,
                    discount_pct=item.discount_pct,
                    extras_catalog=extras_catalog,
                    extras_selection=selection_dict,
                    date_from=getattr(item, 'rental_date_from', None),
                    date_to=getattr(item, 'rental_date_to', None),
                )
                # base stays the pre-existing compute (unit_price * qty * mult
                # * discount); extras_total comes from the pricing helper.
                # We preserve base_line_total already computed above and
                # simply add the extras on top so multi-tier + service_option
                # paths remain source-of-truth for the base portion.
                extras_snapshot = pricing_result.extras
                extras_total = pricing_result.extras_total
        except PricingError as pe:
            # Invalid extras payload → surface as ValueError to the router.
            raise ValueError(f"Extra non valido: {pe.detail}")
        except Exception as exc:
            logger.warning(
                "create_order: extras resolution failed for product %s: %s",
                item.product_id, exc,
            )

        line_total = round(base_line_total + extras_total, 2)

        lines.append(OrderLineBase(
            product_id=item.product_id,
            product_name=product.name,
            sku=product.sku,
            category=product.category,
            item_type=item_type,
            transaction_mode=getattr(product, 'transaction_mode', None) or 'request',
            quantity=item.quantity,
            unit_price=unit_price,
            discount_pct=item.discount_pct,
            line_total=line_total,
            occurrence_id=occurrence_id,
            occurrence_start_at=occurrence_start_at,
            occurrence_location=occurrence_location,
            ticket_tier_id=ticket_tier_id,
            ticket_tier_label=ticket_tier_label,
            service_option_id=service_option_id,
            service_option_label=service_option_label,
            # R4 — persist the custom-request flag so the admin sees it on the
            # order (was previously consumed by the validator and discarded).
            service_custom_request=bool(getattr(item, 'service_custom_request', False)),
            rental_date_from=getattr(item, 'rental_date_from', None),
            rental_date_to=getattr(item, 'rental_date_to', None),
            rental_notes=getattr(item, 'rental_notes', None),
            booking_date=getattr(item, 'booking_date', None),
            booking_start_time=getattr(item, 'booking_start_time', None),
            booking_end_time=getattr(item, 'booking_end_time', None),
            # Onda 17 — cross-day slot end date (None = same-day, preserves
            # historic behaviour for legacy slot products).
            booking_end_date=getattr(item, 'booking_end_date', None),
            attendees=getattr(item, 'attendees', None),  # F1 Onda 8
            extras=extras_snapshot,                       # Onda 16
            extras_total=extras_total,                    # Onda 16
        ))

    subtotal = round(sum(l.line_total for l in lines), 2)

    order = Order(
        organization_id=org_id,
        customer_id=data.customer_id,
        currency=order_currency,
        notes=data.notes,
        due_date=data.due_date,
        order_date=data.order_date or date.today().isoformat(),
        items=lines,
        subtotal=subtotal,
        total=subtotal,  # MVP: no separate tax/shipping
        status=OrderStatus.DRAFT,
        payment_status=OrderPaymentStatus.PENDING,
        payment_intent=payment_intent,
        source=source,
        order_fields_data=order_fields_data or {},  # F2 Onda 9
        terms_accepted_at=terms_accepted_at,        # F4 Onda 11
    )

    # mode='json' serialises enums to strings and datetimes to ISO strings,
    # which is required for MongoDB (motor cannot serialise Python enum objects).
    doc = order.model_dump(mode="json")
    doc["customer_name"] = customer.name
    if store_id:
        doc["store_id"] = store_id
    # v9.0: link to customer account if authenticated (null = guest order)
    if customer_account_id:
        doc["customer_account_id"] = customer_account_id
    # v10.0: derive fulfillment from item composition + customer choice
    fulfillment_doc = derive_fulfillment(lines, fulfillment_input)

    # Shipping: compute and snapshot the shipping option on the order, then
    # fold shipping_cost into Order.total. Call site is here (not inside
    # derive_fulfillment) because the shipping lookup is async and
    # derive_fulfillment is intentionally pure/sync.
    try:
        from services.shipping_service import compute_shipping_for_order
        shipping_snap = await compute_shipping_for_order(
            org_id=org_id,
            store_id=store_id,
            option_id=(fulfillment_input or {}).get("shipping_option_id"),
            mode=fulfillment_doc.get("mode"),
            items=[l.model_dump() for l in lines],
        )
    except ValueError as exc:
        # Translate service-level validation errors ("shipping_option_required:...")
        # into a ValueError the router maps to HTTP 400. Preserves the code
        # prefix for frontend-side i18n routing.
        raise ValueError(str(exc))

    # Merge snapshot into the embedded fulfillment dict.
    fulfillment_doc["shipping_option_id"] = shipping_snap["shipping_option_id"]
    fulfillment_doc["shipping_option_label"] = shipping_snap["shipping_option_label"]
    fulfillment_doc["shipping_cost"] = shipping_snap["shipping_cost"]

    # Recompute the order total to include shipping. subtotal is already
    # computed above; discount_total is unused in this code path today
    # (coupons live on the line level) so we read it from the doc safely.
    shipping_cost = float(shipping_snap["shipping_cost"] or 0)
    doc["total"] = round(float(doc.get("total") or subtotal) + shipping_cost, 2)
    doc["fulfillment"] = fulfillment_doc
    if contact_phone:
        doc["contact_phone"] = contact_phone
    # Onda 17 — rental+slot: reserve the slot atomically BEFORE inserting the
    # order so a pending request holds the calendar entry until admin confirms
    # or the order is cancelled. Other item types keep their existing
    # semantics (reserved only on confirm). Rental+slot behaves this way
    # because a request-mode meeting-room or court booking typically sits in
    # draft for hours before the merchant reviews — during that window a
    # second customer MUST NOT be able to overlap.
    #
    # Reservation happens pre-insert so a conflict raises without leaving a
    # zombie draft behind. The atomic guard uses doc["id"] as reference; all
    # laid-down blocks are released before the raise if any line fails.
    slot_lines_reserved = False
    for line in doc.get("items", []):
        if line.get("item_type") != "rental":
            continue
        bd = line.get("booking_date")
        bs = line.get("booking_start_time")
        be = line.get("booking_end_time")
        if not (bd and bs and be):
            continue
        bd_end = line.get("booking_end_date") or bd
        from services.booking_availability import (
            try_reserve_booking_slot_range, release_booking_slot,
        )
        ok, res_reason, _conflict = await try_reserve_booking_slot_range(
            order_id=doc["id"],
            org_id=org_id,
            product_id=line.get("product_id"),
            date_from=bd,
            time_from=bs,
            date_to=bd_end,
            time_to=be,
            note=f"Affitto (draft): {line.get('product_name', '')}",
            scope="rentals",
        )
        if not ok:
            # Rollback any blocks already laid down for this order in a
            # previous iteration (defensive — usually single-line).
            await release_booking_slot(order_id=doc["id"], org_id=org_id)
            raise ValueError(
                "Slot non più disponibile: qualcun altro ha appena prenotato "
                "questo orario. Ricarica e scegli un altro slot."
            )
        slot_lines_reserved = True

    try:
        await order_repository.insert(doc)
    except Exception:
        # If the insert fails after we've already locked slots, release them.
        if slot_lines_reserved:
            from services.booking_availability import release_booking_slot
            await release_booking_slot(order_id=doc["id"], org_id=org_id)
        raise

    logger.info("order_service: created draft order %s for org=%s", order.id, org_id)

    # Fase 2 (retreat): l'ordine-ritiro nasce col suo libro mastro pagamenti.
    # S1: best-effort (lo schedule non guida ancora gli incassi); da S2, con
    # il checkout caparra, un fallimento qui diventa bloccante.
    if first_event_ctx:
        try:
            from services.payment_schedule_service import create_schedule_for_new_order
            await create_schedule_for_new_order(doc, org_id, first_event_ctx)
        except Exception as exc:
            logger.error(
                "payment schedule creation failed for order %s: %s",
                doc.get("id"), exc,
            )

    return doc


async def update_order(org_id: str, order_id: str, data: OrderUpdate) -> dict:
    """Update a draft order. Only drafts can be updated."""
    from repositories import order_repository, customer_repository, product_repository

    existing = await order_repository.find_one(order_id, org_id)
    if not existing:
        raise ValueError("Order not found")
    if existing["status"] != OrderStatus.DRAFT:
        raise ValueError("Only draft orders can be updated")

    updates = data.model_dump(exclude_unset=True)
    now = utc_now()

    # If customer changed, validate
    if "customer_id" in updates:
        customer = await customer_repository.find_by_id(updates["customer_id"], org_id)
        if not customer:
            raise ValueError(f"Customer '{updates['customer_id']}' not found")
        updates["customer_name"] = customer.name

    # If items changed, rebuild snapshots and totals
    if "items" in updates:
        raw_items = updates.pop("items")
        lines = []
        for item_data in raw_items:
            product = await product_repository.find_by_id(item_data["product_id"], org_id)
            if not product:
                raise ValueError(f"Product '{item_data['product_id']}' not found")

            unit_price = item_data.get("unit_price") if item_data.get("unit_price") is not None else (product.unit_price or 0)
            discount_pct = item_data.get("discount_pct", 0)
            quantity = item_data["quantity"]
            line_total = round(unit_price * quantity * (1 - discount_pct / 100), 2)

            lines.append(OrderLineBase(
                product_id=item_data["product_id"],
                product_name=product.name,
                sku=product.sku,
                category=product.category,
                quantity=quantity,
                unit_price=unit_price,
                discount_pct=discount_pct,
                line_total=line_total,
            ).model_dump())

        updates["items"] = lines
        updates["subtotal"] = round(sum(l["line_total"] for l in lines), 2)
        updates["total"] = updates["subtotal"]

    updates["updated_at"] = now
    ok = await order_repository.update(order_id, org_id, updates)
    if not ok:
        raise ValueError("Order not found")

    return await order_repository.find_one(order_id, org_id)


async def confirm_order(org_id: str, order_id: str, skip_payment_check: bool = False) -> dict:
    """Confirm a draft order: assign order_number and generate SalesRecords.

    Idempotent: if already confirmed, returns the order without side effects.
    Delegates eligibility check to commerce_rules.can_confirm_order().
    """
    from repositories import order_repository
    from services.commerce_rules import can_confirm_order as check_confirmable

    order = await order_repository.find_one(order_id, org_id)
    if not order:
        raise ValueError("Order not found")

    # Idempotency: already confirmed → no-op
    if order["status"] in (OrderStatus.CONFIRMED, OrderStatus.COMPLETED):
        return order

    # Centralized eligibility check (payment gating, cancelled guard)
    can_confirm, reason = check_confirmable(order, skip_payment_check=skip_payment_check)
    if not can_confirm:
        messages = {
            "order_cancelled": "Impossibile confermare un ordine annullato.",
            "payment_not_collected": "Pagamento non ancora incassato. Conferma non consentita per ordini con pagamento diretto.",
        }
        raise ValueError(messages.get(reason, f"Conferma non consentita: {reason}"))

    # Assign order number (retry on collision from concurrent confirms)
    now = utc_now()
    order_number = None
    for _attempt in range(3):
        order_number = await order_repository.get_next_order_number(org_id)
        updates = {
            "status": OrderStatus.CONFIRMED.value,
            "order_number": order_number,
            "updated_at": now,
        }
        try:
            await order_repository.update(order_id, org_id, updates)
            break
        except Exception as e:
            if "duplicate" in str(e).lower() or "E11000" in str(e):
                logger.warning("order_service: order_number %s collision, retrying (attempt %d)", order_number, _attempt + 1)
                if _attempt == 2:
                    raise ValueError(f"Impossibile assegnare numero ordine dopo 3 tentativi")
            else:
                raise

    # Stock deduction (P10): delegated to stock_service. Physical
    # products with stock tracking get an atomic decrement; untracked
    # products are a no-op success. Reason codes surface in logs for
    # ops visibility.
    try:
        from services.stock_service import try_decrement_stock
        for item in order.get("items", []):
            pid = item.get("product_id")
            try:
                qty = int(item.get("quantity", 1))
            except Exception:
                qty = 0
            if pid and qty > 0:
                ok, reason, _rem = await try_decrement_stock(
                    order_id=order_id, org_id=org_id,
                    product_id=pid, qty=qty,
                )
                if not ok:
                    logger.warning(
                        "stock: deduction failed for order %s product %s qty=%d reason=%s",
                        order_id, pid, qty, reason,
                    )
    except Exception as e:
        logger.warning("stock: deduction failed for order %s: %s", order_id, e)

    # Bridge: generate SalesRecords
    await _generate_sales_records(org_id, order, order_number)

    # Trigger post-upload hooks so analytics refresh
    await _trigger_module_hooks(org_id)

    # Onda 14 — explicit customer metrics refresh on confirm.
    # Belt-and-suspenders: _trigger_module_hooks calls customers_light's
    # post_upload_hook if the module is registered in the running process,
    # but this guarantees metrics stay fresh even in unusual import
    # orders (tests, scripts, worker contexts). Fire-and-forget:
    # failure is logged, never blocks confirmation.
    await _refresh_customer_metrics_best_effort(org_id)
    await _refresh_product_metrics_best_effort(org_id)

    order.update(updates)
    logger.info("order_service: confirmed order %s (%s) for org=%s", order_id, order_number, org_id)

    # v12.0: auto-block calendar slots for event/booking items.
    # Moved BEFORE the confirmation email (E4) so tier_id capacity
    # reservation is stable by the time we issue individual tickets.
    try:
        await _sync_calendar_blocks(org_id, order)
    except Exception as e:
        logger.warning("order_service: calendar sync failed: %s", e)

    # E4: issue one ticket per seat for every event_ticket line. Must
    # run BEFORE the confirmation email so the email renderer can
    # embed the per-seat codes + QR. Idempotent — safe on webhook
    # retries. Failure here is logged but does not roll back the
    # confirmation; tickets can be re-issued manually.
    try:
        from services.ticket_service import issue_tickets_for_order
        issued = await issue_tickets_for_order(order, org_id)
        if issued:
            # Stash the list on the in-memory order dict so the
            # confirmation email renderer can embed the codes without
            # a second DB round-trip.
            order["_issued_tickets"] = issued
    except Exception as e:
        logger.warning("order_service: ticket issuance failed for order %s: %s", order.get("id"), e)

    # Onda 14: issue one booking per seat for every service line with a
    # booked slot. Analog of ticket issuance for consulenze. Must run
    # BEFORE the confirmation email so the email renderer can embed the
    # per-booking codes + access_token landing URLs. Idempotent.
    try:
        from services.booking_service import issue_bookings_for_order
        bookings = await issue_bookings_for_order(order, org_id)
        if bookings:
            order["_issued_bookings"] = bookings
    except Exception as e:
        logger.warning("order_service: booking issuance failed for order %s: %s", order.get("id"), e)

    # Onda 16: issue one reservation per rental/booking line. Unified
    # over both flavors (range + slot). Idempotent per
    # (order_id, order_line_index). Runs AFTER tickets + bookings so
    # confirmation email can embed reservation links alongside them.
    try:
        from services.issued_reservation_service import issue_for_order as issue_reservations
        reservations = await issue_reservations(order, org_id)
        if reservations:
            order["_issued_reservations"] = reservations
    except Exception as e:
        logger.warning("order_service: reservation issuance failed for order %s: %s", order.get("id"), e)

    # Release 3 (Digital): issue one IssuedDownload per digital line.
    # Idempotent per (order_id, order_line_index). Runs after the other
    # issuances so the confirmation email renderer can embed download
    # links alongside tickets/bookings/reservations in one pass.
    try:
        from services.issued_download_service import issue_for_order as issue_downloads
        downloads = await issue_downloads(order, org_id)
        if downloads:
            order["_issued_downloads"] = downloads
    except Exception as e:
        logger.warning("order_service: download issuance failed for order %s: %s", order.get("id"), e)

    # Release 4 (Courses): issue one IssuedCourseAccess per course line.
    # Idempotent per (order_id, order_line_index). Resolves the Course
    # via product.metadata.course_id and snapshots the access policy on
    # the enrollment row. Runs here so the confirmation email (Step 8)
    # can embed the "My courses" links alongside downloads/tickets.
    try:
        from services.issued_course_access_service import issue_for_order as issue_course_accesses
        course_accesses = await issue_course_accesses(order, org_id)
        if course_accesses:
            order["_issued_course_accesses"] = course_accesses
    except Exception as e:
        logger.warning("order_service: course enrollment issuance failed for order %s: %s", order.get("id"), e)

    # v10.1: best-effort customer email (with E4 ticket payload when available).
    try:
        from services.order_email_service import notify_customer_order_confirmed
        await notify_customer_order_confirmed(order, org_id)
    except Exception as e:
        logger.warning("order_service: confirmed email failed: %s", e)

    # F1 Onda 8 — send one personal email per holder whose email differs
    # from customer_email. Guest holders get their own link; the main
    # customer stays on the summary email above. Gathered under a
    # semaphore to avoid SMTP provider throttling. Failure is logged but
    # never blocks confirm (the order is still confirmed).
    try:
        from services.event_email_service import send_individual_tickets_for_order
        await send_individual_tickets_for_order(order, org_id)
    except Exception as e:
        logger.warning(
            "order_service: individual ticket delivery failed for order %s: %s",
            order.get("id"), e,
        )

    return order


async def _sync_calendar_blocks(org_id: str, order: dict):
    """Create blocked_slots for confirmed event/booking order items.

    When an order with event_ticket items (with occurrence dates) is confirmed,
    block those time slots in the calendar.

    Deduplication for event_ticket
    --------------------------------
    A single order may carry N event_ticket lines for the same occurrence
    (one per seat). Without aggregation each line would feed the generic
    insert at the end of this function, and although that block has a
    pre-flight `find_one` idempotency check, two concerns made it
    insufficient and produced visible duplicates in the day-detail panel:

      1. The check was not atomic: `find_one` + `insert_one` leaves a
         race window. Two confirms processing the same order in flight
         (retry, webhook redelivery) could both see "no row" and both
         insert.
      2. Lines for the same occurrence still entered the loop one-by-one
         and even within the same task, the early `find_one` runs
         BEFORE the prior iteration's insert completes when called via
         await in tight succession (every line opens its own driver
         round-trip; the cursor doesn't observe sibling writes from the
         same task between awaits in a way that's guaranteed without a
         server-side upsert).

    The fix below pre-aggregates event_ticket items by occurrence so
    only one entry reaches the insert step per occurrence, and the
    insert itself uses find_one_and_update with upsert=True keyed on
    (org, reference_id, date, start_time) so even concurrent writers
    converge on a single document.
    """
    from database import blocked_slots_collection
    from models.common import generate_id as gen_id

    # ── Pre-aggregate event_ticket items by occurrence ─────────────────
    # Each tuple key represents one logical "calendar block" for this
    # order. Multiple seats on the same occurrence collapse into one
    # entry; different occurrences (or different products) stay
    # distinct as expected.
    seen_event_keys: set[tuple] = set()

    for item in order.get("items", []):
        item_type = item.get("item_type")
        item_product_id = item.get("product_id")  # for per-product calendar isolation
        slot_date = slot_start = slot_end = reason = note = None

        if item_type == "event_ticket":
            # P7: atomic seat reservation against occurrence capacity.
            # E1: when the order line has a ticket_tier_id, the call
            # delegates to tier_capacity.try_reserve_with_tier which
            # decrements BOTH tier and occurrence counters atomically
            # (with compensating rollback on occurrence failure).
            occ_id = item.get("occurrence_id")
            tier_id = item.get("ticket_tier_id")  # E1: None for mono-tier
            qty = int(item.get("quantity", 1) or 1)
            if occ_id and qty > 0:
                from services.event_capacity import try_reserve_event_seats
                try:
                    ok, cap_reason, _occ = await try_reserve_event_seats(
                        order_id=order["id"],
                        org_id=org_id,
                        occurrence_id=occ_id,
                        qty=qty,
                        tier_id=tier_id,
                    )
                    if not ok:
                        logger.warning(
                            "calendar_sync: event capacity reservation failed for order=%s occ=%s tier=%s qty=%s reason=%s",
                            order["id"], occ_id, tier_id, qty, cap_reason,
                        )
                except Exception as exc:
                    logger.warning(
                        "calendar_sync: event capacity reservation raised for order=%s: %s",
                        order["id"], exc,
                    )

            occ_start = item.get("occurrence_start_at")
            if not occ_start:
                continue
            try:
                dt = datetime.fromisoformat(occ_start)
                slot_date = dt.strftime("%Y-%m-%d")
                slot_start = dt.strftime("%H:%M")
                slot_end = (dt + timedelta(hours=2)).strftime("%H:%M")
                reason = "event"
                note = f"Evento: {item.get('product_name', '')}"
            except Exception:
                continue

            # Dedup: skip subsequent ticket lines for the same occurrence.
            # The seat-count is already represented in event_capacity's
            # reserved_seats counter; the calendar block is purely a
            # presence marker ("the merchant is busy at this time"), not
            # a per-ticket record.
            event_key = (
                item.get("occurrence_id") or item_product_id,
                slot_date, slot_start, slot_end,
            )
            if event_key in seen_event_keys:
                continue
            seen_event_keys.add(event_key)

        elif item_type == "booking" or item_type == "service":
            # F5 Onda 12 — services riusano la stessa atomic primitive di
            # booking (try_reserve_booking_slot). La differenza è solo
            # l'item_type: per una service line il cliente ha scelto
            # uno slot dal picker, per una booking line lo stesso.
            # Entrambe finiscono in blocked_slots con reason="booking",
            # ma con calendar_type diverso per la UI admin.
            slot_date = item.get("booking_date")
            slot_start = item.get("booking_start_time")
            slot_end = item.get("booking_end_time")
            if not all([slot_date, slot_start, slot_end]):
                continue
            # P5: use the atomic reservation primitive instead of the
            # generic insert below. This prevents two confirmed orders
            # from double-booking the same window even under hot race.
            from services.booking_availability import try_reserve_booking_slot
            noun = "Servizio" if item_type == "service" else "Prenotazione"
            try:
                ok, res_reason, _conflict = await try_reserve_booking_slot(
                    order_id=order["id"],
                    org_id=org_id,
                    product_id=item_product_id,
                    date=slot_date,
                    start_time=slot_start,
                    end_time=slot_end,
                    note=f"{noun}: {item.get('product_name', '')}",
                )
                if not ok:
                    logger.warning(
                        "calendar_sync: %s reservation failed for order=%s slot=%s %s-%s reason=%s",
                        item_type, order["id"], slot_date, slot_start, slot_end, res_reason,
                    )
                elif item_type == "service":
                    # A5 (Onda 12) — tag the just-created blocked_slot with
                    # calendar_type="service" for UI coloring. try_reserve_
                    # booking_slot writes with reason="booking", so the slot
                    # record exists; we patch its metadata.
                    from database import blocked_slots_collection
                    await blocked_slots_collection.update_many(
                        {
                            "organization_id": org_id,
                            "reference_id": order["id"],
                            "date": slot_date,
                            "start_time": slot_start,
                            "end_time": slot_end,
                        },
                        {"$set": {"scope": "agenda", "calendar_type": "service"}},
                    )
            except Exception as exc:
                logger.warning(
                    "calendar_sync: %s reservation raised for order=%s: %s",
                    item_type, order["id"], exc,
                )
            continue  # handled in-place — skip the generic insert below

        elif item_type == "rental":
            # Onda 17 — rental+flavor=slot path (variable duration, cross-day):
            # when the line carries booking_date/start/end (slot flavor), we
            # reuse the booking atomic primitive `try_reserve_booking_slot_range`
            # so cross-day slots materialize as N one-day blocks with the same
            # order_id reference (release-on-cancel stays atomic).
            slot_date = item.get("booking_date")
            slot_start = item.get("booking_start_time")
            slot_end = item.get("booking_end_time")
            if slot_date and slot_start and slot_end:
                slot_date_end = item.get("booking_end_date") or slot_date
                product_name = item.get("product_name", "")
                from services.booking_availability import try_reserve_booking_slot_range
                try:
                    ok, res_reason, _conflict = await try_reserve_booking_slot_range(
                        order_id=order["id"],
                        org_id=org_id,
                        product_id=item_product_id,
                        date_from=slot_date,
                        time_from=slot_start,
                        date_to=slot_date_end,
                        time_to=slot_end,
                        note=f"Affitto: {product_name}",
                        # Affitti vanno nella tab Rentals del calendario admin,
                        # non in Agenda (dove vivono appuntamenti consulenza).
                        scope="rentals",
                    )
                    if not ok:
                        logger.warning(
                            "calendar_sync: rental-slot reservation failed for order=%s %s %s-%s → %s %s reason=%s",
                            order["id"], slot_date, slot_start, slot_end,
                            slot_date_end, slot_end, res_reason,
                        )
                    else:
                        logger.info(
                            "calendar_sync: rental-slot reservation %s %s %s → %s %s product=%s for order %s",
                            res_reason, slot_date, slot_start, slot_date_end, slot_end,
                            item_product_id, order["id"],
                        )
                except Exception as e:
                    logger.warning(
                        "calendar_sync: rental-slot reservation raised for %s: %s",
                        product_name, e,
                    )
                continue

            # P8: atomic rental range reservation. Replaces the previous
            # day-by-day insert loop. The primitive upserts per day
            # keyed on (org, product, date, reason=rental) — identical
            # atomic strategy to P5/P7. On any-day conflict, every day
            # this reservation just inserted is rolled back (never
            # touches other orders' rows).
            date_from = item.get("rental_date_from")
            if not date_from:
                continue
            date_to = item.get("rental_date_to") or date_from
            product_name = item.get("product_name", "")
            from services.rental_availability import try_reserve_rental_range
            try:
                ok, res_reason, _conflict = await try_reserve_rental_range(
                    order_id=order["id"],
                    org_id=org_id,
                    product_id=item_product_id,
                    date_from=date_from,
                    date_to=date_to,
                    note=product_name,
                )
                if not ok:
                    logger.warning(
                        "calendar_sync: rental reservation failed for order=%s %s..%s reason=%s",
                        order["id"], date_from, date_to, res_reason,
                    )
                else:
                    logger.info(
                        "calendar_sync: rental reservation %s %s..%s product=%s for order %s",
                        res_reason, date_from, date_to, item_product_id, order["id"],
                    )
            except Exception as e:
                logger.warning("calendar_sync: rental reservation raised for %s: %s", product_name, e)
            continue  # skip the single-slot logic below

        else:
            continue

        try:
            # Atomic upsert keyed on (org, reference_id, date, start_time).
            # Replaces the previous `find_one` + `insert_one` pair which
            # left a race window: two concurrent confirms (retry, webhook
            # redelivery, or several event_ticket lines awaited in tight
            # succession) could both see "no row" and both insert.
            #
            # `$setOnInsert` ensures we don't overwrite an existing row's
            # fields if the slot is already there for this order (e.g. an
            # earlier partial confirm). The filter is the natural unique
            # key — same shape as services/booking_availability.py uses.
            from pymongo import ReturnDocument
            slot_filter = {
                "organization_id": org_id,
                "reference_id": order["id"],
                "date": slot_date,
                "start_time": slot_start,
            }
            new_doc = {
                "id": gen_id(),
                "organization_id": org_id,
                "store_id": None,
                "product_id": item_product_id,
                "date": slot_date,
                "start_time": slot_start,
                "end_time": slot_end,
                "reason": reason,
                "reference_id": order["id"],
                "note": note,
                # A5 (Onda 12) — scope + calendar_type espliciti.
                # scope="agenda" → appare nella tab "Agenda" del calendario
                # admin accanto a booking/personal; distinto dai rental.
                # calendar_type consente alla UI di colorare diversamente
                # event vs booking vs service.
                "scope": "agenda",
                "calendar_type": "event",
                "created_at": utc_now(),
            }
            before = await blocked_slots_collection.find_one_and_update(
                slot_filter,
                {"$setOnInsert": new_doc},
                upsert=True,
                return_document=ReturnDocument.BEFORE,
                projection={"_id": 0, "id": 1},
            )
            if before is None:
                logger.info(
                    "calendar_sync: blocked %s %s-%s (%s) product=%s for order %s",
                    slot_date, slot_start, slot_end, reason, item_product_id, order["id"],
                )
            else:
                logger.debug(
                    "calendar_sync: dedup hit for order=%s slot=%s %s-%s (already blocked)",
                    order["id"], slot_date, slot_start, slot_end,
                )
        except Exception as e:
            logger.warning("calendar_sync: failed for item %s: %s", item.get("product_name"), e)


async def cancel_order(org_id: str, order_id: str) -> dict:
    """Cancel an order. If it was confirmed, generate storno SalesRecords.

    Idempotent: if already cancelled, returns the order without side effects.
    Delegates eligibility check to commerce_rules.can_cancel_order().
    """
    from repositories import order_repository
    from services.commerce_rules import can_cancel_order as check_cancellable

    order = await order_repository.find_one(order_id, org_id)
    if not order:
        raise ValueError("Order not found")

    # Idempotency: already cancelled → no-op
    if order["status"] == OrderStatus.CANCELLED:
        return order

    can_cancel, reason = check_cancellable(order)
    if not can_cancel:
        messages = {
            "order_completed": "Impossibile annullare un ordine completato.",
            "already_cancelled": "Ordine già annullato.",
        }
        raise ValueError(messages.get(reason, f"Annullamento non consentito: {reason}"))

    was_confirmed = order["status"] == OrderStatus.CONFIRMED

    now = utc_now()
    updates = {
        "status": OrderStatus.CANCELLED.value,
        "updated_at": now,
    }
    await order_repository.update(order_id, org_id, updates)

    # Stock restoration (P10): delegated to stock_service.
    if was_confirmed:
        try:
            from services.stock_service import restore_stock_for_order
            await restore_stock_for_order(order_id, org_id, order.get("items", []))
        except Exception as e:
            logger.warning("stock: restoration failed for order %s: %s", order_id, e)

    # Storno: generate negative SalesRecords if order was confirmed
    if was_confirmed:
        await _generate_storno_records(org_id, order)

        await _trigger_module_hooks(org_id)

        # Onda 14 — keep customer metrics in sync after a cancellation.
        # Same rationale as the confirm path: belt-and-suspenders so
        # metrics reflect the storno even if module registration is
        # incomplete in the caller's process.
        await _refresh_customer_metrics_best_effort(org_id)
    await _refresh_product_metrics_best_effort(org_id)

    order.update(updates)
    logger.info("order_service: cancelled order %s for org=%s (storno=%s)", order_id, org_id, was_confirmed)

    # v10.1: best-effort customer email
    try:
        from services.order_email_service import notify_customer_order_cancelled
        await notify_customer_order_cancelled(order, org_id)
    except Exception as e:
        logger.warning("order_service: cancelled email failed: %s", e)

    # v12.0: release calendar blocks on cancellation
    try:
        from database import blocked_slots_collection
        result = await blocked_slots_collection.delete_many(
            {"organization_id": org_id, "reference_id": order_id},
        )
        if result.deleted_count > 0:
            logger.info("calendar_sync: released %d blocks for cancelled order %s", result.deleted_count, order_id)
    except Exception as e:
        logger.warning("order_service: calendar unblock failed: %s", e)

    # E4: void any tickets issued for this order. Never deletes — rows
    # stay with status="voided" for audit. Safe to call even when no
    # tickets exist.
    try:
        from services.ticket_service import void_tickets_for_order
        voided = await void_tickets_for_order(order_id, org_id)
        if voided:
            logger.info("ticket_service: voided %d tickets for cancelled order %s", voided, order_id)
    except Exception as e:
        logger.warning("order_service: ticket void failed for order %s: %s", order_id, e)

    # Onda 14: cancel any service bookings issued for this order. Mirrors
    # the ticket void pattern — rows stay with status="cancelled" for audit.
    try:
        from services.booking_service import void_bookings_for_order
        cancelled_bookings = await void_bookings_for_order(order_id, org_id)
        if cancelled_bookings:
            logger.info(
                "booking_service: cancelled %d bookings for cancelled order %s",
                cancelled_bookings, order_id,
            )
    except Exception as e:
        logger.warning("order_service: booking cancel failed for order %s: %s", order_id, e)

    # Onda 16: cancel any reservations (rental / slot) issued for this order.
    # Mirrors the booking void pattern; preserves audit trail.
    try:
        from services.issued_reservation_service import release_for_order as release_reservations
        cancelled_res = await release_reservations(order_id, org_id)
        if cancelled_res:
            logger.info(
                "issued_reservation_service: cancelled %d reservations for order %s",
                cancelled_res, order_id,
            )
    except Exception as e:
        logger.warning("order_service: reservation cancel failed for order %s: %s", order_id, e)

    # Release 3 (Digital): cancel any IssuedDownload for this order. Token
    # endpoint responds 404 on cancelled rows so the file stops serving.
    try:
        from services.issued_download_service import release_for_order as release_downloads
        cancelled_dl = await release_downloads(order_id, org_id)
        if cancelled_dl:
            logger.info(
                "issued_download_service: cancelled %d downloads for order %s",
                cancelled_dl, order_id,
            )
    except Exception as e:
        logger.warning("order_service: download cancel failed for order %s: %s", order_id, e)

    # Release 4 (Courses): revoke any IssuedCourseAccess emitted by this
    # order. The player endpoint (Step 7) checks `revoked_at` and refuses
    # to mint new signed Bunny URLs, effectively killing playback on the
    # next request. Enrollment rows are preserved for audit.
    try:
        from services.issued_course_access_service import revoke_for_order as revoke_course_accesses
        revoked_ce = await revoke_course_accesses(order_id, org_id, reason="order_cancelled")
        if revoked_ce:
            logger.info(
                "issued_course_access_service: revoked %d enrollment(s) for order %s",
                revoked_ce, order_id,
            )
    except Exception as e:
        logger.warning("order_service: course enrollment revoke failed for order %s: %s", order_id, e)

    # P7+E1: release event_ticket seat reservations on cancellation.
    # Isolated from calendar unblock: event_ticket items may have both
    # a seat reservation (capacity) and a blocked_slot (calendar); these
    # are independent and each release flow must succeed regardless of
    # the other.
    #
    # E1 contract: tier-level release runs FIRST (decrements tier counters)
    # because release_event_seats (the occurrence-level release) is the
    # one that DELETES the idempotency rows — so we must read the tier_ids
    # from them before the occurrence release wipes the rows.
    try:
        from services.tier_capacity import release_tier_seats
        from services.event_capacity import release_event_seats
        # Step 1 — decrement tier counters (reads idempotency rows).
        tier_released = await release_tier_seats(order_id, org_id)
        # Step 2 — decrement occurrence counters + delete idempotency rows.
        released = await release_event_seats(order_id, org_id)
        if released > 0 or tier_released > 0:
            logger.info(
                "event_capacity: released %d seat + %d tier reservations for cancelled order %s",
                released, tier_released, order_id,
            )
    except Exception as e:
        logger.warning("order_service: event seat release failed: %s", e)

    # R5: release coupon consumption (global current_uses decrement + per-
    # customer redemption cleanup) so a cancelled order doesn't burn the
    # coupon. Best-effort; uses order.coupon_code → covers guest orders too.
    try:
        if order.get("coupon_code"):
            from routers.coupons import release_coupon_for_order
            released = await release_coupon_for_order(org_id, order)
            if released:
                logger.info(
                    "coupons: released coupon %s for cancelled order %s",
                    order.get("coupon_code"), order_id,
                )
    except Exception as e:
        logger.warning("order_service: coupon release failed for order %s: %s", order_id, e)

    return order


async def complete_order(org_id: str, order_id: str) -> dict:
    """Mark a confirmed order as completed (paid/fulfilled).

    Delegates eligibility check to commerce_rules.can_complete_order().
    """
    from repositories import order_repository
    from services.commerce_rules import can_complete_order as check_completable

    order = await order_repository.find_one(order_id, org_id)
    if not order:
        raise ValueError("Order not found")

    can_complete, reason = check_completable(order)
    if not can_complete:
        raise ValueError(f"Completamento non consentito: ordine in stato '{order.get('status', '?')}'.")

    now = utc_now()
    updates = {
        "status": OrderStatus.COMPLETED.value,
        "payment_status": OrderPaymentStatus.PAID.value,
        "updated_at": now,
    }
    await order_repository.update(order_id, org_id, updates)

    # Sync payment_status to linked SalesRecords
    from services.payment_sync import sync_payment_to_sales
    await sync_payment_to_sales(org_id, order_id, OrderPaymentStatus.PAID.value)

    order.update(updates)
    logger.info("order_service: completed order %s for org=%s", order_id, org_id)
    return order


# ── Payment Status Management ─────────────────────────────────────────────

async def mark_order_paid(org_id: str, order_id: str) -> dict:
    """Mark an order as paid without completing it. For manual payment registration."""
    from repositories import order_repository
    from services.payment_sync import sync_payment_to_sales

    order = await order_repository.find_one(order_id, org_id)
    if not order:
        raise ValueError("Order not found")

    status = order.get("status", "draft")
    if status not in ("confirmed", "completed"):
        raise ValueError(f"Pagamento manuale non consentito per ordini in stato '{status}'")
    if order.get("payment_status") == "paid":
        return order  # idempotent

    now = utc_now()
    updates = {"payment_status": OrderPaymentStatus.PAID.value, "updated_at": now}
    await order_repository.update(order_id, org_id, updates)
    await sync_payment_to_sales(org_id, order_id, OrderPaymentStatus.PAID.value)

    order.update(updates)
    logger.info("order_service: marked paid order %s for org=%s", order_id, org_id)
    return order


async def settle_order_manual(
    org_id: str,
    order_id: str,
    *,
    actor: str,
    note: str,
    scope: str = "full",          # "full" | "deposit"
) -> dict:
    """Consolidamento WS-1.1 — "il cliente ha pagato fuori piattaforma".

    IL caso reale italiano: prenotazione online (ordine draft + link Stripe)
    ma pagamento con bonifico. Prima di questa funzione l'ordine restava in
    limbo (mark-paid rifiuta i draft, skip_payment_check non era esposto).

    In UN'azione, con nota obbligatoria e attore tracciato:
      1. se draft → conferma con skip_payment_check=True (posti riservati,
         biglietti emessi, email cliente — la cascata esistente);
      2. payment_intent → collected (il link Stripe non serve più);
      3. schedule: righe pagabili → paid_manual (scope "deposit" = solo la
         prima riga: bonifico della caparra, il saldo prosegue col flusso
         normale di promemoria; "full" = tutte);
      4. scope full → payment_status=paid + sync SalesRecords.

    Fee piattaforma NON applicata (incasso fuori Stripe — regola di
    business della Fase 2).
    """
    from repositories import order_repository
    from services.payment_sync import sync_payment_to_sales

    if not note or not note.strip():
        raise ValueError("La nota è obbligatoria (es. 'bonifico ricevuto il 5/7')")
    if scope not in ("full", "deposit"):
        raise ValueError("scope deve essere 'full' o 'deposit'")

    order = await order_repository.find_one(order_id, org_id)
    if not order:
        raise ValueError("Order not found")
    if order.get("status") == "cancelled":
        raise ValueError("Ordine annullato: non registrabile come incassato")

    note = note.strip()

    # 1. Conferma (se serve) — riserva posti, emette biglietti, email.
    if order.get("status") == "draft":
        order = await confirm_order(org_id, order_id, skip_payment_check=True)

    # 2. Il link Stripe non deve più incassare nulla.
    now = utc_now()
    await order_repository.update(order_id, org_id, {
        "payment_intent": "collected",
        "updated_at": now,
    })

    # 3. Righe schedule → paid_manual (quando esiste un piano).
    settled_rows = []
    try:
        from models.payment_schedule import RowStatus
        from services.payment_schedule_service import (
            InvalidTransition, apply_row_transition, get_schedule_for_order,
        )
        schedule = await get_schedule_for_order(order_id, org_id)
        if schedule:
            payable = {"pending", "processing", "overdue", "at_risk"}
            for row in list(schedule.get("rows") or []):
                if row.get("status") not in payable:
                    continue
                if scope == "deposit" and row.get("seq", 0) != 0:
                    continue
                try:
                    schedule = await apply_row_transition(
                        schedule, row["seq"], RowStatus.PAID_MANUAL,
                        actor=actor, action="row_paid_manual",
                        row_updates={"manual_note": note},
                        detail={"via": "settle_order_manual", "scope": scope},
                    )
                    settled_rows.append(row["seq"])
                except InvalidTransition as exc:
                    logger.warning("settle_manual: riga %s saltata: %s",
                                   row.get("seq"), exc)
            await order_repository.update(order_id, org_id, {
                "payment_state": schedule.get("payment_state"),
            })
    except Exception:
        logger.exception("settle_manual: schedule handling fallito per %s", order_id)

    # 4. Saldato per intero → ordine pagato + SalesRecords.
    if scope == "full":
        await order_repository.update(order_id, org_id, {
            "payment_status": OrderPaymentStatus.PAID.value,
            "updated_at": utc_now(),
        })
        await sync_payment_to_sales(org_id, order_id, OrderPaymentStatus.PAID.value)

    updated = await order_repository.find_one(order_id, org_id)
    logger.info(
        "order_service: settle_manual order=%s scope=%s rows=%s actor=%s",
        order_id, scope, settled_rows, actor,
    )
    updated["_settled_rows"] = settled_rows
    return updated


async def mark_order_unpaid(org_id: str, order_id: str) -> dict:
    """Revert an order to pending payment. For corrections."""
    from repositories import order_repository
    from services.payment_sync import sync_payment_to_sales

    order = await order_repository.find_one(order_id, org_id)
    if not order:
        raise ValueError("Order not found")

    status = order.get("status", "draft")
    if status not in ("confirmed", "completed"):
        raise ValueError(f"Modifica pagamento non consentita per ordini in stato '{status}'")
    if order.get("payment_status") == "pending":
        return order  # idempotent

    now = utc_now()
    updates = {"payment_status": OrderPaymentStatus.PENDING.value, "updated_at": now}
    await order_repository.update(order_id, org_id, updates)
    await sync_payment_to_sales(org_id, order_id, OrderPaymentStatus.PENDING.value)

    order.update(updates)
    logger.info("order_service: marked unpaid order %s for org=%s", order_id, org_id)
    return order


# ── Bridge: Orders → SalesRecords ───────────────────────────────────────────

async def _build_product_category_cache(org_id: str, product_ids: set) -> dict:
    """Fetch product.category for a set of product_ids in one query.

    Returns a dict {product_id: category_str_or_None}. Used by SalesRecord
    generators to backfill `category` when the order line didn't snapshot it
    at create time (older orders, manual CSV imports, storefront drafts).
    Scoped by organization_id for safety.
    """
    if not product_ids:
        return {}
    from database import products_collection
    ids = [pid for pid in product_ids if pid]
    if not ids:
        return {}
    cursor = products_collection.find(
        {"organization_id": org_id, "id": {"$in": ids}},
        {"_id": 0, "id": 1, "category": 1, "name": 1},
    )
    cache = {}
    async for p in cursor:
        cache[p["id"]] = {
            "category": p.get("category"),
            "name": p.get("name"),
        }
    return cache


def _resolve_sales_category(line: dict, product_cache: dict) -> str | None:
    """Resolve the category that goes on a SalesRecord for `line`.

    Precedence:
      1. line.category (order-time snapshot from product.category)
      2. product.category (current value from products collection)
      3. line.product_name / product.name (friendly fallback so the cashflow
         dashboard always has a meaningful grouping bucket — the user
         explicitly agreed that product name is an acceptable fallback)

    Returns None only when all three are missing/empty (shouldn't happen in
    practice but keeps the column nullable-safe for legacy data).
    """
    snap = (line.get("category") or "").strip()
    if snap:
        return snap
    pid = line.get("product_id")
    cached = product_cache.get(pid) if pid else None
    if cached:
        live_cat = (cached.get("category") or "").strip()
        if live_cat:
            return live_cat
        live_name = (cached.get("name") or "").strip()
        if live_name:
            return live_name
    fallback_name = (line.get("product_name") or "").strip()
    return fallback_name or None


async def _generate_sales_records(org_id: str, order: dict, order_number: str) -> int:
    """Generate one SalesRecord per order line. Returns count inserted.

    Category enrichment (Onda 14): each line's SalesRecord carries a category
    resolved via the order-line snapshot → live product.category → product.name
    fallback chain, so the cashflow dashboard always has a meaningful grouping
    even when the line didn't snapshot category at create time.
    """
    from repositories import sales_repository
    from services.module_access import check_module_access, record_module_usage

    items = order.get("items", [])
    if not items:
        return 0

    # Pre-check cashflow quota
    await check_module_access(org_id, "cashflow_monitor", "data_rows", pending_quantity=len(items))

    order_date = order.get("order_date") or order.get("created_at", "")
    if isinstance(order_date, datetime):
        order_date = order_date.strftime("%Y-%m-%d")

    # Batch-fetch product.category for all lines missing a snapshot. O(1) query.
    product_ids = {
        line.get("product_id") for line in items
        if line.get("product_id") and not (line.get("category") or "").strip()
    }
    product_cache = await _build_product_category_cache(org_id, product_ids)

    # 2026-05-20 — Fix Performance Prodotti #2: batch-resolve cost_at_sale
    # for every product on the order in one pass. ``cost_at_sale`` is the
    # per-unit snapshot the Performance Prodotti aggregation reads via
    # ``$sum cost_at_sale`` to compute period-filtered margin. Until now
    # the field was never written → margin always came out as None.
    #
    # Failure modes (all soft):
    #   · Resolver import fails / raises → unit_cost_map stays empty →
    #     SalesRecords are written with cost_at_sale=None (legacy
    #     behaviour, no regression).
    #   · A specific product has no cost_source / resolver returns
    #     ResolverResult(value=None) → that product's cost_at_sale=None,
    #     others get their cost. Granular, not all-or-nothing.
    #
    # The dataset.py model already has the new field; the repository
    # ``insert_many`` accepts whatever ``model_dump`` produces.
    unit_cost_map = {}
    try:
        from services.cost_resolver import CostResolver
        product_ids_for_cost = [
            line.get("product_id") for line in items if line.get("product_id")
        ]
        if product_ids_for_cost:
            from database import products_collection as _pc
            cost_cursor = _pc.find(
                {
                    "organization_id": org_id,
                    "id": {"$in": product_ids_for_cost},
                },
                {"_id": 0, "id": 1, "cost_source": 1, "cost_price": 1,
                 "category": 1, "item_type": 1},
            )
            cost_products = await cost_cursor.to_list(length=len(product_ids_for_cost))
            if cost_products:
                resolver = CostResolver(org_id=org_id)
                results = await resolver.resolve_many(cost_products)
                for pid, result in results.items():
                    if result and result.value is not None:
                        unit_cost_map[pid] = float(result.value)
    except Exception as exc:
        logger.warning(
            "order_service: cost_at_sale resolver batch failed for "
            "order=%s: %s — sales records will be written without "
            "cost_at_sale (legacy fallback).",
            order_number, exc,
        )
        unit_cost_map = {}

    docs = []
    for line in items:
        category = _resolve_sales_category(line, product_cache)
        line_product_id = line.get("product_id")
        # Per-unit cost. Each SalesRecord is 1 unit by repo convention —
        # ``items`` may already be exploded by quantity upstream, so we
        # do NOT multiply by line.quantity here.
        line_cost_at_sale = unit_cost_map.get(line_product_id) if line_product_id else None
        sale = SalesRecord(
            organization_id=org_id,
            dataset_id="orders",
            date=order_date,
            amount=round(line["line_total"], 2),
            category=category,
            description=f"Ordine {order_number}: {line['product_name']} x {line['quantity']}",
            customer_id=order.get("customer_id"),
            product_id=line_product_id,
            payment_status=order.get("payment_status"),
            due_date=order.get("due_date"),
            source_label="Ordini",
            # 2026-05-20 — snapshot the resolver's unit cost so the
            # Performance Prodotti page can compute margin without
            # re-resolving (and so historical margin stays accurate
            # if the merchant later changes cost_source).
            cost_at_sale=line_cost_at_sale,
        )
        doc = sale.model_dump()
        metadata: dict = {"order_id": order["id"], "order_number": order_number}
        # Onda 16 — extras breakdown for cashflow analytics. Purely additive
        # in metadata; the SalesRecord.amount already includes the extras so
        # the cashflow dashboard keeps reading a single authoritative total.
        extras = line.get("extras") or []
        if extras:
            metadata["extras_breakdown"] = [
                {"label": e.get("label"), "kind": e.get("kind"),
                 "amount": e.get("line_total", 0)}
                for e in extras
            ]
            metadata["extras_total"] = round(line.get("extras_total", 0), 2)
        doc["metadata"] = metadata
        docs.append(doc)

    count = await sales_repository.insert_many(docs)
    await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=count)

    logger.info("order_service: generated %d SalesRecords for order %s", count, order_number)
    return count


async def _generate_storno_records(org_id: str, order: dict) -> int:
    """Generate negative SalesRecords to reverse a cancelled confirmed order.

    Onda 14: storno records now carry the same category as the original
    SalesRecords so cashflow category breakdowns stay balanced when an
    order is cancelled (the positive and negative entries offset per-category).

    v5.8 / Onda 9.Y.0.1 — Plan-gated. Closes the cancel-and-reconfirm
    loop bypass: a Free org at 200/200 could repeatedly cancel and
    re-confirm an order to inflate the data_rows counter past quota
    because the storno-only step previously called record_module_usage
    without a preceding check. The forward generator IS gated, but the
    storno was not.
    """
    from repositories import sales_repository
    from services.module_access import check_module_access, record_module_usage

    order_number = order.get("order_number", "???")
    order_date = order.get("order_date") or order.get("created_at", "")
    if isinstance(order_date, datetime):
        order_date = order_date.strftime("%Y-%m-%d")

    items = order.get("items", [])

    # Plan gate — same as forward generator. Storno rows count toward
    # data_rows quota (they're real rows in the cashflow analytics).
    if items:
        await check_module_access(
            org_id, "cashflow_monitor", "data_rows",
            pending_quantity=len(items),
        )

    # Batch-fetch product.category only when line snapshot missing (same pattern
    # as forward generator, keeps storno category consistent with original).
    product_ids = {
        line.get("product_id") for line in items
        if line.get("product_id") and not (line.get("category") or "").strip()
    }
    product_cache = await _build_product_category_cache(org_id, product_ids)

    # 2026-05-20 — Fix Performance Prodotti #2: storno records also need
    # a NEGATIVE cost_at_sale so the period-filtered margin aggregate
    # nets to zero when an order is cancelled. We re-resolve the cost
    # now (same as we re-resolve the category) — for the 99% case where
    # cost_source is unchanged between confirm and cancel, this gives a
    # perfect zero net. If cost_source did change between the two events,
    # the small delta surfaces via metadata.storno=True and is auditable.
    unit_cost_map = {}
    try:
        from services.cost_resolver import CostResolver
        product_ids_for_cost = [
            line.get("product_id") for line in items if line.get("product_id")
        ]
        if product_ids_for_cost:
            from database import products_collection as _pc
            cost_cursor = _pc.find(
                {
                    "organization_id": org_id,
                    "id": {"$in": product_ids_for_cost},
                },
                {"_id": 0, "id": 1, "cost_source": 1, "cost_price": 1,
                 "category": 1, "item_type": 1},
            )
            cost_products = await cost_cursor.to_list(length=len(product_ids_for_cost))
            if cost_products:
                resolver = CostResolver(org_id=org_id)
                results = await resolver.resolve_many(cost_products)
                for pid, result in results.items():
                    if result and result.value is not None:
                        unit_cost_map[pid] = float(result.value)
    except Exception as exc:
        logger.warning(
            "order_service: storno cost_at_sale resolver failed for "
            "order=%s: %s — storno will not include cost_at_sale.",
            order_number, exc,
        )
        unit_cost_map = {}

    docs = []
    for line in items:
        category = _resolve_sales_category(line, product_cache)
        line_product_id = line.get("product_id")
        # Negative per-unit cost so $sum cost_at_sale on the period
        # aggregation cancels the forward record.
        line_cost_at_sale = unit_cost_map.get(line_product_id) if line_product_id else None
        line_cost_at_sale = -line_cost_at_sale if line_cost_at_sale is not None else None
        sale = SalesRecord(
            organization_id=org_id,
            dataset_id="orders",
            date=date.today().isoformat(),  # storno date = today
            amount=-round(line["line_total"], 2),  # negative amount
            category=category,
            description=f"Storno Ordine {order_number}: {line['product_name']} x {line['quantity']}",
            customer_id=order.get("customer_id"),
            product_id=line_product_id,
            payment_status="cancelled",
            source_label="Ordini",
            cost_at_sale=line_cost_at_sale,
        )
        doc = sale.model_dump()
        metadata: dict = {"order_id": order["id"], "order_number": order_number, "storno": True}
        # Onda 16 — mirror forward extras so the storno perfectly cancels
        # the per-category analytics (same labels, negative amounts).
        extras = line.get("extras") or []
        if extras:
            metadata["extras_breakdown"] = [
                {"label": e.get("label"), "kind": e.get("kind"),
                 "amount": -abs(e.get("line_total", 0))}
                for e in extras
            ]
            metadata["extras_total"] = -abs(round(line.get("extras_total", 0), 2))
        doc["metadata"] = metadata
        docs.append(doc)

    count = await sales_repository.insert_many(docs)

    # Track storno records as data_rows usage (same policy as regular SalesRecords).
    # The pre-flight check_module_access above already imported these helpers.
    await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=count)

    logger.info("order_service: generated %d storno SalesRecords for order %s", count, order_number)
    return count


async def update_fulfillment_status(
    org_id: str, order_id: str, new_status: str,
    *,
    tracking_number: Optional[str] = None,
    tracking_url: Optional[str] = None,
) -> dict:
    """Transition fulfillment status. Validates the transition is allowed.

    Allowed transitions:
      pending → shipped | ready_for_pickup | delivered
      shipped → delivered
      ready_for_pickup → picked_up

    Release 1 (Physical) — `tracking_number` and `tracking_url` are persisted
    when the transition is to "shipped". Silently ignored for other transitions
    (delivered / picked_up / fulfilled): they only make sense at ship time.
    """
    from repositories import order_repository

    order = await order_repository.find_one(order_id, org_id)
    if not order:
        raise ValueError("Order not found")

    if order["status"] not in ("confirmed", "completed"):
        raise ValueError("Fulfillment can only be updated on confirmed or completed orders")

    ff = order.get("fulfillment") or {}
    current = ff.get("status", "not_required")

    if current == "not_required":
        raise ValueError("This order does not require fulfillment")

    # Mode-aware valid transitions
    mode = ff.get("mode", "not_required")
    VALID_TRANSITIONS = {
        "shipping": {
            "pending": {"shipped"},
            "shipped": {"delivered"},
        },
        "local_pickup": {
            "pending": {"ready_for_pickup"},
            "ready_for_pickup": {"picked_up"},
        },
        "manual_arrangement": {
            "pending": {"fulfilled"},
        },
    }

    mode_transitions = VALID_TRANSITIONS.get(mode, {})
    allowed = mode_transitions.get(current, set())
    if new_status not in allowed:
        raise ValueError(f"Cannot transition from '{current}' to '{new_status}' (mode={mode})")

    now = utc_now()
    ff_updates = {"fulfillment.status": new_status, "updated_at": now}

    if new_status == "shipped":
        ff_updates["fulfillment.shipped_at"] = now.isoformat()
        # Only attach tracking on the ship transition. Trim to avoid empty
        # strings leaking through — an empty tracking_number is the same as None.
        if tracking_number and tracking_number.strip():
            ff_updates["fulfillment.tracking_number"] = tracking_number.strip()
        if tracking_url and tracking_url.strip():
            ff_updates["fulfillment.tracking_url"] = tracking_url.strip()
    elif new_status in ("delivered", "picked_up", "fulfilled"):
        ff_updates["fulfillment.delivered_at"] = now.isoformat()

    await order_repository.update(order_id, org_id, ff_updates)

    order = await order_repository.find_one(order_id, org_id)
    logger.info("order_service: fulfillment %s → %s for order %s org=%s", current, new_status, order_id, org_id)

    # v10.1: best-effort customer email notification
    try:
        from services.order_email_service import notify_customer_fulfillment_update
        await notify_customer_fulfillment_update(order, org_id, new_status)
    except Exception as e:
        logger.warning("order_service: fulfillment email failed: %s", e)

    return order


async def _refresh_customer_metrics_best_effort(org_id: str) -> None:
    """Refresh customer_metrics after an order state change.

    Onda 14 — explicit belt-and-suspenders complement to the module-registry
    hook path. The registry-based path (_trigger_module_hooks) only fires
    when the customer_insights module is registered in the current
    process; this direct call guarantees metrics stay fresh regardless
    of import order or caller context (HTTP worker, script, test
    harness, background job).

    Migrated to customer_insights post Phase-3 single-brain
    consolidation (the module_key="customers_light" identity is
    preserved on the registration so org activations still match).

    Idempotent, fire-and-forget. Never raises — any exception is logged
    and swallowed so order confirmation / cancellation flows never block
    on analytics refresh.
    """
    try:
        from modules.customer_insights import repository as cl_repo
        linked = await cl_repo.count_linked_sales(org_id)
        if linked == 0:
            return
        from modules.customer_insights.refresh import refresh_customer_metrics
        result = await refresh_customer_metrics(org_id)
        logger.info(
            "order_service: customer_metrics refreshed for org=%s (%s)",
            org_id, result.get("message", "done"),
        )
    except Exception as exc:
        logger.warning(
            "order_service: customer_metrics refresh failed for org=%s: %s",
            org_id, exc,
        )


async def _refresh_product_metrics_best_effort(org_id: str) -> None:
    """Refresh product_catalog metrics after an order state change.

    Onda 15 — sibling of _refresh_customer_metrics_best_effort for the
    product_catalog (Performance Prodotti) module. Without this hook the
    product_metrics_collection was only updated on file upload, leaving
    the page stale for orgs that rely on storefront/manual orders as the
    primary sales driver.

    Idempotent, fire-and-forget. Never raises.
    """
    try:
        from modules.product_catalog.service import refresh_product_metrics
        result = await refresh_product_metrics(org_id)
        logger.info(
            "order_service: product_metrics refreshed for org=%s (%s)",
            org_id, result.get("message", "done") if isinstance(result, dict) else "done",
        )
    except Exception as exc:
        logger.warning(
            "order_service: product_metrics refresh failed for org=%s: %s",
            org_id, exc,
        )


async def _trigger_module_hooks(org_id: str) -> None:
    """Fire post-upload hooks for all registered modules in parallel.

    Same logic as dataset_service._run_post_upload_hooks but kept
    as a separate function to avoid importing the monolithic dataset_service.

    Hooks are executed in parallel via asyncio.gather (each module is
    independent).  return_exceptions=True ensures a failure in one hook
    does not cancel others.
    """
    import asyncio
    from core.module_registry import get_all as registry_get_all

    async def _safe_hook(hook, org_id: str):
        try:
            await hook(org_id)
        except Exception as exc:
            logger.warning(
                "order_service hook %s failed for org %s: %s",
                getattr(hook, "__name__", repr(hook)), org_id, exc,
            )

    tasks = []
    for module in registry_get_all():
        for hook in module.post_upload_hooks:
            tasks.append(_safe_hook(hook, org_id))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
