"""Canonical period-delta formulas — Wave 14.HOTFIX6 (F2).

Pre-HOTFIX6 the codebase had TWO separate delta implementations that
disagreed on edge cases:

  - ``modules.cashflow_monitor.ai_tools._delta_pct`` (used by
    ``query_period_comparison``)::

        if a == 0:
            return 0 if b == 0 else 100
        return round((b - a) / abs(a) * 100, 1)

  - ``modules.cashflow_monitor.overview_builder._yoy_pct`` (used by
    the YoY block of ``query_cashflow_summary``)::

        if previous > 0:
            return round((current - previous) / previous * 100, 1)
        return None

Same logical question ("how much did revenue change?") could return
different answers depending on which tool the model called:

  baseline   current   _delta_pct   _yoy_pct
  ─────────────────────────────────────────────
  100        130       +30          +30      ✓ agree
  0          100       100          None     ✗ disagree
  -100       50        +150         None     ✗ disagree (sign flip in
                                              _yoy_pct, abs() in _delta_pct)
  100        0         -100         -100     ✓ agree

This module provides ONE canonical function used by both call sites.
The convention is documented and stable:

  - delta_abs is ALWAYS (current - baseline). Sign is intuitive:
    positive = current grew, negative = current declined.
  - delta_pct is (current - baseline) / |baseline| * 100, signed.
    Returns None when baseline is zero (genuinely undefined) so callers
    can render "N/A" or skip rather than getting a fake 100% / 0%.
  - direction is one of: "up" / "down" / "stable" / "undefined".
    Threshold for "stable" is |delta_pct| < 0.5%.

The function returns a structured dict so callers get all signals in
one pass instead of having to compute them separately.

The Wave 14.HOTFIX5 ``_interpret_change`` in ai_tools.py still owns
the BUSINESS-MEANING labelling (CRESCITA / RIDUZIONE / PERDITA RIDOTTA
etc.) because that depends on the metric (revenue, expenses, net_result
each behave differently). ``compute_period_delta`` here is the
pure-math layer that ``_interpret_change`` builds on top of.
"""

from typing import Optional


# Threshold below which a delta is reported as "stable" — matches the
# Wave 14.HOTFIX4 _interpret_change threshold so the two layers agree.
_STABLE_THRESHOLD_PCT = 0.5


def compute_period_delta(baseline: float, current: float) -> dict:
    """Compute the canonical period delta between baseline and current.

    Convention:
      - baseline = older / reference period
      - current  = newer / compared period
      - delta is ALWAYS (current - baseline). Sign is intuitive.

    Returns a dict with keys:
        delta_abs        — float, always present
        delta_pct        — float (signed) or None when baseline == 0
        direction        — "up" | "down" | "stable" | "undefined"
        baseline_sign    — "positive" | "negative" | "zero"
        current_sign     — "positive" | "negative" | "zero"

    The float values are rounded to 2 decimal places (abs) and 1
    decimal place (pct) — matching the pre-HOTFIX6 rounding so
    callers that already format the output see no visual difference.
    """
    delta_abs = round(current - baseline, 2)
    baseline_sign = "zero" if baseline == 0 else (
        "positive" if baseline > 0 else "negative"
    )
    current_sign = "zero" if current == 0 else (
        "positive" if current > 0 else "negative"
    )

    if baseline == 0:
        # Genuinely undefined relative change. Callers should render
        # "N/A" or use the absolute delta instead.
        return {
            "delta_abs": delta_abs,
            "delta_pct": None,
            "direction": "undefined" if current != 0 else "stable",
            "baseline_sign": baseline_sign,
            "current_sign": current_sign,
        }

    # Standard signed percentage: (current - baseline) / |baseline|.
    # Using |baseline| in the denominator preserves the sign of the
    # numerator, which means positive pct always reflects "current
    # moved away from baseline in the up direction" — even when
    # baseline is negative (loss → smaller loss → positive pct).
    # The business-meaning interpretation (loss shrunk vs profit
    # grew vs revenue cresciuto) is the caller's responsibility
    # (e.g. _interpret_change in ai_tools.py).
    delta_pct = round((current - baseline) / abs(baseline) * 100, 1)

    if abs(delta_pct) < _STABLE_THRESHOLD_PCT:
        direction = "stable"
    elif delta_pct > 0:
        direction = "up"
    else:
        direction = "down"

    return {
        "delta_abs": delta_abs,
        "delta_pct": delta_pct,
        "direction": direction,
        "baseline_sign": baseline_sign,
        "current_sign": current_sign,
    }


def delta_pct_signed(baseline: float, current: float) -> Optional[float]:
    """Convenience accessor — return ONLY the signed delta_pct.

    Backward-compat shim for callers that used the old ``_delta_pct``
    or ``_yoy_pct`` and only need the percentage. Returns ``None``
    when baseline is 0 (was ``100`` / ``0`` in old _delta_pct,
    ``None`` in old _yoy_pct — None is the safer default).

    For full structured output prefer ``compute_period_delta``.
    """
    return compute_period_delta(baseline, current)["delta_pct"]
