"""Ciclo CP (20/8/2026) — le cinque incoerenze dei percorsi.

Piano: docs/COERENZA_PERCORSI_PIANO_CP_2026-08.md. Il filo comune:
lo stato di una persona deve essere VISIBILE e REVERSIBILE là dove
quella persona si trova.
"""
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
SVC = BACKEND_DIR / "services" / "platform_account_service.py"
ACCOUNT = FRONTEND_SRC / "features" / "account" / "AccountPage.js"


class TestStatoLetteraCp1:
    """Il pending smette di essere invisibile."""

    def test_stato_a_tre_valori(self):
        svc = SVC.read_text()
        fn = svc.split("async def newsletter_status")[1].split("\nasync def")[0]
        assert '"newsletter_state": "none"' in fn
        assert 'out["newsletter_state"] = doc.get("status")' in fn, \
            "lo stato non riflette il documento"
        assert 'doc.get("status") == "confirmed"' in fn, \
            "il booleano non vale piu' solo per i confermati"

    def test_booleano_invariato_per_i_chiamanti(self):
        """BN3, AP2 e il login continuano a leggere il booleano: chi non
        ha confermato NON deve sbloccare nulla."""
        svc = SVC.read_text()
        fn = svc.split("async def newsletter_status")[1].split("\nasync def")[0]
        blocco = fn.split('doc.get("status") == "confirmed"')[1][:260]
        assert "subscriber_token" in blocco, \
            "il token non e' piu' legato alla conferma"
        assert "newsletter_state" not in blocco.split("return out")[0], \
            "lo stato non deve intromettersi nella regola del token"

    def test_account_dice_che_manca_la_conferma(self):
        src = ACCOUNT.read_text()
        assert "me.newsletter_state === 'pending'" in src
        assert 'data-testid="guides-pending"' in src
        assert 'data-testid="guides-resend"' in src, \
            "manca il rinvio dell'email di conferma"
        fn = src.split("const resendLetter")[1][:420]
        assert "'/public/newsletter/subscribe'" in fn, \
            "il rinvio non passa dal flusso pubblico (double opt-in)"


class TestLetteraOperatoreCp2:
    """L'operatore ha un posto suo, con lo stato della SUA email."""

    ROUTER = BACKEND_DIR / "routers" / "unified_auth.py"

    def test_endpoint_stato_e_azione(self):
        src = self.ROUTER.read_text()
        assert '@router.get("/letter")' in src and '@router.post("/letter")' in src
        fn = src.split("async def letter_toggle")[1]
        assert "from routers.subscribers import SubscribePayload, subscribe" in fn, \
            "l'iscrizione non riusa la route pubblica"
        assert "generate_subscriber_token" in fn, \
            "il token di disiscrizione va generato lato server, non chiesto"
        assert 'source="gestionale"' in fn, "sorgente non tracciata"

    def test_solo_la_propria_email(self):
        """Mai un'email arbitraria: si agisce su quella dell'utente."""
        src = self.ROUTER.read_text()
        fn = src.split("async def letter_toggle")[1]
        assert 'current_user.get("email")' in fn
        assert "body.email" not in fn, \
            "l'endpoint accetta un'email dal client: si potrebbe iscrivere chiunque"

    def test_card_nelle_impostazioni(self):
        card = (FRONTEND_SRC / "features" / "settings" / "sections"
                / "LetterCard.jsx").read_text()
        for testid in ("settings-letter", "letter-subscribe",
                       "letter-unsubscribe", "letter-resend"):
            assert testid in card, f"manca l'azione {testid}"
        page = (FRONTEND_SRC / "features" / "settings" / "SettingsPage.js").read_text()
        assert "<LetterCard />" in page, "la card non e' montata"


class TestAccountDallAcquistoCp3:

    def test_success_page_lo_dice(self):
        src = (FRONTEND_SRC / "features" / "storefront"
               / "CheckoutResultPage.js").read_text()
        assert 'data-testid="checkout-account-ready"' in src
        assert "accountReady" in src and "già pronto" in src, \
            "la success page non racconta l'account gia' nato"
        assert 'data-testid="checkout-set-password"' in src, \
            "manca la strada «imposta una password»"
        assert "vista=recupero" in src

    def test_la_porta_capisce_la_vista(self):
        src = (FRONTEND_SRC / "features" / "account"
               / "AccountLoginPage.js").read_text()
        assert "'recupero' ? 'reset'" in src, \
            "?vista=recupero non apre la vista giusta"


class TestPortaDormienteCp4:

    def test_login_legacy_redirige(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert ('path="/account/login" element='
                '{<RedirectPreservingQuery to="/accedi" />}') in app, \
            "la porta dormiente e' di nuovo aperta"
        assert "CustomerLoginPage" not in app, \
            "la pagina del portale legacy e' ancora montata"

    def test_le_pagine_di_servizio_restano(self):
        """Verifica/reset del portale restano vive: i link gia' spediti
        devono continuare a funzionare."""
        app = (FRONTEND_SRC / "App.js").read_text()
        for p in ("/account/verify-email", "/account/reset-password",
                  "/account/forgot-password"):
            assert f'path="{p}"' in app, f"{p} e' stata spenta per sbaglio"


class TestVisibilitaProfiloCp5:

    def test_campi_di_visibilita_esposti(self):
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        blocco = src.split('"visibility_missing"')[1][:320]
        assert '"city"' in blocco and '"disciplines"' in blocco
        # la barra di completezza dell'editor NON si sposta
        checks = src.split("profile_checks = {")[1].split("}")[0]
        assert "disciplines" not in checks, \
            "le discipline sono entrate nei check: la barra dell'editor cambia"

    def test_striscia_chiede_i_campi_mancanti(self):
        src = (FRONTEND_SRC / "features" / "onboarding"
               / "OnboardingStrip.js").read_text()
        assert 'data-testid="onboarding-visibility"' in src
        assert "visibility_missing" in src
        assert "is_complete && visMissing.length" in src, \
            "la riga non compare a chi ha finito l'onboarding (il caso vero)"
        assert "/public-profile" in src, "la riga non porta dove si compila"


class TestBenvenutoRaggiungibileIdOcties:
    """ID-octies (20/8, founder) — il secondo passo esisteva ma NON lo
    vedeva nessuno: il signup non rilascia piu' una sessione (serve la
    verifica email), quindi /benvenuto era irraggiungibile. Ora: verifica
    → benvenuto → (compilato o saltato) → dashboard, una volta sola."""

    def test_dopo_la_verifica_si_va_al_benvenuto(self):
        src = (FRONTEND_SRC / "pages" / "AuthPages.js").read_text()
        assert "/accedi?next=%2Fbenvenuto" in src, \
            "dopo la verifica si torna al login nudo: il benvenuto resta invisibile"

    def test_il_primo_accesso_ci_porta_anche_senza_next(self):
        """Chi verifica sul telefono e poi entra dal computer perde il
        ?next=: il server dice se il benvenuto e' ancora da fare."""
        be = (BACKEND_DIR / "routers" / "unified_auth.py").read_text()
        assert "welcome_pending" in be
        fn = be.split("async def _welcome_pending")[1].split("\ndef ")[0]
        assert "org is not None" in fn, \
            "con la proiezione un doc senza il campo torna {} (falsy): il "\
            "benvenuto non apparirebbe proprio a chi non l'ha mai visto"
        fe = (FRONTEND_SRC / "features" / "account" / "AccountLoginPage.js").read_text()
        # ID-nonies: il benvenuto pendente si fa SEMPRE — un ?next=
        # esplicito non lo scavalca piu' (lo faceva in silenzio, senza
        # timbro, e il benvenuto ricompariva all'accesso successivo:
        # dashboard prima, benvenuto poi — l'ordine inverso). La
        # destinazione viaggia col benvenuto e viene riconsegnata.
        assert "if (operator && welcomePending)" in fe
        assert "/benvenuto?next=" in fe, \
            "il benvenuto butta via la destinazione del next"

    def test_compilato_o_saltato_si_riconsegna_la_destinazione(self):
        src = (FRONTEND_SRC / "features" / "prelaunch" / "WelcomeRetePage.js").read_text()
        fn = src.split("const next =")[1][:400]
        assert "welcome-seen" in fn, "il passaggio non viene timbrato"
        # ID-nonies: si atterra sulla destinazione conservata (dest),
        # che senza ?next= e' la dashboard
        assert "navigate(dest" in fn, \
            "il benvenuto non riconsegna la destinazione conservata"
        assert "'/inizia'" not in fn, "si va ancora alla vecchia destinazione"
        # il ?next= accetta solo percorsi interni (mai '//')
        assert "rawNext.startsWith('/')" in src
        assert "!rawNext.startsWith('//')" in src
        assert "'/dashboard'" in src.split("const dest")[1][:200], \
            "senza next non c'e' il ripiego sulla dashboard"

    def test_non_si_ripropone(self):
        be = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert '"welcome_seen": bool(org_doc.get("welcome_seen_at"))' in be
        endpoint = be.split("async def mark_welcome_seen")[1][:500]
        assert '"welcome_seen_at": {"$exists": False}' in endpoint, \
            "il timbro non e' idempotente: la data si sposterebbe a ogni giro"
        fe = (FRONTEND_SRC / "features" / "prelaunch" / "WelcomeRetePage.js").read_text()
        assert "r.data?.welcome_seen" in fe, \
            "la pagina si ripropone a chi l'ha gia' vista"
