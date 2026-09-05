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
        # i clienti demo sono @example.com: dominio riservato che EmailStr
        # rifiuta (422). Il flusso completo col codice vero e' collaudato
        # dallo script E2E (prestando un'email plausibile); qui si salta.
        if email.lower().rsplit("@", 1)[-1] in ("example.com", "example.org", "test", "localhost"):
            pytest.skip("email demo su dominio riservato: EmailStr la rifiuta")
        h = svc._email_hash(email)
        prima = db.review_otps.count_documents({"email_hash": h})
        r = requests.post(f"{BASE}/public/reviews/request-otp",
                          json={"org_slug": "masseria-demo", "email": email}, timeout=10)
        assert r.status_code == 202
        assert db.review_otps.count_documents({"email_hash": h}) == prima + 1
        # pulizia: il codice di prova non resta a DB
        db.review_otps.delete_many({"email_hash": h, "used_at": None})


class TestRv5LaCodaDelleSegnalazioni:
    """Prima segnalare un abuso era un log: la recensione spariva e
    nessuno la rileggeva. Ora: motivo + email alla piattaforma + coda
    del system admin (/admin/reviews/flagged) + esito al professionista
    via email (ripubblicata o rimossa)."""

    def test_le_parti_ci_sono(self):
        svc_src = (BACKEND_DIR / "services" / "review_service.py").read_text()
        for nome in ("async def flag_review(", "async def list_flagged(",
                     "async def resolve_flag(", "def _send_reviewer_receipt("):
            assert nome in svc_src, nome
        assert "ADMIN_EMAIL" in svc_src, "la piattaforma deve ricevere la segnalazione"
        adm = (BACKEND_DIR / "routers" / "admin.py").read_text()
        assert '"/reviews/flagged"' in adm and '"/reviews/{review_id}/resolve"' in adm
        page = (FRONTEND_SRC / "features" / "admin" / "AdminPage.js").read_text()
        assert "FlaggedReviewsTab" in page and 'value="reviews"' in page
        plancia = (FRONTEND_SRC / "features" / "reviews" / "ReviewsAdminPage.js").read_text()
        assert 'data-testid="review-flag-form"' in plancia
        assert 'data-testid="reviews-settings"' in plancia, "l'interruttore e' una card leggibile"
        assert "viaggiatori" not in plancia

    def test_flusso_live_segnala_coda_decidi(self):
        """Live sulla demo: una recensione pubblicata → l'operatore la
        segnala con un motivo → sparisce dal pubblico, flag_reason a DB
        → il system admin la vede in coda → «restore» la ripubblica.
        Poi «remove» su una seconda → removed. Pulizia finale."""
        from pymongo import MongoClient
        from models.common import generate_id
        db = MongoClient(os.environ["MONGO_URL"])[os.environ.get("DB_NAME", "retreat_db")]
        org = db.organizations.find_one({"public_slug": "masseria-demo"}, {"_id": 0, "id": 1})
        if not org:
            pytest.skip("org demo assente")
        oid = org["id"]
        r_op = requests.post(f"{BASE}/auth/login", json={"email": "admin@demo.com", "password": "demo1234"}, timeout=10)
        r_sa = requests.post(f"{BASE}/auth/login", json={"email": "sysadmin@demo.com", "password": "demo1234"}, timeout=10)
        if r_op.status_code != 200 or r_sa.status_code != 200:
            pytest.skip("login fixture non disponibile (rate limit?)")
        H_op = {"Authorization": f"Bearer {r_op.json()['access_token']}"}
        H_sa = {"Authorization": f"Bearer {r_sa.json()['access_token']}"}
        ids = []
        try:
            for i in range(2):
                rid = generate_id(); ids.append(rid)
                db.reviews.insert_one({
                    "id": rid, "organization_id": oid, "org_slug": "masseria-demo",
                    "author_email_hash": svc._email_hash(f"guardia-rv5-{i}@example.com"),
                    "author_name": "Guardia RV5", "rating": 2, "title": None,
                    "body": "Recensione di collaudo per la coda delle segnalazioni, testo lungo.",
                    "verified": True, "status": "published", "reply": None, "lang": "it",
                    "created_at": "2026-09-05T10:00:00", "updated_at": "2026-09-05T10:00:00",
                    "edited": False})
            # 1) l'operatore segnala con un motivo
            r = requests.post(f"{BASE}/reviews/{ids[0]}/flag", headers=H_op,
                              json={"reason": "persona mai venuta"}, timeout=10)
            assert r.status_code == 200, r.text
            doc = db.reviews.find_one({"id": ids[0]})
            assert doc["status"] == "flagged" and doc["flag_reason"] == "persona mai venuta"
            pub = requests.get(f"{BASE}/public/reviews/masseria-demo", timeout=10).json()
            assert not any(x["id"] == ids[0] for x in pub["items"]), "segnalata: fuori dal pubblico"
            # 2) il system admin la vede in coda, l'operatore no (403)
            assert requests.get(f"{BASE}/admin/reviews/flagged", headers=H_op, timeout=10).status_code == 403
            coda = requests.get(f"{BASE}/admin/reviews/flagged", headers=H_sa, timeout=10)
            assert coda.status_code == 200
            voce = next((x for x in coda.json()["items"] if x["id"] == ids[0]), None)
            assert voce and voce["org_name"] and "author_email_hash" not in voce
            # 3) restore → torna pubblica
            r = requests.patch(f"{BASE}/admin/reviews/{ids[0]}/resolve", headers=H_sa,
                               json={"action": "restore", "note": "nessuna violazione"}, timeout=10)
            assert r.status_code == 200 and r.json()["status"] == "published"
            doc = db.reviews.find_one({"id": ids[0]})
            assert doc["status"] == "published" and doc["resolution"]["action"] == "restore"
            # 4) remove sulla seconda
            requests.post(f"{BASE}/reviews/{ids[1]}/flag", headers=H_op, json={}, timeout=10)
            r = requests.patch(f"{BASE}/admin/reviews/{ids[1]}/resolve", headers=H_sa,
                               json={"action": "remove"}, timeout=10)
            assert r.status_code == 200 and r.json()["status"] == "removed"
            # una decisione non si ripete
            assert requests.patch(f"{BASE}/admin/reviews/{ids[1]}/resolve", headers=H_sa,
                                  json={"action": "restore"}, timeout=10).status_code == 404
        finally:
            db.reviews.delete_many({"id": {"$in": ids}})
            import asyncio
            asyncio.run(svc.recompute_stats(oid))


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
