import re
import secrets
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from .common import generate_id, utc_now

_SLUG_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$')


class OrganizationBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    industry: Optional[str] = Field(default=None, max_length=100)


class OrganizationCreate(OrganizationBase):
    pass


# ── Release 4 (Courses) Step 1: external integrations ────────────────────────
# Per-org credentials for third-party services. Kept as a dedicated
# sub-object so it stays Optional (vecchie org continuano a funzionare
# senza tocco). Future integrations (es. Vimeo, Cloudflare Stream) si
# aggiungono qui senza modificare i campi esistenti.

class BunnyIntegration(BaseModel):
    """Bunny Stream credentials for an organization.

    library_id: numeric ID of the Bunny video library that hosts the
                course videos for this org.
    api_key:    Bunny Stream library API key. Used server-side for
                management calls (future: list videos, upload, etc).
                Never exposed to the frontend.
    token_security_key: the Library's "Token Authentication Key" used to
                sign embed URLs (HMAC-SHA256). When omitted falls back
                to `api_key` — Bunny libraries can be configured with a
                single key for both roles, but the recommended setup
                has a dedicated signing key. Stored in plain text for
                MVP; future: encrypt at rest via vault.
    cdn_hostname: pull-zone hostname, e.g. "vz-xxxx-yyy.b-cdn.net".
                Reserved for future use (direct CDN URLs / thumbnails).
    watermark_enabled: when True, the player overlays the customer
                email/identifier on the video to deter screen recording.
                Implemented as an HTML overlay on the iframe (MVP);
                future: Bunny native watermark via player config.

    Verification status fields (populated by services/bunny/verifier.py
    via the auto-verify-on-PATCH hook in routers/organizations.py).
    All Optional so legacy orgs (configured before this feature) keep
    working — they'll show as "Mai testato" in the admin UI until they
    next save / click Test.

    last_verified_at: timestamp of the last probe attempt (any outcome)
    last_verification_status: stringified BunnyStatus value
                ("ok" | "unauthorized" | "library_not_found" |
                 "network_error" | "unknown" | "not_configured").
                Stored as raw string instead of enum for Mongo
                forward-compat: adding a new status doesn't require a
                migration.
    last_verification_error: human-readable Italian error message when
                last_verification_status != "ok". Surfaced verbatim in
                the admin UI.
    library_name: name of the connected Bunny library, fetched on
                successful verification. Visible to the admin as proof
                of identity ("Connesso a 'Olistica Studio'").
    video_count: number of videos in the connected library at last
                verification. May be 0 (empty library is still OK).
    """

    model_config = ConfigDict(extra="ignore")

    library_id: str = Field(min_length=1, max_length=64)
    api_key: str = Field(min_length=1, max_length=255)
    token_security_key: Optional[str] = Field(default=None, max_length=255)
    cdn_hostname: Optional[str] = Field(default=None, max_length=255)
    watermark_enabled: bool = True

    # ── Verification status (Optional → legacy orgs keep working) ───────
    last_verified_at: Optional[datetime] = None
    last_verification_status: Optional[str] = Field(default=None, max_length=32)
    last_verification_error: Optional[str] = Field(default=None, max_length=512)
    library_name: Optional[str] = Field(default=None, max_length=255)
    video_count: Optional[int] = Field(default=None, ge=0)


# ── Multi-library Bunny support (Step 1 of multi-library feature) ──────────
#
# Each org can connect N independent Bunny libraries. Use cases:
#   • One library for "Premium courses", one for "Free content"
#   • Per-segment libraries (B2B vs B2C)
#   • Geographic separation (EU vs US Bunny regions)
#
# Each library carries its own credentials AND its own verification
# status, so the admin sees per-library health independently.
#
# Identity model: AFianco-side `id` (stable, opaque) + admin-friendly
# `alias` (renamable). Lessons reference libraries by `id` so renaming
# the alias never breaks references. Bunny's own `library_id` (numeric
# string) is just one of the credential fields — not used as identity
# AFianco-side because two libraries with the same Bunny ID could
# never coexist (and we want N independent libraries possibly across
# different Bunny accounts).
#
# Backward compat: the legacy single `bunny: BunnyIntegration` field
# stays in place for orgs that haven't migrated. The resolver in
# `services/bunny/resolver.py` (Step 3) prefers `bunny_libraries` and
# falls back to `bunny`. Orgs are migrated explicitly via the
# `/migrate-legacy` endpoint (Step 5) — never automatically.

class BunnyLibrary(BaseModel):
    """One Bunny Stream library connected to this org.

    Mirrors the shape of the legacy `BunnyIntegration` (same
    credentials + verification status fields) but with three new
    AFianco-side identity fields (`id`, `alias`, `is_default`) so
    multiple libraries can coexist on the same org doc.

    Lifecycle:
      * `id` is generated server-side at creation (POST /libraries)
        and never changes. Lessons reference this id.
      * `alias` is admin-typed; renamable with no impact on lesson
        references.
      * `is_default` is unique within the org's `bunny_libraries`
        array — exactly one library is default at any time. The
        backend enforces this on save.

    Default-library semantics: a lesson without an explicit
    `bunny_library_id` falls back to the org's default library at
    resolve time (see services/bunny/resolver.py).
    """

    model_config = ConfigDict(extra="ignore")

    # ── AFianco-side identity ────────────────────────────────────────────
    # Short URL-safe id; collision-free for any reasonable N libraries
    # per org (8 bytes = ~11 chars after b64). Generated server-side.
    id: str = Field(default_factory=lambda: secrets.token_urlsafe(8), max_length=32)
    alias: str = Field(min_length=1, max_length=64)
    is_default: bool = False

    # ── Bunny credentials (same as legacy BunnyIntegration) ──────────────
    library_id: str = Field(min_length=1, max_length=64)
    api_key: str = Field(min_length=1, max_length=255)
    token_security_key: Optional[str] = Field(default=None, max_length=255)
    cdn_hostname: Optional[str] = Field(default=None, max_length=255)
    watermark_enabled: bool = True

    # ── Verification status (same shape as legacy, populated by
    #     services/bunny/verifier.py via auto-verify on PATCH) ────────────
    last_verified_at: Optional[datetime] = None
    last_verification_status: Optional[str] = Field(default=None, max_length=32)
    last_verification_error: Optional[str] = Field(default=None, max_length=512)
    library_name: Optional[str] = Field(default=None, max_length=255)
    video_count: Optional[int] = Field(default=None, ge=0)

    # ── Lifecycle timestamps (informational; not used for cascade) ───────
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrgIntegrations(BaseModel):
    """Bag of per-org external integrations. All fields Optional so an
    Organization can adopt them à la carte."""

    model_config = ConfigDict(extra="ignore")

    # Legacy single-library Bunny config. Kept for backward
    # compatibility — orgs configured before the multi-library feature
    # keep working unchanged. The resolver tolerates both shapes.
    bunny: Optional[BunnyIntegration] = None

    # NEW: multi-library Bunny array. When non-empty, the resolver
    # prefers it over `bunny`. Default `[]` so orgs without any Bunny
    # config (or legacy orgs that haven't migrated) keep loading
    # without errors.
    bunny_libraries: List[BunnyLibrary] = Field(default_factory=list)


# ── Org-level branding (Step 1 of "olistic settings" feature) ────────────────
#
# Until now branding (logo, colors) lived only on the per-store document
# (`backend/models/store.py`). For organizations with N stores under the
# same brand this meant uploading the same logo N times. We add an
# *organization-level* branding sub-object that:
#
#   1. Acts as **default** for all stores under this org.
#   2. Is **overridable** per-store (existing Store branding fields win
#      when set — no behavior change for stores already configured).
#   3. Feeds the customer auth pages automatically (they read from the
#      catalog response which uses `branding_service.resolve_for_store`).
#   4. Stays Optional so orgs that don't opt in see ZERO change.
#
# Inheritance semantics implemented in `services/branding_service.py`:
#
#   resolved.field = store.field if store.field is not None else org.field
#
# i.e. any non-None Store value (including "") wins. This lets a store
# explicitly clear inheritance ("I want no logo, even though the org
# has one") by saving "" instead of null.
#
# Adding new branding fields later (favicon, footer text, etc.) is a
# 4-touch change: this model + the resolver + the catalog endpoint
# (already centralized) + the admin UI.

class OrgBranding(BaseModel):
    """Org-level branding defaults inherited by every store under this org.

    All fields Optional. Empty Branding object == "inherit nothing" ==
    every store falls through to the platform-level fallback ("AFianco").
    """

    model_config = ConfigDict(extra="ignore")

    # Logo URL — relative path under /uploads/logos/org/ when uploaded
    # via POST /organizations/me/branding/logo, but any URL is accepted
    # (e.g. a CDN-hosted asset).
    logo_url: Optional[str] = Field(default=None, max_length=512)

    # Brand color used as primary accent across storefronts and the
    # auth shell header. Hex string like "#1a1a1a". Validation kept
    # loose for MVP — admin form already enforces format client-side.
    brand_color: Optional[str] = Field(default=None, max_length=32)

    # Foreground color for text rendered ON brand_color (typically
    # white on dark brand, black on light brand). When unset, the
    # frontend defaults to white.
    brand_color_text: Optional[str] = Field(default=None, max_length=32)

    # Tab favicon. Reserved for a follow-up step that actually wires
    # the favicon into HTML <head>. Defining it here keeps the schema
    # ready so we don't bump the model later.
    favicon_url: Optional[str] = Field(default=None, max_length=512)


# ── Phase 0 Step 9 (2026-05-28) — Organization Feature Flags ──────────────
#
# Granular feature toggles per-organization. Tutti default False per
# garantire backward compat + opt-in conscious rollout.
#
# Naming convention:
#   <feature_name>_enabled: bool = False
#
# Aggiungere una nuova flag è additivo — no DB migration richiesta
# (Pydantic legge campo mancante come default False).


class OrganizationFeatureFlags(BaseModel):
    """Per-organization granular feature flags.

    Permettono di abilitare progressivamente le nuove capability
    dell'evoluzione e-commerce (Stream A embed, Stream B AI builder)
    per cohort selezionate di merchant, prima del rollout massivo.

    Lettura: ``services.feature_flag_service.is_enabled(org_id, flag_name)``.
    Scrittura: solo via admin endpoint ``/api/admin/feature-flags/{org_id}``
    (richiede system_admin role).
    """

    model_config = ConfigDict(extra="ignore")

    # ── Phase 0 features ─────────────────────────────────────────────────

    # Step 4b — Frontend dual-write sidecar attivo per questa org.
    # Default False (storefront classic usa sessionStorage standalone).
    # Quando True: useStorefrontCart attiva il sidecar usePersistentCartSync.
    persistent_cart_enabled: bool = False

    # ── Stream A features (futuri) ───────────────────────────────────────

    # Embed widget abilitato: merchant può embedare i suoi prodotti su
    # siti esterni via /api/public/embed/*. Richiede anche
    # store.allowed_origins configurati.
    embed_widget_enabled: bool = False

    # Custom domain abilitato: merchant può servire il proprio storefront
    # su shop.merchantbrand.com via Cloudflare for SaaS.
    custom_domain_enabled: bool = False

    # ── Stream B features (futuri) ───────────────────────────────────────

    # AI site builder abilitato: merchant può generare siti via chat con
    # Claude (slot tags afianco integrati).
    ai_site_builder_enabled: bool = False


class Organization(OrganizationBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # ── Phase-1 additions (all Optional → zero breaking change) ──────────────
    plan: Optional[str] = None              # "free" | "starter" | "pro" | "enterprise"
    data_classification: Optional[str] = None  # "internal" | "confidential" | "restricted"
    timezone: Optional[str] = None         # IANA timezone e.g. "Europe/Rome"
    currency: Optional[str] = None         # ISO 4217 e.g. "EUR"
    settings: Optional[Dict[str, Any]] = None  # flexible org-level settings bag

    # ── Sub-stream 2.6: AFianco platform application fee on Stripe Connect ──
    # When > 0, the connected-account checkout session passes
    # ``application_fee_amount`` to Stripe so AFianco keeps a slice of
    # each transaction. Default 0.0 for the first 10 founding clients
    # (free) and for any merchant pre-monetization. Capped at 10 so a
    # data-entry typo can't accidentally drain a merchant's revenue.
    application_fee_percent: float = Field(default=0.0, ge=0, le=10)

    # ── v3.0: org suspension (default True -> zero breaking change) ----------
    is_active: bool = True                  # False = suspended by system admin

    # ── v5.0: canonical billing fields (all Optional -> zero breaking change) ─
    commercial_plan_slug: str = "free"       # "free" | "core" | "pro" | "enterprise"
    stripe_customer_id: Optional[str] = None # cus_xxx
    stripe_subscription_id: Optional[str] = None  # sub_xxx (active Stripe sub)
    billing_status: str = "none"             # none|trialing|active|past_due|canceled|manual
    billing_interval: Optional[str] = None   # "month" | "year"
    trial_ends_at: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    plan_assigned_by: str = "system"         # "stripe"|"admin"|"system"|"signup"
    plan_assigned_at: Optional[datetime] = None
    billing_email: Optional[str] = None

    # ── v5.8 / Onda 5: grandfather pricing protection ───────────────────────
    # When the platform owner rebrands the public plans + creates new Stripe
    # Prices (Onda 9 manual ops), existing customers must keep paying their
    # original price. `legacy_pricing_lock=True` flags those orgs; the
    # checkout/modify flow then prefers `legacy_price_ids[plan_slug]` over
    # the new CommercialPlan.stripe_price_id_monthly.
    #
    # Set by `migrate_plan_relaunch_v5()` (idempotent one-shot migration)
    # for every org with an active stripe_subscription_id at the time the
    # migration runs. Brand-new signups never trip this flag — they pay
    # the new prices from day one.
    #
    # `legacy_price_ids` is a dict {plan_slug: stripe_price_id} captured
    # by reading sub.items.data[*].price.id at lock time, so the migration
    # is robust against future renames in Stripe.
    legacy_pricing_lock: bool = False
    legacy_pricing_locked_at: Optional[datetime] = None
    legacy_price_ids: Optional[Dict[str, str]] = None

    # ── v5.8 / Onda 9.T: Trial-once enforcement (anti-fraud) ────────────────
    # `has_used_trial` is the SOURCE OF TRUTH for the trial-once gate. Once
    # set True, NEVER reset (except by explicit admin override via the
    # /admin/organizations/{id}/grant-trial endpoint, audit-logged).
    #
    # Set by webhook `customer.subscription.created` when sub.trial_end is
    # not None. Survives cancellations, plan changes, and re-subscriptions.
    #
    # The previous gate used `org.trial_ends_at is not None` which was buggy
    # because `trial_ends_at` is reset to None during deprovision (canceled
    # → free), allowing the cancel-and-retry exploit:
    #   trial Solo → cancel → trial Starter → cancel → trial Pro → 42d free
    #
    # Use `has_used_trial` everywhere instead of `trial_ends_at` for gate
    # decisions. `trial_ends_at` remains a transient state field for the
    # CURRENT trial (cleared on deprovision is OK).
    has_used_trial: bool = False
    has_used_trial_at: Optional[str] = None       # ISO timestamp of FIRST trial start
    has_used_trial_plan_slug: Optional[str] = None  # which plan was the first trial on

    # Granular trial history — one entry per trial subscription.
    # Populated by webhook handlers as the trial lifecycle progresses.
    # Schema (each entry):
    #   {
    #     "plan_slug": "starter",
    #     "stripe_subscription_id": "sub_xxx",
    #     "billing_interval": "month" | "year",
    #     "started_at": "ISO",
    #     "ended_at": "ISO" | None,                # filled when trial closes
    #     "outcome": "converted" | "cancelled_during_trial" | "expired_to_free" | None,
    #     "cancellation_reason": "..." | None,
    #     "days_used": int | None,                  # computed at end
    #     "usage_snapshot": {                       # captured at trial end
    #       "ai_assistant.chat": int,
    #       "cashflow_monitor.data_rows": int,
    #       "commerce.orders_monthly": int,
    #       "product_catalog.products": int,
    #     },
    #     "conversion_lag_days": int | None,        # if converted, days from start to active
    #   }
    trial_history: List[Dict[str, Any]] = []

    # ── v6.0: self-service account deactivation (GDPR art. 17) ────────────
    # Set to utcnow() when the org admin deactivates the account.
    # After 30 days, the background hard-delete job permanently removes all data.
    # Reset to None on reactivation (within the 30-day grace period).
    deactivated_at: Optional[datetime] = None

    # ── v7.0: Public Layer ────────────────────────────────────────────────
    public_slug: Optional[str] = None

    # ── v8.0: Store Settings ──────────────────────────────────────────────
    store_settings: Optional[Dict[str, Any]] = None

    # ── Release 4 (Courses): external integrations (Optional → no breakage) ──
    # See BunnyIntegration above. Only orgs that sell video courses
    # populate `integrations.bunny`. Reading code MUST tolerate the
    # whole sub-object being None.
    integrations: Optional[OrgIntegrations] = None

    # ── Org-level branding defaults (Step 1 of olistic settings) ──────────
    # See OrgBranding above. Optional → orgs without it inherit the
    # platform-level fallback ("AFianco"). Only the resolver in
    # `services/branding_service.py` should read this — never read it
    # directly from a router (use the resolver so the cascade stays
    # in one place).
    branding: Optional[OrgBranding] = None

    # ── Phase 0 Step 9 (2026-05-28) — Organization feature flags ───────────
    # Per-organization control degli sblocchi feature evolutive (Stream A,
    # Stream B, ecc.). Diversamente dagli env var che sono globali, queste
    # flag permettono rollout granulare per cohort merchant:
    #   · Beta privata: enable per N merchant test
    #   · Plan-based: enable per merchant Pro+
    #   · Geo-based: enable per region
    #   · Manual: enable per uno specifico merchant via admin UI
    #
    # Tutte default False — solo system_admin può attivare via admin endpoint.
    # Lettura via services.feature_flag_service.is_enabled(org, flag_name).
    #
    # Naming convention: nome del feature in snake_case + "_enabled" suffix.
    # Aggiungere flag è additivo (default False = comportamento pre-feature).
    feature_flags: "OrganizationFeatureFlags" = Field(
        default_factory=lambda: OrganizationFeatureFlags()
    )

    @field_validator('public_slug', mode='before')
    @classmethod
    def validate_public_slug(cls, v):
        if v is None:
            return v
        v = str(v).lower().strip()
        if not _SLUG_PATTERN.match(v):
            raise ValueError(
                'public_slug must be 3-50 chars, lowercase alphanumeric and dashes, '
                'cannot start or end with a dash'
            )
        return v

    @field_validator('currency', mode='before')
    @classmethod
    def validate_currency(cls, v):
        """Restrict currency to the ISO codes we currently ship.

        ``None`` and ``""`` are accepted so legacy organisations created
        before this validator (currency may be missing on those docs)
        keep loading without errors. Any explicit value must be one of
        the supported currencies; the immutability check ("once orders
        exist, currency cannot change") lives at the router layer in
        ``update_organization`` since it requires a DB lookup.
        """
        if v is None or v == "":
            return None
        # Lazy import: avoid touching services/* at module import time
        # so model loading stays cheap and free of side effects.
        from services.currency_service import (
            UnsupportedCurrencyError,
            validate_currency_code,
        )
        try:
            return validate_currency_code(v)
        except UnsupportedCurrencyError as e:
            raise ValueError(str(e)) from e
