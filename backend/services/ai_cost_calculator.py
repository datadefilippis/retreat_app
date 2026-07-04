"""
AI cost calculator — centralised pricing logic for every LLM provider.

Single source of truth for converting token usage into USD cost.
Storage of usage events records `cost_usd` (the provider's billing
currency); the admin dashboard converts to the org's display currency
at read time via ``services.currency_service.get_currency_for_org``.

Why this module exists
----------------------
Pricing for the same model changes over time. Hardcoding pricing
inline at every record_usage call site would mean a coordinated edit
across many files every time Anthropic (or any future provider)
adjusts rates. Instead, every caller passes the raw token counts +
model_version + provider, and the cost is resolved exactly here. When
pricing changes, ONE constant gets updated.

Resolution order
----------------
1. Lookup ``(provider, model_version)`` in ``_PRICING_TABLE``.
2. If exact model not found, fall back to provider's default tier
   (e.g. unknown Anthropic Sonnet variant → uses sonnet-4 pricing).
3. If provider not found at all → return None (caller logs warning,
   stores cost_usd=None — the tokens stay recorded, so retroactive
   computation remains possible).

Cache reads + cache creation (Wave 3 + Wave 8E.2 bugfix)
--------------------------------------------------------
Anthropic prompt caching returns THREE DISJOINT token counts in
``response.usage``:

  ``input_tokens``                   tokens NOT in cache (priced at full input rate)
  ``cache_read_input_tokens``        tokens READ from cache  (priced at 10% of input)
  ``cache_creation_input_tokens``    tokens WRITTEN to cache (priced at 125% of input)

Total billable input = input_tokens + cache_read + cache_creation. The
three are NEVER added to each other — Anthropic returns them as
separate buckets.

Pre-Wave-8E.2 bug: the calculator used to subtract cache_read from
tokens_prompt (treating them as if they were the same pool). This
under-billed by up to 20% on cache-heavy chats. Also, cache_creation
was silently ignored. Fixed Wave 8E.2 (this revision).

Public API
----------
    compute_cost_usd(
        provider, model_version, tokens_prompt, tokens_completion,
        *, cache_read_tokens=0, cache_creation_tokens=0,
    ) -> Optional[float]

    get_pricing(provider, model_version) -> Optional[dict]
        Returns the active price tuple for diagnostics.

Adding a new model
------------------
Add an entry to ``_PRICING_TABLE`` of the form:

    ("anthropic", "claude-haiku-4-20250514"): {
        "input_usd_per_1m":  0.80,
        "output_usd_per_1m": 4.00,
        "cache_read_usd_per_1m": 0.08,
    }

Tests in tests/test_ai_cost_calculator.py will catch typos in keys.
"""
from __future__ import annotations

from typing import Optional


# ── Pricing table ───────────────────────────────────────────────────────────
# Source: https://www.anthropic.com/pricing (verify before each pricing
# change). Cost is per 1 million tokens. cache_read is the discounted rate
# Anthropic applies when a request hits the ephemeral cache.
#
# We store USD because that's what Anthropic bills in. Conversion to EUR
# (or CHF, or anything else) happens at READ time in the admin dashboard.

_PRICING_TABLE: dict[tuple[str, str], dict[str, float]] = {
    # ── Anthropic Claude Sonnet 4.6 (the model AFianco uses today) ─────
    # Stessa tariffa di Sonnet 4 ($3 / $15 per 1M). Sonnet 4 è stato
    # ritirato (giu 2026); la voce sotto resta per il calcolo costi storico.
    ("anthropic", "claude-sonnet-4-6"): {
        "input_usd_per_1m":      3.00,
        "output_usd_per_1m":    15.00,
        "cache_read_usd_per_1m": 0.30,  # 10% of input
        "cache_write_usd_per_1m": 3.75, # 1.25x of input (5-min TTL)
    },
    # ── Anthropic Claude Sonnet 4 (ritirato — solo storico) ───────────
    ("anthropic", "claude-sonnet-4-20250514"): {
        "input_usd_per_1m":      3.00,
        "output_usd_per_1m":    15.00,
        "cache_read_usd_per_1m": 0.30,  # 10% of input
        "cache_write_usd_per_1m": 3.75, # 1.25x of input (5-min TTL)
    },
    # ── Anthropic Claude Opus 4 ────────────────────────────────────────
    ("anthropic", "claude-opus-4-20250514"): {
        "input_usd_per_1m":     15.00,
        "output_usd_per_1m":    75.00,
        "cache_read_usd_per_1m": 1.50,
        "cache_write_usd_per_1m": 18.75,
    },
    # ── Anthropic Claude Haiku 4 (cheap, fast) ────────────────────────
    ("anthropic", "claude-haiku-4-20250514"): {
        "input_usd_per_1m":      0.80,
        "output_usd_per_1m":     4.00,
        "cache_read_usd_per_1m": 0.08,
        "cache_write_usd_per_1m": 1.00,
    },
}

# Per-provider default pricing — used when an exact model_version isn't
# in the table (e.g. a new dated snapshot). Lets us gracefully degrade
# rather than skipping cost tracking entirely.
_PROVIDER_DEFAULTS: dict[str, tuple[str, str]] = {
    "anthropic": ("anthropic", "claude-sonnet-4-6"),
}


def get_pricing(provider: str, model_version: str) -> Optional[dict]:
    """Return the active pricing dict for (provider, model). None if unknown."""
    if not provider:
        return None
    key = (provider, model_version or "")
    pricing = _PRICING_TABLE.get(key)
    if pricing is not None:
        return pricing
    # Fallback to provider's default tier (e.g. unknown sonnet variant)
    default_key = _PROVIDER_DEFAULTS.get(provider)
    if default_key is None:
        return None
    return _PRICING_TABLE.get(default_key)


def compute_cost_usd(
    provider: str,
    model_version: str,
    tokens_prompt: Optional[int],
    tokens_completion: Optional[int],
    *,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> Optional[float]:
    """Convert token counts into USD cost.

    All four token streams are billed INDEPENDENTLY (Anthropic returns
    them as disjoint counts — see module docstring):

        cost = tokens_prompt         × input_usd_per_1m       (uncached)
             + tokens_completion     × output_usd_per_1m
             + cache_read_tokens     × cache_read_usd_per_1m  (10% of input)
             + cache_creation_tokens × cache_write_usd_per_1m (125% of input)

    Returns None when pricing for the provider/model can't be resolved —
    the caller should still record the event (with cost_usd=None) so the
    tokens remain available for retroactive computation.

    Defensive on bad inputs: negative or None token counts treated as 0.

    Wave 8E.2 bugfix: the previous implementation
      (a) subtracted cache_read from tokens_prompt (wrong: Anthropic
          returns these as disjoint counts, never overlapping)
      (b) ignored cache_creation_tokens entirely
    Together these under-billed cache-heavy chats by 15-25%. Both fixed
    here.
    """
    pricing = get_pricing(provider, model_version)
    if pricing is None:
        return None

    prompt = max(int(tokens_prompt or 0), 0)
    completion = max(int(tokens_completion or 0), 0)
    cache_read = max(int(cache_read_tokens or 0), 0)
    cache_create = max(int(cache_creation_tokens or 0), 0)

    input_cost = prompt * pricing["input_usd_per_1m"] / 1_000_000
    output_cost = completion * pricing["output_usd_per_1m"] / 1_000_000
    cache_read_cost = cache_read * pricing["cache_read_usd_per_1m"] / 1_000_000
    # cache_write_usd_per_1m may be absent on legacy pricing entries —
    # fall back to 1.25× input rate (Anthropic's documented multiplier).
    cache_write_rate = pricing.get(
        "cache_write_usd_per_1m",
        pricing["input_usd_per_1m"] * 1.25,
    )
    cache_create_cost = cache_create * cache_write_rate / 1_000_000

    total = input_cost + output_cost + cache_read_cost + cache_create_cost
    return round(total, 6)  # 6 decimals = sub-cent precision
