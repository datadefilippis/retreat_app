"""
Offer profiles registry — backend-authoritative single source of truth.

Before this module, the 6 offer profiles (direct_sale / request_sale /
quote / rental / open_event / capped_event) lived ONLY in the frontend
constants file (frontend/src/constants/itemTypes.js). The backend
stored the three atomic axes — item_type + transaction_mode +
price_mode — but never knew that certain combinations had canonical
names, defaults, or behavioral semantics.

Consequences:
  - Adding a profile required only a frontend change; servers with
    older clients could not reason about new profiles.
  - An API consumer (mobile, partner integration, AI agent) had no way
    to query the catalog of valid profiles server-side.
  - A misconfigured product could still be saved if the frontend
    derive-profile helper drifted from the backend's compatibility
    checks.

P11 brings the registry backend-side:
  - Declarative, frozen dataclass list of the 6 profiles.
  - Helpers to derive a profile_id from the three axes (mirrors the
    frontend deriveOfferProfile) and to look up a profile by id.
  - Schema-level optional offer_profile_id field on ProductBase so
    clients can identify a profile; the backend validates it and, when
    provided without full axes, fills the three atomic fields from the
    profile's defaults.
  - GET /api/catalog/offer-profiles endpoint (see routers) so the
    frontend can source the catalog from the server instead of
    duplicating constants.

Backward compatibility (mandatory for rollout):
  - offer_profile_id is OPTIONAL. Clients that omit it behave exactly
    as before — item_type + transaction_mode + price_mode are still
    the authoritative fields in the stored document.
  - Clients that send an UNKNOWN offer_profile_id receive a clear
    ValueError — we do not silently drop unknown profile ids, because
    that would mask a client bug.
  - This module does not rename or remove any existing field. It only
    adds optional knowledge on top.

Shape:
    @dataclass(frozen=True)
    class OfferProfile:
        id: str
        item_type: str
        transaction_mode: str
        price_mode: str
        behavior: str            # "checkout" | "review" | "conversation"
        description: str

The UI-only attributes (label, icon, field_hints, use_cases) stay in
the frontend — they are copywriting / UX concerns not needed by the
server. The server owns the CANONICAL AXES + behavior only.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class OfferProfile:
    id: str
    item_type: str
    transaction_mode: str
    price_mode: str
    behavior: str
    description: str

    def defaults(self) -> Dict[str, str]:
        """The three atomic axes this profile pre-fills, as a plain
        dict suitable for merging into a product payload."""
        return {
            "item_type": self.item_type,
            "transaction_mode": self.transaction_mode,
            "price_mode": self.price_mode,
        }


# Canonical list. Order matches the frontend catalog for UI stability
# (the frontend picker renders in this order). Additions go at the end
# so existing client snapshots keep working.
_OFFER_PROFILES_LIST: Tuple[OfferProfile, ...] = (
    OfferProfile(
        id="direct_sale",
        item_type="physical",
        transaction_mode="direct",
        price_mode="fixed",
        behavior="checkout",
        description="Vendita diretta: checkout immediato con prezzo fisso.",
    ),
    OfferProfile(
        id="request_sale",
        item_type="physical",
        transaction_mode="request",
        price_mode="fixed",
        behavior="review",
        description="Vendita su richiesta: il cliente invia l'ordine, l'admin conferma.",
    ),
    OfferProfile(
        id="quote",
        item_type="service",
        transaction_mode="request",
        price_mode="inquiry",
        behavior="conversation",
        description="Preventivo: prezzo concordato dopo una conversazione.",
    ),
    OfferProfile(
        id="rental",
        item_type="rental",
        transaction_mode="approval",
        price_mode="fixed",
        behavior="review",
        description="Noleggio con approvazione: verifica disponibilità prima di confermare.",
    ),
    OfferProfile(
        id="open_event",
        item_type="event_ticket",
        transaction_mode="direct",
        price_mode="fixed",
        behavior="checkout",
        description="Evento aperto: biglietto acquistabile direttamente.",
    ),
    OfferProfile(
        id="capped_event",
        item_type="event_ticket",
        transaction_mode="request",
        price_mode="fixed",
        behavior="review",
        description="Evento a capienza limitata: richiesta rivista prima della conferma.",
    ),
)

OFFER_PROFILES: Dict[str, OfferProfile] = {p.id: p for p in _OFFER_PROFILES_LIST}
OFFER_PROFILE_IDS: Tuple[str, ...] = tuple(p.id for p in _OFFER_PROFILES_LIST)


# ── Lookup helpers ──────────────────────────────────────────────────────────


def get_profile_by_id(profile_id: str) -> Optional[OfferProfile]:
    """Return the OfferProfile dataclass for a given id, or None."""
    if not profile_id:
        return None
    return OFFER_PROFILES.get(profile_id)


def derive_profile_from_axes(
    item_type: Optional[str],
    transaction_mode: Optional[str],
    price_mode: Optional[str],
) -> Optional[str]:
    """Mirror of the frontend deriveOfferProfile helper.

    Given the three atomic axes, returns the canonical profile_id when
    the combination matches exactly one registered profile, else None.
    Matching is strict — partial matches are not returned.

    Used when a client submits the three fields without an explicit
    offer_profile_id but we want to persist or surface the derived
    profile for analytics / reporting.
    """
    if not (item_type and transaction_mode and price_mode):
        return None
    for p in _OFFER_PROFILES_LIST:
        if (p.item_type == item_type
                and p.transaction_mode == transaction_mode
                and p.price_mode == price_mode):
            return p.id
    return None


def apply_profile_defaults(
    profile_id: str,
    payload: Dict,
) -> Dict:
    """Fill missing atomic axes from a profile's defaults.

    If `payload` already has item_type / transaction_mode / price_mode
    set to non-empty values, they are PRESERVED — the client's explicit
    choice always wins. Fields missing or empty in the payload are
    populated from profile.defaults().

    The mutation is shallow and returns the updated dict. Unknown
    profile_id is a silent no-op — validation is done separately at
    schema level so callers get a clean ValueError instead of a mystery
    success.
    """
    profile = get_profile_by_id(profile_id)
    if profile is None:
        return payload
    out = dict(payload)
    for key, default in profile.defaults().items():
        if not out.get(key):
            out[key] = default
    return out


def validate_profile_id(profile_id: Optional[str]) -> None:
    """Raise ValueError when profile_id is non-empty but unknown.

    Accepts None / "" as a pass-through — the field is optional.
    Called from Pydantic validators so the error surfaces as a normal
    422 with a clear message.
    """
    if not profile_id:
        return
    if profile_id not in OFFER_PROFILES:
        raise ValueError(
            f"offer_profile_id sconosciuto: {profile_id!r}. "
            f"Valori ammessi: {list(OFFER_PROFILE_IDS)}"
        )


def serialize_catalog() -> List[Dict]:
    """Return the full registry as a list of dicts, stable order.

    Intended for the GET /api/catalog/offer-profiles endpoint so the
    frontend can fetch this from the backend instead of duplicating
    the list in its constants. The payload includes every field of
    OfferProfile; UI-only decorations (label, icon, i18n) remain a
    frontend concern.
    """
    return [asdict(p) for p in _OFFER_PROFILES_LIST]
