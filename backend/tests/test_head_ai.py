"""AI1 (8/9/2026) — le HEAD rispondono come le GET, senza corpo.

Il founder ha chiesto a ChatGPT e a Claude di analizzare aurya.life ed
entrambi hanno detto «non riesco ad accedere». Il sito era aperto (robots,
200 ai loro user-agent, certificato valido, testo server-side), ma a una
HEAD rispondeva 405 su ogni pagina: FastAPI registra solo i metodi
dichiarati. Un fetcher che apre con una HEAD e legge 405 si ferma li'.

Questa guardia tiene la porta aperta: HEAD = GET senza corpo, stessi
status e header, su shell, sitemap, robots, llms.txt e API pubbliche.
"""
import os
import sys
from pathlib import Path

import pytest
import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")

# in prod nginx manda / → /__seo/, /sitemap.xml → /api/public/sitemap.xml,
# /llms.txt e /robots.txt al backend: qui si bussa alle porte del backend
PORTE = ["/__seo/", "/__seo/manifesto", "/__seo/operatori", "/__seo/blog",
         "/api/public/sitemap.xml", "/api/public/sitemap-core.xml",
         "/llms.txt", "/robots.txt", "/api/health/live"]


def _vivo():
    try:
        return requests.get(f"{BASE}/api/health/live", timeout=5).status_code == 200
    except Exception:
        return False


class TestHeadComeGet:

    def test_il_middleware_e_registrato_per_tutto_il_sito(self):
        src = (BACKEND_DIR / "server.py").read_text()
        assert "class _HeadComeGetMiddleware" in src
        assert "app.add_middleware(_HeadComeGetMiddleware)" in src
        corpo = src.split("class _HeadComeGetMiddleware")[1].split("app.add_middleware(_HeadComeGetMiddleware)")[0]
        assert 'scope["method"] = "GET"' in corpo and '"body": b""' in corpo

    @pytest.mark.parametrize("porta", PORTE)
    def test_head_risponde_come_la_get_senza_corpo(self, porta):
        if not _vivo():
            pytest.skip("backend locale non raggiungibile")
        g = requests.get(f"{BASE}{porta}", timeout=15, allow_redirects=False)
        h = requests.head(f"{BASE}{porta}", timeout=15, allow_redirects=False)
        assert h.status_code == g.status_code, f"{porta}: HEAD {h.status_code} vs GET {g.status_code}"
        assert h.status_code != 405
        assert h.content == b"", f"{porta}: la HEAD non porta corpo"
        for k in ("content-type", "content-length"):
            if k in g.headers:
                assert h.headers.get(k) == g.headers[k], f"{porta}: header {k} diverso fra HEAD e GET"

    def test_una_head_non_apre_porte_chiuse(self):
        """HEAD passa per la rotta GET: le porte riservate restano chiuse."""
        if not _vivo():
            pytest.skip("backend locale non raggiungibile")
        assert requests.head(f"{BASE}/api/admin/strutture", timeout=10).status_code in (401, 403)
        assert requests.head(f"{BASE}/api/auth/me", timeout=10).status_code in (401, 403)
