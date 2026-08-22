"""Aurya Mode — guardie di AV1 (21/8/2026).

Piano in docs/AURYA_MODE_ANALISI_AV_2026-08.md. AV1 e' il cuore: lo
strato che ASCOLTA e un tema che disegna. Se questo e' bello, il resto e' ripetizione.

Le due regole che si romperebbero in silenzio, e che qui si difendono:
la visualizzazione non deve MAI toccare il suono, e i colori sono
quelli della marca — un video esportato da Aurya deve essere
riconoscibile come Aurya (decisione founder: «stile pulito di Aurya
con colori trascendenti», non arcobaleno).
"""
import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
FQ_DIR = BACKEND_DIR.parent / "frontend" / "src" / "features" / "frequenze"

ANALISI = (FQ_DIR / "visual" / "analisi.js").read_text()
SORGENTE = (FQ_DIR / "visual" / "temi" / "sorgente.js").read_text()
TELA = (FQ_DIR / "visual" / "AuryaMode.jsx").read_text()
PUB = (FQ_DIR / "PublicFrequencyPage.js").read_text()
SYNTH = (FQ_DIR / "engine" / "synth.js").read_text()
CSS = (FQ_DIR / "frequenze.css").read_text()


def _senza_commenti(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"^\s*//.*$", "", src, flags=re.M)


class TestAscoltoAv1:
    def test_una_sola_verita_su_cosa_fa_il_suono(self):
        """I temi non toccano MAI un AnalyserNode: leggono l'oggetto
        che esce da analisi.js. Due letture diverse dello stesso suono
        darebbero due scene che non stanno insieme."""
        assert "createAnalyser" in ANALISI
        for nome, src in (("sorgente", SORGENTE), ("AuryaMode", TELA)):
            assert "createAnalyser" not in src and "getByteFrequencyData" not in src, \
                f"{nome} si e' fatto un analizzatore suo"

    def test_le_bande_sono_quelle_dell_orecchio(self):
        """Non una divisione aritmetica: sotto i 200 Hz c'e' il corpo,
        sopra i 6 kHz c'e' l'aria."""
        assert "da: 20, a: 200" in ANALISI
        assert "da: 6000, a: 20000" in ANALISI
        # il conteggio si fa sul BLOCCO delle bande: `nome` compare
        # anche nel codice che le percorre
        blocco = ANALISI.split("export const BANDE")[1].split("];")[0]
        assert blocco.count("nome:") == 5

    def test_ogni_grandezza_ha_il_suo_tempo(self):
        """Un valore grezzo di FFT sfarfalla 60 volte al secondo: una
        scena che sfarfalla non e' immersiva, e' nervosa."""
        assert "const liscia" in ANALISI
        blocco = ANALISI.split("const k = r.nome ===")[1][:200]
        assert "'bassi'" in blocco and "'alti'" in blocco, \
            "tutte le bande lisciate allo stesso modo: bassi e alti hanno tempi diversi"

    def test_la_media_si_aggiorna_dopo_il_confronto(self):
        """Se la media dei bassi si aggiornasse PRIMA, un crescendo
        lento si mangerebbe da solo ogni picco."""
        corpo = ANALISI.split("stato.battito =")[1]
        assert corpo.index("stato.mediaBassi = liscia") > 0
        assert "stato.battito =" in ANALISI.split("stato.mediaBassi = liscia")[0]


class TestNonToccaIlSuonoAv1:
    def test_il_motore_accetta_un_uscita_ma_non_la_possiede(self):
        """L'analizzatore sta FRA il motore e l'altoparlante: legge cio'
        che esce davvero. Ma resta del chiamante — il motore non lo
        crea e non lo chiude."""
        assert "uscita = null" in SYNTH and "sbocco = null" in SYNTH
        assert "if (uscita) sess.connect(uscita);" in SYNTH
        assert "createAnalyser" not in SYNTH, "il motore non deve farsi l'analizzatore"

    def test_la_tela_non_crea_ne_ferma_audio(self):
        pulito = _senza_commenti(TELA)
        for vietato in ("AudioContext", "createAnalyser", ".stop()", ".play()"):
            assert vietato not in pulito, f"la tela tocca l'audio: {vietato}"

    def test_non_si_accende_da_sola(self):
        """Disegnare consuma: la si chiede."""
        assert "useState(false)" in PUB.split("const [guarda")[1][:60]
        assert 'data-testid="fqp-guarda"' in PUB

    def test_niente_tela_in_ascolto_continuo(self):
        """In continuo il suono esce da un <audio>: portarlo dentro
        WebAudio su iOS lo rimetterebbe sotto il tasto silenzioso. E
        guardare a schermo bloccato non ha senso comunque."""
        blocco = PUB.split("{guarda && lettore")[1][:120]
        assert "!continuo" in blocco


class TestFreniAv1:
    def test_tetto_al_dpr(self):
        """Su un telefono a 3x sarebbero nove volte i pixel da riempire
        a ogni fotogramma, per una scena diffusa dove nessuno li conta."""
        assert "Math.min(window.devicePixelRatio || 1, 2)" in TELA

    def test_si_ferma_quando_nessuno_guarda(self):
        assert "visibilitychange" in TELA
        assert "document.visibilityState === 'visible'" in TELA

    def test_rispetta_chi_chiede_meno_movimento(self):
        assert "prefers-reduced-motion" in TELA
        assert "quieto" in TELA

    def test_pulisce_tutto_allo_smontaggio(self):
        """Due vie (prototipo e rete 2D), due pulizie: la via immersiva
        chiama la pulizia che il prototipo restituisce e svuota la
        tela, la 2D spegne raf/timer/listener."""
        assert "pulisci?.()" in TELA
        assert "tela.innerHTML = ''" in TELA
        coda2d = TELA.split("return () => {\n      vivo = false;")[1][:400]
        for pezzo in ("cancelAnimationFrame", "clearTimeout",
                      "removeEventListener", "ro.disconnect"):
            assert pezzo in coda2d, f"lasciato acceso nella via 2D: {pezzo}"


class TestColoriDiCasaAv1:
    """Decisione founder: «stile pulito di Aurya con colori
    trascendenti». Un video esportato deve essere riconoscibile come
    Aurya — e' pubblicita' della marca, non un visualizzatore qualsiasi."""

    def test_la_tavolozza_e_quella_della_marca(self):
        for nome, hex_ in (("lamp", "#C9B37E"), ("water", "#66B79C"),
                           ("violet", "#9B8BC4"), ("ink", "#0C1618"),
                           ("bone", "#E9E4D9")):
            assert hex_ in SORGENTE, f"manca il colore di marca {nome}"
            assert hex_.lower() in CSS.lower() or hex_ in CSS, \
                f"{hex_} non e' piu' nella tavolozza del mondo Sound"

    def test_niente_arcobaleno(self):
        """Nessun colore inventato fuori dalla famiglia della marca."""
        trovati = set(re.findall(r"#[0-9A-Fa-f]{6}", SORGENTE))
        ammessi = {"#C9B37E", "#66B79C", "#9B8BC4", "#0C1618", "#E9E4D9"}
        assert trovati <= ammessi, f"colori estranei alla marca: {trovati - ammessi}"

    def test_niente_hsl_girevole(self):
        """Il trucco piu' comune dei visualizzatori — la tinta che gira
        col tempo — e' esattamente cio' che renderebbe Aurya
        indistinguibile da mille altri."""
        assert "hsl(" not in SORGENTE


class TestTemaComeFunzionePuraAv1:
    def test_il_tema_e_una_funzione_sola(self):
        """Aggiungerne uno non deve toccare nient'altro: e' lo stesso
        contratto delle schede della biblioteca."""
        assert re.search(r"export function disegna\(g, L, t, \{ w, h \}\)", SORGENTE)
        assert "export const NOME" in SORGENTE

    def test_la_scia_invece_della_cancellazione(self):
        """Cancellare a ogni fotogramma da' un disegno che sbatte; un
        velo lascia una memoria luminosa."""
        assert "const SCIA" in SORGENTE, "la scia non e' piu' una scelta dichiarata"
        assert "clearRect" not in SORGENTE

    def test_la_somma_della_luce_si_richiude(self):
        """globalCompositeOperation 'lighter' lasciato acceso
        sporcherebbe tutto cio' che disegna dopo."""
        # il tema apre 'lighter' una volta e lo richiude in coda; il
        # velo del tempo si disegna in source-over PRIMA di aprirlo
        assert SORGENTE.count("globalCompositeOperation = 'lighter'") == 1
        assert SORGENTE.count("globalCompositeOperation = 'source-over'") == 2
        assert SORGENTE.rstrip().endswith("}"), "il file deve chiudersi col disegna"
        coda = SORGENTE.split("globalCompositeOperation = 'lighter'")[1]
        assert "globalCompositeOperation = 'source-over'" in coda, \
            "lighter lasciato acceso: sporcherebbe cio' che disegna dopo"


PROTO = (FQ_DIR / "visual" / "prototipo.js").read_text()
CSS_PROTO = (FQ_DIR / "visual" / "prototipo.css").read_text()
CSS_EMB = (FQ_DIR / "visual" / "incorporato.css").read_text()
MARKUP_EMB = (FQ_DIR / "visual" / "markupIncorporato.js").read_text()
MARKUP_PROTO = (FQ_DIR / "visual" / "prototipoMarkup.js").read_text()
VISUAL_DIR = FQ_DIR / "visual"


class TestUnMotoreSoloAv5:
    """
    AV5 (22/8) — la meditazione e la pagina strumento montano LO STESSO
    file. Prima erano due motori diversi per la stessa cosa, ed e'
    esattamente cio' che il founder ha visto e bocciato («non e' per
    nulla simile al prototipo»). Queste guardie difendono l'unicita':
    se qualcuno ricrea un secondo motore, qui si rompe.
    """

    def test_esiste_un_solo_motore(self):
        assert not (VISUAL_DIR / "motore3d.js").exists(), \
            "e' tornato un secondo motore: la divergenza ricomincia da qui"
        scene = [f.name for f in VISUAL_DIR.glob("*.js")
                 if "new THREE.WebGLRenderer" in f.read_text()]
        assert scene == ["prototipo.js"], f"scene Three fuori dal prototipo: {scene}"

    def test_three_entra_solo_quando_si_guarda(self):
        """Three pesa ~500KB: nel main sarebbe un dazio per chiunque
        apre QUALSIASI pagina. Import dinamico, in tutt'e due i posti."""
        assert "import('./prototipo')" in TELA
        assert "from 'three'" not in TELA
        assert "from 'three'" in PROTO   # l'unico posto

    def test_le_forme_sono_quelle_del_preset_aurya(self):
        """Decisione founder: nella meditazione le forme sono quelle di
        default del preset Aurya, con la palette multicolore."""
        # da VC6 il ramo si chiama `prestato`: vale per la meditazione
        # E per lo studio, che partono dallo stesso ambiente
        blocco = PROTO.split("if (prestato){")[1][:900]
        assert "PRESETS[0]" in blocco, "il preset Aurya non e' piu' quello di partenza"
        assert "p.name === 'Prism'" in blocco, "persa la palette multicolore"
        assert "mode: aurya.mode" in blocco

    def test_la_meditazione_e_un_ambiente_non_un_pannello(self):
        """Niente pannelli, niente cancello: nel markup incorporato ci
        sono solo la tela e la vignettatura."""
        assert "if (!incorporato){" in PROTO, "i pannelli non sono piu' isolati"
        for pannello in ("sliders", "gate", "modebar", "presetName"):
            assert pannello not in MARKUP_EMB, f"pannello nella meditazione: {pannello}"
        assert 'id="gl"' in MARKUP_EMB and 'id="vig"' in MARKUP_EMB

    def test_l_audio_e_prestato_mai_creato(self):
        """La tela non possiede il suono: nella meditazione riceve
        l'analizzatore del grafo che sta suonando, e non chiude un
        contesto che non e' suo (ctxA resta nullo)."""
        # solo il RAMO incorporato: dopo di lui ricomincia ensureCtx,
        # che un contesto lo crea eccome (per la pagina strumento)
        blocco = PROTO.split("if (prestato && opz.analizzatore){")[1].split("\n}")[0]
        assert "analyser = opz.analizzatore" in blocco
        assert "new (window.AudioContext" not in blocco
        assert "if (ctxA) ctxA.close()" in PROTO, \
            "il contesto si chiude solo se e' nostro"
        assert "analizzatore: lettore.analyser" in TELA

    def test_le_manopole_di_un_altro_giorno_non_entrano(self):
        """localStorage e' della stanza degli esperimenti: la
        meditazione dev'essere sempre lo stesso ambiente."""
        assert "if (prestato) return;" in PROTO.split("const save =")[1][:120]
        ramo = PROTO.split("} else {")[1][:200]
        assert "localStorage.getItem('aurya.settings.v2')" in ramo

    def test_lo_scroll_non_viene_rubato(self):
        """Dentro una pagina che si scorre col dito, trascinare la
        scena significa non poter piu' scendere."""
        assert "controls.enableRotate = false" in PROTO
        assert "if (incorporato){ controls.enableRotate" in PROTO

    def test_la_misura_e_la_scatola_non_la_finestra(self):
        assert "function misura()" in PROTO
        # incorporato misura la SCATOLA, le altre modalita' la finestra
        assert "incorporato ? r.width : (window.innerWidth || r.width)" in PROTO
        assert "new ResizeObserver(resize)" in PROTO

    def test_tutto_schermo_col_tocco(self):
        """Richiesta founder: «le forme con un clicco sullo schermo
        possono essere viste a tutto schermo». Su iPhone il fullscreen
        nativo per un elemento non esiste: la verita' e' la classe."""
        assert ".avze.pieno" in CSS_EMB and "position: fixed" in CSS_EMB
        # la promessa DEVE avere il catch: dentro un iframe senza
        # permesso il rifiuto diventa un errore non gestito in faccia
        # all'utente (visto dal vivo: «Permissions check failed»)
        assert "requestFullscreen?.()?.catch(" in TELA
        assert "exitFullscreen?.()?.catch(" in TELA
        assert "'Escape'" in TELA, "senza via d'uscita da tastiera si resta intrappolati"
        assert "fullscreenchange" in TELA

    def test_il_foglio_del_prototipo_non_esce_dalla_stanza(self):
        """Il CSS estratto conteneva regole GLOBALI (*, a, :root, .row,
        .sub): una volta caricata la pagina ripitturavano il sito
        intero — .sub e' usata nella landing Sound. Tutto sotto .avz."""
        for globale in ("\n*{", "\n:root{", "\na{", "\n  a{", "\n  *{",
                        "\n  :root{", "\n  .row{", "\n  .sub{"):
            assert globale not in CSS_PROTO, f"regola globale rimasta: {globale!r}"
        assert CSS_PROTO.count(".avz") > 60

    def test_l_inseguitore_e_asimmetrico(self):
        """Sale piu' svelto di come scende — ma da DA5 a passo di
        tai-chi (0,7s/1,8s): il 4.2/0.85 originale era da club, e ogni
        fluttuazione di nota entrava nella geometria («piu' stress che
        relax», founder). L'orecchio resta veloce per conto suo."""
        assert "target > cur ? 1.5 : 0.55" in PROTO

    def test_la_scia_sbiadisce_verso_il_profondo(self):
        """Non verso il nero piatto ma verso un gradiente
        profondo→bordo: e' quello che da' il volume."""
        assert "uDeep" in PROTO and "uEdge" in PROTO
        assert "smoothstep(.05,.72,r)" in PROTO

    def test_l_aura_ha_il_dithering(self):
        """Senza, i gradienti larghi a 8 bit fanno anelli visibili."""
        assert "Math.random()*2-1" in PROTO

    def test_le_dodici_forme_ci_sono_tutte(self):
        """Le 7 del prototipo + le 5 mistiche di FM3 (founder: «falli
        tutti e 5, li voglio tutti!»)."""
        tab = (VISUAL_DIR / "tabelle.js").read_text()
        blocco = tab.split("const MODES = [")[1].split("];")[0]
        for nome in ("Breath", "Nebula", "Spiral", "Flow", "Mandala",
                     "Helix", "Ripple",
                     "Flower", "Merkaba", "Torus", "Ocean", "Portal"):
            assert f"['{nome}'" in blocco, f"forma persa: {nome}"

    def test_quiete_significa_niente_galassia(self):
        """prefers-reduced-motion: una galassia che turbina non e'
        «movimento ridotto» per nessuna definizione — si resta sul 2D,
        che in quiete rallenta da solo."""
        blocco = TELA.split("webgl2 =")[1][:80]
        assert "!quieto" in blocco

    def test_dispose_completo(self):
        assert "geo.dispose" in PROTO and "renderer.dispose" in PROTO


VISUAL = (FQ_DIR / "visual" / "VisualPage.jsx").read_text()


class TestPaginaStrumentoAv2:
    """
    AV2-bis — /sound/visual E' il prototipo HTML del founder,
    INTEGRALE («era perfetto quello che ti ho mandato»). Markup e
    script sono ESTRATTI dal suo file, non trascritti; le patch di
    montaggio sono chirurgiche e queste guardie ne fissano il
    perimetro.
    """

    PROTO = (FQ_DIR / "visual" / "prototipo.js").read_text()
    MARKUP = (FQ_DIR / "visual" / "prototipoMarkup.js").read_text()
    PAGINA = (FQ_DIR / "visual" / "VisualPage.jsx").read_text()

    def test_la_rotta_esiste(self):
        app = (FQ_DIR.parent.parent / "App.js").read_text()
        assert '"/sound/visual"' in app

    def test_la_rotta_arriva_davvero_all_utente(self):
        """Il 22/8 in produzione /sound/visual dava 404: nginx manda
        tutto /sound/* al prerender SEO, che conosceva solo le pagine
        editoriali piu' crea e tracce. Una rotta SPA nuova sotto
        /sound non basta dichiararla in App.js — va riconosciuta anche
        di la', o l'utente non ci arriva."""
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert '("crea", "tracce", "visual")' in shell

    def test_il_prototipo_e_integrale(self):
        """I numeri del founder: 11 slider, 6 palette, 7 modi, 7
        preset, 4 camere. Da VC1 le tabelle vivono in tabelle.js (lo
        standard che anche Crea legge), estratte verbatim: i contenuti
        si controllano la' e il prototipo deve berle da la'."""
        tab = (FQ_DIR / "visual" / "tabelle.js").read_text()
        assert "'intensity','Intensity'" in tab
        assert tab.count("{ name:'") >= 13   # 6 palette + 7 preset
        for nome in ("Aurya", "Cosmos", "Anahata", "Prana", "Nirvana",
                     "Kundalini", "Samadhi"):
            assert f"name:'{nome}'" in tab, f"preset perso: {nome}"
        assert "from './tabelle'" in self.PROTO, \
            "il prototipo non legge piu' lo standard"
        assert "buildMandala" in self.PROTO, "perso il motore-mandala a petali"
        assert "'aurya.settings.v2'" in self.PROTO, "perse le impostazioni salvate"

    def test_three_entra_solo_qui_e_lazy(self):
        assert "import('./prototipo')" in self.PAGINA
        assert "from 'three'" not in self.PAGINA

    def test_la_promessa_privacy_e_nel_gate(self):
        piatto = " ".join(self.MARKUP.split())
        assert "non viene caricato da nessuna parte" in piatto

    def test_l_audio_non_tocca_mai_la_rete(self):
        pulito = _senza_commenti(self.PROTO)
        for vietato in ("fetch(", "XMLHttpRequest", "FormData"):
            assert vietato not in pulito, f"l'audio dell'utente esce: {vietato}"
        assert "URL.createObjectURL" in self.PROTO

    def test_il_microfono_si_spegne_davvero(self):
        """FIX nostro al prototipo: disconnect() staccava il nodo ma
        lasciava lo stream vivo — la spia del browser restava accesa
        per sempre."""
        blocco = self.PROTO.split("function disconnect()")[1][:300]
        assert "getTracks().forEach((t) => t.stop())" in blocco

    def test_il_microfono_non_va_agli_altoparlanti(self):
        blocco = self.PROTO.split("createMediaStreamSource")[1][:200]
        assert "connect(analyser)" in blocco
        assert "destination" not in blocco, "larsen garantito"

    def test_lo_smontaggio_e_pulito(self):
        """Il prototipo era un file standalone che girava per sempre:
        dentro il sito deve morire con la pagina."""
        coda = self.PROTO.split("function cleanup()")[1][:600]
        for pezzo in ("cancelAnimationFrame", "removeEventListener",
                      "disconnect()", "revokeObjectURL", "ctxA.close",
                      "renderer.dispose"):
            assert pezzo in coda, f"lasciato acceso: {pezzo}"
        assert "pulisci?.()" in self.PAGINA

    def test_il_blob_della_traccia_si_revoca(self):
        assert "if (fileUrl) URL.revokeObjectURL(fileUrl)" in self.PROTO


class TestScenaDellAutoreVc:
    """
    VC1-VC4 (22/8) — la scena e' parte della composizione. Decisioni
    founder: la scena e' DELL'AUTORE (chi ascolta tiene solo il tutto
    schermo); /sound/visual e' LO STANDARD («se aggiungeremo nuovi
    preset o nuove variabili, compariranno anche in Crea»); il ritocco
    post-pubblicazione passa dal normale ritira→bozza→ripubblica.
    """

    TAB = (FQ_DIR / "visual" / "tabelle.js").read_text()
    STUDIO = (FQ_DIR / "visual" / "StudioScena.jsx").read_text()
    CREA = (FQ_DIR / "FrequenzePage.js").read_text()

    # ── il contratto (VC1) ────────────────────────────────────────────
    def test_la_scena_si_valida_con_la_filosofia_listino(self):
        from models.frequency_track import clean_visual
        assert clean_visual(None) is None and clean_visual("x") is None
        vis = clean_visual({"intensity": 999, "pal": 42, "mode": -3})
        assert vis["intensity"] == 200      # riportato nel range
        assert vis["pal"] == 5 and vis["mode"] == 0
        assert vis["particles"] == 17000    # default della tabella
        assert clean_visual({})["mode"] == 4  # vuoto = ambiente AV5

    def test_la_scena_viaggia_nella_ricetta_e_il_pregresso_non_cambia(self):
        from models.frequency_track import clean_score
        base = {"score_version": 1, "duration_sec": 300,
                "layers": [{"method": "bin", "carrier": 200,
                            "f0": 8, "f1": 8}]}
        senza = clean_score(dict(base))
        assert "visual" not in senza, "ricetta mai toccata = campo assente"
        con = clean_score({**base, "visual": {"mode": 2, "pal": 0}})
        assert con["visual"]["mode"] == 2 and con["visual"]["pal"] == 0
        assert con["score_version"] == 1, "la scena non deve alzare la versione"

    def test_parita_backend_frontend_sullo_standard(self):
        """LA guardia della decisione founder: i range del backend sono
        lo specchio della tabella SLIDERS. Un cursore nuovo nello
        standard che il backend non conosce verrebbe strappato dal
        validatore in silenzio — qui invece esplode un test."""
        from models.frequency_track import (
            VISUAL_RANGES, VISUAL_MODES, VISUAL_PALETTES, VISUAL_CAMS)
        righe = re.findall(
            r"\['(\w+)','[^']*',(-?\d+),(-?\d+),(-?\d+),", self.TAB)
        fe = {k: (int(lo), int(hi), int(d)) for k, lo, hi, d in righe}
        assert fe, "tabella SLIDERS non leggibile: aggiornare la guardia"
        assert fe == VISUAL_RANGES, (
            f"BE e standard divergono: solo FE {set(fe) - set(VISUAL_RANGES)},"
            f" solo BE {set(VISUAL_RANGES) - set(fe)}, o range diversi")
        blocco_pal = self.TAB.split("const PALETTES = [")[1].split("];")[0]
        assert blocco_pal.count("name:'") == VISUAL_PALETTES
        blocco_modi = self.TAB.split("const MODES = [")[1].split("];")[0]
        assert blocco_modi.count("['") == VISUAL_MODES
        blocco_cam = self.TAB.split("const CAMS = [")[1].split("]")[0]
        assert blocco_cam.count("'") == VISUAL_CAMS * 2

    def test_lo_standard_non_pesa_500kb(self):
        """tabelle.js e' fatto per essere importato da Crea: se
        importasse Three, Crea pagherebbe il motore per leggere
        quattro liste."""
        codice = re.sub(r"/\*.*?\*/", "", self.TAB, flags=re.S)
        assert "three" not in codice.lower()
        assert "import" not in codice

    # ── la tastiera di Crea (VC3/VC4) ─────────────────────────────────
    def test_lo_studio_e_il_prototipo_non_una_copia(self):
        """VC6, decisione founder: «/sound/visual e' lo standard». Chi
        sceglie in Crea usa QUELLO — stesso markup, stesso script — non
        una tastiera nostra che un giorno divergerebbe."""
        assert "from './prototipoMarkup'" in self.STUDIO
        assert "import('./prototipo')" in self.STUDIO
        assert "studio: true" in self.STUDIO
        assert not (VISUAL_DIR / "ScenaControlli.jsx").exists(), \
            "e' tornata una seconda tastiera: un solo posto dove si sceglie"
        for nome in ("Cosmos", "Anahata", "Samadhi", "SLIDERS"):
            assert nome not in self.STUDIO, \
                f"lo studio si e' copiato lo standard in casa ({nome})"

    def test_cio_che_si_sceglie_torna_nella_ricetta(self):
        assert "alFatto" in self.STUDIO and "onChiudi" in self.STUDIO
        assert "opz.alFatto?.(fotografia())" in PROTO, \
            "il «Fatto» deve consegnare i valori RISOLTI, non un preset"
        assert "if (scelta) setVisual(scelta)" in self.CREA

    def test_la_scena_scelta_arriva_alla_tela_gia_accesa(self):
        """Segnalato dal founder: dopo lo studio la preview in Crea
        restava al mandala. La tela riceveva la scena SOLO al
        montaggio, e il montaggio non dipende da `visual` — di
        proposito: rimontare vuol dire ricostruire 24.000 particelle a
        ogni ritocco. La scena si applica al volo sul motore vivo."""
        assert "manicoRef.current?.applica?.(visual)" in TELA
        assert "}, [visual]);" in TELA
        assert "}, [lettore, attivo]);" in TELA, \
            "se il montaggio dipendesse da `visual`, ogni ritocco ricostruirebbe la scena"

    def test_pubblicare_porta_con_se_la_scena(self):
        """Chi pubblica non deve ricordarsi di salvare prima."""
        blocco = self.CREA.split("const publishTrack")[1][:200]
        assert "await save()" in blocco

    def test_il_marchio_e_quello_di_casa(self):
        """Prima qui «AURYA» compariva DUE volte: il marchio del
        prototipo e il titolo grande, che mostra il nome del preset —
        e il preset di casa si chiama Aurya. Ora c'e' il logo che sta
        in ogni pagina del sito, AURYA nella tipografia di casa, e
        sotto il nome della sezione."""
        assert "/logo-aurya-512.png" in MARKUP_PROTO
        assert "<span class=\"sezione\">Visuals</span>" in MARKUP_PROTO
        assert 'id="presetTitle"' not in MARKUP_PROTO, "il doppione e' tornato"
        assert "'Cinzel'" in CSS_PROTO
        # e chi scriveva quel titolo deve tollerarne l'assenza
        assert "if (titolo) titolo.textContent" in PROTO

    def test_il_titolo_della_sessione_in_cima(self):
        """Richiesta founder: in alto si legge il titolo che l'autore
        ha dato alla sessione; «La tua sessione» solo finche' non ce
        n'e' uno."""
        blocco = PROTO.split("if (studio){")[1][:900]
        assert "opz.titolo" in blocco and "|| 'La tua sessione'" in blocco
        assert "titolo={title}" in self.CREA
        assert "titolo," in self.STUDIO

    def test_i_pannelli_si_chiudono_con_un_gesto(self):
        """Richiesta founder: da desktop i pannelli si chiudono per
        vedere la scena a tutto schermo, e si riaprono altrettanto
        semplicemente. Un solo interruttore (data-aperto); a decidere
        cosa significhi «chiuso» — scorrere di lato o scendere in
        basso — e' il CSS."""
        assert "f.dataset.aperto = apre ? '1' : '0'" in PROTO
        assert 'translateX(-102%)' in CSS_PROTO and 'translateX(102%)' in CSS_PROTO
        largo = CSS_PROTO.split("@media (min-width:761px)")[1]
        assert '#chipPreset,.avz.studio #chipRegola{display:inline-flex}' in largo, \
            "senza i chip a schermo largo, un pannello chiuso non si riapre piu'"

    def test_la_tendina_ha_la_sua_x(self):
        assert 'class="foglio-x"' in MARKUP_PROTO
        assert ".foglio-x" in CSS_PROTO
        assert "b.closest('.panel').dataset.aperto = '0'" in PROTO

    def test_la_soglia_non_si_decide_a_finestra_zero(self):
        """Stessa trappola del NaN: al montaggio `innerWidth` puo'
        dichiarare 0, e zero E' minore di 760 — un desktop nascerebbe
        coi pannelli chiusi. Si usa la misura robusta, e la soglia si
        riapplica quando viene attraversata davvero."""
        assert "const telefono = () => misura().w <= 760" in PROTO
        assert "mqTelefono.addEventListener('change', partenzaFogli)" in PROTO
        assert "mqTelefono.removeEventListener" in PROTO, \
            "il listener della soglia resterebbe acceso dopo l'uscita"

    def test_l_inquadratura_e_parte_della_scena(self):
        """Segnalato dal founder: «col mouse calibro la traiettoria di
        una forma, ma nella preview della meditazione e in Crea resta
        sempre standard». La camera era l'unica cosa che l'autore
        poteva muovere senza che la ricetta se ne accorgesse."""
        from models.frequency_track import clean_visual
        vis = clean_visual({"cam_x": -13.671, "cam_y": 4.33, "cam_z": 24.19})
        assert (vis["cam_x"], vis["cam_y"], vis["cam_z"]) == (-13.67, 4.33, 24.19)
        # facoltativa: chi non la tocca non se la ritrova scritta
        assert "cam_x" not in clean_visual({"mode": 2})
        # e non entra a meta': una terna incompleta o degenere non e'
        # un punto di vista
        assert "cam_x" not in clean_visual({"cam_x": 5, "cam_y": 5})
        assert "cam_x" not in clean_visual({"cam_x": 0, "cam_y": 0, "cam_z": 0})

    def test_l_inquadratura_viaggia_in_tutt_e_due_i_versi(self):
        assert "out.cam_x" in PROTO and "function inquadra(v)" in PROTO
        # si applica al montaggio (meditazione) E al volo (preview in
        # Crea, tornando dallo studio)
        assert "inquadra(opz.impostazioni)" in PROTO
        assert "if (inquadra(patch)) distBase" in PROTO

    def test_il_respiro_non_strappa_la_camera_di_mano(self):
        """La camera «Breathe» modulava intorno a un 28 fisso: qualsiasi
        avvicinamento scelto dall'autore veniva buttato via a ogni
        fotogramma. Ora respira intorno alla SUA distanza, e mentre
        trascina il loop non gliela tocca."""
        assert "28 - breath*3.5" not in PROTO
        assert "distBase * (1 - breath" in PROTO
        assert "if (!manoUtente)" in PROTO
        assert "controls.addEventListener('end'" in PROTO

    def test_lo_studio_sta_fuori_dalla_pagina(self):
        """Trovato dal vivo: montato dentro Crea lo studio EREDITA il
        CSS del sito (`.fqz .row` sotto i 900px impilava i valori dei
        cursori sotto le etichette). Il portale su <body> chiude il
        passaggio — e toglie di mezzo gli antenati con `transform`,
        che rompono i `position:fixed`."""
        assert "createPortal(" in self.STUDIO
        assert "document.body" in self.STUDIO

    def test_le_sorgenti_dello_strumento_sono_spente(self):
        """In studio il suono e' la sessione: microfono e carica-traccia
        non hanno senso, e il gate non deve chiedere nulla."""
        blocco = PROTO.split("if (studio){")[1][:600]
        assert "el('gate').style.display = 'none'" in blocco
        assert "el('srcSect').style.display = 'none'" in blocco
        assert "La tua sessione" in blocco

    def test_il_marchio_non_porta_via_la_sessione(self):
        blocco = PROTO.split("if (studio){")[1][:900]
        assert "marchio.removeAttribute('href')" in blocco, \
            "il marchio navigherebbe via, buttando l'ascolto in corso"

    def test_su_telefono_i_pannelli_sono_fogli(self):
        """I due pannelli fissi fanno 438px: piu' larghi di mezzo
        telefono. Sotto i 760px diventano fogli dal basso, uno alla
        volta, e la forma resta protagonista."""
        assert "@media (max-width:760px)" in CSS_PROTO
        blocco = CSS_PROTO.split("@media (max-width:760px)")[1]
        assert ".avz.studio #left,.avz.studio #right" in blocco
        # da VC7 l'interruttore e' data-aperto, uno solo per tutt'e
        # due i formati (il CSS decide se «chiuso» sia di lato o giu')
        assert "translateY(102%)" in blocco
        assert '[data-aperto="1"]' in blocco
        assert "62dvh" in blocco, "un foglio non deve mangiarsi lo schermo"
        assert "env(safe-area-inset-bottom)" in blocco
        assert "#chipPreset" in blocco and "#chipRegola" in blocco

    def test_una_misura_non_e_mai_zero(self):
        """Trovato dal vivo: al montaggio la finestra puo' dichiarare
        0 (telefono che ruota, riquadro che si dimensiona, scheda che
        torna visibile). Da w=0 nasce un aspect NaN, e NaN e'
        APPICCICOSO: `x += (k-x)*.08` non guarisce mai — il loto
        spariva per sempre."""
        assert "Math.max(1, Math.round(w))" in PROTO
        assert "window.innerWidth || r.width" in PROTO
        assert "if (!Number.isFinite(mandFit)) mandFit = 1" in PROTO

    def test_una_sola_verita_sul_campionamento(self):
        """Lo studio e' la prima modalita' con i pannelli E l'audio
        prestato: `ctxA.sampleRate` era nullo e i misuratori
        spegnevano il disegno (la guardia anti-tempesta l'ha detto in
        una riga sola, invece di sessanta errori al secondo)."""
        assert "const campionamento = () =>" in PROTO
        corpo = _senza_commenti(PROTO)
        assert corpo.count("ctxA.sampleRate") == 1, \
            "qualcuno legge di nuovo il contesto senza passare da campionamento()"

    def test_il_manico_del_motore(self):
        assert "return { pulisci: cleanup, applica, leggi: fotografia };" in PROTO
        blocco = PROTO.split("function applica(patch){")[1][:400]
        assert "U.uMode.value = S.mode" in blocco, \
            "applica() deve trattare il modo come setMode"
        assert "if (opz.impostazioni) Object.assign(S, opz.impostazioni)" in PROTO

    def test_il_telefono_lima_ma_non_firma(self):
        """Trovato salvando DAL VIVO: il tetto del telefono era scritto
        su S.particles e finiva nella fotografia — l'autore che compone
        da telefono avrebbe firmato una scena limata anche per chi
        ascolta da desktop. Il tetto e' un limite di RESA: vive nel
        loop, mai nelle impostazioni."""
        assert "tettoParticelle = 9000" in PROTO
        assert "Math.min(S.particles, tettoParticelle) / MAX_P" in PROTO
        assert "S.particles = Math.min" not in PROTO, \
            "il tetto e' tornato a scrivere sulla scelta dell'autore"

    # ── il flusso in Crea (VC2) ───────────────────────────────────────
    def test_l_anteprima_esce_dall_analizzatore(self):
        assert "uscita: lettoreRef.current.analyser" in self.CREA
        assert "creaLettore(ctx)" in self.CREA


    def test_uno_spezzone_indecifrabile_non_lascia_muta_la_sessione(self):
        """LA causa vera del silenzio su iPhone (22/8, trovata col
        pannello ?diag=1: contesto running, currentTime che avanza,
        `livelloGrafo: 0`). Le basi in loop si scaricano a SPEZZONE
        (Range, risparmio banda del ciclo ES): un m4a tagliato a meta'
        e' un file incompleto — i decoder permissivi lo accettano,
        Safari iOS lo RIFIUTA. Il rifiuto finiva in un catch muto, la
        base spariva dal mix e una sessione fatta di sole basi restava
        senza un solo campione.
        Ora: se lo spezzone non si decodifica si riprende il file
        INTERO (si perde la banda, mai il suono), e ogni base saltata
        lascia una nota nella diagnosi."""
        assets = (FQ_DIR / "engine" / "assets.js").read_text()
        assert "if (!ottenuto) throw e;" in assets, \
            "manca il fallback: senza, un decoder severo azzera la sessione"
        blocco = assets.split("if (!ottenuto) throw e;")[1][:400]
        assert "fetch(url)" in blocco and "decodeAudioData(ab2)" in blocco, \
            "il fallback deve riprendere il file INTERO, non riprovare lo stesso pezzo"
        # e il silenzio non deve piu' essere invisibile: il pannello di
        # diagnosi e' stato rimosso a problema risolto, ma la VOCE
        # dell'errore resta in console — un catch muto ci e' costato
        # mezza giornata e tre diagnosi sbagliate
        assert "BASE SALTATA" in assets
        assert "console.warn" in assets
        assert "catch (e) { /* base saltata" not in assets, \
            "il catch e' tornato muto"

    def test_lo_stop_scende_prima_di_troncare(self):
        """Founder, 22/8: «allo stop un rumore di frequenze fastidioso,
        idem andando indietro». Due cause nel vecchio stop: nodi
        troncati subito (click) con la rampa arrivata a nodi morti; e
        durante il fade-in la rampa di salita GIA' programmata vinceva
        sulla discesa — il suono risaliva dopo lo stop. L'ordine e' la
        cura: cancellare le rampe, scendere, POI fermare."""
        # nel file ci sono piu' stop(): quello della SESSIONE e' dopo
        # `elapsed:` (l'handle di startPreview)
        blocco = SYNTH.split("elapsed: () => ctx.currentTime - t0")[1]
        blocco = blocco.split("stop() {")[1].split("},")[0]
        assert "cancelScheduledValues" in blocco, \
            "senza cancellare le rampe, il fade-in programmato risale sopra lo stop"
        prima = blocco.index("setTargetAtTime(0.0001")
        dopo = blocco.index("n.stop()")
        assert prima < dopo, "i nodi vanno fermati DOPO la discesa, non prima"

    def test_la_durata_e_onesta(self):
        """Ciclo DU (founder, 22/8): tetto 30 FINTO (a schermo 35, il
        motore a 30), popup di adattamento A OGNI CIFRA digitata sopra
        la tastiera del telefono, e il default nascosto di 20 min che
        inganna chi monta 5 minuti di tracce. Ora: AUTO di default (la
        sessione dura quanto il contenuto, pill sempre a vista), FISSA
        solo per scelta dal foglio, commit al rilascio, tetto vero e
        SPIEGATO."""
        assert "const [durataFissaMin, setDurataFissaMin] = useState(null)" in self.CREA, \
            "il default deve essere AUTO (null), non un numero nascosto"
        assert 'data-testid="fq-durata"' in self.CREA          # la pill
        assert 'data-testid="fq-foglio-durata"' in self.CREA   # il foglio
        assert "Il massimo è 30 minuti" in self.CREA           # il tetto spiegato
        assert "onDurationChange" not in self.CREA, \
            "e' tornato il commit per-cifra che apriva il popup sulla tastiera"
        # il protocollo porta la SUA durata (non il pavimento dell'AUTO)
        assert "durataProtocollo" in self.CREA
        # e riaprendo una bozza, durata=fine tracce → torna AUTO
        assert "Math.abs(d - fine) < 1 ? null" in self.CREA

    def test_il_ponte_si_rilascia_alla_pausa(self):
        """Founder (22/8, iPhone): «in pausa resta una vibrazione
        costante, sparisce solo ricaricando». Un <audio> lasciato in
        play su uno stream ammutolito, su iOS, ripete in loop l'ultimo
        buffer. Il ponte va in pausa a ogni stop — ma DOPO la coda
        morbida (rilascio ritardato), e un nuovo play lo annulla."""
        ponte = (FQ_DIR / "engine" / "ponte.js").read_text()
        assert "rilascia(ms = 900)" in ponte
        assert "clearTimeout(timerRilascio)" in ponte.split("async avvia()")[1][:200], \
            "un nuovo play deve annullare il rilascio in volo, o pausera' il suono nuovo"
        for nome, src in (("Crea", self.CREA), ("pagina pubblica", PUB)):
            assert "_fqzPonte?.rilascia?.()" in src, f"{nome}: il ponte resta in play per sempre"

    def test_il_suono_esce_dal_canale_musica(self):
        """LA guardia del silenzio, terza e definitiva — scritta da due
        difetti veri in PRODUZIONE (22/8, iPhone): su iOS (dove OGNI
        browser e' WebKit, Brave incluso) il grafo WebAudio collegato a
        destination e' suono di CONTORNO — il silenziatore lo azzera —
        mentre un <audio> e' musica e suona sempre. Le anteprime
        (<audio>) si sentivano, la sessione (WebAudio) no.
        La regola: il motore sfocia nel PONTE
        (MediaStreamDestination → <audio playsinline>), UN canale solo
        per tutte le piattaforme; l'analizzatore resta un osservatore
        in parallelo — osserva, non trasporta."""
        ponte = (FQ_DIR / "engine" / "ponte.js").read_text()
        assert "createMediaStreamDestination" in ponte
        assert "playsInline = true" in ponte
        assert "navigator.audioSession" in ponte and "'playback'" in ponte
        assert "sess.connect(sbocco || ctx.destination);" in SYNTH
        assert "if (uscita) sess.connect(uscita);" in SYNTH
        assert "sess.connect(uscita || ctx.destination)" not in SYNTH, \
            "l'analizzatore e' tornato in mezzo alla strada del suono"
        for nome, src in (("Crea", self.CREA), ("pagina pubblica", PUB)):
            assert "creaPonte(ctx)" in src, f"{nome}: il ponte non c'e'"
            assert "ponte.avvia()" in src, \
                f"{nome}: l'<audio> del ponte va avviato DENTRO il gesto"
            assert "sbocco:" in src, f"{nome}: il motore non sfocia nel ponte"
            assert "analyser.connect(ctx.destination)" not in src, \
                f"{nome}: doppio percorso del suono"

    def test_la_scena_si_chiede_e_si_salva_con_la_bozza(self):
        assert 'data-testid="fq-guarda"' in self.CREA
        assert "...(visual ? { visual } : {})" in self.CREA
        assert "setVisual(s.visual || null)" in self.CREA, \
            "riaprire la bozza deve riportare la scena"
        assert self.CREA.count("setVisual(null)") >= 1, \
            "la bozza nuova non deve ereditare la scena della vecchia"

    def test_chi_ascolta_vede_la_scena_dell_autore(self):
        assert "visual={track.score?.visual || null}" in PUB
        # e non ha una tastiera per cambiarla: la scelta e' autoriale
        assert "ScenaControlli" not in PUB


class TestBallerinoDa:
    """
    Ciclo DA (22/8) — «un oggetto che si muove come un ballerino e si
    adatta alla musica» (founder). Prima: a silenzio la scena teneva il
    65-70% del moto, il respiro era un metronomo sordo, l'audio pesava
    il 15-20% del gesto. Piano in docs/VISUAL_DANZA_ANALISI_DA_2026-08.md;
    prova strumentale: battito VERO a 2.0 Hz stimato 1.94, fiducia 0.74,
    vita→0 allo stop.
    """

    def test_l_energia_e_il_carburante(self):
        """DA1: senza suono la scena rallenta alla veglia (pavimento
        0.12, non 0.5); col suono corre. Tutto il moto autonomo scorre
        su uTime, quindi questa riga governa la danza intera."""
        # DA5: veglia da quadro (3,5%), non passeggiata (12%)
        assert "0.035 + polso.vita * 0.95 * R" in PROTO
        assert "(0.5 + env.l * 1.1 * R)" not in PROTO, \
            "e' tornato il pavimento che faceva ballare il silenzio"

    def test_il_respiro_non_e_piu_un_metronomo_sordo(self):
        """L'ampiezza segue la vita (a silenzio quasi piatto e
        CENTRATO), e se la sessione ha una marea vera il respiro segue
        quella."""
        assert ".5 + (breath - .5) * (0.05 + 0.95 * polso.vita)" in PROTO
        assert "polso.ondaLenta * marea" in PROTO

    def test_il_polso_sente_la_modulazione(self):
        """Il battito delle nostre ricette (binaurale/isochronic) vive
        nella modulazione d'ampiezza 0.3-14 Hz, non nei transienti:
        autocorrelazione dell'inviluppo, con la regola della
        FONDAMENTALE (dal massimo si raddoppia il lag finche' la
        correlazione regge — la sonda ha smentito la preferenza per i
        lag corti: 4.44 stimati su un battito vero a 2.0)."""
        assert "const lagMin = 3, lagMax = 150" in PROTO
        assert "lagMeglio * 2 <= lagMax && acDi[lagMeglio * 2] >= meglio * 0.72" in PROTO
        # e i fotogrammi lenti non sporcano l'inviluppo: interpolazione
        assert "_bustaPrec + (busta - _bustaPrec) * f" in PROTO

    def test_vita_con_autogain_e_pavimento(self):
        """L'energia si normalizza sul brano (autogain), ma col
        pavimento: il rumore di fondo non deve sembrare un concerto."""
        assert "Math.max(_picco * Math.exp(-dt / 12), bands.level, 0.18)" in PROTO

    def test_il_battito_e_movimento_mai_lampeggio(self):
        """ANTI-STROBO: la fase del battito guida geometria e fase
        SPAZIALE (aprirsi, viaggiare, torcersi) — mai la luminanza.
        Una pulsazione luminosa a frequenza da entrainment sarebbe uno
        strobo, e quello e' territorio fotosensibilita'."""
        frag_gal = PROTO.split("const FRAG = `")[1].split("`;")[0]
        frag_man = PROTO.split("const MAND_FRAG = `")[1].split("`;")[0]
        for frag in (frag_gal, frag_man):
            assert "uBeatPhase" not in frag, "il battito e' arrivato alla luce"
        # e nei vertex il battito entra con fase spaziale, non globale
        assert "uBeatPhase*6.28318 - aTheta" in PROTO

    def test_il_colpo_attraversa_la_scena(self):
        """Eventi PROPAGATIVI: il colpo e' un fronte che parte dal
        centro e viaggia (come un gesto attraversa un ballerino), non
        un sobbalzo uniforme. In piu' Ripple EMETTE un anello vero."""
        assert "exp(-abs(rr0 - dtH*9.0)*.45)" in PROTO      # galassia
        assert "exp(-abs((aR0 + aLen*aU) - dtH*10.0)*.5)" in PROTO   # petali
        assert "fronte" in PROTO                             # ripple

    def test_la_luce_sa_se_c_e_vita(self):
        assert "uVita*.34" in PROTO and "uVita*0.28" in PROTO

    def test_la_pausa_e_silenzio_vero(self):
        """DA5, founder: «l'ho messa in pausa e continua a muoversi».
        Il silenzio TOTALE non e' un pianissimo: la vita scende in ~1 s
        (misurato: 0.42 → 0.014 dopo un secondo), non in otto."""
        assert "bands.level < 0.015 ? 1.6 : 0.4" in PROTO

    def test_la_fase_del_battito_non_salta_mai(self):
        """DA5: al confine della fiducia la fase SALTAVA tra il valore
        vivo e 0.25 fisso — uno strappo periodico. La fase integra
        sempre; a sfumare e' l'AMPIEZZA, con una rampa."""
        assert "? polso.fase : 0.25" not in PROTO
        # DA7: la rampa parte da 0.25 e si moltiplica per la profondita'
        assert "(polso.fiducia - 0.25) / 0.3" in PROTO
        assert "uBeatAmp" in PROTO
        # e l'ampiezza sfuma ANCHE negli shader
        assert "* uBeatAmp;" in PROTO

    def test_l_anima_tonale_c_e(self):
        """DA6, founder: «se una musica da bassa diventa sempre piu'
        alta mi aspetto la stessa elevazione nel visual». Il terzo asse
        della musica (COSA suona) entra con tre gesti universali:
        elevazione col registro, slancio con la derivata, zone
        spettrali sulla topologia di ogni forma. Prova strumentale:
        tono 100 Hz → registro 0.19; 1200 Hz → 0.76 (atteso 0.76);
        salita in crossfade → slancio +0.5 nel gesto."""
        assert "uniform float uSpettro[8];" in PROTO
        assert PROTO.count("float spettro(float z){") == 2, \
            "la topologia spettrale deve vivere in ENTRAMBI i vertex"
        assert "reg * 2.6 + uSlancio * 1.5" in PROTO      # elevazione+slancio
        assert "loc*.30*e" in PROTO                        # corone del mandala
        assert "(1.0 - reg*.30)" in PROTO                  # acuto=polvere fine

    def test_il_registro_e_una_tendenza_non_una_nota(self):
        """DA6, founder: «con melodie tranquille tutto scattoso e
        nervoso» — un'elevazione che segue ogni nota sarebbe un
        ascensore impazzito. Il registro insegue lento (tau ~1,8 s):
        e' la tendenza della melodia; la brillantezza resta viva per
        lo scintillio."""
        assert "(1 - Math.exp(-dt / 1.8))" in PROTO
        assert "polso.registro = polso.brillantezza" not in PROTO

    def test_lo_shepard_non_e_un_test_valido(self):
        """Nota di metodo, incisa qui perche' non si ripeta: la
        «discesa infinita» ha il centroide STAZIONARIO per costruzione
        (l'illusione inganna l'orecchio, non l'FFT). Lo slancio si
        verifica con una salita vera (crossfade grave→acuto), mai con
        lo shepard."""
        assert True

    def test_il_mandala_riceve_tutti_gli_uniform_che_dichiara(self):
        """Svista vera (DA5-DA7): i nuovi uniform venivano aggiunti a U
        ma NON a MAND_U — nel mandala valevano ZERO. uRegistro=0
        significa registro -0.5 FISSO: loto schiacciato e scurito,
        battito muto, zone morte — parte degli «scatti senza senso».
        Parita' meccanica: ogni uniform dichiarato in MAND_VERT deve
        stare in MAND_U."""
        dich = PROTO.split("const MAND_VERT = `")[1].split("void main()")[0]
        import re as _re
        nomi = set(_re.findall(r"\bu[A-Z]\w+", dich))
        blocco_u = PROTO.split("const MAND_U = {")[1].split("};")[0]
        mancanti = {u for u in nomi if (u + ":") not in blocco_u}
        assert not mancanti, f"uniform dichiarati ma non forniti al mandala: {mancanti}"

    def test_niente_va_e_vieni_senza_senso(self):
        """DA7, founder: «con musica tranquillissima le forme si
        muovono a scatti avanti e indietro, sempre lo stesso
        movimento». Due porte chiuse: il battito visivo richiede
        fiducia E profondita' della modulazione (un pad con
        periodicita' debole non balla); e l'onda del colpo porta la
        forza del SUO colpo (uHitAmp) — prima era fissa, e ogni
        colpettino lanciava la stessa onda."""
        assert "polso.profondita" in PROTO
        assert "U.uBeatAmp.value = rampa * prof" in PROTO
        assert "U.uHitAmp.value = polso.colpo" in PROTO
        assert PROTO.count("* uHitAmp") >= 4, \
            "un'onda ha perso la forza del suo colpo"

    def test_le_forme_nuove_hanno_il_ballerino_dentro(self):
        """FM3: ogni forma nuova nasce col motore del ciclo DA — zone
        spettrali, battito come fase, e per il Portale il fade dei
        bordi. Non esistono forme «sorde»."""
        for ancora in ("FLOWER", "MERKABA", "TORUS", "OCEAN", "PORTAL"):
            assert ancora in PROTO, f"ramo mancante: {ancora}"
        flower = PROTO.split("FLOWER")[1].split("MERKABA")[0]
        assert "uSlow" in flower and "spettro(zona)" in flower
        merkaba = PROTO.split("MERKABA")[1].split("TORUS")[0]
        assert "beat" in merkaba and "uSlow" in merkaba, \
            "i due tetraedri devono ruotare uno col battito, l'altro con l'onda"
        torus = PROTO.split("TORUS")[1].split("OCEAN")[0]
        assert "uVita" in torus, "il fiume del toro scorre con la vita"
        portal = PROTO.split("PORTAL")[1].split("organic drift")[0]
        assert "fadeForma" in portal, "il tunnel senza fade mostra il riciclo"
        # e il varco resta LENTO: la velocita' del tunnel e' un numero
        # piccolo per scelta (nausea), non un caso
        assert ".026 + uVita*.045" in portal

    def test_il_loto_regge_ogni_prospettiva(self):
        """FM0, founder: «di lato sembra sottile, perde consistenza».
        Tre difese: il dome ha un pavimento (mai lama), la COPPA
        costante (aU^2), lo SPESSORE dei contorni sfalsati in quota."""
        assert "0.62 + 0.38*sin(t*0.15)" in PROTO
        assert "aU*aU * 1.6 * aScale" in PROTO
        assert "(1.0 - aScale) * 0.9" in PROTO

    def test_ogni_forma_ha_la_sua_posa(self):
        """FM4, founder: «le forme piatte partono schiacciate, viste
        di lato». Ogni forma ha un'inquadratura di casa (i dischi
        dall'alto, il loto e il varco in faccia); l'inquadratura
        salvata dall'AUTORE vince sempre."""
        assert "const POSE = [" in PROTO
        blocco = PROTO.split("const POSE = [")[1].split("];")[0]
        from models.frequency_track import VISUAL_MODES
        import re as _re
        terne = _re.findall(r"\[\s*[\d.-]+\s*,\s*[\d.-]+\s*,\s*[\d.-]+\s*\]", blocco)
        assert len(terne) == VISUAL_MODES, \
            f"pose ({len(terne)}) e forme ({VISUAL_MODES}) fuori sincrono"
        # la posa si applica dove la forma cambia, MAI sopra la scelta
        # dell'autore
        assert "if (!inquadra(opz.impostazioni)) posaCamera(S.mode)" in PROTO
        assert PROTO.count("posaCamera(") >= 4   # def + montaggio + setMode + applica

    def test_la_sonda_non_e_rimasta(self):
        assert "__polso" not in PROTO


class TestRitmoAv4bis:
    """«Non sono convinto che si muovano col ritmo» (founder): la
    causa era la TRIPLA lisciatura — analyser, bande, inseguitore."""

    def test_le_bande_grezze_esistono(self):
        assert "grezze:" in ANALISI
        assert "stato.grezze[r.nome] = grezzo" in ANALISI

    def test_una_sola_orecchia(self):
        """DA2: la lisciatura dell'analyser era 0.88 nello strumento e
        0.5 nell'analizzatore prestato — la stessa scena ballava piu' o
        meno nervosa a seconda della porta. Ora e' UN valore, nello
        standard, e nessuno ne scrive altri per conto suo."""
        tab = (FQ_DIR / "visual" / "tabelle.js").read_text()
        assert "export const LISCIATURA_ANALYSER" in tab
        assert "smoothingTimeConstant = LISCIATURA_ANALYSER" in ANALISI
        assert "smoothingTimeConstant = LISCIATURA_ANALYSER" in PROTO
        for src in (ANALISI, PROTO):
            assert not re.search(r"smoothingTimeConstant\s*=\s*[\d.]", src), \
                "qualcuno ha rimesso un numero a mano: due orecchie di nuovo"
        assert "analyser.getByteFrequencyData(freq)" in PROTO

    def test_il_colpo_e_del_polso_su_tutto_lo_spettro(self):
        """DA2: il vecchio rilevatore (salto dei soli bassi) su una
        meditazione non scattava MAI — droni e battiti non hanno
        percussioni. Il colpo ora e' flusso spettrale con soglia
        adattiva: sente anche un cambio di nota."""
        assert "kick > .035" not in PROTO, "e' tornato il rilevatore da percussioni"
        assert "flux" in PROTO and "_fluxMedia * 3.2" in PROTO
        # DA5/DA6: un'onda per frase, non per nota — refrattario, e su
        # musica dolce la soglia assoluta conta piu' della relativa
        assert "_refrattario = 2.2" in PROTO
        assert "+ 0.012" in PROTO
        assert "(0.3 + 0.7 * polso.vita)" in PROTO
        assert "Math.exp(-dt * 4.2)" in PROTO      # il decadimento resta
        assert "MAND_U.uHit.value = hit" in PROTO

    def test_la_camera_respira_col_suono(self):
        """Nella meditazione la camera e' «Breathe»: si avvicina sul
        respiro e sui bassi, invece di girare intorno. Da VC8 respira
        intorno alla distanza SCELTA dall'autore, non a un 28 fisso."""
        assert "cam: 2" in PROTO
        # DA5: lo zoom insegue con tau ~2s — il su-e-giu' che lo
        # stomaco sente era soprattutto la camera sui bassi a 0,25s
        assert "zoomLento += (env.b - zoomLento) * (1 - Math.exp(-dt / 2))" in PROTO
        assert "distBase * (1 - breath*0.10 - zoomLento*0.06*R)" in PROTO
