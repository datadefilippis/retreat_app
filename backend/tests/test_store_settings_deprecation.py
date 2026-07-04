"""Tests for Phase 6 of the Store consolidation plan: legacy
`/store-settings` endpoint deprecation + dual-write to stores_collection.

The bug
-------
Pre-Phase-6 the platform carried two parallel storage paths for store
configuration:

  · LEGACY:  organizations.store_settings   (embedded dict)
             written by PATCH /store-settings
  · NEW:     stores_collection              (one doc per store)
             written by PATCH /stores/{id}

The two surfaces had different validation (Phase 2 fixed this) and no
synchronisation, so an admin saving via the legacy form would update
`org.store_settings` without touching `stores_collection`. The email
service, the storefront resolver, and the new admin UI all read
`stores_collection` first — the legacy write was effectively a dead
letter for those code paths.

The fix
-------
Phase 6 keeps the legacy endpoint FUNCTIONAL but:

  1. Emits IETF RFC 8594 deprecation signals:
       Deprecation: true
       Sunset: <date>
       Link: </api/stores>; rel="successor-version"

  2. Dual-writes every legacy payload onto the org's default store in
     stores_collection via `_dual_write_to_default_store`. Field name
     translation (legacy -> new) is centralised in
     LEGACY_TO_STORE_FIELD_MAP so the contract is single-source-of-truth.

  3. Bootstraps a default store from `org.store_settings` if the org
     has no entry in stores_collection yet (zero-downtime migration).

  4. Never raises: a failure in the dual-write step logs WARNING and
     returns. The legacy write already succeeded; the new collection
     just drifts until the next admin save (or until the migration
     script runs).

What this file pins
-------------------
  - Field map: legacy -> new field names (5 mappings exact, the rest pass-through)
  - Deprecation headers present on every GET and PATCH response
  - Dual-write idempotency: re-applying the same payload doesn't
    create duplicate stores
  - Dual-write bootstraps a store when the org has zero
  - Dual-write applies the field translation correctly
  - Migration script classifier matches the dual-write logic
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


# ── Pure unit tests (no MongoDB required) ──────────────────────────────────


class TestFieldMap:
    """The legacy->new field mapping is the single source of truth for
    dual-write. Any drift between this map and the production callers
    (email_service, public.py, etc) would silently propagate stale
    data."""

    def test_explicit_mappings(self):
        from routers.store_settings import LEGACY_TO_STORE_FIELD_MAP
        # Only 3 fields are renamed; the rest pass through unchanged.
        # If we add more renames in future, this test should fail until
        # consumers (email_service, etc) are also audited.
        assert LEGACY_TO_STORE_FIELD_MAP == {
            "display_name": "name",
            "store_description": "description",
            "is_storefront_published": "is_published",
        }

    def test_pass_through_fields(self):
        from routers.store_settings import _map_legacy_field
        # All non-mapped fields are returned verbatim.
        same_name_fields = [
            "contact_email", "contact_phone", "notification_email",
            "sender_display_name", "reply_to_email",
            "logo_url", "brand_color", "brand_color_text",
            "seo_title", "seo_description",
            "email_delivery", "fulfillment_modes",
        ]
        for f in same_name_fields:
            assert _map_legacy_field(f) == f, (
                f"Field {f!r} unexpectedly renamed — review consumers "
                "before adding a translation."
            )

    def test_renamed_field_returns_mapped_value(self):
        from routers.store_settings import _map_legacy_field
        assert _map_legacy_field("display_name") == "name"
        assert _map_legacy_field("store_description") == "description"
        assert _map_legacy_field("is_storefront_published") == "is_published"


class TestDeprecationConstants:
    def test_sunset_date_is_http_date_format(self):
        """RFC 7231 IMF-fixdate format. A bad format would make the
        Sunset header invalid; some clients (e.g. modern fetch libs)
        warn or reject the response entirely."""
        from routers.store_settings import DEPRECATION_SUNSET_DATE
        from email.utils import parsedate_to_datetime
        # Must parse without raising
        parsed = parsedate_to_datetime(DEPRECATION_SUNSET_DATE)
        assert parsed is not None
        # Must be in the future (sunsetting a date in the past would be
        # confusing — sane operators won't approve such a PR but this
        # test still gives a guardrail).
        from datetime import datetime, timezone
        assert parsed > datetime(2024, 1, 1, tzinfo=timezone.utc)

    def test_attach_deprecation_headers_sets_all_three(self):
        from routers.store_settings import (
            _attach_deprecation_headers,
            DEPRECATION_SUNSET_DATE,
        )
        # Fake Response object with a headers dict (matches FastAPI's
        # Response interface).
        class FakeResp:
            def __init__(self):
                self.headers = {}
        r = FakeResp()
        _attach_deprecation_headers(r)
        assert r.headers["Deprecation"] == "true"
        assert r.headers["Sunset"] == DEPRECATION_SUNSET_DATE
        # The Link header must point at the successor endpoint per RFC 8594.
        # Frontend banner reads this URL to render the migration CTA.
        assert "rel=\"successor-version\"" in r.headers["Link"]
        assert "/api/stores" in r.headers["Link"]


# ── Integration tests against real MongoDB ─────────────────────────────────


@pytest.fixture
async def isolated_test_db():
    import uuid
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB unavailable: {e}")

    db_name = f"test_phase6_{uuid.uuid4().hex[:8]}"
    db = client[db_name]
    try:
        yield {"client": client, "db": db, "db_name": db_name}
    finally:
        try:
            await client.drop_database(db_name)
        except Exception:
            pass
        client.close()


def _swap_collections(test_db):
    import database as db_mod
    originals = {
        "organizations": db_mod.organizations_collection,
        "stores": db_mod.stores_collection,
    }
    db_mod.organizations_collection = test_db.organizations
    db_mod.stores_collection = test_db.stores
    # The store_settings router imports these at module level too.
    import routers.store_settings as ss_mod
    ss_mod.organizations_collection = test_db.organizations
    ss_mod.stores_collection = test_db.stores
    return originals


def _restore_collections(originals):
    import database as db_mod
    db_mod.organizations_collection = originals["organizations"]
    db_mod.stores_collection = originals["stores"]
    import routers.store_settings as ss_mod
    ss_mod.organizations_collection = originals["organizations"]
    ss_mod.stores_collection = originals["stores"]


class TestDualWriteBootstrap:
    """An org with legacy store_settings but ZERO stores_collection
    entries should get a bootstrapped default store on the first
    dual-write. This is the migration path for very old orgs."""

    @pytest.mark.asyncio
    async def test_creates_store_when_org_has_only_legacy_settings(
        self, isolated_test_db,
    ):
        from routers.store_settings import _dual_write_to_default_store

        test_db = isolated_test_db["db"]
        await test_db.organizations.insert_one({
            "id": "org_only_legacy",
            "name": "Legacy Org",
            "public_slug": "legacy-org",
            "store_settings": {
                "display_name": "Legacy Display",
                "contact_email": "legacy@example.com",
            },
        })

        originals = _swap_collections(test_db)
        try:
            await _dual_write_to_default_store(
                "org_only_legacy",
                {"display_name": "New Name", "contact_email": "new@example.com"},
            )
        finally:
            _restore_collections(originals)

        # A store doc should now exist for this org.
        store = await test_db.stores.find_one(
            {"organization_id": "org_only_legacy"}, {"_id": 0},
        )
        assert store is not None, "Bootstrap failed — no store created"
        assert store["is_default"] is True
        assert store["is_active"] is True
        # The dual-write applies AFTER bootstrap, so the latest payload
        # values should be present (translated via the field map).
        assert store["name"] == "New Name"
        assert store["contact_email"] == "new@example.com"


class TestDualWriteFieldTranslation:
    """The legacy->new field map must apply correctly on every dual
    write. A drift would silently break the email service which reads
    `store.name` (not `store.display_name`)."""

    @pytest.mark.asyncio
    async def test_display_name_becomes_name(self, isolated_test_db):
        from routers.store_settings import _dual_write_to_default_store

        test_db = isolated_test_db["db"]
        await test_db.organizations.insert_one({
            "id": "org_t", "name": "T", "store_settings": {"display_name": "Old"},
        })
        # Pre-seed a default store so we test the UPDATE branch, not
        # the bootstrap branch.
        await test_db.stores.insert_one({
            "id": "store_t", "organization_id": "org_t",
            "name": "Old", "is_default": True, "is_active": True,
        })

        originals = _swap_collections(test_db)
        try:
            await _dual_write_to_default_store(
                "org_t", {"display_name": "Brand New Name"},
            )
        finally:
            _restore_collections(originals)

        store = await test_db.stores.find_one(
            {"id": "store_t"}, {"_id": 0, "name": 1},
        )
        assert store["name"] == "Brand New Name", (
            "display_name -> name translation didn't happen — emails "
            "would still show the old name."
        )

    @pytest.mark.asyncio
    async def test_store_description_becomes_description(self, isolated_test_db):
        from routers.store_settings import _dual_write_to_default_store

        test_db = isolated_test_db["db"]
        await test_db.organizations.insert_one({
            "id": "org_t2", "name": "T2",
        })
        await test_db.stores.insert_one({
            "id": "store_t2", "organization_id": "org_t2",
            "name": "x", "is_default": True, "is_active": True,
        })

        originals = _swap_collections(test_db)
        try:
            await _dual_write_to_default_store(
                "org_t2", {"store_description": "Our story..."},
            )
        finally:
            _restore_collections(originals)

        store = await test_db.stores.find_one(
            {"id": "store_t2"}, {"_id": 0, "description": 1},
        )
        assert store["description"] == "Our story..."

    @pytest.mark.asyncio
    async def test_is_storefront_published_becomes_is_published(
        self, isolated_test_db,
    ):
        from routers.store_settings import _dual_write_to_default_store

        test_db = isolated_test_db["db"]
        await test_db.organizations.insert_one({"id": "org_t3", "name": "T3"})
        await test_db.stores.insert_one({
            "id": "store_t3", "organization_id": "org_t3",
            "name": "x", "is_default": True, "is_active": True,
            "is_published": False,
        })

        originals = _swap_collections(test_db)
        try:
            await _dual_write_to_default_store(
                "org_t3", {"is_storefront_published": True},
            )
        finally:
            _restore_collections(originals)

        store = await test_db.stores.find_one(
            {"id": "store_t3"}, {"_id": 0, "is_published": 1},
        )
        assert store["is_published"] is True

    @pytest.mark.asyncio
    async def test_pass_through_fields_preserved(self, isolated_test_db):
        """Fields with the same name in both schemas should pass
        through verbatim — no special translation needed."""
        from routers.store_settings import _dual_write_to_default_store

        test_db = isolated_test_db["db"]
        await test_db.organizations.insert_one({"id": "org_pt", "name": "PT"})
        await test_db.stores.insert_one({
            "id": "store_pt", "organization_id": "org_pt",
            "name": "x", "is_default": True, "is_active": True,
        })

        originals = _swap_collections(test_db)
        try:
            await _dual_write_to_default_store("org_pt", {
                "contact_email": "test@x.com",
                "brand_color": "#FF5500",
                "fulfillment_modes": ["shipping", "local_pickup"],
            })
        finally:
            _restore_collections(originals)

        store = await test_db.stores.find_one(
            {"id": "store_pt"}, {"_id": 0},
        )
        assert store["contact_email"] == "test@x.com"
        assert store["brand_color"] == "#FF5500"
        assert store["fulfillment_modes"] == ["shipping", "local_pickup"]


class TestDualWriteIdempotency:
    """Re-applying the same payload via dual-write should NOT create
    duplicate stores. The helper finds the existing default and
    updates in place."""

    @pytest.mark.asyncio
    async def test_repeated_calls_dont_duplicate_store(self, isolated_test_db):
        from routers.store_settings import _dual_write_to_default_store

        test_db = isolated_test_db["db"]
        await test_db.organizations.insert_one({
            "id": "org_idem", "name": "Idem", "public_slug": "idem",
            "store_settings": {"display_name": "Idem"},
        })

        originals = _swap_collections(test_db)
        try:
            # First call: bootstrap creates a store.
            await _dual_write_to_default_store("org_idem", {"display_name": "A"})
            # 10 more calls — same payload — should all hit the
            # update branch, never the bootstrap branch.
            for i in range(10):
                await _dual_write_to_default_store("org_idem", {"display_name": f"Name {i}"})
        finally:
            _restore_collections(originals)

        # Exactly ONE store for this org.
        count = await test_db.stores.count_documents({"organization_id": "org_idem"})
        assert count == 1, (
            f"Expected 1 store after 11 dual-writes, got {count} — "
            "idempotency contract violated."
        )


class TestDualWriteFailureSafety:
    """If the dual-write encounters an unexpected error, it must NOT
    propagate the exception. The legacy write has already succeeded
    above the dual-write call; we don't want to roll that back."""

    @pytest.mark.asyncio
    async def test_swallows_exceptions(self, isolated_test_db):
        from routers.store_settings import _dual_write_to_default_store

        test_db = isolated_test_db["db"]
        # No org exists — _dual_write_to_default_store will reach the
        # "org not found" branch and log a WARNING, not raise.

        originals = _swap_collections(test_db)
        try:
            # Must not raise even though org doesn't exist
            await _dual_write_to_default_store(
                "nonexistent_org", {"display_name": "X"},
            )
        finally:
            _restore_collections(originals)

    @pytest.mark.asyncio
    async def test_storage_error_swallowed(self, isolated_test_db):
        """Forcing a storage-layer error (planting a duplicate-key
        condition) must not bubble up — the dual-write helper logs
        WARNING but returns cleanly so the legacy endpoint stays up."""
        from routers.store_settings import _dual_write_to_default_store

        test_db = isolated_test_db["db"]
        await test_db.organizations.insert_one({"id": "org_e", "name": "E"})

        # Mock stores_collection to raise on update_one.
        with patch("routers.store_settings.stores_collection") as mock_stores:
            mock_stores.find_one = AsyncMock(side_effect=Exception("simulated DB error"))
            # No raise expected.
            await _dual_write_to_default_store("org_e", {"display_name": "X"})


class TestMigrationScript:
    """The CLI script's classifier and field map must agree with the
    runtime dual-write helper. Drift between the two would mean the
    pre-deploy migration produces stores that look different from what
    the runtime updates them into."""

    def test_classifier_imports(self):
        # The migration script provides a CLI entrypoint; the helper
        # functions are importable for tests.
        from scripts.migrate_store_settings_to_stores import (
            _audit_org, _apply_org, _legacy_to_store_doc,
        )
        assert callable(_audit_org)
        assert callable(_apply_org)
        assert callable(_legacy_to_store_doc)

    def test_legacy_to_store_doc_field_translation(self):
        """The script's bootstrap function uses the same logical
        mapping as the runtime dual-write. Check key fields."""
        from scripts.migrate_store_settings_to_stores import _legacy_to_store_doc

        org = {"id": "o1", "name": "Org One", "public_slug": "org-one"}
        ss = {
            "display_name": "Store Name",
            "store_description": "Our story",
            "is_storefront_published": True,
            "contact_email": "x@y.com",
            "fulfillment_modes": ["local_pickup"],
        }
        doc = _legacy_to_store_doc(org, ss)
        assert doc["organization_id"] == "o1"
        assert doc["slug"] == "org-one"
        # Renamed fields
        assert doc["name"] == "Store Name"
        assert doc["description"] == "Our story"
        assert doc["is_published"] is True
        # Pass-through fields
        assert doc["contact_email"] == "x@y.com"
        assert doc["fulfillment_modes"] == ["local_pickup"]
        # System fields
        assert doc["is_default"] is True
        assert doc["is_active"] is True
        assert doc["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_audit_org_classifies_correctly(self, isolated_test_db):
        from scripts.migrate_store_settings_to_stores import _audit_org

        test_db = isolated_test_db["db"]

        # Case 1: org with existing default store
        await test_db.organizations.insert_one({"id": "o_a", "name": "A"})
        await test_db.stores.insert_one({
            "id": "s_a", "organization_id": "o_a",
            "is_default": True, "is_active": True,
        })

        # Case 2: org with active stores but none default
        await test_db.organizations.insert_one({"id": "o_b", "name": "B"})
        await test_db.stores.insert_one({
            "id": "s_b", "organization_id": "o_b",
            "is_default": False, "is_active": True,
        })

        # Case 3: org with only legacy data
        await test_db.organizations.insert_one({
            "id": "o_c", "name": "C",
            "store_settings": {"display_name": "Legacy", "contact_email": "c@x.com"},
        })

        # Case 4: empty org
        await test_db.organizations.insert_one({"id": "o_d", "name": "D"})

        # Case 5: nonexistent
        # (no insert)

        import database as db_mod
        originals = {
            "organizations": db_mod.organizations_collection,
            "stores": db_mod.stores_collection,
        }
        db_mod.organizations_collection = test_db.organizations
        db_mod.stores_collection = test_db.stores
        try:
            assert (await _audit_org("o_a"))["state"] == "has_default"
            assert (await _audit_org("o_b"))["state"] == "promote_existing"
            assert (await _audit_org("o_c"))["state"] == "bootstrap_from_legacy"
            assert (await _audit_org("o_d"))["state"] == "empty"
            assert (await _audit_org("nonexistent"))["state"] == "missing_org"
        finally:
            db_mod.organizations_collection = originals["organizations"]
            db_mod.stores_collection = originals["stores"]
