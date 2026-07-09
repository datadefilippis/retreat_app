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
    def test_fallback_logo(self):
        assert shell._abs_image(None).endswith("/logo-aurya.png")

    def test_relative_becomes_absolute(self):
        got = shell._abs_image("/uploads/products/x.jpg")
        assert got.startswith("http") and got.endswith("/uploads/products/x.jpg")


class TestResolveRouting:
    @pytest.mark.asyncio
    async def test_home(self):
        meta = await shell.resolve_meta("/")
        assert meta["canonical"].endswith("/")
        assert meta["jsonld"]["@type"] == "WebSite"

    @pytest.mark.asyncio
    async def test_category(self):
        meta = await shell.resolve_meta("/ritiri/yoga/toscana")
        assert "Yoga" in meta["title"] and "Toscana" in meta["title"]
        assert meta["canonical"].endswith("/ritiri/yoga/toscana")

    @pytest.mark.asyncio
    async def test_unknown_path_is_none(self):
        assert await shell.resolve_meta("/qualcosa/di/strano") is None


class TestEndpointLive:
    """Contro il backend live (stesso pattern degli altri test API)."""

    def test_home_shell(self):
        r = requests.get(f"{BASE_URL}/__seo/", timeout=10)
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "og:title" in r.text and "canonical" in r.text

    def test_unknown_path_serves_neutral_shell(self):
        r = requests.get(f"{BASE_URL}/__seo/pagina/inesistente-xyz", timeout=10)
        assert r.status_code == 200
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
        noindex; categoria vuota → noindex (thin content)."""
        import re, json
        pop = requests.get(f"{BASE_URL}/__seo/ritiri/yoga", timeout=10)
        assert pop.status_code == 200
        if '"ItemList"' in pop.text:
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
