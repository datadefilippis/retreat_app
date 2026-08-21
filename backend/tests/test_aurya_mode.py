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
        """Due vie (motore 3D e rete 2D), due pulizie: la via 3D fa
        dispose del motore, la 2D spegne raf/timer/listener."""
        assert "motoreRef.current.dispose()" in TELA
        assert "_pulisci?.()" in TELA
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


MOTORE = (FQ_DIR / "visual" / "motore3d.js").read_text()


class TestMotoreImmersivoAv4:
    """
    AV4 — il motore WebGL, adattato dal concept HTML del founder
    (Three.js, 7 modi nel vertex shader). I trucchi buoni portati
    com'erano; le regole di casa applicate senza sconti.
    """

    def test_three_entra_solo_quando_si_guarda(self):
        """Three pesa ~500KB: nel main sarebbe un dazio per chiunque
        apre QUALSIASI pagina. Import dinamico, solo qui."""
        assert "import('./motore3d')" in TELA
        assert "from 'three'" not in TELA
        assert "from 'three'" in MOTORE   # l'unico posto

    def test_il_motore_non_tocca_l_audio(self):
        pulito = _senza_commenti(MOTORE)
        for vietato in ("createAnalyser", "AudioContext", "getByteFrequencyData"):
            assert vietato not in pulito, f"il motore tocca l'audio: {vietato}"
        assert "lettore.leggi()" in MOTORE, \
            "l'audio deve arrivare dall'unica verita' (analisi.js)"

    def test_le_triadi_sono_di_marca(self):
        """Ombra→corpo→luce, ma la TINTA e' quella della famiglia: le
        ombre sono derivate scure degli accenti, dichiarate una volta."""
        for hex_ in ("#C9B37E", "#66B79C", "#9B8BC4"):
            assert hex_ in MOTORE, f"manca il corpo di marca {hex_}"
        trovati = set(re.findall(r"#[0-9A-Fa-f]{6}", MOTORE))
        ammessi = {"#241D10", "#C9B37E", "#F2E7C8",      # triade oro
                   "#0E2620", "#66B79C", "#DFF5EC",      # triade acqua
                   "#1B1630", "#9B8BC4", "#EFE9FA",      # triade viola
                   "#0E1B1E", "#070E10"}                 # fondale
        assert trovati <= ammessi, f"colori fuori famiglia: {trovati - ammessi}"

    def test_l_inseguitore_e_asimmetrico(self):
        """Il segreto musicale del concept: l'energia sale in ~0,25s e
        scende in ~2s — il colpo si sente, il rumore no. Con un solo
        tempo la scena o trema o dorme."""
        assert "0.25" in MOTORE and "2.0" in MOTORE
        assert "target > cur" in MOTORE

    def test_la_scia_sbiadisce_verso_il_profondo(self):
        """Il concept insegna: non verso il nero piatto ma verso un
        gradiente profondo→bordo. E' quello che da' il volume."""
        assert "uDeep" in MOTORE and "uEdge" in MOTORE
        assert "smoothstep(.05,.72,r)" in MOTORE

    def test_l_aura_ha_il_dithering(self):
        """Senza, i gradienti larghi a 8 bit fanno anelli visibili."""
        assert "Math.random() * 2 - 1" in MOTORE

    def test_i_sette_modi_ci_sono_tutti(self):
        from_file = re.search(r"export const MODI = \[([^\]]+)\]", MOTORE).group(1)
        assert from_file.count("'") == 14, "modi persi o aggiunti di nascosto"
        for u in ("uMode < 0.5", "uMode < 1.5", "uMode < 2.5", "uMode < 3.5",
                  "uMode < 4.5", "uMode < 5.5"):
            assert u in MOTORE, f"ramo del vertex shader mancante: {u}"

    def test_si_ferma_quando_nessuno_guarda(self):
        assert "visibilitychange" in TELA
        assert "m.ferma()" in TELA

    def test_quiete_significa_niente_galassia(self):
        """prefers-reduced-motion: una galassia che turbina non e'
        «movimento ridotto» per nessuna definizione — si resta sul 2D,
        che in quiete rallenta da solo."""
        blocco = TELA.split("webgl2 =")[1][:80]
        assert "!quieto" in blocco

    def test_dispose_completo(self):
        assert "geo.dispose" in MOTORE and "renderer.dispose" in MOTORE
        assert "dispose()" in TELA


VISUAL = (FQ_DIR / "visual" / "VisualPage.jsx").read_text()


class TestPaginaStrumentoAv2:
    """
    AV2 — /sound/visual: «integrata ma isolata» (founder). Il SUO
    suono, guardato — traccia locale o microfono. La promessa che
    regge tutto: l'audio non lascia mai il dispositivo.
    """

    def test_la_rotta_esiste(self):
        app = (FQ_DIR.parent.parent / "App.js").read_text()
        assert '"/sound/visual"' in app
        assert "visual/VisualPage" in app

    def test_l_ingresso_dalla_landing(self):
        land = (FQ_DIR / "SoundLandingPage.js").read_text()
        assert 'to="/sound/visual"' in land

    def test_la_promessa_privacy_e_scritta_in_pagina(self):
        """Non solo architettura: e' una promessa all'utente, e va
        detta dove carica il file."""
        # il testo JSX va a capo dove vuole: si confronta normalizzato
        piatto = " ".join(VISUAL.split())
        assert "non viene caricato da nessuna parte" in piatto

    def test_la_traccia_non_parte_mai_verso_il_server(self):
        pulito = _senza_commenti(VISUAL)
        for vietato in ("fetch(", "axios", "FormData", "upload"):
            assert vietato not in pulito, \
                f"la pagina tocca la rete con l'audio dell'utente: {vietato}"
        assert "URL.createObjectURL" in VISUAL   # file locale, punto

    def test_il_microfono_non_va_agli_altoparlanti(self):
        """MediaStreamSource → lettore e BASTA: collegarlo a
        destination e' larsen garantito."""
        blocco = VISUAL.split("createMediaStreamSource")[1][:300]
        assert "connect(lettoreRef.current.analyser)" in blocco
        assert "destination" not in blocco

    def test_il_microfono_si_spegne_davvero(self):
        """track.stop(), non pausa: la spia del browser deve spegnersi."""
        assert "getTracks().forEach((t) => t.stop())" in VISUAL

    def test_media_element_source_una_volta_sola(self):
        """createMediaElementSource si puo' chiamare UNA volta per
        elemento: l'elemento e' uno e si cambia solo il src."""
        assert _senza_commenti(VISUAL).count("createMediaElementSource") == 1
        assert "audioElRef.current.src = urlRef.current" in VISUAL

    def test_pulizia_completa_allo_smontaggio(self):
        coda = VISUAL.split("useEffect(() => () => {")[1][:500]
        for pezzo in ("spegniMic", "revokeObjectURL", "close()"):
            assert pezzo in coda, f"lasciato acceso: {pezzo}"


class TestRitmoAv4bis:
    """«Non sono convinto che si muovano col ritmo» (founder): la
    causa era la TRIPLA lisciatura — analyser, bande, inseguitore."""

    def test_le_bande_grezze_esistono(self):
        assert "grezze:" in ANALISI
        assert "stato.grezze[r.nome] = grezzo" in ANALISI

    def test_il_motore_beve_dal_grezzo(self):
        """L'inseguitore asimmetrico dev'essere l'UNICA lisciatura del
        motore: dargli bande gia' lisce = lisciare due volte = scena
        che non segue il colpo."""
        assert "L.grezze || L.bande" in MOTORE
        assert "insegui(env.b, B.bassi" in MOTORE

    def test_il_colpo_del_concept_c_e(self):
        """Il salto dei bassi fra due fotogrammi, con decadimento
        rapido: e' il lampo che aggancia la scena al ritmo."""
        assert "Math.exp(-dt * 4.2)" in MOTORE
        assert "salto > 0.035" in MOTORE
        # e il colpo AVVICINA la camera: la scena viene incontro
        assert "colpo * 1.6" in MOTORE

    def test_lo_zoom_chiesto(self):
        """Base 17 invece di 26: gli elementi riempiono lo schermo."""
        assert "17 - respiro" in MOTORE
        assert "26 - respiro" not in MOTORE
