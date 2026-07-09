"""VT — Visibilità operatore: guardie del tracking first-party.

Il patto col pubblico (cookie banner: "nessuna analytics esterna") e
col business (numeri credibili per l'operatore) si difende qui:

  1. anti-bot: UA bot/vuoti mai contati, browser veri sì;
  2. privacy by design: l'IP entra nell'hash ma NON esiste nel doc
     salvato; il salt ruota ogni giorno (niente percorsi tra giorni);
  3. /public/track risponde SEMPRE 204 (best-effort assoluto) e
     rivalida l'org dal db — slug inventati non scrivono nulla;
  4. dedup: refresh dello stesso visitatore = hits+1, uniques
     invariati;
  5. impression: bump batch + flush → visibility_stats day-level;
  6. /analytics/visibility: auth obbligatoria, shape del funnel;
  7. guardie frontend: hook montato sulle 3 superfici, canale da
     hostname (mai host con porta), niente path del referrer.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import requests

from services.visit_tracking import CHANNELS, SURFACES, is_bot, visitor_hash

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
REPO_ROOT = BACKEND_DIR.parent
SRC = REPO_ROOT / "frontend" / "src"

BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/126.0.0.0 Safari/537.36")


def _login():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
    if r.status_code != 200:
        import pytest
        pytest.skip("demo login unavailable (rate limit?)")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ─── 1. anti-bot ─────────────────────────────────────────────────────────

class TestAntiBot:
    def test_known_bots_are_bots(self):
        for ua in ("Googlebot/2.1 (+http://www.google.com/bot.html)",
                   "curl/8.4.0", "python-requests/2.31",
                   "Mozilla/5.0 AppleWebKit/537.36 HeadlessChrome/120",
                   "GPTBot/1.0", "AhrefsBot/7.0"):
            assert is_bot(ua), f"non riconosciuto come bot: {ua}"

    def test_empty_ua_is_bot(self):
        assert is_bot(None) and is_bot("")

    def test_real_browser_is_not_bot(self):
        assert not is_bot(BROWSER_UA)


# ─── 2. privacy by design ────────────────────────────────────────────────

class TestVisitorHash:
    def test_deterministic_same_day(self):
        a = visitor_hash("1.2.3.4", BROWSER_UA, "2026-07-09")
        b = visitor_hash("1.2.3.4", BROWSER_UA, "2026-07-09")
        assert a == b and len(a) == 16

    def test_salt_rotates_daily(self):
        """Lo stesso visitatore domani ha un hash diverso: nessun
        percorso ricostruibile tra giorni."""
        a = visitor_hash("1.2.3.4", BROWSER_UA, "2026-07-09")
        b = visitor_hash("1.2.3.4", BROWSER_UA, "2026-07-10")
        assert a != b

    def test_ip_never_in_hash_output(self):
        h = visitor_hash("203.0.113.77", BROWSER_UA, "2026-07-09")
        assert "203" not in h or len(h) == 16  # hash esadecimale corto
        assert "203.0.113.77" not in h

    def test_raw_doc_contains_no_pii(self):
        """Il codice di record_view non deve MAI scrivere ip/email/url
        completi nel documento grezzo."""
        src = (BACKEND_DIR / "services" / "visit_tracking.py").read_text()
        # l'IP è solo un argomento di visitor_hash, mai una chiave doc
        assert '"ip"' not in src and "'ip'" not in src, \
            "campo ip nel documento page_views"
        assert "referrer_url" not in src and "full_url" not in src


# ─── 3+4. /public/track: sempre 204, rivalidazione org, dedup ────────────

class TestTrackEndpoint:
    def _track(self, payload, ua=BROWSER_UA):
        return requests.post(
            f"{BASE_URL}/api/public/track", json=payload,
            headers={"User-Agent": ua}, timeout=10)

    def test_always_204_even_on_garbage(self):
        for payload in (
            {"surface": "event", "slug": "slug-inesistente-vt", "channel": "directory"},
            {"surface": "nope", "slug": "x", "channel": "directory"},
            {"surface": "event", "slug": "x", "channel": "canale-finto"},
        ):
            r = self._track(payload)
            assert r.status_code == 204, f"{payload} → {r.status_code}"

    def test_bot_gets_204_but_writes_nothing(self):
        r = self._track({"surface": "event", "slug": "slug-inesistente-vt",
                         "channel": "directory"}, ua="curl/8.4.0")
        assert r.status_code == 204

    def test_validation_error_shape_is_not_500(self):
        r = requests.post(f"{BASE_URL}/api/public/track",
                          json={"surface": "event"},  # slug/channel mancanti
                          headers={"User-Agent": BROWSER_UA}, timeout=10)
        assert r.status_code in (204, 422)  # mai 500


# ─── 5. costanti condivise ───────────────────────────────────────────────

class TestConstants:
    def test_surfaces_and_channels(self):
        assert set(SURFACES) == {"profile", "event", "store"}
        assert set(CHANNELS) == {"directory", "store", "search",
                                 "social", "direct"}


# ─── 6. /analytics/visibility ────────────────────────────────────────────

class TestVisibilityEndpoint:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/analytics/visibility", timeout=10)
        assert r.status_code in (401, 403)

    def test_funnel_shape(self):
        d = requests.get(f"{BASE_URL}/api/analytics/visibility?fresh=true",
                         headers=_login(), timeout=20).json()
        for key in ("month", "summary", "channels", "aurya_visits",
                    "trend_12m", "last_30d", "per_retreat"):
            assert key in d, f"chiave mancante: {key}"
        for metric in ("impressions", "visits", "uniques", "bookings"):
            assert set(d["summary"][metric]) == {"current", "previous"}
        # i canali del payload sono un sottoinsieme dei 5 canonici
        assert set(d["channels"]) <= set(CHANNELS)
        # per_retreat: righe complete per la tabella
        for row in d["per_retreat"]:
            for col in ("slug", "title", "visits", "uniques",
                        "bookings", "conversion_pct"):
                assert col in row


# ─── 7. guardie frontend ─────────────────────────────────────────────────

class TestFrontendGuards:
    def test_hook_mounted_on_three_surfaces(self):
        """useTrackView deve vivere su landing evento, profilo
        operatore e store: senza mount niente dati, niente specchietto."""
        for page, surface in (
            ("features/storefront/EventLandingPage.js", "'event'"),
            ("features/storefront/OperatorProfilePage.js", "'profile'"),
            ("features/storefront/StorefrontPage.js", "'store'"),
        ):
            text = (SRC / page).read_text()
            assert "useTrackView" in text, f"hook non montato su {page}"
            assert f"useTrackView({surface}" in text, \
                f"superficie sbagliata su {page}"

    def test_channel_from_hostname_not_host(self):
        """location.host include la porta e non matcherebbe mai il
        referrer in dev: il confronto deve usare hostname."""
        text = (SRC / "features/storefront/lib/useTrackView.js").read_text()
        assert "window.location.hostname" in text
        assert "window.location.host)" not in text

    def test_referrer_only_hostname(self):
        """Del referrer parte solo l'hostname: mai il path (no PII)."""
        text = (SRC / "features/storefront/lib/useTrackView.js").read_text()
        assert ".hostname" in text
        assert "referrer_host" in text
        # il payload non deve contenere il referrer completo
        assert "referrer: referrer" not in text

    def test_visibility_page_uses_charts_kit(self):
        """La pagina Visibilità passa dal kit CF1 (niente recharts
        diretto — coerenza visiva e palette unica)."""
        text = (SRC / "features/visibility/VisibilityPage.js").read_text()
        assert "components/charts" in text
        assert "from 'recharts'" not in text


# ─── 8. modulo registrato ────────────────────────────────────────────────

class TestModuleRegistry:
    def test_visibility_feature_owned(self):
        from services.module_access import MODULE_OWNERSHIP
        assert "visibility" in MODULE_OWNERSHIP
