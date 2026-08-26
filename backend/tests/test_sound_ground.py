"""GROUND — la seconda esperienza di Aurya Sound (STEP 9, 26/8/2026).

I numeri qui sotto sono la SPECIFICA APPROVATA dal founder, non una
preferenza: se cambiano, e' una decisione — e allora si cambiano anche
qui, con lui. La prova che valgono davvero l'ha data il banco: il
motore vero eseguito sullo score (nessun clipping, picco 0,45,
transizioni senza salti, materia 9 dB sotto il peso).

Il resto verifica che GROUND sia arrivato SENZA portarsi dietro un
secondo player, un secondo metodo audio o una copia della pagina.
"""
import re
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ = FRONTEND_SRC / "features" / "frequenze"
GROUND = FQ / "content" / "ground.js"
REGISTRO = FQ / "content" / "esperienze.js"
PAGINA = FQ / "esperienze" / "EsperienzaPage.js"
ASCOLTO = FQ / "esperienze" / "ascolto.js"


def _codice(p: Path) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", p.read_text(), flags=re.S)


def _prosa(p: Path) -> str:
    t = " ".join(p.read_text().split())
    return t.replace("' + '", "").replace('" + "', "")


def _layers(js: str):
    """I livelli scritti nel protocollo, come dizionari.

    I tempi sono scritti una volta sola in GROUND_TEMPI e richiamati
    per nome (`start: T.materiaDa`): qui si risolvono, altrimenti si
    leggerebbe None dove c'e' un numero."""
    tempi = {k: float(v) for k, v in
             re.findall(r"(\w+):\s*(\d+)", js.split("_TEMPI")[1].split("}")[0])} \
        if "_TEMPI" in js else {}
    fuori = []
    for b in re.findall(r"layer\(\{(.*?)\}\)", js, re.S):
        d = {}
        for k, v in re.findall(r"(\w+):\s*'([^']*)'", b):
            d[k] = v
        for k, v in re.findall(r"(\w+):\s*(-?[\d.]+)\b", b):
            d[k] = float(v)
        for k, rif in re.findall(r"(\w+):\s*T\.(\w+)", b):
            if rif in tempi:
                d[k] = tempi[rif]
        if "end" not in d and "end: d" in b:
            d["end"] = None            # «fino in fondo»
        fuori.append(d)
    return fuori


class TestLoScoreApprovato:
    """La specifica, numero per numero."""

    def test_dura_otto_minuti(self):
        src = _codice(GROUND)
        assert "GROUND_DURATA = 480" in src
        assert "GROUND_FADE_IN = 16" in src and "GROUND_FADE_OUT = 30" in src

    def test_quattro_livelli_e_i_loro_numeri(self):
        atteso = [
            {"name": "Peso", "method": "drone", "carrier": 73.42, "gain": 0.26,
             "start": 0, "end": None},
            {"name": "Materia", "method": "noise", "color": "brown",
             "f0": 0.09, "f1": 0.06, "curve": "exp", "gain": 0.07,
             "start": 60, "end": 340},
            {"name": "Pulsazione", "method": "iso", "carrier": 146.83,
             "f0": 0.55, "f1": 0.40, "curve": "exp", "gain": 0.16,
             "start": 150, "end": 400},
            {"name": "Apertura", "method": "bil", "carrier": 220.25,
             "f0": 0.12, "f1": 0.12, "gain": 0.13, "start": 330, "end": 420},
        ]
        letti = _layers(_codice(GROUND))
        assert len(letti) == 4, f"letti {len(letti)} livelli invece di 4"
        for att, vero in zip(atteso, letti):
            for campo, valore in att.items():
                if valore is None:
                    continue
                assert vero.get(campo) == valore, \
                    (f"{att['name']}: {campo} = {vero.get(campo)} "
                     f"invece di {valore}")

    def test_le_portanti_sono_la_stessa_serie_armonica(self):
        """73,42 · ×2 · ×3 — la nota, la sua ottava, la sua dodicesima.
        Non aggiungono note: fondono in un corpo solo."""
        p = [l["carrier"] for l in _layers(_codice(GROUND)) if "carrier" in l]
        assert sorted(p) == [73.42, 146.83, 220.25]
        assert abs(146.83 / 73.42 - 2) < 0.001
        assert abs(220.25 / 73.42 - 3) < 0.001

    def test_le_cinque_fasi(self):
        src = _codice(GROUND)
        for t, nome in ((0, 'arrivo'), (60, 'peso'), (150, 'stabilità'),
                        (330, 'apertura'), (420, 'congedo')):
            assert f"{{ t: {t}, name: '{nome}' }}" in src, \
                f"fase {nome} spostata o rinominata"

    def test_la_sottrazione_e_il_progetto(self):
        """GROUND si semplifica: la materia esce prima della pulsazione,
        la pulsazione prima dell'apertura, e l'ultimo minuto e' solo
        peso. E' cio' che lo distingue da CALM, che invece aggiunge."""
        src = _codice(GROUND)
        assert "materiaDa: 60, materiaA: 340" in src
        assert "pulsazioneDa: 150, pulsazioneA: 400" in src
        assert "aperturaDa: 330, aperturaA: 420" in src
        assert 420 < 480, "manca l'ultimo minuto di solo peso"

    def test_niente_di_piu(self):
        """Nessun elemento aggiunto «perche' e' olistico», e nessuno
        dei metodi che il progetto ha ESCLUSO con una ragione."""
        src = _codice(GROUND)
        for vietato in ("'bin'", "'shepard'", "'breath'", "'tone'", "'mono'",
                        "432", "528"):
            assert vietato not in src, f"GROUND ha guadagnato {vietato}"


class TestContrattoDelProtocollo:
    """Gli stessi limiti degli score degli operatori. La fonte della
    verita' resta UNA: il validatore del server."""

    def test_ogni_livello_passa_il_validatore_senza_essere_corretto(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.frequency_track import clean_layer, DURATION_MIN, DURATION_MAX

        js = _codice(GROUND)
        durata = float(re.search(r"GROUND_DURATA = (\d+)", js).group(1))
        assert DURATION_MIN <= durata <= DURATION_MAX
        for l in _layers(js):
            grezzo = dict(l)
            if grezzo.get("end") is None:
                grezzo["end"] = durata        # «fino in fondo»
            pulito = clean_layer(grezzo, durata)
            assert pulito is not None, f"{l.get('name')}: rifiutato dal contratto"
            for campo in ("carrier", "f0", "f1", "gain", "start", "end"):
                if l.get(campo) is None:      # «fino in fondo»: lo mette il motore
                    continue
                assert abs(pulito[campo] - l[campo]) < 0.01, \
                    (f"{l.get('name')}: {campo} = {l[campo]} riportato a "
                     f"{pulito[campo]} dal contratto")
            # il colore vale solo per il soffio, e dev'essere quello scelto
            if l["method"] == "noise":
                assert pulito["color"] == "brown"

    def test_lo_score_intero_e_accettato(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.frequency_track import clean_score

        js = _codice(GROUND)
        durata = float(re.search(r"GROUND_DURATA = (\d+)", js).group(1))
        fasi = [{"t": float(t), "name": n}
                for t, n in re.findall(r"\{ t: (\d+), name: '([^']+)' \}", js)]
        score = {
            "score_version": 1, "duration_sec": durata,
            "fade_in_sec": 16.0, "fade_out_sec": 30.0,
            "layers": [{**l, "end": (l["end"] if l.get("end") is not None else durata)}
                       for l in _layers(js)],
            "phases": fasi,
        }
        pulito = clean_score(score)
        assert pulito is not None, "lo score di GROUND non e' valido"
        assert len(pulito["layers"]) == 4 and len(pulito["phases"]) == 5
        assert pulito["duration_sec"] == 480


class TestNienteDuplicati:
    """GROUND non doveva portarsi dietro nulla."""

    def test_una_sola_porta_per_tutte_le_esperienze(self):
        assert not (FQ / "calm").exists(), "e' rimasta una pagina di CALM"
        assert not (FQ / "ground").exists(), "e' nata una pagina di GROUND"
        pagine = list((FQ / "esperienze").glob("*Page.js"))
        assert len(pagine) == 1, f"piu' di una presentazione: {pagine}"
        src = _codice(PAGINA)
        assert "esperienza(id)" in src, "la porta non e' guidata dal registro"
        for nome in ("CALM", "GROUND", "calm", "ground"):
            assert f"'{nome}'" not in src, \
                f"la porta conosce «{nome}»: dovrebbe saperlo solo il registro"

    def test_un_solo_player(self):
        assert (ASCOLTO).exists()
        altri = [f for f in (FQ / "esperienze").glob("*.js")
                 if f.name not in ("ascolto.js",) and "startPreview" in f.read_text()]
        assert not altri, f"un secondo player: {altri}"

    def test_nessun_metodo_audio_nuovo(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.frequency_track import METHODS
        usati = {l["method"] for l in _layers(_codice(GROUND))}
        assert usati <= set(METHODS), f"metodi fuori contratto: {usati - set(METHODS)}"

    def test_il_motore_e_il_lab_sono_intatti(self):
        """Attenzione alla trappola: «ground» sta dentro «background»
        e «foreground». Si cercano i RIFERIMENTI veri all'esperienza."""
        segni = ("GROUND", "costruisciGround", "content/ground", "'ground'")
        for f in list((FQ / "engine").glob("*.js")) + list((FQ / "lab").glob("*.js*")):
            testo = f.read_text()
            for segno in segni:
                assert segno not in testo, f"{f.name} sa di GROUND ({segno})"

    def test_calm_e_rimasta_quella(self):
        """Il consolidamento non doveva cambiare CALM: stessi numeri,
        stessi testi."""
        calm = _codice(FQ / "content" / "calm.js")
        assert "CALM_DURATA = 360" in calm
        for pezzo in ("carrier: 110", "carrier: 220", "carrier: 330"):
            assert pezzo in calm
        reg = _prosa(REGISTRO)
        assert "Una breve esperienza sonora per creare uno spazio di calma." in reg
        assert "battito lento fra i due canali" in reg


class TestLaPromessa:
    """GROUND racconta cosa si sente, non cosa succede nel corpo."""

    @pytest.mark.parametrize("bugia", [
        "sistema nervoso", "cortisolo", "trauma", "guarisc", "riequilibr",
        "chakra", "terapeutic", "curativ", "delta", "scientificamente",
    ])
    def test_nessuna_affermazione_fisiologica(self, bugia):
        for f in (GROUND, REGISTRO, PAGINA):
            assert bugia not in f.read_text().lower(), f"{f.name}: promette «{bugia}»"

    def test_le_cuffie_sono_dette_per_quello_che_sono(self):
        """GROUND dipende dal registro basso: dire che «resta intera»
        senza cuffie sarebbe falso — le tre portanti stanno tutte sotto
        la soglia dell'altoparlante del telefono."""
        reg = _prosa(REGISTRO)
        assert "le cuffie contano davvero" in reg.lower()
        assert "non riesce a riprodurre" in reg or "non riproduce" in reg
        # e l'avviso vero lo calcola il motore, non un'etichetta
        assert "avvisoCuffieScore" in _codice(ASCOLTO)


class TestLaPorta:
    def test_rotta_lazy_prima_del_catchall(self):
        src = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/sound/ground"' in src
        assert src.index('path="/sound/ground"') < src.index('path="/sound/*"')
        assert '<EsperienzaPage id="ground" />' in src

    @pytest.mark.asyncio
    async def test_la_shell_conosce_ground(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from routers import seo_shell as shell
        meta = await shell.resolve_meta("/sound/ground")
        assert meta is not None, "la shell non conosce /sound/ground: 404"
        assert not meta.get("noindex")
        assert meta["canonical"].endswith("/sound/ground")
        corpo = meta.get("content_html", "").lower()
        assert "peso" in corpo and "cuffie" in corpo
        for bugia in ("cortisolo", "theta", "guarisce"):
            assert bugia not in corpo

    def test_sitemap_e_registro(self):
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert "/sound/ground" in seo
        reg = _codice(REGISTRO)
        assert "ground: {" in reg and "costruisci: costruisciGround" in reg
        landing = (FQ / "SoundLandingPage.js").read_text()
        assert "ELENCO.map" in landing, \
            "la landing non elenca le esperienze dal registro"

    def test_niente_tecnicismi_davanti_all_utente(self):
        testo = _prosa(REGISTRO) + _prosa(PAGINA)
        for tecnico in ("Hz", "FFT", "sweep", "binaurale", "portante",
                        "isocronico", "bilaterale"):
            assert tecnico not in testo, f"si mostra «{tecnico}» all'utente"
