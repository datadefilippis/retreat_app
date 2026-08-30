"""
CICLO RO (30/8/2026) — la regia degli operatori in system admin.

Il caso che l'ha generato: olisticamente.silvia non compariva in
/esplora-operatori e il founder ha scoperto che le due vetrine hanno
due regole (rete = sigillo admin; esplora = vetrina pubblicata) e che
il lucchetto exclude_from_listings (XL1) era ORFANO di UI — si
toccava a mano nel database. Piu': la pagina Organizations portava
reperti AFianco (catalogo moduli, pricing plans per-modulo, module
subscriptions) che non esistono in Aurya.

Decisioni del founder (30/8): interruttore Directory accanto a Rete;
specchietto con le info che contano (titolare, email, piano VERO,
profilo pubblico col link /o/{slug}); abbonamenti = SOLO i piani
commerciali; via i reperti.

Collaudato nel pane (30/8): lucchetto andata-e-ritorno sulla Masseria
demo (esplora perde e riacquista l'org), specchietto con
/o/masseria-demo linkato, dialog Piano con Gratis/Pro/Founding/
Partner, zero sezioni Modules/Subscriptions nel dettaglio.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
FRONTEND = BACKEND.parent / "frontend" / "src"
ADMIN_UI = FRONTEND / "features" / "admin" / "OrganizationsTab.js"


class TestLucchettoDirectory:
    def test_l_endpoint_esiste_ed_e_del_system_admin(self):
        src = (BACKEND / "routers" / "admin.py").read_text()
        assert '"/organizations/{org_id}/directory"' in src, \
            "manca l'endpoint del lucchetto directory"
        blocco = src.split('"/organizations/{org_id}/directory"')[1][:1600]
        assert "require_system_admin" in blocco, \
            "il lucchetto e' un potere del solo system admin"
        assert '"exclude_from_listings": not listed' in blocco, \
            "listed=True deve SPEGNERE il lucchetto (e viceversa)"

    def test_il_pubblico_rispetta_ancora_il_lucchetto(self):
        """XL1 gia' viveva in public.py: la UI nuova non deve averlo
        indebolito. Le liste pubbliche proiettano e filtrano il flag."""
        src = (BACKEND / "routers" / "public.py").read_text()
        assert src.count("exclude_from_listings") >= 2, \
            "le liste pubbliche non guardano piu' il lucchetto"


class TestSpecchietto:
    def test_la_lista_porta_le_info_della_regia(self):
        modello = (BACKEND / "models" / "admin.py").read_text()
        for campo in ("directory_listed", "profile_published",
                      "admin_email", "profile_slug"):
            assert campo in modello, f"OrgSummary ha perso {campo}"
        router = (BACKEND / "routers" / "admin.py").read_text()
        assert "slug_pubblico" in router and "email_titolare" in router, \
            "l'arricchimento batch (vetrine+titolari) e' sparito"
        assert '"is_published": True' in router, \
            "profile_published deve usare il criterio di esplora (vetrina pubblicata)"

    def test_lo_slug_esce_solo_se_pubblicato(self):
        """/o/{slug} da non pubblicato fa 404: il link si mostra solo
        quando e' vero."""
        router = (BACKEND / "routers" / "admin.py").read_text()
        assert "slug_pubblico.get(" in router
        assert "pubblicate = set(slug_pubblico)" in router


class TestBonificaAfianco:
    def test_i_reperti_sono_usciti_dalla_pagina(self):
        src = ADMIN_UI.read_text()
        for reperto in ("listAvailableModules", "listPricingPlans",
                        "Module Subscriptions", "buildModuleList",
                        "handleToggleModule", "subDialogOpen",
                        "listOrgSubscriptions"):
            assert reperto not in src, \
                f"reperto AFianco ancora in pagina: {reperto}"

    def test_gli_abbonamenti_sono_quelli_veri(self):
        """Il dialog Piano usa i piani commerciali (free/pro/founding/
        partner), non i pricing plans per-modulo."""
        src = ADMIN_UI.read_text()
        assert "getCommercialPlans" in src and "setOrgCommercialPlan" in src
        assert "commercialPlans.map" in src

    def test_la_riga_e_lo_specchietto_della_regia(self):
        src = ADMIN_UI.read_text()
        assert "handleToggleDirectory" in src and "setDirectoryListed" in src
        assert "'✓ Directory' : 'Directory'" in src
        assert "org.admin_email" in src, "l'email del titolare sotto il nome"
        assert "/o/${org.profile_slug}" in src.replace("`", ""), \
            "il link al profilo pubblico nella riga"
        assert "non pubblicato" in src
        api = (FRONTEND / "api" / "admin.js").read_text()
        assert "setDirectoryListed" in api

    def test_il_dettaglio_ha_i_quattro_gesti(self):
        """Rete, Directory, Sospendi, Elimina — la regia in un posto."""
        src = ADMIN_UI.read_text()
        blocco = src[src.index("LO SPECCHIETTO"):]
        for gesto in ("handleToggleNetwork", "handleToggleDirectory",
                      "handleToggleStatus", "setDeleteOrg"):
            assert gesto in blocco[:6000], f"manca il gesto {gesto} nello specchietto"


class TestRo2SecondaViaPubblicazione:
    """RO2 (30/8) — IL CASO SILVIA. Il suo profilo era VIVO su
    /o/{slug} (gradino GT6: salvataggio con bio → public_slug + flag
    legacy is_storefront_published) ma /esplora-operatori e lo
    specchietto admin guardavano SOLO la collezione stores: profilo
    online, directory e admin che dicevano «non pubblicato». Il
    criterio giusto e' quello di _resolve_org: store pubblicato
    OPPURE via legacy. Nessuna «forza pubblicazione» admin: il
    prodotto pubblica gia' da solo al salvataggio con bio."""

    def test_esplora_conosce_la_seconda_via(self):
        src = (BACKEND / "routers" / "public.py").read_text()
        blocco = src[src.index("async def public_operators_index"):]
        assert '"store_settings.is_storefront_published": True' in blocco[:6000], \
            "esplora-operatori ignora di nuovo i profili GT6"
        assert '"id": {"$nin": org_ids}' in blocco[:6000], \
            "le pseudo-vetrine non devono duplicare chi ha gia' lo store"

    def test_lo_specchietto_conosce_la_seconda_via(self):
        src = (BACKEND / "routers" / "admin.py").read_text()
        blocco = src[src.index("slug_pubblico"):]
        assert '"store_settings.is_storefront_published": True' in blocco[:2500], \
            "lo specchietto dice «non pubblicato» a profili online"

    def test_il_criterio_resta_quello_di_resolve_org(self):
        """La fonte di verita' della pubblicazione e' _resolve_org:
        se cambia li', queste due viste vanno riallineate."""
        src = (BACKEND / "routers" / "public.py").read_text()
        r = src[src.index("async def _resolve_org_uncached"):]
        assert "is_storefront_published" in r[:3000]
