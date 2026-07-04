"""
Stock service — centralized physical-goods inventory primitives.

Before this module, stock handling was scattered:

  - order_service.confirm_order (lines ~314-329) did an atomic
    $inc: -qty with filter stock_quantity >= qty.
  - order_service.cancel_order (lines ~553-566) did the matching
    restore with $inc: +qty.
  - No pre-flight check at validation time — storefront discovered
    sold-out only after attempting confirm, and the "failure" was a
    silent no-op (modified_count=0 logged-only, order still confirmed).
  - No unified way to distinguish "product not tracked" (stock_quantity
    is None) from "insufficient stock" — both resulted in
    modified_count=0 without reason.

This module consolidates the contract:

  check_stock_available(org_id, product_id, qty)
    Read-only pre-flight. Returns one of:
      ("available", remaining)      stock tracked and sufficient
      ("untracked", None)           product has no stock_quantity
      ("insufficient", remaining)   tracked, remaining < qty
      ("not_found", None)           product missing

  try_decrement_stock(order_id, org_id, product_id, qty)
    Atomic decrement. Uses the same server-side primitive that
    order_service.confirm_order already used (find_one_and_update with
    stock_quantity >= qty in the filter), but now also:
      - Separates the "untracked" path (no-op, returns ok=True).
      - Distinguishes stock_quantity<qty from "product missing" via a
        cheap post-failure fetch.
      - Returns a structured reason instead of silent logging.

  restore_stock_for_order(order_id, org_id, items)
    Cancel-path restore. Iterates items, applies $inc:+qty per product
    filtered on stock_quantity != None (untracked products skipped).

Design parity with P5 (booking) / P7 (event) / P8 (rental):
  - Atomic primitive at confirm time.
  - Pre-flight check at validator time (advisory, may false-negative
    under race).
  - Structured reason codes; no exceptions on the happy path.
  - Zero index migration required — all logic is $inc + predicate.

Backward compat:
  - Products with stock_quantity == None remain untracked (no decrement,
    no blocking). This matches the pre-P10 behavior.
  - Pre-P10 orders were counted implicitly by the confirm-time decrement
    already running; nothing in history is re-computed.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, List

from models.common import utc_now

logger = logging.getLogger(__name__)


# Read-only pre-flight ------------------------------------------------------


async def check_stock_available(
    org_id: str,
    product_id: str,
    qty: int,
) -> Tuple[str, Optional[int]]:
    """Pre-flight availability check for a physical product.

    Returns (status, remaining) where status is one of:
      "available"     tracked, remaining >= qty
      "untracked"     product.stock_quantity is None (merchant chose
                      not to track) — order is allowed
      "insufficient"  tracked, remaining < qty
      "not_found"     product does not exist for this org
      "invalid_qty"   qty <= 0

    `remaining` is the CURRENT on-hand count, or None when untracked /
    not found / invalid. Safe to call repeatedly; no writes.
    """
    if not isinstance(qty, int) or qty <= 0:
        return "invalid_qty", None

    from database import products_collection

    prod = await products_collection.find_one(
        {"id": product_id, "organization_id": org_id},
        {"_id": 0, "stock_quantity": 1},
    )
    if prod is None:
        return "not_found", None

    on_hand = prod.get("stock_quantity")
    if on_hand is None:
        return "untracked", None

    try:
        on_hand_int = int(on_hand)
    except Exception:
        # Defensive: malformed stock. Treat as untracked rather than
        # breaking the order flow.
        return "untracked", None

    if on_hand_int < qty:
        return "insufficient", on_hand_int
    return "available", on_hand_int


# Atomic decrement ----------------------------------------------------------


async def try_decrement_stock(
    *,
    order_id: str,
    org_id: str,
    product_id: str,
    qty: int,
) -> Tuple[bool, str, Optional[int]]:
    """Atomically reserve `qty` units of stock for this order.

    Returns:
      (True, "decremented", remaining_after)  — stock decremented.
      (True, "untracked", None)               — product has no stock
                                                tracking; no-op success.
      (False, "insufficient_stock", on_hand)  — tracked, stock < qty.
      (False, "not_found", None)              — product missing.
      (False, "invalid_qty", None)            — qty <= 0.

    Never raises. The decrement uses find_one_and_update with the
    predicate stock_quantity >= qty baked into the filter; this is
    server-side atomic so concurrent callers cannot both pass the same
    "last unit" check.
    """
    if not isinstance(qty, int) or qty <= 0:
        return False, "invalid_qty", None

    from database import products_collection
    from pymongo import ReturnDocument

    updated = await products_collection.find_one_and_update(
        {
            "id": product_id,
            "organization_id": org_id,
            "stock_quantity": {"$ne": None, "$gte": qty},
        },
        {
            "$inc": {"stock_quantity": -qty},
            "$set": {"updated_at": utc_now()},
        },
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0, "stock_quantity": 1},
    )

    if updated is not None:
        remaining = updated.get("stock_quantity")
        logger.info(
            "stock: product %s decremented by %d for order %s (remaining=%s)",
            product_id[:12], qty, order_id[:12], remaining,
        )
        return True, "decremented", remaining

    # Decrement did not match. Disambiguate: not found vs untracked vs
    # insufficient. One extra read on the error path, no atomicity
    # concern because we already failed.
    prod = await products_collection.find_one(
        {"id": product_id, "organization_id": org_id},
        {"_id": 0, "stock_quantity": 1},
    )
    if prod is None:
        return False, "not_found", None

    on_hand = prod.get("stock_quantity")
    if on_hand is None:
        # Untracked — treat as success, no-op.
        return True, "untracked", None

    try:
        on_hand_int = int(on_hand)
    except Exception:
        return True, "untracked", None

    logger.info(
        "stock: insufficient for order %s product %s (on_hand=%d, requested=%d)",
        order_id[:12], product_id[:12], on_hand_int, qty,
    )
    return False, "insufficient_stock", on_hand_int


# Restore -------------------------------------------------------------------


async def restore_stock_for_order(
    order_id: str,
    org_id: str,
    items: List[dict],
) -> int:
    """Restore stock for each item in the given list.

    Called by cancel_order after a confirmed order is cancelled.
    Only products that currently have tracked stock (stock_quantity !=
    None) are incremented — untracked products are skipped by the filter.

    Returns the number of product rows actually updated.
    """
    if not items:
        return 0

    from database import products_collection

    restored = 0
    for item in items:
        pid = item.get("product_id")
        try:
            qty = int(item.get("quantity", 1))
        except Exception:
            continue
        if not pid or qty <= 0:
            continue
        try:
            res = await products_collection.update_one(
                {
                    "id": pid,
                    "organization_id": org_id,
                    "stock_quantity": {"$ne": None},
                },
                {
                    "$inc": {"stock_quantity": qty},
                    "$set": {"updated_at": utc_now()},
                },
            )
            if getattr(res, "modified_count", 0) > 0:
                restored += 1
                logger.info(
                    "stock: product %s restored +%d (cancel order %s)",
                    pid[:12], qty, order_id[:12],
                )
        except Exception as exc:
            logger.warning(
                "stock: restore failed for order %s product %s: %s",
                order_id, pid, exc,
            )
    return restored
