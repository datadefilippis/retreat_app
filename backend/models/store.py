"""
Store model — represents a storefront within an organization.

An organization can have multiple stores, each with its own:
- identity (name, description, contacts)
- catalog (subset of products via store_id assignment)
- visibility (public, private, pos)
- settings (fulfillment, email config)
- publish state

This replaces the embedded org.store_settings with a scalable,
multi-store architecture.
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from .common import generate_id, utc_now


class StoreVisibility:
    PUBLIC = "public"       # Accessible via public slug
    PRIVATE = "private"     # Accessible only via direct link (future: auth-gated)
    POS = "pos"             # Merchant-only interface for in-person sales


# ── Validation constants & shared helper ────────────────────────────────────
#
# Source-of-truth sets for the string-list fields exposed on the public
# Update contracts (StoreUpdate, StoreSettingsUpdate). Lives in the model
# module so both routers can import without a router→router dependency.
#
# `SUPPORTED_STOREFRONT_LANGUAGES` mirrors:
#   · routers/stores.SUPPORTED_LOCALES (used by _resolve_default_storefront_locale)
#   · frontend/src/hooks/useStorefrontLocale.js APP_SUPPORTED
#   · the i18n bundles actually shipped in frontend/src/i18n.js
# A drift between any of these silently makes the storefront 500 or
# fall back to "it" — Phase 1's test_store_default_language.py pins the
# routers/stores.py constant, and this constant pins it again here.
# Future consolidation: hoist to a single shared constants module.
SUPPORTED_STOREFRONT_LANGUAGES = frozenset({"it", "en", "de", "fr"})

# Mirrors the legacy router-level check in routers/stores.update_store
# (lines ~386-390) and the public catalog reader in routers/public.py.
SUPPORTED_FULFILLMENT_MODES = frozenset({"shipping", "local_pickup"})


# ── Phase 9 — Design tokens ────────────────────────────────────────────────
#
# Lightweight visual-design knobs the merchant can tweak from the
# admin UI. Stored as a JSON blob (Mongo native, no schema migration
# needed when we add more tokens in future) on the Store doc.
#
# Naming convention follows the de-facto design-token spec (Figma
# tokens / W3C Design Tokens Format):
#   accent_color    : single hex color (button bg, link color, focus ring)
#   font_family     : enum of curated font choices
#   border_radius   : enum 'sharp' | 'standard' | 'soft' | 'pill'
#   density         : enum 'compact' | 'standard' | 'spacious'
#   header_style    : enum 'solid' | 'translucent' | 'minimal'
#   card_style      : enum 'shadow' | 'flat' | 'outlined'
#
# Backward-compat: all keys are OPTIONAL. The frontend
# useDesignTokens hook fills the gaps with defaults, so an existing
# store without `design_tokens` set renders exactly as it does today.
#
# Future-proof: stored as `Dict[str, Any]` rather than a typed
# Pydantic sub-model so adding a new token in Phase 13+ doesn't
# require a Mongo migration of every document. Validation enforces
# the known keys via SUPPORTED_DESIGN_TOKEN_VALUES dict.

SUPPORTED_DESIGN_TOKEN_VALUES: Dict[str, frozenset] = {
    "font_family":   frozenset({"manrope", "inter", "serif", "system"}),
    "border_radius": frozenset({"sharp", "standard", "soft", "pill"}),
    "density":       frozenset({"compact", "standard", "spacious"}),
    "header_style":  frozenset({"solid", "translucent", "minimal"}),
    "card_style":    frozenset({"shadow", "flat", "outlined"}),
    # ── Logo display tokens (logo flexibility refinement) ──────────────
    #
    # Three preset heights instead of a slider, per merchant decision:
    # bounds the visual chaos at the cost of granularity. The CSS
    # custom property `--sf-logo-height` is set by useDesignTokens
    # so the header inline-style picks it up.
    #
    #   sm  →  32px   (compact header, dense layouts)
    #   md  →  40px   (default — matches pre-refinement)
    #   lg  →  56px   (prominent / brand-forward header)
    "logo_height":   frozenset({"sm", "md", "lg"}),
    # How to fit the uploaded logo image inside the height box:
    #   contain  →  respect aspect ratio, scale to fit (NEW default —
    #               works for wide / vertical / square logos alike)
    #   cover    →  fill the box, crop overflow (legacy behaviour —
    #               opt-in for merchants who want a square-cropped
    #               logo to match the old look)
    "logo_fit":      frozenset({"contain", "cover"}),
}

# Tokens that accept any string value (mostly hex colors) or
# boolean. Validation only checks the type, not an enum membership.
# `show_store_name` is a boolean that controls whether the store
# display name renders next to the logo in the header — merchants
# with a self-branded logo (word-mark + symbol) can hide it.
_FREEFORM_DESIGN_TOKENS: frozenset = frozenset({"accent_color"})
_BOOL_DESIGN_TOKENS: frozenset = frozenset({"show_store_name"})

# All known token keys. Unknown keys land in the doc but log a warning
# server-side — keeps forward-compat (future frontend may write a key
# the current backend doesn't yet validate, but we don't reject it).
_ALL_DESIGN_TOKEN_KEYS = (
    set(SUPPORTED_DESIGN_TOKEN_VALUES.keys())
    | _FREEFORM_DESIGN_TOKENS
    | _BOOL_DESIGN_TOKENS
)


def _validate_hex_color(value: Any, field_name: str) -> str:
    """Lenient hex-color validator. Accepts #RGB, #RRGGBB, #RRGGBBAA.
    Returns the normalized (uppercase) hex string."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} deve essere una stringa esadecimale (es. #FF5500).")
    v = value.strip()
    if not v.startswith("#"):
        raise ValueError(f"{field_name} deve iniziare con '#'.")
    body = v[1:]
    if len(body) not in (3, 6, 8):
        raise ValueError(
            f"{field_name} deve avere 3, 6 o 8 cifre esadecimali dopo '#'."
        )
    try:
        int(body, 16)
    except ValueError:
        raise ValueError(f"{field_name} contiene caratteri non esadecimali.")
    return "#" + body.upper()


def validate_design_tokens(tokens: Any) -> Dict[str, Any]:
    """Validate the design_tokens payload. Pure function — callers
    wrap a ValueError in HTTPException(400, ...) for the API contract.

    Rules:
      - None / missing → returns {} (admin clearing all custom tokens)
      - Must be a dict
      - Unknown keys are KEPT (forward-compat) but flagged in logs
      - Known enum keys must have a value in their allowed set
      - accent_color must be a valid hex string
      - Empty-string values for enum keys are treated as "unset" and dropped

    Returns the cleaned dict (ready for Mongo $set).
    """
    if tokens is None:
        return {}
    if not isinstance(tokens, dict):
        raise ValueError("design_tokens deve essere un oggetto.")

    cleaned: Dict[str, Any] = {}
    for key, value in tokens.items():
        # Treat "" / None as "unset" — admin can clear a token by
        # sending an empty value without having to omit the key.
        # IMPORTANT: explicit `False` for a bool token is NOT empty.
        if value is None or value == "":
            continue

        if key in SUPPORTED_DESIGN_TOKEN_VALUES:
            allowed = SUPPORTED_DESIGN_TOKEN_VALUES[key]
            if value not in allowed:
                raise ValueError(
                    f"design_tokens.{key}: valore '{value}' non supportato. "
                    f"Valori ammessi: {sorted(allowed)}."
                )
            cleaned[key] = value
        elif key in _BOOL_DESIGN_TOKENS:
            # Strict bool coercion: accept True/False, "true"/"false"
            # strings (admin UIs serialize booleans inconsistently).
            # Reject other types so a typo doesn't silently land in
            # the doc as a string.
            if isinstance(value, bool):
                cleaned[key] = value
            elif isinstance(value, str) and value.lower() in ("true", "false"):
                cleaned[key] = value.lower() == "true"
            else:
                raise ValueError(
                    f"design_tokens.{key}: valore deve essere boolean (true/false)."
                )
        elif key in _FREEFORM_DESIGN_TOKENS:
            # Currently only accent_color — validated as hex.
            if key == "accent_color":
                cleaned[key] = _validate_hex_color(value, f"design_tokens.{key}")
            else:
                cleaned[key] = value
        else:
            # Unknown key — keep verbatim for forward-compat with a
            # future frontend that writes a token this backend version
            # doesn't yet understand. Reject only if value is wildly
            # malformed (non-JSON-serializable).
            if not isinstance(value, (str, int, float, bool)):
                raise ValueError(
                    f"design_tokens.{key}: tipo di valore non supportato."
                )
            cleaned[key] = value

    return cleaned


# ── Phase 8 — Custom navigation links ──────────────────────────────────────
#
# Storefront merchants can add up to MAX_CUSTOM_NAV_LINKS custom links to
# the public storefront nav strip (next to the auto-generated category
# pills). Use cases:
#   - link to the merchant's own marketing site
#   - "About us" / "Contact" pages hosted elsewhere
#   - press/blog pages, social profiles, support portal
#
# The link label is multi-locale to support stores with
# storefront_languages spanning multiple languages. Validation rule:
# the label must have an entry for EACH language the store currently
# supports. Storing a label-per-language even for single-locale stores
# (when storefront_languages=["it"]) keeps the data shape future-proof
# — a merchant who later adds DE just needs to backfill, not migrate.

# Hard cap on the number of custom links a merchant can configure.
# Picked to balance "useful customization" with "preventing a
# cluttered header on small screens". Confirmed by user (Phase 8
# decision 3): MAX = 3.
MAX_CUSTOM_NAV_LINKS = 3

# Allowed values for the link's `target` attribute. Mirrors the HTML
# attribute semantics:
#   "self"  → opens in the same tab (default — usually internal links)
#   "blank" → opens in a new tab (usually external links; the frontend
#             adds rel="noopener noreferrer" automatically)
SUPPORTED_NAV_LINK_TARGETS = frozenset({"self", "blank"})


class CustomNavLink(BaseModel):
    """A single custom navigation link rendered in the storefront header.

    Field semantics:
      id            stable UUID assigned at create time so reorder /
                    delete operations from the admin UI can address
                    each link without relying on list position.
      label_i18n    map locale_code → label text. The router validator
                    enforces presence for every active storefront
                    language (see _validate_custom_nav_links below).
      url           internal (`/about`) OR external (`https://...`,
                    `mailto:`, `tel:`) URL. The frontend strips
                    `javascript:` and other unsafe schemes defensively.
      target        "self" or "blank" (see SUPPORTED_NAV_LINK_TARGETS).
      sort_order    integer for stable ordering when multiple links
                    are configured. Lower numbers render first.

    Phase 8.1 — stored as an embedded array inside Store. No new
    collection. Keeps the read path O(1) (no join) at the cost of a
    moderate write amplification when the admin reorders — acceptable
    because reorders are rare and the array is bounded to 3 elements.
    """
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    label_i18n: Dict[str, str] = Field(default_factory=dict)
    url: str = Field(min_length=1, max_length=2000)
    target: str = "self"
    sort_order: int = 0


# ── Track S Step 3.3 — allowed_origins validation ──────────────────────────
# Hardening del field `Store.allowed_origins` (List[str]). Senza
# validation:
#   - "null" → CORS bypass quando client manda `Origin: null` (es.
#     sandbox iframe, file://) e merchant per errore aggiunge "null" alla lista
#   - "*"   → wildcard catch-all (dynamic CORS exact match lo respinge,
#     ma e' un'ambiguita' da catturare alla fonte)
#   - "javascript:..." / "data:..." → schema non-HTTP, non sensato come origin
#   - Empty / whitespace → noise
#   - Lista esplosa (1000+ entries) → cache LRU overflow nel middleware
#
# Validator chiamato sia su creation che assignment (validate_assignment=True
# nel model_config Store) per catturare drift via DB direct update.

_MAX_ALLOWED_ORIGINS = 10
_MAX_ORIGIN_LENGTH = 200
_FORBIDDEN_ORIGIN_VALUES = {"null", "*", ""}


def _validate_allowed_origins(values: List[str]) -> List[str]:
    """Validate `Store.allowed_origins` list. Used by field_validator.

    Rules:
      - Max 10 entries (cache LRU bounded, sanity cap for merchant config)
      - Each entry max 200 char (URLs above this are noise)
      - Each entry must start with "http://" or "https://"
      - Each entry must NOT be "null", "*", or empty/whitespace
      - Strip whitespace before validation (forgiving on input)
      - Duplicates removed (preserve order of first occurrence)
    """
    if not isinstance(values, list):
        raise ValueError("allowed_origins deve essere una lista di stringhe.")
    if len(values) > _MAX_ALLOWED_ORIGINS:
        raise ValueError(
            f"allowed_origins eccede il massimo di {_MAX_ALLOWED_ORIGINS} "
            f"entries (trovato {len(values)})."
        )
    cleaned: List[str] = []
    seen: set = set()
    for raw in values:
        if not isinstance(raw, str):
            raise ValueError(
                f"allowed_origins entries devono essere stringhe (trovato {type(raw).__name__})."
            )
        origin = raw.strip()
        # Reject forbidden values explicitly (case-insensitive for "null")
        if origin.lower() in _FORBIDDEN_ORIGIN_VALUES:
            raise ValueError(
                f"allowed_origins valore non permesso: {raw!r}. "
                f"'null' e '*' bypassano la CORS protection per-store."
            )
        if not origin:
            raise ValueError("allowed_origins entry vuota o solo whitespace.")
        if len(origin) > _MAX_ORIGIN_LENGTH:
            raise ValueError(
                f"allowed_origins entry troppo lunga ({len(origin)} char, "
                f"max {_MAX_ORIGIN_LENGTH}): {origin[:50]!r}..."
            )
        # Schema check — only http(s) origins. file://, ftp://, javascript:
        # etc. non hanno senso come Origin header value.
        if not (origin.startswith("http://") or origin.startswith("https://")):
            raise ValueError(
                f"allowed_origins entry deve iniziare con http:// o https:// "
                f"(trovato: {origin!r})."
            )
        if origin not in seen:
            seen.add(origin)
            cleaned.append(origin)
    return cleaned


def _validate_url(url: str) -> str:
    """Reject obviously unsafe URL schemes. Used by the router validator.

    Allowed prefixes:
      "/"               internal (any path on the storefront)
      "http://"         external (defensive — most merchants will use https)
      "https://"        external (recommended)
      "mailto:"         email link
      "tel:"            phone link

    Explicitly rejected:
      "javascript:"     XSS vector
      "data:"           inline script injection vector
      "vbscript:"       legacy XSS

    Returns the URL unchanged on success. Pure function; safe to call
    from any thread / event loop.
    """
    if not isinstance(url, str):
        raise ValueError("L'URL deve essere una stringa.")
    stripped = url.strip()
    if not stripped:
        raise ValueError("L'URL non può essere vuoto.")
    # Lowercase prefix scan for the unsafe schemes.
    lower = stripped.lower()
    for blocked in ("javascript:", "data:", "vbscript:"):
        if lower.startswith(blocked):
            raise ValueError(
                f"L'URL non può iniziare con '{blocked}'. "
                "Usa http(s)://, mailto:, tel:, o un percorso interno (/about)."
            )
    # At least one of the safe prefixes must match.
    safe_prefixes = ("/", "http://", "https://", "mailto:", "tel:")
    if not any(lower.startswith(p) for p in safe_prefixes):
        raise ValueError(
            "L'URL deve iniziare con http(s)://, mailto:, tel:, "
            "o '/' per un percorso interno."
        )
    return stripped


def validate_custom_nav_links(
    links: Any,
    *,
    store_languages: List[str],
) -> List[Dict[str, Any]]:
    """Validate the custom_nav_links payload against the store's
    current `storefront_languages`. Pure function — callers wrap a
    ValueError in HTTPException(400, ...) for the API contract.

    Rules:
      - None / missing      → returns []  (admin clearing the menu)
      - Must be a list
      - Length ≤ MAX_CUSTOM_NAV_LINKS
      - Each entry:
          · valid Pydantic shape (CustomNavLink-compatible)
          · `url` passes _validate_url
          · `target` ∈ SUPPORTED_NAV_LINK_TARGETS
          · `label_i18n` has a non-empty string for EVERY locale in
            store_languages (decision 5: only the languages the store
            has activated are required; others are optional). The
            label for a non-activated language is silently dropped so
            stale entries don't pollute the response.
          · `sort_order` is an int (clipped to a reasonable range)

    Returns the cleaned list (dicts ready for Mongo $set), already
    sorted by sort_order ASC.
    """
    if links is None:
        return []
    if not isinstance(links, list):
        raise ValueError("custom_nav_links deve essere una lista.")
    if len(links) > MAX_CUSTOM_NAV_LINKS:
        raise ValueError(
            f"Puoi configurare al massimo {MAX_CUSTOM_NAV_LINKS} link personalizzati."
        )

    # Normalize the active languages once. Defensive: if the caller
    # passes an empty list (impossible after Phase 2 validation but
    # defense-in-depth) we accept any label set so the API doesn't
    # 500 — the merchant just gets a useless menu until they fix
    # storefront_languages.
    required_locales = set(store_languages or [])

    cleaned: List[Dict[str, Any]] = []
    for i, entry in enumerate(links):
        if not isinstance(entry, dict):
            raise ValueError(
                f"custom_nav_links[{i}] deve essere un oggetto."
            )

        # URL — required, validated for safe schemes
        url_raw = entry.get("url")
        if not url_raw:
            raise ValueError(f"custom_nav_links[{i}]: campo url mancante.")
        try:
            url_clean = _validate_url(url_raw)
        except ValueError as e:
            raise ValueError(f"custom_nav_links[{i}]: {e}")

        # target — must be in the supported set
        target = entry.get("target", "self")
        if target not in SUPPORTED_NAV_LINK_TARGETS:
            raise ValueError(
                f"custom_nav_links[{i}]: target '{target}' non supportato. "
                f"Valori ammessi: {sorted(SUPPORTED_NAV_LINK_TARGETS)}."
            )

        # label_i18n — must have a non-empty entry for every active locale
        labels_raw = entry.get("label_i18n") or {}
        if not isinstance(labels_raw, dict):
            raise ValueError(
                f"custom_nav_links[{i}]: label_i18n deve essere un oggetto "
                "con chiave per ogni lingua attiva dello store."
            )
        # Filter to active locales only; reject if any required locale
        # is missing/blank.
        cleaned_labels: Dict[str, str] = {}
        for locale in required_locales:
            value = labels_raw.get(locale)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"custom_nav_links[{i}]: manca l'etichetta per la lingua '{locale}'. "
                    "Ogni lingua attiva dello store richiede un'etichetta."
                )
            cleaned_labels[locale] = value.strip()[:80]  # cap length

        # sort_order — clamp to a reasonable range
        sort_order = entry.get("sort_order", i)
        if not isinstance(sort_order, int):
            try:
                sort_order = int(sort_order)
            except (TypeError, ValueError):
                sort_order = i
        sort_order = max(0, min(999, sort_order))

        # id — preserve if present, else generate a fresh one. The
        # router's PATCH endpoint may receive a partial update without
        # an id (admin "Add link" → POST with no id yet) and we
        # generate at validation time so Mongo gets a complete doc.
        link_id = entry.get("id") or generate_id()

        cleaned.append({
            "id": link_id,
            "label_i18n": cleaned_labels,
            "url": url_clean,
            "target": target,
            "sort_order": sort_order,
        })

    # Sort by sort_order ASC so the storage order matches render order
    # — no client-side sorting needed.
    cleaned.sort(key=lambda x: x["sort_order"])
    return cleaned


def validate_string_list_field(
    value,
    *,
    field_name: str,
    allowed: frozenset,
):
    """Validate a string-list payload field for the Store contracts.

    Used by both `PATCH /stores/{id}` and `PATCH /store-settings` to
    enforce the same rules across the two parallel update surfaces.
    Pure function — no I/O, no Pydantic dependency — so call sites can
    raise their own HTTPException with the localized 400 contract the
    UI already handles.

    Rules:
      - `None` is rejected (caller should skip the check entirely when
        the field is absent from the PATCH body; this helper is invoked
        only after presence is established).
      - The value must be a `list`.
      - The list must contain at least one element.
      - Every element must be a `str` belonging to `allowed`.
      - Duplicates are rejected (a future PATCH that grows the array
        via append would hide intent if dups were silently coerced).

    Raises:
      ValueError with a stable, machine-readable message. Callers wrap
      this in HTTPException(400, str(err)) to preserve the historical
      contract. The message intentionally includes the field name and
      the allowed set so the frontend can surface specific copy without
      string-matching the prose.
    """
    if value is None:
        raise ValueError(f"{field_name} is required")
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if len(value) == 0:
        raise ValueError(
            f"{field_name} deve contenere almeno un valore valido."
        )
    seen = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError(
                f"{field_name} contiene un elemento non valido (atteso stringa)."
            )
        if item not in allowed:
            raise ValueError(
                f"{field_name} contiene un valore non supportato: '{item}'. "
                f"Valori ammessi: {sorted(allowed)}."
            )
        if item in seen:
            raise ValueError(
                f"{field_name} contiene un valore duplicato: '{item}'."
            )
        seen.add(item)
    return value


class Store(BaseModel):
    """Full store document as stored in MongoDB."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    slug: Optional[str] = None                     # Public URL slug (unique per org)
    name: str = Field(min_length=1, max_length=255) # Display name
    description: Optional[str] = None              # Public description (max 500)
    visibility: str = "public"                     # public | private | pos

    # Identity & contacts
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    # Email config (platform_managed)
    sender_display_name: Optional[str] = None
    reply_to_email: Optional[str] = None
    notification_email: Optional[str] = None
    email_delivery: str = "platform"

    # Branding (v13.0 — per-store, replaces org-level)
    logo_url: Optional[str] = None
    brand_color: Optional[str] = None              # hex: #FF5500
    brand_color_text: Optional[str] = None         # hex: #FFFFFF
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None

    # Fulfillment
    fulfillment_modes: List[str] = Field(default_factory=lambda: ["shipping"])

    # Storefront languages — which languages are available in the public catalog.
    #
    # Source of truth: the merchant's choice in the admin "Lingue" picker
    # (Store settings → Lingue). The first element drives the storefront's
    # default landing language for guest visitors (see
    # frontend/src/hooks/useStorefrontLocale.js → 'storeDefault' branch).
    #
    # The `["it"]` factory is a DEFENSIVE fallback only — it triggers when
    # a Store object is instantiated without explicit value (tests,
    # scripts, fixtures). The real-world create paths
    # (`POST /stores`, `_ensure_default_store` legacy migration) override
    # this default by reading the creator's `user.locale` via
    # `routers/stores._resolve_default_storefront_locale(user)`, so a
    # German-speaking merchant lands on `["de"]` out of the box. The
    # admin can change the value any time via the Lingue picker.
    storefront_languages: List[str] = Field(default_factory=lambda: ["it"])

    # Publish control
    is_published: bool = False

    # Status tracking (derived values cached for transition detection)
    last_known_store_status: Optional[str] = None
    last_status_transition_at: Optional[str] = None

    # Flags
    is_default: bool = False                       # The original/primary store
    is_active: bool = True

    # Phase 0 Step 7 (2026-05-28) — Dynamic CORS allowlist per store.
    #
    # Origins esterni autorizzati a fare richieste cross-origin verso gli
    # endpoint ``/api/public/embed/*`` (Stream A embed widget) e
    # ``/api/public/ai-site/*`` (Stream B AI-generated sites su custom
    # domain). Match esatto sull'``Origin`` header — wildcard NON
    # supportati per ridurre rischio di mis-allowlist.
    #
    # Esempio:
    #   ["https://merchantbrand.com",
    #    "https://shop.merchantbrand.com",
    #    "https://staging.merchantbrand.com"]
    #
    # Limit per piano (enforced via services.module_access):
    #   · Free / Solo: max 0 (embed non disponibile)
    #   · Commerce Core: max 1 origin
    #   · Commerce Pro: max 3 origin
    #   · Enterprise: illimitato
    #
    # Quando vuoto (default), nessuna richiesta cross-origin /embed/* è
    # accettata. Storefront classic afianco.app continua a funzionare
    # come same-origin (CORSMiddleware statico esistente).
    allowed_origins: List[str] = Field(default_factory=list)

    # Track S Step 3.3 — validator chained to Store.allowed_origins.
    # Pinned by tests/test_invariants_security.py::TestSEC_S3_3_AllowedOriginsValidation
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _check_allowed_origins(cls, v):
        if v is None:
            return []
        return _validate_allowed_origins(v)

    # v5.8 / Onda 9.K — Plan-violation deactivation tracking.
    # Set when a downgrade reduces stores_max below the org's current store count
    # and reconcile_stores_to_plan_limit() flagged this store as overflow.
    # Lifecycle:
    #   · Org on Pro (3 stores active) → downgrades to Solo (stores_max=0)
    #   · The reconcile picks the 3 most-recent stores and sets:
    #       is_active=False, deactivated_for_plan_violation=True,
    #       plan_violation_deactivated_at=<now>
    #   · Storefront `/co/<slug>/<store-slug>` returns 404 (filter is_active=True)
    #   · The store row is preserved in DB (no data loss)
    #   · When the org upgrades back, reconcile reactivates the
    #     longest-deactivated stores first, up to the new stores_max.
    deactivated_for_plan_violation: bool = False
    plan_violation_deactivated_at: Optional[str] = None

    # F4 Onda 11 — Terms & Conditions shown at checkout. When
    # `terms_enabled` is True and `terms_content` is non-empty, the
    # storefront renders an acceptance checkbox required to submit.
    # A product can override the content via metadata.terms_content.
    #
    # Note (Wave GDPR-Commerce CG-1): this legacy field is the simple
    # "checkout T&C blurb" — short text shown inline. The new full
    # GDPR-Commerce stack (merchant_terms_content_<locale> below) is
    # the legally-binding Terms of Service per-locale rendered on
    # /s/<slug>/terms. The two coexist: legacy field for the inline
    # short blurb, new fields for the proper multi-page T&C.
    terms_enabled: bool = False
    terms_content: Optional[str] = Field(default=None, max_length=20000)

    # ── Wave GDPR-Commerce Phase CG-1 (2026-05-18) ─────────────────────────
    #
    # Per-store legally-binding Privacy Policy + Terms of Service. The
    # merchant is the Data Controller toward their end customers; afianco
    # is the Data Processor. The merchant therefore needs their OWN docs
    # disclosed on the storefront — not afianco's platform-level ones.
    #
    # Editing model:
    #   - Merchant can edit content in ALL FOUR locales (it/en/de/fr).
    #     Each locale is independent — no auto-translation by design.
    #   - Merchant chooses ONE ``merchant_legal_display_locale`` that is
    #     the SOLE version shown to ALL customers on the storefront,
    #     regardless of the customer's UI language. That choice is the
    #     legally-binding reference language for this store.
    #   - Version (tag + hash) is computed from the display_locale's
    #     content only — so editing other locales does NOT trigger
    #     re-consent of registered customers. Changing the display_locale
    #     itself, or editing the display_locale content, DOES bump the
    #     version → triggers re-consent (mirrors afianco Phase E).
    #
    # All fields are Optional → legacy stores deserialize cleanly without
    # migration. Status enum is computed by
    # services/merchant_legal_versioning.merchant_legal_status().
    #
    # Length cap 30K per markdown (≈ 6 pages typeset) — generous for
    # standard merchant privacy + terms; the standard afianco template
    # used as draft is ~10K.

    # The four locale drafts — admin edits each independently.
    merchant_privacy_content_it: Optional[str] = Field(default=None, max_length=30000)
    merchant_privacy_content_en: Optional[str] = Field(default=None, max_length=30000)
    merchant_privacy_content_de: Optional[str] = Field(default=None, max_length=30000)
    merchant_privacy_content_fr: Optional[str] = Field(default=None, max_length=30000)

    merchant_terms_content_it: Optional[str] = Field(default=None, max_length=30000)
    merchant_terms_content_en: Optional[str] = Field(default=None, max_length=30000)
    merchant_terms_content_de: Optional[str] = Field(default=None, max_length=30000)
    merchant_terms_content_fr: Optional[str] = Field(default=None, max_length=30000)

    # The locale customers will actually see on the storefront.
    # None → not yet configured → status="not_configured".
    # Must be one of {"it","en","de","fr"} when set.
    merchant_legal_display_locale: Optional[str] = None

    # Versioning — analogous to afianco's CURRENT_VERSION_TAG/HASH but
    # per-store, computed from the display_locale content bundle only.
    #
    # Format mirror afianco: "v1.0", "v1.1", … (semver-ish, no patch).
    # Hash: SHA256-hex16 of (privacy_<display> + "\n\n--- TERMS ---\n\n" + terms_<display>).
    #
    # Bumped by:
    #   · POST /api/stores/{id}/legal/publish — first publish: "v1.0";
    #     subsequent publishes increment minor if hash changed (idempotent
    #     if no content drift).
    #   · PATCH /api/stores/{id}/legal/display-locale — when changing the
    #     locale shown to customers, hash naturally changes; version bumps.
    merchant_legal_version_tag: Optional[str] = None
    merchant_legal_version_hash: Optional[str] = None

    # Publish lifecycle timestamps.
    #   published_at  — None if never published (status ∈ {not_configured, draft}).
    #   last_edited_at — touched by every PATCH on a content field.
    # If last_edited_at > published_at → status="stale_draft" (UI nudges).
    merchant_legal_published_at: Optional[str] = None
    merchant_legal_last_edited_at: Optional[str] = None

    # Wave GDPR-Commerce CG-3-Polish (2026-05-18) — wizard variables.
    #
    # The 7-field wizard form (merchant_name, merchant_email,
    # merchant_country, store_country, collects_phone,
    # collects_shipping_address, uses_marketing, ships_to_eu) is
    # the input to the template-render service. Previously these
    # values lived only in the wizard form state — once the wizard
    # closed, they were "baked" into the generated markdown and the
    # admin had to dig into the 8 doc files to update e.g. the
    # contact email.
    #
    # Now they're persisted on the Store doc so:
    #   · the wizard pre-populates on subsequent opens
    #   · the editor can show a "Dati del titolare" panel for review
    #   · the merchant can update them and re-render all 8 drafts
    #     from the template in one click
    #
    # Stored as a plain dict (not a Pydantic sub-model) so future
    # additions don't require a schema migration; the server-side
    # ``TemplateVars`` model still validates on read/write. Default
    # None → legacy stores deserialize unchanged.
    #
    # NOT a source of legal truth — pure UI convenience metadata.
    # Edits to this field do NOT bump the version (it's not content,
    # it's identity inputs).
    merchant_legal_template_vars: Optional[Dict[str, Any]] = None

    # Phase 8 — custom navigation links rendered in the storefront
    # header strip (next to the auto-generated category pills).
    # Bounded list (max MAX_CUSTOM_NAV_LINKS items). Each item carries
    # a per-locale label, so multi-language stores can show the right
    # text for the visitor's resolved locale. See CustomNavLink above.
    #
    # Stored as embedded array (not a join collection) because:
    #   · the list is bounded (3 items max)
    #   · always read together with the rest of the store doc
    #     (catalog endpoint returns it inside the meta response)
    #   · per-link writes are rare (admin reorder / add / delete)
    #
    # Default empty list, NOT None: lets the catalog endpoint always
    # return an array (no None-vs-empty branching client-side).
    custom_nav_links: List[CustomNavLink] = Field(default_factory=list)

    # Phase 9 — design tokens. Lightweight visual customization
    # (radius, density, font, header_style, card_style, accent_color).
    # See validate_design_tokens above. Stored as plain dict so future
    # tokens land without schema migration. Default empty dict; the
    # frontend useDesignTokens hook applies sensible defaults.
    design_tokens: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ── API Contracts ──────────────────────────────────────────────────────────

class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, min_length=3, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    visibility: str = "public"


class StoreUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = Field(default=None, max_length=255)
    slug: Optional[str] = Field(default=None, min_length=3, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    visibility: Optional[str] = None
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    sender_display_name: Optional[str] = Field(default=None, max_length=100)
    reply_to_email: Optional[str] = Field(default=None, max_length=255)
    notification_email: Optional[str] = Field(default=None, max_length=255)
    # Branding (v13.0)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    brand_color: Optional[str] = Field(default=None, max_length=7)
    brand_color_text: Optional[str] = Field(default=None, max_length=7)
    seo_title: Optional[str] = Field(default=None, max_length=100)
    seo_description: Optional[str] = Field(default=None, max_length=300)
    fulfillment_modes: Optional[List[str]] = None
    storefront_languages: Optional[List[str]] = None
    is_published: Optional[bool] = None
    # F4 Onda 11 — Terms & Conditions
    terms_enabled: Optional[bool] = None
    terms_content: Optional[str] = Field(default=None, max_length=20000)
    # Phase 8 — Custom navigation links. Validated against the store's
    # current storefront_languages in the router (so the label_i18n
    # contract spans multiple fields and can't sit on a single-field
    # Pydantic validator). The router wraps validate_custom_nav_links
    # in HTTPException(400, ...).
    custom_nav_links: Optional[List[Dict[str, Any]]] = None
    # Phase 9 — Design tokens dict. Validated by validate_design_tokens
    # in the router. Submitting an empty dict or omitting the field
    # leaves the existing tokens untouched (admin only updates what
    # they touch).
    design_tokens: Optional[Dict[str, Any]] = None


class StoreResponse(BaseModel):
    id: str
    organization_id: str
    slug: Optional[str] = None
    name: str
    description: Optional[str] = None
    visibility: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    sender_display_name: Optional[str] = None
    reply_to_email: Optional[str] = None
    notification_email: Optional[str] = None
    logo_url: Optional[str] = None
    brand_color: Optional[str] = None
    brand_color_text: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    fulfillment_modes: List[str]
    storefront_languages: List[str] = Field(default_factory=lambda: ["it"])
    is_published: bool
    is_default: bool
    is_active: bool
    # Phase 8 — surfaced on the response so admin UI (StoresPage) can
    # render the configured nav links without a separate fetch. Always
    # an array (never null) so the React component can `.map()` directly.
    custom_nav_links: List[CustomNavLink] = Field(default_factory=list)
    # Phase 9 — design tokens. Empty dict when admin hasn't customized
    # anything; the frontend hook fills defaults at render time.
    design_tokens: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
