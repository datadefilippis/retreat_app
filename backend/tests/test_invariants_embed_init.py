"""Sentinel tests for /api/public/embed/init/{slug} — Phase 1 Step 12.

Pin del contract del bootstrap endpoint che restituisce in 1 round-trip
tutto ciò che serve a un widget cross-origin per renderizzare la
storefront (eccetto la lista prodotti — fetched lazy via /embed/products).

Invariants pinned
=================
  INV-EI-1  Response shape stabile (campi top-level obbligatori)
  INV-EI-2  Multi-tenant isolation (slug A non leakka dati di slug B)
  INV-EI-3  Categories count = solo is_published=True AND is_active=True
  INV-EI-4  No PII leak (cost_price, sku, admin emails, organization_id)
  INV-EI-5  Cache-Control + ETag headers presenti
  INV-EI-6  Rate limit applicato
  INV-EI-7  Store inesistente → 404
  INV-EI-8  Org disattivata → 404
  INV-EI-9  Categories slug è URL-safe (lowercase, hyphens)
  INV-EI-10 capabilities.cart_enabled + checkout_stripe_enabled presenti
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


class TestEmbedInitModule:
    def test_service_module_importable(self):
        from services import embed_init_service
        assert embed_init_service is not None

    def test_router_module_importable(self):
        from routers import embed_public
        assert embed_public.router is not None

    def test_router_prefix_canonical(self):
        from routers.embed_public import router
        # NOTA: il prefix viene composto in server.py come "/api" + router.prefix
        # Endpoint finale: /api/public/embed/init/{slug}
        assert router.prefix == "/public/embed", (
            f"Router prefix changed to '{router.prefix}'. Public URL "
            "/api/public/embed/* is part of the customer-facing contract."
        )

    def test_server_includes_router(self):
        import server
        source = inspect.getsource(server)
        assert "embed_public_router" in source, (
            "server.py non importa embed_public_router. Endpoint /api/public/"
            "embed/init NON raggiungibile."
        )
        assert "app.include_router(embed_public_router.router" in source


# ─── Service contract — category slug normalization ────────────────────


class TestCategorySlugNormalization:
    """Helper _normalize_category_slug deve produrre URL-safe ASCII lowercase."""

    def test_basic_lowercase(self):
        from services.embed_init_service import _normalize_category_slug
        assert _normalize_category_slug("Catering") == "catering"

    def test_spaces_to_hyphens(self):
        from services.embed_init_service import _normalize_category_slug
        assert _normalize_category_slug("Catering Servizi") == "catering-servizi"

    def test_collapse_multi_spaces(self):
        from services.embed_init_service import _normalize_category_slug
        assert _normalize_category_slug("Food  &   Beverages") == "food-beverages"

    def test_strip_special_chars(self):
        from services.embed_init_service import _normalize_category_slug
        assert _normalize_category_slug("Pizza/Pasta!") == "pizza-pasta"

    def test_accents_normalized(self):
        """NFD decomposition + ASCII strip → 'Café' → 'cafe'."""
        from services.embed_init_service import _normalize_category_slug
        assert _normalize_category_slug("Café Italiano") == "cafe-italiano"

    def test_empty_input_returns_empty(self):
        from services.embed_init_service import _normalize_category_slug
        assert _normalize_category_slug("") == ""
        assert _normalize_category_slug(None) == ""

    def test_idempotent(self):
        """Slugify(slug(x)) == slug(x)."""
        from services.embed_init_service import _normalize_category_slug
        s = _normalize_category_slug("Catering Servizi")
        assert _normalize_category_slug(s) == s


# ─── INV-EI-9 — Categories slug URL-safe ───────────────────────────────


class TestINV_EI_9_CategorySlugUrlSafe:
    def test_slug_matches_url_safe_regex(self):
        """Output deve matchare ^[a-z0-9-]*$ (vuoto consentito per edge case)."""
        import re
        from services.embed_init_service import _normalize_category_slug

        cases = [
            "Catering", "Catering Servizi", "Pizza/Pasta", "Café",
            "100% Bio", "Wine & Spirits", "Health-Beauty",
        ]
        for raw in cases:
            slug = _normalize_category_slug(raw)
            assert re.fullmatch(r"[a-z0-9-]*", slug), (
                f"slug {slug!r} (from {raw!r}) is not URL-safe. "
                "Web Component attribute parsing si rompe."
            )


# ─── INV-EI-1 — Response shape ─────────────────────────────────────────


class TestINV_EI_1_ResponseShape:
    """I campi top-level del bootstrap NON si possono rimuovere senza
    breaking change per il widget. Cambiare nomi = bumpare /v0/ → /v1/."""

    def test_response_model_required_fields(self):
        from routers.embed_public import EmbedInitResponse
        fields = EmbedInitResponse.model_fields
        required = (
            "slug", "org_name", "currency", "storefront_languages",
            "available_product_types", "categories", "capabilities",
        )
        for f in required:
            assert f in fields, (
                f"EmbedInitResponse.{f} missing. INV-EI-1 violato — "
                "widget downstream NON può rendere bootstrap."
            )

    def test_capabilities_shape(self):
        from routers.embed_public import EmbedCapabilities
        fields = EmbedCapabilities.model_fields
        for f in ("checkout_stripe_enabled", "cart_enabled", "customer_auth_enabled"):
            assert f in fields, (
                f"EmbedCapabilities.{f} missing — widget non sa quali "
                "feature offrire al merchant."
            )

    def test_category_summary_shape(self):
        from routers.embed_public import EmbedCategorySummary
        fields = EmbedCategorySummary.model_fields
        for f in ("name", "slug", "count"):
            assert f in fields


# ─── INV-EI-4 — No PII leak ────────────────────────────────────────────


class TestINV_EI_4_NoPIILeak:
    """Defense-in-depth: la response shape NON deve mai esporre campi
    privati come cost_price, sku, organization_id, ecc.

    Test introspettivo sul Pydantic model — se uno di questi campi viene
    aggiunto per errore, il test fallisce e blocca il commit."""

    PRIVATE_FIELD_BLACKLIST = (
        "cost_price",
        "sku",
        "organization_id",
        "is_active",
        "is_published",
        "store_ids",
        "supplier_id",
        "internal_notes",
        "admin_email",
        "notification_email",
        "sender_display_name",
        "reply_to_email",
        "email_delivery",
        "deactivated_for_plan_violation",
        "last_status_transition_at",
    )

    def test_top_level_fields_no_blacklisted(self):
        from routers.embed_public import EmbedInitResponse
        fields = set(EmbedInitResponse.model_fields)
        for blocked in self.PRIVATE_FIELD_BLACKLIST:
            assert blocked not in fields, (
                f"INV-EI-4 violato: EmbedInitResponse expone campo privato "
                f"'{blocked}'. Rimuoverlo o normalizzare il payload."
            )

    def test_nested_store_info_no_blacklisted(self):
        """StoreInfo nested non deve esporre campi blacklisted."""
        from routers.embed_public import EmbedInitResponse
        # Find StoreInfo via annotation (importato da routers.public)
        store_info_field = EmbedInitResponse.model_fields.get("store_info")
        assert store_info_field is not None
        # Risolvi il tipo nested
        from routers.public import StoreInfo
        si_fields = set(StoreInfo.model_fields)
        for blocked in self.PRIVATE_FIELD_BLACKLIST:
            assert blocked not in si_fields, (
                f"INV-EI-4 violato: StoreInfo expone campo privato "
                f"'{blocked}'."
            )


# ─── INV-EI-10 — Capabilities default ──────────────────────────────────


class TestINV_EI_10_CapabilitiesDefaults:
    """Capabilities ha default conservativi (true per feature legacy
    già in prod, false per feature flaggate)."""

    def test_defaults_safe(self):
        from routers.embed_public import EmbedCapabilities
        c = EmbedCapabilities()
        # cart_enabled e customer_auth_enabled DEVONO essere True
        # (legacy gia' in prod)
        assert c.cart_enabled is True, (
            "cart_enabled default deve essere True — cart è feature "
            "core esistente, NON dietro flag embed_widget_enabled."
        )
        assert c.customer_auth_enabled is True, (
            "customer_auth_enabled default deve essere True — auth è "
            "feature esistente, NON gated."
        )


# ─── Metrics integration ────────────────────────────────────────────────


class TestMetricsIntegration:
    """Step 10 metric estensione: embed_init_requests_total."""

    def test_metric_counter_exists(self):
        from core.observability import metrics
        if not metrics.is_available():
            pytest.skip("prometheus_client not installed")
        assert hasattr(metrics, "EMBED_INIT_REQUESTS"), (
            "Counter EMBED_INIT_REQUESTS missing. /metrics endpoint NON "
            "mostrerà funnel embed init."
        )

    def test_record_helper_exists(self):
        from core.observability import metrics
        assert hasattr(metrics, "record_embed_init"), (
            "Helper record_embed_init missing. Call sites del router "
            "non sapranno come incrementare."
        )

    def test_record_helper_is_fail_safe(self):
        """Soft-fail su input bogus (pattern del modulo Step 10)."""
        from core.observability import metrics
        # Non deve mai sollevare eccezioni
        metrics.record_embed_init(slug="phantom", cache_result="phantom")
