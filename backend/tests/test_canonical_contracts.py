"""
Canonical Contract Tests — structural verification of the AI-governed platform.

These tests verify the CONTRACTS, not the runtime behavior.
They ensure that:
1. Canonical summaries expose the right fields
2. Legacy fields are isolated
3. Temporal/epistemic metadata is present
4. Daily series uses 4-bucket model
5. Tool registry is consistent
6. Evidence hierarchy is complete

Run with: pytest tests/test_canonical_contracts.py -v
"""
import ast
import json
import os
import re

# ── Helpers ──────────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _read(relpath):
    with open(os.path.join(ROOT, relpath)) as f:
        return f.read()

def _parse(relpath):
    return ast.parse(_read(relpath))


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CANONICAL CASHFLOW ENGINE CONTRACTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCashflowDailySeriesContract:
    """Verify the daily series uses the canonical 4-bucket net formula."""

    def test_daily_net_is_4_bucket(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        # The daily net MUST subtract purchases and daily_fixed
        assert "net = round(s - e - p - daily_fixed, 2)" in code, (
            "daily_series.net must use 4-bucket formula: s - e - p - daily_fixed"
        )

    def test_cumulative_uses_4_bucket_net(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        # Cumulative must be built from the 4-bucket net
        assert "running = round(running + net, 2)" in code

    def test_no_2_bucket_daily_net(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        # There must NOT be a 2-bucket daily net (net = s - e) in the daily series loop
        daily_section = code[code.index("Canonical daily series"):]
        daily_section = daily_section[:daily_section.index("Giorni")]
        assert "net = round(s - e, 2)" not in daily_section, (
            "Found legacy 2-bucket daily net in daily series section"
        )


class TestCashflowLegacyIsolation:
    """Verify legacy fields are isolated from canonical kpis."""

    def test_legacy_block_exists(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        assert '"_legacy"' in code, "Legacy fields must be under _legacy key"

    def test_canonical_kpis_no_net_cashflow(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        kpis_block = code.split('"kpis":')[1].split('"_legacy":')[0]
        assert '"net_cashflow"' not in kpis_block, (
            "net_cashflow (2-bucket) must NOT be in canonical kpis"
        )

    def test_canonical_kpis_no_legacy_burn_rate(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        kpis_block = code.split('"kpis":')[1].split('"_legacy":')[0]
        # burn_rate_total is canonical; plain "burn_rate" is legacy
        lines = [l.strip() for l in kpis_block.split('\n') if '"burn_rate"' in l and 'burn_rate_total' not in l]
        assert len(lines) == 0, (
            "Legacy burn_rate (1-bucket) must NOT be in canonical kpis"
        )

    def test_canonical_kpis_no_expense_ratio(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        kpis_block = code.split('"kpis":')[1].split('"_legacy":')[0]
        assert '"expense_ratio"' not in kpis_block, (
            "expense_ratio (1-bucket) must NOT be in canonical kpis"
        )

    def test_legacy_contains_deprecated_fields(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        legacy_block = code.split('"_legacy":')[1].split('},')[0]
        assert '"net_cashflow"' in legacy_block
        assert '"burn_rate"' in legacy_block
        assert '"expense_ratio"' in legacy_block


class TestCashflowCanonicalFields:
    """Verify all canonical KPI fields are present."""

    REQUIRED_CANONICAL_FIELDS = [
        "total_sales", "total_expenses", "supplier_purchases",
        "fixed_costs_total", "total_outflows", "net_after_fixed",
        "total_outflow_ratio", "operating_margin", "operating_margin_pct",
        "break_even", "burn_rate_total", "giorni_autonomia", "fixed_costs_pct",
        "variable_outflows", "net_before_fixed", "purchase_ratio",
        "avg_daily_sales", "avg_daily_expenses",
        "sales_trend_pct", "expenses_trend_pct", "period_days",
        "dso", "dpo", "cash_conversion_cycle",
        "open_receivables", "open_payables",
    ]

    def test_all_canonical_fields_in_kpis(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        kpis_block = code.split('"kpis":')[1].split('"_legacy":')[0]
        for field in self.REQUIRED_CANONICAL_FIELDS:
            assert f'"{field}"' in kpis_block, (
                f"Canonical field '{field}' missing from kpis dict"
            )


class TestHealthScoreContract:
    """Verify health score handles break-even edge cases correctly."""

    def test_distinguishes_no_fixed_costs_from_deficit(self):
        code = _read("modules/cashflow_monitor/health_score.py")
        assert "fixed_costs > 0" in code, (
            "Health score must check fixed_costs to distinguish "
            "structural deficit from no-fixed-costs"
        )

    def test_v3_dimensions_present(self):
        code = _read("modules/cashflow_monitor/health_score.py")
        for dim in ["net_margin", "revenue_dynamics", "structural_strength", "cash_cycle", "operational_risk"]:
            assert dim in code, f"Health score v3 must include dimension: {dim}"

    def test_receives_fixed_costs_total(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        # The health_kpis dict must include fixed_costs_total
        assert "fixed_costs_total" in code
        assert "health_kpis" in code


# ═══════════════════════════════════════════════════════════════════════════════
# 2. AI SUMMARY CONTRACT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCashflowAISummaryContract:
    """Verify the cashflow AI summary exposes required structures."""

    def test_summary_exists(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        assert "async def build_ai_summary" in code

    def test_epistemic_metadata_defined(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        required_groups = [
            "core_pnl", "observed_totals", "fixed_costs", "break_even",
            "autonomy", "scadenzario", "yoy", "health_score", "alerts",
            "status_banner",
        ]
        for group in required_groups:
            assert f'"{group}"' in code, (
                f"Epistemic group '{group}' missing from _EPISTEMIC"
            )

    def test_scadenzario_quality_assessment_exists(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        assert "_assess_scadenzario_quality" in code

    def test_summary_output_sections(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        required_sections = [
            '"pnl"', '"trends"', '"yoy"', '"scadenzario"',
            '"health_score"', '"status"', '"alerts"',
        ]
        for section in required_sections:
            assert section in code, f"Summary missing section: {section}"

    def test_analytical_blocks_present(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        for block in ["drivers", "period_comparison", "risk_focus", "action_focus"]:
            assert f'"{block}"' in code, f"Analytical block '{block}' missing from summary"

    def test_drivers_block_structure(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        for field in ["dominant_cost_bucket", "diagnosis", "diagnosis_text", "cost_ranking"]:
            assert f'"{field}"' in code, f"Drivers block missing field: {field}"

    def test_period_comparison_block_structure(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        for field in ["sales_change_pct", "expenses_change_pct", "biggest_change", "net_direction"]:
            assert f'"{field}"' in code, f"Period comparison missing field: {field}"

    def test_risk_focus_block_structure(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        assert "def _build_risk_focus" in code

    def test_action_focus_block_structure(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        assert "def _build_action_focus" in code
        assert '"data_grounded": True' in code


class TestCustomDateSupport:
    """Verify summary tools support custom date ranges."""

    def test_cashflow_summary_tool_accepts_start_date(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        # Find the query_cashflow_summary tool definition — use 1500 chars
        # to cover the full description + input_schema properties
        idx = code.index('"query_cashflow_summary"')
        block = code[idx:idx+1500]
        assert '"start_date"' in block, "query_cashflow_summary must accept start_date"
        assert '"end_date"' in block, "query_cashflow_summary must accept end_date"

    def test_business_summary_tool_accepts_start_date(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        idx = code.index('"query_business_summary"')
        block = code[idx:idx+1500]
        assert '"start_date"' in block, "query_business_summary must accept start_date"
        assert '"end_date"' in block, "query_business_summary must accept end_date"

    def test_dispatch_passes_dates_for_cashflow_summary(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        idx = code.index('tool_name == "query_cashflow_summary"')
        block = code[idx:idx+300]
        assert "start_date" in block, "Dispatch must pass start_date for cashflow summary"
        assert "end_date" in block, "Dispatch must pass end_date for cashflow summary"

    def test_dispatch_passes_dates_for_business_summary(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        idx = code.index('tool_name == "query_business_summary"')
        block = code[idx:idx+300]
        assert "start_date" in block, "Dispatch must pass start_date for business summary"
        assert "end_date" in block, "Dispatch must pass end_date for business summary"

    def test_custom_period_triggers_on_both_dates(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        # When both dates provided, period should become "custom"
        assert '"custom"' in code, "Must set period to 'custom' when dates are provided"


class TestBlockScopeMetadata:
    """Verify block-level temporal scope metadata is present."""

    def test_block_scopes_exists_in_summary(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        assert '"block_scopes"' in code, "Summary must include block_scopes metadata"

    def test_period_filtered_blocks_declared(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        for block in ["pnl", "trends", "yoy", "health_score", "drivers", "period_comparison"]:
            assert f'"{block}"' in code, f"Block '{block}' not in block_scopes"

    def test_current_state_blocks_declared(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        assert '"current_state"' in code, "Must declare current_state scope for scadenzario/alerts"

    def test_scadenzario_marked_current_state(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        # Find block_scopes section and verify scadenzario is current_state
        idx = code.index('"block_scopes"')
        scopes_block = code[idx:idx+2000]
        scad_idx = scopes_block.index('"scadenzario"')
        scad_line = scopes_block[scad_idx:scad_idx+200]
        assert "current_state" in scad_line, "Scadenzario must be marked as current_state"

    def test_alerts_marked_current_state(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        idx = code.index('"block_scopes"')
        scopes_block = code[idx:idx+2000]
        alerts_idx = scopes_block.index('"alerts"')
        alerts_line = scopes_block[alerts_idx:alerts_idx+200]
        assert "current_state" in alerts_line, "Alerts must be marked as current_state"

    def test_prompt_references_block_scopes(self):
        code = _read("services/chat_service.py")
        assert "block_scope" in code.lower() or "period_filtered" in code


class TestUnifiedBusinessSummaryContract:
    """Verify the unified business summary exposes required structures."""

    def test_summary_exists(self):
        code = _read("services/business_summary.py")
        assert "async def build_unified_summary" in code

    def test_reasoning_contract_defined(self):
        code = _read("services/business_summary.py")
        assert "_REASONING_CONTRACT" in code
        assert '"evidence_hierarchy"' in code
        assert '"safe_comparisons"' in code
        assert '"unsafe_comparisons"' in code
        assert '"claim_rules"' in code

    def test_evidence_hierarchy_has_expected_ranks(self):
        # Regression guard — alerts on accidental rank deletion / mass-add.
        # Wave 7A (2026-05): commerce_signals removed -> hierarchy is now 6 ranks.
        # Bump this number consciously when extending the hierarchy.
        code = _read("services/business_summary.py")
        rank_count = code.count('"rank":')
        assert rank_count == 6, f"Evidence hierarchy should have 6 ranks, found {rank_count}"

    def test_cross_module_metadata_present(self):
        code = _read("services/business_summary.py")
        assert "revenue_alignment_pct" in code
        assert "temporal_alignment" in code
        assert "customer_id_coverage_pct" in code

    def test_commerce_signals_rank_removed(self):
        """Wave 7A regression guard: signals.snapshot must NOT appear in
        the reasoning_contract any more — commerce_signals was retired."""
        code = _read("services/business_summary.py")
        assert "signals.snapshot" not in code, (
            "commerce_signals reference in reasoning_contract — should be removed (Wave 7A)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. AI TOOL REGISTRY CONTRACT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolRegistryContract:
    """Verify AI tool definitions and routing are consistent."""

    def _count_tools(self, relpath):
        code = _read(relpath)
        import re
        return len(re.findall(r'"name":\s*"query_|"name":\s*"get_', code))

    # Regression guards — alert on accidental tool deletion / mass-add.
    # Update consciously when adding/removing tools in a module.

    def test_cashflow_tool_count(self):
        # Wave 7B.1: 6 commerce ops moved out (22 -> 16).
        # Wave 7D: +1 query_late_payers = 17.
        # Wave 14.HOTFIX4: +2 (query_fixed_costs_detail F2,
        #                  query_health_score_breakdown F3) = 19.
        count = self._count_tools("modules/cashflow_monitor/ai_tools.py")
        assert count == 19, f"Cashflow should have 19 tools, found {count}"

    def test_commerce_tool_count(self):
        # Wave 7B.1: 6 tools moved from cashflow_monitor.
        # Wave 7B.2: +4 analytics = 10.
        # Wave 7B.3: +6 = 16.
        # Wave 7C.1: +5 agenda = 21.
        # Wave 7C.2: +5 rentals = 26.
        # Wave 7C.3: +1 events_calendar = 27.
        # Wave 7D: +2 (coupon_usage, course_engagement) = 29.
        count = self._count_tools("modules/commerce/ai_tools.py")
        assert count == 29, f"Commerce should have 29 tools, found {count}"

    def test_customer_tool_count(self):
        # Wave 7D: +1 customer_acquisition_trend = 8.
        count = self._count_tools("modules/customer_insights/ai_tools.py")
        assert count == 8, f"Customers should have 8 tools, found {count}"

    def test_total_tool_count(self):
        # Wave 7D: cashflow 17 + commerce 29 + customers 8 = 54.
        # Wave 14.HOTFIX4: cashflow 17 -> 19 (+2). Total = 56.
        total = (
            self._count_tools("modules/cashflow_monitor/ai_tools.py")
            + self._count_tools("modules/commerce/ai_tools.py")
            + self._count_tools("modules/customer_insights/ai_tools.py")
        )
        assert total == 56, f"Total tools should be 56, found {total}"

    def test_business_summary_is_first_tool(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        defs_start = code.index("TOOL_DEFINITIONS")
        first_name = code[defs_start:].split('"name":')[1].split('"')[1]
        assert first_name == "query_business_summary", (
            f"First tool must be query_business_summary, found {first_name}"
        )

    def test_cashflow_summary_is_second_tool(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        defs_start = code.index("TOOL_DEFINITIONS")
        second_name = code[defs_start:].split('"name":')[2].split('"')[1]
        assert second_name == "query_cashflow_summary", (
            f"Second tool must be query_cashflow_summary, found {second_name}"
        )

    def test_customer_summary_is_first_customer_tool(self):
        code = _read("modules/customer_insights/ai_tools.py")
        defs_start = code.index("TOOL_DEFINITIONS")
        first_name = code[defs_start:].split('"name":')[1].split('"')[1]
        assert first_name == "query_customer_summary", (
            f"First customer tool must be query_customer_summary, found {first_name}"
        )

    def test_no_legacy_cumulative_in_cashflow_tools(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        assert "aggregate_cumulative_cashflow" not in code, (
            "Legacy 2-bucket aggregate_cumulative_cashflow must not be used in AI tools"
        )

    def test_all_snapshot_tools_have_epistemic(self):
        """Snapshot-based tools must declare epistemic metadata."""
        for path in [
            "modules/customer_insights/ai_tools.py",
        ]:
            code = _read(path)
            # Count tool handlers (elif blocks with "return {")
            if "temporal_scope" not in code:
                raise AssertionError(
                    f"{path}: snapshot tools must declare temporal_scope in epistemic"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CHAT PROMPT CONTRACT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestChatPromptContract:
    """Verify the chat system prompt contains governance rules."""

    def test_business_summary_first_strategy(self):
        code = _read("services/chat_service.py")
        assert "query_business_summary" in code

    def test_evidence_hierarchy_instructions(self):
        # Wave 7A: rank 5 was commerce_signals (removed). The prompt now
        # dynamically includes ranks 1-4 always, rank 5+ conditional on
        # active modules. We just verify rank 1 (the floor of the
        # discipline) is always present.
        code = _read("services/chat_service.py")
        assert "Rank 1" in code

    def test_claim_discipline(self):
        code = _read("services/chat_service.py")
        assert "factual" in code.lower()
        assert "conditional" in code.lower()
        assert "directional" in code.lower()
        assert "contextual" in code.lower()

    def test_analyst_grade_reasoning_instructions(self):
        code = _read("services/chat_service.py")
        assert "drivers" in code
        assert "period_comparison" in code
        assert "risk_focus" in code
        assert "action_focus" in code
        assert "financial analyst" in code.lower()

    def test_causation_warning(self):
        code = _read("services/chat_service.py")
        assert "causation" in code.lower()

    def test_4_bucket_model_described(self):
        code = _read("services/chat_service.py")
        assert "Bucket A" in code
        assert "Bucket B" in code
        assert "Bucket C" in code
        assert "net_after_fixed" in code


# ═══════════════════════════════════════════════════════════════════════════════
# 5. TEMPORAL GOVERNANCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemporalGovernance:
    """Verify temporal metadata is present where required."""

    def test_customer_period_tool_declares_temporal_scope(self):
        code = _read("modules/customer_insights/ai_tools.py")
        assert '"temporal_scope": "period"' in code

    def test_customer_snapshot_tools_declare_snapshot(self):
        code = _read("modules/customer_insights/ai_tools.py")
        assert '"temporal_scope": "snapshot"' in code

    # Wave 7A (2026-05): commerce_signals removed, tests for its
    # ai_tools.py shape have been deleted. The canonical-snapshot
    # tests now apply only to customer_insights below.

    def test_customer_period_tool_declares_alignment_safe(self):
        code = _read("modules/customer_insights/ai_tools.py")
        assert '"temporal_alignment_safe": True' in code


# ═══════════════════════════════════════════════════════════════════════════════
# 6. FRONTEND LEGACY CONTAMINATION PREVENTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestFrontendLegacyPrevention:
    """Verify frontend does not reference legacy fields."""

    def test_kpistrip_no_expense_ratio(self):
        code = _read("../frontend/src/features/cashflow/components/KPIStrip.js")
        assert "expense_ratio" not in code, (
            "KPIStrip must not reference legacy expense_ratio"
        )
