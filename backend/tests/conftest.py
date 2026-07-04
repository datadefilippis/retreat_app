"""Shared fixtures for subscription/gating tests.

All tests mock MongoDB — no real DB connection needed.
"""

import os
import sys
from pathlib import Path

# Set required env vars BEFORE importing any backend modules.
# The import chain touches auth.py which requires JWT_SECRET_KEY at import time.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
# Track O Step 4.2 — disable HIBP password breach check in tests by
# default. Tests che vogliono verify HIBP integration (es. O4.2 sentinel
# class) override esplicitamente via monkeypatch.setenv o passano
# direttamente a is_password_breached (mockable). Senza questo bypass,
# signup/reset tests userebbero password reali HIBP-known (es.
# "StrongPass123!") e fallirebbero spuriamente.
os.environ.setdefault("PASSWORD_BREACH_CHECK_ENABLED", "false")
# Track E Step 1.5 — disable Sentry in tests. Without empty DSN, Sentry
# tenta send pending events at atexit → "Waiting up to 2 seconds" hang
# se test mock set_tag o trigger Sentry hub internal errors.
os.environ.setdefault("SENTRY_DSN", "")
# Force-disable Sentry SDK entirely (DSN=None) per evitare integration
# auto-init (FastApiIntegration crea transactions per request → atexit
# flush queue hangs CI).
try:
    import sentry_sdk as _sentry_sdk
    _sentry_sdk.init(dsn=None)
except Exception:
    pass


# Track E Step 1.5 — session-finalizer per Sentry hub.
# FastApiIntegration capture spans on TestClient request anche con DSN
# None → atexit flush hangs 2s. Forziamo close timeout=0 a fine session.
def _shutdown_sentry_at_session_end():
    try:
        import sentry_sdk as _s
        # Sentry SDK 2.x API
        client = _s.get_client() if hasattr(_s, "get_client") else None
        if client and hasattr(client, "close"):
            client.close(timeout=0.0)
    except Exception:
        pass


import atexit  # noqa: E402
atexit.register(_shutdown_sentry_at_session_end)

from unittest.mock import AsyncMock, patch

import pytest

# Ensure backend/ is on sys.path so service imports work
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# Fake data builders
# ---------------------------------------------------------------------------

def make_org_doc(
    org_id="org_1",
    plan="free",
    currency="EUR",
    is_active=True,
    # v6.0: billing gate fields
    billing_status="none",
    commercial_plan_slug="free",
    trial_ends_at=None,
    current_period_end=None,
    stripe_subscription_id=None,
    cancel_at_period_end=False,
):
    doc = {
        "id": org_id,
        "name": "Test Org",
        "plan": plan,
        "currency": currency,
        "is_active": is_active,
        "billing_status": billing_status,
        "commercial_plan_slug": commercial_plan_slug,
        "cancel_at_period_end": cancel_at_period_end,
    }
    if trial_ends_at is not None:
        doc["trial_ends_at"] = trial_ends_at
    if current_period_end is not None:
        doc["current_period_end"] = current_period_end
    if stripe_subscription_id is not None:
        doc["stripe_subscription_id"] = stripe_subscription_id
    return doc


def make_pricing_plan(
    plan_id="plan_1",
    module_key="ai_assistant",
    slug="ai_assistant_starter",
    name="AI Starter",
    limits=None,
):
    return {
        "id": plan_id,
        "module_key": module_key,
        "slug": slug,
        "name": name,
        "price_monthly": 29.0,
        "limits": limits or {"chat": 50, "digest": 4, "alert_analysis": -1, "health_explanation": -1},
        "is_active": True,
    }


def make_subscription(
    sub_id="sub_1",
    org_id="org_1",
    module_key="ai_assistant",
    pricing_plan_id="plan_1",
    status="active",
):
    return {
        "id": sub_id,
        "organization_id": org_id,
        "module_key": module_key,
        "pricing_plan_id": pricing_plan_id,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Reusable mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_sub_repo():
    """Patch subscription_repository with AsyncMock callables."""
    with patch("services.module_access.subscription_repository") as m:
        m.get_active_subscription = AsyncMock(return_value=None)
        m.get_pricing_plan = AsyncMock(return_value=None)
        m.get_pricing_plan_by_slug = AsyncMock(return_value=None)
        # v5.1: Grace period support — default to no recently cancelled sub
        m.get_recently_cancelled_subscription = AsyncMock(return_value=None)
        yield m


@pytest.fixture
def mock_usage_repo():
    """Patch usage_repository in module_access with AsyncMock."""
    with patch("services.module_access.usage_repository") as m:
        m.count_usage = AsyncMock(return_value=0)
        m.record_usage = AsyncMock(return_value={"id": "evt_1"})
        yield m


@pytest.fixture
def mock_org_repo():
    """Patch organization_repository in module_access for billing gate org loading.

    Returns a default org doc with billing_status="none" (passes billing gate).
    Tests can override: mock_org_repo.find_by_id.return_value = make_org_doc(billing_status="trialing", ...)
    """
    with patch("repositories.organization_repository") as m:
        m.find_by_id = AsyncMock(return_value=make_org_doc())
        yield m
