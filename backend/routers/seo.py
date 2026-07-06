"""SEO router — sitemap.xml dinamica (F3, 5/7/2026).

docs/DIRECTORY_DESIGN_PLAN.md §F3. "Automatico" = derivata dai dati:
directory, pagine categoria×regione con contenuto, landing pubblicate
e future, profili operatore, store pubblicati. Cache in-memory 1h.

In produzione nginx instrada GET /sitemap.xml → questo endpoint
(/api/public/sitemap.xml). robots.txt è statico in frontend/public.
"""

import os
import time
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fastapi import APIRouter, Response

router = APIRouter(prefix="/public", tags=["SEO"])

_CACHE: dict = {"xml": None, "at": 0.0}
_CACHE_TTL_SECONDS = 3600


def _base_url() -> str:
    return os.environ.get("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")


def _url(loc: str, lastmod=None, priority: str = "0.6") -> str:
    parts = [f"<loc>{escape(loc)}</loc>"]
    if lastmod:
        # updated_at puo' essere datetime (Mongo) o stringa ISO
        if isinstance(lastmod, datetime):
            lastmod = lastmod.isoformat()
        parts.append(f"<lastmod>{escape(str(lastmod)[:10])}</lastmod>")
    parts.append(f"<priority>{priority}</priority>")
    return "<url>" + "".join(parts) + "</url>"


async def build_sitemap() -> str:
    from database import (
        event_occurrences_collection,
        products_collection,
        stores_collection,
    )

    base = _base_url()
    now_iso = datetime.now(timezone.utc).isoformat()[:16]
    # S0.1 — la home È la directory (priorità massima); /ritiri è un
    # redirect e NON va in sitemap. Le pagine categoria restano su /ritiri/*.
    urls = [_url(f"{base}/", priority="1.0")]

    # Landing pubblicate e future + coppie categoria×regione REALI
    # (solo combinazioni con contenuto: pagine indice vuote = thin content)
    occs = await event_occurrences_collection.find(
        {"status": "published", "start_at": {"$gte": now_iso},
         "slug": {"$nin": [None, ""]}},
        {"_id": 0, "product_id": 1, "slug": 1, "region": 1, "updated_at": 1},
    ).to_list(2000)

    prod_ids = list({o["product_id"] for o in occs})
    prods = {p["id"]: p for p in await products_collection.find(
        {"id": {"$in": prod_ids}, "is_active": True, "is_published": True},
        {"_id": 0, "id": 1, "category": 1, "organization_id": 1},
    ).to_list(2000)}

    # store pubblicati → slug per landing/profili + pagine store
    org_ids = list({p["organization_id"] for p in prods.values()})
    stores = await stores_collection.find(
        {"organization_id": {"$in": org_ids}, "is_published": True,
         "slug": {"$nin": [None, ""]}},
        {"_id": 0, "organization_id": 1, "slug": 1},
    ).to_list(1000)
    slug_by_org = {}
    for s in stores:
        slug_by_org.setdefault(s["organization_id"], s["slug"])

    # Fallback mono-store: org senza store pubblicato ma con public_slug
    # (stesso doppio percorso del landing resolver — /e/:slug funziona
    # anche cosi', quindi la sitemap DEVE coprirlo)
    from database import organizations_collection
    missing = [oid for oid in org_ids if oid not in slug_by_org]
    if missing:
        async for org in organizations_collection.find(
                {"id": {"$in": missing},
                 "public_slug": {"$nin": [None, ""]}},
                {"_id": 0, "id": 1, "public_slug": 1}):
            slug_by_org[org["id"]] = org["public_slug"]

    cat_reg_pairs = set()
    for o in occs:
        p = prods.get(o["product_id"])
        if not p:
            continue
        org_slug = slug_by_org.get(p["organization_id"])
        if not org_slug:
            continue
        urls.append(_url(f"{base}/e/{org_slug}/{o['slug']}",
                         lastmod=o.get("updated_at"), priority="0.8"))
        if p.get("category") and o.get("region"):
            cat_reg_pairs.add((p["category"], o["region"]))
        if p.get("category"):
            cat_reg_pairs.add((p["category"], None))

    for cat, reg in sorted(cat_reg_pairs, key=lambda x: (x[0], x[1] or "")):
        path = f"/ritiri/{cat}" + (f"/{reg}" if reg else "")
        urls.append(_url(f"{base}{path}", priority="0.7"))

    for org_slug in sorted(set(slug_by_org.values())):
        urls.append(_url(f"{base}/o/{org_slug}", priority="0.6"))
        urls.append(_url(f"{base}/s/{org_slug}", priority="0.5"))

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls) + "</urlset>"
    )


@router.get("/sitemap.xml")
async def sitemap():
    now = time.monotonic()
    if _CACHE["xml"] and now - _CACHE["at"] < _CACHE_TTL_SECONDS:
        xml = _CACHE["xml"]
    else:
        xml = await build_sitemap()
        _CACHE["xml"] = xml
        _CACHE["at"] = now
    return Response(content=xml, media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=3600"})
