"""DPA enforcement service — Wave E.8.1 (Sprint 1 W1.1).

Centralized check that a merchant organization has acknowledged the Data
Processing Agreement (Art. 28 GDPR) before performing actions that
materially expand the data processing surface (publish store, enable
checkout, configure analytics).

Backend infrastructure (Wave CG-7) already implements:
  - GET /api/legal/dpa?lang=xx  → rendered DPA markdown
  - POST /api/legal/dpa/acknowledge → idempotent acceptance + audit log
  - GET /api/legal/dpa/status → has-acknowledged badge

Wave E.8.1 adds the ENFORCEMENT layer: store publish, embed-init exposure,
analytics bridge — all gated by ``require_dpa_acknowledged(org_id)`` so
the merchant cannot accidentally start processing customer data without
having explicitly accepted the legal terms.

Design choices
==============
- **Grace window for legacy stores**: stores that were `is_published=True`
  BEFORE the enforcement was added keep working. New publish actions are
  blocked. The admin sees a warning banner nudging acknowledgement.
- **No feature flag**: ship enforcement directly. Merchants who haven't
  yet acknowledged hit a clear 412 error with link to ``/settings/legal/dpa``.
- **Idempotent check**: the function is read-only (no side effects), safe
  to call from multiple endpoints without conflict.
- **Single source of truth**: every enforcement caller goes through
  ``require_dpa_acknowledged()`` so the rule is centrally maintained.

Sentinel pinning: ``TestSEC_E_8_1_DPAAcceptance`` verifies the helper is
imported + called by every gated endpoint.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


# ─── Public error code for clients ──────────────────────────────────────


DPA_NOT_ACKNOWLEDGED_CODE = "DPA_NOT_ACKNOWLEDGED"
DPA_LINK_ADMIN_PATH = "/settings/legal/dpa"


# ─── Helpers ────────────────────────────────────────────────────────────


async def is_dpa_acknowledged(organization_id: str) -> bool:
    """Return True iff the org has at least one valid DPA acknowledgement.

    Lookups the consent_audit collection for the most recent
    document_type="merchant_dpa" record scoped to the org. Returns False
    on lookup error (defensive — better safe than sorry: if we cannot
    verify acknowledgement, treat as not acknowledged).
    """
    if not organization_id:
        return False
    try:
        from repositories import consent_audit_repository as car
        record = await car.find_latest_for_org_dpa(organization_id)
        return record is not None
    except Exception as exc:
        logger.warning(
            "dpa_enforcement: lookup failed org=%s: %s — denying",
            organization_id, exc,
        )
        return False


async def require_dpa_acknowledged(
    organization_id: str,
    action: str = "this action",
) -> None:
    """Raise HTTP 412 Precondition Failed if the org has not acknowledged
    the DPA. Use as a guard inside endpoints that materially expand the
    data processing surface (store publish, embed-init, analytics).

    Args:
        organization_id: the org being checked (typically from JWT).
        action: human-readable action name for the error message.

    Raises:
        HTTPException 412 with structured detail:
            {
                "code": "DPA_NOT_ACKNOWLEDGED",
                "message": "Per <action> devi accettare il DPA (Art. 28 GDPR).",
                "admin_path": "/settings/legal/dpa"
            }
    """
    if await is_dpa_acknowledged(organization_id):
        return

    raise HTTPException(
        status_code=status.HTTP_412_PRECONDITION_FAILED,
        detail={
            "code": DPA_NOT_ACKNOWLEDGED_CODE,
            "message": (
                f"Per {action} è obbligatorio accettare il Data Processing "
                f"Agreement (Art. 28 GDPR). Vai alle impostazioni legali "
                f"per leggerlo e firmarlo."
            ),
            "admin_path": DPA_LINK_ADMIN_PATH,
        },
    )


async def is_publish_gated(organization_id: str, store: dict) -> Optional[str]:
    """Wave E.8.1 grace window for legacy stores.

    Returns:
        None — publish allowed (DPA acknowledged OR legacy store already
               published before enforcement existed).
        str  — gating reason (i18n-key-ready). Caller can present it to
               the admin as a warning banner instead of a hard block.

    Pattern: if the store was ALREADY ``is_published=True`` before this
    enforcement shipped, we don't break their existing public store —
    but we surface a banner asking them to acknowledge ASAP. New publish
    actions on draft stores ARE hard-blocked.
    """
    if await is_dpa_acknowledged(organization_id):
        return None
    if store.get("is_published") is True:
        # Legacy store already public — soft warning.
        return "dpa.legacy_store_needs_acknowledgement"
    # Draft store + no DPA → hard block.
    return "dpa.not_acknowledged_blocking_publish"
