"""Lotto LA (8/10/2026 sera) — AURYA LAB, il vestito nuovo.

docs/PIANO_LAB_RESTYLING_2026-10-08.md. Il founder: «rendi il Lab usabile,
moderno, immediato, multipiattaforma, anche con popup; senza toccare le
funzionalità, zero regressioni». Dietro LAB_VESTITO_NUOVO (?vestito=vecchio
= il Lab di prima): foglio «?» alla prima visita, selettore a tre + riga
delle stanze, letture accanto ai comandi, didascalie a un tocco, Sala con
le carte a tono. Gli strumenti e il motore non cambiano; lab.css resta.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"
LAB = FQ / "lab"


class TestTelaio:
    def test_flag_e_vestito_vecchio(self):
        # 8/10 sera: il telaio vecchio e' stato POTATO (ok del founder): un telaio solo
        assert "LAB_VESTITO_NUOVO" not in (FQ / "stato.js").read_text()
        src = (LAB / "Stanza.jsx").read_text()
        assert 'className="fqz lab vestito"' in src and "StanzeSound" not in src and "vestitoNuovo" not in src

    def test_il_foglio_e_la_riga_delle_stanze(self):
        src = (LAB / "Stanza.jsx").read_text()
        for tid in ("lab-riga-stanze", "lab-spiega-apri", "lab-spiega-foglio", "lab-spiega-vai", "lab-due-colonne", "lab-col-letture"):
            assert f'"{tid}"' in src, tid
        assert "data-testid={`lab-riga-${id}`}" in src
        for stanza in ("banco", "orecchio", "ritratto", "meraviglie", "risonanze"):
            assert f"['{stanza}', " in src, stanza
        # alla prima visita si apre da solo, in try/catch, mai bloccante
        assert "const k = `fqz_lab_spiega_${slug}`;" in src and "catch { /* privato" in src
        # il testo di sempre resta (pin di LU3) e sta nel foglio
        assert "Perché ti interessa" in src and "Cosa puoi fare qui" in src and 'data-testid="lab-testata"' in src
        assert '<SelettoreTre attiva="lab" />' in src

    def test_le_letture_accanto_ai_comandi_senza_toccare_gli_strumenti(self):
        src = (LAB / "Stanza.jsx").read_text()
        assert "const letture = lettureUltime && figli.length > 1 ? figli[figli.length - 1] : null;" in src
        for stanza in ("LabBanco", "LabOrecchio", "LabMeraviglie"):
            pag = (LAB / f"{stanza}.jsx").read_text()
            assert "lettureUltime" in pag, stanza
            assert pag.index("<LettureBanco") > pag.index("<Stanza"), stanza   # l'ultimo figlio
        # gli strumenti e il motore: intatti rispetto al lotto (nessun riferimento al vestito)
        for f in ("Generatore.jsx", "SecondaVoce.jsx", "LettureBanco.jsx", "Oscilloscopio.jsx", "Spettro.jsx",
                  "Spettrogramma.jsx", "Orecchio.jsx", "Ritratto.jsx", "Meraviglie.jsx", "Risonanze.jsx",
                  "Percorsi.jsx", "usaLab.js", "motore.js"):
            assert "vestitoNuovo" not in (LAB / f).read_text() and "lab-vestito" not in (LAB / f).read_text(), f
        # le didascalie si ripiegano per delega, non toccando i componenti
        assert "e.target.closest('.lab-didascalia')" in src and "d.classList.toggle('aperta')" in src


class TestVestito:
    def test_il_css_si_posa_sopra_e_lab_css_resta(self):
        css = (LAB / "lab-vestito.css").read_text()
        assert css.count(".fqz.lab.vestito") > 60
        assert "grid-template-columns:minmax(0,1fr) minmax(0,1fr)" in css          # due colonne su desktop
        assert "order:-1;position:sticky;top:0" in css and "scroll-snap-type:x mandatory" in css   # striscia sticky sul telefono
        assert ".fqz.lab.vestito .lab-didascalia.aperta{max-height:none" in css
        assert ".fqz.lab.vestito .lab-ritratto>.lab-chead h2::before{content:'1'}" in css
        # lab.css non perde le regole pinzate da test_sound_lab
        vecchio = (LAB / "lab.css").read_text()
        for regola in (".fqz .lab-ritorno{", ".fqz .lab-rz-tono{position:sticky", ".fqz .lab-ondaviva{"):
            assert regola in vecchio, regola

    def test_la_sala_con_le_carte_a_tono(self):
        src = (LAB / "LabSala.jsx").read_text()
        assert 'className="fqz lab vestito"' in src and "vestitoNuovo" not in src
        for tono in ("tono: 'salvia'", "tono: 'acqua'", "tono: 'oro'", "tono: 'viola'", "tono: 'sabbia'"):
            assert tono in src, tono
        assert "className={`lab-sala-carta tono-${s.tono}`}" in src
        assert "StanzeSound" in src and src.count("domanda:") == 5         # i pin di LU restano veri
