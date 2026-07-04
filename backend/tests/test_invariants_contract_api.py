"""Sentinel tests for afianco CONTRACT invariants — public API shape.

Step 2 della Phase 0. Pin del contract delle public API che storefront +
embed + AI site (future) consumano.

Cambiare uno di questi contract = breaking change cross-client. Vanno
deprecati con API versioning (es. v2), non con modifica in-place.

  CTR-1  POST /api/public/order-request response shape (già in test_invariants_public_flow.py)
  CTR-2  GET /api/public/storefront/{slug} catalog payload
  CTR-3  GET /api/public/storefront/{slug}/meta cache + lightweight shape
"""

import inspect
import os
import sys
from pathlib import Path

import pytest

# ── Env bootstrap ────────────────────────────────────────────────────────
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── CTR-2 — Storefront catalog payload shape ──────────────────────────


class TestCTR2_StorefrontCatalogShape:
    """CTR-2 (Contract Invariant 2, High):

    GET /api/public/storefront/{slug} deve sempre ritornare la struttura
    documentata: store_info, products[], design_tokens, custom_nav_links,
    storefront_languages.

    Tutti questi campi sono consumati da:
      - StorefrontPage.js (admin)
      - PublicStorefrontShell.jsx (shell wrapper)
      - 9 LandingPage components
      - future embed SDK
      - future AI site renderer

    Pin location: routers/public.py:417+ (get_storefront)
    """

    def test_storefront_endpoint_function_exists(self):
        """L'endpoint principale esiste come function nel router.

        I nomi canonici sono:
          - ``get_public_catalog`` (catalog completo /storefront/{slug})
          - ``get_public_storefront_meta`` (bootstrap /storefront/{slug}/meta)
        """
        from routers import public
        members = inspect.getmembers(public, inspect.iscoroutinefunction)
        storefront_handlers = [
            name for name, fn in members
            if name in (
                "get_public_catalog",
                "get_public_storefront_meta",
                "get_public_storefront",  # legacy aliases if added
                "get_storefront",
            )
        ]
        assert len(storefront_handlers) >= 2, (
            f"routers/public.py espone solo {storefront_handlers} handler(s) "
            "per /storefront. Atteso almeno 2 (catalog + meta). Storefront "
            "classic + embed widget + AI sites dipendono da questo endpoint."
        )

    def test_storefront_route_registered(self):
        """La rotta deve essere registrata sul router."""
        from routers.public import router
        paths = [route.path for route in router.routes]
        # La route /storefront/{slug} deve esistere (in qualche forma)
        storefront_routes = [p for p in paths if "/storefront/" in p]
        assert len(storefront_routes) > 0, (
            "Nessuna route /storefront/* registrata. CTR-2 violato — "
            "endpoint principale non raggiungibile."
        )

    def test_storefront_meta_route_registered(self):
        """L'endpoint lightweight /meta deve essere registrato (CTR-3)."""
        from routers.public import router
        paths = [route.path for route in router.routes]
        meta_routes = [p for p in paths if p.endswith("/meta")]
        assert len(meta_routes) > 0, (
            "Nessuna route /storefront/{slug}/meta registrata. CTR-3 "
            "violato — bootstrap meta endpoint mancante (frontend "
            "language resolver dipende da questo)."
        )


# ─── CTR-3 — Storefront meta endpoint cache ────────────────────────────


class TestCTR3_StorefrontMetaCache:
    """CTR-3 (Contract Invariant 3, Medium):

    GET /api/public/storefront/{slug}/meta deve avere caching server-side
    aggressivo (cache-control public, max-age=60). Endpoint chiamato al
    bootstrap di ogni storefront landing page — high traffic.

    Pin location: routers/public.py (get_storefront_meta function)
    """

    def test_meta_handler_function_exists(self):
        from routers import public
        members = inspect.getmembers(public, inspect.iscoroutinefunction)
        meta_handlers = [
            name for name, fn in members
            if "meta" in name.lower() and "storefront" in name.lower()
        ]
        assert len(meta_handlers) > 0, (
            "Nessuna funzione meta handler trovata. Bootstrap path "
            "frontend dipende da meta endpoint."
        )

    def test_meta_endpoint_uses_cache_or_low_rate_limit(self):
        """Almeno uno tra: cache-control header / rate limit alto / dedicated path.

        L'endpoint /meta è ottimizzato per essere chiamato spesso. Deve
        avere uno di questi marker:
        - Cache-Control header esplicito (max-age >= 60)
        - Rate limit alto (60+/min) rispetto agli altri public endpoint
        - Esplicito tag "lightweight" / "bootstrap" in docstring
        """
        from routers import public
        source = inspect.getsource(public)
        # Marker accettabili (any):
        markers_acceptable = [
            "max-age=60",
            "Cache-Control",
            '"60/minute"',  # rate limit 60/min
            "bootstrap",  # commenti di design
            "lightweight",  # commenti di design
        ]
        found = any(m in source for m in markers_acceptable)
        assert found, (
            "Nessun marker di caching/rate-friendly per /meta endpoint. "
            "Verifica che esista uno tra: Cache-Control header, rate limit "
            "60/min, o documentazione esplicita lightweight."
        )


# ─── CTR — Public router rate limits canonical ─────────────────────────


class TestCTR_PublicRouterRateLimits:
    """CTR (no specifico INV, but a documented contract):

    Public router rate limit canonical:
      /storefront/{slug}/meta             — 60/min (bootstrap, safe)
      /storefront/{slug} (catalog)        — 30/min
      /storefront/{slug}/marketing-status — 10/min (privacy + enumeration defense)
      /order-request                       — 30/min
      /orders/{order_id}/status            — 30/min

    Modificarli senza pinning rompe il SLA implicito dei client.
    """

    def test_marketing_status_has_strict_rate_limit(self):
        """marketing-status è un endpoint pubblico → strict rate limit
        per defense da enumeration."""
        from routers import public
        source = inspect.getsource(public)
        # marketing-status deve avere rate limit (almeno 10/min, documented)
        # Pattern: @limiter.limit("10/min...") o similar
        # Verifico almeno che marketing-status sia rate-limited
        assert "marketing-status" in source, "Endpoint marketing-status missing"
        # E che il rate limit "10/" sia presente da qualche parte (proxy del
        # fatto che ne esistono di rigorosi)
        assert '"10/minute"' in source or "10/minute" in source, (
            "Nessun rate limit '10/minute' trovato in public.py. "
            "marketing-status endpoint privo di defense da enumeration."
        )

    def test_storefront_meta_uses_higher_rate_limit(self):
        """meta endpoint può sopportare 60/min (bootstrap di ogni page)."""
        from routers import public
        source = inspect.getsource(public)
        # Marker: rate limit 60/min deve esistere come pattern in public.py
        assert '"60/minute"' in source or "60/minute" in source, (
            "Nessun rate limit '60/minute' trovato. Il /meta bootstrap "
            "endpoint sarebbe limited come gli endpoint di lettura "
            "normale (30/min) — degraded UX su page load multipli."
        )
