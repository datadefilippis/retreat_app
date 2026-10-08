"""MR4 (8/10/2026, piano refinement meditazioni) — LE CATEGORIE DAL SYSTEM ADMIN.

Un registro vivo (sound_categorie) con un seme solo, «Meditazioni guidate»;
la Regia aggiunge/rinomina/riordina/spegne senza deploy; in Crea la
categoria si sceglie alla creazione ed e' obbligatoria per pubblicare in
pubblico; la casa filtra e mette in riga per categoria; `intent` resta
interno.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"


class TestRegistro:
    def test_seme_e_regole(self):
        from services import categorie_sound as C
        assert C.SEME["slug"] == "meditazioni-guidate" and C.SEME["label"] == "Meditazioni guidate"
        d = C.valida_nuova({"label": "Respiro guidato", "tono": "acqua"})
        assert d["slug"] == "respiro-guidato" and d["attiva"] is True and d["ordine"] == 100
        for cattiva in ({"label": "x"}, {"label": "Ok", "tono": "rosa"}, {"label": "Ok", "ordine": "boh"}):
            try:
                C.valida_nuova(cattiva)
                raise AssertionError(cattiva)
            except ValueError:
                pass
        try:
            C.valida_modifica({"slug": "altro"})
            raise AssertionError("lo slug e' immutabile")
        except ValueError:
            pass
        assert C.valida_modifica({"attiva": False, "ordine": "3"}) == {"attiva": False, "ordine": 3}

    def test_admin_router(self):
        src = (BACKEND / "routers" / "admin_sound_categorie.py").read_text()
        assert 'router = APIRouter(prefix="/admin/sound/categorie"' in src
        assert src.count("Depends(require_system_admin)") == 3 and "@router.delete" not in src   # mai cancellare
        assert "await C.ricarica()" in src
        assert "admin_sound_categorie_router.router" in (BACKEND / "server.py").read_text()


class TestTraccia:
    def test_modelli_e_guardie(self):
        src = (BACKEND / "routers" / "frequencies.py").read_text()
        assert '@router.get("/categorie")' in src
        for nome in ("_LIST_PROJECTION", "_CATALOG_PROJECTION", "_PUBLIC_PROJECTION"):
            assert '"categoria": 1' in src.split(nome + " = ")[1].split("}")[0], nome
        assert "categoria: Optional[str] = None" in src.split("class TrackCreate")[1].split("\nclass ")[0]
        assert '"categoria": await _categoria_valida(payload.categoria)' in src
        pub = src.split("async def publish_track")[1].split("\n@router")[0]
        assert 'if visibility == "public" and not await _categoria_esiste(track.get("categoria")):' in pub
        # riservata: nessun obbligo (si condivide coi propri clienti)
        assert "Scegli una categoria prima di pubblicare" in pub
        pl = (BACKEND / "routers" / "sound_playlists.py").read_text()
        assert "categoria: Optional[str] = None" in pl and '"categoria")}' in pl

    def test_script_seme(self):
        src = (BACKEND / "scripts" / "categorie_sound_seme.py").read_text()
        assert '"--applica"' in src and '{"$set": {"categoria": seme}}' in src


class TestCreaECasa:
    def test_crea(self):
        src = ((FQ / "FrequenzePage.js").read_text() + (FQ / "crea" / "CreaVista.jsx").read_text() + (FQ / "crea" / "TracceVista.jsx").read_text())
        assert 'data-testid="fq-categoria"' in src
        assert "frequenciesAPI.create({ title: name, score: scorePayload(), intent, categoria })" in src
        assert "frequenciesAPI.update(trackId, { title: name, score: scorePayload(), intent, categoria })" in src
        campi = (FQ / "CasaCampi.jsx").read_text()
        assert "export function useCategorie()" in campi and 'data-testid="fq-categoria-campo"' in campi
        api = (FRONTEND / "api" / "frequencies.js").read_text()
        assert "categorie: () => api.get('/frequencies/categorie')" in api

    def test_casa_per_categoria(self):
        src = (FQ / "casa" / "MeditazioniCasa.jsx").read_text()
        assert "frequenciesAPI.categorie()" in src
        assert "if (intent && (t.categoria || '') !== intent) return false;" in src
        assert "const categoriePresenti = categorie.filter((c) => tutte.some((t) => t.categoria === c.slug));" in src
        assert "id={`cat-${c.slug}`}" in src and "data-testid={`casa-filtro-${c.slug}`}" in src
        # ?categoria= e' un indirizzo condivisibile
        assert "get('categoria')" in src and "u.searchParams.set('categoria', intent)" in src
        # le righe per intento di SN1 non ci sono piu' (una sola verita': la categoria)
        assert "intentiPresenti" not in src

    def test_regia(self):
        adm = (FRONTEND / "features" / "admin" / "SoundCategorieSezione.jsx").read_text()
        assert "api.post('/admin/sound/categorie', nuova)" in adm and "api.patch(`/admin/sound/categorie/${slug}`, campi)" in adm
        assert "Spegni" in adm and "Cancella" not in adm
        assert "<SoundCategorieSezione />" in (FRONTEND / "features" / "admin" / "SoundAccessPage.js").read_text()
