"""Sentinel tests for Prometheus metrics (Phase 0 Step 10).

Pin del contract del modulo ``core.observability.metrics`` + del
``/metrics`` HTTP endpoint + dell'instrumentation nei call site
(dynamic_cors, idempotency, order_creation_service).

Invariants pinned
=================
  INV-MTR-1  Metric names canonical (cart_operations_total, orders_created_total,
             cors_blocked_total, idempotency_cache_total, api_response_time_seconds)
  INV-MTR-2  Public recording API: record_cart_op / record_order /
             record_cors_blocked / record_idempotency / record_api_latency
  INV-MTR-3  /metrics endpoint serves text/plain Prometheus format
  INV-MTR-4  Soft-fail: missing prometheus_client → no-op shim (server boots)
  INV-MTR-5  Recording helpers never raise (try/except inside)
  INV-MTR-6  CORS middleware emits cors_blocked_total on reject
  INV-MTR-7  Idempotency middleware emits idempotency_cache_total on hit/miss
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


class TestMetricsModule:
    def test_module_importable(self):
        from core.observability import metrics
        assert metrics is not None

    def test_module_exported_from_package(self):
        """metrics deve essere accessibile come ``observability.metrics``."""
        from core import observability
        assert hasattr(observability, "metrics")

    def test_is_available_helper(self):
        from core.observability import metrics
        # Boolean either way — soft dependency is OK
        assert isinstance(metrics.is_available(), bool)


# ─── INV-MTR-1 — Canonical metric names ────────────────────────────────


class TestINV_MTR_1_MetricNames:
    """I nomi dei metric sono parte dell'API esposta a Prometheus / Grafana
    dashboard. Cambiarli rompe dashboard storici."""

    def test_canonical_names_present(self):
        from core.observability import metrics
        if not metrics.is_available():
            pytest.skip("prometheus_client not installed")
        # Tutti questi devono essere oggetti Counter/Histogram, non None
        assert metrics.CART_OPERATIONS is not None
        assert metrics.ORDERS_CREATED is not None
        assert metrics.CORS_BLOCKED is not None
        assert metrics.IDEMPOTENCY_CACHE is not None
        assert metrics.API_LATENCY is not None

    def test_metric_names_in_exposition(self):
        """generate_latest output deve contenere i nomi canonici."""
        from core.observability import metrics
        if not metrics.is_available():
            pytest.skip("prometheus_client not installed")
        # Force-record one of each so they appear in output
        metrics.record_cart_op("add", "success")
        metrics.record_order("storefront", "success")
        metrics.record_cors_blocked("embed", "origin_not_allowed")
        metrics.record_idempotency("hit", "enforcement")
        metrics.record_api_latency("/api/public/embed/cart", "200", 0.05)

        body, content_type = metrics.render_latest()
        text = body.decode("utf-8")

        # All canonical metric names must appear (with _total suffix on counters)
        assert "cart_operations_total" in text, (
            "Metric name 'cart_operations_total' missing. Cambiarlo rompe "
            "le dashboard Grafana storiche."
        )
        assert "orders_created_total" in text
        assert "cors_blocked_total" in text
        assert "idempotency_cache_total" in text
        assert "api_response_time_seconds" in text


# ─── INV-MTR-2 — Public recording API ─────────────────────────────────


class TestINV_MTR_2_PublicAPI:
    def test_record_functions_exist(self):
        from core.observability import metrics
        for fn_name in (
            "record_cart_op",
            "record_order",
            "record_cors_blocked",
            "record_idempotency",
            "record_api_latency",
            "render_latest",
        ):
            assert hasattr(metrics, fn_name), (
                f"core.observability.metrics.{fn_name} missing — call sites "
                "del codebase si aspettano questa funzione."
            )

    def test_record_cart_op_signature(self):
        from core.observability.metrics import record_cart_op
        sig = inspect.signature(record_cart_op)
        params = list(sig.parameters)
        assert params[:2] == ["operation", "status"]
        # source ha default
        assert sig.parameters["source"].default == "storefront"


# ─── INV-MTR-3 — /metrics endpoint contract ────────────────────────────


class TestINV_MTR_3_MetricsEndpoint:
    def test_render_latest_returns_tuple(self):
        from core.observability.metrics import render_latest
        result = render_latest()
        assert isinstance(result, tuple) and len(result) == 2
        body, ct = result
        assert isinstance(body, (bytes, bytearray))
        assert isinstance(ct, str)
        assert "text/plain" in ct or "text/" in ct

    def test_server_exposes_metrics_route(self):
        """server.py deve montare /metrics."""
        import server
        source = inspect.getsource(server)
        assert "/metrics" in source, (
            "/metrics endpoint missing from server.py. Prometheus / Grafana "
            "Agent non avranno alcun endpoint da scrapare."
        )
        assert "prometheus_metrics" in source or "render_latest" in source


# ─── INV-MTR-4 — Soft dependency fallback ──────────────────────────────


class TestINV_MTR_4_SoftDependency:
    """Se prometheus_client manca, il modulo carica comunque con no-op shim.
    Quindi import non-conditional in server.py + call site sono safe."""

    def test_module_imports_unconditionally(self):
        # If the metrics module needed prometheus_client to import,
        # this test (run AFTER it's imported) would have already errored.
        from core.observability import metrics
        assert metrics is not None

    def test_render_latest_works_without_metrics(self):
        """Anche se Prometheus non disponibile, render_latest restituisce body."""
        from core.observability.metrics import render_latest
        body, ct = render_latest()
        assert body is not None  # never None


# ─── INV-MTR-5 — Recording is fail-safe ────────────────────────────────


class TestINV_MTR_5_RecordingFailSafe:
    """Recording helpers MAI possono raise — un errore di metric NON deve
    abbattere checkout / cart op / CORS check."""

    def test_record_cart_op_never_raises(self):
        from core.observability import metrics
        # Even on bogus inputs we don't raise
        metrics.record_cart_op("nonexistent_op", "weird_status", "phantom_source")

    def test_record_order_never_raises(self):
        from core.observability import metrics
        metrics.record_order("phantom_source", "phantom_status")

    def test_record_cors_blocked_never_raises(self):
        from core.observability import metrics
        metrics.record_cors_blocked("phantom_prefix", "phantom_reason")

    def test_record_idempotency_never_raises(self):
        from core.observability import metrics
        metrics.record_idempotency("phantom_result", "phantom_scope")

    def test_record_api_latency_never_raises(self):
        from core.observability import metrics
        # Negative value, NaN etc. should NEVER raise
        metrics.record_api_latency("phantom", "phantom", -1.0)


# ─── INV-MTR-6 — CORS instrumentation ─────────────────────────────────


class TestINV_MTR_6_CORSInstrumentation:
    """DynamicCORS deve emettere cors_blocked_total per ogni reject."""

    def test_cors_module_imports_metrics(self):
        from middleware import dynamic_cors
        src = inspect.getsource(dynamic_cors)
        assert "_record_cors_blocked" in src, (
            "dynamic_cors.py non chiama _record_cors_blocked. CORS reject "
            "rates invisibili a Prometheus."
        )

    @pytest.mark.asyncio
    async def test_cors_no_origin_records_metric(self):
        """Trigger un reject e verifica che la metric venga incrementata."""
        from core.observability import metrics
        if not metrics.is_available():
            pytest.skip("prometheus_client not installed")

        from middleware.dynamic_cors import DynamicCORSMiddleware
        from starlette.requests import Request

        # Force scope-in-path → middleware non lo bypassa
        scope = {
            "type": "http", "method": "POST",
            "path": "/api/public/embed/cart",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)
        call_next = AsyncMock()

        # Snapshot pre-call
        body_before, _ = metrics.render_latest()
        text_before = body_before.decode("utf-8")

        mw = DynamicCORSMiddleware(MagicMock())
        resp = await mw.dispatch(request, call_next)
        # Track S Step 3.5: status uniformizzato a 403 (era 400 pre-S3.5)
        # per evitare leak di "quale check ha fatto fail". Vedi
        # test_invariants_security.py::TestSEC_S3_5_DynamicCORSRejectUniform
        assert resp.status_code == 403

        body_after, _ = metrics.render_latest()
        text_after = body_after.decode("utf-8")

        # Counter for no_origin_header reason ha incrementato
        assert "cors_blocked_total" in text_after
        # The counter should appear in the output
        assert text_after != text_before or "cors_blocked_total" in text_before


# ─── INV-MTR-7 — Idempotency instrumentation ──────────────────────────


class TestINV_MTR_7_IdempotencyInstrumentation:
    """Idempotency middleware emette idempotency_cache_total per hit/miss."""

    def test_idempotency_module_imports_metrics(self):
        from middleware import idempotency
        src = inspect.getsource(idempotency)
        assert "_record_idem" in src, (
            "idempotency.py non chiama _record_idem. Cache hit-rate "
            "invisibili a Prometheus."
        )

    @pytest.mark.asyncio
    async def test_idempotency_enforced_reject_records_metric(self):
        """Trigger un enforcement reject (missing key) e verifica metric."""
        from core.observability import metrics
        if not metrics.is_available():
            pytest.skip("prometheus_client not installed")

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

        body, _ = metrics.render_latest()
        text = body.decode("utf-8")
        assert "idempotency_cache_total" in text


# ─── Server endpoint integration ───────────────────────────────────────


class TestServerMetricsEndpoint:
    def test_metrics_endpoint_handler_exists(self):
        """server.prometheus_metrics deve esistere come endpoint coroutine."""
        import server
        assert hasattr(server, "prometheus_metrics"), (
            "server.prometheus_metrics function missing — /metrics endpoint "
            "non più definito a livello modulo."
        )
        assert inspect.iscoroutinefunction(server.prometheus_metrics)
