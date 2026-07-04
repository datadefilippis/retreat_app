"""Sentinel tests for the cashflow list endpoints' limit contract
(2026-05-20).

Background
==========
The cashflow Section tables (Entrate/Sales, Uscite/Expenses,
Acquisti/Purchases) call ``GET /api/{sales,expenses,purchases}``
with no explicit ``limit`` parameter. Before today, the backend
default was 500 and the client never overrode it, so a merchant
with >500 records saw a truncated table AND a client-side filter
that operated only on the truncated subset.

The 2026-05-20 fix:
  - Raises the CLIENT default to 5000 by passing limit=5000
    explicitly in the API helpers (sales.js / purchases.js /
    expenses.js + fixedCosts.js opts).
  - Leaves the BACKEND cap (Query(500, le=5000)) untouched: it
    already accepted 5000.

These sentinels pin the backend's CONTRACT so a future refactor
that lowers the cap below 5000 would break the test (and be caught
before deploy). They are pure backend-contract tests — no DB hit.

Sentinel invariants
-------------------
  1. ``GET /api/sales``      accepts limit up to 5000 (≤ cap).
  2. ``GET /api/sales``      rejects limit above 5000 (FastAPI 422
                              from the ``le=5000`` constraint).
  3. Same shape for ``/api/expenses`` and ``/api/purchases``.
  4. Default limit (no query param) stays at 500 — documented
     contract; a future change must update both backend and this
     sentinel atomically.

The endpoints are auth-gated via ``get_verified_user``; we test the
ROUTE SIGNATURE / QUERY VALIDATION shape rather than the auth+DB
roundtrip (covered by other suites).
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── Route signature inspection ──────────────────────────────────────


def _inspect_limit_param(route_fn):
    """Return the FastAPI Query default + le constraint for the
    ``limit`` parameter of an endpoint, by inspecting the function
    signature. Avoids spinning up a TestClient + auth roundtrip for
    a pure contract check.

    Implementation note: FastAPI (recent versions) stores ``le`` /
    ``ge`` as Pydantic ``Le()`` / ``Ge()`` annotated-metadata objects
    inside ``Query.metadata`` rather than as direct attributes. We
    navigate that list to extract the bound.
    """
    import inspect
    sig = inspect.signature(route_fn)
    param = sig.parameters.get("limit")
    assert param is not None, f"{route_fn.__name__} must have a ``limit`` param"
    default = param.default
    assert hasattr(default, "default"), "expected fastapi.Query(...)"

    le_value = None
    ge_value = None
    for constraint in getattr(default, "metadata", []) or []:
        # Pydantic v2 annotated-types: Le, Ge, Lt, Gt have a single
        # attribute named after the constraint (``le``, ``ge``, ...).
        if hasattr(constraint, "le"):
            le_value = constraint.le
        if hasattr(constraint, "ge"):
            ge_value = constraint.ge

    return {
        "default": default.default,
        "le": le_value,
        "ge": ge_value,
    }


class TestSalesListLimitContract:
    def test_sales_list_default_is_500(self):
        from routers.sales import list_sales
        meta = _inspect_limit_param(list_sales)
        assert meta["default"] == 500, (
            "Default limit on /api/sales is the contract the frontend "
            "relied on for years; lowering it would re-truncate the "
            "cashflow tables. Update the client + this sentinel together."
        )

    def test_sales_list_cap_is_at_least_5000(self):
        from routers.sales import list_sales
        meta = _inspect_limit_param(list_sales)
        assert meta["le"] is not None, "limit must have an upper bound"
        assert meta["le"] >= 5000, (
            "The 2026-05-20 fix passes limit=5000 explicitly from the "
            "frontend; lowering this cap would break the cashflow "
            "Entrate table for SMEs with >500 records."
        )


class TestExpensesListLimitContract:
    def test_expenses_list_default_is_500(self):
        from routers.expenses import list_expenses
        meta = _inspect_limit_param(list_expenses)
        assert meta["default"] == 500

    def test_expenses_list_cap_is_at_least_5000(self):
        from routers.expenses import list_expenses
        meta = _inspect_limit_param(list_expenses)
        assert meta["le"] is not None
        assert meta["le"] >= 5000


class TestPurchasesListLimitContract:
    def test_purchases_list_default_is_500(self):
        from routers.purchases import list_purchases
        meta = _inspect_limit_param(list_purchases)
        assert meta["default"] == 500

    def test_purchases_list_cap_is_at_least_5000(self):
        from routers.purchases import list_purchases
        meta = _inspect_limit_param(list_purchases)
        assert meta["le"] is not None
        assert meta["le"] >= 5000


class TestFixedCostsListLimitContract:
    """The FixedCosts cap is 500 (lower than sales/expenses/purchases
    because the number of fixed-cost rows per org is naturally small).
    The frontend FixedCostsSection now passes limit=500 explicitly to
    use that full cap. If the backend cap is ever lowered below 500
    this sentinel will catch it before the cashflow Costi Fissi table
    silently truncates."""

    def test_fixed_costs_list_default_is_200(self):
        from routers.fixed_costs import list_fixed_costs
        meta = _inspect_limit_param(list_fixed_costs)
        assert meta["default"] == 200, (
            "200 default historically used by the dashboard widget "
            "(CashflowModulePage). The FixedCostsSection now overrides "
            "via opts={limit:500} but the default is the documented "
            "contract for other call sites."
        )

    def test_fixed_costs_list_cap_is_at_least_500(self):
        from routers.fixed_costs import list_fixed_costs
        meta = _inspect_limit_param(list_fixed_costs)
        assert meta["le"] is not None
        assert meta["le"] >= 500
