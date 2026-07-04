"""
Tests for Alert Notification Service + Email Service + Digest Charts/PDF.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


class FakeAlert:
    def __init__(self, severity="high", title="Test Alert"):
        self.severity = MagicMock(value=severity)
        self.title = title
        self.summary = "Test summary"
        self.suggested_action = "Do something"


# Shared patch targets (lazy imports inside functions)
_ORG_REPO = "repositories.organization_repository"
_USERS_COL = "database.users_collection"
_CAN_USE = "services.module_access.can_use_module"
_SEND_EMAIL = "services.email_service.send_email"
_SEND_ATTACH = "services.email_service.send_email_with_attachment"
_ALERT_REPO = "repositories.alert_repository"

# Persistent rate limit — replaced the in-memory _last_high_notification dict.
# Settings live in module_configs_collection; tests mock these helpers directly.
_GET_SETTINGS = "services.alert_notification_service._get_alert_settings"
_UPDATE_RATE_LIMIT = "services.alert_notification_service._update_rate_limit"

# Per-recipient locale lookup — hits MongoDB inside the admin loop. We must
# mock it so unit tests don't try to round-trip to a closed motor loop.
_RESOLVE_LOCALE = "services.order_email_service._resolve_user_email_locale"


def _mock_admins(mock_col, emails):
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[{"email": e} for e in emails])
    mock_col.find.return_value = cursor


# ══════════════════════════════════════════════════════════════════════════════
# notify_high_severity_batch
# ══════════════════════════════════════════════════════════════════════════════

class TestNotifyHighSeverity:

    @pytest.mark.asyncio
    async def test_sends_to_admins(self):
        from services.alert_notification_service import notify_high_severity_batch

        with patch(_GET_SETTINGS, new_callable=AsyncMock, return_value={}), \
             patch(_UPDATE_RATE_LIMIT, new_callable=AsyncMock), \
             patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value={"id": "o1"}), \
             patch(_USERS_COL) as mc, \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=True), \
             patch(_SEND_EMAIL, return_value=True) as ms:
            _mock_admins(mc, ["a@t.com", "b@t.com"])
            r = await notify_high_severity_batch([FakeAlert()], "o1")
            assert r == 1
            assert ms.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_non_high(self):
        from services.alert_notification_service import notify_high_severity_batch
        r = await notify_high_severity_batch([FakeAlert("medium")], "o1")
        assert r == 0

    @pytest.mark.asyncio
    async def test_rate_limit(self):
        # Recent _last_high_email_at in settings → cooldown active → no email.
        from services.alert_notification_service import notify_high_severity_batch
        recent = datetime.now(timezone.utc).isoformat()
        with patch(_GET_SETTINGS, new_callable=AsyncMock,
                   return_value={"_last_high_email_at": recent}), \
             patch(_UPDATE_RATE_LIMIT, new_callable=AsyncMock):
            r = await notify_high_severity_batch([FakeAlert()], "o1")
            assert r == 0

    @pytest.mark.asyncio
    async def test_rate_limit_expired(self):
        # Old _last_high_email_at (>24h cooldown) → email allowed again.
        from services.alert_notification_service import notify_high_severity_batch
        old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
        with patch(_GET_SETTINGS, new_callable=AsyncMock,
                   return_value={"_last_high_email_at": old}), \
             patch(_UPDATE_RATE_LIMIT, new_callable=AsyncMock), \
             patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value={"id": "o1"}), \
             patch(_USERS_COL) as mc, \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=True), \
             patch(_SEND_EMAIL, return_value=True):
            _mock_admins(mc, ["a@t.com"])
            r = await notify_high_severity_batch([FakeAlert()], "o1")
            assert r == 1

    @pytest.mark.asyncio
    async def test_no_org(self):
        from services.alert_notification_service import notify_high_severity_batch
        with patch(_GET_SETTINGS, new_callable=AsyncMock, return_value={}), \
             patch(_UPDATE_RATE_LIMIT, new_callable=AsyncMock), \
             patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value=None), \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=True):
            r = await notify_high_severity_batch([FakeAlert()], "o1")
            assert r == 0

    @pytest.mark.asyncio
    async def test_feature_disabled(self):
        from services.alert_notification_service import notify_high_severity_batch
        with patch(_GET_SETTINGS, new_callable=AsyncMock, return_value={}), \
             patch(_UPDATE_RATE_LIMIT, new_callable=AsyncMock), \
             patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value={"id": "o1"}), \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=False):
            r = await notify_high_severity_batch([FakeAlert()], "o1")
            assert r == 0

    @pytest.mark.asyncio
    async def test_no_admins(self):
        from services.alert_notification_service import notify_high_severity_batch
        with patch(_GET_SETTINGS, new_callable=AsyncMock, return_value={}), \
             patch(_UPDATE_RATE_LIMIT, new_callable=AsyncMock), \
             patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value={"id": "o1"}), \
             patch(_USERS_COL) as mc, \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=True):
            _mock_admins(mc, [])
            r = await notify_high_severity_batch([FakeAlert()], "o1")
            assert r == 0

    @pytest.mark.asyncio
    async def test_email_failure(self):
        from services.alert_notification_service import notify_high_severity_batch
        with patch(_GET_SETTINGS, new_callable=AsyncMock, return_value={}), \
             patch(_UPDATE_RATE_LIMIT, new_callable=AsyncMock), \
             patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value={"id": "o1"}), \
             patch(_USERS_COL) as mc, \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=True), \
             patch(_SEND_EMAIL, return_value=False):
            _mock_admins(mc, ["a@t.com"])
            r = await notify_high_severity_batch([FakeAlert()], "o1")
            assert r == 0


# ══════════════════════════════════════════════════════════════════════════════
# send_weekly_alert_digest
# ══════════════════════════════════════════════════════════════════════════════

class TestWeeklyAlertDigest:

    @pytest.mark.asyncio
    async def test_sends_digest(self):
        from services.alert_notification_service import send_weekly_alert_digest
        with patch(_GET_SETTINGS, new_callable=AsyncMock, return_value={}), \
             patch(f"{_ALERT_REPO}.find_open_alerts_for_digest", new_callable=AsyncMock,
                   return_value=[{"title": "X", "severity": "high"}]), \
             patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value={"id": "o1"}), \
             patch(_USERS_COL) as mc, \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=True), \
             patch(_RESOLVE_LOCALE, new_callable=AsyncMock, return_value="it"), \
             patch(_SEND_EMAIL, return_value=True) as ms:
            _mock_admins(mc, ["a@t.com"])
            r = await send_weekly_alert_digest("o1")
            assert r == 1
            assert ms.call_count == 1

    @pytest.mark.asyncio
    async def test_no_alerts(self):
        from services.alert_notification_service import send_weekly_alert_digest
        with patch(f"{_ALERT_REPO}.find_open_alerts_for_digest", new_callable=AsyncMock, return_value=[]):
            r = await send_weekly_alert_digest("o1")
            assert r == 0

    @pytest.mark.asyncio
    async def test_feature_disabled(self):
        from services.alert_notification_service import send_weekly_alert_digest
        with patch(f"{_ALERT_REPO}.find_open_alerts_for_digest", new_callable=AsyncMock,
                   return_value=[{"title": "X", "severity": "high"}]), \
             patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value={"id": "o1"}), \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=False):
            r = await send_weekly_alert_digest("o1")
            assert r == 0


# ══════════════════════════════════════════════════════════════════════════════
# send_digest_report_email
# ══════════════════════════════════════════════════════════════════════════════

class TestDigestReportEmail:

    @pytest.mark.asyncio
    async def test_sends_pdf(self):
        from services.alert_notification_service import send_digest_report_email
        with patch(_GET_SETTINGS, new_callable=AsyncMock, return_value={}), \
             patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value={"id": "o1"}), \
             patch(_USERS_COL) as mc, \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=True), \
             patch(_RESOLVE_LOCALE, new_callable=AsyncMock, return_value="it"), \
             patch(_SEND_ATTACH, return_value=True) as ms:
            _mock_admins(mc, ["a@t.com"])
            r = await send_digest_report_email("o1", b"pdf", {"snapshot": {}, "alerts_count": 0})
            assert r == 1
            assert ms.call_count == 1

    @pytest.mark.asyncio
    async def test_feature_disabled(self):
        from services.alert_notification_service import send_digest_report_email
        with patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value={"id": "o1"}), \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=False):
            r = await send_digest_report_email("o1", b"pdf", {})
            assert r == 0

    @pytest.mark.asyncio
    async def test_attachment_failure(self):
        from services.alert_notification_service import send_digest_report_email
        with patch(f"{_ORG_REPO}.find_by_id", new_callable=AsyncMock, return_value={"id": "o1"}), \
             patch(_USERS_COL) as mc, \
             patch(_CAN_USE, new_callable=AsyncMock, return_value=True), \
             patch(_SEND_ATTACH, return_value=False):
            _mock_admins(mc, ["a@t.com"])
            r = await send_digest_report_email("o1", b"pdf", {"snapshot": {}, "alerts_count": 0})
            assert r == 0


# ══════════════════════════════════════════════════════════════════════════════
# Email Service
# ══════════════════════════════════════════════════════════════════════════════

class TestEmailService:
    def test_dry_run_returns_false(self):
        from services.email_service import send_email, _configured
        if _configured: pytest.skip("Brevo configured")
        assert send_email("a@b.com", "S", "<p>H</p>") is False

    def test_attachment_dry_run_returns_false(self):
        from services.email_service import send_email_with_attachment, _configured
        if _configured: pytest.skip("Brevo configured")
        assert send_email_with_attachment("a@b.com", "S", "<p>H</p>", b"x", "f.pdf") is False

    def test_returns_bool(self):
        from services.email_service import send_email
        assert isinstance(send_email("a@b.com", "S", "<p>H</p>"), bool)


# ══════════════════════════════════════════════════════════════════════════════
# Locale Subjects
# ══════════════════════════════════════════════════════════════════════════════

class TestLocaleSubjects:
    LOCALES = ["it", "en", "de", "fr"]

    def test_high_alert_subjects(self):
        from services.alert_notification_service import _SUBJECTS
        for loc in self.LOCALES:
            assert loc in _SUBJECTS
            assert "high_alert" in _SUBJECTS[loc]

    def test_digest_subjects(self):
        from services.alert_notification_service import _DIGEST_SUBJECTS
        for loc in self.LOCALES:
            assert loc in _DIGEST_SUBJECTS
            assert "weekly" in _DIGEST_SUBJECTS[loc]
            assert "monthly" in _DIGEST_SUBJECTS[loc]


# ══════════════════════════════════════════════════════════════════════════════
# Charts
# ══════════════════════════════════════════════════════════════════════════════

class TestCharts:
    def test_daily_png(self):
        from modules.cashflow_monitor.digest_charts import generate_daily_chart
        r = generate_daily_chart({"2026-04-01": 1000}, {"2026-04-01": 500})
        assert r[:4] == b'\x89PNG'

    def test_cumulative_png(self):
        from modules.cashflow_monitor.digest_charts import generate_cumulative_chart
        r = generate_cumulative_chart({"2026-04-01": 1000}, {"2026-04-01": 500})
        assert r[:4] == b'\x89PNG'

    def test_category_png(self):
        from modules.cashflow_monitor.digest_charts import generate_category_chart
        r = generate_category_chart([{"_id": "A", "total": 100}], "T")
        assert r[:4] == b'\x89PNG'

    def test_health_png(self):
        from modules.cashflow_monitor.digest_charts import generate_health_gauge
        r = generate_health_gauge(50, "OK")
        assert r[:4] == b'\x89PNG'

    def test_empty_data(self):
        from modules.cashflow_monitor.digest_charts import generate_daily_chart
        r = generate_daily_chart({}, {})
        assert isinstance(r, bytes) and len(r) > 50


# ══════════════════════════════════════════════════════════════════════════════
# PDF
# ══════════════════════════════════════════════════════════════════════════════

class TestPDF:
    def _charts(self):
        from modules.cashflow_monitor.digest_charts import (
            generate_daily_chart, generate_cumulative_chart,
            generate_category_chart, generate_health_gauge,
        )
        s = {"2026-04-01": 1000}
        e = {"2026-04-01": 500}
        return {
            "daily": generate_daily_chart(s, e),
            "cumulative": generate_cumulative_chart(s, e),
            "categories_revenue": generate_category_chart([{"_id": "A", "total": 1000}], "R"),
            "categories_expense": generate_category_chart([{"_id": "B", "total": 500}], "E"),
            "health": generate_health_gauge(75, "OK"),
        }

    def test_valid_pdf(self):
        from modules.cashflow_monitor.digest_pdf import build_report_pdf
        r = build_report_pdf("Org", "1-7 Apr", "weekly",
            {"total_sales": 10000, "total_outflows": 7000, "net_after_fixed": 3000, "operating_margin_pct": 30},
            {"score": 75, "label": "OK"}, self._charts(), [], None, None)
        assert r[:5] == b'%PDF-'

    def test_pdf_without_ai(self):
        from modules.cashflow_monitor.digest_pdf import build_report_pdf
        r = build_report_pdf("Org", "T", "weekly",
            {"total_sales": 5000, "total_outflows": 4000, "net_after_fixed": 1000, "operating_margin_pct": 20},
            {"score": 60, "label": "?"}, self._charts(), [], None, None, is_starter=True)
        assert r[:5] == b'%PDF-'

    def test_all_locales(self):
        from modules.cashflow_monitor.digest_pdf import build_report_pdf
        kpis = {"total_sales": 10000, "total_outflows": 7000, "net_after_fixed": 3000, "operating_margin_pct": 30}
        for loc in ["it", "en", "de", "fr"]:
            r = build_report_pdf("Org", "T", "weekly", kpis, {"score": 80, "label": "OK"},
                                 self._charts(), [], None, None, locale=loc)
            assert r[:5] == b'%PDF-', f"Failed for {loc}"

    def test_negative_margin_critical(self):
        from modules.cashflow_monitor.digest_pdf import _build_verdict, _build_assessment, _g
        t = _g("it")
        kpis = {"total_sales": 5000, "total_outflows": 15000, "total_expenses": 10000,
                "supplier_purchases": 4000, "fixed_costs_total": 1000, "operating_margin_pct": -200}
        v = _build_verdict(kpis, t, {})
        assert "superano" in v

        a, lvl = _build_assessment({"score": 10, "top_issues": []}, [], kpis, t)
        assert lvl == "critical"
