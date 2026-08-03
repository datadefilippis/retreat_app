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
        # SW4 — "readMore" e' uscito col bottone "Leggi": nel kit
        # editoriale il titolo E' il link. Al suo posto entrano le
        # chiavi dell'apertura nuova, che valgono la stessa guardia.
        needed = ("seoTitle", "title", "eyebrow", "lead1", "lead2",
                  "subtitle", "empty", "emptyCat", "moreTitle",
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
        un WebP 1200x630 valido (da SW4 senza titolo stampato)."""
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


def test_seo5_robots_allows_child_sitemaps():
    """SEO5 — Disallow /api/ NON deve coprire le sotto-sitemap: senza
    l'Allow esplicito Google legge l'indice ma rileva 0 pagine."""
    server = (BACKEND_DIR / "server.py").read_text(encoding="utf-8")
    assert 'Allow: /api/public/sitemap-' in server, \
        "regressione: le sotto-sitemap tornerebbero bloccate dal robots"


def test_seo6_shell_hard_404_and_organization():
    """SEO6 (audit P0) — niente soft-404: quando il resolver non trova
    il contenuto la shell risponde 404 vero (la SPA mostra comunque il
    suo 404). E la home serve l'entita' Organization (Knowledge Graph)."""
    src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text(encoding="utf-8")
    assert "status = 404" in src, \
        "regressione: gli URL inesistenti tornerebbero soft-404 (200)"
    assert "status_code=status" in src
    assert '"@type": "Organization"' in src
    assert '"founder"' in src


def test_ga2_csp_allows_google_analytics():
    """GA2 — la CSP di nginx deve permettere gtag.js e gli endpoint
    dati di GA4 (inclusi i regionali), o l'analytics muore in silenzio
    nel browser: zero errori server, zero dati."""
    conf = (BACKEND_DIR.parent / "deploy" / "nginx" / "nginx.conf"
            ).read_text(encoding="utf-8")
    assert "https://www.googletagmanager.com" in conf
    assert "https://*.google-analytics.com" in conf
    assert "https://*.analytics.google.com" in conf


# ── SW4b (31/7) — l'URL della copertina e il ritmo della vetrina ─────────────

class TestMagazineSw4b:
    """SW4b — due correzioni all'onda SW4.

    1. LE COPERTINE VECCHIE RESTAVANO NEI BROWSER. Il file cambiava, il
       nome no: `/uploads/article-covers/{slug}.webp` viene servito con
       `cache-control: public, max-age=31536000, immutable`, quindi chi
       aveva gia' visto il blog teneva la copertina vecchia (quella col
       titolo stampato) per un anno. Nessuna purge di CDN entra nella
       cache di un browser. Ora il nome porta l'impronta dei byte
       generati, `{slug}-{hash8}.webp`, e sta nel PERCORSO: una query
       string `?v=` si perde dietro certi CDN e certi object storage.
    2. IL MAGAZINE DOVEVA RESPIRARE: copertine grandi e testo sotto,
       meno articoli per riga (richiesta del founder, 31/7).
    """

    CARD = FRONTEND_SRC / "components" / "editorial" / "ArticleCard.jsx"
    INDEX = FRONTEND_SRC / "features" / "storefront" / "BlogIndexPage.js"

    # ── 1. l'URL cambia quando cambia l'immagine ─────────────────────

    def test_nome_versionato_e_deterministico(self):
        """Stessi byte → stesso nome (rilanciare lo script non muove
        nulla); byte diversi (= template diverso) → nome diverso."""
        import re
        from services.article_cover import cover_asset_name
        uno = cover_asset_name("guida-yoga", b"template-v1")
        due = cover_asset_name("guida-yoga", b"template-v1")
        tre = cover_asset_name("guida-yoga", b"template-v2")
        assert uno == due, "stesso input, nome diverso: non e' idempotente"
        assert uno != tre, \
            "template diverso, stesso URL: le cache terrebbero il vecchio"
        assert re.fullmatch(r"guida-yoga-[0-9a-f]{8}\.webp", uno), uno
        # l'impronta sta nel percorso, non in query string
        assert "?" not in uno

    def test_il_template_vero_cambia_il_nome(self):
        """Non un test sintetico: due copertine di categoria diversa
        sono immagini diverse e devono avere nomi diversi."""
        from services.article_cover import (cover_asset_name,
                                            render_article_cover)
        a = render_article_cover(None, "yoga", "Yoga")
        b = render_article_cover(None, "suono", "Suono & Sound Healing")
        assert a and b and a != b
        assert cover_asset_name("x", a) != cover_asset_name("x", b)

    def test_store_sostituisce_senza_lasciare_orfani(self, tmp_path,
                                                     monkeypatch):
        """Rigenerare non accumula file: la versione precedente dello
        stesso slug (e il vecchio `{slug}.webp` senza impronta) se ne
        va. Le copertine di ALTRI slug non si toccano, nemmeno quando
        il nome comincia allo stesso modo."""
        from services import object_storage
        from services.article_cover import (COVER_CATEGORY,
                                            cover_asset_name,
                                            store_article_cover)
        monkeypatch.setattr(object_storage, "_UPLOADS_ROOT", tmp_path)
        monkeypatch.setattr(object_storage, "is_s3_enabled", lambda: False)
        cartella = tmp_path / COVER_CATEGORY
        cartella.mkdir(parents=True)
        (cartella / "yoga.webp").write_bytes(b"vecchia senza impronta")
        vicino = cartella / "yoga-e-respiro-a1b2c3d4.webp"
        vicino.write_bytes(b"di un altro articolo")

        primo = store_article_cover("yoga", b"immagine-1")
        assert primo.endswith(cover_asset_name("yoga", b"immagine-1"))
        assert not (cartella / "yoga.webp").exists(), \
            "il file col nome vecchio resta li' come orfano"

        # idempotenza: stessi byte, stesso URL, un solo file
        assert store_article_cover("yoga", b"immagine-1") == primo
        secondo = store_article_cover("yoga", b"immagine-2")
        assert secondo != primo
        nostri = sorted(p.name for p in cartella.glob("yoga-*"))
        assert nostri == [cover_asset_name("yoga", b"immagine-2"),
                          "yoga-e-respiro-a1b2c3d4.webp"], nostri
        assert vicino.read_bytes() == b"di un altro articolo", \
            "il cleanup ha mangiato la copertina di un altro articolo"

    def test_il_router_non_scrive_piu_il_nome_fisso(self):
        src = (BACKEND_DIR / "routers" / "articles.py").read_text()
        assert 'f"{slug}.webp"' not in src, \
            "il router salva ancora con l'URL fisso: la cache non si accorge"
        assert "store_article_cover" in src

    def test_lo_script_tocca_solo_le_copertine_autogenerate(self):
        """La regola che non si tocca: una foto caricata a mano non si
        sostituisce mai."""
        src = (BACKEND_DIR / "scripts"
               / "sw4_regen_article_covers.py").read_text()
        assert "is_autogen_cover_url" in src
        assert "store_article_cover" in src
        # il campo giusto del documento, non un `cover_url` inventato
        assert '"featured_image_url": nuovo' in src
        from services.article_cover import is_autogen_cover_url
        assert is_autogen_cover_url("/uploads/article-covers/x-1234abcd.webp")
        assert not is_autogen_cover_url("/uploads/products/foto.jpg")
        assert not is_autogen_cover_url(None)

    # ── 2. la vetrina: copertina grande, testo sotto ─────────────────

    def _compact(self):
        """Il ramo della scheda della griglia: dal commento che lo apre
        alla fine del file."""
        src = self.CARD.read_text()
        return src[src.index("// compact —"):]

    def test_scheda_griglia_immagine_sopra_testo_sotto(self):
        blocco = self._compact()
        assert blocco.index("<Cover") < blocco.index("<Kicker") \
            < blocco.index("<h3"), \
            "nella scheda della griglia il testo non sta sotto l'immagine"
        assert "flex" not in blocco, \
            "la scheda della griglia e' tornata di fianco (flex)"
        assert "w-28" not in blocco and "w-32" not in blocco, \
            "la copertina della griglia e' di nuovo un francobollo"

    def test_rapporto_unico_e_niente_ritagli_inventati(self):
        """Un solo rapporto per tutte le copertine impilate, e vale
        40:21 = 1200x630: la misura esatta di quelle autogenerate,
        quindi il medaglione centrale non viene tagliato."""
        src = self.CARD.read_text()
        assert "const COVER = 'aspect-[40/21]'" in src
        assert src.count("aspect-[40/21]") == 1, \
            "il rapporto va detto una volta sola, nella costante"
        assert "aspect-[16/9]" not in src, \
            "un 16:9 ritaglia 40 px per lato e taglia la cornice incisa"
        # e il rapporto della cover generata e' davvero quello
        from services.article_cover import HEIGHT, WIDTH
        assert (WIDTH, HEIGHT) == (1200, 630)
        assert abs(WIDTH / HEIGHT - 40 / 21) < 1e-9

    def test_indice_meno_articoli_per_riga(self):
        src = self.INDEX.read_text()
        assert "sm:grid-cols-2" in src
        assert "lg:grid-cols-3" not in src, \
            "la griglia fitta di miniature e' tornata"
        assert "spalla" not in src, \
            "la colonna di miniature accanto all'apertura e' tornata"
        # l'impianto editoriale di SW4 resta
        for pezzo in ("blog.lead1", "blog.lead2",
                      # MG1 — i filtri sono usciti dalla pagina e vivono
                      # in MagazineCategoryNav: qui si controlla che la
                      # pagina li monti ancora, il resto lo verifica la
                      # guardia sul componente in test_listino_tw.
                      "<MagazineCategoryNav",
                      'data-testid="blog-empty"', 'data-testid="blog-card-gated"',
                      "'lead'", "'compact'"):
            assert pezzo in src, f"SW4 perso per strada: {pezzo}"

    def test_la_spalla_della_home_resta_di_fianco(self):
        """La variante orizzontale non sparisce: vive nella sezione
        della home, dove i secondari stanno accanto a un articolo
        grande. Se sparisse, la home mostrerebbe tre copertine in
        concorrenza."""
        card = self.CARD.read_text()
        assert "variant === 'aside'" in card
        home = (FRONTEND_SRC / "features" / "network"
                / "NetworkHomePage.js").read_text()
        assert 'variant="aside"' in home
        assert 'variant="compact"' not in home
