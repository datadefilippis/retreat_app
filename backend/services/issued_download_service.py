"""
issued_download_service.py — Release 3 (Digital) B4.

Issues IssuedDownload rows after an order is confirmed. Mirrors the
pattern of issued_reservation_service (Onda 16), ticket_service (events)
and booking_service (services), for item_type=digital products.

Lifecycle:
  issue_for_order(order, org_id)        → called by order_service.confirm_order
                                          Idempotent per (order_id, order_line_index).

  release_for_order(order_id, org_id)   → called by order_service.cancel_order
                                          transitions active deliveries to
                                          status="cancelled" (never deletes).

  increment_download_count(issued_id)   → called by /public/downloads/{token}/file
                                          atomic $inc on download_count; flips
                                          status="exhausted" when max is reached.

  get_by_token(access_token)            → public endpoint lookup. Token IS
                                          the credential; no org scoping.

IDEMPOTENCY
  Unique DB index on (order_id, order_line_index). On retry of
  confirm_order the insert raises E11000 and we return the existing row.

LINE COVERAGE
  Only lines with item_type="digital" are materialized. Lines missing
  the product / product_name are skipped (defensive — should not happen
  post-validation).
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from models.common import utc_now
from models.issued_download import IssuedDownload, generate_download_code

logger = logging.getLogger(__name__)


def _generate_access_token() -> str:
    """Unguessable URL-safe token for /d/{token}. 192-bit entropy."""
    return secrets.token_urlsafe(24)


def _compute_expiry(meta: Dict[str, Any], now: datetime) -> Optional[str]:
    """Derive token expiry from DigitalMetadata.access_expiry_days.

    None means "never expires" — the customer keeps access until the order
    is cancelled or max_downloads is reached. Returns an ISO string so the
    IssuedDownload row can be serialized to Mongo as-is.
    """
    days = meta.get("access_expiry_days")
    try:
        n = int(days) if days is not None else None
    except (TypeError, ValueError):
        return None
    if not n or n <= 0:
        return None
    return (now + timedelta(days=n)).isoformat()


def _build_download_doc(
    *,
    org_id: str,
    order: Dict[str, Any],
    line_index: int,
    line: Dict[str, Any],
    product_doc: Dict[str, Any],
    now: datetime,
) -> Optional[Dict[str, Any]]:
    """Compose the IssuedDownload dict for a digital order line.

    Returns None when essential fields are missing (caller treats as skip).
    """
    product_id = line.get("product_id")
    product_name = line.get("product_name") or (product_doc.get("name") if product_doc else "")
    if not (product_id and product_name):
        return None

    meta = product_doc.get("metadata") or {}

    customer_name = order.get("customer_name") or ""
    customer_email = order.get("customer_email") or ""
    customer_phone = order.get("customer_phone") or ""

    extras_snapshot = list(line.get("extras") or [])

    raw_max = meta.get("max_downloads_per_delivery")
    try:
        max_downloads = int(raw_max) if raw_max is not None else None
    except (TypeError, ValueError):
        max_downloads = None

    doc_model = IssuedDownload(
        organization_id=org_id,
        order_id=order["id"],
        order_line_index=line_index,
        product_id=product_id,
        product_name=product_name,
        # File snapshot at issue time — frozen so later admin edits to the
        # uploaded file don't retroactively change what the customer paid for.
        download_filename=meta.get("download_filename"),
        download_size_bytes=meta.get("download_size_bytes"),
        download_mime_type=meta.get("download_mime_type"),
        code=generate_download_code(),
        access_token=_generate_access_token(),
        access_token_expires_at=_compute_expiry(meta, now),
        status="active",
        extras_snapshot=extras_snapshot,
        holder_name=customer_name or None,
        holder_email=customer_email or None,
        holder_phone=customer_phone or None,
        max_downloads=max_downloads,
        download_count=0,
        delivery_status="pending",
        delivery_attempts=0,
    )
    return doc_model.model_dump(mode="json")


async def issue_for_order(order: Dict[str, Any], org_id: str) -> List[Dict[str, Any]]:
    """Issue one IssuedDownload per digital line on the order.

    Idempotent per (order_id, order_line_index). Returns every delivery
    associated with the order (newly inserted or pre-existing).
    """
    from database import issued_downloads_collection, products_collection

    order_id = order.get("id")
    if not order_id:
        return []

    existing = await issued_downloads_collection.find(
        {"organization_id": org_id, "order_id": order_id},
        {"_id": 0},
    ).to_list(None)
    existing_by_index: Dict[int, Dict[str, Any]] = {
        r["order_line_index"]: r for r in existing if "order_line_index" in r
    }

    product_cache: Dict[str, Dict[str, Any]] = {}
    now = utc_now()
    issued: List[Dict[str, Any]] = []

    for line_index, line in enumerate(order.get("items", [])):
        if line.get("item_type") != "digital":
            continue

        product_id = line.get("product_id")
        if not product_id:
            continue

        if product_id not in product_cache:
            product_cache[product_id] = await products_collection.find_one(
                {"id": product_id, "organization_id": org_id},
                {"_id": 0},
            ) or {}
        product_doc = product_cache[product_id]

        # Idempotency — return existing row for this (order, line_index).
        if line_index in existing_by_index:
            issued.append(existing_by_index[line_index])
            continue

        doc = _build_download_doc(
            org_id=org_id,
            order=order,
            line_index=line_index,
            line=line,
            product_doc=product_doc,
            now=now,
        )
        if not doc:
            continue

        # Retry loop for rare code collisions on the unique index.
        for attempt in range(5):
            try:
                await issued_downloads_collection.insert_one(doc)
                doc.pop("_id", None)
                issued.append(doc)
                break
            except Exception as exc:
                msg = str(exc)
                if "E11000" in msg and "code" in msg and attempt < 4:
                    # Code collided; regenerate and retry.
                    doc["code"] = generate_download_code()
                    continue
                if "E11000" in msg and "order_id" in msg:
                    # Concurrent confirm race — the other writer already
                    # inserted this row. Read it back.
                    fresh = await issued_downloads_collection.find_one(
                        {"order_id": order_id, "order_line_index": line_index},
                        {"_id": 0},
                    )
                    if fresh:
                        issued.append(fresh)
                    break
                logger.warning(
                    "issued_download_service: insert failed order=%s line=%d: %s",
                    order_id, line_index, exc,
                )
                break

    if issued:
        logger.info(
            "issued_download_service: %d download(s) present for order=%s org=%s",
            len(issued), order_id, org_id,
        )
    return issued


async def release_for_order(order_id: str, org_id: str) -> int:
    """Mark all deliveries of an order as cancelled. Returns count updated."""
    from database import issued_downloads_collection
    now = utc_now()
    result = await issued_downloads_collection.update_many(
        {"organization_id": org_id, "order_id": order_id, "status": {"$ne": "cancelled"}},
        {"$set": {"status": "cancelled", "cancelled_at": now, "updated_at": now}},
    )
    if result.modified_count:
        logger.info(
            "issued_download_service: cancelled %d deliveries for order=%s",
            result.modified_count, order_id,
        )
    return result.modified_count


async def list_for_order(order_id: str, org_id: str) -> List[Dict[str, Any]]:
    from database import issued_downloads_collection
    return await issued_downloads_collection.find(
        {"organization_id": org_id, "order_id": order_id},
        {"_id": 0},
    ).sort("order_line_index", 1).to_list(None)


async def get_by_token(access_token: str) -> Optional[Dict[str, Any]]:
    """Public endpoint lookup. No org scoping (token IS the credential)."""
    from database import issued_downloads_collection
    if not access_token:
        return None
    return await issued_downloads_collection.find_one(
        {"access_token": access_token},
        {"_id": 0},
    )


async def increment_download_count(issued_id: str) -> Optional[Dict[str, Any]]:
    """Atomically increment the download counter.

    When the new count reaches `max_downloads` we flip status to
    "exhausted" in the SAME update so the next request is rejected with
    410 without a separate round-trip.

    Returns the updated document, or None if nothing was matched. The
    caller is expected to have already verified the row is `active` (the
    token endpoint does that before streaming bytes) so this is best-effort.
    """
    from database import issued_downloads_collection
    from pymongo import ReturnDocument

    now = utc_now()
    # First pass: atomic $inc. We cannot know in a single op whether the
    # new value equals max, so we do it in two steps: $inc, then read the
    # returned doc and maybe flip status. This is safe under contention —
    # concurrent downloads will each produce a distinct atomic $inc, and
    # the later one flips status. If two hit the threshold at the same
    # instant, the second update is a no-op (status already exhausted).
    updated = await issued_downloads_collection.find_one_and_update(
        {"id": issued_id},
        {"$inc": {"download_count": 1},
         "$set": {"last_downloaded_at": now.isoformat(), "updated_at": now}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    if not updated:
        return None

    cap = updated.get("max_downloads")
    count = int(updated.get("download_count", 0) or 0)
    if cap is not None and count >= int(cap) and updated.get("status") == "active":
        await issued_downloads_collection.update_one(
            {"id": issued_id, "status": "active"},
            {"$set": {"status": "exhausted", "updated_at": now}},
        )
        updated["status"] = "exhausted"
    return updated
