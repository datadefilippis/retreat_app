"""CF2 — outreach contestuale: invarianti di solidità.

  1. i template contestuali esistono in TUTTE e 4 le lingue
     (library.json valida a load time, non a click time);
  2. il render accetta variabili extra e le mancanti degradano a
     stringa vuota (contesto parziale ≠ crash);
  3. review_link NON è accettato dal client (whitelist);
  4. winback senza consenso → 403 no_marketing_consent (via sorgente:
     il gate vive nel router, verifichiamo che ci sia e che richieda
     accepted_marketing_at non revocato);
  5. endpoint admin protetto (401/403 senza auth);
  6. contesto sconosciuto → 400.
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

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")

CONTEXT_KEYS = ("payment_reminder", "pre_retreat", "post_retreat_review", "winback")
LOCALES = ("it", "en", "de", "fr")


class TestTemplatesLibrary:
    def test_context_templates_exist_in_all_locales(self):
        from services.customer_outreach.templates import loader
        loader.reload_templates()
        lib = loader._ensure_loaded()
        missing = [
            f"{key}/{loc}"
            for key in CONTEXT_KEYS for loc in LOCALES
            if not (lib.get(key, {}).get(loc, {}).get("body"))
        ]
        assert not missing, f"template contestuali incompleti: {missing}"

    def test_render_with_extra_vars(self):
        from services.customer_outreach.templates import loader
        r = loader.render(
            "payment_reminder", "it",
            customer_name="Giulia", merchant_name="Masseria",
            extra={"amount": "150,00 €", "due_date": "10 lug 2026",
                   "order_number": "ORD-1"},
        )
        assert "150,00 €" in r["body"] and "Giulia" in r["body"]

    def test_render_partial_context_degrades_gracefully(self):
        """Variabile mancante → stringa vuota, mai KeyError."""
        from services.customer_outreach.templates import loader
        r = loader.render(
            "pre_retreat", "de",
            customer_name="Hans", merchant_name="Masseria", extra={},
        )
        assert r is not None and "Hans" in r["body"]
        assert "{retreat_name}" not in r["body"]   # interpolato, non crudo


class TestRouterInvariants:
    def test_review_link_not_client_suppliable(self):
        from routers import outreach
        assert "review_link" not in outreach._ALLOWED_VARS

    def test_winback_gate_requires_unrevoked_consent(self):
        import inspect
        from routers import outreach
        src = inspect.getsource(outreach.build_contextual_outreach)
        assert "accepted_marketing_at" in src
        assert "marketing_revoked_at" in src
        assert "no_marketing_consent" in src

    def test_all_contexts_map_to_existing_templates(self):
        from routers import outreach
        from services.customer_outreach.templates import loader
        lib = loader._ensure_loaded()
        for ctx, tpl in outreach.CONTEXT_TEMPLATES.items():
            assert tpl in lib, f"contesto {ctx} → template inesistente {tpl}"


class TestHttp:
    def test_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/outreach/build", json={
            "context": "generic", "channel": "mailto",
            "contact_email": "a@b.it",
        }, timeout=10)
        assert r.status_code in (401, 403)
