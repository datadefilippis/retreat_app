"""
Customer Account model — public-facing customer identity (login).

Separate from the admin `users` collection by design:
- customer_accounts is ORG-SCOPED (one account per org per email)
- the same email can register on different organizations independently
- JWT tokens carry type="customer" + org_id to enforce strict tenant isolation

This model holds auth credentials only — not CRM data.
CRM data stays in the org-scoped `customers` collection,
linked via `customer_account_id` FK.
"""

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from .common import generate_id, utc_now


# ── Stored Document ────────────────────────────────────────────────────────

class CustomerAccount(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str                                # Tenant isolation — required
    email: str                                          # Stored normalised (lowercase, stripped)
    name: str = Field(min_length=1, max_length=255)
    password_hash: str

    is_active: bool = True
    email_verified: bool = False

    # Email verification (one-time token, SHA-256 hashed)
    verification_token_hash: Optional[str] = None
    verification_token_expires: Optional[str] = None   # ISO UTC

    # Password reset (one-time token, SHA-256 hashed)
    reset_token_hash: Optional[str] = None
    reset_token_expires: Optional[str] = None          # ISO UTC

    # Token invalidation
    password_changed_at: Optional[str] = None          # ISO UTC

    last_login_at: Optional[str] = None                # ISO UTC
    locale: str = "it"

    # ── Onda 29 — Anti-bruteforce hardening ─────────────────────────────────
    # Per-account lockout state. Keyed on the account itself, complementary
    # to the per-IP rate limit on the customer auth router (Onda 27.2).
    # Together: per-IP limit catches brute-force from a single source;
    # per-account lockout catches distributed brute-force (botnet, multi-IP)
    # against a specific email.
    #
    # Lifecycle (see services/customer_auth_service.py customer_login):
    #   · on each failed login: $inc failed_login_attempts,
    #     $set last_failed_login_at
    #   · when failed_login_attempts reaches LOCKOUT_THRESHOLD: $set
    #     locked_until = now + duration, $inc lockout_count_today,
    #     $set failed_login_attempts = 0 (the counter has done its job —
    #     it now restarts toward the next threshold AFTER the lockout
    #     window).
    #   · on successful login: $set failed_login_attempts = 0,
    #     $set locked_until = None, $set lockout_count_today = 0.
    #   · on successful password reset (via /customer-auth/reset-password):
    #     same reset as above (the user proved control of their inbox).
    #   · daily cron resets lockout_count_today across all accounts (so
    #     yesterday's lockouts don't extend today's backoff).
    #
    # All four fields default to safe-zero values for backward compat —
    # legacy accounts created before Onda 29 work unchanged on first read.
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None                  # ISO UTC; None = not locked
    lockout_count_today: int = 0                        # for exponential backoff
    last_failed_login_at: Optional[str] = None          # ISO UTC; audit only

    # Slug (store or legacy org public_slug) used during signup. Carried
    # through the verification/reset email flows so the post-link landing
    # page can route the user back to the correct storefront login —
    # localStorage alone is unreliable when users browse multiple stores
    # or click the email link from a different device. Optional + opt-in
    # so legacy accounts (created before this field existed) keep working
    # via the org-side fallback in customer_auth_service.
    signup_slug: Optional[str] = None

    # Wave GDPR-Commerce CG-4 (2026-05-18) — per-store consent snapshot.
    #
    # The customer accepted the MERCHANT'S Privacy + Terms at signup
    # time. Each field captures (a) the version string (tag:hash) of
    # the doc as it was live on the merchant's storefront, plus (b)
    # the locale frozen at acceptance time (= store.merchant_legal_display_locale
    # at the moment of signup) so we can prove which exact rendered
    # text the customer saw.
    #
    # The immutable record lives in consent_audit (CG-1 extended schema);
    # these fields on the account doc are the FAST-PATH read used by
    # /customer-portal/me to decide whether the re-consent modal must
    # block the app on the next page load.
    #
    # All Optional → legacy customer_accounts (pre-CG-4) deserialize
    # cleanly. The re-consent flow will treat None as "stale" and ask
    # for fresh acceptance.
    accepted_store_terms_version: Optional[str] = None       # "v1.0:abc..."
    accepted_store_terms_locale: Optional[str] = None         # frozen
    accepted_store_terms_at: Optional[str] = None             # ISO UTC
    accepted_store_privacy_version: Optional[str] = None
    accepted_store_privacy_locale: Optional[str] = None
    accepted_store_privacy_at: Optional[str] = None
    # Marketing opt-in (separate optional consent — must NEVER be a
    # blocker on signup). ``accepted_marketing_at`` carries the
    # opt-in timestamp; ``marketing_revoked_at`` is set when the
    # customer toggles off in the portal. Both null = never opted in.
    accepted_marketing_at: Optional[str] = None
    marketing_revoked_at: Optional[str] = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ── API Contracts ──────────────────────────────────────────────────────────

class CustomerAccountCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)


class CustomerAccountLogin(BaseModel):
    email: EmailStr
    password: str


class CustomerAccountResponse(BaseModel):
    """Safe public fields — no password_hash, no tokens."""
    id: str
    organization_id: str
    email: str
    name: str
    is_active: bool
    email_verified: bool
    locale: str
    created_at: datetime

    # Wave GDPR-Commerce CG-4 — consent snapshot + computed refresh hint.
    # The frontend reads ``consent_needs_refresh`` on every customer-portal
    # boot and renders the blocking <CustomerReconsentModal/> when True.
    # All Optional → legacy customers without a value default to "needs
    # refresh" on the next read (handled in customer_auth_service).
    accepted_store_terms_version: Optional[str] = None
    accepted_store_privacy_version: Optional[str] = None
    accepted_marketing_at: Optional[str] = None
    marketing_revoked_at: Optional[str] = None
    current_store_legal_version: Optional[str] = None   # what the store is at right now
    consent_needs_refresh: bool = False                  # server-computed


class CustomerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer: CustomerAccountResponse
