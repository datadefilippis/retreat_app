"""
Provider-agnostic payment integration layer.

Public surface (everything the application layer needs):

    from payment_providers import (
        PaymentProvider,            # base ABC for new integrations
        PaymentProviderRegistry,    # registry singleton
        # Models
        CheckoutSessionRequest,
        CheckoutSessionResult,
        CheckoutLineItem,
        AccountCapabilities,
        NormalizedEvent,
        # Exceptions
        ProviderError,
        AccountNotConfigured,
        CapabilityMissing,
        WebhookSignatureInvalid,
        CurrencyMismatch,
    )

Concrete provider sub-packages (``payment_providers/stripe/``,
``payment_providers/datatrans/`` in v1.5+) self-register on import.
The first time anything touches the registry the providers are
loaded, so callers don't need to remember explicit imports.

Until v2.2 lands ``stripe/`` is a placeholder; the registry returns a
``_NullPaymentProvider`` that raises a helpful
:class:`AccountNotConfigured` so existing code paths (which still go
through ``services/payment_checkout_service``) keep working unchanged.
"""

from .base import PaymentProvider
from .registry import PaymentProviderRegistry
from .models import (
    AccountCapabilities,
    CheckoutLineItem,
    CheckoutSessionRequest,
    CheckoutSessionResult,
    NormalizedEvent,
)
from .exceptions import (
    AccountNotConfigured,
    CapabilityMissing,
    CurrencyMismatch,
    ProviderError,
    WebhookSignatureInvalid,
)

__all__ = [
    # Base + registry
    "PaymentProvider",
    "PaymentProviderRegistry",
    # Models
    "AccountCapabilities",
    "CheckoutLineItem",
    "CheckoutSessionRequest",
    "CheckoutSessionResult",
    "NormalizedEvent",
    # Exceptions
    "AccountNotConfigured",
    "CapabilityMissing",
    "CurrencyMismatch",
    "ProviderError",
    "WebhookSignatureInvalid",
]


# Auto-register concrete providers. Each sub-package's __init__ side-
# effects the registry at import time, so by the time any caller
# uses ``PaymentProviderRegistry.get_for_org(...)`` the providers
# are already loaded. We swallow ImportError to keep tests that
# don't need a payment provider (most of the suite) lightweight.
try:
    from . import stripe as _stripe_module  # noqa: F401
except Exception as _exc:  # pragma: no cover — defensive
    import logging
    logging.getLogger(__name__).warning(
        "payment_providers: stripe sub-package not loaded: %s", _exc,
    )
