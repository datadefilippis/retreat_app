# AFianco Platform Governance Rules

## Purpose
These rules govern how the AI-governed platform evolves.
They are enforced by `tests/test_canonical_contracts.py`, `tests/test_ai_eval_harness.py`,
and `tests/test_governance_rules.py`.

## Rule Categories

### 1. Adding New KPIs
- All new KPIs MUST be added to the canonical `kpis` dict in `overview_builder.py`, NOT to `_legacy`.
- New KPIs MUST use the canonical 4-bucket model unless explicitly justified.
- If a new KPI is estimated, proxy, or data-quality-dependent, it MUST be documented with its epistemic class in `cashflow_summary.py`.
- New KPIs MUST be added to `TestCashflowCanonicalFields.REQUIRED_CANONICAL_FIELDS` in contract tests.

### 2. Adding New AI Tools
- New tools MUST declare `temporal_scope` ("period" or "snapshot") in their response.
- New tools MUST declare `temporal_alignment_safe` (true/false).
- New tools MUST include an `epistemic` block with at minimum: `epistemic_class`, `reliability`, `ai_usability`, `caveat`.
- Summary/holistic tools MUST be placed FIRST in TOOL_DEFINITIONS lists.
- New tools MUST be added to `TestToolRegistryContract` test counts.

### 3. Adding New Module Summaries
- New module AI summaries MUST include epistemic metadata per metric group.
- New module summaries that are period-based MUST accept `start_date`/`end_date` parameters.
- New module summaries that are snapshot-based MUST declare `temporal_scope: "snapshot"` and `temporal_alignment_safe: false`.
- New summaries MUST be integrated into `business_summary.py` if they participate in cross-module reasoning.

### 4. Cross-Module Comparisons
- New cross-module comparisons MUST be added to either `safe_comparisons` or `unsafe_comparisons` in the reasoning contract.
- Period-to-snapshot comparisons MUST be declared unsafe.
- New cross-module tools MUST declare their evidence rank in the hierarchy.

### 5. Temporal Metadata
- Every AI tool response MUST include `temporal_scope`.
- Period-based tools MUST include the actual `start_date`/`end_date` in their response.
- Snapshot tools MUST include `temporal_alignment_safe: false`.

### 6. Epistemic Metadata
- Every AI tool response that returns financial metrics MUST include an `epistemic` block.
- The block MUST contain: `epistemic_class`, `reliability`, `ai_usability`.
- Metrics that depend on optional fields (payment_status, due_date, customer_id) MUST include a `caveat`.

### 7. Deprecating Legacy Paths
- Legacy fields MUST be under `_legacy` keys, never in canonical dicts.
- Legacy endpoint functions MUST NOT be used by AI tools.
- Legacy repository functions (`aggregate_cumulative_cashflow`, `aggregate_expense_ratio`, etc.) MUST NOT be imported by AI tools.

### 8. Chat Prompt Governance
- The chat system prompt MUST reference `query_business_summary` as the first tool for cross-module questions.
- The prompt MUST include evidence hierarchy instructions.
- The prompt MUST include claim discipline rules.
- The prompt MUST warn against causation claims without evidence.

## Enforcement
These rules are enforced by the test suite. Every rule maps to at least one test.
Running `pytest tests/test_canonical_contracts.py tests/test_ai_eval_harness.py tests/test_governance_rules.py -v`
verifies compliance.
