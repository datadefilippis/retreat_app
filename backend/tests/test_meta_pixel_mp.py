"""MP (5/10/2026) — Meta Pixel + Conversions API. Piano:
docs/PIANO_META_PIXEL_2026-10-05.md. Un file di guardia, una classe per lotto.

MP0 fondamenta: env e site-config, utm esteso (content/term), click_ids
(fbclid/gclid), blocco di tracciamento pulito (solo con consenso
marketing), provenienza alla registrazione del professionista e
dell'account cliente. Tutto facoltativo: un client vecchio non manda
nulla e il server risponde come prima.
"""
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
