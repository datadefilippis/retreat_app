"""SN2 (8/10/2026, piano Aurya Sound §4.5 e decisione 7) — L'AGGANCIO.

La vetrina a rotazione, il cancello con la copertina e la playlist in vista,
la card social con la copertina, l'email del Cerchio «nuova meditazione /
nuova playlist» (una volta sola, prova a secco, chiave 1), i campi del tuo
spazio sull'account (predisposti, senza interfaccia), il ritiro di CALM,
GROUND e RESPIRO con i rimandi.
"""
import json
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"


class TestAnnuncioAlCerchio:
    def test_testo_traccia_e_playlist(self):
        from services.annunci_sound import testo_annuncio
        t = testo_annuncio("traccia", {"title": "Sera lenta", "slug": "sera-lenta", "intent": "dormire",
                                       "score": {"duration_sec": 600}, "cover_url": "/uploads/frequenze/x.jpg",
                                       "description": "Un respiro <b>lento</b>"}, guida="Davide")
        assert t["oggetto"] == "Nuova meditazione nel Cerchio: Sera lenta"
        assert t["percorso"] == "/frequenze/sera-lenta?da=email"
        assert "Dormire · 10 minuti · guidata da Davide" in t["corpo"]
        assert "/uploads/frequenze/x.jpg" in t["corpo"] and "&lt;b&gt;" in t["corpo"]   # mai HTML dell'utente
        p = testo_annuncio("playlist", {"title": "Sere", "slug": "sere", "tracce_count": 3, "duration_sec": 900})
        assert p["oggetto"] == "Nuova playlist nel Cerchio: Sere" and p["percorso"] == "/meditazioni/playlist/sere?da=email"
        assert "3 meditazioni · 15 minuti" in p["corpo"]

    def test_interruttore_spento(self, monkeypatch):
        """Founder (8/10 sera): nessuna email al Cerchio finche' le meditazioni
        non ci sono. Spento di default, su entrambe le porte e nel bottone."""
        from services import annunci_sound
        monkeypatch.delenv("SOUND_ANNUNCI_ATTIVI", raising=False)
        assert annunci_sound.attivo() is False
        monkeypatch.setenv("SOUND_ANNUNCI_ATTIVI", "1")
        assert annunci_sound.attivo() is True
        for f, porta in (("frequencies.py", '@router.post("/tracks/{track_id}/annuncia")'),
                         ("sound_playlists.py", '@router.post("/{playlist_id}/annuncia")')):
            corpo = (BACKEND / "routers" / f).read_text().split(porta)[1].split("\n@router")[0]
            assert "if not annunci_sound.attivo():" in corpo, f
            # l'interruttore viene PRIMA di ogni altra cosa (prima della prova a secco)
            assert corpo.index("annunci_sound.attivo()") < corpo.index("if a_secco:"), f
        flag = (FQ / "stato.js").read_text()
        assert "export const SOUND_ANNUNCI_ATTIVI = false;" in flag
        ui = (FQ / "CasaCampi.jsx").read_text()
        assert "if (!SOUND_ANNUNCI_ATTIVI && !annuncio?.at) return null;" in ui
        # nessun automatismo: l'annuncio parte solo dalle due porte a mano
        import subprocess
        out = subprocess.run(["grep", "-rln", "--include=*.py", "annunci_sound", str(BACKEND / "services"), str(BACKEND / "routers")],
                             capture_output=True, text=True).stdout.split()
        assert sorted(Path(x).name for x in out) == ["annunci_sound.py", "frequencies.py", "sound_playlists.py"]

    def test_endpoint_traccia(self):
        src = (BACKEND / "routers" / "frequencies.py").read_text()
        corpo = src.split('@router.post("/tracks/{track_id}/annuncia")')[1].split("\n@router")[0]
        assert "Depends(require_sound_crea)" in corpo and 'if not current_user.get("_sound_composer"):' in corpo
        # solo pubblicata e non riservata; prova a secco prima; una volta sola (marca prima di spedire)
        assert 't.get("status") != "published" or t.get("visibility") == "private"' in corpo
        assert "if a_secco:\n        return esito" in corpo
        assert "await annunci_sound.prenota(frequency_tracks_collection, track_id, len(lista))" in corpo
        assert "sfondo.add_task(annunci_sound.spedisci" in corpo
        assert '"annuncio": 1' in src.split("_LIST_PROJECTION = ")[1].split("}")[0]

    def test_endpoint_playlist(self):
        src = (BACKEND / "routers" / "sound_playlists.py").read_text()
        corpo = src.split('@router.post("/{playlist_id}/annuncia")')[1].split("\n@router")[0]
        assert 'if not current_user.get("_sound_composer"):' in corpo and "if a_secco:" in corpo
        assert "await annunci_sound.prenota(sound_playlists_collection, playlist_id, len(lista))" in corpo
        assert '"annuncio"' in src.split("async def _riga")[1].split("out[\"accesso\"]")[0]

    def test_servizio(self):
        src = (BACKEND / "services" / "annunci_sound.py").read_text()
        # i destinatari sono quelli del Cerchio (stesso filtro delle sequenze, interruttore compreso)
        assert "from services.sequenze import filtro_sub" in src and "db.aurya_subscribers.find(filtro_sub()" in src
        # il link apre gia' sbloccato (verificante) e l'email e' editoriale (List-Unsubscribe)
        assert "url = _link(email, percorso)" in src and "unsubscribe_url=url_preferenze_nudo(" in src
        # la marca PRIMA di spedire, e solo se nessuno l'ha gia' messa
        assert '{"id": doc_id, "annuncio.at": {"$exists": False}}' in src
        # un'email alla volta, fuori dal loop
        assert "await asyncio.to_thread(_spedisci_uno" in src

    def test_ui_crea(self):
        src = (FQ / "CasaCampi.jsx").read_text()
        assert "export function AnnunciaCerchio({ annuncio, cosa = 'meditazione', aSecco, invia, onFatto })" in src
        assert "window.confirm(`Scrivo a ${prova.destinatari}" in src       # prima il conto, poi la conferma
        assert 'data-testid="fq-annunciata"' in src and 'data-testid="fq-annuncia"' in src
        assert src.count("<AnnunciaCerchio") == 2                            # traccia e playlist, solo chiave 1
        api = (FRONTEND / "api" / "frequencies.js").read_text()
        assert "annuncia: (trackId, aSecco = false)" in api and "annuncia: (id, aSecco = false)" in api


class TestVetrinaCancelloCard:
    def test_vetrina_a_rotazione(self):
        src = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        assert "const giorno = Math.floor(Date.now() / 86400000);" in src
        assert "inVetrina[giorno % inVetrina.length]" in src
        assert "playlists.filter((p) => p.in_vetrina)" in src and "tutte.filter((t) => t.in_vetrina)" in src

    def test_cancello_con_copertina(self):
        src = (FQ / "CancelloLettera.jsx").read_text()
        assert "cover = null, titolo = '', playlist = null," in src
        assert 'data-testid="cancello-copertina"' in src and "Stai per sbloccare" in src
        assert "Parte della playlist «{playlist.title}»" in src
        player = (FQ / "PublicFrequencyPage.js").read_text()
        assert "cover={track?.cover_url} titolo={track?.title} playlist={playlist}" in player

    def test_card_social_con_copertina(self):
        src = (BACKEND / "routers" / "seo_shell.py").read_text()
        blocco = src.split("async def _meta_frequenza")[1].split("\nasync def ")[0]
        assert '"cover_url": 1' in blocco and '"image": _abs_image(t.get("cover_url"))' in blocco


class TestTuoSpazioPredisposto:
    def test_endpoint_e_pulizia(self):
        src = (BACKEND / "routers" / "platform_accounts.py").read_text()
        assert '@router.patch("/me/sound")' in src
        corpo = src.split('@router.patch("/me/sound")')[1].split("\n@router")[0]
        assert "_SOUND_OBIETTIVI" in corpo and "puliti[:20]" in corpo
        me = src.split('@router.get("/me")')[1].split("\n@router")[0]
        for campo in ("sound_preferenze", "sound_riprendi", "sound_recenti"):
            assert f'out["{campo}"]' in me, campo
        # nessuna interfaccia delle PREFERENZE (decisione 2): nessun componente le tocca
        # (riprendi e recenti sono di SN3 e passano da /me/sound/ascolto, non dalle preferenze)
        import subprocess
        out = subprocess.run(["grep", "-rl", "sound_preferenze", str(FRONTEND)], capture_output=True, text=True).stdout
        assert out.strip() == "", f"interfaccia delle preferenze costruita prima del tempo: {out}"


class TestRitiroEsperienze:
    def test_registro_rimandi(self):
        reg = json.loads((BACKEND / "config" / "rotte.json").read_text())
        for k in ("sound/calm", "sound/ground", "sound/respiro"):
            assert reg["rimandi"][k] == "/meditazioni", k

    def test_sitemap_e_shell(self):
        seo = (BACKEND / "routers" / "seo.py").read_text()
        for u in ("/sound/calm", "/sound/ground", "/sound/respiro"):
            assert u not in seo, u
        shell = (BACKEND / "routers" / "seo_shell.py").read_text()
        assert 'if sub in ("calm", "ground", "respiro"):' in shell
        # la home del suono non le elenca piu' (ma rimanda alla casa)
        home = shell.split("def _sound_home_html")[1].split("\ndef ")[0]
        assert "/sound/calm" not in home and 'href="/meditazioni"' in home

    @pytest.mark.asyncio
    async def test_shell_rimanda(self):
        from routers import seo_shell as shell
        for p in ("/sound/calm", "/sound/ground", "/sound/respiro"):
            meta = await shell.resolve_meta(p)
            assert meta and meta.get("noindex") and meta["canonical"] is None, p
            assert 'href="/meditazioni"' in meta["content_html"]

    def test_spa_rimanda_e_hub_non_le_nomina(self):
        pagina = (FQ / "esperienze" / "EsperienzaPage.js").read_text()
        assert 'if (SOUND_CASA_NUOVA) return <Navigate to="/meditazioni" replace />;' in pagina
        assert "function EsperienzaPageDismessa({ id })" in pagina
        # le rotte restano letterali in App.js (dismesse, non potate): la SPA le serve e rimanda
        app = (FRONTEND / "App.js").read_text()
        assert 'path="/sound/calm"' in app
        hub = (FQ / "casa" / "SoundHubPage.jsx").read_text()
        for u in ("/sound/calm", "/sound/ground", "/sound/respiro"):
            assert u not in hub, u
