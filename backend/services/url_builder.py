"""
url_builder — single source of truth for absolute URLs that the backend
needs to embed in outbound channels (transactional emails, push payloads,
SMS, …).

Two distinct base URLs:

  - PUBLIC_APP_URL — customer-facing post-purchase landings:
      /t/<token>           ticket + QR
      /b/<token>           service booking
      /rsv/<token>         rental reservation
      /d/<token>           digital download
      /account/courses/    enrolled course
    These links are clicked by buyers, often unauthenticated, on devices
    that won't ever know about an internal hostname.

  - APP_URL — admin / authenticated flows:
      /verify-email            admin signup verification
      /reset-password          admin password reset
      /account/orders/<id>     customer area (post-login)
      /account/verify-email    customer signup verification (different
                               path from admin's; same domain)
    Historically these used the same domain as the public side, but we
    keep two settings so future changes (e.g. a separate admin host)
    don't ripple through every email template.

Why a dedicated module
----------------------
Before this helper existed the pattern
    base = os.environ.get("PUBLIC_APP_URL", "http://localhost:3000")
    url  = f"{base}/t/{token}"
was duplicated in 8 places across email_service / order_email_service /
event_email_service / public.py. When PUBLIC_APP_URL was missing from
docker-compose.prod.yml, every one of those sites silently fell back to
localhost — that's the bug that shipped tickets pointing at localhost.

By centralising:
  * env vars are read once at import time, with a single warning when
    they fall back to a localhost default. A misconfigured prod surfaces
    in the startup log instead of in a customer's inbox.
  * adding a new email template requires one call site, not three lines
    of boilerplate that are easy to drift.
  * future provider tweaks (URL signing, domain switch, A/B'd domains
    by region) live in one file.

The module is import-time pure: it does not touch the network, the DB,
or anything that would slow up tests / cold starts.
"""

from __future__ import annotations

import logging
import os
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)


# ── Defaults ────────────────────────────────────────────────────────────────
#
# Frontend (CRA) dev server runs on :3000 by default. Backend dev server
# runs on :8000. So a developer running both locally points the email
# links at :3000 — that's the page the recipient should land on.
#
# Picking distinct defaults for the two env vars would be misleading: in
# practice both the customer post-purchase landings AND the admin pages
# are served by the same React app on the same host (different routes).
# The two env vars exist so that infrastructure can split them later
# without a code migration; the code itself uses the same default.

_DEFAULT_LOCAL_URL = "http://localhost:3000"


def _read_url(env_name: str, default: str) -> tuple[str, bool]:
    """Read a URL env var, normalise (strip trailing slash), validate.

    Returns (resolved_url, is_default_fallback). The bool tells the caller
    whether we fell back to the default — used at module import time to
    surface a single, prominent warning when production is misconfigured.

    A value that doesn't parse as http/https is treated as missing: we
    refuse to embed `ftp://` or empty strings in customer emails, and
    fall back to the default rather than emit a malformed URL.
    """
    raw = os.environ.get(env_name)
    if not raw:
        return default, True

    cleaned = raw.strip().rstrip("/")
    parsed = urlsplit(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        logger.warning(
            "url_builder: %s=%r is not a valid http(s) URL; falling back to %s",
            env_name, raw, default,
        )
        return default, True

    return cleaned, False


PUBLIC_APP_URL, _public_is_default = _read_url("PUBLIC_APP_URL", _DEFAULT_LOCAL_URL)
APP_URL, _app_is_default = _read_url("APP_URL", _DEFAULT_LOCAL_URL)


# ── Startup notice ──────────────────────────────────────────────────────────
#
# Loud about misconfiguration so a prod boot with missing env shows up
# in container logs at minute 0, not via a customer ticket later.

if _public_is_default and _app_is_default:
    logger.warning(
        "url_builder: BOTH PUBLIC_APP_URL and APP_URL fell back to %s — "
        "outbound email links will point at localhost. This is fine for "
        "local dev; if you see this in production, fix the env config.",
        _DEFAULT_LOCAL_URL,
    )
elif _public_is_default:
    logger.warning(
        "url_builder: PUBLIC_APP_URL fell back to %s (APP_URL=%s). "
        "Customer ticket / booking / download links will point at "
        "localhost — set PUBLIC_APP_URL in the environment.",
        _DEFAULT_LOCAL_URL, APP_URL,
    )
elif _app_is_default:
    logger.warning(
        "url_builder: APP_URL fell back to %s (PUBLIC_APP_URL=%s). "
        "Admin links (verify, reset password) will point at localhost — "
        "set APP_URL in the environment.",
        _DEFAULT_LOCAL_URL, PUBLIC_APP_URL,
    )
else:
    logger.info(
        "url_builder: PUBLIC_APP_URL=%s APP_URL=%s",
        PUBLIC_APP_URL, APP_URL,
    )


# ── Builders ────────────────────────────────────────────────────────────────


def _join(base: str, path: str) -> str:
    """Concatenate base + path, tolerating a leading or absent slash on path.

    No URL-encoding of `path` here: callers already pass ready-made paths
    (often with query strings they built themselves) and double-encoding
    would corrupt tokens. If a caller has untrusted input it is their job
    to encode it before passing it in.
    """
    if not path:
        return base
    if path.startswith(("http://", "https://")):
        # Already absolute; pass through. Lets old call sites that built
        # the URL elsewhere migrate without changing behaviour.
        return path
    return f"{base}/{path.lstrip('/')}"


def build_public_url(path: str = "") -> str:
    """Absolute URL for a customer-facing landing.

    Use for `/t/<token>`, `/b/<token>`, `/rsv/<token>`, `/d/<token>`,
    `/account/courses/...`, `/co/<slug>/...` and similar surfaces a
    purchaser opens from an email or shares with a friend.
    """
    return _join(PUBLIC_APP_URL, path)


def build_app_url(path: str = "") -> str:
    """Absolute URL for an admin or authenticated customer flow.

    Use for `/verify-email`, `/reset-password`, `/account/orders/...`,
    `/account/login` and similar pages reached after authentication.
    """
    return _join(APP_URL, path)
