"""Wave 14.8 — Tool description rewrite for routing & scope clarity.

The chat AI sees a `description=` string for every registered tool
when deciding which one to call. Pre-Wave-14.8 these descriptions
accreted across waves 1-14 with no consistent style — some had
Italian routing examples, some didn't; some declared `_temporal_scope`
inline, most didn't; parameter names were almost never mentioned.

Wave 14.8 introduced a canonical template for the 9 highest-traffic
tools:

    [Action, one line]. SCOPE: [period_filtered|all_time|current_state].
    Restituisce: [3-5 key envelope fields].
    Usa per: ['domanda IT 1', 'domanda IT 2', ...].
    Param: [hint with explicit names + format].

The scope tag mirrors the vocabulary of Rule 18 (TEMPORAL SCOPE
DISCIPLINE) so Claude can cross-reference the system prompt rule
with the tool spec at decision time.

This file is the regression sentinel: every priority tool must
contain the canonical structure markers. A future commit that drops
the SCOPE: tag or strips the routing examples turns red.

The 2026-05-16 prod incident root cause: `query_top_customers` had
no temporal scope tag → the model attributed lifetime numbers to
the user's 30d period → hallucinated "fatturato 30 giorni" from
all-time data. Wave 14.8 makes `SCOPE: all_time` explicit on that
tool (and on query_customer_segments — same failure mode).
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


# ── The 9 priority tools rewritten in Wave 14.8 ───────────────────────────


PRIORITY_TOOLS_CASHFLOW = {
    "query_business_summary",
    "query_cashflow_summary",
    "query_revenue",
    "query_expenses",
    "query_anomaly_detection",
    "query_smart_brief",
    "query_period_comparison",
}

PRIORITY_TOOLS_CUSTOMER = {
    "query_customer_summary",
    "query_top_customers",
    "query_customer_segments",
}


def _get_description(tool_name: str) -> str:
    """Look the tool up across all module registries and return the
    description string. Raises KeyError if not found."""
    from modules.cashflow_monitor.ai_tools import (
        TOOL_DEFINITIONS as CF_TOOLS,
    )
    from modules.customer_insights.ai_tools import (
        TOOL_DEFINITIONS as CI_TOOLS,
    )

    for tool in CF_TOOLS + CI_TOOLS:
        if tool["name"] == tool_name:
            return tool["description"]
    raise KeyError(tool_name)


# ── SCOPE tag — the most important Wave 14.8 invariant ────────────────────


class TestExplicitScopeTag:
    """Every priority tool MUST declare `SCOPE: <one_of>` so the model
    knows whether the data is period-filtered, all-time, current-state,
    or forward-looking. This is what Rule 18 keys off of."""

    @pytest.mark.parametrize("tool_name", sorted(
        PRIORITY_TOOLS_CASHFLOW | PRIORITY_TOOLS_CUSTOMER
    ))
    def test_priority_tool_declares_scope(self, tool_name):
        desc = _get_description(tool_name)
        assert "SCOPE:" in desc, (
            f"Wave 14.8 regression — tool {tool_name!r} description "
            f"is missing the explicit 'SCOPE:' tag. Without it the AI "
            f"cannot cross-reference Rule 18 (TEMPORAL SCOPE DISCIPLINE) "
            f"at tool-pick time. Add 'SCOPE: period_filtered' or "
            f"'SCOPE: all_time' to the description."
        )

    def test_top_customers_is_explicitly_all_time(self):
        """The 2026-05-16 prod incident root cause: this tool was
        attributed to the period filter. The rewrite makes scope
        explicit."""
        desc = _get_description("query_top_customers")
        assert "SCOPE: all_time" in desc, (
            "Wave 14.8 — query_top_customers MUST declare "
            "'SCOPE: all_time' explicitly. The 2026-05-16 prod "
            "incident was caused by the model attributing lifetime "
            "numbers to a 30d period filter. Removing this tag "
            "re-opens that failure mode."
        )

    def test_customer_segments_is_explicitly_all_time(self):
        """Same failure mode as query_top_customers."""
        desc = _get_description("query_customer_segments")
        assert "SCOPE: all_time" in desc

    def test_customer_summary_is_explicitly_period_filtered(self):
        """The complement to top_customers — this is the "by period"
        flavour."""
        desc = _get_description("query_customer_summary")
        assert "SCOPE: period_filtered" in desc

    def test_cashflow_tools_are_period_filtered(self):
        """The 5 core cashflow tools all scope to the requested
        period."""
        for tool_name in (
            "query_business_summary",
            "query_cashflow_summary",
            "query_revenue",
            "query_expenses",
            "query_anomaly_detection",
            "query_smart_brief",
            "query_period_comparison",
        ):
            desc = _get_description(tool_name)
            assert "SCOPE: period_filtered" in desc, (
                f"Wave 14.8 — {tool_name} MUST declare "
                f"'SCOPE: period_filtered'."
            )


# ── Routing hints (Italian user-question examples) ────────────────────────


class TestItalianRoutingHints:
    """Every priority tool description embeds at least one example
    user question in Italian, so the model can pattern-match on the
    user's actual phrasing."""

    @pytest.mark.parametrize("tool_name", sorted(
        PRIORITY_TOOLS_CASHFLOW | PRIORITY_TOOLS_CUSTOMER
    ))
    def test_priority_tool_has_italian_routing_examples(self, tool_name):
        desc = _get_description(tool_name)
        assert "Usa" in desc or "usa" in desc, (
            f"Wave 14.8 — tool {tool_name!r} description has no "
            f"'Usa per:' / 'Usa quando:' routing examples in Italian. "
            f"Add at least one 'Usa per: \"<domanda utente IT>\"' "
            f"line so the model can pattern-match user phrasing."
        )
        # At least one quoted question mark — i.e. a literal example
        # question, not just a generic mention of "Usa".
        assert "?" in desc, (
            f"Wave 14.8 — tool {tool_name!r} description has no "
            f"literal example question. Routing hints work best when "
            f"they show actual user phrasing ending in '?'."
        )


# ── Parameter hints in description body ───────────────────────────────────


class TestParameterHintsInDescription:
    """For tools with non-obvious parameters (period_a_start, etc.),
    the description should name the parameters explicitly so the
    model doesn't have to reverse-engineer from input_schema alone."""

    def test_period_comparison_names_its_params(self):
        desc = _get_description("query_period_comparison")
        # All 4 dates are required and easily confused
        for param in (
            "period_a_start",
            "period_a_end",
            "period_b_start",
            "period_b_end",
        ):
            assert param in desc, (
                f"Wave 14.8 — query_period_comparison description "
                f"must mention {param!r} explicitly. With 4 required "
                f"date params, the model needs the parameter name in "
                f"the description body, not only in input_schema."
            )

    def test_summary_tools_name_their_period_alternatives(self):
        """Tools that accept BOTH `period=...` and
        `start_date+end_date` should mention both in the description
        so the model knows it has a choice."""
        for tool_name in (
            "query_business_summary",
            "query_cashflow_summary",
            "query_smart_brief",
        ):
            desc = _get_description(tool_name)
            assert "period=" in desc, (
                f"Wave 14.8 — {tool_name} description should show "
                f"the period parameter syntax (e.g. period='30d|ytd|..')."
            )
            assert "start_date" in desc, (
                f"Wave 14.8 — {tool_name} description should mention "
                f"the start_date+end_date alternative."
            )

    def test_period_keyword_vocabulary_mentioned(self):
        """The period_resolver accepts 7d / 30d / 90d / 1y / ytd /
        mtd / qtd. At least the summary tools should expose this
        vocabulary in their description so the model emits valid
        period strings."""
        for tool_name in (
            "query_business_summary",
            "query_cashflow_summary",
            "query_smart_brief",
        ):
            desc = _get_description(tool_name)
            # At minimum ytd must appear — that's the Wave 14.5 frame
            assert "ytd" in desc.lower(), (
                f"Wave 14.8 — {tool_name} should mention 'ytd' in "
                f"its period vocabulary so the model knows it's a "
                f"valid value (vs the legacy 7d/30d/90d-only list)."
            )


# ── Length sanity ─────────────────────────────────────────────────────────


class TestDescriptionLengthBudget:
    """Descriptions are charged on every API call as part of the
    cached tool spec — keep them under a sensible ceiling. The
    canonical template lands roughly 350-700 chars."""

    @pytest.mark.parametrize("tool_name", sorted(
        PRIORITY_TOOLS_CASHFLOW | PRIORITY_TOOLS_CUSTOMER
    ))
    def test_description_in_reasonable_range(self, tool_name):
        desc = _get_description(tool_name)
        n = len(desc)
        # Wave 14.HOTFIX5 — query_period_comparison description grew to
        # explain the canonicalization semantics and human_label
        # reading convention. Bumped ceiling to 1000.
        assert 200 <= n <= 1000, (
            f"Wave 14.8 — {tool_name} description is {n} chars. "
            f"The canonical template lands in 200-900. Outside that "
            f"range is either too terse (lost detail) or too verbose "
            f"(burning cache budget). Current: {desc[:80]!r}..."
        )


# ── Sibling routing cross-references ──────────────────────────────────────


class TestSiblingCrossReferences:
    """When two tools share a semantic surface but differ in temporal
    scope, each one MUST point to its sibling so the model knows
    when to switch."""

    def test_top_customers_points_to_customer_summary(self):
        """top_customers (all_time) must tell the model: 'for
        period-filtered customers use query_customer_summary'."""
        desc = _get_description("query_top_customers")
        assert "query_customer_summary" in desc, (
            "Wave 14.8 — query_top_customers (all_time) must "
            "cross-reference query_customer_summary (period_filtered) "
            "in its description. Without the back-pointer, the model "
            "won't know to switch tools when the user wants 'top "
            "clienti del periodo' instead of 'top clienti lifetime'."
        )

    def test_customer_summary_points_to_top_customers(self):
        desc = _get_description("query_customer_summary")
        assert "query_top_customers" in desc

    def test_customer_segments_points_to_customer_summary(self):
        desc = _get_description("query_customer_segments")
        assert "query_customer_summary" in desc

    def test_revenue_points_to_broader_alternatives(self):
        """query_revenue is a narrow tool — the description should
        point to broader alternatives for cases where the user wants
        more than just gross revenue."""
        desc = _get_description("query_revenue")
        assert (
            "query_cashflow_summary" in desc
            or "query_business_summary" in desc
        ), (
            "Wave 14.8 — query_revenue should point users to "
            "broader tools when they want margin / health analysis."
        )

    def test_smart_brief_points_to_numerical_alternatives(self):
        """smart_brief is narrative — for hard numbers the model
        should switch to summary tools."""
        desc = _get_description("query_smart_brief")
        assert "query_cashflow_summary" in desc


# ── Tool registry inventory smoke test ────────────────────────────────────


class TestRegistriesStillLoad:
    """All 4 priority modules' TOOL_DEFINITIONS still import and
    contain the 10 priority tools at their expected names."""

    def test_all_priority_tools_present(self):
        for tool_name in PRIORITY_TOOLS_CASHFLOW | PRIORITY_TOOLS_CUSTOMER:
            # raises KeyError if missing
            desc = _get_description(tool_name)
            assert isinstance(desc, str) and len(desc) > 0
