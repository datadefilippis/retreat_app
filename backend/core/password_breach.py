"""
Track O Step 4.2 — Password breach check via HIBP k-anonymity API.

Have I Been Pwned (HIBP) Password range API:
    https://api.pwnedpasswords.com/range/{first_5_chars_of_SHA1}

Privacy-preserving k-anonymity protocol:
    1. Client hashes the password (SHA1) locally.
    2. Client sends ONLY first 5 hex chars (5/40 = ~0.5 bits of entropy).
    3. Server returns ALL suffixes (35 chars each) that match that prefix,
       plus a count of how many times each appeared in breaches.
    4. Client checks locally if its own suffix is in the response.

Result: HIBP never sees the full hash, never sees the plaintext password.
Even a malicious HIBP couldn't reconstruct the password from the prefix
(only ~1/16^5 = ~1M passwords share a 5-char prefix).

Threat model
============

CATCHES: users picking passwords that appear in known breach corpuses
         (RockYou, Collection #1, LinkedIn 2012, etc.). Even strong-looking
         passwords like "P@ssw0rd123!" are in every breach list.
DOES NOT CATCH: novel passwords (no breach exposure yet). For those we
         rely on validate_password_strength (length + complexity).

Fail-OPEN policy
================

If HIBP API is down / timeout / network error → allow signup to proceed.
Rationale: HIBP is a security ENHANCEMENT, not a critical gate. Blocking
signup when HIBP is unreachable would create a hard external dependency.
This matches OWASP recommendation for breach-check integration.

The fail-open is logged + recorded so operator can investigate persistent
HIBP outages, but never visible to user.

Threshold
=========

BREACH_THRESHOLD=5 → password rejected only if seen ≥5 times in breaches.
Rationale: HIBP includes some very small breaches; a count of 1-4 might
be a typo of a legitimate password. 5+ count = definitively spread in
known wordlists used by credential stuffing attackers.

Public API
==========

    is_password_breached(password) -> tuple[bool, int]
        Returns (breached, count). Fail-open on any error.

    validate_password_not_breached(password) -> None
        Raises ValueError if breached above threshold. No-op if not.
        Use in signup/reset flows AFTER validate_password_strength.
"""

import hashlib
import logging
import os
from typing import Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# Env-var feature flag — set to "false"/"0"/"no" to bypass HIBP check.
# Default: enabled (env var absent or "true"). Use case:
#   - Tests: set "false" in conftest to avoid network during unit tests
#     (without per-test mocking of every signup test)
#   - Ops emergency: set "false" temporary if HIBP introduces a
#     production incident (e.g. their API misbehaves in unforeseen way)
# is_password_breached() still works regardless (testable in isolation
# via mocked _get_hibp_session). Only the validate_password_not_breached
# wrapper respects this flag — so signup short-circuits cleanly.
_BREACH_CHECK_ENV_VAR = "PASSWORD_BREACH_CHECK_ENABLED"


def _breach_check_enabled() -> bool:
    """True if HIBP breach check should run for signups/resets."""
    val = os.environ.get(_BREACH_CHECK_ENV_VAR, "true").strip().lower()
    return val not in ("false", "0", "no", "off", "")


# ── Config ──────────────────────────────────────────────────────────────

HIBP_API_URL = "https://api.pwnedpasswords.com/range/"

# Minimum count to consider password "breached" — see module docstring.
BREACH_THRESHOLD = 5

# Total HTTP timeout (connect + read). Short cap because we fail-open
# anyway; longer wait just delays user-visible signup latency.
_HTTP_TIMEOUT_SECONDS = 3.0


# ── HTTP session pool ───────────────────────────────────────────────────
# Same pattern as services/email_service.py post-O1.3: persistent Session
# with connection pool + automatic retry on transient 5xx. Module-level
# singleton — initialized once per worker, thread-safe by design.

_hibp_session: requests.Session | None = None


def _build_hibp_session() -> requests.Session:
    """Build configured requests.Session for HIBP range API."""
    s = requests.Session()
    retry = Retry(
        total=2,                # 2 retries (3 attempts total) — keep low
        backoff_factor=0.3,     # 0.3s, 0.6s — total max ~0.9s overhead
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(
        pool_connections=4,
        pool_maxsize=8,
        max_retries=retry,
    )
    s.mount("https://", adapter)
    # User-Agent obbligatorio per HIBP API — rejection altrimenti.
    s.headers.update({
        "User-Agent": "AFianco-PasswordBreachCheck/1.0",
        # Add-Padding: instructs HIBP to pad response with random fake
        # entries (anti-traffic-analysis). Negligible overhead, big
        # privacy win.
        "Add-Padding": "true",
    })
    return s


def _get_hibp_session() -> requests.Session:
    """Lazy-init the module-level Session."""
    global _hibp_session
    if _hibp_session is None:
        _hibp_session = _build_hibp_session()
    return _hibp_session


# ── Core API ────────────────────────────────────────────────────────────


def _sha1_hex_upper(password: str) -> str:
    """Compute SHA1 hex of password, uppercased (HIBP returns uppercase).

    NB: usedforsecurity=False (Python 3.9+) declares esplicitamente che
    questo SHA1 NON e' usato per security context — HIBP range API
    protocol RICHIEDE SHA1 (e' parte della k-anonymity spec). Bandit
    B324 altrimenti flag l'uso come weak hash (correttamente per
    password hashing, FALSO POSITIVO per protocol-mandated digest).
    Il password NON viene mai hashato con SHA1 per storage — quello
    rimane bcrypt via passlib.
    """
    return hashlib.sha1(  # nosec B324 — HIBP protocol-mandated, not password storage
        password.encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest().upper()


def is_password_breached(password: str) -> Tuple[bool, int]:
    """Check if password appears in HIBP breach corpus via k-anonymity.

    Args:
        password: plaintext password to check. Hashed locally; NEVER sent
                  in plaintext or full-hash form to HIBP.

    Returns:
        (breached, count) tuple:
          breached: True if count >= BREACH_THRESHOLD (caller should block).
          count:    number of times the password appeared in breaches
                    (0 if not found or on API error).

    Fail-open contract:
        Any network error, timeout, malformed response, or unexpected
        HTTP status returns (False, 0) — caller allows the operation.
        Logged at WARNING level so operator can monitor HIBP availability.
    """
    if not password or not isinstance(password, str):
        # Defensive: empty/non-string → caller should have caught at
        # validation. We treat as "not breached" rather than raise.
        return (False, 0)

    sha1 = _sha1_hex_upper(password)
    prefix = sha1[:5]
    suffix = sha1[5:]

    try:
        session = _get_hibp_session()
        resp = session.get(
            HIBP_API_URL + prefix,
            timeout=_HTTP_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            logger.warning(
                "password_breach: HIBP returned status=%s (fail-open)",
                resp.status_code,
            )
            return (False, 0)
        # Response body: text/plain, lines "<suffix>:<count>" CRLF-separated.
        # Padded responses include count=0 entries — ignore those.
        for line in resp.text.splitlines():
            if ":" not in line:
                continue
            line_suffix, _, line_count = line.partition(":")
            if line_suffix.strip().upper() != suffix:
                continue
            try:
                count = int(line_count.strip())
            except ValueError:
                continue
            # Padded random suffix entries have count=0 → skip.
            if count <= 0:
                continue
            breached = count >= BREACH_THRESHOLD
            return (breached, count)
        # Suffix not found in response → password not in HIBP corpus.
        return (False, 0)
    except requests.exceptions.RequestException as e:
        # Network error / timeout / DNS / etc. → fail-open.
        logger.warning(
            "password_breach: HIBP request failed (fail-open): %s: %s",
            type(e).__name__, str(e)[:200],
        )
        return (False, 0)
    except Exception as e:  # pragma: no cover — defensive
        logger.warning(
            "password_breach: unexpected error (fail-open): %s: %s",
            type(e).__name__, str(e)[:200],
        )
        return (False, 0)


def validate_password_not_breached(password: str) -> None:
    """Raise ValueError if password appears in HIBP breach corpus.

    Use AFTER validate_password_strength() in signup / password-reset
    flows. Fail-open: if HIBP is unreachable, no exception raised.

    Feature flag: respects PASSWORD_BREACH_CHECK_ENABLED env var. If
    set to "false"/"0"/"no", function is a no-op (tests + emergency
    bypass). Default: enabled.

    Raises:
        ValueError: with user-friendly Italian message if password is
                    in known breaches (count >= BREACH_THRESHOLD).
    """
    if not _breach_check_enabled():
        return
    breached, count = is_password_breached(password)
    if breached:
        # Don't leak the actual count to the user (slight info-leak — an
        # attacker could ALSO check HIBP to see if THEIR password is
        # weaker/stronger than the victim's). Just say "found".
        raise ValueError(
            "Questa password è stata trovata in noti data breach pubblici. "
            "Per sicurezza, scegli una password diversa che non hai mai "
            "usato su altri siti."
        )


__all__ = [
    "BREACH_THRESHOLD",
    "is_password_breached",
    "validate_password_not_breached",
]
