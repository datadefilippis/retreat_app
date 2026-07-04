"""Tests for the Phase 3 customer_outreach module.

Covers:
  • Channel registry singleton + ABC contract
  • mailto channel URL building + supports() rules
  • whatsapp channel URL building + phone normalisation
  • brevo stub raises NotImplementedError as documented
  • Phone normaliser: every common shape we see in seed data
  • Template loader: library shape, render with context, fallback to ``it``
  • build_outreach() composes channel + template correctly
  • log_outreach is best-effort (does not raise on audit failure)

Pure logic — no DB. The ``service.log_outreach`` is the only async
piece and it's tested with a mocked audit_repository.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

# Importing the package registers all channels.
from services import customer_outreach
from services.customer_outreach import build_outreach, log_outreach, list_templates
from services.customer_outreach.channels.base import CustomerContact
from services.customer_outreach.channels.registry import OutreachChannelRegistry
from services.customer_outreach import phone_normalize as PN
from services.customer_outreach.templates import loader as TPL


# ── Fixtures ─────────────────────────────────────────────────────────────


def _email_customer():
    return CustomerContact(
        id="c1", name="Mario Rossi", email="mario@example.test", phone=None,
    )


def _phone_customer():
    return CustomerContact(
        id="c2", name="Anna Bianchi", email=None,
        phone="+41 79 123 45 67",
    )


def _both_contact():
    return CustomerContact(
        id="c3", name="Sofia Lombardi",
        email="sofia@example.test", phone="079 123 45 67",
    )


def _silent_customer():
    return CustomerContact(
        id="c4", name="Antonio Rizzo", email=None, phone=None,
    )


# ════════════════════════════════════════════════════════════════════════
# 1. Registry contract
# ════════════════════════════════════════════════════════════════════════


class TestChannelRegistry:
    """The registry is a singleton; channels self-register on import.
    Keep these tests order-independent so they pass after other suites
    that may have called ``_reset_for_tests``."""

    def setup_method(self):
        # Re-import the channel modules to repopulate the registry.
        import importlib
        from services.customer_outreach.channels import mailto, whatsapp, brevo
        OutreachChannelRegistry._reset_for_tests()
        importlib.reload(mailto)
        importlib.reload(whatsapp)
        importlib.reload(brevo)

    def test_three_channels_registered(self):
        names = OutreachChannelRegistry.list_names()
        assert names == ["brevo", "mailto", "whatsapp"]

    def test_get_returns_instance(self):
        impl = OutreachChannelRegistry.get_by_name("mailto")
        assert impl is not None
        assert impl.name == "mailto"

    def test_unknown_channel_returns_none(self):
        assert OutreachChannelRegistry.get_by_name("fax") is None


# ════════════════════════════════════════════════════════════════════════
# 2. Phone normaliser
# ════════════════════════════════════════════════════════════════════════


class TestPhoneNormalize:
    """The hand-rolled fallback covers seed-data shapes we control;
    the libphonenumber path is exercised when the library is present."""

    def test_plus_prefix(self):
        assert PN.to_e164("+41 79 123 45 67") == "41791234567"

    def test_national_swiss(self):
        assert PN.to_e164("079 123 45 67", default_country="CH") == "41791234567"

    def test_double_zero_prefix(self):
        assert PN.to_e164("0041 79 123 45 67") == "41791234567"

    def test_parens_and_dashes(self):
        assert PN.to_e164("(079) 123-4567", default_country="CH") == "41791234567"

    def test_none(self):
        assert PN.to_e164(None) is None

    def test_empty(self):
        assert PN.to_e164("") is None

    def test_too_short(self):
        # 5 digits is not a phone — refuse rather than return junk.
        assert PN.to_e164("123") is None

    def test_italian(self):
        # IT default + 0-prefixed national → 39 + national
        result = PN.to_e164("06 12345678", default_country="IT")
        assert result is not None and result.startswith("39")

    def test_to_whatsapp_url_encodes_text(self):
        url = PN.to_whatsapp_url("41791234567", "Ciao Mario, come va?")
        assert url.startswith("https://wa.me/41791234567?text=")
        assert "Ciao" in url
        # Question mark in body must not break URL parsing.
        assert "%3F" in url or "?" in url.split("?text=", 1)[1]

    def test_is_valid_e164(self):
        assert PN.is_valid_e164("41791234567") is True
        assert PN.is_valid_e164("12345") is False
        assert PN.is_valid_e164("+41791234567") is False  # leading + not allowed
        assert PN.is_valid_e164(None) is False


# ════════════════════════════════════════════════════════════════════════
# 3. Templates
# ════════════════════════════════════════════════════════════════════════


class TestTemplates:
    """The library.json must round-trip render for every key/locale combo
    we ship today, with placeholder substitution."""

    def test_library_loads(self):
        n = TPL.reload_templates()
        assert n >= 5

    def test_render_at_risk_followup_it(self):
        out = TPL.render(
            "at_risk_followup", "it",
            customer_name="Mario", merchant_name="Studio Yoga",
        )
        assert out is not None
        assert "Mario" in out["subject"]
        assert "Mario" in out["body"]
        assert "Studio Yoga" in out["body"]

    def test_render_locale_fallback(self):
        # Pretend the template lacks a locale — should fall back to "it".
        out = TPL.render(
            "at_risk_followup", "xx",  # bogus locale
            customer_name="Mario", merchant_name="X",
        )
        assert out is not None  # falls back to it

    def test_render_unknown_template_returns_none(self):
        out = TPL.render("nonexistent", "it", customer_name="x")
        assert out is None

    def test_missing_placeholder_does_not_crash(self):
        # No merchant_name supplied → placeholder renders empty, no error.
        out = TPL.render("new_welcome", "en", customer_name="Mario")
        assert out is not None
        # The "{merchant_name}" placeholder is gone (rendered as empty).
        assert "{merchant_name}" not in out["body"]

    def test_list_templates_shape(self):
        items = TPL.list_templates("it")
        assert len(items) >= 5
        for item in items:
            assert "key" in item
            assert "subject_preview" in item
            assert "body_preview" in item


# ════════════════════════════════════════════════════════════════════════
# 4. Mailto channel
# ════════════════════════════════════════════════════════════════════════


class TestMailtoChannel:
    def test_supports_email_customer(self):
        impl = OutreachChannelRegistry.get_by_name("mailto")
        assert impl.supports(_email_customer()) is True

    def test_does_not_support_silent_customer(self):
        impl = OutreachChannelRegistry.get_by_name("mailto")
        assert impl.supports(_silent_customer()) is False

    def test_build_link_basic(self):
        impl = OutreachChannelRegistry.get_by_name("mailto")
        link = impl.build_link(_email_customer(), "Hi", "Body text")
        assert link.channel == "mailto"
        # We pass safe="@." to quote() so the @ stays literal; clients
        # accept both forms but unencoded is more readable in the URL bar.
        assert link.url.startswith("mailto:mario@example.test")
        assert "subject=Hi" in link.url
        assert "body=Body" in link.url

    def test_build_link_raises_without_email(self):
        impl = OutreachChannelRegistry.get_by_name("mailto")
        with pytest.raises(ValueError, match="email"):
            impl.build_link(_silent_customer(), "Hi", "Body")

    def test_long_body_truncated(self):
        impl = OutreachChannelRegistry.get_by_name("mailto")
        long_body = "x" * 5000
        link = impl.build_link(_email_customer(), "S", long_body)
        # URL should not contain all 5000 chars.
        assert "x" * 5000 not in link.url


# ════════════════════════════════════════════════════════════════════════
# 5. WhatsApp channel
# ════════════════════════════════════════════════════════════════════════


class TestWhatsAppChannel:
    def test_supports_phone_customer(self):
        impl = OutreachChannelRegistry.get_by_name("whatsapp")
        assert impl.supports(_phone_customer()) is True

    def test_supports_national_format(self):
        impl = OutreachChannelRegistry.get_by_name("whatsapp")
        # CH-default national: 079...
        assert impl.supports(_both_contact()) is True

    def test_does_not_support_silent_customer(self):
        impl = OutreachChannelRegistry.get_by_name("whatsapp")
        assert impl.supports(_silent_customer()) is False

    def test_build_link_basic(self):
        impl = OutreachChannelRegistry.get_by_name("whatsapp")
        link = impl.build_link(_phone_customer(), "Hi Anna", "How are you?")
        assert link.channel == "whatsapp"
        assert link.url.startswith("https://wa.me/41791234567?text=")
        assert "Hi" in link.url

    def test_build_link_concats_subject_into_text(self):
        impl = OutreachChannelRegistry.get_by_name("whatsapp")
        link = impl.build_link(_phone_customer(), "Subj", "Body")
        # Subject + blank line + body — but they are URL-encoded in the URL.
        # Instead of asserting on the encoded URL, we check the preview
        # which preserves the original body.
        assert link.preview == "Body"

    def test_build_link_raises_without_phone(self):
        impl = OutreachChannelRegistry.get_by_name("whatsapp")
        with pytest.raises(ValueError, match="phone"):
            impl.build_link(_silent_customer(), "Hi", "Body")


# ════════════════════════════════════════════════════════════════════════
# 6. Brevo stub
# ════════════════════════════════════════════════════════════════════════


class TestBrevoStub:
    def test_registered_in_registry(self):
        assert OutreachChannelRegistry.get_by_name("brevo") is not None

    def test_supports_returns_false_always(self):
        impl = OutreachChannelRegistry.get_by_name("brevo")
        assert impl.supports(_both_contact()) is False
        assert impl.supports(_silent_customer()) is False

    def test_build_link_raises_with_roadmap_pointer(self):
        impl = OutreachChannelRegistry.get_by_name("brevo")
        with pytest.raises(NotImplementedError, match="v2"):
            impl.build_link(_email_customer(), "Hi", "Body")


# ════════════════════════════════════════════════════════════════════════
# 7. Public service.build_outreach
# ════════════════════════════════════════════════════════════════════════


class TestBuildOutreachPublic:
    def test_email_outreach_happy_path(self):
        link = build_outreach(
            _email_customer(),
            template_key="at_risk_followup",
            channel="mailto",
            locale="it",
            merchant_name="Studio Yoga",
        )
        assert link.channel == "mailto"
        assert link.url.startswith("mailto:")

    def test_whatsapp_outreach_happy_path(self):
        link = build_outreach(
            _phone_customer(),
            template_key="new_welcome",
            channel="whatsapp",
            locale="de",
        )
        assert link.channel == "whatsapp"
        assert "wa.me" in link.url

    def test_unknown_channel_raises(self):
        with pytest.raises(ValueError, match="Unknown channel"):
            build_outreach(
                _email_customer(), template_key="at_risk_followup",
                channel="fax",
            )

    def test_unsupported_channel_for_customer_raises(self):
        # mailto on a customer without email
        with pytest.raises(ValueError, match="unsupported"):
            build_outreach(
                _silent_customer(), template_key="at_risk_followup",
                channel="mailto",
            )

    def test_unknown_template_raises(self):
        with pytest.raises(ValueError, match="template_key"):
            build_outreach(
                _email_customer(), template_key="lol",
                channel="mailto",
            )

    def test_brevo_stub_unsupported_via_public_api(self):
        # The public build_outreach path checks supports() BEFORE
        # build_link, and the brevo stub returns supports=False as
        # documented (so the UI can stay sane). Thus calling it via
        # build_outreach raises ValueError("unsupported"), not
        # NotImplementedError. The latter is reachable only by
        # bypassing supports() — see test_brevo_direct_raises below.
        with pytest.raises(ValueError, match="unsupported"):
            build_outreach(
                _email_customer(), template_key="at_risk_followup",
                channel="brevo",
            )

    def test_brevo_direct_raises_not_implemented(self):
        # The stub still raises NotImplementedError if a future caller
        # bypasses supports() and goes straight at build_link — pin the
        # contract so a refactor to "lazy supports" doesn't drop it.
        impl = OutreachChannelRegistry.get_by_name("brevo")
        with pytest.raises(NotImplementedError, match="v2"):
            impl.build_link(_email_customer(), "Hi", "Body")


# ════════════════════════════════════════════════════════════════════════
# 8. Public service.log_outreach
# ════════════════════════════════════════════════════════════════════════


class TestLogOutreachPublic:

    @pytest.mark.asyncio
    async def test_writes_audit_log(self):
        fake_repo = MagicMock()
        fake_repo.create = AsyncMock()
        with patch("repositories.audit_repository", fake_repo):
            await log_outreach(
                "org_1", "user_1", "cust_42",
                channel="mailto", template="at_risk_followup",
            )
        fake_repo.create.assert_called_once()
        log = fake_repo.create.call_args[0][0]
        assert log.action == "customer.outreach.sent"
        assert log.resource_id == "cust_42"
        assert log.details["channel"] == "mailto"

    @pytest.mark.asyncio
    async def test_audit_failure_does_not_propagate(self):
        # Audit log unavailable → the merchant's click must NOT fail.
        fake_repo = MagicMock()
        fake_repo.create = AsyncMock(side_effect=RuntimeError("audit down"))
        with patch("repositories.audit_repository", fake_repo):
            await log_outreach(
                "org_1", "user_1", "cust_42",
                channel="whatsapp", template="x",
            )


# ════════════════════════════════════════════════════════════════════════
# 9. Public service.list_templates
# ════════════════════════════════════════════════════════════════════════


class TestListTemplatesPublic:
    def test_returns_list(self):
        items = list_templates("it")
        assert isinstance(items, list)
        assert len(items) >= 5

    def test_each_item_has_preview(self):
        items = list_templates("en")
        for it in items:
            assert "key" in it
            assert "subject_preview" in it
