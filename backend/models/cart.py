"""Cart model — server-side persistent shopping cart.

Phase 0 Step 4 della roadmap di evoluzione e-commerce (ADR-001).

Razionale
=========
Il carrello classic vive in sessionStorage del browser (10 state slice
gestiti da useStorefrontCart hook frontend). Limiti:
  · si perde se l'utente chiude browser, cambia device, apre incognito
  · niente abandon recovery (email "hai lasciato 3 articoli")
  · niente cross-device sync (mobile → desktop)
  · incompatibile con embed widget cross-origin (Stream A futuro)
  · incompatibile con AI-generated sites (Stream B futuro)

Soluzione: ``Cart`` entity persistita server-side con cookie ``afianco_cart_id``
(HttpOnly Secure SameSite=Lax, 60gg TTL).

Migration strategy (dual-write per 60 giorni)
=============================================
Lo storefront frontend continua a leggere/scrivere su sessionStorage E
ANCHE sul server. I due rappresentazioni convergono su ogni operation.
Dopo 60 giorni la sessionStorage logic verrà rimossa. ADR-001 Decision 1.

Invarianti
==========
INV-CART-1  Atomic operations (find_one_and_update + concurrency control)
INV-CART-2  Multi-tenant isolation (organization_id obbligatorio)
INV-CART-3  expires_at sempre nel futuro per cart attivi (cleanup job)
INV-CART-4  Items shape compatibile con OrderRequestItem (zero-copy conversion)
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .common import generate_id, utc_now


# ── Cart TTL ─────────────────────────────────────────────────────────────

# 60 giorni di TTL su cart attivi. Tale finestra cattura ~95% dei carrelli
# abbandonati che vengono riattivati (vs ~70% con 30 giorni).
CART_TTL_DAYS = 60


def _default_expires_at() -> datetime:
    """Default cart expiration: now + CART_TTL_DAYS."""
    return utc_now() + timedelta(days=CART_TTL_DAYS)


# ── Cart Item ────────────────────────────────────────────────────────────


class CartItem(BaseModel):
    """Cart item — shape compatibile con OrderRequestItem.

    Quando il cart viene convertito a ordine (checkout), i campi sono
    mappati 1:1 su ``OrderRequestItem``. INV-CART-4: questa simmetria
    garantisce zero perdita di informazione durante la conversione.

    Campi di display snapshot (product_name_snapshot, unit_price_snapshot)
    sono cached al momento dell'add-to-cart per evitare refetch del
    prodotto a ogni read del cart. Non sono autoritativi per il prezzo
    finale — il backend ricalcola al checkout dal product attuale.
    """
    model_config = ConfigDict(extra="ignore")

    # ── Required: product reference ──
    product_id: str
    quantity: float = Field(gt=0)

    # ── Event ticket type-specific ──
    occurrence_id: Optional[str] = None
    ticket_tier_id: Optional[str] = None

    # ── Rental type-specific ──
    rental_date_from: Optional[str] = Field(default=None, max_length=10)  # ISO yyyy-mm-dd
    rental_date_to: Optional[str] = Field(default=None, max_length=10)
    rental_notes: Optional[str] = Field(default=None, max_length=500)

    # ── Booking type-specific (v12.0) ──
    booking_date: Optional[str] = Field(default=None, max_length=10)
    booking_start_time: Optional[str] = Field(default=None, max_length=5)   # HH:MM
    booking_end_time: Optional[str] = Field(default=None, max_length=5)
    booking_end_date: Optional[str] = Field(default=None, max_length=10)    # Cross-day (Onda 17)

    # ── Attendees (F1 Onda 8) ──
    # Stored as raw dicts for flexibility (Pydantic AttendeeInfo validated upstream)
    attendees: Optional[List[Dict[str, Any]]] = None

    # ── Service options (F5 Onda 12) ──
    service_option_id: Optional[str] = None

    # ── Richiesta personalizzata (R4) — slot proposto fuori dalle regole di
    #    disponibilità. Forwarded a OrderRequestItem al checkout. ──
    service_custom_request: bool = False

    # ── Extras selezionati (R2 / Onda 16) — optional/radio oltre ai mandatory.
    #    Dict grezzo (ExtraSelections validato a valle in OrderLineCreate). ──
    extra_selections: Optional[Dict[str, Any]] = None

    # ── Display snapshot (cached, non-authoritative for pricing) ──
    product_name_snapshot: Optional[str] = Field(default=None, max_length=255)
    unit_price_snapshot: Optional[float] = Field(default=None, ge=0)
    currency_snapshot: Optional[str] = Field(default=None, max_length=3)


# ── Cart Document ────────────────────────────────────────────────────────


class Cart(BaseModel):
    """Server-side persistent shopping cart.

    Bound to ``(organization_id, store_id)`` for multi-tenant isolation.
    Cookie ``afianco_cart_id`` carries the id across requests.

    Lifecycle:
      created → updated × N → converted_to_order → soft_delete (or expired)
    """
    model_config = ConfigDict(extra="ignore")

    # ── Identity ──
    id: str = Field(default_factory=lambda: f"cart_{generate_id()}")
    organization_id: str
    store_id: Optional[str] = None

    # ── Customer binding (null for guests) ──
    customer_id: Optional[str] = None         # CRM customer id, set on first checkout attempt
    customer_email: Optional[EmailStr] = None # set when user types email at checkout
    customer_account_id: Optional[str] = None # set when user logs in mid-cart

    # ── Cart contents ──
    items: List[CartItem] = Field(default_factory=list)

    # ── Source attribution (per future analytics: classic vs embed vs ai-site) ──
    # Default "storefront_classic"; embed widget setterà "embed_widget",
    # AI-site renderer setterà "ai_site".
    source: str = Field(default="storefront_classic", max_length=32)

    # ── Metadata bag (extensible without schema migration) ──
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # ── Timestamps ──
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(default_factory=_default_expires_at)

    # ── Optional: abandon recovery tracking ──
    recovered_at: Optional[datetime] = None   # set if user followed a recovery email link
    converted_to_order_id: Optional[str] = None  # set when cart → order checkout completed


# ── API DTOs ─────────────────────────────────────────────────────────────


class CartCreate(BaseModel):
    """Payload for POST /api/public/cart — create empty cart bound to store."""
    slug: str = Field(min_length=3, max_length=50)  # Store slug to bind cart to
    source: str = Field(default="storefront_classic", max_length=32)


class CartItemInput(BaseModel):
    """Payload for adding/updating an item via PATCH /api/public/cart/{id}.

    Same shape as CartItem but quantity may be 0 (= remove item).
    """
    product_id: str
    quantity: float = Field(ge=0)  # 0 = remove
    occurrence_id: Optional[str] = None
    ticket_tier_id: Optional[str] = None
    rental_date_from: Optional[str] = Field(default=None, max_length=10)
    rental_date_to: Optional[str] = Field(default=None, max_length=10)
    rental_notes: Optional[str] = Field(default=None, max_length=500)
    booking_date: Optional[str] = Field(default=None, max_length=10)
    booking_start_time: Optional[str] = Field(default=None, max_length=5)
    booking_end_time: Optional[str] = Field(default=None, max_length=5)
    booking_end_date: Optional[str] = Field(default=None, max_length=10)
    attendees: Optional[List[Dict[str, Any]]] = None
    service_option_id: Optional[str] = None
    service_custom_request: bool = False  # R4
    extra_selections: Optional[Dict[str, Any]] = None  # R2


class CartUpdate(BaseModel):
    """Payload for PATCH /api/public/cart/{id} — replace items + optionally bind email."""
    items: Optional[List[CartItemInput]] = None
    customer_email: Optional[EmailStr] = None


class CartMergeRequest(BaseModel):
    """Payload for POST /api/public/cart/{id}/merge — merge anonymous → authenticated.

    Used when guest with cart logs into customer portal and we want to
    bind the existing cart to their account.
    """
    customer_account_id: str = Field(min_length=1)


class CartResponse(BaseModel):
    """Public-safe cart response shape — CTR-CART-1 invariant.

    Includes computed totals for UI display. Items are simplified to
    only what the storefront UI needs (no internal metadata).
    """
    id: str
    organization_id: str
    store_id: Optional[str] = None
    items: List[CartItem]
    customer_email: Optional[str] = None
    item_count: int                     # sum of quantities (computed)
    subtotal_snapshot: float            # sum of unit_price_snapshot × qty (computed, non-authoritative)
    currency_snapshot: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    source: str
