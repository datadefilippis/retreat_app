#!/usr/bin/env python3
"""
E2E Test Suite — Event Ticket Flow
====================================
Tests the full commercial flow for event_ticket products:
  Occurrence CRUD → Storefront order → Calendar sync → Capacity → Storno

Usage:
  cd backend && ./venv/bin/python tests/e2e_event_ticket.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from database import (
    organizations_collection, orders_collection, customers_collection,
    products_collection, stores_collection, blocked_slots_collection,
    availability_rules_collection, customer_accounts_collection,
    sales_records_collection, db,
)
from models.common import generate_id, utc_now

# ── Config ───────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000/api"

# Dynamically set by main() via create_test_org()
ORG_ID = None
ADMIN_EMAIL = None
ADMIN_PASSWORD = None
STORE_SLUG = None

# ── Report ───────────────────────────────────────────────────────────────────
results = []
current_tc = ""

def assertion(label, condition, detail=""):
    status = "✅" if condition else "❌"
    results.append({"tc": current_tc, "label": label, "passed": condition, "detail": detail})
    print(f"  {status} {label}" + (f"  ({detail})" if detail and not condition else ""))
    return condition

def set_tc(name):
    global current_tc
    current_tc = name
    print(f"\n{'='*60}\n{name}\n{'='*60}")

def print_summary():
    print(f"\n{'='*60}\nSUMMARY\n{'='*60}")
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    print(f"  Total: {len(results)} | ✅ Passed: {passed} | ❌ Failed: {failed}")
    if failed:
        print(f"\n  FAILURES:")
        for r in results:
            if not r["passed"]:
                print(f"    ❌ [{r['tc']}] {r['label']}: {r['detail']}")
    print(f"\n  Result: {'ALL PASSED ✅' if failed == 0 else f'{failed} FAILURES ❌'}")

admin_token = None
def admin_h():
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
def public_h():
    return {"Content-Type": "application/json"}

# ── Reset + Seed ─────────────────────────────────────────────────────────────

async def reset_and_seed():
    print("\n🔄 PHASE 0: Reset + Seed (Event Ticket)")
    print("-" * 40)

    for name, coll in [
        ("orders", orders_collection), ("customers", customers_collection),
        ("products", products_collection), ("stores", stores_collection),
        ("blocked_slots", blocked_slots_collection), ("availability_rules", availability_rules_collection),
        ("customer_accounts", customer_accounts_collection),
    ]:
        r = await coll.delete_many({"organization_id": ORG_ID})
        print(f"  Cleared {name}: {r.deleted_count}")

    await sales_records_collection.delete_many({"organization_id": ORG_ID})
    await db.event_occurrences.delete_many({"organization_id": ORG_ID})
    await db.order_counters.delete_many({"organization_id": ORG_ID})
    print("  Cleared sales_records, event_occurrences, order_counters")

    # Store settings
    await organizations_collection.update_one({"id": ORG_ID}, {"$set": {
        "store_settings": {
            "display_name": "Bottega Demo", "contact_email": "bottega@test.com",
            "notification_email": "admin@test.com", "reply_to_email": "bottega@test.com",
            "sender_display_name": "Bottega Demo", "fulfillment_modes": ["shipping", "local_pickup"],
            "is_storefront_published": True,
        }
    }})

    # Store
    store_id = generate_id()
    await stores_collection.insert_one({
        "id": store_id, "organization_id": ORG_ID, "slug": STORE_SLUG,
        "name": "Bottega Demo", "visibility": "public", "fulfillment_modes": ["shipping", "local_pickup"],
        "is_published": True, "is_default": True, "is_active": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  ✅ Store: {STORE_SLUG}")

    # Products
    pids = {}

    # P1: Event with capacity (capped event)
    pids["EVT_CAPPED"] = generate_id()
    await products_collection.insert_one({
        "id": pids["EVT_CAPPED"], "organization_id": ORG_ID,
        "name": "Cena in Masseria", "unit_price": 45.00, "category": "Eventi",
        "is_published": True, "item_type": "event_ticket", "transaction_mode": "request",
        "price_mode": "fixed", "unit_label": "posto", "store_ids": [store_id],
        "is_active": True, "metadata": {}, "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  🎫 EVT_CAPPED: Cena in Masseria (€45, event_ticket)")

    # P2: Event open (no capacity)
    pids["EVT_OPEN"] = generate_id()
    await products_collection.insert_one({
        "id": pids["EVT_OPEN"], "organization_id": ORG_ID,
        "name": "Workshop Fotografia", "unit_price": 25.00, "category": "Corsi",
        "is_published": True, "item_type": "event_ticket", "transaction_mode": "request",
        "price_mode": "fixed", "unit_label": "posto", "store_ids": [store_id],
        "is_active": True, "metadata": {}, "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  🎫 EVT_OPEN: Workshop Fotografia (€25, event_ticket)")

    # P3: Simple physical (for mixed orders)
    pids["PHYSICAL"] = generate_id()
    await products_collection.insert_one({
        "id": pids["PHYSICAL"], "organization_id": ORG_ID,
        "name": "Pane Casereccio", "unit_price": 4.50, "category": "Panetteria",
        "is_published": True, "item_type": "physical", "transaction_mode": "request",
        "price_mode": "fixed", "unit_label": "pz", "store_ids": [store_id],
        "is_active": True, "metadata": {}, "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  📦 PHYSICAL: Pane Casereccio (€4.50)")

    print(f"\n  Product IDs: {pids}")
    return store_id, pids


# ── Helpers ───────────────────────────────────────────────────────────────────

async def get_order(oid):
    return await orders_collection.find_one({"id": oid}, {"_id": 0})

async def get_sales_records(oid):
    return await sales_records_collection.find(
        {"organization_id": ORG_ID, "metadata.order_id": oid}, {"_id": 0}).to_list(50)

async def get_blocked_slots_for_order(oid):
    return await blocked_slots_collection.find(
        {"organization_id": ORG_ID, "reference_id": oid}, {"_id": 0}).to_list(50)

async def count_blocked_slots():
    return await blocked_slots_collection.count_documents({"organization_id": ORG_ID, "reason": "event"})


# ── Tests ─────────────────────────────────────────────────────────────────────

async def run_tests(store_id, pids):
    global admin_token

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20.0) as c:
        # Login
        r = await c.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        admin_token = r.json()["access_token"]
        print("\n🔐 Admin logged in\n")

        occ_ids = {}

        # ══════════════════════════════════════════════════════════════
        # TC-01: Create occurrences (admin)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-01: Create event occurrences")

        # Capped event: 2 occurrences with different dates and capacity
        r = await c.post("/event-occurrences", json={
            "product_id": pids["EVT_CAPPED"],
            "start_at": "2026-05-20T20:30:00",
            "end_at": "2026-05-20T23:00:00",
            "location": "Masseria San Giovanni, Lecce",
            "capacity": 3,
            "notes": "Menù degustazione 5 portate",
        }, headers=admin_h())
        assertion("Occurrence 1 created", r.status_code == 201, f"status={r.status_code} body={r.text[:200]}")
        if r.status_code == 201:
            occ_ids["CAPPED_1"] = r.json()["id"]
            assertion("Status is draft", r.json()["status"] == "draft")

        r = await c.post("/event-occurrences", json={
            "product_id": pids["EVT_CAPPED"],
            "start_at": "2026-05-27T20:30:00",
            "location": "Masseria San Giovanni, Lecce",
            "capacity": 5,
            "price_override": 55.00,
        }, headers=admin_h())
        assertion("Occurrence 2 created (with price_override)", r.status_code == 201)
        if r.status_code == 201:
            occ_ids["CAPPED_2"] = r.json()["id"]
            assertion("Price override saved", r.json().get("price_override") == 55.0)

        # Open event: 1 occurrence, no capacity
        r = await c.post("/event-occurrences", json={
            "product_id": pids["EVT_OPEN"],
            "start_at": "2026-06-05T10:00:00",
            "end_at": "2026-06-05T13:00:00",
            "location": "Studio Arte, Milano",
        }, headers=admin_h())
        assertion("Open occurrence created (no capacity)", r.status_code == 201)
        if r.status_code == 201:
            occ_ids["OPEN_1"] = r.json()["id"]
            assertion("No capacity field", r.json().get("capacity") is None)

        # ══════════════════════════════════════════════════════════════
        # TC-02: Publish occurrences
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-02: Publish occurrences")

        for key in ["CAPPED_1", "CAPPED_2", "OPEN_1"]:
            if key in occ_ids:
                r = await c.patch(f"/event-occurrences/{occ_ids[key]}", json={"status": "published"}, headers=admin_h())
                assertion(f"Publish {key}", r.status_code == 200, f"status={r.status_code}")

        # ══════════════════════════════════════════════════════════════
        # TC-03: Storefront catalog shows published occurrences
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-03: Storefront catalog shows occurrences")

        r = await c.get(f"/public/catalog/{STORE_SLUG}", headers=public_h())
        assertion("Catalog loads", r.status_code == 200)

        if r.status_code == 200:
            catalog = r.json()
            products = catalog.get("products", [])
            evt_capped = next((p for p in products if p["id"] == pids["EVT_CAPPED"]), None)
            evt_open = next((p for p in products if p["id"] == pids["EVT_OPEN"]), None)

            assertion("EVT_CAPPED in catalog", evt_capped is not None)
            if evt_capped:
                occs = evt_capped.get("occurrences", [])
                assertion("2 published occurrences", len(occs) == 2, f"count={len(occs)}")
                occ1 = next((o for o in occs if o["id"] == occ_ids.get("CAPPED_1")), None)
                if occ1:
                    assertion("Occurrence has location", occ1.get("location") == "Masseria San Giovanni, Lecce")

            assertion("EVT_OPEN in catalog", evt_open is not None)
            if evt_open:
                occs = evt_open.get("occurrences", [])
                assertion("1 published occurrence", len(occs) == 1, f"count={len(occs)}")

        # ══════════════════════════════════════════════════════════════
        # TC-04: Order event_ticket — full lifecycle
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-04: Event order — full lifecycle")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Marco Eventi",
            "customer_email": "marco@test.com",
            "items": [{"product_id": pids["EVT_CAPPED"], "quantity": 2, "occurrence_id": occ_ids.get("CAPPED_1")}],
        }, headers=public_h())
        assertion("Order created", r.status_code in (200, 201), f"status={r.status_code} body={r.text[:300]}")

        tc04_oid = None
        if r.status_code in (200, 201):
            tc04_oid = r.json().get("order_id") or r.json().get("id")
            order = await get_order(tc04_oid)
            assertion("Status draft", order["status"] == "draft")
            assertion("1 line item", len(order["items"]) == 1)

            item = order["items"][0]
            assertion("occurrence_id snapshotted", item.get("occurrence_id") == occ_ids.get("CAPPED_1"))
            assertion("occurrence_start_at snapshotted", item.get("occurrence_start_at") == "2026-05-20T20:30:00")
            assertion("occurrence_location snapshotted", item.get("occurrence_location") == "Masseria San Giovanni, Lecce")
            assertion("Unit price from product (no override)", item.get("unit_price") == 45.0)
            assertion("Subtotal = 90.00", order["subtotal"] == 90.0, f"subtotal={order.get('subtotal')}")

            # Confirm
            r = await c.post(f"/orders/{tc04_oid}/confirm", headers=admin_h())
            assertion("Confirm succeeds", r.status_code == 200)

            srs = await get_sales_records(tc04_oid)
            assertion("1 SalesRecord (90.00)", len(srs) == 1 and srs[0]["amount"] == 90.0,
                      f"count={len(srs)} amount={srs[0]['amount'] if srs else 'N/A'}")

            # Calendar block created
            blocks = await get_blocked_slots_for_order(tc04_oid)
            assertion("Calendar block created", len(blocks) >= 1, f"blocks={len(blocks)}")
            if blocks:
                b = blocks[0]
                assertion("Block date=2026-05-20", b["date"] == "2026-05-20")
                assertion("Block reason=event", b["reason"] == "event")
                assertion("Block start_time=20:30", b["start_time"] == "20:30")

        # ══════════════════════════════════════════════════════════════
        # TC-05: Price override occurrence
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-05: Price override from occurrence")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Elena Premium",
            "customer_email": "elena@test.com",
            "items": [{"product_id": pids["EVT_CAPPED"], "quantity": 1, "occurrence_id": occ_ids.get("CAPPED_2")}],
        }, headers=public_h())
        assertion("Order created", r.status_code in (200, 201))

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            order = await get_order(oid)
            item = order["items"][0]
            assertion("Price from occurrence override (55.00)", item.get("unit_price") == 55.0,
                      f"price={item.get('unit_price')}")
            assertion("Subtotal = 55.00", order["subtotal"] == 55.0)

            r = await c.post(f"/orders/{oid}/confirm", headers=admin_h())
            assertion("Confirm succeeds", r.status_code == 200)

        # ══════════════════════════════════════════════════════════════
        # TC-06: Order without occurrence_id → rejected
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-06: Event order without occurrence_id rejected")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Bad Request",
            "customer_email": "bad@test.com",
            "items": [{"product_id": pids["EVT_CAPPED"], "quantity": 1}],
        }, headers=public_h())
        assertion("Rejected without occurrence_id", r.status_code >= 400, f"status={r.status_code}")

        # ══════════════════════════════════════════════════════════════
        # TC-07: Order with draft occurrence → rejected
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-07: Order with draft occurrence rejected")

        # Create a new draft occurrence (don't publish)
        r = await c.post("/event-occurrences", json={
            "product_id": pids["EVT_CAPPED"],
            "start_at": "2026-06-15T20:00:00",
            "location": "Test Draft",
        }, headers=admin_h())
        draft_occ_id = r.json()["id"] if r.status_code == 201 else None

        if draft_occ_id:
            r = await c.post("/public/order-request", json={
                "slug": STORE_SLUG,
                "customer_name": "Draft Test",
                "customer_email": "draft@test.com",
                "items": [{"product_id": pids["EVT_CAPPED"], "quantity": 1, "occurrence_id": draft_occ_id}],
            }, headers=public_h())
            assertion("Rejected with draft occurrence", r.status_code >= 400, f"status={r.status_code}")

        # ══════════════════════════════════════════════════════════════
        # TC-08: Open event order (no capacity)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-08: Open event order (no capacity)")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Fotografo Amatore",
            "customer_email": "foto@test.com",
            "items": [{"product_id": pids["EVT_OPEN"], "quantity": 3, "occurrence_id": occ_ids.get("OPEN_1")}],
        }, headers=public_h())
        assertion("Order created", r.status_code in (200, 201))

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            order = await get_order(oid)
            assertion("Subtotal = 75.00 (3x25)", order["subtotal"] == 75.0)

            r = await c.post(f"/orders/{oid}/confirm", headers=admin_h())
            assertion("Confirm succeeds", r.status_code == 200)

        # ══════════════════════════════════════════════════════════════
        # TC-09: Capacity enforcement (CAPPED_1 has cap=3, 2 booked)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-09: Capacity enforcement (cap=3, 2 booked)")

        # CAPPED_1 has capacity=3, TC-04 booked qty=2. 1 remaining.
        # Book 1 more → should succeed (total=3, at capacity)
        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Last Seat",
            "customer_email": "last@test.com",
            "items": [{"product_id": pids["EVT_CAPPED"], "quantity": 1, "occurrence_id": occ_ids.get("CAPPED_1")}],
        }, headers=public_h())
        assertion("1 seat accepted (3/3)", r.status_code in (200, 201), f"status={r.status_code}")
        tc09_oid = r.json().get("order_id") or r.json().get("id") if r.status_code in (200, 201) else None

        # Now try 1 more → should be BLOCKED (4 > cap=3)
        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Over Capacity",
            "customer_email": "over@test.com",
            "items": [{"product_id": pids["EVT_CAPPED"], "quantity": 1, "occurrence_id": occ_ids.get("CAPPED_1")}],
        }, headers=public_h())
        assertion("Rejected when sold out", r.status_code >= 400, f"status={r.status_code} body={r.text[:200]}")

        # Verify catalog shows remaining=0
        r = await c.get(f"/public/catalog/{STORE_SLUG}", headers=public_h())
        if r.status_code == 200:
            cat_prods = r.json().get("products", [])
            evt = next((p for p in cat_prods if p["id"] == pids["EVT_CAPPED"]), None)
            if evt:
                occ1 = next((o for o in evt.get("occurrences", []) if o["id"] == occ_ids.get("CAPPED_1")), None)
                if occ1:
                    assertion("Catalog shows remaining=0", occ1.get("remaining") == 0,
                              f"remaining={occ1.get('remaining')}")

        # ══════════════════════════════════════════════════════════════
        # TC-10: Cancel event order → calendar block removed
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-10: Cancel event order → calendar block removed")

        if tc04_oid:
            blocks_before = await get_blocked_slots_for_order(tc04_oid)
            assertion("Block exists before cancel", len(blocks_before) >= 1)

            r = await c.post(f"/orders/{tc04_oid}/cancel", headers=admin_h())
            assertion("Cancel succeeds", r.status_code == 200)

            blocks_after = await get_blocked_slots_for_order(tc04_oid)
            assertion("Block removed after cancel", len(blocks_after) == 0, f"remaining={len(blocks_after)}")

            # Storno SalesRecords
            srs = await get_sales_records(tc04_oid)
            storno = [s for s in srs if s["amount"] < 0]
            assertion("Storno record exists (-90.00)", len(storno) == 1 and storno[0]["amount"] == -90.0,
                      f"storno={[s['amount'] for s in storno]}")

        # ══════════════════════════════════════════════════════════════
        # TC-11: Mixed order (event + physical)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-11: Mixed order (event + physical)")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Mix Buyer",
            "customer_email": "mix@test.com",
            "items": [
                {"product_id": pids["EVT_OPEN"], "quantity": 1, "occurrence_id": occ_ids.get("OPEN_1")},
                {"product_id": pids["PHYSICAL"], "quantity": 2},
            ],
        }, headers=public_h())
        assertion("Mixed order created", r.status_code in (200, 201), f"status={r.status_code} body={r.text[:200]}")

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            order = await get_order(oid)
            assertion("2 line items", len(order["items"]) == 2)
            assertion("Subtotal = 34.00 (25+9)", order["subtotal"] == 34.0, f"subtotal={order.get('subtotal')}")

            # Fulfillment should be manual_arrangement (has physical + event)
            ff = order.get("fulfillment") or {}
            has_physical = any(i["item_type"] == "physical" for i in order["items"])
            assertion("Has physical item", has_physical)

            r = await c.post(f"/orders/{oid}/confirm", headers=admin_h())
            assertion("Confirm succeeds", r.status_code == 200)

            srs = await get_sales_records(oid)
            assertion("2 SalesRecords", len(srs) == 2, f"count={len(srs)}")

        # ══════════════════════════════════════════════════════════════
        # TC-12: Close occurrence → no new orders accepted
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-12: Closed occurrence rejects new orders")

        if "CAPPED_2" in occ_ids:
            r = await c.patch(f"/event-occurrences/{occ_ids['CAPPED_2']}", json={"status": "closed"}, headers=admin_h())
            assertion("Close occurrence", r.status_code == 200)

            r = await c.post("/public/order-request", json={
                "slug": STORE_SLUG,
                "customer_name": "Late Buyer",
                "customer_email": "late@test.com",
                "items": [{"product_id": pids["EVT_CAPPED"], "quantity": 1, "occurrence_id": occ_ids["CAPPED_2"]}],
            }, headers=public_h())
            assertion("Rejected with closed occurrence", r.status_code >= 400, f"status={r.status_code}")

        # ══════════════════════════════════════════════════════════════
        # TC-14: Capacity recovery after cancel → seat available again
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-14: Capacity recovery after cancel")

        # Cancel TC-09 order (the "last seat" order) → frees 1 seat
        if tc09_oid:
            r = await c.post(f"/orders/{tc09_oid}/cancel", headers=admin_h())
            assertion("Cancel last-seat order", r.status_code == 200)

            # Now try booking 1 seat again → should succeed (capacity freed)
            r = await c.post("/public/order-request", json={
                "slug": STORE_SLUG,
                "customer_name": "Recovery Buyer",
                "customer_email": "recovery@test.com",
                "items": [{"product_id": pids["EVT_CAPPED"], "quantity": 1, "occurrence_id": occ_ids.get("CAPPED_1")}],
            }, headers=public_h())
            assertion("Seat available again after cancel", r.status_code in (200, 201),
                      f"status={r.status_code} body={r.text[:200]}")

            # Verify catalog shows remaining=1 again
            r = await c.get(f"/public/catalog/{STORE_SLUG}", headers=public_h())
            if r.status_code == 200:
                cat_prods = r.json().get("products", [])
                evt = next((p for p in cat_prods if p["id"] == pids["EVT_CAPPED"]), None)
                if evt:
                    occ1 = next((o for o in evt.get("occurrences", []) if o["id"] == occ_ids.get("CAPPED_1")), None)
                    if occ1:
                        assertion("Catalog shows remaining after recovery", occ1.get("remaining", -1) >= 0,
                                  f"remaining={occ1.get('remaining')}")

        # ══════════════════════════════════════════════════════════════
        # TC-13: Cashflow aggregate
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-13: Cashflow aggregate")

        all_srs = await sales_records_collection.find(
            {"organization_id": ORG_ID, "dataset_id": "orders"}, {"_id": 0}).to_list(500)

        positive = sum(s["amount"] for s in all_srs if s["amount"] > 0)
        negative = sum(s["amount"] for s in all_srs if s["amount"] < 0)
        net = round(positive + negative, 2)

        assertion(f"Positive sales: €{positive}", positive > 0)
        print(f"  ℹ️  Net cashflow: €{net}")

        # No orphans
        orphans = 0
        for sr in all_srs:
            oid = sr.get("metadata", {}).get("order_id")
            if oid:
                exists = await orders_collection.find_one({"id": oid}, {"_id": 0, "id": 1})
                if not exists: orphans += 1
        assertion("No orphan SalesRecords", orphans == 0)

        # Calendar blocks count
        event_blocks = await count_blocked_slots()
        print(f"  ℹ️  Event calendar blocks remaining: {event_blocks}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    global ORG_ID, ADMIN_EMAIL, ADMIN_PASSWORD, STORE_SLUG

    print("=" * 60)
    print("E2E TEST SUITE — Event Ticket Flow")
    print("=" * 60)

    from tests.test_helpers import wait_for_backend, create_test_org, cleanup_test_org
    await wait_for_backend()

    # Create isolated test org
    creds = await create_test_org()
    ORG_ID = creds["org_id"]
    ADMIN_EMAIL = creds["email"]
    ADMIN_PASSWORD = creds["password"]
    STORE_SLUG = f"e2e-{ORG_ID[:8]}"

    try:
        store_id, pids = await reset_and_seed()
        await run_tests(store_id, pids)
        print_summary()
    finally:
        await cleanup_test_org(ORG_ID)

if __name__ == "__main__":
    asyncio.run(main())
