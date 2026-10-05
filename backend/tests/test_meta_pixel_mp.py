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


class TestMP3Capi:
    """MP3 — la Conversions API lato server: stesso event_id del pixel, email
    solo hashata, parte SOLO col consenso marketing, mai bloccante, token mai
    in URL o log, registro per la regia."""

    @pytest.fixture
    def configurato(self, monkeypatch):
        monkeypatch.setenv("META_PIXEL_ID", "1093685309713150")
        monkeypatch.setenv("META_CAPI_TOKEN", "TOKEN-DI-PROVA-mai-nei-log")
        monkeypatch.delenv("META_TEST_EVENT_CODE", raising=False)
        from services import meta_capi
        return meta_capi

    def test_evento_senza_pii_in_chiaro(self, configurato):
        mc = configurato
        ev = mc.costruisci_evento("Lead", "lead_0123456789abcdef01234567", email="  Mario.Rossi@Example.com ",
                                  fbp="fb.1.1700000000000.123456789", ip="127.0.0.1", user_agent="UA/1",
                                  url="https://aurya.life/cerca-ritiro?utm_source=facebook",
                                  custom_data={"content_name": "landing", "vuoto": None, "content_category": "cerchio"})
        dump = json.dumps(ev)
        assert "mario" not in dump.lower() and "example.com" not in dump
        assert ev["user_data"]["em"] == [mc.hash_email("mario.rossi@example.com")]
        assert "client_ip_address" not in ev["user_data"]          # localhost non si manda
        assert ev["user_data"]["fbp"] == "fb.1.1700000000000.123456789"
        assert ev["action_source"] == "website" and ev["event_id"] == "lead_0123456789abcdef01234567"
        assert ev["custom_data"] == {"content_name": "landing", "content_category": "cerchio"}
        assert mc.id_derivato("conf", "A@b.it") == mc.id_derivato("conf", "a@b.it") and "a@b" not in mc.id_derivato("conf", "a@b.it")

    def test_parte_solo_col_consenso_e_configurato(self, configurato, monkeypatch):
        import asyncio
        mc = configurato
        accodati = []

        async def finto(evento, contesto):
            accodati.append((evento, contesto))
        monkeypatch.setattr(mc, "_invia_e_registra", finto)
        pieno = {"url": "https://aurya.life/x", "porta": "landing",
                 "tracciamento": {"marketing": True, "event_id": "lead_0123456789abcdef", "fbp": "fb.1.1.2"}}

        async def scena():
            assert mc.evento_da_provenienza("Lead", {"tracciamento": {"marketing": False}}, email="a@b.it") is False
            assert mc.evento_da_provenienza("Lead", {"tracciamento": {"marketing": True}}, email="a@b.it") is False
            assert mc.evento_da_provenienza("Lead", {"tracciamento": {"marketing": True, "event_id": "x"}}) is False
            assert mc.evento_da_provenienza("Lead", None, email="a@b.it") is False
            assert mc.evento_da_provenienza("Lead", pieno, email="a@b.it", contesto="prova") is True
            await asyncio.sleep(0)
        asyncio.run(scena())
        assert len(accodati) == 1
        ev, ctx = accodati[0]
        assert ev["event_id"] == "lead_0123456789abcdef" and ev["event_source_url"] == "https://aurya.life/x" and ctx == "prova"
        # senza loop (chiamata sincrona) non esplode: False e basta
        assert mc.evento_da_provenienza("Lead", pieno, email="a@b.it") is False
        # senza configurazione: tutto spento
        monkeypatch.delenv("META_CAPI_TOKEN")
        assert mc.configurato() is False
        assert asyncio.run(mc.invia_eventi([{"event_name": "Lead"}]))["errore"] == "non configurato"
        assert mc.evento_da_provenienza("Lead", pieno, email="a@b.it") is False

    def test_invio_token_nel_corpo_e_tentativi(self, configurato, monkeypatch):
        import asyncio
        import httpx
        mc = configurato
        monkeypatch.setenv("META_TEST_EVENT_CODE", "TEST123")
        chiamate = []
        risposte = [500, 200]

        class Risposta:
            def __init__(self, code):
                self.status_code = code
                self.text = "{}"

            def json(self):
                return {"events_received": 1} if self.status_code == 200 else {"error": {"code": 190, "message": "boh"}}

        class FintoClient:
            def __init__(self, **kw):
                chiamate.append(("timeout", kw.get("timeout")))

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, url, json=None, **kw):
                chiamate.append((url, json, kw))
                return Risposta(risposte.pop(0))

        monkeypatch.setattr(httpx, "AsyncClient", FintoClient)

        async def niente(_):
            return None
        monkeypatch.setattr(mc.asyncio, "sleep", niente)
        ev = mc.costruisci_evento("Lead", "lead_0123456789abcdef", email="a@b.it")
        esito = asyncio.run(mc.invia_eventi([ev], codice_test=mc.test_event_code()))
        assert esito == {"ok": True, "accettati": 1, "tentativi": 2, "errore": None}
        post = [c for c in chiamate if isinstance(c[1], dict)]
        assert len(post) == 2
        url, corpo, kw = post[0]
        assert url == "https://graph.facebook.com/v21.0/1093685309713150/events"
        assert "TOKEN" not in url and "params" not in kw            # il token mai in URL
        assert corpo["access_token"] == "TOKEN-DI-PROVA-mai-nei-log" and corpo["test_event_code"] == "TEST123"
        assert corpo["data"][0]["event_id"] == "lead_0123456789abcdef"
        assert chiamate[0] == ("timeout", 5.0)
        # un 4xx (non 429) e' definitivo: UN tentativo, errore corto senza segreti
        risposte[:] = [400]
        esito = asyncio.run(mc.invia_eventi([ev]))
        assert esito["ok"] is False and esito["tentativi"] == 1 and esito["errore"] == "http 400: 190 boh"
        # 3 errori di rete: 3 tentativi
        class Rete(FintoClient):
            async def post(self, url, json=None, **kw):
                raise httpx.ConnectError("giu'")
        monkeypatch.setattr(httpx, "AsyncClient", Rete)
        esito = asyncio.run(mc.invia_eventi([ev]))
        assert esito == {"ok": False, "accettati": 0, "tentativi": 3, "errore": "ConnectError"}

    def test_mai_segreti_nei_log(self):
        src = (BACKEND / "services" / "meta_capi.py").read_text(encoding="utf-8")
        assert src.count("_token()") == 3                          # definizione, configurato() e il corpo della POST
        assert '"access_token": _token()' in src and "params=" not in src
        for riga in src.splitlines():
            if "logger." in riga:
                assert "token" not in riga.lower() and "email" not in riga.lower(), riga

    def test_agganci_nel_codice(self):
        sub = (BACKEND / "routers" / "subscribers.py").read_text(encoding="utf-8")
        assert '"Lead", doc_set.get("provenienza"), email=email, request=request,' in sub
        ver = (BACKEND / "services" / "verifica_email.py").read_text(encoding="utf-8")
        assert '"LeadConfermato", sub.get("provenienza"), email=email,' in ver and 'event_id=id_derivato("conf", email)' in ver
        assert '"provenienza": 1})' in ver
        auth = (BACKEND / "services" / "auth_service.py").read_text(encoding="utf-8")
        assert '"CompleteRegistration", org_doc.get("provenienza"), email=user_data.email,' in auth
        acc = (BACKEND / "services" / "platform_account_service.py").read_text(encoding="utf-8")
        assert '"CompleteRegistration", doc.get("provenienza"), email=email_n,' in acc
        pub = (BACKEND / "routers" / "public.py").read_text(encoding="utf-8")
        assert 'out["registrato"] = bool(nuovo)' in pub and "_contact_a_meta(request, org, identita)" in pub
        assert 'return bool(getattr(esito, "upserted_id", None))' in pub
        pay = (BACKEND / "services" / "payment_checkout_service.py").read_text(encoding="utf-8")
        assert '"Purchase", confirmed.get("provenienza"), event_id=f"acq_{order_id}",' in pay
        rev = (BACKEND / "routers" / "reviews.py").read_text(encoding="utf-8")
        assert "tracciamento=body.tracciamento if isinstance(body.tracciamento, dict) else None," in rev
        # ogni aggancio e' dentro un try/except: mai bloccante
        for testo, nome in ((sub, "subscribers"), (ver, "verifica"), (auth, "auth"), (acc, "account"), (pay, "checkout")):
            i = testo.index("from services.meta_capi import evento_da_provenienza")
            assert "try:" in testo[i - 120:i], nome

    def test_modello_recensione_accetta_il_tracciamento(self):
        from routers.reviews import ReviewSubmit
        base = {"org_slug": "demo-org", "email": "a@b.it", "code": "123456", "rating": 5,
                "body": "bello", "author_name": "A"}
        assert ReviewSubmit(**base).tracciamento is None                                   # payload di ieri
        r = ReviewSubmit(**base, cerchio=True, tracciamento={"marketing": True, "event_id": "lead_0123456789abcdef"})
        assert r.tracciamento["event_id"] == "lead_0123456789abcdef"


class TestMP4Regia:
    """MP4 — la regia legge le campagne: filtri campagna › inserzione negli
    Iscritti (lista + CSV), ripartizione «Per campagna» coi confermati,
    provenienza in riga negli Operatori, campagne 30 giorni e stato Meta
    nei numeri del lunedi'."""

    def test_ripartizione_campagne_dal_vivo(self):
        import asyncio
        from datetime import datetime, timezone
        from services.provenienza import ripartizione_campagne
        tag = "mp4-prova-campagna"
        docs = [
            {"email": f"{tag}-{i}@example.com", "status": st, "created_at": datetime.now(timezone.utc),
             "provenienza": {"utm": {"source": "facebook", "campaign": tag, "content": ins}}}
            for i, (st, ins) in enumerate([("confirmed", "video-1"), ("pending", "video-1"), ("confirmed", "foto-2")])
        ]

        async def scena():
            # un client Mongo tutto suo: il client condiviso di database.py resta
            # legato al loop del primo test che l'ha usato (nella suite intera)
            import database as _d
            from motor.motor_asyncio import AsyncIOMotorClient
            cli = AsyncIOMotorClient(_d.mongo_url, serverSelectionTimeoutMS=5000)
            coll = cli[os.environ["DB_NAME"]].aurya_subscribers
            await coll.delete_many({"email": {"$regex": f"^{tag}-"}})
            await coll.insert_many(docs)
            try:
                tutte = await ripartizione_campagne(coll, limite=50)
                senza_conferma = await ripartizione_campagne(coll, limite=50, conferma=None)
                vecchie = await ripartizione_campagne(coll, da=datetime(2999, 1, 1, tzinfo=timezone.utc))
            finally:
                await coll.delete_many({"email": {"$regex": f"^{tag}-"}})
                cli.close()
            return tutte, senza_conferma, vecchie
        tutte, senza_conferma, vecchie = asyncio.run(scena())
        voce = next(v for v in tutte if v["campagna"] == tag)
        assert voce["n"] == 3 and voce["confermati"] == 2
        assert voce["inserzioni"] == [{"inserzione": "video-1", "n": 2, "confermati": 1},
                                      {"inserzione": "foto-2", "n": 1, "confermati": 1}]
        assert next(v for v in senza_conferma if v["campagna"] == tag)["confermati"] == 0
        assert not any(v["campagna"] == tag for v in vecchie)

    def test_provenienza_breve(self):
        from services.provenienza import provenienza_breve
        assert provenienza_breve(None) is None and provenienza_breve({}) is None
        p = provenienza_breve({"canale": "social", "superficie": "facebook", "url": "https://aurya.life/x",
                               "utm": {"source": "facebook", "campaign": "pro-ott", "content": "ad-1"},
                               "referrer": "https://l.facebook.com/", "dispositivo": "mobile",
                               "tracciamento": {"marketing": True, "event_id": "reg_0123456789abcdef"}})
        assert p == {"canale": "social", "superficie": "facebook", "porta": None, "utm_source": "facebook",
                     "campagna": "pro-ott", "inserzione": "ad-1", "referrer": "https://l.facebook.com/",
                     "dispositivo": "mobile", "marketing": True}
        assert "event_id" not in json.dumps(p)                       # in riga mai gli identificativi

    def test_filtri_e_ripartizioni_nel_codice(self):
        sub = (BACKEND / "routers" / "subscribers.py").read_text(encoding="utf-8")
        assert sub.count("campagna=campagna, inserzione=inserzione") == 2          # lista + CSV
        assert 'query["provenienza.utm.campaign"] = campagna.strip()[:80]' in sub
        assert 'query["provenienza.utm.content"] = inserzione.strip()[:80]' in sub
        assert '"by_campagna": by_campagna' in sub
        lun = (BACKEND / "routers" / "admin_platform.py").read_text(encoding="utf-8")
        assert '"campagne_30g": campagne, "meta": meta' in lun and "meta_riepilogo(24)" in lun
        adm = (BACKEND / "routers" / "admin.py").read_text(encoding="utf-8")
        assert 'provenienza=_provenienza_breve_sicura(doc.get("provenienza"))' in adm
        assert '"provenienza": 1' in (BACKEND / "repositories" / "admin_repository.py").read_text(encoding="utf-8")
        assert "provenienza: Optional[dict] = None" in (BACKEND / "models" / "admin.py").read_text(encoding="utf-8")
        isc = (FE / "features" / "admin" / "IscrittiTab.js").read_text(encoding="utf-8")
        for k in ("campagna: '', inserzione: ''", 'testid="iscritti-rip-campagna"', 'data-testid="iscritti-f-campagna"',
                  'data-testid="iscritti-f-inserzione"', "{ ...prev, campagna: v, inserzione: '' }", "k: 'campagna'",
                  "['source', 'medium', 'campaign', 'content', 'term']", 'k="Pixel Meta"'):
            assert k in isc, k
        org = (FE / "features" / "admin" / "OrganizationsTab.js").read_text(encoding="utf-8")
        assert 'data-testid="org-provenienza"' in org
        ov = (FE / "features" / "admin" / "PlatformOverviewTab.js").read_text(encoding="utf-8")
        assert 'data-testid="numeri-lunedi-campagne"' in ov and 'data-testid="numeri-lunedi-meta"' in ov

    def test_riepilogo_meta_forma(self):
        import asyncio
        from services.meta_capi import riepilogo
        r = asyncio.run(riepilogo(24))
        assert set(r) == {"configurato", "test", "ore", "totale", "accettati", "falliti", "per_nome"}
        assert r["ore"] == 24 and isinstance(r["per_nome"], dict)


class TestMPCoperturaPorte:
    """5/10 sera (founder: «il form di entra-nella-rete e' monitorato? la
    registrazione? l'iscrizione?») — OGNI porta che conta parla con Meta,
    browser e server, con lo stesso event_id. Qui si pinnano le porte che il
    primo giro non copriva: account da /accedi, richieste di contatto
    /public/leads (ramo operatore del LeadForm e le due landing Sound)."""

    def test_tutte_le_porte_nel_codice(self):
        acc = (FE / "features" / "account" / "AccountLoginPage.js").read_text(encoding="utf-8")
        assert "provenienza: { ...provenienzaCorrente(), tracciamento }," in acc
        assert "metaCompleteRegistration({ eventID: tracciamento.event_id, tipo: 'account' });" in acc
        assert "await operatorSignup(" in acc                      # il professionista passa da AuthContext.signup (gia' agganciato)
        inline = (FE / "features" / "prelaunch" / "InlineSignupForm.js").read_text(encoding="utf-8")
        assert "const { signup } = useAuth();" in inline            # /entra-nella-rete#presentati → AuthContext.signup
        lead = (FE / "features" / "prelaunch" / "LeadForm.jsx").read_text(encoding="utf-8")
        assert "provenienza: provenienzaCorrente(), tracciamento: tracciamentoLead," in lead
        assert "metaLead({ eventID: tracciamentoLead.event_id, superficie: `lead_${type}` });" in lead
        for nome, interesse in (("ProfessionalLanding.jsx", "sound_professional"), ("CreaStudioLanding.jsx", "sound_crea")):
            src = (FE / "features" / "frequenze" / nome).read_text(encoding="utf-8")
            assert "provenienza: provenienzaCorrente(), tracciamento," in src, nome
            assert f"metaLead({{ eventID: tracciamento.event_id, superficie: '{interesse}' }});" in src, nome
        # nessun altro POST a /public/leads senza tracciamento
        for p in FE.rglob("*.js*"):
            t = p.read_text(encoding="utf-8", errors="ignore")
            if "'/public/leads'" in t:
                assert "tracciamento" in t, p
        leads = (BACKEND / "routers" / "leads.py").read_text(encoding="utf-8")
        assert "tracciamento: Optional[dict] = None" in leads and 'f"lead_{lead_type}", raw,' in leads
        assert '"Lead", doc_set.get("provenienza"), email=email, request=request,' in leads

    def test_modello_lead_e_dal_vivo(self):
        import os as _os
        import requests
        from routers.leads import LeadPayload
        base = {"email": "a@b.it", "type": "operator", "consent": True}
        assert LeadPayload(**base).tracciamento is None and LeadPayload(**base).provenienza is None   # payload di ieri
        api = (_os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8000") + "/api"
        try:
            requests.get(api + "/health", timeout=2)
        except Exception:
            pytest.skip("backend locale spento")
        email = "mp-copertura-lead@example.com"
        r = requests.post(api + "/public/leads", json={
            **base, "email": email, "name": "Prova MP", "message": "verifica guardia",
            "provenienza": {"url": "https://aurya.life/sound/professional?utm_source=facebook&utm_campaign=prova-mp",
                            "utm": {"source": "facebook", "campaign": "prova-mp", "content": "ad-1"}},
            "tracciamento": {"marketing": False, "event_id": "lead_0123456789abcdef"},
        }, timeout=10)
        if r.status_code == 429:
            pytest.skip("rate limit")
        assert r.status_code == 201 and r.json() == {"ok": True}
        import asyncio
        async def leggi_e_pulisci():
            import database as _d
            from motor.motor_asyncio import AsyncIOMotorClient
            cli = AsyncIOMotorClient(_d.mongo_url, serverSelectionTimeoutMS=5000)
            coll = cli[_os.environ["DB_NAME"]].prelaunch_leads
            try:
                doc = await coll.find_one({"email": email}, {"_id": 0, "provenienza": 1})
                await coll.delete_many({"email": email})
            finally:
                cli.close()
            return doc
        doc = asyncio.run(leggi_e_pulisci())
        prov = (doc or {}).get("provenienza") or {}
        assert prov.get("utm", {}).get("campaign") == "prova-mp" and prov.get("utm", {}).get("content") == "ad-1"
        assert prov.get("porta") == "facebook" and prov.get("canale")      # classificata come il Cerchio
        assert prov.get("tracciamento") == {"marketing": False}      # senza consenso: niente identificativi

    def test_csp_lascia_passare_il_pixel(self):
        """5/10 sera, trovato in prod al primo giro: la CSP bloccava fbevents.js
        (stato 0, nessun cookie, nessun evento dal browser). Ogni riga CSP di
        nginx deve ammettere connect.facebook.net negli script e www.facebook.com
        nelle connessioni; e niente unsafe-inline (resta l'invariante SEC-1)."""
        import re as _re
        conf = (RADICE / "deploy" / "nginx" / "nginx.conf").read_text(encoding="utf-8")
        righe = _re.findall(r'add_header Content-Security-Policy "([^"]+)"', conf)
        assert len(righe) >= 2
        for csp in righe:
            script = _re.search(r"script-src\s+([^;]+);", csp).group(1)
            connect = _re.search(r"connect-src\s+([^;]+);", csp).group(1)
            assert "https://connect.facebook.net" in script and "'unsafe-inline'" not in script, script
            assert "https://www.facebook.com" in connect and "https://connect.facebook.net" in connect, connect
            # il POST di ripiego del pixel (iframe + form verso www.facebook.com/tr)
            assert _re.search(r"form-action 'self' https://www\.facebook\.com;", csp), csp
            assert _re.search(r"frame-src 'self' https://iframe\.mediadelivery\.net https://www\.facebook\.com;", csp), csp
