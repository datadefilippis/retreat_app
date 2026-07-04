"""Wave GDPR-Commerce Phase CG-2 — sentinel tests for the public
storefront legal endpoints.

Scope:
  - GET /api/storefront/{slug}/legal/privacy
  - GET /api/storefront/{slug}/legal/terms
  - GET /api/storefront/{slug}/legal/metadata

Behaviour matrix verified:
  - Unknown slug → 404
  - Slug found + store not configured  → 200 with content="" and
    status="not_configured" (graceful placeholder for the frontend,
    NOT a 404 — the storefront UX should not break just because the
    merchant hasn't filled in their docs yet)
  - Slug found + draft only            → same as not_configured at
    the public layer (draft is not legally published, must not be
    served to customers)
  - Slug found + published             → 200 with full content + the
    display_locale + version metadata
  - Slug found + stale_draft           → 200 still serving the current
    display-locale content (the merchant has unpublished edits in
    progress; until republished the published version remains in force)
  - Multi-tenant isolation: legal data of store A cannot leak to a
    request for store B's slug
  - Cache headers: max-age=300 for content endpoints, max-age=60 for
    metadata (so re-consent propagation is faster after publish)
  - Router wiring: the 3 routes are registered on the FastAPI app
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


# Test fixtures: representative store documents in each lifecycle state.


def _store_not_configured() -> dict:
    return {
        "id": "store-1",
        "organization_id": "org-1",
        "slug": "acme",
        "name": "Acme Store",
        "contact_email": "merchant@acme.test",
        "is_published": True,
        "is_active": True,
        "visibility": "public",
        # No merchant_legal_* fields → not_configured
    }


def _store_draft_only() -> dict:
    """Has content + display locale chosen, but never published."""
    return {
        **_store_not_configured(),
        "merchant_legal_display_locale": "it",
        "merchant_privacy_content_it": "# Acme Privacy IT draft",
        "merchant_terms_content_it": "# Acme Terms IT draft",
        "merchant_legal_published_at": None,
    }


def _store_published() -> dict:
    from services.merchant_legal_versioning import compute_legal_hash
    s = {
        **_store_draft_only(),
        "merchant_legal_published_at": "2026-05-18T10:00:00+00:00",
        "merchant_legal_last_edited_at": "2026-05-18T09:00:00+00:00",
        "merchant_legal_version_tag": "v1.0",
    }
    s["merchant_legal_version_hash"] = compute_legal_hash(s)
    return s


def _store_stale_draft() -> dict:
    """Published once, then edited again — display content reflects the
    new (unpublished) text but version_hash still points at the old
    published bundle."""
    pub = _store_published()
    return {
        **pub,
        "merchant_privacy_content_it": "# Acme Privacy IT (edited but not republished)",
        "merchant_legal_last_edited_at": "2026-05-18T12:00:00+00:00",
    }


def _patch_store_resolver(store_or_none):
    """Patch the helper that reads the store document by slug.

    Returns a context manager. ``store_or_none`` may be a dict (found)
    or None (slug not found / not public).
    """
    return patch(
        "routers.legal._resolve_store_for_legal",
        new=AsyncMock(return_value=store_or_none),
    )


# ── /api/storefront/{slug}/legal/privacy + /terms ───────────────────────


class TestStorefrontDocEndpoints:
    """Content endpoints behave consistently across statuses."""

    @pytest.mark.asyncio
    async def test_unknown_slug_returns_404(self):
        from fastapi import HTTPException
        from routers.legal import get_storefront_privacy, get_storefront_terms

        with _patch_store_resolver(None):
            with pytest.raises(HTTPException) as exc:
                await get_storefront_privacy("nope")
            assert exc.value.status_code == 404
            with pytest.raises(HTTPException) as exc:
                await get_storefront_terms("nope")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.parametrize("doc_type", ["privacy", "terms"])
    async def test_not_configured_serves_autogen_fallback(self, doc_type):
        """Track E Step 7.5 — Auto-fallback contract.

        Pre-fix: status=not_configured → content="" + UI placeholder
        giallo. Customer NON poteva consultare alcuna informativa GDPR
        al momento del consenso (Art. 13 GDPR compliance gap).

        Post-fix: rendiamo SEMPRE il template standard pre-fillato sui
        dati anagrafici store cosi' il customer ha un'informativa
        consultabile. Status rimane "not_configured" come segnale per
        il merchant admin, ma is_autogenerated=true notifica al
        frontend di renderizzare il banner azzurro informativo + il
        contenuto sotto.
        """
        import json
        from routers.legal import get_storefront_privacy, get_storefront_terms

        endpoint = get_storefront_privacy if doc_type == "privacy" else get_storefront_terms
        with _patch_store_resolver(_store_not_configured()):
            response = await endpoint("acme")

        body = json.loads(response.body)
        # Content NOT empty: auto-generato dal template per la locale "it"
        assert body["content"], (
            "Auto-fallback non renderizzato — customer vedrebbe pagina "
            "vuota e perderebbe accesso a informativa GDPR (Art. 13)."
        )
        # Il template inizia con un title markdown "# ..."
        assert body["content"].startswith("#"), (
            "Content auto-generato non e' markdown valido."
        )
        # Status canonical resta "not_configured" — admin notification
        assert body["status"] == "not_configured"
        # NEW field: bandiera UX per il banner azzurro
        assert body["is_autogenerated"] is True, (
            "is_autogenerated deve essere true quando il content viene "
            "dal template fallback (frontend mostra banner)."
        )
        # display_locale resolved a "it" (default storefront_languages)
        assert body["display_locale"] == "it"
        # No version (mai pubblicato dal merchant)
        assert body["version_tag"] is None
        assert body["version_string"] is None
        assert body["doc_type"] == doc_type
        assert body["merchant_email"] == "merchant@acme.test"
        assert body["store_name"] == "Acme Store"

    @pytest.mark.asyncio
    async def test_draft_only_serves_autogen_fallback(self):
        """Track E Step 7.5 — anche per status="draft" usiamo l'auto-fallback.

        Pre-fix: draft → content="" (no leak della draft mid-edit). Lo
        leakage rimane prevented perche' NON serviamo il draft content
        del merchant, ma rendiamo SEPARATAMENTE il template standard
        baseline. Customer vede un'informativa GDPR-compliant generica
        (NON il draft in editing) → no privacy leak, ma anche no UX
        rotto.
        """
        import json
        from routers.legal import get_storefront_privacy

        with _patch_store_resolver(_store_draft_only()):
            response = await get_storefront_privacy("acme")

        body = json.loads(response.body)
        assert body["status"] == "draft"
        # Content NON e' il draft del merchant — e' il template auto-gen
        assert body["content"], "Auto-fallback mancante anche su draft."
        assert body["is_autogenerated"] is True
        # Anti-leak: il content NON deve essere il draft del merchant
        # (il fixture _store_draft_only mette "Acme Privacy IT draft"
        # come marker — verifichiamo che NON appaia: il response deve
        # contenere SOLO il template auto-gen, mai il draft del merchant).
        assert "draft" not in body["content"].lower() or "bozza" in body["content"].lower(), (
            "BUG SICUREZZA: possibile leak del draft mid-edit. "
            "Il template auto-gen italiano usa 'bozza' (it) — se appare "
            "la parola 'draft' (en) potrebbe essere leak del field merchant."
        )
        assert "Acme Privacy IT draft" not in body["content"], (
            "BUG SICUREZZA: leak ESATTO del draft mid-edit nel public response."
        )
        # version_tag still null perche' mai pubblicato
        assert body["version_tag"] is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("doc_type", ["privacy", "terms"])
    async def test_published_serves_full_content(self, doc_type):
        import json
        from routers.legal import get_storefront_privacy, get_storefront_terms

        endpoint = get_storefront_privacy if doc_type == "privacy" else get_storefront_terms
        with _patch_store_resolver(_store_published()):
            response = await endpoint("acme")

        body = json.loads(response.body)
        assert body["status"] == "published"
        # Content is the IT field of the appropriate doc_type
        assert body["content"].startswith(f"# Acme {doc_type.title()} IT")
        assert body["display_locale"] == "it"
        assert body["version_tag"] == "v1.0"
        assert body["version_string"].startswith("v1.0:")
        assert body["published_at"] == "2026-05-18T10:00:00+00:00"

    @pytest.mark.asyncio
    async def test_stale_draft_still_returns_published_status_or_stale(self):
        """When the merchant has edited after a publish, we serve the
        new content (CG-1 doesn't snapshot at publish-time). Status
        flips to 'stale_draft' as a nudge for the admin UI."""
        import json
        from routers.legal import get_storefront_privacy

        with _patch_store_resolver(_store_stale_draft()):
            response = await get_storefront_privacy("acme")

        body = json.loads(response.body)
        assert body["status"] == "stale_draft"
        # Content is the latest (edited) version, not empty
        assert "edited but not republished" in body["content"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("doc_type", ["privacy", "terms"])
    async def test_cache_header_set_for_content_endpoints(self, doc_type):
        """CG-3-Polish-4: 30s max-age + must-revalidate + ETag. The
        ETag mirrors the version_string so a publish bump naturally
        invalidates client caches via the conditional-request flow."""
        from routers.legal import get_storefront_privacy, get_storefront_terms

        endpoint = get_storefront_privacy if doc_type == "privacy" else get_storefront_terms
        with _patch_store_resolver(_store_published()):
            response = await endpoint("acme")

        cc = (response.headers.get("cache-control")
              or response.headers.get("Cache-Control"))
        assert cc is not None
        assert "public" in cc.lower()
        # Shorter cache so admin testing perceives publishes quickly
        assert "max-age=30" in cc.lower()
        assert "must-revalidate" in cc.lower()
        # ETag derived from version_string for proper cache invalidation
        etag = response.headers.get("etag") or response.headers.get("ETag")
        assert etag is not None
        assert etag.startswith('"') and etag.endswith('"')

    @pytest.mark.asyncio
    @pytest.mark.parametrize("doc_type", ["privacy", "terms"])
    async def test_etag_changes_when_version_bumps(self, doc_type):
        """CG-3-Polish-4 cornerstone: when the merchant publishes a new
        version (different version_string), the ETag changes — proving
        the browser cache will be invalidated on the next request."""
        from routers.legal import get_storefront_privacy, get_storefront_terms

        endpoint = get_storefront_privacy if doc_type == "privacy" else get_storefront_terms

        # First publish state
        store_v1 = _store_published()
        with _patch_store_resolver(store_v1):
            response_v1 = await endpoint("acme")
        etag_v1 = response_v1.headers.get("etag") or response_v1.headers.get("ETag")

        # Bumped to v1.1 (different version_string)
        store_v2 = {
            **store_v1,
            "merchant_legal_version_tag": "v1.1",
            "merchant_legal_version_hash": "differenthashv2",
        }
        with _patch_store_resolver(store_v2):
            response_v2 = await endpoint("acme")
        etag_v2 = response_v2.headers.get("etag") or response_v2.headers.get("ETag")

        # Different ETag → browser will refetch
        assert etag_v1 != etag_v2


# ── /api/storefront/{slug}/legal/metadata ───────────────────────────────


class TestStorefrontLegalMetadata:
    """Metadata endpoint is the canonical signal for re-consent."""

    @pytest.mark.asyncio
    async def test_unknown_slug_returns_404(self):
        from fastapi import HTTPException
        from routers.legal import get_storefront_legal_metadata

        with _patch_store_resolver(None):
            with pytest.raises(HTTPException) as exc:
                await get_storefront_legal_metadata("nope")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_metadata_for_published_store(self):
        import json
        from routers.legal import get_storefront_legal_metadata

        with _patch_store_resolver(_store_published()):
            response = await get_storefront_legal_metadata("acme")

        body = json.loads(response.body)
        assert body["status"] == "published"
        assert body["display_locale"] == "it"
        assert body["version_tag"] == "v1.0"
        assert body["version_string"].startswith("v1.0:")
        assert body["published_at"] == "2026-05-18T10:00:00+00:00"
        assert body["merchant_email"] == "merchant@acme.test"
        assert body["store_name"] == "Acme Store"

    @pytest.mark.asyncio
    async def test_metadata_for_not_configured_store(self):
        import json
        from routers.legal import get_storefront_legal_metadata

        with _patch_store_resolver(_store_not_configured()):
            response = await get_storefront_legal_metadata("acme")

        body = json.loads(response.body)
        assert body["status"] == "not_configured"
        assert body["version_tag"] is None

    @pytest.mark.asyncio
    async def test_metadata_cache_header_is_shorter_than_content(self):
        """The frontend polls metadata to detect a published bump for
        the re-consent modal. Short cache so the modal appears within
        a minute of publish, not five."""
        from routers.legal import get_storefront_legal_metadata

        with _patch_store_resolver(_store_published()):
            response = await get_storefront_legal_metadata("acme")

        cc = (response.headers.get("cache-control")
              or response.headers.get("Cache-Control"))
        assert "max-age=60" in cc.lower()


# ── Multi-tenant isolation ──────────────────────────────────────────────


class TestEffectiveDisplayLocaleRegression:
    """Wave CG-3-Polish-3 regression — bug reported by user.

    Scenario: after CG-3-Polish-2 shipped, the auto-cleanup logic
    unset the legacy ``merchant_legal_display_locale`` field on every
    admin write. The public endpoints (``_public_doc_envelope`` and
    ``get_storefront_legal_metadata``) were still reading the raw
    legacy field instead of the ``get_effective_display_locale``
    helper, so they saw ``display=None`` and served empty content
    even though the store WAS published.

    These tests pin the contract: the public envelope must serve the
    correct content via the effective-locale helper regardless of
    whether the legacy field is present.
    """

    def _store_published_no_legacy_field(self) -> dict:
        """Mirror of _store_published() but WITHOUT the legacy
        merchant_legal_display_locale field — the post-cleanup state."""
        from services.merchant_legal_versioning import compute_legal_hash
        s = {
            "id": "store-1",
            "organization_id": "org-1",
            "slug": "acme",
            "name": "Acme Store",
            "contact_email": "merchant@acme.test",
            "is_published": True,
            "is_active": True,
            "visibility": "public",
            "storefront_languages": ["it"],  # primary = it
            # NOTE: merchant_legal_display_locale INTENTIONALLY ABSENT
            "merchant_privacy_content_it": "# Acme Privacy IT v1",
            "merchant_terms_content_it": "# Acme Terms IT v1",
            "merchant_legal_published_at": "2026-05-18T10:00:00+00:00",
            "merchant_legal_last_edited_at": "2026-05-18T09:00:00+00:00",
            "merchant_legal_version_tag": "v1.0",
        }
        s["merchant_legal_version_hash"] = compute_legal_hash(s)
        return s

    @pytest.mark.asyncio
    async def test_public_privacy_serves_content_after_legacy_cleanup(self):
        """The exact bug reported: user clicks save/publish → legacy
        field gets cleaned up → public endpoint should STILL serve
        the IT content because storefront_languages[0]="it"."""
        import json
        from routers.legal import get_storefront_privacy

        store = self._store_published_no_legacy_field()
        with _patch_store_resolver(store):
            response = await get_storefront_privacy("acme")

        body = json.loads(response.body)
        # Content materialises from storefront_languages[0] derivation
        assert body["content"] == "# Acme Privacy IT v1"
        assert body["display_locale"] == "it"
        assert body["status"] == "published"

    @pytest.mark.asyncio
    async def test_metadata_returns_effective_locale_after_cleanup(self):
        import json
        from routers.legal import get_storefront_legal_metadata

        store = self._store_published_no_legacy_field()
        with _patch_store_resolver(store):
            response = await get_storefront_legal_metadata("acme")

        body = json.loads(response.body)
        # The /metadata endpoint surfaces the effective locale so the
        # customer-portal re-consent modal can render the right CTA.
        assert body["display_locale"] == "it"
        assert body["status"] == "published"


class TestMultiTenantIsolation:
    """The resolver MUST scope by slug. We patch the resolver to a
    specific store and verify the endpoint only ever returns that
    store's fields — no leakage from a hypothetical other store."""

    @pytest.mark.asyncio
    async def test_endpoint_returns_only_resolved_store_data(self):
        import json
        from routers.legal import get_storefront_privacy

        store_a = _store_published()
        store_b = {
            **_store_published(),
            "id": "store-b",
            "organization_id": "org-b",
            "slug": "rival",
            "name": "Rival Store",
            "contact_email": "rival@example.test",
            "merchant_privacy_content_it": "# RIVAL secret content",
        }

        # The resolver receives slug=acme, returns store_a. Nothing in
        # store_b should ever appear in the response.
        with _patch_store_resolver(store_a):
            response = await get_storefront_privacy("acme")

        body = json.loads(response.body)
        assert body["store_name"] == "Acme Store"
        assert body["merchant_email"] == "merchant@acme.test"
        assert "RIVAL" not in body["content"]
        assert "rival@example.test" not in body["merchant_email"]


# ── Router wiring ───────────────────────────────────────────────────────


class TestRouteRegistration:
    """The 3 new routes must be registered on the FastAPI app under /api."""

    def _paths(self):
        from server import app
        return {
            (r.path, frozenset(getattr(r, "methods") or set()))
            for r in app.routes
            if getattr(r, "methods", None) is not None
        }

    def test_privacy_route_registered(self):
        assert (
            "/api/legal/storefront/{slug}/privacy",
            frozenset({"GET"}),
        ) in self._paths()

    def test_terms_route_registered(self):
        assert (
            "/api/legal/storefront/{slug}/terms",
            frozenset({"GET"}),
        ) in self._paths()

    def test_metadata_route_registered(self):
        assert (
            "/api/legal/storefront/{slug}/metadata",
            frozenset({"GET"}),
        ) in self._paths()
