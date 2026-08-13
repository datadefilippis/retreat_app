"""Retreat fork — guardie sui piani commerciali retreat_free / retreat_pro.

Fase 1.3 del RETREAT_MASTER_PLAN (kill-list via configurazione):
le org sui piani retreat NON devono vedere i moduli AFianco non pertinenti
(ai_assistant, cashflow_monitor). Il gating esistente nasconde un modulo
quando nessun limite è positivo (_has_any_positive_limit → enabled=False).

Questi test sono deterministici (nessun DB): validano i seed a livello di
definizione — integrità referenziale piano commerciale → pricing plan slug,
limiti a zero sui piani *_disabled, e coerenza del modello Pydantic.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

from models.commercial_plan import CommercialPlan
from services.module_access import _has_any_positive_limit
from services.seed_commercial_plans import (
    ADDON_PLANS,
    COMMERCIAL_PLANS,
    RETREAT_COMMERCIAL_PLANS,
)
from services.seed_pricing import (
    AI_ASSISTANT_PLANS,
    CASHFLOW_MONITOR_PLANS,
    COMMERCE_PLANS,
    CUSTOMERS_LIGHT_PLANS,
    PRODUCT_CATALOG_PLANS,
)

ALL_PRICING = (
    AI_ASSISTANT_PLANS
    + CASHFLOW_MONITOR_PLANS
    + PRODUCT_CATALOG_PLANS
    + COMMERCE_PLANS
    + CUSTOMERS_LIGHT_PLANS
)
PRICING_BY_SLUG = {p["slug"]: p for p in ALL_PRICING}


def _plan(slug: str) -> dict:
    match = [p for p in RETREAT_COMMERCIAL_PLANS if p["slug"] == slug]
    assert match, f"piano commerciale {slug} mancante dal seed"
    return match[0]


class TestRetreatPlansPresence:
    def test_all_retreat_plans_seeded(self):
        slugs = {p["slug"] for p in RETREAT_COMMERCIAL_PLANS}
        assert slugs == {"retreat_free", "retreat_pro",
                         "retreat_founding", "retreat_partner"}

    def test_retreat_slugs_do_not_collide_with_legacy(self):
        legacy = {p["slug"] for p in COMMERCIAL_PLANS + ADDON_PLANS}
        retreat = {p["slug"] for p in RETREAT_COMMERCIAL_PLANS}
        assert not legacy & retreat

    def test_plans_validate_against_model(self):
        for data in RETREAT_COMMERCIAL_PLANS:
            plan = CommercialPlan(**data)
            assert plan.currency == "EUR"


class TestReferentialIntegrity:
    """Ogni module_plans slug deve esistere nei seed pricing — un refuso
    qui produrrebbe org con moduli irrisolvibili a runtime."""

    def test_all_module_plan_slugs_exist(self):
        for plan in RETREAT_COMMERCIAL_PLANS:
            for module_key, pricing_slug in plan["module_plans"].items():
                assert pricing_slug in PRICING_BY_SLUG, (
                    f"{plan['slug']}: pricing plan '{pricing_slug}' inesistente"
                )
                assert PRICING_BY_SLUG[pricing_slug]["module_key"] == module_key, (
                    f"{plan['slug']}: '{pricing_slug}' appartiene al modulo "
                    f"{PRICING_BY_SLUG[pricing_slug]['module_key']}, "
                    f"mappato invece su {module_key}"
                )


class TestKillList:
    """AI e cashflow devono risultare DISABILITATI (nessun limite positivo)
    su entrambi i piani retreat: è il meccanismo con cui la UI li nasconde."""

    def test_disabled_pricing_plans_have_all_zero_limits(self):
        for slug in ("ai_assistant_disabled", "cashflow_monitor_disabled"):
            limits = PRICING_BY_SLUG[slug]["limits"]
            assert not _has_any_positive_limit(limits), (
                f"{slug} ha limiti positivi: {limits}"
            )

    def test_retreat_plans_point_killed_modules_to_disabled(self):
        for plan in RETREAT_COMMERCIAL_PLANS:
            assert plan["module_plans"]["ai_assistant"] == "ai_assistant_disabled"
            # Consolidamento WS-2 (decisione founder): il cashflow core resta
            # acceso — è il gestionale contabile — ma con le sotto-feature
            # non pertinenti spente (vedi test dedicato sotto).
            assert (
                plan["module_plans"]["cashflow_monitor"]
                == "cashflow_monitor_retreat"
            )

    def test_cashflow_retreat_core_on_subfeatures_off(self):
        """WS-2: gestionale acceso (analytics/dati/export), anomalie/alert/
        digest/fornitori/qualità-dati spenti — anche a modulo attivo."""
        limits = PRICING_BY_SLUG["cashflow_monitor_retreat"]["limits"]
        assert limits["analytics"] == -1
        assert limits["data_rows"] == -1
        assert limits["export"] == -1
        for off in ("email_alerts", "email_digest", "alert_config",
                    "suppliers", "data_quality"):
            assert limits[off] == 0, f"{off} deve essere spento"

    def test_commerce_retreat_rentals_off(self):
        """WS-2: la voce Affitti non serve al verticale ritiri."""
        assert PRICING_BY_SLUG["commerce_retreat"]["limits"]["rentals"] == 0

    def test_commerce_retreat_enables_selling(self):
        limits = PRICING_BY_SLUG["commerce_retreat"]["limits"]
        assert limits["orders_monthly"] == -1, "fee transazionale, non quota ordini"
        assert limits["checkout_stripe"] == -1
        assert limits["stores_max"] == 1
        assert _has_any_positive_limit(limits)

    def test_catalog_and_customers_enabled_on_both(self):
        for plan in RETREAT_COMMERCIAL_PLANS:
            for module_key in ("product_catalog", "customers_light"):
                pricing = PRICING_BY_SLUG[plan["module_plans"][module_key]]
                assert _has_any_positive_limit(pricing["limits"]), (
                    f"{plan['slug']}: {module_key} risulterebbe disabilitato"
                )


class TestPricingPositioning:
    def test_free_costs_zero_pro_costs_29(self):
        assert _plan("retreat_free")["price_monthly"] == 0.0
        assert _plan("retreat_pro")["price_monthly"] == 19.0

    def test_free_is_baseline_not_checkout_target(self):
        free = _plan("retreat_free")
        assert free["is_public"] is True
        assert free["is_self_serve"] is False

    def test_pro_is_self_serve(self):
        assert _plan("retreat_pro")["is_self_serve"] is True


class TestRetreatBusinessModel:
    """Decisioni founder 4/7/2026: fee legata al piano, founding dedicato.

    La fee piattaforma è SEPARATA dalle commissioni Stripe (che Stripe
    applica per conto suo sull'account connesso): qui si valida solo la
    parte piattaforma; la UI le dichiara distinte.
    """

    def test_free_fee_5_percent(self):
        assert _plan("retreat_free")["transaction_fee_percent"] == 5.0
        assert _plan("retreat_free")["price_monthly"] == 0.0

    def test_pro_zero_fee_price_29(self):
        # 16/7/2026 (decisione founder): il Pro azzera la fee — chi paga
        # il canone tiene tutto il transato.
        pro = _plan("retreat_pro")
        assert pro["transaction_fee_percent"] == 0.0
        assert pro["price_monthly"] == 19.0
        assert pro["price_yearly"] == 190.0
        assert pro["is_self_serve"] is True
        assert "billing.features.retreat_zero_fee" in pro["features_display"]

    def test_founding_is_dedicated_hidden_plan(self):
        f = _plan("retreat_founding")
        assert f["price_monthly"] == 0.0
        assert f["transaction_fee_percent"] == 0.0   # trattamento Pro (zero fee)
        assert f["is_public"] is False               # non in pagina pricing
        assert f["is_self_serve"] is False           # solo assegnazione admin
        # founding = tutto Pro: stessi module_plans
        assert f["module_plans"] == _plan("retreat_pro")["module_plans"]

    def test_all_retreat_plans_declare_fee(self):
        # Ogni piano retreat DEVE dichiarare la fee: il provisioning la
        # sincronizza su org.application_fee_percent a ogni cambio piano.
        for p in RETREAT_COMMERCIAL_PLANS:
            assert p.get("transaction_fee_percent") is not None, p["slug"]
            assert 0 <= p["transaction_fee_percent"] <= 10

    def test_legacy_plans_do_not_govern_fee(self):
        # I piani legacy non devono toccare la fee org (None sul modello).
        for p in COMMERCIAL_PLANS + ADDON_PLANS:
            assert p.get("transaction_fee_percent") is None, p["slug"]

    def test_features_display_present_and_keyed(self):
        # Le card piani mostrano "cosa è incluso" — ogni piano deve avere
        # bullet i18n non vuoti con il prefisso billing.features.
        for p in RETREAT_COMMERCIAL_PLANS:
            feats = p["features_display"]
            assert len(feats) >= 3, p["slug"]
            for f in feats:
                assert f.startswith("billing.features."), f


class TestFeeSyncOnProvisioning:
    """La fee segue il piano: provision_commercial_plan (entry point
    canonico di OGNI cambio piano: signup, admin, webhook Stripe) deve
    sincronizzare org.application_fee_percent dal piano."""

    @staticmethod
    def _run(plan_doc):
        import asyncio
        from unittest.mock import AsyncMock, patch
        from services import plan_provisioning

        captured = {}

        async def fake_update(org_id, fields):
            captured.update(fields)

        with patch.object(plan_provisioning.billing_repository,
                          "get_commercial_plan",
                          AsyncMock(return_value=plan_doc)), \
             patch.object(plan_provisioning.subscription_repository,
                          "list_subscriptions_by_org",
                          AsyncMock(return_value=[])), \
             patch.object(plan_provisioning.billing_repository,
                          "update_org_billing_fields",
                          AsyncMock(side_effect=fake_update)), \
             patch.object(plan_provisioning,
                          "reconcile_stores_to_plan_limit",
                          AsyncMock(return_value={})):
            asyncio.run(
                plan_provisioning.provision_commercial_plan(
                    "org-x", plan_doc["slug"], "test"))
        return captured

    def test_retreat_plan_syncs_fee_to_org(self):
        fields = self._run({"slug": "retreat_pro", "module_plans": {},
                            "transaction_fee_percent": 2.0})
        assert fields["application_fee_percent"] == 2.0

    def test_zero_fee_stamps_zero_not_missing(self):
        # 0.0 è falsy: il sync non deve scambiarlo per "fee assente"
        # (il Pro è a zero commissioni dal 16/7/2026)
        fields = self._run({"slug": "retreat_pro", "module_plans": {},
                            "transaction_fee_percent": 0.0})
        assert fields["application_fee_percent"] == 0.0

    def test_free_plan_syncs_5(self):
        fields = self._run({"slug": "retreat_free", "module_plans": {},
                            "transaction_fee_percent": 5.0})
        assert fields["application_fee_percent"] == 5.0

    def test_legacy_plan_leaves_org_fee_untouched(self):
        # Piano senza transaction_fee_percent → il campo NON deve comparire
        # nell'update (il valore manuale su org resta com'è).
        fields = self._run({"slug": "core", "module_plans": {}})
        assert "application_fee_percent" not in fields


class TestPaymentsOverviewRoute:
    """D3 — /orders/payments-overview deve stare PRIMA di /{order_id}
    (FastAPI matcha in ordine di definizione: dopo, verrebbe catturato
    come order_id='payments-overview' → 404)."""

    def test_route_defined_before_dynamic_order_id(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "routers", "orders.py")
        src = open(path).read()
        assert src.index('@router.get("/payments-overview")') \
            < src.index('@router.get("/{order_id}")')

    def test_overview_uses_derived_review_state(self):
        # review_state non e' persistito: il conteggio DEVE passare da
        # derive_review_info, non da un count_documents sul campo.
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "routers", "orders.py")
        src = open(path).read()
        i = src.index('@router.get("/payments-overview")')
        block = src[i:i + 2500]
        assert "derive_review_info" in block
        assert 'count_documents(\n        {"organization_id": org_id, "review_state"' not in block


class TestRetreatDedicatedTiers:
    """Consolidamento 4/7/2026 — i limiti di 'Uso corrente' sono decisi
    da tier DEDICATI al verticale, non ereditati dai tier AFianco."""

    def test_catalog_tiers(self):
        free = PRICING_BY_SLUG["product_catalog_retreat_free"]
        pro = PRICING_BY_SLUG["product_catalog_retreat_pro"]
        # AB5 (founder, 13/8): il listino e' senza limiti ANCHE nel
        # Gratis — un tetto artificiale per spingere il Pro sarebbe
        # una promessa disonesta nella pagina /costi.
        assert free["limits"]["products"] == -1
        assert pro["limits"]["products"] == -1

    def test_commerce_pro_tier(self):
        pro = PRICING_BY_SLUG["commerce_retreat_pro"]
        assert pro["limits"]["stores_max"] == 3
        assert pro["limits"]["rentals"] == 0          # coerenza WS-3
        assert pro["limits"]["orders_monthly"] == -1  # fee, non quota

    def test_plans_use_dedicated_tiers(self):
        assert _plan("retreat_free")["module_plans"]["product_catalog"] \
            == "product_catalog_retreat_free"
        for slug in ("retreat_pro", "retreat_founding"):
            mp = _plan(slug)["module_plans"]
            assert mp["product_catalog"] == "product_catalog_retreat_pro"
            assert mp["commerce"] == "commerce_retreat_pro"

    def test_free_features_mention_ecommerce(self):
        # Richiesta founder: le voci non devono essere fuorvianti per
        # omissione — l'e-commerce incluso VA detto.
        # AB5: l'inventario e' stato potato alle sole promesse VERE
        # (via team/coupon/vetrine): 10 voci nel Gratis, non di piu'
        # ma nemmeno tre voci di facciata.
        feats = _plan("retreat_free")["features_display"]
        assert "billing.features.retreat_ecommerce" in feats
        assert len(feats) >= 10   # inventario completo, non tre voci


class TestPartnerZeroFeePlan:
    """Richiesta founder 5/7/2026: piano 0% fee nascosto, assegnabile
    on demand solo dal system admin."""

    def test_partner_zero_fee_hidden_admin_only(self):
        p = _plan("retreat_partner")
        assert p["transaction_fee_percent"] == 0.0
        assert p["price_monthly"] == 0.0
        assert p["is_public"] is False       # mai in pagina pricing
        assert p["is_self_serve"] is False   # solo assegnazione admin
        # tutto Pro: stessi tier
        assert p["module_plans"] == _plan("retreat_pro")["module_plans"]

    def test_provider_omits_fee_when_zero(self):
        # Stripe rifiuta application_fee_amount=0: il provider DEVE
        # includerlo solo quando la fee e' positiva.
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "payment_providers", "stripe", "provider.py")
        src = open(path).read()
        assert "request.application_fee_percent and request.application_fee_percent > 0" in src


class TestWizardCategory:
    """UX round 5/7 — categoria obbligatoria dalla tassonomia standard."""

    def test_payload_requires_category(self):
        from routers.event_occurrences import WizardProductPayload
        import pytest as _pt
        from pydantic import ValidationError
        with _pt.raises(ValidationError):
            WizardProductPayload(name="Ritiro X")     # senza categoria → 422

    def test_taxonomy_is_single_source(self):
        # la stessa costante alimenta directory E validazione wizard
        from models.retreat_taxonomy import RETREAT_CATEGORIES
        assert len(RETREAT_CATEGORIES) >= 9
        src = open(__file__.replace("tests/test_retreat_plans.py",
                                    "routers/event_occurrences.py")).read()
        assert "from models.retreat_taxonomy import RETREAT_CATEGORIES" in src


class TestStoreFirstGate:
    """Fix founder 5/7 — niente auto-creazione store: PUBBLICARE richiede
    un indirizzo pubblico (store attivo o public_slug legacy); la bozza
    resta sempre permessa."""

    @staticmethod
    def _has_home(store_doc, org_doc):
        import asyncio
        from unittest.mock import AsyncMock, patch
        from services import store_guard
        stores = AsyncMock(); stores.find_one = AsyncMock(return_value=store_doc)
        orgs = AsyncMock(); orgs.find_one = AsyncMock(return_value=org_doc)
        with patch("database.stores_collection", stores), \
             patch("database.organizations_collection", orgs):
            return asyncio.run(store_guard.org_has_public_home("org-x"))

    def test_active_store_allows(self):
        assert self._has_home({"_id": 1}, None) is True

    def test_legacy_slug_allows(self):
        assert self._has_home(None, {"public_slug": "masseria"}) is True

    def test_nothing_blocks(self):
        assert self._has_home(None, {"public_slug": None}) is False
        assert self._has_home(None, None) is False

    def test_wizard_and_patch_both_gated(self):
        import os
        src = open(os.path.join(os.path.dirname(__file__), "..",
                                "routers", "event_occurrences.py")).read()
        # due gate: creazione wizard con published + transizione PATCH
        assert src.count("store_required") == 2
        assert "Salvare in BOZZA resta sempre permesso" in src \
            or "bozza" in src.lower()


class TestOnboarding:
    """O1/O2 — signup sul piano giusto, stato derivato dai dati."""

    def test_signup_provisions_retreat_free(self):
        import os
        src = open(os.path.join(os.path.dirname(__file__), "..",
                                "services", "auth_service.py")).read()
        i = src.index("assigned_by=\"signup\"")
        block = src[max(0, i-300):i]
        assert 'plan_slug="retreat_free"' in block
        assert 'plan_slug="free"' not in block   # mai il legacy AFianco

    def test_onboarding_status_is_derived_not_stored(self):
        # lo stato NON si scrive mai: niente update/insert nell'endpoint
        import os
        src = open(os.path.join(os.path.dirname(__file__), "..",
                                "routers", "organizations.py")).read()
        i = src.index("async def onboarding_status")
        # TW4: l'endpoint ha due rami (snello 3 passi + legacy 5 passi),
        # la finestra copre entrambi
        block = src[i:i + 8000]
        assert "update_one" not in block and "insert_one" not in block
        for step in ("stripe_connected", "store_created", "retreat_created",
                     "retreat_published", "profile_completed"):
            assert step in block


class TestV4WizardUnification:
    """V4 — tassonomie per tipo + gate store-first su tutte le porte."""

    def test_taxonomies_defined_per_type(self):
        from models.retreat_taxonomy import PRODUCT_TAXONOMIES
        assert set(PRODUCT_TAXONOMIES) == {"service", "physical", "digital"}
        for tax in PRODUCT_TAXONOMIES.values():
            assert len(tax) >= 3

    def test_products_router_validates_and_gates(self):
        import os
        src = open(os.path.join(os.path.dirname(__file__), "..",
                                "routers", "products.py")).read()
        assert "PRODUCT_TAXONOMIES" in src
        assert src.count("await require_public_home") == 2   # POST + PATCH

    def test_single_guard_source(self):
        # una sola implementazione del criterio (services/store_guard):
        # event_occurrences DELEGA, non duplica
        import os
        src = open(os.path.join(os.path.dirname(__file__), "..",
                                "routers", "event_occurrences.py")).read()
        assert "from services.store_guard import org_has_public_home" in src

    def test_taxonomies_route_before_dynamic(self):
        import os
        src = open(os.path.join(os.path.dirname(__file__), "..",
                                "routers", "products.py")).read()
        assert src.index('@router.get("/taxonomies")') \
            < src.index('@router.get("/{product_id}"')


class TestStoreLegacyMigration:
    """S1 — fine del phantom store: GET /stores materializza il legacy."""

    def test_list_stores_invokes_lazy_migration(self):
        import os
        src = open(os.path.join(os.path.dirname(__file__), "..",
                                "routers", "stores.py")).read()
        i = src.index("async def list_stores")
        block = src[i:i + 2500]
        assert "_ensure_default_store" in block          # richiamata
        assert "public_slug" in block                     # solo org legacy
        # e mai per org nuove: il ramo scatta solo con slug/settings
        assert 'org.get("public_slug") or org.get("store_settings")' in block


class TestQuotaSweepQf1:
    """QF1 (4/8/2026) — lo sweep quote non scambia l'arredamento per
    consumo. In produzione ogni org riceveva «Limite negozi raggiunto»
    per il solo fatto di possedere l'unico negozio che il piano retreat
    prevede (stores_max=1, auto-creato), e l'avviso all'80% — con
    int(1*0.8)=0 — partiva perfino a zero negozi. Riprodotto in locale:
    org_quota_notices conteneva stores_max warn_80 used=0 ed exceeded
    used=1 per piu' org, rinnovati a ogni periodo mensile."""

    def test_stores_max_non_monitorato(self):
        """I tetti STRUTTURALI non generano email: stores_max e' il
        design del piano (1 negozio per org), non una quota."""
        from services.background_service import _MONITORED_METRICS
        metriche = [m for m, _, _ in _MONITORED_METRICS]
        assert "stores_max" not in metriche, \
            "stores_max e' tornato nello sweep: ogni org Aurya " \
            "ricevera' di nuovo 'Limite negozi raggiunto'"
        # le quote consumabili restano monitorate
        for viva in ("chat", "data_rows", "orders_monthly", "products"):
            assert viva in metriche, f"metrica consumabile sparita: {viva}"

    def test_soglia_warn_mai_zero(self):
        """La soglia dell'80% arrotonda per eccesso e non scende mai
        sotto 1: con qualunque limite, a uso zero non parte niente."""
        import math
        for limit in (1, 2, 3, 5, 100):
            threshold = max(1, math.ceil(limit * 0.8))
            assert threshold >= 1, limit
            assert 0 < threshold <= limit, limit
        # il sorgente usa esattamente questa formula (niente int() che
        # tronca verso lo zero)
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent
               / "services" / "background_service.py").read_text()
        assert "max(1, math.ceil(limit * 0.8))" in src
        assert "int(limit * 0.8)" not in src, \
            "la soglia troncata verso zero e' tornata"

    def test_piani_retreat_senza_quote_consumabili(self):
        """I piani Aurya dichiarano -1 (illimitato) su ogni metrica
        consumabile monitorata: con QF1 lo sweep non ha piu' nulla da
        dire a un'org retreat — che e' l'intenzione del founder
        («con Aurya non abbiamo impostato limiti di utilizzo»)."""
        import pymongo, re
        from pathlib import Path as _P
        envtxt = (_P(__file__).resolve().parent.parent / ".env").read_text()
        mongo = re.search(r'MONGO_URL="?([^"\n]+?)"?\n', envtxt).group(1)
        name = re.search(r'DB_NAME="?([^"\n]+?)"?\n', envtxt).group(1)
        db = pymongo.MongoClient(mongo)[name]
        consumabili = ("chat", "data_rows", "orders_monthly")
        for p in db.pricing_plans.find({"slug": {"$regex": "_retreat"}}):
            for k in consumabili:
                v = (p.get("limits") or {}).get(k)
                if v is not None:
                    assert v == -1, \
                        f"{p['slug']}.{k}={v}: quota consumabile finita " \
                        "su un piano retreat (lo sweep tornerebbe a scrivere)"


class TestAbPrezziCoerenti:
    """AB (founder, 13/8) — Pro passa a 19 EUR/mese (190/anno = 10
    mensilita'). La pagina pubblica /costi TIMBRA i numeri: queste
    guardie li tengono agganciati al seed, cosi' un futuro ritocco al
    listino non lascia la pagina a mentire in silenzio."""

    FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"

    def _pro(self):
        from services.seed_commercial_plans import RETREAT_COMMERCIAL_PLANS
        return next(p for p in RETREAT_COMMERCIAL_PLANS
                    if p["slug"] == "retreat_pro")

    def test_pro_costa_19_e_190(self):
        pro = self._pro()
        assert pro["price_monthly"] == 19.0
        assert pro["price_yearly"] == 190.0
        # annuale = 10 mensilita' (2 mesi in regalo): se uno dei due
        # numeri cambia da solo, la promessa "2 mesi gratis" salta
        assert pro["price_yearly"] == pro["price_monthly"] * 10

    def test_pagina_costi_allineata_al_seed(self):
        """PRICING nella pagina /costi == seed backend. Il free_fee
        combacia con la fee del piano gratis (application fee 5%)."""
        import re
        src = (self.FRONTEND / "src" / "features" / "prelaunch"
               / "PricingPage.js").read_text()
        m = re.search(r"PRICING = \{ pro_monthly: (\d+), "
                      r"pro_yearly: (\d+), free_fee: (\d+) \}", src)
        assert m, "PRICING non trovato nella pagina /costi"
        pro = self._pro()
        assert float(m.group(1)) == pro["price_monthly"]
        assert float(m.group(2)) == pro["price_yearly"]
        free = next(p for p in __import__(
            "services.seed_commercial_plans",
            fromlist=["RETREAT_COMMERCIAL_PLANS"]
        ).RETREAT_COMMERCIAL_PLANS if p["slug"] == "retreat_free")
        assert float(m.group(3)) == float(
            free.get("transaction_fee_percent") or 5.0)

    def test_faq_quanto_costa_con_link_ai_piani(self):
        """La FAQ della landing professionisti: tre punti e il rimando
        a /costi. La data promessa (31 dicembre 2026) e' scritta li'."""
        src = (self.FRONTEND / "src" / "features" / "prelaunch"
               / "OperatorLandingPage.js").read_text()
        assert "31 dicembre 2026" in src
        assert 'Link to="/costi"' in src
        assert "sempre gratuito" in src

    def test_rotta_costi_registrata(self):
        app = (self.FRONTEND / "src" / "App.js").read_text()
        assert 'path="/costi"' in app

    def test_gt2_fallback_allineato(self):
        """Il calcolatore fee->Pro usa il prezzo dal seed; il fallback
        cablato deve dire la stessa cifra."""
        src = (Path(__file__).resolve().parent.parent / "routers"
               / "cashflow.py").read_text()
        assert "else 19.0" in src
        assert "else 29.0" not in src

    # ── AB5 — voci vere nei piani (founder, 13/8) ──────────────────
    # Team e' nascosto (CS3b), coupon fuori dal menu snello, il listino
    # e' senza limiti anche nel Gratis: quelle promesse NON devono
    # riapparire nelle features dei piani retreat, ne' in admin ne'
    # sulla pagina pubblica /costi.

    _VOCI_BANDITE = (
        "team_2", "team_5",          # pagina Team nascosta
        "coupons",                    # coupon fuori dal mondo snello
        "catalog_100", "catalog_unlimited",  # listino senza limiti per tutti
        "stores_1", "stores_3",       # vetrine: concetto sparito (profilo=negozio)
        "product_types",              # gergo commerce
    )

    def test_ab5_voci_bandite_fuori_dai_piani(self):
        from services.seed_commercial_plans import RETREAT_COMMERCIAL_PLANS
        for piano in RETREAT_COMMERCIAL_PLANS:
            for chiave in piano.get("features_display", []):
                suffisso = chiave.split(".")[-1].removeprefix("retreat_")
                assert suffisso not in self._VOCI_BANDITE, (
                    f"{piano['slug']}: la voce {chiave!r} promette una "
                    "cosa nascosta o non piu' vera (AB5)")

    def test_ab5_pagina_costi_senza_promesse_morte(self):
        src = (self.FRONTEND / "src" / "features" / "prelaunch"
               / "PricingPage.js").read_text()
        for parola in ("Coupon", "persone nel team", "Listino senza limiti"):
            assert parola not in src, (
                f"/costi promette ancora {parola!r} (AB5)")

    # ── UP1 — upgrade e Stripe Connect senza vincoli legacy (13/8) ──
    # Bug prod: "Passa a Pro" falliva con "Organization has no active
    # Stripe subscription" (isPaid ragionava sullo slug 'free', non
    # sullo stato billing) e il collegamento Stripe appariva bloccato
    # da "Commerce Starter" (scala PLAN_TIERS senza i piani retreat).

    def test_up1_scala_piani_conosce_i_retreat(self):
        src = (self.FRONTEND / "src" / "hooks" / "useBilling.js").read_text()
        for slug in ("retreat_free", "retreat_pro", "retreat_founding"):
            assert f"{slug}:" in src, (
                f"PLAN_TIERS senza {slug}: il gate Stripe Connect "
                "torna a chiedere Commerce Starter (UP1)")

    def test_up1_ispaid_dallo_stato_non_dallo_slug(self):
        src = (self.FRONTEND / "src" / "hooks" / "useBilling.js").read_text()
        assert "isPaid: state.commercialPlanSlug !== 'free'" not in src, (
            "isPaid e' tornato slug-based: retreat_free risulterebbe "
            "a pagamento e l'upgrade proverebbe a modificare un "
            "abbonamento Stripe inesistente (UP1)")
        assert "'active', 'trialing', 'past_due'" in src
        assert "FREE_PLAN_SLUGS" in src and "'retreat_free'" in src

    def test_ab5b_team_fuori_dai_limiti_abbonamento(self):
        """La pagina Team e' nascosta (CS3b): il riquadro limiti in
        Impostazioni non deve mostrare "membri team" ai piani retreat.
        L'iniezione della metrica in /billing/usage-summary deve stare
        dietro il gate sul prefisso retreat_."""
        src = (Path(__file__).resolve().parent.parent / "routers"
               / "billing.py").read_text()
        gate = src.find('startswith("retreat_")')
        team_metric = src.find('"key": "team_members"')
        assert gate != -1, "gate retreat_ sparito da usage-summary (AB5b)"
        assert team_metric != -1
        assert gate < team_metric, (
            "la metrica team_members non e' dietro il gate retreat_ (AB5b)")
