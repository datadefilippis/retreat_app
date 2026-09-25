"""25/9/2026 — «Sei già dentro»: chi ha la sessione aperta non trova piu'
un form di registrazione (caso Marilisa: due account in un giorno).

Tenuto fermo qui:
  1. la scheda GiaDentro esiste con i tre gesti (pagina, gestionale, esci);
  2. /accedi la mostra al posto del form e della registrazione quando
     isAuthenticated (non durante la verifica da token);
  3. la landing /entra-nella-rete (InlineSignupForm) idem;
  4. il 409 «email già esistente» offre i gesti (accedi, nuova password)
     invece di un testo e basta;
  5. la voce d'oro dell'header dice «Il tuo spazio» → /dashboard a chi
     ha gia' il cappello operatore.
"""
from pathlib import Path

FE = Path(__file__).resolve().parents[2] / "frontend" / "src"
CARD = (FE / "components" / "GiaDentro.js").read_text(encoding="utf-8")
ACCEDI = (FE / "features" / "account" / "AccountLoginPage.js").read_text(encoding="utf-8")
INLINE = (FE / "features" / "prelaunch" / "InlineSignupForm.js").read_text(encoding="utf-8")
SHELL = (FE / "features" / "storefront" / "components" / "MarketplaceShell.jsx").read_text(encoding="utf-8")


class TestScheda:
    def test_tre_gesti(self):
        for tid in ("gia-dentro", "gia-dentro-pagina", "gia-dentro-gestionale", "gia-dentro-esci"):
            assert f'data-testid="{tid}"' in CARD, tid
        assert 'to="/public-profile"' in CARD and "to={gestionale}" in CARD
        # il system admin non ha una pagina: va alla regia
        assert "const gestionale = isSys ? '/admin' : '/dashboard';" in CARD and "{!isSys && (" in CARD
        assert "onClick={() => logout()}" in CARD


class TestSuperfici:
    def test_accedi(self):
        assert "const giaDentro = isAuthenticated && !token && (state === 'form' || state === 'signup');" in ACCEDI
        # la scheda AVVOLGE le viste (i letterali «{state === 'signup' && (»
        # restano intatti: altre guardie li usano per leggere le viste)
        assert "{giaDentro ? <GiaDentro compatto /> : (<>" in ACCEDI
        assert "{state === 'form' && (" in ACCEDI and "{state === 'signup' && (" in ACCEDI
        assert ACCEDI.rstrip().endswith("</>)}\n      </div>\n    </div>\n    </MarketplaceShell>\n  );\n}")

    def test_landing(self):
        assert "if (isAuthenticated) {\n    return <GiaDentro />;" in INLINE
        assert "const { signup } = useAuth();" in INLINE and "const { isAuthenticated } = useAuth();" in INLINE

    def test_409_offre_i_gesti(self):
        assert ACCEDI.count("setEsiste(true);") == 2
        assert 'data-testid="signup-esiste"' in ACCEDI and "goTo('form')" in ACCEDI and "goTo('reset')" in ACCEDI
        assert "setState(view); setError(null); setEsiste(false);" in ACCEDI
        assert 'data-testid="ol-signup-esiste"' in INLINE and "/accedi?email=" in INLINE and "/accedi?vista=reset" in INLINE

    def test_header_parla_a_chi_e_dentro(self):
        assert "? (hasOperatorToken ? '/dashboard' : '/entra-nella-rete')" in SHELL
        assert "'Il tuo spazio'" in SHELL
        # e i nomi di sempre restano (guardia AN2: to={operatorTo}, {operatorLabel})
        assert "const operatorTo = isNetwork" in SHELL and "const operatorLabel = isNetwork" in SHELL
