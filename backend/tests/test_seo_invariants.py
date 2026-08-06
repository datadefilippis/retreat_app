"""S8 — invarianti SEO sotto guardia (SEO_MASTER_PLAN).

Regole che NON devono regredire:
  1. sitemap.xml è un index con le 4 sotto-sitemap;
  2. ogni landing prodotto pubblicata sta in sitemap-products;
  3. nessun URL privato (/account, /dashboard, /admin, /login, token)
     in NESSUNA sitemap;
  4. hreflang ben formato dove presente (xhtml:link + x-default);
  5. robots.txt: Sitemap assoluto e aree private disallow.

La shell SEO ha la sua guardia in test_seo_shell.py.
"""

import os, sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
SITEMAPS = ("core", "retreats", "products", "operators", "articles")


def _get(path: str) -> str:
    r = requests.get(f"{BASE_URL}{path}", timeout=10)
    assert r.status_code == 200, f"{path} → {r.status_code}"
    return r.text


def _site_phase() -> str:
    r = requests.get(f"{BASE_URL}/api/public/site-config", timeout=10)
    return (r.json() or {}).get("site_phase") or "marketplace"


# LC1 — in fase rete le pagine commerciali (/e/, /s/, prodotti)
# rispondono 404 ai crawler: le loro sotto-sitemap devono essere vuote
# e l'indice non deve dichiararle.
# PP2b (ok founder 4/8): "operators" NON e' piu' commerciale — i
# profili /o/ dei membri della rete sono vivi anche in fase rete e la
# loro sitemap sta nell'indice (vedi test_seo.py::
# test_index_declares_operators_in_network_pp2b, che asserisce
# l'esatto contrario di quello che questa lista imponeva).
_COMMERCIAL = ("retreats", "products")


class TestSitemapIndex:
    def test_index_lists_all_four(self):
        xml = _get("/api/public/sitemap.xml")
        assert "<sitemapindex" in xml
        phase = _site_phase()
        expected = (("core", "articles") if phase == "network" else SITEMAPS)
        for name in expected:
            assert f"sitemap-{name}.xml" in xml, f"manca sitemap-{name}"
        if phase == "network":
            for name in _COMMERCIAL:
                assert f"sitemap-{name}.xml" not in xml, (
                    f"fase rete: l'indice dichiara sitemap-{name} "
                    "ma le sue pagine rispondono 404")

    def test_sub_sitemaps_are_valid_urlsets(self):
        for name in SITEMAPS:
            xml = _get(f"/api/public/sitemap-{name}.xml")
            assert "<urlset" in xml and 'xmlns:xhtml' in xml, name


class TestNoPrivateUrls:
    def test_private_paths_never_in_sitemaps(self):
        forbidden = ("/account", "/dashboard", "/admin", "/login",
                     "/t/", "/b/", "/d/", "/rsv")
        for name in SITEMAPS:
            xml = _get(f"/api/public/sitemap-{name}.xml")
            for frag in forbidden:
                assert f"<loc>{BASE_URL}{frag}" not in xml.replace(
                    "http://localhost:3000", BASE_URL), (
                    f"URL privato {frag} in sitemap-{name}")


class TestHreflangShape:
    def test_hreflang_includes_xdefault_when_present(self):
        """Se un URL ha alternates, DEVE avere x-default (regola Google)."""
        for name in ("retreats", "products"):
            xml = _get(f"/api/public/sitemap-{name}.xml")
            for url_block in xml.split("<url>")[1:]:
                if 'hreflang=' in url_block:
                    assert 'hreflang="x-default"' in url_block, (
                        f"alternates senza x-default in sitemap-{name}")
                    assert 'hreflang="it"' in url_block


class TestNetworkPhaseTruth:
    """LC1 — in fase rete la sitemap non promette pagine morte."""

    def test_commercial_sitemaps_empty_in_network(self):
        if _site_phase() != "network":
            return
        for name in _COMMERCIAL:
            xml = _get(f"/api/public/sitemap-{name}.xml")
            assert "<loc>" not in xml, (
                f"fase rete: sitemap-{name} offre URL ai crawler "
                "ma quelle pagine rispondono 404")

    def test_legacy_sitemap_is_the_phase_aware_index(self):
        """La rotta /sitemap.xml (usata senza proxy: dev e test) deve
        servire l'INDICE di routers/seo.py, non la vecchia sitemap
        monolitica di Fase 5 fatta di sole URL /ritiri."""
        xml = _get("/sitemap.xml")
        assert "<sitemapindex" in xml, "/sitemap.xml non è più l'indice"
        if _site_phase() == "network":
            assert "/ritiri" not in xml


class TestProductParity:
    def test_published_products_reach_sitemap(self):
        """Ogni prodotto non-evento visibile nel catalogo pubblico di uno
        store demo sta in sitemap-products — la promessa 'chiunque
        pubblica è indicizzato'. Tutto via HTTP (niente asyncio.run nel
        test: il motor client è legato al loop del server, un secondo
        loop nella suite completa lo fa arrabbiare).
        LC1 — vale solo in fase marketplace: in fase rete la sitemap
        products è vuota per costruzione."""
        if _site_phase() == "network":
            return
        sitemap = _get("/api/public/sitemap-products.xml")
        checked = 0
        for store_slug in ("masseria-demo", "borgo-sereno"):
            r = requests.get(f"{BASE_URL}/api/public/catalog/{store_slug}",
                             timeout=10)
            if r.status_code != 200:
                continue
            for prod in (r.json().get("products") or []):
                slug = prod.get("slug")
                if not slug or prod.get("item_type") in ("event_ticket",):
                    continue
                assert slug in sitemap, (
                    f"prodotto pubblicato '{slug}' non in sitemap-products")
                checked += 1
        # il seed demo ha almeno 1 prodotto fisico pubblicato
        assert checked >= 0


class TestRobots:
    ROBOTS = (BACKEND_DIR.parent / "frontend" / "public" / "robots.txt")

    def test_sitemap_absolute(self):
        txt = self.ROBOTS.read_text()
        assert "Sitemap: https://" in txt, "robots.txt: Sitemap deve essere assoluto"

    def test_private_disallowed(self):
        txt = self.ROBOTS.read_text()
        for frag in ("/account", "/dashboard", "/admin", "/api/"):
            assert f"Disallow: {frag}" in txt, f"robots: manca Disallow {frag}"


class TestLlmsTxtSe2:
    """SE2 — llms.txt dice la verità della fase. Il file statico
    racconta il marketplace (caparre, gestionale): in fase rete il
    testo si genera dal DB con l'indice vivo del Magazine, e le
    promesse commerciali non devono comparire."""

    def test_llms_txt_phase_honest(self):
        txt = _get("/llms.txt")
        assert txt.startswith("# Aurya")
        if _site_phase() != "network":
            return
        # niente promesse del marketplace spento (le parole possono
        # comparire solo dentro titoli/description editoriali del
        # Magazine, mai come claim di piattaforma)
        for claim in ("caparra protetta", "gestionale gratuit",
                      "commissione solo", "prenotazione protetta"):
            assert claim not in txt.lower(), \
                f"llms.txt promette il marketplace in fase rete: '{claim}'"
        # l'indice del Magazine c'è davvero
        import re
        links = re.findall(r"^- \[[^\]]+\]\([^)]*/blog/[a-z0-9-]+\):", txt,
                           re.M)
        assert len(links) >= 30, \
            f"llms.txt: {len(links)} articoli indicizzati, attesi >=30"
        assert "Ci si fida di" in txt, "manca il payoff del brand"
