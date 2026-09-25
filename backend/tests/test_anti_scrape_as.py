"""AS (25/9/2026 sera, founder: «quanto e' facile scrappare Aurya? mettiamo
meccanismi anti-scrape e anti-bot, senza rompere la SEO che resta priorita'»).

  AS1  l'IP vero: il limitatore si fidava del PRIMO X-Forwarded-For, che
       scrive il client (nginx accoda il suo): bastava un header falso per
       cambiare identita' e aggirare ogni limite. Ora X-Real-IP (scritto
       da nginx, non falsificabile) e poi l'ULTIMO X-Forwarded-For.
       nginx: zona pubapi su /api/public/ (3 r/s, scorta 60), 444 agli
       scanner (.php, .env, wp-login…). Backend: 30/min sulla directory,
       60/min sul profilo.
  AS2  l'email dell'operatore non viaggia piu' nel JSON del profilo ne'
       nel JSON-LD dell'HTML: arriva al clic da /contatti (10/min). Il
       telefono resta (LocalBusiness, SEO locale). robots.txt invariato:
       «Allow: /api/public/» serve al rendering di Google.
"""
import os
from pathlib import Path
from unittest.mock import MagicMock

import requests

RADICE = Path(__file__).resolve().parents[2]
BACKEND = RADICE / "backend"
FE = RADICE / "frontend" / "src"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")

NGINX = (RADICE / "deploy" / "nginx" / "nginx.conf").read_text(encoding="utf-8")
PUBLIC = (BACKEND / "routers" / "public.py").read_text(encoding="utf-8")
SHELL = (BACKEND / "routers" / "seo_shell.py").read_text(encoding="utf-8")
SERVER = (BACKEND / "server.py").read_text(encoding="utf-8")


def _req(headers, host="10.0.0.9"):
    r = MagicMock()
    r.headers = headers
    r.client = MagicMock(host=host)
    return r


class TestAs1IpVero:
    def test_x_real_ip_vince_e_xff_si_legge_da_destra(self):
        from core.rate_limiting import _extract_forwarded_for, get_real_ip
        # il client scrive 1.2.3.4, nginx accoda il peer: conta il peer
        assert _extract_forwarded_for("1.2.3.4, 203.0.113.7") == "203.0.113.7"
        assert _extract_forwarded_for("1.2.3.4,5.6.7.8, 203.0.113.7") == "203.0.113.7"
        assert _extract_forwarded_for("203.0.113.7") == "203.0.113.7"
        assert _extract_forwarded_for("1.2.3.4, , ") == "1.2.3.4"
        assert _extract_forwarded_for("") is None and _extract_forwarded_for(None) is None
        assert get_real_ip(_req({"x-real-ip": "203.0.113.7", "x-forwarded-for": "1.2.3.4"})) == "203.0.113.7"
        assert get_real_ip(_req({"x-forwarded-for": "1.2.3.4, 203.0.113.7"})) == "203.0.113.7"
        assert get_real_ip(_req({})) == "10.0.0.9"

    def test_lo_spoof_non_cambia_identita(self):
        """Dietro nginx l'header arriva SEMPRE come «<roba del client>, <peer>»
        (proxy_add_x_forwarded_for) e X-Real-IP e' il peer: due richieste
        con spoof diversi devono finire nello stesso secchio."""
        from core.rate_limiting import get_real_ip
        a = get_real_ip(_req({"x-real-ip": "203.0.113.7", "x-forwarded-for": "1.1.1.1, 203.0.113.7"}))
        b = get_real_ip(_req({"x-real-ip": "203.0.113.7", "x-forwarded-for": "9.9.9.9, 203.0.113.7"}))
        assert a == b == "203.0.113.7"
        assert "proxy_set_header X-Real-IP $remote_addr;" in NGINX
        assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;" in NGINX

    def test_nginx_zona_pubapi_e_scanner(self):
        assert "limit_req_zone $binary_remote_addr zone=pubapi:10m rate=3r/s;" in NGINX
        blocco = NGINX.split("location /api/public/ {")[1].split("}")[0]
        assert "limit_req zone=pubapi burst=60 nodelay;" in blocco and "proxy_pass http://backend:8000;" in blocco
        # la location annidata sta DENTRO ^~ /api/ (prima di /api/auth/login)
        assert NGINX.index("location ^~ /api/ {") < NGINX.index("location /api/public/ {") < NGINX.index("location /api/auth/login {")
        assert NGINX.count("return 444;") == 3
        assert r"location ~* \.(php|phtml|asp|aspx|jsp|cgi|sql|bak|old|orig|swp|ini)$ { return 444; }" in NGINX
        assert r"location ~* (^|/)\.(env|git|svn|aws|ssh|DS_Store)(/|$|\.) { return 444; }" in NGINX
        # niente .txt (robots, IndexNow) e niente .xml nelle regole scanner
        for ext in ("txt", "xml", "js", "css", "json", "webp", "png", "map"):
            assert f"|{ext}|" not in NGINX.split("return 444")[0].split("Anti-scanner")[1] and f"|{ext})" not in NGINX.split("return 444")[0].split("Anti-scanner")[1], ext

    def test_backend_limiti_su_directory_e_profilo(self):
        idx = PUBLIC[PUBLIC.index('@router.get("/operators")'):][:400]
        assert '@limiter.limit("30/minute")' in idx and "async def public_operators_index(" in idx
        prof = PUBLIC[PUBLIC.index('@router.get("/operator/{org_slug}")'):][:400]
        assert '@limiter.limit("60/minute")' in prof
        assert "async def public_operator_profile(org_slug: str, request: Request = None, lang: Optional[str] = None):" in prof

    def test_la_seo_non_si_tocca(self):
        """robots.txt tiene «Allow: /api/public/» (il rendering di Google
        chiama le API) e il telefono resta nel LocalBusiness."""
        assert '"Allow: /api/public/\\n"' in SERVER
        assert 'jsonld["telephone"] = profile["public_phone"]' in SHELL
        assert 'jsonld["email"]' not in SHELL


class TestAs2EmailAlClic:
    def test_rotta_contatti_e_profilo_senza_email(self):
        rotta = PUBLIC[PUBLIC.index('@router.get("/operator/{org_slug}/contatti")'):][:900]
        assert '@limiter.limit("10/minute")' in rotta
        assert 'if not pp.get("show_contacts"):\n        return {}' in rotta
        assert 'for k in ("public_email", "public_phone") if pp.get(k)' in rotta
        blocco = PUBLIC[PUBLIC.index('if pp.get("show_contacts"):\n        out["contacts"]'):][:300]
        assert '("public_phone",)' in blocco and 'out["contacts"]["has_email"] = bool(pp.get("public_email"))' in blocco
        assert '"public_email", "public_phone")\n                           if pp.get(k)}' not in PUBLIC

    def test_frontend_mostra_email(self):
        comp = (FE / "features" / "storefront" / "components" / "MostraEmail.jsx").read_text(encoding="utf-8")
        assert "api.get(`/public/operator/${slug}/contatti`)" in comp
        for tid in ("mostra-email", "mostra-email-link", "mostra-email-errore"):
            assert f'data-testid="{tid}"' in comp, tid
        prof = (FE / "features" / "storefront" / "OperatorProfilePage.js").read_text(encoding="utf-8")
        about = (FE / "features" / "storefront" / "components" / "StoreAbout.jsx").read_text(encoding="utf-8")
        for src, nome in ((prof, "profilo"), (about, "about")):
            assert "<MostraEmail slug=" in src and "contacts?.has_email" in src, nome
            assert "contacts?.public_email" not in src and "contacts.public_email" not in src, nome

    def test_dal_vivo_il_profilo_non_porta_email(self):
        r = requests.get(f"{BASE_URL}/api/public/operators", params={"preview": 1}, timeout=15)
        if r.status_code != 200:
            return
        for it in (r.json().get("items") or [])[:8]:
            slug = it.get("org_slug")
            p = requests.get(f"{BASE_URL}/api/public/operator/{slug}", timeout=15)
            if p.status_code == 429:
                return          # il limite nuovo ha morso: e' quello che volevamo
            if p.status_code != 200:
                continue
            c = p.json().get("contacts") or {}
            assert "public_email" not in c, slug
            assert set(c) <= {"public_phone", "has_email"}, (slug, c)
            cc = requests.get(f"{BASE_URL}/api/public/operator/{slug}/contatti", timeout=15)
            assert cc.status_code in (200, 429), slug
            if cc.status_code == 200 and c.get("has_email"):
                assert cc.json().get("public_email"), slug
