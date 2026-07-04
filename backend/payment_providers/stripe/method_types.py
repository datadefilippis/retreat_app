"""
Resolve the Stripe ``payment_method_types`` list from the order's
currency and the merchant's enabled capabilities.

Pulled out of :class:`StripeProvider` so the rule is:

  * **single source of truth** — both the checkout creator and the
    UI capability banner read from here;
  * **trivially testable** — pure function, no SDK dependency.

CH compliance v1: when the order is in CHF and the merchant has
TWINT enabled on their Stripe account, we offer TWINT alongside
cards. EUR (and any other currency we ship later) stays card-only
until a Swiss-specific method is requested.
"""

from __future__ import annotations

from payment_providers.models import AccountCapabilities


# Ordered list — Stripe shows the methods in the order we pass them,
# so cards first keeps the most-used path the most prominent.
_BASE_METHODS_BY_CURRENCY: dict[str, tuple[str, ...]] = {
    "EUR": ("card",),
    "CHF": ("card",),
}

# Methods gated by both currency and merchant capability.
_CONDITIONAL_METHODS: tuple[tuple[str, str, str], ...] = (
    # (method, capability_attr, currency_required)
    ("twint", "twint_active", "CHF"),
)


def resolve_payment_method_types(
    currency: str,
    capabilities: AccountCapabilities,
) -> tuple[str, ...]:
    """Return the ``payment_method_types`` to pass to Stripe.

    Always includes ``"card"`` (Stripe's universal default). Adds
    currency-specific methods only when the merchant's connected
    account has the matching capability ``"active"``.

    Never raises. ``CapabilityMissing`` is the caller's job to surface
    when a method is required but missing — this function is purely
    declarative.
    """
    code = (currency or "").upper()
    methods: list[str] = list(_BASE_METHODS_BY_CURRENCY.get(code, ("card",)))

    for method, attr, required_currency in _CONDITIONAL_METHODS:
        if code != required_currency:
            continue
        if getattr(capabilities, attr, False):
            methods.append(method)

    return tuple(methods)


def is_swiss_method(method: str) -> bool:
    """True for Swiss-specific payment methods (TWINT today, future PostFinance card etc)."""
    return method in {"twint"}
