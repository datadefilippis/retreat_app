"""25/9/2026 — un'email, un account: le maiuscole non creano doppioni.

Caso vero in prod (24/9): stessa persona registrata due volte, la
seconda con la S maiuscola dell'autocorrezione del telefono. Tenuto fermo:
  1. i modelli di registrazione, login e invito normalizzano l'email;
  2. la ricerca per email e' in minuscolo (con ripiego per record storici);
  3. lo script di normalizzazione esiste e non tocca i doppioni veri.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


class TestModelli:
    def test_registrazione_login_invito_normalizzano(self):
        from models.user import UserCreate, UserLogin, UserInvite, UserBase
        u = UserCreate(email="  Spaziomarilisa@Gmail.com ", name="Marilisa", password="Password-Lunga-12")
        assert u.email == "spaziomarilisa@gmail.com"
        assert UserLogin(email="Spaziomarilisa@gmail.com", password="x").email == "spaziomarilisa@gmail.com"
        assert UserInvite(email="Nuovo@Esempio.it", name="N").email == "nuovo@esempio.it"
        assert UserBase(email="A@B.it", name="A").email == "a@b.it"

    def test_una_sola_funzione(self):
        src = (BACKEND / "models" / "user.py").read_text(encoding="utf-8")
        assert src.count("def _email_minuscola(") == 1
        assert src.count("return _email_minuscola(v)") == 4


class TestRicerca:
    def test_find_by_email_in_minuscolo_con_ripiego(self):
        src = (BACKEND / "repositories" / "user_repository.py").read_text(encoding="utf-8")
        i = src.index("async def find_by_email(")
        blocco = src[i:i + 700]
        assert '{"email": e.lower()}' in blocco
        assert "if doc is None and e != e.lower():" in blocco

    def test_lo_script_esiste_e_rispetta_i_doppioni(self):
        src = (BACKEND / "scripts" / "normalizza_email_utenti.py").read_text(encoding="utf-8")
        assert "--prova" in src and "DOPPIONE" in src and "continue" in src
