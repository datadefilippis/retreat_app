"""
AI Eval Harness — scenario-based verification of AI reasoning behavior.

These tests do NOT call the LLM.  They verify that the TOOL INFRASTRUCTURE
and PROMPT GOVERNANCE produce the right inputs for correct reasoning.

Each scenario defines:
- A representative user question
- The preferred tool path (which tool should be called first)
- The evidence priority (what data should anchor the answer)
- Forbidden shortcuts (what the AI must NOT do)
- Required caveats (what qualifications must be present)

Run with: pytest tests/test_ai_eval_harness.py -v
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _read(relpath):
    with open(os.path.join(ROOT, relpath)) as f:
        return f.read()


# ── Scenario definitions ─────────────────────────────────────────────────────

EVAL_SCENARIOS = [
    {
        "id": "Q1_am_i_profitable",
        "question": "Am I making or losing money this period?",
        "category": "cashflow_holistic",
        "preferred_tool": "query_cashflow_summary",
        "also_acceptable": ["query_business_summary"],
        "primary_evidence": "cashflow.pnl.net_after_fixed",
        "evidence_rank": 1,
        "forbidden_shortcuts": [
            "Using net_cashflow (2-bucket legacy) instead of net_after_fixed",
            "Using query_cashflow with only sales and expenses",
        ],
        "required_caveats": [],  # This is a factual question on strong data
        "expected_answer_shape": "factual_with_number",
    },
    {
        "id": "Q2_what_drives_negative",
        "question": "What is driving my negative result?",
        "category": "cashflow_diagnostic",
        "preferred_tool": "query_cashflow_summary",
        "also_acceptable": ["query_business_summary"],
        "primary_evidence": "cashflow.pnl (all 4 buckets compared)",
        "evidence_rank": 1,
        "forbidden_shortcuts": [
            "Blaming only expenses without checking purchases and fixed costs",
            "Using 2-bucket net to diagnose",
        ],
        "required_caveats": [
            "Fixed costs are approximate (prorated)",
        ],
        "expected_answer_shape": "diagnostic_with_bucket_attribution",
    },
    {
        "id": "Q3_collections_problem",
        "question": "Do I have a collections problem?",
        "category": "scadenzario",
        "preferred_tool": "query_cashflow_summary",
        "also_acceptable": ["query_receivables_payables"],
        "primary_evidence": "cashflow.scadenzario (DSO, open_receivables, aging)",
        "evidence_rank": 3,
        "forbidden_shortcuts": [
            "Interpreting DSO=0 as 'excellent collection' when data may be missing",
            "Stating 'no unpaid invoices' when open_receivables=0 could mean no data",
        ],
        "required_caveats": [
            "Must check scadenzario data_quality",
            "Must warn if no_payment_data",
        ],
        "expected_answer_shape": "conditional_on_data_quality",
    },
    {
        "id": "Q4_health_score_low",
        "question": "Why is my health score low?",
        "category": "health_diagnostic",
        "preferred_tool": "query_cashflow_summary",
        "also_acceptable": ["query_business_summary"],
        "primary_evidence": "cashflow.health_score.breakdown (8 dimensions)",
        "evidence_rank": 4,
        "forbidden_shortcuts": [
            "Citing health score as precise diagnostic",
            "Treating it as a single authoritative number",
        ],
        "required_caveats": [
            "Health score is a composite of mixed-quality inputs",
            "Must decompose into dimension breakdown",
        ],
        "expected_answer_shape": "directional_with_dimension_decomposition",
    },
    {
        "id": "Q5_which_customers_drove_revenue",
        "question": "Which customers drove revenue this month?",
        "category": "cross_module",
        "preferred_tool": "query_business_summary",
        "also_acceptable": ["query_customer_summary"],
        "primary_evidence": "customers.period.top_customers",
        "evidence_rank": 2,
        "forbidden_shortcuts": [
            "Using snapshot customer tools (query_top_customers) which are all-time",
            "Comparing all-time customer revenue with period cashflow revenue",
        ],
        "required_caveats": [
            "Must check customer_id_coverage_pct",
            "Must note if coverage < 80%",
        ],
        "expected_answer_shape": "factual_if_data_quality_sufficient",
    },
    {
        "id": "Q6_concentration_linked_to_drop",
        "question": "Is my revenue drop linked to customer concentration?",
        "category": "cross_module_causal",
        "preferred_tool": "query_business_summary",
        "also_acceptable": [],
        "primary_evidence": "cashflow.pnl.sales_trend_pct + customers.period.concentration",
        "evidence_rank": "1+2 combined",
        "forbidden_shortcuts": [
            "Claiming causation without evidence",
            "Using snapshot concentration data for period comparison",
        ],
        "required_caveats": [
            "Correlation is not causation",
            "Must use period-aligned customer data",
        ],
        "expected_answer_shape": "speculative_with_correlation_qualifier",
    },
    {
        "id": "Q7_signals_vs_cashflow",
        "question": "Commerce signals look strong — why is net result still weak?",
        "category": "cross_module_reconciliation",
        "preferred_tool": "query_business_summary",
        "also_acceptable": [],
        "primary_evidence": "cashflow.pnl (factual) vs signals (contextual only)",
        "evidence_rank": "1 vs 5",
        "forbidden_shortcuts": [
            "Comparing signal values with cashflow period values",
            "Treating signal 'value at risk' as cash impact",
        ],
        "required_caveats": [
            "Signals are snapshot/all-time, NOT period-aligned",
            "Signal values represent lifetime potential, not current cash",
            "Must explicitly note temporal mismatch",
        ],
        "expected_answer_shape": "explanation_with_temporal_caveat",
    },
    {
        "id": "Q8_modules_agree",
        "question": "Are these modules saying the same thing?",
        "category": "cross_module_reconciliation",
        "preferred_tool": "query_business_summary",
        "also_acceptable": [],
        "primary_evidence": "All module summaries + cross_module metadata",
        "evidence_rank": "all",
        "forbidden_shortcuts": [
            "Comparing period metrics with snapshot metrics as if aligned",
            "Treating all module outputs as equally reliable",
        ],
        "required_caveats": [
            "Must reference temporal_alignment metadata",
            "Must note which modules are period-aligned and which are snapshot",
            "Must follow evidence hierarchy",
        ],
        "expected_answer_shape": "meta_analysis_with_alignment_context",
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolAvailabilityForScenarios:
    """Verify that each scenario's preferred tool actually exists."""

    def test_all_preferred_tools_exist(self):
        all_tools = set()
        for path in [
            "modules/cashflow_monitor/ai_tools.py",
            "modules/customer_insights/ai_tools.py",
        ]:
            code = _read(path)
            for match in __import__('re').finditer(r'"name":\s*"(\w+)"', code):
                all_tools.add(match.group(1))

        for scenario in EVAL_SCENARIOS:
            tool = scenario["preferred_tool"]
            assert tool in all_tools, (
                f"Scenario {scenario['id']}: preferred tool '{tool}' "
                f"not found in registered tools. Available: {sorted(all_tools)}"
            )
            for alt in scenario.get("also_acceptable", []):
                assert alt in all_tools, (
                    f"Scenario {scenario['id']}: acceptable tool '{alt}' not found"
                )


class TestPromptSupportsScenarios:
    """Verify the system prompt provides guidance for each scenario category."""

    def test_prompt_mentions_business_summary_for_cross_module(self):
        code = _read("services/chat_service.py")
        assert "query_business_summary" in code
        assert "cross-module" in code.lower() or "trasversali" in code.lower()

    def test_prompt_mentions_cashflow_summary_for_cashflow(self):
        code = _read("services/chat_service.py")
        assert "query_cashflow_summary" in code

    def test_prompt_has_scadenzario_data_quality_rule(self):
        code = _read("services/chat_service.py")
        # Must instruct AI to check data quality for scadenzario
        assert "conditional" in code.lower() or "data_quality" in code.lower() or "no data entered" in code.lower()

    def test_prompt_has_causation_rule(self):
        code = _read("services/chat_service.py")
        assert "causation" in code.lower()

    def test_prompt_has_temporal_comparison_rule(self):
        # Wave 7A: commerce_signals was the only "snapshot" surface in
        # the chat prompt. Now we verify the temporal-discipline rule
        # by looking for "period" (always present) and "current" or
        # "scope" (covers commerce_operations vs period distinction).
        code = _read("services/chat_service.py").lower()
        assert "period" in code
        assert "scope" in code or "current" in code


class TestForbiddenShortcutsArePrevented:
    """Verify that known forbidden shortcuts are structurally prevented."""

    def test_no_2_bucket_net_in_ai_tools(self):
        """AI tool query_cashflow must NOT return 2-bucket net_cashflow."""
        code = _read("modules/cashflow_monitor/ai_tools.py")
        # Find the execute handler for query_cashflow (not query_cashflow_summary)
        handler_idx = code.index('tool_name == "query_cashflow"')
        handler_section = code[handler_idx:handler_idx + 2000]
        assert "net_after_fixed" in handler_section, (
            "query_cashflow tool handler must compute net_after_fixed (4-bucket)"
        )

    def test_no_legacy_cumulative_in_ai_tools(self):
        code = _read("modules/cashflow_monitor/ai_tools.py")
        assert "aggregate_cumulative_cashflow" not in code

    def test_snapshot_tools_marked(self):
        """Snapshot tools must declare temporal_alignment_safe: False."""
        for path in [
            "modules/customer_insights/ai_tools.py",
        ]:
            code = _read(path)
            assert "temporal_alignment_safe" in code, (
                f"{path}: must declare temporal_alignment_safe"
            )


class TestReasoningContractCompleteness:
    """Verify the reasoning contract covers all eval scenario categories."""

    def test_evidence_hierarchy_covers_all_sources(self):
        # Wave 7A (2026-05): signals.snapshot removed with the
        # commerce_signals module retirement.
        code = _read("services/business_summary.py")
        required_sources = [
            "cashflow.pnl",
            "customers.period",
            "cashflow.scadenzario",
            "cashflow.health_score",
        ]
        for source in required_sources:
            assert source in code, f"Evidence hierarchy missing source: {source}"

    def test_claim_rules_cover_all_types(self):
        code = _read("services/business_summary.py")
        required_types = [
            "factual",
            "factual_if_data_quality_sufficient",
            "conditional",
            "directional",
            "contextual_only",
        ]
        for claim_type in required_types:
            assert f'"{claim_type}"' in code, (
                f"Claim rules missing type: {claim_type}"
            )


class TestEvalScenarioMatrix:
    """Verify the eval scenario matrix is self-consistent."""

    def test_all_scenarios_have_required_fields(self):
        required = [
            "id", "question", "category", "preferred_tool",
            "primary_evidence", "forbidden_shortcuts", "required_caveats",
        ]
        for s in EVAL_SCENARIOS:
            for field in required:
                assert field in s, f"Scenario {s.get('id', '?')}: missing field '{field}'"

    def test_no_duplicate_scenario_ids(self):
        ids = [s["id"] for s in EVAL_SCENARIOS]
        assert len(ids) == len(set(ids)), f"Duplicate scenario IDs: {ids}"

    def test_scenario_count(self):
        assert len(EVAL_SCENARIOS) == 8, f"Expected 8 scenarios, found {len(EVAL_SCENARIOS)}"
