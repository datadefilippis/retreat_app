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


class TestPotaturaCr6:
    def test_la_libreria_del_compositore_veste_il_nuovo(self):
        page = (FQ / "FrequenzePage.js").read_text()
        assert "&& (view === 'create' || view === 'mine' || (view === 'explore' && canCompose));" in page
        assert '<SelettoreCrea attiva="fonti" badge={layers.length} navigate={navigate} onFonti={() => {}} />' in page
        # la libreria tiene i suoi gesti da compositore (il pubblico non li vede)
        assert "view === 'explore' && canCompose && (" in page
        # il trigger di Studio non compare a chi ha le chiavi (TriggerStudio si nasconde da solo)
        assert "if (user?.sound_crea) return null;" in (FQ / "TriggerStudio.jsx").read_text()


class TestDurataSegueLaBase:
    def test_la_base_detta_la_durata_in_auto(self):
        """8/10 sera (founder): «ho aggiunto una base di 6 minuti e la
        sessione dura 1 minuto». In AUTO la base detta la lunghezza."""
        page = (FQ / "FrequenzePage.js").read_text()
        corpo = page.split("const addSoundToSession = (asset) => {")[1].split("const parolaId")[0]
        assert "const lungaFile = Math.max(1, asset.duration_sec || 0);" in corpo
        assert ": !durataAuto ? duration" in corpo                                   # in FISSA resta la durata scelta
        assert "Math.min(DURATA_MAX_SEC, layers.length ? Math.max(duration, start + lungaFile) : start + lungaFile)" in corpo
