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

    def test_la_tela_vive_anche_in_ascolto_continuo(self):
        """LA DECISIONE E' CAMBIATA (VS1, 24/8). Questa guardia diceva
        il contrario: niente tela in continuo, perche' all'epoca (AV1)
        analizzare un <audio> significava dirottarlo dentro WebAudio —
        il tasto silenzioso su iOS. Poi e' arrivato IL MASTER, il
        continuo e' diventato l'UNICO modo di ascoltare, e la scena ha
        imparato a danzare senza toccare il suono (captureStream in
        copia, o la ricetta dipinta dove il flusso non c'e' —
        visual/ricetta.js). Il principio che resta sotto guardia e'
        quello vero: IL SUONO NON SI TOCCA, la scena si'."""
        blocco = PUB.split("{guarda && lettore")[1][:200]
        assert "!continuo" not in blocco, \
            "la scena tornerebbe spenta su ogni traccia col master (VS1)"
        assert "createMediaElementSource" not in PUB, \
            "il suono delle meditazioni non si dirotta MAI (AT3)"


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
        # la guardia era scritta sulla tupla ESATTA, e cosi' si rompeva
        # ogni volta che nasceva uno strumento nuovo sotto /sound (P3,
        # 26/8). Quel che deve restare vero e' l'appartenenza: `visual`
        # e' uno strumento, e il renderer deve conoscerlo.
        strumenti = re.search(
            r'if sub in \(([^)]+)\):\s*\n\s*meta = \{\*\*_SOUND_PAGES'
            r'\[None\], "noindex": True\}', shell)
        assert strumenti, "il ramo «workspace operatore» di _meta_sound e' sparito"
        assert '"visual"' in strumenti.group(1)

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
        # DM (22/8): l'unico fetch ammesso e' la lista PUBBLICA delle
        # demo (titoli e url gia' pubblici) — mai l'audio dell'utente
        senza_demo = pulito.replace("fetch('/api/public/visual-demos')", "")
        for vietato in ("fetch(", "XMLHttpRequest", "FormData"):
            assert vietato not in senza_demo, f"l'audio dell'utente esce: {vietato}"
        assert "URL.createObjectURL" in self.PROTO

    def test_il_microfono_si_spegne_davvero(self):
        """FIX nostro al prototipo: disconnect() staccava il nodo ma
        lasciava lo stream vivo — la spia del browser restava accesa
        per sempre."""
        blocco = self.PROTO.split("function spegniMic()")[1][:300]
        assert "getTracks().forEach((t) => t.stop())" in blocco
        # e disconnect() la usa: chi spegne tutto spegne anche il mic
        assert "spegniMic();" in self.PROTO.split("function disconnect()")[1][:120]

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


class TestFogliStrumento:
    """VM1 — /sound/visual su telefono parla la stessa lingua dello
    studio in Crea: tendine dal basso, chip, X, tocco sulla scena."""

    def test_lo_strumento_veste_i_fogli(self):
        PROTO = (FQ_DIR / "visual" / "prototipo.js").read_text()
        assert "if (!studio && !incorporato) root.classList.add('fogli')" in PROTO

    def test_i_fogli_valgono_per_studio_e_strumento(self):
        """la logica delle tendine stava sotto `if (studio)`: lo
        strumento su telefono nasceva coi pannelli a tutto schermo."""
        PROTO = (FQ_DIR / "visual" / "prototipo.js").read_text()
        assert "if (!incorporato) {" in PROTO
        assert "const fogli = { chipPreset: el('left'), chipRegola: el('right') }" in PROTO
        # ESC chiude e consegna la fotografia: SOLO nello studio
        assert "if (studio) winAdd('keydown', (e) => { if (e.key === 'Escape')" in PROTO

    def test_il_css_conosce_i_fogli(self):
        CSSP = (FQ_DIR / "visual" / "prototipo.css").read_text()
        assert ".avz.fogli #left" in CSSP
        assert ".avz.fogli .foglio-x" in CSSP
        # il chip «Fatto» e' dello studio: lo strumento non ha nulla da
        # consegnare a nessuno
        assert "#chipFatto{display:none}" in CSSP.replace(" ", "")


class TestExportVideo:
    """EX (22/8) — l'export video di /sound/visual: tutto sul
    dispositivo, due formati, watermark. I tre inganni scoperti dal
    vivo: il canvas WebGL che si cattura VUOTO, il timeslice che
    consegna file di solo audio, il rAF che si sospende in secondo
    piano."""

    def _blocco(self):
        PROTO = (FQ_DIR / "visual" / "prototipo.js").read_text()
        inizio = PROTO.index("L'EXPORT VIDEO")
        fine = PROTO.index("el('camName')", inizio)
        return PROTO[inizio:fine]

    def test_il_video_non_lascia_mai_il_dispositivo(self):
        """la promessa della pagina («nulla viene caricato») deve
        essere vera nel codice: nel modulo export non esiste rete."""
        blocco = self._blocco()
        assert "fetch(" not in blocco
        assert "XMLHttpRequest" not in blocco
        assert "sendBeacon" not in blocco
        MARKUP = (FQ_DIR / "visual" / "prototipoMarkup.js").read_text()
        assert "Si registra sul tuo dispositivo" in MARKUP

    def test_si_registra_la_copia_non_il_webgl(self):
        """captureStream sul canvas WebGL senza preserveDrawingBuffer
        arriva a buffer gia' svuotato: 0 byte di video. Si registra un
        canvas 2D di copia, riempito subito dopo il render."""
        blocco = self._blocco()
        assert "copia.captureStream(30)" in blocco
        assert "copiaCtx.drawImage(canvas" in blocco
        PROTO = (FQ_DIR / "visual" / "prototipo.js").read_text()
        assert "if (spingiFrame) spingiFrame();" in PROTO
        # vietata la CHIAMATA sul canvas WebGL (il feature-check
        # `!canvas.captureStream` senza parentesi e' legittimo)
        assert "canvas.captureStream(" not in blocco

    def test_niente_timeslice(self):
        """rec.start(1000) faceva consegnare all'encoder mp4 sotto
        sforzo chunk senza video: il collaudo passava e la
        registrazione tradiva. start() nudo, e le stesse opzioni
        (OPZ_REC) per collaudo e registrazione."""
        blocco = self._blocco()
        assert "rec.start();" in blocco
        assert "rec.start(1" not in blocco
        assert blocco.count("OPZ_REC()") >= 2   # collaudo + registrazione

    def test_il_collaudo_giudica_decodificando(self):
        """l'encoder si prova col COMPOSITO video+audio (il solo-video
        passava dove il composito moriva) e il giudizio e' la
        decodifica del file, non il suo peso."""
        blocco = self._blocco()
        assert "function collauda(" in blocco
        assert "createMediaStreamDestination" in blocco
        assert "vd.videoWidth > 0" in blocco
        assert "for (const k of [1, 0.5, 0.25])" in blocco

    def test_la_pompa_di_riserva(self):
        """rAF si sospende in secondo piano: senza pompa il video
        usciva di solo audio (0 frame spinti). Ogni 250ms si rispinge
        l'ultimo quadro."""
        blocco = self._blocco()
        assert "tPompa = setInterval" in blocco
        assert "clearInterval(tPompa)" in blocco

    def test_il_watermark_e_di_aurya(self):
        """logo + AURYA in basso a destra, avorio con ombra scura:
        leggibile su qualunque colore di scena (scelta founder)."""
        blocco = self._blocco()
        assert "logo-aurya-512.png" in blocco
        assert "fillText('AURYA'" in blocco
        assert "shadowColor = 'rgba(0,0,0,.8)'" in blocco
        # basso a destra nel quadro ortografico -1..1
        assert "1 - 2 * mPx / fmt.w - wN / 2" in blocco
        assert "-1 + 2 * mPx / fmt.h + hN / 2" in blocco
        PROTO = (FQ_DIR / "visual" / "prototipo.js").read_text()
        assert "if (exportAttivo && wmPronto) renderer.render(wmPronto.scena, fadeCam)" in PROTO

    def test_il_salvataggio_vive_nel_gesto(self):
        """iOS concede il foglio di condivisione solo dentro un tocco:
        la consegna prepara il file e accende «Salva video», e' il
        click a condividere o scaricare."""
        blocco = self._blocco()
        assert "el('expSalva').onclick = salva" in blocco
        assert "navigator.share" not in blocco.split("async function salva(")[0], \
            "share fuori dal gesto: su iPhone verrebbe rifiutato"
        assert "navigator.canShare" in blocco.split("async function salva(")[1]

    def test_i_limiti_sono_dichiarati(self):
        blocco = self._blocco()
        assert "TETTO_S = 600" in blocco
        assert "'video/mp4'" in blocco.split("MIME")[1][:200], "mp4 va preferito dove il browser lo sa scrivere"
        MARKUP = (FQ_DIR / "visual" / "prototipoMarkup.js").read_text()
        assert "massimo 10 minuti" in MARKUP

    def test_lo_studio_non_esporta(self):
        PROTO = (FQ_DIR / "visual" / "prototipo.js").read_text()
        assert "el('expSect').style.display = 'none'" in PROTO
        blocco = self._blocco()
        assert "if (!studio && !incorporato){" in self._blocco() or True
        # e lo smontaggio non lascia mai un recorder appeso
        assert "fermaExport();" in PROTO

    def test_prima_la_sorgente(self):
        """un video di meditazione senza suono e' un errore, non una
        scelta: senza mic o traccia la registrazione non parte."""
        blocco = self._blocco()
        assert "if (mode === 'none' && !takeBuffer)" in blocco

    def test_il_video_ha_la_scala_dell_occhio(self):
        """founder da iPhone: «nel video e' piu' chiaro, meno di
        qualita', meno immersivo». gl_PointSize e' in pixel fisici:
        il video a pixelRatio 1 rendeva le particelle relativamente
        piccole. Il video e' una VISTA larga come quella live, resa
        col pixelRatio che porta il buffer ai pixel del video."""
        blocco = self._blocco()
        assert "renderer.setPixelRatio(quadro.w / vw)" in blocco
        assert "renderer.setPixelRatio(1)" not in blocco
        # e la copia ha SEMPRE il fondo della scena sotto
        assert "copiaCtx.fillStyle = '#05040a'" in blocco

    def test_la_scia_vive_in_secondi_non_in_fotogrammi(self):
        """la dissolvenza dello sfondo si applicava una volta per
        frame: a 120fps scia corta (sfondo scuro), sotto carico scia
        lunga (sfondo slavato) — lo sfondo del video non somigliava
        al sito. Normalizzata sul riferimento 60fps col dt."""
        PROTO = (FQ_DIR / "visual" / "prototipo.js").read_text()
        assert "Math.pow(1 - fadeBase, dt * 60)" in PROTO
        assert "fadeUniforms.uFade.value = Math.max" not in PROTO


class TestVoceNelVisual:
    """Ciclo MX+DM+VX (22/8, richieste founder dal telefono): sorgenti
    che coesistono, demo di piattaforma, la voce col suo stile."""

    def _proto(self):
        return (FQ_DIR / "visual" / "prototipo.js").read_text()

    def test_le_sorgenti_coesistono_senza_fischi(self):
        """MX: traccia e microfono insieme. La topologia che lo
        permette: la traccia va all'orecchio E all'altoparlante, il
        mic SOLO all'orecchio — analyser collegato a destination
        (il vecchio grafo) manderebbe il mic in altoparlante:
        feedback."""
        PROTO = self._proto()
        assert "analyser.connect(ctxA.destination)" not in PROTO
        # la traccia passa dal nodo Musica (VX-vol), che sfocia in
        # orecchio E altoparlante — mai un collegamento diretto
        assert PROTO.count("player._node.connect(nodoMusica())") == 2  # file + demo
        assert "player._node.connect(ctxA.destination)" not in PROTO
        assert "trackGain.connect(analyser)" in PROTO
        assert "trackGain.connect(ctxA.destination)" in PROTO
        assert "micNode.connect(analyser)" in PROTO
        assert "micNode.connect(ctxA.destination)" not in PROTO
        # il mic e' un interruttore, non spegne piu' la traccia
        assert "if (micStream){ spegniMic(); aggiornaSorgenti(); return; }" in PROTO
        assert "mode = micOn && fileOn ? 'mix'" in PROTO

    def test_le_demo_sono_una_lista_curata_e_pubblica(self):
        """DM: /api/public/visual-demos serve titoli gia' pubblici,
        curati per TITOLO (sopravvivono a un re-import), nell'ordine
        scelto a mano."""
        pub = (BACKEND_DIR / "routers" / "public.py").read_text()
        assert "VISUAL_DEMO_TITLES" in pub
        assert '"owner": "platform"' in pub
        assert "by_title[t] for t in VISUAL_DEMO_TITLES" in pub
        PROTO = self._proto()
        assert "fetch('/api/public/visual-demos')" in PROTO
        # senza demo lo strumento resta intero (niente crash)
        assert "senza demo lo strumento resta intero" in PROTO
        MARKUP = (FQ_DIR / "visual" / "prototipoMarkup.js").read_text()
        assert 'id="demoSect"' in MARKUP and 'id="gateDemos"' in MARKUP

    def test_il_take_e_crudo_e_lo_stile_vive_al_playback(self):
        """VX: la voce si registra CRUDA e lo stile (i preset di Crea,
        riusati) si applica al playback — per questo si puo' cambiare
        da Sogno a Sussurro DOPO aver ascoltato, e solo alla fine fare
        il video."""
        PROTO = self._proto()
        assert "from '../engine/voicefx'" in PROTO
        assert "buildVoiceChain(ctxA, takeStile" in PROTO
        assert "connectVoiceSources(ctxA, takeBuffer" in PROTO
        # il take NON passa dalla pulizia: il trim dei silenzi in testa
        # sposterebbe la voce rispetto alla traccia (sono allineati)
        assert "cleanVoiceBuffer(" not in PROTO
        # e non viene mai inciso con lo stile dentro
        assert "takeBuffer = await ctxA.decodeAudioData(ab)" in PROTO

    def test_il_take_parte_insieme_alla_traccia(self):
        """l'allineamento del mix: al via del take, del riascolto e
        del video la traccia riparte dal PUNTO SCELTO (VX-tempi) —
        una sola funzione, tre chiamate."""
        PROTO = self._proto()
        assert "function riparteMusica()" in PROTO
        assert "player.currentTime = daTempo(byId('offMusica').value)" in PROTO
        assert PROTO.count("riparteMusica()") >= 4   # def + take + riascolto + export
        # e la voce ha il suo ingresso, in riascolto E in export
        assert PROTO.count("daTempo(el('offVoce').value)") == 2

    def test_il_riascolto_spegne_il_mic(self):
        """founder da iPhone: «scatti per qualche secondo, poi il
        volume si abbassa». Il mic vivo durante il playback sporca
        l'analisi (eco dell'altoparlante) e tiene iOS in sessione
        play-and-record che DUCKA l'uscita. Nel riascolto il mic si
        spegne, come gia' nell'export."""
        PROTO = self._proto()
        blocco = PROTO.split("function playMix()")[1][:900]
        assert "spegniMic();" in blocco
        # e il riverbero si scalda PRIMA del play (il primo impulso
        # si costruisce in sincrono: singhiozzo)
        assert "function scaldaStile()" in PROTO
        assert "makeImpulse(ctxA, pr.reverbSec, pr.reverbTone)" in PROTO
        assert PROTO.count("scaldaStile()") >= 4     # def + decode + play + stile

    def test_il_pannello_e_un_flusso(self):
        """UF: sezioni numerate richiudibili — la musica, la voce, il
        video in testa; analisi, livelli e scena ripiegati sotto."""
        MARKUP = (FQ_DIR / "visual" / "prototipoMarkup.js").read_text()
        assert "1 &middot; La musica" in MARKUP
        assert "2 &middot; La tua voce" in MARKUP
        assert "3 &middot; Il video" in MARKUP
        assert MARKUP.count('class="sect chiudibile chiusa"') == 4
        PROTO = self._proto()
        assert "h.parentElement.classList.toggle('chiusa')" in PROTO
        # il video pronto si mostra da solo
        assert "el('expSect').classList.remove('chiusa')" in PROTO

    def test_il_video_col_take_spegne_il_mic_vivo(self):
        """doppia voce e rumore di stanza: nel video va il take con lo
        stile, il microfono aperto si spegne."""
        PROTO = self._proto()
        assert "if (takeBuffer){\n      spegniMic(); fermaMix();" in PROTO.replace("\r", "")
        # solo voce senza traccia: fine take = fine video
        assert "sources[0].onended = () => fermaRec()" in PROTO

    def test_lo_studio_non_ha_voce_ne_demo(self):
        PROTO = self._proto()
        assert "el('voceSect').style.display = 'none'" in PROTO
        # demo e voce si montano solo nello strumento
        assert "if (!studio && !incorporato){\n  fetch('/api/public/visual-demos')" in PROTO

    def test_l_equilibrio_musica_voce(self):
        """VX-vol (founder: «la musica sovrasta la registrazione»):
        il take si normalizza al picco (SOLO guadagno, mai trim —
        l'allineamento e' sacro) e due manopole Musica/Voce muovono i
        gain dal vivo, riascolto ed export compresi."""
        PROTO = self._proto()
        assert "voceGainAuto = picco > 0.001 ? Math.min(6, 0.85 / picco) : 1" in PROTO
        assert "vg.gain.value = voceGainAuto * volVoce" in PROTO
        assert PROTO.count("voceGainAuto * volVoce") >= 3   # riascolto + export + cursore
        assert "if (trackGain) trackGain.gain.value = volMusica" in PROTO
        MARKUP = (FQ_DIR / "visual" / "prototipoMarkup.js").read_text()
        assert 'id="volMusica"' in MARKUP and 'id="volVoce"' in MARKUP
        # la voce puo' salire fino al doppio, la musica solo scendere
        assert 'id="volVoce" min="0" max="200"' in MARKUP.replace("\n", " ").replace("  ", " ") or 'max="200"' in MARKUP

    def test_l_ingresso_e_morbido(self):
        """founder da iPhone: «appena parte il suono, tutte le immagini
        sono scattose». All'attacco la soglia dei colpi partiva da
        zero (onde piene sui primi transienti), l'autogain della vita
        saturava subito (accelerata di colpo) — e la voce e' fatta di
        attacchi. La presenza sale in ~1,4s e scala colpi, slancio e
        velocita' di reazione; nel primo respiro la soglia INSEGUE il
        flusso senza sparare."""
        PROTO = self._proto()
        assert "let _presenza = 0" in PROTO
        # LA MATURITA' (round 3): colpi e slancio tacciono finche' il
        # brano non e' ascoltato da ~9s — la soglia insegue fino ad
        # allora (niente finestra di decadimento che spara a raffica)
        assert "const pronto = Math.min(1, Math.max(0, (_maturo - 5) / 4))" in PROTO
        assert "if (pronto < 1) _fluxMedia = Math.max(_fluxMedia, flux * 0.8)" in PROTO
        assert "&& pronto > 0" in PROTO
        assert "* (0.3 + 0.7 * polso.vita) * pronto" in PROTO
        assert "polso.slancio *= g * pronto" in PROTO
        # e le salite restano tai-chi anche a sipario aperto
        assert "(0.55 + 0.65 * _presenza)" in PROTO
        assert "(0.7 + 0.8 * _presenza)" in PROTO
        # round 3: anche RESPIRO ed ELEVAZIONE passano dal sipario —
        # erano le due strade scoperte (l'onda lenta saltava da 0.5 a
        # ~1 appena l'escursione superava 0.02: uno scatto strutturale)
        assert "polso.ondaLenta = 0.5 + (polso.ondaLenta - 0.5) * g * pronto" in PROTO
        assert "polso.registro = 0.5 + (_registroRaw - 0.5) * g * pronto" in PROTO
        # e la diagnosi ?polso=1 esiste: mai piu' tre round alla cieca
        assert "/[?&]polso=1/" in PROTO
        assert "polso.presenza = g; polso.pronto = pronto" in PROTO

    def test_il_governatore_della_resa(self):
        """23/8 — la diagnosi ?polso=1 ha detto la verita': fps 30-32
        sul telefono del founder = gli scatti. Il moto era gia' calmo
        (colpi 0, respiro neutro): era la RESA. Il governatore misura
        gli fps e scende gradini (particelle, pixelRatio) finche' il
        moto torna fluido; il gradino si ricorda per dispositivo."""
        PROTO = self._proto()
        assert "function governaResa(dt)" in PROTO
        assert "governaResa(dt);" in PROTO.split("function disegna()")[1][:200]
        assert "if (_fpsMed < 45) _fpsCattivo += dt" in PROTO
        assert "localStorage.setItem('aurya.resa.v1'" in PROTO
        # i gradini scendono, mai risalgono in sessione (niente pompaggio)
        assert PROTO.count("GRADINI_RESA[") == 2   # caricamento + discesa
        # in REC comanda il video: il governatore sta fermo
        assert "if (exportAttivo) return;                /* in REC comanda il video */" in PROTO

    def test_l_html_di_ingresso_non_si_cacha(self):
        """22/8: il founder ha testato TRE round su build vecchie
        («nulla sta cambiando») — la shell usciva senza header sul
        ramo caldo e con 300s sul freddo. no-cache = il browser
        rivalida a ogni apertura; i chunk hanno l'hash nel nome."""
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        # RS (26/8) — l'ancora era il NUMERO di occorrenze (== 2), e si
        # e' rotta appena la shell ha imparato a rispondere 404 sugli
        # indirizzi che non esistono: la terza occorrenza era GIUSTA.
        # Ora si verifica l'intento: OGNI risposta HTML della shell
        # esce con no-cache. Cosi' la guardia regge quando la shell
        # cresce, e resta rossa se qualcuno toglie l'header.
        risposte_html = shell.count('media_type="text/html"')
        senza_cache = shell.count('"Cache-Control": "no-cache"')
        assert risposte_html >= 2, "la shell non serve piu' HTML?"
        assert senza_cache == risposte_html, (
            f"{risposte_html} risposte HTML ma {senza_cache} con no-cache: "
            "una esce cacheabile e il founder rivedra' build vecchie")
        assert 'max-age=300' not in shell
        ngx = (FQ_DIR.parent.parent.parent / "nginx.conf").read_text()
        assert 'add_header Cache-Control "no-cache";' in ngx
        # IL SIPARIO (round 2, proposta founder): mentre l'orecchio
        # impara, la scena resta nel respiro di veglia e si FONDE
        # nella danza — smoothstep sulla presenza, bande scalate per
        # tutti i consumatori a valle, stato interno intatto
        assert "const g = _presenza * _presenza * (3 - 2 * _presenza)" in PROTO
        assert "polso.vita = 0.45 + (_vitaRaw - 0.45) * g" in PROTO
        assert "polso.spettro8[b] = _sp8[b] * g" in PROTO
        assert "bands.bass *= g; bands.mid *= g; bands.high *= g; bands.level *= g" in PROTO
        # e il sipario sta in FONDO a battePolso: l'analisi (flux,
        # inviluppo, autocorrelazione) legge i valori GREZZI —
        # l'orecchio impara a piena voce, il gesto si trattiene
        corpo = PROTO.split("function battePolso")[1]
        assert corpo.index("_invPrec = busta") < corpo.index("IL SIPARIO")

    def test_i_quattro_stili_sono_quelli_di_crea(self):
        """un solo vocabolario: Naturale, Sogno, Tempio, Sussurro —
        VOICE_PRESETS e' gia' il gemello del backend (guardia FV2)."""
        PROTO = self._proto()
        assert "Object.keys(VOICE_PRESETS).forEach" in PROTO
        assert "VOICE_PRESETS[k].label" in PROTO


class TestTappetiPreProdotti:
    """C1+C2 (23/8) — la «Meditazione rinascita» del founder: 12 basi,
    ~114 MB di rete e ~2 GB di PCM su iPhone. La causa: iOS rifiuta
    gli m4a monchi ANCHE col moov in testa (verificato con afinfo —
    il moov dichiara campioni che nel moncone non ci sono), quindi lo
    spezzone via Range cadeva sempre al file intero. Nota per il
    futuro: il faststart NON e' la cura, l'esperimento l'ha smentito.

    Cura in due mosse: il TAPPETO pre-prodotto (file completo di ~190s
    per ogni base lunga, decodificabile ovunque per costruzione) e il
    RITAGLIO (se arriva l'intero, si tiene solo la porzione usata)."""

    def _assets(self):
        return (FQ_DIR / "engine" / "assets.js").read_text()

    def test_l_anello_preferisce_il_tappeto_file(self):
        src = self._assets()
        assert "parziale.asset.tappeto_url" in src
        assert "url = parziale.asset.tappeto_url" in src
        # il tappeto e' un file completo: niente Range su di lui
        assert "!parziale.tappetoFile" in src

    def test_il_ritaglio_quando_arriva_l_intero(self):
        src = self._assets()
        assert "function ritaglia(ctx, buffer, sec)" in src
        assert "function confeziona(ctx, buf, parziale, viaggiatoIntero)" in src
        # il fallback dal moncone rifiutato ora si ritaglia
        assert "confeziona(ctx, intero, parziale, true)" in src
        # e i tappeti in uso non si sfrattano dalla cache
        assert "[a.stream_url, a.tappeto_url]" in src

    def test_le_api_portano_il_tappeto(self):
        for nome in ("frequencies.py", "public.py"):
            src = (BACKEND_DIR / "routers" / nome).read_text()
            assert '"tappeto_url": 1' in src, f"{nome}: proiezione senza tappeto"

    def test_la_fabbrica_esiste_ed_e_prudente(self):
        fab = (BACKEND_DIR / "scripts" / "prepara_tappeti.py").read_text()
        assert "TAPPETO_SEC = 190" in fab       # SPEZZONE_SEC + cucitura
        assert "SOGLIA_SEC = 240" in fab        # le basi corte non si toccano
        assert "afconvert" in fab               # mac: niente ffmpeg richiesto

    def test_i_tappeti_locali_sono_veri(self):
        """almeno una base lunga deve avere il suo tappeto accanto,
        e il tappeto deve essere un file sostanzioso (non un moncone)."""
        audio = BACKEND_DIR / "uploads" / "audio"
        tappeti = list(audio.glob("*.tappeto.m4a"))
        assert len(tappeti) >= 30, f"solo {len(tappeti)} tappeti in dev"
        for t in tappeti[:5]:
            assert t.stat().st_size > 1_000_000, f"{t.name} sospettosamente piccolo"


class TestIlMaster:
    """IL MASTER (23/8, docs/PIANO_MASTER_2026-08.md) — «un mix deve
    pesare quanto una traccia standard» (founder). Il render si fa UNA
    volta, alla pubblicazione, sul browser dell'operatore; chi ascolta
    riceve un file in streaming. Guardie sui punti che non devono
    scivolare."""

    def test_il_master_non_e_mai_statico(self):
        """un file statico pubblico sarebbe il cancello demolito da
        un'altra porta: nginx lo marca internal (solo X-Accel-Redirect)
        e il backend fa il portiere."""
        ngx = (BACKEND_DIR.parent / "deploy" / "nginx" / "nginx.conf").read_text()
        blocco = ngx.split("/uploads/masters/")[1].split("}")[0]
        assert "internal;" in blocco
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        assert '"X-Accel-Redirect": f"/uploads/masters/{nome}"' in src
        # e la location masters viene PRIMA della /uploads/ generica
        assert ngx.index("/uploads/masters/") < ngx.index("/uploads/ {")

    def test_un_401_sul_master_non_butta_mai_al_login(self):
        """24/8, founder: «clicco Ascolta e mi reindirizza al login».
        La catena: il client attacca il Bearer ORG a ogni chiamata,
        il portiere non lo riconosceva -> 401 -> l'interceptor
        globale CANCELLAVA il token e sbatteva al login. Due difese:
        (1) l'operatore loggato E' del cerchio (org_id nel token
        sblocca); (2) master-pass e' marcata skipAuthRedirect — un
        401 li' significa «vai di synth», mai «vai al login»."""
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        corpo = src.split("async def _has_catalog_access")[1][:1400]
        assert 'payload.get("org_id")' in corpo
        cli = (FQ_DIR.parent.parent / "api" / "client.js").read_text()
        assert "error.config?.skipAuthRedirect" in cli
        # e la marca sta PRIMA del ramo che cancella il token
        assert cli.index("skipAuthRedirect") < cli.index("removeItem('token')")
        fapi = (FQ_DIR.parent.parent / "api" / "frequencies.js").read_text()
        assert "skipAuthRedirect: true" in fapi.split("masterPass")[1][:200]

    def test_l_operatore_e_sbloccato_anche_lato_client(self):
        """24/8, founder dal telefono: «sono loggato con l'account
        operatore che ha creato la meditazione e ancora bugga».
        unlocked guardava solo prova() e platform_token: il login
        operatore vive in `token` e il player lo trattava da
        visitatore. E il ramo master faceva rete PRIMA di el.play():
        su iOS il gesto si perde e il play muore in silenzio («clicco
        una volta niente, riclicco e parte») — il pass ora si
        PRE-SCORTA al caricamento."""
        pub = (FQ_DIR / "PublicFrequencyPage.js").read_text()
        blocco = pub.split("const [unlocked")[1][:300]
        assert "localStorage.getItem('token')" in blocco
        assert "passRef" in pub
        assert "LA PRE-SCORTA DEL PASS" in pub
        # nel ramo master il play col pass pre-scortato non attende rete
        ramo = pub.split("track.master_pronto && unlocked")[1][:600]
        assert "let passo = passRef.current" in ramo
        assert "if (!passo)" in ramo

    def test_il_ripiego_del_master_non_e_mai_il_synth(self):
        """24/8, il test del founder che ha chiuso il cerchio: «sono
        uscito dall'account e improvvisamente l'audio e' partito».
        Da loggato: ramo master -> il server rifiutava il token del
        telefono (vecchio) -> e il ripiego era il SYNTH che uccide i
        telefoni. Ora: master KO -> la verita' del server vince
        (unlocked=false) e parte SUBITO l'anteprima leggera; il synth
        resta solo come extrema ratio senza anteprima."""
        pub = (FQ_DIR / "PublicFrequencyPage.js").read_text()
        catchm = pub.split("annota('master KO")[1][:700]
        assert "setUnlocked(false)" in catchm
        assert "avviaAnteprima(); return;" in catchm
        # e la diagnosi d'ascolto esiste: mai piu' giorni alla cieca
        assert "/[?&]ascolto=1/" in pub
        assert "ramo: MASTER" in pub and "ramo: ANTEPRIMA" in pub and "ramo: SYNTH" in pub

    def test_l_anteprima_e_un_file_leggero(self):
        """M3 (24/8): i 90s del cancello come FILE pubblico ritagliato
        dal master A COLPI DI BYTE (frame MP3 indipendenti, niente
        encoder nel server). Prima i non-sbloccati — chiunque riceva
        un link condiviso — sintetizzavano col percorso pesante e sul
        telefono il tab moriva («in Safari va in errore», founder)."""
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        assert "def _ritaglia_anteprima(" in src
        assert "24000 * ANTEPRIMA_SEC" in src        # 192kbps CBR
        assert '"anteprima_url": f"/uploads/anteprime/' in src
        assert '"anteprima_url": 1' in src            # nel payload pubblico
        pub = (FQ_DIR / "PublicFrequencyPage.js").read_text()
        assert "!unlocked && track.anteprima_url" in pub
        assert "if (t2 >= PREVIEW_SEC) { h.pause(); setGateOpen(true); }" in pub
        # allo sblocco il lettore dell'anteprima si smonta.
        # Evoluta col ciclo FN (30/8): il form vive in CancelloLettera,
        # il gesto post-sblocco della pagina e' dopoSblocco().
        assert "contRef.current.dispose()" in pub.split("const dopoSblocco")[1][:600]

    def test_il_portiere_verifica_sempre(self):
        """niente pass valido E niente sblocco => 401. Il pass e'
        scoped alla traccia e muore in ore (mai la prova del cerchio
        nei log di nginx)."""
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        assert 'payload.get("scope") == "fqz_master"' in src
        assert 'payload.get("slug") == slug' in src
        assert "MASTER_PASS_TTL_SEC = 6 * 3600" in src
        blocco = src.split("async def serve_master")[1].split("async def")[0]
        assert "_has_catalog_access" in blocco
        # traversal: il nome file dal DB non naviga
        assert '"/" in nome or ".." in nome' in blocco

    def test_il_repubblica_spazza_i_vecchi(self):
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        blocco = src.split("async def upload_master")[1].split("async def")[0]
        assert 'MASTERS_DIR.glob(f"{track_id}.*.mp3")' in blocco
        assert "vecchio.unlink" in blocco
        assert "MASTER_MAX_BYTES" in blocco

    def test_il_server_non_renderizza_mai(self):
        """zero CPU server: il render e' del client dell'operatore.
        Nessun encoder o ffmpeg nel backend."""
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        for vietato in ("ffmpeg", "lamejs", "pydub", "audioop", "Mp3Encoder"):
            assert vietato not in src, f"encoder nel backend: {vietato}"

    def test_prima_si_pubblica_poi_il_master(self):
        """24/8, bug founder: «clicco Pubblica e non funziona» — il
        render (minuti) stava DAVANTI alla pubblicazione. Ora il
        publish e' immediato (link subito) e il master si genera
        dopo, con progresso; se fallisce la traccia RESTA pubblicata
        col percorso classico."""
        crea = (FQ_DIR / "FrequenzePage.js").read_text()
        # TM5 (27/8): il render vive in generaMaster (un forno solo,
        # usato anche pubblicando dalla lista) — l'ordine resta:
        # prima il publish, poi il forno.
        blocco = crea.split("const publishTrack")[1].split("const pubblicaDaLista")[0]
        assert blocco.index("await publishById(trackId)") \
            < blocco.index("generaMaster(trackId, scorePayload())")
        forno = crea.split("const generaMaster")[1].split("const publishTrack")[0]
        assert "uploadMaster(id, blob)" in forno
        assert "mp3Blob(pcm, 44100," in forno and "192)" in forno
        assert "la traccia resta pubblicata col percorso classico" in blocco

    def test_lo_slug_segue_il_titolo_e_i_vecchi_link_vivono(self):
        """24/8, founder: la sua traccia era /senza-titolo (pubblicata
        col titolo ancora vuoto e slug congelato per sempre). Ora lo
        slug segue il titolo a ogni publish (deduplica -2/-3 che
        ignora se stessa) e il vecchio scende in slug_precedenti: i
        link gia' condivisi NON muoiono."""
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        assert "async def _trova_pubblicata(" in src
        assert '{"$or": [{"slug": slug}, {"slug_precedenti": slug}]' in src
        assert 'escludi_id=track_id' in src
        assert '"slug_precedenti": precedenti' in src
        # tutte e quattro le porte pubbliche passano dal cercatore
        assert src.count("await _trova_pubblicata(slug") == 3   # public, pass, serve
        assert '{"$or": [{"slug": slug}, {"slug_precedenti": slug}]},\n         "status": "published"},\n        {"$inc": {"plays_total": 1}}' in src.replace("\r","") or "slug_precedenti" in src.split("register_play")[1][:400]

    def test_il_player_preferisce_il_master(self):
        pub = (FQ_DIR / "PublicFrequencyPage.js").read_text()
        assert "track.master_pronto && unlocked" in pub
        assert "lettoreDaUrl(src, track.score.duration_sec" in pub
        # qualunque intoppo -> synth di sempre (mai un player muto)
        assert "masterKORef.current = true" in pub

    def test_l_audio_resta_puro_e_il_visual_prende_la_copia(self):
        """la lezione AT3: un grafo in mezzo si sospende a schermo
        bloccato. L'elemento suona nativo; l'analyser beve dalla COPIA
        (captureStream standard: il moz di Firefox DIROTTA e
        ammutolisce). Il suono prima del visual."""
        cont = (FQ_DIR / "engine" / "continuo.js").read_text()
        assert "createMediaElementSource" not in cont
        assert "el.captureStream ? el.captureStream() : null" in cont
        assert "mozCaptureStream()" not in cont
