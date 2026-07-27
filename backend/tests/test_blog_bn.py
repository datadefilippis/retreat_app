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
