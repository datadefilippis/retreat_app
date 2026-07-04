"""
Per-request context propagation for AFianco backend.

Adds two ContextVar slots that complement the existing correlation_id from
services/correlation_context.py: user_id and org_id. These are populated by
auth.get_current_user when a request is authenticated, and read by the JSON
log formatter so every log line emitted under an authenticated request
automatically carries who/what scope it belongs to.

Why ContextVars (not threading.local):
    asyncio tasks inherit the active context at spawn time, so fire-and-forget
    background tasks launched from a handler still carry the user/org scope.

Why a SEPARATE module from correlation_context.py:
    correlation_context.py was scoped to webhook correlation IDs and is
    already production-stable. Mixing concerns there risks regression in
    Stripe webhook tracking. This module is purely additive — it imports
    correlation_id helpers via re-export so observability.request_context
    becomes the single import surface for log enrichment fields.

All getters return None when not set (rather than the "-" sentinel used by
correlation_id) so JSON formatters can omit the field cleanly.
"""
from contextvars import ContextVar
from typing import Optional

# Re-export correlation_id helpers so callers have one import surface.
from services.correlation_context import (
    new_correlation_id,
    set_correlation_id,
    get_correlation_id,
    clear_correlation_id,
)


_user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_org_id: ContextVar[Optional[str]] = ContextVar("org_id", default=None)


# ── User ID ───────────────────────────────────────────────────────────────────

def set_user_id(user_id: Optional[str]) -> None:
    """Set the authenticated user id for the current context."""
    _user_id.set(user_id)


def get_user_id() -> Optional[str]:
    """Return the authenticated user id, or None if request is anonymous."""
    return _user_id.get()


def clear_user_id() -> None:
    """Reset user_id (typically on response cleanup)."""
    _user_id.set(None)


# ── Org ID ────────────────────────────────────────────────────────────────────

def set_org_id(org_id: Optional[str]) -> None:
    """Set the organization id for the current context."""
    _org_id.set(org_id)


def get_org_id() -> Optional[str]:
    """Return the org id, or None if no auth scope."""
    return _org_id.get()


def clear_org_id() -> None:
    """Reset org_id."""
    _org_id.set(None)


# ── Aliases for clearer intent at call sites ──────────────────────────────────

# get_request_id is a synonym of get_correlation_id; the HTTP middleware sets
# correlation_id from the X-Request-ID header (or generates a fresh one), so
# downstream code can refer to it by either name without confusion.
get_request_id = get_correlation_id


__all__ = [
    # Re-exports from correlation_context
    "new_correlation_id",
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    # New: user_id / org_id
    "set_user_id",
    "get_user_id",
    "clear_user_id",
    "set_org_id",
    "get_org_id",
    "clear_org_id",
    # Alias
    "get_request_id",
]
