"""Seed default AI budgets at server startup — Wave 10.A.8.

Forensic audit on 2026-05-15 revealed:
  - 0 budgets configured in the database
  - kill switch never set
  - i.e. all the Wave 8B governance infrastructure is INERT

This module seeds a conservative set of defaults the FIRST time the
server boots into a database with no budgets at all. The intent is
defense-in-depth: even if the sysadmin never opens the dashboard, AI
spend is bounded.

The seed is fully idempotent and conservative:
  - Runs ONLY when ai_budgets is completely empty (count==0). The
    moment an admin creates any budget, the seed is skipped on the
    next boot (we assume the admin has taken over management).
  - Values err on the side of generous so we don't disrupt operations.

Opt-out (Wave 12 deploy prep)
-----------------------------
Set ``AI_BUDGETS_SEED_DISABLED=1`` in the environment to skip the
auto-seed entirely. Useful for deployments where the operator wants
to set their own budgets manually via the governance dashboard before
ANY default is created — avoids the brief window where boot-time
seeded budgets could surprise an admin who hadn't planned for them.

Seeded defaults (only when collection is empty):

  scope=global  scope_id=*   period=daily   soft=$50   hard=$100
    -> platform-wide circuit breaker. $100/day is ~$3k/month worst
       case; well above expected baseline ($0.5 in the last 52 days
       of measured traffic) but enough to short-circuit a runaway.

  scope=feature scope_id=chat period=monthly soft=$300 hard=$500
    -> chat (the heaviest feature, 94.6% of historical spend).

  scope=feature scope_id=alert_analysis period=daily soft=$10 hard=$25
    -> alert_analysis runs from cron every 6h × all orgs. The forensic
       audit identified this as the highest-risk cost vector (Wave
       10.A.1 wired the budget guard into it; this cap is the matching
       enforcement).

  scope=feature scope_id=digest period=daily soft=$10 hard=$25
    -> digest cron, same shape as alert_analysis.

  scope=feature scope_id=health_explanation period=daily soft=$5 hard=$15
    -> on-demand from dashboard clicks; lower volume.

The sysadmin can override any of these via the dashboard at any time —
the DB is the source of truth, the seed only kicks in when empty.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


_DEFAULT_BUDGETS = [
    # (scope, scope_id, period, soft_usd, hard_usd, notes)
    ("global", "*", "daily", 50.0, 100.0,
     "Platform-wide daily emergency cap. Wave 10.A.8 seed."),
    ("feature", "chat", "monthly", 300.0, 500.0,
     "Chat is the heaviest feature (~95% of historical spend). "
     "Wave 10.A.8 seed."),
    ("feature", "alert_analysis", "daily", 10.0, 25.0,
     "Alert cron fires every 6h × all orgs. Wave 10.A.8 seed."),
    ("feature", "digest", "daily", 10.0, 25.0,
     "Digest cron (weekly/monthly per org). Wave 10.A.8 seed."),
    ("feature", "health_explanation", "daily", 5.0, 15.0,
     "On-demand from dashboard. Wave 10.A.8 seed."),
]


async def seed_default_ai_budgets_if_empty() -> int:
    """Seed conservative default budgets ONLY if ai_budgets is empty.

    Returns the number of budgets created (0 if the seed was skipped
    because budgets already exist OR the env opt-out is set).

    Safe to call on every server boot — the count check makes it a
    no-op once the admin has set anything up.
    """
    # Wave 12 deploy prep — env opt-out for operators who want to
    # configure budgets manually before any default is created.
    import os as _os12
    if _os12.environ.get("AI_BUDGETS_SEED_DISABLED", "").strip() in ("1", "true", "yes"):
        logger.info(
            "seed_ai_budgets: skipped — AI_BUDGETS_SEED_DISABLED is set. "
            "Operator must configure budgets via the governance dashboard.",
        )
        return 0

    try:
        from database import ai_budgets_collection
        existing = await ai_budgets_collection.count_documents({})
    except Exception as exc:
        logger.warning("seed_ai_budgets: count_documents failed: %s", exc)
        return 0

    if existing > 0:
        logger.debug(
            "seed_ai_budgets: skipped (%d budgets already exist)", existing,
        )
        return 0

    logger.info(
        "seed_ai_budgets: ai_budgets is empty — seeding %d default budgets "
        "(Wave 10.A.8). The sysadmin can override any of these via the "
        "governance dashboard.",
        len(_DEFAULT_BUDGETS),
    )

    from repositories import ai_budget_repository
    created = 0
    for scope, scope_id, period, soft, hard, notes in _DEFAULT_BUDGETS:
        try:
            await ai_budget_repository.create_budget(
                scope=scope, scope_id=scope_id, period=period,
                soft_limit_usd=soft, hard_limit_usd=hard,
                hard_action="block",
                organization_id=None,
                notes=notes,
                created_by="system:seed_wave_10a8",
            )
            created += 1
        except Exception as exc:
            logger.warning(
                "seed_ai_budgets: failed to seed %s/%s %s: %s",
                scope, scope_id, period, exc,
            )

    logger.info("seed_ai_budgets: seeded %d/%d default budgets",
                created, len(_DEFAULT_BUDGETS))
    return created
