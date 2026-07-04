"""Wave GDPR-Commerce Phase CG-7 — sentinel tests for the DPA flow.

Scope:
  - 4 DPA template files (it/en/de/fr) ship in backend/legal/
  - GET /api/legal/dpa renders the template with the caller's org
    identity (server-side; never trusted from request)
  - POST /api/legal/dpa/acknowledge records an immutable audit record
    with source="merchant_dpa_acknowledged" and document_type="merchant_dpa"
  - The acknowledgement is IDEMPOTENT: a second POST returns the
    original timestamp without creating a duplicate record (no audit
    spam from double-clicks)
  - GET /api/legal/dpa/status surfaces whether the org has acknowledged
  - Multi-tenant: status / acknowledge for org A never sees org B data
  - The 3 routes are registered on the FastAPI app
"""

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


# ─── Fixtures ────────────────────────────────────────────────────────


def _admin(org_id: str = "org-1") -> dict:
    return {"user_id": "u-1", "organization_id": org_id, "role": "admin"}


def _org(org_id: str = "org-1") -> dict:
    return {
        "id": org_id,
        "name": "Acme SRL",
        "contact_email": "acme@example.com",
        "country": "Italia",
        "is_active": True,
    }


# ─── Template files ──────────────────────────────────────────────────


class TestDpaTemplatesPresent:
    """All 4 DPA templates must ship."""

    LEGAL_DIR = BACKEND_DIR / "legal"

    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_dpa_file_exists(self, locale):
        path = self.LEGAL_DIR / f"dpa_{locale}.md"
        assert path.exists(), (
            f"Wave GDPR-Commerce CG-7 regression — missing DPA template "
            f"{path}. All 4 locales must be present."
        )

    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_dpa_file_has_required_sections(self, locale):
        """Each template must contain section markers covering the core
        Art. 28 obligations. This catches accidentally-truncated files."""
        path = self.LEGAL_DIR / f"dpa_{locale}.md"
        content = path.read_text(encoding="utf-8")
        # All locales preserve numbered section anchors 1-16.
        for n in range(1, 17):
            assert f"## {n}." in content, (
                f"DPA {locale}: missing section #{n}"
            )
        # The variables MUST be present in every locale (they're
        # interpolated at render time).
        for var in ("{{merchant_name}}", "{{merchant_email}}",
                    "{{org_id}}", "{{date}}"):
            assert var in content, (
                f"DPA {locale}: missing placeholder {var}"
            )


# ─── GET /dpa ────────────────────────────────────────────────────────


class TestGetDpa:
    """Render endpoint interpolates server-side vars + cache-control."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    async def test_returns_rendered_content_per_locale(self, locale):
        import json
        from routers.legal import get_dpa

        with patch(
            "routers.legal.organizations_collection.find_one"
            if False  # placeholder pattern; we patch at source below
            else "database.organizations_collection",
            new=AsyncMock(),
        ) as _:
            pass

        # Real patch path — the function imports organizations_collection
        # inside _load_dpa_vars.
        with patch(
            "database.organizations_collection.find_one",
            new=AsyncMock(return_value=_org()),
        ):
            response = await get_dpa(lang=locale, current_user=_admin())

        body = json.loads(response.body)
        assert body["locale_actual"] == locale
        assert body["locale_requested"] == locale
        # Server-side vars interpolated
        assert "Acme SRL" in body["content"]
        assert "acme@example.com" in body["content"]
        assert "org-1" in body["content"]
        # The {{date}} placeholder is replaced with a valid ISO date
        assert body["vars"]["date"]
        # No raw placeholder leak
        assert "{{merchant_name}}" not in body["content"]

    @pytest.mark.asyncio
    async def test_invalid_locale_falls_back_to_it(self):
        import json
        from routers.legal import get_dpa

        with patch(
            "database.organizations_collection.find_one",
            new=AsyncMock(return_value=_org()),
        ):
            response = await get_dpa(lang="xx-bogus", current_user=_admin())

        body = json.loads(response.body)
        assert body["locale_actual"] == "it"
        assert body["locale_requested"] == "xx-bogus"

    @pytest.mark.asyncio
    async def test_cache_is_private_no_store(self):
        """The rendered DPA contains org identity → must not be cached
        by browsers or CDNs."""
        from routers.legal import get_dpa

        with patch(
            "database.organizations_collection.find_one",
            new=AsyncMock(return_value=_org()),
        ):
            response = await get_dpa(lang="it", current_user=_admin())

        cc = (response.headers.get("cache-control")
              or response.headers.get("Cache-Control"))
        assert cc is not None
        assert "private" in cc.lower()
        assert "no-store" in cc.lower()

    @pytest.mark.asyncio
    async def test_system_admin_without_org_is_blocked(self):
        from fastapi import HTTPException
        from routers.legal import get_dpa

        sa = {"user_id": "sa", "organization_id": None, "role": "system_admin"}
        with pytest.raises(HTTPException) as exc:
            await get_dpa(lang="it", current_user=sa)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_org_not_found_returns_404(self):
        from fastapi import HTTPException
        from routers.legal import get_dpa

        with patch(
            "database.organizations_collection.find_one",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_dpa(lang="it", current_user=_admin())
        assert exc.value.status_code == 404


# ─── POST /dpa/acknowledge ───────────────────────────────────────────


class TestAcknowledgeDpa:
    @pytest.mark.asyncio
    async def test_first_acknowledgement_records_audit(self):
        import json
        from routers.legal import acknowledge_dpa

        captured = {}

        async def _fake_record(**kwargs):
            captured.update(kwargs)
            return {"id": "audit-1", **kwargs}

        async def _fake_find_dpa(org_id):
            # No prior acknowledgement
            return None

        class FakeRequest:
            client = type("c", (), {"host": "9.9.9.9"})()
            headers = {"user-agent": "pytest/0"}

            async def json(self):
                return {"locale": "it"}

        with patch(
            "repositories.consent_audit_repository.record_consent",
            new=_fake_record,
        ), patch(
            "repositories.consent_audit_repository.find_latest_for_org_dpa",
            new=_fake_find_dpa,
        ):
            response = await acknowledge_dpa(
                request=FakeRequest(), current_user=_admin(),
            )

        body = json.loads(response.body)
        assert body["status"] == "acknowledged"
        assert body["version_tag"] == "v1.0"
        assert body["locale"] == "it"
        # Audit record args
        assert captured["organization_id"] == "org-1"
        assert captured["user_id"] == "u-1"
        assert captured["source"] == "merchant_dpa_acknowledged"
        assert captured["document_type"] == "merchant_dpa"
        assert captured["ip_address"] == "9.9.9.9"
        assert captured["user_agent"] == "pytest/0"
        # Hash is deterministic 16-hex
        assert len(captured["version_hash"]) == 16

    @pytest.mark.asyncio
    async def test_second_acknowledgement_is_idempotent(self):
        """A second POST returns the ORIGINAL timestamp without creating
        a duplicate audit record."""
        import json
        from routers.legal import acknowledge_dpa

        record_calls = []

        async def _fake_record(**kwargs):
            record_calls.append(kwargs)
            return {"id": "audit-2"}

        existing = {
            "id": "audit-1",
            "user_id": "u-OLD",
            "accepted_at": "2026-05-01T00:00:00+00:00",
            "locale": "en",
            "version_tag": "v1.0",
        }

        async def _fake_find_dpa(org_id):
            return existing

        class FakeRequest:
            client = type("c", (), {"host": "1.1.1.1"})()
            headers = {}

            async def json(self):
                return {}

        with patch(
            "repositories.consent_audit_repository.record_consent",
            new=_fake_record,
        ), patch(
            "repositories.consent_audit_repository.find_latest_for_org_dpa",
            new=_fake_find_dpa,
        ):
            response = await acknowledge_dpa(
                request=FakeRequest(), current_user=_admin(),
            )

        body = json.loads(response.body)
        assert body["status"] == "already_acknowledged"
        assert body["acknowledged_at"] == "2026-05-01T00:00:00+00:00"
        assert body["acknowledged_by_user_id"] == "u-OLD"
        assert body["locale"] == "en"
        # CRITICAL: record_consent was NOT called — no duplicate audit
        assert record_calls == []

    @pytest.mark.asyncio
    async def test_system_admin_blocked(self):
        from fastapi import HTTPException
        from routers.legal import acknowledge_dpa

        class FakeRequest:
            client = None
            headers = {}

            async def json(self):
                return {}

        sa = {"user_id": "sa", "organization_id": None, "role": "system_admin"}
        with pytest.raises(HTTPException) as exc:
            await acknowledge_dpa(request=FakeRequest(), current_user=sa)
        assert exc.value.status_code == 403


# ─── GET /dpa/status ─────────────────────────────────────────────────


class TestGetDpaStatus:
    @pytest.mark.asyncio
    async def test_returns_not_acknowledged_when_no_record(self):
        import json
        from routers.legal import get_dpa_status

        with patch(
            "repositories.consent_audit_repository.find_latest_for_org_dpa",
            new=AsyncMock(return_value=None),
        ):
            response = await get_dpa_status(current_user=_admin())

        body = json.loads(response.body)
        assert body["acknowledged"] is False
        # No identity leak — only the flag
        assert "acknowledged_at" not in body

    @pytest.mark.asyncio
    async def test_returns_full_metadata_when_acknowledged(self):
        import json
        from routers.legal import get_dpa_status

        existing = {
            "user_id": "u-OLD",
            "accepted_at": "2026-05-18T10:00:00+00:00",
            "locale": "it",
            "version_tag": "v1.0",
        }
        with patch(
            "repositories.consent_audit_repository.find_latest_for_org_dpa",
            new=AsyncMock(return_value=existing),
        ):
            response = await get_dpa_status(current_user=_admin())

        body = json.loads(response.body)
        assert body["acknowledged"] is True
        assert body["acknowledged_at"] == "2026-05-18T10:00:00+00:00"
        assert body["acknowledged_by_user_id"] == "u-OLD"
        assert body["locale"] == "it"
        assert body["version_tag"] == "v1.0"

    @pytest.mark.asyncio
    async def test_system_admin_blocked(self):
        from fastapi import HTTPException
        from routers.legal import get_dpa_status

        sa = {"user_id": "sa", "organization_id": None, "role": "system_admin"}
        with pytest.raises(HTTPException) as exc:
            await get_dpa_status(current_user=sa)
        assert exc.value.status_code == 403


# ─── Multi-tenant isolation ──────────────────────────────────────────


class TestMultiTenantIsolation:
    """find_latest_for_org_dpa scopes queries to organization_id —
    org A can NEVER see org B's records."""

    @pytest.mark.asyncio
    async def test_find_latest_query_includes_org_filter(self):
        """Patch the underlying collection.find and assert the query
        passed in contains organization_id."""
        from repositories import consent_audit_repository as car

        captured = {}

        class FakeCursor:
            def __init__(self, items):
                self._items = items

            def sort(self, *a, **kw): return self
            def limit(self, *a, **kw): return self

            async def to_list(self, n):
                return self._items

        def fake_find(query, projection):
            captured["query"] = dict(query)
            return FakeCursor([])

        with patch.object(car.consent_audit_collection, "find", side_effect=fake_find):
            await car.find_latest_for_org_dpa("org-XYZ")

        assert captured["query"]["organization_id"] == "org-XYZ"
        assert captured["query"]["document_type"] == "merchant_dpa"
        assert captured["query"]["source"] == "merchant_dpa_acknowledged"


# ─── Router wiring ───────────────────────────────────────────────────


class TestRouteRegistration:
    """The 3 new admin routes are registered on the FastAPI app."""

    def _paths(self):
        from server import app
        return {
            (r.path, frozenset(getattr(r, "methods") or set()))
            for r in app.routes
            if getattr(r, "methods", None) is not None
        }

    def test_get_dpa_registered(self):
        assert (
            "/api/legal/dpa",
            frozenset({"GET"}),
        ) in self._paths()

    def test_acknowledge_dpa_registered(self):
        assert (
            "/api/legal/dpa/acknowledge",
            frozenset({"POST"}),
        ) in self._paths()

    def test_status_dpa_registered(self):
        assert (
            "/api/legal/dpa/status",
            frozenset({"GET"}),
        ) in self._paths()
