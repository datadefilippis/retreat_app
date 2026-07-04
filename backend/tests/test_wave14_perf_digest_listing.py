"""Wave 14 perf — Digest listing optimization (2026-05-16).

The user reported: clicking the "Digest" tab inside the AI page takes
several seconds to load.

Root cause forensics:
  - ``digest_repository.find_by_org`` projection was ``{"_id": 0}``,
    i.e. INCLUDED every field in the document.
  - Each digest doc has a ``pdf_b64`` field carrying the base64-encoded
    rendered PDF, ~300 KB per doc (a 4-page ReportLab PDF with
    matplotlib charts).
  - ``GET /api/digests`` with limit=10 was transferring ~3 MB of base64
    text to the frontend on every Digest tab open.
  - The frontend NEVER renders the PDF in the list view — it only
    fetches the bytes via the dedicated ``GET /api/digests/{id}/pdf``
    endpoint when the user clicks "Scarica PDF".

The fix is a textbook projection optimization:
  - ``find_by_org`` and ``find_latest`` now exclude ``pdf_b64`` from
    the projection by default. New ``include_pdf`` kwarg (default
    False) lets callers opt in if they truly need the embedded bytes.
  - The two GET endpoints add ``Cache-Control: private, max-age=60``
    so a rapid re-click on the Digest tab is served from the browser
    cache instead of round-tripping to Mongo.

This file is the regression sentinel that locks in both behaviours.
"""

import os
import sys
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


# ── Repository projection ─────────────────────────────────────────────────


class TestProjectionExcludesPdfByDefault:
    """The repository must NOT return pdf_b64 unless explicitly asked."""

    @pytest.mark.asyncio
    async def test_find_by_org_excludes_pdf_b64_by_default(self):
        from repositories import digest_repository as dr

        # Capture the projection argument passed to find()
        captured = {}

        class FakeCursor:
            def __init__(self): pass
            def sort(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            async def to_list(self, n): return []

        def fake_find(query, projection=None):
            captured["query"] = query
            captured["projection"] = projection
            return FakeCursor()

        with patch.object(dr, "digests_collection", type("FC", (), {"find": staticmethod(fake_find)})):
            await dr.find_by_org("org-123", limit=5)

        proj = captured["projection"]
        assert proj is not None
        assert proj.get("pdf_b64") == 0, (
            "Wave 14 perf regression — find_by_org projection must "
            "exclude pdf_b64 by default. Including it transfers ~300 KB "
            "of base64 per digest in the list response."
        )

    @pytest.mark.asyncio
    async def test_find_by_org_include_pdf_true_keeps_pdf(self):
        from repositories import digest_repository as dr

        captured = {}

        class FakeCursor:
            def sort(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            async def to_list(self, n): return []

        def fake_find(query, projection=None):
            captured["projection"] = projection
            return FakeCursor()

        with patch.object(dr, "digests_collection", type("FC", (), {"find": staticmethod(fake_find)})):
            await dr.find_by_org("org-123", limit=5, include_pdf=True)

        proj = captured["projection"]
        # When include_pdf=True the pdf_b64 key must NOT be set to 0
        # (otherwise it's still excluded)
        assert "pdf_b64" not in proj or proj.get("pdf_b64") != 0, (
            "Wave 14 perf — include_pdf=True must return the bytes."
        )

    @pytest.mark.asyncio
    async def test_find_latest_excludes_pdf_b64_by_default(self):
        from repositories import digest_repository as dr

        captured = {}

        class FakeCursor:
            def sort(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            async def to_list(self, n): return []

        def fake_find(query, projection=None):
            captured["projection"] = projection
            return FakeCursor()

        with patch.object(dr, "digests_collection", type("FC", (), {"find": staticmethod(fake_find)})):
            await dr.find_latest("org-123", digest_type="weekly")

        proj = captured["projection"]
        assert proj.get("pdf_b64") == 0


# ── Router Cache-Control headers ──────────────────────────────────────────


class TestCacheControlHeaders:
    """Both list and latest endpoints must carry a Cache-Control header
    so rapid re-clicks on the Digest tab are served from browser cache."""

    @pytest.mark.asyncio
    async def test_list_digests_emits_cache_control(self):
        from routers import digests as digests_router

        async def _fake_find(org_id, digest_type=None, limit=10, **kw):
            return [
                {"id": "d1", "digest_type": "weekly", "content": "summary 1"},
                {"id": "d2", "digest_type": "weekly", "content": "summary 2"},
            ]

        fake_user = {
            "organization_id": "org-test",
            "user_id": "u1",
            "email": "test@example.com",
            "email_verified": True,
        }

        from repositories import digest_repository
        with patch.object(digest_repository, "find_by_org", _fake_find):
            response = await digests_router.list_digests(
                request=None,
                digest_type=None,
                limit=10,
                current_user=fake_user,
            )

        # response is a JSONResponse
        cc = response.headers.get("cache-control") or response.headers.get("Cache-Control")
        assert cc is not None, (
            "Wave 14 perf regression — list_digests must emit "
            "Cache-Control header for browser caching."
        )
        assert "private" in cc.lower(), (
            "Cache-Control must be 'private' — digests are user-scoped."
        )
        assert "max-age" in cc.lower()

    @pytest.mark.asyncio
    async def test_latest_digest_emits_cache_control(self):
        from routers import digests as digests_router

        async def _fake_find_latest(org_id, digest_type="weekly", **kw):
            return {"id": "d1", "digest_type": "weekly", "content": "summary"}

        fake_user = {
            "organization_id": "org-test",
            "user_id": "u1",
            "email": "test@example.com",
            "email_verified": True,
        }

        from repositories import digest_repository
        with patch.object(digest_repository, "find_latest", _fake_find_latest):
            response = await digests_router.get_latest_digest(
                request=None,
                digest_type="weekly",
                current_user=fake_user,
            )

        cc = response.headers.get("cache-control") or response.headers.get("Cache-Control")
        assert cc is not None
        assert "private" in cc.lower()


# ── Payload size sanity ───────────────────────────────────────────────────


class TestPayloadSizeReduction:
    """Verify the projection actually reduces payload size by checking
    that pdf_b64 is NOT in the returned document."""

    @pytest.mark.asyncio
    async def test_pdf_b64_not_in_list_response(self):
        from repositories import digest_repository as dr

        # Fake the cursor to return a doc with pdf_b64 EXISTING in the
        # source data — but the projection should have stripped it.
        # We simulate Mongo's projection behaviour: if projection excludes
        # pdf_b64, the field is absent from the result.
        class FakeCursor:
            def __init__(self, exclude_pdf):
                self.exclude_pdf = exclude_pdf
            def sort(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            async def to_list(self, n):
                doc = {
                    "id": "d1", "digest_type": "weekly",
                    "content": "summary", "kpis_summary": {"net": 100},
                }
                if not self.exclude_pdf:
                    doc["pdf_b64"] = "A" * 100000  # 100 KB of base64
                return [doc]

        def fake_find(query, projection):
            exclude = projection.get("pdf_b64") == 0
            return FakeCursor(exclude_pdf=exclude)

        fake_coll = type("FC", (), {"find": staticmethod(fake_find)})
        with patch.object(dr, "digests_collection", fake_coll):
            docs_lean = await dr.find_by_org("org-123", limit=5)
            docs_heavy = await dr.find_by_org("org-123", limit=5, include_pdf=True)

        assert "pdf_b64" not in docs_lean[0], (
            "Wave 14 perf — default list response must NOT contain pdf_b64."
        )
        assert "pdf_b64" in docs_heavy[0], (
            "Wave 14 perf — include_pdf=True must restore pdf_b64."
        )


# ── Source-code sentinel ─────────────────────────────────────────────────


class TestSourceSentinels:
    def test_router_imports_jsonresponse(self):
        import inspect
        from routers import digests
        src = inspect.getsource(digests)
        # The Cache-Control wiring requires JSONResponse
        assert "JSONResponse" in src
        assert "Cache-Control" in src

    def test_repository_signature_has_include_pdf_kwarg(self):
        import inspect
        from repositories.digest_repository import find_by_org, find_latest

        sig_by_org = inspect.signature(find_by_org)
        assert "include_pdf" in sig_by_org.parameters
        assert sig_by_org.parameters["include_pdf"].default is False

        sig_latest = inspect.signature(find_latest)
        assert "include_pdf" in sig_latest.parameters
        assert sig_latest.parameters["include_pdf"].default is False
