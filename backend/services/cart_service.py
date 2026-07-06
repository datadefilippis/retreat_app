"""Cart Service — orchestration layer per il server-side persistent cart.

Phase 0 Step 4 della roadmap di evoluzione e-commerce (ADR-001).

Responsabilità
==============
- Orchestrare repository + product validation + organization resolution
- Esporre helper per cookie management (cart_id HttpOnly)
- Feature flag ``PERSISTENT_CART_ENABLED`` (default OFF — gradual rollout)
- Conversione cart → OrderRequest item list per checkout

Feature flag (default OFF in production)
=========================================
Diversamente da OrderCreationService (default ON), il cart server-side
parte DEFAULT OFF per primi 30 giorni in produzione. Motivo:
  · È un cambio comportamentale visibile (cookie nuovo)
  · Frontend dual-write logic (Step 4b futuro) deve essere stabilizzato prima
  · Permette osservabilità su tasso adozione

Per dev/test: default OFF anche qui, gli endpoint cart funzionano
ma il frontend storefront continua a usare sessionStorage finché
il flag non è abilitato per la merchant org.
"""

import logging
import os
from typing import Optional

from fastapi import HTTPException, Response, status

from models.cart import (
    Cart,
    CartItem,
    CartItemInput,
    CartMergeRequest,
    CartResponse,
    CART_TTL_DAYS,
)
from repositories import cart_repository
from repositories.customer_repository import upsert_by_email

logger = logging.getLogger(__name__)


# ── Cookie configuration ─────────────────────────────────────────────────

# R1 rebrand — nuovo nome cookie; il vecchio viene ancora LETTO in
# fallback (migrazione dolce: i carrelli in corso sopravvivono al rebrand;
# alla prima risposta il Set-Cookie scrive gia' il nome nuovo).
CART_COOKIE_NAME = "aurya_cart_id"
LEGACY_CART_COOKIE_NAME = "afianco_cart_id"
CART_COOKIE_MAX_AGE_SECONDS = CART_TTL_DAYS * 24 * 60 * 60  # 60 giorni in secondi


def set_cart_cookie(response: Response, cart_id: str) -> None:
    """Set the cart_id cookie on the response.

    Security:
      - HttpOnly: not accessible from JS (mitigates XSS hijack)
      - Secure: HTTPS only in production (auto in browsers when on HTTPS)
      - SameSite=Lax: allows top-level navigation but blocks CSRF
      - Max-age 60 giorni: matches CART_TTL_DAYS
      - Path /: available across all storefront routes
    """
    # ``secure=True`` è critico in produzione ma rompe localhost dev HTTP.
    # In ambiente test/dev usiamo False; in produzione True (env-controlled).
    is_production = os.environ.get("ENVIRONMENT", "development").lower() == "production"
    response.set_cookie(
        key=CART_COOKIE_NAME,
        value=cart_id,
        max_age=CART_COOKIE_MAX_AGE_SECONDS,
        path="/",
        secure=is_production,
        httponly=True,
        samesite="lax",
    )


def clear_cart_cookie(response: Response) -> None:
    """Clear the cart cookie (e.g. after order conversion or explicit logout)."""
    response.delete_cookie(
        key=CART_COOKIE_NAME,
        path="/",
    )


# ── Feature flag ─────────────────────────────────────────────────────────


def persistent_cart_enabled() -> bool:
    """Gate per il cart server-side flow.

    Default OFF perché impacta comportamento user-visible (cookie nuovo).
    Per produzione: abilitare per cohort di merchant dopo aver
    stabilizzato il frontend dual-write (Step 4b).
    """
    val = os.environ.get("PERSISTENT_CART_ENABLED", "false")
    return val.strip().lower() in ("true", "1", "yes", "on")


# ── Service operations ───────────────────────────────────────────────────


async def create_empty_cart(
    *,
    organization_id: str,
    store_id: Optional[str],
    source: str = "storefront_classic",
) -> Cart:
    """Create a brand-new empty cart bound to (org, store).

    Returns the persisted Cart. The caller (router) sets the cookie.
    """
    cart = Cart(
        organization_id=organization_id,
        store_id=store_id,
        source=source,
    )
    await cart_repository.create(cart)
    logger.info(
        "cart_service: created empty cart %s for org=%s store=%s source=%s",
        cart.id, organization_id, store_id, source,
    )
    return cart


async def get_cart(cart_id: str, organization_id: str) -> Optional[dict]:
    """Read cart by id. Returns the raw doc (or None if not found / expired).

    Multi-tenant scoped via organization_id (INV-CART-2).
    """
    return await cart_repository.find_by_id(cart_id, organization_id)


async def update_cart_items(
    *,
    cart_id: str,
    organization_id: str,
    items_input: list[CartItemInput],
) -> Optional[dict]:
    """Replace cart items + snapshot product display fields.

    Pulisce items con quantity=0 (semantica delete).
    Per ogni item non-zero, snapshot product_name + unit_price + currency
    da Mongo per UI display (non autoritativo per pricing finale).
    """
    # Filter out remove-marker items (quantity=0)
    effective_items = [i for i in items_input if i.quantity > 0]

    # Snapshot product fields per UI display (best-effort)
    enriched_items: list[CartItem] = []
    if effective_items:
        from database import products_collection
        product_ids = list({i.product_id for i in effective_items})
        # Track E Step 1.2 — fetch ANCHE item_type + stock_quantity per
        # inventory check sotto. Single round-trip (no perf cost).
        cursor = products_collection.find(
            {
                "organization_id": organization_id,
                "id": {"$in": product_ids},
                "is_published": True,
                "is_active": True,
            },
            {
                "_id": 0, "id": 1, "name": 1,
                "unit_price": 1, "currency": 1,
                # E1.2 additions:
                "item_type": 1, "stock_quantity": 1,
            },
        )
        product_map = {doc["id"]: doc async for doc in cursor}

        # Track E Step 1.2 — inventory check eager pre-snapshot.
        # Razionale: failing fast PRIMA di buildare il cart enriched.
        # Raise InsufficientStockError (caller HTTP layer maps to 409).
        # Pattern industry-standard (Shopify cart add returns rejection).
        # Atomic guarantee rimane al confirm_order (try_decrement_stock).
        from core.inventory_check import check_cart_items_inventory
        check_cart_items_inventory(
            items=[{"product_id": i.product_id, "quantity": i.quantity}
                   for i in effective_items],
            products_by_id=product_map,
        )

        for inp in effective_items:
            prod = product_map.get(inp.product_id)
            snapshot_name = prod.get("name") if prod else None
            snapshot_price = prod.get("unit_price") if prod else None
            snapshot_currency = prod.get("currency") if prod else None

            enriched_items.append(CartItem(
                product_id=inp.product_id,
                quantity=inp.quantity,
                occurrence_id=inp.occurrence_id,
                ticket_tier_id=inp.ticket_tier_id,
                rental_date_from=inp.rental_date_from,
                rental_date_to=inp.rental_date_to,
                rental_notes=inp.rental_notes,
                booking_date=inp.booking_date,
                booking_start_time=inp.booking_start_time,
                booking_end_time=inp.booking_end_time,
                booking_end_date=inp.booking_end_date,
                attendees=inp.attendees,
                service_option_id=inp.service_option_id,
                service_custom_request=inp.service_custom_request,  # R4
                extra_selections=inp.extra_selections,  # R2
                product_name_snapshot=snapshot_name,
                unit_price_snapshot=snapshot_price,
                currency_snapshot=snapshot_currency,
            ))

    return await cart_repository.update_items(cart_id, organization_id, enriched_items)


async def bind_customer_email(
    *,
    cart_id: str,
    organization_id: str,
    customer_email: str,
    customer_name: Optional[str] = None,
    customer_phone: Optional[str] = None,
) -> Optional[dict]:
    """Bind a customer email to cart (typically when customer enters checkout).

    Also creates/finds CRM customer via INV-1 atomic upsert and links the id.
    Used pre-checkout per pre-populare customer data + sblocca abandon recovery.
    """
    # Crea/trova customer atomico per INV-1
    customer_id = None
    if customer_email and customer_name:
        try:
            customer_id, _was_created = await upsert_by_email(
                organization_id,
                name=customer_name,
                email=customer_email,
                phone=customer_phone,
                source="cart_email_capture",
            )
        except Exception as exc:
            logger.warning(
                "cart_service.bind_customer_email: upsert failed: %s",
                exc,
            )

    return await cart_repository.update_customer_binding(
        cart_id,
        organization_id,
        customer_id=customer_id,
        customer_email=customer_email,
    )


async def merge_anonymous_to_account(
    *,
    cart_id: str,
    organization_id: str,
    customer_account_id: str,
) -> Optional[dict]:
    """Bind anonymous cart to a logged-in customer account.

    Triggered when guest with cart logs into customer portal mid-cart.
    """
    return await cart_repository.update_customer_binding(
        cart_id,
        organization_id,
        customer_account_id=customer_account_id,
    )


async def clear_cart(cart_id: str, organization_id: str) -> Optional[dict]:
    """Empty cart items (cart_id rimane vivo per re-use)."""
    return await cart_repository.clear_items(cart_id, organization_id)


# ── Response builders ────────────────────────────────────────────────────


def build_response(cart_doc: dict) -> CartResponse:
    """Convert raw Mongo doc → public-safe CartResponse.

    Compute derived fields: item_count, subtotal_snapshot, currency_snapshot.
    These are NON-AUTHORITATIVE — solo per UI display. Il backend
    ricalcola al checkout dal product attuale.
    """
    items_raw = cart_doc.get("items", []) or []
    items = [CartItem.model_validate(it) for it in items_raw]

    item_count = sum(int(it.quantity) for it in items)
    subtotal = round(
        sum((it.unit_price_snapshot or 0) * it.quantity for it in items),
        2,
    )
    currency = next(
        (it.currency_snapshot for it in items if it.currency_snapshot),
        None,
    )

    from datetime import datetime
    def _parse_dt(value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # Handle Z suffix
                if value.endswith("Z"):
                    value = value[:-1] + "+00:00"
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    return CartResponse(
        id=cart_doc["id"],
        organization_id=cart_doc["organization_id"],
        store_id=cart_doc.get("store_id"),
        items=items,
        customer_email=cart_doc.get("customer_email"),
        item_count=item_count,
        subtotal_snapshot=subtotal,
        currency_snapshot=currency,
        created_at=_parse_dt(cart_doc.get("created_at")),
        updated_at=_parse_dt(cart_doc.get("updated_at")),
        expires_at=_parse_dt(cart_doc.get("expires_at")),
        source=cart_doc.get("source", "storefront_classic"),
    )
