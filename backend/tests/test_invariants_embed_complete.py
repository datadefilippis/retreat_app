"""Sentinel tests for /api/public/embed/checkout/complete — Phase 1 Step 17.

Bridge HTML endpoint che chiude il flow Stripe Checkout cross-origin:
- Riceve order_id come query param
- Risolve order.embed_metadata.return_url (server-derived, MAI da query)
- Ritorna HTML statico con <script> postMessage al parent window
- CSP rigoroso, no-cache, anti-XSS

Invariants pinned
=================
  INV-EXM-1   Endpoint registered + handler coroutine
  INV-EXM-2   Order senza embed_metadata.return_url → 404
  INV-EXM-3   Response Content-Type text/html con postMessage
  INV-EXM-4   Target origin DERIVATO server-side (mai dalla query)
  INV-EXM-5   Anti-XSS: order_id e status escapati in HTML
  INV-EXM-6   CSP frame-ancestors 'none' header presente
  INV-EXM-7   Cache-Control no-store (response varia per order)
  INV-EXM-8   Service helper get_embed_complete_payload esiste + async
  INV-EXM-9   Metric counter embed_postmessage_bridges_total emesso
  INV-EXM-10  No PII leak (no email/name/items nel HTML)
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


# ─── INV-EXM-1: endpoint + handler ─────────────────────────────────────


class TestEmbedCompleteEndpoint:
    def test_endpoint_registered(self):
        from routers.embed_public import router
        paths = {(r.path, tuple(sorted(r.methods or set())))
                 for r in router.routes}
        target = ("/public/embed/checkout/complete", ("GET",))
        assert target in paths, (
            f"GET /public/embed/checkout/complete non registrato. "
            f"Found: {sorted(paths)}"
        )

    def test_handler_is_coroutine(self):
        from routers import embed_public
        assert hasattr(embed_public, "embed_checkout_complete"), (
            "Handler embed_checkout_complete missing."
        )
        assert inspect.iscoroutinefunction(embed_public.embed_checkout_complete)


# ─── INV-EXM-8: service helper ─────────────────────────────────────────


class TestServiceHelper:
    def test_helper_exists(self):
        from services.embed_init_service import get_embed_complete_payload
        assert callable(get_embed_complete_payload)

    def test_helper_is_async(self):
        from services.embed_init_service import get_embed_complete_payload
        assert inspect.iscoroutinefunction(get_embed_complete_payload)

    def test_helper_signature(self):
        from services.embed_init_service import get_embed_complete_payload
        sig = inspect.signature(get_embed_complete_payload)
        params = set(sig.parameters)
        assert "order_id" in params, (
            f"Service signature {params} manca order_id."
        )


# ─── INV-EXM-4: target origin server-derived ──────────────────────────


class TestINV_EXM_4_OriginServerDerived:
    """Il handler NON deve mai leggere il target origin dalla query.
    Lo prende SOLO da order.embed_metadata.return_url.

    Verifica via source code inspection: handler NON deve avere
    `request.query_params.get(...)` o simili che leggano un origin
    direttamente dall'URL.
    """

    def test_handler_does_not_read_origin_from_query(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.embed_checkout_complete)
        # Patterns sospetti
        bad_patterns = (
            "query_params.get(\"return_url\"",
            "query_params.get('return_url'",
            "query_params.get(\"origin\"",
            "query_params.get('origin'",
            "query_params.get(\"target_origin\"",
        )
        for p in bad_patterns:
            assert p not in src, (
                f"Handler legge '{p}' dalla query — DEVE prenderlo SOLO "
                "da order.embed_metadata.return_url server-side."
            )

    def test_handler_reads_embed_metadata(self):
        """Confirm: handler accede a embed_metadata.return_url."""
        from routers import embed_public
        from services import embed_init_service
        src_router = inspect.getsource(embed_public.embed_checkout_complete)
        src_service = inspect.getsource(embed_init_service.get_embed_complete_payload)
        combined = src_router + src_service
        assert "embed_metadata" in combined, (
            "embed_metadata non referenziato — il return_url deve essere "
            "letto dall'order doc."
        )


# ─── INV-EXM-5: HTML escape (anti-XSS) ─────────────────────────────────


class TestINV_EXM_5_AntiXSS:
    """Helper deve avere import html.escape o equivalente."""

    def test_html_escape_used(self):
        """Service o handler deve usare html.escape sui valori reflectati."""
        from services import embed_init_service
        from routers import embed_public
        src_service = inspect.getsource(embed_init_service)
        src_router = inspect.getsource(embed_public)
        combined = src_service + src_router
        # Una delle 2 forme deve esistere
        assert (
            "html.escape" in combined
            or "from html import escape" in combined
            or "escape(" in combined
        ), (
            "Nessun html.escape() trovato nel modulo embed. Reflected "
            "XSS possible via order_id o status."
        )


# ─── INV-EXM-3 + INV-EXM-6 + INV-EXM-7: security headers ──────────────


class TestSecurityHeadersDeclared:
    """Handler deve dichiarare CSP + Cache-Control nel source code."""

    def test_csp_frame_ancestors_declared(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.embed_checkout_complete)
        assert "frame-ancestors" in src, (
            "CSP frame-ancestors NON dichiarato nel handler. "
            "L'HTML bridge potrebbe essere embedded in iframe da terzi."
        )

    def test_cache_control_no_store_declared(self):
        from routers import embed_public
        src = inspect.getsource(embed_public.embed_checkout_complete)
        assert "no-store" in src, (
            "Cache-Control no-store NON dichiarato. Response varia per "
            "order e contiene state - cache CDN potrebbe servire response "
            "wrong al customer sbagliato."
        )


# ─── INV-EXM-9: metric ────────────────────────────────────────────────


class TestMetricBridge:
    def test_counter_exists(self):
        from core.observability import metrics
        if not metrics.is_available():
            pytest.skip("prometheus_client not installed")
        assert hasattr(metrics, "EMBED_POSTMESSAGE_BRIDGES"), (
            "Counter EMBED_POSTMESSAGE_BRIDGES missing."
        )

    def test_record_helper_exists(self):
        from core.observability import metrics
        assert hasattr(metrics, "record_embed_postmessage_bridge"), (
            "Helper record_embed_postmessage_bridge missing."
        )

    def test_record_helper_fail_safe(self):
        from core.observability import metrics
        metrics.record_embed_postmessage_bridge(slug="phantom", status="phantom")


# ─── HTML output integrity (helper-level) ──────────────────────────────


class TestHTMLBridgeOutput:
    """Helper deve produrre HTML con script postMessage e meta refresh
    fallback. Test via mock dell'order doc."""

    @pytest.mark.asyncio
    async def test_helper_returns_html_with_postmessage(self):
        """Mock order doc lookup → helper ritorna dict con html + target_origin."""
        from unittest.mock import patch, AsyncMock
        from services.embed_init_service import get_embed_complete_payload

        fake_order = {
            "id": "ord_test_123",
            "organization_id": "org-x",
            "order_status": "draft",
            "payment_intent": "collected",
            "embed_metadata": {
                "return_url": "https://merchant.com/order-done",
                "source": "embed",
            },
        }
        # Mock the database.orders_collection used by the helper
        from unittest.mock import MagicMock
        mock_orders = MagicMock()
        mock_orders.find_one = AsyncMock(return_value=fake_order)
        with patch(
            "database.orders_collection", mock_orders
        ):
            result = await get_embed_complete_payload(order_id="ord_test_123")

        assert result is not None, (
            "Helper deve ritornare dict valido per order esistente."
        )
        assert "html" in result
        assert "target_origin" in result
        assert "postMessage" in result["html"], (
            "HTML non contiene postMessage call."
        )
        # Target origin server-derived
        assert result["target_origin"] == "https://merchant.com", (
            f"Target origin atteso https://merchant.com, got {result['target_origin']!r}"
        )
        # Order id presente in HTML (escapato; verifica almeno la presenza)
        assert "ord_test_123" in result["html"]

    @pytest.mark.asyncio
    async def test_helper_returns_none_when_order_missing(self):
        """Order non esistente → None (handler poi 404)."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from services.embed_init_service import get_embed_complete_payload
        mock_orders = MagicMock()
        mock_orders.find_one = AsyncMock(return_value=None)
        with patch("database.orders_collection", mock_orders):
            result = await get_embed_complete_payload(order_id="ghost")
        assert result is None

    @pytest.mark.asyncio
    async def test_helper_returns_none_when_no_embed_metadata(self):
        """Order ESISTE ma è stato creato da storefront classic
        (no embed_metadata) → None per evitare leak."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from services.embed_init_service import get_embed_complete_payload
        fake_order = {
            "id": "ord_legacy",
            "order_status": "confirmed",
            # NO embed_metadata
        }
        mock_orders = MagicMock()
        mock_orders.find_one = AsyncMock(return_value=fake_order)
        with patch("database.orders_collection", mock_orders):
            result = await get_embed_complete_payload(order_id="ord_legacy")
        assert result is None, (
            "Order senza embed_metadata.return_url NON deve esporre HTML "
            "bridge — leak di status order legacy possibile."
        )

    @pytest.mark.asyncio
    async def test_xss_payload_escaped(self):
        """Order_id contenente HTML payload deve essere escapato."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from services.embed_init_service import get_embed_complete_payload
        # Order_id con XSS payload
        evil_id = '"><script>alert(1)</script>'
        fake_order = {
            "id": evil_id,
            "order_status": "draft",
            "embed_metadata": {"return_url": "https://merchant.com/x"},
        }
        mock_orders = MagicMock()
        mock_orders.find_one = AsyncMock(return_value=fake_order)
        with patch("database.orders_collection", mock_orders):
            result = await get_embed_complete_payload(order_id=evil_id)
        assert result is not None
        # Lo script payload NON deve apparire in chiaro nell'HTML
        assert "<script>alert(1)</script>" not in result["html"], (
            "INV-EXM-5 violato: XSS reflected via order_id non escapato."
        )
