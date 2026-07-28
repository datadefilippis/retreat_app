"""TW1 — il Listino (docs/LISTINO_PIANO_2026-07.md) + INVARIANTI.

Il listino e' un'interfaccia NUOVA sopra il motore VECCHIO: queste
guardie assicurano che resti cosi'. TestInvariants e' il contratto
anti-sfascio della Parte 0 del piano: se un'onda TW lo rompe, si
torna indietro.
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
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"


class TestInvariants:
    """Parte 0 del piano: cio' che il Listino NON deve mai toccare."""

    def test_i1_event_landing_alive(self):
        # la landing evento resta la pagina di vendita completa
        r = requests.get(f"{BASE_URL}/__seo/e/masseria-demo/"
                         "ritiro-yoga-test-s1-2026-10-02", timeout=10)
        assert r.status_code == 200

    def test_i1_service_landing_alive(self):
        # /p/ resta vivo (retrocompatibilita' + slot picker)
        app = (FRONTEND_SRC / "App.js").read_text()
        assert '/p/:orgSlug' in app or 'path="/p/' in app

    def test_i2_i3_checkout_untouched(self):
        """Il listino non riscrive il checkout: le firme chiave del
        motore ordini/booking restano al loro posto."""
        occ = (BACKEND_DIR / "services" / "order_creation_service.py").read_text()
        assert "dominant_mode" in occ
        bs = (BACKEND_DIR / "services" / "booking_service.py").read_text()
        assert "issue_bookings_for_order" in bs

    def test_i4_slot_engine_untouched(self):
        sg = (BACKEND_DIR / "services" / "slot_generator.py").read_text()
        assert "generate_available_slots" in sg

    def test_i8_no_new_collection(self):
        """Una riga di listino E' un Product service: la pagina usa la
        API products, nessuna collection nuova."""
        page = (FRONTEND_SRC / "features" / "listino"
                / "ListinoPage.js").read_text()
        assert "productsAPI.create" in page
        assert "productsAPI.update" in page
        assert "item_type: 'service'" in page

    def test_store_guard_source_unchanged(self):
        """Il gate store-first NON e' stato ammorbidito: il listino lo
        soddisfa creando lo store tecnico, non aggirandolo."""
        sg = (BACKEND_DIR / "services" / "store_guard.py").read_text()
        assert "store_required" in sg
        assert "require_public_home" in sg


class TestListinoTW1:
    def test_ensure_default_endpoint_exists(self):
        src = (BACKEND_DIR / "routers" / "stores.py").read_text()
        assert '"/ensure-default"' in src
        assert "_ensure_default_store(org_id, current_user)" in src

    def test_ensure_default_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/stores/ensure-default", timeout=10)
        assert r.status_code in (401, 403)

    def test_listino_defaults_are_lean(self):
        """Default snelli: richiesta (niente Stripe richiesto), agenda
        ufficiale (nessuna regola custom), pubblicato subito."""
        page = (FRONTEND_SRC / "features" / "listino"
                / "ListinoPage.js").read_text()
        assert "transaction_mode: 'request'" in page
        assert "is_published: true" in page
        # lo store tecnico si garantisce PRIMA di pubblicare
        assert "storesAPI.ensureDefault()" in page

    def test_services_new_redirects_to_listino(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/listino"' in app
        block = app.split('path="/services/new"')[1][:120]
        assert 'Navigate to="/listino"' in block
        # il wizard resta l'editor avanzato su /services/:id
        assert 'path="/services/:product_id"' in app

    def test_nav_has_listino(self):
        layout = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "'/listino'" in layout
