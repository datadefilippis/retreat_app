"""
Governance Rule Enforcement Tests — prevent architectural regression.

These tests enforce the rules in GOVERNANCE.md.
They verify structural properties of the codebase that must remain true
as the platform evolves.

Run with: pytest tests/test_governance_rules.py -v
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _read(relpath):
    with open(os.path.join(ROOT, relpath)) as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 1: No legacy fields in canonical paths
# ═══════════════════════════════════════════════════════════════════════════════

class TestNoLegacyContamination:
    """Governance Rule: Legacy fields must never appear in canonical paths."""

    LEGACY_FIELDS = ["net_cashflow", "burn_rate", "expense_ratio", "combined_expenses"]
    CANONICAL_CONSUMERS = [
        "modules/cashflow_monitor/cashflow_summary.py",
        "services/business_summary.py",
    ]

    def test_canonical_consumers_dont_use_legacy_as_primary(self):
        for path in self.CANONICAL_CONSUMERS:
            code = _read(path)
            for field in self.LEGACY_FIELDS:
                # Check if the field is used as a primary output (not just reading _legacy)
                if f'"{field}"' in code:
                    # It's OK if it's reading from _legacy or documenting it
                    context = code[max(0, code.index(f'"{field}"') - 100):code.index(f'"{field}"') + 100]
                    assert "_legacy" in context or "legacy" in context.lower() or "deprecated" in context.lower(), (
                        f"{path}: uses legacy field '{field}' outside of _legacy context"
                    )

    def test_ai_tools_dont_return_legacy_net_cashflow(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        # Find all return statements in tool handlers
        # net_cashflow should NOT appear as a primary returned field
        # (it can appear in variable names for computation)
        tool_returns = re.findall(r'"net_cashflow":\s*\w+', code)
        assert len(tool_returns) == 0, (
            f"AI tools return legacy net_cashflow field: {tool_returns}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 2: All AI tools must have temporal metadata
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemporalMetadataGovernance:
    """Governance Rule: All AI tool responses must declare temporal scope."""

    AI_TOOL_FILES = [
        "modules/cashflow_monitor/ai_tools.py",
        "modules/customer_insights/ai_tools.py",
    ]

    def test_all_tool_files_have_temporal_metadata(self):
        for path in self.AI_TOOL_FILES:
            code = _read(path)
            if "TOOL_DEFINITIONS" in code:
                # Cashflow tools delegate metadata to their summary services
                # (cashflow_summary.py, business_summary.py), so it's OK if
                # the tool file itself doesn't contain temporal_scope/epistemic.
                if "cashflow_monitor" in path:
                    # Verify metadata exists in the summary service instead
                    summary_code = _read("modules/cashflow_monitor/cashflow_summary.py")
                    assert "temporal" in summary_code or "epistemic" in summary_code, (
                        "cashflow_summary.py must contain temporal/epistemic metadata"
                    )
                else:
                    assert "temporal_scope" in code or "epistemic" in code, (
                        f"{path}: must declare temporal metadata in responses"
                    )

    def test_snapshot_tools_declare_unsafe(self):
        for path in [
            "modules/customer_insights/ai_tools.py",
        ]:
            code = _read(path)
            if '"snapshot"' in code:
                assert "temporal_alignment_safe" in code, (
                    f"{path}: snapshot tools must declare temporal_alignment_safe"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 3: Epistemic metadata required for financial tools
# ═══════════════════════════════════════════════════════════════════════════════

class TestEpistemicMetadataGovernance:
    """Governance Rule: Financial AI tools must include epistemic metadata."""

    def test_cashflow_summary_has_epistemic(self):
        code = _read("modules/cashflow_monitor/cashflow_summary.py")
        assert '"epistemic"' in code or "'epistemic'" in code

    def test_customer_tools_have_epistemic(self):
        code = _read("modules/customer_insights/ai_tools.py")
        assert '"epistemic"' in code

    # Wave 7A (2026-05): commerce_signals removed, its governance check
    # has been deleted along with the module.

    def test_business_summary_has_reasoning_contract(self):
        code = _read("services/business_summary.py")
        assert '"reasoning_contract"' in code or "'reasoning_contract'" in code


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 4: Tool ordering — summary tools must be first
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolOrderingGovernance:
    """Governance Rule: Summary/holistic tools must be first in TOOL_DEFINITIONS."""

    def test_business_summary_before_cashflow_summary(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        pos_business = code.index("query_business_summary")
        pos_cashflow = code.index("query_cashflow_summary")
        assert pos_business < pos_cashflow, (
            "query_business_summary must come before query_cashflow_summary"
        )

    def test_cashflow_summary_before_drill_down(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        pos_summary = code.index("query_cashflow_summary")
        pos_revenue = code.index("query_revenue")
        assert pos_summary < pos_revenue, (
            "query_cashflow_summary must come before drill-down tools"
        )

    def test_customer_summary_before_snapshot_tools(self):
        code = _read("modules/customer_insights/ai_tools.py")
        pos_summary = code.index("query_customer_summary")
        pos_top = code.index("query_top_customers")
        assert pos_summary < pos_top, (
            "query_customer_summary must come before snapshot tools"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 5: 4-bucket model consistency
# ═══════════════════════════════════════════════════════════════════════════════

class TestFourBucketConsistency:
    """Governance Rule: The 4-bucket financial model must be consistent."""

    def test_overview_daily_series_is_4_bucket(self):
        code = _read("modules/cashflow_monitor/overview_builder.py")
        assert "s - e - p - daily_fixed" in code

    def test_ai_tool_cashflow_is_4_bucket(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        # Find the execute handler for query_cashflow (not query_cashflow_summary)
        handler_idx = code.index('tool_name == "query_cashflow"')
        handler_section = code[handler_idx:handler_idx + 2000]
        assert "net_after_fixed" in handler_section
        assert "total_outflows" in handler_section

    def test_no_2_bucket_cumulative_in_ai_tools(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        assert "aggregate_cumulative_cashflow" not in code


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 6: GOVERNANCE.md exists and is comprehensive
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernanceDocExists:
    """Governance Rule: GOVERNANCE.md must exist and cover key topics."""

    def test_governance_md_exists(self):
        path = os.path.join(ROOT, "GOVERNANCE.md")
        assert os.path.exists(path), "GOVERNANCE.md must exist at backend root"

    def test_governance_covers_key_topics(self):
        code = _read("GOVERNANCE.md")
        topics = [
            "Adding New KPIs",
            "Adding New AI Tools",
            "Adding New Module Summaries",
            "Cross-Module Comparisons",
            "Temporal Metadata",
            "Epistemic Metadata",
            "Deprecating Legacy Paths",
            "Chat Prompt Governance",
        ]
        for topic in topics:
            assert topic in code, f"GOVERNANCE.md missing topic: {topic}"


# ═══════════════════════════════════════════════════════════════════════════════
# RULE 7: Syntax validation for all governed files
# ═══════════════════════════════════════════════════════════════════════════════

class TestAllGovernedFilesSyntaxValid:
    """Governance Rule: All governed files must be syntactically valid."""

    GOVERNED_FILES = [
        "modules/cashflow_monitor/overview_builder.py",
        "modules/cashflow_monitor/cashflow_summary.py",
        "modules/cashflow_monitor/ai_tools.py",
        "modules/cashflow_monitor/health_score.py",
        "modules/cashflow_monitor/status_builder.py",
        "modules/cashflow_monitor/health_explanation.py",
        "modules/customer_insights/ai_tools.py",
        "services/business_summary.py",
        "services/chat_service.py",
        "services/ai_tool_registry.py",
        "repositories/analytics_repository.py",
    ]

    def test_all_governed_files_parse(self):
        import ast
        for relpath in self.GOVERNED_FILES:
            path = os.path.join(ROOT, relpath)
            if os.path.exists(path):
                with open(path) as f:
                    try:
                        ast.parse(f.read())
                    except SyntaxError as e:
                        raise AssertionError(
                            f"Syntax error in {relpath} at line {e.lineno}: {e.msg}"
                        )
