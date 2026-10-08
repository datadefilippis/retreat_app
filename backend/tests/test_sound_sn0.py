"""SN0 (8/10/2026, piano Aurya Sound) — Fondamenta: i campi della casa sulle
tracce (copertina, accesso Cerchio/Più, momento, tag, vetrina, voce), le
PLAYLIST (collezione, API, guardie), gli EVENTI di ascolto, i campi
predisposti sull'account. Nessun campo obbligatorio: senza, tutto resta
come ieri."""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


class TestCampiDellaCasa:
    def test_puliture(self):
        from models.frequency_track import (ACCESSI, MOMENTI, TAGS_MAX, clean_accesso, clean_momento,
                                            clean_tags, has_voce)
        assert ACCESSI == ("cerchio", "piu") and MOMENTI == ("mattina", "pausa", "sera", "notte")
        assert clean_accesso("piu") == "piu" and clean_accesso("boh") == "cerchio" and clean_accesso(None) == "cerchio"
        assert clean_momento("sera") == "sera" and clean_momento("") is None
        assert clean_tags(["Respiro", " sonno ", "respiro", 7]) == ["respiro", "sonno", "7"]
        assert len(clean_tags([str(i) for i in range(20)])) == TAGS_MAX
        assert has_voce({"layers": [{"kind": "neuro"}, {"kind": "voice"}]}) and not has_voce({"layers": [{"kind": "audio"}]})

    def test_router_tracce(self):
        src = (BACKEND / "routers" / "frequencies.py").read_text()
        # i campi nuovi nel PATCH, tutti facoltativi
        for campo in ("accesso: Optional[str] = None", "momento: Optional[str] = None", "tags: Optional[list] = None",
                      "in_vetrina: Optional[bool] = None", "guida_nome: Optional[str] = None"):
            assert campo in src.split("class TrackUpdate")[1].split("\nclass ")[0], campo
        # le proiezioni portano i campi (lista, catalogo, pubblico)
        for nome in ("_LIST_PROJECTION", "_CATALOG_PROJECTION", "_PUBLIC_PROJECTION"):
            blocco = src.split(nome + " = ")[1].split("}")[0]
            assert '"cover_url": 1' in blocco and '"accesso": 1' in blocco, nome
        # «con la voce» si materializza alla pubblicazione; l'accesso ha sempre un valore
        assert '"has_voce": has_voce(score)' in src and '"accesso": clean_accesso(track.get("accesso"))' in src
        # la copertina: formati decisi da noi, storage pubblico come le copertine dei corsi
        assert '@router.post("/tracks/{track_id}/copertina")' in src and 'save_public_upload("frequenze"' in src
        assert '@router.delete("/tracks/{track_id}/copertina"' in src

    def test_eventi_di_ascolto(self):
        src = (BACKEND / "routers" / "frequencies.py").read_text()
        assert 'EVENTI_ASCOLTO = ("avvio", "q25", "q50", "q75", "fine")' in src
        assert '@router.post("/public/{slug}/ascolto", status_code=status.HTTP_204_NO_CONTENT)' in src
        assert '@limiter.limit("120/minute")' in src
        # niente from __future__ nel router col limiter (trappola AC2)
        assert "from __future__ import annotations" not in src.split("\nrouter = APIRouter")[0]
        corpo = src.split("async def registra_ascolto")[1].split("\n@router")[0]
        assert '"account_id": account_id' in corpo and "ip" not in corpo.lower().replace("script", "").replace("zip", "")
        assert '@router.get("/tracks/{track_id}/ascolti")' in src and '"completamento"' in src
        db = (BACKEND / "database.py").read_text()
        assert "sound_ascolti_collection = db.sound_ascolti" in db and 'name="sn0_ascolti_traccia"' in db


class TestPlaylist:
    def test_router_e_guardie(self):
        src = (BACKEND / "routers" / "sound_playlists.py").read_text()
        assert 'router = APIRouter(prefix="/frequencies/playlists"' in src
        # solo tracce proprie, pubblicate, non riservate (stessa guardia dei corsi)
        assert 'solo_pubbliche({"id": {"$in": puliti}, "organization_id": org_id, "status": "published"})' in src
        # pubblicare e' della chiave 1
        assert 'if not current_user.get("_sound_composer"):' in src.split("async def pubblica")[1].split("\n@router")[0]
        # il pubblico passa dallo stesso cancello del catalogo
        assert src.count("_has_catalog_access(request)") == 2 and '"error": "locked"' in src
        # le pubblicate senza tracce vive non compaiono
        assert 'if r["tracce_count"]:' in src
        for r in ('@router.get("/mine")', '@router.post("", status_code=status.HTTP_201_CREATED)', '@router.patch("/{playlist_id}")',
                  '@router.post("/{playlist_id}/copertina")', '@router.post("/{playlist_id}/publish")',
                  '@router.post("/{playlist_id}/unpublish")', '@router.delete("/{playlist_id}"', '@router.get("")',
                  '@router.get("/{slug}")', '@router.post("/{slug}/play"'):
            assert r in src, r
        server = (BACKEND / "server.py").read_text()
        assert 'app.include_router(sound_playlists_router.router, prefix="/api")' in server
        db = (BACKEND / "database.py").read_text()
        assert "sound_playlists_collection = db.sound_playlists" in db and 'name="sn0_playlist_slug"' in db

    def test_modelli_e_account(self):
        from routers.sound_playlists import PlaylistCreate, PlaylistUpdate, TRACCE_MAX
        assert TRACCE_MAX == 60
        assert set(PlaylistUpdate.model_fields) == {"title", "description", "accesso", "in_vetrina", "tracce"}
        assert set(PlaylistCreate.model_fields) == {"title", "description", "accesso", "tracce"}
        from models.platform_account import PlatformAccount
        for campo in ("sound_preferenze", "sound_riprendi", "sound_recenti", "stripe_customer_id", "piu"):
            assert campo in PlatformAccount.model_fields and PlatformAccount.model_fields[campo].default is None, campo


class TestFrontend:
    def test_crea_e_player(self):
        casa = (FRONTEND / "features" / "frequenze" / "CasaCampi.jsx").read_text()
        for t in ("fq-campi-casa", "fq-copertina", "fq-momento", "fq-tags", "fq-accesso", "fq-accesso-cerchio",
                  "fq-accesso-piu", "fq-vetrina", "fq-playlist", "fq-playlist-nuova", "fq-playlist-editor",
                  "fq-playlist-tracce", "fq-playlist-aggiungi", "fq-playlist-pubblica"):
            assert f'data-testid="{t}"' in casa, t
        # accesso e vetrina solo sulle pubbliche; la vetrina solo con la chiave 1
        assert "{pubblica && (" in casa and "{composer && (" in casa
        pagina = (FRONTEND / "features" / "frequenze" / "FrequenzePage.js").read_text()
        assert "<CampiCasa traccia={d} onCambio={loadDrafts} composer={!!user?.sound_composer} />" in pagina
        assert "<PlaylistPannello tracce={drafts} composer={!!user?.sound_composer} />" in pagina
        api = (FRONTEND / "api" / "frequencies.js").read_text()
        for m in ("registraAscolto", "uploadCover", "removeCover", "playlists: {", "pubbliche:", "ascolti:"):
            assert m in api, m
        player = (FRONTEND / "features" / "frequenze" / "PublicFrequencyPage.js").read_text()
        assert "ascoltoEvento('avvio', 0);" in player and "[['q25', 0.25], ['q50', 0.5], ['q75', 0.75], ['fine', 0.98]]" in player
        assert "q.get('da') || 'diretto'" in player and "q.get('playlist')" in player
