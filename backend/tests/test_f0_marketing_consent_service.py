"""Sentinel — F0: marketing_consent_service (fondamenta modulo Newsletter).

Estratta la logica di opt-in marketing (audit + dual snapshot sync) prima
duplicata inline nel checkout. Questi test pinnano:
  · il triple-write del servizio condiviso (audit + customer_accounts + customers);
  · la semantica most-recent-wins (un opt-in azzera marketing_revoked_at);
  · il caso guest (solo customers, nessun account) senza errori;
  · la PARITÀ: il checkout delega al servizio (no più logica inline duplicata).

Richiede MongoDB reale per i test behavioral (skip se assente). Il test di
parità è puro source-inspection (no DB).

INV-F0-1  record_marketing_optin scrive audit(merchant_marketing) + sync account + customers
INV-F0-2  most-recent-wins: accepted_marketing_at settato, marketing_revoked_at azzerato
INV-F0-3  guest (no account) → sync solo su customers, nessuna eccezione
INV-F0-4  PARITÀ: order_creation_service usa record_marketing_optin (non più inline)
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

ORG = "org_f0"


@pytest.fixture
async def consent_db():
    """Ephemeral DB con customers + customer_accounts + consent_audit swappate."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB unavailable: {e}")

    db_name = f"test_f0_{uuid.uuid4().hex[:8]}"
    db = client[db_name]

    import database as db_mod
    import repositories.consent_audit_repository as car_mod
    orig_acc = db_mod.customer_accounts_collection
    orig_cust = db_mod.customers_collection
    orig_audit = car_mod.consent_audit_collection
    db_mod.customer_accounts_collection = db.customer_accounts
    db_mod.customers_collection = db.customers
    car_mod.consent_audit_collection = db.consent_audit
    try:
        yield db
    finally:
        db_mod.customer_accounts_collection = orig_acc
        db_mod.customers_collection = orig_cust
        car_mod.consent_audit_collection = orig_audit
        try:
            await client.drop_database(db_name)
        except Exception:
            pass
        client.close()


async def test_inv_f0_1_and_2_triple_write_and_most_recent_wins(consent_db):
    from services.marketing_consent_service import record_marketing_optin

    # Stato iniziale: cliente registrato che AVEVA revocato (revoke recente).
    await consent_db.customers.insert_one({
        "id": "cust1", "organization_id": ORG, "email": "a@b.c",
        "accepted_marketing_at": None, "marketing_revoked_at": "2020-01-01T00:00:00+00:00",
    })
    await consent_db.customer_accounts.insert_one({
        "id": "acc1", "organization_id": ORG, "email": "a@b.c",
        "accepted_marketing_at": None, "marketing_revoked_at": "2020-01-01T00:00:00+00:00",
    })

    await record_marketing_optin(
        organization_id=ORG,
        customer_id="cust1",
        customer_account_id="acc1",
        store_id="store1",
        email="a@b.c",
        locale="it",
        version_tag="v1.0",
        version_hash="abc123",
        ip_address="1.2.3.4",
        user_agent="UA",
        source="customer_marketing_optin",
    )

    # INV-F0-2 — most-recent-wins su ENTRAMBE le collection
    cust = await consent_db.customers.find_one({"id": "cust1"})
    acc = await consent_db.customer_accounts.find_one({"id": "acc1"})
    assert cust["accepted_marketing_at"] is not None
    assert cust["marketing_revoked_at"] is None
    assert acc["accepted_marketing_at"] is not None
    assert acc["marketing_revoked_at"] is None

    # INV-F0-1 — audit immutabile scritto con document_type marketing
    audit = await consent_db.consent_audit.find_one(
        {"organization_id": ORG, "document_type": "merchant_marketing"},
    )
    assert audit is not None
    assert audit["source"] == "customer_marketing_optin"
    assert audit.get("user_id") == "acc1"
    assert audit.get("customer_email") == "a@b.c"


async def test_inv_f0_3_guest_no_account(consent_db):
    from services.marketing_consent_service import record_marketing_optin

    await consent_db.customers.insert_one({
        "id": "cust_guest", "organization_id": ORG, "email": "g@b.c",
    })

    # Nessun customer_account_id → nessun errore, sync solo su customers.
    await record_marketing_optin(
        organization_id=ORG,
        customer_id="cust_guest",
        customer_account_id=None,
        email="g@b.c",
        source="customer_marketing_optin",
    )

    cust = await consent_db.customers.find_one({"id": "cust_guest"})
    assert cust["accepted_marketing_at"] is not None
    assert cust["marketing_revoked_at"] is None
    audit = await consent_db.consent_audit.find_one(
        {"organization_id": ORG, "customer_email": "g@b.c"},
    )
    assert audit is not None
    assert audit.get("user_id") is None  # guest


def test_inv_f0_4_checkout_delegates_to_service():
    """PARITÀ — il checkout non ha più la logica inline ma chiama il servizio."""
    import inspect
    from services import order_creation_service
    src = inspect.getsource(order_creation_service)
    assert "record_marketing_optin" in src, (
        "order_creation_service non usa record_marketing_optin — la logica "
        "opt-in marketing è di nuovo duplicata inline (drift)."
    )
    # La vecchia sync inline (su due collection separate) non deve riapparire
    # nel ramo marketing: non ci devono essere DUE update_one con
    # accepted_marketing_at scritte a mano nel checkout.
    assert src.count('"accepted_marketing_at": iso_now') == 0, (
        "Sync marketing inline ancora presente nel checkout: estrazione F0 "
        "non completa."
    )
