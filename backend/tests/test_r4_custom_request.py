"""Sentinel — R4: persistenza + propagazione di `service_custom_request`.

Quando il cliente propone una data/ora FUORI dagli slot di disponibilità
(product.metadata.service_allow_custom_request), il flag deve:
  1. essere accettato al boundary (OrderRequestItem / OrderLineCreate),
  2. viaggiare sul carrello embed (CartItem / CartItemInput),
  3. essere PERSISTITO sulla riga d'ordine (OrderLineBase) — prima veniva
     letto solo dal validator e poi scartato, lasciando l'admin senza traccia.

Parità A=B=C: lo stesso campo attraversa storefront, embed-full ed embed
à-la-carte (stesse classi condivise).

INV-R4-1  OrderRequestItem accetta service_custom_request
INV-R4-2  OrderLineCreate accetta service_custom_request
INV-R4-3  OrderLineBase persiste service_custom_request (default False)
INV-R4-4  CartItem + CartItemInput ritengono service_custom_request
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

from routers.public import OrderRequestItem  # noqa: E402
from models.order import OrderLineCreate, OrderLineBase  # noqa: E402
from models.cart import CartItem, CartItemInput  # noqa: E402


# INV-R4-1
def test_order_request_item_accepts_custom_request():
    it = OrderRequestItem(product_id="p1", quantity=1, service_custom_request=True)
    assert it.service_custom_request is True
    # default sicuro
    assert OrderRequestItem(product_id="p1", quantity=1).service_custom_request is False


# INV-R4-2
def test_order_line_create_accepts_custom_request():
    ol = OrderLineCreate(product_id="p1", quantity=1, service_custom_request=True)
    assert ol.service_custom_request is True
    assert OrderLineCreate(product_id="p1", quantity=1).service_custom_request is False


# INV-R4-3
def test_order_line_base_persists_custom_request():
    line = OrderLineBase(
        product_id="p1",
        product_name="Servizio",
        quantity=1,
        unit_price=10.0,
        line_total=10.0,
        service_custom_request=True,
    )
    assert line.service_custom_request is True
    assert line.model_dump().get("service_custom_request") is True
    # back-compat: ordini storici senza il campo → False
    legacy = OrderLineBase(
        product_id="p1", product_name="X", quantity=1, unit_price=1.0, line_total=1.0,
    )
    assert legacy.service_custom_request is False


# INV-R4-4
def test_cart_models_retain_custom_request():
    ci = CartItem(product_id="p1", quantity=1, service_custom_request=True)
    assert ci.service_custom_request is True
    assert ci.model_dump().get("service_custom_request") is True

    cin = CartItemInput(product_id="p1", quantity=1, service_custom_request=True)
    assert cin.service_custom_request is True
