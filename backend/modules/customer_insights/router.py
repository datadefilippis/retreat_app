"""FastAPI router for the new Customer Insights API.

Six endpoints, all org-scoped via ``get_current_user``:

  GET  /api/customer-insights/overview            period-aware KPIs + delta
  GET  /api/customer-insights/customers           paginated table + filters
  GET  /api/customer-insights/cohorts             retention table
  GET  /api/customer-insights/customer/{id}/timeline    drill-down events
  GET  /api/customer-insights/export              streaming CSV
  POST /api/customer-insights/actions/log         outreach action audit

The legacy ``/modules/customers_light/*`` endpoints stay alive
unchanged — the AI tools and the legacy UI continue to call them.
The new UI in Phase 2 will switch its base URL from
``/modules/customers_light`` to ``/customer-insights``.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from auth import get_current_user

from . import service

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/customer-insights", tags=["Customer Insights"])


def _require_cross_sell_module():
    """MD2 — il cross-sell appartiene a customers_light."""
    from services.module_access import require_module
    return require_module("cross_sell")


# ──────────────────────────────────────────────────────────────────────────────
# 1. Overview — KPI strip + delta + segments + concentration
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/overview")
async def overview(
    period: str = Query("30d", description="7d | 30d | 90d | 180d | 12m | 24m | all | custom"),
    custom_start: Optional[str] = Query(None, description="ISO date — only when period=custom"),
    custom_end: Optional[str] = Query(None, description="ISO date — only when period=custom"),
    current_user: dict = Depends(get_current_user),
):
    """KPIs for the period + delta vs immediately preceding window.

    Response shape (truncated):
        {
          "period":  {"start": ..., "end": ..., "label": "30d", "days": 30},
          "compare": {"start": ..., "end": ..., "label": "previous-30d", ...},
          "kpis": {
            "active_customers":    {"value": 47, "previous": 42, "delta_pct": 11.9},
            "new_customers":       {"value":  5, "previous":  3, "delta_pct": 66.7},
            ... (8 KPIs total)
          },
          "segments":      [{"segment": "top", "count": 5, "revenue": 12000.0, ...}],
          "concentration": {"top_5_share_pct": 47.3, "top_10_share_pct": 68.1, ...},
          "suggested_actions": [
            {"trigger": "at_risk_followup", "count": 3, "preview_customer_ids": [...]}
          ]
        }

    Never raises Stripe-style errors at the caller; aggregator failures
    degrade to zero-counts so the UI can still render.
    """
    org_id = current_user["organization_id"]
    return await service.build_overview(
        org_id,
        period=period,
        custom_start=custom_start,
        custom_end=custom_end,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 2. Customer list — paginated + filtered
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/customers")
async def customers(
    segment: Optional[str] = Query(None, description="top | active | occasional | inactive | new"),
    customer_status: Optional[str] = Query(None, description="healthy | watch | at_risk | lost"),
    min_revenue: float = Query(0.0, ge=0),
    has_email: Optional[bool] = Query(None),
    has_phone: Optional[bool] = Query(None),
    # Wave GDPR-Commerce CI-admin-vis (2026-05-19) — two new filters.
    # Both default None = no filter applied → preserves the legacy
    # response shape for clients that don't pass them.
    has_account: Optional[bool] = Query(
        None,
        description="Filter by whether the customer has a registered storefront account",
    ),
    marketing_opted_in: Optional[bool] = Query(
        None,
        description="Filter by current marketing consent state (accepted AND not later revoked)",
    ),
    search: Optional[str] = Query(None, description="Substring match on customer_name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Paginated customer table with the full filter set.

    Note: filters apply to all-time materialised metrics. The period
    selector on the page filters the OVERVIEW KPIs only — the table
    represents lifetime customer state, by design.
    """
    org_id = current_user["organization_id"]
    return await service.build_customer_list(
        org_id,
        segment=segment,
        status=customer_status,
        min_revenue=min_revenue,
        has_email=has_email,
        has_phone=has_phone,
        has_account=has_account,
        marketing_opted_in=marketing_opted_in,
        search=search,
        page=page,
        page_size=page_size,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 3. Cohorts — retention table
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/cohorts")
async def cohorts(
    bucket: str = Query("month", pattern="^(month|quarter|week)$"),
    horizon: int = Query(12, ge=1, le=24),
    since: Optional[str] = Query(None, description="ISO date floor for purchases"),
    current_user: dict = Depends(get_current_user),
):
    """Cohort retention table.

    For micro-merchants with months of history, ``bucket=month`` and
    ``horizon=12`` is the meaningful default. Larger merchants can
    switch to ``bucket=quarter`` to fit the page.
    """
    org_id = current_user["organization_id"]
    return await service.build_cohort_response(
        org_id, bucket=bucket, horizon=horizon, since=since,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 4. Customer timeline — drill-down for slide-over
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/customer/{customer_id}/timeline")
async def customer_timeline(
    customer_id: str,
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Combined orders + sales records for a customer, descending date.

    Returns ``{"events": [{"kind": "order"|"sale", "date": ..., ...}]}``.
    """
    org_id = current_user["organization_id"]
    from . import repository as R
    events = await R.fetch_customer_timeline(org_id, customer_id, limit=limit)
    if not events:
        # Surfaces 404 only when there's neither an order nor a sale; an
        # empty list is also valid (legacy customers with no movement).
        return {"events": []}
    return {"events": events}


# ──────────────────────────────────────────────────────────────────────────────
# 5. CSV export — streaming
# ──────────────────────────────────────────────────────────────────────────────


_CSV_COLUMNS = [
    "customer_id",
    "customer_name",
    "email",
    "phone",
    "segment",
    "customer_status",
    "total_revenue",
    "transaction_count",
    "last_purchase_date",
    "days_since_last_purchase",
    "churn_risk_score",
    "trend_direction",
    # Wave GDPR-Commerce CI-admin-vis (2026-05-19) — 3 new columns
    # appended at the END so legacy CSV consumers reading by index keep
    # working. Marketing tooling (e.g. Mailchimp / Brevo imports) can
    # filter the export to "marketing_opted_in=True" rows.
    "has_account",
    "marketing_opted_in",
    "account_created_at",
    # Wave GDPR-Commerce Piece 1b (2026-05-19) — signed unsubscribe URL.
    # Empty string for rows without a valid email. Mailchimp / Brevo can
    # consume this column as a merge tag (``{{unsubscribe_url}}``) in
    # campaign footers, satisfying GDPR Art. 7(3) symmetry: the customer
    # can revoke marketing consent with one click, no login required.
    "unsubscribe_url",
]


@router.get("/export")
async def export_customers(
    segment: Optional[str] = None,
    customer_status: Optional[str] = None,
    min_revenue: float = Query(0.0, ge=0),
    has_email: Optional[bool] = None,
    has_phone: Optional[bool] = None,
    # CI-admin-vis: mirror the /customers endpoint so the export
    # respects the same filters; default None preserves legacy behaviour.
    has_account: Optional[bool] = None,
    marketing_opted_in: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Export the filtered customer list as CSV.

    Shares the same filter parameters as ``/customers``. Returns a
    StreamingResponse with ``Content-Disposition: attachment`` so the
    browser triggers a download.

    Audited via ``customer.export.csv`` in audit_logs.
    """
    org_id = current_user["organization_id"]
    user_id = current_user.get("user_id") or current_user.get("id") or "unknown"

    # Load all matching rows (no pagination on export — the merchant wants
    # the whole filtered set in one file).
    data = await service.build_customer_list(
        org_id,
        segment=segment,
        status=customer_status,
        min_revenue=min_revenue,
        has_email=has_email,
        has_phone=has_phone,
        has_account=has_account,
        marketing_opted_in=marketing_opted_in,
        search=search,
        page=1,
        page_size=10_000,
    )

    # Audit (best-effort).
    try:
        from repositories import audit_repository
        from models import AuditLog
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="customer.export.csv",
            resource_type="customer",
            resource_id="batch",
            details={
                "row_count": data["total"],
                "filters": {
                    "segment": segment,
                    "status": customer_status,
                    "min_revenue": min_revenue,
                    "has_email": has_email,
                    "has_phone": has_phone,
                    "has_account": has_account,
                    "marketing_opted_in": marketing_opted_in,
                    "search": search,
                },
            },
        ))
    except Exception as exc:
        logger.warning(
            "customer_insights: audit write failed for export: %s", exc,
        )

    # Wave GDPR-Commerce Piece 1b — lazy import keeps this module
    # importable even if the optional unsubscribe helper has issues
    # at startup (the column then falls back to "").
    try:
        from core.marketing_unsubscribe_token import build_unsubscribe_url
        _can_sign_unsubscribe = True
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(
            "customer_insights: unsubscribe URL helper unavailable: %s", exc,
        )
        build_unsubscribe_url = None
        _can_sign_unsubscribe = False

    def _row_iter():
        # ``csv.writer`` writes to a file-like; we adapt with a tiny
        # in-memory buffer per row so the response can stream.
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(_CSV_COLUMNS)
        yield buf.getvalue()
        buf.seek(0); buf.truncate()
        for row in data["rows"]:
            # Compute the per-row unsubscribe URL lazily — empty for
            # rows without an email (anonymous walk-in customers).
            unsub_url = ""
            row_email = row.get("email") or ""
            if _can_sign_unsubscribe and row_email:
                try:
                    unsub_url = build_unsubscribe_url(
                        email=row_email,
                        organization_id=org_id,
                    )
                except Exception as exc:
                    # Never block the export over a per-row failure —
                    # the merchant gets a CSV with one blank cell, not
                    # a 500 in the middle of a streaming download.
                    logger.warning(
                        "customer_insights: unsubscribe URL build "
                        "failed for email=%s: %s", row_email, exc,
                    )
            row_with_unsub = {**row, "unsubscribe_url": unsub_url}
            writer.writerow([row_with_unsub.get(col, "") for col in _CSV_COLUMNS])
            yield buf.getvalue()
            buf.seek(0); buf.truncate()

    return StreamingResponse(
        _row_iter(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                'attachment; filename="customers_export.csv"'
            ),
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# 6. Action log — POST
# ──────────────────────────────────────────────────────────────────────────────


class ActionLogRequest(BaseModel):
    """Body for ``POST /actions/log``.

    Validation kept loose on purpose — different channels evolve at
    different rates and we'd rather log a slightly-wrong entry than
    drop the audit signal.
    """

    customer_id: str = Field(min_length=1)
    channel: str = Field(min_length=1, description="email | whatsapp | task | tag")
    template: Optional[str] = Field(default=None)
    status: str = Field(default="opened")


@router.post("/actions/log", status_code=status.HTTP_201_CREATED)
async def log_action(
    payload: ActionLogRequest,
    current_user: dict = Depends(get_current_user),
):
    """Record a customer outreach action.

    The frontend fires this on click of "Manda email" / "Apri WhatsApp" /
    "Crea promemoria". Status defaults to ``opened`` — we don't know if
    the merchant actually sent the message because the deep-link UX
    hands off to their own client (Gmail / WhatsApp / etc.).
    """
    org_id = current_user["organization_id"]
    user_id = current_user.get("user_id") or current_user.get("id") or "unknown"
    await service.log_outreach_action(
        org_id,
        user_id,
        payload.customer_id,
        channel=payload.channel,
        template=payload.template,
        status=payload.status,
    )
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# 7. Outreach builder — Phase 3
# ──────────────────────────────────────────────────────────────────────────────


class OutreachBuildRequest(BaseModel):
    """Body for ``POST /actions/outreach``.

    Returns the deep-link URL ready for the frontend ``window.open()``.
    """

    customer_id: str = Field(min_length=1)
    channel: str = Field(min_length=1, description="mailto | whatsapp")
    template: str = Field(min_length=1, description="library.json key")
    locale: str = Field(default="it", description="it | en | de | fr")


@router.post("/actions/outreach")
async def build_outreach_endpoint(
    payload: OutreachBuildRequest,
    current_user: dict = Depends(get_current_user),
):
    """Build a deep-link outreach URL + log the action in one call.

    Frontend usage::

        const res = await api.post('/api/customer-insights/actions/outreach', {
          customer_id: 'cust_42',
          channel: 'mailto',          // or 'whatsapp'
          template: 'at_risk_followup',
          locale: i18n.language,
        });
        window.open(res.data.url, '_blank');

    Returns ``{channel, url, subject, preview}``. Raises 404 if the
    customer doesn't exist on this org, 400 if the channel doesn't
    support the customer (e.g. whatsapp + no phone) or the template
    is unknown.
    """
    from services.customer_outreach import build_outreach, log_outreach
    from services.customer_outreach.channels.base import CustomerContact
    from repositories import customer_repository, organization_repository

    org_id = current_user["organization_id"]
    user_id = current_user.get("user_id") or current_user.get("id") or "unknown"

    customer = await customer_repository.find_by_id(payload.customer_id, org_id)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    org = await organization_repository.find_by_id(org_id)
    merchant_name = (org or {}).get("name") if isinstance(org, dict) else getattr(org, "name", "")

    contact = CustomerContact(
        id=customer.id,
        name=customer.name or "",
        email=customer.email,
        phone=customer.phone,
    )

    try:
        link = build_outreach(
            contact,
            template_key=payload.template,
            channel=payload.channel,
            locale=payload.locale,
            merchant_name=merchant_name or "",
        )
    except NotImplementedError as exc:
        # v2 stub channel (e.g. brevo) requested.
        raise HTTPException(status_code=501, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Audit log fire-and-forget.
    await log_outreach(
        org_id, user_id, payload.customer_id,
        channel=payload.channel, template=payload.template,
    )

    return {
        "channel": link.channel,
        "url": link.url,
        "subject": link.subject,
        "body": link.body,
        "preview": link.preview,
    }


@router.get("/actions/templates")
async def list_outreach_templates(
    locale: str = Query("it", description="it | en | de | fr"),
    current_user: dict = Depends(get_current_user),
):
    """Public picker — list the templates available for a locale.

    Used by the frontend to populate a "scegli template" dropdown.
    """
    from services.customer_outreach import list_templates
    return {"templates": list_templates(locale)}




# ── CG4 — cross-sell: le anime acquistate da ogni cliente ────────────────────


@router.get("/cross-sell")
async def cross_sell_candidates(
    have: str = Query("event_ticket", max_length=20),
    missing: str = Query("service", max_length=20),
    customer_id: str = Query(None, max_length=64),
    current_user: dict = Depends(get_current_user),
    _module: dict = Depends(_require_cross_sell_module()),
):
    """Chi ha comprato l'anima X ma mai la Y (default: ritiri ma mai
    consulenze) — LA lista di cross-sell dell'operatore olistico.

    Con ``customer_id``: le anime acquistate da QUEL cliente (per i
    badge nel profilo). Fonte: ordini confermati/completati, item_type
    per riga. Realtà dei dati: fatti, nessuno scoring.
    """
    from database import orders_collection, customers_collection

    org_id = current_user["organization_id"]

    match: dict = {"organization_id": org_id,
                   "status": {"$in": ["confirmed", "completed"]}}
    if customer_id:
        match["customer_id"] = customer_id

    types_by_customer: dict = {}
    async for g in orders_collection.aggregate([
        {"$match": match},
        {"$unwind": "$items"},
        {"$group": {"_id": {"c": "$customer_id",
                            "t": {"$ifNull": ["$items.item_type", "physical"]}}}},
    ]):
        cid = g["_id"].get("c")
        if cid:
            types_by_customer.setdefault(cid, set()).add(g["_id"].get("t"))

    if customer_id:
        return {"customer_id": customer_id,
                "types": sorted(types_by_customer.get(customer_id, set()))}

    candidate_ids = [cid for cid, ts in types_by_customer.items()
                     if have in ts and missing not in ts]
    out = []
    if candidate_ids:
        async for c in customers_collection.find(
                {"id": {"$in": candidate_ids[:200]}, "organization_id": org_id},
                {"_id": 0, "id": 1, "name": 1, "email": 1, "phone": 1,
                 "accepted_marketing_at": 1, "marketing_revoked_at": 1}):
            out.append({
                "customer_id": c["id"],
                "name": c.get("name"),
                "email": c.get("email"),
                "phone": c.get("phone"),
                "marketing_consent": bool(c.get("accepted_marketing_at"))
                                     and not c.get("marketing_revoked_at"),
                "types": sorted(types_by_customer.get(c["id"], set())),
            })
    return {"have": have, "missing": missing,
            "count": len(candidate_ids), "candidates": out}
