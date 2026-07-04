"""Idempotency middleware — Phase 0 Step 8 (2026-05-28).

``Idempotency-Key`` header enforcement con response caching. Defense da:
  - Network retry (browser fa retry su 5xx)
  - User double-click sul checkout button
  - Mobile network instability (request "dispersa" + retry locale)
  - Embed widget cross-origin con bug di lock

Scope path
==========
ENFORCEMENT obbligatorio (header missing = 400):
  - /api/public/embed/*    (Stream A — embed widget)
  - /api/public/ai-site/*  (Stream B — AI-generated sites futuro)

GRACE PERIOD 90gg (header missing = warning log, no 400):
  - /api/public/order-request  (legacy storefront classic)

Tutti gli altri path → passthrough.

Algoritmo
=========
Per ogni request POST/PATCH/DELETE su path in scope con ``Idempotency-Key``:

  1. Calcola digest (org_id + path + key) → lookup ``idempotency_keys_collection``
  2. Hit cache → return cached response (status + body + headers selected)
  3. Miss → process downstream + cache la response per 24h con expires_at TTL
  4. Concurrent: race protection via unique index su digest → second request
     attende il primo (deferred, beyond Step 8 scope)

Storage
=======
``idempotency_keys_collection``:
  {
    "digest": str,                # SHA-256(org_id + path + key)
    "key": str,                   # original Idempotency-Key (per debug)
    "organization_id": str | None,
    "path": str,
    "status": str,                # "pending" | "completed"
    "response_status": int,
    "response_body": str,         # JSON serialized
    "response_content_type": str,
    "created_at": str (ISO),      # debug field, no TTL — ISO ok
    "expires_at": datetime        # BSON Date — TTL index expireAfterSeconds=0
                                  # (Track O Step 1.1 fix — pre-O1.1 era ISO
                                  #  string, MongoDB TTL ignorava silenziosamente
                                  #  → collection growth unbounded)
  }
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse, PlainTextResponse


logger = logging.getLogger(__name__)

# Track S Step 3.2 — race condition fix tunables (module-level for testability)
LOCK_POLL_INTERVAL_SEC = 0.2   # 200ms between polls when waiting for race winner
LOCK_POLL_TIMEOUT_SEC = 30.0   # max wait for downstream to complete (Stripe etc.)


# ── Scope configuration ───────────────────────────────────────────────────


# Enforcement path: header obbligatorio
ENFORCEMENT_PATHS = (
    "/api/public/embed/",
    "/api/public/ai-site/",
)

# Grace path: header opzionale (warning log only)
GRACE_PATHS = (
    "/api/public/order-request",
)

# Methods che richiedono idempotency (read-only methods skip)
IDEMPOTENT_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


# ── Metrics hook (Phase 0 Step 10) ────────────────────────────────────────
def _record_idem(result: str, scope: str) -> None:
    """Record idempotency outcome. Soft-fails so middleware path never breaks."""
    try:
        from core.observability import metrics as _metrics
        _metrics.record_idempotency(result=result, scope=scope)
    except Exception:
        pass


# ── Cache TTL ─────────────────────────────────────────────────────────────


CACHE_TTL_HOURS = 24


def _new_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=CACHE_TTL_HOURS)


# ── Digest computation ────────────────────────────────────────────────────


def _compute_digest(org_id: Optional[str], path: str, key: str) -> str:
    """Compute SHA-256 digest as cache key.

    Including org_id + path prevents collision when 2 different orgs use
    the same Idempotency-Key (e.g. UUID generated client-side).
    """
    raw = f"{org_id or 'guest'}|{path}|{key}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ── Repository helpers (inline to avoid circular import) ─────────────────


async def _lookup_cached_response(digest: str) -> Optional[dict]:
    """Find existing idempotency record by digest. Returns dict or None.

    Track O Step 1.1: dopo il fix BSON Date su expires_at + TTL index,
    MongoDB auto-cleanup ogni doc expired (background thread, 60s polling).
    Mantiene defensive filter manuale per:
      1. record legacy ancora con expires_at ISO string (pre-O1.1)
      2. record appena scaduti che TTL non ha ancora processato (race
         window < 60s tra scadenza e cleanup)
    """
    try:
        from database import idempotency_keys_collection
        now = datetime.now(timezone.utc)
        doc = await idempotency_keys_collection.find_one(
            {"digest": digest},
            {"_id": 0},
        )
        if not doc:
            return None
        # Defensive filter manuale: accetta sia datetime (post-O1.1) che
        # ISO string (legacy pre-O1.1) per backward-compat durante migration.
        exp = doc.get("expires_at")
        if exp:
            if isinstance(exp, datetime):
                if exp < now:
                    return None
            elif isinstance(exp, str):
                # Legacy ISO string — confronto lessicografico funziona per ISO 8601
                if exp < now.isoformat():
                    return None
        return doc
    except Exception as exc:
        logger.warning("Idempotency: cache lookup failed: %s", exc)
        return None


async def _store_cached_response(
    *,
    digest: str,
    key: str,
    organization_id: Optional[str],
    path: str,
    status_code: int,
    body_bytes: bytes,
    content_type: str,
) -> None:
    """Persist response to cache for replay.

    Track S Step 3.2: this is now the SECOND phase of the 2-phase flow.
    The claim doc was inserted by _claim_idempotency_lock() before
    call_next(). Here we just UPDATE with the response data — no upsert
    needed since the doc already exists.
    """
    try:
        from database import idempotency_keys_collection
        # Decode body to UTF-8 string for Mongo storage. If body is not
        # decodable (binary), skip caching — idempotency cache is for
        # JSON responses primarily.
        try:
            body_str = body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger.info("Idempotency: skipping binary response caching")
            return

        # UPDATE the pending claim doc with the response. No upsert:
        # if no doc exists (race claim failed but we somehow got here),
        # we just lose the cache write (not a correctness issue).
        await idempotency_keys_collection.update_one(
            {"digest": digest},
            {
                "$set": {
                    "status": "completed",
                    "response_status": status_code,
                    "response_body": body_str,
                    "response_content_type": content_type,
                },
            },
        )
    except Exception as exc:
        # Cache write failure non blocca la response — log warning only.
        logger.warning("Idempotency: cache store failed: %s", exc)


# ── Track S Step 3.2 — Claim-the-lock pattern for race protection ────────


async def _claim_idempotency_lock(
    *,
    digest: str,
    key: str,
    organization_id: Optional[str],
    path: str,
) -> bool:
    """Try to atomically claim the lock for this idempotency digest.

    Returns True if we won the race (proceed to call_next), False if
    another request already claimed (caller should poll for completion).

    Implementation: insert pending doc. Unique index on `digest` (added
    in database.py create_indexes) makes the insert atomic — exactly
    one concurrent caller wins.
    """
    try:
        from pymongo.errors import DuplicateKeyError
    except ImportError:
        # pymongo not available — fall back to no-lock (cache lookup
        # only). Race protection degraded but middleware still functional.
        return True

    try:
        from database import idempotency_keys_collection
        # Track O Step 1.1 — TTL bug fix:
        # expires_at DEVE essere BSON Date (datetime obj), NON ISO string.
        # MongoDB TTL index su ISO string ignora silenziosamente i record
        # → collection cresceva unbounded pre-O1.1.
        # created_at puo' rimanere ISO string (no TTL, solo debug field).
        now_iso = datetime.now(timezone.utc).isoformat()
        expires_at_dt = _new_expires_at()  # datetime, NO isoformat
        await idempotency_keys_collection.insert_one({
            "digest": digest,
            "key": key,
            "organization_id": organization_id,
            "path": path,
            "status": "pending",
            "created_at": now_iso,
            "expires_at": expires_at_dt,  # BSON Date — TTL index funziona
        })
        return True  # We won
    except DuplicateKeyError:
        # Another request beat us — they're processing now.
        logger.info(
            "Idempotency: lock contention digest=%s path=%s — polling for winner",
            digest[:16], path,
        )
        return False
    except Exception as exc:
        # Any other error (e.g. Mongo unreachable) — log + degrade to
        # no-lock. Better to risk a double-process than 500 the request.
        logger.warning("Idempotency: claim insert failed: %s — degraded mode", exc)
        return True


async def _poll_for_lock_completion(digest: str) -> Optional[dict]:
    """Poll the cache for the winner's response_status until set or timeout.

    Returns the completed cached doc if winner completes within timeout,
    None on timeout. Polling interval LOCK_POLL_INTERVAL_SEC, max wait
    LOCK_POLL_TIMEOUT_SEC.
    """
    deadline = time.time() + LOCK_POLL_TIMEOUT_SEC
    while time.time() < deadline:
        await asyncio.sleep(LOCK_POLL_INTERVAL_SEC)
        doc = await _lookup_cached_response(digest)
        if doc and doc.get("response_status") is not None:
            return doc
    return None


# ── Feature flag (default ON in dev/test, can disable per env) ──────────


def idempotency_enforced() -> bool:
    """Feature flag for emergency rollback.

    Default ON. Set IDEMPOTENCY_ENFORCED=false to bypass middleware
    (only blocks enforcement; passthrough behavior).
    """
    val = os.environ.get("IDEMPOTENCY_ENFORCED", "true")
    return val.strip().lower() in ("true", "1", "yes", "on")


# ── Helper to extract organization context ──────────────────────────────


def _extract_org_id(request: Request) -> Optional[str]:
    """Best-effort org_id extraction from request.

    Strategies (in order):
      1. Query/path param ``slug`` → lookup is deferred (we don't hit DB
         in middleware for perf); use slug itself as proxy for org scoping
      2. Bearer JWT decoded (would require auth import — skipped for perf)

    Returns the slug as proxy. The digest is keyed on (slug, path, key)
    which provides multi-tenant isolation good enough.
    """
    if request.path_params and "slug" in request.path_params:
        return request.path_params["slug"]
    slug = request.query_params.get("slug")
    if slug:
        return slug
    return None


# ── Middleware ────────────────────────────────────────────────────────────


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Enforce Idempotency-Key on /embed/* + /ai-site/*; grace on /order-request.

    Behavior:

      method NOT idempotent (GET, HEAD, OPTIONS)
        → passthrough

      path NOT in ENFORCEMENT_PATHS or GRACE_PATHS
        → passthrough

      path IN ENFORCEMENT_PATHS, no Idempotency-Key
        → 400 (header required)

      path IN GRACE_PATHS, no Idempotency-Key
        → passthrough + warning log

      Idempotency-Key present:
        → compute digest
        → cache lookup
        → HIT: return cached response (skip downstream entirely)
        → MISS: process downstream + cache response for 24h
    """

    async def dispatch(self, request: Request, call_next):
        # Skip middleware globally if feature flag OFF
        if not idempotency_enforced():
            return await call_next(request)

        method = request.method.upper()
        if method not in IDEMPOTENT_METHODS:
            return await call_next(request)

        path = request.url.path
        is_enforcement = any(path.startswith(p) for p in ENFORCEMENT_PATHS)
        is_grace = any(path.startswith(p) for p in GRACE_PATHS)

        if not is_enforcement and not is_grace:
            return await call_next(request)

        key = request.headers.get("Idempotency-Key")

        # No key handling
        if not key:
            if is_enforcement:
                _record_idem("enforced_reject", "enforcement")
                return JSONResponse(
                    status_code=400,
                    content={
                        "detail": (
                            "Idempotency-Key header obbligatorio. "
                            "Generare un UUID v4 per ogni richiesta + retry "
                            "con la stessa key."
                        ),
                        "code": "IDEMPOTENCY_KEY_REQUIRED",
                    },
                )
            # Grace: passthrough with warning log
            logger.warning(
                "Idempotency: missing key on grace path=%s — accepting, "
                "but enforcement will start in 90gg.",
                path,
            )
            _record_idem("grace_warn", "grace")
            return await call_next(request)

        # ── Compute digest ──
        org_id = _extract_org_id(request)
        digest = _compute_digest(org_id, path, key)

        # ── Cache lookup ──
        cached = await _lookup_cached_response(digest)
        if cached and cached.get("response_status") is not None:
            logger.info(
                "Idempotency: replay hit digest=%s path=%s",
                digest[:16], path,
            )
            _record_idem("hit", "enforcement" if is_enforcement else "grace")
            return Response(
                status_code=cached.get("response_status", 200),
                content=cached.get("response_body", ""),
                media_type=cached.get("response_content_type", "application/json"),
                headers={"X-Idempotent-Replay": "true"},
            )

        # If we found a "pending" doc, another worker is processing.
        # Skip the claim attempt and poll directly.
        if cached and cached.get("status") == "pending":
            _record_idem("race_wait", "enforcement" if is_enforcement else "grace")
            completed = await _poll_for_lock_completion(digest)
            if completed:
                return Response(
                    status_code=completed.get("response_status", 200),
                    content=completed.get("response_body", ""),
                    media_type=completed.get("response_content_type", "application/json"),
                    headers={"X-Idempotent-Replay": "true"},
                )
            # Timeout — return 409 Conflict (client should retry)
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "Concurrent request still in progress, retry shortly.",
                    "code": "IDEMPOTENCY_RACE_TIMEOUT",
                },
            )

        # ── Track S Step 3.2: claim the lock before downstream call ──
        # This is the critical race-protection step: insert a pending
        # doc with unique index on `digest`. Exactly one concurrent
        # request wins (insert succeeds); losers get DuplicateKeyError
        # and poll for the winner's response.
        won_lock = await _claim_idempotency_lock(
            digest=digest, key=key, organization_id=org_id, path=path,
        )
        if not won_lock:
            _record_idem("race_wait", "enforcement" if is_enforcement else "grace")
            completed = await _poll_for_lock_completion(digest)
            if completed:
                return Response(
                    status_code=completed.get("response_status", 200),
                    content=completed.get("response_body", ""),
                    media_type=completed.get("response_content_type", "application/json"),
                    headers={"X-Idempotent-Replay": "true"},
                )
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "Concurrent request still in progress, retry shortly.",
                    "code": "IDEMPOTENCY_RACE_TIMEOUT",
                },
            )

        # ── We hold the lock — process downstream ──
        _record_idem("miss", "enforcement" if is_enforcement else "grace")
        response = await call_next(request)

        # Capture response body bytes (consume the stream).
        # We need to re-emit it after caching, so we iterate body_iterator
        # and reassemble a new response.
        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk)
        body_bytes = b"".join(body_chunks)

        # Cache only success responses (2xx) — error responses are
        # transient and should be retryable with same key.
        if 200 <= response.status_code < 300:
            await _store_cached_response(
                digest=digest,
                key=key,
                organization_id=org_id,
                path=path,
                status_code=response.status_code,
                body_bytes=body_bytes,
                content_type=response.headers.get("content-type", "application/json"),
            )

        # Re-emit response with consumed body
        return Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type"),
        )
