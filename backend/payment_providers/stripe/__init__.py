"""
Stripe sub-package.

Importing this module auto-registers :class:`StripeProvider` with the
:class:`PaymentProviderRegistry`, so callers only need to do
``from payment_providers import PaymentProviderRegistry`` and the
registry already knows about ``"stripe"``.

Pattern is intentionally side-effecting on import — it's the same
plug-in style FastAPI itself uses for routers and that we'll mirror
when ``payment_providers/datatrans/`` lands in v1.5.
"""

from payment_providers.registry import PaymentProviderRegistry

from .provider import StripeProvider

# Register a single shared instance — providers are stateless.
PaymentProviderRegistry.register("stripe", StripeProvider())

__all__ = ["StripeProvider"]
