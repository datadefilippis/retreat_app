"""
LLM provider abstraction — platform layer for AFianco AI features.

This package isolates the LLM provider implementation behind a single
interface (LLMProvider) so swapping Anthropic for OpenAI / xAI / etc.
is a one-file change (services/llm/providers/<new>.py).

Public surface:
    get_provider(name=None) -> LLMProvider
        Returns the configured provider. Default name comes from env
        LLM_PROVIDER (currently "anthropic").

    LLMProvider (abstract base):
        is_available() -> bool
        send_message(system, user_message, ...) -> str
        send_messages(system, messages, ...) -> str
        send_messages_with_tools(system, messages, tools, on_tool_call, ...)
            -> (text, messages, usage)
        format_tools(definitions) -> list      # provider-specific schema
        calculate_cost(tokens_in, tokens_out, ...) -> Optional[float]

    LLMUnavailableError:
        Raised when the provider can't be reached / isn't configured.
        ClaudeUnavailableError is an alias preserved for backward compat
        with the 9 pre-Wave-2 callers.

Why a package and not a single module:
    Each provider gets its own file under providers/, keeping their
    SDK imports localised. The interface (provider.py) has zero
    dependencies on any specific SDK. Adding "openai" tomorrow is:
        services/llm/providers/openai.py     +1 file
        update services/llm/factory.py       +1 branch
        zero changes to any caller.
"""
from services.llm.provider import LLMProvider, LLMUnavailableError
from services.llm.factory import get_provider

# Backward-compat alias — 9 existing callers import ClaudeUnavailableError
# from services.claude_client. The shim re-exports this name.
ClaudeUnavailableError = LLMUnavailableError

__all__ = [
    "LLMProvider",
    "LLMUnavailableError",
    "ClaudeUnavailableError",
    "get_provider",
]
