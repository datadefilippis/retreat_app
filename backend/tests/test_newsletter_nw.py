"""NW — la Lettera con opt-in esperienze e il circuito iscrizioni.

Dispositivo sotto guardia (ciclo NW, 5 ago 2026):
  1. NW1 — profilo esperienziale: interessi SOLO dal vocabolario,
     travel solo near/anywhere, flag → retreat_alert.enabled; un
     errore di scrittura NON torna un finto ok.
  2. NW2 — form progressivo: base nome+email, blocco esperienze dietro
     flag, attivo su home e /newsletter; l'errore si mostra.
  3. NW3 — admin: lista iscritti con FONTE sempre presente; il
     drill-down utenti mostra la fonte newsletter.
  4. NW4 — circuito checkout: il consenso marketing si calcola dai
     TIMESTAMP (accepted/revoked), mai dal flag inesistente; il
     conteggio org include i checkout opt-in; la revoca org porta
     anche le submission dei form a 'unsubscribed'.
  5. NW5 — GDPR: export/cancellazione account includono la Lettera;
     l'hard delete dell'org porta via form e submission newsletter.
  6. Flusso live: iscrizione estesa → dati strutturati a DB →
     conferma → disiscrizione.
"""

import os
import sys
import uuid
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
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"


def _server_secret() -> str:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("JWT_SECRET_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ["JWT_SECRET_KEY"]


class TestNw1Model:
    def test_interests_whitelist(self):
        from routers.subscribers import _clean_interests, EXPERIENCE_INTERESTS
        assert _clean_interests(["yoga", "hacker", "reiki", "yoga"]) == \
            ["yoga", "reiki"]
        assert "misto" in EXPERIENCE_INTERESTS

    def test_travel_options(self):
        from routers.subscribers import TRAVEL_OPTIONS
        assert TRAVEL_OPTIONS == ("near", "anywhere")

    def test_payload_accepts_new_fields(self):
        from routers.subscribers import SubscribePayload
        p = SubscribePayload(email="a@b.it", wants_experiences=True,
                             interests=["yoga"], city="Bari",
                             travel="near", consent=True)
        assert p.wants_experiences is True and p.interests == ["yoga"]

    def test_db_error_is_not_a_fake_ok(self):
        src = (BACKEND_DIR / "routers" / "subscribers.py").read_text()
        assert "status_code=503" in src, \
            "un errore di scrittura deve essere onesto, non un finto ok"

    def test_brevo_sync_carries_experience_profile(self):
        src = (BACKEND_DIR / "services" /
               "subscriber_brevo_sync.py").read_text()
        for attr in ("AURYA_INTERESTS", "AURYA_CITY", "AURYA_TRAVEL"):
            assert attr in src, f"attributo Brevo mancante: {attr}"


class TestNw2Form:
    def test_leadform_progressive_block(self):
        src = (FRONTEND_SRC / "features" / "prelaunch"
               / "LeadForm.jsx").read_text()
        assert "experiencesOptIn" in src
        assert "wants_experiences" in src
        assert "EXP_INTERESTS" in src
        # l'errore del subscribe si mostra, niente grazie finto
        assert "setState('error')" in src

    def test_letter_surfaces_have_the_flag(self):
        """TUTTE le superfici della Lettera hanno l'opt-in esperienze
        (richiesta founder 5/8): home, /newsletter, CTA del blog
        (fine articolo + indice) e gate delle guide riservate."""
        surfaces = [
            FRONTEND_SRC / "features" / "network" / "NetworkHomePage.js",
            FRONTEND_SRC / "features" / "prelaunch"
            / "NewsletterLandingPage.js",
            FRONTEND_SRC / "features" / "storefront" / "components"
            / "BlogNewsletterCTA.jsx",
            FRONTEND_SRC / "features" / "storefront" / "BlogArticlePage.js",
        ]
        for path in surfaces:
            assert "experiencesOptIn" in path.read_text(), \
                f"{path.name}: superficie Lettera senza opt-in esperienze"

    def test_preferences_payload_covers_profile(self):
        from routers.subscribers import PreferencesPayload
        p = PreferencesPayload(token="x", interests=["reiki"],
                               city="Roma", travel="anywhere")
        assert p.interests == ["reiki"]


class TestNw3Admin:
    def test_admin_subscribers_endpoint_guarded(self):
        src = (BACKEND_DIR / "routers" / "subscribers.py").read_text()
        assert '"/admin/subscribers"' in src
        i = src.index('"/admin/subscribers"')
        assert "require_system_admin" in src[i:i + 900], \
            "la lista iscritti deve essere solo system admin"

    def test_admin_rows_always_carry_source(self):
        src = (BACKEND_DIR / "routers" / "subscribers.py").read_text()
        assert '"source": d.get("source") or "(sconosciuta)"' in src

    def test_users_tab_renders_newsletter_source(self):
        src = (FRONTEND_SRC / "features" / "admin"
               / "PlatformUsersTab.js").read_text()
        assert "detail.newsletter?.source" in src

    def test_leads_tab_has_subscriber_list(self):
        src = (FRONTEND_SRC / "features" / "admin" / "LeadsTab.js").read_text()
        assert "nl-admin-subscribers" in src
        assert "listSubscribers" in src


class TestNw4CheckoutCircuit:
    def test_ut1_marketing_from_timestamps(self):
        src = (BACKEND_DIR / "routers" / "admin_platform.py").read_text()
        assert "accepted_marketing_at" in src
        # il flag inesistente non deve piu' guidare la pipeline UT1
        assert '{"$eq": ["$_cust.marketing_opted_in", True]}' not in src

    def test_org_detail_counts_checkout_optins(self):
        src = (BACKEND_DIR / "routers" / "admin_platform.py").read_text()
        assert "checkout_optins" in src
        assert "form_subs + checkout_optins" in src

    def test_org_revoke_updates_form_submissions(self):
        src = (BACKEND_DIR / "routers" / "marketing_consent.py").read_text()
        assert "newsletter_subscriptions" in src
        assert '"status": "unsubscribed"' in src


class TestNw5Gdpr:
    def test_account_export_includes_newsletter(self):
        src = (BACKEND_DIR / "services"
               / "platform_account_service.py").read_text()
        assert '"newsletter": newsletter' in src

    def test_account_delete_removes_subscription(self):
        src = (BACKEND_DIR / "services"
               / "platform_account_service.py").read_text()
        assert "aurya_subscribers.delete_one" in src

    def test_org_hard_delete_covers_newsletter(self):
        src = (BACKEND_DIR / "services" / "hard_delete_service.py").read_text()
        assert "newsletter_forms" in src
        assert "newsletter_subscriptions" in src


class TestNwLiveFlow:
    """Iscrizione estesa → DB strutturato → conferma → disiscrizione.
    Salta se il backend live non risponde (suite anche offline)."""

    email = f"nw-guard-{uuid.uuid4().hex[:8]}@example.com"

    @classmethod
    def teardown_class(cls):
        try:
            import pymongo
            c = pymongo.MongoClient("mongodb://localhost:27017")
            c["retreat_dev"].aurya_subscribers.delete_one(
                {"email": cls.email})
        except Exception:
            pass

    def _live(self):
        try:
            requests.get(f"{BASE_URL}/api/health", timeout=3)
        except Exception:
            pytest.skip("backend live non raggiungibile")

    def test_extended_subscribe_confirm_unsubscribe(self):
        self._live()
        r = requests.post(f"{BASE_URL}/api/public/newsletter/subscribe",
                          json={"email": self.email, "name": "Guardia NW",
                                "source": "newsletter",
                                "wants_experiences": True,
                                "interests": ["yoga", "cerchi", "sbagliato"],
                                "city": "Lecce", "travel": "anywhere",
                                "consent": True}, timeout=10)
        if r.status_code == 429:
            # le suite newsletter insieme superano il 10/min per IP: lo
            # skip si riarma da solo (stesso pattern dei login live)
            pytest.skip("rate limit subscribe (suite in batteria)")
        assert r.status_code == 201, r.text

        import pymongo
        col = pymongo.MongoClient(
            "mongodb://localhost:27017")["retreat_dev"].aurya_subscribers
        doc = col.find_one({"email": self.email})
        assert doc, "iscrizione non salvata"
        assert doc["status"] == "pending"                # double opt-in
        assert doc["source"] == "newsletter"
        assert doc["profile"]["city"] == "Lecce"
        assert doc["profile"]["travel"] == "anywhere"
        assert doc["profile"]["interests"] == ["yoga", "cerchi"]
        assert doc["preferences"]["retreat_alert"]["enabled"] is True

        # token firmato col secret del SERVER, come fa bn2: niente
        # reload di moduli (fragile quando la suite gira in batteria)
        import time
        from jose import jwt
        now_ts = int(time.time())
        tok = jwt.encode(
            {"scope": "newsletter_subscriber", "email": self.email,
             "iat": now_ts, "exp": now_ts + 3600},
            _server_secret(), algorithm="HS256")

        r = requests.post(f"{BASE_URL}/api/public/newsletter/confirm",
                          json={"token": tok}, timeout=10)
        assert r.status_code == 200 and r.json()["status"] == "confirmed"

        r = requests.get(
            f"{BASE_URL}/api/public/newsletter/preferences/{tok}", timeout=10)
        body = r.json()
        assert body["interests"] == ["yoga", "cerchi"]
        assert body["city"] == "Lecce" and body["travel"] == "anywhere"

        r = requests.post(f"{BASE_URL}/api/public/newsletter/unsubscribe",
                          json={"token": tok}, timeout=10)
        assert r.json()["status"] == "unsubscribed"
        assert col.find_one({"email": self.email})["status"] == "unsubscribed"
