"""Sentinel — F2: embed del modulo Newsletter (CORS + config pubblica + blocco).

Copre:
  · CORS dinamico risolve l'identità per form_id (nlform:{id}) →
    newsletter_forms.allowed_origins (non store-slug);
  · endpoint GET config pubblica espone shape public-safe (no org/store/origins);
  · blocco builder "newsletter" genera lo snippet <afianco-newsletter-form>.

I test CORS/config richiedono MongoDB reale (skip se assente); i test
unit (path extraction, blocco) no.

INV-F2-1  _extract_slug → "nlform:{form_id}" sui path newsletter
INV-F2-2  _is_origin_allowed(nlform:id) true se origin in form.allowed_origins, false altrimenti
INV-F2-3  GET config pubblica → shape senza campi interni (org/store/allowed_origins)
INV-F2-4  blocco builder "newsletter" → snippet <afianco-newsletter-form form-id="...">
"""

import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest

ORG = "org_f2"


# ── Unit: path extraction + blocco (no DB) ───────────────────────────────

def test_inv_f2_1_extract_slug_newsletter():
    from middleware.dynamic_cors import _extract_slug, _form_id_from_path

    assert _form_id_from_path("/api/public/embed/newsletter/abc123/submit") == "abc123"
    assert _form_id_from_path("/api/public/embed/init/my-store") is None

    class _R:
        def __init__(self, path):
            from urllib.parse import urlparse
            self.url = urlparse(path)
            self.path_params = {}
            self.query_params = {}
            self.headers = {}

    assert _extract_slug(_R("/api/public/embed/newsletter/form-xyz/submit")) == "nlform:form-xyz"


def test_inv_f2_4_block_renders_snippet():
    from core.embed_blocks import compose_alacarte, BLOCKS

    assert "newsletter" in BLOCKS
    res = compose_alacarte("any-store", ["newsletter"], {"newsletter": {"form_id": "abc123def"}})
    joined = res.snippet
    assert "<afianco-newsletter-form" in joined
    assert 'form-id="abc123def"' in joined


def test_block_rejects_bad_form_id():
    from core.embed_blocks import compose_alacarte
    with pytest.raises(ValueError):
        compose_alacarte("any-store", ["newsletter"], {"newsletter": {"form_id": "bad id!"}})


# ── Behavioral: CORS + config (DB) ───────────────────────────────────────

@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    from routers.auth import limiter
    original = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = original


@pytest.fixture
async def nl_forms_db(monkeypatch):
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB unavailable: {e}")

    db_name = f"test_f2_{uuid.uuid4().hex[:8]}"
    db = client[db_name]
    import database as db_mod
    monkeypatch.setattr(db_mod, "newsletter_forms_collection", db.newsletter_forms)
    import middleware.dynamic_cors as cors_mod
    cors_mod.clear_cache()
    try:
        yield db
    finally:
        cors_mod.clear_cache()
        try:
            await client.drop_database(db_name)
        except Exception:
            pass
        client.close()


async def test_inv_f2_2_cors_form_origin_lookup(nl_forms_db):
    from middleware.dynamic_cors import _is_origin_allowed
    await nl_forms_db.newsletter_forms.insert_one({
        "id": "fid1", "organization_id": ORG, "slug": "nl-a", "name": "A",
        "is_active": True, "allowed_origins": ["https://partner.com"],
    })
    assert await _is_origin_allowed("nlform:fid1", "https://partner.com") is True
    assert await _is_origin_allowed("nlform:fid1", "https://evil.com") is False
    # form inattivo → mai allowed
    await nl_forms_db.newsletter_forms.insert_one({
        "id": "fid2", "organization_id": ORG, "slug": "nl-b", "name": "B",
        "is_active": False, "allowed_origins": ["https://partner.com"],
    })
    assert await _is_origin_allowed("nlform:fid2", "https://partner.com") is False


async def test_inv_f2_3_public_config_shape(nl_forms_db):
    from routers.embed_public import get_newsletter_form_public

    await nl_forms_db.newsletter_forms.insert_one({
        "id": "fid3", "organization_id": ORG, "store_id": "s1", "slug": "nl-c",
        "name": "Iscriviti", "collect_name": True, "collect_phone": False,
        "field_configs": [], "consent_text": "ok", "privacy_required": True,
        "success_message": None, "redirect_url": None,
        "allowed_origins": ["https://x.com"], "is_active": True,
    })

    class _Resp:
        def __init__(self):
            self.headers = {}
            self.status_code = 200

    class _Req:
        headers = {}
        path_params = {}
        query_params = {}

    import routers.embed_public as ep
    # apply_api_version no-op (evita dipendenze header nel test)
    orig = ep.apply_api_version
    ep.apply_api_version = lambda req, resp: 1
    try:
        cfg = await get_newsletter_form_public(_Req(), _Resp(), "fid3")
    finally:
        ep.apply_api_version = orig

    dumped = cfg.model_dump()
    assert dumped["id"] == "fid3"
    assert dumped["name"] == "Iscriviti"
    assert dumped["collect_name"] is True
    # shape public-safe: nessun campo interno
    for leaked in ("organization_id", "store_id", "allowed_origins", "created_at"):
        assert leaked not in dumped, f"Campo interno '{leaked}' esposto nella config pubblica"
