"""Tests for Phase 4 of the Store consolidation plan: race-safe
customer upsert keyed on (organization_id, email).

Goal
----
Pre-Phase-4 both `routers/public._find_or_create_customer` and the POS
checkout flow in `routers/orders.py` did:

    existing = find_one({org_id, email})
    if existing: return existing.id
    insert_one(new_doc)

Two concurrent checkouts from the same email could each see
`existing=None` and both insert. Result: duplicate customer rows in
the same org, downstream aggregations (`customer_metrics_collection`)
double-counting the same person.

Phase 4 fixes both code paths to call
`repositories.customer_repository.upsert_by_email`, which wraps a
`find_one_and_update(upsert=True)` — Mongo guarantees atomicity at
the document level. The new unique partial index on
(organization_id, email) is the storage-layer backstop: if a future
caller bypasses the helper, the second insert hits DuplicateKey
instead of silently corrupting state.

This file pins:
  1. Email normalisation (strip + lowercase) is the single
     pre-comparison transform; admin and storefront paths converge.
  2. The upsert is idempotent: calling with the same email twice
     returns the same customer_id (no duplicate rows).
  3. Name updates propagate on re-encounter (latest visitor name wins).
  4. Phone is set on insert but NOT clobbered on update (stable
     contact preference).
  5. customer_account_id is linked on update when caller has one
     and the existing row doesn't.
  6. Concurrent upserts converge on a single document (race test —
     simulates the pre-Phase-4 vulnerability).
  7. The unique partial index spec matches expectations.

Real-MongoDB integration tests. Skip when Mongo unreachable.
"""

import asyncio
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


# ── Pure unit test: email normalisation ─────────────────────────────────────


class TestEmailNormalisation:
    """`_normalise_email` is the single transform applied before
    every (org_id, email) comparison. Drift would break uniqueness
    semantics (admin-typed "Alice@Foo.COM" and storefront-typed
    "alice@foo.com" would map to different documents)."""

    def test_lowercases(self):
        from repositories.customer_repository import _normalise_email
        assert _normalise_email("ALICE@FOO.COM") == "alice@foo.com"

    def test_strips_whitespace(self):
        from repositories.customer_repository import _normalise_email
        assert _normalise_email("  alice@foo.com  ") == "alice@foo.com"

    def test_mixed_case_and_whitespace(self):
        from repositories.customer_repository import _normalise_email
        assert _normalise_email("  Alice@FOO.com\n") == "alice@foo.com"

    def test_none_returns_none(self):
        from repositories.customer_repository import _normalise_email
        assert _normalise_email(None) is None

    def test_empty_returns_none(self):
        # Critical: empty string MUST return None so the partial index
        # bypasses the row. An empty-string email indexed as a string
        # value would collide between any two anonymous customers.
        from repositories.customer_repository import _normalise_email
        assert _normalise_email("") is None

    def test_whitespace_only_returns_none(self):
        from repositories.customer_repository import _normalise_email
        assert _normalise_email("   \n\t") is None


# ── Pre-condition signature test (no DB) ───────────────────────────────────


class TestUpsertBlocksEmptyEmail:
    @pytest.mark.asyncio
    async def test_empty_email_raises(self):
        # The helper is KEYED on email — passing an empty email is a
        # programmer error (caller should branch on email presence
        # before calling). Reject loudly.
        from repositories.customer_repository import upsert_by_email
        with pytest.raises(ValueError, match="non-empty email"):
            await upsert_by_email("org_test", name="x", email="")

    @pytest.mark.asyncio
    async def test_whitespace_email_raises(self):
        from repositories.customer_repository import upsert_by_email
        with pytest.raises(ValueError, match="non-empty email"):
            await upsert_by_email("org_test", name="x", email="   ")


# ── Integration tests with real MongoDB ─────────────────────────────────────


@pytest.fixture
async def isolated_customers_collection():
    """Return a fresh `customers_test_<random>` collection on the dev
    MongoDB with the unique partial index applied, then yield. Cleans
    up by dropping the collection afterwards.

    Skipped if MongoDB is unreachable. The unit tests above still run."""
    import uuid
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB unavailable: {e}")

    db_name = os.environ.get("DB_NAME", "test_db")
    coll_name = f"customers_test_{uuid.uuid4().hex[:8]}"
    coll = client[db_name][coll_name]
    # Mirror the production index spec so race tests exercise the
    # actual storage-layer constraint.
    await coll.create_index(
        [("organization_id", 1), ("email", 1)],
        unique=True,
        partialFilterExpression={"email": {"$type": "string"}},
        name="organization_id_1_email_1",
    )
    try:
        yield coll
    finally:
        try:
            await coll.drop()
        except Exception:
            pass
        client.close()


def _swap_customers_collection(new_coll):
    """Module-level swap so the repository's `customers_collection`
    import points at our isolated test collection. Returns the original
    so the caller can restore."""
    import repositories.customer_repository as cr_mod
    original = cr_mod.customers_collection
    cr_mod.customers_collection = new_coll
    return original


def _restore_customers_collection(original):
    import repositories.customer_repository as cr_mod
    cr_mod.customers_collection = original


class TestUpsertIdempotency:
    """Calling upsert with the same email twice returns the same
    customer_id. This is the core idempotency contract that makes
    storefront re-orders work without creating duplicates."""

    @pytest.mark.asyncio
    async def test_same_email_returns_same_id(self, isolated_customers_collection):
        from repositories.customer_repository import upsert_by_email
        original = _swap_customers_collection(isolated_customers_collection)
        try:
            id1, created1 = await upsert_by_email(
                "org_test", name="Alice", email="alice@foo.com",
            )
            id2, created2 = await upsert_by_email(
                "org_test", name="Alice", email="alice@foo.com",
            )
            assert id1 == id2, "Second upsert should match, not insert"
            assert created1 is True, "First call should be an insert"
            assert created2 is False, "Second call should be an update"
            # Storage-layer assertion: exactly one row in the collection.
            count = await isolated_customers_collection.count_documents(
                {"organization_id": "org_test"}
            )
            assert count == 1

        finally:
            _restore_customers_collection(original)

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self, isolated_customers_collection):
        """`Alice@Foo.COM` and `alice@foo.com` and `  ALICE@FOO.COM  `
        must all converge on the same row — the normalisation contract
        applied before the find_one_and_update filter."""
        from repositories.customer_repository import upsert_by_email
        original = _swap_customers_collection(isolated_customers_collection)
        try:
            id1, _ = await upsert_by_email("org_t", name="A", email="alice@foo.com")
            id2, _ = await upsert_by_email("org_t", name="A", email="ALICE@FOO.COM")
            id3, _ = await upsert_by_email("org_t", name="A", email="  Alice@Foo.com  ")
            assert id1 == id2 == id3
            count = await isolated_customers_collection.count_documents({})
            assert count == 1
        finally:
            _restore_customers_collection(original)

    @pytest.mark.asyncio
    async def test_different_orgs_same_email_separate_rows(
        self, isolated_customers_collection,
    ):
        """The unique constraint is scoped per-org. Two orgs can both
        have a customer with `alice@foo.com` — the partial index keys
        on (organization_id, email) so they don't collide."""
        from repositories.customer_repository import upsert_by_email
        original = _swap_customers_collection(isolated_customers_collection)
        try:
            id_a, _ = await upsert_by_email("org_a", name="A", email="alice@foo.com")
            id_b, _ = await upsert_by_email("org_b", name="A", email="alice@foo.com")
            assert id_a != id_b
            assert await isolated_customers_collection.count_documents({}) == 2
        finally:
            _restore_customers_collection(original)


class TestUpsertUpdateSemantics:
    """The update branch (existing row matched) preserves the
    pre-Phase-4 behaviour of `_find_or_create_customer`:
      - name is overwritten (latest typed value wins)
      - phone is NOT clobbered (stable contact preference)
      - customer_account_id is attached when present-and-not-yet-set"""

    @pytest.mark.asyncio
    async def test_name_overwritten_on_reencounter(
        self, isolated_customers_collection,
    ):
        from repositories.customer_repository import upsert_by_email
        original = _swap_customers_collection(isolated_customers_collection)
        try:
            await upsert_by_email("o", name="Alice", email="x@y.com")
            await upsert_by_email("o", name="Alice Smith", email="x@y.com")
            doc = await isolated_customers_collection.find_one(
                {"organization_id": "o"}, {"_id": 0, "name": 1},
            )
            assert doc["name"] == "Alice Smith"
        finally:
            _restore_customers_collection(original)

    @pytest.mark.asyncio
    async def test_phone_preserved_on_update(
        self, isolated_customers_collection,
    ):
        """Phone is set on insert and intentionally NOT updated on
        re-encounter (admin can change via PATCH /customers/{id})."""
        from repositories.customer_repository import upsert_by_email
        original = _swap_customers_collection(isolated_customers_collection)
        try:
            await upsert_by_email(
                "o", name="A", email="x@y.com", phone="+41791234567",
            )
            # Second call sends a different phone — should be ignored.
            await upsert_by_email(
                "o", name="A", email="x@y.com", phone="+41799999999",
            )
            doc = await isolated_customers_collection.find_one(
                {"organization_id": "o"}, {"_id": 0, "phone": 1},
            )
            assert doc["phone"] == "+41791234567", (
                "Phone was clobbered on update — should be stable"
            )
        finally:
            _restore_customers_collection(original)

    @pytest.mark.asyncio
    async def test_customer_account_id_linked_on_update(
        self, isolated_customers_collection,
    ):
        """Guest checkout, then customer signs up + checks out
        again — the second call's customer_account_id gets attached
        to the existing customer row."""
        from repositories.customer_repository import upsert_by_email
        original = _swap_customers_collection(isolated_customers_collection)
        try:
            await upsert_by_email("o", name="A", email="x@y.com")
            await upsert_by_email(
                "o", name="A", email="x@y.com",
                customer_account_id="acc_123",
            )
            doc = await isolated_customers_collection.find_one(
                {"organization_id": "o"}, {"_id": 0, "customer_account_id": 1},
            )
            assert doc["customer_account_id"] == "acc_123"
        finally:
            _restore_customers_collection(original)


class TestUpsertConcurrencyRaceFix:
    """The motivating bug: simulate the pre-Phase-4 race window with
    high concurrency. All concurrent upserts MUST converge on a
    single customer row and return the same id."""

    @pytest.mark.asyncio
    async def test_concurrent_upserts_converge_to_single_row(
        self, isolated_customers_collection,
    ):
        from repositories.customer_repository import upsert_by_email
        original = _swap_customers_collection(isolated_customers_collection)
        try:
            # Fire 20 concurrent upserts with the same email. In the
            # buggy pre-Phase-4 code, several of these would race past
            # find_one and into insert_one, producing N rows. With the
            # atomic upsert + unique index, exactly one row exists
            # afterwards and all calls return the same id.
            N = 20
            results = await asyncio.gather(*[
                upsert_by_email(
                    "org_race", name=f"Caller{i}", email="race@foo.com",
                )
                for i in range(N)
            ])
            ids = {r[0] for r in results}
            assert len(ids) == 1, (
                f"Concurrent upserts produced {len(ids)} distinct ids — "
                "race condition not fixed."
            )
            count = await isolated_customers_collection.count_documents(
                {"organization_id": "org_race"}
            )
            assert count == 1, (
                f"Found {count} rows after {N} concurrent upserts — "
                "uniqueness index not enforced."
            )
            # Exactly one of the N calls actually inserted.
            insertions = sum(1 for r in results if r[1] is True)
            assert insertions == 1, (
                f"Expected exactly 1 insert across {N} concurrent calls, "
                f"got {insertions}. The was_created flag is unreliable."
            )
        finally:
            _restore_customers_collection(original)


class TestUniqueIndexEnforcement:
    """Storage-layer backstop: a direct insert that bypasses the
    upsert helper must still fail when it would create a duplicate."""

    @pytest.mark.asyncio
    async def test_direct_insert_duplicate_rejected(
        self, isolated_customers_collection,
    ):
        """Plant a customer via upsert, then try a raw insert_one with
        the same (org, email). The unique partial index must reject
        it with DuplicateKey."""
        from pymongo.errors import DuplicateKeyError
        from repositories.customer_repository import upsert_by_email
        original = _swap_customers_collection(isolated_customers_collection)
        try:
            await upsert_by_email("o", name="A", email="x@y.com")
            with pytest.raises(DuplicateKeyError):
                await isolated_customers_collection.insert_one({
                    "id": "duplicate-row",
                    "organization_id": "o",
                    "email": "x@y.com",
                    "name": "B",
                })
        finally:
            _restore_customers_collection(original)

    @pytest.mark.asyncio
    async def test_null_email_rows_dont_collide(
        self, isolated_customers_collection,
    ):
        """POS walk-in customers have `email=None`. The partial filter
        `{email: $type: "string"}` means null-email rows bypass the
        unique constraint — multiple anonymous customers can coexist."""
        await isolated_customers_collection.insert_one({
            "id": "anon-1", "organization_id": "o",
            "email": None, "name": "Walk-in 1",
        })
        await isolated_customers_collection.insert_one({
            "id": "anon-2", "organization_id": "o",
            "email": None, "name": "Walk-in 2",
        })
        await isolated_customers_collection.insert_one({
            "id": "anon-3", "organization_id": "o",
            "name": "Walk-in 3",  # email missing entirely
        })
        count = await isolated_customers_collection.count_documents(
            {"organization_id": "o"}
        )
        assert count == 3, (
            "Anonymous customers (null/missing email) should not collide "
            "on the unique partial index."
        )


class TestDuplicateCheckScript:
    """The pre-deployment duplicate-detection script must classify
    a clean collection as safe and a polluted one as blocked."""

    @pytest.mark.asyncio
    async def test_finds_planted_duplicate(
        self, isolated_customers_collection,
    ):
        """Plant a duplicate that bypasses the index (use a collection
        WITHOUT the index for this test), then verify the script
        detects it."""
        # Drop the unique index so we can plant duplicates for testing
        await isolated_customers_collection.drop_index("organization_id_1_email_1")
        await isolated_customers_collection.insert_many([
            {"id": "a1", "organization_id": "o", "email": "dup@x.com", "name": "A"},
            {"id": "a2", "organization_id": "o", "email": "dup@x.com", "name": "B"},
        ])
        from scripts.check_customer_email_duplicates import _find_duplicates
        import database as db_mod
        original = db_mod.customers_collection
        db_mod.customers_collection = isolated_customers_collection
        try:
            dups = await _find_duplicates()
            assert len(dups) == 1
            assert dups[0]["count"] == 2
            assert set(dups[0]["ids"]) == {"a1", "a2"}
        finally:
            db_mod.customers_collection = original

    @pytest.mark.asyncio
    async def test_clean_collection_reports_zero(
        self, isolated_customers_collection,
    ):
        from scripts.check_customer_email_duplicates import _find_duplicates
        import database as db_mod
        original = db_mod.customers_collection
        db_mod.customers_collection = isolated_customers_collection
        try:
            dups = await _find_duplicates()
            assert dups == []
        finally:
            db_mod.customers_collection = original
