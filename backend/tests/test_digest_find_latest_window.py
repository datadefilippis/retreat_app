"""Tests for Wave 13.7 — digest_repository.find_latest window filters.

The Wave 13 audit (BUG #10) found that ``find_latest`` matched only on
``(org_id, digest_type)``, so two monthly digests covering different
windows (e.g. Mar 1-31 vs Apr 1-30) were indistinguishable for the
24h dedup and the UI's "featured digest" selector.

Phase 13.7 added optional ``period_start`` / ``period_end`` kwargs.
This test verifies:
  - Backward compat: unscoped calls behave as before.
  - New behaviour: window-scoped calls filter MongoDB correctly.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _make_cursor(docs):
    """Build a stub that mimics the motor cursor chain
    ``find(...).sort(...).limit(...).to_list(...)``."""
    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=docs)
    return cursor


@pytest.mark.asyncio
class TestFindLatestBackwardCompat:
    async def test_no_kwargs_matches_org_and_type_only(self):
        """Pre-Wave-13.7 callers must keep working without changes."""
        from repositories import digest_repository

        captured_query = {}

        def _fake_find(query, *_args, **_kwargs):
            captured_query.update(query)
            return _make_cursor([{
                "id": "d1", "organization_id": "org_1",
                "digest_type": "weekly", "content": "",
                "period_start": "2026-04-25", "period_end": "2026-05-02",
                "created_at": "2026-05-02T10:00:00",
            }])

        with patch(
            "repositories.digest_repository.digests_collection",
            MagicMock(find=MagicMock(side_effect=_fake_find)),
        ):
            doc = await digest_repository.find_latest("org_1", "weekly")

        assert doc is not None
        # Query carries ONLY org_id + digest_type — no period filter
        assert captured_query == {
            "organization_id": "org_1",
            "digest_type": "weekly",
        }


@pytest.mark.asyncio
class TestFindLatestWindowScoped:
    async def test_period_start_added_to_query(self):
        from repositories import digest_repository

        captured_query = {}

        def _fake_find(query, *_args, **_kwargs):
            captured_query.update(query)
            return _make_cursor([])

        with patch(
            "repositories.digest_repository.digests_collection",
            MagicMock(find=MagicMock(side_effect=_fake_find)),
        ):
            await digest_repository.find_latest(
                "org_1", "monthly", period_start="2026-04-01",
            )

        assert captured_query == {
            "organization_id": "org_1",
            "digest_type": "monthly",
            "period_start": "2026-04-01",
        }

    async def test_both_window_bounds_added_to_query(self):
        from repositories import digest_repository

        captured_query = {}

        def _fake_find(query, *_args, **_kwargs):
            captured_query.update(query)
            return _make_cursor([])

        with patch(
            "repositories.digest_repository.digests_collection",
            MagicMock(find=MagicMock(side_effect=_fake_find)),
        ):
            await digest_repository.find_latest(
                "org_1", "monthly",
                period_start="2026-04-01",
                period_end="2026-04-30",
            )

        # Both bounds in the query — Mongo returns ONLY the digest with
        # that exact window, not just any monthly.
        assert captured_query == {
            "organization_id": "org_1",
            "digest_type": "monthly",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        }

    async def test_window_mismatch_returns_none(self):
        """If no digest matches the window, returns None (not the
        latest of the same type as pre-13.7)."""
        from repositories import digest_repository

        # MongoDB stub returns NO docs for the window-specific query
        with patch(
            "repositories.digest_repository.digests_collection",
            MagicMock(find=MagicMock(return_value=_make_cursor([]))),
        ):
            doc = await digest_repository.find_latest(
                "org_1", "monthly",
                period_start="2099-01-01",
                period_end="2099-01-31",
            )

        assert doc is None

    async def test_only_period_end_works(self):
        """The kwargs are independent — passing only period_end is
        valid (uncommon but supported)."""
        from repositories import digest_repository

        captured_query = {}

        def _fake_find(query, *_args, **_kwargs):
            captured_query.update(query)
            return _make_cursor([])

        with patch(
            "repositories.digest_repository.digests_collection",
            MagicMock(find=MagicMock(side_effect=_fake_find)),
        ):
            await digest_repository.find_latest(
                "org_1", "weekly", period_end="2026-05-02",
            )

        assert captured_query == {
            "organization_id": "org_1",
            "digest_type": "weekly",
            "period_end": "2026-05-02",
        }
