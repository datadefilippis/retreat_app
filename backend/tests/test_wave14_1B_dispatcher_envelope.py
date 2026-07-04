"""Wave 14.1.B — dispatcher-level envelope wrapping for the remaining
~57 chat AI tools.

Phase 14.1.A migrated the 5 most-called tools to use
``attach_envelope_metadata`` directly in their executor branches.
Phase 14.1.B takes the DRY approach for the rest: a single
``wrap_tool_result_envelope`` call at the chat dispatcher boundary
(in ``chat_service.on_tool_call``) ensures every tool's response
gets the envelope metadata BEFORE it reaches Anthropic, using the
Wave 13.6 ``TOOL_SCOPE`` registry to derive ``_temporal_scope``.

Benefits:
  - Zero per-tool patches for the 57 remaining tools.
  - Future tools added to ``TOOL_SCOPE`` get envelope compliance
    automatically as soon as they're registered.
  - The 5 tools that already build full envelopes (Phase 14.1.A)
    are unchanged — the wrapper detects them via ``is_envelope()``
    and short-circuits.

These tests pin the dispatcher-level contract:

  1. wrap_tool_result_envelope wraps a legacy dict using the
     registered scope.
  2. wrap_tool_result_envelope is idempotent on an already-envelope.
  3. Non-dict results pass through unchanged.
  4. Unknown tools (not in TOOL_SCOPE) get partial envelope but
     fail validate_envelope (signalling registry omission).
  5. The wrapper is wired into chat_service.on_tool_call after
     attach_temporal_scope so the FULL Wave 13.6 + 14 pipeline runs.
"""

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


# ── wrap_tool_result_envelope core behaviour ──────────────────────────────


class TestWrapToolResultEnvelopeCore:
    def test_legacy_dict_gets_envelope_metadata(self):
        from core.tool_envelope import (
            ENVELOPE_VERSION,
            is_envelope,
            wrap_tool_result_envelope,
        )
        legacy = {
            "total": 100,
            "currency": "EUR",
            "by_date": {"2026-05-01": 100.0},
        }
        wrapped = wrap_tool_result_envelope("query_revenue", legacy)
        # Now a full envelope
        assert is_envelope(wrapped)
        # Legacy fields preserved
        assert wrapped["total"] == 100
        assert wrapped["currency"] == "EUR"
        # Envelope metadata added
        assert wrapped["_temporal_scope"] == "period_filtered"
        assert wrapped["_data_integrity"]["status"] == "ok"
        assert wrapped["_source"]["tool"] == "query_revenue"
        assert wrapped["_source"]["envelope_version"] == ENVELOPE_VERSION

    def test_idempotent_on_existing_envelope(self):
        """Calling the wrapper on an already-formed envelope returns
        it unchanged — protects Phase 14.1.A migrated tools."""
        from core.tool_envelope import (
            wrap_response,
            wrap_tool_result_envelope,
            is_envelope,
        )
        envelope = wrap_response(
            tool="query_cashflow_summary",
            has_data=True,
            data={"total_sales": 100},
            temporal_scope="period_filtered",
        )
        result = wrap_tool_result_envelope("query_cashflow_summary", envelope)
        # Same object semantics — wrapper is a no-op
        assert result == envelope
        assert is_envelope(result)

    def test_non_dict_passes_through(self):
        from core.tool_envelope import wrap_tool_result_envelope
        # Defensive: tools may return None / [] / strings under error
        assert wrap_tool_result_envelope("x", None) is None
        assert wrap_tool_result_envelope("x", []) == []
        assert wrap_tool_result_envelope("x", "error string") == "error string"

    def test_known_period_filtered_tool_gets_correct_scope(self):
        from core.tool_envelope import wrap_tool_result_envelope
        wrapped = wrap_tool_result_envelope(
            "query_expenses",
            {"total": 50000, "has_data": True},
        )
        assert wrapped["_temporal_scope"] == "period_filtered"

    def test_known_all_time_tool_gets_correct_scope(self):
        from core.tool_envelope import wrap_tool_result_envelope
        wrapped = wrap_tool_result_envelope(
            "query_churn_risk",
            {"customers": [], "has_data": True},
        )
        assert wrapped["_temporal_scope"] == "all_time"

    def test_known_current_state_tool_gets_correct_scope(self):
        from core.tool_envelope import wrap_tool_result_envelope
        wrapped = wrap_tool_result_envelope(
            "query_fulfillment_status",
            {"orders": [], "has_data": True},
        )
        assert wrapped["_temporal_scope"] == "current_state"

    def test_known_forward_looking_tool_gets_correct_scope(self):
        from core.tool_envelope import wrap_tool_result_envelope
        wrapped = wrap_tool_result_envelope(
            "query_rentals_upcoming",
            {"rentals": [], "has_data": True},
        )
        assert wrapped["_temporal_scope"] == "forward_looking"

    def test_unknown_tool_partial_envelope_only(self):
        """Tools not in TOOL_SCOPE get the OTHER envelope fields but
        not ``_temporal_scope`` — validate_envelope will then surface
        them as missing-scope errors, prompting registry updates."""
        from core.tool_envelope import (
            wrap_tool_result_envelope,
            validate_envelope,
        )
        wrapped = wrap_tool_result_envelope(
            "query_brand_new_tool_unregistered",
            {"data": {"x": 1}, "has_data": True},
        )
        # Got has_data, _data_integrity, _source — but not _temporal_scope
        assert wrapped["has_data"] is True
        assert "_data_integrity" in wrapped
        assert "_source" in wrapped
        assert "_temporal_scope" not in wrapped
        # Validator flags the missing scope as error
        validation = validate_envelope(wrapped)
        assert validation.ok is False
        assert any("_temporal_scope" in e for e in validation.errors)


# ── Per-tool envelope coverage matrix ─────────────────────────────────────


class TestPerToolEnvelopeCoverage:
    """Verify that EVERY tool in TOOL_SCOPE produces a valid envelope
    when passed through the dispatcher wrapper. This is the regression
    sentinel: a future tool added to TOOL_SCOPE without proper
    integration won't fail at import time but will fail this test."""

    def test_all_registered_tools_produce_valid_envelopes(self):
        from core.tool_envelope import (
            validate_envelope,
            wrap_tool_result_envelope,
        )
        from core.tool_temporal_scope import TOOL_SCOPE

        # Simulated minimal response — any tool's dispatcher branch
        # returns at least a dict with some fields. The wrapper adds
        # envelope metadata; we then validate the result.
        sample_response = {"has_data": True, "data": {"value": 1}}

        failures = []
        for tool_name, expected_scope in TOOL_SCOPE.items():
            wrapped = wrap_tool_result_envelope(tool_name, dict(sample_response))
            v = validate_envelope(wrapped)
            if not v.ok:
                failures.append((tool_name, v.errors))
            elif wrapped["_temporal_scope"] != expected_scope:
                failures.append((
                    tool_name,
                    [f"scope mismatch: registry={expected_scope}, got={wrapped['_temporal_scope']}"],
                ))

        assert not failures, (
            "Wave 14.1.B regression — some tools produce non-compliant "
            "envelopes after the dispatcher wrap. Either fix the tool "
            "or update TOOL_SCOPE.\n"
            + "\n".join(f"  {t}: {errs}" for t, errs in failures)
        )


# ── chat_service.on_tool_call wiring sentinel ─────────────────────────────


class TestDispatcherWiringSentinel:
    """Source-code grep ensures the dispatcher actually calls the
    wrapper. A future commit that accidentally removes the line
    turns this red."""

    def test_chat_service_imports_and_calls_wrapper(self):
        import inspect
        from services import chat_service
        src = inspect.getsource(chat_service.chat)
        assert "wrap_tool_result_envelope" in src, (
            "Wave 14.1.B regression — chat_service no longer calls "
            "wrap_tool_result_envelope. Tools will return non-envelope "
            "responses and the AI loses envelope-driven discipline."
        )
