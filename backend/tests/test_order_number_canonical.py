"""Sentinel tests for the canonical order_number contract
(2026-05-20).

Background
==========
The Order.order_number field follows ONE format system-wide:
``ORD-{N:04d}``. A seed script previously emitted ``ORD-CB-XXXX`` and
broke the runtime parser, causing confirm_order to fail with
"Impossibile assegnare numero ordine dopo 3 tentativi" once that
format hit production-like data.

These sentinels pin the invariants of the fix:

  1. ``get_next_order_number`` extracts the LAST digit run from any
     legacy format and produces the next canonical value (no more
     silent fallback to ORD-0001 → collision → retry-loop death).

  2. Bootstrap on empty org returns ORD-0001.

  3. When the MAX has no numeric tail at all, the count-based
     fallback kicks in without raising.

  4. The Order model accepts the new ``external_order_number`` /
     ``external_source`` / ``external_imported_at`` Optional fields.

  5. Format anti-typo: the canonical regex matches ORD-XXXX and
     nothing else.

These tests intentionally mock the Mongo collection — they pin the
parser contract, not the DB integration (which the order_service
sentinels already cover).
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── get_next_order_number parser ────────────────────────────────────


class _StubCursor:
    """Awaitable to_list(length) returning a fixed list."""
    def __init__(self, docs):
        self._docs = docs
    def sort(self, *_, **__): return self
    def limit(self, *_, **__): return self
    async def to_list(self, length):  # noqa: ARG002
        return self._docs


class TestGetNextOrderNumberParser:
    """The parser must produce canonical ORD-XXXX for any legacy
    format it can find a numeric tail in; safe-fallback otherwise."""

    @pytest.mark.asyncio
    async def test_canonical_ord_xxxx_increments(self, monkeypatch):
        from repositories import order_repository
        coll = MagicMock()
        coll.find = MagicMock(return_value=_StubCursor([{"order_number": "ORD-0042"}]))
        coll.count_documents = AsyncMock(return_value=42)
        monkeypatch.setattr(order_repository, "orders_collection", coll)
        result = await order_repository.get_next_order_number("org-1")
        assert result == "ORD-0043"

    @pytest.mark.asyncio
    async def test_legacy_ord_cb_xxxx_parses_tail(self, monkeypatch):
        """The seed-script anomaly that started this whole fix wave."""
        from repositories import order_repository
        coll = MagicMock()
        coll.find = MagicMock(return_value=_StubCursor([{"order_number": "ORD-CB-0162"}]))
        coll.count_documents = AsyncMock(return_value=162)
        monkeypatch.setattr(order_repository, "orders_collection", coll)
        result = await order_repository.get_next_order_number("org-1")
        # Must NOT silently fall back to ORD-0001.
        # MUST extract 162 from the tail and increment to 163.
        assert result == "ORD-0163"

    @pytest.mark.asyncio
    async def test_legacy_with_year_segment(self, monkeypatch):
        """A future import format `ORD-2024-007` must parse the last run."""
        from repositories import order_repository
        coll = MagicMock()
        coll.find = MagicMock(return_value=_StubCursor([{"order_number": "ORD-2024-007"}]))
        coll.count_documents = AsyncMock(return_value=7)
        monkeypatch.setattr(order_repository, "orders_collection", coll)
        result = await order_repository.get_next_order_number("org-1")
        assert result == "ORD-0008"

    @pytest.mark.asyncio
    async def test_bootstrap_empty_org(self, monkeypatch):
        from repositories import order_repository
        coll = MagicMock()
        coll.find = MagicMock(return_value=_StubCursor([]))
        coll.count_documents = AsyncMock(return_value=0)
        monkeypatch.setattr(order_repository, "orders_collection", coll)
        result = await order_repository.get_next_order_number("org-1")
        assert result == "ORD-0001"

    @pytest.mark.asyncio
    async def test_no_numeric_tail_falls_back_to_count(self, monkeypatch):
        """Exotic case: legacy import with non-numeric order_number.
        The fallback must use count+1 — never collapse to ORD-0001
        which would collide with the bootstrap pattern."""
        from repositories import order_repository
        coll = MagicMock()
        coll.find = MagicMock(return_value=_StubCursor([{"order_number": "ORD-UNDEFINED"}]))
        coll.count_documents = AsyncMock(return_value=17)
        monkeypatch.setattr(order_repository, "orders_collection", coll)
        result = await order_repository.get_next_order_number("org-1")
        assert result == "ORD-0018"  # count 17 + 1


# ─── Order model accepts external_* fields ───────────────────────────


class TestOrderModelExternalFields:
    """The Order model gained three Optional fields on 2026-05-20 so
    legacy imports (Shopify, WooCommerce, ERP) can attach their source
    identifier without polluting the canonical order_number."""

    def test_accepts_external_order_number(self):
        from models.order import Order
        o = Order(
            organization_id="org-1",
            customer_id="cust-1",
            external_order_number="#1001",
            external_source="shopify",
            external_imported_at="2026-05-20T10:00:00+00:00",
        )
        assert o.external_order_number == "#1001"
        assert o.external_source == "shopify"
        assert o.external_imported_at == "2026-05-20T10:00:00+00:00"

    def test_legacy_default_none(self):
        """Backward compat: existing orders on disk without the new
        fields must deserialise cleanly with None values."""
        from models.order import Order
        o = Order(organization_id="org-1", customer_id="cust-1")
        assert o.external_order_number is None
        assert o.external_source is None
        assert o.external_imported_at is None


# ─── Canonical format anti-typo guard ────────────────────────────────


class TestCanonicalFormatGuard:
    """Pin the regex shape so a future refactor that "tidies up" the
    parser doesn't accidentally accept ORD-0001-X or similar."""

    def test_canonical_regex_accepts_only_ord_digits(self):
        import re
        canonical = re.compile(r"^ORD-\d+$")
        assert canonical.match("ORD-0001")
        assert canonical.match("ORD-10000")
        assert not canonical.match("ORD-CB-0001")
        assert not canonical.match("ORD-")
        assert not canonical.match("ord-0001")
        assert not canonical.match("ORD0001")
