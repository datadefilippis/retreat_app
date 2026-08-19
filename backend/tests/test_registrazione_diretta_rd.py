"""Ciclo RD (19/8/2026) — registrazione diretta dalla landing
professionisti, senza toccare il flusso auth.

Il patto da difendere: il signup resta INTATTO (4 campi, verifica
email, honeypot, lockout); i campi in piu' (citta', telefono,
Instagram, discipline) si raccolgono DOPO, su /benvenuto, e finiscono
nel profilo pubblico esistente — mai in una collection parallela, mai
via email. Il form di candidatura resta vivo come via secondaria.
"""
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
PRELAUNCH = FRONTEND_SRC / "features" / "prelaunch"


class TestRegistrazioneDirettaRd:

    def test_signup_intatto(self):
        """La registrazione non guadagna campi: quelli extra vivono
        nel benvenuto. Se questo test si rompe, qualcuno sta toccando
        il flusso che il founder ha chiesto di non sfasciare."""
        auth = (FRONTEND_SRC / "pages" / "AuthPages.js").read_text()
        firma = "signup(email, password, name, organizationName, inviteToken"
        assert firma in auth, "la firma del signup e' cambiata"
        for campo in ("instagram", "disciplines", "public_phone"):
            assert campo not in auth, \
                f"{campo} non appartiene al signup: va su /benvenuto"

    def test_benvenuto_scrive_sul_profilo_esistente(self):
        """Zero modelli nuovi: /benvenuto fa PATCH sull'endpoint del
        profilo (F2.0) e SOLO su campi della whitelist."""
        src = (PRELAUNCH / "WelcomeRetePage.js").read_text()
        assert "api.patch('/organizations/current/public-profile'" in src
        for campo in ("city", "public_phone", "instagram", "disciplines"):
            assert campo in src, f"campo {campo} mancante nel benvenuto"
        # i campi vuoti non viaggiano: salvare non cancella
        assert "if (city.trim()) payload.city" in src
        # e il profilo esistente si precarica: mai sovrascritture cieche
        assert "api.get('/organizations/current/public-profile')" in src
        # saltabile: e' un benvenuto, non un cancello
        assert "welcome-skip" in src and "/inizia" in src

    def test_landing_ha_la_registrazione_incorporata(self):
        """RD-bis (founder): via il form di candidatura, all'ancora
        #presentati vive la registrazione vera. Le CTA interne scrollano
        li' — il viaggio finisce in pagina."""
        src = (PRELAUNCH / "OperatorLandingPage.js").read_text()
        assert "<InlineSignupForm" in src and 'id="presentati"' in src
        assert "<LeadForm" not in src, \
            "il form di candidatura non deve tornare su questa landing"
        # 3 CTA (hero, meta' pagina, chiusura): la quarta era il
        # bottone accanto al form, rimosso perche' ridondante
        assert src.count("href={FORM_ANCHOR} onClick={scrollToForm}") >= 3, \
            "le CTA interne devono scrollare alla registrazione"

    def test_inline_signup_e_lo_stesso_flusso(self):
        """Il form incorporato NON e' un secondo flusso: stessa
        signup() del context, stessa firma, honeypot e doppio consenso
        obbligatorio, utility riusate (non copiate)."""
        src = (PRELAUNCH / "InlineSignupForm.js").read_text()
        assert "from '../../context/AuthContext'" in src
        assert "signup(email, password, name, organizationName," in src
        assert "validatePassword, extractApiError } from '../../pages/AuthPages'" in src, \
            "le utility si importano da AuthPages, mai si copiano"
        assert "website" in src and "-9999px" in src, "honeypot mancante"
        assert "!acceptedTerms || !acceptedPrivacy" in src, \
            "i due consensi restano obbligatori anche nel form inline"
        assert "verification_required" in src and "/benvenuto" in src

    def test_niente_promesse_di_selezione(self):
        """I testi della candidatura-selezione sono morti con il
        processo che descrivevano."""
        src = (PRELAUNCH / "OperatorLandingPage.js").read_text()
        for frase in ("Leggeremo personalmente ogni candidatura",
                      "iscrizione automatica",
                      "Se penseremo che ci sia sintonia",
                      "Entriamo in contatto",
                      "Non stiamo cercando iscritti"):
            assert frase not in src, f"testo incoerente sopravvissuto: «{frase}»"
        # e le sostituzioni ci sono
        for frase in ("Si comincia da te", "Crei il tuo account in un minuto",
                      "Non cerchiamo numeri"):
            assert frase in src, f"manca la sostituzione: «{frase}»"

    def test_rete_e_shell_allineate(self):
        """L'incoerenza non vive solo sulla landing: /operatori
        prometteva «ingresso = conversazione», la shell «non e' una
        selezione». Entrambe si spostano sul RACCONTO."""
        rete = (FRONTEND_SRC / "features" / "network"
                / "NetworkOperatorsPage.js").read_text()
        assert "Ogni nuovo ingresso sarà il risultato di una conversazione" \
            not in rete
        assert "raccontata attraverso una conversazione vera" in rete
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert "Non è una selezione" not in shell
        assert "il racconto del tuo lavoro lo scriviamo insieme" in shell

    def test_rotta_benvenuto_protetta(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        blocco = app.split('path="/benvenuto"')[1][:220]
        assert "ProtectedRoute" in blocco, \
            "/benvenuto scrive sul profilo: serve l'account"
