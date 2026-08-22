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
        assert "uscita = null" in SYNTH
        assert "sess.connect(uscita || ctx.destination)" in SYNTH
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
        blocco = PROTO.split("if (incorporato){")[1][:700]
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
        blocco = PROTO.split("if (incorporato && opz.analizzatore){")[1].split("\n}")[0]
        assert "analyser = opz.analizzatore" in blocco
        assert "new (window.AudioContext" not in blocco
        assert "if (ctxA) ctxA.close()" in PROTO, \
            "il contesto si chiude solo se e' nostro"
        assert "analizzatore: lettore.analyser" in TELA

    def test_le_manopole_di_un_altro_giorno_non_entrano(self):
        """localStorage e' della stanza degli esperimenti: la
        meditazione dev'essere sempre lo stesso ambiente."""
        assert "if (incorporato) return;" in PROTO.split("const save =")[1][:120]
        ramo = PROTO.split("} else {")[1][:200]
        assert "localStorage.getItem('aurya.settings.v2')" in ramo

    def test_lo_scroll_non_viene_rubato(self):
        """Dentro una pagina che si scorre col dito, trascinare la
        scena significa non poter piu' scendere."""
        assert "controls.enableRotate = false" in PROTO
        assert "if (incorporato){ controls.enableRotate" in PROTO

    def test_la_misura_e_la_scatola_non_la_finestra(self):
        assert "function misura()" in PROTO
        assert "if (!incorporato) return { w: innerWidth, h: innerHeight }" in PROTO
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
        """Il segreto musicale del prototipo: l'energia sale in ~0,25s
        e scende in ~2s — il colpo si sente, il rumore no."""
        assert "target > cur ? 4.2 : 0.85" in PROTO

    def test_la_scia_sbiadisce_verso_il_profondo(self):
        """Non verso il nero piatto ma verso un gradiente
        profondo→bordo: e' quello che da' il volume."""
        assert "uDeep" in PROTO and "uEdge" in PROTO
        assert "smoothstep(.05,.72,r)" in PROTO

    def test_l_aura_ha_il_dithering(self):
        """Senza, i gradienti larghi a 8 bit fanno anelli visibili."""
        assert "Math.random()*2-1" in PROTO

    def test_i_sette_modi_ci_sono_tutti(self):
        blocco = PROTO.split("const MODES = [")[1].split("];")[0]
        for nome in ("Breath", "Nebula", "Spiral", "Flow", "Mandala",
                     "Helix", "Ripple"):
            assert f"['{nome}'" in blocco, f"modo perso: {nome}"

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

    def test_il_prototipo_e_integrale(self):
        """I numeri del founder: 11 slider, 6 palette, 7 modi, 7
        preset, 4 camere. Se uno sparisce, il porting ha perso pezzi."""
        assert self.PROTO.count("['") >= 11 and "'intensity','Intensity'" in self.PROTO
        assert self.PROTO.count("{ name:'") >= 13   # 6 palette + 7 preset
        for nome in ("Aurya", "Cosmos", "Anahata", "Prana", "Nirvana",
                     "Kundalini", "Samadhi"):
            assert f"name:'{nome}'" in self.PROTO, f"preset perso: {nome}"
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


class TestRitmoAv4bis:
    """«Non sono convinto che si muovano col ritmo» (founder): la
    causa era la TRIPLA lisciatura — analyser, bande, inseguitore."""

    def test_le_bande_grezze_esistono(self):
        assert "grezze:" in ANALISI
        assert "stato.grezze[r.nome] = grezzo" in ANALISI

    def test_il_motore_beve_da_un_analizzatore_poco_lisciato(self):
        """L'inseguitore asimmetrico del prototipo dev'essere l'UNICA
        lisciatura pesante: l'analizzatore che gli passiamo sta a 0.5,
        non a 0.88, e le bande le calcola lui dai bin grezzi."""
        assert "smoothingTimeConstant = 0.5" in ANALISI
        assert "analyser.getByteFrequencyData(freq)" in PROTO

    def test_il_colpo_del_prototipo_c_e(self):
        """Il salto dei bassi fra due fotogrammi, con decadimento
        rapido: e' il lampo che aggancia la scena al ritmo."""
        assert "Math.exp(-dt*4.2)" in PROTO
        assert "kick > .035" in PROTO
        # e il colpo arriva ai petali del mandala
        assert "MAND_U.uHit.value = hit" in PROTO

    def test_la_camera_respira_col_suono(self):
        """Nella meditazione la camera e' «Breathe»: si avvicina sul
        respiro e sui bassi, invece di girare intorno."""
        assert "cam: 2" in PROTO
        assert "28 - breath*3.5 - env.b*2.2*R" in PROTO
