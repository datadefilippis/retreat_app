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
        for via in ('"/panoramica"', '"/meditazioni"', '"/meditazioni/{slug}"', '"/persone"', '"/persone/{persona_id}"', '"/export.csv"'):
            assert via in r, via

    def test_la_sezione_e_in_regia(self):
        page = (FRONTEND / "features" / "admin" / "SoundAccessPage.js").read_text()
        assert "<SoundAscoltiSezione />" in page
        # 8/10 sera (founder): tre sotto-pagine commutabili come il Cerchio
        assert "import AdminPageShell from './AdminPageShell';" in page
        for tab in ("{ value: 'compositori', label: 'Compositori'", "{ value: 'categorie', label: 'Categorie meditazioni'", "{ value: 'ascolti', label: 'Gli ascolti'"):
            assert tab in page, tab
        assert 'tabs={TABS} testid="admin-sound"' in page
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
        assert "pesi" in p and all({"persona_id", "account_id", "tipo", "score", "parti", "ascolti", "minuti", "completati"} <= set(x) for x in p["items"])
        m = requests.get(f"{BASE_URL}/api/admin/sound/ascolti/meditazioni", params={"periodo": "tutto"}, headers=h, timeout=8).json()
        assert all({"slug", "titolo", "ascolti", "completamento", "abbandono_medio", "preferiti"} <= set(x) for x in m["items"])
        c = requests.get(f"{BASE_URL}/api/admin/sound/ascolti/export.csv", params={"vista": "persone", "periodo": "tutto"}, headers=h, timeout=8)
        assert c.status_code == 200 and c.text.startswith("nome,email,tipo,")
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

    def test_chi_ascolta_dal_cerchio_e_una_persona(self):
        # 8/10 sera (founder): chi ascolta col Cerchio senza account entra in
        # «Persone» con nome ed email dell'iscrizione; l'evento porta l'email,
        # la regia la riconduce all'account se la stessa email ne apre uno
        serv = (BACKEND / "services" / "ascolti_regia.py").read_text()
        assert 'FILTRO_PERSONE = {"$or": [{"account_id": {"$ne": None}}, {"subscriber_email": {"$ne": None}}]}' in serv
        assert 'PREFISSO_CERCHIO = "cerchio:"' in serv and "async def _sessioni_unite" in serv
        assert '"tipo": "cerchio"' in serv and "async def scorda_iscritto" in serv
        fq = (BACKEND / "routers" / "frequencies.py").read_text()
        assert '"account_id": account_id, "cerchio": cerchio, "subscriber_email": subscriber_email,' in fq
        # chi lascia il Cerchio (un clic, l'admin, la cancellazione) non resta col nome
        sub = (BACKEND / "routers" / "subscribers.py").read_text()
        assert sub.count("await _scorda_ascolti(email)") == 3
        assert "from services.ascolti_regia import scorda_iscritto" in sub

    def test_il_cuore_senza_account_passa_dalla_porta(self):
        # 8/10 sera (founder): «per i preferiti senza account aggiungiamo
        # l'accettazione» — la porta unica (casella legale) DENTRO l'invito,
        # il cuore toccato resta in attesa e si salva da solo appena dentro
        hook = (FRONTEND / "features" / "frequenze" / "casa" / "preferite.js").read_text()
        assert "const IN_ATTESA_KEY = 'fqz_cuore_in_attesa';" in hook
        assert "async function applicaInAttesa()" in hook and "return applicaInAttesa();" in hook
        assert "const dopoAccount = useCallback(async () => {" in hook
        cuore = (FRONTEND / "features" / "frequenze" / "casa" / "Cuore.jsx").read_text()
        assert "import PortaAurya from '../../account/PortaAurya';" in cuore
        assert '<PortaAurya vista="crea" emailIniziale={emailDellaProva() || \'\'} contesto="preferite"' in cuore
        assert "onDentro={(me) => { onDentro?.(me); onChiudi?.(); }}" in cuore
        assert "window.location.href" not in cuore        # niente uscita dalla pagina
        for rel in ("casa/MeditazioniCasa.jsx", "casa/PlaylistPage.jsx", "PublicFrequencyPage.js"):
            src = (FRONTEND / "features" / "frequenze" / rel).read_text()
            assert "onDentro={pref.dopoAccount} />" in src, rel
        css = (FRONTEND / "features" / "frequenze" / "casa" / "casa.css").read_text()
        assert ".fqz .invito-porta{" in css

    def test_informativa_v213_con_la_riga_degli_ascolti(self):
        import hashlib
        from core.legal_versions import CURRENT_VERSION_HASH, CURRENT_VERSION_TAG
        assert CURRENT_VERSION_TAG == "v2.13"
        priv = (BACKEND / "legal" / "privacy_it.md").read_text("utf-8")
        terms = (BACKEND / "legal" / "terms_it.md").read_text("utf-8")
        assert CURRENT_VERSION_HASH == hashlib.sha256((priv + "\n\n--- TERMS BUNDLE ---\n\n" + terms).encode()).hexdigest()[:16]
        assert "| 7-quater | Ascolto delle meditazioni di Aurya Sound" in priv
        assert "nome ed email dell'iscrizione" in priv and "Mai l'indirizzo IP" in priv
        assert "| Ascolti delle meditazioni (art. 4, riga 7-quater) | 24 mesi |" in priv
        for lang in ("en", "de", "fr"):
            t = (BACKEND / "legal" / f"privacy_{lang}.md").read_text("utf-8")
            assert t.count("7-quater") == 2, lang
