"""
Read a Stripe connected account's capabilities and translate them to
the provider-agnostic :class:`AccountCapabilities` shape.

The dashboard "Activate TWINT on Stripe" banner and the checkout
session builder both consume the result of this helper, so we keep
the field-name mapping in exactly one place.

Stripe returns capabilities as a dict like::

    {
      "card_payments":     "active",
      "transfers":         "active",
      "twint_payments":    "active",   # the one we care about for CH
      "sepa_debit_payments": "inactive",
      ...
    }

Status values: ``"active"``, ``"inactive"``, ``"pending"``.
We treat anything other than ``"active"`` as not-enabled.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Mapping, Optional

from payment_providers.exceptions import AccountNotConfigured, ProviderError
from payment_providers.models import AccountCapabilities

logger = logging.getLogger(__name__)


# Dev/test escape hatch ─ NEVER set this in production.
#
# When ``AFIANCO_DEV_FAKE_CAPABILITIES`` is non-empty, the capability
# lookup short-circuits the Stripe API round-trip and returns a fake
# :class:`AccountCapabilities`. The value is a comma-separated list of
# capability names to mark as ``active``:
#
#   AFIANCO_DEV_FAKE_CAPABILITIES=card,twint           ← CHF + TWINT on
#   AFIANCO_DEV_FAKE_CAPABILITIES=card                 ← card only
#   AFIANCO_DEV_FAKE_CAPABILITIES=card,twint,sepa_debit ← all three
#
# Lets a developer (or the founder, before the first real CH merchant
# onboards) verify the Settings UI rendering — the "TWINT inactive →
# CTA banner" path, the active-method rows, the colors — without
# spinning up a Stripe Connect Express account or completing KYC.
_DEV_FAKE_ENV = "AFIANCO_DEV_FAKE_CAPABILITIES"


def _is_active(capabilities_dict: Mapping, key: str) -> bool:
    """Return True when Stripe reports the capability as ``active``."""
    return str(capabilities_dict.get(key) or "").lower() == "active"


def _stripe_caps_to_model(capabilities_dict: Optional[Mapping]) -> AccountCapabilities:
    """Translate Stripe's flat dict into the provider-agnostic struct.

    Unknown / future capabilities are preserved on ``other`` so a UI
    debug page can show them without code changes.
    """
    if not isinstance(capabilities_dict, Mapping):
        return AccountCapabilities()

    known = {"card_payments", "twint_payments", "sepa_debit_payments"}
    other = {
        k: str(v) for k, v in capabilities_dict.items() if k not in known
    }

    return AccountCapabilities(
        card_active=_is_active(capabilities_dict, "card_payments"),
        twint_active=_is_active(capabilities_dict, "twint_payments"),
        sepa_debit_active=_is_active(capabilities_dict, "sepa_debit_payments"),
        other=other,
    )


async def fetch_account_capabilities(
    account_id: str,
    *,
    stripe_module,
) -> AccountCapabilities:
    """Call ``stripe.Account.retrieve`` and translate the result.

    ``stripe_module`` is injected so:
      * the function is testable with a mock SDK,
      * the only ``import stripe`` lives in :mod:`provider` (and the
        linter rule that ships with Step 2.3 enforces this).

    Raises:
      :class:`AccountNotConfigured` — when ``account_id`` is blank.
      :class:`ProviderError` — when Stripe returns any error
        (connectivity, auth, deleted account); the original message is
        preserved on ``ProviderError.code``.
    """
    if not account_id:
        raise AccountNotConfigured(
            "Stripe account id is required",
            provider="stripe",
        )

    # Dev/test escape hatch — see _DEV_FAKE_ENV docstring above.
    fake_spec = os.environ.get(_DEV_FAKE_ENV, "").strip()
    if fake_spec:
        active_set = {p.strip().lower() for p in fake_spec.split(",") if p.strip()}
        logger.warning(
            "stripe.capabilities: %s active — bypassing Stripe API "
            "and returning fake capabilities=%s for account=%s",
            _DEV_FAKE_ENV, sorted(active_set), account_id,
        )
        return AccountCapabilities(
            card_active="card" in active_set,
            twint_active="twint" in active_set,
            sepa_debit_active="sepa_debit" in active_set,
            other={},
        )

    try:
        # ``stripe.Account.retrieve`` is sync; wrap so the caller can
        # await without blocking the event loop on network IO.
        account = await asyncio.to_thread(
            stripe_module.Account.retrieve, account_id,
        )
    except Exception as exc:
        logger.warning(
            "stripe.capabilities: retrieve failed account=%s err=%s",
            account_id, exc,
        )
        raise ProviderError(
            f"Stripe account capabilities lookup failed: {exc}",
            code=getattr(exc, "code", None),
            provider="stripe",
        ) from exc

    # Stripe SDK returns either a StripeObject or (in v15+) a dict-like
    # — either way, ``capabilities`` indexes into a Mapping.
    caps = None
    if isinstance(account, Mapping):
        caps = account.get("capabilities")
    else:
        caps = getattr(account, "capabilities", None)
        if hasattr(caps, "to_dict"):
            try:
                caps = caps.to_dict()
            except Exception:
                caps = None

    return _stripe_caps_to_model(caps)
