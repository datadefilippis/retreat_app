"""24/9/2026 (founder) — «abbiamo raggiunto molte categorie, orientarsi e'
complicato»: UN selettore condiviso per le discipline (components/
SelettoreDiscipline.js) usato dall'editor del profilo e da /benvenuto.

Tenuto fermo qui:
  1. il processo in due mosse: scelte in alto (con la ×), CERCA per
     sinonimo (CERCA_ANCHE), famiglie chiuse una alla volta, «le piu' scelte»;
  2. i sinonimi e le «piu' scelte» puntano solo a slug esistenti (parita'
     col backend), e coprono le voci nuove (psicologia, gestalt, chakra);
  3. lo stesso componente nelle due pagine, stessi data-testid, toggle
     funzionale (niente stale closure), tetto 10;
  4. la voce «Gestalt counseling» (slug counseling-gestalt) esiste nei due file e ha una casa.
"""
import json
import re
from pathlib import Path

from models.disciplines import DISCIPLINES, DISCIPLINE_FAMILIES

BACKEND = Path(__file__).resolve().parents[1]
FE = BACKEND.parent / "frontend" / "src"
SEL = (FE / "components" / "SelettoreDiscipline.js").read_text(encoding="utf-8")
LIB = (FE / "lib" / "disciplines.js").read_text(encoding="utf-8")
EDITOR = (FE / "features" / "settings" / "PublicProfilePage.js").read_text(encoding="utf-8")
WELCOME = (FE / "features" / "prelaunch" / "WelcomeRetePage.js").read_text(encoding="utf-8")


def _js_slugs(blocco):
    return re.findall(r"'([a-z0-9-]+)'", blocco)


class TestProcesso:
    def test_due_mosse(self):
        for tid in ("disc-scelte", "disc-search", "disc-risultati", "disc-nessuna", "disc-piu-scelte", "disc-famiglie"):
            assert f'data-testid="{tid}"' in SEL, tid
        assert "data-testid={`disc-fam-${fam.slug}`}" in SEL
        assert "data-testid={`pp-disc-${d.slug}`}" in SEL
        assert "setAperta(open ? null : fam.slug)" in SEL      # una famiglia alla volta
        assert "aria-label={`Togli ${disciplineLabel(s)}`}" in SEL   # la × sulle scelte
        assert "{scelte.length}/{max}" in SEL

    def test_toggle_funzionale_e_tetto(self):
        assert "onToggle(d.slug)" in SEL and "disabled={!sel && full}" in SEL
        assert "setForm(f => {" in EDITOR and "cur.length >= DISCIPLINES_MAX) return f;" in EDITOR

    def test_stesso_componente_nelle_due_pagine(self):
        assert "<SelettoreDiscipline" in EDITOR and "<SelettoreDiscipline" in WELCOME
        assert "DISCIPLINE_FAMILIES.map" not in EDITOR and "DISCIPLINE_FAMILIES.map" not in WELCOME
        assert 'data-testid="welcome-disciplines"' in WELCOME
        assert "max-h-56 overflow-y-auto" not in WELCOME        # via la scatola-muro


class TestSinonimi:
    def test_puntano_a_voci_vere(self):
        blocco = LIB.split("export const CERCA_ANCHE")[1].split("});")[0]
        chiavi = re.findall(r"^\s*'?([a-z0-9-]+)'?: \[", blocco, re.M)
        assert chiavi, "CERCA_ANCHE vuoto"
        sconosciute = [k for k in chiavi if k not in DISCIPLINES]
        assert not sconosciute, sconosciute
        piu = _js_slugs(LIB.split("export const PIU_SCELTE")[1].split("]);")[0])
        assert len(piu) == 8 and all(s in DISCIPLINES for s in piu), piu

    def test_coprono_le_voci_nuove(self):
        blocco = LIB.split("export const CERCA_ANCHE")[1].split("});")[0]
        for slug, parola in (("psicologia", "psicologa"), ("counseling-gestalt", "gestalt"),
                             ("allineamento-chakra", "chakra"), ("massaggio-olistico", "massaggiatrice"),
                             ("sound-healing", "gong")):
            riga = next(r for r in blocco.splitlines() if r.strip().startswith(f"{slug}:") or r.strip().startswith(f"'{slug}':"))
            assert parola in riga, (slug, parola)
        assert "export function cercaDiscipline(query)" in LIB
        assert "normalize('NFD')" in LIB                  # «ciclicità» e «ciclicita» sono la stessa cosa


class TestGestalt:
    def test_esiste_in_entrambi_i_file_e_ha_una_casa(self):
        # 1/10/2026 (founder): etichetta «Gestalt counseling», slug invariato
        assert DISCIPLINES["counseling-gestalt"] == "Gestalt counseling"
        assert "{ slug: 'counseling-gestalt', label: 'Gestalt counseling' }" in LIB
        anima = {s for f, _l, items in DISCIPLINE_FAMILIES if f == "anima" for s, _ in items}
        assert "counseling-gestalt" in anima
        from models.retreat_taxonomy import DISCIPLINA_TO_CATEGORIA
        from services.pagine_locali import CATEGORIA_ARTICOLI
        assert DISCIPLINA_TO_CATEGORIA["counseling-gestalt"] == "crescita"
        assert CATEGORIA_ARTICOLI["counseling-gestalt"] == "crescita"
        # 59 voci (1/10: + crescita-personale, crescita-spirituale), 7 famiglie
        assert len(DISCIPLINES) == 59 and len(DISCIPLINE_FAMILIES) == 7
        for slug, label in (("crescita-personale", "Crescita personale"), ("crescita-spirituale", "Crescita spirituale")):
            assert DISCIPLINES[slug] == label and DISCIPLINA_TO_CATEGORIA[slug] == "crescita" and CATEGORIA_ARTICOLI[slug] == "crescita", slug
        for slug, label, cat in (("allineamento", "Allineamento (colonna & postura)", "yoga"),
                                 ("mind-movie", "Mind movie", "meditazione"),
                                 ("massaggio", "Massaggio", "massaggio"),
                                 ("pulizia-energetica", "Pulizia energetica", "reiki")):
            assert DISCIPLINES[slug] == label and DISCIPLINA_TO_CATEGORIA[slug] == cat and CATEGORIA_ARTICOLI[slug] == cat, slug
        assert DISCIPLINES["percorsi-spirituali"] == "Percorsi spirituali" and DISCIPLINA_TO_CATEGORIA["percorsi-spirituali"] == "crescita" and CATEGORIA_ARTICOLI["percorsi-spirituali"] == "crescita"
