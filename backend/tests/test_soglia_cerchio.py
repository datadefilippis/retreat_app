"""25/9/2026 sera (founder) — la SOGLIA del Cerchio: il cancello delle
meditazioni come pagina di valore per chi arriva dai social.

  - il testo e' del founder («Entra nel Cerchio di Aurya», cosa ascolti,
    i tre benefici, «Iscriviti gratuitamente e inizia ad ascoltare»);
  - le due porte di chi e' gia' dentro («Sei già nel Cerchio? Sblocca con
    la tua email», «Hai un account Aurya? Accedi · Crealo gratis») sono
    riquadri in evidenza, con un campo email proprio se il form e' vuoto;
  - parole e porte vivono UNA volta (CorpoCerchio.jsx) e le montano sia
    il cancello della traccia/landing (CancelloLettera) sia la vetrina
    (/meditazioni); llms.txt dice le stesse frasi;
  - «Sei già dentro» nomina la casa, non un nome segnaposto.
"""
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
FE = RADICE / "frontend" / "src"
FQ = FE / "features" / "frequenze"
CORPO = (FQ / "CorpoCerchio.jsx").read_text(encoding="utf-8")
CANCELLO = (FQ / "CancelloLettera.jsx").read_text(encoding="utf-8")
MED = (FQ / "MeditazioniPage.js").read_text(encoding="utf-8")
CSS = (FQ / "frequenze.css").read_text(encoding="utf-8")


class TestParoleDelFounder:
    def test_il_corpo_dice_le_frasi_del_founder(self):
        assert "TITOLO_CERCHIO = 'Entra nel Cerchio di Aurya'" in CORPO
        assert "CTA_ISCRIVITI = 'Iscriviti gratuitamente e inizia ad ascoltare'" in CORPO
        assert "pensate per accompagnare il sonno, la meditazione, il rilassamento" in CORPO
        for b in ("accesso alle nuove esperienze sonore di Aurya",
                  "i ritiri e le esperienze in anteprima",
                  "la Lettera di Aurya, con storie, pratiche e ispirazioni per coltivare il tuo benessere"):
            assert f"'{b}'" in CORPO, b
        assert "Entrando nel Cerchio ricevi anche:" in CORPO
        # niente «newsletter» sulla soglia
        assert "newsletter" not in CORPO.lower()

    def test_le_due_soglie_montano_lo_stesso_corpo(self):
        for src, nome in ((CANCELLO, "CancelloLettera"), (MED, "MeditazioniPage")):
            assert "<ValoreCerchio" in src and "<PorteCerchio" in src and "<FiduciaCerchio" in src, nome
            assert "`${CTA_ISCRIVITI} →`" in src, nome
        # la prima frase cambia con la soglia: la traccia parla di UNA esperienza, la vetrina di tutte
        assert "Questa esperienza sonora è disponibile per intero all’interno del Cerchio di Aurya." in CANCELLO
        assert "Le esperienze sonore di Aurya sono disponibili per intero all’interno del Cerchio di Aurya." in MED

    def test_llms_txt_dice_le_stesse_frasi(self):
        from services.identita import corpo_meditazioni
        corpo = corpo_meditazioni()
        assert "<h2>Entra nel Cerchio di Aurya</h2>" in corpo
        assert "pensate per accompagnare il sonno, la meditazione, il rilassamento" in corpo
        assert "la Lettera di Aurya, con storie, pratiche e ispirazioni" in corpo


class TestLeDuePorte:
    def test_riquadri_in_evidenza_con_campo_proprio(self):
        assert 'data-testid="porta-sblocco"' in CORPO and 'data-testid="porta-account"' in CORPO
        assert "Sei già nel Cerchio?" in CORPO and "Hai un account Aurya?" in CORPO
        assert "Non ce l’hai? {crea}" in CORPO
        # senza email nel form il riquadro apre il SUO campo, non «scrivila qui sopra»
        assert 'data-testid="porta-sblocco-email"' in CORPO and "{chiediEmail ? formSblocco : sblocca}" in CORPO
        for src, nome in ((CANCELLO, "CancelloLettera"), (MED, "MeditazioniPage")):
            assert "if (!email) { setChiediEmail(true); return; }" in src, nome
            assert "Scrivi la tua email qui sopra e ripremi" not in src, nome
        # i bottoni/link con i testid restano nei file dei cancelli (le guardie storiche li leggono la')
        assert 'data-testid="cancello-gia-iscritto"' in CANCELLO and 'data-testid="med-gia-dentro"' in MED

    def test_vestito_scuro_a_due_colonne_che_si_impila_sul_telefono(self):
        assert ".fqz .cerchio-porte{display:grid;grid-template-columns:1fr 1fr" in CSS
        blocco = CSS.split("@media (max-width:640px){\n  .fqz .cerchio-porte")[1][:80]
        assert "grid-template-columns:1fr" in blocco
        assert ".fqz button.primary.cerchio-cta{width:100%" in CSS


class TestGiaDentro:
    def test_il_titolo_nomina_la_casa(self):
        src = (FE / "components" / "GiaDentro.js").read_text(encoding="utf-8")
        assert "defaultValue: 'Sei già dentro Aurya.'" in src
        assert "titoloNome" not in src and "{{nome}}" not in src
