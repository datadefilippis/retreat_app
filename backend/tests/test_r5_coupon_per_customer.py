"""Sentinel — R5: coupon per-cliente (anti-riuso) + rollback su cancellazione.

Prima un coupon aveva solo ``max_uses`` globale: lo stesso cliente poteva
riusarlo all'infinito (finché c'era budget globale), e un ordine annullato
"bruciava" comunque un uso. R5 aggiunge:
  · ``coupon_redemptions`` unique (org, coupon_id, customer_key) → un cliente
    non redime due volte lo stesso coupon;
  · rollback del claim se il global increment fallisce (no slot fantasma);
  · ``release_coupon_for_order`` → cancellazione ordine rilascia il consumo.

Richiede MongoDB reale (unique index → DuplicateKeyError). Skip se assente.

INV-R5-1  Stesso customer_key → secondo validate_coupon = 400 "già utilizzato"
INV-R5-2  customer_key diverso → ok (entrambi consumano)
INV-R5-3  release_coupon_for_order → decrementa current_uses + libera il
          cliente (può riusare)
INV-R5-4  Esaurimento globale dopo il claim → rollback del claim (cliente
          NON resta bruciato)
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

ORG = "org_r5"


@pytest.fixture
async def coupon_db():
    """Ephemeral DB con coupons + coupon_redemptions (+ unique index)."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB unavailable: {e}")

    db_name = f"test_r5_{uuid.uuid4().hex[:8]}"
    db = client[db_name]
    # Unique index come in produzione (database.create_indexes).
    await db.coupon_redemptions.create_index(
        [("organization_id", 1), ("coupon_id", 1), ("customer_key", 1)],
        unique=True,
    )
    import database as db_mod
    orig_c = db_mod.coupons_collection
    orig_r = db_mod.coupon_redemptions_collection
    db_mod.coupons_collection = db.coupons
    db_mod.coupon_redemptions_collection = db.coupon_redemptions
    try:
        yield db
    finally:
        db_mod.coupons_collection = orig_c
        db_mod.coupon_redemptions_collection = orig_r
        try:
            await client.drop_database(db_name)
        except Exception:
            pass
        client.close()


async def _seed_coupon(db, *, code="SAVE10", max_uses=None):
    await db.coupons.insert_one({
        "id": f"cp_{code}", "organization_id": ORG, "code": code,
        "is_active": True, "discount_pct": 10, "current_uses": 0,
        "max_uses": max_uses, "store_ids": [],
    })
    return f"cp_{code}"


async def test_inv_r5_1_same_customer_rejected(coupon_db):
    from routers.coupons import validate_coupon
    await _seed_coupon(coupon_db)
    # Primo riscatto ok
    r1 = await validate_coupon(ORG, "SAVE10", 100.0, customer_key="cust_A", order_id="o1")
    assert r1["discount"] == 10.0
    # Secondo riscatto stesso cliente → rifiutato
    with pytest.raises(HTTPException) as exc:
        await validate_coupon(ORG, "SAVE10", 100.0, customer_key="cust_A", order_id="o2")
    assert exc.value.status_code == 400
    # current_uses NON deve essere salito a 2 (il secondo non ha consumato)
    cp = await coupon_db.coupons.find_one({"id": "cp_SAVE10"})
    assert cp["current_uses"] == 1


async def test_inv_r5_2_different_customer_ok(coupon_db):
    from routers.coupons import validate_coupon
    await _seed_coupon(coupon_db)
    await validate_coupon(ORG, "SAVE10", 100.0, customer_key="cust_A", order_id="o1")
    r2 = await validate_coupon(ORG, "SAVE10", 100.0, customer_key="cust_B", order_id="o2")
    assert r2["discount"] == 10.0
    cp = await coupon_db.coupons.find_one({"id": "cp_SAVE10"})
    assert cp["current_uses"] == 2


async def test_inv_r5_3_release_allows_reuse(coupon_db):
    from routers.coupons import validate_coupon, release_coupon_for_order
    await _seed_coupon(coupon_db)
    await validate_coupon(ORG, "SAVE10", 100.0, customer_key="cust_A", order_id="o1")

    # Cancellazione ordine o1 → rilascia il consumo
    released = await release_coupon_for_order(
        ORG, {"id": "o1", "coupon_code": "SAVE10", "discount_total": 10.0},
    )
    assert released == 1
    cp = await coupon_db.coupons.find_one({"id": "cp_SAVE10"})
    assert cp["current_uses"] == 0
    # Lo stesso cliente ora può riusare il coupon
    r = await validate_coupon(ORG, "SAVE10", 100.0, customer_key="cust_A", order_id="o2")
    assert r["discount"] == 10.0


async def test_inv_r5_4_global_exhaustion_rolls_back_claim(coupon_db):
    from routers.coupons import validate_coupon
    await _seed_coupon(coupon_db, code="ONE", max_uses=1)
    # cust_A consuma l'unico uso globale
    await validate_coupon(ORG, "ONE", 100.0, customer_key="cust_A", order_id="o1")
    # cust_B claima lo slot per-cliente ma il global è esaurito → 400 + rollback
    with pytest.raises(HTTPException):
        await validate_coupon(ORG, "ONE", 100.0, customer_key="cust_B", order_id="o2")
    # Nessuno slot fantasma per cust_B: può riusare se il global tornasse libero.
    rec_b = await coupon_db.coupon_redemptions.find_one(
        {"organization_id": ORG, "coupon_id": "cp_ONE", "customer_key": "cust_B"},
    )
    assert rec_b is None, "Claim per-cliente non rollback-ato dopo esaurimento globale"
