"""Wave 14.4 — System prompt rules consolidation.

The system prompt accreted across waves into 25 numbered rules, the
top half of which addressed format / evidence basics (1-13), the
middle CROSS-TOOL coherence (14-17), then temporal scope (18), and
finally the Wave 14.HOTFIX anti-hallucination cluster (19-25).

Wave 14.4 adds *visual cluster section headers* between groups of
rules WITHOUT renumbering anything — every sentinel test that
greps "19. SOURCE ATTRIBUTION" / "20. HARD STOP ..." etc. still
passes. The headers exist for two reasons:

  1. They help Claude Sonnet 4 form a "rule group" mental model
     so that when the situation matches a cluster (e.g. "I just
     got a tool error" → ANTI-HALLUCINATION cluster), the model
     reaches for the right cluster wholesale rather than recalling
     each rule independently. This was the consistent failure mode
     observed in the 2026-05-16 prod incident — the model violated
     three anti-hallucination rules simultaneously because they
     were buried in a flat 25-item list.

  2. They give future maintainers a navigable structure when adding
     Wave 15+ rules — new rules slot into the correct cluster
     instead of getting tacked onto the bottom as an undifferentiated
     #26.

This file is the regression sentinel: a future commit that removes
or renames a cluster header turns red here.

Wave 9.B.1 cache stability is preserved — all cluster headers are
static strings, no ISO dates, no per-org values.
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


# ── Cluster header sentinels ──────────────────────────────────────────────


class TestClusterHeaders:
    """Each of the 3 clusters in _PROMPT_CORE has a visual section
    header. Removing one is a regression."""

    def test_cross_tool_coherence_cluster_header_present(self):
        from services.chat_service import _PROMPT_CORE
        assert "CROSS-TOOL COHERENCE" in _PROMPT_CORE, (
            "Wave 14.4 regression — the CROSS-TOOL COHERENCE cluster "
            "header (between rules 13 and 14) is missing from "
            "_PROMPT_CORE. Without it, rules 14-17 lose their "
            "grouping cue."
        )

    def test_temporal_handling_cluster_header_present(self):
        from services.chat_service import _PROMPT_CORE
        assert "TEMPORAL SCOPE & PERIOD HANDLING" in _PROMPT_CORE, (
            "Wave 14.4 regression — the TEMPORAL SCOPE & PERIOD "
            "HANDLING cluster header (before rule 18) is missing."
        )

    def test_anti_hallucination_cluster_header_present(self):
        """The Wave 14.HOTFIX cluster header (before rule 19) was
        the first one introduced. Wave 14.4 keeps it intact."""
        from services.chat_service import _PROMPT_CORE
        assert "ANTI-HALLUCINATION CORE DISCIPLINE" in _PROMPT_CORE


# ── Cluster ordering ──────────────────────────────────────────────────────


class TestClusterOrdering:
    """The three cluster headers must appear in a specific order:
    CROSS-TOOL → TEMPORAL → ANTI-HALLUCINATION, mirroring rule
    numbering 14-17 → 18 → 19-25."""

    def test_clusters_appear_in_canonical_order(self):
        from services.chat_service import _PROMPT_CORE
        cross_tool_idx = _PROMPT_CORE.find("CROSS-TOOL COHERENCE")
        temporal_idx = _PROMPT_CORE.find("TEMPORAL SCOPE & PERIOD HANDLING")
        anti_hall_idx = _PROMPT_CORE.find("ANTI-HALLUCINATION CORE DISCIPLINE")

        assert cross_tool_idx > 0
        assert temporal_idx > cross_tool_idx, (
            "Wave 14.4 — TEMPORAL cluster must appear after "
            "CROSS-TOOL cluster (it covers rule 18, which follows "
            "rules 14-17)."
        )
        assert anti_hall_idx > temporal_idx, (
            "Wave 14.4 — ANTI-HALLUCINATION cluster must appear "
            "last (it covers rules 19-25)."
        )

    def test_each_cluster_precedes_its_rules(self):
        """Each cluster header must appear before its first rule."""
        from services.chat_service import _PROMPT_CORE

        cross_tool_idx = _PROMPT_CORE.find("CROSS-TOOL COHERENCE")
        rule_14_idx = _PROMPT_CORE.find("14. CASHFLOW PRIMACY")
        assert cross_tool_idx < rule_14_idx

        temporal_idx = _PROMPT_CORE.find("TEMPORAL SCOPE & PERIOD HANDLING")
        rule_18_idx = _PROMPT_CORE.find("18. TEMPORAL SCOPE DISCIPLINE")
        assert temporal_idx < rule_18_idx

        anti_hall_idx = _PROMPT_CORE.find("ANTI-HALLUCINATION CORE DISCIPLINE")
        rule_19_idx = _PROMPT_CORE.find("19. SOURCE ATTRIBUTION")
        assert anti_hall_idx < rule_19_idx


# ── Sentinel rule numbering still intact ──────────────────────────────────


class TestNoRenumbering:
    """Wave 14.4 added section headers but did NOT renumber any
    rule. Every rule 1-25 must still appear at its original number
    so legacy sentinel tests in other test files keep passing."""

    def test_all_25_rules_still_numbered_canonically(self):
        from services.chat_service import _PROMPT_CORE

        # Spot check the boundary rules at each cluster transition
        canonical_markers = [
            "13. When a tool returns has_data=false",
            "14. CASHFLOW PRIMACY",
            "15. DISCREPANCY DETECTION",
            "16. TOOL VACUUM",
            "17. NO HALLUCINATED TOOLS",
            "18. TEMPORAL SCOPE DISCIPLINE",
            "19. SOURCE ATTRIBUTION",
            "20. HARD STOP ON TOOL ERROR",
            "21. HAS_DATA BINDING",
            "22. NO ESTIMATION",
            "23. TRUNCATION HANDLING",
            "24. CROSS-TURN PERIOD MEMORY",
            "25. SIGN AND DIRECTION INTEGRITY",
        ]
        for marker in canonical_markers:
            assert marker in _PROMPT_CORE, (
                f"Wave 14.4 regression — rule marker {marker!r} no "
                "longer present at the expected canonical position. "
                "Section header addition must NEVER renumber rules."
            )


# ── Cache stability ───────────────────────────────────────────────────────


class TestCacheStability:
    """Cluster headers must not contain interpolation placeholders
    or ISO dates — they are static strings that ride the Anthropic
    prompt cache across requests / orgs / days."""

    def test_cluster_headers_contain_no_iso_dates(self):
        import re
        from services.chat_service import _PROMPT_CORE

        # Extract just the cluster header lines
        for header in (
            "CROSS-TOOL COHERENCE",
            "TEMPORAL SCOPE & PERIOD HANDLING",
            "ANTI-HALLUCINATION CORE DISCIPLINE",
        ):
            idx = _PROMPT_CORE.find(header)
            line_start = _PROMPT_CORE.rfind("\n", 0, idx) + 1
            line_end = _PROMPT_CORE.find("\n", idx)
            line = _PROMPT_CORE[line_start:line_end]
            iso_dates = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", line)
            assert iso_dates == [], (
                f"Wave 9.B.1 / Wave 14.4 regression — cluster header "
                f"line {line!r} contains ISO date {iso_dates}. Headers "
                f"must be cache-stable static strings."
            )

    def test_cluster_headers_contain_no_format_placeholders(self):
        """Section headers must not introduce new {placeholder} tokens
        that _PROMPT_CORE.format() in _build_system_prompt would
        choke on."""
        from services.chat_service import _PROMPT_CORE
        for header in (
            "CROSS-TOOL COHERENCE",
            "TEMPORAL SCOPE & PERIOD HANDLING",
            "ANTI-HALLUCINATION CORE DISCIPLINE",
        ):
            idx = _PROMPT_CORE.find(header)
            line_start = _PROMPT_CORE.rfind("\n", 0, idx) + 1
            line_end = _PROMPT_CORE.find("\n", idx)
            line = _PROMPT_CORE[line_start:line_end]
            # An odd number of unescaped braces would crash format()
            assert "{" not in line or "{{" in line, (
                f"Cluster header {line!r} contains an unescaped '{{' — "
                f"_PROMPT_CORE.format(...) will treat it as a "
                f"placeholder and KeyError at chat() startup."
            )


# ── Rendered prompt smoke test ────────────────────────────────────────────


class TestRenderedPromptStillBuilds:
    """End-to-end check that _build_system_prompt() with the new
    cluster headers still renders without crashing format()."""

    def test_build_system_prompt_succeeds(self):
        from services.chat_service import _build_system_prompt
        from core.locale_utils import get_locale_profile

        # Render for a typical Italian cashflow-only org
        prompt = _build_system_prompt(
            active_modules={"cashflow_monitor"},
            locale_profile=get_locale_profile("it"),
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 1000

        # All 3 cluster headers visible in the final rendered prompt
        assert "CROSS-TOOL COHERENCE" in prompt
        assert "TEMPORAL SCOPE & PERIOD HANDLING" in prompt
        assert "ANTI-HALLUCINATION CORE DISCIPLINE" in prompt

        # No format leftovers
        assert "{respond_instruction}" not in prompt
        assert "{active_modules_list}" not in prompt
