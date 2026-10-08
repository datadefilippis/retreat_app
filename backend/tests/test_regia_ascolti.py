"""CS4 (8/10/2026 sera) — LA REGIA DEGLI ASCOLTI (system admin → Sound → Ascolti).

Il founder: «per ogni utente quali registrazioni ascolta, quante volte, quando,
se la completa, per quanti minuti; uno score di chi segue di più; chi aggiunge
ai preferiti». Gli eventi ci sono gia' (sound_ascolti): la regia li legge e li
riassume. Lo score «seguito» e' una somma leggibile, pinzata qui.
"""
import os
from pathlib import Path

import pytest
import requests

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
SCRATCH = Path("/private/tmp/claude-501/-Users-davidedefilippis-Desktop-BI-PMI/8e77c3c7-13d9-45f8-8159-d2aae3dd7044/scratchpad")


class TestScore:
    def test_la_formula_e_una_tabella(self):
        src = (BACKEND / "services" / "ascolti_regia.py").read_text()
        assert 'PESI_SEGUITO = {"frequenza": 30, "costanza": 20, "profondita": 25, "ampiezza": 15, "affetto": 10}' in src
        assert 'TETTI_SEGUITO = {"giorni_attivi": 12, "settimane": 8, "preferite": 5}' in src

    def test_lo_score_si_legge(self):
        import sys
        sys.path.insert(0, str(BACKEND))
        from services.ascolti_regia import score_seguito
        pieno = score_seguito({"giorni_attivi_30": 12, "settimane_consecutive": 8, "completati": 10, "ascolti": 10, "titoli_diversi": 20, "preferite": 5}, 20)
        assert pieno["score"] == 100 and all(v == 1.0 for v in pieno["parti"].values())
        nulla = score_seguito({"ascolti": 0}, 20)
        assert nulla["score"] == 0
        meta = score_seguito({"giorni_attivi_30": 6, "settimane_consecutive": 4, "completati": 5, "ascolti": 10, "titoli_diversi": 10, "preferite": 0}, 20)
        assert meta["score"] == 45 and meta["parti"] == {"frequenza": 0.5, "costanza": 0.5, "profondita": 0.5, "ampiezza": 0.5, "affetto": 0.0}
        # i tetti: oltre non si sale (chi ascolta ogni giorno non deve «vincere» per inerzia)
        assert score_seguito({"giorni_attivi_30": 30, "ascolti": 1, "completati": 1}, 1)["parti"]["frequenza"] == 1.0


class TestRotte:
    def test_il_router_e_registrato_e_solo_admin(self):
        srv = (BACKEND / "server.py").read_text()
        assert 'app.include_router(admin_sound_ascolti_router.router, prefix="/api")' in srv
        r = (BACKEND / "routers" / "admin_sound_ascolti.py").read_text()
        assert r.count("Depends(require_system_admin)") == 6
        for via in ('"/panoramica"', '"/meditazioni"', '"/meditazioni/{slug}"', '"/persone"', '"/persone/{account_id}"', '"/export.csv"'):
            assert via in r, via

    def test_la_sezione_e_in_regia(self):
        page = (FRONTEND / "features" / "admin" / "SoundAccessPage.js").read_text()
        assert "<SoundAscoltiSezione />" in page
        sez = (FRONTEND / "features" / "admin" / "SoundAscoltiSezione.jsx").read_text()
        for tid in ("admin-sound-ascolti", "admin-ascolti-periodo", "admin-ascolti-meditazioni", "admin-ascolti-persone", "admin-ascolti-dettaglio", "admin-ascolti-linea"):
            assert f'"{tid}"' in sez, tid
        assert "data-testid={`admin-ascolti-vista-${v}`}" in sez
        assert "/admin/sound/ascolti/export.csv" in sez and "responseType: 'blob'" in sez
        # la regia guarda, non tocca
        assert "api.post" not in sez and "api.patch" not in sez and "api.delete" not in sez

    def test_dal_vivo(self):
        tok = SCRATCH / "admin-token.txt"
        demo = SCRATCH / "demo-token.txt"
        if not tok.exists():
            pytest.skip("token admin locale assente")
        h = {"Authorization": f"Bearer {tok.read_text().strip()}"}
        try:
            r = requests.get(f"{BASE_URL}/api/admin/sound/ascolti/panoramica", params={"periodo": "tutto"}, headers=h, timeout=8)
        except requests.RequestException:
            pytest.skip("server locale assente")
        if r.status_code != 200:
            pytest.skip("token admin scaduto")
        d = r.json()
        assert set(d) >= {"ascolti", "persone", "minuti", "completamento", "preferiti_aggiunti", "per_giorno", "per_fascia"}
        p = requests.get(f"{BASE_URL}/api/admin/sound/ascolti/persone", params={"periodo": "tutto"}, headers=h, timeout=8).json()
        assert "pesi" in p and all({"account_id", "score", "parti", "ascolti", "minuti", "completati"} <= set(x) for x in p["items"])
        m = requests.get(f"{BASE_URL}/api/admin/sound/ascolti/meditazioni", params={"periodo": "tutto"}, headers=h, timeout=8).json()
        assert all({"slug", "titolo", "ascolti", "completamento", "abbandono_medio", "preferiti"} <= set(x) for x in m["items"])
        c = requests.get(f"{BASE_URL}/api/admin/sound/ascolti/export.csv", params={"vista": "persone", "periodo": "tutto"}, headers=h, timeout=8)
        assert c.status_code == 200 and c.text.startswith("nome,email,")
        if demo.exists():
            r2 = requests.get(f"{BASE_URL}/api/admin/sound/ascolti/panoramica", headers={"Authorization": f"Bearer {demo.read_text().strip()}"}, timeout=8)
            assert r2.status_code in (401, 403)


class TestPrivacyCs5:
    def test_export_e_cancellazione_portano_gli_ascolti(self):
        src = (BACKEND / "services" / "platform_account_service.py").read_text()
        exp = src.split("async def export_account_data")[1].split("async def delete_account")[0]
        assert '"sound": {' in exp and '"ascolti": ascolti' in exp and '"preferite": preferite' in exp and '"riprendi"' in exp
        dele = src.split("async def delete_account")[1]
        assert '_db.sound_ascolti.delete_many({"account_id": aid})' in dele
        assert '_db.frequency_favorites.delete_many({"platform_account_id": aid})' in dele
        assert '"sound_ascolti_deleted"' in dele

    def test_conservazione_24_mesi(self):
        serv = (BACKEND / "services" / "ascolti_regia.py").read_text()
        assert "CONSERVAZIONE_GIORNI = 730" in serv and "async def conserva()" in serv
        assert "from services.ascolti_regia import conserva as _conserva_ascolti" in (BACKEND / "server.py").read_text()
        assert "--applica" in (BACKEND / "scripts" / "ascolti_conservazione.py").read_text()

    def test_chi_ascolta_senza_account_resta_anonimo(self):
        # chi ascolta col Cerchio senza account non entra in «Persone»
        serv = (BACKEND / "services" / "ascolti_regia.py").read_text()
        assert '{"account_id": {"$ne": None}}' in serv
    # L'informativa (riga sugli ascolti, conservazione 24 mesi) cambia la VERSIONE
    # legale (CURRENT_VERSION_HASH) e chiede un nuovo consenso: si fa con una
    # decisione del founder, non in questo lotto (docs/PIANO_CASA_CONSIGLI §4b).
