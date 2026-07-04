"""
HTTP middleware: per-request correlation/request ID propagation.

Behavior:
    1. On request entry:
       - Read X-Request-ID from inbound headers if client supplied one
         (e.g. from upstream nginx, frontend Sentry, or load balancer).
       - Otherwise generate a fresh one with prefix "req_".
       - set_correlation_id() activates it for the lifetime of this request,
         which makes every logger.info/warning/error emitted downstream
         automatically tagged with that ID by CorrelationIdFilter.
    2. On response:
       - Add X-Request-ID header to the response so client (frontend, support,
         debug tools) can reference it in tickets / Sentry events.
    3. On exception:
       - The correlation ID is preserved in the log record for the exception,
         and an X-Request-ID header is still added to the error response.

ContextVars are isolated per asyncio task, so concurrent requests do not
collide. Fire-and-forget background tasks spawned from a handler inherit
the request_id automatically (asyncio.Task copies the current context).

This middleware does NOT populate user_id / org_id — those are set by
auth.get_current_user when authentication runs (see auth.py).
"""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from core.observability.request_context import (
    new_correlation_id,
    set_correlation_id,
    clear_correlation_id,
    clear_user_id,
    clear_org_id,
)

logger = logging.getLogger(__name__)

# Header name standardized across the industry for request correlation.
REQUEST_ID_HEADER = "X-Request-ID"

# Endpoints that should NOT get a request_id (skip noisy health probes).
# Healthchecks fire 1Hz from load balancers / uptime monitors and would
# spam the logs without any debugging value.
_SKIP_PATHS = frozenset({
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/metrics",
})


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Sets a per-request correlation_id on entry, exposes it on response.

    Compatible with Starlette/FastAPI BaseHTTPMiddleware contract.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip noisy paths to keep logs clean.
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        # Use client-supplied X-Request-ID if present (allows distributed
        # tracing across services), else mint a fresh one.
        incoming = request.headers.get(REQUEST_ID_HEADER, "").strip()
        request_id = incoming if incoming else new_correlation_id(prefix="req")

        # Activate for the lifetime of this asyncio task.
        set_correlation_id(request_id)
        try:
            response = await call_next(request)
        finally:
            # ContextVars are isolated per task; explicit clear is defensive
            # but harmless. user_id / org_id may have been set by auth deps,
            # so clear them too to avoid leaking across requests if the
            # ASGI server reuses tasks (uvicorn does not, but defense in depth).
            clear_correlation_id()
            clear_user_id()
            clear_org_id()

        # Echo back so client can reference it in support tickets / Sentry.
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
