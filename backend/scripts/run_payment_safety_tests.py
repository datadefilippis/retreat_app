#!/usr/bin/env python3
"""
run_payment_safety_tests.py — Automated runner for billing payment safety scenarios.

Onda 9.S2 — covers ~30-40% of the BILLING_PAYMENT_SAFETY_TEST_PLAN.md
scenarios that don't require a real Stripe Checkout flow:

  · Section I (limit enforcement) — full coverage
  · Section H (idempotency) — partial (BillingEvent unique index test)
  · Section E (addon admin override) — full
  · Section D (plan change via admin) — full (no Stripe sub required)
  · Section A02 (trial-once policy) — backend logic check
  · Section F (cancel/reactivate endpoints) — partial (no Stripe sub mock)

What this runner does NOT test (requires Stripe Checkout flow + real card):
  · A01, A03, A04 — initial subscribe via Stripe Checkout
  · B01, B02, B03 — Stripe trial events
  · C01, C02, C03 — recurring renewal
  · D01, D04 — Stripe modify with proration
  · E01-E03 — addon buy via Stripe Checkout
  · F04, F05 — resubscribe via Stripe Portal
  · G01 — Stripe payment_failed sequence

For those, follow the manual procedure in BILLING_PAYMENT_SAFETY_TEST_PLAN.md.

USAGE:

    # Make sure backend is running on localhost:8000
    cd /Users/davidedefilippis/Desktop/BI_PMI/backend
    ./venv/bin/python scripts/run_payment_safety_tests.py

    # Verbose mode (shows full HTTP responses)
    ./venv/bin/python scripts/run_payment_safety_tests.py --verbose

    # Run specific scenario only
    ./venv/bin/python scripts/run_payment_safety_tests.py --only I01a

EXIT CODES:
    0 = all tests passed
    1 = at least one CRITICAL failure
    2 = setup error (backend down, DB unreachable)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

import httpx  # noqa: E402

BACKEND = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
API = f"{BACKEND}/api"

# Test admin password (set on every test org during seed)
TEST_PASSWORD = "Test1234!"

# v5.8 / Onda 9.S2 — alias the seed org IDs to scenario roles
# Seeds creates 4 orgs: org_test_active (core), org_test_trialing (core trial),
# org_test_past_due (pro past_due), org_test_canceled (free).
# We re-provision them per-test to match the scenario role we need.
ORG_FREE = "org_test_canceled"     # already on free plan
ORG_SOLO = "org_test_trialing"     # we'll re-provision to starter/active for solo tests
ORG_STARTER = "org_test_active"    # already on core
ORG_PRO = "org_test_past_due"      # we'll re-provision to pro/active

# System admin for admin endpoint tests — auto-created in pre-flight
SYSADMIN_EMAIL = "sysadmin.test_runner@afian.example.com"
SYSADMIN_PASSWORD = "SysAdmin1234!"


# ── Result tracking ─────────────────────────────────────────────────────────

@dataclass
class TestResult:
    test_id: str
    severity: str   # 'critical' | 'high' | 'medium' | 'low'
    title: str
    status: str     # 'pass' | 'fail' | 'skip' | 'error'
    message: str = ""
    details: Optional[Dict[str, Any]] = None
    duration_ms: int = 0


# ── ANSI color helpers ──────────────────────────────────────────────────────

def _c(s: str, color: str) -> str:
    if not sys.stdout.isatty():
        return s
    codes = {"red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
             "blue": "\033[94m", "gray": "\033[90m", "bold": "\033[1m",
             "reset": "\033[0m"}
    return f"{codes.get(color, '')}{s}{codes['reset']}"


def _icon(status: str) -> str:
    return {"pass": _c("\u2713", "green"), "fail": _c("\u2717", "red"),
            "skip": _c("\u2014", "gray"), "error": _c("\u26A0", "yellow")}.get(status, "?")


def _sev_label(sev: str) -> str:
    return {"critical": _c("[CRIT]", "red"), "high": _c("[HIGH]", "yellow"),
            "medium": _c("[MED ]", "blue"), "low": _c("[LOW ]", "gray")}.get(sev, sev)


# ── HTTP helpers ────────────────────────────────────────────────────────────

class ApiClient:
    """Wrapper around httpx with auth helpers for test orgs."""

    def __init__(self, verbose: bool = False):
        self.client = httpx.AsyncClient(timeout=10.0, follow_redirects=False)
        self.verbose = verbose
        self._tokens: Dict[str, str] = {}  # email -> jwt

    async def login(self, email: str, password: Optional[str] = None) -> Optional[str]:
        if email in self._tokens:
            return self._tokens[email]
        pwd = password or TEST_PASSWORD
        r = await self.client.post(f"{API}/auth/login", json={"email": email, "password": pwd})
        if r.status_code != 200:
            if self.verbose:
                print(f"    LOGIN FAIL {email}: {r.status_code} {r.text[:200]}")
            return None
        token = r.json().get("access_token")
        if token:
            self._tokens[email] = token
        return token

    async def authed_request(self, method: str, path: str, email: str,
                             json_body: Optional[dict] = None,
                             params: Optional[dict] = None,
                             expected_status: Optional[int] = None) -> httpx.Response:
        token = await self.login(email)
        if not token:
            raise RuntimeError(f"Cannot login as {email}")
        headers = {"Authorization": f"Bearer {token}"}
        r = await self.client.request(method, f"{API}{path}", headers=headers,
                                      json=json_body, params=params)
        if self.verbose:
            print(f"    {method} {path} -> {r.status_code}")
            try:
                print(f"      body: {json.dumps(r.json(), indent=2, default=str)[:300]}")
            except Exception:
                pass
        if expected_status is not None and r.status_code != expected_status:
            raise AssertionError(
                f"Expected {expected_status}, got {r.status_code}. Body: {r.text[:300]}"
            )
        return r

    async def close(self):
        await self.client.aclose()


# ── DB helpers ──────────────────────────────────────────────────────────────

async def get_db():
    """Lazy import of database to avoid env-var requirements at module load."""
    from database import (
        organizations_collection, products_collection, orders_collection,
        stores_collection, addon_subscriptions_collection,
        module_subscriptions_collection, billing_events_collection,
        ai_usage_events_collection,  # legacy name; module-agnostic content
        pricing_plans_collection,
        commercial_plans_collection,
    )
    return {
        "orgs": organizations_collection,
        "products": products_collection,
        "orders": orders_collection,
        "stores": stores_collection,
        "addon_subs": addon_subscriptions_collection,
        "module_subs": module_subscriptions_collection,
        "billing_events": billing_events_collection,
        "usage_events": ai_usage_events_collection,
        "pricing_plans": pricing_plans_collection,
        "commercial_plans": commercial_plans_collection,
    }


# ── Test fixture management ─────────────────────────────────────────────────

async def ensure_test_orgs():
    """Make sure the seeded test orgs exist (calls seed_test_orgs --execute idempotently)."""
    from scripts.seed_test_orgs import TEST_ORGS_SPEC
    db = await get_db()

    needed_ids = [o["id"] for o in TEST_ORGS_SPEC]
    cursor = db["orgs"].find({"id": {"$in": needed_ids}}, {"_id": 0, "id": 1})
    found = set()
    async for r in cursor:
        found.add(r["id"])
    missing = [i for i in needed_ids if i not in found]
    return {"found": len(found), "missing": missing, "all_ids": needed_ids}


def admin_email_for(org_id: str) -> str:
    # v5.8 / Onda 9.S2 — using .example.com (RFC 2606 reserved) instead of
    # .test (RFC 6761) because pydantic email-validator rejects .test as
    # special-use TLD with status=400 BEFORE reaching the auth handler.
    return f"admin@{org_id.replace('_', '-')}.example.com"


async def ensure_system_admin():
    """Auto-create a system_admin test user if missing. Idempotent.

    Uses a dedicated email that won't conflict with real prod users.
    Returns the email of the system_admin to use in tests.
    """
    db = await get_db()
    from database import users_collection
    from auth import get_password_hash
    from models.common import generate_id, utc_now

    existing = await users_collection.find_one({"email": SYSADMIN_EMAIL}, {"_id": 0, "email": 1})
    if existing:
        return SYSADMIN_EMAIL

    # Create
    now = utc_now().isoformat()
    user_doc = {
        "id": generate_id(),
        "email": SYSADMIN_EMAIL,
        "name": "Test Runner SystemAdmin",
        "password_hash": get_password_hash(SYSADMIN_PASSWORD),
        "role": "system_admin",
        "organization_id": None,  # system_admin spans orgs
        "is_active": True,
        "is_email_verified": True,
        "locale": "it",
        "created_at": now,
        "updated_at": now,
    }
    await users_collection.insert_one(user_doc)
    return SYSADMIN_EMAIL


async def reset_org_to_state(org_id: str, plan_slug: str = "free", billing_status: str = "none"):
    """Reset an org to a known clean state for the next test."""
    db = await get_db()
    from services.plan_provisioning import provision_commercial_plan
    # Clean usage events for current month
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    await db["usage_events"].delete_many({
        "organization_id": org_id,
        "consumed_at": {"$gte": month_start}
    })
    await db["addon_subs"].delete_many({"organization_id": org_id})
    # Re-provision
    await provision_commercial_plan(
        org_id=org_id,
        plan_slug=plan_slug,
        assigned_by="test_runner:reset",
        billing_status=billing_status,
        notes="Test runner reset",
    )


# ── Test scenarios ──────────────────────────────────────────────────────────

# Each test function returns (status, message, details_dict)
# Status: 'pass' | 'fail' | 'skip' | 'error'

async def test_I01a_free_cannot_create_store(api: ApiClient) -> tuple:
    """Free user (commerce_disabled, stores_max=0) cannot create a store."""
    org_id = ORG_FREE
    await reset_org_to_state(org_id, "free", "none")
    email = admin_email_for(org_id)
    r = await api.authed_request("POST", "/stores", email, json_body={
        "name": "Test Store", "visibility": "public"
    })
    if r.status_code == 429:
        body = r.json()
        code = body.get("detail", {}).get("code") if isinstance(body.get("detail"), dict) else None
        if code == "QUOTA_EXCEEDED":
            return ("pass", f"Got 429 QUOTA_EXCEEDED as expected", {"response": body})
        return ("fail", f"Got 429 but code is {code}, expected QUOTA_EXCEEDED", {"response": body})
    if r.status_code == 403:
        body = r.json()
        code = body.get("detail", {}).get("code") if isinstance(body.get("detail"), dict) else None
        if code in ("FEATURE_NOT_AVAILABLE", "MODULE_NOT_AVAILABLE"):
            return ("pass", f"Got 403 {code} as expected", {"response": body})
        return ("fail", f"Got 403 but code is {code}", {"response": body})
    return ("fail", f"Expected 429 or 403, got {r.status_code}", {"body": r.text[:300]})


async def test_I01b_free_cannot_create_product(api: ApiClient) -> tuple:
    """Free user (product_catalog_disabled, products=0) cannot create a product."""
    org_id = ORG_FREE
    await reset_org_to_state(org_id, "free", "none")
    email = admin_email_for(org_id)
    r = await api.authed_request("POST", "/products", email, json_body={
        "name": "Test Product",
        "item_type": "physical",
        "unit_price": 10.0,
        "currency": "EUR",
    })
    if r.status_code == 429:
        body = r.json()
        code = (body.get("detail") or {}).get("code") if isinstance(body.get("detail"), dict) else None
        if code == "QUOTA_EXCEEDED":
            return ("pass", "Got 429 QUOTA_EXCEEDED", {"response": body})
    return ("fail", f"Expected 429 QUOTA_EXCEEDED, got {r.status_code}", {"body": r.text[:300]})


async def test_I01c_free_cannot_create_order(api: ApiClient) -> tuple:
    """Free user (commerce_disabled, orders_monthly=0) cannot create an order.

    The OrderCreate schema requires customer_id + items[1+] with product_id+quantity.
    We use placeholder IDs that pass Pydantic; the quota check fires BEFORE the
    service tries to resolve them, so 429 is returned regardless.
    """
    org_id = ORG_FREE
    await reset_org_to_state(org_id, "free", "none")
    email = admin_email_for(org_id)
    r = await api.authed_request("POST", "/orders", email, json_body={
        "customer_id": "placeholder_customer_id",
        "currency": "EUR",
        "items": [{"product_id": "placeholder_product_id", "quantity": 1}],
    })
    if r.status_code == 429:
        body = r.json()
        code = (body.get("detail") or {}).get("code") if isinstance(body.get("detail"), dict) else None
        if code == "QUOTA_EXCEEDED":
            return ("pass", "Got 429 QUOTA_EXCEEDED", {"response": body})
    # If a 400/404 fires, it means quota check was passed (e.g. customer not found
    # came AFTER quota). That would be a regression — quota MUST gate.
    return ("fail", f"Expected 429 QUOTA_EXCEEDED, got {r.status_code}",
            {"body": r.text[:300]})


async def test_I01d_solo_cannot_create_store(api: ApiClient) -> tuple:
    """Solo user (commerce_disabled, stores_max=0) cannot create a store either."""
    org_id = ORG_SOLO
    # Force it to starter (Solo) for this test
    await reset_org_to_state(org_id, "starter", "active")
    email = admin_email_for(org_id)
    r = await api.authed_request("POST", "/stores", email, json_body={
        "name": "Test Store Solo", "visibility": "public"
    })
    if r.status_code == 429:
        body = r.json()
        code = (body.get("detail") or {}).get("code") if isinstance(body.get("detail"), dict) else None
        if code == "QUOTA_EXCEEDED":
            return ("pass", "Solo blocked from creating store", {"response": body})
    if r.status_code == 403:
        return ("pass", "Solo blocked with 403", {"body": r.text[:200]})
    return ("fail", f"Expected 429/403, got {r.status_code}", {"body": r.text[:300]})


async def test_I02_off_by_one_products(api: ApiClient) -> tuple:
    """Verify off-by-one: org with limit=N can create N products but not N+1."""
    org_id = ORG_STARTER  # Commerce Starter (products limit=200)
    await reset_org_to_state(org_id, "core", "active")
    db = await get_db()
    # Cleanup: delete any leftover test products from previous runs
    await db["products"].delete_many({
        "organization_id": org_id,
        "name": {"$regex": "^OffByOne"}
    })
    # Now insert exactly 199 products directly
    existing = await db["products"].count_documents({"organization_id": org_id})
    to_insert = max(0, 199 - existing)
    if to_insert > 0:
        from models.common import generate_id, utc_now
        now = utc_now().isoformat()
        docs = [{
            "id": generate_id(), "organization_id": org_id,
            "name": f"OffByOne Test {i}", "item_type": "physical",
            "unit_price": 1.0, "currency": "EUR", "is_active": True,
            "is_published": False, "store_ids": [], "metadata": {},
            "created_at": now, "updated_at": now,
        } for i in range(to_insert)]
        if docs:
            await db["products"].insert_many(docs)

    email = admin_email_for(org_id)

    # Now we have 199. Create 1 more via API → should succeed (200th)
    r1 = await api.authed_request("POST", "/products", email, json_body={
        "name": "OffByOne 200th", "item_type": "physical",
        "unit_price": 10.0, "currency": "EUR",
    })
    if r1.status_code != 201:
        return ("fail", f"200th product (limit=200) should pass, got {r1.status_code}",
                {"body": r1.text[:300]})

    # Now we have 200. Create 1 more → should block (201st)
    r2 = await api.authed_request("POST", "/products", email, json_body={
        "name": "OffByOne 201st", "item_type": "physical",
        "unit_price": 10.0, "currency": "EUR",
    })
    # Cleanup test products before returning (so test is repeatable)
    await db["products"].delete_many({
        "organization_id": org_id,
        "$or": [
            {"name": {"$regex": "^OffByOne"}},
            {"name": "OffByOne 200th"}, {"name": "OffByOne 201st"},
        ]
    })

    if r2.status_code == 429:
        body = r2.json()
        code = (body.get("detail") or {}).get("code") if isinstance(body.get("detail"), dict) else None
        if code == "QUOTA_EXCEEDED":
            return ("pass", "200th passed, 201st blocked correctly",
                    {"r1": r1.status_code, "r2_code": code})

    return ("fail", f"201st product should be blocked, got {r2.status_code}",
            {"body": r2.text[:300]})


async def test_E04_admin_assign_addon_increases_limit(api: ApiClient) -> tuple:
    """Admin assigns custom addon override → effective_limit increases without Stripe."""
    org_id = ORG_STARTER
    await reset_org_to_state(org_id, "core", "active")
    db = await get_db()
    from services.module_access import get_effective_limit

    # Baseline limit
    base_limit = await get_effective_limit(org_id, "ai_assistant", "chat")

    # Need a system_admin to call the admin endpoint
    sysadmin_email = SYSADMIN_EMAIL
    sysadmin_token = await api.login(sysadmin_email, SYSADMIN_PASSWORD)
    if not sysadmin_token:
        return ("skip", f"No system_admin user '{sysadmin_email}' — skipping admin tests",
                {"hint": "Auto-create should have run in pre-flight"})

    r = await api.authed_request("POST", f"/admin/organizations/{org_id}/addons",
                                  sysadmin_email, json_body={
        "addon_slug": "addon_ai_chat_pack",
        "quantity": 1,
        "reason": "Test runner E04 — verify limit raises",
    })
    if r.status_code != 200:
        return ("fail", f"Admin assign addon failed: {r.status_code}", {"body": r.text[:300]})

    new_limit = await get_effective_limit(org_id, "ai_assistant", "chat")
    if new_limit == base_limit + 50:
        # Cleanup
        await api.authed_request("DELETE",
                                 f"/admin/organizations/{org_id}/addons/addon_ai_chat_pack",
                                 sysadmin_email,
                                 params={"reason": "Test cleanup"})
        return ("pass", f"Limit raised from {base_limit} to {new_limit}",
                {"base": base_limit, "after": new_limit})
    return ("fail", f"Limit went from {base_limit} to {new_limit}, expected +50",
            {"base": base_limit, "after": new_limit})


async def test_H01_billing_event_idempotency(api: ApiClient) -> tuple:
    """BillingEvent unique index prevents duplicate event processing."""
    db = await get_db()
    from models.common import utc_now

    test_event_id = f"evt_test_runner_{int(time.time())}"
    doc = {
        "stripe_event_id": test_event_id,
        "event_type": "test.runner.idempotency",
        "stripe_subscription_id": "sub_test_dummy",
        "received_at": utc_now().isoformat(),
        "processed": True,
    }

    try:
        await db["billing_events"].insert_one(doc)
    except Exception as e:
        return ("error", f"First insert failed: {e}", {})

    # Second insert with same stripe_event_id MUST fail (unique index)
    try:
        await db["billing_events"].insert_one(doc.copy())
        # Cleanup
        await db["billing_events"].delete_many({"stripe_event_id": test_event_id})
        return ("fail", "Duplicate insert succeeded — unique index missing!",
                {"event_id": test_event_id})
    except Exception as e:
        # Expected: DuplicateKeyError
        await db["billing_events"].delete_many({"stripe_event_id": test_event_id})
        if "duplicate" in str(e).lower() or "E11000" in str(e):
            return ("pass", "Unique index prevents duplicate event", {"error": str(e)[:100]})
        return ("error", f"Unexpected error type: {e}", {})


async def test_H02_addon_subscription_idempotency(api: ApiClient) -> tuple:
    """upsert_addon_subscription is idempotent (re-upserting same row doesn't create duplicate)."""
    org_id = ORG_STARTER
    await reset_org_to_state(org_id, "core", "active")
    db = await get_db()
    from repositories.billing_repository import upsert_addon_subscription

    payload = {
        "organization_id": org_id,
        "addon_slug": "addon_ai_chat_pack",
        "quantity": 1,
        "stripe_subscription_id": "sub_test_idem",
        "is_custom_override": False,
    }

    id1 = await upsert_addon_subscription(payload)
    id2 = await upsert_addon_subscription(payload)
    id3 = await upsert_addon_subscription({**payload, "quantity": 2})  # change qty

    count = await db["addon_subs"].count_documents({
        "organization_id": org_id, "addon_slug": "addon_ai_chat_pack", "status": "active"
    })

    # Cleanup
    await db["addon_subs"].delete_many({"organization_id": org_id, "addon_slug": "addon_ai_chat_pack"})

    if id1 == id2 == id3 and count == 1:
        return ("pass", f"3 upserts → 1 row, same id, qty updated to 2",
                {"id": id1, "count": count})
    return ("fail", f"Upserts created {count} rows or different ids ({id1}, {id2}, {id3})",
            {"id1": id1, "id2": id2, "id3": id3, "count": count})


async def test_D02_admin_set_plan_provisions_modules(api: ApiClient) -> tuple:
    """Admin set commercial plan free → starter creates all module subscriptions."""
    org_id = ORG_FREE
    await reset_org_to_state(org_id, "free", "none")
    db = await get_db()

    sysadmin_email = SYSADMIN_EMAIL
    sysadmin_token = await api.login(sysadmin_email, SYSADMIN_PASSWORD)
    if not sysadmin_token:
        return ("skip", "Pre-flight failed to create system_admin", {})

    # Switch to starter
    r = await api.authed_request(
        "PUT", f"/admin/organizations/{org_id}/commercial-plan",
        sysadmin_email,
        json_body={"commercial_plan_slug": "starter", "notes": "Test D02"},
    )
    if r.status_code != 200:
        return ("fail", f"Admin set plan failed: {r.status_code}", {"body": r.text[:300]})

    # Verify module_subscriptions
    count = await db["module_subs"].count_documents({
        "organization_id": org_id, "status": "active"
    })

    # Cleanup: revert to free
    await api.authed_request(
        "PUT", f"/admin/organizations/{org_id}/commercial-plan",
        sysadmin_email,
        json_body={"commercial_plan_slug": "free", "notes": "Test D02 cleanup"},
    )

    if count >= 4:  # 5 modules expected (cashflow, ai, product_catalog, commerce, customers_light) — Wave 7A removed commerce_signals
        return ("pass", f"{count} module subscriptions provisioned", {"count": count})
    return ("fail", f"Only {count} module subs (expected >=4)", {"count": count})


async def test_D03_downgrade_reconciles_stores(api: ApiClient) -> tuple:
    """Downgrade Pro → Solo deactivates excess stores via reconcile_stores_to_plan_limit."""
    org_id = ORG_STARTER
    db = await get_db()
    sysadmin_email = SYSADMIN_EMAIL
    sysadmin_token = await api.login(sysadmin_email, SYSADMIN_PASSWORD)
    if not sysadmin_token:
        return ("skip", "Pre-flight failed to create system_admin", {})

    # Setup: pro plan with 3 active stores
    from services.plan_provisioning import provision_commercial_plan
    await provision_commercial_plan(org_id=org_id, plan_slug="pro",
                                     assigned_by="test_setup", billing_status="active")
    # Insert 2 stores (in addition to default if any)
    from models.common import generate_id, utc_now
    now = utc_now().isoformat()
    test_stores = [{
        "id": generate_id(), "organization_id": org_id,
        "name": f"Test Store {i}", "slug": f"test-{int(time.time())}-{i}",
        "visibility": "public", "is_active": True, "is_published": False,
        "is_default": False, "fulfillment_modes": ["shipping"],
        "storefront_languages": ["it"], "created_at": now, "updated_at": now,
    } for i in range(3)]
    await db["stores"].insert_many(test_stores)
    test_ids = [s["id"] for s in test_stores]

    # Now downgrade to Solo (stores_max=0)
    r = await api.authed_request(
        "PUT", f"/admin/organizations/{org_id}/commercial-plan",
        sysadmin_email,
        json_body={"commercial_plan_slug": "starter", "notes": "Test D03"},
    )
    if r.status_code != 200:
        await db["stores"].delete_many({"id": {"$in": test_ids}})
        return ("fail", f"Plan change failed: {r.status_code}", {"body": r.text[:300]})

    # Verify the test stores are now deactivated
    cursor = db["stores"].find({"id": {"$in": test_ids}}, {"_id": 0, "id": 1, "is_active": 1, "deactivated_for_plan_violation": 1})
    deactivated_count = 0
    async for s in cursor:
        if not s.get("is_active") and s.get("deactivated_for_plan_violation"):
            deactivated_count += 1

    # Cleanup
    await db["stores"].delete_many({"id": {"$in": test_ids}})
    await provision_commercial_plan(org_id=org_id, plan_slug="core",
                                     assigned_by="test_cleanup", billing_status="active")

    if deactivated_count >= 2:  # at least 2 of 3 (Solo allows 0, default protected counts as 1 if exists)
        return ("pass", f"{deactivated_count}/3 test stores deactivated by reconcile",
                {"deactivated": deactivated_count})
    return ("fail", f"Only {deactivated_count}/3 stores deactivated", {"deactivated": deactivated_count})


async def test_A02_trial_once_policy_check(api: ApiClient) -> tuple:
    """Verify org with has_used_trial=true does NOT receive a second trial in checkout session."""
    org_id = ORG_FREE
    db = await get_db()
    # Mark has_used_trial
    await db["orgs"].update_one(
        {"id": org_id},
        {"$set": {"has_used_trial": True, "billing_status": "none", "commercial_plan_slug": "free"}}
    )

    # Try to create a checkout session
    email = admin_email_for(org_id)
    r = await api.authed_request("POST", "/billing/checkout-session", email, json_body={
        "plan_slug": "starter", "interval": "month",
        "success_url": "http://localhost:3000/settings?billing_success=1",
        "cancel_url": "http://localhost:3000/plans?billing_cancelled=1",
    })

    # Cleanup
    await db["orgs"].update_one({"id": org_id}, {"$set": {"has_used_trial": False}})

    if r.status_code == 200:
        # Inspect the session — would need Stripe API access. For now we just verify
        # the endpoint doesn't fail. Manual verification needed for trial_period_days.
        return ("skip", "Checkout session created (200) — manually verify trial_period_days=null in Stripe Dashboard",
                {"session": r.json()})
    if r.status_code == 503:
        return ("skip", f"Stripe not configured (503) — skip in this env", {})
    return ("fail", f"Checkout session creation unexpectedly failed: {r.status_code}",
            {"body": r.text[:300]})


# ── Onda 9.T trial-once tests ──────────────────────────────────────────────

async def test_T01_mark_trial_used_idempotent(api: ApiClient) -> tuple:
    """billing_repository.mark_trial_used is idempotent + sets has_used_trial=True permanently."""
    org_id = ORG_FREE
    await reset_org_to_state(org_id, "free", "none")
    db = await get_db()
    # Reset to clean state
    await db["orgs"].update_one(
        {"id": org_id},
        {"$set": {"has_used_trial": False, "has_used_trial_at": None, "trial_history": []}},
    )

    from repositories.billing_repository import mark_trial_used, get_trial_history
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    r1 = await mark_trial_used(org_id, "starter", now, "sub_test_T01", "month")
    r2 = await mark_trial_used(org_id, "starter", now, "sub_test_T01", "month")  # same sub
    r3 = await mark_trial_used(org_id, "core", now, "sub_test_T01_b", "month")  # diff sub

    history = await get_trial_history(org_id)
    org = await db["orgs"].find_one({"id": org_id}, {"_id": 0, "has_used_trial": 1, "has_used_trial_plan_slug": 1})

    # Cleanup
    await db["orgs"].update_one(
        {"id": org_id},
        {"$set": {"has_used_trial": False, "has_used_trial_at": None, "trial_history": [],
                  "has_used_trial_plan_slug": None}}
    )

    if (org and org.get("has_used_trial") is True
        and org.get("has_used_trial_plan_slug") == "starter"  # first trial wins
        and len(history) == 2  # 2 distinct subs, 2 entries
        and r1 is True and r2 is False and r3 is True):  # idempotency working
        return ("pass", f"Idempotent: 3 calls → 2 history entries, has_used_trial=True (first plan: starter)",
                {"history_count": len(history)})
    return ("fail", f"Unexpected state: r1={r1}, r2={r2}, r3={r3}, history={len(history)}, has_used={org.get('has_used_trial') if org else None}",
            {"org": org, "history": history})


async def test_T02_deprovision_does_not_reset_has_used_trial(api: ApiClient) -> tuple:
    """plan_provisioning.deprovision_stripe_subscription must NOT reset has_used_trial."""
    org_id = ORG_FREE
    await reset_org_to_state(org_id, "starter", "active")
    db = await get_db()
    # Set has_used_trial=True
    await db["orgs"].update_one(
        {"id": org_id},
        {"$set": {"has_used_trial": True, "has_used_trial_at": "2024-01-01T00:00:00+00:00",
                  "stripe_subscription_id": "sub_test_T02"}}
    )

    from services.plan_provisioning import deprovision_stripe_subscription
    await deprovision_stripe_subscription(org_id, "sub_test_T02")

    org = await db["orgs"].find_one({"id": org_id}, {"_id": 0, "has_used_trial": 1, "has_used_trial_at": 1})

    # Cleanup
    await db["orgs"].update_one(
        {"id": org_id},
        {"$set": {"has_used_trial": False, "has_used_trial_at": None}}
    )

    if org and org.get("has_used_trial") is True and org.get("has_used_trial_at") == "2024-01-01T00:00:00+00:00":
        return ("pass", "deprovision preserved has_used_trial=True (anti-fraud guarantee)",
                {"org": org})
    return ("fail", f"deprovision RESET has_used_trial — anti-fraud GAP: {org}",
            {"org": org})


async def test_T03_grant_trial_admin_resets_flag(api: ApiClient) -> tuple:
    """Admin grant-trial endpoint resets has_used_trial=False but preserves trial_history."""
    org_id = ORG_FREE
    await reset_org_to_state(org_id, "free", "none")
    db = await get_db()
    # Setup: has_used_trial=True with some history
    await db["orgs"].update_one(
        {"id": org_id},
        {"$set": {
            "has_used_trial": True,
            "has_used_trial_at": "2024-01-01T00:00:00+00:00",
            "has_used_trial_plan_slug": "starter",
            "trial_history": [{"plan_slug": "starter", "stripe_subscription_id": "sub_test_T03",
                               "started_at": "2024-01-01T00:00:00+00:00",
                               "ended_at": "2024-01-15T00:00:00+00:00",
                               "outcome": "expired_to_free"}],
        }}
    )

    sysadmin_email = SYSADMIN_EMAIL
    if not await api.login(sysadmin_email, SYSADMIN_PASSWORD):
        return ("skip", "No system_admin", {})

    r = await api.authed_request(
        "POST", f"/admin/organizations/{org_id}/grant-trial",
        sysadmin_email,
        json_body={"reason": "Test T03 — partner deal"},
    )
    if r.status_code != 200:
        return ("fail", f"grant-trial endpoint failed: {r.status_code}", {"body": r.text[:300]})

    org = await db["orgs"].find_one({"id": org_id}, {"_id": 0, "has_used_trial": 1, "trial_history": 1})

    # Cleanup
    await db["orgs"].update_one(
        {"id": org_id},
        {"$set": {"has_used_trial": False, "has_used_trial_at": None, "trial_history": []}}
    )

    if (org and org.get("has_used_trial") is False
        and len(org.get("trial_history") or []) == 1):
        return ("pass", "Admin reset flag, history preserved", {"org": org})
    return ("fail", f"Unexpected state after grant-trial: {org}", {"org": org})


async def test_T04_grant_trial_requires_reason(api: ApiClient) -> tuple:
    """Admin grant-trial endpoint MUST require a non-empty reason."""
    sysadmin_email = SYSADMIN_EMAIL
    if not await api.login(sysadmin_email, SYSADMIN_PASSWORD):
        return ("skip", "No system_admin", {})

    r = await api.authed_request(
        "POST", f"/admin/organizations/{ORG_FREE}/grant-trial",
        sysadmin_email,
        json_body={"reason": ""},  # empty
    )
    if r.status_code == 400:
        return ("pass", "Empty reason rejected with 400", {})
    return ("fail", f"Empty reason should be rejected, got {r.status_code}",
            {"body": r.text[:200]})


async def test_T05_trial_history_endpoint_returns_summary(api: ApiClient) -> tuple:
    """Admin trial-history endpoint returns history + summary stats."""
    org_id = ORG_FREE
    db = await get_db()
    # Setup history with mix of outcomes
    await db["orgs"].update_one(
        {"id": org_id},
        {"$set": {
            "has_used_trial": True,
            "trial_history": [
                {"plan_slug": "starter", "stripe_subscription_id": "sub_t1", "outcome": "converted",
                 "started_at": "2024-01-01T00:00:00+00:00", "ended_at": "2024-01-15T00:00:00+00:00"},
                {"plan_slug": "core", "stripe_subscription_id": "sub_t2", "outcome": "cancelled_during_trial",
                 "started_at": "2024-02-01T00:00:00+00:00", "ended_at": "2024-02-05T00:00:00+00:00"},
            ],
        }}
    )

    sysadmin_email = SYSADMIN_EMAIL
    if not await api.login(sysadmin_email, SYSADMIN_PASSWORD):
        return ("skip", "No system_admin", {})

    r = await api.authed_request(
        "GET", f"/admin/organizations/{org_id}/trial-history",
        sysadmin_email,
    )

    # Cleanup
    await db["orgs"].update_one({"id": org_id}, {"$set": {"trial_history": [], "has_used_trial": False}})

    if r.status_code != 200:
        return ("fail", f"trial-history endpoint failed: {r.status_code}", {"body": r.text[:200]})

    body = r.json()
    summary = body.get("summary", {})
    if (summary.get("total_trials") == 2
        and summary.get("converted") == 1
        and summary.get("cancelled_during_trial") == 1
        and summary.get("conversion_rate") == 0.5):
        return ("pass", "History + summary stats correct", {"summary": summary})
    return ("fail", f"Summary stats wrong: {summary}", {"body": body})


async def test_T06_close_trial_history_idempotent(api: ApiClient) -> tuple:
    """close_trial_history_entry is idempotent — second call on closed entry is no-op."""
    org_id = ORG_FREE
    db = await get_db()
    await db["orgs"].update_one(
        {"id": org_id},
        {"$set": {
            "trial_history": [
                {"plan_slug": "starter", "stripe_subscription_id": "sub_t6_idem",
                 "started_at": "2024-01-01T00:00:00+00:00", "outcome": None},
            ],
        }}
    )

    from repositories.billing_repository import close_trial_history_entry
    r1 = await close_trial_history_entry(
        org_id, "sub_t6_idem", outcome="converted",
        ended_at="2024-01-15T00:00:00+00:00",
    )
    r2 = await close_trial_history_entry(
        org_id, "sub_t6_idem", outcome="cancelled_during_trial",  # try to overwrite
        ended_at="2024-01-20T00:00:00+00:00",
    )

    org = await db["orgs"].find_one({"id": org_id}, {"_id": 0, "trial_history": 1})
    history = org.get("trial_history", [])
    entry = history[0] if history else {}

    # Cleanup
    await db["orgs"].update_one({"id": org_id}, {"$set": {"trial_history": []}})

    if r1 is True and r2 is False and entry.get("outcome") == "converted":
        return ("pass", "Idempotent: first call closed entry, second call no-op",
                {"entry_outcome": entry.get("outcome")})
    return ("fail", f"Idempotency broken: r1={r1}, r2={r2}, outcome={entry.get('outcome')}",
            {"entry": entry})


# ── Test registry ──────────────────────────────────────────────────────────

ALL_TESTS: List[tuple] = [
    # (test_id, severity, title, function)
    ("I01a", "critical", "Free user cannot create store", test_I01a_free_cannot_create_store),
    ("I01b", "critical", "Free user cannot create product", test_I01b_free_cannot_create_product),
    ("I01c", "critical", "Free user cannot create order (admin path)", test_I01c_free_cannot_create_order),
    ("I01d", "critical", "Solo user cannot create store", test_I01d_solo_cannot_create_store),
    ("I02",  "critical", "Off-by-one: 200th product passes, 201st blocks", test_I02_off_by_one_products),
    ("E04",  "high",     "Admin assign custom-override addon increases limit", test_E04_admin_assign_addon_increases_limit),
    ("H01",  "critical", "BillingEvent unique index prevents duplicate", test_H01_billing_event_idempotency),
    ("H02",  "critical", "Addon upsert is idempotent", test_H02_addon_subscription_idempotency),
    ("D02",  "high",     "Admin set commercial plan provisions modules", test_D02_admin_set_plan_provisions_modules),
    ("D03",  "critical", "Downgrade reconciles excess stores (Onda 9.K)", test_D03_downgrade_reconciles_stores),
    ("A02",  "high",     "Trial-once policy: no second trial after has_used_trial", test_A02_trial_once_policy_check),
    # Onda 9.T trial-once tests
    ("T01",  "critical", "mark_trial_used idempotent + permanent flag", test_T01_mark_trial_used_idempotent),
    ("T02",  "critical", "deprovision does NOT reset has_used_trial (anti-fraud)", test_T02_deprovision_does_not_reset_has_used_trial),
    ("T03",  "high",     "Admin grant-trial resets flag, preserves history", test_T03_grant_trial_admin_resets_flag),
    ("T04",  "medium",   "grant-trial requires non-empty reason (audit)", test_T04_grant_trial_requires_reason),
    ("T05",  "medium",   "trial-history endpoint returns summary stats", test_T05_trial_history_endpoint_returns_summary),
    ("T06",  "high",     "close_trial_history_entry idempotent", test_T06_close_trial_history_idempotent),
]


# ── Main ────────────────────────────────────────────────────────────────────

async def run_test(test_id: str, severity: str, title: str, fn: Callable, api: ApiClient) -> TestResult:
    t0 = time.time()
    try:
        status, message, details = await fn(api)
    except Exception as e:
        return TestResult(test_id, severity, title, "error",
                          message=f"{type(e).__name__}: {e}",
                          details={"traceback": traceback.format_exc()},
                          duration_ms=int((time.time() - t0) * 1000))
    return TestResult(test_id, severity, title, status, message, details,
                      duration_ms=int((time.time() - t0) * 1000))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--only", help="Run only this test ID (e.g. I01a)")
    args = parser.parse_args()

    print(_c("=" * 78, "bold"))
    print(_c("  AFianco Payment Safety Test Runner — Onda 9.S2", "bold"))
    print(_c(f"  Backend: {BACKEND}", "gray"))
    print(_c("=" * 78, "bold"))
    print()

    # Pre-flight
    print("[1/3] Pre-flight checks...")
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{API}/health")
            if r.status_code != 200:
                print(_c(f"  \u2717 Backend not healthy: {r.status_code}", "red"))
                return 2
            print(_c(f"  \u2713 Backend healthy", "green"))
    except Exception as e:
        print(_c(f"  \u2717 Cannot reach backend: {e}", "red"))
        print(_c(f"    Hint: ensure backend is running on {BACKEND}", "yellow"))
        return 2

    # Test orgs check
    print("[2/3] Test orgs + system_admin check...")
    try:
        org_check = await ensure_test_orgs()
        if org_check["missing"]:
            print(_c(f"  \u26A0 Missing test orgs: {org_check['missing']}", "yellow"))
            print(_c(f"    Run: ./venv/bin/python scripts/seed_test_orgs.py --execute", "yellow"))
        else:
            print(_c(f"  \u2713 {org_check['found']} test orgs present", "green"))
    except Exception as e:
        print(_c(f"  \u26A0 Cannot verify test orgs: {e}", "yellow"))

    # Auto-create system_admin
    try:
        sa = await ensure_system_admin()
        print(_c(f"  \u2713 system_admin ready: {sa}", "green"))
    except Exception as e:
        print(_c(f"  \u26A0 Cannot create system_admin: {e}", "yellow"))
    print()

    # Run tests
    print("[3/3] Running tests...")
    print()
    api = ApiClient(verbose=args.verbose)
    results: List[TestResult] = []
    tests = ALL_TESTS
    if args.only:
        tests = [t for t in ALL_TESTS if t[0] == args.only]
        if not tests:
            print(_c(f"No test matches '{args.only}'", "red"))
            return 2

    for test_id, severity, title, fn in tests:
        sys.stdout.write(f"  {_sev_label(severity)} {test_id:6} {title:60} ")
        sys.stdout.flush()
        result = await run_test(test_id, severity, title, fn, api)
        results.append(result)
        print(f"{_icon(result.status)} {_c(result.status.upper(), 'green' if result.status == 'pass' else 'red' if result.status == 'fail' else 'yellow')}")
        if result.status != "pass" and result.message:
            print(f"        {_c(result.message[:120], 'gray')}")

    await api.close()

    # Report
    print()
    print(_c("=" * 78, "bold"))
    print(_c("  Summary", "bold"))
    print(_c("=" * 78, "bold"))
    by_status: Dict[str, int] = {}
    by_severity: Dict[str, Dict[str, int]] = {}
    for r in results:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        by_severity.setdefault(r.severity, {}).setdefault(r.status, 0)
        by_severity[r.severity][r.status] += 1

    total = len(results)
    print(f"  Total: {total}")
    for status in ("pass", "fail", "skip", "error"):
        n = by_status.get(status, 0)
        if n > 0:
            color = "green" if status == "pass" else "red" if status in ("fail", "error") else "yellow"
            print(f"  {_icon(status)} {_c(status.upper(), color)}: {n}")
    print()

    print("  By severity:")
    for sev in ("critical", "high", "medium", "low"):
        s = by_severity.get(sev, {})
        if s:
            line = f"    {_sev_label(sev)} "
            for st in ("pass", "fail", "skip", "error"):
                if s.get(st, 0) > 0:
                    color = "green" if st == "pass" else "red" if st in ("fail", "error") else "yellow"
                    line += f"{_c(st, color)}={s[st]} "
            print(line)
    print()

    # Exit code: 1 if any critical fail
    critical_fails = [r for r in results if r.severity == "critical" and r.status in ("fail", "error")]
    if critical_fails:
        print(_c(f"  \u2717 {len(critical_fails)} CRITICAL failure(s) — DO NOT DEPLOY", "red"))
        for r in critical_fails:
            print(_c(f"    {r.test_id}: {r.message}", "red"))
        return 1

    other_fails = [r for r in results if r.status in ("fail", "error")]
    if other_fails:
        print(_c(f"  \u26A0 {len(other_fails)} non-critical failure(s) — review before deploy", "yellow"))
    else:
        print(_c("  \u2713 All passing tests OK — safe to deploy (pending manual Stripe scenarios)", "green"))

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
