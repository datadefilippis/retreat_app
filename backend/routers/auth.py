import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status, Depends
from pydantic import BaseModel, EmailStr, Field
from pymongo.errors import DuplicateKeyError
from slowapi import Limiter
# Onda 27.2 — was `from slowapi.util import get_remote_address` which
# returns request.client.host (the nginx container's IP behind our
# reverse proxy in the ms-internal Docker network) and made all
# rate limits effectively global. Use our X-Forwarded-For aware
# resolver instead. See backend/core/rate_limiting.py for rationale.
from core.rate_limiting import get_real_ip
from models import (
    UserCreate, UserLogin, TokenResponse, UserResponse,
    ChangePasswordRequest, ChangePasswordResponse,
    ForgotPasswordRequest, ForgotPasswordResponse,
    ResetPasswordRequest, ResetPasswordResponse,
    VerifyEmailRequest, VerifyEmailResponse,
    ResendVerificationRequest, ResendVerificationResponse,
    AuditLog,
)
from auth import get_current_user, get_verified_user, require_admin, verify_password, get_password_hash, validate_password_strength
from services import auth_service
from repositories import user_repository, audit_repository, platform_settings_repository, invite_repository, organization_repository
from services.email_service import send_password_reset, send_welcome, send_password_changed, send_verification, send_deactivation_notice, send_invite_request_notification, send_invite_request_confirmation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Rate limiter — shared with server.py via import.
# Keyed by client IP address.
# default_limits: applies to ALL endpoints without explicit @limiter.limit() decorator.
# Endpoints with explicit limits override this default.
limiter = Limiter(key_func=get_real_ip, default_limits=["60/minute"])


@router.post("/signup", response_model=TokenResponse)
@limiter.limit("5/15minutes")
async def signup(request: Request, user_data: UserCreate):
    # Track O Step 4.1 — honeypot anti-bot check (FIRST, before any DB
    # access — bot non deve consumare resource).
    # Uniform 202 success on trigger: bot can't distinguish "caught"
    # from "succeeded" → anti-enumeration preserved.
    from core.honeypot import is_honeypot_triggered
    if is_honeypot_triggered(user_data.website):
        _hp_ip = None
        try:
            from core.rate_limiting import get_real_ip
            _hp_ip = get_real_ip(request)
        except Exception:
            pass
        _hp_ua = request.headers.get("user-agent") if request else None
        logger.warning(
            "merchant signup honeypot triggered — bot caught. "
            "email=%s ip=%s ua=%s honeypot_value=%r",
            user_data.email, _hp_ip, (_hp_ua or "")[:80],
            (user_data.website or "")[:120],
        )
        # Record metric per Sentry alert + Grafana visibility on bot volume.
        try:
            from core.observability.metrics import record_signup
            record_signup(flow="merchant", status="honeypot_triggered")
        except Exception:
            pass
        # Audit event (no org_id — signup not yet processed).
        try:
            from repositories import audit_repository
            from models import AuditLog
            await audit_repository.create(AuditLog(
                organization_id=None,
                user_id="bot",
                action="merchant_signup_honeypot",
                resource_type="user",
                resource_id=None,
                details={
                    "ip": _hp_ip,
                    "user_agent": (_hp_ua or "")[:200],
                    "email_attempted": user_data.email,
                    "honeypot_value_redacted": (user_data.website or "")[:60],
                    "source": "merchant_auth_signup",
                },
            ))
        except Exception as audit_err:
            logger.warning("merchant honeypot audit insert failed: %s", audit_err)
        # Uniform 202 success matching v6.0 verification_required path —
        # bot riceve la stessa risposta che un legitimate signup.
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=202,
            content={
                "status": "verification_required",
                "message": "Account created. Please check your email to verify your account.",
            },
        )

    # ── Controlled Access gate (v6.0) ────────────────────────────────────
    reg_mode = await platform_settings_repository.get_registration_mode()
    invite_doc = None

    if reg_mode == "invite_only":
        if not user_data.invite_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is by invitation only",
            )
        # Validate the invite token
        token_hash = hashlib.sha256(user_data.invite_token.encode()).hexdigest()
        invite_doc = await invite_repository.find_by_token_hash(token_hash)
        if not invite_doc:
            # Check if it exists but is used/revoked/expired for a better message
            any_doc = await invite_repository.find_by_token_hash_any_status(token_hash)
            if any_doc:
                detail = "Invitation has already been used or revoked"
                if any_doc.get("status") == "revoked":
                    detail = "Invitation has been revoked"
            else:
                detail = "Invalid or expired invitation"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )
        if invite_doc["email"].lower() != user_data.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email does not match invitation",
            )

    # ── Original signup logic ────────────────────────────────────────────
    # Wave GDPR-Admin Phase B (2026-05-16) — pass the request's IP and
    # User-Agent through to auth_service.signup so consent_audit_repository
    # can record the network context of the acceptance. Both are optional;
    # missing values just store None.
    _req_ip = None
    try:
        from core.rate_limiting import get_real_ip
        _req_ip = get_real_ip(request)
    except Exception:
        # Best-effort: missing IP does not block signup. The user doc
        # still carries accepted_terms_version/locale as primary evidence.
        pass
    _user_agent = request.headers.get("user-agent") if request else None

    try:
        result = await auth_service.signup(
            user_data, request_ip=_req_ip, user_agent=_user_agent,
        )
    except ValueError as e:
        # v5.8 / Onda 9.Z Step C — recognize the most common ValueError
        # variants from auth_service.signup and surface them as structured
        # 409 with a `code` so the frontend can render localized copy.
        # Other ValueErrors fall through to the generic 400 (which keeps
        # backward compat for password-strength messages, terms-acceptance
        # messages, etc. — all of which are already in Italian).
        msg = str(e)
        if msg == "Email already registered":
            # Track O Step 3.3 — record duplicate (high-signal funnel datapoint)
            try:
                from core.observability.metrics import record_signup
                record_signup(flow="merchant", status="duplicate")
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EMAIL_ALREADY_REGISTERED",
                    "message": "Questa email è già registrata. Prova a fare login o a recuperare la password.",
                    "field": "email",
                },
            )
        # Track O Step 3.3 — record validation_failed (password weak, etc)
        try:
            from core.observability.metrics import record_signup
            record_signup(flow="merchant", status="validation_failed")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)  # controlled messages from auth_service
        )
    except DuplicateKeyError as e:
        # v5.8 / Onda 9.Z Step C — distinguish DB unique-violation classes
        # so the user gets a clean 409 with i18n-keyed message instead of
        # the previous opaque 500. Pre-9.Z this branch was hit on every
        # signup-after-the-first because of the public_slug bug; with the
        # Step A index migration that case is gone, but legitimate
        # duplicates (email re-use, slug collision) are still possible.
        # Track O Step 3.3 — record duplicate (any DB unique violation maps
        # to status='duplicate' for the funnel chart; field details only in
        # logs to keep metric cardinality low).
        try:
            from core.observability.metrics import record_signup
            record_signup(flow="merchant", status="duplicate")
        except Exception:
            pass
        details = e.details or {}
        key_pattern = details.get("keyPattern") or {}
        field = next(iter(key_pattern), None) if key_pattern else None
        if field == "email":
            logger.info("signup conflict on email (already registered): %s", user_data.email)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "EMAIL_ALREADY_REGISTERED",
                    "message": "Questa email è già registrata. Prova a fare login o a recuperare la password.",
                    "field": "email",
                },
            )
        if field == "public_slug":
            # Should NEVER happen post-Step A index migration. If it does,
            # log loudly so we know to investigate (e.g. concurrent signup
            # collision on the same slug, which would require a slug being
            # passed in — currently never the case during signup).
            logger.error(
                "signup conflict on public_slug (UNEXPECTED — index should "
                "have prevented this): %s", e,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "REGISTRATION_CONFLICT",
                    "message": "Conflitto di registrazione. Riprova fra qualche istante.",
                },
            )
        # Generic duplicate (some other unique field): tell the user, log
        # the field name so we can extend this handler later if needed.
        logger.warning("signup duplicate on field=%s: %s", field, e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REGISTRATION_CONFLICT",
                "message": "Conflitto di registrazione. Verifica i dati e riprova.",
                "field": field,
            },
        )
    except Exception as e:
        logger.error("signup failed: %s", e, exc_info=True)
        # Track O Step 3.3 — record generic error (unexpected 500)
        try:
            from core.observability.metrics import record_signup
            record_signup(flow="merchant", status="error")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante la registrazione. Riprova più tardi.",
        )

    # Track O Step 3.3 — record success (account created, awaiting verification)
    try:
        from core.observability.metrics import record_signup
        record_signup(flow="merchant", status="success")
    except Exception:
        pass

    # Mark invite as used + auto-verify email after successful signup
    if invite_doc:
        try:
            await invite_repository.mark_used(invite_doc["id"])
            # Auto-verify: admin already validated this email by sending the invite
            await user_repository.update(
                result.user.id,
                {"email_verified": True},
            )
        except Exception:
            pass
        return result

    # v6.0: Open registration — email verification required before access.
    # Don't return the JWT; instead return 202 with verification message.
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=202,
        content={
            "status": "verification_required",
            "message": "Account created. Please check your email to verify your account.",
        },
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, credentials: UserLogin):
    try:
        return await auth_service.login(credentials.email, credentials.password)
    except ValueError as e:
        msg = str(e)
        # v6.0: Account deactivated — parse role and deactivated_at from message
        if msg.startswith("Account deactivated|"):
            parts = msg.split("|")
            role = parts[1] if len(parts) > 1 else "user"
            deactivated_at_str = parts[2] if len(parts) > 2 else None
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Account deactivated",
                    "deactivated_at": deactivated_at_str,
                    "is_org_admin": role == "admin",
                },
            )
        if "deactivated" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=msg,
            )
        if "not verified" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified",
            )
        # Onda 30 — admin/owner per-account lockout. Service raises
        # "ACCOUNT_LOCKED:<unlock_at_iso>" so we can extract unlock_at
        # and return a structured 423 the frontend uses to render the
        # live countdown UI. Mirror of the customer_auth router branch.
        # Track S Step 2.1: lockout fires only AFTER password verify, so
        # 423 here is safe (post-credential, no enumeration leak).
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
        # Track S Step 2.1 — ANY other ValueError pre-password (email not
        # found, wrong password) → uniform 401 with identical body bytes.
        # Service guarantees msg == "Invalid email or password" for both
        # paths (anti-enumeration).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    except Exception as e:
        logger.error("login failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante il login. Riprova più tardi.",
        )


# Onda 28 — WHITELIST: /me must remain callable by users who haven't
# verified their email yet, so the frontend can poll it to detect the
# moment verification completes (and so VerifyEmailRequiredPage can
# read the user's locale/email). Keep get_current_user, NOT get_verified_user.
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    try:
        return await auth_service.get_current_user_info(current_user['user_id'])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)  # controlled message from auth_service
        )
    except Exception as e:
        logger.error("get_me failed for user=%s: %s", current_user.get("user_id"), e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nel recupero del profilo utente.",
        )


SUPPORTED_LOCALES = {"it", "en", "de", "fr"}


# Onda 28 — WHITELIST: an unverified user must be able to switch their
# UI language so the verify-email-required screen displays in the right
# language. Keep get_current_user.
@router.patch("/locale")
async def update_locale(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Update the authenticated user's interface locale.

    Accepts: { "locale": "it" | "en" | "de" | "fr" }
    Validates against SUPPORTED_LOCALES.  Persists to user document.
    """
    from pydantic import BaseModel, Field

    class LocaleRequest(BaseModel):
        locale: str = Field(min_length=2, max_length=5)

    body = LocaleRequest(**(await request.json()))

    if body.locale not in SUPPORTED_LOCALES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported locale '{body.locale}'. Allowed: {', '.join(sorted(SUPPORTED_LOCALES))}",
        )

    from repositories import user_repository
    await user_repository.update(current_user["user_id"], {"locale": body.locale})

    return {"locale": body.locale, "message": "Locale updated"}


# ── Wave GDPR-Admin Phase E (2026-05-18) — re-consent endpoint ────────────
#
# When CURRENT_VERSION_TAG in core/legal_versions.py bumps (e.g. v1.0 → v1.1)
# the /auth/me response carries ``consent_needs_refresh=True`` for every
# existing user whose ``accepted_terms_version`` is stale. The frontend
# renders a blocking modal that calls this endpoint on user confirmation.
#
# WHITELIST get_current_user (not get_verified_user) — an unverified user
# whose docs got bumped while they were mid-verify should still be able
# to re-accept; we don't want to lock them out twice.

@router.post("/re-consent")
async def re_consent(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Record a user's re-acceptance of the current Privacy + Terms bundle.

    Body: ``{ "locale": "it" | "en" | "de" | "fr" }``  (locale at acceptance)

    Effects (atomic-ish — see note below):
      1. Append an immutable record to ``consent_audit`` with
         source="re_acceptance" — the legal proof trail.
      2. Update the user document's ``accepted_terms_version``,
         ``accepted_terms_locale`` and ``accepted_terms_at`` to mirror
         what was just accepted.

    Atomicity note: the consent_audit insert is the LEGAL record (immutable,
    TTL-bounded). The user-doc update is the FRONTEND signal (it stops the
    blocking modal from re-appearing). If step 2 fails after step 1 succeeds,
    the user re-sees the modal on next reload — annoying but safe; double
    acceptance is fine, no data loss. The reverse failure mode (user-doc
    updated, audit lost) would be the dangerous one — so we record the
    audit FIRST.

    Returns the updated UserResponse so the frontend can refresh its
    auth context state without an extra /auth/me roundtrip.
    """
    from pydantic import BaseModel, Field
    from core.legal_versions import (
        CURRENT_VERSION_TAG,
        CURRENT_VERSION_HASH,
        current_version_string,
    )
    from repositories import consent_audit_repository, user_repository

    class ReConsentRequest(BaseModel):
        locale: str = Field(min_length=2, max_length=5)

    body = ReConsentRequest(**(await request.json()))

    if body.locale not in SUPPORTED_LOCALES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported locale '{body.locale}'. "
                f"Allowed: {', '.join(sorted(SUPPORTED_LOCALES))}"
            ),
        )

    user_id = current_user["user_id"]
    user_doc = await user_repository.find_by_id(user_id)
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente non trovato",
        )

    # Extract IP + User-Agent for the audit trail (best-effort; both fields
    # are nullable in consent_audit so missing values are fine).
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Step 1 — record the immutable consent audit FIRST.
    try:
        await consent_audit_repository.record_consent(
            user_id=user_id,
            locale=body.locale,
            version_tag=CURRENT_VERSION_TAG,
            version_hash=CURRENT_VERSION_HASH,
            ip_address=client_ip,
            user_agent=user_agent,
            organization_id=user_doc.get("organization_id"),
            source="re_acceptance",
            document_type="privacy_terms",
        )
    except Exception as e:
        logger.error(
            "re_consent: consent_audit insert failed for user=%s: %s",
            user_id, e, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Impossibile registrare l'accettazione in questo momento. "
                "Riprova fra qualche secondo."
            ),
        )

    # Step 2 — update the user doc so the modal stops appearing.
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        await user_repository.update(
            user_id,
            {
                "accepted_terms_version": current_version_string(),
                "accepted_terms_locale": body.locale,
                "accepted_terms_at": now_iso,
            },
        )
    except Exception as e:
        # Audit already in. Log loudly; the modal will re-appear on next
        # reload and the user will accept again (idempotent).
        logger.error(
            "re_consent: user-doc update failed for user=%s after audit "
            "succeeded (modal will re-appear on next reload): %s",
            user_id, e, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Accettazione registrata ma profilo non aggiornato. "
                "Ricarica la pagina."
            ),
        )

    # Return the fresh UserResponse — frontend updates its auth context.
    try:
        return await auth_service.get_current_user_info(user_id)
    except Exception as e:
        logger.error(
            "re_consent: failed to reload UserResponse after re-accept "
            "for user=%s: %s", user_id, e, exc_info=True,
        )
        # Acceptance succeeded; just return a minimal OK envelope.
        return {
            "status": "ok",
            "accepted_terms_version": current_version_string(),
            "accepted_terms_locale": body.locale,
            "accepted_terms_at": now_iso,
            "consent_needs_refresh": False,
        }


# Onda 28 — WHITELIST: change-password is an operational recovery
# endpoint and must remain callable by unverified users (e.g. someone
# who registered with a typo'd email needs to recover). Keep get_current_user.
@router.put("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Change the authenticated user's own password.

    Requires the current password for verification.
    New password must be at least 8 characters (enforced by Pydantic).
    Records an audit log entry on success.
    The current session token is preserved after the change (see inline comment).
    """
    # 1. Load current user document
    user_doc = await user_repository.find_by_id(current_user["user_id"])
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente non trovato",
        )

    # 2. Verify the supplied current password.
    # NOTE: use 400 (not 401) so the frontend axios interceptor does not treat
    # this as a session-expiry and log the user out.
    if not verify_password(body.current_password, user_doc["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password attuale non corretta",
        )

    # 3. Validate new password complexity, then hash and persist.
    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Track O Step 4.2 — anti credential-stuffing on password change.
    try:
        from core.password_breach import validate_password_not_breached
        validate_password_not_breached(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # password_changed_at must equal the current token's iat (Unix int converted to
    # ISO) so that the check `token_iat < int(pcat_dt.timestamp())` in
    # get_current_user() evaluates to FALSE for this exact token, preserving the
    # current session.  All older tokens (iat < pcat) are still invalidated.
    # Falls back to "now" only if token_iat is absent (legacy tokens without iat).
    # must_change_password is cleared: first-login / admin-reset obligation fulfilled.
    new_hash = get_password_hash(body.new_password)
    now_iso = datetime.now(timezone.utc).isoformat()
    token_iat = current_user.get("token_iat")
    if token_iat is not None:
        pcat_iso = datetime.fromtimestamp(token_iat, tz=timezone.utc).isoformat()
    else:
        pcat_iso = now_iso  # fallback: no iat in token, no current session to preserve
    await user_repository.update(
        current_user["user_id"],
        {
            "password_hash": new_hash,
            "password_changed_at": pcat_iso,
            "updated_at": now_iso,
            "must_change_password": False,
        },
    )

    # 4. Audit log (non-blocking — failure must not abort the request)
    try:
        await audit_repository.create(AuditLog(
            organization_id=current_user.get("organization_id"),
            user_id=current_user["user_id"],
            action="change_password",
            resource_type="user",
            resource_id=current_user["user_id"],
        ))
    except Exception:
        pass

    # Notify the user via email (non-blocking)
    try:
        send_password_changed(user_doc["email"], user_doc.get("name", ""), locale=user_doc.get("locale", "it"))
    except Exception:
        pass

    return ChangePasswordResponse(message="Password aggiornata con successo")


# ────────────────────────────────────────────────────────────────────────────
# Track O Step 4.3 — Logout-all-sessions panic button
# ────────────────────────────────────────────────────────────────────────────
#
# Use case: utente sospetta session hijack OR ha lasciato login su shared
# device OR ha venduto laptop. Vuole invalidare tutti i token attivi
# SENZA cambio password.
#
# Implementazione: set tokens_invalidated_at = now ISO. get_current_user()
# rifiuta ogni token con iat < now → tutti i device loggati out istantaneo.
# Il token corrente (di chi invoca l'endpoint) e' ANCHE invalidato — user
# deve fare di nuovo login. Trade-off accettato: UX richiede re-login,
# ma security garanzia 100% (no surface attack di "lasciar valido solo
# il device corrente" che sarebbe vulnerabile a token theft post-call).


@router.post("/logout-all", status_code=200)
@limiter.limit("10/hour")
async def logout_all(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Invalidate ALL active sessions for the current user.

    Sets tokens_invalidated_at = now in DB → ogni token con iat anteriore
    viene rifiutato da get_current_user. Anche il token con cui l'utente
    chiama questo endpoint diventa invalido (re-login required).

    Use cases:
      - Sospetto compromise account
      - Forgot to logout on shared device
      - Sold/lost device

    Audit: action='logout_all', resource_type='user'.
    Rate limit: 10/hour per IP (no abuse vector ma cap defensive).
    """
    user_id = current_user["user_id"]
    now_iso = datetime.now(timezone.utc).isoformat()

    await user_repository.update(
        user_id,
        {"tokens_invalidated_at": now_iso},
    )

    # Audit log (non-blocking)
    try:
        await audit_repository.create(AuditLog(
            organization_id=current_user.get("organization_id"),
            user_id=user_id,
            action="logout_all",
            resource_type="user",
            resource_id=user_id,
            details={"invalidated_at": now_iso},
        ))
    except Exception:
        pass

    logger.info(
        "logout_all: user=%s tokens_invalidated_at=%s",
        user_id, now_iso,
    )

    return {
        "message": "Tutte le sessioni sono state terminate. Effettua di nuovo il login.",
        "invalidated_at": now_iso,
    }


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
# Phase 1 Step D2 — two-tier rate limit:
#   per-IP    (slowapi): 5/min + 30/hour → blocks burst + slow brute force
#   per-email (in-app):  10/hour cross-IP → blocks botnet amplification
@limiter.limit("5/minute;30/hour")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    """
    Initiate a password-reset flow.

    Always returns HTTP 200 with a generic message to prevent email enumeration.
    In ENVIRONMENT=development, also returns dev_reset_url with the plaintext token
    so testers can complete the flow without an SMTP provider.
    In production the dev_reset_url field is omitted and an email would be sent instead.
    """
    _GENERIC = (
        "Se l'indirizzo è registrato, riceverai le istruzioni per "
        "reimpostare la password."
    )

    # Phase 1 Step D2 — per-email cross-IP rate limit (10/h).
    # Returns generic 200 to preserve enumeration resistance even when limited.
    from core.rate_limiting import check_email_rate
    if not check_email_rate(body.email, "admin_forgot_password", max_per_hour=10):
        logger.warning(
            "admin forgot-password: per-email rate limit hit (10/h cross-IP) for %s",
            body.email[:3] + "***",  # partial mask in logs
        )
        return ForgotPasswordResponse(message=_GENERIC)

    user_doc = await user_repository.find_by_email(body.email)
    if not user_doc:
        # Prevent email enumeration — always return the same message.
        return ForgotPasswordResponse(message=_GENERIC)

    # Generate a one-time token; store only its SHA-256 hash in the DB.
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_iso = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    await user_repository.update(
        user_doc["id"],
        {
            "reset_token_hash": token_hash,
            "reset_token_expires": expires_iso,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Audit log (non-blocking)
    try:
        await audit_repository.create(AuditLog(
            organization_id=user_doc.get("organization_id"),
            user_id=user_doc["id"],
            action="forgot_password_request",
            resource_type="user",
            resource_id=user_doc["id"],
        ))
    except Exception:
        pass

    # Send reset email (non-blocking — failure must not affect the response)
    try:
        send_password_reset(user_doc["email"], token, locale=user_doc.get("locale", "it"))
    except Exception:
        logger.error("forgot_password: email send failed for user=%s", user_doc["id"], exc_info=True)

    # Dev mode: also expose the token URL so the pilot can test without SMTP.
    if os.environ.get("ENVIRONMENT", "development") == "development":
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        dev_reset_url = f"{frontend_url}/reset-password?token={token}"
        return ForgotPasswordResponse(message=_GENERIC, dev_reset_url=dev_reset_url)

    return ForgotPasswordResponse(message=_GENERIC)


@router.post("/reset-password", response_model=ResetPasswordResponse)
@limiter.limit("10/minute")
async def reset_password(request: Request, body: ResetPasswordRequest):
    """
    Complete the password-reset flow.
    Validates the one-time token, resets the password, clears must_change_password.
    Token is single-use and expires in 1 hour.
    """
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    user_doc = await user_repository.find_by_reset_token_hash(token_hash)

    if not user_doc:
        # Track S Step 2.3 — detection log for token consumption attempt
        # that failed (invalid, already used post null-out, or expired).
        # Mirror of customer_auth_service log; SOC alerts on per-IP spike.
        logger.info(
            "admin reset_password: token consumption failed (invalid, "
            "already used, or expired). token_hash_prefix=%s",
            token_hash[:8],
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token non valido o scaduto.",
        )

    # Verify token has not expired.
    expires_str = user_doc.get("reset_token_expires")
    if not expires_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token non valido o scaduto.",
        )
    try:
        expires_dt = datetime.fromisoformat(expires_str)
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token non valido o scaduto.",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token non valido o scaduto.",
        )

    # Validate new password complexity before hashing.
    try:
        validate_password_strength(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Track O Step 4.2 — anti credential-stuffing on password reset.
    try:
        from core.password_breach import validate_password_not_breached
        validate_password_not_breached(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Hash the new password and persist; invalidate old tokens via password_changed_at.
    new_hash = get_password_hash(body.new_password)
    now_iso = datetime.now(timezone.utc).isoformat()
    await user_repository.update(
        user_doc["id"],
        {
            "password_hash": new_hash,
            "password_changed_at": now_iso,
            "updated_at": now_iso,
            "must_change_password": False,
            # Consume the token so it cannot be reused.
            "reset_token_hash": None,
            "reset_token_expires": None,
            # Onda 30 — successful password reset implies the user has
            # demonstrated control of their email inbox; treat that as
            # equivalent proof of identity to a successful login and
            # clear all anti-bruteforce state. Without this, a user
            # who locked themselves out by mistyping passwords would
            # still be locked even after recovering via the email
            # reset flow. Mirror of Onda 29 Step 3 on customer side.
            "failed_login_attempts": 0,
            "locked_until": None,
            "lockout_count_today": 0,
        },
    )

    # Audit log (non-blocking)
    try:
        await audit_repository.create(AuditLog(
            organization_id=user_doc.get("organization_id"),
            user_id=user_doc["id"],
            action="reset_password",
            resource_type="user",
            resource_id=user_doc["id"],
        ))
    except Exception:
        pass

    return ResetPasswordResponse(
        message="Password reimpostata con successo. Puoi ora accedere con la nuova password."
    )


@router.post("/verify-email", response_model=VerifyEmailResponse)
@limiter.limit("10/minute")
async def verify_email(request: Request, body: VerifyEmailRequest):
    """
    Verify user email via one-time token.

    The token is sent in the welcome email at signup. It is single-use and
    expires after 24 hours. SHA-256 hash comparison (same pattern as password
    reset). Login is NOT blocked for unverified users — this is informational
    for now.
    """
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    user_doc = await user_repository.find_by_verification_token_hash(token_hash)

    if not user_doc:
        # Track S Step 2.3 — detection log (same rationale as reset).
        logger.info(
            "admin verify_email: token consumption failed (invalid, "
            "already used, or expired). token_hash_prefix=%s",
            token_hash[:8],
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token di verifica non valido o scaduto.",
        )

    # Check if already verified (idempotent)
    if user_doc.get("email_verified", False):
        return VerifyEmailResponse(message="Email già verificata.")

    # Verify token has not expired
    expires_str = user_doc.get("verification_token_expires")
    if not expires_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token di verifica non valido o scaduto.",
        )
    try:
        expires_dt = datetime.fromisoformat(expires_str)
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token di verifica scaduto. Richiedi un nuovo link di verifica.",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token di verifica non valido o scaduto.",
        )

    # Mark email as verified, consume the token
    now_iso = datetime.now(timezone.utc).isoformat()
    await user_repository.update(
        user_doc["id"],
        {
            "email_verified": True,
            "verification_token_hash": None,
            "verification_token_expires": None,
            "updated_at": now_iso,
        },
    )

    # Audit log (non-blocking)
    try:
        await audit_repository.create(AuditLog(
            organization_id=user_doc.get("organization_id"),
            user_id=user_doc["id"],
            action="verify_email",
            resource_type="user",
            resource_id=user_doc["id"],
        ))
    except Exception:
        pass

    return VerifyEmailResponse(message="Email verificata con successo!")


@router.post("/resend-verification", response_model=ResendVerificationResponse)
# Phase 1 Step D2 — two-tier rate limit:
#   per-IP    (slowapi): 3/min + 15/hour
#   per-email (in-app):  5/hour cross-IP
@limiter.limit("3/minute;15/hour")
async def resend_verification(request: Request, body: ResendVerificationRequest):
    """
    Resend email verification link.

    Always returns HTTP 200 with a generic message to prevent email enumeration.
    Generates a fresh token (invalidates the previous one).
    """
    _GENERIC = (
        "Se l'indirizzo è registrato e non ancora verificato, "
        "riceverai un nuovo link di verifica."
    )

    # Phase 1 Step D2 — per-email cross-IP rate limit (5/h).
    from core.rate_limiting import check_email_rate
    if not check_email_rate(body.email, "admin_resend_verification", max_per_hour=5):
        logger.warning(
            "admin resend-verification: per-email rate limit hit (5/h cross-IP) for %s",
            body.email[:3] + "***",
        )
        return ResendVerificationResponse(message=_GENERIC)

    user_doc = await user_repository.find_by_email(body.email)
    if not user_doc:
        # Prevent email enumeration
        return ResendVerificationResponse(message=_GENERIC)

    # Already verified — nothing to do
    if user_doc.get("email_verified", False):
        return ResendVerificationResponse(message=_GENERIC)

    # Generate a new token, invalidating the previous one
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_iso = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    await user_repository.update(
        user_doc["id"],
        {
            "verification_token_hash": token_hash,
            "verification_token_expires": expires_iso,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Send verification email (non-blocking)
    try:
        send_verification(user_doc["email"], token, locale=user_doc.get("locale", "it"))
    except Exception:
        logger.error("resend_verification: email send failed for user=%s", user_doc["id"], exc_info=True)

    # Audit log (non-blocking)
    try:
        await audit_repository.create(AuditLog(
            organization_id=user_doc.get("organization_id"),
            user_id=user_doc["id"],
            action="resend_verification",
            resource_type="user",
            resource_id=user_doc["id"],
        ))
    except Exception:
        pass

    return ResendVerificationResponse(message=_GENERIC)


# ── Controlled Access: Public endpoints (v6.0) ───────────────────────────────


@router.get("/registration-mode")
@limiter.limit("30/minute")
async def get_registration_mode(request: Request) -> dict:
    """Public endpoint — returns current registration mode.

    No authentication required. Used by the frontend to decide
    whether to show the signup form or an invite-only message.
    """
    mode = await platform_settings_repository.get_registration_mode()
    return {"registration_mode": mode}


class InviteRequestBody(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    business: str = Field(min_length=2, max_length=200)
    locale: str = "it"


@router.post("/request-invite", status_code=202)
@limiter.limit("3/hour")
async def request_invite(request: Request, body: InviteRequestBody):
    """Public endpoint — submit an invite request (no auth).

    Sends a notification email to the platform admin and a confirmation
    to the applicant. Always returns 202 to prevent email enumeration.

    Track S Step 2.5: per-email cross-IP rate limit (3/h) as backstop
    to the per-IP slowapi limit (3/h). An attacker with botnet bombing
    the same email cannot multiply throughput via N IPs. Always 202
    even when rate-limited to preserve anti-enumeration.
    """
    locale = body.locale if body.locale in {"it", "en", "de", "fr"} else "it"

    # Per-email cross-IP cap (in addition to per-IP slowapi).
    from core.rate_limiting import check_email_rate
    if not check_email_rate(body.email, "admin_request_invite", max_per_hour=3):
        logger.info(
            "request_invite: per-email rate limit hit (3/h cross-IP) for %s",
            (body.email[:3] + "***" + body.email[body.email.find("@"):])
            if "@" in body.email else "***",
        )
        # Anti-enumeration: same 202 body as success path. Attacker
        # cannot distinguish rate-limit hit from successful invite request.
        return {"status": "sent"}

    try:
        send_invite_request_notification(body.name, body.email, body.business)
        send_invite_request_confirmation(body.email, body.name, locale=locale)
    except Exception:
        logger.error("request_invite: email send failed for %s", body.email, exc_info=True)
    return {"status": "sent"}


class _ValidateInviteResponse(BaseModel):
    valid: bool
    email: Optional[str] = None


@router.get("/validate-invite", response_model=_ValidateInviteResponse)
@limiter.limit("10/minute")
async def validate_invite(request: Request, token: str = "") -> _ValidateInviteResponse:
    """Public endpoint — check if an invite token is valid.

    Does NOT consume the token. Returns the invited email if valid.
    """
    if not token:
        return _ValidateInviteResponse(valid=False)

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    doc = await invite_repository.find_by_token_hash(token_hash)
    if not doc:
        return _ValidateInviteResponse(valid=False)

    return _ValidateInviteResponse(valid=True, email=doc["email"])


# ── Account Deactivation & Reactivation (v6.0, GDPR art. 17) ─────────────────

from database import (
    organizations_collection, users_collection, sales_records_collection,
    purchase_records_collection, expense_records_collection, fixed_costs_collection,
    customers_collection, suppliers_collection, products_collection,
    datasets_collection, chat_sessions_collection,
)
from datetime import timedelta as _timedelta
import asyncio as _asyncio


class _DeactivateBody(BaseModel):
    password: str


@router.post("/deactivate-account")
@limiter.limit("3/minute")
async def deactivate_account(
    request: Request,
    body: _DeactivateBody,
    current_user: dict = Depends(require_admin),
):
    """Self-service account deactivation. Requires admin role + password confirmation.

    Deactivates the entire organization. After 30 days, all data is permanently deleted
    by the background hard-delete job. The admin can reactivate within 30 days.
    """
    org_id = current_user["organization_id"]
    user_id = current_user["user_id"]

    # 1. Verify password
    user_doc = await user_repository.find_by_id(user_id)
    if not user_doc or not verify_password(body.password, user_doc["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
        )

    # 2. Load org
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if org_doc.get("deactivated_at"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account already deactivated")

    # 3. Cancel Stripe subscription if present
    stripe_sub_id = org_doc.get("stripe_subscription_id")
    if stripe_sub_id:
        try:
            import stripe as _stripe
            _stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
            if _stripe.api_key:
                await _asyncio.to_thread(_stripe.Subscription.cancel, stripe_sub_id)
                logger.info("deactivate_account: cancelled Stripe sub %s for org %s", stripe_sub_id, org_id)
        except Exception as e:
            logger.warning("deactivate_account: failed to cancel Stripe sub %s: %s", stripe_sub_id, e)

    # 4. Set deactivated_at + is_active=False on org
    now = datetime.now(timezone.utc)
    deletion_date = now + _timedelta(days=30)
    await organizations_collection.update_one(
        {"id": org_id},
        {"$set": {
            "deactivated_at": now,
            "is_active": False,
            "billing_status": "canceled",
            "stripe_subscription_id": None,
            "updated_at": now.isoformat(),
        }},
    )

    # 5. Deactivate all users in this org
    await users_collection.update_many(
        {"organization_id": org_id},
        {"$set": {"is_active": False}},
    )

    # 6. Notify all org members via email (non-blocking)
    try:
        org_name = org_doc.get("name", "")
        deletion_date_str = deletion_date.strftime("%d/%m/%Y")
        members = await user_repository.find_by_org(org_id)
        for member in members:
            try:
                send_deactivation_notice(member["email"], org_name, deletion_date_str, locale=member.get("locale", "it"))
            except Exception:
                pass
    except Exception as e:
        logger.warning("deactivate_account: email notification failed: %s", e)

    # 7. Audit log
    try:
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="deactivate_account",
            resource_type="organization",
            resource_id=org_id,
            details={"org_name": org_doc.get("name"), "deletion_date": deletion_date.isoformat()},
        ))
    except Exception:
        pass

    return {
        "message": "Account deactivated",
        "deactivated_at": now.isoformat(),
        "reactivation_deadline": deletion_date.isoformat(),
    }


# ── Reactivation lockout (in-memory, single server) ──────────────────────────

_reactivation_attempts: dict = {}  # {"email": {"count": int, "locked_until": datetime | None}}
_LOCKOUT_THRESHOLD = 5
_LOCKOUT_DURATION = _timedelta(minutes=15)


def _check_lockout(email: str) -> bool:
    """Return True if the email is currently locked out. Cleans expired entries."""
    now = datetime.now(timezone.utc)
    # Clean expired entries
    expired = [k for k, v in _reactivation_attempts.items()
               if v.get("locked_until") and v["locked_until"] < now]
    for k in expired:
        del _reactivation_attempts[k]

    entry = _reactivation_attempts.get(email)
    if not entry:
        return False
    if entry.get("locked_until") and entry["locked_until"] > now:
        return True
    return False


def _record_failed_attempt(email: str):
    """Record a failed reactivation attempt. Lock after threshold."""
    now = datetime.now(timezone.utc)
    entry = _reactivation_attempts.get(email, {"count": 0, "locked_until": None})
    entry["count"] = entry.get("count", 0) + 1
    if entry["count"] >= _LOCKOUT_THRESHOLD:
        entry["locked_until"] = now + _LOCKOUT_DURATION
    _reactivation_attempts[email] = entry


def _clear_lockout(email: str):
    """Clear lockout after successful reactivation."""
    _reactivation_attempts.pop(email, None)


class _ReactivateBody(BaseModel):
    email: str
    password: str


_REACTIVATE_GENERIC = "If this account exists and is eligible for reactivation, it has been reactivated."


@router.post("/reactivate-account")
@limiter.limit("3/hour")
async def reactivate_account(request: Request, body: _ReactivateBody):
    """Reactivate a deactivated account within the 30-day grace period.

    No auth required (user can't login while deactivated). Only org admins can reactivate.
    Uses in-memory lockout after 5 failed attempts per email (15 min cooldown).
    """
    email_lower = body.email.lower().strip()

    # Check lockout
    if _check_lockout(email_lower):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
        )

    # Find user + verify password
    user_doc = await user_repository.find_by_email(email_lower)
    if not user_doc or not verify_password(body.password, user_doc["password_hash"]):
        _record_failed_attempt(email_lower)
        # Generic response — don't reveal if email exists
        return {"message": _REACTIVATE_GENERIC}

    # Must be admin
    if user_doc.get("role") != "admin":
        _record_failed_attempt(email_lower)
        return {"message": _REACTIVATE_GENERIC}

    org_id = user_doc.get("organization_id")
    if not org_id:
        _record_failed_attempt(email_lower)
        return {"message": _REACTIVATE_GENERIC}

    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc or not org_doc.get("deactivated_at"):
        _record_failed_attempt(email_lower)
        return {"message": _REACTIVATE_GENERIC}

    # Check 30-day grace period
    deactivated_at = org_doc["deactivated_at"]
    if isinstance(deactivated_at, str):
        deactivated_at = datetime.fromisoformat(deactivated_at)
    if deactivated_at.tzinfo is None:
        deactivated_at = deactivated_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    if now > deactivated_at + _timedelta(days=30):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This account has been permanently deleted and cannot be recovered.",
        )

    # ── Reactivate ────────────────────────────────────────────────────────
    # 1. Reset deactivated_at, re-enable org
    await organizations_collection.update_one(
        {"id": org_id},
        {"$set": {
            "deactivated_at": None,
            "is_active": True,
            "updated_at": now.isoformat(),
        }},
    )

    # 2. Re-enable all users in org
    await users_collection.update_many(
        {"organization_id": org_id},
        {"$set": {"is_active": True}},
    )

    # 3. Re-provision free plan
    try:
        from services.plan_provisioning import provision_commercial_plan
        await provision_commercial_plan(
            org_id=org_id,
            plan_slug="retreat_free",   # O1: baseline del verticale ritiri
            assigned_by="reactivation",
            billing_status="none",
        )
    except Exception as e:
        logger.warning("reactivate_account: failed to provision free plan for org %s: %s", org_id, e)

    # 4. Audit log
    try:
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=user_doc["id"],
            action="reactivate_account",
            resource_type="organization",
            resource_id=org_id,
        ))
    except Exception:
        pass

    # 5. Clear lockout + return token (auto-login)
    _clear_lockout(email_lower)

    from auth import create_access_token
    created_at = user_doc["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)

    token = create_access_token({
        "sub": user_doc["id"],
        "org_id": org_id,
        "role": user_doc["role"],
        "email": user_doc["email"],
    })

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_doc["id"],
            email=user_doc["email"],
            name=user_doc.get("name", ""),
            role=user_doc["role"],
            organization_id=org_id,
            created_at=created_at,
            is_active=True,
            email_verified=user_doc.get("email_verified", False),
            locale=user_doc.get("locale", "it"),
        ),
    )


# ── Account Data Summary (v6.0) ──────────────────────────────────────────────


@router.get("/account-data-summary")
async def get_account_data_summary(
    current_user: dict = Depends(require_admin),
) -> dict:
    """Return counts of all org-scoped data. Used by the deactivation dialog
    to show the user what will be permanently deleted."""
    org_id = current_user["organization_id"]
    f = {"organization_id": org_id}

    return {
        "sales_count": await sales_records_collection.count_documents(f),
        "purchases_count": await purchase_records_collection.count_documents(f),
        "expenses_count": await expense_records_collection.count_documents(f),
        "fixed_costs_count": await fixed_costs_collection.count_documents(f),
        "customers_count": await customers_collection.count_documents(f),
        "suppliers_count": await suppliers_collection.count_documents(f),
        "products_count": await products_collection.count_documents(f),
        "datasets_count": await datasets_collection.count_documents(f),
        "chat_sessions_count": await chat_sessions_collection.count_documents(f),
    }


# ── GDPR Data Export (art. 20 — Data Portability) ─────────────────────────────

from starlette.responses import StreamingResponse as _StreamingResponse


@router.get("/export-data")
@limiter.limit("3/hour")
async def export_data(
    request: Request,
    current_user: dict = Depends(require_admin),
):
    """Export ALL organization data as a ZIP file containing JSON files.

    GDPR art. 20 — right to data portability. Rate limited to 3/hour.
    Each JSON file uses a strict whitelist of fields (no sensitive data).
    """
    org_id = current_user["organization_id"]
    user_id = current_user["user_id"]

    from services.gdpr_export_service import build_gdpr_export_zip
    zip_bytes = await build_gdpr_export_zip(org_id, user_id)

    # Build filename
    org_doc = await organization_repository.find_by_id(org_id)
    org_name = (org_doc.get("name", "org") if org_doc else "org").replace(" ", "_")[:30]
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"afianco_export_{org_name}_{date_str}.zip"

    # Audit log
    try:
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="gdpr_export_data",
            resource_type="organization",
            resource_id=org_id,
        ))
    except Exception:
        pass

    return _StreamingResponse(
        iter([zip_bytes]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
