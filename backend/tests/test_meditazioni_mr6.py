"""MR6 (8/10/2026 sera, founder) — LA LANDING DI /sound TORNA, OTTIMIZZATA.

«La landing aveva il suo perché: spiegava bene e con design figo tutto
Aurya Sound.» L'hub a soli pulsanti di SN1 resta dietro un flag spento;
la landing esplicativa torna senza le esperienze ritirate (CALM, GROUND),
con la meditazione in vetrina del giorno e il rimando alla casa. Anche:
al pubblico niente Visual sulla pagina della meditazione (decisione 3).
"""
import os
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")


class TestLanding:
    def test_torna_la_landing(self):
        flag = (FQ / "stato.js").read_text()
        assert "export const SOUND_HUB_SEMPLICE = false;" in flag
        src = (FQ / "SoundHomePage.jsx").read_text()
        assert "return SOUND_HUB_SEMPLICE && SOUND_CASA_NUOVA ? <SoundHubPage /> : <SoundHomePageVecchia />;" in src
        # via le esperienze ritirate, dentro il rimando alla casa
        for ritirata in ("/sound/calm", "/sound/ground", "ASSAGGI"):
            assert ritirata not in src, ritirata
        assert 'data-testid="sh-casa-rimando"' in src and "Entra nella casa delle meditazioni" in src
        # la vetrina del giorno, con il vecchio slug come ripiego
        assert "frequenciesAPI.vetrinaPubblica()" in src and "r.data?.slug || VETRINA_SLUG" in src
        # il racconto resta: fenomeni, porte, meditazioni, Crea, onesta', metodo, futuro, congedo
        for sez in ("sh-fenomeni", "sh-porte", "sh-porta-esperienze", "sld-crea", "sh-evidenza", "sh-processo", "sh-futuro", "sh-fine"):
            assert sez in src, sez

    def test_vetrina_pubblica(self):
        src = (BACKEND / "routers" / "frequencies.py").read_text()
        assert src.index('@router.get("/public/vetrina")') < src.index('@router.get("/public/{slug}")')   # «vetrina» non e' uno slug
        corpo = src.split('@router.get("/public/vetrina")')[1].split("\n@router")[0]
        assert '"anteprima_url": {"$nin": [None, ""]}' in corpo and '"in_vetrina": True' in corpo
        assert "scelte[giorno % len(scelte)]" in corpo
        api = (FRONTEND / "api" / "frequencies.js").read_text()
        assert "vetrinaPubblica: () => api.get('/frequencies/public/vetrina')" in api

    def test_vetrina_dal_vivo(self):
        import requests
        try:
            r = requests.get(f"{BASE_URL}/api/frequencies/public/vetrina", timeout=10)
        except requests.RequestException:
            pytest.skip("server locale non raggiungibile")
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            slug = r.json()["slug"]
            p = requests.get(f"{BASE_URL}/api/frequencies/public/{slug}", timeout=10)
            assert p.status_code == 200 and p.json().get("anteprima_url")


class TestVisualPubblico:
    def test_niente_visual_al_pubblico(self):
        flag = (FQ / "stato.js").read_text()
        assert "export const VISUAL_PUBBLICO_ATTIVO = false;" in flag
        player = (FQ / "PublicFrequencyPage.js").read_text()
        assert "{VISUAL_PUBBLICO_ATTIVO || localStorage.getItem('token') ? (" in player
        assert "'✦ Guarda il suono'" in player   # il toggle resta per chi compone
