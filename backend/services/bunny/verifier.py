"""
Credential probe — single source of truth for "is this Bunny config valid?".

Three layered checks, each producing a granular signal in the result:

  1. API check      — GET /library/{id} with the AccessKey. Verifies
                      api_key + library_id. Existing path.
  2. Embed check    — fetch the iframe player URL on a real video.
                      Detects the Bunny "This content is blocked" page
                      (signing key wrong, or Token Authentication mis-
                      configured). Skipped when token_security_key is
                      not provided AND api_key is missing.
  3. CDN check      — fetch the HLS playlist on the Pull Zone CDN with
                      `Referer: <PUBLIC_APP_URL>`. Detects the 403 from
                      hotlink-protection. Skipped when cdn_hostname or
                      referrer is missing.

The probe is designed to be backward-compatible: callers that pass only
(library_id, api_key) keep the existing single-check behaviour. Callers
that want the full diagnostic — typically the admin "Test connection"
button — pass token_security_key + cdn_hostname + referrer to enable
checks 2 and 3.

Pure async function + pure data result; no side effects, no DB access.
The router persists the result.

Why a dedicated module instead of methods on BunnyClient: the verifier
is the ONE place where we enumerate every status mapping. Tests target
this function with mocked HTTP responses; the client stays a thin
HTTP wrapper without policy.

Edge cases handled (each documented inline):
  - Empty / whitespace-only credentials              → NOT_CONFIGURED
  - 401 from Bunny on API check                      → UNAUTHORIZED
  - 404 from Bunny on API check                      → LIBRARY_NOT_FOUND
  - Library reachable but empty                      → NO_VIDEOS
  - Embed page contains "This content is blocked"    → EMBED_BLOCKED
  - CDN returns 403 with Referer set                 → CDN_BLOCKED
  - Timeout / DNS / connection refused               → NETWORK_ERROR
  - 5xx, malformed JSON, anything else               → UNKNOWN
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from services.bunny.client import BunnyClient
from services.bunny.models import BunnyStatus, VerificationResult


logger = logging.getLogger(__name__)


# --- Internal helpers for checks 2 and 3 ----------------------------------

_EMBED_BASE = "https://iframe.mediadelivery.net/embed"

# String the iframe body returns when Bunny refuses to play the video for
# any reason that we (the merchant) can fix from the panel: signing key
# wrong, library hostname allowlist not satisfied, etc. Hardcoding the
# exact phrase is brittle but pragmatic — Bunny doesn't return a machine-
# readable error code on this surface.
_EMBED_BLOCKED_MARKER = "This content is blocked"


def _build_signed_embed_url(library_id: str, video_guid: str,
                            signing_key: str, ttl_seconds: int = 600) -> str:
    """Mirror of services.bunny.signer._build_token but inlined to keep
    this module's dependency tree minimal — pulling signer here would
    create a circular boundary (signer is consumed by the customer-portal
    play-url path; this module is consumed by admin verify path).
    Identical math: `sha256(key + guid + expires_unix).hex()`.
    """
    expires = int((datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).timestamp())
    payload = f"{signing_key}{video_guid}{expires}".encode("utf-8")
    token = hashlib.sha256(payload).hexdigest()
    return f"{_EMBED_BASE}/{library_id}/{video_guid}?token={token}&expires={expires}"


def _bunny_panel_url_for_library(library_id: str, *, focus: str = "embed") -> str:
    """Deep link the admin can open to fix the failing check.

    `focus`:
      - "embed"   → library settings page (Token Authentication, hotlink rules)
      - "cdn"     → pull zone settings (Hotlink Protection)
    Bunny's panel uses a single library URL for both today; we keep the
    parameter so future Bunny URL changes can be absorbed in one place.
    """
    return f"https://dash.bunny.net/stream/{library_id}/library"


async def verify_credentials(
    library_id: Optional[str],
    api_key: Optional[str],
    *,
    timeout: float = 5.0,
    token_security_key: Optional[str] = None,
    cdn_hostname: Optional[str] = None,
    referrer: Optional[str] = None,
) -> VerificationResult:
    """Probe Bunny once and return a `VerificationResult`.

    Never raises — every transport / API failure maps to a status. This
    is intentional: the router calling us treats this as "tell me what's
    going on" not "may throw". Easier to use in middleware-style code
    (e.g. auto-verify on PATCH).

    Args:
        library_id:         numeric-string ID of the Bunny library.
                            Empty/None short-circuits to NOT_CONFIGURED.
        api_key:            Library AccessKey. Empty/None ditto.
        timeout:            seconds before giving up on Bunny. 5s default.

        # Optional kwargs — when supplied, run the extended diagnostic.
        # Backward-compatible: existing callers that omit these get the
        # check-1-only behaviour they had before.

        token_security_key: Library's "Token Authentication Key" used to
                            sign embed URLs. When present, used as the
                            signing key for check 2. Falls back to
                            api_key (matches signer.py fallback rule).
        cdn_hostname:       Pull Zone hostname (e.g. vz-XXX.b-cdn.net).
                            When present + `referrer` set, runs check 3.
        referrer:           Public app URL to send as Referer in check 3.
                            Typically PUBLIC_APP_URL.

    Returns:
        VerificationResult — `frozen=True` so the caller can pass it
        around safely without copying. The granular `*_check_passed`
        booleans tell the caller / UI which step is broken.
    """
    # NOT_CONFIGURED short-circuit: no point hitting Bunny when we know
    # the credentials are missing. Distinct from "tested and failed" so
    # the UI can render "Mai testato" vs "Errato".
    if not library_id or not api_key or not library_id.strip() or not api_key.strip():
        return VerificationResult(
            status=BunnyStatus.NOT_CONFIGURED,
            error_message=None,  # null on purpose: nothing went wrong, just nothing tried
        )

    # ── CHECK 1: API access (existing) ────────────────────────────────────
    library_id_clean = library_id.strip()
    try:
        async with BunnyClient(api_key=api_key, timeout=timeout) as client:
            lib = await client.get_library(library_id_clean)
            # Reuse the same client for the optional video lookup later.
            videos_payload = None
            if token_security_key is not None or cdn_hostname is not None:
                # Only list videos if we will actually need a video_guid.
                # Saves an API call when the caller is doing a check-1-only probe.
                try:
                    videos_payload = await client.list_videos(
                        library_id_clean, page=1, items_per_page=1,
                    )
                except Exception:
                    # Listing failed but get_library succeeded — proceed
                    # with API check OK and skip extended checks. Log only.
                    logger.info("Bunny verify: list_videos failed after get_library OK")
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 401:
            return VerificationResult(
                status=BunnyStatus.UNAUTHORIZED,
                error_message=(
                    "API key non valida o revocata. "
                    "Genera una nuova chiave nel pannello Bunny."
                ),
                api_check_passed=False,
            )
        if code == 404:
            return VerificationResult(
                status=BunnyStatus.LIBRARY_NOT_FOUND,
                error_message=(
                    f"Library ID {library_id} non esiste. "
                    "Controlla nella dashboard Bunny → Stream → Libraries."
                ),
                api_check_passed=False,
            )
        logger.warning("Bunny verify returned %s: %s", code, e.response.text[:200])
        return VerificationResult(
            status=BunnyStatus.UNKNOWN,
            error_message=f"Bunny ha risposto con errore {code}. Riprova più tardi.",
            api_check_passed=False,
        )

    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.info("Bunny verify network error: %s", type(e).__name__)
        return VerificationResult(
            status=BunnyStatus.NETWORK_ERROR,
            error_message="Bunny non raggiungibile. Riprova tra qualche minuto.",
            api_check_passed=False,
        )

    except Exception as e:
        logger.error("Bunny verify unexpected error: %s", e, exc_info=True)
        return VerificationResult(
            status=BunnyStatus.UNKNOWN,
            error_message="Errore inatteso. Riprova o contatta il supporto.",
            api_check_passed=False,
        )

    # API check passed — extract metadata.
    # Library NAME is not exposed via /library/{id} with a library-scoped
    # AccessKey (would need account-level key on /videolibrary/{id}).
    # Accept either casing for forward-compat.
    name = lib.get("name") or lib.get("Name")
    count = lib.get("videoCount")
    if count is None:
        count = lib.get("VideoCount")

    # Decide whether to run extended checks. They require:
    #   - a real video_guid from the library
    #   - and at least one of (token_security_key+api_key) for embed,
    #     (cdn_hostname + referrer) for CDN.
    extended_requested = (token_security_key is not None) or (
        cdn_hostname is not None and referrer is not None
    )

    if not extended_requested:
        # Backward-compat path: only check 1 was requested.
        return VerificationResult(
            status=BunnyStatus.OK,
            library_name=name,
            video_count=count,
            error_message=None,
            api_check_passed=True,
        )

    # Extended diagnostic requested. Need a video to test.
    items = (videos_payload or {}).get("items") or []
    if not items:
        # Library is reachable but empty — cannot test embed/CDN. Treat
        # as a soft-OK so the UI shows "tutto ok, ma carica un video
        # per completare la verifica".
        return VerificationResult(
            status=BunnyStatus.NO_VIDEOS,
            library_name=name,
            video_count=count or 0,
            error_message=(
                "Library raggiungibile ma vuota. Carica almeno un video "
                "su Bunny per completare il test embed e CDN."
            ),
            api_check_passed=True,
            embed_check_passed=None,
            cdn_check_passed=None,
        )

    sample_video_guid = items[0].get("guid")
    if not sample_video_guid:
        # Defensive: items present but malformed. Log + return API-OK
        # without extended checks. Better than failing closed.
        logger.warning("Bunny verify: list_videos returned items without guid")
        return VerificationResult(
            status=BunnyStatus.OK,
            library_name=name,
            video_count=count,
            api_check_passed=True,
        )

    # ── CHECK 2: Embed iframe — detects "This content is blocked" ─────────
    embed_check_passed: Optional[bool] = None
    if token_security_key is not None:
        signing_key = (token_security_key or api_key).strip()
        embed_url = _build_signed_embed_url(library_id_clean, sample_video_guid, signing_key)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as h:
                r = await h.get(embed_url, headers={"User-Agent": "Mozilla/5.0 (afianco verify)"})
                body = r.text or ""
                if _EMBED_BLOCKED_MARKER in body:
                    return VerificationResult(
                        status=BunnyStatus.EMBED_BLOCKED,
                        library_name=name,
                        video_count=count,
                        error_message=(
                            "Bunny rifiuta di riprodurre il video. Verifica nelle "
                            "impostazioni della library: 'Token Authentication Key' "
                            "corretta, oppure 'Allowed Domains' include afianco.app. "
                            "I customer vedrebbero 'This content is blocked'."
                        ),
                        api_check_passed=True,
                        embed_check_passed=False,
                        cdn_check_passed=None,
                        bunny_panel_url=_bunny_panel_url_for_library(
                            library_id_clean, focus="embed",
                        ),
                    )
                # 4xx/5xx without the marker is suspicious — log but don't
                # auto-fail; some Bunny error pages may evolve over time.
                if r.status_code >= 400:
                    logger.info(
                        "Bunny verify embed: HTTP %s for video %s, body sample: %s",
                        r.status_code, sample_video_guid, body[:200],
                    )
                    embed_check_passed = False
                else:
                    embed_check_passed = True
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            # Embed CDN unreachable. Don't mark this a hard failure: API
            # worked, network blip is more likely than a config issue here.
            logger.info("Bunny verify embed network error: %s", type(e).__name__)
            embed_check_passed = None

    # ── CHECK 3: CDN HLS playlist — detects pull-zone hotlink protection ──
    cdn_check_passed: Optional[bool] = None
    if cdn_hostname and referrer:
        cdn_host_clean = cdn_hostname.strip().rstrip("/")
        # Strip protocol if the admin pasted a full URL by mistake.
        if cdn_host_clean.startswith(("http://", "https://")):
            cdn_host_clean = cdn_host_clean.split("://", 1)[1]
        manifest_url = f"https://{cdn_host_clean}/{sample_video_guid}/playlist.m3u8"
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as h:
                r = await h.get(manifest_url, headers={
                    "User-Agent": "Mozilla/5.0 (afianco verify)",
                    "Referer": referrer,
                })
                if r.status_code == 200:
                    cdn_check_passed = True
                elif r.status_code == 403:
                    return VerificationResult(
                        status=BunnyStatus.CDN_BLOCKED,
                        library_name=name,
                        video_count=count,
                        error_message=(
                            "Il CDN della library blocca le richieste video. "
                            "Verifica che la Pull Zone associata alla library "
                            "consenta il referrer afianco.app (o disattiva "
                            "Hotlink Protection nelle impostazioni del CDN)."
                        ),
                        api_check_passed=True,
                        embed_check_passed=embed_check_passed,
                        cdn_check_passed=False,
                        bunny_panel_url=_bunny_panel_url_for_library(
                            library_id_clean, focus="cdn",
                        ),
                    )
                else:
                    logger.info(
                        "Bunny verify CDN: unexpected HTTP %s for %s",
                        r.status_code, manifest_url,
                    )
                    cdn_check_passed = False
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.info("Bunny verify CDN network error: %s", type(e).__name__)
            cdn_check_passed = None

    # All applicable checks passed (or network-blip None for non-critical).
    return VerificationResult(
        status=BunnyStatus.OK,
        library_name=name,
        video_count=count,
        error_message=None,
        api_check_passed=True,
        embed_check_passed=embed_check_passed,
        cdn_check_passed=cdn_check_passed,
    )
