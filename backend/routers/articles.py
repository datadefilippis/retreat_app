"""AN5 — Blog di Aurya: CRUD system-admin + endpoint pubblici.

Regole di lingua (le STESSE del multilingua prodotti):
- l'italiano è la lingua sorgente; le traduzioni en/de/fr sono manuali;
- la LISTA in lingua X mostra solo articoli con traduzione X completa
  (title+content), mai fallback — hreflang onesti;
- il DETTAGLIO in lingua X senza traduzione serve l'italiano e lo
  dichiara (served_lang): un link diretto non deve mai fare 404.

Scrive solo il system admin (require_system_admin); la struttura è
pronta per autori futuri (author_name sul documento).
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_system_admin
from database import db
from models.article import (ARTICLE_LANGS, ARTICLE_TRANSLATABLE_FIELDS,
                            Article, ArticleCreate, ArticleUpdate,
                            slugify_title)
from models.common import utc_now
from models.retreat_taxonomy import RETREAT_CATEGORIES
from services.markdown_safe import sanitize_merchant_text

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Articles"])

_LIST_PAGE_SIZE_MAX = 50


# ─── Sanitizzazione ────────────────────────────────────────────────────

def _sanitize_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitizza in place i campi testuali (italiano + traduzioni).
    Il contenuto resta markdown puro: whitelist HTML vuota."""
    for field in ("title", "description", "content"):
        if data.get(field) is not None:
            data[field] = sanitize_merchant_text(data[field])
    translations = data.get("translations")
    if translations:
        for lang, tr in translations.items():
            for field in ARTICLE_TRANSLATABLE_FIELDS:
                if tr.get(field) is not None:
                    tr[field] = sanitize_merchant_text(tr[field])
    return data


async def _unique_slug(base: str, *, exclude_id: Optional[str] = None) -> str:
    """Slug unico: base, poi base-2, base-3… (mai sovrascrivere)."""
    slug = base
    n = 1
    while True:
        query: Dict[str, Any] = {"slug": slug}
        if exclude_id:
            query["id"] = {"$ne": exclude_id}
        if not await db.articles.find_one(query, {"_id": 1}):
            return slug
        n += 1
        slug = f"{base}-{n}"


# ─── Proiezioni pubbliche ──────────────────────────────────────────────

def _has_translation(doc: Dict[str, Any], lang: str) -> bool:
    tr = (doc.get("translations") or {}).get(lang) or {}
    return bool((tr.get("title") or "").strip()
                and (tr.get("content") or "").strip())


def _localized(doc: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """Campi testuali nella lingua richiesta; served_lang dice la verità."""
    out = {
        "slug": doc["slug"],
        "title": doc["title"],
        "description": doc.get("description"),
        "category": doc.get("category"),
        "featured_image_url": doc.get("featured_image_url"),
        "author_name": doc.get("author_name") or "Aurya",
        "published_at": doc.get("published_at"),
        "served_lang": "it",
        "available_langs": ["it"] + [l for l in ARTICLE_LANGS
                                     if _has_translation(doc, l)],
    }
    if lang in ARTICLE_LANGS and _has_translation(doc, lang):
        tr = doc["translations"][lang]
        out["title"] = tr["title"]
        if (tr.get("description") or "").strip():
            out["description"] = tr["description"]
        out["served_lang"] = lang
    return out


# ─── Endpoint pubblici ─────────────────────────────────────────────────

@router.get("/public/articles")
async def list_public_articles(
    category: Optional[str] = None,
    lang: str = "it",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=_LIST_PAGE_SIZE_MAX),
) -> Dict[str, Any]:
    query: Dict[str, Any] = {"published": True}
    if category:
        if category not in RETREAT_CATEGORIES:
            return {"items": [], "total": 0, "page": page}
        query["category"] = category
    if lang in ARTICLE_LANGS:
        # lista onesta: in lingua X solo gli articoli tradotti in X
        query[f"translations.{lang}.title"] = {"$nin": [None, ""]}
        query[f"translations.{lang}.content"] = {"$nin": [None, ""]}

    total = await db.articles.count_documents(query)
    cursor = (db.articles.find(query, {"_id": 0, "content": 0})
              .sort("published_at", -1)
              .skip((page - 1) * page_size).limit(page_size))
    docs = await cursor.to_list(page_size)
    return {
        "items": [_localized(d, lang) for d in docs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/public/articles/{slug}")
async def get_public_article(slug: str, lang: str = "it") -> Dict[str, Any]:
    doc = await db.articles.find_one({"slug": slug, "published": True},
                                     {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    out = _localized(doc, lang)
    out["content"] = doc["content"]
    if out["served_lang"] != "it":
        tr = doc["translations"][lang]
        out["content"] = tr["content"]
    return out


# ─── Cover autogenerata (AN6) ──────────────────────────────────────────

async def _autogen_cover(slug: str, title: str,
                         category: Optional[str]) -> Optional[str]:
    """Rende la cover brand (WebP 1200×630) e la salva su object
    storage. Best-effort SEMPRE: None se qualcosa manca, mai raise."""
    try:
        from services.article_cover import render_article_cover
        from services.object_storage import save_public_upload
        label = RETREAT_CATEGORIES.get(category or "")
        data = await asyncio.to_thread(render_article_cover, title,
                                       category, label)
        if not data:
            return None
        return save_public_upload("article-covers", f"{slug}.webp",
                                  data, "image/webp")
    except Exception as exc:          # noqa: BLE001 — mai bloccare un publish
        logger.warning("article cover skipped for %s: %s", slug, exc)
        return None


# ─── Endpoint admin (system admin only) ────────────────────────────────

@router.get("/admin/articles")
async def admin_list_articles(
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    docs = await (db.articles.find({}, {"_id": 0, "content": 0})
                  .sort("updated_at", -1).to_list(200))
    for d in docs:
        d["translated_langs"] = [l for l in ARTICLE_LANGS
                                 if _has_translation(d, l)]
    return {"items": docs, "categories": RETREAT_CATEGORIES}


@router.get("/admin/articles/{article_id}")
async def admin_get_article(
    article_id: str,
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    doc = await db.articles.find_one({"id": article_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    return doc


@router.post("/admin/articles", status_code=201)
async def admin_create_article(
    payload: ArticleCreate,
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    data = _sanitize_payload(payload.model_dump())
    base = slugify_title(data.pop("slug", None) or data["title"])
    article = Article(
        **{k: v for k, v in data.items() if k != "slug"},
        slug=await _unique_slug(base),
        author_name=current_user.get("full_name") or "Aurya",
    )
    await db.articles.insert_one(article.model_dump())
    return {"id": article.id, "slug": article.slug}


@router.patch("/admin/articles/{article_id}")
async def admin_update_article(
    article_id: str,
    payload: ArticleUpdate,
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    doc = await db.articles.find_one({"id": article_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Articolo non trovato")

    data = _sanitize_payload(payload.model_dump(exclude_unset=True))
    if "slug" in data and data["slug"]:
        data["slug"] = await _unique_slug(slugify_title(data["slug"]),
                                          exclude_id=article_id)
    # publish: timbra published_at alla PRIMA pubblicazione
    publishing = bool(data.get("published")) and not doc.get("published")
    if data.get("published") and not doc.get("published_at"):
        data["published_at"] = utc_now()
    data["updated_at"] = utc_now()

    # AN6 — al publish senza immagine propria, la cover Aurya si genera
    # da sola (titolo dentro, palette di categoria)
    if publishing and not (data.get("featured_image_url")
                           or doc.get("featured_image_url")):
        cover_url = await _autogen_cover(
            data.get("slug") or doc["slug"],
            data.get("title") or doc["title"],
            data.get("category", doc.get("category")))
        if cover_url:
            data["featured_image_url"] = cover_url

    await db.articles.update_one({"id": article_id}, {"$set": data})

    # AN6 — IndexNow al publish: stesse rotaie di ritiri e prodotti
    if publishing:
        try:
            from services.indexnow import ping_urls_async
            asyncio.create_task(ping_urls_async(
                [f"/blog/{data.get('slug') or doc['slug']}"]))
        except Exception:             # noqa: BLE001 — best-effort
            pass
    updated = await db.articles.find_one({"id": article_id}, {"_id": 0})
    return updated


@router.post("/admin/articles/{article_id}/cover")
async def admin_regenerate_cover(
    article_id: str,
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    """AN6 — rigenera la cover autogenerata (sovrascrive anche una
    immagine propria: è un'azione esplicita dell'admin)."""
    doc = await db.articles.find_one({"id": article_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    cover_url = await _autogen_cover(doc["slug"], doc["title"],
                                     doc.get("category"))
    if not cover_url:
        raise HTTPException(status_code=503,
                            detail="Generazione cover non disponibile")
    await db.articles.update_one(
        {"id": article_id},
        {"$set": {"featured_image_url": cover_url,
                  "updated_at": utc_now()}})
    return {"featured_image_url": cover_url}


@router.delete("/admin/articles/{article_id}", status_code=204)
async def admin_delete_article(
    article_id: str,
    current_user: dict = Depends(require_system_admin),
) -> None:
    res = await db.articles.delete_one({"id": article_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
