from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

# Configuration
# Fail-fast: raise at import time if the secret is not set, rather than silently
# using a weak default that would make every JWT token forgeable.
_jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
if not _jwt_secret:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable is not set. "
        "Set a strong random secret (e.g. 'openssl rand -hex 32') "
        "in your .env file before starting the server."
    )
SECRET_KEY = _jwt_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ── Password complexity policy ────────────────────────────────────────────────
# Applied only when a password is *newly submitted* (signup, reset, change).
# Existing hashes are never re-validated — users with old weak passwords can
# still log in; they'll be required to meet the policy on next password change.

PASSWORD_MIN_LENGTH = 12

def validate_password_strength(password: str) -> None:
    """
    Raise ValueError with a user-friendly message if *password* does not
    meet the current complexity policy.

    Policy (configurable via constants above):
      - ≥ PASSWORD_MIN_LENGTH characters
      - at least one lowercase letter
      - at least one uppercase letter
      - at least one digit
      - (special characters NOT required for now)
    """
    errors: list[str] = []

    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"almeno {PASSWORD_MIN_LENGTH} caratteri")
    if not any(c.islower() for c in password):
        errors.append("almeno una lettera minuscola")
    if not any(c.isupper() for c in password):
        errors.append("almeno una lettera maiuscola")
    if not any(c.isdigit() for c in password):
        errors.append("almeno un numero")

    if errors:
        raise ValueError(
            "La password deve contenere: " + ", ".join(errors) + "."
        )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        # iat (issued-at) as Unix int — used by get_current_user() to detect
        # tokens issued before a password change (token invalidation).
        "iat": int(now.timestamp()),
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Validate the Bearer token and return the authenticated user context.

    Security guarantees (v2.7 + v2.8):
    - Token signature and expiry are verified by decode_token().
    - User existence and is_active flag are verified against the DB on every
      request, so a deactivated account cannot keep using an issued token.
    - Role and organization_id are read from the DB (authoritative source),
      not from the token, so role changes take effect immediately.
    - system_admin users have organization_id=None in both DB and JWT;
      the check uses key-presence (not truthiness) to allow None values.

    The DB lookup is a single find_one on the indexed 'id' field (~1-2 ms).
    Import is deferred to avoid a circular dependency at module load time:
      auth ← repositories.user_repository ← database / models
    (none of those modules import auth, so there is no cycle at runtime).
    """
    # Step 1 — decode and validate JWT signature / expiry
    token = credentials.credentials
    payload = decode_token(token)

    user_id = payload.get("sub")
    # IMPORTANT: check key *presence*, not truthiness.
    # system_admin tokens have org_id=None (the key exists, value is null).
    # Using `not payload.get("org_id")` would incorrectly reject them because
    # `not None` evaluates to True.  We only want to reject tokens that are
    # missing the "org_id" claim entirely (malformed tokens).
    # Guard: reject customer tokens — they must never reach admin endpoints.
    if payload.get("type") == "customer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    if not user_id or "org_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Step 2 — verify the user still exists and is active in the DB
    # Deferred import to avoid circular dependency (see docstring above).
    from repositories import user_repository  # noqa: PLC0415

    user_doc = await user_repository.find_by_id(user_id)

    if not user_doc:
        # User was deleted after the token was issued.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_doc.get("is_active", True):
        # Account deactivated after the token was issued.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 3 — verify the user's organization is not suspended (v3.0)
    # system_admin users have organization_id=None → skip the org check.
    # Org-scoped users get a 403 immediately if their org is suspended, so
    # suspended-org users cannot use existing tokens without a token revocation step.
    org_id = user_doc.get("organization_id")
    if org_id:
        from repositories import organization_repository  # noqa: PLC0415
        org_doc = await organization_repository.find_by_id(org_id)
        if org_doc and not org_doc.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization account is suspended",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Step 4 — token invalidation after password change.
    # If the user has a password_changed_at timestamp in the DB, reject any token
    # whose iat (issued-at) predates it.  Tokens issued on or after the password
    # change are still valid (the user's current session is preserved).
    # Backward compat: users/tokens without this field skip the check entirely.
    pcat_str = user_doc.get("password_changed_at")
    if pcat_str:
        token_iat = payload.get("iat")  # int Unix timestamp, or None for old tokens
        if token_iat is None:
            # Old token without iat — must have been issued before we started
            # embedding iat, which means it predates any password change.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessione scaduta. Effettua di nuovo il login.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            pcat_dt = datetime.fromisoformat(pcat_str)
            if pcat_dt.tzinfo is None:
                pcat_dt = pcat_dt.replace(tzinfo=timezone.utc)
            if token_iat < int(pcat_dt.timestamp()):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sessione scaduta. Effettua di nuovo il login.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except (ValueError, TypeError):
            pass  # Malformed field — skip check, don't break all requests

    # Track O Step 4.3 — logout-all-sessions invalidation (parallel a
    # password_changed_at). Quando user invoca POST /api/auth/logout-all
    # noi settiamo tokens_invalidated_at = now. Get_current_user qui
    # rifiuta ogni token con iat < quel timestamp.
    #
    # Pattern: ortogonale a password_changed_at (entrambi valid; il check
    # piu' restrittivo vince). Use case logout-all senza password change:
    #   - "Forgot to logout on shared device" → no password rotation needed
    #   - "Sospetto session hijack" → invalidate all without losing password
    #   - "Sold laptop without wipe" → instant invalidation panic button
    tinv_str = user_doc.get("tokens_invalidated_at")
    if tinv_str:
        token_iat = payload.get("iat")
        if token_iat is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessione scaduta. Effettua di nuovo il login.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            tinv_dt = datetime.fromisoformat(tinv_str)
            if tinv_dt.tzinfo is None:
                tinv_dt = tinv_dt.replace(tzinfo=timezone.utc)
            if token_iat < int(tinv_dt.timestamp()):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sessione invalidata. Effettua di nuovo il login.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except (ValueError, TypeError):
            pass  # Malformed — fail-open per non bloccare ogni request

    # Step 5 — populate per-request observability context (Phase 1 Step A3)
    # Safe to call even before request_context middleware has wrapped the
    # request: ContextVars default to None, set propagates within the asyncio
    # task. Captured automatically by the JSON log formatter for every
    # subsequent logger.info / .warning / .error call within this request.
    try:
        from core.observability import set_user_id, set_org_id
        set_user_id(user_doc["id"])
        set_org_id(user_doc["organization_id"])
    except Exception:
        # Defensive: must never break authentication on observability glitch.
        pass

    # Step 6 — return DB-authoritative values (role + org_id from DB, not token)
    return {
        "user_id":         user_doc["id"],
        "organization_id": user_doc["organization_id"],
        "role":            user_doc["role"],   # authoritative: role changes take effect immediately
        "email":           user_doc["email"],
        "locale":          user_doc.get("locale", "it"),  # AI locale awareness
        "token_iat":       payload.get("iat"), # forwarded so change_password can set pcat = iat
        # Onda 28 — surface email_verified so get_verified_user (and any
        # endpoint that uses get_current_user directly) can read it.
        # Default True for safety: if the field is missing from the user_doc
        # for legacy reasons, we don't want to lock anyone out — they would
        # have been gated at login already if verification was incomplete.
        "email_verified":  user_doc.get("email_verified", True),
    }


# ─── Onda 28 — Email verification gate ──────────────────────────────────────
#
# `get_verified_user` is a thin wrapper around `get_current_user` that
# additionally rejects users who haven't verified their email. It's the
# canonical dependency for endpoints that should be gated until the user
# has confirmed ownership of their email — i.e. virtually every business
# endpoint after Onda 28.
#
# WHITELIST (endpoints that MUST keep using get_current_user, NOT
# get_verified_user, otherwise the user can never escape the un-verified
# state):
#   - POST /api/auth/verify-email           (the very call that flips email_verified=true)
#   - POST /api/auth/resend-verification    (must be callable to resend the link)
#   - GET  /api/auth/me                     (frontend polls this to detect verification)
#   - POST /api/auth/logout                 (always allowed)
#   - POST /api/auth/change-password        (operational; user may need to recover access)
#
# BYPASS for system_admin: an operator with role=system_admin is exempt
# from the verification gate so that emergency support can never lock
# itself out. This mirrors the existing bypass in services/auth_service.py
# at the login step (Onda <pre-27>: system_admin can log in even with
# email_verified=false).
#
# RESPONSE on gate failure: 403 with a structured detail including
# {error: "email_not_verified", user_email}. The frontend
# (Onda 28 ProtectedRoute + VerifyEmailRequiredPage) reads this and
# redirects to /verify-email-required automatically.
async def get_verified_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Like get_current_user, but rejects users who haven't verified email yet.

    Use this dependency for every endpoint that gates business
    functionality on email verification. Use the underlying
    get_current_user only on the small whitelist documented above.

    system_admin role bypasses the check (operational continuity).

    Raises:
        HTTPException 403 with detail={"error": "email_not_verified", ...}
        when the authenticated user has email_verified=false and is not
        a system_admin.
    """
    # System admins bypass — keeps support/recovery operational.
    if current_user.get("role") == "system_admin":
        return current_user

    if not current_user.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "email_not_verified",
                "message": "Email verification required to access this resource",
                "user_email": current_user.get("email"),
            },
        )
    return current_user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Allow only org-level admins. System admin must use require_system_admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_verified_admin(current_user: dict = Depends(require_admin)) -> dict:
    """Org admin (role == 'admin') AND email-verified.

    R8 — gate per le configurazioni embed (CORS allowed_origins, snippet,
    preview token): un admin con email non verificata non deve poter aprire
    origin CORS o generare snippet. `require_admin` ha già rifiutato
    system_admin e i non-admin; qui aggiungiamo solo il vincolo di verifica
    email (stesso error shape di get_verified_user per coerenza client).
    """
    if not current_user.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "email_not_verified",
                "message": "Email verification required to access this resource",
                "user_email": current_user.get("email"),
            },
        )
    return current_user


async def require_system_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Allow access only to platform-level system administrators.

    - Grants access when role == "system_admin".
    - Org-level admins (role == "admin") receive 403 — they must use require_admin.
    - Regular users receive 403.
    - System admins have organization_id=None; this dependency does NOT enforce
      org scoping (that is by design — system admin routes are cross-tenant).

    Use on /admin/* routes only.  Never use on org-scoped routes.
    """
    if current_user.get("role") != "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System administrator access required",
        )
    return current_user


# ── Customer Identity Foundation (v9.0 → v9.1 org-scoped) ───────────────────
# Separate auth layer for public-facing customer accounts.
# Customer tokens carry type="customer" + org_id for tenant isolation.
# get_current_customer() rejects admin tokens; get_current_user() rejects customer tokens.


def create_customer_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT for a customer account. Injects type=customer claim.

    data MUST include: sub (account_id), org_id (organization_id), email.
    """
    token_data = {**data, "type": "customer"}
    return create_access_token(token_data, expires_delta)


# Separate HTTPBearer instance for customer endpoints — keeps OpenAPI docs clean
customer_security = HTTPBearer()


async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(customer_security),
) -> dict:
    """
    Validate a customer Bearer token and return the authenticated customer context.

    Security guarantees:
    - Only accepts tokens with type="customer" (rejects admin tokens)
    - Verifies account exists, is_active, email_verified
    - Enforces password_changed_at token invalidation
    - Returns customer_account_id + organization_id for tenant-scoped access
    """
    token = credentials.credentials
    payload = decode_token(token)

    # Must be a customer token
    if payload.get("type") != "customer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    account_id = payload.get("sub")
    if not account_id or not payload.get("org_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Deferred import to avoid circular dependency
    from repositories import customer_account_repository  # noqa: PLC0415

    account = await customer_account_repository.find_by_id(account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not account.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not account.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Token invalidation after password change (same pattern as admin)
    pcat_str = account.get("password_changed_at")
    if pcat_str:
        token_iat = payload.get("iat")
        if token_iat is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            pcat_dt = datetime.fromisoformat(pcat_str)
            if pcat_dt.tzinfo is None:
                pcat_dt = pcat_dt.replace(tzinfo=timezone.utc)
            if token_iat < int(pcat_dt.timestamp()):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except (ValueError, TypeError):
            pass

    # Track O Step 4.3 — logout-all-sessions invalidation (mirror del check
    # admin sopra). Customer puo' invocare POST /api/customer-auth/logout-all
    # per setting tokens_invalidated_at = now → tutti i token < now rifiutati.
    tinv_str = account.get("tokens_invalidated_at")
    if tinv_str:
        token_iat = payload.get("iat")
        if token_iat is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalidated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            tinv_dt = datetime.fromisoformat(tinv_str)
            if tinv_dt.tzinfo is None:
                tinv_dt = tinv_dt.replace(tzinfo=timezone.utc)
            if token_iat < int(tinv_dt.timestamp()):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session invalidated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except (ValueError, TypeError):
            pass

    # Verify org_id in token matches account's org (defense in depth)
    token_org = payload.get("org_id")
    account_org = account.get("organization_id")
    if token_org and account_org and token_org != account_org:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token org mismatch",
        )

    return {
        "customer_account_id": account["id"],
        "organization_id": account["organization_id"],
        "email": account["email"],
        "name": account["name"],
        "locale": account.get("locale", "it"),
    }
