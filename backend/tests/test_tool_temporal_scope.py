"""Tests for Wave 13.6 — temporal scope marker registry + dispatcher hook.

Covers:
  - The registry vocabulary is sane (all values from VALID_SCOPES).
  - ``get_scope`` lookup behaves safely on unknown tools.
  - ``attach_temporal_scope``:
      * injects the marker for known tools
      * preserves a tool's own _temporal_scope (more precise label wins)
      * leaves non-dict results untouched
      * leaves dicts of unknown tools untouched
  - System prompt rule mentions the marker (so the model is instructed
    to honour it).
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

from core.tool_temporal_scope import (
    ALL_TIME,
    CURRENT_STATE,
    FORWARD_LOOKING,
    META,
    PERIOD_FILTERED,
    TOOL_SCOPE,
    VALID_SCOPES,
    attach_temporal_scope,
    get_scope,
)


# ── Registry integrity ──────────────────────────────────────────────────────


class TestRegistryIntegrity:
    def test_all_scope_values_are_valid(self):
        """Every entry in TOOL_SCOPE must use a known scope constant."""
        for tool, scope in TOOL_SCOPE.items():
            assert scope in VALID_SCOPES, (
                f"tool {tool!r} has invalid scope {scope!r} — "
                f"must be one of {sorted(VALID_SCOPES)}"
            )

    def test_known_period_filtered_tools_classified(self):
        # Spot-check the period-filtered surface — these are the
        # CORE summary tools and MUST stay period_filtered.
        for tool in [
            "query_business_summary",
            "query_cashflow_summary",
            "query_revenue",
            "query_smart_brief",  # Wave 13.5 promoted it
        ]:
            assert TOOL_SCOPE[tool] == PERIOD_FILTERED, f"{tool} regressed"

    def test_known_all_time_tools_classified(self):
        # Customer + product materialised snapshots — the chat model
        # used to misattribute these to "the period you're viewing".
        for tool in [
            "query_top_customers", "query_customer_segments",
            "query_customer_concentration", "query_churn_risk",
            "query_product_analytics", "query_product_margins",
            "query_product_recommendations",
        ]:
            assert TOOL_SCOPE[tool] == ALL_TIME, f"{tool} regressed"

    def test_known_current_state_tools_classified(self):
        for tool in [
            "query_receivables_payables",
            "query_late_payers",
            "query_fulfillment_status",
            "query_payment_pipeline",
            "query_catalog_health",
        ]:
            assert TOOL_SCOPE[tool] == CURRENT_STATE, f"{tool} regressed"

    def test_known_forward_looking_tools_classified(self):
        for tool in [
            "query_agenda_upcoming",
            "query_rentals_upcoming",
            "query_rentals_returning",
            "query_rental_pipeline",
            "query_events_calendar",
        ]:
            assert TOOL_SCOPE[tool] == FORWARD_LOOKING, f"{tool} regressed"

    def test_get_scope_returns_none_for_unknown(self):
        assert get_scope("query_nonexistent") is None
        assert get_scope("") is None


# ── attach_temporal_scope behaviour ─────────────────────────────────────────


class TestAttachTemporalScope:
    def test_injects_for_known_tool(self):
        result = {"data": {"count": 5}, "_epistemic_note": "ok"}
        out = attach_temporal_scope("query_top_customers", result)

        assert out["_temporal_scope"] == ALL_TIME
        # Other fields are preserved
        assert out["data"] == {"count": 5}
        assert out["_epistemic_note"] == "ok"

    def test_preserves_existing_temporal_scope(self):
        """If a tool already set the marker (e.g. Wave 13.5 product_trend
        uses the more precise label), the dispatcher must NOT overwrite."""
        result = {
            "data": {},
            "_temporal_scope": "materialized_30d_vs_prior_30d",
        }
        out = attach_temporal_scope("query_product_trend", result)
        assert out["_temporal_scope"] == "materialized_30d_vs_prior_30d"

    def test_unknown_tool_passthrough(self):
        result = {"data": {}}
        out = attach_temporal_scope("query_nonexistent", result)
        assert "_temporal_scope" not in out
        # Same dict identity is allowed but not required; we just need
        # the contract (no marker injected).
        assert out == {"data": {}}

    def test_non_dict_result_passthrough(self):
        # Some tools may return a list, a string, or None on error.
        assert attach_temporal_scope("query_top_customers", None) is None
        assert attach_temporal_scope("query_top_customers", []) == []
        assert attach_temporal_scope("query_top_customers", "string") == "string"

    def test_does_not_mutate_input(self):
        original = {"data": {"key": "value"}}
        snapshot = dict(original)
        out = attach_temporal_scope("query_receivables_payables", original)

        # Caller's dict is unchanged
        assert original == snapshot
        # New dict carries the marker
        assert out["_temporal_scope"] == CURRENT_STATE

    def test_marker_value_matches_registry(self):
        # End-to-end: registry value flows through correctly.
        result = {"data": {}}
        out = attach_temporal_scope("query_agenda_upcoming", result)
        assert out["_temporal_scope"] == FORWARD_LOOKING
        assert out["_temporal_scope"] == get_scope("query_agenda_upcoming")


# ── System prompt discipline rule wired in ──────────────────────────────────


class TestSystemPromptRule:
    def test_prompt_mentions_temporal_scope_rule(self):
        """The model needs to know HOW to read the marker. The system
        prompt must include a rule referencing the scope vocabulary."""
        # We import the raw core prompt string from chat_service so the
        # test doesn't need to spin up Anthropic — pure string check.
        from services.chat_service import _PROMPT_CORE

        assert "_temporal_scope" in _PROMPT_CORE
        # Each scope value the model might see must be documented
        # so it knows how to interpret it.
        for scope in (PERIOD_FILTERED, ALL_TIME, CURRENT_STATE,
                      FORWARD_LOOKING, META):
            assert scope in _PROMPT_CORE, (
                f"system prompt must document scope value {scope!r}"
            )
        # And the caveat handling rule must be explicit
        assert "_period_caveat" in _PROMPT_CORE
