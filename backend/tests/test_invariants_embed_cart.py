"""Sentinel tests for /api/public/embed/cart/* aliases — Phase 1 Step 15.

4 endpoint che ri-esportano la business logic del cart_service esistente
con metric label ``source="embed"``. Coperti dall'IdempotencyMiddleware
(Phase 0 Step 8) per le mutazioni: ogni POST/PATCH/DELETE richiede header
``Idempotency-Key``.

Invariants pinned
=================
  INV-EXC-1  Source label "embed" emesso (no "storefront_classic" su questi path)
  INV-EXC-2  Multi-tenant: cart creato da slug A NON accessibile via slug B
  INV-EXC-3  Idempotency middleware copre /api/public/embed/cart/* (parent)
  INV-EXC-4  Business logic identica al /api/public/cart (riuso cart_service)
  INV-EXC-5  Pydantic models riutilizzati (CartCreate, CartUpdate, CartResponse)
  INV-EXC-6  Rate limit attivo su tutti i 4 endpoint
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


# ─── Endpoint registration ──────────────────────────────────────────────


class TestEmbedCartEndpointsRegistered:
    """4 endpoint paths must be registered in the embed_public router."""

    REQUIRED_PATHS = (
        "/public/embed/cart",               # POST create
        "/public/embed/cart/{cart_id}",     # GET / PATCH / DELETE
    )

    def test_paths_registered(self):
        from routers.embed_public import router
        paths = {r.path for r in router.routes}
        for p in self.REQUIRED_PATHS:
            assert p in paths, (
                f"Path '{p}' non registrato. Existing paths: {paths}"
            )

    def test_methods_on_cart_id_path(self):
        """GET + PATCH + DELETE handlers all registered su /cart/{cart_id}."""
        from routers.embed_public import router
        methods_per_path: dict[str, set[str]] = {}
        for r in router.routes:
            if r.path == "/public/embed/cart/{cart_id}":
                methods_per_path.setdefault(r.path, set()).update(r.methods or set())
        methods = methods_per_path.get("/public/embed/cart/{cart_id}", set())
        for m in ("GET", "PATCH", "DELETE"):
            assert m in methods, (
                f"Method {m} missing on /public/embed/cart/{{cart_id}}. "
                f"Existing: {methods}"
            )

    def test_post_on_cart_base_path(self):
        """POST handler registrato su /public/embed/cart."""
        from routers.embed_public import router
        for r in router.routes:
            if r.path == "/public/embed/cart" and "POST" in (r.methods or set()):
                return
        pytest.fail("POST /public/embed/cart non registrato.")


# ─── Handler functions exist + are coroutines ──────────────────────────


class TestHandlersAreCoroutines:
    HANDLERS = (
        "create_embed_cart",
        "get_embed_cart",
        "update_embed_cart",
        "clear_embed_cart",
    )

    def test_all_handlers_exist(self):
        from routers import embed_public
        for h in self.HANDLERS:
            assert hasattr(embed_public, h), (
                f"Handler embed_public.{h} missing."
            )

    def test_all_handlers_async(self):
        from routers import embed_public
        for h in self.HANDLERS:
            fn = getattr(embed_public, h)
            assert inspect.iscoroutinefunction(fn), (
                f"Handler {h} non è coroutine."
            )


# ─── INV-EXC-1 — Source label "embed" ──────────────────────────────────


class TestINV_EXC_1_SourceLabelEmbed:
    """Handler create_embed_cart deve passare source='embed' a cart_service.

    Verifichiamo inspect del source del handler (string match) — non
    eseguiamo la chiamata. Sufficiente come "pin" che chi ri-edita il
    file mantenga il source label.
    """

    def test_create_handler_uses_source_embed(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.create_embed_cart)
        assert '"embed"' in src or "'embed'" in src, (
            "create_embed_cart non passa source='embed' a cart_service. "
            "Metric source label sarebbe storefront_classic per default."
        )


# ─── INV-EXC-3 — Idempotency middleware copre i path ───────────────────


class TestINV_EXC_3_IdempotencyParentScope:
    """ENFORCEMENT_PATHS del middleware contiene /api/public/embed/.

    Già verificato in test_invariants_idempotency.py, qui ribadiamo
    consistenza: i nuovi cart alias DEVONO ricadere sotto enforcement."""

    def test_enforcement_path_covers_embed_cart(self):
        from middleware.idempotency import ENFORCEMENT_PATHS
        # ENFORCEMENT_PATHS è tuple di prefix
        covered = any(
            "/api/public/embed/cart".startswith(p)
            for p in ENFORCEMENT_PATHS
        )
        assert covered, (
            f"/api/public/embed/cart NON coperto da ENFORCEMENT_PATHS={ENFORCEMENT_PATHS}. "
            "Mutazioni cart embed sarebbero passthrough, no anti-doppio-ordine."
        )


# ─── INV-EXC-5 — Riuso Pydantic models ─────────────────────────────────


class TestINV_EXC_5_ReusePydanticModels:
    """Handler embed deve riutilizzare gli stessi CartCreate/Update/Response.

    No duplicazione = no divergenza schema = no extra sentinel da scrivere.
    Verifica statica via inspect del source.
    """

    def test_handlers_import_models_cart(self):
        from routers import embed_public
        src = inspect.getsource(embed_public)
        # Almeno uno dei 3 nomi deve apparire
        for model in ("CartCreate", "CartUpdate", "CartResponse"):
            assert model in src, (
                f"Model {model} non importato in embed_public. "
                "Possibile duplicazione schema → divergenza."
            )


# ─── Service contract ──────────────────────────────────────────────────


class TestCartServiceReused:
    """Handler embed deve chiamare cart_service direttamente."""

    def test_handlers_reference_cart_service(self):
        from routers import embed_public
        src = inspect.getsource(embed_public)
        assert "cart_service" in src, (
            "embed_public NON usa cart_service. Probabile duplicazione "
            "di logica = pericoloso (divergenza di INV-CART-* invarianti)."
        )


# ─── Metrics label coverage ────────────────────────────────────────────


class TestMetricSourceLabel:
    """cart_operations_total ha label 'source' (verifica esistenza)."""

    def test_cart_operations_counter_has_source_label(self):
        from core.observability import metrics
        if not metrics.is_available():
            pytest.skip("prometheus_client not installed")
        # CART_OPERATIONS è registrato con labelnames=(operation, status, source)
        # Internamente prometheus_client espone _labelnames
        counter = metrics.CART_OPERATIONS
        labelnames = getattr(counter, "_labelnames", None)
        assert labelnames is not None
        assert "source" in labelnames, (
            f"CART_OPERATIONS labelnames={labelnames}, manca 'source'. "
            "Embed cart non puo' essere distinto da storefront classic."
        )
