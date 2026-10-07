"""AU (8/10/2026) — Lezioni AUDIO (mp3 privato con pass a tempo e Range),
lezioni SUONO (una traccia Aurya Sound dell'operatore, solo le sue e solo
col privilegio del comporre), ALLEGATI scaricabili; player dello studente,
anteprime pubbliche, editor."""
import os
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


class TestStorageEPass:
    def test_storage_privato_e_limiti(self):
        from services import lezioni_file as lf
        assert str(lf._ROOT).endswith(os.path.join("private_uploads", "lezioni"))
        assert lf.AUDIO_MAX_BYTES == 50 * 1024 ** 2 and lf.ALLEGATO_MAX_BYTES == 20 * 1024 ** 2
        assert "mp3" in lf.AUDIO_EXT and "exe" not in lf.ALLEGATO_EXT and "pdf" in lf.ALLEGATO_EXT
        # mai il nome dell'utente su disco; traversal chiuso
        import pytest
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            lf.percorso("org", "corso", "lezione", "../x.mp3")
        with pytest.raises(HTTPException):
            lf._cartella("org/../x", "c", "l")

    def test_pass_firmato_e_scoped(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "segreto-di-prova")
        from services import lezioni_file as lf
        tok = lf.firma_pass("corso_audio", e="E1", l="L1")
        assert lf.verifica_pass(tok, "corso_audio", e="E1", l="L1")
        assert not lf.verifica_pass(tok, "corso_audio", e="E1", l="L2")          # altra lezione
        assert not lf.verifica_pass(tok, "corso_allegato", e="E1", l="L1")       # altro scope
        assert not lf.verifica_pass("xx", "corso_audio", e="E1", l="L1")
        assert not lf.verifica_pass(None, "corso_audio", e="E1", l="L1")

    def test_range_a_mano(self, tmp_path):
        from services.lezioni_file import risposta_file
        p = tmp_path / "a.mp3"
        p.write_bytes(bytes(range(100)))

        class R:  # noqa: D401 — una Request finta: bastano gli header
            def __init__(self, rng):
                self.headers = {"range": rng} if rng else {}
        r = risposta_file(p, R("bytes=10-19"), "audio/mpeg")
        assert r.status_code == 206 and r.headers["content-range"] == "bytes 10-19/100" and r.body == bytes(range(10, 20))
        r = risposta_file(p, R("bytes=-5"), "audio/mpeg")
        assert r.status_code == 206 and r.body == bytes(range(95, 100))
        r = risposta_file(p, R("bytes=500-"), "audio/mpeg")
        assert r.status_code == 416
        r = risposta_file(p, R(None), "audio/mpeg", scarica_come="scheda del respiro.pdf")
        assert r.status_code == 200 and 'attachment; filename="scheda del respiro.pdf"' in r.headers["content-disposition"]


class TestRouterOperatore:
    def test_tipi_endpoint_e_guardie(self):
        acc = (BACKEND / "routers" / "accademia.py").read_text()
        assert 'pattern="^(video|testo|audio|suono)$"' in acc
        for r in ('@router.get("/{course_id}/tracce")', '@router.post("/{course_id}/lezioni/{lesson_id}/audio")',
                  '@router.delete("/{course_id}/lezioni/{lesson_id}/audio")', '@router.post("/{course_id}/lezioni/{lesson_id}/allegati")',
                  '@router.delete("/{course_id}/lezioni/{lesson_id}/allegati/{allegato_id}")'):
            assert r in acc, r
        # SOLO le tracce dell'org, SOLO col privilegio del comporre (deciso in studio_access)
        mia = acc.split("async def _traccia_mia")[1].split("\n@router")[0]
        assert '{"id": track_id, "organization_id": org_id}' in mia and "if not await _sound_attivo(org_id):" in mia
        assert "from services.studio_access import org_per_studio, studio_attivo" in acc
        lista = acc.split("async def tracce_mie")[1].split("\n@router")[0]
        assert '{"organization_id": org_id}' in lista and 'return {"tracce": [], "sound_attivo": False}' in lista
        # pronta: audio = file, suono = traccia; la quota conta anche l'audio
        assert 'return bool((l.get("audio") or {}).get("filename"))' in acc and 'return bool((l.get("suono") or {}).get("track_id"))' in acc
        assert "usati += await _audio_bytes(org_id)" in acc
        # togliere la lezione toglie i file
        assert "lezioni_file.cancella_lezione(org_id, course_id, lesson_id)" in acc
        from models.course import Lesson
        assert "resources" in Lesson.model_fields


class TestStudenteEPubblico:
    def test_play_url_per_tipo_e_consegna(self):
        pc = (BACKEND / "routers" / "platform_corsi.py").read_text()
        assert 'if lezione.get("tipo") == "audio":' in pc and 'if lezione.get("tipo") == "suono":' in pc
        assert 'lezioni_file.firma_pass("corso_audio", e=enrollment_id, l=lesson_id)' in pc
        assert '@router.get("/{enrollment_id}/lezioni/{lesson_id}/audio")' in pc
        assert '@router.get("/{enrollment_id}/lezioni/{lesson_id}/allegati/{allegato_id}")' in pc
        # la consegna richiede pass valido E iscrizione viva (revoca → 403 anche coi pass emessi)
        consegna = pc.split("async def ascolta_audio")[1].split("\n@router")[0]
        assert 'verifica_pass(token, "corso_audio", e=enrollment_id, l=lesson_id)' in consegna and "_apri_o_403(enr" in consegna
        # la ricetta: mai l'org
        tr = pc.split("async def payload_traccia")[1].split("\n@router")[0]
        assert '"organization_id"' not in tr and '"score": 1' in tr
        assert '"audio_pronto": bool((l.get("audio") or {}).get("filename"))' in pc

    def test_anteprime_pubbliche(self):
        pub = (BACKEND / "routers" / "public.py").read_text()
        assert 'not in ("video", "audio", "suono")' in pub
        assert 'lezioni_file.firma_pass("corso_anteprima_audio", o=org["id"], c=c["id"], l=lesson_id)' in pub
        assert '@router.get("/corso/{org_slug}/{slug}/anteprima/{lesson_id}/audio")' in pub
        assert '"allegati": sum(1 for r in (l.get("resources") or []) if r.get("filename"))' in pub


class TestFrontend:
    def test_editor(self):
        e = (FRONTEND / "features" / "accademia" / "LezioniEditor.js").read_text()
        for t in ("aggiungi-audio", "aggiungi-suono", "audio-dropzone", "lezione-suono", "suono-select", "lezione-allegati"):
            assert f'data-testid="{t}"' in e, t
        assert "{soundAttivo && <Bottone" in e            # il tipo «suono» esiste solo col privilegio
        assert "durataAudio(file)" in e                     # la durata la misura il browser
        api = (FRONTEND / "api" / "accademia.js").read_text()
        for m in ("audioCarica", "audioTogli", "tracce:", "allegatoCarica", "allegatoTogli", "export function durataAudio"):
            assert m in api, m

    def test_player_e_landing(self):
        sp = (FRONTEND / "features" / "accademia" / "player" / "SuonoPlayer.jsx").read_text()
        assert "creaAscolto(traccia.score" in sp
        assert "SafetyCurtain" not in sp and "Headphones" not in sp      # founder 8/10: niente sipario, niente testi in piu'
        ap = (FRONTEND / "features" / "accademia" / "player" / "AudioPlayer.jsx").read_text()
        assert "<audio ref={ref}" in ap and 'controlsList="nodownload"' in ap
        st = (FRONTEND / "features" / "account" / "CorsoStudentePage.js").read_text()
        assert "selectedLesson.tipo === 'audio' || selectedLesson.tipo === 'suono'" in st
        assert "<AudioPlayer src=" in st and "<SuonoPlayer traccia={media.traccia}" in st
        assert "(selectedLesson.resources || []).length > 0" in st
        land = (FRONTEND / "features" / "storefront" / "CorsoLandingPage.js").read_text()
        assert "if (media?.tipo === 'audio')" in land and "if (media?.tipo === 'suono')" in land
        assert "'Guarda gratis' : 'Ascolta gratis'" in land
