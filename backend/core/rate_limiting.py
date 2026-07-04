"""
backend/core/rate_limiting.py
==============================
Onda 27.2 — Real client IP resolution for slowapi rate limiter.

Problem
-------
Behind a reverse proxy (nginx → backend container in our Docker stack),
`request.client.host` is the proxy's IP (`172.18.0.5` = nginx in the
ms-internal Docker network), not the real client. Using slowapi's
default `get_remote_address` as `key_func` makes the per-IP rate
limit effectively GLOBAL for the whole app: 5 failed signups from
ANY single user trip the `5/15min` limit for ALL users.

slowapi ships a `get_ipaddr` helper that does try to read
`X-Forwarded-For`, but it looks for the header name `X_FORWARDED_FOR`
(underscore) which Starlette/FastAPI does not normalize that way —
Starlette stores headers lowercase with dashes (`x-forwarded-for`).
So `get_ipaddr` silently falls back to `request.client.host` too.

Solution
--------
This module provides `get_real_ip(request)` — the canonical key_func
to pass to `Limiter(key_func=...)`. It:

  1. Reads the `X-Forwarded-For` request header (case-insensitive).
  2. Splits on `,` and takes the FIRST entry (= original client per
     RFC 7239 / X-Forwarded-For convention: client, proxy1, proxy2).
  3. Strips whitespace.
  4. Falls back to `request.client.host` if the header is absent or
     empty (= local request, no proxy in front).
  5. Final fallback `127.0.0.1` if everything is missing (test env).

Trust assumption
----------------
This module trusts whatever value comes in `X-Forwarded-For`. That's
SAFE in our deployment because:

  * The only public ingress is nginx (deploy/nginx/nginx.conf), which
    explicitly sets `proxy_set_header X-Forwarded-For
    $proxy_add_x_forwarded_for;` — so the value reaching the backend
    is always nginx-controlled, not user-spoofed.
  * The backend container is NOT exposed externally (port 8000 is on
    the internal Docker network only).

If we ever expose the backend directly to the internet (without a
trusted proxy in front), the trust model breaks and this module needs
to be revisited (e.g. configure a TRUSTED_PROXIES list and only honor
X-Forwarded-For when request.client.host ∈ that list).

Usage
-----
    from core.rate_limiting import get_real_ip
    from slowapi import Limiter

    limiter = Limiter(key_func=get_real_ip, default_limits=["60/minute"])

Drop-in replacement for `slowapi.util.get_remote_address`.
"""

from typing import Optional

from starlette.requests import Request


_FALLBACK_IP = "127.0.0.1"


def _extract_forwarded_for(header_value: Optional[str]) -> Optional[str]:
    """Parse an X-Forwarded-For header value into the leftmost (original) IP.

    Examples:
      "203.0.113.7"                       -> "203.0.113.7"
      "203.0.113.7, 70.41.3.18"           -> "203.0.113.7"
      "203.0.113.7,70.41.3.18, 150.0.0.1" -> "203.0.113.7"
      ""                                  -> None
      None                                -> None
      ", , 1.2.3.4"                       -> None  (first non-empty wins)

    Whitespace around each entry is stripped. The leftmost non-empty
    entry is returned, matching the convention that proxies APPEND
    their own IP, so the original client is at the start of the chain.
    """
    if not header_value:
        return None
    for candidate in header_value.split(","):
        candidate = candidate.strip()
        if candidate:
            return candidate
    return None


def get_real_ip(request: Request) -> str:
    """slowapi key_func that returns the real client IP behind a proxy.

    Reads `X-Forwarded-For` (case-insensitive) and returns the leftmost
    IP. Falls back to `request.client.host`, then `127.0.0.1`.

    Args:
        request: Starlette/FastAPI Request instance (slowapi passes
                 this when calling key_func).

    Returns:
        A non-empty string suitable as a rate-limit bucket key.
        Never returns None — callers can rely on it.
    """
    # Starlette normalizes header names to lowercase. `request.headers`
    # is a multi-dict-like object that lookups case-insensitively, so
    # both "X-Forwarded-For" and "x-forwarded-for" work.
    xff = request.headers.get("x-forwarded-for")
    real_ip = _extract_forwarded_for(xff)
    if real_ip:
        return real_ip

    # No XFF header (or empty) — fall back to direct client.
    if request.client and request.client.host:
        return request.client.host

    return _FALLBACK_IP


# ─────────────────────────────────────────────────────────────────────────────
# Track E Step 1.4 — Per-merchant rate limit isolation
# ─────────────────────────────────────────────────────────────────────────────
#
# Pre-E1.4 i rate limit erano per-IP globali (es. 60/min su /products).
# Problema: merchant A con 1000 customer su same NAT (corporate proxy)
# satura il bucket → merchant B (1 customer su stessa NAT) starva.
#
# E1.4 introduce composite key per endpoints embed:
#   bucket = f"{ip}|s={slug}"
#
# Effetto:
#   - Stesso IP, slug diversi → bucket separati (merchant isolation)
#   - Stesso IP, slug stesso → bucket condiviso (legacy comportamento)
#   - Slug assente (es. POST /checkout/start con slug nel body) →
#     fallback a IP only (backward compat).
#
# Slug extraction:
#   1. path_params (es. /init/{slug}) — primario per GET /init, /categories
#   2. query_params (es. /cart/{cart_id}?slug=X) — primario per cart ops
#   3. Fallback: solo IP (es. POST /checkout/start con slug nel body —
#      key_func e' sync, non puo' read body async)
#
# Multi-tenant safety:
#   Composite key NON e' security boundary — e' rate limit isolation.
#   La security multi-tenant resta sui DB query (_resolve_org + org_id
#   filter su Mongo). Sentinel pin entrambi.
#
# Attack surface considerations:
#   - Attaccante rotate slug → bucket diversi per slug → effetto:
#     attaccante PUO' fare N×limit req. Mitigation: nginx layer ha
#     suo per-IP cap (limit_req_zone signup deployato in O1.6). E
#     slug inesistenti → 404 da _resolve_org (Mongo lookup, throttled
#     by connection pool + CPU naturally).
#   - Composite key memory bound: ~100B per bucket × 200 merchant ×
#     100 IP = 2MB → OK in-memory (no Redis needed).
#
# Backward compat: get_real_ip e' INVARIATO. Endpoint NON-embed
# continuano a usare il limiter legacy con get_real_ip (per-IP).


def get_real_ip_with_slug(request: Request) -> str:
    """slowapi key_func composito per per-merchant rate limit isolation.

    Returns:
        - "{ip}|s={slug}" se slug e' presente in path o query params
        - "{ip}" se slug assente (fallback backward-compat)

    Slug extraction order:
      1. request.path_params["slug"] — es. /init/{slug} URL pattern
      2. request.query_params.get("slug") — es. ?slug=X
      3. None → fallback a IP solo

    Defensive: max slug length capped a 64 char (anti-DOS via giant
    slug values inflating bucket key memory). Slug reale validated
    upstream da _resolve_org (3-50 char limit, alphanumeric+hyphen).
    """
    ip = get_real_ip(request)

    slug: Optional[str] = None
    # Path params: most common for GET /init/{slug}, /categories/{slug}
    try:
        path_slug = request.path_params.get("slug") if hasattr(request, "path_params") else None
        if isinstance(path_slug, str) and path_slug.strip():
            slug = path_slug.strip()
    except Exception:
        # Defensive: malformed request, fallback
        pass

    if not slug:
        # Query params: cart ops use /cart/{id}?slug=X
        try:
            query_slug = request.query_params.get("slug") if hasattr(request, "query_params") else None
            if isinstance(query_slug, str) and query_slug.strip():
                slug = query_slug.strip()
        except Exception:
            pass

    if not slug:
        # F1 — endpoint newsletter usano {form_id} come identità embed
        # (uuid globalmente unico) al posto dello slug store: isola comunque
        # il bucket per-risorsa (per-form), non per-IP globale.
        try:
            form_id = request.path_params.get("form_id") if hasattr(request, "path_params") else None
            if isinstance(form_id, str) and form_id.strip():
                slug = form_id.strip()
        except Exception:
            pass

    if not slug:
        return ip

    # Defensive cap: slug max 64 chars (real slugs validated 3-50
    # alphanumeric+hyphen upstream). Cap previene DOS via giant slug
    # values che inflano memory bucket key.
    safe_slug = slug[:64]
    return f"{ip}|s={safe_slug}"


__all__ = [
    "get_real_ip",
    "get_real_ip_with_slug",
    "check_email_rate",
    "reset_email_rate_state",
]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 Step D2 — per-recipient (email) rate limit, cross-IP.
# ─────────────────────────────────────────────────────────────────────────────
# slowapi's per-IP limiting alone is insufficient against amplification: an
# attacker with a botnet (N source IPs) can multiply the effective rate by N
# while each individual IP stays under the per-IP cap. We add a complementary
# per-email rate limit that fires REGARDLESS of source IP, capping how many
# password-reset / verify-email emails we are willing to send to ONE recipient
# in a sliding 1-hour window.
#
# Implementation choice: in-memory sliding window per worker process.
# - No Redis dependency (we don't run Redis in our stack today).
# - Each gunicorn worker has its own bucket → effective limit per worker is
#   independent. With 1-2 workers this is acceptable. If we scale workers
#   later, switch to a shared store (Redis) — the public API stays the same.
# - Memory bound: each entry is "email:action" → list of float timestamps.
#   GC runs lazily on each call: stale entries removed.
#
# Public API:
#     check_email_rate(email, action, max_per_hour) -> bool
#     reset_email_rate_state()  # for tests only
#
# Returns True if the request is allowed (and registers it),
# False if the cap is hit (caller should raise 429).
import time
import threading
from collections import defaultdict
from typing import Dict, List

_WINDOW_SECONDS = 3600  # 1 hour
_email_buckets: Dict[str, List[float]] = defaultdict(list)
_email_lock = threading.Lock()


def _bucket_key(email: str, action: str) -> str:
    """
    Compose a bucket key from email + action so that, for example,
    forgot-password and resend-verification have independent counters.
    Email is lowercased to avoid trivial bypass via case variation.
    """
    return f"{(email or '').strip().lower()}::{action}"


def check_email_rate(email: str, action: str, max_per_hour: int) -> bool:
    """
    Sliding-window 1-hour rate limit per (email, action).

    Args:
        email:        recipient email address (case-insensitive).
        action:       short tag identifying the email type, e.g.
                      "forgot_password", "resend_verification". Different
                      actions have independent buckets so a user receiving
                      a verify email can still request a password reset.
        max_per_hour: maximum allowed calls in the rolling 1-hour window.

    Returns:
        True  → request allowed, timestamp recorded.
        False → cap hit, caller should respond with 429.

    Empty / missing email is permissive (returns True): the upstream auth
    handler always treats unknown emails as 200 anyway (anti-enumeration),
    and rate-limiting on empty string would create a giant shared bucket.
    """
    if not email or not email.strip():
        return True

    key = _bucket_key(email, action)
    now = time.time()
    cutoff = now - _WINDOW_SECONDS

    with _email_lock:
        bucket = _email_buckets[key]
        # Drop expired timestamps in-place.
        bucket[:] = [t for t in bucket if t > cutoff]
        if len(bucket) >= max_per_hour:
            return False
        bucket.append(now)
        return True


def reset_email_rate_state() -> None:
    """Clear all per-email buckets. For unit tests only."""
    with _email_lock:
        _email_buckets.clear()
