"""
Bunny integration domain models — pure data, no I/O.

Two top-level types:

  BunnyStatus       — enum capturing every outcome of a credential probe
  VerificationResult — DTO returned by the verifier; immutable, JSON-serialisable

These are intentionally separate from the persisted `BunnyIntegration` model
(`backend/models/organization.py`). The persisted model stores the FLATTENED
status fields (last_verification_status: str, library_name: str | None, ...);
this module is the in-memory representation the verifier produces and the
router maps to the persisted form.

Why a flat string on the persisted side: Mongo doesn't have native enums and
forward-compat is easier when you can add a new status without a migration.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BunnyStatus(str, Enum):
    """Outcome of a single credential-probe attempt against Bunny's API.

    The values are stable strings — they show up in audit logs and in the
    persisted `last_verification_status` field. Renaming any of these
    requires a migration.

    The verifier now performs three layered checks, each with its own
    failure mode:

      1. API check  — GET /library/{id} with the AccessKey (existing path)
      2. Embed check — fetch the iframe player URL on a real video,
                      detect Bunny's "This content is blocked" page
                      (signing key wrong / token-auth misconfigured)
      3. CDN check  — fetch the HLS playlist on the Pull Zone with
                      `Referer: <PUBLIC_APP_URL>`, detect 403 from the
                      Pull Zone hotlink-protection wall

    Map of failure modes -> status values is in `verifier.verify_credentials`.
    """

    # Happy path: every applicable check passed
    OK = "ok"

    # Bunny returned 401 on the API check — api_key is wrong or revoked
    UNAUTHORIZED = "unauthorized"

    # Bunny returned 404 on the API check — library_id does not exist
    LIBRARY_NOT_FOUND = "library_not_found"

    # Network-level failure: timeout, DNS, connection refused. Distinct from
    # auth errors so the UI can hint "ritenta" instead of "credenziali".
    NETWORK_ERROR = "network_error"

    # Anything else: 5xx from Bunny, unparseable JSON, unexpected status.
    # Always paired with `error_message` so the admin sees what we got.
    UNKNOWN = "unknown"

    # No probe attempted — fields are empty. Distinct from "tested and failed"
    # so the UI can show "Mai testato" instead of "Errato".
    NOT_CONFIGURED = "not_configured"

    # Library is reachable + credentials valid, but it has zero videos so
    # we cannot run the embed/CDN checks (they need a real video_guid).
    # Treat as a SOFT-OK: the merchant just hasn't uploaded yet.
    NO_VIDEOS = "no_videos"

    # Embed iframe loads but the body returns Bunny's "This content is
    # blocked" page. Two underlying causes converge here from a single
    # observation: signing key wrong, OR the library's "Token
    # Authentication" gate is misconfigured. The admin can fix either
    # by re-pasting the Token Authentication Key from the Bunny panel.
    EMBED_BLOCKED = "embed_blocked"

    # Pull Zone CDN refused the HLS playlist request. Typical cause:
    # the Pull Zone has hotlink-protection enabled and our `Referer`
    # is not in its allowed list (or the library has any-referrer
    # required and the customer browser strips it via Referrer-Policy).
    # The admin must edit the Pull Zone settings on the Bunny panel.
    CDN_BLOCKED = "cdn_blocked"


class VerificationResult(BaseModel):
    """Immutable result of `verifier.verify_credentials`.

    Returned to the router which maps it to the persisted state. Never
    contains the api_key (caller already has it; we don't echo secrets).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: BunnyStatus

    # Populated only on `OK`. Surfaced in the admin UI as the visible
    # confirmation that the right library is connected ("Connesso a
    # 'Olistica Studio'").
    library_name: Optional[str] = None

    # Populated only on `OK`. Same purpose: visible proof of a healthy
    # connection. May be 0 for empty libraries — that's still OK.
    video_count: Optional[int] = None

    # Human-readable, Italian, populated on every non-OK status. Designed
    # to be shown verbatim in the admin UI without further translation.
    error_message: Optional[str] = None

    # Granular check results — one bool per probe layer. None means the
    # check was skipped (e.g. embed_check_passed = None when the API
    # check failed earlier and we short-circuited). The admin UI uses
    # these to render a 3-line checklist instead of a single binary
    # "ok / fail" badge, so the merchant sees exactly which step is
    # broken.
    api_check_passed: Optional[bool] = None
    embed_check_passed: Optional[bool] = None
    cdn_check_passed: Optional[bool] = None

    # When CDN_BLOCKED or EMBED_BLOCKED, the deep-link the UI offers
    # to the admin so they don't have to fish for the right Bunny
    # panel page. Built as `https://dash.bunny.net/stream/{lib_id}`
    # plus a sub-path appropriate for the failure mode.
    bunny_panel_url: Optional[str] = None
