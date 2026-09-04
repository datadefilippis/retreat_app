"""RU — Registrazione Unica (4/9/2026, founder).

Su /accedi?vista=crea il box «Sei un professionista del benessere?»
rimandava a /entra-nella-rete: due form separati, con la landing lunga
e il form in fondo. Il founder: «basterebbe un flag che, se
selezionato, riadatta il form e l'utente si registra come operatore
dalla stessa schermata, senza redirect»; il testo dell'interruttore
piu' grande e visibile; ENTRAMBE le registrazioni (solo utente o
operatore) dalla stessa pagina; /entra-nella-rete resta com'e'.

Decisioni founder: nome attivita' obbligatorio (diventa il profilo
pubblico), la spunta del Cerchio resta possibile ANCHE per il
professionista (viaggia sul suo flusso double opt-in), deep link
?pro=1 che accende l'interruttore da URL.

Perche' solo frontend: la policy password e' la stessa per i due
cappelli, il backend operatore riceve UN booleano accepted_terms (una
spunta con i due link basta), e signup() di AuthContext era gia'
condivisa tra SignupPage e InlineSignupForm — la scheda unica e' il
terzo consumatore, zero logica duplicata.

Le guardie ID-septies (split una volta sola, sopra il form, mai sul
login) e LR1 (link a /entra-nella-rete) restano vere: lo stesso box
`operator-rescue-link` ospita l'interruttore e il link «Come funziona».
"""
from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
PORTA = FRONTEND_SRC / "features" / "account" / "AccountLoginPage.js"
LANDING = FRONTEND_SRC / "features" / "prelaunch" / "InlineSignupForm.js"


def _vista_signup(src: str) -> str:
    return src.split("{state === 'signup' && (")[1].split("{state === 'signupSent'")[0]


class TestInterruttoreNellaStessaScheda:

    def test_lo_split_e_un_interruttore_non_un_rimando(self):
        """Il box dei professionisti contiene la spunta che riadatta la
        scheda; il link a /entra-nella-rete resta (LR1), ma secondario."""
        src = PORTA.read_text()
        box = src.split('data-testid="operator-rescue-link"')[1].split("</div>\n            </div>")[0]
        assert 'data-testid="signup-pro-toggle"' in box, \
            "l'interruttore professionista non sta nel box dello split"
        assert 'to="/entra-nella-rete"' in box, \
            "il link «come funziona» a /entra-nella-rete e' sparito dal box"
        assert "onChange={e => togglePro(e.target.checked)}" in box

    def test_il_testo_dell_interruttore_e_piu_grande(self):
        """Founder: «il testo sei un operatore leggermente piu' grande e
        visibile». Era text-xs; ora e' text-sm e in grassetto."""
        src = PORTA.read_text()
        label = src.split('htmlFor="signup-pro-toggle"')[1].split("</label>")[0]
        assert "text-sm font-semibold" in label
        assert "Sono un professionista del benessere" in label

    def test_uscendo_dalla_registrazione_si_spegne(self):
        """RU-bis (founder 4/9): «procedi a resettare il flag». Tornando
        al login o dopo l'invio l'interruttore si spegne e ?pro sparisce:
        la scheda riparte sempre neutra, il deep link vale per l'arrivo."""
        src = PORTA.read_text()
        goto = src.split("const goTo = (view) => {")[1].split("\n  };")[0]
        assert "if (view !== 'signup' && isPro) togglePro(false);" in goto

    def test_deep_link_pro_accende_l_interruttore(self):
        """?pro=1 accende l'interruttore da URL e spegnerlo lo toglie:
        domani il menu «Diventa professionista Aurya» puo' puntarci."""
        src = PORTA.read_text()
        assert "useState(params.get('pro') === '1')" in src
        assert "p.set('pro', '1'); else p.delete('pro');" in src


class TestRegistrazioneOperatoreDallaScheda:

    def test_usa_la_stessa_signup_di_entra_nella_rete(self):
        """Zero backend nuovo: il ramo pro chiama signup() di AuthContext,
        la stessa funzione di InlineSignupForm (stesso endpoint
        /api/auth/signup, stesso honeypot, stesso 202)."""
        src = PORTA.read_text()
        assert "const { signup: operatorSignup } = useAuth();" in src
        assert "await operatorSignup(email.trim(), password, name.trim(), orgName.trim()," in src
        landing = LANDING.read_text()
        assert "const { signup } = useAuth();" in landing, \
            "/entra-nella-rete non usa piu' la signup condivisa"

    def test_nome_attivita_obbligatorio_e_honeypot(self):
        """Decisione founder: il nome dell'attivita' e' obbligatorio come
        in /entra-nella-rete; il campo-esca c'e' anche qui."""
        vista = _vista_signup(PORTA.read_text())
        org = vista.split('data-testid="signup-org"')[0].rsplit("<input", 1)[1]
        assert "required" in org and "value={orgName}" in org
        assert 'name="website"' in vista and "tabIndex={-1}" in vista

    def test_il_ramo_pro_sta_dentro_submit_signup(self):
        """Un solo submit per la scheda: il ramo professionista e' il
        primo passo di submitSignup, il ramo account resta com'era
        (la guardia NL1 lo legge nello stesso blocco)."""
        src = PORTA.read_text()
        blocco = src.split("const submitSignup =")[1].split("\n  };")[0]
        assert "if (isPro) {" in blocco
        assert "setState('signupSentPro');" in blocco
        assert "'/platform/auth/signup'" in blocco

    def test_email_gia_usata_parla_chiaro(self):
        src = PORTA.read_text()
        assert "proSignupExists" in src
        assert "ha già uno spazio su Aurya" in src

    def test_esito_dedicato_per_l_operatore(self):
        """Dopo l'invio l'operatore legge la SUA strada: verifica email,
        poi login e benvenuto (ID-octies) — non «entri nel tuo account»."""
        src = PORTA.read_text()
        assert "{state === 'signupSentPro' && (" in src
        assert 'data-testid="signup-sent-pro-body"' in src
        assert "ti guidiamo nel tuo spazio" in src


class TestCosaCambiaConLInterruttore:

    def test_cerchio_possibile_anche_per_l_operatore(self):
        """Founder 4/9: «la spunta entra anche nel cerchio teniamola
        possibile anche nel caso di operatore». La spunta non e'
        condizionata da isPro e nel ramo pro parte l'iscrizione sul
        flusso double opt-in, best-effort e con la sua sorgente."""
        src = PORTA.read_text()
        vista = _vista_signup(src)
        prima = vista.split('data-testid="signup-letter"')[0]
        assert not prima.rstrip().endswith("{!isPro && ("), \
            "la spunta del Cerchio e' sparita per l'operatore"
        assert "{!isPro && (\n              <label" not in vista
        ramo = src.split("if (isPro) {")[1].split("return;")[0]
        assert "api.post('/public/newsletter/subscribe'" in ramo
        assert "source: 'signup_pro'" in ramo
        assert "if (wantsLetter) {" in ramo

    def test_senza_password_solo_per_l_account_personale(self):
        """Il magic link non esiste sul cappello operatore: con
        l'interruttore acceso l'alternativa sparisce."""
        vista = _vista_signup(PORTA.read_text())
        assert ("{!isPro && (\n            <button type=\"button\" "
                "onClick={submitSignupNoPassword}") in vista, \
            "«senza password» e' visibile anche con l'interruttore acceso"

    def test_titolo_bottone_e_nome_seguono_l_interruttore(self):
        vista = _vista_signup(PORTA.read_text())
        assert "'Apri il tuo spazio su Aurya'" in vista
        assert "'Crea il tuo spazio'" in vista
        assert 'autoComplete="name" required={isPro}' in vista
        # il mondo personale resta detto com'era (ID-ter)
        assert "signupBody2" in vista and "per chi partecipa" in vista

    def test_entra_nella_rete_non_si_tocca(self):
        """La registrazione sulla landing resta identica: stesso form,
        stessa ancora, stessi consensi."""
        landing = LANDING.read_text()
        for marker in ('data-testid="ol-inline-signup"',
                       'data-testid="ol-consent-privacy"',
                       'data-testid="ol-consent-terms"',
                       'data-testid="ol-signup-submit"',
                       "navigate('/benvenuto')"):
            assert marker in landing, f"/entra-nella-rete e' cambiata: {marker}"
