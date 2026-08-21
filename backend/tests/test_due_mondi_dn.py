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
