"""MR2 (8/10/2026, piano refinement meditazioni) — IL CUORE OVUNQUE.

Un hook solo (casa/preferite.js, cache di sessione, toggle ottimistico), un
componente solo (casa/Cuore.jsx), il cuore su card, vetrina «Di oggi»,
«Riprendi», righe della playlist, pagina della meditazione; le playlist
salvate (stessa collezione, slug con prefisso) con la loro riga nel tuo
spazio e nell'account.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"


class TestServer:
    def test_playlist_salvate_stessa_collezione(self):
        src = (BACKEND / "routers" / "frequencies.py").read_text()
        assert '_PL_PREFISSO = "playlist:"' in src
        assert '@router.put("/favorites/playlist/{slug}"' in src and '@router.delete("/favorites/playlist/{slug}"' in src
        # la lista separa meditazioni e playlist e risponde come prima (slugs) piu' le playlist
        lst = src.split('@router.get("/favorites")')[1].split("\n@router")[0]
        assert 'return {"items": items, "slugs": slugs, "playlists": playlists, "playlist_items": playlist_items}' in lst
        assert 'slugs = [f["slug"] for f in favs if not f["slug"].startswith(_PL_PREFISSO)]' in lst
        # il cuore su una playlist esiste solo se e' pubblicata
        add = src.split('@router.put("/favorites/playlist/{slug}"')[1].split("\n@router")[0]
        assert '{"slug": slug, "status": "published"}' in add
        # la rotta della playlist sta PRIMA di quella generica /favorites/{slug} (altrimenti la mangia)
        assert src.index('@router.put("/favorites/playlist/{slug}"') < src.index('@router.put("/favorites/{slug}"')


class TestUnCuore:
    def test_hook_e_componente(self):
        hook = (FQ / "casa" / "preferite.js").read_text()
        assert "export function usePreferite()" in hook and "const cache = {" in hook
        # senza account: il cuore resta in attesa e si apre l'invito, mai l'email (8/10 sera)
        assert "if (!conto) { ricordaInAttesa('slug', slug); setChiediAccount(true); return; }" in hook
        assert "if (era) set.add(slug); else set.delete(slug);   // si ritira" in hook   # ottimistico, si ritira
        cuore = (FQ / "casa" / "Cuore.jsx").read_text()
        assert "export default function Cuore({ on = false, onClick, variante = 'card'" in cuore
        assert "export function InvitoAccount(" in cuore
        css = (FQ / "casa" / "casa.css").read_text()
        for v in (".fqz .cuore-card{", ".fqz .cuore-inline{", ".fqz .cuore-riga{"):
            assert v in css, v

    def test_il_cuore_e_ovunque(self):
        casa = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        assert "const pref = usePreferite();" in casa
        assert "platformApi.get('/frequencies/favorites')" not in casa          # niente seconda copia dello stato
        for tid in ("casa-cuore", "casa-cuore-playlist", "casa-oggi-cuore", "casa-riprendi-cuore"):
            assert f'testid="{tid}"' in casa, tid
        assert 'data-testid="casa-playlist-salvate"' in casa
        assert "<InvitoAccount aperto={heartAsk}" in casa
        pl = (FQ / "casa" / "PlaylistPage.jsx").read_text()
        assert 'testid="playlist-cuore"' in pl and 'testid="playlist-riga-cuore"' in pl
        player = (FQ / "PublicFrequencyPage.js").read_text()
        assert 'testid="fqp-cuore"' in player and "const pref = usePreferite();" in player
        acc = (FQ / "AccountFavorites.js").read_text()
        assert "setPlaylists(r.data.playlist_items || [])" in acc and 'data-testid="account-playlist-salvata"' in acc
