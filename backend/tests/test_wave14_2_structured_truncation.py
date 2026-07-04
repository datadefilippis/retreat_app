"""Wave 14.2 — structured truncation overhaul.

Pre-Wave-14.2 ``_truncate_tool_result`` used a single strategy: if
the JSON-serialised tool result exceeded ``_MAX_TOOL_RESULT_CHARS``,
slice the string at the cap and emit a "head-only" marker. The slice
boundary fell wherever in the JSON it happened to land — typically
mid-key (the 2026-05-16 prod incident saw it cut at ``"fixed_co"``).
The model received corrupted, invalid JSON, declared "data truncated"
to the user, and synthesised plausible-sounding numbers from prior
context.

Wave 14.2 replaces the single head-only cut with a 4-pass progressive
structured strategy:

  Pass 1 — drop verbose time-series arrays (by_date, daily_series, …)
  Pass 2 — cap top_/recent_ lists at 5 items
  Pass 3 — drop epistemic / block_scopes / data_caveats
  Pass 4 — drop diagnostics / breakdown / data_warnings
  Pass 5 (fallback) — head-only on the compacted result, still emits
                       a valid marker for the model to handle

Each pass records the dotted paths of dropped fields in
``_truncated_fields`` so the model knows EXACTLY which sections of
the response are no longer complete and can decide whether to retry
with a narrower window.

These tests are also regression sentinels — a future commit that
reverts to head-only-as-first-resort will turn red here.
"""

import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _make_oversized_with_time_series(cap: int) -> dict:
    """Build a payload whose by_date / daily_series push it over the
    cap, but whose aggregate fields (total / pnl) are compact. After
    Pass 1 strip the result fits under the cap."""
    # Enough days to push the serialised size well above the cap.
    days = max(2000, cap // 25)
    return {
        "has_data": True,
        "total": 209954.34,
        "currency": "EUR",
        "pnl": {"total_sales": 209954.34, "net_after_fixed": 90899.99},
        "_temporal_scope": "period_filtered",
        "_data_integrity": {"status": "ok", "message": None},
        "_source": {"tool": "query_cashflow_summary", "envelope_version": "14.0"},
        "by_date": {
            f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}": float(i) * 100.0
            for i in range(days)
        },
        "daily_series": [
            {"date": f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
             "sales": float(i), "net": float(i) * 1.5}
            for i in range(days)
        ],
    }


# ── Pass 1 — drop verbose time-series ─────────────────────────────────────


class TestPass1DropTimeSeries:
    def test_oversized_with_time_series_shrinks_via_pass_1(self):
        from services.chat_service import (
            _MAX_TOOL_RESULT_CHARS,
            _truncate_tool_result,
        )
        big = _make_oversized_with_time_series(_MAX_TOOL_RESULT_CHARS)
        # Sanity: input IS oversize
        assert len(json.dumps(big, default=str)) > _MAX_TOOL_RESULT_CHARS

        out = _truncate_tool_result(big, "query_cashflow_summary")

        # Pass 1 stripped the verbose series — result now fits
        assert len(json.dumps(out, default=str)) <= _MAX_TOOL_RESULT_CHARS
        # Marker fields applied
        assert out["_truncated"] is True
        assert out["_truncated_by"] == "wave14_structured"
        # The dropped paths are reported to the model
        dropped = out["_truncated_fields"]
        assert any("by_date" in p for p in dropped)
        assert any("daily_series" in p for p in dropped)
        # Aggregate fields ARE preserved
        assert out["total"] == 209954.34
        assert out["pnl"]["total_sales"] == 209954.34
        # Envelope metadata STILL valid
        assert out["has_data"] is True
        assert out["_temporal_scope"] == "period_filtered"
        assert out["_source"]["tool"] == "query_cashflow_summary"

    def test_small_result_passes_through_unchanged(self):
        """Below the cap → no truncation, identical output."""
        from services.chat_service import _truncate_tool_result
        small = {"total": 100, "has_data": True}
        out = _truncate_tool_result(small, "query_revenue")
        assert out == small
        assert out.get("_truncated") is None


# ── Pass 2 — cap top-N lists ──────────────────────────────────────────────


class TestPass2CapTopLists:
    def test_top_n_lists_capped_at_5(self):
        """After Pass 1 strips time-series, if there are still long
        top_X arrays they get capped at 5 entries each."""
        from services.chat_service import (
            _MAX_TOOL_RESULT_CHARS,
            _cap_top_lists,
        )
        # Build a payload with long top_X lists
        payload = {
            "has_data": True,
            "top_customers": [
                {"name": f"Customer {i}", "total": 1000.0 * i}
                for i in range(100)
            ],
            "top_suppliers": [{"name": f"S{i}", "total": 50.0 * i} for i in range(30)],
            "recent_alerts": [{"id": str(i), "title": f"A {i}"} for i in range(50)],
        }
        capped, dropped = _cap_top_lists(payload, max_items=5)

        # Each top-N list capped to 5
        assert len(capped["top_customers"]) == 5
        assert len(capped["top_suppliers"]) == 5
        assert len(capped["recent_alerts"]) == 5
        # Original lengths reported as sibling fields
        assert capped["_top_customers_truncated_from"] == 100
        assert capped["_top_suppliers_truncated_from"] == 30
        assert capped["_recent_alerts_truncated_from"] == 50
        # Dropped paths reported
        assert "top_customers[5:100]" in dropped

    def test_non_top_n_lists_untouched(self):
        """Lists whose keys DON'T start with top_/recent_ pass through
        even if they're long — they may be primary business data."""
        from services.chat_service import _cap_top_lists
        payload = {
            "customers": [{"id": str(i)} for i in range(50)],
            "products": [{"sku": str(i)} for i in range(100)],
        }
        capped, dropped = _cap_top_lists(payload, max_items=5)
        # Non-top_ lists NOT capped
        assert len(capped["customers"]) == 50
        assert len(capped["products"]) == 100
        assert dropped == []

    def test_short_top_n_lists_untouched(self):
        from services.chat_service import _cap_top_lists
        payload = {"top_customers": [{"name": "A"}, {"name": "B"}]}
        capped, dropped = _cap_top_lists(payload, max_items=5)
        # 2 items < 5 cap → no truncation
        assert capped["top_customers"] == [{"name": "A"}, {"name": "B"}]
        assert dropped == []


# ── Pass 3 — drop advisory metadata ───────────────────────────────────────


class TestPass3DropAdvisoryBlocks:
    def test_drops_epistemic_block_scopes_data_caveats(self):
        from services.chat_service import _drop_advisory_blocks
        payload = {
            "has_data": True,
            "total": 100,
            "epistemic": {
                "epistemic_class": "factual",
                "reliability": "high",
                "caveat": "...",
            },
            "block_scopes": {
                "pnl": {"scope": "period_filtered", "note": "..."},
            },
            "data_caveats": ["Caveat 1", "Caveat 2"],
        }
        stripped, dropped = _drop_advisory_blocks(payload)
        assert "epistemic" not in stripped
        assert "block_scopes" not in stripped
        assert "data_caveats" not in stripped
        # Business fields preserved
        assert stripped["total"] == 100
        # Dropped paths reported
        assert set(dropped) == {"epistemic", "block_scopes", "data_caveats"}

    def test_drops_nested_epistemic_blocks(self):
        """Nested epistemic blocks (inside pnl, inside yoy) ALSO dropped."""
        from services.chat_service import _drop_advisory_blocks
        payload = {
            "pnl": {
                "total_sales": 100,
                "epistemic": {"reliability": "high"},
            },
            "yoy": {
                "pct": {"total_sales": 25.0},
                "epistemic": {"caveat": "..."},
            },
        }
        stripped, dropped = _drop_advisory_blocks(payload)
        assert "epistemic" not in stripped["pnl"]
        assert "epistemic" not in stripped["yoy"]
        assert stripped["pnl"]["total_sales"] == 100
        assert stripped["yoy"]["pct"]["total_sales"] == 25.0


# ── Pass 4 — drop deep metadata ──────────────────────────────────────────


class TestPass4DropDeepMetadata:
    def test_drops_diagnostics_breakdown_data_warnings(self):
        from services.chat_service import _drop_deep_metadata
        payload = {
            "has_data": True,
            "health_score": {
                "score": 96,
                "label": "Eccellente",
                "diagnostics": {"giorni_copertura": {"value": 100}},
                "breakdown": [
                    {"dimension": "net_margin", "points": 25},
                ] * 50,
                "top_issues": [],
                "data_warnings": ["w1"],
            },
        }
        stripped, dropped = _drop_deep_metadata(payload)
        # The deep metadata under health_score is dropped
        assert "diagnostics" not in stripped["health_score"]
        assert "breakdown" not in stripped["health_score"]
        assert "data_warnings" not in stripped["health_score"]
        # Score + label preserved (the AI's primary signal)
        assert stripped["health_score"]["score"] == 96
        assert stripped["health_score"]["label"] == "Eccellente"


# ── Pass 5 — head-only fallback ──────────────────────────────────────────


class TestPass5HeadOnlyFallback:
    def test_falls_back_to_head_only_when_structured_fails(self):
        """Build a payload that CANNOT be shrunk by any structured
        pass (all the verbose / advisory keys are absent; the payload
        is one giant business string). The fallback head-only path
        still produces a marker."""
        from services.chat_service import (
            _MAX_TOOL_RESULT_CHARS,
            _truncate_tool_result,
        )
        # Stuff a single giant string under a non-prunable key
        big = {
            "has_data": True,
            "title": "Q",
            "long_text": "x" * (_MAX_TOOL_RESULT_CHARS + 5000),
        }
        out = _truncate_tool_result(big, "query_x")

        # Hit the head-only fallback
        assert out["_truncated"] is True
        assert out["_truncated_by"] == "wave14_head_only_fallback"
        assert "head" in out
        # Hint instructs the AI to NOT parse partial JSON
        assert "DO NOT attempt to parse the partial JSON" in out["_hint"]


# ── End-to-end: real-shaped responses ────────────────────────────────────


class TestRealisticResponseFlow:
    """Higher-confidence tests using payloads shaped like the real
    cashflow_summary / business_summary returns. These prove the
    progressive strategy actually preserves what the AI needs to
    answer most questions, even on very large org data."""

    def test_realistic_cashflow_summary_ytd_survives_truncation(self):
        """Mirrors the 2026-05-16 incident: a YTD cashflow_summary
        for a 209K-€ organisation. Pre-Wave-14.2 this got sliced
        mid-key. Post-Wave-14.2 the aggregate KPIs survive and the
        verbose time-series get dropped instead."""
        from services.chat_service import (
            _MAX_TOOL_RESULT_CHARS,
            _truncate_tool_result,
        )

        days = 136  # YTD as of May 16
        big = {
            "has_data": True,
            "currency": "EUR",
            "period": {"label": "ytd", "start_date": "2026-01-01",
                        "end_date": "2026-05-16", "days": days,
                        "semantic": "ytd"},
            "_temporal_scope": "period_filtered",
            "_data_integrity": {"status": "ok", "message": None},
            "_source": {"tool": "query_cashflow_summary",
                         "envelope_version": "14.0"},
            "pnl": {
                "total_sales": 209954.34,
                "net_after_fixed": 90899.99,
                "operating_margin_pct": 44.6,
            },
            "health_score": {
                "score": 96, "label": "Eccellente",
                "breakdown": [{"dim": f"d{i}", "points": i} for i in range(60)],
                "diagnostics": {"k": "v" * 500},
            },
            "yoy": {
                "has_data": True,
                "pct": {"total_sales": 1808.7,
                         "operating_margin_pct_pp_change": 3.2},
            },
            "by_date": {
                f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}": float(i) * 1500.0
                for i in range(500)  # noisy on purpose
            },
            "daily_series": [
                {"date": f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                 "sales": float(i * 100), "net": float(i * 50)}
                for i in range(500)
            ],
            "top_expense_categories": [
                {"category": f"Cat {i}", "total": float(i) * 100}
                for i in range(50)
            ],
            "top_sales_categories": [
                {"category": f"Sales {i}", "total": float(i) * 200}
                for i in range(50)
            ],
            "top_suppliers": [
                {"supplier": f"S{i}", "total": float(i) * 300}
                for i in range(50)
            ],
        }

        out = _truncate_tool_result(big, "query_cashflow_summary")

        # Result fits under the cap
        assert len(json.dumps(out, default=str)) <= _MAX_TOOL_RESULT_CHARS
        # The CRITICAL business fields the AI needs to answer most
        # questions all survived:
        assert out["pnl"]["total_sales"] == 209954.34
        assert out["pnl"]["net_after_fixed"] == 90899.99
        assert out["health_score"]["score"] == 96
        assert out["health_score"]["label"] == "Eccellente"
        assert out["yoy"]["pct"]["total_sales"] == 1808.7
        # Envelope metadata survives
        assert out["_temporal_scope"] == "period_filtered"
        assert out["_source"]["tool"] == "query_cashflow_summary"
        assert out["period"]["semantic"] == "ytd"
        # Truncation tagged structurally — not head-only
        assert out["_truncated_by"] == "wave14_structured"
        # ``_truncated_fields`` lists what we dropped so the AI knows
        assert "_truncated_fields" in out
        # The time-series got dropped (Pass 1)
        dropped = out["_truncated_fields"]
        assert any("by_date" in p for p in dropped)
        assert any("daily_series" in p for p in dropped)
        # The progressive strategy applies the MINIMUM truncation
        # needed to fit. Top-N lists are kept if Pass 1 was enough.

    def test_realistic_response_needing_pass_2(self):
        """If even after Pass 1 (drop time-series) we're still over
        the cap, Pass 2 caps top-N lists. We force that by making
        the top-N lists themselves the bulk of the payload."""
        from services.chat_service import (
            _MAX_TOOL_RESULT_CHARS,
            _truncate_tool_result,
        )

        big = {
            "has_data": True,
            "_temporal_scope": "period_filtered",
            "_data_integrity": {"status": "ok", "message": None},
            "_source": {"tool": "query_top_customers", "envelope_version": "14.0"},
            "total_customers": 500,
            # No by_date — Pass 1 won't fire; cap pressure forces Pass 2.
            "top_customers": [
                {
                    "name": f"Customer {i:04d}",
                    "total_revenue": float(i) * 1000.0,
                    "metadata": "x" * 50,  # padding to push past the cap
                }
                for i in range(500)
            ],
        }
        out = _truncate_tool_result(big, "query_top_customers")

        # Result fits
        assert len(json.dumps(out, default=str)) <= _MAX_TOOL_RESULT_CHARS
        # Pass 2 capped the list
        assert len(out["top_customers"]) == 5
        assert out["_top_customers_truncated_from"] == 500
        assert out["_truncated_by"] == "wave14_structured"


# ── Source-code regression sentinels ─────────────────────────────────────


class TestSourceRegressionSentinels:
    def test_structured_strategy_documented_in_docstring(self):
        """The docstring must reference the progressive passes so
        future contributors don't accidentally revert to head-only."""
        import inspect
        from services.chat_service import _truncate_tool_result
        src = inspect.getsource(_truncate_tool_result)
        # The four-pass strategy must be present
        assert "Pass 1" in src and "Pass 2" in src
        assert "Pass 3" in src and "Pass 4" in src
        # Reference to the 2026-05-16 incident keeps the rationale
        # visible.
        assert "2026-05-16" in src

    def test_legacy_head_only_marker_preserved(self):
        """Old consumers / tests grep for ``_truncated`` and ``head``
        fields. The fallback branch still emits them."""
        import inspect
        from services import chat_service
        src = inspect.getsource(chat_service._head_only_truncate)
        assert '"_truncated"' in src
        assert '"head"' in src
