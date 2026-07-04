"""
Preferences router — per-user UI preferences (dashboard layout, etc.).

Stores preferences in the existing User.preferences Dict[str, Any] field.
No new collection needed.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from auth import get_current_user, get_verified_user, get_verified_user
from repositories import user_repository
from datetime import datetime, timezone

router = APIRouter(prefix="/preferences", tags=["preferences"])


class DashboardPreferences(BaseModel):
    widgets: List[str] = []


@router.get("/dashboard", response_model=DashboardPreferences)
async def get_dashboard_prefs(current_user: dict = Depends(get_verified_user)):
    """Return the user's pinned dashboard widget keys (ordered)."""
    user = await user_repository.find_by_id(current_user["user_id"])
    prefs = (user or {}).get("preferences") or {}
    return DashboardPreferences(widgets=prefs.get("dashboard_widgets", []))


@router.patch("/dashboard", response_model=DashboardPreferences)
async def update_dashboard_prefs(
    body: DashboardPreferences,
    current_user: dict = Depends(get_verified_user),
):
    """Replace the user's pinned dashboard widget list (order matters)."""
    user = await user_repository.find_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    prefs = user.get("preferences") or {}
    prefs["dashboard_widgets"] = body.widgets

    await user_repository.update(current_user["user_id"], {
        "preferences": prefs,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return DashboardPreferences(widgets=body.widgets)
