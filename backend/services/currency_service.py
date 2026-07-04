"""
Currency policy and lifecycle for an Organization.

This service centralises three concerns that would otherwise be scattered
across routers and validators:

  1. **Validation** — accept only ISO 4217 codes we ship today.
  2. **Resolution** — derive the effective currency for an org doc with a
     consistent fallback (EUR), so callers never have to repeat the
     ``or "EUR"`` pattern that today litters ``routers/public.py``.
  3. **Mutation policy** — once an organisation has any order on file,
     its currency becomes immutable. UI and API layers consult
     ``is_change_allowed_for_org`` before exposing a currency selector.

Pairs with:
  * ``backend/core/checkout_minimums.py`` — per-currency Stripe minimums
  * ``backend/core/currency_format.py``    — display formatting

Public API:
    SUPPORTED_CURRENCIES               # tuple of ISO codes
    DEFAULT_CURRENCY                   # "EUR"
    validate_currency_code(code)       # raises ValueError on unknown
    get_currency_for_org(org)          # safe read with fallback
    get_currency_for_order(order, org) # order snapshot → org → EUR
    get_currency_for_product(p, org)   # product override → org → EUR
    get_currency_for_extra(e, p, org)  # extra → product → org → EUR
    is_change_allowed_for_org(org_id)  # async, queries orders_collection
"""

from __future__ import annotations

from typing import Mapping, Optional


SUPPORTED_CURRENCIES: tuple[str, ...] = ("EUR", "CHF")
DEFAULT_CURRENCY: str = "EUR"


class UnsupportedCurrencyError(ValueError):
    """Raised when a currency code is outside ``SUPPORTED_CURRENCIES``."""


def validate_currency_code(code: Optional[str]) -> str:
    """Normalise to uppercase and assert membership in supported set.

    Empty / None is rejected explicitly so accidental passthrough of an
    unset field never silently picks a default at the wrong layer.
    """
    if not code:
        raise UnsupportedCurrencyError("currency code is required")
    normalised = code.strip().upper()
    if normalised not in SUPPORTED_CURRENCIES:
        raise UnsupportedCurrencyError(
            f"unsupported currency '{code}'; supported: {SUPPORTED_CURRENCIES}"
        )
    return normalised


def get_currency_for_org(org: Mapping) -> str:
    """Return the effective currency for an organisation document.

    Tolerates legacy records where ``currency`` is missing or ``None``;
    those resolve to :data:`DEFAULT_CURRENCY`. Unknown explicit values
    also resolve to the default rather than raising — read paths must
    never crash. The validator on writes is the source of truth.
    """
    raw = org.get("currency") if isinstance(org, Mapping) else None
    if not raw:
        return DEFAULT_CURRENCY
    candidate = str(raw).strip().upper()
    if candidate not in SUPPORTED_CURRENCIES:
        return DEFAULT_CURRENCY
    return candidate


def _resolve_from_doc(doc: Optional[Mapping]) -> Optional[str]:
    """Read ``currency`` off a Mongo doc and normalise it.

    Returns the uppercase ISO code if the doc has a recognised value,
    or ``None`` if the field is missing / empty / unsupported. Used
    internally by the ``get_currency_for_*`` resolvers; callers should
    not invoke it directly.
    """
    if not isinstance(doc, Mapping):
        return None
    raw = doc.get("currency")
    if not raw:
        return None
    candidate = str(raw).strip().upper()
    if candidate not in SUPPORTED_CURRENCIES:
        return None
    return candidate


def get_currency_for_order(
    order_doc: Optional[Mapping],
    org_doc: Optional[Mapping] = None,
) -> str:
    """Resolve the currency for an order.

    Priority:
      1. ``order.currency`` snapshot (the canonical answer once an
         order is created — see ``services/order_service.create_order``)
      2. ``org.currency`` (only consulted when the order doc is missing
         a currency, which only happens for legacy / partially-migrated
         records)
      3. :data:`DEFAULT_CURRENCY` (``"EUR"``) as the last-resort fallback

    Both arguments are tolerated as ``None`` so callers can pass
    whatever the DB returned without pre-checking.
    """
    snapshot = _resolve_from_doc(order_doc)
    if snapshot is not None:
        return snapshot
    if org_doc is not None:
        return get_currency_for_org(org_doc)
    return DEFAULT_CURRENCY


def get_currency_for_product(
    product_doc: Optional[Mapping],
    org_doc: Optional[Mapping] = None,
) -> str:
    """Resolve the currency for a product (catalog read path).

    Priority:
      1. ``product.currency`` if explicitly set on the product
      2. ``org.currency`` (the usual case — products inherit from the org)
      3. :data:`DEFAULT_CURRENCY` (``"EUR"``)
    """
    snapshot = _resolve_from_doc(product_doc)
    if snapshot is not None:
        return snapshot
    if org_doc is not None:
        return get_currency_for_org(org_doc)
    return DEFAULT_CURRENCY


def get_currency_for_extra(
    extra_doc: Optional[Mapping],
    product_doc: Optional[Mapping] = None,
    org_doc: Optional[Mapping] = None,
) -> str:
    """Resolve the currency for an order extra / line modifier.

    Priority:
      1. ``extra.currency`` if explicitly set
      2. ``product.currency`` (when the extra is a per-product add-on)
      3. ``org.currency``
      4. :data:`DEFAULT_CURRENCY`

    Useful for ``ProductExtra``, ``ShippingOption``, ``EventTicketTier``
    and any other line-level modifier whose currency conceptually
    inherits from a parent product or the org.
    """
    snapshot = _resolve_from_doc(extra_doc)
    if snapshot is not None:
        return snapshot
    return get_currency_for_product(product_doc, org_doc)


async def is_change_allowed_for_org(org_id: str) -> bool:
    """True when no order has ever been written for ``org_id``.

    The currency of an organisation is immutable once any order exists,
    because every order carries a snapshot of the currency at creation
    and changing the org-level value retroactively would create
    inconsistent reporting and PDF history.

    Imported lazily so unit tests that don't touch the DB are not
    forced to set up Motor.
    """
    from database import orders_collection  # local import: keep DB optional for unit tests

    existing = await orders_collection.find_one(
        {"organization_id": org_id},
        {"_id": 1},
    )
    return existing is None
