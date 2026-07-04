"""Sentinel tests — embed preview token (Embed à-la-carte, Fase 5).

Invariants pinned
=================
  INV-EP-1  mint→verify round-trip OK per lo stesso slug
  INV-EP-2  token valido per slug diverso → rifiutato (slug-scoped)
  INV-EP-3  token spazzatura / vuoto → rifiutato
  INV-EP-4  bypass CORS read-only: GET ammesso, POST/PATCH/DELETE no
            (preflight OPTIONS ammesso solo se il metodo richiesto e' GET)
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-32b!")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from unittest.mock import AsyncMock, patch  # noqa: E402

from core.embed_preview import mint_preview_token, verify_preview_token  # noqa: E402
from middleware.dynamic_cors import _preview_method_ok, _preview_token_authorizes  # noqa: E402


# INV-EP-1
def test_mint_verify_roundtrip():
    token, ttl = mint_preview_token("acme", "store-1", "org-1")
    assert ttl > 0
    assert verify_preview_token(token, "acme") is True


# INV-EP-2
def test_token_is_slug_scoped():
    token, _ = mint_preview_token("acme", "store-1", "org-1")
    assert verify_preview_token(token, "beta") is False


# INV-EP-3
def test_garbage_token_rejected():
    assert verify_preview_token("", "acme") is False
    assert verify_preview_token("not.a.jwt", "acme") is False


# INV-EP-4
def test_preview_method_read_only():
    def req(reqmethod=None):
        m = MagicMock()
        m.headers = {"Access-Control-Request-Method": reqmethod} if reqmethod else {}
        return m

    assert _preview_method_ok(req(), "GET") is True
    assert _preview_method_ok(req(), "POST") is False
    assert _preview_method_ok(req(), "PATCH") is False
    assert _preview_method_ok(req(), "DELETE") is False
    # preflight di un GET → ok
    assert _preview_method_ok(req("GET"), "OPTIONS") is True
    # preflight di un POST → no
    assert _preview_method_ok(req("POST"), "OPTIONS") is False


# INV-EP-5 — B2: il bypass richiede store_id corrispondente allo store reale
def _patch_store(store_id_or_none):
    coll = AsyncMock()
    coll.find_one = AsyncMock(
        return_value=({"id": store_id_or_none} if store_id_or_none else None)
    )
    return patch("database.stores_collection", coll)


async def test_preview_authorizes_when_store_matches():
    token, _ = mint_preview_token("acme", "store-A", "org-1")
    with _patch_store("store-A"):
        assert await _preview_token_authorizes(token, "acme") is True


async def test_preview_rejected_when_store_mismatch():
    token, _ = mint_preview_token("acme", "store-A", "org-1")
    with _patch_store("store-B"):  # slug rimappato a un altro store
        assert await _preview_token_authorizes(token, "acme") is False


async def test_preview_rejected_when_slug_mismatch():
    token, _ = mint_preview_token("acme", "store-A", "org-1")
    with _patch_store("store-A"):
        assert await _preview_token_authorizes(token, "altro-slug") is False


async def test_preview_rejected_when_store_not_found():
    token, _ = mint_preview_token("acme", "store-A", "org-1")
    with _patch_store(None):
        assert await _preview_token_authorizes(token, "acme") is False
