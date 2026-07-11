"""SEO shell — HTML pubblico con meta server-side (S0.2, SEO_MASTER_PLAN).

PROBLEMA: la SPA (CRA) inietta title/meta/OG/JSON-LD via JavaScript.
Google renderizza, ma Bing e gli scraper social (WhatsApp, Instagram,
LinkedIn, iMessage) leggono SOLO l'HTML iniziale: ogni condivisione di
un ritiro usciva senza titolo né anteprima.

SOLUZIONE: il reverse proxy instrada le route PUBBLICHE qui; questo
router serve l'index.html della build con title/meta/OG/canonical/
JSON-LD già iniettati per QUELLA route, calcolati dagli stessi dati
delle API pubbliche. Il JS poi idrata come sempre (useSeoMeta resta il
driver della navigazione SPA). Stesso HTML per bot e umani: nessun
cloaking.

Config:
  SEO_SHELL_INDEX_PATH  sorgente dell'index.html della build:
                        - path su disco (default dev: ../frontend/build/
                          index.html) → riletto quando cambia (mtime);
                        - URL http(s):// (deploy Docker split-container:
                          il backend legge l'index dal container frontend,
                          es. http://frontend/index.html) → cache TTL.
  PUBLIC_APP_URL        base URL assoluta per canonical/OG

Proxy (Caddy) — vedi docs/DEPLOY_CHECKLIST.md:
  route pubbliche (/, /ritiri*, /e/*, /p/*, /ph/*, /dg/*, /co/*, /r/*,
  /o/*, /s/*) → backend /__seo/<path>; il resto degli asset → build.

Cache: per-URL, TTL 10 minuti (i contenuti cambiano al ritmo dei
publish, non dei click).
"""

import html as _html
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Response

from core.prelaunch import prelaunch_mode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/__seo", tags=["SEO shell"])

_CACHE: dict = {}          # path → (html, monotonic_ts)
_CACHE_TTL = 600
_INDEX_CACHE: dict = {"html": None, "mtime": None}
# Deploy Docker: l'index vive nel container frontend, letto via HTTP e
# ricontrollato ogni _INDEX_HTTP_TTL secondi (un redeploy riavvia il
# backend e svuota comunque la cache).
_INDEX_HTTP_TTL = 300

# Template minimo per dev/test quando la build non esiste: la shell è
# testabile senza `pnpm build`.
_DEV_TEMPLATE = (
    "<!DOCTYPE html><html lang=\"it\"><head><meta charset=\"utf-8\">"
    "<title>Aurya</title>"
    "<meta name=\"description\" content=\"Aurya\">"
    "</head><body><div id=\"root\"></div></body></html>"
)


def _base_url() -> str:
    return os.environ.get("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")


def _index_html() -> str:
    src = os.environ.get(
        "SEO_SHELL_INDEX_PATH",
        str(Path(__file__).resolve().parent.parent.parent
            / "frontend" / "build" / "index.html"),
    )
    if src.startswith("http://") or src.startswith("https://"):
        return _index_html_http(src)
    path = Path(src)
    try:
        mtime = path.stat().st_mtime
        if _INDEX_CACHE["html"] is None or _INDEX_CACHE["mtime"] != mtime:
            _INDEX_CACHE["html"] = path.read_text(encoding="utf-8")
            _INDEX_CACHE["mtime"] = mtime
        return _INDEX_CACHE["html"]
    except OSError:
        return _DEV_TEMPLATE


def _index_html_http(url: str) -> str:
    """Deploy Docker: legge l'index dal container frontend via HTTP con
    cache TTL. Best-effort assoluto: se il frontend non risponde si serve
    la shell neutra (la SPA idrata comunque quando l'asset torna su)."""
    import urllib.request
    now = time.monotonic()
    cached_at = _INDEX_CACHE["mtime"]
    if (_INDEX_CACHE["html"] is not None and cached_at is not None
            and (now - cached_at) < _INDEX_HTTP_TTL):
        return _INDEX_CACHE["html"]
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            _INDEX_CACHE["html"] = resp.read().decode("utf-8")
            _INDEX_CACHE["mtime"] = now
        return _INDEX_CACHE["html"]
    except Exception as exc:                # noqa: BLE001 — mai 500 sulla shell
        logger.warning("seo_shell: index fetch da %s fallito: %s", url, exc)
        return _INDEX_CACHE["html"] or _DEV_TEMPLATE


def _inject(template: str, meta: dict) -> str:
    """Sostituisce title/description e appende OG/canonical/JSON-LD."""
    title = _html.escape(meta.get("title") or "Aurya")
    desc = _html.escape(meta.get("description") or "")

    out = re.sub(r"<title>.*?</title>", f"<title>{title}</title>",
                 template, count=1, flags=re.S)
    # PL21b — via i meta og:/twitter: STATICI di index.html prima di
    # iniettare i nostri: due og:image = i crawler prendono il primo
    # (quello generico) e l'immagine per-pagina non appare mai.
    out = re.sub(r'<meta\s+(?:property="og:[^"]*"|name="twitter:[^"]*")[^>]*/?>\s*', "", out)
    out = re.sub(r'<meta name="description"[^>]*/?>',
                 f'<meta name="description" content="{desc}"/>',
                 out, count=1)

    extra = [
        f'<meta property="og:title" content="{title}"/>',
        f'<meta property="og:description" content="{desc}"/>',
        '<meta property="og:type" content="website"/>',
        '<meta property="og:site_name" content="Aurya"/>',
        '<meta name="twitter:card" content="summary_large_image"/>',
    ]
    if meta.get("image"):
        extra.append(f'<meta property="og:image" content="{_html.escape(meta["image"])}"/>')
        extra.append(f'<meta name="twitter:image" content="{_html.escape(meta["image"])}"/>')
    if meta.get("canonical"):
        canonical = _html.escape(meta["canonical"])
        extra.append(f'<link rel="canonical" href="{canonical}"/>')
        extra.append(f'<meta property="og:url" content="{canonical}"/>')
    for lang, href in (meta.get("hreflang") or {}).items():
        extra.append(f'<link rel="alternate" hreflang="{lang}" href="{_html.escape(href)}"/>')
    if meta.get("noindex"):
        extra.append('<meta name="robots" content="noindex"/>')
    # jsonld può essere un dict singolo o una LISTA di blocchi (es. entità
    # principale + BreadcrumbList + ItemList): uno <script> per blocco,
    # come raccomanda Google.
    blocks = meta.get("jsonld")
    if blocks:
        if not isinstance(blocks, list):
            blocks = [blocks]
        for block in blocks:
            if block:
                extra.append('<script type="application/ld+json">'
                             + json.dumps(block, ensure_ascii=False)
                             + "</script>")

    return out.replace("</head>", "".join(extra) + "</head>", 1)


def _abs_image(url: Optional[str]) -> str:
    """Cover assoluta con fallback SEMPRE presente (og-cover 1200x630:
    il logo quadrato rende male nelle card social large)."""
    base = _base_url()
    if not url:
        return f"{base}/og-cover.jpg"
    if url.startswith("http"):
        return url
    return f"{base}{url}"


# ── Resolver per tipo di route ───────────────────────────────────────────────

def _hub_hreflang(canonical: str) -> dict:
    """Hub UI-translated in tutte e 4 le lingue (i18n files completi):
    alternates piene, x-default italiano."""
    out = {"it": canonical, "x-default": canonical}
    for lang in ("en", "de", "fr"):
        out[lang] = f"{canonical}?lang={lang}"
    return out


async def _meta_home() -> dict:
    base = _base_url()
    return {
        # AN1 — il title porta la promessa, non solo la categoria
        # (docs/BRAND_AURYA.md): caparra protetta + recensioni verificate.
        "title": "Aurya | Ritiri olistici ed esperienze per evolvere",
        "description": ("Trova e prenota ritiri di yoga, meditazione, detox "
                        "ed esperienze olistiche: prenoti online con caparra "
                        "protetta e recensioni solo verificate."),
        "canonical": f"{base}/",
        "hreflang": _hub_hreflang(f"{base}/"),
        "image": f"{base}/media/aurya-hero-poster.jpg",
        "jsonld": {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Aurya",
            "url": f"{base}/",
        },
    }


# AN1 — pagine istituzionali del brand: meta statiche, hreflang hub
_BRAND_PAGES = {
    # PL21 — le landing lead del pre-lancio: sono I link condivisi ora,
    # devono avere titolo/descrizione/immagine social impeccabili.
    "cerca-ritiro": {
        "title": "Trova il tuo ritiro olistico | Aurya",
        "description": ("C'è un ritiro che ti sta aspettando. Raccontaci "
                        "cosa cerchi e al lancio ricevi una selezione di "
                        "ritiri olistici scelti per te, con caparra e "
                        "pagamento diretto online."),
        "image": "/media/hero-destination.webp",
    },
    "per-operatori": {
        "title": "Porta i tuoi ritiri su Aurya | Per operatori olistici",
        "description": ("Tu crei l'esperienza, noi la facciamo trovare. "
                        "Visibilità vera, prenotazioni con caparra e "
                        "pagamento diretto. I primi operatori partono "
                        "da fondatori."),
        "image": "/media/hero-organizer.webp",
    },
    "chi-siamo": {
        "title": "Chi siamo | Aurya, la casa dei ritiri olistici",
        "description": ("Aurya connette chi cerca benessere autentico con chi "
                        "lo crea: ritiri prenotabili online con caparra "
                        "protetta e recensioni solo verificate."),
    },
    "come-funziona": {
        "title": "Come funziona Aurya: prenota ritiri olistici con caparra e pagamento diretto",
        "description": ("Scegli il ritiro, blocca il posto con una piccola "
                        "caparra e il pagamento diretto online, vivi "
                        "l'esperienza e recensisci: su Aurya solo recensioni "
                        "verificate."),
    },
}


async def _meta_brand_page(slug: str) -> Optional[dict]:
    page = _BRAND_PAGES.get(slug)
    if not page:
        return None
    base = _base_url()
    canonical = f"{base}/{slug}"
    return {
        **page,
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        # immagine per-pagina se dichiarata (landing lead), altrimenti og-cover
        "image": (f"{base}{page['image']}" if page.get("image")
                  else f"{base}/og-cover.jpg"),
    }


async def _meta_category(cat: str, region: Optional[str] = None) -> dict:
    from services import seo_schema as sx, seo_listing as sl
    base = _base_url()
    label = cat.replace("-", " ").title()
    where = f" in {region.title()}" if region else ""
    path = f"/ritiri/{cat}" + (f"/{region}" if region else "")
    canonical = f"{base}{path}"
    try:
        retreats = await sl.listable_retreats(category=cat, place=region, limit=20)
        empty = not retreats
    except Exception:            # noqa: BLE001 — fail open: un errore DB NON
        retreats, empty = [], False   # deve deindicizzare una pagina buona
    crumbs = sx.breadcrumb([
        ("Aurya", f"{base}/"),
        (f"Ritiri di {label}", f"{base}/ritiri/{cat}"),
        *([(region.title(), canonical)] if region else []),
    ])
    blocks = [b for b in (crumbs, sx.item_list(retreats, base)) if b]
    return {
        "title": f"Ritiri di {label}{where} | Aurya",
        "description": (f"I migliori ritiri di {label.lower()}{where}: "
                        "date, prezzi e posti disponibili. Prenota online "
                        "con la caparra su Aurya."),
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        "image": f"{base}/og-cover.jpg",
        "jsonld": blocks or None,
        # anti thin-content: categoria senza ritiri prenotabili → noindex
        "noindex": empty,
    }


async def _meta_event(org_slug: str, occ_slug: str) -> Optional[dict]:
    from database import (event_occurrences_collection, products_collection,
                          organizations_collection)
    from services import seo_schema as sx
    base = _base_url()
    occ = await event_occurrences_collection.find_one(
        {"slug": occ_slug, "status": "published"},
        {"_id": 0, "product_id": 1, "start_at": 1, "end_at": 1, "city": 1,
         "region": 1, "country": 1, "postal_code": 1, "venue_name": 1,
         "address": 1, "latitude": 1, "longitude": 1, "capacity": 1,
         "cover_image_url": 1, "price_override": 1},
    )
    if not occ:
        return None
    prod = await products_collection.find_one(
        {"id": occ["product_id"], "is_published": True},
        {"_id": 0, "name": 1, "description": 1, "images": 1, "category": 1,
         "organization_id": 1, "price": 1, "unit_price": 1, "currency": 1,
         "translations": 1},
    )
    if not prod:
        return None
    org = await organizations_collection.find_one(
        {"id": prod["organization_id"]}, {"_id": 0, "name": 1,
                                          "store_settings": 1})
    org_name = ((org or {}).get("store_settings") or {}).get("display_name") \
        or (org or {}).get("name") or ""

    when = sx.human_date(occ.get("start_at"))         # data leggibile, no ISO
    where = occ.get("city") or occ.get("region") or "Italia"
    desc = (prod.get("description") or "")[:300]
    image = _abs_image(occ.get("cover_image_url")
                       or (prod.get("images") or [None])[0])
    canonical = f"{base}/e/{org_slug}/{occ_slug}"

    # SEO1 — location strutturata (PostalAddress + GeoCoordinates) e Offer:
    # è ciò che sblocca il rich result evento con luogo, data e prezzo per
    # le query "ritiro yoga [città]". Niente aggregateRating sull'Event:
    # Google non usa le stelle sugli eventi (finirebbe 'invalid').
    address = sx.postal_address(
        street=occ.get("venue_name") or occ.get("address"),
        city=occ.get("city"), region=occ.get("region"),
        postal_code=occ.get("postal_code"), country=occ.get("country"))
    location = sx.place(
        name=occ.get("venue_name") or where, address=address,
        geo=sx.geo_coordinates(occ.get("latitude"), occ.get("longitude")),
        fallback_name=where)
    price = occ.get("price_override")
    if price is None:
        price = prod.get("unit_price") if prod.get("unit_price") is not None \
            else prod.get("price")
    offer = sx.offer(price=price, currency=prod.get("currency"), url=canonical)

    jsonld = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": prod["name"],
        "startDate": occ.get("start_at"),
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": location,
        "image": [image],
        "description": desc,
        "organizer": {"@type": "Organization", "name": org_name},
        "url": canonical,
    }
    if occ.get("end_at"):
        jsonld["endDate"] = occ["end_at"]
    if offer:
        jsonld["offers"] = offer
    if occ.get("capacity"):
        jsonld["maximumAttendeeCapacity"] = occ["capacity"]

    title = f"{prod['name']} · {where} · {when} | Aurya" if when \
        else f"{prod['name']} · {where} | Aurya"
    cat = prod.get("category")
    crumbs = sx.breadcrumb([
        ("Aurya", f"{base}/"),
        *([(cat.replace("-", " ").title(), f"{base}/ritiri/{cat}")] if cat else []),
        (prod["name"], canonical),
    ])
    return {
        "title": title,
        "description": desc or f"Ritiro a {where} il {when}. Prenota su Aurya.",
        "canonical": canonical,
        "image": image,
        "jsonld": [jsonld, crumbs] if crumbs else jsonld,
        # hreflang: solo lingue con description tradotta (multilingua manuale)
        "hreflang": _hreflang_for(prod.get("translations"), canonical),
    }


async def _meta_blog_list() -> dict:
    """AN6 — hub del blog: hreflang pieno come gli altri hub."""
    from services import seo_schema as sx
    base = _base_url()
    canonical = f"{base}/blog"
    return {
        # SEO1 — il title dell'hub porta le keyword di categoria, non
        # solo la parola "Blog" (che non cerca nessuno).
        "title": "Ritiri, discipline olistiche e benessere | Il magazine di Aurya",
        "description": ("Guide oneste su ritiri olistici, discipline e "
                        "benessere, scritte da chi le pratica e da chi "
                        "le organizza. Il magazine di Aurya."),
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        "image": f"{base}/og-cover.jpg",
        "jsonld": sx.breadcrumb([("Aurya", f"{base}/"), ("Blog", canonical)]),
    }


async def _meta_blog_article(slug: str) -> Optional[dict]:
    """AN6 — articolo: BlogPosting JSON-LD, hreflang solo sulle lingue
    davvero tradotte (title+content, la regola della lista pubblica)."""
    from database import db
    base = _base_url()
    doc = await db.articles.find_one(
        {"slug": slug, "published": True},
        {"_id": 0, "title": 1, "description": 1, "featured_image_url": 1,
         "published_at": 1, "updated_at": 1, "translations": 1,
         "author_name": 1},
    )
    if not doc:
        return None
    canonical = f"{base}/blog/{slug}"
    image = _abs_image(doc.get("featured_image_url"))
    desc = (doc.get("description") or "")[:300]

    hreflang = {"it": canonical, "x-default": canonical}
    for lang, tr in (doc.get("translations") or {}).items():
        if lang in ("en", "de", "fr") and (tr or {}).get("title")                 and (tr or {}).get("content"):
            hreflang[lang] = f"{canonical}?lang={lang}"

    pub = doc.get("published_at")
    upd = doc.get("updated_at")
    jsonld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": doc["title"],
        "description": desc,
        "author": {"@type": "Organization",
                   "name": doc.get("author_name") or "Aurya"},
        "publisher": {"@type": "Organization", "name": "Aurya",
                      "url": f"{base}/"},
        "datePublished": pub.isoformat() if hasattr(pub, "isoformat") else pub,
        "dateModified": upd.isoformat() if hasattr(upd, "isoformat") else upd,
        "url": canonical,
    }
    if image:
        jsonld["image"] = [image]
    from services import seo_schema as sx
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"), ("Blog", f"{base}/blog"),
                            (doc["title"], canonical)])
    return {
        "title": f"{doc['title']} | Aurya",
        "description": desc or "Un articolo dal blog di Aurya.",
        "canonical": canonical,
        "image": image,
        "jsonld": [jsonld, crumbs] if crumbs else jsonld,
        "hreflang": hreflang,
    }


def _hreflang_for(translations: Optional[dict], canonical: str) -> dict:
    out = {"it": canonical, "x-default": canonical}
    for lang, tr in (translations or {}).items():
        if lang in ("en", "de", "fr") and (tr or {}).get("description"):
            out[lang] = f"{canonical}?lang={lang}"
    return out


async def _meta_product(kind: str, org_slug: str, product_slug: str) -> Optional[dict]:
    """Landing prodotto generica: /p /ph /dg /co /r — S1 completerà i
    JSON-LD per tipo; la shell intanto dà title/desc/OG/canonical veri."""
    from database import products_collection
    from services import seo_schema as sx
    base = _base_url()
    prod = await products_collection.find_one(
        {"slug": product_slug, "is_published": True, "is_active": True},
        {"_id": 0, "name": 1, "description": 1, "images": 1, "price": 1,
         "item_type": 1, "translations": 1},
    )
    if not prod:
        return None
    canonical = f"{base}/{kind}/{org_slug}/{product_slug}"
    image = _abs_image((prod.get("images") or [None])[0])
    desc = (prod.get("description") or "")[:300]
    types = {"p": "Service", "co": "Course", "ph": "Product",
             "dg": "Product", "r": "Product"}
    jsonld = {
        "@context": "https://schema.org",
        "@type": types.get(kind, "Product"),
        "name": prod["name"],
        "description": desc,
        "image": [image],
        "url": canonical,
    }
    if prod.get("price") is not None:
        jsonld["offers"] = {"@type": "Offer", "price": prod["price"],
                            "priceCurrency": "EUR",
                            "availability": "https://schema.org/InStock"}
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"), (prod["name"], canonical)])
    return {
        "title": f"{prod['name']} | Aurya",
        "description": desc or prod["name"],
        "canonical": canonical,
        "image": image,
        "jsonld": [jsonld, crumbs] if crumbs else jsonld,
        "hreflang": _hreflang_for(prod.get("translations"), canonical),
    }


async def _meta_destination(place_slug: Optional[str] = None) -> dict:
    from services import seo_schema as sx, seo_listing as sl
    base = _base_url()
    label = place_slug.replace("-", " ").title() if place_slug else None
    path = "/destinazioni" + (f"/{place_slug}" if place_slug else "")
    canonical = f"{base}{path}"

    if not label:
        # hub destinazioni: solo breadcrumb (l'indice dei luoghi lo rende
        # il client; niente noindex, è una pagina hub legittima)
        return {
            "title": "Destinazioni · dove vuoi ritrovarti? | Aurya",
            "description": ("Scegli la destinazione del tuo prossimo ritiro: "
                            "i luoghi con ritiri ed esperienze in programma "
                            "su Aurya."),
            "canonical": canonical,
            "hreflang": _hub_hreflang(canonical),
            "image": f"{base}/og-cover.jpg",
            "jsonld": sx.breadcrumb([("Aurya", f"{base}/"),
                                     ("Destinazioni", canonical)]),
        }

    try:
        retreats = await sl.listable_retreats(place=place_slug, limit=20)
        empty = not retreats
    except Exception:            # noqa: BLE001 — fail open, mai deindicizzare
        retreats, empty = [], False
    # il nome vero del luogo dal primo ritiro (Ostuni, non "Ostuni" slugato)
    real = next((r.get("city") or r.get("region") for r in retreats), label)
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"),
                            ("Destinazioni", f"{base}/destinazioni"),
                            (real, canonical)])
    blocks = [b for b in (crumbs, sx.item_list(retreats, base)) if b]
    return {
        "title": f"Ritiri ed esperienze a {real} | Aurya",
        "description": (f"Ritiri di yoga, meditazione ed esperienze olistiche "
                        f"a {real}: date, prezzi e disponibilità reali. "
                        "Prenota online con la caparra."),
        "canonical": canonical,
        "hreflang": _hub_hreflang(canonical),
        "image": f"{base}/og-cover.jpg",
        "jsonld": blocks or None,
        # destinazione senza ritiri prenotabili → noindex (thin content)
        "noindex": empty,
    }


async def _meta_experiences(category: Optional[str] = None) -> dict:
    base = _base_url()
    label = category.replace("-", " ").title() if category else None
    path = "/esperienze" + (f"/{category}" if category else "")
    return {
        "title": (f"Esperienze di {label} | Aurya" if label
                  else "Esperienze olistiche: massaggi, corsi e soggiorni | Aurya"),
        "description": ("Massaggi, trattamenti, corsi e soggiorni olistici "
                        "dagli organizzatori di Aurya. Prenoti online, paghi "
                        "in sicurezza."),
        "canonical": f"{base}{path}",
        "hreflang": _hub_hreflang(f"{base}{path}"),
        "image": f"{base}/og-cover.jpg",
    }


async def _meta_operators_index(category: Optional[str] = None) -> dict:
    base = _base_url()
    label = category.replace("-", " ").title() if category else None
    path = "/operatori" + (f"/{category}" if category else "")
    return {
        "title": (f"Operatori di {label} | Aurya" if label
                  else "Tutti gli organizzatori di ritiri ed esperienze | Aurya"),
        "description": ("Scopri gli organizzatori di ritiri ed esperienze "
                        "olistiche su Aurya: profili, prossime date e "
                        "prenotazione online con caparra."),
        "canonical": f"{base}{path}",
        "hreflang": _hub_hreflang(f"{base}{path}"),
        "image": f"{base}/og-cover.jpg",
    }


async def _meta_operator(org_slug: str) -> Optional[dict]:
    from database import stores_collection, organizations_collection
    from services import seo_schema as sx
    base = _base_url()
    _proj = {"_id": 0, "name": 1, "public_profile": 1, "store_settings": 1,
             "reviews_stats": 1}
    store = await stores_collection.find_one(
        {"slug": org_slug, "is_published": True},
        {"_id": 0, "organization_id": 1, "name": 1, "description": 1},
    )
    if store:
        org = await organizations_collection.find_one(
            {"id": store["organization_id"]}, _proj)
    else:
        org = await organizations_collection.find_one(
            {"public_slug": org_slug}, _proj)
    if not org:
        return None
    profile = org.get("public_profile") or {}
    # OP4 — stessa risoluzione del pubblico: nome org (settings) prima
    name = (org.get("name")
            or (org.get("store_settings") or {}).get("display_name")
            or org_slug)
    bio = (profile.get("tagline") or profile.get("bio") or "")[:300]
    image = _abs_image(profile.get("logo_url") or profile.get("cover_url")
                       or profile.get("portrait_url"))
    canonical = f"{base}/o/{org_slug}"

    # SEO1 — l'operatore è un LocalBusiness geo-taggato: è ciò che lo fa
    # comparire su Google nella sua zona (la promessa commerciale). Address
    # + geo dal profilo, stelle dalle recensioni verificate, social in
    # sameAs. Solo LocalBusiness/Organization possono portare aggregateRating.
    city, region = profile.get("city"), profile.get("region")
    jsonld = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": name,
        "url": canonical,
        "description": bio,
    }
    if image:
        jsonld["image"] = image
    address = sx.postal_address(city=city, region=region)
    if address:
        jsonld["address"] = address
    geo = sx.geo_coordinates(profile.get("latitude"), profile.get("longitude"))
    if geo:
        jsonld["geo"] = geo
    rating = sx.aggregate_rating(org.get("reviews_stats"))
    if rating:
        jsonld["aggregateRating"] = rating
    sa = sx.same_as(profile.get("instagram"), profile.get("facebook"),
                    profile.get("website"))
    if sa:
        jsonld["sameAs"] = sa
    if profile.get("show_contacts"):
        if profile.get("public_phone"):
            jsonld["telephone"] = profile["public_phone"]
        if profile.get("public_email"):
            jsonld["email"] = profile["public_email"]

    # Title local-oriented: "{nome} · ritiri a {città} | Aurya" cattura la
    # query di brand+luogo dell'operatore.
    title = f"{name} · ritiri a {city} | Aurya" if city \
        else f"{name} · organizzatore su Aurya"
    desc = bio or (f"Ritiri ed esperienze di {name}"
                   + (f" a {city}" if city else "") + " su Aurya.")
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"),
                            ("Organizzatori", f"{base}/operatori"),
                            (name, canonical)])
    hreflang = {"it": canonical, "x-default": canonical}
    for _lang, _f in (profile.get("translations") or {}).items():
        if _lang in ("en", "de", "fr") and (_f or {}).get("bio"):
            hreflang[_lang] = f"{canonical}?lang={_lang}"
    return {
        "title": title,
        "description": desc,
        "canonical": canonical,
        "image": image,
        "jsonld": [jsonld, crumbs] if crumbs else jsonld,
        "hreflang": hreflang,
    }


async def _meta_store(slug: str) -> Optional[dict]:
    from database import stores_collection, organizations_collection
    from services import seo_schema as sx
    base = _base_url()
    store = await stores_collection.find_one(
        {"slug": slug, "is_published": True, "visibility": "public"},
        {"_id": 0, "name": 1, "description": 1, "organization_id": 1},
    )
    if not store:
        return None
    canonical = f"{base}/s/{slug}"
    name = store.get("name") or slug
    jsonld = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": name,
        "url": canonical,
    }
    # SEO1 — lo store è la stessa entità dell'operatore: eredita geo,
    # address, rating e social dal profilo pubblico dell'org collegata.
    org = await organizations_collection.find_one(
        {"id": store.get("organization_id")},
        {"_id": 0, "public_profile": 1, "reviews_stats": 1})
    profile = (org or {}).get("public_profile") or {}
    address = sx.postal_address(city=profile.get("city"),
                                region=profile.get("region"))
    if address:
        jsonld["address"] = address
    geo = sx.geo_coordinates(profile.get("latitude"), profile.get("longitude"))
    if geo:
        jsonld["geo"] = geo
    rating = sx.aggregate_rating((org or {}).get("reviews_stats"))
    if rating:
        jsonld["aggregateRating"] = rating
    sa = sx.same_as(profile.get("instagram"), profile.get("facebook"),
                    profile.get("website"))
    if sa:
        jsonld["sameAs"] = sa
    crumbs = sx.breadcrumb([("Aurya", f"{base}/"), (name, canonical)])
    return {
        "title": f"{name} · negozio su Aurya",
        "description": (store.get("description") or "")[:300]
                       or f"Il negozio di {name} su Aurya.",
        "canonical": canonical,
        "image": f"{base}/og-cover.jpg",
        "jsonld": [jsonld, crumbs] if crumbs else jsonld,
    }


# ── Routing ──────────────────────────────────────────────────────────────────

_PRODUCT_KINDS = ("p", "ph", "dg", "co", "r")


async def resolve_meta(path: str) -> Optional[dict]:
    """path SENZA query, es. '/e/borgo-sereno/ritiro-x'. None = 404 →
    si serve comunque la shell neutra (la SPA mostrerà il suo 404)."""
    parts = [p for p in path.split("/") if p]
    if not parts:
        return await _meta_home()
    head = parts[0]
    if head == "ritiri":
        if len(parts) == 1:
            return await _meta_home()          # /ritiri redirige alla home
        return await _meta_category(parts[1], parts[2] if len(parts) > 2 else None)
    if head == "e" and len(parts) >= 3:
        return await _meta_event(parts[1], parts[2])
    if head in _PRODUCT_KINDS and len(parts) >= 3:
        return await _meta_product(head, parts[1], parts[2])
    if head == "operatori":
        return await _meta_operators_index(parts[1] if len(parts) > 1 else None)
    if head == "destinazioni":
        return await _meta_destination(parts[1] if len(parts) > 1 else None)
    # DS3: /esperienze fuori per ora (redirect alla home lato SPA)
    if head == "o" and len(parts) >= 2:
        return await _meta_operator(parts[1])
    if head == "s" and len(parts) >= 2:
        return await _meta_store(parts[1])
    if head in _BRAND_PAGES and len(parts) == 1:
        return await _meta_brand_page(head)   # AN1 — /chi-siamo, /come-funziona
    if head == "blog":                        # AN6 — il blog sulle stesse rotaie
        if len(parts) == 1:
            return await _meta_blog_list()
        return await _meta_blog_article(parts[1])
    return None


@router.get("/{full_path:path}")
async def seo_shell(full_path: str):
    path = "/" + full_path.strip("/")
    now = time.monotonic()
    hit = _CACHE.get(path)
    if hit and now - hit[1] < _CACHE_TTL:
        return Response(hit[0], media_type="text/html")

    meta = None
    try:
        meta = await resolve_meta(path)
    except Exception as exc:  # noqa: BLE001 — la shell non deve MAI 500
        logger.warning("seo_shell: resolve failed for %s: %s", path, exc)

    # PL22 — in pre-lancio la directory mostra solo campioni d'esempio:
    # onestà anche coi motori (noindex), l'indicizzazione parte al lancio
    # con i contenuti veri. Home e landing lead restano indicizzabili.
    if meta and prelaunch_mode():
        head = path.strip("/").split("/")[0]
        if head in ("ritiri", "operatori", "destinazioni", "esperienze"):
            meta = {**meta, "noindex": True}

    template = _index_html()
    if meta:
        page = _inject(template, meta)
    else:
        page = template  # shell neutra: la SPA gestisce il 404
    _CACHE[path] = (page, now)
    # cache corta lato proxy/browser: i contenuti cambiano coi publish
    return Response(page, media_type="text/html",
                    headers={"Cache-Control": "public, max-age=300"})
