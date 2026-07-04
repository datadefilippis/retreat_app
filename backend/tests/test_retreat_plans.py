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
    def test_all_three_retreat_plans_seeded(self):
        slugs = {p["slug"] for p in RETREAT_COMMERCIAL_PLANS}
        assert slugs == {"retreat_free", "retreat_pro", "retreat_founding"}

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
        assert _plan("retreat_pro")["price_monthly"] == 29.0

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

    def test_pro_fee_2_percent_price_29(self):
        pro = _plan("retreat_pro")
        assert pro["transaction_fee_percent"] == 2.0
        assert pro["price_monthly"] == 29.0
        assert pro["price_yearly"] == 290.0
        assert pro["is_self_serve"] is True

    def test_founding_is_dedicated_hidden_plan(self):
        f = _plan("retreat_founding")
        assert f["price_monthly"] == 0.0
        assert f["transaction_fee_percent"] == 2.0   # trattamento Pro
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
        assert free["limits"]["products"] == 100
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
        feats = _plan("retreat_free")["features_display"]
        assert "billing.features.retreat_ecommerce" in feats
        assert len(feats) >= 12   # inventario completo, non tre voci
