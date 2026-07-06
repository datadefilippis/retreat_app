"""
Healthcheck endpoints (Phase 1 — Step A4).

Two-tier health probe pattern (k8s-style), suitable for load balancers,
external uptime monitors (BetterStack), and Kubernetes liveness/readiness.

    GET /api/health/live
        → 200 always (process is alive). Sub-millisecond, no dependencies.

    GET /api/health/ready
        → 200 if app can serve traffic (MongoDB reachable + Stripe/Brevo
          configured). 503 with detail if a critical dependency is down.

Severity model:
    - mongodb  → CRITICAL. KO → /ready returns 503 (app cannot serve).
    - stripe   → WARNING.  Misconfig surfaced but app degrades (no checkout).
    - brevo    → WARNING.  Misconfig surfaced but app degrades (no email).

Caching:
    - /ready result cached for READY_CACHE_TTL_SECONDS (10s) to avoid hammering
      the DB when load balancers probe at 1Hz. Stale window is acceptable
      because outage detection still happens within ~10s.

Endpoints are NOT authenticated — required by external probes that have no
credentials. To prevent abuse, slowapi rate limit applies (60/min/IP).
"""
import asyncio
import logging
import os
import time
from typing import Any, Dict

from fastapi import APIRouter, Response, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])

# Process start timestamp — used for uptime_seconds.
_START_TIME = time.time()

# Cache for /ready result. Single-process per worker is fine: gunicorn workers
# each have their own cache, but a load balancer probe lands on one worker per
# request, so the user sees consistent reads with low DB load.
_ready_cache: Dict[str, Any] = {"timestamp": 0.0, "result": None}
READY_CACHE_TTL_SECONDS = 10
CHECK_TIMEOUT_SECONDS = 2.0

APP_VERSION = "2.0.0"


# ── Liveness ──────────────────────────────────────────────────────────────────

@router.get("/live")
async def liveness() -> Dict[str, Any]:
    """
    Liveness probe. Returns 200 with uptime info.

    Use case: container orchestrator checks "is the process alive at all?".
    If this fails, restart the container.

    Intentionally has no DB / external dependency: a healthy process should
    answer this even if MongoDB is down.
    """
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - _START_TIME),
        "version": APP_VERSION,
    }


# ── Readiness ─────────────────────────────────────────────────────────────────

async def _check_mongodb() -> Dict[str, Any]:
    """Ping MongoDB. CRITICAL — failure = 503."""
    try:
        from database import client
        await asyncio.wait_for(
            client.admin.command("ping"),
            timeout=CHECK_TIMEOUT_SECONDS,
        )
        return {"status": "ok"}
    except asyncio.TimeoutError:
        return {"status": "fail", "error": f"timeout after {CHECK_TIMEOUT_SECONDS}s"}
    except Exception as e:
        return {"status": "fail", "error": type(e).__name__}


async def _check_stripe() -> Dict[str, Any]:
    """
    Verify Stripe API key is configured. WARNING — does not flip /ready to 503.

    We deliberately do NOT call Stripe.Account.retrieve() here: that would add
    ~200ms per probe and create an external dependency on Stripe's uptime for
    OUR readiness signal (cyclic dependency). Configuration check is enough.
    """
    if os.getenv("STRIPE_SECRET_KEY", "").strip():
        return {"status": "ok"}
    return {"status": "warning", "error": "STRIPE_SECRET_KEY not configured"}


async def _check_brevo() -> Dict[str, Any]:
    """Verify Brevo (transactional email) API key is configured. WARNING."""
    if os.getenv("BREVO_API_KEY", "").strip():
        return {"status": "ok"}
    return {"status": "warning", "error": "BREVO_API_KEY not configured"}


async def _compute_readiness() -> Dict[str, Any]:
    """Run all checks in parallel, aggregate result."""
    checks = await asyncio.gather(
        _check_mongodb(),
        _check_stripe(),
        _check_brevo(),
        return_exceptions=True,
    )
    mongodb_check, stripe_check, brevo_check = checks

    # Defensive: if any check raised an unexpected exception, surface it.
    def _normalize(c):
        if isinstance(c, Exception):
            return {"status": "fail", "error": type(c).__name__}
        return c

    mongodb_check = _normalize(mongodb_check)
    stripe_check = _normalize(stripe_check)
    brevo_check = _normalize(brevo_check)

    # Only mongodb being "fail" flips overall to 503 (degraded).
    is_ready = mongodb_check.get("status") == "ok"

    return {
        "status": "ok" if is_ready else "degraded",
        "ready": is_ready,
        "checks": {
            "mongodb": mongodb_check,
            "stripe": stripe_check,
            "brevo": brevo_check,
        },
        "uptime_seconds": int(time.time() - _START_TIME),
        "version": APP_VERSION,
    }


@router.get("/ready")
async def readiness(response: Response) -> Dict[str, Any]:
    """
    Readiness probe with TTL cache to prevent DB hammering.

    Returns 200 if MongoDB is reachable, 503 otherwise.
    """
    now = time.time()
    cached = _ready_cache["result"]
    cache_age = now - _ready_cache["timestamp"]

    if cached is not None and cache_age < READY_CACHE_TTL_SECONDS:
        # Reuse cached result — set status code from the cached payload.
        if not cached.get("ready", False):
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return cached

    # Recompute
    result = await _compute_readiness()
    _ready_cache["timestamp"] = now
    _ready_cache["result"] = result

    if not result["ready"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        # Log only on transition from ok → degraded (don't spam every 10s)
        prev_ready = cached.get("ready", True) if cached else True
        if prev_ready:
            logger.warning(
                "Readiness probe degraded: %s",
                {k: v.get("status") for k, v in result["checks"].items()},
            )
    else:
        # Log recovery transition
        prev_ready = cached.get("ready", False) if cached else False
        if not prev_ready and cached is not None:
            logger.info("Readiness probe recovered: all checks ok")

    return result


# ── AI health (Wave 5.4) ────────────────────────────────────────────────────
