"""Channel registry — singleton, thread-safe.

Mirrors the PaymentProviderRegistry pattern. Channels self-register
on import via the package's __init__ side-effect. Lookup is by channel
name string (the ``name`` class attribute on each channel).
"""

from __future__ import annotations

import threading
from typing import Optional

from .base import OutreachChannel


class _Registry:
    """Singleton container. Internal — callers go via the class methods
    on :class:`OutreachChannelRegistry`."""

    def __init__(self):
        self._lock = threading.RLock()
        self._channels: dict[str, OutreachChannel] = {}

    def register(self, channel: OutreachChannel) -> None:
        with self._lock:
            self._channels[channel.name] = channel

    def get(self, name: str) -> Optional[OutreachChannel]:
        with self._lock:
            return self._channels.get(name)

    def list_names(self) -> list[str]:
        with self._lock:
            return sorted(self._channels.keys())

    def reset_for_tests(self) -> None:
        with self._lock:
            self._channels.clear()


_singleton = _Registry()


class OutreachChannelRegistry:
    """Public façade. Use class methods, never instantiate."""

    @staticmethod
    def register(channel: OutreachChannel) -> None:
        """Register or replace a channel by name."""
        _singleton.register(channel)

    @staticmethod
    def get_by_name(name: str) -> Optional[OutreachChannel]:
        """Lookup by name string. Returns None when not registered."""
        return _singleton.get(name)

    @staticmethod
    def list_names() -> list[str]:
        """Names of all registered channels. Sorted, stable."""
        return _singleton.list_names()

    @staticmethod
    def _reset_for_tests() -> None:
        """Test-only — clear the registry. Production code never calls this."""
        _singleton.reset_for_tests()
