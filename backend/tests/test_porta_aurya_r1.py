"""R1 (25/9/2026 sera) — la PORTA UNICA dell'account cliente, con password.

Piano docs/ANALISI_REGISTRAZIONE_OBBLIGATORIA_2026-09-25.md. Decisione del
founder: l'account si CREA con una password (mai «senza»); l'accesso resta
email+password col codice come ripiego.

  - PortaAurya.jsx: viste entra/codice/crea/inviata; nella «crea» la casella
    legale (accepted_terms) e la casella del Cerchio SEPARATA e SPENTA con il
    testo versionato; nessun submit del form padre;
  - AuryaQuickLogin monta la porta in vista «crea» («Non ce l'hai? Crealo»);
  - backend: l'email dell'account appena PROVATA (verify-email, codice, magic
    link) conferma l'iscrizione al Cerchio in attesa (segna_verificato tipo
    «account»); con LOGIN_SENZA_VERIFICA acceso il signup risponde gia' con
    la sessione e il login/le sessioni valgono prima del clic; spento, tutto
    come prima. L'export GDPR resta rigido. Il profilo ha `city`.
"""
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

RADICE = Path(__file__).resolve().parents[2]
BACKEND = RADICE / "backend"
FE = RADICE / "frontend" / "src"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")

PORTA = (FE / "features" / "account" / "PortaAurya.jsx").read_text(encoding="utf-8")
QUICK = (FE / "features" / "storefront" / "components" / "checkout" / "AuryaQuickLogin.jsx").read_text(encoding="utf-8")
ROUTER = (BACKEND / "routers" / "platform_accounts.py").read_text(encoding="utf-8")
SERVICE = (BACKEND / "services" / "platform_account_service.py").read_text(encoding="utf-8")
AUTH = (BACKEND / "auth.py").read_text(encoding="utf-8")


class TestPortaFrontend:
    def test_la_porta_crea_con_password_e_caselle_separate(self):
        assert "vista: vistaIniziale = 'entra'" in PORTA
        for v in ("porta-aurya-entra", "porta-aurya-crea", "porta-aurya-inviata"):
            assert f'data-testid="{v}"' in PORTA, v
        # 26/9 (founder): solo account veri con password — niente codice nella porta
        for v in ("porta-aurya-codice", "porta-aurya-vai-codice"):
            assert f'data-testid="{v}"' not in PORTA, v
        assert "/platform/auth/magic-link" not in PORTA and "code/verify" not in PORTA
        for v in ():
            assert f'data-testid="{v}"' in PORTA, v
        # crea → signup con password, legale obbligatoria, Cerchio separato e spento
        blocco = PORTA.split("const crea = async")[1].split("};")[0]
        assert "platformApi.post('/platform/auth/signup'" in blocco
        assert "accepted_terms: true" in blocco and "wants_newsletter: !!cerchio" in blocco
        assert "consenso_versione: VERSIONE_CORRENTE" in blocco
        assert "if (!emailOk || !passwordValida(password) || !legale) return;" in blocco
        assert "const [legale, setLegale] = useState(false);" in PORTA
        assert "const [cerchio, setCerchio] = useState(false);" in PORTA
        assert "{testoConsenso().testo}" in PORTA
        assert 'data-testid="porta-aurya-legale"' in PORTA and 'data-testid="porta-aurya-cerchio"' in PORTA
        # le 4 regole della password sono quelle di AccountLoginPage
        assert "p.length >= 12" in PORTA and "/[a-z]/" in PORTA and "/[A-Z]/" in PORTA and "/\\d/" in PORTA
        # E6 acceso → dentro subito; spento → «ti abbiamo scritto»
        assert "if (res.data?.access_token) await apri(res);" in PORTA and "else setVista('inviata');" in PORTA
        # mai un submit del form padre: ogni bottone e' type=button e Enter e' intercettato
        assert 'type="submit"' not in PORTA and "e.preventDefault(); fn(e);" in PORTA
        # vie di uscita: entra con password e recupero (vista giusta di /accedi)
        assert "/accedi?vista=recupero" in PORTA

    def test_il_pannello_del_checkout_monta_la_porta(self):
        assert "import PortaAurya from '../../../account/PortaAurya';" in QUICK
        assert 'data-testid="aurya-login-crea"' in QUICK
        assert '<PortaAurya vista="crea" emailIniziale={email} contesto="checkout"' in QUICK
        # le fasi di accesso esistenti restano intatte (AP1/AP1b)
        for tid in ("aurya-login-open", "aurya-login-send", "aurya-login-code", "aurya-login-password", "aurya-login-greeting"):
            assert f'data-testid="{tid}"' in QUICK, tid


class TestBackend:
    def test_l_email_provata_conferma_il_cerchio(self):
        assert SERVICE.count("_conferma_cerchio_per_uso(") == 4     # def + verify-email + codice + magic-link
        assert '"account"' in (BACKEND / "services" / "verifica_email.py").read_text(encoding="utf-8").split("TIPI = (")[1].split(")")[0]
        assert 'await segna_verificato(email, "account", dettaglio)' in SERVICE
        for d in ('"verify-email"', '"codice"', '"magic-link"'):
            assert f"_conferma_cerchio_per_uso(account[\"email\"], {d})" in SERVICE, d

    def test_e6_esteso_ai_clienti_ma_export_rigido(self):
        assert "if not account.get(\"email_verified\", False) and not login_senza_verifica():" in SERVICE
        blocco = AUTH[AUTH.index("async def get_current_platform_account("):]
        assert "if not login_senza_verifica():" in blocco.split("async def get_current_platform_account_strict")[0]
        assert "async def get_current_platform_account_strict(" in AUTH
        assert "Depends(get_current_platform_account_strict)" in ROUTER.split("async def export_my_data")[1][:200]
        # signup: sessione nella risposta SOLO col flag
        blocco = ROUTER[ROUTER.index("async def password_signup_ep"):][:3200]
        assert "if login_senza_verifica():" in blocco and '"verifica_morbida": True' in blocco
        assert "return out" in blocco

    def test_flag_spento_di_default_e_login_rigido(self, monkeypatch):
        monkeypatch.delenv("LOGIN_SENZA_VERIFICA", raising=False)
        from core.flags import login_senza_verifica
        assert login_senza_verifica() is False
        monkeypatch.setenv("LOGIN_SENZA_VERIFICA", "1")
        assert login_senza_verifica() is True

    def test_profilo_con_city(self):
        assert "city: Optional[str] = Field(None, max_length=80)" in ROUTER
        assert '"id", "email", "name", "phone", "city", "language"' in ROUTER


class TestDalVivo:
    def test_signup_con_password_iscrive_al_cerchio_in_attesa_e_il_login_resta_rigido(self):
        """Flag spento in locale: 202 + Cerchio pending con provenienza;
        login → 403 EMAIL_NOT_VERIFIED. Poi si pulisce."""
        import time
        email = f"porta-r1-{int(time.time())}@example.com"
        r = requests.post(f"{BASE_URL}/api/platform/auth/signup", timeout=15, json={
            "name": "Porta Prova", "email": email, "password": "PortaAurya2026!x",
            "language": "it", "accepted_terms": True, "wants_newsletter": True,
            "consenso_versione": "cerchio-v3"})
        if r.status_code == 429:
            pytest.skip("rate limit signup")
        assert r.status_code == 202, r.text
        try:
            corpo = r.json()
            if "access_token" in corpo:
                # flag acceso in locale: la sessione vale subito
                me = requests.get(f"{BASE_URL}/api/platform/me", timeout=10,
                                  headers={"Authorization": f"Bearer {corpo['access_token']}"})
                assert me.status_code == 200 and me.json()["email"] == email
                assert requests.get(f"{BASE_URL}/api/platform/me/export", timeout=10,
                                    headers={"Authorization": f"Bearer {corpo['access_token']}"}).status_code == 401
            else:
                assert corpo.get("status") == "verification_required"
                l = requests.post(f"{BASE_URL}/api/platform/auth/login", timeout=10,
                                  json={"email": email, "password": "PortaAurya2026!x"})
                assert l.status_code == 403 and l.json().get("detail") == "EMAIL_NOT_VERIFIED"
            # senza accepted_terms → 400; email gia' presa → 409
            assert requests.post(f"{BASE_URL}/api/platform/auth/signup", timeout=10, json={
                "email": f"x{email}", "password": "PortaAurya2026!x", "accepted_terms": False}).status_code == 400
            assert requests.post(f"{BASE_URL}/api/platform/auth/signup", timeout=10, json={
                "email": email, "password": "PortaAurya2026!x", "accepted_terms": True}).status_code == 409
        finally:
            import pymongo
            c = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
            sub = c.aurya_subscribers.find_one({"email": email})
            c.platform_accounts.delete_many({"email": email})
            c.aurya_subscribers.delete_many({"email": email})
        assert sub, "il Cerchio non ha registrato l'iscrizione chiesta al signup"
        assert sub.get("status") in ("pending", "confirmed")
        assert (sub.get("consenso") or {}).get("versione") == "cerchio-v3"

    def test_la_verifica_conferma_il_cerchio(self):
        """Dal vivo: account con token di verifica noto + iscritto in attesa →
        POST /platform/auth/verify-email → iscritto confermato, verificato_da
        tipo «account». Setup e pulizia con pymongo (niente loop condiviso)."""
        import secrets, time
        import pymongo
        from services.platform_account_service import _hash_token
        c = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        email = f"porta-r1-verify-{int(time.time())}@example.com"
        token = secrets.token_urlsafe(16)
        c.platform_accounts.insert_one({
            "id": f"r1-{token[:8]}", "email": email, "email_verified": False, "is_active": True,
            "verification_token_hash": _hash_token(token), "verification_token_expires": None})
        c.aurya_subscribers.insert_one({"email": email, "status": "pending", "created_at": "2026-09-25T00:00:00"})
        try:
            r = requests.post(f"{BASE_URL}/api/platform/auth/verify-email", json={"token": token}, timeout=15)
            if r.status_code == 429:
                pytest.skip("rate limit verify-email")
            assert r.status_code == 200, r.text
            sub = c.aurya_subscribers.find_one({"email": email})
            acc = c.platform_accounts.find_one({"email": email})
        finally:
            c.platform_accounts.delete_many({"email": email})
            c.aurya_subscribers.delete_many({"email": email})
        assert acc and acc.get("email_verified") is True
        assert sub["status"] == "confirmed" and (sub.get("verificato_da") or {}).get("tipo") == "account"
