"""
Auth Service — Phase 2 + v5.9 signup provisioning.

Changes (all backward-compatible):
  - last_login_at stamped on user document at login time.
  - schema_version="2.0" written to new Organization and User documents.
  - Email verification: signup generates a one-time token, stored as SHA-256 hash.
  - v5.9: signup now calls provision_commercial_plan("free") to create the 4 free-tier
    module subscriptions, ensuring new orgs have consistent billing state from day one.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

from models import (
    UserCreate, User, UserResponse, TokenResponse,
    Organization, UserRole, AuditLog,
)
from auth import get_password_hash, verify_password, create_access_token, validate_password_strength

# Onda 30 — anti-bruteforce lockout (mirror of Onda 29 customer side).
# Pure helpers shared with customer_auth_service via core.lockout_helpers
# (extracted in Onda 30 Step 1). Constants come from core.security_config.
from core.security_config import (
    LOCKOUT_THRESHOLD,
    LOCKOUT_ERROR_CODE,
)
from core.lockout_helpers import (
    compute_lockout_duration_minutes as _compute_lockout_duration_minutes,
    is_account_locked as _is_locked,
)
from repositories import user_repository, organization_repository, audit_repository
from services.email_service import send_welcome
from database import users_collection

# Track S Step 2.1 — timing-constant guard against email enumeration via
# bcrypt latency. See customer_auth_service for full rationale. Burned
# during login() when find_by_email returns None so attacker can't tell
# "email not found" from "password wrong" by measuring response time.
_BCRYPT_DUMMY_HASH = get_password_hash("anti-enumeration-dummy-never-matches")

_SCHEMA_VERSION = "2.0"


async def signup(
    user_data: UserCreate,
    *,
    request_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TokenResponse:
    """Handle user signup – creates org, user, and returns token.

    Wave GDPR-Admin Phase B (2026-05-16) — accepts optional
    ``request_ip`` and ``user_agent`` so the immutable consent_audit
    record can capture the network context of the acceptance. Both
    default to None for backward compat with callers that don't yet
    pass them (e.g. some internal test fixtures); when None, the
    audit record stores nulls in those fields (the legal validity
    of the consent does not depend on IP — the acceptance flag +
    timestamp + hash is sufficient).
    """
    # v6.0: Require terms acceptance
    if not user_data.accepted_terms:
        raise ValueError("You must accept the terms and privacy policy")

    # Validate password complexity before anything else
    validate_password_strength(user_data.password)
    # Track O Step 4.2 — anti credential-stuffing: rifiuta password
    # presenti in noti breach pubblici (HIBP k-anonymity). Fail-open
    # se HIBP API down (security enhancement, not hard gate).
    from core.password_breach import validate_password_not_breached
    validate_password_not_breached(user_data.password)

    existing_user = await user_repository.find_by_email(user_data.email)
    if existing_user:
        raise ValueError("Email already registered")

    org_name = user_data.organization_name or f"{user_data.name}'s Organization"
    organization = Organization(
        name=org_name,
        # Phase-2: seed sensible defaults for new orgs
        plan="free",
        timezone="UTC",
        currency="EUR",
    )
    # Stamp schema_version on the raw doc before insert
    org_doc = organization.model_dump()
    org_doc["created_at"] = org_doc["created_at"].isoformat()
    org_doc["updated_at"] = org_doc["updated_at"].isoformat()
    org_doc["schema_version"] = _SCHEMA_VERSION
    from database import organizations_collection
    await organizations_collection.insert_one(org_doc)

    # v5.9: Provision free-tier module subscriptions for the new org.
    # Creates the 4 ModuleSubscription records (cashflow_monitor_free,
    # ai_assistant_free, customers_light_free, commerce_signals_free) that
    # module_access.py reads to determine feature access.
    # Must run AFTER the org doc is inserted (provision reads the org).
    try:
        from services.plan_provisioning import provision_commercial_plan
        await provision_commercial_plan(
            org_id=organization.id,
            # O1 (5/7/2026) — il verticale ritiri: baseline retreat_free
            # (fee 5%, tutto incluso), non il legacy AFianco "free".
            plan_slug="retreat_free",
            assigned_by="signup",
            billing_status="none",
        )
    except Exception as e:
        # Non-fatal: org + user creation must succeed even if provisioning
        # fails (e.g. commercial_plans collection not yet seeded in dev).
        # Admin can re-provision manually via the admin panel.
        logging.getLogger(__name__).warning(
            "Failed to provision free plan for new org %s: %s", organization.id, e,
        )

    # Generate email-verification token (same pattern as password reset).
    # The plaintext token is sent via email; only the SHA-256 hash is stored.
    verification_token = secrets.token_urlsafe(32)
    verification_token_hash = hashlib.sha256(verification_token.encode()).hexdigest()
    verification_expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    # Validate locale — default to "it" if invalid
    supported_locales = {"it", "en", "de", "fr"}
    user_locale = user_data.locale if user_data.locale in supported_locales else "it"

    # Wave GDPR-Admin Phase B (2026-05-16) — capture which version of
    # the legal documents the user accepted, in which locale. The
    # accepted_terms_version field is the canonical "<tag>:<hash>"
    # string from core.legal_versions; accepted_terms_locale is FROZEN
    # at signup time (user.locale CAN change later via settings, this
    # field cannot — it is the locale they actually saw and agreed to).
    from core.legal_versions import current_version_string
    _accepted_version = current_version_string()
    _accepted_locale = user_locale  # already validated above

    user = User(
        email=user_data.email,
        name=user_data.name,
        role=UserRole.ADMIN,
        organization_id=organization.id,
        password_hash=get_password_hash(user_data.password),
        email_verified=False,
        verification_token_hash=verification_token_hash,
        verification_token_expires=verification_expires,
        accepted_terms_at=datetime.now(timezone.utc).isoformat(),
        accepted_terms_version=_accepted_version,
        accepted_terms_locale=_accepted_locale,
        locale=user_locale,
    )
    user_doc = user.model_dump()
    user_doc["created_at"] = user_doc["created_at"].isoformat()
    user_doc["updated_at"] = user_doc["updated_at"].isoformat()
    user_doc["schema_version"] = _SCHEMA_VERSION
    await users_collection.insert_one(user_doc)

    audit = AuditLog(
        organization_id=organization.id,
        user_id=user.id,
        action="signup",
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email},
    )
    await audit_repository.create(audit)

    # Wave GDPR-Admin Phase B — immutable consent record. Fire-and-forget:
    # if the audit insert fails, log loudly but do NOT block signup
    # (the user already has accepted_terms_at + accepted_terms_version
    # on their user doc, which is the primary evidence; the audit
    # record is the auxiliary tamper-evident log).
    try:
        from repositories import consent_audit_repository
        from core.legal_versions import (
            CURRENT_VERSION_TAG,
            CURRENT_VERSION_HASH,
        )
        await consent_audit_repository.record_consent(
            user_id=user.id,
            organization_id=organization.id,
            locale=_accepted_locale,
            version_tag=CURRENT_VERSION_TAG,
            version_hash=CURRENT_VERSION_HASH,
            ip_address=request_ip,
            user_agent=user_agent,
            source="signup",
            document_type="privacy_terms",
        )
    except Exception as exc:
        logger.error(
            "signup: consent_audit record insert failed for user %s "
            "(version=%s locale=%s): %s — signup continues, user doc "
            "still has accepted_terms_at/version/locale as primary evidence",
            user.id, _accepted_version, _accepted_locale, exc,
            exc_info=True,
        )

    # Welcome email with verification link (non-blocking — failure must not abort signup)
    try:
        send_welcome(user.email, user.name, verification_token=verification_token, locale=user_locale)
    except Exception:
        pass

    token = create_access_token({
        "sub": user.id,
        "org_id": organization.id,
        "role": user.role.value,
        "email": user.email,
    })

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            organization_id=organization.id,
            created_at=user.created_at,
            is_active=user.is_active,
            email_verified=False,
        ),
    )


async def _handle_failed_admin_login(user_doc: dict) -> None:
    """Onda 30 — increment failed_login_attempts on the User doc;
    on threshold reached, set locked_until + send alert email.

    Mirror of customer_auth_service._handle_failed_login but writes
    to users_collection (not customer_accounts_collection) and embeds
    the admin /forgot-password URL in the alert email (not the
    customer /account/forgot-password URL).

    NEVER called for role=system_admin — the caller (`login`) gates
    this. Sysadmin must remain bypassed for operational continuity.
    """
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    current_attempts = int(user_doc.get("failed_login_attempts", 0) or 0)
    new_attempts = current_attempts + 1

    if new_attempts >= LOCKOUT_THRESHOLD:
        prior_lockouts_today = int(user_doc.get("lockout_count_today", 0) or 0)
        duration_min = _compute_lockout_duration_minutes(prior_lockouts_today)
        lockout_until = now + timedelta(minutes=duration_min)

        await users_collection.update_one(
            {"id": user_doc["id"]},
            {"$set": {
                # Reset counter — lockout is the consequence; next cycle
                # restarts from 0 toward the next threshold after expiry.
                "failed_login_attempts": 0,
                "locked_until": lockout_until.isoformat(),
                "lockout_count_today": prior_lockouts_today + 1,
                "last_failed_login_at": now.isoformat(),
            }},
        )

        logger.warning(
            "user.lockout: id=%s email=%s role=%s "
            "attempts=%d prior_today=%d duration_min=%d unlock_at=%s",
            user_doc.get("id"), user_doc.get("email"), user_doc.get("role"),
            new_attempts, prior_lockouts_today, duration_min,
            lockout_until.isoformat(),
        )

        # Best-effort alert email (NEVER block the login flow on this).
        # Onda 30 passes the admin forgot-password URL; Onda 29 customer
        # path uses the default (= /account/forgot-password). The
        # underlying email helper accepts the URL as an optional
        # parameter (Step 30.4 — but already wired here in advance so
        # the call shape is correct after Step 30.4 lands).
        try:
            from services.email_service import send_account_lockout_alert
            import os
            app_url = os.environ.get("APP_URL") or os.environ.get("PUBLIC_APP_URL") or "http://localhost:3000"
            locale = user_doc.get("locale", "it")
            await send_account_lockout_alert(
                customer_email=user_doc["email"],
                locale=locale,
                unlock_at_iso=lockout_until.isoformat(),
                forgot_password_url=f"{app_url}/forgot-password?lang={locale}",
            )
        except (ImportError, AttributeError, TypeError):
            # Step 30.4 not yet shipped (= forgot_password_url kwarg
            # not yet supported). Silently skip — the lockout itself
            # has been recorded, the email is just a courtesy.
            pass
        except Exception as e:
            logger.warning("user.lockout: alert email failed: %s", e)
    else:
        await users_collection.update_one(
            {"id": user_doc["id"]},
            {"$set": {
                "failed_login_attempts": new_attempts,
                "last_failed_login_at": now.isoformat(),
            }},
        )


async def login(email: str, password: str) -> TokenResponse:
    """Handle user login and return token.

    Track S Step 2.1: anti-enumeration order of checks (mirror of
    customer_auth_service.customer_login refactor):

      1. find_by_email → if not found, RUN bcrypt anyway (timing-constant)
         then generic 401 "Invalid email or password"
      2. password verify → generic 401 if wrong (failed_login tracking
         for non-sysadmin)
      3. ⇒ FROM HERE caller proved password knowledge — state-revealing
         errors below are safe (no info leak to brute-forcer)
      4. lockout post-check (skipped for sysadmin) → 423 ACCOUNT_LOCKED
      5. is_active → 403 deactivated
      6. email_verified → 403 not verified (sysadmin bypasses)
      7. org deactivation → 403 with role/timestamp metadata
      8. on success, reset all anti-bruteforce counters

    Pre-S2.1 order had lockout BEFORE password verify. Locked account
    returned 423 to ANY caller (including brute-forcer without password),
    leaking "this email exists and was bruteforced". Post-S2.1 the 423
    surfaces only after correct password.

    Track S Step 2.4: per-email rate limit (cross-IP, 20/h) as backstop
    to the per-account lockout (Onda 30: 5 fail → 15min). When triggered
    we burn bcrypt on dummy hash and return uniform 401 (anti-enum).
    """
    # Track S Step 2.4 — per-email cross-IP rate limit. Anti-botnet
    # backstop. Sysadmin path is rate-limited too (no carve-out): if
    # someone bombards the sysadmin email from 1000 IPs, we cap them.
    from core.rate_limiting import check_email_rate
    if not check_email_rate(email, "admin_login", max_per_hour=20):
        logger.info(
            "admin login: per-email rate limit hit. email_redacted=%s",
            (email[:3] + "***" + email[email.find("@"):]) if "@" in email else "***",
        )
        verify_password(password or "", _BCRYPT_DUMMY_HASH)
        raise ValueError("Invalid email or password")

    user_doc = await user_repository.find_by_email(email)
    if not user_doc:
        # Timing-constant: burn CPU on a bcrypt verify so attacker can't
        # distinguish "email not found" via response latency (~10ms vs ~200ms).
        verify_password(password or "", _BCRYPT_DUMMY_HASH)
        raise ValueError("Invalid email or password")

    is_sysadmin = user_doc.get("role") == "system_admin"

    if not verify_password(password, user_doc["password_hash"]):
        # Onda 30 — track the failure for non-sysadmin users.
        if not is_sysadmin:
            await _handle_failed_admin_login(user_doc)
        raise ValueError("Invalid email or password")

    # ── Password verified — state-revealing errors are now safe ──────────
    # Lockout post-check (skipped for sysadmin). Account locked + correct
    # password = recovery via forgot-password (the lockout is a signal,
    # not a "you remembered the password" override).
    if not is_sysadmin:
        now_dt = datetime.now(timezone.utc)
        locked_until_iso = _is_locked(user_doc, now_dt)
        if locked_until_iso:
            raise ValueError(f"{LOCKOUT_ERROR_CODE}:{locked_until_iso}")

    if not user_doc.get("is_active", True):
        raise ValueError("Account is deactivated")

    # v6.0: Require email verification before login (system_admin bypasses)
    if not user_doc.get("email_verified", False):
        if not is_sysadmin:
            raise ValueError("Email not verified")

    # v6.0: Check org deactivation (system_admin has no org, bypasses)
    login_org_id = user_doc.get("organization_id")
    if login_org_id:
        _org = await organization_repository.find_by_id(login_org_id)
        if _org and _org.get("deactivated_at"):
            _role = user_doc.get("role", "user")
            raise ValueError(f"Account deactivated|{_role}|{_org['deactivated_at']}")

    # Phase-2: stamp last_login_at on every login
    # Onda 30: also reset the anti-bruteforce counters on successful
    # login. Skipped for sysadmin (those fields stay at their default
    # zero values since the lockout never fires for sysadmin anyway).
    now_iso = datetime.now(timezone.utc).isoformat()
    success_set = {"last_login_at": now_iso, "updated_at": now_iso}
    if not is_sysadmin:
        success_set.update({
            "failed_login_attempts": 0,
            "locked_until": None,
            "lockout_count_today": 0,
        })
    await users_collection.update_one(
        {"id": user_doc["id"]},
        {"$set": success_set},
    )

    created_at = user_doc["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)

    token = create_access_token({
        "sub": user_doc["id"],
        "org_id": user_doc["organization_id"],
        "role": user_doc["role"],
        "email": user_doc["email"],
    })

    audit = AuditLog(
        organization_id=user_doc["organization_id"],
        user_id=user_doc["id"],
        action="login",
        resource_type="user",
        resource_id=user_doc["id"],
    )
    await audit_repository.create(audit)

    # Fetch org currency + default_iva for login response
    login_currency = "EUR"
    login_default_iva = None
    login_org_id = user_doc.get("organization_id")
    if login_org_id:
        login_org_doc = await organization_repository.find_by_id(login_org_id)
        if login_org_doc:
            login_currency = login_org_doc.get("currency") or "EUR"
            login_default_iva = (login_org_doc.get("settings") or {}).get("default_iva")

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_doc["id"],
            email=user_doc["email"],
            name=user_doc["name"],
            role=UserRole(user_doc["role"]),
            organization_id=user_doc["organization_id"],
            created_at=created_at,
            is_active=user_doc.get("is_active", True),
            must_change_password=user_doc.get("must_change_password", False),
            email_verified=user_doc.get("email_verified", False),
            currency=login_currency,
            default_iva=login_default_iva,
        ),
    )


async def get_current_user_info(user_id: str) -> UserResponse:
    """Get current user info.

    Wave GDPR-Admin Phase E (2026-05-18): the response now carries a
    server-computed ``consent_needs_refresh`` flag that compares the
    user's stored ``accepted_terms_version`` against
    ``current_version_string()`` from the legal-versions registry. The
    frontend reads this on every /auth/me call (i.e. on every app boot)
    and renders a blocking re-acceptance modal when True.
    """
    user_doc = await user_repository.find_by_id(user_id)
    if not user_doc:
        raise ValueError("User not found")

    created_at = user_doc["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)

    # Fetch org currency + default_iva
    currency = "EUR"
    default_iva = None
    org_id = user_doc.get("organization_id")
    if org_id:
        org_doc = await organization_repository.find_by_id(org_id)
        if org_doc:
            currency = org_doc.get("currency") or "EUR"
            default_iva = (org_doc.get("settings") or {}).get("default_iva")

    # ── Phase E re-consent gate ──────────────────────────────────────────
    from core.legal_versions import current_version_string

    accepted_version = user_doc.get("accepted_terms_version")
    current_version = current_version_string()
    # True when the user either never accepted (legacy) or accepted an
    # older bundle (post version-bump). system_admin role is exempt —
    # they bumped the docs themselves, no UX-blocking needed.
    needs_refresh = (
        UserRole(user_doc["role"]) != UserRole.SYSTEM_ADMIN
        and accepted_version != current_version
    )

    return UserResponse(
        id=user_doc["id"],
        email=user_doc["email"],
        name=user_doc["name"],
        role=UserRole(user_doc["role"]),
        organization_id=user_doc["organization_id"],
        created_at=created_at,
        is_active=user_doc.get("is_active", True),
        must_change_password=user_doc.get("must_change_password", False),
        email_verified=user_doc.get("email_verified", False),
        locale=user_doc.get("locale", "it"),
        currency=currency,
        default_iva=default_iva,
        accepted_terms_version=accepted_version,
        accepted_terms_locale=user_doc.get("accepted_terms_locale"),
        accepted_terms_at=user_doc.get("accepted_terms_at"),
        current_terms_version=current_version,
        consent_needs_refresh=needs_refresh,
    )
