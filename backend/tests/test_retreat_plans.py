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
    def test_both_retreat_plans_seeded(self):
        slugs = {p["slug"] for p in RETREAT_COMMERCIAL_PLANS}
        assert slugs == {"retreat_free", "retreat_pro"}

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
