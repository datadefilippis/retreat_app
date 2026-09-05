"""Ciclo RV — recensioni consolidate (5/9/2026).

Domande del founder: chiunque può recensire? che differenza c'è fra chi
ha ordinato e chi no? dov'è la pagina dell'operatore? E la decisione:
«se l'operatore ha disabilitato le recensioni da chi non ha ordinato,
chi non ha ordinato non deve nemmeno ricevere l'email».

RV1 — la voce «Recensioni» entra nel menu del mondo snello (viveva solo
      nel menu legacy: nel gestionale sembrava non esistere).
RV2 — il professionista riceve un'email a ogni recensione (verificata:
      «rispondi»; non verificata: «aspetta la tua approvazione»).
RV3 — la porta si chiude PRIMA del codice: recensioni riservate ai
      clienti + email senza prenotazioni = niente codice, una riga di
      cortesia; e il profilo pubblico lo dice prima di chiedere l'email.

I test live usano l'org demo (masseria-demo, reviews_open=False) e il
backend locale su :8000.
"""

import os
import sys
from pathlib import Path

import pytest
import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
BASE = os.environ.get("TEST_API_BASE", "http://localhost:8000/api")

from services import review_service as svc  # noqa: E402


class TestRv1MenuSnello:
    def test_recensioni_nel_menu_snello(self):
        """La plancia /reviews c'era dal ciclo PR3; la voce viveva solo
        nel ramo legacy_commerce. Ora sta nel mondo snello, dopo Profilo
        pubblico."""
        src = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        snello = src.split("if (activeSet.has('commerce') && !legacyCommerce) {")[1] \
            .split("if (activeSet.has('commerce') && legacyCommerce) {")[0]
        assert "nameKey: 'nav.public_profile'" in snello
        assert "nameKey: 'nav.reviews', href: '/reviews'" in snello
        assert snello.index("nav.public_profile") < snello.index("nav.reviews")


class TestRv3PortaOnesta:
    def test_il_servizio_chiude_la_porta_prima_del_codice(self):
        src = (BACKEND_DIR / "services" / "review_service.py").read_text()
        assert "async def _org_accetta(" in src
        assert "def _send_review_closed_email(" in src
        # la porta viene PRIMA della generazione del codice
        blocco = src.split("async def request_review_otp(")[1].split("\n\n\n")[0]
        assert blocco.index("_org_accetta(org, email_n)") \
            < blocco.index('code = f"{secrets.randbelow(1_000_000):06d}"')

    def test_il_profilo_pubblico_lo_dice_prima(self):
        src = (FRONTEND_SRC / "features" / "storefront" / "OperatorProfilePage.js").read_text()
        assert "reviewsOpen={!!data?.reviews_open}" in src
        assert src.count("reviewsOpen={!!data?.reviews_open}") == 2, "modal E sezione"
        assert "landings:reviews.emailIntroClosed" in src
        assert "landings:reviews.emailIntroOpen" in src
        assert 'data-testid="review-email-intro"' in src

    def test_non_cliente_su_org_chiusa_non_riceve_il_codice(self):
        """Live: masseria-demo ha reviews_open=False; un'email senza
        prenotazioni chiede il codice → 202 (nulla trapela) ma NESSUN
        OTP a DB per quell'email."""
        from pymongo import MongoClient
        db = MongoClient(os.environ["MONGO_URL"])[os.environ.get("DB_NAME", "retreat_db")]
        org = db.organizations.find_one({"public_slug": "masseria-demo"},
                                        {"_id": 0, "id": 1, "reviews_open": 1})
        if not org:
            pytest.skip("org demo assente")
        assert not org.get("reviews_open"), "la fixture demo deve avere le recensioni riservate"
        email = "nessuna-prenotazione-rv3@example.com"
        h = svc._email_hash(email)
        prima = db.review_otps.count_documents({"email_hash": h})
        r = requests.post(f"{BASE}/public/reviews/request-otp",
                          json={"org_slug": "masseria-demo", "email": email}, timeout=10)
        assert r.status_code == 202
        assert db.review_otps.count_documents({"email_hash": h}) == prima, \
            "chi non ha prenotato non deve ricevere il codice"

    def test_cliente_riceve_il_codice(self):
        """Live: un'email con un ordine vero presso la demo chiede il
        codice → l'OTP nasce (la porta si apre per chi ha prenotato)."""
        from pymongo import MongoClient
        db = MongoClient(os.environ["MONGO_URL"])[os.environ.get("DB_NAME", "retreat_db")]
        org = db.organizations.find_one({"public_slug": "masseria-demo"}, {"_id": 0, "id": 1})
        if not org:
            pytest.skip("org demo assente")
        ordine = db.orders.find_one(
            {"organization_id": org["id"], "status": {"$nin": ["draft", "cancelled"]},
             "customer_id": {"$ne": None}}, {"_id": 0, "customer_id": 1})
        cliente = ordine and db.customers.find_one(
            {"id": ordine["customer_id"], "organization_id": org["id"]}, {"_id": 0, "email": 1})
        if not cliente or not cliente.get("email"):
            pytest.skip("nessun cliente con ordine nella demo")
        email = cliente["email"]
        h = svc._email_hash(email)
        prima = db.review_otps.count_documents({"email_hash": h})
        r = requests.post(f"{BASE}/public/reviews/request-otp",
                          json={"org_slug": "masseria-demo", "email": email}, timeout=10)
        assert r.status_code == 202
        assert db.review_otps.count_documents({"email_hash": h}) == prima + 1
        # pulizia: il codice di prova non resta a DB
        db.review_otps.delete_many({"email_hash": h, "used_at": None})


class TestRv2IlProfessionistaLoSa:
    def test_email_al_professionista_a_ogni_recensione(self):
        src = (BACKEND_DIR / "services" / "review_service.py").read_text()
        assert "async def _notify_operator_new_review(" in src
        assert "await _notify_operator_new_review(org_id, doc)" in src
        # dopo il salvataggio e le statistiche, mai prima
        assert src.index("await recompute_stats(org_id)\n    await _notify_operator_new_review") > 0
        # verificata → rispondi; non verificata → approvazione, con link alla coda
        assert "/reviews?status=pending" in src
        assert "Nuova recensione da" in src
        assert "aspetta la tua approvazione" in src
