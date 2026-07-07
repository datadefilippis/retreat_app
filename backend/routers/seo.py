"""SEO router — sitemap INDEX + sotto-sitemap (S3, SEO_MASTER_PLAN).

Evoluzione della sitemap monolitica di F3. Struttura:

  /api/public/sitemap.xml            → sitemap INDEX (punta alle 4 sotto)
  /api/public/sitemap-core.xml       → home, hub (operatori/destinazioni/
                                       esperienze), categoria×regione, legali
  /api/public/sitemap-retreats.xml   → landing eventi /e/ (con hreflang)
  /api/public/sitemap-products.xml   → TUTTE le landing prodotto pubblicate
                                       /p /ph /dg /co /r (con hreflang)
  /api/public/sitemap-operators.xml  → profili /o/, store /s/, chi-siamo

"Automatico" = derivato dai dati: pagina in sitemap ⟺ contenuto reale
(anti thin-content). hreflang via xhtml:link SOLO per le lingue con la
description tradotta (il gate del multilingua manuale) + x-default.

Scala: ogni sotto-sitemap logga un warning oltre 45k url (limite
protocollo 50k) — il chunking numerato si aggiunge lì quando servirà.
Cache in-memory 1h per file. In produzione il proxy instrada
GET /sitemap*.xml → questi endpoint.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["SEO"])

_CACHE: dict = {}
_CACHE_TTL_SECONDS = 3600

_XMLNS = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:xhtml="http://www.w3.org/1999/xhtml">')

_LANGS = ("en", "de", "fr")


def _base_url() -> str:
    return os.environ.get("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")


def _url(loc: str, lastmod=None, priority: str = "0.6",
         hreflang: Optional[dict] = None) -> str:
    parts = [f"<loc>{escape(loc)}</loc>"]
    for lang, href in (hreflang or {}).items():
        parts.append(f'<xhtml:link rel="alternate" hreflang="{lang}" '
                     f'href="{escape(href)}"/>')
    if lastmod:
        if isinstance(lastmod, datetime):
            lastmod = lastmod.isoformat()
        parts.append(f"<lastmod>{escape(str(lastmod)[:10])}</lastmod>")
    parts.append(f"<priority>{priority}</priority>")
    return "<url>" + "".join(parts) + "</url>"


def _hreflang(translations: Optional[dict], canonical: str) -> Optional[dict]:
    """Alternates SOLO se esiste almeno una traduzione vera (description)."""
    out = {"it": canonical, "x-default": canonical}
    for lang, tr in (translations or {}).items():
        if lang in _LANGS and (tr or {}).get("description"):
            out[lang] = f"{canonical}?lang={lang}"
    return out if len(out) > 2 else None


def _wrap(urls: list, name: str) -> str:
    if len(urls) > 45000:
        logger.warning("sitemap %s oltre 45k url (%d): serve il chunking "
                       "numerato (S3, SEO_MASTER_PLAN)", name, len(urls))
    return ('<?xml version="1.0" encoding="UTF-8"?>' + _XMLNS
            + "".join(urls) + "</urlset>")


async def _public_org_slugs() -> dict:
    """org_id → slug pubblico (store pubblicato; fallback public_slug)."""
    from database import stores_collection, organizations_collection
    slug_by_org: dict = {}
    stores = await stores_collection.find(
        {"is_published": True, "is_active": True, "visibility": "public",
         "slug": {"$nin": [None, ""]}},
        {"_id": 0, "organization_id": 1, "slug": 1},
    ).to_list(1000)
    for s in stores:
        slug_by_org.setdefault(s["organization_id"], s["slug"])
    async for org in organizations_collection.find(
            {"public_slug": {"$nin": [None, ""]}},
            {"_id": 0, "id": 1, "public_slug": 1}):
        slug_by_org.setdefault(org["id"], org["public_slug"])
    return slug_by_org


async def _future_occurrences():
    from database import event_occurrences_collection
    now_iso = datetime.now(timezone.utc).isoformat()[:16]
    return await event_occurrences_collection.find(
        {"status": "published", "start_at": {"$gte": now_iso},
         "slug": {"$nin": [None, ""]}},
        {"_id": 0, "product_id": 1, "slug": 1, "region": 1, "city": 1,
         "updated_at": 1},
    ).to_list(5000)


# ── Builders ─────────────────────────────────────────────────────────────────

async def build_core() -> str:
    from database import products_collection
    base = _base_url()
    urls = [
        _url(f"{base}/", priority="1.0"),
        # AN1 — pagine istituzionali del brand
        _url(f"{base}/chi-siamo", priority="0.6"),
        _url(f"{base}/come-funziona", priority="0.6"),
        _url(f"{base}/privacy", priority="0.3"),
        _url(f"{base}/termini", priority="0.3"),
    ]

    slug_by_org = await _public_org_slugs()
    occs = await _future_occurrences()
    prods = {p["id"]: p for p in await products_collection.find(
        {"id": {"$in": list({o["product_id"] for o in occs})},
         "is_active": True, "is_published": True},
        {"_id": 0, "id": 1, "category": 1, "organization_id": 1},
    ).to_list(5000)}

    from routers.public import _place_slug
    cat_reg = set()
    places = set()
    op_cats = set()
    for o in occs:
        p = prods.get(o["product_id"])
        if not p or not slug_by_org.get(p["organization_id"]):
            continue
        if p.get("category"):
            op_cats.add(p["category"])
            cat_reg.add((p["category"], None))
            if o.get("region"):
                cat_reg.add((p["category"], o["region"]))
        for name in {o.get("region"), o.get("city")}:
            if name:
                places.add(_place_slug(name))

    for cat, reg in sorted(cat_reg, key=lambda x: (x[0], x[1] or "")):
        path = f"/ritiri/{cat}" + (f"/{reg}" if reg else "")
        urls.append(_url(f"{base}{path}", priority="0.7"))

    if slug_by_org:
        urls.append(_url(f"{base}/operatori", priority="0.8"))
        for cat in sorted(op_cats):
            urls.append(_url(f"{base}/operatori/{cat}", priority="0.6"))
        urls.append(_url(f"{base}/esperienze", priority="0.7"))
    if places:
        urls.append(_url(f"{base}/destinazioni", priority="0.8"))
        for pl in sorted(places):
            urls.append(_url(f"{base}/destinazioni/{pl}", priority="0.7"))

    return _wrap(urls, "core")


async def build_retreats() -> str:
    from database import products_collection
    base = _base_url()
    slug_by_org = await _public_org_slugs()
    occs = await _future_occurrences()
    prods = {p["id"]: p for p in await products_collection.find(
        {"id": {"$in": list({o["product_id"] for o in occs})},
         "is_active": True, "is_published": True},
        {"_id": 0, "id": 1, "organization_id": 1, "translations": 1},
    ).to_list(5000)}

    urls = []
    for o in occs:
        p = prods.get(o["product_id"])
        if not p:
            continue
        org_slug = slug_by_org.get(p["organization_id"])
        if not org_slug:
            continue
        loc = f"{base}/e/{org_slug}/{o['slug']}"
        urls.append(_url(loc, lastmod=o.get("updated_at"), priority="0.8",
                         hreflang=_hreflang(p.get("translations"), loc)))
    return _wrap(urls, "retreats")


_PRODUCT_PREFIX = {"service": "p", "physical": "ph", "digital": "dg",
                   "course": "co", "rental": "r"}


async def build_products() -> str:
    """S3 — TUTTE le landing prodotto non-evento pubblicate (prima
    erano invisibili anche alla sitemap)."""
    from database import products_collection
    base = _base_url()
    slug_by_org = await _public_org_slugs()

    urls = []
    prods = await products_collection.find(
        {"organization_id": {"$in": list(slug_by_org)},
         "is_active": True, "is_published": True,
         "item_type": {"$in": list(_PRODUCT_PREFIX)},
         "slug": {"$nin": [None, ""]}},
        {"_id": 0, "slug": 1, "item_type": 1, "organization_id": 1,
         "updated_at": 1, "translations": 1},
    ).to_list(20000)
    for p in prods:
        org_slug = slug_by_org.get(p["organization_id"])
        prefix = _PRODUCT_PREFIX.get(p["item_type"])
        if not org_slug or not prefix:
            continue
        loc = f"{base}/{prefix}/{org_slug}/{p['slug']}"
        urls.append(_url(loc, lastmod=p.get("updated_at"), priority="0.6",
                         hreflang=_hreflang(p.get("translations"), loc)))
    return _wrap(urls, "products")


async def build_operators() -> str:
    base = _base_url()
    slug_by_org = await _public_org_slugs()
    urls = []
    for org_slug in sorted(set(slug_by_org.values())):
        urls.append(_url(f"{base}/o/{org_slug}", priority="0.6"))
        urls.append(_url(f"{base}/s/{org_slug}", priority="0.5"))
        urls.append(_url(f"{base}/s/{org_slug}/chi-siamo", priority="0.4"))
    return _wrap(urls, "operators")


def build_index() -> str:
    base = _base_url()
    now = datetime.now(timezone.utc).isoformat()[:10]
    entries = "".join(
        f"<sitemap><loc>{escape(base)}/api/public/sitemap-{name}.xml</loc>"
        f"<lastmod>{now}</lastmod></sitemap>"
        for name in ("core", "retreats", "products", "operators")
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + entries + "</sitemapindex>")


# ── Endpoints ────────────────────────────────────────────────────────────────

async def _cached(name: str, builder) -> Response:
    now = time.monotonic()
    hit = _CACHE.get(name)
    if hit and now - hit[1] < _CACHE_TTL_SECONDS:
        xml = hit[0]
    else:
        xml = await builder()
        _CACHE[name] = (xml, now)
    return Response(content=xml, media_type="application/xml")


@router.get("/sitemap.xml")
async def sitemap_index():
    return Response(content=build_index(), media_type="application/xml")


@router.get("/sitemap-core.xml")
async def sitemap_core():
    return await _cached("core", build_core)


@router.get("/sitemap-retreats.xml")
async def sitemap_retreats():
    return await _cached("retreats", build_retreats)


@router.get("/sitemap-products.xml")
async def sitemap_products():
    return await _cached("products", build_products)


@router.get("/sitemap-operators.xml")
async def sitemap_operators():
    return await _cached("operators", build_operators)
