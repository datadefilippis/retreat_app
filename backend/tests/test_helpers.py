"""
Shared test helpers for E2E test suites.

Provides robust backend readiness checks, retry logic,
and isolated test organization management.

CRITICAL: Tests MUST use create_test_org() to get an isolated org_id.
Never use the user's production org_id for test data operations.
"""

import asyncio
import sys
import os

# Ensure backend root is on sys.path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from database import (
    organizations_collection, users_collection, orders_collection,
    customers_collection, products_collection, stores_collection,
    blocked_slots_collection, availability_rules_collection,
    customer_accounts_collection, sales_records_collection, db,
)
from models.common import generate_id, utc_now
from auth import get_password_hash

# Fixed password for test users — meets policy (12+ chars, upper, lower, digit)
_TEST_PASSWORD = "TestE2ePass12345!"


async def wait_for_backend(base_url: str = "http://localhost:8000", max_wait: int = 30):
    """Wait until backend is healthy. Retries every 1s up to max_wait seconds.

    Call this before any test suite to ensure the backend is ready,
    especially after file changes that trigger uvicorn --reload.
    """
    health_url = f"{base_url}/api/health"
    for i in range(max_wait):
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                r = await c.get(health_url)
                if r.status_code == 200:
                    return True
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ReadError):
            pass
        if i == 0:
            print("  Waiting for backend...", end="", flush=True)
        elif i % 5 == 0:
            print(".", end="", flush=True)
        await asyncio.sleep(1)

    print(" TIMEOUT")
    raise RuntimeError(f"Backend not healthy after {max_wait}s")


async def create_test_org() -> dict:
    """Create an isolated test organization + admin user for E2E tests.

    Returns dict with keys: org_id, email, password.

    The org_id is a fresh UUID — all test data is scoped to it,
    so cleanup_test_org() only deletes test data, never production.
    """
    now = utc_now()
    org_id = generate_id()
    user_id = generate_id()
    email = f"e2e-{org_id[:8]}@example.com"

    # Insert organization
    org_doc = {
        "id": org_id,
        "name": "E2E Test Org",
        "plan": "free",
        "is_active": True,
        "currency": "EUR",
        "timezone": "Europe/Rome",
        "schema_version": "2.0",
        "created_at": now,
        "updated_at": now,
    }
    await organizations_collection.insert_one(org_doc)

    # Insert admin user (email_verified=True required for login)
    user_doc = {
        "id": user_id,
        "email": email,
        "name": "E2E Admin",
        "role": "admin",
        "organization_id": org_id,
        "password_hash": get_password_hash(_TEST_PASSWORD),
        "is_active": True,
        "email_verified": True,
        "locale": "it",
        "created_at": now,
        "updated_at": now,
    }
    await users_collection.insert_one(user_doc)

    print(f"  🔧 Test org created: {org_id[:8]}... (email: {email})")

    return {
        "org_id": org_id,
        "email": email,
        "password": _TEST_PASSWORD,
    }


async def cleanup_test_org(org_id: str):
    """Delete ALL data for the given org_id. Safe by design — org_id is
    a fresh UUID created by create_test_org(), so it cannot match
    production data.
    """
    filter_ = {"organization_id": org_id}

    # Transactional collections
    for name, coll in [
        ("orders", orders_collection),
        ("customers", customers_collection),
        ("products", products_collection),
        ("stores", stores_collection),
        ("blocked_slots", blocked_slots_collection),
        ("availability_rules", availability_rules_collection),
        ("customer_accounts", customer_accounts_collection),
        ("sales_records", sales_records_collection),
    ]:
        r = await coll.delete_many(filter_)
        if r.deleted_count:
            print(f"  🧹 Cleanup {name}: {r.deleted_count}")

    # Non-standard collections
    await db.event_occurrences.delete_many(filter_)
    await db.order_counters.delete_many(filter_)
    await db.coupons.delete_many(filter_)

    # Organization + user docs
    await organizations_collection.delete_one({"id": org_id})
    await users_collection.delete_many({"organization_id": org_id})

    print(f"  🧹 Test org cleaned up: {org_id[:8]}...")
