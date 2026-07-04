"""
End-to-end test for Sentry integration (Phase 1 — Step A1).

Reusable utility — run after any of:
  - First-time Sentry setup (verify DSN works)
  - DSN rotation (verify new DSN routes events correctly)
  - Scrubber changes (verify PII is filtered before send)
  - SDK upgrade (regression check)

Usage:
    cd backend
    ./venv/bin/python -m scripts.test_sentry_e2e

What it does:
    1. Loads .env from backend root
    2. Calls init_sentry() — must return True (else SENTRY_DSN missing/invalid)
    3. Captures a fake exception that contains PII (email + password + Bearer)
    4. Flushes Sentry SDK queue (forces events to leave the process)
    5. Prints next-step instructions for manual dashboard verification

Verification (manual):
    Open https://sentry.io/issues/ → look for new event tagged with:
        - environment=development-test (or whatever ENVIRONMENT is set to)
        - release=test-sha
    In the event detail, verify:
        - exception message redacts the email and Bearer token
        - request data redacts the password field
        - HTTP headers (if shown) redact authorization
"""
import logging
import os
import sys
from pathlib import Path

# Resolve backend/ root from this file's location (scripts/ is a sibling of core/)
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_sentry_e2e")


def main() -> int:
    # 1. Load .env from backend root
    try:
        from dotenv import load_dotenv
        env_path = BACKEND_ROOT / ".env"
        if not env_path.exists():
            logger.error("backend/.env not found at %s", env_path)
            return 2
        load_dotenv(env_path, override=True)
        logger.info("Loaded env from %s", env_path)
    except ImportError:
        logger.error("python-dotenv not installed; activate venv first")
        return 2

    # 2. Init Sentry
    from core.observability import init_sentry
    initialized = init_sentry()
    if not initialized:
        logger.error(
            "Sentry init returned False. Possible causes:\n"
            "  - SENTRY_DSN not set in backend/.env\n"
            "  - SENTRY_DSN malformed\n"
            "  - sentry-sdk not installed in active venv (pip install 'sentry-sdk[fastapi]')\n"
        )
        return 1

    # 3. Capture fake exception with PII to verify scrubbing
    import sentry_sdk

    fake_email = "test-e2e-user@example.com"
    fake_password = "super_secret_pwd_12345"
    fake_bearer = "Bearer eyJhbGciOiJIUzI1NiJ9.faketoken.xyz"

    logger.info("Capturing test exception with PII payload (will be scrubbed before send)...")

    with sentry_sdk.push_scope() as scope:
        # Add request-like context with sensitive headers
        scope.set_context("request_data", {
            "email": fake_email,
            "password": fake_password,
            "username": "davide-e2e-test",  # NOT redacted (whitelisted)
        })
        scope.set_extra("auth_header", fake_bearer)
        scope.set_tag("test_run", "phase1-step-a1-e2e")

        try:
            raise RuntimeError(
                f"E2E test exception: login failed for {fake_email} "
                f"with token {fake_bearer}. Password was {fake_password}."
            )
        except RuntimeError as e:
            sentry_sdk.capture_exception(e)
            logger.info("Exception captured: %s", e)

    # 4. Flush — forces events to leave the process (default async)
    logger.info("Flushing Sentry SDK queue (timeout=5s)...")
    flushed = sentry_sdk.flush(timeout=5)
    if not flushed:
        logger.warning("Flush did not complete in 5s — event may still be sending in background")
    else:
        logger.info("Flush complete.")

    # 5. Print next steps
    print()
    print("=" * 70)
    print("✅ TEST EXCEPTION SENT TO SENTRY")
    print("=" * 70)
    print()
    print("Open your Sentry dashboard:")
    print("  https://sentry.io/issues/")
    print()
    print("Look for an event titled:")
    print('  RuntimeError: E2E test exception: login failed for [Filtered]...')
    print()
    print("In the event detail, VERIFY THESE 4 SCRUBBING POINTS:")
    print()
    print("  1. Exception message → email is [Filtered] (not test-e2e-user@example.com)")
    print("  2. Exception message → Bearer token is [Filtered]")
    print("  3. Exception message → password value is [Filtered]")
    print("  4. Context 'request_data' → password=[Filtered], email=[Filtered]")
    print("     username remains 'davide-e2e-test' (whitelisted)")
    print()
    print("Tags should include: test_run=phase1-step-a1-e2e")
    print("Environment tag should match ENVIRONMENT env var")
    print()
    print("If any of the 4 points leaks PII, the scrubber is broken — STOP and review.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
