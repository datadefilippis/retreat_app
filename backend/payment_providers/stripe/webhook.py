"""
Stripe webhook signature verification + provider-agnostic event parser.

These helpers are split out of :class:`StripeProvider` so they can be
tested without instantiating the whole provider. The provider's
``verify_webhook`` and ``parse_event`` methods are thin wrappers around
the functions here.

Security note: signature verification is the *single line of defense*
against webhook replay/spoofing. We always raise on a bad signature;
callers must NOT proceed with the event when this raises.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Mapping, Optional

from payment_providers.exceptions import WebhookSignatureInvalid
from payment_providers.models import NormalizedEvent

logger = logging.getLogger(__name__)


# Map Stripe event types → canonical NormalizedEvent.type strings.
# Anything not in this map is normalised with ``type=""`` so the
# dispatcher can log + skip without crashing.
_STRIPE_EVENT_TYPE_MAP = {
    "checkout.session.completed": NormalizedEvent.TYPE_CHECKOUT_COMPLETED,
    "charge.refunded":             NormalizedEvent.TYPE_PAYMENT_REFUNDED,
    "charge.dispute.created":      NormalizedEvent.TYPE_PAYMENT_DISPUTED,
}


def verify_stripe_webhook(
    payload: bytes,
    signature_header: str,
    secret: str,
    *,
    stripe_module,
) -> dict:
    """Verify the Stripe-Signature header and return the parsed event dict.

    Wraps ``stripe.Webhook.construct_event``. Raises
    :class:`WebhookSignatureInvalid` on any verification failure
    (bad signature, malformed payload, missing secret) — the router
    layer maps that to HTTP 400 and refuses to act on the event.

    ``stripe_module`` is injected to keep the SDK import contained
    inside ``payment_providers/stripe/`` and to make this function
    test-friendly.
    """
    if not secret:
        raise WebhookSignatureInvalid(
            "Webhook secret is empty — refusing to verify",
            provider="stripe",
        )
    try:
        return stripe_module.Webhook.construct_event(
            payload, signature_header, secret,
        )
    except Exception as exc:
        logger.warning(
            "stripe.webhook: signature verification failed: %s", exc,
        )
        # Track O Step 3.2 — capture per alert [P0] Payment failure spike.
        # Signature fail puo' essere: attaccante che forge webhook OR webhook
        # secret rotated senza update env. Entrambi i casi critici (attack
        # signal OR money flow broken).
        try:
            from core.observability.sentry import capture_with_tags
            capture_with_tags(
                exc,
                action="payment_webhook",
                surface="api",
                extra={
                    "exception_type": type(exc).__name__,
                    "signature_present": bool(signature_header),
                },
            )
        except Exception:
            pass
        raise WebhookSignatureInvalid(
            f"Stripe webhook signature invalid: {exc}",
            provider="stripe",
        ) from exc


def _amount_major(amount_minor: Optional[int]) -> Optional[Decimal]:
    """Stripe ships amounts in minor units (cents/centimes); convert."""
    if amount_minor is None:
        return None
    try:
        return Decimal(amount_minor) / Decimal(100)
    except Exception:
        return None


def _extract_currency(d: Mapping) -> Optional[str]:
    raw = d.get("currency")
    if not raw:
        return None
    return str(raw).upper()


def parse_stripe_event(
    event: Mapping,
    *,
    connected_account: Optional[str] = None,
) -> NormalizedEvent:
    """Translate a verified Stripe event dict into :class:`NormalizedEvent`.

    Handles the three event families we care about today
    (checkout completion, refund, dispute) and returns a
    :class:`NormalizedEvent` with ``type=""`` for anything else, so
    the dispatcher can log+skip cleanly without ``KeyError`` games.

    The full Stripe event dict is preserved on ``raw`` so audit logs
    and downstream services that still want provider-specific fields
    (e.g. ``stripe_payment_intent_id`` for the orders collection)
    can read them without re-parsing.
    """
    if not isinstance(event, Mapping):
        # Defensive — never let upstream crash here on a malformed
        # payload; let the dispatcher decide on a no-op.
        return NormalizedEvent(
            type="",
            provider="stripe",
            provider_event_id="",
            connected_account=connected_account,
            order_id=None,
            org_id=None,
            currency=None,
            amount=None,
            payment_intent_id=None,
            raw={},
        )

    raw_type = str(event.get("type") or "")
    canonical_type = _STRIPE_EVENT_TYPE_MAP.get(raw_type, "")
    event_id = str(event.get("id") or "")
    obj = event.get("data", {}).get("object", {}) if isinstance(event.get("data"), Mapping) else {}
    if not isinstance(obj, Mapping):
        obj = {}

    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), Mapping) else {}
    order_id = metadata.get("order_id") if isinstance(metadata, Mapping) else None
    org_id = metadata.get("org_id") if isinstance(metadata, Mapping) else None

    # Per event-type extraction
    currency: Optional[str] = None
    amount: Optional[Decimal] = None
    payment_intent_id: Optional[str] = None

    if raw_type == "checkout.session.completed":
        currency = _extract_currency(obj)
        amount = _amount_major(obj.get("amount_total"))
        pi = obj.get("payment_intent")
        if isinstance(pi, str):
            payment_intent_id = pi
        elif isinstance(pi, Mapping):
            payment_intent_id = pi.get("id")
    elif raw_type == "charge.refunded":
        currency = _extract_currency(obj)
        amount = _amount_major(obj.get("amount_refunded"))
        pi = obj.get("payment_intent")
        payment_intent_id = pi if isinstance(pi, str) else None
    elif raw_type == "charge.dispute.created":
        currency = _extract_currency(obj)
        amount = _amount_major(obj.get("amount"))
        pi = obj.get("payment_intent")
        payment_intent_id = pi if isinstance(pi, str) else None

    # Fall back to event-level connected account if not supplied
    if connected_account is None:
        connected_account = event.get("account") if isinstance(event.get("account"), str) else None

    return NormalizedEvent(
        type=canonical_type,
        provider="stripe",
        provider_event_id=event_id,
        connected_account=connected_account,
        order_id=order_id if isinstance(order_id, str) else None,
        org_id=org_id if isinstance(org_id, str) else None,
        currency=currency,
        amount=amount,
        payment_intent_id=payment_intent_id,
        raw=dict(event),
    )
