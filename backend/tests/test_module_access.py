"""Tests for services/module_access.py — entitlement resolution and access checks."""

import pytest
from fastapi import HTTPException

from conftest import make_org_doc, make_pricing_plan, make_subscription
from services.module_access import (
    get_module_entitlements,
    check_module_access,
    build_module_access_status,
)


# ── get_module_entitlements ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_entitlements_active_subscription(mock_sub_repo, mock_usage_repo):
    """Active subscription → returns limits from the linked pricing plan."""
    plan = make_pricing_plan(limits={"chat": 50, "digest": 4})
    sub = make_subscription(pricing_plan_id=plan["id"])

    mock_sub_repo.get_active_subscription.return_value = sub
    mock_sub_repo.get_pricing_plan.return_value = plan

    result = await get_module_entitlements("org_1", "ai_assistant")

    assert result["enabled"] is True
    assert result["limits"] == {"chat": 50, "digest": 4}
    assert result["plan_name"] == "AI Starter"
    assert result["plan_slug"] == "ai_assistant_starter"


@pytest.mark.asyncio
async def test_entitlements_fallback_org_plan(mock_sub_repo, mock_usage_repo):
    """No subscription, org.plan='starter' → fallback slug lookup."""
    plan = make_pricing_plan(slug="ai_assistant_starter", limits={"chat": 50})
    mock_sub_repo.get_active_subscription.return_value = None
    mock_sub_repo.get_pricing_plan_by_slug.return_value = plan

    org_doc = make_org_doc(plan="starter")
    result = await get_module_entitlements("org_1", "ai_assistant", org_doc=org_doc)

    assert result["enabled"] is True
    assert result["limits"]["chat"] == 50
    mock_sub_repo.get_pricing_plan_by_slug.assert_awaited_once_with(
        "ai_assistant", "ai_assistant_starter",
    )


@pytest.mark.asyncio
async def test_entitlements_free_plan_disabled(mock_sub_repo, mock_usage_repo):
    """No subscription, org.plan='free' → module disabled (fallback skipped for free)."""
    mock_sub_repo.get_active_subscription.return_value = None

    org_doc = make_org_doc(plan="free")
    result = await get_module_entitlements("org_1", "ai_assistant", org_doc=org_doc)

    assert result["enabled"] is False
    assert result["limits"] == {}


# ── check_module_access ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_access_module_disabled(mock_sub_repo, mock_usage_repo, mock_org_repo):
    """Module not enabled → 403 MODULE_NOT_AVAILABLE."""
    mock_sub_repo.get_active_subscription.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await check_module_access("org_1", "ai_assistant", "chat")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "MODULE_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_check_access_feature_disabled(mock_sub_repo, mock_usage_repo, mock_org_repo):
    """Feature limit = 0 → 403 FEATURE_NOT_AVAILABLE."""
    plan = make_pricing_plan(limits={"chat": 0, "digest": 4})
    sub = make_subscription()
    mock_sub_repo.get_active_subscription.return_value = sub
    mock_sub_repo.get_pricing_plan.return_value = plan

    with pytest.raises(HTTPException) as exc_info:
        await check_module_access("org_1", "ai_assistant", "chat")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "FEATURE_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_check_access_unlimited(mock_sub_repo, mock_usage_repo, mock_org_repo):
    """Feature limit = -1 → passes without counting usage."""
    plan = make_pricing_plan(limits={"alert_analysis": -1})
    sub = make_subscription()
    mock_sub_repo.get_active_subscription.return_value = sub
    mock_sub_repo.get_pricing_plan.return_value = plan

    # Should not raise
    await check_module_access("org_1", "ai_assistant", "alert_analysis")

    # Usage should NOT have been counted (short-circuit)
    mock_usage_repo.count_usage.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_access_within_quota(mock_sub_repo, mock_usage_repo, mock_org_repo):
    """Usage=12, limit=50, pending=1 → OK."""
    plan = make_pricing_plan(limits={"chat": 50})
    sub = make_subscription()
    mock_sub_repo.get_active_subscription.return_value = sub
    mock_sub_repo.get_pricing_plan.return_value = plan
    mock_usage_repo.count_usage.return_value = 12

    # Should not raise
    await check_module_access("org_1", "ai_assistant", "chat")


@pytest.mark.asyncio
async def test_check_access_quota_exceeded(mock_sub_repo, mock_usage_repo, mock_org_repo):
    """Usage=50, limit=50, pending=1 → 429 QUOTA_EXCEEDED."""
    plan = make_pricing_plan(limits={"chat": 50})
    sub = make_subscription()
    mock_sub_repo.get_active_subscription.return_value = sub
    mock_sub_repo.get_pricing_plan.return_value = plan
    mock_usage_repo.count_usage.return_value = 50

    with pytest.raises(HTTPException) as exc_info:
        await check_module_access("org_1", "ai_assistant", "chat")

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["code"] == "QUOTA_EXCEEDED"


@pytest.mark.asyncio
async def test_check_access_bulk_precheck_exceeded(mock_sub_repo, mock_usage_repo, mock_org_repo):
    """Usage=60, limit=100, pending=50 → 429 (60+50 > 100)."""
    plan = make_pricing_plan(
        module_key="cashflow_monitor",
        slug="cashflow_monitor_free",
        limits={"data_rows": 100},
    )
    sub = make_subscription(module_key="cashflow_monitor", pricing_plan_id=plan["id"])
    mock_sub_repo.get_active_subscription.return_value = sub
    mock_sub_repo.get_pricing_plan.return_value = plan
    mock_usage_repo.count_usage.return_value = 60

    with pytest.raises(HTTPException) as exc_info:
        await check_module_access(
            "org_1", "cashflow_monitor", "data_rows", pending_quantity=50,
        )

    assert exc_info.value.status_code == 429


# ── build_module_access_status ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_status_shape(mock_sub_repo, mock_usage_repo, mock_org_repo):
    """Returns correct shape with usage per feature."""
    plan = make_pricing_plan(limits={"chat": 50, "digest": 4})
    sub = make_subscription()
    mock_sub_repo.get_active_subscription.return_value = sub
    mock_sub_repo.get_pricing_plan.return_value = plan
    mock_usage_repo.count_usage.return_value = 7

    result = await build_module_access_status("org_1", "ai_assistant")

    assert "plan" in result
    assert "enabled" in result
    assert "period" in result
    assert "limits" in result
    assert "usage" in result
    assert result["enabled"] is True
    assert result["limits"] == {"chat": 50, "digest": 4}
    # count_usage called once per feature key
    assert mock_usage_repo.count_usage.await_count == 2
    assert result["usage"]["chat"] == 7
    assert result["usage"]["digest"] == 7
