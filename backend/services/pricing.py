"""
pricing.py — centralized line total computation with extras (Onda 16).

Single source of truth for how an OrderLine's line_total is calculated
when the product has ProductExtra add-ons. Used by:

  - order_service.create_order (authoritative computation at create time)
  - /api/orders/price-preview (stateless preview for the storefront)
  - future: any admin recompute / repricing endpoints

DESIGN CONTRACT
  1. Pure function — no I/O, no database access. Callers hand in the
     already-resolved ProductExtra rows and the customer's selection.
  2. Frozen snapshot semantics — the output uses values from the
     ProductExtra rows passed in; those rows become the snapshot stored
     on OrderLine.extras. Subsequent edits to the underlying extras
     never alter historical totals.
  3. Server-authoritative for mandatory — the client cannot opt out of
     mandatory extras. Callers MUST pass in all active mandatory extras
     for the product; they're always applied regardless of
     ExtraSelections.mandatory_confirmed.
  4. One pick per radio group — within a single group_key the server
     accepts at most one radio_variant extra. Extras pointing to
     unknown group_keys are rejected.

OUTPUT
  {
    "base": float,                      # quantity * unit_price * (1 - discount_pct/100)
    "extras_total": float,              # sum of extras[i].line_total
    "total": float,                     # base + extras_total
    "day_count": Optional[int],         # None for slot; computed for range
    "extras": List[OrderLineExtra],     # ready-to-store snapshot array
    "extras_breakdown": List[{label, amount}],  # for SalesRecord.metadata
  }

NOTE ON DAY COUNT
  per_day multiplier uses (date_to - date_from).days + 1 so a 3-night
  booking Aug 14→17 pays for 3 days (nights). This matches the
  existing rental_availability and multiplier logic in order_service.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple


# ── Result shapes ───────────────────────────────────────────────────────────


@dataclass
class PricingResult:
    base: float
    extras_total: float
    total: float
    day_count: Optional[int]
    extras: List[Dict[str, Any]]                # OrderLineExtra.model_dump() shape
    extras_breakdown: List[Dict[str, Any]]      # [{label, amount}] for SalesRecord metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base": self.base,
            "extras_total": self.extras_total,
            "total": self.total,
            "day_count": self.day_count,
            "extras": self.extras,
            "extras_breakdown": self.extras_breakdown,
        }


class PricingError(Exception):
    """Raised on invalid extras_selection (unknown id, multiple radios per group)."""

    def __init__(self, code: str, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.context = context or {}


# ── Helpers ─────────────────────────────────────────────────────────────────


def _compute_day_count(date_from: Optional[str], date_to: Optional[str]) -> Optional[int]:
    """Inclusive day count for a range reservation.

    Aug 14 → Aug 17 returns 3 (matches rental_availability billing).
    Returns None when either bound is missing (slot flavor or legacy).
    """
    if not date_from:
        return None
    if not date_to or date_to == date_from:
        return 1
    try:
        d1 = date.fromisoformat(date_from)
        d2 = date.fromisoformat(date_to)
    except (TypeError, ValueError):
        return None
    if d2 < d1:
        return None
    return (d2 - d1).days + 1


def _extra_multiplier(
    modifier_type: str,
    day_count: Optional[int],
    quantity: float,
) -> float:
    """Multiplier for extra.unit_price given its modifier type + flavor ctx."""
    if modifier_type == "per_day":
        return float(day_count) if day_count and day_count > 0 else 1.0
    if modifier_type == "per_unit":
        return float(quantity) if quantity and quantity > 0 else 1.0
    # flat (default) — exactly one application regardless of days/qty.
    return 1.0


def compute_rental_multiplier(
    *,
    item_type: Optional[str],
    metadata: Optional[Dict[str, Any]],
    date_from: Optional[str],
    date_to: Optional[str],
    slot_date_from: Optional[str] = None,
    slot_time_from: Optional[str] = None,
    slot_date_to: Optional[str] = None,
    slot_time_to: Optional[str] = None,
) -> float:
    """Rental duration multiplier applied to the base price.

    Mirrors the logic in order_service.create_order so that the price-preview
    endpoints return the same `base` as the actual checkout does when the
    order is created. Callers pre-multiply `quantity` by this factor before
    passing it to `compute_line_total` (which has no knowledge of rental_unit).

    Rules (range flavor):
      - Non-rental items → 1.0 (no multiplier).
      - Rental without date_from → 1.0 (slot flavor or unselected).
      - rental_unit='settimana' → ceil(days / 7)
      - rental_unit='mese'      → ceil(days / 30)
      - Anything else (giorno, notte, ora, missing) → days (inclusive count).

    Rules (Onda 17, slot flavor with variable duration):
      - When slot_date_from + slot_time_from are provided AND the product is
        rental+flavor=slot, the multiplier becomes the reservation duration
        expressed in HOURS. unit_price is therefore interpreted as a per-hour
        price by convention. Supports cross-day (slot_date_to/slot_time_to).
      - slot_date_to defaults to slot_date_from (same-day) when absent —
        preserves legacy single-day slot orders.
      - If the slot fields are absent for a flavor=slot product, the function
        degrades to 1.0 (historic fixed pricing) so legacy rental+slot
        products created before Onda 17 keep working.

    Returns 1.0 on any parsing error so pricing degrades to "one period"
    rather than throwing a 500.
    """
    if item_type != "rental":
        return 1.0

    meta = metadata or {}
    flavor = (meta.get("reservation_flavor") or "").lower()

    # ── Onda 17: slot flavor with start/end timing → hourly multiplier ──
    if slot_date_from and slot_time_from and (flavor == "slot" or not flavor and not date_from):
        try:
            from datetime import datetime as _dt
            sd_from = slot_date_from
            sd_to = slot_date_to or slot_date_from
            st_from = slot_time_from
            st_to = slot_time_to or slot_time_from
            dt_from = _dt.fromisoformat(f"{sd_from}T{st_from}")
            dt_to = _dt.fromisoformat(f"{sd_to}T{st_to}")
            seconds = (dt_to - dt_from).total_seconds()
            if seconds <= 0:
                return 1.0
            hours = seconds / 3600.0
            # Round to 2 decimals so 1h30 → 1.5, 0h45 → 0.75. Sub-minute noise
            # is clipped away.
            return round(hours, 2)
        except (TypeError, ValueError):
            return 1.0

    if not date_from:
        return 1.0
    try:
        d_from = date.fromisoformat(date_from)
        d_to = date.fromisoformat(date_to) if date_to else d_from
    except (TypeError, ValueError):
        return 1.0
    days = max(1, (d_to - d_from).days + 1)
    unit = (meta.get("rental_unit") or "").lower()
    if unit == "settimana":
        return float(-(-days // 7))
    if unit == "mese":
        return float(-(-days // 30))
    return float(days)


# ── Main API ────────────────────────────────────────────────────────────────


def compute_line_total(
    *,
    unit_price: float,
    quantity: float,
    discount_pct: float = 0.0,
    extras_catalog: List[Dict[str, Any]],         # all ACTIVE ProductExtra rows for the product
    extras_selection: Optional[Dict[str, Any]] = None,   # ExtraSelections dict from the client
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> PricingResult:
    """Compute the authoritative line_total with extras resolution.

    Raises PricingError on invalid selection. The caller is expected to
    pre-filter extras_catalog to is_active=True and product-scoped rows.
    """
    sel = extras_selection or {}
    optional_ids = set(sel.get("optional_ids") or [])
    radio_picks = sel.get("radio_picks") or {}

    base = round(
        float(quantity) * float(unit_price) * (1.0 - float(discount_pct or 0) / 100.0),
        2,
    )
    day_count = _compute_day_count(date_from, date_to)

    # Index the catalog by id + by group_key for quick lookup.
    by_id: Dict[str, Dict[str, Any]] = {x["id"]: x for x in extras_catalog if x.get("id")}

    # Mandatory extras are always applied regardless of client input.
    mandatory = [x for x in extras_catalog if x.get("kind") == "mandatory"]
    # Optional extras selected by the customer.
    optionals = []
    for oid in optional_ids:
        ex = by_id.get(oid)
        if not ex:
            raise PricingError(
                "unknown_extra",
                f"Optional extra id {oid!r} not in product catalog.",
                {"extra_id": oid},
            )
        if ex.get("kind") != "optional":
            raise PricingError(
                "wrong_kind_optional",
                f"Extra {oid!r} is kind={ex.get('kind')!r}, not optional.",
                {"extra_id": oid},
            )
        optionals.append(ex)

    # Radio picks — one per group_key. The client sends {group_key: extra_id}.
    radios: List[Dict[str, Any]] = []
    for group_key, eid in radio_picks.items():
        if not eid:
            continue
        ex = by_id.get(eid)
        if not ex:
            raise PricingError(
                "unknown_extra",
                f"Radio extra id {eid!r} not in product catalog.",
                {"group_key": group_key, "extra_id": eid},
            )
        if ex.get("kind") != "radio_variant":
            raise PricingError(
                "wrong_kind_radio",
                f"Extra {eid!r} is kind={ex.get('kind')!r}, not radio_variant.",
                {"group_key": group_key, "extra_id": eid},
            )
        if ex.get("group_key") != group_key:
            raise PricingError(
                "group_key_mismatch",
                f"Extra {eid!r} belongs to group {ex.get('group_key')!r}, not {group_key!r}.",
                {"group_key": group_key, "extra_id": eid, "actual_group": ex.get("group_key")},
            )
        radios.append(ex)

    # Merge applied extras in a deterministic order: mandatory, then radios
    # (sorted by group_key for stability), then optionals.
    applied: List[Dict[str, Any]] = []
    applied.extend(sorted(mandatory, key=lambda x: (x.get("sort_order", 0), x.get("label", ""))))
    applied.extend(sorted(radios, key=lambda x: (x.get("group_key", ""), x.get("sort_order", 0))))
    applied.extend(sorted(optionals, key=lambda x: (x.get("sort_order", 0), x.get("label", ""))))

    extras_out: List[Dict[str, Any]] = []
    extras_breakdown: List[Dict[str, Any]] = []
    extras_total = 0.0
    for ex in applied:
        mod_type = ex.get("price_modifier_type") or "flat"
        multiplier = _extra_multiplier(mod_type, day_count, float(quantity or 1))
        unit = float(ex.get("price") or 0)
        line_total = round(unit * multiplier, 2)
        extras_total += line_total

        snapshot = {
            "extra_id": ex["id"],
            "kind": ex.get("kind", "optional"),
            "group_key": ex.get("group_key"),
            "label": ex.get("label", ""),
            "unit_price": unit,
            "price_modifier_type": mod_type,
            "quantity": multiplier,
            "line_total": line_total,
        }
        extras_out.append(snapshot)
        extras_breakdown.append({
            "label": ex.get("label", ""),
            "kind": ex.get("kind", "optional"),
            "amount": line_total,
        })

    extras_total = round(extras_total, 2)
    total = round(base + extras_total, 2)

    return PricingResult(
        base=base,
        extras_total=extras_total,
        total=total,
        day_count=day_count,
        extras=extras_out,
        extras_breakdown=extras_breakdown,
    )


def normalize_legacy_service_option(
    *,
    service_option_id: Optional[str],
    extras_catalog: List[Dict[str, Any]],
    existing_selection: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Back-compat shim — translate legacy scalar service_option_id into
    the new extra_selections.radio_picks shape when the client hasn't
    already sent one.

    Strategy: find the ProductExtra with matching extra_id (1:1 with the
    old ServiceOption id carried forward by the migration) and insert it
    as radio_picks[group_key].

    Safe to call even when service_option_id is None (returns the existing
    selection unchanged). Does not clobber an explicit radio_picks entry
    the caller already sent for the same group.
    """
    if not service_option_id:
        return existing_selection or {}
    target = None
    for ex in extras_catalog:
        if ex.get("id") == service_option_id and ex.get("kind") == "radio_variant":
            target = ex
            break
    if not target:
        # Unknown id or migrated to non-radio — let the upstream validator
        # handle the error cleanly instead of silently dropping.
        return existing_selection or {}

    merged = dict(existing_selection or {})
    radios = dict(merged.get("radio_picks") or {})
    group_key = target.get("group_key")
    if group_key and group_key not in radios:
        radios[group_key] = service_option_id
    merged["radio_picks"] = radios
    return merged
