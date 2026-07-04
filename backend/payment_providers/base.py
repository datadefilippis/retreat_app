"""
Abstract base for every payment provider implementation.

Adding a new provider — Datatrans, PostFinance Checkout, TWINT direct,
Adyen — is a matter of:

  1. Creating a sub-package under ``payment_providers/`` (e.g.
     ``payment_providers/datatrans/``).
  2. Implementing :class:`PaymentProvider` for it.
  3. Registering the class with :class:`PaymentProviderRegistry`.

The application layer (CheckoutService, webhook dispatcher) NEVER
imports concrete providers — it only sees this interface and the
registry. That's the whole point: keep Stripe SDK leaks contained to
``payment_providers/stripe/`` so a future migration is a localized
change instead of a 30-day refactor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .models import (
    AccountCapabilities,
    CheckoutSessionRequest,
    CheckoutSessionResult,
    NormalizedEvent,
)


class PaymentProvider(ABC):
    """Contract every payment integration must implement.

    Subclasses are expected to be **stateless** — instances are
    cached by :class:`PaymentProviderRegistry` and reused across
    requests. Any per-request state (idempotency keys, retry
    counters) goes through the request models, not instance fields.

    Subclasses must also expose a ``name`` class attribute matching
    the provider's registry key (``"stripe"``, ``"datatrans"``).
    """

    #: Stable identifier used in DB documents (``payment_checkout.provider``)
    #: and in :class:`PaymentProviderRegistry`. Subclasses override.
    name: str = "abstract"

    # ── Checkout ───────────────────────────────────────────────────────────

    @abstractmethod
    async def create_checkout_session(
        self,
        request: CheckoutSessionRequest,
    ) -> CheckoutSessionResult:
        """Create a hosted-checkout session and return the URL the
        customer should be redirected to.

        Implementations must:
          * Pass ``request.idempotency_key`` to the SDK so retries
            don't double-create sessions.
          * Stamp ``request.metadata`` on the provider-side session so
            the webhook can echo it back.
          * Translate provider errors into :class:`ProviderError`
            subclasses; never let raw SDK exceptions leak.
        """

    # ── Capabilities (preflight) ───────────────────────────────────────────

    @abstractmethod
    async def get_account_capabilities(
        self,
        connected_account_id: str,
    ) -> AccountCapabilities:
        """Return which payment methods the merchant has enabled.

        Used by the dashboard to show "Activate TWINT on Stripe"
        prompts and by ``create_checkout_session`` to decide whether
        to include TWINT in ``payment_method_types``.

        Should be cheap to call (cache at the application layer with
        a short TTL — Stripe's account capabilities don't change
        every minute).
        """

    # ── Webhook ────────────────────────────────────────────────────────────

    @abstractmethod
    def verify_webhook(
        self,
        payload: bytes,
        signature_header: str,
        secret: str,
    ) -> dict:
        """Validate a webhook payload and return the parsed dict.

        MUST raise :class:`WebhookSignatureInvalid` on a bad signature.
        Routers refuse to act on the event when this raises — keeping
        signature validation as the single line of defense against
        replay attacks.
        """

    @abstractmethod
    def parse_event(
        self,
        verified_event: dict,
        connected_account: Optional[str] = None,
    ) -> NormalizedEvent:
        """Translate a provider-specific event dict into the canonical
        :class:`NormalizedEvent` shape used by the dispatcher.

        Returns ``None`` is NOT a valid response — implementations
        that don't recognise the event type should still return a
        :class:`NormalizedEvent` with ``type=""`` so the dispatcher
        can log and skip cleanly.
        """


class _NullPaymentProvider(PaymentProvider):
    """Convenience marker for "no provider configured" cases.

    Returned by :class:`PaymentProviderRegistry.get` when an org has
    no payment connection on file. Lets callers detect the case
    without nullable handling everywhere; calling any method raises a
    :class:`AccountNotConfigured` error with a helpful message.
    """

    name = "none"

    async def create_checkout_session(self, request):
        from .exceptions import AccountNotConfigured
        raise AccountNotConfigured(
            "No payment provider configured for this organization",
            provider="none",
        )

    async def get_account_capabilities(self, connected_account_id):
        from .exceptions import AccountNotConfigured
        raise AccountNotConfigured(
            "No payment provider configured for this organization",
            provider="none",
        )

    def verify_webhook(self, payload, signature_header, secret):
        from .exceptions import AccountNotConfigured
        raise AccountNotConfigured(
            "No payment provider configured",
            provider="none",
        )

    def parse_event(self, verified_event, connected_account=None):
        from .exceptions import AccountNotConfigured
        raise AccountNotConfigured(
            "No payment provider configured",
            provider="none",
        )
