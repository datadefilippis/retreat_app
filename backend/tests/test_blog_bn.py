"""BN1 — blog come primo punto di conversione (guardie).

Contratto sotto guardia (docs/BLOG_NEWSLETTER_STRATEGIA_2026-07.md):
  1. le categorie editoriali (ritiri/energia/operatori) esistono accanto
     alla tassonomia ritiri e passano il validatore articolo;
  2. la pagina articolo converte: CTA newsletter di cluster + correlati,
     e la CTA "Vivi un ritiro" e' di fase (solo marketplace) e solo per
     categorie prenotabili;
  3. il cluster operatori NON chiede l'iscrizione: converte alla rete;
  4. la variante compact del LeadForm resta solo email + consenso.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest

FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"


class TestArticleCategoriesBN1:
    def test_extra_categories_exist(self):
        from models.article import (ARTICLE_CATEGORIES,
                                    ARTICLE_EXTRA_CATEGORIES)
        from models.retreat_taxonomy import RETREAT_CATEGORIES
        assert set(ARTICLE_EXTRA_CATEGORIES) == {"ritiri", "energia",
                                                 "operatori"}
        # le editoriali NON entrano nella tassonomia ritiri (nessuna
        # pagina /ritiri/{cat} fantasma)
        assert not set(ARTICLE_EXTRA_CATEGORIES) & set(RETREAT_CATEGORIES)
        assert set(RETREAT_CATEGORIES) <= set(ARTICLE_CATEGORIES)

    def test_validator_accepts_editorial_category(self):
        from models.article import ArticleCreate, ArticleUpdate
        a = ArticleCreate(title="Guida", content="testo", category="energia")
        assert a.category == "energia"
        u = ArticleUpdate(category="operatori")
        assert u.category == "operatori"
        with pytest.raises(ValueError):
            ArticleCreate(title="Guida", content="testo", category="inventata")

    def test_public_filter_uses_article_categories(self):
        src = (BACKEND_DIR / "routers" / "articles.py").read_text()
        assert "if category not in ARTICLE_CATEGORIES:" in src

    def test_shell_article_section_covers_editorial(self):
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert 'ARTICLE_CATEGORIES[doc["category"]]' in src


class TestBlogFunnelBN1:
    ARTICLE = (FRONTEND_SRC / "features" / "storefront"
               / "BlogArticlePage.js").read_text()
    CTA = (FRONTEND_SRC / "features" / "storefront" / "components"
           / "BlogNewsletterCTA.jsx").read_text()
    INDEX = (FRONTEND_SRC / "features" / "storefront"
             / "BlogIndexPage.js").read_text()
    LEADFORM = (FRONTEND_SRC / "features" / "prelaunch"
                / "LeadForm.jsx").read_text()

    def test_article_has_newsletter_cta_and_related(self):
        assert "<BlogNewsletterCTA category={article.category} />" in self.ARTICLE
        assert "blog-related" in self.ARTICLE

    def test_retreat_cta_is_phase_and_taxonomy_gated(self):
        # niente porte finte: in fase rete /ritiri redirige alla home
        assert ("sitePhase === 'marketplace' && "
                "BOOKABLE_CATS.has(article.category)") in self.ARTICLE

    def test_operator_cluster_converts_to_network(self):
        assert "/entra-nella-rete" in self.CTA
        # il box operatori non monta il form newsletter
        head, _, op_block = self.CTA.partition("cluster === 'operator'")
        op_block = op_block.split("const isRetreat")[0]
        assert "LeadForm" not in op_block

    def test_index_has_newsletter_band(self):
        assert "BlogNewsletterCTA" in self.INDEX

    def test_leadform_compact_is_email_only(self):
        # la variante compact salta i campi profilazione del traveler
        assert "compact ? null : isOperator ?" in self.LEADFORM
        assert "{!compact && (" in self.LEADFORM

    def test_cta_tracks_blog_context(self):
        assert "blog_${category}" in self.CTA


class TestGatedGuidesBN3:
    """BN3 — guide riservate: anteprima onesta per tutti (utente e
    crawler: stesso HTML), sblocco SOLO per subscriber confermati,
    markup paywalled standard (niente cloaking)."""

    def test_access_validator(self):
        import pytest as _pytest

        from models.article import ArticleCreate, ArticleUpdate
        a = ArticleCreate(title="Guida", content="testo", access="subscriber")
        assert a.access == "subscriber"
        assert ArticleCreate(title="Guida", content="x").access == "public"
        assert ArticleUpdate(access="subscriber").access == "subscriber"
        with _pytest.raises(ValueError):
            ArticleCreate(title="Guida", content="x", access="vip")

    def test_gated_preview_intro_and_toc(self):
        from routers.articles import gated_preview
        md = ("Intro uno.\n\nIntro due.\n\n## Sezione A\n\ncorpo\n\n"
              "## Sezione B\n\naltro corpo")
        got = gated_preview(md)
        assert got["content"] == "Intro uno.\n\nIntro due."
        assert got["toc"] == ["Sezione A", "Sezione B"]
        # il corpo delle sezioni NON trapela nell'anteprima
        assert "corpo" not in got["content"]

    def test_shell_serves_paywalled_markup_not_full_body(self):
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert '"isAccessibleForFree"' in src
        assert '"cssSelector": ".gated-content"' in src
        # l'articleBody dei gated viene dall'anteprima, non dal pieno
        assert "gated_preview(content_md)" in src

    def test_return_to_is_blog_only(self):
        from routers.subscribers import _safe_return_to
        assert _safe_return_to("/blog/guida-x") == "/blog/guida-x"
        assert _safe_return_to("https://evil.com") is None
        assert _safe_return_to("/blog//evil.com") is None
        assert _safe_return_to("/account") is None

    def test_frontend_gate_wiring(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "BlogArticlePage.js").read_text()
        assert "aurya_nl_token" in page               # sblocco da localStorage
        assert "blog-gate" in page
        # niente doppio form sulla stessa pagina
        assert "{!article.gated && <BlogNewsletterCTA" in page
        confirm = (FRONTEND_SRC / "features" / "prelaunch"
                   / "NewsletterConfirmPage.js").read_text()
        assert "aurya_nl_token" in confirm            # persistenza token
        assert "startsWith('/blog/')" in confirm      # next filtrato


class TestCategoryHubsBN5:
    """BN5 — hub categoria del Magazine: rotte vere indicizzabili
    (ItemList + canonical), vuoti in noindex, in sitemap solo se
    popolati; standard editoriale imposto al publish."""

    def test_hub_live_populated_category(self):
        # contro il backend live (il DB dei test unit puo' essere vuoto)
        import os

        import requests as rq
        base = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
        r = rq.get(f"{base}/__seo/blog/categoria/energia", timeout=10)
        assert r.status_code == 200
        assert '"@type": "ItemList"' in r.text
        assert '/blog/categoria/energia"' in r.text      # canonical
        assert 'content="noindex"' not in r.text

    def test_hub_live_empty_category_noindex(self):
        import os

        import requests as rq
        base = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
        r = rq.get(f"{base}/__seo/blog/categoria/massaggio", timeout=10)
        assert r.status_code == 200
        assert 'content="noindex"' in r.text

    @pytest.mark.asyncio
    async def test_hub_unknown_category_is_404(self):
        from routers.seo_shell import _meta_blog_category
        assert await _meta_blog_category("inventata") is None

    @pytest.mark.asyncio
    async def test_editorial_gate_on_publish(self):
        from fastapi import HTTPException

        from routers.articles import _editorial_gate
        ok = {"category": "yoga", "description": "x" * 130}
        _editorial_gate(ok)                      # non solleva
        with pytest.raises(HTTPException):
            _editorial_gate({"category": None, "description": "x" * 130})
        with pytest.raises(HTTPException):
            _editorial_gate({"category": "yoga", "description": "corta"})

    def test_spa_uses_route_not_query(self):
        idx = (FRONTEND_SRC / "features" / "storefront"
               / "BlogIndexPage.js").read_text()
        assert "navigate(`/blog/categoria/${slug}`)" in idx
        art = (FRONTEND_SRC / "features" / "storefront"
               / "BlogArticlePage.js").read_text()
        assert "/blog/categoria/${article.category}" in art

    def test_sitemap_includes_populated_hubs_only(self):
        src = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert 'distinct("category", {"published": True})' in src
        assert "/blog/categoria/" in src
