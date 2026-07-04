"""
Bunny integration boundary.

This is the single import point for everything Bunny-related. The
folder structure is intentional:

  models.py    — domain types (BunnyStatus, VerificationResult)
  client.py    — async HTTP wrapper around Bunny API
  verifier.py  — credential probe (uses client; produces VerificationResult)
  signer.py    — HMAC-SHA256 signed embed URL generation (moved here
                 from the legacy `services/bunny_service.py` in Step 7;
                 the legacy module path is now a back-compat shim that
                 re-exports from here)

Public API — verifier side (Step 1):
  - verify_credentials       — async credential probe
  - BunnyStatus              — enum of probe outcomes
  - VerificationResult       — DTO returned by the verifier
  - BunnyClient              — low-level HTTP client (for advanced uses)

Public API — signer side (Step 7, moved from bunny_service.py):
  - generate_signed_embed_url — mint a signed Bunny embed URL
  - validate_bunny_config     — quick local validity check
  - BunnyConfigError          — raised when config is incomplete
  - SignedEmbedUrl            — return type of generate_signed_embed_url
  - DEFAULT_PLAY_URL_TTL_SECONDS, REFRESH_MARGIN_SECONDS — constants

Two independent entry points: the verifier MAKES HTTP calls, the
signer is PURE (no I/O). Callers that only need to mint URLs (hot
path, customer playback) don't pull in httpx by accident.
"""

from services.bunny.client import BunnyClient
from services.bunny.models import BunnyStatus, VerificationResult
from services.bunny.verifier import verify_credentials
from services.bunny.signer import (
    BunnyConfigError,
    SignedEmbedUrl,
    DEFAULT_PLAY_URL_TTL_SECONDS,
    REFRESH_MARGIN_SECONDS,
    generate_signed_embed_url,
    validate_bunny_config,
)
from services.bunny.resolver import resolve_library_config


__all__ = [
    # Verifier side
    "BunnyClient",
    "BunnyStatus",
    "VerificationResult",
    "verify_credentials",
    # Signer side
    "BunnyConfigError",
    "SignedEmbedUrl",
    "DEFAULT_PLAY_URL_TTL_SECONDS",
    "REFRESH_MARGIN_SECONDS",
    "generate_signed_embed_url",
    "validate_bunny_config",
    # Resolver (multi-library)
    "resolve_library_config",
]
