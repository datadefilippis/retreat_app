"""Sentinel tests for customer-insights admin visibility extension.

Pins the contract introduced by the CI-admin-vis change:
  - ``build_customer_list`` enriches each row with has_account,
    marketing_opted_in, account_created_at — derived from a real-time
    join against customer_accounts.
  - Two new filters (has_account, marketing_opted_in) wired through.
  - CSV export includes the three new columns (appended at the END so
    legacy positional consumers keep working).
  - Edge cases: guest customer (no account FK), revoked-then-re-opted-in,
    legacy customer FK pointing to a missing account.
  - Backward-compat: passing has_account=None and marketing_opted_in=None
    yields the same set of rows as before the change.
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


# ── Fixtures ────────────────────────────────────────────────────────


def _metric(customer_id: str, **extra) -> dict:
    """Mock row from customer_metrics materialised view."""
    base = {
        "customer_id": customer_id,
        "customer_name": f"Customer {customer_id}",
        "segment": "active",
        "customer_status": "healthy",
        "total_revenue": 100.0,
        "transaction_count": 2,
        "last_purchase_date": "2026-05-01T00:00:00+00:00",
        "days_since_last_purchase": 18,
        "churn_risk_score": 0.2,
        "trend_direction": "stable",
    }
    base.update(extra)
    return base


class _FakeCustomer:
    """Mock Customer model with the attribute shape build_customer_list reads."""

    def __init__(self, id, email=None, phone=None, customer_account_id=None):
        self.id = id
        self.email = email
        self.phone = phone
        self.customer_account_id = customer_account_id


class _FakeAccountsCursor:
    """Mimic motor cursor + async iteration."""

    def __init__(self, docs):
        self._docs = list(docs)

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


def _patch_service_dependencies(*, metrics, customers, accounts):
    """Context manager bundle — patches the three real-time data sources
    that ``build_customer_list`` consults."""
    accounts_collection_mock = AsyncMock()
    accounts_collection_mock.find = lambda *a, **kw: _FakeAccountsCursor(accounts)

    return (
        patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new=AsyncMock(return_value=metrics),
        ),
        patch(
            "repositories.customer_repository.find_by_org",
            new=AsyncMock(return_value=customers),
        ),
        patch(
            "database.customer_accounts_collection",
            new=accounts_collection_mock,
        ),
    )


async def _call_list(**kwargs):
    """Helper: invoke build_customer_list with sane defaults."""
    from modules.customer_insights.service import build_customer_list
    return await build_customer_list(
        kwargs.pop("org_id", "org-1"),
        **kwargs,
    )


# ── Row enrichment ─────────────────────────────────────────────────


class TestRowEnrichment:
    """Each returned row carries the 3 new fields with correctly
    derived values for the registered / guest / revoked cases."""

    @pytest.mark.asyncio
    async def test_registered_opted_in_customer(self):
        metrics = [_metric("c-1")]
        customers = [_FakeCustomer("c-1", email="a@b.com", customer_account_id="acc-1")]
        accounts = [{
            "id": "acc-1",
            "created_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
            "accepted_marketing_at": "2026-01-15T10:00:00+00:00",
            "marketing_revoked_at": None,
        }]

        p1, p2, p3 = _patch_service_dependencies(
            metrics=metrics, customers=customers, accounts=accounts,
        )
        with p1, p2, p3:
            res = await _call_list()

        assert len(res["rows"]) == 1
        row = res["rows"][0]
        assert row["has_account"] is True
        assert row["marketing_opted_in"] is True
        assert row["account_created_at"] == "2026-01-15T00:00:00+00:00"

    @pytest.mark.asyncio
    async def test_registered_never_opted_in(self):
        metrics = [_metric("c-1")]
        customers = [_FakeCustomer("c-1", customer_account_id="acc-1")]
        accounts = [{
            "id": "acc-1",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "accepted_marketing_at": None,
            "marketing_revoked_at": None,
        }]
        p1, p2, p3 = _patch_service_dependencies(
            metrics=metrics, customers=customers, accounts=accounts,
        )
        with p1, p2, p3:
            res = await _call_list()
        row = res["rows"][0]
        assert row["has_account"] is True
        assert row["marketing_opted_in"] is False

    @pytest.mark.asyncio
    async def test_registered_opted_in_then_revoked(self):
        """Revoked after opt-in → final state is opted-out."""
        metrics = [_metric("c-1")]
        customers = [_FakeCustomer("c-1", customer_account_id="acc-1")]
        accounts = [{
            "id": "acc-1",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "accepted_marketing_at": "2026-02-01T10:00:00+00:00",
            "marketing_revoked_at": "2026-03-01T10:00:00+00:00",  # revoked after
        }]
        p1, p2, p3 = _patch_service_dependencies(
            metrics=metrics, customers=customers, accounts=accounts,
        )
        with p1, p2, p3:
            res = await _call_list()
        row = res["rows"][0]
        assert row["marketing_opted_in"] is False

    @pytest.mark.asyncio
    async def test_revoked_then_re_opted_in(self):
        """Revoke first, then a fresh opt-in → final state is opted-in.
        Edge case for users who change their mind."""
        metrics = [_metric("c-1")]
        customers = [_FakeCustomer("c-1", customer_account_id="acc-1")]
        accounts = [{
            "id": "acc-1",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "accepted_marketing_at": "2026-04-01T10:00:00+00:00",  # newer
            "marketing_revoked_at": "2026-03-01T10:00:00+00:00",   # older
        }]
        p1, p2, p3 = _patch_service_dependencies(
            metrics=metrics, customers=customers, accounts=accounts,
        )
        with p1, p2, p3:
            res = await _call_list()
        row = res["rows"][0]
        assert row["marketing_opted_in"] is True

    @pytest.mark.asyncio
    async def test_guest_customer_no_account(self):
        """A guest customer has no customer_account_id FK at all.
        Returned row must surface has_account=False and never crash
        on a None lookup."""
        metrics = [_metric("c-guest")]
        customers = [_FakeCustomer("c-guest", email="guest@x.com", customer_account_id=None)]
        accounts = []  # no accounts exist
        p1, p2, p3 = _patch_service_dependencies(
            metrics=metrics, customers=customers, accounts=accounts,
        )
        with p1, p2, p3:
            res = await _call_list()
        row = res["rows"][0]
        assert row["has_account"] is False
        assert row["marketing_opted_in"] is False
        assert row["account_created_at"] is None

    @pytest.mark.asyncio
    async def test_legacy_fk_to_missing_account(self):
        """FK present but the linked customer_account doc no longer
        exists (data drift) — treat as guest, don't crash."""
        metrics = [_metric("c-1")]
        customers = [_FakeCustomer("c-1", customer_account_id="acc-deleted")]
        accounts = []  # FK target missing
        p1, p2, p3 = _patch_service_dependencies(
            metrics=metrics, customers=customers, accounts=accounts,
        )
        with p1, p2, p3:
            res = await _call_list()
        row = res["rows"][0]
        assert row["has_account"] is False
        assert row["marketing_opted_in"] is False


# ── New filters ────────────────────────────────────────────────────


class TestFilters:
    """The two new filter params correctly narrow the result set."""

    @pytest.mark.asyncio
    async def test_has_account_true_returns_only_registered(self):
        metrics = [_metric("c-acc"), _metric("c-guest")]
        customers = [
            _FakeCustomer("c-acc", customer_account_id="acc-1"),
            _FakeCustomer("c-guest", customer_account_id=None),
        ]
        accounts = [{
            "id": "acc-1",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "accepted_marketing_at": None,
            "marketing_revoked_at": None,
        }]
        p1, p2, p3 = _patch_service_dependencies(
            metrics=metrics, customers=customers, accounts=accounts,
        )
        with p1, p2, p3:
            res = await _call_list(has_account=True)
        assert {r["customer_id"] for r in res["rows"]} == {"c-acc"}

    @pytest.mark.asyncio
    async def test_has_account_false_returns_only_guests(self):
        metrics = [_metric("c-acc"), _metric("c-guest")]
        customers = [
            _FakeCustomer("c-acc", customer_account_id="acc-1"),
            _FakeCustomer("c-guest", customer_account_id=None),
        ]
        accounts = [{
            "id": "acc-1",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "accepted_marketing_at": None,
            "marketing_revoked_at": None,
        }]
        p1, p2, p3 = _patch_service_dependencies(
            metrics=metrics, customers=customers, accounts=accounts,
        )
        with p1, p2, p3:
            res = await _call_list(has_account=False)
        assert {r["customer_id"] for r in res["rows"]} == {"c-guest"}

    @pytest.mark.asyncio
    async def test_marketing_opted_in_true_excludes_non_opted(self):
        metrics = [_metric("c-yes"), _metric("c-no"), _metric("c-guest")]
        customers = [
            _FakeCustomer("c-yes", customer_account_id="acc-yes"),
            _FakeCustomer("c-no", customer_account_id="acc-no"),
            _FakeCustomer("c-guest", customer_account_id=None),
        ]
        accounts = [
            {
                "id": "acc-yes",
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "accepted_marketing_at": "2026-01-01T00:00:00+00:00",
                "marketing_revoked_at": None,
            },
            {
                "id": "acc-no",
                "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "accepted_marketing_at": None,
                "marketing_revoked_at": None,
            },
        ]
        p1, p2, p3 = _patch_service_dependencies(
            metrics=metrics, customers=customers, accounts=accounts,
        )
        with p1, p2, p3:
            res = await _call_list(marketing_opted_in=True)
        assert {r["customer_id"] for r in res["rows"]} == {"c-yes"}

    @pytest.mark.asyncio
    async def test_filters_default_none_preserves_all_rows(self):
        """Backward-compat: with both new filters None, no row is
        excluded by them."""
        metrics = [_metric("c-acc"), _metric("c-guest")]
        customers = [
            _FakeCustomer("c-acc", customer_account_id="acc-1"),
            _FakeCustomer("c-guest", customer_account_id=None),
        ]
        accounts = [{
            "id": "acc-1",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "accepted_marketing_at": None,
            "marketing_revoked_at": None,
        }]
        p1, p2, p3 = _patch_service_dependencies(
            metrics=metrics, customers=customers, accounts=accounts,
        )
        with p1, p2, p3:
            res = await _call_list()  # no filters
        assert {r["customer_id"] for r in res["rows"]} == {"c-acc", "c-guest"}


# ── Resilience ─────────────────────────────────────────────────────


class TestResilience:
    """Account lookup failures must NOT poison the customer list —
    they degrade to ``has_account=False`` per row."""

    @pytest.mark.asyncio
    async def test_account_lookup_failure_is_soft(self):
        from modules.customer_insights.service import build_customer_list

        metrics = [_metric("c-1")]
        customers = [_FakeCustomer("c-1", customer_account_id="acc-1")]

        # Simulate a Mongo hiccup on the bulk account fetch.
        broken_collection = AsyncMock()
        broken_collection.find = AsyncMock(side_effect=RuntimeError("boom"))

        with patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new=AsyncMock(return_value=metrics),
        ), patch(
            "repositories.customer_repository.find_by_org",
            new=AsyncMock(return_value=customers),
        ), patch(
            "database.customer_accounts_collection",
            new=broken_collection,
        ):
            res = await build_customer_list("org-1")

        # The list still renders, just without the visibility.
        assert len(res["rows"]) == 1
        assert res["rows"][0]["has_account"] is False


# ── CSV columns ────────────────────────────────────────────────────


class TestCsvColumns:
    """The 3 new fields are present near the END of ``_CSV_COLUMNS`` so
    existing positional consumers keep working unchanged.

    Wave GDPR-Commerce Piece 1b (2026-05-19) appended a FOURTH column
    (``unsubscribe_url``) AFTER these three — see the dedicated CI-admin-vis
    + Piece 1b sentinel in test_wave_gdpr_commerce_piece1b_unsubscribe.py.
    The contract this test pins is "the 3 CI-admin-vis fields are
    contiguous and live near the end", not "they are the absolute last
    three" (which would couple this sentinel to every future append).
    """

    def test_new_columns_appended(self):
        from modules.customer_insights.router import _CSV_COLUMNS
        assert _CSV_COLUMNS[-4:-1] == [
            "has_account",
            "marketing_opted_in",
            "account_created_at",
        ]

    def test_legacy_columns_unchanged(self):
        """The first 12 columns (legacy contract) are in the same order."""
        from modules.customer_insights.router import _CSV_COLUMNS
        legacy = [
            "customer_id", "customer_name", "email", "phone",
            "segment", "customer_status", "total_revenue",
            "transaction_count", "last_purchase_date",
            "days_since_last_purchase", "churn_risk_score",
            "trend_direction",
        ]
        assert _CSV_COLUMNS[: len(legacy)] == legacy
