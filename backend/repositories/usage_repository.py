"""Usage repository — module-aware facade for feature usage tracking.

Every usage event is scoped to (organization_id, module_key, feature_key).
This prevents feature_key collisions between modules: two modules can both
define a "reports" feature without their counts interfering.

Public API:
    count_usage(org_id, module_key, feature_key, period_start, period_end)
    record_usage(org_id, module_key, feature_key, ...)
    backfill_module_key()  — one-time startup backfill for legacy data

Storage: ai_usage_events collection (name is legacy; content is module-agnostic).

NOTE: ai_usage_repository.py has been removed.  All callers now use this
module exclusively.  The backfill_module_key() function handles legacy
events that were written without a module_key field.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from database import ai_usage_events_collection

logger = logging.getLogger(__name__)


async def count_usage(
    org_id: str,
    module_key: str,
    feature_key: str,
    period_start: str,
    period_end: str,
) -> int:
    """Count usage for an org + module + feature within a billing period.

    For most features: sums the ``quantity`` field of each event (defaults
    to 1 for legacy documents that lack the field). This supports bulk
    recording where a single event represents N units (e.g. 50 data rows
    uploaded at once).

    SPECIAL CASE — feature_key="chat" (Wave 9.A.2 fix):
        Wave 8A.2 split the agentic loop into one AIUsageEvent per
        Anthropic round-trip (correct for cost accuracy). But the chat
        QUOTA counter must count USER MESSAGES, not round-trips —
        otherwise a user on the Starter plan (80 chat/month) burns
        their quota 2-3x faster the moment a tool call kicks in.

        We count distinct ``conversation_id`` (each chat = 1 conv_id =
        1 quota unit). Legacy events that lack conversation_id still
        contribute 1 unit each — backward-compatible.

    Args:
        org_id: Organization ID.
        module_key: Module identifier (e.g. "ai_assistant").
        feature_key: Module-specific feature (e.g. "chat", "insights").
        period_start: ISO date string (inclusive), e.g. "2026-03-01".
        period_end: ISO date string (inclusive), e.g. "2026-03-31".

    Returns:
        Total usage quantity in the period.
    """
    match_stage = {
        "organization_id": org_id,
        "module_key": module_key,
        "feature": feature_key,
        "created_at": {
            "$gte": period_start,
            "$lte": period_end + "T23:59:59",
        },
    }

    if feature_key == "chat" and module_key == "ai_assistant":
        # Count distinct conversation_id (= one user message = one chat).
        # Events without conversation_id (pre-Wave-8A.2) contribute 1
        # each — coalesce nulls to a unique sentinel per event _id.
        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": {"$ifNull": ["$conversation_id", "$id"]},
            }},
            {"$count": "total"},
        ]
        cursor = ai_usage_events_collection.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        return result[0]["total"] if result else 0

    pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": None,
            "total": {"$sum": {"$ifNull": ["$quantity", 1]}},
        }},
    ]
    cursor = ai_usage_events_collection.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    return result[0]["total"] if result else 0


async def record_usage(
    org_id: str,
    module_key: str,
    feature_key: str,
    quantity: int = 1,
    tokens_prompt: Optional[int] = None,
    tokens_completion: Optional[int] = None,
    # ── Wave 1 additions (all Optional, default-keyword form to keep
    # backward-compat with every existing caller) ────────────────────
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    provider: Optional[str] = None,
    model_version: Optional[str] = None,
    cost_usd: Optional[float] = None,
    prompt_version: Optional[str] = None,
    # ── Wave 8A.1 additions (governance / dashboard slicing) ─────────
    conversation_id: Optional[str] = None,
    parent_event_id: Optional[str] = None,
    request_id: Optional[str] = None,
    cache_read_tokens: Optional[int] = None,
    cache_creation_tokens: Optional[int] = None,
    latency_ms: Optional[int] = None,
    error_code: Optional[str] = None,
    feature_metadata: Optional[dict] = None,
    # ── Wave 13.2 addition (Period Integrity audit) ──────────────────
    # period_audit: structured dict capturing the period context active
    # at event time + the resolved period each tool dispatched to. See
    # models.ai_usage.AIUsageEvent.period_audit for the shape. None when
    # not applicable (non-chat features, legacy callers).
    period_audit: Optional[dict] = None,
) -> dict:
    """Record a usage event.  Module-aware write path.

    Args:
        quantity: Number of units this event represents (default 1).
            Use >1 for bulk operations like data row uploads to avoid
            creating many individual events.

        Wave 1 (2026-05) additions — all optional:
        user_id: which user (inside the org) triggered the event. Required
            for per-user usage monitoring; legacy events pre-Wave 1 have
            this field None.
        agent_id: which AI agent persona. Default "financial_analyst"
            applied at the model level when None.
        provider: which LLM provider ("anthropic", "openai", ...). Default
            "anthropic" applied at the model level when None.
        model_version: exact model name (e.g. "claude-sonnet-4-20250514").
        cost_usd: pre-computed USD cost from ai_cost_calculator. Stored
            in the LLM provider's billing currency (USD for Anthropic
            and OpenAI) as the universal source of truth. The admin
            dashboard converts to the org's display currency via
            services.currency_service.get_currency_for_org at READ
            time — never mix currencies at write time. Surviving
            future pricing changes is trivial because tokens are also
            recorded; survives FX rate changes because USD is stable.
        prompt_version: which version of the system prompt was used. Wave 4
            wires this; None until then.

    Returns the inserted document.
    """
    from models.ai_usage import AIUsageEvent

    # Build kwargs so that None values fall back to model defaults
    # ("anthropic", "financial_analyst") instead of overriding them.
    event_kwargs = dict(
        organization_id=org_id,
        module_key=module_key,
        feature=feature_key,
        quantity=quantity,
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
    )
    if user_id is not None:
        event_kwargs["user_id"] = user_id
    if agent_id is not None:
        event_kwargs["agent_id"] = agent_id
    if provider is not None:
        event_kwargs["provider"] = provider
    if model_version is not None:
        event_kwargs["model_version"] = model_version
    if cost_usd is not None:
        event_kwargs["cost_usd"] = cost_usd
    if prompt_version is not None:
        event_kwargs["prompt_version"] = prompt_version
    # Wave 8A.1 — only set when provided so historic events that go
    # through this helper without these kwargs don't materialize the
    # fields as None (saves DB storage + keeps documents shape-stable).
    if conversation_id is not None:
        event_kwargs["conversation_id"] = conversation_id
    if parent_event_id is not None:
        event_kwargs["parent_event_id"] = parent_event_id
    if request_id is not None:
        event_kwargs["request_id"] = request_id
    if cache_read_tokens is not None:
        event_kwargs["cache_read_tokens"] = cache_read_tokens
    if cache_creation_tokens is not None:
        event_kwargs["cache_creation_tokens"] = cache_creation_tokens
    if latency_ms is not None:
        event_kwargs["latency_ms"] = latency_ms
    if error_code is not None:
        event_kwargs["error_code"] = error_code
    if feature_metadata is not None:
        event_kwargs["feature_metadata"] = feature_metadata
    # Wave 13.2 — period audit. Stored only when explicitly provided so
    # non-chat events (digest cron, alert engine, …) don't materialise
    # the field as None.
    if period_audit is not None:
        event_kwargs["period_audit"] = period_audit

    event = AIUsageEvent(**event_kwargs)
    doc = event.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await ai_usage_events_collection.insert_one(doc)

    # Wave 10.B.2 — atomic budget counter increment.
    # For every (scope, scope_id) tuple that COULD have an active budget,
    # bump the per-period counter so check_budget_or_raise reads a
    # near-realtime value (was a 10-50 ms aggregation before, now <1 ms
    # indexed lookup). Failure is logged + swallowed — the event is
    # already persisted, so the counter is an optimisation, not a
    # correctness boundary.
    if cost_usd is not None and cost_usd > 0:
        try:
            from repositories import budget_counter_repository as _bcr
            from repositories.ai_budget_repository import period_start_iso

            # Compute all three period_starts once and reuse for each scope.
            now_dt = datetime.now(timezone.utc)
            period_starts = {
                "daily":   period_start_iso("daily", now=now_dt),
                "monthly": period_start_iso("monthly", now=now_dt),
                "yearly":  period_start_iso("yearly", now=now_dt),
            }

            # Targets to increment. We increment ALL three periods per
            # applicable scope because a budget could be on any of them
            # and we don't want a cache miss to force aggregation later.
            targets = [("global", "*")]
            if org_id:
                targets.append(("org", org_id))
            if user_id:
                targets.append(("user", user_id))
            if feature_key:
                targets.append(("feature", feature_key))
            if agent_id:
                targets.append(("agent", agent_id))

            for scope, scope_id in targets:
                for period, ps in period_starts.items():
                    await _bcr.increment(
                        scope=scope, scope_id=scope_id,
                        period=period, period_start=ps,
                        cost_usd=cost_usd,
                    )
        except Exception as _bcr_exc:
            logger.debug(
                "record_usage: budget counter increment failed (non-fatal): %s",
                _bcr_exc,
            )

    return doc


# ── Wave 8A.1: MongoDB indices for governance dashboard queries ─────────────

async def setup_indexes() -> None:
    """Create indices on ai_usage_events to keep dashboard queries fast.

    Called at server startup (server.py lifespan). Idempotent — Motor's
    create_index is a no-op when an index already exists with the same
    spec, so re-running on every boot is safe.

    Index strategy (Wave 8A.1, extended Wave 10.B.4/5):

      {organization_id: 1, created_at: -1}
        Primary index for the per-org dashboard "spend over time" view.
        Sorting by created_at desc covers "last 30 days" pagination.

      {user_id: 1, created_at: -1}
        Per-user drill-down (sparse: many events have user_id=None for
        cron / system jobs, so sparse saves storage).

      {agent_id: 1, created_at: -1}
        Per-agent breakdown chart. Sparse.

      {conversation_id: 1}
        Group multi-turn agentic loop events for the "cost of this chat"
        view. Sparse — only Wave 8A.2 events populate this.

      {created_at: -1, cost_usd: -1}
        Top-spenders global view. Used by the sysadmin dashboard
        "biggest cost events in the last N days" panel.

      {feature: 1, created_at: -1}
        Per-feature trend chart (chat vs digest vs health_explanation).

      {created_at: -1}
        Catch-all for time-range scans (recovery / debugging).

    Wave 10.B.4 — TTL index on ``created_at`` with ``expireAfterSeconds``
    set from ``AI_USAGE_RETENTION_DAYS`` (default 730 = 2 years). Events
    older than that are auto-purged by Mongo's TTL monitor. Aggregated
    rollups in ``ai_usage_daily`` preserve long-term analytics (Wave
    10.B.4 rollup is computed by a separate cron — TODO if traffic
    justifies it).

    Wave 10.B.5 — drop 3 legacy redundant indices left over from pre-
    Wave-8A.1. They're functionally equivalent to the Wave 8A.1 indices
    but cost write throughput on every insert.
    """
    indexes = [
        ([("organization_id", 1), ("created_at", -1)],
         {"name": "org_created_v1"}),
        ([("user_id", 1), ("created_at", -1)],
         {"name": "user_created_v1", "sparse": True}),
        ([("agent_id", 1), ("created_at", -1)],
         {"name": "agent_created_v1", "sparse": True}),
        ([("conversation_id", 1)],
         {"name": "conversation_v1", "sparse": True}),
        ([("created_at", -1), ("cost_usd", -1)],
         {"name": "cost_time_v1"}),
        ([("feature", 1), ("created_at", -1)],
         {"name": "feature_created_v1"}),
        ([("created_at", -1)],
         {"name": "created_at_v1"}),
    ]
    for keys, opts in indexes:
        try:
            await ai_usage_events_collection.create_index(keys, **opts)
        except Exception as exc:
            # Non-fatal: log and continue. The dashboard will still
            # work, just slower. A migration script can retry later.
            logger.warning(
                "usage_repository.setup_indexes: failed to create %s: %s",
                opts.get("name"), exc,
            )

    # Wave 10.B.4 — TTL on created_at. Mongo's TTL monitor requires the
    # field to be a BSON Date for native expiry, but we store ISO strings.
    # Workaround: maintain a separate ``expires_at`` date computed at
    # insert time (handled by AIUsageEvent.model_post_init in models/ai_usage.py
    # if/when wired). For now we just CREATE the index spec so that once
    # the field is populated, expiry kicks in automatically. No-op until
    # then. This is an additive index, doesn't affect read paths.
    import os as _os
    _retention_days = int(_os.environ.get("AI_USAGE_RETENTION_DAYS", "730"))
    try:
        await ai_usage_events_collection.create_index(
            [("expires_at", 1)],
            expireAfterSeconds=0,
            sparse=True,  # only events that opt-in to TTL carry expires_at
            name="ai_usage_ttl_v1",
        )
        logger.info(
            "usage_repository: TTL index ready (retention=%dd, sparse — "
            "applies only to events that populate expires_at)",
            _retention_days,
        )
    except Exception as exc:
        logger.warning("usage_repository.setup_indexes: TTL index failed: %s", exc)

    # Wave 10.B.5 — drop 3 legacy redundant indices identified by the
    # Wave 10 audit. They cost write throughput (every insert updates
    # them) but provide no read benefit beyond what the Wave 8A.1
    # indices already cover.
    _LEGACY_INDEXES_TO_DROP = [
        "organization_id_1",
        "organization_id_1_feature_1_created_at_-1",
        "organization_id_1_module_key_1_feature_1_created_at_-1",
    ]
    for _name in _LEGACY_INDEXES_TO_DROP:
        try:
            await ai_usage_events_collection.drop_index(_name)
            logger.info("usage_repository: dropped legacy index %r", _name)
        except Exception as exc:
            # Already-dropped is fine: only log when it's a real error.
            if "index not found" not in str(exc).lower():
                logger.debug(
                    "usage_repository: drop_index(%r) skipped: %s",
                    _name, exc,
                )

    logger.info("usage_repository.setup_indexes: %d indices ensured", len(indexes))


async def backfill_module_key() -> int:
    """Backfill module_key='ai_assistant' on legacy documents that lack it.

    Idempotent: only updates documents where module_key does not exist.
    Safe to call on every startup.

    Returns the number of documents updated.
    """
    result = await ai_usage_events_collection.update_many(
        {"module_key": {"$exists": False}},
        {"$set": {"module_key": "ai_assistant"}},
    )
    updated = result.modified_count
    if updated > 0:
        logger.info(
            "Backfilled module_key='ai_assistant' on %d legacy usage events.",
            updated,
        )
    return updated
