"""Sentinel tests for the persistent server-side Cart (Phase 0 Step 4).

Pin del contract Cart model + repository + service + endpoints. Garantisce
che future surface (embed widget Stream A, AI site Stream B) trovino il
cart sempre coerente con gli invarianti dichiarati.

Invarianti pinned
=================
  INV-CART-1  Atomic operations via find_one_and_update
  INV-CART-2  Multi-tenant isolation (organization_id obbligatorio)
  INV-CART-3  expires_at sempre nel futuro per cart attivi (TTL 60gg)
  INV-CART-4  CartItem shape compatibile con OrderRequestItem
  CTR-CART-1  CartResponse shape stabile (7+ campi obbligatori)
"""

import inspect
import os
import sys
from datetime import datetime, timedelta, timezone
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


# ─── Cart model contract ────────────────────────────────────────────────


class TestCartModelShape:
    """Cart Pydantic model contract — adding/removing fields = breaking change."""

    def test_cart_model_importable(self):
        from models.cart import Cart, CartItem, CART_TTL_DAYS
        assert CART_TTL_DAYS == 60, (
            "CART_TTL_DAYS != 60. Cambio del TTL impatta cookie max-age + "
            "abandon recovery window — verifica system-invariants.md prima."
        )

    def test_cart_required_fields(self):
        """Required scalar fields on Cart."""
        from models.cart import Cart
        fields = Cart.model_fields
        required = {"organization_id"}
        for f in required:
            assert f in fields, f"Cart model missing required field: {f}"

    def test_cart_has_canonical_optional_fields(self):
        """Cart model exposes the canonical optional fields."""
        from models.cart import Cart
        fields = Cart.model_fields
        expected = {
            "id", "store_id", "customer_id", "customer_email",
            "customer_account_id", "items", "source", "metadata",
            "created_at", "updated_at", "expires_at",
            "recovered_at", "converted_to_order_id",
        }
        for f in expected:
            assert f in fields, f"Cart missing canonical field: {f}"

    def test_cart_id_has_canonical_prefix(self):
        """Cart id default uses cart_ prefix per debugging readability."""
        from models.cart import Cart
        instance = Cart(organization_id="org-x")
        assert instance.id.startswith("cart_"), (
            f"Cart.id default doesn't have 'cart_' prefix: {instance.id}. "
            "Naming convention helps debugging (sees 'cart_xxx' vs 'ord_xxx' in logs)."
        )

    def test_cart_default_expires_at_60_days(self):
        """INV-CART-3: default expires_at is now + CART_TTL_DAYS."""
        from models.cart import Cart, CART_TTL_DAYS
        from datetime import datetime, timezone
        instance = Cart(organization_id="org-x")
        delta_days = (instance.expires_at - datetime.now(timezone.utc)).days
        # Permette 1 giorno di tolleranza per timing
        assert CART_TTL_DAYS - 1 <= delta_days <= CART_TTL_DAYS + 1, (
            f"Default expires_at delta = {delta_days} days, expected ~{CART_TTL_DAYS}. "
            "INV-CART-3 violato."
        )


class TestCartItemMatchesOrderRequestItem:
    """INV-CART-4: CartItem shape compatibile con OrderRequestItem.

    Permette conversione zero-loss durante checkout. Aggiungere campi
    a OrderRequestItem senza aggiornare CartItem rompe il flow.
    """

    def test_cart_item_has_all_order_request_item_fields(self):
        """Tutti i campi critici di OrderRequestItem esistono in CartItem."""
        from models.cart import CartItem
        from routers.public import OrderRequestItem

        cart_fields = set(CartItem.model_fields.keys())
        order_fields = set(OrderRequestItem.model_fields.keys())

        # Campi che DEVONO essere in CartItem per supportare i 7 product type
        critical_fields = {
            "product_id", "quantity",
            "occurrence_id", "ticket_tier_id",
            "rental_date_from", "rental_date_to", "rental_notes",
            "booking_date", "booking_start_time", "booking_end_time", "booking_end_date",
            "attendees", "service_option_id",
        }

        missing = critical_fields - cart_fields
        assert not missing, (
            f"CartItem missing critical fields from OrderRequestItem: {missing}. "
            "INV-CART-4 violato — checkout conversion perderebbe questi campi."
        )

    def test_cart_item_has_display_snapshot_fields(self):
        """CartItem cached snapshot per UI display (non in OrderRequestItem)."""
        from models.cart import CartItem
        fields = CartItem.model_fields
        snapshot_fields = {
            "product_name_snapshot",
            "unit_price_snapshot",
            "currency_snapshot",
        }
        for f in snapshot_fields:
            assert f in fields, (
                f"CartItem missing display snapshot: {f}. Frontend dovrebbe "
                "fetchare product per ogni cart read — performance regression."
            )


# ─── CartResponse contract ──────────────────────────────────────────────


class TestCTR_CART_1_CartResponseShape:
    """CTR-CART-1: CartResponse shape stabile.

    Consumato da storefront classic frontend + future embed SDK + AI sites.
    """

    def test_cart_response_required_fields(self):
        from models.cart import CartResponse
        fields = CartResponse.model_fields
        required = {
            "id", "organization_id", "items",
            "item_count", "subtotal_snapshot",
            "created_at", "updated_at", "expires_at",
            "source",
        }
        for f in required:
            assert f in fields, f"CartResponse missing required field: {f}"

    def test_cart_response_includes_derived_fields(self):
        """Derived: item_count + subtotal_snapshot calcolati server-side."""
        from models.cart import CartResponse
        from services import cart_service

        # Mock-cart con 3 items
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        cart_doc = {
            "id": "cart_test_1",
            "organization_id": "org-x",
            "store_id": None,
            "items": [
                {"product_id": "p1", "quantity": 2, "unit_price_snapshot": 10.0, "currency_snapshot": "EUR"},
                {"product_id": "p2", "quantity": 1, "unit_price_snapshot": 25.0, "currency_snapshot": "EUR"},
            ],
            "customer_email": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "expires_at": now.isoformat(),
            "source": "storefront_classic",
        }
        resp = cart_service.build_response(cart_doc)
        assert resp.item_count == 3, "item_count derivation incorrect"
        assert resp.subtotal_snapshot == 45.0, "subtotal_snapshot derivation incorrect"
        assert resp.currency_snapshot == "EUR"


# ─── Repository contract (INV-CART-1 + INV-CART-2) ──────────────────────


class TestINV_CART_1_AtomicOperations:
    """INV-CART-1: tutte le mutation usano find_one_and_update (atomic)."""

    def test_repository_uses_find_one_and_update_for_mutations(self):
        """update_items, update_customer_binding, clear_items usano l'atomic API."""
        from repositories import cart_repository
        source = inspect.getsource(cart_repository)
        assert "find_one_and_update" in source, (
            "cart_repository non usa find_one_and_update. INV-CART-1 violato — "
            "concurrent updates su stesso cart_id race su read-then-write."
        )
        # Specifically: ReturnDocument.AFTER per leggere il doc post-mutation
        assert "ReturnDocument" in source, (
            "cart_repository non usa pymongo.ReturnDocument. Callers ricevono "
            "il doc pre-mutation invece di post-mutation."
        )

    def test_repository_update_items_is_async(self):
        from repositories.cart_repository import update_items
        assert inspect.iscoroutinefunction(update_items)

    def test_repository_find_by_id_is_async(self):
        from repositories.cart_repository import find_by_id
        assert inspect.iscoroutinefunction(find_by_id)


class TestINV_CART_2_MultiTenantIsolation:
    """INV-CART-2: ogni query repository filtra su (id, organization_id).

    Senza, un cart_id rubato potrebbe leggere/modificare cart di altre org.
    """

    def test_find_by_id_requires_organization_id(self):
        """Signature di find_by_id richiede organization_id obbligatorio."""
        from repositories.cart_repository import find_by_id
        sig = inspect.signature(find_by_id)
        assert "organization_id" in sig.parameters, (
            "find_by_id senza organization_id parameter. INV-CART-2 violato — "
            "cart_id potrebbe fetchare cart di org diverse."
        )

    def test_update_items_requires_organization_id(self):
        from repositories.cart_repository import update_items
        sig = inspect.signature(update_items)
        assert "organization_id" in sig.parameters

    def test_delete_by_id_requires_organization_id(self):
        from repositories.cart_repository import delete_by_id
        sig = inspect.signature(delete_by_id)
        assert "organization_id" in sig.parameters

    def test_repository_source_filters_on_organization_id(self):
        """Source check: ogni Mongo query filtra esplicitamente su organization_id."""
        from repositories import cart_repository
        source = inspect.getsource(cart_repository)
        # Marker: l'occorrenza "organization_id" dovrebbe apparire in ogni filtro
        org_filter_count = source.count('"organization_id":')
        assert org_filter_count >= 5, (
            f"Solo {org_filter_count} riferimenti 'organization_id' nei filtri. "
            "Atteso >= 5 (find, update_items, update_binding, clear, delete). "
            "INV-CART-2 violato."
        )


class TestINV_CART_3_ExpiresAtMaintenance:
    """INV-CART-3: expires_at sempre nel futuro per cart attivi."""

    def test_update_items_refreshes_expires_at(self):
        """Ogni mutation di items bumpa expires_at a +60gg."""
        from repositories import cart_repository
        source = inspect.getsource(cart_repository.update_items)
        assert "expires_at" in source, (
            "update_items non bumpa expires_at. Cart attivamente usato "
            "rischia di scadere mid-shopping."
        )
        assert "_new_expires_at" in source or "timedelta" in source, (
            "expires_at update non usa la helper canonical +60gg."
        )

    def test_update_customer_binding_refreshes_expires_at(self):
        """Ogni mutation di customer binding bumpa expires_at."""
        from repositories import cart_repository
        source = inspect.getsource(cart_repository.update_customer_binding)
        assert "expires_at" in source, (
            "update_customer_binding non refresha expires_at."
        )


# ─── Service contract ───────────────────────────────────────────────────


class TestCartService:
    """Cart service orchestration layer."""

    def test_persistent_cart_feature_flag_default_off(self):
        """Default OFF per gradual rollout post-Step 4b."""
        from services.cart_service import persistent_cart_enabled
        original = os.environ.pop("PERSISTENT_CART_ENABLED", None)
        try:
            assert persistent_cart_enabled() is False, (
                "PERSISTENT_CART_ENABLED default deve essere OFF. Frontend "
                "dual-write logic (Step 4b) richiede stabilization prima di "
                "abilitare il path server-side."
            )
        finally:
            if original is not None:
                os.environ["PERSISTENT_CART_ENABLED"] = original

    @pytest.mark.parametrize("value,expected", [
        ("true", True), ("TRUE", True), ("1", True), ("yes", True), ("on", True),
        ("false", False), ("0", False), ("", False), ("garbage", False),
    ])
    def test_feature_flag_env_parsing(self, value, expected):
        from services.cart_service import persistent_cart_enabled
        original = os.environ.pop("PERSISTENT_CART_ENABLED", None)
        try:
            os.environ["PERSISTENT_CART_ENABLED"] = value
            assert persistent_cart_enabled() == expected
        finally:
            if original is not None:
                os.environ["PERSISTENT_CART_ENABLED"] = original
            else:
                os.environ.pop("PERSISTENT_CART_ENABLED", None)

    def test_cart_cookie_constants(self):
        """Cookie configuration is the contract for frontend dual-write."""
        from services.cart_service import (
            CART_COOKIE_NAME,
            CART_COOKIE_MAX_AGE_SECONDS,
            set_cart_cookie,
            clear_cart_cookie,
        )
        assert CART_COOKIE_NAME == "aurya_cart_id", (   # R1 rebrand 11/7
            "cookie rinominato col rebrand Aurya"
        )
        # migrazione dolce: il nome legacy resta LEGGIBILE finche' i
        # carrelli pre-rebrand sono vivi (TTL 60gg)
        from services.cart_service import LEGACY_CART_COOKIE_NAME
        assert LEGACY_CART_COOKIE_NAME == "afianco_cart_id"
        _dummy = (
            "Cookie name changed — frontend dual-write logic (Step 4b) "
            "rompe. Update both atomically."
        )
        # 60 giorni in secondi
        assert CART_COOKIE_MAX_AGE_SECONDS == 60 * 24 * 60 * 60

    def test_set_cart_cookie_uses_httponly_samesite(self):
        """Cookie security: HttpOnly + SameSite=Lax."""
        from services import cart_service
        source = inspect.getsource(cart_service.set_cart_cookie)
        assert "httponly=True" in source, (
            "set_cart_cookie non setta HttpOnly. XSS hijack del cart_id possibile."
        )
        assert 'samesite="lax"' in source or "samesite='lax'" in source, (
            "set_cart_cookie non setta SameSite=Lax. CSRF su cart operations."
        )


# ─── Endpoint registration ──────────────────────────────────────────────


class TestCartEndpointsRegistered:
    """5 endpoint /api/public/cart/* registered su public router."""

    def test_all_5_cart_endpoints_registered(self):
        from routers.public import router
        cart_paths = [r.path for r in router.routes if "/cart" in r.path]
        expected_count = 5
        assert len(cart_paths) >= expected_count, (
            f"Solo {len(cart_paths)} cart endpoints registered, atteso >= {expected_count}. "
            f"Found: {cart_paths}"
        )

    def test_cart_endpoints_methods(self):
        """Verifica HTTP methods canonical per cart endpoints."""
        from routers.public import router
        cart_routes = [r for r in router.routes if "/cart" in r.path]
        methods_seen = set()
        for r in cart_routes:
            methods_seen.update(getattr(r, "methods", []) or [])
        # Atteso: POST (create + merge), GET, PATCH, DELETE
        expected_methods = {"POST", "GET", "PATCH", "DELETE"}
        for m in expected_methods:
            assert m in methods_seen, f"Cart endpoints missing method: {m}"


class TestCartEndpointSecurity:
    """Cart endpoints sono protetti da rate limiting + multi-tenant scoping."""

    def test_cart_endpoints_rate_limited(self):
        """Tutti i cart endpoints hanno @limiter.limit decoration."""
        from routers import public
        source = inspect.getsource(public)
        # Cerchiamo "/cart" + "@limiter.limit" in vicinanza
        # Conta i rate limit decorator dopo lo header "Phase 0 Step 4"
        idx_step4 = source.find("Phase 0 Step 4")
        assert idx_step4 > 0, "Phase 0 Step 4 cart endpoints section not found"
        cart_section = source[idx_step4:]
        limiter_count = cart_section.count("@limiter.limit")
        # 5 endpoints (POST cart, GET, PATCH, POST merge, DELETE)
        assert limiter_count >= 5, (
            f"Solo {limiter_count} @limiter.limit nel cart section. "
            "Atteso >= 5 (uno per endpoint). Rate limiting incompleto."
        )

    def test_cart_merge_requires_bearer_token(self):
        """POST /cart/{id}/merge verifica Bearer token customer."""
        from routers import public
        source = inspect.getsource(public.merge_cart_to_account)
        assert "authorization" in source.lower(), (
            "merge_cart_to_account non check Bearer token. Anonymous cart "
            "claim potrebbe essere fatta da chiunque."
        )
        assert "customer" in source.lower(), (
            "merge_cart_to_account non valida che il token sia di tipo customer."
        )

    def test_cart_endpoints_use_resolve_org(self):
        """Endpoints risolvono org via _resolve_org per multi-tenant scoping."""
        from routers import public
        # Per ogni handler, check che chiami _resolve_org
        handlers = [
            "create_cart", "get_cart_by_id", "update_cart",
            "merge_cart_to_account", "clear_or_delete_cart",
        ]
        for handler_name in handlers:
            handler = getattr(public, handler_name)
            source = inspect.getsource(handler)
            assert "_resolve_org" in source, (
                f"{handler_name} non chiama _resolve_org. INV-CART-2 violato — "
                "endpoint non risolve organization_id dal slug."
            )
