#!/usr/bin/env python3
"""
P11 — Offer profiles registry + schema integration test suite.

Invocation:
  cd backend && ./venv/bin/python tests/test_offer_profiles.py
"""
from __future__ import annotations

import os
import sys
import traceback
from typing import Callable

os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_database")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.offer_profiles import (  # noqa: E402
    OFFER_PROFILES,
    OFFER_PROFILE_IDS,
    OfferProfile,
    apply_profile_defaults,
    derive_profile_from_axes,
    get_profile_by_id,
    serialize_catalog,
    validate_profile_id,
)
from models.product import ProductCreate, ProductUpdate  # noqa: E402


def t01_registry_shape():
    # Registry has the 6 expected ids
    expected = {"direct_sale", "request_sale", "quote", "rental", "open_event", "capped_event"}
    assert set(OFFER_PROFILE_IDS) == expected, OFFER_PROFILE_IDS
    assert len(OFFER_PROFILES) == 6
    # Each entry is a frozen dataclass
    for p in OFFER_PROFILES.values():
        assert isinstance(p, OfferProfile)
        assert p.id and p.item_type and p.transaction_mode and p.price_mode and p.behavior


def t02_get_profile_by_id():
    p = get_profile_by_id("direct_sale")
    assert p is not None and p.behavior == "checkout"
    assert get_profile_by_id("nope") is None
    assert get_profile_by_id(None) is None
    assert get_profile_by_id("") is None


def t03_derive_from_axes():
    assert derive_profile_from_axes("physical", "direct", "fixed") == "direct_sale"
    assert derive_profile_from_axes("physical", "request", "fixed") == "request_sale"
    assert derive_profile_from_axes("service", "request", "inquiry") == "quote"
    assert derive_profile_from_axes("rental", "approval", "fixed") == "rental"
    assert derive_profile_from_axes("event_ticket", "direct", "fixed") == "open_event"
    assert derive_profile_from_axes("event_ticket", "request", "fixed") == "capped_event"
    # Unknown combo
    assert derive_profile_from_axes("physical", "approval", "fixed") is None
    # Missing axis
    assert derive_profile_from_axes("physical", "", "fixed") is None
    assert derive_profile_from_axes(None, "direct", "fixed") is None


def t04_apply_profile_defaults_fills_missing():
    out = apply_profile_defaults("direct_sale", {"name": "x"})
    assert out["item_type"] == "physical"
    assert out["transaction_mode"] == "direct"
    assert out["price_mode"] == "fixed"
    assert out["name"] == "x"
    # Untouched original
    orig = {"name": "x"}
    _ = apply_profile_defaults("direct_sale", orig)
    assert "item_type" not in orig, "mutation leaked to input"


def t05_apply_profile_defaults_preserves_explicit():
    # Client's explicit choice wins over profile default
    out = apply_profile_defaults("direct_sale", {
        "item_type": "rental", "transaction_mode": "approval", "price_mode": "fixed",
    })
    assert out["item_type"] == "rental"
    assert out["transaction_mode"] == "approval"
    assert out["price_mode"] == "fixed"


def t06_apply_profile_defaults_unknown_noop():
    out = apply_profile_defaults("ghost_profile", {"name": "x"})
    assert out == {"name": "x"}


def t07_validate_profile_id():
    # Accepts known ids and pass-through for None/empty
    validate_profile_id("direct_sale")
    validate_profile_id(None)
    validate_profile_id("")
    # Rejects unknown
    try:
        validate_profile_id("never_heard_of")
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "offer_profile_id" in str(e) or "sconosciuto" in str(e)


def t08_serialize_catalog():
    cat = serialize_catalog()
    assert isinstance(cat, list) and len(cat) == 6
    # Each entry has the full OfferProfile shape
    for entry in cat:
        for k in ("id", "item_type", "transaction_mode", "price_mode", "behavior", "description"):
            assert k in entry, f"missing {k}"
    # Ids in stable order
    ids = [e["id"] for e in cat]
    assert ids == list(OFFER_PROFILE_IDS)


def t09_product_create_no_profile_is_backward_compat():
    p = ProductCreate(
        name="legacy client",
        item_type="physical", transaction_mode="request", price_mode="fixed",
    )
    assert p.offer_profile_id is None
    assert p.item_type == "physical"


def t10_product_create_with_profile_fills_axes():
    p = ProductCreate(name="x", offer_profile_id="quote")
    assert p.offer_profile_id == "quote"
    assert p.item_type == "service"
    assert p.transaction_mode == "request"
    assert p.price_mode == "inquiry"


def t11_product_create_explicit_axes_override_profile():
    p = ProductCreate(
        name="override",
        offer_profile_id="direct_sale",
        item_type="rental", transaction_mode="approval", price_mode="fixed",
    )
    # Explicit wins over profile defaults
    assert p.item_type == "rental"
    assert p.transaction_mode == "approval"
    assert p.price_mode == "fixed"


def t12_product_create_unknown_profile_rejected():
    try:
        ProductCreate(name="x", offer_profile_id="ghost_profile")
        raise AssertionError("expected ValidationError")
    except Exception as e:
        assert "offer_profile_id" in str(e) or "ghost_profile" in str(e) or "sconosciuto" in str(e)


def t13_product_update_accepts_profile_id_optional():
    u = ProductUpdate(offer_profile_id="rental")
    assert u.offer_profile_id == "rental"
    u2 = ProductUpdate()
    assert u2.offer_profile_id is None
    u3 = ProductUpdate(offer_profile_id=None)
    assert u3.offer_profile_id is None


def t14_product_update_unknown_profile_rejected():
    try:
        ProductUpdate(offer_profile_id="nonexistent")
        raise AssertionError("expected ValidationError")
    except Exception as e:
        assert "offer_profile" in str(e) or "sconosciuto" in str(e)


def t15_existing_compat_check_still_active():
    # P11 must NOT break the pre-existing direct + inquiry block
    try:
        ProductCreate(name="x", transaction_mode="direct", price_mode="inquiry")
        raise AssertionError("expected ValidationError on direct+inquiry")
    except Exception as e:
        assert "diretta" in str(e) or "checkout" in str(e) or "inquiry" in str(e).lower()


TESTS: list[tuple[str, Callable]] = [
    ("t01 registry shape", t01_registry_shape),
    ("t02 get_profile_by_id", t02_get_profile_by_id),
    ("t03 derive_profile_from_axes", t03_derive_from_axes),
    ("t04 apply_profile_defaults fills missing", t04_apply_profile_defaults_fills_missing),
    ("t05 apply_profile_defaults preserves explicit", t05_apply_profile_defaults_preserves_explicit),
    ("t06 apply_profile_defaults unknown no-op", t06_apply_profile_defaults_unknown_noop),
    ("t07 validate_profile_id", t07_validate_profile_id),
    ("t08 serialize_catalog shape + order", t08_serialize_catalog),
    ("t09 ProductCreate without profile_id (backward-compat)", t09_product_create_no_profile_is_backward_compat),
    ("t10 ProductCreate with profile fills axes", t10_product_create_with_profile_fills_axes),
    ("t11 ProductCreate explicit axes override profile", t11_product_create_explicit_axes_override_profile),
    ("t12 ProductCreate unknown profile rejected", t12_product_create_unknown_profile_rejected),
    ("t13 ProductUpdate optional profile_id", t13_product_update_accepts_profile_id_optional),
    ("t14 ProductUpdate unknown profile rejected", t14_product_update_unknown_profile_rejected),
    ("t15 pre-existing direct+inquiry still blocked", t15_existing_compat_check_still_active),
]


def run_all() -> int:
    passed = 0
    failed = 0
    for name, fn in TESTS:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {name}: {exc}")
            traceback.print_exc()
            failed += 1
    print()
    print(f"{passed}/{len(TESTS)} PASSED, {failed} FAILED")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all())
