"""OP4 + VT7 — consolidamento profilo operatore: guardie.

  1. il TITOLO pubblico dell'operatore e' organizations.name (la riga
     delle Impostazioni) su TUTTE le superfici: /public/operators,
     /public/operator/{slug}, directory ritiri, SEO shell;
  2. il nome si modifica anche dal profilo (PATCH public-profile) e il
     vuoto NON cancella;
  3. /public/operators parla la lingua del viaggiatore (bio tradotte,
     fallback italiano mai buchi);
  4. i18n: le chiavi operators.* esistono nelle 4 lingue (il bug era
     proprio questo: card e hero rendevano il defaultValue italiano);
  5. VT7: business-profile espone il blocco traffic, i segnali hanno
     traffic_drop;
  6. VT6b: la riga sulla misurazione aggregata e' nelle 4 privacy.
"""

import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
REPO_ROOT = BACKEND_DIR.parent
LOCALES = REPO_ROOT / "frontend" / "src" / "locales"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/126 Safari/537.36"}


def _login(email="admin@demo.com"):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email, "password": "demo1234"}, timeout=10)
    if r.status_code != 200:
        pytest.skip("demo login unavailable (rate limit?)")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ─── 1+2+3. nome org come titolo pubblico + multilingua ──────────────────

class TestPublicName:
    def test_profile_edit_round_trip_and_public_surfaces(self):
        h = _login()
        # stato di partenza
        before = requests.get(
            f"{BASE_URL}/api/organizations/current/public-profile",
            headers=h, timeout=10).json()
        assert "name" in before, "GET public-profile deve esporre name"

        # PATCH nome + traduzione en della bio
        marker = "Test OP4 public name"
        r = requests.patch(
            f"{BASE_URL}/api/organizations/current/public-profile",
            headers=h, timeout=10,
            json={"name": marker,
                  "translations": {"en": {"bio": "An English bio for the "
                                                 "OP4 guard test."}}})
        assert r.status_code == 200
        assert r.json()["name"] == marker

        try:
            # /public/operators: name = nome org, bio en con ?lang=en
            ops = requests.get(f"{BASE_URL}/api/public/operators",
                               params={"lang": "en"}, headers=UA,
                               timeout=10).json()
            row = next((i for i in ops["items"]
                        if i["name"] == marker), None)
            assert row, "il nome org aggiornato deve comparire nell'indice"
            assert "English bio" in (row.get("bio") or "")

            # fallback IT senza lang
            ops_it = requests.get(f"{BASE_URL}/api/public/operators",
                                  headers=UA, timeout=10).json()
            row_it = next((i for i in ops_it["items"]
                           if i["name"] == marker), None)
            assert row_it and "English bio" not in (row_it.get("bio") or "")

            # /public/operator/{slug}: stesso nome
            prof = requests.get(
                f"{BASE_URL}/api/public/operator/{row['org_slug']}",
                timeout=10).json()
            assert prof["name"] == marker

            # vuoto NON cancella
            r2 = requests.patch(
                f"{BASE_URL}/api/organizations/current/public-profile",
                headers=h, timeout=10, json={"name": "   ", "bio": before.get("bio")})
            assert r2.json()["name"] == marker
        finally:
            # ripristino il nome originale (dev db condiviso)
            if before.get("name"):
                requests.patch(
                    f"{BASE_URL}/api/organizations/current/public-profile",
                    headers=h, timeout=10, json={"name": before["name"]})

    def test_name_resolution_is_org_first_in_code(self):
        """La risoluzione 'org.name prima dei nomi store' deve restare
        su tutte e 4 le superfici (regressione = incongruenza)."""
        pub = (BACKEND_DIR / "routers" / "public.py").read_text()
        # PL9: davanti c'è la redazione dei campioni, ma la risoluzione
        # resta org-first (org.name → display_name → store name → slug)
        assert '"name": "" if _is_sample else (org.get("name")' in pub
        assert 'or ss.get("display_name") or s.get("name") or s["slug"])' in pub
        assert '"name": org.get("name") or store.get("name")' in pub
        assert 'org_name[o["id"]] = o.get("name") or' in pub
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert 'name = (org.get("name")' in shell


# ─── 4. i18n: chiavi operators nelle 4 lingue ────────────────────────────

OPERATORS_KEYS = ("heading", "headingCat", "subtitle", "seoTitle",
                  "seoDesc", "retreatCount_one", "retreatCount_other",
                  "productCount_one", "productCount_other",
                  "emptyTitle", "emptyBody", "backHome")


class TestOperatorsI18n:
    @pytest.mark.parametrize("lang", ["it", "en", "de", "fr"])
    def test_operators_keys_exist(self, lang):
        data = json.loads((LOCALES / lang / "landings.json").read_text())
        ops = data.get("operators") or {}
        missing = [k for k in OPERATORS_KEYS if not ops.get(k)]
        assert not missing, f"{lang}: chiavi operators mancanti {missing}"

    @pytest.mark.parametrize("lang", ["it", "en", "de", "fr"])
    def test_visibility_keys_exist(self, lang):
        common = json.loads((LOCALES / lang / "common.json").read_text())
        vis = common.get("visibility") or {}
        for k in ("title", "impressions", "visits", "bookings",
                  "proofTitle", "earlyTitle", "privacyNote"):
            assert vis.get(k), f"{lang}: visibility.{k} mancante"
        settings = json.loads((LOCALES / lang / "settings.json").read_text())
        pp = settings.get("publicProfile") or {}
        for k in ("publicName", "publicNameHint",
                  "visibilityTitle", "visibilityHint"):
            assert pp.get(k), f"{lang}: publicProfile.{k} mancante"


class TestProfileEditorConsolidato:
    """OP4c-bis — l'editor profilo e' consolidato: UNA sezione
    multilingua con tutte le bandierine (IT inclusa col badge
    'principale') e OGNI label della pagina tradotta nelle 4 lingue
    dell'admin."""

    PAGE = (REPO_ROOT / "frontend" / "src" / "features" / "settings"
            / "PublicProfilePage.js")

    def test_single_multilang_section_with_children(self):
        src = self.PAGE.read_text()
        # children mode = tab Italiano presente (niente sezione
        # traduzioni separata dalla casella italiana)
        assert "</MultiLangSection>" in src,             "la sezione multilingua deve avvolgere i campi italiani"
        # la tagline non deve avere una seconda casella fuori dalle tab
        assert src.count("set('tagline'") == 1
        assert src.count("set('bio'") == 1

    @pytest.mark.parametrize("lang", ["it", "en", "de", "fr"])
    def test_every_page_key_translated(self, lang):
        """Ogni publicProfile.* usata nella pagina esiste nella lingua:
        un admin con locale en/de/fr non deve vedere il defaultValue
        italiano."""
        import re
        used = sorted(set(re.findall(r"publicProfile\.([a-zA-Z]+)",
                                     self.PAGE.read_text())))
        data = json.loads((LOCALES / lang / "settings.json").read_text())
        pp = data.get("publicProfile") or {}
        missing = [k for k in used if not pp.get(k)]
        assert not missing, f"{lang}: publicProfile.{missing} mancanti"

    @pytest.mark.parametrize("lang", ["it", "en", "de", "fr"])
    def test_multilang_component_keys(self, lang):
        data = json.loads(
            (LOCALES / lang / "products.json").read_text())
        ml = data.get("multilang") or {}
        for k in ("primaryTag", "primaryHint", "sectionHint"):
            assert ml.get(k), f"{lang}: multilang.{k} mancante"


# ─── 5. VT7 admin ────────────────────────────────────────────────────────

class TestVt7Admin:
    def test_business_profile_has_traffic(self):
        h = _login("sysadmin@demo.com")
        # una org qualsiasi dalla directory admin
        snap = requests.get(f"{BASE_URL}/api/admin/platform/directory",
                            headers=h, timeout=20).json()
        rows = snap.get("rows") or []
        if not rows:
            pytest.skip("nessuna org nello snapshot dev")
        org_id = rows[0]["organization_id"]
        d = requests.get(
            f"{BASE_URL}/api/admin/platform/organizations/{org_id}/business-profile",
            headers=h, timeout=20).json()
        tr = d.get("traffic")
        assert tr is not None
        for k in ("visits_month", "uniques_month",
                  "visits_prev_month", "impressions_month"):
            assert k in tr

    def test_signals_have_traffic_drop(self):
        h = _login("sysadmin@demo.com")
        d = requests.get(f"{BASE_URL}/api/admin/platform/signals",
                         headers=h, timeout=20).json()
        assert "traffic_drop" in d
        assert isinstance(d["traffic_drop"], list)


# ─── 6. VT6b privacy ─────────────────────────────────────────────────────

class TestPrivacyLine:
    @pytest.mark.parametrize("lang,needle", [
        ("it", "Statistiche di visibilita' in forma aggregata e anonima"),
        ("en", "Aggregated, anonymous visibility statistics"),
        ("de", "Aggregierte, anonyme Sichtbarkeitsstatistiken"),
        ("fr", "Statistiques de visibilité agrégées et anonymes"),
    ])
    def test_privacy_mentions_aggregated_measurement(self, lang, needle):
        text = (BACKEND_DIR / "legal" / f"privacy_{lang}.md").read_text()
        assert needle in text
        # la promessa resta: niente IP salvato
        assert "IP" in text
