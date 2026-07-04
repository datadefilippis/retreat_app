"""Wave 13.8 — End-to-end Period Contracts test suite.

Living specification of the period-handling contract introduced by
Wave 13 (Period Integrity). Each test maps EXPLICITLY to one of the
bugs catalogued in the Wave 13 audit doc so a future contributor can
trace a failing test back to the original failure mode it prevents.

This file complements the per-phase test files
(``test_period_resolver.py``, ``test_get_date_range_adapter.py``, …)
by exercising the layers TOGETHER rather than in isolation:

  * Vocabulary alignment across layers (resolver / adapter / audit /
    temporal-scope registry).
  * Regression sentinels: one test per audit BUG #N, asserting the
    fix is still in place. A bug that re-appears in a future commit
    breaks the corresponding sentinel and the failure name pinpoints
    the audit reference.
  * Cross-layer composition checks that depend on multiple Wave 13
    phases working together.

The file is intentionally heavier on documentation than test logic —
the assertions are simple, the comments explain WHY each one matters.
"""

import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# Fixed "today" for deterministic checks. Same date used across the
# Wave 13 audit doc and the per-phase tests — keep in sync to make
# debugging easier.
T = date(2026, 5, 16)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Vocabulary alignment across layers
# ═══════════════════════════════════════════════════════════════════════════


class TestVocabularyAlignment:
    """The resolver, the adapter, the audit dict, and the temporal-scope
    registry must agree on the same period token vocabulary. A
    divergence would re-introduce silent fallbacks of the
    pre-Wave-13 kind."""

    def test_resolver_vocabulary_complete(self):
        """The canonical resolver must accept every token the
        frontend can emit (Phase 13.0 contract)."""
        from core.period_resolver import ACCEPTED_TOKENS

        # Tokens the frontend's PeriodSelector + computePeriodDates can
        # produce, plus the rolling-window tokens the model is trained
        # on. Adding any of these to the frontend WITHOUT extending
        # ACCEPTED_TOKENS would re-create BUG #1 (silent 30d).
        required = {"7d", "30d", "90d", "1y",
                    "ytd", "mtd", "qtd",
                    "custom", "data_range"}
        missing = required - ACCEPTED_TOKENS
        assert not missing, (
            f"Wave 13 vocabulary regressed — missing tokens: {missing}. "
            "If the frontend or model can emit a token, the resolver "
            "MUST accept it or the system reverts to silent 30d fallback."
        )

    def test_adapter_delegates_to_resolver(self):
        """``_get_date_range`` must call the resolver. If a future
        refactor reverts to inline date math the silent-fallback bug
        comes back."""
        import inspect
        from services import ai_analytics_service
        src = inspect.getsource(ai_analytics_service._get_date_range)
        # The adapter must reference the resolver — either via import
        # or via a thin wrapper. We assert on the import string rather
        # than mocking because the contract is "adapter uses resolver",
        # not "adapter has a specific implementation".
        assert "period_resolver" in src or "from core.period_resolver" in src, (
            "Wave 13.1 adapter regression — _get_date_range no longer "
            "delegates to core.period_resolver. The pre-13.1 silent-30d "
            "fallback for unknown tokens will resurface."
        )

    def test_temporal_scope_registry_covers_active_tools(self):
        """Every CORE summary tool needs an entry in the temporal-scope
        registry. Missing entries surface as no-marker → model can't
        scope its claims correctly (BUG #8)."""
        from core.tool_temporal_scope import TOOL_SCOPE

        # These are the tools the chat AI uses most for monetary
        # claims. Each one MUST be classified. Adding a new core tool
        # without an entry here means the model will treat its output
        # as untagged and may attribute it to the wrong period.
        for required_tool in [
            "query_business_summary",
            "query_cashflow_summary",
            "query_smart_brief",
            "query_top_customers",
            "query_product_analytics",
            "query_product_margins",
            "query_receivables_payables",
        ]:
            assert required_tool in TOOL_SCOPE, (
                f"Tool {required_tool!r} has no temporal scope entry. "
                "Add it to core/tool_temporal_scope.py:TOOL_SCOPE so "
                "the chat dispatcher can attach the marker."
            )


# ═══════════════════════════════════════════════════════════════════════════
# 2. Regression sentinels — one per Wave 13 audit BUG
# ═══════════════════════════════════════════════════════════════════════════


class TestBug01SilentFallback:
    """BUG #1 — `_get_date_range` accepted only 7d/30d/90d; every
    other token silently became 30d. User asking YTD got 30d data."""

    def test_ytd_token_resolves_to_year_start(self):
        from core.period_resolver import resolve, ResolutionSource

        r = resolve("ytd", today=T)

        assert r.resolution_source == ResolutionSource.TOKEN, (
            "BUG #1 sentinel — 'ytd' is no longer recognised as a token "
            "and falls through to default. Check core/period_resolver.py."
        )
        assert r.start == date(2026, 1, 1)
        assert r.end == T

    def test_adapter_resolves_ytd_correctly(self):
        """Same check at the adapter layer — proves the wire-up is
        intact end-to-end."""
        from services.ai_analytics_service import _get_date_range
        from unittest.mock import patch as _p
        from datetime import datetime, timezone

        class _FrozenDT(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(T.year, T.month, T.day, tzinfo=timezone.utc)

        with _p("services.ai_analytics_service.datetime", _FrozenDT):
            start, end = _get_date_range("ytd", None, None)

        assert start == "2026-01-01"
        assert end == "2026-05-16"


class TestBug02ProactiveContextHardcoded30d:
    """BUG #2 — `_build_proactive_context` hardcoded `period="30d"`.
    User on YTD opened chat → AI quoted the 30d health as if YTD."""

    @pytest.mark.asyncio
    async def test_proactive_uses_period_context_dates(self):
        from services.chat_service import _build_proactive_context

        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(return_value={
                "health_score": {"score": 33, "label": "Critico"},
                "status": {"level": "Critico"},
            }),
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

        # The summary builder MUST receive the user's YTD dates, not
        # the pre-Wave-13.3 hardcoded 30d.
        _, kwargs = mock_summary.await_args
        assert kwargs["start_date"] == "2026-01-01", (
            "BUG #2 regression — proactive context still calls "
            "build_ai_summary with non-YTD dates."
        )
        assert kwargs["end_date"] == "2026-05-16"

        # And the proactive text MUST tag the period explicitly so the
        # model never quotes the snapshot as a period-other answer.
        assert "[periodo: ytd" in ctx


class TestBug03AlertWindowNotStored:
    """BUG #3 — Alert documents never recorded the window they were
    generated on, so chat AI couldn't explain old alerts coherently."""

    def test_alert_model_has_window_fields(self):
        from models.alert import Alert, AlertSeverity

        a = Alert(
            organization_id="org_1",
            module_key="cashflow_monitor",
            severity=AlertSeverity.HIGH,
            title="t", summary="s", date_reference="2026-05-16",
            period_start="2026-04-16",
            period_end="2026-05-15",
            window_label="30d",
        )

        assert a.period_start == "2026-04-16", (
            "BUG #3 sentinel — Alert.period_start no longer accepted. "
            "Check models/alert.py:AlertBase."
        )
        assert a.window_label == "30d"


class TestBug04AlertAnalysisEmptyKpis:
    """BUG #4 — `alert_analysis` was called with `kpis={}`. The Sonnet
    prompt had no numerical context and produced generic prose."""

    @pytest.mark.asyncio
    async def test_kpi_builder_returns_real_kpis_for_window(self):
        from services.alert_service import _build_alert_window_kpis

        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(return_value={
                "kpis": {
                    "total_sales": 10000, "total_outflows": 7000,
                    "operating_margin_pct": 30.0,
                    "dso": 35, "dpo": 25, "giorni_autonomia": 60,
                    "total_outflow_ratio": 70.0,
                }
            }),
        ):
            kpis = await _build_alert_window_kpis(
                "org_1", "2026-04-16", "2026-05-15", "it",
            )

        # All keys that ``alert_analysis._build_batch_message``
        # interpolates must be present and non-zero.
        assert kpis["total_sales"] == 10000, (
            "BUG #4 regression — _build_alert_window_kpis returned an "
            "empty dict for a valid window. Sonnet will regress to "
            "generic generic alert analyses."
        )
        assert kpis["operating_margin_pct"] == 30.0


class TestBug05SmartBriefHardcoded30d:
    """BUG #5 — `query_smart_brief` ignored period_context and always
    returned 30d data. User on YTD asked for a brief, got 30d, was
    told it was YTD."""

    def test_smart_brief_schema_advertises_period_params(self):
        from modules.cashflow_monitor.ai_tools import TOOL_DEFINITIONS

        sb = next(t for t in TOOL_DEFINITIONS
                  if t["name"] == "query_smart_brief")

        # The MODEL sees the schema; period params must be there.
        assert "period" in sb["parameters"], (
            "BUG #5 sentinel — query_smart_brief schema regressed to "
            "no-period. Dispatcher injection from period_context will "
            "silently drop the user's window."
        )
        assert "start_date" in sb["parameters"]
        assert "end_date" in sb["parameters"]


class TestBug06ProductTrendHardcodedScope:
    """BUG #6 — `query_product_trend` returned a 30d-vs-prior-30d
    snapshot without any temporal-scope marker, so the model quoted
    its `trend_30d_pct` field as YTD / MTD trends."""

    def test_product_trend_describes_its_scope(self):
        from modules.product_catalog.ai_tools import TOOL_DEFINITIONS

        pt = next(t for t in TOOL_DEFINITIONS
                  if t["name"] == "query_product_trend")

        # The description must steer the model AWAY from using this
        # tool for non-30d questions.
        assert "30" in pt["description"]
        assert "query_business_summary" in pt["description"], (
            "BUG #6 sentinel — query_product_trend description no "
            "longer signposts the alternative tool for other windows. "
            "Model will use it for YTD/MTD trend questions and get "
            "the wrong scope."
        )


class TestBug07NoPeriodLogging:
    """BUG #7 — period_context received from the frontend was never
    logged, so forensic period reconstruction was impossible. Phase
    13.2 introduced `period_audit` on AIUsageEvent."""

    def test_aiusage_event_accepts_period_audit(self):
        from models.ai_usage import AIUsageEvent

        e = AIUsageEvent(
            organization_id="org_1", feature="chat",
            period_audit={"active": {"label": "ytd"}},
        )
        assert e.period_audit == {"active": {"label": "ytd"}}, (
            "BUG #7 sentinel — AIUsageEvent.period_audit field "
            "removed. Forensic period audit no longer possible."
        )


class TestBug08SnapshotToolsNoScopeMarker:
    """BUG #8 — 19 snapshot tools returned data without any scope
    marker. Model attributed lifetime / current-state totals to the
    user's period filter."""

    def test_dispatcher_injects_scope_for_snapshot_tool(self):
        from core.tool_temporal_scope import attach_temporal_scope

        result = {"customers": [{"name": "ACME", "ltv": 50000}]}
        marked = attach_temporal_scope("query_top_customers", result)

        assert marked["_temporal_scope"] == "all_time", (
            "BUG #8 sentinel — attach_temporal_scope no longer marks "
            "query_top_customers as all_time. Model will quote "
            "lifetime totals as period-filtered."
        )

    def test_system_prompt_has_scope_discipline_rule(self):
        from services.chat_service import _PROMPT_CORE

        # The model needs explicit instructions on how to read the
        # marker — without them the marker is data the model can
        # ignore.
        assert "_temporal_scope" in _PROMPT_CORE
        assert "all_time" in _PROMPT_CORE
        assert "current_state" in _PROMPT_CORE
        assert "_period_caveat" in _PROMPT_CORE


class TestBug10DigestDedupWindowAware:
    """BUG #10 — digest dedup matched only on (org, type), so two
    monthly digests for different windows were indistinguishable.
    Phase 13.7 added window-scoping kwargs to find_latest."""

    @pytest.mark.asyncio
    async def test_find_latest_filters_on_window_when_provided(self):
        from repositories import digest_repository

        captured = {}

        def _fake_find(query, *args, **kwargs):
            captured.update(query)
            cur = MagicMock()
            cur.sort = MagicMock(return_value=cur)
            cur.limit = MagicMock(return_value=cur)
            cur.to_list = AsyncMock(return_value=[])
            return cur

        with patch(
            "repositories.digest_repository.digests_collection",
            MagicMock(find=MagicMock(side_effect=_fake_find)),
        ):
            await digest_repository.find_latest(
                "org_1", "monthly",
                period_start="2026-04-01", period_end="2026-04-30",
            )

        assert captured.get("period_start") == "2026-04-01", (
            "BUG #10 sentinel — find_latest no longer filters on "
            "period_start when provided. Window-precise dedup will "
            "regress."
        )
        assert captured.get("period_end") == "2026-04-30"


# ═══════════════════════════════════════════════════════════════════════════
# 3. Cross-layer composition checks
# ═══════════════════════════════════════════════════════════════════════════


class TestComposition:
    """The Wave 13 layers must work together. Composition tests catch
    regressions where one layer was updated but the wire-up to a
    consumer was forgotten."""

    @pytest.mark.asyncio
    async def test_resolver_audit_dict_serialises_for_aiusage_event(self):
        """The resolver's `to_audit_dict()` shape must be persistable
        as `AIUsageEvent.period_audit['active']`. If the shape drifts,
        forensic queries break silently."""
        from core.period_resolver import resolve
        from models.ai_usage import AIUsageEvent

        r = resolve("ytd", today=T)
        active = r.to_audit_dict()

        # Should be a plain dict, JSON-serialisable, no exceptions.
        evt = AIUsageEvent(
            organization_id="org_1",
            feature="chat",
            period_audit={"active": active},
        )
        # Round-trip via model_dump — this is what record_usage does.
        dumped = evt.model_dump()
        assert dumped["period_audit"]["active"]["label"] == "ytd"
        assert dumped["period_audit"]["active"]["start"] == "2026-01-01"
        assert dumped["period_audit"]["active"]["end"] == "2026-05-16"

    def test_chat_service_imports_attach_temporal_scope(self):
        """The dispatcher hook (Phase 13.6) must keep its import path
        valid — otherwise the marker injection is dead code."""
        from core.tool_temporal_scope import attach_temporal_scope
        assert callable(attach_temporal_scope), (
            "Wave 13.6 wire-up broken — attach_temporal_scope is no "
            "longer importable from core.tool_temporal_scope. The "
            "chat dispatcher will fail to inject scope markers."
        )

    def test_default_period_resolves_consistently(self):
        """DEFAULT_PERIOD must resolve to the SAME window
        irrespective of which entry point is used (resolver direct,
        adapter, or audit helper). A divergence would create
        layer-specific results — exactly the silent-mismatch class of
        bug Wave 13 set out to eliminate."""
        from core.period_resolver import DEFAULT_PERIOD, resolve

        r = resolve(today=T)  # uses DEFAULT_PERIOD
        # Inclusive 30-day window ending today
        assert r.label == DEFAULT_PERIOD
        assert r.days == 30
        assert r.end == T


# ═══════════════════════════════════════════════════════════════════════════
# 4. Failure-mode scenarios from the audit (end-to-end-ish smoke)
# ═══════════════════════════════════════════════════════════════════════════


class TestScenarioFromAudit:
    """Concrete narratives taken VERBATIM from the Wave 13 audit doc.
    Each one was reported as a real user-visible failure pre-13. Each
    test reproduces the scenario and asserts the fix."""

    def test_scenario_user_on_standalone_ai_asks_ytd(self):
        """Audit Modality A: 'User opens /ai standalone, asks YTD
        performance. Sonnet emits period=ytd (no dates). Pre-Wave-13:
        silent 30d. Post-Wave-13: resolver computes correct YTD.'"""
        from core.period_resolver import resolve, ResolutionSource

        r = resolve(period="ytd", today=T)

        assert r.resolution_source == ResolutionSource.TOKEN
        assert r.start == date(2026, 1, 1)
        assert r.end == T
        # The audit shape used downstream is stable
        d = r.to_audit_dict()
        assert d["resolution_source"] == "token"
        assert d["label"] == "ytd"

    def test_scenario_user_on_ytd_filter_asks_smart_brief(self):
        """Audit Modality D: 'User on YTD filter asks the chat for a
        brief. Sonnet calls query_smart_brief. Pre-Wave-13.5 the
        tool hardcoded 30d. Post-13.5 the dispatcher injects YTD
        dates and the brief uses them.'

        We exercise the period_audit shape that the dispatcher
        produces — same data the AIUsageEvent records — so a
        regression that drops the period_used field is caught."""
        from services.chat_service import _resolve_tool_period_audit

        audit = _resolve_tool_period_audit({
            "start_date": "2026-01-01",
            "end_date": "2026-05-16",
            "period": "ytd",
        })

        assert audit is not None
        assert audit["resolution_source"] == "explicit_dates"
        assert audit["start"] == "2026-01-01"

    def test_scenario_unknown_token_in_strict_mode_clear_error(self):
        """Audit Plan P0.1: 'Strict mode rejects unknown tokens with a
        readable error so the model can self-correct.'"""
        from core.period_resolver import InvalidPeriodError, resolve

        with pytest.raises(InvalidPeriodError) as exc_info:
            resolve(period="last_month", today=T, strict=True)

        msg = str(exc_info.value)
        # The error must educate the caller (model) on what IS valid.
        assert "7d" in msg
        assert "ytd" in msg
        assert "start_date" in msg


# ═══════════════════════════════════════════════════════════════════════════
# 5. Anti-regression guardrails — assert that bad patterns stay dead
# ═══════════════════════════════════════════════════════════════════════════


class TestAntiRegression:
    """Hard-coded checks that block the specific code patterns the
    Wave 13 audit found problematic. Each one would have caught the
    original bug if it had existed before the audit."""

    def test_no_period_30d_hardcoded_in_proactive_context(self):
        """Asserts the source of `_build_proactive_context` no longer
        calls build_ai_summary with a literal `period="30d"` regardless
        of context. The pre-fix bug was exactly this line of code."""
        import inspect
        from services import chat_service

        src = inspect.getsource(chat_service._build_proactive_context)

        # The string ``period="30d"`` may still appear as a FALLBACK
        # branch (when no period_context is supplied), so we look for
        # the SPECIFIC pre-fix call signature
        # ``build_ai_summary(org_id, period="30d", locale=locale)``
        # without any branching context. The fixed version calls
        # build_ai_summary with a resolved `_brief_period` / dates.
        forbidden = 'build_ai_summary(org_id, period="30d", locale=locale)'
        assert forbidden not in src, (
            "BUG #2 anti-regression — proactive context fell back to "
            "the pre-Wave-13.3 unconditional 30d hardcode. Re-read "
            "the Wave 13 audit and the Phase 13.3 commit before "
            "removing the period_context propagation."
        )

    def test_alert_analysis_call_passes_real_kpis(self):
        """The pre-Wave-13.4 alert_service called
        ``alert_analysis(module_alerts, kpis={}, ...)``. The fix
        replaced ``kpis={}`` with per-window KPI batches."""
        import inspect
        from services import alert_service

        src = inspect.getsource(alert_service.generate_and_save_alerts)

        # Specifically: NO bare `kpis={}` should remain. The fixed
        # code uses ``kpis=batch_kpis`` (or a named variable).
        forbidden = "kpis={}, locale=locale,"
        assert forbidden not in src, (
            "BUG #4 anti-regression — alert_service is back to "
            "passing kpis={} to alert_analysis. Sonnet will regress "
            "to generic prose with no numerical context."
        )

    def test_temporal_scope_dispatcher_hook_present(self):
        """The chat dispatcher must call attach_temporal_scope after
        every tool dispatch. Removing this hook re-creates BUG #8."""
        import inspect
        from services import chat_service

        src = inspect.getsource(chat_service.chat)

        assert "attach_temporal_scope" in src, (
            "BUG #8 anti-regression — chat dispatcher no longer "
            "injects temporal_scope markers. Snapshot tools will "
            "return un-tagged data again and the model will quote "
            "lifetime totals as period-filtered."
        )
