#!/usr/bin/env python3
"""
E2E Test Suite — Rental Flow
==============================
Tests: rental order → fulfillment manual_arrangement → review flag →
       calendar visibility → cancel/storno → mixed orders

Usage:
  cd backend && ./venv/bin/python tests/e2e_rental.py
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
    print("\n🔄 PHASE 0: Reset + Seed (Rental)")
    print("-" * 40)

    for name, coll in [
        ("orders", orders_collection), ("customers", customers_collection),
        ("products", products_collection), ("stores", stores_collection),
        ("blocked_slots", blocked_slots_collection),
        ("availability_rules", availability_rules_collection),
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
            "display_name": "Noleggio Attrezzature", "contact_email": "noleggio@test.com",
            "notification_email": "admin@test.com", "reply_to_email": "noleggio@test.com",
            "sender_display_name": "Noleggio Attrezzature",
            "fulfillment_modes": ["shipping", "local_pickup"],
            "is_storefront_published": True,
        }
    }})

    store_id = generate_id()
    await stores_collection.insert_one({
        "id": store_id, "organization_id": ORG_ID, "slug": STORE_SLUG,
        "name": "Noleggio Attrezzature", "visibility": "public",
        "fulfillment_modes": ["shipping", "local_pickup"],
        "is_published": True, "is_default": True, "is_active": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  ✅ Store: {STORE_SLUG}")

    pids = {}

    pids["RENTAL_DAY"] = generate_id()
    await products_collection.insert_one({
        "id": pids["RENTAL_DAY"], "organization_id": ORG_ID,
        "name": "Trapano Professionale", "unit_price": 25.00, "category": "Utensili",
        "is_published": True, "item_type": "rental", "transaction_mode": "approval",
        "price_mode": "fixed", "unit_label": "giorno", "store_ids": [store_id],
        "is_active": True, "metadata": {"rental_unit": "giorno"},
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  🔧 RENTAL_DAY: Trapano Professionale (€25/giorno, rental)")

    pids["RENTAL_WEEK"] = generate_id()
    await products_collection.insert_one({
        "id": pids["RENTAL_WEEK"], "organization_id": ORG_ID,
        "name": "Generatore Elettrico", "unit_price": 150.00, "category": "Energia",
        "is_published": True, "item_type": "rental", "transaction_mode": "approval",
        "price_mode": "fixed", "unit_label": "settimana", "store_ids": [store_id],
        "is_active": True, "metadata": {"rental_unit": "settimana"},
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  ⚡ RENTAL_WEEK: Generatore Elettrico (€150/settimana, rental)")

    pids["PHYSICAL"] = generate_id()
    await products_collection.insert_one({
        "id": pids["PHYSICAL"], "organization_id": ORG_ID,
        "name": "Guanti Lavoro", "unit_price": 8.00, "category": "Accessori",
        "is_published": True, "item_type": "physical", "transaction_mode": "request",
        "price_mode": "fixed", "unit_label": "paio", "store_ids": [store_id],
        "is_active": True, "metadata": {}, "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  📦 PHYSICAL: Guanti Lavoro (€8)")

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


# ── Tests ─────────────────────────────────────────────────────────────────────

async def run_tests(store_id, pids):
    global admin_token

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20.0) as c:
        r = await c.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        admin_token = r.json()["access_token"]
        print("\n🔐 Admin logged in\n")

        # ══════════════════════════════════════════════════════════════
        # TC-01: Rental order — full lifecycle
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-01: Rental order full lifecycle")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Mario Noleggio",
            "customer_email": "mario.r@test.com",
            "customer_phone": "+39 333 2222222",
            "items": [{
                "product_id": pids["RENTAL_DAY"], "quantity": 1,
                "rental_date_from": "2026-06-01",
                "rental_date_to": "2026-06-05",
                "rental_notes": "Serve per ristrutturazione bagno",
            }],
        }, headers=public_h())
        assertion("Order created", r.status_code in (200, 201), f"status={r.status_code} body={r.text[:300]}")

        tc01_oid = None
        if r.status_code in (200, 201):
            tc01_oid = r.json().get("order_id") or r.json().get("id")
            order = await get_order(tc01_oid)

            assertion("Status draft", order["status"] == "draft")
            assertion("Source storefront", order["source"].startswith("storefront"))

            item = order["items"][0]
            assertion("item_type=rental", item["item_type"] == "rental")
            assertion("rental_date_from snapshotted", item["rental_date_from"] == "2026-06-01")
            assertion("rental_date_to snapshotted", item["rental_date_to"] == "2026-06-05")
            assertion("rental_notes snapshotted", item["rental_notes"] == "Serve per ristrutturazione bagno")
            assertion("Subtotal=25.00", order["subtotal"] == 25.0)

            # Fulfillment = manual_arrangement (forced for rental)
            ff = order.get("fulfillment") or {}
            assertion("Fulfillment mode=manual_arrangement", ff.get("mode") == "manual_arrangement",
                      f"mode={ff.get('mode')}")
            assertion("Fulfillment status=pending", ff.get("status") == "pending")

            # Confirm
            r = await c.post(f"/orders/{tc01_oid}/confirm", headers=admin_h())
            assertion("Confirm succeeds", r.status_code == 200)

            # SalesRecord
            srs = await get_sales_records(tc01_oid)
            assertion("1 SalesRecord (25.00)", len(srs) == 1 and srs[0]["amount"] == 25.0)

            # Calendar blocks for rental: one per day in range (1 Jun → 5 Jun = 5 days)
            blocks = await get_blocked_slots_for_order(tc01_oid)
            assertion("Calendar blocks created (5 days)", len(blocks) == 5, f"blocks={len(blocks)}")
            if blocks:
                dates = sorted([b["date"] for b in blocks])
                assertion("First block = 2026-06-01", dates[0] == "2026-06-01")
                assertion("Last block = 2026-06-05", dates[-1] == "2026-06-05")
                assertion("All blocks reason=rental", all(b["reason"] == "rental" for b in blocks))
                assertion("All blocks full day (00:00-23:59)",
                          all(b["start_time"] == "00:00" and b["end_time"] == "23:59" for b in blocks))

            # Complete
            r = await c.post(f"/orders/{tc01_oid}/complete", headers=admin_h())
            assertion("Complete succeeds", r.status_code == 200)

            order = await get_order(tc01_oid)
            assertion("Status completed", order["status"] == "completed")
            assertion("Payment paid", order["payment_status"] == "paid")

        # ══════════════════════════════════════════════════════════════
        # TC-02: Rental without date_from → rejected
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-02: Rental without date_from rejected")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Bad Rental",
            "customer_email": "bad@test.com",
            "items": [{"product_id": pids["RENTAL_DAY"], "quantity": 1}],
        }, headers=public_h())
        assertion("Rejected without date_from", r.status_code >= 400, f"status={r.status_code}")

        # ══════════════════════════════════════════════════════════════
        # TC-03: Rental with date_from only (no date_to)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-03: Rental with date_from only")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Single Date",
            "customer_email": "single@test.com",
            "items": [{
                "product_id": pids["RENTAL_DAY"], "quantity": 1,
                "rental_date_from": "2026-07-10",
            }],
        }, headers=public_h())
        assertion("Accepted with date_from only", r.status_code in (200, 201))

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            order = await get_order(oid)
            item = order["items"][0]
            assertion("date_to is null", item.get("rental_date_to") is None)

        # ══════════════════════════════════════════════════════════════
        # TC-04: Review flag for rental orders
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-04: Review flag for rental orders")

        r = await c.get("/orders", headers=admin_h())
        if r.status_code == 200:
            orders_list = r.json().get("orders", [])
            draft_rental = next((o for o in orders_list
                if o["status"] == "draft"
                and any(it.get("item_type") == "rental" for it in o.get("items", []))
            ), None)
            if draft_rental:
                # Rental with transaction_mode=approval → review state is needs_approval (approval takes priority)
                # Rental with transaction_mode=request → review state is needs_review / rental_availability
                has_review = draft_rental.get("review_state") is not None
                assertion("Has review state (needs operator attention)", has_review,
                          f"state={draft_rental.get('review_state')} reason={draft_rental.get('review_reason')}")
                assertion("Review state is actionable",
                          draft_rental.get("review_state") in ("needs_review", "needs_approval"),
                          f"state={draft_rental.get('review_state')}")
            else:
                assertion("Draft rental found for review check", False, "no draft rental in list")

        # ══════════════════════════════════════════════════════════════
        # TC-05: Cancel rental → storno
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-05: Cancel confirmed rental → storno + blocks removed")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Cancel Rental",
            "customer_email": "cancel.r@test.com",
            "items": [{
                "product_id": pids["RENTAL_WEEK"], "quantity": 1,
                "rental_date_from": "2026-08-01",
                "rental_date_to": "2026-08-07",
            }],
        }, headers=public_h())

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            await c.post(f"/orders/{oid}/confirm", headers=admin_h())

            # Verify blocks created (7 days: Aug 1-7)
            blocks = await get_blocked_slots_for_order(oid)
            assertion("Calendar blocks created (7 days)", len(blocks) == 7, f"blocks={len(blocks)}")

            srs_before = await get_sales_records(oid)
            assertion("SalesRecord +150.00", len(srs_before) == 1 and srs_before[0]["amount"] == 150.0)

            r = await c.post(f"/orders/{oid}/cancel", headers=admin_h())
            assertion("Cancel succeeds", r.status_code == 200)

            # Verify blocks removed
            blocks_after = await get_blocked_slots_for_order(oid)
            assertion("All blocks removed after cancel", len(blocks_after) == 0, f"remaining={len(blocks_after)}")

            srs_after = await get_sales_records(oid)
            storno = [s for s in srs_after if s["amount"] < 0]
            assertion("Storno record (-150.00)", len(storno) == 1 and storno[0]["amount"] == -150.0)

        # ══════════════════════════════════════════════════════════════
        # TC-06: Mixed order (rental + physical)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-06: Mixed order rental + physical")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Mix Rental",
            "customer_email": "mix.r@test.com",
            "items": [
                {
                    "product_id": pids["RENTAL_DAY"], "quantity": 1,
                    "rental_date_from": "2026-09-01",
                    "rental_date_to": "2026-09-03",
                },
                {"product_id": pids["PHYSICAL"], "quantity": 3},
            ],
        }, headers=public_h())
        assertion("Mixed order created", r.status_code in (200, 201))

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            order = await get_order(oid)
            assertion("2 line items", len(order["items"]) == 2)
            assertion("Subtotal = 49.00 (25+24)", order["subtotal"] == 49.0,
                      f"subtotal={order.get('subtotal')}")

            # Fulfillment forced to manual_arrangement (rental rule)
            ff = order.get("fulfillment") or {}
            assertion("Fulfillment forced manual_arrangement", ff.get("mode") == "manual_arrangement",
                      f"mode={ff.get('mode')}")

            r = await c.post(f"/orders/{oid}/confirm", headers=admin_h())
            assertion("Confirm succeeds", r.status_code == 200)

            srs = await get_sales_records(oid)
            assertion("2 SalesRecords", len(srs) == 2)

        # ══════════════════════════════════════════════════════════════
        # TC-07: Fulfillment lifecycle (manual_arrangement)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-07: Fulfillment manual_arrangement lifecycle")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "FF Rental",
            "customer_email": "ff.r@test.com",
            "items": [{
                "product_id": pids["RENTAL_DAY"], "quantity": 2,
                "rental_date_from": "2026-10-01",
                "rental_date_to": "2026-10-05",
            }],
        }, headers=public_h())

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            await c.post(f"/orders/{oid}/confirm", headers=admin_h())

            r = await c.post(f"/orders/{oid}/fulfillment", json={"status": "fulfilled"}, headers=admin_h())
            assertion("Transition to fulfilled", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

            order = await get_order(oid)
            ff = order.get("fulfillment") or {}
            assertion("Fulfillment status=fulfilled", ff.get("status") == "fulfilled")

        # ══════════════════════════════════════════════════════════════
        # TC-08: Calendar visibility
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-08: Calendar shows rental orders")

        r = await c.get("/calendar/items", params={"year": 2026, "month": 6}, headers=admin_h())
        assertion("Calendar loads", r.status_code == 200)

        if r.status_code == 200:
            items = r.json().get("items", [])
            rental_items = [i for i in items if i.get("type") == "rental_order"]
            assertion("Rental orders in calendar", len(rental_items) >= 1,
                      f"rental_items={len(rental_items)}")
            if rental_items:
                ri = rental_items[0]
                assertion("Has date range", ri.get("date") is not None)
                assertion("Has customer name", ri.get("customer_name") is not None)

        # ══════════════════════════════════════════════════════════════
        # TC-09: Customer dedup
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-09: Customer dedup")

        cust_count = await customers_collection.count_documents({"organization_id": ORG_ID})

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Mario Noleggio",
            "customer_email": "mario.r@test.com",  # same as TC-01
            "items": [{
                "product_id": pids["RENTAL_DAY"], "quantity": 1,
                "rental_date_from": "2026-11-01",
            }],
        }, headers=public_h())
        assertion("Repeat order created", r.status_code in (200, 201))

        cust_after = await customers_collection.count_documents({"organization_id": ORG_ID})
        assertion("No new customer", cust_after == cust_count)

        # ══════════════════════════════════════════════════════════════
        # TC-10: Mark paid + payment sync
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-10: Mark paid + payment sync")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Pagante Noleggio",
            "customer_email": "pay.r@test.com",
            "items": [{
                "product_id": pids["RENTAL_WEEK"], "quantity": 1,
                "rental_date_from": "2026-12-01",
                "rental_date_to": "2026-12-07",
            }],
        }, headers=public_h())

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            await c.post(f"/orders/{oid}/confirm", headers=admin_h())

            r = await c.post(f"/orders/{oid}/mark-paid", headers=admin_h())
            assertion("Mark paid succeeds", r.status_code == 200)

            order = await get_order(oid)
            assertion("Order payment_status=paid", order["payment_status"] == "paid")

            srs = await get_sales_records(oid)
            if srs:
                assertion("SalesRecord synced to paid", srs[0]["payment_status"] == "paid")

        # ══════════════════════════════════════════════════════════════
        # TC-11: Cashflow aggregate
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-11: Cashflow aggregate")

        all_srs = await sales_records_collection.find(
            {"organization_id": ORG_ID, "dataset_id": "orders"}, {"_id": 0}).to_list(500)

        positive = sum(s["amount"] for s in all_srs if s["amount"] > 0)
        negative = sum(s["amount"] for s in all_srs if s["amount"] < 0)
        net = round(positive + negative, 2)

        assertion(f"Positive sales: €{positive}", positive > 0)
        print(f"  ℹ️  Net cashflow: €{net}")

        orphans = 0
        for sr in all_srs:
            oid = sr.get("metadata", {}).get("order_id")
            if oid and not await orders_collection.find_one({"id": oid}, {"_id": 0, "id": 1}):
                orphans += 1
        assertion("No orphan SalesRecords", orphans == 0)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    global ORG_ID, ADMIN_EMAIL, ADMIN_PASSWORD, STORE_SLUG

    print("=" * 60)
    print("E2E TEST SUITE — Rental Flow")
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
