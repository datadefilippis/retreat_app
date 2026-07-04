"""
Tool temporal scope registry — Wave 13.6 (Period Integrity).

Each AI chat tool that returns business data has a *temporal nature*:

  ``period_filtered`` — Data is scoped to the request's date window
                        (start_date / end_date, or the period token).
                        These tools are correct to attribute to "the
                        user's selected period" in answers.
                        Example: ``query_business_summary``.

  ``all_time``        — Data is a materialised aggregate over ALL the
                        org's history (e.g. ``customer_metrics`` and
                        ``product_metrics`` collections), refreshed by
                        a background job. Not period-filterable
                        without re-running aggregation on raw records.
                        Example: ``query_top_customers``.

  ``current_state``   — Data reflects the entity state RIGHT NOW
                        (open invoices, draft orders, low stock,
                        unfulfilled deliveries). Not period-filterable
                        because "at this moment" is a single instant.
                        Example: ``query_receivables_payables``.

  ``forward_looking`` — Data covers DATES IN THE FUTURE (upcoming
                        bookings, scheduled rentals, agenda for next
                        N days). Period filtering is supported but the
                        window is anchored AFTER today, not before.
                        Example: ``query_agenda_upcoming``.

  ``meta``            — Tool returns metadata or quality information,
                        not business data per se (e.g. data range,
                        coherence audit).

The Wave 13 audit found the chat AI often misattributed snapshot
data ("top 5 customer" lifetime totals) to the user's currently
filtered period (YTD). Surfacing the scope EXPLICITLY in every tool
response — backed by a system prompt rule — closes that gap without
expensive per-tool refactors.

Public API
----------
    :data:`TOOL_SCOPE`             — full registry mapping tool name → scope
    :func:`get_scope`              — safe lookup, returns ``None`` if unknown
    :func:`attach_temporal_scope`  — post-processor that injects the marker
                                     into a tool's response dict
"""

from __future__ import annotations

from typing import Mapping, Optional


# ── Scope vocabulary ────────────────────────────────────────────────────────

PERIOD_FILTERED = "period_filtered"
ALL_TIME = "all_time"
CURRENT_STATE = "current_state"
FORWARD_LOOKING = "forward_looking"
META = "meta"

#: All valid scope values — useful for assertions and test discipline.
VALID_SCOPES = frozenset({
    PERIOD_FILTERED, ALL_TIME, CURRENT_STATE, FORWARD_LOOKING, META,
})


# ── Tool → scope mapping ────────────────────────────────────────────────────
#
# Source of truth for what each chat tool returns. Keep in sync with the
# tool registry in modules/{cashflow_monitor,customer_insights,
# product_catalog,commerce}/ai_tools.py. The Wave 13 audit doc has the
# full table of tools and their scopes (Section "All AI tools").
#
# Conventions:
#   * Only list tools that exist in production. Future tools added via
#     module registry should be added here in the same commit that
#     introduces them.
#   * When in doubt, OMIT — unknown tools surface as scope=None at
#     runtime, which the dispatcher treats as "leave alone, don't claim".

TOOL_SCOPE: Mapping[str, str] = {
    # ── Cashflow summary surface — period-filtered ──────────────────────
    "query_business_summary":     PERIOD_FILTERED,
    "query_cashflow_summary":     PERIOD_FILTERED,
    "query_revenue":              PERIOD_FILTERED,
    "query_expenses":             PERIOD_FILTERED,
    "query_purchases":            PERIOD_FILTERED,
    "query_fixed_costs":          PERIOD_FILTERED,
    # Wave 14.HOTFIX4 (F2 + F3)
    "query_fixed_costs_detail":   PERIOD_FILTERED,
    "query_health_score_breakdown": PERIOD_FILTERED,
    "query_cashflow":             PERIOD_FILTERED,
    "query_period_comparison":    PERIOD_FILTERED,
    "query_monthly_trend":        PERIOD_FILTERED,
    "query_revenue_forecast":     PERIOD_FILTERED,
    "query_anomaly_detection":    PERIOD_FILTERED,
    "query_data_coherence":       PERIOD_FILTERED,
    # Wave 13.5 made this period-aware
    "query_smart_brief":          PERIOD_FILTERED,

    # ── Cashflow current-state surface ──────────────────────────────────
    "query_receivables_payables": CURRENT_STATE,
    "query_late_payers":          CURRENT_STATE,

    # ── Meta tools (no temporal scope) ──────────────────────────────────
    "get_data_range":             META,
    "query_data_quality_audit":   META,

    # ── Customer insights ───────────────────────────────────────────────
    # Period-filtered (accepts explicit dates):
    "query_customer_summary":             PERIOD_FILTERED,
    "query_customer_acquisition_trend":   PERIOD_FILTERED,  # months_back-based
    # All-time materialised snapshots (customer_metrics collection):
    "query_top_customers":                ALL_TIME,
    "query_customer_segments":            ALL_TIME,
    "query_customer_profile":             ALL_TIME,
    "query_churn_risk":                   ALL_TIME,
    "query_customer_product_affinity":    ALL_TIME,
    "query_customer_concentration":       ALL_TIME,

    # ── Product catalog ─────────────────────────────────────────────────
    # All-time / materialised:
    "query_product_analytics":            ALL_TIME,
    "query_product_margins":              ALL_TIME,
    "query_product_recommendations":      ALL_TIME,
    "query_low_stock_products":           CURRENT_STATE,
    "query_underperforming_events":       ALL_TIME,
    "query_idle_rentals":                 ALL_TIME,
    "query_high_cancellation_products":   ALL_TIME,
    # Note: query_product_trend already sets _temporal_scope explicitly
    # in its implementation (Wave 13.5) — listed here for completeness
    # but the dispatcher's "only-set-if-missing" rule means the tool's
    # own value wins (which is what we want: more precise scope label).
    "query_product_trend":                ALL_TIME,

    # ── Commerce operations ─────────────────────────────────────────────
    # Period-filtered:
    "query_order_pipeline":               PERIOD_FILTERED,
    "query_orders_dashboard":             PERIOD_FILTERED,
    "query_aov_trend":                    PERIOD_FILTERED,
    "query_cancellations_breakdown":      PERIOD_FILTERED,
    "query_channels_performance":         PERIOD_FILTERED,
    "query_new_vs_returning_split":       PERIOD_FILTERED,
    "query_basket_size_distribution":     PERIOD_FILTERED,
    "query_store_performance":            PERIOD_FILTERED,
    "query_booking_utilization":          PERIOD_FILTERED,
    "query_rental_utilization":           PERIOD_FILTERED,
    "query_coupon_usage":                 PERIOD_FILTERED,
    "query_course_engagement":            PERIOD_FILTERED,
    # Current-state snapshots:
    "query_fulfillment_status":           CURRENT_STATE,
    "query_payment_pipeline":             CURRENT_STATE,
    "query_catalog_health":               CURRENT_STATE,
    "query_dormant_products":             CURRENT_STATE,
    "query_stores_overview":              CURRENT_STATE,  # lifetime + last 30d
    # Forward-looking surfaces:
    "query_event_metrics":                FORWARD_LOOKING,
    "query_agenda_today":                 CURRENT_STATE,
    "query_agenda_upcoming":              FORWARD_LOOKING,
    "query_agenda_summary":               CURRENT_STATE,   # today/tomorrow/week
    "query_free_slots":                   FORWARD_LOOKING,
    "query_blocked_periods":              FORWARD_LOOKING,
    "query_rentals_today":                CURRENT_STATE,
    "query_rentals_upcoming":             FORWARD_LOOKING,
    "query_rentals_returning":            FORWARD_LOOKING,
    "query_rental_availability":          FORWARD_LOOKING,
    "query_rental_pipeline":              FORWARD_LOOKING,
    "query_events_calendar":              FORWARD_LOOKING,
}


# ── Public helpers ──────────────────────────────────────────────────────────


def get_scope(tool_name: str) -> Optional[str]:
    """Return the registered scope for ``tool_name`` or ``None``.

    ``None`` is the safe default: the dispatcher will NOT inject any
    marker, leaving the tool's response untouched. Unregistered tools
    are conservatively un-marked rather than guessed.
    """
    return TOOL_SCOPE.get(tool_name)


def attach_temporal_scope(tool_name: str, result):
    """Inject ``_temporal_scope`` into a tool's return when missing.

    Rules:
      * If ``result`` is not a dict — return unchanged. Defensive: some
        tools occasionally return raw lists or None; we never mutate
        those silently.
      * If the tool already set ``_temporal_scope`` (e.g.
        ``query_product_trend`` does this from Wave 13.5) we preserve
        the tool's value — it's likely a more precise label (e.g.
        ``materialized_30d_vs_prior_30d`` vs the registry's ``all_time``).
      * If the tool is not in the registry — return unchanged. We do
        NOT guess; an unknown tool has no contract yet.

    The function is pure: it returns a NEW dict when injection happens
    so callers don't accidentally rely on identity. (Mutating the dict
    in place would work today but cripples future caching layers.)
    """
    if not isinstance(result, dict):
        return result
    if "_temporal_scope" in result:
        return result
    scope = TOOL_SCOPE.get(tool_name)
    if scope is None:
        return result
    # Shallow copy + add the field — preserves all other keys including
    # the tool's existing audit / epistemic markers.
    return {**result, "_temporal_scope": scope}
