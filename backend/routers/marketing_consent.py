"""Marketing consent router — Wave GDPR-Commerce Piece 1b (2026-05-19).

Public endpoints (NO auth required) that let any customer — guest or
registered — revoke their marketing consent via a signed link
typically embedded in an email footer or a newsletter campaign.

GDPR rationale:
  Art. 7(3): "It shall be as easy to withdraw consent as to give it."
  Guest customers who ticked the marketing checkbox at checkout cannot
  log into a portal (they have no account) — they would otherwise have
  NO technical way to revoke. The signed token in the unsubscribe URL
  closes that gap.

Endpoints:

  GET  /api/marketing-consent/unsubscribe/{token}
       Validate the token (signature + scope + expiry) and return
       public info for the confirmation page (masked email + the
       merchant org name + idempotency hint). NO write.

  POST /api/marketing-consent/unsubscribe/{token}/confirm
       Execute the revocation. Always idempotent:
         - writes ONE consent_audit row with source=customer_marketing_revoke
           (immutable legal proof, regardless of whether the customer
           was already opted out).
         - if a customer_account exists for email+org, sets
           marketing_revoked_at = now() so the fast-path read
           (/customer-portal/me) reflects the new state.

Both endpoints are intentionally tolerant of unknown emails (a guest
who NEVER opted in can still hit /confirm — we record the explicit
"no marketing" statement and that is itself legally valid). What we
NEVER do: leak whether the email exists in our DB. The error language
is identical for "valid token, unknown email" and "valid token,
known email" → no oracle for enumeration.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from core.marketing_unsubscribe_token import (
    TokenExpiredError,
    TokenInvalidError,
    decode_marketing_unsubscribe_token,
)


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/marketing-consent", tags=["Marketing Consent"])


# ── Helpers ────────────────────────────────────────────────────────────────


def _mask_email(email: str) -> str:
    """Return a privacy-safe masked rendering of the email.

    "mario.rossi@example.com" → "m***i@example.com"

    Used on the GET response so the customer can confirm the link
    targets THEIR address without us echoing the full string back
    (which would help phishing pages built around leaked tokens).
    """
    s = (email or "").strip().lower()
    if "@" not in s:
        return "***"
    local, _, domain = s.partition("@")
    if len(local) <= 2:
        masked = local[:1] + "***"
    else:
        masked = local[0] + "***" + local[-1]
    return f"{masked}@{domain}"


def _decode_or_raise(token: str) -> dict:
    """Decode token → payload, or raise the right HTTPException.

    Maps:
      TokenInvalidError  → 401 (bad signature / scope / shape)
      TokenExpiredError  → 410 (sig OK but exp in the past)

    Keeps the error language uniform: the response body just says
    "invalid_token" or "expired_token" — no detail about which claim
    failed. This avoids an oracle for an attacker probing the secret.
    """
    try:
        return decode_marketing_unsubscribe_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error_code": "expired_token",
                "message": "This unsubscribe link has expired.",
            },
        )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "invalid_token",
                "message": "This unsubscribe link is not valid.",
            },
        )


async def _fetch_org_name(organization_id: str) -> Optional[str]:
    """Return the human-readable org name, or None on failure.

    Best-effort: the UI shows "{org_name}" so the customer recognises
    which merchant they are unsubscribing from. Failure here just
    falls back to a generic label — never blocks the unsubscribe.
    """
    try:
        from database import organizations_collection
        org = await organizations_collection.find_one(
            {"id": organization_id},
            {"_id": 0, "name": 1},
        )
        if org and isinstance(org.get("name"), str):
            return org["name"]
    except Exception as exc:
        logger.warning(
            "marketing_consent: org name lookup failed for org_id=%s: %s",
            organization_id, exc,
        )
    return None


async def _is_already_unsubscribed(
    email: str, organization_id: str,
) -> bool:
    """Return True iff the most recent marketing event is a revoke.

    Looks at consent_audit (the immutable legal record) AND
    customer_accounts.marketing_revoked_at when present. The two are
    OR-ed because a customer who toggled off in the portal will only
    have the customer_account field set (no audit row from the
    /customer-portal flow yet — that lives in Piece 1a, future work).

    Only used to drive the UI hint "you are already unsubscribed";
    never used to refuse the POST (the POST is idempotent by design
    and ALWAYS writes a fresh audit row).
    """
    # 1. Fast-path: registered customer flag.
    try:
        from database import customer_accounts_collection
        acct = await customer_accounts_collection.find_one(
            {"email": email, "organization_id": organization_id},
            {"_id": 0, "marketing_revoked_at": 1, "accepted_marketing_at": 1},
        )
        if acct:
            revoked = acct.get("marketing_revoked_at")
            accepted = acct.get("accepted_marketing_at")
            # Revoked is the most recent action iff it exists AND
            # (no accepted, OR accepted is older than revoked).
            if revoked and (not accepted or revoked > accepted):
                return True
    except Exception as exc:
        logger.warning(
            "marketing_consent: customer_account lookup failed: %s", exc,
        )

    # 2. Audit-trail fallback (covers guest customers without an account).
    try:
        from database import consent_audit_collection
        cursor = consent_audit_collection.find(
            {
                "customer_email": email,
                "organization_id": organization_id,
                "document_type": "merchant_marketing",
                "source": {
                    "$in": [
                        "customer_marketing_optin",
                        "customer_marketing_revoke",
                        "customer_checkout",
                    ]
                },
            },
            {"_id": 0, "source": 1, "accepted_at": 1},
        ).sort("accepted_at", -1).limit(1)
        docs = await cursor.to_list(1)
        if docs and docs[0].get("source") == "customer_marketing_revoke":
            return True
    except Exception as exc:
        logger.warning(
            "marketing_consent: consent_audit lookup failed: %s", exc,
        )

    return False


def _client_ip(request: Request) -> Optional[str]:
    """Extract the originating client IP (X-Forwarded-For aware).

    The audit row carries the IP for forensic value. We trust the
    first hop of X-Forwarded-For when present (production deployment
    sits behind a reverse proxy). Falls back to request.client.host.
    """
    try:
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip() or None
        return request.client.host if request.client else None
    except Exception:
        return None


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/unsubscribe/{token}")
async def preview_unsubscribe(token: str):
    """Validate the token and return public info for the confirm page.

    This endpoint does NOT mutate any state — it exists so the
    frontend can render a "Are you sure you want to unsubscribe?"
    confirmation rather than acting on a one-click GET (which
    aggressive email clients sometimes pre-fetch, leading to
    accidental unsubscribes).

    Response:
      200 → {"valid": True, "email_masked": "m***i@x.com",
             "organization_name": "ACME Srl",
             "already_unsubscribed": False}
      401 → {"detail": {"error_code": "invalid_token", ...}}
      410 → {"detail": {"error_code": "expired_token", ...}}
    """
    payload = _decode_or_raise(token)
    email = payload["email"]
    org_id = payload["organization_id"]

    org_name = await _fetch_org_name(org_id)
    already = await _is_already_unsubscribed(email, org_id)

    return JSONResponse(
        content={
            "valid": True,
            "email_masked": _mask_email(email),
            "organization_name": org_name,
            "already_unsubscribed": already,
        },
        headers={
            # Don't cache: the already_unsubscribed flag is stateful
            # and a stale cache would mislead a customer who just
            # toggled back on from another device.
            "Cache-Control": "no-store",
        },
    )


@router.post("/unsubscribe/{token}/confirm")
async def confirm_unsubscribe(token: str, request: Request):
    """Execute the marketing-consent revocation. Idempotent.

    Writes exactly ONE consent_audit row regardless of prior state
    (the row IS the legal proof — duplicate revocations create
    duplicate proofs, which is fine; the customer's intent is
    captured each time the link is clicked).

    Also updates customer_accounts.marketing_revoked_at when a
    matching account exists so the registered-customer fast-path
    reflects the revocation immediately on next portal load.

    Response:
      200 → {"success": True, "applied_to_account": True/False}
      401 → invalid_token
      410 → expired_token
      500 → only if the audit write itself fails (very rare; mirrors
            the consent_audit insert error policy from CG-1)
    """
    payload = _decode_or_raise(token)
    email = payload["email"]
    org_id = payload["organization_id"]

    now_iso = datetime.now(timezone.utc).isoformat()
    ip = _client_ip(request)
    ua = request.headers.get("user-agent", "") or None

    # 1a. Update customer_accounts (best-effort; legacy guests have no row).
    applied_to_account = False
    try:
        from database import customer_accounts_collection
        result = await customer_accounts_collection.update_one(
            {"email": email, "organization_id": org_id},
            {"$set": {
                "marketing_revoked_at": now_iso,
                "updated_at": now_iso,
            }},
        )
        # matched_count is the canonical "did we find the doc"; the
        # update is set-only and so modified_count may be 0 on a
        # re-click which is still success.
        applied_to_account = bool(getattr(result, "matched_count", 0))
    except Exception as exc:
        # Soft-fail: the audit row (next step) is the legal proof
        # and must be written even if the account update glitched.
        logger.warning(
            "marketing_consent: customer_account update failed "
            "for email=%s org_id=%s: %s",
            email, org_id, exc,
        )

    # 1b. 2026-05-20 — Update CRM customer row too. This is what makes
    # the revocation visible in CI-admin-vis for GUEST customers (who
    # have no customer_account doc but DO have a CRM record created at
    # checkout). Independent of step 1a — a registered customer who
    # ALSO has a CRM row gets both rows updated (the dashboard reads
    # CRM as fallback, customer_account as primary for registered).
    applied_to_customer = False
    try:
        from database import customers_collection
        # The CRM customer is keyed by ``email`` within the org. Email
        # is unique per (org, email) by storefront contract — the
        # storefront's order submission upserts a CRM record on this
        # exact pair. update_one with matched_count is enough.
        # Note: email may be stored mixed-case on legacy rows; we
        # normalise both sides defensively.
        normalised_email = (email or "").strip().lower()
        if normalised_email:
            crm_result = await customers_collection.update_one(
                {
                    "organization_id": org_id,
                    "email": {"$regex": f"^{re.escape(normalised_email)}$", "$options": "i"},
                },
                {"$set": {
                    "marketing_revoked_at": now_iso,
                    "updated_at": now_iso,
                }},
            )
            applied_to_customer = bool(getattr(crm_result, "matched_count", 0))
    except Exception as exc:
        logger.warning(
            "marketing_consent: customer CRM update failed "
            "for email=%s org_id=%s: %s",
            email, org_id, exc,
        )

    # 2. Write the immutable consent_audit record. THIS IS THE LEGAL
    # PROOF — if it fails, the operation fails (500). The merchant
    # cannot pretend the revocation never happened from the customer's
    # standpoint, but our compliance posture requires the audit row
    # to exist, so we surface the failure rather than silently swallow.
    try:
        from repositories.consent_audit_repository import record_consent
        from core.legal_versions import current_version_string
        # Use the current legal version_string for the version_tag/hash —
        # the customer is revoking against whatever the merchant is
        # currently publishing. Keeps the schema field populated; the
        # action (source=customer_marketing_revoke) is what actually
        # matters for compliance.
        version_string = current_version_string() or "v0.0:unknown"
        if ":" in version_string:
            ver_tag, ver_hash = version_string.split(":", 1)
        else:
            ver_tag, ver_hash = version_string, "unknown"

        await record_consent(
            user_id=None,
            customer_email=email,
            organization_id=org_id,
            source="customer_marketing_revoke",
            document_type="merchant_marketing",
            locale="it",  # the merchant's binding language; the actual
                          # confirmation page locale is observed via
                          # user_agent / Accept-Language separately
            version_tag=ver_tag,
            version_hash=ver_hash,
            ip_address=ip,
            user_agent=ua,
        )
    except Exception as exc:
        logger.error(
            "marketing_consent: consent_audit write FAILED "
            "for email=%s org_id=%s: %s",
            email, org_id, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "audit_write_failed",
                "message": "Unable to record the revocation. Please try again.",
            },
        )

    return JSONResponse(
        content={
            "success": True,
            "applied_to_account": applied_to_account,
        },
        headers={"Cache-Control": "no-store"},
    )
