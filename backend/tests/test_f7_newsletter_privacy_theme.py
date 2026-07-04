"""Sentinel — F7: privacy policy link + theme nel form newsletter.

Verifica la risoluzione dell'URL privacy (riuso per-store, custom, none) e
l'esposizione di theme + privacy_policy_url nella config pubblica.

INV-F7-1  privacy mode 'custom' → ritorna l'URL custom
INV-F7-2  privacy mode 'none' → None
INV-F7-3  privacy mode 'store' → {APP_BASE_URL}/s/{slug}/privacy (riusa route esistente)
INV-F7-4  config pubblica espone theme + privacy_policy_url
INV-F7-5  NewsletterTheme valida colori esadecimali
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
from pydantic import ValidationError

ORG = "org_f7"


def test_inv_f7_5_theme_hex_validation():
    from models.newsletter import NewsletterTheme
    NewsletterTheme(primary_color="#4b72ce", primary_text_color="#ffffff")
    with pytest.raises(ValidationError):
        NewsletterTheme(primary_color="blue")
    with pytest.raises(ValidationError):
        NewsletterTheme(primary_color="#xyz")


async def test_inv_f7_1_2_custom_and_none():
    from routers.embed_public import _resolve_newsletter_privacy_url
    assert await _resolve_newsletter_privacy_url(
        {"privacy_mode": "custom", "privacy_custom_url": "https://x.com/privacy"},
    ) == "https://x.com/privacy"
    assert await _resolve_newsletter_privacy_url({"privacy_mode": "none"}) is None
    # store mode senza store_id → None
    assert await _resolve_newsletter_privacy_url({"privacy_mode": "store"}) is None


def test_inv_f7_6_custom_url_normalized_absolute():
    """URL custom senza schema → assoluto https:// (no link relativo errato)."""
    from models.newsletter import normalize_external_url, NewsletterFormCreate
    assert normalize_external_url("afianco.ch/privacy") == "https://afianco.ch/privacy"
    assert normalize_external_url("http://x.com") == "http://x.com"
    assert normalize_external_url("https://x.com") == "https://x.com"
    assert normalize_external_url("  ") is None
    # validator a livello modello
    c = NewsletterFormCreate(name="X", privacy_mode="custom", privacy_custom_url="www.sito.com/p")
    assert c.privacy_custom_url == "https://www.sito.com/p"


@pytest.fixture
async def stores_db(monkeypatch):
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(os.environ.get("MONGO_URL"), serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB unavailable: {e}")
    db = client[f"test_f7_{uuid.uuid4().hex[:8]}"]
    import database as db_mod
    monkeypatch.setattr(db_mod, "stores_collection", db.stores)
    try:
        yield db
    finally:
        try:
            await client.drop_database(db.name)
        except Exception:
            pass
        client.close()


async def test_inv_f7_3_store_mode_resolves_public_url(stores_db):
    from routers.embed_public import _resolve_newsletter_privacy_url
    from core.embed_distribution import APP_BASE_URL
    await stores_db.stores.insert_one(
        {"id": "st1", "organization_id": ORG, "slug": "my-shop"},
    )
    url = await _resolve_newsletter_privacy_url(
        {"privacy_mode": "store", "privacy_store_id": "st1", "organization_id": ORG},
    )
    assert url == f"{APP_BASE_URL}/s/my-shop/privacy"
    # store di un'altra org → non risolve (multi-tenant)
    url2 = await _resolve_newsletter_privacy_url(
        {"privacy_mode": "store", "privacy_store_id": "st1", "organization_id": "other"},
    )
    assert url2 is None


def test_inv_f7_4_public_config_exposes_theme_and_privacy():
    from models.newsletter import NewsletterFormPublic
    cfg = NewsletterFormPublic(
        id="f", name="N", collect_name=False, collect_phone=False,
        field_configs=[], privacy_required=True,
        theme={"primary_color": "#112233", "primary_text_color": "#ffffff"},
        privacy_policy_url="https://x.com/privacy",
    )
    d = cfg.model_dump()
    assert d["theme"]["primary_color"] == "#112233"
    assert d["privacy_policy_url"] == "https://x.com/privacy"
