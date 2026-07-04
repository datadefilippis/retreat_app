#!/usr/bin/env python3
"""
backfill_customer_marketing_status.py
======================================
2026-05-20 — One-shot backfill that derives ``customer.accepted_marketing_at``
and ``customer.marketing_revoked_at`` from the ``consent_audit`` event log.

Why
---
Before 2026-05-20, marketing opt-in events were written only to:
  - consent_audit_collection (legal proof, always)
  - customer_accounts.accepted_marketing_at (only for REGISTERED customers)

Guest customers who ticked the marketing checkbox at checkout were
recorded in consent_audit (their consent is legally valid) but the
admin Customer Insights table showed them as "not opted-in" because
that view reads from customer_account, which guests don't have.

The fix shipped on 2026-05-20 added accepted_marketing_at /
marketing_revoked_at on the CRM ``customers`` collection so the admin
view can read a uniform source-of-truth covering both registered and
guest customers. The runtime now writes those fields on every
checkout opt-in and on every unsubscribe link click.

This script catches up the HISTORICAL state: for every existing CRM
customer, derive the marketing status from the most recent consent_audit
event with document_type="merchant_marketing", and snapshot it onto the
customer row.

Algorithm (per org)
-------------------
  1. Load every CRM customer in the org (id, email).
  2. For each unique email present in consent_audit, fetch the latest
     ``merchant_marketing`` event (sort accepted_at DESC, limit 1).
  3. Map the event source to a snapshot:
       customer_marketing_optin   →  $set accepted_marketing_at
       customer_marketing_revoke  →  $set marketing_revoked_at
       customer_checkout          →  $set accepted_marketing_at
       (anything else)            →  skip
  4. Update the CRM customer row with the derived timestamps.
  5. Idempotent: if the customer's accepted/revoked timestamps are
     already >= the audit timestamp (forward-write from a fresh
     runtime path), do not regress.

Usage
-----
  python -m scripts.backfill_customer_marketing_status                 # dry-run all orgs
  python -m scripts.backfill_customer_marketing_status --apply          # commit
  python -m scripts.backfill_customer_marketing_status --org-id <id>    # one org
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Dict, Optional

# Make backend importable when run as a script.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("backfill_customer_marketing_status")


# Event sources that imply an OPT-IN snapshot.
_OPTIN_SOURCES = {
    "customer_marketing_optin",
    "customer_checkout",      # only when the doc_type below is satisfied
}
# Event sources that imply a REVOKE snapshot.
_REVOKE_SOURCES = {
    "customer_marketing_revoke",
}


async def _latest_marketing_event_per_email(
    org_id: str,
) -> Dict[str, dict]:
    """For each customer_email in this org's consent_audit, return the
    most recent event with document_type='merchant_marketing'.

    Returns dict keyed by lowercased email, value is the audit doc.
    """
    from database import consent_audit_collection

    pipeline = [
        {
            "$match": {
                "organization_id": org_id,
                "document_type": "merchant_marketing",
                "customer_email": {"$ne": None, "$exists": True},
            },
        },
        # Sort newest-first so the $first in the next stage picks the latest.
        {"$sort": {"accepted_at": -1}},
        {
            "$group": {
                "_id": "$customer_email",
                "latest": {"$first": "$$ROOT"},
            },
        },
    ]
    out: Dict[str, dict] = {}
    async for doc in consent_audit_collection.aggregate(pipeline):
        email = (doc.get("_id") or "").strip().lower()
        if not email:
            continue
        out[email] = doc["latest"]
    return out


async def _backfill_org(org_id: str, *, apply: bool) -> dict:
    """Backfill all CRM customers in one org. Returns stats dict."""
    from database import customers_collection
    from datetime import datetime, timezone

    stats = {
        "org_id": org_id,
        "customers_scanned": 0,
        "would_optin": 0,
        "would_revoke": 0,
        "would_skip_no_audit": 0,
        "would_skip_already_current": 0,
        "applied": 0,
        "errors": 0,
    }

    # 1. Build the email -> latest_marketing_event map for this org.
    latest_map = await _latest_marketing_event_per_email(org_id)

    # 2. Iterate CRM customers (we DO want every active+inactive).
    cursor = customers_collection.find(
        {"organization_id": org_id, "email": {"$ne": None, "$exists": True}},
        {
            "_id": 0,
            "id": 1,
            "email": 1,
            "accepted_marketing_at": 1,
            "marketing_revoked_at": 1,
        },
    )

    async for cust in cursor:
        stats["customers_scanned"] += 1
        raw_email = (cust.get("email") or "").strip()
        email_key = raw_email.lower()
        if not email_key:
            continue

        event = latest_map.get(email_key)
        if not event:
            stats["would_skip_no_audit"] += 1
            continue

        source = event.get("source")
        event_ts = event.get("accepted_at")  # ISO string

        # Build the $set dict based on source.
        update_set: dict = {}
        if source in _OPTIN_SOURCES:
            # For customer_checkout, only treat as opt-in if a sibling
            # customer_marketing_optin row exists at the same timestamp
            # — otherwise checkout events are agnostic on marketing.
            # The aggregation grouped by email already returns the
            # latest merchant_marketing-typed event; if its source is
            # customer_checkout AND document_type is merchant_marketing,
            # that already implies the customer ticked the marketing
            # box at the merchant's request (audit row only created
            # when gdpr_marketing_accepted=True).
            existing_accepted = cust.get("accepted_marketing_at")
            existing_revoked = cust.get("marketing_revoked_at")
            # Idempotence: if the customer doc already has accepted_at
            # >= event_ts AND no later revoke, skip — runtime already
            # caught up.
            if (
                existing_accepted
                and existing_accepted >= event_ts
                and (not existing_revoked or existing_accepted > existing_revoked)
            ):
                stats["would_skip_already_current"] += 1
                continue
            update_set["accepted_marketing_at"] = event_ts
            # If a revoke happened BEFORE this opt-in, the opt-in wins
            # (most recent wins). The runtime $set already nullifies
            # revoked_at on a fresh opt-in; mirror that here.
            update_set["marketing_revoked_at"] = None
            stats["would_optin"] += 1
        elif source in _REVOKE_SOURCES:
            existing_revoked = cust.get("marketing_revoked_at")
            if existing_revoked and existing_revoked >= event_ts:
                stats["would_skip_already_current"] += 1
                continue
            update_set["marketing_revoked_at"] = event_ts
            stats["would_revoke"] += 1
        else:
            stats["would_skip_no_audit"] += 1
            continue

        if not apply:
            continue

        try:
            update_set["updated_at"] = datetime.now(timezone.utc).isoformat()
            await customers_collection.update_one(
                {"id": cust["id"], "organization_id": org_id},
                {"$set": update_set},
            )
            stats["applied"] += 1
        except Exception as exc:
            logger.error(
                "org=%s customer=%s update failed: %s",
                org_id, cust.get("id"), exc,
            )
            stats["errors"] += 1

    return stats


async def _list_orgs_with_customers() -> list:
    from database import customers_collection
    return await customers_collection.distinct("organization_id")


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually write the updates (default dry-run).")
    parser.add_argument("--org-id", default=None,
                        help="Restrict to one org.")
    args = parser.parse_args()

    if args.org_id:
        org_ids = [args.org_id]
    else:
        org_ids = await _list_orgs_with_customers()

    logger.info(
        "backfill_customer_marketing_status: %s mode, %d org(s)",
        "APPLY" if args.apply else "DRY-RUN", len(org_ids),
    )

    grand_total: Dict[str, int] = {
        "orgs": 0, "customers_scanned": 0, "would_optin": 0,
        "would_revoke": 0, "would_skip_no_audit": 0,
        "would_skip_already_current": 0, "applied": 0, "errors": 0,
    }
    for org_id in org_ids:
        try:
            stats = await _backfill_org(org_id, apply=args.apply)
        except Exception as exc:
            logger.error("org=%s crashed: %s", org_id, exc, exc_info=True)
            continue
        grand_total["orgs"] += 1
        for k in (
            "customers_scanned", "would_optin", "would_revoke",
            "would_skip_no_audit", "would_skip_already_current",
            "applied", "errors",
        ):
            grand_total[k] += stats.get(k, 0)
        logger.info(
            "org=%s scanned=%d optin=%d revoke=%d skipped(no_audit/already)=%d/%d applied=%d errors=%d",
            org_id, stats["customers_scanned"],
            stats["would_optin"], stats["would_revoke"],
            stats["would_skip_no_audit"],
            stats["would_skip_already_current"],
            stats["applied"], stats["errors"],
        )

    logger.info("──────────────────────────── SUMMARY ────────────────────────────")
    logger.info(
        "orgs=%d scanned=%d optin=%d revoke=%d skipped(no_audit/already)=%d/%d applied=%d errors=%d",
        grand_total["orgs"], grand_total["customers_scanned"],
        grand_total["would_optin"], grand_total["would_revoke"],
        grand_total["would_skip_no_audit"],
        grand_total["would_skip_already_current"],
        grand_total["applied"], grand_total["errors"],
    )
    if not args.apply:
        logger.info("(dry-run — re-run with --apply to commit)")


if __name__ == "__main__":
    asyncio.run(main())
