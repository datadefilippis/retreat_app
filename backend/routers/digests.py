"""Digest router — generate, retrieve, and download financial digests."""
import logging
import base64
from fastapi import APIRouter, HTTPException, Request, Depends, Query, status
from fastapi.responses import Response
from typing import Optional
from auth import get_current_user, get_verified_user, get_verified_user
from routers.auth import limiter
from repositories import organization_repository
from services.module_access import check_module_access
# Wave 8A.0: usage tracking moved into digest_builder; no longer needed here.

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/digests", tags=["Digests"])


@router.post("/generate")
@limiter.limit("3/minute")
async def generate_digest(
    request: Request,
    period: Optional[int] = Query(default=None, ge=1, le=366, description="Period in days (ignored when start/end date provided)"),
    digest_type: str = Query(default="weekly", regex="^(weekly|monthly)$"),
    format: str = Query(default="report", regex="^(text|report)$"),
    start_date: Optional[str] = Query(default=None, description="Custom start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="Custom end date (YYYY-MM-DD)"),
    current_user: dict = Depends(get_verified_user),
):
    """Generate a new financial digest (admin only).

    Args:
        period: Number of days (default 7 for weekly).
        digest_type: "weekly" or "monthly".
        format: "text" (legacy) or "report" (PDF with charts).
        start_date/end_date: Custom period (overrides `period`).
    """
    if current_user.get("role") not in ("admin", "system_admin"):
        raise HTTPException(status_code=403, detail="Solo gli admin possono generare digest.")

    org_id = current_user["organization_id"]

    # AI access gate — checks entitlement for "digest" feature
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organizzazione non trovata.")
    await check_module_access(org_id, "ai_assistant", "digest", org_doc=org_doc)

    # B-14 fix — single source of truth for AI-in-digest gating.
    # The previous code hard-coded ``plan in ("core","pro","enterprise")``,
    # which duplicated the policy across this file and background_service,
    # and silently disabled AI for any new plan slug added later (the
    # entitlement system already knows the answer). Now we read the same
    # ai_assistant.digest entitlement that ``check_module_access`` above
    # already validated for the gate.
    from services.module_access import can_use_module
    include_ai = await can_use_module(org_doc, "ai_assistant", "digest")

    # Validate custom dates or default period
    if start_date and end_date:
        from datetime import datetime
        try:
            s = datetime.fromisoformat(start_date)
            e = datetime.fromisoformat(end_date)
            if e <= s:
                raise ValueError("end_date must be after start_date")
            diff = (e - s).days
            if diff > 366:
                raise ValueError("Maximum period is 366 days")
            if diff < 1:
                raise ValueError("Period must be at least 1 day")
            period = diff
            # Auto-set digest_type based on period length
            if period > 14:
                digest_type = "monthly"
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
    elif period is None:
        period = 7 if digest_type == "weekly" else 30

    from core.module_registry import get_all as registry_get_all
    from repositories import digest_repository
    from models.digest import Digest

    digest_modules = [m for m in registry_get_all() if m.digest_builder is not None]
    if not digest_modules:
        raise HTTPException(status_code=404, detail="Nessun modulo digest disponibile.")

    locale = current_user.get("locale", "it")
    # Wave 8A.0 — pass user_id so the builder records the AIUsageEvent
    # with full attribution (token counts + cost_usd). Prior to this
    # the manual digest path wrote a stub event from this router with
    # no tokens/cost, while the cron-driven path wrote no event at all.
    result = await digest_modules[0].digest_builder(
        org_id=org_id, period_days=period, digest_type=digest_type,
        locale=locale, format=format, include_ai=include_ai,
        start_date=start_date, end_date=end_date,
        user_id=current_user.get("user_id") or current_user.get("id"),
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nessun dato disponibile per generare il digest.",
        )

    # Extract PDF bytes before saving to DB (don't store raw bytes in Mongo)
    pdf_bytes = result.pop("pdf_bytes", None)

    digest = Digest(**result)
    doc = await digest_repository.create(digest)

    # Store PDF separately if generated
    if pdf_bytes:
        await digest_repository.store_pdf(doc["id"], org_id, pdf_bytes)

    # Wave 8A.0 — usage tracking moved INSIDE the builder so the cron
    # path is also covered. The previous stub event written here (no
    # tokens, no cost_usd) is replaced by the builder's full event
    # including tokens_prompt, tokens_completion, cost_usd, agent_id.
    # If the AI call failed and the builder fell back to rule-based,
    # NO usage event is written (correct: nothing was billed by
    # Anthropic for the fallback path).

    # B-15 fix — manual trigger now sends the email too, mirroring the
    # behaviour of the scheduled tick in background_service._run_digest_
    # generation. Without this, clicking "Genera Report" produced a digest
    # in DB but never delivered it: the merchant saw the entry in the
    # dashboard list but no PDF in inbox, which is the surface that
    # legitimately read as "the report stopped working".
    # send_digest_report_email applies its own preference + plan + gate
    # checks (email_weekly_digest / can_use_module email_digest / email_
    # gate bounced filter), so we can call it unconditionally — anything
    # the merchant has opted out of is short-circuited inside.
    if pdf_bytes and format == "report":
        try:
            from services.alert_notification_service import send_digest_report_email
            period_label = f"{result.get('period_start', '')} — {result.get('period_end', '')}"
            await send_digest_report_email(
                org_id=org_id,
                pdf_bytes=pdf_bytes,
                sections=result.get("sections", {}),
                digest_type=digest_type,
                period_label=period_label,
                locale=locale,
            )
        except Exception as exc:
            # Never let a transport error mask the successful digest
            # generation — the merchant still gets the record + the
            # PDF download via /digests/{id}/pdf, and the failure is
            # surfaced in logs for the ops team to investigate.
            logger.warning(
                "digests: manual trigger — email delivery failed for org=%s: %s",
                org_id, exc,
            )

    return doc


@router.get("")
async def list_digests(
    request: Request,
    digest_type: Optional[str] = Query(default=None, regex="^(weekly|monthly)$"),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_verified_user),
):
    """List digests for the current organization.

    Wave 14 perf (2026-05-16) — response excludes ``pdf_b64`` by default
    (repository projection) and carries a short ``Cache-Control: private,
    max-age=60`` so the browser dedups rapid re-clicks on the Digest tab
    without serving stale data when a new digest is generated. The
    ``private`` directive prevents shared caches (nginx, CDN) from
    leaking digests across users — they are per-org, auth-required.
    """
    from fastapi.responses import JSONResponse
    from repositories import digest_repository

    org_id = current_user["organization_id"]
    docs = await digest_repository.find_by_org(org_id, digest_type=digest_type, limit=limit)
    return JSONResponse(
        content=docs,
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.get("/latest")
async def get_latest_digest(
    request: Request,
    digest_type: str = Query(default="weekly", regex="^(weekly|monthly)$"),
    current_user: dict = Depends(get_verified_user),
):
    """Get the most recent digest of a given type.

    Wave 14 perf (2026-05-16) — see ``list_digests`` for the
    ``Cache-Control`` rationale. Also excludes ``pdf_b64`` (~300 KB
    saved per call).
    """
    from fastapi.responses import JSONResponse
    from repositories import digest_repository

    org_id = current_user["organization_id"]
    doc = await digest_repository.find_latest(org_id, digest_type=digest_type)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nessun digest trovato.",
        )
    return JSONResponse(
        content=doc,
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.get("/{digest_id}/pdf")
async def download_digest_pdf(
    digest_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Download the PDF for a specific digest."""
    from repositories import digest_repository

    org_id = current_user["organization_id"]

    # Verify digest exists and belongs to org
    doc = await digest_repository.find_by_id(digest_id, org_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Digest non trovato.")

    if not doc.get("has_pdf"):
        raise HTTPException(status_code=404, detail="PDF non disponibile per questo digest.")

    pdf_bytes = await digest_repository.get_pdf(digest_id, org_id)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="PDF non trovato.")

    filename = f"aurya_report_{doc.get('digest_type', 'weekly')}_{doc.get('period_start', '')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{digest_id}")
async def get_digest(
    digest_id: str,
    request: Request,
    current_user: dict = Depends(get_verified_user),
):
    """Get a specific digest by ID."""
    from repositories import digest_repository

    org_id = current_user["organization_id"]
    doc = await digest_repository.find_by_id(digest_id, org_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Digest non trovato.",
        )
    return doc
