"""Wave GDPR-Admin Phase C — sentinel tests (2026-05-16).

Multilingual legal documents routing infrastructure. Pre-Phase-C
the Privacy Policy and T&C lived as hardcoded JSX in Italian only;
non-Italian users saw the IT version while the UI was in EN/DE/FR,
violating GDPR Art. 13 transparency.

Phase C introduces:
  - 8 Markdown files in backend/legal/ (privacy + terms x 4 locales)
  - core.legal_versions.get_legal_document(doc_type, locale)
  - GET /api/legal/privacy?lang=xx
  - GET /api/legal/terms?lang=xx
  - GET /api/legal/versions
  - Frontend Privacy/Terms pages fetch dynamically with locale picker

Phase D will replace the EN/DE/FR drafts with lawyer-validated
translations (bumping CURRENT_VERSION_TAG to "v1.0").

These tests lock in:
  - All 8 files exist
  - The loader handles every locale combination + invalid input fallback
  - Endpoints return the canonical envelope shape
  - Cache headers are set
  - The router is registered in server.py
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── 8 legal MD files exist ──────────────────────────────────────────────


class TestLegalFilesPresent:
    """Phase C must ship privacy + terms in 4 locales (8 files total)."""

    LEGAL_DIR = BACKEND_DIR / "legal"

    @pytest.mark.parametrize("doc_type", ["privacy", "terms"])
    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_legal_file_exists(self, doc_type, locale):
        path = self.LEGAL_DIR / f"{doc_type}_{locale}.md"
        assert path.exists(), (
            f"Wave GDPR-Admin Phase C regression — missing legal file "
            f"{path}. All 4 locales (it/en/de/fr) x both doc types "
            f"(privacy/terms) must exist."
        )

    @pytest.mark.parametrize("doc_type", ["privacy", "terms"])
    @pytest.mark.parametrize("locale", ["en", "de", "fr"])
    def test_translated_files_have_no_draft_banner_in_v1(self, doc_type, locale):
        """v1.0 launch (2026-05-18): EN/DE/FR are full translations of
        the IT v1.0 binding bundle. They MUST NOT carry any "translation
        in progress" / "draft" banner — this is the first public release
        and user-facing legal pages cannot show provisional language.

        Italian remains the legally binding reference language; this
        disclosure is part of each translated document's own header
        ("Legal reference language: Italian ...").
        """
        path = self.LEGAL_DIR / f"{doc_type}_{locale}.md"
        content = path.read_text(encoding="utf-8")
        forbidden = [
            "TRANSLATION IN PROGRESS",      # EN
            "ÜBERSETZUNG IN ARBEIT",        # DE
            "TRADUCTION EN COURS",          # FR
            "pre-V1.0",                      # any locale
            "draft pending legal review",   # EN draft marker
        ]
        for marker in forbidden:
            assert marker not in content, (
                f"Wave GDPR-Admin v1.0 regression — {doc_type}_{locale}.md "
                f"contains forbidden draft marker {marker!r}. v1.0 is the "
                f"production launch and must not surface provisional "
                f"language to end users."
            )

    def test_italian_file_has_no_translation_banner(self):
        """Sanity — the IT file is the binding reference and must
        NOT carry a 'translation in progress' marker."""
        path = self.LEGAL_DIR / "privacy_it.md"
        content = path.read_text(encoding="utf-8")
        assert "TRANSLATION IN PROGRESS" not in content
        # IT-localized phrase shouldn't be there either
        assert "TRADUZIONE IN CORSO" not in content


# ── Loader: get_legal_document behaviour ────────────────────────────────


class TestLegalDocumentLoader:
    @pytest.mark.parametrize("doc_type", ["privacy", "terms"])
    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_loads_each_locale(self, doc_type, locale):
        from core.legal_versions import get_legal_document
        d = get_legal_document(doc_type, locale)
        assert d["content"], (
            f"Loader returned empty content for {doc_type}/{locale}"
        )
        assert d["locale_actual"] == locale
        assert d["locale_requested"] == locale
        assert d["doc_type"] == doc_type
        assert d["version_tag"]
        assert isinstance(d["is_draft"], bool)
        assert set(d["available_locales"]) == {"it", "en", "de", "fr"}

    def test_invalid_locale_falls_back_to_italian(self):
        from core.legal_versions import get_legal_document
        d = get_legal_document("privacy", "xx-invalid")
        assert d["locale_actual"] == "it"
        assert d["locale_requested"] == "xx-invalid"
        assert d["is_draft"] is False  # IT is binding, not draft

    def test_none_locale_falls_back_to_italian(self):
        from core.legal_versions import get_legal_document
        d = get_legal_document("privacy", None)
        assert d["locale_actual"] == "it"

    def test_italian_is_not_marked_as_draft(self):
        from core.legal_versions import get_legal_document
        d = get_legal_document("privacy", "it")
        assert d["is_draft"] is False

    @pytest.mark.parametrize("locale", ["en", "de", "fr"])
    def test_non_italian_is_not_marked_as_draft_in_v1(self, locale):
        """v1.0 launch (2026-05-18): EN/DE/FR are full translations of
        the IT v1.0 binding bundle. None of the locales is flagged as
        a draft in the public envelope. Italian remains the legally
        binding reference language (declared in each document header).
        """
        from core.legal_versions import get_legal_document
        d = get_legal_document("privacy", locale)
        assert d["is_draft"] is False

    def test_invalid_doc_type_raises(self):
        from core.legal_versions import get_legal_document
        with pytest.raises(ValueError, match="doc_type"):
            get_legal_document("invalid", "it")


# ── Router endpoints ────────────────────────────────────────────────────


class TestLegalRouterEndpoints:
    """The /api/legal/* endpoints return the canonical JSON envelope
    plus cache headers."""

    @pytest.mark.asyncio
    async def test_get_privacy_returns_envelope(self):
        from routers.legal import get_privacy_policy
        response = await get_privacy_policy(lang="it")
        # JSONResponse — peek at content + headers
        import json
        body = json.loads(response.body)
        assert body["doc_type"] == "privacy"
        assert body["locale_actual"] == "it"
        assert body["content"]
        assert body["version_tag"]
        # Cache header set
        cc = response.headers.get("cache-control") or response.headers.get("Cache-Control")
        assert cc is not None
        assert "public" in cc.lower()
        assert "max-age" in cc.lower()

    @pytest.mark.asyncio
    async def test_get_terms_returns_envelope(self):
        from routers.legal import get_terms_of_service
        response = await get_terms_of_service(lang="en")
        import json
        body = json.loads(response.body)
        assert body["doc_type"] == "terms"
        assert body["locale_actual"] == "en"
        # v1.0: EN is a full translation, not a draft
        assert body["is_draft"] is False
        assert body["content"]

    @pytest.mark.asyncio
    async def test_get_versions_returns_metadata(self):
        from routers.legal import get_legal_versions
        response = await get_legal_versions()
        import json
        body = json.loads(response.body)
        assert "version_tag" in body
        assert "version_hash" in body
        assert "version_string" in body
        assert ":" in body["version_string"]
        assert "available_locales" in body
        assert "draft_locales" in body
        assert "binding_locale" in body
        assert body["binding_locale"] == "it"


# ── Router is registered in server.py ───────────────────────────────────


class TestRouterRegistered:
    def test_server_includes_legal_router(self):
        """The router must be wired into the FastAPI app."""
        import inspect
        import server
        src = inspect.getsource(server)
        assert "legal_router" in src or "routers.legal" in src or "from routers import legal" in src
        assert "/api/legal" in src or "legal_router.router" in src


# ── Backward compat: existing /privacy + /terms URLs still work ─────────


class TestBackwardCompat:
    """Pre-Phase-C the /privacy and /terms frontend routes existed.
    Phase C must NOT change those URLs — only add an optional ?lang=
    query parameter."""

    def test_privacy_route_in_frontend_still_relative(self):
        """The signup form must still link to /privacy (with optional
        ?lang=) — not to /api/legal/privacy."""
        signup_path = BACKEND_DIR.parent / "frontend" / "src" / "pages" / "AuthPages.js"
        if not signup_path.exists():
            pytest.skip("Frontend AuthPages.js not present")
        text = signup_path.read_text(encoding="utf-8")
        # Must reference /privacy (frontend page), not /api/legal/privacy directly
        assert "/privacy?lang=" in text or '"/privacy"' in text or "'/privacy'" in text
        assert "/terms?lang=" in text or '"/terms"' in text or "'/terms'" in text


# ── Source sentinels ────────────────────────────────────────────────────


class TestSourceSentinels:
    def test_core_legal_versions_exports_loader(self):
        from core.legal_versions import (
            get_legal_document,
            CURRENT_VERSION_TAG,
            current_version_string,
        )
        assert callable(get_legal_document)
        assert isinstance(CURRENT_VERSION_TAG, str)
        assert callable(current_version_string)

    def test_legal_router_has_three_endpoints(self):
        import inspect
        from routers import legal
        src = inspect.getsource(legal)
        # 3 endpoint definitions
        assert '/privacy' in src
        assert '/terms' in src
        assert '/versions' in src

    def test_router_emits_cache_headers(self):
        import inspect
        from routers import legal
        src = inspect.getsource(legal)
        assert "Cache-Control" in src
        assert "max-age" in src
