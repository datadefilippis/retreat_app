"""
:class:`StripeProvider` — concrete :class:`PaymentProvider` for Stripe Connect.

This is the ONLY place in the application that ``import stripe`` is
allowed. The linter rule shipped with Sub-stream 2.3 enforces that
``stripe`` cannot be imported from ``services/`` or ``routers/``
anymore — every call goes through this provider.

Behaviour mirrors the legacy ``services/payment_checkout_service``
flow exactly so the Sub-stream 2.3 refactor (which swaps the call
site to go through the registry) is a no-op for merchants.
"""

from __future__ import annotations

import asyncio
import logging
import os
from decimal import Decimal
from typing import Optional

from payment_providers.base import PaymentProvider
from payment_providers.exceptions import (
    AccountNotConfigured,
    ProviderError,
)
from payment_providers.models import (
    AccountCapabilities,
    CheckoutSessionRequest,
    CheckoutSessionResult,
    NormalizedEvent,
)

from .capabilities import fetch_account_capabilities
from .method_types import resolve_payment_method_types
from .webhook import parse_stripe_event, verify_stripe_webhook

logger = logging.getLogger(__name__)


def _get_stripe():
    """Lazy import of the Stripe SDK + API key bootstrap.

    Lazy so the rest of the package can be imported (and unit-tested)
    without the SDK installed in the environment. Pattern is identical
    to ``services/payment_checkout_service._get_stripe`` so the
    behaviour during the Step 2.3 refactor stays bit-for-bit compatible.
    """
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    return stripe


class StripeProvider(PaymentProvider):
    """Concrete :class:`PaymentProvider` for Stripe.

    Stateless. Stored as a singleton in :class:`PaymentProviderRegistry`.
    """

    name = "stripe"

    # ── Checkout ──────────────────────────────────────────────────────────

    async def create_checkout_session(
        self,
        request: CheckoutSessionRequest,
    ) -> CheckoutSessionResult:
        """Create a Stripe Checkout Session on the merchant's
        connected account.

        Mirrors the legacy ``services.payment_checkout_service.create_checkout_session``
        body so the Step 2.3 refactor is invisible to merchants:

          * line_items in price_data shape (currency-aware after Step A3)
          * metadata round-tripped (org_id, order_id, source, flow_version)
          * customer_email pre-fill when available
          * idempotency key forwarded to the SDK
          * application_fee_amount only when fee > 0 (v1 always 0)
          * payment_method_types resolved per merchant capability
        """
        if not request.line_items:
            raise ProviderError(
                "Cannot create checkout with zero line items",
                provider="stripe",
            )

        # Resolve payment_method_types via merchant capabilities. We
        # only fetch capabilities when the order is in CHF — for EUR
        # we know the answer is "card" and skip the round-trip.
        method_types: tuple[str, ...]
        if request.currency.upper() == "CHF":
            try:
                # The connected account id is required for capability
                # lookup; the registry layer resolved it before
                # building the request, but we let the lookup itself
                # fail loudly if it's missing.
                connected_account_id = request.metadata.get("connected_account_id")
                if connected_account_id:
                    caps = await fetch_account_capabilities(
                        connected_account_id,
                        stripe_module=_get_stripe(),
                    )
                else:
                    caps = AccountCapabilities()
            except Exception as exc:
                # Capability lookup failure is non-fatal — degrade to
                # card-only and surface the issue in logs.
                logger.warning(
                    "stripe.provider: capabilities lookup failed for "
                    "account=%s currency=%s err=%s — falling back to card-only",
                    request.metadata.get("connected_account_id"),
                    request.currency, exc,
                )
                caps = AccountCapabilities(card_active=True)
            method_types = resolve_payment_method_types(request.currency, caps)
        else:
            method_types = resolve_payment_method_types(
                request.currency, AccountCapabilities(card_active=True),
            )

        # Build Stripe-shaped line_items. Stripe wants minor units
        # (cents/centimes) as int.
        stripe_line_items = [
            {
                "price_data": {
                    "currency": request.currency.lower(),
                    "unit_amount": int(round(float(item.unit_amount) * 100)),
                    "product_data": {"name": item.name},
                },
                "quantity": int(item.quantity),
            }
            for item in request.line_items
        ]

        connected_account_id = request.metadata.get("connected_account_id")
        if not connected_account_id:
            raise AccountNotConfigured(
                "No connected Stripe account on this organization",
                provider="stripe",
            )

        # Strip the synthetic ``connected_account_id`` from metadata
        # before passing to Stripe — it's an internal carrier, not a
        # field merchants/customers should see in the dashboard.
        metadata_for_stripe = {
            k: str(v) for k, v in request.metadata.items()
            if k != "connected_account_id"
        }

        session_kwargs: dict = {
            "mode": "payment",
            "line_items": stripe_line_items,
            "metadata": metadata_for_stripe,
            "success_url": request.success_url,
            "cancel_url": request.cancel_url,
            "stripe_account": connected_account_id,
            "payment_method_types": list(method_types),
        }
        if request.customer_email:
            session_kwargs["customer_email"] = request.customer_email

        stripe = _get_stripe()

        # R1 — sconto coupon: Stripe non ammette line item negativi, quindi si
        # crea un coupon one-off (amount_off) sul connected account e lo si
        # applica alla session → addebito = Σ(line_items) − sconto = order.total.
        discount_minor = int(round(float(request.discount_amount) * 100))
        if discount_minor > 0:
            try:
                coupon_kwargs = dict(
                    amount_off=discount_minor,
                    currency=request.currency.lower(),
                    duration="once",
                    name="Sconto",
                    stripe_account=connected_account_id,
                )
                if request.idempotency_key:
                    coupon_kwargs["idempotency_key"] = f"{request.idempotency_key}:coupon"
                coupon = await asyncio.to_thread(stripe.Coupon.create, **coupon_kwargs)
                session_kwargs["discounts"] = [{"coupon": coupon["id"]}]
            except Exception as exc:
                logger.error(
                    "stripe.provider: Coupon.create failed for order=%s err=%s",
                    request.order_id, exc,
                )
                raise ProviderError(
                    f"Stripe Coupon.create failed: {exc}",
                    code=getattr(exc, "code", None),
                )

        # Application fee (Stripe Connect) sul NET (lordo − sconto). v1 = 0.
        if request.application_fee_percent and request.application_fee_percent > 0:
            gross_minor = sum(
                int(round(float(item.unit_amount) * 100)) * int(item.quantity)
                for item in request.line_items
            )
            net_minor = max(0, gross_minor - discount_minor)
            fee_minor = int(round(
                net_minor * float(request.application_fee_percent) / 100
            ))
            if fee_minor > 0:
                session_kwargs["application_fee_amount"] = fee_minor

        try:
            create_kwargs = {}
            if request.idempotency_key:
                create_kwargs["idempotency_key"] = request.idempotency_key
            session = await asyncio.to_thread(
                stripe.checkout.Session.create,
                **session_kwargs,
                **create_kwargs,
            )
        except Exception as exc:
            logger.error(
                "stripe.provider: Session.create failed for order=%s err=%s",
                request.order_id, exc,
            )
            raise ProviderError(
                f"Stripe Session.create failed: {exc}",
                code=getattr(exc, "code", None),
                provider="stripe",
            ) from exc

        return CheckoutSessionResult(
            url=getattr(session, "url", None) or session["url"],
            session_id=getattr(session, "id", None) or session["id"],
            provider="stripe",
            connected_account=connected_account_id,
            payment_method_types=method_types,
        )

    # ── Capabilities ──────────────────────────────────────────────────────

    async def get_account_capabilities(
        self,
        connected_account_id: str,
    ) -> AccountCapabilities:
        return await fetch_account_capabilities(
            connected_account_id,
            stripe_module=_get_stripe(),
        )

    # ── Webhook ───────────────────────────────────────────────────────────

    def verify_webhook(
        self,
        payload: bytes,
        signature_header: str,
        secret: str,
    ) -> dict:
        return verify_stripe_webhook(
            payload, signature_header, secret,
            stripe_module=_get_stripe(),
        )

    def parse_event(
        self,
        verified_event: dict,
        connected_account: Optional[str] = None,
    ) -> NormalizedEvent:
        return parse_stripe_event(
            verified_event,
            connected_account=connected_account,
        )
