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
    # PL9 — i campioni di pre-lancio non entrano MAI in sitemap:
    # le loro pagine rispondono 404 e non vanno offerte ai crawler.
    stores = await stores_collection.find(
        {"is_published": True, "is_active": True, "visibility": "public",
         "slug": {"$nin": [None, ""]}, "is_sample": {"$ne": True}},
        {"_id": 0, "organization_id": 1, "slug": 1},
    ).to_list(1000)
    for s in stores:
        slug_by_org.setdefault(s["organization_id"], s["slug"])
    async for org in organizations_collection.find(
            {"public_slug": {"$nin": [None, ""]},
             "is_sample": {"$ne": True}},
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
    from core.prelaunch import site_phase
    base = _base_url()
    urls = [
        _url(f"{base}/", priority="1.0"),
        _url(f"{base}/manifesto", priority="0.8"),
        # SW3 — /chi-siamo e' una pagina propria (le persone dietro
        # Aurya): torna in sitemap, un gradino sotto il Manifesto, che
        # resta la pagina di posizione.
        _url(f"{base}/chi-siamo", priority="0.6"),
        _url(f"{base}/entra-nella-rete", priority="0.7"),
        _url(f"{base}/newsletter", priority="0.7"),
        # SP5 — Aurya Sound pubblico: solo le pagine editoriali
        # (crea/tracce sono workspace: noindex e fuori di qui)
        # ES2 (25/8) — pagine pubbliche vere che non erano dichiarate:
        # /meditazioni e' persino nel menu, /costi risponde alla domanda
        # che ogni professionista fa per prima
        _url(f"{base}/meditazioni", priority="0.7"),
        _url(f"{base}/costi", priority="0.6"),
        _url(f"{base}/sound", priority="0.7"),
        _url(f"{base}/sound/esplora", priority="0.6"),
        _url(f"{base}/sound/impara", priority="0.6"),
        _url(f"{base}/sound/impara/glossario", priority="0.4"),
        _url(f"{base}/sound/calm", priority="0.7"),
        _url(f"{base}/sound/lab", priority="0.5"),
        # GS5 (25/8) — privacy/termini NON stanno piu' qui: sono rotte
        # di servizio (noindex nella shell) e dichiararle in sitemap
        # mentre si chiede il noindex e' un segnale in conflitto. In
        # Search Console erano tra le POCHE pagine indicizzate, con lo
        # snippet generico del sito — sporcizia al posto degli articoli.
    ]

    # RT5 — fase rete: il marketplace è spento, la sitemap dice la
    # verità: home, manifesto, rete, newsletter. Gli hub commerciali
    # (/ritiri, /destinazioni) rientrano al flip in fase marketplace;
    # /operatori è la landing della rete e resta (indicizzabile).
    if site_phase() == "network":
        urls.append(_url(f"{base}/operatori", priority="0.8"))
        # ES (25/8) — le due directory della fase rete entrano in
        # sitemap SOLO quando hanno contenuto: una pagina dichiarata ai
        # crawler e poi trovata vuota e' una promessa mancata, e la
        # sitemap e' il posto dove le promesse si contano. Si accendono
        # da sole — nessuna azione il giorno del primo ritiro.
        # LEZIONE SEO2, ripetuta: questo ramo prima NON toccava il DB
        # (i test unit girano senza loop motor) e i due conteggi lo
        # cambiano. Avvolti: una sitemap che esplode e' peggio di una
        # sitemap senza le due directory.
        try:
            from database import organizations_collection
            if await organizations_collection.count_documents(
                    {"is_sample": {"$ne": True}, "is_active": {"$ne": False},
                     "exclude_from_listings": {"$ne": True},
                     "public_slug": {"$nin": [None, ""]}}):
                urls.append(_url(f"{base}/esplora-operatori", priority="0.9"))
            from services.seo_listing import listable_retreats
            if await listable_retreats():
                urls.append(_url(f"{base}/esplora-ritiri", priority="0.9"))
            # RS (26/8) — LE MEDITAZIONI PUBBLICATE. Sono il link che
            # l'operatore condivide coi suoi clienti, e non stavano in
            # nessuna sitemap: trovate insieme alla loro pagina muta,
            # censendo il registro delle rotte.
            from database import frequency_tracks_collection
            async for t in frequency_tracks_collection.find(
                    {"status": "published", "slug": {"$nin": [None, ""]}},
                    {"_id": 0, "slug": 1, "updated_at": 1}).limit(500):
                urls.append(_url(f"{base}/frequenze/{t['slug']}",
                                 priority="0.6", lastmod=t.get("updated_at")))
        except Exception:   # noqa: BLE001 — mai una sitemap rotta
            pass
        return _wrap(urls, "core")

    urls.append(_url(f"{base}/come-funziona", priority="0.6"))

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
        # stessa regola dell'indice destinazioni: una per occorrenza
        name = o.get("city") or o.get("region")
        if name:
            places.add(_place_slug(name))

    for cat, reg in sorted(cat_reg, key=lambda x: (x[0], x[1] or "")):
        path = f"/ritiri/{cat}" + (f"/{reg}" if reg else "")
        urls.append(_url(f"{base}{path}", priority="0.7"))

    if slug_by_org:
        urls.append(_url(f"{base}/operatori", priority="0.8"))
        for cat in sorted(op_cats):
            urls.append(_url(f"{base}/operatori/{cat}", priority="0.6"))
        # DS3: /esperienze fuori dal sitemap finché il founder non la riapre
    if places:
        urls.append(_url(f"{base}/destinazioni", priority="0.8"))
        for pl in sorted(places):
            urls.append(_url(f"{base}/destinazioni/{pl}", priority="0.7"))

    return _wrap(urls, "core")


async def build_retreats() -> str:
    from database import products_collection
    from core.prelaunch import site_phase
    # LC1→PN0 — fase rete: le landing /e/ restano VIVE (rispondono 200:
    # il profilo-negozio le linka e chi riceve il link puo' comprare),
    # ma non le pubblicizziamo ai crawler: la sitemap resta vuota fino
    # al flip in marketplace. La scoperta passa solo dai profili membri.
    if site_phase() == "network":
        return _wrap([], "retreats")
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
    from core.prelaunch import site_phase
    if site_phase() == "network":          # LC1 — come build_retreats
        return _wrap([], "products")
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
    from database import organizations_collection
    from core.prelaunch import site_phase
    # LC1→PN0→PP2b (ok founder 4/8) — fase rete: la promessa fatta agli
    # intervistati e' un profilo pubblico INDICIZZATO, quindi la
    # sitemap elenca gia' ora i SOLI membri della rete, e il solo
    # profilo /o/ (niente /s/: lo store non esiste nel mondo snello).
    # Al flip in marketplace torna l'elenco pieno qui sotto.
    if site_phase() == "network":
        base = _base_url()
        slug_by_org = await _public_org_slugs()
        members: dict = {}
        # ES (25/8) — il criterio non e' piu' SOLO `network_member`.
        # Quel flag dice «intervistato e accolto» ed e' una decisione
        # editoriale del founder; la sitemap invece ha un compito
        # diverso e meccanico: dichiarare le pagine INDICIZZABILI E
        # LINKATE. Da quando /esplora-operatori e' aperta ed elenca i
        # professionisti registrati, i loro profili sono esattamente
        # questo — e restavano fuori da ogni sitemap perche' nessuno
        # aveva ancora alzato un flag. Una pagina che il sito linka e
        # non dichiara e' una pagina che chiediamo a Google di trovare
        # da solo.
        async for o in organizations_collection.find(
                {"is_active": {"$ne": False}, "is_sample": {"$ne": True},
                 "exclude_from_listings": {"$ne": True},
                 "$or": [{"network_member": True},
                         {"public_slug": {"$nin": [None, ""]}}]},
                {"_id": 0, "id": 1, "updated_at": 1}):
            slug = slug_by_org.get(o["id"])
            if slug:
                members[slug] = o.get("updated_at")
        urls = [_url(f"{base}/o/{slug}", priority="0.6",
                     lastmod=members[slug])
                for slug in sorted(members)]
        return _wrap(urls, "operators")
    base = _base_url()
    slug_by_org = await _public_org_slugs()
    # SEO2 — lastmod onesto per operatore: quando il profilo/store cambia
    # il crawler sa che vale la pena ripassare (l'update già pinga IndexNow).
    lastmod_by_slug: dict = {}
    async for o in organizations_collection.find(
            {"id": {"$in": list(slug_by_org)}},
            {"_id": 0, "id": 1, "updated_at": 1}):
        slug = slug_by_org.get(o["id"])
        if slug and o.get("updated_at"):
            lastmod_by_slug[slug] = o["updated_at"]
    urls = []
    for org_slug in sorted(set(slug_by_org.values())):
        lm = lastmod_by_slug.get(org_slug)
        urls.append(_url(f"{base}/o/{org_slug}", priority="0.6", lastmod=lm))
        urls.append(_url(f"{base}/s/{org_slug}", priority="0.5", lastmod=lm))
        urls.append(_url(f"{base}/s/{org_slug}/chi-siamo", priority="0.4",
                         lastmod=lm))
    return _wrap(urls, "operators")


async def build_articles() -> str:
    """AN6 — il blog nel sitemap: hub /blog + articoli pubblicati,
    hreflang solo sulle lingue con traduzione vera (title+content)."""
    from database import db
    base = _base_url()
    # GS4 (25/8) — in fase rete l'hub dichiara solo l'italiano: gli
    # alternates ?lang= servivano contenuto italiano con UI tradotta,
    # e Google gia' classificava male la lingua del sito. Gli articoli
    # con traduzione VERA (title+content) tengono i loro, sotto.
    from core.prelaunch import site_phase
    _hub_alt = {"it": f"{base}/blog", "x-default": f"{base}/blog"}
    if site_phase() != "network":
        _hub_alt.update({l: f"{base}/blog?lang={l}" for l in _LANGS})
    urls = [_url(f"{base}/blog", priority="0.6", hreflang=_hub_alt)]
    # BN5 — hub categoria del Magazine: in sitemap solo quelli con
    # almeno un articolo (pagina in sitemap ⟺ contenuto reale)
    cats = await db.articles.distinct("category", {"published": True})
    for cat in sorted(c for c in cats if c):
        urls.append(_url(f"{base}/blog/categoria/{cat}", priority="0.5"))
    docs = await (db.articles
                  .find({"published": True},
                        {"_id": 0, "slug": 1, "published_at": 1,
                         "updated_at": 1, "translations": 1})
                  .sort("published_at", -1).limit(5000).to_list(5000))
    for d in docs:
        canonical = f"{base}/blog/{d['slug']}"
        hl = {"it": canonical, "x-default": canonical}
        for lang, tr in (d.get("translations") or {}).items():
            if lang in _LANGS and (tr or {}).get("title") \
                    and (tr or {}).get("content"):
                hl[lang] = f"{canonical}?lang={lang}"
        urls.append(_url(canonical,
                         lastmod=d.get("updated_at") or d.get("published_at"),
                         priority="0.6",
                         hreflang=hl if len(hl) > 2 else None))
    return _wrap(urls, "articles")


def build_index() -> str:
    from core.prelaunch import site_phase
    base = _base_url()
    now = datetime.now(timezone.utc).isoformat()[:10]
    # LC1→PP2b — l'indice elenca solo sotto-sitemap con contenuto
    # possibile: in fase rete retreats/products sono vuote per
    # costruzione, ma operators elenca i membri della rete (ok founder
    # 4/8) e quindi si dichiara.
    names = (("core", "operators", "articles")
             if site_phase() == "network"
             else ("core", "retreats", "products", "operators", "articles"))
    entries = "".join(
        f"<sitemap><loc>{escape(base)}/api/public/sitemap-{name}.xml</loc>"
        f"<lastmod>{now}</lastmod></sitemap>"
        for name in names
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


@router.get("/sitemap-articles.xml")
async def sitemap_articles():
    return await _cached("articles", build_articles)
