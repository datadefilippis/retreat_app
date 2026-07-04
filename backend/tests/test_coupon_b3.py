"""Sentinel — B3: coupon (no doppio incremento + min su subtotale).

INV-B3-1  dry_run NON incrementa current_uses (nessun find_one_and_update)
INV-B3-2  dry_run check_min_order=False NON solleva su min, anche con subtotal 0
INV-B3-3  dry_run check_min_order=True (default) solleva su min non raggiunto
INV-B3-4  validate_coupon (reale) incrementa una volta (find_one_and_update 1×)
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-32b!")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException  # noqa: E402
from routers.coupons import validate_coupon, validate_coupon_dry_run  # noqa: E402

COUPON = {
    "id": "c1", "code": "SAVE10", "organization_id": "org-1", "is_active": True,
    "min_order_amount": 50.0, "discount_pct": 10, "current_uses": 0, "max_uses": 100,
    "store_ids": [],
}


def _mock_coll():
    coll = AsyncMock()
    coll.find_one = AsyncMock(return_value=dict(COUPON))
    # l'increment ritorna il doc "reserved" (truthy) per validate_coupon
    coll.find_one_and_update = AsyncMock(return_value=dict(COUPON))
    return coll


# INV-B3-1 + INV-B3-2
async def test_dry_run_no_increment_and_skip_min():
    coll = _mock_coll()
    with patch("database.coupons_collection", coll):
        res = await validate_coupon_dry_run(
            "org-1", "SAVE10", 0.0, check_min_order=False
        )
    assert res["code"] == "SAVE10"
    coll.find_one_and_update.assert_not_called()  # nessun incremento


# INV-B3-3
async def test_dry_run_enforces_min_by_default():
    coll = _mock_coll()
    with patch("database.coupons_collection", coll):
        with pytest.raises(HTTPException) as ei:
            await validate_coupon_dry_run("org-1", "SAVE10", 0.0)  # default check_min_order=True
    assert ei.value.status_code == 400
    coll.find_one_and_update.assert_not_called()


# INV-B3-4
async def test_validate_coupon_increments_once():
    coll = _mock_coll()
    with patch("database.coupons_collection", coll):
        res = await validate_coupon("org-1", "SAVE10", 100.0)  # sopra il minimo
    assert res["discount"] == 10.0  # 10% di 100
    assert coll.find_one_and_update.call_count == 1  # un solo incremento
