"""
Statistical significance helpers for the alert engine (Pillar 2 — v14.2).

The point of this module
-----------------------
Cashflow rules used to call out anomalies by computing ``(curr - prev) / prev``
on two adjacent 30-day windows. That formula is mathematically correct but
business-blind: a bimonthly electricity bill of €48 (partial month) → €680
(full month) reads as "+1316% increase" and the merchant sees an alarming
email. The signal is real (one bill is larger than the other) but the
*conclusion* (cost is exploding) is wrong — the underlying frequency of the
expense changed, not the cost level.

The functions below give the rules the tools to distinguish those cases:

  • ``detect_payment_frequency`` infers whether a category pays monthly,
    bimonthly, quarterly, or annually — purely from its 12-month timeline.

  • ``rolling_window_baseline`` returns a (median, mad) tuple over a window;
    MAD = Median Absolute Deviation, robust to single outliers in a way that
    mean+stddev is not (a single huge outlier inflates stddev so much that
    it falls back under threshold — that's why we use MAD here too).

  • ``is_significant_anomaly`` is the single function rules call. It accepts
    several scoring methods (median_ratio | z_score | percentile) and
    returns a structured ``AnomalyOutcome`` with score + reason so the
    engine can log decisions uniformly.

Design constraints
------------------
- **Pure**: no DB, no I/O, no datetime.now(). Inputs are dicts and lists.
  Every function is deterministic and unit-testable in isolation.
- **Robust by default**: median-based methods (not mean+stddev) so a single
  outlier in the input history doesn't dominate the baseline.
- **Honest about uncertainty**: when the history is too short for a
  meaningful signal (``len(history) < min_history``), the function returns
  ``allowed=False reason='insufficient_history'`` instead of guessing.
- **Forward-compatible**: adding a new scoring method tomorrow means a new
  branch in ``is_significant_anomaly``, with no impact on call sites that
  use the existing methods.

How rules should use it (the typical shape)
-------------------------------------------
    history_amounts = _category_non_zero_values_last_12mo(ctx, category)
    outcome = is_significant_anomaly(
        current_value=curr_amount,
        history=history_amounts,
        method="median_ratio",
        min_history=4,
        threshold=2.5,
    )
    if not outcome.is_anomaly:
        return []  # silenced — not statistically meaningful

The rule body then formats the alert using ``outcome.score`` (the ratio
or z-score) for the human-readable summary and ``outcome.label`` for the
suggested action.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple


# ── Payment frequency detection ─────────────────────────────────────────────

# Tags returned by detect_payment_frequency. "irregular" covers truly random
# patterns; the engine treats those with extra scepticism (raises min_history).
PaymentFrequency = Literal["monthly", "bimonthly", "quarterly", "annual", "irregular", "unknown"]


def detect_payment_frequency(
    monthly_amounts_last_12mo: List[float],
) -> PaymentFrequency:
    """Infer a category's payment cadence from its last 12 monthly totals.

    Input shape:
        ``monthly_amounts_last_12mo`` is a list of 12 floats, ordered
        chronologically (index 0 = oldest, index 11 = newest). Months
        without payment are passed as 0.0 — they are the signal.

    Algorithm:
        Count non-zero months. The ratio of paid months / 12 maps to a
        canonical frequency. We intentionally use a coarse mapping (a few
        buckets) instead of returning a continuous "every N months" — the
        downstream rules only need to know whether to compare values from
        the SAME bucket position (e.g. "this Q3 vs last Q3").

    Returns "unknown" when the list is empty or shorter than 6 months — too
    little data to claim anything about cadence.

    Edge cases:
      - 12 months / 12 paid → monthly (or "continuous")
      - 6 months / 12 paid → likely bimonthly
      - 4 months / 12 paid → likely quarterly
      - 1-2 months / 12 paid → likely annual
      - 3, 5 months / 12 paid → irregular (the rule should be more cautious)

    The thresholds were picked from a small sample of real PMI data
    (electricity, water, accounting fees, insurance, software subs). They
    err on the side of "irregular" when the pattern is ambiguous, which
    pushes the rule into a more conservative mode for those categories.
    """
    if not monthly_amounts_last_12mo or len(monthly_amounts_last_12mo) < 6:
        return "unknown"

    non_zero = sum(1 for x in monthly_amounts_last_12mo if x > 0)
    total_months = len(monthly_amounts_last_12mo)

    # Continuous payments — at least 75% of months had a payment.
    if non_zero >= int(total_months * 0.75):
        return "monthly"
    # Quarterly comes BEFORE bimonthly in the cascade: 4/12 maps cleanly
    # to "once a quarter", and we want it labelled that way before the
    # bimonthly range catches it. A merchant paying quarterly typically
    # has exactly 4 non-zero months; some flexibility (3) covers cases
    # where they skipped a payment.
    if non_zero in (3, 4):
        return "quarterly"
    # ~Every other month: 5-7 months out of 12. We exclude 4 (handled
    # above) and 8 (which would be ~67% and reads more like "monthly
    # with occasional skips"; we fall to "irregular" for it).
    if non_zero in (5, 6, 7):
        return "bimonthly"
    # Once or twice a year
    if non_zero in (1, 2):
        return "annual"
    # Anything else — typically 0 (skipped earlier) or weird 8/12.
    return "irregular"


# ── Rolling baseline (median + MAD) ─────────────────────────────────────────

def rolling_window_baseline(
    values: List[float],
    *,
    exclude_zero: bool = True,
) -> Tuple[Optional[float], Optional[float]]:
    """Return (median, MAD) over the values, ignoring zeros by default.

    Why median+MAD instead of mean+stddev:
        One huge outlier inflates the standard deviation so much that the
        outlier itself falls back under ``mean + 5σ``. MAD is robust by
        design (the median doesn't move with one extreme value), so the
        threshold derived from it stays meaningful.

    Why ``exclude_zero=True`` by default:
        For expense categories that pay irregularly (bimonthly, quarterly),
        the 0-months are not "low spending" — they are "no bill issued".
        Including them in the baseline would compute a much smaller median,
        making any actual bill look like an outlier. The bills among
        themselves are the meaningful comparison.

    Returns (None, None) when there is too little data to compute a baseline:
    a single value has no MAD (only itself to compare to), so we treat the
    baseline as undefined. Caller must handle this case gracefully (skip
    the alert).
    """
    sample = [v for v in values if v > 0] if exclude_zero else list(values)
    if len(sample) < 2:
        return None, None

    sample.sort()
    n = len(sample)
    if n % 2:
        median = sample[n // 2]
    else:
        median = (sample[n // 2 - 1] + sample[n // 2]) / 2

    abs_devs = sorted(abs(v - median) for v in sample)
    if n % 2:
        mad = abs_devs[n // 2]
    else:
        mad = (abs_devs[n // 2 - 1] + abs_devs[n // 2]) / 2

    return median, mad


# ── Anomaly outcome ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AnomalyOutcome:
    """Structured result returned by ``is_significant_anomaly``.

    Fields
    ------
    is_anomaly
        True when the rule should fire.
    score
        A scalar for the human-readable summary:
          • method='median_ratio' → ``current / median`` (e.g. 3.7 = "3.7×")
          • method='z_score'       → number of MAD-units above median
          • method='percentile'    → the value's rank in [0..1]
    label
        One of "below_threshold" | "above_threshold" | "matches_baseline"
        | "insufficient_history" | "stable" — drives the engine log line.
    reason
        Human-readable diagnostic for the log, never shown to the merchant.
    """
    is_anomaly: bool
    score: float
    label: str
    reason: str


# ── Main entry point ────────────────────────────────────────────────────────

def is_significant_anomaly(
    current_value: float,
    history: List[float],
    *,
    method: Literal["median_ratio", "z_score", "percentile"] = "median_ratio",
    min_history: int = 4,
    threshold: float = 2.5,
    min_absolute_delta: float = 0.0,
) -> AnomalyOutcome:
    """Decide whether ``current_value`` deviates enough from ``history``
    to count as a business-meaningful anomaly.

    Parameters
    ----------
    current_value
        The metric value we're testing (e.g. ``680`` for this month's
        electricity bill).
    history
        Past values to compare against. Should be the same kind of
        measurement (e.g. only the months where the bill was issued, when
        the category pays bimonthly).
    method
        Scoring strategy:
          * "median_ratio" — current_value / median(history). Threshold is
            the multiplier (2.5 = "2.5× the historical median"). Robust to
            outliers, easy to explain to merchants.
          * "z_score" — uses MAD-scaled deviation from median. Threshold is
            number of sigma equivalents (2.0 = "2σ above"). For data with
            visible noise but a stable baseline.
          * "percentile" — rank-based. Threshold is in [0, 1]; 0.95 means
            "current is in the top 5% of history". Useful for skewed data
            where mean/median are misleading.
    min_history
        Minimum length of ``history`` to compute a baseline. Below this,
        return ``insufficient_history`` — honest skip, not a false positive.
    threshold
        Method-specific significance bar (see ``method``).
    min_absolute_delta
        Absolute minimum difference between ``current_value`` and the
        baseline before considering an anomaly. Stops the rule from
        firing on tiny categories (e.g. a €5 → €12 stationery purchase
        is a 240% increase but irrelevant in business terms).

    Returns
    -------
    AnomalyOutcome
        Always returned — never raises. ``is_anomaly=False`` covers
        every "skip" reason with a clear ``label`` for telemetry.

    Why ``method='median_ratio'`` is the default:
        It's the most explainable. "Elettricità è 3.7× la mediana storica"
        is a sentence the merchant can verify and act on. z_score and
        percentile are harder to communicate but available for rules that
        need them.
    """
    if len(history) < min_history:
        return AnomalyOutcome(
            is_anomaly=False, score=0.0,
            label="insufficient_history",
            reason=f"history has {len(history)} samples, min is {min_history}",
        )

    median, mad = rolling_window_baseline(history, exclude_zero=True)
    if median is None:
        return AnomalyOutcome(
            is_anomaly=False, score=0.0,
            label="insufficient_history",
            reason="median undefined — all history values are zero",
        )

    # Absolute-delta gate: small categories make for noisy big ratios.
    if min_absolute_delta > 0 and abs(current_value - median) < min_absolute_delta:
        return AnomalyOutcome(
            is_anomaly=False, score=0.0,
            label="below_threshold",
            reason=(
                f"abs delta {abs(current_value - median):.2f} below "
                f"min_absolute_delta={min_absolute_delta}"
            ),
        )

    # Dispatch by method
    if method == "median_ratio":
        if median <= 0:
            return AnomalyOutcome(
                is_anomaly=False, score=0.0,
                label="insufficient_history",
                reason="median is zero — ratio undefined",
            )
        score = current_value / median
        # Threshold check goes both ways: a value 0.4× the median is just
        # as anomalous as 2.5× (collapse). The default rules only care
        # about "above"; rules that want to catch drops can pass
        # ``threshold < 1.0`` and we'd handle it below — for clarity in
        # this version we only check the "above" side. Inverting is a
        # one-liner the day we need it.
        if score >= threshold:
            return AnomalyOutcome(
                is_anomaly=True, score=round(score, 2),
                label="above_threshold",
                reason=f"current {current_value:.2f} = {score:.2f}× median {median:.2f}",
            )
        return AnomalyOutcome(
            is_anomaly=False, score=round(score, 2),
            label="matches_baseline",
            reason=f"current {current_value:.2f} = {score:.2f}× median {median:.2f}",
        )

    if method == "z_score":
        # MAD * 1.4826 ≈ σ for a normal distribution. We use that scaling
        # so the ``threshold`` argument reads as the familiar "2σ".
        if mad is None or mad <= 0:
            # MAD == 0 means every history value is identical to the
            # median. In that case, ANY deviation is technically a
            # change — fall back to the simple "ratio > 1.5" heuristic
            # for the same intent.
            if current_value > median * 1.5:
                return AnomalyOutcome(
                    is_anomaly=True, score=999.0,
                    label="above_threshold",
                    reason=f"flat history (MAD=0), current {current_value:.2f} > 1.5× median",
                )
            return AnomalyOutcome(
                is_anomaly=False, score=0.0,
                label="stable",
                reason="flat history and current within 1.5× median",
            )
        scaled_sigma = 1.4826 * mad
        z = (current_value - median) / scaled_sigma
        if z >= threshold:
            return AnomalyOutcome(
                is_anomaly=True, score=round(z, 2),
                label="above_threshold",
                reason=f"z={z:.2f} ≥ threshold={threshold}",
            )
        return AnomalyOutcome(
            is_anomaly=False, score=round(z, 2),
            label="matches_baseline",
            reason=f"z={z:.2f} < threshold={threshold}",
        )

    if method == "percentile":
        sorted_h = sorted(history)
        # Rank of current in history: how many values are <= current
        rank = sum(1 for v in sorted_h if v <= current_value)
        pct = rank / len(sorted_h)
        if pct >= threshold:
            return AnomalyOutcome(
                is_anomaly=True, score=round(pct, 3),
                label="above_threshold",
                reason=f"current at p{pct:.2f}, ≥ threshold p{threshold}",
            )
        return AnomalyOutcome(
            is_anomaly=False, score=round(pct, 3),
            label="matches_baseline",
            reason=f"current at p{pct:.2f}",
        )

    # Should never reach — Literal type catches typos at type-check time
    return AnomalyOutcome(
        is_anomaly=False, score=0.0,
        label="stable",
        reason=f"unknown method {method!r}",
    )


# ── Helper: build monthly timeline from daily aggregate ─────────────────────

def monthly_totals_from_daily(
    daily_amounts: Dict[str, float],
    months_back: int = 12,
    end_iso: Optional[str] = None,
) -> List[float]:
    """Roll up a {iso_date: amount} dict into a list of N monthly totals.

    Returns ``months_back`` values, chronologically ordered (oldest first),
    each = sum of all daily amounts in that calendar month. Months with no
    activity are returned as 0.0 — that 0 is the signal
    ``detect_payment_frequency`` reads to infer cadence.

    Why this helper lives in this module:
        It's the bridge between the daily-aggregate world the engine
        already uses and the monthly-cadence world ``detect_payment_frequency``
        expects. Keeping it next to the consumer keeps the dependency
        graph one-directional (rules import from here, never the other way).
    """
    from datetime import date as _date, timedelta as _td

    if end_iso:
        try:
            end = _date.fromisoformat(end_iso)
        except ValueError:
            end = _date.today()
    else:
        end = _date.today()

    # Anchor at start of end's month, then walk back months_back-1 months.
    out: List[float] = []
    cursor_year, cursor_month = end.year, end.month
    months: List[Tuple[int, int]] = []
    for _ in range(months_back):
        months.append((cursor_year, cursor_month))
        # Decrement (year, month) by one
        cursor_month -= 1
        if cursor_month == 0:
            cursor_month = 12
            cursor_year -= 1
    months.reverse()  # oldest first

    for year, month in months:
        prefix = f"{year:04d}-{month:02d}-"
        total = sum(v for k, v in daily_amounts.items()
                    if isinstance(k, str) and k.startswith(prefix))
        out.append(total)
    return out


# ── P2.5 severity scaling ──────────────────────────────────────────────────
# When a rule fires off the back of an ``is_significant_anomaly`` outcome,
# the natural mapping is "bigger score → worse severity". B4 and C1 each
# wrote their own if/elif/elif inline; the thresholds differ legitimately
# (a 2.5× DSO ratio is alarming, a 2.5× category spend ratio is routine),
# but the SHAPE of the mapping shouldn't be reinvented per rule. This
# helper is the single source of truth for that shape: three tiers,
# fail-safe to LOW for any unexpected input.


def severity_tier_from_score(
    score: float,
    high_threshold: float,
    medium_threshold: float,
) -> str:
    """Map an anomaly score to a severity tier name.

    Returns one of "high" / "medium" / "low". The string form keeps this
    function free of dependencies on the ``AlertSeverity`` enum (which
    lives in the models package) — callers convert the string to the
    enum at their boundary. Decouples the math from the protocol.

    Contract
    --------
    - ``score >= high_threshold`` → "high"
    - ``high_threshold > score >= medium_threshold`` → "medium"
    - else → "low" (includes negative, zero, and NaN scores)

    The asymmetric "≥" boundaries match the merchant's natural
    expectation: "at 5× or worse it's high", not "above 5×".

    Raises
    ------
    ValueError if ``medium_threshold > high_threshold`` — a logic bug
    in the caller, surfaced eagerly rather than silently swapped.
    """
    if medium_threshold > high_threshold:
        raise ValueError(
            f"medium_threshold ({medium_threshold}) must be <= "
            f"high_threshold ({high_threshold})"
        )
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "low"
    if s != s:  # NaN check
        return "low"
    if s >= high_threshold:
        return "high"
    if s >= medium_threshold:
        return "medium"
    return "low"
