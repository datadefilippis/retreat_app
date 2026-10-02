"""DV1-DV3 (2/10/2026) — le discipline create dalla regia.

Il codice resta la base (guardia di parita' in test_selettore_discipline);
il registro `discipline_extra` AGGIUNGE, applicato IN PLACE alle strutture
che tutto il backend legge. Slug immutabile, mai cancellazioni (solo
attiva=false, che resta valida per chi l'ha), voci di codice arricchibili
solo di sinonimi, famiglie e categorie di codice, interruttore
DISCIPLINE_VIVE (spento = codice e basta).
"""
import os
from pathlib import Path

import pytest
import requests

RADICE = Path(__file__).resolve().parents[2]
BACKEND = RADICE / "backend"
FE = RADICE / "frontend" / "src"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
ADMIN = (BACKEND / "routers" / "admin.py").read_text(encoding="utf-8")
LIB = (FE / "lib" / "disciplines.js").read_text(encoding="utf-8")


class TestRegistroInPlace:
    def test_il_codice_e_la_base_e_il_registro_aggiunge(self, monkeypatch):
        from models import disciplines as D
        from models import retreat_taxonomy as RT
        from services import discipline_vive as V
        from services.pagine_locali import CATEGORIA_ARTICOLI, FAMIGLIA_DI
        assert all(isinstance(f[2], list) for f in D.DISCIPLINE_FAMILIES)   # mutabili di proposito
        base = dict(D.DISCIPLINES)
        n_massaggio = len(V._famiglia("massaggio")[2])
        try:
            V._applica([{"slug": "prova-vive", "label": "Prova viva", "famiglia": "massaggio",
                         "categoria": "massaggio", "cat_articoli": "massaggio", "sinonimi": ["prova"], "attiva": True},
                        {"slug": "prova-spenta", "label": "Prova spenta", "famiglia": "massaggio",
                         "categoria": "massaggio", "cat_articoli": "massaggio", "attiva": False},
                        {"slug": "reiki", "arricchimento": True, "sinonimi": ["usui"], "attiva": True},
                        {"slug": "boh", "label": "Senza famiglia", "famiglia": "ignota", "attiva": True}])
            assert D.DISCIPLINES["prova-vive"] == "Prova viva" and D.DISCIPLINES["prova-spenta"] == "Prova spenta"
            assert "boh" not in D.DISCIPLINES
            assert D.DISCIPLINES["reiki"] == base["reiki"]                      # la voce di codice non cambia
            assert len(V._famiglia("massaggio")[2]) == n_massaggio + 1          # solo l'attiva entra nel selettore
            assert RT.DISCIPLINA_TO_CATEGORIA["prova-vive"] == "massaggio" and CATEGORIA_ARTICOLI["prova-vive"] == "massaggio"
            assert FAMIGLIA_DI["prova-vive"] == ("massaggio", "Massaggio & Bodywork")
            assert D.clean_disciplines(["prova-vive", "prova-spenta", "boh"]) == ["prova-vive", "prova-spenta"]
            assert V.sinonimi_extra() == {"prova-vive": ["prova"], "reiki": ["usui"]}
            pub = V.payload_pubblico()
            assert "prova-vive" in pub["extra"] and "prova-spenta" not in pub["extra"]
        finally:
            V._applica([])
        assert dict(D.DISCIPLINES) == base and len(V._famiglia("massaggio")[2]) == n_massaggio
        assert "prova-vive" not in RT.DISCIPLINA_TO_CATEGORIA and "prova-vive" not in CATEGORIA_ARTICOLI

    def test_slug_e_validazioni(self):
        from services import discipline_vive as V
        assert V.slugify("Regressione & Vite passate") == "regressione-e-vite-passate"
        assert V.slugify("  Massaggio   Svedese (rilassante)! ") == "massaggio-svedese-rilassante"
        assert V.slug_valido("massaggio-svedese") and not V.slug_valido("Massaggio") and not V.slug_valido("-a-")
        for cattivo in ({"label": "Yoga", "famiglia": "corpo", "categoria": "yoga"},            # slug di codice
                        {"label": "Nuova", "famiglia": "ignota", "categoria": "yoga"},
                        {"label": "Nuova", "famiglia": "corpo", "categoria": "ignota"},
                        {"label": "X", "famiglia": "corpo", "categoria": "yoga"},
                        {"label": "Massaggio Olistico", "famiglia": "massaggio", "categoria": "massaggio"}):  # doppione per nome
            with pytest.raises(ValueError):
                V.valida_nuova(cattivo)
        doc = V.valida_nuova({"label": "Massaggio svedese", "famiglia": "massaggio", "categoria": "massaggio", "sinonimi": "svedese, rilassante, svedese"})
        assert doc["slug"] == "massaggio-svedese" and doc["sinonimi"] == ["svedese", "rilassante"] and doc["attiva"] is True
        assert V.pulisci_sinonimi(["A", " a ", "b"] * 10) == ["a", "b"]

    def test_flag_spento_di_default(self, monkeypatch):
        monkeypatch.delenv("DISCIPLINE_VIVE", raising=False)
        from core.flags import discipline_vive
        assert discipline_vive() is False


class TestRotte:
    def test_regia_e_pubblico(self):
        for r in ('"/discipline"', '"/discipline/anteprima"', '"/discipline/{slug}"'):
            assert r in ADMIN, r
        blocco = ADMIN[ADMIN.index("async def admin_disciplina_crea"):][:2600]
        assert "_motivo_pulito(body.get" in blocco and "await V.ricarica()" in blocco and '"action": "DISCIPLINA_ADMIN_EDIT"' in ADMIN
        mod = ADMIN[ADMIN.index("async def admin_disciplina_modifica"):][:4200]
        assert 'detail="Di una voce di codice si cambiano solo i sinonimi."' in mod
        assert "router.delete" not in ADMIN[ADMIN.index("# ── DV2"):ADMIN.index("async def admin_disciplina_modifica")]
        pub = (BACKEND / "routers" / "public.py").read_text(encoding="utf-8")
        assert '@router.get("/discipline")' in pub and "await assicura_fresco()" in pub
        srv = (BACKEND / "server.py").read_text(encoding="utf-8")
        assert "from services.discipline_vive import ricarica as _ricarica_discipline" in srv
        assert "DISCIPLINE_VIVE=${DISCIPLINE_VIVE:-}" in (RADICE / "docker-compose.prod.yml").read_text(encoding="utf-8")

    def test_dal_vivo(self):
        r = requests.get(f"{BASE_URL}/api/public/discipline", timeout=10)
        if r.status_code != 200:
            pytest.skip("backend su :8000 non riavviato con DV1")
        d = r.json()
        assert len(d["famiglie"]) == 7 and d["totale"] >= 60 and isinstance(d["sinonimi"], dict)
        assert requests.get(f"{BASE_URL}/api/admin/discipline", timeout=10).status_code in (401, 403)
        assert requests.post(f"{BASE_URL}/api/admin/discipline", json={"label": "x"}, timeout=10).status_code in (401, 403)


class TestFrontend:
    def test_il_modulo_legge_il_registro_con_il_codice_di_riserva(self):
        assert "export function famiglieVive()" in LIB and "return VIVO?.famiglie || DISCIPLINE_FAMILIES;" in LIB
        assert "export const disciplineLabel = (slug) => etichette()[slug] || slug;" in LIB
        assert "etichetteCache = { ...m, ...DISCIPLINE_LABELS };" in LIB          # le voci di codice vincono
        assert "api.get('/public/discipline')" in LIB and "applica(null);" in LIB   # rete giu' → codice
        assert "export function useDiscipline()" in LIB and "export async function caricaDiscipline(" in LIB
        assert "...(extraSin[d.slug] || [])" in LIB
        sel = (FE / "components" / "SelettoreDiscipline.js").read_text(encoding="utf-8")
        assert "const { famiglie } = useDiscipline();" in sel and "DISCIPLINE_FAMILIES" not in sel
        idx = (FE / "features" / "storefront" / "OperatorsIndexPage.js").read_text(encoding="utf-8")
        assert "useDiscipline()" in idx and "famiglieVive.map(" in idx
        app = (FE / "App.js").read_text(encoding="utf-8")
        assert "React.useEffect(() => { caricaDiscipline(); }, []);" in app   # lo stile del file: React.useEffect
        tab = (FE / "features" / "admin" / "DisciplineTab.js").read_text(encoding="utf-8")
        for tid in ("admin-discipline", "admin-discipline-aggiungi", "admin-discipline-label", "admin-discipline-slug",
                    "admin-discipline-famiglia", "admin-discipline-categoria", "admin-discipline-articoli",
                    "admin-discipline-sinonimi", "admin-discipline-motivo", "admin-discipline-salva", "admin-discipline-modifica"):
            assert f'data-testid="{tid}"' in tab, tid
        assert "await caricaDiscipline(true);" in tab                       # dopo il salvataggio il registro si ricarica
        op = (FE / "features" / "admin" / "OperatoriPage.js").read_text(encoding="utf-8")
        assert "value: 'discipline'" in op and "<DisciplineTab />" in op
        api = (FE / "api" / "admin.js").read_text(encoding="utf-8")
        for m in ("getDiscipline", "anteprimaDisciplina", "creaDisciplina", "modificaDisciplina"):
            assert m in api, m
