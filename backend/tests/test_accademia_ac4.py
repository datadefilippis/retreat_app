"""AC4 (7/10/2026) — Regia e rifinitura: colonna Strumenti con gli interruttori
in regia Operatori, checkout del corso con l'account Aurya (niente secondo
account legacy), pagina di successo e landing «già tuo», /costi coi corsi,
sblocco v2.13 pronto ma NON applicato."""
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


class TestRegia:
    def test_specchietto_strumenti_nel_modello_e_nella_lista(self):
        from models.admin import OrgSummary
        assert "strumenti" in OrgSummary.model_fields
        adm = (BACKEND / "routers" / "admin.py").read_text()
        assert "async def _strumenti_batch(org_ids: list, docs: list) -> dict:" in adm
        assert 'strumenti = await _strumenti_batch(org_ids, docs)' in adm
        assert '"strumenti": strumenti.get(d["id"])' in adm and 'strumenti=regia.get("strumenti")' in adm
        # i due interruttori sono i kill switch di module_access, letti dai flag dell'org
        assert "FLAG_PRODOTTI_SPENTO" in adm and "FLAG_ACCADEMIA_SPENTO" in adm
        repo = (BACKEND / "repositories" / "admin_repository.py").read_text()
        assert '"feature_flags": 1' in repo and '"integrations.bunny_libraries.quota": 1' in repo

    def test_colonna_e_interruttori_nel_frontend(self):
        tab = (FRONTEND / "features" / "admin" / "OrganizationsTab.js").read_text()
        assert "<TableHead>Strumenti</TableHead>" in tab
        for t in ("org-strumenti", "org-toggle-prodotti", "org-toggle-accademia"):
            assert f'data-testid="{t}"' in tab, t
        assert "adminAPI.setFeatureFlag(org.id, flag, !spento)" in tab
        api = (FRONTEND / "api" / "admin.js").read_text()
        assert "api.put(`/admin/feature-flags/${orgId}`, { flag_name: flagName, value })" in api
        # il flag arriva al router esistente dei feature flag (system admin, audit)
        ff = (BACKEND / "routers" / "admin_feature_flags.py").read_text()
        assert 'router = APIRouter(prefix="/admin/feature-flags"' in ff


class TestKillSwitchPubblico:
    def test_il_flag_spegne_anche_il_pubblico(self):
        pub = (BACKEND / "routers" / "public.py").read_text()
        assert "async def _modulo_spento(org_id: str, flag: str) -> bool:" in pub
        corsi = pub.split("async def _operator_corsi")[1].split("\nclass ")[0]
        assert "if await _modulo_spento(org_id, FLAG_ACCADEMIA_SPENTO):\n        return []" in corsi
        prod = pub.split("async def _operator_prodotti")[1].split("\n@router")[0]
        assert "if await _modulo_spento(org_id, FLAG_PRODOTTI_SPENTO):\n        return []" in prod
        # le landing e l'anteprima passano dalle stesse liste → 404 quando spento
        assert 'righe = await _operator_corsi(org["id"])' in pub and 'righe = await _operator_prodotti(org["id"])' in pub
        ordini = (BACKEND / "services" / "order_creation_service.py").read_text()
        assert '"error": "modulo_spento"' in ordini and "status.HTTP_409_CONFLICT" in ordini
        # il conteggio «online» dei corsi legge il prodotto gemello, non il corso
        adm = (BACKEND / "routers" / "admin.py").read_text()
        assert '"item_type": "course"}},' in adm


class TestCheckoutDelCorso:
    def test_niente_secondo_account_con_aurya(self):
        hook = (FRONTEND / "features" / "storefront" / "hooks" / "useCheckoutForm.js").read_text()
        blocco = hook.split("const requiresCustomerAccount = useMemo(() => {")[1].split("}, [")[0]
        assert "if (platformLoggedIn) return false;" in blocco
        assert "}, [selectedItems, catalog, platformLoggedIn]);" in hook

    def test_cors_lascia_passare_l_account(self):
        srv = (BACKEND / "server.py").read_text()
        assert 'allow_headers=["Content-Type", "Authorization", "X-Fqz-Unlock", "X-Aurya-Account"]' in srv

    def test_successo_e_landing_gia_tuo(self):
        ok = (FRONTEND / "features" / "storefront" / "CheckoutResultPage.js").read_text()
        assert 'data-testid="checkout-corso-pronto"' in ok and "includes('course')" in ok and "Vai ai miei corsi" in ok
        land = (FRONTEND / "features" / "storefront" / "CorsoLandingPage.js").read_text()
        assert "corsiAPI.getMyCourses()" in land and 'data-testid="corso-landing-vai"' in land
        assert "['attivo', 'completato'].includes(r.iscrizione?.stato)" in land
        assert 'data-testid="corso-landing-gia-tuo"' in land


class TestCostiESblocco:
    def test_costi_parla_anche_di_corsi(self):
        src = (FRONTEND / "features" / "prelaunch" / "PricingPage.js").read_text()
        assert "Guide, audio, libri, kit e corsi online" in src
        assert "Sui prodotti e sui corsi online che vendi dal profilo il Pro azzera il 15%" in src
        assert "sui prodotti e sui corsi venduti dal profilo il 15%, zero col Pro" in src
        # i numeri restano SOLO su /costi: i Termini non cambiano prima dello sblocco
        from core.legal_versions import CURRENT_VERSION_TAG
        assert CURRENT_VERSION_TAG == "v2.12"

    def test_sblocco_v213_pronto_ma_non_applicato(self):
        """Lo script di sblocco deve trovare TUTTE le sue ancore (altrimenti
        marcisce in silenzio) e, a secco, non toccare nulla."""
        sys.path.insert(0, str(BACKEND / "scripts"))
        import sblocco_accademia_v213 as sb
        scritture, problemi = sb.pianifica()
        assert problemi == [], problemi
        cambiate = [p.name for p, s in scritture if p.read_text(encoding="utf-8") != s]
        # cambierebbero i 4 Termini, legal_versions, i 4 legal.json e stato.js
        assert set(cambiate) == {"terms_it.md", "terms_en.md", "terms_de.md", "terms_fr.md",
                                 "legal_versions.py", "legal.json", "stato.js"}
        # a secco il repo resta com'e'
        r = subprocess.run([sys.executable, str(BACKEND / "scripts" / "sblocco_accademia_v213.py")],
                           capture_output=True, text=True, cwd=str(BACKEND))
        assert r.returncode == 0 and "PROVA A SECCO" in r.stdout, r.stdout + r.stderr
        from core.legal_versions import CURRENT_VERSION_TAG
        assert CURRENT_VERSION_TAG == "v2.12"
        st = (FRONTEND / "features" / "accademia" / "stato.js").read_text()
        assert "export const ACCADEMIA_UI_PRONTA = false;" in st
