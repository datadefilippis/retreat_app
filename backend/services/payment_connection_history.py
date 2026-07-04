"""
Payment connection history — append-only audit log for connect_type transitions.

Why:
  The `payment_connections` document is a point-in-time snapshot. When a
  merchant disconnects Standard and reconnects via Express, the doc is
  updated in place — there is no way later to reconstruct when each
  transition happened, from which account to which, or who triggered it.

  Compliance + support workflows occasionally need this: "why is this org's
  transactions isolated from their old Stripe account" or "when did we
  migrate this tenant off Standard". This collection is the answer.

Design:
  - Append-only (no updates, no deletes). Each event is a new row.
  - Best-effort writes: callers must never have their main operation
    blocked because the history collection hiccupped.
  - Free-form `metadata` field for future-proofing without a schema
    migration.

Event taxonomy (stable identifiers — used by support tooling + future
admin UIs; do not rename without updating both):

  onboarding_started   : merchant initiated a new onboarding (any flow)
  onboarding_resumed   : merchant continued an in-progress Express onboarding
  oauth_linked         : Standard OAuth callback successfully exchanged
  runtime_ready        : capability check flipped to `ready` (post onboarding)
  disconnected         : admin flipped status to `disconnected` via PATCH

Collection shape:
  {
    id: uuid,
    org_id: str,
    actor_user_id: str | None,   # None for background / webhook-triggered
    event: str,                  # one of the taxonomy above
    from_connect_type: str | None,   # the prior connect_type, if any
    to_connect_type: str | None,     # the current connect_type after event
    external_account_id: str | None, # Stripe account id if known
    metadata: dict,              # free-form per-event context
    created_at: datetime,
  }
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Event taxonomy — stable constants
EVENT_ONBOARDING_STARTED = "onboarding_started"
EVENT_ONBOARDING_RESUMED = "onboarding_resumed"
EVENT_OAUTH_LINKED = "oauth_linked"
EVENT_RUNTIME_READY = "runtime_ready"
EVENT_DISCONNECTED = "disconnected"

_VALID_EVENTS = {
    EVENT_ONBOARDING_STARTED,
    EVENT_ONBOARDING_RESUMED,
    EVENT_OAUTH_LINKED,
    EVENT_RUNTIME_READY,
    EVENT_DISCONNECTED,
}


async def record_transition(
    *,
    org_id: str,
    event: str,
    to_connect_type: Optional[str] = None,
    from_connect_type: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    external_account_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a connect_type transition to payment_connection_history.

    Best-effort: exceptions are logged and swallowed. The caller's main
    operation must never fail because of the audit log.
    """
    if event not in _VALID_EVENTS:
        # Defensive: keep taxonomy tight; a mistyped event name is a bug
        # in the caller we want to surface in logs, but do not raise so
        # the caller's primary operation still completes.
        logger.warning(
            "payment_connection_history: unknown event '%s' for org=%s — recorded with best-effort",
            event, org_id,
        )

    try:
        from database import db
        from models.common import generate_id, utc_now

        doc = {
            "id": generate_id(),
            "org_id": org_id,
            "actor_user_id": actor_user_id,
            "event": event,
            "from_connect_type": from_connect_type,
            "to_connect_type": to_connect_type,
            "external_account_id": external_account_id,
            "metadata": dict(metadata) if metadata else {},
            "created_at": utc_now(),
        }
        await db.payment_connection_history.insert_one(doc)
        logger.info(
            "payment_connection_history: org=%s event=%s from=%s to=%s account=%s",
            org_id, event, from_connect_type, to_connect_type, external_account_id,
        )
    except Exception as exc:
        # Don't log as error — this is genuinely best-effort audit. The main
        # operation already succeeded or failed on its own terms.
        logger.warning(
            "payment_connection_history: failed to record event=%s for org=%s: %s",
            event, org_id, exc,
        )
