#!/usr/bin/env python3
"""
E2E Test Suite — Simple Product Flow
=====================================
Tests the full commercial flow for physical products (fixed price, request mode):
  Storefront order → Admin states → Email triggers → Fulfillment → Cashflow → Customer dedup

Usage:
  cd backend && ./venv/bin/python tests/e2e_simple_product.py
"""

import asyncio
import sys
import os
import time
import logging
from datetime import datetime, date

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from database import sales_records_collection as sr_collection

# ── Config ───────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000/api"

# ── Test Report ──────────────────────────────────────────────────────────────
results = []
current_tc = ""

def assertion(label: str, condition: bool, detail: str = ""):
    status = "✅" if condition else "❌"
    results.append({"tc": current_tc, "label": label, "passed": condition, "detail": detail})
    print(f"  {status} {label}" + (f"  ({detail})" if detail and not condition else ""))
    return condition

def set_tc(name: str):
    global current_tc
    current_tc = name
    print(f"\n{'='*60}\n{name}\n{'='*60}")

def print_summary():
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)
    print(f"  Total: {total} | ✅ Passed: {passed} | ❌ Failed: {failed}")
    if failed > 0:
        print(f"\n  FAILURES:")
        for r in results:
            if not r["passed"]:
                print(f"    ❌ [{r['tc']}] {r['label']}: {r['detail']}")
    print(f"\n  Result: {'ALL PASSED ✅' if failed == 0 else f'{failed} FAILURES ❌'}")

# ── HTTP Client ──────────────────────────────────────────────────────────────

admin_token = None

def admin_headers():
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

def public_headers():
    return {"Content-Type": "application/json"}

# ── Phase 0: Reset + Seed ────────────────────────────────────────────────────

async def reset_and_seed(org_id: str):
    """Reset all transactional data and create test fixtures.
    org_id comes from create_test_org() — never the live user's org.
    """
    from database import (
        organizations_collection, orders_collection, customers_collection,
        products_collection, stores_collection, blocked_slots_collection,
        availability_rules_collection, customer_accounts_collection,
    )
    from database import sales_records_collection as sr_collection

    # Dynamic slug to avoid global unique index collision
    store_slug = f"e2e-{org_id[:8]}"

    print("\n🔄 PHASE 0: Reset + Seed")
    print("-" * 40)

    # Reset collections (harmless on fresh org, useful on re-run)
    for name, coll in [
        ("orders", orders_collection),
        ("customers", customers_collection),
        ("products", products_collection),
        ("stores", stores_collection),
        ("blocked_slots", blocked_slots_collection),
        ("availability_rules", availability_rules_collection),
        ("customer_accounts", customer_accounts_collection),
    ]:
        r = await coll.delete_many({"organization_id": org_id})
        print(f"  Cleared {name}: {r.deleted_count} docs")

    # Clear sales records
    r = await sr_collection.delete_many({"organization_id": org_id})
    print(f"  Cleared sales_records: {r.deleted_count} docs")

    # Clear event occurrences
    from database import db
    eo_coll = db.event_occurrences
    r = await eo_coll.delete_many({"organization_id": org_id})
    print(f"  Cleared event_occurrences: {r.deleted_count} docs")

    # Reset order counter
    counters_coll = db.order_counters
    await counters_coll.delete_many({"organization_id": org_id})
    print(f"  Cleared order_counters")

    # ── Seed store settings on test org ──
    await organizations_collection.update_one(
        {"id": org_id},
        {"$set": {
            "store_settings": {
                "display_name": "Bottega Demo",
                "contact_email": "bottega@test.com",
                "contact_phone": "+39 333 1234567",
                "notification_email": "admin@test.com",
                "reply_to_email": "bottega@test.com",
                "sender_display_name": "Bottega Demo",
                "fulfillment_modes": ["shipping", "local_pickup"],
                "is_storefront_published": True,
                "store_description": "Bottega artigianale per test E2E",
            }
        }}
    )
    print("  ✅ Store settings configured")

    # ── Seed store (multi-store) ──
    from models.common import generate_id, utc_now
    store_id = generate_id()
    await stores_collection.insert_one({
        "id": store_id,
        "organization_id": org_id,
        "slug": store_slug,
        "name": "Bottega Demo",
        "description": "Store di test per validazione E2E",
        "visibility": "public",
        "contact_email": "bottega@test.com",
        "contact_phone": "+39 333 1234567",
        "fulfillment_modes": ["shipping", "local_pickup"],
        "is_published": True,
        "is_default": True,
        "is_active": True,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    })
    print(f"  ✅ Store created: {store_slug} (id={store_id})")

    # ── Seed products ──
    product_ids = {}
    products = [
        {"key": "P1", "name": "Pane Casereccio", "unit_price": 4.50, "category": "Panetteria",
         "is_published": True, "item_type": "physical", "transaction_mode": "request", "price_mode": "fixed",
         "unit_label": "pz", "store_ids": [store_id]},
        {"key": "P2", "name": "Olio Extra Vergine 1L", "unit_price": 12.00, "category": "Alimentari",
         "is_published": True, "item_type": "physical", "transaction_mode": "request", "price_mode": "fixed",
         "unit_label": "bottiglia", "store_ids": [store_id]},
        {"key": "P3", "name": "Cesto Regalo Deluxe", "unit_price": 45.00, "category": "Regali",
         "is_published": True, "item_type": "physical", "transaction_mode": "request", "price_mode": "fixed",
         "unit_label": "pz", "store_ids": [store_id]},
        {"key": "P4", "name": "Prodotto Bozza", "unit_price": 10.00, "category": "Test",
         "is_published": False, "item_type": "physical", "transaction_mode": "request", "price_mode": "fixed",
         "unit_label": "pz", "store_ids": [store_id]},
    ]
    for p in products:
        pid = generate_id()
        product_ids[p["key"]] = pid
        await products_collection.insert_one({
            "id": pid,
            "organization_id": org_id,
            "name": p["name"],
            "unit_price": p["unit_price"],
            "category": p["category"],
            "is_published": p["is_published"],
            "item_type": p["item_type"],
            "transaction_mode": p["transaction_mode"],
            "price_mode": p["price_mode"],
            "unit_label": p["unit_label"],
            "store_ids": p.get("store_ids", []),
            "is_active": True,
            "description": f"Prodotto test: {p['name']}",
            "sku": None, "cost_price": None, "unit": None,
            "metadata": {},
            "created_at": utc_now(),
            "updated_at": utc_now(),
        })
        status = "📦" if p["is_published"] else "📝"
        print(f"  {status} Product {p['key']}: {p['name']} (€{p['unit_price']}) {'[published]' if p['is_published'] else '[draft]'}")

    print(f"\n  Seed complete. Product IDs: {product_ids}")
    return org_id, store_id, store_slug, product_ids


# ── Test Helpers ──────────────────────────────────────────────────────────────

async def get_db_order(order_id: str):
    from database import orders_collection
    return await orders_collection.find_one({"id": order_id}, {"_id": 0})

async def get_db_customer_by_email(org_id: str, email: str):
    from database import customers_collection
    return await customers_collection.find_one(
        {"organization_id": org_id, "email": email.lower()}, {"_id": 0})

async def get_sales_records_for_order(org_id: str, order_id: str):
    cursor = sr_collection.find(
        {"organization_id": org_id, "metadata.order_id": order_id}, {"_id": 0})
    return await cursor.to_list(100)

async def count_customers(org_id: str):
    from database import customers_collection
    return await customers_collection.count_documents({"organization_id": org_id})

async def count_orders_for_customer(org_id: str, customer_id: str):
    from database import orders_collection
    return await orders_collection.count_documents(
        {"organization_id": org_id, "customer_id": customer_id})


# ── Test Cases ────────────────────────────────────────────────────────────────

async def run_tests(org_id: str, store_id: str, store_slug: str, pids: dict,
                    admin_email: str, admin_password: str):
    global admin_token

    # Rate limit workaround: small delay between storefront requests
    async def storefront_post(client, json_data):
        """POST to storefront with rate-limit-aware delay."""
        await asyncio.sleep(0.3)  # space out requests
        return await client.post("/public/order-request", json=json_data, headers=public_headers())

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20.0) as client:

        # ── Login ──
        r = await client.post("/auth/login", json={"email": admin_email, "password": admin_password})
        assert r.status_code == 200, f"Login failed: {r.text}"
        admin_token = r.json()["access_token"]
        print("\n🔐 Admin logged in\n")

        # Keep track of IDs across tests
        tc01_order_id = None
        tc01_customer_id = None

        # ══════════════════════════════════════════════════════════════
        # TC-01: Full lifecycle draft → confirmed → completed
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-01: Full lifecycle draft → confirmed → completed")

        r = await client.post("/public/order-request", json={
            "slug": store_slug,
            "customer_name": "Mario Rossi",
            "customer_email": "mario@test.com",
            "customer_phone": "+39 333 0000001",
            "items": [{"product_id": pids["P1"], "quantity": 2}],
            "notes": None,
        }, headers=public_headers())
        assertion("Storefront order created", r.status_code in (200, 201), f"status={r.status_code} body={r.text[:200]}")

        if r.status_code in (200, 201):
            tc01_order_id = r.json().get("order_id") or r.json().get("id")
            assertion("Order ID returned", bool(tc01_order_id), f"id={tc01_order_id}")

            # Check DB state
            order = await get_db_order(tc01_order_id)
            assertion("Status is draft", order["status"] == "draft", f"status={order.get('status')}")
            assertion("Source is storefront", order["source"] == "storefront", f"source={order.get('source')}")
            assertion("Subtotal is 9.00", order["subtotal"] == 9.0, f"subtotal={order.get('subtotal')}")
            assertion("1 line item", len(order["items"]) == 1, f"items={len(order.get('items', []))}")

            # Check customer created
            cust = await get_db_customer_by_email(org_id, "mario@test.com")
            assertion("Customer mario@test.com created", cust is not None)
            if cust:
                tc01_customer_id = cust["id"]
                assertion("Customer has storefront source",
                          cust.get("metadata", {}).get("source") == "storefront",
                          f"metadata={cust.get('metadata')}")

            # Confirm
            r = await client.post(f"/orders/{tc01_order_id}/confirm", headers=admin_headers())
            assertion("Confirm succeeds", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

            order = await get_db_order(tc01_order_id)
            assertion("Status is confirmed", order["status"] == "confirmed")
            assertion("Order number assigned", order.get("order_number") is not None, f"number={order.get('order_number')}")

            # Check SalesRecord
            srs = await get_sales_records_for_order(org_id, tc01_order_id)
            assertion("1 SalesRecord created", len(srs) == 1, f"count={len(srs)}")
            if srs:
                assertion("SalesRecord amount=9.00", srs[0]["amount"] == 9.0, f"amount={srs[0]['amount']}")
                assertion("SalesRecord dataset_id=orders", srs[0]["dataset_id"] == "orders")
                assertion("SalesRecord customer_id linked", srs[0].get("customer_id") == tc01_customer_id,
                          f"sr_cust={srs[0].get('customer_id')} expected={tc01_customer_id}")

            # Complete
            r = await client.post(f"/orders/{tc01_order_id}/complete", headers=admin_headers())
            assertion("Complete succeeds", r.status_code == 200, f"status={r.status_code}")

            order = await get_db_order(tc01_order_id)
            assertion("Status is completed", order["status"] == "completed")
            assertion("Payment status is paid", order["payment_status"] == "paid")

            # No duplicate SalesRecords
            srs2 = await get_sales_records_for_order(org_id, tc01_order_id)
            assertion("No duplicate SalesRecords", len(srs2) == 1, f"count={len(srs2)}")

        # ══════════════════════════════════════════════════════════════
        # TC-02: Idempotent confirm
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-02: Idempotent confirm")

        if tc01_order_id:
            r = await client.post(f"/orders/{tc01_order_id}/confirm", headers=admin_headers())
            assertion("Re-confirm does not error", r.status_code == 200, f"status={r.status_code}")
            srs = await get_sales_records_for_order(org_id, tc01_order_id)
            assertion("Still only 1 SalesRecord", len(srs) == 1, f"count={len(srs)}")

        # ══════════════════════════════════════════════════════════════
        # TC-03: Cancel from draft (no storno)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-03: Cancel from draft (no storno)")

        r = await client.post("/public/order-request", json={
            "slug": store_slug,
            "customer_name": "Anna Neri",
            "customer_email": "anna@test.com",
            "items": [{"product_id": pids["P1"], "quantity": 1}],
        }, headers=public_headers())
        assertion("Order created", r.status_code in (200, 201))

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            r = await client.post(f"/orders/{oid}/cancel", headers=admin_headers())
            assertion("Cancel succeeds", r.status_code == 200)

            order = await get_db_order(oid)
            assertion("Status is cancelled", order["status"] == "cancelled")

            srs = await get_sales_records_for_order(org_id, oid)
            assertion("Zero SalesRecords (no storno)", len(srs) == 0, f"count={len(srs)}")

            cust = await get_db_customer_by_email(org_id, "anna@test.com")
            assertion("Customer anna@test.com exists anyway", cust is not None)

        # ══════════════════════════════════════════════════════════════
        # TC-04: Cancel from confirmed (storno)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-04: Cancel from confirmed (storno)")

        r = await client.post("/public/order-request", json={
            "slug": store_slug,
            "customer_name": "Luca Verdi",
            "customer_email": "luca@test.com",
            "items": [{"product_id": pids["P2"], "quantity": 3}],
        }, headers=public_headers())
        assertion("Order created", r.status_code in (200, 201))

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")

            r = await client.post(f"/orders/{oid}/confirm", headers=admin_headers())
            assertion("Confirm succeeds", r.status_code == 200)

            srs = await get_sales_records_for_order(org_id, oid)
            assertion("SalesRecord +36.00 created", len(srs) == 1 and srs[0]["amount"] == 36.0,
                      f"count={len(srs)} amount={srs[0]['amount'] if srs else 'N/A'}")

            r = await client.post(f"/orders/{oid}/cancel", headers=admin_headers())
            assertion("Cancel succeeds", r.status_code == 200)

            order = await get_db_order(oid)
            assertion("Status is cancelled", order["status"] == "cancelled")

            srs = await get_sales_records_for_order(org_id, oid)
            assertion("2 SalesRecords (original + storno)", len(srs) == 2, f"count={len(srs)}")
            storno = [s for s in srs if s["amount"] < 0]
            assertion("Storno record is -36.00", len(storno) == 1 and storno[0]["amount"] == -36.0,
                      f"storno={[s['amount'] for s in storno]}")
            if storno:
                assertion("Storno description contains 'Storno'", "Storno" in (storno[0].get("description") or ""),
                          f"desc={storno[0].get('description','')[:60]}")

        # ══════════════════════════════════════════════════════════════
        # TC-05: Completed order cannot be cancelled
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-05: Completed order cannot be cancelled")

        if tc01_order_id:
            r = await client.post(f"/orders/{tc01_order_id}/cancel", headers=admin_headers())
            assertion("Cancel returns 400", r.status_code == 400, f"status={r.status_code}")

        # ══════════════════════════════════════════════════════════════
        # TC-06: Draft order is editable (PATCH)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-06: Draft order is editable (PATCH)")

        r = await client.post("/public/order-request", json={
            "slug": store_slug,
            "customer_name": "Giulia Rosa",
            "customer_email": "giulia@test.com",
            "items": [{"product_id": pids["P1"], "quantity": 1}],
        }, headers=public_headers())
        assertion("Order created", r.status_code in (200, 201))

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")

            r = await client.patch(f"/orders/{oid}", json={
                "items": [{"product_id": pids["P2"], "quantity": 2}],
            }, headers=admin_headers())
            assertion("PATCH succeeds", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

            order = await get_db_order(oid)
            assertion("Updated subtotal=24.00", order["subtotal"] == 24.0, f"subtotal={order.get('subtotal')}")
            assertion("Items updated to P2", order["items"][0]["product_id"] == pids["P2"],
                      f"pid={order['items'][0].get('product_id')}")

            r = await client.post(f"/orders/{oid}/confirm", headers=admin_headers())
            assertion("Confirm updated order", r.status_code == 200)

            srs = await get_sales_records_for_order(org_id, oid)
            assertion("SalesRecord reflects 24.00", len(srs) == 1 and srs[0]["amount"] == 24.0,
                      f"amount={srs[0]['amount'] if srs else 'N/A'}")

        # ══════════════════════════════════════════════════════════════
        # TC-07: Multi-product order
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-07: Multi-product order")

        r = await client.post("/public/order-request", json={
            "slug": store_slug,
            "customer_name": "Giulia Bianchi",
            "customer_email": "giulia.b@test.com",
            "items": [
                {"product_id": pids["P2"], "quantity": 1},
                {"product_id": pids["P3"], "quantity": 1},
            ],
        }, headers=public_headers())
        assertion("Order created", r.status_code in (200, 201))

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            order = await get_db_order(oid)
            assertion("2 line items", len(order["items"]) == 2)
            assertion("Subtotal=57.00", order["subtotal"] == 57.0, f"subtotal={order.get('subtotal')}")

            r = await client.post(f"/orders/{oid}/confirm", headers=admin_headers())
            assertion("Confirm succeeds", r.status_code == 200)

            srs = await get_sales_records_for_order(org_id, oid)
            assertion("2 SalesRecords", len(srs) == 2, f"count={len(srs)}")
            amounts = sorted([s["amount"] for s in srs])
            assertion("Amounts are 12.00 and 45.00", amounts == [12.0, 45.0], f"amounts={amounts}")

        # ══════════════════════════════════════════════════════════════
        # TC-08: Returning customer (dedup)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-08: Returning customer (dedup)")

        cust_before = await get_db_customer_by_email(org_id, "mario@test.com")
        cust_count_before = await count_customers(org_id)

        r = await client.post("/public/order-request", json={
            "slug": store_slug,
            "customer_name": "Mario Rossi",
            "customer_email": "mario@test.com",
            "items": [{"product_id": pids["P3"], "quantity": 1}],
        }, headers=public_headers())
        assertion("Order created", r.status_code in (200, 201))

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            order = await get_db_order(oid)

            assertion("Same customer_id as TC-01", order["customer_id"] == tc01_customer_id,
                      f"got={order['customer_id']} expected={tc01_customer_id}")

            cust_count_after = await count_customers(org_id)
            assertion("No new customer created", cust_count_after == cust_count_before,
                      f"before={cust_count_before} after={cust_count_after}")

            r = await client.post(f"/orders/{oid}/confirm", headers=admin_headers())
            assertion("Confirm succeeds", r.status_code == 200)

            srs = await get_sales_records_for_order(org_id, oid)
            if srs:
                assertion("SalesRecord has same customer_id", srs[0]["customer_id"] == tc01_customer_id)

            mario_orders = await count_orders_for_customer(org_id, tc01_customer_id)
            assertion("Mario has multiple orders", mario_orders >= 2, f"orders={mario_orders}")

        # ══════════════════════════════════════════════════════════════
        # TC-09: Fulfillment lifecycle — Shipping
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-09: Fulfillment — Shipping")

        r = await client.post("/public/order-request", json={
            "slug": store_slug,
            "customer_name": "Paolo Gialli",
            "customer_email": "paolo@test.com",
            "items": [{"product_id": pids["P2"], "quantity": 2}],
            "fulfillment_mode": "shipping",
            "shipping_address": "Via Roma 1, 20100 Milano MI",
        }, headers=public_headers())
        assertion("Order created", r.status_code in (200, 201), f"status={r.status_code} body={r.text[:200]}")

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            order = await get_db_order(oid)
            ff = order.get("fulfillment") or {}
            assertion("Fulfillment mode=shipping", ff.get("mode") == "shipping", f"mode={ff.get('mode')}")
            assertion("Fulfillment status=pending", ff.get("status") == "pending", f"status={ff.get('status')}")
            assertion("Shipping address present", bool(ff.get("shipping_address")), f"addr={ff.get('shipping_address')}")

            r = await client.post(f"/orders/{oid}/confirm", headers=admin_headers())
            assertion("Confirm succeeds", r.status_code == 200)

            r = await client.post(f"/orders/{oid}/fulfillment", json={"status": "shipped"}, headers=admin_headers())
            assertion("Transition to shipped", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

            order = await get_db_order(oid)
            ff = order.get("fulfillment") or {}
            assertion("Status=shipped", ff.get("status") == "shipped")
            assertion("shipped_at populated", ff.get("shipped_at") is not None)

            r = await client.post(f"/orders/{oid}/fulfillment", json={"status": "delivered"}, headers=admin_headers())
            assertion("Transition to delivered", r.status_code == 200)

            order = await get_db_order(oid)
            ff = order.get("fulfillment") or {}
            assertion("Status=delivered", ff.get("status") == "delivered")
            assertion("delivered_at populated", ff.get("delivered_at") is not None)

        # ══════════════════════════════════════════════════════════════
        # TC-10: Fulfillment lifecycle — Local Pickup
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-10: Fulfillment — Local Pickup")

        r = await client.post("/public/order-request", json={
            "slug": store_slug,
            "customer_name": "Sara Blu",
            "customer_email": "sara@test.com",
            "items": [{"product_id": pids["P1"], "quantity": 1}],
            "fulfillment_mode": "local_pickup",
        }, headers=public_headers())
        assertion("Order created", r.status_code in (200, 201), f"status={r.status_code} body={r.text[:200]}")

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")

            r = await client.post(f"/orders/{oid}/confirm", headers=admin_headers())
            assertion("Confirm succeeds", r.status_code == 200)

            r = await client.post(f"/orders/{oid}/fulfillment", json={"status": "ready_for_pickup"}, headers=admin_headers())
            assertion("Transition to ready_for_pickup", r.status_code == 200, f"body={r.text[:200]}")

            r = await client.post(f"/orders/{oid}/fulfillment", json={"status": "picked_up"}, headers=admin_headers())
            assertion("Transition to picked_up", r.status_code == 200)

            order = await get_db_order(oid)
            ff = order.get("fulfillment") or {}
            assertion("Final status=picked_up", ff.get("status") == "picked_up")

        # ══════════════════════════════════════════════════════════════
        # TC-11: Email triggers (log verification)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-11: Email triggers (log check)")

        # Capture logs
        email_logger = logging.getLogger("services.order_email_service")
        email_logger.setLevel(logging.DEBUG)

        class LogCapture(logging.Handler):
            def __init__(self):
                super().__init__()
                self.records = []
            def emit(self, record):
                self.records.append(record.getMessage())

        capture = LogCapture()
        email_logger.addHandler(capture)

        # Also capture email_service logs
        svc_logger = logging.getLogger("services.email_service")
        svc_logger.setLevel(logging.DEBUG)
        svc_capture = LogCapture()
        svc_logger.addHandler(svc_capture)

        r = await client.post("/public/order-request", json={
            "slug": store_slug,
            "customer_name": "Email Test",
            "customer_email": "emailtest@test.com",
            "items": [{"product_id": pids["P1"], "quantity": 1}],
        }, headers=public_headers())

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            await asyncio.sleep(0.5)  # Let async email fire

            all_logs = " ".join(capture.records + svc_capture.records)
            assertion("Email log: order received or DRY RUN",
                      "emailtest@test.com" in all_logs or "DRY RUN" in all_logs or "order_email" in all_logs,
                      f"logs contain {len(capture.records)} email entries, {len(svc_capture.records)} svc entries")

            # Confirm
            capture.records.clear()
            svc_capture.records.clear()
            r = await client.post(f"/orders/{oid}/confirm", headers=admin_headers())
            await asyncio.sleep(0.5)

            all_logs = " ".join(capture.records + svc_capture.records)
            assertion("Email log: order confirmed trigger",
                      len(capture.records) > 0 or len(svc_capture.records) > 0 or "confirmed" in all_logs,
                      f"email entries={len(capture.records)} svc={len(svc_capture.records)}")

            # Cancel
            capture.records.clear()
            svc_capture.records.clear()
            r = await client.post(f"/orders/{oid}/cancel", headers=admin_headers())
            await asyncio.sleep(0.5)

            all_logs = " ".join(capture.records + svc_capture.records)
            assertion("Email log: order cancelled trigger",
                      len(capture.records) > 0 or len(svc_capture.records) > 0,
                      f"email entries={len(capture.records)} svc={len(svc_capture.records)}")

        email_logger.removeHandler(capture)
        svc_logger.removeHandler(svc_capture)

        # ══════════════════════════════════════════════════════════════
        # TC-12: Unpublished product rejected
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-12: Unpublished product rejected")

        r = await client.post("/public/order-request", json={
            "slug": store_slug,
            "customer_name": "Hacker",
            "customer_email": "hack@test.com",
            "items": [{"product_id": pids["P4"], "quantity": 1}],
        }, headers=public_headers())
        assertion("Rejected (not 200/201)", r.status_code not in (200, 201), f"status={r.status_code}")

        # ══════════════════════════════════════════════════════════════
        # TC-13: Cashflow aggregate verification
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-13: Cashflow aggregate verification")

        from database import sales_records_collection
        all_srs = await sales_records_collection.find(
            {"organization_id": org_id, "dataset_id": "orders"}, {"_id": 0}
        ).to_list(500)

        positive = sum(s["amount"] for s in all_srs if s["amount"] > 0)
        negative = sum(s["amount"] for s in all_srs if s["amount"] < 0)
        net = round(positive + negative, 2)

        assertion(f"Positive sales: {positive}", positive > 0)
        assertion(f"Storno total: {negative}", negative <= 0)
        print(f"  ℹ️  Net cashflow from orders: €{net}")

        # Check linkage — every SalesRecord has an order
        from database import orders_collection
        orphans = 0
        for sr in all_srs:
            oid = sr.get("metadata", {}).get("order_id")
            if oid:
                exists = await orders_collection.find_one({"id": oid}, {"_id": 0, "id": 1})
                if not exists:
                    orphans += 1
        assertion("No orphan SalesRecords", orphans == 0, f"orphans={orphans}")

        # Every confirmed order has SalesRecords
        confirmed_orders = await orders_collection.find(
            {"organization_id": org_id, "status": {"$in": ["confirmed", "completed"]}},
            {"_id": 0, "id": 1}
        ).to_list(100)
        missing_sr = 0
        for o in confirmed_orders:
            srs = await get_sales_records_for_order(org_id, o["id"])
            if len(srs) == 0:
                missing_sr += 1
        assertion("Every confirmed/completed order has SalesRecords", missing_sr == 0,
                  f"missing={missing_sr}/{len(confirmed_orders)}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("E2E TEST SUITE — Simple Product Flow")
    print("=" * 60)

    from tests.test_helpers import wait_for_backend, create_test_org, cleanup_test_org
    await wait_for_backend()

    # Create isolated test org
    creds = await create_test_org()
    org_id = creds["org_id"]

    try:
        # Phase 0: Reset + Seed
        org_id, store_id, store_slug, pids = await reset_and_seed(org_id)

        # Phase 1: Run tests
        await run_tests(org_id, store_id, store_slug, pids, creds["email"], creds["password"])

        # Summary
        print_summary()
    finally:
        await cleanup_test_org(org_id)

if __name__ == "__main__":
    asyncio.run(main())
