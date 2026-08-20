"""Ciclo ID (20/8/2026) — la porta unica /accedi e il legame dei cappelli.

Il principio da difendere (docs/IDENTITA_UNICA_PLAN_2026-08.md): il
mondo di appartenenza (operatore/cliente) e' un dettaglio NOSTRO — la
password lo seleziona, il legame fra identita' VERIFICATE porta l'SSO,
e nessuna porta secondaria puo' riaprire il bivio che confondeva gli
operatori (caso Rossato, 20/8: otto 401 sulla porta dei clienti).
"""
import os
from pathlib import Path

import pytest
import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")


class TestPortaUnicaId2:
    """/api/auth/entra: una porta, la password seleziona il mondo."""

    def test_porta_montata(self):
        src = (BACKEND_DIR / "server.py").read_text()
        assert "unified_auth_router.router" in src, "la porta unica non e' montata"

    def test_errore_unico_generico(self):
        """Email inesistente e password sbagliata devono essere
        INDISTINGUIBILI (byte per byte). E il rate limit per email si
        traveste da stesso errore: mai un segnale diverso."""
        src = (BACKEND_DIR / "routers" / "unified_auth.py").read_text()
        assert src.count('_GENERIC_401 = "Email o password non corretti."') == 1
        # il limite per email risponde col GENERICO, non con un 429
        blocco = src.split("check_email_rate(email, \"unified_login\"")[1][:300]
        assert "_GENERIC_401" in blocco, \
            "il rate limit per email rivela l'esistenza dell'account"

    def test_contatore_trasversale(self):
        """Una porta = un conto. Il bucket e' unico (unified_login),
        non uno per mondo."""
        src = (BACKEND_DIR / "routers" / "unified_auth.py").read_text()
        assert '"unified_login"' in src
        assert "max_per_hour=20" in src, "soglia diversa dalle porte storiche"

    def test_operatore_prima_e_sso_esplicito(self):
        """Match doppio → operatore per primo; l'SSO arriva SOLO dal
        legame (operator_user_id / platform_account_id), mai dalla sola
        coincidenza di email."""
        src = (BACKEND_DIR / "routers" / "unified_auth.py").read_text()
        assert '"operator_user_id": user_id' in src
        assert 'worlds.insert(0, sso)' in src, "l'operatore non e' piu' il primo cappello"
        for guardia in ('"is_active": True', '"email_verified": True'):
            assert src.count(guardia) >= 2, \
                "l'SSO deve pretendere account attivi e verificati su ENTRAMBI i lati"

    def test_live_generico_su_email_ignota(self):
        try:
            r = requests.post(f"{BASE_URL}/api/auth/entra", json={
                "email": "nessuno-di-nessuno@example.com",
                "password": "una-password-qualsiasi-123"}, timeout=10)
        except requests.RequestException:
            pytest.skip("backend non raggiungibile")
        if r.status_code == 429:
            pytest.skip("rate limit IP (suite calda)")
        assert r.status_code == 401
        assert r.json()["detail"] == "Email o password non corretti."


class TestLegameCappelliId3:
    """identity_link_service: le 5 regole del piano."""

    def test_link_solo_fra_email_verificate(self):
        src = (BACKEND_DIR / "services" / "identity_link_service.py").read_text()
        fn = src.split("async def link_hats")[1].split("async def")[0]
        assert 'user_doc.get("email_verified")' in fn
        assert 'account_doc.get("email_verified")' in fn
        assert "_norm(user_doc.get(\"email\")) != _norm(account_doc.get(\"email\"))" in fn, \
            "manca il confronto email: il link accetterebbe coppie qualsiasi"

    def test_auto_link_non_crea_mai(self):
        src = (BACKEND_DIR / "services" / "identity_link_service.py").read_text()
        fn = src.split("async def auto_link_by_email")[1].split("async def")[0]
        assert "insert_one" not in fn, \
            "auto_link deve COLLEGARE l'esistente, mai creare account"

    def test_cappello_su_gesto_esplicito(self):
        """Il provisioning vive solo dietro POST /hats/client (operatore
        autenticato): mai automatico, e mai sopra un account cliente
        non verificato."""
        src = (BACKEND_DIR / "services" / "identity_link_service.py").read_text()
        fn = src.split("async def ensure_client_hat_for_operator")[1]
        assert 'raise ValueError("OPERATOR_EMAIL_NOT_VERIFIED")' in fn
        assert 'raise ValueError("CLIENT_ACCOUNT_UNVERIFIED")' in fn
        router = (BACKEND_DIR / "routers" / "unified_auth.py").read_text()
        assert "ensure_client_hat_for_operator" in router
        assert router.count("Depends(get_current_user)") == 1

    def test_verifiche_email_agganciano_il_legame(self):
        """Tutte le strade in cui un'email diventa verificata chiamano
        l'auto-link: verify operatore, verify/magic/OTP piattaforma."""
        auth_src = (BACKEND_DIR / "routers" / "auth.py").read_text()
        assert "auto_link_by_email" in auth_src, "manca l'hook sulla verifica operatore"
        pa_src = (BACKEND_DIR / "services" / "platform_account_service.py").read_text()
        assert pa_src.count("auto_link_by_email") >= 3, \
            "una strada di verifica piattaforma non aggancia il legame"

    def test_cancellazioni_sganciano(self):
        pa_src = (BACKEND_DIR / "services" / "platform_account_service.py").read_text()
        assert "unlink_for_account" in pa_src, \
            "la cancellazione GDPR del cliente lascia il puntatore appeso"
        auth_src = (BACKEND_DIR / "routers" / "auth.py").read_text()
        assert "unlink_for_user" in auth_src, \
            "la disattivazione operatore lascia l'SSO vivo"

    def test_indici_del_legame(self):
        src = (BACKEND_DIR / "database.py").read_text()
        assert '"platform_account_id", sparse=True' in src
        assert '"operator_user_id", sparse=True' in src


class TestSuperficieId4:
    """Una porta visibile, alias vivi, menu onesto."""

    def test_alias_conservano_la_query(self):
        """/login e /account/accedi non muoiono MAI: redirect che porta
        con se' ?next= e ?token= (i magic link vecchi funzionano)."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert '<Route path="/accedi" element={<AccountLoginPage />} />' in app
        assert app.count('<RedirectPreservingQuery to="/accedi" />') == 2, \
            "un alias e' morto o non conserva la query"

    def test_porta_unica_nel_form(self):
        src = (FRONTEND_SRC / "features" / "account" / "AccountLoginPage.js").read_text()
        assert "'/auth/entra'" in src, "il form non parla con la porta unica"
        assert "localStorage.setItem('token', w.access_token)" in src, \
            "il cappello operatore non viene salvato"
        assert "next || (operator ? '/dashboard' : '/account')" in src, \
            "l'operatore non atterra nel suo posto di lavoro"
        assert "rawNext.startsWith('/') && !rawNext.startsWith('//')" in src, \
            "manca la guardia open-redirect su ?next="

    def test_niente_soccorso_verso_porte_morte(self):
        src = (FRONTEND_SRC / "features" / "account" / "AccountLoginPage.js").read_text()
        assert 'to="/login"' not in src, \
            "la porta unica rimanda ancora alla porta vecchia"

    def test_menu_una_sola_porta(self):
        """L'etichetta «Il tuo account Aurya» sopra una porta di meta'
        account era la CAUSA del bug: da sloggato si accede da UN posto."""
        src = (FRONTEND_SRC / "features" / "storefront" / "components"
               / "MarketplaceShell.jsx").read_text()
        assert "'/accedi'" in src and "'/accedi?vista=crea'" in src
        assert "account-menu-operator-login" not in src, \
            "«Area professionisti» e' tornata nel menu: e' la stessa porta"
        assert "'/account/accedi'" not in src, "il menu punta alla porta vecchia"

    def test_recupero_password_per_tutti_i_mondi(self):
        fe = (FRONTEND_SRC / "features" / "account" / "AccountLoginPage.js").read_text()
        assert "'/auth/recupero'" in fe
        be = (BACKEND_DIR / "routers" / "unified_auth.py").read_text()
        assert "request_password_reset" in be and "forgot_password" in be, \
            "il recupero unificato non copre entrambi i mondi"
        blocco = be.split("async def recupero")[1]
        assert blocco.count("return generic") >= 2, \
            "il recupero non risponde sempre neutro (enumeration)"

    def test_link_interni_sulla_porta_unica(self):
        links = (FRONTEND_SRC / "features" / "frequenze" / "links.js").read_text()
        assert "/accedi?next=" in links, "PRO_ENTRY punta ancora a /login"
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        assert 'to="/accedi"' in shell, "il footer non punta alla porta unica"


class TestSuperficieIdBis:
    """ID-bis (20/8, feedback founder dopo il primo giro): dal sito il
    gestionale resta a un clic, /account mostra il cappello, i link
    che mentono spariscono."""

    def test_menu_gestionale_per_operatore_loggato(self):
        src = (FRONTEND_SRC / "features" / "storefront" / "components"
               / "MarketplaceShell.jsx").read_text()
        assert "hasOperatorToken" in src, \
            "il menu non sa del cappello operatore"
        assert "'/dashboard'" in src and "account-menu-gestionale" in src, \
            "manca «Il tuo gestionale» per chi e' gia' dentro"

    def test_account_mostra_il_cappello_professionista(self):
        be = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        assert '"operator_linked"' in be, "/platform/me non espone il legame"
        fe = (FRONTEND_SRC / "features" / "account" / "AccountPage.js").read_text()
        assert "me.operator_linked" in fe \
            and 'data-testid="account-operator-hat"' in fe, \
            "/account non mostra il ponte verso il gestionale"

    def test_niente_ritiri_promessi_in_fase_rete(self):
        """«Scopri i prossimi ritiri» quando i ritiri non esistono e'
        una promessa falsa: in fase rete il link sparisce."""
        fe = (FRONTEND_SRC / "features" / "account" / "AccountPage.js").read_text()
        assert "sitePhase === 'network'" in fe
        assert "{!isNetwork && (" in fe, \
            "il link ritiri non e' legato alla fase"

    def test_torna_su_aurya_non_ai_ritiri(self):
        for f in ("AccountLoginPage.js", "AccountVerifyEmailPage.js",
                  "AccountResetPasswordPage.js"):
            src = (FRONTEND_SRC / "features" / "account" / f).read_text()
            assert "backToRetreats" not in src, \
                f"{f}: promette ancora i ritiri (fase rete)"
            assert "backToAurya2" in src

    def test_signup_vecchio_porta_alla_landing(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert ('path="/signup" element='
                '{<Navigate to="/entra-nella-rete#presentati" replace />}') in app, \
            "il vecchio /signup condiviso con gli operatori e' morto o va altrove"

    def test_registrazione_omino_dichiara_il_suo_mondo(self):
        """«Crea il tuo account» dall'omino crea l'account PERSONALE:
        la vista lo dice, e la via professionale e' li' accanto — UNA
        volta sola (ID-ter: in registrazione l'invito era doppio)."""
        src = (FRONTEND_SRC / "features" / "account"
               / "AccountLoginPage.js").read_text()
        assert "signupBody2" in src and "per chi partecipa" in src
        assert src.count('data-testid="operator-rescue-link"') == 1, \
            "l'invito professionisti e' duplicato (o sparito)"
        assert 'data-testid="signup-pro-hint"' not in src, \
            "e' tornato il secondo invito nella vista registrazione"

    def test_invito_professionisti_ben_visibile(self):
        """Non piu' una postilla grigia da 12px: un blocco con titolo,
        spiegazione e bottone, presente in TUTTE le viste della porta."""
        src = (FRONTEND_SRC / "features" / "account"
               / "AccountLoginPage.js").read_text()
        box = src.split('data-testid="operator-rescue-link"')[1][:900]
        assert "proBoxTitle" in box and "proBoxBody" in box \
            and 'data-testid="pro-box-cta"' in box, \
            "il blocco professionisti non ha titolo/corpo/bottone"
        assert "text-xs text-gray-400" not in box.split("proBoxTitle")[0], \
            "il blocco e' ancora una postilla sbiadita"
        # il messaggio che evita il bivio: chi ha gia' lo spazio entra da QUI
        assert "stessa email" in box, \
            "il blocco non dice che l'accesso professionale e' questo stesso"


class TestMenuCoerenteIdQuater:
    """ID-quater (20/8, feedback founder): chi e' dentro non deve mai
    leggere un invito a entrare. Il menu leggeva SOLO il token cliente,
    cosi' un operatore loggato si vedeva «Accedi / Crea il tuo account»
    e non trovava «Esci»."""

    SHELL = (FRONTEND_SRC / "features" / "storefront" / "components"
             / "MarketplaceShell.jsx")

    def test_niente_accedi_per_chi_e_dentro(self):
        src = self.SHELL.read_text()
        assert "const loggedIn = hasPlatformToken || hasOperatorToken" in src, \
            "il menu guarda un cappello solo"
        blocco = src.split("const userLinks =")[1].split("const operatorLinks")[0]
        assert "hasOperatorToken" in blocco, \
            "l'operatore loggato riceve ancora l'invito ad accedere"
        assert "account-menu-add-client" in blocco, \
            "all'operatore senza cappello cliente non viene offerto nulla"

    def test_esci_c_e_sempre_quando_si_e_dentro(self):
        src = self.SHELL.read_text()
        assert src.count("{loggedIn && (") >= 2, \
            "«Esci» (o il pallino) guarda ancora il solo token cliente"
        assert "hasPlatformToken && (" not in src.split("const trigger")[1][:600], \
            "il pallino di stato ignora il cappello operatore"

    def test_esci_chiude_entrambi_i_cappelli(self):
        """Con la porta unica la sessione e' una: «Esci» esce davvero."""
        src = self.SHELL.read_text()
        fn = src.split("const logoutPlatform")[1].split("}, [")[0]
        assert "localStorage.removeItem('token')" in fn, \
            "il gestionale resta aperto dopo «Esci»"
        assert "setHasOperatorToken(false)" in fn
        assert "window.location.assign('/')" in fn, \
            "senza hard navigate l'AuthContext resta con la sessione morta"

    def test_via_per_diventare_professionista(self):
        """Chi ha creato per sbaglio l'account personale (o cambia
        mestiere) deve trovare la strada: registrazione professionale
        con la STESSA email, che al termine collega i cappelli."""
        acc = (FRONTEND_SRC / "features" / "account" / "AccountPage.js").read_text()
        assert 'data-testid="account-become-pro"' in acc, \
            "da /account non si scopre come diventare professionista"
        assert "/entra-nella-rete?email=" in acc, \
            "la via non porta l'email che collega i due cappelli"
        form = (FRONTEND_SRC / "features" / "prelaunch"
                / "InlineSignupForm.js").read_text()
        assert "params.get('email')" in form, \
            "la registrazione professionale non raccoglie l'email dal ponte"
