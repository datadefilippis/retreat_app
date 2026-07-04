"""Tests for Wave 14.HOTFIX — chat AI quality emergency fixes (2026-05-16).

Replays the four concrete failure modes observed in production today and
asserts each fix is in place. Each test maps to a specific HOTFIX item:

  #1 — smart_brief risk_focus / action_focus list/dict handling
  #2 — _MAX_TOOL_RESULT_CHARS raised from 10K to 30K
  #3 — proactive context emits an explicit "insufficient data" line
       when build_ai_summary returns has_data=False (was silent before,
       letting the model hallucinate a plausible health number)
  #4 — Rules 19-25 added to the system prompt (source attribution,
       hard-stop on error, no estimation, truncation handling, cross-turn
       period memory, sign integrity)

These tests are also regression sentinels — a future commit that
reverts any of the four hotfixes will turn red here.
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


# ── HOTFIX #1: smart_brief list/dict handling ───────────────────────────────


class TestHotfix1FirstItemNormaliser:
    """The ``_first_item`` helper normalises risk_focus/action_focus
    payloads to a dict regardless of the upstream shape. This is the
    root-cause fix for the smart_brief crash that hit prod today."""

    def test_list_with_dict_first(self):
        from modules.cashflow_monitor.ai_tools import _first_item
        assert _first_item([{"description": "high alert"}]) == {
            "description": "high alert",
        }

    def test_empty_list(self):
        from modules.cashflow_monitor.ai_tools import _first_item
        assert _first_item([]) == {}

    def test_none(self):
        from modules.cashflow_monitor.ai_tools import _first_item
        assert _first_item(None) == {}

    def test_dict_passthrough(self):
        from modules.cashflow_monitor.ai_tools import _first_item
        # Plain dict without "primary" key — return verbatim.
        assert _first_item({"description": "x"}) == {"description": "x"}

    def test_legacy_dict_with_primary(self):
        """Some legacy paths produced ``{"primary": {...}}`` — flatten."""
        from modules.cashflow_monitor.ai_tools import _first_item
        out = _first_item({"primary": {"summary": "y"}, "other": "z"})
        assert out == {"summary": "y"}

    def test_garbage_input(self):
        """Strings, numbers, etc. → empty dict (defensive)."""
        from modules.cashflow_monitor.ai_tools import _first_item
        assert _first_item("oops") == {}
        assert _first_item(42) == {}

    def test_list_with_non_dict_first(self):
        """Defensive — list of non-dicts shouldn't crash."""
        from modules.cashflow_monitor.ai_tools import _first_item
        assert _first_item(["not a dict"]) == {}


class TestHotfix1SmartBriefRegressionSentinel:
    """Source-code grep: assert the buggy pattern is gone and the
    helper-based code is in place. Catches accidental revert."""

    def test_buggy_pattern_gone(self):
        """The exact pre-fix pattern was the full chained call
        ``risk_focus.get("primary", {}).get("summary")``. Searching for
        that EXACT signature avoids false positives from docstrings or
        comments that mention the bug for historical reference."""
        import inspect
        from modules.cashflow_monitor import ai_tools
        src = inspect.getsource(ai_tools)
        forbidden = 'risk_focus.get("primary", {}).get("summary")'
        assert forbidden not in src, (
            "Wave 14.HOTFIX #1 regression — smart_brief is back to "
            "treating risk_focus as a dict. The shape from "
            "build_ai_summary is list[dict] for rich-data orgs and "
            "this code path will crash with AttributeError again."
        )

    def test_first_item_helper_used(self):
        import inspect
        from modules.cashflow_monitor import ai_tools
        src = inspect.getsource(ai_tools)
        assert "_first_item(risk_focus_raw)" in src
        assert "_first_item(action_focus_raw)" in src


# ── HOTFIX #2: truncation cap raised ────────────────────────────────────────


class TestHotfix2TruncationCap:
    """13_391-char YTD summaries were getting cut mid-JSON at 10K cap.
    New default 30K accommodates rich-data periods."""

    def test_cap_is_at_least_30k(self):
        from services.chat_service import _MAX_TOOL_RESULT_CHARS
        assert _MAX_TOOL_RESULT_CHARS >= 30000, (
            "Wave 14.HOTFIX #2 regression — truncation cap is back below "
            "30K. YTD summaries (~13K chars) will be cut mid-JSON and "
            "the chat AI will hallucinate as observed on 2026-05-16."
        )

    def test_typical_ytd_summary_size_fits(self):
        """The actual prod YTD summary was 13_391 chars. Verify the new
        cap is comfortably above that with headroom for richer orgs."""
        from services.chat_service import _MAX_TOOL_RESULT_CHARS
        prod_observed_ytd_size = 13_391
        # 2x headroom — orgs with more sales records, more alerts,
        # longer category lists can push this higher.
        assert _MAX_TOOL_RESULT_CHARS >= 2 * prod_observed_ytd_size

    def test_env_override_still_works(self):
        """Ops escape hatch: should still respect env var override.
        Verify by re-importing fresh (we can't easily test the live
        module since it captured the value at import time)."""
        import os
        # Just verify the env var name is referenced — concrete override
        # behaviour is exercised at module load time.
        import inspect
        from services import chat_service
        src = inspect.getsource(chat_service)
        assert "CHAT_MAX_TOOL_RESULT_CHARS" in src


# ── HOTFIX #3: proactive emits explicit "insufficient data" ─────────────────


@pytest.mark.asyncio
class TestHotfix3ProactiveHasDataFalse:
    """When build_ai_summary returns has_data=False, the proactive
    context now emits an explicit line directing the model NOT to
    invent numbers — was silently absent before."""

    async def test_proactive_emits_insufficient_data_line(self):
        from unittest.mock import AsyncMock, patch
        from services.chat_service import _build_proactive_context

        # build_ai_summary returns has_data=False (no records in window)
        fake_no_data_summary = {
            "has_data": False,
            "period": {"label": "30d"},
            "currency": "EUR",
            "message": "No sales or expense data available for this period.",
            "health_score": None,
            "status": {},
        }

        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(return_value=fake_no_data_summary),
        ), \
             patch(
                "repositories.alert_repository.find_by_org",
                new=AsyncMock(return_value=[]),
             ), \
             patch(
                "database.customer_metrics_collection.count_documents",
                new=AsyncMock(return_value=0),
             ), \
             patch(
                "database.orders_collection.count_documents",
                new=AsyncMock(return_value=0),
             ):
            ctx = await _build_proactive_context(
                "org_1", {"cashflow_monitor"}, locale="it",
                period_context={"label": "30d"},
            )

        # The model MUST see an explicit signal that data is missing
        # AND an instruction not to invent.
        assert "dati insufficienti" in ctx
        assert "NON inventare" in ctx
        assert "[periodo: 30d]" in ctx

    async def test_proactive_emits_score_when_has_data_true(self):
        """Sanity: when has_data=True, the score line is still emitted
        normally (Wave 13.3 behaviour preserved)."""
        from unittest.mock import AsyncMock, patch
        from services.chat_service import _build_proactive_context

        fake_good_summary = {
            "has_data": True,
            "health_score": {"score": 87, "label": "Buono"},
            "status": {"level": "Buono"},
        }
        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(return_value=fake_good_summary),
        ), \
             patch(
                "repositories.alert_repository.find_by_org",
                new=AsyncMock(return_value=[]),
             ), \
             patch(
                "database.customer_metrics_collection.count_documents",
                new=AsyncMock(return_value=0),
             ), \
             patch(
                "database.orders_collection.count_documents",
                new=AsyncMock(return_value=0),
             ):
            ctx = await _build_proactive_context(
                "org_1", {"cashflow_monitor"}, locale="it",
                period_context={"label": "ytd",
                                "start": "2026-01-01",
                                "end":   "2026-05-16"},
            )

        assert "87/100" in ctx
        assert "Buono" in ctx
        assert "dati insufficienti" not in ctx


# ── HOTFIX #4: anti-hallucination rules 19-25 in system prompt ──────────────


class TestHotfix4AntiHallucinationRules:
    """Rules 19-25 are mandatory anti-hallucination discipline. Each
    rule must appear verbatim in the system prompt so the model sees
    it on every chat turn."""

    def test_rule_19_source_attribution(self):
        from services.chat_service import _PROMPT_CORE
        assert "19. SOURCE ATTRIBUTION" in _PROMPT_CORE
        assert "FORBIDDEN" in _PROMPT_CORE  # numbers without tool source

    def test_rule_20_hard_stop_on_error(self):
        from services.chat_service import _PROMPT_CORE
        assert "20. HARD STOP ON TOOL ERROR" in _PROMPT_CORE
        assert "NEVER synthesize" in _PROMPT_CORE
        assert "NEVER estimate" in _PROMPT_CORE

    def test_rule_21_has_data_binding(self):
        from services.chat_service import _PROMPT_CORE
        assert "21. HAS_DATA BINDING" in _PROMPT_CORE
        assert "has_data" in _PROMPT_CORE

    def test_rule_22_no_estimation(self):
        from services.chat_service import _PROMPT_CORE
        assert "22. NO ESTIMATION" in _PROMPT_CORE
        assert "NO EXTRAPOLATION" in _PROMPT_CORE

    def test_rule_23_truncation_handling(self):
        from services.chat_service import _PROMPT_CORE
        assert "23. TRUNCATION HANDLING" in _PROMPT_CORE
        assert "_truncated" in _PROMPT_CORE

    def test_rule_24_cross_turn_period_memory(self):
        from services.chat_service import _PROMPT_CORE
        assert "24. CROSS-TURN PERIOD MEMORY" in _PROMPT_CORE
        assert "EXPLICITLY sets a period" in _PROMPT_CORE
        # The concrete example must guide the model
        assert "start_date" in _PROMPT_CORE and "end_date" in _PROMPT_CORE

    def test_rule_25_sign_and_direction(self):
        from services.chat_service import _PROMPT_CORE
        assert "25. SIGN AND DIRECTION INTEGRITY" in _PROMPT_CORE
        # The specific +1808.7 example anchors the rule to today's bug
        assert "+1808.7" in _PROMPT_CORE

    def test_all_rules_grouped_under_core_discipline_header(self):
        """All Wave 14 rules sit under one clearly marked section so
        future contributors don't accidentally split them."""
        from services.chat_service import _PROMPT_CORE
        assert "ANTI-HALLUCINATION CORE DISCIPLINE" in _PROMPT_CORE
