"""Sentinel — F1: backend modulo Newsletter (modelli + submit pubblico).

Copre:
  · modelli (FieldConfig esteso, NewsletterForm slug/origins, Subscription source);
  · endpoint pubblico submit: crea customer org-scoped + opt-in marketing (via
    servizio condiviso) + subscription con sorgente (D7);
  · dedup per email; honeypot; consenso privacy obbligatorio; first-touch.

I test behavioral richiedono MongoDB reale (skip se assente).

INV-F1-1  FieldConfig: select richiede options; tipi non-select non le hanno
INV-F1-2  submit → customer (source=newsletter_form) + opt-in (accepted_marketing_at) + subscription confirmed
INV-F1-3  sorgente (D7): origin/referer da header server + url/label da client
INV-F1-4  dedup: stessa email due volte → 1 sola subscription (aggiornata)
INV-F1-5  honeypot valorizzato → nessuna subscription, success silenzioso
INV-F1-6  privacy_required + consenso assente → 400
INV-F1-7  first-touch: customers.metadata.acquisition_source impostato una volta
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
from fastapi import HTTPException
from pydantic import ValidationError

ORG = "org_f1"


# ── Unit: modelli (no DB) ────────────────────────────────────────────────

def test_inv_f1_1_fieldconfig_select_options():
    from models.field_config import FieldConfig
    # select senza options → errore
    with pytest.raises(ValidationError):
        FieldConfig(id="x", label="X", type="select")
    # select con options → ok, ripulite
    fc = FieldConfig(id="x", label="X", type="select", options=[" A ", "", "B"])
    assert fc.options == ["A", "B"]
    # tipo non-select → options azzerate
    fc2 = FieldConfig(id="y", label="Y", type="text", options=["A"])
    assert fc2.options is None
    # nuovi tipi accettati
    assert FieldConfig(id="e", label="E", type="email").type == "email"
    assert FieldConfig(id="p", label="P", type="tel").type == "tel"


def test_newsletter_form_slug_pattern():
    from models.newsletter import NewsletterForm
    with pytest.raises(ValidationError):
        NewsletterForm(organization_id=ORG, slug="Bad Slug!", name="N")
    f = NewsletterForm(organization_id=ORG, slug="my-form", name="N")
    assert f.store_id is None and f.is_active is True


# ── Behavioral: endpoint submit ──────────────────────────────────────────

class _Resp:
    def __init__(self):
        self.headers = {}
        self.status_code = 200


class _Req:
    def __init__(self, headers=None, ip="9.9.9.9"):
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.client = type("C", (), {"host": ip})()
        self.path_params = {}
        self.query_params = {}
        self.state = type("S", (), {})()


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
async def nl_db(monkeypatch):
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB unavailable: {e}")

    db_name = f"test_f1_{uuid.uuid4().hex[:8]}"
    db = client[db_name]
    # Dedup index come in produzione.
    await db.newsletter_subscriptions.create_index(
        [("organization_id", 1), ("form_id", 1), ("email", 1)], unique=True,
    )

    import database as db_mod
    import repositories.customer_repository as cr_mod
    import repositories.consent_audit_repository as car_mod
    monkeypatch.setattr(db_mod, "newsletter_forms_collection", db.newsletter_forms)
    monkeypatch.setattr(db_mod, "newsletter_subscriptions_collection", db.newsletter_subscriptions)
    monkeypatch.setattr(db_mod, "customers_collection", db.customers)
    monkeypatch.setattr(db_mod, "customer_accounts_collection", db.customer_accounts)
    monkeypatch.setattr(cr_mod, "customers_collection", db.customers)
    monkeypatch.setattr(car_mod, "consent_audit_collection", db.consent_audit)
    # apply_api_version: no-op nel test (irrilevante alla logica F1).
    import routers.embed_public as ep_mod
    monkeypatch.setattr(ep_mod, "apply_api_version", lambda req, resp: 1)
    try:
        yield db
    finally:
        try:
            await client.drop_database(db_name)
        except Exception:
            pass
        client.close()


async def _seed_form(db, **over):
    from models.newsletter import NewsletterForm
    form = NewsletterForm(
        organization_id=ORG, slug=over.pop("slug", "nl-form"), name="Iscriviti",
        **over,
    )
    doc = form.model_dump(mode="json")
    await db.newsletter_forms.insert_one(doc.copy())
    return doc["id"]


async def test_inv_f1_2_3_submit_creates_customer_optin_subscription(nl_db):
    from routers.embed_public import submit_newsletter_form
    from models.newsletter import NewsletterSubmitRequest

    form_id = await _seed_form(nl_db, collect_name=True)
    req = _Req(headers={
        "Origin": "https://partner.example.com",
        "Referer": "https://partner.example.com/blog",
        "User-Agent": "UA/1.0",
    })
    body = NewsletterSubmitRequest(
        email="Mario.Rossi@Example.com", name="Mario", consent_privacy=True,
        source_url="https://partner.example.com/blog/post-1",
        source_referrer="https://google.com",
        source_label="blog-footer",
    )
    res = await submit_newsletter_form(req, _Resp(), form_id, body)
    assert res.success and res.subscriber_id

    # INV-F1-2 — customer org-scoped + opt-in
    cust = await nl_db.customers.find_one({"organization_id": ORG, "email": "mario.rossi@example.com"})
    assert cust is not None
    assert cust["metadata"]["source"] == "newsletter_form"
    assert cust["accepted_marketing_at"] is not None
    assert cust["marketing_revoked_at"] is None
    # audit marketing scritto
    audit = await nl_db.consent_audit.find_one({"organization_id": ORG, "document_type": "merchant_marketing"})
    assert audit is not None
    # subscription confirmed
    sub = await nl_db.newsletter_subscriptions.find_one({"organization_id": ORG, "form_id": form_id})
    assert sub["status"] == "confirmed"
    assert sub["email"] == "mario.rossi@example.com"
    assert sub["customer_id"] == cust["id"]

    # INV-F1-3 — sorgente: server (trust) + client
    assert sub["source_origin"] == "https://partner.example.com"
    assert sub["source_referrer_server"] == "https://partner.example.com/blog"
    assert sub["source_url"] == "https://partner.example.com/blog/post-1"
    assert sub["source_referrer"] == "https://google.com"
    assert sub["source_label"] == "blog-footer"

    # INV-F1-7 — first-touch acquisition_source
    assert cust["metadata"].get("acquisition_source") == "blog-footer"


async def test_inv_f1_4_dedup_same_email(nl_db):
    from routers.embed_public import submit_newsletter_form
    from models.newsletter import NewsletterSubmitRequest

    form_id = await _seed_form(nl_db)
    for nm in ("Primo", "Secondo"):
        await submit_newsletter_form(
            _Req(headers={"Origin": "https://a.com"}), _Resp(), form_id,
            NewsletterSubmitRequest(email="dup@x.com", name=nm, consent_privacy=True),
        )
    subs = await nl_db.newsletter_subscriptions.find(
        {"organization_id": ORG, "form_id": form_id, "email": "dup@x.com"},
    ).to_list(None)
    assert len(subs) == 1, "Dedup fallito: più righe per la stessa email"
    assert subs[0]["name"] == "Secondo", "L'ultima submit deve aggiornare la riga"


async def test_inv_f1_5_honeypot_drops(nl_db):
    from routers.embed_public import submit_newsletter_form
    from models.newsletter import NewsletterSubmitRequest

    form_id = await _seed_form(nl_db)
    res = await submit_newsletter_form(
        _Req(), _Resp(), form_id,
        NewsletterSubmitRequest(email="bot@x.com", consent_privacy=True, hp="i am a bot"),
    )
    assert res.success is True  # silenzioso
    count = await nl_db.newsletter_subscriptions.count_documents({"form_id": form_id})
    assert count == 0, "Honeypot non ha scartato: subscription creata da bot"


async def test_inv_f1_6_consent_required(nl_db):
    from routers.embed_public import submit_newsletter_form
    from models.newsletter import NewsletterSubmitRequest

    form_id = await _seed_form(nl_db, privacy_required=True)
    with pytest.raises(HTTPException) as exc:
        await submit_newsletter_form(
            _Req(), _Resp(), form_id,
            NewsletterSubmitRequest(email="x@y.com", consent_privacy=False),
        )
    assert exc.value.status_code == 400
