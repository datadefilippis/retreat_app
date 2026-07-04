"""
issued_course_access_service.py — Release 4 (Courses) Step 5.

Issues IssuedCourseAccess (enrollment) rows after an order is confirmed.
Mirrors the pattern of issued_download_service.py, specialized for
item_type="course":

  * One enrollment per (order_id, order_line_index). Even if quantity > 1
    on a course line, we emit a single enrollment — a course is licensed
    nominatively per customer, not per seat.

  * Idempotent via the unique DB index on (order_id, order_line_index).
    On retry, the insert either succeeds (first run) or raises E11000
    and we read the existing row back.

  * Mandatory customer_account_id — guest orders with courses are
    blocked upstream by the public router (Step 4) so a course line
    ALWAYS carries a logged-in customer by the time it reaches here.
    The service still guards defensively and skips lines missing it.

  * course_id, title, access policy are resolved at emission time from
    product.metadata.course_id → Course document. The snapshot is
    frozen on the enrollment row so later admin edits to the course
    don't retroactively mutate the customer's expires_at.

Lifecycle:
  issue_for_order(order, org_id)   → called from order_service.confirm_order.
  revoke_for_order(order_id, reason) → called from order_service.cancel_order.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from models.common import utc_now
from models.issued_course_access import IssuedCourseAccess

logger = logging.getLogger(__name__)


def _generate_access_token() -> str:
    """Unguessable URL-safe token — 192-bit entropy. Used as an internal
    enrollment fingerprint (the customer-facing URL is authenticated via
    JWT, not by the token)."""
    return secrets.token_urlsafe(24)


def _compute_expires_at(course_doc: Dict[str, Any], enrolled_at: datetime) -> Optional[datetime]:
    """Resolve the expiry datetime from the Course access policy.

    Returns None for lifetime access (the default). For expiring courses,
    returns enrolled_at + access_expiry_days. Malformed values degrade
    silently to lifetime rather than crashing the confirm flow.
    """
    policy = (course_doc.get("access_policy") or "lifetime").lower()
    if policy != "expiring":
        return None
    raw_days = course_doc.get("access_expiry_days")
    try:
        days = int(raw_days) if raw_days is not None else None
    except (TypeError, ValueError):
        return None
    if not days or days <= 0:
        return None
    return enrolled_at + timedelta(days=days)


async def _resolve_course(
    *, org_id: str, product_doc: Dict[str, Any], course_cache: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Look up the Course for a product, caching across lines of the same order.

    Returns None when the product has no `metadata.course_id` or the course
    has been deleted / deactivated. Caller treats None as "skip this line"
    (best-effort, never raises).
    """
    from database import courses_collection

    meta = product_doc.get("metadata") or {}
    course_id = meta.get("course_id")
    if not course_id:
        return None

    cached = course_cache.get(course_id)
    if cached is not None:
        return cached or None  # empty dict sentinel → "lookup failed"

    doc = await courses_collection.find_one(
        {"id": course_id, "organization_id": org_id, "is_active": True},
        {"_id": 0},
    )
    # Store an empty dict on miss so subsequent lines with the same
    # course_id don't re-query Mongo.
    course_cache[course_id] = doc or {}
    return doc


def _build_enrollment_doc(
    *,
    org_id: str,
    order: Dict[str, Any],
    line_index: int,
    line: Dict[str, Any],
    product_doc: Dict[str, Any],
    course_doc: Dict[str, Any],
    now: datetime,
) -> Optional[Dict[str, Any]]:
    """Compose the IssuedCourseAccess dict for a course order line.

    Returns None when essential fields are missing — caller skips.
    """
    product_id = line.get("product_id")
    if not (product_id and course_doc.get("id")):
        return None

    customer_account_id = order.get("customer_account_id")
    if not customer_account_id:
        # Defensive: the public router blocks this upstream. If somehow
        # a course order reaches confirm without customer_account_id
        # (e.g. admin-created order), we decline to emit rather than
        # producing a broken enrollment.
        logger.warning(
            "issued_course_access_service: order %s line %d missing customer_account_id; skipping",
            order.get("id"), line_index,
        )
        return None

    expires_at = _compute_expires_at(course_doc, now)

    doc_model = IssuedCourseAccess(
        organization_id=org_id,
        order_id=order["id"],
        order_line_index=line_index,
        course_id=course_doc["id"],
        course_title_snapshot=course_doc.get("title", "") or line.get("product_name", ""),
        customer_account_id=customer_account_id,
        customer_id=order.get("customer_id"),
        access_token=_generate_access_token(),
        enrolled_at=now,
        expires_at=expires_at,
        revoked_at=None,
        progress={},
        last_accessed_at=None,
    )
    return doc_model.model_dump(mode="json")


async def issue_for_order(order: Dict[str, Any], org_id: str) -> List[Dict[str, Any]]:
    """Emit one IssuedCourseAccess per course line on the order.

    Idempotent per (order_id, order_line_index). Returns every enrollment
    associated with the order (newly inserted or pre-existing). Never
    raises — best-effort with logging.
    """
    from database import issued_course_accesses_collection, products_collection

    order_id = order.get("id")
    if not order_id:
        return []

    # Load existing enrollments for this order (idempotency source of truth).
    existing = await issued_course_accesses_collection.find(
        {"organization_id": org_id, "order_id": order_id},
        {"_id": 0},
    ).to_list(None)
    existing_by_index: Dict[int, Dict[str, Any]] = {
        r["order_line_index"]: r for r in existing if "order_line_index" in r
    }

    product_cache: Dict[str, Dict[str, Any]] = {}
    course_cache: Dict[str, Dict[str, Any]] = {}
    now = utc_now()
    issued: List[Dict[str, Any]] = []

    for line_index, line in enumerate(order.get("items", [])):
        if line.get("item_type") != "course":
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
        if not product_doc:
            continue

        # Idempotency — already emitted for this (order, line_index).
        if line_index in existing_by_index:
            issued.append(existing_by_index[line_index])
            continue

        course_doc = await _resolve_course(
            org_id=org_id, product_doc=product_doc, course_cache=course_cache,
        )
        if not course_doc:
            logger.warning(
                "issued_course_access_service: no active course for product %s (order=%s line=%d); skipping",
                product_id, order_id, line_index,
            )
            continue

        doc = _build_enrollment_doc(
            org_id=org_id,
            order=order,
            line_index=line_index,
            line=line,
            product_doc=product_doc,
            course_doc=course_doc,
            now=now,
        )
        if not doc:
            continue

        # Retry on rare access_token collisions (unique index). Order-line
        # collisions signal a concurrent confirm race — read back the row.
        for attempt in range(5):
            try:
                await issued_course_accesses_collection.insert_one(doc)
                doc.pop("_id", None)
                issued.append(doc)
                break
            except Exception as exc:
                msg = str(exc)
                if "E11000" in msg and "access_token" in msg and attempt < 4:
                    doc["access_token"] = _generate_access_token()
                    continue
                if "E11000" in msg and ("order_id" in msg or "order_line_index" in msg):
                    # Concurrent confirm — another writer won the race.
                    fresh = await issued_course_accesses_collection.find_one(
                        {"order_id": order_id, "order_line_index": line_index},
                        {"_id": 0},
                    )
                    if fresh:
                        issued.append(fresh)
                    break
                logger.warning(
                    "issued_course_access_service: insert failed order=%s line=%d: %s",
                    order_id, line_index, exc,
                )
                break

    if issued:
        logger.info(
            "issued_course_access_service: %d enrollment(s) present for order=%s org=%s",
            len(issued), order_id, org_id,
        )
    return issued


async def revoke_for_order(
    order_id: str, org_id: str, reason: str = "order_cancelled",
) -> int:
    """Mark all enrollments of an order as revoked.

    Used by order_service.cancel_order and (in Step 8) by the admin
    "revoke enrollment" endpoint. Never deletes — preserves audit trail.
    Returns the count of rows flipped to revoked. No-op on already-revoked
    rows (the {revoked_at: null} filter prevents double-set).
    """
    from database import issued_course_accesses_collection
    now = utc_now()
    result = await issued_course_accesses_collection.update_many(
        {
            "organization_id": org_id,
            "order_id": order_id,
            "revoked_at": None,
        },
        {
            "$set": {
                "revoked_at": now,
                "revoked_reason": reason,
                "updated_at": now,
            },
        },
    )
    if result.modified_count:
        logger.info(
            "issued_course_access_service: revoked %d enrollment(s) for order=%s reason=%s",
            result.modified_count, order_id, reason,
        )
    return result.modified_count


async def list_for_order(order_id: str, org_id: str) -> List[Dict[str, Any]]:
    """Admin-side lookup of every enrollment emitted for an order."""
    from database import issued_course_accesses_collection
    return await issued_course_accesses_collection.find(
        {"organization_id": org_id, "order_id": order_id},
        {"_id": 0},
    ).sort("order_line_index", 1).to_list(None)
