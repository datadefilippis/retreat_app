"""Sentinel tests for Dynamic CORS Middleware (Phase 0 Step 7).

Pin del contract del middleware che gestisce CORS per ``/api/public/embed/*``
e ``/api/public/ai-site/*``. Cambiare il behavior senza aggiornare i sentinel
rompe i futuri client embed/AI cross-origin.

Invariants pinned
=================
  INV-CORS-1   Middleware attivo SOLO su DYNAMIC_CORS_PATHS prefix
  INV-CORS-2   Lookup esatto Origin in store.allowed_origins (no wildcard)
  INV-CORS-3   Preflight OPTIONS gestita con 204 + full CORS headers
  INV-CORS-4   Multi-tenant: lookup atomico via slug + allowed_origins
  INV-CORS-5   Vary: Origin header su response (CDN cache safety)
  INV-CORS-6   Store model.allowed_origins field presente
"""

import asyncio
import inspect
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Env bootstrap ────────────────────────────────────────────────────────
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── INV-CORS-6 — Store.allowed_origins field ─────────────────────────────


class TestINV_CORS_6_StoreModelAllowedOrigins:
    """Store model deve esporre allowed_origins per il lookup CORS."""

    def test_store_model_has_allowed_origins_field(self):
        from models.store import Store
        fields = Store.model_fields
        assert "allowed_origins" in fields, (
            "Store model missing allowed_origins field. INV-CORS-6 violato "
            "— Dynamic CORS middleware non può lookup la lista."
        )

    def test_allowed_origins_default_empty_list(self):
        """Default vuoto — nessuna richiesta cross-origin accettata."""
        from models.store import Store
        instance = Store(organization_id="org-x", name="Test Store")
        assert instance.allowed_origins == [], (
            "Store.allowed_origins default deve essere [] (empty). "
            "Diversamente, store nuovi consentirebbero embed da chiunque."
        )

    def test_allowed_origins_is_list_of_strings(self):
        """Typing: List[str]."""
        from models.store import Store
        from typing import List
        annot = Store.model_fields["allowed_origins"].annotation
        assert annot == List[str], (
            f"allowed_origins annotation must be List[str], got {annot}"
        )


# ─── Middleware module contract ──────────────────────────────────────────


class TestDynamicCORSMiddlewareModule:
    """Module-level contract: middleware importable, key symbols presenti."""

    def test_middleware_module_importable(self):
        from middleware import dynamic_cors
        assert dynamic_cors is not None

    def test_middleware_class_exists(self):
        from middleware.dynamic_cors import DynamicCORSMiddleware
        from starlette.middleware.base import BaseHTTPMiddleware
        assert issubclass(DynamicCORSMiddleware, BaseHTTPMiddleware)

    def test_dynamic_cors_paths_tuple_exists(self):
        """Lista path che attivano il middleware è esportata."""
        from middleware.dynamic_cors import DYNAMIC_CORS_PATHS
        assert isinstance(DYNAMIC_CORS_PATHS, tuple)
        assert "/api/public/embed/" in DYNAMIC_CORS_PATHS
        assert "/api/public/ai-site/" in DYNAMIC_CORS_PATHS

    def test_phase1_f3_customer_paths_in_scope(self):
        """Phase 1 hardening F3: customer area embeddable cross-origin."""
        from middleware.dynamic_cors import DYNAMIC_CORS_PATHS
        assert "/api/customer-auth/" in DYNAMIC_CORS_PATHS, (
            "F3 regression: /api/customer-auth/ deve essere in "
            "DYNAMIC_CORS_PATHS per consentire signup/login cross-origin "
            "via embed SDK (Stream A)."
        )
        assert "/api/customer/" in DYNAMIC_CORS_PATHS, (
            "F3 regression: /api/customer/ deve essere in DYNAMIC_CORS_PATHS "
            "per consentire customer portal embed (Stream A 'MyArea')."
        )

    def test_cache_helpers_exported(self):
        """clear_cache exposed per testing + admin tooling."""
        from middleware.dynamic_cors import clear_cache
        assert callable(clear_cache)


# ─── INV-CORS-1 — Middleware attivo SOLO su DYNAMIC_CORS_PATHS ──────────


class TestINV_CORS_1_PathScoping:
    """Middleware passa-through per path fuori scope."""

    @pytest.mark.asyncio
    async def test_passthrough_for_unscoped_path(self):
        """Path /api/auth/login NON triggera il middleware."""
        from middleware.dynamic_cors import DynamicCORSMiddleware
        from starlette.requests import Request

        # Mock Request con path fuori scope
        scope = {
            "type": "http", "method": "GET", "path": "/api/auth/login",
            "headers": [(b"origin", b"https://evil.example.com")],
            "query_string": b"",
        }
        request = Request(scope)

        call_next = AsyncMock(return_value=MagicMock(headers={}, status_code=200))
        mw = DynamicCORSMiddleware(MagicMock())
        await mw.dispatch(request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_passthrough_for_storefront_classic(self):
        """Path /api/public/storefront/* (storefront classic) NON triggera."""
        from middleware.dynamic_cors import DynamicCORSMiddleware
        from starlette.requests import Request

        scope = {
            "type": "http", "method": "GET",
            "path": "/api/public/storefront/marco-conti-coaching",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=MagicMock(headers={}, status_code=200))
        mw = DynamicCORSMiddleware(MagicMock())
        await mw.dispatch(request, call_next)
        call_next.assert_called_once()


# ─── F3 — Opt-in guard for customer area paths ────────────────────────


class TestF3_CustomerOptInGuard:
    """Phase 1 F3: /api/customer-auth/* e /api/customer/* attivano il
    middleware SOLO se la richiesta dichiara uno slug. Questo preserva il
    flow same-origin dall'admin SPA su afianco.app (no slug signal →
    passthrough al CORSMiddleware statico).
    """

    @pytest.mark.asyncio
    async def test_customer_auth_without_slug_signals_passthrough(self):
        """Senza slug header/query, /customer-auth/* deve fare passthrough."""
        from middleware.dynamic_cors import DynamicCORSMiddleware
        from starlette.requests import Request

        scope = {
            "type": "http", "method": "POST",
            "path": "/api/customer-auth/login",
            # Origin=afianco.app (same-origin from admin SPA simulation)
            "headers": [(b"origin", b"https://afianco.app")],
            "query_string": b"",
            "path_params": {},
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=MagicMock(headers={}, status_code=200))
        mw = DynamicCORSMiddleware(MagicMock())
        await mw.dispatch(request, call_next)
        call_next.assert_called_once()  # passthrough → downstream chiamato

    @pytest.mark.asyncio
    async def test_customer_with_slug_header_triggers_enforcement(self):
        """Con X-Afianco-Store-Slug header presente, customer-auth scatta."""
        from middleware.dynamic_cors import DynamicCORSMiddleware, clear_cache
        from starlette.requests import Request

        clear_cache()
        scope = {
            "type": "http", "method": "POST",
            "path": "/api/customer-auth/login",
            "headers": [
                (b"origin", b"https://attacker.example.com"),
                (b"x-afianco-store-slug", b"test-store"),
            ],
            "query_string": b"",
            "path_params": {},
        }
        request = Request(scope)

        with patch("middleware.dynamic_cors._is_origin_allowed",
                   new=AsyncMock(return_value=False)):
            call_next = AsyncMock()
            mw = DynamicCORSMiddleware(MagicMock())
            resp = await mw.dispatch(request, call_next)
            assert resp.status_code == 403, (
                "Customer-auth con slug header + origin non in allowlist "
                "deve essere 403 (enforcement attivo)."
            )
            call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_strict_embed_path_enforces_without_slug_signal(self):
        """/api/public/embed/* è strict — niente passthrough anche senza slug."""
        from middleware.dynamic_cors import DynamicCORSMiddleware
        from starlette.requests import Request

        scope = {
            "type": "http", "method": "POST",
            "path": "/api/public/embed/cart",
            "headers": [],  # no Origin, no slug — should reject (uniform 403)
            "query_string": b"",
            "path_params": {},
        }
        request = Request(scope)
        call_next = AsyncMock()
        mw = DynamicCORSMiddleware(MagicMock())
        resp = await mw.dispatch(request, call_next)
        # Track S Step 3.5: status uniformizzato a 403 (era 400 pre-S3.5)
        # per evitare leak di "quale check ha fatto fail" (Origin missing
        # vs slug missing vs origin not allowed — ora tutti 403).
        # Pin: tests/test_invariants_security.py::TestSEC_S3_5_DynamicCORSRejectUniform
        assert resp.status_code == 403
        call_next.assert_not_called()


# ─── INV-CORS-2 — Exact Origin lookup ──────────────────────────────────


class TestINV_CORS_2_ExactOriginLookup:
    """Origin matching è esatto, mai wildcard."""

    @pytest.mark.asyncio
    async def test_blocks_origin_not_in_allowlist(self):
        """Origin sconosciuto → 403."""
        from middleware.dynamic_cors import DynamicCORSMiddleware, clear_cache
        from starlette.requests import Request

        clear_cache()

        scope = {
            "type": "http", "method": "GET",
            "path": "/api/public/embed/store/test-slug/products",
            "headers": [(b"origin", b"https://evil.example.com")],
            "query_string": b"",
            "path_params": {"slug": "test-slug"},
        }
        request = Request(scope)
        # Mock the path_params manually since Starlette doesn't populate
        # them outside the routing context.
        request.scope["path_params"] = {"slug": "test-slug"}

        with patch("middleware.dynamic_cors._is_origin_allowed", new=AsyncMock(return_value=False)):
            call_next = AsyncMock()
            mw = DynamicCORSMiddleware(MagicMock())
            resp = await mw.dispatch(request, call_next)
            assert resp.status_code == 403
            call_next.assert_not_called()  # downstream MAI chiamato

    @pytest.mark.asyncio
    async def test_allows_origin_in_allowlist(self):
        """Origin whitelisted → passa through + headers iniettati."""
        from middleware.dynamic_cors import DynamicCORSMiddleware, clear_cache
        from starlette.requests import Request

        clear_cache()

        scope = {
            "type": "http", "method": "GET",
            "path": "/api/public/embed/store/test-slug/products",
            "headers": [(b"origin", b"https://merchantbrand.com")],
            "query_string": b"",
            "path_params": {"slug": "test-slug"},
        }
        request = Request(scope)
        request.scope["path_params"] = {"slug": "test-slug"}

        mock_response = MagicMock(headers={}, status_code=200)

        with patch("middleware.dynamic_cors._is_origin_allowed", new=AsyncMock(return_value=True)):
            call_next = AsyncMock(return_value=mock_response)
            mw = DynamicCORSMiddleware(MagicMock())
            resp = await mw.dispatch(request, call_next)
            call_next.assert_called_once()
            # Headers iniettati
            assert resp.headers["Access-Control-Allow-Origin"] == "https://merchantbrand.com"
            assert resp.headers["Access-Control-Allow-Credentials"] == "true"


# ─── INV-CORS-3 — Preflight OPTIONS ─────────────────────────────────────


class TestINV_CORS_3_PreflightHandling:
    """OPTIONS preflight → 204 senza chiamare downstream."""

    @pytest.mark.asyncio
    async def test_options_preflight_returns_204(self):
        from middleware.dynamic_cors import DynamicCORSMiddleware, clear_cache
        from starlette.requests import Request

        clear_cache()

        scope = {
            "type": "http", "method": "OPTIONS",
            "path": "/api/public/embed/cart",
            "headers": [(b"origin", b"https://merchantbrand.com")],
            "query_string": b"slug=test",
            "path_params": {},
        }
        request = Request(scope)

        with patch("middleware.dynamic_cors._is_origin_allowed", new=AsyncMock(return_value=True)):
            call_next = AsyncMock()
            mw = DynamicCORSMiddleware(MagicMock())
            resp = await mw.dispatch(request, call_next)
            assert resp.status_code == 204
            call_next.assert_not_called()  # OPTIONS short-circuit
            # Check headers preflight canonical
            assert resp.headers["Access-Control-Allow-Origin"] == "https://merchantbrand.com"
            assert "POST" in resp.headers["Access-Control-Allow-Methods"]
            assert "Idempotency-Key" in resp.headers["Access-Control-Allow-Headers"]


# ─── INV-CORS-4 — Multi-tenant lookup ──────────────────────────────────


class TestINV_CORS_4_MultiTenantLookup:
    """Lookup atomico Mongo filtra su (slug, allowed_origins)."""

    def test_lookup_function_filters_on_slug_and_origin(self):
        """_is_origin_allowed costruisce filter Mongo {slug, allowed_origins}."""
        from middleware import dynamic_cors
        source = inspect.getsource(dynamic_cors._is_origin_allowed)
        assert '"slug": slug' in source, (
            "_is_origin_allowed non filtra su slug. Cross-store leak possibile."
        )
        assert '"allowed_origins": origin' in source, (
            "_is_origin_allowed non filtra su allowed_origins. Lookup esatto "
            "non garantito."
        )
        assert '"is_active": True' in source, (
            "_is_origin_allowed non filtra su is_active. Store deattivati "
            "potrebbero ancora accettare embed."
        )


# ─── INV-CORS-5 — Vary header ──────────────────────────────────────────


class TestINV_CORS_5_VaryHeader:
    """Response includes Vary: Origin per cache safety."""

    @pytest.mark.asyncio
    async def test_vary_origin_header_set(self):
        from middleware.dynamic_cors import DynamicCORSMiddleware, clear_cache
        from starlette.requests import Request

        clear_cache()
        scope = {
            "type": "http", "method": "GET",
            "path": "/api/public/embed/store/x/products",
            "headers": [(b"origin", b"https://merchant.com")],
            "query_string": b"",
            "path_params": {"slug": "x"},
        }
        request = Request(scope)
        request.scope["path_params"] = {"slug": "x"}
        mock_response = MagicMock(headers={}, status_code=200)

        with patch("middleware.dynamic_cors._is_origin_allowed", new=AsyncMock(return_value=True)):
            mw = DynamicCORSMiddleware(MagicMock())
            resp = await mw.dispatch(request, AsyncMock(return_value=mock_response))
            assert "Origin" in resp.headers.get("Vary", ""), (
                "Response manca Vary: Origin header. CDN/Cloudflare può "
                "cachare con wrong Allow-Origin per visitatori di origin diverso."
            )


# ─── Server integration ────────────────────────────────────────────────


class TestServerInstallsMiddleware:
    """server.py installa il middleware nella stack."""

    def test_server_imports_and_adds_middleware(self):
        import inspect
        import server
        source = inspect.getsource(server)
        assert "DynamicCORSMiddleware" in source, (
            "server.py non importa DynamicCORSMiddleware. Middleware non "
            "installato — embed cross-origin restano bloccati da CORS statico."
        )
        assert "app.add_middleware(DynamicCORSMiddleware)" in source, (
            "server.py non chiama add_middleware(DynamicCORSMiddleware). "
            "Middleware definito ma non attivo."
        )

    def test_middleware_added_after_static_cors(self):
        """LIFO: add ordering = DynamicCORS dopo CORSMiddleware statico
        → eseguito PRIMA (perché last-added is innermost).

        Cerchiamo l'invocazione vera `app.add_middleware(DynamicCORSMiddleware)`,
        non un'eventuale menzione del nome nei commenti (che ha causato un
        falso positivo dopo Phase 1 hardening F1).
        """
        import inspect
        import server
        source = inspect.getsource(server)
        # Static CORSMiddleware: cerca l'add_middleware con allow_credentials
        # come ancoraggio canonico (è un argomento specifico solo a questa chiamata).
        idx_static = source.find("CORSMiddleware,\n    allow_credentials")
        # Dynamic CORS: usa rfind sul pattern app.add_middleware() esatto.
        idx_dynamic = source.rfind("app.add_middleware(DynamicCORSMiddleware)")
        assert idx_static > 0, "CORSMiddleware statico non trovato in server.py"
        assert idx_dynamic > 0, (
            "app.add_middleware(DynamicCORSMiddleware) non trovato in server.py"
        )
        assert idx_dynamic > idx_static, (
            "DynamicCORSMiddleware deve essere added DOPO CORSMiddleware "
            "statico (LIFO: last-added = first-executed = correct order)."
        )


# ─── Cache contract ────────────────────────────────────────────────────


class TestDynamicCORSCache:
    """TTL cache per (slug, origin) — 5min."""

    def test_cache_ttl_constant_is_5_minutes(self):
        from middleware.dynamic_cors import _CACHE_TTL_SECONDS
        assert _CACHE_TTL_SECONDS == 5 * 60, (
            f"_CACHE_TTL_SECONDS = {_CACHE_TTL_SECONDS}, expected 300. "
            "Modifiche admin a allowed_origins si propagano lentamente."
        )

    def test_clear_cache_empties_dict(self):
        from middleware.dynamic_cors import _CACHE, _cache_store, clear_cache
        _cache_store("test-slug", "https://test.com", True)
        assert len(_CACHE) > 0
        clear_cache()
        assert len(_CACHE) == 0
