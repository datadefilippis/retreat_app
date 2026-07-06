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
  SEO_SHELL_INDEX_PATH  path dell'index.html della build
                        (default: ../frontend/build/index.html)
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/__seo", tags=["SEO shell"])

_CACHE: dict = {}          # path → (html, monotonic_ts)
_CACHE_TTL = 600
_INDEX_CACHE: dict = {"html": None, "mtime": None}

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
    path = Path(os.environ.get(
        "SEO_SHELL_INDEX_PATH",
        Path(__file__).resolve().parent.parent.parent / "frontend" / "build" / "index.html",
    ))
    try:
        mtime = path.stat().st_mtime
        if _INDEX_CACHE["html"] is None or _INDEX_CACHE["mtime"] != mtime:
            _INDEX_CACHE["html"] = path.read_text(encoding="utf-8")
            _INDEX_CACHE["mtime"] = mtime
        return _INDEX_CACHE["html"]
    except OSError:
        return _DEV_TEMPLATE


def _inject(template: str, meta: dict) -> str:
    """Sostituisce title/description e appende OG/canonical/JSON-LD."""
    title = _html.escape(meta.get("title") or "Aurya")
    desc = _html.escape(meta.get("description") or "")

    out = re.sub(r"<title>.*?</title>", f"<title>{title}</title>",
                 template, count=1, flags=re.S)
    out = re.sub(r'<meta name="description"[^>]*/?>',
                 f'<meta name="description" content="{desc}"/>',
                 out, count=1)

    extra = [
        f'<meta property="og:title" content="{title}"/>',
        f'<meta property="og:description" content="{desc}"/>',
        '<meta property="og:type" content="website"/>',
        '<meta name="twitter:card" content="summary_large_image"/>',
    ]
    if meta.get("image"):
        extra.append(f'<meta property="og:image" content="{_html.escape(meta["image"])}"/>')
    if meta.get("canonical"):
        canonical = _html.escape(meta["canonical"])
        extra.append(f'<link rel="canonical" href="{canonical}"/>')
        extra.append(f'<meta property="og:url" content="{canonical}"/>')
    for lang, href in (meta.get("hreflang") or {}).items():
        extra.append(f'<link rel="alternate" hreflang="{lang}" href="{_html.escape(href)}"/>')
    if meta.get("noindex"):
        extra.append('<meta name="robots" content="noindex"/>')
    if meta.get("jsonld"):
        extra.append('<script type="application/ld+json">'
                     + json.dumps(meta["jsonld"], ensure_ascii=False)
                     + "</script>")

    return out.replace("</head>", "".join(extra) + "</head>", 1)


def _abs_image(url: Optional[str]) -> str:
    """Cover assoluta con fallback SEMPRE presente (logo Aurya)."""
    base = _base_url()
    if not url:
        return f"{base}/logo-aurya.png"
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
        "title": "Aurya — Ritiri ed esperienze olistiche",
        "description": ("Trova e prenota ritiri di yoga, meditazione, detox "
                        "ed esperienze olistiche in tutta Italia: date, prezzi "
                        "e disponibilità reali, prenoti online con la caparra."),
        "canonical": f"{base}/",
        "hreflang": _hub_hreflang(f"{base}/"),
        "image": f"{base}/logo-aurya.png",
        "jsonld": {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Aurya",
            "url": f"{base}/",
        },
    }


async def _meta_category(cat: str, region: Optional[str] = None) -> dict:
    base = _base_url()
    label = cat.replace("-", " ").title()
    where = f" in {region.title()}" if region else " in Italia"
    path = f"/ritiri/{cat}" + (f"/{region}" if region else "")
    return {
        "title": f"Ritiri di {label}{where} | Aurya",
        "description": (f"I migliori ritiri di {label.lower()}{where}: "
                        "date, prezzi e posti disponibili. Prenota online "
                        "con la caparra su Aurya."),
        "canonical": f"{base}{path}",
        "hreflang": _hub_hreflang(f"{base}{path}"),
        "image": f"{base}/logo-aurya.png",
    }


async def _meta_event(org_slug: str, occ_slug: str) -> Optional[dict]:
    from database import (event_occurrences_collection, products_collection,
                          organizations_collection)
    base = _base_url()
    occ = await event_occurrences_collection.find_one(
        {"slug": occ_slug, "status": "published"},
        {"_id": 0, "product_id": 1, "start_at": 1, "end_at": 1, "city": 1,
         "region": 1, "cover_image_url": 1, "price_override": 1},
    )
    if not occ:
        return None
    prod = await products_collection.find_one(
        {"id": occ["product_id"], "is_published": True},
        {"_id": 0, "name": 1, "description": 1, "images": 1,
         "organization_id": 1, "price": 1, "translations": 1},
    )
    if not prod:
        return None
    org = await organizations_collection.find_one(
        {"id": prod["organization_id"]}, {"_id": 0, "name": 1,
                                          "store_settings": 1})
    org_name = ((org or {}).get("store_settings") or {}).get("display_name") \
        or (org or {}).get("name") or ""

    when = (occ.get("start_at") or "")[:10]
    where = occ.get("city") or occ.get("region") or "Italia"
    desc = (prod.get("description") or "")[:300]
    image = _abs_image(occ.get("cover_image_url")
                       or (prod.get("images") or [None])[0])
    canonical = f"{base}/e/{org_slug}/{occ_slug}"

    jsonld = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": prod["name"],
        "startDate": occ.get("start_at"),
        "endDate": occ.get("end_at"),
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {"@type": "Place", "name": where,
                     "address": where},
        "image": [image],
        "description": desc,
        "organizer": {"@type": "Organization", "name": org_name},
        "url": canonical,
    }
    return {
        "title": f"{prod['name']} — {where}, {when} | Aurya",
        "description": desc or f"Ritiro a {where} il {when}. Prenota su Aurya.",
        "canonical": canonical,
        "image": image,
        "jsonld": jsonld,
        # hreflang: solo lingue con description tradotta (multilingua manuale)
        "hreflang": _hreflang_for(prod.get("translations"), canonical),
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
    return {
        "title": f"{prod['name']} | Aurya",
        "description": desc or prod["name"],
        "canonical": canonical,
        "image": image,
        "jsonld": jsonld,
        "hreflang": _hreflang_for(prod.get("translations"), canonical),
    }


async def _meta_destination(place_slug: Optional[str] = None) -> dict:
    base = _base_url()
    label = place_slug.replace("-", " ").title() if place_slug else None
    path = "/destinazioni" + (f"/{place_slug}" if place_slug else "")
    return {
        "title": (f"Ritiri ed esperienze a {label} | Aurya" if label
                  else "Destinazioni — dove vuoi ritrovarti? | Aurya"),
        "description": ((f"Ritiri di yoga, meditazione ed esperienze "
                         f"olistiche a {label}: date, prezzi e "
                         f"disponibilità reali. Prenota online con la caparra.")
                        if label else
                        ("Scegli la destinazione del tuo prossimo ritiro: i "
                         "luoghi con ritiri ed esperienze in programma su Aurya.")),
        "canonical": f"{base}{path}",
        "hreflang": _hub_hreflang(f"{base}{path}"),
        "image": f"{base}/logo-aurya.png",
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
        "image": f"{base}/logo-aurya.png",
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
        "image": f"{base}/logo-aurya.png",
    }


async def _meta_operator(org_slug: str) -> Optional[dict]:
    from database import stores_collection, organizations_collection
    base = _base_url()
    store = await stores_collection.find_one(
        {"slug": org_slug, "is_published": True},
        {"_id": 0, "organization_id": 1, "name": 1, "description": 1},
    )
    org = None
    if store:
        org = await organizations_collection.find_one(
            {"id": store["organization_id"]},
            {"_id": 0, "name": 1, "public_profile": 1, "store_settings": 1})
    else:
        org = await organizations_collection.find_one(
            {"public_slug": org_slug}, {"_id": 0, "name": 1,
                                        "public_profile": 1,
                                        "store_settings": 1})
    if not org:
        return None
    profile = org.get("public_profile") or {}
    name = ((org.get("store_settings") or {}).get("display_name")
            or org.get("name") or org_slug)
    bio = (profile.get("bio") or "")[:300]
    image = _abs_image(profile.get("logo_url") or profile.get("cover_url"))
    canonical = f"{base}/o/{org_slug}"
    return {
        "title": f"{name} — organizzatore su Aurya",
        "description": bio or f"Ritiri ed esperienze di {name} su Aurya.",
        "canonical": canonical,
        "image": image,
        "jsonld": {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": name,
            "url": canonical,
            "description": bio,
        },
    }


async def _meta_store(slug: str) -> Optional[dict]:
    from database import stores_collection
    base = _base_url()
    store = await stores_collection.find_one(
        {"slug": slug, "is_published": True, "visibility": "public"},
        {"_id": 0, "name": 1, "description": 1},
    )
    if not store:
        return None
    canonical = f"{base}/s/{slug}"
    return {
        "title": f"{store.get('name') or slug} — negozio su Aurya",
        "description": (store.get("description") or "")[:300]
                       or f"Il negozio di {store.get('name') or slug} su Aurya.",
        "canonical": canonical,
        "image": f"{base}/logo-aurya.png",
        "jsonld": {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": store.get("name") or slug,
            "url": canonical,
        },
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
    if head == "esperienze":
        return await _meta_experiences(parts[1] if len(parts) > 1 else None)
    if head == "o" and len(parts) >= 2:
        return await _meta_operator(parts[1])
    if head == "s" and len(parts) >= 2:
        return await _meta_store(parts[1])
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

    template = _index_html()
    if meta:
        page = _inject(template, meta)
    else:
        page = template  # shell neutra: la SPA gestisce il 404
    _CACHE[path] = (page, now)
    # cache corta lato proxy/browser: i contenuti cambiano coi publish
    return Response(page, media_type="text/html",
                    headers={"Cache-Control": "public, max-age=300"})
