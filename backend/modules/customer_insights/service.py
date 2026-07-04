"""Service layer — orchestrates pure formulas + repository reads.

The legacy ``modules.customers_light.service`` is unchanged and remains
the writer of the materialized ``customer_metrics`` collection. This
service is read-only: it pulls the materialized snapshot for "all-time"
KPIs and runs period-aware Mongo aggregations for "in window" KPIs,
then assembles the response shape that the Phase 2 UI consumes.

Three response builders:

    build_overview(org_id, period)
        Headline KPIs + segment distribution + concentration + smart
        suggestion candidates. The dashboard widget and the main
        Insights page both read from this.

    build_customer_list(org_id, period, filters, page)
        Paginated customer table with optional segment / status / min
        revenue filters.

    build_cohort_response(org_id, bucket, horizon)
        Cohort retention table. Uses the cohort module for math.

All response shapes are JSON-serialisable dicts. No Pydantic models on
the boundary so the FastAPI router can render them directly without an
extra type hop.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any, Optional

from . import formulas as F
from . import repository as R
from .cohort import build_cohort_table
from .period_filter import PeriodWindow, parse_period, previous_period

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Overview — KPI strip + delta
# ──────────────────────────────────────────────────────────────────────────────


async def build_overview(
    org_id: str,
    period: str = "30d",
    *,
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    today_override: Optional[date] = None,
) -> dict:
    """Assemble the headline KPIs with period-vs-previous deltas.

    Args:
        org_id: Caller's organization scope.
        period: ``"30d"`` / ``"90d"`` / ``"12m"`` / ``"all"`` / ``"custom"``.
        custom_start / custom_end: Only consulted when ``period == "custom"``.
        today_override: Override today's date (testability).

    Returns:
        ``{"period": {...}, "compare": {...}, "kpis": {...}, "segments": [...],
            "concentration": {...}, "suggested_actions": [...]}``.

        ``kpis`` is a dict where each value is itself a 3-tuple-shaped
        object ``{"value": .., "previous": .., "delta_pct": ..}``.
        ``delta_pct`` is None when the previous window had no data.
    """
    today = today_override or date.today()
    window = parse_period(period, start=custom_start, end=custom_end, today=today)
    previous = previous_period(window)

    # Period-aware aggregations — current and previous in parallel.
    current_agg, previous_agg = await asyncio.gather(
        R.aggregate_revenue_in_period(org_id, window),
        R.aggregate_revenue_in_period(org_id, previous),
        return_exceptions=True,
    )
    current_agg = _safe_list(current_agg)
    previous_agg = _safe_list(previous_agg)

    # Period-snapshot cardinals — counted independently from the
    # all-time aggregates so "active customers at end of window" is
    # truthful even when no purchases happened in the period itself.
    new_curr_t, new_prev_t, active_curr_t, active_prev_t = await asyncio.gather(
        R.count_new_customers_in_period(org_id, window),
        R.count_new_customers_in_period(org_id, previous),
        R.count_active_customers_at(org_id, window.end),
        R.count_active_customers_at(org_id, previous.end),
        return_exceptions=True,
    )
    new_curr = _safe_int(new_curr_t)
    new_prev = _safe_int(new_prev_t)
    active_curr = _safe_int(active_curr_t)
    active_prev = _safe_int(active_prev_t)

    # All-time materialised metrics (for status counts / concentration).
    all_time_metrics = await _safe_legacy_metrics(org_id)

    # ── Compose KPIs ────────────────────────────────────────────────
    revenue_curr = sum(a["total_revenue"] for a in current_agg)
    revenue_prev = sum(a["total_revenue"] for a in previous_agg)
    customers_curr = len(current_agg)
    customers_prev = len(previous_agg)

    avg_curr = F.avg_customer_value(revenue_curr, customers_curr)
    avg_prev = F.avg_customer_value(revenue_prev, customers_prev)

    revenues_curr = [a["total_revenue"] for a in current_agg]
    top10_curr = F.top_n_share_pct(revenues_curr, 10)
    top10_prev = F.top_n_share_pct(
        [a["total_revenue"] for a in previous_agg], 10
    )

    at_risk_count = sum(
        1 for m in all_time_metrics if m.get("churn_risk_score", 0) >= 60
    )
    inactive_count = sum(
        1 for m in all_time_metrics if m.get("segment") == "inactive"
    )
    inactive_rate = F.inactive_rate_pct(inactive_count, len(all_time_metrics))

    kpis: dict[str, dict[str, Any]] = {
        "active_customers": _kpi(active_curr, active_prev),
        "new_customers": _kpi(new_curr, new_prev),
        "purchasing_customers": _kpi(customers_curr, customers_prev),
        "total_revenue": _kpi(round(revenue_curr, 2), round(revenue_prev, 2)),
        "avg_customer_value": _kpi(avg_curr, avg_prev),
        "top_10_share_pct": _kpi(top10_curr, top10_prev),
        "at_risk_count": _kpi(at_risk_count, None),
        "inactive_rate_pct": _kpi(inactive_rate, None),
    }

    # ── Segment distribution + concentration (all-time) ─────────────
    segments = _segment_breakdown(all_time_metrics)
    concentration = _concentration_breakdown(all_time_metrics)

    # ── Smart suggestion candidates (Phase 4 surface) ───────────────
    suggested = _suggested_actions(all_time_metrics)

    return {
        "period": _window_dict(window),
        "compare": _window_dict(previous),
        "kpis": kpis,
        "segments": segments,
        "concentration": concentration,
        "suggested_actions": suggested,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Customer list — paginated + filtered
# ──────────────────────────────────────────────────────────────────────────────


async def build_customer_list(
    org_id: str,
    *,
    segment: Optional[str] = None,
    status: Optional[str] = None,
    min_revenue: float = 0.0,
    has_email: Optional[bool] = None,
    has_phone: Optional[bool] = None,
    # Wave GDPR-Commerce CI-admin-vis (2026-05-19) — new filters.
    # ``has_account`` filters by whether the customer has a registered
    # account on the storefront (vs guest-only orders).
    # ``marketing_opted_in`` filters by current marketing consent state
    # (accepted_marketing_at set AND not later revoked).
    # Both default None = no filter, preserving legacy behaviour.
    has_account: Optional[bool] = None,
    marketing_opted_in: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Paginated customer list with active filters applied in-memory.

    The list reads the all-time materialised ``customer_metrics``; the
    period filter is intentionally NOT applied here because the table
    represents lifetime customer state. Period filtering lives on the
    overview KPIs only.

    Wave GDPR-Commerce CI-admin-vis: the rows are enriched in-place
    with 3 new fields derived from a real-time join against
    ``customer_accounts``:
        - has_account: bool
        - marketing_opted_in: bool
        - account_created_at: Optional[str] (ISO UTC)

    We join real-time (single bulk query per request) rather than
    pre-materializing in ``customer_metrics`` because the marketing
    toggle from the customer portal changes in real time and the admin
    must see it immediately, not at the next refresh job tick.
    """
    from . import repository
    from repositories import customer_repository

    metrics = await repository.find_metrics_by_org(org_id, segment=segment, limit=5000)

    # Hydrate contact fields (email / phone) from shared customers
    # collection so we can apply has_email / has_phone filters and the
    # frontend can render outreach buttons.
    customers = await customer_repository.find_by_org(
        org_id, active_only=False, limit=5000,
    )
    contact_map = {c.id: c for c in customers}

    # ── Wave GDPR-Commerce CI-admin-vis — account + marketing join ──
    # Collect every distinct customer_account_id referenced by the
    # customers in scope, then bulk-fetch the corresponding accounts in
    # a SINGLE query. This is bounded (≤5K accounts per org for SME);
    # measured <100ms on a real org dataset.
    #
    # Soft-fail: if the lookup raises (DB hiccup), we proceed with an
    # empty account_map → ``has_account`` and ``marketing_opted_in``
    # default to False for every row. The page still renders normally,
    # just without the new visibility — never blocks the admin.
    account_ids = []
    for c in customers:
        acc_id = getattr(c, "customer_account_id", None)
        if acc_id:
            account_ids.append(acc_id)
    account_map: dict = {}
    if account_ids:
        try:
            from database import customer_accounts_collection
            cursor = customer_accounts_collection.find(
                {"id": {"$in": account_ids}, "organization_id": org_id},
                {
                    "_id": 0,
                    "id": 1,
                    "created_at": 1,
                    "accepted_marketing_at": 1,
                    "marketing_revoked_at": 1,
                },
            )
            async for doc in cursor:
                account_map[doc["id"]] = doc
        except Exception as exc:
            # Log but don't fail the whole list — degraded visibility
            # is better than a 500 on the admin page.
            import logging
            logging.getLogger(__name__).warning(
                "CI-admin-vis: customer_accounts lookup failed for "
                "org=%s (%d ids): %s — falling back to no-account",
                org_id, len(account_ids), exc,
            )

    def _compute_opted_in(accepted_at, revoked_at):
        """Shared opt-in logic — keeps the "most recent wins" semantics
        identical between customer_account fast-path and CRM customer
        fallback. Documented once so future toggles (e.g. the portal
        toggle of Piece 1a) can call the same helper.

        opted_in iff there's an accepted_at AND it's strictly newer
        than any revoked_at. Equal timestamps (rare) are treated as
        revoked-wins for conservative GDPR posture.
        """
        if not accepted_at:
            return False
        if revoked_at and not (accepted_at > revoked_at):
            return False
        return True

    def _resolve_account_state(contact_obj):
        """Map a single customer to its marketing + account state.

        Returns ``(has_account, marketing_opted_in, account_created_at)``.

        Lookup order (most-trustworthy first):
          1. ``customer_account`` fast-path — used when the customer is
             REGISTERED (has a customer_account_id). The portal login +
             signup write here, so this is the freshest snapshot for
             logged-in users.
          2. ``customer`` (CRM) fallback — used for GUEST customers AND
             as a secondary signal for registered ones if the account
             lookup returned nothing. submit_order_request and the Piece
             1b unsubscribe link write here so every checkout opt-in /
             link-revoke is visible in the admin table.

        Edge cases handled:
          - Guest with NO marketing event ever  → (False, False, None)
          - Guest who opted-in at checkout      → (False, True,  None)
          - Guest who later clicks unsubscribe  → (False, False, None)
          - Registered, account drift (FK exists but doc missing)
              → fall back to CRM lookup, has_account still True since
                the FK says so.
        """
        if not contact_obj:
            return (False, False, None)

        # ── 1. Try the customer_account fast-path (registered customers) ──
        # has_account follows the PHYSICAL presence of the account doc
        # (not just the FK). Rationale documented in the legacy
        # "legacy data drift" branch: when the FK is set but the doc
        # is missing (deleted manually, batch lookup failure, etc.),
        # the merchant filter "has_account=true" should NOT include
        # the orphan. Preserves the contract that pre-dates this
        # refactor.
        acc_id = getattr(contact_obj, "customer_account_id", None)
        acc = account_map.get(acc_id) if acc_id else None
        has_account = bool(acc)
        created_iso = None
        if acc:
            accepted_at = acc.get("accepted_marketing_at")
            revoked_at = acc.get("marketing_revoked_at")
            # Extract account created_at regardless of opt-in outcome
            # so the "Account registrato dal …" row stays informative.
            created_raw = acc.get("created_at")
            if created_raw is not None:
                try:
                    created_iso = (
                        created_raw.isoformat()
                        if hasattr(created_raw, "isoformat")
                        else str(created_raw)
                    )
                except Exception:
                    created_iso = None
            if _compute_opted_in(accepted_at, revoked_at):
                return (True, True, created_iso)
            # account exists but not opted-in → continue to CRM as
            # secondary signal (e.g. customer opted-in at checkout
            # BEFORE the portal account was created — rare but real).

        # ── 2. CRM Customer fallback (covers guests AND the safety
        # net for registered customers whose account is missing the
        # marketing field for any reason) ──────────────────────────────
        # Type-guard: getattr on a MagicMock (used by some tests as a
        # stub Customer) returns a chained MagicMock rather than None,
        # which would crash the comparison in _compute_opted_in. Only
        # accept string timestamps; coerce anything else to None.
        crm_accepted = getattr(contact_obj, "accepted_marketing_at", None)
        if not isinstance(crm_accepted, str):
            crm_accepted = None
        crm_revoked = getattr(contact_obj, "marketing_revoked_at", None)
        if not isinstance(crm_revoked, str):
            crm_revoked = None
        opted_in = _compute_opted_in(crm_accepted, crm_revoked)

        return (has_account, opted_in, created_iso)

    rows: list[dict] = []
    for m in metrics:
        cid = m.get("customer_id")
        contact = contact_map.get(cid)
        email = getattr(contact, "email", None) if contact else None
        phone = getattr(contact, "phone", None) if contact else None

        # CI-admin-vis: resolve account/marketing state per row
        row_has_account, row_marketing, row_account_at = _resolve_account_state(contact)

        # Filter chain
        if status and m.get("customer_status") != status:
            continue
        if min_revenue > 0 and (m.get("total_revenue") or 0) < min_revenue:
            continue
        if has_email is True and not email:
            continue
        if has_email is False and email:
            continue
        if has_phone is True and not phone:
            continue
        if has_phone is False and phone:
            continue
        # CI-admin-vis: new filters. None means "no filter applied".
        if has_account is not None and row_has_account != has_account:
            continue
        if marketing_opted_in is not None and row_marketing != marketing_opted_in:
            continue
        if search:
            needle = search.strip().lower()
            haystack = (m.get("customer_name") or "").lower()
            if needle and needle not in haystack:
                continue

        rows.append({
            **m,
            "email": email,
            "phone": phone,
            "has_account": row_has_account,
            "marketing_opted_in": row_marketing,
            "account_created_at": row_account_at,
        })

    # ── F4 — inclusione lead/iscritti senza storico acquisti ──────────────
    # La lista nasce da ``customer_metrics`` (derivato dagli ordini): un
    # cliente CRM SENZA acquisti (es. iscritto via form newsletter) non avrebbe
    # riga e resterebbe invisibile. Lo aggiungiamo come "lead" (metriche zero)
    # così è visibile e filtrabile in Customer Insights — in particolare via
    # ``marketing_opted_in=true``. Coerenza coi filtri:
    #   - segment: lead inclusi solo se nessun filtro segment o segment=='lead';
    #   - status / min_revenue: un lead non ha status né revenue → se quei
    #     filtri sono attivi i lead sono esclusi (comportamento corretto).
    if segment in (None, "lead") and status is None and min_revenue <= 0:
        # seen_ids = acquirenti da escludere dai lead. Con segment=None i
        # ``metrics`` sono GIÀ il set completo → niente query extra. Con
        # segment='lead' i metrics sono filtrati a [], quindi serve il set
        # globale (così un acquirente non torna come lead).
        if segment is None:
            seen_ids = {m.get("customer_id") for m in metrics}
        else:
            seen_ids = await repository.find_metric_customer_ids(org_id)
        for c in customers:
            cid = getattr(c, "id", None)
            if not cid or cid in seen_ids:
                continue
            email = getattr(c, "email", None)
            phone = getattr(c, "phone", None)
            row_has_account, row_marketing, row_account_at = _resolve_account_state(c)

            if has_email is True and not email:
                continue
            if has_email is False and email:
                continue
            if has_phone is True and not phone:
                continue
            if has_phone is False and phone:
                continue
            if has_account is not None and row_has_account != has_account:
                continue
            if marketing_opted_in is not None and row_marketing != marketing_opted_in:
                continue
            if search:
                needle = search.strip().lower()
                name_l = (getattr(c, "name", "") or "").lower()
                if needle and needle not in name_l:
                    continue

            rows.append({
                "customer_id": cid,
                "customer_name": getattr(c, "name", None),
                "segment": "lead",
                "customer_status": None,
                "total_revenue": 0,
                "transaction_count": 0,
                "avg_transaction_value": 0,
                "last_purchase_date": None,
                "days_since_last_purchase": None,
                "churn_risk_score": None,
                "trend_direction": None,
                "email": email,
                "phone": phone,
                "has_account": row_has_account,
                "marketing_opted_in": row_marketing,
                "account_created_at": row_account_at,
            })

    total = len(rows)
    page = max(page, 1)
    page_size = max(min(page_size, 200), 1)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "rows": rows[start:end],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Cohort response
# ──────────────────────────────────────────────────────────────────────────────


async def build_cohort_response(
    org_id: str,
    *,
    bucket: str = "month",
    horizon: int = 12,
    since: Optional[str] = None,
) -> dict:
    """Compute the cohort retention table for the org.

    Returns ``{"bucket": "month", "horizon": 12, "rows": [...]}``. Each
    row is dict-shaped (not the dataclass) so it serialises directly.
    """
    purchases = await R.fetch_purchase_dates_per_customer(org_id, since=since)
    rows = build_cohort_table(purchases, bucket=bucket, horizon=horizon)
    return {
        "bucket": bucket,
        "horizon": horizon,
        "rows": [
            {
                "acquisition_bucket": r.acquisition_bucket,
                "size": r.size,
                "retention": r.retention,
                "retention_pct": r.retention_pct,
            }
            for r in rows
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Action logging (writes audit_logs)
# ──────────────────────────────────────────────────────────────────────────────


async def log_outreach_action(
    org_id: str,
    user_id: str,
    customer_id: str,
    *,
    channel: str,
    template: Optional[str] = None,
    status: str = "opened",
) -> None:
    """Persist a customer outreach event to ``audit_logs``.

    The Phase 3 deep-link buttons fire this when the merchant opens the
    composer (mailto: / wa.me) — we don't know if they actually sent
    anything, just that they triggered. ``status`` defaults to "opened"
    accordingly.
    """
    try:
        from repositories import audit_repository
        from models import AuditLog

        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="customer.outreach.sent",
            resource_type="customer",
            resource_id=customer_id,
            details={
                "channel": channel,
                "template": template,
                "status": status,
            },
        ))
    except Exception as exc:
        # Best-effort: outreach should never fail because audit logging blew up.
        logger.warning(
            "customer_insights: audit log write failed for customer=%s: %s",
            customer_id, exc,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Internal composers
# ──────────────────────────────────────────────────────────────────────────────


def _kpi(value, previous):
    """Wrap a value/previous pair as a UI-ready KPI block."""
    delta = (
        F.percentage_delta(float(value), float(previous))
        if previous is not None else None
    )
    return {
        "value": value,
        "previous": previous,
        "delta_pct": delta,
    }


def _window_dict(w: PeriodWindow) -> dict:
    return {
        "start": w.start_iso,
        "end": w.end_iso,
        "label": w.label,
        "days": w.days,
    }


def _segment_breakdown(metrics: list[dict]) -> list[dict]:
    """Aggregate count + revenue per segment, with share of total."""
    if not metrics:
        return []
    total = sum(m.get("total_revenue") or 0 for m in metrics)
    by_seg: dict[str, dict] = {}
    for m in metrics:
        s = m.get("segment") or "unknown"
        rev = m.get("total_revenue") or 0
        if s not in by_seg:
            by_seg[s] = {"segment": s, "count": 0, "revenue": 0.0}
        by_seg[s]["count"] += 1
        by_seg[s]["revenue"] = round(by_seg[s]["revenue"] + rev, 2)
    for v in by_seg.values():
        v["pct_of_revenue"] = round(
            (v["revenue"] / total * 100) if total > 0 else 0, 1
        )
    return list(by_seg.values())


def _concentration_breakdown(metrics: list[dict]) -> dict:
    """Top-5 / top-10 / Pareto slices for the concentration KPI."""
    if not metrics:
        return {
            "total_customers": 0,
            "total_revenue": 0.0,
            "top_5_share_pct": 0.0,
            "top_10_share_pct": 0.0,
        }
    revenues = [m.get("total_revenue") or 0 for m in metrics]
    return {
        "total_customers": len(metrics),
        "total_revenue": round(sum(revenues), 2),
        "top_5_share_pct": F.top_n_share_pct(revenues, 5),
        "top_10_share_pct": F.top_n_share_pct(revenues, 10),
    }


def _suggested_actions(metrics: list[dict]) -> list[dict]:
    """Return up to 3 deterministic next-step suggestions.

    These are *candidates* — the Phase 4 frontend renders them with
    "Skip" / "Do it" controls and the audit log de-duplication runs at
    click time. We just compute the data here.
    """
    if not metrics:
        return []

    suggestions: list[dict] = []

    at_risk = [m for m in metrics if m.get("customer_status") == "at_risk"]
    if len(at_risk) >= 1:
        suggestions.append({
            "trigger": "at_risk_followup",
            "count": len(at_risk),
            "preview_customer_ids": [m["customer_id"] for m in at_risk[:3]],
            "template": "at_risk_followup",
        })

    new_seg = [m for m in metrics if m.get("segment") == "new"]
    if len(new_seg) >= 1:
        suggestions.append({
            "trigger": "new_welcome",
            "count": len(new_seg),
            "preview_customer_ids": [m["customer_id"] for m in new_seg[:3]],
            "template": "new_welcome",
        })

    top_seg = [m for m in metrics if m.get("segment") == "top"]
    if len(top_seg) >= 1:
        suggestions.append({
            "trigger": "top_personal_note",
            "count": len(top_seg),
            "preview_customer_ids": [m["customer_id"] for m in top_seg[:3]],
            "template": "top_personal_note",
        })

    return suggestions


# ──────────────────────────────────────────────────────────────────────────────
# Defensive helpers (asyncio.gather returns exceptions when caller asks)
# ──────────────────────────────────────────────────────────────────────────────


async def _safe_legacy_metrics(org_id: str) -> list[dict]:
    """Fetch the all-time materialised metrics. Tolerates DB issues."""
    try:
        from . import repository
        return await repository.find_metrics_by_org(org_id, limit=5000)
    except Exception as exc:
        logger.warning(
            "customer_insights: metrics fetch failed: %s", exc,
        )
        return []


def _safe_list(value):
    if isinstance(value, Exception):
        logger.warning("customer_insights: gather sub-task failed: %s", value)
        return []
    return value or []


def _safe_int(value):
    if isinstance(value, Exception):
        logger.warning("customer_insights: gather sub-task failed: %s", value)
        return 0
    return int(value or 0)
