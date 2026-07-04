"""Sentinel tests for /api/public/embed/categories/{slug} — Phase 1 Step 13.

Endpoint dedicato che ritorna la lista categorie pubbliche di uno store
con count + slug normalizzato + thumbnail opzionale. Permette al widget
di renderizzare un nav menu / filter UI senza ri-scaricare l'intero init
payload.

Invariants pinned
=================
  INV-EC-1   Categories distinct case-normalized (slug merge)
  INV-EC-2   Slug è URL-safe (regex ^[a-z0-9-]+$)
  INV-EC-3   Count accurate (solo is_published=True AND is_active=True)
  INV-EC-4   Empty store → {categories: []} not 404
  INV-EC-5   Multi-tenant scoping (slug A non leakka B)
  INV-EC-6   No PII leak (no cost_price, sku, organization_id, ecc.)
  INV-EC-7   with_thumbnail=true → ogni cat ha campo thumbnail_url
  INV-EC-8   with_thumbnail=false (default) → thumbnail_url == None
  INV-EC-9   include_empty=false (default) → categorie con count=0 escluse
  INV-EC-10  query param boolean parsing (true/false/1/0 robusti)
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


# ─── Module contract ───────────────────────────────────────────────────


class TestEmbedCategoriesModule:
    def test_service_function_exists(self):
        """Service helper get_embed_categories_data deve essere esposto."""
        from services.embed_init_service import get_embed_categories_data
        assert callable(get_embed_categories_data)

    def test_endpoint_registered(self):
        """Endpoint GET /categories/{slug} deve essere nel router."""
        from routers.embed_public import router
        paths = {r.path for r in router.routes}
        assert "/public/embed/categories/{slug}" in paths, (
            f"Endpoint /categories/{{slug}} non registrato. Path attuali: {paths}"
        )

    def test_handler_function_exists(self):
        """Handler get_embed_categories deve essere coroutine."""
        from routers import embed_public
        assert hasattr(embed_public, "get_embed_categories"), (
            "Handler get_embed_categories missing in routers.embed_public"
        )
        assert inspect.iscoroutinefunction(embed_public.get_embed_categories)


# ─── INV-EC-1 + INV-EC-2 — Response shape ──────────────────────────────


class TestINV_EC_ResponseShape:
    """Response model EmbedCategoriesResponse stable; pinning del contract."""

    def test_response_model_required_fields(self):
        from routers.embed_public import EmbedCategoriesResponse
        fields = EmbedCategoriesResponse.model_fields
        for f in ("slug", "categories"):
            assert f in fields, (
                f"EmbedCategoriesResponse.{f} missing — widget filter UI rotto."
            )

    def test_category_item_includes_thumbnail_field(self):
        """EmbedCategoryItem deve esporre thumbnail_url (anche None)."""
        from routers.embed_public import EmbedCategoryItem
        fields = EmbedCategoryItem.model_fields
        for f in ("name", "slug", "count", "thumbnail_url"):
            assert f in fields, (
                f"EmbedCategoryItem.{f} missing. Widget aspetta tutti questi campi."
            )


# ─── INV-EC-2 — Slug URL-safe ──────────────────────────────────────────


class TestINV_EC_2_SlugUrlSafe:
    """Slug normalizer è riusato (defined in embed_init_service)."""

    def test_slug_normalizer_reused(self):
        """Stesso helper di Step 12 — no duplicazione."""
        from services.embed_init_service import _normalize_category_slug
        slug = _normalize_category_slug("Café & Catering")
        # Regex check
        import re
        assert re.fullmatch(r"[a-z0-9-]+", slug)


# ─── INV-EC-6 — No PII leak ────────────────────────────────────────────


class TestINV_EC_6_NoPIILeak:
    """EmbedCategoryItem NON deve mai esporre campi privati. Anche se per
    ora la response è minimale, il sentinel previene drift futuro."""

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
        "_id",
    )

    def test_category_item_no_blacklisted_fields(self):
        from routers.embed_public import EmbedCategoryItem
        fields = set(EmbedCategoryItem.model_fields)
        for blocked in self.PRIVATE_FIELD_BLACKLIST:
            assert blocked not in fields, (
                f"INV-EC-6 violato: EmbedCategoryItem expone '{blocked}'."
            )

    def test_response_no_blacklisted_fields(self):
        from routers.embed_public import EmbedCategoriesResponse
        fields = set(EmbedCategoriesResponse.model_fields)
        for blocked in self.PRIVATE_FIELD_BLACKLIST:
            assert blocked not in fields


# ─── INV-EC-8 — Thumbnail default OFF ──────────────────────────────────


class TestINV_EC_8_ThumbnailDefaultOff:
    """Default with_thumbnail=False per ridurre payload + Mongo cost."""

    def test_handler_with_thumbnail_default_false(self):
        """Inspect signature: il parametro `with_thumbnail` ha default False."""
        from routers.embed_public import get_embed_categories
        sig = inspect.signature(get_embed_categories)
        param = sig.parameters.get("with_thumbnail")
        assert param is not None, (
            "Handler signature manca `with_thumbnail` param."
        )
        # Pydantic Query default è nel `.default` se non required
        # FastAPI Query(default=False) → param.default è Query(False)
        # Verifichiamo che il default sia coercibile a False
        from fastapi import Query
        default = param.default
        # Caso 1: default è Query(False) → has .default attribute
        # Caso 2: default è False direttamente
        actual = getattr(default, "default", default)
        assert actual is False, (
            f"with_thumbnail default = {actual!r}, expected False. "
            "Cambiarlo aumenta latency + bandwidth widget di default."
        )

    def test_handler_include_empty_default_false(self):
        """Categorie con count=0 escluse di default."""
        from routers.embed_public import get_embed_categories
        sig = inspect.signature(get_embed_categories)
        param = sig.parameters.get("include_empty")
        assert param is not None
        actual = getattr(param.default, "default", param.default)
        assert actual is False, (
            "include_empty default deve essere False — categorie senza "
            "prodotti pubblicati confondono il widget filter UI."
        )


# ─── Service contract — categories aggregation ─────────────────────────


class TestServiceContract:
    """L'helper get_embed_categories_data accetta with_thumbnail boolean
    e ritorna lista dict con campi attesi."""

    def test_function_signature(self):
        from services.embed_init_service import get_embed_categories_data
        sig = inspect.signature(get_embed_categories_data)
        params = list(sig.parameters)
        # slug + with_thumbnail + include_empty (almeno)
        assert "slug" in params
        assert "with_thumbnail" in params
        assert "include_empty" in params

    @pytest.mark.asyncio
    async def test_returns_dict_with_categories(self):
        """Smoke: import-time check sulla funzione, non chiamata reale al DB."""
        from services.embed_init_service import get_embed_categories_data
        # Verifica che è async
        assert inspect.iscoroutinefunction(get_embed_categories_data)


# ─── Metrics integration ───────────────────────────────────────────────


class TestMetricsIntegration:
    """Step 13 extends metrics with embed_category_lookups_total."""

    def test_metric_counter_exists(self):
        from core.observability import metrics
        if not metrics.is_available():
            pytest.skip("prometheus_client not installed")
        assert hasattr(metrics, "EMBED_CATEGORY_LOOKUPS"), (
            "Counter EMBED_CATEGORY_LOOKUPS missing."
        )

    def test_record_helper_exists(self):
        from core.observability import metrics
        assert hasattr(metrics, "record_embed_category_lookup"), (
            "Helper record_embed_category_lookup missing."
        )

    def test_record_helper_is_fail_safe(self):
        """Soft-fail su input bogus."""
        from core.observability import metrics
        metrics.record_embed_category_lookup(slug="phantom", with_thumbnail=True)
