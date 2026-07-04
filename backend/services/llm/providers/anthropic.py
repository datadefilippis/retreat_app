"""
AnthropicProvider — concrete LLMProvider implementation for Claude.

Behaviour-equivalent to the pre-Wave-2 services/claude_client.py. All
logic moved here so the legacy module can become a thin re-export shim.

Encapsulated provider-specific concerns:
  - SDK import (anthropic.AsyncAnthropic)
  - API key resolution (ANTHROPIC_API_KEY env)
  - Tool format conversion (input_schema)
  - Message format (content blocks: text / tool_use / tool_result)
  - Error wrapping (any anthropic exception -> LLMUnavailableError)

Cross-cutting concerns deliberately stay outside:
  - Cost calculation -> services.ai_cost_calculator (per-provider table
    lives there because it's likely to grow with each new provider
    rather than scale per-provider file)
  - Usage event recording -> chat_service / call sites (they have the
    user_id + agent_id context this layer doesn't)
  - Retry / circuit breaker -> Wave 3 (will land here once introduced)
  - Sentry tagging -> done at the call site (chat_service) so the tags
    include user_id + agent_id too
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

from services.llm.provider import LLMProvider, LLMUnavailableError
from services.llm.circuit_breaker import get_breaker

logger = logging.getLogger(__name__)


# ── Anthropic-specific constants ────────────────────────────────────────────

# Claude Sonnet 4 (claude-sonnet-4-20250514) è stato ritirato (giu 2026) → 404.
# Sostituto drop-in: Sonnet 4.6. Override runtime via env CLAUDE_MODEL.
_DEFAULT_MODEL = "claude-sonnet-4-6"
_TIMEOUT_SECONDS = 30.0

# ── Wave 3.7 (2026-05): backpressure semaphore ─────────────────────────────
# Caps the number of concurrent in-flight Anthropic calls per process.
# At 150 user target with peak ~25 concurrent chats × up to 5 rounds,
# bursts can hit 30+ simultaneous requests against Anthropic. Without
# a semaphore we send them all immediately and Anthropic's rate limit
# starts 429-ing — which retry/backoff covers, but at the cost of
# 1-7 seconds of perceived latency on the affected requests.
#
# A semaphore at MAX_CONCURRENT (default 20) holds excess requests
# inside our process while the active ones drain. Latency stays
# bounded because we never let more than 20 wait at Anthropic.
#
# Env override lets ops bump this when we move from Tier 1 to Tier 2/3.
_MAX_CONCURRENT = int(os.environ.get("LLM_MAX_CONCURRENT", "20"))
_semaphore: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    """Lazy-init the semaphore so it binds to the active event loop."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
    return _semaphore

# ── Wave 3.1: retry on transient errors ──────────────────────────────────────
# Anthropic returns 429 (rate limit), 529 (overloaded), and occasional 5xx
# that are transient. Without retry the first such error bubbles up as a
# 503 to the merchant. Three retries with exponential backoff + jitter
# converts most transient failures into successful requests.
#
# Pre-Wave-3 baseline: 0 retries — every transient -> user-facing 503.
# Post-Wave-3 target: <1% user-facing 503 under normal traffic.

_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 1.0  # 1s, 2s, 4s (plus jitter)


# Status codes / error names that justify retry. We retry on transient
# server-side problems but NOT on 4xx (other than 429), which are
# permanent and would just waste latency.
def _is_retriable(exc: Exception) -> bool:
    """Decide whether an Anthropic SDK exception is worth retrying.

    Strategy:
        - 429 RateLimitError -> retry (server says "slow down")
        - 529 OverloadedError -> retry (capacity issue, transient)
        - 5xx APIStatusError -> retry (server fault, transient)
        - APIConnectionError / APITimeoutError -> retry (network)
        - 4xx other than 429 -> NO retry (auth/quota/bad request)
        - Everything else -> NO retry (unknown -> fail fast)
    """
    # Lazy import: anthropic SDK may not be installed in some test envs
    try:
        import anthropic
    except ImportError:
        return False

    if isinstance(exc, anthropic.RateLimitError):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        # status_code attr is the HTTP code
        code = getattr(exc, "status_code", None)
        if code is None or not isinstance(code, int):
            return False
        if code == 529:  # OverloadedError surfaced as APIStatusError
            return True
        return 500 <= code < 600
    if isinstance(exc, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
        return True
    return False


# ── Wave 10.B.3 — per-process "degraded" mark after consecutive retries ──
# When a single _retry_with_backoff burns 2+ retries (i.e. Anthropic was
# flapping for several seconds), mark the provider degraded for a short
# window. While degraded, _retry_with_backoff drops max_retries to 1.
# This bounds the cost of a thundering-herd retry storm during an
# Anthropic outage:
#   - normal: 3 retries × 20 concurrent = up to 60 in-flight retries
#   - degraded: 1 retry × 20 concurrent = up to 20 in-flight retries
# The global circuit breaker still exists for the catastrophic case
# (≥5 consecutive failures opens it for 30s); this is the gentler,
# always-on companion.
_DEGRADED_THRESHOLD_RETRIES = int(os.environ.get("LLM_DEGRADED_THRESHOLD", "2"))
_DEGRADED_WINDOW_SECONDS = float(os.environ.get("LLM_DEGRADED_WINDOW_SEC", "60"))
_degraded_until_ts: float = 0.0


def _is_degraded() -> bool:
    """True when the provider is in the degraded window."""
    return asyncio.get_event_loop().time() < _degraded_until_ts


def _mark_degraded(reason: str) -> None:
    """Mark the provider degraded for _DEGRADED_WINDOW_SECONDS."""
    global _degraded_until_ts
    _degraded_until_ts = (
        asyncio.get_event_loop().time() + _DEGRADED_WINDOW_SECONDS
    )
    logger.warning(
        "anthropic_provider: marked DEGRADED for %.0fs (reason=%s). "
        "max_retries will drop to 1 until the window passes.",
        _DEGRADED_WINDOW_SECONDS, reason,
    )


async def _retry_with_backoff(call, *, max_retries: int = _MAX_RETRIES):
    """Execute ``call`` (an async callable) with retry on transient errors.

    Exponential backoff with jitter so retries don't synchronise across
    concurrent requests (the "thundering herd" problem on the Anthropic
    side after a brief outage).

    Wave 10.B.3: when the process is in the degraded window, max_retries
    is clamped to 1 regardless of the caller's value. This limits the
    cost amplification of an outage from 4× (1 + 3 retries) to 2×.

    The function preserves the LAST exception type so the LLM-layer
    error wrapping still works as before.
    """
    if _is_degraded():
        max_retries = min(max_retries, 1)

    last_exc: Optional[Exception] = None
    consecutive_retries_this_call = 0
    for attempt in range(max_retries + 1):  # initial + retries
        try:
            return await call()
        except Exception as e:
            last_exc = e
            if attempt >= max_retries or not _is_retriable(e):
                # Wave 10.B.3 — if this call already burned the
                # degraded threshold of retries, mark the process.
                if consecutive_retries_this_call >= _DEGRADED_THRESHOLD_RETRIES:
                    _mark_degraded(
                        f"call exhausted {consecutive_retries_this_call} "
                        f"retries with {type(e).__name__}",
                    )
                raise
            # Sleep with jitter to avoid synchronised retry storms.
            delay = _BACKOFF_BASE_SECONDS * (2 ** attempt)
            delay += random.uniform(0, delay * 0.5)
            logger.warning(
                "anthropic_provider: transient error %s, retry %d/%d in %.2fs",
                type(e).__name__, attempt + 1, max_retries, delay,
            )
            consecutive_retries_this_call += 1
            await asyncio.sleep(delay)
    # Should be unreachable thanks to the `raise` inside the loop
    if last_exc is not None:
        raise last_exc
    raise LLMUnavailableError("anthropic_provider: retry loop exhausted unexpectedly")


# ── Wave 3.3: Anthropic prompt caching ───────────────────────────────────────
# Anthropic supports an "ephemeral" cache type on parts of the prompt.
# When the same prefix is reused across requests, the server reads it
# from the cache and bills cache_read tokens at 10% of normal input
# pricing. With AFianco's ~5k-token system prompt rebroadcast every
# round (4-5 rounds per chat), prompt caching saves ~60% on input
# tokens. Output tokens are unaffected.
#
# We wrap the system prompt in the cache_control marker. The Anthropic
# API accepts either a string or a list of TextBlockParam for "system";
# we use the list form when caching is enabled so the cache_control
# flag rides on the block. Smaller prompts (under the minimum cacheable
# size) silently skip caching, so we can enable unconditionally.

_PROMPT_CACHE_ENABLED = os.environ.get("LLM_PROMPT_CACHE", "1") != "0"


def _system_with_cache(system: Any) -> Any:
    """Wrap the system prompt in Anthropic's cache_control structure.

    Accepts two input shapes (Wave 10.B.1):

      1. **string** (legacy) — wraps as a single ephemeral cached block.

      2. **list of dicts** — pass-through. The caller has already split
         the prompt into stable (cached) + dynamic (fresh) blocks and
         pre-marked the cacheable ones. We honour their decisions.
         Example:
             [
               {"type":"text","text":"<stable>","cache_control":{"type":"ephemeral"}},
               {"type":"text","text":"<dynamic>"}
             ]

    When ``LLM_PROMPT_CACHE=0`` (env override):
      - string input is returned unchanged
      - list input has its ``cache_control`` markers stripped so the
        request stays well-formed but bypasses caching entirely.
    """
    if isinstance(system, list):
        if not _PROMPT_CACHE_ENABLED:
            return [
                {k: v for k, v in block.items() if k != "cache_control"}
                for block in system
            ]
        return system
    # String (legacy) path
    if not _PROMPT_CACHE_ENABLED:
        return system
    return [{
        "type": "text",
        "text": system,
        "cache_control": {"type": "ephemeral"},
    }]


# ── Tool-result compaction (token optimisation) ─────────────────────────────
# Pre-Wave-2 these lived in claude_client.py as module-level constants. They
# stay co-located with the provider because the compaction rules depend on
# what the model emits (Anthropic-specific tool_result block format).

_VERBOSE_KEYS = {"by_date", "daily_series", "by_day", "daily_breakdown"}
_SUMMARY_KEYS = {"total", "pnl", "net_result", "summary", "has_data"}


def _compact_tool_result(result: Any, _depth: int = 0) -> Any:
    """Compact a tool result dict to save tokens.

    Rules:
        - Remove by_date/daily_series arrays when a summary/total exists
          (the AI has the aggregate, the per-day breakdown is redundant
          most of the time)
        - Cap arrays > 15 items to top 10 + count note
        - Strip None values
        - Add _compacted flag when modifications occur

    Typically saves 40-60% of tokens on large tool results.
    """
    if not isinstance(result, dict):
        return result
    if _depth > 5:
        return result

    compacted: Dict[str, Any] = {}
    did_compact = False
    has_summary = bool(_SUMMARY_KEYS & set(result.keys()))

    for key, value in result.items():
        if value is None:
            continue
        if has_summary and key in _VERBOSE_KEYS and isinstance(value, (list, dict)):
            did_compact = True
            if isinstance(value, list) and len(value) > 0:
                compacted[f"_{key}_count"] = len(value)
            continue
        if isinstance(value, list) and len(value) > 15:
            compacted[key] = value[:10]
            compacted[f"_{key}_note"] = f"{len(value)} totali, mostrati top 10"
            did_compact = True
        elif isinstance(value, dict):
            compacted[key] = _compact_tool_result(value, _depth + 1)
        elif isinstance(value, list):
            compacted[key] = [
                _compact_tool_result(item, _depth + 1) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            compacted[key] = value

    if did_compact:
        compacted["_compacted"] = True

    return compacted


# ── The provider class ──────────────────────────────────────────────────────


class AnthropicProvider(LLMProvider):
    """Anthropic / Claude implementation of LLMProvider.

    Lazy SDK init: the anthropic.AsyncAnthropic client is created on
    first use and cached on the instance. is_available() returns False
    cleanly when ANTHROPIC_API_KEY isn't set or the anthropic package
    isn't installed — callers raise a clean 503 instead of crashing.

    Threading: AsyncAnthropic is safe to share across coroutines. We
    construct one client per provider instance and reuse it.
    """

    def __init__(self):
        self._client = None
        self._available: Optional[bool] = None  # tri-state: None / True / False

    # ── Identity ──────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        # Honour env override if set — lets the system_admin upgrade the
        # model (e.g. claude-opus-4) without a redeploy. Wave 4 will
        # also let individual agents specify their own model.
        return os.environ.get("CLAUDE_MODEL", _DEFAULT_MODEL)

    # ── Availability ──────────────────────────────────────────────────────

    def _get_client(self):
        """Lazy-init the AsyncAnthropic client. Returns None on failure."""
        if self._client is not None:
            return self._client
        try:
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                self._available = False
                logger.warning("anthropic_provider: ANTHROPIC_API_KEY not set")
                return None
            self._client = anthropic.AsyncAnthropic(
                api_key=api_key,
                timeout=_TIMEOUT_SECONDS,
            )
            self._available = True
            return self._client
        except ImportError:
            self._available = False
            logger.warning("anthropic_provider: anthropic package not installed")
            return None

    def is_available(self) -> bool:
        if self._available is None:
            self._get_client()
        return bool(self._available)

    # ── Internal: gated call ─────────────────────────────────────────────
    # Composes (in order): circuit breaker → semaphore → retry → SDK call.
    # Order matters: the breaker fail-fasts BEFORE we wait on the semaphore,
    # so a degraded provider doesn't fill our backpressure queue.

    async def _gated_call(self, fn):
        """Run an async SDK call through breaker + semaphore + retry."""
        breaker = get_breaker(self.name)

        async def _inside_breaker():
            async with _get_semaphore():
                return await _retry_with_backoff(fn)

        return await breaker.call(_inside_breaker)

    # ── Tool format conversion ────────────────────────────────────────────

    def format_tools(self, definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert AFianco tool definitions to Anthropic's input_schema format.

        Supports two input shapes:
            A) Flat (legacy): {"name", "description",
                              "parameters": {param_name: {type, description}}, "required": [...]}
            B) JSON Schema:   {"name", "description",
                              "parameters": {"type": "object",
                                             "properties": {...},
                                             "required": [...]}}

        Output (per tool):
            {"name", "description",
             "input_schema": {"type": "object",
                              "properties": {...},
                              "required": [...]}}
        """
        anthropic_tools = []
        for tool in definitions:
            params = tool.get("parameters", {})
            if params.get("type") == "object" and "properties" in params:
                # JSON Schema -> input_schema directly
                input_schema = {
                    "type": "object",
                    "properties": params["properties"],
                    "required": params.get("required", tool.get("required", [])),
                }
            else:
                # Flat -> convert to JSON Schema
                properties: Dict[str, Any] = {}
                for param_name, param_def in params.items():
                    if isinstance(param_def, dict):
                        properties[param_name] = {
                            "type": param_def.get("type", "string"),
                            "description": param_def.get("description", ""),
                        }
                input_schema = {
                    "type": "object",
                    "properties": properties,
                    "required": tool.get("required", []),
                }
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": input_schema,
            })
        return anthropic_tools

    # ── Single-shot send ─────────────────────────────────────────────────

    async def send_message(
        self,
        system: str,
        user_message: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        model_version: Optional[str] = None,
    ) -> str:
        client = self._get_client()
        if client is None:
            raise LLMUnavailableError("Anthropic API not configured")
        model = model_version or self.default_model

        async def _do_call():
            return await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=_system_with_cache(system),
                messages=[{"role": "user", "content": user_message}],
                temperature=temperature,
            )

        try:
            response = await self._gated_call(_do_call)
            if hasattr(response, "usage"):
                # Anthropic returns cache_read_input_tokens when caching
                # hits — log it so we can verify the optimisation works.
                cr = getattr(response.usage, "cache_read_input_tokens", 0)
                logger.debug(
                    "anthropic_provider: send_message %d in + %d out + %d cache_read tokens",
                    response.usage.input_tokens, response.usage.output_tokens, cr,
                )
            return response.content[0].text
        except Exception as e:
            logger.error("anthropic_provider: send_message failed after retries: %s", e, exc_info=True)
            # Track O Step 3.2 — capture per [P1] 500 spike alert. Final fail
            # post-retry e' indicatore di Anthropic outage OR key invalid OR
            # rate limit at provider side → operatore deve sapere.
            try:
                from core.observability.sentry import capture_with_tags
                capture_with_tags(
                    e,
                    action="ai_complete",
                    surface="api",
                    extra={"method": "send_message", "stage": "post_retry"},
                )
            except Exception:
                pass
            raise LLMUnavailableError(f"Anthropic API error: {e}") from e

    async def send_message_with_usage(
        self,
        system,
        user_message: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        model_version: Optional[str] = None,
    ) -> Tuple[str, Dict[str, int]]:
        """Wave 8A.0 — same as send_message but surfaces token usage.

        Returns (text, usage_dict) so callers can record an AIUsageEvent
        with cost_usd. Without this, digests / health-explanation /
        insights were SHIPPING but NOT TRACKED — the principal source
        of the un-attributed Anthropic spend pre-Wave 8.

        Wave 10.B.6: ``usage`` now also carries ``latency_ms`` measured
        around the actual SDK call (post-breaker, post-semaphore, post-
        retry). Callers can pass it to ``record_usage`` so the
        governance dashboard can surface a real "AI call latency" KPI.
        """
        import time as _time10b6
        client = self._get_client()
        if client is None:
            raise LLMUnavailableError("Anthropic API not configured")
        model = model_version or self.default_model

        async def _do_call():
            return await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=_system_with_cache(system),
                messages=[{"role": "user", "content": user_message}],
                temperature=temperature,
            )

        _t0 = _time10b6.monotonic()
        try:
            response = await self._gated_call(_do_call)
            _elapsed_ms = int((_time10b6.monotonic() - _t0) * 1000)
            usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
                "latency_ms": _elapsed_ms,
            }
            if hasattr(response, "usage"):
                usage["input_tokens"] = int(getattr(response.usage, "input_tokens", 0) or 0)
                usage["output_tokens"] = int(getattr(response.usage, "output_tokens", 0) or 0)
                usage["cache_read_tokens"] = int(getattr(response.usage, "cache_read_input_tokens", 0) or 0)
                usage["cache_creation_tokens"] = int(getattr(response.usage, "cache_creation_input_tokens", 0) or 0)
                logger.debug(
                    "anthropic_provider: send_message_with_usage %d in + %d out + %d cache_read + %d cache_create tokens in %dms",
                    usage["input_tokens"], usage["output_tokens"],
                    usage["cache_read_tokens"], usage["cache_creation_tokens"],
                    _elapsed_ms,
                )
            return response.content[0].text, usage
        except Exception as e:
            logger.error(
                "anthropic_provider: send_message_with_usage failed after retries: %s",
                e, exc_info=True,
            )
            # Track O Step 3.2 — capture per [P1] 500 spike alert.
            try:
                from core.observability.sentry import capture_with_tags
                capture_with_tags(
                    e,
                    action="ai_complete",
                    surface="api",
                    extra={"method": "send_message_with_usage", "stage": "post_retry"},
                )
            except Exception:
                pass
            raise LLMUnavailableError(f"Anthropic API error: {e}") from e

    # ── Multi-turn send (no tools) ───────────────────────────────────────

    async def send_messages(
        self,
        system: str,
        messages: List[dict],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        model_version: Optional[str] = None,
    ) -> str:
        client = self._get_client()
        if client is None:
            raise LLMUnavailableError("Anthropic API not configured")
        model = model_version or self.default_model

        async def _do_call():
            return await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=_system_with_cache(system),
                messages=messages,
                temperature=temperature,
            )

        try:
            response = await self._gated_call(_do_call)
            return response.content[0].text
        except Exception as e:
            logger.error("anthropic_provider: send_messages failed after retries: %s", e, exc_info=True)
            raise LLMUnavailableError(f"Anthropic API error: {e}") from e

    # ── Agentic send (multi-turn + tool use) ─────────────────────────────

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
        client = self._get_client()
        if client is None:
            raise LLMUnavailableError("Anthropic API not configured")

        working_messages = list(messages)
        total_input = 0
        total_output = 0
        model = model_version or self.default_model

        # Wave 10.A.5 — agentic loop convergence guards.
        # Two cost-explosion vectors closed:
        #
        # 1. Same (tool_name, input) called twice in a row → the model is
        #    looping on a tool that's not giving it what it needs. Force
        #    end_turn instead of paying for round 3, 4, 5.
        #
        # 2. The model emits N parallel tool_use blocks in a single round.
        #    Each one's result is fed back in the next round, multiplying
        #    input tokens by N. Cap at _MAX_TOOL_USES_PER_ROUND (default 5);
        #    excess blocks return a marker so the model knows to refine.
        #
        # Forensic evidence: pre-Wave 9.A.3 a single chat hit $0.10 (33k
        # tokens) via runaway tool iteration. Wave 9.A.3 capped tool result
        # *size*. Wave 10.A.5 caps tool *iteration* — the second valve.
        import json as _json10a
        import hashlib as _hashlib10a
        _MAX_TOOL_USES_PER_ROUND = int(os.environ.get("LLM_MAX_TOOL_USES_PER_ROUND", "5"))
        _last_tool_signature: Optional[str] = None

        import time as _time10b6
        cached_system = _system_with_cache(system)
        for round_num in range(max_rounds):
            async def _do_call():
                return await client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=cached_system,
                    messages=working_messages,
                    tools=tools,
                    temperature=temperature,
                )

            _t0_round = _time10b6.monotonic()
            try:
                response = await self._gated_call(_do_call)
                _round_elapsed_ms = int((_time10b6.monotonic() - _t0_round) * 1000)
                round_usage = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read_tokens": 0,
                    "cache_creation_tokens": 0,
                    "latency_ms": _round_elapsed_ms,
                }
                if hasattr(response, "usage"):
                    round_usage["input_tokens"] = int(response.usage.input_tokens or 0)
                    round_usage["output_tokens"] = int(response.usage.output_tokens or 0)
                    round_usage["cache_read_tokens"] = int(
                        getattr(response.usage, "cache_read_input_tokens", 0) or 0
                    )
                    round_usage["cache_creation_tokens"] = int(
                        getattr(response.usage, "cache_creation_input_tokens", 0) or 0
                    )
                    total_input += round_usage["input_tokens"]
                    total_output += round_usage["output_tokens"]
                    logger.debug(
                        "anthropic_provider: round=%d %d in + %d out + %d cache_read + %d cache_write in %dms",
                        round_num,
                        round_usage["input_tokens"], round_usage["output_tokens"],
                        round_usage["cache_read_tokens"], round_usage["cache_creation_tokens"],
                        _round_elapsed_ms,
                    )
                # Wave 8A.2 — fire the per-round callback. Never let a
                # tracking exception kill the chat: catch and log.
                if on_round is not None:
                    try:
                        await on_round(round_num, round_usage)
                    except Exception as cb_exc:
                        logger.warning(
                            "anthropic_provider: on_round callback failed for round=%d: %s",
                            round_num, cb_exc,
                        )
            except Exception as e:
                logger.error(
                    "anthropic_provider: send_messages_with_tools failed after retries (round %d): %s",
                    round_num, e, exc_info=True,
                )
                raise LLMUnavailableError(f"Anthropic API error: {e}") from e

            # Re-emit the assistant content (text + tool_use blocks) into history.
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
            working_messages.append({"role": "assistant", "content": assistant_content})
            usage = {"input_tokens": total_input, "output_tokens": total_output}

            # End of generation?
            if response.stop_reason == "end_turn":
                final = ""
                for block in response.content:
                    if block.type == "text":
                        final += block.text
                logger.info(
                    "anthropic_provider: total tokens: %d in + %d out",
                    total_input, total_output,
                )
                return final, working_messages, usage

            # Tool execution?
            if response.stop_reason == "tool_use":
                # Wave 10.A.5 — collect tool_use blocks first so we can
                # apply the per-round cap before executing.
                pending_uses = [b for b in response.content if b.type == "tool_use"]
                if len(pending_uses) > _MAX_TOOL_USES_PER_ROUND:
                    logger.warning(
                        "anthropic_provider: round=%d emitted %d tool_use blocks "
                        "(cap=%d). Executing first %d; rest get a 'capped' marker.",
                        round_num, len(pending_uses),
                        _MAX_TOOL_USES_PER_ROUND, _MAX_TOOL_USES_PER_ROUND,
                    )

                # Wave 10.A.5 — same-tool-twice detection. Hash all the
                # tool_use signatures in this round. If a SINGLE-use round
                # repeats the previous round's signature, force end_turn.
                # We only apply this when the round has exactly 1 tool_use
                # (multi-tool rounds tend to be legitimately exploratory).
                this_round_signature: Optional[str] = None
                if len(pending_uses) == 1:
                    try:
                        sig_payload = _json10a.dumps(
                            {"name": pending_uses[0].name,
                             "input": pending_uses[0].input},
                            sort_keys=True, ensure_ascii=False, default=str,
                        )
                        this_round_signature = _hashlib10a.sha256(
                            sig_payload.encode("utf-8"),
                        ).hexdigest()
                    except Exception:
                        this_round_signature = None

                if (this_round_signature is not None
                        and _last_tool_signature == this_round_signature):
                    logger.warning(
                        "anthropic_provider: round=%d repeated the same "
                        "(tool_name, input) signature as round=%d — forcing "
                        "end_turn to prevent agentic loop runaway.",
                        round_num, round_num - 1,
                    )
                    # Append a synthetic tool_result that tells the model
                    # to stop and produce a final answer based on what it
                    # already has. The model's NEXT response will be
                    # end_turn because there are no new tool_uses pending.
                    tool_results = []
                    for block in pending_uses:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": _json10a.dumps({
                                "_capped_by": "wave10a5_same_tool_twice",
                                "_hint": (
                                    "You called this same tool with the same "
                                    "arguments twice in a row. The data isn't "
                                    "changing. Produce your final answer based "
                                    "on the previous round's result, or ask the "
                                    "user to refine the question."
                                ),
                            }, ensure_ascii=False),
                            "is_error": True,
                        })
                    working_messages.append({"role": "user", "content": tool_results})
                    _last_tool_signature = this_round_signature
                    continue

                _last_tool_signature = this_round_signature

                tool_results = []
                for idx, block in enumerate(pending_uses):
                    if idx >= _MAX_TOOL_USES_PER_ROUND:
                        # Wave 10.A.5 — over-cap blocks get a marker. The
                        # model sees the marker on the next round and can
                        # decide what to do (typically: pick a subset and
                        # retry). We still attach a tool_result for each
                        # tool_use_id (Anthropic requires this) so the
                        # protocol stays well-formed.
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": _json10a.dumps({
                                "_capped_by": "wave10a5_max_tool_uses_per_round",
                                "_cap": _MAX_TOOL_USES_PER_ROUND,
                                "_hint": (
                                    f"This round emitted {len(pending_uses)} parallel "
                                    f"tool calls; only the first {_MAX_TOOL_USES_PER_ROUND} "
                                    f"were executed. Pick the most relevant ones."
                                ),
                            }, ensure_ascii=False),
                            "is_error": True,
                        })
                        continue
                    logger.info(
                        "anthropic_provider: tool_use round=%d name=%s",
                        round_num, block.name,
                    )
                    try:
                        result = await on_tool_call(block.name, block.input)
                        compacted = _compact_tool_result(result)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(
                                compacted, ensure_ascii=False, default=str,
                            ),
                        })
                    except Exception as e:
                        logger.error(
                            "anthropic_provider: tool execution failed: %s — %s",
                            block.name, e,
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": str(e)}, ensure_ascii=False),
                            "is_error": True,
                        })
                working_messages.append({"role": "user", "content": tool_results})
                continue

            # Unexpected stop reason — return whatever text we have.
            logger.warning(
                "anthropic_provider: unexpected stop_reason=%s", response.stop_reason,
            )
            final = ""
            for block in response.content:
                if block.type == "text":
                    final += block.text
            return (
                final or "Mi dispiace, non sono riuscito a completare l'analisi.",
                working_messages,
                usage,
            )

        # Max rounds exceeded.
        logger.warning("anthropic_provider: max_rounds (%d) exceeded", max_rounds)
        final = ""
        for block in response.content:
            if block.type == "text":
                final += block.text
        return (
            final or "Mi dispiace, l'analisi ha richiesto troppi passaggi.",
            working_messages,
            {"input_tokens": total_input, "output_tokens": total_output},
        )

    # ── Cost calculation ─────────────────────────────────────────────────

    def calculate_cost_usd(
        self,
        model_version: str,
        tokens_prompt: Optional[int],
        tokens_completion: Optional[int],
        *,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> Optional[float]:
        # Centralised pricing lives in ai_cost_calculator so it can be
        # updated independently of provider logic — Anthropic adjusts
        # pricing more often than they change the API surface.
        from services.ai_cost_calculator import compute_cost_usd
        return compute_cost_usd(
            provider=self.name,
            model_version=model_version,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            cache_read_tokens=cache_read_tokens,
            cache_creation_tokens=cache_creation_tokens,
        )

    # ── Streaming (Wave 3.4) ─────────────────────────────────────────────

    async def stream_messages(
        self,
        system: str,
        messages: List[dict],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        model_version: Optional[str] = None,
    ):
        """Stream text chunks from Anthropic.

        Uses the AsyncAnthropic streaming API (.messages.stream()). Yields
        plain str chunks of the text delta as soon as the server emits
        them. Aborts cleanly if the client disconnects.

        Streaming intentionally does NOT compose with retry/breaker/
        semaphore — they protect non-streaming bursty traffic; the
        streaming path is opt-in for chat UX and used with smaller
        concurrency. If we later want them, we'll wrap the outer
        ``async for`` in the same _gated_call pattern.

        Caveat: this path bypasses tool use (Anthropic streams text only
        when the model decides not to use tools). For tool-using chats
        callers should keep using send_messages_with_tools.
        """
        client = self._get_client()
        if client is None:
            raise LLMUnavailableError("Anthropic API not configured")
        model = model_version or self.default_model

        try:
            async with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=_system_with_cache(system),
                messages=messages,
                temperature=temperature,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error("anthropic_provider: stream_messages failed: %s", e, exc_info=True)
            raise LLMUnavailableError(f"Anthropic streaming error: {e}") from e
