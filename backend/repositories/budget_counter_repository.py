"""Atomic budget spend counter — Wave 10.B.2.

Replaces the per-call ``compute_period_spend`` aggregation (10-50 ms,
TOCTOU race window the size of an Anthropic round-trip) with an atomic
``findOneAndUpdate``-backed counter (<1 ms).

Why this exists
---------------
``services/llm/budget_guard.check_budget_or_raise`` is the pre-flight
governance check on every Anthropic call. Pre-Wave 10.B.2 it called
``ai_budget_repository.compute_period_spend`` which runs a Mongo
aggregation over the entire ``ai_usage_events`` collection filtered
by scope. That has two problems:

  1. **Latency** — aggregation per call adds 10-50 ms; at 100 calls/sec
     in a busy hour that's 1-5 seconds of cumulative Mongo CPU.

  2. **TOCTOU race** — aggregation runs at T0, the actual call returns
     at T0 + ~1500 ms, then ``record_usage`` writes. 50 concurrent
     callers all see the SAME aggregation result, all proceed, all
     write events. Documented in the Wave 10 audit (finding C4).

This module provides a sidecar counter that's:
  - **Atomic** on increment ($inc with upsert).
  - **Fast** to read (single indexed lookup).
  - **Eventually consistent** with ``ai_usage_events`` (the counter is
    incremented inside ``record_usage`` after the event insert).

When the counter is missing (newly-active budget, fresh deploy, manual
ops scenario), the guard falls back to the original aggregation AND
populates the counter from that aggregation. After the first call, the
counter is the fast path.

Collection: ``ai_budget_counters``
Schema:
    {
        "_id": ObjectId,
        "scope": str,           # "global" | "org" | "user" | "feature" | "agent"
        "scope_id": str,        # e.g. "org_abc" or "*" for global
        "period": str,          # "daily" | "monthly" | "yearly"
        "period_start": str,    # ISO-date, the bucket key
        "cumulative_cents": int, # cumulative cost_usd × 100 (integer math)
        "event_count": int,     # number of events that contributed
        "updated_at": str,      # ISO timestamp
    }

Index: unique on (scope, scope_id, period, period_start).

We use **cents** (integer) instead of floats for $inc atomicity. Float
$inc works but accumulates rounding errors over millions of events.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


_INDEXES_INITIALIZED = False


async def setup_indexes() -> None:
    """Create the unique index for fast lookups. Idempotent.

    Called from server.py lifespan alongside the other Wave 8B indices.
    """
    global _INDEXES_INITIALIZED
    if _INDEXES_INITIALIZED:
        return
    try:
        from database import db
        coll = db.ai_budget_counters
        await coll.create_index(
            [("scope", 1), ("scope_id", 1), ("period", 1), ("period_start", 1)],
            unique=True,
            name="budget_counter_key_v1",
        )
        _INDEXES_INITIALIZED = True
        logger.info("budget_counter_repository: index ensured")
    except Exception as exc:
        logger.warning("budget_counter_repository.setup_indexes: %s", exc)


def _key_filter(scope: str, scope_id: str, period: str, period_start: str) -> dict:
    return {
        "scope": scope,
        "scope_id": scope_id,
        "period": period,
        "period_start": period_start,
    }


async def increment(
    *,
    scope: str,
    scope_id: str,
    period: str,
    period_start: str,
    cost_usd: float,
) -> Optional[int]:
    """Atomically add ``cost_usd`` (converted to cents) to the counter.

    Upserts the doc if it doesn't exist. Returns the post-increment
    cumulative_cents, or None on Mongo error (fail-open).
    """
    if cost_usd is None or cost_usd <= 0:
        # Don't track zero-cost events — they aren't billable. Cron
        # data_rows / system events typically have cost_usd=None.
        return None
    cents = int(round(cost_usd * 100))
    if cents <= 0:
        return None

    try:
        from database import db
        from pymongo import ReturnDocument
        coll = db.ai_budget_counters
        now_iso = datetime.now(timezone.utc).isoformat()
        doc = await coll.find_one_and_update(
            _key_filter(scope, scope_id, period, period_start),
            {
                "$inc": {"cumulative_cents": cents, "event_count": 1},
                "$set": {"updated_at": now_iso},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(doc.get("cumulative_cents", 0) or 0)
    except Exception as exc:
        logger.warning(
            "budget_counter.increment failed (scope=%s/%s period=%s start=%s): %s",
            scope, scope_id, period, period_start, exc,
        )
        return None


async def read_cents(
    *,
    scope: str,
    scope_id: str,
    period: str,
    period_start: str,
) -> Optional[int]:
    """Read the current cumulative_cents for this key. Returns:
      - int (>= 0) — counter found, value returned
      - None       — counter missing OR Mongo error (caller falls back)
    """
    try:
        from database import db
        coll = db.ai_budget_counters
        doc = await coll.find_one(
            _key_filter(scope, scope_id, period, period_start),
            {"_id": 0, "cumulative_cents": 1},
        )
        if doc is None:
            return None
        return int(doc.get("cumulative_cents", 0) or 0)
    except Exception as exc:
        logger.debug(
            "budget_counter.read_cents failed (scope=%s/%s): %s",
            scope, scope_id, exc,
        )
        return None


async def seed_from_aggregation(
    *,
    scope: str,
    scope_id: str,
    period: str,
    period_start: str,
    aggregated_usd: float,
) -> None:
    """Seed the counter from a one-shot aggregation result.

    Used when ``read_cents`` returns None and the caller has just
    computed the spend via the legacy aggregation path. After this,
    subsequent reads hit the counter directly.

    Uses ``$max`` semantics conceptually: we only seed if missing, so
    that concurrent seeders don't double-count. We do this with
    ``$setOnInsert`` on a fresh upsert.
    """
    if aggregated_usd is None or aggregated_usd < 0:
        aggregated_usd = 0.0
    cents = int(round(aggregated_usd * 100))
    try:
        from database import db
        coll = db.ai_budget_counters
        now_iso = datetime.now(timezone.utc).isoformat()
        await coll.update_one(
            _key_filter(scope, scope_id, period, period_start),
            {
                "$setOnInsert": {
                    "cumulative_cents": cents,
                    "event_count": 0,  # we don't know yet; will catch up
                    "updated_at": now_iso,
                },
            },
            upsert=True,
        )
    except Exception as exc:
        logger.debug("budget_counter.seed_from_aggregation failed: %s", exc)


def cents_to_usd(cents: Optional[int]) -> float:
    """Convert integer cents back to USD float. None → 0.0."""
    if cents is None:
        return 0.0
    return cents / 100.0
