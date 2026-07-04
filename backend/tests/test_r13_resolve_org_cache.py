"""Sentinel — R13: TTL cache su `_resolve_org`.

`_resolve_org` è hot-path (ogni endpoint pubblico/embed, spesso più volte per
richiesta). La cache positive-only deve:
  · risolvere UNA sola volta lo stesso slug entro il TTL,
  · ritornare copie isolate (mutazioni downstream non inquinano la cache),
  · NON cacheare i miss (404),
  · invalidarsi a TTL scaduto e via helper esplicito.

INV-R13-1  Stesso slug entro TTL → core risolto 1 sola volta
INV-R13-2  Ritorno è una deep-copy isolata (mutare non inquina la cache)
INV-R13-3  Il 404 (miss) NON viene cacheato → riprovato
INV-R13-4  Invalidazione esplicita → ri-risoluzione
INV-R13-5  TTL scaduto → ri-risoluzione
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-32b!")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from fastapi import HTTPException

import routers.public as pub


@pytest.fixture(autouse=True)
def _clear_cache():
    pub._invalidate_resolve_org_cache()
    yield
    pub._invalidate_resolve_org_cache()


def _install_counter(monkeypatch, *, raise_404=False):
    """Sostituisce il core con un contatore; ritorna la lista delle chiamate."""
    calls = []

    async def fake_uncached(slug: str):
        calls.append(slug)
        if raise_404:
            raise HTTPException(status_code=404, detail="Catalog not found")
        return {"id": f"org-{slug}", "_store": {"slug": slug}}

    monkeypatch.setattr(pub, "_resolve_org_uncached", fake_uncached)
    return calls


async def test_inv_r13_1_same_slug_resolved_once(monkeypatch):
    calls = _install_counter(monkeypatch)
    a = await pub._resolve_org("acme")
    b = await pub._resolve_org("acme")
    assert calls == ["acme"], "Slug risolto più di una volta entro il TTL"
    assert a["id"] == b["id"] == "org-acme"
    # slug diverso → nuova risoluzione
    await pub._resolve_org("other")
    assert calls == ["acme", "other"]


async def test_inv_r13_2_returns_isolated_copy(monkeypatch):
    _install_counter(monkeypatch)
    first = await pub._resolve_org("acme")
    first["id"] = "MUTATED"
    first["_store"]["slug"] = "MUTATED"
    second = await pub._resolve_org("acme")
    assert second["id"] == "org-acme", "La mutazione downstream ha inquinato la cache"
    assert second["_store"]["slug"] == "acme", "Deep-copy non isola il nested _store"
    assert first is not second


async def test_inv_r13_3_miss_not_cached(monkeypatch):
    calls = _install_counter(monkeypatch, raise_404=True)
    with pytest.raises(HTTPException):
        await pub._resolve_org("ghost")
    with pytest.raises(HTTPException):
        await pub._resolve_org("ghost")
    assert calls == ["ghost", "ghost"], "Un miss (404) è stato cacheato"


async def test_inv_r13_4_explicit_invalidation(monkeypatch):
    calls = _install_counter(monkeypatch)
    await pub._resolve_org("acme")
    pub._invalidate_resolve_org_cache("acme")
    await pub._resolve_org("acme")
    assert calls == ["acme", "acme"], "Invalidazione esplicita non rilegge"


async def test_inv_r13_5_ttl_expiry(monkeypatch):
    calls = _install_counter(monkeypatch)
    fake_now = {"t": 1000.0}
    monkeypatch.setattr(pub.time, "monotonic", lambda: fake_now["t"])
    await pub._resolve_org("acme")
    # entro TTL → cache
    fake_now["t"] += pub._RESOLVE_ORG_TTL - 1
    await pub._resolve_org("acme")
    assert calls == ["acme"]
    # oltre TTL → ri-risoluzione
    fake_now["t"] += 2
    await pub._resolve_org("acme")
    assert calls == ["acme", "acme"]
