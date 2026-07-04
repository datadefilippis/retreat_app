"""Wave 8E.2 — CI guard: no direct Anthropic SDK usage outside the gateway.

The entire AI governance suite (tracking + budgets + kill switch) only
works because ONE FILE is allowed to talk to the Anthropic SDK:

    services/llm/providers/anthropic.py

If any other file imports ``anthropic`` directly or instantiates an
``Anthropic()`` / ``AsyncAnthropic()`` client, governance is bypassed —
that call is invisible to AIUsageEvent, escapes budget enforcement,
ignores the kill switch.

This test pins the invariant: a PR that introduces a bypass fails CI.

Allowlist (files that may legitimately reference the SDK)
--------------------------------------------------------
  services/llm/providers/anthropic.py   — the canonical gateway
  tests/**                              — may mock + reference symbols
  scripts/migrate_*.py                   — one-off migrations (none today)

If you're tempted to add another file to ALLOWED_PATHS, ask first:
  "Can I do this through services.claude_client or services.llm
   instead?" — 99% yes.
"""
import os
import re
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parent.parent

# Files explicitly allowed to use the Anthropic SDK directly.
# Anything else is a governance bypass.
ALLOWED_PATHS = frozenset({
    # The canonical gateway — the WHOLE POINT is that this file talks
    # to Anthropic so the rest of the codebase doesn't have to.
    "services/llm/providers/anthropic.py",
})

# Tests are exempt: they may import anthropic for typing, mocking, or
# inspecting return shapes. Test code never reaches production runtime.
ALLOWED_DIR_PREFIXES = (
    "tests/",
)

# Patterns that indicate direct SDK usage. Each pattern is matched
# line-by-line with word boundaries so we don't trip on substrings.
_FORBIDDEN_PATTERNS = [
    # Import statements
    (re.compile(r"^\s*from\s+anthropic(\.|\s)"), "from anthropic import"),
    (re.compile(r"^\s*import\s+anthropic(\.|\s|$)"), "import anthropic"),
    # Client constructors — \b prevents matching AnthropicProvider(
    (re.compile(r"\bAnthropic\("), "Anthropic() constructor"),
    (re.compile(r"\bAsyncAnthropic\("), "AsyncAnthropic() constructor"),
    (re.compile(r"\banthropic\.Client\b"), "anthropic.Client"),
    (re.compile(r"\bAnthropicBedrock\("), "AnthropicBedrock() constructor"),
    (re.compile(r"\bAnthropicVertex\("), "AnthropicVertex() constructor"),
]


def _is_allowed(rel_path: str) -> bool:
    """True if the file is in the allowlist."""
    if rel_path in ALLOWED_PATHS:
        return True
    return any(rel_path.startswith(p) for p in ALLOWED_DIR_PREFIXES)


def _scan_python_files():
    """Yield (rel_path, abs_path) tuples for every .py file in backend."""
    for root, dirs, files in os.walk(BACKEND_ROOT):
        # Don't descend into common noise directories
        dirs[:] = [
            d for d in dirs
            if d not in (
                "venv", "__pycache__", "node_modules",
                ".pytest_cache", ".git", "dist", "build",
            )
        ]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            abs_path = Path(root) / fname
            rel_path = str(abs_path.relative_to(BACKEND_ROOT))
            yield rel_path, abs_path


def _violations_in(abs_path: Path):
    """Return a list of (line_no, line_text, why) for forbidden patterns."""
    violations = []
    try:
        with open(abs_path, encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, start=1):
                # Skip comment-only lines and docstring content
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for pattern, why in _FORBIDDEN_PATTERNS:
                    if pattern.search(line):
                        violations.append((line_no, line.rstrip(), why))
                        break  # one violation per line is enough
    except OSError:
        pass
    return violations


# ── The actual test ─────────────────────────────────────────────────────────


def test_no_direct_anthropic_sdk_outside_gateway():
    """Every Anthropic SDK reference must live in the allowlist.

    If this test fails, route your code through ``services.claude_client``
    (or the LLMProvider abstraction in ``services.llm``) so that:
      - The call is recorded as an AIUsageEvent (governance tracking).
      - The budget pre-flight check fires before the request.
      - The kill switch can disable it platform-wide.

    If you genuinely need a new direct-SDK file (very rare — e.g. a
    one-off migration script), add it to ALLOWED_PATHS WITH a justifying
    comment + a paired test that asserts your script ALSO writes an
    AIUsageEvent for each call.
    """
    bypasses = {}
    for rel_path, abs_path in _scan_python_files():
        if _is_allowed(rel_path):
            continue
        hits = _violations_in(abs_path)
        if hits:
            bypasses[rel_path] = hits

    if bypasses:
        # Produce a maximally helpful failure message
        lines = [
            "Direct Anthropic SDK usage detected outside the gateway.",
            "",
            "Governance suite (Wave 8) requires every Anthropic call to "
            "pass through services.llm.providers.anthropic.AnthropicProvider.",
            "Refactor the offending file to use services.claude_client or "
            "the LLMProvider abstraction.",
            "",
            "Offending files:",
        ]
        for path, hits in bypasses.items():
            lines.append(f"  {path}")
            for line_no, content, why in hits[:5]:  # cap per file
                lines.append(f"    L{line_no}  [{why}]")
                lines.append(f"           {content.strip()}")
            if len(hits) > 5:
                lines.append(f"    ... ({len(hits) - 5} more)")
        pytest.fail("\n".join(lines))


def test_gateway_file_actually_uses_sdk():
    """Sanity check: the allowlisted file MUST actually use the SDK.

    Without this, someone could refactor the gateway to a stub and
    accidentally pass the bypass test trivially (no callers + no SDK).
    """
    gateway = BACKEND_ROOT / "services" / "llm" / "providers" / "anthropic.py"
    assert gateway.exists(), f"Gateway file missing: {gateway}"

    with open(gateway, encoding="utf-8") as f:
        content = f.read()

    # At least one of: SDK import OR client constructor
    has_import = re.search(r"^\s*(from|import)\s+anthropic\b", content,
                           re.MULTILINE)
    has_client = re.search(r"\b(Async)?Anthropic\(", content)
    assert has_import or has_client, (
        "services/llm/providers/anthropic.py does not appear to use "
        "the Anthropic SDK. The whole governance architecture relies "
        "on this being the SOLE entry point — refusing to silently "
        "let it degrade into a no-op."
    )


def test_pattern_detection_actually_catches_known_bypasses():
    """Meta-test: pattern set catches the bypass shapes we care about.

    Without this, a regex regression could silently let bypasses through
    while this test file still passes (false negative).
    """
    cases_should_match = [
        "from anthropic import Anthropic",
        "from anthropic.types import Message",
        "import anthropic",
        "import anthropic.types",
        "client = Anthropic()",
        "client = Anthropic(api_key='x')",
        "client = AsyncAnthropic()",
        "c = anthropic.Client()",
        "client = AnthropicBedrock()",
        "client = AnthropicVertex()",
    ]
    cases_should_not_match = [
        # Class name, not the SDK constructor
        "provider = AnthropicProvider()",
        "from services.llm.providers.anthropic import AnthropicProvider",
        # A variable named with Anthropic but not a constructor call
        "AnthropicProviderError",
        # Comments referencing the SDK by name
        "# Note: anthropic returns cache_read_input_tokens",
        # Method chains on existing client
        "client.messages.create(...)",
    ]

    def _matches_any(line):
        return any(p.search(line) for p, _ in _FORBIDDEN_PATTERNS)

    for case in cases_should_match:
        assert _matches_any(case), (
            f"Bypass pattern should have caught this line but didn't: {case!r}"
        )
    for case in cases_should_not_match:
        assert not _matches_any(case), (
            f"False positive — pattern flagged this legitimate line: {case!r}"
        )


def test_allowlist_files_exist():
    """Every entry in ALLOWED_PATHS must resolve to a real file.

    If we ever remove a gateway file but forget to update the allowlist,
    new bypasses elsewhere would silently slip through this guard. This
    test keeps the allowlist honest.
    """
    for rel_path in ALLOWED_PATHS:
        abs_path = BACKEND_ROOT / rel_path
        assert abs_path.exists(), (
            f"ALLOWED_PATHS references a file that doesn't exist: {rel_path}. "
            "Either restore the file or remove the entry from ALLOWED_PATHS."
        )
