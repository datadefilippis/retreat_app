"""R4 (25/9/2026 sera) — la misura della porta in regia.

I «numeri del lunedi» (RB14, /admin/platform/lunedi) portano la sezione
`porta`: account Aurya creati (7/30 giorni, totali), richieste di contatto
(righe, persone, operatori raggiunti, 30 giorni), ordini nati con l'account
su tutti gli ordini (30 giorni), iscritti al Cerchio arrivati dall'account,
stato degli interruttori. Solo conteggi, mai email. La Panoramica mostra
la card «La porta (30 giorni)» e la riga degli interruttori.
"""
import os
from pathlib import Path

import pytest
import requests

RADICE = Path(__file__).resolve().parents[2]
BACKEND = RADICE / "backend"
FE = RADICE / "frontend" / "src"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
ADMIN = (BACKEND / "routers" / "admin_platform.py").read_text(encoding="utf-8")
TAB = (FE / "features" / "admin" / "PlatformOverviewTab.js").read_text(encoding="utf-8")

CHIAVI = {"account_7g", "account_30g", "account_totali", "richieste_30g", "persone_30g",
          "operatori_raggiunti_30g", "ordini_30g", "ordini_con_account_30g",
          "cerchio_via_account_30g", "interruttori"}


class TestSorgente:
    def test_la_sezione_porta_solo_conteggi(self):
        blocco = ADMIN[ADMIN.index("# 8. LA PORTA (R4"):ADMIN.index('_cache["lunedi"]')]
        for k in CHIAVI:
            assert f'"{k}"' in blocco, k
        assert '"porta": porta,' in blocco
        assert '"provenienza.canale": "account"' in blocco
        assert '"platform_account_id": {"$nin": [None, ""]}' in blocco
        assert '"email"' not in blocco                      # mai email: solo conteggi
        assert "contatti_dietro_porta()" in blocco and "login_senza_verifica()" in blocco

    def test_la_panoramica_mostra_la_porta(self):
        assert 'label="La porta (30 giorni)"' in TAB
        assert 'data-testid="numeri-lunedi-porta"' in TAB
        assert "lunedi.porta.richieste_30g" in TAB and "lunedi.porta.ordini_con_account_30g" in TAB
        assert "contatti dietro la porta {lunedi.porta.interruttori.contatti_dietro_porta ? 'ACCESO' : 'spento'}" in TAB


class TestDalVivo:
    def test_lunedi_porta(self):
        r = None
        for pwd in ("demo1234", "Demo1234!"):
            r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "sysadmin@demo.com", "password": pwd}, timeout=10)
            if r.status_code == 200:
                break
        if not r or r.status_code != 200:
            pytest.skip("login sysadmin non disponibile (rate limit?)")
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        x = requests.get(f"{BASE_URL}/api/admin/platform/lunedi", headers=h, timeout=30)
        if x.status_code == 404:
            pytest.skip("backend su :8000 non riavviato con R4")
        assert x.status_code == 200, x.text
        porta = x.json().get("porta")
        assert porta and set(porta) == CHIAVI
        assert porta["account_totali"] >= porta["account_30g"] >= porta["account_7g"] >= 0
        assert porta["ordini_30g"] >= porta["ordini_con_account_30g"] >= 0
        assert set(porta["interruttori"]) == {"contatti_dietro_porta", "login_senza_verifica"}
