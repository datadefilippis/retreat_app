"""BN2 — iscritti alla lettera di Aurya: double opt-in e preferenze.

Contratto sotto guardia:
  1. token firmato: roundtrip, scope isolato (un JWT di login non passa),
     email canonicalizzata;
  2. sanificazione preferenze: topics solo dalle categorie editoriali
     (mai 'operatori'), regioni solo italiane, scope valido;
  3. flusso live: subscribe → pending, confirm → confirmed, update
     preferenze, unsubscribe → unsubscribed (idempotente);
  4. il frontend usa la strada subscribe (double opt-in) per la lettera
     e il grazie dice "controlla la posta", non "sei iscritto".
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


def _server_secret() -> str:
    """Il flusso live firma token che il SERVER deve verificare: il
    secret va letto da backend/.env, NON da os.environ (conftest fissa
    il fallback di test prima che dotenv possa caricare quello vero)."""
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("JWT_SECRET_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ["JWT_SECRET_KEY"]

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"


class TestSubscriberToken:
    def test_roundtrip_canonicalises_email(self):
        from core.subscriber_token import (decode_subscriber_token,
                                           generate_subscriber_token)
        tok = generate_subscriber_token("  Mario.Rossi@Example.COM ")
        assert decode_subscriber_token(tok)["email"] == "mario.rossi@example.com"

    def test_scope_isolation(self):
        from core.marketing_unsubscribe_token import (
            TokenInvalidError, generate_marketing_unsubscribe_token)
        from core.subscriber_token import decode_subscriber_token
        other = generate_marketing_unsubscribe_token(
            email="a@b.it", organization_id="org1")
        with pytest.raises(TokenInvalidError):
            decode_subscriber_token(other)

    def test_expired_token(self):
        from core.marketing_unsubscribe_token import TokenExpiredError
        from core.subscriber_token import (decode_subscriber_token,
                                           generate_subscriber_token)
        tok = generate_subscriber_token("a@b.it", ttl_days=-1)
        with pytest.raises(TokenExpiredError):
            decode_subscriber_token(tok)


class TestPreferenceSanitisation:
    def test_topics_exclude_operatori(self):
        from routers.subscribers import _clean_topics, subscriber_topics
        assert "operatori" not in subscriber_topics()
        assert "energia" in subscriber_topics()
        assert _clean_topics(["yoga", "operatori", "inventata", "yoga"]) == ["yoga"]

    def test_alert_clean(self):
        from routers.subscribers import _clean_alert
        got = _clean_alert({"enabled": 1, "scope": "marte",
                            "regions": ["puglia", "narnia", "puglia"]})
        assert got == {"enabled": True, "scope": "italy",
                       "regions": ["puglia"]}

    def test_regions_are_twenty(self):
        from routers.subscribers import ITALIAN_REGIONS
        assert len(ITALIAN_REGIONS) == 20


class TestLiveFlow:
    """Contro il backend live (stesso pattern di TestEndpointLive)."""

    EMAIL = "bn2-flow@test.aurya"

    def _token(self):
        import time

        from jose import jwt
        now = int(time.time())
        return jwt.encode(
            {"scope": "newsletter_subscriber", "email": self.EMAIL,
             "iat": now, "exp": now + 3600},
            _server_secret(), algorithm="HS256")

    def test_full_lifecycle(self):
        # subscribe → risposta generica, mai oracolo
        r = requests.post(f"{BASE_URL}/api/public/newsletter/subscribe",
                          json={"email": self.EMAIL, "consent": True,
                                "source": "blog_yoga",
                                "topics": ["yoga", "operatori"]},
                          timeout=10)
        assert r.status_code == 201 and r.json() == {"ok": True}

        # confirm col token firmato
        r = requests.post(f"{BASE_URL}/api/public/newsletter/confirm",
                          json={"token": self._token()}, timeout=10)
        assert r.status_code == 200 and r.json()["status"] == "confirmed"

        # preferenze: lette e aggiornate
        r = requests.get(
            f"{BASE_URL}/api/public/newsletter/preferences/{self._token()}",
            timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "confirmed"
        assert body["topics"] == ["yoga"]          # 'operatori' filtrato
        assert "operatori" not in body["available_topics"]
        assert "@" in body["email_masked"] and self.EMAIL != body["email_masked"]

        r = requests.put(f"{BASE_URL}/api/public/newsletter/preferences",
                         json={"token": self._token(),
                               "topics": ["meditazione"],
                               "format": "practices",
                               "retreat_alert": {"enabled": True,
                                                 "scope": "regions",
                                                 "regions": ["puglia"]}},
                         timeout=10)
        assert r.status_code == 200
        r = requests.get(
            f"{BASE_URL}/api/public/newsletter/preferences/{self._token()}",
            timeout=10)
        assert r.json()["format"] == "practices"
        assert r.json()["retreat_alert"]["regions"] == ["puglia"]

        # unsubscribe: un click, idempotente
        for _ in range(2):
            r = requests.post(f"{BASE_URL}/api/public/newsletter/unsubscribe",
                              json={"token": self._token()}, timeout=10)
            assert r.status_code == 200
            assert r.json()["status"] == "unsubscribed"

    def test_invalid_token_is_401(self):
        r = requests.post(f"{BASE_URL}/api/public/newsletter/confirm",
                          json={"token": "spazzatura"}, timeout=10)
        assert r.status_code == 401


class TestFrontendWiringBN2:
    LEADFORM = (FRONTEND_SRC / "features" / "prelaunch"
                / "LeadForm.jsx").read_text()
    CTA = (FRONTEND_SRC / "features" / "storefront" / "components"
           / "BlogNewsletterCTA.jsx").read_text()
    NL = (FRONTEND_SRC / "features" / "prelaunch"
          / "NewsletterLandingPage.js").read_text()
    APP = (FRONTEND_SRC / "App.js").read_text()

    def test_subscribe_path_used_by_letter_surfaces(self):
        assert "/public/newsletter/subscribe" in self.LEADFORM
        assert "subscribe" in self.CTA and "thanksDoi" in self.CTA
        assert "subscribe" in self.NL and "thanksDoi" in self.NL

    def test_token_pages_routed(self):
        assert '/newsletter/conferma/:token' in self.APP
        assert '/newsletter/preferenze/:token' in self.APP

    def test_operator_module_moved_off_public_path(self):
        # /newsletter e' del pubblico: il back-office vive altrove
        assert '"/newsletter-forms"' in self.APP
        layout = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "'/newsletter-forms'" in layout
        assert "href: '/newsletter'," not in layout


class TestBrevoSyncBN6:
    """BN6 — sync Brevo: attributi coerenti, blacklist sui disiscritti,
    best-effort (mai un raise verso l'utente), stats admin protette."""

    def test_attribute_mapping(self):
        from services.subscriber_brevo_sync import _attributes
        doc = {"status": "confirmed", "source": "blog_yoga",
               "language": "it",
               "preferences": {"topics": ["yoga", "suono"],
                               "format": "practices",
                               "retreat_alert": {"enabled": True,
                                                 "scope": "regions",
                                                 "regions": ["puglia"]}}}
        got = _attributes(doc)
        assert got["AURYA_STATUS"] == "confirmed"
        assert got["AURYA_TOPICS"] == "yoga,suono"
        assert got["AURYA_FORMAT"] == "practices"
        assert got["AURYA_ALERT"] == "puglia"
        assert got["AURYA_SOURCE"] == "blog_yoga"

    def test_alert_off_and_italy(self):
        from services.subscriber_brevo_sync import _attributes
        assert _attributes({})["AURYA_ALERT"] == "off"
        got = _attributes({"preferences": {"retreat_alert":
                                           {"enabled": True,
                                            "scope": "italy"}}})
        assert got["AURYA_ALERT"] == "italy"

    def test_sync_hooked_on_state_changes(self):
        src = (BACKEND_DIR / "routers" / "subscribers.py").read_text()
        # conferma, preferenze e unsubscribe riflettono su Brevo
        assert src.count("sync_subscriber_background(email)") >= 3

    def test_stats_requires_system_admin(self):
        import requests as rq
        r = rq.get(f"{BASE_URL}/api/admin/newsletter-stats", timeout=10)
        assert r.status_code in (401, 403)


class TestAccessMagicLink:
    """Founder 27/7 — l'iscritto GIA' confermato che rimette la email
    (nuovo dispositivo, gate di una guida) riceve il magic link di
    accesso, non silenzio. La risposta HTTP resta identica (nessun
    oracolo di enumerazione)."""

    def test_confirmed_resubscribe_sends_access_email(self):
        src = (BACKEND_DIR / "routers" / "subscribers.py").read_text()
        confirmed_branch = src.split('existing.get("status") == "confirmed"')[1]
        confirmed_branch = confirmed_branch.split("# nuovo, pending")[0]
        assert "_send_access_email(" in confirmed_branch
        assert 'return {"ok": True}' in confirmed_branch
        # il magic link porta il return_to (si torna alla guida)
        assert "_safe_return_to(payload.return_to)" in confirmed_branch

    def test_gate_copy_tells_new_device_flow(self):
        """Chi e' gia' iscritto deve avere una strada che NON sia
        riiscriversi. Guardia sul significato, non sulla frase: dal
        ciclo NL-septies la strada e' il modulo di sblocco (che chiama
        /public/newsletter/unlock); prima era solo il magic link. Se un
        domani cambia di nuovo, deve restare vero che il gate nomina il
        caso «gia' iscritto» e offre un'azione sua."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "BlogArticlePage.js").read_text()
        assert "già iscritto" in page.lower()
        assert 'data-testid="blog-gate-already"' in page
        assert "/public/newsletter/unlock" in page
        assert "dispositivo" in page      # il caso raccontato e' quello
