"""Atomic per-(key) rate limit counter — Wave 10.A.6.

Replaces the count_documents + later-insert TOCTOU pattern used in
several places (most notably /modules/{module_key}/health-explanation-ai
where 50 concurrent clicks could all pass a "count <= 10" check before
any of them wrote their usage event).

Design
------
A dedicated collection ``rate_limit_counters`` holds one document per
(key, bucket_minute_iso). The atomic operation is:

    findOneAndUpdate(
        {"key": key, "bucket": minute_iso},
        {"$inc": {"count": 1},
         "$setOnInsert": {"created_at": now_iso, "expires_at": ttl_dt}},
        upsert=True,
        return_document=AFTER,
    )

The returned ``count`` is the post-increment value. If it exceeds the
limit, we decrement back (best-effort) and raise. The caller catches
``RateLimitExceeded`` and turns it into HTTP 429.

A TTL index on ``expires_at`` cleans up old buckets after ~10 minutes
so the collection never grows unbounded.

Why a separate collection and not ai_usage_events?
--------------------------------------------------
ai_usage_events is written AFTER the AI call returns (we need the token
counts). The rate-limit check must happen BEFORE the call. Mixing the
two means racing 50 concurrent requests can all read "count<limit" and
all proceed. A dedicated pre-increment counter is the only way to make
the check race-free.

Fail-open
---------
If Mongo is unreachable, the helper returns ``None`` and the caller
treats it as "allowed" (same defense-in-depth as budget_guard). The
caller logs a warning so ops sees the degraded state.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional


logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when the atomic counter for a key crosses its limit.

    Attributes:
        key: the rate-limit key (e.g. f"health_explanation:{org_id}:{user_id}")
        limit: the per-bucket cap
        count: the actual post-increment count (= limit + 1)
        bucket: the minute bucket where the cap was hit
    """

    def __init__(self, key: str, limit: int, count: int, bucket: str):
        super().__init__(
            f"Rate limit exceeded for key={key!r}: {count} > {limit} in bucket={bucket}",
        )
        self.key = key
        self.limit = limit
        self.count = count
        self.bucket = bucket


_TTL_INDEX_CREATED = False


async def _ensure_index() -> None:
    """Idempotent TTL index creation. Called lazily on first use to avoid
    coupling to server.py startup.
    """
    global _TTL_INDEX_CREATED
    if _TTL_INDEX_CREATED:
        return
    try:
        from database import db
        coll = db.rate_limit_counters
        await coll.create_index(
            [("expires_at", 1)], expireAfterSeconds=0,
            name="rate_limit_ttl_v1",
        )
        await coll.create_index(
            [("key", 1), ("bucket", 1)],
            unique=True,
            name="rate_limit_key_bucket_v1",
        )
        _TTL_INDEX_CREATED = True
    except Exception as exc:
        # Non-fatal: the counter still works without the indexes (slower
        # cleanup + writes won't be unique-enforced). Ops will see the
        # warning and can run setup_indexes manually.
        logger.warning("rate_limit: ensure_index failed: %s", exc)


def _minute_bucket(now: Optional[datetime] = None) -> str:
    """Return the current minute as 'YYYY-MM-DDTHH:MM' — the bucket key."""
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M")


async def acquire(
    *,
    key: str,
    limit: int,
    window_seconds: int = 60,
) -> int:
    """Atomically increment the per-(key, current-minute) counter and
    return the post-increment value.

    Raises ``RateLimitExceeded`` if the post-increment count is over
    ``limit``. On Mongo error, logs a warning and returns 0 (fail-open
    behaviour consistent with budget_guard).

    Args:
        key: any string identifying the rate-limit scope. Conventionally
            ``"<feature>:<org_id>:<user_id>"`` so two users in the same
            org get separate buckets.
        limit: max calls per minute window.
        window_seconds: TTL on the bucket document. Default 60s. Set
            higher to keep buckets alive for longer windows (this
            implementation is always 1-minute-bucketed, but TTL is
            independent of bucket size).
    """
    await _ensure_index()

    bucket = _minute_bucket()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=max(window_seconds, 60) + 30)

    try:
        from database import db
        from pymongo import ReturnDocument
        coll = db.rate_limit_counters
        doc = await coll.find_one_and_update(
            {"key": key, "bucket": bucket},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {
                    "created_at": now.isoformat(),
                    "expires_at": expires_at,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        count = int(doc.get("count", 0) or 0)
    except Exception as exc:
        # Fail-open: log and let the call proceed. The caller may have
        # other defenses (budget guard, IP slowapi, etc.).
        logger.warning(
            "rate_limit.acquire: Mongo error for key=%r (fail-open): %s",
            key, exc,
        )
        return 0

    if count > limit:
        # Best-effort: decrement so the burst doesn't "stick" in the
        # bucket and trigger 429s for the remaining seconds of the minute
        # unfairly. Not strictly necessary (the bucket resets in <60s)
        # but it's the polite move when we know the request didn't run.
        try:
            from database import db
            await db.rate_limit_counters.update_one(
                {"key": key, "bucket": bucket},
                {"$inc": {"count": -1}},
            )
        except Exception:
            pass  # decrement best-effort only
        raise RateLimitExceeded(
            key=key, limit=limit, count=count, bucket=bucket,
        )

    return count
