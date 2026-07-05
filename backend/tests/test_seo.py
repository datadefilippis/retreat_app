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

from routers.seo import _url


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

    def test_sitemap_only_published_future(self):
        src = open(os.path.join(os.path.dirname(__file__), "..",
                                "routers", "seo.py")).read()
        assert '"status": "published"' in src
        assert '"$gte": now_iso' in src      # mai ritiri passati
