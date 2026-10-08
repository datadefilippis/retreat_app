"""CR1-CR3 (8/10/2026 sera) — IL VESTITO NUOVO DI CREA.

docs/PIANO_CREA_RESTYLING_2026-10-08.md. Barra a una riga, sessione al
centro coi livelli ripiegabili, il banco del mix (frequenze, suoni, voce,
respiro, protocolli, le tue tracce), salva/pubblica in basso. Il componente
resta FrequenzePage: stato, funzioni e contratto delle ricette non cambiano;
il vestito nuovo (crea/CreaVista.jsx) riceve l'oggetto dei gesti `kit`.
?vestito=vecchio mostra la vista di prima.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"
CR = FQ / "crea"


class TestVestito:
    def test_flag_e_vestito_vecchio(self):
        assert "export const SOUND_CREA_NUOVO = true;" in (FQ / "stato.js").read_text()
        page = (FQ / "FrequenzePage.js").read_text()
        assert "const nuovo = SOUND_CREA_NUOVO && qs.get('vestito') !== 'vecchio' && (view === 'create' || view === 'mine');" in page
        assert 'data-vestito={nuovo ? \'nuovo\' : undefined}' in page
        assert "{view === 'create' && nuovo && <CreaVista kit={kit} />}" in page
        assert "{view === 'create' && !nuovo && (" in page               # la vista vecchia resta, intera
        assert "{!nuovo && (\n      <header>" in page                      # niente testata doppia nel nuovo
        assert "view !== 'impara' && <SafetyLine" in page                 # la riga resta nel file (il CSS la nasconde nel nuovo)

    def test_il_kit_porta_gli_stessi_gesti(self):
        page = (FQ / "FrequenzePage.js").read_text()
        kit = page.split("const kit = {")[1].split("};")[0]
        for g in ("playGuarded", "stopSession", "seekTo", "fissaDurata", "tornaDurataAuto", "save", "publishTrack",
                  "unpublishTrack", "esportaMp3", "resetSession", "loadProtocol", "toggleCard", "addCardToSession",
                  "toggleSoundPreview", "addSoundToSession", "openDraft", "aggiungiLivelliDa", "lineaDelTempo",
                  "leggioVoce", "guard", "liveCardsRef", "composeAllLive", "stopAllCards", "setStanza", "setCategoria"):
            assert g in kit, f"manca nel kit: {g}"
        # la linea del tempo e il leggio sono UNA volta sola, per i due vestiti
        assert "const lineaDelTempo = (" in page and "const leggioVoce = (" in page
        assert "{layers.length > 0 ? lineaDelTempo : (" in page and "{leggioVoce}" in page
        assert page.count('<div className="voicedesk" data-testid="fqz-voicedesk">') == 1

    def test_i_livelli_si_ripiegano(self):
        page = (FQ / "FrequenzePage.js").read_text()
        assert "const [aperti, setAperti] = useState({});" in page
        assert "${nuovo && !aperti[l.id] ? ' chiusa' : ''}" in page
        assert "data-testid={`cr-riga-apri-${l.id}`}" in page and "data-testid={`cr-riga-riassunto-${l.id}`}" in page
        css = (CR / "crea.css").read_text()
        assert ".row.chiusa .r4{display:none}" in css and ".row.chiusa .timerow" in css

    def test_le_tue_tracce_come_fonte(self):
        page = (FQ / "FrequenzePage.js").read_text()
        corpo = page.split("const aggiungiLivelliDa = async (d) => {")[1].split("const openDraft")[0]
        assert "frequenciesAPI.get(d.id)" in corpo and "id: ++_uid" in corpo
        assert "const offset = playing ? Math.max(0, Math.min(elapsed, duration - 1)) : 0;" in corpo
        assert "DURATA_MAX_SEC : duration" in corpo                        # il tetto parla, non taglia in silenzio


class TestCreaVista:
    def test_le_tre_zone(self):
        src = (CR / "CreaVista.jsx").read_text()
        for tid in ("cr-sel", "cr-barra", "cr-play", "cr-seekbar", "cr-durata", "cr-aggiungi", "cr-altro",
                    "cr-riassunto", "cr-sessione", "cr-vuoto", "cr-banco", "cr-cerca", "cr-piede", "cr-stato",
                    "cr-foglio-altro", "fq-foglio-durata"):
            assert f'"{tid}"' in src, tid
        # i testid dei gesti che i test di ieri conoscono restano gli stessi
        for tid in ("fq-save", "fq-publish", "fq-unpublish", "fq-export", "fq-guarda", "fq-categoria", "fq-stanza",
                    "fq-durata-auto", "fq-durata-min", "fq-live-hint", "fq-stima-memoria", "fq-crea-avviso-cuffie",
                    "fq-crea-scena", "fq-studio-apri"):
            assert f'"{tid}"' in src, tid
        assert "export function SelettoreCrea" in src and "['fonti', 'Fonti', onFonti]" in src

    def test_il_banco_del_mix(self):
        src = (CR / "CreaVista.jsx").read_text()
        for scheda in ("'frequenze'", "'suoni'", "'voce'", "'respiro'", "'protocolli'", "'tracce'"):
            assert f"[{scheda}," in src, scheda
        assert "k.toggleCard(s.chiave, s)" in src and "k.addCardToSession(s)" in src
        assert "k.addSoundToSession(s)" in src and "data-testid={`fq-sound-add-${s.id}`}" in src
        assert "k.aggiungiLivelliDa(d)" in src and "k.openDraft(d.id)" in src
        assert "k.loadProtocol(name)" in src
        assert "{k.leggioVoce}" in src
        # nessuno stato di sessione qui dentro: solo interfaccia
        for vietato in ("setLayers", "frequenciesAPI", "useAuth", "startCardLive"):
            assert vietato not in src, vietato
        css = (CR / "crea.css").read_text()
        assert "@media(min-width:1024px)" in css and "grid-template-columns:380px minmax(0,1fr)" in css   # colonna
        assert "position:fixed;left:0;right:0;bottom:0" in css and "height:58vh" in css                   # foglio a mezza altezza
