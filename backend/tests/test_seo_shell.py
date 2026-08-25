"""S0.2 — SEO shell: HTML pubblico con meta server-side.

Contratto sotto guardia:
  1. l'iniezione sostituisce title/description e appende OG/canonical/
     JSON-LD prima di </head>;
  2. i resolver coprono home, categoria, evento, prodotti (5 tipi),
     operatore, store; path ignoti → None (shell neutra, mai 500);
  3. hreflang solo per le lingue davvero tradotte (description gate);
  4. og:image ha SEMPRE un fallback (logo Aurya);
  5. l'endpoint /__seo/... risponde 200 text/html anche su path ignoto.
"""

import os, sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest
import requests

from routers import seo_shell as shell

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")


class TestInject:
    TEMPLATE = ('<html><head><title>Old</title>'
                '<meta name="description" content="old"/></head>'
                '<body></body></html>')

    def test_replaces_title_and_description(self):
        out = shell._inject(self.TEMPLATE, {"title": "Nuovo & Bello",
                                            "description": "desc nuova"})
        assert "<title>Nuovo &amp; Bello</title>" in out
        assert 'content="desc nuova"' in out
        assert "Old" not in out and 'content="old"' not in out

    def test_appends_og_canonical_jsonld_before_head_close(self):
        out = shell._inject(self.TEMPLATE, {
            "title": "T", "description": "D",
            "canonical": "https://aurya.life/e/x/y",
            "image": "https://aurya.life/img.jpg",
            "jsonld": {"@type": "Event"},
            "hreflang": {"it": "https://aurya.life/e/x/y",
                         "de": "https://aurya.life/e/x/y?lang=de"},
        })
        head = out.split("</head>")[0]
        assert 'property="og:image"' in head
        assert 'rel="canonical"' in head
        assert 'hreflang="de"' in head
        assert 'application/ld+json' in head
        assert '"@type": "Event"' in head

    def test_noindex_flag(self):
        out = shell._inject(self.TEMPLATE, {"title": "T", "noindex": True})
        assert 'name="robots" content="noindex"' in out


class TestHreflang:
    def test_only_translated_languages(self):
        got = shell._hreflang_for(
            {"de": {"description": "Deutsch"}, "en": {"name": "solo nome"}},
            "https://aurya.life/e/a/b")
        assert "de" in got            # description tradotta → dentro
        assert "en" not in got        # solo il nome NON basta (gate)
        assert got["x-default"] == "https://aurya.life/e/a/b"


class TestAbsImage:
    def test_fallback_og_cover(self):
        # scelta 10/7: il fallback social è la og-cover 1200x630 (il logo
        # quadrato renderebbe male nelle anteprime di condivisione)
        assert shell._abs_image(None).endswith("/og-cover.jpg")

    def test_relative_becomes_absolute(self):
        got = shell._abs_image("/uploads/products/x.jpg")
        assert got.startswith("http") and got.endswith("/uploads/products/x.jpg")


class TestResolveRouting:
    @pytest.mark.asyncio
    async def test_home(self):
        meta = await shell.resolve_meta("/")
        assert meta["canonical"].endswith("/")
        # SEO6: la home serve WebSite + Organization (lista di blocchi)
        types = [b["@type"] for b in meta["jsonld"]]
        assert "WebSite" in types and "Organization" in types

    @pytest.mark.asyncio
    async def test_category(self):
        meta = await shell.resolve_meta("/ritiri/yoga/toscana")
        assert "Yoga" in meta["title"] and "Toscana" in meta["title"]
        assert meta["canonical"].endswith("/ritiri/yoga/toscana")

    @pytest.mark.asyncio
    async def test_unknown_path_is_none(self):
        assert await shell.resolve_meta("/qualcosa/di/strano") is None


class TestNetworkPhaseRT5:
    """RT5 (piano sito-rete) — la shell dice la verita' della fase:
    le rotte nuove sono note (mai 404 dai crawler), /operatori si
    indicizza in fase network.
    SW3 — /chi-siamo non migra piu' il canonical sul Manifesto: e'
    tornata una pagina propria e canonica di se stessa."""

    def test_brand_pages_include_network_routes(self):
        for slug in ("manifesto", "newsletter", "entra-nella-rete"):
            assert slug in shell._BRAND_PAGES, f"rotta rete assente: {slug}"

    @pytest.mark.asyncio
    async def test_chi_siamo_e_manifesto_canonici_di_se_stessi(self):
        """SW3 — due pagine, due canonical: il Manifesto e' la
        posizione, Chi siamo sono le persone."""
        meta = await shell._meta_brand_page("chi-siamo")
        assert meta["canonical"].endswith("/chi-siamo")
        assert "Chi siamo" in meta["title"]
        meta2 = await shell._meta_brand_page("manifesto")
        assert meta2["canonical"].endswith("/manifesto")

    @pytest.mark.asyncio
    async def test_operators_index_network_meta(self, monkeypatch):
        monkeypatch.setenv("SITE_PHASE", "network")
        meta = await shell._meta_operators_index()
        assert "rete" in meta["title"].lower()
        # le varianti /operatori/{cat} rendono la stessa landing:
        # canonical sulla radice
        meta_cat = await shell._meta_operators_index("yoga")
        assert meta_cat["canonical"].endswith("/operatori")

    def test_phase_noindex_spares_operatori(self):
        assert "operatori" not in shell._PHASE_NOINDEX_HEADS
        assert set(shell._PHASE_NOINDEX_HEADS) == {
            "ritiri", "destinazioni", "esperienze"}

    @pytest.mark.asyncio
    async def test_come_funziona_404_in_network_lc2(self, monkeypatch):
        """LC2 — /come-funziona racconta il percorso d'acquisto
        (caparra, prenotazione): in fase rete la pagina non esiste, la
        shell deve rispondere 404 vero (None), non offrire ai crawler
        le meta di un marketplace spento. In marketplace torna 200."""
        monkeypatch.setenv("SITE_PHASE", "network")
        assert await shell._meta_brand_page("come-funziona") is None
        monkeypatch.setenv("SITE_PHASE", "marketplace")
        meta = await shell._meta_brand_page("come-funziona")
        assert meta and meta["canonical"].endswith("/come-funziona")


class TestEndpointLive:
    """Contro il backend live (stesso pattern degli altri test API)."""

    def test_home_shell(self):
        r = requests.get(f"{BASE_URL}/__seo/", timeout=10)
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "og:title" in r.text and "canonical" in r.text

    def test_unknown_path_serves_neutral_shell(self):
        # SEO6 — 404 VERO sui path ignoti (niente soft-404), ma la shell
        # HTML viene servita comunque: la SPA mostra il suo 404.
        r = requests.get(f"{BASE_URL}/__seo/pagina/inesistente-xyz", timeout=10)
        assert r.status_code == 404
        assert "text/html" in r.headers["content-type"]
        assert "<html" in r.text.lower()

    def test_event_shell_has_event_jsonld(self):
        # slug del seed demo: se non esiste, il test resta significativo
        # sulla shell neutra (nessun 500)
        r = requests.get(
            f"{BASE_URL}/__seo/e/masseria-demo/ritiro-yoga-test-s1-2026-10-02",
            timeout=10)
        assert r.status_code == 200
        if '"@type": "Event"' in r.text:
            assert 'og:image' in r.text
            assert 'rel="canonical"' in r.text

    def test_event_shell_has_location_offers_and_no_emdash(self):
        """SEO1 — l'evento porta la LOCATION strutturata (PostalAddress +
        GeoCoordinates) e l'Offer col prezzo: è ciò che sblocca il rich
        result 'ritiro [città]'. Title senza em-dash, data leggibile."""
        r = requests.get(
            f"{BASE_URL}/__seo/e/masseria-demo/ritiro-yoga-test-s1-2026-10-02",
            timeout=10)
        assert r.status_code == 200
        if '"@type": "Event"' in r.text:
            import re, json
            m = re.search(r'application/ld\+json">(.*?)</script>', r.text, re.S)
            d = json.loads(m.group(1))
            loc = d.get("location", {})
            assert loc.get("address", {}).get("@type") == "PostalAddress"
            assert loc.get("geo", {}).get("@type") == "GeoCoordinates"
            assert d.get("offers", {}).get("@type") == "Offer"
            # regola brand: mai em-dash nel title pubblico
            title = re.search(r"<title>([^<]*)</title>", r.text).group(1)
            assert "—" not in title

    def test_operator_shell_is_localbusiness_geo_rated(self):
        """SEO1 — l'operatore è un LocalBusiness geo-taggato con stelle:
        la scheda che lo fa comparire su Google nella sua zona."""
        r = requests.get(f"{BASE_URL}/__seo/o/masseria-demo", timeout=10)
        assert r.status_code == 200
        if '"LocalBusiness"' in r.text:
            import re, json
            m = re.search(r'application/ld\+json">(.*?)</script>', r.text, re.S)
            d = json.loads(m.group(1))
            assert d.get("@type") == "LocalBusiness"
            assert d.get("geo", {}).get("@type") == "GeoCoordinates"
            assert d.get("address", {}).get("@type") == "PostalAddress"
            # aggregateRating solo se ci sono recensioni (seed demo ne ha 1)
            if d.get("aggregateRating"):
                assert d["aggregateRating"]["reviewCount"] >= 1
            title = re.search(r"<title>([^<]*)</title>", r.text).group(1)
            assert "—" not in title

    def test_event_has_breadcrumb(self):
        r = requests.get(
            f"{BASE_URL}/__seo/e/masseria-demo/ritiro-yoga-test-s1-2026-10-02",
            timeout=10)
        assert r.status_code == 200
        if '"@type": "Event"' in r.text:
            assert '"BreadcrumbList"' in r.text

    def test_category_itemlist_or_noindex(self):
        """SEO2 — categoria con ritiri prenotabili → ItemList + niente
        noindex; categoria vuota → noindex (thin content). PL22→RT5: a
        marketplace spento /ritiri/* e' SEMPRE noindex, il test si adatta
        alla fase del server live."""
        import re, json
        cfg = requests.get(f"{BASE_URL}/api/public/site-config", timeout=10).json()
        marketplace_off = cfg.get("site_phase", "marketplace") != "marketplace"
        pop = requests.get(f"{BASE_URL}/__seo/ritiri/yoga", timeout=10)
        assert pop.status_code == 200
        if marketplace_off:
            assert 'content="noindex"' in pop.text
        elif '"ItemList"' in pop.text:
            assert 'content="noindex"' not in pop.text
        # categoria del dominio quasi certamente vuota nel seed → noindex
        empty = requests.get(f"{BASE_URL}/__seo/ritiri/breathwork", timeout=10)
        assert empty.status_code == 200
        if '"ItemList"' not in empty.text:
            assert 'content="noindex"' in empty.text

    def test_destination_noindex_when_empty(self):
        r = requests.get(f"{BASE_URL}/__seo/destinazioni/citta-inesistente-xyz",
                         timeout=10)
        assert r.status_code == 200
        assert 'content="noindex"' in r.text

    def test_indexnow_pings_operator_update(self):
        """SEO2 — l'update del profilo/store pinga IndexNow di /o/ e /s/."""
        orgs = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert "_ping_operator_indexnow" in orgs
        assert '"/o/{slug}"' in orgs and '"/s/{slug}"' in orgs
        stores = (BACKEND_DIR / "routers" / "stores.py").read_text()
        assert "_ping_operator_indexnow" in stores


class TestSe1ContentInBody:
    """SE1 — il contenuto sta nell'HTML iniziale, non solo nel JS.

    Prima il body della shell era vuoto (108 byte, `<div id="root">`)
    e per i crawler senza rendering — Bing, GPTBot, ClaudeBot,
    PerplexityBot — gli articoli erano pagine vuote con buoni metadati.
    Queste guardie pretendono: l'articolo intero nel body (i riservati
    con la SOLA anteprima: niente cloaking), gli hub con i link veri,
    og:type article con i tempi, le date col fuso.
    """

    FREE_SLUG = "reiki-cose-come-funziona-una-sessione"
    GATED_SLUG = "kit-pratiche-quotidiane-15-minuti"

    @staticmethod
    def _visible_body(html_text: str) -> str:
        import re
        body = html_text.split("</head>", 1)[1]
        return re.sub(r"<script.*?</script>", "", body, flags=re.S)

    def test_free_article_body_has_full_content(self):
        import re
        r = requests.get(f"{BASE_URL}/__seo/blog/{self.FREE_SLUG}", timeout=10)
        assert r.status_code == 200
        visible = self._visible_body(r.text)
        words = len(re.sub(r"<[^>]+>", " ", visible).split())
        assert words > 800, f"articolo nel body: {words} parole, attese >800"
        assert "<h1>" in visible and "<h2>" in visible, \
            "la struttura dei titoli deve stare nell'HTML"
        assert 'href="/blog/' in visible, \
            "i link interni dell'articolo devono stare nell'HTML"

    def test_gated_article_body_is_preview_only(self):
        """BN3 — il crawler vede la STESSA anteprima dell'utente non
        iscritto: il corpo completo del riservato non deve uscire."""
        import re
        r = requests.get(f"{BASE_URL}/__seo/blog/{self.GATED_SLUG}", timeout=10)
        assert r.status_code == 200
        visible = self._visible_body(r.text)
        words = len(re.sub(r"<[^>]+>", " ", visible).split())
        assert 0 < words < 400, \
            f"riservato nel body: {words} parole visibili, attesa solo l'anteprima"

    def test_blog_hub_and_category_link_articles_in_body(self):
        import re
        hub = requests.get(f"{BASE_URL}/__seo/blog", timeout=10)
        assert hub.status_code == 200
        links = re.findall(r'href="[^"]*/blog/[a-z0-9-]+"',
                           self._visible_body(hub.text))
        assert len(links) >= 30, \
            f"hub /blog: {len(links)} articoli linkati nel body, attesi >=30"
        cat = requests.get(f"{BASE_URL}/__seo/blog/categoria/yoga", timeout=10)
        assert cat.status_code == 200
        cat_links = re.findall(r'href="[^"]*/blog/[a-z0-9-]+"',
                               self._visible_body(cat.text))
        assert len(cat_links) >= 1, "categoria: nessun articolo nel body"

    def test_article_og_type_and_times(self):
        r = requests.get(f"{BASE_URL}/__seo/blog/{self.FREE_SLUG}", timeout=10)
        assert 'og:type" content="article"' in r.text
        assert 'property="article:published_time"' in r.text
        # le date del JSON-LD dichiarano il fuso
        import re
        pub = re.search(r'"datePublished": "([^"]+)"', r.text)
        assert pub and ("+" in pub.group(1)[10:] or pub.group(1).endswith("Z")), \
            "datePublished senza timezone"
        # le pagine non-articolo restano website
        hub = requests.get(f"{BASE_URL}/__seo/blog", timeout=10)
        assert 'og:type" content="website"' in hub.text

    def test_markdown_renderer_subset_and_escape(self):
        """Unit del renderer: il sottoinsieme reale degli articoli
        (h2/h3, bold, corsivo, link whitelisted, liste, blockquote)
        e l'escape che non fa eccezioni."""
        from services.markdown_html import render_markdown
        out = render_markdown(
            "## Titolo\n\nUn **grasso** e un *corsivo* e un "
            "[link](/blog/x) e [fuori](https://esempio.it/a).\n\n"
            "- uno\n- due\n\n1. primo\n2) secondo\n\n> una citazione\n\n"
            "<script>alert(1)</script> resta testo")
        assert "<h2>Titolo</h2>" in out
        assert "<strong>grasso</strong>" in out and "<em>corsivo</em>" in out
        assert '<a href="/blog/x">link</a>' in out
        assert '<a href="https://esempio.it/a">fuori</a>' in out
        assert "<ul><li>uno</li><li>due</li></ul>" in out
        assert "<ol><li>primo</li><li>secondo</li></ol>" in out
        assert "<blockquote>" in out
        assert "<script>" not in out and "&lt;script&gt;" in out
        # javascript: non passa la whitelist dei link
        cattivo = render_markdown("[x](javascript:alert(1))")
        assert "<a " not in cattivo


class TestSbloccoIndicizzazioneGs:
    """GS (25/8/2026) — lo sblocco dell'indicizzazione, misurato in
    Search Console: 20 pagine indicizzate e SBAGLIATE (/inizia, /login,
    /termini, home col copy di luglio, una classificata inglese) mentre
    46 articoli su 47 aspettavano in coda. Tre cause, tre guardie:
    body vuoto sulle pagine d'ingresso, robots che bloccava il
    rendering, nessun modo di dire noindex alle rotte app.
    Piano: docs/SEO_SBLOCCO_E_SCALATA_2026-08.md."""

    @pytest.mark.asyncio
    async def test_la_home_parla_ai_crawler(self, monkeypatch):
        """GS1 — la pagina col piu' alto PageRank del sito diceva 46
        caratteri INGLESI. Ora: racconto del founder + link agli
        articoli. Se questo torna vuoto, Google riclassifica la home
        come pagina inglese senza contenuto — di nuovo."""
        monkeypatch.setenv("SITE_PHASE", "network")
        meta = await shell.resolve_meta("/")
        html = meta.get("content_html") or ""
        assert len(html) > 1500, "la home deve avere un corpo vero"
        assert "Il benessere inizia dalle persone." in html
        for porta in ('href="/blog"', 'href="/operatori"',
                      'href="/entra-nella-rete"', 'href="/newsletter"'):
            assert porta in html, f"manca la porta {porta}"

    def test_parita_copy_home_col_locale(self):
        """il copy della home vive in DUE posti (locale it = fonte,
        shell = copia per Docker): questa guardia e' il patto — se il
        founder cambia una parola nel locale, la shell deve seguirla."""
        import json
        locale = json.loads(
            (BACKEND_DIR.parent / "frontend" / "src" / "locales" / "it"
             / "landings.json").read_text())["nwHome"]
        for k, v in shell._HOME_COPY.items():
            assert k in locale, f"chiave {k} sparita dal locale"
            assert v == locale[k], (
                f"nwHome.{k}: la shell dice «{v[:40]}…» ma il locale "
                f"dice «{locale[k][:40]}…» — allineare la shell")

    @pytest.mark.asyncio
    async def test_le_rotte_app_sono_noindex(self, monkeypatch):
        """GS5 — /inizia e /login stavano nell'indice al posto degli
        articoli. La shell risponde 200+noindex; nginx DEVE mandarle
        alla shell (prima andavano al frontend statico, dove nessuno
        puo' dire noindex)."""
        monkeypatch.setenv("SITE_PHASE", "network")
        for rotta in ("/login", "/accedi", "/inizia", "/benvenuto",
                      "/account", "/termini", "/privacy"):
            meta = await shell.resolve_meta(rotta)
            assert meta and meta.get("noindex") is True, rotta
        nginx = (BACKEND_DIR.parent / "deploy" / "nginx"
                 / "nginx.conf").read_text()
        for nome in ("login", "accedi", "inizia", "benvenuto",
                     "account", "termini", "privacy"):
            assert nome in nginx, f"nginx non instrada /{nome} alla shell"

    def test_robots_apre_le_api_pubbliche(self):
        """GS6 — 'Disallow: /api/' bloccava le chiamate con cui le
        pagine non-SSR caricano i contenuti: il rendering di Google
        falliva PER MANO NOSTRA. L'Allow piu' lungo vince sul Disallow."""
        src = (BACKEND_DIR / "server.py").read_text()
        assert 'Allow: /api/public/\\n' in src
        # e le rotte noindex NON devono finire in Disallow: un crawler
        # che non puo' leggere la pagina non ne vede il noindex
        for rotta in ("login", "accedi", "inizia", "account"):
            assert f"Disallow: /{rotta}" not in src, rotta

    @pytest.mark.asyncio
    async def test_le_directory_esplora_sono_indicizzabili(self, monkeypatch):
        """ES (25/8) — /esplora-* nacquero come anteprime VIETATE ai
        crawler, perche' mostravano i CAMPIONI del pre-lancio (sei org
        senza proprietario, dieci ritiri inventati in localita' vere).
        Rimossi quelli, li' dentro c'e' solo roba vera e sono le uniche
        due directory della fase rete."""
        monkeypatch.setenv("SITE_PHASE", "network")
        for rotta in ("/esplora-operatori", "/esplora-ritiri"):
            meta = await shell.resolve_meta(rotta)
            assert meta, f"{rotta} non arriva alla shell"
            assert meta.get("content_html"), f"{rotta} servirebbe un body vuoto"
            assert meta.get("canonical"), rotta
        server = (BACKEND_DIR / "server.py").read_text()
        assert "Disallow: /esplora-" not in server, \
            "il Disallow e' tornato: le directory sparirebbero dagli indici"
        nginx = (BACKEND_DIR.parent / "deploy" / "nginx"
                 / "nginx.conf").read_text()
        assert "esplora-operatori" in nginx and "esplora-ritiri" in nginx, \
            "senza nginx quelle rotte tornano al frontend statico (body vuoto)"

    @pytest.mark.asyncio
    async def test_una_directory_vuota_non_si_indicizza_e_si_accende_da_sola(
            self, monkeypatch):
        """LA REGOLA CHE EVITA LAVORO FUTURO (richiesta founder):
        promettere ai crawler un calendario di ritiri che non esiste e'
        il rimbalzo garantito, ma nessuno deve ricordarsi di togliere
        il noindex il giorno del primo evento. Decide il DATO."""
        monkeypatch.setenv("SITE_PHASE", "network")
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        blocco = src.split("async def _meta_esplora_ritiri")[1].split("async def _meta_operator")[0]
        assert '"noindex": quanti == 0' in blocco, \
            "il vuoto deve decidersi dai dati, non da una costante"
        assert "listable_retreats" in blocco
        # e la sitemap segue la stessa regola
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert "esplora-ritiri" in seo and "listable_retreats" in seo

    def test_il_client_non_annulla_il_lavoro_della_shell(self):
        """LA TRAPPOLA PIU' SUBDOLA di tutto il ciclo: la shell serve
        meta perfetti, poi React monta e li RISCRIVE. Google legge il
        DOM renderizzato, quindi vince il client. Qui il client
        forzava `noindex: isPreview` sulle rotte esplora e puntava il
        canonical a /operatori e a / — due documenti diversi. Con
        quelle righe, tutto il server-side di questo ciclo sarebbe
        stato annullato al primo rendering, e in Search Console
        avremmo visto «pagina esclusa da noindex» senza capire
        perche'."""
        FE = BACKEND_DIR.parent / "frontend" / "src" / "features" / "storefront"
        ops = (FE / "OperatorsIndexPage.js").read_text()
        rit = (FE / "RetreatsCalendarPage.js").read_text()
        for nome, src in (("operatori", ops), ("ritiri", rit)):
            assert "noindex: isPreview," not in src, \
                f"{nome}: il client rimette noindex e annulla la shell"
            assert "isPreview || (!loading" not in src, nome
            assert "isPreview ? '/esplora-" in src, \
                f"{nome}: su esplora il canonico dev'essere se stessa"
        # e il vuoto resta governato dai dati, in entrambe
        assert "!loading && items.length === 0" in ops
        assert "!loading && (data?.items || []).length === 0" in rit

    def test_lo_script_dei_campioni_non_puo_toccare_i_veri(self):
        """La pulizia dei campioni gira su un database di PRODUZIONE
        dove vivono 4 professionisti veri. Le guardie dello script sono
        la differenza tra una pulizia e un disastro."""
        src = (BACKEND_DIR / "scripts"
               / "pulisci_campioni_prelancio.py").read_text()
        assert '{"is_sample": True}' in src, "deve selezionare SOLO i campioni"
        for guardia in ("orders_collection.count_documents",
                        "customers_collection.count_documents",
                        "users_collection.count_documents"):
            assert guardia in src, f"manca la guardia {guardia}"
        assert "sys.exit" in src, "senza uscita, le guardie sono decorative"
        assert "--prova" in src and "--esegui" in src

    @pytest.mark.asyncio
    async def test_nessuna_pagina_pubblica_resta_muta(self, monkeypatch):
        """ES2 (25/8) — trovate CENSENDO gli URL che rispondono 200:
        /meditazioni (linkata dal menu!) e /costi servivano ai crawler
        46 caratteri e il TITOLO MARKETPLACE di luglio, perche' nessuno
        le aveva messe nell'elenco delle rotte che passano dalla shell.
        Il difetto della home, in piccolo, su pagine che nessuno aveva
        pensato di controllare.

        LA REGOLA: una pagina pubblica o passa di qui, o e' muta. Se
        se ne aggiunge una, va aggiunta in TRE posti — shell, nginx,
        sitemap — e questa guardia li verifica tutti e tre."""
        monkeypatch.setenv("SITE_PHASE", "network")
        nginx = (BACKEND_DIR.parent / "deploy" / "nginx"
                 / "nginx.conf").read_text()
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        for rotta in ("meditazioni", "costi"):
            meta = await shell.resolve_meta(f"/{rotta}")
            assert meta and meta.get("content_html"), f"/{rotta} muta"
            assert "Ritiri ed esperienze olistiche" not in meta["title"], \
                f"/{rotta} serve ancora il titolo marketplace"
            assert rotta in nginx, f"nginx non instrada /{rotta}"
            assert rotta in seo, f"/{rotta} non e' in sitemap"

    def test_in_breve_arriva_a_tutte_le_superfici(self):
        """M1 (25/8) — MISURA: su quattro articoli presi a caso TRE
        aprono con una scena. E' la voce del brand e non si tocca — ma
        chi cerca «codice ateco operatore olistico» vuole il codice, e
        un motore generativo che cerca una frase da citare trova un
        preambolo. «In breve» sta SOPRA il racconto, e deve arrivare
        DOVUNQUE: se lo rende solo il client, i crawler senza JS (i
        motori AI, proprio quelli per cui esiste) non lo vedono."""
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert '"in_breve": 1' in shell, "la shell non lo legge nemmeno"
        assert "<h2>In breve</h2>" in shell, "non finisce nell'HTML servito"
        assert 'jsonld["abstract"]' in shell, "manca nei dati strutturati"
        server = (BACKEND_DIR / "server.py").read_text()
        assert "**In breve:**" in server, "manca in llms-full.txt"
        api = (BACKEND_DIR / "routers" / "articles.py").read_text()
        assert '"in_breve": doc.get("in_breve")' in api

    def test_in_breve_e_nei_tre_modelli(self):
        """Il file models/article.py lo dice da solo: un campo nuovo va
        aggiunto in ArticleCreate E in ArticleUpdate, o il PATCH lo
        scarta IN SILENZIO — la redazione scriverebbe l'In breve e al
        salvataggio sparirebbe, senza un errore."""
        src = (BACKEND_DIR / "models" / "article.py").read_text()
        assert src.count("in_breve") >= 3, \
            "in_breve manca in uno dei tre modelli (Create/Update/Article)"

    def test_una_guida_riservata_non_regala_il_riassunto(self):
        """Il cancello del cerchio vale anche per «In breve»: un
        riassunto completo in cima a una guida riservata sarebbe il
        cancello scavalcato dalla porta di servizio."""
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert "if breve and not gated:" in shell
        pagina = (BACKEND_DIR.parent / "frontend" / "src" / "features"
                  / "storefront" / "BlogArticlePage.js").read_text()
        assert "!article.gated && article.in_breve" in pagina

    def test_lo_script_in_breve_non_sovrascrive_il_lavoro_a_mano(self):
        """Le bozze sono TRATTE dagli articoli, ma la voce finale e'
        della redazione: rilanciare lo script dopo una revisione non
        deve cancellarla."""
        src = (BACKEND_DIR / "scripts" / "in_breve_articoli.py").read_text()
        assert 'if (doc.get("in_breve") or "").strip() and not args.sovrascrivi' in src
        assert "--prova" in src and "--esegui" in src

    def test_la_directory_non_e_orfana(self):
        """T7 (25/8) — /esplora-operatori era indicizzabile e con ZERO
        link interni: in SEO un documento senza voti dal proprio sito
        vale quanto un documento che non esiste. Ora la linkano la
        home, il racconto della rete e ogni profilo."""
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        # la home (blocco _home_content_html) e la pagina rete
        assert src.count('href="/esplora-operatori"') >= 3, \
            "la directory deve avere piu' di una porta interna"

    def test_i_profili_veri_sono_dichiarati_in_sitemap(self):
        """ES (25/8) — restavano fuori da ogni sitemap perche' il
        criterio era il solo flag editoriale `network_member` (0 su 13
        in produzione). Una pagina che il sito LINKA e non dichiara e'
        una pagina che chiediamo a Google di indovinare."""
        src = (BACKEND_DIR / "routers" / "seo.py").read_text()
        blocco = src.split("async def build_operators")[1][:2000]
        assert '"$or": [{"network_member": True}' in blocco
        assert '"is_sample": {"$ne": True}' in blocco, \
            "i campioni non devono poter rientrare dalla finestra"

    def test_media_e_font_non_pagano_un_giro_di_rete_ogni_volta(self):
        """T8 — solo /static/ era in cache: il video da 1,6 MB e ogni
        immagine uscivano con no-cache. Sette giorni e non un anno: i
        nomi non hanno l'hash, quindi `immutable` sarebbe una bugia."""
        conf = (BACKEND_DIR.parent / "frontend" / "nginx.conf").read_text()
        assert "mp4|webm" in conf and "woff2" in conf
        assert "max-age=604800" in conf
        assert "immutable" not in conf.split("location ~*")[1], \
            "immutable su nomi senza hash congela un file per un anno"

    def test_llms_full_esiste_e_rispetta_il_cancello(self):
        """T2 — llms.txt e' l'indice, llms-full.txt e' il TESTO: la
        porta dei motori generativi, che citano fonti oggi mentre le
        SERP classiche ci faranno aspettare mesi. Ma le guide
        riservate entrano con la sola anteprima: il cancello del
        cerchio vale per gli assistenti come per le persone."""
        src = (BACKEND_DIR / "server.py").read_text()
        assert '@app.get("/llms-full.txt"' in src
        corpo = src.split("async def llms_full_txt")[1][:3000]
        assert "gated_preview" in corpo, \
            "llms-full regalerebbe le guide riservate"
        assert '"published": True' in corpo, "solo articoli pubblicati"

    def test_gli_articoli_si_linkano_tra_loro(self):
        """T5 — MISURATO: l'articolo sul Reiki linkava 2 pezzi su 47.
        Un Magazine senza rete interna e' 47 pagine sole. La rete si
        costruisce dai DATI (stesso argomento, i piu' recenti), non
        chiedendo alla redazione di infilare link a mano in 47 testi."""
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        blocco = src.split("T5 (25/8)")[1][:1800]
        assert "Continua a leggere" in blocco
        assert '"category": doc.get("category")' in blocco, \
            "i correlati devono venire dallo stesso argomento"
        assert '"slug": {"$ne": slug}' in blocco, "un articolo non si autolinkia"

    def test_il_primo_istante_e_vestito(self):
        """FP (26/8) — founder: «per un momento vedo una schermata
        bianca piena di testi, poi il sito si compone». Il contenuto
        server-side era HTML nudo fino al montaggio dell'app.
        Nasconderlo = cloaking; la cura e' vestirlo: stile minimo
        INCORPORATO (zero richieste extra) con la palette del brand.
        Se questo salta, il primo istante torna anni novanta."""
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert "_SSR_STILE" in src
        assert 'class="ssrp"' in src, "il contenuto SSR non ha il vestito"
        assert "background:#f6f3ec" in src, "manca il fondo crema del brand"
        assert "content:'AURYA'" in src, "manca il marchio nel primo istante"
        # lo stile viaggia DENTRO la risposta: mai un file esterno, che
        # arriverebbe dopo il testo e riporterebbe il lampo
        assert '<link' not in src.split("_SSR_STILE = (")[1][:900]

    def test_nginx_comprime_cio_che_vale_la_pena(self):
        """T1 (25/8) — MISURATO in produzione: main.js usciva a
        2.045.088 byte NON compressi anche chiedendo gzip, perche' la
        conf non aveva UNA sola direttiva. ~1,5 MB di troppo su ogni
        prima visita: LCP e budget di rendering, proprio su un sito
        che al crawler chiede di eseguire JS."""
        conf = (BACKEND_DIR.parent / "deploy" / "nginx"
                / "nginx.conf").read_text()
        assert "gzip on;" in conf
        assert "gzip_vary on;" in conf, "senza Vary le cache servono il file sbagliato"
        for tipo in ("application/javascript", "text/css", "application/json",
                     "image/svg+xml", "application/xml"):
            assert tipo in conf, f"{tipo} resta non compresso"
        # i formati gia' compressi NON si ricomprimono
        for gia in ("image/webp", "video/mp4", "font/woff2"):
            assert gia not in conf.split("gzip_types")[1].split(";")[0], gia

    def test_hreflang_onesti_in_fase_rete(self, monkeypatch):
        """GS4 — dichiarare ?lang=en su contenuto italiano confonde la
        classificazione di lingua, che e' esattamente cio' che ci
        tradiva («Traduci questa pagina» in SERP)."""
        monkeypatch.setenv("SITE_PHASE", "network")
        alt = shell._hub_hreflang("https://aurya.life/")
        assert set(alt) == {"it", "x-default"}
        monkeypatch.setenv("SITE_PHASE", "marketplace")
        alt = shell._hub_hreflang("https://aurya.life/")
        assert set(alt) == {"it", "x-default", "en", "de", "fr"}

    def test_privacy_termini_fuori_dalla_sitemap(self):
        """GS5 — noindex + presenza in sitemap sono segnali in
        conflitto: le pagine legali escono dalla core."""
        src = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert '/privacy"' not in src.replace("privacy-", ""), \
            "privacy e' tornata in sitemap con il noindex addosso"
        assert '/termini"' not in src

    @pytest.mark.asyncio
    async def test_il_profilo_del_professionista_parla(self, monkeypatch):
        """GS7 — misurato in PRODUZIONE: i profili veri rispondevano
        200 con meta e JSON-LD perfetti e un body di 46 caratteri.
        Sono le pagine che nessun elenco puo' replicare, ed erano anche
        il bersaglio del volano-backlink: chi linkava il proprio
        profilo mandava i crawler su una pagina muta."""
        monkeypatch.setenv("SITE_PHASE", "network")
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        corpo = src.split("GS7 (25/8)")[1][:2200]
        # il testo VERO del profilo, non un riassunto generato
        for campo in ("tagline", "bio", "disciplines"):
            assert campo in corpo, f"il corpo del profilo ignora {campo}"
        assert '"content_html": "".join(pezzi)' in corpo, \
            "il corpo costruito non viene consegnato alla shell"
        assert "_html.escape(name)" in corpo, "nome non escapato"

    @pytest.mark.asyncio
    async def test_operatori_e_brand_hanno_un_corpo(self, monkeypatch):
        """GS2/GS3 — anche /operatori e le pagine di brand erano 46
        caratteri inglesi: ora un corpo italiano con h1 e link."""
        monkeypatch.setenv("SITE_PHASE", "network")
        ops = await shell.resolve_meta("/operatori")
        assert "<h1>La rete Aurya</h1>" in (ops.get("content_html") or "")
        assert 'href="/entra-nella-rete"' in ops["content_html"]
        man = await shell.resolve_meta("/manifesto")
        assert "<h1>" in (man.get("content_html") or "")
        assert 'href="/blog"' in man["content_html"]
