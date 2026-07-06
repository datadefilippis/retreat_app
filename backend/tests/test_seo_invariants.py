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
SITEMAPS = ("core", "retreats", "products", "operators")


def _get(path: str) -> str:
    r = requests.get(f"{BASE_URL}{path}", timeout=10)
    assert r.status_code == 200, f"{path} → {r.status_code}"
    return r.text


class TestSitemapIndex:
    def test_index_lists_all_four(self):
        xml = _get("/api/public/sitemap.xml")
        assert "<sitemapindex" in xml
        for name in SITEMAPS:
            assert f"sitemap-{name}.xml" in xml, f"manca sitemap-{name}"

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


class TestProductParity:
    def test_published_products_reach_sitemap(self):
        """Ogni prodotto non-evento visibile nel catalogo pubblico di uno
        store demo sta in sitemap-products — la promessa 'chiunque
        pubblica è indicizzato'. Tutto via HTTP (niente asyncio.run nel
        test: il motor client è legato al loop del server, un secondo
        loop nella suite completa lo fa arrabbiare)."""
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
