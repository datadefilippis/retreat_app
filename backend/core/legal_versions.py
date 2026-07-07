"""Legal documents version registry — Wave GDPR-Admin.

Single source of truth for the "current version" of the Privacy
Policy + Terms of Service. The signup flow reads this module to
stamp ``users.accepted_terms_version`` and the immutable
``consent_audit`` record at acceptance time.

How versions are bumped:
  - When the LEGAL CONTENT of Privacy Policy or T&C changes
    (real wording change, not just CSS or typos), bump
    ``CURRENT_VERSION_TAG`` to the new semver-ish label (e.g.
    "v1.0" → "v1.1") and recompute ``CURRENT_VERSION_HASH`` from
    the new text bundle.
  - Existing users with the OLD version in their
    ``accepted_terms_version`` are NOT automatically migrated —
    they will be prompted to re-accept at next login (handled
    elsewhere, future Phase). Their old consent record in
    ``consent_audit`` remains as proof of what they originally
    agreed to.

How version_hash is computed:
  hash_document_text(privacy_text + "\\n\\n--- TERMS BUNDLE ---\\n\\n" + terms_text)
  → SHA256 hex digest, truncated to 16 chars

Multilingual model:
  Italian is the legally binding reference language (clearly
  declared in the header of each document). EN/DE/FR are full
  translations of the IT bundle, served via the public
  ``/api/legal/{privacy,terms}?locale=<xx>`` endpoint. All four
  locales are considered production-ready in v1.0 — no draft
  markers anywhere in the user-facing UI.
"""

from typing import Final

# ── Current legal document version ─────────────────────────────────────────
#
# IMPORTANT: bump CURRENT_VERSION_TAG whenever the LEGAL CONTENT changes.
# The hash is recomputed manually from the IT bundle (see procedure below).

CURRENT_VERSION_TAG: Final[str] = "v2.0"
"""Human-readable tag of the documents the user is currently shown.

History:
  - v0.preD (Phase B, 2026-05-16 morning) — pre-finalization Italian
    text, bootstrap hash placeholder.
  - v0.9 (Wave GDPR-Admin D content, 2026-05-16 afternoon) — lawyer-
    grade rewrite of the IT bundle (Privacy: 20 sections; Terms: 24
    sections; full GDPR + LPD compliance, complete sub-processor
    table, end-customer Commerce coverage, indemnification, data
    breach notification procedure, severability, survival). EN/DE/FR
    files were Phase-C synthetic drafts pointing to the IT version.
  - v1.0 (production launch, 2026-05-18) — first public release.
    Removed all draft banners and "pre-V1.0" notices. EN/DE/FR are
    now complete translations of the IT v1.0 binding bundle (Privacy
    20 sections; Terms 24 sections per locale). Italian remains the
    legally binding reference language per the disclosure in each
    document header. Controller: Davide De Filippis, Lugano (CH).
  - v2.0 (AN4, 2026-07-07) — riscrittura integrale per il pivot
    Aurya marketplace: 4 ruoli (Titolare/Operatore/Cliente-Passaporto/
    Visitatore), Stripe Connect + application fee 5%/2% solo sul
    calendario pubblico, caparre e piani di pagamento, recensioni
    verificate OTP, AI ridimensionata alle traduzioni, sub-processor
    Nominatim, Aurya intermediario tecnico + DAC7. Zero AFianco.
    EN/DE/FR ritradotti dal bundle IT v2.0.
"""

CURRENT_VERSION_HASH: Final[str] = "cbbb9cdc2ec25b48"
"""SHA256-hex16 of the rendered IT privacy + terms text bundle.

Computed from the concatenation:
    privacy_it.md  +  "\\n\\n--- TERMS BUNDLE ---\\n\\n"  +  terms_it.md

Recompute by running:
    python -c "
    import hashlib
    from pathlib import Path
    priv = Path('backend/legal/privacy_it.md').read_text('utf-8')
    terms = Path('backend/legal/terms_it.md').read_text('utf-8')
    print(hashlib.sha256(
      (priv + '\\n\\n--- TERMS BUNDLE ---\\n\\n' + terms).encode()
    ).hexdigest()[:16])"

The 16-char truncation is safe for our scale (a few document
versions per year; collision probability negligible).
"""

# Backward-compat marker for legacy users (created BEFORE Phase B).
# Used by the backfill function in repositories/consent_audit_repository.py
# to populate ``accepted_terms_version`` on existing user docs.
LEGACY_VERSION_TAG: Final[str] = "v0.legacy"
LEGACY_VERSION_HASH: Final[str] = "unknown_bootstrap"


def current_version_string() -> str:
    """Return the canonical ``<tag>:<hash>`` representation.

    This is what gets stored in ``users.accepted_terms_version`` and
    is also passed to consent_audit records. Format kept short to
    minimise storage cost (32 chars max).
    """
    return f"{CURRENT_VERSION_TAG}:{CURRENT_VERSION_HASH}"


def legacy_version_string() -> str:
    """Return the canonical legacy version string for backfill."""
    return f"{LEGACY_VERSION_TAG}:{LEGACY_VERSION_HASH}"


# ── Wave GDPR-Admin Phase C — multilingual legal document loader ───────────
#
# The legal text bundles live as Markdown files in ``backend/legal/`` so
# they can be replaced (next version bump) without touching code.
#
#   backend/legal/privacy_<locale>.md
#   backend/legal/terms_<locale>.md
#
# where <locale> is one of: it, en, de, fr.
#
# get_legal_document() returns the raw Markdown text. The signup form
# and the public Privacy / Terms pages render it client-side.
#
# v1.0 status:
#   - Italian file: the legally binding reference version.
#   - English / German / French files: full translations of the IT
#     v1.0 bundle. No draft banner is rendered by the frontend; the
#     "Italian is the binding reference" disclosure is part of each
#     translated document's own header.

from pathlib import Path
from typing import Optional

_SUPPORTED_LOCALES = ("it", "en", "de", "fr")
_DEFAULT_LOCALE = "it"
_SUPPORTED_DOC_TYPES = ("privacy", "terms")

# Resolve from this module's location → backend/legal/
_LEGAL_DIR = Path(__file__).resolve().parent.parent / "legal"


def get_legal_document(doc_type: str, locale: Optional[str] = None) -> dict:
    """Load a legal document text bundle.

    Args:
        doc_type: "privacy" | "terms"
        locale:   "it" | "en" | "de" | "fr" — falls back to "it" if
                  None / unknown.

    Returns a dict with:
        content:        raw Markdown text
        locale_actual:  the locale actually served (may differ from
                        the requested one if we fell back)
        locale_requested: what the caller asked for (echoed back)
        doc_type:       passthrough
        is_draft:       always False in v1.0 — all four locales are
                        production-ready. Field retained for forward
                        compatibility (a future locale could ship as
                        a draft while others are stable).
        version_tag:    the CURRENT_VERSION_TAG from this module
        available_locales: list of locale codes for which a file
                          exists (for UI language switcher)

    Raises ValueError on invalid doc_type. Returns the Italian
    fallback (never raises) for invalid locales.
    """
    if doc_type not in _SUPPORTED_DOC_TYPES:
        raise ValueError(
            f"Invalid doc_type {doc_type!r}; allowed: {_SUPPORTED_DOC_TYPES}"
        )

    requested = (locale or _DEFAULT_LOCALE).lower()
    actual = requested if requested in _SUPPORTED_LOCALES else _DEFAULT_LOCALE

    file_path = _LEGAL_DIR / f"{doc_type}_{actual}.md"
    if not file_path.exists():
        # Should never happen if all 4 locales are present, but fail
        # safe to IT.
        actual = _DEFAULT_LOCALE
        file_path = _LEGAL_DIR / f"{doc_type}_{_DEFAULT_LOCALE}.md"

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        # If even the Italian fallback fails, return empty string —
        # the frontend handles the empty state gracefully.
        content = ""

    # v1.0: all locales are production-ready (full translations of the
    # IT binding bundle). The field is kept on the response for forward
    # compatibility — a future locale added before review completion
    # could be flagged here without breaking the frontend contract.
    is_draft = False

    # Inventory of available locales (existence of the file on disk).
    available = sorted([
        loc for loc in _SUPPORTED_LOCALES
        if (_LEGAL_DIR / f"{doc_type}_{loc}.md").exists()
    ])

    return {
        "content": content,
        "locale_actual": actual,
        "locale_requested": requested,
        "doc_type": doc_type,
        "is_draft": is_draft,
        "version_tag": CURRENT_VERSION_TAG,
        "available_locales": available,
    }
