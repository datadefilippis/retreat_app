"""
backend/core/lockout_helpers.py
================================
Onda 30 — DRY pure helpers for the per-account anti-bruteforce lockout.

Originally introduced in Onda 29 inside services/customer_auth_service.py
as private helpers. Extracted to this module in Onda 30 so that the
admin/owner login path (services/auth_service.py) can reuse the exact
same math + parsing logic without duplication.

These helpers are PURE (no DB access, no side effects). They consume:
  · the lockout config constants from core/security_config.py
  · a generic "account dict" that has the four anti-bruteforce fields
    (works for both User and CustomerAccount documents — the two
    schemas converged on the same field names by design).

The DB-write side of the lockout (the $set / $inc that records the new
state, plus the email alert send) is intentionally NOT in here. It
stays in each service module because it depends on the right
repository / collection name (users_collection vs
customer_accounts_collection) and on the right forgot-password URL
to embed in the alert email.

Usage
-----
    from core.lockout_helpers import (
        compute_lockout_duration_minutes,
        is_account_locked,
    )

    # Pre-check before bcrypt
    if is_account_locked(user_doc, utc_now()):
        raise ValueError("ACCOUNT_LOCKED:...")

    # On threshold reached
    duration_min = compute_lockout_duration_minutes(prior_lockouts_today)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from core.security_config import (
    LOCKOUT_BASE_DURATION_MIN,
    LOCKOUT_BACKOFF_FACTOR,
    LOCKOUT_MAX_DURATION_MIN,
)

logger = logging.getLogger(__name__)


def compute_lockout_duration_minutes(prior_lockouts_today: int) -> int:
    """Exponential backoff capped at LOCKOUT_MAX_DURATION_MIN.

    With base=15, factor=2, max=1440 the sequence is:
      0 prior → 15 min       (1st lockout in 24h)
      1 prior → 30 min       (2nd)
      2 prior → 60 min       (3rd)
      3 prior → 120 min      (4th)
      ...
      6 prior → 960 min      (7th)
      7+ prior → 1440 min    (capped at 24h)

    Pure function: no I/O, no side effects, deterministic.
    """
    raw = LOCKOUT_BASE_DURATION_MIN * (LOCKOUT_BACKOFF_FACTOR ** prior_lockouts_today)
    return min(raw, LOCKOUT_MAX_DURATION_MIN)


def is_account_locked(account: dict, now_dt: datetime) -> Optional[str]:
    """Return the locked_until ISO string if `account` is currently
    locked (= locked_until is in the future), else None.

    Defensive parsing: malformed or naive timestamps fall back to
    "not locked" rather than failing the login flow on a storage
    glitch. A logger.warning is emitted in that case so operators can
    catch the corruption upstream.

    `account` is a dict with at least an `id` key (for logging) and
    optionally a `locked_until` ISO string. Works equally for User
    and CustomerAccount documents.
    """
    locked_until_iso = account.get("locked_until")
    if not locked_until_iso:
        return None
    try:
        dt = datetime.fromisoformat(locked_until_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt > now_dt:
            return locked_until_iso
    except (ValueError, TypeError) as e:
        logger.warning(
            "lockout_helpers.is_account_locked: malformed locked_until=%r "
            "on account=%s: %s",
            locked_until_iso, account.get("id"), e,
        )
    return None


__all__ = [
    "compute_lockout_duration_minutes",
    "is_account_locked",
]
