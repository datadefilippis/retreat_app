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
        # versioni future mai degradate in silenzio (v2 = voce, e' nostra)
        assert clean_score({"score_version": 3,
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
        """Ogni query sulle TRACCE filtra per organization_id (i suoni
        FQ2 sono platform-level per design: senza org, ma solo su
        audio_assets)."""
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        # il CRUD bozze e' org-scoped; le sezioni FQ1 (public by slug,
        # solo published) e FQ2 (platform-level) hanno regole proprie
        tracks_part, rest = src.split("FQ1 — pubblicazione")
        sounds_part = rest.split("libreria suoni curata")[1]
        # publish/unpublish restano org-scoped
        fq1_part = rest.split("libreria suoni curata")[0]
        for op in ("publish_track", "unpublish_track"):
            fn = fq1_part.split(f"async def {op}")[1][:600]
            assert "organization_id" in fn, f"{op} senza filtro org"
        assert 'status": "published"' in fq1_part.replace("'", '"'), \
            "gli endpoint pubblici devono servire SOLO tracce pubblicate"
        for op in ("find(", "find_one(", "find_one_and_update(",
                   "delete_one("):
            for chunk in tracks_part.split(op)[1:]:
                assert "organization_id" in chunk[:220], \
                    f"query tracce {op} senza filtro organization_id"
        # e la scrittura suoni resta blindata al system admin
        assert sounds_part.count("require_system_admin") >= 2


class TestIsolamentoFrontendFq0:
    """Il modulo e' un mondo a parte: chunk lazy, motore puro."""

    def test_pagina_lazy_in_app(self):
        src = (FRONTEND_SRC / "App.js").read_text()
        assert 'lazy(() => import("./features/frequenze/FrequenzePage"))' in src
        assert 'path="/frequenze"' in src

    def test_engine_senza_react_e_dom(self):
        for name in ("synth.js", "render.js", "voicefx.js", "assets.js"):
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
        # FQ2: layer audio SENZA asset_id = irrecuperabile, si scarta
        assert clean_score({"duration_sec": 600,
                            "layers": [{"kind": "audio",
                                        "buffer": "x" * 1000}]}) is None
        # con asset_id il layer passa, ma i byte no: solo il riferimento
        s = clean_score({"duration_sec": 600,
                         "layers": [{"kind": "audio", "asset_id": "abc123",
                                     "buffer": "x" * 1000, "gain": 0.7}]})
        assert s is not None
        lay = s["layers"][0]
        assert lay["kind"] == "audio" and lay["asset_id"] == "abc123"
        assert "buffer" not in lay


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
        """L'OPERATORE non carica audio. L'unico file input della pagina
        e' quello della regia piattaforma (FQ2), dietro isSystemAdmin."""
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "uploadzone" not in src, "upload operatore tornato nel compositore"
        assert "decodeAudioData" not in src, \
            "la pagina decodifica file locali: l'upload deve restare fuori"
        assert src.count('type="file"') == 1
        admin_block = src.split("fq-sound-upload")[0]
        assert admin_block.rstrip().endswith('data-testid=') or \
            "isSystemAdmin && (" in admin_block[-600:], \
            "il file input dei suoni non e' dietro il gate system admin"

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

    def test_avvio_sessione_invalidato_dallo_stop(self):
        """Secondo bug dello stop (Crea, 19/8): playSession ha degli await
        in mezzo (resume del contesto, decodifica delle basi). Senza token
        di sequenza, un Ferma — o un secondo click su Ascolta mentre il
        primo carica — non trova ancora niente da fermare e il grafo nasce
        subito dopo ORFANO: suona fino in fondo, ingovernabile.
        Misurato in browser: due click davano 48 oscillatori, il Ferma ne
        spegneva 24. Col token: 24 creati, 24 spenti."""
        import re
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "playTokenRef" in src, "manca il token di sequenza dell'ascolto"
        stop_fn = src.split("const stopSession = () =>")[1][:400]
        assert "playTokenRef.current += 1" in stop_fn, \
            "stopSession non invalida gli avvii in volo"
        play_fn = src.split("const playSession = async")[1].split("const seekTo")[0]
        awaits = [m.start() for m in re.finditer(r"\bawait\b", play_fn)]
        start = play_fn.index("startPreview")
        guard = play_fn.rindex("playTokenRef.current !== token", 0, start)
        assert all(a < guard for a in awaits), \
            "c'e' un await dopo l'ultimo controllo del token: il grafo puo' nascere orfano"


class TestSeekMotoreFq05c:
    """Terzo bug dell'ascolto (19/8): spostando il cursore in avanti in
    «Crea», l'ascolto moriva con «Time must be a finite non-negative
    number». Col seek l'origine dei tempi va all'indietro (t0 = adesso -
    punto) e i livelli gia' cominciati finiscono a istanti NEGATIVI, che
    Web Audio rifiuta. Ogni istante schedulato dev'essere ancorato al
    presente. Misurato: pre-fix rejection e cursore congelato, col fix
    tre seek di fila senza un errore."""

    def test_ogni_istante_ancorato_al_presente(self):
        import re
        src = (FQ_DIR / "engine" / "synth.js").read_text()
        body = src.split("export function startPreview")[1]
        assert "const at = (t) => Math.max(now, t);" in body, \
            "manca l'ancora `at` degli istanti in startPreview"
        # nessun istante derivato da s0/t0 puo' finire nudo dentro una
        # chiamata di scheduling: deve passare da at(...)
        for m in re.finditer(
                r"\.(?:setValueAtTime|linearRampToValueAtTime|start|stop)\(([^;]*?)\)\s*;", body):
            arg = m.group(1)
            if "s0" in arg or "t0" in arg:
                assert "at(" in arg, f"istante non ancorato: {m.group(0).strip()}"

    def test_curva_riprende_dal_punto_giusto(self):
        """rampCurve deve saltare il passato invece di schedularlo:
        prende `now` e parte da max(t0, now) col valore di quel punto."""
        src = (FQ_DIR / "engine" / "synth.js").read_text()
        fn = src.split("const rampCurve =")[1].split("\n};")[0]
        assert "now = 0" in fn, "rampCurve non riceve il presente"
        assert "Math.max(t0, now)" in fn, "rampCurve non ancora l'inizio della curva"
        assert "if (t0 + u > from)" in fn, "rampCurve schedula ancora punti nel passato"
        chiamate = src.split("export function startPreview")[1]
        assert chiamate.count("rampCurve(") == chiamate.count(", now)"), \
            "qualche rampCurve dentro startPreview non riceve `now`"


class TestLibreriaSuoniFq2:
    """FQ2 — basi sonore curate: lettura per tutti, scrittura SOLO
    system admin, byte su disco mai in Mongo."""

    def test_lista_pubblica_con_categorie(self):
        try:
            r = requests.get(f"{BASE_URL}/api/frequencies/sounds", timeout=10)
        except requests.RequestException:
            pytest.skip("backend non raggiungibile")
        assert r.status_code == 200
        data = r.json()
        assert set(data["categories"]) == {"ambient", "droni", "campane",
                                           "natura", "ritmi", "voce"}
        for item in data["items"]:
            assert item["stream_url"].startswith("/uploads/audio/")
            assert "buffer" not in item and "data" not in item

    def test_upload_negato_a_org_admin(self):
        hdr = _login()  # admin@demo.com = admin di ORG, non di piattaforma
        r = requests.post(f"{BASE_URL}/api/frequencies/sounds", headers=hdr,
                          files={"file": ("x.wav", b"RIFF0000WAVE", "audio/wav")},
                          data={"title": "abusiva", "category": "droni"},
                          timeout=10)
        assert r.status_code == 403

    def test_roundtrip_bozza_con_base(self):
        """Una traccia con layer audio salva il riferimento asset_id e
        lo restituisce identico: la ricetta resta pochi KB."""
        hdr = _login()
        score = {"score_version": 1, "duration_sec": 600,
                 "layers": [
                     {"kind": "audio", "asset_id": "guardia-fq2",
                      "name": "Base", "start": 0, "end": 600,
                      "gain": 0.7, "loop": True},
                     {"kind": "neuro", "method": "bin", "f0": 10, "f1": 6,
                      "curve": "exp", "start": 0, "end": 600, "gain": 0.25},
                 ]}
        r = requests.post(f"{BASE_URL}/api/frequencies/tracks", headers=hdr,
                          json={"title": "Guardia FQ2", "score": score},
                          timeout=10)
        assert r.status_code == 201, r.text
        tid = r.json()["id"]
        try:
            got = requests.get(f"{BASE_URL}/api/frequencies/tracks/{tid}",
                               headers=hdr, timeout=10).json()
            kinds = [l["kind"] for l in got["score"]["layers"]]
            assert kinds == ["audio", "neuro"]
            assert got["score"]["layers"][0]["asset_id"] == "guardia-fq2"
        finally:
            requests.delete(f"{BASE_URL}/api/frequencies/tracks/{tid}",
                            headers=hdr, timeout=10)

    def test_pagina_risolve_via_engine_non_da_file(self):
        """La pagina non decodifica mai audio direttamente: fetch+decode
        vivono in engine/assets.js (e l'upload resta solo admin)."""
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "decodeAudioData" not in src
        assert "resolveAudioLayers" in src and "isSystemAdmin" in src
        assets = (FQ_DIR / "engine" / "assets.js").read_text()
        assert "decodeAudioData" in assets and "bufferCache" in assets


class TestPubblicazioneFq1:
    """FQ1 — publish org-scoped, ascolto pubblico della RICETTA,
    contatore ascolti; le bozze non pubblicate restano invisibili."""

    def test_ciclo_publish_public_unpublish(self):
        hdr = _login()
        r = requests.post(f"{BASE_URL}/api/frequencies/tracks", headers=hdr,
                          json={"title": "Guardia FQ1 publish",
                                "score": VALID_SCORE}, timeout=10)
        assert r.status_code == 201
        tid = r.json()["id"]
        try:
            # bozza: nessuna superficie pubblica
            slugless = requests.get(
                f"{BASE_URL}/api/frequencies/public/guardia-fq1-publish",
                timeout=10)
            assert slugless.status_code == 404
            pub = requests.post(
                f"{BASE_URL}/api/frequencies/tracks/{tid}/publish",
                headers=hdr, timeout=10)
            assert pub.status_code == 200
            slug = pub.json()["slug"]
            got = requests.get(
                f"{BASE_URL}/api/frequencies/public/{slug}", timeout=10)
            assert got.status_code == 200
            data = got.json()
            assert data["score"]["score_version"] == 1
            assert "organization_id" not in data      # niente id interni
            assert data["operator"]["name"]
            plays0 = data["plays_total"]
            hit = requests.post(
                f"{BASE_URL}/api/frequencies/public/{slug}/play", timeout=10)
            assert hit.status_code == 204
            after = requests.get(
                f"{BASE_URL}/api/frequencies/public/{slug}", timeout=10).json()
            assert after["plays_total"] == plays0 + 1
            # unpublish: il link muore, lo slug resta per la ripubblica
            requests.post(
                f"{BASE_URL}/api/frequencies/tracks/{tid}/unpublish",
                headers=hdr, timeout=10)
            gone = requests.get(
                f"{BASE_URL}/api/frequencies/public/{slug}", timeout=10)
            assert gone.status_code == 404
            again = requests.post(
                f"{BASE_URL}/api/frequencies/tracks/{tid}/publish",
                headers=hdr, timeout=10)
            assert again.json()["slug"] == slug
        finally:
            requests.delete(f"{BASE_URL}/api/frequencies/tracks/{tid}",
                            headers=hdr, timeout=10)

    def test_publish_senza_auth_negato(self):
        try:
            r = requests.post(
                f"{BASE_URL}/api/frequencies/tracks/x/publish", timeout=10)
        except requests.RequestException:
            pytest.skip("backend non raggiungibile")
        assert r.status_code in (401, 403)

    def test_player_pubblico_col_cancello(self):
        """La pagina pubblica esiste, usa lo stesso motore, e il
        cancello chiede Lettera (source frequenze:slug) o account."""
        src = (FQ_DIR / "PublicFrequencyPage.js").read_text()
        assert "startPreview" in src and "resolveAudioLayers" in src
        assert "PREVIEW_SEC" in src and "frequenze:${slug}" in src
        assert "/public/newsletter/subscribe" in src
        assert "platform_token" in src, "l'account Aurya deve sbloccare da solo"
        assert "epilessia" in src, "manca il disclaimer salute"
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/frequenze/:slug"' in app


class TestVetrinaMeditazioniFq3:
    """FQ3 — la vetrina e' l'incentivo: il catalogo NON si vede senza
    sblocco, e lo sblocco e' verificato server-side (iscritto Lettera
    reale via HMAC, o account Aurya). I preferiti vivono sull'account."""

    def test_catalogo_chiuso_senza_sblocco(self):
        try:
            r = requests.get(f"{BASE_URL}/api/frequencies/catalog", timeout=10)
        except requests.RequestException:
            pytest.skip("backend non raggiungibile")
        assert r.status_code == 403
        detail = r.json()["detail"]
        assert detail["error"] == "locked" and "tracks_count" in detail

    def test_unlock_solo_per_iscritti_veri(self):
        # email mai vista: niente sblocco
        r = requests.post(f"{BASE_URL}/api/frequencies/catalog/unlock",
                          json={"email": "fantasma@example.com"}, timeout=10)
        assert r.status_code == 403
        # un token contraffatto non apre
        r2 = requests.get(f"{BASE_URL}/api/frequencies/catalog",
                          headers={"X-Fqz-Unlock": "x@example.com:abc123"},
                          timeout=10)
        assert r2.status_code == 403
        # il Bearer di un OPERATORE non e' un account Aurya: non sblocca
        hdr = _login()
        r3 = requests.get(f"{BASE_URL}/api/frequencies/catalog",
                          headers=hdr, timeout=10)
        assert r3.status_code == 403

    def test_unlock_iscritto_apre_il_catalogo(self):
        """Iscrizione reale via endpoint Lettera consolidato (non si
        tocca: si USA) → unlock → catalogo."""
        email = "guardia.fq3@example.com"
        try:
            sub = requests.post(
                f"{BASE_URL}/api/public/newsletter/subscribe",
                json={"email": email, "consent": True, "language": "it",
                      "source": "guardia-fq3"}, timeout=10)
        except requests.RequestException:
            pytest.skip("backend non raggiungibile")
        if sub.status_code == 429:
            pytest.skip("rate limit subscribe")
        assert sub.status_code == 201
        unlock = requests.post(
            f"{BASE_URL}/api/frequencies/catalog/unlock",
            json={"email": email}, timeout=10)
        assert unlock.status_code == 200
        u = unlock.json()
        cat = requests.get(
            f"{BASE_URL}/api/frequencies/catalog",
            headers={"X-Fqz-Unlock": f"{u['email']}:{u['token']}"},
            timeout=10)
        assert cat.status_code == 200
        for item in cat.json()["items"]:
            assert item.get("slug") and item["operator"]["name"]
            assert "score" not in item     # la vetrina lista, non serve ricette
            assert "organization_id" not in item

    def test_preferiti_solo_account_aurya(self):
        r = requests.get(f"{BASE_URL}/api/frequencies/favorites", timeout=10)
        assert r.status_code in (401, 403)
        # il token OPERATORE non basta (type sbagliato)
        hdr = _login()
        r2 = requests.get(f"{BASE_URL}/api/frequencies/favorites",
                          headers=hdr, timeout=10)
        assert r2.status_code == 401

    def test_superfici_frontend(self):
        src = (FQ_DIR / "MeditazioniPage.js").read_text()
        assert "fqz-meditazioni-locked" in src, "manca lo schermo d'invito"
        assert "/public/newsletter/subscribe" in src
        assert "'meditazioni'" in src        # source dell'iscrizione
        assert "catalogUnlock" in src and "heartAsk" in src
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/meditazioni"' in app
        # innesto minimo nell'hub account consolidato: import + una riga
        account = (FRONTEND_SRC / "features" / "account" /
                   "AccountPage.js").read_text()
        assert "import AccountFavorites from '../frequenze/AccountFavorites'" in account
        assert account.count("<AccountFavorites />") == 1, \
            "l'hub account innesta Frequenze con un import e UNA riga"


class TestVoceOperatoreFv1:
    """FV1 — spezzoni voce: score v2 additivo, asset PER-ORG, solo
    registrazione in-app (docs/FREQUENZE_VOCE_PLAN_2026-08.md)."""

    def test_score_v2_con_voce_roundtrip(self):
        from models.frequency_track import clean_score
        s = clean_score({
            "score_version": 2, "duration_sec": 1200, "voice_duck": True,
            "layers": [
                VALID_SCORE["layers"][0],
                {"kind": "voice", "asset_id": "abc", "name": "Respira",
                 "start": 60, "end": 90, "gain": 2.0,
                 "fx": "dream", "fx_amount": 5},
            ],
        })
        assert s and s["score_version"] == 2 and s["voice_duck"] is True
        voce = [l for l in s["layers"] if l["kind"] == "voice"][0]
        assert voce["gain"] == 1.0 and voce["fx_amount"] == 1.0  # clamp
        assert voce["fx"] == "dream"
        # il campo buffer/di lavoro non passa mai
        assert "buffer" not in voce and "_laneEl" not in voce

    def test_senza_voce_resta_v1_identico(self):
        """Il pregresso non cambia: uno score senza voce salva v1."""
        from models.frequency_track import clean_score
        s = clean_score(VALID_SCORE)
        assert s["score_version"] == 1
        assert "voice_duck" not in s, "voice_duck non deve inquinare il v1"

    def test_voce_invalida_scartata_fx_whitelist(self):
        from models.frequency_track import clean_score
        # senza asset_id il layer voce muore, lo score resta se c'e' altro
        s = clean_score({"duration_sec": 600, "layers": [
            VALID_SCORE["layers"][0], {"kind": "voice", "start": 0}]})
        assert s and all(l["kind"] != "voice" for l in s["layers"])
        # fx sconosciuto → preset di default, mai passthrough
        s2 = clean_score({"duration_sec": 600, "layers": [
            {"kind": "voice", "asset_id": "x", "fx": "vocoder-alieno"}]})
        assert s2["layers"][0]["fx"] == "dream"

    def test_sezione_voce_sempre_org_scoped(self):
        """Ogni query sugli spezzoni filtra per organization_id, e la
        sezione non introduce upload da file manager (registrazione)."""
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        voice_part = src.split("FV1 — spezzoni voce")[1]
        for op in ("find(", "find_one(", "update_one(", "delete_one("):
            for chunk in voice_part.split(op)[1:]:
                assert "organization_id" in chunk[:220], \
                    f"query voce {op} senza filtro organization_id"
        assert "require_system_admin" not in voice_part, \
            "la voce e' dell'operatore, non della regia"
        assert "ext_for_mime" in voice_part, \
            "manca il vaglio del MIME di registrazione"

    def test_api_ciclo_vita_spezzone(self):
        """POST → lista con quota → PATCH rename → DELETE, org-scoped."""
        headers = _login()
        fake = b"\x1aE\xdf\xa3" + b"\x00" * 2000   # magic EBML/webm + padding
        r = requests.post(
            f"{BASE_URL}/api/frequencies/voice", headers=headers,
            files={"file": ("clip.webm", fake, "audio/webm")},
            data={"title": "Guardia FV1", "duration_sec": 4.2}, timeout=15)
        assert r.status_code == 201, r.text
        clip = r.json()
        assert clip["stream_url"].startswith("/uploads/voice/")
        assert "organization_id" not in clip     # mai id interni al client
        try:
            lst = requests.get(f"{BASE_URL}/api/frequencies/voice",
                               headers=headers, timeout=10).json()
            assert any(i["id"] == clip["id"] for i in lst["items"])
            assert lst["quota_bytes"] > 0 and lst["used_bytes"] > 0
            r2 = requests.patch(
                f"{BASE_URL}/api/frequencies/voice/{clip['id']}",
                headers=headers, json={"title": "Rinominata"}, timeout=10)
            assert r2.status_code == 200 and r2.json()["title"] == "Rinominata"
            # i byte sono serviti dallo static mount
            r3 = requests.get(f"{BASE_URL}{clip['stream_url']}", timeout=10)
            assert r3.status_code == 200 and len(r3.content) == len(fake)
        finally:
            rd = requests.delete(
                f"{BASE_URL}/api/frequencies/voice/{clip['id']}",
                headers=headers, timeout=10)
            assert rd.status_code == 204
        # dopo il delete anche il file sparisce
        r4 = requests.get(f"{BASE_URL}{clip['stream_url']}", timeout=10)
        assert r4.status_code == 404

    def test_upload_senza_mime_audio_rifiutato(self):
        headers = _login()
        r = requests.post(
            f"{BASE_URL}/api/frequencies/voice", headers=headers,
            files={"file": ("nota.pdf", b"%PDF-", "application/pdf")},
            data={"title": "x", "duration_sec": 1}, timeout=10)
        assert r.status_code == 400


class TestMotoreVoceFv2:
    """FV2 — catena effetti voce: preset allineati col backend, motore
    puro, nessun kind ignoto nel ramo oscillatori, export con coda."""

    def test_preset_allineati_backend_frontend(self):
        """VOICE_FX (modello) e VOICE_PRESETS (voicefx.js) sono gemelli:
        un preset aggiunto da una parte sola e' un bug di contratto."""
        import re
        from models.frequency_track import VOICE_FX
        src = (FQ_DIR / "engine" / "voicefx.js").read_text()
        js_keys = re.findall(r"^  (\w+): \{", src, re.M)
        assert sorted(js_keys) == sorted(VOICE_FX), \
            f"preset disallineati: js={js_keys} py={list(VOICE_FX)}"

    def test_ir_sintetica_niente_file_esterni(self):
        src = (FQ_DIR / "engine" / "voicefx.js").read_text()
        assert "makeImpulse" in src and "createConvolver" in src
        assert "fetch(" not in src, \
            "il riverbero deve generare l'IR, non scaricarla"

    def test_nessun_kind_ignoto_nel_ramo_neuro(self):
        """Un layer voice/futuro non deve MAI cadere nel ramo oscillatori
        (suonerebbe come un tono): il filtro e' kind === 'neuro'."""
        for name in ("synth.js", "render.js"):
            src = (FQ_DIR / "engine" / name).read_text()
            assert "!== 'audio'" not in src, \
                f"engine/{name}: filtro per esclusione — i kind nuovi cadono nel ramo neuro"
            assert "=== 'neuro'" in src

    def test_export_prerender_con_coda(self):
        """L'export pre-renderizza ogni clip CON l'effetto e la sua coda
        (tailSeconds): il mixer a chunk non deve troncare i riverberi."""
        src = (FQ_DIR / "engine" / "render.js").read_text()
        assert "renderWetVoice" in src and "tailSeconds" in src
        assert "duckEnvelope" in src, "manca il ducking nell'export"

    def test_preview_voce_e_ducking(self):
        src = (FQ_DIR / "engine" / "synth.js").read_text()
        assert "voiceLayers" in src and "buildVoiceChain" in src
        assert "duckEnvelope" in src and "voiceDuck" in src
        # il declick agisce sull'ingresso della catena, mai sulla coda
        blocco = src.split("spezzoni voce")[1].split("score.layers")[0]
        assert "chain.input.gain" in blocco
