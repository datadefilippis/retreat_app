"""
Order domain model — structured sales transactions.

An Order represents a sale of N products to a customer, with status
tracking and payment lifecycle.  OrderLines are embedded in the Order
document (not a separate collection).

When an Order is confirmed (status: draft → confirmed), a separate
service generates SalesRecords for the cashflow module.  This model
defines only the data contracts — no business logic here.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .common import generate_id, utc_now
from .attendee import AttendeeInfo
from .product_extra import OrderLineExtra, ExtraSelections


# ── Enums ───────────────────────────────────────────────────────────────────

class OrderStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderPaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


# ── Fulfillment (v10.0) ───────────────────────────────────────────────────

class FulfillmentMode(str, Enum):
    SHIPPING = "shipping"
    LOCAL_PICKUP = "local_pickup"
    MANUAL_ARRANGEMENT = "manual_arrangement"
    NOT_REQUIRED = "not_required"


class FulfillmentStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    READY_FOR_PICKUP = "ready_for_pickup"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    PICKED_UP = "picked_up"
    FULFILLED = "fulfilled"                 # Neutral terminal for manual_arrangement


class ShippingAddressDetails(BaseModel):
    """Structured shipping address — additive layer on top of the legacy
    free-text `shipping_address` field.

    When the client submits this object, the backend:
      1. Persists it verbatim on `Fulfillment.shipping_address_details`
      2. Synthesizes the flattened canonical string into
         `Fulfillment.shipping_address` so readers that only know the old
         field (email templates, PDF receipts, legacy admin views) keep
         working without changes.

    Every field is Optional at persistence time — this lets legacy orders
    load the embedded object gracefully even if only partial data exists.
    Hard required-field validation lives at the payload boundary
    (see ShippingAddressInput in routers/public.py), not here.
    """
    model_config = ConfigDict(extra="ignore")
    recipient_name: Optional[str] = Field(default=None, max_length=160)
    line1: Optional[str] = Field(default=None, max_length=200)      # via / street
    civic: Optional[str] = Field(default=None, max_length=20)        # civico
    postal_code: Optional[str] = Field(default=None, max_length=16)  # CAP
    city: Optional[str] = Field(default=None, max_length=120)
    # Sigla 2 lettere per IT (MI, RM, TO) — max 8 per tollerare codici
    # territoriali esteri (es. codici di contea UK).
    province: Optional[str] = Field(default=None, max_length=8)
    # ISO 3166-1 alpha-2. Default IT al submit, ma lasciato Optional in
    # persistenza per non forzare ordini storici.
    country: Optional[str] = Field(default=None, max_length=2)


class Fulfillment(BaseModel):
    """Embedded fulfillment state on an Order. One order = one fulfillment."""
    mode: str = "not_required"              # FulfillmentMode value
    status: str = "not_required"            # FulfillmentStatus value
    # Legacy free-text flattened address. Always populated for
    # mode=shipping — when the client submits shipping_address_details,
    # the backend synthesizes this string server-side. Readers that only
    # know this field (email / PDF / old admin views) keep working.
    shipping_address: Optional[str] = None
    # Structured source of truth. None for legacy orders + clients that
    # still submit only the free-text string. When present, takes
    # precedence over shipping_address for admin renderers that opt in.
    shipping_address_details: Optional[ShippingAddressDetails] = None
    fulfillment_notes: Optional[str] = None # Notes for any mode (pickup, delivery, arrangement)
    shipped_at: Optional[str] = None        # ISO UTC timestamp
    delivered_at: Optional[str] = None      # ISO UTC timestamp (or fulfilled_at for manual)
    # Release 1 (Physical) — carrier tracking captured at mark_shipped time. Both
    # optional; when populated they flow into the fulfillment-update email so the
    # customer can follow the parcel without contacting support.
    tracking_number: Optional[str] = Field(default=None, max_length=120)
    tracking_url: Optional[str] = Field(default=None, max_length=500)
    # Shipping feature — snapshot of the shipping option chosen at checkout.
    # Stored on the order so subsequent admin edits to the option row never
    # rewrite historical order totals. `shipping_cost` is the source of truth
    # for the shipping line on the order and is added to `Order.total`.
    shipping_option_id: Optional[str] = Field(default=None, max_length=64)
    shipping_option_label: Optional[str] = Field(default=None, max_length=200)
    shipping_cost: float = Field(default=0.0, ge=0)


# ── OrderLine (embedded in Order) ───────────────────────────────────────────

class OrderLineBase(BaseModel):
    """A single line item in an order — references a product with snapshot."""
    product_id: str                               # FK → products._id (required)
    product_name: str                             # Snapshot at order time
    sku: Optional[str] = None                     # Snapshot from product.sku
    category: Optional[str] = None                # Snapshot from product.category
    item_type: str = "physical"                   # Snapshot: physical|service|rental|event_ticket
    transaction_mode: str = "request"              # Snapshot: request|direct|approval
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)               # Price at order time (snapshot)
    discount_pct: float = Field(default=0, ge=0, le=100)
    line_total: float = Field(ge=0)               # quantity * unit_price * (1 - discount_pct/100)
    # ── Event occurrence snapshot (optional) ────────────────────────────────
    occurrence_id: Optional[str] = None
    occurrence_start_at: Optional[str] = None
    occurrence_location: Optional[str] = None
    # ── Event ticket tier snapshot (optional, E1) ───────────────────────────
    # Stored on the order line so admin views never lose the tier label even
    # if the tier is later renamed or deleted. ticket_tier_id is the FK used
    # by capacity release on cancel; ticket_tier_label is the human-readable
    # snapshot displayed in dashboards / invoices / emails.
    ticket_tier_id: Optional[str] = None
    ticket_tier_label: Optional[str] = None
    # ── Service option snapshot (optional, F5 Onda 12) ───────────────────────
    # Mirrors the tier pattern for service products: when the customer
    # picked a specific service option (radio-select), these fields snapshot
    # the choice so invoices / dashboards / CSV exports keep showing the
    # correct label even after the merchant edits the option later.
    service_option_id: Optional[str] = None
    service_option_label: Optional[str] = None
    # ── Custom request flag (R4, Onda 14 Parte B persistence) ────────────────
    # True when the customer proposed booking_date/start/end OUTSIDE the
    # product's availability rules (product.metadata.service_allow_custom_request).
    # Previously consumed only by the validator and then LOST — now snapshot on
    # the line so the admin sees "richiesta personalizzata" and confirms the
    # slot manually. Default False = standard slot picked from availability.
    service_custom_request: bool = False
    # ── Attendees (optional, F1 Onda 8) ────────────────────────────────────
    # One entry per seat, populated only when the product requires per-ticket
    # holder details (product.metadata.requires_attendee_details). When set,
    # len(attendees) must equal quantity. Copied into each IssuedTicket as
    # holder_name / holder_email / holder_phone at confirm time. None (the
    # default) = backward-compat single-holder flow (all tickets inherit
    # customer_name / customer_email).
    attendees: Optional[List[AttendeeInfo]] = None
    # ── Rental request snapshot (optional) ─────────────────────────────────
    rental_date_from: Optional[str] = None     # ISO date: "2026-08-14"
    rental_date_to: Optional[str] = None       # ISO date: "2026-08-17"
    rental_notes: Optional[str] = None
    # ── Booking slot snapshot (optional, v12.0) ───────────────────────────
    booking_date: Optional[str] = None         # ISO date: "2026-05-15" (start date)
    booking_start_time: Optional[str] = None   # HH:MM: "10:00"
    booking_end_time: Optional[str] = None     # HH:MM: "11:00"
    # Onda 17 — cross-day slot support. When None (default), the reservation
    # ends on the same day as booking_date (historic semantics). When set, the
    # slot spans from booking_date + booking_start_time to booking_end_date +
    # booking_end_time. Backend reads must treat booking_end_date ?? booking_date
    # to stay back-compat with legacy orders.
    booking_end_date: Optional[str] = None     # ISO date (same-day when None)
    # ── Product extras (Onda 16 Prenotazione consolidation) ──────────────
    # One entry per applied ProductExtra (mandatory auto-merged by server,
    # optional/radio_variant selected by customer). Snapshot is FROZEN at
    # create time — edits / deletes on the underlying ProductExtra NEVER
    # alter historical order totals.
    #
    # line_total now equals:
    #   base = quantity * unit_price * (1 - discount_pct/100)
    #   line_total = base + extras_total
    #
    # For old orders written before Onda 16, extras defaults to [] and
    # extras_total to 0.0 — totals and reads stay correct.
    extras: List[OrderLineExtra] = Field(default_factory=list)
    extras_total: float = Field(default=0.0, ge=0)


class OrderLineCreate(BaseModel):
    """Input model for creating an order line."""
    product_id: str
    quantity: float = Field(gt=0)
    unit_price: Optional[float] = Field(default=None, ge=0)  # If null, use product.unit_price
    discount_pct: float = Field(default=0, ge=0, le=100)
    occurrence_id: Optional[str] = None           # For event_ticket items
    ticket_tier_id: Optional[str] = None          # For event_ticket items (E1)
    # Rental request context (storefront only)
    rental_date_from: Optional[str] = None       # ISO date
    rental_date_to: Optional[str] = None         # ISO date
    rental_notes: Optional[str] = Field(default=None, max_length=500)
    # Booking slot (v12.0) + Onda 17 cross-day end
    booking_date: Optional[str] = None           # ISO date (start)
    booking_start_time: Optional[str] = None     # HH:MM
    booking_end_time: Optional[str] = None       # HH:MM
    booking_end_date: Optional[str] = None       # ISO date (same-day if None)
    # Attendees (F1 Onda 8) — one per seat; required when the event product
    # has metadata.requires_attendee_details = True.
    attendees: Optional[List[AttendeeInfo]] = None
    # F5 Onda 12 — service option picked by the customer (radio-select)
    # for item_type="service" products. None for events/physical/rental/booking.
    #
    # DEPRECATED by Onda 16: prefer `extra_selections.radio_picks` which
    # supports multi-group variants. When this scalar is present, the
    # server auto-translates into a single-entry radio_picks for
    # backward-compat (one release window).
    service_option_id: Optional[str] = None
    # R4 — customer proposed a slot outside the availability rules. Validated
    # against product.metadata.service_allow_custom_request, then snapshot on
    # the persisted line (OrderLineBase.service_custom_request).
    service_custom_request: bool = False
    # Onda 16 — richer extras selection. Supports mandatory (server-merged
    # regardless of client input), optional (checkbox multi-select), and
    # radio_variant (mutually exclusive per group_key).
    extra_selections: Optional[ExtraSelections] = None


# ── Order ───────────────────────────────────────────────────────────────────

class OrderBase(BaseModel):
    """Shared fields between create and full Order."""
    customer_id: str                              # FK → customers._id (required)
    currency: str = "EUR"
    notes: Optional[str] = Field(default=None, max_length=2000)
    due_date: Optional[str] = None                # ISO date — payment due
    order_date: Optional[str] = None              # ISO date — date of the order (defaults to created_at date)


class OrderCreate(OrderBase):
    """Input model for POST /orders."""
    items: List[OrderLineCreate] = Field(min_length=1)


class OrderUpdate(BaseModel):
    """Partial update model for PATCH /orders/{id}. Status changes via dedicated endpoints."""
    model_config = ConfigDict(extra="ignore")

    customer_id: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[str] = None
    order_date: Optional[str] = None
    items: Optional[List[OrderLineCreate]] = None


class Order(OrderBase):
    """Full Order document as stored in MongoDB."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    order_number: Optional[str] = None            # Human-readable, auto-generated (e.g. "ORD-0042")
    status: OrderStatus = OrderStatus.DRAFT
    payment_status: OrderPaymentStatus = OrderPaymentStatus.PENDING
    payment_intent: str = "none"                  # none | required | collected | waived
    payment_checkout: Optional[Dict[str, Any]] = None  # {url, provider, reference, created_at, expires_at}
    items: List[OrderLineBase] = Field(default_factory=list)
    subtotal: float = 0                           # Sum of line_total
    total: float = 0                              # subtotal (discounts already in line_total)
    source: str = "manual"                        # "manual" | "storefront" | "storefront_direct" | "storefront_approval"
    customer_account_id: Optional[str] = None     # FK → customer_accounts.id; null = guest order (v9.0)
    fulfillment: Optional[Dict[str, Any]] = None  # Embedded fulfillment state (v10.0)
    contact_phone: Optional[str] = None           # Customer contact phone for this order (v10.0)
    coupon_code: Optional[str] = None              # Applied promo code (v13.0)
    discount_total: float = 0                      # Total discount amount applied (v13.0)
    # F2 Onda 9 — snapshot of merchant-defined order_fields values filled
    # at checkout (keyed by FieldConfig.id). Survives product metadata
    # edits — historical orders keep whatever was asked at that time.
    order_fields_data: Dict[str, Any] = Field(default_factory=dict)
    # F4 Onda 11 — ISO timestamp of T&C acceptance at checkout. Null for
    # orders where T&C were not required. Legal audit trail.
    terms_accepted_at: Optional[str] = None

    # ── Wave GDPR-Commerce CG-5 (2026-05-19) — per-order consent snapshot ──
    #
    # SEPARATE from the legacy ``terms_accepted_at`` field above. That
    # field is just an ISO timestamp; these capture the EXACT version
    # of Privacy + Terms the customer saw at checkout time, so a future
    # compliance audit can answer "what document did the customer
    # actually accept for this order?".
    #
    # ALL fields are Optional → legacy orders (pre-CG-5) deserialise
    # cleanly with None values. Orders placed on stores without GDPR
    # published also stay at None — these fields ONLY get populated
    # when the merchant has explicitly published their legal docs and
    # the customer accepted at checkout.
    #
    # The corresponding consent_audit record (one per doc_type) is
    # the immutable legal proof trail; this denormalized snapshot on
    # the Order is the fast path for showing the merchant which
    # version was in force at order time.
    gdpr_terms_version: Optional[str] = None       # "v1.0:abc123def456..."
    gdpr_privacy_version: Optional[str] = None     # "v1.0:abc123def456..."
    gdpr_locale: Optional[str] = None              # locale frozen at checkout
    gdpr_accepted_at: Optional[str] = None         # ISO UTC of click
    # Marketing is OPTIONAL — None means the merchant did not ask for it
    # (no GDPR config OR not enabled). True/False are explicit customer
    # choices. None is NOT the same as False semantically.
    gdpr_marketing_accepted: Optional[bool] = None

    # ── 2026-05-20 — Legacy import provenance ─────────────────────────────
    #
    # Separates the CANONICAL ``order_number`` (always ``ORD-XXXX``,
    # generated by the runtime) from the IDENTIFIER carried by the source
    # system when an order is imported from Shopify, WooCommerce, a
    # custom ERP, or a legacy CSV.
    #
    # The merchant keeps full traceability of their original numbering
    # for receipts / customer search / invoice cross-reference; the
    # internal afianco counter stays clean and the parser in
    # ``get_next_order_number`` doesn't have to learn every foreign
    # format.
    #
    # All three fields are Optional + nullable → backward-compat with
    # every existing order on disk (they get None on read).
    #
    # The non-unique compound index ``(organization_id, external_source,
    # external_order_number)`` (declared in database.py) powers
    # idempotent re-imports: the import service skips a row when a
    # match exists for that (source, external id) pair within the org.
    external_order_number: Optional[str] = None   # e.g. "#1001" from Shopify
    external_source: Optional[str] = None         # "shopify" | "woocommerce" | "fatture_in_cloud" | ...
    external_imported_at: Optional[str] = None    # ISO UTC of the import batch

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class OrderResponse(BaseModel):
    """Response model for API endpoints."""
    id: str
    organization_id: str
    order_number: Optional[str] = None
    customer_id: str
    customer_name: Optional[str] = None           # Denormalized for display (populated at read time)
    status: OrderStatus
    payment_status: OrderPaymentStatus
    items: List[OrderLineBase]
    subtotal: float
    total: float
    currency: str
    notes: Optional[str] = None
    due_date: Optional[str] = None
    order_date: Optional[str] = None
    source: str
    customer_account_id: Optional[str] = None
    fulfillment: Optional[Dict[str, Any]] = None
    contact_phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime
