"""
Commerce Rules — centralized commercial truth enforcement.

Single source of truth for:
  - order action policy (confirm, complete, cancel, edit)
  - transaction mode behavioral contracts
  - occurrence availability validation
  - rental request validation
  - confirmation eligibility (payment gating)

Design: conservative, truthful, explicit.
No booking engine. No capacity locking. No conflict resolution.
Only prevent lies — don't promise availability we can't guarantee.
"""

import logging
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)


# ── Order Action Policy ────────────────────────────────────────────────────

def _action(allowed=False, reason=None, severity="normal", confirm_text=None, warn_text=None):
    """Build an action policy entry."""
    return {"allowed": allowed, "reason": reason, "severity": severity,
            "confirm_text": confirm_text, "warn_text": warn_text}


def get_order_actions(order: dict) -> Dict[str, dict]:
    """Return the canonical action policy for an order.

    Single source of truth for what admin actions are allowed, and why.
    Used by both backend (guard) and frontend (CTA visibility + confirmation).

    Each action returns:
      allowed:      bool
      reason:       str | None (why blocked)
      severity:     "normal" | "warning" | "danger"
      confirm_text: str | None (if set, frontend must confirm with this text)
      warn_text:    str | None (shown below the button as context)
    """
    status = order.get("status", "draft")
    pi = order.get("payment_intent", "none")

    ps = order.get("payment_status", "pending")

    actions = {
        "confirm":    _action(),
        "complete":   _action(),
        "cancel":     _action(),
        "edit":       _action(),
        "mark_paid":  _action(),
        "mark_unpaid": _action(),
        # WS-1.1 consolidamento — "il cliente ha pagato fuori piattaforma"
        # (bonifico/contanti): conferma + registra l'incasso in un'azione.
        "settle_manual": _action(),
    }

    if status == "draft":
        # Confirm
        if pi == "required":
            actions["confirm"] = _action(reason="payment_not_collected")
            # ...ma il bonifico esterno deve avere una via d'uscita:
            actions["settle_manual"] = _action(allowed=True,
                confirm_text="settle_manual_confirm")
        elif pi == "collected":
            actions["confirm"] = _action(allowed=True,
                warn_text="confirm_retry_safe")
        else:
            actions["confirm"] = _action(allowed=True,
                confirm_text="confirm_draft")
            actions["settle_manual"] = _action(allowed=True,
                confirm_text="settle_manual_confirm")

        # Complete: never from draft
        actions["complete"] = _action(reason="not_confirmed")

        # Cancel
        if pi == "collected":
            actions["cancel"] = _action(allowed=True, severity="danger",
                confirm_text="cancel_paid_draft",
                warn_text="warn_payment_collected")
        else:
            actions["cancel"] = _action(allowed=True,
                confirm_text="cancel_draft")

        # Edit
        if pi == "collected":
            actions["edit"] = _action(reason="payment_collected")
        else:
            actions["edit"] = _action(allowed=True)

    elif status == "confirmed":
        actions["confirm"] = _action(reason="already_confirmed")
        actions["complete"] = _action(allowed=True,
            confirm_text="complete_confirmed")
        actions["cancel"] = _action(allowed=True, severity="danger",
            confirm_text="cancel_confirmed",
            warn_text="warn_storno")
        actions["edit"] = _action(reason="already_confirmed")
        # Payment toggle — confirmed orders
        if ps != "paid":
            actions["mark_paid"] = _action(allowed=True, confirm_text="mark_paid_confirm")
        else:
            actions["mark_unpaid"] = _action(allowed=True, confirm_text="mark_unpaid_confirm")

    elif status == "completed":
        actions["confirm"] = _action(reason="already_completed")
        actions["complete"] = _action(reason="already_completed")
        actions["cancel"] = _action(reason="already_completed")
        actions["edit"] = _action(reason="already_completed")
        # Payment toggle — completed orders (rare, for corrections)
        if ps != "paid":
            actions["mark_paid"] = _action(allowed=True, confirm_text="mark_paid_confirm")
        else:
            actions["mark_unpaid"] = _action(allowed=True, confirm_text="mark_unpaid_confirm")

    elif status == "cancelled":
        actions["confirm"] = _action(reason="order_cancelled")
        actions["complete"] = _action(reason="order_cancelled")
        actions["cancel"] = _action(reason="already_cancelled")
        actions["edit"] = _action(reason="order_cancelled")

    return actions


# ── Confirmation Eligibility ───────────────────────────────────────────────

def can_confirm_order(order: dict, skip_payment_check: bool = False) -> Tuple[bool, str]:
    """Single source of truth for order confirmation eligibility.

    Called by order_service.confirm_order() before any state change.

    Rules:
    - cancelled orders cannot be confirmed
    - payment_intent="required" blocks confirmation unless payment collected
    - skip_payment_check=True bypasses payment gating (used by payment webhook
      after verified collection)
    - payment_intent="none"/"waived"/"collected" → confirmable

    Returns (can_confirm: bool, reason: str).
    """
    if order.get("status") == "cancelled":
        return False, "order_cancelled"

    if not skip_payment_check:
        pi = order.get("payment_intent", "none")
        if pi == "required":
            return False, "payment_not_collected"

    return True, "eligible"


def can_cancel_order(order: dict) -> Tuple[bool, str]:
    """Check if an order can be cancelled.

    Rules:
    - completed orders cannot be cancelled
    - already cancelled → idempotent (handled by service, not here)
    - draft and confirmed can be cancelled

    Returns (can_cancel: bool, reason: str).
    """
    if order.get("status") == "completed":
        return False, "order_completed"
    if order.get("status") == "cancelled":
        return False, "already_cancelled"
    return True, "eligible"


def can_complete_order(order: dict) -> Tuple[bool, str]:
    """Check if an order can be completed.

    Rules:
    - only confirmed orders can be completed
    - draft/cancelled/completed → not eligible

    Returns (can_complete: bool, reason: str).
    """
    if order.get("status") != "confirmed":
        return False, f"status_is_{order.get('status', 'unknown')}"
    return True, "eligible"


# ── Occurrence Availability ────────────────────────────────────────────────

async def validate_occurrence_for_order(
    occurrence_id: str,
    org_id: str,
    product_id: str,
    requested_quantity: float = 1,
) -> Tuple[bool, str, Optional[dict]]:
    """Validate that an occurrence is available for ordering.

    Checks:
      1. Occurrence exists and belongs to org + product
      2. Status is "published" (not draft/closed/cancelled)
      3. If capacity is set, warn (but don't block — no atomic reservation yet)

    Returns (valid: bool, reason: str, occurrence: dict | None).

    Note: capacity check is advisory, not enforced. True enforcement requires
    atomic reservation which is out of scope for this wave. The system remains
    truthfully request-oriented for capacity.
    """
    from database import event_occurrences_collection

    occ = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id, "product_id": product_id},
        {"_id": 0},
    )

    if not occ:
        return False, "occurrence_not_found", None

    status = occ.get("status", "draft")

    if status == "cancelled":
        return False, "occurrence_cancelled", occ
    if status == "closed":
        return False, "occurrence_closed", occ
    if status == "draft":
        return False, "occurrence_not_published", occ
    if status != "published":
        return False, f"occurrence_status_invalid:{status}", occ

    # Capacity enforcement — block if sold out.
    # A2 (Onda 12): combiniamo due fonti per ridurre la race window:
    #   1. `reserved_seats` — counter atomico incrementato al confirm_order
    #      via try_reserve_event_seats (P7/E1). Rappresenta i posti già
    #      CONFERMATI al millisecond-level.
    #   2. Aggregate dei DRAFT non ancora confermati — posti "in carrello"
    #      ma non ancora pagati. Restano anche se la validazione è advisory.
    # Il remaining è capacity - max(reserved_seats, booked_qty_including_drafts).
    capacity = occ.get("capacity")
    if capacity is not None and capacity > 0:
        from database import orders_collection
        reserved_seats = int(occ.get("reserved_seats") or 0)

        # Count booked seats (sum of quantities) from non-cancelled orders
        pipeline = [
            {"$match": {
                "organization_id": org_id,
                "status": {"$ne": "cancelled"},
                "items.occurrence_id": occurrence_id,
            }},
            {"$unwind": "$items"},
            {"$match": {"items.occurrence_id": occurrence_id}},
            {"$group": {"_id": None, "total_qty": {"$sum": "$items.quantity"}}},
        ]
        cursor = orders_collection.aggregate(pipeline)
        agg = await cursor.to_list(1)
        booked_qty = agg[0]["total_qty"] if agg else 0

        # Effective booked is the max of the two signals (reserved_seats is
        # authoritative after confirm; booked_qty covers drafts in flight).
        effective_booked = max(reserved_seats, int(booked_qty))
        remaining = capacity - effective_booked
        if remaining < requested_quantity:
            logger.info(
                "commerce_rules: occurrence %s capacity full "
                "(reserved=%d, booked=%d, effective=%d/%d, requested=%d)",
                occurrence_id, reserved_seats, booked_qty,
                effective_booked, capacity, requested_quantity,
            )
            occ["_booked_qty"] = effective_booked
            occ["_remaining"] = max(0, remaining)
            return False, "occurrence_sold_out", occ

    return True, "available", occ


def is_direct_checkout_safe(order: dict) -> Tuple[bool, str]:
    """Check if direct checkout (payment before manual review) is semantically
    safe for the items in this order.

    Post-P7/P8: both rental (range) and event_ticket (capacity) gain
    atomic reservation at confirm time, so there is no longer a sync-
    level reason to block direct checkout for those types. Occurrence
    capacity is still re-checked in is_direct_checkout_safe_async for
    a precise, DB-backed answer before payment collection.

    Returns (safe: bool, reason: str).
    """
    return True, "safe"


# ── Fulfillment Action Policy (v10.0) ─────────────────────────────────────

def get_fulfillment_actions(order: dict) -> Dict[str, dict]:
    """Return policy-driven fulfillment actions based on current mode + status.

    Returns dict with action keys and their allowed/blocked state.
    Frontend uses this to render fulfillment buttons.
    """
    ff = order.get("fulfillment") or {}
    mode = ff.get("mode", "not_required")
    ff_status = ff.get("status", "not_required")
    order_status = order.get("status", "draft")

    # Fulfillment actions only available on confirmed/completed orders
    if order_status not in ("confirmed", "completed"):
        return {}

    if mode == "not_required":
        return {}

    actions = {}

    if mode == "shipping":
        if ff_status == "pending":
            actions["mark_shipped"] = _action(allowed=True, confirm_text="fulfillment_mark_shipped")
        elif ff_status == "shipped":
            actions["mark_delivered"] = _action(allowed=True, confirm_text="fulfillment_mark_delivered")

    elif mode == "local_pickup":
        if ff_status == "pending":
            actions["mark_ready_for_pickup"] = _action(allowed=True, confirm_text="fulfillment_mark_ready")
        elif ff_status == "ready_for_pickup":
            actions["mark_picked_up"] = _action(allowed=True, confirm_text="fulfillment_mark_picked_up")

    elif mode == "manual_arrangement":
        if ff_status == "pending":
            actions["mark_fulfilled"] = _action(allowed=True, confirm_text="fulfillment_mark_fulfilled")

    return actions


# ── Order Composition Analysis ─────────────────────────────────────────────

def analyze_order_composition(order: dict) -> Optional[Dict]:
    """Analyze an order's composition for mixed-intent semantics.

    Detects when an order contains lines with different transaction_mode
    or item_type combinations that affect how the order should be processed.

    Returns a dict or None if composition is uniform.

    Returns:
      {
        "mixed_modes": bool,
        "modes_present": list[str],
        "mixed_types": bool,
        "types_present": list[str],
        "has_temporal": bool,       # rental or event lines
        "has_inquiry": bool,        # any zero-price / inquiry lines
        "degraded_from": str|None,  # if any line was direct but order is request
        "message": str|None,        # Italian description for operator
      }
    """
    items = order.get("items", [])
    if not items:
        return None

    modes = list(set(it.get("transaction_mode", "request") for it in items))
    types = list(set(it.get("item_type", "physical") for it in items))
    has_temporal = any(it.get("rental_date_from") or it.get("occurrence_id") for it in items)
    has_inquiry = any(it.get("line_total", 0) <= 0 and it.get("quantity", 0) > 0 for it in items)

    is_mixed_modes = len(modes) > 1
    degraded_from = None
    message = None

    if is_mixed_modes:
        if "direct" in modes:
            degraded_from = "direct"
            other_modes = [m for m in modes if m != "direct"]
            message = f"Ordine misto: articoli diretti combinati con articoli {'/'.join(other_modes)}. Trattato come richiesta."
        elif "approval" in modes:
            degraded_from = "approval"
            message = "Ordine misto: articoli con approvazione combinati con articoli standard. Trattato come richiesta."

    if not is_mixed_modes and not has_temporal and not has_inquiry:
        return None  # uniform, simple — no composition note needed

    return {
        "mixed_modes": is_mixed_modes,
        "modes_present": sorted(modes),
        "mixed_types": len(types) > 1,
        "types_present": sorted(types),
        "has_temporal": has_temporal,
        "has_inquiry": has_inquiry,
        "degraded_from": degraded_from,
        "message": message,
    }


async def is_direct_checkout_safe_async(order: dict, org_id: str) -> Tuple[bool, str]:
    """Async version that verifies direct checkout is safe.

    Post-P7/P8: both rental and event_ticket have atomic reservation
    primitives that run at confirm time, so there is no longer a
    blanket reason to block direct checkout. The authoritative
    guarantee is provided by try_reserve_rental_range (P8) and
    try_reserve_event_seats (P7). A late-arriving conflict at confirm
    time is handled by the reservation primitive returning a
    structured conflict, not by denying payment up-front.

    Returns (safe: bool, reason: str).
    """
    return True, "safe"


# ── Occurrence Status Transitions ──────────────────────────────────────────

VALID_OCCURRENCE_TRANSITIONS = {
    # Online/Offline is a visibility toggle — merchants must be able to flip
    # it freely (published → draft is "go offline"). Only `cancelled` is
    # terminal (cancelling an event is a commitment to customers).
    "draft": {"published", "closed", "cancelled"},
    "published": {"draft", "closed", "cancelled"},
    "closed": {"draft", "published", "cancelled"},
    "cancelled": set(),           # cancelled is terminal
}


def validate_occurrence_transition(current: str, target: str) -> Tuple[bool, str]:
    """Validate an occurrence status transition.

    Returns (valid: bool, reason: str).
    """
    allowed = VALID_OCCURRENCE_TRANSITIONS.get(current, set())
    if target not in allowed:
        return False, f"Transizione non valida: {current} → {target}"
    return True, "valid"


# ── Order Review / Approval Semantics ──────────────────────────────────────

def derive_review_info(order: dict) -> Optional[Dict]:
    """Derive the review/approval state for an order with reason context.

    Returns a dict or None if no special review is needed.

    Returns:
      {
        "state":   str,   — the review state for filtering
        "reason":  str,   — specific reason code
        "message": str,   — operator-facing Italian description
      }

    States:
      "paid_needs_confirm" — payment collected but confirmation failed
      "needs_payment"      — direct-mode order awaiting payment
      "needs_approval"     — approval-mode order awaiting operator review
      "needs_review"       — rental/event order needs availability check
    """
    source = order.get("source", "")
    pi = order.get("payment_intent", "none")
    status = order.get("status", "draft")

    # Confirmed/completed + fulfilled but unpaid — prompt to collect payment
    if status in ("confirmed", "completed"):
        ff = order.get("fulfillment") or {}
        ps = order.get("payment_status", "pending")
        ff_status = ff.get("status", "not_required")
        if ps != "paid" and ff_status in ("delivered", "picked_up", "fulfilled"):
            return {"state": "fulfilled_unpaid", "reason": "delivered_not_paid",
                    "message": "Ordine consegnato ma pagamento non registrato"}
        return None

    if status != "draft":
        return None

    # Payment-collected but unconfirmed — critical recovery state
    if pi == "collected":
        return {"state": "paid_needs_confirm", "reason": "confirm_failed"}

    if pi == "required":
        items = order.get("items", [])
        has_rental = any(it.get("item_type") == "rental" for it in items)
        has_capped_event = any(
            it.get("item_type") == "event_ticket" and it.get("occurrence_id")
            for it in items
        )
        if has_rental:
            return {"state": "needs_payment", "reason": "rental_needs_availability"}
        if has_capped_event:
            return {"state": "needs_payment", "reason": "event_needs_capacity_check"}
        return {"state": "needs_payment", "reason": "awaiting_payment"}

    if source == "storefront_approval":
        return {"state": "needs_approval", "reason": "approval_required"}

    items = order.get("items", [])
    has_rental = any(it.get("rental_date_from") for it in items)
    has_event = any(it.get("occurrence_id") for it in items)

    if has_rental and source.startswith("storefront"):
        return {"state": "needs_review", "reason": "rental_availability"}
    if has_event and source.startswith("storefront"):
        return {"state": "needs_review", "reason": "event_availability"
        }

    return None
