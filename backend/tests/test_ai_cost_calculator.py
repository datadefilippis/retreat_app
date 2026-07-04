"""Unit tests for services.ai_cost_calculator.

Pure functions, no DB / no I/O — fast.

Acceptance gate for Wave 1.4: every public function deterministic for
the inputs in this file.
"""
import pytest
from services.ai_cost_calculator import compute_cost_usd, get_pricing


# ── get_pricing ─────────────────────────────────────────────────────────────


def test_get_pricing_known_sonnet():
    p = get_pricing("anthropic", "claude-sonnet-4-20250514")
    assert p is not None
    assert p["input_usd_per_1m"] == 3.00
    assert p["output_usd_per_1m"] == 15.00


def test_get_pricing_known_opus():
    p = get_pricing("anthropic", "claude-opus-4-20250514")
    assert p["input_usd_per_1m"] == 15.00
    assert p["output_usd_per_1m"] == 75.00


def test_get_pricing_unknown_model_falls_back_to_provider_default():
    # An unknown sonnet variant should resolve to the configured default
    # (today: claude-sonnet-4-20250514).
    p = get_pricing("anthropic", "claude-sonnet-5-NEW")
    assert p is not None
    assert p["input_usd_per_1m"] == 3.00  # sonnet-4 fallback


def test_get_pricing_unknown_provider_returns_none():
    assert get_pricing("openai", "gpt-4") is None


def test_get_pricing_empty_provider_returns_none():
    assert get_pricing("", "claude-sonnet-4-20250514") is None


# ── compute_cost_usd ────────────────────────────────────────────────────────


def test_compute_cost_simple_sonnet():
    # 1000 input + 500 output tokens on Sonnet 4
    # input  : 1000  * 3.00  / 1M = 0.003
    # output : 500   * 15.00 / 1M = 0.0075
    # total  : 0.0105
    cost = compute_cost_usd("anthropic", "claude-sonnet-4-20250514", 1000, 500)
    assert cost == 0.0105


def test_compute_cost_sonnet_realistic_chat():
    # Realistic AFianco chat: ~4500 input, ~600 output, NO cache
    # input  : 4500 * 3.00  / 1M = 0.0135
    # output : 600  * 15.00 / 1M = 0.009
    # total  : 0.0225 USD per chat
    cost = compute_cost_usd("anthropic", "claude-sonnet-4-20250514", 4500, 600)
    assert cost == 0.0225


def test_compute_cost_with_cache_read():
    # Wave 8E.2: Anthropic returns DISJOINT token counts —
    #   tokens_prompt           = NEW (uncached) input tokens
    #   cache_read_tokens       = served-from-cache tokens (10% rate)
    #   cache_creation_tokens   = written-to-cache tokens (125% rate)
    # A realistic Anthropic response when prompt cache hits:
    #   input_tokens=500, cache_read_input_tokens=4000, output=600
    # Pricing:
    #   500   * 3.00  / 1M = 0.0015
    #   4000  * 0.30  / 1M = 0.0012
    #   600   * 15.00 / 1M = 0.009
    # Total: 0.0117  (vs 0.0135 + 0.009 = 0.0225 with no cache → 48% saving)
    cost = compute_cost_usd(
        "anthropic", "claude-sonnet-4-20250514",
        tokens_prompt=500, tokens_completion=600,
        cache_read_tokens=4000,
    )
    assert cost == 0.0117


def test_compute_cost_with_cache_creation():
    """Wave 8E.2 — cache_creation tokens cost 1.25× input."""
    # 1000 new input + 2000 being written to cache + 500 output:
    #   1000 * 3.00  / 1M = 0.003
    #   2000 * 3.75  / 1M = 0.0075
    #    500 * 15.00 / 1M = 0.0075
    # Total: 0.018
    cost = compute_cost_usd(
        "anthropic", "claude-sonnet-4-20250514",
        tokens_prompt=1000, tokens_completion=500,
        cache_creation_tokens=2000,
    )
    assert cost == 0.018


def test_compute_cost_all_four_streams_disjoint():
    """All four token streams sum independently (no subtraction)."""
    # Realistic chat with first-time cache creation:
    #   input=300, output=200, cache_read=0, cache_create=4500
    #   300  * 3.00  / 1M = 0.0009
    #   200  * 15.00 / 1M = 0.003
    #   4500 * 3.75  / 1M = 0.016875
    # Total: 0.020775
    cost = compute_cost_usd(
        "anthropic", "claude-sonnet-4-20250514",
        tokens_prompt=300, tokens_completion=200,
        cache_read_tokens=0, cache_creation_tokens=4500,
    )
    assert cost == 0.020775


def test_compute_cost_no_longer_subtracts_cache_read_from_prompt():
    """Wave 8E.2 regression guard: the old buggy formula subtracted
    cache_read from tokens_prompt. New formula treats them as disjoint.
    """
    # If old buggy formula:
    #   max(1000 - 500, 0) * 3 + 500 * 0.30 + 0 * 15 = 0.0015 + 0.00015 = 0.00165
    # New correct formula:
    #   1000 * 3 / 1M + 500 * 0.30 / 1M = 0.003 + 0.00015 = 0.00315
    cost = compute_cost_usd(
        "anthropic", "claude-sonnet-4-20250514",
        tokens_prompt=1000, tokens_completion=0,
        cache_read_tokens=500,
    )
    assert cost == 0.00315
    # If the test ever produces 0.00165, the buggy subtraction is back.


def test_compute_cost_opus_4x_more_expensive():
    cost_sonnet = compute_cost_usd("anthropic", "claude-sonnet-4-20250514", 1000, 500)
    cost_opus = compute_cost_usd("anthropic", "claude-opus-4-20250514", 1000, 500)
    # Opus input is 5x, output is 5x of sonnet → total cost ~5x
    assert cost_opus > cost_sonnet * 4
    assert cost_opus < cost_sonnet * 6


def test_compute_cost_unknown_provider_returns_none():
    assert compute_cost_usd("xai", "grok-1", 1000, 500) is None


def test_compute_cost_zero_tokens():
    cost = compute_cost_usd("anthropic", "claude-sonnet-4-20250514", 0, 0)
    assert cost == 0


def test_compute_cost_none_tokens_treated_as_zero():
    cost = compute_cost_usd("anthropic", "claude-sonnet-4-20250514", None, None)
    assert cost == 0


def test_compute_cost_negative_tokens_treated_as_zero():
    # Defensive: negative input should not produce negative cost
    cost = compute_cost_usd("anthropic", "claude-sonnet-4-20250514", -100, -50)
    assert cost == 0


def test_compute_cost_cache_read_can_exceed_prompt():
    """Wave 8E.2: cache_read can exceed tokens_prompt without weird math.

    Old (buggy) clamp: max(1000-2000, 0) = 0 → uninformative.
    New (correct): the two streams are disjoint, each billed independently.
    """
    # input  : 1000 * 3.00  / 1M = 0.003
    # cache  : 2000 * 0.30  / 1M = 0.0006
    # output : 500  * 15.00 / 1M = 0.0075
    # total  : 0.0111
    cost = compute_cost_usd(
        "anthropic", "claude-sonnet-4-20250514",
        tokens_prompt=1000, tokens_completion=500,
        cache_read_tokens=2000,
    )
    assert cost == 0.0111


def test_compute_cost_precision_six_decimals():
    # Verify the rounding is at 6 decimals (sub-cent)
    cost = compute_cost_usd("anthropic", "claude-sonnet-4-20250514", 1, 1)
    # 1 * 3.00 / 1M + 1 * 15.00 / 1M = 0.0000180
    # Rounded to 6 decimals: 0.000018
    assert cost == 0.000018
