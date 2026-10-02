"""RC1-RC2 (2/10/2026 sera) — il Cerchio dalla recensione.

Una casella facoltativa nel passo «form», UN solo invio: la recensione si
salva come oggi, poi (solo se `cerchio`) l'iscrizione best-effort con la
prova OTP (entra confermata, niente seconda email). La risposta aggiunge
`cerchio` e tiene le tre chiavi di sempre. Il «grazie» resta il titolo.
Piano: docs/PIANO_RECENSIONE_CERCHIO_2026-10-02.md
"""
import os
import time
from datetime import timedelta
from pathlib import Path

import pytest
import requests

RADICE = Path(__file__).resolve().parents[2]
BACKEND = RADICE / "backend"
FE = RADICE / "frontend" / "src"
BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000") + "/api"
ROUTER = (BACKEND / "routers" / "reviews.py").read_text(encoding="utf-8")
PAGINA = (FE / "features" / "storefront" / "OperatorProfilePage.js").read_text(encoding="utf-8")


class TestSorgente:
    def test_backend_ordine_e_isolamento(self):
        from routers.reviews import ReviewSubmit
        campi = ReviewSubmit.model_fields
        assert not campi["cerchio"].is_required() and campi["cerchio"].default is False
        assert not campi["consenso_versione"].is_required()
        blocco = ROUTER[ROUTER.index("async def review_submit("):ROUTER.index('@router.get("/public/reviews/{org_slug}")')]
        # prima la recensione (e il suo errore di sempre), POI il Cerchio, dentro l'helper che non alza mai
        assert blocco.index("review = await submit_review(") < blocco.index("_cerchio_dalla_recensione(")
        assert 'if body.cerchio:' in blocco and '"cerchio": esito_cerchio' in blocco
        assert '"status": review["status"], "verified": review["verified"]' in blocco   # le tre chiavi di sempre
        helper = ROUTER[ROUTER.index("async def _cerchio_dalla_recensione("):ROUTER.index("@router.post(\"/public/reviews/submit\")")]
        assert "gia_verificato=True" in helper and 'segna_verificato(email, "otp"' in helper
        assert 'source="recensione"' in helper and "unlock_flow=True" in helper    # mai un magic link in piu'
        assert "except Exception" in helper and "return None" in helper
        from services.provenienza import classifica
        assert classifica("recensione") == {"canale": "sito", "superficie": "recensione"} or \
            (classifica("recensione").get("canale"), classifica("recensione").get("superficie")) == ("sito", "recensione")

    def test_modal_una_casella_un_invio_il_grazie_resta(self):
        modal = PAGINA[PAGINA.index("function WriteReviewModal("):PAGINA.index("function ReviewsSection(")]
        assert "const [cerchio, setCerchio] = useState(false);" in modal          # non preselezionata
        assert 'data-testid="review-cerchio"' in modal and "testoConsenso().testo" in modal
        assert "cerchio, consenso_versione: cerchio ? testoConsenso().versione : null" in modal
        assert modal.count("api.post('/public/reviews/submit'") == 1 and "api.post('/public/newsletter/subscribe'" not in modal
        assert "setEsitoCerchio(r?.data?.cerchio || null)" in modal
        assert "landings:reviews.thanks" in modal and 'data-testid="review-cerchio-esito"' in modal
        # la riga di esito viene DOPO il grazie e solo se c'e' un esito
        assert modal.index("landings:reviews.thanks") < modal.index('data-testid="review-cerchio-esito"')
        assert "{esitoCerchio && (" in modal
        import json
        for lang in ("it", "en", "de", "fr"):
            d = json.loads((FE / "locales" / lang / "landings.json").read_text(encoding="utf-8"))
            assert d["reviews"]["cerchioIscritto"] and d["reviews"]["cerchioGiaDentro"], lang
        it = json.loads((FE / "locales" / "it" / "landings.json").read_text(encoding="utf-8"))["reviews"]
        assert it["thanks"] == "Grazie della tua recensione!"                      # il titolo non cambia


class TestDalVivo:
    """Sul backend locale: si forgia un OTP valido (come fa il servizio),
    si apre l'operatore demo alle recensioni per il tempo del test, e si
    guarda cosa succede con e senza casella. Tutto ripulito alla fine."""

    def test_con_e_senza_casella(self):
        try:
            if requests.get(f"{BASE}/health", timeout=5).status_code != 200:
                pytest.skip("backend locale spento")
        except Exception:
            pytest.skip("backend locale spento")
        from pymongo import MongoClient
        from services import review_service as svc
        from models.common import generate_id
        from datetime import datetime, timezone
        db = MongoClient(os.environ["MONGO_URL"])[os.environ.get("DB_NAME", "retreat_db")]
        org = db.organizations.find_one({"public_slug": "masseria-demo"}, {"_id": 0, "id": 1, "reviews_open": 1})
        if not org:
            pytest.skip("org demo assente")
        slug = "masseria-demo"
        stamp = int(time.time())
        e_si, e_no = f"rc-si-{stamp}@example.com", f"rc-no-{stamp}@example.com"

        def otp(email, code):
            db.review_otps.insert_one({
                "id": generate_id(), "org_slug": slug, "email_hash": svc._email_hash(email),
                "code_hash": svc._hash_code(code), "attempts": 0, "used_at": None,
                "expires_at": svc._iso(datetime.now(timezone.utc) + timedelta(minutes=10)),
                "created_at": svc._iso(datetime.now(timezone.utc))})

        def submit(email, code, **extra):
            return requests.post(f"{BASE}/public/reviews/submit", json={
                "org_slug": slug, "email": email, "code": code, "rating": 5,
                "body": "Recensione di collaudo per il Cerchio dalla recensione, testo lungo abbastanza.",
                "author_name": "Guardia RC", "language": "it", "website": "", **extra}, timeout=15)

        aperto_prima = bool(org.get("reviews_open"))
        try:
            db.organizations.update_one({"id": org["id"]}, {"$set": {"reviews_open": True}})
            # 1) codice sbagliato: l'errore di sempre, anche con la casella
            otp(e_si, "111111")
            r = submit(e_si, "222222", cerchio=True)
            if r.status_code == 429:
                pytest.skip("submit a 5/minuto: il test e' gia' girato da poco")
            assert r.status_code == 400 and r.json()["detail"]["error"] == "invalid_code"
            assert db.aurya_subscribers.find_one({"email": e_si}) is None      # niente iscrizione senza recensione
            # 2) con la casella: recensione + iscritto confermato con prova otp
            r = submit(e_si, "111111", cerchio=True, consenso_versione="cerchio-v3")
            assert r.status_code == 200, r.text
            d = r.json()
            assert set(d) >= {"status", "verified", "id"} and d["cerchio"] == "iscritto"
            sub = db.aurya_subscribers.find_one({"email": e_si})
            assert sub and sub["status"] == "confirmed" and sub["source"] == "recensione"
            assert sub["verificato_da"]["tipo"] == "otp" and sub["verificato_da"]["dettaglio"] == f"recensione:{slug}"
            assert sub["provenienza"]["superficie"] == "recensione" and sub["consenso"]["versione"] == "cerchio-v3"
            # 3) senza casella (payload di oggi): identico a oggi, nessun iscritto
            otp(e_no, "333333")
            r = submit(e_no, "333333")
            assert r.status_code == 200 and r.json()["cerchio"] is None
            assert db.aurya_subscribers.find_one({"email": e_no}) is None
            assert db.reviews.count_documents({"organization_id": org["id"],
                                               "author_email_hash": {"$in": [svc._email_hash(e_si), svc._email_hash(e_no)]}}) == 2
        finally:
            db.organizations.update_one({"id": org["id"]}, {"$set": {"reviews_open": aperto_prima}})
            db.reviews.delete_many({"author_email_hash": {"$in": [svc._email_hash(e_si), svc._email_hash(e_no)]}})
            db.review_otps.delete_many({"email_hash": {"$in": [svc._email_hash(e_si), svc._email_hash(e_no)]}})
            db.aurya_subscribers.delete_many({"email": {"$in": [e_si, e_no]}})
            db.consent_audit.delete_many({"email": {"$in": [e_si, e_no]}})
