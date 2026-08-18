"""Frequenze by Aurya — guardie del ciclo FQ0 (18/8/2026).

Il principio da difendere (docs/FREQUENZE_PLAN_2026-08.md): la traccia
e' la RICETTA (score JSON versionato), mai l'audio; il modulo e' isolato
(collection dedicata, chunk lazy, motore senza React) e org-scoped.
"""
import os
from pathlib import Path

import pytest
import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ_DIR = FRONTEND_SRC / "features" / "frequenze"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")

VALID_SCORE = {
    "score_version": 1, "duration_sec": 1200,
    "fade_in_sec": 10, "fade_out_sec": 20,
    "layers": [
        {"kind": "neuro", "name": "Alpha", "method": "bin", "timbre": "warm",
         "carrier": 180, "f0": 12, "f1": 8, "curve": "exp",
         "start": 0, "end": 240, "gain": 0.25},
    ],
    "phases": [{"t": 0, "name": "ingresso"}],
}


def _login():
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
    except requests.RequestException:
        pytest.skip("backend non raggiungibile")
    if r.status_code != 200:
        pytest.skip("demo login unavailable (rate limit?)")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestScoreModelFq0:
    """clean_score: contratto v1 — struttura netta, valori riportati."""

    def test_score_valido_roundtrip(self):
        from models.frequency_track import clean_score
        s = clean_score(VALID_SCORE)
        assert s and s["score_version"] == 1
        assert s["duration_sec"] == 1200 and len(s["layers"]) == 1
        assert s["layers"][0]["method"] == "bin"

    def test_struttura_sbagliata_rifiutata(self):
        from models.frequency_track import clean_score
        assert clean_score(None) is None
        assert clean_score({}) is None
        assert clean_score({"layers": []}) is None
        assert clean_score({"layers": [{"method": "telepatia"}]}) is None
        # versioni future mai degradate in silenzio
        assert clean_score({"score_version": 2,
                            "layers": VALID_SCORE["layers"]}) is None

    def test_valori_fuori_range_riportati(self):
        from models.frequency_track import clean_score, LAYERS_MAX
        s = clean_score({"duration_sec": 10 ** 9,
                         "layers": [{"method": "iso", "f0": 500, "f1": -3,
                                     "gain": 9, "carrier": 1}]})
        assert s["duration_sec"] == 7200
        lay = s["layers"][0]
        assert lay["f0"] == 60 and lay["f1"] == 0.2
        assert lay["gain"] == 1.0 and lay["carrier"] == 20.0
        # tetto livelli
        many = {"duration_sec": 600,
                "layers": [{"method": "bin"}] * (LAYERS_MAX + 10)}
        assert len(clean_score(many)["layers"]) == LAYERS_MAX

    def test_bilaterale_ha_tetto_suo(self):
        from models.frequency_track import clean_score
        s = clean_score({"duration_sec": 600,
                         "layers": [{"method": "bil", "f0": 40, "f1": 40}]})
        assert s["layers"][0]["f0"] == 3.0  # alternanza dx/sx, non battito


class TestApiCrudFq0:
    """CRUD bozze: org-scoped, draft-only, validazione server."""

    def test_ciclo_completo(self):
        hdr = _login()
        r = requests.post(f"{BASE_URL}/api/frequencies/tracks", headers=hdr,
                          json={"title": "Guardia FQ0", "score": VALID_SCORE,
                                "intent": "meditare"}, timeout=10)
        assert r.status_code == 201, r.text
        t = r.json()
        assert t["status"] == "draft" and t["intent"] == "meditare"
        tid = t["id"]
        try:
            lst = requests.get(f"{BASE_URL}/api/frequencies/tracks",
                               headers=hdr, timeout=10).json()["items"]
            mine = [i for i in lst if i["id"] == tid]
            assert mine and mine[0]["layers_count"] == 1
            # patch score invalido = 400, la bozza resta intatta
            bad = requests.patch(
                f"{BASE_URL}/api/frequencies/tracks/{tid}", headers=hdr,
                json={"score": {"layers": []}}, timeout=10)
            assert bad.status_code == 400
            ok = requests.patch(
                f"{BASE_URL}/api/frequencies/tracks/{tid}", headers=hdr,
                json={"title": "Guardia FQ0 v2"}, timeout=10)
            assert ok.status_code == 200
            assert ok.json()["title"] == "Guardia FQ0 v2"
        finally:
            d = requests.delete(f"{BASE_URL}/api/frequencies/tracks/{tid}",
                                headers=hdr, timeout=10)
            assert d.status_code == 204
        gone = requests.get(f"{BASE_URL}/api/frequencies/tracks/{tid}",
                            headers=hdr, timeout=10)
        assert gone.status_code == 404

    def test_senza_auth_niente(self):
        try:
            r = requests.get(f"{BASE_URL}/api/frequencies/tracks", timeout=10)
        except requests.RequestException:
            pytest.skip("backend non raggiungibile")
        assert r.status_code in (401, 403)

    def test_router_sempre_org_scoped(self):
        """Ogni query del router filtra per organization_id: l'isolamento
        multi-tenant non deve dipendere dalla memoria di chi edita."""
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        for op in ("find(", "find_one(", "find_one_and_update(",
                   "delete_one("):
            for chunk in src.split(op)[1:]:
                assert "organization_id" in chunk[:220], \
                    f"query {op} senza filtro organization_id"


class TestIsolamentoFrontendFq0:
    """Il modulo e' un mondo a parte: chunk lazy, motore puro."""

    def test_pagina_lazy_in_app(self):
        src = (FRONTEND_SRC / "App.js").read_text()
        assert 'lazy(() => import("./features/frequenze/FrequenzePage"))' in src
        assert 'path="/frequenze"' in src

    def test_engine_senza_react_e_dom(self):
        for name in ("synth.js", "render.js"):
            src = (FQ_DIR / "engine" / name).read_text()
            assert "from 'react'" not in src and 'from "react"' not in src, \
                f"engine/{name} dipende da React"
            assert "document." not in src, f"engine/{name} tocca il DOM"

    def test_lamejs_solo_nel_chunk_frequenze(self):
        """L'encoder da 150KB non deve mai entrare nel bundle principale:
        import dinamico, e nessun riferimento fuori da features/frequenze."""
        render = (FQ_DIR / "engine" / "render.js").read_text()
        assert "await import('./lamejs.vendor')" in render
        offenders = []
        for path in FRONTEND_SRC.rglob("*.js"):
            if "features/frequenze" in str(path) or "node_modules" in str(path):
                continue
            if "lamejs" in path.read_text():
                offenders.append(str(path))
        assert not offenders, f"lamejs referenziato fuori dal chunk: {offenders}"

    def test_contenuti_estratti(self):
        bib = (FQ_DIR / "content" / "biblioteca.js").read_text()
        assert "Bande cerebrali" in bib and "Glossario" in bib
        prots = (FQ_DIR / "content" / "protocolli.js").read_text()
        for name in ("Dormire", "Meditare", "Rilassare", "Concentrare",
                     "Elaborare", "Energizzare"):
            assert name in prots, f"protocollo {name} mancante"
        # il patto di onesta' scientifica viaggia coi dati
        assert "EMDR" in prots and "grade" in prots


class TestNienteAudioInMongoFq0:
    """Il principio del piano: mai byte audio nel documento traccia."""

    def test_score_non_accetta_buffer(self):
        from models.frequency_track import clean_score
        s = clean_score({"duration_sec": 600,
                         "layers": [{"method": "bin", "kind": "audio",
                                     "buffer": "x" * 1000}]})
        # il layer viene normalizzato a neuro puro: niente campi estranei
        assert s is not None
        assert "buffer" not in s["layers"][0]
        assert s["layers"][0]["kind"] == "neuro"


class TestDesignPrototipoFq05:
    """FQ0.5 (founder, 18/8): il design dell'app Frequenze e' quello del
    prototipo — prodotto a se' stante, scuro — e NON deve mai inquinare
    il gestionale: ogni selettore del suo CSS vive sotto .fqz."""

    def test_css_tutto_scopato(self):
        import re
        css = (FQ_DIR / "frequenze.css").read_text()
        # rimuovi commenti e blocchi @ (i selettori interni sono gia'
        # scopati dal generatore, controllati sotto)
        css_clean = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        for rule in re.finditer(r"([^{}]+)\{", css_clean):
            sel = rule.group(1).strip()
            if not sel or sel.startswith("@"):
                continue
            for part in sel.split(","):
                part = part.strip()
                if part and not part.startswith(".fqz"):
                    raise AssertionError(f"selettore non scopato: {part!r}")

    def test_pagina_standalone_col_ritorno(self):
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "AppLayout" not in src, \
            "l'app Frequenze e' un prodotto a se': niente guscio gestionale"
        assert "navigate('/dashboard')" in src, \
            "manca il ritorno al gestionale dalla testata"
        assert "frequenze.css" in src
        # il gate sicurezza del prototipo c'e' ancora
        assert "fqz_gate_ok" in src and "epilessia" in src


class TestSoloSuoniPiattaformaFq05b:
    """Founder 18/8: niente upload dell'operatore — le tracce si
    compongono SOLO con frequenze e suoni della piattaforma. E il mondo
    «Suoni» (sparito nel primo porting) deve esserci, come segnaposto
    finche' FQ2 non porta la libreria."""

    def test_niente_upload_nel_compositore(self):
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "uploadzone" not in src, "upload operatore tornato nel compositore"
        assert "decodeAudioData" not in src, \
            "la pagina decodifica file locali: l'upload deve restare fuori"
        assert 'type="file"' not in src

    def test_worldswitch_frequenze_suoni(self):
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "fq-worldswitch" in src and "Suoni" in src
        assert "fq-soundsoon" in src, "manca il segnaposto della libreria"
        for cat in ("Ambient", "Droni", "Campane", "Natura", "Ritmi", "Voce"):
            assert cat in src, f"categoria suoni {cat} mancante"

    def test_handle_live_fuori_dagli_updater(self):
        """Il bug dello stop: creare il grafo audio dentro un updater
        React lo fa partire due volte in dev (updater rieseguiti) e una
        voce resta orfana a suonare. Gli handle vivono in un ref."""
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "liveCardsRef" in src
        import re
        for m in re.finditer(r"set\w+\(\s*\((?:lc|ls|ps|x)\)?\s*=>", src):
            chunk = src[m.start():m.start() + 400]
            assert "startCardLive" not in chunk and "startPreview" not in chunk, \
                "side effect audio dentro un updater React"
