"""FL (5/10/2026 sera) — «Iscrizione senza attrito». Piano:
docs/PIANO_ISCRIZIONE_SENZA_ATTRITO_2026-10-05.md. Un file di guardia, una
classe per lotto.

FL2: il pulsante dell'email apre davvero. Il link verificante (/v/{token})
e «entro nel Cerchio» (/entra/{token}) portano la prova nel redirect
(`?prova=<token>`); il browser la salva PRIMA del primo render e la toglie
dall'indirizzo (lib/cerchio.raccogliProvaDaUrl, chiamata in index.js).
"""
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

import pytest
import requests

RADICE = Path(__file__).resolve().parents[2]
BACKEND = RADICE / "backend"
FE = RADICE / "frontend" / "src"
API = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8000") + "/api"


def _vivo():
    try:
        return requests.get(API + "/health", timeout=2).status_code == 200
    except Exception:  # noqa: BLE001
        return False


class TestFL2Prova:
    def test_con_prova(self):
        from routers.subscribers import _con_prova
        t = "a.b.c"
        assert _con_prova("/meditazioni", t) == "/meditazioni?prova=a.b.c"
        assert _con_prova("/blog/guida?x=1", t) == "/blog/guida?x=1&prova=a.b.c"
        assert _con_prova("/frequenze/calm#ascolta", t) == "/frequenze/calm?prova=a.b.c#ascolta"      # l'ancora resta in coda
        assert _con_prova("/newsletter/conferma/a.b.c", t) == "/newsletter/conferma/a.b.c"   # la pagina salva da sola
        assert _con_prova("/x?prova=gia", t) == "/x?prova=gia"
        assert _con_prova("", t) == "" and _con_prova("/x", "") == "/x"
        assert _con_prova("/x", "a b/c") == "/x?prova=a%20b%2Fc"                              # sempre codificato

    def test_redirect_dal_vivo(self):
        if not _vivo():
            pytest.skip("backend locale spento")
        from core.subscriber_token import generate_subscriber_token
        token = generate_subscriber_token("fl2-prova@example.com")
        r = requests.get(API + f"/public/newsletter/v/{token}", params={"to": "/meditazioni"},
                         allow_redirects=False, timeout=10)
        assert r.status_code == 302
        assert r.headers["location"].endswith("/meditazioni?prova=" + quote(token, safe="")), r.headers["location"]
        # token rotto: si va lo stesso alla pagina, ma SENZA prova
        r = requests.get(API + "/public/newsletter/v/non.un.token", params={"to": "/meditazioni"},
                         allow_redirects=False, timeout=10)
        assert r.status_code == 302 and "prova=" not in r.headers["location"]
        # percorso esterno: mai un open redirect (si va a «/», con la prova)
        r = requests.get(API + f"/public/newsletter/v/{token}", params={"to": "https://evil.example/"},
                         allow_redirects=False, timeout=10)
        assert r.status_code == 302 and "evil" not in r.headers["location"] and "prova=" in r.headers["location"]
        # /entra senza `to` va alla pagina di conferma (che salva da sola): niente doppio token
        r = requests.get(API + "/public/newsletter/entra/non.un.token", allow_redirects=False, timeout=10)
        assert r.status_code == 302 and r.headers["location"].endswith("/newsletter")

    def test_browser_raccoglie_e_pulisce(self):
        """Il modulo gira in node: salva la prova, toglie il parametro, ignora il resto."""
        import shutil
        node = shutil.which("node")
        if not node:
            pytest.skip("node assente")
        fe = RADICE / "frontend"
        prova = tempfile.NamedTemporaryFile("w", suffix=".js", dir=str(fe), delete=False)
        prova.write(r"""
const babel = require('@babel/core'); const path = require('path'); const Module = require('module');
process.env.NODE_ENV = 'development';
const cache = {};
function carica(rel) {
  const file = path.join(__dirname, 'src', rel);
  if (cache[file]) return cache[file].exports;
  const out = babel.transformFileSync(file, {presets: ['babel-preset-react-app'], babelrc: false, configFile: false}).code;
  const m = new Module(file, module); m.filename = file; m.paths = Module._nodeModulePaths(path.dirname(file)); cache[file] = m;
  m.require = (p) => p.startsWith('.') ? carica(path.relative(path.join(__dirname,'src'), path.resolve(path.dirname(file), p)) + '.js') : (p === '../api/client' ? {} : require(p));
  m._compile(out, file); return m.exports;
}
const store = {}; global.localStorage = { getItem: (k) => store[k] ?? null, setItem: (k, v) => { store[k] = String(v); }, removeItem: (k) => { delete store[k]; } };
let href = 'https://aurya.life/meditazioni?utm_source=x&prova=aaa.bbb.ccc#top'; const replaced = [];
global.window = { get location() { return { href }; }, history: { state: null, replaceState: (s, t, u) => { replaced.push(u); } } };
const c = carica('lib/cerchio.js');
console.assert(c.raccogliProvaDaUrl() === true, 'salva');
console.assert(store['aurya_nl_token'] === 'aaa.bbb.ccc', 'token salvato: ' + store['aurya_nl_token']);
console.assert(replaced[0] === '/meditazioni?utm_source=x#top', 'url pulito: ' + replaced[0]);
href = 'https://aurya.life/meditazioni'; console.assert(c.raccogliProvaDaUrl() === false, 'senza parametro');
delete store['aurya_nl_token']; href = 'https://aurya.life/x?prova=non-un-jwt';
console.assert(c.raccogliProvaDaUrl() === false && store['aurya_nl_token'] === undefined, 'ignora chi non e un jwt');
console.assert(replaced[1] === '/x', 'pulisce comunque: ' + replaced[1]);
console.log('OK');
""")
        prova.close()
        try:
            r = subprocess.run([node, prova.name], cwd=str(fe), capture_output=True, text=True, timeout=120)
        finally:
            os.unlink(prova.name)
        assert r.returncode == 0 and "OK" in r.stdout and "Assertion failed" not in r.stderr, r.stdout + r.stderr

    def test_agganci_nel_codice(self):
        idx = (FE / "index.js").read_text(encoding="utf-8")
        assert 'import { raccogliProvaDaUrl } from "@/lib/cerchio";' in idx
        assert idx.index("raccogliProvaDaUrl();") < idx.index("root.render(")      # PRIMA del primo render
        sub = (BACKEND / "routers" / "subscribers.py").read_text(encoding="utf-8")
        assert "dove = _con_prova(dove, token)" in sub and "build_public_url(_con_prova(dove, token))" in sub
        med = (FE / "features" / "frequenze" / "MeditazioniPage.js").read_text(encoding="utf-8")
        assert "useState(() => emailDellaProva() || '')" in med


class TestFL1Esito:
    """FL1 — il risultato si vede dove hai cliccato: UN helper (lib/esito.js,
    <Esito>), montato su ogni box di successo; via i due reload del blog."""

    PUNTI = (
        ("features/prelaunch/LeadForm.jsx", 'data-testid="lead-esito"'),
        ("features/frequenze/InvitoSound.jsx", '<Esito as="p"'),
        ("features/storefront/components/checkout/GrazieCerchio.jsx", '<Esito as="p"'),
        ("features/account/PortaAurya.jsx", '<Esito className="rounded-lg border border-emerald-200'),
        ("features/prelaunch/InlineSignupForm.js", '<Esito className="text-center py-6" data-testid="ol-signup-verify">'),
        ("features/frequenze/ProfessionalLanding.jsx", 'data-testid="prof-grazie"'),
        ("features/frequenze/CreaStudioLanding.jsx", 'data-testid="studio-grazie"'),
        ("features/network/AziendePage.js", '<Esito data-testid="az-fatto"'),
        ("features/frequenze/CancelloLettera.jsx", 'data-testid="cancello-attesa"'),
        ("features/frequenze/MeditazioniPage.js", 'data-testid="med-attesa-conferma"'),
        ("features/frequenze/SoundHomePage.jsx", '<Esito data-testid="sh-anteprima-sbloccata">'),
        ("features/account/AccountLoginPage.js", '<Esito data-testid="signup-sent-esito">'),
        ("features/storefront/components/ContattiOperatore.jsx", 'data-testid="contatti-aperti"'),
        ("features/storefront/OperatorProfilePage.js", '<Esito className="text-center py-4" data-testid="review-done">'),
    )

    def test_ogni_punto_usa_esito(self):
        for rel, pin in self.PUNTI:
            src = (FE / rel).read_text(encoding="utf-8")
            assert "from '" in src and "/lib/esito'" in src, rel
            assert pin in src, (rel, pin)
            # il tag si apre e si chiude lo stesso numero di volte
            assert src.count("<Esito") == src.count("</Esito>"), rel
        acc = (FE / "features" / "account" / "AccountLoginPage.js").read_text(encoding="utf-8")
        assert '<Esito data-testid="signup-sent-pro-esito">' in acc and 'data-testid="signup-sent-pro-cerchio"' in acc
        blog = (FE / "features" / "storefront" / "BlogArticlePage.js").read_text(encoding="utf-8")
        assert "window.location.reload()" not in blog and "onSbloccato={ricarica}" in blog
        assert "}, [slug, lang, versione]);" in blog

    def test_helper_in_node(self):
        import shutil
        node = shutil.which("node")
        if not node:
            pytest.skip("node assente")
        fe = RADICE / "frontend"
        prova = tempfile.NamedTemporaryFile("w", suffix=".js", dir=str(fe), delete=False)
        prova.write(r"""
const babel = require('@babel/core'); const path = require('path'); const Module = require('module');
process.env.NODE_ENV = 'development';
function carica(rel) {
  const file = path.join(__dirname, 'src', rel);
  const out = babel.transformFileSync(file, {presets: ['babel-preset-react-app'], babelrc: false, configFile: false}).code;
  const m = new Module(file, module); m.filename = file; m.paths = Module._nodeModulePaths(path.dirname(file));
  m._compile(out, file); return m.exports;
}
global.window = { innerHeight: 800, matchMedia: () => ({ matches: false }) }; global.document = { documentElement: { clientHeight: 800 } };
const e = carica('lib/esito.js');
const fuori = { chiamate: [], getBoundingClientRect: () => ({ top: 1200, bottom: 1300 }), scrollIntoView(o) { this.chiamate.push(['scroll', o]); }, focus(o) { this.chiamate.push(['focus', o]); } };
console.assert(e.mostraEsito(fuori) === true, 'ritorna true');
console.assert(fuori.chiamate.length === 2 && fuori.chiamate[0][0] === 'scroll' && fuori.chiamate[0][1].block === 'center' && fuori.chiamate[0][1].behavior === 'smooth', 'scorre al centro, morbido');
console.assert(fuori.chiamate[1][0] === 'focus' && fuori.chiamate[1][1].preventScroll === true, 'focus senza riscorrere');
const dentro = { chiamate: [], getBoundingClientRect: () => ({ top: 100, bottom: 300 }), scrollIntoView(o) { this.chiamate.push(['scroll', o]); }, focus(o) { this.chiamate.push(['focus', o]); } };
e.mostraEsito(dentro);
console.assert(dentro.chiamate.length === 1 && dentro.chiamate[0][0] === 'focus', 'gia visibile: solo il focus');
global.window.matchMedia = () => ({ matches: true });
const ridotto = { chiamate: [], getBoundingClientRect: () => ({ top: -500, bottom: -400 }), scrollIntoView(o) { this.chiamate.push(['scroll', o]); }, focus() {} };
e.mostraEsito(ridotto);
console.assert(ridotto.chiamate[0][1].behavior === 'auto', 'reduced motion: secco');
console.assert(e.mostraEsito(null) === false, 'null tollerato');
console.log('OK');
""")
        prova.close()
        try:
            r = subprocess.run([node, prova.name], cwd=str(fe), capture_output=True, text=True, timeout=120)
        finally:
            os.unlink(prova.name)
        assert r.returncode == 0 and "OK" in r.stdout and "Assertion failed" not in r.stderr, r.stdout + r.stderr


class TestFL4Testo:
    """FL4 — una frase sola per «sei dentro, cosa succede adesso», vera (FL2),
    senza declinazioni; i tre form del Cerchio la leggono da lib/cerchio.js."""

    def test_frase_unica(self):
        c = (FE / "lib" / "cerchio.js").read_text(encoding="utf-8")
        assert "export const TESTO_BENVENUTO = 'Sei nel Cerchio: la prima Lettera è in arrivo" in c
        assert "export const TESTO_CONFERMA = 'Ti abbiamo scritto:" in c
        assert "export const testoEsito = () => (_ultimaModalita === 'benvenuto' ? TESTO_BENVENUTO : TESTO_CONFERMA);" in c
        lead = (FE / "features" / "prelaunch" / "LeadForm.jsx").read_text(encoding="utf-8")
        assert "defaultValue: TESTO_BENVENUTO" in lead and "Benvenuto.'" not in lead
        assert "defaultValue: 'Ci sei.' }" in lead
        inv = (FE / "features" / "frequenze" / "InvitoSound.jsx").read_text(encoding="utf-8")
        assert ": testoEsito()}" in inv and "apre anche le meditazioni intere" not in inv
        gr = (FE / "features" / "storefront" / "components" / "checkout" / "GrazieCerchio.jsx").read_text(encoding="utf-8")
        assert "{testoEsito()}" in gr and "la prima Lettera sta arrivando" not in gr
        import json
        it = json.loads((FE / "locales" / "it" / "prelaunch.json").read_text(encoding="utf-8"))
        assert it["form"]["thanksTitle"] == "Ci sei."
        # mai piu' «Benvenuto» come saluto nei testi di successo dei form
        for rel in ("features/prelaunch/LeadForm.jsx", "features/frequenze/InvitoSound.jsx",
                    "features/storefront/components/checkout/GrazieCerchio.jsx", "lib/cerchio.js"):
            assert "Benvenuto." not in (FE / rel).read_text(encoding="utf-8"), rel


class TestFL5VerificaEntra:
    """FL5 — il clic di verifica dell'account cliente FA ENTRARE (stessa
    sessione del magic link), come per il professionista; token rotto = 400."""

    def test_nel_codice(self):
        r = (BACKEND / "routers" / "platform_accounts.py").read_text(encoding="utf-8")
        i = r.index("async def verify_email_ep(")
        blocco = r[i:i + 2500]
        assert "esito = await verify_signup_email(body.token)" in blocco
        assert 'if account and account.get("is_active", True):' in blocco
        assert "expires_delta=timedelta(days=PLATFORM_SESSION_DAYS)" in blocco
        assert '**await newsletter_status(account["email"])' in blocco           # anche la prova del Cerchio, se c'e'
        s = (BACKEND / "services" / "platform_account_service.py").read_text(encoding="utf-8")
        assert '"account_id": account["id"]}' in s
        p = (FE / "features" / "account" / "AccountVerifyEmailPage.js").read_text(encoding="utf-8")
        assert "localStorage.setItem(PLATFORM_TOKEN_KEY, d.access_token);" in p
        assert "if (d.subscriber_token) salvaProva(d.subscriber_token);" in p
        assert 'data-testid="verify-vai"' in p and 'data-testid="verify-torna"' in p    # la strada di ieri resta

    def test_token_rotto_dal_vivo(self):
        if not _vivo():
            pytest.skip("backend locale spento")
        r = requests.post(API + "/platform/auth/verify-email", json={"token": "non-esiste"}, timeout=10)
        assert r.status_code == 400 and "access_token" not in r.text


class TestFL3Email:
    """FL3 — le email automatiche nelle parole del founder (docs/EMAIL_COPY_2026-10
    + la sua versione): una voce, mai declinate, un passo successivo; le parole
    proibite non rientrano; ogni template si renderizza pieno e vuoto."""

    PROIBITE = ("con successo", "click", "pack ", "upgrade", "regolarizzare", "Benvenuto nel", "Sei stato",
                "sei stato tu", "iscritto tu", "con lui", "gestione finanziaria", "la tua posizione",
                "partecipante,", "dettalo", "Conformemente", "storefront", "Ti contatteremo")
    FILE = ("services/email_sequenze.py", "services/cerchio_reminder.py", "routers/subscribers.py",
            "services/platform_account_service.py", "services/strutture_email.py", "services/review_service.py",
            "services/order_email_service.py", "services/payment_email_service.py", "services/event_email_service.py",
            "services/quota_email_service.py")

    def _it(self):
        from services.email_service import EMAIL_TRANSLATIONS
        return EMAIL_TRANSLATIONS["it"]

    def test_parole_proibite(self):
        import ast as _ast
        import re as _re
        for rel in self.FILE:
            tree = _ast.parse((BACKEND / rel).read_text(encoding="utf-8"))
            # solo le STRINGHE del codice (quello che finisce nelle email), mai docstring e commenti
            doc = set()
            for n in _ast.walk(tree):
                if isinstance(n, (_ast.Module, _ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)) and n.body \
                        and isinstance(n.body[0], _ast.Expr) and isinstance(getattr(n.body[0], "value", None), _ast.Constant):
                    doc.add(id(n.body[0].value))
            corpo = "\n".join(n.value for n in _ast.walk(tree)
                              if isinstance(n, _ast.Constant) and isinstance(n.value, str) and id(n) not in doc)
            for p in self.PROIBITE:
                assert not _re.search(r"(?<![\w_])" + _re.escape(p.strip()) + r"(?![\w_])", corpo), (rel, p)   # parole intere («click», non click_ids)
        for k, v in self._it().items():
            for p in self.PROIBITE:
                assert not _re.search(r"(?<![\w_])" + _re.escape(p.strip()) + r"(?![\w_])", v), (k, p)
            # accenti veri nei testi italiani (mai e' / piu' / gia' / sara')
            assert not _re.search(r"\b(e|piu|gia|sara|puo|perche)'", v), (k, v)

    def test_piede_unico(self):
        from services.email_service import _wrap_template
        html = _wrap_template("<p>x</p>", "it")
        assert "Ritiri ed esperienze olistiche, in un posto solo" in html and "aurya.life" in html
        assert "Per rispondere, scrivi a" not in html and "non rispondere" not in html

    def test_cerchio_e_sequenze_piene_e_vuote(self):
        import services.email_sequenze as T
        pieno = {"nome": "Anna", "email": "a@b.it", "token": "tok", "citta": "Bari", "interessi": ["yoga", "suono"],
                 "travel": "near", "vuole_ritiri": True, "porta": "altro"}
        vuoto = {"nome": "", "email": "a@b.it", "token": "tok"}
        o, c = T.benvenuto_cerchio_ritiri(pieno)
        assert o == "Sei nel Cerchio di Aurya"
        assert "Sappiamo che ti interessano lo yoga e il suono e i ritiri di Aurya a Bari (zona)." in c
        assert "interessato" not in c and "Benvenuto" not in c
        _, c2 = T.benvenuto_cerchio_ritiri(vuoto)
        assert "Sappiamo che ti interessano gli eventi e i ritiri di Aurya." in c2 and "Le mie preferenze" in c2
        _, c3 = T.benvenuto_cerchio_ritiri({**pieno, "interessi": [], "travel": "abroad"})
        assert "gli eventi e i ritiri di Aurya in Italia o all'estero." in c3
        for fn, sogg in ((T.benvenuto_cerchio_meditazioni, "Sei nel Cerchio: le meditazioni sono aperte"),
                         (T.benvenuto_cerchio_generico, "Sei nel Cerchio di Aurya")):
            for ctx in (pieno, vuoto):
                o, c = fn(ctx)
                assert o == sogg and "Ciao" in c and "Valentina e Davide" in c and "{" not in c
        on = {"nome": "Anna", "stato": {"pagina": True, "online": True, "slug": "anna", "n_servizi": 0}}
        off = {"nome": "", "stato": {}}
        attesi = {T.op_profilo_online: "La tua pagina è online: ecco il link", T.op_canali: "I canali della rete Aurya",
                  T.op_np10: "Le tre cose che fermano una pagina", T.op_np15: "Grazie di essere su Aurya",
                  T.op_r14: "Vuoi pubblicare i tuoi ritiri su Aurya?"}
        for fn, sogg in attesi.items():
            o, c = fn(on)
            assert o == sogg and "{" not in c, fn.__name__
            assert 'class="btn"' in c or fn is T.op_canali, fn.__name__      # i canali sono link, non un bottone
        assert T.op_np5(on)[0] == "La tua pagina può ancora raccontare qualcosa di te"
        assert T.op_np5(off)[0] == "Dieci minuti per completare la tua pagina"
        for fn in (T.op_np5, T.op_np10, T.op_np15):
            o, c = fn(off)
            assert "Ciao," in c and "{" not in c
        # la pagina online fa UNA cosa: niente canali, niente consulenza
        _, c = T.op_profilo_online(on)
        assert "Telegram" not in c and "consulenza" not in c and "listino" in c
        from services.sequenze import PASSI
        assert [p.nome for p in PASSI["operatore"]][:2] == ["profilo_online", "canali"]
        canali = PASSI["operatore"][1]
        assert canali.dopo == "profilo_online" and canali.giorno == 1 and canali.fine == 21   # il giro dopo la pagina, mai prima, mai a chi e' online da mesi

    def test_promemoria_conferma_accesso(self):
        from services.cerchio_reminder import _testo_promemoria
        import services.cerchio_reminder as R
        orig = R._singolo_optin
        try:
            R._singolo_optin = lambda: True
            o, c = _testo_promemoria("Ciao,", "https://x", "")
            assert o == "Un tocco e si aprono le meditazioni" and "Apro le meditazioni" in c
            R._singolo_optin = lambda: False
            o, c = _testo_promemoria("Ciao,", "https://x", "")
            assert o == "Ti manca un clic per entrare nel Cerchio" and "non ti scriviamo più" in c
        finally:
            R._singolo_optin = orig                                   # mai sporcare i test dopo
        sub = (BACKEND / "routers" / "subscribers.py").read_text(encoding="utf-8")
        assert '"Un clic e sei nel Cerchio di Aurya"' in sub and "Riapro il mio accesso" in sub
        assert "Se non eri tu, ignora questa email: senza il clic non ti scriviamo." in sub

    def test_dizionario_segnaposto(self):
        from services.email_service import _t
        it = self._it()
        import re as _re
        # ogni segnaposto {x} del testo italiano deve essere accettato dai chiamanti: li proviamo tutti
        for k, v in it.items():
            segnaposto = set(_re.findall(r"\{(\w+)\}", v))
            _t(k, "it", **{s: "x" for s in segnaposto})          # ogni testo si formatta coi suoi segnaposto
        assert _t("order_cancelled_refund_paid", "en", store_name="X").startswith("Se hai già pagato")   # ripiego it
        assert it["review_otp_subject"] == "Il codice per la tua recensione a {operator}"
        assert it["order_confirmed_subject"] == "{store_name} ha confermato il tuo ordine"

    def test_richieste_e_stati(self):
        import services.strutture_email as S
        inviate = []
        class _E:
            @staticmethod
            def send_email(to, oggetto, html, **kw): inviate.append((to, oggetto, html))
            @staticmethod
            def _wrap_template(c, l, **kw): return c
        import sys, types
        import services.email_service as E
        orig = (E.send_email, E._wrap_template)
        E.send_email, E._wrap_template = _E.send_email, _E._wrap_template
        try:
            richieste = (
                {"email": "a@b.it", "tipo": "struttura", "zona": "Puglia", "periodo": "giugno", "persone": 12, "notti": 3, "budget_persona": 120.0, "nome": "Anna Bianchi"},
                {"email": "a@b.it", "tipo": "struttura"},
                {"email": "a@b.it", "tipo": "regia", "periodo": "giugno", "persone": 12, "formula": "leggera"},
                {"email": "a@b.it", "tipo": "team_building", "azienda": "Acme", "nome": "Luca", "periodo": "luglio", "persone": 20},
                {"email": "a@b.it", "tipo": "lettera_eventi"},
                {"email": "a@b.it", "tipo": "social"},
            )
            for r in richieste:
                S.ricevuta_operatore(r)
                for st in ("nuova", "in_lavorazione", "proposta", "chiusa"):
                    S.avvisa_operatore_stato({**r, "stato": st})
        finally:
            E.send_email, E._wrap_template = orig
        assert len(inviate) == len(richieste) * 5
        testi = "\n".join(o + "\n" + h for _, o, h in inviate)
        assert "i suoi eventi" not in testi and "i tuoi eventi nella Lettera" in testi
        assert "è abbiamo" not in testi and "è la proposta" not in testi
        assert "Ciao Anna," in testi and "Ciao Luca," in testi and "Ciao," in testi
        assert "a Puglia, giugno, per 12 persone, 3 notti, budget 120 € a persona" in testi
        assert "Abbiamo ricevuto la richiesta di Acme" in testi and "Vi scriviamo entro due giorni lavorativi" in testi
        oggetti = {o for _, o, _ in inviate}
        assert {"Ci stiamo lavorando alla tua richiesta", "Abbiamo una proposta per te", "La tua richiesta è chiusa"} <= oggetti
        assert all("Aggiornamento sulla tua richiesta" != o for o in oggetti)
        assert "Se non è quello che ti aspettavi, oppure vuoi riaprirla" in testi

    def test_invito_team_senza_password(self):
        src = (BACKEND / "services" / "email_service.py").read_text(encoding="utf-8")
        blocco = src[src.index("def send_team_invite("):src.index("def send_deactivation_notice(")]
        assert "temp_password" not in blocco.split('"""')[2]   # mai scritta nel corpo
        assert "reset-password?token=" in blocco
        org = (BACKEND / "routers" / "organizations.py").read_text(encoding="utf-8")
        assert "reset_token=_tok" in org and '"reset_token_hash": _hl.sha256(_tok.encode()).hexdigest()' in org
        assert "send_team_invite(invite_data.email, org_name, inviter_name, temp_password" not in org

    def test_recensioni(self):
        src = (BACKEND / "services" / "review_service.py").read_text(encoding="utf-8")
        assert "_send_review_otp_email(email_n, code, _nome_org(org), locale, riga_cerchio)" in src
        assert "Ci serve l’email con cui hai prenotato" in src and "con questa persona" in src
        assert '"Hai ricevuto una nuova recensione"' in src and '"Hai una recensione da leggere"' in src
        assert "non va contro le regole delle recensioni" in src
        assert "<p>Ciao,</p>\n        <p>grazie: la tua recensione" in src

    def test_ordini_ed_eventi(self):
        oe = (BACKEND / "services" / "order_email_service.py").read_text(encoding="utf-8")
        assert '_t("order_received_body", locale, store_name=store_name)' in oe
        assert '_t("order_confirmed_body", locale, store_name=store_name)' in oe
        assert '"order_cancelled_refund_paid" if pagato else "order_cancelled_refund_none"' in oe
        ev = (BACKEND / "services" / "event_email_service.py").read_text(encoding="utf-8")
        assert ev.count('if holder_display else') == 2                     # «Ciao,» senza nome
        pay = (BACKEND / "services" / "payment_email_service.py").read_text(encoding="utf-8")
        assert '_t("pay_atrisk_merchant_cta", locale)' in pay and "/incassi" in pay
