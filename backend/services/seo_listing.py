"""SEO2 — elenco ritiri listabili per le pagine local (categoria,
destinazione), fonte unica del gate GT1b.

Le pagine /ritiri/{categoria} e /destinazioni/{luogo} sono le pagine
"pratica × luogo" su cui si gioca il ranking locale. Servono di un
ItemList dei ritiri reali (ottimo per la SERP) e del segnale di
contenuto (se vuoto → noindex, niente thin content).

Applica ESATTAMENTE lo stesso gate del calendario pubblico (decisione
founder GT1b): solo ritiri prenotabili online adesso — transaction_mode
direct, org con superficie pubblica, pagamenti pronti. Così l'ItemList
non promette mai un ritiro che poi non esiste nella lista.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


async def listable_retreats(*, category: Optional[str] = None,
                            place: Optional[str] = None,
                            limit: int = 20) -> List[Dict[str, Any]]:
    """Ritiri futuri prenotabili online, opz. filtrati per categoria o
    luogo (city O region, case-insensitive). Ritorna item leggeri:
    {name, url, city, region, start_at, price}. Vuoto = niente contenuto."""
    from database import (event_occurrences_collection, products_collection,
                          stores_collection, organizations_collection,
                          payment_connections_collection)

    now_iso = datetime.now(timezone.utc).isoformat()[:16]
    occs = await (event_occurrences_collection.find(
        {"status": "published", "start_at": {"$gte": now_iso}},
        {"_id": 0, "product_id": 1, "slug": 1, "start_at": 1, "city": 1,
         "region": 1, "price_override": 1})
        .sort("start_at", 1).limit(500).to_list(500))
    if place:
        # match luogo su city O region normalizzando gli slug: il param
        # arriva sia come 'Puglia' (categoria×regione) sia come
        # 'greve-in-chianti' (destinazione). _place_slug allinea i due lati.
        from routers.public import _place_slug
        key = _place_slug(place)
        occs = [o for o in occs
                if _place_slug(o.get("city") or "") == key
                or _place_slug(o.get("region") or "") == key]
    if not occs:
        return []

    product_ids = list({o["product_id"] for o in occs if o.get("product_id")})
    prod_query: Dict[str, Any] = {
        "id": {"$in": product_ids}, "is_active": True, "is_published": True,
        "item_type": "event_ticket", "transaction_mode": "direct"}
    if category:
        prod_query["category"] = category
    prods = await products_collection.find(
        prod_query,
        {"_id": 0, "id": 1, "name": 1, "organization_id": 1, "unit_price": 1},
    ).to_list(1000)
    prod_by_id = {p["id"]: p for p in prods}
    org_ids = list({p["organization_id"] for p in prods})

    # gate GT1b: org con superficie pubblica + pagamenti pronti
    public_orgs: set = set()
    org_slug: Dict[str, str] = {}
    async for s in stores_collection.find(
            {"organization_id": {"$in": org_ids}, "is_published": True,
             "is_active": True, "visibility": "public"},
            {"_id": 0, "organization_id": 1, "slug": 1}):
        public_orgs.add(s["organization_id"])
        org_slug.setdefault(s["organization_id"], s["slug"])
    async for o in organizations_collection.find(
            {"id": {"$in": org_ids}, "public_slug": {"$nin": [None, ""]},
             "store_settings.is_storefront_published": True},
            {"_id": 0, "id": 1, "public_slug": 1}):
        public_orgs.add(o["id"])
        org_slug.setdefault(o["id"], o["public_slug"])
    pay_ready: set = set()
    async for pc in payment_connections_collection.find(
            {"organization_id": {"$in": org_ids},
             "status": "active", "runtime_status": "ready"},
            {"_id": 0, "organization_id": 1}):
        pay_ready.add(pc["organization_id"])

    items: List[Dict[str, Any]] = []
    for occ in occs:
        prod = prod_by_id.get(occ.get("product_id"))
        if not prod:
            continue
        oid = prod["organization_id"]
        if oid not in public_orgs or oid not in pay_ready:
            continue
        slug = org_slug.get(oid)
        if not slug:
            continue
        items.append({
            "name": prod["name"],
            "url": f"/e/{slug}/{occ['slug']}",
            "city": occ.get("city"),
            "region": occ.get("region"),
            "start_at": occ.get("start_at"),
            "price": occ.get("price_override")
            if occ.get("price_override") is not None else prod.get("unit_price"),
        })
        if len(items) >= limit:
            break
    return items
