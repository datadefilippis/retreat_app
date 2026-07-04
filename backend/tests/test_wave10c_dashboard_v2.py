"""Wave 10.C — dashboard V2 observability backend.

Backend changes covered by this test pack:

  10.C.2  /ai-usage/summary and /by-user enrich rows with
          organization_name (and user_name on /by-user) via batch lookup
          against organizations / users collections.

  10.C.6  Governance mutations (kill_switch + budget CRUD) write to
          audit_logs with resource_type in ('ai_governance', 'ai_budget').
          A new endpoint /ai-governance/audit-log lists them.

  10.C.7  /ai-usage/failed-events returns events with error_code != null
          plus a by_code rollup.

  10.C.8  /ai-usage/top-conversations groups events by conversation_id
          and returns the top N by total cost; /conversations/{id}
          returns the round-by-round breakdown.
"""
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ════════════════════════════════════════════════════════════════════════════
# 10.C.6 — audit log writes on mutations
# ════════════════════════════════════════════════════════════════════════════


async def test_kill_switch_write_emits_audit_log():
    """write_kill_switch must create an AuditLog entry with
    resource_type='ai_governance' AND action='kill_switch_updated'."""
    from services.llm import budget_guard

    fake_settings = MagicMock()
    fake_settings.update_one = AsyncMock()

    audit_create_mock = AsyncMock()
    with patch("database.platform_settings_collection", fake_settings), \
         patch("repositories.audit_repository.create", new=audit_create_mock):
        await budget_guard.write_kill_switch(
            ai_enabled=False, ai_throttle_pct=0,
            reason="anthropic outage", activated_by="admin_user_xyz",
        )

    audit_create_mock.assert_awaited_once()
    audit_log = audit_create_mock.await_args.args[0]
    assert audit_log.resource_type == "ai_governance"
    assert audit_log.action == "kill_switch_updated"
    assert audit_log.user_id == "admin_user_xyz"
    assert audit_log.details["ai_enabled"] is False
    assert audit_log.details["reason"] == "anthropic outage"


async def test_kill_switch_audit_failure_does_not_break_mutation():
    """If audit_repository.create raises, the kill-switch update must
    still succeed (best-effort audit, never blocks the operator)."""
    from services.llm import budget_guard

    fake_settings = MagicMock()
    fake_settings.update_one = AsyncMock()

    with patch("database.platform_settings_collection", fake_settings), \
         patch("repositories.audit_repository.create",
               new=AsyncMock(side_effect=RuntimeError("audit down"))):
        # Should NOT raise — audit is opportunistic.
        result = await budget_guard.write_kill_switch(
            ai_enabled=True, ai_throttle_pct=0, reason=None, activated_by="ops",
        )
    assert result["key"] == "ai_governance"


async def test_budget_create_emits_audit_log():
    """ai_budget_repository.create_budget must record an audit event."""
    from repositories import ai_budget_repository

    fake_coll = MagicMock()
    fake_coll.find_one = AsyncMock(return_value=None)
    fake_coll.insert_one = AsyncMock()

    audit_mock = AsyncMock()
    with patch("repositories.ai_budget_repository.ai_budgets_collection", fake_coll), \
         patch("repositories.audit_repository.create", new=audit_mock):
        await ai_budget_repository.create_budget(
            scope="org", scope_id="org_a",
            period="monthly",
            soft_limit_usd=5.0, hard_limit_usd=10.0,
            created_by="admin_x",
        )
    audit_mock.assert_awaited_once()
    log = audit_mock.await_args.args[0]
    assert log.resource_type == "ai_budget"
    assert log.action == "budget_created"
    assert log.user_id == "admin_x"


async def test_budget_update_emits_audit_log():
    """update_budget records a 'budget_updated' audit event with changes."""
    from repositories import ai_budget_repository

    fake_coll = MagicMock()
    fake_coll.update_one = AsyncMock(return_value=MagicMock(matched_count=1))
    fake_coll.find_one = AsyncMock(return_value={
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly", "hard_limit_usd": 20.0, "soft_limit_usd": 10.0,
    })

    audit_mock = AsyncMock()
    with patch("repositories.ai_budget_repository.ai_budgets_collection", fake_coll), \
         patch("repositories.audit_repository.create", new=audit_mock):
        await ai_budget_repository.update_budget(
            "b1", {"hard_limit_usd": 20.0}, actor="admin_y",
        )
    audit_mock.assert_awaited_once()
    log = audit_mock.await_args.args[0]
    assert log.action == "budget_updated"
    assert log.user_id == "admin_y"
    assert log.details["changes"]["hard_limit_usd"] == 20.0


async def test_budget_delete_emits_audit_log():
    """delete_budget records a 'budget_deleted' with snapshot."""
    from repositories import ai_budget_repository

    snapshot = {
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly", "hard_limit_usd": 10.0,
    }
    fake_coll = MagicMock()
    fake_coll.find_one = AsyncMock(return_value=snapshot)
    fake_coll.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))

    audit_mock = AsyncMock()
    with patch("repositories.ai_budget_repository.ai_budgets_collection", fake_coll), \
         patch("repositories.audit_repository.create", new=audit_mock):
        await ai_budget_repository.delete_budget("b1", actor="admin_z")

    audit_mock.assert_awaited_once()
    log = audit_mock.await_args.args[0]
    assert log.action == "budget_deleted"
    assert log.user_id == "admin_z"
    assert log.details["snapshot"]["scope_id"] == "org_a"


# ════════════════════════════════════════════════════════════════════════════
# 10.C.2 / 10.C.6 / 10.C.7 / 10.C.8 — endpoint shape introspection
# ════════════════════════════════════════════════════════════════════════════


def test_summary_endpoint_enriches_with_organization_name():
    """The summary endpoint source must include the org_name batch lookup
    and attach 'organization_name' to each by_org row."""
    from routers import admin
    src = inspect.getsource(admin.admin_ai_usage_summary)
    assert "organizations_collection" in src
    assert "organization_name" in src


def test_byuser_endpoint_enriches_with_user_name():
    """The /by-user endpoint must include both org_name and user_name
    batch lookups."""
    from routers import admin
    src = inspect.getsource(admin.admin_ai_usage_by_user)
    assert "users_collection" in src
    assert "user_name" in src
    assert "organization_name" in src


def test_audit_log_endpoint_filters_governance_resources():
    """The audit-log endpoint must scope to resource_type IN
    (ai_governance, ai_budget) so it doesn't leak unrelated audit
    entries (Stripe billing, user management, etc.)."""
    from routers import admin
    src = inspect.getsource(admin.admin_ai_governance_audit_log)
    assert '"ai_governance"' in src
    assert '"ai_budget"' in src
    assert "resource_type" in src


def test_top_conversations_endpoint_groups_by_conversation_id():
    """Top conversations must aggregate by conversation_id and sort by
    cost desc (the whole point of the endpoint)."""
    from routers import admin
    src = inspect.getsource(admin.admin_ai_usage_top_conversations)
    assert '"$group"' in src
    assert "conversation_id" in src
    assert '"$sort"' in src
    assert "cost_usd" in src


def test_conversation_detail_endpoint_orders_by_created_at():
    """Drill-in endpoint must sort events ASC by created_at so the
    modal renders rounds in chronological order."""
    from routers import admin
    src = inspect.getsource(admin.admin_ai_usage_conversation_detail)
    assert "created_at" in src
    # Sort ascending (1)
    assert '("created_at", 1)' in src


def test_failed_events_endpoint_filters_by_error_code():
    """Failed-events must filter by error_code != null and emit a
    by_code rollup."""
    from routers import admin
    src = inspect.getsource(admin.admin_ai_usage_failed_events)
    assert "error_code" in src
    assert "by_code" in src
    assert '"$ne": None' in src or "'$ne': None" in src


# ════════════════════════════════════════════════════════════════════════════
# Auth coverage — every new endpoint requires require_system_admin
# ════════════════════════════════════════════════════════════════════════════


def test_all_wave10c_endpoints_require_system_admin():
    """Every new admin endpoint MUST gate on require_system_admin
    (defense against accidental exposure)."""
    from routers import admin
    new_endpoints = [
        admin.admin_ai_governance_audit_log,
        admin.admin_ai_usage_top_conversations,
        admin.admin_ai_usage_conversation_detail,
        admin.admin_ai_usage_failed_events,
    ]
    for fn in new_endpoints:
        sig = inspect.signature(fn)
        # The dependency is bound to a parameter (often named '_' or
        # 'current_user') whose default is a Depends(require_system_admin).
        found = False
        for param in sig.parameters.values():
            default = param.default
            # FastAPI's Depends wraps the dependency callable.
            if hasattr(default, "dependency"):
                if default.dependency.__name__ == "require_system_admin":
                    found = True
                    break
        assert found, f"{fn.__name__} is missing require_system_admin dependency"
