"""
Canonical period resolver for AI surfaces (chat, digest, alert, cashflow).

Wave 13.0 — Period Integrity foundation.

Single source of truth for translating "period intent" (a named token, or
an explicit pair of dates, or nothing) into a concrete inclusive date
range. Replaces ad-hoc per-tool period parsing where the same token
(e.g. ``"ytd"``) was silently treated as 30d in some places and as
Jan 1 → today in others.

The resolver is pure: no DB, no async, no I/O — just date math. That
means it is trivially testable AND can be safely imported from any
layer (router, service, repository, test, …) without circular-import
or side-effect concerns.

Why this exists
---------------
Pre-Wave-13 the period vocabulary was implicit and inconsistent:

  - Frontend ``PeriodSelector`` offers: 7d, 30d, 90d, ytd, mtd, custom,
    data_range. (See: frontend/src/components/PeriodSelector.js)
  - Tool descriptions advertise: 7d, 30d, 90d only.
  - Backend ``services.ai_analytics_service._get_date_range`` accepts
    ONLY 7d / 30d / 90d — everything else (ytd, mtd, q1, last_year, …)
    silently falls back to 30d.

The mismatch surfaced in the chat AI: a merchant on the YTD filter
asked "qual è il mio health score" and the model quoted 48/100 — which
was the 30-day score injected by the proactive context and a 30d fall-
back of mis-routed tokens, NOT the actual YTD value of 33/100 shown on
the dashboard. See the Wave 13 audit doc for the full trace.

Public API
----------
    :class:`ResolvedPeriod`     — immutable result with start/end/days/source
    :class:`ResolutionSource`   — enum identifying how the period was resolved
    :class:`InvalidPeriodError` — raised on invalid input (also a ValueError)
    :func:`resolve`             — the canonical resolver
    :data:`ACCEPTED_TOKENS`     — frozenset of the canonical vocabulary
    :data:`DEFAULT_PERIOD`      — module-level default ("30d")

Vocabulary
----------
Rolling windows (anchored to today, inclusive end):
    "7d"   — last 7 days
    "30d"  — last 30 days
    "90d"  — last 90 days
    "1y"   — last 365 days

Calendar-to-date windows (anchored to start of period, inclusive end):
    "ytd"  — year-to-date  (Jan 1 → today)
    "mtd"  — month-to-date (1st of current month → today)
    "qtd"  — quarter-to-date (1st of current quarter → today)

Explicit-only (require start_date + end_date from the caller):
    "custom"     — generic custom range
    "data_range" — frontend's "from first ever record to today"

Aliases (case-insensitive, applied before lookup; see _ALIASES):
    last_7_days, 7days        → 7d
    last_30_days, 30days      → 30d
    last_90_days, 90days      → 90d
    last_12_months, last_365_days, last_year_rolling → 1y
    year_to_date, this_year   → ytd
    month_to_date, this_month → mtd
    quarter_to_date, this_quarter → qtd

NOT aliased (deliberate — these have semantic ambiguity that only the
caller can disambiguate):

    "last_month"   — previous calendar month? Or rolling 30 days?
    "last_year"    — previous calendar year? Or rolling 365 days?
    "last_quarter" — previous calendar quarter? Or rolling 90 days?

The chat system prompt (see services/chat_service.py) instructs the
model to use explicit start_date + end_date for those.

Resolution priority
-------------------
1. ``start_date`` AND ``end_date`` provided → use them verbatim
   (any ``period`` is preserved as a label hint but NOT used for math).
2. Exactly one of start_date / end_date → :class:`InvalidPeriodError`
   (prevents silent half-baked windows).
3. Token provided:
   3a. canonical or alias → compute from token + today.
   3b. token in {custom, data_range} → :class:`InvalidPeriodError`.
   3c. unknown + strict=True → :class:`InvalidPeriodError`.
   3d. unknown + strict=False → fall back to default, source set to
       ``FALLBACK_UNKNOWN_TOKEN`` so the caller can warn.
4. Nothing provided → use default, source=``DEFAULT``.

Backward compatibility (Wave 13.1 contract)
-------------------------------------------
The legacy ``_get_date_range`` accepted only 7d/30d/90d and silently
returned 30d for anything else. Once Wave 13.1 wires this resolver
in (via a thin adapter), all existing callers passing 7d/30d/90d see
identical output. NEW callers (or the model emitting ytd/mtd/qtd)
now get correct output instead of the silent 30d fallback. The
``strict=True`` mode is opt-in and will become the production default
once Wave 13.1.C flips ``STRICT_PERIOD_VALIDATION``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional


# ── Public constants ─────────────────────────────────────────────────────────

#: Default period when the caller provides no input. Must be a token in
#: ``ACCEPTED_TOKENS`` and NOT in ``_EXPLICIT_REQUIRED_TOKENS``.
DEFAULT_PERIOD = "30d"


#: Rolling-window tokens: dates derived from ``today`` minus N days.
#: Mapping value is the inclusive window length.
_ROLLING_TOKENS = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "1y": 365,
}

#: Calendar-anchored tokens: dates derived from start-of-period → today.
_CALENDAR_TOKENS = frozenset({"ytd", "mtd", "qtd"})

#: Tokens that require explicit start_date + end_date from the caller.
#: Listing them lets the resolver give a precise error instead of
#: falling through to "unknown token" handling.
_EXPLICIT_REQUIRED_TOKENS = frozenset({"custom", "data_range"})


#: Full accepted vocabulary, AFTER alias normalisation. Re-exported as a
#: frozenset so consumers (system prompt builder, schema introspection,
#: tests) can enumerate the contract without re-deriving it.
ACCEPTED_TOKENS = frozenset(
    set(_ROLLING_TOKENS.keys()) | _CALENDAR_TOKENS | _EXPLICIT_REQUIRED_TOKENS
)


#: Aliases the LLM is likely to emit (financial vocabulary it learned in
#: training). Mapped to canonical tokens before lookup. Case-insensitive.
#:
#: We DELIBERATELY do not alias "last_month" / "last_year" / "last_quarter"
#: because their meaning is ambiguous (previous calendar period vs rolling
#: N days). The system prompt directs the model to use explicit dates for
#: those.
_ALIASES = {
    # rolling
    "last_7_days": "7d",
    "7days": "7d",
    "last_week_rolling": "7d",
    "last_30_days": "30d",
    "30days": "30d",
    "last_90_days": "90d",
    "90days": "90d",
    "last_365_days": "1y",
    "last_12_months": "1y",
    "last_year_rolling": "1y",
    # calendar-to-date
    "year_to_date": "ytd",
    "this_year": "ytd",
    "month_to_date": "mtd",
    "this_month": "mtd",
    "quarter_to_date": "qtd",
    "this_quarter": "qtd",
}


# ── Errors ───────────────────────────────────────────────────────────────────


class InvalidPeriodError(ValueError):
    """Raised when the resolver cannot translate the input into a valid range.

    Inherits :class:`ValueError` so callers that handle ValueError generic-
    ally still catch it, but the specific class lets the chat dispatcher
    catch only period errors and translate them into a tool-result error
    the model can read and self-correct from.
    """


# ── Result shape ─────────────────────────────────────────────────────────────


class ResolutionSource(str, Enum):
    """How the resolver arrived at the final dates.

    Useful for audit logging (Wave 13.2) and for callers that want to
    treat fallbacks differently (e.g. attach an explicit caveat to the
    tool result saying "you asked for X but I returned Y").
    """

    #: Caller provided both ``start_date`` and ``end_date``.
    EXPLICIT_DATES = "explicit_dates"

    #: Caller provided a canonical or aliased token (e.g. "ytd", "30d").
    TOKEN = "token"

    #: Caller provided nothing; resolver used :data:`DEFAULT_PERIOD`.
    DEFAULT = "default"

    #: Caller provided a token outside the vocabulary AND ``strict=False``;
    #: resolver fell back to the default and recorded this source so the
    #: dispatcher can log a warning + surface a caveat to the model.
    FALLBACK_UNKNOWN_TOKEN = "fallback_unknown_token"


@dataclass(frozen=True)
class ResolvedPeriod:
    """Immutable result of :func:`resolve`.

    Attributes:
        label: The canonical token used for the window (e.g. ``"ytd"``,
            ``"30d"``, or ``"custom"`` when explicit dates were given
            without a token hint).
        start: Inclusive start date.
        end: Inclusive end date.
        days: ``(end - start).days + 1`` — convenience for downstream
            burn-rate / avg-daily calculations.
        resolution_source: How the resolver reached this result.
            See :class:`ResolutionSource`.
        requested_period: The original ``period`` argument as passed by
            the caller (un-normalised). Useful for audit logging so we
            can see what the model actually emitted vs what we resolved.
        requested_start: Original ``start_date`` argument as passed.
        requested_end: Original ``end_date`` argument as passed.
    """

    label: str
    start: date
    end: date
    days: int
    resolution_source: ResolutionSource

    # Audit-only fields — preserve the un-normalised inputs for logging.
    requested_period: Optional[str] = None
    requested_start: Optional[str] = None
    requested_end: Optional[str] = None

    @property
    def start_iso(self) -> str:
        """ISO-formatted start date (``YYYY-MM-DD``)."""
        return self.start.isoformat()

    @property
    def end_iso(self) -> str:
        """ISO-formatted end date (``YYYY-MM-DD``)."""
        return self.end.isoformat()

    def to_audit_dict(self) -> dict:
        """Serialise for structured logging.

        Consumed by ``services/chat_service.py`` (Wave 13.2) to emit one
        structured log line per tool dispatch capturing the full period
        resolution audit trail. The shape is intentionally stable so
        downstream log queries can rely on it.
        """
        return {
            "label": self.label,
            "start": self.start_iso,
            "end": self.end_iso,
            "days": self.days,
            "resolution_source": self.resolution_source.value,
            "requested": {
                "period": self.requested_period,
                "start_date": self.requested_start,
                "end_date": self.requested_end,
            },
        }


# ── Internal helpers ─────────────────────────────────────────────────────────


def _normalise(token: Optional[str]) -> Optional[str]:
    """Lowercase + strip + alias-map a raw token string.

    Returns ``None`` when the input is None, empty, or only whitespace —
    so the caller can treat "no token" uniformly.
    """
    if not token:
        return None
    norm = token.strip().lower()
    if not norm:
        return None
    return _ALIASES.get(norm, norm)


def _parse_iso_date(value: str, *, field_name: str) -> date:
    """Parse ``YYYY-MM-DD`` or raise :class:`InvalidPeriodError` with field context."""
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise InvalidPeriodError(
            f"{field_name} is not a valid YYYY-MM-DD date: {value!r}"
        ) from exc


def _quarter_start(today: date) -> date:
    """Return the first day of the calendar quarter containing ``today``.

    Q1 = Jan-Mar, Q2 = Apr-Jun, Q3 = Jul-Sep, Q4 = Oct-Dec.
    """
    quarter_index = (today.month - 1) // 3   # 0..3
    first_month = quarter_index * 3 + 1      # 1, 4, 7, 10
    return date(today.year, first_month, 1)


def _resolve_token(token: str, today: date) -> tuple:
    """Compute ``(start, end)`` for a canonical, non-explicit token.

    Precondition: ``token`` must be in ``ACCEPTED_TOKENS`` and NOT in
    ``_EXPLICIT_REQUIRED_TOKENS``. Caller is responsible for that check.
    """
    if token in _ROLLING_TOKENS:
        days = _ROLLING_TOKENS[token]
        return today - timedelta(days=days - 1), today
    if token == "ytd":
        return date(today.year, 1, 1), today
    if token == "mtd":
        return today.replace(day=1), today
    if token == "qtd":
        return _quarter_start(today), today
    # Should be unreachable due to caller-side guards. Defence-in-depth:
    # raise rather than return junk if a future contributor extends
    # ACCEPTED_TOKENS without extending this branch.
    raise InvalidPeriodError(
        f"Internal error: _resolve_token does not handle {token!r}. "
        "ACCEPTED_TOKENS was extended without updating the resolver."
    )


def _validate_range(
    sd: date, ed: date, *, today: date, allow_future: bool
) -> None:
    """Common validations for explicit-date input."""
    if sd > ed:
        raise InvalidPeriodError(
            f"start_date ({sd.isoformat()}) must be <= end_date ({ed.isoformat()})."
        )
    if not allow_future and ed > today:
        raise InvalidPeriodError(
            f"end_date ({ed.isoformat()}) is in the future "
            f"(today={today.isoformat()}). Pass allow_future=True for "
            "forward-looking surfaces (rentals/agenda)."
        )


# ── Public resolver ──────────────────────────────────────────────────────────


def resolve(
    period: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    *,
    today: Optional[date] = None,
    strict: bool = False,
    default: str = DEFAULT_PERIOD,
    allow_future: bool = False,
) -> ResolvedPeriod:
    """Translate period intent into a concrete inclusive date range.

    See module docstring for the resolution priority and vocabulary.

    Args:
        period: A token from :data:`ACCEPTED_TOKENS` or a known alias.
            Whitespace and case are normalised.
        start_date: ISO ``YYYY-MM-DD`` string; inclusive.
        end_date: ISO ``YYYY-MM-DD`` string; inclusive.
        today: Anchor for "today" — defaults to :func:`date.today`.
            Inject a fixed date in tests for deterministic output.
        strict: When True, unknown tokens raise instead of falling back
            to ``default``. Production should flip this to True via env
            once log analysis confirms no legitimate caller still emits
            unknown tokens.
        default: Token used when no input is provided OR as fallback for
            unknown tokens (non-strict mode). Must be a known rolling or
            calendar token (not ``custom`` / ``data_range``).
        allow_future: When True, ``end_date`` may be after ``today``.
            Used only for forward-looking surfaces (rentals upcoming,
            agenda, free slots).

    Returns:
        :class:`ResolvedPeriod` with concrete dates and audit metadata.

    Raises:
        :class:`InvalidPeriodError`: on any validation failure
            (bad format, swapped dates, future dates when not allowed,
            only one of start/end provided, unknown token in strict mode,
            invalid ``default`` parameter, …).
    """
    # ── Step 0. Validate the ``default`` config argument. ──────────────────
    # If a contributor passes default="custom" or default="ytd_oops" this
    # is a programmer error, not a user error — surface it eagerly.
    norm_default = _normalise(default)
    if (
        norm_default is None
        or norm_default in _EXPLICIT_REQUIRED_TOKENS
        or norm_default not in ACCEPTED_TOKENS
    ):
        valid = sorted(ACCEPTED_TOKENS - _EXPLICIT_REQUIRED_TOKENS)
        raise InvalidPeriodError(
            f"resolve() called with invalid default={default!r}. "
            f"Must be one of: {valid}."
        )

    today = today or date.today()
    norm_period = _normalise(period)

    # ── Step 1. Both explicit dates provided → use verbatim. ───────────────
    if start_date is not None and end_date is not None:
        sd = _parse_iso_date(start_date, field_name="start_date")
        ed = _parse_iso_date(end_date, field_name="end_date")
        _validate_range(sd, ed, today=today, allow_future=allow_future)
        # If the caller also passed a token, preserve it as a label hint
        # (audit logs benefit); otherwise label = "custom" so the audit
        # log is unambiguous about "this was explicit-dates input".
        label = norm_period if norm_period else "custom"
        return ResolvedPeriod(
            label=label,
            start=sd,
            end=ed,
            days=(ed - sd).days + 1,
            resolution_source=ResolutionSource.EXPLICIT_DATES,
            requested_period=period,
            requested_start=start_date,
            requested_end=end_date,
        )

    # ── Step 2. Only one of start_date / end_date → error. ─────────────────
    # Better to fail loud than silently treat as "no dates provided",
    # which previously caused half-baked windows where the user thought
    # they had pinned a date but the resolver ignored it.
    if (start_date is None) != (end_date is None):
        raise InvalidPeriodError(
            "Both start_date and end_date must be provided together "
            f"(got start_date={start_date!r}, end_date={end_date!r})."
        )

    # ── Step 3. Token-based resolution. ────────────────────────────────────
    if norm_period is not None:
        if norm_period in _EXPLICIT_REQUIRED_TOKENS:
            raise InvalidPeriodError(
                f"period={period!r} requires explicit start_date + end_date."
            )
        if norm_period in ACCEPTED_TOKENS:
            sd, ed = _resolve_token(norm_period, today)
            # No future-validation needed for known tokens — they end at
            # ``today`` by construction.
            return ResolvedPeriod(
                label=norm_period,
                start=sd,
                end=ed,
                days=(ed - sd).days + 1,
                resolution_source=ResolutionSource.TOKEN,
                requested_period=period,
                requested_start=None,
                requested_end=None,
            )
        # Unknown token.
        if strict:
            valid = sorted(ACCEPTED_TOKENS)
            raise InvalidPeriodError(
                f"Unknown period token: {period!r}. "
                f"Accepted: {valid} (or pass start_date + end_date)."
            )
        # Non-strict: fall back to default. Source records the fallback
        # so the dispatcher can log + attach a caveat to the tool result.
        sd, ed = _resolve_token(norm_default, today)
        return ResolvedPeriod(
            label=norm_default,
            start=sd,
            end=ed,
            days=(ed - sd).days + 1,
            resolution_source=ResolutionSource.FALLBACK_UNKNOWN_TOKEN,
            requested_period=period,
            requested_start=None,
            requested_end=None,
        )

    # ── Step 4. Nothing provided → use default. ────────────────────────────
    sd, ed = _resolve_token(norm_default, today)
    return ResolvedPeriod(
        label=norm_default,
        start=sd,
        end=ed,
        days=(ed - sd).days + 1,
        resolution_source=ResolutionSource.DEFAULT,
        requested_period=None,
        requested_start=None,
        requested_end=None,
    )
