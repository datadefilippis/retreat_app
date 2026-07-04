"""
backend/core/security_config.py
================================
Onda 29 — Centralized security knobs.

Single source of truth for tunable thresholds used by the
authentication / anti-bruteforce machinery. Kept as plain module-level
constants (not env vars) for these reasons:

  · Values are policy decisions, not deployment-specific. The same
    thresholds are correct in dev, staging, and prod.
  · Code reviews surface threshold changes naturally (the diff shows
    the new value next to the old one).
  · No risk of typo'd env var silently falling back to a default that
    differs between environments.

If we ever need per-environment overrides (e.g. lower thresholds in
staging for testing), we'll add a Settings model that reads from env
and falls back to these defaults — but only when the need is real.

Currently tuned for AFianco's risk profile (B2B SaaS, small tenant
count, low signal-to-noise ratio for brute-force). Adjust mindfully:
  · Lower threshold → harder for attacker, but more accidental
    self-DOS by users who mistype passwords a few times.
  · Higher base duration → harder for attacker, more friction for
    user recovery (forgot-password remains available as escape hatch).
  · Higher max → unbounded growth of pain for persistent attackers,
    but legitimate user can theoretically be locked out for >24h if
    they keep re-failing in the same UTC day.

History
-------
v1 (Onda 29 Step 2) — initial values:
  THRESHOLD = 5, BASE_MIN = 15, FACTOR = 2, MAX_MIN = 1440 (24h)
  Backoff sequence at 1-2-3-4-5 lockouts in 24h:
    15 min → 30 min → 1 h → 2 h → 4 h → ... → 24 h cap
"""


# ── Customer account lockout (Onda 29) ──────────────────────────────────────

#: Number of consecutive failed login attempts that triggers a lockout.
#: Counter is reset to 0 on a successful login OR when a lockout fires
#: (the lockout itself is the "punishment" — once it expires, the
#: counter restarts from 0 toward the next threshold).
LOCKOUT_THRESHOLD = 5

#: Minutes to lock the account on the FIRST lockout in the rolling 24h
#: window. Subsequent lockouts in the same window grow exponentially
#: per LOCKOUT_BACKOFF_FACTOR, capped at LOCKOUT_MAX_DURATION_MIN.
LOCKOUT_BASE_DURATION_MIN = 15

#: Exponential backoff multiplier. With factor=2 and base=15min:
#:   1st lockout in 24h: 15 min
#:   2nd: 30 min
#:   3rd: 1 h
#:   4th: 2 h
#:   5th: 4 h
#:   6th: 8 h
#:   7th: 16 h
#:   8th+: 24 h (capped)
LOCKOUT_BACKOFF_FACTOR = 2

#: Hard cap on lockout duration. Prevents pathological multi-day locks.
#: 24h means a determined attacker can resume after a day, but at that
#: point they'll have generated enough audit trail to be caught.
LOCKOUT_MAX_DURATION_MIN = 60 * 24

#: Field name used in the user-facing error response when a login
#: attempt is rejected because the account is locked. The frontend
#: matches on this string to render the live countdown UI.
LOCKOUT_ERROR_CODE = "ACCOUNT_LOCKED"


__all__ = [
    "LOCKOUT_THRESHOLD",
    "LOCKOUT_BASE_DURATION_MIN",
    "LOCKOUT_BACKOFF_FACTOR",
    "LOCKOUT_MAX_DURATION_MIN",
    "LOCKOUT_ERROR_CODE",
]
