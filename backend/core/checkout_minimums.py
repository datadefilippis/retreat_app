"""
Per-currency minimum checkout amounts.

Stripe enforces a per-currency minimum for charges; below that, the
PaymentIntent fails. We mirror Stripe's published minimums here so we
can reject undersized orders before opening a checkout session and
return a clear error to the merchant/customer.

Public API:
    get_minimum(currency: str) → Decimal
    is_below_minimum(amount: Decimal, currency: str) → bool

Adding a currency: append to ``_MINIMUMS`` and update tests. ISO 4217
codes only. Values are taken from Stripe's official minimum charge
amounts table; recheck if Stripe updates them.
"""

from decimal import Decimal
from typing import Dict


_MINIMUMS: Dict[str, Decimal] = {
    "EUR": Decimal("0.50"),
    "CHF": Decimal("0.50"),
}

DEFAULT_MINIMUM = Decimal("0.50")


def get_minimum(currency: str) -> Decimal:
    """Return the minimum charge amount for ``currency`` (uppercase ISO 4217).

    Falls back to ``DEFAULT_MINIMUM`` for unknown currencies so that
    callers never crash on a bad currency string; the validator chain at
    org/order creation is the source of truth for currency correctness.
    """
    return _MINIMUMS.get(currency.upper(), DEFAULT_MINIMUM)


def is_below_minimum(amount: Decimal, currency: str) -> bool:
    """True iff ``amount`` is strictly below the minimum for ``currency``."""
    return amount < get_minimum(currency)


def supported_currencies() -> tuple[str, ...]:
    """Return the tuple of ISO 4217 codes we ship today."""
    return tuple(_MINIMUMS.keys())
