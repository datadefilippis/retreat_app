"""Wave Digest-Consistency — sentinel tests (2026-05-16).

Root cause of the +4.1% vs +3.0% YoY discrepancy:

  digest_builder._build_user_message used to send Claude:
    - kpis.sales_trend_pct = +4.1% (MoM, vs prev period)
    - yoy.total_sales = 78,884 EUR (+3.0% YoY)
  but the labels were ambiguous and "Trend ricavi: +4.1%" was the
  most prominent percentage. Claude conflated MoM with YoY in the
  narrative ("ricavi in crescita +4,1% rispetto al periodo precedente
  E +4,1% YoY"), back-calculating an incorrect prior-year baseline.

Fix:
  1. Restructure YoY section in user_message to present each metric
     SIDE-BY-SIDE: "current EUR (corrente) vs prior EUR (precedente)
     -> +X.X%". Add a NOTA instructing Claude to always cite both
     absolute values.
  2. Rename MoM trend fields to "Trend ricavi (vs periodo precedente)"
     so the LLM cannot confuse them with YoY.
  3. Add a new reasoning rule (1bis) in the system prompt MANDATING
     absolute from/to values when citing percentage variations.

These tests lock in the user-message + system-prompt contracts.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Sample overview fixture matching the prod Macelleria YTD 2026 ───────


def _fixture_overview():
    """A minimal overview dict matching the prod Macelleria YTD 2026
    structure — used by all user_message tests."""
    return {
        "period": {
            "start_date": "2026-01-01",
            "end_date":   "2026-05-16",
            "days": 136,
        },
        "kpis": {
            "total_sales": 81275.63,
            "total_expenses": 17754.76,
            "supplier_purchases": 58380.41,
            "fixed_costs_total": 5337.11,
            "net_after_fixed": -196.65,
            "operating_margin_pct": 6.3,
            "total_outflow_ratio": 100.2,
            "dso": 0,
            "dpo": 0,
            "burn_rate_total": 0,
            "giorni_autonomia": 0,
            "sales_trend_pct": 3.0,
            "expenses_trend_pct": -2.8,
            "period_days": 136,
        },
        "health_score": {
            "score": 41,
            "label": "Critico",
            "trend": "stabile",
            "breakdown": [],
        },
        "alerts": {"open_count": 1, "by_severity": {"high": 1}},
        "yoy": {
            "has_data": True,
            "period_start": "2025-01-01",
            "period_end":   "2025-05-16",
            "total_sales": 78884.94,
            "total_expenses": 18269.29,
            "supplier_purchases": 56148.03,
            "net_after_fixed": -1582.25,
            "total_outflows": 79767.19,
            "pct": {
                "total_sales": 3.0,
                "total_expenses": -2.8,
                "supplier_purchases": 4.0,
                "net_after_fixed": 87.6,
                "operating_margin_pct": 10.5,
                "total_outflow_ratio": None,
            },
        },
        "categories": {},
        "suppliers": {},
    }


# ── D1: YoY section is side-by-side and unambiguous ──────────────────────


class TestYoYSectionStructure:
    def test_yoy_section_includes_both_absolutes_and_percentages(self):
        from modules.cashflow_monitor.digest_builder import _build_user_message
        msg = _build_user_message(_fixture_overview(), "monthly", 136, "it")

        # The YoY header is present
        assert "YEAR-OVER-YEAR" in msg
        # Both periods are explicitly labelled
        assert "Periodo corrente:" in msg
        assert "Periodo confronto:" in msg
        # Current period date
        assert "2026-01-01" in msg
        assert "2026-05-16" in msg
        # Prior-year period date
        assert "2025-01-01" in msg
        assert "2025-05-16" in msg

    def test_yoy_rows_show_side_by_side_current_vs_prior(self):
        from modules.cashflow_monitor.digest_builder import _build_user_message
        msg = _build_user_message(_fixture_overview(), "monthly", 136, "it")

        # Each row format: "<label>: <cur> EUR (corrente) vs <prior> EUR (precedente) -> +X.X%"
        # Sales row must have both absolutes
        assert "81.276 EUR (corrente)" in msg or "81,276 EUR (corrente)" in msg
        assert "78.885 EUR (precedente)" in msg or "78,885 EUR (precedente)" in msg
        # Expense row
        assert "17.755 EUR (corrente)" in msg or "17,755 EUR (corrente)" in msg
        assert "18.269 EUR (precedente)" in msg or "18,269 EUR (precedente)" in msg
        # Supplier purchases row
        assert "58.380 EUR (corrente)" in msg or "58,380 EUR (corrente)" in msg
        assert "56.148 EUR (precedente)" in msg or "56,148 EUR (precedente)" in msg

    def test_yoy_section_includes_explicit_nota_to_cite_both_values(self):
        """Claude must see an explicit instruction inside the data section
        telling it to always include both absolutes when citing %."""
        from modules.cashflow_monitor.digest_builder import _build_user_message
        msg = _build_user_message(_fixture_overview(), "monthly", 136, "it")
        assert "NOTA per la stesura" in msg or "INCLUDI SEMPRE" in msg
        assert "entrambi i valori assoluti" in msg or "entrambi" in msg.lower()


# ── D2: MoM trend fields are disambiguated from YoY ──────────────────────


class TestMoMLabelDisambiguation:
    def test_mom_trend_labels_clarify_period_precedente(self):
        """The kpis section labels for sales_trend_pct + expenses_trend_pct
        must explicitly say 'vs periodo precedente' so Claude doesn't
        confuse them with YoY."""
        from modules.cashflow_monitor.digest_builder import _build_user_message
        msg = _build_user_message(_fixture_overview(), "monthly", 136, "it")
        assert "Trend ricavi (vs periodo precedente)" in msg
        assert "Trend spese (vs periodo precedente)" in msg


# ── D3: System prompt mandates absolute values ───────────────────────────


class TestSystemPromptYoYRule:
    def test_system_prompt_has_yoy_transparency_rule(self):
        from modules.cashflow_monitor.digest_builder import _SYSTEM_PROMPT
        # The Wave Digest-Consistency rule is rule 1bis
        assert "Wave Digest-Consistency" in _SYSTEM_PROMPT or "1bis" in _SYSTEM_PROMPT
        # Mandates both absolute values
        assert "entrambi" in _SYSTEM_PROMPT.lower() or "both absolute" in _SYSTEM_PROMPT.lower()
        # Has concrete examples
        assert "FORBIDDEN" in _SYSTEM_PROMPT or "CORRECT" in _SYSTEM_PROMPT
        # The exact example with the prod numbers
        assert "78.884" in _SYSTEM_PROMPT and "81.275" in _SYSTEM_PROMPT

    def test_system_prompt_warns_about_mom_vs_yoy(self):
        from modules.cashflow_monitor.digest_builder import _SYSTEM_PROMPT
        # The rule warns NOT to derive YoY from MoM trend fields
        assert "Never derive a YoY % from the MoM" in _SYSTEM_PROMPT or "MoM" in _SYSTEM_PROMPT
        # Or it mentions "Trend ricavi" being vs prev-period
        assert (
            "Trend ricavi" in _SYSTEM_PROMPT
            or "previous-period" in _SYSTEM_PROMPT
            or "previous period" in _SYSTEM_PROMPT.lower()
        )


# ── Absence of bug-pattern strings (pre-fix anti-patterns) ──────────────


class TestPreFixPatternsAbsent:
    """The old YoY format ('YoY: 78,884 EUR (+3.0%)' without current
    value alongside) must NOT be in the new user_message."""

    def test_old_yoy_compact_label_is_gone(self):
        """The pre-fix compact format was:
            '- Fatturato YoY: 78,884 EUR (+3.0%)'
        This is ambiguous (78,884 is the YoY VALUE not the variation).
        The new format must use 'corrente vs precedente'."""
        from modules.cashflow_monitor.digest_builder import _build_user_message
        msg = _build_user_message(_fixture_overview(), "monthly", 136, "it")
        # The pre-fix line wasn't "Fatturato YoY: <val> EUR (+pct%)"
        # — search for that exact pattern and confirm it's NOT present
        import re
        # Old pattern: "- <label> YoY: <number> EUR (+pct%)"
        old_pattern = re.compile(
            r"-\s+\w+\s+YoY:\s+\d[\d.,]*\s+EUR\s+\([+-]?\d",
            re.UNICODE,
        )
        assert not old_pattern.search(msg), (
            "Wave Digest-Consistency regression — the old compact YoY "
            "format is back. Use the side-by-side 'corrente vs precedente' "
            "format instead."
        )


# ── End-to-end: locale variants ─────────────────────────────────────────


class TestLocaleHandling:
    @pytest.mark.parametrize("locale", ["it", "en"])
    def test_user_message_renders_in_locale_without_crash(self, locale):
        from modules.cashflow_monitor.digest_builder import _build_user_message
        msg = _build_user_message(_fixture_overview(), "monthly", 136, locale)
        # No raw {placeholder} leakage
        assert "{na}" not in msg
        assert "{total_sales}" not in msg
        # YoY section present
        assert "YEAR-OVER-YEAR" in msg
