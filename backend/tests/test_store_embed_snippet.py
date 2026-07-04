"""Sentinel tests — store embed builder à-la-carte (Fase 3).

Invariants pinned
=================
  INV-ES-1  embed-info espone blocks_catalog (con "full")
  INV-ES-2  POST embed-snippet compone lo snippet dallo slug DELLO STORE
            (slug server-derived, non dal client)
  INV-ES-3  blocco sconosciuto → HTTP 422
  INV-ES-4  config prodotto invalida → HTTP 422 (sanitize centralizzata)
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException  # noqa: E402
from routers import store_embed  # noqa: E402

STORE = {
    "id": "store-1",
    "slug": "marco-conti-coaching",
    "name": "Marco Conti",
    "is_published": True,
    "allowed_origins": ["https://x.com"],
    "organization_id": "org-1",
}
USER = {"organization_id": "org-1", "user_id": "u1", "role": "admin"}


# INV-ES-1
def test_embed_info_includes_catalog():
    resp = store_embed._build_embed_info_response(STORE)
    assert isinstance(resp.blocks_catalog, list) and resp.blocks_catalog
    ids = {b["id"] for b in resp.blocks_catalog}
    assert "full" in ids
    assert {"cart-button", "account-button", "categories", "product"} <= ids


# INV-ES-2
async def test_compose_endpoint_uses_store_slug():
    body = store_embed.EmbedSnippetComposeRequest(blocks=["cart-button"], config={})
    with patch.object(store_embed, "_load_store_or_404", AsyncMock(return_value=STORE)):
        resp = await store_embed.compose_store_embed_snippet("store-1", body, USER)
    assert "afianco-cart-button" in resp.snippet
    assert 'data-afianco-slug="marco-conti-coaching"' in resp.head
    assert any(s["id"] == "cart" for s in resp.singletons)


# INV-ES-3
async def test_compose_endpoint_unknown_block_422():
    body = store_embed.EmbedSnippetComposeRequest(blocks=["does-not-exist"], config={})
    with patch.object(store_embed, "_load_store_or_404", AsyncMock(return_value=STORE)):
        with pytest.raises(HTTPException) as ei:
            await store_embed.compose_store_embed_snippet("store-1", body, USER)
    assert ei.value.status_code == 422


# INV-ES-4
async def test_compose_endpoint_invalid_product_id_422():
    body = store_embed.EmbedSnippetComposeRequest(
        blocks=["product"], config={"product": {"product_id": "bad id!"}}
    )
    with patch.object(store_embed, "_load_store_or_404", AsyncMock(return_value=STORE)):
        with pytest.raises(HTTPException) as ei:
            await store_embed.compose_store_embed_snippet("store-1", body, USER)
    assert ei.value.status_code == 422
