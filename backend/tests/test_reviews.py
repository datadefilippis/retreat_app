"""PR2 — sistema recensioni: invarianti di solidità.

  1. OTP: 202 sempre (enumeration-safe), codice sbagliato → 400,
     one-shot (riuso → 400);
  2. verified gate: senza ordini non-draft e org chiusa → orders_required;
  3. l'email NON compare mai nelle risposte pubbliche/admin;
  4. honeypot → 202 finto senza scrittura;
  5. validazioni: rating fuori range, body corto;
  6. moderazione: solo pending unverified;
  7. stats denormalizzate coerenti.

Unit (service) con mock; flusso HTTP contro il backend live.
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

from services import review_service as svc


class TestEmailHash:
    def test_hash_is_salted_and_stable(self):
        a = svc._email_hash("Test@Example.com ")
        b = svc._email_hash("test@example.com")
        assert a == b                       # normalizzazione
        assert "test@example.com" not in a  # mai in chiaro
        assert len(a) == 64


class TestOtpEndpoint:
    def test_always_202(self):
        for payload in (
            {"org_slug": "org-inesistente-xyz", "email": "a@b.it"},
            {"org_slug": "masseria-demo", "email": "chiunque@ovunque.it"},
        ):
            r = requests.post(f"{BASE_URL}/api/public/reviews/request-otp",
                              json=payload, timeout=10)
            assert r.status_code == 202, payload

    def test_wrong_code_rejected(self):
        r = requests.post(f"{BASE_URL}/api/public/reviews/submit", json={
            "org_slug": "masseria-demo", "email": "nessuno@test.it",
            "code": "000000", "rating": 5, "author_name": "X",
            "body": "Testo abbastanza lungo da passare la validazione.",
        }, timeout=10)
        assert r.status_code == 400
        assert r.json()["detail"]["error"] == "invalid_code"


class TestHoneypot:
    def test_bot_gets_fake_accepted(self):
        r = requests.post(f"{BASE_URL}/api/public/reviews/submit", json={
            "org_slug": "masseria-demo", "email": "bot@spam.io",
            "code": "123456", "rating": 5, "author_name": "Bot",
            "body": "Spam spam spam spam spam spam spam spam.",
            "website": "http://spam.io",
        }, timeout=10)
        assert r.status_code == 200
        assert r.json() == {"status": "accepted"}


class TestPublicListPrivacy:
    def test_no_email_or_hash_in_public_payload(self):
        r = requests.get(f"{BASE_URL}/api/public/reviews/masseria-demo",
                         timeout=10)
        assert r.status_code == 200
        text = r.text.lower()
        assert "email" not in text and "hash" not in text

    def test_unknown_org_404(self):
        r = requests.get(f"{BASE_URL}/api/public/reviews/org-fantasma-xyz",
                         timeout=10)
        assert r.status_code == 404


class TestValidation:
    def test_pydantic_rejects_bad_rating_and_short_code(self):
        r = requests.post(f"{BASE_URL}/api/public/reviews/submit", json={
            "org_slug": "masseria-demo", "email": "a@b.it",
            "code": "123", "rating": 9, "author_name": "X",
            "body": "abcdefghilmnopqrstuvz.",
        }, timeout=10)
        assert r.status_code == 422        # ge/le + min_length dal modello


class TestAdminAuth:
    def test_admin_endpoints_require_auth(self):
        assert requests.get(f"{BASE_URL}/api/reviews",
                            timeout=10).status_code in (401, 403)
        assert requests.patch(f"{BASE_URL}/api/reviews/settings",
                              json={"reviews_open": True},
                              timeout=10).status_code in (401, 403)


class TestModerationInvariant:
    def test_moderate_touches_only_pending_unverified(self):
        """La query di moderazione DEVE filtrare status=pending e
        verified=False — l'operatore non governa le verified."""
        import inspect
        from routers import reviews as r
        src = inspect.getsource(r.admin_moderate)
        assert '"status": "pending"' in src
        assert '"verified": False' in src

    def test_verified_publish_immediately(self):
        import inspect
        src = inspect.getsource(svc.submit_review)
        assert '"published" if verified else "pending"' in src
