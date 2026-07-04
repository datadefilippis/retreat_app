"""Tests for the in-process capabilities cache + force_refresh bypass.

The Settings → Metodi di pagamento card reads
``GET /organizations/current/payment-capabilities``. Because the call
fans out to Stripe's API per request, we cache the response in-process
for 5 minutes (``_CAPABILITIES_TTL_SECONDS``). The ↻ refresh button on
the card passes ``?force_refresh=true`` so a merchant who just toggled
TWINT off on the Stripe dashboard sees the change immediately, instead
of waiting out the TTL.

These tests pin both halves of the contract:
  1. Plain calls hit the cache after the first miss (rate-limit Stripe).
  2. ``force_refresh=true`` bypasses AND evicts the cache so the next
     plain call also gets a fresh value (no stale read after refresh).
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from payment_providers import AccountCapabilities
from routers import organizations as orgs_router


@pytest.fixture
def reset_cache():
    """Clear the in-process cache before and after each test."""
    orgs_router._capabilities_cache.clear()
    yield
    orgs_router._capabilities_cache.clear()


def _fake_user(org_id="org_test"):
    return {"organization_id": org_id, "user_id": "u1", "email": "u1@t.com"}


async def _run_endpoint(force_refresh=False, fake_caps=None,
                        org_currency="CHF", account_id="acct_x"):
    """Drive get_payment_capabilities() with all DB/Stripe stubbed.

    Returns the response dict and the AsyncMock used to count provider
    calls so the caller can assert cache hits/misses.
    """
    if fake_caps is None:
        fake_caps = AccountCapabilities(card_active=True, twint_active=True)

    org_doc = {"id": "org_test", "currency": org_currency}

    fake_provider = AsyncMock()
    fake_provider.name = "stripe"
    fake_provider.get_account_capabilities = AsyncMock(return_value=fake_caps)

    with patch.object(orgs_router.organization_repository, "find_by_id",
                      new_callable=AsyncMock, return_value=org_doc), \
         patch("services.payment_checkout_service._get_connected_account_id",
               new_callable=AsyncMock, return_value=account_id), \
         patch("payment_providers.PaymentProviderRegistry.get_for_org",
               return_value=fake_provider):
        result = await orgs_router.get_payment_capabilities(
            current_user=_fake_user(),
            force_refresh=force_refresh,
        )
    return result, fake_provider.get_account_capabilities


# ── 1. Cache populates on first call, hits on subsequent ──────────────────


@pytest.mark.asyncio
async def test_first_call_misses_cache_and_populates(reset_cache):
    """First call → Stripe round-trip + cache write."""
    result, mock_caps = await _run_endpoint()
    assert result["status"] == "ok"
    assert result["capabilities"]["twint_active"] is True
    assert mock_caps.call_count == 1
    # Cache populated
    assert ("org_test", "acct_x") in orgs_router._capabilities_cache


@pytest.mark.asyncio
async def test_second_plain_call_hits_cache(reset_cache):
    """Within TTL, plain calls reuse the cached AccountCapabilities."""
    _, mock_caps_1 = await _run_endpoint()
    assert mock_caps_1.call_count == 1

    # Note: each _run_endpoint creates a new fake_provider mock, so the
    # cache hit is observable as: result returned *without* invoking the
    # second mock at all. Track via the actual cached value being reused.
    cached_before = orgs_router._capabilities_cache[("org_test", "acct_x")]
    _, mock_caps_2 = await _run_endpoint()
    cached_after = orgs_router._capabilities_cache[("org_test", "acct_x")]

    # If the cache hit, the timestamp must NOT have moved.
    assert cached_before[0] == cached_after[0]
    # And the second provider mock must not have been invoked.
    assert mock_caps_2.call_count == 0


# ── 2. force_refresh bypasses + evicts ────────────────────────────────────


@pytest.mark.asyncio
async def test_force_refresh_bypasses_cache_even_if_fresh(reset_cache):
    """force_refresh=True must hit the provider even with a fresh cache."""
    # Prime the cache.
    await _run_endpoint()
    assert ("org_test", "acct_x") in orgs_router._capabilities_cache

    # Force-refresh call — must round-trip even though entry is fresh.
    _, mock_caps = await _run_endpoint(force_refresh=True)
    assert mock_caps.call_count == 1


@pytest.mark.asyncio
async def test_force_refresh_evicts_so_next_plain_call_also_fresh(reset_cache):
    """A plain call right after force_refresh must read the fresh value
    (i.e. force_refresh must repopulate, not just bypass once).

    Without eviction-then-repopulate, the sequence
    [plain → force_refresh → plain] would: 1) populate stale, 2) bypass
    + return fresh, 3) read the STALE plain entry again. We pin against
    that footgun.
    """
    # Step 1: prime cache with stale_caps.
    stale = AccountCapabilities(card_active=True, twint_active=True)
    await _run_endpoint(fake_caps=stale)
    assert orgs_router._capabilities_cache[("org_test", "acct_x")][1].twint_active is True

    # Step 2: force-refresh with NEW value (twint disabled on Stripe side).
    fresh = AccountCapabilities(card_active=True, twint_active=False)
    result, _ = await _run_endpoint(force_refresh=True, fake_caps=fresh)
    assert result["capabilities"]["twint_active"] is False

    # Step 3: subsequent plain call reads the freshly cached value, not stale.
    cached = orgs_router._capabilities_cache[("org_test", "acct_x")]
    assert cached[1].twint_active is False, (
        "force_refresh must REPOPULATE the cache with the fresh value, "
        "otherwise a follow-up plain call would re-read the stale entry"
    )


# ── 3. Provider failure with force_refresh leaves no stale entry ─────────


@pytest.mark.asyncio
async def test_provider_error_during_force_refresh_does_not_resurrect_stale(reset_cache):
    """If Stripe fails during a force_refresh, the cache stays empty
    (we evicted before the call). The user sees status=error with a
    truthful "could not reach provider" message — better than serving
    a stale-cache-pretending-to-be-fresh value.
    """
    from payment_providers import ProviderError

    # Step 1: prime cache.
    await _run_endpoint()
    assert ("org_test", "acct_x") in orgs_router._capabilities_cache

    # Step 2: force_refresh while provider raises ProviderError.
    org_doc = {"id": "org_test", "currency": "CHF"}
    failing_provider = AsyncMock()
    failing_provider.name = "stripe"
    failing_provider.get_account_capabilities = AsyncMock(
        side_effect=ProviderError("rate_limit"),
    )

    with patch.object(orgs_router.organization_repository, "find_by_id",
                      new_callable=AsyncMock, return_value=org_doc), \
         patch("services.payment_checkout_service._get_connected_account_id",
               new_callable=AsyncMock, return_value="acct_x"), \
         patch("payment_providers.PaymentProviderRegistry.get_for_org",
               return_value=failing_provider):
        result = await orgs_router.get_payment_capabilities(
            current_user=_fake_user(),
            force_refresh=True,
        )

    assert result["status"] == "error"
    assert "rate_limit" in (result["error_message"] or "")
    # Cache must NOT be repopulated with stale data.
    assert ("org_test", "acct_x") not in orgs_router._capabilities_cache
