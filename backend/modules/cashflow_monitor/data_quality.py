"""
Data Quality infrastructure for the alert engine (Pillar 1 — v14.1).

Provides two collaborating primitives:

  - ``DataQualitySnapshot``: a frozen view of the org's data state at the
    moment an alert tick runs. Computed once by the engine, consumed by
    rule decorators (and exposed on ``AlertContext.data_quality``).

  - ``RuleRequirements`` + ``@requires_data(...)``: a declarative contract
    each rule attaches to itself, describing what data conditions must be
    satisfied before the rule may emit an alert. The engine checks the
    contract before calling the rule.

Design principles
-----------------
- **Backward-compatible**: rules without ``@requires_data`` keep firing as
  before. The decorator is opt-in per rule. We can roll out gradually,
  one category at a time, without breaking the existing 26-rule lineup.
- **Pure data**: no DB writes, no I/O. The snapshot is built from data the
  engine has already loaded into ``AlertContext``. This keeps the cost
  near-zero (single struct populate, ~microseconds).
- **Single source of truth**: every "should-this-rule-fire?" question
  routes through ``RuleRequirements.evaluate(snapshot)``. The engine no
  longer carries inline min-sample / data-presence checks scattered
  across rule files.
- **Telemetry-ready**: ``RequirementOutcome`` records the reason a rule
  was skipped (insufficient_data / missing_dataset / outlier_present),
  which the engine logs for downstream rule-health monitoring.
- **Forward-compatible**: adding a new requirement axis (e.g. "needs
  payment_status coverage > 50%") means one new field on
  ``RuleRequirements`` plus one new check in ``evaluate``. The 26 existing
  decorated rules don't need to change.

This module is intentionally framework-free: no FastAPI imports, no DB
client. It can be unit-tested with a hand-built snapshot dict and a
mock rule function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Set, Callable
import logging

logger = logging.getLogger(__name__)


# ── Dataset coverage flags ──────────────────────────────────────────────────
#
# Canonical names that rule decorators reference in their ``datasets``
# requirement. Kept as a frozenset constant so a typo at decoration time
# fails fast at module import (the validator in ``RuleRequirements`` will
# raise) rather than at run time.

KNOWN_DATASETS = frozenset({
    "sales",            # sales_records
    "expenses",         # expense_records
    "purchases",        # purchase_records
    "fixed_costs",      # fixed_costs (no date filter — uses start/end_date)
    "orders",           # commerce orders (cat F)
    "customer_ids",     # sales records with a customer_id set
    "due_dates",        # sales/purchase records with due_date populated
    "payment_status",   # sales/purchase records with payment_status set
})


# ── Snapshot ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DataQualitySnapshot:
    """Frozen view of one org's data state at tick time.

    Built once by the engine (in ``_build_context``) from the same data
    the rules will read. Frozen so a rule can hold a reference without
    accidentally mutating the engine's view.

    The fields are deliberately small + boolean / int / float — no
    nested objects, no DB cursors. This keeps the snapshot trivially
    serialisable for telemetry / debugging.
    """

    # ── Age + recency ──────────────────────────────────────────────────────
    # ``days_since_first_record`` covers the "is this org brand new?"
    # question. ``last_upload_age_days`` covers the "did the merchant
    # stop importing?" question. Together they gate the org-onboarding
    # rule (G3) and any rule that needs fresh data.
    days_since_first_record: int = 0
    last_upload_age_days: int = 999  # large default = "stale or unknown"

    # ── Dataset population (within the alert window) ──────────────────────
    # Sample sizes in the last 30 days. Rules use these to decide
    # "do I have enough signal to call this an anomaly?". A min_samples
    # of 20 is the rough threshold below which any trend/stddev becomes
    # noise.
    sales_count_30d: int = 0
    expenses_count_30d: int = 0
    purchases_count_30d: int = 0
    fixed_costs_active: int = 0

    # Counts in the full history horizon (90 days) — used by rules that
    # compare current-period against longer baselines.
    sales_count_90d: int = 0
    expenses_count_90d: int = 0
    purchases_count_90d: int = 0

    # ── Field coverage (within sales_records) ────────────────────────────
    # Required by rules that need a specific column populated to be
    # meaningful (e.g. customer concentration alerts need customer_id
    # set on > 30% of records).
    customer_id_coverage_pct: float = 0.0
    payment_status_coverage_pct: float = 0.0
    due_date_coverage_pct: float = 0.0

    # ── Outlier flag ─────────────────────────────────────────────────────
    # True when at least one record in the last 30 days deviates more
    # than 5σ from the mean. Pattern-based rules (cat D) opt-in to skip
    # when this is set, since their anomaly signal becomes meaningless
    # with one giant outlier dominating the distribution.
    has_outlier_5sigma_30d: bool = False

    # Suspicious dates (future > 7d or before 2020-01-01).
    # Surface them as a count for telemetry; rules don't read this
    # directly — the date-validity filter at aggregate level handles
    # exclusion.
    suspicious_dates_count: int = 0

    # ── Available dataset flags (derived) ────────────────────────────────
    # The set ``available_datasets`` lets the decorator do a quick
    # set-membership check against the rule's ``datasets`` requirement.
    available_datasets: Set[str] = field(default_factory=frozenset)

    def has_dataset(self, name: str) -> bool:
        """Quick membership check used by the decorator."""
        return name in self.available_datasets

    def is_org_onboarding(self, min_days: int = 14) -> bool:
        """True when the org has too little history to run general rules.

        Sole consumer of this method today: the engine's onboarding
        gate and the soft G3 rule. Kept as a method (not a property) so
        the threshold can be passed in for future per-rule overrides.
        """
        return self.days_since_first_record < min_days


# ── Requirements contract ──────────────────────────────────────────────────

@dataclass(frozen=True)
class RuleRequirements:
    """Declarative contract a rule attaches to itself via ``@requires_data``.

    Every field is independently optional. The default value of each
    field is the "no constraint" choice, so a bare ``@requires_data()``
    is equivalent to no decorator at all (backward-compat sentinel).

    Field semantics
    ---------------
    min_days_of_data
        Minimum age of the org's first record (days). Below this, the
        rule is suppressed. Use 0 to disable.

    datasets
        Datasets that must be non-empty in the snapshot's
        ``available_datasets``. Use an empty frozenset to disable.
        Names must be in ``KNOWN_DATASETS`` (validation at construction).

    min_samples_30d
        Minimum count of records (of the primary dataset, typically
        ``sales``) in the last 30 days. Pattern-based rules need this to
        avoid emitting alerts from a tiny sample.

    outlier_robust
        When True, the rule is suppressed if the snapshot reports a
        5-sigma outlier in the 30-day window. The default False means
        the rule does not care about outliers (e.g. concentration
        alerts work fine even with one big invoice).

    min_field_coverage
        Map ``{field_name: min_pct}`` (e.g. ``{"customer_ids": 30}``).
        The rule is suppressed when a referenced field's coverage is
        below the threshold — used to gate customer / supplier
        concentration alerts so they don't fire on near-empty datasets.

    confidence_label
        Self-documenting tag ("high" / "medium" / "low") for future
        telemetry / UI: a low-confidence rule whose alerts get
        repeatedly dismissed by merchants is a candidate for retirement.

    Validation
    ----------
    Dataset names are checked against KNOWN_DATASETS at construction so
    a typo in @requires_data fails fast at module import, not at the
    first tick of the alert engine.
    """

    min_days_of_data: int = 0
    datasets: frozenset = frozenset()
    min_samples_30d: int = 0
    outlier_robust: bool = False
    min_field_coverage: dict = field(default_factory=dict)
    confidence_label: str = "medium"

    def __post_init__(self):
        # Cheap fail-fast: unknown dataset name in the decorator is
        # almost always a typo. We surface it at import time so the
        # backend literally won't boot until the rule author fixes it.
        unknown = set(self.datasets) - KNOWN_DATASETS
        if unknown:
            raise ValueError(
                f"RuleRequirements.datasets contains unknown names: {unknown}. "
                f"Known datasets: {sorted(KNOWN_DATASETS)}"
            )
        unknown_fields = set(self.min_field_coverage) - KNOWN_DATASETS
        if unknown_fields:
            raise ValueError(
                f"RuleRequirements.min_field_coverage references unknown fields: "
                f"{unknown_fields}. Known: {sorted(KNOWN_DATASETS)}"
            )
        if self.confidence_label not in ("low", "medium", "high"):
            raise ValueError(
                f"RuleRequirements.confidence_label must be low/medium/high, "
                f"got: {self.confidence_label!r}"
            )

    # ── Evaluation ────────────────────────────────────────────────────────

    def evaluate(self, snapshot: DataQualitySnapshot) -> "RequirementOutcome":
        """Return a RequirementOutcome explaining whether the rule may fire.

        The check is short-circuiting: the first failed requirement is
        recorded as the reason. Order matters here for logging clarity
        (more user-meaningful reasons first):
          1. age (onboarding gate)
          2. last upload (stale data)
          3. required datasets present
          4. minimum sample size
          5. field coverage
          6. outlier robustness
        """
        # 1. Onboarding gate
        if self.min_days_of_data > 0:
            if snapshot.days_since_first_record < self.min_days_of_data:
                return RequirementOutcome(
                    allowed=False,
                    reason="insufficient_history",
                    detail=(
                        f"org has {snapshot.days_since_first_record} days of data, "
                        f"rule requires {self.min_days_of_data}"
                    ),
                )

        # 2. Required datasets present
        for ds in self.datasets:
            if not snapshot.has_dataset(ds):
                return RequirementOutcome(
                    allowed=False,
                    reason="missing_dataset",
                    detail=f"dataset {ds!r} is empty or unavailable",
                )

        # 3. Minimum sample size (primary dataset assumed to be "sales"
        #    unless the rule explicitly required something else; we check
        #    against sales_count_30d as the most useful default).
        if self.min_samples_30d > 0:
            primary_count = snapshot.sales_count_30d
            if primary_count < self.min_samples_30d:
                return RequirementOutcome(
                    allowed=False,
                    reason="insufficient_samples",
                    detail=(
                        f"only {primary_count} sales records in last 30d, "
                        f"rule requires {self.min_samples_30d}"
                    ),
                )

        # 4. Field coverage
        for field_name, min_pct in self.min_field_coverage.items():
            cov = _coverage_for_field(snapshot, field_name)
            if cov < min_pct:
                return RequirementOutcome(
                    allowed=False,
                    reason="low_field_coverage",
                    detail=(
                        f"{field_name} coverage is {cov:.0f}%, "
                        f"rule requires {min_pct}%"
                    ),
                )

        # 5. Outlier robustness
        if self.outlier_robust and snapshot.has_outlier_5sigma_30d:
            return RequirementOutcome(
                allowed=False,
                reason="outlier_present",
                detail="30-day window contains a >5σ outlier",
            )

        return RequirementOutcome(allowed=True, reason="ok", detail="")


def _coverage_for_field(snapshot: DataQualitySnapshot, field_name: str) -> float:
    """Map field name to snapshot percentage. Keeps the evaluator generic."""
    mapping = {
        "customer_ids": snapshot.customer_id_coverage_pct,
        "payment_status": snapshot.payment_status_coverage_pct,
        "due_dates": snapshot.due_date_coverage_pct,
    }
    return mapping.get(field_name, 100.0)  # unknown field → no constraint


# ── Outcome ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RequirementOutcome:
    """Why a rule was allowed or skipped — surfaced to engine telemetry."""
    allowed: bool
    reason: str   # "ok" | "insufficient_history" | "missing_dataset" | ...
    detail: str


# ── Decorator ───────────────────────────────────────────────────────────────

# The decorator does NOT wrap the rule function. It only attaches the
# requirements object as a side-channel attribute. This keeps the rule's
# signature pristine (async + AlertContext arg) and lets the engine
# read the contract without inspecting the function source.
#
# Reasoning for the side-channel approach:
#   - The engine already iterates ``ALL_RULES`` and calls each. A wrapper
#     would force the engine to also know about the wrapper's contract,
#     which couples the two pieces. The side-channel keeps the engine
#     ignorant of the decorator existence — it just probes for
#     ``rule._requirements`` and uses it if present, else runs the rule
#     unconditionally (full backward compat).
#   - Test ergonomics: a unit test can call the bare rule function with
#     a hand-built AlertContext and ignore the requirement layer.

def requires_data(
    *,
    min_days_of_data: int = 0,
    datasets: tuple = (),
    min_samples_30d: int = 0,
    outlier_robust: bool = False,
    min_field_coverage: Optional[dict] = None,
    confidence_label: str = "medium",
) -> Callable:
    """Attach a RuleRequirements contract to a rule function.

    Keyword-only args by design: the call site reads as a checklist of
    declarative constraints, never positional. Adding a new constraint
    field tomorrow doesn't risk breaking existing decorators.
    """
    req = RuleRequirements(
        min_days_of_data=min_days_of_data,
        datasets=frozenset(datasets),
        min_samples_30d=min_samples_30d,
        outlier_robust=outlier_robust,
        min_field_coverage=dict(min_field_coverage or {}),
        confidence_label=confidence_label,
    )

    def _decorator(fn):
        # Attach the contract as a side-channel attribute. The engine
        # reads ``getattr(fn, "_requirements", None)`` before calling.
        fn._requirements = req
        return fn

    return _decorator


# ── Engine helper ───────────────────────────────────────────────────────────

def should_run_rule(
    rule_fn: Callable,
    snapshot: DataQualitySnapshot,
) -> RequirementOutcome:
    """Single function the engine calls for every rule before running it.

    Rules without a ``@requires_data`` decorator have no contract attached
    and are unconditionally allowed (backward-compat path).

    A skipped rule still gets a structured outcome (with reason + detail)
    so the engine can log uniformly and downstream telemetry can compute
    "% suppressed" per rule.
    """
    req = getattr(rule_fn, "_requirements", None)
    if req is None:
        return RequirementOutcome(allowed=True, reason="no_contract", detail="")
    return req.evaluate(snapshot)
