"""
CICLO FN (30/8/2026) — il funnel delle landing.

Il test del founder: anteprima 90s in landing → «Continua l'ascolto»
→ la pagina traccia chiedeva di RIASCOLTARE 90 secondi prima del
cancello, che poi parlava in gergo («la Lettera di Aurya») a chi non
sa cosa sia. Piano in docs/FUNNEL_LANDING_PLAN_2026-08.md.

Il principio: UN pedaggio, detto in chiaro, pagabile sul posto.
"""
from pathlib import Path

FE = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
FQ = FE / "features" / "frequenze"


class TestFn1PedaggioUnaVolta:
    def test_il_segno_e_il_parametro_aprono_il_cancello_all_arrivo(self):
        src = (FQ / "PublicFrequencyPage.js").read_text()
        assert "'da') === 'anteprima'" in src.replace('"', "'")
        assert "fqz_anteprima_finita" in src
        assert "setGateOpen(true)" in src

    def test_la_landing_lascia_il_segno_a_fine_anteprima(self):
        src = (FQ / "SoundHomePage.jsx").read_text()
        assert "sessionStorage.setItem('fqz_anteprima_finita'" in src

    def test_il_link_freddo_vive_il_flusso_di_sempre(self):
        """Chi arriva da un link condiviso senza segno: 90s liberi,
        poi cancello — la logica t>=PREVIEW_SEC resta."""
        src = (FQ / "PublicFrequencyPage.js").read_text()
        assert "PREVIEW_SEC" in src
        assert "cur >= PREVIEW_SEC" in src


class TestFn2CancelloInChiaro:
    def test_un_solo_cancello_per_due_mondi(self):
        c = (FQ / "CancelloLettera.jsx").read_text()
        assert "variante" in c and "'chiaro'" in c.replace('"', "'")
        for pagina in ("PublicFrequencyPage.js", "SoundHomePage.jsx"):
            assert "<CancelloLettera" in (FQ / pagina).read_text(), \
                f"{pagina} non monta il cancello condiviso"

    def test_il_copy_dice_valore_e_prezzo_in_chiaro(self):
        c = (FQ / "CancelloLettera.jsx").read_text()
        assert "riservata agli iscritti" in c
        assert "gratuita" in c
        # il brand e' apposizione, non premessa (30/8: senza trattini,
        # per volere del founder, la frase usa le virgole)
        assert "newsletter di Aurya, la Lettera" in c

    def test_le_tre_porte_restano(self):
        """Iscriviti / gia' iscritto / account: nessuna via persa."""
        c = (FQ / "CancelloLettera.jsx").read_text()
        for t in ("cancello-iscriviti", "cancello-gia-iscritto",
                  "cancello-accedi", "cancello-crea"):
            assert f'data-testid="{t}"' in c


class TestFn3IscrizioneSulPosto:
    def test_a_fine_anteprima_il_form_e_li(self):
        src = (FQ / "SoundHomePage.jsx").read_text()
        patto = src[src.index('sh-anteprima-patto'):]
        assert "<CancelloLettera" in patto[:800], \
            "a fine anteprima deve comparire il FORM, non due link"

    def test_dopo_lo_sblocco_la_landing_offre_il_completo(self):
        src = (FQ / "SoundHomePage.jsx").read_text()
        assert 'data-testid="sh-anteprima-sbloccata"' in src
        assert "Ascolta la meditazione completa" in src


class TestFn4TriggerInEvidenza:
    def test_le_meditazioni_sono_un_bottone_col_numero(self):
        src = (FQ / "SoundHomePage.jsx").read_text()
        assert "ctaMeditazioni" in src
        assert "tracks_count" in src, "il numero deve essere VERO (dal catalogo)"
        blocco = src[src.index('sh-porta-meditazioni') - 200:src.index('sh-porta-meditazioni') + 200]
        assert "<Bottone" in blocco, "il trigger e' un bottone pieno, non un richiamo"

    def test_l_hero_vende_il_gancio_caldo(self):
        src = (FQ / "SoundHomePage.jsx").read_text()
        assert 'testid="sh-cta-ascolta"' in src
        assert "Ascolta una meditazione" in src
        assert "sh-hero-studio" not in src, \
            "il richiamo pro e' uscito dall'hero (ha la sua band)"


class TestFn5CreaStudio:
    def test_su_invito_detto_una_volta(self):
        src = (FQ / "CreaStudioLanding.jsx").read_text()
        assert src.count("Accesso su invito") == 1

    def test_prova_sociale_e_cosa_succede_dopo(self):
        src = (FQ / "CreaStudioLanding.jsx").read_text()
        assert 'data-testid="studio-prova-sociale"' in src
        assert "nascono qui" in src
        assert "venti minuti" in src


class TestFn6Potatura:
    def test_le_code_ridondanti_sono_uscite(self):
        src = (FQ / "SoundHomePage.jsx").read_text()
        for coda in ("qualcosa che possa durare",
                     "nasce dallo stesso metodo",
                     "senza diventare misterioso"):
            assert coda not in src, f"coda ridondante ancora in pagina: {coda}"
