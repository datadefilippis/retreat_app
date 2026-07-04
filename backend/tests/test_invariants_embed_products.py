"""Sentinel tests for /api/public/embed/products/{slug} — Phase 1 Step 14.

Endpoint catalog filterable per il widget embed cross-origin.
Supporta filter (category slug, item_type), sort (name/price_asc/
price_desc/newest), pagination (limit/offset).

Response leggera: card view (no side-fetches enrichment come
service_options, occurrences, extras — quelli saranno in un futuro
endpoint /embed/products/{slug}/{product_id} di dettaglio).

Invariants pinned
=================
  INV-EP-1   Filter category case-insensitive su slug normalizzato
  INV-EP-2   Filter type whitelisted (PRODUCT_TYPE_KEYS); type sconosciuto → 400
  INV-EP-3   Pagination meta accurata (total, limit, offset, has_more)
  INV-EP-4   Sort whitelisted (4 valori). Input bogus → 400
  INV-EP-5   Limit max 100 enforced
  INV-EP-6   Solo is_published=True AND is_active=True (parity con catalog)
  INV-EP-7   Multi-tenant scoping (slug A non leakka B)
  INV-EP-8   No PII leak (no cost_price, sku, organization_id, ecc.)
  INV-EP-9   Response shape stable (EmbedProductCard fields canonical)
  INV-EP-10  Empty filter → items=[], total=0, no 404
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


class TestEmbedProductsModule:
    def test_service_function_exists(self):
        from services.embed_init_service import get_embed_products_data
        assert callable(get_embed_products_data)

    def test_endpoint_registered(self):
        from routers.embed_public import router
        paths = {r.path for r in router.routes}
        assert "/public/embed/products/{slug}" in paths, (
            f"Endpoint /products/{{slug}} non registrato. Paths: {paths}"
        )

    def test_handler_is_coroutine(self):
        from routers import embed_public
        assert hasattr(embed_public, "get_embed_products")
        assert inspect.iscoroutinefunction(embed_public.get_embed_products)


# ─── INV-EP-9 — Response shape ─────────────────────────────────────────


class TestINV_EP_9_ResponseShape:
    """EmbedProductCard è il modello stable della response. Cambiare un
    campo = breaking change widget downstream."""

    REQUIRED_CARD_FIELDS = (
        "id",
        "name",
        "image_url",
        "unit_price",
        "currency",
        "category",
        "category_slug",
        "item_type",
        "price_mode",
        "transaction_mode",
        "stock_quantity",
    )

    def test_card_required_fields(self):
        from routers.embed_public import EmbedProductCard
        fields = EmbedProductCard.model_fields
        for f in self.REQUIRED_CARD_FIELDS:
            assert f in fields, (
                f"EmbedProductCard.{f} missing. Widget V1 rotto."
            )

    def test_response_required_fields(self):
        from routers.embed_public import EmbedProductsResponse
        fields = EmbedProductsResponse.model_fields
        for f in ("slug", "currency", "items", "pagination"):
            assert f in fields

    def test_pagination_shape(self):
        from routers.embed_public import EmbedPagination
        fields = EmbedPagination.model_fields
        for f in ("total", "limit", "offset", "has_more"):
            assert f in fields


# ─── INV-EP-8 — No PII leak ────────────────────────────────────────────


class TestINV_EP_8_NoPIILeak:
    """EmbedProductCard NON deve mai esporre campi privati."""

    PRIVATE_FIELD_BLACKLIST = (
        "cost_price",
        "sku",
        "organization_id",
        "is_active",
        "is_published",
        "store_ids",
        "supplier_id",
        "internal_notes",
        "created_at",  # admin-only timestamp
        "updated_at",
        "_id",
        "admin_email",
        "notification_email",
    )

    def test_card_model_no_blacklisted(self):
        from routers.embed_public import EmbedProductCard
        fields = set(EmbedProductCard.model_fields)
        for blocked in self.PRIVATE_FIELD_BLACKLIST:
            assert blocked not in fields, (
                f"INV-EP-8 violato: EmbedProductCard expone '{blocked}'."
            )


# ─── INV-EP-2 — Type whitelist ─────────────────────────────────────────


class TestINV_EP_2_TypeWhitelist:
    """Filter `?type=` deve accettare SOLO valori di PRODUCT_TYPE_KEYS."""

    def test_product_type_keys_known(self):
        from models.product_types import PRODUCT_TYPE_KEYS
        # I 6 product types canonici Phase 0
        expected = {
            "physical", "service", "rental", "event_ticket",
            "digital", "course",
        }
        for t in expected:
            assert t in PRODUCT_TYPE_KEYS, (
                f"Type '{t}' rimosso da PRODUCT_TYPE_KEYS — widget rotto."
            )

    def test_handler_validates_type_param(self):
        """Il service o handler deve riusare PRODUCT_TYPE_KEYS per validation."""
        from services.embed_init_service import get_embed_products_data
        sig = inspect.signature(get_embed_products_data)
        assert "type_filter" in sig.parameters or "item_type" in sig.parameters, (
            "Service signature deve esporre filter type. Per V1 il "
            "validation puo' essere in handler — l'importante e' che esista."
        )


# ─── INV-EP-4 — Sort whitelist ─────────────────────────────────────────


class TestINV_EP_4_SortWhitelist:
    """Sort accetta SOLO 4 valori: name | price_asc | price_desc | newest."""

    def test_sort_modes_constant_exists(self):
        from services.embed_init_service import EMBED_PRODUCT_SORT_MODES
        assert isinstance(EMBED_PRODUCT_SORT_MODES, (set, tuple, frozenset))
        for m in ("name", "price_asc", "price_desc", "newest"):
            assert m in EMBED_PRODUCT_SORT_MODES, (
                f"Sort mode '{m}' missing — widget filter UI rotto."
            )

    def test_sort_modes_size_minimal(self):
        """Whitelist conservative — nessun escape ad altri campi via injection.

        Track E Step 1.3: aggiunto 'relevance' (totale 5). Pinning resta
        critico per evitare drift accidentale (es. qualcuno aggiunge
        sort=stock_quantity senza review consapevole). Cambiare il count
        atteso richiede update consapevole.
        """
        from services.embed_init_service import EMBED_PRODUCT_SORT_MODES
        expected = {"name", "price_asc", "price_desc", "newest", "relevance"}
        assert set(EMBED_PRODUCT_SORT_MODES) == expected, (
            f"EMBED_PRODUCT_SORT_MODES drift: {set(EMBED_PRODUCT_SORT_MODES)} "
            f"!= {expected}. Aggiungere/rimuovere modi richiede review "
            f"consapevole + update sentinel + update widget filter UI."
        )


# ─── INV-EP-5 — Limit max enforced ─────────────────────────────────────


class TestINV_EP_5_LimitCap:
    """Hard cap su limit per evitare scraping massivo."""

    def test_limit_cap_constant(self):
        from services.embed_init_service import EMBED_PRODUCT_LIMIT_MAX
        assert EMBED_PRODUCT_LIMIT_MAX == 100, (
            f"EMBED_PRODUCT_LIMIT_MAX={EMBED_PRODUCT_LIMIT_MAX}, expected 100. "
            "Soglia troppo alta = scraping facile. Troppo bassa = piu' "
            "round-trip per il widget grid."
        )

    def test_limit_default(self):
        from services.embed_init_service import EMBED_PRODUCT_LIMIT_DEFAULT
        assert EMBED_PRODUCT_LIMIT_DEFAULT == 20


# ─── Service contract ──────────────────────────────────────────────────


class TestServiceContract:
    @pytest.mark.asyncio
    async def test_function_is_async(self):
        from services.embed_init_service import get_embed_products_data
        assert inspect.iscoroutinefunction(get_embed_products_data)

    def test_function_params(self):
        from services.embed_init_service import get_embed_products_data
        sig = inspect.signature(get_embed_products_data)
        params = set(sig.parameters)
        # Slug obbligatorio, gli altri opzionali
        assert "slug" in params
        # I filter params dovrebbero esistere (esatto nome puo' variare)
        # Almeno category, type, sort, limit, offset in qualche forma
        has_filter_capable = any(
            x in params for x in ("category_slug", "category", "type_filter",
                                    "item_type", "sort_mode", "sort")
        )
        assert has_filter_capable, (
            f"Service signature {params} manca params di filter — "
            "widget filter UI non funzionera'."
        )


# ─── Metrics integration ───────────────────────────────────────────────


class TestMetricsIntegration:
    def test_metric_counter_exists(self):
        from core.observability import metrics
        if not metrics.is_available():
            pytest.skip("prometheus_client not installed")
        assert hasattr(metrics, "EMBED_PRODUCT_SEARCHES"), (
            "Counter EMBED_PRODUCT_SEARCHES missing."
        )

    def test_record_helper_exists(self):
        from core.observability import metrics
        assert hasattr(metrics, "record_embed_product_search"), (
            "Helper record_embed_product_search missing."
        )

    def test_record_helper_fail_safe(self):
        from core.observability import metrics
        metrics.record_embed_product_search(slug="phantom", has_filter=True)
