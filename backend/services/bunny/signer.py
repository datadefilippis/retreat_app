"""
signer.py — Bunny Stream signed embed URL generator.

Moved from `services/bunny_service.py` in Step 7 of the bunny
consolidation. The legacy module path stays as a back-compat shim so
existing call sites (`from services.bunny_service import ...`) keep
working without churn — see `services/bunny_service.py` for the shim.

References the public Bunny documentation for Embed View Token Authentication:

  URL pattern:
    https://iframe.mediadelivery.net/embed/{library_id}/{video_guid}
        ?token={hex_sha256}
        &expires={unix_timestamp}

  Token formula (as documented at docs.bunny.net):
    token = sha256( token_security_key + video_guid + expires ).hex()

The `token_security_key` is the Library's "Token Authentication Key"
(distinct from the generic API key). We accept both — if the org only
configured an `api_key`, we fall back to it so the single-key
deployments of Bunny keep working. Merchants with separate keys are
recommended to populate `token_security_key` explicitly.

This module is PURE: no MongoDB access, no HTTP calls. Callers pass in
the already-loaded integration config and the video_guid, and receive
a ready-to-render URL + expiry. Keeping it pure makes it trivially
unit-testable against vectors published by Bunny, AND keeps it
decoupled from the verifier module (which DOES make HTTP calls — see
services/bunny/verifier.py). The two are independent entry points of
the `bunny/` boundary.

Security notes:
  * Never log the `token_security_key` / `api_key`.
  * The returned `play_url` is the credential — it must transit over
    HTTPS and be stored only briefly in the customer browser.
  * TTL default is 2 hours. Callers should prefer a shorter value for
    high-value content.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default TTL for signed embed URLs. Bunny accepts any window; we pick
# 2h as a balance between UX (no mid-watch re-fetches) and security
# (stolen URLs expire before the same-day attacker can exploit them).
DEFAULT_PLAY_URL_TTL_SECONDS = 7200          # 2 hours
# Refresh threshold: the frontend auto-refetches when the URL has less
# than this many seconds left, so the iframe never dies mid-playback.
REFRESH_MARGIN_SECONDS = 300                 # 5 minutes

_EMBED_BASE = "https://iframe.mediadelivery.net/embed"


class BunnyConfigError(Exception):
    """Raised when the org's Bunny integration is missing or incomplete."""


@dataclass(frozen=True)
class SignedEmbedUrl:
    """Return shape of `generate_signed_embed_url`."""
    play_url: str
    expires_at: datetime
    watermark_text: Optional[str]


def _extract_signing_key(config: Dict[str, Any]) -> str:
    """Return the key used to HMAC the embed URL.

    Priority: `token_security_key` → `api_key`. Raises when neither is
    populated so callers can surface a 503 to the merchant.
    """
    key = (config.get("token_security_key") or config.get("api_key") or "").strip()
    if not key:
        raise BunnyConfigError("Bunny library has no signing key configured")
    return key


def _build_token(signing_key: str, video_guid: str, expires: int) -> str:
    """Compute the Bunny embed token.

    Per Bunny docs the hash input is the concatenation of the 3 strings
    in this exact order. SHA-256 hex-encoded is what Bunny expects.
    """
    payload = f"{signing_key}{video_guid}{expires}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_bunny_config(config: Optional[Dict[str, Any]]) -> bool:
    """Return True when the org has a Bunny config complete enough to mint
    signed URLs. Callers hit this first and return 503 on False so the
    customer UI can show a "contact the merchant" message instead of a
    generic error.
    """
    if not config:
        return False
    lib = (config.get("library_id") or "").strip()
    if not lib:
        return False
    try:
        _extract_signing_key(config)
    except BunnyConfigError:
        return False
    return True


def generate_signed_embed_url(
    config: Dict[str, Any],
    video_guid: str,
    *,
    customer_email: Optional[str] = None,
    ttl_seconds: int = DEFAULT_PLAY_URL_TTL_SECONDS,
    autoplay: bool = True,
) -> SignedEmbedUrl:
    """Mint a signed Bunny Stream embed URL for a single video.

    Args:
      config:          org.integrations.bunny as a plain dict
      video_guid:      the Bunny video UUID (stored on the Lesson row)
      customer_email:  used to compute the watermark label ONLY when
                       `config.watermark_enabled` is truthy. Never ends
                       up in the token itself.
      ttl_seconds:     URL validity window. Kept >= 60s to tolerate
                       small clock skew between our server and Bunny.
      autoplay:        when True appends &autoplay=true for the iframe
                       player — reduces the UX friction of a second
                       click before the video starts.

    Returns:
      SignedEmbedUrl with `play_url`, `expires_at` (timezone-aware UTC)
      and `watermark_text` (None when watermark is disabled).

    Raises:
      BunnyConfigError when the config is incomplete. ValueError when
      video_guid is empty or ttl is non-positive.
    """
    if not video_guid or not isinstance(video_guid, str):
        raise ValueError("video_guid is required")
    if ttl_seconds < 60:
        raise ValueError("ttl_seconds must be at least 60s")

    library_id = (config.get("library_id") or "").strip()
    if not library_id:
        raise BunnyConfigError("Bunny library_id is missing")
    signing_key = _extract_signing_key(config)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)
    expires_unix = int(expires_at.timestamp())
    token = _build_token(signing_key, video_guid, expires_unix)

    params = f"token={token}&expires={expires_unix}"
    if autoplay:
        params += "&autoplay=true"

    play_url = f"{_EMBED_BASE}/{library_id}/{video_guid}?{params}"

    watermark_text: Optional[str] = None
    if config.get("watermark_enabled") and customer_email:
        watermark_text = customer_email

    # Defensive: never log the signed URL or the signing key.
    logger.debug(
        "bunny.signer: minted play-url for library=%s video=%s ttl=%ds",
        library_id, video_guid, ttl_seconds,
    )

    return SignedEmbedUrl(
        play_url=play_url,
        expires_at=expires_at,
        watermark_text=watermark_text,
    )
