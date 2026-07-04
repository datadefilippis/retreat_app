"""
Setup Wizard HTTP boundary (Fase 2 Track F — Step 3).

Single endpoint:

    GET /api/setup/wizard
        Returns the full personalized wizard payload for the authenticated
        user's organization. Read-only.

Auth: same gate as `routers/store_progress.py` — get_verified_user (logged
in + email verified). Email-not-verified users are redirected to the
verify-email-required page anyway, so the wizard is never the first thing
they hit.

Why a separate router (instead of extending store_progress):
  - The wizard has a richer response shape (sections, multi-CTA, plan
    metadata) — overloading store_progress would muddy its contract.
  - The wizard reads from MULTIPLE modules (cashflow, commerce, ai), not
    just the storefront. Ownership belongs in services/setup_wizard, not
    in store_progress.
  - The legacy /api/store/setup-progress endpoint stays in place so any
    external caller (or admin tools) keeps working.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from auth import get_verified_user
from services.setup_wizard.wizard_service import build_wizard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["Setup Wizard"])


@router.get("/wizard")
async def get_setup_wizard(current_user: dict = Depends(get_verified_user)):
    """Return the personalized setup wizard for the current org.

    Response shape: see `services/setup_wizard/step_models.SetupWizardResponse`.

    The endpoint is read-only and idempotent. Frontend caches the response
    for ~30s and re-fetches on focus.
    """
    org_id = current_user.get("organization_id")
    user_id = current_user.get("id")

    if not org_id:
        # Should never happen for authenticated users, but defend.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no organization context",
        )

    wizard = await build_wizard(org_id=org_id, user_id=user_id)
    if wizard is None:
        # Org document missing — same 404 semantics as store_progress
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return wizard.model_dump()
