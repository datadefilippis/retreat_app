"""
Circuit breaker for LLM providers.

The retry/backoff in Wave 3.1 handles transient single-request errors.
A circuit breaker handles the case where the provider is STRUCTURALLY
down (sustained outage): instead of letting every request burn through
its 3-retry budget before failing (4-7s wasted per request × 25
concurrent requests = the loop saturates), the breaker opens after
N consecutive failures and fails-fast for a cool-down period.

States (classic three-state breaker):
  CLOSED       Normal operation. Failures counted; threshold crossed
               -> OPEN.
  OPEN         All requests fail-fast with LLMUnavailableError. After
               the cool-down -> HALF_OPEN.
  HALF_OPEN    Allow exactly one probe request. Success -> CLOSED
               (failures reset). Failure -> OPEN (new cool-down).

Thread/coroutine safety:
  All state mutations are protected by an asyncio.Lock. The breaker
  is intended to be a singleton per (provider_name) — created via
  get_breaker() in the LLM factory and reused across requests.

Why we WRAP retry, not replace it:
  Retry deals with one-off blips (a single 429). The breaker deals
  with sustained outages (Anthropic in a degraded zone). They compose:
  request -> breaker.check -> retry-loop -> provider -> response
  If a request fails 3x retry, the breaker counts ONE failure; after
  5 such failures in the time window, the breaker opens.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Callable, Optional, TypeVar, Awaitable

from services.llm.provider import LLMUnavailableError

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ── Tuning knobs (env-overridable for ops control) ─────────────────────────

# How many failures in the window before the breaker opens.
_FAILURE_THRESHOLD = int(os.environ.get("LLM_CB_FAILURE_THRESHOLD", "5"))

# How many seconds the rolling failure window covers. Older failures
# don't count.
_FAILURE_WINDOW_SECONDS = float(os.environ.get("LLM_CB_FAILURE_WINDOW", "60"))

# How long the breaker stays OPEN before allowing a HALF_OPEN probe.
_OPEN_DURATION_SECONDS = float(os.environ.get("LLM_CB_OPEN_DURATION", "30"))


class CircuitOpenError(LLMUnavailableError):
    """Raised when the breaker is open (provider considered down).

    Inherits from LLMUnavailableError so existing callers that catch
    LLMUnavailableError (or its alias ClaudeUnavailableError) treat
    the circuit-open path identically to "provider unreachable" —
    they don't need to know the breaker exists.
    """
    pass


class CircuitBreaker:
    """Async-safe circuit breaker for one provider name."""

    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = _FAILURE_THRESHOLD,
        window_seconds: float = _FAILURE_WINDOW_SECONDS,
        open_duration_seconds: float = _OPEN_DURATION_SECONDS,
    ):
        self.name = name
        self._failure_threshold = failure_threshold
        self._window_seconds = window_seconds
        self._open_duration = open_duration_seconds

        self._state = self.STATE_CLOSED
        self._failure_times: list[float] = []  # monotonic timestamps
        self._opened_at: Optional[float] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        """Current state name. For diagnostics/admin endpoint."""
        return self._state

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Execute `fn` through the breaker.

        - CLOSED: pass through; failures counted.
        - OPEN: fail-fast with CircuitOpenError.
        - HALF_OPEN: allow one probe; outcome decides close-or-reopen.
        """
        await self._maybe_reset_to_half_open()

        async with self._lock:
            if self._state == self.STATE_OPEN:
                # Fail-fast, no provider call
                raise CircuitOpenError(
                    f"LLM provider '{self.name}' is currently degraded. "
                    f"Please retry in a few seconds."
                )
            # CLOSED or HALF_OPEN — proceed.
            current_state = self._state

        try:
            result = await fn()
        except Exception as exc:
            await self._record_failure(exc, was_half_open=(current_state == self.STATE_HALF_OPEN))
            raise
        else:
            await self._record_success(was_half_open=(current_state == self.STATE_HALF_OPEN))
            return result

    async def _maybe_reset_to_half_open(self) -> None:
        """Promote OPEN -> HALF_OPEN once the cool-down has elapsed."""
        async with self._lock:
            if self._state != self.STATE_OPEN or self._opened_at is None:
                return
            if time.monotonic() - self._opened_at >= self._open_duration:
                logger.info(
                    "circuit_breaker[%s]: OPEN -> HALF_OPEN (probing)", self.name,
                )
                self._state = self.STATE_HALF_OPEN

    async def _record_failure(self, exc: Exception, *, was_half_open: bool) -> None:
        async with self._lock:
            if was_half_open:
                # The probe failed -> back to OPEN with fresh cool-down
                logger.warning(
                    "circuit_breaker[%s]: HALF_OPEN probe failed (%s) -> OPEN",
                    self.name, type(exc).__name__,
                )
                self._opened_at = time.monotonic()
                self._state = self.STATE_OPEN
                return

            # CLOSED state: record failure timestamp + prune the window
            now = time.monotonic()
            self._failure_times.append(now)
            cutoff = now - self._window_seconds
            self._failure_times = [t for t in self._failure_times if t >= cutoff]

            if len(self._failure_times) >= self._failure_threshold:
                logger.error(
                    "circuit_breaker[%s]: threshold reached (%d failures in %.0fs) -> OPEN",
                    self.name, len(self._failure_times), self._window_seconds,
                )
                self._state = self.STATE_OPEN
                self._opened_at = now

    async def _record_success(self, *, was_half_open: bool) -> None:
        async with self._lock:
            if was_half_open:
                logger.info(
                    "circuit_breaker[%s]: HALF_OPEN probe succeeded -> CLOSED",
                    self.name,
                )
                self._state = self.STATE_CLOSED
                self._failure_times.clear()
                self._opened_at = None
            # In CLOSED state, a single success doesn't reset the failure
            # window — we let the timestamps age out naturally.


# ── Per-provider instance registry ──────────────────────────────────────────

_BREAKERS: dict[str, CircuitBreaker] = {}


def get_breaker(provider_name: str) -> CircuitBreaker:
    """Return the singleton breaker for a provider. Lazy init."""
    if provider_name not in _BREAKERS:
        _BREAKERS[provider_name] = CircuitBreaker(provider_name)
    return _BREAKERS[provider_name]


def reset_for_tests() -> None:
    """Clear all breakers. ONLY for tests."""
    _BREAKERS.clear()
