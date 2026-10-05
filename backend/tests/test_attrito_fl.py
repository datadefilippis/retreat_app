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
