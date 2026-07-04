"""
Customer Authentication Service — signup, login, password reset, email verification.

Separate from the admin auth_service by design.
Customer accounts are ORG-SCOPED and use type="customer" + org_id JWT tokens.
Every operation requires organization_id for tenant isolation.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

# Onda 29 — anti-bruteforce lockout constants
from core.security_config import (
    LOCKOUT_THRESHOLD,
    LOCKOUT_ERROR_CODE,
)
# Onda 30 — pure lockout helpers extracted to core/lockout_helpers.py
# so the admin auth_service.login() can reuse the exact same logic.
# Behaviour identical to the Onda 29 inline definitions; only the
# import path changes.
from core.lockout_helpers import (
    compute_lockout_duration_minutes as _compute_lockout_duration_minutes,
    is_account_locked as _is_locked,
)

from models.common import generate_id, utc_now
from auth import (
    get_password_hash,
    verify_password,
    validate_password_strength,
    create_customer_token,
)
from repositories import customer_account_repository
from models.customer_account import CustomerAccountResponse, CustomerTokenResponse
from services.email_service import (
    send_customer_welcome,
    send_customer_verification,
    send_customer_password_reset,
    send_customer_password_changed,
)

logger = logging.getLogger(__name__)


# Track S Step 2.1 — timing-constant guard against email enumeration via
# bcrypt latency. When `find_by_email` returns None we still need to burn
# the same CPU cycles a real bcrypt verify would, otherwise an attacker
# distinguishes "email exists" from "doesn't exist" by measuring response
# time (~200ms for bcrypt 12 rounds vs ~10ms for early-return).
#
# Computed once at module load. The plaintext used to generate is
# intentionally non-empty and non-trivially guessable but irrelevant —
# we only need a valid bcrypt hash shape so `pwd_context.verify(p, h)`
# performs the full work factor pass.
_BCRYPT_DUMMY_HASH = get_password_hash("anti-enumeration-dummy-never-matches")


async def _load_email_context(
    org_id: str,
    *,
    store_slug: Optional[str] = None,
) -> dict:
    """Load store email branding (sender_name, reply_to, store_name) for an org.

    Multi-store-aware (Onda 6):
      - When `store_slug` is given AND it resolves to a real `stores`
        document of this org, the per-store fields override the legacy
        org-level `organizations.store_settings` block. Used by every
        customer-auth flow (signup, forgot password, reset, resend
        verification) so the welcome email of a customer who registered
        on the German store carries the German store's sender, reply-to,
        and display name — not the org-level legacy ones.
      - When `store_slug` is None or the lookup misses, falls back to
        the existing org-level shape — preserves behaviour for orgs
        without per-store config (single-store / legacy customers).
    """
    from database import organizations_collection, stores_collection
    from services.email_service import SMTP_FROM_NAME

    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "name": 1, "store_settings": 1},
    )
    legacy = (org.get("store_settings") or {}) if org else {}
    org_name = org.get("name") if org else None

    store_doc: Optional[dict] = None
    if store_slug:
        store_doc = await stores_collection.find_one(
            {"slug": store_slug, "organization_id": org_id},
            {"_id": 0, "name": 1, "sender_display_name": 1,
             "reply_to_email": 1},
        )

    if store_doc:
        return {
            "sender_name": (
                store_doc.get("sender_display_name")
                or legacy.get("sender_display_name")
                or SMTP_FROM_NAME
            ),
            "reply_to": (
                store_doc.get("reply_to_email")
                or legacy.get("reply_to_email")
            ),
            "store_name": (
                store_doc.get("name")
                or legacy.get("display_name")
                or org_name
            ),
        }

    # Legacy path (no slug or store not found): byte-equivalent to the
    # pre-Onda-6 implementation.
    return {
        "sender_name": legacy.get("sender_display_name") or SMTP_FROM_NAME,
        "reply_to": legacy.get("reply_to_email"),
        "store_name": legacy.get("display_name") or org_name,
    }


async def resolve_slug_for_org(org_id: str, *, preferred: str | None = None) -> str | None:
    """Reverse-lookup a public slug usable by /account/login?store=… for an org.

    Resolution order mirrors `_resolve_org_id` in routers/customer_auth.py
    (modern stores → legacy org.public_slug) so a slug we hand back to the
    frontend always resolves on the way back in:

      1. `preferred` (e.g. saved `signup_slug` on the account) — wins if
         it still resolves to this org_id (store could have been renamed
         or deactivated since signup; we don't return a stale value).
      2. First published+public store for the org.
      3. Org `public_slug` (legacy).
      4. None — caller decides whether to fall back to localStorage.

    Used by the email-verification and password-reset flows so the
    landing page can route the user to the right storefront login.
    """
    from database import organizations_collection, stores_collection

    if preferred:
        store = await stores_collection.find_one(
            {"slug": preferred, "organization_id": org_id,
             "is_published": True, "is_active": True, "visibility": "public"},
            {"_id": 0, "slug": 1},
        )
        if store:
            return preferred
        org = await organizations_collection.find_one(
            {"id": org_id, "public_slug": preferred,
             "is_active": {"$ne": False}, "deactivated_at": None},
            {"_id": 0, "id": 1},
        )
        if org:
            return preferred

    store = await stores_collection.find_one(
        {"organization_id": org_id, "is_published": True,
         "is_active": True, "visibility": "public"},
        {"_id": 0, "slug": 1},
    )
    if store and store.get("slug"):
        return store["slug"]

    org = await organizations_collection.find_one(
        {"id": org_id, "is_active": {"$ne": False}, "deactivated_at": None},
        {"_id": 0, "public_slug": 1},
    )
    if org and org.get("public_slug"):
        return org["public_slug"]

    return None


def _normalize_email(email: str) -> str:
    """Normalize email: strip whitespace + lowercase."""
    return email.strip().lower()


def _hash_token(token: str) -> str:
    """SHA-256 hash a one-time token (plaintext never stored)."""
    return hashlib.sha256(token.encode()).hexdigest()


def _account_to_response(
    doc: dict,
    *,
    current_store_legal_version: Optional[str] = None,
    consent_needs_refresh: bool = False,
) -> CustomerAccountResponse:
    """Convert raw DB document to safe response model.

    Wave GDPR-Commerce CG-4: optional kwargs let callers pass the
    server-computed re-consent freshness (only the /me endpoint needs
    it; signup + login leave the defaults because the customer just
    consented or just authenticated).
    """
    return CustomerAccountResponse(
        id=doc["id"],
        organization_id=doc["organization_id"],
        email=doc["email"],
        name=doc["name"],
        is_active=doc.get("is_active", True),
        email_verified=doc.get("email_verified", False),
        locale=doc.get("locale", "it"),
        created_at=doc["created_at"],
        # CG-4 — consent snapshot from the account doc (None on legacy
        # accounts; the /me endpoint then surfaces consent_needs_refresh=True
        # and the modal will prompt for fresh acceptance).
        accepted_store_terms_version=doc.get("accepted_store_terms_version"),
        accepted_store_privacy_version=doc.get("accepted_store_privacy_version"),
        accepted_marketing_at=doc.get("accepted_marketing_at"),
        marketing_revoked_at=doc.get("marketing_revoked_at"),
        current_store_legal_version=current_store_legal_version,
        consent_needs_refresh=consent_needs_refresh,
    )


# ── Signup ───────────────────────────────────────────────────────────────────

async def customer_signup(
    org_id: str, email: str, name: str, password: str, locale: str = "it",
    *, auto_login: bool = False, signup_slug: str | None = None,
    # Wave GDPR-Commerce CG-4 — explicit consent capture at signup.
    # These three flags ARE NOT optional in the API contract (the
    # router validates them before delegating). They land here with
    # defaults False so legacy in-process callers (none today) don't
    # accidentally re-introduce silent consent acceptance.
    accepted_terms: bool = False,
    accepted_privacy: bool = False,
    accepted_marketing: bool = False,
    request_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> dict:
    """Create a new customer account within an org.

    Default flow: returns {"status": "verification_required"} and the
    customer must click the emailed link before being able to log in.

    Course checkout flow: when `auto_login=True`, also mints an
    access_token so the caller can complete a purchase immediately
    without waiting for email verification. The account still starts
    with email_verified=False — subsequent fresh logins (after logout)
    will require the link to have been clicked. A "verifica l'email
    entro N giorni" banner surfaces in the customer portal so the
    user doesn't forget.

    Wave GDPR-Commerce CG-4: at signup the customer MUST accept the
    merchant's published Privacy + Terms (both required); marketing
    consent is optional. The version + locale they actually saw are
    read SERVER-SIDE from the store document — never trusted from the
    request. If the merchant has not published their docs yet
    (merchant_legal_status != "published") the signup is REJECTED with
    a 400 — see customer_auth.py for the user-facing message.
    """
    email = _normalize_email(email)

    # CG-4: enforce both mandatory consents BEFORE running the
    # expensive password hash and DB lookups. A failed-consent signup
    # attempt should not waste a bcrypt round-trip nor disclose
    # password-policy hints to a probing client.
    if not accepted_terms or not accepted_privacy:
        raise ValueError(
            "Devi accettare i Termini e Condizioni e l'Informativa "
            "sulla Privacy per registrarti."
        )

    try:
        validate_password_strength(password)
    except ValueError as e:
        raise ValueError(str(e))
    # Track O Step 4.2 — anti credential-stuffing: rifiuta password
    # presenti in noti breach pubblici (HIBP k-anonymity). Fail-open
    # se HIBP API down.
    from core.password_breach import validate_password_not_breached
    validate_password_not_breached(password)

    # Track S Step 2.2 — anti-enumeration: pre-check email exists in this
    # org. Pre-fix the create() at line ~359 would raise DuplicateKeyError
    # via the unique compound index (organization_id, email) → catched as
    # generic 500. Combined with the 400 paths above, an attacker could
    # distinguish (400 = email new + validation fail) from (500 = email
    # exists + validation pass) → email enumeration.
    #
    # Post-fix: if duplicate, RETURN the SAME success response as a new
    # signup (status=202 verification_required). The legitimate user
    # whose email is already registered gets no signal they "exist" —
    # they go to login/forgot-password by intent, not by this flow.
    # The audit log captures the duplicate attempt for ops visibility.
    existing = await customer_account_repository.find_by_email(email, org_id)
    if existing is not None:
        logger.warning(
            "customer_signup: duplicate attempt detected — returning uniform "
            "success response (anti-enumeration). email_redacted=%s org=%s",
            email[:3] + "***" + email[email.find("@"):] if "@" in email else "***",
            org_id,
        )
        # NB: NO bcrypt waste, NO audit consent record (it's not a real
        # signup). Just return the same body shape clients see for success.
        # auto_login is intentionally NOT honored here — minting a token
        # for a duplicate attempt would BE the enumeration leak we're
        # closing. Legitimate user reaches their account via /login.
        return {"status": "verification_required"}

    # CG-4: resolve store + verify merchant has published their docs.
    # The customer must accept SOMETHING binding — if the merchant
    # hasn't published, there's nothing to bind to.
    store_doc = None
    if signup_slug:
        from database import stores_collection
        store_doc = await stores_collection.find_one(
            {"slug": signup_slug, "organization_id": org_id},
            {"_id": 0},
        )
    if store_doc is None:
        # Legacy org without multi-store doc — refuse signup until the
        # merchant migrates and publishes. This is the "GDPR before
        # data collection" hard rule.
        raise ValueError(
            "Il negozio non ha ancora completato la configurazione "
            "legale. Riprova più tardi o contatta il venditore."
        )

    from services.merchant_legal_versioning import (
        merchant_legal_status, current_version_string,
        get_effective_display_locale,
    )
    legal_status = merchant_legal_status(store_doc)
    if legal_status not in ("published", "stale_draft"):
        raise ValueError(
            "Il negozio non ha ancora pubblicato la propria Privacy "
            "Policy e Termini. Riprova più tardi o contatta il venditore."
        )

    legal_version = current_version_string(store_doc)
    # CG-3-Polish-3 — resolve via helper (the auto-cleanup unsets the
    # raw legacy field; reading it directly returns None and breaks
    # signup for any store edited after polish-2 shipped).
    legal_display_locale = get_effective_display_locale(store_doc)
    # Defensive: published status means both are non-None, but verify.
    if not legal_version or not legal_display_locale:
        raise ValueError(
            "Impossibile registrare l'accettazione legale del negozio."
        )

    verification_token = secrets.token_urlsafe(32)
    verification_hash = _hash_token(verification_token)
    now = utc_now()

    from datetime import timedelta
    verification_expires = (now + timedelta(hours=24)).isoformat()

    # CG-4: snapshot consent fields on the account doc (the fast-path
    # used by /me to detect re-consent needs). The immutable record
    # lives in consent_audit (written below).
    now_iso = now.isoformat()
    marketing_accepted_iso = now_iso if accepted_marketing else None

    doc = {
        "id": generate_id(),
        "organization_id": org_id,
        "email": email,
        "name": name.strip(),
        "password_hash": get_password_hash(password),
        "is_active": True,
        "email_verified": False,
        "verification_token_hash": verification_hash,
        "verification_token_expires": verification_expires,
        "reset_token_hash": None,
        "reset_token_expires": None,
        "password_changed_at": None,
        "last_login_at": None,
        "locale": locale if locale in {"it", "en", "de", "fr"} else "it",
        "signup_slug": signup_slug,
        # CG-4 consent snapshot
        "accepted_store_terms_version": legal_version,
        "accepted_store_terms_locale": legal_display_locale,
        "accepted_store_terms_at": now_iso,
        "accepted_store_privacy_version": legal_version,
        "accepted_store_privacy_locale": legal_display_locale,
        "accepted_store_privacy_at": now_iso,
        "accepted_marketing_at": marketing_accepted_iso,
        "marketing_revoked_at": None,
        "created_at": now,
        "updated_at": now,
    }

    await customer_account_repository.create(doc)

    # CG-4: write the immutable audit records. These are the legal
    # proof trail — best-effort but loud on failure (we log + raise
    # for visibility, the calling endpoint catches and turns into an
    # observability signal; the account exists either way).
    try:
        from repositories import consent_audit_repository as car
        version_tag, _, version_hash = legal_version.partition(":")
        # Required field on consent_audit: locale ∈ {it,en,de,fr}.
        # legal_display_locale is guaranteed in that set by CG-1
        # validation, but we defensively assert it here.
        audit_locale = legal_display_locale if legal_display_locale in (
            "it", "en", "de", "fr"
        ) else "it"

        for doc_type in ("merchant_privacy", "merchant_terms"):
            await car.record_consent(
                user_id=doc["id"],
                organization_id=org_id,
                store_id=store_doc.get("id"),
                locale=audit_locale,
                version_tag=version_tag or "v1.0",
                version_hash=version_hash or "unknown",
                ip_address=request_ip,
                user_agent=user_agent,
                source="customer_signup",
                document_type=doc_type,
            )

        if accepted_marketing:
            await car.record_consent(
                user_id=doc["id"],
                organization_id=org_id,
                store_id=store_doc.get("id"),
                locale=audit_locale,
                version_tag=version_tag or "v1.0",
                version_hash=version_hash or "unknown",
                ip_address=request_ip,
                user_agent=user_agent,
                source="customer_marketing_optin",
                document_type="merchant_marketing",
            )
    except Exception as exc:
        # Audit insert failure should NOT roll back the account
        # creation (that would leave the user with a 500 after their
        # email is taken). Log loudly so ops notices.
        logger.error(
            "customer_signup: consent_audit insert failed for "
            "id=%s org=%s store=%s: %s",
            doc["id"], org_id, store_doc.get("id"), exc, exc_info=True,
        )

    try:
        # Per-store branding (Onda 6): pass the signup slug so the
        # welcome email carries this store's sender / reply-to / name
        # instead of the org-level legacy values. Falls back gracefully
        # when the slug doesn't resolve to a real store (e.g. legacy
        # org.public_slug signup).
        email_ctx = await _load_email_context(org_id, store_slug=signup_slug)
        # Verify the saved slug still resolves to this org before embedding
        # it in the email link — guards against a misconfigured client
        # passing a slug that belongs to another org.
        email_slug = await resolve_slug_for_org(org_id, preferred=signup_slug)
        send_customer_welcome(email, name.strip(), verification_token, locale,
                              sender_name=email_ctx["sender_name"], reply_to=email_ctx["reply_to"],
                              store_name=email_ctx["store_name"],
                              store_slug=email_slug)
    except Exception as e:
        logger.error("customer_signup: failed to send welcome email: %s", e)

    # Link to existing org-scoped customer records (same org only)
    await _link_account_to_existing_customers(doc["id"], email, org_id)

    logger.info("customer_signup: account created id=%s email=%s org=%s", doc["id"], email, org_id)

    response = {"status": "verification_required"}

    # Release 4 (Courses) — inline signup during course checkout: mint a
    # session token immediately so the customer can complete the purchase.
    # We deliberately bypass the usual email_verified gate here because
    # the signup + checkout happen in the same user action; rejecting
    # the login at this step would strand the customer outside the funnel.
    # Future logins (after logout) still require a verified email.
    if auto_login:
        token = create_customer_token({
            "sub": doc["id"],
            "org_id": org_id,
            "email": doc["email"],
        })
        response["access_token"] = token
        response["customer"] = _account_to_response(doc)
        logger.info(
            "customer_signup: auto_login token minted for id=%s (email not yet verified)",
            doc["id"],
        )

    return response


# ── Login ────────────────────────────────────────────────────────────────────


# ─── Onda 29/30 — Anti-bruteforce helpers ───────────────────────────────────
# Pure helpers (compute_lockout_duration_minutes, is_account_locked) live in
# core/lockout_helpers.py and are imported above as _compute_lockout_duration_minutes
# and _is_locked respectively. The DB-write side stays here because it
# depends on customer_account_repository.

async def _handle_failed_login(account: dict, org_id: str) -> None:
    """Increment failed_login_attempts. If threshold reached, lock the
    account for the appropriate exponential-backoff duration and
    best-effort send the alert email.

    Atomic-ish: reads the current counter from the freshly-loaded
    account dict and writes the new value with $set. Two truly
    concurrent failed logins for the same account could undercount by
    one — acceptable because the attacker model that benefits from
    that is exotic (would need to time-align <50ms requests across
    two TCP connections). The IP rate limit (Onda 27.2) caps that
    attack profile separately.
    """
    now = utc_now()
    current_attempts = int(account.get("failed_login_attempts", 0) or 0)
    new_attempts = current_attempts + 1

    if new_attempts >= LOCKOUT_THRESHOLD:
        prior_lockouts_today = int(account.get("lockout_count_today", 0) or 0)
        duration_min = _compute_lockout_duration_minutes(prior_lockouts_today)
        lockout_until = now + timedelta(minutes=duration_min)

        await customer_account_repository.update(account["id"], {
            # Reset the counter — the lockout itself is the consequence;
            # next threshold cycle starts fresh after lockout expires.
            "failed_login_attempts": 0,
            "locked_until": lockout_until.isoformat(),
            "lockout_count_today": prior_lockouts_today + 1,
            "last_failed_login_at": now.isoformat(),
        })

        logger.warning(
            "customer_account.lockout: id=%s email=%s org=%s "
            "attempts=%d prior_lockouts_today=%d duration_min=%d unlock_at=%s",
            account.get("id"), account.get("email"), org_id,
            new_attempts, prior_lockouts_today, duration_min,
            lockout_until.isoformat(),
        )

        # Best-effort alert email. NEVER block the login flow on this:
        #   · Step 4 will implement send_account_lockout_alert in
        #     email_service. Until then, the import will not exist;
        #     we wrap in try/except ImportError so this commit can land
        #     before Step 4 without a NameError.
        #   · Even after Step 4 lands, SMTP failures must not flip a
        #     successful lockout into a failed login response.
        try:
            from services.email_service import send_account_lockout_alert
            await send_account_lockout_alert(
                customer_email=account["email"],
                locale=account.get("locale", "it"),
                unlock_at_iso=lockout_until.isoformat(),
            )
        except (ImportError, AttributeError):
            # Step 4 not yet shipped — silently skip.
            pass
        except Exception as e:
            logger.warning("customer_account.lockout: alert email failed: %s", e)

    else:
        # Below threshold — just bump the counter and audit timestamp.
        await customer_account_repository.update(account["id"], {
            "failed_login_attempts": new_attempts,
            "last_failed_login_at": now.isoformat(),
        })


async def customer_login(org_id: str, email: str, password: str) -> CustomerTokenResponse:
    """Authenticate customer within an org and return JWT with org_id.

    Track S Step 2.1: anti-enumeration order of checks:

      1. find_by_email — if not found, RUN bcrypt anyway (timing-constant)
         then generic 401 error
      2. password verify — generic 401 if wrong (with failed_login tracking)
      3. ⇒ FROM HERE the caller has demonstrated knowledge of the password.
         State-revealing errors below are safe (no info leak to brute-forcer)
      4. lockout post-check → 423 ACCOUNT_LOCKED (legitimate user UX)
      5. is_active check → 403 ACCOUNT_DISABLED
      6. email_verified check → 403 EMAIL_NOT_VERIFIED
      7. on success, reset all anti-bruteforce counters

    Pre-S2.1 the order was: find → lockout → password → is_active → verified.
    The old lockout pre-check returned 423 BEFORE password verify, leaking
    "account exists + has been brute-forced". Post-S2.1 the 423 happens only
    after correct password — an attacker without the password sees only 401.

    Track S Step 2.4: per-email rate limit (cross-IP, 20/h) as backstop to
    the account lockout (Onda 29: 5 fail → 15min lockout). When rate-limit
    fires we still burn bcrypt on dummy hash and return the SAME generic
    401 — preserves anti-enumeration. Attacker with a botnet hitting one
    email is capped to 20/h regardless of source IP count.
    """
    email = _normalize_email(email)

    # Track S Step 2.4 — per-email cross-IP rate limit. Same uniform
    # 401 path as email-not-found when triggered (no enumeration leak
    # via "you're rate-limited" message).
    from core.rate_limiting import check_email_rate
    if not check_email_rate(email, "customer_login", max_per_hour=20):
        logger.info(
            "customer_login: per-email rate limit hit. email_redacted=%s org=%s",
            email[:3] + "***" + email[email.find("@"):] if "@" in email else "***",
            org_id,
        )
        verify_password(password or "", _BCRYPT_DUMMY_HASH)
        raise ValueError("Email o password non corretti.")

    account = await customer_account_repository.find_by_email(email, org_id)
    if not account:
        # Timing-constant: burn the same CPU as a bcrypt verify so attacker
        # can't distinguish "email not found" via response latency.
        verify_password(password or "", _BCRYPT_DUMMY_HASH)
        raise ValueError("Email o password non corretti.")

    if not verify_password(password, account["password_hash"]):
        # Onda 29 — track the failure (may trigger lockout).
        await _handle_failed_login(account, org_id)
        raise ValueError("Email o password non corretti.")

    # ── Password verified — state-revealing errors are now safe ──────────
    # Lockout post-check: a locked account with the correct password still
    # cannot login (recovery via forgot-password). Returning 423 here is
    # OK because the caller already proved password knowledge.
    now_dt = utc_now()
    locked_until_iso = _is_locked(account, now_dt)
    if locked_until_iso:
        raise ValueError(f"{LOCKOUT_ERROR_CODE}:{locked_until_iso}")

    if not account.get("is_active", True):
        raise ValueError("ACCOUNT_DISABLED")

    if not account.get("email_verified", False):
        raise ValueError("EMAIL_NOT_VERIFIED")

    # Successful authentication — reset all anti-bruteforce state.
    now = utc_now()
    await customer_account_repository.update(account["id"], {
        "last_login_at": now.isoformat(),
        "failed_login_attempts": 0,
        "locked_until": None,
        "lockout_count_today": 0,  # clean slate after a successful login
    })

    token = create_customer_token({
        "sub": account["id"],
        "org_id": org_id,
        "email": account["email"],
    })

    return CustomerTokenResponse(
        access_token=token,
        customer=_account_to_response(account),
    )


# ── Forgot Password ─────────────────────────────────────────────────────────

async def customer_forgot_password(org_id: str, email: str, locale: str = "it") -> dict:
    """Generate password reset token. Always returns generic message."""
    email = _normalize_email(email)

    account = await customer_account_repository.find_by_email(email, org_id)
    if not account:
        return {"message": "Se l'email esiste, riceverai un link per reimpostare la password."}

    reset_token = secrets.token_urlsafe(32)
    reset_hash = _hash_token(reset_token)

    from datetime import timedelta
    expires = (utc_now() + timedelta(hours=1)).isoformat()

    await customer_account_repository.update(account["id"], {
        "reset_token_hash": reset_hash,
        "reset_token_expires": expires,
        "updated_at": utc_now(),
    })

    loc = account.get("locale", locale)
    try:
        # Per-store branding (Onda 6): forgot-password email picks up
        # the store the customer originally signed up on.
        signup_slug = account.get("signup_slug")
        email_ctx = await _load_email_context(org_id, store_slug=signup_slug)
        email_slug = await resolve_slug_for_org(org_id, preferred=signup_slug)
        send_customer_password_reset(email, reset_token, loc,
                                     sender_name=email_ctx["sender_name"], reply_to=email_ctx["reply_to"],
                                     store_name=email_ctx["store_name"],
                                     store_slug=email_slug)
    except Exception as e:
        logger.error("customer_forgot_password: failed to send email: %s", e)

    return {"message": "Se l'email esiste, riceverai un link per reimpostare la password."}


# ── Reset Password ───────────────────────────────────────────────────────────

async def customer_reset_password(token: str, new_password: str) -> dict:
    """Validate reset token and set new password. Token is single-use.

    Track S Step 2.3: single-use enforcement is implemented implicitly —
    after successful reset, the update() at line ~696-711 sets
    reset_token_hash=None and reset_token_expires=None. A second call
    with the same token finds no matching account → 400. Pinned by
    sentinel TestSEC_S2_3_TokenSingleUse_Customer.
    """
    token_hash = _hash_token(token)

    account = await customer_account_repository.find_by_reset_token_hash(token_hash)
    if not account:
        # Track S Step 2.3 — log token-consumption-failed for detection.
        # An attacker who got a leaked reset token and tries to use it
        # post-consumption (or a guessed/expired token) leaves a trail
        # here. SOC can alert on spikes of this event per IP.
        logger.info(
            "customer_reset_password: token consumption failed (invalid, "
            "already used, or expired). token_hash_prefix=%s",
            token_hash[:8],
        )
        raise ValueError("Token non valido o scaduto.")

    from datetime import datetime
    expires_str = account.get("reset_token_expires", "")
    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str)
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            if utc_now() > expires_dt:
                raise ValueError("Token non valido o scaduto.")
        except (ValueError, TypeError):
            raise ValueError("Token non valido o scaduto.")

    validate_password_strength(new_password)
    # Track O Step 4.2 — anti credential-stuffing su password reset.
    # Stesso reasoning del signup: user che resetta password con una
    # password breach-known potrebbe essere account-takeover via
    # credential stuffing su email gia' compromessa.
    from core.password_breach import validate_password_not_breached
    validate_password_not_breached(new_password)

    now = utc_now()
    await customer_account_repository.update(account["id"], {
        "password_hash": get_password_hash(new_password),
        "reset_token_hash": None,
        "reset_token_expires": None,
        "password_changed_at": now.isoformat(),
        "updated_at": now,
        # Onda 29 — successful password reset implies the user has
        # demonstrated control of their email inbox; treat that as
        # equivalent proof of identity to a successful login and
        # clear all anti-bruteforce state. Without this, a user who
        # locked themselves out by mistyping passwords would still
        # be locked even after recovering via the email reset flow.
        "failed_login_attempts": 0,
        "locked_until": None,
        "lockout_count_today": 0,
    })

    org_id_for_slug = account.get("organization_id", "")
    signup_slug = account.get("signup_slug")
    org_slug = await resolve_slug_for_org(
        org_id_for_slug, preferred=signup_slug,
    )

    try:
        # Per-store branding (Onda 6): password-changed confirmation
        # mirrors the signup store identity.
        email_ctx = await _load_email_context(org_id_for_slug, store_slug=signup_slug)
        send_customer_password_changed(
            account["email"], account["name"], account.get("locale", "it"),
            sender_name=email_ctx["sender_name"], reply_to=email_ctx["reply_to"],
            store_name=email_ctx["store_name"],
        )
    except Exception:
        pass

    return {"message": "Password reimpostata con successo.", "org_slug": org_slug}


# ── Verify Email ─────────────────────────────────────────────────────────────

async def customer_verify_email(token: str) -> dict:
    """Consume verification token. Token is single-use (SHA-256 hash).

    Track S Step 2.3: single-use is implicit — successful verify nulls
    verification_token_hash + _expires. Pinned by sentinel
    TestSEC_S2_3_TokenSingleUse_Customer.
    """
    token_hash = _hash_token(token)

    account = await customer_account_repository.find_by_verification_token_hash(token_hash)
    if not account:
        # Track S Step 2.3 — detection log (same rationale as reset).
        logger.info(
            "customer_verify_email: token consumption failed (invalid, "
            "already used, or expired). token_hash_prefix=%s",
            token_hash[:8],
        )
        raise ValueError("Token di verifica non valido o scaduto.")

    from datetime import datetime
    expires_str = account.get("verification_token_expires", "")
    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str)
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            if utc_now() > expires_dt:
                raise ValueError("Token di verifica non valido o scaduto.")
        except (ValueError, TypeError):
            raise ValueError("Token di verifica non valido o scaduto.")

    org_slug = await resolve_slug_for_org(
        account.get("organization_id", ""),
        preferred=account.get("signup_slug"),
    )

    if account.get("email_verified"):
        return {"message": "Email gia' verificata.", "org_slug": org_slug}

    await customer_account_repository.update(account["id"], {
        "email_verified": True,
        "verification_token_hash": None,
        "verification_token_expires": None,
        "updated_at": utc_now(),
    })

    return {"message": "Email verificata con successo.", "org_slug": org_slug}


# ── Resend Verification ─────────────────────────────────────────────────────

async def customer_resend_verification(org_id: str, email: str) -> dict:
    """Resend verification email within an org. Always returns generic message."""
    email = _normalize_email(email)

    account = await customer_account_repository.find_by_email(email, org_id)
    if not account or account.get("email_verified"):
        return {"message": "Se l'email esiste e non e' verificata, riceverai un link."}

    verification_token = secrets.token_urlsafe(32)
    verification_hash = _hash_token(verification_token)

    from datetime import timedelta
    expires = (utc_now() + timedelta(hours=24)).isoformat()

    await customer_account_repository.update(account["id"], {
        "verification_token_hash": verification_hash,
        "verification_token_expires": expires,
        "updated_at": utc_now(),
    })

    try:
        # Per-store branding (Onda 6): resend keeps the original store identity.
        signup_slug = account.get("signup_slug")
        email_ctx = await _load_email_context(org_id, store_slug=signup_slug)
        email_slug = await resolve_slug_for_org(org_id, preferred=signup_slug)
        send_customer_verification(email, verification_token, account.get("locale", "it"),
                                   sender_name=email_ctx["sender_name"], reply_to=email_ctx["reply_to"],
                                   store_name=email_ctx["store_name"],
                                   store_slug=email_slug)
    except Exception as e:
        logger.error("customer_resend_verification: failed: %s", e)

    return {"message": "Se l'email esiste e non e' verificata, riceverai un link."}


# ── Account-to-Customer Linking (ORG-SCOPED) ────────────────────────────────

async def _link_account_to_existing_customers(account_id: str, email: str, org_id: str):
    """Link newly created customer_account to existing customer records IN THE SAME ORG.

    Runs at signup time. Only links records within the same organization.
    No cross-org linking ever happens.
    """
    from database import customers_collection, orders_collection

    import re
    email_pattern = re.compile(f"^{re.escape(email)}$", re.IGNORECASE)

    # Only within this org
    cursor = customers_collection.find(
        {"organization_id": org_id, "email": email_pattern, "customer_account_id": None},
        {"_id": 0, "id": 1},
    )
    customer_docs = await cursor.to_list(500)

    if not customer_docs:
        return

    customer_ids = [d["id"] for d in customer_docs]

    await customers_collection.update_many(
        {"id": {"$in": customer_ids}, "organization_id": org_id, "customer_account_id": None},
        {"$set": {"customer_account_id": account_id}},
    )

    await orders_collection.update_many(
        {"customer_id": {"$in": customer_ids}, "organization_id": org_id, "customer_account_id": None},
        {"$set": {"customer_account_id": account_id}},
    )

    logger.info(
        "customer_linking: linked account=%s to %d customer records in org=%s",
        account_id, len(customer_ids), org_id,
    )
