"""
Data Integrity Router — entity linking coverage and retroactive linking.

Provides:
  GET  /data-integrity/coverage     — linking coverage across all datasets
  POST /data-integrity/relink       — retroactive linking (preview or apply)

Admin-only. No automatic mutations — always requires explicit action.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, get_verified_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-integrity", tags=["Data Integrity"])


class RelinkRequest(BaseModel):
    dataset_type: str = Field(default="sales", pattern="^(sales|purchases|expenses)$")
    dry_run: bool = True  # Default to preview mode


@router.get("/coverage")
async def get_coverage(current_user: dict = Depends(get_verified_user)):
    """Return entity linking coverage across all dataset types."""
    from services.retroactive_linker import get_linking_coverage

    org_id = current_user["organization_id"]
    coverage = await get_linking_coverage(org_id)
    return {"coverage": coverage}


@router.post("/relink")
async def run_relink(
    body: RelinkRequest,
    current_user: dict = Depends(require_admin),
):
    """
    Run retroactive entity linking.

    Default: dry_run=True (preview only, no mutations).
    Set dry_run=False to apply exact-match links. Admin-only.
    """
    from services.retroactive_linker import run_retroactive_linking

    org_id = current_user["organization_id"]

    result = await run_retroactive_linking(
        org_id=org_id,
        dataset_type=body.dataset_type,
        dry_run=body.dry_run,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    logger.info(
        "data_integrity: relink %s for org=%s dry_run=%s → scanned=%d candidates=%d applied=%d",
        body.dataset_type, org_id, body.dry_run,
        result.get("scanned", 0), result.get("candidates_found", 0), result.get("links_applied", 0),
    )

    return result
