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
        for path in ("/esperienze", "/operatori", "/destinazioni"):
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
        assert CURRENT_VERSION_TAG == "v2.0"
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
