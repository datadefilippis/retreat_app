"""Period filter — parses period strings into date windows.

The legacy ``customers_light`` overview ignored period parameters entirely
(see audit notes: ``period``, ``start_date``, ``end_date`` were declared
but never applied). Phase 1 of the Customer Insights restructuring fixes
that by introducing a single canonical parser used by every endpoint:

  • ``parse_period("30d")``  → last 30 days ending today
  • ``parse_period("90d")``  → last 90 days
  • ``parse_period("12m")``  → last 12 months
  • ``parse_period("all")``  → org's entire history (start = epoch)
  • ``parse_period("custom", start="2026-01-01", end="2026-01-31")``
                              → explicit window

For period-vs-previous comparisons the helper ``previous_period`` returns
a window of the same length immediately preceding the input window.
This is what the UI uses to render delta badges ("+12 % vs 30g prima").

Pure / synchronous / no I/O. Testable without a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────


# Pinned origin used as the lower bound for ``period=all``. Predates any
# realistic merchant onboarding by years, so any sales record is included.
_EPOCH_FALLBACK = date(2020, 1, 1)


# Recognised symbolic period codes. Anything else falls back to "30d" with
# a warning logged by the caller — never raises so a malformed query
# parameter on the URL doesn't 500 the page.
_RELATIVE_PERIODS = {
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "180d": timedelta(days=180),
    "12m": timedelta(days=365),
    "24m": timedelta(days=730),
}


# ──────────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PeriodWindow:
    """An inclusive [start, end] date range with a human-readable label.

    Attributes:
        start: First day in the window (inclusive).
        end: Last day in the window (inclusive).
        label: Origin marker, e.g. "30d", "custom", "previous-30d".
               Used by the UI to render labels and by ``previous_period``
               to derive the comparison window.
    """

    start: date
    end: date
    label: str

    @property
    def days(self) -> int:
        """Inclusive length of the window in days."""
        return (self.end - self.start).days + 1

    @property
    def start_iso(self) -> str:
        """ISO date string suitable for MongoDB date-string comparisons."""
        return self.start.isoformat()

    @property
    def end_iso(self) -> str:
        return self.end.isoformat()


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────


def parse_period(
    period: str,
    *,
    start: Optional[str] = None,
    end: Optional[str] = None,
    today: Optional[date] = None,
) -> PeriodWindow:
    """Parse a period string into a concrete date window.

    Args:
        period: One of ``7d / 30d / 90d / 180d / 12m / 24m / all / custom``.
                Unknown values fall back to ``30d`` (caller is expected to
                validate at the FastAPI layer if strict behaviour is wanted).
        start: ISO date, only consulted when ``period == "custom"``.
        end:   ISO date, only consulted when ``period == "custom"``.
        today: Override "today" for testability.

    Returns:
        A ``PeriodWindow`` whose label preserves the original ``period``
        string (or ``custom`` for explicit windows). The window is
        ``end_inclusive`` — both ``start`` and ``end`` count as in-window.

    Examples:
        >>> from datetime import date
        >>> w = parse_period("30d", today=date(2026, 5, 10))
        >>> w.start.isoformat(), w.end.isoformat()
        ('2026-04-10', '2026-05-10')
        >>> w.days
        31

        >>> w = parse_period("all", today=date(2026, 5, 10))
        >>> w.start.year
        2020

        >>> w = parse_period("custom", start="2026-01-01", end="2026-01-31",
        ...                   today=date(2026, 5, 10))
        >>> w.label
        'custom'
        >>> w.days
        31

    Notes:
        Even an "all" window has a concrete ``start`` so the Mongo
        ``$gte / $lte`` clauses are uniform across all paths. The fallback
        date (Jan 2020) is well before any production data.
    """
    if today is None:
        today = date.today()

    code = (period or "").strip().lower()

    if code == "custom":
        s = _parse_iso(start) or today - timedelta(days=29)
        e = _parse_iso(end) or today
        # Defensive: swap if caller inverted them.
        if s > e:
            s, e = e, s
        return PeriodWindow(start=s, end=e, label="custom")

    if code == "all":
        return PeriodWindow(start=_EPOCH_FALLBACK, end=today, label="all")

    delta = _RELATIVE_PERIODS.get(code) or _RELATIVE_PERIODS["30d"]
    # 30d means "the last 30 days inclusive of today" — so subtract 29 to
    # get exactly 30 days when both endpoints are inclusive.
    return PeriodWindow(
        start=today - delta + timedelta(days=1),
        end=today,
        label=code if code in _RELATIVE_PERIODS else "30d",
    )


def previous_period(window: PeriodWindow) -> PeriodWindow:
    """Return a same-length window immediately preceding ``window``.

    Used to compute MoM/QoQ deltas. The returned label is prefixed with
    ``previous-`` so the UI can distinguish it from the live one.

    Examples:
        >>> from datetime import date
        >>> curr = PeriodWindow(start=date(2026, 5, 1), end=date(2026, 5, 30),
        ...                     label="30d")
        >>> prev = previous_period(curr)
        >>> prev.start.isoformat(), prev.end.isoformat()
        ('2026-04-01', '2026-04-30')
        >>> prev.label
        'previous-30d'

        >>> # An ``all`` window has no meaningful "previous" — we still
        >>> # return one of equivalent length anchored before the start.
        >>> all_w = parse_period("all", today=date(2026, 5, 10))
        >>> prev_all = previous_period(all_w)
        >>> prev_all.label
        'previous-all'
    """
    span_days = window.days
    new_end = window.start - timedelta(days=1)
    new_start = new_end - timedelta(days=span_days - 1)
    return PeriodWindow(
        start=new_start,
        end=new_end,
        label=f"previous-{window.label}",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────


def _parse_iso(value: Optional[str]) -> Optional[date]:
    """Parse a YYYY-MM-DD string. Returns None for invalid input."""
    if not value:
        return None
    try:
        from datetime import datetime
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
