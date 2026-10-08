"""MR3 (8/10/2026, piano refinement meditazioni) — L'ASCOLTO PARTE DOVE SEI.

Un lettore solo per la casa e la playlist (casa/lettore.js + LettoreBarra),
sui due FILE che la pagina pubblica gia' usa (anteprima 90 s, master mp3)
con lo stesso lettoreDaUrl: niente sintesi dal vivo qui, una meditazione
senza master si apre nella pagina intera. Stesse regole: sipario prima del
primo suono, cancello a 90 s nel foglio, eventi di ascolto, riprendi e
recenti con l'account, la playlist continua da sola. Il motore non si tocca.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"


class TestLettore:
    def test_usa_il_lettore_da_file_e_mai_il_motore(self):
        src = (FQ / "casa" / "lettore.js").read_text()
        assert "import { lettoreDaUrl } from '../engine/continuo';" in src
        for vietato in ("startPreview", "engine/synth", "preparaContinuo", "AuryaMode"):
            assert vietato not in src, vietato
        # le due vie della pagina, nello stesso ordine: master se sbloccati, altrimenti l'anteprima
        assert "if (apertoOra && t.master_pronto) {" in src and "else if (t.anteprima_url) {" in src
        assert "durata = Math.min(PREVIEW_SEC, d || PREVIEW_SEC); anteprima = true;" in src
        # senza file: la pagina intera (che sa sintetizzare)
        assert "window.location.href = `/frequenze/${t.slug}?da=" in src
        # il sipario prima del primo suono, lo stesso della pagina
        assert "const { guard, curtain, openReview } = useSafetyGate();" in src and "guard(avviaDavvero)" in src
        # il cancello a 90 s; dopo lo sblocco si riparte col master
        assert "if (anteprima && sec >= PREVIEW_SEC) { h.pause(); setCancello(true); }" in src
        assert "if (anteprima) { setCancello(true); return; }" in src
        assert "const sbloccaERiparti" in src
        # gli eventi di ascolto (SN0) e il tuo spazio (SN3)
        assert "frequenciesAPI.registraAscolto(slug, { evento: nome" in src
        assert "platformApi.post('/platform/me/sound/ascolto', { slug: t.slug, secondo: Math.floor(sec) })" in src
        # la playlist continua da sola
        assert "prossimaRef.current = () => { if (!vai(1)) butta(); };" in src
        # la copertina sullo schermo bloccato (predisposizione app)
        assert "artwork: [{ src: t.cover_url" in src

    def test_barra_e_foglio(self):
        src = (FQ / "casa" / "LettoreBarra.jsx").read_text()
        for tid in ("lettore-barra", "lettore-play", "lettore-prev", "lettore-next", "lettore-cuore", "lettore-chiudi", "lettore-cancello", "scheda-meditazione", "scheda-ascolta"):
            assert f'data-testid="{tid}"' in src or f'testid="{tid}"' in src, tid
        assert "<CancelloLettera slug={t.slug} durataSec={t.score?.duration_sec} cover={t.cover_url} titolo={t.title} playlist={L.playlist}" in src
        assert 'Apri la pagina' in src   # la pagina intera resta raggiungibile

    def test_casa_e_playlist_suonano_sul_posto(self):
        flag = (FQ / "stato.js").read_text()
        assert "export const SOUND_LETTORE_IN_CASA = true;" in flag
        casa = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        assert "<LettoreProvider>" in casa and "<LettoreBarra />" in casa and "<SchedaMeditazione />" in casa
        # barra, foglio e sipario DENTRO il .fqz: fuori resterebbero senza stile (visto dal vivo)
        assert casa.index("<LettoreBarra />") > casa.index('data-testid="casa-meditazioni"') and "{L?.curtain}" in casa
        assert "const inCasa = SOUND_LETTORE_IN_CASA && !!onPlay;" in casa
        # senza flag (o senza onPlay) la card e' un link come prima
        assert "const Cover = inCasa ? 'div' : Link;" in casa
        assert 'data-testid="casa-play"' in casa
        assert "suona(vetrina, { da: 'vetrina', playlist: null })" in casa
        assert "suona(riprendi.t, { da: 'riprendi', playlist: null, da_secondo: riprendi.secondo })" in casa
        pl = (FQ / "casa" / "PlaylistPage.jsx").read_text()
        assert "L.avvia(t, { da: 'playlist', playlist: pl })" in pl
        assert 'data-testid="playlist-riga-ascolta"' in pl and "suona(prima, p)" in pl
        css = (FQ / "casa" / "casa.css").read_text()
        assert ".fqz .lettore{position:fixed;left:0;right:0;bottom:0;" in css
        assert "@media(max-width:767px){.fqz.casa .lettore{bottom:58px" in css   # sopra la barra di navigazione

    def test_la_pagina_pubblica_resta_com_era(self):
        """Il motore e la pagina del link condiviso non cambiano: il lettore e' in piu'."""
        player = (FQ / "PublicFrequencyPage.js").read_text()
        for v in ("const avviaAnteprima = () => {", "annota('ramo: SYNTH (risintesi delle basi)');", "annota('ramo: MASTER (pass '"):
            assert v in player, v
        assert "from './casa/lettore'" not in player
