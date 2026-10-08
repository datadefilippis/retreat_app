"""SN4 (8/10/2026, piano Aurya Sound §5.2 e §7) — LA CASSA PRONTA.

L'ossatura del Più (abbonamento ascoltatore, 39 €/anno, solo annuale)
scritta e provata ma SPENTA: SOUND_PIU_ATTIVO chiude checkout e portale;
la riga «Percorsi» nella casa (corsi con lezioni Suono, una sola cassa);
il badge «Presto nel Più»; la sezione nell'account e lo stato in regia.
Nessun paywall: il cancello del Più lo decide l'accensione.
"""
import os
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")


class TestOssatura:
    def test_flag_si_legge_a_ogni_chiamata(self, monkeypatch):
        from services import sound_piu
        monkeypatch.delenv("SOUND_PIU_ATTIVO", raising=False)
        assert sound_piu.attivo() is False
        monkeypatch.setenv("SOUND_PIU_ATTIVO", "1")
        assert sound_piu.attivo() is True
        assert sound_piu.PREZZO_EUR_ANNO == 39            # decisione 5: 39 €/anno, solo annuale

    def test_stato_account(self, monkeypatch):
        from services import sound_piu
        monkeypatch.delenv("SOUND_PIU_ATTIVO", raising=False)
        vuoto = sound_piu.stato_account({"id": "a"})
        assert vuoto == {"attivo": False, "prezzo_eur_anno": 39, "abbonato": False, "status": None,
                         "current_period_end": None, "cancel_at_period_end": False, "omaggio_until": None,
                         "ha_cliente_stripe": False}
        assert sound_piu.stato_account({"piu": {"status": "active"}})["abbonato"]
        assert sound_piu.stato_account({"piu": {"status": "past_due"}})["abbonato"]     # Stripe ritenta
        assert not sound_piu.stato_account({"piu": {"status": "canceled"}})["abbonato"]
        assert sound_piu.stato_account({"piu": {"omaggio_until": "2999-01-01T00:00:00+00:00"}})["abbonato"]
        assert not sound_piu.stato_account({"piu": {"omaggio_until": "2000-01-01T00:00:00+00:00"}})["abbonato"]

    def test_piu_da_subscription(self):
        from services.sound_piu import piu_da_subscription
        c = piu_da_subscription({"id": "sub_1", "status": "active", "cancel_at_period_end": True,
                                 "items": {"data": [{"current_period_end": 1800000000}]}})
        assert c["stripe_subscription_id"] == "sub_1" and c["status"] == "active" and c["cancel_at_period_end"]
        assert c["current_period_end"].year == 2027

    def test_servizio_e_router(self):
        src = (BACKEND / "services" / "sound_piu.py").read_text()
        # sul conto di Aurya (Customer dell'account), abbonamento, prezzo da ambiente, metadata per ritrovare l'account
        assert 'mode="subscription", customer=cus' in src and 'line_items=[{"price": price_id(), "quantity": 1}]' in src
        assert '"platform_account_id": account["id"], "aurya_piu": "1"' in src
        # webhook: segreto proprio con ripiego, lucchetto per evento (idempotente), mai l'org
        assert 'os.getenv("STRIPE_PIU_WEBHOOK_SECRET"), os.getenv("STRIPE_WEBHOOK_SECRET")' in src
        assert "billing_repository.try_acquire_event_lock(eid, etype)" in src
        assert "organization" not in src.lower().replace("organizations_collection", "")
        r = (BACKEND / "routers" / "sound_piu.py").read_text()
        for porta in ('@router.get("/platform/me/piu")', '@router.post("/platform/me/piu/checkout")',
                      '@router.post("/platform/me/piu/portale")', '@router.post("/public/sound/piu/webhook")'):
            assert porta in r, porta
        # checkout e portale chiusi finche' spento; lo stato risponde sempre
        assert r.count("    _spento_404()\n") == 2   # (la def non conta)
        assert "sound_piu_router.router" in (BACKEND / "server.py").read_text()
        # la regia vede il Più nella scheda dell'utente
        assert '"piu": 1, "stripe_customer_id": 1' in (BACKEND / "routers" / "admin_platform.py").read_text()

    def test_dal_vivo_spento(self):
        import requests
        try:
            r = requests.post(f"{BASE_URL}/api/public/sound/piu/webhook", data=b"{}", timeout=10)
        except requests.RequestException:
            pytest.skip("server locale non raggiungibile")
        assert r.status_code == 400          # senza firma: mai accettato
        r = requests.post(f"{BASE_URL}/api/public/sound/piu/webhook", data=b"{}",
                          headers={"stripe-signature": "t=1,v1=finta"}, timeout=10)
        assert r.status_code == 400
        # la pagina del Più: noindex finche' spento
        r = requests.get(f"{BASE_URL}/__seo/meditazioni/piu", timeout=10)
        assert r.status_code == 200 and 'name="robots" content="noindex"' in r.text


class TestPercorsiEBadge:
    def test_directory_filtra_i_percorsi(self):
        src = (BACKEND / "routers" / "public.py").read_text()
        assert '"suono_count": sum(1 for l in pronte if l.get("tipo") == "suono")' in src
        assert 'righe = [r for r in righe if r.get("suono_count")]' in src
        casa = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        assert "storefrontAPI.getCorsiDirectory({ suono: 1 })" in casa
        assert 'id="percorsi"' in casa and "export function CardPercorso({ c })" in casa
        # il Percorso porta al corso: una sola cassa, mai una seconda in Sound
        assert '<a href={c.url} className="mcard tono-oro"' in casa

    def test_badge_presto_nel_piu(self):
        flag = (FQ / "stato.js").read_text()
        assert "export const SOUND_PIU_ATTIVO = false;" in flag and "export const PIU_PREZZO = '39 € l\\'anno';" in flag
        casa = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        assert "{SOUND_PIU_ATTIVO ? 'PIÙ' : 'PRESTO NEL PIÙ'}" in casa
        player = (FQ / "PublicFrequencyPage.js").read_text()
        assert 'data-testid="fqp-piu"' in player and "'Presto nel Più · oggi la ascolti col Cerchio'" in player
        # nessun cancello del Più nel player (lo decide l'accensione)
        assert "abbonato" not in player


class TestPaginaEAccount:
    def test_pagina_piu_rimanda_finche_spenta(self):
        src = (FQ / "casa" / "PiuPage.jsx").read_text()
        assert 'if (!SOUND_PIU_ATTIVO) return <Navigate to="/meditazioni" replace />;' in src
        assert "soundPiuAPI.checkout('/account#meditazioni')" in src and "soundPiuAPI.portale" in src
        app = (FRONTEND / "App.js").read_text()
        assert 'path="/meditazioni/piu" element={<PiuPage />}' in app
        api = (FRONTEND / "api" / "soundPiu.js").read_text()
        assert "platformApi.post('/platform/me/piu/checkout'" in api and "platformApi.get('/platform/me/piu')" in api

    def test_sezione_account(self):
        src = (FQ / "casa" / "PiuAccount.jsx").read_text()
        # invisibile finche' spento e senza traccia sull'account
        assert "if (!stato || (!stato.attivo && !stato.status && !stato.omaggio_until)) return null;" in src
        acc = (FRONTEND / "features" / "account" / "AccountPage.js").read_text()
        assert "<AccountFavorites /><PiuAccount />" in acc

    def test_shell_piu(self):
        shell = (BACKEND / "routers" / "seo_shell.py").read_text()
        assert 'if head == "meditazioni" and len(parts) == 2 and parts[1] == "piu":' in shell
        assert "def _meta_piu() -> dict:" in shell and 'return {**meta, "noindex": True, "canonical": None, "hreflang": None}' in shell
