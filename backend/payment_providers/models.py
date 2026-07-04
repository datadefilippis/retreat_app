"""
Provider-agnostic data shapes for the payment abstraction layer.

These are the *only* types the application layer (CheckoutService,
routers, webhook dispatcher) sees. Concrete providers translate to/from
their own SDK objects internally.

Keeping the shapes here — rather than scattering them across
``stripe/`` or future ``datatrans/`` — makes adding a second provider
a pure additive change: the new provider only has to implement the
abstract methods in ``base.py`` and serialize to/from these models.

All amounts are kept in MAJOR units (e.g. 49.50 EUR/CHF) as
``Decimal``. Conversion to minor units (cents/centimes) is the
provider's responsibility, since each one has its own quirks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class CheckoutLineItem:
    """One line on the checkout session."""
    name: str
    quantity: int
    unit_amount: Decimal
    # Optional product/SKU reference for the provider's analytics.
    sku: Optional[str] = None


@dataclass(frozen=True)
class CheckoutSessionRequest:
    """Provider-agnostic checkout creation payload.

    The CheckoutService builds this from the Order + Org and passes it
    to ``provider.create_checkout_session(req)``. Providers must NOT
    reach back into the Order/Org models — everything they need lives
    here.

    Fields:
      org_id           caller's org id (used for connected account lookup)
      order_id         caller's order id (round-tripped via metadata)
      currency         ISO 4217 uppercase ("EUR", "CHF")
      line_items       list of CheckoutLineItem
      customer_email   pre-fill hint, may be None
      success_url      where the customer lands after a successful pay
      cancel_url       where the customer lands on cancel/abort
      metadata         caller-defined key-values; providers must echo
                       them back on webhooks (Stripe does this natively)
      idempotency_key  optional; providers should use this to dedupe
                       retries on the wire
      application_fee_percent  % of total to charge as platform fee
                       (Stripe Connect "application_fee_amount").
                       0 means "do not pass any fee".
    """
    org_id: str
    order_id: str
    currency: str
    line_items: tuple[CheckoutLineItem, ...]
    success_url: str
    cancel_url: str
    customer_email: Optional[str] = None
    metadata: dict[str, str] = field(default_factory=dict)
    idempotency_key: Optional[str] = None
    application_fee_percent: Decimal = Decimal("0")
    # R1 — importo sconto (coupon) in major units. Il provider lo applica come
    # discount nativo (Stripe coupon one-off) così l'addebito = Σ(line_items) −
    # discount = order.total. 0 = nessuno sconto.
    discount_amount: Decimal = Decimal("0")


@dataclass(frozen=True)
class CheckoutSessionResult:
    """What a provider returns after creating a checkout session."""
    url: str                       # hosted checkout URL the customer opens
    session_id: str                # provider-side reference (cs_xxx for Stripe)
    provider: str                  # "stripe", "datatrans", ...
    connected_account: Optional[str] = None
    # Methods Stripe (or the next provider) actually offered to the
    # customer — useful for audit / debugging.
    payment_method_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class AccountCapabilities:
    """Subset of a connected account's capabilities relevant to checkout.

    Each provider populates the keys it knows about. Currently TWINT
    is the only Swiss-specific gating signal we surface to the UI;
    everything else flows through ``other`` for forward-compat without
    schema changes.
    """
    card_active: bool = False
    twint_active: bool = False
    sepa_debit_active: bool = False
    other: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedEvent:
    """Provider-agnostic webhook event shape.

    The router pipeline goes:
        raw_event_bytes
        → provider.verify_webhook(payload, sig, secret)
        → provider.parse_event(verified_event) → NormalizedEvent
        → CheckoutService.reconcile(normalized_event)

    Concrete providers normalize their own event types into one of the
    canonical ``type`` strings below. The application layer never
    branches on a provider name.
    """
    # Canonical event type strings — keep this list narrow and explicit.
    # Add a new constant only when *all* providers need to react to it.
    TYPE_CHECKOUT_COMPLETED = "checkout.completed"
    TYPE_PAYMENT_REFUNDED = "payment.refunded"
    TYPE_PAYMENT_DISPUTED = "payment.disputed"

    type: str
    provider: str                      # "stripe", "datatrans", ...
    provider_event_id: str             # raw provider event id (for dedup)
    connected_account: Optional[str]
    order_id: Optional[str]            # echoed from metadata
    org_id: Optional[str]              # echoed from metadata
    currency: Optional[str]            # uppercase ISO 4217
    amount: Optional[Decimal]          # major units
    payment_intent_id: Optional[str]   # provider-side payment ref
    raw: dict                          # full provider-side dict (for audit)
