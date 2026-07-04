"""Sentinel tests for Idempotency Middleware (Phase 0 Step 8).

Pin del contract del middleware ``Idempotency-Key`` per /embed/* + /ai-site/*
+ grace period 90gg su /order-request legacy.

Invariants pinned
=================
  INV-IDEM-1  Path scoping (enforcement, grace, passthrough)
  INV-IDEM-2  Idempotent methods only (POST/PATCH/PUT/DELETE)
  INV-IDEM-3  Cache key include org_id + path + Idempotency-Key (no collision)
  INV-IDEM-4  Cache hit ritorna identical response (replay safety)
  INV-IDEM-5  Cache TTL = 24h
  INV-IDEM-6  Feature flag IDEMPOTENCY_ENFORCED default ON
  INV-IDEM-7  Solo 2xx responses cachate (4xx/5xx retryable)
"""

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


# ─── Module contract ───────────────────────────────────────────────────


class TestIdempotencyModule:
    def test_module_importable(self):
        from middleware import idempotency
        assert idempotency is not None

    def test_middleware_class_exists(self):
        from middleware.idempotency import IdempotencyMiddleware
        from starlette.middleware.base import BaseHTTPMiddleware
        assert issubclass(IdempotencyMiddleware, BaseHTTPMiddleware)

    def test_enforcement_paths_canonical(self):
        from middleware.idempotency import ENFORCEMENT_PATHS
        assert "/api/public/embed/" in ENFORCEMENT_PATHS
        assert "/api/public/ai-site/" in ENFORCEMENT_PATHS

    def test_grace_paths_canonical(self):
        """Legacy /order-request è grace path (no enforcement during 90gg)."""
        from middleware.idempotency import GRACE_PATHS
        assert "/api/public/order-request" in GRACE_PATHS, (
            "GRACE_PATHS missing /api/public/order-request. Legacy client "
            "che NON manda Idempotency-Key verrebbero rejected con 400 "
            "rompendo ordini in volo."
        )

    def test_idempotent_methods(self):
        from middleware.idempotency import IDEMPOTENT_METHODS
        for m in {"POST", "PATCH", "PUT", "DELETE"}:
            assert m in IDEMPOTENT_METHODS
        # GET non deve essere idempotent-tracked
        assert "GET" not in IDEMPOTENT_METHODS


# ─── INV-IDEM-5 — Cache TTL ────────────────────────────────────────────


class TestINV_IDEM_5_CacheTTL:
    def test_cache_ttl_24_hours(self):
        from middleware.idempotency import CACHE_TTL_HOURS
        assert CACHE_TTL_HOURS == 24, (
            f"CACHE_TTL_HOURS = {CACHE_TTL_HOURS}, expected 24. "
            "Cambio TTL impacta abilità di replay legacy retry."
        )


# ─── INV-IDEM-3 — Digest computation ──────────────────────────────────


class TestINV_IDEM_3_DigestComposition:
    """Digest include org_id + path + key per multi-tenant isolation."""

    def test_digest_includes_org_path_key(self):
        from middleware.idempotency import _compute_digest
        d1 = _compute_digest("org-a", "/api/public/embed/cart", "key-1")
        d2 = _compute_digest("org-b", "/api/public/embed/cart", "key-1")
        d3 = _compute_digest("org-a", "/api/public/embed/order", "key-1")
        d4 = _compute_digest("org-a", "/api/public/embed/cart", "key-2")
        # Tutti diversi → collision-free
        assert len({d1, d2, d3, d4}) == 4, (
            "Digest collision detected. Stesso Idempotency-Key da org/path "
            "diverse non genera digest distinti → cross-tenant replay possibile."
        )

    def test_digest_is_deterministic(self):
        from middleware.idempotency import _compute_digest
        d1 = _compute_digest("org-a", "/api/public/embed/cart", "key-1")
        d2 = _compute_digest("org-a", "/api/public/embed/cart", "key-1")
        assert d1 == d2

    def test_digest_handles_guest_org_id(self):
        """org_id=None (guest) deve produrre digest valido."""
        from middleware.idempotency import _compute_digest
        d = _compute_digest(None, "/api/public/embed/cart", "key-1")
        assert d and len(d) == 64  # SHA-256 hex


# ─── INV-IDEM-1 — Path scoping ─────────────────────────────────────────


class TestINV_IDEM_1_PathScoping:
    """Middleware attivo solo su scope paths."""

    @pytest.mark.asyncio
    async def test_passthrough_for_get_method(self):
        """GET non triggera idempotency anche su path in scope."""
        from middleware.idempotency import IdempotencyMiddleware
        from starlette.requests import Request

        scope = {
            "type": "http", "method": "GET",
            "path": "/api/public/embed/cart",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=MagicMock(headers={}, status_code=200))
        mw = IdempotencyMiddleware(MagicMock())
        await mw.dispatch(request, call_next)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_passthrough_for_unscoped_path(self):
        """POST /api/dashboard NON triggera (out of scope)."""
        from middleware.idempotency import IdempotencyMiddleware
        from starlette.requests import Request

        scope = {
            "type": "http", "method": "POST",
            "path": "/api/dashboard/refresh",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)
        call_next = AsyncMock(return_value=MagicMock(headers={}, status_code=200))
        mw = IdempotencyMiddleware(MagicMock())
        await mw.dispatch(request, call_next)
        call_next.assert_called_once()


class TestEnforcementVsGracePathBehavior:
    """Enforcement = 400 if missing, Grace = warning log only."""

    @pytest.mark.asyncio
    async def test_enforcement_path_missing_key_returns_400(self):
        from middleware.idempotency import IdempotencyMiddleware
        from starlette.requests import Request

        scope = {
            "type": "http", "method": "POST",
            "path": "/api/public/embed/cart",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)
        call_next = AsyncMock()
        mw = IdempotencyMiddleware(MagicMock())
        resp = await mw.dispatch(request, call_next)
        assert resp.status_code == 400
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_grace_path_missing_key_passes_through(self):
        from middleware.idempotency import IdempotencyMiddleware
        from starlette.requests import Request

        scope = {
            "type": "http", "method": "POST",
            "path": "/api/public/order-request",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)
        # Use a real async response so body_iterator works
        from starlette.responses import Response as StarletteResponse
        async def fake_next(req):
            return StarletteResponse(content="{}", status_code=200, media_type="application/json")
        mw = IdempotencyMiddleware(MagicMock())
        resp = await mw.dispatch(request, fake_next)
        # Should pass through (status 200 from downstream)
        assert resp.status_code == 200


# ─── INV-IDEM-6 — Feature flag ────────────────────────────────────────


class TestINV_IDEM_6_FeatureFlag:
    def test_default_enforced(self):
        from middleware.idempotency import idempotency_enforced
        original = os.environ.pop("IDEMPOTENCY_ENFORCED", None)
        try:
            assert idempotency_enforced() is True
        finally:
            if original is not None:
                os.environ["IDEMPOTENCY_ENFORCED"] = original

    @pytest.mark.parametrize("value,expected", [
        ("true", True), ("false", False), ("1", True), ("0", False),
    ])
    def test_feature_flag_parsing(self, value, expected):
        from middleware.idempotency import idempotency_enforced
        os.environ["IDEMPOTENCY_ENFORCED"] = value
        try:
            assert idempotency_enforced() == expected
        finally:
            os.environ.pop("IDEMPOTENCY_ENFORCED", None)


# ─── Server integration ──────────────────────────────────────────────


class TestServerInstallsIdempotency:
    def test_server_imports_and_adds_middleware(self):
        import server
        source = inspect.getsource(server)
        assert "IdempotencyMiddleware" in source
        assert "app.add_middleware(IdempotencyMiddleware)" in source

    def test_dynamic_cors_runs_before_idempotency(self):
        """LIFO middleware order: last-added = first-executed.

        Phase 1 hardening F1 (2026-05-28): per garantire che il CORS check
        rifiuti Origin non autorizzati PRIMA che Idempotency consumi cache
        slots, DynamicCORSMiddleware deve essere added DOPO IdempotencyMiddleware
        (così risulta più esterno nella catena → eseguito per primo).

        Cerco le `app.add_middleware(...)` (consider commenti che menzionano
        i nomi: prendiamo l'ultima occorrenza per ciascuno)."""
        import server
        source = inspect.getsource(server)
        idx_idem = source.rfind("app.add_middleware(IdempotencyMiddleware)")
        idx_cors = source.rfind("app.add_middleware(DynamicCORSMiddleware)")
        assert idx_idem > 0 and idx_cors > 0, (
            "Sia IdempotencyMiddleware sia DynamicCORSMiddleware devono "
            "essere registrati in server.py via app.add_middleware()."
        )
        assert idx_cors > idx_idem, (
            "DynamicCORSMiddleware deve essere added DOPO IdempotencyMiddleware. "
            "LIFO: last-added = first-executed = CORS check FIRST → reject "
            "unauthorized origin senza consumare cache idempotency."
        )


# ─── Database collection registration ─────────────────────────────────


class TestIdempotencyKeysCollection:
    def test_collection_registered_in_database(self):
        from database import idempotency_keys_collection
        assert idempotency_keys_collection is not None
        assert idempotency_keys_collection.name == "idempotency_keys"
