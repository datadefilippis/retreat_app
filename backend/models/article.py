"""AN5 — Blog di Aurya: modello Article.

Un articolo vive in italiano (lingua sorgente, come i prodotti) con
traduzioni manuali opzionali en/de/fr. La categoria è la STESSA
tassonomia dei ritiri (RETREAT_CATEGORIES): il blog alimenta la SEO
delle stesse foglie, non un albero parallelo. Il contenuto è markdown
puro sanitizzato (sanitize_merchant_text — whitelist HTML vuota).
"""

import re
import unicodedata
import uuid
from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator

from models.common import utc_now
from models.retreat_taxonomy import RETREAT_CATEGORIES

ARTICLE_LANGS = ("en", "de", "fr")

# Campi traducibili di un articolo (stesso principio dei prodotti:
# struttura solo in italiano, testi per lingua).
ARTICLE_TRANSLATABLE_FIELDS = ("title", "description", "content")

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify_title(title: str) -> str:
    """Slug URL-safe dal titolo: translitterazione ASCII, minuscole,
    trattini singoli. Non garantisce unicità (la fa il router)."""
    ascii_ = (unicodedata.normalize("NFKD", title or "")
              .encode("ascii", "ignore").decode("ascii"))
    slug = _SLUG_STRIP.sub("-", ascii_.lower()).strip("-")
    return slug[:80] or "articolo"


class ArticleTranslation(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None


class ArticleCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: Optional[str] = Field(default=None, max_length=400)
    content: str = Field(min_length=1)
    category: Optional[str] = None
    featured_image_url: Optional[str] = None
    slug: Optional[str] = None
    translations: Dict[str, ArticleTranslation] = Field(default_factory=dict)

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v):
        if v and v not in RETREAT_CATEGORIES:
            raise ValueError(f"Categoria sconosciuta: {v}")
        return v

    @field_validator("translations")
    @classmethod
    def _valid_langs(cls, v):
        unknown = set(v) - set(ARTICLE_LANGS)
        if unknown:
            raise ValueError(f"Lingue non supportate: {sorted(unknown)}")
        return v


class ArticleUpdate(BaseModel):
    """PATCH whitelisted — extra=ignore di default, ogni campo opzionale.
    NB: come ProductUpdate, un campo nuovo va aggiunto QUI oltre che in
    ArticleCreate, o il PATCH lo scarta in silenzio."""
    title: Optional[str] = Field(default=None, min_length=3, max_length=180)
    description: Optional[str] = Field(default=None, max_length=400)
    content: Optional[str] = None
    category: Optional[str] = None
    featured_image_url: Optional[str] = None
    slug: Optional[str] = None
    translations: Optional[Dict[str, ArticleTranslation]] = None
    published: Optional[bool] = None

    _valid_category = field_validator("category")(
        ArticleCreate._valid_category.__func__)

    @field_validator("translations")
    @classmethod
    def _valid_langs(cls, v):
        if v is None:
            return v
        unknown = set(v) - set(ARTICLE_LANGS)
        if unknown:
            raise ValueError(f"Lingue non supportate: {sorted(unknown)}")
        return v


class Article(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    title: str
    description: Optional[str] = None
    content: str
    category: Optional[str] = None
    featured_image_url: Optional[str] = None
    translations: Dict[str, ArticleTranslation] = Field(default_factory=dict)
    published: bool = False
    published_at: Optional[datetime] = None
    author_name: str = "Aurya"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
