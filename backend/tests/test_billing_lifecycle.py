"""Tests for v6.0 billing status enforcement and lifecycle sweep.

Tests cover:
  A. Billing gate in module_access.py (_check_billing_gate)
  B. Billing gate integration with check_module_access
  C. Billing lifecycle sweep (billing_lifecycle.py)

All tests mock MongoDB and Stripe — no real connections needed.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend/ is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

from fastapi import HTTPException
from conftest import make_org_doc, make_pricing_plan, make_subscription
from services.module_access import (
    _check_billing_gate,
    _parse_iso_datetime,
    check_module_access,
    build_module_access_status,
    TRIAL_EXPIRED_GRACE_HOURS,
)


# ══════════════════════════════════════════════════════════════════════════════
# A. Pure billing gate tests (_check_billing_gate)
# ══════════════════════════════════════════════════════════════════════════════


class TestBillingGatePure:
    """Test _check_billing_gate as a pure function — no mocking needed."""

    def test_active_status_passes(self):
        """billing_status='active' → no restriction."""
        org = make_org_doc(billing_status="active")
        assert _check_billing_gate(org) is None

    def test_none_status_passes(self):
        """billing_status='none' → no restriction (free tier / signup)."""
        org = make_org_doc(billing_status="none")
        assert _check_billing_gate(org) is None

    def test_manual_status_passes(self):
        """billing_status='manual' → no restriction (admin override)."""
        org = make_org_doc(billing_status="manual")
        assert _check_billing_gate(org) is None

    def test_canceled_status_passes(self):
        """billing_status='canceled' → passes (entitlement chain handles it)."""
        org = make_org_doc(billing_status="canceled")
        assert _check_billing_gate(org) is None

    def test_no_org_doc_passes(self):
        """None org_doc → passes (can't check, fail-open)."""
        assert _check_billing_gate(None) is None

    def test_missing_billing_status_passes(self):
        """Org doc without billing_status field → treated as 'none', passes."""
        org = {"id": "org_1", "name": "Test"}
        assert _check_billing_gate(org) is None

    # ── Trialing tests ──────────────────────────────────────────────────

    def test_trialing_valid_passes(self):
        """billing_status='trialing' with trial_ends_at in future → passes."""
        future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        org = make_org_doc(billing_status="trialing", trial_ends_at=future)
        assert _check_billing_gate(org) is None

    def test_trialing_within_grace_passes(self):
        """Trial ended < 2h ago → within grace, passes."""
        # Ended 1 hour ago — within TRIAL_EXPIRED_GRACE_HOURS (2)
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        org = make_org_doc(billing_status="trialing", trial_ends_at=recent)
        assert _check_billing_gate(org) is None

    def test_trialing_expired_restricted(self):
        """Trial ended > 2h ago → BILLING_TRIAL_EXPIRED restriction."""
        expired = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        org = make_org_doc(billing_status="trialing", trial_ends_at=expired)
        result = _check_billing_gate(org)
        assert result is not None
        assert result["code"] == "BILLING_TRIAL_EXPIRED"
        assert result["read_only"] is True

    def test_trialing_expired_long_ago(self):
        """Trial ended days ago → still triggers restriction."""
        expired = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        org = make_org_doc(billing_status="trialing", trial_ends_at=expired)
        result = _check_billing_gate(org)
        assert result is not None
        assert result["code"] == "BILLING_TRIAL_EXPIRED"

    def test_trialing_no_trial_ends_at_passes(self):
        """billing_status='trialing' without trial_ends_at → can't determine, passes."""
        org = make_org_doc(billing_status="trialing")
        assert _check_billing_gate(org) is None

    def test_trialing_invalid_trial_ends_at_passes(self):
        """billing_status='trialing' with malformed trial_ends_at → passes."""
        org = make_org_doc(billing_status="trialing", trial_ends_at="not-a-date")
        assert _check_billing_gate(org) is None

    # ── Past due tests ──────────────────────────────────────────────────

    def test_past_due_within_period_passes(self):
        """billing_status='past_due' with current_period_end in future → passes."""
        future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        org = make_org_doc(billing_status="past_due", current_period_end=future)
        assert _check_billing_gate(org) is None

    def test_past_due_period_ended_restricted(self):
        """billing_status='past_due' with current_period_end in past → restricted."""
        past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        org = make_org_doc(billing_status="past_due", current_period_end=past)
        result = _check_billing_gate(org)
        assert result is not None
        assert result["code"] == "BILLING_PAST_DUE"
        assert result["read_only"] is True

    def test_past_due_no_period_end_restricted(self):
        """billing_status='past_due' with no current_period_end → restricted (conservative)."""
        org = make_org_doc(billing_status="past_due")
        result = _check_billing_gate(org)
        assert result is not None
        assert result["code"] == "BILLING_PAST_DUE"

    def test_past_due_period_end_exactly_now(self):
        """billing_status='past_due' at exact period end boundary."""
        # current_period_end = 1 second in the past — restricted
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        org = make_org_doc(billing_status="past_due", current_period_end=past)
        result = _check_billing_gate(org)
        assert result is not None
        assert result["code"] == "BILLING_PAST_DUE"


# ══════════════════════════════════════════════════════════════════════════════
# B. Integration: billing gate + check_module_access
# ══════════════════════════════════════════════════════════════════════════════


class TestBillingGateIntegration:
    """Test that the billing gate raises 403 from check_module_access."""

    @pytest.mark.asyncio
    async def test_expired_trial_blocks_access(self, mock_sub_repo, mock_usage_repo):
        """Expired trial → 403 BILLING_TRIAL_EXPIRED before entitlement check."""
        expired = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        org_doc = make_org_doc(
            billing_status="trialing",
            trial_ends_at=expired,
            commercial_plan_slug="pro",
        )
        # Even with an active subscription, the billing gate blocks first
        plan = make_pricing_plan(limits={"chat": 50})
        sub = make_subscription()
        mock_sub_repo.get_active_subscription.return_value = sub
        mock_sub_repo.get_pricing_plan.return_value = plan

        with pytest.raises(HTTPException) as exc_info:
            await check_module_access(
                "org_1", "ai_assistant", "chat", org_doc=org_doc,
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "BILLING_TRIAL_EXPIRED"
        # Entitlement check should NOT have been reached
        mock_sub_repo.get_active_subscription.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_past_due_period_ended_blocks_access(self, mock_sub_repo, mock_usage_repo):
        """Past due with expired period → 403 BILLING_PAST_DUE."""
        past = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        org_doc = make_org_doc(
            billing_status="past_due",
            current_period_end=past,
            commercial_plan_slug="core",
        )

        with pytest.raises(HTTPException) as exc_info:
            await check_module_access(
                "org_1", "ai_assistant", "chat", org_doc=org_doc,
            )

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "BILLING_PAST_DUE"

    @pytest.mark.asyncio
    async def test_active_org_passes_normally(self, mock_sub_repo, mock_usage_repo):
        """billing_status='active' → normal entitlement check runs."""
        org_doc = make_org_doc(billing_status="active", commercial_plan_slug="pro")
        plan = make_pricing_plan(limits={"chat": -1})
        sub = make_subscription()
        mock_sub_repo.get_active_subscription.return_value = sub
        mock_sub_repo.get_pricing_plan.return_value = plan

        # Should NOT raise
        await check_module_access("org_1", "ai_assistant", "chat", org_doc=org_doc)
        mock_sub_repo.get_active_subscription.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_valid_trialing_passes_normally(self, mock_sub_repo, mock_usage_repo):
        """billing_status='trialing' with valid trial → normal access."""
        future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        org_doc = make_org_doc(
            billing_status="trialing",
            trial_ends_at=future,
            commercial_plan_slug="core",
        )
        plan = make_pricing_plan(limits={"chat": -1})
        sub = make_subscription()
        mock_sub_repo.get_active_subscription.return_value = sub
        mock_sub_repo.get_pricing_plan.return_value = plan

        await check_module_access("org_1", "ai_assistant", "chat", org_doc=org_doc)
        mock_sub_repo.get_active_subscription.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_manual_org_passes_normally(self, mock_sub_repo, mock_usage_repo):
        """billing_status='manual' → no billing gate, normal check."""
        org_doc = make_org_doc(billing_status="manual", commercial_plan_slug="pro")
        plan = make_pricing_plan(limits={"chat": -1})
        sub = make_subscription()
        mock_sub_repo.get_active_subscription.return_value = sub
        mock_sub_repo.get_pricing_plan.return_value = plan

        await check_module_access("org_1", "ai_assistant", "chat", org_doc=org_doc)
        mock_sub_repo.get_active_subscription.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_free_none_org_passes_normally(self, mock_sub_repo, mock_usage_repo):
        """billing_status='none' (free tier) → normal entitlement chain."""
        org_doc = make_org_doc(billing_status="none", commercial_plan_slug="free")
        plan = make_pricing_plan(limits={"chat": 5})
        sub = make_subscription()
        mock_sub_repo.get_active_subscription.return_value = sub
        mock_sub_repo.get_pricing_plan.return_value = plan

        await check_module_access("org_1", "ai_assistant", "chat", org_doc=org_doc)

    @pytest.mark.asyncio
    async def test_past_due_within_period_passes(self, mock_sub_repo, mock_usage_repo):
        """past_due but current_period_end still in future → no billing gate."""
        future = (datetime.now(timezone.utc) + timedelta(days=15)).isoformat()
        org_doc = make_org_doc(
            billing_status="past_due",
            current_period_end=future,
            commercial_plan_slug="core",
        )
        plan = make_pricing_plan(limits={"chat": -1})
        sub = make_subscription()
        mock_sub_repo.get_active_subscription.return_value = sub
        mock_sub_repo.get_pricing_plan.return_value = plan

        await check_module_access("org_1", "ai_assistant", "chat", org_doc=org_doc)
        mock_sub_repo.get_active_subscription.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_org_doc_loaded_when_not_provided(self, mock_sub_repo, mock_usage_repo):
        """When org_doc is None, check_module_access loads it from repository."""
        org_doc = make_org_doc(billing_status="active")
        plan = make_pricing_plan(limits={"chat": -1})
        sub = make_subscription()
        mock_sub_repo.get_active_subscription.return_value = sub
        mock_sub_repo.get_pricing_plan.return_value = plan

        with patch("repositories.organization_repository") as mock_org_repo:
            mock_org_repo.find_by_id = AsyncMock(return_value=org_doc)
            await check_module_access("org_1", "ai_assistant", "chat")
            mock_org_repo.find_by_id.assert_awaited_once_with("org_1")


# ══════════════════════════════════════════════════════════════════════════════
# C. Billing lifecycle sweep
# ══════════════════════════════════════════════════════════════════════════════


class TestBillingSweep:
    """Test the billing_lifecycle sweep functions."""

    @pytest.mark.asyncio
    async def test_sync_expired_trial_active_in_stripe(self):
        """Expired trial + Stripe says 'active' → sync to active."""
        from services.billing_lifecycle import _sync_expired_trial

        org = make_org_doc(
            billing_status="trialing",
            trial_ends_at=(datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            stripe_subscription_id="sub_test_123",
        )

        mock_stripe_sub = {
            "status": "active",
            "current_period_end": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
        }

        with patch("services.billing_lifecycle._retrieve_stripe_subscription", new_callable=AsyncMock) as mock_retrieve, \
             patch("services.billing_lifecycle.billing_repository") as mock_repo:
            mock_retrieve.return_value = mock_stripe_sub
            mock_repo.update_org_billing_fields = AsyncMock()

            result = await _sync_expired_trial(org)

        assert result["action"] == "synced_active"
        mock_repo.update_org_billing_fields.assert_awaited_once()
        call_args = mock_repo.update_org_billing_fields.call_args
        assert call_args[0][1]["billing_status"] == "active"

    @pytest.mark.asyncio
    async def test_sync_expired_trial_no_stripe_sub(self):
        """Expired trial with no Stripe subscription → revert to free."""
        from services.billing_lifecycle import _sync_expired_trial

        org = make_org_doc(
            billing_status="trialing",
            trial_ends_at=(datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            # No stripe_subscription_id
        )

        with patch("services.plan_provisioning.provision_commercial_plan", new_callable=AsyncMock) as mock_provision:
            mock_provision.return_value = {"cancelled": 0, "created": []}
            result = await _sync_expired_trial(org)

        assert result["action"] == "reverted_to_free"
        assert result["reason"] == "no_stripe_sub"
        mock_provision.assert_awaited_once()
        call_kwargs = mock_provision.call_args[1]
        assert call_kwargs["plan_slug"] == "free"
        assert call_kwargs["assigned_by"] == "billing_sweep"

    @pytest.mark.asyncio
    async def test_sync_expired_trial_canceled_in_stripe(self):
        """Expired trial + Stripe says 'canceled' → deprovision to free."""
        from services.billing_lifecycle import _sync_expired_trial

        org = make_org_doc(
            billing_status="trialing",
            trial_ends_at=(datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            stripe_subscription_id="sub_test_456",
        )

        with patch("services.billing_lifecycle._retrieve_stripe_subscription", new_callable=AsyncMock) as mock_retrieve, \
             patch("services.plan_provisioning.deprovision_stripe_subscription", new_callable=AsyncMock) as mock_deprov:
            mock_retrieve.return_value = {"status": "canceled"}
            mock_deprov.return_value = 2

            result = await _sync_expired_trial(org)

        assert result["action"] == "deprovisioned"
        assert result["stripe_status"] == "canceled"

    @pytest.mark.asyncio
    async def test_sync_stale_past_due_active_in_stripe(self):
        """Stale past_due + Stripe says 'active' → sync to active."""
        from services.billing_lifecycle import _sync_stale_past_due

        org = make_org_doc(
            billing_status="past_due",
            current_period_end=(datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            stripe_subscription_id="sub_test_789",
        )

        mock_stripe_sub = {
            "status": "active",
            "current_period_end": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
        }

        with patch("services.billing_lifecycle._retrieve_stripe_subscription", new_callable=AsyncMock) as mock_retrieve, \
             patch("services.billing_lifecycle.billing_repository") as mock_repo:
            mock_retrieve.return_value = mock_stripe_sub
            mock_repo.update_org_billing_fields = AsyncMock()

            result = await _sync_stale_past_due(org)

        assert result["action"] == "synced_active"
        mock_repo.update_org_billing_fields.assert_awaited_once()
        call_args = mock_repo.update_org_billing_fields.call_args
        assert call_args[0][1]["billing_status"] == "active"

    @pytest.mark.asyncio
    async def test_sync_stale_past_due_canceled_in_stripe(self):
        """Stale past_due + Stripe says 'canceled' → deprovision."""
        from services.billing_lifecycle import _sync_stale_past_due

        org = make_org_doc(
            billing_status="past_due",
            current_period_end=(datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            stripe_subscription_id="sub_test_abc",
        )

        with patch("services.billing_lifecycle._retrieve_stripe_subscription", new_callable=AsyncMock) as mock_retrieve, \
             patch("services.plan_provisioning.deprovision_stripe_subscription", new_callable=AsyncMock) as mock_deprov:
            mock_retrieve.return_value = {"status": "canceled"}
            mock_deprov.return_value = 4

            result = await _sync_stale_past_due(org)

        assert result["action"] == "deprovisioned"

    @pytest.mark.asyncio
    async def test_sweep_skips_on_stripe_error(self):
        """When Stripe API fails, sweep skips that org instead of crashing."""
        from services.billing_lifecycle import _sync_expired_trial

        org = make_org_doc(
            billing_status="trialing",
            trial_ends_at=(datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            stripe_subscription_id="sub_test_err",
        )

        with patch("services.billing_lifecycle._retrieve_stripe_subscription", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.side_effect = Exception("Stripe API timeout")
            result = await _sync_expired_trial(org)

        assert result["action"] == "skipped"
        assert "stripe_error" in result["reason"]

    @pytest.mark.asyncio
    async def test_run_billing_sweep_end_to_end(self):
        """Full sweep: processes expired trials and stale past_due."""
        from services.billing_lifecycle import run_billing_sweep

        expired_org = make_org_doc(
            org_id="org_expired",
            billing_status="trialing",
            trial_ends_at=(datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            stripe_subscription_id="sub_exp",
        )
        stale_org = make_org_doc(
            org_id="org_stale",
            billing_status="past_due",
            current_period_end=(datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            stripe_subscription_id="sub_stale",
        )

        mock_stripe_active = {
            "status": "active",
            "current_period_end": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
        }

        with patch("services.billing_lifecycle.billing_repository") as mock_repo, \
             patch("services.billing_lifecycle._retrieve_stripe_subscription", new_callable=AsyncMock) as mock_retrieve:
            mock_repo.find_expired_trials = AsyncMock(return_value=[expired_org])
            mock_repo.find_stale_past_due = AsyncMock(return_value=[stale_org])
            mock_repo.update_org_billing_fields = AsyncMock()
            mock_retrieve.return_value = mock_stripe_active

            result = await run_billing_sweep()

        assert result["expired_trials_processed"] == 1
        assert result["past_due_processed"] == 1
        assert result["errors"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# D. Helper tests
# ══════════════════════════════════════════════════════════════════════════════


class TestParseIsoDatetime:
    """Test _parse_iso_datetime helper."""

    def test_valid_iso_string(self):
        dt = _parse_iso_datetime("2025-06-15T10:30:00+00:00")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_naive_iso_string_gets_utc(self):
        dt = _parse_iso_datetime("2025-06-15T10:30:00")
        assert dt is not None
        assert dt.tzinfo == timezone.utc

    def test_none_returns_none(self):
        assert _parse_iso_datetime(None) is None

    def test_invalid_string_returns_none(self):
        assert _parse_iso_datetime("not-a-date") is None

    def test_datetime_object_passthrough(self):
        original = datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc)
        result = _parse_iso_datetime(original)
        assert result is original

    def test_naive_datetime_gets_utc(self):
        original = datetime(2025, 6, 15, 10, 30)
        result = _parse_iso_datetime(original)
        assert result.tzinfo == timezone.utc


# ══════════════════════════════════════════════════════════════════════════════
# E. build_module_access_status with billing restriction
# ══════════════════════════════════════════════════════════════════════════════


class TestBuildStatusWithBillingGate:
    """Test that build_module_access_status includes billing restriction info."""

    @pytest.mark.asyncio
    async def test_expired_trial_in_status(self, mock_sub_repo, mock_usage_repo):
        """Expired trial → status payload includes billing_restriction."""
        expired = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        org_doc = make_org_doc(
            billing_status="trialing",
            trial_ends_at=expired,
            commercial_plan_slug="pro",
        )

        plan = make_pricing_plan(limits={"chat": 50})
        sub = make_subscription()
        mock_sub_repo.get_active_subscription.return_value = sub
        mock_sub_repo.get_pricing_plan.return_value = plan

        result = await build_module_access_status(
            "org_1", "ai_assistant", org_doc=org_doc,
        )

        assert result["read_only"] is True
        assert result["billing_restriction"] == "BILLING_TRIAL_EXPIRED"

    @pytest.mark.asyncio
    async def test_active_org_no_restriction(self, mock_sub_repo, mock_usage_repo):
        """Active org → no billing_restriction in status."""
        org_doc = make_org_doc(billing_status="active")

        plan = make_pricing_plan(limits={"chat": 50})
        sub = make_subscription()
        mock_sub_repo.get_active_subscription.return_value = sub
        mock_sub_repo.get_pricing_plan.return_value = plan
        mock_usage_repo.count_usage.return_value = 5

        result = await build_module_access_status(
            "org_1", "ai_assistant", org_doc=org_doc,
        )

        assert result["read_only"] is False
        assert result["billing_restriction"] is None
