"""Sentinel — B1: isolamento per-store del carrello embed.

Invariante: un cart appartiene a UN solo store. Accederlo con lo slug di un
ALTRO store (anche nella stessa org) → 404. Backward-compat: cart senza
store_id (legacy/org-global) non viene bloccato.

INV-B1-1  cart.store_id != store risolto → HTTPException 404
INV-B1-2  cart.store_id == store risolto → nessun blocco
INV-B1-3  cart senza store_id → nessun blocco (fail-safe legacy)
INV-B1-4  org senza _store → nessun blocco
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-32b!")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException  # noqa: E402
from routers.embed_public import _assert_cart_in_store  # noqa: E402


def _org(store_id):
    return {"id": "org-1", "_store": ({"id": store_id} if store_id else None)}


# INV-B1-1
def test_cross_store_same_org_blocked():
    cart = {"id": "cart-1", "organization_id": "org-1", "store_id": "store-A"}
    with pytest.raises(HTTPException) as ei:
        _assert_cart_in_store(cart, _org("store-B"))
    assert ei.value.status_code == 404


# INV-B1-2
def test_same_store_ok():
    cart = {"id": "cart-1", "organization_id": "org-1", "store_id": "store-A"}
    _assert_cart_in_store(cart, _org("store-A"))  # no raise


# INV-B1-3
def test_legacy_cart_no_store_id_not_blocked():
    cart = {"id": "cart-1", "organization_id": "org-1"}  # no store_id
    _assert_cart_in_store(cart, _org("store-B"))  # no raise
    cart2 = {"id": "cart-1", "organization_id": "org-1", "store_id": None}
    _assert_cart_in_store(cart2, _org("store-B"))  # no raise


# INV-B1-4
def test_org_without_store_not_blocked():
    cart = {"id": "cart-1", "organization_id": "org-1", "store_id": "store-A"}
    _assert_cart_in_store(cart, _org(None))  # no raise
