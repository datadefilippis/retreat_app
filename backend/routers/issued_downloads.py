"""
Issued Downloads — admin list + actions.

Release 3 (Digital) B8 backend complement. Analog of
routers/issued_reservations.py for item_type=digital deliveries.

Routes:
  GET  /api/issued-downloads            — list (optional product_id / order_id / status filters)
  POST /api/issued-downloads/{id}/resend — re-send the "your download is ready" email
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from database import issued_downloads_collection
from auth import get_current_user, get_verified_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issued-downloads", tags=["Issued Downloads"])


class IssuedDownloadListResponse(BaseModel):
    downloads: List[dict]


@router.get("", response_model=IssuedDownloadListResponse)
async def list_issued_downloads(
    order_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(
        None, alias="status", pattern="^(active|cancelled|exhausted)$",
    ),
    search: Optional[str] = Query(
        None,
        description="Case-insensitive match on code, holder_name, holder_email, product_name",
    ),
    limit: int = Query(default=200, le=500),
    current_user: dict = Depends(get_verified_user),
):
    """List IssuedDownload rows for the admin DigitalDashboardPage / triage.

    The shape mirrors issued_reservations so the frontend can reuse
    presentational patterns with minimal adaptation.
    """
    org_id = current_user["organization_id"]
    query: dict = {"organization_id": org_id}
    if order_id:
        query["order_id"] = order_id
    if product_id:
        query["product_id"] = product_id
    if status_filter:
        query["status"] = status_filter

    if search:
        import re
        safe = re.escape(search.strip())
        if safe:
            rx = {"$regex": safe, "$options": "i"}
            query["$or"] = [
                {"code": rx},
                {"holder_name": rx},
                {"holder_email": rx},
                {"product_name": rx},
                {"download_filename": rx},
            ]

    rows = await issued_downloads_collection.find(
        query, {"_id": 0},
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"downloads": rows}


@router.post("/{download_id}/resend")
async def resend_download_email(
    download_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Re-send the confirmation email that carries the /d/{token} link.

    Idempotent on the token itself (we never rotate it here — the same
    link still works). Refuses on cancelled rows: if the order was
    cancelled the customer should be told separately, not handed a
    stale link that would 404.
    """
    if current_user.get("role") not in ("admin", "system_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    org_id = current_user["organization_id"]
    row = await issued_downloads_collection.find_one(
        {"id": download_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Download non trovato")
    if row.get("status") == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Download cancellato — non posso rinviare la conferma.",
        )

    # Piggyback on the order-confirmation renderer: the simplest way to
    # hand the customer the same link + surrounding context is to rerun
    # notify_customer_order_confirmed for the parent order. It is idempotent
    # on the DB side (no duplicate issuance) and will re-embed the current
    # download status.
    try:
        from database import orders_collection
        from services.order_email_service import notify_customer_order_confirmed
        order = await orders_collection.find_one(
            {"id": row["order_id"], "organization_id": org_id}, {"_id": 0},
        )
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordine associato non trovato",
            )
        await notify_customer_order_confirmed(order, org_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("issued_downloads.resend: failed for %s: %s", download_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile rinviare l'email",
        )

    return {"ok": True, "download_id": download_id}
