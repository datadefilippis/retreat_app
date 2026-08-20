"""Ciclo NL (20/8/2026) — Lettera leggera, account magnete.

Il fastidio del founder («mi iscrivo alla Lettera, poi creo l'account e
vado in errore») non era un conflitto fra i due sistemi: era la POLICY
PASSWORD (12 caratteri + maiuscole + numeri + controllo data-breach) e
poi il rate limit del signup. Piano: docs/FUNNEL_LETTERA_ACCOUNT_2026-08.md.

Quello che queste guardie difendono:
  - l'account nasce SENZA password (magic-link-first, come da piano P1);
  - nessun account nasce senza consenso legale (AP-L), nemmeno dal
    magic link — che prima lo creava a vuoto;
  - la Lettera resta un consenso SEPARATO e mai preselezionato;
  - l'iscrizione email-only resta viva su tutte le superfici;
  - dopo l'iscrizione c'e' un ponte verso l'account, non un muro.
"""
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
SVC = BACKEND_DIR / "services" / "platform_account_service.py"
PORTA = FRONTEND_SRC / "features" / "account" / "AccountLoginPage.js"


class TestAccountSenzaPasswordNl1:

    def test_registrazione_non_chiede_password(self):
        src = PORTA.read_text()
        blocco = src.split("const submitSignup")[1].split("};")[0]
        assert "'/platform/auth/magic-link'" in blocco, \
            "la registrazione passa ancora dal signup con password"
        assert "password," not in blocco, \
            "il submit manda ancora una password"
        vista = src.split("{state === 'signup' && (")[1].split("{state === 'signupSent'")[0]
        assert 'type="password"' not in vista, \
            "il campo password e' tornato nella registrazione"

    def test_una_sola_strada_di_creazione(self):
        """Niente terza via: la registrazione leggera E' il find-or-create
        del magic link, non un endpoint parallelo che gli somiglia."""
        svc = SVC.read_text()
        fn = svc.split("async def request_magic_link")[1].split("\nasync def")[0]
        assert "insert_one" in fn and "accepted_terms" in fn
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        assert router.count("/auth/signup") == 1, \
            "e' comparso un secondo endpoint di registrazione"

    def test_niente_account_senza_consenso(self):
        """AP-L: il magic link creava account SENZA timbro legale.
        Ora senza consenso e' find-only."""
        svc = SVC.read_text()
        fn = svc.split("async def request_magic_link")[1].split("\nasync def")[0]
        assert "if not accepted_terms:" in fn and "return" in fn, \
            "il magic link crea di nuovo account senza consenso"
        assert 'source="signup_passwordless"' in fn, \
            "il consenso non viene timbrato alla creazione leggera"
        assert "record_aurya_consent_audit" in fn, \
            "manca l'audit immutabile del consenso (AP-L)"

    def test_password_resta_opzionale_dopo(self):
        """Chi la vuole la imposta da /account: la strada esiste ancora."""
        acc = (FRONTEND_SRC / "features" / "account" / "AccountPage.js").read_text()
        assert "pwSet" in acc, "sparita «Imposta una password» da /account"


class TestPonteLetteraAccountNl2:

    def test_ponte_dopo_ogni_iscrizione(self):
        """LeadForm serve home, blog, /newsletter e i gate delle guide:
        il ponte vive li', una volta sola, per tutte."""
        src = (FRONTEND_SRC / "features" / "prelaunch" / "LeadForm.jsx").read_text()
        assert 'data-testid="lead-account-bridge"' in src
        assert "/accedi?vista=crea&email=" in src, \
            "il ponte non porta l'email gia' compilata"
        assert "!isOperator" in src.split('data-testid="lead-account-bridge"')[0][-400:], \
            "il ponte compare anche ai lead operatore"

    def test_email_precompilata_nella_porta(self):
        src = PORTA.read_text()
        assert "params.get('email')" in src, \
            "l'email del ponte non arriva nel form"

    def test_lettera_mai_preselezionata(self):
        """Consenso marketing: la casella si spunta, non si trova spuntata."""
        src = PORTA.read_text()
        assert 'data-testid="signup-letter"' in src
        blocco = src.split('data-testid="signup-letter"')[0][-400:]
        assert "checked={wantsLetter}" in blocco
        assert "useState(false)" in src.split("const [wantsLetter")[1][:60], \
            "la casella Lettera nasce spuntata (GDPR)"

    def test_iscrizione_riusa_il_flusso_pubblico(self):
        """Nessuna scorciatoia: stesso double opt-in, stesso consenso."""
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        fn = router.split("async def _subscribe_to_letter")[1].split("\n@router")[0]
        assert "from routers.subscribers import" in fn and "subscribe" in fn, \
            "l'iscrizione dal signup non passa dalla route pubblica"
        assert "source=\"account_signup\"" in fn, "sorgente non tracciata"

    def test_iscrizione_solo_email_resta_viva(self):
        """La cattura leggera NON si tocca: e' la cima del funnel."""
        sub = (BACKEND_DIR / "routers" / "subscribers.py").read_text()
        assert '@router.post("/public/newsletter/subscribe"' in sub
        for f in ("features/frequenze/MeditazioniPage.js",
                  "features/frequenze/PublicFrequencyPage.js"):
            src = (FRONTEND_SRC / f).read_text()
            assert "/public/newsletter/subscribe" in src, \
                f"{f}: sparita l'iscrizione email-only"


class TestErroriCheAiutanoNl3:

    def test_rate_limit_spiegato(self):
        for f in ("features/account/AccountLoginPage.js",
                  "features/account/AccountResetPasswordPage.js",
                  "features/prelaunch/InlineSignupForm.js"):
            src = (FRONTEND_SRC / f).read_text()
            assert "429" in src, f"{f}: il 429 resta un «errore» muto"

    def test_requisiti_password_dicono_anche_del_breach(self):
        """Il rifiuto piu' sorprendente e' quello da data-breach: va
        annunciato PRIMA, non scoperto sbagliando."""
        for f, key in (("features/account/AccountResetPasswordPage.js", "passwordHint2"),
                       ("features/prelaunch/InlineSignupForm.js", "password_hint2")):
            src = (FRONTEND_SRC / f).read_text()
            assert key in src and "fughe di dati" in src, \
                f"{f}: l'hint non avverte del controllo sui data-breach"
