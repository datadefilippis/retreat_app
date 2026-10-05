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
