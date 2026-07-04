"""AIBudget — Wave 8B governance primitive for capping Anthropic spend.

A budget declares a soft + hard USD limit on AI cost for a given scope
within a recurring period. The pre-flight check in services/llm/
budget_guard.py reads applicable budgets before every Anthropic call:
when the cumulative spend in the current period reaches the hard limit,
the call is refused with a structured error.

Design choices (Wave 8B MVP)
-----------------------------
- ``current_spend`` is NOT stored on the document. The guard computes it
  on-the-fly via an aggregation on ai_usage_events filtered by the
  period window. This avoids race conditions on increment, removes the
  need for a reset cron, and benefits from the indices added in 8A.1.

- Scopes form a CASCADE: a single Anthropic call is checked against
  every applicable budget (global, org-specific, user-specific). The
  FIRST one whose hard_limit is reached blocks the call. This lets
  sysadmins set platform-wide caps + per-org caps + per-user caps
  independently and have them ALL enforced.

- An ``override_until`` timestamp lets the sysadmin temporarily disable
  enforcement for a specific budget (e.g. legitimate burst). Logged in
  audit_logs at update time.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from .common import generate_id, utc_now


# Allowed values — pinned here so the guard + admin endpoints share one source.
BUDGET_SCOPES = ("global", "org", "user", "feature", "agent")
BUDGET_PERIODS = ("daily", "monthly", "yearly")
BUDGET_HARD_ACTIONS = ("block", "throttle")


class AIBudget(BaseModel):
    """A budget cap on AI spend for a (scope, scope_id, period) tuple.

    The combination (scope, scope_id, period) is UNIQUE — only one active
    budget per (scope, scope_id, period). Re-creating with same key updates.
    """
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)

    # ── Scope: who/what does this budget cover? ──────────────────────
    scope: Literal["global", "org", "user", "feature", "agent"]
    scope_id: str  # "*" for global, org_id, user_id, feature name, agent_id

    # Optional org tag for fast filtering when scope=user / feature / agent
    # is restricted to a single org. None for platform-wide budgets.
    organization_id: Optional[str] = None

    # ── Period semantics ─────────────────────────────────────────────
    period: Literal["daily", "monthly", "yearly"]

    # ── Limits (USD) ─────────────────────────────────────────────────
    soft_limit_usd: float = Field(ge=0)
    hard_limit_usd: float = Field(ge=0)
    hard_action: Literal["block", "throttle"] = "block"

    # ── Override / audit ─────────────────────────────────────────────
    # If set and in the future, the guard skips this budget. Lets admin
    # temporarily disable enforcement without deleting the budget.
    override_until: Optional[datetime] = None

    # Stable enable flag (defaults to true). Setting False keeps the
    # row for audit but stops enforcement.
    is_active: bool = True

    # Free-text rationale (visible in admin UI).
    notes: Optional[str] = Field(default=None, max_length=500)

    # Who created / last updated (system_admin user_id).
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AIBudgetCreate(BaseModel):
    """Input payload for POST /api/admin/ai-budgets."""
    scope: Literal["global", "org", "user", "feature", "agent"]
    scope_id: str = Field(min_length=1, max_length=128)
    organization_id: Optional[str] = None
    period: Literal["daily", "monthly", "yearly"]
    soft_limit_usd: float = Field(ge=0)
    hard_limit_usd: float = Field(ge=0)
    hard_action: Literal["block", "throttle"] = "block"
    notes: Optional[str] = Field(default=None, max_length=500)


class AIBudgetUpdate(BaseModel):
    """Input payload for PATCH /api/admin/ai-budgets/{id}.

    Every field optional — only provided ones get applied.
    """
    model_config = ConfigDict(extra="ignore")
    soft_limit_usd: Optional[float] = Field(default=None, ge=0)
    hard_limit_usd: Optional[float] = Field(default=None, ge=0)
    hard_action: Optional[Literal["block", "throttle"]] = None
    is_active: Optional[bool] = None
    override_until: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class BudgetEnforcementResult(BaseModel):
    """Returned by budget_guard.check_budget — visible state for the caller."""
    blocked: bool
    blocked_by: Optional[str] = None   # which budget id triggered the block
    blocked_scope: Optional[str] = None
    blocked_scope_id: Optional[str] = None
    current_spend_usd: float = 0
    hard_limit_usd: Optional[float] = None
    soft_limit_reached: bool = False
    period_start_iso: Optional[str] = None
