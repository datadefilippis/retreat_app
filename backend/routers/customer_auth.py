"""
Customer Authentication Router — public-facing signup, login, password reset, verification.

All endpoints are public (no auth required). Rate-limited per endpoint.
Completely separate from admin auth routes (/api/auth/*).

ORG-SCOPED: signup and login require a `slug` parameter to identify the
organization. The slug is resolved to org_id server-side.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from auth import get_current_customer
from models import AuditLog
from repositories import audit_repository, customer_account_repository
from routers.auth import limiter
from services import customer_auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customer-auth", tags=["Customer Authentication"])


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _resolve_org_id(slug: str) -> str:
    """Resolve organization_id from a public slug.

    Two-tier resolution to stay consistent with the public storefront
    (`public._resolve_org`):

      1. Multi-store (v12+): look up `stores.slug` → org_id from the
         matched store document. This is the modern path used by
         /s/:slug on the storefront.
      2. Legacy fallback: `organizations.public_slug` for orgs that
         predate the multi-store split.

    Without this dual lookup, customer signup/login from a multi-store
    storefront (e.g. /s/eventi) 404s even though the storefront itself
    resolves correctly — the mismatch broke the course-checkout flow
    where signup is mandatory.
    """
    from database import organizations_collection, stores_collection

    # Modern multi-store path.
    store = await stores_collection.find_one(
        {"slug": slug, "is_published": True, "is_active": True, "visibility": "public"},
        {"_id": 0, "organization_id": 1},
    )
    if store:
        # `$ne: False` — legacy-safe. Pre-v3 orgs don't have the `is_active`
        # field in MongoDB at all; an exact `True` match would reject them
        # even though they are functionally active. Same for `deactivated_at`.
        org = await organizations_collection.find_one(
            {
                "id": store["organization_id"],
                "is_active": {"$ne": False},
                "deactivated_at": None,
            },
            {"_id": 0, "id": 1},
        )
        if org:
            return org["id"]

    # Legacy org.public_slug fallback.
    org = await organizations_collection.find_one(
        {"public_slug": slug, "is_active": {"$ne": False}, "deactivated_at": None},
        {"_id": 0, "id": 1},
    )
    if not org:
        raise HTTPException(status_code=404, detail="Store not found")
    return org["id"]


# ── Request Models ───────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    slug: str                 # Store slug → resolves to org_id
    email: EmailStr
    name: str
    password: str
    locale: str = "it"
    # Release 4 (Courses) — when True, the signup response also carries
    # an access_token so the caller can complete a purchase immediately
    # without a round-trip through email verification. Only the course
    # checkout is expected to pass this flag today.
    auto_login: bool = False
    # Wave GDPR-Commerce CG-4 — explicit consent fields. Both terms +
    # privacy are MANDATORY (the service rejects False with a 400);
    # marketing is opt-in and defaults to False.
    accepted_terms: bool = False
    accepted_privacy: bool = False
    accepted_marketing: bool = False
    # Track O Step 4.1 — honeypot field for anti-bot. Frontend renders
    # this as a hidden input (display:none / off-screen) so humans never
    # see it; naive bots that fill all form inputs will populate it and
    # be silently rejected. Field name 'website' is intentionally
    # innocuous-looking to maximize bot fill rate.
    # See backend/core/honeypot.py for details + threat model.
    website: Optional[str] = None


class LoginRequest(BaseModel):
    slug: str                 # Store slug → resolves to org_id
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    slug: str                 # Store slug → resolves to org_id
    email: EmailStr
    locale: str = "it"


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    slug: str                 # Store slug → resolves to org_id
    email: EmailStr


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/signup", status_code=202)
@limiter.limit("5/15 minutes")
async def signup(body: SignupRequest, request: Request):
    """Create a new customer account within an org. Returns 202 + verification_required.

    Wave GDPR-Commerce CG-4: signup requires explicit acceptance of the
    merchant's Privacy + Terms (the service enforces both flags True
    and rejects with 400 if either is False). The version + locale that
    the customer saw are read server-side from the store doc — the
    request payload only carries the boolean acceptance.
    """
    org_id = await _resolve_org_id(body.slug)
    # CG-4: capture identifying client metadata for the audit trail.
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Track O Step 4.1 — honeypot anti-bot check.
    # If filled, return uniform 202 success (anti-enumeration: bot can't
    # distinguish "caught" from "succeeded") + log + audit + metric.
    from core.honeypot import is_honeypot_triggered
    if is_honeypot_triggered(body.website):
        logger.warning(
            "customer signup honeypot triggered — bot caught. "
            "slug=%s email=%s ip=%s ua=%s honeypot_value=%r",
            body.slug, body.email, client_ip, (user_agent or "")[:80],
            (body.website or "")[:120],
        )
        # Record metric per Sentry alert + Grafana visibility on bot volume.
        try:
            from core.observability.metrics import record_signup
            record_signup(flow="customer", status="honeypot_triggered")
        except Exception:
            pass
        # Audit event for post-incident review (uses same AuditLog schema
        # as other auth events — vedi routers/auth.py:557 reference).
        try:
            from repositories import audit_repository
            from models import AuditLog
            await audit_repository.create(AuditLog(
                organization_id=org_id,
                user_id="bot",  # placeholder — no account exists yet
                action="customer_signup_honeypot",
                resource_type="customer_account",
                resource_id=None,
                details={
                    "ip": client_ip,
                    "user_agent": (user_agent or "")[:200],
                    "email_attempted": body.email,
                    "honeypot_value_redacted": (body.website or "")[:60],
                    "source": "customer_auth_signup",
                },
            ))
        except Exception as audit_err:
            # Audit failure NEVER blocks anti-enumeration response.
            logger.warning("honeypot audit insert failed: %s", audit_err)
        # Uniform success — bot doesn't learn it was caught.
        return {"status": "verification_required"}

    try:
        result = await customer_auth_service.customer_signup(
            org_id=org_id,
            email=body.email,
            name=body.name,
            password=body.password,
            locale=body.locale,
            auto_login=body.auto_login,
            signup_slug=body.slug,
            accepted_terms=body.accepted_terms,
            accepted_privacy=body.accepted_privacy,
            accepted_marketing=body.accepted_marketing,
            request_ip=client_ip,
            user_agent=user_agent,
        )
        # Track O Step 3.3 — record success in customer flow funnel
        try:
            from core.observability.metrics import record_signup
            record_signup(flow="customer", status="success")
        except Exception:
            pass
        return result
    except ValueError as e:
        # Track O Step 3.3 — record validation_failed (invalid input)
        try:
            from core.observability.metrics import record_signup
            record_signup(flow="customer", status="validation_failed")
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Track S Step 2.2 — defense-in-depth anti-enumeration.
        # The service pre-checks duplicate email and returns uniform
        # success, BUT a concurrent signup race could still trigger
        # DuplicateKeyError from the DB unique index. Pre-fix this fell
        # through to global 500 handler → leak ("email exists" via 500
        # vs "new email" via 202). Post-fix: catch DuplicateKeyError
        # specifically and ALSO return uniform 202 success.
        # Any OTHER exception bubbles to the global handler unchanged.
        from pymongo.errors import DuplicateKeyError
        if isinstance(e, DuplicateKeyError):
            # Log loudly so ops sees the race (rare). Anti-enum: same
            # response body as the success branch.
            from logging import getLogger
            getLogger(__name__).warning(
                "customer signup race condition on duplicate key — "
                "returning uniform 202 (anti-enumeration). org=%s",
                org_id,
            )
            # Track O Step 3.3 — record duplicate (the race resolved as such)
            try:
                from core.observability.metrics import record_signup
                record_signup(flow="customer", status="duplicate")
            except Exception:
                pass
            return {"status": "verification_required"}
        # Track O Step 3.3 — record generic error (will become 500 via global handler)
        try:
            from core.observability.metrics import record_signup
            record_signup(flow="customer", status="error")
        except Exception:
            pass
        raise


# ────────────────────────────────────────────────────────────────────────────
# Track O Step 4.3 — Customer logout-all-sessions panic button
# ────────────────────────────────────────────────────────────────────────────


@router.post("/logout-all", status_code=200)
@limiter.limit("10/hour")
async def customer_logout_all(
    request: Request,
    current_customer: dict = Depends(get_current_customer),
):
    """Invalidate ALL active sessions for the current customer account.

    Mirror del merchant /api/auth/logout-all (O4.3). Use cases:
      - Customer sospetta account compromise
      - Logout su shared device
      - Lost device

    Sets tokens_invalidated_at = now in customer_account doc. Tutti i
    JWT customer con iat < now vengono rifiutati da get_current_customer.

    Audit: action='customer_logout_all'.
    Rate limit: 10/hour per IP.
    """
    customer_account_id = current_customer["customer_account_id"]
    org_id = current_customer.get("organization_id")
    now_iso = datetime.now(timezone.utc).isoformat()

    await customer_account_repository.update(
        customer_account_id,
        {"tokens_invalidated_at": now_iso},
    )

    try:
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=customer_account_id,
            action="customer_logout_all",
            resource_type="customer_account",
            resource_id=customer_account_id,
            details={"invalidated_at": now_iso},
        ))
    except Exception:
        pass

    logger.info(
        "customer_logout_all: account=%s org=%s tokens_invalidated_at=%s",
        customer_account_id, org_id, now_iso,
    )

    return {
        "message": "Tutte le sessioni sono state terminate. Effettua di nuovo il login.",
        "invalidated_at": now_iso,
    }


@router.post("/login")
@limiter.limit("10/minute")
async def login(body: LoginRequest, request: Request):
    """Authenticate customer within an org and return JWT with org_id."""
    org_id = await _resolve_org_id(body.slug)
    try:
        result = await customer_auth_service.customer_login(
            org_id=org_id,
            email=body.email,
            password=body.password,
        )
        return result
    except ValueError as e:
        msg = str(e)
        # Track S Step 2.1: these structured errors are emitted by the
        # service ONLY after the password has been verified — they are
        # post-credential signals (UX for legitimate users) and do NOT
        # leak account existence to brute-forcers.
        if msg == "EMAIL_NOT_VERIFIED":
            raise HTTPException(
                status_code=403,
                detail={"code": "EMAIL_NOT_VERIFIED", "message": "Verifica la tua email prima di accedere."},
            )
        if msg == "ACCOUNT_DISABLED":
            raise HTTPException(
                status_code=403,
                detail={"code": "ACCOUNT_DISABLED", "message": "Account disattivato. Contatta il supporto."},
            )
        # Onda 29 — account lockout. Service raises "ACCOUNT_LOCKED:<unlock_at_iso>"
        # so the router can extract unlock_at and return a structured error
        # the frontend uses to render the live countdown UI.
        if msg.startswith("ACCOUNT_LOCKED:"):
            unlock_at_iso = msg.split(":", 1)[1]
            raise HTTPException(
                status_code=423,  # Locked (RFC 4918)
                detail={
                    "code": "ACCOUNT_LOCKED",
                    "message": "Account temporaneamente bloccato per troppi tentativi falliti.",
                    "unlock_at": unlock_at_iso,
                },
            )
        # Track S Step 2.1: ANY other ValueError → uniform 401.
        # Pre-password errors all collapse to identical body (anti-enum).
        # The service guarantees msg == "Email o password non corretti."
        # for both "email not found" and "wrong password" paths.
        raise HTTPException(
            status_code=401,
            detail="Email o password non corretti.",
        )


@router.post("/forgot-password")
# Phase 1 Step D2 — two-tier rate limit:
#   per-IP    (slowapi): 5/min + 30/hour
#   per-email (in-app):  10/hour cross-IP
@limiter.limit("5/minute;30/hour")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    """Send password reset email. Always returns 200 (prevents email enumeration)."""
    # Per-email cross-IP rate limit (anti-amplification).
    # We still return 200 even when limited, to preserve enumeration resistance:
    # a probing attacker should not be able to distinguish "email exists, limited"
    # from "email exists, not limited" via timing or response shape.
    from core.rate_limiting import check_email_rate
    if not check_email_rate(body.email, "customer_forgot_password", max_per_hour=10):
        # Silently swallow without sending: returning the standard 200 keeps the
        # public surface uniform; the request is logged + audited but no email leaves.
        import logging
        logging.getLogger(__name__).warning(
            "customer forgot-password: per-email rate limit hit (10/h cross-IP)",
        )
        return {"message": "If the email exists, a reset link has been sent."}

    org_id = await _resolve_org_id(body.slug)
    result = await customer_auth_service.customer_forgot_password(
        org_id=org_id,
        email=body.email,
        locale=body.locale,
    )
    return result


@router.post("/reset-password")
@limiter.limit("10/minute")
async def reset_password(body: ResetPasswordRequest, request: Request):
    """Validate reset token and set new password."""
    try:
        result = await customer_auth_service.customer_reset_password(
            token=body.token,
            new_password=body.new_password,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-email")
@limiter.limit("10/minute")
async def verify_email(body: VerifyEmailRequest, request: Request):
    """Consume verification token and mark email as verified."""
    try:
        result = await customer_auth_service.customer_verify_email(token=body.token)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resend-verification")
# Phase 1 Step D2 — two-tier rate limit:
#   per-IP    (slowapi): 3/min + 15/hour
#   per-email (in-app):  5/hour cross-IP
@limiter.limit("3/minute;15/hour")
async def resend_verification(body: ResendVerificationRequest, request: Request):
    """Resend email verification link within an org. Always returns 200."""
    # Per-email cross-IP rate limit. Same anti-enumeration pattern as forgot-password:
    # we keep the 200 response shape uniform whether the cap was hit or not.
    from core.rate_limiting import check_email_rate
    if not check_email_rate(body.email, "customer_resend_verification", max_per_hour=5):
        import logging
        logging.getLogger(__name__).warning(
            "customer resend-verification: per-email rate limit hit (5/h cross-IP)",
        )
        return {"message": "If the email exists, a verification link has been sent."}

    org_id = await _resolve_org_id(body.slug)
    result = await customer_auth_service.customer_resend_verification(
        org_id=org_id, email=body.email,
    )
    return result
