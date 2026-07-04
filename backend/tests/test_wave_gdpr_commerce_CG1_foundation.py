"""Wave GDPR-Commerce Phase CG-1 — sentinel tests for the foundation layer.

Scope:
  - Store model exposes the per-store merchant legal fields
    (4 locales × 2 docs + display_locale + version_tag/hash +
    published_at + last_edited_at), all Optional, retrocompat with
    legacy store documents that don't carry them.

  - consent_audit_repository accepts the new optional fields
    (store_id, customer_email, order_id) and the new source +
    document_type enum members for the customer-side events,
    without rejecting any existing call shape (Phase B/E
    backward-compat preserved).

  - services/merchant_legal_versioning computes hashes from the
    display-locale bundle only, deterministically; state machine
    transitions correctly between not_configured / draft /
    published / stale_draft; tag bumper handles malformed input
    safely.

  - services/merchant_legal_template_service ships 8 template
    files (4 locales × 2 doc types), interpolates {{vars}} from a
    TemplateVars pydantic model, and never raises on unknown
    placeholders (left literal so the merchant can spot them).

All tests are additive — they exercise NEW code paths and verify
backward compat. No existing test in the suite is modified.
"""

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Store model: per-store legal fields ─────────────────────────────────


class TestStoreModelFields:
    """The Store model must carry the per-store merchant legal block.

    All fields Optional with safe defaults so existing store docs
    deserialize unchanged.
    """

    def test_store_has_new_legal_fields(self):
        from models.store import Store

        # Build with bare minimum — new fields default to None
        s = Store(
            organization_id="org-1",
            name="Acme",
            slug="acme",
        )
        # 4 locales × 2 doc types
        for loc in ("it", "en", "de", "fr"):
            assert hasattr(s, f"merchant_privacy_content_{loc}")
            assert hasattr(s, f"merchant_terms_content_{loc}")
            assert getattr(s, f"merchant_privacy_content_{loc}") is None
            assert getattr(s, f"merchant_terms_content_{loc}") is None

        # Versioning + lifecycle
        assert s.merchant_legal_display_locale is None
        assert s.merchant_legal_version_tag is None
        assert s.merchant_legal_version_hash is None
        assert s.merchant_legal_published_at is None
        assert s.merchant_legal_last_edited_at is None

    def test_store_accepts_explicit_legal_block(self):
        from models.store import Store

        s = Store(
            organization_id="org-1",
            name="Acme",
            slug="acme",
            merchant_privacy_content_it="# Privacy IT",
            merchant_privacy_content_en="# Privacy EN",
            merchant_terms_content_it="# Terms IT",
            merchant_terms_content_en="# Terms EN",
            merchant_legal_display_locale="it",
            merchant_legal_version_tag="v1.0",
            merchant_legal_version_hash="abcdef0123456789",
            merchant_legal_published_at="2026-05-18T10:00:00+00:00",
        )
        assert s.merchant_privacy_content_it == "# Privacy IT"
        assert s.merchant_legal_display_locale == "it"
        assert s.merchant_legal_version_tag == "v1.0"

    def test_content_max_length_enforced_at_30k(self):
        from pydantic import ValidationError
        from models.store import Store

        too_long = "x" * 30_001
        with pytest.raises(ValidationError):
            Store(
                organization_id="org-1",
                name="Acme",
                slug="acme",
                merchant_privacy_content_it=too_long,
            )


# ── consent_audit_repository: extended fields + enums ───────────────────


class TestConsentAuditExtended:
    """Phase CG-1 extends record_consent with optional store_id,
    customer_email, order_id; user_id is now Optional (guest support);
    new source + document_type enum members are accepted."""

    @pytest.mark.asyncio
    async def test_record_consent_accepts_new_fields(self):
        from repositories import consent_audit_repository as car

        captured = {}

        class FakeColl:
            async def insert_one(self, doc):
                captured["doc"] = doc

        with patch.object(car, "consent_audit_collection", FakeColl()):
            result = await car.record_consent(
                user_id="customer-1",
                organization_id="org-1",
                store_id="store-1",
                order_id="order-1",
                customer_email="buyer@example.com",
                locale="it",
                version_tag="v1.0",
                version_hash="abc1234567890def",
                ip_address="1.2.3.4",
                user_agent="Mozilla/5.0",
                source="customer_checkout",
                document_type="merchant_privacy",
            )

        doc = captured["doc"]
        assert doc["store_id"] == "store-1"
        assert doc["order_id"] == "order-1"
        assert doc["customer_email"] == "buyer@example.com"
        assert doc["source"] == "customer_checkout"
        assert doc["document_type"] == "merchant_privacy"

    @pytest.mark.asyncio
    async def test_record_consent_guest_without_user_id(self):
        """Guest checkout: user_id=None is allowed IFF customer_email
        is provided (legal subject must be identifiable)."""
        from repositories import consent_audit_repository as car

        captured = {}

        class FakeColl:
            async def insert_one(self, doc):
                captured["doc"] = doc

        with patch.object(car, "consent_audit_collection", FakeColl()):
            await car.record_consent(
                user_id=None,
                organization_id="org-1",
                store_id="store-1",
                customer_email="Guest@Example.Com",  # case-normalised
                locale="it",
                version_tag="v1.0",
                version_hash="abc1234567890def",
                source="customer_checkout",
                document_type="merchant_terms",
            )

        doc = captured["doc"]
        assert doc["user_id"] is None
        assert doc["customer_email"] == "guest@example.com"

    @pytest.mark.asyncio
    async def test_record_consent_rejects_no_identifiable_subject(self):
        """Both user_id AND customer_email missing → ValueError."""
        from repositories import consent_audit_repository as car

        with pytest.raises(ValueError, match="data subject"):
            await car.record_consent(
                user_id=None,
                customer_email=None,
                locale="it",
                version_tag="v1.0",
                version_hash="abc1234567890def",
                source="customer_checkout",
                document_type="merchant_privacy",
            )

    def test_new_source_and_doc_type_enums_present(self):
        from repositories import consent_audit_repository as car

        for s in (
            "customer_signup", "customer_re_acceptance",
            "customer_checkout",
            "customer_marketing_optin", "customer_marketing_revoke",
            "customer_deletion_request",
            "merchant_dpa_acknowledged",
        ):
            assert s in car._VALID_SOURCES

        for d in (
            "merchant_privacy", "merchant_terms",
            "merchant_marketing", "merchant_dpa",
        ):
            assert d in car._VALID_DOCUMENT_TYPES

    def test_legacy_sources_and_doc_types_still_present(self):
        """Phase A/B/E enum members must remain in the set —
        regression guard for retrocompat."""
        from repositories import consent_audit_repository as car

        for s in ("signup", "re_acceptance", "backfill"):
            assert s in car._VALID_SOURCES
        for d in ("privacy_terms", "privacy_only", "terms_only"):
            assert d in car._VALID_DOCUMENT_TYPES


# ── merchant_legal_versioning ───────────────────────────────────────────


class TestVersioningHash:
    """Hash depends ONLY on the display-locale bundle. Editing other
    locales does not change it (the cornerstone of the language model:
    only display_locale is legally visible to customers).

    Wave CG-3-Polish (2026-05-18) updated the resolution of the
    display locale: it now derives from ``storefront_languages[0]``
    via ``get_effective_display_locale``, with the legacy explicit
    ``merchant_legal_display_locale`` field still honoured for
    backward compat. So a store with ``storefront_languages=["it"]``
    and content in IT now produces a valid hash without setting the
    legacy field.
    """

    def test_hash_uses_storefront_languages_when_no_explicit_locale(self):
        """CG-3-Polish: no explicit merchant_legal_display_locale →
        derive from storefront_languages[0]. The hash is computed
        successfully because IT content is present and IT is the
        store's primary language."""
        from services.merchant_legal_versioning import compute_legal_hash

        store = {
            "storefront_languages": ["it"],
            "merchant_privacy_content_it": "# Privacy",
            "merchant_terms_content_it": "# Terms",
        }
        h = compute_legal_hash(store)
        assert h is not None and len(h) == 16

    def test_hash_none_when_storefront_languages_empty_and_no_content(self):
        """When neither explicit locale nor storefront_languages are
        useful AND the IT fallback locale has empty content, hash is
        None — caller must surface the "not_configured" status."""
        from services.merchant_legal_versioning import compute_legal_hash

        store = {
            # No storefront_languages, no explicit field
            "merchant_privacy_content_en": "# Privacy EN",
            "merchant_terms_content_en": "# Terms EN",
            # IT fallback has no content
        }
        assert compute_legal_hash(store) is None

    def test_hash_none_when_one_doc_missing(self):
        from services.merchant_legal_versioning import compute_legal_hash

        store = {
            "merchant_legal_display_locale": "it",
            "merchant_privacy_content_it": "# Privacy",
            # No terms content → hash undefined
        }
        assert compute_legal_hash(store) is None

    def test_hash_deterministic_and_uses_only_display_locale(self):
        from services.merchant_legal_versioning import compute_legal_hash

        base = {
            "merchant_legal_display_locale": "it",
            "merchant_privacy_content_it": "# Privacy IT",
            "merchant_terms_content_it": "# Terms IT",
            # Other locales — should NOT affect the hash
            "merchant_privacy_content_en": "# Privacy EN",
            "merchant_terms_content_en": "# Terms EN",
            "merchant_privacy_content_de": "different",
            "merchant_terms_content_de": "different",
        }

        h1 = compute_legal_hash(base)
        h2 = compute_legal_hash(base)
        assert h1 == h2
        assert len(h1) == 16

        # Manual recomputation
        expected = hashlib.sha256(
            (base["merchant_privacy_content_it"]
             + "\n\n--- TERMS BUNDLE ---\n\n"
             + base["merchant_terms_content_it"]).encode()
        ).hexdigest()[:16]
        assert h1 == expected

        # Mutating EN/DE must NOT change the hash
        mutated = {**base, "merchant_privacy_content_en": "totally new EN"}
        assert compute_legal_hash(mutated) == h1

        # Mutating IT (the display locale) DOES change the hash
        mutated_it = {**base, "merchant_privacy_content_it": "# CHANGED IT"}
        assert compute_legal_hash(mutated_it) != h1

    def test_hash_changes_when_display_locale_switches(self):
        """Cornerstone: changing the display_locale flips which content
        gets hashed, so the hash changes — which is exactly what we
        want (triggers re-consent of registered customers)."""
        from services.merchant_legal_versioning import compute_legal_hash

        store = {
            "merchant_legal_display_locale": "it",
            "merchant_privacy_content_it": "# Privacy IT",
            "merchant_terms_content_it": "# Terms IT",
            "merchant_privacy_content_en": "# Privacy EN",
            "merchant_terms_content_en": "# Terms EN",
        }
        h_it = compute_legal_hash(store)

        store["merchant_legal_display_locale"] = "en"
        h_en = compute_legal_hash(store)

        assert h_it != h_en

    def test_hash_works_with_pydantic_store_model(self):
        """CG-3-Polish-2 updated priority: storefront_languages[0]
        wins. Build the Store with both storefront_languages=["en"]
        AND English content, so the resolver picks EN and the hash
        materialises from EN content."""
        from models.store import Store
        from services.merchant_legal_versioning import compute_legal_hash

        s = Store(
            organization_id="org-1", name="Acme", slug="acme",
            storefront_languages=["en"],
            merchant_privacy_content_en="# P",
            merchant_terms_content_en="# T",
        )
        h = compute_legal_hash(s)
        assert h is not None and len(h) == 16


class TestVersioningStatus:
    """State machine: not_configured → draft → published → stale_draft."""

    def test_status_not_configured_when_display_unset(self):
        from services.merchant_legal_versioning import merchant_legal_status

        assert merchant_legal_status({}) == "not_configured"
        assert merchant_legal_status(
            {"merchant_legal_display_locale": None}
        ) == "not_configured"

    def test_status_not_configured_when_display_content_empty(self):
        from services.merchant_legal_versioning import merchant_legal_status

        store = {
            "merchant_legal_display_locale": "it",
            "merchant_privacy_content_it": "",   # empty
            "merchant_terms_content_it": "# T",
        }
        assert merchant_legal_status(store) == "not_configured"

    def test_status_draft_when_content_but_never_published(self):
        from services.merchant_legal_versioning import merchant_legal_status

        store = {
            "merchant_legal_display_locale": "it",
            "merchant_privacy_content_it": "# P",
            "merchant_terms_content_it": "# T",
            "merchant_legal_published_at": None,
        }
        assert merchant_legal_status(store) == "draft"

    def test_status_published_when_in_sync(self):
        from services.merchant_legal_versioning import (
            compute_legal_hash, merchant_legal_status,
        )

        store = {
            "merchant_legal_display_locale": "it",
            "merchant_privacy_content_it": "# P",
            "merchant_terms_content_it": "# T",
            "merchant_legal_published_at": "2026-05-18T10:00:00+00:00",
            "merchant_legal_last_edited_at": "2026-05-18T09:00:00+00:00",
        }
        store["merchant_legal_version_hash"] = compute_legal_hash(store)
        assert merchant_legal_status(store) == "published"

    def test_status_stale_draft_after_edit(self):
        from services.merchant_legal_versioning import (
            compute_legal_hash, merchant_legal_status,
        )

        store = {
            "merchant_legal_display_locale": "it",
            "merchant_privacy_content_it": "# P",
            "merchant_terms_content_it": "# T",
            "merchant_legal_published_at": "2026-05-18T10:00:00+00:00",
            "merchant_legal_version_hash": compute_legal_hash({
                "merchant_legal_display_locale": "it",
                "merchant_privacy_content_it": "# P",
                "merchant_terms_content_it": "# T",
            }),
            "merchant_legal_last_edited_at": "2026-05-18T11:00:00+00:00",
        }
        assert merchant_legal_status(store) == "stale_draft"

    def test_status_stale_draft_on_hash_drift(self):
        """Hash drift (DB-tampering edge case) also flags stale_draft."""
        from services.merchant_legal_versioning import merchant_legal_status

        store = {
            "merchant_legal_display_locale": "it",
            "merchant_privacy_content_it": "# CHANGED",
            "merchant_terms_content_it": "# T",
            "merchant_legal_published_at": "2026-05-18T10:00:00+00:00",
            "merchant_legal_last_edited_at": "2026-05-18T09:00:00+00:00",
            # Stored hash from BEFORE the content change
            "merchant_legal_version_hash": "stalehash000abcd",
        }
        assert merchant_legal_status(store) == "stale_draft"


class TestVersionTagBump:
    """bump_version_tag handles all happy paths + malformed inputs."""

    def test_bump_first_publish(self):
        from services.merchant_legal_versioning import bump_version_tag
        assert bump_version_tag(None) == "v1.0"
        assert bump_version_tag("") == "v1.0"

    def test_bump_minor(self):
        from services.merchant_legal_versioning import bump_version_tag
        assert bump_version_tag("v1.0") == "v1.1"
        assert bump_version_tag("v1.7") == "v1.8"
        assert bump_version_tag("v2.3") == "v2.4"

    def test_bump_malformed_falls_back_to_v1_0(self):
        from services.merchant_legal_versioning import bump_version_tag
        assert bump_version_tag("garbage") == "v1.0"
        assert bump_version_tag("1.0") == "v1.0"     # missing 'v'
        assert bump_version_tag("v1.0.1") == "v1.0"  # patch component not supported


class TestCurrentVersionString:
    def test_none_when_not_published(self):
        from services.merchant_legal_versioning import current_version_string

        assert current_version_string({}) is None
        assert current_version_string(
            {"merchant_legal_version_tag": "v1.0"}
        ) is None

    def test_concatenated_when_published(self):
        from services.merchant_legal_versioning import current_version_string

        store = {
            "merchant_legal_version_tag": "v1.0",
            "merchant_legal_version_hash": "abc1234567890def",
        }
        assert current_version_string(store) == "v1.0:abc1234567890def"


# ── merchant_legal_template_service ─────────────────────────────────────


class TestTemplateFilesPresent:
    """All 8 templates (4 locales × 2 doc types) must ship."""

    TEMPLATE_DIR = (
        BACKEND_DIR / "legal" / "merchant_templates"
    )

    @pytest.mark.parametrize("doc_type", ["privacy", "terms"])
    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_template_file_exists(self, doc_type, locale):
        path = self.TEMPLATE_DIR / f"{doc_type}_{locale}.template.md"
        assert path.exists(), (
            f"Wave GDPR-Commerce CG-1 regression — missing merchant "
            f"template {path}. The 4 × 2 matrix is mandatory."
        )

    def test_list_template_files_returns_all_8(self):
        from services.merchant_legal_template_service import list_template_files
        paths = list_template_files()
        assert len(paths) == 8


class TestTemplateRender:
    """Variable interpolation is simple {{name}} → str(value), unknown
    placeholders left literal, no Jinja, no eval."""

    def _vars(self, **overrides):
        from services.merchant_legal_template_service import TemplateVars
        defaults = dict(
            merchant_name="Mario Rossi",
            merchant_email="mario@example.com",
            merchant_country="Italia",
            store_name="Mario Store",
            store_country="Italia",
            collects_phone=True,
            collects_shipping_address=True,
            uses_marketing=False,
            ships_to_eu=True,
        )
        defaults.update(overrides)
        return TemplateVars(**defaults)

    @pytest.mark.parametrize("doc_type", ["privacy", "terms"])
    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_render_each_combination(self, doc_type, locale):
        from services.merchant_legal_template_service import render_template
        out = render_template(doc_type, locale, self._vars())
        # Merchant identity vars always interpolated everywhere
        assert "Mario Rossi" in out
        assert "mario@example.com" in out
        assert "Mario Store" in out
        # Platform identity always mentioned (afianco as processor)
        assert "afianco" in out
        # No raw placeholder for variables we provided
        assert "{{merchant_name}}" not in out
        assert "{{store_name}}" not in out
        # Reasonable length sanity
        assert len(out) > 2000

    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_privacy_discloses_platform_controller_email(self, locale):
        """The PRIVACY doc must surface the platform's contact email
        because afianco is the data processor (sub-processor chain
        disclosure under GDPR Art. 28.3.i + Art. 13.1.f). Terms doc
        does not strictly need it, so we only assert it for privacy."""
        from services.merchant_legal_template_service import render_template
        out = render_template("privacy", locale, self._vars())
        assert "davide@afianco.ch" in out

    def test_render_invalid_doc_type_raises(self):
        from services.merchant_legal_template_service import render_template
        with pytest.raises(ValueError, match="doc_type"):
            render_template("invalid", "it", self._vars())

    def test_render_invalid_locale_raises(self):
        from services.merchant_legal_template_service import render_template
        with pytest.raises(ValueError, match="locale"):
            render_template("privacy", "xx", self._vars())

    def test_unknown_placeholder_left_literal(self):
        """A template line with {{unknown_var}} survives interpolation
        unchanged — gives the merchant a visual handle to spot gaps.

        We don't ship templates with unknown placeholders, but the
        contract matters: if a future template adds a new placeholder
        before the TemplateVars model catches up, render() must not
        raise."""
        from services.merchant_legal_template_service import _interpolate, TemplateVars
        result = _interpolate(
            "Hello {{merchant_name}}, see {{unknown_thing}}.",
            TemplateVars(merchant_name="X"),
        )
        assert result == "Hello X, see {{unknown_thing}}."
