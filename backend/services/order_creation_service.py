"""Order Creation Service — unified entry point for storefront orders.

Phase 0 Step 3 della roadmap di evoluzione e-commerce (ADR-001).

Ruolo
=====
Centralizza la logica di order submission che PRIMA viveva inline in
``routers/public.py:submit_order_request`` (~750 righe). Ora chiamata da:

  · /api/public/order-request (storefront classic) — invariato come contract
  · /api/public/embed/order-request (Stream A, futuro)
  · /api/public/ai-site/order-request (Stream B, futuro)
  · POS / admin manual order (futuro Phase 1)

Tutti questi surface DEVONO ottenere comportamento identico per le 17 collection
write nelle 8 fasi sequenziali documentate in system-invariants.md. Avere un
unico service garantisce che le invarianti INV-1 → INV-10 siano enforced
uniformemente.

Invarianti preservate
=====================
INV-1  Customer atomic upsert (eseguito dal router PRIMA di chiamare il service;
       il service riceve customer_id già risolto)
INV-2  Order number canonical ``ORD-{N:04d}`` (eseguito da services.order_service)
INV-3  Marketing opt-in triple-write (consent_audit + customer_accounts + customers)
INV-4  GDPR snapshot on Order ($set su orders_collection)
INV-6  Rental slot atomic pre-reservation (in services.order_service.create_order)
INV-8  SalesRecords 1:1 con order lines (in services.order_service post-confirm)

Mossa architetturale di Step 3
==============================
Questa è una MOSSA pura, non un refactor di logica. Il body della funzione
``submit_order_request`` è stato copiato qui IDENTICAL byte-by-byte, con
adjustments minimi per le dipendenze esterne:

  - ``request.client.host`` → parametro ``client_ip``
  - ``request.headers.get("user-agent")`` → parametro ``user_agent``
  - ``customer_id`` ricevuto già risolto dal chiamante
  - ``org`` ricevuto già risolto dal chiamante

Future refactor (Step 3b, 3c in altri commit) divideranno questo service in
sub-services (customer_resolver, items_validator, gdpr_writer, marketing_sync,
coupon_applier, payment_intent_resolver). Per ora preservare il comportamento
1:1 è prioritario su clean architecture.

Unica pipeline (R10)
====================
Questo service è l'UNICO path di creazione ordini da storefront/embed. Il
vecchio dual-path con flag ``USE_ORDER_CREATION_SERVICE`` e il legacy inline
in ``public.py`` sono stati rimossi (R10, 2026-06-19) dopo il soak in
produzione: niente più drift tra le superfici.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


# ── Main service entry point ─────────────────────────────────────────────


async def submit_order_from_storefront(
    *,
    org: dict,
    body: Any,  # OrderRequestPayload (Pydantic model) — late typing to avoid cycle
    customer_account_id: Optional[str],
    customer_id: str,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    cart_id: Optional[str] = None,
) -> dict:
    """Submit a storefront order — the canonical path that all storefront
    surfaces (classic, embed, AI site) flow through.

    Parameters
    ----------
    org : dict
        The resolved organization document (with ``_store`` sub-doc when
        the storefront is a store-scoped catalog).
    body : OrderRequestPayload
        The validated request payload from the client. Type is ``Any`` here
        to avoid a circular import with routers/public.py where the
        Pydantic model is defined — duck-typing on attribute access.
    customer_account_id : Optional[str]
        Set when the customer is authenticated (Bearer customer token).
        ``None`` for guest checkout.
    customer_id : str
        The CRM customer id, already created/found by the caller via
        ``customer_repository.upsert_by_email``. INV-1 enforced at the
        caller boundary.
    client_ip : Optional[str]
        Client IP for consent_audit records (legal proof trail).
    user_agent : Optional[str]
        Client User-Agent for consent_audit records.
    cart_id : Optional[str]
        Phase 0 Step 5 — server-side persistent cart id (cookie afianco_cart_id).
        If provided AND the order is successfully created, the cart is marked
        as ``converted_to_order_id`` so it stops being a recovery candidate.
        Soft-fail: cart conversion failure non blocca l'order. Sempre None
        finché il frontend non passa il cookie (REACT_APP_PERSISTENT_CART_ENABLED).

    Returns
    -------
    dict
        Keys: ``order_id``, ``message``, ``transaction_mode``,
        ``order_status``, ``payment_checkout_url``, ``payment_reason``.
        Caller constructs the OrderRequestResponse from this dict.

    Raises
    ------
    HTTPException
        Same status codes as the legacy router (400, 429, 500).
    """
    org_id = org["id"]

    # ── Validate all products are published and belong to org ──────────────
    from database import products_collection
    product_ids = [item.product_id for item in body.items]
    cursor = products_collection.find(
        {"organization_id": org_id, "id": {"$in": product_ids}, "is_published": True, "is_active": True},
        # F4 Onda 11: include metadata so terms_resolver can read product override
        {"_id": 0, "id": 1, "item_type": 1, "transaction_mode": 1, "stock_quantity": 1, "metadata": 1},
    )
    valid_products = {doc["id"]: doc async for doc in cursor}

    invalid = [pid for pid in product_ids if pid not in valid_products]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Products not found or not published: {', '.join(invalid[:3])}",
        )

    # Release 4 (Courses) Step 4 — orders containing a video course require
    # an authenticated customer account. The enrollment is nominative and
    # fulfilled through the customer portal player; guest emission would
    # leave a dangling enrollment with no portal access. This guard is the
    # server-side safety net even if a modified frontend tries to bypass
    # the UI restriction. The error code `course_requires_account` lets
    # the frontend surface a dedicated message + inline login/signup form.
    has_course_item = any(
        valid_products.get(item.product_id, {}).get("item_type") == "course"
        for item in body.items
    )
    if has_course_item and not customer_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "course_requires_account",
                "message": (
                    "L'ordine contiene un corso video: accedi o crea un "
                    "account per completare l'acquisto."
                ),
            },
        )

    # F4 Onda 11 — Terms & Conditions acceptance check.
    # Resolve effective T&C from the first product in the cart (product
    # override) falling back to the store-level default. If non-empty,
    # the customer must have accepted via the checkbox.
    from services.terms_resolver import resolve_effective_terms_sync
    resolved_store_for_terms = org.get("_store") or {}
    first_prod_for_terms = valid_products.get(product_ids[0]) if product_ids else None
    effective_terms = resolve_effective_terms_sync(
        product=first_prod_for_terms, store=resolved_store_for_terms,
    )
    if effective_terms and not body.terms_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Devi accettare i termini e condizioni per procedere.",
        )

    # ── Wave GDPR-Commerce CG-5 (2026-05-19) — per-order consent capture ──
    #
    # STRICTLY ADDITIVE on top of the legacy T&C check above. The GDPR
    # consent flow only kicks in when the merchant has explicitly
    # published their per-store legal docs (CG-3 admin UI). Otherwise
    # the checkout proceeds exactly as before (legacy stores untouched).
    from services.merchant_legal_versioning import (
        merchant_legal_status as _gdpr_status_fn,
        current_version_string as _gdpr_version_string,
        get_effective_display_locale as _gdpr_effective_locale,
    )
    gdpr_active_status = _gdpr_status_fn(resolved_store_for_terms)
    gdpr_enforce = gdpr_active_status in ("published", "stale_draft")
    gdpr_version_string = None
    gdpr_locale = None

    if gdpr_enforce:
        # 2026-05-20 — Fix Bug #3b: logged-in customers already accepted
        # the merchant's Privacy + Terms at signup (CG-4 captured the
        # snapshot on customer_account.accepted_store_{privacy,terms}_*).
        # The frontend hides the GDPR checkboxes for them (Fix 3a), so
        # the payload arrives with gdpr_terms_accepted=False and
        # gdpr_privacy_accepted=False — but those flags are MEANINGLESS
        # for an authenticated customer.
        terms_implicitly_accepted = False
        privacy_implicitly_accepted = False
        if customer_account_id:
            from database import customer_accounts_collection
            current_version = _gdpr_version_string(resolved_store_for_terms)
            try:
                cust_doc = await customer_accounts_collection.find_one(
                    {"id": customer_account_id, "organization_id": org_id},
                    {
                        "_id": 0,
                        "accepted_store_terms_version": 1,
                        "accepted_store_privacy_version": 1,
                    },
                )
            except Exception:
                cust_doc = None
            if cust_doc and current_version:
                terms_implicitly_accepted = (
                    cust_doc.get("accepted_store_terms_version") == current_version
                )
                privacy_implicitly_accepted = (
                    cust_doc.get("accepted_store_privacy_version") == current_version
                )

        effective_terms_accepted = (
            body.gdpr_terms_accepted or terms_implicitly_accepted
        )
        effective_privacy_accepted = (
            body.gdpr_privacy_accepted or privacy_implicitly_accepted
        )

        if not effective_terms_accepted or not effective_privacy_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Devi accettare la Privacy Policy e i Termini di "
                    "Servizio per completare l'ordine."
                ),
            )
        gdpr_version_string = _gdpr_version_string(resolved_store_for_terms)
        gdpr_locale = _gdpr_effective_locale(resolved_store_for_terms)
        if not gdpr_version_string or not gdpr_locale:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Impossibile registrare il consenso legale del negozio."
                ),
            )

    # ── Stock validation (v13.0) ───────────────────────────────────────
    for item in body.items:
        prod = valid_products.get(item.product_id, {})
        stock = prod.get("stock_quantity")
        if stock is not None and stock <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prodotto esaurito: {item.product_id}",
            )
        if stock is not None and item.quantity > stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quantita' richiesta ({int(item.quantity)}) superiore alla disponibilita' ({stock})",
            )

    # ── Validate type-specific fields via the centralized dispatcher ──
    from services.product_type_validators import (
        validate_order_item, message_for_reason,
    )

    _validation_ctx = {
        "org_id": org_id,
        "order_fields": body.order_fields or {},
    }

    def _legacy_message(item_, result_) -> str:
        """Translate a ValidationResult.reason → exact legacy string."""
        reason = result_.reason
        pid = item_.product_id
        occ = result_.detail or ""
        if reason == "occurrence_id_required":
            return f"occurrence_id is required for event_ticket product '{pid}'"
        if reason == "occurrence_not_found":
            return f"Occorrenza '{occ}' non trovata"
        if reason == "occurrence_cancelled":
            return "Questa data è stata annullata"
        if reason == "occurrence_closed":
            return "Questa data è chiusa"
        if reason == "occurrence_not_published":
            return "Questa data non è ancora disponibile"
        if reason == "rental_date_from_required":
            return f"rental_date_from is required for rental product '{pid}'"
        if reason == "rental_date_range_invalid":
            return "rental_date_to must be >= rental_date_from"
        if reason == "booking_slot_incomplete":
            return (
                "booking_date, booking_start_time, and booking_end_time "
                f"are required for booking product '{pid}'"
            )
        if reason.startswith("occurrence_"):
            return f"Occorrenza non disponibile: {reason}"
        return message_for_reason(reason, result_.detail)

    for item in body.items:
        prod = valid_products.get(item.product_id, {})
        result = await validate_order_item(item, prod, _validation_ctx)
        if result.valid:
            continue
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_legacy_message(item, result),
        )

    # ── Resolve dominant transaction_mode from products ──────────────────
    product_modes = [valid_products.get(item.product_id, {}).get("transaction_mode", "request") for item in body.items]
    unique_modes = list(set(m or "request" for m in product_modes))
    dominant_mode = unique_modes[0] if len(unique_modes) == 1 else "request"

    # ── v5.8 / Onda 4: Commerce plan enforcement ────────────────────────
    try:
        from services.module_access import get_effective_limit

        # (1) Orders monthly quota
        orders_limit = await get_effective_limit(org_id, "commerce", "orders_monthly")
        if orders_limit > 0:
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            from database import orders_collection
            current_usage = await orders_collection.count_documents({
                "organization_id": org_id,
                "created_at": {"$gte": month_start},
            })
            if current_usage + 1 > orders_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "orders_quota_exceeded",
                        "message": (
                            f"Limite ordini mensile raggiunto ({orders_limit}/mese). "
                            "Contatta il merchant per assistenza."
                        ),
                        "current_usage": current_usage,
                        "effective_limit": orders_limit,
                    },
                )

        # (2) checkout_stripe flag — Free plans get the contact-request flow
        checkout_stripe_enabled = await get_effective_limit(org_id, "commerce", "checkout_stripe")
        if checkout_stripe_enabled == 0 and dominant_mode == "direct":
            logger.info(
                "order_creation: downgraded direct→request for org=%s (commerce.checkout_stripe=0)",
                org_id,
            )
            dominant_mode = "request"
    except HTTPException:
        raise  # propagate 429 immediately
    except Exception as exc:  # noqa: BLE001 — defence-in-depth
        logger.warning(
            "order_creation: commerce plan enforcement skipped for org=%s due to: %s",
            org_id, exc,
        )

    # Source tag reflects transaction intent
    source_map = {
        "request": "storefront",
        "direct": "storefront_direct",
        "approval": "storefront_approval",
    }
    source = source_map.get(dominant_mode, "storefront")

    # ── Create order via existing service ──────────────────────────────
    from models.order import OrderCreate, OrderLineCreate
    from services.order_service import create_order

    order_create = OrderCreate(
        customer_id=customer_id,
        notes=body.notes,
        items=[
            OrderLineCreate(
                product_id=item.product_id,
                quantity=item.quantity,
                occurrence_id=item.occurrence_id,
                ticket_tier_id=item.ticket_tier_id,
                rental_date_from=item.rental_date_from,
                rental_date_to=item.rental_date_to,
                rental_notes=item.rental_notes,
                booking_date=item.booking_date,
                booking_start_time=item.booking_start_time,
                booking_end_time=item.booking_end_time,
                booking_end_date=item.booking_end_date,
                attendees=item.attendees,
                service_option_id=item.service_option_id,
                # R4 — propaga il flag richiesta personalizzata (slot fuori
                # dalle regole) fino alla persistenza dell'ordine.
                service_custom_request=getattr(item, 'service_custom_request', False),
                # R2 — propaga gli extra (optional/radio) fino al pricing.
                extra_selections=item.extra_selections,
            )
            for item in body.items
        ],
    )

    # v10.3: validate shipping address required when fulfillment_mode=shipping.
    if body.fulfillment_mode == "shipping":
        has_structured = bool(body.shipping_address_details)
        has_legacy = bool(body.shipping_address and body.shipping_address.strip())
        if not (has_structured or has_legacy):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Indirizzo di spedizione obbligatorio per la modalita' spedizione.",
            )

    # Direct mode: payment is required before confirmation.
    pi = "required" if dominant_mode == "direct" else "none"

    try:
        # v10.0: build fulfillment input from customer choice
        fulfillment_input = {}
        if body.fulfillment_mode:
            fulfillment_input["mode"] = body.fulfillment_mode
        if body.shipping_address_details:
            details_dict = body.shipping_address_details.model_dump(exclude_none=True)
            country = (details_dict.get("country") or "IT").strip().upper()
            details_dict["country"] = country[:2] or "IT"
            prov = details_dict.get("province")
            if prov:
                details_dict["province"] = prov.strip().upper()
            fulfillment_input["shipping_address_details"] = details_dict
            from services.shipping_address_formatter import format_address_oneline
            flattened = format_address_oneline(details_dict)
            if flattened:
                fulfillment_input["shipping_address"] = flattened
        elif body.shipping_address:
            fulfillment_input["shipping_address"] = body.shipping_address
        if body.fulfillment_notes:
            fulfillment_input["fulfillment_notes"] = body.fulfillment_notes
        if body.shipping_option_id:
            fulfillment_input["shipping_option_id"] = body.shipping_option_id

        # Coupon validation (v13.0)
        # B3 — pre-creazione: validazione fail-fast SENZA incremento e SENZA
        # check min_order (il subtotale reale non e' ancora noto). L'unico
        # incremento atomico + il check min_order avvengono post-creazione,
        # sul subtotale autoritativo (vedi più sotto).
        coupon_info = None
        _coupon_store_id = org.get("_store", {}).get("id")
        if body.coupon_code:
            from routers.coupons import validate_coupon_dry_run
            coupon_info = await validate_coupon_dry_run(
                org_id, body.coupon_code, 0.0,
                store_id=_coupon_store_id,
                check_min_order=False,
            )

        # F4 Onda 11 — stamp T&C acceptance timestamp only when T&C were
        # actually required for this order (effective_terms was non-empty above).
        terms_ts = datetime.now(timezone.utc).isoformat() if effective_terms else None

        order = await create_order(
            org_id, order_create, source=source, payment_intent=pi,
            customer_account_id=customer_account_id,
            fulfillment_input=fulfillment_input or None,
            contact_phone=body.customer_phone,
            store_id=org.get("_store", {}).get("id"),
            order_fields_data=body.order_fields or None,
            terms_accepted_at=terms_ts,
        )

        # ── Wave GDPR-Commerce CG-5 (2026-05-19) ──────────────────────
        # Stamp per-order GDPR consent snapshot AND write the immutable
        # audit records. We do this AFTER create_order returns so the
        # create_order signature stays untouched.
        if gdpr_enforce and order:
            from database import orders_collection as _oc_gdpr
            now_gdpr_iso = datetime.now(timezone.utc).isoformat()
            gdpr_update = {
                "gdpr_terms_version": gdpr_version_string,
                "gdpr_privacy_version": gdpr_version_string,
                "gdpr_locale": gdpr_locale,
                "gdpr_accepted_at": now_gdpr_iso,
                "gdpr_marketing_accepted": bool(body.gdpr_marketing_accepted),
            }
            try:
                await _oc_gdpr.update_one(
                    {"id": order["id"], "organization_id": org_id},
                    {"$set": gdpr_update},
                )
                order.update(gdpr_update)
            except Exception as exc:
                logger.error(
                    "CG-5: gdpr snapshot $set failed for order=%s: %s",
                    order.get("id"), exc, exc_info=True,
                )

            # Write the immutable consent_audit records.
            try:
                from repositories import consent_audit_repository as _car
                version_tag, _, version_hash = gdpr_version_string.partition(":")
                audit_locale = gdpr_locale if gdpr_locale in (
                    "it", "en", "de", "fr"
                ) else "it"
                # IP + UA passed from caller (router extracted from request)
                ip_addr = client_ip
                ua_str = user_agent

                # Both privacy + terms are mandatory at checkout
                for doc_type in ("merchant_privacy", "merchant_terms"):
                    await _car.record_consent(
                        user_id=customer_account_id,
                        organization_id=org_id,
                        store_id=org.get("_store", {}).get("id"),
                        customer_email=body.customer_email,
                        order_id=order["id"],
                        locale=audit_locale,
                        version_tag=version_tag or "v1.0",
                        version_hash=version_hash or "unknown",
                        ip_address=ip_addr,
                        user_agent=ua_str,
                        source="customer_checkout",
                        document_type=doc_type,
                    )

                if body.gdpr_marketing_accepted:
                    # F0 — opt-in marketing via servizio condiviso (audit +
                    # dual snapshot sync). Stessa logica di prima, ora
                    # riusata anche da signup/newsletter (no duplicazione).
                    from services.marketing_consent_service import (
                        record_marketing_optin,
                    )
                    await record_marketing_optin(
                        organization_id=org_id,
                        customer_id=order.get("customer_id"),
                        customer_account_id=customer_account_id,
                        store_id=org.get("_store", {}).get("id"),
                        email=body.customer_email,
                        locale=audit_locale,
                        version_tag=version_tag or "v1.0",
                        version_hash=version_hash or "unknown",
                        ip_address=ip_addr,
                        user_agent=ua_str,
                        source="customer_marketing_optin",
                        order_id=order["id"],
                    )
            except Exception as exc:
                logger.error(
                    "CG-5: consent_audit insert failed for order=%s: %s",
                    order.get("id"), exc, exc_info=True,
                )

        # Apply coupon discount post-creation
        # B3 — UNICA validazione autoritativa: subtotale reale + check min_order
        # + incremento atomico di current_uses (un solo incremento per ordine).
        if coupon_info and order:
            from database import orders_collection as _oc
            discount = 0
            if coupon_info.get("code"):
                from routers.coupons import validate_coupon as _vc
                # R5 — identità cliente per l'anti-riuso per-cliente: account id
                # se loggato, altrimenti email normalizzata. order_id lega la
                # redemption all'ordine per il rollback su cancellazione.
                _customer_key = customer_account_id or (
                    (body.customer_email or "").strip().lower() or None
                )
                try:
                    coupon_info = await _vc(
                        org_id, body.coupon_code, order.get("subtotal", 0),
                        store_id=_coupon_store_id,
                        customer_key=_customer_key,
                        order_id=order.get("id"),
                    )
                    discount = coupon_info["discount"]
                except Exception:
                    # Coupon non applicabile sul subtotale reale (min non
                    # raggiunto / esaurito tra pre-check e creazione): nessun
                    # discount, ordine confermato a prezzo pieno.
                    discount = 0
            if discount > 0:
                new_total = max(0, round(order.get("total", 0) - discount, 2))
                await _oc.update_one(
                    {"id": order["id"], "organization_id": org_id},
                    {"$set": {"coupon_code": coupon_info["code"], "discount_total": discount, "total": new_total}},
                )
                order["coupon_code"] = coupon_info["code"]
                order["discount_total"] = discount
                order["total"] = new_total
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # ── Direct-mode: attempt Stripe checkout creation ──────────────────
    checkout_result = None
    if dominant_mode == "direct":
        from services.payment_checkout_service import create_checkout_session
        checkout_result = await create_checkout_session(org_id, order)
        # If checkout created, re-read order to get updated payment_checkout
        if checkout_result:
            from database import orders_collection
            order = await orders_collection.find_one({"id": order["id"]}, {"_id": 0}) or order

    logger.info(
        "order_creation: order %s created (mode=%s, checkout=%s) for org=%s by %s",
        order["id"], dominant_mode, bool(checkout_result), org_id, body.customer_email,
    )

    # ── Best-effort transactional emails ──────────────────────────────
    direct_with_checkout = dominant_mode == "direct" and checkout_result is not None
    if not direct_with_checkout:
        from services.order_email_service import notify_customer_order_received, notify_merchant_new_order
        await notify_customer_order_received(order, org_id)
        await notify_merchant_new_order(order, org_id, body.customer_name, body.customer_email)
    else:
        logger.info(
            "order_creation: order %s direct-mode with checkout — deferring received-emails to webhook",
            order["id"],
        )

    # ── Mode-aware response messages ──────────────────────────────────
    checkout = order.get("payment_checkout") or {}
    payment_reason = None

    if dominant_mode == "direct":
        if checkout.get("url"):
            payment_reason = "checkout_created"
            direct_msg = "Ordine ricevuto. Completa il pagamento per confermare."
        else:
            # Resolve why checkout wasn't created — order matters:
            # 1. Order-level eligibility (minimum amount, zero totals)
            # 2. Availability safety (rental / event capacity)
            # 3. Provider readiness (Stripe connection)
            from services.payment_checkout_service import check_order_eligibility
            eligible, eligibility_reason = check_order_eligibility(order)
            if not eligible and eligibility_reason == "below_minimum_amount":
                payment_reason = eligibility_reason
                from core.checkout_minimums import get_minimum
                from core.currency_format import format_amount
                from services.currency_service import get_currency_for_order

                order_currency = get_currency_for_order(order)
                min_amount = get_minimum(order_currency)
                min_fmt = format_amount(min_amount, order_currency)
                direct_msg = (
                    f"Importo minimo per il pagamento online: {min_fmt}. "
                    "Contatta il venditore per completare l'ordine."
                )
            else:
                from services.commerce_rules import is_direct_checkout_safe_async
                safe, safety_reason = await is_direct_checkout_safe_async(order, org_id)
                if not safe:
                    payment_reason = safety_reason
                    safety_messages = {
                        "rental_no_availability_guarantee": "Richiesta noleggio registrata. Verificheremo la disponibilità e ti contatteremo per confermare.",
                        "event_capacity_no_reservation_guarantee": "Richiesta registrata. Verificheremo la disponibilità dei posti e ti contatteremo.",
                    }
                    direct_msg = safety_messages.get(safety_reason, "Richiesta registrata. Sarai contattato per confermare.")
                else:
                    from services.payment_resolution import resolve_org_payment_readiness
                    readiness = await resolve_org_payment_readiness(org_id)
                    payment_reason = readiness.reason_code
                    direct_msg = "Ordine ricevuto. Sarai contattato a breve per completare."
    else:
        direct_msg = None

    messages = {
        "request": "Richiesta inviata. Sarai contattato per la conferma.",
        "direct": direct_msg or "Ordine ricevuto. Sarai contattato a breve.",
        "approval": "Richiesta inviata. Verificheremo la disponibilità e ti contatteremo.",
    }

    # ── Phase 0 Step 5 — link cart → order (best-effort, soft-fail) ──
    # Se il chiamante ha passato un cart_id (cookie afianco_cart_id letto
    # dal router), marca il cart come "converted_to_order_id" così:
    #   1. abandon recovery worker NON lo include più nei candidates
    #   2. analytics può tracciare cart conversion rate
    #   3. cleanup TTL job rimuove cart converted dopo ~30gg di history
    #
    # Soft-fail by design: l'order è già creato, non possiamo fail il
    # checkout per un mark di metadata. Log warning per ops visibility.
    if cart_id and order:
        try:
            from repositories import cart_repository
            await cart_repository.mark_converted_to_order(
                cart_id=cart_id,
                organization_id=org_id,
                order_id=order["id"],
            )
            logger.info(
                "order_creation: cart %s linked to order %s for org=%s",
                cart_id, order["id"], org_id,
            )
        except Exception as exc:
            logger.warning(
                "order_creation: cart-order linking failed cart=%s order=%s: %s",
                cart_id, order.get("id"), exc,
            )

    # Phase 0 Step 10 — Observability: record successful order creation.
    # Soft-fail (try/except inside helper) so metric write never breaks
    # the checkout flow.
    try:
        from core.observability import metrics as _metrics
        _metrics.record_order(source=source, status="success")
    except Exception:
        pass

    return {
        "order_id": order["id"],
        "message": messages.get(dominant_mode, messages["request"]),
        "transaction_mode": dominant_mode,
        "order_status": "draft",
        "payment_checkout_url": checkout.get("url"),
        "payment_reason": payment_reason,
        # Phase 0 Step 5 — pass-through cart_id se conversion ha avuto luogo.
        # Permette al router di decidere se clear il cookie post-checkout.
        "cart_converted": bool(cart_id and order),
    }
