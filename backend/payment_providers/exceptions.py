"""
Exceptions raised by payment provider implementations.

The hierarchy is intentionally shallow — every concrete provider
(Stripe in v1, Datatrans/PostFinance in v1.5+) raises one of these
errors so the application layer can react uniformly without having to
catch ``stripe.error.*`` or ``datatrans.error.*`` directly.

Only ``payment_providers/*`` should raise these. Routers and services
import from this module by name.
"""

from __future__ import annotations


class ProviderError(Exception):
    """Generic failure inside a payment provider integration.

    Use this when the third-party SDK raised an error that we cannot
    classify more precisely. The ``code`` attribute carries the
    provider's own error code (e.g. ``"card_declined"``) so logs and
    dashboards can group on it.
    """

    def __init__(self, message: str, *, code: str | None = None, provider: str | None = None):
        super().__init__(message)
        self.code = code
        self.provider = provider


class AccountNotConfigured(ProviderError):
    """The merchant has not connected (or has disconnected) the provider.

    Raised by the dispatcher before any checkout attempt so the caller
    can return a clean 409 to the frontend instead of bubbling a raw
    Stripe / Datatrans error.
    """


class CapabilityMissing(ProviderError):
    """The merchant's connected account does not have a payment method
    capability the order requires.

    Example: a CHF order asks for TWINT, but the merchant hasn't
    enabled TWINT on their Stripe dashboard. We surface this as a
    distinct error so the UI can render a "go enable TWINT on Stripe"
    deep link instead of a generic checkout failure.
    """

    def __init__(
        self,
        message: str,
        *,
        capability: str,
        provider: str | None = None,
    ):
        super().__init__(message, code="capability_missing", provider=provider)
        self.capability = capability


class WebhookSignatureInvalid(ProviderError):
    """The provider's webhook signature did not validate.

    Webhook handlers MUST raise this (and refuse to act on the event)
    rather than logging-and-continuing — an unverified event could be
    a malicious replay. The router maps this to HTTP 400.
    """


class CurrencyMismatch(ProviderError):
    """The provider charged a currency different from the order's.

    Already enforced in ``payment_checkout_service.reconcile_checkout_event``
    for Stripe; this exception class lets future providers signal the
    same condition uniformly.
    """

    def __init__(
        self,
        *,
        expected: str,
        got: str,
        provider: str | None = None,
    ):
        super().__init__(
            f"Currency mismatch: expected={expected} got={got}",
            code="currency_mismatch",
            provider=provider,
        )
        self.expected = expected
        self.got = got
