"""P3 (24/9/2026, founder) — il telefono del professionista: obbligatorio nei
moduli di registrazione, PRIVATO di default (show_contacts spento), e
chiesto a chi non l'ha dato, dalla home, senza cambiare pagina.

  1. forma canonica (services/telefono.py) e rifiuto dei numeri malformati
     gia' nel modello UserCreate (422, prima di toccare il db);
  2. alla registrazione entra in public_profile.public_phone, mai in un
     campo pubblico: show_contacts non si accende;
  3. i due moduli lo chiedono (required) e lo dicono privato; /benvenuto
     non lo richiede a chi l'ha gia' dato;
  4. la home dell'operatore lo chiede a chi non ce l'ha; la regia lo vede
     nella scheda 360.
"""
import pytest
from pathlib import Path

from services.telefono import normalizza_telefono, telefono_valido

BACKEND = Path(__file__).resolve().parents[1]
FE = BACKEND.parent / "frontend" / "src"
LOGIN = (FE / "features" / "account" / "AccountLoginPage.js").read_text(encoding="utf-8")
INLINE = (FE / "features" / "prelaunch" / "InlineSignupForm.js").read_text(encoding="utf-8")
WELCOME = (FE / "features" / "prelaunch" / "WelcomeRetePage.js").read_text(encoding="utf-8")
HOME = (FE / "features" / "dashboard" / "OperatorHome.js").read_text(encoding="utf-8")
CTX = (FE / "context" / "AuthContext.js").read_text(encoding="utf-8")
DIALOG = (FE / "features" / "admin" / "OrgBusinessProfileDialog.js").read_text(encoding="utf-8")
AUTH = (BACKEND / "services" / "auth_service.py").read_text(encoding="utf-8")
ADMIN = (BACKEND / "routers" / "admin_platform.py").read_text(encoding="utf-8")


class TestFormaCanonica:
    def test_normalizza(self):
        assert normalizza_telefono("+39 366 371 3543") == "+393663713543"
        assert normalizza_telefono("366.371-3543") == "3663713543"
        assert normalizza_telefono("(0039) 366 3713543") == "00393663713543"

    def test_rifiuta(self):
        for cattivo in ("", "   ", "12345", "abc", "+39", "1" * 16):
            assert normalizza_telefono(cattivo) is None, cattivo
            assert not telefono_valido(cattivo)

    def test_il_modello_lo_rende_canonico_o_rifiuta(self):
        from models.user import UserCreate
        base = dict(email="a@b.it", name="Anna Bianchi", password="Password-Lunga-12", accepted_terms=True)
        assert UserCreate(**base, phone="+39 366 371 3543").phone == "+393663713543"
        assert UserCreate(**base).phone is None and UserCreate(**base, phone="  ").phone is None
        with pytest.raises(Exception):
            UserCreate(**base, phone="12")


class TestPrivatoDalPrimoGiorno:
    def test_entra_nel_profilo_ma_non_si_espone(self):
        assert 'org_doc.setdefault("public_profile", {})["public_phone"] = user_data.phone' in AUTH
        assert "show_contacts" not in AUTH.split("public_phone")[1][:400] or '"show_contacts": False' in AUTH

    def test_i_moduli_lo_chiedono_e_lo_dicono_privato(self):
        assert 'data-testid="signup-phone"' in LOGIN and 'type="tel" required' in LOGIN
        assert "Non compare sulla tua pagina finché non lo decidi tu" in LOGIN
        assert 'data-testid="signup-phone"' in INLINE and 'type="tel" required' in INLINE
        assert "website, phone" in CTX and "if (phone) payload.phone = phone;" in CTX
        assert "emailLang() || 'it', website, phone.trim());" in LOGIN
        assert "i18n.language, website, phone.trim());" in INLINE

    def test_benvenuto_non_lo_richiede(self):
        assert "setPhonePresente(true)" in WELCOME and "{!phonePresente && (" in WELCOME

    def test_la_home_lo_chiede_a_chi_non_ce_l_ha(self):
        assert 'data-testid="home-telefono"' in HOME
        # il segnale viaggia in onboarding-status: NESSUNA chiamata in piu' (IG4)
        assert "obSteps?.telefono_mancante === true" in HOME
        assert HOME.count("api.get(") == 6
        assert '"telefono_mancante": not bool(pp.get("public_phone"))' in (BACKEND / "routers" / "organizations.py").read_text(encoding="utf-8")
        assert "api.patch('/organizations/current/public-profile', { public_phone: telefono.trim() })" in HOME
        assert "chiediRecensioni && !telefonoSalvato" in HOME   # la regia non la vede

    def test_la_regia_lo_vede(self):
        assert '"public_profile.public_phone": 1' in ADMIN and '"telefono":' in ADMIN
        assert 'data-testid="business-recapito"' in DIALOG
