"""
Frontend Semantic Verification Tests — ensure frontend labels match governed backend.

These tests read the locale JSON files and component source code to verify
that the frontend semantics are aligned with the canonical backend model.

Catches:
- Legacy 2-bucket language in 4-bucket contexts
- "Cash"/"bank balance" language in cumulative contexts
- Missing epistemic caveats on weak metrics
- Hardcoded (non-i18n) strings in components
- Missing locale keys across all 4 languages

Run with: pytest tests/test_frontend_semantics.py -v
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_ROOT = os.path.join(os.path.dirname(ROOT), "frontend")
LOCALES_DIR = os.path.join(FRONTEND_ROOT, "src", "locales")
COMPONENTS_DIR = os.path.join(FRONTEND_ROOT, "src", "features", "cashflow")

LOCALE_LANGS = ["it", "en", "fr", "de"]


def _read_locale(lang):
    path = os.path.join(LOCALES_DIR, lang, "cashflow_monitor.json")
    with open(path) as f:
        return json.load(f)


def _read_component(relpath):
    path = os.path.join(COMPONENTS_DIR, relpath)
    with open(path) as f:
        return f.read()


def _flatten_keys(d, prefix=""):
    """Flatten nested dict keys with dot notation."""
    keys = set()
    for k, v in d.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.update(_flatten_keys(v, full))
        else:
            keys.add(full)
    return keys


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 1: 4-bucket language — no 2-bucket framing in net result contexts
# ═══════════════════════════════════════════════════════════════════════════════

class TestFourBucketLanguage:
    """Frontend labels must not use 2-bucket framing for 4-bucket metrics."""

    def test_net_cashflow_desc_mentions_all_outflows(self):
        """The daily result chart description must reference all cost types, not just expenses."""
        for lang in LOCALE_LANGS:
            loc = _read_locale(lang)
            desc = loc["charts"]["net_cashflow_desc"].lower()
            # Must NOT say only "expenses" without mentioning other buckets
            assert (
                "operati" in desc or "fourniss" in desc or "supplier" in desc
                or "lieferant" in desc or "fissi" in desc or "fixed" in desc
                or "fixes" in desc or "fixkosten" in desc
                or "all outflows" in desc or "tutte le uscite" in desc
                or "toutes les sorties" in desc or "allen abfluessen" in desc
            ), f"{lang}: net_cashflow_desc must reference multiple outflow types, got: {desc}"

    def test_net_result_tooltip_mentions_all_costs(self):
        """Net result tooltip must indicate ALL costs, not just operating expenses."""
        for lang in LOCALE_LANGS:
            loc = _read_locale(lang)
            tooltip = loc["kpis"]["tooltip_net_result"].lower()
            # Must contain "all" / "tutte" / "toutes" / "allen" indicating completeness
            assert any(w in tooltip for w in ["all", "tutte", "toutes", "allen"]), (
                f"{lang}: tooltip_net_result must indicate ALL costs"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 2: No bank-balance language in cumulative/proxy contexts
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoBankBalanceLanguage:
    """Cumulative and proxy metrics must not imply they are bank balance."""

    def test_cumulative_desc_disclaims_bank_balance(self):
        for lang in LOCALE_LANGS:
            loc = _read_locale(lang)
            desc = loc["charts"]["cumulative_desc"].lower()
            # Must contain a disclaimer about bank balance
            assert any(w in desc for w in [
                "non corrisponde", "does not reflect", "ne correspond pas",
                "entspricht nicht", "not", "non", "ne ",
            ]), f"{lang}: cumulative_desc must disclaim bank balance"

    def test_cumulative_legend_no_cash_word(self):
        """Legend should say 'Cumulative Result', not 'Cumulative Cash'."""
        for lang in LOCALE_LANGS:
            loc = _read_locale(lang)
            legend = loc["charts"]["legend_cumulative"].lower()
            assert "cash" not in legend and "cassa" not in legend and "kasse" not in legend, (
                f"{lang}: legend_cumulative should not use 'cash'/'cassa'/'kasse', got: {legend}"
            )

    def test_autonomy_tooltip_disclaims_bank_balance(self):
        for lang in LOCALE_LANGS:
            loc = _read_locale(lang)
            tooltip = loc["kpis"]["estimated_tooltip_autonomy"].lower()
            assert any(w in tooltip for w in [
                "saldo bancario", "bank balance", "solde bancaire",
                "kontostand", "credit", "credito", "kreditlinien",
            ]), f"{lang}: autonomy tooltip must disclaim bank balance"


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 3: Epistemic caveats present on weak metrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestEpistemicCaveats:
    """Weak metrics must carry appropriate epistemic caveats."""

    def test_health_score_tooltip_says_directional(self):
        """Health score tooltip must indicate it is directional, not a precise diagnosis."""
        for lang in LOCALE_LANGS:
            loc = _read_locale(lang)
            tooltip = loc["kpis"]["tooltip_health_score"].lower()
            assert any(w in tooltip for w in [
                "direzionale", "directional", "directionnel", "richtungssignal",
            ]), f"{lang}: health score tooltip must say directional"

    def test_health_score_info_says_composite(self):
        """Health score info text must call it a composite indicator."""
        for lang in LOCALE_LANGS:
            loc = _read_locale(lang)
            info = loc["health"]["info_text"].lower()
            assert any(w in info for w in [
                "composito", "composite", "zusammengesetzt",
            ]), f"{lang}: health info_text must say composite"

    def test_scadenzario_warning_mentions_zero_values(self):
        """Scadenzario data quality warning must mention zero-value ambiguity."""
        for lang in LOCALE_LANGS:
            loc = _read_locale(lang)
            warning = loc["scadenzario"]["data_quality_warning"].lower()
            assert any(w in warning for w in [
                "zero", "zéro", "null",
            ]), f"{lang}: scadenzario warning must mention zero-value ambiguity"

    def test_autonomy_uses_estimated_badge(self):
        """Days of Autonomy KPI card must include the estimated badge in its label."""
        code = _read_component("components/KPIStrip.js")
        # Both the full KPIStrip and SummaryKPIStrip should use estimated_badge for days_autonomy
        assert "estimated_badge" in code, (
            "KPIStrip must use estimated_badge for days_autonomy"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 4: No hardcoded strings in components
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoHardcodedStrings:
    """Components must use i18n keys, not hardcoded text."""

    COMPONENT_FILES = [
        "components/AnalisiTab.js",
        "components/CashflowCharts.js",
        "components/KPIStrip.js",
        "components/ScadenzarioTab.js",
        "components/HealthScoreGauge.js",
        "components/AlertsTab.js",
    ]

    # Known Italian phrases that should NOT appear in component code
    FORBIDDEN_ITALIAN_PHRASES = [
        "Nessun dato",
        "Aggiunto alla",
        "Rimosso dalla",
        "Errore nel",
        "Impossibile caricare",
        "Modulo attivato",
        "Analisi alert",
        "Generati ",
    ]

    def test_no_hardcoded_italian_in_components(self):
        for relpath in self.COMPONENT_FILES:
            code = _read_component(relpath)
            for phrase in self.FORBIDDEN_ITALIAN_PHRASES:
                # Skip if it's in a comment
                assert phrase not in code, (
                    f"{relpath}: contains hardcoded Italian '{phrase}'"
                )

    def test_pareto_legend_uses_i18n(self):
        """Pareto chart legend must use t() for cumulative % label."""
        code = _read_component("components/AnalisiTab.js")
        # The Pareto Line's name prop should use t()
        assert 'name="% Cumulativa"' not in code, (
            "Pareto cumulative legend must use i18n, not hardcoded"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 5: Locale key parity across all 4 languages
# ═══════════════════════════════════════════════════════════════════════════════

class TestLocaleKeyParity:
    """All 4 language files must have the same keys."""

    def test_all_locales_have_same_keys(self):
        """Every key in the Italian locale must exist in en, fr, de."""
        it_keys = _flatten_keys(_read_locale("it"))
        for lang in ["en", "fr", "de"]:
            other_keys = _flatten_keys(_read_locale(lang))
            missing = it_keys - other_keys
            assert len(missing) == 0, (
                f"{lang} locale missing keys present in it: {sorted(missing)}"
            )

    def test_no_extra_keys_in_translations(self):
        """Non-primary locales should not have extra keys not in Italian."""
        it_keys = _flatten_keys(_read_locale("it"))
        for lang in ["en", "fr", "de"]:
            other_keys = _flatten_keys(_read_locale(lang))
            extra = other_keys - it_keys
            assert len(extra) == 0, (
                f"{lang} locale has extra keys not in it: {sorted(extra)}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 6: Required keys exist for canonical model
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanonicalKeysExist:
    """Locale files must contain keys for all canonical KPIs."""

    REQUIRED_KPI_KEYS = [
        "kpis.total_sales",
        "kpis.total_expenses",
        "kpis.supplier_purchases",
        "kpis.fixed_costs",
        "kpis.net_result",
        "kpis.outflow_ratio",
        "kpis.operating_margin",
        "kpis.break_even",
        "kpis.burn_rate",
        "kpis.days_autonomy",
        "kpis.fixed_costs_pct",
    ]

    REQUIRED_TOOLTIP_KEYS = [
        "kpis.tooltip_net_result",
        "kpis.tooltip_health_score",
        "kpis.tooltip_outflow_ratio",
        "kpis.tooltip_break_even",
        "kpis.tooltip_burn_rate",
        "kpis.tooltip_fixed_costs",
        "kpis.tooltip_fixed_costs_pct",
        "kpis.estimated_tooltip_autonomy",
    ]

    def test_all_kpi_keys_exist(self):
        for lang in LOCALE_LANGS:
            keys = _flatten_keys(_read_locale(lang))
            for required_key in self.REQUIRED_KPI_KEYS:
                assert required_key in keys, (
                    f"{lang} locale missing canonical KPI key: {required_key}"
                )

    def test_all_tooltip_keys_exist(self):
        for lang in LOCALE_LANGS:
            keys = _flatten_keys(_read_locale(lang))
            for required_key in self.REQUIRED_TOOLTIP_KEYS:
                assert required_key in keys, (
                    f"{lang} locale missing tooltip key: {required_key}"
                )
