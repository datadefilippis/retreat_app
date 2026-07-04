"""Feature Flag admin endpoint — Phase 0 Step 9 (2026-05-28).

Read-only and write surface per ``feature_flags`` per-organization gestiti
da System Admin (role == "system_admin"). NON è esposto a org admin.

Endpoints
=========
  GET  /api/admin/feature-flags/{org_id}
       → ritorna lo stato corrente di TUTTI i flag canonici (dict bool)

  PUT  /api/admin/feature-flags/{org_id}
       Body: {"flag_name": "embed_widget_enabled", "value": true}
       → toggle del singolo flag, audit-logged, cache invalidated

Sicurezza
=========
- Ogni endpoint richiede ``require_system_admin``.
- ``flag_name`` validato contro ``feature_flag_service.KNOWN_FLAGS``
  → niente write su key arbitrarie (sandbox da typos / abuse).
- Cache 60s invalidata automaticamente dopo set.

Audit trail
===========
Ogni write produce un AuditLog con action="admin_set_feature_flag" e
``details = {flag_name, previous_value, new_value, org_name}``.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth import require_system_admin
from models import AuditLog
from repositories import admin_repository, audit_repository
from services import feature_flag_service

router = APIRouter(prefix="/admin/feature-flags", tags=["System Admin – Feature Flags"])


# ── Schemas ─────────────────────────────────────────────────────────────


class FeatureFlagUpdate(BaseModel):
    """Body schema per PUT /api/admin/feature-flags/{org_id}."""

    flag_name: str = Field(..., description="Canonical flag name (es. 'embed_widget_enabled')")
    value: bool = Field(..., description="Nuovo stato del flag")


class FeatureFlagStateResponse(BaseModel):
    """Risposta letture/scritture. ``flags`` riflette lo stato post-write."""

    org_id: str
    flags: dict


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get(
    "/{org_id}",
    response_model=FeatureFlagStateResponse,
    summary="List all feature flags for an organization",
)
async def get_feature_flags(
    org_id: str,
    _current_user: dict = Depends(require_system_admin),
) -> FeatureFlagStateResponse:
    """Ritorna lo stato corrente di tutti i flag canonici per ``org_id``.

    Per i flag NON ancora settati sul doc Mongo, il valore default è False
    (contract del service). Output normalizzato: tutti i KNOWN_FLAGS
    presenti in risposta, anche se assenti dal doc DB.
    """
    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    raw_flags = await feature_flag_service.get_all_flags(org_id)
    # Normalize: ogni KNOWN_FLAG presente come bool (False se non set)
    normalized = {
        flag: bool(raw_flags.get(flag, False))
        for flag in feature_flag_service.KNOWN_FLAGS
    }
    return FeatureFlagStateResponse(org_id=org_id, flags=normalized)


@router.put(
    "/{org_id}",
    response_model=FeatureFlagStateResponse,
    summary="Toggle a single feature flag for an organization",
)
async def set_feature_flag(
    org_id: str,
    body: FeatureFlagUpdate,
    current_user: dict = Depends(require_system_admin),
) -> FeatureFlagStateResponse:
    """Imposta ``flag_name`` = ``value`` su ``org_id``.

    Validazioni:
      - ``flag_name`` deve essere in ``KNOWN_FLAGS`` → altrimenti 400.
      - ``org_id`` deve esistere → altrimenti 404.

    Side effects:
      - Cache feature_flag_service invalidata per ``org_id``.
      - AuditLog scritto con previous_value + new_value.
    """
    if body.flag_name not in feature_flag_service.KNOWN_FLAGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown flag_name '{body.flag_name}'. "
                f"Valid: {sorted(feature_flag_service.KNOWN_FLAGS)}"
            ),
        )

    org_doc = await admin_repository.get_organization_detail(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found",
        )

    # Snapshot stato precedente per audit trail
    previous_flags = await feature_flag_service.get_all_flags(org_id)
    previous_value = bool(previous_flags.get(body.flag_name, False))

    updated = await feature_flag_service.set_flag(org_id, body.flag_name, body.value)
    if not updated:
        # set_flag soft-fails (logs error, returns False) → bubble up
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update feature flag (see backend logs)",
        )

    # Audit (system_admin: organization_id=None → cross-tenant log)
    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_set_feature_flag",
        resource_type="organization",
        resource_id=org_id,
        details={
            "flag_name": body.flag_name,
            "previous_value": previous_value,
            "new_value": bool(body.value),
            "org_name": org_doc.get("name"),
        },
    ))

    # Ritorna lo stato corrente (post-write)
    raw_flags = await feature_flag_service.get_all_flags(org_id)
    normalized = {
        flag: bool(raw_flags.get(flag, False))
        for flag in feature_flag_service.KNOWN_FLAGS
    }
    return FeatureFlagStateResponse(org_id=org_id, flags=normalized)
