from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from .common import generate_id, utc_now


class UserRole(str, Enum):
    # ── Platform-level role (no org scope) ──────────────────────────────────
    # system_admin users have organization_id=None in the DB and in the JWT.
    # They CANNOT be created via any API endpoint — use scripts/create_system_admin.py.
    # Protected by require_system_admin dependency (auth.py).
    SYSTEM_ADMIN = "system_admin"  # platform-level, organization_id=None
    # ── Org-level roles (always scoped to an organization_id) ────────────────
    ADMIN = "admin"  # org-level administrator
    USER  = "user"   # org-level standard user


class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole = UserRole.USER


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=12)
    organization_name: Optional[str] = None  # For signup
    invite_token: Optional[str] = None       # Platform invite token (invite-only mode)
    accepted_terms: bool = False             # Must be True to register (not stored in DB)
    locale: Optional[str] = "it"             # Language preference from signup form
    # Track O Step 4.1 — honeypot field for anti-bot. Frontend renders
    # this as a hidden input (display:none / off-screen) so humans never
    # see it; naive bots that fill every form input will populate it and
    # be silently rejected. Field name 'website' is intentionally
    # innocuous-looking to maximize bot fill rate.
    # See backend/core/honeypot.py for details + threat model.
    website: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    # Optional: system_admin users have organization_id=None (not scoped to any org).
    # All org-level users (admin, user) always have a non-null string value here.
    organization_id: Optional[str] = None
    password_hash: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    is_active: bool = True

    # ── Phase-1 additions (all Optional → zero breaking change) ──────────────
    last_login_at: Optional[datetime] = None
    preferences: Optional[Dict[str, Any]] = None  # UI preferences bag
    mfa_enabled: Optional[bool] = None
    # ── Security: token invalidation after password change ────────────────────
    # Set to utcnow() whenever password is changed (self-service or admin reset).
    # get_current_user() rejects tokens whose iat < this value.
    # None = no password change has occurred → all tokens are valid.
    password_changed_at: Optional[str] = None
    # ── Security: force password change on first login ────────────────────────
    # True for invited users and after admin password reset.
    # Cleared to False after a successful change_password.
    must_change_password: bool = False
    # ── Security: self-service password reset tokens ──────────────────────────
    # SHA256 hex digest of the one-time reset token (plaintext never stored).
    # Cleared after successful use or expiry.
    reset_token_hash: Optional[str] = None
    reset_token_expires: Optional[str] = None  # ISO UTC timestamp
    # ── Email verification ──────────────────────────────────────────────────
    # False until the user clicks the verification link sent after signup.
    # Existing users without this field default to False (backward-compatible).
    email_verified: bool = False
    # ── i18n: user interface locale ────────────────────────────────────────────
    # ISO 639-1 language code.  Allowed: "it", "en", "de", "fr".
    # Default "it" (Italian).  Validated at the API layer.
    locale: str = "it"
    # SHA256 hex digest of the one-time verification token.
    verification_token_hash: Optional[str] = None
    verification_token_expires: Optional[str] = None  # ISO UTC timestamp
    # ── Legal: terms & privacy acceptance ────────────────────────────────────
    # ISO UTC timestamp of when the user accepted Terms of Service & Privacy Policy.
    # None for legacy users created before this field existed.
    accepted_terms_at: Optional[str] = None
    # ── Wave GDPR-Admin Phase B (2026-05-16) — consent versioning ───────────
    # SHA256 hex digest (first 16 chars) of the legal documents text the
    # user actually saw at signup time. If we later update the Privacy
    # Policy or T&C, this lets us prove WHICH version each user agreed
    # to in case of dispute.
    #
    # Format: "<version_tag>:<hash_16>" e.g. "v1.0:a3f2c8e9d1b4f5a6"
    #   - version_tag bumped manually when content changes (semver-ish)
    #   - hash is the SHA256 hex truncated to 16 chars of the rendered
    #     privacy_<locale>.md + terms_<locale>.md concatenated
    #
    # Legacy users (created before Phase B) have this field = None on
    # first read; the GDPR-Admin Phase B backfill marks them as
    # "v0.legacy:unknown".
    accepted_terms_version: Optional[str] = None
    # ── Wave GDPR-Admin Phase B — locale at acceptance ──────────────────────
    # ISO 639-1 locale code ("it" | "en" | "de" | "fr") of the version
    # the user accepted. Distinct from User.locale (which is the UI
    # preference and CAN change later) — accepted_terms_locale is FROZEN
    # at the moment of signup acceptance, never updated.
    #
    # Legacy users get backfilled to their current User.locale value
    # (best-effort approximation of what they likely saw).
    accepted_terms_locale: Optional[str] = None

    # ── Onda 30 — Anti-bruteforce hardening (admin/owner side) ───────────────
    # Mirror of CustomerAccount Onda 29 fields. Per-account lockout state
    # complementary to the per-IP rate limit (Onda 27.2). Together: per-IP
    # limit catches single-source brute-force; per-account lockout catches
    # distributed brute-force (botnet, multi-IP) against a specific email.
    #
    # IMPORTANT: enforcement in services/auth_service.login() bypasses the
    # lockout for users with role=system_admin — operational continuity, so
    # the platform operator can never lock themselves out. Same bypass
    # pattern as Onda 28 email_verified.
    #
    # All four fields default to safe-zero values for backward compat.
    # Legacy users created before Onda 30 work unchanged on first read.
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None                  # ISO UTC; None = not locked
    lockout_count_today: int = 0                        # for exponential backoff
    last_failed_login_at: Optional[str] = None          # ISO UTC; audit only


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: UserRole
    # None for system_admin users; always a string for org-level users.
    organization_id: Optional[str] = None
    created_at: datetime
    is_active: bool
    must_change_password: bool = False
    email_verified: bool = False
    locale: str = "it"
    currency: str = "EUR"
    default_iva: Optional[float] = None  # org-level default IVA for purchases
    # ── Wave GDPR-Admin Phase E (2026-05-18) — re-consent enforcement ───
    # Exposes the user's accepted legal version + the current platform
    # version so the frontend can detect mismatches and trigger the
    # blocking <ReconsentModal/>. Legacy users (created before Phase B)
    # have ``accepted_terms_version=None`` until backfill or first
    # re-acceptance.
    #
    # ``consent_needs_refresh`` is server-computed:
    #   True iff accepted_terms_version != current_version_string()
    # The frontend treats True as "show the modal, block the app".
    accepted_terms_version: Optional[str] = None
    accepted_terms_locale: Optional[str] = None
    accepted_terms_at: Optional[str] = None
    current_terms_version: Optional[str] = None
    consent_needs_refresh: bool = False


class UserInvite(BaseModel):
    email: EmailStr
    name: str
    role: UserRole = UserRole.USER


class UserInviteResponse(UserResponse):
    """Returned only from POST /organizations/team/invite.
    Includes the one-time temp_password so the admin can share it with the new member.
    Not stored in DB — generated at invite time and returned once."""
    temp_password: str
