"""Sentinel tests for Cart ↔ Order integration (Phase 0 Step 5).

Pin del contract di linking tra cart server-side e order al checkout.
Dopo l'order creation, il cart viene marcato come ``converted_to_order_id``
così:
  1. abandon recovery worker NON lo include più nei candidates
  2. analytics può tracciare cart→order conversion rate
  3. cleanup TTL job rimuove cart converted dopo ~30gg di history

Invariants pinned
=================
  INV-CART-5  OrderCreationService accetta optional cart_id parameter
  INV-CART-6  Cart conversion è SOFT-FAIL (non rompe order on failure)
  INV-CART-7  Router estrae cart_id dal cookie afianco_cart_id
  INV-CART-8  Router clear cookie post-conversion success
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


# ─── INV-CART-5 — Service accepts cart_id ───────────────────────────────


class TestINV_CART_5_ServiceAcceptsCartId:
    """OrderCreationService.submit_order_from_storefront accepts cart_id."""

    def test_signature_includes_cart_id_param(self):
        """cart_id deve essere keyword-only optional param."""
        from services.order_creation_service import submit_order_from_storefront
        sig = inspect.signature(submit_order_from_storefront)
        assert "cart_id" in sig.parameters, (
            "submit_order_from_storefront missing cart_id parameter. "
            "INV-CART-5 violato — Step 5 cart-order integration non funziona."
        )
        param = sig.parameters["cart_id"]
        # Keyword-only (dopo *)
        assert param.kind == inspect.Parameter.KEYWORD_ONLY
        # Has default (Optional, default None)
        assert param.default is None

    def test_cart_id_default_none(self):
        """Default None preserva comportamento esistente (callers pre-Step 5)."""
        from services.order_creation_service import submit_order_from_storefront
        sig = inspect.signature(submit_order_from_storefront)
        assert sig.parameters["cart_id"].default is None, (
            "cart_id non ha default None. Callers esistenti (router pre-Step 5) "
            "si romperebbero perché non lo passerebbero."
        )


# ─── INV-CART-6 — Cart conversion is soft-fail ──────────────────────────


class TestINV_CART_6_SoftFailConversion:
    """Cart mark_converted failure NON blocca order creation."""

    def test_service_uses_try_except_around_conversion(self):
        """Il blocco di cart conversion è in try/except per soft-fail."""
        from services import order_creation_service
        source = inspect.getsource(order_creation_service.submit_order_from_storefront)
        # Cerca il pattern: cart conversion dentro try/except
        # Marker: mark_converted_to_order chiamato + except Exception nearby
        assert "mark_converted_to_order" in source, (
            "submit_order_from_storefront non chiama cart_repository."
            "mark_converted_to_order. INV-CART-6 incompleto."
        )
        # Conta i try/except (per assicurarsi che il chiamata sia in uno)
        # La chiamata mark_converted dovrebbe essere preceduta da "try:"
        idx_mark = source.find("mark_converted_to_order")
        assert idx_mark > 0
        # Cerchiamo "try:" entro 200 caratteri prima
        context_before = source[max(0, idx_mark - 200):idx_mark]
        assert "try:" in context_before, (
            "mark_converted_to_order non è in un try/except. INV-CART-6 "
            "violato — failure del mark blocherebbe il return dell'order."
        )

    def test_service_returns_cart_converted_field(self):
        """Service result include 'cart_converted' boolean per il router."""
        from services import order_creation_service
        source = inspect.getsource(order_creation_service.submit_order_from_storefront)
        assert '"cart_converted"' in source, (
            "Service non ritorna cart_converted nel result. Router non sa "
            "se deve clear il cookie."
        )

    def test_service_skips_conversion_if_no_cart_id(self):
        """Se cart_id is None, conversion logic è skippata."""
        from services import order_creation_service
        source = inspect.getsource(order_creation_service.submit_order_from_storefront)
        # Marker: il blocco conversion è gated da `if cart_id`
        assert "if cart_id" in source, (
            "Service non ha gate `if cart_id` prima del mark_converted. "
            "Calls senza cart_id triggererebbero comunque la conversion logic."
        )


# ─── INV-CART-7 — Router extracts cart_id from cookie ───────────────────


class TestINV_CART_7_RouterExtractsCookie:
    """Router public.py legge cookie afianco_cart_id e passa al service."""

    def test_router_reads_afianco_cart_id_cookie(self):
        from routers import public
        source = inspect.getsource(public.submit_order_request)
        # Marker: legge cookie via request.cookies.get("afianco_cart_id")
        assert "afianco_cart_id" in source, (
            "Router non legge il cookie afianco_cart_id. Cart→order linking "
            "non funziona — cookie viene scartato silenziosamente."
        )
        assert "request.cookies.get" in source, (
            "Router non usa request.cookies.get per leggere il cookie. "
            "Pattern di lettura cookie non canonical."
        )

    def test_router_passes_cart_id_to_service(self):
        from routers import public
        source = inspect.getsource(public.submit_order_request)
        # cart_id deve apparire come argument della call al service
        # (es. cart_id=cart_id_cookie)
        assert "cart_id=" in source, (
            "Router non passa cart_id=... al service. Service riceve "
            "None sempre — Step 5 effettivamente disabilitato."
        )

    def test_router_has_response_parameter(self):
        """Router accetta Response per poter chiamare delete_cookie."""
        from routers import public
        sig = inspect.signature(public.submit_order_request)
        assert "response" in sig.parameters, (
            "Router non accetta Response param. Non può clear il cart cookie "
            "post-checkout. INV-CART-8 violato."
        )


# ─── INV-CART-8 — Router clears cookie post-conversion ──────────────────


class TestINV_CART_8_RouterClearsCookie:
    """Router clear afianco_cart_id cookie dopo conversion success."""

    def test_router_calls_clear_cart_cookie(self):
        from routers import public
        source = inspect.getsource(public.submit_order_request)
        assert "clear_cart_cookie" in source, (
            "Router non chiama clear_cart_cookie post-checkout. Customer "
            "rimane con cookie afianco_cart_id stale → il prossimo visit "
            "ricarica un cart già converted."
        )

    def test_router_clear_is_conditional_on_cart_converted(self):
        """Clear cookie SOLO se cart_converted=True."""
        from routers import public
        source = inspect.getsource(public.submit_order_request)
        # Marker: clear è dentro un branch che check cart_converted
        idx_clear = source.find("clear_cart_cookie")
        assert idx_clear > 0
        context_before = source[max(0, idx_clear - 300):idx_clear]
        assert "cart_converted" in context_before, (
            "clear_cart_cookie chiamato senza check 'cart_converted'. "
            "Se l'order failed, il cookie verrebbe clearato comunque — "
            "il customer perderebbe il cart in flight."
        )


# ─── Repository contract for cart-order linking ─────────────────────────


class TestCartRepositoryMarkConverted:
    """cart_repository.mark_converted_to_order signature contract."""

    def test_mark_converted_function_exists(self):
        from repositories.cart_repository import mark_converted_to_order
        assert inspect.iscoroutinefunction(mark_converted_to_order)

    def test_mark_converted_signature(self):
        from repositories.cart_repository import mark_converted_to_order
        sig = inspect.signature(mark_converted_to_order)
        params = sig.parameters
        # Required: cart_id, organization_id, order_id
        assert "cart_id" in params
        assert "organization_id" in params, (
            "mark_converted_to_order missing organization_id — INV-CART-2 "
            "multi-tenant isolation violato."
        )
        assert "order_id" in params, (
            "mark_converted_to_order missing order_id — non potrebbe linkare "
            "cart → order."
        )

    def test_mark_converted_filters_on_organization_id(self):
        """Implementation filtra su (cart_id, organization_id) per INV-CART-2."""
        from repositories import cart_repository
        source = inspect.getsource(cart_repository.mark_converted_to_order)
        assert '"organization_id":' in source, (
            "mark_converted_to_order non filtra su organization_id. "
            "Cart di org diversa potrebbe essere accidentalmente marcato."
        )
        assert "$set" in source and "converted_to_order_id" in source, (
            "mark_converted_to_order non setta $set converted_to_order_id."
        )
