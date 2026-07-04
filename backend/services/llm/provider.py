"""
LLMProvider — abstract interface every concrete provider implements.

Design principles
-----------------
- **Zero SDK dependencies in this file.** The interface only knows about
  primitives (str, list[dict], Callable). Each concrete provider in
  providers/<name>.py imports its own SDK. Adding a new provider must
  not require changing this file.

- **Provider-agnostic data shapes.** Tool definitions arrive as plain
  dicts (the format AFianco's modules already produce). The provider
  knows how to translate them to its native schema (Anthropic's
  input_schema, OpenAI's parameters, etc.) inside format_tools().

- **Token usage normalisation.** Every call that consumes tokens
  returns a token_usage dict with the same shape:
    {"input_tokens": int, "output_tokens": int,
     "cache_read_tokens": int (optional)}
  so the calling layer (chat_service, digest_builder, etc.) can record
  usage uniformly regardless of provider.

- **Errors are normalised too.** Every failure raises
  LLMUnavailableError (or a subclass). Provider-specific exceptions
  must be caught and re-wrapped inside the concrete provider so callers
  never need to import anthropic / openai / etc.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple


class LLMUnavailableError(Exception):
    """Raised when the configured LLM provider cannot fulfil the request.

    The exception message is safe to surface to the user; the underlying
    cause is left in __cause__ for logging / Sentry capture.

    Reasons that produce this error:
        - Provider SDK not installed
        - API key missing / invalid
        - Provider returned an unrecoverable error
        - Provider down (network / 5xx)

    Transient errors (429 rate limit, 529 overloaded) are wrapped in
    this exception today; Wave 3 will introduce retry/backoff inside
    the provider before bubbling up, so this exception will become
    rarer.
    """
    pass


class LLMProvider(ABC):
    """Abstract interface every concrete LLM provider must implement.

    A new provider lives in services/llm/providers/<name>.py and is
    a subclass of this. The factory (services/llm/factory.py) decides
    which one to instantiate based on the LLM_PROVIDER env var.
    """

    # ── Identity ──────────────────────────────────────────────────────────

    @property
    @abstractmethod
    def name(self) -> str:
        """Short slug, e.g. "anthropic" or "openai". Used in logs + usage events."""
        raise NotImplementedError

    @property
    @abstractmethod
    def default_model(self) -> str:
        """The default model version this provider uses when none is specified."""
        raise NotImplementedError

    # ── Availability ──────────────────────────────────────────────────────

    @abstractmethod
    def is_available(self) -> bool:
        """True when the provider is configured (key present, SDK installed).

        Called by chat_service.chat() before invoking the provider, so a
        misconfigured environment returns a clean 503 instead of a stack
        trace.
        """
        raise NotImplementedError

    # ── Tool format conversion ────────────────────────────────────────────

    @abstractmethod
    def format_tools(self, definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert AFianco's provider-agnostic tool definitions to the
        provider's native schema.

        AFianco modules expose tools in either of two shapes (legacy flat
        or JSON Schema). The provider knows how to map both to its own
        format (Anthropic: input_schema; OpenAI: parameters / function
        spec). This is where the SDK-specific knowledge lives.
        """
        raise NotImplementedError

    # ── Single-shot send ─────────────────────────────────────────────────

    @abstractmethod
    async def send_message(
        self,
        system: str,
        user_message: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        model_version: Optional[str] = None,
    ) -> str:
        """Send one user message + system prompt. Return the text response.

        Used by: digests, insights, signal enrichment, alert analysis.
        For multi-turn or tool-use, use send_messages_with_tools instead.

        For governance / usage tracking, prefer ``send_message_with_usage()``
        which returns both text AND a normalised token_usage dict so the
        caller can record an AIUsageEvent with cost_usd populated. This
        method is kept for callers that do not need governance (e.g. tests).

        Raises LLMUnavailableError on failure.
        """
        raise NotImplementedError

    async def send_message_with_usage(
        self,
        system: str,
        user_message: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        model_version: Optional[str] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Wave 8A.0 — same as send_message but also returns token usage.

        Honours the "token usage normalisation" design principle stated
        at the top of this file: every call that consumes tokens MUST
        return a normalised usage dict.

        Returns:
            (text, usage) where usage is:
                {"input_tokens": int,
                 "output_tokens": int,
                 "cache_read_tokens": int,
                 "cache_creation_tokens": int}

        Default implementation: call send_message() and return zero-usage.
        Concrete providers SHOULD override to surface real Anthropic /
        OpenAI usage from the SDK response.
        """
        text = await self.send_message(
            system, user_message,
            max_tokens=max_tokens,
            temperature=temperature,
            model_version=model_version,
        )
        return text, {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_creation_tokens": 0,
        }

    # ── Multi-turn send (no tools) ───────────────────────────────────────

    @abstractmethod
    async def send_messages(
        self,
        system: str,
        messages: List[dict],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        model_version: Optional[str] = None,
    ) -> str:
        """Multi-turn send without tool use. Returns the text response.

        `messages` follows the provider-agnostic shape:
            [{"role": "user"|"assistant", "content": str}, ...]
        The provider translates it to its native message format inside.

        Raises LLMUnavailableError on failure.
        """
        raise NotImplementedError

    # ── Agentic send (multi-turn + tool use) ─────────────────────────────

    @abstractmethod
    async def send_messages_with_tools(
        self,
        system: str,
        messages: List[dict],
        tools: List[Dict[str, Any]],
        on_tool_call: Callable,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        max_rounds: int = 5,
        model_version: Optional[str] = None,
        on_round: Optional[Callable] = None,
    ) -> Tuple[str, List[dict], Dict[str, int]]:
        """Run an agentic loop: send messages, intercept tool_use,
        execute via on_tool_call, send tool_result back, repeat until
        the model emits its final text.

        Args:
            tools: list of tool dicts in PROVIDER NATIVE format (already
                passed through self.format_tools() by the caller — the
                tool registry).
            on_tool_call: async callable (tool_name, tool_input) -> dict.
                Returns the tool's JSON-serialisable result. The agentic
                loop wraps it into the provider's tool_result block.
            max_rounds: safety limit to prevent infinite tool loops.
            on_round: Wave 8A.2 — optional async callable invoked AFTER
                each Anthropic round-trip with the per-round usage.
                Signature: ``async on_round(round_index: int, usage: dict) -> None``
                where usage has keys input_tokens, output_tokens,
                cache_read_tokens, cache_creation_tokens.
                chat_service uses this to write one AIUsageEvent per
                round-trip (linked by conversation_id) instead of a
                single aggregate event per chat — closes the previous
                under-counting that made Anthropic spend look smaller
                than it really was.
                The callback MUST NOT raise — exceptions are caught and
                logged so a tracking failure cannot kill the chat itself.

        Returns:
            (assistant_text, updated_messages, usage) where usage is
            {"input_tokens": int, "output_tokens": int} summed across
            all rounds.

        Raises LLMUnavailableError on failure.
        """
        raise NotImplementedError

    # ── Cost calculation ─────────────────────────────────────────────────

    @abstractmethod
    def calculate_cost_usd(
        self,
        model_version: str,
        tokens_prompt: Optional[int],
        tokens_completion: Optional[int],
        *,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> Optional[float]:
        """Return the USD cost for the given token counts.

        Wave 8E.2: ``cache_creation_tokens`` added (Anthropic's
        cache_creation_input_tokens, billed at 1.25× input rate). The
        4 token streams (input / output / cache_read / cache_creation)
        are DISJOINT and each contributes to the total independently.

        Delegates to services.ai_cost_calculator under the hood; here
        it lives on the provider because pricing tables live PER
        provider. Returns None for unknown models (caller persists
        cost_usd=None but still records the event).
        """
        raise NotImplementedError

    # ── Streaming (Wave 3.4) ────────────────────────────────────────────
    # Emits text chunks as they're generated so the UI can render the
    # first words within ~1s instead of waiting for the full response
    # (~5-30s with the agentic loop). The contract is intentionally
    # simple — an async generator of plain str chunks — so callers
    # don't need to know about Anthropic's MessageStreamEvent shape.
    # Tool use is NOT supported in the streaming path (Anthropic
    # streams text only when no tools are in flight); callers wanting
    # streaming + tools should use send_messages_with_tools and
    # adapt the final text to a single chunk if needed.
    #
    # Default implementation: NotImplementedError. Providers that
    # support streaming override this.

    async def stream_messages(
        self,
        system: str,
        messages: List[dict],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        model_version: Optional[str] = None,
    ):
        """Stream a multi-turn response chunk by chunk.

        Returns an async generator yielding str chunks (the text
        deltas produced by the model). Raises LLMUnavailableError
        on configuration / API errors.

        Override on the concrete provider. Subclasses that don't
        support streaming let this raise NotImplementedError, and
        the router falls back to the non-streaming endpoint.
        """
        raise NotImplementedError(
            f"{self.name} provider does not yet support streaming. "
            "Use send_messages instead."
        )
