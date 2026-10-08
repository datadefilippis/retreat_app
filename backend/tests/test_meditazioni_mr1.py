"""MR1 (8/10/2026, piano refinement meditazioni) — LE COPERTINE, UN FORMATO SOLO.

Decisione del founder: 1:1. Ogni foto caricata si ritaglia al centro in
quadrato 1200 WebP (traccia e playlist); chi pubblica senza foto riceve la
copertina generata (tono + titolo), salvata come vera cover_url.
"""
import io
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"


class TestQuadra:
    def test_ritaglio_al_centro_e_webp(self):
        from PIL import Image
        from services.copertine_sound import quadra, LATO
        for size in ((1600, 900), (700, 1400), (300, 300)):
            im = Image.new("RGB", size, (90, 140, 120)); b = io.BytesIO(); im.save(b, "PNG")
            data, ext = quadra(b.getvalue())
            out = Image.open(io.BytesIO(data))
            assert ext == "webp" and out.format == "WEBP" and out.size == (LATO, LATO), size

    def test_copertina_generata(self):
        from PIL import Image
        from services.copertine_sound import genera_fallback, tono_di
        assert tono_di("dormire") == "viola" and tono_di("meditare") == "salvia" and tono_di(None) == "oro"
        assert tono_di("dormire", tono="oro") == "oro"
        data, ext = genera_fallback("Respiro lento per la sera", "dormire", "12 minuti")
        out = Image.open(io.BytesIO(data))
        assert out.size == (1200, 1200) and ext == "webp"
        # un titolo lunghissimo non rompe: al massimo tre righe
        data, _ = genera_fallback("x " * 200, "meditare")
        assert Image.open(io.BytesIO(data)).size == (1200, 1200)

    def test_endpoint_e_pubblicazione(self):
        fr = (BACKEND / "routers" / "frequencies.py").read_text()
        up = fr.split('@router.post("/tracks/{track_id}/copertina")')[1].split("\n@router")[0]
        assert "data, ext = quadra(data)" in up and 'content_type="image/webp"' in up
        pub = fr.split("async def publish_track")[1].split("\n@router")[0]
        assert 'if not track.get("cover_url") and visibility != "private":' in pub
        assert "salva_fallback_traccia" in pub
        pl = (BACKEND / "routers" / "sound_playlists.py").read_text()
        assert pl.count("data, ext = quadra(data)") == 1
        assert "salva_fallback_playlist(p, len(tracce))" in pl.split("async def pubblica")[1].split("\n@router")[0]
        # mai bloccare una pubblicazione per una copertina
        srv = (BACKEND / "services" / "copertine_sound.py").read_text()
        assert srv.count("except Exception as exc:  # noqa: BLE001") == 2 and "return None" in srv

    def test_card_quadrate(self):
        css = (FQ / "casa" / "casa.css").read_text()
        assert ".fqz.casa .mcard .mcover{position:relative;aspect-ratio:1;" in css
        assert ".fqz.casa .pl-cover{aspect-ratio:1;" in css

    def test_script(self):
        src = (BACKEND / "scripts" / "copertine_sound_quadrate.py").read_text()
        assert '"--applica"' in src and '".q." in cu or ".gen." in cu' in src    # idempotente
