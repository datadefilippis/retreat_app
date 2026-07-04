"""Sentinel — R9: price-preview pubblico scoping-ato all'organizzazione.

Prima il `/api/public/price-preview` risolveva il prodotto per solo
``product_id`` (active+published) → qualunque visitatore poteva ottenere
prezzo/nome di QUALSIASI prodotto pubblicato di QUALSIASI org conoscendone
l'id (enumerazione cross-tenant). R9 aggiunge lo ``slug`` (required) e vincola
il prodotto all'org risolta — parità col wrapper embed.

INV-R9-1  `slug` è un campo REQUIRED di _PublicPricePreviewRequest
INV-R9-2  product di un'ALTRA org (via slug dello store) → 404 (no leak)
INV-R9-3  product della PROPRIA org → 200 con total calcolato
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from test_catalog_n_plus_one import (  # noqa: E402
    seeded_catalog_db,
    _swap_collections,
    _restore_collections,
    _build_request,
)


@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    from routers.auth import limiter
    original = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = original


def test_inv_r9_1_slug_required():
    from routers.public import _PublicPricePreviewRequest
    assert "slug" in _PublicPricePreviewRequest.model_fields
    with pytest.raises(ValidationError):
        _PublicPricePreviewRequest(product_id="p_physical_1")  # slug mancante


async def test_inv_r9_2_cross_tenant_product_rejected(seeded_catalog_db):
    from routers.public import (
        public_price_preview,
        _PublicPricePreviewRequest,
        _invalidate_resolve_org_cache,
    )
    test_db = seeded_catalog_db["client"][seeded_catalog_db["db_name"]]
    slug = seeded_catalog_db["store_slug"]

    # Inserisci un prodotto in un'ALTRA org (non collegato a questo store).
    await test_db.products.insert_one({
        "id": "p_foreign", "organization_id": "org_OTHER_tenant",
        "name": "Foreign Product", "item_type": "physical", "unit_price": 999.0,
        "is_published": True, "is_active": True,
        "transaction_mode": "direct", "price_mode": "fixed",
    })

    originals = _swap_collections(test_db)
    try:
        _invalidate_resolve_org_cache(slug)
        body = _PublicPricePreviewRequest(slug=slug, product_id="p_foreign")
        with pytest.raises(HTTPException) as exc:
            await public_price_preview(_build_request(), body)
        assert exc.value.status_code == 404, (
            "R9 violato: prodotto di un'altra org accessibile via slug dello store "
            "→ leak cross-tenant di prezzo/nome."
        )
    finally:
        _restore_collections(originals)


async def test_inv_r9_3_own_product_ok(seeded_catalog_db):
    from routers.public import (
        public_price_preview,
        _PublicPricePreviewRequest,
        _invalidate_resolve_org_cache,
    )
    test_db = seeded_catalog_db["client"][seeded_catalog_db["db_name"]]
    slug = seeded_catalog_db["store_slug"]

    originals = _swap_collections(test_db)
    try:
        _invalidate_resolve_org_cache(slug)
        body = _PublicPricePreviewRequest(slug=slug, product_id="p_physical_1", quantity=2)
        result = await public_price_preview(_build_request(), body)
    finally:
        _restore_collections(originals)

    # Shape compute_line_total: total presente e coerente (10.0 × 2).
    total = result.get("total") if isinstance(result, dict) else getattr(result, "total", None)
    assert total == 20.0, f"total inatteso: {result!r}"
