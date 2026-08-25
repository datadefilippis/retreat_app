"""F3 — sitemap dinamica e regole SEO."""

import os, sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

from datetime import datetime, timezone

import pytest

from routers.seo import (_url, build_core, build_index, build_operators,
                         build_products, build_retreats)


class TestSitemapUrl:
    def test_lastmod_accepts_datetime(self):
        out = _url("https://x.it/a", lastmod=datetime(2026, 7, 5, tzinfo=timezone.utc))
        assert "<lastmod>2026-07-05</lastmod>" in out

    def test_lastmod_accepts_iso_string(self):
        out = _url("https://x.it/a", lastmod="2026-07-05T10:00:00+00:00")
        assert "<lastmod>2026-07-05</lastmod>" in out

    def test_loc_is_escaped(self):
        out = _url("https://x.it/a?b=1&c=2")
        assert "&amp;" in out          # XML valido anche con query string

    def test_robots_blocks_tokenized_and_private(self):
        robots = open(os.path.join(os.path.dirname(__file__), "..", "..",
                                   "frontend", "public", "robots.txt")).read()
        for path in ("/account", "/admin", "/t/", "/b/", "/api/"):
            assert f"Disallow: {path}" in robots
        assert "Sitemap:" in robots

    @pytest.mark.asyncio
    async def test_core_network_phase_rt5(self, monkeypatch):
        """RT5 — in fase network la sitemap core dice la verita': home,
        manifesto, chi siamo, rete, newsletter. Niente hub commerciali
        (il ramo network esce PRIMA di toccare il DB: il test non
        richiede Mongo).
        SW3 — /chi-siamo rientra in sitemap: e' una pagina vera (le
        persone dietro Aurya), non piu' un redirect sul Manifesto."""
        monkeypatch.setenv("SITE_PHASE", "network")
        xml = await build_core()
        for path in ("/manifesto", "/chi-siamo", "/entra-nella-rete",
                     "/newsletter", "/operatori"):
            assert f"{path}</loc>" in xml, f"manca {path}"
        # GS5 (25/8) — privacy/termini USCITE dalla sitemap: sono rotte
        # di servizio con noindex nella shell, e sitemap+noindex sono
        # segnali in conflitto (in Search Console stavano tra le poche
        # pagine indicizzate, al posto degli articoli).
        for assente in ("/come-funziona", "/ritiri",
                        "/destinazioni", "/privacy", "/termini"):
            assert assente not in xml, f"non deve esserci {assente}"

    @pytest.mark.asyncio
    async def test_commercial_builders_empty_in_network_lc1(self, monkeypatch):
        """LC1 — in fase rete le sitemap transazionali (/e/, landing
        prodotto) restano vuote: non si pubblicizzano ai crawler."""
        monkeypatch.setenv("SITE_PHASE", "network")
        for build in (build_retreats, build_products):
            xml = await build()
            assert "<loc>" not in xml, f"{build.__name__} non vuoto in rete"

    @pytest.mark.asyncio
    async def test_operators_sitemap_members_only_in_network_pp2b(
            self, monkeypatch):
        """PP2b (ok founder 4/8) — in fase rete la sitemap operators
        elenca i SOLI membri della rete, e il solo profilo /o/: mai
        /s/ (lo store non esiste nel mondo snello)."""
        monkeypatch.setenv("SITE_PHASE", "network")
        xml = await build_operators()
        assert "/s/" not in xml, "store in sitemap in fase rete"
        import re
        locs = re.findall(r"<loc>([^<]+)</loc>", xml)
        assert all("/o/" in u for u in locs), f"URL non-profilo: {locs}"
        # ogni voce corrisponde a un membro vero della rete
        from database import organizations_collection
        n_members = await organizations_collection.count_documents(
            {"network_member": True, "is_active": {"$ne": False}})
        assert len(locs) <= n_members

    def test_index_declares_operators_in_network_pp2b(self, monkeypatch):
        monkeypatch.setenv("SITE_PHASE", "network")
        xml = build_index()
        assert "sitemap-core.xml" in xml and "sitemap-articles.xml" in xml
        # PP2b — operators si dichiara (elenca i membri della rete)
        assert "sitemap-operators.xml" in xml
        for name in ("retreats", "products"):
            assert f"sitemap-{name}.xml" not in xml, (
                f"l'indice dichiara sitemap-{name} in fase rete")

    def test_sitemap_only_published_future(self):
        src = open(os.path.join(os.path.dirname(__file__), "..",
                                "routers", "seo.py")).read()
        assert '"status": "published"' in src
        assert '"$gte": now_iso' in src      # mai ritiri passati
