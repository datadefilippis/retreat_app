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
        # LN — il workspace vive su /sound/*, il vecchio indirizzo redirige
        assert 'path="/sound/*"' in src
        assert '<Route path="/frequenze" element={<Navigate to="/sound/esplora"' in src

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
        for cat in ("Bande cerebrali", "Altre frequenze", "Metodi"):
            assert cat in bib, f"categoria {cat} mancante nella biblioteca"
        # la Guida e il Glossario hanno lasciato la griglia di schede:
        # ora sono una pagina editoriale a se'
        guida = (FQ_DIR / "content" / "guida.js").read_text()
        assert "GLOSSARIO" in guida and "PERCORSO" in guida
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
        # i @keyframes non contengono selettori DOM (percentuali/from/to),
        # ma il loro NOME vive nel namespace globale: deve essere fqz*
        for m in re.finditer(r"@keyframes\s+([\w-]+)", css_clean):
            assert m.group(1).startswith("fqz"), \
                f"@keyframes {m.group(1)!r} senza prefisso fqz (namespace globale)"
        css_clean = re.sub(
            r"@keyframes[^{]+\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css_clean)
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
        from models.audio_asset import SOUND_CATEGORIES
        # la lista puo' crescere (SL, 20/8: «corpo» e «transizioni»):
        # cio' che deve restare vero e' che l'endpoint dica ESATTAMENTE
        # le categorie del modello, etichette comprese
        assert data["categories"] == SOUND_CATEGORIES
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


class TestLeggioVoceFv3:
    """FV3 — il leggio in Crea: registrazione in-app, spezzoni riusabili,
    preset per layer, ducking. Verificato live in browser (webm/opus
    sintetico → upload → + sessione → catena Sogno in ascolto)."""

    def test_leggio_solo_registrazione(self):
        """La voce nasce dal microfono: getUserMedia + MediaRecorder,
        nessun nuovo input file (resta solo quello regia suoni FQ2)."""
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "fqz-voicedesk" in src, "manca il pannello leggio"
        assert "getUserMedia" in src and "MediaRecorder" in src
        assert src.count('type="file"') == 1, \
            "la voce non deve aprire la porta all'upload di file"
        assert "recordVoice" in src, "la registrazione deve passare dall'API"

    def test_handle_registrazione_nei_ref(self):
        """MediaRecorder/stream/anteprime vivono in ref: mai side effect
        audio dentro gli updater React (lezione del bug stop)."""
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        for ref in ("recRef", "voicePrevRef"):
            assert ref in src, f"manca {ref}"

    def test_layer_voce_con_preset_e_taglio_leggibile(self):
        """Il layer voce parla la lingua dell'operatore: preset e dose
        di effetto sulla riga. Il taglio NON sta piu' qui — vive sulla
        registrazione (FV6, feedback founder 19/8), e comunque mai in
        offset tecnici."""
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "VOICE_PRESETS" in src and "fx_amount" in src
        assert '">salta<' not in src, "il vecchio campo «salta» confondeva"
        assert "setVoiceCutStart" not in src and "setVoiceCutEnd" not in src, \
            "il taglio e' tornato sul livello invece che sulla registrazione"
        assert "togli dall'inizio" in src, \
            "il taglio non e' nelle impostazioni della registrazione"

    def test_voce_e_duck_arrivano_a_motore_ed_export(self):
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "resolveVoiceLayers" in src
        play = src.split("const playSession")[1].split("const seekTo")[0]
        assert "voiceLayers" in play and "voiceDuck" in play
        # decisione founder 19/8: NESSUN export nella UI del compositore
        # (la capacita' resta nel motore: render.js, guardia FV2)
        assert "doExport" not in src and "Esporta MP3" not in src, \
            "l'export non deve riapparire in Crea"


class TestPuliziaVoceFv5:
    """FV5 — pulizia non distruttiva e taglio: il FILE registrato non si
    tocca mai; trim/gate/declick/normalize sono matematica deterministica
    sul buffer, il taglio dell'inizio vive nella ricetta (clip_in)."""

    def test_clip_in_nella_ricetta(self):
        from models.frequency_track import clean_score
        s = clean_score({"duration_sec": 600, "layers": [
            {"kind": "voice", "asset_id": "x", "clip_in": 3.5},
            {"kind": "voice", "asset_id": "y", "clip_in": -7},
        ]})
        assert s["layers"][0]["clip_in"] == 3.5
        assert s["layers"][1]["clip_in"] == 0.0, "clip_in negativo va a zero"

    def test_pulizia_deterministica_ovunque(self):
        """cleanVoiceBuffer si applica alla RISOLUZIONE (assets) e
        all'anteprima del leggio: mai al file, identica ovunque."""
        assets = (FQ_DIR / "engine" / "assets.js").read_text()
        assert "cleanVoiceBuffer" in assets
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "cleanVoiceBuffer" in page, \
            "l'anteprima del leggio deve suonare come la sessione"
        fx = (FQ_DIR / "engine" / "voicefx.js").read_text()
        assert "cleanCache" in fx, "senza cache si ripulisce a ogni play"
        assert "solo silenzio" in fx, \
            "un clip tutto silenzio non va toccato (bordo documentato)"

    def test_clip_in_arriva_a_preview_ed_export(self):
        synth = (FQ_DIR / "engine" / "synth.js").read_text()
        blocco = synth.split("spezzoni voce")[1].split("score.layers")[0]
        assert "clip_in" in blocco, "il taglio non arriva all'anteprima"
        render = (FQ_DIR / "engine" / "render.js").read_text()
        assert "clip_in" in render.split("renderWetVoice")[1][:800], \
            "il taglio non arriva all'export"


class TestGuidaEditorialeGd:
    """GD — «Le fondamenta»: la Guida e' una pagina editoriale, non piu'
    una griglia di schede. Queste guardie tengono il patto scientifico:
    la pagina descrive cosa viene generato, non promette cosa accade
    nel cervello di chi ascolta."""

    # frasi che il founder ha chiesto di eliminare, con il motivo
    VIETATE = {
        "6.000 Hz": "confondeva la frequenza di battito con quella udibile",
        "il binaurale e' il piu' elegante": "gerarchia di efficacia non dimostrata",
        "il binaurale è il più elegante": "gerarchia di efficacia non dimostrata",
        "effetto è identico ovunque": "effetto ≠ segnale",
        "l'effetto degrada": "senza cuffie il segnale cambia natura, non «degrada»",
        "tende ad assecondarne il ritmo": "entrainment presentato come automatico",
        "invita\" verso il theta": "battito descritto come interruttore di stato",
        "è la gradualità che fa il lavoro": "scelta di design spacciata per legge",
        "svegliarlo di soprassalto": "prescrizione neurofisiologica non dimostrata",
    }
    # verbi che non si usano su un fenomeno non dimostrato
    PROMESSE = ("sincronizza il cervello", "porta il cervello in",
                "riequilibra", "guarisce", "ripara", "rigenera")

    def _testi(self):
        """Solo il testo che l'utente legge: i commenti del codice
        NOMINANO le frasi vietate per spiegarle, e non vanno contati."""
        import re
        out = {}
        for p in (FQ_DIR / "content" / "guida.js", FQ_DIR / "GuidaView.js",
                  FQ_DIR / "content" / "biblioteca.js"):
            src = re.sub(r"/\*.*?\*/", " ", p.read_text(), flags=re.S)
            src = re.sub(r"^\s*//.*$", " ", src, flags=re.M)
            out[p.name] = src
        return out

    def test_nessun_claim_ritirato(self):
        for nome, src in self._testi().items():
            basso = src.lower()
            for frase, motivo in self.VIETATE.items():
                assert frase.lower() not in basso, \
                    f"{nome}: «{frase}» e' tornata — {motivo}"

    # una promessa CITATA per smentirla e' il contrario di una promessa:
    # «Non e' corretto dire che un battito 6 Hz porta il cervello in Theta»
    # la smentita puo' stare prima («non e' corretto dire che…») o dopo
    # («l'affermazione secondo cui… non e' supportata»): si guardano
    # entrambi i lati, ed e' il contesto a decidere, non la parola
    SMENTITE = (r"non è .{0,14}corretto", r"non e' .{0,14}corretto",
                "non significa", "non va descritt", "invece che",
                "non determina", "affermazione secondo cui",
                "non è supportat", "non e' supportat", "non sono supportat",
                "nessuna evidenza", "non dimostra", "non va ridotto",
                "attribuzione tradizionale")

    def test_nessuna_promessa_terapeutica(self):
        import re
        for nome, src in self._testi().items():
            basso = src.lower()
            for verbo in self.PROMESSE:
                for m in re.finditer(re.escape(verbo), basso):
                    intorno = basso[max(0, m.start() - 160):m.end() + 220]
                    assert any(re.search(s, intorno) for s in self.SMENTITE), \
                        f"{nome}: promessa «{verbo}» non smentita — …{intorno[:120]}"

    def test_le_sei_tappe_in_ordine(self):
        guida = (FQ_DIR / "content" / "guida.js").read_text()
        attese = ["gd-cervello", "gd-entrainment", "gd-metodi",
                  "gd-ascolto", "gd-sessione", "gd-precisione"]
        pos = [guida.index(a) for a in attese]
        assert pos == sorted(pos), "il percorso non e' piu' progressivo"
        view = (FQ_DIR / "GuidaView.js").read_text()
        for a in attese:
            assert f'id="{a}"' in view, f"sezione {a} senza ancora"

    def test_distinzione_e_contesto_sono_in_pagina(self):
        """I due passaggi che il founder considera identita' editoriale."""
        view = (FQ_DIR / "GuidaView.js").read_text()
        assert "Il suono non lavora da solo" in view
        assert "dimostrare un cambiamento cerebrale" in view
        assert "Un badge C non significa" in view

    def test_precisione_promette_solo_cio_che_il_motore_fa(self):
        """La sezione 06 puo' dichiarare continuita' di fase e dissolvenze
        solo perche' il motore le implementa davvero."""
        synth = (FQ_DIR / "engine" / "synth.js").read_text()
        render = (FQ_DIR / "engine" / "render.js").read_text()
        assert "_ph +=" in render or "_ph +=" in synth, \
            "nessuna fase accumulata: la Guida non puo' promettere continuita'"
        assert "fade_in_sec" in render, "nessuna dissolvenza dichiarabile"
        guida = (FQ_DIR / "content" / "guida.js").read_text()
        assert "file esportato" not in guida.lower(), \
            "l'export non e' piu' esposto all'operatore: non si promette"

    def test_guida_non_porta_a_crea(self):
        """«Esplora Aurya Sound» riporta alla biblioteca, mai al compositore."""
        view = (FQ_DIR / "GuidaView.js").read_text()
        assert "setView('create')" not in view and "onCreate" not in view
        for cat in ("Bande cerebrali", "Altre frequenze", "Metodi"):
            assert f"onExplore('{cat}')" in view, f"manca l'uscita verso {cat}"

    def test_la_guida_non_tocca_audio_ne_biblioteca(self):
        view = (FQ_DIR / "GuidaView.js").read_text()
        for vietato in ("AudioContext", "startPreview", "oscillator", "BIB"):
            assert vietato not in view, \
                f"GuidaView tocca {vietato}: deve restare editoriale"


class TestLinkPagineLn:
    """LN — ogni pagina di valore ha il suo link, e i link vecchi
    continuano a rispondere. La regola piu' importante: /frequenze/:slug
    appartiene ai link pubblici gia' condivisi e non si tocca MAI."""

    def test_slug_pubblici_intatti(self):
        """La rotta player e i link generati restano su /frequenze/<slug>."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/frequenze/:slug"' in app
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        assert page.count("/frequenze/${") >= 2, \
            "publish e copia-link devono generare ancora origin/frequenze/<slug>"

    def test_viste_derivate_dall_url(self):
        """La vista non e' piu' useState: la verita' sta nell'URL,
        cosi' il refresh resta dove sei."""
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "useState('explore')" not in page
        for path in ("esplora", "crea", "impara", "tracce"):
            assert f"{path}:" in page.replace("'", "").replace(" ", "") \
                or f"'{path}'" in page, f"vista {path} non mappata"
        # glossario = percorso, non stato
        assert "/sound/impara/glossario" in page

    def test_bozza_nell_url(self):
        """/sound/crea?bozza=<id>: apertura, salvataggio e refresh
        parlano lo stesso link; la bozza eliminata esce dall'URL."""
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "bozza=${t.id}" in page.replace("`", "")
        assert "qs.get('bozza')" in page
        blocco_open = page.split("const openDraft")[1][:900]
        assert "nav" in blocco_open, \
            "openDraft deve distinguere click (naviga) da refresh (no)"

    def test_login_rispetta_next(self):
        """LN0 — il rimbalzo refresh→login non deve piu' perdere la
        pagina: ProtectedRoute passa next=, il login lo rispetta e
        accetta SOLO path interni (niente open redirect)."""
        app = (FRONTEND_SRC / "App.js").read_text()
        blocco = app.split("const ProtectedRoute")[1][:900]
        assert "next=" in blocco and "encodeURIComponent" in blocco
        auth = (FRONTEND_SRC / "pages" / "AuthPages.js").read_text()
        assert "searchParams.get('next')" in auth
        assert "startsWith('//')" in auth, "manca la guardia open-redirect"

    def test_history_onesta(self):
        """Cambio vista = push; cambio tab/mondo/categoria = replace.
        Il back non deve ripercorrere ogni tab cliccato."""
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        for setter in ("setWorld", "setSoundCat", "setCurTab"):
            blocco = page.split(f"const {setter} = ")[1][:300]
            assert "replace: true" in blocco, f"{setter} deve fare replace"
        set_view = page.split("const setView = ")[1].split("\n")[0]
        assert "replace" not in set_view, "setView deve fare push (vista nuova)"


class TestSoundPubblicoSp:
    """SP — la biblioteca e' pubblica (LEGGI → APPROFONDISCI → IMPARA),
    l'ascolto resta valore professionale. La vera frontiera sono le API
    org-scoped (gia' sotto guardia): qui si difende la separazione."""

    def test_rotte_pubbliche_e_cancello_interno(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        # la wildcard NON e' piu' avvolta da ProtectedRoute…
        assert '<Route path="/sound/*" element={<FrequenzePage />} />' in app
        # …e /sound esatto e' la porta pubblica
        assert 'path="/sound" element={<SoundLandingPage />}' in app
        # il cancello vive dentro la pagina: crea/tracce → login?next=
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        blocco = page.split("const needsAuth =")[1][:900]
        assert "'create'" in page.split("const needsAuth =")[1][:80]
        assert "/login?next=" in blocco
        assert "verify-email-required" in blocco, \
            "il gate email-verificata di ProtectedRoute va replicato"

    def test_ascolto_libero_composizione_professionale(self):
        """SP-bis (decisione founder 19/8): le frequenze si ascoltano
        tutti. Resta professionale COMPORRE — e chi ascolta, chiunque
        sia, deve prima leggere gli avvisi di sicurezza."""
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        foot = page.split("{entry.cfg && (")[1][:700]
        # Ascolta viene PRIMA di qualsiasi gate di ruolo; il gate copre
        # solo «+ sessione», che sta dopo
        i_ascolta = foot.index("'Ferma' : 'Ascolta'")
        i_gate = foot.index("{canCompose && (")
        assert i_ascolta < i_gate, \
            "Ascolta e' finito dietro un gate di ruolo: si ascolta tutti"
        assert "+ sessione" in foot[i_gate:], \
            "«+ sessione» e' composizione: resta agli operatori"
        assert "      {!gateOk && (" in page, \
            "il sipario vale per CHIUNQUE ascolti, non solo per gli operatori"
        # composizione e mondo di lavoro restano professionali
        assert "view === 'explore' && canCompose && (" in page, \
            "il mondo Suoni e' materiale di lavoro, non editoriale"
        assert "canCompose && view !== 'create' && layers.length > 0" in page
        # e la barra live: fermare tutto si', comporre no
        live = page.split("liveCount > 0 && view === 'explore' && (")[1][:600]
        assert "Ferma tutto" in live and "{canCompose && (" in live

    def test_cta_non_promette_ascolto_come_esclusiva(self):
        """Da quando si ascolta tutti, una CTA che vende «puoi
        ascoltare» sarebbe falsa: la promessa e' comporre e pubblicare."""
        for f in ("FrequenzePage.js", "GuidaView.js", "SoundLandingPage.js"):
            src = (FQ_DIR / f).read_text()
            for bugia in ("gli operatori possono ascoltare",
                          "Vuoi ascoltarla e usarla"):
                assert bugia not in src, f"{f}: «{bugia}» non e' piu' vero"

    def test_niente_chiamate_authed_per_anonimi(self):
        """Il visitatore non deve generare 401 (bozze/voce) ne' portare
        nel DOM gli URL delle basi audio (lista suoni)."""
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        for fn in ("loadDrafts", "loadSounds", "loadVoice"):
            assert f"if (canCompose) {fn}()" in page, \
                f"{fn} deve caricare solo per chi compone"

    def test_cta_gerarchia(self):
        """1 primaria (landing) + 3 contestuali (popup, fine biblioteca,
        chiusura Guida). MAI sulle card in griglia."""
        landing = (FQ_DIR / "SoundLandingPage.js").read_text()
        assert "Vuoi andare oltre l'esplorazione?" in landing
        assert "fqz-cta-landing" in landing
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "fqz-cta-learn" in page and "fqz-cta-explore" in page
        guida = (FQ_DIR / "GuidaView.js").read_text()
        assert "fqz-cta-guida" in guida
        # la card in griglia non contiene la CTA: solo il popup (flag cta)
        card_zone = page.split("const renderCard")[1].split("const bibKeys")[0]
        assert "PRO_ENTRY" not in card_zone, \
            "la CTA non sta sulle card: 40 card = 40 pubblicita'"
        # e il flag cta si accende solo per i visitatori
        assert "cta: !canCompose" in card_zone

    def test_cta_porta_dentro_sound_non_altrove(self):
        """L'invito «per operatori» porta alla biblioteca da operatore
        (dove Ascolta e' acceso), passando dal login che offre anche la
        registrazione. Una sola verita' condivisa: links.js."""
        links = (FQ_DIR / "links.js").read_text()
        assert "/sound/esplora" in links and "/login?next=" in links, \
            "l'invito deve rientrare in Sound passando dal login"
        for f in ("FrequenzePage.js", "GuidaView.js", "SoundLandingPage.js"):
            src = (FQ_DIR / f).read_text()
            assert "PRO_ENTRY" in src, f"{f} non usa la destinazione condivisa"
            assert "/professionisti" not in src, \
                f"{f}: rotta inesistente (finiva sul catch-all → homepage)"
        # il login propaga il next anche alla registrazione, e non
        # accetta destinazioni esterne
        auth = (FRONTEND_SRC / "pages" / "AuthPages.js").read_text()
        assert "to={`/signup${searchParams.get('next')" in auth
        assert "nextAfterSignup.startsWith('//')" in auth
        # e chi e' GIA' dentro non deve finire in gestionale: PublicRoute
        # rimbalzava su /dashboard hardcoded, vincendo pure la corsa col
        # navigate della LoginPage (era il «poi mi porta a gestionale»)
        app = (FRONTEND_SRC / "App.js").read_text()
        pub = app.split("const PublicRoute")[1][:900]
        assert "get('next')" in pub and "startsWith('//')" in pub, \
            "PublicRoute deve rispettare next (solo path interni)"
        assert pub.count('to="/dashboard"') == 0, \
            "il redirect di PublicRoute non puo' essere hardcoded"

    def test_operatore_non_perde_ascolto_durante_il_login(self):
        """Il bug trovato dal founder: `user` arriva solo dopo /auth/me,
        quindi al reload l'operatore vedeva la biblioteca PUBBLICA (senza
        Ascolta) finche' la chiamata non tornava. Il token si legge
        subito e copre la finestra."""
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        riga = [l for l in page.splitlines() if "const canCompose" in l][0]
        assert "authLoading" in riga and "localStorage.getItem('token')" in riga, \
            "canCompose deve reggere anche mentre /auth/me e' in volo"

    def test_operatore_intatto(self):
        """Per chi compone il comportamento resta quello di oggi: i
        controlli esistono ancora tutti (solo condizionati)."""
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        for segno in ("'Ferma' : 'Ascolta'", "+ sessione", "Salva bozza",
                      "fqz-mine", "Gestionale"):
            assert segno in page, f"perso pezzo operatore: {segno}"

    def test_shell_e_sitemap(self):
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert '"sound"' in shell and "_meta_sound" in shell
        blocco = shell.split("async def _meta_sound")[1][:900]
        assert '"crea", "tracce"' in blocco and "noindex" in blocco, \
            "il workspace non si indicizza"
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert "/sound/esplora" in seo and "/sound/impara" in seo
        assert "/sound/crea" not in seo and "/sound/tracce" not in seo, \
            "le protette non vanno in sitemap"
        # nginx instrada /sound* alla shell (entrambe le conf di deploy)
        for conf in ("nginx.conf", "nginx-bootstrap.conf"):
            src = (BACKEND_DIR.parent / "deploy" / "nginx" / conf).read_text()
            assert "|sound)(/|$)" in src, f"{conf}: /sound non arriva alla shell"

    def test_parita_titoli_shell_biblioteca(self):
        """_SOUND_CARDS e' una copia dichiarata (Docker non vede i
        sorgenti frontend): questa guardia la tiene identica alla
        biblioteca vera, titolo per titolo."""
        import re as _re
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        bib = (FQ_DIR / "content" / "biblioteca.js").read_text()
        chunks = _re.split(r"'(Bande cerebrali|Altre frequenze|Metodi)':\[", bib)
        veri = {}
        for i in range(1, len(chunks), 2):
            titoli = _re.findall(r"\{t:'((?:[^'\\]|\\.)*)'", chunks[i + 1])
            veri[chunks[i]] = [t.replace("\\'", "'") for t in titoli]
        import ast
        dict_src = shell.split("_SOUND_CARDS = ")[1].split("\n}")[0] + "\n}"
        copiati = ast.literal_eval(dict_src)
        assert copiati == veri, (
            "la copia in seo_shell e' divergente dalla biblioteca: "
            f"{ {k: (len(v), len(veri.get(k, []))) for k, v in copiati.items()} }")

    def test_via_di_casa_dal_mondo_scuro(self):
        """SP-ter — Aurya Sound e' un mondo visivo a se' e il menu del
        sito non c'e': senza marchio in alto e uscite in fondo, chi
        arriva dal sito resta chiuso dentro."""
        for f in ("FrequenzePage.js", "SoundLandingPage.js"):
            src = (FQ_DIR / f).read_text()
            assert 'data-testid="fqz-brand"' in src and 'href="/"' in src, \
                f"{f}: manca il marchio che riporta al sito"
            assert 'data-testid="fqz-foot"' in src, \
                f"{f}: manca il piede con le uscite"
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        piede = page.split('data-testid="fqz-foot"')[1][:500]
        for dove in ("/blog", "/newsletter", "/meditazioni"):
            assert dove in piede, f"uscita {dove} mancante nel piede"


class TestTaglioRegistrazioneFv6:
    """FV6 (19/8, feedback founder) — il taglio e' una proprieta' della
    REGISTRAZIONE, decisa una volta nel leggio: nella linea del tempo la
    voce deve avere lo stesso specchietto degli altri suoni (entra a /
    esce a + effetto), niente forbici sparse per la riga."""

    def test_clamp_lascia_sempre_un_secondo(self):
        from models.voice_asset import clamp_trim
        assert clamp_trim(0, 0, 120) == (0.0, 0.0)
        assert clamp_trim(5, 10, 120) == (5.0, 10.0)
        # somma oltre la durata: la fine cede, resta 1 secondo utile
        assert clamp_trim(100, 100, 120) == (100.0, 19.0)
        # inizio oltre la durata e valori negativi
        assert clamp_trim(999, 0, 30) == (29.0, 0.0)
        assert clamp_trim(-4, -9, 60) == (0.0, 0.0)
        # durata sconosciuta: si applica solo il tetto del clip
        assert clamp_trim(9999, 0, 0) == (600.0, 0.0)

    def test_patch_separa_titolo_e_taglio(self):
        """Rinominare non azzera il taglio, tagliare non tocca il nome."""
        import inspect
        from routers import frequencies as fr
        src = inspect.getsource(fr.update_voice_clip)
        assert "if payload.title is not None" in src, \
            "il titolo non e' piu' facoltativo: rinomina e taglio sono legati"
        assert "clamp_trim(" in src, "il taglio entra senza passare dal clamp"
        assert '"trim_start"' in src and '"trim_end"' in src

    def test_riga_del_livello_come_gli_altri_suoni(self):
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        riga = src.split("const renderRow = ")[1].split("const renderLane")[0] \
            if "const renderLane" in src else src.split("const renderRow = ")[1][:6000]
        assert "✂" not in riga, "le forbici sono ancora nella riga del livello"
        assert ">parte a<" not in riga, \
            "la voce ha ancora un suo formato: deve dire entra a / esce a"
        assert riga.count(">entra a<") == 1 and riga.count(">esce a<") == 1, \
            "il blocco tempo non e' piu' uno solo per tutti i tipi di suono"

    def test_taglio_nel_leggio_e_propagato(self):
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert "togli dall'inizio" in src and "togli dalla fine" in src, \
            "il taglio non vive nelle impostazioni della registrazione"
        salva = src.split("const saveVoiceTrim")[1][:1200]
        assert "trimVoice" in salva, "il taglio non viene salvato sullo spezzone"
        assert "l.asset_id === clip.id" in salva, \
            "i livelli gia' in sessione non seguono il nuovo taglio"
        add = src.split("const addVoiceToSession")[1][:600]
        assert "clip.trim_start" in add and "clipUseful(clip)" in add, \
            "«+ sessione» non nasce gia' tagliato"

    def test_barra_ascolto_compatta_su_telefono(self):
        """I quattro campi (titolo/durata/apertura/chiusura) su telefono
        stanno dietro un tocco; salva e pubblica restano sempre a vista."""
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        assert 'data-testid="fq-setup"' in src, "manca il tasto che apre i campi"
        assert 'className="cb-collapse open"' not in src, \
            "il pannello e' di nuovo inchiodato aperto"
        bar = src.split('<div className="createbar">')[1].split("</div>\n\n")[0]
        assert bar.index('className="cb-export"') > bar.index("cb-collapse"), \
            "salva/pubblica sono finiti dentro il pannello a scomparsa"
        css = (FQ_DIR / "frequenze.css").read_text()
        assert ".fqz .cb-opt{display:none}" in css, \
            "il tasto comparirebbe anche su schermo largo"


class TestLibreriaSuoniSl:
    """SL (20/8) — la libreria di basi della piattaforma: categorie in
    parita' fra server e pagina, una riga di orientamento per ognuna,
    ordine prevedibile nelle card e un manifest che non dichiara cio'
    che l'audio non contiene."""

    def _manifest(self):
        import importlib
        return importlib.import_module("scripts.seed_sound_library_sl")

    def test_categorie_in_parita(self):
        from models.audio_asset import SOUND_CATEGORIES
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        riga = src.split("const SOUND_CATS = ")[1].split(";")[0]
        import re
        cats = re.findall(r"'([^']+)'", riga)
        assert [c.lower() for c in cats] == list(SOUND_CATEGORIES), (
            "tab della pagina e categorie del server divergono: "
            f"{cats} vs {list(SOUND_CATEGORIES)}")
        assert cats == list(SOUND_CATEGORIES.values()), \
            "le etichette dei tab non sono quelle dichiarate dal server"

    def test_ogni_categoria_ha_la_sua_riga(self):
        from models.audio_asset import SOUND_CATEGORIES
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        blocco = src.split("const SOUND_HINT = {")[1].split("};")[0]
        for label in SOUND_CATEGORIES.values():
            assert f"{label}:" in blocco, f"manca l'orientamento per {label}"
        assert 'data-testid="fq-sound-hint"' in src, \
            "la riga di orientamento non e' in pagina"

    def test_card_in_ordine(self):
        src = (FQ_DIR / "FrequenzePage.js").read_text()
        blocco = src.split("const inCat = sounds")[1][:400]
        assert ".sort(" in blocco and "localeCompare" in blocco, \
            "le basi non hanno un ordine dichiarato"
        assert "numeric: true" in blocco, \
            "senza ordinamento numerico la serie del corpo si sfalda (1, 2, 3...)"

    def test_manifest_coerente(self):
        from models.audio_asset import SOUND_CATEGORIES
        mod = self._manifest()
        titoli = [t for _, t, _, _ in mod.MANIFEST]
        assert len(titoli) == len(set(titoli)), "due basi con lo stesso titolo"
        for rel, titolo, cat, _ in mod.MANIFEST:
            assert cat in SOUND_CATEGORIES, f"{titolo}: categoria {cat} inesistente"
            assert titolo.strip() == titolo and titolo, f"titolo sporco: {titolo!r}"

    def test_nessun_hertz_dichiarato_a_vuoto(self):
        """L'analisi spettrale del 20/8 dice che i file chiamati
        «741 Hz», «285 Hz», «174 Hz» hanno i picchi altrove (220, 52,
        295 Hz). I titoli non riportano piu' quei numeri: un hertz nel
        titolo e' una dichiarazione tecnica, e va difesa come tale."""
        mod = self._manifest()
        import re
        for _, titolo, _, _ in mod.MANIFEST:
            assert not re.search(r"\d+\s*Hz", titolo, re.I), (
                f"«{titolo}» dichiara una frequenza: o e' verificata sul file, "
                "o non sta nel titolo")

    def test_licenze_mai_inventate(self):
        """Il materiale senza licenza allegata si annota come tale:
        meglio «da confermare» di un CC0 che nessuno ha verificato."""
        mod = self._manifest()
        assert "da confermare" in mod._aurya("x.wav")
        dichiarate = [n for _, _, _, n in mod.MANIFEST if n]
        assert all("CC0" in n for n in dichiarate), \
            "una licenza dichiarata senza dire quale"
