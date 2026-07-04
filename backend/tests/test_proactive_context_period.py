"""Tests for Wave 13.3 — Period-aware proactive context (BUG #2 fix).

The proactive context is injected into the system prompt for NEW chat
sessions. Pre-Wave-13 it hardcoded a 30-day health snapshot, which the
model then quoted as the answer to questions about OTHER periods (e.g.
"qual è il mio health YTD?" → cited the 30d value as YTD).

Phase 13.3 makes the proactive context honour the user's active period:
  * Health score is computed on the period_context's window.
  * Every snapshot line is tagged with its scope in brackets.
  * The preamble instructs the model to call a tool when the user asks
    about a DIFFERENT period than the bracketed scope.

These tests mock the downstream summary builders + repositories so we
can assert ONLY on the contract of the proactive context itself.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Shared mock helpers ──────────────────────────────────────────────────────


def _summary_with_score(score=42, level="Attenzione"):
    """Build a minimal build_ai_summary return shape.

    Wave 14.HOTFIX #3 added an explicit ``has_data`` gate before the
    proactive context emits the health line — the field MUST be True
    for the "score" path to fire, otherwise the helper emits the
    "dati insufficienti" line. We default it to True here so tests
    that want to assert on the score path get the right behaviour.
    """
    return {
        "has_data": True,
        "health_score": {"score": score, "label": level},
        "status": {"level": level},
    }


def _patch_repos(*, alerts=None, churn=0, drafts=0):
    """Patch all collaborators of _build_proactive_context."""
    return [
        patch(
            "repositories.alert_repository.find_by_org",
            new=AsyncMock(return_value=alerts or []),
        ),
        patch(
            "database.customer_metrics_collection.count_documents",
            new=AsyncMock(return_value=churn),
        ),
        patch(
            "database.orders_collection.count_documents",
            new=AsyncMock(return_value=drafts),
        ),
    ]


# ── Health score period scoping ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestHealthScorePeriodScoping:
    """The core BUG #2 fix: health score now uses the user's active
    period instead of always 30d."""

    async def test_ytd_period_context_uses_ytd_dates(self):
        from services.chat_service import _build_proactive_context

        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(return_value=_summary_with_score(33, "Critico")),
        ) as mock_summary, \
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
                period_context={
                    "label": "ytd",
                    "start": "2026-01-01",
                    "end": "2026-05-16",
                },
            )

        # The summary builder must have been called with the YTD dates,
        # NOT the pre-Wave-13 hardcoded 30d.
        mock_summary.assert_awaited_once()
        _, kwargs = mock_summary.await_args
        assert kwargs["start_date"] == "2026-01-01"
        assert kwargs["end_date"] == "2026-05-16"
        # The period token survives so the audit captures the user's
        # filter name.
        assert kwargs["period"] == "ytd"

        # The output text must explicitly tag the scope so the model
        # never confuses this snapshot with a different period.
        assert "Health score [periodo: ytd 2026-01-01→2026-05-16]" in ctx
        assert "33/100" in ctx

    async def test_30d_label_only_uses_token(self):
        from services.chat_service import _build_proactive_context

        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(return_value=_summary_with_score(48)),
        ) as mock_summary, \
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

        # No dates → must call with the token, no start/end.
        _, kwargs = mock_summary.await_args
        assert kwargs["period"] == "30d"
        assert kwargs.get("start_date") is None
        assert kwargs.get("end_date") is None

        # Tag uses just the token (no dates available).
        assert "[periodo: 30d]" in ctx
        assert "48/100" in ctx

    async def test_no_period_context_falls_back_with_explicit_default_tag(self):
        from services.chat_service import _build_proactive_context

        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(return_value=_summary_with_score(50)),
        ) as mock_summary, \
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
                period_context=None,  # standalone /ai page
            )

        # Falls back to 30d but the tag explicitly tells the model this
        # is a DEFAULT, not the user's filter.
        _, kwargs = mock_summary.await_args
        assert kwargs["period"] == "30d"
        assert "default" in ctx.lower()
        # The model must SEE that no user-active filter was supplied.
        assert "non ha un filtro attivo" in ctx


# ── Scope tagging on all snapshot lines ─────────────────────────────────────


@pytest.mark.asyncio
class TestScopeTagging:
    """Every metric line must declare its scope in brackets so the
    model never attributes a snapshot to the wrong period."""

    async def test_alerts_tagged_current_state(self):
        from services.chat_service import _build_proactive_context

        # Mix of statuses — the proactive helper must filter out
        # resolved alerts in Python (Wave 13.3 also revives this
        # previously-dead-code path).
        alerts = [
            {"severity": "high", "status": "new"},
            {"severity": "high", "status": "acknowledged"},
            {"severity": "medium", "status": "new"},
            {"severity": "high", "status": "resolved"},  # filtered out
        ]
        with patch(
            "repositories.alert_repository.find_by_org",
            new=AsyncMock(return_value=alerts),
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
                "org_1", set(), locale="it", period_context=None,
            )

        assert "Alert attivi [stato corrente]: 2 critici, 1 medi" in ctx

    async def test_churn_tagged_all_time_snapshot(self):
        from services.chat_service import _build_proactive_context

        with patch(
            "repositories.alert_repository.find_by_org",
            new=AsyncMock(return_value=[]),
        ), \
             patch(
                "database.customer_metrics_collection.count_documents",
                new=AsyncMock(return_value=7),
             ), \
             patch(
                "database.orders_collection.count_documents",
                new=AsyncMock(return_value=0),
             ):
            ctx = await _build_proactive_context(
                "org_1", {"customers_light"}, locale="it",
                period_context={"label": "ytd",
                                "start": "2026-01-01",
                                "end": "2026-05-16"},
            )

        # Note: even when the user is on YTD, churn count is still
        # all-time (materialised in customer_metrics) — tag must say so.
        assert "Clienti a rischio churn [snapshot all-time]: 7" in ctx

    async def test_drafts_tagged_current_state(self):
        from services.chat_service import _build_proactive_context

        with patch(
            "repositories.alert_repository.find_by_org",
            new=AsyncMock(return_value=[]),
        ), \
             patch(
                "database.customer_metrics_collection.count_documents",
                new=AsyncMock(return_value=0),
             ), \
             patch(
                "database.orders_collection.count_documents",
                new=AsyncMock(return_value=3),
             ):
            ctx = await _build_proactive_context(
                "org_1", set(), locale="it", period_context=None,
            )

        assert "Ordini in bozza [stato corrente]: 3" in ctx


# ── Discipline preamble ──────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDisciplinePreamble:
    """The proactive block now ends with explicit instructions that
    prevent the model from misquoting bracketed snapshots."""

    async def test_preamble_warns_against_cross_period_citation(self):
        from services.chat_service import _build_proactive_context

        with patch(
            "repositories.alert_repository.find_by_org",
            new=AsyncMock(return_value=[{"severity": "high"}]),
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
                "org_1", set(), locale="it", period_context=None,
            )

        # The model must be explicitly told NOT to reuse these numbers
        # for other periods, and to call a tool instead.
        assert "tagged with its scope in brackets" in ctx
        assert "MUST call the appropriate tool" in ctx
        assert "do NOT" in ctx and "cite these snapshot numbers" in ctx


# ── No-data case: emit explicit "insufficient data" signal ─────────────────


@pytest.mark.asyncio
class TestNoDataCase:
    """Wave 14.HOTFIX #3 — when build_ai_summary returns has_data=False
    (or no has_data field), the proactive context now emits an EXPLICIT
    "dati insufficienti" line directing the model NOT to invent numbers.
    Pre-Wave-14 the helper stayed silent on this case, which let the
    chat AI hallucinate a plausible health score (the bug observed in
    prod 2026-05-16).

    The "ctx == empty" assertion that was valid in Wave 13.3 is replaced
    here by the more accurate Wave 14 contract."""

    async def test_no_data_emits_explicit_insufficient_data_signal(self):
        from services.chat_service import _build_proactive_context

        with patch(
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
             ), \
             patch(
                "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
                new=AsyncMock(return_value={
                    "has_data": False,
                    "health_score": None,
                    "status": {},
                }),
             ):
            ctx = await _build_proactive_context(
                "org_1", {"cashflow_monitor"}, locale="it",
                period_context={"label": "30d"},
            )

        # Wave 14.HOTFIX #3 — model must SEE that data is missing AND
        # be instructed not to fabricate. Previously this was silent.
        assert "dati insufficienti" in ctx
        assert "NON inventare" in ctx
        # No fabricated score must appear.
        assert "/100" not in ctx or "dati insufficienti" in ctx

    async def test_completely_empty_when_no_modules_active(self):
        """If literally NO module is active, no proactive content
        whatsoever — the empty-string short-circuit (Wave 13.3) still
        applies for this case."""
        from services.chat_service import _build_proactive_context

        with patch(
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
                "org_1", set(), locale="it",  # no active modules
                period_context=None,
            )

        assert ctx == ""
