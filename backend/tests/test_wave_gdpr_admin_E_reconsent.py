"""Wave GDPR-Admin Phase E — sentinel tests for re-consent enforcement.

Scope:
  - UserResponse exposes accepted_terms_version, accepted_terms_locale,
    accepted_terms_at, current_terms_version, consent_needs_refresh.
  - auth_service.get_current_user_info computes consent_needs_refresh by
    comparing stored vs current_version_string().
  - System admins are EXEMPT from re-consent (they bump the docs).
  - POST /api/auth/re-consent records an immutable audit (source =
    "re_acceptance") AND updates the user doc atomically (audit first,
    then user-doc — see endpoint docstring for the failure-mode trade-off).
  - GET /api/legal/sub-processors returns a locale-aware registry with
    the canonical 5 sub-processors (Hetzner, MongoDB-self-hosted,
    Anthropic, Stripe, Brevo) and stable machine fields.

All tests are additive; nothing in Phase A/B/C/D is mutated.
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


# ── UserResponse: new consent fields surface on /auth/me ────────────────


class TestUserResponseConsentFields:
    """UserResponse must carry the Phase E consent block so the frontend
    can drive the blocking re-acceptance modal."""

    def test_user_response_has_consent_fields(self):
        from models.user import UserResponse, UserRole

        ur = UserResponse(
            id="u1",
            email="a@b.example.com",
            name="A",
            role=UserRole.ADMIN,
            organization_id="o1",
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )
        # Phase E fields are present, default to safe values.
        assert hasattr(ur, "accepted_terms_version")
        assert hasattr(ur, "accepted_terms_locale")
        assert hasattr(ur, "accepted_terms_at")
        assert hasattr(ur, "current_terms_version")
        assert hasattr(ur, "consent_needs_refresh")
        # Safe defaults
        assert ur.accepted_terms_version is None
        assert ur.accepted_terms_locale is None
        assert ur.consent_needs_refresh is False

    def test_user_response_accepts_explicit_consent_block(self):
        from models.user import UserResponse, UserRole

        ur = UserResponse(
            id="u1",
            email="a@b.example.com",
            name="A",
            role=UserRole.ADMIN,
            organization_id="o1",
            created_at=datetime.now(timezone.utc),
            is_active=True,
            accepted_terms_version="v0.9:olderhash00000",
            accepted_terms_locale="it",
            accepted_terms_at="2026-05-16T10:00:00+00:00",
            current_terms_version="v1.0:48eaf31ba7826c92",
            consent_needs_refresh=True,
        )
        assert ur.accepted_terms_version == "v0.9:olderhash00000"
        assert ur.consent_needs_refresh is True


# ── auth_service.get_current_user_info: needs_refresh computation ───────


class TestGetCurrentUserInfoConsentLogic:
    """The service-layer helper must compute consent_needs_refresh as
    (accepted_terms_version != current_version_string()), with the
    system_admin role exempted."""

    @pytest.mark.asyncio
    async def test_user_with_current_version_does_not_need_refresh(self):
        from services import auth_service
        from core.legal_versions import current_version_string

        cur = current_version_string()
        fake_user = {
            "id": "u1",
            "email": "u@example.com",
            "name": "U",
            "role": "admin",
            "organization_id": "o1",
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
            "must_change_password": False,
            "email_verified": True,
            "locale": "it",
            "accepted_terms_version": cur,
            "accepted_terms_locale": "it",
            "accepted_terms_at": "2026-05-18T10:00:00+00:00",
        }

        with patch(
            "services.auth_service.user_repository.find_by_id",
            new=AsyncMock(return_value=fake_user),
        ), patch(
            "services.auth_service.organization_repository.find_by_id",
            new=AsyncMock(return_value={"currency": "CHF", "settings": {}}),
        ):
            ur = await auth_service.get_current_user_info("u1")

        assert ur.consent_needs_refresh is False
        assert ur.accepted_terms_version == cur
        assert ur.current_terms_version == cur

    @pytest.mark.asyncio
    async def test_user_with_stale_version_needs_refresh(self):
        from services import auth_service

        fake_user = {
            "id": "u2",
            "email": "u2@example.com",
            "name": "U2",
            "role": "admin",
            "organization_id": "o1",
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
            "must_change_password": False,
            "email_verified": True,
            "locale": "it",
            # Deliberately stale tag
            "accepted_terms_version": "v0.9:somethingold0000",
            "accepted_terms_locale": "it",
            "accepted_terms_at": "2026-05-16T10:00:00+00:00",
        }

        with patch(
            "services.auth_service.user_repository.find_by_id",
            new=AsyncMock(return_value=fake_user),
        ), patch(
            "services.auth_service.organization_repository.find_by_id",
            new=AsyncMock(return_value=None),
        ):
            ur = await auth_service.get_current_user_info("u2")

        assert ur.consent_needs_refresh is True
        assert ur.accepted_terms_version == "v0.9:somethingold0000"

    @pytest.mark.asyncio
    async def test_legacy_user_without_version_needs_refresh(self):
        from services import auth_service

        fake_user = {
            "id": "u3",
            "email": "legacy@example.com",
            "name": "L",
            "role": "admin",
            "organization_id": "o1",
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
            "must_change_password": False,
            "email_verified": True,
            "locale": "it",
            # No accepted_terms_version field at all (legacy)
        }

        with patch(
            "services.auth_service.user_repository.find_by_id",
            new=AsyncMock(return_value=fake_user),
        ), patch(
            "services.auth_service.organization_repository.find_by_id",
            new=AsyncMock(return_value=None),
        ):
            ur = await auth_service.get_current_user_info("u3")

        assert ur.consent_needs_refresh is True
        assert ur.accepted_terms_version is None

    @pytest.mark.asyncio
    async def test_system_admin_is_exempt_from_reconsent(self):
        """system_admin bumps the docs themselves — they must NEVER be
        blocked by the modal."""
        from services import auth_service

        fake_user = {
            "id": "sa1",
            "email": "sa@example.com",
            "name": "SA",
            "role": "system_admin",
            "organization_id": None,
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
            "must_change_password": False,
            "email_verified": True,
            "locale": "it",
            "accepted_terms_version": None,
        }

        with patch(
            "services.auth_service.user_repository.find_by_id",
            new=AsyncMock(return_value=fake_user),
        ):
            ur = await auth_service.get_current_user_info("sa1")

        assert ur.consent_needs_refresh is False


# ── POST /api/auth/re-consent endpoint ──────────────────────────────────


class TestReConsentEndpoint:
    """The endpoint records an immutable audit AND updates the user doc."""

    @pytest.mark.asyncio
    async def test_re_consent_records_audit_and_updates_user(self):
        from routers import auth as auth_router
        from core.legal_versions import (
            CURRENT_VERSION_TAG,
            CURRENT_VERSION_HASH,
            current_version_string,
        )

        captured_audit = {}
        captured_update = {}

        async def _fake_record(**kwargs):
            captured_audit.update(kwargs)
            return {"id": "audit-1", **kwargs}

        async def _fake_update(user_id, patch_dict):
            captured_update["user_id"] = user_id
            captured_update["patch"] = patch_dict

        async def _fake_find(user_id):
            return {
                "id": user_id,
                "email": "u@example.com",
                "name": "U",
                "role": "admin",
                "organization_id": "o1",
                "created_at": datetime.now(timezone.utc),
                "is_active": True,
                "must_change_password": False,
                "email_verified": True,
                "locale": "it",
                "accepted_terms_version": current_version_string(),
                "accepted_terms_locale": "it",
                "accepted_terms_at": "2026-05-18T10:00:00+00:00",
            }

        # Fake request object mimicking FastAPI Request
        class FakeClient:
            host = "9.9.9.9"

        class FakeRequest:
            client = FakeClient()
            headers = {"user-agent": "pytest/0"}

            async def json(self):
                return {"locale": "it"}

        with patch(
            "repositories.consent_audit_repository.record_consent",
            new=_fake_record,
        ), patch(
            "repositories.user_repository.update",
            new=_fake_update,
        ), patch(
            "repositories.user_repository.find_by_id",
            new=_fake_find,
        ), patch(
            "services.auth_service.user_repository.find_by_id",
            new=_fake_find,
        ), patch(
            "services.auth_service.organization_repository.find_by_id",
            new=AsyncMock(return_value=None),
        ):
            result = await auth_router.re_consent(
                request=FakeRequest(),
                current_user={"user_id": "u-test"},
            )

        # Audit was written with the canonical args
        assert captured_audit["user_id"] == "u-test"
        assert captured_audit["locale"] == "it"
        assert captured_audit["version_tag"] == CURRENT_VERSION_TAG
        assert captured_audit["version_hash"] == CURRENT_VERSION_HASH
        assert captured_audit["source"] == "re_acceptance"
        assert captured_audit["document_type"] == "privacy_terms"
        assert captured_audit["ip_address"] == "9.9.9.9"
        assert captured_audit["user_agent"] == "pytest/0"

        # User doc was patched to the current version
        assert captured_update["user_id"] == "u-test"
        assert captured_update["patch"]["accepted_terms_version"] == current_version_string()
        assert captured_update["patch"]["accepted_terms_locale"] == "it"
        assert "accepted_terms_at" in captured_update["patch"]

    @pytest.mark.asyncio
    async def test_re_consent_rejects_unsupported_locale(self):
        from fastapi import HTTPException
        from routers import auth as auth_router

        class FakeRequest:
            client = None
            headers = {}

            async def json(self):
                return {"locale": "xx"}

        with pytest.raises(HTTPException) as exc_info:
            await auth_router.re_consent(
                request=FakeRequest(),
                current_user={"user_id": "u-test"},
            )
        assert exc_info.value.status_code == 400
        assert "Unsupported locale" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_re_consent_404_when_user_missing(self):
        from fastapi import HTTPException
        from routers import auth as auth_router

        class FakeRequest:
            client = None
            headers = {}

            async def json(self):
                return {"locale": "it"}

        with patch(
            "repositories.user_repository.find_by_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await auth_router.re_consent(
                    request=FakeRequest(),
                    current_user={"user_id": "missing"},
                )
        assert exc_info.value.status_code == 404


# ── GET /api/legal/sub-processors endpoint ──────────────────────────────


class TestSubProcessorsEndpoint:
    """The sub-processors registry endpoint is the public, discoverable
    source of truth required by GDPR Art. 28.3.i + Art. 13.1.f."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    async def test_returns_canonical_5_processors_in_each_locale(self, locale):
        import json
        from routers.legal import get_sub_processors

        response = await get_sub_processors(lang=locale)
        body = json.loads(response.body)

        assert body["locale_actual"] == locale
        assert body["binding_locale"] == "it"
        assert "version_tag" in body
        assert body["version_tag"]  # non-empty

        sps = body["sub_processors"]
        ids = [s["id"] for s in sps]
        assert set(ids) == {
            "hetzner", "mongodb_self_hosted",
            "anthropic", "stripe", "brevo",
        }, (
            f"Sub-processor list drift detected for locale={locale}. "
            f"Expected exactly the 5 canonical processors disclosed in "
            f"the Privacy Policy. Adding/removing entries here MUST be "
            f"mirrored in privacy_<locale>.md."
        )

        # Each entry has the legally-required fields populated
        for s in sps:
            for required in ("name", "country_code", "url",
                             "purpose", "data", "safeguard"):
                assert s.get(required), (
                    f"sub-processor {s['id']} missing field {required!r} "
                    f"for locale {locale}"
                )

    @pytest.mark.asyncio
    async def test_invalid_locale_falls_back_to_italian(self):
        import json
        from routers.legal import get_sub_processors

        response = await get_sub_processors(lang="xx-unknown")
        body = json.loads(response.body)
        assert body["locale_actual"] == "it"
        assert body["locale_requested"] == "xx-unknown"

    @pytest.mark.asyncio
    async def test_anthropic_carries_dpf_safeguard(self):
        """Anthropic is the only non-EU/EEA processor — the safeguard
        field must explicitly mention SCC and/or Data Privacy Framework."""
        import json
        from routers.legal import get_sub_processors

        response = await get_sub_processors(lang="en")
        body = json.loads(response.body)
        anthropic = next(s for s in body["sub_processors"] if s["id"] == "anthropic")
        assert anthropic["is_eu_eea"] is False
        safeguard = anthropic["safeguard"]
        # Either DPF or SCC must appear (the en bundle uses both)
        assert ("Data Privacy Framework" in safeguard) or ("DPF" in safeguard) \
            or ("SCC" in safeguard.upper())

    @pytest.mark.asyncio
    async def test_controller_block_present(self):
        """The controller identity is part of the public envelope so
        downstream tooling (audit exports) can render it standalone."""
        import json
        from routers.legal import get_sub_processors

        response = await get_sub_processors(lang="it")
        body = json.loads(response.body)
        assert body["controller"]["name"] == "Davide De Filippis"
        assert body["controller"]["country"] == "Switzerland"
        assert body["controller"]["email"] == "info@aurya.life"   # R1 rebrand

    @pytest.mark.asyncio
    async def test_cache_header_set(self):
        from routers.legal import get_sub_processors

        response = await get_sub_processors(lang="it")
        cc = response.headers.get("cache-control") or response.headers.get("Cache-Control")
        assert cc is not None
        assert "public" in cc.lower()
        assert "max-age" in cc.lower()


# ── Router wiring sanity ────────────────────────────────────────────────


class TestRouterWiring:
    """The new endpoints must be registered on the FastAPI app."""

    def _collect_paths(self):
        from server import app
        # Only "real" routes have .methods; static-file mounts don't.
        return {
            (r.path, frozenset(getattr(r, "methods") or set()))
            for r in app.routes
            if getattr(r, "methods", None) is not None
        }

    def test_re_consent_route_registered(self):
        paths = self._collect_paths()
        # /api prefix is added by the include_router call
        assert ("/api/auth/re-consent", frozenset({"POST"})) in paths

    def test_sub_processors_route_registered(self):
        paths = self._collect_paths()
        assert ("/api/legal/sub-processors", frozenset({"GET"})) in paths
