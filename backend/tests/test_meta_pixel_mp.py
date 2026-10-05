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
        assert "payload.provenienza = provenienzaCorrente();" in auth
        porta = (FE / "features" / "account" / "PortaAurya.jsx").read_text(encoding="utf-8")
        assert "provenienza: provenienzaCorrente()," in porta and "provenienzaCorrente } from '../../lib/testiConsenso'" in porta

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
