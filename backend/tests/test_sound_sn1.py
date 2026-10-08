"""SN1 (8/10/2026, piano Aurya Sound §4) — LA CASA E LA PASSERELLA.

/meditazioni ridisegnata come un'app di meditazione (di oggi, cerca e
filtri, righe con copertine, barra in basso), la pagina della playlist,
/sound che diventa l'hub del suono, la passerella a tre porte, il player
che sa di essere «parte di» una playlist. Tutto dietro SOUND_CASA_NUOVA:
le pagine vecchie restano intatte accanto (i pin degli altri test le
leggono ancora) e la soglia del Cerchio e' UNA, condivisa.
"""
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"


class TestFlagEPagineAccanto:
    def test_flag(self):
        assert "export const SOUND_CASA_NUOVA = true;" in (FQ / "stato.js").read_text()

    def test_meditazioni_wrapper_e_soglia_condivisa(self):
        src = (FQ / "MeditazioniPage.js").read_text()
        assert "export function SogliaCerchio({ teaserCount = 0, onSbloccato })" in src
        assert "function MeditazioniPageVecchia()" in src
        assert "export default function MeditazioniPage()" in src
        # il ciclo (la casa importa la soglia da qui) si spezza col lazy
        assert "const MeditazioniCasa = React.lazy(() => import('./casa/MeditazioniCasa'));" in src
        assert "SOUND_CASA_NUOVA" in src.split("export default function MeditazioniPage()")[1]
        # la vetrina vecchia usa la soglia condivisa, non una copia
        assert "<SogliaCerchio teaserCount={teaserCount} onSbloccato={() => loadCatalog()} />" in src

    def test_sound_wrapper(self):
        src = (FQ / "SoundHomePage.jsx").read_text()
        assert "return SOUND_HUB_SEMPLICE && SOUND_CASA_NUOVA ? <SoundHubPage /> : <SoundHomePageVecchia />;" in src   # MR6: la landing torna
        assert "function SoundHomePageVecchia()" in src
        # la rotta resta il letterale che gli altri test pretendono
        app = (FRONTEND / "App.js").read_text()
        assert 'path="/sound" element={<SoundHomePage />}' in app
        assert 'path="/meditazioni/playlist/:slug" element={<PlaylistPage />}' in app
        assert "import(\"./features/frequenze/casa/PlaylistPage\")" in app


class TestLaCasa:
    def test_casa_meditazioni(self):
        src = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        # il cancello e' lo stesso: senza sblocco si vede la soglia del Cerchio
        assert "if (locked) return <SogliaCerchio teaserCount={teaserCount} onSbloccato={() => carica()} />;" in src
        assert "from '../MeditazioniPage'" in src
        # i due modi di chiedere il catalogo, come prima (account → platformApi, altrimenti la prova)
        assert "platformApi.get('/frequencies/catalog'" in src and "frequenciesAPI.getCatalog(prova(), before || null)" in src   # MR7: account + prova
        assert "frequenciesAPI.playlists.pubbliche(prova())" in src and "platformApi.get('/frequencies/playlists')" in src
        # le righe della casa
        for riga in ("casa-oggi", "casa-cerca", "casa-filtri", "casa-barra", "casa-card", "casa-playlist-card"):
            assert f'data-testid="{riga}"' in src or f"data-testid={{`{riga}" in src, riga
        for riga in ('id="playlist"', 'id="per-iniziare"', 'id="novita"', 'id="piu-ascoltate"', 'id="con-la-voce"', 'id="solo-suono"', 'id="tuo-spazio"'):
            assert riga in src, riga
        # la card porta la provenienza al player (SN0: ?da=, ?playlist=)
        assert "const href = `/frequenze/${t.slug}?da=${da}${playlist ? `&playlist=${encodeURIComponent(playlist)}` : ''}`;" in src
        # la vetrina: a rotazione fra le in_vetrina (SN2), altrimenti la piu' recente
        assert "inVetrina[giorno % inVetrina.length]" in src and "tutte[0]" in src
        # le preferite chiedono l'account, mai l'email (MR2: la regola vive nell'hook condiviso)
        assert "if (!conto) { setChiediAccount(true); return; }" in (FQ / "casa" / "preferite.js").read_text()
        # la barra in basso: cinque gesti
        barra = src.split('data-testid="casa-barra"')[1].split("</nav>")[0]
        for voce in ("Esplora", "Playlist", "Cerca", "I tuoi", "Impara"):   # SN3: «Preferite» → «I tuoi»
            assert voce in barra, voce
        # niente motore qui dentro
        assert "startPreview" not in src and "engine/" not in src

    def test_css_barra_solo_telefono(self):
        css = (FQ / "casa" / "casa.css").read_text()
        assert "@media(min-width:900px){.fqz.casa .casa-barra{display:none}}" in css
        assert ".fqz.casa .casa-barra{position:fixed;left:0;right:0;bottom:0" in css
        # il cuore nel bottone: senza il padding dei bottoni Sound il cuore spariva (2px)
        assert "padding:0;min-height:0" in css.split(".mcuore{")[1].split("}")[0]

    def test_pagina_playlist(self):
        src = (FQ / "casa" / "PlaylistPage.jsx").read_text()
        assert "frequenciesAPI.playlists.pubblica(slug, prova())" in src and "platformApi.get(`/frequencies/playlists/${slug}`)" in src
        assert "setStato(st === 403 ? 'locked' : 'notfound')" in src
        assert "if (stato === 'locked') return <SogliaCerchio teaserCount={0} onSbloccato={carica} />;" in src
        assert "?da=playlist&playlist=${encodeURIComponent(p.slug)}" in src
        assert 'data-testid="casa-playlist-ascolta"' in src and 'data-testid="casa-playlist-lista"' in src

    def test_hub_del_suono(self):
        src = (FQ / "casa" / "SoundHubPage.jsx").read_text()
        for porta in ("'/sound/esplora'", "'/sound/impara'", "'/sound/lab'", 'to="/meditazioni"'):
            assert porta in src, porta
        assert "canonicalPath: '/sound'" in src
        # il Visual non e' in menu (fuori dalla mappa a tre porte)
        assert "/sound/visual" not in src


class TestPasserellaEPlayer:
    def test_passerella_tre_porte(self):
        src = (FQ / "SoundTopbar.jsx").read_text()
        assert "{ to: '/meditazioni', label: 'Meditazioni' },\n  { to: '/sound', label: 'Il suono' },\n];" in src
        assert "const CASA_VOCE_CREA = { to: '/sound/crea', label: 'Crea' };" in src
        assert "(puoComporre ? [...CASA_PASSERELLA, CASA_VOCE_CREA] : CASA_PASSERELLA)" in src   # MR7: solo chi puo' comporre
        # la vecchia resta, letterale, per i pin degli altri test
        assert "label: 'Aurya Lab'" in src and "{ to: '/sound/esplora', label: 'Aurya Sound' }" in src

    def test_player_parte_di(self):
        src = (FQ / "PublicFrequencyPage.js").read_text()
        assert "import { Link, useParams, useNavigate } from 'react-router-dom';" in src
        assert 'data-testid="fqz-parte-di"' in src and 'data-testid="fqz-pl-next"' in src
        # la playlist si chiede con la stessa prova del catalogo
        assert "frequenciesAPI.playlists.pubblica(ps, prova())" in src
        # a fine traccia: la prossima, solo se sbloccato
        assert "if (prossima && unlocked) navigate(`${prossima}&auto=1`);" in src
        assert src.count("fineTracciaRef.current?.()") == 3   # master, continuo, synth (mai l'anteprima)
        # il tentativo di partire da solo: una volta, solo dentro una playlist
        assert "if (!/[?&]auto=1/.test(window.location.search)) return;" in src
        assert "import './casa/casa.css';" in src


class TestServer:
    def test_meta_playlist(self):
        """Dal vivo, contro il server locale (il client Motor del modulo resta
        legato al loop dei test precedenti: in suite un test async sul DB
        muore con «Event loop is closed»). Dati con pymongo, pagina via HTTP."""
        import os
        import requests
        try:
            from pymongo import MongoClient
            db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
                             serverSelectionTimeoutMS=2000)[os.environ.get("DB_NAME", "retreat_dev")]
            db.command("ping")
        except Exception:
            pytest.skip("Mongo non raggiungibile")
        base = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
        slug = "sn1-test-playlist"
        ids = ["sn1-t1", "sn1-t2"]
        db.sound_playlists.delete_many({"slug": slug})
        db.frequency_tracks.delete_many({"id": {"$in": ids}})
        db.frequency_tracks.insert_many([
            {"id": "sn1-t1", "slug": "sn1-traccia-uno", "title": "Uno", "status": "published", "visibility": "public",
             "organization_id": "sn1-org", "score": {"duration_sec": 60, "layers": []}},
            {"id": "sn1-t2", "slug": "sn1-traccia-due", "title": "Due", "status": "published", "visibility": "private",
             "organization_id": "sn1-org", "score": {"duration_sec": 60, "layers": []}},
        ])
        db.sound_playlists.insert_one({
            "id": "sn1-pl", "slug": slug, "title": "Sere di prova", "description": "", "status": "published",
            "organization_id": "sn1-org", "tracce": ["sn1-t2", "sn1-t1"], "cover_url": "/uploads/frequenze/x.jpg"})
        try:
            try:
                r = requests.get(f"{base}/__seo/meditazioni/playlist/{slug}", timeout=10)
            except requests.RequestException:
                pytest.skip("server locale non raggiungibile")
            assert r.status_code == 200
            html = r.text
            assert "<title>Sere di prova · Playlist | Aurya Sound</title>" in html
            assert f"/meditazioni/playlist/{slug}" in html and "/uploads/frequenze/x.jpg" in html
            # la traccia riservata non compare, l'ordine e' quello della playlist
            assert '"@type": "ItemList"' in html and '"numberOfItems": 1' in html
            assert "/frequenze/sn1-traccia-uno" in html and "sn1-traccia-due" not in html
            # una playlist in bozza non e' una pagina: shell neutra, niente titolo
            # (slug a parte: la shell tiene in cache la pagina gia' servita)
            db.sound_playlists.insert_one({
                "id": "sn1-pl-bozza", "slug": f"{slug}-bozza", "title": "Bozza di prova", "status": "draft",
                "organization_id": "sn1-org", "tracce": ["sn1-t1"]})
            r2 = requests.get(f"{base}/__seo/meditazioni/playlist/{slug}-bozza", timeout=10)
            assert "Bozza di prova" not in r2.text
        finally:
            db.sound_playlists.delete_many({"slug": {"$in": [slug, f"{slug}-bozza"]}})
            db.frequency_tracks.delete_many({"id": {"$in": ids}})

    def test_sitemap_playlist(self):
        src = (BACKEND / "routers" / "seo.py").read_text()
        blocco = src.split("# SN1 (8/10)")[1].split("except Exception")[0]
        assert '{"status": "published", "slug": {"$nin": [None, ""]}}' in blocco
        assert 'f"{base}/meditazioni/playlist/{p[\'slug\']}"' in blocco
