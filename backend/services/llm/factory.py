"""
LLM provider factory — resolve which concrete provider to use.

Resolution priority:
    1. Explicit `name` argument (used by tests + future per-agent provider)
    2. LLM_PROVIDER env var
    3. Default: "anthropic" (today's only production provider)

The factory caches one instance per provider name so the underlying
SDK client (and its connection pool) is reused across requests.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

from services.llm.provider import LLMProvider, LLMUnavailableError


# ── Registry of available providers ─────────────────────────────────────────
# Keep this declarative + tiny — adding a new provider is one line.

_PROVIDER_REGISTRY: Dict[str, type] = {}


def _ensure_anthropic_registered() -> None:
    """Lazy registration to avoid importing the SDK at module-load time
    when callers only need the interface types."""
    if "anthropic" in _PROVIDER_REGISTRY:
        return
    from services.llm.providers.anthropic import AnthropicProvider
    _PROVIDER_REGISTRY["anthropic"] = AnthropicProvider


# Future providers register the same way:
#   def _ensure_openai_registered():
#       from services.llm.providers.openai import OpenAIProvider
#       _PROVIDER_REGISTRY["openai"] = OpenAIProvider

_REGISTERS = {
    "anthropic": _ensure_anthropic_registered,
    # "openai": _ensure_openai_registered,
}


# ── Instance cache ──────────────────────────────────────────────────────────
# One instance per provider name. The provider itself does lazy SDK init,
# so calling get_provider() at import time is safe.

_INSTANCES: Dict[str, LLMProvider] = {}


def get_provider(name: Optional[str] = None) -> LLMProvider:
    """Return a configured LLMProvider instance.

    Args:
        name: explicit provider slug. When None, reads LLM_PROVIDER env
            (default "anthropic").

    Raises:
        LLMUnavailableError: when the requested provider isn't registered.

    Examples:
        >>> get_provider()                # uses LLM_PROVIDER env
        >>> get_provider("anthropic")     # explicit
        >>> get_provider("openai")        # would raise until OpenAI ships
    """
    if name is None:
        name = os.environ.get("LLM_PROVIDER", "anthropic").lower().strip()

    if name not in _REGISTERS:
        raise LLMUnavailableError(
            f"Unknown LLM provider '{name}'. "
            f"Available: {sorted(_REGISTERS.keys())}. "
            f"Add a provider at services/llm/providers/<name>.py."
        )

    if name in _INSTANCES:
        return _INSTANCES[name]

    _REGISTERS[name]()
    instance = _PROVIDER_REGISTRY[name]()
    _INSTANCES[name] = instance
    return instance


def reset_for_tests() -> None:
    """Clear the instance cache. ONLY for tests; never call from prod code."""
    _INSTANCES.clear()
