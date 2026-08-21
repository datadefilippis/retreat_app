"""Aurya Sound — guardie del ciclo AT: l'ascolto dal telefono (21/8/2026).

Tre fatti da difendere:

AT1 — l'avviso cuffie. L'altoparlante di un telefono non riproduce i
toni sotto i ~500 Hz (27 schede su 32 stanno li'), e il web non puo'
sapere se le cuffie sono collegate. Quindi l'avviso vive NEL momento
del play, solo su telefono, e solo dove il tono e' davvero muto — e la
verita' su «cosa si sente» sta in UN modulo (engine/altoparlante.js),
non ricalcolata da ogni pagina.

AT2 — lo schermo acceso. La sintesi e' WebAudio dal vivo: il blocco
schermo la sospende. Finche' qualcosa suona, il Wake Lock chiede al
sistema di non spegnere lo schermo da solo (engine/veglia.js).

AT3 — l'ascolto continuo. Quello che sopravvive al blocco e' un media
element che riproduce un FILE: la sessione si renderizza (renderPcm,
che gia' esisteva per l'export) e si riproduce con <audio> + Media
Session (engine/continuo.js). Il cancello dei 90 secondi resta
sovrano: niente file intero per chi ha solo l'anteprima.
"""
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ_DIR = FRONTEND_SRC / "features" / "frequenze"

ALTO = (FQ_DIR / "engine" / "altoparlante.js").read_text()
VEGLIA = (FQ_DIR / "engine" / "veglia.js").read_text()
CONTINUO = (FQ_DIR / "engine" / "continuo.js").read_text()
PAGE = (FQ_DIR / "FrequenzePage.js").read_text()
PUB = (FQ_DIR / "PublicFrequencyPage.js").read_text()
CSS = (FQ_DIR / "frequenze.css").read_text()


def _senza_commenti(src):
    """Le guardie leggono il codice, non le spiegazioni: un valore
    citato in un commento non deve farle passare (o fallire)."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"^\s*//.*$", "", src, flags=re.M)


class TestAvvisoCuffieAt1:
    def test_una_sola_verita_sulla_soglia(self):
        """La soglia dei 500 Hz vive in altoparlante.js e basta: una
        seconda copia in una pagina e' il preludio alla divergenza."""
        assert "SOGLIA_TELEFONO_HZ = 500" in ALTO
        for nome, src in (("FrequenzePage", PAGE), ("PublicFrequencyPage", PUB)):
            pulito = _senza_commenti(src)
            assert "500" not in re.sub(r"[a-zA-Z-]500|500[a-zA-Z]", "", pulito) \
                or "SOGLIA" not in pulito.replace("SOGLIA_TELEFONO_HZ", ""), \
                f"{nome} sembra ricalcolarsi una soglia propria"
            assert "from './engine/altoparlante'" in src, \
                f"{nome} non importa la verita' condivisa"

    def test_le_schede_avvisano_al_play(self):
        """L'avviso compare quando la scheda SUONA, col numero vero di
        quella scheda — non un cartello generico all'ingresso."""
        assert "live && avvisoCuffie(entry.cfg)" in PAGE
        assert 'data-testid="fq-avviso-cuffie"' in PAGE

    def test_la_pagina_pubblica_avvisa_al_play(self):
        assert "playing && avvisoTelefono" in PUB
        assert 'data-testid="fqp-avviso-cuffie"' in PUB
        assert "avvisoCuffieScore(track.score)" in PUB

    def test_solo_sul_telefono_e_con_una_sola_media_query(self):
        """Il «dove» lo decide il CSS con la STESSA media query di
        .solo-telefono: due soglie di larghezza sarebbero due telefoni
        diversi nella stessa app."""
        for testo in ("fq-avviso-cuffie", "fqp-avviso-cuffie"):
            src = PAGE if testo.startswith("fq-") else PUB
            blocco = src.split(f'data-testid="{testo}"')[0][-300:]
            assert "solo-telefono-block" in blocco, \
                f"l'avviso {testo} comparirebbe anche sul desktop"
        assert CSS.count(".fqz .solo-telefono-block{display:none}") == 1
        # tutte le regole telefono vivono nelle media query a 820px
        larghezze = set(re.findall(r"@media \(max-width:(\d+)px\)\{[^}]*solo-telefono", CSS))
        assert larghezze == {"820"}, f"soglie telefono divergenti: {larghezze}"

    def test_il_rumore_non_avvisa(self):
        """noise e' banda larga: dal telefono si sente. Un avviso li'
        sarebbe un falso allarme, e i falsi allarmi insegnano a
        ignorare quelli veri."""
        assert "method === 'noise') return null" in ALTO

    def test_la_riga_di_metodo_dice_la_verita_del_dispositivo(self):
        """«Anche in altoparlante» (verita' del metodo) non puo'
        stare, sul telefono, accanto a «servono le cuffie» (verita'
        della fisica): sul telefono vince il dispositivo."""
        assert 'className="no-telefono"' in PAGE
        assert "Dal telefono: solo in cuffia" in PAGE
        assert ".fqz .no-telefono{display:inline}" in CSS
        # la regola inversa vive solo dentro la media query del telefono
        dentro = CSS.split("@media (max-width:820px){", 1)[1]
        assert ".fqz .no-telefono{display:none}" in dentro


class TestSchermoAccesoAt2:
    def test_il_lock_e_condizionato_allo_stato_che_suona(self):
        """Un interruttore DERIVATO («qualcosa suona si'/no»), non
        conteggi sparsi nei punti di stop che perdono il conto."""
        assert "playing || liveKeys.length > 0" in PAGE
        assert "schermoAcceso(); return schermoLibero" in PAGE
        assert "playing && !continuo" in PUB
        assert "schermoAcceso(); return schermoLibero" in PUB

    def test_dove_manca_l_api_si_tace(self):
        assert "'wakeLock' in navigator" in VEGLIA, \
            "senza feature-detect, un browser vecchio esplode al play"

    def test_al_ritorno_visibile_si_riprende(self):
        """L'API rilascia il lock quando la pagina va in background:
        senza il riaggancio su visibilitychange, il primo cambio di
        app spegnerebbe la rete per sempre."""
        assert "visibilitychange" in VEGLIA
        assert re.search(r"addEventListener\('release'", VEGLIA), \
            "il rilascio di sistema lascerebbe un lock fantasma"


class TestAscoltoContinuoAt3:
    def test_il_cancello_resta_sovrano(self):
        """Il continuo e' un FILE INTERO in mano al browser: offrirlo
        prima dello sblocco sarebbe il cancello dei 90 secondi demolito
        da un'altra porta."""
        pulito = _senza_commenti(PUB)
        riga = next(l for l in pulito.splitlines() if "continuoPossibile =" in l)
        assert "unlocked" in riga, "il continuo non controlla lo sblocco"

    def test_passa_dal_sipario(self):
        """Ogni via al suono passa dalle controindicazioni: anche
        questa. `guard(...)` e' il sipario di useSafetyGate."""
        assert re.search(r"preparaGuarded = guard\(", PUB)
        assert 'onClick={() => preparaGuarded(' in PUB

    def test_riusa_il_render_dell_export(self):
        """Niente secondo motore: il file nasce da renderPcm — lo
        stesso dell'export operatore — e diventa WAV, non MP3 (lamejs
        su un telefono sono minuti di attesa in piu')."""
        assert "from './render'" in CONTINUO
        assert "renderPcm(" in CONTINUO and "wavBlob(" in CONTINUO
        assert "lamejs" not in _senza_commenti(CONTINUO)

    def test_limiti_onesti(self):
        """22050 Hz (meta' memoria, contenuto fino a 11 kHz: la
        portante massima del catalogo e' 963 Hz) e tetto a 30 minuti:
        oltre, il WAV non sta nella memoria di un telefono."""
        assert "CONTINUO_SR = 22050" in CONTINUO
        assert "CONTINUO_MAX_SEC = 1800" in CONTINUO
        assert "duration_sec || 0) <= CONTINUO_MAX_SEC" in CONTINUO

    def test_media_session_completa(self):
        """Titolo e comandi sulla schermata di blocco: senza gli
        handler, il telefono mostra un player che non risponde."""
        for azione in ("'play'", "'pause'", "'seekto'", "'stop'"):
            assert f"az({azione}" in CONTINUO, f"manca l'azione {azione}"
        assert "MediaMetadata" in CONTINUO
        assert "setPositionState" in CONTINUO

    def test_gli_eventi_comandano_lo_stato(self):
        """play/pausa arrivano ANCHE dalla schermata di blocco: la
        pagina si sincronizza dagli eventi dell'elemento, mai
        supponendo di essere l'unica a comandare."""
        assert "addEventListener('play'" in CONTINUO
        assert "addEventListener('pause'" in CONTINUO
        assert "onPlay: () => setPlaying(true)" in PUB
        assert "onPause: () => setPlaying(false)" in PUB

    def test_il_file_muore_con_la_pagina(self):
        """revokeObjectURL nel dispose, e dispose allo smontaggio:
        158 MB di WAV che sopravvivono alla pagina sono una perdita
        che il telefono paga al terzo ascolto."""
        assert "URL.revokeObjectURL(url)" in CONTINUO
        assert "contRef.current.dispose()" in PUB

    def test_cambio_traccia_butta_il_file(self):
        """Da /frequenze/a a /frequenze/b il componente NON si smonta:
        senza la pulizia nell'effetto [slug], il file preparato di A
        suonerebbe dentro la pagina di B."""
        blocco_slug = PUB.split("}, [slug]);")[0]
        assert "contRef.current.dispose()" in blocco_slug
        assert "playedRef.current = false" in blocco_slug, \
            "il contatore d'ascolto resterebbe timbrato sulla traccia vecchia"

    def test_un_solo_caricamento_basi(self):
        """Vivo e continuo caricano basi e voce dalla STESSA funzione:
        due percorsi di caricamento divergono alla prima modifica."""
        pulito = _senza_commenti(PUB)
        assert pulito.count("resolveAudioLayers(") == 1
        assert pulito.count("resolveVoiceLayers(") == 1
        assert "caricaLayers = async" in pulito
        assert pulito.count("await caricaLayers(") == 2   # vivo + continuo

    def test_dove_manca_l_api_il_pulsante_non_compare(self):
        assert "'mediaSession' in navigator" in CONTINUO
        assert "continuoSupportato()" in PUB
