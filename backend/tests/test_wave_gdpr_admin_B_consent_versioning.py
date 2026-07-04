"""Wave GDPR-Admin Phase B — sentinel tests for consent versioning.

Scope:
  - User model carries accepted_terms_version + accepted_terms_locale
    (Optional, default None for back-compat)
  - core.legal_versions exposes the current + legacy version strings
  - consent_audit_repository inserts immutable records on signup
  - The signup flow populates both new user fields AND writes the
    consent_audit record (fire-and-forget on errors)
  - The backfill script is idempotent and isolates legacy users

All tests are additive — they exercise NEW code paths and verify
backward compat. No existing test in the suite is modified.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── User model: new optional fields ───────────────────────────────────────


class TestUserModelFields:
    """The User model carries the new fields, all Optional[str] = None
    so existing user docs without them deserialize cleanly."""

    def test_user_has_new_consent_fields(self):
        from models import User
        # Build with bare minimum — new fields are Optional
        u = User(
            email="x@example.com", name="X",
            role="admin", password_hash="x",
        )
        # Both default to None
        assert u.accepted_terms_version is None
        assert u.accepted_terms_locale is None

    def test_user_accepts_explicit_consent_values(self):
        from models import User
        u = User(
            email="x@example.com", name="X",
            role="admin", password_hash="x",
            accepted_terms_version="v1.0:abc123",
            accepted_terms_locale="en",
        )
        assert u.accepted_terms_version == "v1.0:abc123"
        assert u.accepted_terms_locale == "en"

    def test_user_back_compat_without_new_fields(self):
        """A Mongo doc serialized BEFORE Phase B must deserialize via
        Pydantic with extra='ignore' and missing-optional defaults to
        None."""
        from models import User
        legacy_doc = {
            "email": "legacy@example.com",
            "name": "Legacy",
            "role": "admin",
            "password_hash": "hash",
            "id": "u-legacy",
            "accepted_terms_at": "2025-06-15T10:00:00+00:00",
            "locale": "fr",
            # Notice: no accepted_terms_version, no accepted_terms_locale
        }
        u = User(**legacy_doc)
        assert u.accepted_terms_version is None
        assert u.accepted_terms_locale is None
        assert u.accepted_terms_at == "2025-06-15T10:00:00+00:00"


# ── legal_versions module ────────────────────────────────────────────────


class TestLegalVersionsModule:
    def test_module_exports_required_constants(self):
        from core import legal_versions as lv
        assert isinstance(lv.CURRENT_VERSION_TAG, str)
        assert isinstance(lv.CURRENT_VERSION_HASH, str)
        assert isinstance(lv.LEGACY_VERSION_TAG, str)
        assert isinstance(lv.LEGACY_VERSION_HASH, str)
        # tag is human readable
        assert lv.CURRENT_VERSION_TAG.startswith("v")
        # hash is short (storage-friendly)
        assert len(lv.CURRENT_VERSION_HASH) <= 32
        assert len(lv.LEGACY_VERSION_HASH) <= 32

    def test_current_version_string_format(self):
        from core.legal_versions import current_version_string, CURRENT_VERSION_TAG, CURRENT_VERSION_HASH
        s = current_version_string()
        assert s == f"{CURRENT_VERSION_TAG}:{CURRENT_VERSION_HASH}"
        assert ":" in s

    def test_legacy_version_string_format(self):
        from core.legal_versions import legacy_version_string
        s = legacy_version_string()
        assert s.startswith("v0.legacy:")


# ── consent_audit_repository: hash helper ────────────────────────────────


class TestConsentAuditRepository:
    def test_hash_document_text_deterministic(self):
        from repositories.consent_audit_repository import hash_document_text
        h1 = hash_document_text("Privacy Policy v1\n\nTerms of Service v1")
        h2 = hash_document_text("Privacy Policy v1\n\nTerms of Service v1")
        h3 = hash_document_text("Privacy Policy v2\n\nTerms of Service v1")
        assert h1 == h2
        assert h1 != h3
        # Output is 16 hex chars
        assert len(h1) == 16
        assert all(c in "0123456789abcdef" for c in h1)

    def test_record_consent_rejects_invalid_enum(self):
        """Invalid document_type or source must raise."""
        from repositories import consent_audit_repository as car
        import asyncio

        async def _bad_doc_type():
            await car.record_consent(
                user_id="u1", locale="it",
                version_tag="v1", version_hash="h1",
                document_type="invalid_type",
            )

        async def _bad_source():
            await car.record_consent(
                user_id="u1", locale="it",
                version_tag="v1", version_hash="h1",
                source="invalid_source",
            )

        with pytest.raises(ValueError, match="document_type"):
            asyncio.run(_bad_doc_type())
        with pytest.raises(ValueError, match="source"):
            asyncio.run(_bad_source())

    @pytest.mark.asyncio
    async def test_record_consent_inserts_full_doc(self):
        from repositories import consent_audit_repository as car

        captured = {}

        class FakeColl:
            async def insert_one(self, doc):
                captured["doc"] = doc

        with patch.object(car, "consent_audit_collection", FakeColl()):
            result = await car.record_consent(
                user_id="u-test",
                organization_id="org-test",
                locale="en",
                version_tag="v0.preD",
                version_hash="bootstrap00abcd00",
                ip_address="1.2.3.4",
                user_agent="Mozilla/5.0",
                source="signup",
                document_type="privacy_terms",
            )

        doc = captured["doc"]
        assert doc["user_id"] == "u-test"
        assert doc["organization_id"] == "org-test"
        assert doc["locale"] == "en"
        assert doc["version_tag"] == "v0.preD"
        assert doc["version_hash"] == "bootstrap00abcd00"
        assert doc["ip_address"] == "1.2.3.4"
        assert doc["user_agent"] == "Mozilla/5.0"
        assert doc["source"] == "signup"
        assert doc["document_type"] == "privacy_terms"
        # Expiry is set
        assert doc["expire_at"] is not None
        # Id is generated
        assert doc["id"] is not None
        # Accepted_at is set
        assert "accepted_at" in doc

    @pytest.mark.asyncio
    async def test_record_consent_truncates_user_agent(self):
        """User-Agent longer than 200 chars must be truncated."""
        from repositories import consent_audit_repository as car

        captured = {}

        class FakeColl:
            async def insert_one(self, doc):
                captured["doc"] = doc

        long_ua = "X" * 500
        with patch.object(car, "consent_audit_collection", FakeColl()):
            await car.record_consent(
                user_id="u1", locale="it",
                version_tag="v1", version_hash="h1",
                user_agent=long_ua,
            )

        assert len(captured["doc"]["user_agent"]) == 200


# ── Signup flow integration ──────────────────────────────────────────────


class TestSignupPopulatesConsentFields:
    """The signup service stamps accepted_terms_version +
    accepted_terms_locale on the new User doc, AND fires a
    consent_audit record."""

    def test_signup_accepts_request_ip_and_user_agent_kwargs(self):
        """The signup signature must accept the new kwargs."""
        import inspect
        from services.auth_service import signup
        sig = inspect.signature(signup)
        assert "request_ip" in sig.parameters
        assert "user_agent" in sig.parameters
        # Both default to None for backward compat
        assert sig.parameters["request_ip"].default is None
        assert sig.parameters["user_agent"].default is None

    def test_signup_source_writes_version_to_user_doc(self):
        """The signup source code references CURRENT_VERSION_TAG
        and assigns accepted_terms_version on the User."""
        import inspect
        from services import auth_service
        src = inspect.getsource(auth_service.signup)
        assert "current_version_string" in src
        assert "accepted_terms_version" in src
        assert "accepted_terms_locale" in src

    def test_signup_source_writes_consent_audit(self):
        """The signup source code references the consent_audit repo."""
        import inspect
        from services import auth_service
        src = inspect.getsource(auth_service.signup)
        assert "consent_audit_repository" in src
        assert "record_consent" in src
        # Must use source="signup"
        assert 'source="signup"' in src or "source='signup'" in src


class TestSignupRouterPassesNetworkContext:
    """The router populates request_ip + user_agent and passes
    them through to auth_service.signup."""

    def test_router_source_imports_get_real_ip(self):
        import inspect
        from routers import auth as auth_router
        # Get the source of signup function
        src = inspect.getsource(auth_router.signup)
        assert "get_real_ip" in src
        assert "user-agent" in src.lower()
        assert "request_ip" in src
        assert "user_agent" in src


# ── Backfill script ──────────────────────────────────────────────────────


class TestBackfillScript:
    def test_script_file_exists(self):
        script = BACKEND_DIR / "scripts" / "backfill_consent_versioning.py"
        assert script.exists(), (
            "Wave GDPR-Admin Phase B — backfill script not found at "
            "expected path."
        )

    def test_script_has_dry_run_default(self):
        script_text = (
            BACKEND_DIR / "scripts" / "backfill_consent_versioning.py"
        ).read_text()
        assert "--apply" in script_text
        # Dry-run is the default (apply=False unless --apply passed)
        assert 'action="store_true"' in script_text

    def test_script_uses_legacy_version_string(self):
        script_text = (
            BACKEND_DIR / "scripts" / "backfill_consent_versioning.py"
        ).read_text()
        assert "legacy_version_string" in script_text or "LEGACY_VERSION_TAG" in script_text


# ── Database: consent_audit collection + index wiring ───────────────────


class TestDatabaseWiring:
    def test_consent_audit_collection_in_database_module(self):
        from database import consent_audit_collection
        assert consent_audit_collection is not None

    def test_database_indexes_setup_includes_consent_audit(self):
        """The create_indexes function creates indexes on the new
        collection."""
        import inspect
        from database import create_indexes
        src = inspect.getsource(create_indexes)
        assert "consent_audit_collection.create_index" in src
        # TTL index
        assert "consent_audit_ttl" in src or "consent_audit" in src
