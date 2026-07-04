"""
Track E Step 1.2 — Cart inventory check (anti over-sell).

Pre-E1.2 lo stock check esisteva SOLO al checkout (services/order_creation_
service.py:270-283 + stock_service.try_decrement_stock at order confirm).
Customer poteva add unlimited qty al cart, scoprire al checkout che stock
insufficient → bad UX + order abandonment.

E1.2 introduce check EAGER al cart add/update:
  - Best-effort signal "questo product non puoi metterlo in qty N" PRIMA
    del checkout
  - Atomic guarantee rimane al confirm_order (try_decrement_stock con
    find_one_and_update predicate stock>=qty)
  - Pattern industry-standard (Shopify, WooCommerce, Stripe Checkout)

Threat model
============

Catches:
  - Single customer adds qty > stock (immediate feedback)
  - Customer adds qty=N when stock=0 (out of stock prevented)

Does NOT catch:
  - Race condition: 2 customer simultanei add last unit → entrambi
    passano il check, primo vince al confirm. Atomic decrement at
    try_decrement_stock e' la fonte ultima di verita'.
  - Stock change mid-session (admin decrease) → cart "stale" fino al
    refresh. Acceptable: customer vede error al checkout.

Per-product-type semantics
==========================

Inventory check si applica SOLO se ENTRAMBE condizioni:
  1. product.item_type ha requires_stock=True (physical, digital)
  2. product.stock_quantity is not None (esplicitamente tracked)

Skip se:
  - item_type ∈ {service, rental, event_ticket, course, booking} →
    questi types hanno loro logica (calendar, capacity, licensing)
  - stock_quantity is None → unlimited inventory (default per legacy
    products + intentional config "untracked")

Backward compatibility
======================

100%. Prodotti pre-esistenti senza stock_quantity → skip check (no-op,
allowed). Prodotti con item_type non-stock → skip check.

Solo prodotti che esplicitamente sono physical/digital CON stock_quantity
settato → check attivo. Stesso comportamento del legacy storefront
order_creation_service.py.

Public API
==========

    InsufficientStockError(product_id, requested, available, message)
        Exception strutturata con campi utili per HTTP error response.

    check_cart_items_inventory(items, products_by_id) -> None
        Itera items, verifica stock per ognuno. Raise
        InsufficientStockError sul primo violation (fail-fast).

    inventory_check_required(product_doc) -> bool
        Helper booleano: True se product e' soggetto a stock check.
        Esposto per uso esterno (es. UI hint, metrics filter).
"""

from typing import Iterable, Mapping, Optional


# ── Exception type ─────────────────────────────────────────────────────


class InsufficientStockError(Exception):
    """Raised when a cart item quantity exceeds product stock_quantity.

    Carries strutturata error info per HTTP error response shape
    canonical:

        {
          "code": "STOCK_INSUFFICIENT",
          "message": "...",
          "product_id": "...",
          "requested": N,
          "available": M,
        }

    Anti-info-leak: il message NON include product_id raw (potenziale
    leak di prodotto). Caller HTTP layer decide se exposare product_id
    nel response detail (per embed widget UI: si, vogliamo che il
    customer veda quale prodotto e' problematic).
    """

    def __init__(
        self,
        product_id: str,
        requested,  # float OR int — cart model usa float (e.g. 0.5 kg)
        available: int,
        message: Optional[str] = None,
    ):
        self.product_id = product_id
        self.requested = requested
        self.available = available
        # Format display: int se whole number, else stripped decimal.
        # 10.0 → "10", 0.5 → "0.5", 1.250 → "1.25".
        req_display = self._fmt_qty(requested)
        avail_display = str(available)
        self.message = message or (
            f"Quantita' richiesta ({req_display}) supera la disponibilita' "
            f"({avail_display})."
        )
        super().__init__(self.message)

    @staticmethod
    def _fmt_qty(value) -> str:
        """Format quantity per display: clean int o decimal stripped."""
        try:
            f = float(value)
        except (TypeError, ValueError):
            return str(value)
        if f.is_integer():
            return str(int(f))
        # Remove trailing zeros but keep at least 1 decimal
        return f"{f:g}"

    def to_detail(self) -> dict:
        """Serialize to HTTPException detail dict (canonical shape)."""
        return {
            "code": "STOCK_INSUFFICIENT",
            "message": self.message,
            "product_id": self.product_id,
            "requested": self.requested,
            "available": self.available,
        }


# ── Core logic ─────────────────────────────────────────────────────────


def inventory_check_required(product_doc: Mapping) -> bool:
    """True se il prodotto e' soggetto a inventory check.

    Conditions:
      - item_type ∈ {physical, digital} (requires_stock=True per type)
      - stock_quantity NON None (esplicitamente tracked)

    Args:
        product_doc: dict-like product document with at least
                     'item_type' + 'stock_quantity' fields.

    Returns:
        True se il check va applicato, False se skip (untracked /
        non-stock-type / legacy).

    Note: usiamo qui un set hardcoded {physical, digital} invece di
    importare PRODUCT_TYPES per evitare circular import + accoppiamento
    tight a product_types module. La logica e' pinned dal sentinel
    test_inventory_check_only_physical_digital. Se aggiungi un type
    nuovo requires_stock=True, aggiorna ENTRAMBI (questa set + sentinel).
    """
    item_type = product_doc.get("item_type")
    if item_type not in _STOCK_TRACKED_TYPES:
        return False
    stock = product_doc.get("stock_quantity")
    if stock is None:
        return False
    return True


# Pinned set — sentinel verifica coerenza con models/product_types.py
# requires_stock=True. Anti-drift se in futuro aggiungiamo nuovo type
# stockable senza update qui.
_STOCK_TRACKED_TYPES: frozenset[str] = frozenset({"physical", "digital"})


def check_cart_items_inventory(
    items: Iterable[Mapping],
    products_by_id: Mapping[str, Mapping],
) -> None:
    """Verify ogni item nel cart vs product stock_quantity.

    Args:
        items: iterable di dict-like cart items with 'product_id' +
               'quantity' fields. Tipicamente list[CartItemInput] (.dict)
               or list[CartItem] (post-snapshot).
        products_by_id: dict mappante product_id → product_doc. Caller
                        deve aver pre-fetchato i product docs (single
                        Mongo round-trip).

    Raises:
        InsufficientStockError sul PRIMO item che viola lo stock.
        Fail-fast: se piu' items violano, solo il primo viene reported.
        L'UI mostra l'error per item per item dopo retry (acceptable UX:
        customer rimuove item violation, retries, vede prossimo violation).

    Returns:
        None se tutti gli item passano (incluso skipped per untracked /
        non-stock types).
    """
    for item in items:
        product_id = item.get("product_id") if hasattr(item, "get") else getattr(item, "product_id", None)
        if not product_id:
            # Item malformato → skip (validation altrove dovrebbe gia'
            # aver rifiutato).
            continue

        quantity = item.get("quantity") if hasattr(item, "get") else getattr(item, "quantity", 0)
        if not quantity or quantity <= 0:
            # Quantity zero/negative non e' un add reale (remove marker
            # gia' filtered upstream). Skip.
            continue

        product_doc = products_by_id.get(product_id)
        if product_doc is None:
            # Product non trovato nel map fornito dal caller → skip.
            # Caller potrebbe avere filtered (e.g. product not published).
            # Caso "product missing" e' responsabilita' del caller, qui
            # solo inventory.
            continue

        if not inventory_check_required(product_doc):
            # Type non-stock OR stock_quantity=None → skip (allowed).
            continue

        available = product_doc.get("stock_quantity", 0)
        if not isinstance(available, int):
            # Difensivo: tipo non int (es. None passed through despite
            # check sopra, malformed doc). Skip → fail-open. Atomic
            # confirm-time check catchera' comunque.
            continue

        if available <= 0:
            raise InsufficientStockError(
                product_id=product_id,
                requested=quantity,
                available=0,
                message=(
                    f"Prodotto esaurito: disponibilita' attuale 0 unita'."
                ),
            )

        if quantity > available:
            raise InsufficientStockError(
                product_id=product_id,
                requested=quantity,
                available=available,
            )


__all__ = [
    "InsufficientStockError",
    "inventory_check_required",
    "check_cart_items_inventory",
]
