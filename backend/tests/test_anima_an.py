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
        """'In tutto il mondo' era falso: la tagline dice Italia, in
        entrambe le fonti di verita' (backend + i18n IT)."""
        from core.brand import BRAND_TAGLINE
        assert "Italia" in BRAND_TAGLINE["it"]
        assert "mondo" not in BRAND_TAGLINE["it"]
        landings = json.loads((FRONTEND_SRC / "locales" / "it" / "landings.json").read_text())
        assert "Italia" in landings["marketplace"]["tagline"]
        assert "mondo" not in landings["marketplace"]["tagline"]

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
        # e la home porta la promessa, non un title generico
        assert "marketplace italiano" in src

    def test_sitemap_includes_brand_pages(self):
        src = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert "/chi-siamo" in src
        assert "/come-funziona" in src
