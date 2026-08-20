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
    """NL1-bis (decisione founder 20/8): la password e' la strada
    PRINCIPALE, «senza password» resta un'alternativa dichiarata. Il
    funnel non si rompe come prima perche' i requisiti si spuntano
    mentre si scrive, invece di essere scoperti sbagliando."""

    def test_password_primaria_con_alternativa(self):
        src = PORTA.read_text()
        blocco = src.split("const submitSignup =")[1].split("\n  };")[0]
        assert "'/platform/auth/signup'" in blocco and "password," in blocco, \
            "la registrazione principale non usa piu' la password"
        vista = src.split("{state === 'signup' && (")[1].split("{state === 'signupSent'")[0]
        assert 'data-testid="signup-password"' in vista, \
            "manca il campo password nella registrazione"
        assert 'data-testid="signup-no-password"' in vista, \
            "sparita l'alternativa senza password"
        alt = src.split("const submitSignupNoPassword")[1].split("\n  };")[0]
        assert "'/platform/auth/magic-link'" in alt and "accepted_terms: true" in alt, \
            "la via senza password non passa dal magic link col consenso"

    def test_requisiti_password_dal_vivo(self):
        """Il vero fix del muro: i requisiti si accendono mentre scrivi
        e il bottone resta spento finche' non sono soddisfatti."""
        src = PORTA.read_text()
        assert 'data-testid="pw-checklist"' in src and "const pwChecks" in src
        assert "disabled={sending || !pwOk}" in src, \
            "si puo' ancora inviare una password che sara' rifiutata"
        assert "pwBreach" in src, \
            "la checklist non avverte del controllo sui data-breach"

    def test_una_sola_strada_per_tipo(self):
        """Due strade dichiarate (password / link), nessuna terza via
        nascosta: la leggera E' il find-or-create del magic link."""
        svc = SVC.read_text()
        fn = svc.split("async def request_magic_link")[1].split("\nasync def")[0]
        assert "insert_one" in fn and "accepted_terms" in fn
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        assert router.count('@router.post("/auth/signup"') == 1, \
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

    def test_password_impostabile_anche_dopo(self):
        """Chi entra dalla via senza password deve poterla aggiungere."""
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

    def test_lettera_su_entrambe_le_strade(self):
        """La casella vale sia col signup password sia col link."""
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        assert router.count("await _subscribe_to_letter(request") == 2, \
            "una delle due strade di registrazione ignora la Lettera"
        assert "wants_newsletter" in router.split(
            "class PasswordSignup")[1].split("\n\n")[0], \
            "il signup con password non accetta l'opt-in Lettera"

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


class TestIndirizzoDichiaratoNlBis:
    """NL-bis (20/8, founder) — la Lettera vive sull'INDIRIZZO, non
    sull'account: chi si iscrive con un'email diversa dalla sua legge
    poi «non ricevi la lettera» nel gestionale, e si iscrive due volte.
    Il rimedio non e' cambiare la regola (il consenso appartiene alla
    casella) ma renderla VISIBILE."""

    LEAD = FRONTEND_SRC / "features" / "prelaunch" / "LeadForm.jsx"

    def test_email_precompilata_per_chi_e_loggato(self):
        src = self.LEAD.read_text()
        assert "useAuth" in src and "accountEmail" in src
        assert "setEmail((cur) => cur || accountEmail)" in src, \
            "la precompilazione sovrascriverebbe quello che l'utente ha scritto"
        assert "'/platform/me'" in src, \
            "il cliente loggato non viene riconosciuto (solo l'operatore)"

    def test_avviso_se_l_indirizzo_e_diverso(self):
        src = self.LEAD.read_text()
        assert 'data-testid="lead-other-email"' in src
        blocco = src.split('data-testid="lead-other-email"')[0][-400:]
        assert "toLowerCase() !== accountEmail.toLowerCase()" in blocco, \
            "il confronto e' sensibile a maiuscole: falsi avvisi"
        assert "!isOperator" in blocco, \
            "l'avviso compare anche sul form di candidatura operatori"

    def test_l_avviso_non_blocca(self):
        """Resta una scelta: informiamo, non impediamo."""
        src = self.LEAD.read_text()
        avviso = src.split('data-testid="lead-other-email"')[1][:400]
        assert "disabled" not in avviso, \
            "l'avviso e' diventato un blocco: l'indirizzo resta una scelta"

    def test_le_superfici_dichiarano_su_cosa_guardano(self):
        card = (FRONTEND_SRC / "features" / "settings" / "sections"
                / "LetterCard.jsx").read_text()
        assert 'data-testid="letter-address"' in card and "letter.address" in card, \
            "la card non dice su quale indirizzo sta guardando"
        acc = (FRONTEND_SRC / "features" / "account" / "AccountPage.js").read_text()
        assert 'data-testid="guides-address"' in acc, \
            "/account non dice su quale indirizzo sta guardando"
        be = (BACKEND_DIR / "routers" / "unified_auth.py").read_text()
        assert '"email": current_user.get("email")' in be, \
            "l'endpoint non restituisce l'indirizzo osservato"


class TestPonteConsapevoleNlTer:
    """NL-ter (20/8, founder) — «se sono già loggato, l'invito a creare
    l'account non dovrebbe apparire»: giusto. A chi è dentro non si
    propone una cosa già fatta; lo si porta dove vedrà l'iscrizione."""

    LEAD = FRONTEND_SRC / "features" / "prelaunch" / "LeadForm.jsx"

    def test_niente_invito_a_chi_e_gia_dentro(self):
        src = self.LEAD.read_text()
        ponte = src.split('data-testid="lead-account-bridge"')[0][-260:]
        assert "!accountEmail" in ponte, \
            "l'invito a creare l'account compare anche a chi ce l'ha gia'"

    def test_a_chi_e_dentro_si_indica_dove_guardare(self):
        src = self.LEAD.read_text()
        assert 'data-testid="lead-account-here"' in src
        blocco = src.split('data-testid="lead-account-here"')[0][-300:]
        assert "email.trim().toLowerCase() === accountEmail.toLowerCase()" in blocco, \
            "il messaggio «lo trovi nel tuo account» compare anche a chi si e'"\
            " iscritto con un ALTRO indirizzo, dove l'iscrizione non risultera'"
        dopo = src.split('data-testid="lead-account-here"')[1][:400]
        assert 'href="/account"' in dopo, "manca la via verso l'account"


class TestGuideSbloccateDallaSessioneNlQuater:
    """NL-quater (20/8, founder) — «sono iscritto e loggato, ma la guida
    mi chiede ancora l'email». Causa: lo sblocco guardava SOLO il
    subscriber token nel browser — una fotografia scattata al login.
    Chi si iscrive dopo, chi conferma da un altro dispositivo, e ogni
    OPERATORE (il cui login non portava quel token) restava fuori."""

    ART = BACKEND_DIR / "routers" / "articles.py"

    def test_la_sessione_sblocca(self):
        src = self.ART.read_text()
        assert "_session_unlocked" in src
        # NL-quinquies ha unificato le due condizioni in out["subscriber"]:
        # quello che conta e' che la SESSIONE partecipi allo sblocco
        assert "or await _session_unlocked(request)" in src, \
            "la guida guarda ancora solo il token nel browser"
        assert 'if out["subscriber"]:' in src, \
            "il cancello non usa piu' la verita' condivisa"

    def test_sblocca_solo_se_confermato(self):
        """Essere loggati non basta: serve l'iscrizione CONFERMATA."""
        src = self.ART.read_text()
        fn = src.split("async def _session_unlocked")[1].split("\n@router")[0]
        assert 'doc.get("status") == "confirmed"' in fn, \
            "basterebbe una sessione qualsiasi per leggere le guide"

    def test_lettore_anonimo_mai_un_errore(self):
        src = self.ART.read_text()
        fn = src.split("async def _email_from_session")[1].split("\nasync def")[0]
        assert "return None" in fn and "except Exception" in fn, \
            "un token scaduto farebbe fallire la pagina invece di servire"\
            " l'anteprima"

    def test_il_token_arriva_da_entrambi_i_cappelli(self):
        be = (BACKEND_DIR / "routers" / "unified_auth.py").read_text()
        blocco = be.split("worlds.append({")[1][:400]
        assert "newsletter_status(email)" in blocco, \
            "il login operatore non porta il token delle guide"
        fe = (FRONTEND_SRC / "features" / "account" / "AccountLoginPage.js").read_text()
        op = fe.split("if (w.type === 'operator')")[1][:400]
        assert "saveSubscriberToken(w)" in op, \
            "il frontend scarta il token quando arriva dal cappello operatore"


class TestNienteInvitiAChiEIscrittoNlQuinquies:
    """NL-quinquies (20/8) — «sono iscritto ma la pagina mi chiede
    ancora di iscrivermi»: non era il cancello della guida (quello si
    apriva), era l'invito in fondo all'ARTICOLO, che non sapeva nulla
    di chi legge. Chi lo seguiva riceveva una seconda email di conferma
    senza capire perche'."""

    ART = BACKEND_DIR / "routers" / "articles.py"
    PAGE = FRONTEND_SRC / "features" / "storefront" / "BlogArticlePage.js"

    def test_l_articolo_dice_se_chi_legge_e_iscritto(self):
        src = self.ART.read_text()
        assert 'out["subscriber"] = (await _subscriber_unlocked(st)' in src, \
            "l'articolo non dichiara se chi lo chiede e' iscritto"
        # il flag vale su TUTTI gli articoli, non solo le guide riservate
        i_flag = src.index('out["subscriber"]')
        i_gate = src.index('if out["gated"]:')
        assert i_flag < i_gate, \
            "il flag e' calcolato solo dentro il ramo delle guide riservate"

    def test_una_sola_verita_per_lo_sblocco(self):
        """Il gate riusa lo stesso flag: niente doppia valutazione che
        puo' divergere."""
        src = self.ART.read_text()
        blocco = src.split('if out["gated"]:')[1][:200]
        assert 'if out["subscriber"]:' in blocco, \
            "il cancello ricalcola lo sblocco per conto suo"

    def test_la_cta_tace_con_gli_iscritti(self):
        src = self.PAGE.read_text()
        assert "article.subscriber ?" in src, \
            "l'invito in fondo all'articolo ignora chi e' gia' iscritto"
        blocco = src.split("article.subscriber ?")[1][:400]
        assert "null" in blocco.split("BlogNewsletterCTA")[0], \
            "per gli iscritti si mostra ancora qualcosa al posto dell'invito"
