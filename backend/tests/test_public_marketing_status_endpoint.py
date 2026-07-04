"""Sentinel tests for the public marketing-status endpoint
(2026-05-20).

The endpoint ``GET /api/public/storefront/{slug}/marketing-status``
powers the guest checkout's "is this email already opted-in?" check.
The frontend hides the marketing checkbox at checkout when the
response is ``{opted_in: true}`` (the customer is already iscritto;
re-displaying the box would confuse them).

Invariants pinned by these sentinels:
  1. Endpoint returns ``opted_in=true`` for an email that has
     ``accepted_marketing_at`` AND no later ``marketing_revoked_at``.
  2. Endpoint returns ``opted_in=false`` for an email that was
     revoked after opting in (most-recent-wins).
  3. Endpoint returns ``opted_in=false`` UNIFORMLY for emails not
     present in the CRM — indistinguishable from a known-not-opted
     case, mitigating email enumeration.
  4. Email matching is case-insensitive (stored byte-lowercase by
     repository normalisation; the endpoint normalises input).
  5. Cache headers: ``Cache-Control: private, no-store`` (the
     answer is per-email, never cache).

The endpoint also enforces a 10/min/IP rate limit via slowapi; that
guard is tested indirectly by the slowapi integration tests of the
auth router and we don't re-test the same library here.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# The @limiter.limit decorator on the endpoint does an
# ``isinstance(request, Request)`` check that's awkward to satisfy
# from a unit test (real Request needs the full ASGI scope).
# Disabling the limiter is cleaner — we're not testing rate-limit
# behaviour here, just the lookup logic. Same pattern as
# test_catalog_n_plus_one.py.
@pytest.fixture(autouse=True)
def _disable_rate_limiter():
    from routers.auth import limiter
    original = limiter.enabled
    limiter.enabled = False
    try:
        yield
    finally:
        limiter.enabled = original


def _org(org_id: str = "org-1") -> dict:
    """Minimal org stub the endpoint's _resolve_org returns."""
    return {"id": org_id, "name": "Acme SRL", "_store": {"id": "store-1"}}


# ─── Endpoint contract ───────────────────────────────────────────────


class TestMarketingStatusEndpoint:
    """The endpoint reads from customers.{accepted,revoked}_marketing_at
    with most-recent-wins semantics. The customer is keyed by
    (organization_id, lowercased email)."""

    @pytest.mark.asyncio
    async def test_opted_in_email_returns_true(self):
        from routers.public import get_public_marketing_status

        with patch("routers.public._resolve_org", new=AsyncMock(return_value=_org())), \
             patch("database.customers_collection.find_one",
                   new=AsyncMock(return_value={
                       "accepted_marketing_at": "2026-05-20T10:00:00+00:00",
                       "marketing_revoked_at": None,
                   })):
            from fastapi import Response
            response = Response()
            result = await get_public_marketing_status(
                request=_FakeRequest(),
                response=response,
                slug="acme",
                email="known@example.com",
            )
        assert result == {"opted_in": True}
        # Privacy header pinned.
        assert response.headers.get("cache-control") == "private, no-store"

    @pytest.mark.asyncio
    async def test_revoked_after_optin_returns_false(self):
        """Most-recent-wins: revoke after opt-in → opted_in=false."""
        from routers.public import get_public_marketing_status

        with patch("routers.public._resolve_org", new=AsyncMock(return_value=_org())), \
             patch("database.customers_collection.find_one",
                   new=AsyncMock(return_value={
                       "accepted_marketing_at": "2026-05-20T10:00:00+00:00",
                       "marketing_revoked_at": "2026-05-20T12:00:00+00:00",
                   })):
            from fastapi import Response
            response = Response()
            result = await get_public_marketing_status(
                request=_FakeRequest(),
                response=response,
                slug="acme",
                email="revoked@example.com",
            )
        assert result == {"opted_in": False}

    @pytest.mark.asyncio
    async def test_reoptin_after_revoke_returns_true(self):
        """Most-recent-wins symmetric: opt-in after revoke wins."""
        from routers.public import get_public_marketing_status

        with patch("routers.public._resolve_org", new=AsyncMock(return_value=_org())), \
             patch("database.customers_collection.find_one",
                   new=AsyncMock(return_value={
                       "accepted_marketing_at": "2026-05-20T15:00:00+00:00",
                       "marketing_revoked_at": "2026-05-20T12:00:00+00:00",
                   })):
            from fastapi import Response
            response = Response()
            result = await get_public_marketing_status(
                request=_FakeRequest(),
                response=response,
                slug="acme",
                email="reopted@example.com",
            )
        assert result == {"opted_in": True}

    @pytest.mark.asyncio
    async def test_unknown_email_returns_false_uniformly(self):
        """Privacy guard: an email that doesn't exist in CRM returns
        the same shape as a known-but-not-opted email. Mitigates
        email enumeration by making membership indistinguishable
        from non-membership."""
        from routers.public import get_public_marketing_status

        with patch("routers.public._resolve_org", new=AsyncMock(return_value=_org())), \
             patch("database.customers_collection.find_one",
                   new=AsyncMock(return_value=None)):
            from fastapi import Response
            response = Response()
            result = await get_public_marketing_status(
                request=_FakeRequest(),
                response=response,
                slug="acme",
                email="never-seen@example.com",
            )
        assert result == {"opted_in": False}

    @pytest.mark.asyncio
    async def test_email_lookup_is_lowercased(self):
        """The repository stores emails lowercased; the endpoint
        normalises input the same way. Mixed-case input must hit
        the same row that a fully-lowercase input would."""
        from routers.public import get_public_marketing_status

        captured = {}

        async def _capture(query, projection):
            captured["query"] = query
            return {
                "accepted_marketing_at": "2026-05-20T10:00:00+00:00",
                "marketing_revoked_at": None,
            }

        with patch("routers.public._resolve_org", new=AsyncMock(return_value=_org())), \
             patch("database.customers_collection.find_one", new=_capture):
            from fastapi import Response
            response = Response()
            result = await get_public_marketing_status(
                request=_FakeRequest(),
                response=response,
                slug="acme",
                email="Mario.ROSSI@Example.COM  ",
            )
        # The lookup query must use the lowercased+stripped form.
        assert captured["query"]["email"] == "mario.rossi@example.com"
        assert result == {"opted_in": True}

    @pytest.mark.asyncio
    async def test_malformed_email_safe_default(self):
        """An email without '@' is a programmer/typo error. The
        endpoint returns the safe default (False) rather than 400 —
        the frontend can keep flowing without an error toast."""
        from routers.public import get_public_marketing_status

        with patch("routers.public._resolve_org", new=AsyncMock(return_value=_org())):
            from fastapi import Response
            response = Response()
            result = await get_public_marketing_status(
                request=_FakeRequest(),
                response=response,
                slug="acme",
                email="not-an-email",
            )
        assert result == {"opted_in": False}


# ─── Helpers ─────────────────────────────────────────────────────────


class _FakeRequest:
    """Minimal Request stub — slowapi's limiter inspects .state +
    .headers + .client; for tests calling the function directly we
    bypass the limiter via the decorator's slowapi-aware behaviour."""

    def __init__(self):
        from types import SimpleNamespace
        self.state = SimpleNamespace()
        self.headers = {}

        class _Client:
            host = "127.0.0.1"
        self.client = _Client()
        self.url = SimpleNamespace(path="/api/public/storefront/acme/marketing-status")
        self.method = "GET"
        self.scope = {"type": "http", "path": "/api/public/storefront/acme/marketing-status"}
