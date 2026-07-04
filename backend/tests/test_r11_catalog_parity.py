"""Contract test — R11/R12: parità catalogo storefront ↔ embed.

Decisione R11 (2026-06-19): le due superfici catalogo NON vengono fuse in un
service unico (hanno contratti di risposta e capacità intenzionalmente diversi:
storefront = ``PublicProduct``/lista piatta; embed = card dict + ricerca/
filtro/paginazione). Il drift che conta — "stessi prodotti, stesse logiche
commerciali" — viene invece BLOCCATO da questo contract test: per lo stesso
store, le due superfici devono mostrare lo STESSO insieme di prodotti con gli
STESSI campi-identità/commercio.

Questo realizza l'intento di R11 (no differenze di logica A↔B) e di R12
(contract-test backend) a costo/rischio minimi, senza toccare il codice di
produzione.

Campi condivisi pinnati (intersezione PublicProduct ∩ EmbedProductCard):
  id, slug, name, description, image_url, unit_price, category, unit,
  item_type, unit_label, price_mode, transaction_mode, stock_quantity.

INV-R11-1  Stesso store → stesso SET di product_id su entrambe le superfici
INV-R11-2  Per ogni prodotto, i campi-identità/commercio coincidono
INV-R11-3  Il filtro "event_ticket senza occorrenze" è identico (parità di
           visibilità) — coperto da INV-R11-1 sul set.
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

# Riuso la fixture di seeding + gli swap helper già provati (no duplicazione).
from test_catalog_n_plus_one import (  # noqa: E402
    seeded_catalog_db,
    _swap_collections,
    _restore_collections,
    _build_request,
)

SHARED_FIELDS = [
    "id", "slug", "name", "description", "image_url", "unit_price",
    "category", "unit", "item_type", "unit_label", "price_mode",
    "transaction_mode", "stock_quantity",
]


@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    from routers.auth import limiter
    original = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = original


def _sf_field(p, key):
    return getattr(p, key, None)


async def _both_catalogs(seeded):
    """Risolve il catalogo da ENTRAMBE le superfici sullo stesso DB seedato."""
    from routers.public import get_public_catalog, _invalidate_resolve_org_cache
    from services.embed_init_service import get_embed_products_data

    test_db = seeded["client"][seeded["db_name"]]
    slug = seeded["store_slug"]
    originals = _swap_collections(test_db)
    try:
        # R13 — evita hit di cache da run precedenti sullo stesso slug.
        _invalidate_resolve_org_cache(slug)
        sf = await get_public_catalog(_build_request(), slug)
        _invalidate_resolve_org_cache(slug)
        emb = await get_embed_products_data(slug, limit=100)
    finally:
        _restore_collections(originals)
    return sf, emb


async def test_inv_r11_1_same_product_set(seeded_catalog_db):
    sf, emb = await _both_catalogs(seeded_catalog_db)
    sf_ids = {p.id for p in sf.products}
    emb_ids = {it["id"] for it in emb["items"]}
    assert sf_ids == emb_ids, (
        f"Drift di visibilità catalogo storefront↔embed: "
        f"solo storefront={sf_ids - emb_ids}, solo embed={emb_ids - sf_ids}"
    )
    # Sanity: il seed espone 6 prodotti acquistabili.
    assert len(sf_ids) == 6


async def test_inv_r11_2_shared_fields_match(seeded_catalog_db):
    sf, emb = await _both_catalogs(seeded_catalog_db)
    sf_by_id = {p.id: p for p in sf.products}
    emb_by_id = {it["id"]: it for it in emb["items"]}

    for pid, sf_item in sf_by_id.items():
        emb_item = emb_by_id[pid]
        for field in SHARED_FIELDS:
            sf_val = _sf_field(sf_item, field)
            emb_val = emb_item.get(field)
            assert sf_val == emb_val, (
                f"Drift campo '{field}' per prodotto {pid}: "
                f"storefront={sf_val!r} vs embed={emb_val!r}"
            )
