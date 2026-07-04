"""
Tests for locale-aware digest generation.

Covers:
- _L text table completeness (all 4 locales, all required keys)
- _rule_based_fallback produces locale-specific headings and text
- _build_user_message produces locale-specific KPI labels
- build_digest() passes locale to AI prompt (system prompt check)
- Unknown locale falls back to Italian
- Default locale (no locale param) produces Italian output

All tests mock the overview builder and Claude — no real DB or AI calls.
"""
import pytest
from unittest.mock import AsyncMock, patch


# ── Shared test data ─────────────────────────────────────────────────────────

SAMPLE_OVERVIEW = {
    "kpis": {
        "total_sales": 10000,
        "total_expenses": 3000,
        "supplier_purchases": 800,
        "fixed_costs_total": 1000,
        "net_after_fixed": 5200,
        "operating_margin_pct": 62.0,
        "total_outflow_ratio": 48.0,
        "dso": 15,
        "dpo": 30,
        "cash_conversion_cycle": -15,
        "burn_rate_total": 1600,
        "giorni_autonomia": 3,
        "break_even": 1613,
        "sales_trend_pct": 10.0,
        "expenses_trend_pct": -5.0,
    },
    "health_score": {"score": 81, "label": "Eccellente"},
    "alerts_summary": {
        "open_count": 2,
        "by_severity": {"critical": 1, "warning": 1, "info": 0},
    },
    "period": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
}


# ── Text table completeness ─────────────────────────────────────────────────


class TestDigestLocaleTable:
    """Verify _L text table has all 4 locales with required keys."""

    def test_all_four_locales_present(self):
        from modules.cashflow_monitor.digest_builder import _L

        assert set(_L.keys()) == {"it", "en", "de", "fr"}

    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_locale_has_required_top_level_keys(self, locale):
        from modules.cashflow_monitor.digest_builder import _L

        required = {"digest_type", "headings", "structure_instructions", "rules", "user_msg", "fallback"}
        assert required.issubset(set(_L[locale].keys()))

    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_headings_complete(self, locale):
        from modules.cashflow_monitor.digest_builder import _L

        required = {"summary", "key_points", "alerts", "recommendations", "outlook"}
        assert required == set(_L[locale]["headings"].keys())

    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_digest_type_labels(self, locale):
        from modules.cashflow_monitor.digest_builder import _L

        assert "weekly" in _L[locale]["digest_type"]
        assert "monthly" in _L[locale]["digest_type"]

    @pytest.mark.parametrize("locale", ["it", "en", "de", "fr"])
    def test_fallback_keys_complete(self, locale):
        from modules.cashflow_monitor.digest_builder import _L

        required = {
            "positive", "negative", "summary_tpl", "revenue", "expenses",
            "fixed_costs", "burn_rate", "days_autonomy", "alerts_tpl",
            "rec_burn", "rec_dso", "outlook_text",
        }
        assert required.issubset(set(_L[locale]["fallback"].keys()))


# ── Fallback locale tests ───────────────────────────────────────────────────


class TestRuleBasedFallbackLocale:
    """Verify _rule_based_fallback produces locale-specific text."""

    def test_italian_fallback_has_italian_headings(self):
        from modules.cashflow_monitor.digest_builder import _rule_based_fallback

        result = _rule_based_fallback(SAMPLE_OVERVIEW, "weekly", locale="it")
        assert "**Sintesi del periodo**" in result
        assert "**Punti chiave**" in result
        assert "**Alert e rischi**" in result
        assert "**Raccomandazioni**" in result
        assert "**Outlook**" in result

    def test_english_fallback_has_english_headings(self):
        from modules.cashflow_monitor.digest_builder import _rule_based_fallback

        result = _rule_based_fallback(SAMPLE_OVERVIEW, "weekly", locale="en")
        assert "**Period Summary**" in result
        assert "**Key Points**" in result
        assert "**Alerts & Risks**" in result
        assert "**Recommendations**" in result
        assert "**Outlook**" in result

    def test_german_fallback_has_german_headings(self):
        from modules.cashflow_monitor.digest_builder import _rule_based_fallback

        result = _rule_based_fallback(SAMPLE_OVERVIEW, "weekly", locale="de")
        assert "**Zusammenfassung des Zeitraums**" in result
        assert "**Kernpunkte**" in result
        assert "**Warnungen & Risiken**" in result
        assert "**Empfehlungen**" in result
        assert "**Ausblick**" in result

    def test_french_fallback_has_french_headings(self):
        from modules.cashflow_monitor.digest_builder import _rule_based_fallback

        result = _rule_based_fallback(SAMPLE_OVERVIEW, "weekly", locale="fr")
        assert "**Synth\u00e8se de la p\u00e9riode**" in result
        assert "**Points cl\u00e9s**" in result
        assert "**Alertes et risques**" in result
        assert "**Recommandations**" in result
        assert "**Perspectives**" in result

    def test_english_fallback_has_english_trend_word(self):
        from modules.cashflow_monitor.digest_builder import _rule_based_fallback

        result = _rule_based_fallback(SAMPLE_OVERVIEW, "weekly", locale="en")
        # net_after_fixed=5200 > 0 → "positive"
        assert "positive" in result

    def test_italian_fallback_has_italian_trend_word(self):
        from modules.cashflow_monitor.digest_builder import _rule_based_fallback

        result = _rule_based_fallback(SAMPLE_OVERVIEW, "weekly", locale="it")
        assert "positivo" in result

    def test_english_fallback_uses_english_labels(self):
        from modules.cashflow_monitor.digest_builder import _rule_based_fallback

        result = _rule_based_fallback(SAMPLE_OVERVIEW, "weekly", locale="en")
        assert "Revenue:" in result
        assert "Operating expenses:" in result
        assert "Fixed costs:" in result
        assert "EUR/day" in result

    def test_default_locale_is_italian(self):
        from modules.cashflow_monitor.digest_builder import _rule_based_fallback

        result = _rule_based_fallback(SAMPLE_OVERVIEW, "weekly")
        assert "**Sintesi del periodo**" in result

    def test_unknown_locale_falls_back_to_italian(self):
        from modules.cashflow_monitor.digest_builder import _rule_based_fallback

        result = _rule_based_fallback(SAMPLE_OVERVIEW, "weekly", locale="ja")
        assert "**Sintesi del periodo**" in result

    def test_fallback_contains_numeric_data(self):
        from modules.cashflow_monitor.digest_builder import _rule_based_fallback

        result = _rule_based_fallback(SAMPLE_OVERVIEW, "weekly", locale="en")
        assert "10,000" in result   # total_sales
        assert "5,200" in result    # net_after_fixed
        assert "62.0%" in result    # operating_margin_pct
        assert "81/100" in result   # health score


# ── User message locale tests ───────────────────────────────────────────────


class TestBuildUserMessageLocale:
    """Verify _build_user_message produces locale-specific KPI labels."""

    def test_italian_labels(self):
        from modules.cashflow_monitor.digest_builder import _build_user_message

        result = _build_user_message(SAMPLE_OVERVIEW, "weekly", 30, locale="it")
        assert "Ricavi totali:" in result
        assert "Spese operative:" in result
        assert "KPI PRINCIPALI" in result
        assert "SALUTE FINANZIARIA" in result

    def test_english_labels(self):
        from modules.cashflow_monitor.digest_builder import _build_user_message

        result = _build_user_message(SAMPLE_OVERVIEW, "weekly", 30, locale="en")
        assert "Total revenue:" in result
        assert "Operating expenses:" in result
        assert "KEY KPIS" in result
        assert "FINANCIAL HEALTH" in result

    def test_german_labels(self):
        from modules.cashflow_monitor.digest_builder import _build_user_message

        result = _build_user_message(SAMPLE_OVERVIEW, "weekly", 30, locale="de")
        assert "Gesamtumsatz:" in result
        assert "Betriebsausgaben:" in result
        assert "WICHTIGE KENNZAHLEN" in result

    def test_french_labels(self):
        from modules.cashflow_monitor.digest_builder import _build_user_message

        result = _build_user_message(SAMPLE_OVERVIEW, "weekly", 30, locale="fr")
        assert "Chiffre d'affaires total:" in result
        assert "Charges d'exploitation:" in result
        assert "KPI PRINCIPAUX" in result

    def test_days_unit_localized(self):
        from modules.cashflow_monitor.digest_builder import _build_user_message

        en = _build_user_message(SAMPLE_OVERVIEW, "weekly", 30, locale="en")
        de = _build_user_message(SAMPLE_OVERVIEW, "weekly", 30, locale="de")
        assert "days" in en
        assert "Tage" in de


# ── Build digest integration tests ──────────────────────────────────────────


class TestBuildDigestLocale:
    """Verify build_digest passes locale through to prompt and fallback."""

    @pytest.fixture
    def mock_deps(self):
        """Patch overview builder and Claude client.

        build_overview is a lazy import inside build_digest(), so we patch
        at the source module, not at the digest_builder import site.

        Wave 8A.0: digest_builder switched from send_message (text-only)
        to send_message_with_usage which returns (text, usage_dict). The
        fixture now patches the new function and returns the tuple shape.
        record_usage is also patched so the new tracking write does not
        try to talk to MongoDB during these locale-focused tests.
        """
        with (
            patch(
                "modules.cashflow_monitor.overview_builder.build_overview",
                new_callable=AsyncMock,
                return_value=SAMPLE_OVERVIEW,
            ) as overview,
            patch(
                "services.claude_client.send_message_with_usage",
                new_callable=AsyncMock,
            ) as send,
            patch(
                "services.claude_client.is_available",
                return_value=True,
            ) as available,
            patch(
                "services.claude_client.get_active_model",
                return_value="claude-sonnet-4-20250514",
            ),
            patch(
                "services.claude_client.calculate_cost_usd",
                return_value=0.0042,
            ),
            patch(
                "repositories.usage_repository.record_usage",
                new_callable=AsyncMock,
            ),
        ):
            send.return_value = (
                "AI-generated digest content",
                {"input_tokens": 100, "output_tokens": 50,
                 "cache_read_tokens": 0, "cache_creation_tokens": 0},
            )
            yield {
                "overview": overview,
                "send": send,
                "available": available,
            }

    async def test_ai_prompt_contains_english_instruction(self, mock_deps):
        """Wave 12.B: the prompt headers are universal markdown (## TL;DR
        etc.); the locale shows up in the respond_instruction and in the
        per-section structure instructions."""
        from modules.cashflow_monitor.digest_builder import build_digest

        await build_digest("org_1", 30, "weekly", locale="en")

        send_call = mock_deps["send"].call_args
        system_prompt = send_call[1]["system"]
        assert "Respond ONLY in English" in system_prompt
        assert "## TL;DR" in system_prompt
        # The English structure_instructions text is what differentiates locales
        assert "How is the company doing" in system_prompt

    async def test_ai_prompt_contains_italian_instruction(self, mock_deps):
        from modules.cashflow_monitor.digest_builder import build_digest

        await build_digest("org_1", 30, "weekly", locale="it")

        send_call = mock_deps["send"].call_args
        system_prompt = send_call[1]["system"]
        assert "Rispondi SOLO in italiano" in system_prompt
        assert "## TL;DR" in system_prompt
        assert "Come sta andando l'azienda" in system_prompt

    async def test_ai_prompt_contains_german_instruction(self, mock_deps):
        from modules.cashflow_monitor.digest_builder import build_digest

        await build_digest("org_1", 30, "weekly", locale="de")

        send_call = mock_deps["send"].call_args
        system_prompt = send_call[1]["system"]
        assert "Antworte NUR auf Deutsch" in system_prompt
        assert "Wie l\u00e4uft das Unternehmen" in system_prompt

    async def test_ai_prompt_contains_french_instruction(self, mock_deps):
        from modules.cashflow_monitor.digest_builder import build_digest

        await build_digest("org_1", 30, "weekly", locale="fr")

        send_call = mock_deps["send"].call_args
        system_prompt = send_call[1]["system"]
        assert "Reponds UNIQUEMENT en francais" in system_prompt
        assert "Comment va l'entreprise" in system_prompt

    async def test_digest_type_label_localized(self, mock_deps):
        from modules.cashflow_monitor.digest_builder import build_digest

        await build_digest("org_1", 30, "weekly", locale="en")
        system_en = mock_deps["send"].call_args[1]["system"]
        assert "weekly" in system_en

        mock_deps["send"].reset_mock()
        await build_digest("org_1", 30, "weekly", locale="de")
        system_de = mock_deps["send"].call_args[1]["system"]
        assert "w\u00f6chentlich" in system_de

    async def test_fallback_used_when_claude_unavailable(self, mock_deps):
        from modules.cashflow_monitor.digest_builder import build_digest

        mock_deps["available"].return_value = False

        result = await build_digest("org_1", 30, "weekly", locale="en")

        assert result is not None
        assert result["model_version"] == "rule-based"
        assert "**Period Summary**" in result["content"]
        assert "**Sintesi del periodo**" not in result["content"]

    async def test_fallback_locale_on_claude_error(self, mock_deps):
        from modules.cashflow_monitor.digest_builder import build_digest

        mock_deps["send"].side_effect = RuntimeError("API error")

        result = await build_digest("org_1", 30, "weekly", locale="fr")

        assert result is not None
        assert result["model_version"] == "rule-based"
        assert "**Synth\u00e8se de la p\u00e9riode**" in result["content"]

    async def test_default_locale_is_italian(self, mock_deps):
        from modules.cashflow_monitor.digest_builder import build_digest

        await build_digest("org_1", 30, "weekly")

        system_prompt = mock_deps["send"].call_args[1]["system"]
        assert "Rispondi SOLO in italiano" in system_prompt

    async def test_unknown_locale_falls_back_to_italian(self, mock_deps):
        from modules.cashflow_monitor.digest_builder import build_digest

        mock_deps["available"].return_value = False

        result = await build_digest("org_1", 30, "weekly", locale="ja")
        assert "**Sintesi del periodo**" in result["content"]

    async def test_user_message_localized(self, mock_deps):
        from modules.cashflow_monitor.digest_builder import build_digest

        await build_digest("org_1", 30, "weekly", locale="en")

        user_msg = mock_deps["send"].call_args[1]["user_message"]
        assert "Total revenue:" in user_msg
        assert "Ricavi totali:" not in user_msg
