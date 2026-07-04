"""Wave GDPR-Admin Phase A — sentinel tests for hard-delete pipeline.

Scope: only the NEW 7-day warning email job + verification that the
pre-existing hard-delete machinery is wired correctly. We do NOT
re-test cascade_hard_delete itself (separate sentinel exists for that
since v6.0).

The Wave GDPR-Admin Phase A adds:
  - email_service.send_final_delete_warning (i18n in it/en/de/fr)
  - background_service._hard_delete_warning_job (runs every 12h)
  - organization.hard_delete_warning_sent_at field for idempotency

Tests verify:
  1. The email function exists and renders the 4 locales without
     KeyError on the i18n template.
  2. The job is wired into the scheduler startup task list.
  3. The selection cursor picks orgs in the correct 7-day window AND
     skips already-warned orgs.
  4. The idempotency flag is set after a successful send.
  5. The pre-existing hard-delete cleanup job remains untouched (no
     accidental regression on its 6h interval / 30-day grace constants).
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Email function: i18n coverage ────────────────────────────────────────


class TestFinalDeleteWarningEmail:
    """The email renders in all 4 locales without missing i18n keys."""

    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_send_final_delete_warning_renders_locale(self, locale):
        from services.email_service import send_final_delete_warning

        # Patch send_email at module level so we capture the rendered
        # HTML + subject without actually hitting Brevo.
        captured = {}

        def _fake_send(to_email, subject, html, **kw):
            captured["to"] = to_email
            captured["subject"] = subject
            captured["html"] = html
            return True

        with patch("services.email_service.send_email", _fake_send):
            ok = send_final_delete_warning(
                to_email="test@example.com",
                org_name="Macelleria Test",
                days_ago=23,
                delete_date_str="2026-06-15",
                locale=locale,
            )

        assert ok is True
        # The subject must mention the org name (interpolation worked)
        assert "Macelleria Test" in captured["subject"], (
            f"Wave GDPR-Admin A — locale={locale!r}: subject missing "
            f"org_name interpolation. Got: {captured.get('subject')!r}"
        )
        # The body must mention BOTH days_ago and delete_date
        assert "23" in captured["html"], (
            f"locale={locale!r}: days_ago=23 not in body"
        )
        assert "2026-06-15" in captured["html"], (
            f"locale={locale!r}: delete_date not in body"
        )
        # No raw {placeholder} leakage
        assert "{org_name}" not in captured["html"]
        assert "{days_ago}" not in captured["html"]
        assert "{delete_date}" not in captured["html"]

    def test_unknown_locale_falls_back_to_italian(self):
        """If a user has locale='xx' (corrupted), the email helper
        should still render — fallback to it via _t()."""
        from services.email_service import send_final_delete_warning

        captured = {}

        def _fake_send(to_email, subject, html, **kw):
            captured["html"] = html
            return True

        with patch("services.email_service.send_email", _fake_send):
            ok = send_final_delete_warning(
                to_email="test@example.com",
                org_name="Org",
                days_ago=23,
                delete_date_str="2026-06-15",
                locale="xx-invalid",
            )

        assert ok is True
        # Some content rendered — the _t() helper falls back gracefully.
        assert len(captured.get("html", "")) > 100


# ── Background job wiring ────────────────────────────────────────────────


class TestSchedulerWiring:
    """The new warning job is registered in the scheduler startup."""

    def test_warning_job_in_startup_tasks(self):
        import inspect
        from services import background_service

        src = inspect.getsource(background_service)
        assert "_hard_delete_warning_job" in src
        assert 'name="hard_delete_warning_job"' in src

    def test_cleanup_job_constants_unchanged(self):
        """Wave GDPR-Admin A must NOT change the pre-existing
        hard-delete cleanup parameters."""
        from services.background_service import (
            _HARD_DELETE_CHECK_INTERVAL_HOURS,
            _HARD_DELETE_GRACE_DAYS,
        )
        assert _HARD_DELETE_GRACE_DAYS == 30, (
            "Pre-existing 30-day grace period must not be modified."
        )
        # 6h interval is the deployed default
        assert _HARD_DELETE_CHECK_INTERVAL_HOURS in (6, 6.0), (
            "Pre-existing 6h cleanup interval must not be modified."
        )

    def test_warning_job_constants_are_sane(self):
        from services.background_service import (
            _HARD_DELETE_WARNING_INTERVAL_HOURS,
            _HARD_DELETE_WARNING_LEAD_DAYS,
            _HARD_DELETE_GRACE_DAYS,
        )
        # Warning lead must be > 0 and strictly less than grace
        assert 0 < _HARD_DELETE_WARNING_LEAD_DAYS < _HARD_DELETE_GRACE_DAYS
        # Interval is positive
        assert _HARD_DELETE_WARNING_INTERVAL_HOURS > 0


# ── Idempotency: warning is NOT sent twice ───────────────────────────────


@pytest.mark.asyncio
async def test_warning_job_skips_already_warned_orgs():
    """The selection cursor must filter out orgs where
    hard_delete_warning_sent_at is already set."""
    import inspect
    from services import background_service

    src = inspect.getsource(background_service._hard_delete_warning_job)
    # The cursor must check the warning flag
    assert "hard_delete_warning_sent_at" in src
    assert "$exists" in src or "None" in src
    # Must filter by the date window
    assert "warning_cutoff" in src
    assert "grace_cutoff" in src


@pytest.mark.asyncio
async def test_warning_job_marks_org_after_send():
    """The job sets hard_delete_warning_sent_at on the org doc after
    sending so the next tick doesn't re-send."""
    import inspect
    from services import background_service
    src = inspect.getsource(background_service._hard_delete_warning_job)
    assert "hard_delete_warning_sent_at" in src
    assert "update_one" in src
    assert '"$set"' in src


# ── Selection window correctness ─────────────────────────────────────────


class TestSelectionWindow:
    """Verify the math of warning_cutoff and grace_cutoff."""

    def test_warning_window_math(self):
        """For grace=30, lead=7: warning fires when deactivated_at is
        between (now - 30d) and (now - 23d). Confirm via direct
        computation."""
        from services.background_service import (
            _HARD_DELETE_GRACE_DAYS,
            _HARD_DELETE_WARNING_LEAD_DAYS,
        )
        now = datetime.now(timezone.utc)
        warning_cutoff = now - timedelta(
            days=_HARD_DELETE_GRACE_DAYS - _HARD_DELETE_WARNING_LEAD_DAYS
        )
        grace_cutoff = now - timedelta(days=_HARD_DELETE_GRACE_DAYS)

        # warning_cutoff is more recent than grace_cutoff
        assert warning_cutoff > grace_cutoff

        # A deactivation 25 days ago is in the window
        sample = now - timedelta(days=25)
        assert grace_cutoff <= sample < warning_cutoff

        # A deactivation 5 days ago is NOT in the window
        too_recent = now - timedelta(days=5)
        assert too_recent >= warning_cutoff  # filtered out

        # A deactivation 35 days ago is NOT in the window (past grace)
        too_old = now - timedelta(days=35)
        assert too_old < grace_cutoff  # filtered out


# ── i18n key presence ────────────────────────────────────────────────────


class TestI18nKeysPresent:
    """All 4 locales must define the 6 new warning email keys."""

    REQUIRED_KEYS = [
        "final_delete_warning_subject",
        "final_delete_warning_intro",
        "final_delete_warning_body",
        "final_delete_warning_reactivate",
        "final_delete_warning_export",
        "final_delete_warning_no_action",
    ]

    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_locale_has_all_keys(self, locale):
        from services.email_service import EMAIL_TRANSLATIONS
        strings = EMAIL_TRANSLATIONS.get(locale)
        assert strings is not None
        for key in self.REQUIRED_KEYS:
            assert key in strings, (
                f"Wave GDPR-Admin A — locale={locale!r} missing key "
                f"{key!r}. Add it to email_service.EMAIL_TRANSLATIONS[{locale!r}]."
            )


# ── data-retention.md doc updated ────────────────────────────────────────


class TestDocsUpdated:
    """The data-retention.md must reference the new pipeline."""

    def test_doc_mentions_warning_pipeline(self):
        doc_path = (
            BACKEND_DIR.parent / "docs" / "operations" / "data-retention.md"
        )
        if not doc_path.exists():
            pytest.skip(f"docs file not at {doc_path}")
        text = doc_path.read_text()
        # The doc must explain the new warning pipeline
        assert "_hard_delete_warning_job" in text
        assert "Wave GDPR-Admin A" in text
        assert "hard_delete_warning_sent_at" in text
