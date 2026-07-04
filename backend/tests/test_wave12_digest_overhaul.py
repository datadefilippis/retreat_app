"""Wave 12 — digest overhaul.

The Wave 12 audit identified that the pre-Wave-12 digest was using ~30%
of the data already in build_overview and IGNORING every cross-module
data source (customers, products, orders) even when those modules were
active. The output was "4 numbers and no intelligence" — the audit's
verbatim quote of user feedback.

Wave 12 changes (all backed by tests here):

  12.A — Data layer
    A new build_digest_context() orchestrator wraps build_overview and
    adds per-module summaries (customers_summary, products_summary,
    commerce_summary) when those modules are entitled for the org.
    Plus health_score enrichment: trend + weakest/strongest dimension.

  12.B — Prompt rewrite
    _SYSTEM_PROMPT now defines 7 sections (TL;DR / Salute / Performance
    / Driver / Rischi / Azioni / Prospettive) with concrete per-section
    instructions, reasoning rules, output format spec, quality bar.

  12.B (unify) — Single AI call for text + PDF
    Pre-Wave-12 the PDF path made a SECOND Sonnet call via
    digest_report_builder._generate_ai_insights. Post-Wave-12 it reuses
    the markdown digest from generate_digest_markdown and parses sections
    via parse_digest_sections. Net: 1 Sonnet call per digest, not 2.

  12.D — PDF cross-module sections
    build_report_pdf renders Customer / Product / Commerce sections from
    overview when the respective summaries are .available. Rule-based,
    no extra AI.
"""
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio


# ════════════════════════════════════════════════════════════════════════════
# 12.A.1 — build_digest_context orchestrator
# ════════════════════════════════════════════════════════════════════════════


async def test_build_digest_context_returns_none_when_no_overview():
    """If build_overview fails / returns empty, the context is None
    (digest can't be built without at least cashflow data)."""
    from modules.cashflow_monitor import digest_context_builder

    with patch(
        "modules.cashflow_monitor.overview_builder.build_overview",
        new=AsyncMock(return_value=None),
    ):
        out = await digest_context_builder.build_digest_context(
            org_id="org_x", period="30d",
        )
    assert out is None


async def test_build_digest_context_adds_three_summary_sections():
    """Even when modules are not entitled, the three summary keys exist
    (with available=False) so downstream callers can branch uniformly."""
    from modules.cashflow_monitor import digest_context_builder

    fake_overview = {
        "kpis": {"total_sales": 50000},
        "health_score": {"breakdown": []},
        "period": {"start_date": "2026-04-15", "end_date": "2026-05-15"},
    }
    with patch(
        "modules.cashflow_monitor.overview_builder.build_overview",
        new=AsyncMock(return_value=fake_overview),
    ), patch(
        "services.module_access.get_module_entitlements",
        new=AsyncMock(return_value={"enabled": False, "limits": {}}),
    ):
        ctx = await digest_context_builder.build_digest_context(
            org_id="org_x", period="30d",
            start_date="2026-04-15", end_date="2026-05-15",
        )
    assert ctx is not None
    assert "customers_summary" in ctx
    assert "products_summary" in ctx
    assert "commerce_summary" in ctx
    assert ctx["customers_summary"]["available"] is False
    assert ctx["products_summary"]["available"] is False
    assert ctx["commerce_summary"]["available"] is False


# ════════════════════════════════════════════════════════════════════════════
# 12.A.5 — health score enrichment
# ════════════════════════════════════════════════════════════════════════════


def test_enrich_health_score_picks_weakest_and_strongest():
    from modules.cashflow_monitor.digest_context_builder import _enrich_health_score

    health = {
        "score": 60, "label": "Buono",
        "breakdown": [
            {"dimension": "Margine Netto", "dimension_key": "net_margin",
             "points": 5, "max": 25, "level": "critical"},
            {"dimension": "Resilienza Strutturale",
             "dimension_key": "structural_strength",
             "points": 18, "max": 20, "level": "ok"},
            {"dimension": "Ciclo di Cassa", "dimension_key": "cash_cycle",
             "points": None, "max": 25, "status": "not_computable"},
        ],
    }
    enriched = _enrich_health_score(health)
    assert enriched["weakest_dimension"]["dimension"] == "Margine Netto"
    assert enriched["strongest_dimension"]["dimension"] == "Resilienza Strutturale"
    # The not_computable dimension is excluded from min/max selection


def test_enrich_health_score_handles_empty_breakdown():
    """Gracefully no-ops when breakdown is empty."""
    from modules.cashflow_monitor.digest_context_builder import _enrich_health_score

    out = _enrich_health_score({"score": 0, "breakdown": []})
    # No crash. weakest/strongest just absent or None.
    assert out.get("weakest_dimension") is None
    assert out.get("strongest_dimension") is None


# ════════════════════════════════════════════════════════════════════════════
# 12.B — prompt structure
# ════════════════════════════════════════════════════════════════════════════


def test_system_prompt_declares_seven_sections():
    """The new prompt MUST instruct exactly the 7 section headings (one
    per section type from the audit). A future contributor who silently
    drops a section breaks this test."""
    from modules.cashflow_monitor.digest_builder import _SYSTEM_PROMPT

    expected_sections = [
        "## TL;DR",
        "## Salute Finanziaria",
        "## Performance del Periodo",
        "## Driver del Risultato",
        "## Rischi e Anomalie",
        "## Azioni Prioritarie",
        "## Prospettive",
    ]
    for header in expected_sections:
        assert header in _SYSTEM_PROMPT, f"missing section header: {header}"


def test_locale_table_has_seven_structure_instructions_for_all_languages():
    """Every locale must have exactly 7 structure_instructions entries
    to match the prompt's seven {si_*} placeholders."""
    from modules.cashflow_monitor.digest_builder import _L

    for locale in ("it", "en", "de", "fr"):
        si = _L[locale]["structure_instructions"]
        assert len(si) == 7, f"{locale}: expected 7 instructions, got {len(si)}"
        # Every instruction should be non-empty
        for i, item in enumerate(si):
            assert item and len(item) > 20, (
                f"{locale}: instruction #{i} is too short ({len(item) if item else 0} chars)"
            )


def test_user_message_includes_cross_module_blocks_when_available():
    """When the context contains customer/product/commerce summaries
    (available=True), the user message MUST surface them so the model
    can use them in the digest."""
    from modules.cashflow_monitor.digest_builder import _build_user_message

    overview = {
        "kpis": {"total_sales": 50000, "total_expenses": 30000,
                 "net_after_fixed": 5000, "operating_margin_pct": 10.0,
                 "burn_rate_total": 100, "giorni_autonomia": 60,
                 "supplier_purchases": 0, "fixed_costs_total": 0,
                 "dso": 30, "dpo": 30, "sales_trend_pct": 5.0,
                 "expenses_trend_pct": 2.0, "total_outflow_ratio": 60.0},
        "health_score": {"score": 65, "label": "Buono"},
        "alerts": {"open_count": 2, "by_severity": {"high": 1, "medium": 1}},
        "period": {"start_date": "2026-04-15", "end_date": "2026-05-15"},
        "customers_summary": {
            "available": True, "top_customers": [
                {"name": "Cliente Alpha", "total_revenue": 12000, "segment": "top"},
            ],
            "total_customers": 25, "new_customers_count": 3,
            "concentration_top5_pct": 60.0, "churn_risk_count": 4,
            "avg_clv": 480.0,
        },
        "products_summary": {
            "available": True, "top_sellers": [
                {"name": "Prod X", "revenue": 8000, "units": 200},
            ],
            "total_products": 50, "avg_margin_pct": 22.5,
            "low_margin_count": 5, "declining_count": 2, "dormant_count": 8,
        },
        "commerce_summary": {
            "available": True, "orders_count": 120, "orders_prev_count": 100,
            "aov": 85.0, "aov_prev": 80.0, "aov_trend_pct": 6.25,
            "cancellation_rate_pct": 4.2, "top_channels": [
                {"channel": "web", "revenue": 7000, "share_pct": 70.0, "count": 80},
            ],
            "draft_orders_count": 5,
        },
    }
    msg = _build_user_message(overview, "monthly", 30, locale="it")
    assert "CUSTOMER_SUMMARY" in msg
    assert "Cliente Alpha" in msg
    assert "PRODUCT_SUMMARY" in msg
    assert "Prod X" in msg
    assert "COMMERCE_SUMMARY" in msg
    assert "AOV" in msg


def test_user_message_omits_blocks_when_module_not_available():
    """When a module isn't entitled (available=False), its block must
    NOT appear in the user message — otherwise the prompt asks Sonnet
    to reason about empty data."""
    from modules.cashflow_monitor.digest_builder import _build_user_message

    overview = {
        "kpis": {"total_sales": 50000, "total_expenses": 30000,
                 "operating_margin_pct": 10, "net_after_fixed": 5000,
                 "burn_rate_total": 100, "giorni_autonomia": 60,
                 "supplier_purchases": 0, "fixed_costs_total": 0,
                 "dso": 30, "dpo": 30, "sales_trend_pct": 0,
                 "expenses_trend_pct": 0, "total_outflow_ratio": 60},
        "health_score": {"score": 65, "label": "Buono"},
        "alerts": {"open_count": 0, "by_severity": {}},
        "period": {"start_date": "2026-04-15", "end_date": "2026-05-15"},
        "customers_summary": {"available": False},
        "products_summary": {"available": False},
        "commerce_summary": {"available": False},
    }
    msg = _build_user_message(overview, "monthly", 30, locale="it")
    assert "CUSTOMER_SUMMARY" not in msg
    assert "PRODUCT_SUMMARY" not in msg
    assert "COMMERCE_SUMMARY" not in msg


# ════════════════════════════════════════════════════════════════════════════
# 12.B (unify) — markdown parser + single AI call
# ════════════════════════════════════════════════════════════════════════════


def test_parse_digest_sections_extracts_all_seven():
    from modules.cashflow_monitor.digest_builder import parse_digest_sections

    md = """## TL;DR
Quick verdict here.

## Salute Finanziaria
Health analysis with weakest dimension X.

## Performance del Periodo
Revenue and margin breakdown.

## Driver del Risultato
Main drivers identified.

## Rischi e Anomalie
- alert 1
- alert 2

## Azioni Prioritarie
1. First priority action
2. Second priority action
3. Third action

## Prospettive
Forward-looking projection.
"""
    out = parse_digest_sections(md)
    assert out["tldr"].startswith("Quick verdict")
    assert "weakest dimension" in out["health"]
    assert "Revenue and margin" in out["performance"]
    assert "Main drivers" in out["drivers"]
    assert "alert 1" in out["risks"]
    assert out["actions"] == [
        "First priority action",
        "Second priority action",
        "Third action",
    ]
    assert "Forward-looking" in out["outlook"]


def test_parse_digest_sections_handles_missing_sections():
    """Missing sections come back as empty strings — never None."""
    from modules.cashflow_monitor.digest_builder import parse_digest_sections

    out = parse_digest_sections("## TL;DR\nOnly this section.\n")
    assert out["tldr"] == "Only this section."
    # Missing sections are empty strings (not None)
    for k in ("health", "performance", "drivers", "risks", "outlook"):
        assert out[k] == ""
    assert out["actions"] == []


def test_parse_digest_sections_locale_aware_headers():
    """The parser must recognize section headers across locales the
    prompt may produce. Today the prompt headers are hardcoded IT
    ('TL;DR', 'Salute Finanziaria', etc.); the parser also tolerates
    EN/DE/FR variants in case the prompt is later localized."""
    from modules.cashflow_monitor.digest_builder import parse_digest_sections

    # English-style variant: 'Priority Actions' should still classify
    # as the actions section.
    md = """## TL;DR
Quick verdict.

## Priority Actions
1. Do thing one
2. Do thing two
"""
    out = parse_digest_sections(md)
    assert "Quick verdict" in out["tldr"]
    assert out["actions"] == ["Do thing one", "Do thing two"]


async def test_generate_digest_markdown_returns_dict_with_required_keys():
    """The unified AI-call helper returns a dict with content,
    model_version, usage, ok. Failure path returns ok=False."""
    from modules.cashflow_monitor import digest_builder

    # Simulate Claude unavailable
    with patch("services.claude_client.is_available", return_value=False):
        result = await digest_builder.generate_digest_markdown(
            overview={"kpis": {}}, digest_type="weekly",
            period_days=7, locale="it", org_id="org_x",
        )
    assert result["ok"] is False
    assert result["content"] is None
    assert result["model_version"] == "rule-based"


async def test_digest_report_builder_uses_unified_markdown_helper():
    """Wave 12.B unify: the PDF path must call generate_digest_markdown
    + parse_digest_sections instead of the old _generate_ai_insights
    (which was a second separate Sonnet call). Introspection-based."""
    import inspect as _ins
    from modules.cashflow_monitor import digest_report_builder

    src = _ins.getsource(digest_report_builder.build_digest_report)
    assert "generate_digest_markdown" in src
    assert "parse_digest_sections" in src
    # The old function must be GONE (was a second Sonnet call)
    assert not hasattr(digest_report_builder, "_generate_ai_insights"), (
        "Wave 12.B removed _generate_ai_insights — replaced by parsing the "
        "unified markdown digest"
    )


# ════════════════════════════════════════════════════════════════════════════
# 12.D — PDF cross-module sections
# ════════════════════════════════════════════════════════════════════════════


def test_pdf_renders_customer_section_when_summary_available():
    """The PDF builder must include the new Customers section logic
    keyed on customers_summary.available."""
    import inspect as _ins
    from modules.cashflow_monitor import digest_pdf

    src = _ins.getsource(digest_pdf.build_report_pdf)
    # The Wave 12.D section markers must be present
    assert 'customers_summary' in src
    assert 't["customers_title"]' in src
    assert 'cust_top_title' in src


def test_pdf_renders_product_section_when_summary_available():
    import inspect as _ins
    from modules.cashflow_monitor import digest_pdf

    src = _ins.getsource(digest_pdf.build_report_pdf)
    assert 'products_summary' in src
    assert 't["products_title"]' in src
    assert 'prod_top_title' in src


def test_pdf_renders_commerce_section_when_summary_available():
    import inspect as _ins
    from modules.cashflow_monitor import digest_pdf

    src = _ins.getsource(digest_pdf.build_report_pdf)
    assert 'commerce_summary' in src
    assert 't["commerce_title"]' in src
    assert 'comm_channels_title' in src


def test_pdf_locale_table_has_cross_module_keys_for_all_languages():
    """Every locale must define the cross-module label keys so the PDF
    renders correctly in IT/EN/DE/FR."""
    from modules.cashflow_monitor.digest_pdf import _T

    required_keys = [
        "customers_title", "cust_total", "cust_top_title",
        "products_title", "prod_total", "prod_top_title",
        "commerce_title", "comm_orders", "comm_channels_title",
    ]
    for loc in ("it", "en", "de", "fr"):
        for k in required_keys:
            assert k in _T[loc], f"locale {loc} missing key: {k}"


# ════════════════════════════════════════════════════════════════════════════
# Smoke — full digest pipeline (mocked Claude)
# ════════════════════════════════════════════════════════════════════════════


async def test_build_digest_end_to_end_smoke():
    """Smoke test: build_digest(format='text') with a mocked Claude
    returns a dict with the markdown content stored in 'content' and
    the cross-module summaries flowing through."""
    from modules.cashflow_monitor import digest_builder

    fake_markdown = """## TL;DR
Smoke test verdict.

## Salute Finanziaria
Score 65/100.

## Azioni Prioritarie
1. Action one
"""
    fake_overview = {
        "kpis": {"total_sales": 50000, "total_expenses": 30000,
                 "net_after_fixed": 5000, "operating_margin_pct": 10,
                 "burn_rate_total": 100, "giorni_autonomia": 60,
                 "supplier_purchases": 0, "fixed_costs_total": 0,
                 "dso": 30, "dpo": 30, "sales_trend_pct": 0,
                 "expenses_trend_pct": 0, "total_outflow_ratio": 60,
                 "break_even": 0, "cash_conversion_cycle": 0},
        "health_score": {"score": 65, "label": "Buono", "breakdown": []},
        "alerts": {"open_count": 0, "by_severity": {}},
        "alerts_summary": {"open_count": 0, "by_severity": {}},
        "period": {"start_date": "2026-04-15", "end_date": "2026-05-15"},
        "customers_summary": {"available": False},
        "products_summary": {"available": False},
        "commerce_summary": {"available": False},
    }
    fake_usage = {"input_tokens": 1000, "output_tokens": 400,
                  "cache_read_tokens": 0, "cache_creation_tokens": 0,
                  "latency_ms": 1500}

    with patch(
        "modules.cashflow_monitor.digest_context_builder.build_digest_context",
        new=AsyncMock(return_value=fake_overview),
    ), patch(
        "services.claude_client.is_available", return_value=True,
    ), patch(
        "services.claude_client.send_message_with_usage",
        new=AsyncMock(return_value=(fake_markdown, fake_usage)),
    ), patch(
        "services.claude_client.get_active_model",
        return_value="claude-sonnet-4-20250514",
    ), patch(
        "services.claude_client.calculate_cost_usd", return_value=0.018,
    ), patch(
        "services.claude_client.resolve_non_chat_model", return_value="",
    ), patch(
        "services.llm.budget_guard.check_budget_or_raise",
        new=AsyncMock(),
    ), patch(
        "repositories.usage_repository.record_usage",
        new=AsyncMock(),
    ):
        result = await digest_builder.build_digest(
            org_id="org_x", period_days=30, digest_type="monthly",
            locale="it", format="text",
        )

    assert result is not None
    assert "## TL;DR" in result["content"]
    assert "## Azioni Prioritarie" in result["content"]
    assert result["model_version"] == "claude-sonnet-4-20250514"
