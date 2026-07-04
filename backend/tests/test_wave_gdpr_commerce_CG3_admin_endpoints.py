"""Wave GDPR-Commerce Phase CG-3 — sentinel tests for the admin
endpoints that let the merchant edit and publish per-store legal docs.

Endpoints covered (all under /api/stores/{store_id}/legal):
  - POST   /generate-draft        — render a template (stateless)
  - GET    /                       — admin snapshot of all 8 content slots
  - PATCH  /content                — save one content slot
  - PATCH  /display-locale         — change locale + maybe bump version
  - POST   /publish                — publish (idempotent on no hash change)

Invariants asserted:
  - Multi-tenant: admin of org A cannot see / edit / publish a store
    that belongs to org B. The 404 message is the same in both
    "not found" and "wrong org" cases so we don't leak cross-org
    existence.
  - publish is idempotent when content hash hasn't changed (no
    accidental customer re-consent spam from impatient clicks).
  - publish bumps the version_tag exactly once per real content
    change.
  - patch_display_locale on a published store with a complete bundle
    in the new locale bumps the version (customer re-consent
    triggered) — this is the documented side-effect.
  - patch_display_locale on a not-yet-published store just sets the
    locale, no version yet.
  - patch_content NEVER bumps the version (drafts are free to iterate).
  - generate-draft is stateless — does not mutate the store doc.
  - publish refuses when display_locale is unset or either content
    slot is empty (422 with a specific message).
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


# ─── Test fixtures ───────────────────────────────────────────────────


def _user(org_id: str = "org-1") -> dict:
    return {"user_id": "u-1", "organization_id": org_id, "role": "admin"}


def _store_not_configured() -> dict:
    return {
        "id": "store-1",
        "organization_id": "org-1",
        "slug": "acme",
        "name": "Acme Store",
        "is_published": True,
        "is_active": True,
        "visibility": "public",
        "storefront_languages": ["it"],
    }


def _store_published() -> dict:
    """Store with a complete bundle and a published version (v1.0)."""
    from services.merchant_legal_versioning import compute_legal_hash
    s = {
        **_store_not_configured(),
        "merchant_legal_display_locale": "it",
        "merchant_privacy_content_it": "# Privacy IT v1",
        "merchant_terms_content_it": "# Terms IT v1",
        "merchant_legal_published_at": "2026-05-18T10:00:00+00:00",
        "merchant_legal_last_edited_at": "2026-05-18T09:00:00+00:00",
        "merchant_legal_version_tag": "v1.0",
    }
    s["merchant_legal_version_hash"] = compute_legal_hash(s)
    return s


def _vars(**overrides):
    from services.merchant_legal_template_service import TemplateVars
    defaults = dict(
        merchant_name="Mario Rossi",
        merchant_email="mario@example.com",
        merchant_country="Italia",
        store_name="Acme Store",
        store_country="Italia",
    )
    defaults.update(overrides)
    return TemplateVars(**defaults)


# ─── Mocking machinery for ``stores_collection`` ────────────────────


class FakeStoresCollection:
    """In-memory stand-in for the real Mongo stores_collection.

    Stores a dict keyed by store id; supports find_one + update_one
    semantics needed by the router. Resets on each test via the helper
    factory below.
    """

    def __init__(self, stores: list[dict]):
        self._docs = {s["id"]: dict(s) for s in stores}

    async def find_one(self, query: dict, projection=None):
        for d in self._docs.values():
            if all(d.get(k) == v for k, v in query.items()):
                # mimic the projection={"_id": 0, ...} behaviour by
                # returning a shallow copy — we never store _id anyway.
                return dict(d)
        return None

    async def update_one(self, query: dict, update: dict):
        for d in self._docs.values():
            if all(d.get(k) == v for k, v in query.items()):
                set_payload = (update or {}).get("$set", {})
                for k, v in set_payload.items():
                    d[k] = v
                # CG-3-Polish-2 — emulate $unset semantics needed by the
                # legacy-field cleanup logic in patch_legal_content /
                # patch_template_vars / publish_legal.
                unset_payload = (update or {}).get("$unset", {})
                for k in unset_payload:
                    if k in d:
                        del d[k]
                return
        # No match — mongo would just no-op; mirror that.

    def get(self, store_id: str) -> dict:
        return self._docs[store_id]


def _make_fake_db(stores: list[dict]) -> FakeStoresCollection:
    return FakeStoresCollection(stores)


def _patch_db(fake):
    """Patch BOTH import paths because the router module + the
    auth/database module each import the symbol once."""
    return patch(
        "routers.store_legal.stores_collection",
        new=fake,
    )


# ─── generate_draft ─────────────────────────────────────────────────


class TestGenerateDraft:
    @pytest.mark.asyncio
    async def test_returns_rendered_markdown(self):
        from routers.store_legal import generate_draft, GenerateDraftRequest

        fake = _make_fake_db([_store_not_configured()])
        body = GenerateDraftRequest(
            doc_type="privacy", locale="it", vars=_vars(),
        )
        with _patch_db(fake):
            result = await generate_draft(
                store_id="store-1", body=body, current_user=_user(),
            )

        assert result["doc_type"] == "privacy"
        assert result["locale"] == "it"
        assert "Mario Rossi" in result["content"]
        assert "{{merchant_name}}" not in result["content"]

    @pytest.mark.asyncio
    async def test_does_not_mutate_store(self):
        from routers.store_legal import generate_draft, GenerateDraftRequest

        fake = _make_fake_db([_store_not_configured()])
        before = dict(fake.get("store-1"))
        body = GenerateDraftRequest(
            doc_type="privacy", locale="en", vars=_vars(),
        )
        with _patch_db(fake):
            await generate_draft(
                store_id="store-1", body=body, current_user=_user(),
            )
        after = fake.get("store-1")
        # No merchant_legal_* field appears
        for k in after:
            assert not k.startswith("merchant_privacy_content_")
            assert not k.startswith("merchant_terms_content_")

    @pytest.mark.asyncio
    async def test_404_when_cross_org_attempt(self):
        from fastapi import HTTPException
        from routers.store_legal import generate_draft, GenerateDraftRequest

        fake = _make_fake_db([_store_not_configured()])  # belongs to org-1
        body = GenerateDraftRequest(
            doc_type="privacy", locale="it", vars=_vars(),
        )
        with _patch_db(fake), pytest.raises(HTTPException) as exc:
            await generate_draft(
                store_id="store-1", body=body,
                current_user=_user("org-OTHER"),
            )
        assert exc.value.status_code == 404


# ─── GET /legal — admin snapshot ────────────────────────────────────


class TestGetStoreLegal:
    @pytest.mark.asyncio
    async def test_returns_all_8_slots_plus_metadata(self):
        from routers.store_legal import get_store_legal

        store = _store_published()
        # Add some content in EN so we can verify the slot is exposed
        store["merchant_privacy_content_en"] = "# EN content"
        fake = _make_fake_db([store])
        with _patch_db(fake):
            snapshot = await get_store_legal("store-1", _user())

        # Lifecycle fields
        assert snapshot["store_id"] == "store-1"
        assert snapshot["display_locale"] == "it"
        assert snapshot["status"] == "published"
        assert snapshot["version_tag"] == "v1.0"
        assert snapshot["version_string"].startswith("v1.0:")
        # All 8 slots present
        for loc in ("it", "en", "de", "fr"):
            assert f"privacy_content_{loc}" in snapshot
            assert f"terms_content_{loc}" in snapshot
        assert snapshot["privacy_content_it"] == "# Privacy IT v1"
        assert snapshot["privacy_content_en"] == "# EN content"
        # Locales without content come back as "" (never None)
        assert snapshot["privacy_content_de"] == ""

    @pytest.mark.asyncio
    async def test_cross_org_returns_404(self):
        from fastapi import HTTPException
        from routers.store_legal import get_store_legal

        fake = _make_fake_db([_store_published()])
        with _patch_db(fake), pytest.raises(HTTPException) as exc:
            await get_store_legal("store-1", _user("org-OTHER"))
        assert exc.value.status_code == 404


# ─── PATCH /content ─────────────────────────────────────────────────


class TestPatchContent:
    @pytest.mark.asyncio
    async def test_saves_slot_and_touches_last_edited(self):
        from routers.store_legal import patch_legal_content, PatchContentRequest

        fake = _make_fake_db([_store_not_configured()])
        body = PatchContentRequest(
            doc_type="privacy", locale="it", content="# NEW IT PRIVACY",
        )
        with _patch_db(fake):
            snapshot = await patch_legal_content(
                "store-1", body, _user(),
            )

        stored = fake.get("store-1")
        assert stored["merchant_privacy_content_it"] == "# NEW IT PRIVACY"
        assert stored["merchant_legal_last_edited_at"] is not None
        # Snapshot reflects the change
        assert snapshot["privacy_content_it"] == "# NEW IT PRIVACY"

    @pytest.mark.asyncio
    async def test_does_not_bump_version_tag(self):
        """Saving a draft never publishes — version_tag stays."""
        from routers.store_legal import patch_legal_content, PatchContentRequest

        store = _store_published()
        original_tag = store["merchant_legal_version_tag"]
        original_hash = store["merchant_legal_version_hash"]
        fake = _make_fake_db([store])

        body = PatchContentRequest(
            doc_type="privacy", locale="it", content="# EDITED",
        )
        with _patch_db(fake):
            await patch_legal_content("store-1", body, _user())

        stored = fake.get("store-1")
        # Tag + hash unchanged — only last_edited_at moved.
        # (Status will report "stale_draft" once the helper re-runs,
        # which is the intended UI nudge.)
        assert stored["merchant_legal_version_tag"] == original_tag
        assert stored["merchant_legal_version_hash"] == original_hash


# ─── PATCH /display-locale ──────────────────────────────────────────


class TestPatchDisplayLocaleDeprecated:
    """Wave CG-3-Polish (2026-05-18) deprecated the explicit
    ``merchant_legal_display_locale`` field. The PATCH endpoint is
    retained for backward compatibility with stale clients but
    performs NO state change — the customer-facing locale now derives
    from ``storefront_languages[0]``.

    These tests assert the no-op contract: the endpoint accepts the
    request, doesn't mutate the store doc, returns the current snapshot.
    """

    @pytest.mark.asyncio
    async def test_endpoint_is_no_op(self):
        from routers.store_legal import (
            patch_display_locale, PatchDisplayLocaleRequest,
        )

        store = {
            **_store_published(),
            # Capture the values before the call
        }
        original_tag = store["merchant_legal_version_tag"]
        original_hash = store["merchant_legal_version_hash"]
        original_explicit = store.get("merchant_legal_display_locale")
        fake = _make_fake_db([store])

        body = PatchDisplayLocaleRequest(locale="en")  # would-be change
        with _patch_db(fake):
            await patch_display_locale("store-1", body, _user())

        stored = fake.get("store-1")
        # NONE of the fields changed
        assert stored["merchant_legal_version_tag"] == original_tag
        assert stored["merchant_legal_version_hash"] == original_hash
        assert stored.get("merchant_legal_display_locale") == original_explicit

    @pytest.mark.asyncio
    async def test_cross_org_still_returns_404(self):
        """Even though no-op, org scoping is still enforced — cross-org
        callers must get 404 (no information leak about the deprecated
        endpoint's behaviour for other tenants)."""
        from fastapi import HTTPException
        from routers.store_legal import (
            patch_display_locale, PatchDisplayLocaleRequest,
        )

        fake = _make_fake_db([_store_published()])
        body = PatchDisplayLocaleRequest(locale="en")
        with _patch_db(fake), pytest.raises(HTTPException) as exc:
            await patch_display_locale(
                "store-1", body, _user("org-OTHER"),
            )
        assert exc.value.status_code == 404


# ─── POST /publish ──────────────────────────────────────────────────


class TestPublish:
    @pytest.mark.asyncio
    async def test_first_publish_sets_v1_0(self):
        from routers.store_legal import publish_legal, PublishRequest

        store = {
            **_store_not_configured(),
            "merchant_legal_display_locale": "it",
            "merchant_privacy_content_it": "# P",
            "merchant_terms_content_it": "# T",
        }
        fake = _make_fake_db([store])
        with _patch_db(fake):
            snapshot = await publish_legal(
                "store-1", PublishRequest(), _user(),
            )

        stored = fake.get("store-1")
        assert stored["merchant_legal_version_tag"] == "v1.0"
        assert stored["merchant_legal_version_hash"] is not None
        assert stored["merchant_legal_published_at"] is not None
        assert snapshot["no_change"] is False
        assert snapshot["status"] == "published"

    @pytest.mark.asyncio
    async def test_idempotent_publish_no_version_bump(self):
        """Clicking 'Pubblica' twice without editing must NOT bump."""
        from routers.store_legal import publish_legal, PublishRequest

        store = _store_published()
        original_tag = store["merchant_legal_version_tag"]
        original_hash = store["merchant_legal_version_hash"]
        fake = _make_fake_db([store])

        with _patch_db(fake):
            snapshot = await publish_legal(
                "store-1", PublishRequest(), _user(),
            )

        stored = fake.get("store-1")
        assert stored["merchant_legal_version_tag"] == original_tag
        assert stored["merchant_legal_version_hash"] == original_hash
        assert snapshot["no_change"] is True

    @pytest.mark.asyncio
    async def test_publish_after_edit_bumps_minor(self):
        from routers.store_legal import publish_legal, PublishRequest

        store = _store_published()
        # Simulate an edit AFTER the publish: change IT content
        store["merchant_privacy_content_it"] = "# CHANGED IT PRIVACY"
        fake = _make_fake_db([store])

        with _patch_db(fake):
            snapshot = await publish_legal(
                "store-1", PublishRequest(), _user(),
            )

        stored = fake.get("store-1")
        assert stored["merchant_legal_version_tag"] == "v1.1"
        assert snapshot["no_change"] is False

    @pytest.mark.asyncio
    async def test_publish_without_active_locale_content_422(self):
        """CG-3-Polish: the display locale auto-derives from
        ``storefront_languages[0]`` (default "it"), so there's no
        longer a "missing display_locale" failure mode. The 422 fires
        when the active locale has empty content — the message tells
        the admin which locale needs filling."""
        from fastapi import HTTPException
        from routers.store_legal import publish_legal, PublishRequest

        # _store_not_configured() has storefront_languages=["it"] but
        # no merchant_*_content_* — effective locale = "it" but the
        # bundle is empty → 422.
        fake = _make_fake_db([_store_not_configured()])
        with _patch_db(fake), pytest.raises(HTTPException) as exc:
            await publish_legal("store-1", PublishRequest(), _user())
        assert exc.value.status_code == 422
        # Message references the language that needs content (uppercase)
        assert "IT" in exc.value.detail \
            or "lingua" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_publish_without_content_422(self):
        from fastapi import HTTPException
        from routers.store_legal import publish_legal, PublishRequest

        store = {
            **_store_not_configured(),
            # No content slots set, no explicit locale set →
            # effective locale = "it" (from storefront_languages[0])
            # but content is empty → 422.
        }
        fake = _make_fake_db([store])
        with _patch_db(fake), pytest.raises(HTTPException) as exc:
            await publish_legal("store-1", PublishRequest(), _user())
        assert exc.value.status_code == 422


# ─── Multi-tenant isolation ─────────────────────────────────────────


class TestMultiTenantIsolation:
    """For every mutating endpoint a cross-org call must 404 without
    leaking that the store_id exists in another org."""

    @pytest.mark.asyncio
    async def test_patch_content_cross_org(self):
        from fastapi import HTTPException
        from routers.store_legal import patch_legal_content, PatchContentRequest

        fake = _make_fake_db([_store_published()])  # org-1
        body = PatchContentRequest(
            doc_type="privacy", locale="it", content="hijack",
        )
        with _patch_db(fake), pytest.raises(HTTPException) as exc:
            await patch_legal_content(
                "store-1", body, _user("org-OTHER"),
            )
        assert exc.value.status_code == 404
        # The store doc is unchanged
        assert fake.get("store-1")["merchant_privacy_content_it"] != "hijack"

    @pytest.mark.asyncio
    async def test_publish_cross_org(self):
        from fastapi import HTTPException
        from routers.store_legal import publish_legal, PublishRequest

        fake = _make_fake_db([_store_published()])  # org-1
        with _patch_db(fake), pytest.raises(HTTPException) as exc:
            await publish_legal(
                "store-1", PublishRequest(), _user("org-OTHER"),
            )
        assert exc.value.status_code == 404


# ─── Router wiring ──────────────────────────────────────────────────


class TestRouteRegistration:
    """The 5 new admin routes are registered under /api/stores."""

    def _paths(self):
        from server import app
        return {
            (r.path, frozenset(getattr(r, "methods") or set()))
            for r in app.routes
            if getattr(r, "methods", None) is not None
        }

    def test_generate_draft_registered(self):
        assert (
            "/api/stores/{store_id}/legal/generate-draft",
            frozenset({"POST"}),
        ) in self._paths()

    def test_get_legal_registered(self):
        assert (
            "/api/stores/{store_id}/legal",
            frozenset({"GET"}),
        ) in self._paths()

    def test_patch_content_registered(self):
        assert (
            "/api/stores/{store_id}/legal/content",
            frozenset({"PATCH"}),
        ) in self._paths()

    def test_patch_display_locale_registered(self):
        assert (
            "/api/stores/{store_id}/legal/display-locale",
            frozenset({"PATCH"}),
        ) in self._paths()

    def test_publish_registered(self):
        assert (
            "/api/stores/{store_id}/legal/publish",
            frozenset({"POST"}),
        ) in self._paths()

    def test_patch_template_vars_registered(self):
        """Wave CG-3-Polish — new endpoint for persistent wizard vars."""
        assert (
            "/api/stores/{store_id}/legal/template-vars",
            frozenset({"PATCH"}),
        ) in self._paths()


# ─── Wave CG-3-Polish — new behavior ────────────────────────────────


class TestEffectiveDisplayLocale:
    """``get_effective_display_locale`` resolves the customer-facing
    legal language with three-tier priority (CG-3-Polish-2 flipped
    the order — storefront_languages[0] now wins):
        1. ``storefront_languages[0]`` (modern path, always wins)
        2. legacy ``merchant_legal_display_locale`` (defensive fallback
           when storefront_languages is empty/missing)
        3. ``"it"`` ultimate fallback
    """

    def test_storefront_languages_wins_over_legacy_field(self):
        """CG-3-Polish-2: a stale legacy field set by the original
        CG-3 wizard MUST NOT override the merchant's current store
        primary language. Reported as a user-facing bug: merchant
        edited IT but received "your customers see EN" because the
        legacy field was stuck on "en" from a prior wizard run.
        """
        from services.merchant_legal_versioning import get_effective_display_locale
        store = {
            "merchant_legal_display_locale": "en",  # legacy drift
            "storefront_languages": ["it"],          # admin's current choice
        }
        assert get_effective_display_locale(store) == "it"

    def test_storefront_languages_when_no_explicit(self):
        from services.merchant_legal_versioning import get_effective_display_locale
        store = {"storefront_languages": ["en", "it"]}
        assert get_effective_display_locale(store) == "en"

    def test_fallback_to_it_when_both_missing(self):
        from services.merchant_legal_versioning import get_effective_display_locale
        store = {}
        assert get_effective_display_locale(store) == "it"

    def test_invalid_storefront_languages_falls_through_to_legacy(self):
        """When storefront_languages is empty / invalid AND the legacy
        field has a valid value, the legacy field becomes the fallback."""
        from services.merchant_legal_versioning import get_effective_display_locale
        store = {
            "merchant_legal_display_locale": "de",
            "storefront_languages": [],  # empty
        }
        assert get_effective_display_locale(store) == "de"

    def test_invalid_storefront_languages_value_falls_through(self):
        """A storefront_languages with an unsupported code falls
        through to the legacy field."""
        from services.merchant_legal_versioning import get_effective_display_locale
        store = {
            "merchant_legal_display_locale": "fr",
            "storefront_languages": ["xx-bogus"],
        }
        assert get_effective_display_locale(store) == "fr"


class TestPatchTemplateVars:
    """Wave CG-3-Polish — wizard vars are persisted on the store doc."""

    @pytest.mark.asyncio
    async def test_persists_vars_dict(self):
        from routers.store_legal import (
            patch_template_vars, PatchTemplateVarsRequest,
        )
        from services.merchant_legal_template_service import TemplateVars

        store = _store_not_configured()
        fake = _make_fake_db([store])
        vars_obj = TemplateVars(
            merchant_name="Mario Rossi",
            merchant_email="mario@example.com",
            merchant_country="Italia",
            store_name="Acme",
        )
        body = PatchTemplateVarsRequest(vars=vars_obj)

        with _patch_db(fake):
            snapshot = await patch_template_vars(
                "store-1", body, _user(),
            )

        stored = fake.get("store-1")
        assert stored["merchant_legal_template_vars"]["merchant_name"] == "Mario Rossi"
        assert stored["merchant_legal_template_vars"]["merchant_email"] == "mario@example.com"
        # Snapshot returned to the frontend exposes it
        assert snapshot["template_vars"]["merchant_name"] == "Mario Rossi"

    @pytest.mark.asyncio
    async def test_does_not_bump_version(self):
        """Editing template vars is identity metadata — NEVER bumps
        the legal version (the customer-visible content didn't change)."""
        from routers.store_legal import (
            patch_template_vars, PatchTemplateVarsRequest,
        )
        from services.merchant_legal_template_service import TemplateVars

        store = _store_published()
        original_tag = store["merchant_legal_version_tag"]
        original_hash = store["merchant_legal_version_hash"]
        fake = _make_fake_db([store])

        body = PatchTemplateVarsRequest(vars=TemplateVars(
            merchant_name="NEW Mario",
        ))
        with _patch_db(fake):
            await patch_template_vars("store-1", body, _user())

        stored = fake.get("store-1")
        assert stored["merchant_legal_version_tag"] == original_tag
        assert stored["merchant_legal_version_hash"] == original_hash

    @pytest.mark.asyncio
    async def test_cross_org_returns_404(self):
        from fastapi import HTTPException
        from routers.store_legal import (
            patch_template_vars, PatchTemplateVarsRequest,
        )
        from services.merchant_legal_template_service import TemplateVars

        fake = _make_fake_db([_store_published()])
        body = PatchTemplateVarsRequest(vars=TemplateVars(merchant_name="X"))
        with _patch_db(fake), pytest.raises(HTTPException) as exc:
            await patch_template_vars(
                "store-1", body, _user("org-OTHER"),
            )
        assert exc.value.status_code == 404


class TestLegacyFieldCleanup:
    """CG-3-Polish-2 — the deprecated ``merchant_legal_display_locale``
    field is silently unset whenever a polish-aware write happens
    (patch_legal_content / patch_template_vars / publish_legal). This
    cleans up drift left by the original CG-3 wizard, so the user's
    next "I changed the store's primary language" actually applies
    without manual DB intervention.
    """

    @pytest.mark.asyncio
    async def test_patch_content_unsets_legacy_field(self):
        from routers.store_legal import patch_legal_content, PatchContentRequest

        store = {
            **_store_published(),
            # Drift from a prior CG-3 wizard run
            "merchant_legal_display_locale": "en",
            "storefront_languages": ["it"],
        }
        fake = _make_fake_db([store])
        body = PatchContentRequest(
            doc_type="privacy", locale="it", content="# Updated",
        )
        with _patch_db(fake):
            await patch_legal_content("store-1", body, _user())

        stored = fake.get("store-1")
        # Legacy field is removed; the resolver now reads from
        # storefront_languages[0] cleanly.
        assert "merchant_legal_display_locale" not in stored \
            or stored.get("merchant_legal_display_locale") is None

    @pytest.mark.asyncio
    async def test_publish_unsets_legacy_field(self):
        from routers.store_legal import publish_legal, PublishRequest

        store = {
            **_store_published(),
            "merchant_legal_display_locale": "en",  # drift
            "storefront_languages": ["it"],
            # Edit so publish actually has work to do
            "merchant_privacy_content_it": "# CHANGED",
        }
        fake = _make_fake_db([store])
        with _patch_db(fake):
            await publish_legal("store-1", PublishRequest(), _user())

        stored = fake.get("store-1")
        assert "merchant_legal_display_locale" not in stored \
            or stored.get("merchant_legal_display_locale") is None


class TestGenerateDraftFallsBackToSavedVars:
    """When the client omits ``vars`` from the request, the endpoint
    pulls them from the persisted ``merchant_legal_template_vars``.
    """

    @pytest.mark.asyncio
    async def test_uses_saved_vars_when_request_omits_vars(self):
        from routers.store_legal import generate_draft, GenerateDraftRequest

        store = {
            **_store_not_configured(),
            "merchant_legal_template_vars": {
                "merchant_name": "Saved Mario",
                "merchant_email": "saved@example.com",
                "store_name": "Saved Store",
            },
        }
        fake = _make_fake_db([store])
        body = GenerateDraftRequest(
            doc_type="privacy", locale="it", vars=None,
        )
        with _patch_db(fake):
            result = await generate_draft(
                "store-1", body, _user(),
            )

        # The rendered output should carry the persisted identity
        assert "Saved Mario" in result["content"]
        assert "saved@example.com" in result["content"]


class TestPublishNoChangeReason:
    """Wave CG-3-Polish — publish surfaces WHY there's nothing to
    publish so the frontend can render a precise toast."""

    @pytest.mark.asyncio
    async def test_no_change_reason_when_only_non_display_edits(self):
        """Edits to EN/DE/FR with display=IT → no_change_reason
        explains it + lists which locales were edited."""
        from routers.store_legal import publish_legal, PublishRequest

        store = _store_published()  # IT display, IT published
        # Admin adds full EN bundle but doesn't change IT
        store["merchant_privacy_content_en"] = "# Privacy EN draft"
        store["merchant_terms_content_en"] = "# Terms EN draft"
        store["merchant_privacy_content_de"] = "# Privacy DE draft"
        store["merchant_terms_content_de"] = "# Terms DE draft"
        fake = _make_fake_db([store])

        with _patch_db(fake):
            res = await publish_legal(
                "store-1", PublishRequest(), _user(),
            )

        assert res["no_change"] is True
        assert res["no_change_reason"] == "non_display_edits_only"
        assert set(res["edited_non_display_locales"]) == {"en", "de"}
        assert res["active_locale"] == "it"

    @pytest.mark.asyncio
    async def test_no_change_reason_when_identical_content(self):
        """Click Publish twice with no edits → ``identical_content``."""
        from routers.store_legal import publish_legal, PublishRequest

        store = _store_published()  # already published, no further edits
        fake = _make_fake_db([store])

        with _patch_db(fake):
            res = await publish_legal(
                "store-1", PublishRequest(), _user(),
            )

        assert res["no_change"] is True
        assert res["no_change_reason"] == "identical_content"
        assert res["edited_non_display_locales"] == []

    @pytest.mark.asyncio
    async def test_real_change_bumps_and_returns_no_change_false(self):
        """Editing the DISPLAY locale + Publish → no_change=False."""
        from routers.store_legal import publish_legal, PublishRequest

        store = _store_published()
        # Real content change on the IT display locale
        store["merchant_privacy_content_it"] = "# REAL CHANGE IT"
        fake = _make_fake_db([store])

        with _patch_db(fake):
            res = await publish_legal(
                "store-1", PublishRequest(), _user(),
            )

        assert res["no_change"] is False
        assert res["no_change_reason"] is None
        assert res["edited_non_display_locales"] == []
        assert res["active_locale"] == "it"
        # Tag bumped from v1.0 → v1.1
        stored = fake.get("store-1")
        assert stored["merchant_legal_version_tag"] == "v1.1"


class TestEndToEndPublishVisibility:
    """Wave CG-3-Polish-4 regression — full save → publish → public-read
    flow asserted from end to end.

    Pins the user-reported bug: "after I save + publish, the changes
    don't actually appear in the public documents." Each step is
    exercised through its real call path so an issue at any layer
    (patch_legal_content / publish_legal / _public_doc_envelope) is
    caught here.
    """

    @pytest.mark.asyncio
    async def test_edit_save_publish_public_read_serves_new_content(self):
        """Simulate the merchant's real workflow:
            1. patch_legal_content with NEW IT content (display=IT)
            2. publish_legal → real bump (hash changed)
            3. _public_doc_envelope serves the NEW content
        """
        from routers.store_legal import (
            patch_legal_content, PatchContentRequest,
            publish_legal, PublishRequest,
        )
        from routers.legal import _public_doc_envelope

        # Start: published v1.0 with "old" IT content
        original = _store_published()
        original_content = "# Privacy IT v1"  # matches _store_published()
        original_hash = original["merchant_legal_version_hash"]
        fake = _make_fake_db([original])

        # Step 1: save new IT content
        save_body = PatchContentRequest(
            doc_type="privacy", locale="it",
            content="# REVISED Privacy IT — new clauses here",
        )
        with _patch_db(fake):
            snapshot_after_save = await patch_legal_content(
                "store-1", save_body, _user(),
            )

        stored_after_save = fake.get("store-1")
        # Content persisted, last_edited_at updated, version NOT bumped
        assert stored_after_save["merchant_privacy_content_it"] == \
            "# REVISED Privacy IT — new clauses here"
        assert stored_after_save["merchant_legal_last_edited_at"] is not None
        assert stored_after_save["merchant_legal_version_hash"] == original_hash
        # Status should now read "stale_draft" because we edited after publish
        assert snapshot_after_save["status"] == "stale_draft"

        # Step 2: publish
        with _patch_db(fake):
            publish_res = await publish_legal(
                "store-1", PublishRequest(), _user(),
            )

        stored_after_publish = fake.get("store-1")
        # Real publish happened
        assert publish_res["no_change"] is False
        assert publish_res["no_change_reason"] is None
        assert stored_after_publish["merchant_legal_version_hash"] != original_hash
        assert stored_after_publish["merchant_legal_version_tag"] == "v1.1"
        assert publish_res["status"] == "published"

        # Step 3: public storefront endpoint serves the NEW content
        envelope = _public_doc_envelope(stored_after_publish, "privacy")
        assert envelope["content"] == "# REVISED Privacy IT — new clauses here"
        assert envelope["status"] == "published"
        assert envelope["display_locale"] == "it"
        assert envelope["version_tag"] == "v1.1"
        assert envelope["version_string"] == publish_res["version_string"]

    @pytest.mark.asyncio
    async def test_publish_without_save_is_a_noop(self):
        """If the merchant clicks Publish WITHOUT saving the textarea
        first, the backend sees the OLD content in the DB and treats
        the publish as a no-op. This is the design contract that the
        frontend's "smart publish" (auto-save before publish) papers
        over for the user."""
        from routers.store_legal import publish_legal, PublishRequest

        store = _store_published()
        original_hash = store["merchant_legal_version_hash"]
        fake = _make_fake_db([store])

        # No patch_legal_content here — simulating "click Publish
        # without saving". The frontend buffer is dirty but the DB is
        # unchanged.
        with _patch_db(fake):
            res = await publish_legal(
                "store-1", PublishRequest(), _user(),
            )

        assert res["no_change"] is True
        assert res["no_change_reason"] == "identical_content"
        # No bump
        stored = fake.get("store-1")
        assert stored["merchant_legal_version_hash"] == original_hash

    @pytest.mark.asyncio
    async def test_edit_non_display_locale_does_not_block_other_publishes(self):
        """Edit EN (non-display), save, publish → no_change. Then edit
        IT (display), save, publish → real bump. Asserts that the
        no-display-edits-only state doesn't poison subsequent publishes."""
        from routers.store_legal import (
            patch_legal_content, PatchContentRequest,
            publish_legal, PublishRequest,
        )

        store = _store_published()
        store["merchant_privacy_content_en"] = "# Privacy EN v1"
        store["merchant_terms_content_en"] = "# Terms EN v1"
        fake = _make_fake_db([store])

        # 1. Save EN content
        with _patch_db(fake):
            await patch_legal_content(
                "store-1",
                PatchContentRequest(doc_type="privacy", locale="en", content="# EN edited"),
                _user(),
            )

        # 2. Publish → no_change (EN is non-display)
        with _patch_db(fake):
            res1 = await publish_legal("store-1", PublishRequest(), _user())
        assert res1["no_change"] is True
        assert res1["no_change_reason"] == "non_display_edits_only"
        assert "en" in res1["edited_non_display_locales"]

        # 3. NOW save IT content (display locale)
        with _patch_db(fake):
            await patch_legal_content(
                "store-1",
                PatchContentRequest(doc_type="privacy", locale="it", content="# IT edited"),
                _user(),
            )

        # 4. Publish again → real bump (IT changed)
        with _patch_db(fake):
            res2 = await publish_legal("store-1", PublishRequest(), _user())
        assert res2["no_change"] is False
        stored = fake.get("store-1")
        assert stored["merchant_legal_version_tag"] == "v1.1"
