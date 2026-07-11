"""AN5 — Blog di Aurya: guardie su modello, router e frontend.

Il blog condivide la tassonomia dei ritiri e le regole multilingua dei
prodotti (lista onesta per lingua, italiano sorgente). Queste guardie
inchiodano i confini: solo il system admin scrive, il pubblico vede
solo il pubblicato, il contenuto passa SEMPRE dal sanitizer.
"""

import json
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
LANGS = ("it", "en", "de", "fr")


class TestArticleModel:

    def test_slugify(self):
        from models.article import slugify_title
        assert slugify_title("Perché lo yoga cambia il respiro") == \
            "perche-lo-yoga-cambia-il-respiro"
        assert slugify_title("  Détox & Digiuno: guida  ") == \
            "detox-digiuno-guida"
        assert slugify_title("???") == "articolo"      # mai slug vuoto
        assert len(slugify_title("x" * 300)) <= 80

    def test_category_must_be_in_retreat_taxonomy(self):
        """Il blog NON ha un albero suo: stessa tassonomia dei ritiri."""
        from models.article import ArticleCreate
        ok = ArticleCreate(title="Titolo valido", content="c", category="yoga")
        assert ok.category == "yoga"
        with pytest.raises(ValueError):
            ArticleCreate(title="Titolo valido", content="c",
                          category="ricette-vegane")

    def test_translations_langs_whitelist(self):
        from models.article import ArticleCreate
        with pytest.raises(ValueError):
            ArticleCreate(title="Titolo valido", content="c",
                          translations={"es": {"title": "Hola"}})


class TestArticleRouterGuards:

    def _src(self):
        return (BACKEND_DIR / "routers" / "articles.py").read_text()

    def test_admin_endpoints_require_system_admin(self):
        """Ogni endpoint admin dipende da require_system_admin — il blog
        lo scrive solo la piattaforma, non gli operatori."""
        src = self._src()
        admin_routes = src.count('"/admin/articles')
        assert admin_routes >= 5
        assert src.count("Depends(require_system_admin)") >= 5

    def test_public_endpoints_only_published(self):
        src = self._src()
        assert '"published": True' in src

    def test_all_text_goes_through_sanitizer(self):
        """Create e patch passano da _sanitize_payload (markdown puro,
        whitelist HTML vuota) — traduzioni comprese."""
        src = self._src()
        assert "sanitize_merchant_text" in src
        assert src.count("_sanitize_payload") >= 3   # def + create + patch

    def test_honest_language_listing(self):
        """In lingua X la lista mostra solo articoli tradotti in X
        (title+content), come i prodotti: mai fallback in lista."""
        src = self._src()
        assert 'query[f"translations.{lang}.title"]' in src
        assert 'query[f"translations.{lang}.content"]' in src

    def test_sanitizer_strips_script(self):
        from services.markdown_safe import sanitize_merchant_text
        dirty = "## Titolo\n<script>alert(1)</script>**ok**"
        clean = sanitize_merchant_text(dirty)
        assert "<script>" not in clean
        assert "**ok**" in clean

    def test_router_registered_and_indexed(self):
        server = (BACKEND_DIR / "server.py").read_text()
        assert "articles_router" in server
        database = (BACKEND_DIR / "database.py").read_text()
        assert "an5_article_slug" in database


class TestBlogFrontend:

    def test_pages_exist_and_use_safe_renderer(self):
        article = (FRONTEND_SRC / "features" / "storefront"
                   / "BlogArticlePage.js").read_text()
        # il markdown passa dal renderer sicuro condiviso, mai da
        # dangerouslySetInnerHTML
        assert "LegalMarkdownRenderer" in article
        assert "dangerouslySetInnerHTML" not in article
        index = (FRONTEND_SRC / "features" / "storefront"
                 / "BlogIndexPage.js").read_text()
        assert "/public/articles" in index

    def test_routes_and_nav(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/blog"' in app
        assert 'path="/blog/:slug"' in app
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        assert "navBlog" in shell
        # menu (to: '/blog') + footer (to="/blog")
        assert shell.count("'/blog'") + shell.count('"/blog"') >= 2

    def test_admin_tab_wired(self):
        admin = (FRONTEND_SRC / "features" / "admin"
                 / "AdminPage.js").read_text()
        assert "BlogAdminTab" in admin
        tab = (FRONTEND_SRC / "features" / "admin"
               / "BlogAdminTab.js").read_text()
        assert "MultiLangSection" in tab             # tab lingua unificate
        assert "/admin/articles" in tab

    def test_blog_i18n_keys_all_langs(self):
        needed = ("seoTitle", "title", "subtitle", "readMore", "empty",
                  "notFound", "backToBlog", "italianOnly")
        for lang in LANGS:
            data = json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            assert "blog" in data, f"{lang}: blocco blog mancante"
            for key in needed:
                assert key in data["blog"], f"{lang}: blog.{key} mancante"
            assert "navBlog" in data["marketplace"], f"{lang}: navBlog"

    def test_no_em_dash_in_blog_copy(self):
        """Regola RB4 anche qui: zero trattini lunghi nel copy blog."""
        for rel in ("features/storefront/BlogIndexPage.js",
                    "features/storefront/BlogArticlePage.js"):
            src = (FRONTEND_SRC / rel).read_text()
            for line in src.splitlines():
                if "defaultValue" in line:
                    assert "—" not in line, f"{rel}: trattino lungo nel copy"


class TestBlogSeoAn6:
    """AN6 — il blog sulle stesse rotaie SEO dei ritiri: shell
    server-side con BlogPosting, sitemap-articles nel canone, IndexNow
    al publish, cover autogenerata quando manca un'immagine propria."""

    def test_seo_shell_resolves_blog(self):
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert "_meta_blog_list" in src
        assert "_meta_blog_article" in src
        assert '"BlogPosting"' in src
        assert '"blog"' in src                     # branch nel dispatcher

    def test_sitemap_articles_in_canon(self):
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert "build_articles" in seo
        assert "sitemap-articles.xml" in seo
        assert '"articles"' in seo                 # nel sitemap index
        inv = (BACKEND_DIR / "tests" / "test_seo_invariants.py").read_text()
        assert '"articles"' in inv                 # nel canone invariants

    def test_publish_pings_indexnow_and_makes_cover(self):
        src = (BACKEND_DIR / "routers" / "articles.py").read_text()
        assert "ping_urls_async" in src
        assert "_autogen_cover" in src
        # la cover non sovrascrive MAI una immagine propria al publish
        assert 'not (data.get("featured_image_url")' in src

    def test_cover_renders_all_categories(self):
        """Ogni categoria della tassonomia ha la sua palette e rende
        un WebP 1200x630 valido col titolo dentro."""
        from io import BytesIO
        from PIL import Image
        from models.retreat_taxonomy import RETREAT_CATEGORIES
        from services.article_cover import (CATEGORY_PALETTES,
                                            render_article_cover)
        assert set(CATEGORY_PALETTES) == set(RETREAT_CATEGORIES)
        data = render_article_cover("Titolo di prova per la cover",
                                    category="suono",
                                    category_label="Suono & Sound Healing")
        assert data and data[:4] == b"RIFF"        # container WebP
        img = Image.open(BytesIO(data))
        assert img.size == (1200, 630)             # OG-perfetto

    def test_cover_is_best_effort(self):
        """Il generatore non solleva MAI: titolo estremo → bytes o None,
        mai eccezione (un publish non si blocca per una cover)."""
        from services.article_cover import render_article_cover
        out = render_article_cover("x" * 500, category="inesistente")
        assert out is None or isinstance(out, bytes)

    def test_fonts_shipped(self):
        """I font brand (OFL) viaggiano col repo: la cover non dipende
        dai font di sistema del VPS."""
        fonts = BACKEND_DIR / "assets" / "fonts"
        assert (fonts / "Cinzel-SemiBold.ttf").exists()
        assert (fonts / "Manrope-Regular.ttf").exists()


# ── SEO4 (consolidamento 11/7) ───────────────────────────────────────────────

def test_seo4_article_shell_serves_body_faq_person():
    """I crawler senza JS (LLM inclusi) leggono SOLO l'HTML iniziale:
    l'articolo INTERO deve stare nel JSON-LD (articleBody), le FAQ
    diventano FAQPage, la firma vera diventa Person (E-E-A-T)."""
    src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text(encoding="utf-8")
    assert '"articleBody"' in src, "l'articolo intero deve stare nel JSON-LD"
    assert '"FAQPage"' in src
    assert "_extract_faq" in src
    assert '"@type": "Person"' in src, "firma vera = Person, non Organization"
    assert '"inLanguage": "it"' in src


def test_seo4_llms_txt_exists_and_points_home():
    """GEO — llms.txt presenta Aurya agli assistenti AI."""
    p = BACKEND_DIR / "assets" / "llms.txt"
    txt = p.read_text(encoding="utf-8")
    assert "aurya.life" in txt
    assert "ritiri olistici" in txt.lower()
    assert "sitemap" in txt.lower()
    server = (BACKEND_DIR / "server.py").read_text(encoding="utf-8")
    assert '@app.get("/llms.txt"' in server, \
        "il proxy manda i *.txt di root al backend: serve la route"


def test_seo4_faq_extraction_works_on_seed_articles():
    """Ogni articolo del seed deve produrre almeno 3 FAQ estraibili
    (il blocco Domande frequenti è parte del formato, non un optional)."""
    from routers.seo_shell import _extract_faq
    from scripts.seed_blog_initial_articles import ARTICLES
    for slug, _t, _d, _c, _a, content in ARTICLES:
        faqs = _extract_faq(content)
        assert len(faqs) >= 3, f"{slug}: solo {len(faqs)} FAQ estratte"
