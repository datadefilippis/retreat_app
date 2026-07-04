"""Cohort retention math — pure functions.

A *cohort* is the set of customers acquired in a given time bucket
(month, quarter, etc.), tracked over subsequent buckets to measure
retention. The Phase 2 UI renders this as a triangular table:

                  M0     M1      M2      M3       ...   M11
    Jan 2026     12      9 (75%) 6 (50%) 5 (42%)  ...   3 (25%)
    Feb 2026     18     15 (83%) 12 (67%) ...
    Mar 2026     15     11 (73%) ...
    ...

Each cell is "# of customers from cohort still active in that bucket".
"Active in bucket B" = "made at least one purchase in B".

These functions are pure: they accept already-fetched purchase records
and bucket them. The repository layer is the one that talks to Mongo.

Bucket granularity (the ``bucket`` param) is one of:

    "month"   — YYYY-MM
    "quarter" — YYYY-Q1..Q4
    "week"    — YYYY-Www  (ISO week)

Everywhere else in the codebase a "period" refers to a date range
(see ``period_filter.PeriodWindow``). A cohort "bucket" is different:
it's a recurring tag applied to dates so we can group purchases.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# Bucketing primitives
# ──────────────────────────────────────────────────────────────────────────────


def bucket_for_date(d: date, bucket: str) -> str:
    """Return the cohort-bucket tag for a date.

    >>> from datetime import date
    >>> bucket_for_date(date(2026, 5, 10), "month")
    '2026-05'
    >>> bucket_for_date(date(2026, 5, 10), "quarter")
    '2026-Q2'
    >>> bucket_for_date(date(2026, 1, 6), "week")
    '2026-W02'
    """
    if bucket == "quarter":
        q = (d.month - 1) // 3 + 1
        return f"{d.year}-Q{q}"
    if bucket == "week":
        # ISO calendar week. Note: edge dates may belong to neighbouring year.
        iso_year, iso_week, _ = d.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    # default + "month"
    return f"{d.year}-{d.month:02d}"


def bucket_index_diff(bucket_a: str, bucket_b: str, kind: str) -> int:
    """How many buckets *forward* from ``bucket_a`` to ``bucket_b``.

    Used to assign each purchase to its "M0 / M1 / M2 / ..." offset
    relative to the customer's acquisition cohort.

    Returns a non-negative int. If b precedes a (impossible for
    a properly-ordered cohort) the offset is 0 (clamped) so the
    triangular table never gets negative-offset cells.

    >>> bucket_index_diff("2026-01", "2026-05", "month")
    4
    >>> bucket_index_diff("2026-Q1", "2026-Q3", "quarter")
    2
    >>> bucket_index_diff("2026-05", "2026-01", "month")  # b before a
    0
    """
    if kind == "month":
        return _month_diff(bucket_a, bucket_b)
    if kind == "quarter":
        return _quarter_diff(bucket_a, bucket_b)
    if kind == "week":
        return _week_diff(bucket_a, bucket_b)
    return 0


# ──────────────────────────────────────────────────────────────────────────────
# Cohort table assembly
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CohortRow:
    """One row of the retention table.

    Attributes:
        acquisition_bucket: e.g. "2026-01"
        size: # of distinct customers acquired in that bucket
        retention: list aligned with offset 0..N-1; each value is the
                   count of those customers active in that offset bucket.
                   Cell 0 is always == size (M0 by definition).
    """

    acquisition_bucket: str
    size: int
    retention: list[int]

    @property
    def retention_pct(self) -> list[Optional[float]]:
        """Same as ``retention`` but as percentage (None for offset > size)."""
        if self.size <= 0:
            return [None] * len(self.retention)
        return [round(c / self.size * 100, 1) for c in self.retention]


def build_cohort_table(
    customer_purchases: dict[str, list[date]],
    bucket: str = "month",
    horizon: int = 12,
) -> list[CohortRow]:
    """Assemble the cohort retention table from raw per-customer dates.

    Args:
        customer_purchases:
            ``{customer_id: [date, date, ...]}`` — every distinct purchase
            date for each customer. Same-day dupes are tolerated; we
            de-duplicate when computing activity.
        bucket: ``"month"``, ``"quarter"``, or ``"week"``.
        horizon: Number of follow-up periods to track per cohort.

    Returns:
        List of :class:`CohortRow` sorted by ``acquisition_bucket`` ascending.
        Empty input → empty list.

    Algorithm:
        1. For each customer, compute first_purchase_date → acquisition bucket.
        2. For each purchase of theirs, compute its bucket → offset from
           acquisition. If offset < horizon, that customer is "active" in
           that offset for their cohort.
        3. Aggregate: count distinct customers active per (cohort, offset).

    Example:
        >>> from datetime import date
        >>> rows = build_cohort_table({
        ...     "c1": [date(2026, 1, 5), date(2026, 2, 10), date(2026, 3, 1)],
        ...     "c2": [date(2026, 1, 20), date(2026, 4, 3)],
        ...     "c3": [date(2026, 2, 1), date(2026, 2, 25)],
        ... }, bucket="month", horizon=4)
        >>> rows[0].acquisition_bucket
        '2026-01'
        >>> rows[0].size
        2
        >>> rows[0].retention      # Jan: M0=2, M1=1 (only c1), M2=1 (c1), M3=1 (c2)
        [2, 1, 1, 1]
        >>> rows[1].acquisition_bucket
        '2026-02'
        >>> rows[1].size
        1
        >>> rows[1].retention
        [1, 0, 0, 0]
    """
    if not customer_purchases:
        return []

    # Step 1 — acquisition bucket per customer
    acquisition: dict[str, str] = {}
    for cid, dates in customer_purchases.items():
        if not dates:
            continue
        first = min(dates)
        acquisition[cid] = bucket_for_date(first, bucket)

    if not acquisition:
        return []

    # Step 2 — activity matrix: {cohort_bucket: {offset: set(customer_ids)}}
    matrix: dict[str, dict[int, set[str]]] = {}
    for cid, dates in customer_purchases.items():
        coh = acquisition.get(cid)
        if coh is None:
            continue
        for d in dates:
            tag = bucket_for_date(d, bucket)
            offset = bucket_index_diff(coh, tag, bucket)
            if offset < 0 or offset >= horizon:
                continue
            matrix.setdefault(coh, {}).setdefault(offset, set()).add(cid)

    # Step 3 — flatten + sort
    cohorts_sorted = sorted(matrix.keys())
    rows: list[CohortRow] = []
    for coh in cohorts_sorted:
        size = len(matrix[coh].get(0, set()))
        retention = [
            len(matrix[coh].get(off, set())) for off in range(horizon)
        ]
        rows.append(
            CohortRow(
                acquisition_bucket=coh,
                size=size,
                retention=retention,
            )
        )
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Bucket diff helpers
# ──────────────────────────────────────────────────────────────────────────────


def _month_diff(a: str, b: str) -> int:
    """Months from a to b. Inputs are 'YYYY-MM' strings."""
    try:
        ay, am = (int(p) for p in a.split("-"))
        by, bm = (int(p) for p in b.split("-"))
    except (ValueError, AttributeError):
        return 0
    diff = (by - ay) * 12 + (bm - am)
    return max(0, diff)


def _quarter_diff(a: str, b: str) -> int:
    """Quarters from a to b. Inputs are 'YYYY-QN' strings."""
    try:
        ay, aq_str = a.split("-Q")
        by, bq_str = b.split("-Q")
        ay, aq = int(ay), int(aq_str)
        by, bq = int(by), int(bq_str)
    except (ValueError, AttributeError):
        return 0
    diff = (by - ay) * 4 + (bq - aq)
    return max(0, diff)


def _week_diff(a: str, b: str) -> int:
    """ISO weeks from a to b. Inputs are 'YYYY-Www' strings.

    Naive implementation: convert both to first-day-of-iso-week dates and
    subtract. Adequate for a 12-bucket horizon.
    """
    try:
        ay, aw_str = a.split("-W")
        by, bw_str = b.split("-W")
        ay, aw = int(ay), int(aw_str)
        by, bw = int(by), int(bw_str)
    except (ValueError, AttributeError):
        return 0
    a_date = date.fromisocalendar(ay, aw, 1)
    b_date = date.fromisocalendar(by, bw, 1)
    diff_days = (b_date - a_date).days
    return max(0, diff_days // 7)
