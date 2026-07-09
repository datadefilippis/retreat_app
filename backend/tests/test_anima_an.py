"""Ciclo AN — L'Anima di Aurya (docs/ANIMA_AURYA_FRONTEND_PIANO_2026-07-07.md).

AN1: il brand smette di essere invisibile — la home racconta cos'è
Aurya, esistono /chi-siamo e /come-funziona, i meta portano la
promessa, la tagline è onesta (Italia, non "tutto il mondo").
"""

import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

LANGS = ("it", "en", "de", "fr")


class TestBrandFoundationsAn1:

    def test_brand_doc_exists_with_pillars(self):
        doc = (BACKEND_DIR.parent / "docs" / "BRAND_AURYA.md").read_text()
        for pillar in ("Missione", "Visione", "promessa", "Tono di voce"):
            assert pillar in doc, f"pilastro '{pillar}' mancante nel brand doc"

    def test_tagline_is_honest_everywhere(self):
        """RB4 — la tagline non impone geografie (si parte da Italia e
        Svizzera ma la visione e' internazionale) e non ha trattini."""
        from core.brand import BRAND_TAGLINE
        for lang, tagline in BRAND_TAGLINE.items():
            assert "Itali" not in tagline, f"{lang}: geografia nella tagline"
            assert "mondo" not in tagline
            assert "—" not in tagline
        landings = json.loads((FRONTEND_SRC / "locales" / "it" / "landings.json").read_text())
        assert "Itali" not in landings["marketplace"]["tagline"]

    def test_home_mounts_value_sections(self):
        """La home racconta l'anima: come funziona / perche' Aurya /
        CTA organizzatori — ma solo senza filtri attivi."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "RetreatsCalendarPage.js").read_text()
        assert "MarketplaceValueSections" in page
        assert "!anyFilter" in page
        comp = (FRONTEND_SRC / "features" / "storefront" / "components"
                / "MarketplaceValueSections.jsx").read_text()
        for key in ("brandHome.howTitle", "brandHome.whyTitle",
                    "brandHome.orgTitle"):
            assert key in comp

    def test_brand_pages_routed_and_linked(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert '"/chi-siamo"' in app
        assert '"/come-funziona"' in app
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        assert '"/chi-siamo"' in shell
        assert '"/come-funziona"' in shell

    def test_how_page_has_faq_jsonld(self):
        """Le FAQ di fiducia (caparra, recensioni, Passaporto) vanno
        anche in SERP: FAQPage schema sulla pagina."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "HowItWorksPage.js").read_text()
        assert "FAQPage" in page
        assert "howPage.${f}q" in page      # template literal sulle 4 FAQ
        assert "'faq1', 'faq2', 'faq3', 'faq4'" in page

    def test_brand_copy_in_four_languages(self):
        """brandHome / aboutPage / howPage: parita' chiave per chiave
        nelle 4 lingue — mai piu' sezioni solo-italiane."""
        blocks = {}
        for lang in LANGS:
            data = json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            blocks[lang] = data
            for section in ("brandHome", "aboutPage", "howPage"):
                assert section in data, f"{lang}: sezione {section} mancante"
        base_keys = {s: set(blocks["it"][s]) for s in
                     ("brandHome", "aboutPage", "howPage")}
        for lang in ("en", "de", "fr"):
            for section, keys in base_keys.items():
                missing = keys - set(blocks[lang][section])
                assert not missing, f"{lang}.{section}: mancano {sorted(missing)}"

    def test_seo_shell_serves_brand_pages(self):
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert "_BRAND_PAGES" in src
        assert '"chi-siamo"' in src and '"come-funziona"' in src
        # e la home porta la promessa, non un title generico ne' geografie
        assert "che fanno crescere" in src
        assert "marketplace italiano" not in src

    def test_sitemap_includes_brand_pages(self):
        src = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert "/chi-siamo" in src
        assert "/come-funziona" in src


class TestUnifiedNavAn2:
    """AN2 — un solo menu su tutte le superfici pubbliche: gli
    aggregatori smettono di essere scopribili solo dal footer, il
    mobile non perde ricerca/CTA, dallo store si torna sempre."""

    SHELL = (FRONTEND_SRC / "features" / "storefront" / "components"
             / "MarketplaceShell.jsx").read_text()

    def test_main_nav_single_definition(self):
        """NAV_ITEMS è LA definizione: desktop e mobile la condividono
        (chi aggiunge una superficie la aggiunge in un posto solo)."""
        assert "NAV_ITEMS" in self.SHELL
        assert self.SHELL.count("NAV_ITEMS.map") == 2   # desktop + mobile
        for path in ("/operatori", "/destinazioni"):
            assert f"to: '{path}'" in self.SHELL

    def test_mobile_menu_keeps_organizer_cta(self):
        """Il CTA organizzatori su mobile spariva dall'header: ora
        vive nel pannello hamburger."""
        assert "mobileNavOpen" in self.SHELL
        panel = self.SHELL.split("pannello mobile")[1]
        assert '"/inizia"' in panel
        assert '"/chi-siamo"' in panel

    def test_footer_links_seo_paths_not_query(self):
        """I link categoria del footer puntano ai PATH (/ritiri/yoga),
        non alla query — i crawler seguono i link, non i filtri."""
        assert '"/ritiri/yoga"' in self.SHELL
        assert "/ritiri?categoria=" not in self.SHELL

    def test_store_header_bridges_back_to_marketplace(self):
        """Dentro uno store il visitatore non è più intrappolato:
        c'è la via di ritorno discreta al marketplace."""
        header = (FRONTEND_SRC / "features" / "storefront" / "components"
                  / "StorefrontHeader.js").read_text()
        assert "partOfAurya" in header
        assert 'to="/"' in header

    def test_part_of_aurya_in_four_languages(self):
        for lang in LANGS:
            data = json.loads((FRONTEND_SRC / "locales" / lang
                               / "storefront.json").read_text())
            assert data.get("partOfAurya"), f"{lang}: partOfAurya mancante"
        # e le voci del menu x4
        for lang in LANGS:
            mp = json.loads((FRONTEND_SRC / "locales" / lang
                             / "landings.json").read_text())["marketplace"]
            for key in ("navRetreats", "navExperiences", "navOperators",
                        "navDestinations", "navMenu"):
                assert mp.get(key), f"{lang}: marketplace.{key} mancante"


class TestOperatorGeoAn3:
    """AN3 — la scoperta geografica degli operatori vive sul PROFILO,
    non sui ritiri futuri: coordinate configurabili, geocoding
    best-effort, /operatori con raggio e mappa."""

    ORG_SRC = (BACKEND_DIR / "routers" / "organizations.py").read_text()
    PUB_SRC = (BACKEND_DIR / "routers" / "public.py").read_text()

    def test_profile_accepts_validated_coordinates(self):
        """lat/lng dal form vengono validati e trasformati in GeoJSON
        per l'indice 2dsphere."""
        assert '"public_profile.latitude"' in self.ORG_SRC
        assert '"public_profile.geo"' in self.ORG_SRC
        assert "-90 <= lat_f <= 90" in self.ORG_SRC

    def test_geocoding_is_best_effort(self):
        """City senza coordinate → geocoding con la stessa cache
        Nominatim; MAI bloccante per il salvataggio del profilo."""
        idx = self.ORG_SRC.index("_geocode_profile_if_needed")
        block = self.ORG_SRC[idx:idx + 2000]
        assert "from services.geocoding import geocode" in block
        assert "except Exception" in block

    def test_org_geo_index_exists(self):
        src = (BACKEND_DIR / "database.py").read_text()
        assert '"public_profile.geo"' in src
        assert "an3_org_geo" in src

    def test_operators_endpoint_has_geo_filters(self):
        """lat/lng/radius + location: la posizione viene dal profilo,
        l'operatore senza ritiri futuri resta scopribile."""
        idx = self.PUB_SRC.index("public_operators_index")
        block = self.PUB_SRC[idx:idx + 6000]
        for marker in ("radius_km", '"latitude": pp.get("latitude")',
                       "distance_km", "prof_regions"):
            assert marker in block, f"manca {marker}"

    def test_operators_page_wired_with_geo_and_map(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorsIndexPage.js").read_text()
        assert "GeoSearchBar" in page
        assert "OperatorsMapView" in page
        assert "radius_km" in page
        comp = (FRONTEND_SRC / "features" / "storefront" / "components"
                / "OperatorsMapView.jsx").read_text()
        assert "/o/${op.org_slug}" in comp or "/o/" in comp

    def test_profile_editor_has_location_autocomplete(self):
        editor = (FRONTEND_SRC / "features" / "settings"
                  / "PublicProfilePage.js").read_text()
        assert "LocationAutocomplete" in editor
        assert "/public/geo/search" in editor
        assert "payload.latitude" in editor

    def test_backfill_script_respects_nominatim(self):
        src = (BACKEND_DIR / "scripts" / "backfill_org_geo.py").read_text()
        assert "--dry-run" in src
        assert "asyncio.sleep(1.1)" in src   # policy OSM 1 req/s


class TestLegalAn4:
    """AN4 — il legal racconta il business VERO: Aurya marketplace,
    caparre, fee, Passaporto, recensioni. Zero AFianco. Versione
    consensi v2.0 con hash che DEVE combaciare coi file."""

    LEGAL_DIR = BACKEND_DIR / "legal"

    def test_no_afianco_in_legal_bundle(self):
        """Le 12 superfici legal (privacy+terms+DPA x4 lingue) non
        contengono più il vecchio brand."""
        for doc in ("privacy", "terms", "dpa"):
            for lang in LANGS:
                text = (self.LEGAL_DIR / f"{doc}_{lang}.md").read_text().lower()
                assert "afianco" not in text, f"{doc}_{lang}.md: AFianco residuo"

    def test_legal_describes_the_real_business(self):
        """I contenuti IT (vincolanti) parlano del marketplace: caparra,
        commissione, Stripe, Passaporto, recensioni."""
        privacy = (self.LEGAL_DIR / "privacy_it.md").read_text().lower()
        terms = (self.LEGAL_DIR / "terms_it.md").read_text().lower()
        for token in ("aurya", "caparr", "stripe"):
            assert token in privacy, f"privacy_it: manca '{token}'"
        for token in ("aurya", "caparr", "commission", "passaporto",
                      "recension"):
            assert token in terms, f"terms_it: manca '{token}'"
        # e il vecchio prodotto non c'è più
        assert "business intelligence" not in privacy
        assert "business intelligence" not in terms

    def test_consent_version_bumped_and_hash_matches_files(self):
        """v2.0 e hash RICALCOLATO dal bundle IT: se qualcuno cambia i
        testi senza bumpare, questa guardia diventa rossa."""
        import hashlib
        from core.legal_versions import (CURRENT_VERSION_TAG,
                                         CURRENT_VERSION_HASH)
        assert CURRENT_VERSION_TAG == "v2.1"
        priv = (self.LEGAL_DIR / "privacy_it.md").read_text("utf-8")
        terms = (self.LEGAL_DIR / "terms_it.md").read_text("utf-8")
        expected = hashlib.sha256(
            (priv + "\n\n--- TERMS BUNDLE ---\n\n" + terms).encode()
        ).hexdigest()[:16]
        assert CURRENT_VERSION_HASH == expected, (
            f"hash consensi {CURRENT_VERSION_HASH} != bundle {expected}: "
            "testi cambiati senza ricomputare l'hash")

    def test_legal_pages_show_aurya_not_afianco(self):
        for rel in ("pages/PrivacyPolicyPage.js",
                    "pages/TermsOfServicePage.js"):
            src = (FRONTEND_SRC / rel).read_text()
            assert "AFianco" not in src
            assert "afianco.ch" not in src
            assert "Aurya" in src

    def test_operator_signup_has_granular_consent(self):
        """Due checkbox distinte (art. 7 GDPR), submit bloccato finché
        entrambe non sono vere — come già fa il signup cliente."""
        src = (FRONTEND_SRC / "pages" / "AuthPages.js").read_text()
        assert "signup-privacy-checkbox" in src
        assert "signup-terms-checkbox" in src
        assert "!acceptedTerms || !acceptedPrivacy" in src


class TestTrustAn7:
    """AN7 — trust in vetrina: il rating verificato compare dove si
    sceglie (card directory, hero landing), le recensioni parlano
    dentro la landing, le domande che frenano una prenotazione hanno
    risposta prima del checkout, il Passaporto ha un nome in vetrina."""

    def test_public_listing_carries_org_rating(self):
        """/public/retreats espone org_rating {avg, count} costruito da
        reviews_stats, e la landing evento ha il campo nel modello."""
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        assert '"reviews_stats": 1' in src
        assert '"org_rating"' in src
        assert "org_rating: Optional[Dict[str, Any]]" in src

    def test_directory_card_shows_rating(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "RetreatsCalendarPage.js").read_text()
        assert "item.org_rating" in page

    def test_landing_hero_rating_and_reviews_section(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "EventLandingPage.js").read_text()
        assert "landing-org-rating" in page
        assert "ReviewsSnippet" in page
        assert "/public/reviews/" in page          # fetch delle voci vere
        assert "verifiedBadge" in page

    def test_landing_has_booking_faq(self):
        """Il box FAQ vive nella colonna prenotazione e risponde su
        caparra, dopo-prenotazione e contatto con chi organizza."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "EventLandingPage.js").read_text()
        assert "booking-faq" in page
        for key in ("faqDepositQ", "faqAfterQ", "faqWhoQ"):
            assert key in page

    def test_an7_i18n_keys_in_all_langs(self):
        needed_event = ("verifiedReviews_one", "verifiedReviews_other",
                        "reviewsHeading", "verifiedBadge",
                        "faqHeading", "faqDepositQ", "faqDepositA",
                        "faqAfterQ", "faqAfterA", "faqWhoQ", "faqWhoA")
        for lang in LANGS:
            data = json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            for key in needed_event:
                assert key in data["event"], f"{lang}: event.{key} mancante"
            assert "passportLink" in data["marketplace"], f"{lang}: passportLink"

    def test_passport_promoted_in_footer(self):
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        assert "passportLink" in shell


class TestDsBrandGlow:
    """DS (7/7/2026) — il tramonto di Aurya nell'hero e il filo d'oro
    su tutto il frontend pubblico: gli asset devono esistere e restare
    leggeri, il video deve rispettare prefers-reduced-motion."""

    def test_hero_video_assets_exist_and_light(self):
        pub = FRONTEND_SRC.parent / "public" / "media"
        video = pub / "aurya-hero.mp4"
        poster = pub / "aurya-hero-poster.jpg"
        assert video.exists() and poster.exists()
        # sottofondo, non cinema: mai oltre i 3MB
        assert video.stat().st_size < 3_000_000
        assert poster.stat().st_size < 200_000

    def test_home_hero_uses_video_with_scrim(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "RetreatsCalendarPage.js").read_text()
        assert "aurya-hero.mp4" in page
        assert "aurya-hero-poster.jpg" in page       # fallback sempre sotto
        assert "hero-video" in page                  # gate reduced-motion
        assert "text-hero-shadow" in page            # leggibilita' sul tramonto

    def test_design_utilities_exist(self):
        css = (FRONTEND_SRC / "index.css").read_text()
        for util in (".eyebrow", ".gold-rule", ".card-lift", ".aura-corner",
                     ".text-hero-shadow"):
            assert util in css, f"{util} mancante in index.css"
        # il video si spegne per chi preferisce meno movimento
        assert "prefers-reduced-motion" in css

    def test_footer_is_dark_brand(self):
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        idx = shell.index("<footer")
        footer = shell[idx:idx + 400]
        assert "bg-gradient-sidebar" in footer
        assert "gold-rule" in footer

    def test_home_og_image_is_sunset(self):
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert "aurya-hero-poster.jpg" in src


class TestDs2Polish:
    """DS2 (feedback founder 7/7 sera) — niente emoji nel marketplace
    (icone lucide), motto in evidenza, destinazioni oneste (i conteggi
    contano SOLO ciò che la lista mostra), firma logo+wordmark e
    geometria sacra per categoria nelle cover del blog."""

    _NO_EMOJI_FILES = (
        "features/storefront/RetreatsCalendarPage.js",
        "features/storefront/OperatorsIndexPage.js",
        "features/storefront/ExperiencesPage.js",
        "features/storefront/EventLandingPage.js",
        "features/storefront/BlogIndexPage.js",
        "features/storefront/components/MarketplaceShell.jsx",
        "features/storefront/components/GeoSearchBar.jsx",
        "features/storefront/components/StoreHome.jsx",
    )

    def test_no_emoji_in_marketplace_surfaces(self):
        import re
        emoji = re.compile(r"[\U0001F300-\U0001FAFF]")
        for rel in self._NO_EMOJI_FILES:
            src = (FRONTEND_SRC / rel).read_text()
            hits = emoji.findall(src)
            assert not hits, f"{rel}: emoji residue {hits[:3]}"

    def test_shared_category_icons_module(self):
        mod = (FRONTEND_SRC / "features" / "storefront" / "lib"
               / "categoryIcons.js").read_text()
        assert "lucide-react" in mod
        from models.retreat_taxonomy import RETREAT_CATEGORIES
        for slug in RETREAT_CATEGORIES:
            assert f"{slug}:" in mod, f"categoria {slug} senza icona"

    def test_motto_is_prominent_in_hero(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "RetreatsCalendarPage.js").read_text()
        idx = page.index("Connect · Heal · Grow")
        block = page[max(0, idx - 600):idx]
        # non più micro-etichetta: almeno text-base, con i fili d'oro
        assert "text-base" in block and "md:text-2xl" in block

    def test_destinations_promise_only_listable(self):
        """I conteggi di /public/destinations applicano lo STESSO gate
        GT1b del calendario: direct + org pubblica + pagamenti pronti."""
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        idx = src.index("async def public_destinations_index")
        body = src[idx:idx + 3000]
        assert '"transaction_mode": "direct"' in body
        assert "pay_ready" in body
        assert "listable_products" in body

    def test_cover_has_brand_signature_and_geometry(self):
        from models.retreat_taxonomy import RETREAT_CATEGORIES
        from services.article_cover import CATEGORY_GEOMETRY, _LOGO_PATH
        assert set(CATEGORY_GEOMETRY) == set(RETREAT_CATEGORIES)
        assert _LOGO_PATH.exists()          # la firma loto+sole viaggia col repo
        src = (BACKEND_DIR / "services" / "article_cover.py").read_text()
        assert "A U R Y A" in src           # wordmark in Cinzel oro


class TestDs3EsperienzeOut:
    """DS3 (decisione founder 7/7) — /esperienze fuori dal pubblico per
    ora: niente menu, footer, sitemap né SEO shell. La pagina resta nel
    repo pronta a tornare; il vecchio URL redirige alla home."""

    def test_esperienze_not_in_nav_or_footer(self):
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        assert "'/esperienze'" not in shell
        assert '"/esperienze"' not in shell

    def test_esperienze_route_redirects(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert "ExperiencesPage" not in app          # niente route attiva
        assert '"/esperienze/*"' in app              # redirect esplicito

    def test_esperienze_out_of_seo(self):
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert 'f"{base}/esperienze"' not in seo
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert 'head == "esperienze"' not in shell


class TestPlaceFilterCoherence:
    """Fix definitivo bug destinazioni (founder 7/7): l'indice promette
    anche CITTÀ, quindi il filtro ?region= della directory è un filtro
    LUOGO (region O city, case-insensitive). Contare una città e poi
    non trovarla al click non deve più poter succedere."""

    def test_region_param_matches_city_too(self):
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        idx = src.index('occ_query["$or"]')
        block = src[idx - 500:idx + 200]
        assert '{"region": _place}' in block
        assert '{"city": _place}' in block
        assert '"$options": "i"' in block           # slug minuscoli dai link

    def test_destinations_page_filter_case_insensitive(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "DestinationsPage.js").read_text()
        assert ".toLowerCase()" in page


    def test_one_destination_per_occurrence(self):
        """Città E regione dello stesso ritiro = doppione fuorviante
        (founder 7/7): ogni occorrenza contribuisce a UNA destinazione,
        la città se c'è, la regione altrimenti. Stessa regola nel
        sitemap (build_core)."""
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        idx = src.index("async def public_destinations_index")
        body = src[idx:idx + 4000]
        assert 'o.get("city") or o.get("region")' in body
        assert '{o.get("region"), o.get("city")}' not in body
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert '{o.get("region"), o.get("city")}' not in seo


class TestDs5IconsAndLang:
    """DS5 (founder 8/7) — icone categoria COLORATE (contrasto e
    riconoscibilità, mai emoji) e lingue ridotte a un globo con menu."""

    def test_category_icons_are_colored(self):
        import re
        mod = (FRONTEND_SRC / "features" / "storefront" / "lib"
               / "categoryIcons.js").read_text()
        from models.retreat_taxonomy import RETREAT_CATEGORIES
        for slug in RETREAT_CATEGORIES:
            assert f"{slug}:" in mod, f"categoria {slug} senza icona"
        # ogni voce porta il suo colore: [Icona, '#rrggbb']
        assert len(re.findall(r"#[0-9a-f]{6}", mod)) >= len(RETREAT_CATEGORIES)
        assert "colored" in mod                     # opt-out esplicito

    def test_lang_switcher_is_dropdown(self):
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        assert 'role="listbox"' in shell            # menu a tendina
        assert "Globe" in shell                     # icona globo
        assert "persistMarketplaceLang" in shell    # L1 resta: scelta persistita


class TestSeo3OnPage:
    """SEO3 (piano SEO Tier 3) — on-page: alt descrittivi, <html lang>
    dinamico (mai 'en' fisso), internal linking alle pagine local."""

    def test_html_lang_is_italian_not_english(self):
        html = (FRONTEND_SRC.parent / "public" / "index.html").read_text()
        assert '<html lang="it">' in html
        assert '<html lang="en">' not in html
        i18n = (FRONTEND_SRC / "i18n.js").read_text()
        assert "documentElement.lang" in i18n
        assert "languageChanged" in i18n

    def test_descriptive_alt_text(self):
        op = (FRONTEND_SRC / "features" / "storefront"
              / "OperatorProfilePage.js").read_text()
        assert 'alt=""' not in op or "aria-hidden" in op  # solo decorative
        assert "Logo di" in op                            # logo descrittivo
        ev = (FRONTEND_SRC / "features" / "storefront"
              / "EventLandingPage.js").read_text()
        assert "foto ${" in ev                            # gallery numerata

    def test_category_page_links_regions(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "RetreatsCalendarPage.js").read_text()
        assert "regionsForCategory" in page
        assert "/ritiri/${category}/${rg}" in page        # link crawlabile
        assert 'aria-label="breadcrumb"' in page
        # niente em-dash né 'in Italia' nel title/description SEO
        assert "— prenota online" not in page
        assert "' in Italia'" not in page

    def test_blog_article_links_category_retreats(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "BlogArticlePage.js").read_text()
        assert "/ritiri/${article.category}" in page
        assert "exploreRetreatsCta" in page


class TestOperatorProfileMultilang:
    """OP2 — il profilo operatore parla le lingue come i prodotti:
    traduzioni manuali bio/tagline, serving onesto per lingua, hreflang
    solo dove il contenuto esiste, mobile con la carta sopra la bio."""

    def test_patch_whitelists_translations(self):
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert '"translations" in body' in src
        # solo en/de/fr, solo bio/tagline, clip alle stesse lunghezze
        assert '("bio", 600), ("tagline", 80)' in src

    def test_public_endpoint_serves_language(self):
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        idx = src.index("async def public_operator_profile")
        body = src[idx:idx + 3500]
        assert "lang: Optional[str]" in body
        assert '_tr.get("bio")' in body
        assert '"served_lang"' in body
        assert '"profile_langs"' in body

    def test_shell_hreflang_only_translated(self):
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        idx = src.index("async def _meta_operator")
        body = src[idx:idx + 4000]
        assert '(_f or {}).get("bio")' in body    # gate: bio tradotta
        assert '"x-default"' in body

    def test_editor_has_multilang_section(self):
        page = (FRONTEND_SRC / "features" / "settings"
                / "PublicProfilePage.js").read_text()
        assert "MultiLangSection" in page
        assert "payload.translations" in page
        assert "mergeTr" in page

    def test_profile_page_refetches_on_language(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorProfilePage.js").read_text()
        assert "[org_slug, uiLang]" in page        # deps: refetch al cambio
        assert "{ lang: uiLang }" in page

    def test_mobile_card_above_description(self):
        """OP1 — su mobile la carta d'identità sale sotto la copertina
        (order-1) e i contenuti scendono (order-2); desktop invariato."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorProfilePage.js").read_text()
        assert "order-2 lg:order-1" in page        # contenuti
        assert "order-1 lg:order-2" in page        # carta d'identità
