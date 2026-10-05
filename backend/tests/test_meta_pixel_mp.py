"""MP (5/10/2026) — Meta Pixel + Conversions API. Piano:
docs/PIANO_META_PIXEL_2026-10-05.md. Un file di guardia, una classe per lotto.

MP0 fondamenta: env e site-config, utm esteso (content/term), click_ids
(fbclid/gclid), blocco di tracciamento pulito (solo con consenso
marketing), provenienza alla registrazione del professionista e
dell'account cliente. Tutto facoltativo: un client vecchio non manda
nulla e il server risponde come prima.
"""
import json
import os
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[2]
BACKEND = RADICE / "backend"
FE = RADICE / "frontend" / "src"


class TestMP0Fondamenta:
    def test_env_e_site_config(self):
        compose = (RADICE / "docker-compose.prod.yml").read_text(encoding="utf-8")
        for k in ("META_PIXEL_ID=${META_PIXEL_ID:-}", "META_CAPI_TOKEN=${META_CAPI_TOKEN:-}",
                  "META_TEST_EVENT_CODE=${META_TEST_EVENT_CODE:-}"):
            assert k in compose, k
        pub = (BACKEND / "routers" / "public.py").read_text(encoding="utf-8")
        assert '"meta_pixel_id": (os.environ.get("META_PIXEL_ID") or "").strip() or None' in pub
        # il token NON esce mai dal site-config
        blocco = pub[pub.index("async def site_config("):pub.index("# ── Response / Request Models")]
        assert "META_CAPI_TOKEN" not in blocco

    def test_utm_esteso_e_click_ids(self):
        from services.provenienza import pulisci_click_ids, pulisci_utm
        assert pulisci_utm({"utm_source": "facebook", "utm_medium": "paid", "utm_campaign": "cerchio-ott",
                            "utm_content": "video-1", "utm_term": "x" * 100}) == \
            {"source": "facebook", "medium": "paid", "campaign": "cerchio-ott", "content": "video-1", "term": "x" * 80}
        assert pulisci_utm({"utm_source": "ig", "medium": "bio", "x": 1}) == {"source": "ig", "medium": "bio"}  # come prima
        assert pulisci_click_ids({"fbclid": "IwAR0abc-DEF_123", "gclid": "Cj0KCQ", "altro": "no"}) == \
            {"fbclid": "IwAR0abc-DEF_123", "gclid": "Cj0KCQ"}
        assert pulisci_click_ids({"fbclid": "<script>"}) is None and pulisci_click_ids("x") is None

    def test_tracciamento_solo_col_consenso(self):
        from services.provenienza import pulisci_tracciamento
        pieno = {"marketing": True, "event_id": "ev_0123456789abcdef", "fbp": "fb.1.1700000000000.123456789",
                 "fbc": "fb.1.1700000000000.IwAR0abc", "altro": "x"}
        assert pulisci_tracciamento(pieno) == {"marketing": True, "event_id": "ev_0123456789abcdef",
                                               "fbp": "fb.1.1700000000000.123456789", "fbc": "fb.1.1700000000000.IwAR0abc"}
        # senza consenso: resta SOLO il flag, nessun identificativo
        assert pulisci_tracciamento({**pieno, "marketing": False}) == {"marketing": False}
        assert pulisci_tracciamento({**pieno, "marketing": "si"}) == {"marketing": False}
        assert pulisci_tracciamento({"marketing": True, "event_id": "x", "fbp": "non-un-cookie"}) == {"marketing": True}
        assert pulisci_tracciamento(None) is None

    def test_provenienza_registrazione(self):
        from services.provenienza import provenienza_registrazione
        p = provenienza_registrazione("signup_pro", {
            "url": "https://aurya.life/accedi?vista=crea&utm_source=facebook&utm_campaign=pro",
            "referrer": "https://l.facebook.com/", "utm": {"source": "facebook", "campaign": "pro", "content": "ad-2"},
            "click_ids": {"fbclid": "IwAR0xyz"}, "tracciamento": {"marketing": True, "event_id": "ev_abcdefgh12345678"},
        }, "Mozilla/5.0 (iPhone)")
        assert p["canale"] == "account" and p["superficie"] == "signup-pro"
        assert p["utm"]["content"] == "ad-2" and p["click_ids"] == {"fbclid": "IwAR0xyz"}
        assert p["tracciamento"] == {"marketing": True, "event_id": "ev_abcdefgh12345678"}
        assert p["dispositivo"] == "mobile"
        # client vecchio: nessun blocco → solo la classificazione dalla fonte
        v = provenienza_registrazione("account_signup", None, None)
        assert v["canale"] == "account" and v["utm"] is None and "click_ids" not in v

    def test_modelli_e_agganci(self):
        from models.user import UserCreate
        from routers.platform_accounts import PasswordSignup
        from routers.subscribers import SubscribePayload
        for m in (UserCreate, PasswordSignup):
            assert not m.model_fields["provenienza"].is_required()
        for k in ("click_ids", "tracciamento"):
            assert not SubscribePayload.model_fields[k].is_required()
        auth = (BACKEND / "services" / "auth_service.py").read_text(encoding="utf-8")
        assert 'provenienza_registrazione(\n            "signup_pro", getattr(user_data, "provenienza", None), user_agent)' in auth
        pa = (BACKEND / "services" / "platform_account_service.py").read_text(encoding="utf-8")
        assert 'provenienza_registrazione("account_signup", provenienza, user_agent)' in pa
        route = (BACKEND / "routers" / "platform_accounts.py").read_text(encoding="utf-8")
        assert "provenienza=body.provenienza)" in route
        subs = (BACKEND / "routers" / "subscribers.py").read_text(encoding="utf-8")
        assert 'click = pulisci_click_ids(payload.click_ids)' in subs and 'tracc = pulisci_tracciamento(payload.tracciamento)' in subs

    def test_frontend_manda_la_provenienza(self):
        tc = (FE / "lib" / "testiConsenso.js").read_text(encoding="utf-8")
        for k in ("pulisci('utm_content')", "pulisci('utm_term')", "q.get('fbclid')", "q.get('gclid')", "click_ids: click"):
            assert k in tc, k
        auth = (FE / "context" / "AuthContext.js").read_text(encoding="utf-8")
        # (MP2 ha aggiunto il blocco di tracciamento accanto alla provenienza)
        assert "payload.provenienza = { ...provenienzaCorrente(), tracciamento };" in auth
        porta = (FE / "features" / "account" / "PortaAurya.jsx").read_text(encoding="utf-8")
        assert "provenienza: { ...provenienzaCorrente(), tracciamento }," in porta and "provenienzaCorrente } from '../../lib/testiConsenso'" in porta

    def test_dal_vivo_payload_vecchio_identico(self):
        """Il subscribe senza i campi nuovi risponde come prima."""
        import requests
        base = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
        try:
            if requests.get(f"{base}/api/health", timeout=5).status_code != 200:
                pytest.skip("backend locale spento")
        except Exception:
            pytest.skip("backend locale spento")
        r1 = requests.post(f"{base}/api/public/newsletter/subscribe", json={"email": "mp0-guardia@example.com", "consent": False}, timeout=10)
        r2 = requests.post(f"{base}/api/public/newsletter/subscribe",
                           json={"email": "mp0-guardia@example.com", "consent": False,
                                 "click_ids": {"fbclid": "x"}, "tracciamento": {"marketing": False}}, timeout=10)
        assert r1.status_code == r2.status_code and r1.status_code != 500


class TestMP1Consenso:
    """Banner a tre scelte, lib/consenso.js come verita', informativa v2.11."""

    def test_consenso_js(self):
        c = (FE / "lib" / "consenso.js").read_text(encoding="utf-8")
        for k in ("const CHIAVE = 'aurya_consent_v3';", "export function leggiConsenso()", "export function bannerDaMostrare()",
                  "export const consensoMarketing", "export function salvaConsenso(", "export function onCambio(",
                  "export function apriPreferenzeCookie()", "legacy: true"):
            assert k in c, k
        # nessun ciclo: consenso.js non importa GA ne' Meta
        assert "from './analytics'" not in c and "from './meta'" not in c

    def test_banner_tre_scelte_mai_consenso_implicito(self):
        b = (FE / "components" / "legal" / "CookieConsentBanner.js").read_text(encoding="utf-8")
        for t in ("cookie-solo-essenziali", "cookie-statistiche", "cookie-accetta-tutto"):
            assert f'data-testid="{t}"' in b, t
        assert "scegli(false, false)" in b and "scegli(true, false)" in b and "scegli(true, true)" in b
        assert "bannerDaMostrare()" in b and "salvaConsenso({ analytics, marketing })" in b
        assert "EVENTO_APRI" in b                                     # il pie' di pagina lo riapre
        # la X = solo essenziali: nessun «chiudi = accetto»
        assert b.count("scegli(false, false)") >= 2
        a = (FE / "lib" / "analytics.js").read_text(encoding="utf-8")
        assert "leggiConsenso() || readStoredConsent()" in a
        import json
        for lang in ("it", "en", "de", "fr"):
            cb = json.loads((FE / "locales" / lang / "legal.json").read_text(encoding="utf-8"))["cookie_banner"]
            for k in ("stats_button", "all_button", "preferences_link", "essential_button", "body"):
                assert cb.get(k), (lang, k)
            assert "Meta" in cb["body"]
            assert "mai" not in cb["body"].lower().split("pubblicitari")[-1][:12] if lang == "it" else True
        it = json.loads((FE / "locales" / "it" / "legal.json").read_text(encoding="utf-8"))["cookie_banner"]
        assert "Nessun cookie pubblicitario, mai" not in it["body"]

    def test_informativa_v211(self):
        from core.legal_versions import CURRENT_VERSION_TAG
        assert CURRENT_VERSION_TAG == "v2.11"
        for lang, (meta, cat) in {"it": ("Meta Pixel e Meta Conversions API", "Marketing"),
                                  "en": ("Meta Pixel and Meta Conversions API", "Marketing"),
                                  "de": ("Meta Pixel und Meta Conversions API", "Marketing"),
                                  "fr": ("Meta Pixel et Meta Conversions API", "Marketing")}.items():
            p = (BACKEND / "legal" / f"privacy_{lang}.md").read_text(encoding="utf-8")
            assert meta in p and "Facebook Pixel" not in p, lang          # via la vecchia smentita
            assert "_fbp" in p and "SHA-256" in p, lang
            assert "| **Meta Platforms Ireland Limited** |" in p, lang
        modal = json.loads((FE / "locales" / "it" / "legal.json").read_text(encoding="utf-8"))["reconsent"]["what_changed_body"]
        assert modal.startswith("Versione 2.11")


class TestMP2Pixel:
    """MP2 — il pixel nel browser: fbevents SOLO col consenso marketing, ogni
    evento che conta porta lo stesso event_id del payload al server."""

    def test_meta_js_consenso_prima_di_tutto(self):
        src = (FE / "lib" / "meta.js").read_text(encoding="utf-8")
        # lo script di Meta vive in UNA funzione, chiamata solo da applicaConsenso(true)
        assert src.count("connect.facebook.net/en_US/fbevents.js") == 1
        assert src.count("inietta();") == 1 and "if (marketing) {\n    attivo = true;\n    inietta();" in src
        assert "fbq('consent', 'revoke');" in src and "cancellaCookieMeta();" in src
        # senza consenso il blocco di tracciamento NON porta identificativi
        assert "if (!consensoMarketing()) return { marketing: false };" in src
        # ogni evento e' no-op senza pixel/consenso
        assert "if (!metaAttivo()) return false;" in src
        for ev in ("'Lead'", "'CompleteRegistration'", "'Contact'", "'Purchase'"):
            assert ev in src, ev
        # il pixel parte dal site-config (ID runtime), non dal bundle
        ctx = (FE / "context" / "SiteConfigContext.js").read_text(encoding="utf-8")
        assert "initMeta(res.data?.meta_pixel_id);" in ctx
        # nessun altro file carica fbevents o chiama fbq a mano
        for p in FE.rglob("*.js*"):
            if p.name == "meta.js":
                continue
            t = p.read_text(encoding="utf-8", errors="ignore")
            assert "fbevents.js" not in t and "window.fbq" not in t, p

    def test_stesso_event_id_payload_e_pixel(self):
        lead = (FE / "features" / "prelaunch" / "LeadForm.jsx").read_text(encoding="utf-8")
        assert "const tracciamento = datiTracciamento('lead');" in lead
        assert "tracciamento,\n" in lead and "metaLead({ eventID: tracciamento.event_id" in lead
        cer = (FE / "lib" / "cerchio.js").read_text(encoding="utf-8")
        assert "source, tracciamento," in cer and "metaLead({ eventID: tracciamento.event_id" in cer
        rec = (FE / "features" / "storefront" / "OperatorProfilePage.js").read_text(encoding="utf-8")
        assert "const tracciamento = cerchio ? datiTracciamento('lead') : null;" in rec
        assert "if (r?.data?.cerchio === 'iscritto' && tracciamento) metaLead(" in rec
        auth = (FE / "context" / "AuthContext.js").read_text(encoding="utf-8")
        assert "payload.provenienza = { ...provenienzaCorrente(), tracciamento };" in auth
        assert "metaCompleteRegistration({ eventID: tracciamento?.event_id, tipo: 'operatore' })" in auth
        porta = (FE / "features" / "account" / "PortaAurya.jsx").read_text(encoding="utf-8")
        assert "provenienza: { ...provenienzaCorrente(), tracciamento }," in porta
        assert "metaCompleteRegistration({ eventID: tracciamento.event_id, tipo: 'account' });" in porta
        con = (FE / "features" / "storefront" / "components" / "ContattiOperatore.jsx").read_text(encoding="utf-8")
        # i parametri ev/fbp/fbc partono SOLO col consenso, e il Contact solo se registrato
        assert "const params = tr.marketing ? { ev: tr.event_id" in con
        assert "if (r.data?.registrato) metaContact({ eventID: tr.event_id, slug });" in con
        chk = (FE / "features" / "storefront" / "CheckoutResultPage.js").read_text(encoding="utf-8")
        assert "metaPurchase({ eventID: `acq_${orderId}`" in chk and "purchaseInviato.current = true;" in chk
        app = (FE / "App.js").read_text(encoding="utf-8")
        assert "metaPageView();" in app

    def test_evento_pixel_nel_browser(self):
        """Il modulo gira davvero: senza consenso niente script e niente fbq;
        col consenso parte init + Lead con l'eventID dato."""
        import shutil
        import subprocess
        import tempfile
        node = shutil.which("node")
        if not node:
            pytest.skip("node assente")
        fe = RADICE / "frontend"
        prova = tempfile.NamedTemporaryFile("w", suffix=".js", dir=str(fe), delete=False)
        prova.write(r"""
const babel = require('@babel/core');
const fs = require('fs'); const path = require('path'); const Module = require('module');
process.env.NODE_ENV = 'development';
const cache = {};   // UN'istanza per modulo: meta e consenso devono condividere gli ascoltatori
function carica(rel) {
  const file = path.join(__dirname, 'src', rel);
  if (cache[file]) return cache[file].exports;
  const out = babel.transformFileSync(file, {presets: ['babel-preset-react-app'], babelrc: false, configFile: false}).code;
  const m = new Module(file, module); m.filename = file; m.paths = Module._nodeModulePaths(path.dirname(file)); cache[file] = m;
  m.require = (p) => p.startsWith('.') ? carica(path.relative(path.join(__dirname,'src'), path.resolve(path.dirname(file), p)) + '.js') : require(p);
  m._compile(out, file); return m.exports;
}
const script = []; const chiamate = [];
global.window = global; global.localStorage = { _d:{}, getItem(k){return this._d[k]??null}, setItem(k,v){this._d[k]=String(v)}, removeItem(k){delete this._d[k]} };
global.document = { cookie: '', createElement: () => ({ set src(v){ script.push(v); } }), getElementsByTagName: () => [], head: { appendChild(){} } };
global.location = { hostname: 'aurya.life' }; global.crypto = require('crypto').webcrypto;
global.addEventListener = () => {}; global.dispatchEvent = () => {};
const meta = carica('lib/meta.js'); const cons = carica('lib/consenso.js');
// 1) senza consenso: niente script, Lead no-op, tracciamento senza id
meta.initMeta('123');
console.assert(script.length === 0, 'script senza consenso');
console.assert(meta.metaLead({eventID:'x'}) === false, 'lead senza consenso');
console.assert(JSON.stringify(meta.datiTracciamento('lead')) === '{"marketing":false}', 'tracciamento senza consenso');
// 2) consenso marketing: script iniettato UNA volta, init col pixel, Lead con eventID
cons.salvaConsenso({ analytics: true, marketing: true });
console.assert(script.length === 1 && script[0].includes('fbevents.js'), 'script col consenso');
const vera = global.fbq; global.fbq = (...a) => { chiamate.push(a); vera(...a); };
const tr = meta.datiTracciamento('lead');
console.assert(tr.marketing === true && /^lead_[0-9a-f]{24}$/.test(tr.event_id), 'event_id: ' + tr.event_id);
console.assert(meta.metaLead({eventID: tr.event_id, superficie: 'landing'}) === true, 'lead col consenso');
const lead = chiamate.find(a => a[0]==='track' && a[1]==='Lead');
console.assert(lead && lead[3].eventID === tr.event_id, 'stesso eventID');
console.assert(global.fbq.queue === undefined || true);
// 3) revoca: niente piu' eventi
cons.salvaConsenso({ analytics: true, marketing: false });
console.assert(meta.metaLead({eventID:'y'}) === false, 'lead dopo revoca');
console.assert(JSON.stringify(meta.datiTracciamento()) === '{"marketing":false}', 'tracciamento dopo revoca');
console.log('OK');
""")
        prova.close()
        try:
            r = subprocess.run([node, prova.name], cwd=str(fe), capture_output=True, text=True, timeout=120)
        finally:
            os.unlink(prova.name)
        assert r.returncode == 0 and "OK" in r.stdout and "Assertion failed" not in r.stderr, r.stdout + r.stderr
