"""
Brevo transactional email webhook handler (Phase 1 Step B2).

Receives bounce / complaint / blocked / unsubscribed events from Brevo
and tracks them on the recipient's user_doc or customer_account_doc so
future code (B2.5) can avoid sending again. Today the integration is
*read-write to the DB only* — it does NOT yet gate outgoing emails.
That gate is intentionally deferred to a separate step to minimize
the regression surface of B2.

Why this matters
----------------
Without bounce tracking, every retry of (forgot-password, resend-verify,
order-confirmation) to a dead inbox keeps Brevo's bounce-rate counter
ticking. After ~5% bounce, Gmail / Outlook downgrade our sender
reputation; new transactional emails start landing in spam. This
endpoint closes that loop: bounces are caught the moment Brevo sees
them, and the user/customer doc is annotated with the reason.

Security
--------
- Endpoint requires the `X-Webhook-Secret` request header to match the
  `BREVO_WEBHOOK_SECRET` env var.
- If the env var is unset, the endpoint default-denies (503): we don't
  want Brevo events to land in production while authentication is off.
- Brevo does NOT sign webhook payloads (no HMAC). The shared-secret
  header is the strongest auth Brevo offers natively. We treat it as
  a bearer token: anyone with the secret can write to our user docs,
  so rotate via secrets-rotation.md if leaked.

Idempotency
-----------
DB updates use `$set` — re-sending the same event repaints the same
field values; safe. Audit log inserts include the event timestamp in
their id so an exact replay creates an exact-duplicate insert (Mongo
allows this; doesn't break anything but adds noise — Brevo retries are
documented to use new event ids).

Configure in Brevo dashboard
----------------------------
  Settings → Webhooks → Add new
  URL:           https://afianco.app/api/webhooks/brevo
  Events:        Hard bounce, Spam, Blocked, Unsubscribed, Complaint
  Custom header: X-Webhook-Secret = <value of BREVO_WEBHOOK_SECRET>
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Request

from database import (
    users_collection,
    customer_accounts_collection,
    audit_logs_collection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Events we care about — Brevo sends many more (delivered, click, open)
# that we silently ignore. Map: brevo event name → email_status field value.
# `None` = transient event, no DB write (only soft_bounce currently).
TRACKED_EVENTS = {
    "hard_bounce": "bounced",
    "soft_bounce": None,
    "spam": "complaint",
    "blocked": "blocked",
    "unsubscribed": "unsubscribed",
    "complaint": "complaint",
}


def _mask_email(email: str) -> str:
    """Partial mask for log lines (avoid full PII in logs)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:2]}***@{domain}"


@router.post("/brevo")
async def brevo_webhook(
    request: Request,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
):
    """
    Receive Brevo transactional email events.

    Always returns 200 with a count of processed events, even if some
    individual events failed to update the DB — Brevo treats non-2xx as
    a retry signal, and we don't want a single broken event to trigger
    re-delivery storms.

    Authentication accepts BOTH:
      - `Authorization: Bearer <BREVO_WEBHOOK_SECRET>` — Brevo's outgoing-
        webhook "Token" auth method (recommended; what Brevo dashboard sets).
      - `X-Webhook-Secret: <BREVO_WEBHOOK_SECRET>` — legacy custom-header
        path, kept for backward compat in case the dashboard UI changes.
    Both are checked against the same env var so the operator manages one
    shared secret only.
    """
    expected_secret = os.getenv("BREVO_WEBHOOK_SECRET", "").strip()
    if not expected_secret:
        # Default-deny: env var must be configured to enable the endpoint.
        # 503 is intentional — tells Brevo "service unavailable", which
        # they will retry, giving us time to configure the secret without
        # losing events.
        logger.warning(
            "brevo webhook received but BREVO_WEBHOOK_SECRET not configured (default-deny)"
        )
        raise HTTPException(
            status_code=503,
            detail="Webhook receiver not configured (BREVO_WEBHOOK_SECRET unset)",
        )

    # Resolve the presented secret from EITHER Bearer token OR custom header.
    presented_secret: Optional[str] = None
    auth_source: str = "none"
    if authorization:
        auth_source = "bearer"
        auth_value = authorization.strip()
        # Tolerant Bearer parse: "Bearer <t>", "bearer <t>", or bare "<t>"
        # (Brevo strips the prefix in some configurations).
        if auth_value.lower().startswith("bearer "):
            presented_secret = auth_value[7:].strip()
        else:
            presented_secret = auth_value
    elif x_webhook_secret:
        auth_source = "custom-header"
        presented_secret = x_webhook_secret.strip()

    if not presented_secret or presented_secret != expected_secret:
        logger.warning(
            "brevo webhook: invalid auth (prefix=%r, source=%s)",
            (presented_secret or "")[:5], auth_source,
        )
        raise HTTPException(status_code=401, detail="Invalid webhook authentication")

    # Parse JSON
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("brevo webhook: invalid JSON body: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Brevo may send a single event or an array — normalize to list.
    events = payload if isinstance(payload, list) else [payload]
    if not isinstance(events, list):
        events = [payload]

    processed = 0
    skipped = 0

    for event in events:
        if not isinstance(event, dict):
            skipped += 1
            continue

        event_type = (event.get("event") or "").strip().lower()
        email = (event.get("email") or "").strip().lower()

        if not email or not event_type:
            skipped += 1
            continue

        if event_type not in TRACKED_EVENTS:
            # Silent ignore: delivered, opened, click, etc.
            skipped += 1
            continue

        new_status = TRACKED_EVENTS[event_type]
        if new_status is None:
            # Transient event (e.g. soft_bounce) — log but do not persist.
            logger.info(
                "brevo webhook: transient event ignored type=%s email=%s",
                event_type, _mask_email(email),
            )
            skipped += 1
            continue

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        reason = (event.get("reason") or event_type)[:200]  # cap length

        update_doc = {
            "email_status": new_status,
            "email_bounce_reason": reason,
            "email_bounced_at": now_iso,
        }

        # Update both users and customer_accounts. Same email may exist in
        # either (admin) or both (admin who is also a storefront customer).
        # Each update_one is independent — failure of one does not break the other.
        try:
            await users_collection.update_one(
                {"email": email},
                {"$set": update_doc},
            )
        except Exception as e:
            logger.error(
                "brevo webhook: users update failed email=%s err=%s",
                _mask_email(email), e,
            )

        try:
            await customer_accounts_collection.update_one(
                {"email": email},
                {"$set": update_doc},
            )
        except Exception as e:
            logger.error(
                "brevo webhook: customer_accounts update failed email=%s err=%s",
                _mask_email(email), e,
            )

        # Audit log entry. expire_at populated for the D3 TTL index.
        try:
            await audit_logs_collection.insert_one({
                "id": f"brevo_{event_type}_{int(now_dt.timestamp())}_{email[:5]}",
                "actor_user_id": "brevo_webhook",
                "actor_role": "system",
                "organization_id": None,
                "action": f"BREVO_{event_type.upper()}",
                "target_type": "email",
                "target_id": _mask_email(email),
                "metadata": {
                    "event_type": event_type,
                    "reason": reason,
                    "raw_event_keys": list(event.keys()),
                },
                "created_at": now_iso,
                "expire_at": now_dt,
            })
        except Exception as e:
            logger.error("brevo webhook: audit log insert failed: %s", e)

        processed += 1
        logger.info(
            "brevo webhook: %s email=%s reason=%s",
            event_type, _mask_email(email), reason[:50],
        )

    return {
        "status": "ok",
        "processed": processed,
        "skipped": skipped,
        "received": len(events),
    }
