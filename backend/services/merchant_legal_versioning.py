"""Merchant legal versioning service — Wave GDPR-Commerce Phase CG-1.

Per-store Privacy + Terms versioning, analogous to afianco's
``core.legal_versions`` but scoped to a single ``Store`` document.

Rationale
=========
Each merchant publishes their OWN Privacy Policy + Terms on their
storefront (they are Data Controller toward end customers; afianco is
Data Processor). The merchant edits content in up to 4 locales but
chooses ONE ``merchant_legal_display_locale`` that is the SOLE version
shown to ALL customers, regardless of customer UI language. That choice
is the legally-binding reference language for this store.

Versioning model
================
- ``version_hash``: SHA256-hex16 of the BUNDLE
    privacy_<display>  +  "\\n\\n--- TERMS BUNDLE ---\\n\\n"  +  terms_<display>
  Computed ONLY from the display_locale content — editing other
  locales does NOT bump the hash and does NOT trigger customer
  re-consent (those are archived translations the merchant may switch
  to later).
- ``version_tag``: human-readable "v1.0", "v1.1", … bumped MINORS at
  every publish where the content hash actually changed. First publish
  is always ``v1.0``. No-op publish (hash identical to currently
  published) is idempotent — no version bump, no audit churn.
- Changing ``merchant_legal_display_locale`` is treated as a content
  change (the bundle considered for hashing flips locale → hash flips)
  and bumps the version accordingly.

Status state machine
====================
::

    not_configured ──[generate-draft+save]──> draft
    draft          ──[publish]──────────────> published
    published      ──[edit + save]──────────> stale_draft
    stale_draft    ──[publish]──────────────> published
                   ──[discard-draft]────────> published   (future)

The state is COMPUTED from the Store document on every read — there is
no persistent ``status`` field to keep in sync.

Public API
==========
``compute_legal_hash(store, doc_type=None)`` — hex16 hash
``current_version_string(store)`` — ``"v1.0:48ea..."`` or None
``merchant_legal_status(store)`` — Literal status
``bump_version_tag(current_tag)`` — semver-ish increment
``hash_inputs(store)`` — (privacy_content, terms_content) tuple for the
                        display_locale (utility for tests + admin UI)

All functions accept either a Pydantic Store model OR a raw dict
(MongoDB document) — the latter is what most callers will pass after
``store_repository.find_by_id`` reads.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal, Optional, Tuple


SUPPORTED_LOCALES = ("it", "en", "de", "fr")

LegalStatus = Literal["not_configured", "draft", "published", "stale_draft"]


# ─── Internal helpers ────────────────────────────────────────────────────


def _get(store: Any, field: str) -> Any:
    """Read a field from a Store model or a raw dict."""
    if isinstance(store, dict):
        return store.get(field)
    return getattr(store, field, None)


def _content_for(store: Any, doc_type: str, locale: str) -> Optional[str]:
    """Return the markdown content for the given doc + locale slot.

    doc_type ∈ {"privacy", "terms"}
    locale ∈ {"it","en","de","fr"}
    Returns None if the field is absent or empty (whitespace-only).
    """
    field = f"merchant_{doc_type}_content_{locale}"
    raw = _get(store, field)
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def _display_locale(store: Any) -> Optional[str]:
    """Legacy CG-1 reader — kept for backward compat in places that
    explicitly want to know whether the deprecated explicit field was
    set. New code should call ``get_effective_display_locale`` instead.
    """
    raw = _get(store, "merchant_legal_display_locale")
    if not raw:
        return None
    loc = str(raw).strip().lower()
    return loc if loc in SUPPORTED_LOCALES else None


def get_effective_display_locale(store: Any) -> Optional[str]:
    """Return the locale ACTUALLY shown to customers.

    Wave CG-3-Polish (2026-05-18): the source of truth for which
    language customers see on the storefront is the store's
    ``storefront_languages[0]`` — the same field the admin already
    configures in store settings.

    CG-3-Polish-2 (2026-05-18 evening): a user reported confusion
    when the legacy ``merchant_legal_display_locale`` field was set
    from the original CG-3 wizard (which called the now-deprecated
    patchDisplayLocale endpoint) and silently overrode their
    ``storefront_languages[0]`` choice. We flipped the priority:
    ``storefront_languages[0]`` now wins. The legacy field is only
    consulted as a defensive fallback when ``storefront_languages``
    is missing or invalid — which should never happen in production
    (the Store model defaults it to ["it"]).

    Resolution order:
      1. ``storefront_languages[0]`` if valid → modern primary path.
      2. Legacy ``merchant_legal_display_locale`` if set AND valid →
         only when (1) fails. Pre-Polish stores with the legacy field
         set and no storefront_languages fall through to this.
      3. ``"it"`` as ultimate fallback (mirrors the i18n stack default).

    The returned value is guaranteed to be in SUPPORTED_LOCALES when
    not None.
    """
    # CG-3-Polish-2: storefront_languages[0] is the ONLY source of
    # truth in modern stores. The legacy field is treated as data drift
    # that must be ignored unless storefront_languages is unusable.
    langs = _get(store, "storefront_languages")
    if isinstance(langs, list) and len(langs) > 0:
        first = str(langs[0]).strip().lower()
        if first in SUPPORTED_LOCALES:
            return first

    # Defensive: legacy field as last resort when storefront_languages
    # is genuinely missing. NOT triggered in normal operation.
    explicit = _display_locale(store)
    if explicit:
        return explicit

    # Ultimate fallback — mirrors the i18n stack default. Preserves
    # the contract that hash computation can ALWAYS succeed when both
    # privacy + terms content exist in at least one locale.
    return "it"


# ─── Public API ──────────────────────────────────────────────────────────


def hash_inputs(store: Any) -> Tuple[Optional[str], Optional[str]]:
    """Return (privacy_content, terms_content) for the effective
    display locale (= what the customer actually sees).

    Either element may be None when not yet populated. Callers use this
    for preview, diff, or test assertions — not for hashing directly
    (use ``compute_legal_hash`` for that).

    Wave CG-3-Polish: now reads the effective locale (derived from
    storefront_languages[0] with legacy field fallback) instead of the
    deprecated explicit ``merchant_legal_display_locale``. So if the
    admin changes the store's primary language, the hash naturally
    flips → correct re-consent trigger.
    """
    loc = get_effective_display_locale(store)
    if not loc:
        return (None, None)
    return (
        _content_for(store, "privacy", loc),
        _content_for(store, "terms", loc),
    )


def compute_legal_hash(store: Any) -> Optional[str]:
    """SHA256-hex16 of the display-locale bundle, or None if not ready.

    Returns None when either:
      - merchant_legal_display_locale is unset, or
      - either privacy or terms in the display locale is empty.

    The string format mirrors afianco's bundle hash exactly:
        privacy_<display>  +  "\\n\\n--- TERMS BUNDLE ---\\n\\n"  +  terms_<display>
    so manual cross-checks (and the test sentinel that recomputes the
    hash with a stdlib one-liner) stay trivial.
    """
    priv, terms = hash_inputs(store)
    if priv is None or terms is None:
        return None
    bundle = priv + "\n\n--- TERMS BUNDLE ---\n\n" + terms
    return hashlib.sha256(bundle.encode("utf-8")).hexdigest()[:16]


def current_version_string(store: Any) -> Optional[str]:
    """Return ``"v1.0:48ea..."`` for the currently-published version.

    Returns None when the store has never published (tag or hash is
    missing). When stamping consent_audit records at customer signup or
    checkout, the caller MUST treat None as "no published docs → block
    consent capture" because there is nothing to legally bind to.
    """
    tag = _get(store, "merchant_legal_version_tag")
    h = _get(store, "merchant_legal_version_hash")
    if not tag or not h:
        return None
    return f"{tag}:{h}"


def merchant_legal_status(store: Any) -> LegalStatus:
    """Compute the lifecycle status from the Store document.

    Pure function — no DB writes, safe to call on every request.
    See module docstring for the state machine diagram.

    Wave CG-3-Polish: now resolves the display locale via
    ``get_effective_display_locale`` instead of reading the legacy
    explicit field. This means a store with ``storefront_languages=["it"]``
    but no ``merchant_legal_display_locale`` set is now correctly
    treated as "display = IT" rather than "not_configured".
    """
    loc = get_effective_display_locale(store)
    priv = _content_for(store, "privacy", loc) if loc else None
    terms = _content_for(store, "terms", loc) if loc else None

    if not loc or priv is None or terms is None:
        # The effective display locale has at least one of
        # (privacy, terms) empty. Nothing publishable.
        return "not_configured"

    published_at = _get(store, "merchant_legal_published_at")
    if not published_at:
        # Content exists for display locale but never published.
        return "draft"

    # Published — check for unpublished edits (last_edited_at > published_at
    # OR the live hash differs from the stored hash).
    last_edited_at = _get(store, "merchant_legal_last_edited_at")
    if last_edited_at and published_at and last_edited_at > published_at:
        return "stale_draft"

    # Defensive secondary check: if hash drift slipped past last_edited_at
    # (e.g. raw DB patches), still surface as stale_draft so the admin
    # is nudged to re-publish.
    stored_hash = _get(store, "merchant_legal_version_hash")
    live_hash = compute_legal_hash(store)
    if stored_hash and live_hash and stored_hash != live_hash:
        return "stale_draft"

    return "published"


_TAG_RE = re.compile(r"^v(\d+)\.(\d+)$")


def bump_version_tag(current_tag: Optional[str]) -> str:
    """Increment the minor of a ``vMAJOR.MINOR`` tag.

    Examples:
        bump_version_tag(None)     -> "v1.0"
        bump_version_tag("")       -> "v1.0"
        bump_version_tag("v1.0")   -> "v1.1"
        bump_version_tag("v1.7")   -> "v1.8"
        bump_version_tag("v2.3")   -> "v2.4"

    On any malformed input we fall back to ``"v1.0"`` rather than raise:
    the caller is in a publish flow that must complete; a malformed tag
    is treated as "never published before, start clean". The malformed
    value would only ever appear from manual DB tampering, which is
    out-of-scope for runtime correctness.
    """
    if not current_tag:
        return "v1.0"
    m = _TAG_RE.match(current_tag.strip())
    if not m:
        return "v1.0"
    major, minor = int(m.group(1)), int(m.group(2))
    return f"v{major}.{minor + 1}"
