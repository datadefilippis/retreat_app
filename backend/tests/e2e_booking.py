#!/usr/bin/env python3
"""
E2E Test Suite — Booking (1:1 Consultation) Flow
==================================================
Tests: availability rules → booking order → calendar sync → slot removal →
       cancel recovery → double-booking → cashflow propagation

Usage:
  cd backend && ./venv/bin/python tests/e2e_booking.py
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
    print("\n🔄 PHASE 0: Reset + Seed (Booking)")
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
            "display_name": "Studio Consulenze", "contact_email": "studio@test.com",
            "notification_email": "admin@test.com", "reply_to_email": "studio@test.com",
            "sender_display_name": "Studio Consulenze",
            "fulfillment_modes": ["shipping", "local_pickup"],
            "is_storefront_published": True,
        }
    }})

    # Store
    store_id = generate_id()
    await stores_collection.insert_one({
        "id": store_id, "organization_id": ORG_ID, "slug": STORE_SLUG,
        "name": "Studio Consulenze", "visibility": "public",
        "fulfillment_modes": ["shipping", "local_pickup"],
        "is_published": True, "is_default": True, "is_active": True,
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  ✅ Store: {STORE_SLUG}")

    # Products
    pids = {}

    pids["CONSULT_60"] = generate_id()
    # Back-compat test — intentional use of deprecated item_type=booking
    # (Onda 16 Fase 6). Verifies read-path shims still render legacy
    # documents; new products must use item_type=rental + reservation_flavor=slot.
    await products_collection.insert_one({
        "id": pids["CONSULT_60"], "organization_id": ORG_ID,
        "name": "Consulenza Strategica 60min", "unit_price": 120.00, "category": "Consulenze",
        "is_published": True, "item_type": "booking", "transaction_mode": "request",
        "price_mode": "fixed", "unit_label": "sessione", "store_ids": [store_id],
        "is_active": True, "metadata": {"duration_label": "60 min"},
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  📅 CONSULT_60: Consulenza Strategica 60min (€120, booking)")

    pids["CONSULT_30"] = generate_id()
    await products_collection.insert_one({
        "id": pids["CONSULT_30"], "organization_id": ORG_ID,
        "name": "Consulenza Rapida 30min", "unit_price": 60.00, "category": "Consulenze",
        "is_published": True, "item_type": "booking", "transaction_mode": "request",
        "price_mode": "fixed", "unit_label": "sessione", "store_ids": [store_id],
        "is_active": True, "metadata": {"duration_label": "30 min"},
        "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  📅 CONSULT_30: Consulenza Rapida 30min (€60, booking)")

    pids["PHYSICAL"] = generate_id()
    await products_collection.insert_one({
        "id": pids["PHYSICAL"], "organization_id": ORG_ID,
        "name": "Libro Strategia", "unit_price": 25.00, "category": "Libri",
        "is_published": True, "item_type": "physical", "transaction_mode": "request",
        "price_mode": "fixed", "unit_label": "copia", "store_ids": [store_id],
        "is_active": True, "metadata": {}, "created_at": utc_now(), "updated_at": utc_now(),
    })
    print(f"  📦 PHYSICAL: Libro Strategia (€25)")

    # ── Availability Rules: Mon-Fri 09:00-18:00, 60min slots ──
    rule_ids = []
    for day in range(5):  # 0=Mon to 4=Fri
        rid = generate_id()
        await availability_rules_collection.insert_one({
            "id": rid, "organization_id": ORG_ID, "store_id": None,
            "day_of_week": day, "start_time": "09:00", "end_time": "18:00",
            "slot_duration_minutes": 60, "is_active": True,
            "created_at": utc_now(), "updated_at": utc_now(),
        })
        rule_ids.append(rid)
    DAY_NAMES = ["Lun", "Mar", "Mer", "Gio", "Ven"]
    print(f"  ✅ Availability rules: {', '.join(DAY_NAMES)} 09:00-18:00 (60min slots)")

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

async def get_blocked_slots_for_date(date_str):
    return await blocked_slots_collection.find(
        {"organization_id": ORG_ID, "date": date_str, "reason": "booking"}, {"_id": 0}).to_list(50)


# ── Tests ─────────────────────────────────────────────────────────────────────

async def run_tests(store_id, pids):
    global admin_token

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20.0) as c:
        r = await c.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        admin_token = r.json()["access_token"]
        print("\n🔐 Admin logged in\n")

        # ══════════════════════════════════════════════════════════════
        # TC-01: Verify availability rules produce slots
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-01: Availability rules → free slots")

        # 2026-05-18 is a Monday
        r = await c.get("/availability/slots", params={
            "date_from": "2026-05-18", "date_to": "2026-05-18",
        }, headers=admin_h())
        assertion("Slots endpoint works", r.status_code == 200, f"status={r.status_code}")

        if r.status_code == 200:
            data = r.json()
            avail = data.get("available", [])
            assertion("Monday has slots", len(avail) == 1 and len(avail[0].get("slots", [])) > 0,
                      f"days={len(avail)} slots={len(avail[0].get('slots', [])) if avail else 0}")
            if avail and avail[0].get("slots"):
                slots = avail[0]["slots"]
                assertion("9 slots (09-18, 60min each)", len(slots) == 9, f"count={len(slots)}")
                assertion("First slot 09:00-10:00", slots[0] == {"start": "09:00", "end": "10:00"},
                          f"first={slots[0]}")
                assertion("Last slot 17:00-18:00", slots[-1] == {"start": "17:00", "end": "18:00"},
                          f"last={slots[-1]}")

        # Check Saturday (no rules) → no slots
        r = await c.get("/availability/slots", params={
            "date_from": "2026-05-23", "date_to": "2026-05-23",  # Saturday
        }, headers=admin_h())
        if r.status_code == 200:
            avail = r.json().get("available", [])
            sat_slots = avail[0].get("slots", []) if avail else []
            assertion("Saturday has no slots", len(sat_slots) == 0, f"slots={len(sat_slots)}")

        # ══════════════════════════════════════════════════════════════
        # TC-02: Public availability endpoint
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-02: Public availability endpoint")

        r = await c.get(f"/public/availability/{STORE_SLUG}", params={
            "date_from": "2026-05-18", "date_to": "2026-05-22",  # Mon-Fri
        }, headers=public_h())
        assertion("Public slots endpoint works", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")

        if r.status_code == 200:
            avail = r.json().get("available", [])
            assertion("5 weekdays returned", len(avail) == 5, f"days={len(avail)}")
            total_slots = sum(len(d.get("slots", [])) for d in avail)
            assertion("45 total slots (9 per day x 5 days)", total_slots == 45, f"total={total_slots}")

        # ══════════════════════════════════════════════════════════════
        # TC-03: Create booking order → full lifecycle
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-03: Booking order → full lifecycle")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Cliente Consulenza",
            "customer_email": "cliente@test.com",
            "customer_phone": "+39 333 1111111",
            "items": [{
                "product_id": pids["CONSULT_60"],
                "quantity": 1,
                "booking_date": "2026-05-18",          # Monday
                "booking_start_time": "10:00",
                "booking_end_time": "11:00",
            }],
        }, headers=public_h())
        assertion("Booking order created", r.status_code in (200, 201), f"status={r.status_code} body={r.text[:300]}")

        tc03_oid = None
        if r.status_code in (200, 201):
            tc03_oid = r.json().get("order_id") or r.json().get("id")
            order = await get_order(tc03_oid)

            assertion("Status draft", order["status"] == "draft")
            item = order["items"][0]
            assertion("booking_date snapshotted", item.get("booking_date") == "2026-05-18")
            assertion("booking_start_time snapshotted", item.get("booking_start_time") == "10:00")
            assertion("booking_end_time snapshotted", item.get("booking_end_time") == "11:00")
            assertion("item_type=booking", item.get("item_type") == "booking")
            assertion("Subtotal=120.00", order["subtotal"] == 120.0)

            # Confirm → calendar sync
            r = await c.post(f"/orders/{tc03_oid}/confirm", headers=admin_h())
            assertion("Confirm succeeds", r.status_code == 200, f"status={r.status_code}")

            # SalesRecord
            srs = await get_sales_records(tc03_oid)
            assertion("1 SalesRecord (120.00)", len(srs) == 1 and srs[0]["amount"] == 120.0,
                      f"count={len(srs)} amount={srs[0]['amount'] if srs else 'N/A'}")

            # Calendar block
            blocks = await get_blocked_slots_for_order(tc03_oid)
            assertion("Calendar block created", len(blocks) == 1, f"blocks={len(blocks)}")
            if blocks:
                b = blocks[0]
                assertion("Block date=2026-05-18", b["date"] == "2026-05-18")
                assertion("Block start=10:00", b["start_time"] == "10:00")
                assertion("Block end=11:00", b["end_time"] == "11:00")
                assertion("Block reason=booking", b["reason"] == "booking")
                assertion("Block reference_id=order_id", b["reference_id"] == tc03_oid)

        # ══════════════════════════════════════════════════════════════
        # TC-04: Slot removed from availability after confirm
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-04: Slot removed from availability")

        r = await c.get(f"/public/availability/{STORE_SLUG}", params={
            "date_from": "2026-05-18", "date_to": "2026-05-18",
        }, headers=public_h())
        assertion("Availability loads", r.status_code == 200)

        if r.status_code == 200:
            avail = r.json().get("available", [])
            if avail:
                slots = avail[0].get("slots", [])
                ten_am = {"start": "10:00", "end": "11:00"}
                assertion("10:00-11:00 slot REMOVED", ten_am not in slots,
                          f"slots={[s['start'] for s in slots]}")
                assertion("8 remaining slots (was 9)", len(slots) == 8, f"count={len(slots)}")
                assertion("09:00 still available", {"start": "09:00", "end": "10:00"} in slots)
                assertion("11:00 still available", {"start": "11:00", "end": "12:00"} in slots)

        # ══════════════════════════════════════════════════════════════
        # TC-05: Cancel → slot freed
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-05: Cancel booking → slot freed")

        if tc03_oid:
            r = await c.post(f"/orders/{tc03_oid}/cancel", headers=admin_h())
            assertion("Cancel succeeds", r.status_code == 200)

            # Block removed
            blocks = await get_blocked_slots_for_order(tc03_oid)
            assertion("Calendar block removed", len(blocks) == 0, f"remaining={len(blocks)}")

            # Storno
            srs = await get_sales_records(tc03_oid)
            storno = [s for s in srs if s["amount"] < 0]
            assertion("Storno record (-120.00)", len(storno) == 1 and storno[0]["amount"] == -120.0)

            # Slot available again
            r = await c.get(f"/public/availability/{STORE_SLUG}", params={
                "date_from": "2026-05-18", "date_to": "2026-05-18",
            }, headers=public_h())
            if r.status_code == 200:
                slots = r.json().get("available", [{}])[0].get("slots", [])
                assertion("10:00 slot available again", {"start": "10:00", "end": "11:00"} in slots,
                          f"slots={[s['start'] for s in slots]}")
                assertion("Back to 9 slots", len(slots) == 9, f"count={len(slots)}")

        # ══════════════════════════════════════════════════════════════
        # TC-06: Multiple bookings same day, different slots
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-06: Multiple bookings same day, different slots")

        booking_oids = []
        for slot, email in [("09:00", "slot1@test.com"), ("14:00", "slot2@test.com"), ("16:00", "slot3@test.com")]:
            r = await c.post("/public/order-request", json={
                "slug": STORE_SLUG,
                "customer_name": f"Client {slot}",
                "customer_email": email,
                "items": [{
                    "product_id": pids["CONSULT_60"], "quantity": 1,
                    "booking_date": "2026-05-19",  # Tuesday
                    "booking_start_time": slot,
                    "booking_end_time": f"{int(slot[:2])+1:02d}:00",
                }],
            }, headers=public_h())
            if r.status_code in (200, 201):
                oid = r.json().get("order_id") or r.json().get("id")
                booking_oids.append(oid)
                await c.post(f"/orders/{oid}/confirm", headers=admin_h())

        assertion("3 bookings created and confirmed", len(booking_oids) == 3)

        # Check availability: 3 slots removed from 9
        r = await c.get(f"/public/availability/{STORE_SLUG}", params={
            "date_from": "2026-05-19", "date_to": "2026-05-19",
        }, headers=public_h())
        if r.status_code == 200:
            slots = r.json().get("available", [{}])[0].get("slots", [])
            assertion("6 remaining slots (9-3)", len(slots) == 6, f"count={len(slots)}")
            booked_starts = ["09:00", "14:00", "16:00"]
            for bs in booked_starts:
                present = any(s["start"] == bs for s in slots)
                assertion(f"Slot {bs} removed", not present, f"found={present}")

        # ══════════════════════════════════════════════════════════════
        # TC-07: Booking on weekend → order works but no availability rule
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-07: Booking on weekend (no availability rule)")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Weekend Client",
            "customer_email": "weekend@test.com",
            "items": [{
                "product_id": pids["CONSULT_60"], "quantity": 1,
                "booking_date": "2026-05-23",  # Saturday
                "booking_start_time": "10:00",
                "booking_end_time": "11:00",
            }],
        }, headers=public_h())
        # Order should still be accepted (no validation at submit time)
        assertion("Weekend booking accepted (request mode)", r.status_code in (200, 201),
                  f"status={r.status_code}")

        # ══════════════════════════════════════════════════════════════
        # TC-08: Mixed order (booking + physical)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-08: Mixed order (booking + physical)")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Mix Client",
            "customer_email": "mix@test.com",
            "items": [
                {
                    "product_id": pids["CONSULT_30"], "quantity": 1,
                    "booking_date": "2026-05-20",  # Wednesday
                    "booking_start_time": "15:00",
                    "booking_end_time": "15:30",
                },
                {"product_id": pids["PHYSICAL"], "quantity": 2},
            ],
        }, headers=public_h())
        assertion("Mixed order created", r.status_code in (200, 201), f"status={r.status_code} body={r.text[:200]}")

        tc08_oid = None
        if r.status_code in (200, 201):
            tc08_oid = r.json().get("order_id") or r.json().get("id")
            order = await get_order(tc08_oid)
            assertion("2 line items", len(order["items"]) == 2)
            assertion("Subtotal = 110.00 (60+50)", order["subtotal"] == 110.0,
                      f"subtotal={order.get('subtotal')}")

            r = await c.post(f"/orders/{tc08_oid}/confirm", headers=admin_h())
            assertion("Confirm succeeds", r.status_code == 200)

            srs = await get_sales_records(tc08_oid)
            assertion("2 SalesRecords", len(srs) == 2, f"count={len(srs)}")

            blocks = await get_blocked_slots_for_order(tc08_oid)
            assertion("1 calendar block (booking only, not physical)", len(blocks) == 1,
                      f"blocks={len(blocks)}")

        # ══════════════════════════════════════════════════════════════
        # TC-09: Two bookings same slot (double-booking scenario)
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-09: Double-booking same slot")

        # First booking
        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "First Booker",
            "customer_email": "first@test.com",
            "items": [{
                "product_id": pids["CONSULT_60"], "quantity": 1,
                "booking_date": "2026-05-21",  # Thursday
                "booking_start_time": "11:00",
                "booking_end_time": "12:00",
            }],
        }, headers=public_h())
        assertion("First booking created", r.status_code in (200, 201))
        first_oid = r.json().get("order_id") or r.json().get("id") if r.status_code in (200, 201) else None

        # Second booking same slot (before first is confirmed)
        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Second Booker",
            "customer_email": "second@test.com",
            "items": [{
                "product_id": pids["CONSULT_60"], "quantity": 1,
                "booking_date": "2026-05-21",
                "booking_start_time": "11:00",
                "booking_end_time": "12:00",
            }],
        }, headers=public_h())
        assertion("Second booking also accepted (both drafts)", r.status_code in (200, 201))
        second_oid = r.json().get("order_id") or r.json().get("id") if r.status_code in (200, 201) else None

        # Confirm first → blocks slot
        if first_oid:
            r = await c.post(f"/orders/{first_oid}/confirm", headers=admin_h())
            assertion("First booking confirmed", r.status_code == 200)

            blocks = await get_blocked_slots_for_order(first_oid)
            assertion("First booking blocks calendar", len(blocks) == 1)

        # Check availability → slot gone
        r = await c.get(f"/public/availability/{STORE_SLUG}", params={
            "date_from": "2026-05-21", "date_to": "2026-05-21",
        }, headers=public_h())
        if r.status_code == 200:
            slots = r.json().get("available", [{}])[0].get("slots", [])
            assertion("11:00 slot removed from availability", not any(s["start"] == "11:00" for s in slots))

        # Admin sees second order as draft — should review conflict before confirming
        if second_oid:
            order2 = await get_order(second_oid)
            assertion("Second order still draft (admin must review)", order2["status"] == "draft")

        # ══════════════════════════════════════════════════════════════
        # TC-10: Complete booking order + payment sync
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-10: Complete booking + payment sync")

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Pagatore",
            "customer_email": "pay@test.com",
            "items": [{
                "product_id": pids["CONSULT_60"], "quantity": 1,
                "booking_date": "2026-05-22",  # Friday
                "booking_start_time": "09:00",
                "booking_end_time": "10:00",
            }],
        }, headers=public_h())

        if r.status_code in (200, 201):
            oid = r.json().get("order_id") or r.json().get("id")
            await c.post(f"/orders/{oid}/confirm", headers=admin_h())

            # Mark paid
            r = await c.post(f"/orders/{oid}/mark-paid", headers=admin_h())
            assertion("Mark paid succeeds", r.status_code == 200)

            order = await get_order(oid)
            assertion("payment_status=paid", order["payment_status"] == "paid")

            srs = await get_sales_records(oid)
            if srs:
                assertion("SalesRecord synced to paid", srs[0]["payment_status"] == "paid")

            # Complete
            r = await c.post(f"/orders/{oid}/complete", headers=admin_h())
            assertion("Complete succeeds", r.status_code == 200)

        # ══════════════════════════════════════════════════════════════
        # TC-11: Customer dedup across booking orders
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-11: Customer dedup")

        cust_before = await customers_collection.count_documents({"organization_id": ORG_ID})

        r = await c.post("/public/order-request", json={
            "slug": STORE_SLUG,
            "customer_name": "Cliente Consulenza",
            "customer_email": "cliente@test.com",  # same as TC-03
            "items": [{
                "product_id": pids["CONSULT_30"], "quantity": 1,
                "booking_date": "2026-05-22",
                "booking_start_time": "14:00",
                "booking_end_time": "14:30",
            }],
        }, headers=public_h())
        assertion("Repeat client order created", r.status_code in (200, 201))

        cust_after = await customers_collection.count_documents({"organization_id": ORG_ID})
        assertion("No new customer (dedup)", cust_after == cust_before,
                  f"before={cust_before} after={cust_after}")

        # ══════════════════════════════════════════════════════════════
        # TC-12: Cashflow aggregate
        # ══════════════════════════════════════════════════════════════
        set_tc("TC-12: Cashflow aggregate")

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

        booking_blocks = await blocked_slots_collection.count_documents(
            {"organization_id": ORG_ID, "reason": "booking"})
        print(f"  ℹ️  Active booking calendar blocks: {booking_blocks}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    global ORG_ID, ADMIN_EMAIL, ADMIN_PASSWORD, STORE_SLUG

    print("=" * 60)
    print("E2E TEST SUITE — Booking (1:1 Consultation) Flow")
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
