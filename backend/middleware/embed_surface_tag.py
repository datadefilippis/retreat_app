"""
Track E Step 1.5 — Embed surface tagging middleware.

Pre-E1.5 gli errori del flow embed (/api/public/embed/*) finivano in
Sentry SENZA distinzione vs errori admin/storefront. Inbox triage piu'
lento + alert rules O3.1 [P2] Embed-SDK error spike non triggherabili
(tag `surface=embed` mai settato → filter rule fail).

Soluzione:
  - Middleware auto-tag a livello Starlette
  - Match path prefix /api/public/embed/* → set surface=embed
  - Sentry scope per-request: tag applicato a TUTTI gli event (error
    capture, breadcrumb, transaction) di quella request
  - Zero per-endpoint changes (DRY: nuovo embed endpoint auto-tagged)

Pattern alignment con O3.2:
  - capture_with_tags helper resta per per-call site explicit tagging
    (es. action=payment_charge in stripe handler)
  - Middleware fa il BASELINE surface tag (orthogonale ad action)
  - Errori non handled → Sentry FastApiIntegration cattura comunque,
    surface tag presente grazie a questo middleware

Performance
===========

Cost trascurabile:
  - Path string prefix check (O(1))
  - Sentry set_tag (in-memory dict update)
  - Solo /api/public/embed/* paths affetti

Safe-no-op
==========

Se sentry_sdk non installato OR DSN non settato (dev env), middleware
e' no-op silenzioso. Mai blocca request anche su errore Sentry SDK.
"""

import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


# Path prefix che attiva il tag. Pinned dal sentinel per coerenza
# con router mount in server.py (app.include_router(embed_router,
# prefix="/api") + router prefix="/public/embed" → /api/public/embed/*).
EMBED_PATH_PREFIX = "/api/public/embed/"

# Canonical surface tag value. Match con sentry-alert-rules.md tag
# taxonomy (O3.1) + capture_with_tags _KNOWN_SURFACES.
EMBED_SURFACE_TAG_VALUE = "embed"


class EmbedSurfaceTagMiddleware(BaseHTTPMiddleware):
    """Auto-tag Sentry scope with surface=embed for embed router paths.

    Mounted at app level. For every request matching EMBED_PATH_PREFIX:
      1. Set `surface=embed` on current Sentry scope (per-request)
      2. Pass-through to next middleware / endpoint
      3. Any exception captured during the request automatically
         carries the tag (via FastApiIntegration default capture)

    Non-embed paths: pass-through senza side-effects.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path or ""
        if path.startswith(EMBED_PATH_PREFIX):
            try:
                import sentry_sdk
                sentry_sdk.set_tag("surface", EMBED_SURFACE_TAG_VALUE)
            except ImportError:
                # Sentry SDK not installed (dev env senza opt-in) — no-op.
                pass
            except Exception as exc:
                # Defensive: tag setting must NEVER break request flow.
                # Log + continue.
                logger.debug(
                    "embed_surface_tag: set_tag failed (continuing): %s",
                    exc,
                )

        return await call_next(request)


__all__ = [
    "EmbedSurfaceTagMiddleware",
    "EMBED_PATH_PREFIX",
    "EMBED_SURFACE_TAG_VALUE",
]
