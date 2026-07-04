"""
Tests for admin plan change + Stripe cancellation fix.

Simulates all billing scenarios from both admin and user perspectives
to verify no double billing occurs and all states are consistent.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services import plan_provisioning


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mock_org(plan="free", stripe_sub_id=None, billing_status="none"):
    """Build a fake org billing summary."""
    return {
        "commercial_plan_slug": plan,
        "billing_status": billing_status,
        "stripe_subscription_id": stripe_sub_id,
        "stripe_customer_id": "cus_test" if stripe_sub_id else None,
        "cancel_at_period_end": False,
    }


def _mock_commercial_plan(slug, module_plans=None):
    """Build a fake commercial plan."""
    return {
        "slug": slug,
        "name": slug.title(),
        "module_plans": module_plans or {"cashflow_monitor": f"cashflow_monitor_{slug}"},
    }


def _mock_pricing_plan(module_key, slug):
    return {"id": f"pp_{slug}", "slug": slug, "module_key": module_key, "limits": {}}


# ── Test: _cancel_org_stripe_subscription ────────────────────────────────────

class TestCancelOrgStripeSubscription:

    @pytest.mark.asyncio
    async def test_no_stripe_sub_returns_none(self):
        """Org without Stripe sub → no action, returns None."""
        with patch.object(
            plan_provisioning.billing_repository,
            "get_org_billing_summary",
            new_callable=AsyncMock,
            return_value=_mock_org(plan="free", stripe_sub_id=None),
        ):
            result = await plan_provisioning._cancel_org_stripe_subscription("org_1")
            assert result is None

    @pytest.mark.asyncio
    async def test_with_stripe_sub_cancels_and_returns_id(self):
        """Org with Stripe sub → cancels it, returns sub ID."""
        with patch.object(
            plan_provisioning.billing_repository,
            "get_org_billing_summary",
            new_callable=AsyncMock,
            return_value=_mock_org(plan="core", stripe_sub_id="sub_abc123", billing_status="active"),
        ), patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_fake"}), \
           patch("stripe.Subscription") as mock_stripe_sub:
            mock_stripe_sub.cancel = MagicMock()

            result = await plan_provisioning._cancel_org_stripe_subscription("org_1")

            assert result == "sub_abc123"
            mock_stripe_sub.cancel.assert_called_once_with("sub_abc123")

    @pytest.mark.asyncio
    async def test_stripe_failure_logs_warning_no_raise(self):
        """Stripe cancel fails → logs warning, returns sub ID anyway (best-effort)."""
        with patch.object(
            plan_provisioning.billing_repository,
            "get_org_billing_summary",
            new_callable=AsyncMock,
            return_value=_mock_org(plan="core", stripe_sub_id="sub_fail", billing_status="active"),
        ), patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_fake"}), \
           patch("stripe.Subscription") as mock_stripe_sub:
            mock_stripe_sub.cancel = MagicMock(side_effect=Exception("Stripe API error"))

            # Should NOT raise — best effort
            result = await plan_provisioning._cancel_org_stripe_subscription("org_1")
            assert result == "sub_fail"

    @pytest.mark.asyncio
    async def test_no_stripe_key_skips_cancel(self):
        """No STRIPE_SECRET_KEY → skips cancel, returns sub ID."""
        with patch.object(
            plan_provisioning.billing_repository,
            "get_org_billing_summary",
            new_callable=AsyncMock,
            return_value=_mock_org(plan="core", stripe_sub_id="sub_nokey", billing_status="active"),
        ), patch.dict("os.environ", {"STRIPE_SECRET_KEY": ""}):
            result = await plan_provisioning._cancel_org_stripe_subscription("org_1")
            assert result == "sub_nokey"


# ── Test: admin_set_plan scenarios ───────────────────────────────────────────

class TestAdminSetPlanScenarios:
    """Simulate all admin plan change scenarios end-to-end."""

    def _patch_all(self, org_doc, plan_doc, pricing_plan_doc):
        """Return a context manager that patches all dependencies."""
        from contextlib import ExitStack
        stack = ExitStack()

        stack.enter_context(patch.object(
            plan_provisioning.billing_repository,
            "get_org_billing_summary",
            new_callable=AsyncMock,
            return_value=org_doc,
        ))
        stack.enter_context(patch.object(
            plan_provisioning.billing_repository,
            "get_commercial_plan",
            new_callable=AsyncMock,
            return_value=plan_doc,
        ))
        stack.enter_context(patch.object(
            plan_provisioning.billing_repository,
            "update_org_billing_fields",
            new_callable=AsyncMock,
        ))
        stack.enter_context(patch.object(
            plan_provisioning.subscription_repository,
            "list_subscriptions_by_org",
            new_callable=AsyncMock,
            return_value=[],
        ))
        stack.enter_context(patch.object(
            plan_provisioning.subscription_repository,
            "get_pricing_plan_by_slug",
            new_callable=AsyncMock,
            return_value=pricing_plan_doc,
        ))
        stack.enter_context(patch.object(
            plan_provisioning.subscription_repository,
            "create_subscription",
            new_callable=AsyncMock,
        ))
        stack.enter_context(patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_fake"}))

        return stack

    # ── Scenario A: Free → Core (admin) ──────────────────────────────────────

    @pytest.mark.asyncio
    async def test_free_to_core_no_stripe_to_cancel(self):
        """Free org → Core via admin: no Stripe sub exists, clean provision."""
        org = _mock_org(plan="free", stripe_sub_id=None)
        plan = _mock_commercial_plan("core")
        pp = _mock_pricing_plan("cashflow_monitor", "cashflow_monitor_core")

        with self._patch_all(org, plan, pp):
            result = await plan_provisioning.admin_set_plan("org_1", "core", "admin_1")

            assert result["plan_slug"] == "core"
            assert "cancelled_stripe_sub" not in result

            # Verify Stripe fields cleared
            plan_provisioning.billing_repository.update_org_billing_fields.assert_any_call(
                "org_1",
                {"stripe_subscription_id": None, "cancel_at_period_end": False},
            )

    # ── Scenario B: Core (Stripe) → Free (admin downgrade) ──────────────────

    @pytest.mark.asyncio
    async def test_core_stripe_to_free_cancels_stripe(self):
        """Core org with Stripe sub → Free via admin: Stripe sub must be cancelled."""
        org = _mock_org(plan="core", stripe_sub_id="sub_core_123", billing_status="active")
        plan = _mock_commercial_plan("free")
        pp = _mock_pricing_plan("cashflow_monitor", "cashflow_monitor_free")

        with self._patch_all(org, plan, pp), \
             patch("stripe.Subscription") as mock_stripe:
            mock_stripe.cancel = MagicMock()

            result = await plan_provisioning.admin_set_plan("org_1", "free", "admin_1")

            assert result["plan_slug"] == "free"
            assert result["cancelled_stripe_sub"] == "sub_core_123"
            mock_stripe.cancel.assert_called_once_with("sub_core_123")

    # ── Scenario C: Pro (Stripe) → Core (admin downgrade) ───────────────────

    @pytest.mark.asyncio
    async def test_pro_stripe_to_core_cancels_stripe(self):
        """Pro org with Stripe → Core via admin: old Stripe sub cancelled."""
        org = _mock_org(plan="pro", stripe_sub_id="sub_pro_456", billing_status="active")
        plan = _mock_commercial_plan("core")
        pp = _mock_pricing_plan("cashflow_monitor", "cashflow_monitor_core")

        with self._patch_all(org, plan, pp), \
             patch("stripe.Subscription") as mock_stripe:
            mock_stripe.cancel = MagicMock()

            result = await plan_provisioning.admin_set_plan("org_1", "core", "admin_1")

            assert result["plan_slug"] == "core"
            assert result["cancelled_stripe_sub"] == "sub_pro_456"
            mock_stripe.cancel.assert_called_once_with("sub_pro_456")

    # ── Scenario D: Core (manual) → Pro (admin upgrade) ─────────────────────

    @pytest.mark.asyncio
    async def test_manual_core_to_pro_no_stripe(self):
        """Core org (manual, no Stripe) → Pro: no Stripe to cancel."""
        org = _mock_org(plan="core", stripe_sub_id=None, billing_status="manual")
        plan = _mock_commercial_plan("pro")
        pp = _mock_pricing_plan("cashflow_monitor", "cashflow_monitor_pro")

        with self._patch_all(org, plan, pp):
            result = await plan_provisioning.admin_set_plan("org_1", "pro", "admin_1")

            assert result["plan_slug"] == "pro"
            assert "cancelled_stripe_sub" not in result

    # ── Scenario E: Trialing → Free (admin kills trial) ─────────────────────

    @pytest.mark.asyncio
    async def test_trialing_to_free_cancels_stripe(self):
        """Trialing org → Free via admin: Stripe trial sub cancelled."""
        org = _mock_org(plan="core", stripe_sub_id="sub_trial_789", billing_status="trialing")
        plan = _mock_commercial_plan("free")
        pp = _mock_pricing_plan("cashflow_monitor", "cashflow_monitor_free")

        with self._patch_all(org, plan, pp), \
             patch("stripe.Subscription") as mock_stripe:
            mock_stripe.cancel = MagicMock()

            result = await plan_provisioning.admin_set_plan("org_1", "free", "admin_1")

            assert result["cancelled_stripe_sub"] == "sub_trial_789"
            mock_stripe.cancel.assert_called_once_with("sub_trial_789")

    # ── Scenario F: Past-due → Free (admin resolves) ────────────────────────

    @pytest.mark.asyncio
    async def test_past_due_to_free_cancels_stripe(self):
        """Past-due org → Free via admin: Stripe sub cancelled, stops retries."""
        org = _mock_org(plan="pro", stripe_sub_id="sub_pastdue", billing_status="past_due")
        plan = _mock_commercial_plan("free")
        pp = _mock_pricing_plan("cashflow_monitor", "cashflow_monitor_free")

        with self._patch_all(org, plan, pp), \
             patch("stripe.Subscription") as mock_stripe:
            mock_stripe.cancel = MagicMock()

            result = await plan_provisioning.admin_set_plan("org_1", "free", "admin_1")

            assert result["cancelled_stripe_sub"] == "sub_pastdue"
            mock_stripe.cancel.assert_called_once_with("sub_pastdue")

    # ── Scenario G: Same plan reassign (admin) ──────────────────────────────

    @pytest.mark.asyncio
    async def test_same_plan_reassign_clears_stripe(self):
        """Admin reassigns same plan: Stripe sub still cancelled (clean state)."""
        org = _mock_org(plan="core", stripe_sub_id="sub_same", billing_status="active")
        plan = _mock_commercial_plan("core")
        pp = _mock_pricing_plan("cashflow_monitor", "cashflow_monitor_core")

        with self._patch_all(org, plan, pp), \
             patch("stripe.Subscription") as mock_stripe:
            mock_stripe.cancel = MagicMock()

            result = await plan_provisioning.admin_set_plan("org_1", "core", "admin_1")

            # Even same plan: Stripe cancelled because admin override = manual
            assert result["cancelled_stripe_sub"] == "sub_same"

    # ── Scenario H: Stripe fields cleared after admin set ────────────────────

    @pytest.mark.asyncio
    async def test_stripe_fields_cleared_after_admin_set(self):
        """After admin_set_plan, stripe_subscription_id and cancel_at_period_end are cleared."""
        org = _mock_org(plan="core", stripe_sub_id="sub_clear", billing_status="active")
        plan = _mock_commercial_plan("pro")
        pp = _mock_pricing_plan("cashflow_monitor", "cashflow_monitor_pro")

        with self._patch_all(org, plan, pp), \
             patch("stripe.Subscription") as mock_stripe:
            mock_stripe.cancel = MagicMock()

            await plan_provisioning.admin_set_plan("org_1", "pro", "admin_1")

            # Check the LAST call to update_org_billing_fields (the cleanup call)
            calls = plan_provisioning.billing_repository.update_org_billing_fields.call_args_list
            cleanup_call = calls[-1]
            assert cleanup_call[0][0] == "org_1"
            assert cleanup_call[0][1] == {
                "stripe_subscription_id": None,
                "cancel_at_period_end": False,
            }
