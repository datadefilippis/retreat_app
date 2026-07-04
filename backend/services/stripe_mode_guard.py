"""
Stripe mode guard — prevent test-mode Stripe accounts from being used in production.

Rationale:
  The most subtle class of production incident is a test-mode account silently
  accepted by the platform. Customers "pay" with test cards, Stripe accepts
  the charges, but the funds never hit the merchant's real bank account —
  the issue surfaces only at payout time, potentially weeks later.

  This module centralizes the two signals needed to catch it:
    1. Platform mode: derived from the STRIPE_SECRET_KEY prefix
       ("sk_test_..." → test, "sk_live_..." → live, anything else → unknown)
    2. Account mode: from Stripe Account.livemode attribute

  Both Express and Standard onboarding paths call assert_account_mode_matches()
  after retrieving the connected account. In production, a mismatch is fatal
  (we raise ValueError); outside production we log a warning so devs can still
  test freely.

  An explicit override ALLOW_TEST_STRIPE_IN_PRODUCTION=1 exists strictly for
  the narrow case of running a production deploy against a test Stripe key
  (e.g. staging environment that mirrors production config). This must never
  be set on a real production deployment.
"""

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def platform_stripe_mode() -> str:
    """Return 'test', 'live', or 'unknown' based on the configured secret key prefix."""
    key = os.environ.get("STRIPE_SECRET_KEY", "") or ""
    if key.startswith("sk_test_") or key.startswith("rk_test_"):
        return "test"
    if key.startswith("sk_live_") or key.startswith("rk_live_"):
        return "live"
    return "unknown"


def is_production() -> bool:
    """True when the backend is running in a production environment."""
    return os.environ.get("ENVIRONMENT", "development") == "production"


def allow_test_override() -> bool:
    """Explicit opt-in for running a production deploy against a test key.

    Must never be set for a real production tenant — exists only to allow
    staging environments that mirror production config to use test keys.
    """
    return os.environ.get("ALLOW_TEST_STRIPE_IN_PRODUCTION", "") in ("1", "true", "yes")


def check_platform_mode_at_startup() -> Optional[str]:
    """Log-level-appropriate warning if platform mode / environment are inconsistent.

    Returns a machine-readable reason code when an issue is detected (for tests
    and future health-check surfacing), or None when everything is consistent.

    Does NOT abort startup — the backend must keep serving non-payment traffic
    even if Stripe is misconfigured. Onboarding / checkout entrypoints enforce
    the gate at their own boundary.
    """
    mode = platform_stripe_mode()

    if not is_production():
        return None  # dev/test: anything goes

    if mode == "test":
        if allow_test_override():
            logger.warning(
                "stripe_mode_guard: platform running in production with TEST Stripe key. "
                "ALLOW_TEST_STRIPE_IN_PRODUCTION is set — accepting test key. "
                "This must ONLY be used on staging / preview environments."
            )
            return "test_key_in_prod_with_override"
        logger.critical(
            "stripe_mode_guard: ENVIRONMENT=production but STRIPE_SECRET_KEY is a TEST key. "
            "Commerce and billing will use test-mode Stripe — no real funds will move. "
            "Set a live sk_live_ key, or set ALLOW_TEST_STRIPE_IN_PRODUCTION=1 if this is intentional."
        )
        return "test_key_in_prod"

    if mode == "unknown":
        logger.warning(
            "stripe_mode_guard: STRIPE_SECRET_KEY format not recognized "
            "(expected sk_test_ or sk_live_ prefix). Payments may fail."
        )
        return "unknown_key_format"

    return None  # production + live key → consistent


class StripeModeMismatch(ValueError):
    """Raised when a connected account's mode does not match the platform's mode."""

    def __init__(self, account_id: str, account_mode: str, platform_mode: str):
        self.account_id = account_id
        self.account_mode = account_mode
        self.platform_mode = platform_mode
        super().__init__(
            f"Stripe mode mismatch: platform={platform_mode}, "
            f"account={account_id} is {account_mode}. "
            "Cannot process payments across test/live boundary."
        )


def assert_account_mode_matches(account: Any, account_id: str) -> None:
    """Raise StripeModeMismatch if the account's livemode disagrees with the platform's mode.

    Rules:
      - In production WITHOUT override: hard reject mismatch. No exceptions.
      - In production WITH override: warn but allow (staging scenario).
      - In non-production: warn only (dev may use either mode).
      - If platform mode is 'unknown': warn but allow — we cannot verify.

    `account` accepts either a Stripe Account object or a plain dict (post
    _normalize_stripe_object), so it works at both webhook and pull paths.
    """
    # Extract livemode — tolerate both StripeObject and dict
    livemode = None
    if isinstance(account, dict):
        livemode = account.get("livemode")
    else:
        livemode = getattr(account, "livemode", None)
        if livemode is None and hasattr(account, "get"):
            try:
                livemode = account.get("livemode")
            except Exception:
                pass

    if livemode is None:
        # Account payload does not include livemode — do not block, but log.
        logger.warning(
            "stripe_mode_guard: account %s has no livemode field — cannot verify match",
            account_id,
        )
        return

    account_mode = "live" if livemode else "test"
    platform_mode = platform_stripe_mode()

    if platform_mode == "unknown":
        logger.warning(
            "stripe_mode_guard: platform mode unknown, skipping match check for account %s",
            account_id,
        )
        return

    if account_mode == platform_mode:
        return  # all good

    # Mismatch
    if is_production() and not allow_test_override():
        logger.error(
            "stripe_mode_guard: REJECTING account %s — platform=%s, account=%s",
            account_id, platform_mode, account_mode,
        )
        raise StripeModeMismatch(account_id, account_mode, platform_mode)

    logger.warning(
        "stripe_mode_guard: account %s mode=%s does not match platform=%s "
        "(allowed outside production or with override)",
        account_id, account_mode, platform_mode,
    )
