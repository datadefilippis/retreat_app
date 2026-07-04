"""
Registry that maps a payment provider name (``"stripe"``,
``"datatrans"``, …) to the concrete :class:`PaymentProvider`
implementation.

Two consumption patterns:

  1. ``get_by_name("stripe")`` — when a webhook router knows which
     provider sent the event (from URL or signature header).
  2. ``get_for_org(org)`` — when the application layer needs the
     provider configured for a specific merchant. Reads
     ``org.payment_provider`` (defaults to ``"stripe"`` for legacy
     orgs that pre-date the field).

Implementations register themselves at import time. To add Datatrans
in v1.5: drop a ``payment_providers/datatrans/__init__.py`` that does
``PaymentProviderRegistry.register("datatrans", DatatransProvider)``,
and the registry picks it up — zero edits to existing code.
"""

from __future__ import annotations

import logging
import threading
from typing import Mapping, Optional

from .base import PaymentProvider, _NullPaymentProvider

logger = logging.getLogger(__name__)


class PaymentProviderRegistry:
    """Process-wide, thread-safe singleton.

    Class methods only — there is no instance to construct. We keep
    a tiny lock around mutations so module import order can't race
    with itself in unusual deployments (gunicorn fork+import cases).
    """

    _providers: dict[str, PaymentProvider] = {}
    _lock: threading.Lock = threading.Lock()
    _null: PaymentProvider = _NullPaymentProvider()

    # ── Registration ───────────────────────────────────────────────────────

    @classmethod
    def register(cls, name: str, provider: PaymentProvider) -> None:
        """Register a provider instance under ``name``.

        Subsequent calls to ``register("stripe", ...)`` overwrite the
        previous registration — useful in tests that want to swap in a
        mock.
        """
        if not name:
            raise ValueError("provider name must be non-empty")
        with cls._lock:
            cls._providers[name] = provider
            logger.info("payment_providers: registered '%s' (%s)",
                        name, type(provider).__name__)

    @classmethod
    def unregister(cls, name: str) -> None:
        """Drop a registration. Used by tests to restore baseline state."""
        with cls._lock:
            cls._providers.pop(name, None)

    @classmethod
    def names(cls) -> tuple[str, ...]:
        """List registered provider names (snapshot)."""
        with cls._lock:
            return tuple(cls._providers.keys())

    # ── Lookup ─────────────────────────────────────────────────────────────

    @classmethod
    def get_by_name(cls, name: str) -> PaymentProvider:
        """Look up a provider by registry key.

        Returns a :class:`_NullPaymentProvider` (which raises a
        helpful :class:`AccountNotConfigured` on every method) when
        the name isn't registered. This avoids ``None`` checks at the
        call sites.
        """
        with cls._lock:
            provider = cls._providers.get(name)
        if provider is None:
            logger.warning(
                "payment_providers: requested unknown provider '%s' "
                "(registered: %s)", name, list(cls._providers.keys())
            )
            return cls._null
        return provider

    @classmethod
    def get_for_org(cls, org: Optional[Mapping]) -> PaymentProvider:
        """Resolve the provider configured for a given organisation.

        Order of precedence:
          1. ``org["payment_provider"]`` if present and registered.
          2. ``"stripe"`` as the universal default for legacy orgs.
          3. :class:`_NullPaymentProvider` only when literally nothing
             is registered (means we've never imported any concrete
             provider — almost always a bug).
        """
        configured = None
        if isinstance(org, Mapping):
            raw = org.get("payment_provider")
            if isinstance(raw, str) and raw:
                configured = raw.strip().lower()

        if configured:
            with cls._lock:
                if configured in cls._providers:
                    return cls._providers[configured]
            logger.warning(
                "payment_providers: org configured for '%s' but not "
                "registered; falling back to stripe", configured,
            )

        # Fallback chain.
        with cls._lock:
            if "stripe" in cls._providers:
                return cls._providers["stripe"]

        logger.error("payment_providers: no provider registered at all")
        return cls._null

    # ── Test helpers ───────────────────────────────────────────────────────

    @classmethod
    def _reset_for_tests(cls) -> None:
        """Wipe the registry. ONLY for use inside tests."""
        with cls._lock:
            cls._providers.clear()
