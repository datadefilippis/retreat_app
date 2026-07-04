"""Sentinel tests — Embed Block Catalog (Embed à-la-carte, Fase 0).

Congela il contract del catalogo blocchi e del generatore à-la-carte.

Invariants pinned
=================
  INV-EB-1  Preset "full" byte-identico a generate_embed_snippet (no drift)
  INV-EB-2  Catalogo serializzabile: solo blocchi selectable, "full" incluso
  INV-EB-3  Risoluzione dipendenze: requires → singleton dedup, ordine stabile
  INV-EB-4  Head contiene data-afianco-slug; base-url opzionale
  INV-EB-5  Config categorie: sanitize (lowercase, dedup, filtro invalidi)
  INV-EB-6  Sicurezza: slug/product-id invalidi → ValueError; HTML escaped
  INV-EB-7  Blocco sconosciuto → ValueError
  INV-EB-8  Output stabile/deterministico (ordine canonico del catalogo)
"""

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

from core import embed_blocks as eb  # noqa: E402
from core.embed_distribution import generate_embed_snippet  # noqa: E402


SLUG = "marco-conti-coaching"


# ─── INV-EB-1: full preset byte-identico ───────────────────────────────


def test_full_preset_byte_identical_to_legacy():
    composed = eb.compose_alacarte(SLUG, ["full"])
    assert composed.snippet == generate_embed_snippet(SLUG)
    # full non produce sezioni à-la-carte
    assert composed.head == ""
    assert composed.elements == ()
    assert composed.singletons == ()


def test_full_render_helper_matches_legacy():
    assert eb.BLOCKS["full"].render(SLUG, {}) == generate_embed_snippet(SLUG)


# ─── INV-EB-2: catalogo serializzabile ──────────────────────────────────


def test_catalog_only_selectable_blocks():
    cat = eb.get_blocks_catalog()
    ids = {b["id"] for b in cat}
    # selezionabili presenti
    assert {"full", "cart-button", "account-button", "categories", "product"} <= ids
    # singleton NON esposti
    assert "cart" not in ids
    assert "account" not in ids
    assert "product-detail" not in ids


def test_catalog_entries_have_contract_shape():
    for b in eb.get_blocks_catalog():
        assert set(b.keys()) == {"id", "label", "description", "group", "needs"}
        for f in b["needs"]:
            assert set(f.keys()) == {"key", "type", "label", "required"}


def test_product_block_needs_product_id():
    cat = {b["id"]: b for b in eb.get_blocks_catalog()}
    needs = cat["product"]["needs"]
    assert len(needs) == 1 and needs[0]["key"] == "product_id"
    assert needs[0]["required"] is True


# ─── INV-EB-3: risoluzione dipendenze ───────────────────────────────────


def test_cart_button_pulls_cart_singleton():
    c = eb.compose_alacarte(SLUG, ["cart-button"])
    sing_ids = [s["id"] for s in c.singletons]
    assert sing_ids == ["cart"]
    assert "<afianco-cart-button>" in c.elements[0]["html"]
    assert "<afianco-cart-drawer hide-trigger>" in c.singletons[0]["html"]
    assert "<afianco-checkout-button>" in c.singletons[0]["html"]


def test_categories_pulls_product_detail_and_cart():
    c = eb.compose_alacarte(SLUG, ["categories"])
    sing_ids = [s["id"] for s in c.singletons]
    # ordine canonico del catalogo (cart precede product-detail in _BLOCK_LIST)
    assert set(sing_ids) == {"product-detail", "cart"}
    assert sing_ids == ["cart", "product-detail"]


def test_singletons_deduplicated_across_blocks():
    # cart-button + product → entrambi richiedono "cart": un solo singleton
    c = eb.compose_alacarte(SLUG, ["cart-button", "product"], {"product": {"product_id": "abc123"}})
    sing_ids = [s["id"] for s in c.singletons]
    assert sing_ids.count("cart") == 1


# ─── INV-EB-4: head + config pagina ─────────────────────────────────────


def test_head_contains_slug_data_attribute():
    c = eb.compose_alacarte(SLUG, ["cart-button"])
    assert f'data-afianco-slug="{SLUG}"' in c.head
    assert "data-afianco-base-url" not in c.head


def test_head_includes_base_url_when_provided():
    c = eb.compose_alacarte(SLUG, ["cart-button"], base_url="http://localhost:8000")
    assert 'data-afianco-base-url="http://localhost:8000"' in c.head


# ─── INV-EB-5: sanitize categorie ───────────────────────────────────────


def test_categories_sanitized_lowercase_dedup_filtered():
    c = eb.compose_alacarte(
        SLUG,
        ["categories"],
        {"categories": {"categories": ["Coaching", "coaching", "BAD SLUG!", "workshop"]}},
    )
    html = c.elements[0]["html"]
    # "Coaching"→"coaching" dedup, "BAD SLUG!" scartato, "workshop" tenuto.
    # Una griglia per categoria (attributo `category`).
    assert '<afianco-product-grid category="coaching">' in html
    assert '<afianco-product-grid category="workshop">' in html
    assert html.count("<afianco-product-grid category=") == 2


def test_categories_empty_renders_full_grid():
    c = eb.compose_alacarte(SLUG, ["categories"], {"categories": {"categories": []}})
    html = c.elements[0]["html"]
    assert "<afianco-product-grid show-filter-nav>" in html
    assert "categories=" not in html


# ─── INV-EB-6: sicurezza ────────────────────────────────────────────────


def test_invalid_slug_raises():
    with pytest.raises(ValueError):
        eb.compose_alacarte("a", ["cart-button"])  # troppo corto
    with pytest.raises(ValueError):
        eb.compose_alacarte("Bad Slug!", ["cart-button"])


def test_invalid_product_id_raises():
    with pytest.raises(ValueError):
        eb.compose_alacarte(SLUG, ["product"], {"product": {"product_id": "bad id!"}})
    with pytest.raises(ValueError):
        eb.compose_alacarte(SLUG, ["product"], {"product": {"product_id": ""}})


def test_product_id_escaped_and_emitted():
    c = eb.compose_alacarte(SLUG, ["product"], {"product": {"product_id": "prod-42"}})
    assert '<afianco-product product-id="prod-42">' in c.elements[0]["html"]


# ─── INV-EB-7: blocco sconosciuto ───────────────────────────────────────


def test_unknown_block_raises():
    with pytest.raises(ValueError):
        eb.compose_alacarte(SLUG, ["does-not-exist"])


# ─── INV-EB-8: output deterministico ────────────────────────────────────


def test_output_stable_regardless_of_selection_order():
    a = eb.compose_alacarte(SLUG, ["cart-button", "account-button"])
    b = eb.compose_alacarte(SLUG, ["account-button", "cart-button"])
    assert a.snippet == b.snippet


def test_snippet_has_three_guided_sections():
    c = eb.compose_alacarte(SLUG, ["cart-button"])
    assert "<!-- 1)" in c.snippet
    assert "<!-- 2)" in c.snippet
    assert "<!-- 3)" in c.snippet
