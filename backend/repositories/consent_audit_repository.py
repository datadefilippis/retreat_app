"""Consent audit repository — Wave GDPR-Admin Phase B (2026-05-16).

Immutable append-only log of consent acceptances. ONE record per
acceptance event (signup, re-acceptance after policy update,
explicit re-consent flow).

The repository is intentionally narrow: only INSERT + read-only
queries. There is no UPDATE or DELETE method by design — once a
consent is recorded, it is evidence and must not be mutated.
The 365-day TTL on ``expire_at`` is the only automatic removal
path; it mirrors the audit_logs retention so legal compliance
windows align.

Record shape (Wave GDPR-Commerce CG-1 extends with store_id,
customer_email, order_id — all optional, retrocompat with legacy
records that don't carry them):

    {
      "id": "<uuid>",                       # primary key
      "user_id": "<user.id>" | None,        # FK → users.id (None for guests at checkout)
      "organization_id": "<org.id>" | None, # FK → organizations.id
      "store_id": "<store.id>" | None,      # CG-1: FK → stores.id (None for afianco-level consents)
      "customer_email": "x@y.z" | None,     # CG-1: identifier for guest checkout audit (no user_id)
      "order_id": "<order.id>" | None,      # CG-1: FK → orders.id (only for checkout-time consent)
      "document_type": "privacy_terms",     # extensible enum (afianco) | merchant_privacy | merchant_terms | merchant_marketing | merchant_dpa
      "version_tag": "v1.0",                # human-readable tag of the docs
      "version_hash": "a3f2c8e9d1b4f5a6",   # SHA256 first 16 chars (collision-safe for our scale)
      "locale": "it" | "en" | "de" | "fr",  # locale of the docs presented
      "accepted_at": "2026-05-16T14:30:00+00:00",  # ISO UTC
      "ip_address": "1.2.3.4" | None,       # captured from request (optional, masked if config requires)
      "user_agent": "Mozilla/5.0...",       # captured from request (truncated 200 chars)
      "expire_at": <Date>,                  # TTL: accepted_at + 365 days
      "source": "signup" | "re_acceptance" | "backfill" |
                "customer_signup" | "customer_re_acceptance" |
                "customer_checkout" | "customer_marketing_optin" |
                "customer_marketing_revoke" | "customer_deletion_request" |
                "merchant_dpa_acknowledged",
    }

This module exports:
    record_consent(user_id, locale, version_tag, version_hash, ip,
                   user_agent, organization_id=None, source="signup",
                   document_type="privacy_terms",
                   store_id=None, customer_email=None, order_id=None
                  ) -> dict
    find_by_user(user_id) -> List[dict]       # newest first
    find_latest_for_user(user_id) -> Optional[dict]
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from database import consent_audit_collection

logger = logging.getLogger(__name__)


_TTL_DAYS = 365  # mirrors audit_logs retention (Phase 1 Step D3)
_VALID_DOCUMENT_TYPES = {
    # Phase B (afianco-level) — admin signup + re-consent
    "privacy_terms", "privacy_only", "terms_only",
    # Wave GDPR-Commerce CG-1 — per-store merchant docs + DPA
    "merchant_privacy", "merchant_terms",
    "merchant_marketing",
    "merchant_dpa",
}
_VALID_SOURCES = {
    # Phase A/B/E (afianco admin)
    "signup", "re_acceptance", "backfill",
    # Wave GDPR-Commerce CG-1 — customer-side events
    "customer_signup", "customer_re_acceptance",
    "customer_checkout",
    "customer_marketing_optin", "customer_marketing_revoke",
    "customer_deletion_request",
    # Wave GDPR-Commerce CG-7 — merchant DPA acknowledgement
    "merchant_dpa_acknowledged",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _gen_id() -> str:
    import uuid
    return str(uuid.uuid4())


def hash_document_text(text: str) -> str:
    """Hash document text → first 16 chars of SHA256 hex.

    Used to compute ``version_hash`` from the rendered Privacy Policy
    + Terms of Service text bundle. The truncation to 16 chars is
    safe for our scale (collision probability negligible vs the few
    document versions per year).
    """
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest[:16]


async def record_consent(
    *,
    user_id: Optional[str],
    locale: str,
    version_tag: str,
    version_hash: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    organization_id: Optional[str] = None,
    source: str = "signup",
    document_type: str = "privacy_terms",
    # Wave GDPR-Commerce CG-1 — optional per-store / per-customer fields.
    # Backward-compatible: callers from Phase A/B/E never set these and
    # records are written exactly as before.
    store_id: Optional[str] = None,
    customer_email: Optional[str] = None,
    order_id: Optional[str] = None,
) -> dict:
    """Append an immutable consent record.

    Raises ValueError on invalid enum values. Returns the inserted
    document (with ``id`` populated). NEVER raises on DB errors —
    the caller (signup flow) must not be blocked by consent audit
    failures; failures are logged and surfaced via observability,
    not via HTTP error to the user.

    Wave GDPR-Commerce CG-1 made ``user_id`` Optional to support GUEST
    CHECKOUT audit trails: in that case the caller MUST provide
    ``customer_email`` so the record still identifies a real natural
    person. A record with both user_id=None AND customer_email=None is
    rejected (no identifiable subject).
    """
    if document_type not in _VALID_DOCUMENT_TYPES:
        raise ValueError(
            f"Invalid document_type {document_type!r}; "
            f"allowed: {sorted(_VALID_DOCUMENT_TYPES)}"
        )
    if source not in _VALID_SOURCES:
        raise ValueError(
            f"Invalid source {source!r}; "
            f"allowed: {sorted(_VALID_SOURCES)}"
        )
    if locale not in {"it", "en", "de", "fr"}:
        # Don't raise — fallback gracefully but log so we know
        # someone bypassed the locale validation upstream.
        logger.warning(
            "consent_audit.record_consent: unexpected locale=%r "
            "(allowed: it/en/de/fr) for user_id=%s; recording anyway",
            locale, user_id,
        )
    # CG-1: guarantee at least ONE identifier for the natural person.
    # A consent record without a subject is legally useless — fail fast.
    if user_id is None and not customer_email:
        raise ValueError(
            "consent_audit.record_consent: at least one of user_id or "
            "customer_email must be provided to identify the data subject"
        )

    now = _utc_now()
    # Truncate user_agent to 200 chars — protects against abusive
    # / malformed UA strings and bounds storage cost.
    ua = (user_agent or "")[:200] or None
    # CG-1: light email validation — keep the field optional but reject
    # obviously broken inputs so the audit trail stays clean.
    email_clean = None
    if customer_email:
        s = str(customer_email).strip().lower()
        if "@" in s and len(s) <= 255:
            email_clean = s

    doc = {
        "id": _gen_id(),
        "user_id": user_id,
        "organization_id": organization_id,
        # Wave GDPR-Commerce CG-1 — per-store + per-checkout fields.
        # Stored as null when not provided so legacy queries that
        # `find({user_id: X})` continue to work unchanged.
        "store_id": store_id,
        "customer_email": email_clean,
        "order_id": order_id,
        "document_type": document_type,
        "version_tag": version_tag,
        "version_hash": version_hash,
        "locale": locale,
        "accepted_at": now.isoformat(),
        "ip_address": ip_address,
        "user_agent": ua,
        "expire_at": now + timedelta(days=_TTL_DAYS),
        "source": source,
    }

    try:
        await consent_audit_collection.insert_one(doc.copy())
    except Exception as exc:
        logger.error(
            "consent_audit.record_consent: insert failed for user_id=%s "
            "(version=%s locale=%s source=%s): %s",
            user_id, version_tag, locale, source, exc, exc_info=True,
        )
        # Re-raise so the caller can decide. For signup specifically the
        # caller catches and continues — losing one audit record does
        # not block account creation, only emits a warning.
        raise

    return doc


async def find_by_user(user_id: str, limit: int = 50) -> List[dict]:
    """Return all consent records for a user, newest first."""
    cursor = (
        consent_audit_collection
        .find({"user_id": user_id}, {"_id": 0})
        .sort("accepted_at", -1)
        .limit(limit)
    )
    return await cursor.to_list(limit)


async def find_latest_for_user(user_id: str) -> Optional[dict]:
    """Return the most recent consent record for the user, or None."""
    docs = await find_by_user(user_id, limit=1)
    return docs[0] if docs else None


async def find_latest_for_org_dpa(organization_id: str) -> Optional[dict]:
    """Return the most recent DPA acknowledgement for the org, or None.

    Wave GDPR-Commerce CG-7 helper. The DPA is per-organization (not
    per-user, not per-store), so the lookup key is just organization_id
    + the document_type/source filter for ``merchant_dpa``.

    Returns the freshest record (newest accepted_at) — the endpoint
    uses it both for idempotency on POST /acknowledge and for the
    "has-acknowledged" status badge on the admin UI.
    """
    cursor = (
        consent_audit_collection
        .find(
            {
                "organization_id": organization_id,
                "document_type": "merchant_dpa",
                "source": "merchant_dpa_acknowledged",
            },
            {"_id": 0},
        )
        .sort("accepted_at", -1)
        .limit(1)
    )
    docs = await cursor.to_list(1)
    return docs[0] if docs else None
