"""Sound Professional S3 — il rito della sessione (26/8/2026).

Il principio sotto guardia: il rito ORCHESTRA E REGISTRA, non suona —
chi suona è il player condiviso delle esperienze (creaAscolto), lo
stesso di CALM e GROUND. E gli esiti sono onesti: una strada per
completata, una per interrotta, una per persa — quest'ultima chiusa
sul server nel momento stesso in cui il contesto muore, senza fidarsi
del fatto che l'operatore torni.
"""
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
PRO = FRONTEND_SRC / "features" / "frequenze" / "pro"
RITO = PRO / "Rito.jsx"
PAGINA = PRO / "SoundProPage.jsx"
API = FRONTEND_SRC / "api" / "soundPro.js"


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


class TestIlRitoNonSuona:
    def test_01_solo_il_player_condiviso(self):
        """Un player nuovo sarebbe la duplicazione che il consolidamento
        di agosto ha appena tolto: il rito importa creaAscolto e basta."""
        src = _senza_commenti(RITO.read_text())
        assert "creaAscolto" in src
        assert "from '../esperienze/ascolto'" in src
        basso = src.lower()
        for vietato in ("startpreview", "audiocontext", "creaponte",
                        "new audio", "media session", "engine/synth",
                        "requestanimationframe", "canvas"):
            assert vietato not in basso, f"il rito contiene «{vietato}»"
        assert "../engine" not in src, "il rito parla col motore direttamente"

    def test_02_la_pagina_continua_a_non_toccare_l_audio(self):
        """La separazione di S1 regge anche col rito: la pagina importa
        Rito, non il player."""
        src = _senza_commenti(PAGINA.read_text()).lower()
        for vietato in ("creaascolto", "esperienze/ascolto",
                        "startpreview", "audiocontext"):
            assert vietato not in src, f"la pagina importa «{vietato}»"
        assert "from './rito'" in src

    def test_03_niente_compilatore_nel_rito(self):
        """Il rito ESEGUE: core = score del catalogo (git), operatore =
        score del server. Compilare qui sarebbe una terza verità."""
        src = _senza_commenti(RITO.read_text())
        assert "compila" not in src
        assert "clean_score" not in src

    def test_04_sipario_e_cuffie_di_casa(self):
        src = _senza_commenti(RITO.read_text())
        assert "useSafetyGate" in src and "guard(" in src, \
            "l'avvio non passa dal sipario"
        assert "{curtain}" in src
        # l'avviso cuffie è QUELLO del player (ascolto.avviso), non
        # una soglia ricalcolata
        assert ".avviso" in src
        assert "SOGLIA" not in src and "500" not in src


class TestGliEsitiOnesti:
    def test_05_tre_strade_tre_esiti(self):
        src = _senza_commenti(RITO.read_text())
        assert "onFine: () => { setEsito('completata')" in src
        assert re.search(r"const termina = \(\) => \{[^}]*setEsito\('interrotta'\)",
                         src, re.S), "Termina non chiude come interrotta"
        assert "setEsito('persa')" in src

    def test_06_la_persa_si_chiude_subito_sul_server(self):
        """onPerso non aspetta l'operatore: chiude la sessione nel
        momento in cui il contesto muore — il registro non dipende dal
        fatto che qualcuno torni a premere un pulsante."""
        src = _senza_commenti(RITO.read_text())
        blocco = src[src.find("onPerso:"):]
        blocco = blocco[:blocco.find("});") + 3]
        assert "sessioni.chiudi" in blocco
        assert "'persa'" in blocco
        # e il vissuto arriva dopo, con l'aggiornamento (non una
        # seconda chiusura, che il server rifiuterebbe)
        assert "sessioni.aggiorna" in src

    def test_07_prima_il_suono_poi_il_server(self):
        """avvia() dentro il gesto, la registrazione subito dopo; se il
        server rifiuta si spegne tutto e si dice perché."""
        src = _senza_commenti(RITO.read_text())
        corpo = src[src.find("const avvia = async"):]
        corpo = corpo[:corpo.find("const avviaGuardato")]
        suono = corpo.find("await a.avvia()")
        server = corpo.find("sessioni.apri")
        assert -1 < suono < server, "il server prima del gesto audio"
        assert "a.ferma()" in corpo, "il rifiuto del server non spegne il suono"

    def test_08_ascolto_dichiarato_dal_ticker_del_player(self):
        src = _senza_commenti(RITO.read_text())
        assert "onTic" in src and "ascoltatoRef" in src
        assert src.count("ascolto_sec: Math.round(ascoltatoRef.current * 10) / 10") >= 2, \
            "l'ascolto dichiarato non viene dal ticker"

    def test_09_smontare_non_lascia_niente_acceso(self):
        src = _senza_commenti(RITO.read_text())
        assert ".smonta()" in src, "uscire dalla pagina lascia il motore acceso"
        blocco = src[src.find("useEffect(() => () => {"):]
        blocco = blocco[:blocco.find("}, []);")]
        assert "'interrotta'" in blocco, \
            "la sessione abbandonata non si prova nemmeno a chiudere"


class TestIlVissuto:
    def test_10_scala_1_10_senza_aggettivi(self):
        """Dieci tacche, nessuna etichetta psicologica: il numero è
        della persona, non nostro."""
        src = _senza_commenti(RITO.read_text())
        assert "length: 10" in src
        basso = src.lower()
        for aggettivo in ("rilassat", "ansios", "stressat", "energic",
                          "depress", "malessere estremo"):
            assert aggettivo not in basso, \
                f"la scala si è presa un aggettivo: «{aggettivo}»"
        # pre facoltativo all'apertura, post al congedo
        assert "feedback_pre: pre" in src
        assert "feedback_post: post" in src

    def test_11_note_private_e_cliente_facoltativo(self):
        src = _senza_commenti(RITO.read_text())
        assert "note_operative" in src
        assert "Private" in src or "private" in src
        assert "facoltativo" in src.lower(), \
            "il legame col cliente deve essere dichiaratamente facoltativo"
        # il cliente si sceglie/crea nel CRM via il combobox condiviso
        # (M-CRM): la lista vera sta in ScegliPersona
        assert "ScegliPersona" in src
        scegli = _senza_commenti((PRO / "ScegliPersona.jsx").read_text())
        assert "customersAPI.list" in scegli


class TestPaginaERipescaggio:
    def test_12_da_ogni_scaffale_si_avvia(self):
        src = _senza_commenti(PAGINA.read_text())
        assert 'data-testid="pro-avvia-core"' in src
        assert 'data-testid="pro-avvia-mio"' in src
        # core: lo score è del catalogo (costruisci); operatore: del
        # server (GET del documento)
        assert "score: p.costruisci()" in src
        assert "score: data.score" in src

    def test_13_il_ripescaggio_chiude_onesto(self):
        """Le sessioni rimaste aperte si vedono in home e si chiudono
        come interrotte con ascolto ZERO: l'ascolto è ignoto, e non si
        accredita ciò che non si sa."""
        src = _senza_commenti(PAGINA.read_text())
        assert 'data-testid="pro-sessioni-aperte"' in src
        blocco = src[src.find("function SessioniAperte"):]
        blocco = blocco[:blocco.find("/* ── LA PAGINA")]
        assert "stato: 'in_corso'" in blocco
        assert "esito: 'interrotta', ascolto_sec: 0" in blocco

    def test_14_l_api_client_non_porta_score(self):
        src = _senza_commenti(API.read_text())
        assert "sessioni" in src
        for proibito in ("score_snapshot", "durata_prevista",
                         "organization_id", "operator_user_id"):
            assert proibito not in src

    def test_15_niente_dipendenze_nuove(self):
        import json
        pkg = json.loads((BACKEND_DIR.parent / "frontend"
                          / "package.json").read_text())
        # la fotografia delle dipendenze al 26/8: S3 non ne aggiunge
        assert "web-bluetooth" not in json.dumps(pkg).lower()
        src = _senza_commenti(RITO.read_text())
        importi = re.findall(r"from '([^']+)'", src)
        for imp in importi:
            assert imp.startswith((".", "..")) or imp == "react", \
                f"il rito importa una dipendenza esterna: {imp}"
