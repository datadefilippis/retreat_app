"""Tests for Phase 3 of the Store consolidation plan: slug-index
lifecycle hardening.

Goal
----
The `stores_collection` carries TWO slug-related uniqueness indexes by
intentional design:

  · composite (organization_id, slug) UNIQUE partial
        defense-in-depth + fast org-scoped lookups
  · global  slug                       UNIQUE partial
        REQUIRED for deterministic public routing
        (`/co/<slug>` URL → `_resolve_org()` in routers/public.py
        finds the store by slug alone, with no org context)

Pre-Phase-3 the global index was created with a silent try/except
swallowing all errors. If a legacy `sparse=True` index existed from
pre-Onda-9.Z, the create-index call would fail (options conflict), and
the system silently ran WITHOUT global slug uniqueness. Public routing
becomes non-deterministic in that state — two orgs with the same slug
would `find_one()` randomly.

Phase 3 introduces:
  · `database._ensure_stores_indexes()` — idempotent helper that
    detects legacy specs, drops them, and creates the canonical pair.
  · `scripts/migrate_stores_slug_index.py` — explicit CLI for the
    one-shot migration of existing deployments (canary-verified).

This file pins:
  1. The canonical index spec constants (single source of truth).
  2. The `_index_spec_matches()` classifier — legacy vs canonical.
  3. The idempotency contract: calling `_ensure_stores_indexes` on
     a clean state must produce the canonical indexes; calling it
     a second time must no-op.
  4. The migration helper's classification logic (`_classify` from
     the CLI script) agrees with the database helper.

Tests use a real ephemeral Motor connection to MongoDB (same as the
e2e tests). When MongoDB isn't available, they're skipped — no
unittest.mock contortions that misrepresent how MongoDB indexes
actually behave.
"""

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


# ── Pure spec/classifier tests (no MongoDB required) ───────────────────────


class TestCanonicalSpecConstants:
    """The canonical index spec constants are the contract between
    runtime, migration script, and tests. Lock the exact values."""

    def test_composite_index_name_pinned(self):
        from database import _STORES_COMPOSITE_SLUG_NAME

        # MongoDB auto-names compound indexes as `field_dir_field_dir`.
        # The migration script's idempotency check assumes this exact
        # name — drift would break the spec-match comparison.
        assert _STORES_COMPOSITE_SLUG_NAME == "organization_id_1_slug_1"

    def test_composite_index_keys_pinned(self):
        from database import _STORES_COMPOSITE_SLUG_KEYS

        # Order matters: org_id first, then slug. A reversed order
        # would still be unique but slower for org-scoped queries
        # (which is the primary read path: `find({"organization_id":x})`).
        assert _STORES_COMPOSITE_SLUG_KEYS == [("organization_id", 1), ("slug", 1)]

    def test_composite_index_options_pinned(self):
        from database import _STORES_COMPOSITE_SLUG_OPTIONS

        assert _STORES_COMPOSITE_SLUG_OPTIONS == {
            "unique": True,
            "partialFilterExpression": {"slug": {"$type": "string"}},
        }
        # The partial filter must exclude null/missing slugs so multiple
        # stores can exist in draft state. `$type: "string"` is stricter
        # than `$exists: true` (which also matches null).
        pfe = _STORES_COMPOSITE_SLUG_OPTIONS["partialFilterExpression"]
        assert pfe["slug"]["$type"] == "string"

    def test_global_index_name_pinned(self):
        from database import _STORES_GLOBAL_SLUG_NAME

        # MUST be exactly `slug_1` — the migration CLI looks up the
        # index by this name. A rename here breaks the rollback path.
        assert _STORES_GLOBAL_SLUG_NAME == "slug_1"

    def test_global_index_options_pinned(self):
        from database import _STORES_GLOBAL_SLUG_OPTIONS

        # MUST mirror the composite's partial filter so the two
        # uniqueness scopes agree on which docs are "live": null-slug
        # drafts are bypassed by both.
        assert _STORES_GLOBAL_SLUG_OPTIONS == {
            "unique": True,
            "partialFilterExpression": {"slug": {"$type": "string"}},
        }


class TestIndexSpecMatcher:
    """The `_index_spec_matches` helper decides whether an existing
    Mongo index document satisfies the expected options. Wrong answer
    here means either:
      - false positive: legacy index left in place → silent bug
      - false negative: canonical index dropped + recreated → harmless
        but adds startup latency on every boot
    Pin the exact decision rules."""

    EXPECTED = {
        "unique": True,
        "partialFilterExpression": {"slug": {"$type": "string"}},
    }

    def test_matches_canonical_spec(self):
        from database import _index_spec_matches

        existing = {
            "name": "slug_1",
            "unique": True,
            "partialFilterExpression": {"slug": {"$type": "string"}},
        }
        assert _index_spec_matches(existing, self.EXPECTED) is True

    def test_rejects_legacy_sparse(self):
        from database import _index_spec_matches

        # The pre-Onda-9.Z spec. `sparse=True` instead of
        # partialFilterExpression. Must be classified as mismatch
        # so the helper drops and recreates.
        existing = {
            "name": "slug_1",
            "unique": True,
            "sparse": True,
        }
        assert _index_spec_matches(existing, self.EXPECTED) is False

    def test_rejects_missing_unique(self):
        from database import _index_spec_matches

        # A non-unique index on the same field would let collisions
        # through silently. Defense-in-depth: treat as mismatch.
        existing = {
            "name": "slug_1",
            "partialFilterExpression": {"slug": {"$type": "string"}},
        }
        assert _index_spec_matches(existing, self.EXPECTED) is False

    def test_rejects_different_partial_filter(self):
        from database import _index_spec_matches

        # If someone manually altered the partial filter to (say)
        # `{$exists: true}` (which would include null slugs), the
        # uniqueness semantics shift. Treat as mismatch.
        existing = {
            "name": "slug_1",
            "unique": True,
            "partialFilterExpression": {"slug": {"$exists": True}},
        }
        assert _index_spec_matches(existing, self.EXPECTED) is False

    def test_rejects_sparse_plus_partial_combination(self):
        from database import _index_spec_matches

        # Belt-and-braces: even if both flags are set (which Mongo
        # accepts but is semantically ambiguous), treat as legacy.
        existing = {
            "name": "slug_1",
            "unique": True,
            "sparse": True,
            "partialFilterExpression": {"slug": {"$type": "string"}},
        }
        assert _index_spec_matches(existing, self.EXPECTED) is False


# ── Migration script classifier ────────────────────────────────────────────


class TestMigrationScriptClassifier:
    """The CLI script's `_classify` function maps a Mongo index doc to
    one of {missing, partial, sparse, unknown}. The runtime helper's
    `_index_spec_matches` and the CLI's `_classify` must agree on what
    counts as "needs migration" — drift between them would mean the
    CLI reports OK while runtime keeps re-migrating (or vice versa)."""

    def test_classify_missing(self):
        from scripts.migrate_stores_slug_index import _classify

        assert _classify(None) == "missing"
        assert _classify({}) == "missing"

    def test_classify_canonical_partial(self):
        from scripts.migrate_stores_slug_index import _classify

        idx = {
            "name": "slug_1",
            "unique": True,
            "partialFilterExpression": {"slug": {"$type": "string"}},
        }
        assert _classify(idx) == "partial"

    def test_classify_legacy_sparse(self):
        from scripts.migrate_stores_slug_index import _classify

        idx = {"name": "slug_1", "unique": True, "sparse": True}
        assert _classify(idx) == "sparse"

    def test_classify_unknown(self):
        from scripts.migrate_stores_slug_index import _classify

        # No sparse, no partial — neither shape. The CLI should flag
        # for manual review rather than blindly drop+recreate.
        idx = {"name": "slug_1", "unique": True}
        assert _classify(idx) == "unknown"


# ── End-to-end integration with real MongoDB (skipped when unavailable) ────


@pytest.fixture
async def isolated_stores_collection():
    """Return a fresh `stores_test_<random>` collection on the dev
    MongoDB, drop all indexes (including the auto-_id_), and yield.
    Cleans up by dropping the entire collection afterwards.

    Skipped automatically if MongoDB isn't reachable — tests degrade
    gracefully on developer laptops without a running mongod."""
    import uuid
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        # Ping to check availability
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB unavailable: {e}")

    db_name = os.environ.get("DB_NAME", "test_db")
    coll_name = f"stores_test_{uuid.uuid4().hex[:8]}"
    coll = client[db_name][coll_name]
    try:
        yield coll
    finally:
        try:
            await coll.drop()
        except Exception:
            pass
        client.close()


class TestEnsureStoresIndexesIntegration:
    """End-to-end: pointing the helper at an ephemeral collection,
    verify it leaves the canonical indexes in place.

    Skipped when MongoDB is unreachable (most CI environments are; the
    pure tests above cover the spec contract there)."""

    @pytest.mark.asyncio
    async def test_first_call_creates_canonical_set(self, isolated_stores_collection):
        from database import (
            _ensure_stores_indexes,
            _STORES_COMPOSITE_SLUG_NAME,
            _STORES_GLOBAL_SLUG_NAME,
        )
        # Monkey-patch the helper's collection reference. The helper
        # uses module-level `stores_collection`, so we swap it
        # in/out via a direct attribute assignment.
        import database as db_mod
        original = db_mod.stores_collection
        db_mod.stores_collection = isolated_stores_collection
        try:
            await _ensure_stores_indexes()
            names = set()
            async for idx in isolated_stores_collection.list_indexes():
                names.add(idx["name"])
            # _id_ is auto-created; canonical indexes must be present.
            assert _STORES_COMPOSITE_SLUG_NAME in names
            assert _STORES_GLOBAL_SLUG_NAME in names
        finally:
            db_mod.stores_collection = original

    @pytest.mark.asyncio
    async def test_idempotent_second_call_noop(self, isolated_stores_collection):
        from database import _ensure_stores_indexes
        import database as db_mod
        original = db_mod.stores_collection
        db_mod.stores_collection = isolated_stores_collection
        try:
            await _ensure_stores_indexes()
            first = {idx["name"] async for idx in isolated_stores_collection.list_indexes()}
            await _ensure_stores_indexes()  # should be a no-op
            second = {idx["name"] async for idx in isolated_stores_collection.list_indexes()}
            assert first == second, (
                "Second call to _ensure_stores_indexes changed the index "
                "set — idempotency violation."
            )
        finally:
            db_mod.stores_collection = original

    @pytest.mark.asyncio
    async def test_legacy_sparse_is_migrated(self, isolated_stores_collection):
        """The whole point of the Phase 3 hardening: a pre-existing
        `slug_1` with sparse=True must be detected and replaced with
        the partialFilterExpression spec on the next startup."""
        from database import _ensure_stores_indexes, _STORES_GLOBAL_SLUG_NAME
        import database as db_mod

        # Plant the legacy spec
        await isolated_stores_collection.create_index(
            "slug",
            name=_STORES_GLOBAL_SLUG_NAME,
            unique=True,
            sparse=True,
        )
        original = db_mod.stores_collection
        db_mod.stores_collection = isolated_stores_collection
        try:
            await _ensure_stores_indexes()
            spec = None
            async for idx in isolated_stores_collection.list_indexes():
                if idx["name"] == _STORES_GLOBAL_SLUG_NAME:
                    spec = idx
                    break
            assert spec is not None
            assert "partialFilterExpression" in spec, (
                f"Migration didn't apply — index still has spec={spec}. "
                "_ensure_stores_indexes failed to detect the legacy sparse."
            )
            assert not spec.get("sparse"), (
                "Migration left sparse=True on the new index — should be "
                "pure partialFilterExpression."
            )
        finally:
            db_mod.stores_collection = original
