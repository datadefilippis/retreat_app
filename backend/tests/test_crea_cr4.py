"""CR4 (8/10/2026 sera) — LE MIE TRACCE, il vestito nuovo.

Card compatte in griglia, un gesto primario per stato (stessi handler e
testid), «Apri» in Crea, i campi della casa (CampiCasa, intatto) dietro
«Modifica» in un foglio, filtri e cerca, le playlist nel loro pannello.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"
CR = FQ / "crea"


class TestTracce:
    def test_la_vista_e_dietro_il_flag(self):
        page = (FQ / "FrequenzePage.js").read_text()
        assert "{view === 'mine' && nuovo && <TracceVista kit={kit} />}" in page
        assert "{view === 'mine' && !nuovo && (" in page                 # la vista vecchia resta intera
        assert "<CampiCasa traccia={d} onCambio={loadDrafts} composer={!!user?.sound_composer} />" in page   # SN0
        kit = page.split("const kit = {")[1].split("};")[0]
        for g in ("removeDraft", "confermaMeditazioni", "pubblicaDaLista", "unpublishById", "copyPublicLink",
                  "setCondividi", "loadDrafts", "composer: !!user?.sound_composer"):
            assert g in kit, g

    def test_card_compatte_stessi_gesti(self):
        src = (CR / "TracceVista.jsx").read_text()
        for tid in ("tracce-vista", "cr-tracce-filtri", "cr-tracce-cerca", "cr-tracce", "cr-traccia-card",
                    "cr-traccia-modifica", "cr-foglio-modifica", "cr-traccia-elimina"):
            assert f'"{tid}"' in src, tid
        # i gesti di TM1/TM2 con i loro testid
        for tid in ("fq-pubblica-meditazioni", "fq-pubblica-riservata", "fq-link-riservati"):
            assert f'"{tid}"' in src, tid
        assert "k.confermaMeditazioni(d)" in src and "k.pubblicaDaLista(d.id, 'private')" in src
        assert "k.unpublishById(d.id)" in src and "k.copyPublicLink(d.slug)" in src and "k.openDraft(d.id)" in src
        # i campi della casa, intatti, nel foglio
        assert "<CampiCasa traccia={inModifica} onCambio={k.loadDrafts} composer={k.composer} />" in src
        assert "<PlaylistPannello tracce={k.drafts} composer={k.composer} />" in src
        assert "<CondivisioniTraccia trackId={k.condividi.id}" in src
        for f in ("tutte", "bozze", "riservate", "pubbliche"):
            assert f"['{f}'," in src, f
        for vietato in ("frequenciesAPI", "useAuth", "setDrafts"):
            assert vietato not in src, vietato
