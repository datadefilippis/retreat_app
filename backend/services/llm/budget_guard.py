"""LLM budget guard — pre-flight check that runs before every Anthropic call.

Wave 8B (2026-05) governance enforcement layer.
Wave 10.A (2026-05) docstring/integration accuracy fix + fail-open cap.

Two-tier protection:

  1. GLOBAL KILL SWITCH (platform_settings)
     ``ai_enabled=false`` → all calls refused with AIDisabledError
     ``ai_throttle_pct=N`` → N% of calls refused with AIThrottledError

  2. BUDGETS (ai_budgets_collection)
     For every applicable budget (global, org, user, feature, agent),
     compute current spend in its period window. If spend >= hard_limit,
     refuse with BudgetExceededError.

The guard NEVER computes an estimated cost for the upcoming call — it
checks if the cumulative spend in the period is already at the hard
limit. Side effect: when the limit is hit, exactly one call may slip
through before the next one is refused. Acceptable trade-off for an
MVP that avoids the complexity of cost estimation + refund-on-failure.

Integration model (Wave 10.A correction)
----------------------------------------
The guard is invoked **PER CALL SITE**, not inside the LLM provider. A
pre-Wave 10 docstring claimed integration inside
``AnthropicProvider._gated_call``; that was aspirational, never landed,
and produced a real gap (alert_analysis was missing the call). Now every
known AI call site invokes ``check_budget_or_raise`` explicitly before
hitting Anthropic. Coverage matrix:

  chat                — services/chat_service.py
  digest              — modules/cashflow_monitor/digest_builder.py
  health_explanation  — modules/cashflow_monitor/health_explanation.py
  alert_analysis      — modules/cashflow_monitor/alert_analysis.py  (Wave 10.A.1)

A test in ``tests/test_no_anthropic_bypass.py`` ensures every code path
that calls ``send_message_with_usage`` is preceded by a guard call.

Fail-open emergency cap (Wave 10.A.4)
--------------------------------------
If MongoDB is unreachable, the guard fails OPEN by design (a DB outage
must not also kill AI). To prevent unbounded spend during a prolonged
outage, the process tracks every fail-open event in memory. After
``_FAIL_OPEN_LIMIT`` events in the sliding ``_FAIL_OPEN_WINDOW_SEC``
window, subsequent fail-open events are converted to fail-CLOSED
(``AIDisabledError``). This bounds the worst-case spend during a Mongo
outage to a known ceiling.

Defaults: 100 fail-open events per 600s. Override via env:
  AI_FAIL_OPEN_LIMIT, AI_FAIL_OPEN_WINDOW_SEC
"""

import logging
import os
import random
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from repositories import ai_budget_repository

logger = logging.getLogger(__name__)


# ── Wave 10.A.4 — fail-open emergency cap ───────────────────────────────────
#
# In-memory sliding window of recent fail-open events. The window is
# process-local (good enough for the single-uvicorn-worker MVP; a future
# HA setup with multiple processes would need Redis here).

_FAIL_OPEN_LIMIT: int = int(os.environ.get("AI_FAIL_OPEN_LIMIT", "100"))
_FAIL_OPEN_WINDOW_SEC: float = float(os.environ.get("AI_FAIL_OPEN_WINDOW_SEC", "600"))
_fail_open_timestamps: "deque[float]" = deque(maxlen=10000)


def _record_fail_open_and_check_cap(reason: str) -> None:
    """Record a fail-open event and raise AIDisabledError if we've crossed
    the cap. Called from the guard whenever Mongo lookups fail.

    Sliding-window logic: drop timestamps older than the window, then
    append the current one. If the window count >= _FAIL_OPEN_LIMIT,
    the next fail-open is converted to a fail-CLOSED.
    """
    now_mono = datetime.now(timezone.utc).timestamp()
    cutoff = now_mono - _FAIL_OPEN_WINDOW_SEC
    # Drop expired timestamps from the left.
    while _fail_open_timestamps and _fail_open_timestamps[0] < cutoff:
        _fail_open_timestamps.popleft()
    _fail_open_timestamps.append(now_mono)
    if len(_fail_open_timestamps) >= _FAIL_OPEN_LIMIT:
        logger.error(
            "budget_guard: fail-open emergency cap REACHED — %d events in last %.0fs "
            "(reason=%r). Converting to fail-CLOSED until Mongo recovers and the "
            "window drains. Investigate Mongo health.",
            len(_fail_open_timestamps), _FAIL_OPEN_WINDOW_SEC, reason,
        )
        raise AIDisabledError(
            "AI temporarily disabled — governance store unavailable. "
            "Retry in a few minutes.",
            reason="fail_open_emergency_cap",
            fail_open_count=len(_fail_open_timestamps),
            window_seconds=_FAIL_OPEN_WINDOW_SEC,
        )


# ── Exceptions (caller-friendly, structured for FastAPI) ────────────────────


class GovernanceError(Exception):
    """Base class for all governance refusals.

    Subclasses carry structured fields that the HTTP layer maps onto a
    422/429/503 response with a stable error_code the frontend can act on.
    """
    error_code: str = "governance_refused"
    http_status: int = 503

    def __init__(self, message: str, **context):
        super().__init__(message)
        self.context = context


class AIDisabledError(GovernanceError):
    """Global kill switch active — all AI calls refused."""
    error_code = "ai_disabled"
    http_status = 503


class AIThrottledError(GovernanceError):
    """Throttled by the load-shedding switch (random reject)."""
    error_code = "ai_throttled"
    http_status = 503


class BudgetExceededError(GovernanceError):
    """A budget's hard_limit_usd has been reached for the current period."""
    error_code = "budget_exceeded"
    http_status = 429  # too many spends, try again next period


# ── Kill-switch state read from platform_settings_collection ─────────────────


_KILL_SWITCH_KEY = "ai_governance"


_DEFAULTS = {
    "ai_enabled": True,
    "ai_throttle_pct": 0,
    "kill_reason": None,
    "activated_at": None,
    "activated_by": None,
}


async def _read_kill_switch() -> dict:
    """Return the active kill-switch document, or defaults.

    Fail-open: if MongoDB is unreachable or the lookup raises, return
    the safe defaults (AI enabled, no throttle). The kill switch is a
    SAFETY mechanism — a database outage must not also disable AI.
    Audit logs surface the underlying problem to the sysadmin.

    Default shape (kill switch never configured):
        {ai_enabled: True, ai_throttle_pct: 0,
         kill_reason: None, activated_at: None, activated_by: None}
    """
    try:
        from database import platform_settings_collection
        doc = await platform_settings_collection.find_one(
            {"key": _KILL_SWITCH_KEY}, {"_id": 0},
        )
    except Exception as exc:
        logger.debug(
            "budget_guard: kill-switch read failed (returning defaults): %s",
            exc,
        )
        # Wave 10.A.4 — track the fail-open. If too many in a short window,
        # this call raises AIDisabledError before we return.
        _record_fail_open_and_check_cap("kill_switch_read_failed")
        return dict(_DEFAULTS)
    if not doc:
        return dict(_DEFAULTS)
    return {
        "ai_enabled": doc.get("ai_enabled", True),
        "ai_throttle_pct": int(doc.get("ai_throttle_pct", 0)),
        "kill_reason": doc.get("kill_reason"),
        "activated_at": doc.get("activated_at"),
        "activated_by": doc.get("activated_by"),
    }


async def write_kill_switch(
    *,
    ai_enabled: bool,
    ai_throttle_pct: int = 0,
    reason: Optional[str] = None,
    activated_by: Optional[str] = None,
) -> dict:
    """Persist kill-switch state. Called from the admin endpoint.

    Idempotent upsert keyed on ``key="ai_governance"``.
    """
    from database import platform_settings_collection

    if ai_throttle_pct < 0 or ai_throttle_pct > 100:
        raise ValueError("ai_throttle_pct must be in [0, 100]")

    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "key": _KILL_SWITCH_KEY,
        "ai_enabled": bool(ai_enabled),
        "ai_throttle_pct": int(ai_throttle_pct),
        "kill_reason": reason,
        "activated_at": now_iso,
        "activated_by": activated_by,
        "updated_at": now_iso,
    }
    await platform_settings_collection.update_one(
        {"key": _KILL_SWITCH_KEY},
        {"$set": payload},
        upsert=True,
    )
    logger.warning(
        "ai_governance: kill switch updated — enabled=%s throttle=%d%% by=%s reason=%r",
        ai_enabled, ai_throttle_pct, activated_by, reason,
    )

    # Wave 10.C.6 — write to the existing audit_logs collection so the
    # new /api/admin/ai-governance/audit-log endpoint can surface a
    # full history of governance mutations to the system admin. Best
    # effort: never let an audit-log write fail the kill-switch update.
    try:
        from models import AuditLog
        from repositories import audit_repository
        await audit_repository.create(AuditLog(
            organization_id=None,  # platform-level event
            user_id=activated_by or "system",
            action="kill_switch_updated",
            resource_type="ai_governance",
            resource_id=_KILL_SWITCH_KEY,
            details={
                "ai_enabled": bool(ai_enabled),
                "ai_throttle_pct": int(ai_throttle_pct),
                "reason": reason,
            },
        ))
    except Exception as _audit_exc:
        logger.warning(
            "ai_governance: audit log write failed (non-fatal): %s",
            _audit_exc,
        )

    return payload


# ── The main check ──────────────────────────────────────────────────────────


async def check_budget_or_raise(
    *,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    feature: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> None:
    """Run all governance checks. Raises on refusal, returns None on OK.

    Order:
      1. Global kill switch (ai_enabled).
      2. Throttle (ai_throttle_pct random reject).
      3. Applicable budgets in cascade.

    Performance note: each call does:
      - 1 read on platform_settings (~indexed by key, microseconds)
      - 1 read on ai_budgets (indexed by scope/scope_id, microseconds)
      - K aggregations on ai_usage_events (one per applicable budget)
        — indexed by org/user/agent/feature + created_at, fast.

    Total typical overhead: ~10-30ms per call. The Anthropic call itself
    takes 500-3000ms, so this is <2% overhead.
    """
    # 1. Kill switch
    ks = await _read_kill_switch()
    if not ks["ai_enabled"]:
        raise AIDisabledError(
            "AI calls are temporarily disabled by the system administrator.",
            reason=ks.get("kill_reason"),
            activated_at=ks.get("activated_at"),
        )

    # 2. Throttle (random reject N% of calls)
    pct = ks["ai_throttle_pct"]
    if pct > 0 and random.randint(1, 100) <= pct:
        raise AIThrottledError(
            f"AI calls are currently throttled at {pct}%. Please retry shortly.",
            throttle_pct=pct,
        )

    # 3. Budgets — cascade through every applicable scope.
    # Fail-open on lookup failure (MongoDB outage MUST NOT also kill AI).
    try:
        budgets = await ai_budget_repository.find_applicable_budgets(
            organization_id=organization_id,
            user_id=user_id,
            feature=feature,
            agent_id=agent_id,
        )
    except Exception as exc:
        logger.warning(
            "budget_guard: find_applicable_budgets failed (allowing call): %s",
            exc,
        )
        # Wave 10.A.4 — track the fail-open. Raises AIDisabledError if cap
        # exceeded so a Mongo outage cannot burn unbounded budget.
        _record_fail_open_and_check_cap("find_applicable_budgets_failed")
        return None
    now = datetime.now(timezone.utc)
    for b in budgets:
        # Skip inactive or override-suspended budgets
        if not b.get("is_active", True):
            continue
        override = b.get("override_until")
        if override:
            try:
                if isinstance(override, str):
                    until = datetime.fromisoformat(override.replace("Z", "+00:00"))
                else:
                    until = override
                if until.tzinfo is None:
                    until = until.replace(tzinfo=timezone.utc)
                if until > now:
                    continue  # override is in the future → suspended
            except (ValueError, TypeError):
                pass

        # Wave 10.B.2 — fast-path via atomic counter.
        # Pre-Wave 10.B.2 we ran the full aggregation on every chat call
        # (10-50ms × every Anthropic round-trip, plus a TOCTOU race
        # window the size of the LLM call itself). Now we read an
        # atomic counter (<1ms, kept in sync by record_usage). On cache
        # miss (counter not yet populated for this budget), fall back
        # to aggregation and seed the counter for next time.
        try:
            from repositories import budget_counter_repository as _bcr
            period_start = ai_budget_repository.period_start_iso(b["period"])
            counter_cents = await _bcr.read_cents(
                scope=b["scope"], scope_id=b["scope_id"],
                period=b["period"], period_start=period_start,
            )
            if counter_cents is None:
                # Counter not initialized — compute via aggregation and seed.
                spend = await ai_budget_repository.compute_period_spend(
                    scope=b["scope"], scope_id=b["scope_id"],
                    period=b["period"],
                    organization_id=b.get("organization_id"),
                )
                await _bcr.seed_from_aggregation(
                    scope=b["scope"], scope_id=b["scope_id"],
                    period=b["period"], period_start=period_start,
                    aggregated_usd=spend,
                )
            else:
                spend = _bcr.cents_to_usd(counter_cents)
        except Exception as exc:
            # Aggregation failure must NOT block the chat — log + continue.
            logger.warning(
                "budget_guard: spend lookup failed for budget=%s: %s",
                b.get("id"), exc,
            )
            continue

        if spend >= b["hard_limit_usd"]:
            raise BudgetExceededError(
                f"Budget exceeded for scope={b['scope']!r} ({b['scope_id']}): "
                f"${spend:.4f} reached limit ${b['hard_limit_usd']:.4f}.",
                budget_id=b.get("id"),
                scope=b["scope"],
                scope_id=b["scope_id"],
                period=b["period"],
                period_start=ai_budget_repository.period_start_iso(b["period"]),
                current_spend_usd=spend,
                hard_limit_usd=b["hard_limit_usd"],
                soft_limit_usd=b.get("soft_limit_usd"),
            )

    # All gates passed — caller is free to proceed with the Anthropic call.
    return None
