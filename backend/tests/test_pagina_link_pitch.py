"""24/9/2026 (founder) — «la sezione pagina link non viene usata e
probabilmente non viene capita». La card nell'editor del profilo si
spiega col VALORE (un solo link che raccoglie tutto, da mandare
ovunque, non solo in bio) e da spenta e' una vetrina che invita.

Tenuto fermo qui:
  1. da spenta: indirizzo futuro, «cosa trova chi lo apre» (6 voci),
     «dove usarlo», bottone «Attiva il mio link» oltre all'interruttore;
  2. il bozzetto da spenta e' STATICO (niente iframe su /l/{slug}, che
     da spenta rimanda al profilo) e mostra il nome pubblico vero;
  3. da accesa: sotto l'URL c'e' il «dove usarlo», la riga «Scopri chi
     sono» dice che porta al profilo Aurya;
  4. i tre gesti (attiva → copia → incolla) restano, testid invariati.
"""
from pathlib import Path

FE = Path(__file__).resolve().parents[2] / "frontend" / "src"
CARD = (FE / "features" / "settings" / "LinkPageCard.js").read_text(encoding="utf-8")
EDITOR = (FE / "features" / "settings" / "PublicProfilePage.js").read_text(encoding="utf-8")


class TestVetrinaDaSpenta:
    def test_pitch_completo(self):
        assert 'data-testid="linkpage-pitch"' in CARD
        assert "Il tuo indirizzo sarà" in CARD
        assert 'data-testid="linkpage-pitch-cosa"' in CARD
        for voce in ("pitchCosa1", "pitchCosa2", "pitchCosa3", "pitchCosa4", "pitchCosa5", "pitchCosa6"):
            assert f"linkPage.{voce}" in CARD, voce
        assert "Dove usarlo" in CARD and "bio di Instagram e TikTok" in CARD
        assert 'data-testid="linkpage-attiva"' in CARD and "Attiva il mio link" in CARD
        # il bottone fa la stessa cosa dell'interruttore: persist enabled
        i = CARD.index('data-testid="linkpage-attiva"')
        assert "persist({ ...lp, enabled: true })" in CARD[i - 200:i]

    def test_bozzetto_statico_col_nome_vero(self):
        pitch = CARD.split('data-testid="linkpage-pitch"')[1].split("{slug && lp.enabled &&")[0]
        assert "<iframe" not in pitch, "da spenta /l/{slug} rimanda al profilo: niente iframe"
        assert 'data-testid="linkpage-pitch-preview"' in pitch
        assert "{nome || t('linkPage.pitchNome'" in pitch
        assert "nome={nomePubblico(form.nome_persona, orgName)}" in EDITOR

    def test_il_titolo_dice_il_valore(self):
        assert "Un solo link per tutto" in CARD
        assert "Un solo link per la bio di Instagram" not in CARD


class TestDaAccesa:
    def test_dove_usarlo_sotto_url_e_riga_profilo(self):
        assert 'data-testid="linkpage-dove"' in CARD
        assert "linkPage.hintProfile" in CARD and "profilo Aurya" in CARD
        # i tre gesti restano
        for tid in ("linkpage-toggle", "linkpage-copy", "linkpage-url"):
            assert f'data-testid="{tid}"' in CARD, tid
        assert "navigator.clipboard" in CARD and "api.patch" in CARD
