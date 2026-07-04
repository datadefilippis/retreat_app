"""Sentinel — R2: propagazione extra_selections lungo la catena modelli.

L'utente sceglie extra optional/radio: devono arrivare fino all'ordine
(non solo i mandatory). Qui si pinna la PROPAGAZIONE a livello modelli
(OrderRequestItem, CartItem, CartItemInput) — la fonte dei bug era proprio
il campo assente/scartato al boundary.

INV-R2-1  OrderRequestItem accetta extra_selections (coerce a ExtraSelections)
INV-R2-2  OrderLineCreate accetta extra_selections
INV-R2-3  CartItem + CartItemInput accettano e ritengono extra_selections
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
from models.order import OrderLineCreate  # noqa: E402
from models.cart import CartItem, CartItemInput  # noqa: E402

EXTRAS = {"optional_ids": ["e1", "e2"], "radio_picks": {"size": "L"}}


# INV-R2-1
def test_order_request_item_accepts_extras():
    it = OrderRequestItem(product_id="p1", quantity=1, extra_selections=EXTRAS)
    assert it.extra_selections is not None
    assert it.extra_selections.optional_ids == ["e1", "e2"]
    assert it.extra_selections.radio_picks == {"size": "L"}


# INV-R2-2
def test_order_line_create_accepts_extras():
    ol = OrderLineCreate(product_id="p1", quantity=1, extra_selections=EXTRAS)
    assert ol.extra_selections is not None
    assert ol.extra_selections.optional_ids == ["e1", "e2"]


# INV-R2-3
def test_cart_models_retain_extras():
    ci = CartItem(product_id="p1", quantity=1, extra_selections=EXTRAS)
    assert ci.extra_selections == EXTRAS
    assert ci.model_dump().get("extra_selections") == EXTRAS  # persistito

    cin = CartItemInput(product_id="p1", quantity=1, extra_selections=EXTRAS)
    assert cin.extra_selections == EXTRAS
