import logging

from fastapi import APIRouter, HTTPException, Request, status, Depends, Query
from typing import List, Optional
from models import Insight
from auth import get_current_user, get_verified_user, require_admin
from repositories import insight_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("", response_model=List[Insight])
async def list_insights(
    module_key: Optional[str] = None,
    limit: int = Query(20, le=100),
    current_user: dict = Depends(get_verified_user)
):
    """List AI-generated insights for the organization"""
    docs = await insight_repository.find_by_org(
        current_user['organization_id'],
        module_key=module_key,
        limit=limit
    )
    return [insight_repository.doc_to_insight(doc) for doc in docs]


@router.get("/latest")
async def get_latest_insight(
    module_key: str = "cashflow_monitor",
    current_user: dict = Depends(get_verified_user)
):
    """Get the most recent insight for a module"""
    doc = await insight_repository.find_latest(
        current_user['organization_id'],
        module_key=module_key
    )
    
    if not doc:
        return None
    return insight_repository.doc_to_insight(doc)


@router.post("/generate")
async def generate_insight(
    request: Request,
    current_user: dict = Depends(require_admin),
):
    """DEPRECATED — Insight generation replaced by Digest.

    Returns 410 Gone. Existing insights are still readable via GET endpoints.
    Use POST /digests/generate instead.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "La generazione Insights è stata sostituita dal Digest. "
            "Usa la funzione Digest per generare analisi aggiornate."
        ),
    )


@router.get("/{insight_id}", response_model=Insight)
async def get_insight(
    insight_id: str,
    current_user: dict = Depends(get_verified_user)
):
    """Get a specific insight"""
    doc = await insight_repository.find_by_id(
        insight_id,
        current_user['organization_id']
    )
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found"
        )
    return insight_repository.doc_to_insight(doc)
