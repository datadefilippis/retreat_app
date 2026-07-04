"""Sentinel — R1: l'addebito Stripe NETTA a order['total'].

Invariante: Σ(line_items.unit_amount) − discount == order['total'].
Prima del fix i line_items erano solo unit_price×qty (ignoravano extras,
shipping e coupon) → incasso ≠ order.total.

INV-R1-1  prodotti(line_total) + shipping − discount == total
INV-R1-2  riga Spedizione presente sse shipping_cost>0, assente altrimenti
INV-R1-3  line_total include gli extra (usato al posto di unit_price×qty)
INV-R1-4  fallback unit_price×qty se line_total assente
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-32b!")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.payment_checkout_service import _build_checkout_lines  # noqa: E402


def _net(lines, discount):
    return sum((li.unit_amount for li in lines), Decimal("0")) - discount


# INV-R1-1 + INV-R1-2 + INV-R1-3
def test_products_shipping_discount_net_to_total():
    order = {
        "id": "o1",
        "total": 115.0,
        "discount_total": 10.0,
        "items": [
            # 20 base + 5 extras = 25 (line_total INCLUDE gli extra)
            {"product_name": "A", "quantity": 2, "unit_price": 10, "line_total": 25.0},
            {"product_name": "B", "quantity": 1, "unit_price": 50, "line_total": 50.0},
        ],
        "fulfillment": {"shipping_cost": 50.0},
    }
    lines, discount = _build_checkout_lines(order)
    assert discount == Decimal("10.0")
    # 2 prodotti + 1 spedizione
    assert len(lines) == 3
    assert any(li.name == "Spedizione" and li.unit_amount == Decimal("50.0") for li in lines)
    # riga A usa line_total (25), non unit_price×qty (20)
    assert any(li.name.startswith("A") and li.unit_amount == Decimal("25.0") for li in lines)
    # INVARIANTE
    assert _net(lines, discount) == Decimal(str(order["total"]))


# INV-R1-2 (no shipping/discount)
def test_no_shipping_no_discount():
    order = {
        "id": "o2",
        "total": 30.0,
        "items": [{"product_name": "X", "quantity": 3, "unit_price": 10, "line_total": 30.0}],
        "fulfillment": {},
    }
    lines, discount = _build_checkout_lines(order)
    assert discount == Decimal("0")
    assert all(li.name != "Spedizione" for li in lines)
    assert _net(lines, discount) == Decimal("30.0")


# INV-R1-4 (fallback)
def test_fallback_unit_price_when_no_line_total():
    order = {
        "id": "o3",
        "total": 20.0,
        "items": [{"product_name": "Y", "quantity": 2, "unit_price": 10}],  # no line_total
        "fulfillment": {},
    }
    lines, discount = _build_checkout_lines(order)
    assert lines[0].unit_amount == Decimal("20.0")  # 10×2
    assert _net(lines, discount) == Decimal("20.0")
