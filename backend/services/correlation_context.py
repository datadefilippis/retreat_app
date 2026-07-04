"""
Correlation IDs for async request flows.

Motivation:
  During incident investigation the first question is always "show me
  every log line for this webhook". Today that requires guessing by
  event_id and hoping it appears in every downstream log message — which
  it mostly doesn't. A correlation ID propagated through contextvars
  solves this: set once at the request boundary, auto-injected into
  every log record emitted underneath.

Scope for Fase 8b:
  - Webhook entry point (routers/billing.stripe_webhook).
  - Downstream handlers via contextvars (asyncio-safe).
  - Logging formatter extended to emit the correlation_id tag when set.

Design notes:
  - contextvars.ContextVar is the right primitive: asyncio tasks inherit
    the context at spawn time, so fire-and-forget tasks still carry the
    id if they were launched after set_correlation_id().
  - The filter is defensive: missing correlation_id is rendered as "-"
    so grep for "[cid=...]" never matches noise.
  - new_correlation_id() prefixes a fixed tag so it is easy to spot in
    mixed log streams (e.g. from WSGI/health probes).
"""

import logging
import uuid
from contextvars import ContextVar
from typing import Optional


# Use a sentinel default so the filter can tell "never set" from "empty".
_MISSING = "-"
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default=_MISSING)


def new_correlation_id(prefix: str = "cid") -> str:
    """Generate a fresh correlation id (short uuid4 hex with a prefix)."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation id for the current context (async-safe)."""
    _correlation_id.set(correlation_id or _MISSING)


def get_correlation_id() -> Optional[str]:
    """Return the current correlation id, or None if not set."""
    cid = _correlation_id.get()
    return None if cid == _MISSING else cid


def clear_correlation_id() -> None:
    """Clear the correlation id for the current context."""
    _correlation_id.set(_MISSING)


class CorrelationIdFilter(logging.Filter):
    """Logging filter that attaches correlation_id to each LogRecord.

    Records the current contextvar value into record.correlation_id
    so formatters / JSON handlers can include it. Adds nothing when
    unset (rendered as '-' by default, keeping log lines grep-friendly).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get()
        return True


def install_correlation_id_logging() -> None:
    """Attach the filter to the root logger and extend the default format.

    Safe to call multiple times — re-installs are no-op.
    """
    root = logging.getLogger()
    # Avoid double-install if called twice
    already = any(
        isinstance(f, CorrelationIdFilter)
        for h in root.handlers
        for f in h.filters
    )
    if already:
        return
    flt = CorrelationIdFilter()
    for h in root.handlers:
        h.addFilter(flt)
        # If the handler uses the default formatter, rebuild it with the cid tag.
        fmt = h.formatter
        if fmt is not None:
            base = fmt._fmt or "%(levelname)s %(name)s: %(message)s"
            # Avoid duplicate injection if a prior run already added the tag
            if "%(correlation_id)s" not in base:
                new_fmt = base.replace(
                    "%(levelname)s",
                    "%(levelname)s [cid=%(correlation_id)s]",
                    1,
                )
                h.setFormatter(logging.Formatter(new_fmt, datefmt=fmt.datefmt))
