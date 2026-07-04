"""
Claude client — backward-compatibility shim for the LLM provider abstraction.

DEPRECATED — do not add new logic here. As of Wave 2 (2026-05) the
provider implementation lives in services/llm/providers/anthropic.py
behind the generic services.llm.LLMProvider interface.

This file remains as a thin re-export shim so the pre-Wave-2 callers
(chat_service, ai_insight_service, alert_analysis, health_explanation,
digest_builder, digest_report_builder, plus tests) continue to import
the same names without modification. Wave 8E.2 removed the long-
dormant ai_store router + ai_enrichment paths from the surface.

    from services.claude_client import (
        send_message, send_messages, send_messages_with_tools,
        is_available, ClaudeUnavailableError,
    )

New code should import from services.llm directly:

    from services.llm import get_provider, LLMUnavailableError
    provider = get_provider()           # honours LLM_PROVIDER env
    text = await provider.send_message(...)

The shim is planned for removal in Wave 5 once all callers have
migrated to the new entry point. Until then, semantics are preserved
bit-for-bit.

The _MODEL re-export is kept because chat_service uses it for the
usage event's model_version field. Wave 4 will replace this with
provider.default_model + per-agent overrides.
"""
import logging
from typing import Callable, Dict, List, Optional, Tuple

from services.llm import LLMUnavailableError as _LLMUnavailableError
from services.llm import get_provider

logger = logging.getLogger(__name__)

# ── Backward-compat re-exports ──────────────────────────────────────────────

# Symbol names preserved from pre-Wave-2 to avoid breaking the 9 callers.
ClaudeUnavailableError = _LLMUnavailableError

# Wave 1.3 callers (chat_service) reference this to set
# AIUsageEvent.model_version. Keep it pointing at the active provider's
# default model so it's always correct.
_MODEL = get_provider().default_model


def is_available() -> bool:
    """True when the active LLM provider is configured."""
    return get_provider().is_available()


async def send_message(
    system: str,
    user_message: str,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str:
    """Send a single user message to the active LLM. Returns text response.

    Raises ClaudeUnavailableError on failure (alias of LLMUnavailableError).
    """
    return await get_provider().send_message(
        system, user_message,
        max_tokens=max_tokens, temperature=temperature,
    )


async def send_message_with_usage(
    system: str,
    user_message: str,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    *,
    model_version: Optional[str] = None,
) -> Tuple[str, Dict[str, int]]:
    """Wave 8A.0 — like send_message but returns (text, usage_dict).

    Usage dict shape:
        {"input_tokens": int, "output_tokens": int,
         "cache_read_tokens": int, "cache_creation_tokens": int}

    Wave 9.B.2 — ``model_version`` keyword lets callers pick a cheaper
    model for non-chat summarization (e.g. Haiku 4 at ~25% of Sonnet 4
    cost). When None, the provider's default is used (Sonnet 4 today).

    Use this in code paths that were previously hitting Anthropic
    without tracking (digests, health explanations, insights) — closes
    the visibility gap that produced un-attributed spend.

    Raises ClaudeUnavailableError on failure.
    """
    return await get_provider().send_message_with_usage(
        system, user_message,
        max_tokens=max_tokens, temperature=temperature,
        model_version=model_version,
    )


def resolve_non_chat_model() -> str:
    """Model_version for non-chat features (digest, health, alert_analysis).

    Wave 9.B.2 (2026-05) introduced this helper and defaulted to Haiku 4
    to optimize cost. After ~3 weeks in production the user-perceived
    quality regression on narrative-synthesis features (digest, health
    explanation, alert analysis) was significant — Haiku tends to
    just restate input numbers rather than connect them with reasoning.

    Wave 11.1 (2026-05) reverts the default to "" (= provider's
    default = Sonnet 4). The cost trade-off is small at current scale
    (+$11/mo at 50 org, +$110/mo at 500 org) and is offset by Wave 11.2
    reducing the cron frequency from 4× to 1× per day. Net cost roughly
    flat; quality jump substantial.

    The env knob ``LLM_NON_CHAT_MODEL`` remains as an escape hatch:
      - Set to a specific slug (e.g. "claude-haiku-4-20250514") to
        force Haiku per-feature for high-volume / low-quality-need paths.
      - Set to "default" / "provider" → empty string (same as unset
        post-Wave 11.1; kept for backward compat with env scripts).
      - Unset (production default) → empty string → Sonnet 4 via
        ``AnthropicProvider.default_model``.
    """
    import os as _os9b
    explicit = (_os9b.environ.get("LLM_NON_CHAT_MODEL") or "").strip()
    if explicit in ("default", "provider"):
        return ""  # caller will use provider.default_model (Sonnet)
    if explicit:
        return explicit  # ops-supplied specific model
    # Wave 11.1 — provider default (Sonnet 4). Was Haiku in 9.B.2.
    return ""


def get_active_model() -> str:
    """Return the model_version string the active provider will use.

    Helper for callers that need to record AIUsageEvent.model_version
    without depending on the deprecated _MODEL re-export.
    """
    return get_provider().default_model


def calculate_cost_usd(
    tokens_prompt: Optional[int],
    tokens_completion: Optional[int],
    *,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
    model_version: Optional[str] = None,
) -> Optional[float]:
    """Convenience helper for callers that have usage but need the cost.

    Routes to the active provider's calculate_cost_usd(). Returns None
    for unknown models so caller can still write the event without cost.

    Wave 8E.2: ``cache_creation_tokens`` added so callers can pass the
    Anthropic ``cache_creation_input_tokens`` value. Default 0 keeps
    backward compat with pre-fix callers; new ones SHOULD pass it.
    """
    provider = get_provider()
    return provider.calculate_cost_usd(
        model_version or provider.default_model,
        tokens_prompt,
        tokens_completion,
        cache_read_tokens=cache_read_tokens,
        cache_creation_tokens=cache_creation_tokens,
    )


async def send_messages(
    system: str,
    messages: List[dict],
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str:
    """Multi-turn send (no tools). Returns text response."""
    return await get_provider().send_messages(
        system, messages,
        max_tokens=max_tokens, temperature=temperature,
    )


async def send_messages_with_tools(
    system,  # str OR list of {type, text, cache_control?} blocks — Wave 10.B.1
    messages: List[dict],
    tools: List[dict],
    on_tool_call: Callable,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    max_rounds: int = 5,
    on_round: Optional[Callable] = None,
) -> Tuple[str, List[dict], Dict[str, int]]:
    """Agentic loop with tool use. Returns (text, messages, usage).

    Wave 8A.2: `on_round` is an optional async callable invoked after
    each round-trip with the per-round token usage. Used by chat_service
    to write one AIUsageEvent per round-trip (replaces the single
    aggregate event that under-counted multi-turn chats).

    Wave 10.B.1: `system` accepts a list of {type:"text", text, cache_control}
    blocks for explicit cache split. The provider's _system_with_cache
    detects the shape and passes through. String input keeps current
    behaviour (single cached block).
    """
    return await get_provider().send_messages_with_tools(
        system, messages, tools, on_tool_call,
        max_tokens=max_tokens,
        temperature=temperature,
        max_rounds=max_rounds,
        on_round=on_round,
    )


__all__ = [
    "ClaudeUnavailableError",
    "is_available",
    "send_message",
    "send_message_with_usage",   # Wave 8A.0 — usage-aware variant
    "send_messages",
    "send_messages_with_tools",
    "get_active_model",          # Wave 8A.0 — model_version helper
    "calculate_cost_usd",        # Wave 8A.0 — cost helper for tracking
    "resolve_non_chat_model",    # Wave 9.B.2 — Haiku selector for digest/health/alert
    "_MODEL",  # used by chat_service for AIUsageEvent.model_version
]
