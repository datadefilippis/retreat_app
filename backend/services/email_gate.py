"""
Pre-flight email send gate (Fase 2 Track G — Step G1, "B2.5").

Inspects the recipient's `email_status` field on user / customer_account
documents BEFORE handing the message to Brevo. Skips delivery when the
address is in a known-bad state (bounced / blocked / unsubscribed) so we
stop eroding our Brevo sender reputation by retrying dead inboxes.

Closes the loop opened by Phase 1 Step B2:
  B2 (webhook)   →  writes email_status to users / customer_accounts
  G1 (this file) →  reads it before every outbound email

Why sync (not async)
--------------------
`email_service.send_email()` is sync (uses urllib). Making it async
would touch every caller across the codebase and is out of scope for
this micro-step. We open a separate sync pymongo client here; the
`pymongo` package is already an indirect dependency of `motor` so no
new install is needed.

Both motor (writers) and pymongo (this gate) point at the same MongoDB
instance — there is no consistency concern: the field is set once on
bounce by the webhook, and stays bounced until an admin action resets
it. The 5-minute in-process cache is therefore safe.

Defensive contract
------------------
Every error path in this module returns "NOT BLOCKED" — fail-open is
the correct policy here. A temporary DB hiccup, a missing env var, a
serialization quirk, must NEVER silently kill all outgoing email. The
worst case of fail-open is "we send an email to a bounced address",
exactly what we did before this gate existed.

Public API
----------
    is_email_blocked(email)   →  (bool, Optional[str])
        True + reason  ⇒ skip delivery
        False + None   ⇒ proceed (or fail-open path)

    invalidate_cache(email=None)
        Drop a single entry or wipe the whole cache. Used by tests
        and (future) the admin "Mark as deliverable" action.
"""
from __future__ import annotations

import logging
import os
import time
from threading import Lock
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# ── Statuses that block sending ─────────────────────────────────────────────
# Source-of-truth set, kept in one place. Webhook B2 writes any of:
#   "bounced" | "complaint" | "blocked" | "unsubscribed"
#
# We block 3 out of 4. Why "complaint" is NOT blocked:
#   - A "complaint" (user marked us as spam) ALREADY took the reputation
#     hit at the moment they clicked. Blocking further sends doesn't
#     undo damage and risks losing legitimate retries (e.g. password
#     reset for an admin who later un-spammed us).
#   - Legal duty applies to "unsubscribed" not "complaint".
# The set is overridable via env for ops experiments without redeploy.

_DEFAULT_BLOCKING_STATUSES = frozenset({"bounced", "blocked", "unsubscribed"})


def _resolve_blocking_statuses() -> frozenset[str]:
    """Read EMAIL_GATE_BLOCK env (comma-list) or fall back to default."""
    env_val = os.environ.get("EMAIL_GATE_BLOCK", "").strip()
    if not env_val:
        return _DEFAULT_BLOCKING_STATUSES
    parsed = {s.strip().lower() for s in env_val.split(",") if s.strip()}
    if not parsed:
        return _DEFAULT_BLOCKING_STATUSES
    return frozenset(parsed)


_BLOCKING_STATUSES = _resolve_blocking_statuses()


# ── Sync pymongo client (lazy-init, process-level) ───────────────────────────
# Kept separate from the motor client used by FastAPI routes so this gate
# works from sync helpers, sync tests, async routes — without juggling
# event loops.

_pymongo_client = None
_pymongo_db = None
_pymongo_lock = Lock()


def _get_db():
    """Return the sync pymongo db handle, lazy-initialised. None on failure."""
    global _pymongo_client, _pymongo_db
    if _pymongo_db is not None:
        return _pymongo_db

    with _pymongo_lock:
        # Double-check inside the lock (classic singleton pattern).
        if _pymongo_db is not None:
            return _pymongo_db

        try:
            from pymongo import MongoClient
        except ImportError:
            logger.warning(
                "email_gate: pymongo not installed — gate is no-op (fail-open)"
            )
            return None

        url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        if not url or not db_name:
            logger.warning(
                "email_gate: MONGO_URL or DB_NAME missing — gate is no-op (fail-open)"
            )
            return None

        try:
            _pymongo_client = MongoClient(
                url,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                socketTimeoutMS=2000,
            )
            _pymongo_db = _pymongo_client[db_name]
            return _pymongo_db
        except Exception as e:
            logger.warning(
                "email_gate: pymongo client init failed err=%s — fail-open",
                e,
            )
            return None


# ── In-process LRU-ish cache with TTL ────────────────────────────────────────
# Keyed by lowercased email. Entry shape: (expires_at_ts, status_or_None).
# Bounded to 5000 entries (cleared wholesale when full — simple is fine,
# this is a per-process cache that only matters during request bursts).

_CACHE_TTL_SECONDS = 300       # 5 minutes
_CACHE_MAX_ENTRIES = 5000

_cache: dict[str, Tuple[float, Optional[str]]] = {}
_cache_lock = Lock()


def _cache_get(email: str) -> Optional[Optional[str]]:
    """Return the cached status (which may be None = "not blocked"), or
    a sentinel `_MISS` if no fresh entry exists.
    """
    now = time.time()
    with _cache_lock:
        entry = _cache.get(email)
    if entry is None:
        return _MISS
    expires_at, status = entry
    if now > expires_at:
        return _MISS
    return status


# Sentinel object — `None` is a valid cached value (= "checked, not blocked").
_MISS = object()


def _cache_set(email: str, status: Optional[str]) -> None:
    expires_at = time.time() + _CACHE_TTL_SECONDS
    with _cache_lock:
        if len(_cache) > _CACHE_MAX_ENTRIES:
            # Crude eviction: drop everything. The next ~minute of sends
            # will re-query Mongo, then the cache fills again. Acceptable.
            _cache.clear()
        _cache[email] = (expires_at, status)


def _mask_email(email: str) -> str:
    """Mask email for logs. PII protection: never log full addresses."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:2]}***@{domain}"


# ── Public API ───────────────────────────────────────────────────────────────

def is_email_blocked(email: str) -> Tuple[bool, Optional[str]]:
    """Decide whether an outbound email to `email` should be skipped.

    Args:
        email: recipient address (case-insensitive; trimmed internally).

    Returns:
        (True, reason)  → caller MUST skip the send; `reason` is one of
                          "bounced" / "blocked" / "unsubscribed"
                          (or whatever the EMAIL_GATE_BLOCK env mandates).
        (False, None)   → caller MAY send. This is also the fail-open
                          response for any unexpected error.

    Idempotent. Thread-safe. Never raises.
    """
    if not email:
        return (False, None)

    addr = email.strip().lower()

    # ── Cache layer ──────────────────────────────────────────────────────────
    cached = _cache_get(addr)
    if cached is not _MISS:
        # `cached` is the persisted status (str) or None.
        if cached and cached in _BLOCKING_STATUSES:
            return (True, cached)
        return (False, None)

    # ── DB layer (lazy connect) ──────────────────────────────────────────────
    db = _get_db()
    if db is None:
        # No DB available → fail-open. Don't cache the miss (we want to
        # retry on the next send in case the DB comes back).
        return (False, None)

    found_status: Optional[str] = None
    try:
        # users + customer_accounts both index `email`. Two tiny queries
        # (each <2ms typical), can't merge into one because they live
        # in different collections.
        for coll_name in ("users", "customer_accounts"):
            doc = db[coll_name].find_one(
                {"email": addr},
                {"email_status": 1, "_id": 0},
            )
            if not doc:
                continue
            status = doc.get("email_status")
            if status in _BLOCKING_STATUSES:
                found_status = status
                break  # one bad collection is enough
    except Exception as e:
        # Any error (timeout, unavailable, malformed doc) → fail-open.
        # Importantly: don't cache the failure either, so transient
        # outages self-heal on retry.
        logger.warning(
            "email_gate: query failed email=%s err=%s — fail-open",
            _mask_email(addr), type(e).__name__,
        )
        return (False, None)

    # ── Cache the result (None = "checked, clean") ──────────────────────────
    _cache_set(addr, found_status)

    if found_status:
        logger.info(
            "email_gate: BLOCK send email=%s status=%s",
            _mask_email(addr), found_status,
        )
        return (True, found_status)

    return (False, None)


def invalidate_cache(email: Optional[str] = None) -> None:
    """Drop a cache entry, or the whole cache if `email is None`.

    Use cases:
      - Tests: ensure isolation between test cases.
      - Future admin action "Mark deliverable" after a customer
        successfully reverifies their email — the cache must forget
        the prior bounced state.
    """
    with _cache_lock:
        if email is None:
            _cache.clear()
        else:
            _cache.pop(email.strip().lower(), None)
