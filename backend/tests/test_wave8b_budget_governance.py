"""Wave 8B — budget guard + kill switch governance tests.

Covers:
  1. period_start_iso math (daily / monthly / yearly).
  2. compute_period_spend aggregates only events in the period window.
  3. find_applicable_budgets returns cascading scopes.
  4. check_budget_or_raise blocks when hard_limit is reached, allows otherwise.
  5. Kill switch: ai_enabled=False raises AIDisabledError.
  6. Kill switch: ai_throttle_pct triggers AIThrottledError.
  7. Override_until in the future suspends enforcement.
  8. CRUD basics on the repository.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fake_agg(docs):
    async def _aiter():
        for d in docs:
            yield d
    cursor = MagicMock()
    cursor.__aiter__ = lambda self: _aiter()
    return cursor


def _patch_kill_switch_ok():
    """Patch kill-switch to return defaults (AI enabled, no throttle)."""
    return patch(
        "services.llm.budget_guard._read_kill_switch",
        new=AsyncMock(return_value={
            "ai_enabled": True, "ai_throttle_pct": 0,
            "kill_reason": None, "activated_at": None, "activated_by": None,
        }),
    )


# ── period_start_iso ────────────────────────────────────────────────────────

def test_period_start_daily_returns_today():
    from repositories.ai_budget_repository import period_start_iso
    fixed = datetime(2026, 5, 15, 14, 30, tzinfo=timezone.utc)
    assert period_start_iso("daily", now=fixed) == "2026-05-15"


def test_period_start_monthly_returns_first_of_month():
    from repositories.ai_budget_repository import period_start_iso
    fixed = datetime(2026, 5, 15, 14, 30, tzinfo=timezone.utc)
    assert period_start_iso("monthly", now=fixed) == "2026-05-01"


def test_period_start_yearly_returns_jan_first():
    from repositories.ai_budget_repository import period_start_iso
    fixed = datetime(2026, 5, 15, 14, 30, tzinfo=timezone.utc)
    assert period_start_iso("yearly", now=fixed) == "2026-01-01"


def test_period_start_invalid_raises():
    from repositories.ai_budget_repository import period_start_iso
    with pytest.raises(ValueError):
        period_start_iso("weekly")


# ── compute_period_spend ─────────────────────────────────────────────────────

async def test_compute_period_spend_sums_cost_in_window():
    """Aggregation returns the sum of cost_usd inside the period window."""
    from repositories import ai_budget_repository as repo

    fake_coll = MagicMock()
    fake_coll.aggregate = MagicMock(return_value=_fake_agg([{"spend": 3.21}]))
    with patch("repositories.ai_budget_repository.ai_usage_events_collection",
               fake_coll):
        spend = await repo.compute_period_spend(
            scope="org", scope_id="org_a", period="monthly",
        )
    assert spend == 3.21


async def test_compute_period_spend_no_events_returns_zero():
    from repositories import ai_budget_repository as repo

    fake_coll = MagicMock()
    fake_coll.aggregate = MagicMock(return_value=_fake_agg([]))
    with patch("repositories.ai_budget_repository.ai_usage_events_collection",
               fake_coll):
        spend = await repo.compute_period_spend(
            scope="user", scope_id="user_x", period="daily",
        )
    assert spend == 0.0


# ── find_applicable_budgets ──────────────────────────────────────────────────

async def test_find_applicable_budgets_returns_cascade():
    """For a chat call with org+user+agent+feature context, query covers all 5 scopes."""
    from repositories import ai_budget_repository as repo

    captured_query = {}
    fake_coll = MagicMock()

    def _fake_find(q, projection=None):
        nonlocal captured_query
        captured_query = q
        # Return one matching org-scoped budget
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=[
            {"scope": "org", "scope_id": "org_a", "is_active": True,
             "period": "monthly", "soft_limit_usd": 5, "hard_limit_usd": 10},
        ])
        return cursor

    fake_coll.find = _fake_find
    with patch("repositories.ai_budget_repository.ai_budgets_collection",
               fake_coll):
        budgets = await repo.find_applicable_budgets(
            organization_id="org_a", user_id="user_x",
            feature="chat", agent_id="financial_analyst",
        )

    # The query's $or has 5 scope/scope_id combinations + is_active=True
    or_clauses = captured_query["$or"]
    assert len(or_clauses) == 5
    assert {"scope": "global", "scope_id": "*"} in or_clauses
    assert {"scope": "org", "scope_id": "org_a"} in or_clauses
    assert {"scope": "user", "scope_id": "user_x"} in or_clauses
    assert {"scope": "feature", "scope_id": "chat"} in or_clauses
    assert {"scope": "agent", "scope_id": "financial_analyst"} in or_clauses
    assert captured_query["is_active"] is True
    assert len(budgets) == 1


# ── check_budget_or_raise (the heart of the wave) ────────────────────────────

async def test_check_budget_allows_when_under_limit():
    """Spend < hard_limit → no exception."""
    from services.llm.budget_guard import check_budget_or_raise

    budgets = [{
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly",
        "soft_limit_usd": 5.0, "hard_limit_usd": 10.0,
        "is_active": True, "hard_action": "block",
    }]

    with _patch_kill_switch_ok(), \
         patch("repositories.ai_budget_repository.find_applicable_budgets",
               new=AsyncMock(return_value=budgets)), \
         patch("repositories.ai_budget_repository.compute_period_spend",
               new=AsyncMock(return_value=3.0)):
        # Should NOT raise
        await check_budget_or_raise(
            organization_id="org_a", feature="chat",
        )


async def test_check_budget_blocks_at_hard_limit():
    """Spend == hard_limit → BudgetExceededError."""
    from services.llm.budget_guard import check_budget_or_raise, BudgetExceededError

    budgets = [{
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly",
        "soft_limit_usd": 5.0, "hard_limit_usd": 10.0,
        "is_active": True,
    }]

    with _patch_kill_switch_ok(), \
         patch("repositories.ai_budget_repository.find_applicable_budgets",
               new=AsyncMock(return_value=budgets)), \
         patch("repositories.ai_budget_repository.compute_period_spend",
               new=AsyncMock(return_value=10.0)):
        with pytest.raises(BudgetExceededError) as exc_info:
            await check_budget_or_raise(organization_id="org_a")

    assert exc_info.value.error_code == "budget_exceeded"
    assert exc_info.value.context["scope"] == "org"
    assert exc_info.value.context["current_spend_usd"] == 10.0
    assert exc_info.value.context["hard_limit_usd"] == 10.0


async def test_check_budget_skips_inactive():
    """is_active=False budgets are not enforced."""
    from services.llm.budget_guard import check_budget_or_raise

    budgets = [{
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly",
        "soft_limit_usd": 5.0, "hard_limit_usd": 10.0,
        "is_active": False,
    }]

    with _patch_kill_switch_ok(), \
         patch("repositories.ai_budget_repository.find_applicable_budgets",
               new=AsyncMock(return_value=budgets)), \
         patch("repositories.ai_budget_repository.compute_period_spend",
               new=AsyncMock(return_value=100.0)):
        # Should NOT raise — inactive budget skipped
        await check_budget_or_raise(organization_id="org_a")


async def test_check_budget_skips_when_override_in_future():
    """A future override_until temporarily disables enforcement."""
    from services.llm.budget_guard import check_budget_or_raise

    future_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    budgets = [{
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly",
        "soft_limit_usd": 5.0, "hard_limit_usd": 10.0,
        "is_active": True, "override_until": future_iso,
    }]

    with _patch_kill_switch_ok(), \
         patch("repositories.ai_budget_repository.find_applicable_budgets",
               new=AsyncMock(return_value=budgets)), \
         patch("repositories.ai_budget_repository.compute_period_spend",
               new=AsyncMock(return_value=100.0)):
        # Should NOT raise — override is active
        await check_budget_or_raise(organization_id="org_a")


async def test_check_budget_enforces_when_override_in_past():
    """A past override_until does NOT suspend enforcement."""
    from services.llm.budget_guard import check_budget_or_raise, BudgetExceededError

    past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    budgets = [{
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly",
        "soft_limit_usd": 5.0, "hard_limit_usd": 10.0,
        "is_active": True, "override_until": past_iso,
    }]

    with _patch_kill_switch_ok(), \
         patch("repositories.ai_budget_repository.find_applicable_budgets",
               new=AsyncMock(return_value=budgets)), \
         patch("repositories.ai_budget_repository.compute_period_spend",
               new=AsyncMock(return_value=100.0)):
        with pytest.raises(BudgetExceededError):
            await check_budget_or_raise(organization_id="org_a")


async def test_check_budget_aggregation_failure_does_not_block():
    """If compute_period_spend raises, the budget is skipped (fail-open)."""
    from services.llm.budget_guard import check_budget_or_raise

    budgets = [{
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly",
        "soft_limit_usd": 5.0, "hard_limit_usd": 10.0,
        "is_active": True,
    }]

    with _patch_kill_switch_ok(), \
         patch("repositories.ai_budget_repository.find_applicable_budgets",
               new=AsyncMock(return_value=budgets)), \
         patch("repositories.ai_budget_repository.compute_period_spend",
               new=AsyncMock(side_effect=RuntimeError("mongo down"))):
        # Should NOT raise — fail-open is the right call (chat must work
        # even if governance has issues; admin alerted via logs).
        await check_budget_or_raise(organization_id="org_a")


# ── Kill switch ──────────────────────────────────────────────────────────────

async def test_kill_switch_disabled_raises_ai_disabled():
    """ai_enabled=False causes AIDisabledError regardless of budgets."""
    from services.llm.budget_guard import check_budget_or_raise, AIDisabledError

    with patch(
        "services.llm.budget_guard._read_kill_switch",
        new=AsyncMock(return_value={
            "ai_enabled": False, "ai_throttle_pct": 0,
            "kill_reason": "Anthropic outage", "activated_at": "x",
            "activated_by": "sysadmin_id",
        }),
    ):
        with pytest.raises(AIDisabledError) as exc_info:
            await check_budget_or_raise(organization_id="org_a")
    assert exc_info.value.error_code == "ai_disabled"
    assert exc_info.value.context["reason"] == "Anthropic outage"


async def test_kill_switch_throttle_100pct_always_throttles():
    """throttle_pct=100 should always reject."""
    from services.llm.budget_guard import check_budget_or_raise, AIThrottledError

    with patch(
        "services.llm.budget_guard._read_kill_switch",
        new=AsyncMock(return_value={
            "ai_enabled": True, "ai_throttle_pct": 100,
            "kill_reason": None, "activated_at": None, "activated_by": None,
        }),
    ), patch(
        "services.llm.budget_guard.random.randint", return_value=1,
    ):
        with pytest.raises(AIThrottledError):
            await check_budget_or_raise(organization_id="org_a")


async def test_kill_switch_throttle_0pct_never_throttles():
    """Throttle=0 must never block (random.randint result irrelevant)."""
    from services.llm.budget_guard import check_budget_or_raise

    with patch(
        "services.llm.budget_guard._read_kill_switch",
        new=AsyncMock(return_value={
            "ai_enabled": True, "ai_throttle_pct": 0,
            "kill_reason": None, "activated_at": None, "activated_by": None,
        }),
    ), patch(
        "repositories.ai_budget_repository.find_applicable_budgets",
        new=AsyncMock(return_value=[]),
    ):
        await check_budget_or_raise(organization_id="org_a")


async def test_write_kill_switch_rejects_out_of_range_throttle():
    from services.llm.budget_guard import write_kill_switch

    with pytest.raises(ValueError):
        await write_kill_switch(ai_enabled=True, ai_throttle_pct=200)
    with pytest.raises(ValueError):
        await write_kill_switch(ai_enabled=True, ai_throttle_pct=-1)


# ── Repository CRUD ─────────────────────────────────────────────────────────

async def test_create_budget_inserts_new_doc():
    from repositories import ai_budget_repository as repo

    fake_coll = MagicMock()
    fake_coll.find_one = AsyncMock(return_value=None)  # no existing
    fake_coll.insert_one = AsyncMock()
    with patch("repositories.ai_budget_repository.ai_budgets_collection",
               fake_coll):
        doc = await repo.create_budget(
            scope="org", scope_id="org_a", period="monthly",
            soft_limit_usd=5.0, hard_limit_usd=10.0,
            organization_id="org_a", notes="test",
            created_by="admin_id",
        )
    fake_coll.insert_one.assert_awaited_once()
    assert doc["scope"] == "org"
    assert doc["soft_limit_usd"] == 5.0
    assert doc["hard_limit_usd"] == 10.0
    assert doc["hard_action"] == "block"
    assert doc["is_active"] is True


async def test_create_budget_updates_existing():
    from repositories import ai_budget_repository as repo

    existing = {"id": "b_existing", "scope": "org", "scope_id": "org_a",
                "period": "monthly"}
    fake_coll = MagicMock()
    # First find_one returns the existing doc; update + re-find returns updated.
    fake_coll.find_one = AsyncMock(side_effect=[
        existing,  # check for existing
        {**existing, "soft_limit_usd": 7.0, "hard_limit_usd": 14.0},  # post-update
    ])
    fake_coll.update_one = AsyncMock()
    with patch("repositories.ai_budget_repository.ai_budgets_collection",
               fake_coll):
        doc = await repo.create_budget(
            scope="org", scope_id="org_a", period="monthly",
            soft_limit_usd=7.0, hard_limit_usd=14.0,
        )
    fake_coll.update_one.assert_awaited_once()
    assert doc["hard_limit_usd"] == 14.0


async def test_delete_budget_returns_true_when_deleted():
    """Wave 10.C.6 added a find_one() snapshot capture before delete so
    the audit-log entry can record what was removed. Mock both calls."""
    from repositories import ai_budget_repository as repo

    fake_coll = MagicMock()
    fake_coll.find_one = AsyncMock(return_value={
        "id": "b1", "scope": "org", "scope_id": "org_a",
        "period": "monthly", "hard_limit_usd": 10.0,
    })
    fake_coll.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    with patch("repositories.ai_budget_repository.ai_budgets_collection",
               fake_coll), \
         patch("repositories.audit_repository.create", new=AsyncMock()):
        result = await repo.delete_budget("b1")
    assert result is True


async def test_delete_budget_returns_false_when_missing():
    """When find_one returns None and delete_count==0, return False AND
    skip the audit-log write."""
    from repositories import ai_budget_repository as repo

    fake_coll = MagicMock()
    fake_coll.find_one = AsyncMock(return_value=None)
    fake_coll.delete_one = AsyncMock(return_value=MagicMock(deleted_count=0))
    audit_mock = AsyncMock()
    with patch("repositories.ai_budget_repository.ai_budgets_collection",
               fake_coll), \
         patch("repositories.audit_repository.create", new=audit_mock):
        result = await repo.delete_budget("b_missing")
    assert result is False
    # Wave 10.C.6 — no delete means no audit entry.
    audit_mock.assert_not_awaited()
