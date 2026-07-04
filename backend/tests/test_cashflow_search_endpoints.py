"""Sentinel tests for the cashflow `/search` endpoints (Phase 2,
2026-05-20).

Background
==========
Phase 2 of the cashflow refactor introduces paginated + server-filtered
endpoints ALONGSIDE the existing list endpoints (which stay byte-for-byte
identical for backward compat):

    GET /api/sales      → List[record]              (legacy, unchanged)
    GET /api/sales/search?…&page=K&page_size=P
                        → {items, total, page, page_size, has_more}

Same for ``/api/expenses/search`` and ``/api/purchases/search``.

Sentinel invariants
-------------------
  1. Response envelope shape is ``{items, total, page, page_size,
     has_more}`` — frontend pagination + total counter depend on it.
  2. CSV multi-value params (categories, channels, …) parse into a list.
     Empty CSV (``categories=``) maps to None → "no filter".
  3. ``source`` accepts only ``manual|file`` (FastAPI ``pattern``).
  4. ``page_size`` capped at 200, ``page`` at 10k, ``q`` at 100 chars.
  5. Free-text ``q`` is regex-escaped at the repository layer — a hostile
     input like ``(a+)+`` becomes a literal substring search, not a
     catastrophic-backtracking pattern.
  6. The repository receives ``organization_id`` from ``current_user`` —
     tenant isolation invariant preserved.
  7. The legacy ``list`` endpoint signature is untouched (re-asserts the
     Phase 1 sentinels — Phase 2 must not regress them).

These are pure contract tests — no DB hit, no auth roundtrip. The
repository layer is mocked.
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


def _user(org_id: str = "org-A") -> dict:
    """Minimal current_user stub the verified_user dependency yields."""
    return {"id": "user-1", "organization_id": org_id, "role": "owner"}


def _envelope(items=None, total=0, page=1, page_size=50, has_more=False):
    """Build a canonical response envelope — used to mock the repository."""
    return {
        "items": items or [],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": has_more,
    }


# ─── CSV helper ──────────────────────────────────────────────────────────


class TestCsvHelper:
    """The CSV → list helper is shared by all three /search endpoints and
    drives every multi-value filter. Sentinel-pin its behaviour so a
    future "we should support quoted values" refactor doesn't silently
    change the semantics of every cashflow filter at once."""

    def test_empty_string_returns_none(self):
        from routers.sales import _csv_to_list
        assert _csv_to_list("") is None
        assert _csv_to_list(None) is None

    def test_single_value(self):
        from routers.sales import _csv_to_list
        assert _csv_to_list("A") == ["A"]

    def test_multi_value_with_spaces(self):
        from routers.sales import _csv_to_list
        assert _csv_to_list("A, B,C  ") == ["A", "B", "C"]

    def test_all_empty_tokens_returns_none(self):
        # ``categories=,,,`` (a stale param the UI accidentally sends)
        # must collapse to None, never to [""] — an "$in: ['']" filter
        # would match nothing and confuse the merchant.
        from routers.sales import _csv_to_list
        assert _csv_to_list(",,,") is None

    def test_purchases_iva_float_csv(self):
        from routers.purchases import _csv_to_float_list
        assert _csv_to_float_list("0,4,10,22") == [0.0, 4.0, 10.0, 22.0]

    def test_purchases_iva_skips_garbage(self):
        from routers.purchases import _csv_to_float_list
        # "abc" silently dropped — see comment in the helper.
        assert _csv_to_float_list("4,abc,22") == [4.0, 22.0]
        assert _csv_to_float_list("abc") is None


# ─── Route signature / contract sentinels ───────────────────────────────


def _inspect_query_default(route_fn, param_name):
    """Return the FastAPI Query() default object for a route parameter.

    Returns None when the param has no Query(…) default (typed-only
    Optional[X] with no default value).
    """
    import inspect
    sig = inspect.signature(route_fn)
    p = sig.parameters.get(param_name)
    if p is None:
        return None
    return p.default


class TestSalesSearchContract:
    def test_endpoint_exists(self):
        from routers.sales import search_sales
        assert callable(search_sales)

    def test_page_size_capped_at_200(self):
        from routers.sales import search_sales
        d = _inspect_query_default(search_sales, "page_size")
        assert d is not None
        le_value = None
        for c in getattr(d, "metadata", []) or []:
            if hasattr(c, "le"):
                le_value = c.le
        assert le_value == 200, (
            "page_size cap protects against payload bloat — see "
            "/search docstring. Raising it requires updating both the "
            "client (CashflowPagination component) and this sentinel."
        )

    def test_page_capped_at_10000(self):
        from routers.sales import search_sales
        d = _inspect_query_default(search_sales, "page")
        le_value = None
        for c in getattr(d, "metadata", []) or []:
            if hasattr(c, "le"):
                le_value = c.le
        assert le_value == 10000

    def test_q_max_length_100(self):
        from routers.sales import search_sales
        d = _inspect_query_default(search_sales, "q")
        max_length = None
        for c in getattr(d, "metadata", []) or []:
            if hasattr(c, "max_length"):
                max_length = c.max_length
        assert max_length == 100, (
            "q cap protects against huge regex inputs even after "
            "escaping. Both are defence-in-depth."
        )

    def test_source_pattern_enum(self):
        from routers.sales import search_sales
        d = _inspect_query_default(search_sales, "source")
        # FastAPI stores regex pattern on the Query default's metadata.
        pattern = None
        for c in getattr(d, "metadata", []) or []:
            if hasattr(c, "pattern"):
                pattern = c.pattern
        assert pattern is not None
        assert "manual" in pattern and "file" in pattern


class TestExpensesSearchContract:
    def test_endpoint_exists(self):
        from routers.expenses import search_expenses
        assert callable(search_expenses)

    def test_page_size_capped_at_200(self):
        from routers.expenses import search_expenses
        d = _inspect_query_default(search_expenses, "page_size")
        le_value = None
        for c in getattr(d, "metadata", []) or []:
            if hasattr(c, "le"):
                le_value = c.le
        assert le_value == 200


class TestPurchasesSearchContract:
    def test_endpoint_exists(self):
        from routers.purchases import search_purchases
        assert callable(search_purchases)

    def test_page_size_capped_at_200(self):
        from routers.purchases import search_purchases
        d = _inspect_query_default(search_purchases, "page_size")
        le_value = None
        for c in getattr(d, "metadata", []) or []:
            if hasattr(c, "le"):
                le_value = c.le
        assert le_value == 200

    def test_has_iva_filter_param(self):
        """Purchases is the only collection with an ``iva`` field —
        guard against an accidental rename / removal that would silently
        break the IVA filter chip in the popup."""
        import inspect
        from routers.purchases import search_purchases
        sig = inspect.signature(search_purchases)
        assert "iva_values" in sig.parameters


# ─── End-to-end behaviour (mocked repository) ───────────────────────────


class TestSearchEndpointWiring:
    """Drive the route function directly with a mocked repository.
    Verifies the route forwards every param into the right kwarg, parses
    CSV correctly, and yields the envelope unchanged. This is the
    'no-DB' equivalent of a TestClient test."""

    @pytest.mark.asyncio
    async def test_sales_forwards_org_id_and_filters(self):
        from routers.sales import search_sales

        mock_repo = AsyncMock(return_value=_envelope(items=[{"id": "s1"}], total=1))
        with patch("repositories.sales_repository.find_paginated", mock_repo):
            result = await search_sales(
                date_from="2024-01-01",
                date_to="2024-12-31",
                categories="Food,Tech",
                channels="online,store",
                payment_status="paid,pending",
                source="manual",
                amount_min=10.0,
                amount_max=1000.0,
                q="acme",
                page=2,
                page_size=25,
                current_user=_user("org-X"),
            )

        # Envelope passes through unchanged.
        assert result["total"] == 1
        assert result["items"][0]["id"] == "s1"

        # Repository called once with the right kwargs.
        mock_repo.assert_awaited_once()
        kwargs = mock_repo.await_args.kwargs
        assert mock_repo.await_args.args[0] == "org-X"
        assert kwargs["date_from"] == "2024-01-01"
        assert kwargs["categories"] == ["Food", "Tech"]
        assert kwargs["channels"] == ["online", "store"]
        assert kwargs["payment_status"] == ["paid", "pending"]
        assert kwargs["source"] == "manual"
        assert kwargs["amount_min"] == 10.0
        assert kwargs["q"] == "acme"
        assert kwargs["page"] == 2
        assert kwargs["page_size"] == 25

    @pytest.mark.asyncio
    async def test_expenses_forwards_supplier_filters(self):
        from routers.expenses import search_expenses

        mock_repo = AsyncMock(return_value=_envelope())
        with patch("repositories.expenses_repository.find_paginated", mock_repo):
            await search_expenses(
                suppliers="Acme,Beta",
                supplier_ids="sup-1,sup-2",
                current_user=_user("org-Y"),
            )

        kwargs = mock_repo.await_args.kwargs
        assert mock_repo.await_args.args[0] == "org-Y"
        assert kwargs["suppliers"] == ["Acme", "Beta"]
        assert kwargs["supplier_ids"] == ["sup-1", "sup-2"]

    @pytest.mark.asyncio
    async def test_purchases_forwards_iva_csv(self):
        from routers.purchases import search_purchases

        mock_repo = AsyncMock(return_value=_envelope())
        with patch("repositories.purchase_repository.find_paginated", mock_repo):
            await search_purchases(
                iva_values="4,22",
                units="kg,pezzi",
                current_user=_user("org-Z"),
            )

        kwargs = mock_repo.await_args.kwargs
        assert kwargs["iva_values"] == [4.0, 22.0]
        assert kwargs["units"] == ["kg", "pezzi"]


# ─── Repository-layer ReDoS guard ───────────────────────────────────────


class TestRegexEscapeInRepository:
    """The free-text ``q`` parameter goes into a Mongo $regex match. A
    naive ``{"$regex": q}`` is a ReDoS vector — a hostile user typing
    ``(a+)+$`` on a 100k-row collection makes the DB spin. The repo
    layer calls ``re.escape(q)`` so the regex degrades to a literal
    substring search.

    This sentinel verifies the escape is in place by checking that the
    Mongo query built for a metacharacter-laden input does NOT contain
    the metacharacters in their special form."""

    @pytest.mark.asyncio
    async def test_sales_q_is_regex_escaped(self):
        from repositories import sales_repository

        captured = {}

        class _FakeCursor:
            def sort(self, *a, **kw): return self
            def skip(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            async def to_list(self, n): return []

        async def fake_count(match, **kw):
            captured["match"] = match
            return 0

        def fake_find(match, *a, **kw):
            captured["match"] = match
            return _FakeCursor()

        with patch.object(
            sales_repository.sales_records_collection,
            "count_documents",
            new=fake_count,
        ), patch.object(
            sales_repository.sales_records_collection,
            "find",
            new=fake_find,
        ):
            await sales_repository.find_paginated(
                "org-X",
                q="(a+)+$",
            )

        # The regex string in the Mongo match must NOT contain raw
        # metacharacters — they must be backslash-escaped.
        rgx = captured["match"]["description"]["$regex"]
        assert "\\(" in rgx or "(" not in rgx  # paren escaped
        assert "\\+" in rgx                    # plus escaped
        # And the original hostile string is no longer regex-active.
        import re as _re
        assert _re.compile(rgx)  # never raises

    @pytest.mark.asyncio
    async def test_purchases_q_searches_description_or_invoice(self):
        """Purchases is special: ``q`` ORs over description AND
        invoice_number (single search box, two fields). Pin that shape."""
        from repositories import purchase_repository

        captured = {}

        class _FakeCursor:
            def sort(self, *a, **kw): return self
            def skip(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            async def to_list(self, n): return []

        async def fake_count(match, **kw):
            captured["match"] = match
            return 0

        def fake_find(match, *a, **kw):
            return _FakeCursor()

        with patch.object(
            purchase_repository.purchase_records_collection,
            "count_documents",
            new=fake_count,
        ), patch.object(
            purchase_repository.purchase_records_collection,
            "find",
            new=fake_find,
        ):
            await purchase_repository.find_paginated("org-X", q="FT2024")

        assert "$or" in captured["match"]
        fields = {list(clause.keys())[0] for clause in captured["match"]["$or"]}
        assert fields == {"description", "invoice_number"}


# ─── Tenant isolation invariant ─────────────────────────────────────────


class TestTenantIsolation:
    """All three repository methods MUST scope by organization_id. A
    regression that drops the scope = catastrophic cross-tenant leak."""

    @pytest.mark.asyncio
    async def test_sales_match_includes_org_id(self):
        from repositories import sales_repository
        captured = {}

        class _FakeCursor:
            def sort(self, *a, **kw): return self
            def skip(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            async def to_list(self, n): return []

        async def fake_count(match, **kw):
            captured["match"] = match
            return 0

        def fake_find(match, *a, **kw):
            return _FakeCursor()

        with patch.object(sales_repository.sales_records_collection,
                          "count_documents", new=fake_count), \
             patch.object(sales_repository.sales_records_collection,
                          "find", new=fake_find):
            await sales_repository.find_paginated("org-secret")

        assert captured["match"]["organization_id"] == "org-secret"

    @pytest.mark.asyncio
    async def test_expenses_match_includes_org_id(self):
        from repositories import expenses_repository
        captured = {}

        class _FakeCursor:
            def sort(self, *a, **kw): return self
            def skip(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            async def to_list(self, n): return []

        async def fake_count(match, **kw):
            captured["match"] = match
            return 0

        def fake_find(match, *a, **kw):
            return _FakeCursor()

        with patch.object(expenses_repository.expense_records_collection,
                          "count_documents", new=fake_count), \
             patch.object(expenses_repository.expense_records_collection,
                          "find", new=fake_find):
            await expenses_repository.find_paginated("org-X")

        assert captured["match"]["organization_id"] == "org-X"

    @pytest.mark.asyncio
    async def test_purchases_match_includes_org_id(self):
        from repositories import purchase_repository
        captured = {}

        class _FakeCursor:
            def sort(self, *a, **kw): return self
            def skip(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            async def to_list(self, n): return []

        async def fake_count(match, **kw):
            captured["match"] = match
            return 0

        def fake_find(match, *a, **kw):
            return _FakeCursor()

        with patch.object(purchase_repository.purchase_records_collection,
                          "count_documents", new=fake_count), \
             patch.object(purchase_repository.purchase_records_collection,
                          "find", new=fake_find):
            await purchase_repository.find_paginated("org-Z")

        assert captured["match"]["organization_id"] == "org-Z"


# ─── Pagination stability (secondary sort key) ──────────────────────────


class TestPaginationStability:
    """Skip-based pagination requires a STABLE sort order. Two records
    with the same primary key (``date``) must have a deterministic
    secondary tiebreaker, otherwise the same row can appear on two
    different pages (or none at all) under concurrent writes."""

    @pytest.mark.asyncio
    async def test_sales_sort_has_secondary_key(self):
        from repositories import sales_repository
        captured = {}

        class _FakeCursor:
            def sort(self, sort_list, *a, **kw):
                captured["sort"] = sort_list
                return self
            def skip(self, *a, **kw): return self
            def limit(self, *a, **kw): return self
            async def to_list(self, n): return []

        async def fake_count(*a, **kw): return 0
        def fake_find(*a, **kw): return _FakeCursor()

        with patch.object(sales_repository.sales_records_collection,
                          "count_documents", new=fake_count), \
             patch.object(sales_repository.sales_records_collection,
                          "find", new=fake_find):
            await sales_repository.find_paginated("org-X")

        sort_list = captured["sort"]
        # Two-element sort = (primary, secondary). The secondary on
        # ``id`` (a UUID) gives a deterministic tiebreaker even when
        # dates collide.
        assert len(sort_list) == 2
        assert sort_list[0][0] == "date"
        assert sort_list[1][0] == "id"


# ─── Phase-1 sentinels re-asserted (must not regress) ───────────────────


class TestLegacyListEndpointsUnchanged:
    """Phase 2 must NOT change the legacy ``list_*`` endpoint signatures —
    they're consumed by dashboard widgets + analytics call sites that
    expect the bare-array response shape."""

    def test_legacy_sales_list_still_capped_at_5000(self):
        import inspect
        from routers.sales import list_sales
        sig = inspect.signature(list_sales)
        limit_default = sig.parameters["limit"].default
        le_value = None
        for c in getattr(limit_default, "metadata", []) or []:
            if hasattr(c, "le"):
                le_value = c.le
        assert le_value == 5000
        assert limit_default.default == 500

    def test_legacy_expenses_list_still_capped_at_5000(self):
        import inspect
        from routers.expenses import list_expenses
        sig = inspect.signature(list_expenses)
        limit_default = sig.parameters["limit"].default
        le_value = None
        for c in getattr(limit_default, "metadata", []) or []:
            if hasattr(c, "le"):
                le_value = c.le
        assert le_value == 5000

    def test_legacy_purchases_list_still_capped_at_5000(self):
        import inspect
        from routers.purchases import list_purchases
        sig = inspect.signature(list_purchases)
        limit_default = sig.parameters["limit"].default
        le_value = None
        for c in getattr(limit_default, "metadata", []) or []:
            if hasattr(c, "le"):
                le_value = c.le
        assert le_value == 5000
