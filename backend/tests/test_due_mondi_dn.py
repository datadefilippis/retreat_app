"""Ciclo DN (21/8/2026) — due mondi, un marchio.

Il sito e Aurya Sound restano prodotti separati: chiaro per leggere e
scegliere, scuro per ascoltare. Ma «prodotti separati» non vuol dire
«marche separate»: la regola del ciclo e'

    cambia la LUCE, non l'identita'.

Queste guardie tengono le costanti — il marchio, la famiglia degli
accenti, le voci dell'account — e lasciano libera la pelle.

Piano: docs/DUE_MONDI_UN_MARCHIO_2026-08.md
"""
import re
from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
FQ_DIR = FRONTEND_SRC / "features" / "frequenze"
CSS = FQ_DIR / "frequenze.css"
SHELL = FRONTEND_SRC / "features" / "storefront" / "components" / "MarketplaceShell.jsx"


class TestUnSoloMarchioDn1:
    """Prima il nome era «Aurya» in serif minuscolo nel buio e «AURYA»
    in Cinzel maiuscolo sul sito: stesso medaglione, due lockup. E'
    l'unica cosa che non deve mai cambiare tra due prodotti della
    stessa casa."""

    def test_il_lockup_del_buio_e_quello_del_sito(self):
        css = CSS.read_text()
        regola = css.split(".fqz .fqzbrand b{")[1].split("}")[0]
        assert "Cinzel" in regola, "il marchio nel buio non usa il font della marca"
        assert "text-transform:uppercase" in regola
        assert "letter-spacing:.28em" in regola, \
            "tracking diverso da quello del sito: il marchio non combacia"
        assert "var(--lamp)" in regola, "il marchio non e' nell'oro di marca"

    def test_il_marchio_ha_la_misura_del_sito(self):
        """DN6 (21/8, founder) — nel buio il medaglione era 26px contro
        i 36 del sito (h-9) e il nome 17 contro 18: stesso disegno, ma
        piu' piccolo, e a colpo d'occhio e' un altro marchio."""
        topbar = (FQ_DIR / "SoundTopbar.jsx").read_text()
        assert 'width="36" height="36"' in topbar, \
            "il medaglione non ha la misura del sito (h-9 = 36px)"
        shell = SHELL.read_text()
        assert "h-9 w-9" in shell, "cambiata la misura sul sito: riallineare il buio"
        regola = CSS.read_text().split(".fqz .fqzbrand b{")[1].split("}")[0]
        assert "font-size:18px" in regola, "il nome non ha la misura del sito (text-lg)"

    def test_la_testata_parla_con_una_voce_sola(self):
        """Le controindicazioni stanno nella testata accanto alle voci
        del menu: stesso corpo e stesso tracking, altrimenti gridano.
        Restano rosse e bordate — e' un avviso, non una voce."""
        css = CSS.read_text()
        safety = css.split(".fqz .safetybtn{")[1].split("}")[0]
        nav = css.split(".fqz .tb-nav a{")[1].split("}")[0]
        for prop in ("font-size:10px", "letter-spacing:.12em", "text-transform:uppercase"):
            assert prop in safety, f"controindicazioni: manca {prop}"
            assert prop in nav, f"passerella: manca {prop} (le due voci sono divergute)"
        assert "var(--alert)" in safety, "l'avviso ha perso il suo rosso"
        # DN7 — e la MISURA: stessa altezza dell'omino accanto. La
        # testata allinea al centro invece di stirare: con stretch ogni
        # figlio prendeva l'altezza del marchio (52px) e le voci brevi
        # diventavano il doppio dell'omino (salvo dalla sua misura fissa).
        omino = css.split(".fqz .sam-trigger{")[1].split("}")[0]
        alt = re.search(r"height:(\d+)px", omino).group(1)
        assert f"height:{alt}px" in safety, \
            f"controindicazioni non alte come l'omino ({alt}px)"
        # DN8 — e vale per OGNI voce della testata: la forma e' una
        # sola (.tbpill), il colore cambia. «Le mie tracce» era una
        # carta a due righe alta il doppio.
        pill = css.split(".fqz .tbpill{")[1].split("}")[0]
        assert f"height:{alt}px" in pill, \
            f"le voci della testata non sono alte come l'omino ({alt}px)"
        for prop in ("font-size:10px", "letter-spacing:.12em", "text-transform:uppercase"):
            assert prop in pill, f"voce della testata: manca {prop}"
        topbar = [r for r in css.split(".fqz .topbar{")[1:] if "align-items" in r[:80]]
        assert topbar and "align-items:center" in topbar[0][:80], \
            "la testata stira i figli invece di allinearli"

    def test_niente_doppioni_tra_testata_e_menu(self):
        """DN6 — «Esplora meditazioni» e «Per gli operatori» erano carte
        nella testata del workspace: da quando le stesse destinazioni
        vivono nella passerella e nel menu dell'omino, sarebbero due
        modi di dire la stessa cosa nella stessa riga."""
        page = (FQ_DIR / "FrequenzePage.js").read_text()
        testata = page.split("<SoundTopbar")[1].split("</>} />")[0]
        assert 'data-testid="fqz-top-meditazioni"' not in testata
        assert 'data-testid="fqz-pro"' not in testata
        # ma l'invito ai professionisti non sparisce: vive nel menu
        modello = (FRONTEND_SRC / "lib" / "cappelli.js").read_text()
        assert "account-menu-operator-join" in modello

    def test_il_marchio_e_uno_solo_non_ricomposto_a_mano(self):
        """Il lockup vive in SoundTopbar. Se una vista se lo riscrive,
        al primo ritocco i mondi ridivergono — e' esattamente cosi' che
        erano scivolati via."""
        topbar = (FQ_DIR / "SoundTopbar.jsx").read_text()
        assert 'className="fqzbrand"' in topbar
        for f in ("SoundLandingPage.js", "MeditazioniPage.js",
                  "FrequenzePage.js", "PublicFrequencyPage.js"):
            src = (FQ_DIR / f).read_text()
            assert "<SoundTopbar" in src, f"{f}: non usa la testata condivisa"
            assert 'className="fqzbrand"' not in src, \
                f"{f}: ricompone il marchio a mano"


class TestUnaSolaFamigliaDiAccentiDn3:
    """L'acqua era 30 gradi piu' blu del verde Aurya e l'oro 26 punti
    piu' saturo: derive del prototipo, ed erano loro a far sembrare
    «un'altra azienda» la stessa stanza di sera. Il fondo resta scuro:
    si allinea la TINTA, non la luce."""

    ORO_DEL_SITO = "#c9b37e"      # index.css, .gold-rule

    def test_loro_e_lo_stesso_del_sito(self):
        css = CSS.read_text()
        lamp = re.search(r"--lamp:\s*(#[0-9A-Fa-f]{6})", css).group(1)
        assert lamp.lower() == self.ORO_DEL_SITO, \
            f"l'oro del buio ({lamp}) non e' quello della marca"

    def test_il_verde_ha_la_tinta_della_marca(self):
        import colorsys
        css = CSS.read_text()
        water = re.search(r"--water:\s*(#[0-9A-Fa-f]{6})", css).group(1).lstrip("#")
        r, g, b = (int(water[i:i + 2], 16) / 255 for i in (0, 2, 4))
        tinta = round(colorsys.rgb_to_hls(r, g, b)[0] * 360)
        # verde di marca: hsl(158-160, 28%, 30%). Nel buio e' piu'
        # chiaro (serve contrasto), ma la tinta resta la sua.
        assert 150 <= tinta <= 170, \
            f"l'acqua e' a {tinta} gradi: fuori dalla famiglia del verde Aurya"


class TestOminoAncheNelBuioDn2:
    """Chi era loggato entrava in Sound e smetteva di vedersi: niente
    account, niente «Esci». Con preferiti e contenuti riservati e' un
    vuoto, non una scelta estetica."""

    def test_le_voci_vengono_dal_modello_unico(self):
        """Un menu che esiste in un mondo solo diverge dall'altro al
        primo cambiamento: le voci si decidono in lib/cappelli e i due
        mondi le vestono."""
        modello = (FRONTEND_SRC / "lib" / "cappelli.js").read_text()
        assert "export function vociAccount" in modello
        for testid in ("account-menu-my", "account-menu-add-client",
                       "account-menu-signin", "account-menu-signup",
                       "account-menu-gestionale", "account-menu-operator-join"):
            assert testid in modello, f"{testid} non e' nel modello unico"
        buio = (FQ_DIR / "SoundAccountMenu.jsx").read_text()
        chiaro = SHELL.read_text()
        for src, nome in ((buio, "SoundAccountMenu"), (chiaro, "MarketplaceShell")):
            assert "vociAccount" in src, f"{nome} non usa il modello unico"

    def test_chi_e_dentro_puo_uscire_da_qualunque_mondo(self):
        buio = (FQ_DIR / "SoundAccountMenu.jsx").read_text()
        assert 'data-testid="sound-account-logout"' in buio
        assert "esci(" in buio
        # e l'uscita e' la stessa: entrambi i token + la prova del cerchio
        modello = (FRONTEND_SRC / "lib" / "cappelli.js").read_text()
        uscita = modello.split("export function esci")[1]
        assert "PLATFORM_TOKEN_KEY" in uscita and "'token'" in uscita \
            and "scordaProva()" in uscita, \
            "«Esci» non chiude tutta la sessione"

    def test_la_testata_porta_omino_e_passerella(self):
        topbar = (FQ_DIR / "SoundTopbar.jsx").read_text()
        assert "SoundAccountMenu" in topbar, "nel buio non c'e' l'omino"
        # DN4 — la passerella e' corta: in un posto fatto per chiudere
        # gli occhi, l'intero menu del sito sarebbe rumore
        voci = re.findall(r"to: '(/[a-z-]*)'", topbar)
        assert 0 < len(voci) <= 4, f"passerella troppo lunga: {voci}"
        assert "/meditazioni" in voci and "/sound" in voci


class TestLaParentelaEDettaDn5:
    def test_la_landing_dichiara_di_essere_lo_studio_di_aurya(self):
        src = (FQ_DIR / "SoundLandingPage.js").read_text()
        assert 'data-testid="sound-parentela"' in src
        assert "studio di Aurya" in src


class TestInstagramSoc:
    """SOC (21/8, founder) — l'icona Instagram nel sito.

    Sta nella barra di chiusura del footer (© · Privacy · Termini) e
    non tra le «Risorse»: Instagram non e' un contenuto di Aurya, e' il
    canale dove Aurya sta — e un'uscita dal sito appartiene alla fine
    della pagina, non alla testata.
    """

    BRAND = FRONTEND_SRC / "config" / "brand.js"

    def test_l_icona_e_nella_barra_di_chiusura(self):
        src = SHELL.read_text()
        assert 'data-testid="footer-instagram"' in src
        barra = src.split('© {BRAND_NAME}')[1].split("</footer>")[0]
        assert 'data-testid="footer-instagram"' in barra, \
            "l'icona non e' nella striscia d'identita' del footer"
        assert "<Instagram " in src, "e' tornato un link testuale invece dell'icona"

    def test_non_e_ripetuta_nello_stesso_piede(self):
        """Prima viveva anche come link testuale sotto «Risorse»: due
        Instagram nello stesso footer sono rumore. Si contano le RESE,
        non le occorrenze della costante (import e href sono due usi
        legittimi della stessa cosa)."""
        src = SHELL.read_text()
        assert src.count('data-testid="footer-instagram"') == 1, \
            "Instagram e' reso piu' di una volta nel footer"
        risorse = src.split("footerResources")[1].split("</div>")[0]
        assert "BRAND_INSTAGRAM" not in risorse, \
            "e' tornato il doppione testuale tra le Risorse"

    def test_l_uscita_e_sicura_e_ha_un_nome(self):
        """Un link che porta fuori si apre altrove e non passa il
        referrer; un'icona senza testo ha bisogno di un nome per chi
        naviga con lo screen reader."""
        src = SHELL.read_text()
        blocco = src.split('data-testid="footer-instagram"')[0][-400:] \
            + src.split('data-testid="footer-instagram"')[1][:400]
        assert 'target="_blank"' in blocco and "noreferrer" in blocco \
            and "noopener" in blocco
        assert "aria-label" in blocco, "l'icona non ha un nome accessibile"

    def test_niente_indirizzo_inventato(self):
        """Finche' il profilo vero non c'e', la costante resta vuota e
        la voce non compare: un indirizzo social sbagliato porta il
        pubblico a casa di qualcun altro."""
        brand = self.BRAND.read_text()
        riga = [l for l in brand.splitlines()
                if l.startswith("export const BRAND_INSTAGRAM")][0]
        valore = riga.split("=")[1].strip().strip("';\" ")
        assert valore == "" or valore.startswith("https://www.instagram.com/"), \
            f"BRAND_INSTAGRAM non e' un profilo Instagram valido: {valore!r}"
        assert "PROVA" not in brand, "e' rimasto un indirizzo di prova"


class TestStrisciaSoundInHome:
    """HS (21/8, founder) — Aurya Sound viveva in DUE voci di menu e in
    nessun punto della home: chi ci cliccava attraversava il confine
    visivo scuro senza sapere cosa fosse. La striscia chiude il buco
    dentro la battuta che si chiama «la mappa», senza toccare la
    griglia delle tre schede.
    """

    HOME = FRONTEND_SRC / "features" / "network" / "NetworkHomePage.js"

    def test_la_mappa_nomina_sound(self):
        src = self.HOME.read_text()
        assert 'data-testid="hp-sound"' in src
        assert 'data-testid="hp-sound-cta"' in src
        # dentro la sezione dei pilastri, non in una battuta nuova: la
        # scaletta e' passata da sette a sei per decisione
        mappa = src.split('data-testid="hp-pillars"')[1].split("</Section>")[0]
        assert 'data-testid="hp-sound"' in mappa, \
            "la striscia e' fuori dalla mappa (o e' diventata una settima battuta)"

    def test_le_tre_schede_restano_tre(self):
        """La fila e' larga 1088 px: tre schede da 341. A quattro
        diventerebbero 248 l'una — la griglia non si tocca."""
        src = self.HOME.read_text()
        assert "lg:grid-cols-3" in src, "la griglia dei pilastri e' cambiata"
        pillars = src.split("const pillars = [")[1].split("\n  ];")[0]
        assert pillars.count("id: '") == 3, \
            "i pilastri non sono piu' tre: Sound doveva restare una striscia"

    def test_il_fondo_e_l_inchiostro_di_sound_non_il_salvia(self):
        """Due verdi adiacenti romperebbero l'alternanza dei fondi (la
        battuta 3 e' l'ancora salvia). L'inchiostro di Sound e' anche
        un'anteprima onesta del mondo in cui si sta per entrare."""
        src = self.HOME.read_text()
        blocco = src.split('data-testid="hp-sound"')[1][:400]
        assert "#122125" in blocco, "la striscia non usa l'inchiostro di Sound"
        assert "#2f5749" not in blocco, "la striscia e' salvia come la battuta 3"

    def test_una_porta_sola(self):
        """Il menu ha due voci (Sound e Meditazioni) per un mondo solo:
        la home non deve replicare la doppia porta."""
        src = self.HOME.read_text()
        striscia = src.split('data-testid="hp-sound"')[1].split("</Section>")[0]
        assert striscia.count("<EditorialCta") == 1, \
            "la striscia ha piu' di un invito"
        assert 'to="/meditazioni"' not in striscia, \
            "seconda porta nella striscia: le meditazioni si nominano nel testo"

    def test_la_foto_non_si_richiede_finche_non_esiste(self):
        """Un `src` che punta al nulla e' una richiesta a vuoto a ogni
        caricamento della home."""
        src = self.HOME.read_text()
        riga = [l for l in src.splitlines() if l.startswith("const SOUND_PHOTO")][0]
        valore = riga.split("=")[1].strip().strip("';\" ")
        assert valore == "" or valore.startswith("/media/"), \
            f"SOUND_PHOTO non e' un percorso interno: {valore!r}"
        assert "{SOUND_PHOTO && (" in src, \
            "l'immagine verrebbe richiesta anche quando non c'e'"

    def test_il_ciano_non_diventa_un_colore_di_marca(self):
        """La foto scelta e' luce blu-ciano: entra come TEXTURE — in
        screen sull'inchiostro, velata sul lato del testo e con la
        tinta spostata verso l'acqua di Sound — non a piena forza."""
        src = self.HOME.read_text()
        if "SOUND_PHOTO = ''" not in src:
            pass  # foto accesa: le regole sotto valgono comunque
        blocco = src.split("{SOUND_PHOTO && (")[1].split(")}")[0]
        assert "mix-blend-screen" in blocco
        assert "hue-rotate" in blocco, "il ciano entra senza correzione di tinta"
        assert 'alt=""' in blocco, "l'immagine decorativa ha un alt parlante"
        # Il velo e' UNIFORME: il testo occupa tutta la larghezza della
        # striscia (titolo a sinistra, corpo e invito a destra), quindi
        # un gradiente che si apre da un lato lo lascia scoperto — la
        # misura sui pixel veri dava 4,69:1 nel punto piu' chiaro.
        assert "bg-gradient" not in blocco, \
            "velo a gradiente: un lato del testo resta scoperto"
        assert "bg-[#122125]/[0.66]" in blocco, \
            "velo diverso da quello misurato (peggiore 6,41 · tipico 10,09)"


    def test_l_oro_della_striscia_e_quello_dei_fondi_scuri(self):
        """Founder (21/8): oro su titolo e sottotitolo. Ma non l'oro
        editoriale #c9b37e — sotto il velo e la texture scende a
        3,49:1 nel punto piu' chiaro. Si usa #d6c49a, che il sito adopera
        GIA' sui fondi scuri (i titoletti del footer): 9,62 sull'inchiostro,
        4,17 nel caso peggiore contro una soglia di 3:1 (entrambi i testi
        sono «grandi» per WCAG: 52 px e 24 px)."""
        src = self.HOME.read_text()
        striscia = src.split('data-testid="hp-sound"')[1].split("</Section>")[0]
        # Si guarda il CODICE, non i commenti: il commento che spiega
        # perche' NON usiamo l'oro editoriale lo nomina, ovviamente.
        import re as _re
        codice = _re.sub(r"\{/\*.*?\*/\}", "", striscia, flags=_re.S)
        assert codice.count("#d6c49a") >= 2, \
            "l'oro non e' su titolo E sottotitolo"
        assert "#c9b37e" not in codice, \
            "e' tornato l'oro editoriale, che qui non regge la texture"
        shell = SHELL.read_text()
        assert "#d6c49a" in shell, \
            "questo oro non e' piu' quello dei fondi scuri del sito"

    def test_il_sottotitolo_eredita_il_colore(self):
        """Lede porta `text-current`: e' fatto per EREDITARE. Passargli
        il colore da className mette due utility sulla stessa cascata e
        vince quella che capita — successo davvero, il sottotitolo era
        rimasto crema."""
        src = self.HOME.read_text()
        striscia = src.split('data-testid="hp-sound"')[1].split("</Section>")[0]
        assert 'className="text-[#d6c49a]"' in striscia, \
            "l'oro del sottotitolo non passa da un contenitore"
        lede = striscia.split("soundP1")[0]
        assert '<Lede size="lead" tone="inherit">' in lede, \
            "il Lede del sottotitolo non eredita piu' il colore"

    def test_la_foto_non_pesa_come_un_originale(self):
        """L'originale era 12000x8000 e 3,8 MB: su una fascia larga
        1088 px sarebbe un download inutile a ogni visita."""
        f = FRONTEND_SRC.parent / "public" / "media" / "hp-sound.jpg"
        if not f.exists():
            return                      # slot spento: niente da pesare
        kb = f.stat().st_size / 1024
        assert kb < 400, f"la fotografia della striscia pesa {kb:.0f} KB"


class TestVoceProfessionistiPro:
    """PRO (21/8, founder) — «Per i professionisti» deve emergere, e
    allo stesso modo su ogni piattaforma. Prima erano due cose diverse:
    su desktop un testo grigio piatto, su mobile una pastiglia
    TERRACOTTA (#C97B5D) — un colore fuori dalla tavolozza di Aurya che
    nel menu suonava come un avviso invece che come un invito."""

    def test_una_forma_sola_per_desktop_e_mobile(self):
        src = SHELL.read_text()
        assert "const PRO_CTA = " in src, \
            "le due voci non condividono piu' la stessa forma"
        assert 'data-testid="header-pro-cta"' in src
        assert 'data-testid="mobile-pro-cta"' in src
        for testid in ("header-pro-cta", "mobile-pro-cta"):
            blocco = src.split(f'data-testid="{testid}"')[1][:400]
            assert "${PRO_CTA}" in blocco, \
                f"{testid} si e' scritta uno stile suo invece di usare la forma condivisa"

    def test_niente_terracotta(self):
        """Il colore era l'unico problema segnalato dal founder sul
        mobile: non appartiene ad Aurya."""
        import re as _re
        src = SHELL.read_text()
        codice = _re.sub(r"/\*.*?\*/", "", src, flags=_re.S)
        for c in ("#C97B5D", "#a8593f"):
            assert c not in codice, f"il terracotta {c} e' tornato nel menu"

    def test_il_contrasto_regge_sul_velo_d_oro(self):
        """La pastiglia ha un velo d'oro sotto di se': misurato su
        QUELLO, non sul bianco. L'oro del marchio (#8a7440) darebbe
        4,15:1 a corpo 12 px — sotto il minimo."""
        import re as _re
        src = SHELL.read_text()
        forma = src.split("const PRO_CTA = ")[1].split("`;")[0]
        assert "text-[#6f5c33]" in forma, \
            "il testo e' tornato a un oro che sul proprio velo non regge"
        assert "border-[#8a7440]" in forma and "border-[#8a7440]/" not in forma, \
            "il bordo e' velato: sotto il 3:1 che delimita un controllo"
        # al passaggio del mouse il contrasto AUMENTA, non cala
        assert "hover:text-[#5a4b29]" in forma
