"""Ciclo ES — Economia del suono (21/8/2026).

Piano in docs/ECONOMIA_SOUND_PIANO_ES_2026-08.md. Qui si difendono le
prime due onde:

ES1 — gli audio li serve NGINX dal volume (sendfile, Range nativo),
non piu' l'unico worker Python del backend — lo stesso che serve
tutte le API: 20 download simultanei da 55MB rallentavano ordini e
dashboard.

ES4 — la vetrina /meditazioni: indice (status, published_at) al posto
di SORT+COLLSCAN, numeri materializzati alla pubblicazione al posto
dell'array dei livelli trasportato per contarlo, paginazione a cursore
al posto del to_list(500) che alla traccia 501 faceva SPARIRE le piu'
vecchie in silenzio.
"""
import os
import re
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT = BACKEND_DIR.parent

NGINX = (ROOT / "deploy" / "nginx" / "nginx.conf").read_text()
COMPOSE = (ROOT / "docker-compose.prod.yml").read_text()
FREQ = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
DB = (BACKEND_DIR / "database.py").read_text()


class TestNginxServeGliAudioEs1:
    def test_il_volume_e_montato_in_sola_lettura(self):
        assert "backend_uploads:/srv/uploads:ro" in COMPOSE, \
            "senza il volume, nginx non ha i file e /uploads muore"

    def test_uploads_e_alias_non_proxy(self):
        blocco = NGINX.split("location /uploads/")[1].split("}")[0]
        assert "alias /srv/uploads/" in blocco
        assert "proxy_pass" not in blocco, \
            "tornato il tubo verso il worker Python unico"
        assert "sendfile on" in blocco

    def test_il_freno_anti_raschiatori(self):
        """/uploads e' pubblico per necessita' (debito noto): il freno
        per IP ferma chi vuole svuotarci la banda, non l'ascoltatore."""
        assert "zone=uploads" in NGINX
        blocco = NGINX.split("location /uploads/")[1].split("}")[0]
        assert "limit_req zone=uploads" in blocco

    def test_immutable_anche_da_nginx(self):
        blocco = NGINX.split("location /uploads/")[1].split("}")[0]
        assert "immutable" in blocco

    def test_i_tipi_coprono_cio_che_vive_in_uploads(self):
        """`types` in una location SOSTITUISCE la mappa ereditata: se
        manca un'estensione davvero presente, quel file esce
        octet-stream. La voce di Chrome e' webm: non deve mancare."""
        blocco = NGINX.split("location /uploads/")[1].split("types {")[1].split("}")[0]
        for ext in ("m4a", "mp3", "webm", "webp", "jpeg", "png"):
            assert re.search(rf"\b{ext}\b", blocco), f"manca {ext}"

    def test_il_fallback_python_resta(self):
        """Il Range-shim nel backend serve il DEV (dove nginx non c'e')
        e fa da rete se mai nginx tornasse proxy."""
        srv = (BACKEND_DIR / "server.py").read_text()
        assert "_StaticsConRange" in srv


class TestVetrinaCheScalaEs4:
    def test_l_indice_esiste(self):
        assert 'name="es4_catalog"' in DB
        assert '[("status", 1), ("published_at", -1)]' in DB

    def test_il_piano_di_query_usa_l_indice(self):
        """Non la dichiarazione: il PIANO. Prima era SORT+COLLSCAN."""
        try:
            from pymongo import MongoClient
            db = MongoClient("mongodb://localhost:27017",
                             serverSelectionTimeoutMS=2000)["retreat_dev"]
            pl = db.frequency_tracks.find({"status": "published"}) \
                .sort("published_at", -1).explain()
        except Exception:
            pytest.skip("Mongo non raggiungibile")
        assert "COLLSCAN" not in str(pl["queryPlanner"]["winningPlan"]), \
            "la vetrina e' tornata a scandire l'intera collezione"

    def test_la_pubblicazione_materializza_i_numeri(self):
        blocco = FREQ.split("def publish_track")[1][:1400]
        assert '"layers_count": len(score.get("layers")' in blocco
        assert '"duration_sec": score.get("duration_sec")' in blocco

    def test_il_catalogo_non_trasporta_i_livelli(self):
        proiezione = FREQ.split("_CATALOG_PROJECTION = ")[1].split("}")[0]
        assert "score.layers" not in proiezione, \
            "si ritrasporta l'array dei livelli solo per contarlo"

    def test_niente_piu_tetto_muto_a_500(self):
        blocco = FREQ.split("async def catalog(request")[1].split("async def ")[0]
        codice = "\n".join(r for r in blocco.splitlines()
                           if not r.strip().startswith("#"))
        assert "to_list(500)" not in codice
        assert ".to_list(limit)" in codice and "next_before" in codice

    def test_il_cursore_diventa_datetime(self):
        """published_at in Mongo e' un datetime: un $lt con la stringa
        del client confronterebbe tipi BSON diversi e non troverebbe
        MAI niente — vetrina vuota a pagina due, senza errori."""
        blocco = FREQ.split("async def catalog(request")[1].split("async def ")[0]
        assert "datetime.fromisoformat" in blocco

    def test_paginazione_dal_vivo(self):
        """Due pagine da 1: titoli diversi, cursore che avanza, e
        NIENTE score nel payload."""
        env = (BACKEND_DIR / ".env")
        if not env.exists():
            pytest.skip("niente .env locale")
        m = re.search(r'^JWT_SECRET_KEY\s*=\s*"?([^"\n]+)"?', env.read_text(), re.M)
        if not m:
            pytest.skip("JWT_SECRET_KEY non in .env")
        # conftest.py inietta un segreto FINTO per tutta la suite:
        # importare generate_subscriber_token qui firmerebbe col falso
        # e il server direbbe 403. Si firma a mano col segreto vero,
        # leggendo scope e algoritmo dal modulo (una verita' sola).
        import time
        import jwt as pyjwt
        mod = (BACKEND_DIR / "core" / "subscriber_token.py").read_text()
        scope = re.search(r'_SCOPE\s*=\s*"([^"]+)"', mod).group(1)
        alg = re.search(r'_ALGORITHM\s*=\s*"([^"]+)"', mod).group(1)
        adesso = int(time.time())
        tok = pyjwt.encode(
            {"scope": scope, "email": "davidone@demo.com",
             "iat": adesso, "exp": adesso + 3600},
            m.group(1), algorithm=alg)
        h = {"X-Fqz-Unlock": tok}
        r1 = requests.get(f"{BASE_URL}/api/frequencies/catalog?limit=1",
                          headers=h, timeout=10)
        if r1.status_code == 403:
            pytest.skip("sblocco non accettato in questo ambiente")
        d1 = r1.json()
        if not d1.get("items"):
            pytest.skip("nessuna traccia pubblicata nell'ambiente")
        assert "score" not in d1["items"][0]
        nb = d1.get("next_before")
        if not nb:
            return   # una sola traccia: il cursore giustamente manca
        r2 = requests.get(
            f"{BASE_URL}/api/frequencies/catalog?limit=1&before={nb}",
            headers=h, timeout=10)
        d2 = r2.json()
        assert d2["items"], "pagina due vuota: il cursore non funziona"
        assert d2["items"][0]["slug"] != d1["items"][0]["slug"]


FQ_DIR = ROOT / "frontend" / "src" / "features" / "frequenze"
ASSETS = (FQ_DIR / "engine" / "assets.js").read_text()
ANELLO = (FQ_DIR / "engine" / "anello.js").read_text()
PAGE = (FQ_DIR / "FrequenzePage.js").read_text()


class TestSpezzoneEs3:
    """
    ES3 — «lo spezzone». Misurato: una base ambient da 45 min
    decodificata occupa 908 MB di RAM (x11 rispetto al file), e in
    libreria 9 basi ambient su 18 sono lunghe: il muro non e' un caso
    limite, e' la strada normale di chi compone.

    Rimedio: di una base usata come TAPPETO si chiede solo il primo
    spezzone (Range HTTP) e lo si chiude in anello con la dissolvenza.
    Misurato dopo: 69 MB e 1,5 s al posto di 908 MB e 4,9 s.
    """

    def test_il_criterio_e_il_flag_loop_non_un_indovinello(self):
        """Un brano che EVOLVE (loop:false) si scarica intero: e' una
        scelta dell'operatore, non un caso da ottimizzare."""
        assert "l.loop !== false ? { asset } : null" in ASSETS

    def test_lo_spezzone_si_calcola_dai_metadati(self):
        """size/durata = bitrate medio reale della base: niente
        indovinelli, e se i metadati mancano si torna al file intero."""
        blocco = ASSETS.split("function bytesSpezzone")[1][:400]
        assert "size / dur" in blocco
        assert "return null" in blocco, "senza metadati deve tornare al file intero"

    def test_sotto_i_cinque_minuti_non_si_tocca_niente(self):
        """Dove non c'e' problema non si cambia comportamento."""
        assert "SOGLIA_LUNGA_SEC = 300" in ASSETS
        assert "dur <= SOGLIA_LUNGA_SEC) return null" in ASSETS

    def test_il_206_e_la_condizione_per_tagliare(self):
        """Se il server IGNORA il Range risponde 200 col file intero:
        chiuderlo in anello taglierebbe un brano di 45 minuti a 3.
        Solo un 206 autorizza il ritaglio."""
        assert "r.status === 206" in ASSETS
        assert "parziale ? anelloDaBuffer(ctx, buf) : buf" in ASSETS

    def test_la_dissolvenza_e_la_stessa_dell_anello(self):
        """Due materie diverse (PCM Int16 del render, AudioBuffer del
        file) ma UNA curva: se un giorno va cambiata, va cambiata per
        tutt'e due."""
        assert "export function anelloDaBuffer" in ANELLO
        curve = [b for b in ANELLO.split("0.5 * (1 + Math.cos((Math.PI * i) / x))")]
        assert len(curve) == 3, "le due dissolvenze non usano piu' la stessa curva"

    def test_si_scarta_la_coda_prima_di_incrociare(self):
        """Un troncamento a meta' frame lascia spesso silenzio o sporco
        negli ultimi decimi: incrociarci sopra li stamperebbe nel giro."""
        blocco = ANELLO.split("export function anelloDaBuffer")[1][:600]
        assert "coda = 0.5" in blocco
        assert "buffer.duration - coda" in blocco

    def test_lo_sfratto_ragiona_sull_url_nudo(self):
        """La chiave di cache ora puo' portare #tappeto: confrontare la
        CHIAVE con gli URL in uso sfratterebbe proprio le basi in
        ascolto."""
        blocco = ASSETS.split("function sfoltisci")[1][:500]
        assert "chiave.split('#')[0]" in blocco

    def test_la_stessa_base_puo_servire_intera_e_a_spezzone(self):
        assert "`${url}#tappeto`" in ASSETS

    def test_la_stima_di_memoria_e_in_crea(self):
        """L'operatore deve sapere cosa sta costruendo PRIMA di
        pubblicarlo, non scoprirlo dai telefoni di chi ascolta."""
        assert "export function memoriaStimataMB" in ASSETS
        assert 'data-testid="fq-stima-memoria"' in PAGE
        blocco = PAGE.split('data-testid="fq-stima-memoria"')[0][-500:]
        assert "mb < 350) return null" in blocco, \
            "un avviso che compare sempre non lo legge piu' nessuno"

    def test_la_stima_conosce_lo_spezzone(self):
        """Se stimasse la durata intera per i tappeti, griderebbe al
        lupo su sessioni che ormai pesano un decimo."""
        blocco = ASSETS.split("export function memoriaStimataMB")[1][:700]
        assert "SPEZZONE_SEC" in blocco and "l.loop !== false" in blocco


SCRIPT_ES2 = (ROOT / "scripts" / "comprimi_basi_non_compresse.py").read_text()
VOICE_MODEL = (BACKEND_DIR / "models" / "voice_asset.py").read_text()


class TestBasiCompresseEs2:
    def test_lo_script_aggiorna_prima_di_cancellare(self):
        """Se il processo muore in mezzo deve restare un file orfano
        (innocuo), non un asset che punta al nulla (base muta)."""
        corpo = SCRIPT_ES2.split("_ricodifica(vecchio, nuovo)")[1]
        i_doc = corpo.index("update_one")
        i_del = corpo.index("vecchio.unlink()")
        assert i_doc < i_del

    def test_lo_script_cambia_estensione_quindi_indirizzo(self):
        """I file sono serviti `immutable` per un anno: sostituire i
        byte sotto lo STESSO url darebbe a meta' utenti la versione
        vecchia per mesi. Cambiando estensione cambia l'indirizzo."""
        assert 'with_suffix(".m4a")' in SCRIPT_ES2
        assert '"mime": "audio/mp4"' in SCRIPT_ES2

    def test_lo_script_non_esegue_per_sbaglio(self):
        """Tocca file e documenti: senza --esegui deve solo elencare."""
        assert '"--esegui", action="store_true"' in SCRIPT_ES2
        assert "if not esegui:" in SCRIPT_ES2

    def test_niente_basi_non_compresse_in_libreria(self):
        """Guardia viva: una base sopra gli 800 kbps e' un difetto di
        ingestione (5 MB per 30 secondi), non una scelta di qualita'."""
        try:
            from pymongo import MongoClient
            db = MongoClient("mongodb://localhost:27017",
                             serverSelectionTimeoutMS=2000)["retreat_dev"]
            assets = list(db.audio_assets.find(
                {}, {"title": 1, "size_bytes": 1, "duration_sec": 1}))
        except Exception:
            pytest.skip("Mongo non raggiungibile")
        colpevoli = [a.get("title") for a in assets
                     if a.get("duration_sec") and a.get("size_bytes")
                     and a["size_bytes"] * 8 / 1000 / a["duration_sec"] > 800]
        assert not colpevoli, (
            f"basi non compresse in libreria: {colpevoli} — "
            "scripts/comprimi_basi_non_compresse.py --esegui")


class TestQuotaVoceEs5:
    """ES5 era GIA' fatto: il piano diceva il falso, e non l'avevo
    verificato prima di scriverlo. Questi assert lo fissano, cosi' la
    prossima analisi parte da un fatto e non da un ricordo."""

    def test_i_tetti_esistono(self):
        for nome in ("CLIP_MAX_SECONDS", "CLIP_MAX_BYTES",
                     "ORG_QUOTA_BYTES", "CLIPS_MAX_PER_ORG"):
            assert f"{nome} = " in VOICE_MODEL, f"sparito il tetto {nome}"

    def test_la_quota_e_APPLICATA_non_solo_dichiarata(self):
        """Un tetto che nessuno controlla non e' un tetto."""
        assert "used + len(data) > ORG_QUOTA_BYTES" in FREQ
        assert "len(existing) >= CLIPS_MAX_PER_ORG" in FREQ
