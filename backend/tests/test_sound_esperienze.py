"""IL CONTRATTO DELLE ESPERIENZE INTEGRATE (26/8/2026).

Queste guardie non parlano di CALM ne' di GROUND: parlano del
REGISTRO. Ogni esperienza che qualcuno vi aggiungera' passa da qui,
senza che nessuno debba ricordarsi di scrivere il suo file di test —
ed e' esattamente la lacuna che l'audit aveva trovato: il contratto
veniva verificato solo nei due file individuali, quindi una terza
esperienza sarebbe entrata con portanti, battiti, gain, metodi e curve
NON verificati.

LA FONTE DELLA VERITA' RESTA UNA: il validatore del server
(`models.frequency_track`). Qui non si riscrivono le regole — si
estraggono i numeri dal protocollo e si passano al validatore vero. Se
un valore fosse fuori range il validatore lo riporterebbe dentro, e la
differenza fra cio' che abbiamo scritto e cio' che il contratto
accetta E' il difetto.
"""
import re
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ = FRONTEND_SRC / "features" / "frequenze"
REGISTRO = FQ / "content" / "esperienze.js"

# il tetto di casa: un'esperienza integrata non supera i 10 minuti
TETTO_SEC = 600


def _codice(p: Path) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", p.read_text(), flags=re.S)


def _registrate():
    """Gli id elencati nel registro, con il loro file di protocollo."""
    ids = re.findall(r"^  (\w+): \{", _codice(REGISTRO), re.M)
    return [(i, FQ / "content" / f"{i}.js") for i in ids]


def _score_di(protocollo: Path):
    """Lo score scritto in un protocollo, come dizionario.

    I numeri si leggono dal file: cosi' la guardia misura cio' che il
    prodotto suonera' davvero, non una copia scritta a mano nel test.
    """
    js = _codice(protocollo)
    durata = float(re.search(r"_DURATA = (\d+)", js).group(1))
    tempi = {}
    if "_TEMPI" in js:
        tempi = {k: float(v) for k, v in
                 re.findall(r"(\w+):\s*(\d+)", js.split("_TEMPI")[1].split("}")[0])}
    layers = []
    for b in re.findall(r"layer\(\{(.*?)\}\)", js, re.S):
        d = {}
        for k, v in re.findall(r"(\w+):\s*'([^']*)'", b):
            d[k] = v
        for k, v in re.findall(r"(\w+):\s*(-?[\d.]+)\b", b):
            d[k] = float(v)
        for k, rif in re.findall(r"(\w+):\s*T\.(\w+)", b):
            if rif in tempi:
                d[k] = tempi[rif]
        # `alMinuto(8)` e' un ritmo espresso in cicli al minuto
        for k, v in re.findall(r"(\w+):\s*alMinuto\(([\d.]+)\)", b):
            d[k] = float(v) / 60.0
        if "end" not in d and "end: d" in b:
            d["end"] = durata            # «fino in fondo»
        layers.append(d)
    fasi = [{"t": float(t), "name": n}
            for t, n in re.findall(r"\{ t: (\d+), name: '([^']+)' \}", js)]
    fade_in = re.search(r"_FADE_IN = (\d+)", js)
    fade_out = re.search(r"_FADE_OUT = (\d+)", js)
    return {
        "score_version": 1,
        "duration_sec": durata,
        "fade_in_sec": float(fade_in.group(1)) if fade_in else 0.0,
        "fade_out_sec": float(fade_out.group(1)) if fade_out else 0.0,
        "layers": layers,
        "phases": fasi,
    }


def _ids():
    return [i for i, _ in _registrate()]


class TestOgniEsperienzaRegistrata:
    """Vale per quelle di oggi e per quelle che verranno."""

    def test_il_registro_non_e_vuoto(self):
        assert _ids(), "il registro non elenca nessuna esperienza"

    @pytest.mark.parametrize("eid", _ids())
    def test_ha_un_protocollo(self, eid):
        _, protocollo = next(x for x in _registrate() if x[0] == eid)
        assert protocollo.exists(), \
            f"{eid}: registrata ma senza protocollo in content/{eid}.js"
        js = _codice(protocollo)
        assert "duration_sec:" in js and "layers:" in js, \
            f"{eid}: il protocollo non ha la forma di uno score"

    @pytest.mark.parametrize("eid", _ids())
    def test_sta_sotto_il_tetto_di_casa(self, eid):
        _, protocollo = next(x for x in _registrate() if x[0] == eid)
        durata = _score_di(protocollo)["duration_sec"]
        assert durata <= TETTO_SEC, \
            f"{eid}: dura {durata}s — le esperienze integrate stanno sotto i 10 minuti"

    @pytest.mark.parametrize("eid", _ids())
    def test_lo_score_e_accettato_dal_contratto(self, eid):
        """Il validatore DEL SERVER, non una sua copia."""
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.frequency_track import clean_score, LAYERS_MAX, PHASES_MAX

        _, protocollo = next(x for x in _registrate() if x[0] == eid)
        score = _score_di(protocollo)
        pulito = clean_score(score)
        assert pulito is not None, f"{eid}: lo score non e' uno score valido"
        assert len(pulito["layers"]) == len(score["layers"]), \
            f"{eid}: il contratto ha scartato un livello"
        assert len(pulito["layers"]) <= LAYERS_MAX
        assert len(pulito["phases"]) == len(score["phases"]) <= PHASES_MAX
        assert pulito["duration_sec"] == score["duration_sec"]

    @pytest.mark.parametrize("eid", _ids())
    def test_nessun_valore_viene_riportato_nel_range(self, eid):
        """Il validatore corregge i valori fuori range invece di
        rifiutarli: se ha dovuto correggere qualcosa, quel qualcosa era
        fuori contratto — portante, battito, guadagno o finestra."""
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.frequency_track import clean_layer

        _, protocollo = next(x for x in _registrate() if x[0] == eid)
        score = _score_di(protocollo)
        for l in score["layers"]:
            pulito = clean_layer(dict(l), score["duration_sec"])
            assert pulito is not None, \
                f"{eid}/{l.get('name')}: metodo o struttura fuori contratto"
            for campo in ("carrier", "f0", "f1", "gain", "start", "end"):
                if l.get(campo) is None:
                    continue
                assert abs(pulito[campo] - l[campo]) < 0.01, \
                    (f"{eid}/{l.get('name')}: {campo} = {l[campo]} riportato a "
                     f"{pulito[campo]} dal contratto")

    @pytest.mark.parametrize("eid", _ids())
    def test_metodi_e_curve_esistono(self, eid):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.frequency_track import METHODS, CURVES

        _, protocollo = next(x for x in _registrate() if x[0] == eid)
        for l in _score_di(protocollo)["layers"]:
            assert l["method"] in METHODS, \
                f"{eid}: metodo inesistente «{l['method']}»"
            assert l.get("curve", "lin") in CURVES, \
                f"{eid}: curva inesistente «{l.get('curve')}»"


class TestLaPromessaValePerTutte:
    """Nessuna esperienza puo' introdurre un claim, nemmeno la terza."""

    @pytest.mark.parametrize("bugia", [
        "sistema nervoso", "cortisolo", "trauma", "guarisc", "riequilibr",
        "chakra", "terapeutic", "curativ", "scientificamente", "biorisonanza",
    ])
    def test_nessuna_affermazione_fisiologica(self, bugia):
        sorgenti = [REGISTRO, FQ / "esperienze" / "EsperienzaPage.js"]
        sorgenti += [p for _, p in _registrate() if p.exists()]
        for f in sorgenti:
            assert bugia not in f.read_text().lower(), f"{f.name}: promette «{bugia}»"


class TestLaPorta:
    """Le cose che l'audit ha chiesto di chiudere (P1)."""

    def test_le_cuffie_si_dicono_una_volta_sola(self):
        """Prima di partire il testo dell'esperienza le nomina UNA
        volta: il dettaglio per i telefoni lo dicono gia' la riga di
        sicurezza e l'avviso di sistema. Dirlo tre volte era un muro."""
        reg = " ".join(REGISTRO.read_text().split()).replace("' + '", "")
        for pezzo in re.findall(r"cuffie: '([^']*(?:' \+ '[^']*)*)'", reg):
            frasi = [f for f in pezzo.split('.') if f.strip()]
            assert len(frasi) <= 1, \
                f"la riga sulle cuffie ha {len(frasi)} frasi: «{pezzo}»"

    def test_la_durata_si_sa_prima_di_entrare(self):
        pagina = _codice(FQ / "esperienze" / "EsperienzaPage.js")
        assert 'data-testid="esp-durata"' in pagina
        assert "Math.round(exp.durata / 60)" in pagina, \
            "la durata non viene dal registro"

    def test_il_doppio_tocco_non_apre_due_sessioni(self):
        """P0 misurato: due tocchi rapidi facevano partire due
        sessioni, e la prima restava a suonare senza che nessuno
        potesse fermarla (picco 0,32 invece di 0,08)."""
        asc = _codice(FQ / "esperienze" / "ascolto.js")
        assert "if (live || avviando) return;" in asc
        assert "avviando = true;" in asc
        # la bandierina si rialza SEMPRE, anche se qualcosa esplode
        assert "} finally {" in asc and "avviando = false;" in asc
        # e si chiude PRIMA di qualsiasi attesa
        blocco = asc.split("async avvia()")[1][:400]
        assert blocco.index("avviando = true;") < blocco.index("await")
