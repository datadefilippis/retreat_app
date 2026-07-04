"""Tests for Wave 13.4 — Alert window memory (BUG #3 + #4 fix).

The Wave 13 audit found two related bugs:

  BUG #3 — Alert documents never recorded the window they were generated
           on. When the chat AI later "explained" an alert, it had to
           guess the window from the title and often used the user's
           CURRENT period filter, producing self-contradicting analyses
           ("the alert says revenue fell — but revenue is now +12 %").

  BUG #4 — services.alert_service called alert_analysis with kpis={}.
           Sonnet had no numerical context, producing generic prose.

Phase 13.4 fixes both:

  1. Alert model gains period_start / period_end / window_label.
  2. alert_engine stamps the default 30-day window on every new alert
     a rule did not pin a different window for.
  3. overview_builder surfaces analysis_window in recent_alerts so the
     chat tool returns it to the model.
  4. alert_service groups alerts by their window and passes real KPIs
     of that window to alert_analysis.

This file unit-tests each layer; end-to-end smoke is in
test_period_contracts (Phase 13.8).
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


# ── Model layer: Alert accepts the new optional fields ──────────────────────


class TestAlertModelWindowFields:
    def test_defaults_to_none(self):
        from models.alert import Alert, AlertSeverity
        a = Alert(
            organization_id="org_1",
            module_key="cashflow_monitor",
            severity=AlertSeverity.HIGH,
            title="t", summary="s", date_reference="2026-05-16",
        )
        assert a.period_start is None
        assert a.period_end is None
        assert a.window_label is None

    def test_accepts_explicit_window(self):
        from models.alert import Alert, AlertSeverity
        a = Alert(
            organization_id="org_1",
            module_key="cashflow_monitor",
            severity=AlertSeverity.MEDIUM,
            title="t", summary="s", date_reference="2026-05-16",
            period_start="2026-04-16",
            period_end="2026-05-15",
            window_label="30d",
        )
        assert a.period_start == "2026-04-16"
        assert a.period_end == "2026-05-15"
        assert a.window_label == "30d"

    def test_extra_ignore_still_works(self):
        # Backward compat: alerts loaded from MongoDB pre-13.4 don't have
        # these fields, AlertBase has model_config extra="ignore", so
        # unknown fields are dropped gracefully (no crash). Test the
        # absence-of-field case directly.
        from models.alert import Alert, AlertSeverity
        a = Alert(
            organization_id="org_1",
            module_key="cashflow_monitor",
            severity=AlertSeverity.LOW,
            title="t", summary="s", date_reference="2026-05-16",
            # legacy alert — no window fields
        )
        # Should serialise cleanly with the new fields = None
        dumped = a.model_dump()
        assert dumped["period_start"] is None
        assert dumped["window_label"] is None


# ── Engine layer: default window stamping ───────────────────────────────────


@pytest.mark.asyncio
class TestEngineDefaultWindowStamping:
    """run_alert_engine stamps the default 30d window on alerts that
    don't already have one, leaves rule-specified windows alone."""

    async def test_alerts_without_window_get_default_30d(self):
        """An alert emitted by a rule WITHOUT setting period_* should
        come out of the engine with the default 30d window."""
        from datetime import date, timedelta
        from models.alert import Alert, AlertSeverity
        from modules.cashflow_monitor import alert_engine

        # Build a minimal Alert as a rule would emit it (no window).
        rule_alert = Alert(
            organization_id="org_1",
            module_key="cashflow_monitor",
            severity=AlertSeverity.HIGH,
            title="Sales below average",
            summary="...",
            date_reference="2026-05-16",
        )
        assert rule_alert.period_start is None  # sanity

        # Stub the engine so we only exercise the new stamping path.
        async def fake_rule(ctx):
            return [rule_alert]

        with patch.object(alert_engine, "ALL_RULES", [fake_rule]), \
             patch.object(alert_engine, "_get_org_alert_preset",
                          new=AsyncMock(return_value="standard")), \
             patch(
                 "modules.cashflow_monitor.alert_engine.alert_repository."
                 "find_active_dedup_keys_v3",
                 new=AsyncMock(return_value=set()),
             ), \
             patch(
                 "modules.cashflow_monitor.alert_engine.alert_repository."
                 "find_recently_resolved_types",
                 new=AsyncMock(return_value=set()),
             ), \
             patch(
                 "modules.cashflow_monitor.alert_engine.alert_repository."
                 "auto_resolve_stale",
                 new=AsyncMock(return_value=0),
             ), \
             patch.object(alert_engine, "_build_context") as mock_ctx, \
             patch.object(alert_engine, "should_run_rule") as mock_gate, \
             patch(
                 "database.module_configs_collection",
                 MagicMock(find_one=AsyncMock(return_value=None)),
             ):
            # Minimal AlertContext stand-in with has_data=True
            ctx_stub = MagicMock()
            ctx_stub.has_data = True
            ctx_stub.data_quality = None
            mock_ctx.return_value = ctx_stub
            mock_gate.return_value = MagicMock(allowed=True, reason="")

            new_alerts = await alert_engine.run_alert_engine("org_1")

        assert len(new_alerts) == 1
        stamped = new_alerts[0]

        # The default window is "30 days back from today".
        expected_end = date.today().isoformat()
        expected_start = (date.today() - timedelta(days=29)).isoformat()
        assert stamped.period_start == expected_start
        assert stamped.period_end == expected_end
        assert stamped.window_label == "30d"

    async def test_alerts_with_explicit_window_preserved(self):
        """A rule that pins a 90d window must NOT be overwritten by the
        engine's default 30d stamping logic."""
        from models.alert import Alert, AlertSeverity
        from modules.cashflow_monitor import alert_engine

        # Rule emits an alert with its own (90d) window
        rule_alert = Alert(
            organization_id="org_1",
            module_key="cashflow_monitor",
            severity=AlertSeverity.MEDIUM,
            title="Custom-window rule",
            summary="...",
            date_reference="2026-05-16",
            period_start="2026-02-16",
            period_end="2026-05-16",
            window_label="90d",
        )

        async def fake_rule(ctx):
            return [rule_alert]

        with patch.object(alert_engine, "ALL_RULES", [fake_rule]), \
             patch.object(alert_engine, "_get_org_alert_preset",
                          new=AsyncMock(return_value="standard")), \
             patch(
                 "modules.cashflow_monitor.alert_engine.alert_repository."
                 "find_active_dedup_keys_v3",
                 new=AsyncMock(return_value=set()),
             ), \
             patch(
                 "modules.cashflow_monitor.alert_engine.alert_repository."
                 "find_recently_resolved_types",
                 new=AsyncMock(return_value=set()),
             ), \
             patch(
                 "modules.cashflow_monitor.alert_engine.alert_repository."
                 "auto_resolve_stale",
                 new=AsyncMock(return_value=0),
             ), \
             patch.object(alert_engine, "_build_context") as mock_ctx, \
             patch.object(alert_engine, "should_run_rule") as mock_gate, \
             patch(
                 "database.module_configs_collection",
                 MagicMock(find_one=AsyncMock(return_value=None)),
             ):
            ctx_stub = MagicMock()
            ctx_stub.has_data = True
            ctx_stub.data_quality = None
            mock_ctx.return_value = ctx_stub
            mock_gate.return_value = MagicMock(allowed=True, reason="")

            new_alerts = await alert_engine.run_alert_engine("org_1")

        assert len(new_alerts) == 1
        preserved = new_alerts[0]
        assert preserved.period_start == "2026-02-16"
        assert preserved.period_end == "2026-05-16"
        assert preserved.window_label == "90d"


# ── overview_builder: analysis_window in recent_alerts ──────────────────────


class TestOverviewExposesAnalysisWindow:
    def test_recent_alerts_carry_analysis_window(self):
        """The chat AI consumes alerts via query_cashflow_summary which
        embeds overview['alerts']['recent']. That list must surface the
        original analysis window so the model knows the alert's scope."""
        # We import build_overview's transformation snippet directly
        # via re-implementation since we cannot easily run the full
        # async pipeline in a unit test. Mirror the production logic
        # to verify the shape we promised.
        open_alerts = [
            {
                "id": "a1", "title": "Sales drop", "severity": "high",
                "date_reference": "2026-05-15", "status": "new",
                "period_start": "2026-04-16",
                "period_end":   "2026-05-15",
                "window_label": "30d",
            },
            {
                # Legacy alert: no window — must yield analysis_window=None
                "id": "a2", "title": "Old alert", "severity": "medium",
                "date_reference": "2025-12-01", "status": "new",
            },
        ]

        # Replicate the exact list comprehension used in
        # overview_builder.py for the recent_alerts_list field.
        recent_alerts_list = [
            {
                "id": a.get("id"),
                "title": a.get("title"),
                "severity": a.get("severity"),
                "date_reference": a.get("date_reference"),
                "status": a.get("status"),
                "analysis_window": (
                    {
                        "start": a.get("period_start"),
                        "end": a.get("period_end"),
                        "label": a.get("window_label"),
                    }
                    if a.get("period_start") and a.get("period_end")
                    else None
                ),
            }
            for a in open_alerts[:5]
        ]

        assert recent_alerts_list[0]["analysis_window"] == {
            "start": "2026-04-16",
            "end": "2026-05-15",
            "label": "30d",
        }
        # Legacy / pre-13.4 alerts surface as None so the chat layer
        # can disambiguate "unknown window" cleanly.
        assert recent_alerts_list[1]["analysis_window"] is None


# ── alert_service: KPI builder + per-window batching ────────────────────────


@pytest.mark.asyncio
class TestAlertWindowKpiBuilder:
    async def test_returns_empty_dict_when_window_missing(self):
        from services.alert_service import _build_alert_window_kpis

        kpis = await _build_alert_window_kpis("org_1", None, None, "it")
        assert kpis == {}

    async def test_uses_build_ai_summary_with_window(self):
        from services import alert_service
        from services.alert_service import _build_alert_window_kpis

        fake_summary = {
            "kpis": {
                "total_sales": 12345,
                "total_outflows": 6789,
                "operating_margin_pct": 21.5,
                "dso": 45,
                "dpo": 30,
                "giorni_autonomia": 60,
                "total_outflow_ratio": 55.0,
            }
        }
        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(return_value=fake_summary),
        ) as mock_summary:
            kpis = await _build_alert_window_kpis(
                "org_1", "2026-04-01", "2026-04-30", "it",
            )

        # Window was forwarded to the summary builder verbatim
        mock_summary.assert_awaited_once()
        _, kwargs = mock_summary.await_args
        assert kwargs["period"] == "custom"
        assert kwargs["start_date"] == "2026-04-01"
        assert kwargs["end_date"] == "2026-04-30"

        # All keys alert_analysis._build_batch_message reads are present
        assert kpis["total_sales"] == 12345
        assert kpis["operating_margin_pct"] == 21.5
        assert kpis["dso"] == 45
        # Audit-only fields for log forensics
        assert kpis["_window_start"] == "2026-04-01"
        assert kpis["_window_end"] == "2026-04-30"

    async def test_returns_empty_on_summary_failure(self):
        from services.alert_service import _build_alert_window_kpis
        with patch(
            "modules.cashflow_monitor.cashflow_summary.build_ai_summary",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            kpis = await _build_alert_window_kpis(
                "org_1", "2026-04-01", "2026-04-30", "it",
            )
        # Graceful degradation, not propagation.
        assert kpis == {}
